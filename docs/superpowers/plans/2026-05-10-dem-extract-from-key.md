# DEM Extract From Key Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone `examples/dem_extract` from-key pipeline that reads paired `.key` files, runs ISIS `Stereo.elevation`, rasterizes radius values into an ISIS Cube DEM, and writes point-cloud/summary sidecars.

**Architecture:** Add a focused `examples/dem_extract` package parallel to `examples/controlnet_construct`, sharing only the existing `.key` reader and ISIS sample/line convention. Keep data loading, triangulation, grid aggregation, cube writing, and CLI orchestration in separate modules so each part can be unit-tested with fakes before any ISIS-heavy integration checks. The first pass requires a projected ISIS cube as `map_template_cube`; pure PVL projection construction and tutorial docs stay outside this first pass.

**Tech Stack:** Python 3.11 in the `asp360_new` conda environment, `unittest`, `argparse`, `dataclasses`, `json`, `csv`, `statistics`, `collections`, existing `examples.controlnet_construct.keypoints.read_key_file`, and `isis_pybind` APIs including `Cube`, `Camera.set_image`, `Stereo.elevation`, `Stereo.spherical`, `Projection`, `LineManager`, and `PvlGroup`.

---

## File Structure and Responsibilities

- Create: `examples/dem_extract/__init__.py` — package metadata, version string, and public re-exports for stable helper classes/functions.
- Create: `examples/dem_extract/runtime.py` — optional `isis_pybind` import boundary, cube open/close helpers, JSON/JSONL/CSV-ish sidecar writers, and summary counter helpers.
- Create: `examples/dem_extract/key_pairs.py` — load left/right `.key` files via `examples.controlnet_construct.keypoints.read_key_file`, validate synchronized point counts and cube image bounds, and yield immutable point-pair records.
- Create: `examples/dem_extract/triangulation.py` — open left/right cubes once, fetch cameras once, call `Camera.set_image`, `ip.Stereo.elevation`, and `ip.Stereo.spherical`, preserve per-point status/reason, and apply geometry filters.
- Create: `examples/dem_extract/grid.py` — map latitude/longitude to template-grid cells through `template_cube.projection()`, aggregate cell radius values using `median`, `mean`, or `min-error`, and fill empty cells with nodata.
- Create: `examples/dem_extract/cube_writer.py` — preflight binding capabilities and write one-band radius DEM cubes using `Cube.set_dimensions`, `Cube.create`, `Cube.put_group`, `ip.LineManager`, and `Cube.write(...)`.
- Create: `examples/dem_extract/isis_stereo_dem.py` — CLI entry point with `from-key` subcommand, positional args, kebab-case flags, compact JSON stdout, and non-zero exits for invalid run-level inputs.
- Create: `tests/unitTest/dem_extract_unit_test.py` — focused unit tests with fakes for `.key` loading, triangulation lifecycle, filtering counters, grid aggregation, writer preflight, sidecar output, and CLI surface.
- Optionally create out-of-first-pass: `examples/dem_extract/usage.md` — user-facing examples after the CLI and cube writer behavior are stable; do not include this file in the first implementation unless documentation is explicitly added to the acceptance scope.

## Shared Interface Contracts

All tasks use these dataclass names and field names consistently:

```python
@dataclass(frozen=True, slots=True)
class KeyPointPair:
    index: int
    left_sample: float
    left_line: float
    right_sample: float
    right_line: float

@dataclass(frozen=True, slots=True)
class TriangulatedPoint:
    index: int
    left_sample: float
    left_line: float
    right_sample: float
    right_line: float
    status: str
    reason: str
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    radius_m: float | None = None
    sepang_deg: float | None = None
    intersection_error_m: float | None = None
    x_km: float | None = None
    y_km: float | None = None
    z_km: float | None = None

@dataclass(frozen=True, slots=True)
class FilterOptions:
    max_error_m: float | None = None
    min_sepang_deg: float | None = None
    min_radius_m: float | None = None
    max_radius_m: float | None = None

@dataclass(frozen=True, slots=True)
class GridSpec:
    samples: int
    lines: int
    nodata_value: float

@dataclass(frozen=True, slots=True)
class RasterResult:
    values: list[list[float]]
    rasterized_point_count: int
    filled_cell_count: int
    nodata_value: float = -9999.0
```

Summary JSON counters must include these exact keys: `input_left_cube`, `input_right_cube`, `input_left_key`, `input_right_key`, `map_template`, `output_dem_cube`, `input_point_count`, `success_count`, `failed_set_image_count`, `failed_elevation_count`, `filtered_error_count`, `filtered_sepang_count`, `filtered_radius_count`, `rasterized_point_count`, `filled_cell_count`, `max_error_m`, `min_sepang_deg`, `aggregation`, and `value_type`.

## Task 1: Package Runtime Bootstrap and Metadata

**Files:**
- Create: `examples/dem_extract/__init__.py`
- Create: `examples/dem_extract/runtime.py`
- Test: `tests/unitTest/dem_extract_unit_test.py`

- [ ] **Step 1: Write failing package bootstrap tests**

Add the test file with the repository test metadata header and path setup:

