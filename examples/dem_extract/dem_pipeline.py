"""End-to-end DEM extraction pipeline orchestration.

Author: Geng Xun
Created: 2026-05-10
Last Modified: 2026-05-14
Updated: 2026-05-10  Geng Xun added sparse stereo DEM orchestration from original-image and DOM matching routes.
Updated: 2026-05-10  Geng Xun added optional `.key` refinement stages between matching and DEM triangulation.
Updated: 2026-05-14  Geng Xun resolved merge conflicts by preferring shared image_match imports with compatibility fallbacks.

This module bridges the existing ``controlnet_construct`` matching helpers with
``dem_extract.isis_stereo_dem`` so a stereo DEM can be generated from either
original-image matching or DOM matching without duplicating the matching or DEM
triangulation implementations.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any, Mapping

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from dem_extract import isis_stereo_dem
    from dem_extract.runtime import write_summary_json
    from controlnet_construct.dom2ori import convert_paired_dom_keypoints_to_original
    try:
        from image_match.image_match import (
            load_image_match_defaults_from_config,
            match_dom_pair_to_key_files,
            match_ori_pair_to_key_files,
        )
        from image_match.stereo_ransac import filter_stereo_pair_key_files_with_ransac
    except ImportError:
        from controlnet_construct.image_match import (
            load_image_match_defaults_from_config,
            match_dom_pair_to_key_files,
            match_ori_pair_to_key_files,
        )
        from controlnet_construct.stereo_ransac import filter_stereo_pair_key_files_with_ransac
    from controlnet_construct.tie_point_merge_in_overlap import merge_stereo_pair_key_files
else:
    from . import isis_stereo_dem
    from .runtime import write_summary_json
    from controlnet_construct.dom2ori import convert_paired_dom_keypoints_to_original
    try:
        from image_match.image_match import (
            load_image_match_defaults_from_config,
            match_dom_pair_to_key_files,
            match_ori_pair_to_key_files,
        )
        from image_match.stereo_ransac import filter_stereo_pair_key_files_with_ransac
    except ImportError:
        from controlnet_construct.image_match import (
            load_image_match_defaults_from_config,
            match_dom_pair_to_key_files,
            match_ori_pair_to_key_files,
        )
        from controlnet_construct.stereo_ransac import filter_stereo_pair_key_files_with_ransac
    from controlnet_construct.tie_point_merge_in_overlap import merge_stereo_pair_key_files


DEFAULT_CONFIG_PATH = Path(__file__).with_name("dem_config.example.json")
DEFAULT_WORK_DIR = Path("work") / "dem_extract"


@dataclass(frozen=True, slots=True)
class PipelinePaths:
    work_dir: Path
    output_dem_cube: Path
    left_dom_key: Path
    right_dom_key: Path
    left_dom_merged_key: Path
    right_dom_merged_key: Path
    left_dom_ransac_key: Path
    right_dom_ransac_key: Path
    left_ori_key: Path
    right_ori_key: Path
    left_refined_key: Path
    right_refined_key: Path
    point_cloud_output: Path
    dem_summary_output: Path
    quality_prefix: Path
    pipeline_summary_output: Path
    dom_match_metadata_output: Path
    dom_merge_summary_output: Path
    dom_ransac_summary_output: Path
    dom2ori_summary_output: Path
    ori_match_summary_output: Path
    key_refinement_summary_output: Path
    match_visualization_output_dir: Path


@dataclass(frozen=True, slots=True)
class DemOptions:
    aggregation: str = "median"
    value_type: str = "radius_m"
    datum_radius_m: float | None = None
    nodata_value: float = -9999.0
    max_error_m: float | None = None
    min_sepang_deg: float | None = None
    min_radius_m: float | None = None
    max_radius_m: float | None = None


@dataclass(frozen=True, slots=True)
class KeyRefinementConfig:
    stages: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DomFilterOptions:
    merge_decimals: int = 3
    skip_merge: bool = False
    ransac_reproj_threshold: float = 3.0
    ransac_confidence: float = 0.995
    ransac_max_iters: int = 5000
    ransac_mode: str = "loose"
    loose_ransac_keep_threshold: float = 1.0


MATCH_OPTION_ALIASES = {
    "sub_block_size_x": "block_width",
    "subBlockSizeX": "block_width",
    "SubBlockSizeX": "block_width",
    "sub_block_size_y": "block_height",
    "subBlockSizeY": "block_height",
    "SubBlockSizeY": "block_height",
    "overlap_size_x": "overlap_x",
    "overlapSizeX": "overlap_x",
    "OverlapSizeX": "overlap_x",
    "overlap_size_y": "overlap_y",
    "overlapSizeY": "overlap_y",
    "OverlapSizeY": "overlap_y",
    "invalid_value": "invalid_values",
    "invalid_values": "invalid_values",
    "invalidValue": "invalid_values",
    "invalidValues": "invalid_values",
}

CORE_MATCH_OPTIONS = {
    "adaptive_recheck_every",
    "adaptive_throughput_threshold_mbps",
    "adaptive_warmup_count",
    "band",
    "block_height",
    "block_width",
    "crop_expand_pixels",
    "enable_low_resolution_offset_estimation",
    "enable_tile_validity_prefilter",
    "gpu_batch_size",
    "gpu_dynamic_batch",
    "gpu_max_batch_size",
    "gpu_min_batch_size",
    "invalid_pixel_radius",
    "invalid_values",
    "left_low_resolution_dom",
    "low_resolution_level",
    "low_resolution_matching_target_long_edge",
    "low_resolution_max_mean_projected_offset_meters",
    "low_resolution_max_mean_reprojection_error_pixels",
    "low_resolution_min_retained_match_count",
    "low_resolution_output_dir",
    "low_resolution_trim_fraction_each_side",
    "lower_percent",
    "matcher_method",
    "max_features",
    "max_image_dimension",
    "maximum_value",
    "min_overlap_size",
    "min_valid_pixels",
    "minimum_value",
    "num_worker_parallel_cpu",
    "overlap_x",
    "overlap_y",
    "ratio_test",
    "right_low_resolution_dom",
    "show_progress",
    "sift_contrast_threshold",
    "sift_edge_threshold",
    "sift_octave_layers",
    "sift_sigma",
    "special_pixel_abs_threshold",
    "tile_cache_max_mb",
    "tile_validity_cache_dir",
    "tile_validity_cell_height",
    "tile_validity_cell_width",
    "upper_percent",
    "use_gpu",
    "use_parallel_cpu",
    "use_tile_cache",
    "valid_pixel_percent_threshold",
}

DOM_WRAPPER_OPTIONS = {
    "match_visualization_output_dir",
    "match_visualization_output_path",
    "match_visualization_scale",
    "max_preview_pixels",
    "memory_profile",
    "preview_cache_dir",
    "preview_cache_source",
    "preview_crop_margin_pixels",
    "preview_force_regenerate",
    "preview_level",
    "show_progress",
    "visualization_mode",
    "visualization_target_long_edge",
    "write_match_visualization",
}


class PipelineConfigError(ValueError):
    """Raised when the DEM pipeline config cannot be interpreted."""


def _load_json_object(config_path: str | Path | None) -> dict[str, Any]:
    if config_path is None:
        return {}
    path = Path(config_path)
    if not path.exists():
        raise PipelineConfigError(f"Config JSON not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PipelineConfigError(f"Failed to parse config JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PipelineConfigError("DEM pipeline config JSON must decode to an object at the top level.")
    return payload


def _first_section(payload: Mapping[str, Any], *names: str) -> dict[str, Any]:
    for name in names:
        value = payload.get(name)
        if isinstance(value, dict):
            return dict(value)
    return {}


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _coerce_bool(value: Any) -> bool:
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
    raise PipelineConfigError(f"Expected a boolean-compatible value, got {value!r}.")


def _clean_options(options: Mapping[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in options.items():
        if value is None:
            continue
        if isinstance(value, str) and value == "":
            continue
        cleaned[MATCH_OPTION_ALIASES.get(key, key)] = value
    if "invalid_values" in cleaned and not isinstance(cleaned["invalid_values"], tuple):
        value = cleaned["invalid_values"]
        if isinstance(value, list):
            cleaned["invalid_values"] = tuple(float(item) for item in value)
        else:
            cleaned["invalid_values"] = (float(value),)
    return cleaned


def _load_common_image_match_defaults(config_path: str | Path | None) -> dict[str, Any]:
    if config_path is None:
        return {}
    try:
        return _clean_options(load_image_match_defaults_from_config(config_path))
    except ValueError as exc:
        raise PipelineConfigError(str(exc)) from exc


def image_match_options_for_route(
    config_path: str | Path | None,
    route: str,
    *,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve common ImageMatch defaults plus route-specific overrides."""

    config_payload = _load_json_object(config_path) if payload is None else dict(payload)
    options = _load_common_image_match_defaults(config_path)
    if route == "ori":
        options.update(_clean_options(_first_section(config_payload, "OriginalImageMatch", "original_image_match", "OriImageMatch", "ori_image_match")))
    elif route == "dom":
        options.update(_clean_options(_first_section(config_payload, "DomImageMatch", "DOMImageMatch", "dom_image_match", "DomMatch", "dom_match")))
    else:
        raise PipelineConfigError(f"Unsupported match route: {route}")
    return options


