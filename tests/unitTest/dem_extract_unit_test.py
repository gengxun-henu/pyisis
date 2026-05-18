"""
Unit tests for the DEM extract example package.

Author: Geng Xun
Created: 2026-05-10
Last Modified: 2026-05-18
Updated: 2026-05-10  Geng Xun added focused coverage for the dem_extract from-key pipeline.
Updated: 2026-05-10  Geng Xun added focused coverage for the DEM image-matching pipeline wrapper.
Updated: 2026-05-10  Geng Xun added focused coverage for `.key` refinement stages in the DEM flow.
Updated: 2026-05-10  Geng Xun added coverage for dense NCC disparity DEM modules and CLI.
Updated: 2026-05-18  Geng Xun added config-key compatibility coverage for camelCase route overrides in dem_pipeline.
"""

from __future__ import annotations

import json
import subprocess
import sys
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import unittest

import numpy as np


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

    def test_apply_datum_radius_populates_height_m(self):
        from dem_extract.triangulation import TriangulatedPoint, apply_datum_radius

        records = [TriangulatedPoint(0, 1, 1, 1, 1, "success", "", radius_m=1737412.5)]

        adjusted = apply_datum_radius(records, 1737400.0)

        self.assertEqual(adjusted[0].datum_radius_m, 1737400.0)
        self.assertAlmostEqual(adjusted[0].height_m, 12.5, places=6)


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
        self.assertIsNone(row["height_m"])
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
            value_type="height_m",
            datum_radius_m=1737400.0,
            refinement={"applied": True, "stage_count": 1},
            max_error_m=10.0,
            min_sepang_deg=0.5,
            nodata_value=-32768.0,
            aggregation="median",
        )

        self.assertEqual(summary["value_type"], "height_m")
        self.assertEqual(summary["datum_radius_m"], 1737400.0)
        self.assertEqual(summary["refinement"]["stage_count"], 1)
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

    def test_aggregation_supports_height_field(self):
        from dem_extract.grid import aggregate_cell_values
        from dem_extract.triangulation import TriangulatedPoint

        records = [
            TriangulatedPoint(0, 1, 1, 1, 1, "success", "", radius_m=10.0, height_m=1.0, intersection_error_m=5.0),
            TriangulatedPoint(1, 1, 1, 1, 1, "success", "", radius_m=30.0, height_m=3.0, intersection_error_m=1.0),
            TriangulatedPoint(2, 1, 1, 1, 1, "success", "", radius_m=20.0, height_m=2.0, intersection_error_m=3.0),
        ]

        self.assertEqual(aggregate_cell_values(records, "median", value_field="height_m"), 2.0)
        self.assertEqual(aggregate_cell_values(records, "mean", value_field="height_m"), 2.0)
        self.assertEqual(aggregate_cell_values(records, "min-error", value_field="height_m"), 3.0)

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
        original_read_key = isis_stereo_dem.read_key_file
        original_load = isis_stereo_dem.load_key_point_pairs_from_key_files
        original_triangulate = isis_stereo_dem.triangulate_pairs
        original_rasterize = isis_stereo_dem.rasterize_points
        original_write_cube = isis_stereo_dem.write_radius_cube
        try:
            isis_stereo_dem.import_isis_pybind = lambda: FakeIp
            isis_stereo_dem.read_key_file = lambda *args, **kwargs: type("KeyFile", (), {"points": (object(),), "image_width": 2, "image_height": 1})()
            isis_stereo_dem.load_key_point_pairs_from_key_files = lambda *args, **kwargs: [object()]
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
            isis_stereo_dem.read_key_file = original_read_key
            isis_stereo_dem.load_key_point_pairs_from_key_files = original_load
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
            "--value-type", "height_m",
            "--datum-radius-m", "1737400",
            "--refine-stage", "maximum-correlation",
            "--refine-stage", "gruen",
            "--refined-left-key-output", "left_refined.key",
            "--refined-right-key-output", "right_refined.key",
            "--refinement-summary-output", "refinement_summary.json",
            "--nodata-value", "-9999",
            "--log-level", "DEBUG",
        ])

        self.assertEqual(args.command, "from-key")
        self.assertEqual(args.aggregation, "min-error")
        self.assertEqual(args.value_type, "height_m")
        self.assertEqual(args.datum_radius_m, 1737400.0)
        self.assertEqual(args.refine_stage, ["maximum-correlation", "gruen"])
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