```python
"""
Unit tests for the DEM extract example package.

Author: Geng Xun
Created: 2026-05-10
Last Modified: 2026-05-10
"""

from __future__ import annotations

import json
import sys
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dem_extract'`.

- [ ] **Step 3: Add package metadata and runtime helpers**

Create `examples/dem_extract/__init__.py`:

```python
"""Standalone ISIS stereo DEM extraction helpers."""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
```

Create `examples/dem_extract/runtime.py`:

```python
"""Runtime helpers for the DEM extraction example."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def import_isis_pybind():
    """Import the installed isis_pybind module at runtime."""
    import isis_pybind as ip

    return ip


def write_summary_json(output_path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: PASS for the two bootstrap tests.

- [ ] **Step 5: Commit bootstrap slice**

Run:

```bash
git add examples/dem_extract/__init__.py examples/dem_extract/runtime.py tests/unitTest/dem_extract_unit_test.py
git commit -m "feat: bootstrap dem_extract package"
```

Expected: commit succeeds with only those three files staged.

## Task 2: Key Pair Loading and Validation

**Files:**
- Create/modify: `examples/dem_extract/key_pairs.py`
- Modify: `examples/dem_extract/__init__.py`
- Test: `tests/unitTest/dem_extract_unit_test.py`

- [ ] **Step 1: Write failing `.key` pair tests**

Append tests using temporary files under `build/` only:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dem_extract.key_pairs'`.

- [ ] **Step 3: Implement key pair module**

Create `examples/dem_extract/key_pairs.py`:

```python
"""Load and validate synchronized left/right .key point pairs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    from examples.controlnet_construct.keypoints import read_key_file
except ModuleNotFoundError:
    from controlnet_construct.keypoints import read_key_file


@dataclass(frozen=True, slots=True)
class KeyPointPair:
    index: int
    left_sample: float
    left_line: float
    right_sample: float
    right_line: float


def _cube_size(cube, fallback_width: int, fallback_height: int) -> tuple[int, int]:
    if cube is None:
        return fallback_width, fallback_height
    return int(cube.sample_count()), int(cube.line_count())


def _validate_point(label: str, index: int, sample: float, line: float, samples: int, lines: int) -> None:
    if not (1.0 <= sample <= float(samples)) or not (1.0 <= line <= float(lines)):
        raise ValueError(
            f"{label} point {index} has sample/line ({sample}, {line}) outside "
            f"1..{samples}, 1..{lines}."
        )


def load_key_point_pairs(
    left_key_path: str | Path,
    right_key_path: str | Path,
    *,
    left_cube,
    right_cube,
) -> list[KeyPointPair]:
    left_file = read_key_file(left_key_path)
    right_file = read_key_file(right_key_path)
    if len(left_file.points) != len(right_file.points):
        raise ValueError("Left and right .key files must contain the same number of points.")

    left_samples, left_lines = _cube_size(left_cube, left_file.image_width, left_file.image_height)
    right_samples, right_lines = _cube_size(right_cube, right_file.image_width, right_file.image_height)
    pairs: list[KeyPointPair] = []
    for index, (left, right) in enumerate(zip(left_file.points, right_file.points)):
        _validate_point("left", index, left.sample, left.line, left_samples, left_lines)
        _validate_point("right", index, right.sample, right.line, right_samples, right_lines)
        pairs.append(KeyPointPair(index, left.sample, left.line, right.sample, right.line))
    return pairs
```

Update `examples/dem_extract/__init__.py`:

```python
"""Standalone ISIS stereo DEM extraction helpers."""

from __future__ import annotations

from .key_pairs import KeyPointPair, load_key_point_pairs

__version__ = "0.1.0"

__all__ = ["KeyPointPair", "__version__", "load_key_point_pairs"]
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: PASS for bootstrap and key-pair tests.

- [ ] **Step 5: Commit key-pair slice**

Run:

```bash
git add examples/dem_extract/__init__.py examples/dem_extract/key_pairs.py tests/unitTest/dem_extract_unit_test.py
git commit -m "feat: load dem key point pairs"
```

Expected: commit succeeds.

## Task 3: Triangulation Records, Camera Reuse, and Filtering

**Files:**
- Create: `examples/dem_extract/triangulation.py`
- Modify: `examples/dem_extract/__init__.py`
- Test: `tests/unitTest/dem_extract_unit_test.py`

- [ ] **Step 1: Write failing triangulation lifecycle tests**

Append fake-based tests that do not require real cubes:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dem_extract.triangulation'`.

- [ ] **Step 3: Implement triangulation module**

Create `examples/dem_extract/triangulation.py` with these exact public functions:

