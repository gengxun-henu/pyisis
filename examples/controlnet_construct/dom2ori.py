"""Convert DOM-space tie points into original-image pixel coordinates.

Author: Geng Xun
Created: 2026-04-16
Updated: 2026-04-16  Geng Xun added an initial DOM-to-original coordinate conversion workflow using UniversalGroundMap with projection-first and camera-first backends.
Updated: 2026-04-16  Geng Xun strengthened failure classification, structured failure logs, and file-based semi-integration helpers for DOM-to-original conversion.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from dataclasses import dataclass
import json
import logging
import math
from pathlib import Path
import sys


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.keypoints import Keypoint, KeypointFile, read_key_file, write_key_file
    from controlnet_construct.runtime import bootstrap_runtime_environment
else:
    from .keypoints import Keypoint, KeypointFile, read_key_file, write_key_file
    from .runtime import bootstrap_runtime_environment


bootstrap_runtime_environment()

import isis_pybind as ip


@dataclass(frozen=True, slots=True)
class DomToOriginalFailure:
    index: int
    sample: float
    line: float
    reason: str
    category: str
    detail: str = ""
    latitude: float | None = None
    longitude: float | None = None
    projected_sample: float | None = None
    projected_line: float | None = None


@dataclass(frozen=True, slots=True)
class DomToOriginalSummary:
    input_count: int
    output_count: int
    failure_count: int
    failure_reasons: dict[str, int]
    failure_categories: dict[str, int]


def _is_point_in_bounds(sample: float, line: float, width: int, height: int) -> bool:
    return 1.0 <= sample <= float(width) and 1.0 <= line <= float(height)


def _build_failure(
    index: int,
    sample: float,
    line: float,
    *,
    reason: str,
    category: str,
    detail: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
    projected_sample: float | None = None,
    projected_line: float | None = None,
) -> DomToOriginalFailure:
    return DomToOriginalFailure(
        index=index,
        sample=sample,
        line=line,
        reason=reason,
        category=category,
        detail=detail,
        latitude=latitude,
        longitude=longitude,
        projected_sample=projected_sample,
        projected_line=projected_line,
    )


def _append_failure(
    failures: list[DomToOriginalFailure],
    failure: DomToOriginalFailure,
    *,
    logger: logging.Logger | None,
) -> None:
    failures.append(failure)
    if logger is not None:
        logger.warning(
            "dom2ori point #%d failed [%s/%s] sample=%.6f line=%.6f detail=%s",
            failure.index,
            failure.category,
            failure.reason,
            failure.sample,
            failure.line,
            failure.detail or "-",
        )


def _build_summary(input_count: int, output_count: int, failures: list[DomToOriginalFailure]) -> DomToOriginalSummary:
    reason_counts = Counter(failure.reason for failure in failures)
    category_counts = Counter(failure.category for failure in failures)
    return DomToOriginalSummary(
        input_count=input_count,
        output_count=output_count,
        failure_count=len(failures),
        failure_reasons=dict(reason_counts),
        failure_categories=dict(category_counts),
    )


def _write_failure_log(failure_log_path: str | Path, payload: dict[str, object]) -> None:
    Path(failure_log_path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def convert_points_via_ground_functions(
    dom_key_file: KeypointFile,
    *,
    ground_lookup,
    image_project,
    output_width: int,
    output_height: int,
    logger: logging.Logger | None = None,
    validate_input_bounds: bool = True,
    require_output_in_bounds: bool = True,
) -> tuple[KeypointFile, list[DomToOriginalFailure], DomToOriginalSummary]:
    """Convert points using injected ground-lookup and image-projection callables."""
    output_points: list[Keypoint] = []
    failures: list[DomToOriginalFailure] = []

    for index, point in enumerate(dom_key_file.points, start=1):
        if validate_input_bounds and not _is_point_in_bounds(
            point.sample,
            point.line,
            dom_key_file.image_width,
            dom_key_file.image_height,
        ):
            _append_failure(
                failures,
                _build_failure(
                    index,
                    point.sample,
                    point.line,
                    reason="dom_point_out_of_bounds",
                    category="input_validation",
                    detail=(
                        f"DOM keypoint lies outside declared image bounds "
                        f"{dom_key_file.image_width}x{dom_key_file.image_height}."
                    ),
                ),
                logger=logger,
            )
            continue

        try:
            ground = ground_lookup(point.sample, point.line)
        except Exception as exc:  # pragma: no cover - defensive path, covered via unit test with stub exceptions
            _append_failure(
                failures,
                _build_failure(
                    index,
                    point.sample,
                    point.line,
                    reason="dom_lookup_exception",
                    category="dom_lookup",
                    detail=f"{type(exc).__name__}: {exc}",
                ),
                logger=logger,
            )
            continue

        if ground is None:
            _append_failure(
                failures,
                _build_failure(
                    index,
                    point.sample,
                    point.line,
                    reason="dom_lookup_failed",
                    category="dom_lookup",
                    detail="DOM cube could not resolve a valid ground location for this image coordinate.",
                ),
                logger=logger,
            )
            continue

        try:
            latitude, longitude = ground
        except Exception as exc:
            _append_failure(
                failures,
                _build_failure(
                    index,
                    point.sample,
                    point.line,
                    reason="dom_lookup_invalid_payload",
                    category="dom_lookup",
                    detail=f"Unable to unpack ground tuple: {type(exc).__name__}: {exc}",
                ),
                logger=logger,
            )
            continue

        if not (math.isfinite(latitude) and math.isfinite(longitude)):
            _append_failure(
                failures,
                _build_failure(
                    index,
                    point.sample,
                    point.line,
                    reason="dom_ground_not_finite",
                    category="dom_lookup",
                    detail="DOM ground lookup returned a non-finite latitude/longitude.",
                    latitude=latitude,
                    longitude=longitude,
                ),
                logger=logger,
            )
            continue

        try:
            projected = image_project(latitude, longitude)
        except Exception as exc:  # pragma: no cover - defensive path, covered via unit test with stub exceptions
            _append_failure(
                failures,
                _build_failure(
                    index,
                    point.sample,
                    point.line,
                    reason="original_projection_exception",
                    category="original_projection",
                    detail=f"{type(exc).__name__}: {exc}",
                    latitude=latitude,
                    longitude=longitude,
                ),
                logger=logger,
            )
            continue

        if projected is None:
            _append_failure(
                failures,
                _build_failure(
                    index,
                    point.sample,
                    point.line,
                    reason="original_projection_failed",
                    category="original_projection",
                    detail="Original cube could not project the DOM ground point into image coordinates.",
                    latitude=latitude,
                    longitude=longitude,
                ),
                logger=logger,
            )
            continue

        try:
            projected_sample, projected_line = projected
        except Exception as exc:
            _append_failure(
                failures,
                _build_failure(
                    index,
                    point.sample,
                    point.line,
                    reason="original_projection_invalid_payload",
                    category="original_projection",
                    detail=f"Unable to unpack projected tuple: {type(exc).__name__}: {exc}",
                    latitude=latitude,
                    longitude=longitude,
                ),
                logger=logger,
            )
            continue

        if not (math.isfinite(projected_sample) and math.isfinite(projected_line)):
            _append_failure(
                failures,
                _build_failure(
                    index,
                    point.sample,
                    point.line,
                    reason="original_pixel_not_finite",
                    category="original_projection",
                    detail="Original projection returned a non-finite sample/line.",
                    latitude=latitude,
                    longitude=longitude,
                    projected_sample=projected_sample,
                    projected_line=projected_line,
                ),
                logger=logger,
            )
            continue

        if require_output_in_bounds and not _is_point_in_bounds(
            projected_sample,
            projected_line,
            output_width,
            output_height,
        ):
            _append_failure(
                failures,
                _build_failure(
                    index,
                    point.sample,
                    point.line,
                    reason="original_point_out_of_bounds",
                    category="output_validation",
                    detail=f"Projected point lies outside output image bounds {output_width}x{output_height}.",
                    latitude=latitude,
                    longitude=longitude,
                    projected_sample=projected_sample,
                    projected_line=projected_line,
                ),
                logger=logger,
            )
            continue

        output_points.append(Keypoint(projected_sample, projected_line))

    output_key_file = KeypointFile(output_width, output_height, tuple(output_points))
    summary = _build_summary(len(dom_key_file.points), len(output_points), failures)
    return output_key_file, failures, summary


def convert_dom_key_file_via_ground_functions(
    dom_key_path: str | Path,
    output_key_path: str | Path,
    *,
    ground_lookup,
    image_project,
    output_width: int,
    output_height: int,
    failure_log_path: str | Path | None = None,
    logger: logging.Logger | None = None,
    validate_input_bounds: bool = True,
    require_output_in_bounds: bool = True,
) -> dict[str, object]:
    """Convert a `.key` file through injected geometry functions and persist structured results.

    This helper is intended for semi-integration tests and fallback wiring when a fully paired
    DOM/original dataset is not yet available.
    """
    dom_key_file = read_key_file(dom_key_path)
    output_key_file, failures, summary = convert_points_via_ground_functions(
        dom_key_file,
        ground_lookup=ground_lookup,
        image_project=image_project,
        output_width=output_width,
        output_height=output_height,
        logger=logger,
        validate_input_bounds=validate_input_bounds,
        require_output_in_bounds=require_output_in_bounds,
    )
    write_key_file(output_key_path, output_key_file)

    result = {
        "dom_key": str(dom_key_path),
        "output_key": str(output_key_path),
        "input_count": summary.input_count,
        "output_count": summary.output_count,
        "failure_count": summary.failure_count,
        "failure_reasons": summary.failure_reasons,
        "failure_categories": summary.failure_categories,
        "failures": [asdict(failure) for failure in failures],
    }
    if failure_log_path is not None:
        _write_failure_log(failure_log_path, result)
        result["failure_log"] = str(failure_log_path)

    return result


def convert_dom_keypoints_to_original(
    dom_key_path: str | Path,
    dom_cube_path: str | Path,
    original_cube_path: str | Path,
    output_key_path: str | Path,
    *,
    dom_band: int = 1,
    original_band: int = 1,
    failure_log_path: str | Path | None = None,
    logger: logging.Logger | None = None,
    require_output_in_bounds: bool = True,
) -> dict[str, object]:
    """Convert DOM-space keypoints to original-image coordinates using UniversalGroundMap."""
    dom_cube = ip.Cube()
    original_cube = ip.Cube()
    if logger is not None:
        logger.info(
            "dom2ori starting: dom_key=%s dom_cube=%s original_cube=%s output_key=%s",
            dom_key_path,
            dom_cube_path,
            original_cube_path,
            output_key_path,
        )
    dom_cube.open(str(dom_cube_path), "r")
    original_cube.open(str(original_cube_path), "r")
    try:
        if dom_band <= 0 or dom_band > dom_cube.band_count():
            raise ValueError(f"DOM band {dom_band} is out of range for cube {dom_cube_path}.")
        if original_band <= 0 or original_band > original_cube.band_count():
            raise ValueError(f"Original band {original_band} is out of range for cube {original_cube_path}.")

        dom_ground_map = ip.UniversalGroundMap(
            dom_cube,
            ip.UniversalGroundMap.CameraPriority.ProjectionFirst,
        )
        original_ground_map = ip.UniversalGroundMap(
            original_cube,
            ip.UniversalGroundMap.CameraPriority.CameraFirst,
        )
        dom_ground_map.set_band(dom_band)
        original_ground_map.set_band(original_band)

        def ground_lookup(sample: float, line: float):
            if not dom_ground_map.set_image(sample, line):
                return None
            return dom_ground_map.universal_latitude(), dom_ground_map.universal_longitude()

        def image_project(latitude: float, longitude: float):
            if not original_ground_map.set_universal_ground(latitude, longitude):
                return None
            return original_ground_map.sample(), original_ground_map.line()

        result = convert_dom_key_file_via_ground_functions(
            dom_key_path,
            output_key_path,
            ground_lookup=ground_lookup,
            image_project=image_project,
            output_width=original_cube.sample_count(),
            output_height=original_cube.line_count(),
            failure_log_path=failure_log_path,
            logger=logger,
            require_output_in_bounds=require_output_in_bounds,
        )
        result["dom_cube"] = str(dom_cube_path)
        result["original_cube"] = str(original_cube_path)
        result["dom_band"] = dom_band
        result["original_band"] = original_band
        if logger is not None:
            logger.info(
                "dom2ori completed: output_count=%s failure_count=%s",
                result["output_count"],
                result["failure_count"],
            )
        return result
    finally:
        if dom_cube.is_open():
            dom_cube.close()
        if original_cube.is_open():
            original_cube.close()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert DOM-space tie points into original-image coordinates.")
    parser.add_argument("dom_key", help="Input DOM-space .key file.")
    parser.add_argument("dom_cube", help="DOM cube path.")
    parser.add_argument("original_cube", help="Original-image cube path.")
    parser.add_argument("output_key", help="Output original-image .key path.")
    parser.add_argument("--dom-band", type=int, default=1, help="Band index to use when reading the DOM cube.")
    parser.add_argument("--original-band", type=int, default=1, help="Band index to use when projecting into the original cube.")
    parser.add_argument("--failure-log", default=None, help="Optional JSON path that records structured conversion failures.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity for runtime diagnostics.",
    )
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(message)s")
    logger = logging.getLogger("controlnet_construct.dom2ori")
    result = convert_dom_keypoints_to_original(
        args.dom_key,
        args.dom_cube,
        args.original_cube,
        args.output_key,
        dom_band=args.dom_band,
        original_band=args.original_band,
        failure_log_path=args.failure_log,
        logger=logger,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()