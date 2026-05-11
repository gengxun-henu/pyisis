"""DEM grid aggregation helpers.

Author: Geng Xun
Created: 2026-05-10
Last Modified: 2026-05-10
Updated: 2026-05-10  Geng Xun added raster aggregation helpers for sparse DEM point grids.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable

from .triangulation import TriangulatedPoint


@dataclass(frozen=True, slots=True)
class GridSpec:
    samples: int
    lines: int
    nodata_value: float = -9999.0


@dataclass(frozen=True, slots=True)
class RasterResult:
    values: list[list[float]]
    rasterized_point_count: int
    filled_cell_count: int
    nodata_value: float = -9999.0


def _record_value(record: TriangulatedPoint, value_field: str) -> float | None:
    return getattr(record, value_field)


def aggregate_cell_values(records: Iterable[TriangulatedPoint], aggregation: str, *, value_field: str = "radius_m") -> float:
    record_list = list(records)
    if not record_list:
        raise ValueError("Cannot aggregate an empty cell.")
    if aggregation == "median":
        return float(median(value for record in record_list if (value := _record_value(record, value_field)) is not None))
    if aggregation == "mean":
        values = [value for record in record_list if (value := _record_value(record, value_field)) is not None]
        return float(sum(values) / len(values))
    if aggregation == "min-error":
        best = min(record_list, key=lambda record: float("inf") if record.intersection_error_m is None else record.intersection_error_m)
        best_value = _record_value(best, value_field)
        if best_value is None:
            raise ValueError(f"Best min-error record has no {value_field} value.")
        return float(best_value)
    raise ValueError(f"Unsupported aggregation: {aggregation}")


def _world_to_cell(world_x: float, world_y: float, spec: GridSpec) -> tuple[int, int] | None:
    sample = int(round(world_x)) - 1
    line = int(round(world_y)) - 1
    if not (0 <= sample < spec.samples and 0 <= line < spec.lines):
        return None
    return line, sample


def rasterize_points(
    records: Iterable[TriangulatedPoint],
    template_cube,
    spec: GridSpec,
    *,
    aggregation: str,
    value_field: str = "radius_m",
) -> RasterResult:
    projection = template_cube.projection()
    cells: dict[tuple[int, int], list[TriangulatedPoint]] = {}
    rasterized_count = 0
    for record in records:
        if record.status != "success" or record.latitude_deg is None or record.longitude_deg is None:
            continue
        if _record_value(record, value_field) is None:
            continue
        if not projection.set_universal_ground(record.latitude_deg, record.longitude_deg):
            continue
        cell = _world_to_cell(float(projection.world_x()), float(projection.world_y()), spec)
        if cell is None:
            continue
        cells.setdefault(cell, []).append(record)
        rasterized_count += 1

    values = [[spec.nodata_value for _ in range(spec.samples)] for _ in range(spec.lines)]
    for (line, sample), cell_records in cells.items():
        values[line][sample] = aggregate_cell_values(cell_records, aggregation, value_field=value_field)
    return RasterResult(values, rasterized_count, len(cells), spec.nodata_value)
