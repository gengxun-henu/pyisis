"""
Unit tests for the DEM extract example package.

Author: Geng Xun
Created: 2026-05-10
Last Modified: 2026-05-10
Updated: 2026-05-10  Geng Xun added focused coverage for the dem_extract from-key pipeline.
"""

from __future__ import annotations

import json
import subprocess
import sys
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))


class DemExtractBootstrapUnitTest(unittest.TestCase):
    def test_package_exports_version_and_runtime_helpers(self):
        import dem_extract
        from dem_extract import runtime

        self.assertRegex(dem_extract.__version__, r"^0\.1\.0$")
        self.assertTrue(callable(runtime.import_isis_pybind))
        self.assertTrue(callable(runtime.write_summary_json))

    def test_write_summary_json_uses_stable_indented_json(self):
        from dem_extract.runtime import write_summary_json

        output_path = PROJECT_ROOT / "build" / "dem_extract_summary_test.json"
        self.addCleanup(lambda: output_path.exists() and output_path.unlink())
        payload = {"status": "ok", "success_count": 2}

        write_summary_json(output_path, payload)

        self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), payload)
        self.assertTrue(output_path.read_text(encoding="utf-8").endswith("\n"))


class DemExtractKeyPairUnitTest(unittest.TestCase):
    def setUp(self):
        self.workspace = PROJECT_ROOT / "build" / "dem_extract_key_pair_tests"
        self.workspace.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        for path in sorted(self.workspace.glob("*.key")):
            path.unlink()
        if self.workspace.exists():
            self.workspace.rmdir()

    def write_key(self, name: str, text: str) -> Path:
        path = self.workspace / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_mismatched_key_counts_raise_value_error(self):
        from dem_extract.key_pairs import load_key_point_pairs

        left = self.write_key("left.key", "2\n100\n50\n1, 2,\n3, 4,\n")
        right = self.write_key("right.key", "1\n100\n50\n1, 2,\n")

        with self.assertRaisesRegex(ValueError, "same number of points"):
            load_key_point_pairs(left, right, left_cube=None, right_cube=None)

    def test_key_sample_line_are_preserved_without_offset(self):
        from dem_extract.key_pairs import load_key_point_pairs

        left = self.write_key("left.key", "1\n100\n50\n10.25, 20.5,\n")
        right = self.write_key("right.key", "1\n100\n50\n30.75, 40.5,\n")

        pairs = load_key_point_pairs(left, right, left_cube=None, right_cube=None)

        self.assertEqual(pairs[0].left_sample, 10.25)
        self.assertEqual(pairs[0].left_line, 20.5)
        self.assertEqual(pairs[0].right_sample, 30.75)
        self.assertEqual(pairs[0].right_line, 40.5)

    def test_coordinates_outside_cube_bounds_raise_value_error(self):
        from dem_extract.key_pairs import load_key_point_pairs

        class FakeCube:
            def sample_count(self):
                return 100

            def line_count(self):
                return 50

        left = self.write_key("left.key", "1\n100\n50\n101, 20,\n")
        right = self.write_key("right.key", "1\n100\n50\n30, 40,\n")

        with self.assertRaisesRegex(ValueError, "left point 0"):
            load_key_point_pairs(left, right, left_cube=FakeCube(), right_cube=FakeCube())