class DemExtractRefinementUnitTest(unittest.TestCase):
    def test_refinement_chain_updates_right_keypoints_and_reuses_stage_output_as_next_seed(self):
        from controlnet_construct.keypoints import Keypoint, KeypointFile
        from dem_extract.refinement import KeyRefinementOptions, refine_keypoint_file_pair

        class FakeCube:
            def sample_count(self):
                return 100

            def line_count(self):
                return 100

        class FakeChip:
            def __init__(self):
                self.tack_calls = []

            def tack_cube(self, sample, line):
                self.tack_calls.append((sample, line))

            def load(self, cube):
                pass

        class FakeMatcher:
            def __init__(self, scripted_results):
                self.scripted_results = list(scripted_results)
                self._pattern_chip = FakeChip()
                self._search_chip = FakeChip()
                self._current = None

            def pattern_chip(self):
                return self._pattern_chip

            def search_chip(self):
                return self._search_chip

            def register(self):
                self._current = self.scripted_results.pop(0)
                return self._current["status"]

            def success(self):
                return self._current["status"] in {1, 2}

            def cube_sample(self):
                return self._current["sample"]

            def cube_line(self):
                return self._current["line"]

            def goodness_of_fit(self):
                return self._current.get("goodness", 1.0)

        class FakeIp:
            class AutoReg:
                class RegisterStatus:
                    SuccessPixel = 1
                    SuccessSubPixel = 2
                    FitChipToleranceNotMet = 3

        left_key_file = KeypointFile(100, 100, (Keypoint(10.0, 20.0),))
        right_key_file = KeypointFile(100, 100, (Keypoint(30.0, 40.0),))

        maxcorr_matcher = FakeMatcher([
            {"status": FakeIp.AutoReg.RegisterStatus.SuccessSubPixel, "sample": 31.5, "line": 41.5}
        ])
        gruen_matcher = FakeMatcher([
            {"status": FakeIp.AutoReg.RegisterStatus.SuccessSubPixel, "sample": 31.75, "line": 41.25}
        ])

        import dem_extract.refinement as refinement

        original_factory = refinement._create_stage_matcher
        try:
            def fake_factory(ip, stage_name, options):
                if stage_name == "maximum_correlation":
                    return maxcorr_matcher
                if stage_name == "gruen":
                    return gruen_matcher
                raise AssertionError(stage_name)

            refinement._create_stage_matcher = fake_factory

            refined_left, refined_right, summary = refine_keypoint_file_pair(
                left_cube=FakeCube(),
                right_cube=FakeCube(),
                left_key_file=left_key_file,
                right_key_file=right_key_file,
                ip=FakeIp,
                options=KeyRefinementOptions(stages=("maximum_correlation", "gruen")),
            )
        finally:
            refinement._create_stage_matcher = original_factory

        self.assertEqual(refined_left.points[0], Keypoint(10.0, 20.0))
        self.assertEqual(refined_right.points[0], Keypoint(31.75, 41.25))
        self.assertTrue(summary["applied"])
        self.assertEqual(summary["stage_count"], 2)
        self.assertEqual(gruen_matcher.search_chip().tack_calls[0], (31.5, 41.5))

    def test_refinement_failure_retains_original_seed_and_reports_failure(self):
        from controlnet_construct.keypoints import Keypoint, KeypointFile
        from dem_extract.refinement import KeyRefinementOptions, refine_keypoint_file_pair

        class FakeCube:
            def sample_count(self):
                return 100

            def line_count(self):
                return 100

        class FakeChip:
            def tack_cube(self, sample, line):
                pass

            def load(self, cube):
                pass

        class FakeMatcher:
            def __init__(self, status):
                self.status = status
                self._pattern_chip = FakeChip()
                self._search_chip = FakeChip()

            def pattern_chip(self):
                return self._pattern_chip

            def search_chip(self):
                return self._search_chip

            def register(self):
                return self.status

            def success(self):
                return False

            def cube_sample(self):
                return 0.0

            def cube_line(self):
                return 0.0

            def goodness_of_fit(self):
                return 0.0

        class FakeIp:
            class AutoReg:
                class RegisterStatus:
                    SuccessPixel = 1
                    SuccessSubPixel = 2
                    FitChipToleranceNotMet = 3

        left_key_file = KeypointFile(100, 100, (Keypoint(10.0, 20.0),))
        right_key_file = KeypointFile(100, 100, (Keypoint(30.0, 40.0),))

        import dem_extract.refinement as refinement

        original_factory = refinement._create_stage_matcher
        try:
            refinement._create_stage_matcher = lambda *args, **kwargs: FakeMatcher(FakeIp.AutoReg.RegisterStatus.FitChipToleranceNotMet)
            _, refined_right, summary = refine_keypoint_file_pair(
                left_cube=FakeCube(),
                right_cube=FakeCube(),
                left_key_file=left_key_file,
                right_key_file=right_key_file,
                ip=FakeIp,
                options=KeyRefinementOptions(stages=("maximum_correlation",)),
            )
        finally:
            refinement._create_stage_matcher = original_factory

        self.assertEqual(refined_right.points[0], Keypoint(30.0, 40.0))
        self.assertEqual(summary["stages"][0]["failed_count"], 1)
        self.assertEqual(summary["stages"][0]["updated_count"], 0)

    def test_run_from_key_requires_datum_radius_for_height_mode(self):
        from dem_extract import isis_stereo_dem

        args = isis_stereo_dem.build_argument_parser().parse_args(
            [
                "from-key",
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "template.cub",
                "dem.cub",
                "--value-type",
                "height_m",
            ]
        )

        with self.assertRaisesRegex(ValueError, "datum-radius-m"):
            isis_stereo_dem.run_from_key(args)


