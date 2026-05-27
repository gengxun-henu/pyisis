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
Updated: 2026-05-03  Geng Xun added optional tile-validity prefilter configuration, summaries, and metadata output.
Updated: 2026-05-03  Geng Xun wired image-match visualization preview options and low-resolution target-long-edge defaults.
Updated: 2026-05-05  Geng Xun added stdout tile-detail trimming plus optional full-result JSON output for quieter CLI runs.
Updated: 2026-05-08  Geng Xun added dynamic GPU batch config defaults and CLI options.
Updated: 2026-05-08  Geng Xun added a --no-gpu-dynamic-batch CLI opt-out.
Updated: 2026-05-08  Geng Xun wired dynamic GPU batch options into image-match execution.
Updated: 2026-05-08  Geng Xun corrected GPU tile-route backend diagnostics.
Updated: 2026-05-08  Geng Xun added GPU execution configuration summary fields.
Updated: 2026-05-08  Geng Xun aligned GPU batch defaults and backend reporting with effective GPU route support.
Updated: 2026-05-10  Geng Xun added a baseline ori-space matching entrypoint with superpoint dependency fail-fast checks.
Updated: 2026-05-10  Geng Xun threaded a minimal dom/ori image-space backend selector through tile-matching entrypoints.
Updated: 2026-05-10  Geng Xun added ORI pair-level `.key` export helpers and accepted the `superpoint` selector in CLI matcher choices.
Updated: 2026-05-14  Geng Xun added an optional adaptive-routing prepass that can select a pair-level initial matcher from low-resolution previews and record routing metadata.
Updated: 2026-05-14  Geng Xun wired adaptive fallback cascade execution through post-match quality gating and persisted cascade diagnostics.
Updated: 2026-05-16  Geng Xun added deep-match result import mode to convert manifest NPZ outputs back into `.key` files.
Updated: 2026-05-16  Geng Xun added named adaptive-routing profiles that expand to quality-gate thresholds in metadata.
Updated: 2026-05-19  Geng Xun routed adaptive texture-sparseness diagnostics through
    tile-window readers instead of full-band cube reads.
Updated: 2026-05-19  Geng Xun added shared deep matcher config path parsing, validation, and metadata recording.
Updated: 2026-05-19  Geng Xun resolved deep matcher runtime config and added matcher conflict checks.
Updated: 2026-05-20  Geng Xun added preset-aware adaptive routing config loading, route metadata, and deep preset cascade execution.
Updated: 2026-05-20  Geng Xun enriched export-mode deep-match manifests with per-task runtime-config provenance and environment metadata.
Updated: 2026-05-20  Geng Xun normalized config-relative adaptive-routing deep preset paths during config loading.
Updated: 2026-05-20  Geng Xun restored repo-root fallback when resolving adaptive-routing deep preset maps from config JSON.
Updated: 2026-05-20  Geng Xun reused deep preset matcher compatibility validation for routed initial and cascade configs.
Updated: 2026-05-27  Geng Xun added --opencv-num-threads CLI/config validation helpers and ImageMatch config alias parsing.
Updated: 2026-05-27  Geng Xun wired ISIS storage-tile block alignment through ImageMatch API, config, CLI, and metadata.
Updated: 2026-05-27  Geng Xun deferred storage-tile alignment until DOM preparation is ready.
Updated: 2026-05-27  Geng Xun recorded serial tile cache summaries in match metadata.
Updated: 2026-05-27  Geng Xun clarified worker-local parallel tile cache metadata when aggregate summaries are unavailable.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import TextIO, Literal

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore[assignment]


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.parameter_validation import parse_catalog_choice, parse_catalog_number
    from image_match.adaptive_routing import (
        DEFAULT_ADAPTIVE_ROUTING_PROFILE,
        SUPPORTED_ADAPTIVE_ROUTING_PROFILES,
        augment_pair_probe_sidecar_with_sparseness_lighting,
        build_pair_probe_sidecar,
        build_cascade_plan,
        compute_real_image_texture_probe,
        decide_post_match_action,
        evaluate_match_quality,
        normalize_adaptive_routing_profile,
        resolve_adaptive_routing_quality_profile,
        route_matcher_for_pair,
        route_matcher_for_pair_with_sparseness,
    )
    from image_match.lighting_difference import (
        SolarGeometryFieldMissing,
        compute_lighting_difference,
        lighting_summary_to_diagnostic_dict,
        read_solar_geometry_from_cube,
    )
    from image_match.texture_sparseness import (
        aggregate_pair_texture_sparseness,
        compute_image_texture_sparseness_from_reader,
        pair_summary_to_diagnostic_dict,
    )
    from image_match.tiling import TileWindow
    from image_match.dom_prepare import prepare_dom_pair_for_matching, write_pair_preparation_metadata
    from image_match.deep_match_manifest import (
        DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
        build_deep_match_pair_manifest,
        ensure_deep_match_workspace,
        read_deep_match_pair_manifest,
        read_deep_match_task_result,
        resolve_deep_match_workspace,
        write_deep_match_pair_manifest,
        write_deep_match_task_arrays,
    )
    from image_match.keypoints import Keypoint, KeypointFile, write_key_file
    import image_match.lowres_offset as _lowres_offset
    import image_match.match_visualization as _match_visualization
    from image_match.preprocess import summarize_valid_pixels, validate_invalid_pixel_radius
    from image_match.runtime import bootstrap_runtime_environment
    import image_match.stereo_ransac as _stereo_ransac
    from image_match.tile_block_alignment import (
        DEFAULT_TILE_BLOCK_ALIGNMENT_MODE,
        SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES,
        normalize_tile_block_alignment_mode,
        resolve_tile_aligned_block_config,
        storage_tile_shape_from_cube,
    )
    from image_match.tile_validity import (
        DEFAULT_TILE_VALIDITY_CELL_HEIGHT,
        DEFAULT_TILE_VALIDITY_CELL_WIDTH,
        default_tile_validity_cache_dir,
        ensure_dom_validity_index,
        prefilter_paired_windows_by_validity,
        validate_tile_validity_cell_size,
    )
    from image_match.tile_matching import (
        DEEP_MATCHER_METHODS,
        PairedTileWindow,
        DEFAULT_GPU_BATCH_SIZE,
        DEFAULT_MATCHER_METHOD,
        GpuSiftStats,
        TileMatchResult,
        TileMatchStats,
        TileMatchTask,
        _build_sift_detector,
        build_image_backend,
        _build_tile_match_tasks,
        _can_use_dedicated_gpu_tile_route,
        _full_image_window,
        _keypoint_to_isis_coordinates,
        _matcher_diagnostics_for_method,
        _normalize_matcher_method,
        _paired_windows,
        _read_cube_window,
        _resolved_invalid_values_for_cube,
        _run_parallel_tile_match_tasks,
        _run_serial_tile_match_tasks,
    )
    import image_match.tile_matching as tile_matching_module
else:
    from controlnet_construct.parameter_validation import parse_catalog_choice, parse_catalog_number
    from .adaptive_routing import (
        DEFAULT_ADAPTIVE_ROUTING_PROFILE,
        SUPPORTED_ADAPTIVE_ROUTING_PROFILES,
        augment_pair_probe_sidecar_with_sparseness_lighting,
        build_pair_probe_sidecar,
        build_cascade_plan,
        compute_real_image_texture_probe,
        decide_post_match_action,
        evaluate_match_quality,
        normalize_adaptive_routing_profile,
        resolve_adaptive_routing_quality_profile,
        route_matcher_for_pair,
        route_matcher_for_pair_with_sparseness,
    )
    from .lighting_difference import (
        SolarGeometryFieldMissing,
        compute_lighting_difference,
        lighting_summary_to_diagnostic_dict,
        read_solar_geometry_from_cube,
    )
    from .texture_sparseness import (
        aggregate_pair_texture_sparseness,
        compute_image_texture_sparseness_from_reader,
        pair_summary_to_diagnostic_dict,
    )
    from .tiling import TileWindow
    from .dom_prepare import prepare_dom_pair_for_matching, write_pair_preparation_metadata
    from .deep_match_manifest import (
        DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
        build_deep_match_pair_manifest,
        ensure_deep_match_workspace,
        read_deep_match_pair_manifest,
        read_deep_match_task_result,
        resolve_deep_match_workspace,
        write_deep_match_pair_manifest,
        write_deep_match_task_arrays,
    )
    from .keypoints import Keypoint, KeypointFile, write_key_file
    from . import lowres_offset as _lowres_offset
    from . import match_visualization as _match_visualization
    from .preprocess import summarize_valid_pixels, validate_invalid_pixel_radius
    from .runtime import bootstrap_runtime_environment
    from . import stereo_ransac as _stereo_ransac
    from .tile_block_alignment import (
        DEFAULT_TILE_BLOCK_ALIGNMENT_MODE,
        SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES,
        normalize_tile_block_alignment_mode,
        resolve_tile_aligned_block_config,
        storage_tile_shape_from_cube,
    )
    from .tile_validity import (
        DEFAULT_TILE_VALIDITY_CELL_HEIGHT,
        DEFAULT_TILE_VALIDITY_CELL_WIDTH,
        default_tile_validity_cache_dir,
        ensure_dom_validity_index,
        prefilter_paired_windows_by_validity,
        validate_tile_validity_cell_size,
    )
    from .tile_matching import (
        DEEP_MATCHER_METHODS,
        PairedTileWindow,
        DEFAULT_GPU_BATCH_SIZE,
        DEFAULT_MATCHER_METHOD,
        GpuSiftStats,
        TileMatchResult,
        TileMatchStats,
        TileMatchTask,
        _build_sift_detector,
        build_image_backend,
        _build_tile_match_tasks,
        _can_use_dedicated_gpu_tile_route,
        _full_image_window,
        _keypoint_to_isis_coordinates,
        _matcher_diagnostics_for_method,
        _normalize_matcher_method,
        _paired_windows,
        _read_cube_window,
        _resolved_invalid_values_for_cube,
        _run_parallel_tile_match_tasks,
        _run_serial_tile_match_tasks,
    )
    from . import tile_matching as tile_matching_module


bootstrap_runtime_environment()

import isis_pybind as ip


DEFAULT_NUM_WORKER_PARALLEL_CPU = 8
MAX_NUM_WORKER_PARALLEL_CPU = 4096
DEFAULT_LOW_RESOLUTION_LEVEL = 3
DEFAULT_LOW_RESOLUTION_TRIM_FRACTION_EACH_SIDE = _lowres_offset.DEFAULT_TRIM_FRACTION_EACH_SIDE
DEFAULT_LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT = _lowres_offset.DEFAULT_MIN_RETAINED_MATCH_COUNT
DEFAULT_LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS = _lowres_offset.DEFAULT_MAX_MEAN_PROJECTED_OFFSET_METERS
DEFAULT_ENABLE_ADAPTIVE_ROUTING = False
DEFAULT_DEEP_MATCH_MODE = "direct"
SUPPORTED_DEEP_MATCH_MODES = ("direct", "export", "import")


_run_command = _lowres_offset._run_command
_require_command = _lowres_offset._require_command
_validate_projection_ready_cube = _lowres_offset._validate_projection_ready_cube
_copy_precomputed_low_resolution_dom = _lowres_offset.copy_precomputed_low_resolution_dom
_reduce_level_for_pair_target_long_edge = _lowres_offset.reduce_level_for_pair_target_long_edge
_low_resolution_pair_tag = _lowres_offset._low_resolution_pair_tag
_default_low_resolution_output_dir = _lowres_offset._default_low_resolution_output_dir
_projected_xy_from_keypoints_in_open_cube = _lowres_offset._projected_xy_from_keypoints_in_open_cube
_projected_xy_from_keypoints = _lowres_offset._projected_xy_from_keypoints
_projected_xy_from_keypoint = _lowres_offset._projected_xy_from_keypoint
_trimmed_mean = _lowres_offset._trimmed_mean

default_match_visualization_path = _match_visualization.default_match_visualization_path
write_stereo_pair_match_visualization = _match_visualization.write_stereo_pair_match_visualization
write_stereo_pair_match_visualization_from_key_files = _match_visualization.write_stereo_pair_match_visualization_from_key_files
DEFAULT_MATCH_VISUALIZATION_MODE = _match_visualization.DEFAULT_VISUALIZATION_MODE
DEFAULT_MEMORY_PROFILE = _match_visualization.DEFAULT_MEMORY_PROFILE
DEFAULT_PREVIEW_CROP_MARGIN_PIXELS = _match_visualization.DEFAULT_PREVIEW_CROP_MARGIN_PIXELS
DEFAULT_PREVIEW_CACHE_SOURCE = _match_visualization.DEFAULT_PREVIEW_CACHE_SOURCE
SUPPORTED_VISUALIZATION_MODES = _match_visualization.SUPPORTED_VISUALIZATION_MODES
SUPPORTED_MEMORY_PROFILES = _match_visualization.SUPPORTED_MEMORY_PROFILES
SUPPORTED_PREVIEW_CACHE_SOURCES = _match_visualization.SUPPORTED_PREVIEW_CACHE_SOURCES


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


def _validate_opencv_num_threads(value: int | None) -> int | None:
    if value is None:
        return None
    resolved_value = int(value)
    if resolved_value < 1:
        raise ValueError("opencv_num_threads must be >= 1.")
    return resolved_value


def _parse_opencv_num_threads(value: str) -> int:
    try:
        return _validate_opencv_num_threads(int(value))
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("opencv_num_threads must be an integer >= 1.") from exc


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


def _format_supported_values(values: tuple[str, ...]) -> str:
    return ", ".join(value.replace("_", "-") for value in values)


def _normalize_visualization_mode(value: object) -> str:
    return _match_visualization.resolve_visualization_options(visualization_mode=str(value)).visualization_mode


def _normalize_memory_profile(value: object) -> str:
    return _match_visualization.resolve_visualization_options(memory_profile=str(value)).memory_profile


def _normalize_preview_cache_source(value: object) -> str:
    return _match_visualization.resolve_visualization_options(preview_cache_source=str(value)).preview_cache_source