class DemExtractTriangulationUnitTest(unittest.TestCase):
    def test_triangulation_reuses_cameras_and_preserves_key_coordinates(self):
        from dem_extract.key_pairs import KeyPointPair
        from dem_extract.triangulation import FilterOptions, triangulate_pairs

        class FakeCamera:
            def __init__(self):
                self.calls = []

            def set_image(self, sample, line):
                self.calls.append((sample, line))
                return True

        class FakeCube:
            def __init__(self):
                self.camera_call_count = 0
                self._camera = FakeCamera()

            def camera(self):
                self.camera_call_count += 1
                return self._camera

        class FakeStereo:
            @staticmethod
            def elevation(left_camera, right_camera):
                return True, 3396190.0, 12.0, 34.0, 5.0, 2.5

            @staticmethod
            def spherical(latitude_deg, longitude_deg, radius_m):
                return 1.0, 2.0, 3.0

        class FakeIp:
            Stereo = FakeStereo

        left_cube = FakeCube()
        right_cube = FakeCube()
        pairs = [KeyPointPair(0, 10.25, 20.5, 30.75, 40.5), KeyPointPair(1, 11.0, 21.0, 31.0, 41.0)]

        records, counters = triangulate_pairs(pairs, left_cube, right_cube, FakeIp, FilterOptions())

        self.assertEqual(left_cube.camera_call_count, 1)
        self.assertEqual(right_cube.camera_call_count, 1)
        self.assertEqual(left_cube._camera.calls[0], (10.25, 20.5))
        self.assertEqual(right_cube._camera.calls[0], (30.75, 40.5))
        self.assertEqual([record.status for record in records], ["success", "success"])
        self.assertEqual(counters["success_count"], 2)

    def test_triangulation_filters_error_sepang_and_radius_with_counters(self):
        from dem_extract.key_pairs import KeyPointPair
        from dem_extract.triangulation import FilterOptions, triangulate_pairs

        class FakeCamera:
            def set_image(self, sample, line):
                return True

        class FakeCube:
            def camera(self):
                return FakeCamera()

        class FakeStereo:
            values = [
                (True, 10.0, 1.0, 2.0, 5.0, 99.0),
                (True, 10.0, 1.0, 2.0, 0.1, 1.0),
                (True, 200.0, 1.0, 2.0, 5.0, 1.0),
                (True, 50.0, 1.0, 2.0, 5.0, 1.0),
            ]

            @classmethod
            def elevation(cls, left_camera, right_camera):
                return cls.values.pop(0)

            @staticmethod
            def spherical(latitude_deg, longitude_deg, radius_m):
                return 0.0, 0.0, radius_m / 1000.0

        class FakeIp:
            Stereo = FakeStereo

        pairs = [KeyPointPair(i, 1.0, 1.0, 1.0, 1.0) for i in range(4)]
        records, counters = triangulate_pairs(
            pairs,
            FakeCube(),
            FakeCube(),
            FakeIp,
            FilterOptions(max_error_m=10.0, min_sepang_deg=1.0, min_radius_m=20.0, max_radius_m=100.0),
        )

        self.assertEqual([record.status for record in records], ["filtered", "filtered", "filtered", "success"])
        self.assertEqual(counters["filtered_error_count"], 1)
        self.assertEqual(counters["filtered_sepang_count"], 1)
        self.assertEqual(counters["filtered_radius_count"], 1)
        self.assertEqual(counters["success_count"], 1)


