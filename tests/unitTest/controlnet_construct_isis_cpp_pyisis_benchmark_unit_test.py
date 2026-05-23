"""Unit tests for the ISIS C++ vs PyISIS benchmark config model."""

from __future__ import annotations

import json
import sys
from pathlib import Path
import unittest


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import temporary_directory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.experiments import isis_cpp_pyisis_benchmark as benchmark


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

    def close(self):
        self.closed = True


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


def _write_benchmark_config(path: Path) -> None:
    local_cube = path.parent / "local.cub"
    local_cube.write_text("fixture\n", encoding="utf-8")
    path.write_text(
        json.dumps(
            {
                "run_id": "unit_benchmark",
                "description": "unit benchmark config",
                "execution": {
                    "cpp_benchmark_path": "tools/cpp_benchmark",
                    "repeat_count": 3,
                    "keep_intermediate_json": False,
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
        self.assertEqual(config.execution.repeat_count, 3)
        self.assertFalse(config.execution.keep_intermediate_json)

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

    def test_load_benchmark_config_rejects_duplicate_labels_across_task_types(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            _write_benchmark_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["controlnet_tasks"][0]["label"] = "config_relative_camera"
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

        self.assertEqual(fake_ip.cubes[0].open_args, ("/tmp/fake.cub", "r"))
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

        self.assertEqual(fake_ip.control_nets[0].path, "/tmp/fake.net")
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
                ["config_relative_camera", "repo_relative_camera", "controlnet_fixture"],
            )
            self.assertEqual(manifest["cpp_benchmark_path"], str(PROJECT_ROOT / "tools/cpp_benchmark"))
            self.assertRegex(manifest["created_at"], r"^\d{4}-\d{2}-\d{2}T.*\+00:00$")
            self.assertTrue((run_dir / "pyisis").is_dir())
            self.assertTrue((run_dir / "cpp").is_dir())
            self.assertTrue((run_dir / "reports").is_dir())

    def test_write_summary_reports_writes_json_and_csv_schemas(self):
        results = [
            {
                "label": "camera_a",
                "task_type": "camera",
                "implementation": "pyisis",
                "status": "completed",
                "core_seconds": 1.25,
                "wall_seconds": 1.5,
                "successful_point_count": 2,
            },
            {
                "label": "net_a",
                "task_type": "controlnet",
                "implementation": "cpp",
                "status": "completed",
                "core_seconds": 2.0,
                "wall_seconds": 2.25,
                "point_count": 7,
                "measure_count": 11,
            },
        ]
        camera_comparisons = [
            {
                "label": "camera_a",
                "matched_point_count": 1,
                "missing_in_pyisis": [],
                "missing_in_cpp": [],
                "stats": {"latitude_abs_max": 0.5},
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
            benchmark.write_summary_reports(temp_dir, results, camera_comparisons)

            summary = json.loads((temp_dir / "reports" / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["results"], results)
            self.assertEqual(summary["camera_comparisons"], camera_comparisons)
            self.assertEqual(
                (temp_dir / "reports" / "summary.csv").read_text(encoding="utf-8").splitlines(),
                [
                    "label,task_type,implementation,status,core_seconds,wall_seconds,point_count,measure_count,successful_point_count",
                    "camera_a,camera,pyisis,completed,1.25,1.5,,,2",
                    "net_a,controlnet,cpp,completed,2.0,2.25,7,11,",
                ],
            )
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


if __name__ == "__main__":
    unittest.main()
