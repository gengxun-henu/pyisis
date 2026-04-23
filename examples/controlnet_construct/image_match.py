"""Match DOM cube pairs with OpenCV SIFT and write DOM-space `.key` files.

Author: Geng Xun
Created: 2026-04-16
Updated: 2026-04-16  Geng Xun added the initial DOM-space SIFT matching CLI with block matching, grayscale stretch, invalid-value masking, and `.key` export.
Updated: 2026-04-17  Geng Xun allowed tiled DOM matching to operate on the shared raster extent when paired DOM cubes differ slightly in size.
Updated: 2026-04-17  Geng Xun upgraded DOM matching to use projected-overlap crop metadata with configurable expansion and small-overlap skipping.
Updated: 2026-04-17  Geng Xun exposed additional OpenCV SIFT detector parameters through the matching API and CLI.
Updated: 2026-04-18  Geng Xun added merge-stage homography RANSAC helpers and default `cv2.drawMatches` visualization output for preserved DOM matching diagnostics.
Updated: 2026-04-18  Geng Xun changed match-visualization default scaling to one-third size and now use area interpolation when downsampling previews.
Updated: 2026-04-19  Geng Xun moved default match-visualization output into the image-match stage so users get PNG diagnostics by default while still being able to disable them explicitly.
Updated: 2026-04-22  Geng Xun added default CPU process-pool tile matching with opt-out CLI flags while preserving the existing serial code path and summary diagnostics.
Updated: 2026-04-22  Geng Xun extended match_metadata JSON sidecars to persist image-match execution diagnostics including whether CPU parallelism was actually used and how many workers were selected.
Updated: 2026-04-22  Geng Xun added a configurable --num-worker-parallel-cpu worker cap for process-pool tile matching and persisted the requested worker setting alongside actual runtime diagnostics.
Updated: 2026-04-22  Geng Xun standardized the public image-match CLI on kebab-case flags and removed legacy underscore spellings.
Updated: 2026-04-22  Geng Xun added optional --config JSON loading so image_match.py and the example batch wrappers can share ImageMatch defaults from the same configuration file.
Updated: 2026-04-23  Geng Xun batched low-resolution projected keypoint conversion so repeated offset estimation reuses opened cubes and projection objects instead of reopening the same DOM for every point.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
import json
import multiprocessing as mp
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import cv2
import numpy as np


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.dom_prepare import prepare_dom_pair_for_matching, write_pair_preparation_metadata
    from controlnet_construct.keypoints import Keypoint, KeypointFile, read_key_file, write_key_file
    from controlnet_construct.preprocess import (
        StretchStats,
        expand_invalid_mask_for_radius,
        summarize_valid_pixels,
        stretch_to_byte,
        validate_invalid_pixel_radius,
    )
    from controlnet_construct.runtime import bootstrap_runtime_environment
    from controlnet_construct.tiling import TileWindow, generate_tiles, requires_tiling
else:
    from .dom_prepare import prepare_dom_pair_for_matching, write_pair_preparation_metadata
    from .keypoints import Keypoint, KeypointFile, read_key_file, write_key_file
    from .preprocess import (
        StretchStats,
        expand_invalid_mask_for_radius,
        summarize_valid_pixels,
        stretch_to_byte,
        validate_invalid_pixel_radius,
    )
    from .runtime import bootstrap_runtime_environment
    from .tiling import TileWindow, generate_tiles, requires_tiling


bootstrap_runtime_environment()

import isis_pybind as ip


DEFAULT_NUM_WORKER_PARALLEL_CPU = 8
MAX_NUM_WORKER_PARALLEL_CPU = 4096
DEFAULT_LOW_RESOLUTION_LEVEL = 3


@dataclass(frozen=True, slots=True)
class TileMatchStats:
    local_start_x: int
    local_start_y: int
    width: int
    height: int
    left_start_x: int
    left_start_y: int
    right_start_x: int
    right_start_y: int
    left_valid_pixel_count: int
    right_valid_pixel_count: int
    left_valid_pixel_ratio: float
    right_valid_pixel_ratio: float
    left_feature_count: int
    right_feature_count: int
    match_count: int
    status: str


@dataclass(frozen=True, slots=True)
class PairedTileWindow:
    local_window: TileWindow
    left_window: TileWindow
    right_window: TileWindow


@dataclass(frozen=True, slots=True)
class TileMatchTask:
    left_dom_path: str
    right_dom_path: str
    band: int
    paired_window: PairedTileWindow
    minimum_value: float | None
    maximum_value: float | None
    lower_percent: float
    upper_percent: float
    invalid_values: tuple[float, ...]
    special_pixel_abs_threshold: float
    min_valid_pixels: int
    valid_pixel_percent_threshold: float
    invalid_pixel_radius: int
    ratio_test: float
    max_features: int | None
    sift_octave_layers: int
    sift_contrast_threshold: float
    sift_edge_threshold: float
    sift_sigma: float


@dataclass(frozen=True, slots=True)
class TileMatchResult:
    stats: TileMatchStats
    left_points: tuple[Keypoint, ...]
    right_points: tuple[Keypoint, ...]


def _normalize_ransac_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in {"strict", "loose"}:
        raise ValueError(f"Unsupported RANSAC mode {mode!r}. Expected 'strict' or 'loose'.")
    return normalized


def _validate_valid_pixel_percent_threshold(threshold: float) -> float:
    if not (0.0 <= float(threshold) <= 1.0):
        raise ValueError(
            "valid_pixel_percent_threshold must be within [0.0, 1.0]."
        )
    return float(threshold)


def _parse_valid_pixel_percent_threshold(value: str) -> float:
    try:
        return _validate_valid_pixel_percent_threshold(float(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _validate_num_worker_parallel_cpu(value: int) -> int:
    resolved_value = int(value)
    if not (1 <= resolved_value <= MAX_NUM_WORKER_PARALLEL_CPU):
        raise ValueError(
            f"num_worker_parallel_cpu must be within [1, {MAX_NUM_WORKER_PARALLEL_CPU}]."
        )
    return resolved_value


def _parse_num_worker_parallel_cpu(value: str) -> int:
    try:
        return _validate_num_worker_parallel_cpu(int(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _validate_low_resolution_level(value: int) -> int:
    resolved_value = int(value)
    if resolved_value < 0:
        raise ValueError("low_resolution_level must be >= 0.")
    return resolved_value


def _parse_low_resolution_level(value: str) -> int:
    try:
        return _validate_low_resolution_level(int(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_invalid_pixel_radius(value: str) -> int:
    try:
        return validate_invalid_pixel_radius(int(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _image_match_config_containers(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        raise ValueError("image_match config JSON must decode to an object at the top level.")

    containers: list[dict[str, object]] = []
    for key in ("ImageMatch", "image_match", "imageMatch"):
        value = payload.get(key)
        if isinstance(value, dict):
            containers.append(value)
    containers.append(payload)
    return containers


def _first_present_config_value(
    containers: list[dict[str, object]],
    candidate_keys: tuple[str, ...],
) -> object | None:
    for container in containers:
        for key in candidate_keys:
            if key not in container:
                continue
            value = container[key]
            if value is None:
                continue
            if isinstance(value, str) and value == "":
                continue
            return value
    return None


def _coerce_config_bool(value: object, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"{field_name} in config JSON must be a boolean-compatible value.")


def _coerce_invalid_value_list(value: object) -> list[float]:
    if isinstance(value, (list, tuple)):
        return [float(item) for item in value]
    return [float(value)]


def load_image_match_defaults_from_config(config_path: str | Path) -> dict[str, object]:
    resolved_path = Path(config_path)
    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Config JSON not found: {resolved_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse config JSON {resolved_path}: {exc}") from exc

    containers = _image_match_config_containers(payload)
    defaults: dict[str, object] = {}
    field_specs: tuple[tuple[str, tuple[str, ...], object], ...] = (
        ("band", ("band", "Band"), lambda value: int(value)),
        ("max_image_dimension", ("max_image_dimension", "maxImageDimension", "MaxImageDimension"), lambda value: int(value)),
        ("sub_block_size_x", ("sub_block_size_x", "subBlockSizeX", "SubBlockSizeX"), lambda value: int(value)),
        ("sub_block_size_y", ("sub_block_size_y", "subBlockSizeY", "SubBlockSizeY"), lambda value: int(value)),
        ("overlap_size_x", ("overlap_size_x", "overlapSizeX", "OverlapSizeX"), lambda value: int(value)),
        ("overlap_size_y", ("overlap_size_y", "overlapSizeY", "OverlapSizeY"), lambda value: int(value)),
        ("minimum_value", ("minimum_value", "minimumValue", "MinimumValue"), lambda value: float(value)),
        ("maximum_value", ("maximum_value", "maximumValue", "MaximumValue"), lambda value: float(value)),
        ("lower_percent", ("lower_percent", "lowerPercent", "LowerPercent"), lambda value: float(value)),
        ("upper_percent", ("upper_percent", "upperPercent", "UpperPercent"), lambda value: float(value)),
        ("invalid_value", ("invalid_values", "invalid_value", "invalidValues", "invalidValue", "InvalidValues", "InvalidValue"), _coerce_invalid_value_list),
        ("special_pixel_abs_threshold", ("special_pixel_abs_threshold", "specialPixelAbsThreshold", "SpecialPixelAbsThreshold"), lambda value: float(value)),
        ("min_valid_pixels", ("min_valid_pixels", "minValidPixels", "MinValidPixels"), lambda value: int(value)),
        (
            "valid_pixel_percent_threshold",
            ("valid_pixel_percent_threshold", "validPixelPercentThreshold", "ValidPixelPercentThreshold"),
            lambda value: _validate_valid_pixel_percent_threshold(float(value)),
        ),
        (
            "invalid_pixel_radius",
            ("invalid_pixel_radius", "invalidPixelRadius", "InvalidPixelRadius"),
            lambda value: validate_invalid_pixel_radius(int(value)),
        ),
        ("ratio_test", ("ratio_test", "ratioTest", "RatioTest"), lambda value: float(value)),
        ("max_features", ("max_features", "maxFeatures", "MaxFeatures"), lambda value: int(value)),
        ("sift_octave_layers", ("sift_octave_layers", "siftOctaveLayers", "SiftOctaveLayers"), lambda value: int(value)),
        ("sift_contrast_threshold", ("sift_contrast_threshold", "siftContrastThreshold", "SiftContrastThreshold"), lambda value: float(value)),
        ("sift_edge_threshold", ("sift_edge_threshold", "siftEdgeThreshold", "SiftEdgeThreshold"), lambda value: float(value)),
        ("sift_sigma", ("sift_sigma", "siftSigma", "SiftSigma"), lambda value: float(value)),
        ("crop_expand_pixels", ("crop_expand_pixels", "cropExpandPixels", "CropExpandPixels"), lambda value: int(value)),
        ("min_overlap_size", ("min_overlap_size", "minOverlapSize", "MinOverlapSize"), lambda value: int(value)),
        (
            "use_parallel_cpu",
            ("use_parallel_cpu", "useParallelCpu", "UseParallelCpu"),
            lambda value: _coerce_config_bool(value, field_name="use_parallel_cpu"),
        ),
        (
            "enable_low_resolution_offset_estimation",
            (
                "enable_low_resolution_offset_estimation",
                "enableLowResolutionOffsetEstimation",
                "EnableLowResolutionOffsetEstimation",
            ),
            lambda value: _coerce_config_bool(value, field_name="enable_low_resolution_offset_estimation"),
        ),
        (
            "low_resolution_level",
            ("low_resolution_level", "lowResolutionLevel", "LowResolutionLevel"),
            lambda value: _validate_low_resolution_level(int(value)),
        ),
        (
            "num_worker_parallel_cpu",
            ("num_worker_parallel_cpu", "numWorkerParallelCpu", "NumWorkerParallelCpu"),
            lambda value: _validate_num_worker_parallel_cpu(int(value)),
        ),
        (
            "write_match_visualization",
            ("write_match_visualization", "writeMatchVisualization", "WriteMatchVisualization"),
            lambda value: _coerce_config_bool(value, field_name="write_match_visualization"),
        ),
        (
            "match_visualization_output_path",
            ("match_visualization_output_path", "matchVisualizationOutputPath", "MatchVisualizationOutputPath"),
            lambda value: str(value),
        ),
        (
            "match_visualization_output_dir",
            ("match_visualization_output_dir", "matchVisualizationOutputDir", "MatchVisualizationOutputDir"),
            lambda value: str(value),
        ),
        (
            "match_visualization_scale",
            ("match_visualization_scale", "matchVisualizationScale", "MatchVisualizationScale"),
            lambda value: float(value),
        ),
    )

    for destination, candidate_keys, coercer in field_specs:
        value = _first_present_config_value(containers, candidate_keys)
        if value is None:
            continue
        try:
            defaults[destination] = coercer(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid ImageMatch config value for {destination!r}: {value!r}"
            ) from exc
    return defaults


def _full_image_window(image_width: int, image_height: int) -> TileWindow:
    return TileWindow(start_x=0, start_y=0, width=image_width, height=image_height)


def _paired_windows(
    *,
    left_offset_x: int,
    left_offset_y: int,
    right_offset_x: int,
    right_offset_y: int,
    common_width: int,
    common_height: int,
    max_image_dimension: int,
    block_width: int,
    block_height: int,
    overlap_x: int,
    overlap_y: int,
) -> list[PairedTileWindow]:
    if common_width <= 0 or common_height <= 0:
        return []

    if requires_tiling(common_width, common_height, max_dimension=max_image_dimension):
        local_windows = generate_tiles(
            common_width,
            common_height,
            block_width=block_width,
            block_height=block_height,
            overlap_x=overlap_x,
            overlap_y=overlap_y,
        )
    else:
        local_windows = [_full_image_window(common_width, common_height)]

    return [
        PairedTileWindow(
            local_window=local_window,
            left_window=TileWindow(
                start_x=left_offset_x + local_window.start_x,
                start_y=left_offset_y + local_window.start_y,
                width=local_window.width,
                height=local_window.height,
            ),
            right_window=TileWindow(
                start_x=right_offset_x + local_window.start_x,
                start_y=right_offset_y + local_window.start_y,
                width=local_window.width,
                height=local_window.height,
            ),
        )
        for local_window in local_windows
    ]


def _read_cube_window(cube: ip.Cube, window: TileWindow, *, band: int) -> np.ndarray:
    brick = ip.Brick(cube, window.width, window.height, 1)
    # TileWindow uses Python-style 0-based offsets, but ISIS Brick base positions are
    # 1-based sample/line coordinates. Keep this +1 explicit so regressions do not
    # silently shift all extracted pixels by one column/row.
    brick.set_base_position(window.start_x + 1, window.start_y + 1, band)
    cube.read(brick)
    return np.asarray(brick.double_buffer(), dtype=np.float64).reshape((window.height, window.width))


def _prepare_image_for_sift(
    values: np.ndarray,
    *,
    minimum_value: float | None,
    maximum_value: float | None,
    lower_percent: float,
    upper_percent: float,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    invalid_mask: np.ndarray | None = None,
    invalid_pixel_radius: int = 0,
) -> tuple[np.ndarray, np.ndarray, StretchStats]:
    resolved_invalid_mask, valid_pixel_stats = summarize_valid_pixels(
        values,
        invalid_values=invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
        invalid_mask=invalid_mask,
    )
    resolved_invalid_mask = expand_invalid_mask_for_radius(
        resolved_invalid_mask,
        invalid_pixel_radius=invalid_pixel_radius,
    )
    _, valid_pixel_stats = summarize_valid_pixels(values, invalid_mask=resolved_invalid_mask)
    if resolved_invalid_mask.all():
        stretched = np.zeros(values.shape, dtype=np.uint8)
        stretch_stats = StretchStats(
            minimum_value=0.0,
            maximum_value=0.0,
            valid_pixel_count=valid_pixel_stats.valid_pixel_count,
            invalid_pixel_count=valid_pixel_stats.invalid_pixel_count,
        )
        sift_mask = np.zeros(values.shape, dtype=np.uint8)
        return stretched, sift_mask, stretch_stats

    stretched, resolved_invalid_mask, stretch_stats = stretch_to_byte(
        values,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        lower_percent=lower_percent,
        upper_percent=upper_percent,
        invalid_values=invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
        invalid_mask=resolved_invalid_mask,
    )
    sift_mask = np.where(resolved_invalid_mask, 0, 255).astype(np.uint8)
    return stretched, sift_mask, stretch_stats


def _build_sift_detector(
    *,
    max_features: int | None,
    octave_layers: int,
    contrast_threshold: float,
    edge_threshold: float,
    sigma: float,
) -> cv2.SIFT:
    sift_kwargs: dict[str, int | float] = {
        "nOctaveLayers": octave_layers,
        "contrastThreshold": contrast_threshold,
        "edgeThreshold": edge_threshold,
        "sigma": sigma,
    }
    if max_features is not None:
        sift_kwargs["nfeatures"] = max_features
    return cv2.SIFT_create(**sift_kwargs)


def _match_tile(
    left_image: np.ndarray,
    right_image: np.ndarray,
    *,
    left_mask: np.ndarray,
    right_mask: np.ndarray,
    ratio_test: float,
    max_features: int | None,
    sift_octave_layers: int,
    sift_contrast_threshold: float,
    sift_edge_threshold: float,
    sift_sigma: float,
) -> tuple[list[cv2.KeyPoint], list[cv2.KeyPoint], list[cv2.DMatch]]:
    sift = _build_sift_detector(
        max_features=max_features,
        octave_layers=sift_octave_layers,
        contrast_threshold=sift_contrast_threshold,
        edge_threshold=sift_edge_threshold,
        sigma=sift_sigma,
    )
    left_keypoints, left_descriptors = sift.detectAndCompute(left_image, left_mask)
    right_keypoints, right_descriptors = sift.detectAndCompute(right_image, right_mask)

    if not left_keypoints or left_descriptors is None:
        return [], [], []
    if not right_keypoints or right_descriptors is None:
        return left_keypoints, [], []

    matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    raw_matches = matcher.knnMatch(left_descriptors, right_descriptors, k=2)

    filtered_matches: list[cv2.DMatch] = []
    for candidates in raw_matches:
        if len(candidates) < 2:
            continue
        best, alternate = candidates
        if best.distance < ratio_test * alternate.distance:
            filtered_matches.append(best)

    return left_keypoints, right_keypoints, filtered_matches


def _match_tile_from_window_values(
    *,
    left_values: np.ndarray,
    right_values: np.ndarray,
    local_window: TileWindow,
    left_window: TileWindow,
    right_window: TileWindow,
    minimum_value: float | None,
    maximum_value: float | None,
    lower_percent: float,
    upper_percent: float,
    left_invalid_values: tuple[float, ...],
    right_invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    min_valid_pixels: int,
    valid_pixel_percent_threshold: float,
    invalid_pixel_radius: int,
    ratio_test: float,
    max_features: int | None,
    sift_octave_layers: int,
    sift_contrast_threshold: float,
    sift_edge_threshold: float,
    sift_sigma: float,
) -> TileMatchResult:
    left_invalid_mask, left_valid_pixel_stats = summarize_valid_pixels(
        left_values,
        invalid_values=left_invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
    )
    right_invalid_mask, right_valid_pixel_stats = summarize_valid_pixels(
        right_values,
        invalid_values=right_invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
    )

    left_invalid_mask = expand_invalid_mask_for_radius(
        left_invalid_mask,
        invalid_pixel_radius=invalid_pixel_radius,
    )
    right_invalid_mask = expand_invalid_mask_for_radius(
        right_invalid_mask,
        invalid_pixel_radius=invalid_pixel_radius,
    )
    _, left_valid_pixel_stats = summarize_valid_pixels(left_values, invalid_mask=left_invalid_mask)
    _, right_valid_pixel_stats = summarize_valid_pixels(right_values, invalid_mask=right_invalid_mask)

    if (
        left_valid_pixel_stats.valid_pixel_ratio < valid_pixel_percent_threshold
        or right_valid_pixel_stats.valid_pixel_ratio < valid_pixel_percent_threshold
    ):
        return TileMatchResult(
            stats=TileMatchStats(
                local_start_x=local_window.start_x,
                local_start_y=local_window.start_y,
                width=local_window.width,
                height=local_window.height,
                left_start_x=left_window.start_x,
                left_start_y=left_window.start_y,
                right_start_x=right_window.start_x,
                right_start_y=right_window.start_y,
                left_valid_pixel_count=left_valid_pixel_stats.valid_pixel_count,
                right_valid_pixel_count=right_valid_pixel_stats.valid_pixel_count,
                left_valid_pixel_ratio=left_valid_pixel_stats.valid_pixel_ratio,
                right_valid_pixel_ratio=right_valid_pixel_stats.valid_pixel_ratio,
                left_feature_count=0,
                right_feature_count=0,
                match_count=0,
                status="skipped_valid_pixel_ratio_below_threshold",
            ),
            left_points=(),
            right_points=(),
        )

    left_image, left_mask, left_stats = _prepare_image_for_sift(
        left_values,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        lower_percent=lower_percent,
        upper_percent=upper_percent,
        invalid_values=left_invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
        invalid_mask=left_invalid_mask,
        invalid_pixel_radius=0,
    )
    right_image, right_mask, right_stats = _prepare_image_for_sift(
        right_values,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        lower_percent=lower_percent,
        upper_percent=upper_percent,
        invalid_values=right_invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
        invalid_mask=right_invalid_mask,
        invalid_pixel_radius=0,
    )

    if left_stats.valid_pixel_count < min_valid_pixels or right_stats.valid_pixel_count < min_valid_pixels:
        return TileMatchResult(
            stats=TileMatchStats(
                local_start_x=local_window.start_x,
                local_start_y=local_window.start_y,
                width=local_window.width,
                height=local_window.height,
                left_start_x=left_window.start_x,
                left_start_y=left_window.start_y,
                right_start_x=right_window.start_x,
                right_start_y=right_window.start_y,
                left_valid_pixel_count=left_stats.valid_pixel_count,
                right_valid_pixel_count=right_stats.valid_pixel_count,
                left_valid_pixel_ratio=left_stats.valid_pixel_ratio,
                right_valid_pixel_ratio=right_stats.valid_pixel_ratio,
                left_feature_count=0,
                right_feature_count=0,
                match_count=0,
                status="skipped_insufficient_valid_pixels",
            ),
            left_points=(),
            right_points=(),
        )

    left_keypoints, right_keypoints, filtered_matches = _match_tile(
        left_image,
        right_image,
        left_mask=left_mask,
        right_mask=right_mask,
        ratio_test=ratio_test,
        max_features=max_features,
        sift_octave_layers=sift_octave_layers,
        sift_contrast_threshold=sift_contrast_threshold,
        sift_edge_threshold=sift_edge_threshold,
        sift_sigma=sift_sigma,
    )

    if not left_keypoints or not right_keypoints:
        return TileMatchResult(
            stats=TileMatchStats(
                local_start_x=local_window.start_x,
                local_start_y=local_window.start_y,
                width=local_window.width,
                height=local_window.height,
                left_start_x=left_window.start_x,
                left_start_y=left_window.start_y,
                right_start_x=right_window.start_x,
                right_start_y=right_window.start_y,
                left_valid_pixel_count=left_stats.valid_pixel_count,
                right_valid_pixel_count=right_stats.valid_pixel_count,
                left_valid_pixel_ratio=left_stats.valid_pixel_ratio,
                right_valid_pixel_ratio=right_stats.valid_pixel_ratio,
                left_feature_count=len(left_keypoints),
                right_feature_count=len(right_keypoints),
                match_count=0,
                status="skipped_no_features",
            ),
            left_points=(),
            right_points=(),
        )

    if not filtered_matches:
        return TileMatchResult(
            stats=TileMatchStats(
                local_start_x=local_window.start_x,
                local_start_y=local_window.start_y,
                width=local_window.width,
                height=local_window.height,
                left_start_x=left_window.start_x,
                left_start_y=left_window.start_y,
                right_start_x=right_window.start_x,
                right_start_y=right_window.start_y,
                left_valid_pixel_count=left_stats.valid_pixel_count,
                right_valid_pixel_count=right_stats.valid_pixel_count,
                left_valid_pixel_ratio=left_stats.valid_pixel_ratio,
                right_valid_pixel_ratio=right_stats.valid_pixel_ratio,
                left_feature_count=len(left_keypoints),
                right_feature_count=len(right_keypoints),
                match_count=0,
                status="skipped_no_matches",
            ),
            left_points=(),
            right_points=(),
        )

    matched_left_points = tuple(
        _keypoint_to_isis_coordinates(left_keypoints[match.queryIdx], left_window)
        for match in filtered_matches
    )
    matched_right_points = tuple(
        _keypoint_to_isis_coordinates(right_keypoints[match.trainIdx], right_window)
        for match in filtered_matches
    )
    return TileMatchResult(
        stats=TileMatchStats(
            local_start_x=local_window.start_x,
            local_start_y=local_window.start_y,
            width=local_window.width,
            height=local_window.height,
            left_start_x=left_window.start_x,
            left_start_y=left_window.start_y,
            right_start_x=right_window.start_x,
            right_start_y=right_window.start_y,
            left_valid_pixel_count=left_stats.valid_pixel_count,
            right_valid_pixel_count=right_stats.valid_pixel_count,
            left_valid_pixel_ratio=left_stats.valid_pixel_ratio,
            right_valid_pixel_ratio=right_stats.valid_pixel_ratio,
            left_feature_count=len(left_keypoints),
            right_feature_count=len(right_keypoints),
            match_count=len(filtered_matches),
            status="matched",
        ),
        left_points=matched_left_points,
        right_points=matched_right_points,
    )


def _build_tile_match_tasks(
    windows: list[PairedTileWindow],
    *,
    left_dom_path: str | Path,
    right_dom_path: str | Path,
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
    ratio_test: float,
    max_features: int | None,
    sift_octave_layers: int,
    sift_contrast_threshold: float,
    sift_edge_threshold: float,
    sift_sigma: float,
) -> list[TileMatchTask]:
    return [
        TileMatchTask(
            left_dom_path=str(left_dom_path),
            right_dom_path=str(right_dom_path),
            band=band,
            paired_window=paired_window,
            minimum_value=minimum_value,
            maximum_value=maximum_value,
            lower_percent=lower_percent,
            upper_percent=upper_percent,
            invalid_values=invalid_values,
            special_pixel_abs_threshold=special_pixel_abs_threshold,
            min_valid_pixels=min_valid_pixels,
            valid_pixel_percent_threshold=valid_pixel_percent_threshold,
            invalid_pixel_radius=invalid_pixel_radius,
            ratio_test=ratio_test,
            max_features=max_features,
            sift_octave_layers=sift_octave_layers,
            sift_contrast_threshold=sift_contrast_threshold,
            sift_edge_threshold=sift_edge_threshold,
            sift_sigma=sift_sigma,
        )
        for paired_window in windows
    ]


def _match_single_paired_window_worker(task: TileMatchTask) -> TileMatchResult:
    left_cube = ip.Cube()
    right_cube = ip.Cube()
    left_cube.open(task.left_dom_path, "r")
    right_cube.open(task.right_dom_path, "r")
    try:
        left_invalid_values = _resolved_invalid_values_for_cube(left_cube, task.invalid_values)
        right_invalid_values = _resolved_invalid_values_for_cube(right_cube, task.invalid_values)
        left_values = _read_cube_window(left_cube, task.paired_window.left_window, band=task.band)
        right_values = _read_cube_window(right_cube, task.paired_window.right_window, band=task.band)
    finally:
        if left_cube.is_open():
            left_cube.close()
        if right_cube.is_open():
            right_cube.close()

    return _match_tile_from_window_values(
        left_values=left_values,
        right_values=right_values,
        local_window=task.paired_window.local_window,
        left_window=task.paired_window.left_window,
        right_window=task.paired_window.right_window,
        minimum_value=task.minimum_value,
        maximum_value=task.maximum_value,
        lower_percent=task.lower_percent,
        upper_percent=task.upper_percent,
        left_invalid_values=left_invalid_values,
        right_invalid_values=right_invalid_values,
        special_pixel_abs_threshold=task.special_pixel_abs_threshold,
        min_valid_pixels=task.min_valid_pixels,
        valid_pixel_percent_threshold=task.valid_pixel_percent_threshold,
        invalid_pixel_radius=task.invalid_pixel_radius,
        ratio_test=task.ratio_test,
        max_features=task.max_features,
        sift_octave_layers=task.sift_octave_layers,
        sift_contrast_threshold=task.sift_contrast_threshold,
        sift_edge_threshold=task.sift_edge_threshold,
        sift_sigma=task.sift_sigma,
    )


def _tile_match_process_pool_context() -> mp.context.BaseContext:
    preferred_context = "fork" if os.name == "posix" else "spawn"
    return mp.get_context(preferred_context)


def _run_parallel_tile_match_tasks(tasks: list[TileMatchTask], *, max_workers: int) -> list[TileMatchResult]:
    if not tasks:
        return []
    with ProcessPoolExecutor(max_workers=max_workers, mp_context=_tile_match_process_pool_context()) as executor:
        return list(executor.map(_match_single_paired_window_worker, tasks))


def _run_serial_tile_match_tasks(
    windows: list[PairedTileWindow],
    *,
    left_cube: ip.Cube,
    right_cube: ip.Cube,
    band: int,
    minimum_value: float | None,
    maximum_value: float | None,
    lower_percent: float,
    upper_percent: float,
    left_invalid_values: tuple[float, ...],
    right_invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    min_valid_pixels: int,
    valid_pixel_percent_threshold: float,
    invalid_pixel_radius: int,
    ratio_test: float,
    max_features: int | None,
    sift_octave_layers: int,
    sift_contrast_threshold: float,
    sift_edge_threshold: float,
    sift_sigma: float,
) -> list[TileMatchResult]:
    tile_results: list[TileMatchResult] = []
    for paired_window in windows:
        left_values = _read_cube_window(left_cube, paired_window.left_window, band=band)
        right_values = _read_cube_window(right_cube, paired_window.right_window, band=band)
        tile_results.append(
            _match_tile_from_window_values(
                left_values=left_values,
                right_values=right_values,
                local_window=paired_window.local_window,
                left_window=paired_window.left_window,
                right_window=paired_window.right_window,
                minimum_value=minimum_value,
                maximum_value=maximum_value,
                lower_percent=lower_percent,
                upper_percent=upper_percent,
                left_invalid_values=left_invalid_values,
                right_invalid_values=right_invalid_values,
                special_pixel_abs_threshold=special_pixel_abs_threshold,
                min_valid_pixels=min_valid_pixels,
                valid_pixel_percent_threshold=valid_pixel_percent_threshold,
                invalid_pixel_radius=invalid_pixel_radius,
                ratio_test=ratio_test,
                max_features=max_features,
                sift_octave_layers=sift_octave_layers,
                sift_contrast_threshold=sift_contrast_threshold,
                sift_edge_threshold=sift_edge_threshold,
                sift_sigma=sift_sigma,
            )
        )
    return tile_results


def _keypoint_to_isis_coordinates(keypoint: cv2.KeyPoint, window: TileWindow) -> Keypoint:
    # OpenCV keypoint.pt is expressed in tile-local 0-based image coordinates, while
    # .key files and downstream ISIS geometry use 1-based sample/line coordinates in
    # the full DOM image. The +1 here is therefore required, not cosmetic.
    return Keypoint(
        sample=window.start_x + float(keypoint.pt[0]) + 1.0,
        line=window.start_y + float(keypoint.pt[1]) + 1.0,
    )


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
        full_window = _full_image_window(cube.sample_count(), cube.line_count())
        values = _read_cube_window(cube, full_window, band=band)
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


def _resolved_invalid_values_for_cube(cube: ip.Cube, invalid_values: tuple[float, ...]) -> tuple[float, ...]:
    resolved_invalid_values = list(invalid_values)
    zero_invalid_pixel_types = {
        getattr(ip.PixelType, "UnsignedByte", None),
        getattr(ip.PixelType, "SignedByte", None),
    }
    if cube.pixel_type() in zero_invalid_pixel_types and 0.0 not in resolved_invalid_values:
        resolved_invalid_values.append(0.0)
    return tuple(resolved_invalid_values)


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


def _create_low_resolution_dom(
    source_path: str | Path,
    output_path: str | Path,
    *,
    level: int,
) -> Path:
    resolved_source_path = Path(source_path)
    resolved_output_path = Path(output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    if level == 0:
        resolved_output_path.write_bytes(resolved_source_path.read_bytes())
        return resolved_output_path

    scale_divisor = 2 ** level
    percent = 100.0 / float(scale_divisor)
    _run_command(["gdaladdo", "-r", "average", str(resolved_source_path), *[str(2 ** index) for index in range(1, level + 1)]])
    _run_command(
        [
            "gdal_translate",
            "-of",
            "ISIS3",
            "-r",
            "bilinear",
            "-outsize",
            f"{percent:.8f}%",
            f"{percent:.8f}%",
            str(resolved_source_path),
            str(resolved_output_path),
        ]
    )
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


def _trimmed_mean(values: list[float], *, trim_ratio: float = 0.05) -> float:
    if not values:
        raise ValueError("Cannot compute a trimmed mean from an empty sample set.")
    sorted_values = sorted(float(value) for value in values)
    trim_count = int(len(sorted_values) * trim_ratio)
    if trim_count * 2 >= len(sorted_values):
        trimmed_values = sorted_values
    else:
        trimmed_values = sorted_values[trim_count: len(sorted_values) - trim_count]
    return float(sum(trimmed_values) / len(trimmed_values))


def _estimate_low_resolution_projected_offset(
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
    ratio_test: float,
    max_features: int | None,
    sift_octave_layers: int,
    sift_contrast_threshold: float,
    sift_edge_threshold: float,
    sift_sigma: float,
) -> dict[str, object]:
    if not enabled:
        return {
            "enabled": False,
            "status": "disabled",
            "fallback_offset_zero": False,
            "reason": "Low-resolution offset estimation is disabled.",
            "delta_x_projected": 0.0,
            "delta_y_projected": 0.0,
            "retained_match_count": 0,
        }

    resolved_level = _validate_low_resolution_level(low_resolution_level)
    resolved_output_dir = Path(low_resolution_output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    pair_tag = _low_resolution_pair_tag(left_dom_path, right_dom_path)
    started_at = time.perf_counter()
    try:
        _require_command("gdaladdo")
        _require_command("gdal_translate")

        left_low_res_dom = _create_low_resolution_dom(
            left_dom_path,
            resolved_output_dir / f"{Path(left_dom_path).stem}__level{resolved_level}.cub",
            level=resolved_level,
        )
        right_low_res_dom = _create_low_resolution_dom(
            right_dom_path,
            resolved_output_dir / f"{Path(right_dom_path).stem}__level{resolved_level}.cub",
            level=resolved_level,
        )

        raw_left_key, raw_right_key, raw_summary = match_dom_pair(
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

        filtered_left_key, filtered_right_key, ransac_summary = filter_stereo_pair_keypoints_with_ransac(
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
                "delta_x_projected": 0.0,
                "delta_y_projected": 0.0,
                "retained_match_count": 0,
                "low_resolution_level": resolved_level,
                "left_low_resolution_dom": str(left_low_res_dom),
                "right_low_resolution_dom": str(right_low_res_dom),
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

        delta_x_projected = _trimmed_mean(delta_x_values)
        delta_y_projected = _trimmed_mean(delta_y_values)
        visualization_result = write_stereo_pair_match_visualization(
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
            "trim_fraction_each_side": 0.05,
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
            "delta_x_projected": 0.0,
            "delta_y_projected": 0.0,
            "retained_match_count": 0,
            "low_resolution_level": resolved_level,
            "elapsed_seconds": elapsed_seconds,
        }


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


def filter_stereo_pair_keypoints_with_ransac(
    left_key_file: KeypointFile,
    right_key_file: KeypointFile,
    *,
    ransac_reproj_threshold: float = 3.0,
    ransac_confidence: float = 0.995,
    ransac_max_iters: int = 5000,
    ransac_mode: str = "loose",
    loose_keep_pixel_threshold: float = 1.0,
) -> tuple[KeypointFile, KeypointFile, dict[str, object]]:
    if len(left_key_file.points) != len(right_key_file.points):
        raise ValueError("Left and right keypoint files must contain the same number of points.")

    normalized_mode = _normalize_ransac_mode(ransac_mode)
    input_count = len(left_key_file.points)

    if input_count < 4:
        summary = {
            "applied": False,
            "status": "skipped_insufficient_points",
            "mode": normalized_mode,
            "input_count": input_count,
            "retained_count": input_count,
            "dropped_count": 0,
            "opencv_inlier_count": input_count,
            "opencv_outlier_count": 0,
            "retained_soft_outlier_count": 0,
            "soft_outlier_original_indices": [],
            "retained_soft_outlier_positions": [],
            "reproj_threshold": float(ransac_reproj_threshold),
            "confidence": float(ransac_confidence),
            "max_iters": int(ransac_max_iters),
            "loose_keep_pixel_threshold": float(loose_keep_pixel_threshold),
            "homography_matrix": None,
        }
        return left_key_file, right_key_file, summary

    left_points = np.asarray([(point.sample, point.line) for point in left_key_file.points], dtype=np.float32).reshape(-1, 1, 2)
    right_points = np.asarray([(point.sample, point.line) for point in right_key_file.points], dtype=np.float32).reshape(-1, 1, 2)
    homography, mask = cv2.findHomography(
        left_points,
        right_points,
        cv2.RANSAC,
        ransacReprojThreshold=float(ransac_reproj_threshold),
        confidence=float(ransac_confidence),
        maxIters=int(ransac_max_iters),
    )

    if homography is None or mask is None:
        summary = {
            "applied": False,
            "status": "skipped_homography_failed",
            "mode": normalized_mode,
            "input_count": input_count,
            "retained_count": input_count,
            "dropped_count": 0,
            "opencv_inlier_count": 0,
            "opencv_outlier_count": 0,
            "retained_soft_outlier_count": 0,
            "soft_outlier_original_indices": [],
            "retained_soft_outlier_positions": [],
            "reproj_threshold": float(ransac_reproj_threshold),
            "confidence": float(ransac_confidence),
            "max_iters": int(ransac_max_iters),
            "loose_keep_pixel_threshold": float(loose_keep_pixel_threshold),
            "homography_matrix": None,
        }
        return left_key_file, right_key_file, summary

    opencv_inlier_mask = mask.reshape(-1).astype(bool)
    retained_mask = opencv_inlier_mask.copy()
    soft_outlier_original_indices: list[int] = []

    if normalized_mode == "loose":
        projected_right = cv2.perspectiveTransform(left_points, homography).reshape(-1, 2)
        right_coordinates = right_points.reshape(-1, 2)
        for index, (is_inlier, projected, actual) in enumerate(zip(opencv_inlier_mask, projected_right, right_coordinates, strict=True)):
            if is_inlier:
                continue
            reprojection_error = float(np.linalg.norm(projected - actual))
            if reprojection_error <= float(loose_keep_pixel_threshold):
                retained_mask[index] = True
                soft_outlier_original_indices.append(index)

    filtered_left_points: list[Keypoint] = []
    filtered_right_points: list[Keypoint] = []
    retained_soft_outlier_positions: list[int] = []
    retained_position = 0
    for index, (left_point, right_point, keep_point) in enumerate(
        zip(left_key_file.points, right_key_file.points, retained_mask, strict=True)
    ):
        if not keep_point:
            continue
        filtered_left_points.append(left_point)
        filtered_right_points.append(right_point)
        if index in soft_outlier_original_indices:
            retained_soft_outlier_positions.append(retained_position)
        retained_position += 1

    summary = {
        "applied": True,
        "status": "filtered",
        "mode": normalized_mode,
        "input_count": input_count,
        "retained_count": len(filtered_left_points),
        "dropped_count": input_count - len(filtered_left_points),
        "opencv_inlier_count": int(opencv_inlier_mask.sum()),
        "opencv_outlier_count": int((~opencv_inlier_mask).sum()),
        "retained_soft_outlier_count": len(soft_outlier_original_indices),
        "soft_outlier_original_indices": soft_outlier_original_indices,
        "retained_soft_outlier_positions": retained_soft_outlier_positions,
        "reproj_threshold": float(ransac_reproj_threshold),
        "confidence": float(ransac_confidence),
        "max_iters": int(ransac_max_iters),
        "loose_keep_pixel_threshold": float(loose_keep_pixel_threshold),
        "homography_matrix": homography.tolist(),
    }
    return (
        KeypointFile(left_key_file.image_width, left_key_file.image_height, tuple(filtered_left_points)),
        KeypointFile(right_key_file.image_width, right_key_file.image_height, tuple(filtered_right_points)),
        summary,
    )


def filter_stereo_pair_key_files_with_ransac(
    left_input: str | Path,
    right_input: str | Path,
    left_output: str | Path,
    right_output: str | Path,
    *,
    ransac_reproj_threshold: float = 3.0,
    ransac_confidence: float = 0.995,
    ransac_max_iters: int = 5000,
    ransac_mode: str = "loose",
    loose_keep_pixel_threshold: float = 1.0,
) -> dict[str, object]:
    left_key_file = read_key_file(left_input)
    right_key_file = read_key_file(right_input)
    filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_with_ransac(
        left_key_file,
        right_key_file,
        ransac_reproj_threshold=ransac_reproj_threshold,
        ransac_confidence=ransac_confidence,
        ransac_max_iters=ransac_max_iters,
        ransac_mode=ransac_mode,
        loose_keep_pixel_threshold=loose_keep_pixel_threshold,
    )
    write_key_file(left_output, filtered_left)
    write_key_file(right_output, filtered_right)
    return {
        **summary,
        "left_input": str(left_input),
        "right_input": str(right_input),
        "left_output": str(left_output),
        "right_output": str(right_output),
    }


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

    left_image = _read_cube_as_stretched_byte(
        left_dom_path,
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
    left_keypoints = [_isis_keypoint_to_draw_matches_keypoint(point, scale_factor=scale_factor) for point in left_key_file.points]
    right_keypoints = [_isis_keypoint_to_draw_matches_keypoint(point, scale_factor=scale_factor) for point in right_key_file.points]
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

    return {
        "output_path": str(resolved_output_path),
        "point_count": len(left_keypoints),
        "scale_factor": float(scale_factor),
        "highlighted_match_count": 0 if highlight_match_indices is None else len(highlight_match_indices),
        "left_dom": str(left_dom_path),
        "right_dom": str(right_dom_path),
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


def match_dom_pair(
    left_dom_path: str | Path,
    right_dom_path: str | Path,
    *,
    band: int = 1,
    max_image_dimension: int = 3000,
    block_width: int = 1024,
    block_height: int = 1024,
    overlap_x: int = 128,
    overlap_y: int = 128,
    minimum_value: float | None = None,
    maximum_value: float | None = None,
    lower_percent: float = 0.5,
    upper_percent: float = 99.5,
    invalid_values: tuple[float, ...] = (),
    special_pixel_abs_threshold: float = 1.0e300,
    min_valid_pixels: int = 64,
    valid_pixel_percent_threshold: float = 0.0,
    invalid_pixel_radius: int = 1,
    ratio_test: float = 0.75,
    max_features: int | None = None,
    sift_octave_layers: int = 3,
    sift_contrast_threshold: float = 0.04,
    sift_edge_threshold: float = 10.0,
    sift_sigma: float = 1.6,
    crop_expand_pixels: int = 100,
    min_overlap_size: int = 16,
    use_parallel_cpu: bool = True,
    num_worker_parallel_cpu: int = DEFAULT_NUM_WORKER_PARALLEL_CPU,
    enable_low_resolution_offset_estimation: bool = False,
    low_resolution_level: int = DEFAULT_LOW_RESOLUTION_LEVEL,
    low_resolution_output_dir: str | Path | None = None,
) -> tuple[KeypointFile, KeypointFile, dict[str, object]]:
    left_cube = ip.Cube()
    right_cube = ip.Cube()
    left_cube.open(str(left_dom_path), "r")
    right_cube.open(str(right_dom_path), "r")

    try:
        resolved_valid_pixel_percent_threshold = _validate_valid_pixel_percent_threshold(valid_pixel_percent_threshold)
        resolved_num_worker_parallel_cpu = _validate_num_worker_parallel_cpu(num_worker_parallel_cpu)
        resolved_invalid_pixel_radius = validate_invalid_pixel_radius(invalid_pixel_radius)
        resolved_low_resolution_level = _validate_low_resolution_level(low_resolution_level)
        left_width = left_cube.sample_count()
        left_height = left_cube.line_count()
        right_width = right_cube.sample_count()
        right_height = right_cube.line_count()
        left_invalid_values = _resolved_invalid_values_for_cube(left_cube, invalid_values)
        right_invalid_values = _resolved_invalid_values_for_cube(right_cube, invalid_values)

        if band <= 0 or band > min(left_cube.band_count(), right_cube.band_count()):
            raise ValueError(f"Band {band} is out of range for the requested DOM cubes.")

        left_points: list[Keypoint] = []
        right_points: list[Keypoint] = []
        tile_summaries: list[TileMatchStats] = []
        parallel_cpu_requested = bool(use_parallel_cpu)
        parallel_cpu_used = False
        parallel_cpu_backend = "serial"
        parallel_cpu_worker_count = 0
        low_resolution_offset_summary = _estimate_low_resolution_projected_offset(
            left_dom_path,
            right_dom_path,
            enabled=enable_low_resolution_offset_estimation,
            low_resolution_level=resolved_low_resolution_level,
            low_resolution_output_dir=(
                low_resolution_output_dir
                if low_resolution_output_dir is not None
                else _default_low_resolution_output_dir(left_dom_path, right_dom_path)
            ),
            band=band,
            minimum_value=minimum_value,
            maximum_value=maximum_value,
            lower_percent=lower_percent,
            upper_percent=upper_percent,
            invalid_values=invalid_values,
            special_pixel_abs_threshold=special_pixel_abs_threshold,
            min_valid_pixels=min_valid_pixels,
            valid_pixel_percent_threshold=resolved_valid_pixel_percent_threshold,
            invalid_pixel_radius=resolved_invalid_pixel_radius,
            ratio_test=ratio_test,
            max_features=max_features,
            sift_octave_layers=sift_octave_layers,
            sift_contrast_threshold=sift_contrast_threshold,
            sift_edge_threshold=sift_edge_threshold,
            sift_sigma=sift_sigma,
        )
        preparation = prepare_dom_pair_for_matching(
            left_dom_path,
            right_dom_path,
            expand_pixels=crop_expand_pixels,
            min_overlap_size=min_overlap_size,
            projected_delta_x=float(low_resolution_offset_summary["delta_x_projected"]),
            projected_delta_y=float(low_resolution_offset_summary["delta_y_projected"]),
        )

        if preparation.status == "ready":
            windows = _paired_windows(
                left_offset_x=preparation.left.offset_sample,
                left_offset_y=preparation.left.offset_line,
                right_offset_x=preparation.right.offset_sample,
                right_offset_y=preparation.right.offset_line,
                common_width=preparation.shared_width,
                common_height=preparation.shared_height,
                max_image_dimension=max_image_dimension,
                block_width=block_width,
                block_height=block_height,
                overlap_x=overlap_x,
                overlap_y=overlap_y,
            )

            if windows:
                if parallel_cpu_requested and len(windows) > 1:
                    candidate_worker_count = min(len(windows), resolved_num_worker_parallel_cpu)
                    if candidate_worker_count > 1:
                        tile_results = _run_parallel_tile_match_tasks(
                            _build_tile_match_tasks(
                                windows,
                                left_dom_path=left_dom_path,
                                right_dom_path=right_dom_path,
                                band=band,
                                minimum_value=minimum_value,
                                maximum_value=maximum_value,
                                lower_percent=lower_percent,
                                upper_percent=upper_percent,
                                invalid_values=invalid_values,
                                special_pixel_abs_threshold=special_pixel_abs_threshold,
                                min_valid_pixels=min_valid_pixels,
                                valid_pixel_percent_threshold=resolved_valid_pixel_percent_threshold,
                                invalid_pixel_radius=resolved_invalid_pixel_radius,
                                ratio_test=ratio_test,
                                max_features=max_features,
                                sift_octave_layers=sift_octave_layers,
                                sift_contrast_threshold=sift_contrast_threshold,
                                sift_edge_threshold=sift_edge_threshold,
                                sift_sigma=sift_sigma,
                            ),
                            max_workers=candidate_worker_count,
                        )
                        parallel_cpu_used = True
                        parallel_cpu_backend = "process_pool"
                        parallel_cpu_worker_count = candidate_worker_count
                    else:
                        tile_results = _run_serial_tile_match_tasks(
                            windows,
                            left_cube=left_cube,
                            right_cube=right_cube,
                            band=band,
                            minimum_value=minimum_value,
                            maximum_value=maximum_value,
                            lower_percent=lower_percent,
                            upper_percent=upper_percent,
                            left_invalid_values=left_invalid_values,
                            right_invalid_values=right_invalid_values,
                            special_pixel_abs_threshold=special_pixel_abs_threshold,
                            min_valid_pixels=min_valid_pixels,
                            valid_pixel_percent_threshold=resolved_valid_pixel_percent_threshold,
                            invalid_pixel_radius=resolved_invalid_pixel_radius,
                            ratio_test=ratio_test,
                            max_features=max_features,
                            sift_octave_layers=sift_octave_layers,
                            sift_contrast_threshold=sift_contrast_threshold,
                            sift_edge_threshold=sift_edge_threshold,
                            sift_sigma=sift_sigma,
                        )
                        parallel_cpu_worker_count = 1
                else:
                    tile_results = _run_serial_tile_match_tasks(
                        windows,
                        left_cube=left_cube,
                        right_cube=right_cube,
                        band=band,
                        minimum_value=minimum_value,
                        maximum_value=maximum_value,
                        lower_percent=lower_percent,
                        upper_percent=upper_percent,
                        left_invalid_values=left_invalid_values,
                        right_invalid_values=right_invalid_values,
                        special_pixel_abs_threshold=special_pixel_abs_threshold,
                        min_valid_pixels=min_valid_pixels,
                        valid_pixel_percent_threshold=resolved_valid_pixel_percent_threshold,
                        invalid_pixel_radius=resolved_invalid_pixel_radius,
                        ratio_test=ratio_test,
                        max_features=max_features,
                        sift_octave_layers=sift_octave_layers,
                        sift_contrast_threshold=sift_contrast_threshold,
                        sift_edge_threshold=sift_edge_threshold,
                        sift_sigma=sift_sigma,
                    )
                    parallel_cpu_worker_count = 1

                for tile_result in tile_results:
                    tile_summaries.append(tile_result.stats)
                    left_points.extend(tile_result.left_points)
                    right_points.extend(tile_result.right_points)
        else:
            windows = []

        left_key_file = KeypointFile(left_width, left_height, tuple(left_points))
        right_key_file = KeypointFile(right_width, right_height, tuple(right_points))
        summary = {
            "left_dom": str(left_dom_path),
            "right_dom": str(right_dom_path),
            "band": band,
            "min_valid_pixels": min_valid_pixels,
            "valid_pixel_percent_threshold": resolved_valid_pixel_percent_threshold,
            "invalid_pixel_radius": resolved_invalid_pixel_radius,
            "ratio_test": ratio_test,
            "status": preparation.status if preparation.status != "ready" else ("matched" if left_points else "matched_no_points"),
            "reason": preparation.reason,
            "tiling_used": len(windows) > 1,
            "shared_extent_width": preparation.shared_width,
            "shared_extent_height": preparation.shared_height,
            "dimension_mismatch": left_width != right_width or left_height != right_height,
            "tile_count": len(windows),
            "matched_tile_count": sum(1 for tile in tile_summaries if tile.status == "matched"),
            "skipped_tile_count": sum(1 for tile in tile_summaries if tile.status != "matched"),
            "point_count": len(left_points),
            "parallel_cpu_requested": parallel_cpu_requested,
            "num_worker_parallel_cpu": resolved_num_worker_parallel_cpu,
            "parallel_cpu_used": parallel_cpu_used,
            "parallel_cpu_backend": parallel_cpu_backend,
            "parallel_cpu_worker_count": parallel_cpu_worker_count,
            "left_image_width": left_width,
            "left_image_height": left_height,
            "right_image_width": right_width,
            "right_image_height": right_height,
            "sift_parameters": {
                "max_features": max_features,
                "octave_layers": sift_octave_layers,
                "contrast_threshold": sift_contrast_threshold,
                "edge_threshold": sift_edge_threshold,
                "sigma": sift_sigma,
            },
            "low_resolution_offset": low_resolution_offset_summary,
            "preparation": asdict(preparation),
            "tiles": [asdict(tile) for tile in tile_summaries],
        }
        return left_key_file, right_key_file, summary
    finally:
        if left_cube.is_open():
            left_cube.close()
        if right_cube.is_open():
            right_cube.close()


def match_dom_pair_to_key_files(
    left_dom_path: str | Path,
    right_dom_path: str | Path,
    left_output_key: str | Path,
    right_output_key: str | Path,
    metadata_output: str | Path | None = None,
    write_match_visualization: bool = True,
    match_visualization_output_path: str | Path | None = None,
    match_visualization_output_dir: str | Path | None = None,
    match_visualization_scale: float = 1.0 / 3.0,
    **kwargs,
) -> dict[str, object]:
    if "low_resolution_output_dir" not in kwargs or kwargs.get("low_resolution_output_dir") is None:
        kwargs["low_resolution_output_dir"] = _default_low_resolution_output_dir(
            left_dom_path,
            right_dom_path,
            metadata_output=metadata_output,
            left_output_key=left_output_key,
        )
    left_key_file, right_key_file, summary = match_dom_pair(left_dom_path, right_dom_path, **kwargs)
    write_key_file(left_output_key, left_key_file)
    write_key_file(right_output_key, right_key_file)
    if metadata_output is not None:
        metadata_payload = dict(summary["preparation"])
        metadata_payload["image_match"] = {
            "status": summary["status"],
            "reason": summary["reason"],
            "point_count": summary["point_count"],
            "tile_count": summary["tile_count"],
            "matched_tile_count": summary["matched_tile_count"],
            "skipped_tile_count": summary["skipped_tile_count"],
            "tiling_used": summary["tiling_used"],
            "valid_pixel_percent_threshold": summary["valid_pixel_percent_threshold"],
            "invalid_pixel_radius": summary["invalid_pixel_radius"],
            "parallel_cpu_requested": summary["parallel_cpu_requested"],
            "num_worker_parallel_cpu": summary["num_worker_parallel_cpu"],
            "parallel_cpu_used": summary["parallel_cpu_used"],
            "parallel_cpu_backend": summary["parallel_cpu_backend"],
            "parallel_cpu_worker_count": summary["parallel_cpu_worker_count"],
            "low_resolution_offset": summary["low_resolution_offset"],
        }
        write_pair_preparation_metadata(
            metadata_output,
            metadata_payload,
        )
    match_visualization_result: dict[str, object] | None = None
    if write_match_visualization:
        visualization_output_directory = (
            Path(match_visualization_output_dir)
            if match_visualization_output_dir is not None
            else (None if match_visualization_output_path is not None else Path(left_output_key).parent)
        )
        match_visualization_result = write_stereo_pair_match_visualization(
            left_dom_path,
            right_dom_path,
            left_key_file,
            right_key_file,
            output_path=match_visualization_output_path,
            output_directory=visualization_output_directory,
            scale_factor=match_visualization_scale,
            band=int(kwargs.get("band", 1)),
            minimum_value=kwargs.get("minimum_value"),
            maximum_value=kwargs.get("maximum_value"),
            lower_percent=float(kwargs.get("lower_percent", 0.5)),
            upper_percent=float(kwargs.get("upper_percent", 99.5)),
            invalid_values=tuple(kwargs.get("invalid_values", ())),
            special_pixel_abs_threshold=float(kwargs.get("special_pixel_abs_threshold", 1.0e300)),
        )
    return {
        **summary,
        "left_output_key": str(left_output_key),
        "right_output_key": str(right_output_key),
        **({"metadata_output": str(metadata_output)} if metadata_output is not None else {}),
        **({"match_visualization": match_visualization_result} if match_visualization_result is not None else {}),
    }


def build_argument_parser(config_defaults: dict[str, object] | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Match two DOM cubes with OpenCV SIFT and write DOM-space `.key` files.")
    parser.add_argument("--config", default=None, help="Optional config JSON path. When provided, the ImageMatch section supplies default values for this CLI; explicit CLI flags still win.")
    parser.add_argument("left_dom", help="Left DOM cube path.")
    parser.add_argument("right_dom", help="Right DOM cube path.")
    parser.add_argument("left_output_key", help="Output `.key` file for the left DOM image.")
    parser.add_argument("right_output_key", help="Output `.key` file for the right DOM image.")
    parser.add_argument("--metadata-output", default=None, help="Optional JSON sidecar path for projected-overlap crop metadata.")
    parser.add_argument("--band", type=int, default=1, help="Cube band index used for matching.")
    parser.add_argument("--max-image-dimension", type=int, default=3000, help="Maximum image dimension allowed before tiling is enabled.")
    parser.add_argument("--sub-block-size-x", type=int, default=1024, help="Tile width used when block matching is enabled.")
    parser.add_argument("--sub-block-size-y", type=int, default=1024, help="Tile height used when block matching is enabled.")
    parser.add_argument("--overlap-size-x", type=int, default=128, help="Horizontal overlap between adjacent tiles.")
    parser.add_argument("--overlap-size-y", type=int, default=128, help="Vertical overlap between adjacent tiles.")
    parser.add_argument("--minimum-value", type=float, default=None, help="Manual gray-stretch minimum value.")
    parser.add_argument("--maximum-value", type=float, default=None, help="Manual gray-stretch maximum value.")
    parser.add_argument("--lower-percent", type=float, default=0.5, help="Lower percentile used by automatic gray stretch.")
    parser.add_argument("--upper-percent", type=float, default=99.5, help="Upper percentile used by automatic gray stretch.")
    parser.add_argument("--invalid-value", action="append", default=[], type=float, help="Additional invalid pixel sentinel. Repeat for multiple values.")
    parser.add_argument("--special-pixel-abs-threshold", type=float, default=1.0e300, help="Absolute-value threshold used to treat extreme ISIS special pixels as invalid.")
    parser.add_argument("--min-valid-pixels", type=int, default=64, help="Minimum number of valid pixels required before attempting SIFT on a tile.")
    parser.add_argument("--valid-pixel-percent-threshold", type=_parse_valid_pixel_percent_threshold, default=0.0, help="Minimum valid-pixel ratio required before attempting SIFT on a tile. Must be within [0.0, 1.0].")
    parser.add_argument("--invalid-pixel-radius", type=_parse_invalid_pixel_radius, default=1, help="Don't detect feature point within this many pixels of image borders or invalid pixel. Must be within [0, 100]. Default: 1.")
    parser.add_argument("--ratio-test", type=float, default=0.75, help="Lowe ratio-test threshold used for descriptor filtering.")
    parser.add_argument("--max-features", type=int, default=None, help="Optional maximum number of SIFT features per tile.")
    parser.add_argument("--sift-octave-layers", type=int, default=3, help="Number of octave layers used by the OpenCV SIFT detector.")
    parser.add_argument("--sift-contrast-threshold", type=float, default=0.04, help="Contrast threshold used by the OpenCV SIFT detector.")
    parser.add_argument("--sift-edge-threshold", type=float, default=10.0, help="Edge threshold used by the OpenCV SIFT detector.")
    parser.add_argument("--sift-sigma", type=float, default=1.6, help="Gaussian sigma used by the OpenCV SIFT detector.")
    parser.add_argument("--crop-expand-pixels", type=int, default=100, help="Extra projected-overlap margin, expressed in pixels, added before matching.")
    parser.add_argument("--min-overlap-size", type=int, default=16, help="Skip matching when the expanded projected-overlap window is smaller than this many pixels in either direction.")
    parser.add_argument("--enable-low-resolution-offset-estimation", dest="enable_low_resolution_offset_estimation", action="store_true", help="Enable low-resolution DOM matching to estimate a projected global offset before the full-resolution overlap crop is prepared.")
    parser.add_argument("--low-resolution-level", type=_parse_low_resolution_level, default=DEFAULT_LOW_RESOLUTION_LEVEL, help=f"Low-resolution pyramid level used for the projected offset estimation stage. Must be >= 0. Default: {DEFAULT_LOW_RESOLUTION_LEVEL}.")
    parser.add_argument("--num-worker-parallel-cpu", type=_parse_num_worker_parallel_cpu, default=DEFAULT_NUM_WORKER_PARALLEL_CPU, help=f"Maximum worker-process count used when CPU tile parallelism is enabled. Must be within [1, {MAX_NUM_WORKER_PARALLEL_CPU}]. Default: {DEFAULT_NUM_WORKER_PARALLEL_CPU}.")
    parser.add_argument("--use-parallel-cpu", dest="use_parallel_cpu", action="store_true", help="Enable CPU process-pool parallelism for tiled matching. Enabled by default.")
    parser.add_argument("--no-parallel-cpu", dest="use_parallel_cpu", action="store_false", help="Disable CPU process-pool parallelism and force serial tile matching.")
    parser.add_argument("--no-write-match-visualization", dest="write_match_visualization", action="store_false", help="Disable the default pre-RANSAC drawMatches PNG output written for the matched DOM pair.")
    parser.add_argument("--match-visualization-output-path", default=None, help="Optional explicit output path for the pre-RANSAC drawMatches PNG written by the image-match stage.")
    parser.add_argument("--match-visualization-output-dir", default=None, help="Optional directory used when auto-naming the pre-RANSAC drawMatches PNG written by the image-match stage.")
    parser.add_argument("--match-visualization-scale", type=float, default=1.0 / 3.0, help="Image scale factor used when writing the pre-RANSAC drawMatches PNG. Defaults to 1/3 for a smaller preview.")
    parser.set_defaults(write_match_visualization=True, use_parallel_cpu=True, enable_low_resolution_offset_estimation=False)
    if config_defaults:
        parser.set_defaults(**config_defaults)
    return parser


def main(argv: list[str] | None = None) -> None:
    config_probe_parser = argparse.ArgumentParser(add_help=False)
    config_probe_parser.add_argument("--config", default=None)
    config_probe_args, _ = config_probe_parser.parse_known_args(argv)

    config_defaults: dict[str, object] = {}
    if config_probe_args.config is not None:
        try:
            config_defaults = load_image_match_defaults_from_config(config_probe_args.config)
        except ValueError as exc:
            config_probe_parser.error(str(exc))

    parser = build_argument_parser(config_defaults=config_defaults)
    args = parser.parse_args(argv)
    result = match_dom_pair_to_key_files(
        args.left_dom,
        args.right_dom,
        args.left_output_key,
        args.right_output_key,
        metadata_output=args.metadata_output,
        band=args.band,
        max_image_dimension=args.max_image_dimension,
        block_width=args.sub_block_size_x,
        block_height=args.sub_block_size_y,
        overlap_x=args.overlap_size_x,
        overlap_y=args.overlap_size_y,
        minimum_value=args.minimum_value,
        maximum_value=args.maximum_value,
        lower_percent=args.lower_percent,
        upper_percent=args.upper_percent,
        invalid_values=tuple(args.invalid_value),
        special_pixel_abs_threshold=args.special_pixel_abs_threshold,
        min_valid_pixels=args.min_valid_pixels,
        valid_pixel_percent_threshold=args.valid_pixel_percent_threshold,
        invalid_pixel_radius=args.invalid_pixel_radius,
        ratio_test=args.ratio_test,
        max_features=args.max_features,
        sift_octave_layers=args.sift_octave_layers,
        sift_contrast_threshold=args.sift_contrast_threshold,
        sift_edge_threshold=args.sift_edge_threshold,
        sift_sigma=args.sift_sigma,
        crop_expand_pixels=args.crop_expand_pixels,
        min_overlap_size=args.min_overlap_size,
        use_parallel_cpu=args.use_parallel_cpu,
        num_worker_parallel_cpu=args.num_worker_parallel_cpu,
        enable_low_resolution_offset_estimation=args.enable_low_resolution_offset_estimation,
        low_resolution_level=args.low_resolution_level,
        write_match_visualization=args.write_match_visualization,
        match_visualization_output_path=args.match_visualization_output_path,
        match_visualization_output_dir=args.match_visualization_output_dir,
        match_visualization_scale=args.match_visualization_scale,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()