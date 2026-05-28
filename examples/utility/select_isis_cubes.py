"""Select ISIS cubes from caminfo metadata files.

Author: Geng Xun
Created: 2026-05-28
Updated: 2026-05-28  Geng Xun added the initial caminfo parsing skeleton for cube selection workflows.
Updated: 2026-05-28  Geng Xun aligned the Task 1 caminfo record surface with optional approved field names.
Updated: 2026-05-28  Geng Xun added approved Task 2 caminfo numeric field parsing for selector metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
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
