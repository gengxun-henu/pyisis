"""DOM tile-validity cache helpers for full-resolution matching prefilters.

Author: Geng Xun
Created: 2026-05-02
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, TYPE_CHECKING

import numpy as np

from .preprocess import expand_invalid_mask_for_radius, summarize_valid_pixels
from .runtime import bootstrap_runtime_environment
from .tiling import TileWindow

if TYPE_CHECKING:
    from .tile_matching import PairedTileWindow


bootstrap_runtime_environment()

import isis_pybind as ip


CACHE_FORMAT_VERSION = 1
DEFAULT_TILE_VALIDITY_CELL_WIDTH = 1024
DEFAULT_TILE_VALIDITY_CELL_HEIGHT = 1024


@dataclass(frozen=True, slots=True)
class TileValidityIndex:
    dom_path: str
    image_width: int
    image_height: int
    cell_width: int
    cell_height: int
    grid_width: int
    grid_height: int
    valid_counts: np.ndarray
    total_counts: np.ndarray
    uncertain: np.ndarray
    manifest: dict[str, Any]


@dataclass(frozen=True, slots=True)
class TileValidityUpperBound:
    valid_pixel_upper_bound: int
    window_pixel_count: int
    valid_ratio_upper_bound: float
    has_uncertain_cells: bool


@dataclass(frozen=True, slots=True)
class TileValidityPrefilterResult:
    kept_windows: list[PairedTileWindow]
    skipped_windows: list[PairedTileWindow]
    preindexed_skipped_tile_count: int
    skip_reasons: dict[str, int]


def validate_tile_validity_cell_size(value: int, *, field_name: str) -> int:
    resolved_value = int(value)
    if resolved_value <= 0:
        raise ValueError(f"{field_name} must be positive.")
    return resolved_value


def _covered_cell_range(start: int, length: int, cell_size: int, grid_size: int) -> range:
    """Return the inclusive cell index range covered by a span, or empty if none."""
    if length <= 0 or cell_size <= 0 or grid_size <= 0:
        return range(0, 0)

    start_cell = start // cell_size
    end_cell = (start + length - 1) // cell_size

    if end_cell < 0 or start_cell >= grid_size:
        return range(0, 0)

    clamped_start = max(0, start_cell)
    clamped_end = min(grid_size - 1, end_cell)
    if clamped_end < clamped_start:
        return range(0, 0)

    return range(clamped_start, clamped_end + 1)


def window_valid_upper_bound(index: TileValidityIndex, window: TileWindow) -> TileValidityUpperBound:
    """Compute a conservative upper bound for valid pixels in a window."""
    x_range = _covered_cell_range(window.start_x, window.width, index.cell_width, index.grid_width)
    y_range = _covered_cell_range(window.start_y, window.height, index.cell_height, index.grid_height)

    valid_pixel_upper_bound = 0
    has_uncertain_cells = False
    for cell_y in y_range:
        for cell_x in x_range:
            valid_pixel_upper_bound += int(index.valid_counts[cell_y, cell_x])
            if bool(index.uncertain[cell_y, cell_x]):
                has_uncertain_cells = True

    window_pixel_count = int(window.width * window.height)
    if window_pixel_count <= 0:
        valid_ratio_upper_bound = 0.0
    else:
        valid_ratio_upper_bound = min(valid_pixel_upper_bound / float(window_pixel_count), 1.0)

    return TileValidityUpperBound(
        valid_pixel_upper_bound=valid_pixel_upper_bound,
        window_pixel_count=window_pixel_count,
        valid_ratio_upper_bound=valid_ratio_upper_bound,
        has_uncertain_cells=has_uncertain_cells,
    )


def _side_skip_reason(
    upper_bound: TileValidityUpperBound,
    *,
    side_name: str,
    valid_pixel_percent_threshold: float,
) -> str | None:
    if upper_bound.has_uncertain_cells:
        return None
    if valid_pixel_percent_threshold > 0 and upper_bound.valid_ratio_upper_bound < valid_pixel_percent_threshold:
        return f"{side_name}_valid_upper_bound_below_threshold"
    return None


def prefilter_paired_windows_by_validity(
    windows: list[PairedTileWindow],
    *,
    left_index: TileValidityIndex,
    right_index: TileValidityIndex,
    valid_pixel_percent_threshold: float,
) -> TileValidityPrefilterResult:
    """Conservatively skip only when upper bounds cannot meet the [0, 1] ratio threshold."""
    if valid_pixel_percent_threshold < 0.0 or valid_pixel_percent_threshold > 1.0:
        raise ValueError("valid_pixel_percent_threshold must be within [0.0, 1.0].")
    if valid_pixel_percent_threshold <= 0:
        return TileValidityPrefilterResult(
            kept_windows=list(windows),
            skipped_windows=[],
            preindexed_skipped_tile_count=0,
            skip_reasons={},
        )

    kept_windows: list[PairedTileWindow] = []
    skipped_windows: list[PairedTileWindow] = []
    skip_reasons: dict[str, int] = {}

    for paired_window in windows:
        left_upper_bound = window_valid_upper_bound(left_index, paired_window.left_window)
        right_upper_bound = window_valid_upper_bound(right_index, paired_window.right_window)

        skip_reason = _side_skip_reason(
            left_upper_bound,
            side_name="left",
            valid_pixel_percent_threshold=valid_pixel_percent_threshold,
        )
        if skip_reason is None:
            skip_reason = _side_skip_reason(
                right_upper_bound,
                side_name="right",
                valid_pixel_percent_threshold=valid_pixel_percent_threshold,
            )

        if skip_reason is None:
            kept_windows.append(paired_window)
        else:
            skipped_windows.append(paired_window)
            skip_reasons[skip_reason] = skip_reasons.get(skip_reason, 0) + 1

    return TileValidityPrefilterResult(
        kept_windows=kept_windows,
        skipped_windows=skipped_windows,
        preindexed_skipped_tile_count=len(skipped_windows),
        skip_reasons=skip_reasons,
    )


def default_tile_validity_cache_dir(
    *,
    metadata_output: str | Path | None = None,
    left_output_key: str | Path | None = None,
) -> Path:
    if metadata_output is not None:
        return Path(metadata_output).parent.parent / "tile_validity_cache"
    if left_output_key is not None:
        return Path(left_output_key).parent.parent / "tile_validity_cache"
    return Path.cwd() / "tile_validity_cache"


def _read_cube_window_for_validity(cube: ip.Cube, window: TileWindow, *, band: int) -> np.ndarray:
    brick = ip.Brick(cube, window.width, window.height, 1)
    brick.set_base_position(window.start_x + 1, window.start_y + 1, band)
    cube.read(brick)
    return np.asarray(brick.double_buffer(), dtype=np.float64).reshape((window.height, window.width))


def _dom_file_fingerprint(dom_path: str | Path) -> dict[str, object]:
    resolved_path = Path(dom_path)
    stat = resolved_path.stat()
    return {
        "path": str(resolved_path.resolve()),
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def _index_manifest(
    *,
    dom_path: str | Path,
    image_width: int,
    image_height: int,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    invalid_pixel_radius: int,
    cell_width: int,
    cell_height: int,
    format_version: int = CACHE_FORMAT_VERSION,
) -> dict[str, object]:
    grid_width = int(math.ceil(int(image_width) / int(cell_width)))
    grid_height = int(math.ceil(int(image_height) / int(cell_height)))

    return {
        "format_version": int(format_version),
        "dom": _dom_file_fingerprint(dom_path),
        "image_width": int(image_width),
        "image_height": int(image_height),
        "band": int(band),
        "invalid_values": [float(value) for value in invalid_values],
        "special_pixel_abs_threshold": float(special_pixel_abs_threshold),
        "invalid_pixel_radius": int(invalid_pixel_radius),
        "cell_width": int(cell_width),
        "cell_height": int(cell_height),
        "grid_width": grid_width,
        "grid_height": grid_height,
    }


def _cache_key_for_manifest(manifest: dict[str, object]) -> str:
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_paths(cache_dir: str | Path, cache_key: str) -> tuple[Path, Path]:
    resolved_dir = Path(cache_dir)
    return resolved_dir / f"{cache_key}.json", resolved_dir / f"{cache_key}.npz"


def _load_index_from_cache(manifest_path: str | Path, data_path: str | Path) -> TileValidityIndex:
    resolved_manifest_path = Path(manifest_path)
    resolved_data_path = Path(data_path)

    manifest = json.loads(resolved_manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Cache manifest must decode to an object.")
    if int(manifest.get("format_version", -1)) != CACHE_FORMAT_VERSION:
        raise ValueError("Unsupported cache manifest format version.")

    required_keys = (
        "dom",
        "image_width",
        "image_height",
        "cell_width",
        "cell_height",
        "grid_width",
        "grid_height",
    )
    for key in required_keys:
        if key not in manifest:
            raise ValueError(f"Cache manifest missing required key {key!r}.")

    with np.load(resolved_data_path, allow_pickle=False) as npz:
        try:
            valid_counts = np.asarray(npz["valid_counts"], dtype=np.int64)
            total_counts = np.asarray(npz["total_counts"], dtype=np.int64)
            uncertain = np.asarray(npz["uncertain"], dtype=bool)
        except KeyError as exc:
            raise ValueError(f"Cache data missing required array {exc.args[0]!r}.") from exc

    expected_shape = (int(manifest["grid_height"]), int(manifest["grid_width"]))
    if valid_counts.shape != expected_shape or total_counts.shape != expected_shape or uncertain.shape != expected_shape:
        raise ValueError("Cache arrays do not match manifest grid dimensions.")

    dom_fingerprint = manifest.get("dom")
    dom_path = None
    if isinstance(dom_fingerprint, dict):
        dom_path = dom_fingerprint.get("path")

    return TileValidityIndex(
        dom_path=str(dom_path) if dom_path else "",
        image_width=int(manifest["image_width"]),
        image_height=int(manifest["image_height"]),
        cell_width=int(manifest["cell_width"]),
        cell_height=int(manifest["cell_height"]),
        grid_width=int(manifest["grid_width"]),
        grid_height=int(manifest["grid_height"]),
        valid_counts=valid_counts,
        total_counts=total_counts,
        uncertain=uncertain,
        manifest=manifest,  # type: ignore[arg-type]
    )


def _save_index_to_cache(index: TileValidityIndex, manifest_path: str | Path, data_path: str | Path) -> None:
    resolved_manifest_path = Path(manifest_path)
    resolved_data_path = Path(data_path)
    resolved_manifest_path.parent.mkdir(parents=True, exist_ok=True)

    resolved_manifest_path.write_text(
        json.dumps(index.manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    np.savez_compressed(
        resolved_data_path,
        valid_counts=np.asarray(index.valid_counts, dtype=np.int64),
        total_counts=np.asarray(index.total_counts, dtype=np.int64),
        uncertain=np.asarray(index.uncertain, dtype=bool),
    )


def _cell_window_with_halo(
    *,
    cell_x: int,
    cell_y: int,
    image_width: int,
    image_height: int,
    cell_width: int,
    cell_height: int,
    invalid_pixel_radius: int,
) -> tuple[TileWindow, slice, slice, int, int]:
    start_x = int(cell_x) * int(cell_width)
    start_y = int(cell_y) * int(cell_height)

    actual_cell_width = max(0, min(int(cell_width), int(image_width) - start_x))
    actual_cell_height = max(0, min(int(cell_height), int(image_height) - start_y))

    halo = max(0, int(invalid_pixel_radius))
    read_start_x = max(0, start_x - halo)
    read_start_y = max(0, start_y - halo)
    read_end_x = min(int(image_width), start_x + actual_cell_width + halo)
    read_end_y = min(int(image_height), start_y + actual_cell_height + halo)

    read_window = TileWindow(
        start_x=read_start_x,
        start_y=read_start_y,
        width=read_end_x - read_start_x,
        height=read_end_y - read_start_y,
    )

    inner_x = slice(start_x - read_start_x, start_x - read_start_x + actual_cell_width)
    inner_y = slice(start_y - read_start_y, start_y - read_start_y + actual_cell_height)

    return read_window, inner_y, inner_x, actual_cell_width, actual_cell_height


def _build_index_from_open_cube(
    *,
    cube: ip.Cube,
    dom_path: str | Path,
    manifest: dict[str, object],
) -> TileValidityIndex:
    image_width = int(manifest["image_width"])
    image_height = int(manifest["image_height"])
    band = int(manifest["band"])
    invalid_values = tuple(float(value) for value in manifest.get("invalid_values", []))
    special_pixel_abs_threshold = float(manifest["special_pixel_abs_threshold"])
    invalid_pixel_radius = int(manifest["invalid_pixel_radius"])
    cell_width = int(manifest["cell_width"])
    cell_height = int(manifest["cell_height"])
    grid_width = int(manifest["grid_width"])
    grid_height = int(manifest["grid_height"])

    if image_width != int(cube.sample_count()) or image_height != int(cube.line_count()):
        raise ValueError("Cube dimensions do not match the cache manifest.")

    valid_counts = np.zeros((grid_height, grid_width), dtype=np.int64)
    total_counts = np.zeros((grid_height, grid_width), dtype=np.int64)
    uncertain = np.zeros((grid_height, grid_width), dtype=bool)

    for cell_y in range(grid_height):
        for cell_x in range(grid_width):
            read_window, inner_y, inner_x, actual_width, actual_height = _cell_window_with_halo(
                cell_x=cell_x,
                cell_y=cell_y,
                image_width=image_width,
                image_height=image_height,
                cell_width=cell_width,
                cell_height=cell_height,
                invalid_pixel_radius=invalid_pixel_radius,
            )

            if actual_width <= 0 or actual_height <= 0:
                continue

            values = _read_cube_window_for_validity(cube, read_window, band=band)
            invalid_mask, _stats = summarize_valid_pixels(
                values,
                invalid_values=invalid_values,
                special_pixel_abs_threshold=special_pixel_abs_threshold,
            )
            expanded_mask = expand_invalid_mask_for_radius(
                invalid_mask,
                invalid_pixel_radius=invalid_pixel_radius,
            )

            inner_mask = expanded_mask[inner_y, inner_x]
            total = int(actual_width * actual_height)
            invalid = int(inner_mask.sum())
            valid_counts[cell_y, cell_x] = total - invalid
            total_counts[cell_y, cell_x] = total

    return TileValidityIndex(
        dom_path=str(dom_path),
        image_width=image_width,
        image_height=image_height,
        cell_width=cell_width,
        cell_height=cell_height,
        grid_width=grid_width,
        grid_height=grid_height,
        valid_counts=valid_counts,
        total_counts=total_counts,
        uncertain=uncertain,
        manifest={str(k): v for k, v in manifest.items()},
    )


def ensure_dom_validity_index(
    *,
    cache_dir: str | Path,
    dom_path: str | Path,
    cube: ip.Cube,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    invalid_pixel_radius: int,
    cell_width: int,
    cell_height: int,
) -> tuple[TileValidityIndex, dict[str, object]]:
    resolved_cell_width = validate_tile_validity_cell_size(cell_width, field_name="tile_validity_cell_width")
    resolved_cell_height = validate_tile_validity_cell_size(cell_height, field_name="tile_validity_cell_height")

    manifest = _index_manifest(
        dom_path=dom_path,
        image_width=int(cube.sample_count()),
        image_height=int(cube.line_count()),
        band=int(band),
        invalid_values=tuple(float(value) for value in invalid_values),
        special_pixel_abs_threshold=float(special_pixel_abs_threshold),
        invalid_pixel_radius=int(invalid_pixel_radius),
        cell_width=resolved_cell_width,
        cell_height=resolved_cell_height,
    )
    cache_key = _cache_key_for_manifest(manifest)
    manifest_path, data_path = _cache_paths(cache_dir, cache_key)

    diagnostics: dict[str, object] = {
        "status": "unknown",
        "cache_key": cache_key,
        "manifest_path": str(manifest_path),
        "data_path": str(data_path),
        "cell_width": resolved_cell_width,
        "cell_height": resolved_cell_height,
    }

    if manifest_path.exists() and data_path.exists():
        try:
            index = _load_index_from_cache(manifest_path, data_path)
        except Exception as exc:  # noqa: BLE001
            diagnostics["cache_error"] = f"{type(exc).__name__}: {exc}"
        else:
            diagnostics["status"] = "hit"
            return index, diagnostics

    index = _build_index_from_open_cube(cube=cube, dom_path=dom_path, manifest=manifest)
    _save_index_to_cache(index, manifest_path, data_path)
    diagnostics["status"] = "rebuilt"
    return index, diagnostics
