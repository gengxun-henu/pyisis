"""Triangulate synchronized key-point pairs with ISIS Stereo.

Author: Geng Xun
Created: 2026-05-10
Last Modified: 2026-05-10
Updated: 2026-05-10  Geng Xun added ISIS Stereo triangulation and quality filtering helpers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Iterable

from .key_pairs import KeyPointPair


@dataclass(frozen=True, slots=True)
class FilterOptions:
    max_error_m: float | None = None
    min_sepang_deg: float | None = None
    min_radius_m: float | None = None
    max_radius_m: float | None = None


@dataclass(frozen=True, slots=True)
class TriangulatedPoint:
    index: int
    left_sample: float
    left_line: float
    right_sample: float
    right_line: float
    status: str
    reason: str
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    radius_m: float | None = None
    sepang_deg: float | None = None
    intersection_error_m: float | None = None
    x_km: float | None = None
    y_km: float | None = None
    z_km: float | None = None
    height_m: float | None = None
    datum_radius_m: float | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def apply_datum_radius(records: Iterable[TriangulatedPoint], datum_radius_m: float) -> list[TriangulatedPoint]:
    adjusted_records: list[TriangulatedPoint] = []
    for record in records:
        height_m = None if record.radius_m is None else float(record.radius_m - datum_radius_m)
        adjusted_records.append(replace(record, height_m=height_m, datum_radius_m=float(datum_radius_m)))
    return adjusted_records


def _base_record(pair: KeyPointPair, status: str, reason: str, **geometry: float | None) -> TriangulatedPoint:
    return TriangulatedPoint(
        pair.index,
        pair.left_sample,
        pair.left_line,
        pair.right_sample,
        pair.right_line,
        status,
        reason,
        **geometry,
    )


def _filter_reason(radius_m: float, sepang_deg: float, error_m: float, filters: FilterOptions) -> str | None:
    if filters.max_error_m is not None and error_m > filters.max_error_m:
        return "filtered_error"
    if filters.min_sepang_deg is not None and sepang_deg < filters.min_sepang_deg:
        return "filtered_sepang"
    if filters.min_radius_m is not None and radius_m < filters.min_radius_m:
        return "filtered_radius"
    if filters.max_radius_m is not None and radius_m > filters.max_radius_m:
        return "filtered_radius"
    return None


def _initial_counters(input_point_count: int) -> dict[str, int]:
    return {
        "input_point_count": input_point_count,
        "success_count": 0,
        "failed_set_image_count": 0,
        "failed_elevation_count": 0,
        "filtered_error_count": 0,
        "filtered_sepang_count": 0,
        "filtered_radius_count": 0,
    }


def triangulate_pairs(
    pairs: Iterable[KeyPointPair],
    left_cube,
    right_cube,
    ip,
    filters: FilterOptions,
) -> tuple[list[TriangulatedPoint], dict[str, int]]:
    pair_list = list(pairs)
    counters = _initial_counters(len(pair_list))
    left_camera = left_cube.camera()
    right_camera = right_cube.camera()
    records: list[TriangulatedPoint] = []
    for pair in pair_list:
        if not left_camera.set_image(pair.left_sample, pair.left_line):
            counters["failed_set_image_count"] += 1
            records.append(_base_record(pair, "failed", "left_set_image"))
            continue
        if not right_camera.set_image(pair.right_sample, pair.right_line):
            counters["failed_set_image_count"] += 1
            records.append(_base_record(pair, "failed", "right_set_image"))
            continue
        try:
            success, radius_m, latitude_deg, longitude_deg, sepang_deg, error_m = ip.Stereo.elevation(left_camera, right_camera)
        except Exception as exc:
            counters["failed_elevation_count"] += 1
            records.append(_base_record(pair, "failed", f"elevation:{exc.__class__.__name__}"))
            continue
        if not success:
            counters["failed_elevation_count"] += 1
            records.append(_base_record(pair, "failed", "elevation_false"))
            continue
        x_km, y_km, z_km = ip.Stereo.spherical(latitude_deg, longitude_deg, radius_m)
        reason = _filter_reason(radius_m, sepang_deg, error_m, filters)
        if reason is not None:
            counters[f"{reason}_count"] += 1
            status = "filtered"
        else:
            counters["success_count"] += 1
            reason = ""
            status = "success"
        records.append(
            _base_record(
                pair,
                status,
                reason,
                latitude_deg=latitude_deg,
                longitude_deg=longitude_deg,
                radius_m=radius_m,
                sepang_deg=sepang_deg,
                intersection_error_m=error_m,
                x_km=x_km,
                y_km=y_km,
                z_km=z_km,
            )
        )
    return records, counters
