# Pre-RANSAC Ground-Distance Prefilter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a default-on, pre-RANSAC stereo ground-distance outlier filter for ORI and DOM matching/ControlNet paths, with `--pre-ransac-max-ground-distance-km 0` disabling it.

**Architecture:** Add a focused `ground_distance_prefilter.py` module that filters index-aligned left/right `.key` pairs through injected ground lookup functions, then wrap it with ORI and DOM ISIS lookup helpers. Matching paths run the filter first and write metadata; ControlNet paths skip fallback filtering when upstream metadata already proves it ran.

**Tech Stack:** Python 3.12, PyISIS/ISIS `UniversalGroundMap`, existing `.key` helpers, `unittest`, shell wrappers, ControlNet parameter catalog.

---

## File Structure

- Create `examples/controlnet_construct/ground_distance_prefilter.py`
  - Pure spherical-distance helpers.
  - Keypoint/key-file filtering with injected lookup functions.
  - ISIS-backed ORI and DOM key-file wrappers.
  - Metadata skip helper for ControlNet fallback.
- Modify `examples/controlnet_construct/__init__.py`
  - Export the public prefilter helpers.
- Modify `examples/controlnet_construct/controlnet_stereopair.py`
  - Add CLI arguments.
  - Add from-dom and from-ori-match fallback/check wiring before RANSAC.
  - Include summaries in reports/results.
- Modify `examples/image_match/image_match.py`
  - Add matching-stage options.
  - Apply prefilter to ORI and DOM key outputs before visualization RANSAC.
  - Persist `pre_ransac_ground_distance_filter` in metadata.
- Modify shell wrappers:
  - `examples/controlnet_construct/run_image_match_batch_example.sh`
  - `examples/controlnet_construct/run_pipeline_example.sh`
  - `examples/controlnet_construct/run_ori_match_pipeline_example.sh`
- Modify `examples/controlnet_construct/parameter_catalog.py`
  - Register the new threshold option for matching and ControlNet entrypoints.
- Tests:
  - `tests/unitTest/controlnet_construct_ground_distance_prefilter_unit_test.py`
  - Existing focused tests in `tests/unitTest/controlnet_construct_matching_unit_test.py`
  - Existing focused tests in `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

## Task 1: Pure Ground-Distance Filter Module

**Files:**
- Create: `examples/controlnet_construct/ground_distance_prefilter.py`
- Test: `tests/unitTest/controlnet_construct_ground_distance_prefilter_unit_test.py`

- [ ] **Step 1: Write failing pure-function tests**

Create `tests/unitTest/controlnet_construct_ground_distance_prefilter_unit_test.py`:

```python
from __future__ import annotations

import math
from pathlib import Path
import sys
import tempfile
import unittest

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from image_match.keypoints import Keypoint, KeypointFile, read_key_file
from controlnet_construct.ground_distance_prefilter import (
    LUNAR_MEAN_RADIUS_KM,
    ground_distance_km,
    filter_stereo_pair_keypoints_by_ground_distance,
    filter_stereo_pair_key_files_by_ground_distance,
)


def _key_file(points):
    return KeypointFile(1000, 1000, tuple(Keypoint(float(x), float(y)) for x, y in points))