class DemExtractDisparityModelUnitTest(unittest.TestCase):
    def test_fit_disparity_model_returns_valid_model_with_r_squared(self):
        from dem_extract.disparity_model import fit_disparity_model
        from dem_extract.key_pairs import KeyPointPair

        pairs = [
            KeyPointPair(
                i,
                float(s),
                float(l),
                float(s) + float(s) * 0.1,
                float(l) + float(l) * 0.05,
            )
            for i, (s, l) in enumerate(
                [(10, 10), (20, 20), (30, 30), (40, 40), (50, 50)]
            )
        ]

        model = fit_disparity_model(pairs, order=2, min_points=3)

        self.assertEqual(model.order, 2)
        self.assertGreater(model.dx_r_squared, 0.99)
        self.assertGreater(model.dy_r_squared, 0.99)
        dx = model.eval_dx(20.0, 20.0)
        dy = model.eval_dy(20.0, 20.0)
        self.assertAlmostEqual(dx, 2.0, places=1)
        self.assertAlmostEqual(dy, 1.0, places=1)

    def test_fit_disparity_model_fallback_to_mean_when_insufficient_points(self):
        from dem_extract.disparity_model import fit_disparity_model
        from dem_extract.key_pairs import KeyPointPair

        pairs = [
            KeyPointPair(0, 10.0, 10.0, 15.0, 12.0),
            KeyPointPair(1, 20.0, 20.0, 25.0, 22.0),
        ]

        model = fit_disparity_model(pairs, order=2, min_points=5)

        self.assertEqual(model.prior_fallback, "mean_disparity")
        self.assertAlmostEqual(model.eval_dx(30.0, 30.0), 5.0, places=6)
        self.assertAlmostEqual(model.eval_dy(30.0, 30.0), 2.0, places=6)

    def test_disparity_model_eval_at_image_corners(self):
        from dem_extract.disparity_model import fit_disparity_model
        from dem_extract.key_pairs import KeyPointPair

        pairs = [
            KeyPointPair(
                i,
                100.0 + i * 100,
                100.0 + i * 50,
                100.0 + i * 100 + 5.0,
                100.0 + i * 50 + 2.0,
            )
            for i in range(20)
        ]

        model = fit_disparity_model(pairs, order=1)

        self.assertIsInstance(model.eval_dx(1.0, 1.0), float)
        self.assertIsInstance(model.eval_dx(1000.0, 1000.0), float)


