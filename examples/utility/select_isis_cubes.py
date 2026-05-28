"""Select ISIS cubes from caminfo metadata files.

Author: Geng Xun
Created: 2026-05-28
Updated: 2026-05-28  Geng Xun added the initial caminfo parsing skeleton for cube selection workflows.
Updated: 2026-05-28  Geng Xun aligned the Task 1 caminfo record surface with optional approved field names.
Updated: 2026-05-28  Geng Xun added approved Task 2 caminfo numeric field parsing for selector metadata.
Updated: 2026-05-28  Geng Xun added Task 3 rule evaluation helpers for approved range and center-distance selection.
Updated: 2026-05-28  Geng Xun aligned Task 3 selection criteria names and list-based evaluation outcomes with the approved plan surface.
Updated: 2026-05-28  Geng Xun added Task 4 move execution helpers with unresolved, dry-run, conflict, and successful move outcomes.
Updated: 2026-05-28  Geng Xun aligned Task 4 move-result field names and status strings with the approved plan surface.
Updated: 2026-05-28  Geng Xun added Task 5 CLI argument parsing, validation, batched execution, and concise summary output.
Updated: 2026-05-28  Geng Xun hardened Task 5 batch input handling for unreadable list files, per-entry parse failures, and invalid negative center distance.
Updated: 2026-05-28  Geng Xun polished Task 6 verbose reporting so per-entry diagnostics keep caminfo context and unresolved move details readable.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
from pathlib import Path
import re
import shutil
import sys


@dataclass(frozen=True)
class CaminfoRecord:
    cube_name: str | None
    cube_path: Path | None
    center_latitude: float | None
    center_longitude: float | None
    minimum_latitude: float | None
    maximum_latitude: float | None
    minimum_longitude: float | None
    maximum_longitude: float | None
    incidence: float | None
    emission: float | None
    phase: float | None
    sub_solar_azimuth: float | None


@dataclass(frozen=True)
class SelectionCriteria:
    center_latitude: float | None = None
    center_longitude: float | None = None
    max_center_distance_deg: float | None = None
    min_latitude: float | None = None
    max_latitude: float | None = None
    min_longitude: float | None = None
    max_longitude: float | None = None
    min_incidence: float | None = None
    max_incidence: float | None = None
    min_emission: float | None = None
    max_emission: float | None = None
    min_phase: float | None = None
    max_phase: float | None = None
    min_sub_solar_azimuth: float | None = None
    max_sub_solar_azimuth: float | None = None


@dataclass(frozen=True)
class EvaluationOutcome:
    matched: bool
    reasons: list[str]


@dataclass(frozen=True)
class MoveResult:
    status: str
    source: Path | None
    destination: Path | None
    detail: str | None = None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select ISIS cubes from caminfo metadata files and move matches.",
    )
    parser.add_argument("--caminfo-list", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--center-latitude", type=float)
    parser.add_argument("--center-longitude", type=float)
    parser.add_argument("--max-center-distance-deg", type=float)
    parser.add_argument("--min-latitude", type=float)
    parser.add_argument("--max-latitude", type=float)
    parser.add_argument("--min-longitude", type=float)
    parser.add_argument("--max-longitude", type=float)
    parser.add_argument("--min-incidence", type=float)
    parser.add_argument("--max-incidence", type=float)
    parser.add_argument("--min-emission", type=float)
    parser.add_argument("--max-emission", type=float)
    parser.add_argument("--min-phase", type=float)
    parser.add_argument("--max-phase", type=float)
    parser.add_argument("--min-sub-solar-azimuth", type=float)
    parser.add_argument("--max-sub-solar-azimuth", type=float)
    return parser.parse_args(argv)


def _validate_min_max(
    field_name: str,
    minimum: float | None,
    maximum: float | None,
) -> None:
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError(
            f"Invalid {field_name} range: minimum {minimum} cannot exceed maximum {maximum}.",
        )


def build_criteria(args: argparse.Namespace) -> SelectionCriteria:
    center_distance_values = (
        args.center_latitude,
        args.center_longitude,
        args.max_center_distance_deg,
    )
    provided_center_distance_values = [value for value in center_distance_values if value is not None]
    if provided_center_distance_values and len(provided_center_distance_values) != len(center_distance_values):
        raise ValueError(
            "Incomplete center distance filter: provide --center-latitude, "
            "--center-longitude, and --max-center-distance-deg together.",
        )

    if args.max_center_distance_deg is not None and args.max_center_distance_deg < 0:
        raise ValueError(
            "Invalid --max-center-distance-deg value: cannot be negative.",
        )

    _validate_min_max("latitude", args.min_latitude, args.max_latitude)
    _validate_min_max("longitude", args.min_longitude, args.max_longitude)
    _validate_min_max("incidence", args.min_incidence, args.max_incidence)
    _validate_min_max("emission", args.min_emission, args.max_emission)
    _validate_min_max("phase", args.min_phase, args.max_phase)
    _validate_min_max(
        "sub-solar azimuth",
        args.min_sub_solar_azimuth,
        args.max_sub_solar_azimuth,
    )

    return SelectionCriteria(
        center_latitude=args.center_latitude,
        center_longitude=args.center_longitude,
        max_center_distance_deg=args.max_center_distance_deg,
        min_latitude=args.min_latitude,
        max_latitude=args.max_latitude,
        min_longitude=args.min_longitude,
        max_longitude=args.max_longitude,
        min_incidence=args.min_incidence,
        max_incidence=args.max_incidence,
        min_emission=args.min_emission,
        max_emission=args.max_emission,
        min_phase=args.min_phase,
        max_phase=args.max_phase,
        min_sub_solar_azimuth=args.min_sub_solar_azimuth,
        max_sub_solar_azimuth=args.max_sub_solar_azimuth,
    )


def _read_caminfo_list(list_path: Path) -> list[Path]:
    resolved_list_path = Path(list_path)
    caminfo_paths: list[Path] = []
    for line in resolved_list_path.read_text(encoding="utf-8").splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            continue

        entry_path = Path(stripped_line)
        if not entry_path.is_absolute():
            entry_path = (resolved_list_path.parent / entry_path).resolve()
        caminfo_paths.append(entry_path)

    return caminfo_paths


def _evaluate_range(
    *,
    field_name: str,
    value: float | None,
    minimum: float | None,
    maximum: float | None,
) -> str | None:
    if minimum is None and maximum is None:
        return None

    if value is None:
        return f"Missing required {field_name} value for selection criteria."

    if minimum is not None and value < minimum:
        return f"{field_name} {value} is below minimum {minimum}."

    if maximum is not None and value > maximum:
        return f"{field_name} {value} exceeds maximum {maximum}."

    return None


def evaluate_record(record: CaminfoRecord, criteria: SelectionCriteria) -> EvaluationOutcome:
    reasons: list[str] = []

    range_checks = (
        ("latitude", record.center_latitude, criteria.min_latitude, criteria.max_latitude),
        ("longitude", record.center_longitude, criteria.min_longitude, criteria.max_longitude),
        ("incidence", record.incidence, criteria.min_incidence, criteria.max_incidence),
        ("emission", record.emission, criteria.min_emission, criteria.max_emission),
        ("phase", record.phase, criteria.min_phase, criteria.max_phase),
        (
            "sub_solar_azimuth",
            record.sub_solar_azimuth,
            criteria.min_sub_solar_azimuth,
            criteria.max_sub_solar_azimuth,
        ),
    )

    for field_name, value, minimum, maximum in range_checks:
        mismatch_reason = _evaluate_range(
            field_name=field_name,
            value=value,
            minimum=minimum,
            maximum=maximum,
        )
        if mismatch_reason is not None:
            reasons.append(mismatch_reason)

    if criteria.max_center_distance_deg is not None:
        if record.center_latitude is None or record.center_longitude is None:
            reasons.append(
                "Missing required center latitude/longitude for center distance check.",
            )
        elif criteria.center_latitude is None or criteria.center_longitude is None:
            reasons.append(
                "Missing required selection center latitude/longitude for center distance check.",
            )
        else:
            center_distance = math.hypot(
                record.center_latitude - criteria.center_latitude,
                record.center_longitude - criteria.center_longitude,
            )
            if center_distance > criteria.max_center_distance_deg:
                reasons.append(
                    f"Center distance {center_distance} exceeds maximum "
                    f"{criteria.max_center_distance_deg}."
                )

    return EvaluationOutcome(matched=not reasons, reasons=reasons)


def execute_move(record: CaminfoRecord, output_dir: Path, dry_run: bool) -> MoveResult:
    source_path = None if record.cube_path is None else Path(record.cube_path)
    output_dir = Path(output_dir)

    if source_path is None:
        return MoveResult(
            status="unresolved",
            source=None,
            destination=None,
            detail="Cannot move cube because the cube path is missing.",
        )

    destination_path = output_dir / source_path.name

    if not source_path.exists():
        return MoveResult(
            status="unresolved",
            source=source_path,
            destination=None,
            detail=f"Cannot move cube because source path does not exist: {source_path}",
        )

    if dry_run:
        return MoveResult(
            status="dry-run",
            source=source_path,
            destination=destination_path,
            detail=f"Dry-run only; cube would be moved to {destination_path}",
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    if destination_path.exists():
        return MoveResult(
            status="destination-conflict",
            source=source_path,
            destination=destination_path,
            detail=(
                "Cannot move cube because the destination already exists: "
                f"{destination_path}"
            ),
        )

    shutil.move(str(source_path), str(destination_path))
    return MoveResult(
        status="moved",
        source=source_path,
        destination=destination_path,
        detail=f"Moved cube to {destination_path}",
    )


def _extract_string(text: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(text)
    if match is None:
        return None

    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value


def _extract_float(text: str, pattern: re.Pattern[str]) -> float | None:
    value = _extract_string(text, pattern)
    if value is None:
        return None

    return float(value)


def parse_caminfo_file(caminfo_path: Path) -> CaminfoRecord:
    caminfo_path = Path(caminfo_path)
    text = caminfo_path.read_text(encoding="utf-8")

    from_pattern = re.compile(r"^\s*From\s*=\s*(.+?)\s*$", re.MULTILINE)
    center_latitude_pattern = re.compile(r"^\s*CenterLatitude\s*=\s*(.+?)\s*$", re.MULTILINE)
    center_longitude_pattern = re.compile(r"^\s*CenterLongitude\s*=\s*(.+?)\s*$", re.MULTILINE)
    minimum_latitude_pattern = re.compile(r"^\s*MinimumLatitude\s*=\s*(.+?)\s*$", re.MULTILINE)
    maximum_latitude_pattern = re.compile(r"^\s*MaximumLatitude\s*=\s*(.+?)\s*$", re.MULTILINE)
    minimum_longitude_pattern = re.compile(r"^\s*MinimumLongitude\s*=\s*(.+?)\s*$", re.MULTILINE)
    maximum_longitude_pattern = re.compile(r"^\s*MaximumLongitude\s*=\s*(.+?)\s*$", re.MULTILINE)
    incidence_angle_pattern = re.compile(r"^\s*IncidenceAngle\s*=\s*(.+?)\s*$", re.MULTILINE)
    emission_angle_pattern = re.compile(r"^\s*EmissionAngle\s*=\s*(.+?)\s*$", re.MULTILINE)
    phase_angle_pattern = re.compile(r"^\s*PhaseAngle\s*=\s*(.+?)\s*$", re.MULTILINE)
    sub_solar_azimuth_pattern = re.compile(r"^\s*SubSolarAzimuth\s*=\s*(.+?)\s*$", re.MULTILINE)

    cube_name = _extract_string(text, from_pattern)
    cube_path = None
    if cube_name is not None:
        cube_path = Path(cube_name)
        if not cube_path.is_absolute():
            cube_path = (caminfo_path.parent / cube_path).resolve()

    return CaminfoRecord(
        cube_name=cube_name,
        cube_path=cube_path,
        center_latitude=_extract_float(text, center_latitude_pattern),
        center_longitude=_extract_float(text, center_longitude_pattern),
        minimum_latitude=_extract_float(text, minimum_latitude_pattern),
        maximum_latitude=_extract_float(text, maximum_latitude_pattern),
        minimum_longitude=_extract_float(text, minimum_longitude_pattern),
        maximum_longitude=_extract_float(text, maximum_longitude_pattern),
        incidence=_extract_float(text, incidence_angle_pattern),
        emission=_extract_float(text, emission_angle_pattern),
        phase=_extract_float(text, phase_angle_pattern),
        sub_solar_azimuth=_extract_float(text, sub_solar_azimuth_pattern),
    )


def _record_display_label(record: CaminfoRecord) -> str:
    if record.cube_name:
        return record.cube_name

    if record.cube_path is not None:
        return record.cube_path.name

    return "<unknown cube>"


def _format_match_diagnostic(
    caminfo_path: Path,
    record: CaminfoRecord,
    move_result: MoveResult,
) -> str:
    message = (
        f"MATCH {caminfo_path} -> {_record_display_label(record)} "
        f"[{move_result.status}]"
    )
    if move_result.detail:
        message += f": {move_result.detail}"
    return message


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        criteria = build_criteria(args)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    try:
        caminfo_paths = _read_caminfo_list(args.caminfo_list)
    except OSError as error:
        print(
            f"Error: Unable to read caminfo list {args.caminfo_list}: {error}",
            file=sys.stderr,
        )
        return 2

    matched_count = 0
    skipped_count = 0
    parse_failure_count = 0
    moved_count = 0
    dry_run_count = 0
    destination_conflict_count = 0
    unresolved_count = 0

    for caminfo_path in caminfo_paths:
        try:
            record = parse_caminfo_file(caminfo_path)
        except (OSError, ValueError) as error:
            parse_failure_count += 1
            if args.verbose:
                print(f"PARSE-FAIL {caminfo_path}: {error}")
            continue

        evaluation = evaluate_record(record, criteria)
        if not evaluation.matched:
            skipped_count += 1
            if args.verbose:
                print(
                    f"SKIP {caminfo_path}: {'; '.join(evaluation.reasons)}",
                )
            continue

        matched_count += 1
        move_result = execute_move(record, args.output_dir, args.dry_run)
        if move_result.status == "moved":
            moved_count += 1
        elif move_result.status == "dry-run":
            dry_run_count += 1
        elif move_result.status == "destination-conflict":
            destination_conflict_count += 1
        elif move_result.status == "unresolved":
            unresolved_count += 1

        if args.verbose:
            print(_format_match_diagnostic(caminfo_path, record, move_result))

    print(
        " ".join(
            [
                f"Processed {len(caminfo_paths)} caminfo files.",
                f"Matched {matched_count}.",
                f"Skipped {skipped_count}.",
                f"Parse failures {parse_failure_count}.",
                f"Moved {moved_count}.",
                f"Dry-run moves {dry_run_count}.",
                f"Destination conflicts {destination_conflict_count}.",
                f"Unresolved moves {unresolved_count}.",
            ]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
