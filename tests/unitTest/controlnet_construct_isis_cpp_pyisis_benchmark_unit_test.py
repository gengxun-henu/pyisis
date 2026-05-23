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


if __name__ == "__main__":
    unittest.main()