class DemExtractDenseNCCUnitTest(unittest.TestCase):
    @staticmethod
    def _make_fake_cube(width: int, height: int, data: np.ndarray):
        class FakeCube:
            def __init__(self):
                self._data = data

            def sample_count(self):
                return width

            def line_count(self):
                return height

            def read(self, band=1):
                return self._data

        return FakeCube()

    @staticmethod
    def _make_model(dx: float = 5.0, dy: float = 3.0):
        from dem_extract.disparity_model import DisparityModel

        return DisparityModel(
            dx_coeffs=np.array([dx, 0.0, 0.0, 0.0, 0.0, 0.0]),
            dy_coeffs=np.array([dy, 0.0, 0.0, 0.0, 0.0, 0.0]),
            order=2,
            dx_r_squared=1.0,
            dy_r_squared=1.0,
        )

    def test_integer_pixel_match_succeeds_with_known_disparity(self):
        from dem_extract.dense_ncc import NCCMatchOptions, dense_ncc_match

        left = np.zeros((50, 50), dtype=np.float64)
        left[15:35, 15:35] = 1.0
        right = np.zeros((50, 50), dtype=np.float64)
        right[18:38, 20:40] = 1.0

        left_cube = self._make_fake_cube(50, 50, left)
        right_cube = self._make_fake_cube(50, 50, right)
        model = self._make_model(dx=5.0, dy=3.0)

        disp_x, disp_y, ncc = dense_ncc_match(
            left_cube,
            right_cube,
            model,
            NCCMatchOptions(
                window_size=11,
                search_range=3,
                ncc_threshold=0.7,
                enable_subpixel=False,
            ),
        )

        center_ncc = ncc[15, 15]
        center_dx = disp_x[15, 15]
        center_dy = disp_y[15, 15]

        self.assertGreater(center_ncc, 0.7)
        self.assertAlmostEqual(center_dx, 5.0, delta=1.0)
        self.assertAlmostEqual(center_dy, 3.0, delta=1.0)

    def test_nodata_for_unmatchable_region(self):
        from dem_extract.dense_ncc import NCCMatchOptions, dense_ncc_match

        left = np.zeros((30, 30), dtype=np.float64)
        right = np.ones((30, 30), dtype=np.float64) * 0.5

        left_cube = self._make_fake_cube(30, 30, left)
        right_cube = self._make_fake_cube(30, 30, right)
        model = self._make_model(dx=0.0, dy=0.0)

        _, _, ncc = dense_ncc_match(
            left_cube,
            right_cube,
            model,
            NCCMatchOptions(
                window_size=7,
                search_range=2,
                ncc_threshold=0.7,
                enable_subpixel=False,
            ),
        )

        self.assertTrue(np.all((ncc == -9999.0) | (ncc < 0.7)))

    def test_subpixel_match_succeeds_on_shifted_pattern(self):
        from dem_extract.dense_ncc import NCCMatchOptions, dense_ncc_match

        left = np.zeros((40, 40), dtype=np.float64)
        left[15:25, 15:25] = 1.0
        right = np.zeros((40, 40), dtype=np.float64)
        right[18:28, 20:30] = 1.0

        left_cube = self._make_fake_cube(40, 40, left)
        right_cube = self._make_fake_cube(40, 40, right)
        model = self._make_model(dx=5.0, dy=3.0)

        _, _, ncc = dense_ncc_match(
            left_cube,
            right_cube,
            model,
            NCCMatchOptions(
                window_size=11,
                search_range=3,
                ncc_threshold=0.7,
                enable_subpixel=True,
            ),
        )

        self.assertGreater(ncc[15, 15], 0.7)

    def test_count_disparity_stats_returns_correct_counts(self):
        from dem_extract.dense_ncc import count_disparity_stats

        disp_x = np.array([[1.0, -9999.0], [2.0, 3.0]], dtype=np.float32)
        disp_y = np.array([[1.0, -9999.0], [2.0, 3.0]], dtype=np.float32)
        ncc = np.array([[0.9, -9999.0], [0.5, 0.95]], dtype=np.float32)

        stats = count_disparity_stats(
            disp_x, disp_y, ncc, ncc_threshold=0.7, nodata_value=-9999.0
        )

        self.assertEqual(stats["total_pixels"], 4)
        self.assertEqual(stats["matched_count"], 2)
        self.assertEqual(stats["failed_match_count"], 2)


