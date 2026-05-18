"""Solar lighting-difference metrics for adaptive matcher routing.

Author: Geng Xun
Created: 2026-05-18
Updated: 2026-05-18  Geng Xun added cube-label solar geometry parsing with
    mission-aware keyword fallbacks, azimuth-wrap difference, and the initial
    normalized weighted-sum lighting-difference score.

This first release intentionally limits itself to solar elevation and solar
azimuth read from the cube ``Instrument`` group; ``incidence``, ``emission``,
and ``phase`` angles are reserved for future expansion without changing the
public API.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

import math


DEFAULT_SOLAR_ELEVATION_KEYWORDS: tuple[str, ...] = (
    "SolarElevation",
    "SolarElevationAngle",
    "SubSolarLatitude",
)
DEFAULT_SOLAR_AZIMUTH_KEYWORDS: tuple[str, ...] = (
    "SolarAzimuth",
    "SubSolarAzimuth",
    "SunAzimuth",
)
DEFAULT_INSTRUMENT_GROUP_NAMES: tuple[str, ...] = (
    "Instrument",
    "Photometry",
)

DEFAULT_ELEVATION_WEIGHT = 0.4
DEFAULT_AZIMUTH_WEIGHT = 0.6
DEFAULT_ELEVATION_NORMALIZER_DEGREES = 90.0
DEFAULT_AZIMUTH_NORMALIZER_DEGREES = 180.0


class SolarGeometryFieldMissing(LookupError):
    """Raised when neither elevation nor azimuth fields can be resolved from a cube label."""


@dataclass(frozen=True, slots=True)
class SolarGeometry:
    """Solar geometry sampled from a cube label."""

    solar_elevation_degrees: float | None
    solar_azimuth_degrees: float | None
    source_group_name: str | None
    elevation_keyword: str | None
    azimuth_keyword: str | None


@dataclass(frozen=True, slots=True)
class LightingDifferenceSummary:
    """Pair-level lighting-difference diagnostic payload."""

    left_solar_geometry: SolarGeometry
    right_solar_geometry: SolarGeometry
    elevation_difference_degrees: float | None
    azimuth_difference_degrees: float | None
    normalized_elevation_difference: float | None
    normalized_azimuth_difference: float | None
    lighting_difference_score: float | None
    elevation_weight: float
    azimuth_weight: float
    reason: str


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))


def _finite_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(resolved):
        return None
    return resolved


def _coerce_keyword_value(keyword: Any) -> float | None:
    """Return the first finite float in a PVL keyword-like value.

    Accepts ISIS ``PvlKeyword`` objects (indexable, length 1+), strings, and
    plain numbers. Returns ``None`` if no usable float can be extracted.
    """

    if keyword is None:
        return None
    if isinstance(keyword, (int, float)):
        return _finite_float(keyword)
    if isinstance(keyword, str):
        return _finite_float(keyword)

    try:
        candidate = keyword[0]
    except (TypeError, IndexError, KeyError):
        candidate = keyword

    if isinstance(candidate, (int, float)):
        return _finite_float(candidate)

    if isinstance(candidate, str):
        return _finite_float(candidate)

    try:
        return _finite_float(str(candidate))
    except Exception:
        return None


def _resolve_keyword(group: Any, keyword_names: Iterable[str]) -> tuple[str, float] | None:
    has_keyword = getattr(group, "has_keyword", None)
    find_keyword = getattr(group, "find_keyword", None)
    for name in keyword_names:
        if has_keyword is None or find_keyword is None:
            try:
                keyword = group[name]  # type: ignore[index]
            except (KeyError, TypeError):
                continue
        else:
            if not has_keyword(name):
                continue
            keyword = find_keyword(name)
        value = _coerce_keyword_value(keyword)
        if value is not None:
            return name, value
    return None


def read_solar_geometry_from_cube(
    cube: Any,
    *,
    group_names: Iterable[str] = DEFAULT_INSTRUMENT_GROUP_NAMES,
    elevation_keywords: Iterable[str] = DEFAULT_SOLAR_ELEVATION_KEYWORDS,
    azimuth_keywords: Iterable[str] = DEFAULT_SOLAR_AZIMUTH_KEYWORDS,
) -> SolarGeometry:
    """Extract solar elevation/azimuth from an open ISIS cube using fallback keys.

    Mission-specific labels differ in keyword names, so this helper accepts an
    ordered fallback list per field. Raises :class:`SolarGeometryFieldMissing`
    when neither field could be resolved in any of the candidate groups.
    """

    has_group = getattr(cube, "has_group", None)
    group_getter = getattr(cube, "group", None)
    if has_group is None or group_getter is None:
        raise SolarGeometryFieldMissing(
            "cube object does not expose has_group/group; cannot read solar geometry."
        )

    resolved_elevation: tuple[str, float] | None = None
    resolved_azimuth: tuple[str, float] | None = None
    resolved_group_name: str | None = None
    for candidate_group_name in group_names:
        if not has_group(candidate_group_name):
            continue
        group = group_getter(candidate_group_name)
        if resolved_elevation is None:
            resolved_elevation = _resolve_keyword(group, elevation_keywords)
            if resolved_elevation is not None:
                resolved_group_name = candidate_group_name
        if resolved_azimuth is None:
            resolved_azimuth = _resolve_keyword(group, azimuth_keywords)
            if resolved_azimuth is not None and resolved_group_name is None:
                resolved_group_name = candidate_group_name
        if resolved_elevation is not None and resolved_azimuth is not None:
            break

    if resolved_elevation is None and resolved_azimuth is None:
        raise SolarGeometryFieldMissing(
            "Could not resolve solar elevation or azimuth from any of the candidate groups: "
            f"{tuple(group_names)!r}."
        )

    return SolarGeometry(
        solar_elevation_degrees=None if resolved_elevation is None else resolved_elevation[1],
        solar_azimuth_degrees=None if resolved_azimuth is None else resolved_azimuth[1],
        source_group_name=resolved_group_name,
        elevation_keyword=None if resolved_elevation is None else resolved_elevation[0],
        azimuth_keyword=None if resolved_azimuth is None else resolved_azimuth[0],
    )


def azimuth_difference_degrees(left_degrees: float, right_degrees: float) -> float:
    """Return the smallest absolute difference between two azimuths in degrees.

    Handles the 360° wrap so an angular distance of 350° vs 10° resolves to 20°.
    """

    raw = abs(float(left_degrees) - float(right_degrees)) % 360.0
    if raw > 180.0:
        raw = 360.0 - raw
    return float(raw)


def compute_lighting_difference(
    left: SolarGeometry,
    right: SolarGeometry,
    *,
    elevation_weight: float = DEFAULT_ELEVATION_WEIGHT,
    azimuth_weight: float = DEFAULT_AZIMUTH_WEIGHT,
    elevation_normalizer_degrees: float = DEFAULT_ELEVATION_NORMALIZER_DEGREES,
    azimuth_normalizer_degrees: float = DEFAULT_AZIMUTH_NORMALIZER_DEGREES,
) -> LightingDifferenceSummary:
    """Compute the pair-level lighting-difference score from two solar geometries."""

    if elevation_weight < 0.0 or azimuth_weight < 0.0:
        raise ValueError("weights must be non-negative.")
    if elevation_normalizer_degrees <= 0.0:
        raise ValueError("elevation_normalizer_degrees must be positive.")
    if azimuth_normalizer_degrees <= 0.0:
        raise ValueError("azimuth_normalizer_degrees must be positive.")

    left_elev = _finite_float(left.solar_elevation_degrees)
    right_elev = _finite_float(right.solar_elevation_degrees)
    left_az = _finite_float(left.solar_azimuth_degrees)
    right_az = _finite_float(right.solar_azimuth_degrees)

    elevation_diff: float | None = None
    if left_elev is not None and right_elev is not None:
        elevation_diff = abs(left_elev - right_elev)

    azimuth_diff: float | None = None
    if left_az is not None and right_az is not None:
        azimuth_diff = azimuth_difference_degrees(left_az, right_az)

    normalized_elevation = (
        None if elevation_diff is None else _clamp(elevation_diff / float(elevation_normalizer_degrees))
    )
    normalized_azimuth = (
        None if azimuth_diff is None else _clamp(azimuth_diff / float(azimuth_normalizer_degrees))
    )

    components: list[tuple[float, float]] = []
    if normalized_elevation is not None:
        components.append((elevation_weight, normalized_elevation))
    if normalized_azimuth is not None:
        components.append((azimuth_weight, normalized_azimuth))

    if not components:
        score: float | None = None
        reason = "both elevation and azimuth differences are unavailable"
    else:
        total_weight = sum(weight for weight, _ in components)
        if total_weight <= 0.0:
            score = None
            reason = "all weights are zero; lighting-difference score cannot be computed"
        else:
            score = _clamp(
                sum(weight * value for weight, value in components) / total_weight
            )
            if normalized_elevation is None:
                reason = "elevation difference unavailable; using azimuth-only weighting"
            elif normalized_azimuth is None:
                reason = "azimuth difference unavailable; using elevation-only weighting"
            else:
                reason = "weighted sum of normalized elevation and azimuth differences"

    return LightingDifferenceSummary(
        left_solar_geometry=left,
        right_solar_geometry=right,
        elevation_difference_degrees=elevation_diff,
        azimuth_difference_degrees=azimuth_diff,
        normalized_elevation_difference=normalized_elevation,
        normalized_azimuth_difference=normalized_azimuth,
        lighting_difference_score=score,
        elevation_weight=float(elevation_weight),
        azimuth_weight=float(azimuth_weight),
        reason=reason,
    )


def lighting_summary_to_diagnostic_dict(summary: LightingDifferenceSummary) -> dict[str, Any]:
    """Return a JSON-serializable diagnostic view of a lighting-difference summary."""

    return asdict(summary)


__all__ = [
    "DEFAULT_AZIMUTH_NORMALIZER_DEGREES",
    "DEFAULT_AZIMUTH_WEIGHT",
    "DEFAULT_ELEVATION_NORMALIZER_DEGREES",
    "DEFAULT_ELEVATION_WEIGHT",
    "DEFAULT_INSTRUMENT_GROUP_NAMES",
    "DEFAULT_SOLAR_AZIMUTH_KEYWORDS",
    "DEFAULT_SOLAR_ELEVATION_KEYWORDS",
    "LightingDifferenceSummary",
    "SolarGeometry",
    "SolarGeometryFieldMissing",
    "azimuth_difference_degrees",
    "compute_lighting_difference",
    "lighting_summary_to_diagnostic_dict",
    "read_solar_geometry_from_cube",
]
