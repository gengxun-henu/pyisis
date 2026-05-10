"""Dense per-pixel NCC matching between stereo image pairs.

Author: Geng Xun
Created: 2026-05-10
Last Modified: 2026-05-10
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .disparity_model import DisparityModel


@dataclass
class NCCMatchOptions:
    window_size: int = 21
    search_range: int = 5
    ncc_threshold: float = 0.70
    enable_subpixel: bool = True
    enable_gruen: bool = False
    chunk_size_lines: int = 100


def _read_cube_data(cube) -> np.ndarray:
    """Read single-band cube data into a 2D numpy array (lines x samples)."""
    return np.asarray(cube.read(band=1))


def _is_valid_pixel(value: float) -> bool:
    if math.isnan(value):
        return False
    # ISIS Null pixel value for floats is approximately -3.4028235e+38.
    if value <= -3.4028234663852886e+38:
        return False
    return True


def _compute_ncc_score(pattern: np.ndarray, search_region: np.ndarray) -> tuple[float, int, int]:
    """Compute NCC between ``pattern`` and every position inside ``search_region``.

    Returns ``(best_ncc, best_offset_y, best_offset_x)`` where the offsets are
    relative to the search-region center (``0`` means center).
    """
    ph, pw = pattern.shape
    sh, sw = search_region.shape

    if sh < ph or sw < pw:
        return float("-inf"), 0, 0

    pattern_mean = float(np.mean(pattern))
    pattern_std = float(np.std(pattern))
    if pattern_std < 1e-10:
        return float("-inf"), 0, 0

    pattern_norm = (pattern - pattern_mean) / pattern_std

    max_ncc = float("-inf")
    best_oy = 0
    best_ox = 0

    for oy in range(sh - ph + 1):
        for ox in range(sw - pw + 1):
            window = search_region[oy:oy + ph, ox:ox + pw]
            win_mean = float(np.mean(window))
            win_std = float(np.std(window))
            if win_std < 1e-10:
                continue
            win_norm = (window - win_mean) / win_std
            ncc = float(np.sum(pattern_norm * win_norm) / (ph * pw))
            if ncc > max_ncc:
                max_ncc = ncc
                best_oy = oy
                best_ox = ox

    center_oy = (sh - ph) // 2
    center_ox = (sw - pw) // 2
    return max_ncc, best_oy - center_oy, best_ox - center_ox


def _ncc_at(pattern: np.ndarray, search_region: np.ndarray, oy: int, ox: int) -> float:
    ph, pw = pattern.shape
    sh, sw = search_region.shape
    if oy < 0 or ox < 0 or oy + ph > sh or ox + pw > sw:
        return float("-inf")
    window = search_region[oy:oy + ph, ox:ox + pw]
    p_mean = float(np.mean(pattern))
    p_std = float(np.std(pattern))
    w_mean = float(np.mean(window))
    w_std = float(np.std(window))
    if p_std < 1e-10 or w_std < 1e-10:
        return float("-inf")
    return float(np.sum((pattern - p_mean) * (window - w_mean)) / (ph * pw * p_std * w_std))


def _subpixel_refine(
    pattern: np.ndarray,
    search_region: np.ndarray,
    int_oy: int,
    int_ox: int,
) -> tuple[float, float, float]:
    """Parabolic subpixel refinement around an integer best position.

    Inputs are absolute offsets inside ``search_region``. Returns
    ``(subpixel_oy, subpixel_ox, refined_ncc)`` where the offsets are still
    relative to the search-region center.
    """
    ph, pw = pattern.shape
    sh, sw = search_region.shape
    center_oy = (sh - ph) // 2
    center_ox = (sw - pw) // 2

    fx_left = _ncc_at(pattern, search_region, int_oy, int_ox - 1)
    fx_center = _ncc_at(pattern, search_region, int_oy, int_ox)
    fx_right = _ncc_at(pattern, search_region, int_oy, int_ox + 1)

    dx_sub = 0.0
    denom_x = fx_left + fx_right - 2.0 * fx_center
    if math.isfinite(denom_x) and abs(denom_x) > 1e-10:
        dx_sub = (fx_left - fx_right) / (2.0 * denom_x)
    dx_sub = max(-0.5, min(0.5, dx_sub))

    fy_up = _ncc_at(pattern, search_region, int_oy - 1, int_ox)
    fy_center = _ncc_at(pattern, search_region, int_oy, int_ox)
    fy_down = _ncc_at(pattern, search_region, int_oy + 1, int_ox)

    dy_sub = 0.0
    denom_y = fy_up + fy_down - 2.0 * fy_center
    if math.isfinite(denom_y) and abs(denom_y) > 1e-10:
        dy_sub = (fy_up - fy_down) / (2.0 * denom_y)
    dy_sub = max(-0.5, min(0.5, dy_sub))

    refined_ncc = fx_center

    subpixel_oy = (int_oy - center_oy) + dy_sub
    subpixel_ox = (int_ox - center_ox) + dx_sub
    return subpixel_oy, subpixel_ox, refined_ncc


def _match_pixel(
    left_data: np.ndarray,
    right_data: np.ndarray,
    s: int,
    l: int,
    pred_dx: float,
    pred_dy: float,
    options: NCCMatchOptions,
) -> tuple[float, float, float]:
    """Match a single pixel. Returns ``(dx, dy, ncc)`` or ``(nodata, nodata, nodata)``."""
    nodata = -9999.0
    lines, samples = left_data.shape
    half_w = options.window_size // 2
    sr = options.search_range

    if not _is_valid_pixel(float(left_data[l, s])):
        return nodata, nodata, nodata

    center_s = int(round(s + pred_dx))
    center_l = int(round(l + pred_dy))

    ps = max(0, s - half_w)
    pe = min(samples, s + half_w + 1)
    pl = max(0, l - half_w)
    pe_l = min(lines, l + half_w + 1)
    pattern = left_data[pl:pe_l, ps:pe]
    if pattern.size == 0:
        return nodata, nodata, nodata

    search_s_start = max(0, center_s - half_w - sr)
    search_s_end = min(samples, center_s + half_w + sr + 1)
    search_l_start = max(0, center_l - half_w - sr)
    search_l_end = min(lines, center_l + half_w + sr + 1)
    search_region = right_data[search_l_start:search_l_end, search_s_start:search_s_end]
    if search_region.size == 0:
        return nodata, nodata, nodata

    ncc, off_oy, off_ox = _compute_ncc_score(pattern, search_region)
    if not math.isfinite(ncc) or ncc < options.ncc_threshold:
        return nodata, nodata, nodata

    ph, pw = pattern.shape
    sh, sw = search_region.shape
    center_oy = (sh - ph) // 2
    center_ox = (sw - pw) // 2
    int_oy = center_oy + off_oy
    int_ox = center_ox + off_ox

    # Best match's top-left in right image -> center pixel = +half_w (in pattern frame).
    best_match_s = search_s_start + int_ox + half_w
    best_match_l = search_l_start + int_oy + half_w

    if not options.enable_subpixel:
        return float(best_match_s) - s, float(best_match_l) - l, ncc

    can_refine = (
        int_oy >= 1
        and int_ox >= 1
        and int_oy + ph + 1 <= sh
        and int_ox + pw + 1 <= sw
    )
    if not can_refine:
        return float(best_match_s) - s, float(best_match_l) - l, ncc

    sub_oy, sub_ox, refined_ncc = _subpixel_refine(pattern, search_region, int_oy, int_ox)
    final_s = search_s_start + center_ox + sub_ox + half_w
    final_l = search_l_start + center_oy + sub_oy + half_w
    # Clamp the absolute right-image coordinate to valid 0-based pixel bounds.
    final_s = max(0.0, min(float(samples - 1), final_s))
    final_l = max(0.0, min(float(lines - 1), final_l))
    return final_s - s, final_l - l, refined_ncc


def dense_ncc_match(
    left_cube,
    right_cube,
    model: DisparityModel,
    options: NCCMatchOptions,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-pixel NCC matching.

    Returns ``(disparity_x, disparity_y, ncc_score)`` as ``H x W`` ``float32``
    arrays. Failed matches are filled with the nodata value ``-9999.0``.
    """
    left_data = _read_cube_data(left_cube)
    right_data = _read_cube_data(right_cube)
    lines, samples = left_data.shape
    nodata = -9999.0

    disp_x = np.full((lines, samples), nodata, dtype=np.float32)
    disp_y = np.full((lines, samples), nodata, dtype=np.float32)
    ncc = np.full((lines, samples), nodata, dtype=np.float32)

    chunk_size = max(1, int(options.chunk_size_lines))
    for start_line in range(0, lines, chunk_size):
        end_line = min(start_line + chunk_size, lines)
        for l in range(start_line, end_line):
            for s in range(samples):
                # Disparity prior is evaluated in 1-based ISIS coordinates.
                pred_dx = model.eval_dx(float(s + 1), float(l + 1))
                pred_dy = model.eval_dy(float(s + 1), float(l + 1))
                dx, dy, ncc_val = _match_pixel(
                    left_data, right_data, s, l, pred_dx, pred_dy, options
                )
                disp_x[l, s] = dx
                disp_y[l, s] = dy
                ncc[l, s] = ncc_val

    return disp_x, disp_y, ncc