class DemExtractDenseTriangulationUnitTest(unittest.TestCase):
    def test_dense_triangulate_yields_triangulated_points(self):
        from dem_extract.dense_triangulation import dense_triangulate_from_disparity
        from dem_extract.triangulation import FilterOptions, TriangulatedPoint

        class FakeCamera:
            def set_image(self, sample, line):
                return True

        class FakeCube:
            def camera(self):
                return FakeCamera()

            def sample_count(self):
                return 3

            def line_count(self):
                return 2

        class FakeStereo:
            values = [
                (True, 3396190.0, 12.0, 34.0, 5.0, 2.5),
                (True, 3396190.0, 12.5, 34.5, 5.5, 1.5),
                (True, 3396190.0, 12.6, 34.6, 5.6, 1.6),
                (True, 3396190.0, 12.7, 34.7, 5.7, 1.7),
            ]

            @classmethod
            def elevation(cls, left_camera, right_camera):
                return cls.values.pop(0)

            @staticmethod
            def spherical(lat, lon, radius):
                return (1.0, 2.0, 3.0)

        class FakeIp:
            Stereo = FakeStereo

        disp_x = np.array([[5.0, -9999.0, 6.0], [7.0, 8.0, -9999.0]], dtype=np.float32)
        disp_y = np.array([[3.0, -9999.0, 4.0], [2.0, 1.0, -9999.0]], dtype=np.float32)
        ncc = np.array([[0.9, -9999.0, 0.8], [0.85, 0.95, -9999.0]], dtype=np.float32)

        points = list(
            dense_triangulate_from_disparity(
                FakeCube(),
                FakeCube(),
                disp_x,
                disp_y,
                ncc,
                filters=FilterOptions(),
                ip=FakeIp,
            )
        )

        self.assertEqual(len(points), 4)
        self.assertTrue(all(isinstance(p, TriangulatedPoint) for p in points))

    def test_dense_triangulate_filters_by_ncc_threshold(self):
        from dem_extract.dense_triangulation import dense_triangulate_from_disparity
        from dem_extract.triangulation import FilterOptions

        class FakeCamera:
            def set_image(self, sample, line):
                return True

        class FakeCube:
            def camera(self):
                return FakeCamera()

            def sample_count(self):
                return 2

            def line_count(self):
                return 1

        class FakeStereo:
            @staticmethod
            def elevation(*args):
                return (True, 3396190.0, 12.0, 34.0, 5.0, 2.5)

            @staticmethod
            def spherical(lat, lon, radius):
                return (1.0, 2.0, 3.0)

        class FakeIp:
            Stereo = FakeStereo

        disp_x = np.array([[5.0, 5.0]], dtype=np.float32)
        disp_y = np.array([[3.0, 3.0]], dtype=np.float32)
        ncc = np.array([[0.9, 0.5]], dtype=np.float32)

        points = list(
            dense_triangulate_from_disparity(
                FakeCube(),
                FakeCube(),
                disp_x,
                disp_y,
                ncc,
                filters=FilterOptions(),
                ip=FakeIp,
                ncc_threshold=0.7,
            )
        )

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].index, 0)

    def test_dense_triangulate_applies_filter_options(self):
        from dem_extract.dense_triangulation import dense_triangulate_from_disparity
        from dem_extract.triangulation import FilterOptions

        class FakeCamera:
            def set_image(self, sample, line):
                return True

        class FakeCube:
            def camera(self):
                return FakeCamera()

            def sample_count(self):
                return 1

            def line_count(self):
                return 1

        class FakeStereo:
            @staticmethod
            def elevation(*args):
                return (True, 3396190.0, 12.0, 34.0, 5.0, 99.0)

            @staticmethod
            def spherical(lat, lon, radius):
                return (1.0, 2.0, 3.0)

        class FakeIp:
            Stereo = FakeStereo

        disp_x = np.array([[5.0]], dtype=np.float32)
        disp_y = np.array([[3.0]], dtype=np.float32)
        ncc = np.array([[0.9]], dtype=np.float32)

        points = list(
            dense_triangulate_from_disparity(
                FakeCube(),
                FakeCube(),
                disp_x,
                disp_y,
                ncc,
                filters=FilterOptions(max_error_m=10.0),
                ip=FakeIp,
            )
        )

        self.assertEqual(len(points), 0)


class DemExtractDenseNCCSummaryUnitTest(unittest.TestCase):
    def test_build_dense_ncc_summary_includes_all_required_keys(self):
        from dem_extract.runtime import build_dense_ncc_summary

        summary = build_dense_ncc_summary(
            input_left_cube="left.cub",
            input_right_cube="right.cub",
            input_left_key="left.key",
            input_right_key="right.key",
            output_dem_cube="dem.cub",
            total_pixels=100,
            matched_count=80,
            failed_match_count=20,
            rasterized_point_count=70,
            filled_cell_count=65,
            value_type="radius_m",
            datum_radius_m=None,
            ncc_threshold=0.7,
            polynomial_order=2,
            dx_r_squared=0.95,
            dy_r_squared=0.93,
            key_points_used_for_prior=42,
            prior_fallback=None,
            nodata_value=-9999.0,
            aggregation="median",
            max_error_m=10.0,
            min_sepang_deg=0.5,
            triangulation_counters={
                "success_count": 70,
                "failed_elevation_count": 5,
            },
        )

        self.assertEqual(summary["pipeline"], "from-dense-ncc")
        self.assertEqual(summary["total_pixels"], 100)
        self.assertEqual(summary["matched_count"], 80)
        self.assertEqual(summary["dx_r_squared"], 0.95)
        self.assertEqual(summary["key_points_used_for_prior"], 42)
        self.assertEqual(summary["success_count"], 70)
        self.assertEqual(summary["failed_elevation_count"], 5)
        for key in (
            "input_left_cube",
            "input_right_cube",
            "input_left_key",
            "input_right_key",
            "output_dem_cube",
            "value_type",
            "ncc_threshold",
            "polynomial_order",
            "dy_r_squared",
            "prior_fallback",
            "nodata_value",
            "aggregation",
            "max_error_m",
            "min_sepang_deg",
            "rasterized_point_count",
            "filled_cell_count",
        ):
            self.assertIn(key, summary)


