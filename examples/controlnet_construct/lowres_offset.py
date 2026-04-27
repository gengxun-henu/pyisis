"""Reusable low-resolution offset-estimation helpers for `image_match.py`.

Author: Geng Xun
Created: 2026-04-24
Updated: 2026-04-24  Geng Xun made low-resolution projected-offset trimmed-mean fraction configurable while preserving the previous 5% default.
Updated: 2026-04-26  Geng Xun added low-resolution homography reprojection-error gating so coarse offsets fall back to zero when the retained match geometry is not trustworthy.
Updated: 2026-04-27  Geng Xun added minimum retained-match and projected-offset magnitude gates so weak or implausible low-resolution estimates fall back to zero.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import time
from typing import Callable

import cv2
import numpy as np

from .keypoints import Keypoint, KeypointFile, write_key_file
from .runtime import bootstrap_runtime_environment


bootstrap_runtime_environment()

import isis_pybind as ip


DEFAULT_TRIM_FRACTION_EACH_SIDE = 0.05
DEFAULT_MIN_RETAINED_MATCH_COUNT = 5
DEFAULT_MAX_MEAN_PROJECTED_OFFSET_METERS = 0.0


def _low_resolution_pair_tag(left_dom_path: str | Path, right_dom_path: str | Path) -> str:
    return f"{Path(left_dom_path).stem}__{Path(right_dom_path).stem}"


def _default_low_resolution_output_dir(
    left_dom_path: str | Path,
    right_dom_path: str | Path,
    *,
    metadata_output: str | Path | None = None,
    left_output_key: str | Path | None = None,
) -> Path:
    pair_tag = _low_resolution_pair_tag(left_dom_path, right_dom_path)
    if metadata_output is not None:
        root = Path(metadata_output).parent
    elif left_output_key is not None:
        root = Path(left_output_key).parent
    else:
        root = Path.cwd()
    return root / "low_resolution" / pair_tag


def _require_command(command_name: str) -> None:
    if shutil.which(command_name) is None:
        raise RuntimeError(f"Required command not found: {command_name}")


def _run_command(command: list[str]) -> None:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({' '.join(command)}): {completed.stderr.strip() or completed.stdout.strip()}"
        )


def _validate_projection_ready_cube(cube_path: str | Path) -> float:
    cube = ip.Cube()
    cube.open(str(cube_path), "r")
    try:
        projection = cube.projection()
        resolution = float(projection.resolution())
        if not np.isfinite(resolution) or resolution <= 0.0:
            raise RuntimeError(
                f"Projection resolution must be positive and finite for {cube_path}; got {resolution!r}."
            )
        return resolution
    except Exception as exc:
        raise RuntimeError(
            f"Low-resolution ISIS cube is not projection-ready: {cube_path}: {exc}"
        ) from exc
    finally:
        if cube.is_open():
            cube.close()


def create_low_resolution_dom(
    source_path: str | Path,
    output_path: str | Path,
    *,
    level: int,
    run_command_func: Callable[[list[str]], None] = _run_command,
    validate_projection_ready_cube_func: Callable[[str | Path], float] = _validate_projection_ready_cube,
) -> Path:
    resolved_level = int(level)
    if resolved_level < 0:
        raise ValueError("low_resolution_level must be >= 0.")

    resolved_source_path = Path(source_path)
    resolved_output_path = Path(output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    if resolved_output_path.exists():
        resolved_output_path.unlink()

    if resolved_level == 0:
        shutil.copyfile(resolved_source_path, resolved_output_path)
        validate_projection_ready_cube_func(resolved_output_path)
        return resolved_output_path

    scale_divisor = 2 ** resolved_level
    run_command_func(
        [
            "reduce",
            f"from={resolved_source_path}",
            f"to={resolved_output_path}",
            "mode=scale",
            f"sscale={scale_divisor}",
            f"lscale={scale_divisor}",
            "algorithm=AVERAGE",
        ]
    )
    validate_projection_ready_cube_func(resolved_output_path)
    return resolved_output_path


def _projected_xy_from_keypoints_in_open_cube(
    cube: ip.Cube,
    cube_path: str | Path,
    points: tuple[Keypoint, ...],
) -> tuple[tuple[float, float], ...]:
    projection = cube.projection()
    projected_coordinates: list[tuple[float, float]] = []
    for point in points:
        if not projection.set_world(point.sample, point.line):
            raise RuntimeError(
                f"Failed to convert keypoint sample/line to projected coordinates for {cube_path}: "
                f"({point.sample}, {point.line})"
            )
        projected_coordinates.append((float(projection.x_coord()), float(projection.y_coord())))
    return tuple(projected_coordinates)


def _projected_xy_from_keypoints(cube_path: str | Path, points: tuple[Keypoint, ...]) -> tuple[tuple[float, float], ...]:
    cube = ip.Cube()
    cube.open(str(cube_path), "r")
    try:
        return _projected_xy_from_keypoints_in_open_cube(cube, cube_path, points)
    finally:
        if cube.is_open():
            cube.close()


def _projected_xy_from_keypoint(cube_path: str | Path, point: Keypoint) -> tuple[float, float]:
    return _projected_xy_from_keypoints(cube_path, (point,))[0]


def _validate_trim_fraction_each_side(trim_fraction_each_side: float) -> float:
    resolved_value = float(trim_fraction_each_side)
    if not (0.0 <= resolved_value < 0.5):
        raise ValueError("trim_fraction_each_side must be within [0.0, 0.5).")
    return resolved_value


def _validate_min_retained_match_count(min_retained_match_count: int) -> int:
    resolved_value = int(min_retained_match_count)
    if resolved_value < 1:
        raise ValueError("low_resolution_min_retained_match_count must be >= 1.")
    return resolved_value


def _validate_max_mean_projected_offset_meters(max_mean_projected_offset_meters: float) -> float:
    resolved_value = float(max_mean_projected_offset_meters)
    if resolved_value < 0.0:
        raise ValueError("low_resolution_max_mean_projected_offset_meters must be >= 0.0.")
    return resolved_value


def _trimmed_mean(
    values: list[float],
    *,
    trim_ratio: float = DEFAULT_TRIM_FRACTION_EACH_SIDE,
) -> float:
    if not values:
        raise ValueError("Cannot compute a trimmed mean from an empty sample set.")
    resolved_trim_ratio = _validate_trim_fraction_each_side(trim_ratio)
    sorted_values = sorted(float(value) for value in values)
    trim_count = int(len(sorted_values) * resolved_trim_ratio)
    if trim_count * 2 >= len(sorted_values):
        trimmed_values = sorted_values
    else:
        trimmed_values = sorted_values[trim_count: len(sorted_values) - trim_count]
    return float(sum(trimmed_values) / len(trimmed_values))


def _compute_reprojection_errors(
    left_points: tuple[Keypoint, ...],
    right_points: tuple[Keypoint, ...],
    *,
    homography_matrix: list[list[float]],
) -> list[float]:
    if len(left_points) != len(right_points):
        raise ValueError("Left and right keypoint tuples must contain the same number of points.")
    if len(left_points) < 1:
        raise ValueError("At least one retained point is required to compute reprojection errors.")

    left_coordinates = np.asarray(
        [(point.sample, point.line) for point in left_points],
        dtype=np.float32,
    ).reshape(-1, 1, 2)
    right_coordinates = np.asarray(
        [(point.sample, point.line) for point in right_points],
        dtype=np.float32,
    ).reshape(-1, 2)
    projected_right_coordinates = cv2.perspectiveTransform(
        left_coordinates,
        np.asarray(homography_matrix, dtype=np.float64),
    ).reshape(-1, 2)
    return [
        float(np.linalg.norm(projected - actual))
        for projected, actual in zip(projected_right_coordinates, right_coordinates, strict=True)
    ]


def estimate_low_resolution_projected_offset(
    left_dom_path: str | Path,
    right_dom_path: str | Path,
    *,
    enabled: bool,
    low_resolution_level: int,
    low_resolution_output_dir: str | Path,
    band: int,
    minimum_value: float | None,
    maximum_value: float | None,
    lower_percent: float,
    upper_percent: float,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    min_valid_pixels: int,
    valid_pixel_percent_threshold: float,
    invalid_pixel_radius: int,
    matcher_method: str,
    ratio_test: float,
    max_features: int | None,
    sift_octave_layers: int,
    sift_contrast_threshold: float,
    sift_edge_threshold: float,
    sift_sigma: float,
    trim_fraction_each_side: float = DEFAULT_TRIM_FRACTION_EACH_SIDE,
    low_resolution_max_mean_reprojection_error_pixels: float = 3.0,
    low_resolution_min_retained_match_count: int = DEFAULT_MIN_RETAINED_MATCH_COUNT,
    low_resolution_max_mean_projected_offset_meters: float = DEFAULT_MAX_MEAN_PROJECTED_OFFSET_METERS,
    match_dom_pair_func: Callable[..., tuple[KeypointFile, KeypointFile, dict[str, object]]],
    filter_stereo_pair_keypoints_with_ransac_func: Callable[..., tuple[KeypointFile, KeypointFile, dict[str, object]]],
    write_stereo_pair_match_visualization_func: Callable[..., dict[str, object]],
    require_command_func: Callable[[str], None] = _require_command,
    create_low_resolution_dom_func: Callable[..., Path] = create_low_resolution_dom,
) -> dict[str, object]:
    resolved_trim_fraction_each_side = _validate_trim_fraction_each_side(trim_fraction_each_side)
    resolved_max_mean_reprojection_error_pixels = float(low_resolution_max_mean_reprojection_error_pixels)
    if resolved_max_mean_reprojection_error_pixels < 0.0:
        raise ValueError("low_resolution_max_mean_reprojection_error_pixels must be >= 0.0.")
    resolved_min_retained_match_count = _validate_min_retained_match_count(low_resolution_min_retained_match_count)
    resolved_max_mean_projected_offset_meters = _validate_max_mean_projected_offset_meters(
        low_resolution_max_mean_projected_offset_meters
    )
    summary_thresholds = {
        "trim_fraction_each_side": resolved_trim_fraction_each_side,
        "max_mean_reprojection_error_pixels": resolved_max_mean_reprojection_error_pixels,
        "min_retained_match_count": resolved_min_retained_match_count,
        "max_mean_projected_offset_meters": resolved_max_mean_projected_offset_meters,
    }
    if not enabled:
        return {
            "enabled": False,
            "status": "disabled",
            "fallback_offset_zero": False,
            "reason": "Low-resolution offset estimation is disabled.",
            "failure_reason_code": None,
            "delta_x_projected": 0.0,
            "delta_y_projected": 0.0,
            "retained_match_count": 0,
            **summary_thresholds,
            "trimmed_mean_reprojection_error_pixels": None,
            "mean_projected_offset_meters": None,
            "reprojection_error_pixel_samples": [],
        }

    resolved_level = int(low_resolution_level)
    if resolved_level < 0:
        raise ValueError("low_resolution_level must be >= 0.")

    resolved_output_dir = Path(low_resolution_output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    pair_tag = _low_resolution_pair_tag(left_dom_path, right_dom_path)
    started_at = time.perf_counter()
    try:
        require_command_func("reduce")

        left_low_res_dom = create_low_resolution_dom_func(
            left_dom_path,
            resolved_output_dir / f"{Path(left_dom_path).stem}__level{resolved_level}.cub",
            level=resolved_level,
        )
        right_low_res_dom = create_low_resolution_dom_func(
            right_dom_path,
            resolved_output_dir / f"{Path(right_dom_path).stem}__level{resolved_level}.cub",
            level=resolved_level,
        )

        raw_left_key, raw_right_key, raw_summary = match_dom_pair_func(
            left_low_res_dom,
            right_low_res_dom,
            band=band,
            max_image_dimension=10**9,
            block_width=10**9,
            block_height=10**9,
            overlap_x=0,
            overlap_y=0,
            minimum_value=minimum_value,
            maximum_value=maximum_value,
            lower_percent=lower_percent,
            upper_percent=upper_percent,
            invalid_values=invalid_values,
            special_pixel_abs_threshold=special_pixel_abs_threshold,
            min_valid_pixels=min_valid_pixels,
            valid_pixel_percent_threshold=valid_pixel_percent_threshold,
            invalid_pixel_radius=invalid_pixel_radius,
            matcher_method=matcher_method,
            ratio_test=ratio_test,
            max_features=max_features,
            sift_octave_layers=sift_octave_layers,
            sift_contrast_threshold=sift_contrast_threshold,
            sift_edge_threshold=sift_edge_threshold,
            sift_sigma=sift_sigma,
            crop_expand_pixels=0,
            min_overlap_size=1,
            use_parallel_cpu=False,
            num_worker_parallel_cpu=1,
            enable_low_resolution_offset_estimation=False,
            low_resolution_level=resolved_level,
        )

        raw_left_key_path = resolved_output_dir / f"{pair_tag}_low_resolution_raw_A.key"
        raw_right_key_path = resolved_output_dir / f"{pair_tag}_low_resolution_raw_B.key"
        write_key_file(raw_left_key_path, raw_left_key)
        write_key_file(raw_right_key_path, raw_right_key)

        filtered_left_key, filtered_right_key, ransac_summary = filter_stereo_pair_keypoints_with_ransac_func(
            raw_left_key,
            raw_right_key,
        )
        filtered_left_key_path = resolved_output_dir / f"{pair_tag}_low_resolution_A.key"
        filtered_right_key_path = resolved_output_dir / f"{pair_tag}_low_resolution_B.key"
        write_key_file(filtered_left_key_path, filtered_left_key)
        write_key_file(filtered_right_key_path, filtered_right_key)

        retained_match_count = len(filtered_left_key.points)
        if retained_match_count <= 0:
            elapsed_seconds = time.perf_counter() - started_at
            return {
                "enabled": True,
                "status": "fallback_zero",
                "fallback_offset_zero": True,
                "reason": "Low-resolution matching produced no retained RANSAC inliers.",
                "failure_reason_code": "no_matches",
                "delta_x_projected": 0.0,
                "delta_y_projected": 0.0,
                "retained_match_count": 0,
                **summary_thresholds,
                "trimmed_mean_reprojection_error_pixels": None,
                "mean_projected_offset_meters": None,
                "reprojection_error_pixel_samples": [],
                "low_resolution_level": resolved_level,
                "left_low_resolution_dom": str(left_low_res_dom),
                "right_low_resolution_dom": str(right_low_res_dom),
                "elapsed_seconds": elapsed_seconds,
                "image_match_summary": raw_summary,
                "ransac_summary": ransac_summary,
            }

        if retained_match_count < resolved_min_retained_match_count:
            elapsed_seconds = time.perf_counter() - started_at
            return {
                "enabled": True,
                "status": "fallback_zero",
                "fallback_offset_zero": True,
                "reason": (
                    "Low-resolution retained match count is below the configured minimum; "
                    "ignoring coarse offset statistics and falling back to zero."
                ),
                "failure_reason_code": "retained_match_count_below_threshold",
                "delta_x_projected": 0.0,
                "delta_y_projected": 0.0,
                "retained_match_count": retained_match_count,
                **summary_thresholds,
                "trimmed_mean_reprojection_error_pixels": None,
                "mean_projected_offset_meters": None,
                "reprojection_error_pixel_samples": [],
                "low_resolution_level": resolved_level,
                "left_low_resolution_dom": str(left_low_res_dom),
                "right_low_resolution_dom": str(right_low_res_dom),
                "raw_left_key": str(raw_left_key_path),
                "raw_right_key": str(raw_right_key_path),
                "filtered_left_key": str(filtered_left_key_path),
                "filtered_right_key": str(filtered_right_key_path),
                "elapsed_seconds": elapsed_seconds,
                "image_match_summary": raw_summary,
                "ransac_summary": ransac_summary,
            }

        if not ransac_summary.get("applied", False):
            failure_reason_code = "homography_failed"
            if ransac_summary.get("status") == "skipped_insufficient_points":
                failure_reason_code = "insufficient_points_for_homography"
            elapsed_seconds = time.perf_counter() - started_at
            return {
                "enabled": True,
                "status": "fallback_zero",
                "fallback_offset_zero": True,
                "reason": "Low-resolution matching retained points, but homography-based reliability gating could not be applied.",
                "failure_reason_code": failure_reason_code,
                "delta_x_projected": 0.0,
                "delta_y_projected": 0.0,
                "retained_match_count": retained_match_count,
                **summary_thresholds,
                "trimmed_mean_reprojection_error_pixels": None,
                "mean_projected_offset_meters": None,
                "reprojection_error_pixel_samples": [],
                "low_resolution_level": resolved_level,
                "left_low_resolution_dom": str(left_low_res_dom),
                "right_low_resolution_dom": str(right_low_res_dom),
                "raw_left_key": str(raw_left_key_path),
                "raw_right_key": str(raw_right_key_path),
                "filtered_left_key": str(filtered_left_key_path),
                "filtered_right_key": str(filtered_right_key_path),
                "elapsed_seconds": elapsed_seconds,
                "image_match_summary": raw_summary,
                "ransac_summary": ransac_summary,
            }

        homography_matrix = ransac_summary.get("homography_matrix")
        if homography_matrix is None:
            elapsed_seconds = time.perf_counter() - started_at
            return {
                "enabled": True,
                "status": "fallback_zero",
                "fallback_offset_zero": True,
                "reason": "Low-resolution homography matrix is unavailable after RANSAC filtering.",
                "failure_reason_code": "homography_failed",
                "delta_x_projected": 0.0,
                "delta_y_projected": 0.0,
                "retained_match_count": retained_match_count,
                **summary_thresholds,
                "trimmed_mean_reprojection_error_pixels": None,
                "mean_projected_offset_meters": None,
                "reprojection_error_pixel_samples": [],
                "low_resolution_level": resolved_level,
                "left_low_resolution_dom": str(left_low_res_dom),
                "right_low_resolution_dom": str(right_low_res_dom),
                "raw_left_key": str(raw_left_key_path),
                "raw_right_key": str(raw_right_key_path),
                "filtered_left_key": str(filtered_left_key_path),
                "filtered_right_key": str(filtered_right_key_path),
                "elapsed_seconds": elapsed_seconds,
                "image_match_summary": raw_summary,
                "ransac_summary": ransac_summary,
            }

        reprojection_error_pixel_samples = _compute_reprojection_errors(
            filtered_left_key.points,
            filtered_right_key.points,
            homography_matrix=homography_matrix,
        )
        trimmed_mean_reprojection_error_pixels = _trimmed_mean(
            reprojection_error_pixel_samples,
            trim_ratio=resolved_trim_fraction_each_side,
        )
        if trimmed_mean_reprojection_error_pixels > resolved_max_mean_reprojection_error_pixels:
            elapsed_seconds = time.perf_counter() - started_at
            return {
                "enabled": True,
                "status": "fallback_zero",
                "fallback_offset_zero": True,
                "reason": (
                    "Low-resolution reprojection error exceeded the configured threshold; "
                    "ignoring coarse projected offset and falling back to zero."
                ),
                "failure_reason_code": "reprojection_error_above_threshold",
                "delta_x_projected": 0.0,
                "delta_y_projected": 0.0,
                "retained_match_count": retained_match_count,
                **summary_thresholds,
                "trimmed_mean_reprojection_error_pixels": trimmed_mean_reprojection_error_pixels,
                "mean_projected_offset_meters": None,
                "reprojection_error_pixel_samples": reprojection_error_pixel_samples,
                "low_resolution_level": resolved_level,
                "left_low_resolution_dom": str(left_low_res_dom),
                "right_low_resolution_dom": str(right_low_res_dom),
                "raw_left_key": str(raw_left_key_path),
                "raw_right_key": str(raw_right_key_path),
                "filtered_left_key": str(filtered_left_key_path),
                "filtered_right_key": str(filtered_right_key_path),
                "elapsed_seconds": elapsed_seconds,
                "image_match_summary": raw_summary,
                "ransac_summary": ransac_summary,
            }

        left_low_res_cube = ip.Cube()
        right_low_res_cube = ip.Cube()
        left_low_res_cube.open(str(left_low_res_dom), "r")
        right_low_res_cube.open(str(right_low_res_dom), "r")
        try:
            left_projected_points = _projected_xy_from_keypoints_in_open_cube(
                left_low_res_cube,
                left_low_res_dom,
                filtered_left_key.points,
            )
            right_projected_points = _projected_xy_from_keypoints_in_open_cube(
                right_low_res_cube,
                right_low_res_dom,
                filtered_right_key.points,
            )
        finally:
            if left_low_res_cube.is_open():
                left_low_res_cube.close()
            if right_low_res_cube.is_open():
                right_low_res_cube.close()

        delta_x_values = [
            right_x - left_x
            for (left_x, _left_y), (right_x, _right_y) in zip(left_projected_points, right_projected_points, strict=True)
        ]
        delta_y_values = [
            right_y - left_y
            for (_left_x, left_y), (_right_x, right_y) in zip(left_projected_points, right_projected_points, strict=True)
        ]

        delta_x_projected = _trimmed_mean(
            delta_x_values,
            trim_ratio=resolved_trim_fraction_each_side,
        )
        delta_y_projected = _trimmed_mean(
            delta_y_values,
            trim_ratio=resolved_trim_fraction_each_side,
        )
        mean_projected_offset_meters = float(np.hypot(delta_x_projected, delta_y_projected))
        if (
            resolved_max_mean_projected_offset_meters > 0.0
            and mean_projected_offset_meters > resolved_max_mean_projected_offset_meters
        ):
            elapsed_seconds = time.perf_counter() - started_at
            return {
                "enabled": True,
                "status": "fallback_zero",
                "fallback_offset_zero": True,
                "reason": (
                    "Low-resolution mean projected offset exceeded the configured threshold in meters; "
                    "ignoring coarse projected offset and falling back to zero."
                ),
                "failure_reason_code": "mean_projected_offset_above_threshold",
                "delta_x_projected": 0.0,
                "delta_y_projected": 0.0,
                "retained_match_count": retained_match_count,
                **summary_thresholds,
                "trimmed_mean_reprojection_error_pixels": trimmed_mean_reprojection_error_pixels,
                "mean_projected_offset_meters": mean_projected_offset_meters,
                "reprojection_error_pixel_samples": reprojection_error_pixel_samples,
                "low_resolution_level": resolved_level,
                "left_low_resolution_dom": str(left_low_res_dom),
                "right_low_resolution_dom": str(right_low_res_dom),
                "raw_left_key": str(raw_left_key_path),
                "raw_right_key": str(raw_right_key_path),
                "filtered_left_key": str(filtered_left_key_path),
                "filtered_right_key": str(filtered_right_key_path),
                "elapsed_seconds": elapsed_seconds,
                "image_match_summary": raw_summary,
                "ransac_summary": ransac_summary,
            }
        visualization_result = write_stereo_pair_match_visualization_func(
            left_low_res_dom,
            right_low_res_dom,
            filtered_left_key,
            filtered_right_key,
            output_path=resolved_output_dir / f"{pair_tag}_low_resolution_ransac.png",
            band=band,
            minimum_value=minimum_value,
            maximum_value=maximum_value,
            lower_percent=lower_percent,
            upper_percent=upper_percent,
            invalid_values=invalid_values,
            special_pixel_abs_threshold=special_pixel_abs_threshold,
        )
        elapsed_seconds = time.perf_counter() - started_at
        return {
            "enabled": True,
            "status": "succeeded",
            "fallback_offset_zero": False,
            "reason": "Low-resolution projected offset estimated successfully.",
            "failure_reason_code": None,
            "delta_x_projected": float(delta_x_projected),
            "delta_y_projected": float(delta_y_projected),
            "retained_match_count": retained_match_count,
            "low_resolution_level": resolved_level,
            "left_low_resolution_dom": str(left_low_res_dom),
            "right_low_resolution_dom": str(right_low_res_dom),
            "raw_left_key": str(raw_left_key_path),
            "raw_right_key": str(raw_right_key_path),
            "filtered_left_key": str(filtered_left_key_path),
            "filtered_right_key": str(filtered_right_key_path),
            "elapsed_seconds": elapsed_seconds,
            "histogram_bin_count": 100,
            **summary_thresholds,
            "trimmed_mean_reprojection_error_pixels": trimmed_mean_reprojection_error_pixels,
            "mean_projected_offset_meters": mean_projected_offset_meters,
            "reprojection_error_pixel_samples": reprojection_error_pixel_samples,
            "image_match_summary": raw_summary,
            "ransac_summary": ransac_summary,
            "match_visualization": visualization_result,
        }
    except Exception as exc:
        elapsed_seconds = time.perf_counter() - started_at
        return {
            "enabled": True,
            "status": "fallback_zero",
            "fallback_offset_zero": True,
            "reason": str(exc),
            "failure_reason_code": "other_runtime_failure",
            "delta_x_projected": 0.0,
            "delta_y_projected": 0.0,
            "retained_match_count": 0,
            **summary_thresholds,
            "trimmed_mean_reprojection_error_pixels": None,
            "mean_projected_offset_meters": None,
            "reprojection_error_pixel_samples": [],
            "low_resolution_level": resolved_level,
            "elapsed_seconds": elapsed_seconds,
        }


__all__ = [
    "_default_low_resolution_output_dir",
    "_compute_reprojection_errors",
    "_low_resolution_pair_tag",
    "_projected_xy_from_keypoint",
    "_projected_xy_from_keypoints",
    "_projected_xy_from_keypoints_in_open_cube",
    "_require_command",
    "_run_command",
    "_trimmed_mean",
    "_validate_max_mean_projected_offset_meters",
    "_validate_min_retained_match_count",
    "_validate_trim_fraction_each_side",
    "_validate_projection_ready_cube",
    "DEFAULT_MAX_MEAN_PROJECTED_OFFSET_METERS",
    "DEFAULT_MIN_RETAINED_MATCH_COUNT",
    "DEFAULT_TRIM_FRACTION_EACH_SIDE",
    "create_low_resolution_dom",
    "estimate_low_resolution_projected_offset",
]
