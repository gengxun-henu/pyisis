"""Select ISIS cubes from caminfo metadata files.

Author: Geng Xun
Created: 2026-05-28
Updated: 2026-05-28  Geng Xun added the initial caminfo parsing skeleton for cube selection workflows.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class CaminfoRecord:
    from_value: str
    cube_path: Path
    center_latitude: float
    center_longitude: float
    subsolar_azimuth: float


def _extract_string(text: str, key: str) -> str:
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=\s*(.+?)\s*$", re.MULTILINE)
    match = pattern.search(text)
    if match is None:
        raise ValueError(f"Missing required caminfo field: {key}")

    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value


def _extract_float(text: str, key: str) -> float:
    return float(_extract_string(text, key))


def parse_caminfo_file(caminfo_path: Path) -> CaminfoRecord:
    caminfo_path = Path(caminfo_path)
    text = caminfo_path.read_text(encoding="utf-8")

    from_value = _extract_string(text, "From")
    cube_path = Path(from_value)
    if not cube_path.is_absolute():
        cube_path = (caminfo_path.parent / cube_path).resolve()

    return CaminfoRecord(
        from_value=from_value,
        cube_path=cube_path,
        center_latitude=_extract_float(text, "CenterLatitude"),
        center_longitude=_extract_float(text, "CenterLongitude"),
        subsolar_azimuth=_extract_float(text, "SubSolarAzimuth"),
    )
