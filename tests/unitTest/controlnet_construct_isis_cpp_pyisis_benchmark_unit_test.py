"""Unit tests for the ISIS C++ vs PyISIS benchmark config model.

Author: Geng Xun
Created: 2026-06-09
Last Modified: 2026-06-18
Updated: 2026-06-09  Geng Xun added coverage for benchmark report generation without matplotlib.
Updated: 2026-06-18  Geng Xun made benchmark command and script-mode tests portable on Windows.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
import stat
import subprocess
import unittest
from unittest import mock


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import temporary_directory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.experiments import isis_cpp_pyisis_benchmark as benchmark


def _path_text(path: str) -> str:
    return str(Path(path))


def _require_directory_symlink(test_case: unittest.TestCase, temp_dir: Path) -> None:
    probe_target = temp_dir / "symlink_probe_target"
    probe_link = temp_dir / "symlink_probe_link"
    probe_target.mkdir()
    try:
        probe_link.symlink_to(probe_target, target_is_directory=True)
    except OSError as exc:
        test_case.skipTest(f"directory symlinks are unavailable in this Windows session: {exc}")
    else:
        probe_link.unlink()
        probe_target.rmdir()


class _FakeCamera:
    def __init__(self):
        self._sample = None
        self._line = None
        self.set_image_calls = []

    def samples(self):
        return 21

    def lines(self):
        return 21

    def set_image(self, sample, line):
        index = len(self.set_image_calls)
        self.set_image_calls.append((sample, line))
        if index == 2:
            return False
        self._sample = sample
        self._line = line
        return True

    def universal_latitude(self):
        return self._line / 100.0

    def universal_longitude(self):
        return self._sample / 100.0

    def set_universal_ground(self, latitude, longitude):
        self._line = latitude * 100.0
        self._sample = longitude * 100.0
        return True

    def sun_azimuth(self):
        return self._sample + self._line

    def incidence_angle(self):
        return 90.0 - (self._sample - self._line)

    def sample(self):
        return self._sample

    def line(self):
        return self._line


class _FakeCube:
    def __init__(self):
        self.open_args = None
        self.closed = False
        self.fake_camera = _FakeCamera()

    def open(self, path, mode):
        self.open_args = (path, mode)

    def camera(self):
        return self.fake_camera

    def sample_count(self):
        return 21

    def line_count(self):
        return 21

    def close(self):
        self.closed = True


class _FakeSolarCamera(_FakeCamera):
    def set_image(self, sample, line):
        self.set_image_calls.append((sample, line))
        self._sample = sample
        self._line = line
        return True


class _FakeSolarCube(_FakeCube):
    def __init__(self):
        super().__init__()
        self.fake_camera = _FakeSolarCamera()


class _FakeControlMeasure:
    def __init__(self, serial, sample, line):
        self._serial = serial
        self._sample = sample
        self._line = line

    def get_cube_serial_number(self):
        return self._serial

    def get_sample(self):
        return self._sample

    def get_line(self):
        return self._line

    def get_type(self):
        return "Candidate"

    def is_ignored(self):
        return False

    def is_edit_locked(self):
        return False


class _FakeControlPoint:
    def __init__(self, point_id, measures):
        self._point_id = point_id
        self._measures = measures

    def get_id(self):
        return self._point_id

    def get_type(self):
        return "Free"

    def is_ignored(self):
        return False

    def is_edit_locked(self):
        return False

    def get_num_measures(self):
        return len(self._measures)

    def get_measure(self, index):
        return self._measures[index]


class _FakeControlNet:
    def __init__(self, path):
        self.path = path
        self._points = [
            _FakeControlPoint(
                "P1",
                [
                    _FakeControlMeasure("SERIAL_A", 1.0, 2.0),
                    _FakeControlMeasure("SERIAL_B", 3.0, 4.0),
                ],
            ),
            _FakeControlPoint("P2", [_FakeControlMeasure("SERIAL_A", 5.0, 6.0)]),
        ]

    def get_num_points(self):
        return len(self._points)

    def get_num_measures(self):
        return sum(point.get_num_measures() for point in self._points)

    def get_num_valid_points(self):
        return 1

    def get_num_valid_measures(self):
        return 2

    def get_point(self, index):
        return self._points[index]


class _FakeControlNetWithoutValidCounts:
    def __init__(self, path):
        self.path = path
        self._points = [
            _FakeControlPoint("P1", [_FakeControlMeasure("SERIAL_A", 1.0, 2.0)]),
        ]

    def get_num_points(self):
        return len(self._points)

    def get_point(self, index):
        return self._points[index]


class _FakeIpModule:
    def __init__(self):
        self.cubes = []
        self.control_nets = []

    def Cube(self):
        cube = _FakeCube()
        self.cubes.append(cube)
        return cube

    def ControlNet(self, path):
        control_net = _FakeControlNet(path)
        self.control_nets.append(control_net)
        return control_net


class _FakeIpModuleWithoutValidCounts(_FakeIpModule):
    def ControlNet(self, path):
        control_net = _FakeControlNetWithoutValidCounts(path)
        self.control_nets.append(control_net)
        return control_net


class _FakeUniversalGroundMap:
    class CameraPriority:
        ProjectionFirst = object()
        CameraFirst = object()

    def __init__(self, cube, priority):
        self.cube = cube
        self.priority = priority
        self._sample = None
        self._line = None

    def set_image(self, sample, line):
        self._sample = sample
        self._line = line
        return True

    def universal_latitude(self):
        return self._line / 100.0

    def universal_longitude(self):
        return self._sample / 100.0

    def set_universal_ground(self, latitude, longitude):
        self._line = latitude * 100.0
        self._sample = longitude * 100.0
        return True

    def sample(self):
        return self._sample

    def line(self):
        return self._line


class _FakeIpModuleWithGroundMap(_FakeIpModule):
    UniversalGroundMap = _FakeUniversalGroundMap

    def Cube(self):
        cube = _FakeSolarCube()
        self.cubes.append(cube)
        return cube


class _FakeSolarIpModule(_FakeIpModule):
    def Cube(self):
        cube = _FakeSolarCube()
        self.cubes.append(cube)
        return cube


def _write_benchmark_config(path: Path) -> None:
    local_cube = path.parent / "local.cub"
    local_cube.write_text("fixture\n", encoding="utf-8")
    local_dom = path.parent / "dom.cub"
    local_dom.write_text("fixture\n", encoding="utf-8")
    path.write_text(
        json.dumps(
            {
                "run_id": "unit_benchmark",
                "description": "unit benchmark config",
                "execution": {
                    "cpp_benchmark_path": "tools/cpp_benchmark",
                    "repeat_count": 1,
                    "keep_intermediate_json": True,
                },
                "camera_tasks": [
                    {
                        "label": "config_relative_camera",
                        "cube_path": "local.cub",
                        "sample_step": 7,
                        "line_step": 11,
                        "max_points": 13,
                        "top_error_count": 5,
                    },
                    {
                        "label": "repo_relative_camera",
                        "cube_path": "tests/data/lronacpho/M143947267L.cal.echo.crop.cub",
                    },
                ],
                "controlnet_tasks": [
                    {
                        "label": "controlnet_fixture",
                        "net_path": "tests/data/threeImageNetwork/controlnetwork.net",
                    }
                ],
                "dom_ori_tasks": [
                    {
                        "label": "dom_ori_fixture",
                        "dom_path": "dom.cub",
                        "original_path": "local.cub",
                        "point_count": 9,
                        "top_error_count": 3,
                    }
                ],
                "solar_geometry_tasks": [
                    {
                        "label": "solar_fixture",
                        "cube_path": "local.cub",
                        "point_count": 9,
                        "top_error_count": 3,
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


class IsisCppPyisisBenchmarkConfigUnitTest(unittest.TestCase):
    def test_load_benchmark_config_resolves_paths_and_preserves_fields(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)

            config = benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

        self.assertEqual(config.run_id, "unit_benchmark")
        self.assertEqual(config.description, "unit benchmark config")
        self.assertEqual(config.config_path, config_path.resolve())
        self.assertEqual(config.execution.cpp_benchmark_path, PROJECT_ROOT / "tools/cpp_benchmark")
        self.assertEqual(config.execution.repeat_count, 1)
        self.assertTrue(config.execution.keep_intermediate_json)

        self.assertEqual(len(config.camera_tasks), 2)
        self.assertEqual(config.camera_tasks[0].label, "config_relative_camera")
        self.assertEqual(config.camera_tasks[0].cube_path, (config_path.parent / "local.cub").resolve())
        self.assertEqual(config.camera_tasks[0].sample_step, 7)
        self.assertEqual(config.camera_tasks[0].line_step, 11)
        self.assertEqual(config.camera_tasks[0].max_points, 13)
        self.assertEqual(config.camera_tasks[0].top_error_count, 5)
        self.assertEqual(
            config.camera_tasks[1].cube_path,
            PROJECT_ROOT / "tests/data/lronacpho/M143947267L.cal.echo.crop.cub",
        )

        self.assertEqual(len(config.controlnet_tasks), 1)
        self.assertEqual(config.controlnet_tasks[0].label, "controlnet_fixture")
        self.assertEqual(
            config.controlnet_tasks[0].net_path,
            PROJECT_ROOT / "tests/data/threeImageNetwork/controlnetwork.net",
        )
        self.assertEqual(len(config.dom_ori_tasks), 1)
        self.assertEqual(config.dom_ori_tasks[0].label, "dom_ori_fixture")
        self.assertEqual(config.dom_ori_tasks[0].dom_path, (config_path.parent / "dom.cub").resolve())
        self.assertEqual(config.dom_ori_tasks[0].original_path, (config_path.parent / "local.cub").resolve())
        self.assertEqual(config.dom_ori_tasks[0].point_count, 9)
        self.assertEqual(config.dom_ori_tasks[0].top_error_count, 3)
        self.assertEqual(config.dom_ori_tasks[0].sampling_mode, "ori_roundtrip")
        self.assertEqual(len(config.solar_geometry_tasks), 1)
        self.assertEqual(config.solar_geometry_tasks[0].label, "solar_fixture")
        self.assertEqual(config.solar_geometry_tasks[0].cube_path, (config_path.parent / "local.cub").resolve())
        self.assertEqual(config.solar_geometry_tasks[0].point_count, 9)
        self.assertEqual(config.solar_geometry_tasks[0].top_error_count, 3)

    def test_generate_camera_samples_includes_edges_and_respects_max_points(self):
        samples = benchmark.generate_camera_samples(
            sample_count=35,
            line_count=45,
            sample_step=10,
            line_step=20,
            max_points=6,
        )

        self.assertEqual(
            samples,
            (
                benchmark.CameraSample(0, 1.0, 1.0),
                benchmark.CameraSample(1, 11.0, 1.0),
                benchmark.CameraSample(2, 21.0, 1.0),
                benchmark.CameraSample(3, 31.0, 1.0),
                benchmark.CameraSample(4, 35.0, 1.0),
                benchmark.CameraSample(5, 1.0, 21.0),
            ),
        )

    def test_generate_camera_samples_uses_step_grid_without_midpoint_insertion(self):
        samples = benchmark.generate_camera_samples(
            sample_count=11,
            line_count=11,
            sample_step=10,
            line_step=10,
        )

        self.assertEqual(
            samples,
            (
                benchmark.CameraSample(0, 1.0, 1.0),
                benchmark.CameraSample(1, 11.0, 1.0),
                benchmark.CameraSample(2, 1.0, 11.0),
                benchmark.CameraSample(3, 11.0, 11.0),
            ),
        )

    def test_generate_regular_grid_samples_spreads_exact_point_count_over_extent(self):
        samples = benchmark.generate_regular_grid_samples(
            sample_count=21,
            line_count=21,
            point_count=9,
        )

        self.assertEqual(len(samples), 9)
        self.assertEqual(samples[0], benchmark.CameraSample(0, 1.0, 1.0))
        self.assertEqual(samples[4], benchmark.CameraSample(4, 11.0, 11.0))
        self.assertEqual(samples[8], benchmark.CameraSample(8, 21.0, 21.0))

    def test_load_benchmark_config_rejects_duplicate_labels_across_task_types(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["controlnet_tasks"][0]["label"] = "config_relative_camera"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Duplicate task label"):
                benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

    def test_load_benchmark_config_rejects_duplicate_labels_across_new_task_types(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["solar_geometry_tasks"][0]["label"] = "dom_ori_fixture"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Duplicate task label"):
                benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

    def test_load_benchmark_config_rejects_nonpositive_sample_step(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["camera_tasks"][0]["sample_step"] = 0
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "sample_step must be positive"):
                benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

    def test_load_benchmark_config_rejects_unimplemented_repeat_count(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["execution"]["repeat_count"] = 2
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "repeat_count values other than 1 are not supported"):
                benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

    def test_load_benchmark_config_rejects_unimplemented_keep_intermediate_json_false(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["execution"]["keep_intermediate_json"] = False
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "keep_intermediate_json=false is not supported"):
                benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

    def test_load_benchmark_config_rejects_path_traversal_run_id(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["run_id"] = "../escape"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "run_id must match"):
                benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

    def test_load_benchmark_config_rejects_path_traversal_task_label(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["camera_tasks"][0]["label"] = "bad/label"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "label must match"):
                benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

    def test_load_benchmark_config_requires_at_least_one_task(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["camera_tasks"] = []
            payload["controlnet_tasks"] = []
            payload["dom_ori_tasks"] = []
            payload["solar_geometry_tasks"] = []
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError,
                "At least one camera task or controlnet task is required",
            ):
                benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

    def test_example_config_loads_with_camera_and_controlnet_tasks(self):
        config_path = (
            PROJECT_ROOT
            / "examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json"
        )

        config = benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

        self.assertEqual(config.run_id, "lro_nac_pyisis_cpp_20260523")
        self.assertGreaterEqual(len(config.camera_tasks), 1)
        self.assertGreaterEqual(len(config.controlnet_tasks), 1)

    def test_run_pyisis_camera_task_round_trips_generated_camera_points(self):
        fake_ip = _FakeIpModule()
        task = benchmark.CameraTaskConfig(
            label="fake_camera",
            cube_path=Path("/tmp/fake.cub"),
            sample_step=10,
            line_step=10,
        )

        result = benchmark.run_pyisis_camera_task(task, ip_module=fake_ip)

        self.assertEqual(fake_ip.cubes[0].open_args, (_path_text("/tmp/fake.cub"), "r"))
        self.assertTrue(fake_ip.cubes[0].closed)
        self.assertEqual(fake_ip.cubes[0].fake_camera.set_image_calls, [
            (1.0, 1.0),
            (11.0, 1.0),
            (21.0, 1.0),
            (1.0, 11.0),
            (11.0, 11.0),
            (21.0, 11.0),
            (1.0, 21.0),
            (11.0, 21.0),
            (21.0, 21.0),
        ])
        self.assertEqual(result["task_type"], "camera")
        self.assertEqual(result["implementation"], "pyisis")
        self.assertEqual(result["label"], "fake_camera")
        self.assertEqual(result["input_point_count"], 9)
        self.assertEqual(result["successful_point_count"], 8)
        self.assertEqual(result["failed_set_image_count"], 1)
        self.assertEqual(result["failed_set_universal_ground_count"], 0)
        self.assertEqual(result["first_point_index"], 0)
        self.assertIn("points", result)
        self.assertEqual(len(result["points"]), 8)
        self.assertEqual(
            result["points"][0],
            {
                "index": 0,
                "input_sample": 1.0,
                "input_line": 1.0,
                "latitude": 0.01,
                "longitude": 0.01,
                "roundtrip_sample": 1.0,
                "roundtrip_line": 1.0,
            },
        )
        self.assertGreaterEqual(result["core_seconds"], 0.0)
        self.assertIn("average_successful_point_seconds", result)
        self.assertIsNotNone(result["average_successful_point_seconds"])
        self.assertAlmostEqual(
            result["average_successful_point_seconds"],
            result["core_seconds"] / len(result["points"]),
        )

    def test_run_pyisis_camera_task_includes_edges_for_three_by_three_grid(self):
        fake_ip = _FakeIpModule()
        task = benchmark.CameraTaskConfig(
            label="fake_camera_edges",
            cube_path=Path("/tmp/fake.cub"),
            sample_step=10,
            line_step=10,
        )

        result = benchmark.run_pyisis_camera_task(task, ip_module=fake_ip)

        self.assertEqual(result["input_point_count"], 9)

    def test_run_pyisis_controlnet_task_loads_and_traverses_control_net(self):
        fake_ip = _FakeIpModule()
        task = benchmark.ControlNetTaskConfig(
            label="fake_controlnet",
            net_path=Path("/tmp/fake.net"),
        )

        result = benchmark.run_pyisis_controlnet_task(task, ip_module=fake_ip)

        self.assertEqual(fake_ip.control_nets[0].path, _path_text("/tmp/fake.net"))
        self.assertEqual(result["task_type"], "controlnet")
        self.assertEqual(result["implementation"], "pyisis")
        self.assertEqual(result["label"], "fake_controlnet")
        self.assertEqual(result["point_count"], 2)
        self.assertEqual(result["measure_count"], 3)
        self.assertEqual(result["valid_point_count"], 1)
        self.assertEqual(result["valid_measure_count"], 2)
        self.assertEqual(result["serial_measure_counts"], {"SERIAL_A": 2, "SERIAL_B": 1})
        self.assertGreaterEqual(result["load_seconds"], 0.0)
        self.assertGreaterEqual(result["traverse_seconds"], 0.0)
        self.assertGreaterEqual(result["core_seconds"], result["load_seconds"])
        self.assertGreaterEqual(result["core_seconds"], result["traverse_seconds"])

    def test_run_pyisis_controlnet_task_returns_none_for_missing_valid_count_apis(self):
        fake_ip = _FakeIpModuleWithoutValidCounts()
        task = benchmark.ControlNetTaskConfig(
            label="fake_controlnet_no_valid_counts",
            net_path=Path("/tmp/fake-no-valid.net"),
        )

        result = benchmark.run_pyisis_controlnet_task(task, ip_module=fake_ip)

        self.assertEqual(result["point_count"], 1)
        self.assertEqual(result["measure_count"], 1)
        self.assertIsNone(result["valid_point_count"])
        self.assertIsNone(result["valid_measure_count"])

    def test_run_pyisis_dom_ori_task_uses_ori_seed_roundtrip_without_full_point_dump_by_default(self):
        fake_ip = _FakeIpModuleWithGroundMap()
        task = benchmark.DomOriTaskConfig(
            label="fake_dom_ori",
            dom_path=Path("/tmp/dom.cub"),
            original_path=Path("/tmp/original.cub"),
            point_count=9,
            top_error_count=3,
        )

        result = benchmark.run_pyisis_dom_ori_task(task, ip_module=fake_ip)

        self.assertEqual(result["task_type"], "dom_ori")
        self.assertEqual(result["implementation"], "pyisis")
        self.assertEqual(result["label"], "fake_dom_ori")
        self.assertEqual(result["sampling_mode"], "ori_roundtrip")
        self.assertEqual(result["input_point_count"], 9)
        self.assertEqual(result["ori_seed_point_count"], 9)
        self.assertEqual(result["ori_to_dom_successful_count"], 9)
        self.assertEqual(result["ori_to_dom_failed_count"], 0)
        self.assertEqual(result["dom_ori_successful_count"], 9)
        self.assertEqual(result["dom_ori_failed_count"], 0)
        self.assertEqual(result["roundtrip_successful_count"], 9)
        self.assertEqual(result["roundtrip_success_rate"], 1.0)
        self.assertEqual(result["successful_point_count"], 9)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(result["failed_ori_set_image_count"], 0)
        self.assertEqual(result["failed_ori_ground_not_finite_count"], 0)
        self.assertEqual(result["failed_ori_to_dom_projection_count"], 0)
        self.assertEqual(result["failed_dom_point_out_of_bounds_count"], 0)
        self.assertEqual(result["failed_dom_lookup_count"], 0)
        self.assertEqual(result["failed_dom_to_ori_projection_count"], 0)
        self.assertGreaterEqual(result["ori_to_dom_seconds"], 0.0)
        self.assertGreaterEqual(result["dom_to_ori_seconds"], 0.0)
        self.assertAlmostEqual(result["core_seconds"], result["ori_to_dom_seconds"] + result["dom_to_ori_seconds"])
        self.assertGreater(result["points_per_second"], 0.0)
        self.assertGreater(result["roundtrip_points_per_second"], 0.0)
        self.assertNotIn("points", result)
        self.assertLessEqual(len(result["top_errors"]), 3)
        self.assertEqual(result["top_errors"][0]["index"], 0)
        self.assertEqual(result["top_errors"][0]["pixel_error"], 0.0)
        self.assertEqual(result["sample_abs_max"], 0.0)
        self.assertEqual(result["line_abs_max"], 0.0)
        self.assertEqual(result["pixel_error_abs_max"], 0.0)

    def test_run_pyisis_solar_geometry_task_samples_pixel_angles_without_full_point_dump_by_default(self):
        fake_ip = _FakeSolarIpModule()
        task = benchmark.SolarGeometryTaskConfig(
            label="fake_solar",
            cube_path=Path("/tmp/original.cub"),
            point_count=9,
            top_error_count=3,
        )

        result = benchmark.run_pyisis_solar_geometry_task(task, ip_module=fake_ip)

        self.assertEqual(result["task_type"], "solar_geometry")
        self.assertEqual(result["implementation"], "pyisis")
        self.assertEqual(result["label"], "fake_solar")
        self.assertEqual(result["input_point_count"], 9)
        self.assertEqual(result["successful_point_count"], 9)
        self.assertEqual(result["failed_count"], 0)
        self.assertGreater(result["points_per_second"], 0.0)
        self.assertNotIn("points", result)
        self.assertEqual(result["top_errors"], [])
        self.assertEqual(result["azimuth_abs_max"], 0.0)
        self.assertEqual(result["elevation_abs_max"], 0.0)

    def test_load_cpp_result_rejects_non_dict_json(self):
        with temporary_directory() as temp_dir:
            result_path = temp_dir / "result.json"
            result_path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Expected cpp result"):
                benchmark.load_cpp_result(result_path)

    def test_load_cpp_result_rejects_wrong_implementation(self):
        with temporary_directory() as temp_dir:
            result_path = temp_dir / "result.json"
            result_path.write_text(json.dumps({"implementation": "pyisis"}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Expected cpp result"):
                benchmark.load_cpp_result(result_path)

    def test_load_cpp_result_accepts_cpp_result(self):
        with temporary_directory() as temp_dir:
            result_path = temp_dir / "result.json"
            result_path.write_text(
                json.dumps({"implementation": "cpp", "task_type": "camera"}),
                encoding="utf-8",
            )

            result = benchmark.load_cpp_result(result_path)

        self.assertEqual(result["task_type"], "camera")

    def test_cpp_controlnet_timing_includes_point_count_lookup(self):
        source_path = PROJECT_ROOT / "tools/benchmarks/isis_cpp_benchmark.cpp"
        source = source_path.read_text(encoding="utf-8")
        function_body = source.split("void write_controlnet_result", 1)[1].split("std::ofstream out", 1)[0]

        self.assertLess(
            function_body.index("const auto traverse_start"),
            function_body.index("control_net.GetNumPoints()"),
        )

    def test_cpp_controlnet_result_reports_file_size_and_measure_throughput(self):
        source_path = PROJECT_ROOT / "tools/benchmarks/isis_cpp_benchmark.cpp"
        source = source_path.read_text(encoding="utf-8")
        function_body = source.split("void write_controlnet_result", 1)[1].split("std::ofstream out", 1)[0]

        self.assertIn("file_size_bytes", function_body)
        self.assertIn("measures_per_second", function_body)

    def test_compare_camera_results_computes_stats_and_top_errors(self):
        py_result = {
            "points": [
                {
                    "index": 0,
                    "latitude": 1.0,
                    "longitude": 2.0,
                    "roundtrip_sample": 10.0,
                    "roundtrip_line": 20.0,
                },
                {
                    "index": 1,
                    "latitude": 2.0,
                    "longitude": 4.0,
                    "roundtrip_sample": 30.0,
                    "roundtrip_line": 40.0,
                },
                {
                    "index": 3,
                    "latitude": 10.0,
                    "longitude": 12.0,
                    "roundtrip_sample": 50.0,
                    "roundtrip_line": 60.0,
                },
            ]
        }
        cpp_result = {
            "points": [
                {
                    "index": 0,
                    "latitude": 1.5,
                    "longitude": 2.25,
                    "roundtrip_sample": 11.0,
                    "roundtrip_line": 20.5,
                },
                {
                    "index": 2,
                    "latitude": 9.0,
                    "longitude": 9.0,
                    "roundtrip_sample": 9.0,
                    "roundtrip_line": 9.0,
                },
                {
                    "index": 3,
                    "latitude": 8.0,
                    "longitude": 11.0,
                    "roundtrip_sample": 48.0,
                    "roundtrip_line": 59.0,
                },
            ]
        }

        comparison = benchmark.compare_camera_results(
            "camera_a",
            py_result,
            cpp_result,
            top_error_count=1,
        )

        self.assertEqual(comparison["label"], "camera_a")
        self.assertEqual(comparison["matched_point_count"], 2)
        self.assertEqual(comparison["missing_in_pyisis"], [2])
        self.assertEqual(comparison["missing_in_cpp"], [1])
        self.assertAlmostEqual(comparison["stats"]["latitude_abs_max"], 2.0)
        self.assertAlmostEqual(comparison["stats"]["latitude_abs_mean"], 1.25)
        self.assertAlmostEqual(comparison["stats"]["latitude_abs_rms"], ((0.5**2 + 2.0**2) / 2) ** 0.5)
        self.assertAlmostEqual(comparison["stats"]["longitude_abs_max"], 1.0)
        self.assertAlmostEqual(comparison["stats"]["sample_abs_max"], 2.0)
        self.assertAlmostEqual(comparison["stats"]["line_abs_max"], 1.0)
        self.assertEqual([row["index"] for row in comparison["top_errors"]], [3])
        self.assertAlmostEqual(comparison["top_errors"][0]["combined_error"], 6.0)

    def test_prepare_run_directory_writes_config_snapshot_manifest_and_dirs(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            config = benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

            run_dir = benchmark.prepare_run_directory(
                config,
                output_root=temp_dir / "out",
                dry_run=True,
            )

            self.assertEqual(run_dir, (temp_dir / "out" / "unit_benchmark").resolve())
            self.assertTrue((run_dir / "experiment_config.json").is_file())
            self.assertEqual(
                json.loads((run_dir / "experiment_config.json").read_text(encoding="utf-8")),
                json.loads(config_path.read_text(encoding="utf-8")),
            )
            manifest = json.loads((run_dir / "experiment_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["run_id"], "unit_benchmark")
            self.assertTrue(manifest["dry_run"])
            self.assertEqual(
                manifest["tasks"],
                [
                    "config_relative_camera",
                    "repo_relative_camera",
                    "controlnet_fixture",
                    "dom_ori_fixture",
                    "solar_fixture",
                ],
            )
            self.assertEqual(manifest["cpp_benchmark_path"], str(PROJECT_ROOT / "tools/cpp_benchmark"))
            self.assertRegex(manifest["created_at"], r"^\d{4}-\d{2}-\d{2}T.*\+00:00$")
            self.assertTrue((run_dir / "pyisis").is_dir())
            self.assertTrue((run_dir / "cpp").is_dir())
            self.assertTrue((run_dir / "reports").is_dir())

    def test_prepare_run_directory_removes_owned_stale_artifacts_only(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            config = benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)
            run_dir = temp_dir / "out" / "unit_benchmark"
            (run_dir / "pyisis").mkdir(parents=True)
            (run_dir / "cpp").mkdir()
            (run_dir / "reports").mkdir()
            (run_dir / "pyisis" / "stale.json").write_text("stale\n", encoding="utf-8")
            (run_dir / "cpp" / "stale.json").write_text("stale\n", encoding="utf-8")
            (run_dir / "reports" / "stale.csv").write_text("stale\n", encoding="utf-8")
            (run_dir / "experiment_config.json").write_text("old config\n", encoding="utf-8")
            (run_dir / "experiment_manifest.json").write_text("old manifest\n", encoding="utf-8")
            (run_dir / "custom-note.txt").write_text("keep me\n", encoding="utf-8")

            prepared_run_dir = benchmark.prepare_run_directory(
                config,
                output_root=temp_dir / "out",
                dry_run=True,
            )

            self.assertEqual(prepared_run_dir, run_dir.resolve())
            self.assertFalse((prepared_run_dir / "pyisis" / "stale.json").exists())
            self.assertFalse((prepared_run_dir / "cpp" / "stale.json").exists())
            self.assertFalse((prepared_run_dir / "reports" / "stale.csv").exists())
            self.assertEqual((prepared_run_dir / "custom-note.txt").read_text(encoding="utf-8"), "keep me\n")
            self.assertTrue((prepared_run_dir / "experiment_config.json").is_file())
            self.assertTrue((prepared_run_dir / "experiment_manifest.json").is_file())

    def test_prepare_run_directory_replaces_owned_symlink_without_removing_target(self):
        with temporary_directory() as temp_dir:
            _require_directory_symlink(self, temp_dir)
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            config = benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)
            run_dir = temp_dir / "out" / "unit_benchmark"
            external_target = temp_dir / "external_pyisis_target"
            external_target.mkdir()
            (external_target / "keep.txt").write_text("external\n", encoding="utf-8")
            run_dir.mkdir(parents=True)
            (run_dir / "pyisis").symlink_to(external_target, target_is_directory=True)

            prepared_run_dir = benchmark.prepare_run_directory(
                config,
                output_root=temp_dir / "out",
                dry_run=True,
            )

            self.assertFalse((prepared_run_dir / "pyisis").is_symlink())
            self.assertTrue((prepared_run_dir / "pyisis").is_dir())
            self.assertTrue(external_target.is_dir())
            self.assertEqual((external_target / "keep.txt").read_text(encoding="utf-8"), "external\n")

    def test_prepare_run_directory_replaces_symlinked_run_dir_without_removing_target(self):
        with temporary_directory() as temp_dir:
            _require_directory_symlink(self, temp_dir)
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            config = benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)
            output_root = temp_dir / "out"
            run_dir = output_root / "unit_benchmark"
            external_target = temp_dir / "external_run_dir_target"
            (external_target / "pyisis").mkdir(parents=True)
            (external_target / "pyisis" / "keep.txt").write_text("external\n", encoding="utf-8")
            output_root.mkdir()
            run_dir.symlink_to(external_target, target_is_directory=True)

            prepared_run_dir = benchmark.prepare_run_directory(
                config,
                output_root=output_root,
                dry_run=True,
            )

            self.assertEqual(prepared_run_dir, run_dir.resolve())
            self.assertEqual((external_target / "pyisis" / "keep.txt").read_text(encoding="utf-8"), "external\n")
            self.assertFalse(run_dir.is_symlink())
            self.assertTrue((run_dir / "pyisis").is_dir())
            self.assertFalse((run_dir / "pyisis").is_symlink())

    def test_write_summary_reports_writes_json_and_csv_schemas(self):
        results = [
            {
                "label": "camera_a",
                "task_type": "camera",
                "implementation": "pyisis",
                "status": "success",
                "core_seconds": 1.25,
                "wall_seconds": 1.5,
                "successful_point_count": 2,
            },
            {
                "label": "net_a",
                "task_type": "controlnet",
                "implementation": "cpp",
                "status": "success",
                "core_seconds": 2.0,
                "wall_seconds": 2.25,
                "point_count": 7,
                "measure_count": 11,
                "file_size_bytes": 12345,
                "measures_per_second": 5.5,
            },
            {
                "label": "dom_ori_a",
                "task_type": "dom_ori",
                "implementation": "pyisis",
                "status": "success",
                "core_seconds": 3.0,
                "ori_to_dom_seconds": 1.25,
                "dom_to_ori_seconds": 1.75,
                "successful_point_count": 100,
                "roundtrip_successful_count": 100,
                "roundtrip_success_rate": 1.0,
                "points_per_second": 33.3,
                "roundtrip_points_per_second": 33.3,
                "sample_abs_max": 0.0,
                "line_abs_max": 0.0,
                "pixel_error_abs_max": 0.0,
            },
            {
                "label": "solar_a",
                "task_type": "solar_geometry",
                "implementation": "cpp",
                "status": "success",
                "core_seconds": 4.0,
                "successful_point_count": 100,
                "points_per_second": 25.0,
                "azimuth_abs_max": 0.0,
                "elevation_abs_max": 0.0,
            },
        ]
        camera_comparisons = [
            {
                "label": "camera_a",
                "matched_point_count": 1,
                "missing_in_pyisis": [3, 5],
                "missing_in_cpp": [7],
                "stats": {
                    "latitude_abs_max": 0.5,
                    "longitude_abs_max": 0.25,
                    "sample_abs_max": 0.5,
                    "line_abs_max": 0.25,
                },
                "top_errors": [
                    {
                        "label": "camera_a",
                        "index": 4,
                        "combined_error": 1.5,
                        "latitude_abs": 0.5,
                        "longitude_abs": 0.25,
                        "sample_abs": 0.5,
                        "line_abs": 0.25,
                    }
                ],
            }
        ]

        with temporary_directory() as temp_dir:
            provenance = {
                "config_snapshot": "/tmp/run/experiment_config.json",
                "pyisis_import_path": "/tmp/isis_pybind/__init__.py",
                "cpp_benchmark_path": "/tmp/isis_cpp_benchmark",
                "ISISDATA": "/tmp/isisdata",
                "CONDA_DEFAULT_ENV": "asp360_new",
                "git_commit": "abc123",
            }
            benchmark.write_summary_reports(temp_dir, results, camera_comparisons, provenance=provenance)

            summary = json.loads((temp_dir / "reports" / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["results"], results)
            self.assertEqual(summary["camera_comparisons"], camera_comparisons)
            self.assertEqual(summary["provenance"], provenance)
            with (temp_dir / "reports" / "summary.csv").open(encoding="utf-8", newline="") as csv_file:
                rows = list(csv.DictReader(csv_file))
            self.assertEqual(rows[0]["label"], "camera_a")
            self.assertEqual(rows[0]["task_type"], "camera")
            self.assertEqual(rows[1]["label"], "net_a")
            self.assertEqual(rows[1]["task_type"], "controlnet")
            self.assertEqual(rows[1]["file_size_bytes"], "12345")
            self.assertEqual(rows[1]["measures_per_second"], "5.5")
            self.assertEqual(rows[2]["label"], "dom_ori_a")
            self.assertEqual(rows[2]["task_type"], "dom_ori")
            self.assertEqual(rows[2]["points_per_second"], "33.3")
            self.assertEqual(rows[2]["roundtrip_points_per_second"], "33.3")
            self.assertEqual(rows[2]["roundtrip_success_rate"], "1.0")
            self.assertEqual(rows[2]["ori_to_dom_seconds"], "1.25")
            self.assertEqual(rows[2]["dom_to_ori_seconds"], "1.75")
            self.assertEqual(rows[2]["pixel_error_abs_max"], "0.0")
            self.assertEqual(rows[3]["label"], "solar_a")
            self.assertEqual(rows[3]["task_type"], "solar_geometry")
            self.assertEqual(rows[3]["azimuth_abs_max"], "0.0")
            self.assertEqual(rows[3]["elevation_abs_max"], "0.0")
            self.assertEqual(rows[4]["label"], "camera_a")
            self.assertEqual(rows[4]["task_type"], "camera_comparison")
            self.assertEqual(rows[4]["implementation"], "comparison")
            self.assertEqual(rows[4]["matched_point_count"], "1")
            self.assertEqual(rows[4]["missing_in_pyisis_count"], "2")
            self.assertEqual(rows[4]["missing_in_cpp_count"], "1")
            self.assertEqual(rows[4]["latitude_abs_max"], "0.5")
            self.assertEqual(rows[4]["longitude_abs_max"], "0.25")
            self.assertEqual(rows[4]["sample_abs_max"], "0.5")
            self.assertEqual(rows[4]["line_abs_max"], "0.25")
            self.assertEqual(
                (temp_dir / "reports" / "camera_top_errors.csv").read_text(encoding="utf-8").splitlines(),
                [
                    "label,index,combined_error,latitude_abs,longitude_abs,sample_abs,line_abs",
                    "camera_a,4,1.5,0.5,0.25,0.5,0.25",
                ],
            )
            controlnet_summary = json.loads(
                (temp_dir / "reports" / "controlnet_summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(controlnet_summary["results"], [results[1]])
            self.assertEqual(controlnet_summary["provenance"], provenance)
            precision_summary = json.loads(
                (temp_dir / "reports" / "precision_comparison.json").read_text(encoding="utf-8")
            )
            self.assertEqual([row["label"] for row in precision_summary["dom_ori"]], ["dom_ori_a"])
            self.assertEqual(precision_summary["dom_ori"][0]["pixel_error_abs_max"], 0.0)
            self.assertEqual([row["label"] for row in precision_summary["solar_geometry"]], ["solar_a"])
            self.assertEqual(precision_summary["solar_geometry"][0]["azimuth_abs_max"], 0.0)
            self.assertEqual(precision_summary["provenance"], provenance)
            figure_skip_path = temp_dir / "reports" / "benchmark_figure_skipped.json"
            if figure_skip_path.is_file():
                figure_skip = json.loads(figure_skip_path.read_text(encoding="utf-8"))
                self.assertEqual(figure_skip["status"], "skipped")
                self.assertEqual(figure_skip["reason"], "matplotlib_unavailable")
            else:
                self.assertTrue((temp_dir / "reports" / "benchmark_figure.svg").is_file())
                self.assertTrue((temp_dir / "reports" / "benchmark_figure.pdf").is_file())
                self.assertTrue((temp_dir / "reports" / "benchmark_figure.tiff").is_file())

    def test_build_cpp_camera_command_includes_required_arguments(self):
        task = benchmark.CameraTaskConfig(
            label="camera_a",
            cube_path=Path("/tmp/input cube.cub"),
            sample_step=7,
            line_step=11,
            max_points=13,
        )

        command = benchmark.build_cpp_camera_command(
            Path("/tmp/cpp benchmark"),
            task,
            Path("/tmp/out/result.json"),
        )

        self.assertEqual(
            command,
            [
                _path_text("/tmp/cpp benchmark"),
                "camera",
                "--label",
                "camera_a",
                "--cube",
                _path_text("/tmp/input cube.cub"),
                "--sample-step",
                "7",
                "--line-step",
                "11",
                "--output",
                _path_text("/tmp/out/result.json"),
                "--max-points",
                "13",
            ],
        )

    def test_build_cpp_camera_command_omits_unconfigured_max_points(self):
        task = benchmark.CameraTaskConfig(
            label="camera_a",
            cube_path=Path("/tmp/input.cub"),
            sample_step=7,
            line_step=11,
        )

        command = benchmark.build_cpp_camera_command(
            Path("/tmp/cpp_benchmark"),
            task,
            Path("/tmp/out/result.json"),
        )

        self.assertNotIn("--max-points", command)

    def test_build_cpp_controlnet_command_includes_required_arguments(self):
        task = benchmark.ControlNetTaskConfig(
            label="net_a",
            net_path=Path("/tmp/control.net"),
        )

        command = benchmark.build_cpp_controlnet_command(
            Path("/tmp/cpp_benchmark"),
            task,
            Path("/tmp/out/result.json"),
        )

        self.assertEqual(
            command,
            [
                _path_text("/tmp/cpp_benchmark"),
                "controlnet",
                "--label",
                "net_a",
                "--net",
                _path_text("/tmp/control.net"),
                "--output",
                _path_text("/tmp/out/result.json"),
            ],
        )

    def test_build_cpp_dom_ori_command_includes_required_arguments(self):
        task = benchmark.DomOriTaskConfig(
            label="dom_ori_a",
            dom_path=Path("/tmp/dom.cub"),
            original_path=Path("/tmp/original.cub"),
            point_count=1000000,
            top_error_count=25,
        )

        command = benchmark.build_cpp_dom_ori_command(
            Path("/tmp/cpp_benchmark"),
            task,
            Path("/tmp/out/result.json"),
        )

        self.assertEqual(
            command,
            [
                _path_text("/tmp/cpp_benchmark"),
                "dom-ori",
                "--label",
                "dom_ori_a",
                "--dom",
                _path_text("/tmp/dom.cub"),
                "--original",
                _path_text("/tmp/original.cub"),
                "--point-count",
                "1000000",
                "--top-error-count",
                "25",
                "--sampling-mode",
                "ori_roundtrip",
                "--output",
                _path_text("/tmp/out/result.json"),
            ],
        )

    def test_build_cpp_dom_ori_command_preserves_direct_dom_diagnostic_mode(self):
        task = benchmark.DomOriTaskConfig(
            label="dom_ori_direct",
            dom_path=Path("/tmp/dom.cub"),
            original_path=Path("/tmp/original.cub"),
            point_count=10,
            sampling_mode="direct_dom",
        )

        command = benchmark.build_cpp_dom_ori_command(
            Path("/tmp/cpp_benchmark"),
            task,
            Path("/tmp/out/result.json"),
        )

        self.assertIn("--sampling-mode", command)
        self.assertEqual(command[command.index("--sampling-mode") + 1], "direct_dom")

    def test_build_cpp_solar_geometry_command_includes_required_arguments(self):
        task = benchmark.SolarGeometryTaskConfig(
            label="solar_a",
            cube_path=Path("/tmp/original.cub"),
            point_count=1000000,
            top_error_count=25,
        )

        command = benchmark.build_cpp_solar_geometry_command(
            Path("/tmp/cpp_benchmark"),
            task,
            Path("/tmp/out/result.json"),
        )

        self.assertEqual(
            command,
            [
                _path_text("/tmp/cpp_benchmark"),
                "solar-geometry",
                "--label",
                "solar_a",
                "--cube",
                _path_text("/tmp/original.cub"),
                "--point-count",
                "1000000",
                "--top-error-count",
                "25",
                "--output",
                _path_text("/tmp/out/result.json"),
            ],
        )

    def test_run_cpp_command_keep_going_records_failure_without_raising(self):
        command = [
            sys.executable,
            "-c",
            "import sys; print('out text'); print('err text', file=sys.stderr); sys.exit(7)",
        ]

        result = benchmark.run_cpp_command(command, keep_going=True, task_type="camera", label="camera_a")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["return_code"], 7)
        self.assertEqual(result["stdout"], "out text\n")
        self.assertEqual(result["stderr"], "err text\n")
        self.assertEqual(result["command"], command)
        self.assertEqual(result["implementation"], "cpp")
        self.assertEqual(result["task_type"], "camera")
        self.assertEqual(result["label"], "camera_a")
        self.assertGreaterEqual(result["wall_seconds"], 0.0)

    def test_run_cpp_command_fail_fast_raises_on_failure(self):
        command = [sys.executable, "-c", "import sys; sys.exit(3)"]

        with self.assertRaises(subprocess.CalledProcessError) as context:
            benchmark.run_cpp_command(command, keep_going=False)

        self.assertEqual(context.exception.returncode, 3)
        self.assertEqual(context.exception.cmd, command)

    def test_run_cpp_command_keep_going_records_launch_failure_without_raising(self):
        with temporary_directory() as temp_dir:
            command = [str(temp_dir / "definitely_missing_cpp_benchmark"), "camera"]

            result = benchmark.run_cpp_command(
                command,
                keep_going=True,
                task_type="camera",
                label="missing_binary",
            )

        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["return_code"])
        self.assertEqual(result["stdout"], "")
        self.assertIn("definitely_missing_cpp_benchmark", result["stderr"])
        self.assertEqual(result["command"], command)
        self.assertEqual(result["implementation"], "cpp")
        self.assertEqual(result["task_type"], "camera")
        self.assertEqual(result["label"], "missing_binary")
        self.assertGreaterEqual(result["wall_seconds"], 0.0)

    def test_run_cpp_command_fail_fast_wraps_launch_failure(self):
        with temporary_directory() as temp_dir:
            command = [str(temp_dir / "definitely_missing_cpp_benchmark"), "camera"]

            with self.assertRaisesRegex(RuntimeError, "Failed to launch C\\+\\+ benchmark command"):
                benchmark.run_cpp_command(
                    command,
                    keep_going=False,
                    task_type="camera",
                    label="missing_binary",
                )

    def test_record_cpp_result_keep_going_records_bad_json_after_zero_exit(self):
        with temporary_directory() as temp_dir:
            result_path = temp_dir / "result.json"
            command = [sys.executable, "-c", "print('unused')", "--output", str(result_path)]
            result_path.write_text("{bad json", encoding="utf-8")

            with mock.patch.object(
                benchmark,
                "run_cpp_command",
                return_value={
                    "status": "success",
                    "return_code": 0,
                    "stdout": "",
                    "stderr": "",
                    "command": command,
                    "wall_seconds": 0.01,
                    "implementation": "cpp",
                    "label": "camera_a",
                    "task_type": "camera",
                },
            ):
                result = benchmark._record_cpp_result(
                    result_path,
                    command,
                    task_type="camera",
                    label="camera_a",
                    keep_going=True,
                )

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["implementation"], "cpp")
            self.assertEqual(result["label"], "camera_a")
            self.assertEqual(result["task_type"], "camera")
            self.assertEqual(result["return_code"], 0)
            self.assertEqual(result["command"], command)
            self.assertIn("Failed to load C++ result", result["error"])
            self.assertIn("Failed to load C++ result", result["stderr"])
            self.assertGreaterEqual(result["wall_seconds"], 0.0)
            self.assertEqual(json.loads(result_path.read_text(encoding="utf-8")), result)

    def test_record_cpp_result_fail_fast_raises_on_bad_json_after_zero_exit(self):
        with temporary_directory() as temp_dir:
            result_path = temp_dir / "result.json"
            command = [sys.executable, "-c", "print('unused')", "--output", str(result_path)]
            result_path.write_text("{bad json", encoding="utf-8")

            with (
                mock.patch.object(
                    benchmark,
                    "run_cpp_command",
                    return_value={
                        "status": "success",
                        "return_code": 0,
                        "stdout": "",
                        "stderr": "",
                        "command": command,
                        "wall_seconds": 0.01,
                        "implementation": "cpp",
                        "label": "camera_a",
                        "task_type": "camera",
                    },
                ),
                self.assertRaisesRegex(RuntimeError, "Failed to load C\\+\\+ result"),
            ):
                benchmark._record_cpp_result(
                    result_path,
                    command,
                    task_type="camera",
                    label="camera_a",
                    keep_going=False,
                )

    def test_write_command_uses_shell_quoting_and_executable_mode(self):
        with temporary_directory() as temp_dir:
            command_path = temp_dir / "command.sh"

            benchmark._write_command(command_path, ["/tmp/cpp benchmark", "camera", "--label", "space label"])

            mode = command_path.stat().st_mode
            if os.name != "nt":
                self.assertTrue(mode & stat.S_IXUSR)
                self.assertTrue(mode & stat.S_IXGRP)
                self.assertTrue(mode & stat.S_IXOTH)
            self.assertEqual(
                command_path.read_text(encoding="utf-8").splitlines(),
                [
                    "#!/usr/bin/env bash",
                    "set -euo pipefail",
                    "'/tmp/cpp benchmark' camera --label 'space label'",
                ],
            )

    def test_run_benchmark_dry_run_writes_cpp_command_scripts_without_reports(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            config = benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

            run_dir = benchmark.run_benchmark(
                config,
                output_root=temp_dir / "out",
                dry_run=True,
                only={"config_relative_camera", "controlnet_fixture"},
                keep_going=True,
            )

            camera_command_path = run_dir / "cpp" / "config_relative_camera" / "command.sh"
            controlnet_command_path = run_dir / "cpp" / "controlnet_fixture" / "command.sh"
            self.assertTrue(camera_command_path.is_file())
            self.assertTrue(os.access(camera_command_path, os.X_OK))
            self.assertTrue(controlnet_command_path.is_file())
            self.assertIn("camera", camera_command_path.read_text(encoding="utf-8"))
            self.assertIn("--cube", camera_command_path.read_text(encoding="utf-8"))
            self.assertIn("controlnet", controlnet_command_path.read_text(encoding="utf-8"))
            self.assertIn("--net", controlnet_command_path.read_text(encoding="utf-8"))
            self.assertFalse((run_dir / "cpp" / "repo_relative_camera").exists())
            self.assertFalse((run_dir / "reports" / "summary.json").exists())
            self.assertFalse(any((run_dir / "pyisis").iterdir()))

    def test_run_benchmark_real_run_rejects_missing_selected_inputs_before_outputs(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["camera_tasks"][0]["cube_path"] = "missing.cub"
            payload["controlnet_tasks"][0]["net_path"] = "missing.net"
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            config = benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

            with self.assertRaisesRegex(ValueError, "Missing benchmark input path"):
                benchmark.run_benchmark(
                    config,
                    output_root=temp_dir / "out",
                    dry_run=False,
                    only={"config_relative_camera", "controlnet_fixture"},
                    keep_going=True,
                )

            self.assertFalse((temp_dir / "out" / "unit_benchmark" / "pyisis").exists())

    def test_run_benchmark_dry_run_allows_missing_inputs_and_writes_commands(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["camera_tasks"][0]["cube_path"] = "missing.cub"
            payload["controlnet_tasks"][0]["net_path"] = "missing.net"
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            config = benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

            run_dir = benchmark.run_benchmark(
                config,
                output_root=temp_dir / "out",
                dry_run=True,
                only={"config_relative_camera", "controlnet_fixture"},
                keep_going=True,
            )

            self.assertTrue((run_dir / "cpp" / "config_relative_camera" / "command.sh").is_file())
            self.assertTrue((run_dir / "cpp" / "controlnet_fixture" / "command.sh").is_file())

    def test_run_benchmark_keep_going_records_pyisis_failure_and_continues(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            config = benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)
            expected_camera_cpp = {
                "task_type": "camera",
                "implementation": "cpp",
                "label": "config_relative_camera",
                "status": "success",
                "points": [],
            }
            expected_controlnet_cpp = {
                "task_type": "controlnet",
                "implementation": "cpp",
                "label": "controlnet_fixture",
                "status": "success",
                "point_count": 2,
                "measure_count": 3,
            }

            def fake_run_cpp_command(command, *, keep_going, task_type="", label=""):
                output_path = Path(command[command.index("--output") + 1])
                if task_type == "camera":
                    output_path.write_text(json.dumps(expected_camera_cpp), encoding="utf-8")
                else:
                    output_path.write_text(json.dumps(expected_controlnet_cpp), encoding="utf-8")
                return {
                    "status": "success",
                    "return_code": 0,
                    "stdout": "",
                    "stderr": "",
                    "command": command,
                    "wall_seconds": 0.01,
                    "implementation": "cpp",
                    "label": label,
                    "task_type": task_type,
                }

            with (
                mock.patch.object(benchmark, "run_pyisis_camera_task", side_effect=RuntimeError("camera exploded")),
                mock.patch.object(
                    benchmark,
                    "run_pyisis_controlnet_task",
                    return_value={
                        "task_type": "controlnet",
                        "implementation": "pyisis",
                        "label": "controlnet_fixture",
                        "status": "success",
                        "point_count": 2,
                        "measure_count": 3,
                    },
                ),
                mock.patch.object(benchmark, "run_cpp_command", side_effect=fake_run_cpp_command),
            ):
                run_dir = benchmark.run_benchmark(
                    config,
                    output_root=temp_dir / "out",
                    dry_run=False,
                    only={"config_relative_camera", "controlnet_fixture"},
                    keep_going=True,
                )

            summary = json.loads((run_dir / "reports" / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual([result["status"] for result in summary["results"]], ["failed", "success", "success", "success"])
            pyisis_failure = summary["results"][0]
            self.assertEqual(pyisis_failure["implementation"], "pyisis")
            self.assertEqual(pyisis_failure["task_type"], "camera")
            self.assertEqual(pyisis_failure["label"], "config_relative_camera")
            self.assertIn("camera exploded", pyisis_failure["error"])
            self.assertIn("camera exploded", pyisis_failure["stderr"])
            self.assertGreaterEqual(pyisis_failure["wall_seconds"], 0.0)
            self.assertTrue((run_dir / "pyisis" / "config_relative_camera.json").is_file())
            self.assertTrue((run_dir / "pyisis" / "controlnet_fixture.json").is_file())

    def test_main_defaults_to_keep_going(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            output_root = temp_dir / "out"

            with mock.patch.object(benchmark, "run_benchmark", return_value=output_root / "unit_benchmark") as mocked:
                exit_code = benchmark.main([str(config_path), "--output-root", str(output_root), "--dry-run"])

            self.assertEqual(exit_code, 0)
            self.assertTrue(mocked.call_args.kwargs["keep_going"])

    def test_main_fail_fast_sets_keep_going_false(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            output_root = temp_dir / "out"

            with mock.patch.object(benchmark, "run_benchmark", return_value=output_root / "unit_benchmark") as mocked:
                exit_code = benchmark.main(
                    [str(config_path), "--output-root", str(output_root), "--dry-run", "--fail-fast"]
                )

            self.assertEqual(exit_code, 0)
            self.assertFalse(mocked.call_args.kwargs["keep_going"])

    def test_run_benchmark_with_stubbed_tasks_writes_results_and_reports(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            config = benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)
            expected_camera_cpp = {
                "task_type": "camera",
                "implementation": "cpp",
                "label": "config_relative_camera",
                "status": "success",
                "points": [
                    {
                        "index": 0,
                        "latitude": 1.0,
                        "longitude": 2.0,
                        "roundtrip_sample": 3.0,
                        "roundtrip_line": 4.0,
                    }
                ],
            }
            expected_controlnet_cpp = {
                "task_type": "controlnet",
                "implementation": "cpp",
                "label": "controlnet_fixture",
                "status": "success",
                "point_count": 2,
                "measure_count": 3,
            }

            def fake_run_pyisis_camera_task(task):
                return {
                    "task_type": "camera",
                    "implementation": "pyisis",
                    "label": task.label,
                    "status": "success",
                    "points": [
                        {
                            "index": 0,
                            "latitude": 1.0,
                            "longitude": 2.0,
                            "roundtrip_sample": 3.0,
                            "roundtrip_line": 4.0,
                        }
                    ],
                }

            def fake_run_pyisis_controlnet_task(task):
                return {
                    "task_type": "controlnet",
                    "implementation": "pyisis",
                    "label": task.label,
                    "status": "success",
                    "point_count": 2,
                    "measure_count": 3,
                }

            def fake_run_cpp_command(command, *, keep_going, task_type="", label=""):
                output_path = Path(command[command.index("--output") + 1])
                if command[1] == "camera":
                    output_path.write_text(json.dumps(expected_camera_cpp), encoding="utf-8")
                else:
                    output_path.write_text(json.dumps(expected_controlnet_cpp), encoding="utf-8")
                return {
                    "status": "success",
                    "return_code": 0,
                    "stdout": "",
                    "stderr": "",
                    "command": command,
                    "wall_seconds": 0.01,
                }

            with (
                mock.patch.object(benchmark, "run_pyisis_camera_task", side_effect=fake_run_pyisis_camera_task),
                mock.patch.object(
                    benchmark,
                    "run_pyisis_controlnet_task",
                    side_effect=fake_run_pyisis_controlnet_task,
                ),
                mock.patch.object(benchmark, "run_cpp_command", side_effect=fake_run_cpp_command),
            ):
                run_dir = benchmark.run_benchmark(
                    config,
                    output_root=temp_dir / "out",
                    dry_run=False,
                    only={"config_relative_camera", "controlnet_fixture"},
                    keep_going=True,
                )

            camera_pyisis_path = run_dir / "pyisis" / "config_relative_camera.json"
            camera_cpp_path = run_dir / "cpp" / "config_relative_camera.json"
            controlnet_pyisis_path = run_dir / "pyisis" / "controlnet_fixture.json"
            controlnet_cpp_path = run_dir / "cpp" / "controlnet_fixture.json"
            camera_command_path = run_dir / "cpp" / "config_relative_camera" / "command.sh"
            controlnet_command_path = run_dir / "cpp" / "controlnet_fixture" / "command.sh"
            self.assertTrue(camera_pyisis_path.is_file())
            self.assertTrue(camera_cpp_path.is_file())
            self.assertTrue(controlnet_pyisis_path.is_file())
            self.assertTrue(controlnet_cpp_path.is_file())
            self.assertTrue(camera_command_path.is_file())
            self.assertTrue(os.access(camera_command_path, os.X_OK))
            self.assertTrue(controlnet_command_path.is_file())
            self.assertTrue(os.access(controlnet_command_path, os.X_OK))
            self.assertEqual(json.loads(camera_cpp_path.read_text(encoding="utf-8")), expected_camera_cpp)
            summary = json.loads((run_dir / "reports" / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual([result["status"] for result in summary["results"]], ["success"] * 4)
            self.assertEqual(
                [(result["implementation"], result["label"]) for result in summary["results"]],
                [
                    ("pyisis", "config_relative_camera"),
                    ("cpp", "config_relative_camera"),
                    ("pyisis", "controlnet_fixture"),
                    ("cpp", "controlnet_fixture"),
                ],
            )
            self.assertEqual(len(summary["camera_comparisons"]), 1)
            self.assertEqual(summary["camera_comparisons"][0]["label"], "config_relative_camera")
            self.assertIn("provenance", summary)
            self.assertEqual(summary["provenance"]["config_snapshot"], str(run_dir / "experiment_config.json"))
            self.assertEqual(summary["provenance"]["cpp_benchmark_path"], str(PROJECT_ROOT / "tools/cpp_benchmark"))
            self.assertIn("pyisis_import_path", summary["provenance"])
            self.assertIn("ISISDATA", summary["provenance"])
            self.assertIn("CONDA_DEFAULT_ENV", summary["provenance"])
            self.assertIn("git_commit", summary["provenance"])
            controlnet_summary = json.loads(
                (run_dir / "reports" / "controlnet_summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(controlnet_summary["provenance"], summary["provenance"])


if __name__ == "__main__":
    unittest.main()
