# ISIS C++ vs PyISIS Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible benchmark harness that compares PyISIS and direct ISIS C++ on LRO NAC camera coordinate conversion and ControlNet loading/traversal.

**Architecture:** Keep orchestration in a Python experiment runner under `examples/controlnet_construct/experiments/`, and add one CMake-built C++ executable under `tools/benchmarks/` for direct ISIS API timing. The Python runner parses a JSON config, generates shared camera sample grids, runs PyISIS and C++ implementations with matching task parameters, compares result schemas, and writes reports without changing PyISIS bindings or ControlNet pipeline behavior.

**Tech Stack:** Python 3.12 standard library (`argparse`, `csv`, `dataclasses`, `json`, `math`, `pathlib`, `statistics`, `subprocess`, `time`, `unittest`), pybind package `isis_pybind`, C++17, CMake, ISIS C++ libraries from the `asp360_new` conda environment, Qt5 Core for ISIS support types.

---

## File Structure

- Create: `examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py`
  - Config dataclasses, camera grid generation, PyISIS task execution, C++ command generation, subprocess execution, result loading, numeric diffing, report writing, and CLI.
- Create: `examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json`
  - Small example config using repo fixtures, with `max_points` set for safe smoke runs.
- Create: `tools/benchmarks/isis_cpp_benchmark.cpp`
  - Direct ISIS C++ executable with `camera` and `controlnet` subcommands, JSON output, and core timing.
- Modify: `CMakeLists.txt`
  - Add `isis_cpp_benchmark` executable, include dirs, link libraries, RPATH, and output directory.
- Create: `tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py`
  - Python unit tests for config parsing, grid generation, report diffing, dry-run behavior, failure handling, and C++ JSON parsing.
- Modify: `examples/controlnet_construct/experiments/README.md`
  - Add a short benchmark section with build, dry-run, fixture smoke, and production `ISISDATA` commands.

Execution should happen in an isolated worktree, for example:

```bash
git worktree add .worktrees/isis-cpp-pyisis-benchmark-20260523 -b feat/isis-cpp-pyisis-benchmark-20260523 HEAD
cd .worktrees/isis-cpp-pyisis-benchmark-20260523
```

---

### Task 1: Python Config Model and Camera Sample Grid

**Files:**
- Create: `examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py`
- Create: `examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json`
- Test: `tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py`

- [ ] **Step 1: Write failing config and grid tests**

Create `tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py` with:

```python
"""Unit tests for ISIS C++ vs PyISIS benchmark orchestration."""

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


def write_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "run_id": "unit_benchmark",
                "description": "unit test benchmark",
                "execution": {
                    "cpp_benchmark_path": "build/tools/benchmarks/isis_cpp_benchmark",
                    "repeat_count": 2,
                    "keep_intermediate_json": True,
                },
                "camera_tasks": [
                    {
                        "label": "camera_small",
                        "cube_path": "tests/data/lronacpho/M143947267L.cal.echo.crop.cub",
                        "sample_step": 10,
                        "line_step": 20,
                        "max_points": 5,
                        "top_error_count": 3,
                    }
                ],
                "controlnet_tasks": [
                    {
                        "label": "net_small",
                        "net_path": "tests/data/threeImageNetwork/controlnetwork.net",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


class BenchmarkConfigUnitTest(unittest.TestCase):
    def test_load_config_resolves_paths_and_preserves_limits(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            write_config(config_path)

            config = benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

        self.assertEqual(config.run_id, "unit_benchmark")
        self.assertEqual(config.execution.repeat_count, 2)
        self.assertTrue(config.execution.keep_intermediate_json)
        self.assertEqual(config.execution.cpp_benchmark_path, PROJECT_ROOT / "build/tools/benchmarks/isis_cpp_benchmark")
        self.assertEqual(config.camera_tasks[0].label, "camera_small")
        self.assertEqual(config.camera_tasks[0].cube_path, PROJECT_ROOT / "tests/data/lronacpho/M143947267L.cal.echo.crop.cub")
        self.assertEqual(config.camera_tasks[0].max_points, 5)
        self.assertEqual(config.controlnet_tasks[0].net_path, PROJECT_ROOT / "tests/data/threeImageNetwork/controlnetwork.net")

    def test_generate_camera_samples_uses_one_based_grid_and_max_points(self):
        samples = benchmark.generate_camera_samples(sample_count=35, line_count=45, sample_step=10, line_step=20, max_points=6)

        self.assertEqual(
            samples,
            [
                benchmark.CameraSample(index=0, sample=1.0, line=1.0),
                benchmark.CameraSample(index=1, sample=11.0, line=1.0),
                benchmark.CameraSample(index=2, sample=21.0, line=1.0),
                benchmark.CameraSample(index=3, sample=31.0, line=1.0),
                benchmark.CameraSample(index=4, sample=35.0, line=1.0),
                benchmark.CameraSample(index=5, sample=1.0, line=21.0),
            ],
        )

    def test_load_config_rejects_duplicate_task_labels(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            write_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["controlnet_tasks"].append({"label": "camera_small", "net_path": "x.net"})
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Duplicate task label"):
                benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)

    def test_load_config_rejects_invalid_steps(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            write_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["camera_tasks"][0]["sample_step"] = 0
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "sample_step must be positive"):
                benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_isis_cpp_pyisis_benchmark_unit_test -v
```

Expected: failure because `isis_cpp_pyisis_benchmark.py` does not exist.

- [ ] **Step 3: Implement config parsing and grid generation**

Create `examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py` with:

```python
"""Benchmark PyISIS against direct ISIS C++ workflows.

Author: Geng Xun
Created: 2026-05-23
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


SAFE_PATH_COMPONENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


@dataclass(frozen=True)
class CameraSample:
    index: int
    sample: float
    line: float


@dataclass(frozen=True)
class ExecutionConfig:
    cpp_benchmark_path: Path
    repeat_count: int = 1
    keep_intermediate_json: bool = True


@dataclass(frozen=True)
class CameraTaskConfig:
    label: str
    cube_path: Path
    sample_step: int = 10
    line_step: int = 10
    max_points: int | None = None
    top_error_count: int = 50


@dataclass(frozen=True)
class ControlNetTaskConfig:
    label: str
    net_path: Path


@dataclass(frozen=True)
class BenchmarkConfig:
    run_id: str
    description: str
    execution: ExecutionConfig
    camera_tasks: tuple[CameraTaskConfig, ...]
    controlnet_tasks: tuple[ControlNetTaskConfig, ...]
    config_path: Path


def _validate_path_component(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped or not SAFE_PATH_COMPONENT_RE.match(stripped):
        raise ValueError(f"{field_name} must be a safe non-empty path component")
    return stripped


def _resolve_path(value: str | Path, base_dir: Path, repo_root: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    config_relative = base_dir / path
    if config_relative.exists():
        return config_relative.resolve()
    return (repo_root / path).resolve()


def _require_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def _optional_string(payload: dict[str, Any], key: str, default: str) -> str:
    value = payload.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _optional_bool(payload: dict[str, Any], key: str, default: bool) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _optional_positive_int(payload: dict[str, Any], key: str, default: int | None) -> int | None:
    value = payload.get(key, default)
    if value is None:
        return None
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{key} must be positive")
    return value


def load_benchmark_config(config_path: str | Path, *, repo_root: str | Path | None = None) -> BenchmarkConfig:
    config_path = Path(config_path).expanduser().resolve()
    repo_root_path = Path(repo_root).expanduser().resolve() if repo_root is not None else Path(__file__).resolve().parents[3]

    with config_path.open(encoding="utf-8") as config_file:
        payload = json.load(config_file)
    if not isinstance(payload, dict):
        raise ValueError("Benchmark config must be a JSON object")

    run_id = _validate_path_component(_optional_string(payload, "run_id", ""), "run_id")
    execution_payload = _require_mapping(payload, "execution")
    execution = ExecutionConfig(
        cpp_benchmark_path=_resolve_path(
            _optional_string(execution_payload, "cpp_benchmark_path", "build/tools/benchmarks/isis_cpp_benchmark"),
            config_path.parent,
            repo_root_path,
        ),
        repeat_count=_optional_positive_int(execution_payload, "repeat_count", 1) or 1,
        keep_intermediate_json=_optional_bool(execution_payload, "keep_intermediate_json", True),
    )

    camera_tasks = _load_camera_tasks(payload.get("camera_tasks", []), config_path.parent, repo_root_path)
    controlnet_tasks = _load_controlnet_tasks(payload.get("controlnet_tasks", []), config_path.parent, repo_root_path)
    if not camera_tasks and not controlnet_tasks:
        raise ValueError("At least one camera task or controlnet task is required")

    labels: set[str] = set()
    for label in [task.label for task in camera_tasks] + [task.label for task in controlnet_tasks]:
        if label in labels:
            raise ValueError(f"Duplicate task label: {label}")
        labels.add(label)

    return BenchmarkConfig(
        run_id=run_id,
        description=_optional_string(payload, "description", ""),
        execution=execution,
        camera_tasks=tuple(camera_tasks),
        controlnet_tasks=tuple(controlnet_tasks),
        config_path=config_path,
    )


def _load_camera_tasks(payload: Any, base_dir: Path, repo_root: Path) -> list[CameraTaskConfig]:
    if not isinstance(payload, list):
        raise ValueError("camera_tasks must be an array")
    tasks: list[CameraTaskConfig] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"camera_tasks[{index}] must be an object")
        sample_step = _optional_positive_int(item, "sample_step", 10) or 10
        line_step = _optional_positive_int(item, "line_step", 10) or 10
        max_points = _optional_positive_int(item, "max_points", None)
        top_error_count = _optional_positive_int(item, "top_error_count", 50) or 50
        tasks.append(
            CameraTaskConfig(
                label=_validate_path_component(_optional_string(item, "label", ""), "label"),
                cube_path=_resolve_path(_optional_string(item, "cube_path", ""), base_dir, repo_root),
                sample_step=sample_step,
                line_step=line_step,
                max_points=max_points,
                top_error_count=top_error_count,
            )
        )
    return tasks


def _load_controlnet_tasks(payload: Any, base_dir: Path, repo_root: Path) -> list[ControlNetTaskConfig]:
    if not isinstance(payload, list):
        raise ValueError("controlnet_tasks must be an array")
    tasks: list[ControlNetTaskConfig] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"controlnet_tasks[{index}] must be an object")
        tasks.append(
            ControlNetTaskConfig(
                label=_validate_path_component(_optional_string(item, "label", ""), "label"),
                net_path=_resolve_path(_optional_string(item, "net_path", ""), base_dir, repo_root),
            )
        )
    return tasks


def generate_camera_samples(
    *,
    sample_count: int,
    line_count: int,
    sample_step: int,
    line_step: int,
    max_points: int | None,
) -> list[CameraSample]:
    if sample_count <= 0 or line_count <= 0:
        raise ValueError("sample_count and line_count must be positive")
    if sample_step <= 0:
        raise ValueError("sample_step must be positive")
    if line_step <= 0:
        raise ValueError("line_step must be positive")

    sample_values = _axis_positions(sample_count, sample_step)
    line_values = _axis_positions(line_count, line_step)
    samples: list[CameraSample] = []
    for line in line_values:
        for sample in sample_values:
            samples.append(CameraSample(index=len(samples), sample=float(sample), line=float(line)))
            if max_points is not None and len(samples) >= max_points:
                return samples
    return samples


def _axis_positions(max_value: int, step: int) -> list[int]:
    values = list(range(1, max_value + 1, step))
    if values[-1] != max_value:
        values.append(max_value)
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config")
    args = parser.parse_args(argv)
    load_benchmark_config(args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Create `examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json`:

```json
{
  "run_id": "lro_nac_pyisis_cpp_20260523",
  "description": "Compare PyISIS and direct ISIS C++ on camera and ControlNet workflows.",
  "execution": {
    "cpp_benchmark_path": "build/tools/benchmarks/isis_cpp_benchmark",
    "repeat_count": 1,
    "keep_intermediate_json": true
  },
  "camera_tasks": [
    {
      "label": "lro_nac_fixture",
      "cube_path": "tests/data/lronacpho/M143947267L.cal.echo.crop.cub",
      "sample_step": 10,
      "line_step": 10,
      "max_points": 100,
      "top_error_count": 20
    }
  ],
  "controlnet_tasks": [
    {
      "label": "three_image_network",
      "net_path": "tests/data/threeImageNetwork/controlnetwork.net"
    }
  ]
}
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_isis_cpp_pyisis_benchmark_unit_test -v
```

Expected: all tests in this file pass.

Commit:

```bash
git add examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json \
  tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py
