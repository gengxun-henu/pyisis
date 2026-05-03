"""Reusable stereo-pair match visualization helpers for `image_match.py`.

Author: Geng Xun
Created: 2026-04-24
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from .keypoints import Keypoint, KeypointFile, read_key_file
from .runtime import bootstrap_runtime_environment
from .tile_matching import (
    _full_image_window,
    _prepare_image_for_sift,
    _read_cube_window,
    _resolved_invalid_values_for_cube,
)
from .tiling import TileWindow


bootstrap_runtime_environment()

import isis_pybind as ip

SUPPORTED_VISUALIZATION_MODES = ("auto", "full", "reduced", "cropped", "reduced_cropped")
SUPPORTED_MEMORY_PROFILES = ("high-memory", "balanced", "low-memory")
SUPPORTED_PREVIEW_CACHE_SOURCES = ("auto", "matching_cache", "visualization_cache", "disabled")
MEMORY_PROFILE_TARGET_LONG_EDGES = {
    "high-memory": 4096,
    "balanced": 2048,
    "low-memory": 1024,
}
DEFAULT_VISUALIZATION_MODE = "auto"
DEFAULT_MEMORY_PROFILE = "balanced"
DEFAULT_PREVIEW_CROP_MARGIN_PIXELS = 256
DEFAULT_PREVIEW_CACHE_SOURCE = "auto"


@dataclass(frozen=True, slots=True)
class VisualizationOptions:
    visualization_mode: str = DEFAULT_VISUALIZATION_MODE
    memory_profile: str = DEFAULT_MEMORY_PROFILE
    visualization_target_long_edge: int = MEMORY_PROFILE_TARGET_LONG_EDGES[DEFAULT_MEMORY_PROFILE]
    max_preview_pixels: int | None = None
    preview_crop_margin_pixels: int = DEFAULT_PREVIEW_CROP_MARGIN_PIXELS
    preview_cache_dir: Path | None = None
    preview_cache_source: str = DEFAULT_PREVIEW_CACHE_SOURCE
    preview_force_regenerate: bool = False
    preview_level: int | None = None


def _normalize_choice(value: str, *, field_name: str, supported: tuple[str, ...]) -> str:
    normalized = str(value).strip().lower().replace("_", "-")
    supported_lookup = {option.replace("_", "-"): option for option in supported}
    if normalized not in supported_lookup:
        raise ValueError(f"{field_name} must be one of {supported}; got {value!r}.")
    return supported_lookup[normalized]


def _positive_int(value: int, *, field_name: str) -> int:
    resolved = int(value)
    if resolved <= 0:
        raise ValueError(f"{field_name} must be positive.")
    return resolved


def _non_negative_int(value: int, *, field_name: str) -> int:
    resolved = int(value)
    if resolved < 0:
        raise ValueError(f"{field_name} must be >= 0.")
    return resolved


def resolve_visualization_options(
    *,
    visualization_mode: str = DEFAULT_VISUALIZATION_MODE,
    memory_profile: str = DEFAULT_MEMORY_PROFILE,
    visualization_target_long_edge: int | None = None,
    max_preview_pixels: int | None = None,
    preview_crop_margin_pixels: int = DEFAULT_PREVIEW_CROP_MARGIN_PIXELS,
    preview_cache_dir: str | Path | None = None,
    preview_cache_source: str = DEFAULT_PREVIEW_CACHE_SOURCE,
    preview_force_regenerate: bool = False,
    preview_level: int | None = None,
) -> VisualizationOptions:
    resolved_profile = _normalize_choice(
        memory_profile,
        field_name="memory_profile",
        supported=SUPPORTED_MEMORY_PROFILES,
    )
    resolved_mode = _normalize_choice(
        visualization_mode,
        field_name="visualization_mode",
        supported=SUPPORTED_VISUALIZATION_MODES,
    )
    resolved_cache_source = _normalize_choice(
        preview_cache_source,
        field_name="preview_cache_source",
        supported=SUPPORTED_PREVIEW_CACHE_SOURCES,
    )
    resolved_target = (
        _positive_int(visualization_target_long_edge, field_name="visualization_target_long_edge")
        if visualization_target_long_edge is not None
        else MEMORY_PROFILE_TARGET_LONG_EDGES[resolved_profile]
    )
    resolved_max_pixels = (
        None if max_preview_pixels is None else _positive_int(max_preview_pixels, field_name="max_preview_pixels")
    )
    resolved_preview_level = (
        None if preview_level is None else _non_negative_int(preview_level, field_name="preview_level")
    )
    return VisualizationOptions(
        visualization_mode=resolved_mode,
        memory_profile=resolved_profile,
        visualization_target_long_edge=resolved_target,
        max_preview_pixels=resolved_max_pixels,
        preview_crop_margin_pixels=_non_negative_int(
            preview_crop_margin_pixels,
            field_name="preview_crop_margin_pixels",
        ),
        preview_cache_dir=None if preview_cache_dir is None else Path(preview_cache_dir),
        preview_cache_source=resolved_cache_source,
        preview_force_regenerate=bool(preview_force_regenerate),
        preview_level=resolved_preview_level,
    )


def _cube_dimensions(cube_path: str | Path) -> tuple[int, int]:
    cube = ip.Cube()
    cube.open(str(cube_path), "r")
    try:
        return int(cube.sample_count()), int(cube.line_count())
    finally:
        if cube.is_open():
            cube.close()


def _auto_visualization_mode(
    *,
    image_width: int,
    image_height: int,
    options: VisualizationOptions,
    has_keypoints: bool,
) -> str:
    pixel_count = int(image_width) * int(image_height)
    if options.max_preview_pixels is not None and pixel_count > options.max_preview_pixels and has_keypoints:
        return "cropped"
    if max(image_width, image_height) > options.visualization_target_long_edge and has_keypoints:
        return "cropped"
    return "full"


def crop_window_for_keypoints(
    points: tuple[Keypoint, ...],
    *,
    image_width: int,
    image_height: int,
    margin_pixels: int,
) -> TileWindow:
    if not points:
        raise ValueError("At least one keypoint is required for cropped visualization.")
    resolved_width = _positive_int(image_width, field_name="image_width")
    resolved_height = _positive_int(image_height, field_name="image_height")
    margin = _non_negative_int(margin_pixels, field_name="margin_pixels")
    min_sample = min(point.sample - 1.0 for point in points)
    max_sample = max(point.sample - 1.0 for point in points)
    min_line = min(point.line - 1.0 for point in points)
    max_line = max(point.line - 1.0 for point in points)
    start_x = int(np.floor(min_sample)) - margin
    start_y = int(np.floor(min_line)) - margin
    end_x = int(np.ceil(max_sample)) + margin + 1
    end_y = int(np.ceil(max_line)) + margin + 1

    def clamp_window(start: int, end: int, limit: int) -> tuple[int, int]:
        if end <= 0:
            return 0, 1
        if start >= limit:
            return limit - 1, limit
        clamped_start = max(0, start)
        clamped_end = min(limit, end)
        if clamped_end <= clamped_start:
            clamped_end = min(limit, clamped_start + 1)
        return clamped_start, clamped_end

    start_x, end_x = clamp_window(start_x, end_x, resolved_width)
    start_y, end_y = clamp_window(start_y, end_y, resolved_height)
    return TileWindow(
        start_x=start_x,
        start_y=start_y,
        width=end_x - start_x,
        height=end_y - start_y,
    )


def _offset_keypoint_file(
    key_file: KeypointFile,
    *,
    start_x: int,
    start_y: int,
    width: int,
    height: int,
) -> KeypointFile:
    return KeypointFile(
        width,
        height,
        tuple(Keypoint(point.sample - start_x, point.line - start_y) for point in key_file.points),
    )


def default_match_visualization_path(
    left_image_path: str | Path,
    right_image_path: str | Path,
    output_directory: str | Path | None = None,
    *,
    timestamp: datetime | None = None,
) -> Path:
    resolved_timestamp = timestamp or datetime.now()
    filename = f"{Path(left_image_path).stem}__{Path(right_image_path).stem}__{resolved_timestamp.strftime('%Y%m%dT%H%M%S')}.png"
    if output_directory is None:
        return Path(filename)
    return Path(output_directory) / filename


def _isis_keypoint_to_draw_matches_keypoint(point: Keypoint, *, scale_factor: float) -> cv2.KeyPoint:
    return cv2.KeyPoint(
        float((point.sample - 1.0) * scale_factor),
        float((point.line - 1.0) * scale_factor),
        6.0,
    )


def _resize_visualization_image(image: np.ndarray, *, scale_factor: float) -> np.ndarray:
    interpolation = cv2.INTER_AREA if scale_factor < 1.0 else cv2.INTER_LINEAR
    return cv2.resize(image, dsize=None, fx=scale_factor, fy=scale_factor, interpolation=interpolation)


def _read_cube_as_stretched_byte(
    cube_path: str | Path,
    *,
    window: TileWindow | None = None,
    band: int = 1,
    minimum_value: float | None = None,
    maximum_value: float | None = None,
    lower_percent: float = 0.5,
    upper_percent: float = 99.5,
    invalid_values: tuple[float, ...] = (),
    special_pixel_abs_threshold: float = 1.0e300,
) -> np.ndarray:
    cube = ip.Cube()
    cube.open(str(cube_path), "r")
    try:
        resolved_invalid_values = _resolved_invalid_values_for_cube(cube, invalid_values)
        read_window = window if window is not None else _full_image_window(cube.sample_count(), cube.line_count())
        values = _read_cube_window(cube, read_window, band=band)
    finally:
        if cube.is_open():
            cube.close()

    stretched, _, _ = _prepare_image_for_sift(
        values,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        lower_percent=lower_percent,
        upper_percent=upper_percent,
        invalid_values=resolved_invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
    )
    return stretched


def write_stereo_pair_match_visualization(
    left_dom_path: str | Path,
    right_dom_path: str | Path,
    left_key_file: KeypointFile,
    right_key_file: KeypointFile,
    *,
    output_path: str | Path | None = None,
    output_directory: str | Path | None = None,
    timestamp: datetime | None = None,
    scale_factor: float = 1.0 / 3.0,
    band: int = 1,
    minimum_value: float | None = None,
    maximum_value: float | None = None,
    lower_percent: float = 0.5,
    upper_percent: float = 99.5,
    invalid_values: tuple[float, ...] = (),
    special_pixel_abs_threshold: float = 1.0e300,
    highlight_match_indices: list[int] | None = None,
    visualization_mode: str = "full",
    memory_profile: str = DEFAULT_MEMORY_PROFILE,
    visualization_target_long_edge: int | None = None,
    max_preview_pixels: int | None = None,
    preview_crop_margin_pixels: int = DEFAULT_PREVIEW_CROP_MARGIN_PIXELS,
    preview_cache_dir: str | Path | None = None,
    preview_cache_source: str = DEFAULT_PREVIEW_CACHE_SOURCE,
    preview_force_regenerate: bool = False,
    preview_level: int | None = None,
) -> dict[str, object]:
    if len(left_key_file.points) != len(right_key_file.points):
        raise ValueError("Left and right keypoint files must contain the same number of points for visualization.")
    if scale_factor <= 0.0:
        raise ValueError("scale_factor must be positive.")

    resolved_output_path = (
        Path(output_path)
        if output_path is not None
        else default_match_visualization_path(left_dom_path, right_dom_path, output_directory, timestamp=timestamp)
    )

    options = resolve_visualization_options(
        visualization_mode=visualization_mode,
        memory_profile=memory_profile,
        visualization_target_long_edge=visualization_target_long_edge,
        max_preview_pixels=max_preview_pixels,
        preview_crop_margin_pixels=preview_crop_margin_pixels,
        preview_cache_dir=preview_cache_dir,
        preview_cache_source=preview_cache_source,
        preview_force_regenerate=preview_force_regenerate,
        preview_level=preview_level,
    )
    if options.visualization_mode in {"reduced", "reduced_cropped"}:
        raise NotImplementedError(
            f"Visualization mode '{options.visualization_mode}' requires reduced previews (Task 5)."
        )
    left_width, left_height = _cube_dimensions(left_dom_path)
    right_width, right_height = _cube_dimensions(right_dom_path)
    mode_used = options.visualization_mode
    if mode_used == "auto":
        mode_used = _auto_visualization_mode(
            image_width=max(left_width, right_width),
            image_height=max(left_height, right_height),
            options=options,
            has_keypoints=bool(left_key_file.points),
        )
        if mode_used in {"reduced", "reduced_cropped"}:
            raise NotImplementedError(
                f"Visualization mode '{mode_used}' requires reduced previews (Task 5)."
            )

    left_window: TileWindow | None = None
    right_window: TileWindow | None = None
    left_render_key_file = left_key_file
    right_render_key_file = right_key_file
    if mode_used == "cropped":
        if left_key_file.points and right_key_file.points:
            left_window = crop_window_for_keypoints(
                left_key_file.points,
                image_width=left_width,
                image_height=left_height,
                margin_pixels=options.preview_crop_margin_pixels,
            )
            right_window = crop_window_for_keypoints(
                right_key_file.points,
                image_width=right_width,
                image_height=right_height,
                margin_pixels=options.preview_crop_margin_pixels,
            )
            left_render_key_file = _offset_keypoint_file(
                left_key_file,
                start_x=left_window.start_x,
                start_y=left_window.start_y,
                width=left_window.width,
                height=left_window.height,
            )
            right_render_key_file = _offset_keypoint_file(
                right_key_file,
                start_x=right_window.start_x,
                start_y=right_window.start_y,
                width=right_window.width,
                height=right_window.height,
            )
        else:
            mode_used = "full"

    left_image = _read_cube_as_stretched_byte(
        left_dom_path,
        window=left_window,
        band=band,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        lower_percent=lower_percent,
        upper_percent=upper_percent,
        invalid_values=invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
    )
    right_image = _read_cube_as_stretched_byte(
        right_dom_path,
        window=right_window,
        band=band,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        lower_percent=lower_percent,
        upper_percent=upper_percent,
        invalid_values=invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
    )

    scaled_left = _resize_visualization_image(left_image, scale_factor=scale_factor)
    scaled_right = _resize_visualization_image(right_image, scale_factor=scale_factor)
    left_keypoints = [
        _isis_keypoint_to_draw_matches_keypoint(point, scale_factor=scale_factor) for point in left_render_key_file.points
    ]
    right_keypoints = [
        _isis_keypoint_to_draw_matches_keypoint(point, scale_factor=scale_factor) for point in right_render_key_file.points
    ]
    matches = [cv2.DMatch(_queryIdx=index, _trainIdx=index, _distance=0.0) for index in range(len(left_keypoints))]

    rendered = cv2.drawMatches(
        scaled_left,
        left_keypoints,
        scaled_right,
        right_keypoints,
        matches,
        None,
        matchColor=(0, 220, 0),
        singlePointColor=(255, 80, 80),
        flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
    )

    if highlight_match_indices:
        left_panel_width = scaled_left.shape[1]
        for match_index in highlight_match_indices:
            if match_index < 0 or match_index >= len(left_keypoints):
                continue
            left_point = left_keypoints[match_index].pt
            right_point = right_keypoints[match_index].pt
            left_center = (int(round(left_point[0])), int(round(left_point[1])))
            right_center = (left_panel_width + int(round(right_point[0])), int(round(right_point[1])))
            cv2.circle(rendered, left_center, 8, (0, 165, 255), 2, cv2.LINE_AA)
            cv2.circle(rendered, right_center, 8, (0, 165, 255), 2, cv2.LINE_AA)

    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(resolved_output_path), rendered):
        raise IOError(f"Failed to write stereo-pair match visualization: {resolved_output_path}")

    preview_cache_source = "disabled" if mode_used in {"full", "cropped"} else options.preview_cache_source
    crop_window_payload = None
    if left_window is not None and right_window is not None:
        crop_window_payload = {
            "left": {
                "start_x": left_window.start_x,
                "start_y": left_window.start_y,
                "width": left_window.width,
                "height": left_window.height,
            },
            "right": {
                "start_x": right_window.start_x,
                "start_y": right_window.start_y,
                "width": right_window.width,
                "height": right_window.height,
            },
        }

    return {
        "output_path": str(resolved_output_path),
        "point_count": len(left_keypoints),
        "scale_factor": float(scale_factor),
        "highlighted_match_count": 0 if highlight_match_indices is None else len(highlight_match_indices),
        "left_dom": str(left_dom_path),
        "right_dom": str(right_dom_path),
        "visualization_mode_requested": options.visualization_mode,
        "visualization_mode_used": mode_used,
        "memory_profile": options.memory_profile,
        "preview_level": options.preview_level,
        "preview_cache_hit": False,
        "preview_cache_source": preview_cache_source,
        "preview_dimensions": {
            "left": [left_image.shape[1], left_image.shape[0]],
            "right": [right_image.shape[1], right_image.shape[0]],
        },
        "crop_window": crop_window_payload,
        "source_scale_factor": 1.0,
    }


def write_stereo_pair_match_visualization_from_key_files(
    left_dom_path: str | Path,
    right_dom_path: str | Path,
    left_key_path: str | Path,
    right_key_path: str | Path,
    **kwargs,
) -> dict[str, object]:
    left_key_file = read_key_file(left_key_path)
    right_key_file = read_key_file(right_key_path)
    result = write_stereo_pair_match_visualization(
        left_dom_path,
        right_dom_path,
        left_key_file,
        right_key_file,
        **kwargs,
    )
    return {
        **result,
        "left_key_path": str(left_key_path),
        "right_key_path": str(right_key_path),
    }


__all__ = [
    "crop_window_for_keypoints",
    "default_match_visualization_path",
    "write_stereo_pair_match_visualization",
    "write_stereo_pair_match_visualization_from_key_files",
]
