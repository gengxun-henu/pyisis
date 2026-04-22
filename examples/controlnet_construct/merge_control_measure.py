"""Merge duplicate ControlNet points by per-image rounded measure coordinates.

Author: Geng Xun
Created: 2026-04-21
Updated: 2026-04-21  Geng Xun added a post-cnetmerge ControlNet deduplication CLI that collapses duplicate points by rounded per-image measure hashes while preserving the first point's point-level metadata.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Mapping


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.listing import read_path_list
    from controlnet_construct.runtime import _has_leap_second_kernels, bootstrap_runtime_environment
    from controlnet_construct.tie_point_merge_in_overlap import validate_merge_decimals
else:
    from .listing import read_path_list
    from .runtime import _has_leap_second_kernels, bootstrap_runtime_environment
    from .tie_point_merge_in_overlap import validate_merge_decimals


bootstrap_runtime_environment()

import isis_pybind as ip


MERGE_HASH_STRATEGY = "rounded_per_image_measure_coordinate_hash"
MERGE_HASH_COORDINATE_FIELDS = "cube_serial_number,sample,line"
MERGE_HASH_DESCRIPTION = (
    "Round each ControlMeasure sample/line coordinate to a fixed decimal precision within each cube"
    " serial-number track, then merge later ControlPoints into the first matching ControlPoint."
)
DEFAULT_HASH_DECIMALS = 1


@dataclass(frozen=True, slots=True)
class ControlMeasureMergeSummary:
    input_control_net: str
    output_control_net: str
    original_image_list: str
    point_count_before: int
    point_count_after: int
    measure_count_before: int
    measure_count_after: int
    duplicate_point_count: int
    merged_point_count: int
    matched_measure_count: int
    merged_measure_candidate_count: int
    added_measure_count: int
    skipped_existing_serial_count: int
    decimals: int
    hash_rounding_decimals: int
    hash_strategy: str
    hash_coordinate_fields: str
    hash_description: str
    known_image_count: int
    pvl_format: bool
    merged_point_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _InPlaceMergeState:
    point_count_before: int
    measure_count_before: int
    duplicate_point_count: int = 0
    merged_point_count: int = 0
    matched_measure_count: int = 0
    merged_measure_candidate_count: int = 0
    added_measure_count: int = 0
    skipped_existing_serial_count: int = 0
    merged_point_ids: tuple[str, ...] = ()


def _parse_merge_decimals(value: str) -> int:
    return validate_merge_decimals(int(value))


def _default_output_path(input_control_net_path: str | Path) -> Path:
    path = Path(input_control_net_path)
    return path.with_name(f"{path.stem}_merged_measures{path.suffix}")


def _measure_hash(sample: float, line: float, decimals: int) -> tuple[float, float]:
    return (round(float(sample), decimals), round(float(line), decimals))


def _measure_hash_from_measure(measure: ip.ControlMeasure, decimals: int) -> tuple[float, float]:
    return _measure_hash(measure.get_sample(), measure.get_line(), decimals)


def _snapshot_point_ids(net: ip.ControlNet) -> tuple[str, ...]:
    return tuple(net.get_point(index).get_id() for index in range(net.get_num_points()))


def _require_isisdata() -> str:
    isisdata_root = os.environ.get("ISISDATA", "").strip()
    if not isisdata_root:
        raise RuntimeError(
            "ISISDATA is not configured. Please set ISISDATA to a valid ISIS data root before running"
            " merge_control_measure.py."
        )

    if not _has_leap_second_kernels(Path(isisdata_root)):
        raise RuntimeError(
            f"ISISDATA does not appear usable for SerialNumber.compose(): {isisdata_root}."
        )
    return isisdata_root


def resolve_original_image_serials(original_image_list_path: str | Path) -> dict[str, str]:
    _require_isisdata()
    image_paths = read_path_list(original_image_list_path)
    if not image_paths:
        raise ValueError("The original image list is empty.")

    serial_to_path: dict[str, str] = {}
    for image_path in image_paths:
        serial_number = ip.SerialNumber.compose(str(image_path))
        if not serial_number or serial_number == "Unknown":
            raise ValueError(
                "Failed to compose a valid cube serial number from "
                f"{image_path!r}. Make sure the cube is readable and has already been spiceinit'ed."
            )
        previous = serial_to_path.get(serial_number)
        if previous is not None and previous != image_path:
            raise ValueError(
                "The original image list contains duplicate serial numbers for different cubes: "
                f"{serial_number!r} from {previous!r} and {image_path!r}."
            )
        serial_to_path[serial_number] = image_path

    return serial_to_path


def _select_first_point_id(candidate_point_ids: set[str], point_order: Mapping[str, int]) -> str:
    return min(candidate_point_ids, key=lambda point_id: point_order.get(point_id, sys.maxsize))


def _update_registry_for_point(
    point: ip.ControlPoint,
    *,
    target_point_id: str,
    registry: dict[str, dict[tuple[float, float], str]],
    known_serials: set[str],
    decimals: int,
) -> None:
    for measure in point.get_measures():
        serial_number = measure.get_cube_serial_number()
        if serial_number not in known_serials:
            continue
        registry.setdefault(serial_number, {})[_measure_hash_from_measure(measure, decimals)] = target_point_id


def _merge_source_point_into_target(
    net: ip.ControlNet,
    *,
    target_point_id: str,
    source_point_id: str,
    registry: dict[str, dict[tuple[float, float], str]],
    known_serials: set[str],
    decimals: int,
    merged_point_ids: list[str],
) -> dict[str, int]:
    if target_point_id == source_point_id:
        return {
            "merged_measure_candidate_count": 0,
            "added_measure_count": 0,
            "skipped_existing_serial_count": 0,
        }

    target_point = net.get_point(target_point_id)
    source_point = net.get_point(source_point_id)
    source_measures = list(source_point.get_measures())

    merged_measure_candidate_count = 0
    added_measure_count = 0
    skipped_existing_serial_count = 0

    for measure in source_measures:
        merged_measure_candidate_count += 1
        serial_number = measure.get_cube_serial_number()
        if target_point.has_serial_number(serial_number):
            skipped_existing_serial_count += 1
            continue

        target_point.add_measure(measure)
        added_measure_count += 1

    _update_registry_for_point(
        target_point,
        target_point_id=target_point_id,
        registry=registry,
        known_serials=known_serials,
        decimals=decimals,
    )
    _update_registry_for_point(
        source_point,
        target_point_id=target_point_id,
        registry=registry,
        known_serials=known_serials,
        decimals=decimals,
    )

    net.delete_point(source_point_id)
    merged_point_ids.append(source_point_id)

    return {
        "merged_measure_candidate_count": merged_measure_candidate_count,
        "added_measure_count": added_measure_count,
        "skipped_existing_serial_count": skipped_existing_serial_count,
    }


def merge_controlnet_duplicate_points_in_place(
    net: ip.ControlNet,
    serial_to_image_path: Mapping[str, str],
    *,
    decimals: int = DEFAULT_HASH_DECIMALS,
) -> dict[str, object]:
    validated_decimals = validate_merge_decimals(decimals)
    known_serials = set(serial_to_image_path)

    point_ids = _snapshot_point_ids(net)
    point_order = {point_id: index for index, point_id in enumerate(point_ids)}
    registry: dict[str, dict[tuple[float, float], str]] = {}
    merged_point_ids: list[str] = []

    duplicate_point_count = 0
    merged_point_count = 0
    matched_measure_count = 0
    merged_measure_candidate_count = 0
    added_measure_count = 0
    skipped_existing_serial_count = 0

    point_count_before = net.get_num_points()
    measure_count_before = net.get_num_measures()

    for point_id in point_ids:
        if not net.contains_point(point_id):
            continue

        point = net.get_point(point_id)
        matched_target_ids: set[str] = set()

        for measure in point.get_measures():
            serial_number = measure.get_cube_serial_number()
            if serial_number not in known_serials:
                continue
            matched_point_id = registry.get(serial_number, {}).get(_measure_hash_from_measure(measure, validated_decimals))
            if matched_point_id is None or not net.contains_point(matched_point_id):
                continue
            matched_target_ids.add(matched_point_id)
            matched_measure_count += 1

        if not matched_target_ids:
            _update_registry_for_point(
                point,
                target_point_id=point_id,
                registry=registry,
                known_serials=known_serials,
                decimals=validated_decimals,
            )
            continue

        target_point_id = _select_first_point_id(matched_target_ids, point_order)

        source_point_ids: list[str] = []
        if point_id != target_point_id:
            source_point_ids.append(point_id)
        source_point_ids.extend(
            candidate_id
            for candidate_id in sorted(
                matched_target_ids - {target_point_id, point_id},
                key=lambda candidate_id: point_order.get(candidate_id, sys.maxsize),
            )
            if net.contains_point(candidate_id)
        )

        for source_point_id in source_point_ids:
            if not net.contains_point(source_point_id):
                continue
            counts = _merge_source_point_into_target(
                net,
                target_point_id=target_point_id,
                source_point_id=source_point_id,
                registry=registry,
                known_serials=known_serials,
                decimals=validated_decimals,
                merged_point_ids=merged_point_ids,
            )
            duplicate_point_count += 1
            merged_point_count += 1
            merged_measure_candidate_count += counts["merged_measure_candidate_count"]
            added_measure_count += counts["added_measure_count"]
            skipped_existing_serial_count += counts["skipped_existing_serial_count"]

        _update_registry_for_point(
            net.get_point(target_point_id),
            target_point_id=target_point_id,
            registry=registry,
            known_serials=known_serials,
            decimals=validated_decimals,
        )

    summary = _InPlaceMergeState(
        point_count_before=point_count_before,
        measure_count_before=measure_count_before,
        duplicate_point_count=duplicate_point_count,
        merged_point_count=merged_point_count,
        matched_measure_count=matched_measure_count,
        merged_measure_candidate_count=merged_measure_candidate_count,
        added_measure_count=added_measure_count,
        skipped_existing_serial_count=skipped_existing_serial_count,
        merged_point_ids=tuple(merged_point_ids),
    )
    result = asdict(summary)
    result["point_count_after"] = net.get_num_points()
    result["measure_count_after"] = net.get_num_measures()
    result["decimals"] = validated_decimals
    result["hash_rounding_decimals"] = validated_decimals
    result["hash_strategy"] = MERGE_HASH_STRATEGY
    result["hash_coordinate_fields"] = MERGE_HASH_COORDINATE_FIELDS
    result["hash_description"] = MERGE_HASH_DESCRIPTION
    result["known_image_count"] = len(serial_to_image_path)
    return result


def merge_control_measure_file(
    original_image_list_path: str | Path,
    input_control_net_path: str | Path,
    output_control_net_path: str | Path | None = None,
    *,
    decimals: int = DEFAULT_HASH_DECIMALS,
    pvl_format: bool = False,
) -> dict[str, object]:
    serial_to_image_path = resolve_original_image_serials(original_image_list_path)
    input_path = Path(input_control_net_path)
    output_path = Path(output_control_net_path) if output_control_net_path is not None else _default_output_path(input_path)

    net = ip.ControlNet(str(input_path))
    summary = merge_controlnet_duplicate_points_in_place(net, serial_to_image_path, decimals=decimals)
    net.write(str(output_path), pvl=pvl_format)

    typed_summary = ControlMeasureMergeSummary(
        input_control_net=str(input_path),
        output_control_net=str(output_path),
        original_image_list=str(original_image_list_path),
        point_count_before=int(summary["point_count_before"]),
        point_count_after=int(summary["point_count_after"]),
        measure_count_before=int(summary["measure_count_before"]),
        measure_count_after=int(summary["measure_count_after"]),
        duplicate_point_count=int(summary["duplicate_point_count"]),
        merged_point_count=int(summary["merged_point_count"]),
        matched_measure_count=int(summary["matched_measure_count"]),
        merged_measure_candidate_count=int(summary["merged_measure_candidate_count"]),
        added_measure_count=int(summary["added_measure_count"]),
        skipped_existing_serial_count=int(summary["skipped_existing_serial_count"]),
        decimals=int(summary["decimals"]),
        hash_rounding_decimals=int(summary["hash_rounding_decimals"]),
        hash_strategy=str(summary["hash_strategy"]),
        hash_coordinate_fields=str(summary["hash_coordinate_fields"]),
        hash_description=str(summary["hash_description"]),
        known_image_count=int(summary["known_image_count"]),
        pvl_format=bool(pvl_format),
        merged_point_ids=tuple(str(point_id) for point_id in summary["merged_point_ids"]),
    )
    return asdict(typed_summary)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Post-process a merged ISIS ControlNet by collapsing duplicate ControlPoints whose"
            " per-image measure sample/line coordinates match after rounded hashing."
        )
    )
    parser.add_argument("original_images", help="Path to original_images.lis used to compose cube serial numbers.")
    parser.add_argument("input_control_net", help="Input merged ControlNet path, typically the cnetmerge result.")
    parser.add_argument(
        "output_control_net",
        nargs="?",
        default=None,
        help="Optional output ControlNet path. Defaults to <input>_merged_measures.net.",
    )
    parser.add_argument(
        "--decimals",
        type=_parse_merge_decimals,
        default=DEFAULT_HASH_DECIMALS,
        help="Decimal precision used by the rounded per-image sample/line hash. Valid range: 0-6.",
    )
    parser.add_argument(
        "--pvl-format",
        action="store_true",
        help="Write the output ControlNet in PVL format instead of the default binary format.",
    )
    return parser


def main(argv: list[str] | None = None) -> dict[str, object]:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    result = merge_control_measure_file(
        args.original_images,
        args.input_control_net,
        args.output_control_net,
        decimals=args.decimals,
        pvl_format=args.pvl_format,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    main()