git commit -m "feat: add isis benchmark config model"
```

---

### Task 2: PyISIS Camera and ControlNet Benchmark Core

**Files:**
- Modify: `examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py`
- Test: `tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py`

- [ ] **Step 1: Add failing tests for PyISIS task functions with fake `isis_pybind`**

Append these tests to `BenchmarkConfigUnitTest`:

```python
    def test_run_pyisis_camera_task_uses_camera_round_trip_and_counts_failures(self):
        fake_ip = FakeIsisModule.for_camera(sample_count=21, line_count=11, fail_indices={2})
        task = benchmark.CameraTaskConfig(
            label="camera_fake",
            cube_path=Path("fake.cub"),
            sample_step=10,
            line_step=10,
            max_points=None,
            top_error_count=3,
        )

        result = benchmark.run_pyisis_camera_task(task, ip_module=fake_ip)

        self.assertEqual(result["task_type"], "camera")
        self.assertEqual(result["implementation"], "pyisis")
        self.assertEqual(result["input_point_count"], 9)
        self.assertEqual(result["successful_point_count"], 8)
        self.assertEqual(result["failed_set_image_count"], 1)
        self.assertEqual(result["failed_set_universal_ground_count"], 0)
        self.assertEqual(result["points"][0]["index"], 0)
        self.assertIn("core_seconds", result)

    def test_run_pyisis_controlnet_task_reads_counts_and_measure_fields(self):
        fake_ip = FakeIsisModule.for_controlnet()
        task = benchmark.ControlNetTaskConfig(label="net_fake", net_path=Path("fake.net"))

        result = benchmark.run_pyisis_controlnet_task(task, ip_module=fake_ip)

        self.assertEqual(result["task_type"], "controlnet")
        self.assertEqual(result["implementation"], "pyisis")
        self.assertEqual(result["point_count"], 2)
        self.assertEqual(result["measure_count"], 3)
        self.assertEqual(result["valid_measure_count"], 3)
        self.assertEqual(result["serial_measure_counts"], {"SERIAL_A": 2, "SERIAL_B": 1})
        self.assertGreaterEqual(result["load_seconds"], 0.0)
        self.assertGreaterEqual(result["traverse_seconds"], 0.0)
```

Add fake test helpers at module level in the test file:

```python
class FakeCamera:
    def __init__(self, sample_count: int, line_count: int, fail_indices: set[int]):
        self._sample_count = sample_count
        self._line_count = line_count
        self._fail_indices = fail_indices
        self._sample = 0.0
        self._line = 0.0
        self.calls = 0

    def samples(self):
        return self._sample_count

    def lines(self):
        return self._line_count

    def set_image(self, sample, line):
        if self.calls in self._fail_indices:
            self.calls += 1
            return False
        self.calls += 1
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


class FakeCube:
    def __init__(self, camera):
        self._camera = camera

    def open(self, path, mode):
        self.path = path
        self.mode = mode

    def camera(self):
        return self._camera

    def close(self):
        pass


class FakeMeasure:
    def __init__(self, serial, sample, line):
        self.serial = serial
        self.sample = sample
        self.line = line

    def get_cube_serial_number(self):
        return self.serial

    def get_sample(self):
        return self.sample

    def get_line(self):
        return self.line

    def get_measure_type_string(self):
        return "Manual"

    def is_ignored(self):
        return False

    def is_edit_locked(self):
        return False


class FakePoint:
    def __init__(self, point_id, measures):
        self.point_id = point_id
        self.measures = measures

    def get_id(self):
        return self.point_id

    def get_point_type_string(self):
        return "Free"

    def get_num_measures(self):
        return len(self.measures)

    def get_measure(self, index):
        return self.measures[index]

    def is_ignored(self):
        return False

    def is_edit_locked(self):
        return False


class FakeControlNet:
    def __init__(self, path):
        self.points = [
            FakePoint("P1", [FakeMeasure("SERIAL_A", 1.0, 2.0), FakeMeasure("SERIAL_B", 3.0, 4.0)]),
            FakePoint("P2", [FakeMeasure("SERIAL_A", 5.0, 6.0)]),
        ]

    def get_num_points(self):
        return len(self.points)

    def get_num_measures(self):
        return sum(point.get_num_measures() for point in self.points)

    def get_num_valid_points(self):
        return len(self.points)

    def get_num_valid_measures(self):
        return self.get_num_measures()

    def get_point(self, index):
        return self.points[index]


class FakeIsisModule:
    @classmethod
    def for_camera(cls, sample_count, line_count, fail_indices):
        module = cls()
        module._camera = FakeCamera(sample_count, line_count, fail_indices)
        module.Cube = lambda: FakeCube(module._camera)
        return module

    @classmethod
    def for_controlnet(cls):
        module = cls()
        module.ControlNet = FakeControlNet
        return module
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_isis_cpp_pyisis_benchmark_unit_test -v
```

Expected: failure because `run_pyisis_camera_task` and `run_pyisis_controlnet_task` are missing.

- [ ] **Step 3: Implement PyISIS task functions**

Add these imports:

```python
import time
from collections import Counter
```

Add this helper:

```python
def _import_isis_pybind():
    import isis_pybind as ip

    return ip
```

Add these functions:

```python
def run_pyisis_camera_task(task: CameraTaskConfig, *, ip_module=None) -> dict[str, Any]:
    ip = ip_module if ip_module is not None else _import_isis_pybind()
    cube = ip.Cube()
    cube.open(str(task.cube_path), "r")
    try:
        camera = cube.camera()
        samples = generate_camera_samples(
            sample_count=int(camera.samples()),
            line_count=int(camera.lines()),
            sample_step=task.sample_step,
            line_step=task.line_step,
            max_points=task.max_points,
        )
        points: list[dict[str, Any]] = []
        failed_set_image_count = 0
        failed_set_universal_ground_count = 0
        start = time.perf_counter()
        for camera_sample in samples:
            if not camera.set_image(camera_sample.sample, camera_sample.line):
                failed_set_image_count += 1
                continue
            latitude = float(camera.universal_latitude())
            longitude = float(camera.universal_longitude())
            if not camera.set_universal_ground(latitude, longitude):
                failed_set_universal_ground_count += 1
                continue
            points.append(
                {
                    "index": camera_sample.index,
                    "input_sample": camera_sample.sample,
                    "input_line": camera_sample.line,
                    "latitude": latitude,
                    "longitude": longitude,
                    "roundtrip_sample": float(camera.sample()),
                    "roundtrip_line": float(camera.line()),
                }
            )
        core_seconds = time.perf_counter() - start
    finally:
        cube.close()

    return {
        "task_type": "camera",
        "implementation": "pyisis",
        "label": task.label,
        "cube_path": str(task.cube_path),
        "input_point_count": len(samples),
        "successful_point_count": len(points),
        "failed_set_image_count": failed_set_image_count,
        "failed_set_universal_ground_count": failed_set_universal_ground_count,
        "core_seconds": core_seconds,
        "average_successful_point_seconds": core_seconds / len(points) if points else None,
        "points": points,
    }
```

```python
def _optional_call(obj: Any, method_name: str, default: Any = None) -> Any:
    method = getattr(obj, method_name, None)
    if method is None:
        return default
    return method()