```python
"""Triangulate synchronized key-point pairs with ISIS Stereo."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable

from .key_pairs import KeyPointPair


@dataclass(frozen=True, slots=True)
class FilterOptions:
    max_error_m: float | None = None
    min_sepang_deg: float | None = None
    min_radius_m: float | None = None
    max_radius_m: float | None = None


@dataclass(frozen=True, slots=True)
class TriangulatedPoint:
    index: int
    left_sample: float
    left_line: float
    right_sample: float
    right_line: float
    status: str
    reason: str
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    radius_m: float | None = None
    sepang_deg: float | None = None
    intersection_error_m: float | None = None
    x_km: float | None = None
    y_km: float | None = None
    z_km: float | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _base_record(pair: KeyPointPair, status: str, reason: str, **geometry: float | None) -> TriangulatedPoint:
    return TriangulatedPoint(
        pair.index,
        pair.left_sample,
        pair.left_line,
        pair.right_sample,
        pair.right_line,
        status,
        reason,
        **geometry,
    )


def _filter_reason(radius_m: float, sepang_deg: float, error_m: float, filters: FilterOptions) -> str | None:
    if filters.max_error_m is not None and error_m > filters.max_error_m:
        return "filtered_error"
    if filters.min_sepang_deg is not None and sepang_deg < filters.min_sepang_deg:
        return "filtered_sepang"
    if filters.min_radius_m is not None and radius_m < filters.min_radius_m:
        return "filtered_radius"
    if filters.max_radius_m is not None and radius_m > filters.max_radius_m:
        return "filtered_radius"
    return None


def triangulate_pairs(
    pairs: Iterable[KeyPointPair],
    left_cube,
    right_cube,
    ip,
    filters: FilterOptions,
) -> tuple[list[TriangulatedPoint], dict[str, int]]:
    counters = {
        "success_count": 0,
        "failed_set_image_count": 0,
        "failed_elevation_count": 0,
        "filtered_error_count": 0,
        "filtered_sepang_count": 0,
        "filtered_radius_count": 0,
    }
    left_camera = left_cube.camera()
    right_camera = right_cube.camera()
    records: list[TriangulatedPoint] = []
    for pair in pairs:
        if not left_camera.set_image(pair.left_sample, pair.left_line):
            counters["failed_set_image_count"] += 1
            records.append(_base_record(pair, "failed", "left_set_image"))
            continue
        if not right_camera.set_image(pair.right_sample, pair.right_line):
            counters["failed_set_image_count"] += 1
            records.append(_base_record(pair, "failed", "right_set_image"))
            continue
        try:
            success, radius_m, latitude_deg, longitude_deg, sepang_deg, error_m = ip.Stereo.elevation(left_camera, right_camera)
        except Exception as exc:
            counters["failed_elevation_count"] += 1
            records.append(_base_record(pair, "failed", f"elevation:{exc.__class__.__name__}"))
            continue
        if not success:
            counters["failed_elevation_count"] += 1
            records.append(_base_record(pair, "failed", "elevation_false"))
            continue
        x_km, y_km, z_km = ip.Stereo.spherical(latitude_deg, longitude_deg, radius_m)
        reason = _filter_reason(radius_m, sepang_deg, error_m, filters)
        if reason is not None:
            counters[f"{reason}_count"] += 1
            status = "filtered"
        else:
            counters["success_count"] += 1
            reason = ""
            status = "success"
        records.append(_base_record(
            pair,
            status,
            reason,
            latitude_deg=latitude_deg,
            longitude_deg=longitude_deg,
            radius_m=radius_m,
            sepang_deg=sepang_deg,
            intersection_error_m=error_m,
            x_km=x_km,
            y_km=y_km,
            z_km=z_km,
        ))
    return records, counters
```

- [ ] **Step 4: Export triangulation types**

Update `examples/dem_extract/__init__.py`:

```python
from .triangulation import FilterOptions, TriangulatedPoint, triangulate_pairs

__all__ = [
    "FilterOptions",
    "KeyPointPair",
    "TriangulatedPoint",
    "__version__",
    "load_key_point_pairs",
    "triangulate_pairs",
]
```

Keep the existing module docstring, future import, key-pair import, and `__version__` assignment in the same file.

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: PASS for bootstrap, key-pair, and triangulation tests.

- [ ] **Step 6: Commit triangulation slice**

Run:

```bash
git add examples/dem_extract/__init__.py examples/dem_extract/triangulation.py tests/unitTest/dem_extract_unit_test.py
git commit -m "feat: triangulate dem key pairs"
```

Expected: commit succeeds.

## Task 4: Point-Cloud Sidecars and Summary Counters

**Files:**
- Modify: `examples/dem_extract/runtime.py`
- Test: `tests/unitTest/dem_extract_unit_test.py`

- [ ] **Step 1: Write failing sidecar and summary tests**

Append tests:

```python
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
            aggregation="median",
        )

        self.assertEqual(summary["value_type"], "radius_m")
        self.assertEqual(summary["input_point_count"], 4)
        self.assertEqual(summary["failed_set_image_count"], 1)

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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: FAIL with missing `write_point_cloud_jsonl`, `write_quality_summary_json`, and `build_summary` imports.

- [ ] **Step 3: Add output helpers**

Extend `examples/dem_extract/runtime.py`:

```python
from dataclasses import asdict, is_dataclass
from typing import Iterable


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

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [_record_to_dict(record) for record in records]
    fieldnames = [
        "index", "left_sample", "left_line", "right_sample", "right_line", "status", "reason",
        "latitude_deg", "longitude_deg", "radius_m", "sepang_deg", "intersection_error_m", "x_km", "y_km", "z_km",
    ]
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
    max_error_m: float | None,
    min_sepang_deg: float | None,
    aggregation: str,
) -> dict[str, object]:
    summary = {
        "input_left_cube": input_left_cube,
        "input_right_cube": input_right_cube,
        "input_left_key": input_left_key,
        "input_right_key": input_right_key,
        "map_template": map_template,
        "output_dem_cube": output_dem_cube,
        "input_point_count": input_point_count,
        "rasterized_point_count": rasterized_point_count,
        "filled_cell_count": filled_cell_count,
        "max_error_m": max_error_m,
        "min_sepang_deg": min_sepang_deg,
        "aggregation": aggregation,
        "value_type": "radius_m",
    }
    summary.update(triangulation_counters)
    for key in (
        "success_count", "failed_set_image_count", "failed_elevation_count",
        "filtered_error_count", "filtered_sepang_count", "filtered_radius_count",
    ):
        summary.setdefault(key, 0)
    return summary
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: PASS for runtime output and quality-summary tests.

- [ ] **Step 5: Commit sidecar slice**

Run:

```bash
git add examples/dem_extract/runtime.py tests/unitTest/dem_extract_unit_test.py
git commit -m "feat: write dem_extract sidecars"
```

Expected: commit succeeds.

## Task 5: Grid Aggregation and Template Projection Mapping

**Files:**
- Create: `examples/dem_extract/grid.py`
- Modify: `examples/dem_extract/__init__.py`
- Test: `tests/unitTest/dem_extract_unit_test.py`

- [ ] **Step 1: Write failing aggregation and projection tests**

Append tests:

```python
class DemExtractGridUnitTest(unittest.TestCase):
    def test_aggregate_same_cell_supports_median_mean_and_min_error(self):
        from dem_extract.grid import aggregate_cell_values
        from dem_extract.triangulation import TriangulatedPoint

        records = [
            TriangulatedPoint(0, 1, 1, 1, 1, "success", "", 0, 0, 10.0, 1.0, 5.0, 0, 0, 0),
            TriangulatedPoint(1, 1, 1, 1, 1, "success", "", 0, 0, 30.0, 1.0, 1.0, 0, 0, 0),
            TriangulatedPoint(2, 1, 1, 1, 1, "success", "", 0, 0, 50.0, 1.0, 3.0, 0, 0, 0),
        ]

        self.assertEqual(aggregate_cell_values(records, "median"), 30.0)
        self.assertEqual(aggregate_cell_values(records, "mean"), 30.0)
        self.assertEqual(aggregate_cell_values(records, "min-error"), 30.0)

    def test_rasterize_uses_template_projection_world_coordinates_and_nodata(self):
        from dem_extract.grid import GridSpec, rasterize_points
        from dem_extract.triangulation import TriangulatedPoint

        class FakeProjection:
            def __init__(self):
                self.calls = []
            def set_universal_ground(self, latitude, longitude):
                self.calls.append((latitude, longitude))
                return True
            def world_x(self):
                return 2.2
            def world_y(self):
                return 3.8

        class FakeTemplateCube:
            def __init__(self):
                self._projection = FakeProjection()
            def projection(self):
                return self._projection

        template = FakeTemplateCube()
        records = [TriangulatedPoint(0, 1, 1, 1, 1, "success", "", 12.5, 45.0, 100.0, 2.0, 1.0, 0, 0, 0)]

        result = rasterize_points(records, template, GridSpec(samples=4, lines=4, nodata_value=-9999.0), aggregation="median")

        self.assertEqual(template._projection.calls, [(12.5, 45.0)])
        self.assertEqual(result.values[2][1], 100.0)
        self.assertEqual(result.values[0][0], -9999.0)
        self.assertEqual(result.rasterized_point_count, 1)
        self.assertEqual(result.filled_cell_count, 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dem_extract.grid'`.

- [ ] **Step 3: Implement grid module**

Create `examples/dem_extract/grid.py`:

