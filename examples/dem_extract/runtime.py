"""Runtime and sidecar helpers for the DEM extraction example.

Author: Geng Xun
Created: 2026-05-10
Last Modified: 2026-05-10
Updated: 2026-05-10  Geng Xun added runtime bootstrap and sidecar writers for sparse DEM extraction.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILD_PYTHON_DIR = PROJECT_ROOT / "build" / "python"
WORKSPACE_ISISDATA_MOCKUP = PROJECT_ROOT / "tests" / "data" / "isisdata" / "mockup"


def _has_leap_second_kernels(data_root: Path) -> bool:
    lsk_dir = data_root / "base" / "kernels" / "lsk"
    return lsk_dir.exists() and any(lsk_dir.glob("naif*.tls"))


def bootstrap_runtime_environment() -> None:
    """Make the standalone example runnable from the repository checkout."""
    if str(BUILD_PYTHON_DIR) not in sys.path and BUILD_PYTHON_DIR.exists():
        sys.path.insert(0, str(BUILD_PYTHON_DIR))

    configured_isisdata = os.environ.get("ISISDATA")
    if configured_isisdata and _has_leap_second_kernels(Path(configured_isisdata)):
        return
    if _has_leap_second_kernels(WORKSPACE_ISISDATA_MOCKUP):
        os.environ["ISISDATA"] = str(WORKSPACE_ISISDATA_MOCKUP)


def import_isis_pybind():
    """Import `isis_pybind` after applying the repository runtime bootstrap."""
    bootstrap_runtime_environment()
    import isis_pybind as ip

    return ip


def write_summary_json(output_path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _record_to_dict(record) -> dict[str, Any]:
    if hasattr(record, "to_dict"):
        return dict(record.to_dict())
    if is_dataclass(record):
        return asdict(record)
    return dict(record)


def write_point_cloud_jsonl(output_path: str | Path, records: Iterable[object]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(_record_to_dict(record), sort_keys=True) + "\n")


def write_point_cloud_csvish(output_path: str | Path, records: Iterable[object]) -> None:
    import csv

    fieldnames = [
        "index",
        "left_sample",
        "left_line",
        "right_sample",
        "right_line",
        "status",
        "reason",
        "latitude_deg",
        "longitude_deg",
        "radius_m",
        "height_m",
        "datum_radius_m",
        "sepang_deg",
        "intersection_error_m",
        "x_km",
        "y_km",
        "z_km",
    ]
    rows = [_record_to_dict(record) for record in records]
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_quality_summary_json(output_path: str | Path, raster) -> None:
    payload = {
        "quality_product_type": "summary",
        "rasterized_point_count": raster.rasterized_point_count,
        "filled_cell_count": raster.filled_cell_count,
        "empty_cell_count": sum(1 for row in raster.values for value in row if value == raster.nodata_value),
    }
    write_summary_json(output_path, payload)


def build_summary(
    *,
    input_left_cube: str,
    input_right_cube: str,
    input_left_key: str,
    input_right_key: str,
    map_template: str,
    output_dem_cube: str,
    input_point_count: int,
    triangulation_counters: dict[str, int],
    rasterized_point_count: int,
    filled_cell_count: int,
    value_type: str,
    datum_radius_m: float | None,
    refinement: dict[str, object] | None,
    max_error_m: float | None,
    min_sepang_deg: float | None,
    nodata_value: float,
    aggregation: str,
) -> dict[str, object]:
    summary: dict[str, object] = {
        "input_left_cube": input_left_cube,
        "input_right_cube": input_right_cube,
        "input_left_key": input_left_key,
        "input_right_key": input_right_key,
        "map_template": map_template,
        "output_dem_cube": output_dem_cube,
        "input_point_count": input_point_count,
        "rasterized_point_count": rasterized_point_count,
        "filled_cell_count": filled_cell_count,
        "value_type": value_type,
        "datum_radius_m": datum_radius_m,
        "nodata_value": nodata_value,
        "max_error_m": max_error_m,
        "min_sepang_deg": min_sepang_deg,
        "aggregation": aggregation,
    }
    if refinement is not None:
        summary["refinement"] = refinement
    for key in (
        "success_count",
        "failed_set_image_count",
        "failed_elevation_count",
        "filtered_error_count",
        "filtered_sepang_count",
        "filtered_radius_count",
    ):
        summary[key] = int(triangulation_counters.get(key, 0))
    return summary
