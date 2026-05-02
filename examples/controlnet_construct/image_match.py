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
Updated: 2026-04-23  Geng Xun batched low-resolution projected keypoints conversion so repeated offset estimation reuses opened cubes and projection objects instead of reopening the same DOM for every point.
Updated: 2026-04-23  Geng Xun replaced GDAL-based low-resolution DOM generation with ISIS reduce so coarse-offset cubes preserve projection-ready Mapping labels.
Updated: 2026-04-24  Geng Xun extracted reusable stereo-pair RANSAC filtering helpers into a dedicated module so image_match.py stays smaller while preserving the existing public API.
Updated: 2026-04-24  Geng Xun extracted low-resolution offset, match visualization, and tile-matching helpers into dedicated modules so image_match.py now focuses on configuration, orchestration, and CLI compatibility.
Updated: 2026-04-24  Geng Xun exposed the low-resolution projected-offset trimmed-mean fraction through the Python API, CLI, and config JSON while preserving the previous 5% default.
Updated: 2026-04-26  Geng Xun added selectable BF/FLANN SIFT descriptor matching plus low-resolution reprojection-error gating for coarse offset estimation.
Updated: 2026-04-27  Geng Xun added low-resolution retained-match and projected-offset magnitude gates so implausible coarse offsets fall back to zero.
Updated: 2026-05-01  Geng Xun added shell-print helpers and an early --print-config-default CLI probe for ImageMatch config defaults.
Updated: 2026-05-01  Geng Xun added configurable helper lookup order so shell wrappers can preserve legacy top-level config precedence where required.
Updated: 2026-05-02  Geng Xun added precomputed low-resolution DOM inputs so batch wrappers can reuse one reduced cube per DOM.
Updated: 2026-05-02  Geng Xun added CLI progress reporting for full-resolution tile matching without changing JSON stdout.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import TextIO, Literal

import cv2


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.dom_prepare import prepare_dom_pair_for_matching, write_pair_preparation_metadata
    from controlnet_construct.keypoints import Keypoint, KeypointFile, write_key_file
    import controlnet_construct.lowres_offset as _lowres_offset
    import controlnet_construct.match_visualization as _match_visualization
    from controlnet_construct.preprocess import validate_invalid_pixel_radius
    from controlnet_construct.runtime import bootstrap_runtime_environment
    import controlnet_construct.stereo_ransac as _stereo_ransac
    from controlnet_construct.tile_matching import (
        PairedTileWindow,
        DEFAULT_MATCHER_METHOD,
        TileMatchResult,
        TileMatchStats,
        TileMatchTask,
        _build_sift_detector,
        _build_tile_match_tasks,
        _keypoint_to_isis_coordinates,
        _matcher_diagnostics_for_method,
        _normalize_matcher_method,
        _paired_windows,
        _resolved_invalid_values_for_cube,
        _run_parallel_tile_match_tasks,
        _run_serial_tile_match_tasks,
    )
else:
    from .dom_prepare import prepare_dom_pair_for_matching, write_pair_preparation_metadata
    from .keypoints import Keypoint, KeypointFile, write_key_file
    from . import lowres_offset as _lowres_offset
    from . import match_visualization as _match_visualization
    from .preprocess import validate_invalid_pixel_radius
    from .runtime import bootstrap_runtime_environment
    from . import stereo_ransac as _stereo_ransac
    from .tile_matching import (
        PairedTileWindow,
        DEFAULT_MATCHER_METHOD,
        TileMatchResult,
        TileMatchStats,
        TileMatchTask,
        _build_sift_detector,
        _build_tile_match_tasks,
        _keypoint_to_isis_coordinates,
        _matcher_diagnostics_for_method,
        _normalize_matcher_method,
        _paired_windows,
        _resolved_invalid_values_for_cube,
        _run_parallel_tile_match_tasks,
        _run_serial_tile_match_tasks,
    )


bootstrap_runtime_environment()

import isis_pybind as ip


DEFAULT_NUM_WORKER_PARALLEL_CPU = 8
MAX_NUM_WORKER_PARALLEL_CPU = 4096
DEFAULT_LOW_RESOLUTION_LEVEL = 3
DEFAULT_LOW_RESOLUTION_TRIM_FRACTION_EACH_SIDE = _lowres_offset.DEFAULT_TRIM_FRACTION_EACH_SIDE
DEFAULT_LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT = _lowres_offset.DEFAULT_MIN_RETAINED_MATCH_COUNT
DEFAULT_LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS = _lowres_offset.DEFAULT_MAX_MEAN_PROJECTED_OFFSET_METERS


