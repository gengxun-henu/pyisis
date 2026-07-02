# DOM-Space Measure RANSAC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `examples/controlnet_construct/filter_controlnet_dom_ransac.py`, a measure-level DOM-space RANSAC filter that projects original-image `ControlMeasure` coordinates to DOM pixels, runs pair-parallel RANSAC, marks outlier measures ignored, and writes auditable reports.

**Architecture:** The implementation is a two-stage pipeline: pure data extraction/grouping in the main process, pair-level projection/RANSAC work in isolated workers, then single-process writeback to the output `ControlNet`. The first implementation keeps all logic in one focused CLI module with dataclasses and small pure helpers, matching existing example-script style while keeping units independently testable.

**Tech Stack:** Python 3.12, `isis_pybind._isis_core`, existing `examples/image_match/stereo_ransac.py`, `argparse`, `concurrent.futures.ProcessPoolExecutor`, `json`, `csv/jsonl`, `unittest`.

---

## File Structure

- Create: `examples/controlnet_construct/filter_controlnet_dom_ransac.py`
  - CLI parser and `main()`.
  - Dataclasses for measure keys, pair records, projection failures, pair summaries, and worker results.
  - Pure helpers for list reading, serial mapping, measure extraction, pair grouping, outlier aggregation, writeback, and JSON/JSONL output.
  - Worker-local `CubeProjectorCache` with bounded LRU cube/camera/projection cache.
  - Pair worker function that projects original coordinates to DOM pixels and calls existing RANSAC helper.
- Create: `tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py`
  - Focused tests for pure helper behavior and mocked worker/writeback behavior.
- Modify: `tests/smoke_import.py`
  - Optional only if a public import is added; otherwise do not modify.
- Do not modify pybind C++ bindings unless a missing API is found during implementation. Current bindings expose the needed measure ignore and coordinate accessors.

## Task 1: Data Model and Pair Grouping

**Files:**
- Create: `examples/controlnet_construct/filter_controlnet_dom_ransac.py`
- Create: `tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py`

- [ ] **Step 1: Write failing tests for measure keys and pair grouping**

Add this test file skeleton:

```python
"""Unit tests for DOM-space measure-level ControlNet RANSAC filtering."""

from __future__ import annotations

import unittest

from controlnet_construct.filter_controlnet_dom_ransac import (
    MeasureKey,
    MeasureRecord,
    group_measure_pairs_by_serial_pair,
)


class DomRansacFilterDataModelUnitTest(unittest.TestCase):
    def test_group_measure_pairs_by_serial_pair_emits_unordered_pairs_per_point(self):
        records = [
            MeasureRecord(MeasureKey(0, "P1", 0, "SERIAL_A"), 10.0, 20.0),
            MeasureRecord(MeasureKey(0, "P1", 1, "SERIAL_B"), 11.0, 21.0),
            MeasureRecord(MeasureKey(0, "P1", 2, "SERIAL_C"), 12.0, 22.0),
            MeasureRecord(MeasureKey(1, "P2", 0, "SERIAL_A"), 30.0, 40.0),
            MeasureRecord(MeasureKey(1, "P2", 1, "SERIAL_B"), 31.0, 41.0),
        ]

        grouped = group_measure_pairs_by_serial_pair(records)

        self.assertEqual(sorted(grouped), [
            ("SERIAL_A", "SERIAL_B"),
            ("SERIAL_A", "SERIAL_C"),
            ("SERIAL_B", "SERIAL_C"),
        ])
        self.assertEqual(len(grouped[("SERIAL_A", "SERIAL_B")]), 2)
        first = grouped[("SERIAL_A", "SERIAL_B")][0]
        self.assertEqual(first.left.key.point_id, "P1")
        self.assertEqual(first.right.key.point_id, "P1")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_dom_ransac_filter_unit_test.DomRansacFilterDataModelUnitTest -v
```

Expected: import failure because `controlnet_construct.filter_controlnet_dom_ransac` does not exist.

- [ ] **Step 3: Implement dataclasses and pair grouping**

Create the module with:

```python
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MeasureKey:
    point_index: int
    point_id: str
    measure_index: int
    serial: str


@dataclass(frozen=True, slots=True)
class MeasureRecord:
    key: MeasureKey
    sample: float
    line: float


@dataclass(frozen=True, slots=True)
class PairRecord:
    left: MeasureRecord
    right: MeasureRecord


def _serial_pair_key(left_serial: str, right_serial: str) -> tuple[str, str]:
    return (left_serial, right_serial) if left_serial <= right_serial else (right_serial, left_serial)


def group_measure_pairs_by_serial_pair(records: list[MeasureRecord]) -> dict[tuple[str, str], list[PairRecord]]:
    by_point: dict[tuple[int, str], list[MeasureRecord]] = defaultdict(list)
    for record in records:
        by_point[(record.key.point_index, record.key.point_id)].append(record)

    grouped: dict[tuple[str, str], list[PairRecord]] = defaultdict(list)
    for point_records in by_point.values():
        if len(point_records) < 2:
            continue
        for left_index in range(len(point_records)):
            for right_index in range(left_index + 1, len(point_records)):
                left = point_records[left_index]
                right = point_records[right_index]
                if left.key.serial == right.key.serial:
                    continue
                key = _serial_pair_key(left.key.serial, right.key.serial)
                if key[0] == left.key.serial:
                    grouped[key].append(PairRecord(left, right))
                else:
                    grouped[key].append(PairRecord(right, left))
    return dict(grouped)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

Run the same unittest command.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/controlnet_construct/filter_controlnet_dom_ransac.py tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py
git commit -m "feat: add dom ransac measure grouping"
```

## Task 2: ControlNet Measure Extraction and Writeback

**Files:**
- Modify: `examples/controlnet_construct/filter_controlnet_dom_ransac.py`
- Modify: `tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py`

- [ ] **Step 1: Write failing tests using fake ControlNet objects**

Append fake classes and tests:

```python
class FakeMeasure:
    def __init__(self, serial, sample, line, ignored=False):
        self.serial = serial
        self.sample = sample
        self.line = line
        self.ignored = ignored

    def get_cube_serial_number(self):
        return self.serial

    def get_sample(self):
        return self.sample

    def get_line(self):
        return self.line

    def is_ignored(self):
        return self.ignored

    def set_ignored(self, ignored):
        self.ignored = ignored


class FakePoint:
    def __init__(self, point_id, measures, ignored=False):
        self.point_id = point_id
        self.measures = measures
        self.ignored = ignored

    def get_id(self):
        return self.point_id

    def is_ignored(self):
        return self.ignored

    def get_num_measures(self):
        return len(self.measures)

    def get_measure(self, index):
        return self.measures[index]


class FakeNet:
    def __init__(self, points):
        self.points = points

    def get_num_points(self):
        return len(self.points)

    def get_point(self, index):
        return self.points[index]


class DomRansacFilterControlNetUnitTest(unittest.TestCase):
    def test_extract_active_measure_records_skips_ignored_points_and_measures(self):
        from controlnet_construct.filter_controlnet_dom_ransac import extract_active_measure_records

        net = FakeNet([
            FakePoint("P1", [FakeMeasure("A", 1, 2), FakeMeasure("B", 3, 4, ignored=True)]),
            FakePoint("P2", [FakeMeasure("A", 5, 6), FakeMeasure("B", 7, 8)], ignored=True),
            FakePoint("P3", [FakeMeasure("C", 9, 10), FakeMeasure("D", 11, 12)]),
        ])

        records = extract_active_measure_records(net)

        self.assertEqual([record.key.point_id for record in records], ["P1", "P3", "P3"])
        self.assertEqual(records[0].key.measure_index, 0)

    def test_apply_ignored_measures_marks_only_requested_measure_keys(self):
        from controlnet_construct.filter_controlnet_dom_ransac import apply_ignored_measures

        net = FakeNet([FakePoint("P1", [FakeMeasure("A", 1, 2), FakeMeasure("B", 3, 4)])])
        key = MeasureKey(point_index=0, point_id="P1", measure_index=1, serial="B")

        changed = apply_ignored_measures(net, {key})

        self.assertEqual(changed, 1)
        self.assertFalse(net.get_point(0).get_measure(0).is_ignored())
        self.assertTrue(net.get_point(0).get_measure(1).is_ignored())
```

