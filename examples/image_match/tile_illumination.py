"""Tile-level illumination data models for adaptive matcher routing."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Any, Iterable, Mapping


def _finite_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    resolved = float(value)
    return resolved if math.isfinite(resolved) else None


def angular_difference_degrees(left: float | None, right: float | None) -> float | None:
    left_value = _finite_or_none(left)
    right_value = _finite_or_none(right)
    if left_value is None or right_value is None:
        return None
    return abs((left_value - right_value + 180.0) % 360.0 - 180.0)


def illumination_difference_score(
    *,
    azimuth_difference_degrees: float | None,
    incidence_difference_degrees: float | None,
    elevation_difference_degrees: float | None,
) -> float | None:
    terms: list[float] = []
    azimuth = _finite_or_none(azimuth_difference_degrees)
    incidence = _finite_or_none(incidence_difference_degrees)
    elevation = _finite_or_none(elevation_difference_degrees)
    if azimuth is not None:
        terms.append(min(azimuth / 180.0, 1.0))
    if incidence is not None:
        terms.append(min(abs(incidence) / 90.0, 1.0))
    if elevation is not None:
        terms.append(min(abs(elevation) / 90.0, 1.0))
    if not terms:
        return None
    return max(0.0, min(1.0, sum(terms) / len(terms)))


@dataclass(frozen=True, slots=True)
class TileWindowMetadata:
    start_x: int
    start_y: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class RepresentativePoint:
    status: str
    selection_reason: str
    local_x_0_based: int | None
    local_y_0_based: int | None
    dom_sample_1_based: float | None
    dom_line_1_based: float | None
    pixel_available: bool
    radiometric_valid_for_matching: bool | None
    source_projectable: bool
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class TileIlluminationSample:
    side: str
    dom_path: str
    dom_source_cube: str
    upstream_source_cube: str | None
    tile_index: int
    tile_window_0_based: TileWindowMetadata
    representative_point: RepresentativePoint
    latitude: float | None
    longitude: float | None
    source_sample_1_based: float | None
    source_line_1_based: float | None
    sun_azimuth_degrees: float | None
    incidence_angle_degrees: float | None
    solar_elevation_degrees: float | None

    @classmethod
    def failed(
        cls,
        *,
        side: str,
        dom_path: str,
        dom_source_cube: str,
        upstream_source_cube: str | None,
        tile_index: int,
        tile_window_0_based: TileWindowMetadata,
        representative_point: RepresentativePoint,
    ) -> "TileIlluminationSample":
        return cls(
            side=side,
            dom_path=dom_path,
            dom_source_cube=dom_source_cube,
            upstream_source_cube=upstream_source_cube,
            tile_index=tile_index,
            tile_window_0_based=tile_window_0_based,
            representative_point=representative_point,
            latitude=None,
            longitude=None,
            source_sample_1_based=None,
            source_line_1_based=None,
            sun_azimuth_degrees=None,
            incidence_angle_degrees=None,
            solar_elevation_degrees=None,
        )


@dataclass(frozen=True, slots=True)
class TileIlluminationPair:
    tile_index: int
    status: str
    left: TileIlluminationSample
    right: TileIlluminationSample
    azimuth_difference_degrees: float | None
    incidence_difference_degrees: float | None
    elevation_difference_degrees: float | None
    illumination_difference_score: float | None

    @classmethod
    def from_samples(
        cls,
        *,
        tile_index: int,
        left: TileIlluminationSample,
        right: TileIlluminationSample,
    ) -> "TileIlluminationPair":
        left_ok = bool(left.representative_point.source_projectable)
        right_ok = bool(right.representative_point.source_projectable)
        if left_ok and right_ok:
            status = "ok"
        elif left_ok:
            status = "right_failed"
        elif right_ok:
            status = "left_failed"
        else:
            status = "both_failed"
        azimuth = angular_difference_degrees(left.sun_azimuth_degrees, right.sun_azimuth_degrees)
        incidence = _abs_difference(left.incidence_angle_degrees, right.incidence_angle_degrees)
        elevation = _abs_difference(left.solar_elevation_degrees, right.solar_elevation_degrees)
        score = illumination_difference_score(
            azimuth_difference_degrees=azimuth,
            incidence_difference_degrees=incidence,
            elevation_difference_degrees=elevation,
        )
        return cls(
            tile_index=tile_index,
            status=status,
            left=left,
            right=right,
            azimuth_difference_degrees=azimuth,
            incidence_difference_degrees=incidence,
            elevation_difference_degrees=elevation,
            illumination_difference_score=score,
        )


def _abs_difference(left: float | None, right: float | None) -> float | None:
    left_value = _finite_or_none(left)
    right_value = _finite_or_none(right)
    if left_value is None or right_value is None:
        return None
    return abs(left_value - right_value)


def load_dom_source_metadata_csv(csv_path: str | Path) -> dict[str, dict[str, str | None]]:
    lookup: dict[str, dict[str, str | None]] = {}
    ambiguous_basenames: set[str] = set()
    path = Path(csv_path)
    if not path.exists():
        return lookup

    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            dom_path = (row.get("dom_cube") or "").strip()
            if not dom_path:
                continue
            selected_source_cube = (row.get("echo_cal_cube") or "").strip()
            upstream_source_cube = (row.get("source_echo_cal_cube") or "").strip() or None
            metadata = {
                "dom_path": dom_path,
                "dom_source_cube": selected_source_cube,
                "upstream_source_cube": upstream_source_cube,
                "dom_source_kind": _dom_source_kind(selected_source_cube),
            }
            lookup[dom_path] = metadata
            dom_basename = Path(dom_path).name
            if dom_basename in ambiguous_basenames:
                continue
            existing_basename_metadata = lookup.get(dom_basename)
            if existing_basename_metadata is not None and existing_basename_metadata.get("dom_path") != dom_path:
                ambiguous_basenames.add(dom_basename)
                lookup.pop(dom_basename, None)
                continue
            lookup[dom_basename] = metadata
    return lookup


def resolve_dom_source_metadata(
    dom_path: str | Path,
    lookup: Mapping[str, Mapping[str, str | None]] | None,
) -> dict[str, str | None]:
    resolved_dom_path = str(dom_path)
    candidates = (resolved_dom_path, Path(resolved_dom_path).name)
    if lookup is not None:
        for candidate in candidates:
            metadata = lookup.get(candidate)
            if metadata is not None:
                return {
                    "dom_path": metadata.get("dom_path") or resolved_dom_path,
                    "dom_source_cube": metadata.get("dom_source_cube") or "",
                    "upstream_source_cube": metadata.get("upstream_source_cube"),
                    "dom_source_kind": metadata.get("dom_source_kind") or "unknown",
                }
    return _unknown_dom_source_metadata(resolved_dom_path)


def _unknown_dom_source_metadata(dom_path: str) -> dict[str, str | None]:
    return {
        "dom_path": dom_path,
        "dom_source_cube": "",
        "upstream_source_cube": None,
        "dom_source_kind": "unknown",
    }


def _dom_source_kind(source_cube: str | None) -> str:
    if source_cube is not None and Path(source_cube).name.startswith("REDUCED_"):
        return "reduced"
    return "unknown"


def illumination_pair_to_payload(pair: TileIlluminationPair) -> dict[str, Any]:
    return asdict(pair)


def summarize_tile_illumination_pairs(pairs: Iterable[TileIlluminationPair]) -> dict[str, Any]:
    resolved_pairs = tuple(pairs)
    skip_reasons: dict[str, int] = {}
    projectable = 0
    scores: list[float] = []
    for pair in resolved_pairs:
        if pair.status == "ok":
            projectable += 1
        else:
            skip_reasons[pair.status] = skip_reasons.get(pair.status, 0) + 1
        if pair.illumination_difference_score is not None:
            scores.append(float(pair.illumination_difference_score))
    return {
        "illumination_granularity": "tile",
        "tile_count": len(resolved_pairs),
        "projectable_tile_count": projectable,
        "skipped_tile_count": len(resolved_pairs) - projectable,
        "skip_reasons": skip_reasons,
        "illumination_difference_score_summary": _summary(scores),
    }


def _summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {
        "count": len(values),
        "min": min(values),
        "mean": sum(values) / len(values),
        "max": max(values),
    }
