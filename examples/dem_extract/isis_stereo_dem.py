"""Command line interface for extracting a DEM from synchronized `.key` files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dem_extract.cube_writer import write_radius_cube
from dem_extract.grid import GridSpec, rasterize_points
from dem_extract.key_pairs import load_key_point_pairs
from dem_extract.runtime import (
    build_summary,
    import_isis_pybind,
    write_point_cloud_csvish,
    write_point_cloud_jsonl,
    write_quality_summary_json,
    write_summary_json,
)
from dem_extract.triangulation import FilterOptions, triangulate_pairs


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    from_key = subparsers.add_parser("from-key", help="extract a DEM from synchronized left/right .key files")
    from_key.add_argument("left_cube")
    from_key.add_argument("right_cube")
    from_key.add_argument("left_key")
    from_key.add_argument("right_key")
    from_key.add_argument("map_template_cube")
    from_key.add_argument("output_dem_cube")
    from_key.add_argument("--point-cloud-output")
    from_key.add_argument("--summary-output")
    from_key.add_argument("--quality-prefix")
    from_key.add_argument("--max-error-m", type=float)
    from_key.add_argument("--min-sepang-deg", type=float)
    from_key.add_argument("--min-radius-m", type=float)
    from_key.add_argument("--max-radius-m", type=float)
    from_key.add_argument("--aggregation", choices=("median", "mean", "min-error"), default="median")
    from_key.add_argument("--nodata-value", type=float, default=-9999.0)
    from_key.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR"), default="INFO")
    return parser


def compact_stdout_payload(
    *,
    output_dem_cube: str,
    point_cloud_output: str | None,
    summary_output: str | None,
    summary: dict[str, object],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": "ok",
        "output_dem_cube": output_dem_cube,
        "point_cloud_output": point_cloud_output,
        "summary_output": summary_output,
    }
    for key in (
        "input_point_count",
        "success_count",
        "failed_set_image_count",
        "failed_elevation_count",
        "filtered_error_count",
        "filtered_sepang_count",
        "filtered_radius_count",
        "rasterized_point_count",
        "filled_cell_count",
    ):
        if key in summary:
            payload[key] = summary[key]
    return payload


def _open_cube(ip, path: str, access: str = "r"):
    cube = ip.Cube()
    cube.open(path, access)
    return cube


def _close_cube(cube) -> None:
    if cube is not None and hasattr(cube, "close"):
        cube.close()


def _template_grid_spec(template_cube, nodata_value: float) -> GridSpec:
    return GridSpec(samples=int(template_cube.sample_count()), lines=int(template_cube.line_count()), nodata_value=nodata_value)


def run_from_key(args: argparse.Namespace) -> dict[str, object]:
    ip = import_isis_pybind()
    left_cube = right_cube = template_cube = None
    try:
        left_cube = _open_cube(ip, args.left_cube)
        right_cube = _open_cube(ip, args.right_cube)
        template_cube = _open_cube(ip, args.map_template_cube)
        pairs = load_key_point_pairs(args.left_key, args.right_key, left_cube=left_cube, right_cube=right_cube)
        records, counters = triangulate_pairs(
            pairs,
            left_cube,
            right_cube,
            ip,
            FilterOptions(
                max_error_m=args.max_error_m,
                min_sepang_deg=args.min_sepang_deg,
                min_radius_m=args.min_radius_m,
                max_radius_m=args.max_radius_m,
            ),
        )
        raster = rasterize_points(records, template_cube, _template_grid_spec(template_cube, args.nodata_value), aggregation=args.aggregation)
        if counters.get("success_count", 0) == 0 or raster.filled_cell_count == 0:
            raise RuntimeError("No triangulated DEM points survived filtering and rasterization.")

        write_radius_cube(ip, template_cube, args.output_dem_cube, raster)
        if args.point_cloud_output:
            if Path(args.point_cloud_output).suffix.lower() == ".csv":
                write_point_cloud_csvish(args.point_cloud_output, records)
            else:
                write_point_cloud_jsonl(args.point_cloud_output, records)
        if args.quality_prefix:
            write_quality_summary_json(f"{args.quality_prefix}.summary.json", raster)

        summary = build_summary(
            input_left_cube=args.left_cube,
            input_right_cube=args.right_cube,
            input_left_key=args.left_key,
            input_right_key=args.right_key,
            map_template=args.map_template_cube,
            output_dem_cube=args.output_dem_cube,
            input_point_count=len(pairs),
            triangulation_counters=counters,
            rasterized_point_count=raster.rasterized_point_count,
            filled_cell_count=raster.filled_cell_count,
            max_error_m=args.max_error_m,
            min_sepang_deg=args.min_sepang_deg,
            nodata_value=args.nodata_value,
            aggregation=args.aggregation,
        )
        if args.summary_output:
            write_summary_json(args.summary_output, summary)
        return compact_stdout_payload(
            output_dem_cube=args.output_dem_cube,
            point_cloud_output=args.point_cloud_output,
            summary_output=args.summary_output,
            summary=summary,
        )
    finally:
        _close_cube(template_cube)
        _close_cube(right_cube)
        _close_cube(left_cube)


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    if args.command == "from-key":
        print(json.dumps(run_from_key(args), sort_keys=True))
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
