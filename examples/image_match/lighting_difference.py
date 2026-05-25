"""Solar lighting-difference metrics for adaptive matcher routing.

Author: Geng Xun
Created: 2026-05-18
Updated: 2026-05-18  Geng Xun added cube-label solar geometry parsing with
    mission-aware keyword fallbacks, azimuth-wrap difference, and the initial
    normalized weighted-sum lighting-difference score.
Updated: 2026-05-19  Geng Xun added sampler-driven tile lighting summaries for
    tile-aligned diagnostics without requiring SPICE-heavy unit fixtures.

This first release intentionally limits itself to solar elevation and solar
azimuth read from the cube ``Instrument`` group; ``incidence``, ``emission``,
and ``phase`` angles are reserved for future expansion without changing the
public API.
"""

from __future__ import annotations

from collections.abc import Callable
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
SENSOR_MODEL_SOURCE_NAME = "SensorModelCenter"
SENSOR_MODEL_ELEVATION_KEYWORD = "90-IncidenceAngle"
SENSOR_MODEL_AZIMUTH_KEYWORD = "SunAzimuth"


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


@dataclass(frozen=True, slots=True)
class TileLightingSample:
    """Lighting geometry sample associated with one tile diagnostic point."""

    sample: float
    line: float
    incidence_degrees: float | None
    emission_degrees: float | None
    phase_degrees: float | None
    solar_azimuth_degrees: float | None
    solar_elevation_degrees: float | None
    valid: bool
    reason: str


@dataclass(frozen=True, slots=True)
class TileLightingSummary:
    """Aggregate tile-level lighting diagnostics."""

    tile_total_count: int
    tile_valid_count: int
    incidence_quantiles: dict[str, float | None]
    emission_quantiles: dict[str, float | None]
    phase_quantiles: dict[str, float | None]
    samples: tuple[TileLightingSample, ...]


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


def _read_label_solar_geometry_from_cube(
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

    candidate_group_names = tuple(group_names)
    has_group = getattr(cube, "has_group", None)
    group_getter = getattr(cube, "group", None)
    if has_group is None or group_getter is None:
        raise SolarGeometryFieldMissing(
            "cube object does not expose has_group/group; cannot read solar geometry."
        )

    resolved_elevation: tuple[str, float] | None = None
    resolved_azimuth: tuple[str, float] | None = None
    resolved_group_name: str | None = None
    for candidate_group_name in candidate_group_names:
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
            f"{candidate_group_names!r}."
        )

    return SolarGeometry(
        solar_elevation_degrees=None if resolved_elevation is None else resolved_elevation[1],
        solar_azimuth_degrees=None if resolved_azimuth is None else resolved_azimuth[1],
        source_group_name=resolved_group_name,
        elevation_keyword=None if resolved_elevation is None else resolved_elevation[0],
        azimuth_keyword=None if resolved_azimuth is None else resolved_azimuth[0],
    )


def _read_sensor_model_solar_geometry_from_cube(cube: Any) -> SolarGeometry:
    try:
        camera_getter = getattr(cube, "camera")
        sample_count_getter = getattr(cube, "sample_count")
        line_count_getter = getattr(cube, "line_count")
    except AttributeError as exc:
        raise SolarGeometryFieldMissing(
            f"sensor model error: cube object does not expose required sensor-model method: {exc}."
        ) from exc

    try:
        sample_count = _finite_float(sample_count_getter())
    except Exception as exc:
        raise SolarGeometryFieldMissing(
            f"sensor model error: could not read cube sample_count: {exc}."
        ) from exc
    if sample_count is None or sample_count <= 0.0:
        raise SolarGeometryFieldMissing(
            f"sensor model error: cube sample_count must be finite and positive; got {sample_count!r}."
        )

    try:
        line_count = _finite_float(line_count_getter())
    except Exception as exc:
        raise SolarGeometryFieldMissing(
            f"sensor model error: could not read cube line_count: {exc}."
        ) from exc
    if line_count is None or line_count <= 0.0:
        raise SolarGeometryFieldMissing(
            f"sensor model error: cube line_count must be finite and positive; got {line_count!r}."
        )

    center_sample = (sample_count + 1.0) / 2.0
    center_line = (line_count + 1.0) / 2.0

    try:
        camera = camera_getter()
    except Exception as exc:
        raise SolarGeometryFieldMissing(
            f"sensor model error: could not initialize cube camera: {exc}."
        ) from exc

    set_image = getattr(camera, "set_image", None)
    if set_image is None:
        raise SolarGeometryFieldMissing(
            "sensor model error: cube camera does not expose set_image."
        )

    try:
        if not set_image(center_sample, center_line):
            raise SolarGeometryFieldMissing(
                "sensor model error: camera.set_image returned false at cube center."
            )
    except SolarGeometryFieldMissing:
        raise
    except Exception as exc:
        raise SolarGeometryFieldMissing(
            f"sensor model error: camera.set_image failed at cube center: {exc}."
        ) from exc

    missing_reasons: list[str] = []

    resolved_azimuth: float | None = None
    sun_azimuth = getattr(camera, "sun_azimuth", None)
    if sun_azimuth is None:
        missing_reasons.append("camera does not expose sun_azimuth")
    else:
        try:
            resolved_azimuth = _finite_float(sun_azimuth())
        except Exception as exc:
            missing_reasons.append(f"sun_azimuth failed: {exc}")
        if resolved_azimuth is None:
            missing_reasons.append("sun_azimuth was missing or non-finite")

    resolved_elevation: float | None = None
    incidence_angle = getattr(camera, "incidence_angle", None)
    if incidence_angle is None:
        missing_reasons.append("camera does not expose incidence_angle")
    else:
        try:
            incidence = _finite_float(incidence_angle())
        except Exception as exc:
            missing_reasons.append(f"incidence_angle failed: {exc}")
            incidence = None
        if incidence is None:
            missing_reasons.append("incidence_angle was missing or non-finite")
        else:
            resolved_elevation = 90.0 - incidence

    if resolved_elevation is None and resolved_azimuth is None:
        raise SolarGeometryFieldMissing(
            "sensor model error: could not resolve solar elevation or azimuth from camera "
            f"at cube center: {'; '.join(missing_reasons)}."
        )

    return SolarGeometry(
        solar_elevation_degrees=resolved_elevation,
        solar_azimuth_degrees=resolved_azimuth,
        source_group_name=SENSOR_MODEL_SOURCE_NAME,
        elevation_keyword=None if resolved_elevation is None else SENSOR_MODEL_ELEVATION_KEYWORD,
        azimuth_keyword=None if resolved_azimuth is None else SENSOR_MODEL_AZIMUTH_KEYWORD,
    )