```python
"""Rasterize triangulated radius points onto a projected ISIS template grid."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import mean, median

from .triangulation import TriangulatedPoint


@dataclass(frozen=True, slots=True)
class GridSpec:
    samples: int
    lines: int
    nodata_value: float


@dataclass(frozen=True, slots=True)
class RasterResult:
    values: list[list[float]]
    rasterized_point_count: int
    filled_cell_count: int
    nodata_value: float = -9999.0


def aggregate_cell_values(records: list[TriangulatedPoint], aggregation: str) -> float:
    radii = [record.radius_m for record in records if record.radius_m is not None]
    if not radii:
        raise ValueError("Cannot aggregate a cell without radius values.")
    if aggregation == "median":
        return float(median(radii))
    if aggregation == "mean":
        return float(mean(radii))
    if aggregation == "min-error":
        record = min(records, key=lambda item: float("inf") if item.intersection_error_m is None else item.intersection_error_m)
        if record.radius_m is None:
            raise ValueError("The minimum-error point has no radius value.")
        return float(record.radius_m)
    raise ValueError("aggregation must be one of: median, mean, min-error")


def _record_to_cell(record: TriangulatedPoint, projection, grid_spec: GridSpec) -> tuple[int, int] | None:
    if record.latitude_deg is None or record.longitude_deg is None:
        return None
    if not projection.set_universal_ground(record.latitude_deg, record.longitude_deg):
        return None
    sample_index = int(round(projection.world_x())) - 1
    line_index = int(round(projection.world_y())) - 1
    if 0 <= sample_index < grid_spec.samples and 0 <= line_index < grid_spec.lines:
        return line_index, sample_index
    return None


def rasterize_points(
    records: list[TriangulatedPoint],
    template_cube,
    grid_spec: GridSpec,
    *,
    aggregation: str,
) -> RasterResult:
    projection = template_cube.projection()
    cells: dict[tuple[int, int], list[TriangulatedPoint]] = defaultdict(list)
    rasterized_point_count = 0
    for record in records:
        if record.status != "success" or record.radius_m is None:
            continue
        cell = _record_to_cell(record, projection, grid_spec)
        if cell is None:
            continue
        cells[cell].append(record)
        rasterized_point_count += 1

    values = [[grid_spec.nodata_value for _sample in range(grid_spec.samples)] for _line in range(grid_spec.lines)]
    for (line_index, sample_index), cell_records in cells.items():
        values[line_index][sample_index] = aggregate_cell_values(cell_records, aggregation)
    return RasterResult(values, rasterized_point_count, len(cells), grid_spec.nodata_value)
```

- [ ] **Step 4: Export grid types**

Update `examples/dem_extract/__init__.py` to import and include `GridSpec`, `RasterResult`, and `rasterize_points` in `__all__`.

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: PASS for grid tests.

- [ ] **Step 6: Commit grid slice**

Run:

```bash
git add examples/dem_extract/__init__.py examples/dem_extract/grid.py tests/unitTest/dem_extract_unit_test.py
git commit -m "feat: rasterize dem radius grid"
```

Expected: commit succeeds.

## Task 6: Cube Writer With Binding Capability Preflight

**Files:**
- Create: `examples/dem_extract/cube_writer.py`
- Modify: `examples/dem_extract/__init__.py`
- Test: `tests/unitTest/dem_extract_unit_test.py`

- [ ] **Step 1: Write failing preflight and writer tests**

Append tests using fakes:

```python
class DemExtractCubeWriterUnitTest(unittest.TestCase):
    def test_preflight_reports_missing_required_bindings(self):
        from dem_extract.cube_writer import preflight_cube_writer_bindings

        class FakeIp:
            class Cube:
                pass

        missing = preflight_cube_writer_bindings(FakeIp)

        self.assertIn("Cube.set_dimensions", missing)
        self.assertIn("LineManager", missing)

    def test_write_radius_cube_sets_dimensions_copies_mapping_and_writes_lines(self):
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dem_extract.cube_writer'`.

- [ ] **Step 3: Implement cube writer module**

Create `examples/dem_extract/cube_writer.py`:

```python
"""Write rasterized radius grids as ISIS Cube DEM products."""

from __future__ import annotations

from pathlib import Path

from .grid import RasterResult


REQUIRED_CUBE_METHODS = ("set_dimensions", "set_pixel_type", "create", "group", "put_group", "write")


def preflight_cube_writer_bindings(ip, template_cube=None, output_cube=None) -> list[str]:
    missing: list[str] = []
    cube_type = getattr(ip, "Cube", None)
    if cube_type is None:
        missing.append("Cube")
    else:
        for method_name in REQUIRED_CUBE_METHODS:
            if not hasattr(cube_type, method_name):
                missing.append(f"Cube.{method_name}")
    if not hasattr(ip, "LineManager"):
        missing.append("LineManager")
    if not hasattr(ip, "PixelType") or not hasattr(ip.PixelType, "Real"):
        missing.append("PixelType.Real")
    if template_cube is not None:
        try:
            template_cube.group("Mapping")
        except Exception as exc:
            missing.append(f"template_cube.group('Mapping'): {exc}")
    if output_cube is not None and hasattr(ip, "LineManager"):
        try:
            line_manager = ip.LineManager(output_cube)
            if not hasattr(line_manager, "__setitem__"):
                missing.append("LineManager.__setitem__")
            else:
                line_manager.set_line(1, 1)
                line_manager[0] = 0.0
        except Exception as exc:
            missing.append(f"LineManager(output_cube): {exc}")
    return missing


def write_radius_cube(ip, template_cube, output_path: str | Path, raster: RasterResult) -> None:
    missing = preflight_cube_writer_bindings(ip, template_cube=template_cube)
    if missing:
        raise RuntimeError("Missing ISIS cube writer bindings: " + ", ".join(missing))
    output_cube = ip.Cube()
    try:
        lines = len(raster.values)
        samples = len(raster.values[0]) if lines else 0
        output_cube.set_dimensions(samples, lines, 1)
        output_cube.set_pixel_type(ip.PixelType.Real)
        output_cube.create(str(output_path))
        missing = preflight_cube_writer_bindings(ip, template_cube=template_cube, output_cube=output_cube)
        if missing:
            raise RuntimeError("Missing ISIS cube writer bindings: " + ", ".join(missing))
        output_cube.put_group(template_cube.group("Mapping"))
        for line_number, row in enumerate(raster.values, start=1):
            line_manager = ip.LineManager(output_cube)
            line_manager.set_line(line_number, 1)
            for sample_index, value in enumerate(row):
                line_manager[sample_index] = value
            output_cube.write(line_manager)
    finally:
        close = getattr(output_cube, "close", None)
        if callable(close):
            close()
```