class DemExtractRuntimeOutputUnitTest(unittest.TestCase):
    def setUp(self):
        self.workspace = PROJECT_ROOT / "build" / "dem_extract_output_tests"
        self.workspace.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        for path in sorted(self.workspace.glob("*")):
            if path.is_file():
                path.unlink()
        if self.workspace.exists():
            self.workspace.rmdir()

    def test_write_point_cloud_jsonl_preserves_required_fields(self):
        from dem_extract.triangulation import TriangulatedPoint
        from dem_extract.runtime import write_point_cloud_jsonl

        path = self.workspace / "points.jsonl"
        records = [TriangulatedPoint(0, 1.0, 2.0, 3.0, 4.0, "success", "", 5.0, 6.0, 7.0, 8.0, 9.0, 1.0, 2.0, 3.0)]

        write_point_cloud_jsonl(path, records)

        row = json.loads(path.read_text(encoding="utf-8").strip())
        self.assertEqual(row["index"], 0)
        self.assertEqual(row["radius_m"], 7.0)
        self.assertEqual(row["intersection_error_m"], 9.0)

    def test_build_summary_contains_required_counters_and_value_type(self):
        from dem_extract.runtime import build_summary

        summary = build_summary(
            input_left_cube="left.cub",
            input_right_cube="right.cub",
            input_left_key="left.key",
            input_right_key="right.key",
            map_template="template.cub",
            output_dem_cube="dem.cub",
            input_point_count=4,
            triangulation_counters={
                "success_count": 1,
                "failed_set_image_count": 1,
                "failed_elevation_count": 1,
                "filtered_error_count": 1,
                "filtered_sepang_count": 0,
                "filtered_radius_count": 0,
            },
            rasterized_point_count=1,
            filled_cell_count=1,
            max_error_m=10.0,
            min_sepang_deg=0.5,
            nodata_value=-32768.0,
            aggregation="median",
        )

        self.assertEqual(summary["value_type"], "radius_m")
        self.assertEqual(summary["input_point_count"], 4)
        self.assertEqual(summary["failed_set_image_count"], 1)
        self.assertEqual(summary["nodata_value"], -32768.0)

    def test_write_quality_summary_json_records_quality_prefix_payload(self):
        from dem_extract.runtime import write_quality_summary_json

        class FakeRaster:
            values = [[1.0, -9999.0]]
            rasterized_point_count = 1
            filled_cell_count = 1
            nodata_value = -9999.0

        path = self.workspace / "quality.summary.json"

        write_quality_summary_json(path, FakeRaster())

        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["rasterized_point_count"], 1)
        self.assertEqual(payload["filled_cell_count"], 1)
        self.assertEqual(payload["quality_product_type"], "summary")


class DemExtractGridUnitTest(unittest.TestCase):
    def test_same_cell_aggregation_supports_median_mean_and_min_error(self):
        from dem_extract.grid import aggregate_cell_values
        from dem_extract.triangulation import TriangulatedPoint

        records = [
            TriangulatedPoint(0, 1, 1, 1, 1, "success", "", radius_m=10.0, intersection_error_m=5.0),
            TriangulatedPoint(1, 1, 1, 1, 1, "success", "", radius_m=30.0, intersection_error_m=1.0),
            TriangulatedPoint(2, 1, 1, 1, 1, "success", "", radius_m=20.0, intersection_error_m=3.0),
        ]

        self.assertEqual(aggregate_cell_values(records, "median"), 20.0)
        self.assertEqual(aggregate_cell_values(records, "mean"), 20.0)
        self.assertEqual(aggregate_cell_values(records, "min-error"), 30.0)

    def test_rasterize_points_uses_template_projection_and_fills_nodata(self):
        from dem_extract.grid import GridSpec, rasterize_points
        from dem_extract.triangulation import TriangulatedPoint

        class FakeProjection:
            def set_universal_ground(self, latitude, longitude):
                self.latitude = latitude
                self.longitude = longitude
                return latitude >= 0

            def world_x(self):
                return 2.0

            def world_y(self):
                return 1.0

        class FakeTemplateCube:
            def projection(self):
                return FakeProjection()

        records = [
            TriangulatedPoint(0, 1, 1, 1, 1, "success", "", latitude_deg=10.0, longitude_deg=20.0, radius_m=42.0, intersection_error_m=1.0),
            TriangulatedPoint(1, 1, 1, 1, 1, "filtered", "filtered_error", latitude_deg=10.0, longitude_deg=20.0, radius_m=99.0, intersection_error_m=99.0),
            TriangulatedPoint(2, 1, 1, 1, 1, "success", "", latitude_deg=-1.0, longitude_deg=20.0, radius_m=12.0, intersection_error_m=1.0),
        ]

        raster = rasterize_points(records, FakeTemplateCube(), GridSpec(samples=3, lines=2, nodata_value=-9999.0), aggregation="median")

        self.assertEqual(raster.values, [[-9999.0, 42.0, -9999.0], [-9999.0, -9999.0, -9999.0]])
        self.assertEqual(raster.rasterized_point_count, 1)
        self.assertEqual(raster.filled_cell_count, 1)
        self.assertEqual(raster.nodata_value, -9999.0)