def _parse_visualization_mode(value: str) -> str:
    try:
        return parse_catalog_choice("visualization_mode", value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_memory_profile(value: str) -> str:
    try:
        return parse_catalog_choice("memory_profile", value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_preview_cache_source(value: str) -> str:
    try:
        return parse_catalog_choice("preview_cache_source", value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_adaptive_routing_profile(value: str) -> str:
    try:
        return parse_catalog_choice("adaptive_routing_profile", value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_tile_block_alignment_mode(value: str) -> str:
    try:
        return normalize_tile_block_alignment_mode(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _validate_low_resolution_matching_target_long_edge(value: int) -> int:
    resolved_value = int(value)
    if resolved_value <= 0:
        raise ValueError("low_resolution_matching_target_long_edge must be positive.")
    return resolved_value


def _parse_low_resolution_matching_target_long_edge(value: str) -> int:
    try:
        return _validate_low_resolution_matching_target_long_edge(int(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_invalid_pixel_radius(value: str) -> int:
    try:
        return validate_invalid_pixel_radius(int(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_tile_validity_cell_size(value: str, *, field_name: str) -> int:
    try:
        return validate_tile_validity_cell_size(int(value), field_name=field_name)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_matcher_method(value: str) -> str:
    try:
        return parse_catalog_choice("matcher_method", value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _normalize_deep_match_mode(value: object) -> str:
    normalized = str(value).strip().lower().replace("-", "_")
    if normalized not in SUPPORTED_DEEP_MATCH_MODES:
        raise ValueError(
            f"deep_match_mode must be one of {SUPPORTED_DEEP_MATCH_MODES}."
        )
    return normalized


def _parse_deep_match_mode(value: str) -> str:
    try:
        return parse_catalog_choice("deep_match_mode", value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _load_deep_match_config(config_path: str | Path) -> dict[str, object]:
    from controlnet_construct.deep_match_config import load_deep_match_config

    return load_deep_match_config(config_path)


def _resolve_deep_match_runtime_config(config_path: str | Path):
    from controlnet_construct.deep_match_config import resolve_deep_match_runtime_config

    return resolve_deep_match_runtime_config(config_path)


def _resolve_match_preset_path(raw_path: str | Path, *, config_path: str | Path | None = None) -> Path:
    from controlnet_construct.match_preset_config import resolve_match_preset_path

    raw = Path(raw_path).expanduser()
    if config_path is None:
        if raw.is_absolute():
            return raw.resolve()
        caller_relative = raw.resolve()
        if caller_relative.exists():
            return caller_relative

    return resolve_match_preset_path(
        raw,
        config_path=config_path,
        repo_root=Path(__file__).resolve().parents[2],
    )


def _resolve_match_preset_defaults(raw_path: str | Path, *, config_path: str | Path | None = None) -> dict[str, object]:
    from controlnet_construct.match_preset_config import resolve_match_preset_runtime_config

    preset_path = _resolve_match_preset_path(raw_path, config_path=config_path)
    return dict(resolve_match_preset_runtime_config(preset_path).image_match_defaults)


class _MatchPresetPathAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            preset_path = _resolve_match_preset_path(values)
        except ValueError as exc:
            raise argparse.ArgumentError(self, str(exc)) from exc
        setattr(namespace, self.dest, str(preset_path))


_MATCH_PRESET_DEFAULT_OPTION_NAMES: dict[str, tuple[str, ...]] = {
    "matcher_method": ("--matcher-method",),
    "deep_match_config_path": ("--deep-match-config-path",),
    "ratio_test": ("--ratio-test",),
    "max_features": ("--max-features",),
    "sift_octave_layers": ("--sift-octave-layers",),
    "sift_contrast_threshold": ("--sift-contrast-threshold",),
    "sift_edge_threshold": ("--sift-edge-threshold",),
    "sift_sigma": ("--sift-sigma",),
}


def _argv_has_option(argv: list[str], option_name: str) -> bool:
    return any(arg == option_name or arg.startswith(f"{option_name}=") for arg in argv)


def _argv_has_any_option(argv: list[str], option_names: tuple[str, ...]) -> bool:
    return any(_argv_has_option(argv, option_name) for option_name in option_names)


class _ImageMatchArgumentParser(argparse.ArgumentParser):
    def parse_known_args(self, args=None, namespace=None):
        resolved_args = sys.argv[1:] if args is None else list(args)
        parsed, extras = super().parse_known_args(args, namespace)
        match_preset_path = getattr(parsed, "match_preset_path", None)
        if match_preset_path not in (None, ""):
            try:
                preset_defaults = _resolve_match_preset_defaults(match_preset_path)
            except ValueError as exc:
                self.error(str(exc))
            for key, value in preset_defaults.items():
                option_names = _MATCH_PRESET_DEFAULT_OPTION_NAMES.get(key, ())
                if option_names and _argv_has_any_option(resolved_args, option_names):
                    continue
                setattr(parsed, key, value)
        return parsed, extras


def _runtime_config_to_metadata(runtime_config: object | None) -> dict[str, object] | None:
    if runtime_config is None:
        return None
    return asdict(runtime_config)


def _resolve_matcher_method_with_deep_config(
    *,
    requested_matcher_method: str,
    deep_match_runtime_config: object | None,
) -> str:
    if deep_match_runtime_config is None:
        return requested_matcher_method

    config_matcher_method = _normalize_matcher_method(getattr(deep_match_runtime_config, "matcher_method"))
    if (
        requested_matcher_method in DEEP_MATCHER_METHODS
        and config_matcher_method in DEEP_MATCHER_METHODS
        and requested_matcher_method != config_matcher_method
    ):
        raise ValueError(
            f"matcher_method '{requested_matcher_method}' conflicts with "
            f"deep_match_config matcher.method '{config_matcher_method}'. "
            "Use matching values or remove one override."
        )
    if requested_matcher_method == DEFAULT_MATCHER_METHOD and config_matcher_method in DEEP_MATCHER_METHODS:
        return config_matcher_method
    return requested_matcher_method


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


def _coerce_string_mapping(value: object, *, field_name: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} in config JSON must be an object.")
    return {
        str(key).strip(): str(item)
        for key, item in value.items()
        if key not in (None, "") and item not in (None, "")
    }


def _resolve_config_relative_string_mapping(mapping: dict[str, str], *, config_path: str | Path) -> dict[str, str]:
    config_dir = Path(config_path).parent
    repo_root = Path(__file__).resolve().parents[2]
    resolved_mapping: dict[str, str] = {}
    for key, value in mapping.items():
        resolved_value = Path(value).expanduser()
        if resolved_value.is_absolute():
            resolved_mapping[key] = str(resolved_value)
            continue

        config_relative_candidate = config_dir / resolved_value
        if config_relative_candidate.exists():
            resolved_value = config_relative_candidate
        else:
            resolved_value = repo_root / resolved_value
        resolved_mapping[key] = str(resolved_value)
    return resolved_mapping


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
        (
            "tile_block_alignment_mode",
            ("tile_block_alignment_mode", "tileBlockAlignmentMode", "TileBlockAlignmentMode"),
            lambda value: normalize_tile_block_alignment_mode(value),
        ),
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
            "enable_tile_validity_prefilter",
            ("enable_tile_validity_prefilter", "enableTileValidityPrefilter", "EnableTileValidityPrefilter"),
            lambda value: _coerce_config_bool(value, field_name="enable_tile_validity_prefilter"),
        ),
        (
            "tile_validity_cache_dir",
            ("tile_validity_cache_dir", "tileValidityCacheDir", "TileValidityCacheDir"),
            lambda value: str(value),
        ),
        (
            "tile_validity_cell_width",
            ("tile_validity_cell_width", "tileValidityCellWidth", "TileValidityCellWidth"),
            lambda value: validate_tile_validity_cell_size(int(value), field_name="tile_validity_cell_width"),
        ),
        (
            "tile_validity_cell_height",
            ("tile_validity_cell_height", "tileValidityCellHeight", "TileValidityCellHeight"),
            lambda value: validate_tile_validity_cell_size(int(value), field_name="tile_validity_cell_height"),
        ),
        (
            "match_preset_path",
            ("match_preset_path", "matchPresetPath", "MatchPresetPath"),
            lambda value: str(value),
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
            "enable_adaptive_routing",
            ("enable_adaptive_routing", "enableAdaptiveRouting", "EnableAdaptiveRouting"),
            lambda value: _coerce_config_bool(value, field_name="enable_adaptive_routing"),
        ),
        (
            "adaptive_routing_profile",
            ("adaptive_routing_profile", "adaptiveRoutingProfile", "AdaptiveRoutingProfile"),
            lambda value: normalize_adaptive_routing_profile(value),
        ),
        (
            "adaptive_routing_deep_presets",
            ("adaptive_routing_deep_presets", "adaptiveRoutingDeepPresets", "AdaptiveRoutingDeepPresets"),
            lambda value: _resolve_config_relative_string_mapping(
                _coerce_string_mapping(value, field_name="adaptive_routing_deep_presets"),
                config_path=resolved_path,
            ),
        ),
        (
            "deep_match_mode",
            ("deep_match_mode", "deepMatchMode", "DeepMatchMode"),
            lambda value: _normalize_deep_match_mode(value),
        ),
        (
            "deep_match_temp_root_dir",
            ("deep_match_temp_root_dir", "deepMatchTempRootDir", "DeepMatchTempRootDir"),
            lambda value: str(value),
        ),
        (
            "deep_match_manifest",
            ("deep_match_manifest", "deepMatchManifest", "DeepMatchManifest"),
            lambda value: str(value),
        ),
        (
            "deep_match_config_path",
            (
                "deep_match_config_path",
                "deepMatchConfigPath",
                "DeepMatchConfigPath",
                "deep_matcher_config_path",
                "deepMatcherConfigPath",
                "DeepMatcherConfigPath",
            ),
            lambda value: str(value),
        ),
        (
            "low_resolution_level",
            ("low_resolution_level", "lowResolutionLevel", "LowResolutionLevel"),
            lambda value: _validate_low_resolution_level(int(value)),
        ),
        (
            "low_resolution_matching_target_long_edge",
            (
                "low_resolution_matching_target_long_edge",
                "lowResolutionMatchingTargetLongEdge",
                "LowResolutionMatchingTargetLongEdge",
            ),
            lambda value: _validate_low_resolution_matching_target_long_edge(int(value)),
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
            "opencv_num_threads",
            ("opencv_num_threads", "opencvNumThreads", "OpenCVNumThreads"),
            lambda value: _validate_opencv_num_threads(int(value)),
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
        (
            "visualization_mode",
            ("visualization_mode", "visualizationMode", "VisualizationMode"),
            lambda value: _normalize_visualization_mode(value),
        ),
        (
            "memory_profile",
            ("memory_profile", "memoryProfile", "MemoryProfile"),
            lambda value: _normalize_memory_profile(value),
        ),
        (
            "visualization_target_long_edge",
            ("visualization_target_long_edge", "visualizationTargetLongEdge", "VisualizationTargetLongEdge"),
            lambda value: _match_visualization.resolve_visualization_options(
                visualization_target_long_edge=int(value)
            ).visualization_target_long_edge,
        ),
        (
            "max_preview_pixels",
            ("max_preview_pixels", "maxPreviewPixels", "MaxPreviewPixels"),
            lambda value: _match_visualization.resolve_visualization_options(
                max_preview_pixels=int(value)
            ).max_preview_pixels,
        ),
        (
            "preview_crop_margin_pixels",
            ("preview_crop_margin_pixels", "previewCropMarginPixels", "PreviewCropMarginPixels"),
            lambda value: _match_visualization.resolve_visualization_options(
                preview_crop_margin_pixels=int(value)
            ).preview_crop_margin_pixels,
        ),
        (
            "preview_cache_dir",
            ("preview_cache_dir", "previewCacheDir", "PreviewCacheDir"),
            lambda value: str(value),
        ),
        (
            "preview_cache_source",
            ("preview_cache_source", "previewCacheSource", "PreviewCacheSource"),
            lambda value: _normalize_preview_cache_source(value),
        ),
        (
            "preview_force_regenerate",
            ("preview_force_regenerate", "previewForceRegenerate", "PreviewForceRegenerate"),
            lambda value: _coerce_config_bool(value, field_name="preview_force_regenerate"),
        ),
        (
            "preview_level",
            ("preview_level", "previewLevel", "PreviewLevel"),
            lambda value: _match_visualization.resolve_visualization_options(preview_level=int(value)).preview_level,
        ),
        (
            "use_tile_cache",
            ("use_tile_cache", "useTileCache", "UseTileCache"),
            lambda value: _coerce_config_bool(value, field_name="use_tile_cache"),
        ),
        (
            "omit_tile_details",
            ("omit_tile_details", "omitTileDetails", "OmitTileDetails"),
            lambda value: _coerce_config_bool(value, field_name="omit_tile_details"),
        ),
        (
            "tile_cache_max_mb",
            ("tile_cache_max_mb", "tileCacheMaxMb", "TileCacheMaxMb"),
            lambda value: int(value),
        ),
        (
            "adaptive_warmup_count",
            ("adaptive_warmup_count", "adaptiveWarmupCount", "AdaptiveWarmupCount"),
            lambda value: int(value),
        ),
        (
            "adaptive_throughput_threshold_mbps",
            ("adaptive_throughput_threshold_mbps", "adaptiveThroughputThresholdMbps", "AdaptiveThroughputThresholdMbps"),
            lambda value: float(value),
        ),
        (
            "adaptive_recheck_every",
            ("adaptive_recheck_every", "adaptiveRecheckEvery", "AdaptiveRecheckEvery"),
            lambda value: int(value),
        ),
        (
            "use_gpu",
            ("use_gpu", "useGpu", "UseGpu"),
            lambda value: _coerce_config_bool(value, field_name="use_gpu"),
        ),
        (
            "gpu_batch_size",
            ("gpu_batch_size", "gpuBatchSize", "GpuBatchSize"),
            lambda value: int(value),
        ),
        (
            "gpu_dynamic_batch",
            ("gpu_dynamic_batch", "gpuDynamicBatch", "GpuDynamicBatch"),
            lambda value: _coerce_config_bool(value, field_name="gpu_dynamic_batch"),
        ),
        (
            "gpu_min_batch_size",
            ("gpu_min_batch_size", "gpuMinBatchSize", "GpuMinBatchSize"),
            lambda value: int(value),
        ),
        (
            "gpu_max_batch_size",
            ("gpu_max_batch_size", "gpuMaxBatchSize", "GpuMaxBatchSize"),
            lambda value: int(value),
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
    match_preset_path = defaults.get("match_preset_path")
    if match_preset_path not in (None, ""):
        preset_defaults = _resolve_match_preset_defaults(
            str(match_preset_path),
            config_path=resolved_path,
        )
        defaults.update(preset_defaults)
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
        if field_name == "deep_matcher_config_path" and "deep_match_config_path" in defaults:
            return format_image_match_default_for_shell(defaults["deep_match_config_path"])
        return ""
    return format_image_match_default_for_shell(defaults[field_name])


def _stdout_result_payload(result: dict[str, object], *, omit_tile_details: bool) -> dict[str, object]:
    payload = dict(result)
    if omit_tile_details:
        payload.pop("tiles", None)
    return payload


def _write_json_output(output_path: str | Path, payload: object) -> str:
    resolved_output_path = Path(output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return str(resolved_output_path)


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


def _tile_execution_backend_summary(
    *,
    use_parallel_cpu: bool,
    use_gpu: bool,
    effective_gpu_tile_route: bool | None = None,
    candidate_window_count: int,
    resolved_num_worker_parallel_cpu: int,
) -> dict[str, object]:
    parallel_cpu_requested = bool(use_parallel_cpu)
    gpu_tile_route_used = bool(use_gpu) if effective_gpu_tile_route is None else bool(effective_gpu_tile_route)
    if candidate_window_count <= 0:
        return {
            "parallel_cpu_requested": parallel_cpu_requested,
            "num_worker_parallel_cpu": resolved_num_worker_parallel_cpu,
            "parallel_cpu_used": False,
            "parallel_cpu_backend": "serial",
            "parallel_cpu_worker_count": 0,
            "tile_match_backend": "serial",
        }

    if parallel_cpu_requested and candidate_window_count > 1:
        candidate_worker_count = min(candidate_window_count, resolved_num_worker_parallel_cpu)
        if candidate_worker_count > 1:
            if gpu_tile_route_used:
                return {
                    "parallel_cpu_requested": parallel_cpu_requested,
                    "num_worker_parallel_cpu": resolved_num_worker_parallel_cpu,
                    "parallel_cpu_used": False,
                    "parallel_cpu_backend": "gpu_tile_pipeline",
                    "parallel_cpu_worker_count": 0,
                    "tile_match_backend": "gpu_tile_pipeline",
                }
            return {
                "parallel_cpu_requested": parallel_cpu_requested,
                "num_worker_parallel_cpu": resolved_num_worker_parallel_cpu,
                "parallel_cpu_used": True,
                "parallel_cpu_backend": "process_pool_batched_cube_reuse",
                "parallel_cpu_worker_count": candidate_worker_count,
                "tile_match_backend": "process_pool_batched_cube_reuse",
            }

    return {
        "parallel_cpu_requested": parallel_cpu_requested,
        "num_worker_parallel_cpu": resolved_num_worker_parallel_cpu,
        "parallel_cpu_used": False,
        "parallel_cpu_backend": "serial",
        "parallel_cpu_worker_count": 1,
        "tile_match_backend": "serial",
    }


def _gpu_execution_summary(
    *,
    use_gpu: bool,
    gpu_effective: bool | None = None,
    gpu_batch_size: int,
    gpu_dynamic_batch: bool,
    gpu_min_batch_size: int,
    gpu_max_batch_size: int,
    gpu_stats: GpuSiftStats | None = None,
) -> dict[str, object]:
    effective_gpu = bool(use_gpu) if gpu_effective is None else bool(gpu_effective)
    if gpu_stats is not None:
        effective_gpu = effective_gpu and gpu_stats.gpu_batch_count > 0
    summary: dict[str, object] = {
        "requested": bool(use_gpu),
        "enabled": effective_gpu,
        "batch_size": int(gpu_batch_size),
        "dynamic_batch": bool(gpu_dynamic_batch),
        "min_batch_size": int(gpu_min_batch_size),
        "max_batch_size": int(gpu_max_batch_size),
    }
    if gpu_stats is not None:
        summary["runtime"] = {
            "gpu_batch_count": gpu_stats.gpu_batch_count,
            "gpu_pair_count": gpu_stats.gpu_pair_count,
            "cpu_fallback_pair_count": gpu_stats.cpu_fallback_pair_count,
            "gpu_failure_count": gpu_stats.gpu_failure_count,
            "batch_size_histogram": dict(gpu_stats.batch_size_histogram),
        }
    return summary


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


def _read_full_cube_band(cube: ip.Cube, *, band: int) -> np.ndarray:
    return _read_cube_window(
        cube,
        _full_image_window(cube.sample_count(), cube.line_count()),
        band=band,
    )


def _compute_texture_probe_from_cube_path(
    cube_path: str | Path,
    *,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
):
    cube = ip.Cube()
    cube.open(str(cube_path), "r")
    try:
        values = _read_full_cube_band(cube, band=band)
        resolved_invalid_values = _resolved_invalid_values_for_cube(cube, invalid_values)
        invalid_mask, _ = summarize_valid_pixels(
            values,
            invalid_values=resolved_invalid_values,
            special_pixel_abs_threshold=special_pixel_abs_threshold,
        )
        return compute_real_image_texture_probe(values, invalid_mask=invalid_mask)
    finally:
        if cube.is_open():
            cube.close()


def _compute_texture_sparseness_and_geometry_from_cube_path(
    cube_path: str | Path,
    *,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
):
    """Compute the texture-sparseness summary and best-effort solar geometry.

    Returns ``(ImageSparsenessSummary, SolarGeometry | None, error_reason | None)``.
    The solar geometry read is best-effort: a missing-field error is captured in
    ``error_reason`` and the geometry value is ``None``, so adaptive routing can
    still surface the sparseness diagnostics by themselves.
    """

    cube = ip.Cube()
    cube.open(str(cube_path), "r")
    try:
        resolved_invalid_values = _resolved_invalid_values_for_cube(cube, invalid_values)

        window_value_cache: dict[tuple[int, int, int, int], np.ndarray] = {}

        def read_window(start_x: int, start_y: int, width: int, height: int) -> np.ndarray:
            key = (int(start_x), int(start_y), int(width), int(height))
            values = _read_cube_window(
                cube,
                TileWindow(start_x=key[0], start_y=key[1], width=key[2], height=key[3]),
                band=band,
            )
            window_value_cache[key] = values
            return values

        def read_invalid_mask(start_x: int, start_y: int, width: int, height: int) -> np.ndarray:
            key = (int(start_x), int(start_y), int(width), int(height))
            values = window_value_cache.get(key)
            if values is None:
                values = read_window(*key)
            invalid_mask, _ = summarize_valid_pixels(
                values,
                invalid_values=resolved_invalid_values,
                special_pixel_abs_threshold=special_pixel_abs_threshold,
            )
            return invalid_mask

        sparseness_summary = compute_image_texture_sparseness_from_reader(
            image_width=cube.sample_count(),
            image_height=cube.line_count(),
            read_window=read_window,
            invalid_mask_reader=read_invalid_mask,
        )
        solar_geometry = None
        solar_error: str | None = None
        try:
            solar_geometry = read_solar_geometry_from_cube(cube)
        except SolarGeometryFieldMissing as exc:
            solar_error = str(exc)
        except Exception as exc:  # noqa: BLE001 - keep best-effort diagnostics
            solar_error = f"unexpected error reading solar geometry: {exc}"
        return sparseness_summary, solar_geometry, solar_error
    finally:
        if cube.is_open():
            cube.close()


def _resolve_adaptive_route_for_pair(
    *,
    enable_adaptive_routing: bool,
    requested_matcher_method: str,
    adaptive_routing_deep_presets: dict[str, str] | None,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    low_resolution_offset_summary: dict[str, object],
    left_low_resolution_dom: str | Path | None,
    right_low_resolution_dom: str | Path | None,
    image_space: str = "dom",
    left_source_path: str | Path | None = None,
    right_source_path: str | Path | None = None,
) -> tuple[str, dict[str, object] | None]:
    if not enable_adaptive_routing:
        return requested_matcher_method, None

    summary_left_preview = str(low_resolution_offset_summary.get("left_low_resolution_dom", "") or "")
    summary_right_preview = str(low_resolution_offset_summary.get("right_low_resolution_dom", "") or "")
    resolved_left_preview = summary_left_preview or (str(left_low_resolution_dom) if left_low_resolution_dom is not None else "")
    resolved_right_preview = summary_right_preview or (str(right_low_resolution_dom) if right_low_resolution_dom is not None else "")
    normalized_image_space = str(image_space or "dom").strip().lower()
    preview_source_type = "low_resolution_dom"
    if normalized_image_space == "ori" and (not resolved_left_preview or not resolved_right_preview):
        resolved_left_preview = str(left_source_path) if left_source_path is not None else ""
        resolved_right_preview = str(right_source_path) if right_source_path is not None else ""
        preview_source_type = "raw_original_cube"

    if not resolved_left_preview or not resolved_right_preview:
        return requested_matcher_method, {
            "enabled": True,
            "status": "skipped_missing_previews",
            "requested_matcher": requested_matcher_method,
            "selected_initial_matcher": requested_matcher_method,
            "selected_deep_match_config_path": None,
            "route_reason": (
                "Adaptive routing requires low-resolution preview DOMs for DOM-space matching "
                "or original cube paths for raw image-space matching."
            ),
            "reason": (
                "Adaptive routing requires low-resolution preview DOMs for DOM-space matching "
                "or original cube paths for raw image-space matching."
            ),
        }

    try:
        left_texture_probe = _compute_texture_probe_from_cube_path(
            resolved_left_preview,
            band=band,
            invalid_values=invalid_values,
            special_pixel_abs_threshold=special_pixel_abs_threshold,
        )
        right_texture_probe = _compute_texture_probe_from_cube_path(
            resolved_right_preview,
            band=band,
            invalid_values=invalid_values,
            special_pixel_abs_threshold=special_pixel_abs_threshold,
        )
        # Additive diagnostics: tile-level texture sparseness + solar
        # lighting-difference are computed best-effort and attached to the
        # sidecar without changing the legacy routing decision shape.
        sparseness_lighting_diagnostics: dict[str, object] = {}
        route_decision = route_matcher_for_pair(
            left_texture_probe=left_texture_probe,
            right_texture_probe=right_texture_probe,
        )
        try:
            left_sparseness, left_solar_geometry, left_solar_error = (
                _compute_texture_sparseness_and_geometry_from_cube_path(
                    resolved_left_preview,
                    band=band,
                    invalid_values=invalid_values,
                    special_pixel_abs_threshold=special_pixel_abs_threshold,
                )
            )
            right_sparseness, right_solar_geometry, right_solar_error = (
                _compute_texture_sparseness_and_geometry_from_cube_path(
                    resolved_right_preview,
                    band=band,
                    invalid_values=invalid_values,
                    special_pixel_abs_threshold=special_pixel_abs_threshold,
                )
            )
            pair_sparseness = aggregate_pair_texture_sparseness(left_sparseness, right_sparseness)
            sparseness_diagnostic = pair_summary_to_diagnostic_dict(pair_sparseness)

            lighting_diagnostic: dict[str, object] | None = None
            if left_solar_geometry is not None and right_solar_geometry is not None:
                lighting_summary = compute_lighting_difference(left_solar_geometry, right_solar_geometry)
                lighting_diagnostic = lighting_summary_to_diagnostic_dict(lighting_summary)
            else:
                lighting_diagnostic = {
                    "lighting_difference_score": None,
                    "reason": "solar geometry missing for at least one image",
                    "left_solar_geometry_error": left_solar_error,
                    "right_solar_geometry_error": right_solar_error,
                }

            sparseness_lighting_diagnostics = {
                "texture_sparseness": sparseness_diagnostic,
                "lighting_difference": lighting_diagnostic,
            }
            route_decision = route_matcher_for_pair_with_sparseness(
                pair_texture_sparseness=sparseness_diagnostic.get("pair_texture_sparseness"),
                lighting_difference_score=lighting_diagnostic.get("lighting_difference_score"),
                traditional_matcher=requested_matcher_method,
                adaptive_routing_deep_presets=adaptive_routing_deep_presets,
            )
        except Exception as diag_exc:  # noqa: BLE001 - keep diagnostics best-effort
            sparseness_lighting_diagnostics = {
                "diagnostics_error": str(diag_exc),
            }

        sidecar_payload = build_pair_probe_sidecar(
            left_texture_probe=left_texture_probe,
            right_texture_probe=right_texture_probe,
            route_decision=route_decision,
        )
        sparseness_diagnostic_for_sidecar = sparseness_lighting_diagnostics.get("texture_sparseness")
        lighting_diagnostic_for_sidecar = sparseness_lighting_diagnostics.get("lighting_difference")
        tile_diagnostics_for_sidecar = None
        if isinstance(sparseness_diagnostic_for_sidecar, dict):
            tile_diagnostics_for_sidecar = {
                "texture_sparseness": sparseness_diagnostic_for_sidecar,
                "lighting": {},
            }
        sidecar_payload = augment_pair_probe_sidecar_with_sparseness_lighting(
            sidecar_payload,
            pair_sparseness_summary=(
                sparseness_diagnostic_for_sidecar
                if isinstance(sparseness_diagnostic_for_sidecar, dict)
                else None
            ),
            lighting_difference_summary=(
                lighting_diagnostic_for_sidecar
                if isinstance(lighting_diagnostic_for_sidecar, dict)
                else None
            ),
            tile_diagnostics_summary=tile_diagnostics_for_sidecar,
        )
        return route_decision.initial_matcher, {
            "enabled": True,
            "status": "routed",
            "requested_matcher": requested_matcher_method,
            "selected_initial_matcher": route_decision.initial_matcher,
            "selected_deep_match_config_path": route_decision.deep_match_config_path,
            "route_confidence": route_decision.route_confidence,
            "route_reason": route_decision.route_reason,
            "reason": route_decision.route_reason,
            "preview_sources": {
                "left": resolved_left_preview,
                "right": resolved_right_preview,
                "source_type": preview_source_type,
            },
            "sidecar": sidecar_payload,
        }
    except Exception as exc:
        return requested_matcher_method, {
            "enabled": True,
            "status": "routing_failed",
            "requested_matcher": requested_matcher_method,
            "selected_initial_matcher": requested_matcher_method,
            "selected_deep_match_config_path": None,
            "route_confidence": None,
            "route_reason": str(exc),
            "reason": str(exc),
            "preview_sources": {
                "left": resolved_left_preview,
                "right": resolved_right_preview,
                "source_type": preview_source_type,
            },
        }


def _quality_report_for_tile_results(
    tile_results: list[TileMatchResult],
    *,
    candidate_window_count: int,
    quality_gate: dict[str, object],
):
    total_match_count = sum(int(result.stats.match_count) for result in tile_results)
    inlier_count = sum(len(result.left_points) for result in tile_results)
    matched_tile_count = sum(1 for result in tile_results if result.stats.status == "matched")
    coverage = 0.0 if candidate_window_count <= 0 else matched_tile_count / float(candidate_window_count)
    residual_summary = {
        "count": inlier_count,
        "mean": 0.0,
        "median": 0.0,
        "p95": 0.0,
        "max": 0.0,
    }
    return evaluate_match_quality(
        inlier_count=inlier_count,
        total_match_count=total_match_count,
        coverage=coverage,
        residual_summary=residual_summary,
        min_inlier_count=int(quality_gate["min_inlier_count"]),
        min_inlier_ratio=float(quality_gate["min_inlier_ratio"]),
        min_coverage=float(quality_gate["min_coverage"]),
        max_mean_residual=float(quality_gate["max_mean_residual"]),
        max_p95_residual=float(quality_gate["max_p95_residual"]),
    )


def _default_deep_match_temp_root_dir(
    *,
    metadata_output: str | Path | None = None,
    left_output_key: str | Path | None = None,
) -> Path:
    if metadata_output is not None:
        return Path(metadata_output).expanduser().resolve().parent / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME
    if left_output_key is not None:
        return Path(left_output_key).expanduser().resolve().parent / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME
    return Path.cwd() / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME


def _export_tile_summary_from_payload(payload: object) -> TileMatchStats:
    local_window = payload.local_window
    left_window = payload.left_window
    right_window = payload.right_window
    return TileMatchStats(
        local_start_x=local_window.start_x,
        local_start_y=local_window.start_y,
        width=local_window.width,
        height=local_window.height,
        left_start_x=left_window.start_x,
        left_start_y=left_window.start_y,
        right_start_x=right_window.start_x,
        right_start_y=right_window.start_y,
        left_valid_pixel_count=payload.left_valid_pixel_count,
        right_valid_pixel_count=payload.right_valid_pixel_count,
        left_valid_pixel_ratio=payload.left_valid_pixel_ratio,
        right_valid_pixel_ratio=payload.right_valid_pixel_ratio,
        left_feature_count=0,
        right_feature_count=0,
        match_count=0,
        status="exported_for_deep_learning",
    )


def _export_deep_match_pair_tasks(
    *,
    left_dom_path: str | Path,
    right_dom_path: str | Path,
    image_space: str,
    left_cube: ip.Cube,
    right_cube: ip.Cube,
    candidate_windows: list[PairedTileWindow],
    band: int,
    minimum_value: float | None,
    maximum_value: float | None,
    lower_percent: float,
    upper_percent: float,
    left_invalid_values: tuple[float, ...],
    right_invalid_values: tuple[float, ...],
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    min_valid_pixels: int,
    valid_pixel_percent_threshold: float,
    invalid_pixel_radius: int,
    ratio_test: float,
    matcher_method: str,
    max_features: int | None,
    sift_octave_layers: int,
    sift_contrast_threshold: float,
    sift_edge_threshold: float,
    sift_sigma: float,
    use_gpu: bool,
    gpu_batch_size: int,
    deep_match_temp_root_dir: str | Path,
    deep_match_config_path: str | Path | None = None,
    deep_match_runtime_config: object | None = None,
) -> tuple[list[TileMatchStats], dict[str, object]]:
    image_backend = build_image_backend(image_space)
    tile_tasks = _build_tile_match_tasks(
        candidate_windows,
        left_dom_path=left_dom_path,
        right_dom_path=right_dom_path,
        image_space=image_backend.space,
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
        matcher_method=matcher_method,
        max_features=max_features,
        sift_octave_layers=sift_octave_layers,
        sift_contrast_threshold=sift_contrast_threshold,
        sift_edge_threshold=sift_edge_threshold,
        sift_sigma=sift_sigma,
        use_gpu=use_gpu,
        gpu_batch_size=gpu_batch_size,
        deep_match_runtime_config=deep_match_runtime_config,
    )
    manifest = build_deep_match_pair_manifest(
        tasks=tile_tasks,
        left_dom_path=left_dom_path,
        right_dom_path=right_dom_path,
        matcher_method=matcher_method,
        band=band,
        image_space=image_backend.space,
        temp_root_dir=deep_match_temp_root_dir,
        requested_device="cuda" if use_gpu else "cpu",
        deep_match_config_path=deep_match_config_path,
        deep_match_runtime_config=deep_match_runtime_config,
        created_by_python=sys.executable,
        metadata={
            "export_source": "image_match.match_dom_pair",
            "candidate_tile_count": len(candidate_windows),
            "deep_match_config_path": (
                None if deep_match_config_path is None else str(Path(deep_match_config_path))
            ),
            "deep_match_runtime_config": _runtime_config_to_metadata(deep_match_runtime_config),
            "matcher_method": matcher_method,
            "feature_extractor_method": (
                None
                if deep_match_runtime_config is None
                else getattr(deep_match_runtime_config, "feature_extractor_method", None)
            ),
            "created_by_python": sys.executable,
        },
    )
    workspace = resolve_deep_match_workspace(
        temp_root_dir=deep_match_temp_root_dir,
        pair_id=manifest.pair_id,
    )
    ensure_deep_match_workspace(workspace)

    exported_records = []
    tile_summaries: list[TileMatchStats] = []
    skipped_tile_count = 0
    for record in manifest.tasks:
        task = record.tile_task
        left_values = _read_cube_window(left_cube, task.paired_window.left_window, band=task.band)
        right_values = _read_cube_window(right_cube, task.paired_window.right_window, band=task.band)
        prepared = tile_matching_module._prepare_gpu_tile_payload_from_values(
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
        )
        if isinstance(prepared, TileMatchResult):
            tile_summaries.append(prepared.stats)
            skipped_tile_count += 1
            continue
        write_deep_match_task_arrays(
            record,
            left_image=prepared.left_image,
            right_image=prepared.right_image,
            left_mask=prepared.left_mask,
            right_mask=prepared.right_mask,
        )
        exported_records.append(record)
        tile_summaries.append(_export_tile_summary_from_payload(prepared))

    filtered_manifest = manifest.__class__(
        format_version=manifest.format_version,
        pair_id=manifest.pair_id,
        workspace_root=manifest.workspace_root,
        left_dom_path=manifest.left_dom_path,
        right_dom_path=manifest.right_dom_path,
        image_space=manifest.image_space,
        matcher_method=manifest.matcher_method,
        requested_device=manifest.requested_device,
        band=manifest.band,
        created_at_utc=manifest.created_at_utc,
        tasks=tuple(exported_records),
        metadata={
            **manifest.metadata,
            "exported_task_count": len(exported_records),
            "skipped_task_count": skipped_tile_count,
        },
    )
    manifest_path = write_deep_match_pair_manifest(filtered_manifest)
    return tile_summaries, {
        "status": "exported_for_deep_learning" if exported_records else "export_skipped_no_tasks",
        "reason": (
            "Prepared deep-matching task workspace for execution in the deep-learning environment."
            if exported_records
            else "No tile tasks met the validity requirements for deep-learning export."
        ),
        "manifest_path": str(manifest_path),
        "workspace_root": str(workspace.root_dir),
        "images_dir": str(workspace.images_dir),
        "results_dir": str(workspace.results_dir),
        "logs_dir": str(workspace.logs_dir),
        "pair_id": filtered_manifest.pair_id,
        "exported_task_count": len(exported_records),
        "skipped_task_count": skipped_tile_count,
        "requested_device": filtered_manifest.requested_device,
    }


def _adaptive_cascade_steps_from_summary(
    adaptive_routing_summary: dict[str, object] | None,
    *,
    initial_matcher: str,
    initial_deep_match_config_path: str | Path | None = None,
    adaptive_routing_deep_presets: dict[str, str] | None = None,
) -> tuple[dict[str, object], ...]:
    normalized_initial_config_path = (
        None if initial_deep_match_config_path is None else str(initial_deep_match_config_path)
    )
    if not adaptive_routing_summary or adaptive_routing_summary.get("status") != "routed":
        return ({"matcher_method": initial_matcher, "deep_match_config_path": normalized_initial_config_path},)

    preset_map = {
        str(key).strip().lower(): str(value)
        for key, value in (adaptive_routing_deep_presets or {}).items()
        if value not in (None, "")
    }
    selected_matcher = str(adaptive_routing_summary.get("selected_initial_matcher", initial_matcher))
    selected_config_path = adaptive_routing_summary.get("selected_deep_match_config_path")
    steps: list[dict[str, object]] = [
        {
            "matcher_method": selected_matcher,
            "deep_match_config_path": (
                None if selected_config_path in (None, "") else str(selected_config_path)
            ),
        }
    ]
    if selected_matcher in {"bf", "flann"}:
        if preset_map.get("lightglue_high_recall"):
            steps.append(
                {
                    "matcher_method": "lightglue",
                    "deep_match_config_path": preset_map["lightglue_high_recall"],
                }
            )
        elif preset_map.get("lightglue"):
            steps.append(
                {
                    "matcher_method": "lightglue",
                    "deep_match_config_path": preset_map["lightglue"],
                }
            )
        else:
            steps.append(
                {
                    "matcher_method": "lightglue",
                    "deep_match_config_path": None,
                }
            )
        if preset_map.get("loftr"):
            steps.append(
                {
                    "matcher_method": "loftr",
                    "deep_match_config_path": preset_map["loftr"],
                }
            )
        else:
            steps.append(
                {
                    "matcher_method": "loftr",
                    "deep_match_config_path": None,
                }
            )
    elif selected_matcher == "lightglue":
        high_recall_path = preset_map.get("lightglue_high_recall")
        if high_recall_path and high_recall_path != steps[0]["deep_match_config_path"]:
            steps.append(
                {
                    "matcher_method": "lightglue",
                    "deep_match_config_path": high_recall_path,
                }
            )
        if preset_map.get("loftr"):
            steps.append(
                {
                    "matcher_method": "loftr",
                    "deep_match_config_path": preset_map["loftr"],
                }
            )
        else:
            steps.append(
                {
                    "matcher_method": "loftr",
                    "deep_match_config_path": None,
                }
            )

    deduped_steps: list[dict[str, object]] = []
    seen: set[tuple[str, str | None]] = set()
    for step in steps:
        dedupe_key = (
            str(step["matcher_method"]),
            None if step["deep_match_config_path"] in (None, "") else str(step["deep_match_config_path"]),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped_steps.append(step)
    return tuple(deduped_steps)


def _local_points_to_keypoints(points: np.ndarray, window: object) -> tuple[Keypoint, ...]:
    point_array = np.asarray(points, dtype=np.float32).reshape(-1, 2)
    return tuple(
        Keypoint(
            sample=int(window.start_x) + float(point[0]) + 1.0,
            line=int(window.start_y) + float(point[1]) + 1.0,
        )
        for point in point_array
    )


def import_deep_match_manifest_results(
    manifest_path: str | Path,
    *,
    left_dom_path: str | Path | None = None,
    right_dom_path: str | Path | None = None,
) -> tuple[KeypointFile, KeypointFile, dict[str, object]]:
    """Import standardized deep-match result NPZ files into DOM/ORI `.key` data."""

    manifest = read_deep_match_pair_manifest(manifest_path)
    resolved_left_dom_path = str(left_dom_path if left_dom_path is not None else manifest.left_dom_path)
    resolved_right_dom_path = str(right_dom_path if right_dom_path is not None else manifest.right_dom_path)

    left_cube = ip.Cube()
    right_cube = ip.Cube()
    left_cube.open(resolved_left_dom_path, "r")
    right_cube.open(resolved_right_dom_path, "r")
    try:
        left_width = left_cube.sample_count()
        left_height = left_cube.line_count()
        right_width = right_cube.sample_count()
        right_height = right_cube.line_count()
    finally:
        if left_cube.is_open():
            left_cube.close()
        if right_cube.is_open():
            right_cube.close()

    left_points: list[Keypoint] = []
    right_points: list[Keypoint] = []
    task_summaries: list[dict[str, object]] = []
    imported_task_count = 0
    failed_task_count = 0
    missing_result_count = 0
    skipped_empty_task_count = 0

    for record in manifest.tasks:
        result_path = Path(record.result_path).expanduser().resolve()
        if not result_path.exists():
            missing_result_count += 1
            task_summaries.append(
                {
                    "task_index": record.task_index,
                    "status": "missing_result",
                    "result_path": str(result_path),
                    "match_count": 0,
                }
            )
            continue

        result = read_deep_match_task_result(record)
        metadata = dict(result.get("metadata", {}))
        task_status = str(metadata.get("status", "matched"))
        if task_status == "failed":
            failed_task_count += 1
            task_summaries.append(
                {
                    "task_index": record.task_index,
                    "status": "failed",
                    "result_path": str(result_path),
                    "match_count": 0,
                    "metadata": metadata,
                }
            )
            continue

        left_result_points = np.asarray(result["left_points"], dtype=np.float32).reshape(-1, 2)
        right_result_points = np.asarray(result["right_points"], dtype=np.float32).reshape(-1, 2)
        pair_count = min(left_result_points.shape[0], right_result_points.shape[0])
        if pair_count <= 0:
            skipped_empty_task_count += 1
            task_summaries.append(
                {
                    "task_index": record.task_index,
                    "status": task_status,
                    "result_path": str(result_path),
                    "match_count": 0,
                    "metadata": metadata,
                }
            )
            continue

        left_imported = _local_points_to_keypoints(
            left_result_points[:pair_count],
            record.tile_task.paired_window.left_window,
        )
        right_imported = _local_points_to_keypoints(
            right_result_points[:pair_count],
            record.tile_task.paired_window.right_window,
        )
        left_points.extend(left_imported)
        right_points.extend(right_imported)
        imported_task_count += 1
        task_summaries.append(
            {
                "task_index": record.task_index,
                "status": "imported",
                "source_status": task_status,
                "result_path": str(result_path),
                "match_count": pair_count,
                "metadata": metadata,
            }
        )

    total_issue_count = failed_task_count + missing_result_count
    import_status = "imported" if left_points else "imported_no_points"
    if total_issue_count and imported_task_count:
        import_status = "imported_with_missing_or_failed_tasks"
    elif total_issue_count and not imported_task_count:
        import_status = "import_failed_no_usable_results"

    left_key_file = KeypointFile(left_width, left_height, tuple(left_points))
    right_key_file = KeypointFile(right_width, right_height, tuple(right_points))
    summary = {
        "left_dom": resolved_left_dom_path,
        "right_dom": resolved_right_dom_path,
        "image_space": manifest.image_space,
        "band": manifest.band,
        "matcher_method_requested": manifest.matcher_method,
        "matcher_method_effective": manifest.matcher_method,
        "status": import_status,
        "reason": "Imported standardized deep-learning match results from a manifest workspace.",
        "point_count": len(left_points),
        "left_image_width": left_width,
        "left_image_height": left_height,
        "right_image_width": right_width,
        "right_image_height": right_height,
        "deep_match_mode": "import",
        "deep_match_import": {
            "manifest_path": str(Path(manifest_path).expanduser().resolve()),
            "workspace_root": manifest.workspace_root,
            "pair_id": manifest.pair_id,
            "task_count": len(manifest.tasks),
            "imported_task_count": imported_task_count,
            "failed_task_count": failed_task_count,
            "missing_result_count": missing_result_count,
            "skipped_empty_task_count": skipped_empty_task_count,
            "imported_match_count": len(left_points),
            "requested_device": manifest.requested_device,
            "created_at_utc": manifest.created_at_utc,
            "tasks": task_summaries,
        },
        "deep_match_export": None,
        "matcher": {
            "matcher_method_requested": manifest.matcher_method,
            "matcher_method_effective": manifest.matcher_method,
            **_matcher_diagnostics_for_method(manifest.matcher_method),
        },
        "preparation": {
            "status": import_status,
            "reason": "Imported standardized deep-learning match results from a manifest workspace.",
        },
    }
    return left_key_file, right_key_file, summary


def _match_pair_generic(
    left_path: str | Path,
    right_path: str | Path,
    *,
    image_space: str,
    matcher_method: str = DEFAULT_MATCHER_METHOD,
    **kwargs,
):
    backend = build_image_backend(image_space)
    resolved_image_space = backend.space

    resolved_matcher_method = str(matcher_method).strip().lower()
    if resolved_image_space == "ori" and resolved_matcher_method == "superpoint":
        if __package__ in {None, ""}:
            from image_match.deep_frontends import DeepDependencyError, SuperPointFrontend
        else:
            from .deep_frontends import DeepDependencyError, SuperPointFrontend

        try:
            SuperPointFrontend().extract([[0.0]], device="cpu")
        except DeepDependencyError as exc:
            raise RuntimeError(str(exc)) from exc

    return match_dom_pair(
        left_path,
        right_path,
        image_space=resolved_image_space,
        matcher_method=matcher_method,
        **kwargs,
    )


def match_ori_pair(
    left_cube_path: str | Path,
    right_cube_path: str | Path,
    *,
    matcher_method: str = DEFAULT_MATCHER_METHOD,
    **kwargs,
):
    return _match_pair_generic(
        left_cube_path,
        right_cube_path,
        image_space="ori",
        matcher_method=matcher_method,
        **kwargs,
    )


def match_ori_pair_to_key_files(
    left_cube_path: str | Path,
    right_cube_path: str | Path,
    left_output_key: str | Path,
    right_output_key: str | Path,
    **kwargs,
) -> dict[str, object]:
    left_key_file, right_key_file, summary = match_ori_pair(
        left_cube_path,
        right_cube_path,
        **kwargs,
    )
    write_key_file(left_output_key, left_key_file)
    write_key_file(right_output_key, right_key_file)
    return {
        **summary,
        "left_output_key": str(left_output_key),
        "right_output_key": str(right_output_key),
    }


def _tile_cache_metadata(
    *,
    use_tile_cache: bool,
    aggregate_summary: dict[str, object] | None,
) -> dict[str, object]:
    if aggregate_summary is not None:
        metadata = dict(aggregate_summary)
        metadata.setdefault("enabled", bool(use_tile_cache))
        if metadata.get("left") is not None and metadata.get("right") is not None:
            metadata.setdefault("summary_available", True)
            metadata.setdefault("scope", "serial")
        else:
            metadata.setdefault("summary_available", False)
        return metadata
    if use_tile_cache:
        return {
            "enabled": True,
            "summary_available": False,
            "scope": "parallel_worker_local",
            "reason": "TileCache summaries are worker-local and not aggregated for parallel tile matching.",
        }
    return {
        "enabled": False,
        "summary_available": False,
    }


def match_dom_pair(
    left_dom_path: str | Path,
    right_dom_path: str | Path,
    *,
    image_space: str = "dom",
    band: int = 1,
    max_image_dimension: int = 3000,
    block_width: int = 1024,
    block_height: int = 1024,
    overlap_x: int = 128,
    overlap_y: int = 128,
    tile_block_alignment_mode: str = DEFAULT_TILE_BLOCK_ALIGNMENT_MODE,
    minimum_value: float | None = None,
    maximum_value: float | None = None,
    lower_percent: float = 0.5,
    upper_percent: float = 99.5,
    invalid_values: tuple[float, ...] = (),
    special_pixel_abs_threshold: float = 1.0e300,
    min_valid_pixels: int = 64,
    valid_pixel_percent_threshold: float = 0.0,
    invalid_pixel_radius: int = 1,
    enable_tile_validity_prefilter: bool = False,
    tile_validity_cache_dir: str | Path | None = None,
    tile_validity_cell_width: int = DEFAULT_TILE_VALIDITY_CELL_WIDTH,
    tile_validity_cell_height: int = DEFAULT_TILE_VALIDITY_CELL_HEIGHT,
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
    enable_adaptive_routing: bool = DEFAULT_ENABLE_ADAPTIVE_ROUTING,
    adaptive_routing_profile: str = DEFAULT_ADAPTIVE_ROUTING_PROFILE,
    adaptive_routing_deep_presets: dict[str, str] | None = None,
    low_resolution_level: int | None = None,
    low_resolution_matching_target_long_edge: int | None = None,
    low_resolution_trim_fraction_each_side: float = DEFAULT_LOW_RESOLUTION_TRIM_FRACTION_EACH_SIDE,
    low_resolution_max_mean_reprojection_error_pixels: float = 3.0,
    low_resolution_min_retained_match_count: int = DEFAULT_LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT,
    low_resolution_max_mean_projected_offset_meters: float = DEFAULT_LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS,
    low_resolution_output_dir: str | Path | None = None,
    left_low_resolution_dom: str | Path | None = None,
    right_low_resolution_dom: str | Path | None = None,
    show_progress: bool = False,
    use_tile_cache: bool = False,
    tile_cache_max_mb: int = 100,
    adaptive_warmup_count: int = 10,
    adaptive_throughput_threshold_mbps: float = 200.0,
    adaptive_recheck_every: int = 0,
    use_gpu: bool = False,
    gpu_batch_size: int = DEFAULT_GPU_BATCH_SIZE,
    gpu_dynamic_batch: bool = True,
    gpu_min_batch_size: int = 2,
    gpu_max_batch_size: int = 16,
    deep_match_mode: str = DEFAULT_DEEP_MATCH_MODE,
    deep_match_temp_root_dir: str | Path | None = None,
    deep_match_config_path: str | Path | None = None,
) -> tuple[KeypointFile, KeypointFile, dict[str, object]]:
    left_cube = ip.Cube()
    right_cube = ip.Cube()

    try:
        resolved_deep_match_config = None
        resolved_deep_match_runtime_config = None
        resolved_deep_match_config_path = None
        resolved_adaptive_routing_deep_presets = {
            str(key).strip().lower(): str(value)
            for key, value in (adaptive_routing_deep_presets or {}).items()
            if value not in (None, "")
        }
        if deep_match_config_path is not None:
            resolved_deep_match_config_path = Path(deep_match_config_path)
            resolved_deep_match_runtime_config = _resolve_deep_match_runtime_config(resolved_deep_match_config_path)
            resolved_deep_match_config = resolved_deep_match_runtime_config.raw_config

        resolved_requested_matcher_method = _normalize_matcher_method(matcher_method)
        resolved_matcher_method = _resolve_matcher_method_with_deep_config(
            requested_matcher_method=resolved_requested_matcher_method,
            deep_match_runtime_config=resolved_deep_match_runtime_config,
        )
        resolved_requested_matcher_method = resolved_matcher_method

        image_backend = build_image_backend(image_space)
        left_cube.open(str(left_dom_path), "r")
        right_cube.open(str(right_dom_path), "r")
        resolved_valid_pixel_percent_threshold = _validate_valid_pixel_percent_threshold(valid_pixel_percent_threshold)
        resolved_num_worker_parallel_cpu = _validate_num_worker_parallel_cpu(num_worker_parallel_cpu)
        resolved_invalid_pixel_radius = validate_invalid_pixel_radius(invalid_pixel_radius)
        resolved_tile_validity_cell_width = validate_tile_validity_cell_size(
            tile_validity_cell_width,
            field_name="tile_validity_cell_width",
        )
        resolved_tile_validity_cell_height = validate_tile_validity_cell_size(
            tile_validity_cell_height,
            field_name="tile_validity_cell_height",
        )
        resolved_tile_validity_cache_dir = (
            Path(tile_validity_cache_dir)
            if tile_validity_cache_dir is not None
            else default_tile_validity_cache_dir()
        )
        resolved_deep_match_mode = _normalize_deep_match_mode(deep_match_mode)
        resolved_adaptive_routing_quality_profile = resolve_adaptive_routing_quality_profile(adaptive_routing_profile)
        adaptive_routing_quality_gate = asdict(resolved_adaptive_routing_quality_profile)
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
        resolved_low_resolution_matching_target_long_edge = (
            _validate_low_resolution_matching_target_long_edge(low_resolution_matching_target_long_edge)
            if low_resolution_matching_target_long_edge is not None
            else None
        )
        if low_resolution_level is not None:
            resolved_low_resolution_level = _validate_low_resolution_level(low_resolution_level)
        elif enable_low_resolution_offset_estimation and resolved_low_resolution_matching_target_long_edge is not None:
            resolved_low_resolution_level = _reduce_level_for_pair_target_long_edge(
                left_width=left_width,
                left_height=left_height,
                right_width=right_width,
                right_height=right_height,
                target_long_edge=resolved_low_resolution_matching_target_long_edge,
            )
        else:
            resolved_low_resolution_level = DEFAULT_LOW_RESOLUTION_LEVEL
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
        tile_match_backend = "serial"
        gpu_stats = GpuSiftStats() if use_gpu else None
        deep_match_export_summary: dict[str, object] | None = None
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
            matcher_method=resolved_requested_matcher_method,
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
        adaptive_routing_summary: dict[str, object] | None = None
        resolved_matcher_method, adaptive_routing_summary = _resolve_adaptive_route_for_pair(
            enable_adaptive_routing=bool(enable_adaptive_routing),
            requested_matcher_method=resolved_requested_matcher_method,
            adaptive_routing_deep_presets=resolved_adaptive_routing_deep_presets,
            band=band,
            invalid_values=invalid_values,
            special_pixel_abs_threshold=special_pixel_abs_threshold,
            low_resolution_offset_summary=low_resolution_offset_summary,
            left_low_resolution_dom=resolved_left_low_resolution_dom,
            right_low_resolution_dom=resolved_right_low_resolution_dom,
            image_space=image_backend.space,
            left_source_path=left_dom_path,
            right_source_path=right_dom_path,
        )
        routed_deep_match_config_path = (
            adaptive_routing_summary.get("selected_deep_match_config_path")
            if isinstance(adaptive_routing_summary, dict)
            else None
        )
        if routed_deep_match_config_path not in (None, ""):
            resolved_deep_match_config_path = Path(str(routed_deep_match_config_path))
            resolved_deep_match_runtime_config = _resolve_deep_match_runtime_config(resolved_deep_match_config_path)
            resolved_deep_match_config = resolved_deep_match_runtime_config.raw_config
            resolved_matcher_method = _resolve_matcher_method_with_deep_config(
                requested_matcher_method=resolved_matcher_method,
                deep_match_runtime_config=resolved_deep_match_runtime_config,
            )
        elif resolved_matcher_method not in DEEP_MATCHER_METHODS:
            resolved_deep_match_config_path = None
            resolved_deep_match_runtime_config = None
            resolved_deep_match_config = None
        if adaptive_routing_summary is not None:
            adaptive_routing_summary["profile"] = resolved_adaptive_routing_quality_profile.profile
            adaptive_routing_summary["quality_gate"] = dict(adaptive_routing_quality_gate)
        preparation = prepare_dom_pair_for_matching(
            left_dom_path,
            right_dom_path,
            expand_pixels=crop_expand_pixels,
            min_overlap_size=min_overlap_size,
            projected_delta_x=float(low_resolution_offset_summary["delta_x_projected"]),
            projected_delta_y=float(low_resolution_offset_summary["delta_y_projected"]),
        )
        resolved_tile_block_alignment_mode = normalize_tile_block_alignment_mode(tile_block_alignment_mode)
        tile_block_alignment = resolve_tile_aligned_block_config(
            mode=(
                resolved_tile_block_alignment_mode
                if preparation.status == "ready"
                else DEFAULT_TILE_BLOCK_ALIGNMENT_MODE
            ),
            left_shape=storage_tile_shape_from_cube(left_cube),
            right_shape=storage_tile_shape_from_cube(right_cube),
            left_offset_x=preparation.left.offset_sample,
            left_offset_y=preparation.left.offset_line,
            right_offset_x=preparation.right.offset_sample,
            right_offset_y=preparation.right.offset_line,
            requested_block_width=block_width,
            requested_block_height=block_height,
            requested_overlap_x=overlap_x,
            requested_overlap_y=overlap_y,
            common_width=preparation.shared_width,
            common_height=preparation.shared_height,
        )

        tile_cache_summary: dict[str, object] | None = None

        if preparation.status == "ready":
            windows = _paired_windows(
                left_offset_x=preparation.left.offset_sample,
                left_offset_y=preparation.left.offset_line,
                right_offset_x=preparation.right.offset_sample,
                right_offset_y=preparation.right.offset_line,
                common_width=preparation.shared_width,
                common_height=preparation.shared_height,
                max_image_dimension=max_image_dimension,
                block_width=tile_block_alignment.effective_block_width,
                block_height=tile_block_alignment.effective_block_height,
                overlap_x=tile_block_alignment.effective_overlap_x,
                overlap_y=tile_block_alignment.effective_overlap_y,
                local_windows=tile_block_alignment.local_windows,
            )
            tile_count_before_preindex_filter = len(windows)
            preindexed_skipped_tile_count = 0
            tile_validity_skip_reasons: dict[str, int] = {}
            left_tile_validity_index_summary: dict[str, object] | None = None
            right_tile_validity_index_summary: dict[str, object] | None = None
            candidate_windows = windows

            if enable_tile_validity_prefilter and windows:
                left_tile_validity_index, left_tile_validity_index_summary = ensure_dom_validity_index(
                    cache_dir=resolved_tile_validity_cache_dir,
                    dom_path=left_dom_path,
                    cube=left_cube,
                    band=band,
                    invalid_values=left_invalid_values,
                    special_pixel_abs_threshold=special_pixel_abs_threshold,
                    invalid_pixel_radius=resolved_invalid_pixel_radius,
                    cell_width=resolved_tile_validity_cell_width,
                    cell_height=resolved_tile_validity_cell_height,
                    use_tile_cache=use_tile_cache,
                    cache_max_mb=tile_cache_max_mb,
                    adaptive_warmup_count=adaptive_warmup_count,
                    adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
                    adaptive_recheck_every=adaptive_recheck_every,
                )
                right_tile_validity_index, right_tile_validity_index_summary = ensure_dom_validity_index(
                    cache_dir=resolved_tile_validity_cache_dir,
                    dom_path=right_dom_path,
                    cube=right_cube,
                    band=band,
                    invalid_values=right_invalid_values,
                    special_pixel_abs_threshold=special_pixel_abs_threshold,
                    invalid_pixel_radius=resolved_invalid_pixel_radius,
                    cell_width=resolved_tile_validity_cell_width,
                    cell_height=resolved_tile_validity_cell_height,
                    use_tile_cache=use_tile_cache,
                    cache_max_mb=tile_cache_max_mb,
                    adaptive_warmup_count=adaptive_warmup_count,
                    adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
                    adaptive_recheck_every=adaptive_recheck_every,
                )
                prefilter_result = prefilter_paired_windows_by_validity(
                    windows,
                    left_index=left_tile_validity_index,
                    right_index=right_tile_validity_index,
                    valid_pixel_percent_threshold=resolved_valid_pixel_percent_threshold,
                )
                candidate_windows = prefilter_result.kept_windows
                preindexed_skipped_tile_count = prefilter_result.preindexed_skipped_tile_count
                tile_validity_skip_reasons = prefilter_result.skip_reasons

            if candidate_windows:
                if resolved_deep_match_mode == "export":
                    if resolved_matcher_method not in DEEP_MATCHER_METHODS:
                        raise ValueError(
                            "deep_match_mode='export' currently supports only deep matcher methods: "
                            f"{DEEP_MATCHER_METHODS}."
                        )
                    tile_summaries, deep_match_export_summary = _export_deep_match_pair_tasks(
                        left_dom_path=left_dom_path,
                        right_dom_path=right_dom_path,
                        image_space=image_backend.space,
                        left_cube=left_cube,
                        right_cube=right_cube,
                        candidate_windows=candidate_windows,
                        band=band,
                        minimum_value=minimum_value,
                        maximum_value=maximum_value,
                        lower_percent=lower_percent,
                        upper_percent=upper_percent,
                        left_invalid_values=left_invalid_values,
                        right_invalid_values=right_invalid_values,
                        invalid_values=invalid_values,
                        special_pixel_abs_threshold=special_pixel_abs_threshold,
                        min_valid_pixels=min_valid_pixels,
                        valid_pixel_percent_threshold=resolved_valid_pixel_percent_threshold,
                        invalid_pixel_radius=resolved_invalid_pixel_radius,
                        ratio_test=ratio_test,
                        matcher_method=resolved_matcher_method,
                        max_features=max_features,
                        sift_octave_layers=sift_octave_layers,
                        sift_contrast_threshold=sift_contrast_threshold,
                        sift_edge_threshold=sift_edge_threshold,
                        sift_sigma=sift_sigma,
                        use_gpu=use_gpu,
                        gpu_batch_size=gpu_batch_size,
                        deep_match_temp_root_dir=(
                            deep_match_temp_root_dir
                            if deep_match_temp_root_dir is not None
                            else Path.cwd() / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME
                        ),
                        deep_match_config_path=resolved_deep_match_config_path,
                        deep_match_runtime_config=resolved_deep_match_runtime_config,
                    )
                else:
                    def run_tile_matching_pass(
                        candidate_matcher_method: str,
                        *,
                        candidate_deep_match_runtime_config: object | None = None,
                    ) -> list[TileMatchResult]:
                        nonlocal parallel_cpu_used, parallel_cpu_backend, parallel_cpu_worker_count, tile_match_backend, tile_cache_summary

                        progress_bar = (
                            _TileProgressBar(
                                left_dom_path=left_dom_path,
                                right_dom_path=right_dom_path,
                                total_tiles=len(candidate_windows),
                            )
                            if show_progress
                            else None
                        )
                        if progress_bar is not None:
                            progress_bar.start()
                        if parallel_cpu_requested and len(candidate_windows) > 1:
                            candidate_worker_count = min(len(candidate_windows), resolved_num_worker_parallel_cpu)
                            if candidate_worker_count > 1:
                                tile_tasks = _build_tile_match_tasks(
                                    candidate_windows,
                                    left_dom_path=left_dom_path,
                                    right_dom_path=right_dom_path,
                                    image_space=image_backend.space,
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
                                    matcher_method=candidate_matcher_method,
                                    ratio_test=ratio_test,
                                    max_features=max_features,
                                    sift_octave_layers=sift_octave_layers,
                                    sift_contrast_threshold=sift_contrast_threshold,
                                    sift_edge_threshold=sift_edge_threshold,
                                     sift_sigma=sift_sigma,
                                     use_gpu=use_gpu,
                                     gpu_batch_size=gpu_batch_size,
                                     deep_match_runtime_config=candidate_deep_match_runtime_config,
                                 )
                                try:
                                    pass_results = _run_parallel_tile_match_tasks(
                                        tile_tasks,
                                        image_space=image_backend.space,
                                        max_workers=candidate_worker_count,
                                        progress_callback=progress_bar.update if progress_bar is not None else None,
                                        gpu_dynamic_batch=gpu_dynamic_batch,
                                        gpu_min_batch_size=gpu_min_batch_size,
                                        gpu_max_batch_size=gpu_max_batch_size,
                                        gpu_stats=gpu_stats,
                                        use_tile_cache=use_tile_cache,
                                        cache_max_mb=tile_cache_max_mb,
                                        adaptive_warmup_count=adaptive_warmup_count,
                                        adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
                                        adaptive_recheck_every=adaptive_recheck_every,
                                    )
                                finally:
                                    if progress_bar is not None:
                                        progress_bar.finish()
                                backend_summary = _tile_execution_backend_summary(
                                    use_parallel_cpu=parallel_cpu_requested,
                                    use_gpu=use_gpu,
                                    effective_gpu_tile_route=_can_use_dedicated_gpu_tile_route(tile_tasks),
                                    candidate_window_count=len(candidate_windows),
                                    resolved_num_worker_parallel_cpu=resolved_num_worker_parallel_cpu,
                                )
                                parallel_cpu_used = bool(backend_summary["parallel_cpu_used"])
                                parallel_cpu_backend = str(backend_summary["parallel_cpu_backend"])
                                parallel_cpu_worker_count = int(backend_summary["parallel_cpu_worker_count"])
                                tile_match_backend = str(backend_summary["tile_match_backend"])
                                return pass_results

                        try:
                            serial_batch = _run_serial_tile_match_tasks(
                                candidate_windows,
                                image_space=image_backend.space,
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
                                matcher_method=candidate_matcher_method,
                                ratio_test=ratio_test,
                                max_features=max_features,
                                sift_octave_layers=sift_octave_layers,
                                sift_contrast_threshold=sift_contrast_threshold,
                                sift_edge_threshold=sift_edge_threshold,
                                sift_sigma=sift_sigma,
                                use_gpu=use_gpu,
                                deep_match_runtime_config=candidate_deep_match_runtime_config,
                                progress_callback=progress_bar.update if progress_bar is not None else None,
                                use_tile_cache=use_tile_cache,
                                cache_max_mb=tile_cache_max_mb,
                                adaptive_warmup_count=adaptive_warmup_count,
                                adaptive_throughput_threshold_mbps=adaptive_throughput_threshold_mbps,
                                adaptive_recheck_every=adaptive_recheck_every,
                            )
                            pass_results = serial_batch.results
                            tile_cache_summary = serial_batch.tile_cache_summary
                        finally:
                            if progress_bar is not None:
                                progress_bar.finish()
                        parallel_cpu_worker_count = 1
                        tile_match_backend = "serial"
                        return pass_results

                    cascade_plan = _adaptive_cascade_steps_from_summary(
                        adaptive_routing_summary,
                        initial_matcher=resolved_matcher_method,
                        initial_deep_match_config_path=resolved_deep_match_config_path,
                        adaptive_routing_deep_presets=resolved_adaptive_routing_deep_presets,
                    )
                    cascade_attempts: list[dict[str, object]] = []
                    selected_tile_results: list[TileMatchResult] = []
                    final_decision: dict[str, object] | None = None
                    final_quality_report = None

                    for cascade_index, cascade_step in enumerate(cascade_plan):
                        candidate_matcher_method = str(cascade_step["matcher_method"])
                        candidate_deep_match_config_path = cascade_step.get("deep_match_config_path")
                        candidate_deep_match_runtime_config = None
                        candidate_deep_match_config = None
                        if candidate_deep_match_config_path not in (None, ""):
                            candidate_deep_match_config_path = Path(str(candidate_deep_match_config_path))
                            if (
                                resolved_deep_match_config_path is not None
                                and candidate_deep_match_config_path == resolved_deep_match_config_path
                            ):
                                candidate_deep_match_runtime_config = resolved_deep_match_runtime_config
                                candidate_deep_match_config = resolved_deep_match_config
                            else:
                                candidate_deep_match_runtime_config = _resolve_deep_match_runtime_config(
                                    candidate_deep_match_config_path
                                )
                                candidate_deep_match_config = candidate_deep_match_runtime_config.raw_config
                            candidate_matcher_method = _resolve_matcher_method_with_deep_config(
                                requested_matcher_method=candidate_matcher_method,
                                deep_match_runtime_config=candidate_deep_match_runtime_config,
                            )
                        selected_tile_results = run_tile_matching_pass(
                            candidate_matcher_method,
                            candidate_deep_match_runtime_config=candidate_deep_match_runtime_config,
                        )
                        quality_report = _quality_report_for_tile_results(
                            selected_tile_results,
                            candidate_window_count=len(candidate_windows),
                            quality_gate=adaptive_routing_quality_gate,
                        )
                        final_quality_report = quality_report
                        final_decision = decide_post_match_action(
                            current_matcher=candidate_matcher_method,
                            quality_report=quality_report,
                            cascade_plan=tuple(str(step["matcher_method"]) for step in cascade_plan),
                            current_index=cascade_index,
                        )
                        cascade_attempts.append(
                            {
                                "matcher": candidate_matcher_method,
                                "deep_match_config_path": (
                                    None
                                    if candidate_deep_match_config_path in (None, "")
                                    else str(candidate_deep_match_config_path)
                                ),
                                "match_quality": asdict(quality_report),
                                "decision": final_decision,
                            }
                        )
                        if final_decision["accepted"] or final_decision["next_matcher"] is None:
                            resolved_matcher_method = candidate_matcher_method
                            resolved_deep_match_config_path = candidate_deep_match_config_path
                            resolved_deep_match_runtime_config = candidate_deep_match_runtime_config
                            resolved_deep_match_config = candidate_deep_match_config
                            break

                    if adaptive_routing_summary is not None:
                        adaptive_routing_summary["profile"] = resolved_adaptive_routing_quality_profile.profile
                        adaptive_routing_summary["quality_gate"] = dict(adaptive_routing_quality_gate)
                        adaptive_routing_summary["cascade_plan"] = [
                            str(step["matcher_method"]) for step in cascade_plan
                        ]
                        adaptive_routing_summary["cascade_steps"] = list(cascade_plan)
                        adaptive_routing_summary["cascade_attempts"] = cascade_attempts
                        adaptive_routing_summary["selected_final_matcher"] = resolved_matcher_method
                        adaptive_routing_summary["selected_final_deep_match_config_path"] = (
                            None
                            if resolved_deep_match_config_path is None
                            else str(resolved_deep_match_config_path)
                        )
                        if final_quality_report is not None:
                            adaptive_routing_summary["match_quality"] = asdict(final_quality_report)
                        if final_decision is not None:
                            adaptive_routing_summary["final_decision"] = final_decision
                        sidecar = adaptive_routing_summary.get("sidecar")
                        if isinstance(sidecar, dict):
                            if final_quality_report is not None:
                                sidecar["match_quality"] = asdict(final_quality_report)
                            if final_decision is not None:
                                sidecar["final_decision"] = final_decision

                    for tile_result in selected_tile_results:
                        tile_summaries.append(tile_result.stats)
                        left_points.extend(tile_result.left_points)
                        right_points.extend(tile_result.right_points)
        else:
            windows = []
            candidate_windows = []
            tile_count_before_preindex_filter = 0
            preindexed_skipped_tile_count = 0
            tile_validity_skip_reasons = {}
            left_tile_validity_index_summary = None
            right_tile_validity_index_summary = None

        left_key_file = KeypointFile(left_width, left_height, tuple(left_points))
        right_key_file = KeypointFile(right_width, right_height, tuple(right_points))
        full_resolution_skipped_tile_count = sum(1 for tile in tile_summaries if tile.status != "matched")
        resolved_status = preparation.status if preparation.status != "ready" else ("matched" if left_points else "matched_no_points")
        resolved_reason = preparation.reason
        if deep_match_export_summary is not None:
            resolved_status = str(deep_match_export_summary["status"])
            resolved_reason = str(deep_match_export_summary["reason"])
        summary = {
            "left_dom": str(left_dom_path),
            "right_dom": str(right_dom_path),
            "image_space": image_backend.space,
            "band": band,
            "min_valid_pixels": min_valid_pixels,
            "valid_pixel_percent_threshold": resolved_valid_pixel_percent_threshold,
            "invalid_pixel_radius": resolved_invalid_pixel_radius,
            "tile_block_alignment_mode": tile_block_alignment.mode,
            "block_alignment_reason": tile_block_alignment.reason,
            "tile_block_alignment": tile_block_alignment.to_metadata(),
            "matcher_method_requested": resolved_requested_matcher_method,
            "matcher_method_effective": resolved_matcher_method,
            "adaptive_routing_profile": resolved_adaptive_routing_quality_profile.profile,
            "adaptive_routing_quality_gate": adaptive_routing_quality_gate,
            "ratio_test": ratio_test,
            "status": resolved_status,
            "reason": resolved_reason,
            "tiling_used": len(windows) > 1,
            "shared_extent_width": preparation.shared_width,
            "shared_extent_height": preparation.shared_height,
            "dimension_mismatch": left_width != right_width or left_height != right_height,
            "tile_count": len(windows),
            "tile_count_before_preindex_filter": tile_count_before_preindex_filter,
            "tile_count_after_preindex_filter": len(candidate_windows),
            "preindexed_skipped_tile_count": preindexed_skipped_tile_count,
            "full_resolution_skipped_tile_count": full_resolution_skipped_tile_count,
            "matched_tile_count": sum(1 for tile in tile_summaries if tile.status == "matched"),
            "skipped_tile_count": preindexed_skipped_tile_count + full_resolution_skipped_tile_count,
            "tile_validity_prefilter_enabled": bool(enable_tile_validity_prefilter),
            "tile_validity_cache_dir": str(resolved_tile_validity_cache_dir) if enable_tile_validity_prefilter else None,
            "tile_validity_cell_width": resolved_tile_validity_cell_width,
            "tile_validity_cell_height": resolved_tile_validity_cell_height,
            "tile_validity_skip_reasons": tile_validity_skip_reasons,
            "left_tile_validity_index": left_tile_validity_index_summary,
            "right_tile_validity_index": right_tile_validity_index_summary,
            "point_count": len(left_points),
            "parallel_cpu_requested": parallel_cpu_requested,
            "num_worker_parallel_cpu": resolved_num_worker_parallel_cpu,
            "parallel_cpu_used": parallel_cpu_used,
            "parallel_cpu_backend": parallel_cpu_backend,
            "parallel_cpu_worker_count": parallel_cpu_worker_count,
            "tile_match_backend": tile_match_backend,
            "tile_cache": _tile_cache_metadata(
                use_tile_cache=bool(use_tile_cache),
                aggregate_summary=tile_cache_summary,
            ),
            "gpu": _gpu_execution_summary(
                use_gpu=use_gpu,
                gpu_effective=tile_match_backend == "gpu_tile_pipeline",
                gpu_batch_size=gpu_batch_size,
                gpu_dynamic_batch=gpu_dynamic_batch,
                gpu_min_batch_size=gpu_min_batch_size,
                gpu_max_batch_size=gpu_max_batch_size,
                gpu_stats=gpu_stats,
            ),
            "use_gpu": bool(use_gpu),
            "gpu_batch_size": gpu_batch_size,
            "gpu_dynamic_batch": bool(gpu_dynamic_batch),
            "gpu_min_batch_size": gpu_min_batch_size,
            "gpu_max_batch_size": gpu_max_batch_size,
            "low_resolution_trim_fraction_each_side": resolved_low_resolution_trim_fraction_each_side,
            "low_resolution_max_mean_reprojection_error_pixels": resolved_low_resolution_max_mean_reprojection_error_pixels,
            "low_resolution_min_retained_match_count": resolved_low_resolution_min_retained_match_count,
            "low_resolution_max_mean_projected_offset_meters": resolved_low_resolution_max_mean_projected_offset_meters,
            "low_resolution_matching_target_long_edge": resolved_low_resolution_matching_target_long_edge,
            "resolved_low_resolution_level": resolved_low_resolution_level,
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
                "matcher_method_requested": resolved_requested_matcher_method,
                "matcher_method_effective": resolved_matcher_method,
                **_matcher_diagnostics_for_method(resolved_matcher_method),
                "ratio_test": ratio_test,
            },
            "adaptive_routing": adaptive_routing_summary,
            "deep_match_mode": resolved_deep_match_mode,
            "deep_match_config_path": str(resolved_deep_match_config_path) if resolved_deep_match_config_path is not None else None,
            "deep_match_config": resolved_deep_match_config,
            "deep_match_runtime_config": _runtime_config_to_metadata(resolved_deep_match_runtime_config),
            "deep_match_export": deep_match_export_summary,
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
    *,
    visualization_mode: str = DEFAULT_MATCH_VISUALIZATION_MODE,
    memory_profile: str = DEFAULT_MEMORY_PROFILE,
    visualization_target_long_edge: int | None = None,
    max_preview_pixels: int | None = None,
    preview_crop_margin_pixels: int = DEFAULT_PREVIEW_CROP_MARGIN_PIXELS,
    preview_cache_dir: str | Path | None = None,
    preview_cache_source: str = DEFAULT_PREVIEW_CACHE_SOURCE,
    tile_block_alignment_mode: str = DEFAULT_TILE_BLOCK_ALIGNMENT_MODE,
    preview_force_regenerate: bool = False,
    preview_level: int | None = None,
    gpu_dynamic_batch: bool = True,
    gpu_min_batch_size: int = 2,
    gpu_max_batch_size: int = 16,
    deep_match_mode: str = DEFAULT_DEEP_MATCH_MODE,
    deep_match_temp_root_dir: str | Path | None = None,
    deep_match_manifest: str | Path | None = None,
    deep_match_config_path: str | Path | None = None,
    **kwargs,
) -> dict[str, object]:
    resolved_deep_match_mode = _normalize_deep_match_mode(deep_match_mode)
    if resolved_deep_match_mode == "import":
        if deep_match_manifest is None:
            raise ValueError("deep_match_mode='import' requires deep_match_manifest.")
        left_key_file, right_key_file, summary = import_deep_match_manifest_results(
            deep_match_manifest,
            left_dom_path=left_dom_path,
            right_dom_path=right_dom_path,
        )
        Path(left_output_key).parent.mkdir(parents=True, exist_ok=True)
        Path(right_output_key).parent.mkdir(parents=True, exist_ok=True)
        write_key_file(left_output_key, left_key_file)
        write_key_file(right_output_key, right_key_file)
        metadata_payload = None
        if metadata_output is not None:
            metadata_payload = dict(summary["preparation"])
            metadata_payload["image_match"] = {
                "status": summary["status"],
                "reason": summary["reason"],
                "point_count": summary["point_count"],
                "matcher": summary["matcher"],
                "deep_match_mode": summary["deep_match_mode"],
                "deep_match_import": summary["deep_match_import"],
                "deep_match_export": summary["deep_match_export"],
            }
        match_visualization_result: dict[str, object] | None = None
        if write_match_visualization:
            visualization_output_directory = (
                Path(match_visualization_output_dir)
                if match_visualization_output_dir is not None
                else (None if match_visualization_output_path is not None else Path(left_output_key).parent)
            )
            visualization_timestamp = None if match_visualization_output_path is not None else datetime.now()
            match_visualization_result = write_stereo_pair_match_visualization(
                left_dom_path,
                right_dom_path,
                left_key_file,
                right_key_file,
                output_path=match_visualization_output_path,
                output_directory=visualization_output_directory,
                timestamp=visualization_timestamp,
                scale_factor=match_visualization_scale,
                visualization_mode=visualization_mode,
                memory_profile=memory_profile,
                visualization_target_long_edge=visualization_target_long_edge,
                max_preview_pixels=max_preview_pixels,
                preview_crop_margin_pixels=preview_crop_margin_pixels,
                preview_cache_dir=preview_cache_dir,
                preview_cache_source=preview_cache_source,
                preview_force_regenerate=preview_force_regenerate,
                preview_level=preview_level,
                band=int(kwargs.get("band", 1)),
                minimum_value=kwargs.get("minimum_value"),
                maximum_value=kwargs.get("maximum_value"),
                lower_percent=float(kwargs.get("lower_percent", 0.5)),
                upper_percent=float(kwargs.get("upper_percent", 99.5)),
                invalid_values=tuple(kwargs.get("invalid_values", ())),
                special_pixel_abs_threshold=float(kwargs.get("special_pixel_abs_threshold", 1.0e300)),
            )
        if metadata_output is not None and metadata_payload is not None:
            if match_visualization_result is not None:
                metadata_payload["match_visualization"] = match_visualization_result
            write_pair_preparation_metadata(metadata_output, metadata_payload)
        return {
            **summary,
            "left_output_key": str(left_output_key),
            "right_output_key": str(right_output_key),
            "export_only": False,
            **({"metadata_output": str(metadata_output)} if metadata_output is not None else {}),
            **({"match_visualization": match_visualization_result} if match_visualization_result is not None else {}),
        }

    if kwargs.get("enable_tile_validity_prefilter") and kwargs.get("tile_validity_cache_dir") is None:
        kwargs["tile_validity_cache_dir"] = default_tile_validity_cache_dir(
            metadata_output=metadata_output,
            left_output_key=left_output_key,
        )
    if "low_resolution_output_dir" not in kwargs or kwargs.get("low_resolution_output_dir") is None:
        kwargs["low_resolution_output_dir"] = _default_low_resolution_output_dir(
            left_dom_path,
            right_dom_path,
            metadata_output=metadata_output,
            left_output_key=left_output_key,
        )
    left_key_file, right_key_file, summary = match_dom_pair(
        left_dom_path,
        right_dom_path,
        show_progress=show_progress,
        gpu_dynamic_batch=gpu_dynamic_batch,
        gpu_min_batch_size=gpu_min_batch_size,
        gpu_max_batch_size=gpu_max_batch_size,
        deep_match_mode=resolved_deep_match_mode,
        deep_match_temp_root_dir=deep_match_temp_root_dir,
        deep_match_config_path=deep_match_config_path,
        tile_block_alignment_mode=tile_block_alignment_mode,
        **kwargs,
    )
    export_only = summary.get("deep_match_mode") == "export"
    if not export_only:
        write_key_file(left_output_key, left_key_file)
        write_key_file(right_output_key, right_key_file)
    metadata_payload = None
    if metadata_output is not None:
        metadata_payload = dict(summary["preparation"])
        metadata_payload["image_match"] = {
            "status": summary["status"],
            "reason": summary["reason"],
            "point_count": summary["point_count"],
            "tile_count": summary["tile_count"],
            "tile_count_before_preindex_filter": summary["tile_count_before_preindex_filter"],
            "tile_count_after_preindex_filter": summary["tile_count_after_preindex_filter"],
            "preindexed_skipped_tile_count": summary["preindexed_skipped_tile_count"],
            "full_resolution_skipped_tile_count": summary["full_resolution_skipped_tile_count"],
            "matched_tile_count": summary["matched_tile_count"],
            "skipped_tile_count": summary["skipped_tile_count"],
            "tile_validity_prefilter_enabled": summary["tile_validity_prefilter_enabled"],
            "tile_validity_cache_dir": summary["tile_validity_cache_dir"],
            "tile_validity_cell_width": summary["tile_validity_cell_width"],
            "tile_validity_cell_height": summary["tile_validity_cell_height"],
            "tile_block_alignment_mode": summary["tile_block_alignment_mode"],
            "block_alignment_reason": summary["block_alignment_reason"],
            "tile_block_alignment": summary["tile_block_alignment"],
            "tile_validity_skip_reasons": summary["tile_validity_skip_reasons"],
            "left_tile_validity_index": summary["left_tile_validity_index"],
            "right_tile_validity_index": summary["right_tile_validity_index"],
            "tiling_used": summary["tiling_used"],
            "valid_pixel_percent_threshold": summary["valid_pixel_percent_threshold"],
            "invalid_pixel_radius": summary["invalid_pixel_radius"],
            "matcher": summary["matcher"],
            "parallel_cpu_requested": summary["parallel_cpu_requested"],
            "num_worker_parallel_cpu": summary["num_worker_parallel_cpu"],
            "parallel_cpu_used": summary["parallel_cpu_used"],
            "parallel_cpu_backend": summary["parallel_cpu_backend"],
            "parallel_cpu_worker_count": summary["parallel_cpu_worker_count"],
            "tile_match_backend": summary["tile_match_backend"],
            "low_resolution_offset": summary["low_resolution_offset"],
            "low_resolution_matching_target_long_edge": summary["low_resolution_matching_target_long_edge"],
            "resolved_low_resolution_level": summary["resolved_low_resolution_level"],
            "adaptive_routing_profile": summary.get("adaptive_routing_profile", DEFAULT_ADAPTIVE_ROUTING_PROFILE),
            "adaptive_routing_quality_gate": summary.get(
                "adaptive_routing_quality_gate",
                asdict(resolve_adaptive_routing_quality_profile(DEFAULT_ADAPTIVE_ROUTING_PROFILE)),
            ),
            "adaptive_routing": summary["adaptive_routing"],
            "deep_match_mode": summary.get("deep_match_mode", DEFAULT_DEEP_MATCH_MODE),
            "deep_match_config_path": summary.get("deep_match_config_path"),
            "deep_match_config": summary.get("deep_match_config"),
            "deep_match_runtime_config": summary.get("deep_match_runtime_config"),
            "deep_match_export": summary.get("deep_match_export"),
        }
    match_visualization_result: dict[str, object] | None = None
    if write_match_visualization and not export_only:
        visualization_output_directory = (
            Path(match_visualization_output_dir)
            if match_visualization_output_dir is not None
            else (None if match_visualization_output_path is not None else Path(left_output_key).parent)
        )
        visualization_timestamp = None if match_visualization_output_path is not None else datetime.now()
        low_resolution_visualization_preview = summary.get("low_resolution_offset", {})
        try:
            match_visualization_result = write_stereo_pair_match_visualization(
                left_dom_path,
                right_dom_path,
                left_key_file,
                right_key_file,
                output_path=match_visualization_output_path,
                output_directory=visualization_output_directory,
                timestamp=visualization_timestamp,
                scale_factor=match_visualization_scale,
                visualization_mode=visualization_mode,
                memory_profile=memory_profile,
                visualization_target_long_edge=visualization_target_long_edge,
                max_preview_pixels=max_preview_pixels,
                preview_crop_margin_pixels=preview_crop_margin_pixels,
                preview_cache_dir=preview_cache_dir,
                preview_cache_source=preview_cache_source,
                preview_force_regenerate=preview_force_regenerate,
                preview_level=preview_level,
                left_matching_preview_dom=low_resolution_visualization_preview.get("left_low_resolution_dom"),
                right_matching_preview_dom=low_resolution_visualization_preview.get("right_low_resolution_dom"),
                matching_preview_level=low_resolution_visualization_preview.get("low_resolution_level"),
                band=int(kwargs.get("band", 1)),
                minimum_value=kwargs.get("minimum_value"),
                maximum_value=kwargs.get("maximum_value"),
                lower_percent=float(kwargs.get("lower_percent", 0.5)),
                upper_percent=float(kwargs.get("upper_percent", 99.5)),
                invalid_values=tuple(kwargs.get("invalid_values", ())),
                special_pixel_abs_threshold=float(kwargs.get("special_pixel_abs_threshold", 1.0e300)),
            )
        except Exception as exc:
            if metadata_output is not None and metadata_payload is not None:
                match_visualization_result = {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
                if match_visualization_output_path is not None:
                    match_visualization_result["output_path"] = str(match_visualization_output_path)
                else:
                    match_visualization_result["output_path"] = str(
                        default_match_visualization_path(
                            left_dom_path,
                            right_dom_path,
                            visualization_output_directory,
                            timestamp=visualization_timestamp,
                        )
                    )
                metadata_payload["match_visualization"] = match_visualization_result
                write_pair_preparation_metadata(
                    metadata_output,
                    metadata_payload,
                )
            raise
    if metadata_output is not None and metadata_payload is not None:
        if match_visualization_result is not None:
            metadata_payload["match_visualization"] = match_visualization_result
        write_pair_preparation_metadata(
            metadata_output,
            metadata_payload,
        )
    return {
        **summary,
        "left_output_key": str(left_output_key),
        "right_output_key": str(right_output_key),
        "export_only": export_only,
        **({"metadata_output": str(metadata_output)} if metadata_output is not None else {}),
        **({"match_visualization": match_visualization_result} if match_visualization_result is not None else {}),
    }


def build_argument_parser(config_defaults: dict[str, object] | None = None) -> argparse.ArgumentParser:
    parser = _ImageMatchArgumentParser(description="Match two DOM cubes with OpenCV SIFT and write DOM-space `.key` files.")
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
    parser.add_argument(
        "--tile-block-alignment-mode",
        type=_parse_tile_block_alignment_mode,
        default=DEFAULT_TILE_BLOCK_ALIGNMENT_MODE,
        help=(
            "Full-resolution block alignment mode for ISIS storage tile boundaries. "
            f"Supported values: {_format_supported_values(SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES)}. "
            f"Default: {DEFAULT_TILE_BLOCK_ALIGNMENT_MODE}."
        ),
    )
    parser.add_argument("--minimum-value", type=float, default=None, help="Manual gray-stretch minimum value.")
    parser.add_argument("--maximum-value", type=float, default=None, help="Manual gray-stretch maximum value.")
    parser.add_argument("--lower-percent", type=float, default=0.5, help="Lower percentile used by automatic gray stretch.")
    parser.add_argument("--upper-percent", type=float, default=99.5, help="Upper percentile used by automatic gray stretch.")
    parser.add_argument("--invalid-value", action="append", default=[], type=float, help="Additional invalid pixel sentinel. Repeat for multiple values.")
    parser.add_argument("--special-pixel-abs-threshold", type=float, default=1.0e300, help="Absolute-value threshold used to treat extreme ISIS special pixels as invalid.")
    parser.add_argument("--min-valid-pixels", type=int, default=64, help="Minimum number of valid pixels required before attempting SIFT on a tile.")
    parser.add_argument("--valid-pixel-percent-threshold", type=_parse_valid_pixel_percent_threshold, default=0.0, help="Minimum valid-pixel ratio required before attempting SIFT on a tile. Must be within [0.0, 1.0].")
    parser.add_argument("--invalid-pixel-radius", type=_parse_invalid_pixel_radius, default=1, help="Don't detect feature point within this many pixels of image borders or invalid pixel. Must be within [0, 100]. Default: 1.")
    parser.add_argument("--enable-tile-validity-prefilter", dest="enable_tile_validity_prefilter", action="store_true", help="Enable workflow-level DOM validity index prefiltering before full-resolution tile reads.")
    parser.add_argument("--tile-validity-cache-dir", default=None, help="Directory for reusable per-DOM tile-validity index cache files.")
    parser.add_argument("--tile-validity-cell-width", type=lambda value: _parse_tile_validity_cell_size(value, field_name="tile_validity_cell_width"), default=DEFAULT_TILE_VALIDITY_CELL_WIDTH, help=f"Coarse validity-index cell width. Default: {DEFAULT_TILE_VALIDITY_CELL_WIDTH}.")
    parser.add_argument("--tile-validity-cell-height", type=lambda value: _parse_tile_validity_cell_size(value, field_name="tile_validity_cell_height"), default=DEFAULT_TILE_VALIDITY_CELL_HEIGHT, help=f"Coarse validity-index cell height. Default: {DEFAULT_TILE_VALIDITY_CELL_HEIGHT}.")
    parser.add_argument(
        "--match-preset-path",
        action=_MatchPresetPathAction,
        default=None,
        help=(
            "Path to a neutral match preset JSON. Classic SIFT presets set OpenCV SIFT/BF/FLANN "
            "parameters; deep presets set matcher_method plus deep_match_config_path."
        ),
    )
    parser.add_argument("--matcher-method", type=_parse_matcher_method, default=DEFAULT_MATCHER_METHOD, help="Matcher method: bf, flann, superpoint, superglue, lightglue, loftr (default: bf).")
    parser.add_argument(
        "--deep-match-config-path",
        type=Path,
        default=None,
        help=(
            "Path to a deep matcher preset JSON. The file is validated before "
            "running deep matcher methods and its resolved values are recorded in metadata."
        ),
    )
    parser.add_argument("--deep-match-mode", type=_parse_deep_match_mode, default=DEFAULT_DEEP_MATCH_MODE, help="Deep-match execution mode: direct, export, or import. 'export' writes a manifest plus tile arrays; 'import' reads completed manifest NPZ results and writes `.key` files.")
    parser.add_argument("--deep-match-temp-root-dir", default=None, help="Root directory used for exported deep-match workspaces when --deep-match-mode export is selected.")
    parser.add_argument("--deep-match-manifest", default=None, help="Path to an exported deep-match tasks.json manifest when --deep-match-mode import is selected.")
    parser.add_argument("--ratio-test", type=float, default=0.75, help="Lowe ratio-test threshold used for descriptor filtering.")
    parser.add_argument("--max-features", type=int, default=None, help="Optional maximum number of SIFT features per tile.")
    parser.add_argument("--sift-octave-layers", type=int, default=3, help="Number of octave layers used by the OpenCV SIFT detector.")
    parser.add_argument("--sift-contrast-threshold", type=float, default=0.04, help="Contrast threshold used by the OpenCV SIFT detector.")
    parser.add_argument("--sift-edge-threshold", type=float, default=10.0, help="Edge threshold used by the OpenCV SIFT detector.")
    parser.add_argument("--sift-sigma", type=float, default=1.6, help="Gaussian sigma used by the OpenCV SIFT detector.")
    parser.add_argument("--crop-expand-pixels", type=int, default=100, help="Extra projected-overlap margin, expressed in pixels, added before matching.")
    parser.add_argument("--min-overlap-size", type=int, default=16, help="Skip matching when the expanded projected-overlap window is smaller than this many pixels in either direction.")
    parser.add_argument("--adaptive-routing", dest="enable_adaptive_routing", action="store_true", help="Enable a low-resolution texture-probe prepass that can select a pair-level initial matcher before full-resolution matching.")
    parser.add_argument("--no-adaptive-routing", dest="enable_adaptive_routing", action="store_false", help="Disable the adaptive routing prepass and use the requested matcher directly.")
    parser.add_argument(
        "--adaptive-routing-profile",
        type=_parse_adaptive_routing_profile,
        default=DEFAULT_ADAPTIVE_ROUTING_PROFILE,
        help=(
            "Named adaptive-routing quality profile used to expand post-match fallback thresholds. "
            f"Supported values: {_format_supported_values(SUPPORTED_ADAPTIVE_ROUTING_PROFILES)}. "
            f"Default: {DEFAULT_ADAPTIVE_ROUTING_PROFILE}."
        ),
    )
    parser.add_argument("--enable-low-resolution-offset-estimation", dest="enable_low_resolution_offset_estimation", action="store_true", help="Enable low-resolution DOM matching to estimate a projected global offset before the full-resolution overlap crop is prepared.")
    parser.add_argument(
        "--low-resolution-level",
        type=_parse_low_resolution_level,
        default=None,
        help=(
            "Low-resolution pyramid level used for the projected offset estimation stage. Must be >= 0. "
            f"Overrides --low-resolution-matching-target-long-edge. Default: {DEFAULT_LOW_RESOLUTION_LEVEL}."
        ),
    )
    parser.add_argument(
        "--low-resolution-matching-target-long-edge",
        type=_parse_low_resolution_matching_target_long_edge,
        default=None,
        help="Target long-edge size used to derive a low-resolution match level when --low-resolution-level is not set.",
    )
    parser.add_argument("--low-resolution-trim-fraction-each-side", type=_parse_low_resolution_trim_fraction_each_side, default=DEFAULT_LOW_RESOLUTION_TRIM_FRACTION_EACH_SIDE, help=f"Fraction of low-resolution projected offset samples trimmed from each tail before averaging. Must be within [0.0, 0.5). Default: {DEFAULT_LOW_RESOLUTION_TRIM_FRACTION_EACH_SIDE}.")
    parser.add_argument("--low-resolution-max-mean-reprojection-error-pixels", type=_parse_low_resolution_max_mean_reprojection_error_pixels, default=3.0, help="Maximum allowed trimmed-mean low-resolution homography reprojection error, in pixels. Values above this threshold force low-resolution offset fallback to zero. Default: 3.0.")
    parser.add_argument("--low-resolution-min-retained-match-count", type=_parse_low_resolution_min_retained_match_count, default=DEFAULT_LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT, help=f"Minimum retained low-resolution RANSAC match count required before projected-offset statistics are trusted. Values below this threshold skip low-resolution statistics and force fallback to zero. Default: {DEFAULT_LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT}.")
    parser.add_argument("--low-resolution-max-mean-projected-offset-meters", type=_parse_low_resolution_max_mean_projected_offset_meters, default=DEFAULT_LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS, help="Maximum allowed magnitude of the mean low-resolution projected offset, in meters. Values above this threshold force fallback to zero. Set to 0 to disable this gate. Default: 0.0.")
    parser.add_argument("--left-low-resolution-dom", default=None, help="Optional precomputed low-resolution DOM cube for the left input. Must be provided together with --right-low-resolution-dom.")
    parser.add_argument("--right-low-resolution-dom", default=None, help="Optional precomputed low-resolution DOM cube for the right input. Must be provided together with --left-low-resolution-dom.")
    parser.add_argument("--num-worker-parallel-cpu", type=_parse_num_worker_parallel_cpu, default=DEFAULT_NUM_WORKER_PARALLEL_CPU, help=f"Maximum worker-process count used when CPU tile parallelism is enabled. Must be within [1, {MAX_NUM_WORKER_PARALLEL_CPU}]. Default: {DEFAULT_NUM_WORKER_PARALLEL_CPU}.")
    parser.add_argument("--opencv-num-threads", type=_parse_opencv_num_threads, default=None, help="Optional OpenCV internal thread limit for CPU SIFT/FLANN work. Must be >= 1. Omit to keep OpenCV's default thread policy; set to 1 alongside multiple CPU workers to avoid oversubscription.")
    parser.add_argument("--use-parallel-cpu", dest="use_parallel_cpu", action="store_true", help="Enable CPU process-pool parallelism for tiled matching. Enabled by default.")
    parser.add_argument("--no-parallel-cpu", dest="use_parallel_cpu", action="store_false", help="Disable CPU process-pool parallelism and force serial tile matching.")
    parser.add_argument("--no-write-match-visualization", dest="write_match_visualization", action="store_false", help="Disable the default pre-RANSAC drawMatches PNG output written for the matched DOM pair.")
    parser.add_argument("--no-progress", dest="show_progress", action="store_false", help="Disable full-resolution tile progress output on stderr.")
    parser.add_argument("--omit-tile-details", dest="omit_tile_details", action="store_true", help="Omit per-tile detail records from the JSON printed to stdout while keeping top-level tile counters and summary diagnostics.")
    parser.add_argument("--include-tile-details", dest="omit_tile_details", action="store_false", help="Force per-tile detail records to remain in the JSON printed to stdout, even if config defaults requested omission.")
    parser.add_argument("--result-output", default=None, help="Optional JSON path used to persist the full image-match result, including per-tile details, before any stdout trimming is applied.")
    parser.add_argument("--match-visualization-output-path", default=None, help="Optional explicit output path for the pre-RANSAC drawMatches PNG written by the image-match stage.")
    parser.add_argument("--match-visualization-output-dir", default=None, help="Optional directory used when auto-naming the pre-RANSAC drawMatches PNG written by the image-match stage.")
    parser.add_argument("--match-visualization-scale", type=float, default=1.0 / 3.0, help="Image scale factor used when writing the pre-RANSAC drawMatches PNG. Defaults to 1/3 for a smaller preview.")
    parser.add_argument(
        "--visualization-mode",
        type=_parse_visualization_mode,
        default=DEFAULT_MATCH_VISUALIZATION_MODE,
        help=(
            "Visualization mode used for the pre-RANSAC match preview. "
            f"Supported values: {_format_supported_values(SUPPORTED_VISUALIZATION_MODES)}. "
            f"Default: {DEFAULT_MATCH_VISUALIZATION_MODE}."
        ),
    )
    parser.add_argument(
        "--memory-profile",
        type=_parse_memory_profile,
        default=DEFAULT_MEMORY_PROFILE,
        help=(
            "Memory profile used to select visualization defaults. "
            f"Supported values: {_format_supported_values(SUPPORTED_MEMORY_PROFILES)}. "
            f"Default: {DEFAULT_MEMORY_PROFILE}."
        ),
    )
    parser.add_argument(
        "--visualization-target-long-edge",
        type=int,
        default=None,
        help="Override the visualization long-edge target size when reduced previews are enabled.",
    )
    parser.add_argument(
        "--max-preview-pixels",
        type=int,
        default=None,
        help="Maximum pixel count allowed for visualization previews before additional reductions apply.",
    )
    parser.add_argument(
        "--preview-crop-margin-pixels",
        type=int,
        default=DEFAULT_PREVIEW_CROP_MARGIN_PIXELS,
        help=f"Extra margin added to cropped visualization windows. Default: {DEFAULT_PREVIEW_CROP_MARGIN_PIXELS}.",
    )
    parser.add_argument(
        "--preview-cache-dir",
        default=None,
        help="Directory for reduced-visualization preview cache cubes.",
    )
    parser.add_argument(
        "--preview-cache-source",
        type=_parse_preview_cache_source,
        default=DEFAULT_PREVIEW_CACHE_SOURCE,
        help=(
            "Preview cache selection mode used for reduced visualizations. "
            f"Supported values: {_format_supported_values(SUPPORTED_PREVIEW_CACHE_SOURCES)}. "
            f"Default: {DEFAULT_PREVIEW_CACHE_SOURCE.replace('_', '-')}"
            "."
        ),
    )
    parser.add_argument(
        "--preview-force-regenerate",
        action="store_true",
        help="Force regeneration of reduced preview cache cubes even when a cached preview exists.",
    )
    parser.add_argument(
        "--preview-level",
        type=int,
        default=None,
        help="Explicit pyramid level used for reduced visualization previews.",
    )
    parser.add_argument(
        "--use-tile-cache",
        action="store_true",
        default=False,
        help="Enable tile-aware I/O caching for DOM image reads",
    )
    parser.add_argument(
        "--tile-cache-max-mb",
        type=int,
        default=100,
        help="Maximum tile cache memory in MB (default: 100)",
    )
    parser.add_argument(
        "--adaptive-warmup-count",
        type=int,
        default=10,
        help="Number of reads to measure before deciding cache vs bypass",
    )
    parser.add_argument(
        "--adaptive-throughput-threshold-mbps",
        type=float,
        default=200.0,
        help="Throughput threshold (MB/s) for bypass decision",
    )
    parser.add_argument(
        "--adaptive-recheck-every",
        type=int,
        default=0,
        help="Re-evaluate bypass decision every N reads (0=never)",
    )
    parser.add_argument(
        "--use-gpu",
        action="store_true",
        default=False,
        help="Use GPU-accelerated SIFT via OpenCV CUDA (requires opencv-contrib-python with CUDA support)",
    )
    parser.add_argument(
        "--gpu-batch-size",
        type=int,
        default=DEFAULT_GPU_BATCH_SIZE,
        help=f"Number of tiles to batch for GPU SIFT processing (default: {DEFAULT_GPU_BATCH_SIZE})",
    )
    parser.add_argument(
        "--gpu-dynamic-batch",
        dest="gpu_dynamic_batch",
        action="store_true",
        help="Dynamically adjust GPU tile batch size during matching (default: enabled)",
    )
    parser.add_argument(
        "--no-gpu-dynamic-batch",
        dest="gpu_dynamic_batch",
        action="store_false",
        help="Disable dynamic GPU tile batch sizing",
    )
    parser.add_argument(
        "--gpu-min-batch-size",
        type=int,
        default=2,
        help="Minimum dynamic GPU batch size (default: 2)",
    )
    parser.add_argument(
        "--gpu-max-batch-size",
        type=int,
        default=16,
        help="Maximum dynamic GPU batch size for 8GB-class GPUs (default: 16)",
    )
    parser.set_defaults(write_match_visualization=True, use_parallel_cpu=True, enable_low_resolution_offset_estimation=False, enable_adaptive_routing=DEFAULT_ENABLE_ADAPTIVE_ROUTING, enable_tile_validity_prefilter=False, show_progress=True, gpu_dynamic_batch=True)
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
    if _argv_has_option(resolved_argv, "--match-preset-path"):
        if _argv_has_option(resolved_argv, "--matcher-method"):
            parser.error("--match-preset-path conflicts with --matcher-method")
        if _argv_has_option(resolved_argv, "--deep-match-config-path"):
            parser.error("--match-preset-path conflicts with --deep-match-config-path")
    args = parser.parse_args(resolved_argv)
    try:
        _validate_low_resolution_dom_pair_args(args.left_low_resolution_dom, args.right_low_resolution_dom)
    except ValueError as exc:
        parser.error(str(exc))
    if args.deep_match_mode == "import" and args.deep_match_manifest is None:
        parser.error("--deep-match-mode import requires --deep-match-manifest")
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
        tile_block_alignment_mode=args.tile_block_alignment_mode,
        minimum_value=args.minimum_value,
        maximum_value=args.maximum_value,
        lower_percent=args.lower_percent,
        upper_percent=args.upper_percent,
        invalid_values=tuple(args.invalid_value),
        special_pixel_abs_threshold=args.special_pixel_abs_threshold,
        min_valid_pixels=args.min_valid_pixels,
        valid_pixel_percent_threshold=args.valid_pixel_percent_threshold,
        invalid_pixel_radius=args.invalid_pixel_radius,
        enable_tile_validity_prefilter=args.enable_tile_validity_prefilter,
        tile_validity_cache_dir=args.tile_validity_cache_dir,
        tile_validity_cell_width=args.tile_validity_cell_width,
        tile_validity_cell_height=args.tile_validity_cell_height,
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
        enable_adaptive_routing=args.enable_adaptive_routing,
        adaptive_routing_profile=args.adaptive_routing_profile,
        adaptive_routing_deep_presets=getattr(args, "adaptive_routing_deep_presets", None),
        low_resolution_level=args.low_resolution_level,
        low_resolution_matching_target_long_edge=args.low_resolution_matching_target_long_edge,
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
        visualization_mode=args.visualization_mode,
        memory_profile=args.memory_profile,
        visualization_target_long_edge=args.visualization_target_long_edge,
        max_preview_pixels=args.max_preview_pixels,
        preview_crop_margin_pixels=args.preview_crop_margin_pixels,
        preview_cache_dir=args.preview_cache_dir,
        preview_cache_source=args.preview_cache_source,
        preview_force_regenerate=args.preview_force_regenerate,
        preview_level=args.preview_level,
        use_gpu=args.use_gpu,
        gpu_batch_size=args.gpu_batch_size,
        gpu_dynamic_batch=args.gpu_dynamic_batch,
        gpu_min_batch_size=args.gpu_min_batch_size,
        gpu_max_batch_size=args.gpu_max_batch_size,
        deep_match_config_path=args.deep_match_config_path,
        deep_match_mode=args.deep_match_mode,
        deep_match_temp_root_dir=(
            args.deep_match_temp_root_dir
            if args.deep_match_temp_root_dir is not None
            else _default_deep_match_temp_root_dir(
                metadata_output=args.metadata_output,
                left_output_key=args.left_output_key,
            )
        ),
        deep_match_manifest=args.deep_match_manifest,
        use_tile_cache=args.use_tile_cache,
        tile_cache_max_mb=args.tile_cache_max_mb,
        adaptive_warmup_count=args.adaptive_warmup_count,
        adaptive_throughput_threshold_mbps=args.adaptive_throughput_threshold_mbps,
        adaptive_recheck_every=args.adaptive_recheck_every,
    )
    result_output_path = None
    if args.result_output is not None:
        result_output_path = _write_json_output(args.result_output, result)

    stdout_result = _stdout_result_payload(result, omit_tile_details=args.omit_tile_details)
    if result_output_path is not None:
        stdout_result = {
            **stdout_result,
            "result_output": result_output_path,
        }
    print(json.dumps(stdout_result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