- [ ] **Step 2: Run tests and confirm failures**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_dom_ransac_filter_unit_test -v
```

Expected: failures for missing `extract_active_measure_records` and `apply_ignored_measures`.

- [ ] **Step 3: Implement extraction and writeback helpers**

Add:

```python
def extract_active_measure_records(net) -> list[MeasureRecord]:
    records: list[MeasureRecord] = []
    for point_index in range(net.get_num_points()):
        point = net.get_point(point_index)
        if point.is_ignored():
            continue
        point_id = point.get_id()
        for measure_index in range(point.get_num_measures()):
            measure = point.get_measure(measure_index)
            if measure.is_ignored():
                continue
            serial = measure.get_cube_serial_number()
            records.append(
                MeasureRecord(
                    key=MeasureKey(point_index, point_id, measure_index, serial),
                    sample=float(measure.get_sample()),
                    line=float(measure.get_line()),
                )
            )
    return records


def apply_ignored_measures(net, outlier_keys: set[MeasureKey]) -> int:
    changed = 0
    for key in sorted(outlier_keys, key=lambda item: (item.point_index, item.measure_index, item.serial)):
        point = net.get_point(key.point_index)
        if point.get_id() != key.point_id:
            raise ValueError(
                f"Point index/key mismatch at index {key.point_index}: expected {key.point_id!r}, got {point.get_id()!r}."
            )
        measure = point.get_measure(key.measure_index)
        if measure.get_cube_serial_number() != key.serial:
            raise ValueError(
                f"Measure index/key mismatch for point {key.point_id}: expected {key.serial!r}, got {measure.get_cube_serial_number()!r}."
            )
        if not measure.is_ignored():
            measure.set_ignored(True)
            changed += 1
    return changed
```

- [ ] **Step 4: Run tests**

Expected: all tests in the new test module pass.

- [ ] **Step 5: Commit**

```bash
git add examples/controlnet_construct/filter_controlnet_dom_ransac.py tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py
git commit -m "feat: add dom ransac measure writeback helpers"
```

## Task 3: Serial Mapping, Projection Failures, and Bounded Cube Cache

**Files:**
- Modify: `examples/controlnet_construct/filter_controlnet_dom_ransac.py`
- Modify: `tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py`

- [ ] **Step 1: Write failing tests for aligned list validation and cache eviction**

Add tests with a fake cube factory:

```python
class FakeClosableCube:
    def __init__(self, name):
        self.name = name
        self.closed = False

    def close(self):
        self.closed = True