class DemExtractCubeWriterUnitTest(unittest.TestCase):
    def test_preflight_reports_missing_writer_bindings(self):
        from dem_extract.cube_writer import preflight_cube_writer_bindings

        class FakeIp:
            pass

        self.assertIn("Cube", preflight_cube_writer_bindings(FakeIp))

    def test_write_radius_cube_sets_dimensions_pixel_type_copies_mapping_and_writes_lines(self):
        from dem_extract.cube_writer import write_radius_cube
        from dem_extract.grid import RasterResult

        class FakeGroup:
            pass

        class FakeTemplateCube:
            def group(self, name):
                self.requested_group = name
                return FakeGroup()

        class FakeLineManager:
            def __init__(self, cube, reverse=False):
                self.cube = cube
                self.values = []

            def set_line(self, line, band=1):
                self.line = line
                self.band = band

            def __setitem__(self, index, value):
                self.values.append((index, value))

        class FakeCube:
            created = None

            def __init__(self):
                self.groups = []
                self.writes = []
                FakeCube.created = self

            def set_dimensions(self, samples, lines, bands):
                self.dimensions = (samples, lines, bands)

            def set_pixel_type(self, pixel_type):
                self.pixel_type = pixel_type

            def group(self, name):
                self.requested_group = name
                return FakeGroup()

            def create(self, path):
                self.path = path

            def put_group(self, group):
                self.groups.append(group)

            def write(self, line_manager):
                self.writes.append((line_manager.line, tuple(line_manager.values)))

            def close(self):
                self.closed = True

        class FakeIp:
            Cube = FakeCube
            LineManager = FakeLineManager

            class PixelType:
                Real = "Real"

        result = RasterResult(values=[[1.0, 2.0], [3.0, 4.0]], rasterized_point_count=4, filled_cell_count=4)

        write_radius_cube(FakeIp, FakeTemplateCube(), "out.cub", result)

        cube = FakeCube.created
        self.assertEqual(cube.dimensions, (2, 2, 1))
        self.assertEqual(cube.pixel_type, "Real")
        self.assertEqual(cube.path, "out.cub")
        self.assertEqual(len(cube.groups), 1)
        self.assertEqual([line for line, values in cube.writes], [1, 2])

    def test_write_radius_cube_closes_output_when_mapping_copy_fails(self):
        from dem_extract.cube_writer import write_radius_cube
        from dem_extract.grid import RasterResult

        class FakeTemplateCube:
            def group(self, name):
                raise RuntimeError("missing mapping")

        class FakeLineManager:
            pass

        class FakeCube:
            created = None

            def __init__(self):
                self.closed = False
                FakeCube.created = self

            def set_dimensions(self, samples, lines, bands):
                pass

            def set_pixel_type(self, pixel_type):
                pass

            def create(self, path):
                self.path = path

            def put_group(self, group):
                pass

            def write(self, line_manager):
                pass

            def close(self):
                self.closed = True

        class FakeIp:
            Cube = FakeCube
            LineManager = FakeLineManager

            class PixelType:
                Real = "Real"

        with self.assertRaisesRegex(RuntimeError, "Mapping"):
            write_radius_cube(FakeIp, FakeTemplateCube(), "out.cub", RasterResult([[1.0]], 1, 1))

        self.assertTrue(FakeCube.created.closed)