def dem_options_from_config(payload: Mapping[str, Any]) -> DemOptions:
    section = _first_section(payload, "DemExtract", "DEMExtract", "dem_extract", "Dem", "DEM")
    return DemOptions(
        aggregation=str(section.get("aggregation", "median")),
        value_type=str(section.get("value_type", section.get("valueType", "radius_m"))),
        datum_radius_m=_optional_float(section.get("datum_radius_m", section.get("datumRadiusM"))),
        nodata_value=float(section.get("nodata_value", section.get("nodataValue", -9999.0))),
        max_error_m=_optional_float(section.get("max_error_m", section.get("maxErrorM"))),
        min_sepang_deg=_optional_float(section.get("min_sepang_deg", section.get("minSepangDeg"))),
        min_radius_m=_optional_float(section.get("min_radius_m", section.get("minRadiusM"))),
        max_radius_m=_optional_float(section.get("max_radius_m", section.get("maxRadiusM"))),
    )


def dom_filter_options_from_config(payload: Mapping[str, Any]) -> DomFilterOptions:
    section = _first_section(payload, "DomToOriginal", "dom_to_original", "DomFiltering", "dom_filtering")
    return DomFilterOptions(
        merge_decimals=int(section.get("merge_decimals", section.get("mergeDecimals", 3))),
        skip_merge=_coerce_bool(section.get("skip_merge", section.get("skipMerge", False))),
        ransac_reproj_threshold=float(section.get("ransac_reproj_threshold", section.get("ransacReprojThreshold", 3.0))),
        ransac_confidence=float(section.get("ransac_confidence", section.get("ransacConfidence", 0.995))),
        ransac_max_iters=int(section.get("ransac_max_iters", section.get("ransacMaxIters", 5000))),
        ransac_mode=str(section.get("ransac_mode", section.get("ransacMode", "loose"))),
        loose_ransac_keep_threshold=float(section.get("loose_ransac_keep_threshold", section.get("looseRansacKeepThreshold", 1.0))),
    )


