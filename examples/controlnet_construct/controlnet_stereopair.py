"""Build an ISIS ControlNet for a single stereo pair from original-image `.key` files.

Author: Geng Xun
Created: 2026-04-16
Updated: 2026-04-16  Geng Xun added an initial stereo-pair ControlNet builder that reads original-image tie points and writes PVL or binary `.net` files.
Updated: 2026-04-16  Geng Xun added a DOM-key CLI wrapper that chains dom2ori conversion into ControlNet creation.
Updated: 2026-04-16  Geng Xun inserted DOM-space tie-point merging into the from-dom pipeline so the wrapped CLI now covers merge plus dom2ori plus ControlNet creation.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.dom2ori import convert_dom_keypoints_to_original
    from controlnet_construct.keypoints import read_key_file
    from controlnet_construct.tie_point_merge_in_overlap import merge_stereo_pair_key_files
    from controlnet_construct.runtime import bootstrap_runtime_environment
else:
    from .dom2ori import convert_dom_keypoints_to_original
    from .keypoints import read_key_file
    from .runtime import bootstrap_runtime_environment
    from .tie_point_merge_in_overlap import merge_stereo_pair_key_files


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


@dataclass(frozen=True, slots=True)
class ControlNetConfig:
    network_id: str
    target_name: str
    user_name: str
    description: str = ""
    point_id_prefix: str = "P"


def _default_intermediate_key_path(output_path: str | Path, side: str, stage: str) -> Path:
    output = Path(output_path)
    return output.with_name(f"{output.stem}_{side}_{stage}.key")


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


def read_controlnet_config(config_path: str | Path) -> ControlNetConfig:
    payload = json.loads(Path(config_path).read_text(encoding="utf-8"))
    network_id = _first_present(payload, "NetworkId", "network_id")
    target_name = _first_present(payload, "TargetName", "target_name")
    user_name = _first_present(payload, "UserName", "user_name")
    description = _first_present(payload, "Description", "description") or ""
    point_id_prefix = _first_present(payload, "PointIdPrefix", "point_id_prefix") or "P"

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

    for index, (left_point, right_point) in enumerate(
        zip(left_key_file.points, right_key_file.points, strict=True),
        start=1,
    ):
        point = ip.ControlPoint(f"{config.point_id_prefix}{index:06d}")
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
    left_output_key_path: str | Path | None = None,
    right_output_key_path: str | Path | None = None,
    merge_decimals: int = 3,
    skip_merge: bool = False,
    dom_band: int = 1,
    left_original_band: int = 1,
    right_original_band: int = 1,
    left_failure_log_path: str | Path | None = None,
    right_failure_log_path: str | Path | None = None,
    pvl_format: bool = True,
    logger: logging.Logger | None = None,
) -> dict[str, object]:
    left_output_key = Path(left_output_key_path) if left_output_key_path is not None else _default_intermediate_key_path(output_path, "left", "ori")
    right_output_key = Path(right_output_key_path) if right_output_key_path is not None else _default_intermediate_key_path(output_path, "right", "ori")
    left_merged_dom_key = Path(left_merged_dom_key_path) if left_merged_dom_key_path is not None else _default_intermediate_key_path(output_path, "left", "dom_merged")
    right_merged_dom_key = Path(right_merged_dom_key_path) if right_merged_dom_key_path is not None else _default_intermediate_key_path(output_path, "right", "dom_merged")

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
            "decimals": merge_decimals,
        }
        left_dom_key_for_conversion = Path(left_dom_key_path)
        right_dom_key_for_conversion = Path(right_dom_key_path)
    else:
        merge_stats = merge_stereo_pair_key_files(
            str(left_dom_key_path),
            str(right_dom_key_path),
            str(left_merged_dom_key),
            str(right_merged_dom_key),
            decimals=merge_decimals,
        )
        merge_result = {
            "applied": True,
            **merge_stats,
        }
        left_dom_key_for_conversion = left_merged_dom_key
        right_dom_key_for_conversion = right_merged_dom_key
        if logger is not None:
            logger.info(
                "controlnet_stereopair merged DOM tie points: input_count=%s unique_count=%s duplicate_count=%s",
                merge_stats["input_count"],
                merge_stats["unique_count"],
                merge_stats["duplicate_count"],
            )

    left_conversion = convert_dom_keypoints_to_original(
        left_dom_key_for_conversion,
        left_dom_cube_path,
        left_cube_path,
        left_output_key,
        dom_band=dom_band,
        original_band=left_original_band,
        failure_log_path=left_failure_log_path,
        logger=logger,
    )
    right_conversion = convert_dom_keypoints_to_original(
        right_dom_key_for_conversion,
        right_dom_cube_path,
        right_cube_path,
        right_output_key,
        dom_band=dom_band,
        original_band=right_original_band,
        failure_log_path=right_failure_log_path,
        logger=logger,
    )

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
        "left_conversion": left_conversion,
        "right_conversion": right_conversion,
        "controlnet": controlnet_result,
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
    parser.add_argument("--left-merged-dom-key", default=None, help="Optional path to persist the merged DOM-space .key for image A before dom2ori.")
    parser.add_argument("--right-merged-dom-key", default=None, help="Optional path to persist the merged DOM-space .key for image B before dom2ori.")
    parser.add_argument("--left-output-key", default=None, help="Optional path to persist the converted original-image .key for image A.")
    parser.add_argument("--right-output-key", default=None, help="Optional path to persist the converted original-image .key for image B.")
    parser.add_argument("--merge-decimals", type=int, default=3, help="Number of decimal places used when merging duplicate DOM tie points.")
    parser.add_argument("--skip-merge", action="store_true", help="Skip DOM-space duplicate merge and pass the input DOM .key files straight to dom2ori.")
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


def _normalize_cli_argv(argv: list[str]) -> list[str]:
    if argv and argv[0] not in {"from-ori", "from-dom", "-h", "--help"}:
        return ["from-ori", *argv]
    return argv


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a single stereo-pair ISIS ControlNet from original-image or DOM-space `.key` files.")
    subparsers = parser.add_subparsers(dest="command")
    _build_from_original_parser(subparsers)
    _build_from_dom_parser(subparsers)
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
        config = read_controlnet_config(args.config)
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
            left_output_key_path=args.left_output_key,
            right_output_key_path=args.right_output_key,
            merge_decimals=args.merge_decimals,
            skip_merge=args.skip_merge,
            dom_band=args.dom_band,
            left_original_band=args.left_original_band,
            right_original_band=args.right_original_band,
            left_failure_log_path=args.left_failure_log,
            right_failure_log_path=args.right_failure_log,
            pvl_format=not args.binary,
            logger=logger,
        )
    else:
        config = read_controlnet_config(args.config)
        result = build_controlnet_for_stereo_pair(
            args.left_key,
            args.right_key,
            args.left_cube,
            args.right_cube,
            config,
            args.output_net,
            pvl_format=not args.binary,
        )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()