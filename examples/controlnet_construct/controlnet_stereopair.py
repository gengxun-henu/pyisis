"""Build an ISIS ControlNet for a single stereo pair from original-image `.key` files.

Author: Geng Xun
Created: 2026-04-16
Updated: 2026-04-16  Geng Xun added an initial stereo-pair ControlNet builder that reads original-image tie points and writes PVL or binary `.net` files.
Updated: 2026-04-16  Geng Xun added a DOM-key CLI wrapper that chains dom2ori conversion into ControlNet creation.
Updated: 2026-04-16  Geng Xun inserted DOM-space tie-point merging into the from-dom pipeline so the wrapped CLI now covers merge plus dom2ori plus ControlNet creation.
Updated: 2026-04-17  Geng Xun added optional JSON sidecar report writing so per-pair results can be aggregated into regression-friendly batch summaries.
Updated: 2026-04-17  Geng Xun annotated per-pair JSON sidecars with explicit coordinate-basis metadata for nested DOM and original-image sample/line fields.
Updated: 2026-04-17  Geng Xun switched the DOM wrapper to pair-synchronized dom2ori conversion so left/right correspondences stay aligned.
Updated: 2026-04-18  Geng Xun added merge-stage RANSAC filtering and optional drawMatches visualization for DOM-space tie points before dom2ori.
Updated: 2026-04-18  Geng Xun aligned drawMatches preview defaults so the CLI now documents and uses one-third-size visualization output by default.
Updated: 2026-04-18  Geng Xun clarified that DOM duplicate merging uses a rounded stereo-pair coordinate hash and surfaces the hash precision in logs and result metadata.
Updated: 2026-04-19  Geng Xun change 'point = ip.ControlPoint(f"{config.point_id_prefix}{index:08d}")' from 6-digit to 8-digit zero padding for better future-proofing against large point counts.
Updated: 2026-04-20  Geng Xun added optional stereo-pair point-ID namespacing with CLI override support so multi-pair cnetmerge workflows avoid accidental PointId collisions.
Updated: 2026-04-20  Geng Xun added a from-dom batch wrapper that auto-assigns S1/S2/S3-style pair IDs across images_overlap.lis processing.
Updated: 2026-04-20  Geng Xun added an explicit post-RANSAC visualization output path so E2E runs can preserve deterministic pre/post drawMatches PNGs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.batch_summary import DEFAULT_BATCH_REPORT_NAME, write_batch_summary_report
    from controlnet_construct.controlnet_merge import pair_controlnet_filename
    from controlnet_construct.coordinate_metadata import CONTROLNET_RESULT_COORDINATE_FIELD_BASES, annotate_coordinate_payload
    from controlnet_construct.dom2ori import convert_paired_dom_keypoints_to_original
    from controlnet_construct.image_match import write_stereo_pair_match_visualization_from_key_files
    from controlnet_construct.keypoints import read_key_file
    from controlnet_construct.listing import StereoPair, read_path_list, read_stereo_pair_list, validate_paired_path_lists
    from controlnet_construct.runtime import bootstrap_runtime_environment
    from controlnet_construct.stereo_ransac import filter_stereo_pair_key_files_with_ransac
    from controlnet_construct.tie_point_merge_in_overlap import (
        MERGE_HASH_DESCRIPTION,
        MERGE_HASH_COORDINATE_FIELDS,
        MERGE_HASH_STRATEGY,
        merge_stereo_pair_key_files,
        validate_merge_decimals,
    )
else:
    from .batch_summary import DEFAULT_BATCH_REPORT_NAME, write_batch_summary_report
    from .controlnet_merge import pair_controlnet_filename
    from .coordinate_metadata import CONTROLNET_RESULT_COORDINATE_FIELD_BASES, annotate_coordinate_payload
    from .dom2ori import convert_paired_dom_keypoints_to_original
    from .image_match import write_stereo_pair_match_visualization_from_key_files
    from .keypoints import read_key_file
    from .listing import StereoPair, read_path_list, read_stereo_pair_list, validate_paired_path_lists
    from .runtime import bootstrap_runtime_environment
    from .stereo_ransac import filter_stereo_pair_key_files_with_ransac
    from .tie_point_merge_in_overlap import (
        MERGE_HASH_DESCRIPTION,
        MERGE_HASH_COORDINATE_FIELDS,
        MERGE_HASH_STRATEGY,
        merge_stereo_pair_key_files,
        validate_merge_decimals,
    )


bootstrap_runtime_environment()

import isis_pybind as ip


SUPPORTED_TARGET_NAMES = {
    "Moon",
    "Mars",
    "Earth",
    "Mercury",
    "Venus",
    "Ryugu",
    "Bennu",
    "Ceres",
    "Vesta",
    "Europa",
    "Ganymede",
    "Callisto",
    "Io",
    "Titan",
    "Enceladus",
}


DEFAULT_CONTROLNET_REPORT_SUFFIX = ".summary.json"


@dataclass(frozen=True, slots=True)
class ControlNetConfig:
    network_id: str
    target_name: str
    user_name: str
    description: str = ""
    point_id_prefix: str = "P"
    pair_id: str | None = None


def _default_intermediate_key_path(output_path: str | Path, side: str, stage: str) -> Path:
    output = Path(output_path)
    return output.with_name(f"{output.stem}_{side}_{stage}.key")


def default_controlnet_report_path(output_path: str | Path) -> Path:
    output = Path(output_path)
    if output.suffix:
        return output.with_suffix(DEFAULT_CONTROLNET_REPORT_SUFFIX)
    return output.with_name(f"{output.name}{DEFAULT_CONTROLNET_REPORT_SUFFIX}")


def write_controlnet_result_report(
    result: dict[str, object],
    output_path: str | Path,
    *,
    report_path: str | Path | None = None,
) -> str:
    resolved_report_path = Path(report_path) if report_path is not None else default_controlnet_report_path(output_path)
    annotated_result = annotate_coordinate_payload(
        result,
        context="controlnet_pair_result",
        field_bases=CONTROLNET_RESULT_COORDINATE_FIELD_BASES,
    )
    resolved_report_path.write_text(json.dumps(annotated_result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(resolved_report_path)


def _compose_unique_serial_number(cube_path: str | Path) -> str:
    serial_number = ip.SerialNumber.compose(str(cube_path))
    if serial_number and serial_number != "Unknown":
        return serial_number
    return f"Path::{Path(cube_path).resolve()}"


def _first_present(mapping: dict[str, object], *keys: str) -> object | None:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _normalize_optional_identifier(value: object | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _compose_point_id_namespace(config: ControlNetConfig) -> str:
    if config.pair_id is None:
        return config.point_id_prefix
    return f"{config.point_id_prefix}_{config.pair_id}_"


def _build_control_point_id(config: ControlNetConfig, index: int) -> str:
    return f"{_compose_point_id_namespace(config)}{index:08d}"


def _apply_cli_pair_id_override(config: ControlNetConfig, pair_id: object | None) -> ControlNetConfig:
    normalized_pair_id = _normalize_optional_identifier(pair_id)
    if normalized_pair_id == config.pair_id:
        return config
    return replace(config, pair_id=normalized_pair_id)


def _pair_tag(pair: StereoPair) -> str:
    return pair_controlnet_filename(pair, suffix="")


def _auto_batch_pair_id(index: int, *, prefix: str = "S", start: int = 1) -> str:
    if start < 1:
        raise ValueError("pair_id_start must be at least 1.")
    normalized_prefix = prefix.strip()
    if not normalized_prefix:
        raise ValueError("pair_id_prefix must be a non-empty string.")
    return f"{normalized_prefix}{start + index - 1}"


def _build_dom_lookup(original_list_path: str | Path, dom_list_path: str | Path) -> dict[str, str]:
    original_paths = read_path_list(original_list_path)
    dom_paths = read_path_list(dom_list_path)
    return {
        original_path: dom_path
        for original_path, dom_path in validate_paired_path_lists(original_paths, dom_paths)
    }


def build_controlnets_for_dom_overlap_list(
    overlap_list_path: str | Path,
    original_list_path: str | Path,
    dom_list_path: str | Path,
    dom_key_directory: str | Path,
    output_directory: str | Path,
    config: ControlNetConfig,
    *,
    report_directory: str | Path | None = None,
    pair_id_prefix: str = "S",
    pair_id_start: int = 1,
    left_dom_key_suffix: str = "_A.key",
    right_dom_key_suffix: str = "_B.key",
    pair_net_suffix: str = ".net",
    merge_decimals: int = 3,
    skip_merge: bool = False,
    ransac_reproj_threshold: float = 3.0,
    ransac_confidence: float = 0.995,
    ransac_max_iters: int = 5000,
    ransac_mode: str = "loose",
    loose_ransac_keep_threshold: float = 1.0,
    write_match_visualization: bool = False,
    match_visualization_scale: float = 1.0 / 3.0,
    match_visualization_output_dir: str | Path | None = None,
    dom_band: int = 1,
    left_original_band: int = 1,
    right_original_band: int = 1,
    pvl_format: bool = True,
    logger: logging.Logger | None = None,
) -> dict[str, object]:
    overlap_pairs = read_stereo_pair_list(overlap_list_path)
    if not overlap_pairs:
        raise ValueError("The overlap pair list is empty.")

    dom_lookup = _build_dom_lookup(original_list_path, dom_list_path)
    dom_key_dir = Path(dom_key_directory)
    net_output_dir = Path(output_directory)
    report_dir = Path(report_directory) if report_directory is not None else net_output_dir
    match_visualization_dir = (
        Path(match_visualization_output_dir) if match_visualization_output_dir is not None else None
    )
    net_output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    if match_visualization_dir is not None:
        match_visualization_dir.mkdir(parents=True, exist_ok=True)

    pair_results: list[dict[str, object]] = []
    pair_report_paths: list[str] = []
    batch_pairs: list[dict[str, object]] = []
    for index, pair in enumerate(overlap_pairs, start=1):
        if pair.left not in dom_lookup or pair.right not in dom_lookup:
            raise KeyError(
                f"Unable to resolve DOM paths for stereo pair {pair.as_csv_line()} from the provided original/dom lists."
            )

        pair_id = _auto_batch_pair_id(index, prefix=pair_id_prefix, start=pair_id_start)
        pair_tag = _pair_tag(pair)
        left_dom_key_path = dom_key_dir / f"{pair_tag}{left_dom_key_suffix}"
        right_dom_key_path = dom_key_dir / f"{pair_tag}{right_dom_key_suffix}"
        if not left_dom_key_path.exists() or not right_dom_key_path.exists():
            raise FileNotFoundError(
                "Expected DOM-space key files are missing for stereo pair "
                f"{pair.as_csv_line()}: left={left_dom_key_path} right={right_dom_key_path}"
            )

        pair_output_net = net_output_dir / pair_controlnet_filename(pair, suffix=pair_net_suffix)
        pair_report_path = report_dir / default_controlnet_report_path(pair_output_net).name
        pair_config = replace(config, pair_id=pair_id)
        if logger is not None and config.pair_id is not None:
            logger.info(
                "controlnet_stereopair batch auto pair-id override: config_pair_id=%s generated_pair_id=%s pair=%s",
                config.pair_id,
                pair_id,
                pair.as_csv_line(),
            )

        pair_result = build_controlnet_for_dom_stereo_pair(
            left_dom_key_path,
            right_dom_key_path,
            dom_lookup[pair.left],
            dom_lookup[pair.right],
            pair.left,
            pair.right,
            pair_config,
            pair_output_net,
            merge_decimals=merge_decimals,
            skip_merge=skip_merge,
            ransac_reproj_threshold=ransac_reproj_threshold,
            ransac_confidence=ransac_confidence,
            ransac_max_iters=ransac_max_iters,
            ransac_mode=ransac_mode,
            loose_ransac_keep_threshold=loose_ransac_keep_threshold,
            write_match_visualization=write_match_visualization,
            match_visualization_scale=match_visualization_scale,
            match_visualization_output_dir=match_visualization_dir,
            dom_band=dom_band,
            left_original_band=left_original_band,
            right_original_band=right_original_band,
            pvl_format=pvl_format,
            logger=logger,
        )
        pair_result = {
            "pair": pair.as_csv_line(),
            "pair_id": pair_id,
            **pair_result,
        }
        report_path = write_controlnet_result_report(pair_result, pair_output_net, report_path=pair_report_path)
        pair_result = {
            **pair_result,
            "report_path": report_path,
        }
        pair_results.append(pair_result)
        pair_report_paths.append(report_path)
        batch_pairs.append(
            {
                "pair": pair.as_csv_line(),
                "pair_id": pair_id,
                "output_net": str(pair_output_net),
                "report_path": report_path,
                "control_point_count": pair_result["controlnet"]["point_count"],
            }
        )

    batch_report_path = report_dir / DEFAULT_BATCH_REPORT_NAME
    batch_summary = write_batch_summary_report(
        pair_results,
        batch_report_path,
        source_reports=pair_report_paths,
    )
    return {
        "mode": "from-dom-batch",
        "overlap_list_path": str(overlap_list_path),
        "pair_count": len(overlap_pairs),
        "pair_id_prefix": pair_id_prefix,
        "pair_id_start": pair_id_start,
        "output_directory": str(net_output_dir),
        "report_directory": str(report_dir),
        "batch_report_path": str(batch_report_path),
        "pairs": batch_pairs,
        "batch_summary": batch_summary,
    }


def read_controlnet_config(config_path: str | Path) -> ControlNetConfig:
    payload = json.loads(Path(config_path).read_text(encoding="utf-8"))
    network_id = _first_present(payload, "NetworkId", "network_id")
    target_name = _first_present(payload, "TargetName", "target_name")
    user_name = _first_present(payload, "UserName", "user_name")
    description = _first_present(payload, "Description", "description") or ""
    point_id_prefix = _first_present(payload, "PointIdPrefix", "point_id_prefix") or "P"
    pair_id = _normalize_optional_identifier(
        _first_present(payload, "PairId", "pair_id", "StereoPairId", "stereo_pair_id")
    )

    if not network_id or not target_name or not user_name:
        raise ValueError("The controlnet config must define NetworkId, TargetName, and UserName.")

    if str(target_name) not in SUPPORTED_TARGET_NAMES:
        raise ValueError(
            f"Unsupported TargetName {target_name!r}. Supported values include: {sorted(SUPPORTED_TARGET_NAMES)}"
        )

    return ControlNetConfig(
        network_id=str(network_id),
        target_name=str(target_name),
        user_name=str(user_name),
        description=str(description),
        point_id_prefix=str(point_id_prefix),
        pair_id=pair_id,
    )


def build_controlnet_for_stereo_pair(
    left_key_path: str | Path,
    right_key_path: str | Path,
    left_cube_path: str | Path,
    right_cube_path: str | Path,
    config: ControlNetConfig,
    output_path: str | Path,
    *,
    pvl_format: bool = True,
) -> dict[str, object]:
    left_key_file = read_key_file(left_key_path)
    right_key_file = read_key_file(right_key_path)
    if len(left_key_file.points) != len(right_key_file.points):
        raise ValueError("The left and right original-image key files must contain the same number of points.")

    left_serial_number = _compose_unique_serial_number(left_cube_path)
    right_serial_number = _compose_unique_serial_number(right_cube_path)

    net = ip.ControlNet()
    net.set_network_id(config.network_id)
    net.set_target(config.target_name)
    net.set_user_name(config.user_name)
    net.set_description(config.description)

    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    net.set_created_date(timestamp)
    net.set_modified_date(timestamp)

    point_id_namespace = _compose_point_id_namespace(config)
    first_point_id = _build_control_point_id(config, 1) if left_key_file.points else None

    for index, (left_point, right_point) in enumerate(
        zip(left_key_file.points, right_key_file.points, strict=True),
        start=1,
    ):
        point = ip.ControlPoint(_build_control_point_id(config, index))
        point.set_type(ip.ControlPoint.PointType.Free)

        left_measure = ip.ControlMeasure()
        left_measure.set_cube_serial_number(left_serial_number)
        left_measure.set_coordinate(left_point.sample, left_point.line)
        left_measure.set_type(ip.ControlMeasure.MeasureType.Manual)
        point.add_measure(left_measure)

        right_measure = ip.ControlMeasure()
        right_measure.set_cube_serial_number(right_serial_number)
        right_measure.set_coordinate(right_point.sample, right_point.line)
        right_measure.set_type(ip.ControlMeasure.MeasureType.Manual)
        point.add_measure(right_measure)

        point.set_ref_measure(0)
        net.add_point(point)

    net.write(str(output_path), pvl_format)
    return {
        "output_path": str(output_path),
        "network_id": config.network_id,
        "target_name": config.target_name,
        "user_name": config.user_name,
        "point_id_prefix": config.point_id_prefix,
        "pair_id": config.pair_id,
        "point_id_namespace": point_id_namespace,
        "point_id_example": first_point_id,
        "point_count": net.get_num_points(),
        "measure_count": net.get_num_measures(),
        "left_serial_number": left_serial_number,
        "right_serial_number": right_serial_number,
        "pvl_format": pvl_format,
    }


def build_controlnet_for_dom_stereo_pair(
    left_dom_key_path: str | Path,
    right_dom_key_path: str | Path,
    left_dom_cube_path: str | Path,
    right_dom_cube_path: str | Path,
    left_cube_path: str | Path,
    right_cube_path: str | Path,
    config: ControlNetConfig,
    output_path: str | Path,
    *,
    left_merged_dom_key_path: str | Path | None = None,
    right_merged_dom_key_path: str | Path | None = None,
    left_ransac_dom_key_path: str | Path | None = None,
    right_ransac_dom_key_path: str | Path | None = None,
    left_output_key_path: str | Path | None = None,
    right_output_key_path: str | Path | None = None,
    merge_decimals: int = 3,
    skip_merge: bool = False,
    ransac_reproj_threshold: float = 3.0,
    ransac_confidence: float = 0.995,
    ransac_max_iters: int = 5000,
    ransac_mode: str = "loose",
    loose_ransac_keep_threshold: float = 1.0,
    write_match_visualization: bool = False,
    match_visualization_output_path: str | Path | None = None,
    match_visualization_scale: float = 1.0 / 3.0,
    match_visualization_output_dir: str | Path | None = None,
    dom_band: int = 1,
    left_original_band: int = 1,
    right_original_band: int = 1,
    left_failure_log_path: str | Path | None = None,
    right_failure_log_path: str | Path | None = None,
    pvl_format: bool = True,
    logger: logging.Logger | None = None,
) -> dict[str, object]:
    validated_merge_decimals = validate_merge_decimals(merge_decimals)
    left_output_key = Path(left_output_key_path) if left_output_key_path is not None else _default_intermediate_key_path(output_path, "left", "ori")
    right_output_key = Path(right_output_key_path) if right_output_key_path is not None else _default_intermediate_key_path(output_path, "right", "ori")
    left_merged_dom_key = Path(left_merged_dom_key_path) if left_merged_dom_key_path is not None else _default_intermediate_key_path(output_path, "left", "dom_merged")
    right_merged_dom_key = Path(right_merged_dom_key_path) if right_merged_dom_key_path is not None else _default_intermediate_key_path(output_path, "right", "dom_merged")
    left_ransac_dom_key = Path(left_ransac_dom_key_path) if left_ransac_dom_key_path is not None else _default_intermediate_key_path(output_path, "left", "dom_ransac")
    right_ransac_dom_key = Path(right_ransac_dom_key_path) if right_ransac_dom_key_path is not None else _default_intermediate_key_path(output_path, "right", "dom_ransac")

    if logger is not None:
        logger.info(
            "controlnet_stereopair chaining from DOM keys into original-image keys: %s, %s",
            left_dom_key_path,
            right_dom_key_path,
        )

    if skip_merge:
        merge_result: dict[str, object] = {
            "applied": False,
            "left_input": str(left_dom_key_path),
            "right_input": str(right_dom_key_path),
            "left_output": str(left_dom_key_path),
            "right_output": str(right_dom_key_path),
            "decimals": validated_merge_decimals,
            "hash_rounding_decimals": validated_merge_decimals,
            "hash_strategy": MERGE_HASH_STRATEGY,
            "hash_coordinate_fields": MERGE_HASH_COORDINATE_FIELDS,
            "hash_description": MERGE_HASH_DESCRIPTION,
        }
        left_dom_key_for_conversion = Path(left_dom_key_path)
        right_dom_key_for_conversion = Path(right_dom_key_path)
        if logger is not None:
            logger.info(
                "controlnet_stereopair skipped DOM duplicate merge: hash_strategy=%s hash_coordinate_fields=%s hash_rounding_decimals=%s",
                MERGE_HASH_STRATEGY,
                MERGE_HASH_COORDINATE_FIELDS,
                validated_merge_decimals,
            )
    else:
        merge_stats = merge_stereo_pair_key_files(
            str(left_dom_key_path),
            str(right_dom_key_path),
            str(left_merged_dom_key),
            str(right_merged_dom_key),
            decimals=validated_merge_decimals,
        )
        merge_result = {
            "applied": True,
            **merge_stats,
        }
        left_dom_key_for_conversion = left_merged_dom_key
        right_dom_key_for_conversion = right_merged_dom_key
        if logger is not None:
            logger.info(
                "controlnet_stereopair merged DOM tie points: hash_strategy=%s hash_coordinate_fields=%s hash_rounding_decimals=%s input_count=%s unique_count=%s duplicate_count=%s",
                merge_stats["hash_strategy"],
                merge_stats["hash_coordinate_fields"],
                merge_stats["hash_rounding_decimals"],
                merge_stats["input_count"],
                merge_stats["unique_count"],
                merge_stats["duplicate_count"],
            )

    ransac_result = filter_stereo_pair_key_files_with_ransac(
        str(left_dom_key_for_conversion),
        str(right_dom_key_for_conversion),
        str(left_ransac_dom_key),
        str(right_ransac_dom_key),
        ransac_reproj_threshold=ransac_reproj_threshold,
        ransac_confidence=ransac_confidence,
        ransac_max_iters=ransac_max_iters,
        ransac_mode=ransac_mode,
        loose_keep_pixel_threshold=loose_ransac_keep_threshold,
    )
    left_dom_key_for_conversion = left_ransac_dom_key
    right_dom_key_for_conversion = right_ransac_dom_key
    if logger is not None:
        logger.info(
            "controlnet_stereopair applied RANSAC filtering: status=%s retained_count=%s dropped_count=%s mode=%s",
            ransac_result["status"],
            ransac_result["retained_count"],
            ransac_result["dropped_count"],
            ransac_result["mode"],
        )

    match_visualization_result: dict[str, object] | None = None
    if write_match_visualization:
        visualization_directory = Path(match_visualization_output_dir) if match_visualization_output_dir is not None else Path(output_path).parent
        match_visualization_result = write_stereo_pair_match_visualization_from_key_files(
            left_dom_cube_path,
            right_dom_cube_path,
            left_dom_key_for_conversion,
            right_dom_key_for_conversion,
            output_path=match_visualization_output_path,
            output_directory=visualization_directory,
            scale_factor=match_visualization_scale,
            band=dom_band,
            highlight_match_indices=ransac_result["retained_soft_outlier_positions"],
        )

    paired_conversion = convert_paired_dom_keypoints_to_original(
        left_dom_key_for_conversion,
        right_dom_key_for_conversion,
        left_dom_cube_path,
        right_dom_cube_path,
        left_cube_path,
        right_cube_path,
        left_output_key,
        right_output_key,
        dom_band=dom_band,
        left_original_band=left_original_band,
        right_original_band=right_original_band,
        left_failure_log_path=left_failure_log_path,
        right_failure_log_path=right_failure_log_path,
        logger=logger,
    )
    left_conversion = paired_conversion["left_conversion"]
    right_conversion = paired_conversion["right_conversion"]

    controlnet_result = build_controlnet_for_stereo_pair(
        left_output_key,
        right_output_key,
        left_cube_path,
        right_cube_path,
        config,
        output_path,
        pvl_format=pvl_format,
    )
    return {
        "mode": "from-dom",
        "merge": merge_result,
        "ransac": ransac_result,
        "left_conversion": left_conversion,
        "right_conversion": right_conversion,
        "controlnet": controlnet_result,
        **({"match_visualization": match_visualization_result} if match_visualization_result is not None else {}),
    }


def _build_from_original_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "from-ori",
        help="Build a ControlNet directly from original-image `.key` files.",
    )
    parser.add_argument("left_key", help="Original-image .key file for cube A.")
    parser.add_argument("right_key", help="Original-image .key file for cube B.")
    parser.add_argument("left_cube", help="Original cube path for image A.")
    parser.add_argument("right_cube", help="Original cube path for image B.")
    parser.add_argument("config", help="JSON config file containing NetworkId, TargetName, and UserName.")
    parser.add_argument("output_net", help="Output ControlNet path.")
    parser.add_argument("--report-path", default=None, help="Optional JSON path used to persist the per-pair result summary.")
    parser.add_argument(
        "--pair-id",
        default=None,
        help="Optional stereo-pair ID appended to the point-id namespace so different pairwise ControlNets avoid PointId collisions during later cnetmerge steps.",
    )
    parser.add_argument("--binary", action="store_true", help="Write the ControlNet in binary format instead of PVL.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity for runtime diagnostics.",
    )


def _build_from_dom_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "from-dom",
        help="Convert DOM-space `.key` files to original-image coordinates and then build a ControlNet.",
    )
    parser.add_argument("left_dom_key", help="DOM-space .key file for image A.")
    parser.add_argument("right_dom_key", help="DOM-space .key file for image B.")
    parser.add_argument("left_dom_cube", help="DOM cube path for image A.")
    parser.add_argument("right_dom_cube", help="DOM cube path for image B.")
    parser.add_argument("left_cube", help="Original cube path for image A.")
    parser.add_argument("right_cube", help="Original cube path for image B.")
    parser.add_argument("config", help="JSON config file containing NetworkId, TargetName, and UserName.")
    parser.add_argument("output_net", help="Output ControlNet path.")
    parser.add_argument("--report-path", default=None, help="Optional JSON path used to persist the per-pair result summary.")
    parser.add_argument(
        "--pair-id",
        default=None,
        help="Optional stereo-pair ID appended to the point-id namespace so different pairwise ControlNets avoid PointId collisions during later cnetmerge steps.",
    )
    parser.add_argument("--left-merged-dom-key", default=None, help="Optional path to persist the merged DOM-space .key for image A before dom2ori.")
    parser.add_argument("--right-merged-dom-key", default=None, help="Optional path to persist the merged DOM-space .key for image B before dom2ori.")
    parser.add_argument("--left-ransac-dom-key", default=None, help="Optional path to persist the RANSAC-filtered DOM-space .key for image A before dom2ori.")
    parser.add_argument("--right-ransac-dom-key", default=None, help="Optional path to persist the RANSAC-filtered DOM-space .key for image B before dom2ori.")
    parser.add_argument("--left-output-key", default=None, help="Optional path to persist the converted original-image .key for image A.")
    parser.add_argument("--right-output-key", default=None, help="Optional path to persist the converted original-image .key for image B.")
    parser.add_argument(
        "--merge-decimals",
        type=validate_merge_decimals,
        default=3,
        help=(
            "Decimal precision used by the rounded left/right sample-line coordinate hash when"
            " merging duplicate DOM tie points. Valid range: 0-6."
        ),
    )
    parser.add_argument("--skip-merge", action="store_true", help="Skip DOM-space duplicate merge and pass the input DOM .key files straight to dom2ori.")
    parser.add_argument("--ransac-reproj-threshold", type=float, default=3.0, help="Reprojection threshold passed to OpenCV homography RANSAC on merged DOM tie points.")
    parser.add_argument("--ransac-confidence", type=float, default=0.995, help="Confidence passed to OpenCV homography RANSAC on merged DOM tie points.")
    parser.add_argument("--ransac-max-iters", type=int, default=5000, help="Maximum iteration count passed to OpenCV homography RANSAC on merged DOM tie points.")
    parser.add_argument("--ransac-mode", choices=("strict", "loose"), default="loose", help="Strict mode drops every OpenCV RANSAC outlier; loose mode re-checks outliers against the fitted homography and keeps those within the loose threshold.")
    parser.add_argument("--loose-ransac-keep-threshold", type=float, default=1.0, help="Loose-mode pixel threshold used to keep OpenCV RANSAC outliers whose homography reprojection error stays within this limit.")
    parser.add_argument("--write-match-visualization", action="store_true", help="Write a post-RANSAC drawMatches PNG after merge-stage RANSAC filtering using the default A__B__timestamp naming rule. The default preview uses one-fourth of the original image width and height.")
    parser.add_argument("--match-visualization-output-path", default=None, help="Optional explicit output path for the post-RANSAC drawMatches PNG written by the from-dom wrapper.")
    parser.add_argument("--match-visualization-scale", type=float, default=0.25, help="Image scale factor used when writing the post-RANSAC drawMatches visualization PNG. Defaults to 1/4, producing a one-fourth-size preview in each dimension.")
    parser.add_argument("--match-visualization-output-dir", default=None, help="Optional directory used for the auto-named post-RANSAC drawMatches PNG.")
    parser.add_argument("--dom-band", type=int, default=1, help="Band index used when reading the DOM cubes.")
    parser.add_argument("--left-original-band", type=int, default=1, help="Band index used when projecting into the left original cube.")
    parser.add_argument("--right-original-band", type=int, default=1, help="Band index used when projecting into the right original cube.")
    parser.add_argument("--left-failure-log", default=None, help="Optional JSON failure-log path for the left dom2ori conversion.")
    parser.add_argument("--right-failure-log", default=None, help="Optional JSON failure-log path for the right dom2ori conversion.")
    parser.add_argument("--binary", action="store_true", help="Write the ControlNet in binary format instead of PVL.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity for runtime diagnostics.",
    )


def _build_from_dom_batch_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "from-dom-batch",
        help="Build pairwise ControlNets for every stereo pair in images_overlap.lis and auto-assign S1/S2/S3-style pair IDs.",
    )
    parser.add_argument("overlap_list", help="Path to images_overlap.lis.")
    parser.add_argument("original_list", help="Path to original_images.lis.")
    parser.add_argument("dom_list", help="Path to doms.lis or doms_scaled.lis aligned with the original list.")
    parser.add_argument("dom_key_directory", help="Directory containing per-pair DOM-space key files named like A__B_A.key and A__B_B.key.")
    parser.add_argument("config", help="JSON config file containing NetworkId, TargetName, and UserName.")
    parser.add_argument("output_directory", help="Directory used to write pairwise .net files and default intermediate outputs.")
    parser.add_argument("--report-dir", default=None, help="Optional directory used to write per-pair JSON sidecars and the batch summary JSON. Defaults to <output_directory>.")
    parser.add_argument("--pair-id-prefix", default="S", help="Prefix used when auto-assigning batch pair IDs. Defaults to S, producing S1, S2, S3, ...")
    parser.add_argument("--pair-id-start", type=int, default=1, help="Starting integer used when auto-assigning batch pair IDs. Defaults to 1.")
    parser.add_argument("--left-dom-key-suffix", default="_A.key", help="Filename suffix for the left DOM key file inside --dom-key-directory.")
    parser.add_argument("--right-dom-key-suffix", default="_B.key", help="Filename suffix for the right DOM key file inside --dom-key-directory.")
    parser.add_argument("--pair-net-suffix", default=".net", help="Filename suffix used for output pairwise ControlNet files.")
    parser.add_argument(
        "--merge-decimals",
        type=validate_merge_decimals,
        default=3,
        help=(
            "Decimal precision used by the rounded left/right sample-line coordinate hash when"
            " merging duplicate DOM tie points. Valid range: 0-6."
        ),
    )
    parser.add_argument("--skip-merge", action="store_true", help="Skip DOM-space duplicate merge and pass the input DOM .key files straight to dom2ori.")
    parser.add_argument("--ransac-reproj-threshold", type=float, default=3.0, help="Reprojection threshold passed to OpenCV homography RANSAC on merged DOM tie points.")
    parser.add_argument("--ransac-confidence", type=float, default=0.995, help="Confidence passed to OpenCV homography RANSAC on merged DOM tie points.")
    parser.add_argument("--ransac-max-iters", type=int, default=5000, help="Maximum iteration count passed to OpenCV homography RANSAC on merged DOM tie points.")
    parser.add_argument("--ransac-mode", choices=("strict", "loose"), default="loose", help="Strict mode drops every OpenCV RANSAC outlier; loose mode re-checks outliers against the fitted homography and keeps those within the loose threshold.")
    parser.add_argument("--loose-ransac-keep-threshold", type=float, default=1.0, help="Loose-mode pixel threshold used to keep OpenCV RANSAC outliers whose homography reprojection error stays within this limit.")
    parser.add_argument("--write-match-visualization", action="store_true", help="Write a post-RANSAC drawMatches PNG after merge-stage RANSAC filtering for each pair in the batch.")
    parser.add_argument("--match-visualization-scale", type=float, default=0.25, help="Image scale factor used when writing batch post-RANSAC drawMatches visualization PNG files. Defaults to 1/4.")
    parser.add_argument("--match-visualization-output-dir", default=None, help="Optional directory used for batch post-RANSAC drawMatches visualization PNG files.")
    parser.add_argument("--dom-band", type=int, default=1, help="Band index used when reading the DOM cubes.")
    parser.add_argument("--left-original-band", type=int, default=1, help="Band index used when projecting into the left original cube.")
    parser.add_argument("--right-original-band", type=int, default=1, help="Band index used when projecting into the right original cube.")
    parser.add_argument("--binary", action="store_true", help="Write the ControlNet in binary format instead of PVL.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity for runtime diagnostics.",
    )


def _normalize_cli_argv(argv: list[str]) -> list[str]:
    if argv and argv[0] not in {"from-ori", "from-dom", "from-dom-batch", "-h", "--help"}:
        return ["from-ori", *argv]
    return argv


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a single stereo-pair ISIS ControlNet from original-image or DOM-space `.key` files.")
    subparsers = parser.add_subparsers(dest="command")
    _build_from_original_parser(subparsers)
    _build_from_dom_parser(subparsers)
    _build_from_dom_batch_parser(subparsers)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_argument_parser()
    normalized_argv = _normalize_cli_argv(sys.argv[1:] if argv is None else list(argv))
    if not normalized_argv:
        parser.print_help()
        return
    args = parser.parse_args(normalized_argv)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(message)s")
    logger = logging.getLogger("controlnet_construct.controlnet_stereopair")

    if args.command == "from-dom":
        config = _apply_cli_pair_id_override(read_controlnet_config(args.config), args.pair_id)
        result = build_controlnet_for_dom_stereo_pair(
            args.left_dom_key,
            args.right_dom_key,
            args.left_dom_cube,
            args.right_dom_cube,
            args.left_cube,
            args.right_cube,
            config,
            args.output_net,
            left_merged_dom_key_path=args.left_merged_dom_key,
            right_merged_dom_key_path=args.right_merged_dom_key,
            left_ransac_dom_key_path=args.left_ransac_dom_key,
            right_ransac_dom_key_path=args.right_ransac_dom_key,
            left_output_key_path=args.left_output_key,
            right_output_key_path=args.right_output_key,
            merge_decimals=args.merge_decimals,
            skip_merge=args.skip_merge,
            ransac_reproj_threshold=args.ransac_reproj_threshold,
            ransac_confidence=args.ransac_confidence,
            ransac_max_iters=args.ransac_max_iters,
            ransac_mode=args.ransac_mode,
            loose_ransac_keep_threshold=args.loose_ransac_keep_threshold,
            write_match_visualization=args.write_match_visualization,
            match_visualization_output_path=args.match_visualization_output_path,
            match_visualization_scale=args.match_visualization_scale,
            match_visualization_output_dir=args.match_visualization_output_dir,
            dom_band=args.dom_band,
            left_original_band=args.left_original_band,
            right_original_band=args.right_original_band,
            left_failure_log_path=args.left_failure_log,
            right_failure_log_path=args.right_failure_log,
            pvl_format=not args.binary,
            logger=logger,
        )
    elif args.command == "from-dom-batch":
        config = read_controlnet_config(args.config)
        result = build_controlnets_for_dom_overlap_list(
            args.overlap_list,
            args.original_list,
            args.dom_list,
            args.dom_key_directory,
            args.output_directory,
            config,
            report_directory=args.report_dir,
            pair_id_prefix=args.pair_id_prefix,
            pair_id_start=args.pair_id_start,
            left_dom_key_suffix=args.left_dom_key_suffix,
            right_dom_key_suffix=args.right_dom_key_suffix,
            pair_net_suffix=args.pair_net_suffix,
            merge_decimals=args.merge_decimals,
            skip_merge=args.skip_merge,
            ransac_reproj_threshold=args.ransac_reproj_threshold,
            ransac_confidence=args.ransac_confidence,
            ransac_max_iters=args.ransac_max_iters,
            ransac_mode=args.ransac_mode,
            loose_ransac_keep_threshold=args.loose_ransac_keep_threshold,
            write_match_visualization=args.write_match_visualization,
            match_visualization_scale=args.match_visualization_scale,
            match_visualization_output_dir=args.match_visualization_output_dir,
            dom_band=args.dom_band,
            left_original_band=args.left_original_band,
            right_original_band=args.right_original_band,
            pvl_format=not args.binary,
            logger=logger,
        )
    else:
        config = _apply_cli_pair_id_override(read_controlnet_config(args.config), args.pair_id)
        result = build_controlnet_for_stereo_pair(
            args.left_key,
            args.right_key,
            args.left_cube,
            args.right_cube,
            config,
            args.output_net,
            pvl_format=not args.binary,
        )

    if getattr(args, "report_path", None):
        report_path = write_controlnet_result_report(result, args.output_net, report_path=args.report_path)
        result = {
            **result,
            "report_path": report_path,
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()