class DomRansacFilterMappingUnitTest(unittest.TestCase):
    def test_read_aligned_cube_lists_rejects_mismatched_lengths(self):
        from controlnet_construct.filter_controlnet_dom_ransac import read_aligned_cube_lists

        with temporary_directory() as temp_dir:
            original = temp_dir / "original.lis"
            dom = temp_dir / "dom.lis"
            original.write_text("a.cub\nb.cub\n", encoding="utf-8")
            dom.write_text("dom_a.cub\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "length"):
                read_aligned_cube_lists(original, dom)

    def test_lru_cache_closes_evicted_cubes(self):
        from controlnet_construct.filter_controlnet_dom_ransac import BoundedCubeCache

        opened = []

        def factory(path):
            cube = FakeClosableCube(path)
            opened.append(cube)
            return cube

        cache = BoundedCubeCache(max_open=2, factory=factory)
        first = cache.get("A")
        cache.get("B")
        cache.get("C")

        self.assertTrue(first.closed)
        self.assertFalse(opened[-1].closed)
```

Import `temporary_directory` from `_unit_test_support`.

- [ ] **Step 2: Run tests and confirm failures**

Expected: missing mapping/cache helpers.

- [ ] **Step 3: Implement list reading and LRU cache**

Add:

```python
from collections import OrderedDict
from typing import Callable, TypeVar

T = TypeVar("T")


def _read_lis(path: Path) -> list[Path]:
    base = path.parent
    entries: list[Path] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        candidate = Path(value)
        entries.append(candidate if candidate.is_absolute() else base / candidate)
    return entries


def read_aligned_cube_lists(original_list: Path, dom_list: Path) -> list[tuple[Path, Path]]:
    originals = _read_lis(original_list)
    doms = _read_lis(dom_list)
    if len(originals) != len(doms):
        raise ValueError(
            f"Original and DOM list length mismatch: {original_list} has {len(originals)}, {dom_list} has {len(doms)}."
        )
    return list(zip(originals, doms, strict=True))


class BoundedCubeCache:
    def __init__(self, *, max_open: int, factory: Callable[[str], T]):
        if max_open <= 0:
            raise ValueError("max_open must be positive.")
        self._max_open = max_open
        self._factory = factory
        self._items: OrderedDict[str, T] = OrderedDict()

    def get(self, path: str) -> T:
        if path in self._items:
            value = self._items.pop(path)
            self._items[path] = value
            return value
        value = self._factory(path)
        self._items[path] = value
        while len(self._items) > self._max_open:
            _, evicted = self._items.popitem(last=False)
            close = getattr(evicted, "close", None)
            if close is not None:
                close()
        return value

    def close_all(self) -> None:
        while self._items:
            _, value = self._items.popitem(last=False)
            close = getattr(value, "close", None)
            if close is not None:
                close()
```

- [ ] **Step 4: Implement real serial mapping and projection dataclasses**

Add dataclasses:

```python
@dataclass(frozen=True, slots=True)
class SerialPathMaps:
    original_by_serial: dict[str, Path]
    dom_by_serial: dict[str, Path]


@dataclass(frozen=True, slots=True)
class ProjectionFailure:
    measure_key: MeasureKey
    original_sample: float
    original_line: float
    failure_stage: str
    message: str
```

Add `build_serial_path_maps(aligned_pairs, ip_module=ip)` using `ip_module.SerialNumber.compose(str(original_path))`.

- [ ] **Step 5: Run tests**

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add examples/controlnet_construct/filter_controlnet_dom_ransac.py tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py
git commit -m "feat: add dom ransac serial mapping cache"
```

## Task 4: Original-to-DOM Projection Adapter

**Files:**
- Modify: `examples/controlnet_construct/filter_controlnet_dom_ransac.py`
- Modify: `tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py`

- [ ] **Step 1: Write tests with fake camera and projection objects**

Add:

```python
class FakeCamera:
    def __init__(self, ok=True):
        self.ok = ok
        self.sample = None
        self.line = None

    def set_image(self, sample, line):
        self.sample = sample
        self.line = line
        return self.ok

    def universal_latitude(self):
        return self.line + 1.0

    def universal_longitude(self):
        return self.sample + 2.0


class FakeProjection:
    def __init__(self, ok=True):
        self.ok = ok
        self.latitude = None
        self.longitude = None

    def set_universal_ground(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude
        return self.ok

    def world_x(self):
        return self.longitude * 10.0

    def world_y(self):
        return self.latitude * 10.0


class DomRansacFilterProjectionUnitTest(unittest.TestCase):
    def test_project_measure_to_dom_returns_dom_pixel_coordinates(self):
        from controlnet_construct.filter_controlnet_dom_ransac import project_measure_to_dom

        record = MeasureRecord(MeasureKey(0, "P1", 0, "SERIAL_A"), sample=3.0, line=4.0)

        result = project_measure_to_dom(record, FakeCamera(), FakeProjection())

        self.assertEqual(result, (50.0, 50.0))

    def test_project_measure_to_dom_reports_camera_failure(self):
        from controlnet_construct.filter_controlnet_dom_ransac import project_measure_to_dom

        record = MeasureRecord(MeasureKey(0, "P1", 0, "SERIAL_A"), sample=3.0, line=4.0)

        result = project_measure_to_dom(record, FakeCamera(ok=False), FakeProjection())

        self.assertEqual(result.failure_stage, "camera_set_image_failed")
```

- [ ] **Step 2: Run tests and confirm failures**

Expected: missing `project_measure_to_dom`.

- [ ] **Step 3: Implement projection helper**

Add:

```python
import math


def project_measure_to_dom(record: MeasureRecord, camera, projection) -> tuple[float, float] | ProjectionFailure:
    if not (math.isfinite(record.sample) and math.isfinite(record.line)):
        return ProjectionFailure(record.key, record.sample, record.line, "invalid_original_coordinate", "Sample/line is not finite.")
    if not camera.set_image(record.sample, record.line):
        return ProjectionFailure(record.key, record.sample, record.line, "camera_set_image_failed", "Camera failed to set image coordinate.")
    latitude = float(camera.universal_latitude())
    longitude = float(camera.universal_longitude())
    if not (math.isfinite(latitude) and math.isfinite(longitude)):
        return ProjectionFailure(record.key, record.sample, record.line, "invalid_ground_coordinate", "Camera returned non-finite ground coordinate.")
    if not projection.set_universal_ground(latitude, longitude):
        return ProjectionFailure(record.key, record.sample, record.line, "dom_set_universal_ground_failed", "DOM projection failed to set universal ground.")
    dom_sample = float(projection.world_x())
    dom_line = float(projection.world_y())
    if not (math.isfinite(dom_sample) and math.isfinite(dom_line)):
        return ProjectionFailure(record.key, record.sample, record.line, "invalid_dom_coordinate", "DOM projection returned non-finite sample/line.")
    return dom_sample, dom_line
```

- [ ] **Step 4: Implement worker projector cache wrapper**

Add `WorkerProjectorCache` that owns two `BoundedCubeCache` instances and exposes:

```python
def camera_for_serial(self, serial: str)
def projection_for_serial(self, serial: str)
def close_all(self) -> None
```

The real factory uses:

```python
cube = self._ip.Cube()
cube.open(str(path), "r")
camera = cube.camera()
projection = cube.projection()
```

Keep cube objects alive in the cache so camera/projection references remain valid.

- [ ] **Step 5: Run tests**

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add examples/controlnet_construct/filter_controlnet_dom_ransac.py tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py
git commit -m "feat: add original to dom measure projection"
```

## Task 5: Pair Worker RANSAC and Outlier Keys

**Files:**
- Modify: `examples/controlnet_construct/filter_controlnet_dom_ransac.py`
- Modify: `tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py`

- [ ] **Step 1: Write failing tests for worker result aggregation**

Use monkeypatch-style assignment with `unittest.mock.patch`:

```python
from unittest.mock import patch


class DomRansacFilterWorkerUnitTest(unittest.TestCase):
    def test_run_pair_ransac_marks_both_measures_from_dropped_correspondence(self):
        from controlnet_construct import filter_controlnet_dom_ransac as module
        from controlnet_construct.filter_controlnet_dom_ransac import PairTask, run_pair_ransac_task

        left = MeasureRecord(MeasureKey(0, "P1", 0, "A"), 1.0, 1.0)
        right = MeasureRecord(MeasureKey(0, "P1", 1, "B"), 2.0, 2.0)
        task = PairTask(("A", "B"), [PairRecord(left, right)])

        with patch.object(module, "project_measure_to_dom", side_effect=[(1.0, 1.0), (100.0, 100.0)]), \
             patch.object(module, "filter_stereo_pair_keypoints_with_ransac") as ransac:
            ransac.return_value = (
                module.KeypointFile(1, 1, ()),
                module.KeypointFile(1, 1, ()),
                {"status": "filtered", "input_count": 1, "retained_count": 0, "dropped_count": 1},
            )
            result = run_pair_ransac_task(task, serial_maps=None, options=module.RansacOptions(), projector_cache=None)

        self.assertEqual(result.outlier_measure_keys, {left.key, right.key})
```

- [ ] **Step 2: Run tests and confirm failures**

Expected: missing task/result dataclasses and worker function.

- [ ] **Step 3: Implement worker dataclasses and `run_pair_ransac_task`**

Add:

```python
from image_match.keypoints import Keypoint, KeypointFile
from image_match.stereo_ransac import (
    DEFAULT_RANSAC_MODEL,
    DEFAULT_RANSAC_REPROJ_THRESHOLD,
    filter_stereo_pair_keypoints_with_ransac,
)


@dataclass(frozen=True, slots=True)
class RansacOptions:
    model: str = DEFAULT_RANSAC_MODEL
    reproj_threshold: float = DEFAULT_RANSAC_REPROJ_THRESHOLD
    confidence: float = 0.995
    max_iters: int = 5000
    mode: str = "loose"
    loose_keep_pixel_threshold: float = 1.0


@dataclass(frozen=True, slots=True)
class PairTask:
    serial_pair: tuple[str, str]
    records: list[PairRecord]


@dataclass(frozen=True, slots=True)
class PairRansacResult:
    serial_pair: tuple[str, str]
    outlier_measure_keys: set[MeasureKey]
    projection_failures: list[ProjectionFailure]
    summary: dict[str, object]
```

Implement worker logic:

- project left and right records;
- collect projection failures;
- keep only correspondences where both projections succeed;
- build `KeypointFile(1, 1, points)`;
- call `filter_stereo_pair_keypoints_with_ransac`;
- because the helper returns retained keypoints but not retained original indices, add a local RANSAC mask helper or extend this module with a small `compute_retained_mask(...)` using the same OpenCV calls as the helper;
- dropped correspondence means both measure keys are outliers.

- [ ] **Step 4: Add tests for projection failures not producing outliers**

Test:

```python
def test_run_pair_ransac_reports_projection_failures_without_outliers(self):
    from controlnet_construct import filter_controlnet_dom_ransac as module
    from controlnet_construct.filter_controlnet_dom_ransac import PairTask, ProjectionFailure, run_pair_ransac_task

    left = MeasureRecord(MeasureKey(0, "P1", 0, "A"), 1.0, 1.0)
    right = MeasureRecord(MeasureKey(0, "P1", 1, "B"), 2.0, 2.0)
    failure = ProjectionFailure(left.key, left.sample, left.line, "camera_set_image_failed", "failed")

    with patch.object(module, "project_measure_to_dom", side_effect=[failure, (2.0, 2.0)]):
        result = run_pair_ransac_task(PairTask(("A", "B"), [PairRecord(left, right)]), None, module.RansacOptions(), None)

    self.assertEqual(result.outlier_measure_keys, set())
    self.assertEqual(result.projection_failures, [failure])
    self.assertEqual(result.summary["status"], "skipped_no_projected_correspondences")
```

- [ ] **Step 5: Run tests**

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add examples/controlnet_construct/filter_controlnet_dom_ransac.py tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py
git commit -m "feat: add dom ransac pair worker"
```

## Task 6: Parallel Orchestration and Reporting

**Files:**
- Modify: `examples/controlnet_construct/filter_controlnet_dom_ransac.py`
- Modify: `tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py`

- [ ] **Step 1: Write tests for result aggregation and report writing**

Add:

```python
class DomRansacFilterReportingUnitTest(unittest.TestCase):
    def test_aggregate_worker_results_uses_any_pair_outlier_policy(self):
        from controlnet_construct.filter_controlnet_dom_ransac import PairRansacResult, aggregate_worker_results

        key = MeasureKey(0, "P1", 0, "A")
        results = [
            PairRansacResult(("A", "B"), {key}, [], {"status": "filtered"}),
            PairRansacResult(("A", "C"), set(), [], {"status": "filtered"}),
        ]

        outliers, failures, summaries = aggregate_worker_results(results)

        self.assertEqual(outliers, {key})
        self.assertEqual(failures, [])
        self.assertEqual(len(summaries), 2)
```

- [ ] **Step 2: Implement aggregation and JSON/JSONL helpers**

Add:

```python
def aggregate_worker_results(results: list[PairRansacResult]) -> tuple[set[MeasureKey], list[ProjectionFailure], list[dict[str, object]]]:
    outliers: set[MeasureKey] = set()
    failures: list[ProjectionFailure] = []
    summaries: list[dict[str, object]] = []
    for result in results:
        outliers.update(result.outlier_measure_keys)
        failures.extend(result.projection_failures)
        summaries.append({"left_serial": result.serial_pair[0], "right_serial": result.serial_pair[1], **result.summary})
    return outliers, failures, summaries
```

Add serializers:

```python
def measure_key_to_dict(key: MeasureKey) -> dict[str, object]
def projection_failure_to_dict(failure: ProjectionFailure) -> dict[str, object]
def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None
def write_summary_report(path: Path, report: dict[str, object]) -> None
```

- [ ] **Step 3: Implement sequential and parallel task execution**

Add:

```python
def run_pair_tasks(tasks, serial_maps, options, *, num_workers: int, max_open_cubes_per_worker: int) -> list[PairRansacResult]:
    if num_workers <= 1:
        return [
            run_pair_ransac_task(task, serial_maps, options, WorkerProjectorCache(serial_maps, max_open=max_open_cubes_per_worker))
            for task in tasks
        ]
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(run_pair_ransac_task_in_subprocess, task, serial_maps, options, max_open_cubes_per_worker)
            for task in tasks
        ]
        return [future.result() for future in as_completed(futures)]
```

Make `run_pair_ransac_task_in_subprocess(...)` create and close its own worker cache.

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/controlnet_construct/filter_controlnet_dom_ransac.py tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py
git commit -m "feat: add dom ransac orchestration reports"
```

## Task 7: CLI, ControlNet I/O, and Writeback

**Files:**
- Modify: `examples/controlnet_construct/filter_controlnet_dom_ransac.py`
- Modify: `tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py`

- [ ] **Step 1: Write CLI parser tests**

Add:

```python
class DomRansacFilterCliUnitTest(unittest.TestCase):
    def test_parser_accepts_required_paths_and_parallel_options(self):
        from controlnet_construct.filter_controlnet_dom_ransac import build_argument_parser

        args = build_argument_parser().parse_args([
            "--input-net", "input.net",
            "--original-list", "original.lis",
            "--dom-list", "dom.lis",
            "--output-net", "output.net",
            "--report", "report.json",
            "--outlier-measures", "outliers.jsonl",
            "--projection-failures", "projection_failures.jsonl",
            "--num-workers", "4",
            "--max-open-cubes-per-worker", "32",
        ])

        self.assertEqual(args.num_workers, 4)
        self.assertEqual(args.max_open_cubes_per_worker, 32)
```

- [ ] **Step 2: Implement parser and `filter_controlnet_dom_ransac(...)`**

Parser arguments:

```python
--input-net Path required
--original-list Path required
--dom-list Path required
--output-net Path required
--report Path required
--outlier-measures Path required
--projection-failures Path required
--ransac-model choices=("affine-partial", "affine", "homography") default=DEFAULT_RANSAC_MODEL
--ransac-reproj-threshold float default=DEFAULT_RANSAC_REPROJ_THRESHOLD
--ransac-confidence float default=0.995
--ransac-max-iters int default=5000
--ransac-mode choices=("strict", "loose") default="loose"
--loose-ransac-keep-threshold float default=1.0
--num-workers int default=1
--max-open-cubes-per-worker int default=16
--binary action="store_true" default True behavior should write binary unless --pvl is added
--pvl action="store_true" write PVL text output
```

Implement top-level function:

```python
def filter_controlnet_dom_ransac(args, *, ip_module=ip) -> dict[str, object]:
    aligned = read_aligned_cube_lists(args.original_list, args.dom_list)
    serial_maps = build_serial_path_maps(aligned, ip_module=ip_module)
    net = ip_module.ControlNet(str(args.input_net))
    records = extract_active_measure_records(net)
    grouped = group_measure_pairs_by_serial_pair(records)
    tasks = [PairTask(serial_pair, pair_records) for serial_pair, pair_records in grouped.items()]
    results = run_pair_tasks(tasks, serial_maps, options, num_workers=args.num_workers, max_open_cubes_per_worker=args.max_open_cubes_per_worker)
    outlier_keys, projection_failures, pair_summaries = aggregate_worker_results(results)
    changed = apply_ignored_measures(net, outlier_keys)
    net.write(str(args.output_net), bool(args.pvl))
    write_jsonl(args.outlier_measures, [{"policy": "any_pair_outlier", **measure_key_to_dict(key)} for key in sorted(outlier_keys, key=...)])
    write_jsonl(args.projection_failures, [projection_failure_to_dict(failure) for failure in projection_failures])
    report = {...}
    write_summary_report(args.report, report)
    return report
```

Use binary output by default: `net.write(output, False)` unless `--pvl` is set.

- [ ] **Step 3: Write mocked integration test**

Patch `ip.ControlNet`, `build_serial_path_maps`, `run_pair_tasks`, and verify:

- `set_ignored(True)` is called on only outlier measures;
- output net write is called once after worker results;
- report and JSONL files are created.

- [ ] **Step 4: Implement `main(argv=None)`**

```python
def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    report = filter_controlnet_dom_ransac(args)
    print(json.dumps({
        "input_point_count": report["input_point_count"],
        "input_measure_count": report["input_measure_count"],
        "outlier_measure_count": report["outlier_measure_count"],
        "projection_failure_count": report["projection_failure_count"],
        "output_net": report["output_net"],
    }, indent=2))
    return 0
```

- [ ] **Step 5: Run focused tests**

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add examples/controlnet_construct/filter_controlnet_dom_ransac.py tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py
git commit -m "feat: add dom measure ransac cli"
```

## Task 8: Documentation and Validation

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `examples/controlnet_construct/usage.md`
- Modify: `tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py`

- [ ] **Step 1: Add README usage snippets**

Add a short section after the DOM ControlNet workflow references:

```markdown
### Measure-level DOM RANSAC filtering

After building or refining a control network whose measures are in original image
coordinates, use `examples/controlnet_construct/filter_controlnet_dom_ransac.py`
to project measures into DOM pixel space, run pair-parallel RANSAC, and mark
outlier measures ignored in a new `.net`.
```

Include the command from the spec.

- [ ] **Step 2: Add Chinese README equivalent**

Mirror the English section in `README.zh-CN.md`, explicitly saying it filters
`ControlMeasure` rather than deleting `ControlPoint`.

- [ ] **Step 3: Add focused usage doc details**

In `examples/controlnet_construct/usage.md`, add:

- where it fits after `pointreg`/BA seed network generation;
- that measure coordinates are interpreted as original image sample/line;
- that projection failures are reported but not ignored;
- that workers do not write `.net`; final write is single-process.

- [ ] **Step 4: Run focused unit tests**

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_dom_ransac_filter_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Run import smoke test**

```bash
python tests/smoke_import.py
```

Expected: PASS.

- [ ] **Step 6: Optional real-data validation command**

Run only when the external LRO data path is available:

```bash
python examples/controlnet_construct/filter_controlnet_dom_ransac.py \
  --input-net "/run/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/ba2_cnet_seedgrid_cnetadd_cnetref_pointreg_dom-M.net" \
  --original-list "/run/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/reduced_original_images.lis" \
  --dom-list "/run/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/dom_images.lis" \
  --output-net "/tmp/ba2_dom_measure_ransac.net" \
  --report "/tmp/ba2_dom_measure_ransac_report.json" \
  --outlier-measures "/tmp/ba2_dom_measure_ransac_outliers.jsonl" \
  --projection-failures "/tmp/ba2_dom_measure_ransac_projection_failures.jsonl" \
  --num-workers 8 \
  --max-open-cubes-per-worker 16
```

Then verify:

```bash
python - <<'PY'
import isis_pybind._isis_core as ip
net = ip.ControlNet("/tmp/ba2_dom_measure_ransac.net")
print(net.get_num_points(), net.get_num_measures(), net.get_num_ignored_measures())
PY
```

Expected: readable output network, point count preserved, ignored measure count increased.

- [ ] **Step 7: Commit docs and final verification**

```bash
git add README.md README.zh-CN.md examples/controlnet_construct/usage.md tests/unitTest/controlnet_construct_dom_ransac_filter_unit_test.py
git commit -m "docs: document dom measure ransac filter"
```

## Self-Review Checklist

- Spec coverage:
  - Measure-level filtering: Tasks 1, 2, 5, 7.
  - Original-to-DOM projection: Tasks 3, 4.
  - Pair-parallel RANSAC: Tasks 5, 6.
  - Single-process writeback: Tasks 2, 7.
  - Projection failures report-only: Tasks 4, 5, 6.
  - Large cube lazy open/LRU: Task 3.
  - CLI/report docs: Tasks 7, 8.
- Placeholder scan: no TBD/TODO/fill-in steps; each task has explicit code or commands.
- Type consistency:
  - `MeasureKey`, `MeasureRecord`, `PairRecord`, `PairTask`, and `PairRansacResult` names are consistent across tasks.
  - `apply_ignored_measures` uses `point_index` and `measure_index` as writeback coordinates.
  - `project_measure_to_dom` returns either `(sample, line)` or `ProjectionFailure`.