class DemExtractDenseNCCCliUnitTest(unittest.TestCase):
    def test_from_dense_ncc_requires_projection_choice(self):
        from dem_extract.isis_stereo_dem import build_argument_parser

        parser = build_argument_parser()
        with self.assertRaises(SystemExit):
            with redirect_stderr(StringIO()):
                parser.parse_args(
                    [
                        "from-dense-ncc",
                        "left.cub",
                        "right.cub",
                        "left.key",
                        "right.key",
                        "dem.cub",
                    ]
                )

    def test_from_dense_ncc_parses_all_options(self):
        from dem_extract.isis_stereo_dem import build_argument_parser

        parser = build_argument_parser()
        args = parser.parse_args(
            [
                "from-dense-ncc",
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "dem.cub",
                "--use-left-projection",
                "--ncc-window",
                "15",
                "--ncc-search-range",
                "3",
                "--ncc-threshold",
                "0.75",
                "--no-subpixel",
                "--save-disparity",
                "disparity.cub",
                "--value-type",
                "height_m",
                "--datum-radius-m",
                "3396190",
                "--aggregation",
                "mean",
                "--nodata-value",
                "-9999",
                "--polynomial-order",
                "1",
                "--min-key-points",
                "10",
                "--chunk-size-lines",
                "50",
            ]
        )

        self.assertEqual(args.command, "from-dense-ncc")
        self.assertEqual(args.ncc_window, 15)
        self.assertEqual(args.ncc_search_range, 3)
        self.assertEqual(args.ncc_threshold, 0.75)
        self.assertTrue(args.no_subpixel)
        self.assertEqual(args.save_disparity, "disparity.cub")
        self.assertEqual(args.value_type, "height_m")
        self.assertEqual(args.datum_radius_m, 3396190.0)
        self.assertEqual(args.aggregation, "mean")
        self.assertEqual(args.polynomial_order, 1)
        self.assertEqual(args.min_key_points, 10)
        self.assertEqual(args.chunk_size_lines, 50)
        self.assertTrue(args.use_left_projection)

    def test_cli_script_help_shows_from_dense_ncc(self):
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
        self.assertIn("from-dense-ncc", result.stdout)


class DemExtractDenseNCCPackageExportsUnitTest(unittest.TestCase):
    def test_package_exposes_dense_ncc_helpers(self):
        from dem_extract import (
            DisparityModel,
            NCCMatchOptions,
            count_disparity_stats,
            dense_ncc_match,
            dense_triangulate_from_disparity,
            fit_disparity_model,
            write_disparity_cube,
        )

        self.assertTrue(callable(dense_ncc_match))
        self.assertTrue(callable(dense_triangulate_from_disparity))
        self.assertTrue(callable(fit_disparity_model))
        self.assertTrue(callable(count_disparity_stats))
        self.assertTrue(callable(write_disparity_cube))
        self.assertEqual(NCCMatchOptions().window_size, 21)
        self.assertEqual(
            DisparityModel(
                dx_coeffs=np.array([0.0]),
                dy_coeffs=np.array([0.0]),
                order=0,
                dx_r_squared=0.0,
                dy_r_squared=0.0,
            ).order,
            0,
        )