def key_refinement_config_from_config(payload: Mapping[str, Any]) -> KeyRefinementConfig:
    section = _first_section(payload, "KeyRefinement", "key_refinement", "TiePointRefinement", "tie_point_refinement")
    enabled = section.get("enabled", True)
    if not _coerce_bool(enabled):
        return KeyRefinementConfig()

    raw_stages = section.get("stages", section.get("pipeline", []))
    if raw_stages is None:
        return KeyRefinementConfig()
    if isinstance(raw_stages, str):
        raw_stages = [raw_stages]
    if not isinstance(raw_stages, list):
        raise PipelineConfigError("KeyRefinement.stages must be a string or array of strings.")
    return KeyRefinementConfig(stages=tuple(str(stage) for stage in raw_stages if str(stage).strip()))


def _output_path(value: str | None, default_path: Path) -> Path:
    return Path(value) if value else default_path


def build_pipeline_paths(args: argparse.Namespace) -> PipelinePaths:
    work_dir = Path(args.work_dir)
    reports_dir = work_dir / "reports"
    return PipelinePaths(
        work_dir=work_dir,
        output_dem_cube=_output_path(args.output_dem_cube, work_dir / "dem" / "stereo_dem.cub"),
        left_dom_key=work_dir / "keys_dom" / "left_dom.key",
        right_dom_key=work_dir / "keys_dom" / "right_dom.key",
        left_dom_merged_key=work_dir / "keys_dom" / "left_dom_merged.key",
        right_dom_merged_key=work_dir / "keys_dom" / "right_dom_merged.key",
        left_dom_ransac_key=work_dir / "keys_dom" / "left_dom_ransac.key",
        right_dom_ransac_key=work_dir / "keys_dom" / "right_dom_ransac.key",
        left_ori_key=work_dir / "keys_ori" / "left_ori.key",
        right_ori_key=work_dir / "keys_ori" / "right_ori.key",
        left_refined_key=work_dir / "keys_refined" / "left_refined.key",
        right_refined_key=work_dir / "keys_refined" / "right_refined.key",
        point_cloud_output=_output_path(args.point_cloud_output, work_dir / "point_cloud" / "stereo_points.jsonl"),
        dem_summary_output=_output_path(args.summary_output, reports_dir / "dem_summary.json"),
        quality_prefix=_output_path(args.quality_prefix, work_dir / "quality" / "stereo_dem"),
        pipeline_summary_output=_output_path(args.pipeline_summary_output, reports_dir / "pipeline_summary.json"),
        dom_match_metadata_output=reports_dir / "dom_match_metadata.json",
        dom_merge_summary_output=reports_dir / "dom_merge_summary.json",
        dom_ransac_summary_output=reports_dir / "dom_ransac_summary.json",
        dom2ori_summary_output=reports_dir / "dom2ori_summary.json",
        ori_match_summary_output=reports_dir / "ori_match_summary.json",
        key_refinement_summary_output=reports_dir / "key_refinement_summary.json",
        match_visualization_output_dir=work_dir / "match_viz",
    )