class DemExtractCliUnitTest(unittest.TestCase):
    def test_package_exports_grid_and_writer_helpers(self):
        from dem_extract import GridSpec, RasterResult, preflight_cube_writer_bindings, rasterize_points, write_radius_cube

        self.assertTrue(callable(rasterize_points))
        self.assertTrue(callable(preflight_cube_writer_bindings))
        self.assertTrue(callable(write_radius_cube))
        self.assertEqual(GridSpec(samples=1, lines=1).samples, 1)
        self.assertEqual(RasterResult(values=[[1.0]], rasterized_point_count=1, filled_cell_count=1).filled_cell_count, 1)

    def test_run_from_key_closes_input_and_template_cubes(self):
        from dem_extract import isis_stereo_dem
        from dem_extract.grid import RasterResult
        from dem_extract.triangulation import TriangulatedPoint

        opened_cubes = []

        class FakeCube:
            def __init__(self):
                self.closed = False
                opened_cubes.append(self)

            def open(self, path, access):
                self.path = path
                self.access = access

            def sample_count(self):
                return 2

            def line_count(self):
                return 1

            def close(self):
                self.closed = True

        class FakeIp:
            Cube = FakeCube

        original_import = isis_stereo_dem.import_isis_pybind
        original_load = isis_stereo_dem.load_key_point_pairs
        original_triangulate = isis_stereo_dem.triangulate_pairs
        original_rasterize = isis_stereo_dem.rasterize_points
        original_write_cube = isis_stereo_dem.write_radius_cube
        try:
            isis_stereo_dem.import_isis_pybind = lambda: FakeIp
            isis_stereo_dem.load_key_point_pairs = lambda *args, **kwargs: [object()]
            isis_stereo_dem.triangulate_pairs = lambda *args, **kwargs: (
                [TriangulatedPoint(0, 1, 1, 1, 1, "success", "", radius_m=1.0)],
                {"success_count": 1},
            )
            isis_stereo_dem.rasterize_points = lambda *args, **kwargs: RasterResult([[1.0]], 1, 1)
            isis_stereo_dem.write_radius_cube = lambda *args, **kwargs: None
            args = isis_stereo_dem.build_argument_parser().parse_args(
                ["from-key", "left.cub", "right.cub", "left.key", "right.key", "template.cub", "dem.cub"]
            )

            isis_stereo_dem.run_from_key(args)
        finally:
            isis_stereo_dem.import_isis_pybind = original_import
            isis_stereo_dem.load_key_point_pairs = original_load
            isis_stereo_dem.triangulate_pairs = original_triangulate
            isis_stereo_dem.rasterize_points = original_rasterize
            isis_stereo_dem.write_radius_cube = original_write_cube

        self.assertEqual(len(opened_cubes), 3)
        self.assertTrue(all(cube.closed for cube in opened_cubes))

    def test_cli_script_help_runs_from_repository_root(self):
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "examples" / "dem_extract" / "isis_stereo_dem.py"),
                "--help",
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("from-key", result.stdout)

    def test_from_key_requires_all_positionals_and_kebab_case_options(self):
        from dem_extract.isis_stereo_dem import build_argument_parser

        parser = build_argument_parser()
        with self.assertRaises(SystemExit):
            with redirect_stderr(StringIO()):
                parser.parse_args(["from-key", "left.cub"])

        args = parser.parse_args([
            "from-key",
            "left.cub", "right.cub", "left.key", "right.key", "template.cub", "dem.cub",
            "--point-cloud-output", "points.jsonl",
            "--summary-output", "summary.json",
            "--quality-prefix", "quality",
            "--max-error-m", "10",
            "--min-sepang-deg", "0.5",
            "--min-radius-m", "1000",
            "--max-radius-m", "4000000",
            "--aggregation", "min-error",
            "--nodata-value", "-9999",
            "--log-level", "DEBUG",
        ])

        self.assertEqual(args.command, "from-key")
        self.assertEqual(args.aggregation, "min-error")
        self.assertEqual(args.point_cloud_output, "points.jsonl")
        self.assertEqual(args.quality_prefix, "quality")

    def test_compact_stdout_payload_omits_point_records(self):
        from dem_extract.isis_stereo_dem import compact_stdout_payload

        payload = compact_stdout_payload(
            output_dem_cube="dem.cub",
            point_cloud_output="points.jsonl",
            summary_output="summary.json",
            summary={"success_count": 2, "filled_cell_count": 1, "records": [{"index": 0}]},
        )

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["output_dem_cube"], "dem.cub")
        self.assertNotIn("records", payload)
        self.assertEqual(payload["success_count"], 2)


if __name__ == "__main__":
    unittest.main()