If the real `LineManager` binding does not expose item assignment during integration, stop this implementation plan and revise the design instead of adding binding code. If `template_cube.group("Mapping")` fails on a projected template cube, stop and revise the design before enabling CLI writes.

- [ ] **Step 4: Export cube writer functions**

Update `examples/dem_extract/__init__.py` to import and include `preflight_cube_writer_bindings` and `write_radius_cube` in `__all__`.

- [ ] **Step 5: Run focused unit test**

Run:

```bash
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: PASS for cube writer tests. If the fake assignment test passes but a real binding smoke check fails, stop and revise the design or use an already exposed buffer mutation API verified by `dir(ip.LineManager(ip.Cube()))`; do not add binding code in this `examples/dem_extract` implementation plan.

- [ ] **Step 6: Run real binding preflight check**

Run:

```bash
conda run -n asp360_new python - <<'PY'
import isis_pybind as ip
required = {
    "Cube.set_dimensions": hasattr(ip.Cube, "set_dimensions"),
    "Cube.set_pixel_type": hasattr(ip.Cube, "set_pixel_type"),
    "Cube.create": hasattr(ip.Cube, "create"),
    "Cube.group": hasattr(ip.Cube, "group"),
    "Cube.put_group": hasattr(ip.Cube, "put_group"),
    "Cube.write": hasattr(ip.Cube, "write"),
    "LineManager": hasattr(ip, "LineManager"),
    "PixelType.Real": hasattr(ip, "PixelType") and hasattr(ip.PixelType, "Real"),
}
print(required)
if not all(required.values()):
    raise SystemExit(1)
PY
```

Expected: prints all eight capabilities as `True`. If a capability is `False`, bind or route around that exact missing operation before enabling CLI writes. After creating a real output cube in the writer tests, also call `preflight_cube_writer_bindings(ip, template_cube=template_cube, output_cube=output_cube)` so Mapping label access, explicit Real pixel type, and line-buffer mutation are verified against live cube instances.

Run this live-instance smoke check before committing the cube writer slice:

```bash
conda run -n asp360_new python - <<'PY'
from pathlib import Path
import shutil
import isis_pybind as ip
from examples.dem_extract.cube_writer import preflight_cube_writer_bindings

scratch_dir = Path("build/dem_extract_writer_preflight_smoke")
if scratch_dir.exists():
    shutil.rmtree(scratch_dir)
scratch_dir.mkdir(parents=True)
try:
    template_cube = ip.Cube()
    template_cube.set_dimensions(1, 1, 1)
    template_cube.set_pixel_type(ip.PixelType.Real)
    template_cube.create(str(scratch_dir / "template.cub"))
    mapping = ip.PvlGroup("Mapping")
    mapping.add_keyword(ip.PvlKeyword("ProjectionName", "Equirectangular"))
    template_cube.put_group(mapping)

    output_cube = ip.Cube()
    output_cube.set_dimensions(1, 1, 1)
    output_cube.set_pixel_type(ip.PixelType.Real)
    output_cube.create(str(scratch_dir / "output.cub"))

    missing = preflight_cube_writer_bindings(ip, template_cube=template_cube, output_cube=output_cube)
    print({"missing": missing})
    if missing:
        raise SystemExit(1)
    template_cube.close()
    output_cube.close()
finally:
    shutil.rmtree(scratch_dir, ignore_errors=True)
PY
```

Expected: prints `{'missing': []}`. This verifies live `template_cube.group("Mapping")`, `LineManager(output_cube)`, and actual line-buffer mutation with `line_manager[0] = 0.0`, not only static class attributes.

- [ ] **Step 7: Commit cube writer slice**

Run:

```bash
git add examples/dem_extract/__init__.py examples/dem_extract/cube_writer.py tests/unitTest/dem_extract_unit_test.py
git commit -m "feat: write dem radius cubes"
```

Expected: commit succeeds.

## Task 7: `from-key` CLI Orchestration

**Files:**
- Create: `examples/dem_extract/isis_stereo_dem.py`
- Modify: `examples/dem_extract/runtime.py`
- Test: `tests/unitTest/dem_extract_unit_test.py`

- [ ] **Step 1: Write failing CLI parser and stdout tests**

Append tests:

```python
class DemExtractCliUnitTest(unittest.TestCase):
    def test_from_key_requires_all_positionals_and_kebab_case_options(self):
        from dem_extract.isis_stereo_dem import build_argument_parser

        parser = build_argument_parser()
        with self.assertRaises(SystemExit):
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dem_extract.isis_stereo_dem'`.