def ensure_pipeline_directories(paths: PipelinePaths) -> None:
    for path in (
        paths.output_dem_cube.parent,
        paths.left_dom_key.parent,
        paths.left_ori_key.parent,
        paths.left_refined_key.parent,
        paths.point_cloud_output.parent,
        paths.dem_summary_output.parent,
        paths.quality_prefix.parent,
        paths.pipeline_summary_output.parent,
        paths.match_visualization_output_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


def _split_dom_wrapper_options(options: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    core: dict[str, Any] = {}
    wrapper: dict[str, Any] = {}
    for key, value in options.items():
        if key in DOM_WRAPPER_OPTIONS:
            wrapper[key] = value
        elif key in CORE_MATCH_OPTIONS:
            core[key] = value
    return core, wrapper


def _core_match_options(options: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in options.items() if key in CORE_MATCH_OPTIONS}


def _run_dem_from_key(
    *,
    left_cube: str,
    right_cube: str,
    map_template_cube: str,
    paths: PipelinePaths,
    dem_options: DemOptions,
    refinement_config: KeyRefinementConfig,
) -> dict[str, Any]:
    dem_args = argparse.Namespace(
        command="from-key",
        left_cube=left_cube,
        right_cube=right_cube,
        left_key=str(paths.left_ori_key),
        right_key=str(paths.right_ori_key),
        map_template_cube=map_template_cube,
        output_dem_cube=str(paths.output_dem_cube),
        point_cloud_output=str(paths.point_cloud_output),
        summary_output=str(paths.dem_summary_output),
        quality_prefix=str(paths.quality_prefix),
        max_error_m=dem_options.max_error_m,
        min_sepang_deg=dem_options.min_sepang_deg,
        min_radius_m=dem_options.min_radius_m,
        max_radius_m=dem_options.max_radius_m,
        aggregation=dem_options.aggregation,
        value_type=dem_options.value_type,
        datum_radius_m=dem_options.datum_radius_m,
        refine_stage=list(refinement_config.stages),
        refined_left_key_output=str(paths.left_refined_key) if refinement_config.stages else None,
        refined_right_key_output=str(paths.right_refined_key) if refinement_config.stages else None,
        refinement_summary_output=str(paths.key_refinement_summary_output) if refinement_config.stages else None,
        nodata_value=dem_options.nodata_value,
        log_level="INFO",
    )
    return dict(isis_stereo_dem.run_from_key(dem_args))


def run_from_ori_match(
    args: argparse.Namespace,
    *,
    payload: Mapping[str, Any],
    paths: PipelinePaths,
    mode_name: str = "from-ori-match-dem",
) -> dict[str, Any]:
    match_options = _core_match_options(image_match_options_for_route(args.config, "ori", payload=payload))
    refinement_config = key_refinement_config_from_config(payload)
    match_result = match_ori_pair_to_key_files(
        args.left_cube,
        args.right_cube,
        paths.left_ori_key,
        paths.right_ori_key,
        **match_options,
    )
    write_summary_json(paths.ori_match_summary_output, match_result)
    dem_result = _run_dem_from_key(
        left_cube=args.left_cube,
        right_cube=args.right_cube,
        map_template_cube=args.map_template_cube,
        paths=paths,
        dem_options=dem_options_from_config(payload),
        refinement_config=refinement_config,
    )
    return {
        "mode": mode_name,
        "left_cube": args.left_cube,
        "right_cube": args.right_cube,
        "map_template_cube": args.map_template_cube,
        "keys": {
            "left_ori_key": str(paths.left_ori_key),
            "right_ori_key": str(paths.right_ori_key),
            "left_refined_key": str(paths.left_refined_key) if refinement_config.stages else None,
            "right_refined_key": str(paths.right_refined_key) if refinement_config.stages else None,
        },
        "match": match_result,
        "dem": dem_result,
    }


def run_from_dom_match(args: argparse.Namespace, *, payload: Mapping[str, Any], paths: PipelinePaths) -> dict[str, Any]:
    dom_match_options, dom_wrapper_options = _split_dom_wrapper_options(image_match_options_for_route(args.config, "dom", payload=payload))
    refinement_config = key_refinement_config_from_config(payload)
    dom_wrapper_options.setdefault("write_match_visualization", True)
    dom_wrapper_options.setdefault("match_visualization_output_dir", str(paths.match_visualization_output_dir))
    dom_match_result = match_dom_pair_to_key_files(
        args.left_dom,
        args.right_dom,
        paths.left_dom_key,
        paths.right_dom_key,
        metadata_output=paths.dom_match_metadata_output,
        **dom_wrapper_options,
        **dom_match_options,
    )
    dom_filter_options = dom_filter_options_from_config(payload)
    if dom_filter_options.skip_merge:
        merge_result: dict[str, Any] = {
            "applied": False,
            "left_input": str(paths.left_dom_key),
            "right_input": str(paths.right_dom_key),
            "left_output": str(paths.left_dom_key),
            "right_output": str(paths.right_dom_key),
            "decimals": dom_filter_options.merge_decimals,
        }
        left_dom_for_ransac = paths.left_dom_key
        right_dom_for_ransac = paths.right_dom_key
    else:
        merge_result = merge_stereo_pair_key_files(
            paths.left_dom_key,
            paths.right_dom_key,
            paths.left_dom_merged_key,
            paths.right_dom_merged_key,
            decimals=dom_filter_options.merge_decimals,
        )
        left_dom_for_ransac = paths.left_dom_merged_key
        right_dom_for_ransac = paths.right_dom_merged_key
    write_summary_json(paths.dom_merge_summary_output, merge_result)

    ransac_result = filter_stereo_pair_key_files_with_ransac(
        left_dom_for_ransac,
        right_dom_for_ransac,
        paths.left_dom_ransac_key,
        paths.right_dom_ransac_key,
        ransac_reproj_threshold=dom_filter_options.ransac_reproj_threshold,
        ransac_confidence=dom_filter_options.ransac_confidence,
        ransac_max_iters=dom_filter_options.ransac_max_iters,
        ransac_mode=dom_filter_options.ransac_mode,
        loose_keep_pixel_threshold=dom_filter_options.loose_ransac_keep_threshold,
    )
    write_summary_json(paths.dom_ransac_summary_output, ransac_result)

    dom2ori_result = convert_paired_dom_keypoints_to_original(
        paths.left_dom_ransac_key,
        paths.right_dom_ransac_key,
        args.left_dom,
        args.right_dom,
        args.left_cube,
        args.right_cube,
        paths.left_ori_key,
        paths.right_ori_key,
    )
    write_summary_json(paths.dom2ori_summary_output, dom2ori_result)

    dem_result = _run_dem_from_key(
        left_cube=args.left_cube,
        right_cube=args.right_cube,
        map_template_cube=args.map_template_cube,
        paths=paths,
        dem_options=dem_options_from_config(payload),
        refinement_config=refinement_config,
    )
    return {
        "mode": "from-dom-match",
        "left_dom": args.left_dom,
        "right_dom": args.right_dom,
        "left_cube": args.left_cube,
        "right_cube": args.right_cube,
        "map_template_cube": args.map_template_cube,
        "keys": {
            "left_dom_key": str(paths.left_dom_key),
            "right_dom_key": str(paths.right_dom_key),
            "left_ori_key": str(paths.left_ori_key),
            "right_ori_key": str(paths.right_ori_key),
            "left_refined_key": str(paths.left_refined_key) if refinement_config.stages else None,
            "right_refined_key": str(paths.right_refined_key) if refinement_config.stages else None,
        },
        "dom_match": dom_match_result,
        "merge": merge_result,
        "ransac": ransac_result,
        "dom2ori": dom2ori_result,
        "dem": dem_result,
    }


def run_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    payload = _load_json_object(args.config)
    paths = build_pipeline_paths(args)
    ensure_pipeline_directories(paths)
    if args.command == "from-ori-match-dem":
        result = run_from_ori_match(args, payload=payload, paths=paths, mode_name=args.command)
    elif args.command == "from-dom-match":
        result = run_from_dom_match(args, payload=payload, paths=paths)
    else:
        raise PipelineConfigError(f"Unsupported command: {args.command}")
    summary = {
        "status": "ok",
        "work_dir": str(paths.work_dir),
        "output_dem_cube": str(paths.output_dem_cube),
        "point_cloud_output": str(paths.point_cloud_output),
        "dem_summary_output": str(paths.dem_summary_output),
        **result,
    }
    write_summary_json(paths.pipeline_summary_output, summary)
    return summary


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR), help=f"Root working directory. Default: {DEFAULT_WORK_DIR}")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help=f"DEM pipeline config JSON. Default: {DEFAULT_CONFIG_PATH}")
    parser.add_argument("--output-dem-cube", default=None, help="Output DEM cube. Default: <work-dir>/dem/stereo_dem.cub")
    parser.add_argument("--point-cloud-output", default=None, help="Output point-cloud JSONL/CSV path. Default: <work-dir>/point_cloud/stereo_points.jsonl")
    parser.add_argument("--summary-output", default=None, help="DEM extraction summary JSON. Default: <work-dir>/reports/dem_summary.json")
    parser.add_argument("--quality-prefix", default=None, help="Prefix for DEM quality sidecars. Default: <work-dir>/quality/stereo_dem")
    parser.add_argument("--pipeline-summary-output", default=None, help="Pipeline summary JSON. Default: <work-dir>/reports/pipeline_summary.json")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a sparse stereo DEM extraction pipeline from image matching to DEM cube output.")
    _add_common_options(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    ori_dem_parser = subparsers.add_parser(
        "from-ori-match-dem",
        help="Match original-image cubes directly, then extract a sparse DEM.",
    )
    ori_dem_parser.add_argument("--left-cube", required=True, help="Left original ISIS cube.")
    ori_dem_parser.add_argument("--right-cube", required=True, help="Right original ISIS cube.")
    ori_dem_parser.add_argument("--map-template-cube", required=True, help="Projected cube whose Mapping/group and dimensions define the DEM grid.")

    dom_parser = subparsers.add_parser("from-dom-match", help="Match DOM cubes, convert tie points to original-image coordinates, then extract a sparse DEM.")
    dom_parser.add_argument("--left-dom", required=True, help="Left DOM/projected cube used for matching.")
    dom_parser.add_argument("--right-dom", required=True, help="Right DOM/projected cube used for matching.")
    dom_parser.add_argument("--left-cube", required=True, help="Left original ISIS cube used for triangulation.")
    dom_parser.add_argument("--right-cube", required=True, help="Right original ISIS cube used for triangulation.")
    dom_parser.add_argument("--map-template-cube", required=True, help="Projected cube whose Mapping/group and dimensions define the DEM grid.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        result = run_pipeline(args)
    except PipelineConfigError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