class GroundDistancePrefilterUnitTest(unittest.TestCase):
    def test_ground_distance_handles_longitude_wrap(self):
        distance = ground_distance_km(0.0, 359.99, 0.0, 0.01, radius_km=LUNAR_MEAN_RADIUS_KM)
        self.assertLess(distance, 1.0)

    def test_filter_drops_pair_over_threshold_and_keeps_alignment(self):
        left = _key_file([(1, 1), (2, 2), (3, 3)])
        right = _key_file([(10, 10), (20, 20), (30, 30)])
        left_lookup = {
            (1.0, 1.0): (0.0, 0.0),
            (2.0, 2.0): (0.0, 0.0),
            (3.0, 3.0): (0.0, 0.0),
        }
        right_lookup = {
            (10.0, 10.0): (0.0, 0.0),
            (20.0, 20.0): (0.0, 0.01),
            (30.0, 30.0): (0.0, 0.0),
        }
        filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_by_ground_distance(
            left,
            right,
            left_ground_lookup=lambda sample, line: left_lookup[(sample, line)],
            right_ground_lookup=lambda sample, line: right_lookup[(sample, line)],
            threshold_km=0.1,
        )
        self.assertEqual([(p.sample, p.line) for p in filtered_left.points], [(1.0, 1.0), (3.0, 3.0)])
        self.assertEqual([(p.sample, p.line) for p in filtered_right.points], [(10.0, 10.0), (30.0, 30.0)])
        self.assertEqual(summary["input_count"], 3)
        self.assertEqual(summary["retained_count"], 2)
        self.assertEqual(summary["dropped_ground_distance_count"], 1)

    def test_lookup_failure_drops_pair_by_default(self):
        left = _key_file([(1, 1), (2, 2)])
        right = _key_file([(10, 10), (20, 20)])
        filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_by_ground_distance(
            left,
            right,
            left_ground_lookup=lambda sample, line: None if sample == 2.0 else (0.0, 0.0),
            right_ground_lookup=lambda sample, line: (0.0, 0.0),
            threshold_km=1.0,
        )
        self.assertEqual(len(filtered_left.points), 1)
        self.assertEqual(len(filtered_right.points), 1)
        self.assertEqual(summary["ground_lookup_failure_count"], 1)

    def test_threshold_zero_disables_filter(self):
        left = _key_file([(1, 1)])
        right = _key_file([(10, 10)])
        filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_by_ground_distance(
            left,
            right,
            left_ground_lookup=lambda sample, line: (_ for _ in ()).throw(AssertionError("lookup not expected")),
            right_ground_lookup=lambda sample, line: (_ for _ in ()).throw(AssertionError("lookup not expected")),
            threshold_km=0.0,
        )
        self.assertEqual(filtered_left.points, left.points)
        self.assertEqual(filtered_right.points, right.points)
        self.assertFalse(summary["applied"])
        self.assertEqual(summary["status"], "disabled")

    def test_key_file_wrapper_writes_filtered_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            left_input = tmp_path / "left.key"
            right_input = tmp_path / "right.key"
            left_output = tmp_path / "left_filtered.key"
            right_output = tmp_path / "right_filtered.key"
            left_input.write_text("100 100\n1 1\n2 2\n", encoding="utf-8")
            right_input.write_text("100 100\n10 10\n20 20\n", encoding="utf-8")
            summary = filter_stereo_pair_key_files_by_ground_distance(
                left_input,
                right_input,
                left_output,
                right_output,
                left_ground_lookup=lambda sample, line: (0.0, 0.0),
                right_ground_lookup=lambda sample, line: (0.0, 0.0 if sample == 10.0 else 0.01),
                threshold_km=0.1,
            )
            self.assertEqual(summary["retained_count"], 1)
            self.assertEqual(len(read_key_file(left_output).points), 1)
            self.assertEqual(len(read_key_file(right_output).points), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new test to verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_ground_distance_prefilter_unit_test -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'controlnet_construct.ground_distance_prefilter'`.

- [ ] **Step 3: Implement the pure module**

Create `examples/controlnet_construct/ground_distance_prefilter.py`:

```python
"""Pre-RANSAC stereo ground-distance filtering for `.key` correspondences."""

from __future__ import annotations

from pathlib import Path
import math
from statistics import mean, median
from typing import Callable

try:
    from image_match.keypoints import Keypoint, KeypointFile, read_key_file, write_key_file
except ImportError:
    from .keypoints import Keypoint, KeypointFile, read_key_file, write_key_file

LUNAR_MEAN_RADIUS_KM = 1737.4
PREFILTER_METADATA_KEY = "pre_ransac_ground_distance_filter"
GroundLookup = Callable[[float, float], tuple[float, float] | None]


def _validate_threshold(threshold_km: float) -> float:
    threshold = float(threshold_km)
    if not math.isfinite(threshold) or threshold < 0.0:
        raise ValueError("pre-RANSAC ground-distance threshold must be finite and non-negative.")
    return threshold


def _normalize_longitude_delta_degrees(delta: float) -> float:
    return (float(delta) + 180.0) % 360.0 - 180.0


def ground_distance_km(
    left_latitude_degrees: float,
    left_longitude_degrees: float,
    right_latitude_degrees: float,
    right_longitude_degrees: float,
    *,
    radius_km: float = LUNAR_MEAN_RADIUS_KM,
) -> float:
    values = (
        left_latitude_degrees,
        left_longitude_degrees,
        right_latitude_degrees,
        right_longitude_degrees,
        radius_km,
    )
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("Ground coordinates and radius must be finite.")
    left_lat = math.radians(float(left_latitude_degrees))
    right_lat = math.radians(float(right_latitude_degrees))
    delta_lat = math.radians(float(right_latitude_degrees) - float(left_latitude_degrees))
    delta_lon = math.radians(
        _normalize_longitude_delta_degrees(float(right_longitude_degrees) - float(left_longitude_degrees))
    )
    sin_lat = math.sin(delta_lat / 2.0)
    sin_lon = math.sin(delta_lon / 2.0)
    a = sin_lat * sin_lat + math.cos(left_lat) * math.cos(right_lat) * sin_lon * sin_lon
    return float(radius_km) * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def _distance_summary(distances: list[float]) -> dict[str, float | int | None]:
    if not distances:
        return {"count": 0, "min": None, "mean": None, "median": None, "p90": None, "max": None}
    ordered = sorted(distances)
    p90_index = min(len(ordered) - 1, math.ceil(0.9 * len(ordered)) - 1)
    return {
        "count": len(ordered),
        "min": ordered[0],
        "mean": mean(ordered),
        "median": median(ordered),
        "p90": ordered[p90_index],
        "max": ordered[-1],
    }


def _disabled_summary(
    left_key_file: KeypointFile,
    right_key_file: KeypointFile,
    *,
    threshold_km: float,
    lookup_failure_policy: str,
    lunar_radius_km: float,
) -> dict[str, object]:
    return {
        "applied": False,
        "already_prefiltered": False,
        "status": "disabled",
        "threshold_km": float(threshold_km),
        "lookup_failure_policy": lookup_failure_policy,
        "lunar_radius_km": float(lunar_radius_km),
        "input_count": len(left_key_file.points),
        "retained_count": len(left_key_file.points),
        "dropped_count": 0,
        "dropped_ground_distance_count": 0,
        "ground_lookup_failure_count": 0,
        "distance_summary_km": _distance_summary([]),
        "max_ground_distance_km": None,
    }


def filter_stereo_pair_keypoints_by_ground_distance(
    left_key_file: KeypointFile,
    right_key_file: KeypointFile,
    *,
    left_ground_lookup: GroundLookup,
    right_ground_lookup: GroundLookup,
    threshold_km: float,
    lookup_failure_policy: str = "drop",
    lunar_radius_km: float = LUNAR_MEAN_RADIUS_KM,
    space: str | None = None,
    geometry_source: str | None = None,
) -> tuple[KeypointFile, KeypointFile, dict[str, object]]:
    if len(left_key_file.points) != len(right_key_file.points):
        raise ValueError("Left and right keypoint files must contain the same number of points.")
    if lookup_failure_policy not in {"drop", "keep"}:
        raise ValueError("lookup_failure_policy must be 'drop' or 'keep'.")
    threshold = _validate_threshold(threshold_km)
    if threshold == 0.0:
        return (
            left_key_file,
            right_key_file,
            _disabled_summary(
                left_key_file,
                right_key_file,
                threshold_km=threshold,
                lookup_failure_policy=lookup_failure_policy,
                lunar_radius_km=lunar_radius_km,
            ),
        )

    retained_left: list[Keypoint] = []
    retained_right: list[Keypoint] = []
    distances: list[float] = []
    dropped_distance = 0
    lookup_failures = 0

    for left_point, right_point in zip(left_key_file.points, right_key_file.points, strict=True):
        left_ground = left_ground_lookup(left_point.sample, left_point.line)
        right_ground = right_ground_lookup(right_point.sample, right_point.line)
        if left_ground is None or right_ground is None:
            lookup_failures += 1
            if lookup_failure_policy == "keep":
                retained_left.append(left_point)
                retained_right.append(right_point)
            continue
        distance = ground_distance_km(
            left_ground[0],
            left_ground[1],
            right_ground[0],
            right_ground[1],
            radius_km=lunar_radius_km,
        )
        distances.append(distance)
        if distance > threshold:
            dropped_distance += 1
            continue
        retained_left.append(left_point)
        retained_right.append(right_point)

    retained_count = len(retained_left)
    input_count = len(left_key_file.points)
    summary = {
        "applied": True,
        "already_prefiltered": False,
        "status": "filtered",
        "threshold_km": threshold,
        "lookup_failure_policy": lookup_failure_policy,
        "lunar_radius_km": float(lunar_radius_km),
        "input_count": input_count,
        "retained_count": retained_count,
        "dropped_count": input_count - retained_count,
        "dropped_ground_distance_count": dropped_distance,
        "ground_lookup_failure_count": lookup_failures,
        "distance_summary_km": _distance_summary(distances),
        "max_ground_distance_km": max(distances) if distances else None,
        **({"space": space} if space else {}),
        **({"geometry_source": geometry_source} if geometry_source else {}),
    }
    return (
        KeypointFile(left_key_file.image_width, left_key_file.image_height, tuple(retained_left)),
        KeypointFile(right_key_file.image_width, right_key_file.image_height, tuple(retained_right)),
        summary,
    )


def filter_stereo_pair_key_files_by_ground_distance(
    left_input: str | Path,
    right_input: str | Path,
    left_output: str | Path,
    right_output: str | Path,
    *,
    left_ground_lookup: GroundLookup,
    right_ground_lookup: GroundLookup,
    threshold_km: float,
    lookup_failure_policy: str = "drop",
    lunar_radius_km: float = LUNAR_MEAN_RADIUS_KM,
    space: str | None = None,
    geometry_source: str | None = None,
) -> dict[str, object]:
    left_key_file = read_key_file(left_input)
    right_key_file = read_key_file(right_input)
    filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_by_ground_distance(
        left_key_file,
        right_key_file,
        left_ground_lookup=left_ground_lookup,
        right_ground_lookup=right_ground_lookup,
        threshold_km=threshold_km,
        lookup_failure_policy=lookup_failure_policy,
        lunar_radius_km=lunar_radius_km,
        space=space,
        geometry_source=geometry_source,
    )
    write_key_file(left_output, filtered_left)
    write_key_file(right_output, filtered_right)
    return {
        **summary,
        "left_input": str(left_input),
        "right_input": str(right_input),
        "left_output": str(left_output),
        "right_output": str(right_output),
    }
```

- [ ] **Step 4: Run the pure module tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_ground_distance_prefilter_unit_test -v
```

Expected: PASS for the new tests.

- [ ] **Step 5: Commit**

```bash
git add examples/controlnet_construct/ground_distance_prefilter.py tests/unitTest/controlnet_construct_ground_distance_prefilter_unit_test.py
git commit -m "feat: add ground distance keypoint prefilter"
```

## Task 2: ISIS-Backed ORI and DOM Ground Lookup Wrappers

**Files:**
- Modify: `examples/controlnet_construct/ground_distance_prefilter.py`
- Modify: `examples/controlnet_construct/__init__.py`
- Test: `tests/unitTest/controlnet_construct_ground_distance_prefilter_unit_test.py`

- [ ] **Step 1: Add failing wrapper tests with fake ISIS objects**

Append to `tests/unitTest/controlnet_construct_ground_distance_prefilter_unit_test.py`:

```python
from unittest import mock


class FakeCube:
    def __init__(self):
        self.opened_path = None
        self.closed = False

    def open(self, path, mode):
        self.opened_path = path

    def band_count(self):
        return 1

    def is_open(self):
        return self.opened_path is not None and not self.closed

    def close(self):
        self.closed = True


class FakeGroundMap:
    def __init__(self, cube, priority=None):
        self.band = None
        self.sample = None
        self.line = None

    def set_band(self, band):
        self.band = band

    def set_image(self, sample, line):
        self.sample = sample
        self.line = line
        return sample != 99.0

    def universal_latitude(self):
        return 0.0

    def universal_longitude(self):
        return 0.0 if self.sample < 50.0 else 0.01


class GroundDistanceGeometryWrapperUnitTest(unittest.TestCase):
    def test_dom_wrapper_uses_projection_first_and_writes_summary(self):
        from controlnet_construct import ground_distance_prefilter as module

        fake_ip = type(
            "FakeIp",
            (),
            {
                "Cube": FakeCube,
                "UniversalGroundMap": type(
                    "UGM",
                    (FakeGroundMap,),
                    {"CameraPriority": type("Priority", (), {"ProjectionFirst": "projection", "CameraFirst": "camera"})},
                ),
            },
        )
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(module, "bootstrap_runtime_environment", lambda: None), mock.patch.dict(sys.modules, {"isis_pybind": fake_ip}):
            tmp_path = Path(tmp)
            left_input = tmp_path / "left.key"
            right_input = tmp_path / "right.key"
            left_output = tmp_path / "left_filtered.key"
            right_output = tmp_path / "right_filtered.key"
            left_input.write_text("100 100\n1 1\n", encoding="utf-8")
            right_input.write_text("100 100\n60 1\n", encoding="utf-8")
            summary = module.filter_dom_key_files_by_ground_distance(
                left_input,
                right_input,
                left_output,
                right_output,
                "left_dom.cub",
                "right_dom.cub",
                threshold_km=0.1,
            )
            self.assertEqual(summary["space"], "dom")
            self.assertEqual(summary["geometry_source"], "dom_projection_set_image")
            self.assertEqual(summary["retained_count"], 0)

    def test_ori_wrapper_uses_camera_first_and_drops_lookup_failure(self):
        from controlnet_construct import ground_distance_prefilter as module

        fake_ip = type(
            "FakeIp",
            (),
            {
                "Cube": FakeCube,
                "UniversalGroundMap": type(
                    "UGM",
                    (FakeGroundMap,),
                    {"CameraPriority": type("Priority", (), {"ProjectionFirst": "projection", "CameraFirst": "camera"})},
                ),
            },
        )
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(module, "bootstrap_runtime_environment", lambda: None), mock.patch.dict(sys.modules, {"isis_pybind": fake_ip}):
            tmp_path = Path(tmp)
            left_input = tmp_path / "left.key"
            right_input = tmp_path / "right.key"
            left_output = tmp_path / "left_filtered.key"
            right_output = tmp_path / "right_filtered.key"
            left_input.write_text("100 100\n99 1\n", encoding="utf-8")
            right_input.write_text("100 100\n1 1\n", encoding="utf-8")
            summary = module.filter_ori_key_files_by_ground_distance(
                left_input,
                right_input,
                left_output,
                right_output,
                "left.cub",
                "right.cub",
                threshold_km=1.0,
            )
            self.assertEqual(summary["space"], "ori")
            self.assertEqual(summary["geometry_source"], "ori_camera_set_image")
            self.assertEqual(summary["ground_lookup_failure_count"], 1)
            self.assertEqual(summary["retained_count"], 0)
```

- [ ] **Step 2: Run wrapper tests to verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_ground_distance_prefilter_unit_test -v
```

Expected: FAIL with missing `filter_dom_key_files_by_ground_distance` and `filter_ori_key_files_by_ground_distance`.

- [ ] **Step 3: Implement ISIS-backed wrappers**

Append to `examples/controlnet_construct/ground_distance_prefilter.py`:

```python
def _open_ground_map(cube_path: str | Path, *, band: int, priority_name: str):
    if int(band) <= 0:
        raise ValueError("Ground-distance prefilter band must be positive.")
    bootstrap_runtime_environment()
    import isis_pybind as ip

    cube = ip.Cube()
    cube.open(str(cube_path), "r")
    try:
        if int(band) > cube.band_count():
            raise ValueError(f"Band {band} is out of range for cube {cube_path}.")
        priority = getattr(ip.UniversalGroundMap.CameraPriority, priority_name)
        ground_map = ip.UniversalGroundMap(cube, priority)
        ground_map.set_band(int(band))
        return cube, ground_map
    except Exception:
        if cube.is_open():
            cube.close()
        raise


def _lookup_from_ground_map(ground_map):
    def lookup(sample: float, line: float) -> tuple[float, float] | None:
        if not ground_map.set_image(sample, line):
            return None
        latitude = float(ground_map.universal_latitude())
        longitude = float(ground_map.universal_longitude())
        if not (math.isfinite(latitude) and math.isfinite(longitude)):
            return None
        return latitude, longitude

    return lookup


def _filter_key_files_with_cube_ground_maps(
    left_input: str | Path,
    right_input: str | Path,
    left_output: str | Path,
    right_output: str | Path,
    left_cube_path: str | Path,
    right_cube_path: str | Path,
    *,
    threshold_km: float,
    lookup_failure_policy: str,
    lunar_radius_km: float,
    band: int,
    priority_name: str,
    space: str,
    geometry_source: str,
) -> dict[str, object]:
    left_cube, left_ground_map = _open_ground_map(left_cube_path, band=band, priority_name=priority_name)
    right_cube, right_ground_map = _open_ground_map(right_cube_path, band=band, priority_name=priority_name)
    try:
        return filter_stereo_pair_key_files_by_ground_distance(
            left_input,
            right_input,
            left_output,
            right_output,
            left_ground_lookup=_lookup_from_ground_map(left_ground_map),
            right_ground_lookup=_lookup_from_ground_map(right_ground_map),
            threshold_km=threshold_km,
            lookup_failure_policy=lookup_failure_policy,
            lunar_radius_km=lunar_radius_km,
            space=space,
            geometry_source=geometry_source,
        )
    finally:
        if left_cube.is_open():
            left_cube.close()
        if right_cube.is_open():
            right_cube.close()


def filter_dom_key_files_by_ground_distance(
    left_input: str | Path,
    right_input: str | Path,
    left_output: str | Path,
    right_output: str | Path,
    left_dom_cube_path: str | Path,
    right_dom_cube_path: str | Path,
    *,
    threshold_km: float,
    lookup_failure_policy: str = "drop",
    lunar_radius_km: float = LUNAR_MEAN_RADIUS_KM,
    dom_band: int = 1,
) -> dict[str, object]:
    return _filter_key_files_with_cube_ground_maps(
        left_input,
        right_input,
        left_output,
        right_output,
        left_dom_cube_path,
        right_dom_cube_path,
        threshold_km=threshold_km,
        lookup_failure_policy=lookup_failure_policy,
        lunar_radius_km=lunar_radius_km,
        band=dom_band,
        priority_name="ProjectionFirst",
        space="dom",
        geometry_source="dom_projection_set_image",
    )


def filter_ori_key_files_by_ground_distance(
    left_input: str | Path,
    right_input: str | Path,
    left_output: str | Path,
    right_output: str | Path,
    left_cube_path: str | Path,
    right_cube_path: str | Path,
    *,
    threshold_km: float,
    lookup_failure_policy: str = "drop",
    lunar_radius_km: float = LUNAR_MEAN_RADIUS_KM,
    band: int = 1,
) -> dict[str, object]:
    return _filter_key_files_with_cube_ground_maps(
        left_input,
        right_input,
        left_output,
        right_output,
        left_cube_path,
        right_cube_path,
        threshold_km=threshold_km,
        lookup_failure_policy=lookup_failure_policy,
        lunar_radius_km=lunar_radius_km,
        band=band,
        priority_name="CameraFirst",
        space="ori",
        geometry_source="ori_camera_set_image",
    )
```

Also add near the top of the file:

```python
try:
    from controlnet_construct.runtime import bootstrap_runtime_environment
except ImportError:
    from .runtime import bootstrap_runtime_environment
```

Modify `examples/controlnet_construct/__init__.py` to export:

```python
_LAZY_GROUND_DISTANCE_PREFILTER_EXPORTS = {
    "filter_dom_key_files_by_ground_distance",
    "filter_ori_key_files_by_ground_distance",
    "filter_stereo_pair_key_files_by_ground_distance",
    "filter_stereo_pair_keypoints_by_ground_distance",
    "ground_distance_km",
}
```

and route those names in the existing `__getattr__` lazy import pattern to `.ground_distance_prefilter`.

- [ ] **Step 4: Run wrapper tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_ground_distance_prefilter_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/controlnet_construct/ground_distance_prefilter.py examples/controlnet_construct/__init__.py tests/unitTest/controlnet_construct_ground_distance_prefilter_unit_test.py
git commit -m "feat: add ISIS ground-distance prefilter wrappers"
```

## Task 3: ControlNet from-dom Fallback Before RANSAC

**Files:**
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`
- Test: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Write failing from-dom call-order test**

Add to `tests/unitTest/controlnet_construct_matching_unit_test.py` near existing `build_controlnet_for_dom_stereo_pair` tests:

```python
def test_from_dom_runs_ground_distance_prefilter_before_ransac_when_enabled(self):
    calls = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        left_dom_key = tmp_path / "left_dom.key"
        right_dom_key = tmp_path / "right_dom.key"
        output_net = tmp_path / "out.net"
        for path in (left_dom_key, right_dom_key):
            path.write_text("100 100\n1 1\n2 2\n", encoding="utf-8")

        def fake_merge(left_input, right_input, left_output, right_output, **kwargs):
            calls.append("merge")
            Path(left_output).write_text(Path(left_input).read_text(encoding="utf-8"), encoding="utf-8")
            Path(right_output).write_text(Path(right_input).read_text(encoding="utf-8"), encoding="utf-8")
            return {"input_count": 2, "unique_count": 2, "duplicate_count": 0, "hash_strategy": "rounded_stereo_pair", "hash_coordinate_fields": ["left_sample", "left_line", "right_sample", "right_line"], "hash_rounding_decimals": 2}

        def fake_prefilter(left_input, right_input, left_output, right_output, left_dom_cube, right_dom_cube, **kwargs):
            calls.append("prefilter")
            Path(left_output).write_text(Path(left_input).read_text(encoding="utf-8"), encoding="utf-8")
            Path(right_output).write_text(Path(right_input).read_text(encoding="utf-8"), encoding="utf-8")
            return {"applied": True, "retained_count": 2, "dropped_count": 0, "threshold_km": 1.0}

        def fake_ransac(left_input, right_input, left_output, right_output, **kwargs):
            calls.append("ransac")
            self.assertTrue(str(left_input).endswith("dom_ground_prefilter.key"))
            Path(left_output).write_text(Path(left_input).read_text(encoding="utf-8"), encoding="utf-8")
            Path(right_output).write_text(Path(right_input).read_text(encoding="utf-8"), encoding="utf-8")
            return {"status": "filtered", "retained_count": 2, "dropped_count": 0, "mode": "loose", "retained_soft_outlier_positions": []}

        with mock.patch("controlnet_construct.controlnet_stereopair.merge_stereo_pair_key_files", fake_merge), \
             mock.patch("controlnet_construct.controlnet_stereopair.filter_dom_key_files_by_ground_distance", fake_prefilter), \
             mock.patch("controlnet_construct.controlnet_stereopair.filter_stereo_pair_key_files_with_ransac", fake_ransac), \
             mock.patch("controlnet_construct.controlnet_stereopair.convert_paired_dom_keypoints_to_original", return_value={"left_conversion": {"output_count": 2}, "right_conversion": {"output_count": 2}}), \
             mock.patch("controlnet_construct.controlnet_stereopair.build_controlnet_for_stereo_pair", return_value={"point_count": 2}):
            result = build_controlnet_for_dom_stereo_pair(
                left_dom_key,
                right_dom_key,
                tmp_path / "left_dom.cub",
                tmp_path / "right_dom.cub",
                tmp_path / "left.cub",
                tmp_path / "right.cub",
                {},
                output_net,
                pre_ransac_max_ground_distance_km=1.0,
            )

        self.assertEqual(calls, ["merge", "prefilter", "ransac"])
        self.assertEqual(result["pre_ransac_ground_distance_filter"]["applied"], True)
```

- [ ] **Step 2: Write failing disabled-mode test**

Add:

```python
def test_from_dom_ground_distance_prefilter_disabled_with_zero_threshold(self):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        left_dom_key = tmp_path / "left_dom.key"
        right_dom_key = tmp_path / "right_dom.key"
        output_net = tmp_path / "out.net"
        for path in (left_dom_key, right_dom_key):
            path.write_text("100 100\n1 1\n", encoding="utf-8")

        with mock.patch("controlnet_construct.controlnet_stereopair.filter_dom_key_files_by_ground_distance") as prefilter_mock, \
             mock.patch("controlnet_construct.controlnet_stereopair.filter_stereo_pair_key_files_with_ransac", side_effect=lambda left, right, left_out, right_out, **kwargs: {"status": "skipped_insufficient_points", "retained_count": 1, "dropped_count": 0, "mode": "loose", "retained_soft_outlier_positions": []}), \
             mock.patch("controlnet_construct.controlnet_stereopair.convert_paired_dom_keypoints_to_original", return_value={"left_conversion": {"output_count": 1}, "right_conversion": {"output_count": 1}}), \
             mock.patch("controlnet_construct.controlnet_stereopair.build_controlnet_for_stereo_pair", return_value={"point_count": 1}):
            result = build_controlnet_for_dom_stereo_pair(
                left_dom_key,
                right_dom_key,
                tmp_path / "left_dom.cub",
                tmp_path / "right_dom.cub",
                tmp_path / "left.cub",
                tmp_path / "right.cub",
                {},
                output_net,
                skip_merge=True,
                pre_ransac_max_ground_distance_km=0.0,
            )

        prefilter_mock.assert_not_called()
        self.assertEqual(result["pre_ransac_ground_distance_filter"]["status"], "disabled")
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Expected: FAIL because `pre_ransac_max_ground_distance_km` is not accepted.

- [ ] **Step 4: Implement from-dom fallback**

Modify imports in `examples/controlnet_construct/controlnet_stereopair.py`:

```python
from controlnet_construct.ground_distance_prefilter import (
    PREFILTER_METADATA_KEY,
    filter_dom_key_files_by_ground_distance,
)
```

Add constants:

```python
DEFAULT_PRE_RANSAC_MAX_GROUND_DISTANCE_KM = 1.0
DEFAULT_PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY = "drop"
```

Add parameters to `build_controlnet_for_dom_stereo_pair(...)`:

```python
pre_ransac_max_ground_distance_km: float = DEFAULT_PRE_RANSAC_MAX_GROUND_DISTANCE_KM,
pre_ransac_ground_lookup_failure_policy: str = DEFAULT_PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY,
```

After merge and before RANSAC:

```python
    left_ground_prefilter_dom_key = _default_intermediate_key_path(output_path, "left", "dom_ground_prefilter")
    right_ground_prefilter_dom_key = _default_intermediate_key_path(output_path, "right", "dom_ground_prefilter")
    if float(pre_ransac_max_ground_distance_km) > 0.0:
        pre_ransac_ground_distance_filter = filter_dom_key_files_by_ground_distance(
            left_dom_key_for_conversion,
            right_dom_key_for_conversion,
            left_ground_prefilter_dom_key,
            right_ground_prefilter_dom_key,
            left_dom_cube_path,
            right_dom_cube_path,
            threshold_km=float(pre_ransac_max_ground_distance_km),
            lookup_failure_policy=pre_ransac_ground_lookup_failure_policy,
            dom_band=dom_band,
        )
        left_dom_key_for_conversion = left_ground_prefilter_dom_key
        right_dom_key_for_conversion = right_ground_prefilter_dom_key
    else:
        pre_ransac_ground_distance_filter = {
            "applied": False,
            "already_prefiltered": False,
            "status": "disabled",
            "threshold_km": float(pre_ransac_max_ground_distance_km),
        }
```

Add to returned result:

```python
"pre_ransac_ground_distance_filter": pre_ransac_ground_distance_filter,
```

- [ ] **Step 5: Run from-dom tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Expected: PASS for the new tests and no regressions in this module.

- [ ] **Step 6: Commit**

```bash
git add examples/controlnet_construct/controlnet_stereopair.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: add ControlNet DOM ground-distance prefilter"
```

## Task 4: ControlNet Metadata Skip Rule

**Files:**
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`
- Test: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Write failing skip-rule test**

Add:

```python
def test_from_dom_skips_ground_distance_prefilter_when_upstream_metadata_applied(self):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        left_dom_key = tmp_path / "left_dom.key"
        right_dom_key = tmp_path / "right_dom.key"
        metadata_path = tmp_path / "match_metadata.json"
        output_net = tmp_path / "out.net"
        for path in (left_dom_key, right_dom_key):
            path.write_text("100 100\n1 1\n", encoding="utf-8")
        metadata_path.write_text(
            json.dumps({"pre_ransac_ground_distance_filter": {"applied": True, "threshold_km": 5.0}}),
            encoding="utf-8",
        )

        with mock.patch("controlnet_construct.controlnet_stereopair.filter_dom_key_files_by_ground_distance") as prefilter_mock, \
             mock.patch("controlnet_construct.controlnet_stereopair.filter_stereo_pair_key_files_with_ransac", return_value={"status": "skipped_insufficient_points", "retained_count": 1, "dropped_count": 0, "mode": "loose", "retained_soft_outlier_positions": []}), \
             mock.patch("controlnet_construct.controlnet_stereopair.convert_paired_dom_keypoints_to_original", return_value={"left_conversion": {"output_count": 1}, "right_conversion": {"output_count": 1}}), \
             mock.patch("controlnet_construct.controlnet_stereopair.build_controlnet_for_stereo_pair", return_value={"point_count": 1}):
            result = build_controlnet_for_dom_stereo_pair(
                left_dom_key,
                right_dom_key,
                tmp_path / "left_dom.cub",
                tmp_path / "right_dom.cub",
                tmp_path / "left.cub",
                tmp_path / "right.cub",
                {},
                output_net,
                skip_merge=True,
                pre_ransac_match_metadata_path=metadata_path,
                pre_ransac_max_ground_distance_km=1.0,
            )

        prefilter_mock.assert_not_called()
        self.assertTrue(result["pre_ransac_ground_distance_filter"]["already_prefiltered"])
        self.assertEqual(result["pre_ransac_ground_distance_filter"]["upstream_summary"]["threshold_km"], 5.0)
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Expected: FAIL because `pre_ransac_match_metadata_path` is not accepted.

- [ ] **Step 3: Implement metadata read helper and skip**

In `controlnet_stereopair.py`, add:

```python
def _load_upstream_ground_distance_filter_summary(metadata_path: str | Path | None) -> dict[str, object] | None:
    if metadata_path is None:
        return None
    path = Path(metadata_path)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    summary = payload.get(PREFILTER_METADATA_KEY)
    if isinstance(summary, dict) and summary.get("applied") is True:
        return dict(summary)
    image_match = payload.get("image_match")
    if isinstance(image_match, dict):
        summary = image_match.get(PREFILTER_METADATA_KEY)
        if isinstance(summary, dict) and summary.get("applied") is True:
            return dict(summary)
    return None
```

Add parameter:

```python
pre_ransac_match_metadata_path: str | Path | None = None,
```

Before fallback filtering:

```python
    upstream_ground_filter = _load_upstream_ground_distance_filter_summary(pre_ransac_match_metadata_path)
    if upstream_ground_filter is not None:
        pre_ransac_ground_distance_filter = {
            "applied": False,
            "already_prefiltered": True,
            "source": "input_metadata",
            "upstream_summary": upstream_ground_filter,
        }
    elif float(pre_ransac_max_ground_distance_km) > 0.0:
        ...
```

- [ ] **Step 4: Run matching unit tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/controlnet_construct/controlnet_stereopair.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: skip ControlNet prefilter for upstream-filtered keys"
```

## Task 5: Matching-Stage DOM and ORI Filtering

**Files:**
- Modify: `examples/image_match/image_match.py`
- Test: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Write failing DOM metadata test**

Add to existing DOM match tests:

```python
def test_match_dom_pair_records_pre_ransac_ground_distance_filter(self):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        left_output = tmp_path / "left.key"
        right_output = tmp_path / "right.key"
        metadata_output = tmp_path / "metadata.json"

        with mock.patch("image_match.image_match.match_dom_pair", return_value=(
            KeypointFile(100, 100, (Keypoint(1, 1),)),
            KeypointFile(100, 100, (Keypoint(2, 2),)),
            {
                "preparation": {"left": {"path": "left_dom.cub"}, "right": {"path": "right_dom.cub"}},
                "status": "matched",
                "reason": "ok",
                "point_count": 1,
                "left_feature_count_total": 1,
                "right_feature_count_total": 1,
                "feature_count_total": 2,
                "tile_match_count_total": 1,
                "tile_count": 1,
                "tile_count_before_preindex_filter": 1,
                "tile_count_after_preindex_filter": 1,
                "preindexed_skipped_tile_count": 0,
                "full_resolution_skipped_tile_count": 0,
                "matched_tile_count": 1,
                "skipped_tile_count": 0,
                "tile_validity_prefilter_enabled": False,
                "tile_validity_cache_dir": "",
                "tile_validity_cell_width": 0,
                "tile_validity_cell_height": 0,
                "tile_block_alignment_mode": "none",
                "block_alignment_reason": "",
                "tile_block_alignment": {},
                "tile_validity_skip_reasons": {},
                "left_tile_validity_index": {},
                "right_tile_validity_index": {},
                "tiling_used": False,
                "valid_pixel_percent_threshold": 0.0,
                "invalid_pixel_radius": 0,
                "matcher": {"method": "flann"},
                "parallel_cpu_requested": False,
                "num_worker_parallel_cpu": 1,
                "parallel_cpu_used": False,
                "parallel_cpu_backend": "serial",
                "parallel_cpu_worker_count": 1,
                "tile_match_backend": "serial",
                "low_resolution_offset": {},
                "low_resolution_matching_target_long_edge": None,
                "resolved_low_resolution_level": None,
                "adaptive_routing": {},
            },
        )), mock.patch("image_match.image_match.filter_dom_key_files_by_ground_distance", return_value={
            "applied": True,
            "retained_count": 1,
            "dropped_count": 0,
        }):
            result = match_dom_pair_to_key_files(
                "left_dom.cub",
                "right_dom.cub",
                left_output,
                right_output,
                metadata_output=metadata_output,
                write_match_visualization=False,
                pre_ransac_max_ground_distance_km=1.0,
            )

        self.assertEqual(result["pre_ransac_ground_distance_filter"]["applied"], True)
        payload = json.loads(metadata_output.read_text(encoding="utf-8"))
        self.assertEqual(payload["pre_ransac_ground_distance_filter"]["applied"], True)
```

- [ ] **Step 2: Run focused test to verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Expected: FAIL because `pre_ransac_max_ground_distance_km` is not accepted.

- [ ] **Step 3: Implement matching-stage prefilter in `image_match.py`**

Add imports:

```python
try:
    from controlnet_construct.ground_distance_prefilter import (
        PREFILTER_METADATA_KEY,
        filter_dom_key_files_by_ground_distance,
        filter_ori_key_files_by_ground_distance,
    )
except ImportError:
    from .ground_distance_prefilter import (
        PREFILTER_METADATA_KEY,
        filter_dom_key_files_by_ground_distance,
        filter_ori_key_files_by_ground_distance,
    )
```

Add defaults:

```python
DEFAULT_PRE_RANSAC_MAX_GROUND_DISTANCE_KM = 1.0
DEFAULT_PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY = "drop"
```

Add helper:

```python
def _disabled_ground_distance_filter_summary(threshold_km: float) -> dict[str, object]:
    return {
        "applied": False,
        "already_prefiltered": False,
        "status": "disabled",
        "threshold_km": float(threshold_km),
    }
```

Add parameters to `match_dom_pair_to_key_files(...)`:

```python
pre_ransac_max_ground_distance_km: float = DEFAULT_PRE_RANSAC_MAX_GROUND_DISTANCE_KM,
pre_ransac_ground_lookup_failure_policy: str = DEFAULT_PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY,
```

After writing matched key files and before visualization:

```python
    if float(pre_ransac_max_ground_distance_km) > 0.0 and not export_only:
        pre_ransac_ground_distance_filter = filter_dom_key_files_by_ground_distance(
            left_output_key,
            right_output_key,
            left_output_key,
            right_output_key,
            left_dom_cube_path,
            right_dom_cube_path,
            threshold_km=float(pre_ransac_max_ground_distance_km),
            lookup_failure_policy=pre_ransac_ground_lookup_failure_policy,
            dom_band=band,
        )
    else:
        pre_ransac_ground_distance_filter = _disabled_ground_distance_filter_summary(pre_ransac_max_ground_distance_km)
    metadata_payload[PREFILTER_METADATA_KEY] = pre_ransac_ground_distance_filter
```

Add equivalent parameters to `match_ori_pair_to_key_files(...)` and call `filter_ori_key_files_by_ground_distance(...)` with `left_cube_path`, `right_cube_path`, and `band=band`.

- [ ] **Step 4: Run focused matching tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/image_match/image_match.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: apply ground-distance prefilter during matching"
```

## Task 6: CLI and Wrapper Forwarding

**Files:**
- Modify: `examples/image_match/image_match.py`
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`
- Modify: `examples/controlnet_construct/run_image_match_batch_example.sh`
- Modify: `examples/controlnet_construct/run_pipeline_example.sh`
- Modify: `examples/controlnet_construct/run_ori_match_pipeline_example.sh`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Write failing parser and wrapper tests**

Add focused parser tests in `tests/unitTest/controlnet_construct_pipeline_unit_test.py`:

```python
def test_image_match_parser_accepts_pre_ransac_ground_distance_threshold(self):
    parser = image_match.build_argument_parser()
    args = parser.parse_args([
        "left.cub",
        "right.cub",
        "--pre-ransac-max-ground-distance-km",
        "2.5",
    ])
    self.assertEqual(args.pre_ransac_max_ground_distance_km, 2.5)


def test_controlnet_from_dom_parser_accepts_pre_ransac_ground_distance_threshold(self):
    parser = controlnet_stereopair.build_argument_parser()
    args = parser.parse_args([
        "from-dom",
        "left.key",
        "right.key",
        "left_dom.cub",
        "right_dom.cub",
        "left.cub",
        "right.cub",
        "config.json",
        "out.net",
        "--pre-ransac-max-ground-distance-km",
        "0",
    ])
    self.assertEqual(args.pre_ransac_max_ground_distance_km, 0.0)
```

Add a shell wrapper test following the existing style for `run_image_match_batch_example.sh`:

```python
def test_run_image_match_batch_example_forwards_pre_ransac_ground_distance(self):
    with temporary_directory() as temp_dir:
        work_dir = temp_dir / "work"
        work_dir.mkdir()

        original_list = work_dir / "original_images.lis"
        dom_list = work_dir / "doms.lis"
        pair_list = work_dir / "images_overlap.lis"
        fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
        fake_python = temp_dir / "fake_python"

        write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
        pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")

        fake_python_dispatcher.write_text(
            _embedded_python_script(
                f"""
                #!{sys.executable}
                import sys
                from pathlib import Path

                def _run_stdin_python() -> int:
                    code = sys.stdin.read()
                    globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                    sys.argv = ['-'] + sys.argv[2:]
                    exec(compile(code, "<stdin>", "exec"), globals_dict)
                    return 0

                def main() -> int:
                    if len(sys.argv) < 2:
                        return 0
                    if sys.argv[1] == "-":
                        return _run_stdin_python()

                    script_name = Path(sys.argv[1]).name
                    args = sys.argv[2:]
                    if script_name == "image_match.py":
                        if "--pre-ransac-max-ground-distance-km" not in args:
                            raise SystemExit("missing --pre-ransac-max-ground-distance-km forwarding")
                        threshold = args[args.index("--pre-ransac-max-ground-distance-km") + 1]
                        if threshold != "0":
                            raise SystemExit(f"unexpected pre-ransac threshold: {{threshold}}")
                        if "--pre-ransac-ground-lookup-failure-policy" not in args:
                            raise SystemExit("missing --pre-ransac-ground-lookup-failure-policy forwarding")
                        policy = args[args.index("--pre-ransac-ground-lookup-failure-policy") + 1]
                        if policy != "keep":
                            raise SystemExit(f"unexpected lookup failure policy: {{policy}}")
                        key_index = 4 if args and args[0] == "--config" else 2
                        Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                        Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
                        return 0
                    raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                raise SystemExit(main())
                """
            ),
            encoding="utf-8",
        )
        fake_python.write_text(
            textwrap.dedent(
                f"""
                #!/usr/bin/env bash
                exec {sys.executable} "{fake_python_dispatcher}" "$@"
                """
            ).lstrip()
            + "\n",
            encoding="utf-8",
        )
        fake_python.chmod(0o755)

        completed = subprocess.run(
            [
                "bash",
                str(RUN_IMAGE_MATCH_BATCH_EXAMPLE_PATH),
                "--work-dir",
                str(work_dir),
                "--python",
                str(fake_python),
                "--pre-ransac-max-ground-distance-km",
                "0",
                "--pre-ransac-ground-lookup-failure-policy",
                "keep",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    self.assertEqual(completed.returncode, 0, msg=completed.stderr)
```

- [ ] **Step 2: Run parser/wrapper tests to verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: FAIL because parser and wrapper flags are not wired.

- [ ] **Step 3: Add image_match CLI args and function forwarding**

In `examples/image_match/image_match.py`, add parser args near RANSAC visualization args:

```python
parser.add_argument("--pre-ransac-max-ground-distance-km", type=float, default=DEFAULT_PRE_RANSAC_MAX_GROUND_DISTANCE_KM, help="Drop stereo correspondences before RANSAC when spherical ground distance exceeds this threshold in kilometers. Use 0 to disable.")
parser.add_argument("--pre-ransac-ground-lookup-failure-policy", choices=("drop", "keep"), default=DEFAULT_PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY, help="How pre-RANSAC ground-distance filtering handles points whose ground coordinate cannot be resolved. Default: drop.")
```

Pass into `match_dom_pair_to_key_files(...)` in `main()`:

```python
pre_ransac_max_ground_distance_km=args.pre_ransac_max_ground_distance_km,
pre_ransac_ground_lookup_failure_policy=args.pre_ransac_ground_lookup_failure_policy,
```

- [ ] **Step 4: Add controlnet CLI args and dispatch forwarding**

In `controlnet_stereopair.py`, add helper:

```python
def _add_pre_ransac_ground_distance_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pre-ransac-max-ground-distance-km", type=float, default=DEFAULT_PRE_RANSAC_MAX_GROUND_DISTANCE_KM, help="Drop stereo correspondences before RANSAC when spherical ground distance exceeds this threshold in kilometers. Use 0 to disable.")
    parser.add_argument("--pre-ransac-ground-lookup-failure-policy", choices=("drop", "keep"), default=DEFAULT_PRE_RANSAC_GROUND_LOOKUP_FAILURE_POLICY, help="How pre-RANSAC ground-distance filtering handles unresolved ground coordinates. Default: drop.")
```

Call this helper from:

- `_build_from_original_match_parser`
- `_build_from_dom_match_parser`
- `_build_from_dom_parser`
- `_build_from_dom_batch_parser`

Pass parsed values into build functions:

```python
pre_ransac_max_ground_distance_km=args.pre_ransac_max_ground_distance_km,
pre_ransac_ground_lookup_failure_policy=args.pre_ransac_ground_lookup_failure_policy,
```

- [ ] **Step 5: Add shell wrapper forwarding**

In each shell wrapper, add state variables:

```bash
local pre_ransac_max_ground_distance_km_input=""
local pre_ransac_ground_lookup_failure_policy_input=""
```

Add parse cases:

```bash
--pre-ransac-max-ground-distance-km)
  [[ $# -ge 2 ]] || die "missing value for --pre-ransac-max-ground-distance-km"
  pre_ransac_max_ground_distance_km_input=$2
  shift 2
  ;;
--pre-ransac-ground-lookup-failure-policy)
  [[ $# -ge 2 ]] || die "missing value for --pre-ransac-ground-lookup-failure-policy"
  pre_ransac_ground_lookup_failure_policy_input=$2
  shift 2
  ;;
```

Append to command arrays when set:

```bash
if [[ -n "$pre_ransac_max_ground_distance_km_input" ]]; then
  match_args+=(--pre-ransac-max-ground-distance-km "$pre_ransac_max_ground_distance_km_input")
fi
if [[ -n "$pre_ransac_ground_lookup_failure_policy_input" ]]; then
  match_args+=(--pre-ransac-ground-lookup-failure-policy "$pre_ransac_ground_lookup_failure_policy_input")
fi
```

For `controlnet_stereopair.py` command arrays, use `controlnet_args+=` or the local array name already present in that wrapper.

- [ ] **Step 6: Run pipeline unit tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add examples/image_match/image_match.py examples/controlnet_construct/controlnet_stereopair.py examples/controlnet_construct/run_image_match_batch_example.sh examples/controlnet_construct/run_pipeline_example.sh examples/controlnet_construct/run_ori_match_pipeline_example.sh tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: forward pre-ransac ground-distance options"
```

## Task 7: Parameter Catalog and Report Metadata

**Files:**
- Modify: `examples/controlnet_construct/parameter_catalog.py`
- Modify: `examples/controlnet_construct/batch_summary.py`
- Test: `tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py`
- Test: `tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py`

- [ ] **Step 1: Write failing catalog test**

Add:

```python
def test_catalog_includes_pre_ransac_ground_distance_threshold(self):
    catalog = parameter_catalog.build_parameter_catalog()
    by_name = {entry.name: entry for entry in catalog.parameters}
    self.assertIn("pre_ransac_max_ground_distance_km", by_name)
    entry = by_name["pre_ransac_max_ground_distance_km"]
    self.assertEqual(entry.cli_flag, "--pre-ransac-max-ground-distance-km")
    self.assertIn("controlnet_stereopair.from-dom", entry.entrypoints)
    self.assertIn("controlnet_stereopair.from-ori-match", entry.entrypoints)
```

- [ ] **Step 2: Write failing batch-summary extraction test**

Add:

```python
def test_batch_summary_extracts_pre_ransac_ground_distance_counts(self):
    pair_result = {
        "merge": {"unique_count": 12},
        "pre_ransac_ground_distance_filter": {
            "applied": True,
            "retained_count": 9,
            "dropped_count": 3,
            "dropped_ground_distance_count": 2,
            "ground_lookup_failure_count": 1,
        },
        "ransac": {"retained_count": 8},
        "controlnet": {"point_count": 8},
    }
    summary = batch_summary.summarize_pair_result(pair_result)
    self.assertEqual(summary["pre_ransac_ground_distance_retained_count"], 9)
    self.assertEqual(summary["pre_ransac_ground_distance_dropped_count"], 3)
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: FAIL with missing catalog entry and missing summary fields.

- [ ] **Step 4: Add catalog entries**

In `parameter_catalog.py`, add specs:

```python
_spec("pre_ransac_max_ground_distance_km", "matching", "--pre-ransac-max-ground-distance-km", "float", config_path="ImageMatch.pre_ransac_max_ground_distance_km", default=1.0, min_value=0.0, entrypoints=(IMAGE_MATCH, FROM_ORI_MATCH, FROM_DOM_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Pre-RANSAC spherical ground-distance threshold in kilometers; 0 disables.")
_spec("pre_ransac_ground_lookup_failure_policy", "matching", "--pre-ransac-ground-lookup-failure-policy", "choice", config_path="ImageMatch.pre_ransac_ground_lookup_failure_policy", default="drop", choices=("drop", "keep"), entrypoints=(IMAGE_MATCH, FROM_ORI_MATCH, FROM_DOM_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Policy for correspondences whose ground coordinates cannot be resolved during pre-RANSAC filtering.")
```

Use the exact local `_spec` signature from the file. If the file uses different keyword names, preserve its pattern while keeping the field values above.

- [ ] **Step 5: Add batch summary fields**

In `batch_summary.py`, read:

```python
ground_filter = pair_result.get("pre_ransac_ground_distance_filter")
if not isinstance(ground_filter, dict):
    ground_filter = {}
```

Add pair summary fields:

```python
"pre_ransac_ground_distance_applied": bool(ground_filter.get("applied")),
"pre_ransac_ground_distance_already_prefiltered": bool(ground_filter.get("already_prefiltered")),
"pre_ransac_ground_distance_retained_count": _maybe_int(ground_filter.get("retained_count")),
"pre_ransac_ground_distance_dropped_count": _maybe_int(ground_filter.get("dropped_count")),
"pre_ransac_ground_distance_dropped_distance_count": _maybe_int(ground_filter.get("dropped_ground_distance_count")),
"pre_ransac_ground_lookup_failure_count": _maybe_int(ground_filter.get("ground_lookup_failure_count")),
```

- [ ] **Step 6: Run tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add examples/controlnet_construct/parameter_catalog.py examples/controlnet_construct/batch_summary.py tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py
git commit -m "feat: report pre-ransac ground-distance filtering"
```

## Task 8: Final Focused Verification

**Files:**
- Verify only; do not edit implementation files in this task unless a preceding task failed.

- [ ] **Step 1: Run smoke import**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tests/smoke_import.py
```

Expected: `smoke import ok`.

- [ ] **Step 2: Run focused unit suite**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_ground_distance_prefilter_unit_test tests.unitTest.controlnet_construct_matching_unit_test tests.unitTest.controlnet_construct_pipeline_unit_test tests.unitTest.controlnet_construct_parameter_catalog_unit_test tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: PASS, allowing existing unrelated skips.

- [ ] **Step 3: Run a CLI help sanity check**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
python examples/image_match/image_match.py --help | rg "pre-ransac-max-ground-distance-km"
python examples/controlnet_construct/controlnet_stereopair.py from-dom --help | rg "pre-ransac-max-ground-distance-km"
python examples/controlnet_construct/controlnet_stereopair.py from-ori-match --help | rg "pre-ransac-max-ground-distance-km"
```

Expected: all three commands print the new flag.

- [ ] **Step 4: Check git status for local-file guardrails**

Run:

```bash
git status --short
```

Expected:

- `.gitignore` is not modified or staged.
- `print.prt` may be modified as a local ISIS runtime artifact; do not stage it.
- Only intentional implementation/test/wrapper files are staged or committed.

- [ ] **Step 5: Commit any final test-only correction**

If Step 1-4 required a small correction, commit it:

```bash
git add <intentional-files-only>
git commit -m "test: verify pre-ransac ground-distance filtering"
```

If no correction was needed, do not create an empty commit.

## Self-Review

- Spec coverage:
  - Default-on threshold and zero-disable are covered in Tasks 3, 5, and 6.
  - Spherical distance and longitude wrap are covered in Task 1.
  - ORI and DOM ground lookup wrappers are covered in Task 2.
  - Matching-stage filtering and metadata are covered in Task 5.
  - ControlNet fallback and metadata skip are covered in Tasks 3 and 4.
  - Wrapper/config/reporting coverage is covered in Tasks 6 and 7.
  - Final verification is covered in Task 8.
- Placeholder scan:
  - No `TBD` or `TODO` steps remain.
  - Every code-changing task includes concrete code snippets and commands.
- Type consistency:
  - Metadata key is consistently `pre_ransac_ground_distance_filter`.
  - Threshold flag is consistently `--pre-ransac-max-ground-distance-km`.
  - Disable value is consistently threshold `0`.
  - Lookup failure policy is consistently `drop|keep`, default `drop`.