- [ ] **Step 3: Implement CLI parser, orchestration, and stdout payload**

Create `examples/dem_extract/isis_stereo_dem.py`:

```python
"""Command line interface for ISIS Stereo DEM extraction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    EXAMPLES_DIR = Path(__file__).resolve().parents[1]
    PROJECT_ROOT = EXAMPLES_DIR.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    if str(EXAMPLES_DIR) not in sys.path:
        sys.path.insert(0, str(EXAMPLES_DIR))
    from dem_extract.cube_writer import write_radius_cube
    from dem_extract.grid import GridSpec, rasterize_points
    from dem_extract.key_pairs import load_key_point_pairs
    from dem_extract.runtime import build_summary, import_isis_pybind, write_point_cloud_csvish, write_point_cloud_jsonl, write_quality_summary_json, write_summary_json
    from dem_extract.triangulation import FilterOptions, triangulate_pairs
else:
    from .cube_writer import write_radius_cube
    from .grid import GridSpec, rasterize_points
    from .key_pairs import load_key_point_pairs
    from .runtime import build_summary, import_isis_pybind, write_point_cloud_csvish, write_point_cloud_jsonl, write_quality_summary_json, write_summary_json
    from .triangulation import FilterOptions, triangulate_pairs


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract an ISIS Cube DEM from paired .key files using ISIS Stereo.elevation.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    from_key = subparsers.add_parser("from-key", help="Triangulate paired .key files into a radius DEM cube.")
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


def compact_stdout_payload(*, output_dem_cube: str, point_cloud_output: str | None, summary_output: str | None, summary: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "status": "ok",
        "output_dem_cube": output_dem_cube,
        "point_cloud_output": point_cloud_output,
        "summary_output": summary_output,
    }
    for key in (
        "input_point_count", "success_count", "failed_set_image_count", "failed_elevation_count",
        "filtered_error_count", "filtered_sepang_count", "filtered_radius_count",
        "rasterized_point_count", "filled_cell_count",
    ):
        if key in summary:
            payload[key] = summary[key]
    return payload


def run_from_key(args: argparse.Namespace) -> dict[str, Any]:
    ip = import_isis_pybind()
    left_cube = ip.Cube()
    right_cube = ip.Cube()
    template_cube = ip.Cube()
    try:
        left_cube.open(args.left_cube, "r")
        right_cube.open(args.right_cube, "r")
        template_cube.open(args.map_template_cube, "r")
        pairs = load_key_point_pairs(args.left_key, args.right_key, left_cube=left_cube, right_cube=right_cube)
        records, counters = triangulate_pairs(
            pairs,
            left_cube,
            right_cube,
            ip,
            FilterOptions(args.max_error_m, args.min_sepang_deg, args.min_radius_m, args.max_radius_m),
        )
        grid_spec = GridSpec(template_cube.sample_count(), template_cube.line_count(), args.nodata_value)
        raster = rasterize_points(records, template_cube, grid_spec, aggregation=args.aggregation)
        if raster.filled_cell_count == 0:
            raise RuntimeError("No successful triangulated points reached the output DEM grid.")
        write_radius_cube(ip, template_cube, args.output_dem_cube, raster)
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
            aggregation=args.aggregation,
        )
        if args.point_cloud_output:
            if Path(args.point_cloud_output).suffix.lower() == ".jsonl":
                write_point_cloud_jsonl(args.point_cloud_output, records)
            else:
                write_point_cloud_csvish(args.point_cloud_output, records)
        if args.summary_output:
            write_summary_json(args.summary_output, summary)
        if args.quality_prefix:
            write_quality_summary_json(f"{args.quality_prefix}.summary.json", raster)
        return compact_stdout_payload(
            output_dem_cube=args.output_dem_cube,
            point_cloud_output=args.point_cloud_output,
            summary_output=args.summary_output,
            summary=summary,
        )
    finally:
        for cube in (left_cube, right_cube, template_cube):
            close = getattr(cube, "close", None)
            if callable(close):
                close()


def main(argv: list[str] | None = None) -> dict[str, Any]:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    if args.command == "from-key":
        payload = run_from_key(args)
        print(json.dumps(payload, sort_keys=True))
        return payload
    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run focused unit test**

Run:

```bash
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: PASS for CLI parser and compact stdout tests.

- [ ] **Step 5: Run CLI help smoke checks**

Run:

```bash
conda run -n asp360_new python examples/dem_extract/isis_stereo_dem.py --help
conda run -n asp360_new python examples/dem_extract/isis_stereo_dem.py from-key --help
```

Expected: both commands exit 0; second help lists `left_cube right_cube left_key right_key map_template_cube output_dem_cube` and kebab-case flags `--point-cloud-output`, `--summary-output`, `--quality-prefix`, `--max-error-m`, `--min-sepang-deg`, `--min-radius-m`, `--max-radius-m`, `--aggregation`, `--nodata-value`, and `--log-level`.

- [ ] **Step 6: Commit CLI slice**

Run:

```bash
git add examples/dem_extract/isis_stereo_dem.py tests/unitTest/dem_extract_unit_test.py
git commit -m "feat: add dem_extract from-key cli"
```