def count_disparity_stats(
    disparity_x: np.ndarray,
    disparity_y: np.ndarray,
    ncc_score: np.ndarray,
    ncc_threshold: float = 0.70,
    nodata_value: float = -9999.0,
) -> dict[str, int]:
    """Count matching statistics."""
    total = int(disparity_x.size)
    valid_mask = ncc_score >= ncc_threshold
    matched = int(np.sum(valid_mask))
    failed = total - matched
    return {
        "total_pixels": total,
        "matched_count": matched,
        "failed_match_count": failed,
    }


def write_disparity_cube(
    ip,
    disparity_x: np.ndarray,
    disparity_y: np.ndarray,
    ncc_score: np.ndarray,
    output_path: str,
    nodata_value: float = -9999.0,
) -> None:
    """Write a 3-band ``float32`` disparity cube with BandBin labels."""
    lines, samples = disparity_x.shape

    cube = ip.Cube()
    cube.set_dimensions(samples, lines, 3)
    if hasattr(ip, "PixelType") and hasattr(cube, "set_pixel_type"):
        cube.set_pixel_type(ip.PixelType.Real)
    cube.create(output_path)

    try:
        if hasattr(ip, "PvlGroup") and hasattr(cube, "put_group"):
            band_bin = ip.PvlGroup("BandBin")
            band_names = ["X_Disparity", "Y_Disparity", "NCC_Correlation_Coefficient"]
            for name in band_names:
                band_bin.insert(ip.PvlKeyword("Name", name))
            cube.put_group(band_bin)

        for band_idx, band_data in enumerate(
            [disparity_x, disparity_y, ncc_score], start=1
        ):
            for line_idx in range(lines):
                line_manager = ip.LineManager(cube, False)
                if hasattr(line_manager, "set_line"):
                    line_manager.set_line(line_idx + 1, band_idx)
                for sample_idx in range(samples):
                    line_manager[sample_idx] = float(band_data[line_idx, sample_idx])
                cube.write(line_manager)
    finally:
        if hasattr(cube, "close"):
            cube.close()
