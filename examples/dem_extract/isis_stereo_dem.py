"""Command line interface for extracting a DEM from synchronized `.key` files.

Author: Geng Xun
Created: 2026-05-10
Last Modified: 2026-05-10
Updated: 2026-05-10  Geng Xun added the from-key sparse stereo DEM extraction command.
Updated: 2026-05-10  Geng Xun added optional `.key` refinement stages before DEM triangulation.
Updated: 2026-05-10  Geng Xun added the from-dense-ncc dense disparity DEM command.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controlnet_construct.keypoints import read_key_file, write_key_file
from dem_extract.cube_writer import write_radius_cube
from dem_extract.dense_ncc import (
    NCCMatchOptions,
    count_disparity_stats,
    dense_ncc_match,
    write_disparity_cube,
)
from dem_extract.dense_triangulation import dense_triangulate_from_disparity
from dem_extract.disparity_model import fit_disparity_model
from dem_extract.grid import GridSpec, rasterize_points
from dem_extract.key_pairs import load_key_point_pairs, load_key_point_pairs_from_key_files
from dem_extract.refinement import KeyRefinementOptions, normalize_refinement_stages, refine_keypoint_file_pair
from dem_extract.runtime import (
    build_dense_ncc_summary,
    build_summary,
    import_isis_pybind,
    write_point_cloud_csvish,
    write_point_cloud_jsonl,
    write_quality_summary_json,
    write_summary_json,
)
from dem_extract.triangulation import FilterOptions, apply_datum_radius, triangulate_pairs


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
    from_key.add_argument("--value-type", choices=("radius_m", "height_m"), default="radius_m")
    from_key.add_argument("--datum-radius-m", type=float)
    from_key.add_argument(
        "--refine-stage",
        action="append",
        choices=("maximum-correlation", "gruen"),
        default=[],
        help="Optional `.key` refinement stage to run before triangulation. Repeat to chain stages.",
    )
    from_key.add_argument("--refined-left-key-output")
    from_key.add_argument("--refined-right-key-output")
    from_key.add_argument("--refinement-summary-output")
    from_key.add_argument("--nodata-value", type=float, default=-9999.0)
    from_key.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR"), default="INFO")

    from_dense_ncc = subparsers.add_parser(
        "from-dense-ncc",
        help="dense per-pixel NCC matching seeded by sparse KEY priors, then extract DEM",
    )
    from_dense_ncc.add_argument("left_cube")
    from_dense_ncc.add_argument("right_cube")
    from_dense_ncc.add_argument("left_key")
    from_dense_ncc.add_argument("right_key")
    from_dense_ncc.add_argument("output_dem_cube")
    proj_group = from_dense_ncc.add_mutually_exclusive_group(required=True)
    proj_group.add_argument("--map-template-cube", help="projected cube for DEM grid")
    proj_group.add_argument(
        "--use-left-projection",
        action="store_true",
        help="use the left cube's projection as the DEM grid",
    )
    from_dense_ncc.add_argument("--ncc-window", type=int, default=21, help="NCC window size (odd)")
    from_dense_ncc.add_argument("--ncc-search-range", type=int, default=5, help="search radius around prior")
    from_dense_ncc.add_argument("--ncc-threshold", type=float, default=0.70, help="NCC acceptance threshold")
    from_dense_ncc.add_argument("--no-subpixel", action="store_true", help="disable subpixel refinement")
    from_dense_ncc.add_argument("--enable-gruen", action="store_true", help="enable GRUN refinement (reserved)")
    from_dense_ncc.add_argument("--save-disparity", help="optional path for the 3-band disparity cube")
    from_dense_ncc.add_argument("--value-type", choices=("radius_m", "height_m"), default="radius_m")
    from_dense_ncc.add_argument("--datum-radius-m", type=float)
    from_dense_ncc.add_argument("--aggregation", choices=("median", "mean", "min-error"), default="median")
    from_dense_ncc.add_argument("--nodata-value", type=float, default=-9999.0)
    from_dense_ncc.add_argument("--max-error-m", type=float)
    from_dense_ncc.add_argument("--min-sepang-deg", type=float)
    from_dense_ncc.add_argument("--polynomial-order", type=int, default=2)
    from_dense_ncc.add_argument("--min-key-points", type=int, default=20)
    from_dense_ncc.add_argument("--chunk-size-lines", type=int, default=100)
    from_dense_ncc.add_argument("--point-cloud-output")
    from_dense_ncc.add_argument("--summary-output")
    from_dense_ncc.add_argument("--quality-prefix")
    from_dense_ncc.add_argument(
        "--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR"), default="INFO"
    )
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
        "value_type": summary.get("value_type"),
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
        if args.value_type == "height_m" and args.datum_radius_m is None:
            raise ValueError("--datum-radius-m is required when --value-type height_m is selected.")
        left_cube = _open_cube(ip, args.left_cube)
        right_cube = _open_cube(ip, args.right_cube)
        template_cube = _open_cube(ip, args.map_template_cube)
        left_key_file = read_key_file(args.left_key)
        right_key_file = read_key_file(args.right_key)
        refinement_summary: dict[str, object] | None = None
        refine_stages = normalize_refinement_stages(getattr(args, "refine_stage", []))
        if refine_stages:
            left_key_file, right_key_file, refinement_summary = refine_keypoint_file_pair(
                left_cube=left_cube,
                right_cube=right_cube,
                left_key_file=left_key_file,
                right_key_file=right_key_file,
                ip=ip,
                options=KeyRefinementOptions(stages=refine_stages),
            )
            if args.refined_left_key_output:
                write_key_file(args.refined_left_key_output, left_key_file)
            if args.refined_right_key_output:
                write_key_file(args.refined_right_key_output, right_key_file)
            if args.refinement_summary_output and refinement_summary is not None:
                write_summary_json(args.refinement_summary_output, refinement_summary)

        pairs = load_key_point_pairs_from_key_files(left_key_file, right_key_file, left_cube=left_cube, right_cube=right_cube)
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
        if args.datum_radius_m is not None:
            records = apply_datum_radius(records, args.datum_radius_m)

        raster = rasterize_points(
            records,
            template_cube,
            _template_grid_spec(template_cube, args.nodata_value),
            aggregation=args.aggregation,
            value_field=args.value_type,
        )
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
            value_type=args.value_type,
            datum_radius_m=args.datum_radius_m,
            refinement=refinement_summary,
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


def run_from_dense_ncc(args: argparse.Namespace) -> dict[str, object]:
    ip = import_isis_pybind()
    left_cube = right_cube = template_cube = None
    close_template = False
    try:
        if args.value_type == "height_m" and args.datum_radius_m is None:
            raise ValueError(
                "--datum-radius-m is required when --value-type height_m is selected."
            )

        left_cube = _open_cube(ip, args.left_cube)
        right_cube = _open_cube(ip, args.right_cube)

        pairs = load_key_point_pairs(
            args.left_key, args.right_key, left_cube=left_cube, right_cube=right_cube
        )

        model = fit_disparity_model(
            pairs, order=args.polynomial_order, min_points=args.min_key_points
        )

        options = NCCMatchOptions(
            window_size=args.ncc_window,
            search_range=args.ncc_search_range,
            ncc_threshold=args.ncc_threshold,
            enable_subpixel=not args.no_subpixel,
            enable_gruen=args.enable_gruen,
            chunk_size_lines=args.chunk_size_lines,
        )
        disp_x, disp_y, ncc_score = dense_ncc_match(left_cube, right_cube, model, options)

        if args.save_disparity:
            write_disparity_cube(
                ip,
                disp_x,
                disp_y,
                ncc_score,
                args.save_disparity,
                nodata_value=args.nodata_value,
            )

        if args.use_left_projection:
            template_cube = left_cube
            close_template = False
        else:
            template_cube = _open_cube(ip, args.map_template_cube)
            close_template = True

        filters = FilterOptions(
            max_error_m=args.max_error_m,
            min_sepang_deg=args.min_sepang_deg,
        )
        records = list(
            dense_triangulate_from_disparity(
                left_cube,
                right_cube,
                disp_x,
                disp_y,
                ncc_score,
                filters=filters,
                ip=ip,
                ncc_threshold=args.ncc_threshold,
                nodata_value=args.nodata_value,
            )
        )

        if args.datum_radius_m is not None:
            records = apply_datum_radius(records, args.datum_radius_m)

        raster = rasterize_points(
            records,
            template_cube,
            _template_grid_spec(template_cube, args.nodata_value),
            aggregation=args.aggregation,
            value_field=args.value_type,
        )

        if not records or raster.filled_cell_count == 0:
            raise RuntimeError(
                "No triangulated DEM points survived filtering and rasterization."
            )

        write_radius_cube(ip, template_cube, args.output_dem_cube, raster)

        if args.point_cloud_output:
            if Path(args.point_cloud_output).suffix.lower() == ".csv":
                write_point_cloud_csvish(args.point_cloud_output, records)
            else:
                write_point_cloud_jsonl(args.point_cloud_output, records)
        if args.quality_prefix:
            write_quality_summary_json(f"{args.quality_prefix}.summary.json", raster)

        ncc_stats = count_disparity_stats(
            disp_x,
            disp_y,
            ncc_score,
            ncc_threshold=args.ncc_threshold,
            nodata_value=args.nodata_value,
        )
        triangulation_counters = {
            "success_count": raster.rasterized_point_count,
            "failed_elevation_count": ncc_stats["failed_match_count"],
        }

        summary = build_dense_ncc_summary(
            input_left_cube=args.left_cube,
            input_right_cube=args.right_cube,
            input_left_key=args.left_key,
            input_right_key=args.right_key,
            output_dem_cube=args.output_dem_cube,
            total_pixels=ncc_stats["total_pixels"],
            matched_count=ncc_stats["matched_count"],
            failed_match_count=ncc_stats["failed_match_count"],
            rasterized_point_count=raster.rasterized_point_count,
            filled_cell_count=raster.filled_cell_count,
            value_type=args.value_type,
            datum_radius_m=args.datum_radius_m,
            ncc_threshold=args.ncc_threshold,
            polynomial_order=args.polynomial_order,
            dx_r_squared=model.dx_r_squared,
            dy_r_squared=model.dy_r_squared,
            key_points_used_for_prior=len(pairs),
            prior_fallback=model.prior_fallback,
            nodata_value=args.nodata_value,
            aggregation=args.aggregation,
            max_error_m=args.max_error_m,
            min_sepang_deg=args.min_sepang_deg,
            triangulation_counters=triangulation_counters,
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
        if template_cube is not None and close_template:
            _close_cube(template_cube)
        _close_cube(right_cube)
        _close_cube(left_cube)


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    if args.command == "from-key":
        print(json.dumps(run_from_key(args), sort_keys=True))
        return 0
    if args.command == "from-dense-ncc":
        print(json.dumps(run_from_dense_ncc(args), sort_keys=True))
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