def read_solar_geometry_from_cube(
    cube: Any,
    *,
    group_names: Iterable[str] = DEFAULT_INSTRUMENT_GROUP_NAMES,
    elevation_keywords: Iterable[str] = DEFAULT_SOLAR_ELEVATION_KEYWORDS,
    azimuth_keywords: Iterable[str] = DEFAULT_SOLAR_AZIMUTH_KEYWORDS,
) -> SolarGeometry:
    """Extract solar elevation/azimuth from an open ISIS cube.

    Sensor-model geometry sampled at the cube center is preferred. Mission label
    keywords remain the fallback when the camera model cannot provide either
    elevation or azimuth.
    """

    try:
        return _read_sensor_model_solar_geometry_from_cube(cube)
    except SolarGeometryFieldMissing as sensor_error:
        try:
            return _read_label_solar_geometry_from_cube(
                cube,
                group_names=group_names,
                elevation_keywords=elevation_keywords,
                azimuth_keywords=azimuth_keywords,
            )
        except SolarGeometryFieldMissing as label_error:
            sensor_message = str(sensor_error)
            if not sensor_message.startswith("sensor model error:"):
                sensor_message = f"sensor model error: {sensor_message}"
            raise SolarGeometryFieldMissing(
                f"{sensor_message}; label fallback error: {label_error}"
            ) from label_error


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


def _interpolated_quantile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("values must not be empty.")
    if len(values) == 1:
        return float(values[0])
    sorted_values = sorted(values)
    clamped = _clamp(quantile)
    position = clamped * (len(sorted_values) - 1)
    lower_index = int(math.floor(position))
    upper_index = int(math.ceil(position))
    if lower_index == upper_index:
        return float(sorted_values[lower_index])
    fraction = position - lower_index
    return float(sorted_values[lower_index] + (sorted_values[upper_index] - sorted_values[lower_index]) * fraction)


def _quantile_dict(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"p10": None, "p50": None, "p90": None, "max": None}
    return {
        "p10": _interpolated_quantile(values, 0.10),
        "p50": _interpolated_quantile(values, 0.50),
        "p90": _interpolated_quantile(values, 0.90),
        "max": max(values),
    }


def _tile_window_bounds(tile_window: Any) -> tuple[float, float, float, float]:
    if hasattr(tile_window, "start_x") and hasattr(tile_window, "start_y"):
        return (
            float(tile_window.start_x),
            float(tile_window.start_y),
            float(tile_window.width),
            float(tile_window.height),
        )
    try:
        start_x, start_y, width, height = tile_window
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "tile windows must be TileWindow-like objects or (start_x, start_y, width, height) tuples."
        ) from exc
    return float(start_x), float(start_y), float(width), float(height)


def sample_lighting_at_tile_center(
    point_sampler: Callable[[float, float], TileLightingSample],
) -> Callable[[Any], TileLightingSample]:
    """Adapt a point lighting sampler to sample each tile at its center."""

    def sample_tile(tile_window: Any) -> TileLightingSample:
        start_x, start_y, width, height = _tile_window_bounds(tile_window)
        return point_sampler(start_x + width / 2.0, start_y + height / 2.0)

    return sample_tile


def compute_tile_lighting_summary(
    *,
    tile_windows: Iterable[Any],
    sample_lighting: Callable[[Any], TileLightingSample],
) -> TileLightingSummary:
    """Sample lighting for tile windows and aggregate valid angle quantiles."""

    samples = tuple(sample_lighting(tile_window) for tile_window in tile_windows)
    valid_samples = [sample for sample in samples if sample.valid]

    def collect(field_name: str) -> list[float]:
        values: list[float] = []
        for sample in valid_samples:
            value = _finite_float(getattr(sample, field_name))
            if value is not None:
                values.append(value)
        return values

    return TileLightingSummary(
        tile_total_count=len(samples),
        tile_valid_count=len(valid_samples),
        incidence_quantiles=_quantile_dict(collect("incidence_degrees")),
        emission_quantiles=_quantile_dict(collect("emission_degrees")),
        phase_quantiles=_quantile_dict(collect("phase_degrees")),
        samples=samples,
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
    "SENSOR_MODEL_AZIMUTH_KEYWORD",
    "SENSOR_MODEL_ELEVATION_KEYWORD",
    "SENSOR_MODEL_SOURCE_NAME",
    "SolarGeometry",
    "SolarGeometryFieldMissing",
    "TileLightingSample",
    "TileLightingSummary",
    "azimuth_difference_degrees",
    "compute_lighting_difference",
    "compute_tile_lighting_summary",
    "lighting_summary_to_diagnostic_dict",
    "read_solar_geometry_from_cube",
    "sample_lighting_at_tile_center",
]