_run_command = _lowres_offset._run_command
_require_command = _lowres_offset._require_command
_validate_projection_ready_cube = _lowres_offset._validate_projection_ready_cube
_copy_precomputed_low_resolution_dom = _lowres_offset.copy_precomputed_low_resolution_dom
_low_resolution_pair_tag = _lowres_offset._low_resolution_pair_tag
_default_low_resolution_output_dir = _lowres_offset._default_low_resolution_output_dir
_projected_xy_from_keypoints_in_open_cube = _lowres_offset._projected_xy_from_keypoints_in_open_cube
_projected_xy_from_keypoints = _lowres_offset._projected_xy_from_keypoints
_projected_xy_from_keypoint = _lowres_offset._projected_xy_from_keypoint
_trimmed_mean = _lowres_offset._trimmed_mean

default_match_visualization_path = _match_visualization.default_match_visualization_path
write_stereo_pair_match_visualization = _match_visualization.write_stereo_pair_match_visualization
write_stereo_pair_match_visualization_from_key_files = _match_visualization.write_stereo_pair_match_visualization_from_key_files


class _TileProgressBar:
    def __init__(
        self,
        *,
        left_dom_path: str | Path,
        right_dom_path: str | Path,
        total_tiles: int,
        stream: TextIO | None = None,
        width: int = 30,
    ) -> None:
        self._left_dom_path = Path(left_dom_path)
        self._right_dom_path = Path(right_dom_path)
        self._total_tiles = max(0, int(total_tiles))
        self._stream = sys.stderr if stream is None else stream
        self._width = max(10, int(width))
        self._completed_tiles = 0
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        print(
            "[image-match] "
            f"{self._left_dom_path.name} ↔ {self._right_dom_path.name}: "
            f"{self._total_tiles} TILE(s) to process at full resolution.",
            file=self._stream,
            flush=True,
        )
        self._render()

    def update(self) -> None:
        if not self._started:
            self.start()
        self._completed_tiles = min(self._completed_tiles + 1, self._total_tiles)
        self._render()

    def finish(self) -> None:
        if not self._started:
            return
        print(file=self._stream, flush=True)

    def _render(self) -> None:
        if self._total_tiles <= 0:
            bar = "-" * self._width
            percent = 100.0
        else:
            percent = 100.0 * self._completed_tiles / self._total_tiles
            filled_width = int(round(self._width * self._completed_tiles / self._total_tiles))
            bar = "#" * filled_width + "-" * (self._width - filled_width)
        print(
            "\r[image-match] "
            f"[{bar}] {self._completed_tiles}/{self._total_tiles} TILE(s) "
            f"done ({percent:5.1f}%)",
            end="",
            file=self._stream,
            flush=True,
        )


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


