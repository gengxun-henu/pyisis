"""Select ISIS cubes from caminfo metadata files.

Author: Geng Xun
Created: 2026-05-28
Updated: 2026-05-28  Geng Xun added the initial caminfo parsing skeleton for cube selection workflows.
Updated: 2026-05-28  Geng Xun aligned the Task 1 caminfo record surface with optional approved field names.
Updated: 2026-05-28  Geng Xun added approved Task 2 caminfo numeric field parsing for selector metadata.
Updated: 2026-05-28  Geng Xun added Task 3 rule evaluation helpers for approved range and center-distance selection.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re


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
    latitude_min: float | None = None
    latitude_max: float | None = None
    longitude_min: float | None = None
    longitude_max: float | None = None
    incidence_min: float | None = None
    incidence_max: float | None = None
    emission_min: float | None = None
    emission_max: float | None = None
    phase_min: float | None = None
    phase_max: float | None = None
    sub_solar_azimuth_min: float | None = None
    sub_solar_azimuth_max: float | None = None
    center_latitude: float | None = None
    center_longitude: float | None = None
    center_distance_max: float | None = None


@dataclass(frozen=True)
class EvaluationOutcome:
    is_match: bool
    reason: str


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
    range_checks = (
        ("latitude", record.center_latitude, criteria.latitude_min, criteria.latitude_max),
        ("longitude", record.center_longitude, criteria.longitude_min, criteria.longitude_max),
        ("incidence", record.incidence, criteria.incidence_min, criteria.incidence_max),
        ("emission", record.emission, criteria.emission_min, criteria.emission_max),
        ("phase", record.phase, criteria.phase_min, criteria.phase_max),
        (
            "sub_solar_azimuth",
            record.sub_solar_azimuth,
            criteria.sub_solar_azimuth_min,
            criteria.sub_solar_azimuth_max,
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
            return EvaluationOutcome(is_match=False, reason=mismatch_reason)

    if criteria.center_distance_max is not None:
        if record.center_latitude is None or record.center_longitude is None:
            return EvaluationOutcome(
                is_match=False,
                reason="Missing required center latitude/longitude for center distance check.",
            )

        if criteria.center_latitude is None or criteria.center_longitude is None:
            return EvaluationOutcome(
                is_match=False,
                reason="Missing required selection center latitude/longitude for center distance check.",
            )

        center_distance = math.hypot(
            record.center_latitude - criteria.center_latitude,
            record.center_longitude - criteria.center_longitude,
        )
        if center_distance > criteria.center_distance_max:
            return EvaluationOutcome(
                is_match=False,
                reason=(
                    f"Center distance {center_distance} exceeds maximum "
                    f"{criteria.center_distance_max}."
                ),
            )

    return EvaluationOutcome(is_match=True, reason="Matched all selection criteria.")


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
