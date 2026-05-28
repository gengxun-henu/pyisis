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
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re
import shutil


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
