"""Shared parameter catalog for ControlNet construction entry points."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


try:
    from .parameter_profiles import PARAMETER_PROFILE_NAMES
except ImportError:
    from parameter_profiles import PARAMETER_PROFILE_NAMES

try:
    from image_match.adaptive_routing import DEFAULT_ADAPTIVE_ROUTING_PROFILE, SUPPORTED_ADAPTIVE_ROUTING_PROFILES
    from image_match.tile_block_alignment import DEFAULT_TILE_BLOCK_ALIGNMENT_MODE, SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES
    from image_match.match_visualization import (
        DEFAULT_MEMORY_PROFILE,
        DEFAULT_PREVIEW_CACHE_SOURCE,
        DEFAULT_PREVIEW_CROP_MARGIN_PIXELS,
        DEFAULT_VISUALIZATION_MODE,
        SUPPORTED_MEMORY_PROFILES,
        SUPPORTED_PREVIEW_CACHE_SOURCES,
        SUPPORTED_VISUALIZATION_MODES,
    )
    from image_match.tile_matching import DEFAULT_GPU_BATCH_SIZE, DEFAULT_MATCHER_METHOD, SUPPORTED_MATCHER_METHODS
except ImportError:
    DEFAULT_ADAPTIVE_ROUTING_PROFILE = "balanced"
    SUPPORTED_ADAPTIVE_ROUTING_PROFILES = ("balanced", "strict", "relaxed", "fast")
    DEFAULT_TILE_BLOCK_ALIGNMENT_MODE = "off"
    SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES = ("off", "auto", "isis-storage")
    DEFAULT_MEMORY_PROFILE = "balanced"
    DEFAULT_PREVIEW_CACHE_SOURCE = "auto"
    DEFAULT_PREVIEW_CROP_MARGIN_PIXELS = 256
    DEFAULT_VISUALIZATION_MODE = "auto"
    SUPPORTED_MEMORY_PROFILES = ("high-memory", "balanced", "low-memory")
    SUPPORTED_PREVIEW_CACHE_SOURCES = ("auto", "matching_cache", "visualization_cache", "disabled")
    SUPPORTED_VISUALIZATION_MODES = ("auto", "full", "reduced", "cropped", "reduced_cropped")
    DEFAULT_GPU_BATCH_SIZE = 4
    DEFAULT_MATCHER_METHOD = "bf"
    SUPPORTED_MATCHER_METHODS = ("bf", "flann", "superpoint", "superglue", "lightglue", "loftr")


DEFAULT_DEEP_MATCH_MODE = "direct"
DEFAULT_LOW_RESOLUTION_LEVEL = 3
DEFAULT_PRE_RANSAC_MAX_GROUND_DISTANCE_KM = 1.0
DEFAULT_PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY = "drop"
SUPPORTED_PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICIES = ("drop", "keep")
DEFAULT_NUM_WORKER_PARALLEL_CPU = 8
MAX_NUM_WORKER_PARALLEL_CPU = 4096
SUPPORTED_DEEP_MATCH_MODES = ("direct", "export", "import")

RUN_PIPELINE = "run_pipeline_example"
IMAGE_MATCH = "image_match"
FROM_ORI_MATCH = "controlnet_stereopair.from-ori-match"
FROM_DOM = "controlnet_stereopair.from-dom"
FROM_DOM_BATCH = "controlnet_stereopair.from-dom-batch"

_CONTROLNET_ENTRYPOINTS = (RUN_PIPELINE, FROM_ORI_MATCH, FROM_DOM, FROM_DOM_BATCH)
_MATCH_ENTRYPOINTS = (RUN_PIPELINE, IMAGE_MATCH, FROM_ORI_MATCH)
_DOM_ENTRYPOINTS = (RUN_PIPELINE, FROM_DOM, FROM_DOM_BATCH)
_ALL_ENTRYPOINTS = (RUN_PIPELINE, IMAGE_MATCH, FROM_ORI_MATCH, FROM_DOM, FROM_DOM_BATCH)
_PRE_RANSAC_GROUND_FILTER_ENTRYPOINTS = (RUN_PIPELINE, IMAGE_MATCH, FROM_ORI_MATCH, FROM_DOM, FROM_DOM_BATCH)
RUN_PIPELINE_CLI_PARAMETER_NAMES = frozenset(
    {
        "work_dir",
        "original_list",
        "dom_list",
        "config",
        "python",
        "deep_match_mode",
        "deep_match_temp_root_dir",
        "deep_match_manifest_dir",
        "deep_match_manifest_summary",
        "parameter_profile",
        "skip_final_merge",
        "post_merge_control_measure",
        "post_merge_output",
        "post_merge_decimals",
        "matcher_method",
        "match_preset_path",
        "deep_match_config_path",
        "valid_pixel_percent_threshold",
        "invalid_pixel_radius",
        "pre_ransac_max_ground_distance_km",
        "pre_ransac_ground_lookup_failure_policy",
        "enable_low_resolution_offset_estimation",
        "low_resolution_level",
        "low_resolution_max_mean_reprojection_error_pixels",
        "low_resolution_min_retained_match_count",
        "low_resolution_max_mean_projected_offset_meters",
        "enable_adaptive_routing",
        "adaptive_routing_profile",
        "use_parallel_cpu",
        "num_worker_parallel_cpu",
        "opencv_num_threads",
        "visualization_mode",
        "memory_profile",
        "visualization_target_long_edge",
        "preview_crop_margin_pixels",
        "preview_cache_source",
        "pair_id_prefix",
        "pair_id_start",
        "network_id",
        "description",
        "merged_net",
        "merge_script",
        "merge_log",
        "pair_list",
        "cnetmerge",
        "timing_json",
        "validate_parameters_only",
        "strict_parameter_validation",
    }
)


@dataclass(frozen=True, slots=True)
class ParameterGroup:
    name: str
    title: str
    description: str


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    name: str
    group: str
    cli_flag: str | None
    config_path: str | None
    value_type: str
    default: Any
    allowed_values: tuple[Any, ...] | None
    min_value: int | float | None
    max_value: int | float | None
    entrypoints: tuple[str, ...]
    help: str


PARAMETER_GROUPS = (
    ParameterGroup("inputs", "Inputs", "Input lists, work directory, config, and Python executable."),
    ParameterGroup("pipeline", "Pipeline", "End-to-end pipeline mode and deep-match manifest controls."),
    ParameterGroup("matching", "Matching", "Feature matcher, presets, and classic SIFT tuning."),
    ParameterGroup("tile", "Tile", "Tile geometry and validity-prefilter controls."),
    ParameterGroup("low_resolution", "Low Resolution", "Low-resolution offset-estimation inputs and gates."),
    ParameterGroup("adaptive_routing", "Adaptive Routing", "Pair-level adaptive matcher routing controls."),
    ParameterGroup("execution", "Execution", "CPU and GPU execution controls."),
    ParameterGroup("visualization", "Visualization", "Match-visualization output and preview-cache controls."),
    ParameterGroup("controlnet", "ControlNet", "Control-network generation, merge, and pair metadata controls."),
    ParameterGroup("reporting", "Reporting", "Reports, metadata, logging, and validation strictness."),
)

GROUP_BY_NAME = {group.name: group for group in PARAMETER_GROUPS}


def _flag(name: str) -> str:
    return "--" + name.replace("_", "-")


def _image_match_path(name: str) -> str:
    return f"ImageMatch.{name}"


def _spec(
    name: str,
    group: str,
    *,
    cli_flag: str | None = None,
    config_path: str | None = None,
    value_type: str = "string",
    default: Any = None,
    allowed_values: tuple[Any, ...] | None = None,
    min_value: int | float | None = None,
    max_value: int | float | None = None,
    entrypoints: tuple[str, ...] = (RUN_PIPELINE,),
    help: str,
) -> ParameterSpec:
    return ParameterSpec(
        name=name,
        group=group,
        cli_flag=_flag(name) if cli_flag is None else cli_flag,
        config_path=config_path,
        value_type=value_type,
        default=default,
        allowed_values=allowed_values,
        min_value=min_value,
        max_value=max_value,
        entrypoints=entrypoints,
        help=help,
    )


PARAMETERS = (
    _spec("work_dir", "inputs", config_path=None, entrypoints=(RUN_PIPELINE,), help="Pipeline work directory."),
    _spec("original_list", "inputs", config_path=None, entrypoints=(RUN_PIPELINE, FROM_ORI_MATCH), help="Input ORI image list."),
    _spec("dom_list", "inputs", config_path=None, entrypoints=(RUN_PIPELINE, FROM_DOM_BATCH), help="Input DOM image list."),
    _spec("config", "inputs", config_path=None, entrypoints=_CONTROLNET_ENTRYPOINTS, help="ControlNet JSON config path."),
    _spec("python", "inputs", config_path=None, entrypoints=(RUN_PIPELINE,), help="Python executable used by shell wrappers."),
    _spec(
        "deep_match_mode",
        "pipeline",
        config_path=_image_match_path("deep_match_mode"),
        default=DEFAULT_DEEP_MATCH_MODE,
        allowed_values=SUPPORTED_DEEP_MATCH_MODES,
        entrypoints=(RUN_PIPELINE, IMAGE_MATCH),
        help="Deep-match execution mode.",
    ),
    _spec("deep_match_temp_root_dir", "pipeline", config_path=_image_match_path("deep_match_temp_root_dir"), entrypoints=(RUN_PIPELINE, IMAGE_MATCH), help="Root directory for exported deep-match tile payloads."),
    _spec("deep_match_manifest_dir", "pipeline", config_path=_image_match_path("deep_match_manifest_dir"), entrypoints=(RUN_PIPELINE,), help="Directory containing deep-match manifests."),
    _spec("deep_match_manifest", "pipeline", config_path=_image_match_path("deep_match_manifest"), entrypoints=(IMAGE_MATCH,), help="Deep-match manifest tasks JSON path."),
    _spec("deep_match_manifest_summary", "pipeline", config_path=_image_match_path("deep_match_manifest_summary"), entrypoints=(RUN_PIPELINE,), help="Manifest summary JSON path."),
    _spec("parameter_profile", "pipeline", allowed_values=PARAMETER_PROFILE_NAMES, entrypoints=(RUN_PIPELINE,), help="Named matching-parameter profile applied below config, preset, and CLI values."),
    _spec("skip_final_merge", "pipeline", value_type="bool", entrypoints=(RUN_PIPELINE,), help="Skip the final control-network merge step."),
    _spec("post_merge_control_measure", "pipeline", value_type="bool", default=False, entrypoints=(RUN_PIPELINE,), help="Control measure run after merge."),
    _spec("post_merge_output", "pipeline", entrypoints=(RUN_PIPELINE,), help="Post-merge control-measure output path."),
    _spec("post_merge_decimals", "pipeline", value_type="int", min_value=0, entrypoints=(RUN_PIPELINE,), help="Decimal precision for post-merge output."),
    _spec(
        "matcher_method",
        "matching",
        config_path=_image_match_path("matcher_method"),
        default=DEFAULT_MATCHER_METHOD,
        allowed_values=tuple(SUPPORTED_MATCHER_METHODS),
        entrypoints=_MATCH_ENTRYPOINTS,
        help="Feature matcher method.",
    ),
    _spec("match_preset_path", "matching", config_path=_image_match_path("match_preset_path"), entrypoints=_MATCH_ENTRYPOINTS, help="Image-match preset JSON path."),
    _spec("deep_match_config_path", "matching", config_path=_image_match_path("deep_match_config_path"), entrypoints=_MATCH_ENTRYPOINTS, help="Deep matcher runtime config path."),
    _spec("ratio_test", "matching", config_path=_image_match_path("ratio_test"), value_type="float", min_value=0.0, max_value=1.0, entrypoints=_MATCH_ENTRYPOINTS, help="Descriptor ratio-test threshold."),
    _spec("pre_ransac_max_ground_distance_km", "matching", config_path=_image_match_path("pre_ransac_max_ground_distance_km"), value_type="float", default=DEFAULT_PRE_RANSAC_MAX_GROUND_DISTANCE_KM, min_value=0.0, entrypoints=_PRE_RANSAC_GROUND_FILTER_ENTRYPOINTS, help="Maximum paired ground distance retained before RANSAC; 0 disables the filter."),
    _spec("pre_ransac_ground_lookup_failure_policy", "matching", config_path=_image_match_path("pre_ransac_ground_lookup_failure_policy"), default=DEFAULT_PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY, allowed_values=SUPPORTED_PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICIES, entrypoints=_PRE_RANSAC_GROUND_FILTER_ENTRYPOINTS, help="Policy for match points whose cube-to-ground lookup fails before RANSAC."),
    _spec("max_features", "matching", config_path=_image_match_path("max_features"), value_type="int", min_value=1, entrypoints=_MATCH_ENTRYPOINTS, help="Maximum SIFT feature count."),
    _spec("sift_octave_layers", "matching", config_path=_image_match_path("sift_octave_layers"), value_type="int", min_value=1, entrypoints=_MATCH_ENTRYPOINTS, help="SIFT octave layer count."),
    _spec("sift_contrast_threshold", "matching", config_path=_image_match_path("sift_contrast_threshold"), value_type="float", min_value=0.0, entrypoints=_MATCH_ENTRYPOINTS, help="SIFT contrast threshold."),
    _spec("sift_edge_threshold", "matching", config_path=_image_match_path("sift_edge_threshold"), value_type="float", min_value=0.0, entrypoints=_MATCH_ENTRYPOINTS, help="SIFT edge threshold."),
    _spec("sift_sigma", "matching", config_path=_image_match_path("sift_sigma"), value_type="float", min_value=0.0, entrypoints=_MATCH_ENTRYPOINTS, help="SIFT Gaussian sigma."),
    _spec("max_image_dimension", "tile", config_path=_image_match_path("max_image_dimension"), value_type="int", min_value=1, entrypoints=_MATCH_ENTRYPOINTS, help="Maximum full-image dimension before tiling."),
    _spec("valid_pixel_percent_threshold", "tile", config_path=_image_match_path("valid_pixel_percent_threshold"), value_type="float", default=0.0, min_value=0.0, max_value=1.0, entrypoints=_MATCH_ENTRYPOINTS, help="Minimum valid-pixel ratio required before matching a tile."),
    _spec("invalid_pixel_radius", "tile", config_path=_image_match_path("invalid_pixel_radius"), value_type="int", default=1, min_value=0, max_value=100, entrypoints=_MATCH_ENTRYPOINTS, help="Invalid-pixel and image-border suppression radius."),
    _spec("sub_block_size_x", "tile", config_path=_image_match_path("sub_block_size_x"), value_type="int", min_value=1, entrypoints=_MATCH_ENTRYPOINTS, help="Tile width in pixels."),
    _spec("sub_block_size_y", "tile", config_path=_image_match_path("sub_block_size_y"), value_type="int", min_value=1, entrypoints=_MATCH_ENTRYPOINTS, help="Tile height in pixels."),
    _spec("overlap_size_x", "tile", config_path=_image_match_path("overlap_size_x"), value_type="int", min_value=0, entrypoints=_MATCH_ENTRYPOINTS, help="Horizontal tile overlap in pixels."),
    _spec("overlap_size_y", "tile", config_path=_image_match_path("overlap_size_y"), value_type="int", min_value=0, entrypoints=_MATCH_ENTRYPOINTS, help="Vertical tile overlap in pixels."),
    _spec(
        "tile_block_alignment_mode",
        "tile",
        config_path=_image_match_path("tile_block_alignment_mode"),
        default=DEFAULT_TILE_BLOCK_ALIGNMENT_MODE,
        allowed_values=tuple(SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES),
        entrypoints=_MATCH_ENTRYPOINTS,
        help="Full-resolution block alignment mode for ISIS storage tile boundaries.",
    ),
    _spec("enable_tile_validity_prefilter", "tile", config_path=_image_match_path("enable_tile_validity_prefilter"), value_type="bool", default=False, entrypoints=_MATCH_ENTRYPOINTS, help="Enable coarse tile validity filtering."),
    _spec("tile_validity_cache_dir", "tile", config_path=_image_match_path("tile_validity_cache_dir"), entrypoints=_MATCH_ENTRYPOINTS, help="Tile validity cache directory."),
    _spec("tile_validity_cell_width", "tile", config_path=_image_match_path("tile_validity_cell_width"), value_type="int", min_value=1, entrypoints=_MATCH_ENTRYPOINTS, help="Tile validity cell width."),
    _spec("tile_validity_cell_height", "tile", config_path=_image_match_path("tile_validity_cell_height"), value_type="int", min_value=1, entrypoints=_MATCH_ENTRYPOINTS, help="Tile validity cell height."),
    _spec("enable_low_resolution_offset_estimation", "low_resolution", config_path=_image_match_path("enable_low_resolution_offset_estimation"), value_type="bool", default=False, entrypoints=_MATCH_ENTRYPOINTS, help="Enable low-resolution offset estimation."),
    _spec("low_resolution_level", "low_resolution", config_path=_image_match_path("low_resolution_level"), value_type="int", default=DEFAULT_LOW_RESOLUTION_LEVEL, min_value=0, entrypoints=_MATCH_ENTRYPOINTS, help="Reduced pyramid level for low-resolution matching."),
    _spec("low_resolution_matching_target_long_edge", "low_resolution", config_path=_image_match_path("low_resolution_matching_target_long_edge"), value_type="int", min_value=1, entrypoints=_MATCH_ENTRYPOINTS, help="Target long edge for low-resolution matching."),
    _spec("low_resolution_trim_fraction_each_side", "low_resolution", config_path=_image_match_path("low_resolution_trim_fraction_each_side"), value_type="float", min_value=0.0, max_value=0.5, entrypoints=_MATCH_ENTRYPOINTS, help="Trim fraction for low-resolution offset statistics."),
    _spec("low_resolution_max_mean_reprojection_error_pixels", "low_resolution", config_path=_image_match_path("low_resolution_max_mean_reprojection_error_pixels"), value_type="float", min_value=0.0, entrypoints=_MATCH_ENTRYPOINTS, help="Maximum mean reprojection error for low-resolution offsets."),
    _spec("low_resolution_min_retained_match_count", "low_resolution", config_path=_image_match_path("low_resolution_min_retained_match_count"), value_type="int", min_value=0, entrypoints=_MATCH_ENTRYPOINTS, help="Minimum retained matches for low-resolution statistics."),
    _spec("low_resolution_max_mean_projected_offset_meters", "low_resolution", config_path=_image_match_path("low_resolution_max_mean_projected_offset_meters"), value_type="float", min_value=0.0, entrypoints=_MATCH_ENTRYPOINTS, help="Maximum mean projected low-resolution offset."),
    _spec("left_low_resolution_dom", "low_resolution", config_path=_image_match_path("left_low_resolution_dom"), entrypoints=_MATCH_ENTRYPOINTS, help="Left prebuilt low-resolution DOM path."),
    _spec("right_low_resolution_dom", "low_resolution", config_path=_image_match_path("right_low_resolution_dom"), entrypoints=_MATCH_ENTRYPOINTS, help="Right prebuilt low-resolution DOM path."),
    _spec("enable_adaptive_routing", "adaptive_routing", cli_flag="--adaptive-routing", config_path=_image_match_path("enable_adaptive_routing"), value_type="bool", default=False, entrypoints=_MATCH_ENTRYPOINTS, help="Enable adaptive matcher routing."),
    _spec("adaptive_routing_profile", "adaptive_routing", config_path=_image_match_path("adaptive_routing_profile"), default=DEFAULT_ADAPTIVE_ROUTING_PROFILE, allowed_values=tuple(SUPPORTED_ADAPTIVE_ROUTING_PROFILES), entrypoints=_MATCH_ENTRYPOINTS, help="Adaptive-routing quality profile."),
    _spec("adaptive_routing_deep_presets", "adaptive_routing", config_path=_image_match_path("adaptive_routing_deep_presets"), value_type="mapping", entrypoints=_MATCH_ENTRYPOINTS, help="Adaptive-routing deep preset map."),
    _spec("use_parallel_cpu", "execution", config_path=_image_match_path("use_parallel_cpu"), value_type="bool", default=True, entrypoints=_MATCH_ENTRYPOINTS, help="Enable CPU process parallelism."),
    _spec("num_worker_parallel_cpu", "execution", config_path=_image_match_path("num_worker_parallel_cpu"), value_type="int", default=DEFAULT_NUM_WORKER_PARALLEL_CPU, min_value=1, max_value=MAX_NUM_WORKER_PARALLEL_CPU, entrypoints=_MATCH_ENTRYPOINTS, help="CPU worker-process count."),
    _spec("opencv_num_threads", "execution", config_path=_image_match_path("opencv_num_threads"), value_type="int", min_value=1, entrypoints=_MATCH_ENTRYPOINTS, help="OpenCV internal thread limit for CPU SIFT/FLANN work."),
    _spec("use_gpu", "execution", config_path=_image_match_path("use_gpu"), value_type="bool", default=False, entrypoints=_MATCH_ENTRYPOINTS, help="Enable GPU SIFT route."),
    _spec("gpu_batch_size", "execution", config_path=_image_match_path("gpu_batch_size"), value_type="int", default=DEFAULT_GPU_BATCH_SIZE, min_value=1, entrypoints=_MATCH_ENTRYPOINTS, help="GPU SIFT batch size."),
    _spec("gpu_dynamic_batch", "execution", config_path=_image_match_path("gpu_dynamic_batch"), value_type="bool", default=True, entrypoints=_MATCH_ENTRYPOINTS, help="Enable dynamic GPU batch sizing."),
    _spec("gpu_min_batch_size", "execution", config_path=_image_match_path("gpu_min_batch_size"), value_type="int", min_value=1, entrypoints=_MATCH_ENTRYPOINTS, help="Minimum dynamic GPU batch size."),
    _spec("gpu_max_batch_size", "execution", config_path=_image_match_path("gpu_max_batch_size"), value_type="int", min_value=1, entrypoints=_MATCH_ENTRYPOINTS, help="Maximum dynamic GPU batch size."),
    _spec("write_match_visualization", "visualization", config_path=_image_match_path("write_match_visualization"), value_type="bool", default=True, entrypoints=_MATCH_ENTRYPOINTS, help="Write match visualization PNG output."),
    _spec("match_visualization_output_path", "visualization", config_path=_image_match_path("match_visualization_output_path"), entrypoints=_MATCH_ENTRYPOINTS, help="Explicit match visualization output path."),
    _spec("match_visualization_output_dir", "visualization", config_path=_image_match_path("match_visualization_output_dir"), entrypoints=_MATCH_ENTRYPOINTS, help="Directory for auto-named match visualizations."),
    _spec("match_visualization_scale", "visualization", config_path=_image_match_path("match_visualization_scale"), value_type="float", min_value=0.0, entrypoints=_MATCH_ENTRYPOINTS, help="Match visualization image scale."),
    _spec("visualization_mode", "visualization", config_path=_image_match_path("visualization_mode"), default=DEFAULT_VISUALIZATION_MODE, allowed_values=tuple(SUPPORTED_VISUALIZATION_MODES), entrypoints=_MATCH_ENTRYPOINTS, help="Visualization preview mode."),
    _spec("memory_profile", "visualization", config_path=_image_match_path("memory_profile"), default=DEFAULT_MEMORY_PROFILE, allowed_values=tuple(SUPPORTED_MEMORY_PROFILES), entrypoints=_MATCH_ENTRYPOINTS, help="Visualization memory profile."),
    _spec("visualization_target_long_edge", "visualization", config_path=_image_match_path("visualization_target_long_edge"), value_type="int", min_value=1, entrypoints=_MATCH_ENTRYPOINTS, help="Visualization target long edge."),
    _spec("max_preview_pixels", "visualization", config_path=_image_match_path("max_preview_pixels"), value_type="int", min_value=1, entrypoints=_MATCH_ENTRYPOINTS, help="Maximum visualization preview pixels."),
    _spec("preview_crop_margin_pixels", "visualization", config_path=_image_match_path("preview_crop_margin_pixels"), value_type="int", default=DEFAULT_PREVIEW_CROP_MARGIN_PIXELS, min_value=0, entrypoints=_MATCH_ENTRYPOINTS, help="Preview crop margin in pixels."),
    _spec("preview_cache_dir", "visualization", config_path=_image_match_path("preview_cache_dir"), entrypoints=_MATCH_ENTRYPOINTS, help="Visualization preview cache directory."),
    _spec("preview_cache_source", "visualization", config_path=_image_match_path("preview_cache_source"), default=DEFAULT_PREVIEW_CACHE_SOURCE, allowed_values=tuple(SUPPORTED_PREVIEW_CACHE_SOURCES), entrypoints=_MATCH_ENTRYPOINTS, help="Visualization preview cache source."),
    _spec("preview_force_regenerate", "visualization", config_path=_image_match_path("preview_force_regenerate"), value_type="bool", default=False, entrypoints=_MATCH_ENTRYPOINTS, help="Regenerate visualization preview cache."),
    _spec("preview_level", "visualization", config_path=_image_match_path("preview_level"), value_type="int", min_value=0, entrypoints=_MATCH_ENTRYPOINTS, help="Explicit visualization preview pyramid level."),
    _spec("pair_id", "controlnet", config_path="ControlNet.pair_id", entrypoints=(FROM_DOM,), help="ControlNet pair identifier."),
    _spec("pair_id_prefix", "controlnet", config_path="ControlNet.pair_id_prefix", entrypoints=(RUN_PIPELINE, FROM_ORI_MATCH, FROM_DOM_BATCH), help="Generated pair identifier prefix."),
    _spec("pair_id_start", "controlnet", config_path="ControlNet.pair_id_start", value_type="int", min_value=1, entrypoints=(RUN_PIPELINE, FROM_ORI_MATCH, FROM_DOM_BATCH), help="Starting generated pair identifier number."),
    _spec("network_id", "controlnet", config_path="ControlNet.network_id", entrypoints=_CONTROLNET_ENTRYPOINTS, help="Control network identifier."),
    _spec("description", "controlnet", config_path="ControlNet.description", entrypoints=_CONTROLNET_ENTRYPOINTS, help="Control network description."),
    _spec("binary", "controlnet", config_path="ControlNet.binary", value_type="bool", entrypoints=_CONTROLNET_ENTRYPOINTS, help="Write binary control network output."),
    _spec("merged_net", "controlnet", config_path="ControlNet.merged_net", entrypoints=(RUN_PIPELINE, FROM_DOM_BATCH), help="Merged control network output path."),
    _spec("merge_script", "controlnet", config_path="ControlNet.merge_script", entrypoints=(RUN_PIPELINE, FROM_DOM_BATCH), help="Generated merge script path."),
    _spec("merge_log", "controlnet", config_path="ControlNet.merge_log", entrypoints=(RUN_PIPELINE, FROM_DOM_BATCH), help="Merge log path."),
    _spec("pair_list", "controlnet", config_path="ControlNet.pair_list", entrypoints=(RUN_PIPELINE, FROM_DOM_BATCH), help="ControlNet pair list path."),
    _spec("cnetmerge", "controlnet", config_path="ControlNet.cnetmerge", entrypoints=(RUN_PIPELINE, FROM_DOM_BATCH), help="cnetmerge executable path."),
    _spec("metadata_output", "reporting", config_path="Reporting.metadata_output", entrypoints=_ALL_ENTRYPOINTS, help="Metadata JSON output path."),
    _spec("result_output", "reporting", config_path="Reporting.result_output", entrypoints=_ALL_ENTRYPOINTS, help="Result JSON output path."),
    _spec("report_path", "reporting", config_path="Reporting.report_path", entrypoints=(RUN_PIPELINE, FROM_DOM, FROM_ORI_MATCH), help="Single report JSON path."),
    _spec("report_dir", "reporting", config_path="Reporting.report_dir", entrypoints=(RUN_PIPELINE, FROM_DOM_BATCH), help="Report directory path."),
    _spec("timing_json", "reporting", config_path="Reporting.timing_json", entrypoints=(RUN_PIPELINE,), help="Timing JSON output path."),
    _spec("omit_tile_details", "reporting", config_path="Reporting.omit_tile_details", value_type="bool", default=False, entrypoints=(RUN_PIPELINE, IMAGE_MATCH), help="Omit per-tile detail records."),
    _spec("omit_detail_records", "reporting", config_path="Reporting.omit_detail_records", value_type="bool", default=False, entrypoints=(RUN_PIPELINE, FROM_DOM_BATCH), help="Omit per-pair detail records."),
    _spec("log_level", "reporting", config_path="Reporting.log_level", default="info", allowed_values=("debug", "info", "warning", "error"), entrypoints=_ALL_ENTRYPOINTS, help="Logging verbosity."),
    _spec("validate_parameters_only", "reporting", value_type="bool", default=False, entrypoints=(RUN_PIPELINE,), help="Validate effective parameters and exit before running pipeline steps."),
    _spec("strict_parameter_validation", "reporting", cli_flag="--strict-parameter-validation", config_path="Reporting.strict_parameter_validation", value_type="bool", default=False, entrypoints=(RUN_PIPELINE,), help="Promote parameter validation warnings to errors."),
)

PARAMETER_BY_NAME = {parameter.name: parameter for parameter in PARAMETERS}


def parameters_for_entrypoint(entrypoint: str) -> tuple[ParameterSpec, ...]:
    """Return catalog parameters supported by an entry point."""

    return tuple(parameter for parameter in PARAMETERS if entrypoint in parameter.entrypoints)


def grouped_parameters_for_entrypoint(entrypoint: str) -> dict[str, tuple[ParameterSpec, ...]]:
    """Return entry-point parameters grouped in catalog order, omitting empty groups."""

    parameters = parameters_for_entrypoint(entrypoint)
    grouped: dict[str, tuple[ParameterSpec, ...]] = {}
    for group in PARAMETER_GROUPS:
        group_parameters = tuple(parameter for parameter in parameters if parameter.group == group.name)
        if group_parameters:
            grouped[group.name] = group_parameters
    return grouped


def parameter_catalog_as_dict(entrypoint: str | None = None) -> dict[str, Any]:
    """Return a JSON-serializable catalog summary."""

    parameters = PARAMETERS if entrypoint is None else parameters_for_entrypoint(entrypoint)
    active_group_names = {parameter.group for parameter in parameters}
    groups = [group for group in PARAMETER_GROUPS if entrypoint is None or group.name in active_group_names]
    return {
        "groups": [asdict(group) for group in groups],
        "parameters": [_parameter_as_dict(parameter, entrypoint) for parameter in parameters],
    }


def cli_flag_for_entrypoint(parameter: ParameterSpec, entrypoint: str | None) -> str | None:
    """Return the CLI flag accepted by an entry point for a catalog parameter."""

    if entrypoint == RUN_PIPELINE and parameter.name not in RUN_PIPELINE_CLI_PARAMETER_NAMES:
        return None
    return parameter.cli_flag


def _parameter_as_dict(parameter: ParameterSpec, entrypoint: str | None) -> dict[str, Any]:
    data = asdict(parameter)
    data["cli_flag"] = cli_flag_for_entrypoint(parameter, entrypoint)
    return data