Expected: commit succeeds.

## Task 8: Focused Validation and Integration Review

**Files:**
- Modify only if validation exposes a directly related defect: `examples/dem_extract/*.py` or `tests/unitTest/dem_extract_unit_test.py`

- [ ] **Step 1: Run accepted focused validation commands**

Run exactly:

```bash
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'stereo_unit_test.py' -v
PYTHONPATH=examples/forward_intersection conda run -n asp360_new python -m unittest discover -s tests/unitTest -p 'forward_intersection_example_test.py' -v
```

Expected: all three commands pass. The first command proves the new package behavior; the second protects existing `Stereo` bindings; the third protects the forward-intersection example that shares camera/Stereo assumptions.

- [ ] **Step 2: Run writer binding preflight from Task 6 again after all imports are wired**

Run:

```bash
conda run -n asp360_new python - <<'PY'
from pathlib import Path
import shutil
import isis_pybind as ip
from examples.dem_extract.cube_writer import preflight_cube_writer_bindings

scratch_dir = Path("build/dem_extract_writer_preflight_smoke")
if scratch_dir.exists():
    shutil.rmtree(scratch_dir)
scratch_dir.mkdir(parents=True)
try:
    template_cube = ip.Cube()
    template_cube.set_dimensions(1, 1, 1)
    template_cube.set_pixel_type(ip.PixelType.Real)
    template_cube.create(str(scratch_dir / "template.cub"))
    mapping = ip.PvlGroup("Mapping")
    mapping.add_keyword(ip.PvlKeyword("ProjectionName", "Equirectangular"))
    template_cube.put_group(mapping)

    output_cube = ip.Cube()
    output_cube.set_dimensions(1, 1, 1)
    output_cube.set_pixel_type(ip.PixelType.Real)
    output_cube.create(str(scratch_dir / "output.cub"))

    missing = preflight_cube_writer_bindings(ip, template_cube=template_cube, output_cube=output_cube)
    print({"missing": missing})
    if missing:
        raise SystemExit(1)
    template_cube.close()
    output_cube.close()
finally:
    shutil.rmtree(scratch_dir, ignore_errors=True)
PY
```

Expected: prints `{'missing': []}`. If the only missing operation is buffer item assignment, add the minimal verified buffer mutation path and a fake plus real preflight assertion before rerunning this step.

- [ ] **Step 3: Review summary and point-cloud field coverage**

Run:

```bash
python - <<'PY'
from examples.dem_extract.runtime import build_summary
summary = build_summary(
    input_left_cube='left.cub', input_right_cube='right.cub', input_left_key='left.key', input_right_key='right.key',
    map_template='template.cub', output_dem_cube='dem.cub', input_point_count=1,
    triangulation_counters={}, rasterized_point_count=0, filled_cell_count=0,
    max_error_m=None, min_sepang_deg=None, aggregation='median')
required = {'input_left_cube','input_right_cube','input_left_key','input_right_key','map_template','output_dem_cube','input_point_count','success_count','failed_set_image_count','failed_elevation_count','filtered_error_count','filtered_sepang_count','filtered_radius_count','rasterized_point_count','filled_cell_count','max_error_m','min_sepang_deg','aggregation','value_type'}
print(sorted(required - set(summary)))
if required - set(summary):
    raise SystemExit(1)
PY
```

Expected: prints `[]`.

- [ ] **Step 4: Commit validation fixes if any were required**

Run only when Step 1, 2, or 3 required code/test changes:

```bash
git add examples/dem_extract tests/unitTest/dem_extract_unit_test.py
git commit -m "fix: stabilize dem_extract validation"
```

Expected: commit succeeds when changes exist; skip this command when validation required no edits.

## Self-Review Checklist for Plan Authors

- [ ] **Spec coverage:** This plan maps every optimized-design requirement to a task: package boundary and runtime bootstrap in Task 1; `.key` loading in Task 2; camera reuse, `Camera.set_image`, `Stereo.elevation`, `Stereo.spherical`, and filters in Task 3; JSONL/CSV-ish point-cloud plus summary counters in Task 4; template projection grid mapping, `median`, `mean`, `min-error`, and nodata in Task 5; `Cube.set_dimensions`, `Cube.create`, `Cube.put_group`, `ip.LineManager`, `Cube.write(...)`, and binding preflight in Task 6; CLI `from-key` positional args and kebab-case flags in Task 7; accepted validation commands in Task 8.
- [ ] **Placeholder scan:** Run the forbidden-placeholder search requested by this task against `docs/superpowers/plans/2026-05-10-dem-extract-from-key.md` and require zero results.
- [ ] **Type consistency:** Confirm `KeyPointPair`, `TriangulatedPoint`, `FilterOptions`, `GridSpec`, `RasterResult`, `load_key_point_pairs`, `triangulate_pairs`, `rasterize_points`, `write_radius_cube`, and `compact_stdout_payload` use the same names and field spellings in tasks, tests, and snippets.
- [ ] **Docs boundary:** Confirm `examples/dem_extract/usage.md` remains an out-of-first-pass optional document and is not included in first-pass file creation commands.