def _parse_matcher_method(value: str) -> str:
    try:
        return _normalize_matcher_method(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _validate_low_resolution_max_mean_reprojection_error_pixels(value: float) -> float:
    resolved_value = float(value)
    if resolved_value < 0.0:
        raise ValueError("low_resolution_max_mean_reprojection_error_pixels must be >= 0.0.")
    return resolved_value


def _parse_low_resolution_max_mean_reprojection_error_pixels(value: str) -> float:
    try:
        return _validate_low_resolution_max_mean_reprojection_error_pixels(float(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _validate_low_resolution_trim_fraction_each_side(value: float) -> float:
    return _lowres_offset._validate_trim_fraction_each_side(value)


def _parse_low_resolution_trim_fraction_each_side(value: str) -> float:
    try:
        return _validate_low_resolution_trim_fraction_each_side(float(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _validate_low_resolution_min_retained_match_count(value: int) -> int:
    return _lowres_offset._validate_min_retained_match_count(value)


def _parse_low_resolution_min_retained_match_count(value: str) -> int:
    try:
        return _validate_low_resolution_min_retained_match_count(int(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _validate_low_resolution_max_mean_projected_offset_meters(value: float) -> float:
    return _lowres_offset._validate_max_mean_projected_offset_meters(value)


def _parse_low_resolution_max_mean_projected_offset_meters(value: str) -> float:
    try:
        return _validate_low_resolution_max_mean_projected_offset_meters(float(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


ConfigContainerOrder = Literal["image-match-first", "top-level-first"]


def _image_match_config_containers(
    payload: object,
    *,
    container_order: ConfigContainerOrder = "image-match-first",
) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        raise ValueError("image_match config JSON must decode to an object at the top level.")

    image_match_containers: list[dict[str, object]] = []
    for key in ("ImageMatch", "image_match", "imageMatch"):
        value = payload.get(key)
        if isinstance(value, dict):
            image_match_containers.append(value)

    if container_order == "top-level-first":
        return [payload, *image_match_containers]
    if container_order == "image-match-first":
        return [*image_match_containers, payload]
    raise ValueError(f"Unsupported ImageMatch config container order: {container_order}")


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


def load_image_match_defaults_from_config(
    config_path: str | Path,
    *,
    config_container_order: ConfigContainerOrder = "image-match-first",
) -> dict[str, object]:
    resolved_path = Path(config_path)
    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Config JSON not found: {resolved_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse config JSON {resolved_path}: {exc}") from exc

    containers = _image_match_config_containers(payload, container_order=config_container_order)
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
        (
            "matcher_method",
            ("matcher_method", "matcherMethod", "MatcherMethod"),
            lambda value: _normalize_matcher_method(str(value)),
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
            "low_resolution_trim_fraction_each_side",
            (
                "low_resolution_trim_fraction_each_side",
                "lowResolutionTrimFractionEachSide",
                "LowResolutionTrimFractionEachSide",
            ),
            lambda value: _validate_low_resolution_trim_fraction_each_side(float(value)),
        ),
        (
            "low_resolution_max_mean_reprojection_error_pixels",
            (
                "low_resolution_max_mean_reprojection_error_pixels",
                "lowResolutionMaxMeanReprojectionErrorPixels",
                "LowResolutionMaxMeanReprojectionErrorPixels",
            ),
            lambda value: _validate_low_resolution_max_mean_reprojection_error_pixels(float(value)),
        ),
        (
            "low_resolution_min_retained_match_count",
            (
                "low_resolution_min_retained_match_count",
                "lowResolutionMinRetainedMatchCount",
                "LowResolutionMinRetainedMatchCount",
            ),
            lambda value: _validate_low_resolution_min_retained_match_count(int(value)),
        ),
        (
            "low_resolution_max_mean_projected_offset_meters",
            (
                "low_resolution_max_mean_projected_offset_meters",
                "lowResolutionMaxMeanProjectedOffsetMeters",
                "LowResolutionMaxMeanProjectedOffsetMeters",
            ),
            lambda value: _validate_low_resolution_max_mean_projected_offset_meters(float(value)),
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


def format_image_match_default_for_shell(value: object) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        raise ValueError("List-valued ImageMatch defaults cannot be printed as a single shell scalar.")
    return str(value)


def print_image_match_config_default(
    config_path: str | Path,
    field_name: str,
    *,
    config_container_order: ConfigContainerOrder = "image-match-first",
) -> str:
    defaults = load_image_match_defaults_from_config(
        config_path,
        config_container_order=config_container_order,
    )
    if field_name not in defaults:
        return ""
    return format_image_match_default_for_shell(defaults[field_name])


def _create_low_resolution_dom(
    source_path: str | Path,
    output_path: str | Path,
    *,
    level: int,
) -> Path:
    return _lowres_offset.create_low_resolution_dom(
        source_path,
        output_path,
        level=level,
        run_command_func=_run_command,
        validate_projection_ready_cube_func=_validate_projection_ready_cube,
    )


def _validate_low_resolution_dom_pair_args(
    left_low_resolution_dom: str | Path | None,
    right_low_resolution_dom: str | Path | None,
) -> tuple[str | Path | None, str | Path | None]:
    if (left_low_resolution_dom is None) != (right_low_resolution_dom is None):
        raise ValueError("left_low_resolution_dom and right_low_resolution_dom must be provided together.")
    return left_low_resolution_dom, right_low_resolution_dom


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
    return _stereo_ransac.filter_stereo_pair_keypoints_with_ransac(
        left_key_file,
        right_key_file,
        ransac_reproj_threshold=ransac_reproj_threshold,
        ransac_confidence=ransac_confidence,
        ransac_max_iters=ransac_max_iters,
        ransac_mode=ransac_mode,
        loose_keep_pixel_threshold=loose_keep_pixel_threshold,
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
    return _stereo_ransac.filter_stereo_pair_key_files_with_ransac(
        left_input,
        right_input,
        left_output,
        right_output,
        ransac_reproj_threshold=ransac_reproj_threshold,
        ransac_confidence=ransac_confidence,
        ransac_max_iters=ransac_max_iters,
        ransac_mode=ransac_mode,
        loose_keep_pixel_threshold=loose_keep_pixel_threshold,
    )


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
    matcher_method: str,
    ratio_test: float,
    max_features: int | None,
    sift_octave_layers: int,
    sift_contrast_threshold: float,
    sift_edge_threshold: float,
    sift_sigma: float,
    low_resolution_trim_fraction_each_side: float,
    low_resolution_max_mean_reprojection_error_pixels: float = 3.0,
    low_resolution_min_retained_match_count: int = DEFAULT_LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT,
    low_resolution_max_mean_projected_offset_meters: float = DEFAULT_LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS,
    left_low_resolution_dom: str | Path | None = None,
    right_low_resolution_dom: str | Path | None = None,
    match_dom_pair_func=None,
    filter_stereo_pair_keypoints_with_ransac_func=None,
    write_stereo_pair_match_visualization_func=None,
    require_command_func=None,
    create_low_resolution_dom_func=None,
    copy_precomputed_low_resolution_dom_func=None,
) -> dict[str, object]:
    if match_dom_pair_func is None:
        match_dom_pair_func = match_dom_pair
    if filter_stereo_pair_keypoints_with_ransac_func is None:
        filter_stereo_pair_keypoints_with_ransac_func = filter_stereo_pair_keypoints_with_ransac
    if write_stereo_pair_match_visualization_func is None:
        write_stereo_pair_match_visualization_func = write_stereo_pair_match_visualization
    if require_command_func is None:
        require_command_func = _require_command
    if create_low_resolution_dom_func is None:
        create_low_resolution_dom_func = _create_low_resolution_dom
    if copy_precomputed_low_resolution_dom_func is None:
        copy_precomputed_low_resolution_dom_func = _copy_precomputed_low_resolution_dom

    return _lowres_offset.estimate_low_resolution_projected_offset(
        left_dom_path,
        right_dom_path,
        enabled=enabled,
        low_resolution_level=low_resolution_level,
        low_resolution_output_dir=low_resolution_output_dir,
        band=band,
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
        matcher_method=matcher_method,
        sift_octave_layers=sift_octave_layers,
        sift_contrast_threshold=sift_contrast_threshold,
        sift_edge_threshold=sift_edge_threshold,
        sift_sigma=sift_sigma,
        trim_fraction_each_side=low_resolution_trim_fraction_each_side,
        low_resolution_max_mean_reprojection_error_pixels=low_resolution_max_mean_reprojection_error_pixels,
        low_resolution_min_retained_match_count=low_resolution_min_retained_match_count,
        low_resolution_max_mean_projected_offset_meters=low_resolution_max_mean_projected_offset_meters,
        left_precomputed_low_resolution_dom=left_low_resolution_dom,
        right_precomputed_low_resolution_dom=right_low_resolution_dom,
        match_dom_pair_func=match_dom_pair_func,
        filter_stereo_pair_keypoints_with_ransac_func=filter_stereo_pair_keypoints_with_ransac_func,
        write_stereo_pair_match_visualization_func=write_stereo_pair_match_visualization_func,
        require_command_func=require_command_func,
        create_low_resolution_dom_func=create_low_resolution_dom_func,
        copy_precomputed_low_resolution_dom_func=copy_precomputed_low_resolution_dom_func,
    )


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
    matcher_method: str = DEFAULT_MATCHER_METHOD,
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
    low_resolution_trim_fraction_each_side: float = DEFAULT_LOW_RESOLUTION_TRIM_FRACTION_EACH_SIDE,
    low_resolution_max_mean_reprojection_error_pixels: float = 3.0,
    low_resolution_min_retained_match_count: int = DEFAULT_LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT,
    low_resolution_max_mean_projected_offset_meters: float = DEFAULT_LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS,
    low_resolution_output_dir: str | Path | None = None,
    left_low_resolution_dom: str | Path | None = None,
    right_low_resolution_dom: str | Path | None = None,
    show_progress: bool = False,
) -> tuple[KeypointFile, KeypointFile, dict[str, object]]:
    left_cube = ip.Cube()
    right_cube = ip.Cube()
    left_cube.open(str(left_dom_path), "r")
    right_cube.open(str(right_dom_path), "r")

    try:
        resolved_valid_pixel_percent_threshold = _validate_valid_pixel_percent_threshold(valid_pixel_percent_threshold)
        resolved_num_worker_parallel_cpu = _validate_num_worker_parallel_cpu(num_worker_parallel_cpu)
        resolved_invalid_pixel_radius = validate_invalid_pixel_radius(invalid_pixel_radius)
        resolved_matcher_method = _normalize_matcher_method(matcher_method)
        resolved_low_resolution_level = _validate_low_resolution_level(low_resolution_level)
        resolved_low_resolution_trim_fraction_each_side = _validate_low_resolution_trim_fraction_each_side(
            low_resolution_trim_fraction_each_side
        )
        resolved_low_resolution_max_mean_reprojection_error_pixels = _validate_low_resolution_max_mean_reprojection_error_pixels(
            low_resolution_max_mean_reprojection_error_pixels
        )
        resolved_low_resolution_min_retained_match_count = _validate_low_resolution_min_retained_match_count(
            low_resolution_min_retained_match_count
        )
        resolved_low_resolution_max_mean_projected_offset_meters = _validate_low_resolution_max_mean_projected_offset_meters(
            low_resolution_max_mean_projected_offset_meters
        )
        resolved_left_low_resolution_dom, resolved_right_low_resolution_dom = _validate_low_resolution_dom_pair_args(
            left_low_resolution_dom,
            right_low_resolution_dom,
        )
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
            matcher_method=resolved_matcher_method,
            ratio_test=ratio_test,
            max_features=max_features,
            sift_octave_layers=sift_octave_layers,
            sift_contrast_threshold=sift_contrast_threshold,
            sift_edge_threshold=sift_edge_threshold,
            sift_sigma=sift_sigma,
            low_resolution_trim_fraction_each_side=resolved_low_resolution_trim_fraction_each_side,
            low_resolution_max_mean_reprojection_error_pixels=resolved_low_resolution_max_mean_reprojection_error_pixels,
            low_resolution_min_retained_match_count=resolved_low_resolution_min_retained_match_count,
            low_resolution_max_mean_projected_offset_meters=resolved_low_resolution_max_mean_projected_offset_meters,
            left_low_resolution_dom=resolved_left_low_resolution_dom,
            right_low_resolution_dom=resolved_right_low_resolution_dom,
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
                progress_bar = (
                    _TileProgressBar(
                        left_dom_path=left_dom_path,
                        right_dom_path=right_dom_path,
                        total_tiles=len(windows),
                    )
                    if show_progress
                    else None
                )
                if progress_bar is not None:
                    progress_bar.start()
                if parallel_cpu_requested and len(windows) > 1:
                    candidate_worker_count = min(len(windows), resolved_num_worker_parallel_cpu)
                    if candidate_worker_count > 1:
                        try:
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
                                    matcher_method=resolved_matcher_method,
                                    ratio_test=ratio_test,
                                    max_features=max_features,
                                    sift_octave_layers=sift_octave_layers,
                                    sift_contrast_threshold=sift_contrast_threshold,
                                    sift_edge_threshold=sift_edge_threshold,
                                    sift_sigma=sift_sigma,
                                ),
                                max_workers=candidate_worker_count,
                                progress_callback=progress_bar.update if progress_bar is not None else None,
                            )
                        finally:
                            if progress_bar is not None:
                                progress_bar.finish()
                        parallel_cpu_used = True
                        parallel_cpu_backend = "process_pool"
                        parallel_cpu_worker_count = candidate_worker_count
                    else:
                        try:
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
                                matcher_method=resolved_matcher_method,
                                ratio_test=ratio_test,
                                max_features=max_features,
                                sift_octave_layers=sift_octave_layers,
                                sift_contrast_threshold=sift_contrast_threshold,
                                sift_edge_threshold=sift_edge_threshold,
                                sift_sigma=sift_sigma,
                                progress_callback=progress_bar.update if progress_bar is not None else None,
                            )
                        finally:
                            if progress_bar is not None:
                                progress_bar.finish()
                        parallel_cpu_worker_count = 1
                else:
                    try:
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
                            matcher_method=resolved_matcher_method,
                            ratio_test=ratio_test,
                            max_features=max_features,
                            sift_octave_layers=sift_octave_layers,
                            sift_contrast_threshold=sift_contrast_threshold,
                            sift_edge_threshold=sift_edge_threshold,
                            sift_sigma=sift_sigma,
                            progress_callback=progress_bar.update if progress_bar is not None else None,
                        )
                    finally:
                        if progress_bar is not None:
                            progress_bar.finish()
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
            "matcher_method_requested": resolved_matcher_method,
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
            "low_resolution_trim_fraction_each_side": resolved_low_resolution_trim_fraction_each_side,
            "low_resolution_max_mean_reprojection_error_pixels": resolved_low_resolution_max_mean_reprojection_error_pixels,
            "low_resolution_min_retained_match_count": resolved_low_resolution_min_retained_match_count,
            "low_resolution_max_mean_projected_offset_meters": resolved_low_resolution_max_mean_projected_offset_meters,
            "left_precomputed_low_resolution_dom": str(resolved_left_low_resolution_dom) if resolved_left_low_resolution_dom is not None else None,
            "right_precomputed_low_resolution_dom": str(resolved_right_low_resolution_dom) if resolved_right_low_resolution_dom is not None else None,
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
            "matcher": {
                "matcher_method_requested": resolved_matcher_method,
                **_matcher_diagnostics_for_method(resolved_matcher_method),
                "ratio_test": ratio_test,
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
    show_progress: bool = False,
    **kwargs,
) -> dict[str, object]:
    if "low_resolution_output_dir" not in kwargs or kwargs.get("low_resolution_output_dir") is None:
        kwargs["low_resolution_output_dir"] = _default_low_resolution_output_dir(
            left_dom_path,
            right_dom_path,
            metadata_output=metadata_output,
            left_output_key=left_output_key,
        )
    left_key_file, right_key_file, summary = match_dom_pair(left_dom_path, right_dom_path, show_progress=show_progress, **kwargs)
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
            "matcher": summary["matcher"],
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
    parser.add_argument("--matcher-method", type=_parse_matcher_method, default=DEFAULT_MATCHER_METHOD, help="Descriptor matcher backend used after SIFT feature extraction. Supported values: bf, flann. Default: bf.")
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
    parser.add_argument("--low-resolution-trim-fraction-each-side", type=_parse_low_resolution_trim_fraction_each_side, default=DEFAULT_LOW_RESOLUTION_TRIM_FRACTION_EACH_SIDE, help=f"Fraction of low-resolution projected offset samples trimmed from each tail before averaging. Must be within [0.0, 0.5). Default: {DEFAULT_LOW_RESOLUTION_TRIM_FRACTION_EACH_SIDE}.")
    parser.add_argument("--low-resolution-max-mean-reprojection-error-pixels", type=_parse_low_resolution_max_mean_reprojection_error_pixels, default=3.0, help="Maximum allowed trimmed-mean low-resolution homography reprojection error, in pixels. Values above this threshold force low-resolution offset fallback to zero. Default: 3.0.")
    parser.add_argument("--low-resolution-min-retained-match-count", type=_parse_low_resolution_min_retained_match_count, default=DEFAULT_LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT, help=f"Minimum retained low-resolution RANSAC match count required before projected-offset statistics are trusted. Values below this threshold skip low-resolution statistics and force fallback to zero. Default: {DEFAULT_LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT}.")
    parser.add_argument("--low-resolution-max-mean-projected-offset-meters", type=_parse_low_resolution_max_mean_projected_offset_meters, default=DEFAULT_LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS, help="Maximum allowed magnitude of the mean low-resolution projected offset, in meters. Values above this threshold force fallback to zero. Set to 0 to disable this gate. Default: 0.0.")
    parser.add_argument("--left-low-resolution-dom", default=None, help="Optional precomputed low-resolution DOM cube for the left input. Must be provided together with --right-low-resolution-dom.")
    parser.add_argument("--right-low-resolution-dom", default=None, help="Optional precomputed low-resolution DOM cube for the right input. Must be provided together with --left-low-resolution-dom.")
    parser.add_argument("--num-worker-parallel-cpu", type=_parse_num_worker_parallel_cpu, default=DEFAULT_NUM_WORKER_PARALLEL_CPU, help=f"Maximum worker-process count used when CPU tile parallelism is enabled. Must be within [1, {MAX_NUM_WORKER_PARALLEL_CPU}]. Default: {DEFAULT_NUM_WORKER_PARALLEL_CPU}.")
    parser.add_argument("--use-parallel-cpu", dest="use_parallel_cpu", action="store_true", help="Enable CPU process-pool parallelism for tiled matching. Enabled by default.")
    parser.add_argument("--no-parallel-cpu", dest="use_parallel_cpu", action="store_false", help="Disable CPU process-pool parallelism and force serial tile matching.")
    parser.add_argument("--no-write-match-visualization", dest="write_match_visualization", action="store_false", help="Disable the default pre-RANSAC drawMatches PNG output written for the matched DOM pair.")
    parser.add_argument("--no-progress", dest="show_progress", action="store_false", help="Disable full-resolution tile progress output on stderr.")
    parser.add_argument("--match-visualization-output-path", default=None, help="Optional explicit output path for the pre-RANSAC drawMatches PNG written by the image-match stage.")
    parser.add_argument("--match-visualization-output-dir", default=None, help="Optional directory used when auto-naming the pre-RANSAC drawMatches PNG written by the image-match stage.")
    parser.add_argument("--match-visualization-scale", type=float, default=1.0 / 3.0, help="Image scale factor used when writing the pre-RANSAC drawMatches PNG. Defaults to 1/3 for a smaller preview.")
    parser.set_defaults(write_match_visualization=True, use_parallel_cpu=True, enable_low_resolution_offset_estimation=False, show_progress=True)
    if config_defaults:
        parser.set_defaults(**config_defaults)
    return parser


def main(argv: list[str] | None = None) -> None:
    resolved_argv = sys.argv[1:] if argv is None else list(argv)
    config_probe_parser = argparse.ArgumentParser(add_help=False)
    config_probe_parser.add_argument("--config", default=None)
    config_probe_parser.add_argument("--print-config-default", default=None)
    config_probe_parser.add_argument(
        "--print-config-default-container-order",
        choices=("image-match-first", "top-level-first"),
        default="image-match-first",
    )
    config_probe_args, _ = config_probe_parser.parse_known_args(resolved_argv)

    if config_probe_args.print_config_default is not None:
        if config_probe_args.config is None:
            config_probe_parser.error("--print-config-default requires --config")
        try:
            print(
                print_image_match_config_default(
                    config_probe_args.config,
                    config_probe_args.print_config_default,
                    config_container_order=config_probe_args.print_config_default_container_order,
                )
            )
        except ValueError as exc:
            config_probe_parser.error(str(exc))
        return

    config_defaults: dict[str, object] = {}
    if config_probe_args.config is not None:
        try:
            config_defaults = load_image_match_defaults_from_config(config_probe_args.config)
        except ValueError as exc:
            config_probe_parser.error(str(exc))

    parser = build_argument_parser(config_defaults=config_defaults)
    args = parser.parse_args(resolved_argv)
    try:
        _validate_low_resolution_dom_pair_args(args.left_low_resolution_dom, args.right_low_resolution_dom)
    except ValueError as exc:
        parser.error(str(exc))
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
        matcher_method=args.matcher_method,
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
        low_resolution_trim_fraction_each_side=args.low_resolution_trim_fraction_each_side,
        low_resolution_max_mean_reprojection_error_pixels=args.low_resolution_max_mean_reprojection_error_pixels,
        low_resolution_min_retained_match_count=args.low_resolution_min_retained_match_count,
        low_resolution_max_mean_projected_offset_meters=args.low_resolution_max_mean_projected_offset_meters,
        left_low_resolution_dom=args.left_low_resolution_dom,
        right_low_resolution_dom=args.right_low_resolution_dom,
        write_match_visualization=args.write_match_visualization,
        show_progress=args.show_progress,
        match_visualization_output_path=args.match_visualization_output_path,
        match_visualization_output_dir=args.match_visualization_output_dir,
        match_visualization_scale=args.match_visualization_scale,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