class DemExtractPipelineUnitTest(unittest.TestCase):
    def setUp(self):
        self.workspace = PROJECT_ROOT / "build" / "dem_extract_pipeline_tests"
        self.workspace.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        for path in sorted(self.workspace.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        if self.workspace.exists():
            self.workspace.rmdir()

    def write_config(self, payload: dict) -> Path:
        path = self.workspace / "dem_config.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_image_match_options_merge_common_and_route_overrides(self):
        from dem_extract import dem_pipeline

        config_path = self.write_config(
            {
                "ImageMatch": {
                    "sub_block_size_x": 512,
                    "sub_block_size_y": 256,
                    "overlap_size_x": 32,
                    "overlap_size_y": 16,
                    "valid_pixel_percent_threshold": 0.05,
                    "matcher_method": "bf",
                },
                "OriginalImageMatch": {
                    "matcher_method": "flann",
                    "valid_pixel_percent_threshold": 0.0,
                },
            }
        )

        options = dem_pipeline.image_match_options_for_route(config_path, "ori")

        self.assertEqual(options["block_width"], 512)
        self.assertEqual(options["block_height"], 256)
        self.assertEqual(options["overlap_x"], 32)
        self.assertEqual(options["overlap_y"], 16)
        self.assertEqual(options["matcher_method"], "flann")
        self.assertEqual(options["valid_pixel_percent_threshold"], 0.0)

    def test_image_match_options_accept_camel_case_route_overrides(self):
        from dem_extract import dem_pipeline

        config_path = self.write_config(
            {
                "ImageMatch": {
                    "sub_block_size_x": 512,
                    "matcher_method": "bf",
                },
                "OriginalImageMatch": {
                    "subBlockSizeX": 640,
                    "matcherMethod": "flann",
                    "validPixelPercentThreshold": 0.25,
                },
                "DomImageMatch": {
                    "writeMatchVisualization": True,
                    "previewCacheSource": "manual",
                    "visualizationTargetLongEdge": 1024,
                },
            }
        )

        ori_options = dem_pipeline.image_match_options_for_route(config_path, "ori")
        dom_options = dem_pipeline.image_match_options_for_route(config_path, "dom")

        self.assertEqual(ori_options["block_width"], 640)
        self.assertEqual(ori_options["matcher_method"], "flann")
        self.assertEqual(ori_options["valid_pixel_percent_threshold"], 0.25)
        self.assertEqual(dom_options["block_width"], 512)
        self.assertTrue(dom_options["write_match_visualization"])
        self.assertEqual(dom_options["preview_cache_source"], "manual")
        self.assertEqual(dom_options["visualization_target_long_edge"], 1024)

    def test_run_from_ori_match_dispatches_matching_then_dem(self):
        from dem_extract import dem_pipeline

        config_path = self.write_config(
            {
                "DemExtract": {"aggregation": "mean", "nodata_value": -1.0},
                "ImageMatch": {"matcher_method": "bf", "sub_block_size_x": 128},
                "KeyRefinement": {"enabled": True, "stages": ["maximum_correlation", "gruen"]},
            }
        )
        args = dem_pipeline.build_argument_parser().parse_args(
            [
                "--work-dir",
                str(self.workspace / "work"),
                "--config",
                str(config_path),
                "from-ori-match-dem",
                "--left-cube",
                "left.cub",
                "--right-cube",
                "right.cub",
                "--map-template-cube",
                "template.cub",
            ]
        )
        calls = []
        original_match = dem_pipeline.match_ori_pair_to_key_files
        original_dem = dem_pipeline.isis_stereo_dem.run_from_key
        try:
            def fake_match(left_cube, right_cube, left_output_key, right_output_key, **kwargs):
                calls.append(("match", left_cube, right_cube, str(left_output_key), str(right_output_key), kwargs))
                return {"matched_point_count": 2}

            def fake_dem(dem_args):
                calls.append(
                    (
                        "dem",
                        dem_args.left_key,
                        dem_args.right_key,
                        dem_args.aggregation,
                        dem_args.nodata_value,
                        tuple(dem_args.refine_stage),
                        dem_args.refined_left_key_output,
                        dem_args.refined_right_key_output,
                    )
                )
                return {"success_count": 2, "filled_cell_count": 1}

            dem_pipeline.match_ori_pair_to_key_files = fake_match
            dem_pipeline.isis_stereo_dem.run_from_key = fake_dem

            result = dem_pipeline.run_pipeline(args)
        finally:
            dem_pipeline.match_ori_pair_to_key_files = original_match
            dem_pipeline.isis_stereo_dem.run_from_key = original_dem

        self.assertEqual(result["mode"], "from-ori-match-dem")
        self.assertEqual(calls[0][0], "match")
        self.assertEqual(calls[0][5]["block_width"], 128)
        self.assertEqual(calls[1][0], "dem")
        self.assertEqual(calls[1][3], "mean")
        self.assertEqual(calls[1][4], -1.0)
        self.assertEqual(calls[1][5], ("maximum_correlation", "gruen"))
        self.assertIn("keys_refined", calls[1][6])
        self.assertIn("keys_refined", calls[1][7])
        self.assertTrue((self.workspace / "work" / "reports" / "pipeline_summary.json").exists())

    def test_parser_exposes_from_ori_match_dem_alias(self):
        from dem_extract import dem_pipeline

        parser = dem_pipeline.build_argument_parser()
        args = parser.parse_args(
            [
                "from-ori-match-dem",
                "--left-cube",
                "left.cub",
                "--right-cube",
                "right.cub",
                "--map-template-cube",
                "template.cub",
            ]
        )

        self.assertEqual(args.command, "from-ori-match-dem")
        self.assertEqual(args.left_cube, "left.cub")
        self.assertEqual(args.right_cube, "right.cub")
        self.assertEqual(args.map_template_cube, "template.cub")

    def test_run_from_dom_match_dispatches_dom_filters_then_dem(self):
        from dem_extract import dem_pipeline

        config_path = self.write_config(
            {
                "DemExtract": {"aggregation": "median"},
                "ImageMatch": {"matcher_method": "bf", "write_match_visualization": True},
                "DomImageMatch": {"valid_pixel_percent_threshold": 0.05},
                "DomToOriginal": {"merge_decimals": 2, "ransac_mode": "strict"},
            }
        )
        args = dem_pipeline.build_argument_parser().parse_args(
            [
                "--work-dir",
                str(self.workspace / "dom_work"),
                "--config",
                str(config_path),
                "from-dom-match",
                "--left-dom",
                "left_dom.cub",
                "--right-dom",
                "right_dom.cub",
                "--left-cube",
                "left.cub",
                "--right-cube",
                "right.cub",
                "--map-template-cube",
                "template.cub",
            ]
        )
        calls = []
        original_dom_match = dem_pipeline.match_dom_pair_to_key_files
        original_merge = dem_pipeline.merge_stereo_pair_key_files
        original_ransac = dem_pipeline.filter_stereo_pair_key_files_with_ransac
        original_dom2ori = dem_pipeline.convert_paired_dom_keypoints_to_original
        original_dem = dem_pipeline.isis_stereo_dem.run_from_key
        try:
            def fake_dom_match(left_dom, right_dom, left_key, right_key, metadata_output=None, **kwargs):
                calls.append(("dom_match", left_dom, right_dom, str(left_key), str(right_key), str(metadata_output), kwargs))
                return {"point_count": 3}

            def fake_merge(left_key, right_key, left_output, right_output, decimals=3):
                calls.append(("merge", str(left_key), str(right_key), str(left_output), str(right_output), decimals))
                return {"input_count": 3, "unique_count": 2}

            def fake_ransac(left_key, right_key, left_output, right_output, **kwargs):
                calls.append(("ransac", str(left_key), str(right_key), str(left_output), str(right_output), kwargs))
                return {"status": "ok", "retained_count": 2}

            def fake_dom2ori(left_key, right_key, left_dom, right_dom, left_cube, right_cube, left_output, right_output):
                calls.append(("dom2ori", str(left_key), str(right_key), str(left_output), str(right_output)))
                return {"left_conversion": {"success_count": 2}, "right_conversion": {"success_count": 2}}

            def fake_dem(dem_args):
                calls.append(("dem", dem_args.left_key, dem_args.right_key))
                return {"success_count": 2, "filled_cell_count": 1}

            dem_pipeline.match_dom_pair_to_key_files = fake_dom_match
            dem_pipeline.merge_stereo_pair_key_files = fake_merge
            dem_pipeline.filter_stereo_pair_key_files_with_ransac = fake_ransac
            dem_pipeline.convert_paired_dom_keypoints_to_original = fake_dom2ori
            dem_pipeline.isis_stereo_dem.run_from_key = fake_dem

            result = dem_pipeline.run_pipeline(args)
        finally:
            dem_pipeline.match_dom_pair_to_key_files = original_dom_match
            dem_pipeline.merge_stereo_pair_key_files = original_merge
            dem_pipeline.filter_stereo_pair_key_files_with_ransac = original_ransac
            dem_pipeline.convert_paired_dom_keypoints_to_original = original_dom2ori
            dem_pipeline.isis_stereo_dem.run_from_key = original_dem

        self.assertEqual(result["mode"], "from-dom-match")
        self.assertEqual([call[0] for call in calls], ["dom_match", "merge", "ransac", "dom2ori", "dem"])
        self.assertEqual(calls[1][-1], 2)
        self.assertEqual(calls[2][-1]["ransac_mode"], "strict")
        self.assertIn("keys_ori", calls[-1][1])
        self.assertTrue((self.workspace / "dom_work" / "reports" / "dom2ori_summary.json").exists())


if __name__ == "__main__":
    unittest.main()