def run_pyisis_controlnet_task(task: ControlNetTaskConfig, *, ip_module=None) -> dict[str, Any]:
    ip = ip_module if ip_module is not None else _import_isis_pybind()
    load_start = time.perf_counter()
    control_net = ip.ControlNet(str(task.net_path))
    load_seconds = time.perf_counter() - load_start

    serial_counts: Counter[str] = Counter()
    traverse_start = time.perf_counter()
    point_count = int(control_net.get_num_points())
    for point_index in range(point_count):
        point = control_net.get_point(point_index)
        _optional_call(point, "get_id", "")
        _optional_call(point, "get_point_type_string", "")
        _optional_call(point, "is_ignored", False)
        _optional_call(point, "is_edit_locked", False)
        for measure_index in range(int(point.get_num_measures())):
            measure = point.get_measure(measure_index)
            serial = str(measure.get_cube_serial_number())
            serial_counts[serial] += 1
            _optional_call(measure, "get_sample", 0.0)
            _optional_call(measure, "get_line", 0.0)
            _optional_call(measure, "get_measure_type_string", "")
            _optional_call(measure, "is_ignored", False)
            _optional_call(measure, "is_edit_locked", False)
    traverse_seconds = time.perf_counter() - traverse_start

    return {
        "task_type": "controlnet",
        "implementation": "pyisis",
        "label": task.label,
        "net_path": str(task.net_path),
        "point_count": point_count,
        "measure_count": int(control_net.get_num_measures()),
        "valid_point_count": _optional_call(control_net, "get_num_valid_points"),
        "valid_measure_count": _optional_call(control_net, "get_num_valid_measures"),
        "serial_measure_counts": dict(sorted(serial_counts.items())),
        "load_seconds": load_seconds,
        "traverse_seconds": traverse_seconds,
        "core_seconds": load_seconds + traverse_seconds,
    }
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_isis_cpp_pyisis_benchmark_unit_test -v
```

Expected: all tests pass.

Commit:

```bash
git add examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py
git commit -m "feat: add pyisis benchmark tasks"
```

---

### Task 3: Diffing, Report Writers, and Dry-Run Manifest

**Files:**
- Modify: `examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py`
- Test: `tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py`

- [ ] **Step 1: Add failing tests for diffing and dry-run files**

Append:

```python
    def test_compare_camera_results_computes_stats_and_top_errors(self):
        py_result = {
            "points": [
                {"index": 0, "latitude": 1.0, "longitude": 2.0, "roundtrip_sample": 10.0, "roundtrip_line": 20.0},
                {"index": 1, "latitude": 2.0, "longitude": 4.0, "roundtrip_sample": 30.0, "roundtrip_line": 40.0},
            ]
        }
        cpp_result = {
            "points": [
                {"index": 0, "latitude": 1.5, "longitude": 2.0, "roundtrip_sample": 11.0, "roundtrip_line": 20.0},
                {"index": 2, "latitude": 9.0, "longitude": 9.0, "roundtrip_sample": 9.0, "roundtrip_line": 9.0},
            ]
        }

        comparison = benchmark.compare_camera_results("camera_a", py_result, cpp_result, top_error_count=5)

        self.assertEqual(comparison["matched_point_count"], 1)
        self.assertEqual(comparison["missing_in_pyisis"], [2])
        self.assertEqual(comparison["missing_in_cpp"], [1])
        self.assertAlmostEqual(comparison["stats"]["latitude_abs_max"], 0.5)
        self.assertAlmostEqual(comparison["stats"]["sample_abs_max"], 1.0)
        self.assertEqual(comparison["top_errors"][0]["index"], 0)

    def test_prepare_run_directory_writes_config_snapshot_and_manifest(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "benchmark.json"
            write_config(config_path)
            config = benchmark.load_benchmark_config(config_path, repo_root=PROJECT_ROOT)
            run_dir = benchmark.prepare_run_directory(config, output_root=temp_dir / "out", dry_run=True)

            self.assertTrue((run_dir / "experiment_config.json").is_file())
            manifest = json.loads((run_dir / "experiment_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["run_id"], "unit_benchmark")
            self.assertTrue(manifest["dry_run"])
            self.assertEqual(manifest["tasks"], ["camera_small", "net_small"])
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_isis_cpp_pyisis_benchmark_unit_test -v
```

Expected: missing comparison and manifest functions.

- [ ] **Step 3: Implement comparison and manifest helpers**

Add imports:

```python
import csv
import math
import shutil
from datetime import datetime, timezone
```

Add:

```python
def compare_camera_results(
    label: str,
    pyisis_result: dict[str, Any],
    cpp_result: dict[str, Any],
    *,
    top_error_count: int,
) -> dict[str, Any]:
    py_points = {int(point["index"]): point for point in pyisis_result.get("points", [])}
    cpp_points = {int(point["index"]): point for point in cpp_result.get("points", [])}
    matched_indices = sorted(set(py_points) & set(cpp_points))
    missing_in_pyisis = sorted(set(cpp_points) - set(py_points))
    missing_in_cpp = sorted(set(py_points) - set(cpp_points))

    rows: list[dict[str, Any]] = []
    for index in matched_indices:
        py_point = py_points[index]
        cpp_point = cpp_points[index]
        row = {
            "label": label,
            "index": index,
            "latitude_abs": abs(float(py_point["latitude"]) - float(cpp_point["latitude"])),
            "longitude_abs": abs(float(py_point["longitude"]) - float(cpp_point["longitude"])),
            "sample_abs": abs(float(py_point["roundtrip_sample"]) - float(cpp_point["roundtrip_sample"])),
            "line_abs": abs(float(py_point["roundtrip_line"]) - float(cpp_point["roundtrip_line"])),
        }
        row["combined_error"] = row["latitude_abs"] + row["longitude_abs"] + row["sample_abs"] + row["line_abs"]
        rows.append(row)

    return {
        "label": label,
        "matched_point_count": len(matched_indices),
        "missing_in_pyisis": missing_in_pyisis,
        "missing_in_cpp": missing_in_cpp,
        "stats": _camera_error_stats(rows),
        "top_errors": sorted(rows, key=lambda row: row["combined_error"], reverse=True)[:top_error_count],
    }


def _camera_error_stats(rows: list[dict[str, Any]]) -> dict[str, float | None]:
    stats: dict[str, float | None] = {}
    for key in ("latitude_abs", "longitude_abs", "sample_abs", "line_abs"):
        values = [float(row[key]) for row in rows]
        if not values:
            stats[f"{key}_max"] = None
            stats[f"{key}_mean"] = None
            stats[f"{key}_rms"] = None
        else:
            stats[f"{key}_max"] = max(values)
            stats[f"{key}_mean"] = sum(values) / len(values)
            stats[f"{key}_rms"] = math.sqrt(sum(value * value for value in values) / len(values))
    return stats


def prepare_run_directory(config: BenchmarkConfig, *, output_root: str | Path, dry_run: bool) -> Path:
    output_root = Path(output_root).expanduser().resolve()
    run_dir = output_root / config.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "pyisis").mkdir(exist_ok=True)
    (run_dir / "cpp").mkdir(exist_ok=True)
    (run_dir / "reports").mkdir(exist_ok=True)
    shutil.copyfile(config.config_path, run_dir / "experiment_config.json")
    manifest = {
        "run_id": config.run_id,
        "description": config.description,
        "dry_run": dry_run,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tasks": [task.label for task in config.camera_tasks] + [task.label for task in config.controlnet_tasks],
        "cpp_benchmark_path": str(config.execution.cpp_benchmark_path),
    }
    (run_dir / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return run_dir
```

- [ ] **Step 4: Add report writer functions**

Add:

```python
def write_summary_reports(run_dir: Path, results: list[dict[str, Any]], camera_comparisons: list[dict[str, Any]]) -> None:
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    summary = {"results": results, "camera_comparisons": camera_comparisons}
    (reports_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_summary_csv(reports_dir / "summary.csv", results)
    _write_camera_top_errors(reports_dir / "camera_top_errors.csv", camera_comparisons)
    controlnet_results = [result for result in results if result.get("task_type") == "controlnet"]
    (reports_dir / "controlnet_summary.json").write_text(
        json.dumps({"results": controlnet_results}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_summary_csv(path: Path, results: list[dict[str, Any]]) -> None:
    columns = ["label", "task_type", "implementation", "status", "core_seconds", "wall_seconds", "point_count", "measure_count", "successful_point_count"]
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        for result in results:
            writer.writerow({column: result.get(column) for column in columns})


def _write_camera_top_errors(path: Path, comparisons: list[dict[str, Any]]) -> None:
    columns = ["label", "index", "combined_error", "latitude_abs", "longitude_abs", "sample_abs", "line_abs"]
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        for comparison in comparisons:
            for row in comparison.get("top_errors", []):
                writer.writerow({column: row.get(column) for column in columns})
```

- [ ] **Step 5: Run tests and commit**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_isis_cpp_pyisis_benchmark_unit_test -v
```

Expected: all current tests pass.

Commit:

```bash
git add examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py
git commit -m "feat: add benchmark reporting helpers"
```

---

### Task 4: C++ Benchmark Executable and CMake Target

**Files:**
- Create: `tools/benchmarks/isis_cpp_benchmark.cpp`
- Modify: `CMakeLists.txt`
- Test: `tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py`

- [ ] **Step 1: Add Python schema parsing test for C++ JSON**

Append:

```python
    def test_load_json_result_rejects_wrong_implementation(self):
        with temporary_directory() as temp_dir:
            result_path = temp_dir / "result.json"
            result_path.write_text(json.dumps({"implementation": "pyisis"}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Expected cpp result"):
                benchmark.load_cpp_result(result_path)

    def test_load_json_result_accepts_cpp_result(self):
        with temporary_directory() as temp_dir:
            result_path = temp_dir / "result.json"
            result_path.write_text(json.dumps({"implementation": "cpp", "task_type": "camera"}), encoding="utf-8")

            result = benchmark.load_cpp_result(result_path)

        self.assertEqual(result["task_type"], "camera")
```

- [ ] **Step 2: Implement JSON result loader**

Add:

```python
def load_cpp_result(path: str | Path) -> dict[str, Any]:
    path = Path(path).expanduser().resolve()
    with path.open(encoding="utf-8") as result_file:
        payload = json.load(result_file)
    if not isinstance(payload, dict):
        raise ValueError("C++ result must be a JSON object")
    if payload.get("implementation") != "cpp":
        raise ValueError("Expected cpp result")
    return payload
```

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_isis_cpp_pyisis_benchmark_unit_test -v
```

Expected: all Python tests pass.

- [ ] **Step 3: Create C++ executable**

Create `tools/benchmarks/isis_cpp_benchmark.cpp`:

```cpp
// Direct ISIS C++ benchmark executable for PyISIS comparison.
//
// Author: Geng Xun
// Created: 2026-05-23

#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "Camera.h"
#include "ControlMeasure.h"
#include "ControlNet.h"
#include "ControlPoint.h"
#include "Cube.h"
#include "FileName.h"
#include "IException.h"

namespace {

struct Options {
  std::string mode;
  std::string label;
  std::string cube_path;
  std::string net_path;
  std::string output_path;
  int sample_step = 10;
  int line_step = 10;
  int max_points = 0;
};

struct CameraSample {
  int index;
  double sample;
  double line;
};

double seconds_since(std::chrono::steady_clock::time_point start) {
  return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
}

std::string escape_json(const std::string &value) {
  std::ostringstream out;
  for (char ch : value) {
    switch (ch) {
      case '"': out << "\\\""; break;
      case '\\': out << "\\\\"; break;
      case '\n': out << "\\n"; break;
      case '\r': out << "\\r"; break;
      case '\t': out << "\\t"; break;
      default: out << ch; break;
    }
  }
  return out.str();
}

std::string qstring_to_string(const QString &value) {
  return value.toStdString();
}

void require_value(int &index, int argc, char **argv, const std::string &flag) {
  if (index + 1 >= argc) {
    throw std::runtime_error(flag + " requires a value");
  }
}

Options parse_options(int argc, char **argv) {
  if (argc < 2) {
    throw std::runtime_error("usage: isis_cpp_benchmark <camera|controlnet> [options]");
  }
  Options options;
  options.mode = argv[1];
  for (int i = 2; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg == "--label") {
      require_value(i, argc, argv, arg);
      options.label = argv[++i];
    } else if (arg == "--cube") {
      require_value(i, argc, argv, arg);
      options.cube_path = argv[++i];
    } else if (arg == "--net") {
      require_value(i, argc, argv, arg);
      options.net_path = argv[++i];
    } else if (arg == "--output") {
      require_value(i, argc, argv, arg);
      options.output_path = argv[++i];
    } else if (arg == "--sample-step") {
      require_value(i, argc, argv, arg);
      options.sample_step = std::stoi(argv[++i]);
    } else if (arg == "--line-step") {
      require_value(i, argc, argv, arg);
      options.line_step = std::stoi(argv[++i]);
    } else if (arg == "--max-points") {
      require_value(i, argc, argv, arg);
      options.max_points = std::stoi(argv[++i]);
    } else {
      throw std::runtime_error("unknown argument: " + arg);
    }
  }
  if (options.label.empty()) {
    throw std::runtime_error("--label is required");
  }
  if (options.output_path.empty()) {
    throw std::runtime_error("--output is required");
  }
  return options;
}

std::vector<int> axis_positions(int max_value, int step) {
  if (max_value <= 0 || step <= 0) {
    throw std::runtime_error("axis size and step must be positive");
  }
  std::vector<int> values;
  for (int value = 1; value <= max_value; value += step) {
    values.push_back(value);
  }
  if (values.back() != max_value) {
    values.push_back(max_value);
  }
  return values;
}

std::vector<CameraSample> generate_samples(int sample_count, int line_count, int sample_step, int line_step, int max_points) {
  std::vector<CameraSample> samples;
  std::vector<int> sample_values = axis_positions(sample_count, sample_step);
  std::vector<int> line_values = axis_positions(line_count, line_step);
  for (int line : line_values) {
    for (int sample : sample_values) {
      samples.push_back(CameraSample{static_cast<int>(samples.size()), static_cast<double>(sample), static_cast<double>(line)});
      if (max_points > 0 && static_cast<int>(samples.size()) >= max_points) {
        return samples;
      }
    }
  }
  return samples;
}

void write_camera_result(const Options &options) {
  if (options.cube_path.empty()) {
    throw std::runtime_error("--cube is required for camera mode");
  }
  Isis::Cube cube;
  cube.open(QString::fromStdString(options.cube_path), "r");
  Isis::Camera *camera = cube.camera();
  std::vector<CameraSample> samples = generate_samples(camera->Samples(), camera->Lines(), options.sample_step, options.line_step, options.max_points);

  int failed_set_image_count = 0;
  int failed_set_universal_ground_count = 0;
  std::ostringstream points_json;
  bool first_point = true;
  auto start = std::chrono::steady_clock::now();
  int success_count = 0;
  for (const CameraSample &sample : samples) {
    if (!camera->SetImage(sample.sample, sample.line)) {
      ++failed_set_image_count;
      continue;
    }
    double latitude = camera->UniversalLatitude();
    double longitude = camera->UniversalLongitude();
    if (!camera->SetUniversalGround(latitude, longitude)) {
      ++failed_set_universal_ground_count;
      continue;
    }
    if (!first_point) {
      points_json << ",\n";
    }
    first_point = false;
    ++success_count;
    points_json << "    {\"index\":" << sample.index
                << ",\"input_sample\":" << std::setprecision(17) << sample.sample
                << ",\"input_line\":" << std::setprecision(17) << sample.line
                << ",\"latitude\":" << std::setprecision(17) << latitude
                << ",\"longitude\":" << std::setprecision(17) << longitude
                << ",\"roundtrip_sample\":" << std::setprecision(17) << camera->Sample()
                << ",\"roundtrip_line\":" << std::setprecision(17) << camera->Line()
                << "}";
  }
  double core_seconds = seconds_since(start);
  cube.close();

  std::ofstream out(options.output_path);
  out << "{\n"
      << "  \"task_type\": \"camera\",\n"
      << "  \"implementation\": \"cpp\",\n"
      << "  \"label\": \"" << escape_json(options.label) << "\",\n"
      << "  \"cube_path\": \"" << escape_json(options.cube_path) << "\",\n"
      << "  \"input_point_count\": " << samples.size() << ",\n"
      << "  \"successful_point_count\": " << success_count << ",\n"
      << "  \"failed_set_image_count\": " << failed_set_image_count << ",\n"
      << "  \"failed_set_universal_ground_count\": " << failed_set_universal_ground_count << ",\n"
      << "  \"core_seconds\": " << std::setprecision(17) << core_seconds << ",\n"
      << "  \"average_successful_point_seconds\": " << (success_count > 0 ? core_seconds / success_count : 0.0) << ",\n"
      << "  \"points\": [\n" << points_json.str() << "\n  ]\n"
      << "}\n";
}

void write_controlnet_result(const Options &options) {
  if (options.net_path.empty()) {
    throw std::runtime_error("--net is required for controlnet mode");
  }
  auto load_start = std::chrono::steady_clock::now();
  Isis::ControlNet control_net(QString::fromStdString(options.net_path));
  double load_seconds = seconds_since(load_start);

  std::map<std::string, int> serial_counts;
  auto traverse_start = std::chrono::steady_clock::now();
  for (int point_index = 0; point_index < control_net.GetNumPoints(); ++point_index) {
    Isis::ControlPoint *point = control_net.GetPoint(point_index);
    (void) point->GetId();
    (void) point->GetPointTypeString();
    (void) point->IsIgnored();
    (void) point->IsEditLocked();
    for (int measure_index = 0; measure_index < point->GetNumMeasures(); ++measure_index) {
      Isis::ControlMeasure *measure = point->GetMeasure(measure_index);
      std::string serial = qstring_to_string(measure->GetCubeSerialNumber());
      serial_counts[serial] += 1;
      (void) measure->GetSample();
      (void) measure->GetLine();
      (void) measure->GetMeasureTypeString();
      (void) measure->IsIgnored();
      (void) measure->IsEditLocked();
    }
  }
  double traverse_seconds = seconds_since(traverse_start);

  std::ofstream out(options.output_path);
  out << "{\n"
      << "  \"task_type\": \"controlnet\",\n"
      << "  \"implementation\": \"cpp\",\n"
      << "  \"label\": \"" << escape_json(options.label) << "\",\n"
      << "  \"net_path\": \"" << escape_json(options.net_path) << "\",\n"
      << "  \"point_count\": " << control_net.GetNumPoints() << ",\n"
      << "  \"measure_count\": " << control_net.GetNumMeasures() << ",\n"
      << "  \"valid_point_count\": " << control_net.GetNumValidPoints() << ",\n"
      << "  \"valid_measure_count\": " << control_net.GetNumValidMeasures() << ",\n"
      << "  \"load_seconds\": " << std::setprecision(17) << load_seconds << ",\n"
      << "  \"traverse_seconds\": " << std::setprecision(17) << traverse_seconds << ",\n"
      << "  \"core_seconds\": " << std::setprecision(17) << (load_seconds + traverse_seconds) << ",\n"
      << "  \"serial_measure_counts\": {";
  bool first = true;
  for (const auto &entry : serial_counts) {
    if (!first) {
      out << ", ";
    }
    first = false;
    out << "\"" << escape_json(entry.first) << "\": " << entry.second;
  }
  out << "}\n}\n";
}

}  // namespace

int main(int argc, char **argv) {
  try {
    Options options = parse_options(argc, argv);
    if (options.mode == "camera") {
      write_camera_result(options);
    } else if (options.mode == "controlnet") {
      write_controlnet_result(options);
    } else {
      throw std::runtime_error("mode must be camera or controlnet");
    }
    return EXIT_SUCCESS;
  } catch (const Isis::IException &error) {
    std::cerr << error.toString().toStdString() << std::endl;
  } catch (const std::exception &error) {
    std::cerr << error.what() << std::endl;
  }
  return EXIT_FAILURE;
}
```

- [ ] **Step 4: Add CMake target**

Modify `CMakeLists.txt` after the `_isis_core` target setup and before `install(...)`:

```cmake
add_executable(isis_cpp_benchmark
  tools/benchmarks/isis_cpp_benchmark.cpp)

target_compile_definitions(isis_cpp_benchmark
  PRIVATE
    _GNU_SOURCE)

target_include_directories(isis_cpp_benchmark
  PRIVATE
    "${ISIS_INCLUDE_DIR}"
    "${ISIS_DEP_INCLUDE_DIR}"
    "${ISIS_DEP_INCLUDE_DIR}/cspice"
    "${ISIS_DEP_INCLUDE_DIR}/qt"
    "${ISIS_DEP_INCLUDE_DIR}/qt/QtCore"
    ${Qt5Core_INCLUDE_DIRS})

target_link_libraries(isis_cpp_benchmark
  PRIVATE
    "${ISIS_CORE_LIBRARY}"
    ${ISIS_EXTRA_CAMERA_LIBS}
    ${ISIS_EXTRA_PROJECTION_LIBS}
    ${BULLET_RUNTIME_LIBS}
    Qt5::Core)

set_target_properties(isis_cpp_benchmark PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/tools/benchmarks"
  BUILD_RPATH "${ISIS_LIBRARY_DIR}"
  INSTALL_RPATH "${ISIS_LIBRARY_DIR}")
```

- [ ] **Step 5: Build target and commit**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" \
  -DISIS_PREFIX="$ISIS_PREFIX" \
  -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON \
  -DCMAKE_CXX_COMPILER="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-c++"
cmake --build build --target isis_cpp_benchmark -j"$(nproc)"
python -m unittest tests.unitTest.controlnet_construct_isis_cpp_pyisis_benchmark_unit_test -v
```

Expected: CMake config succeeds, `isis_cpp_benchmark` builds, and Python tests pass.

Commit:

```bash
git add CMakeLists.txt tools/benchmarks/isis_cpp_benchmark.cpp \
  examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py
git commit -m "feat: add direct isis cpp benchmark tool"
```

---

### Task 5: Runner Execution, C++ Commands, and Failure Handling

**Files:**
- Modify: `examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py`
- Test: `tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py`

- [ ] **Step 1: Add failing command generation and dry-run tests**

Append:

```python
    def test_build_cpp_camera_command_contains_matching_sampling_args(self):
        task = benchmark.CameraTaskConfig(
            label="camera_a",
            cube_path=Path("/tmp/a.cub"),
            sample_step=10,
            line_step=20,
            max_points=30,
            top_error_count=5,
        )
        command = benchmark.build_cpp_camera_command(Path("/bin/cppbench"), task, Path("/tmp/out.json"))

        self.assertEqual(command[0], "/bin/cppbench")
        self.assertIn("camera", command)
        self.assertIn("--sample-step", command)
        self.assertIn("10", command)
        self.assertIn("--line-step", command)
        self.assertIn("20", command)
        self.assertIn("--max-points", command)
        self.assertIn("30", command)

    def test_run_cpp_command_records_failure_without_raising_when_keep_going(self):
        result = benchmark.run_cpp_command(
            label="bad",
            task_type="camera",
            command=["/bin/sh", "-c", "echo failure >&2; exit 7"],
            output_path=Path("/tmp/nonexistent.json"),
            keep_going=True,
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["return_code"], 7)
        self.assertIn("failure", result["stderr"])
```

- [ ] **Step 2: Implement C++ command helpers and subprocess wrapper**

Add import:

```python
import subprocess
```

Add:

```python
def build_cpp_camera_command(cpp_benchmark_path: Path, task: CameraTaskConfig, output_path: Path) -> list[str]:
    command = [
        str(cpp_benchmark_path),
        "camera",
        "--label",
        task.label,
        "--cube",
        str(task.cube_path),
        "--sample-step",
        str(task.sample_step),
        "--line-step",
        str(task.line_step),
        "--output",
        str(output_path),
    ]
    if task.max_points is not None:
        command.extend(["--max-points", str(task.max_points)])
    return command


def build_cpp_controlnet_command(cpp_benchmark_path: Path, task: ControlNetTaskConfig, output_path: Path) -> list[str]:
    return [
        str(cpp_benchmark_path),
        "controlnet",
        "--label",
        task.label,
        "--net",
        str(task.net_path),
        "--output",
        str(output_path),
    ]


def run_cpp_command(
    *,
    label: str,
    task_type: str,
    command: list[str],
    output_path: Path,
    keep_going: bool,
) -> dict[str, Any]:
    start = time.perf_counter()
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    wall_seconds = time.perf_counter() - start
    if completed.returncode != 0:
        failure = {
            "label": label,
            "task_type": task_type,
            "implementation": "cpp",
            "status": "failed",
            "return_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "command": command,
            "wall_seconds": wall_seconds,
        }
        if not keep_going:
            raise RuntimeError(f"C++ benchmark failed for {label}: {completed.stderr.strip()}")
        return failure
    result = load_cpp_result(output_path)
    result["status"] = "success"
    result["return_code"] = completed.returncode
    result["stdout"] = completed.stdout
    result["stderr"] = completed.stderr
    result["command"] = command
    result["wall_seconds"] = wall_seconds
    return result
```

- [ ] **Step 3: Implement run orchestration and CLI flags**

Replace `main` with:

```python
def run_benchmark(
    config: BenchmarkConfig,
    *,
    output_root: str | Path,
    dry_run: bool,
    only: set[str] | None,
    keep_going: bool,
) -> Path:
    selected = only if only else None
    run_dir = prepare_run_directory(config, output_root=output_root, dry_run=dry_run)
    if dry_run:
        _write_dry_run_commands(config, run_dir, selected)
        return run_dir

    results: list[dict[str, Any]] = []
    camera_comparisons: list[dict[str, Any]] = []
    for task in config.camera_tasks:
        if selected is not None and task.label not in selected:
            continue
        py_result = run_pyisis_camera_task(task)
        py_result["status"] = "success"
        py_output = run_dir / "pyisis" / f"{task.label}.json"
        py_output.write_text(json.dumps(py_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        cpp_output = run_dir / "cpp" / f"{task.label}.json"
        command = build_cpp_camera_command(config.execution.cpp_benchmark_path, task, cpp_output)
        _write_command(run_dir / "cpp" / task.label / "command.sh", command)
        cpp_result = run_cpp_command(label=task.label, task_type="camera", command=command, output_path=cpp_output, keep_going=keep_going)
        results.extend([py_result, cpp_result])
        if cpp_result.get("status") == "success":
            camera_comparisons.append(compare_camera_results(task.label, py_result, cpp_result, top_error_count=task.top_error_count))

    for task in config.controlnet_tasks:
        if selected is not None and task.label not in selected:
            continue
        py_result = run_pyisis_controlnet_task(task)
        py_result["status"] = "success"
        py_output = run_dir / "pyisis" / f"{task.label}.json"
        py_output.write_text(json.dumps(py_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        cpp_output = run_dir / "cpp" / f"{task.label}.json"
        command = build_cpp_controlnet_command(config.execution.cpp_benchmark_path, task, cpp_output)
        _write_command(run_dir / "cpp" / task.label / "command.sh", command)
        cpp_result = run_cpp_command(label=task.label, task_type="controlnet", command=command, output_path=cpp_output, keep_going=keep_going)
        results.extend([py_result, cpp_result])

    write_summary_reports(run_dir, results, camera_comparisons)
    return run_dir


def _write_command(path: Path, command: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + " ".join(_shell_quote(part) for part in command) + "\n", encoding="utf-8")
    path.chmod(0o755)


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _write_dry_run_commands(config: BenchmarkConfig, run_dir: Path, selected: set[str] | None) -> None:
    for task in config.camera_tasks:
        if selected is not None and task.label not in selected:
            continue
        command = build_cpp_camera_command(config.execution.cpp_benchmark_path, task, run_dir / "cpp" / f"{task.label}.json")
        _write_command(run_dir / "cpp" / task.label / "command.sh", command)
    for task in config.controlnet_tasks:
        if selected is not None and task.label not in selected:
            continue
        command = build_cpp_controlnet_command(config.execution.cpp_benchmark_path, task, run_dir / "cpp" / f"{task.label}.json")
        _write_command(run_dir / "cpp" / task.label / "command.sh", command)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config")
    parser.add_argument("--output-root", default="work/isis_cpp_pyisis_benchmark")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", default="")
    parser.add_argument("--keep-going", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--cpp-benchmark-path")
    args = parser.parse_args(argv)

    config = load_benchmark_config(args.config)
    if args.cpp_benchmark_path:
        config = BenchmarkConfig(
            run_id=config.run_id,
            description=config.description,
            execution=ExecutionConfig(
                cpp_benchmark_path=Path(args.cpp_benchmark_path).expanduser().resolve(),
                repeat_count=config.execution.repeat_count,
                keep_intermediate_json=config.execution.keep_intermediate_json,
            ),
            camera_tasks=config.camera_tasks,
            controlnet_tasks=config.controlnet_tasks,
            config_path=config.config_path,
        )
    only = {value.strip() for value in args.only.split(",") if value.strip()} or None
    keep_going = args.keep_going or not args.fail_fast
    run_dir = run_benchmark(config, output_root=args.output_root, dry_run=args.dry_run, only=only, keep_going=keep_going)
    print(f"Benchmark run directory: {run_dir}")
    return 0
```

- [ ] **Step 4: Run dry-run smoke and tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_isis_cpp_pyisis_benchmark_unit_test -v
python examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json \
  --output-root work/isis_cpp_pyisis_benchmark \
  --dry-run
```

Expected: tests pass, dry-run creates `work/isis_cpp_pyisis_benchmark/lro_nac_pyisis_cpp_20260523/experiment_manifest.json` and per-task `command.sh` files.

Commit:

```bash
git add examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py
git commit -m "feat: orchestrate isis benchmark runs"
```

---

### Task 6: Fixture Smoke Run and Documentation

**Files:**
- Modify: `examples/controlnet_construct/experiments/README.md`
- Modify: `examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py`
- Test: `tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py`

- [ ] **Step 1: Run fixture smoke with real PyISIS and C++**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
cmake --build build --target isis_cpp_benchmark -j"$(nproc)"
python examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json \
  --output-root work/isis_cpp_pyisis_benchmark \
  --keep-going
```

Expected: the command exits 0 and writes `reports/summary.json`, `reports/summary.csv`, `reports/camera_top_errors.csv`, and `reports/controlnet_summary.json`.

- [ ] **Step 2: Inspect summary for schema and status**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path
path = Path("work/isis_cpp_pyisis_benchmark/lro_nac_pyisis_cpp_20260523/reports/summary.json")
payload = json.loads(path.read_text())
print(len(payload["results"]))
print(sorted({item["implementation"] for item in payload["results"]}))
print(sorted({item["status"] for item in payload["results"]}))
PY
```

Expected: implementations include `cpp` and `pyisis`; statuses include only `success` for fixture smoke. If the LRO NAC fixture lacks mock SPICE support, reduce the camera smoke to a repo camera fixture known to support `camera.set_image` under mock `ISISDATA`, and keep the production LRO NAC path in the example config for real runs.

- [ ] **Step 3: Add README instructions**

Append to `examples/controlnet_construct/experiments/README.md`:

```markdown
## ISIS C++ vs PyISIS Benchmark

`isis_cpp_pyisis_benchmark.py` compares direct ISIS C++ calls against PyISIS for
camera coordinate conversion and ControlNet traversal. It is a benchmark harness,
not a ControlNet construction pipeline.

Build the C++ benchmark first:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
cmake --build build --target isis_cpp_benchmark -j"$(nproc)"
```

Dry-run:

```bash
python examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json \
  --output-root work/isis_cpp_pyisis_benchmark \
  --dry-run
```

Fixture smoke:

```bash
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json \
  --output-root work/isis_cpp_pyisis_benchmark \
  --keep-going
```

For real LRO NAC performance runs, set production `ISISDATA` and point the
config at production CUBE and ControlNet files. Remove `max_points` from a
camera task when you want full-grid sampling at the configured step.
```

- [ ] **Step 4: Run documentation-safe verification and commit**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_isis_cpp_pyisis_benchmark_unit_test -v
python examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json \
  --output-root work/isis_cpp_pyisis_benchmark \
  --dry-run
```

Expected: tests and dry-run pass.

Commit:

```bash
git add examples/controlnet_construct/experiments/README.md \
  examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py
git commit -m "docs: document isis cpp pyisis benchmark"
```

---

### Task 7: Final Verification and Branch Handoff

**Files:**
- No code changes expected.

- [ ] **Step 1: Run smoke import**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tests/smoke_import.py
```

Expected: exits 0.

- [ ] **Step 2: Run focused benchmark tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_isis_cpp_pyisis_benchmark_unit_test -v
```

Expected: all tests pass.

- [ ] **Step 3: Rebuild C++ benchmark target**

Run:

```bash
cmake --build build --target isis_cpp_benchmark -j"$(nproc)"
```

Expected: target builds without errors.

- [ ] **Step 4: Run dry-run CLI**

Run:

```bash
python examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json \
  --output-root work/isis_cpp_pyisis_benchmark \
  --dry-run
```

Expected: command exits 0 and writes current command scripts.

- [ ] **Step 5: Run fixture smoke if mock ISISDATA supports the chosen fixtures**

Run:

```bash
python examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py \
  examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.example.json \
  --output-root work/isis_cpp_pyisis_benchmark \
  --keep-going
```

Expected: command exits 0. If a camera fixture cannot initialize under mock `ISISDATA`, document that limitation in the final handoff and keep dry-run plus unit tests as automated verification evidence.

- [ ] **Step 6: Check worktree status**

Run:

```bash
git status --short --branch
```

Expected: only intentional untracked benchmark output under `work/` or a clean tree. Do not commit generated `work/` output.

- [ ] **Step 7: Final handoff**

Report:

- branch name and worktree path
- commits created
- verification commands and pass/fail status
- whether fixture smoke ran with real camera data or was limited by mock `ISISDATA`
- exact command for production LRO NAC runs with production `ISISDATA`
