# DOM-Coordinate Affine RANSAC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make DOM-projected distance filtering and DOM-pixel affine-partial RANSAC the default geometric filtering path for DOM matching, ORI matching, and ControlNet construction while preserving explicit legacy spherical/homography modes.

**Architecture:** Extend the existing ground-distance and stereo-RANSAC helper modules rather than creating a parallel stack. DOM and ORI callers pass explicit method/model options through `image_match.py`, `controlnet_stereopair.py`, wrappers, and parameter catalog; ORI default DOM-projected filtering fails early unless corresponding DOMs are provided. Final filtering keeps left/right keypoint alignment by applying one retained-index mask to both sides.

**Tech Stack:** Python 3.12, unittest, OpenCV `cv2.estimateAffinePartial2D` / `cv2.estimateAffine2D` / `cv2.findHomography`, PyISIS DOM projection APIs, existing `.key` file helpers.

---

## Scope Check

This SPEC spans the matching filter stack, ControlNet wiring, and CLI forwarding, but these are one coherent behavior change: the default geometric filter policy. Do not split into separate specs. The implementation should remain incremental: pure helpers first, then matching entrypoints, then ControlNet and wrappers.

## File Structure

- Modify: `examples/controlnet_construct/ground_distance_prefilter.py`
  - Add projected-distance filtering helpers with retained indices.
  - Refine DOM wrapper metadata from spherical `dom_projection_set_image` to projected `dom_projection_coordinate`.
  - Keep ORI spherical wrapper as explicit legacy behavior.
- Modify: `examples/image_match/stereo_ransac.py`
  - Add model selection for `affine-partial`, `affine`, and `homography`.
  - Change defaults to affine-partial with 10 pixel threshold.
  - Add modern summary fields while preserving `homography_matrix` for homography.
- Modify: `examples/controlnet_construct/stereo_ransac.py`
  - Keep this copy in sync with `examples/image_match/stereo_ransac.py`.
- Modify: `examples/image_match/image_match.py`
  - Add validation and CLI/config support for `pre_ransac_distance_method` and `ransac_model`.
  - Use projected DOM distance by default for DOM matches/imports.
  - Require corresponding DOMs for ORI default DOM-projected filtering.
  - Forward RANSAC model/threshold into visualization filtering.
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`
  - Add `pre_ransac_distance_method` and `ransac_model` to from-DOM/from-DOM-match/from-DOM-batch/from-ORI-match paths.
  - Use affine-partial RANSAC in DOM pixel coordinates by default.
  - Skip duplicate distance filtering only when upstream metadata records default DOM-projected filtering.
- Modify: `examples/controlnet_construct/parameter_catalog.py`
  - Add catalog entries and allowed values.
- Modify: `examples/controlnet_construct/run_image_match_batch_example.sh`
  - Forward `--pre-ransac-distance-method` and `--ransac-model`.
- Modify: `examples/controlnet_construct/experiments/match_original_gsd_lro_dom_pairs_large.py`
  - Forward the same two flags to batch/direct image matching where this script shells out.
- Test: `tests/unitTest/controlnet_construct_ground_distance_prefilter_unit_test.py`
- Test: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
- Test: add `tests/unitTest/stereo_ransac_model_unit_test.py`

---

### Task 1: Add Projected-Distance Pure Helper

**Files:**
- Modify: `examples/controlnet_construct/ground_distance_prefilter.py`
- Modify: `tests/unitTest/controlnet_construct_ground_distance_prefilter_unit_test.py`

- [ ] **Step 1: Write failing projected-distance helper tests**

Append these tests inside `GroundDistancePrefilterTest` in `tests/unitTest/controlnet_construct_ground_distance_prefilter_unit_test.py`:

```python
    def test_projected_distance_filter_drops_by_planar_kilometers_and_returns_indices(self) -> None:
        from controlnet_construct.ground_distance_prefilter import (
            filter_stereo_pair_keypoints_by_projected_distance,
        )

        left_key_file = KeypointFile(
            1000,
            1000,
            (Keypoint(1.0, 1.0), Keypoint(2.0, 2.0), Keypoint(3.0, 3.0)),
        )
        right_key_file = KeypointFile(
            1000,
            1000,
            (Keypoint(10.0, 10.0), Keypoint(20.0, 20.0), Keypoint(30.0, 30.0)),
        )
        left_lookup = {
            (1.0, 1.0): (0.0, 0.0),
            (2.0, 2.0): (0.0, 0.0),
            (3.0, 3.0): (1000.0, 1000.0),
        }
        right_lookup = {
            (10.0, 10.0): (500.0, 0.0),
            (20.0, 20.0): (2500.0, 0.0),
            (30.0, 30.0): (1000.0, 1000.0),
        }

        filtered_left, filtered_right, summary, retained_indices = filter_stereo_pair_keypoints_by_projected_distance(
            left_key_file,
            right_key_file,
            left_projected_lookup=lambda sample, line: left_lookup[(sample, line)],
            right_projected_lookup=lambda sample, line: right_lookup[(sample, line)],
            threshold_km=1.0,
            left_dom="left_dom.cub",
            right_dom="right_dom.cub",
        )

        self.assertEqual(filtered_left.points, (Keypoint(1.0, 1.0), Keypoint(3.0, 3.0)))
        self.assertEqual(filtered_right.points, (Keypoint(10.0, 10.0), Keypoint(30.0, 30.0)))
        self.assertEqual(retained_indices, (0, 2))
        self.assertEqual(summary["distance_method"], "dom_projected")
        self.assertEqual(summary["space"], "dom")
        self.assertEqual(summary["geometry_source"], "dom_projection_coordinate")
        self.assertEqual(summary["input_count"], 3)
        self.assertEqual(summary["retained_count"], 2)
        self.assertEqual(summary["dropped_ground_distance_count"], 1)
        self.assertEqual(summary["distance_summary_km"]["max"], 2.5)
        self.assertEqual(summary["left_dom"], "left_dom.cub")
        self.assertEqual(summary["right_dom"], "right_dom.cub")

    def test_projected_distance_filter_disabled_returns_all_indices_without_lookups(self) -> None:
        from controlnet_construct.ground_distance_prefilter import (
            filter_stereo_pair_keypoints_by_projected_distance,
        )

        left_key_file = KeypointFile(1000, 1000, (Keypoint(1.0, 1.0), Keypoint(2.0, 2.0)))
        right_key_file = KeypointFile(1000, 1000, (Keypoint(10.0, 10.0), Keypoint(20.0, 20.0)))

        def raising_lookup(sample: float, line: float) -> tuple[float, float] | None:
            raise AssertionError("projected lookup must not be called for threshold 0")

        filtered_left, filtered_right, summary, retained_indices = filter_stereo_pair_keypoints_by_projected_distance(
            left_key_file,
            right_key_file,
            left_projected_lookup=raising_lookup,
            right_projected_lookup=raising_lookup,
            threshold_km=0.0,
        )

        self.assertEqual(filtered_left.points, left_key_file.points)
        self.assertEqual(filtered_right.points, right_key_file.points)
        self.assertEqual(retained_indices, (0, 1))
        self.assertFalse(summary["applied"])
        self.assertEqual(summary["distance_method"], "dom_projected")
        self.assertEqual(summary["geometry_source"], "dom_projection_coordinate")
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_ground_distance_prefilter_unit_test -v
```

Expected: FAIL/ERROR because `filter_stereo_pair_keypoints_by_projected_distance` is not defined.

- [ ] **Step 3: Implement projected-distance helper**

In `examples/controlnet_construct/ground_distance_prefilter.py`, add the alias near `GroundLookup`:

```python
ProjectedLookup = Callable[[float, float], tuple[float, float] | None]
SUPPORTED_PRE_RANSAC_DISTANCE_METHODS = ("dom-projected", "ori-spherical")
DEFAULT_PRE_RANSAC_DISTANCE_METHOD = "dom-projected"
```

Add this function after `ground_distance_km`:

```python
def projected_distance_km(
    left_x: float,
    left_y: float,
    right_x: float,
    right_y: float,
) -> float:
    """Return planar projected-coordinate distance in kilometers."""
    left_projected_x = _validate_finite_coordinate(left_x, "left_x")
    left_projected_y = _validate_finite_coordinate(left_y, "left_y")
    right_projected_x = _validate_finite_coordinate(right_x, "right_x")
    right_projected_y = _validate_finite_coordinate(right_y, "right_y")
    return math.hypot(right_projected_x - left_projected_x, right_projected_y - left_projected_y) / 1000.0
```

Add this function after `filter_stereo_pair_keypoints_by_ground_distance`:

```python
def filter_stereo_pair_keypoints_by_projected_distance(
    left_key_file: KeypointFile,
    right_key_file: KeypointFile,
    *,
    left_projected_lookup: ProjectedLookup,
    right_projected_lookup: ProjectedLookup,
    threshold_km: float,
    lookup_failure_policy: str = "drop",
    left_dom: str | Path | None = None,
    right_dom: str | Path | None = None,
) -> tuple[KeypointFile, KeypointFile, dict[str, object], tuple[int, ...]]:
    if len(left_key_file.points) != len(right_key_file.points):
        raise ValueError("Left and right keypoint files must contain the same number of points.")

    threshold = _validate_threshold(threshold_km)
    policy = _validate_lookup_failure_policy(lookup_failure_policy)

    if threshold == 0.0:
        summary = _disabled_summary(
            left_key_file,
            right_key_file,
            threshold,
            policy,
            LUNAR_MEAN_RADIUS_KM,
            space="dom",
            geometry_source="dom_projection_coordinate",
        )
        summary["distance_method"] = "dom_projected"
        if left_dom is not None:
            summary["left_dom"] = str(left_dom)
        if right_dom is not None:
            summary["right_dom"] = str(right_dom)
        return left_key_file, right_key_file, summary, tuple(range(len(left_key_file.points)))

    retained_left_points: list[Keypoint] = []
    retained_right_points: list[Keypoint] = []
    retained_indices: list[int] = []
    distances: list[float] = []
    dropped_ground_distance_count = 0
    ground_lookup_failure_count = 0

    for index, (left_point, right_point) in enumerate(zip(left_key_file.points, right_key_file.points, strict=True)):
        left_projected = left_projected_lookup(left_point.sample, left_point.line)
        right_projected = right_projected_lookup(right_point.sample, right_point.line)
        if left_projected is None or right_projected is None:
            ground_lookup_failure_count += 1
            if policy == "keep":
                retained_left_points.append(left_point)
                retained_right_points.append(right_point)
                retained_indices.append(index)
            continue

        distance = projected_distance_km(left_projected[0], left_projected[1], right_projected[0], right_projected[1])
        distances.append(distance)
        if distance > threshold:
            dropped_ground_distance_count += 1
            continue
        retained_left_points.append(left_point)
        retained_right_points.append(right_point)
        retained_indices.append(index)

    retained_count = len(retained_left_points)
    distance_summary = _distance_summary(distances)
    summary: dict[str, object] = {
        "applied": True,
        "already_prefiltered": False,
        "status": "filtered",
        "distance_method": "dom_projected",
        "space": "dom",
        "geometry_source": "dom_projection_coordinate",
        "threshold_km": threshold,
        "lookup_failure_policy": policy,
        "input_count": len(left_key_file.points),
        "retained_count": retained_count,
        "dropped_count": len(left_key_file.points) - retained_count,
        "dropped_ground_distance_count": dropped_ground_distance_count,
        "ground_lookup_failure_count": ground_lookup_failure_count,
        "distance_summary_km": distance_summary,
        "max_ground_distance_km": distance_summary["max"],
    }
    if left_dom is not None:
        summary["left_dom"] = str(left_dom)
    if right_dom is not None:
        summary["right_dom"] = str(right_dom)

    return (
        KeypointFile(left_key_file.image_width, left_key_file.image_height, tuple(retained_left_points)),
        KeypointFile(right_key_file.image_width, right_key_file.image_height, tuple(retained_right_points)),
        summary,
        tuple(retained_indices),
    )
```

Update `__all__`:

```python
    "DEFAULT_PRE_RANSAC_DISTANCE_METHOD",
    "ProjectedLookup",
    "SUPPORTED_PRE_RANSAC_DISTANCE_METHODS",
    "filter_stereo_pair_keypoints_by_projected_distance",
    "projected_distance_km",
```

- [ ] **Step 4: Run tests and verify they pass**

Run the same unittest command from Step 2.

Expected: PASS for all ground-distance prefilter tests.

- [ ] **Step 5: Commit**

```bash
git add examples/controlnet_construct/ground_distance_prefilter.py tests/unitTest/controlnet_construct_ground_distance_prefilter_unit_test.py
git commit -m "feat: add projected distance prefilter helper"
```

---

### Task 2: Switch DOM Wrapper to Projection Coordinates

**Files:**
- Modify: `examples/controlnet_construct/ground_distance_prefilter.py`
- Modify: `tests/unitTest/controlnet_construct_ground_distance_prefilter_unit_test.py`

- [ ] **Step 1: Write failing DOM wrapper tests**

Add this fake projection class near `FakeGroundMap`:

```python
class FakeProjection:
    instances = []

    def __init__(self, cube) -> None:
        self.cube = cube
        FakeProjection.instances.append(self)

    def set_world(self, sample: float, line: float) -> bool:
        return sample != 99.0

    def to_projection_x(self, sample: float) -> float:
        return float(sample) * 1000.0

    def to_projection_y(self, line: float) -> float:
        return float(line) * 1000.0
```

Change `fake_ip` to include `ProjectionFactory`:

```python
FakeProjectionFactory = type(
    "ProjectionFactory",
    (),
    {"create_from_cube": staticmethod(lambda cube: FakeProjection(cube))},
)
fake_ip = type(
    "FakeIsisPybind",
    (),
    {
        "Cube": FakeCube,
        "UniversalGroundMap": FakeUniversalGroundMap,
        "ProjectionFactory": FakeProjectionFactory,
    },
)
```

In `setUp`, clear projections:

```python
        FakeProjection.instances.clear()
```

Replace assertions in `test_dom_wrapper_uses_projection_first_and_writes_summary`:

```python
            self.assertEqual(summary["space"], "dom")
            self.assertEqual(summary["geometry_source"], "dom_projection_coordinate")
            self.assertEqual(summary["distance_method"], "dom_projected")
            self.assertEqual(summary["retained_count"], 0)
            self.assertEqual(summary["left_dom"], "left_dom.cub")
            self.assertEqual(summary["right_dom"], "right_dom.cub")
            self.assertEqual(len(FakeProjection.instances), 2)
            self.assertEqual(FakeGroundMap.instances, [])
            self.assertEqual([cube.closed for cube in FakeCube.instances], [True, True])
```

Replace assertions in `test_dom_wrapper_disabled_threshold_keeps_summary_identity`:

```python
            self.assertFalse(summary["applied"])
            self.assertEqual(summary["space"], "dom")
            self.assertEqual(summary["geometry_source"], "dom_projection_coordinate")
            self.assertEqual(summary["distance_method"], "dom_projected")
            self.assertEqual(summary["left_dom"], "left_dom.cub")
            self.assertEqual(summary["right_dom"], "right_dom.cub")
            self.assertEqual([cube.closed for cube in FakeCube.instances], [True, True])
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_ground_distance_prefilter_unit_test -v
```

Expected: FAIL because `filter_dom_key_files_by_ground_distance` still reports `dom_projection_set_image` and uses UniversalGroundMap.

- [ ] **Step 3: Implement DOM projection lookup wrapper**

In `examples/controlnet_construct/ground_distance_prefilter.py`, add after `_lookup_from_ground_map`:

```python
def _open_dom_projection(cube_path: str | Path):
    bootstrap_runtime_environment()
    import isis_pybind as ip

    cube = ip.Cube()
    try:
        cube.open(str(cube_path), "r")
        projection = ip.ProjectionFactory.create_from_cube(cube)
        return cube, projection
    except Exception:
        if cube.is_open():
            cube.close()
        raise


def _lookup_from_dom_projection(projection) -> ProjectedLookup:
    def lookup(sample: float, line: float) -> tuple[float, float] | None:
        if hasattr(projection, "set_world") and not projection.set_world(float(sample), float(line)):
            return None
        projected_x = float(projection.to_projection_x(float(sample)))
        projected_y = float(projection.to_projection_y(float(line)))
        if not (math.isfinite(projected_x) and math.isfinite(projected_y)):
            return None
        return projected_x, projected_y

    return lookup
```

Replace `filter_dom_key_files_by_ground_distance` with:

```python
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
    del lunar_radius_km, dom_band
    left_cube = None
    right_cube = None
    try:
        left_cube, left_projection = _open_dom_projection(left_dom_cube_path)
        right_cube, right_projection = _open_dom_projection(right_dom_cube_path)
        left_key_file = read_key_file(left_input)
        right_key_file = read_key_file(right_input)
        filtered_left, filtered_right, summary, _retained_indices = filter_stereo_pair_keypoints_by_projected_distance(
            left_key_file,
            right_key_file,
            left_projected_lookup=_lookup_from_dom_projection(left_projection),
            right_projected_lookup=_lookup_from_dom_projection(right_projection),
            threshold_km=threshold_km,
            lookup_failure_policy=lookup_failure_policy,
            left_dom=left_dom_cube_path,
            right_dom=right_dom_cube_path,
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
    finally:
        if left_cube is not None and left_cube.is_open():
            left_cube.close()
        if right_cube is not None and right_cube.is_open():
            right_cube.close()
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_ground_distance_prefilter_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/controlnet_construct/ground_distance_prefilter.py tests/unitTest/controlnet_construct_ground_distance_prefilter_unit_test.py
git commit -m "feat: use dom projection coordinates for distance prefilter"
```

---

### Task 3: Add RANSAC Model Selection

**Files:**
- Create: `tests/unitTest/stereo_ransac_model_unit_test.py`
- Modify: `examples/image_match/stereo_ransac.py`
- Modify: `examples/controlnet_construct/stereo_ransac.py`

- [ ] **Step 1: Write failing RANSAC model tests**

Create `tests/unitTest/stereo_ransac_model_unit_test.py`:

```python
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from image_match.keypoints import Keypoint, KeypointFile
from image_match import stereo_ransac


def _key_file(count: int) -> KeypointFile:
    return KeypointFile(100, 100, tuple(Keypoint(float(i), float(i + 1)) for i in range(count)))


class StereoRansacModelTest(unittest.TestCase):
    def test_affine_partial_calls_estimate_affine_partial_2d(self) -> None:
        left_key = _key_file(4)
        right_key = _key_file(4)
        mask = np.asarray([[1], [0], [1], [1]], dtype=np.uint8)

        with mock.patch.object(stereo_ransac.cv2, "estimateAffinePartial2D", return_value=(np.eye(2, 3), mask)) as affine_partial:
            filtered_left, filtered_right, summary = stereo_ransac.filter_stereo_pair_keypoints_with_ransac(
                left_key,
                right_key,
                ransac_model="affine-partial",
                ransac_coordinate_space="dom_pixel",
                ransac_reproj_threshold=10.0,
            )

        affine_partial.assert_called_once()
        self.assertEqual(len(filtered_left.points), 3)
        self.assertEqual(len(filtered_right.points), 3)
        self.assertEqual(summary["model"], "affine-partial")
        self.assertEqual(summary["coordinate_space"], "dom_pixel")
        self.assertEqual(summary["matrix_type"], "affine_2x3")
        self.assertEqual(summary["retained_count"], 3)
        self.assertEqual(summary["dropped_count"], 1)

    def test_affine_calls_estimate_affine_2d(self) -> None:
        left_key = _key_file(4)
        right_key = _key_file(4)
        mask = np.asarray([[1], [1], [0], [1]], dtype=np.uint8)

        with mock.patch.object(stereo_ransac.cv2, "estimateAffine2D", return_value=(np.eye(2, 3), mask)) as affine:
            _filtered_left, _filtered_right, summary = stereo_ransac.filter_stereo_pair_keypoints_with_ransac(
                left_key,
                right_key,
                ransac_model="affine",
            )

        affine.assert_called_once()
        self.assertEqual(summary["model"], "affine")
        self.assertEqual(summary["matrix_type"], "affine_2x3")
        self.assertEqual(summary["retained_count"], 3)

    def test_homography_keeps_legacy_find_homography_path(self) -> None:
        left_key = _key_file(4)
        right_key = _key_file(4)
        mask = np.asarray([[1], [1], [1], [0]], dtype=np.uint8)

        with mock.patch.object(stereo_ransac.cv2, "findHomography", return_value=(np.eye(3), mask)) as homography:
            _filtered_left, _filtered_right, summary = stereo_ransac.filter_stereo_pair_keypoints_with_ransac(
                left_key,
                right_key,
                ransac_model="homography",
                ransac_reproj_threshold=3.0,
            )

        homography.assert_called_once()
        self.assertEqual(summary["model"], "homography")
        self.assertEqual(summary["matrix_type"], "homography_3x3")
        self.assertEqual(summary["homography_matrix"], np.eye(3).tolist())
        self.assertEqual(summary["retained_count"], 3)

    def test_insufficient_points_for_affine_partial_keeps_all_points(self) -> None:
        left_key = _key_file(1)
        right_key = _key_file(1)

        filtered_left, filtered_right, summary = stereo_ransac.filter_stereo_pair_keypoints_with_ransac(
            left_key,
            right_key,
            ransac_model="affine-partial",
        )

        self.assertEqual(filtered_left.points, left_key.points)
        self.assertEqual(filtered_right.points, right_key.points)
        self.assertFalse(summary["applied"])
        self.assertEqual(summary["status"], "skipped_insufficient_points")
        self.assertEqual(summary["skipped_reason"], "insufficient_points")
        self.assertEqual(summary["retained_count"], 1)

    def test_invalid_ransac_model_raises_actionable_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "ransac_model must be one of"):
            stereo_ransac.filter_stereo_pair_keypoints_with_ransac(
                _key_file(4),
                _key_file(4),
                ransac_model="projective",
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python -m unittest tests.unitTest.stereo_ransac_model_unit_test -v
```

Expected: FAIL because `ransac_model` and `ransac_coordinate_space` are unsupported.

- [ ] **Step 3: Implement model selection in `examples/image_match/stereo_ransac.py`**

At the top after imports, add:

```python
DEFAULT_RANSAC_MODEL = "affine-partial"
DEFAULT_RANSAC_REPROJ_THRESHOLD = 10.0
SUPPORTED_RANSAC_MODELS = ("affine-partial", "affine", "homography")
```

Add:

```python
def _normalize_ransac_model(model: str) -> str:
    normalized = str(model).strip().lower()
    if normalized not in SUPPORTED_RANSAC_MODELS:
        raise ValueError("ransac_model must be one of: affine-partial, affine, homography.")
    return normalized
```

Extend `_build_ransac_summary` parameters with:

```python
    model: str,
    coordinate_space: str,
    matrix: list[list[float]] | None,
    matrix_type: str | None,
    skipped_reason: str | None = None,
```

And add these fields to the returned dict:

```python
        "model": model,
        "coordinate_space": coordinate_space,
        "matrix": matrix,
        "matrix_type": matrix_type,
        **({"skipped_reason": skipped_reason} if skipped_reason is not None else {}),
```

Change `filter_stereo_pair_keypoints_with_ransac` signature defaults:

```python
    ransac_model: str = DEFAULT_RANSAC_MODEL,
    ransac_coordinate_space: str = "dom_pixel",
    ransac_reproj_threshold: float = DEFAULT_RANSAC_REPROJ_THRESHOLD,
```

Before `input_count`, add:

```python
    normalized_model = _normalize_ransac_model(ransac_model)
    threshold = float(ransac_reproj_threshold)
    if not np.isfinite(threshold) or threshold <= 0.0:
        raise ValueError("ransac_reproj_threshold must be finite and positive.")
```

Use this model setup before calling OpenCV:

```python
    minimum_points = 4 if normalized_model == "homography" else 2
    if input_count < minimum_points:
        summary = _build_ransac_summary(
            applied=False,
            status="skipped_insufficient_points",
            mode=normalized_mode,
            model=normalized_model,
            coordinate_space=ransac_coordinate_space,
            input_count=input_count,
            retained_count=input_count,
            dropped_count=0,
            opencv_inlier_count=input_count,
            opencv_outlier_count=0,
            retained_soft_outlier_count=0,
            soft_outlier_original_indices=[],
            retained_soft_outlier_positions=[],
            reproj_threshold=threshold,
            confidence=ransac_confidence,
            max_iters=ransac_max_iters,
            loose_keep_pixel_threshold=loose_keep_pixel_threshold,
            matrix=None,
            matrix_type=None,
            homography_matrix=None,
            skipped_reason="insufficient_points",
        )
        return left_key_file, right_key_file, summary
```

Replace the single `cv2.findHomography` call with:

```python
    if normalized_model == "affine-partial":
        model_matrix, mask = cv2.estimateAffinePartial2D(
            left_points.reshape(-1, 2),
            right_points.reshape(-1, 2),
            method=cv2.RANSAC,
            ransacReprojThreshold=threshold,
            confidence=float(ransac_confidence),
            maxIters=int(ransac_max_iters),
        )
        matrix_type = "affine_2x3"
        homography_matrix = None
    elif normalized_model == "affine":
        model_matrix, mask = cv2.estimateAffine2D(
            left_points.reshape(-1, 2),
            right_points.reshape(-1, 2),
            method=cv2.RANSAC,
            ransacReprojThreshold=threshold,
            confidence=float(ransac_confidence),
            maxIters=int(ransac_max_iters),
        )
        matrix_type = "affine_2x3"
        homography_matrix = None
    else:
        model_matrix, mask = cv2.findHomography(
            left_points,
            right_points,
            cv2.RANSAC,
            ransacReprojThreshold=threshold,
            confidence=float(ransac_confidence),
            maxIters=int(ransac_max_iters),
        )
        matrix_type = "homography_3x3"
        homography_matrix = None if model_matrix is None else model_matrix.tolist()
```

Replace the failure summary status with:

```python
            status=f"skipped_{normalized_model.replace('-', '_')}_failed",
            model=normalized_model,
            coordinate_space=ransac_coordinate_space,
            matrix=None,
            matrix_type=None,
            homography_matrix=None,
            skipped_reason="model_estimation_failed",
```

For loose soft-outlier projection, branch by model:

```python
    if normalized_mode == "loose":
        if normalized_model == "homography":
            projected_right = cv2.perspectiveTransform(left_points, model_matrix).reshape(-1, 2)
        else:
            left_xy = left_points.reshape(-1, 2)
            projected_right = (left_xy @ model_matrix[:, :2].T) + model_matrix[:, 2]
        right_coordinates = right_points.reshape(-1, 2)
```

For the final filtered summary, pass:

```python
        model=normalized_model,
        coordinate_space=ransac_coordinate_space,
        matrix=model_matrix.tolist(),
        matrix_type=matrix_type,
        homography_matrix=homography_matrix,
```

Add new parameters to `filter_stereo_pair_key_files_with_ransac` and forward them:

```python
    ransac_model: str = DEFAULT_RANSAC_MODEL,
    ransac_coordinate_space: str = "dom_pixel",
```

Forward:

```python
        ransac_model=ransac_model,
        ransac_coordinate_space=ransac_coordinate_space,
```

Update `__all__`:

```python
    "DEFAULT_RANSAC_MODEL",
    "DEFAULT_RANSAC_REPROJ_THRESHOLD",
    "SUPPORTED_RANSAC_MODELS",
```

- [ ] **Step 4: Copy the synced implementation to ControlNet helper**

Run:

```bash
cp examples/image_match/stereo_ransac.py examples/controlnet_construct/stereo_ransac.py
```

Then edit only the metadata header in `examples/controlnet_construct/stereo_ransac.py` if the file already carries module-specific history comments. Do not change function bodies after copying.

- [ ] **Step 5: Run tests and verify they pass**

Run:

```bash
python -m unittest tests.unitTest.stereo_ransac_model_unit_test -v
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Expected: model unit tests PASS. Existing matching tests may fail where they assert the old default threshold or old summary fields; update those tests in Task 4.

- [ ] **Step 6: Commit**

```bash
git add examples/image_match/stereo_ransac.py examples/controlnet_construct/stereo_ransac.py tests/unitTest/stereo_ransac_model_unit_test.py
git commit -m "feat: support affine ransac models"
```

---

### Task 4: Wire RANSAC Defaults Through Image Match

**Files:**
- Modify: `examples/image_match/image_match.py`
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Write failing image-match forwarding tests**

In `tests/unitTest/controlnet_construct_matching_unit_test.py`, add this test near the existing visualization RANSAC tests:

```python
    def test_match_dom_pair_to_key_files_visualization_forwards_affine_partial_ransac_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            left_dom = tmp_path / "left.cub"
            right_dom = tmp_path / "right.cub"
            left_key = tmp_path / "left.key"
            right_key = tmp_path / "right.key"
            metadata = tmp_path / "metadata.json"
            left_dom.write_text("left")
            right_dom.write_text("right")

            raw_left = KeypointFile(100, 100, (Keypoint(1.0, 1.0), Keypoint(2.0, 2.0)))
            raw_right = KeypointFile(100, 100, (Keypoint(1.0, 2.0), Keypoint(2.0, 3.0)))
            ransac_summary = {
                "applied": False,
                "status": "skipped_insufficient_points",
                "mode": "loose",
                "model": "affine-partial",
                "coordinate_space": "dom_pixel",
                "input_count": 2,
                "retained_count": 2,
                "dropped_count": 0,
                "opencv_inlier_count": 2,
                "opencv_outlier_count": 0,
                "retained_soft_outlier_count": 0,
                "soft_outlier_original_indices": [],
                "retained_soft_outlier_positions": [],
                "reproj_threshold": 10.0,
                "confidence": 0.995,
                "max_iters": 5000,
                "loose_keep_pixel_threshold": 1.0,
                "matrix": None,
                "matrix_type": None,
                "homography_matrix": None,
                "skipped_reason": "insufficient_points",
            }

            with mock.patch.object(image_match_module, "match_dom_pair", return_value=(raw_left, raw_right, {
                "status": "matched",
                "reason": "test",
                "point_count": 2,
                "tile_count": 1,
                "tile_count_before_preindex_filter": 1,
                "tile_count_after_preindex_filter": 1,
                "preindexed_skipped_tile_count": 0,
                "full_resolution_skipped_tile_count": 0,
                "matched_tile_count": 1,
                "skipped_tile_count": 0,
                "tile_validity_prefilter_enabled": False,
                "tile_validity_cache_dir": None,
                "tile_validity_cell_width": 512,
                "tile_validity_cell_height": 512,
                "tile_block_alignment_mode": "off",
                "block_alignment_reason": "off",
                "tile_block_alignment": {},
                "tile_validity_skip_reasons": {},
                "left_tile_validity_index": None,
                "right_tile_validity_index": None,
                "tiling_used": False,
                "valid_pixel_percent_threshold": 0.0,
                "invalid_pixel_radius": 1,
                "matcher": {},
                "parallel_cpu_requested": False,
                "num_worker_parallel_cpu": 1,
                "parallel_cpu_used": False,
                "parallel_cpu_backend": "serial",
                "parallel_cpu_worker_count": 0,
                "tile_match_backend": {},
                "low_resolution_offset": {},
                "low_resolution_matching_target_long_edge": None,
                "resolved_low_resolution_level": None,
                "adaptive_routing": {"enabled": False},
                "preparation": {"status": "prepared"},
            })), mock.patch.object(image_match_module, "filter_dom_key_files_by_ground_distance", return_value={
                "applied": False,
                "already_prefiltered": False,
                "status": "disabled",
                "threshold_km": 0.0,
                "lookup_failure_policy": "drop",
                "distance_method": "dom_projected",
                "space": "dom",
                "geometry_source": "dom_projection_coordinate",
            }), mock.patch.object(
                image_match_module,
                "filter_stereo_pair_keypoints_with_ransac",
                return_value=(raw_left, raw_right, ransac_summary),
            ) as ransac_mock, mock.patch.object(
                image_match_module,
                "write_stereo_pair_match_visualization",
                return_value={"status": "written", "output_path": str(tmp_path / "viz.png"), "point_count": 2},
            ):
                result = image_match_module.match_dom_pair_to_key_files(
                    left_dom,
                    right_dom,
                    left_key,
                    right_key,
                    metadata_output=metadata,
                    write_match_visualization=True,
                    pre_ransac_max_ground_distance_km=0.0,
                )

            ransac_mock.assert_called_once()
            self.assertEqual(ransac_mock.call_args.kwargs["ransac_model"], "affine-partial")
            self.assertEqual(ransac_mock.call_args.kwargs["ransac_reproj_threshold"], 10.0)
            self.assertEqual(result["match_visualization"]["ransac"]["coordinate_space"], "dom_pixel")
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingTest.test_match_dom_pair_to_key_files_visualization_forwards_affine_partial_ransac_model -v
```

Expected: FAIL because `filter_stereo_pair_keypoints_with_ransac` is called without `ransac_model`, or default threshold is still 3.0.

- [ ] **Step 3: Add constants and validators in `image_match.py`**

Near RANSAC visualization constants, replace threshold default and add:

```python
DEFAULT_MATCH_VISUALIZATION_RANSAC_THRESHOLD = _stereo_ransac.DEFAULT_RANSAC_REPROJ_THRESHOLD
DEFAULT_RANSAC_MODEL = _stereo_ransac.DEFAULT_RANSAC_MODEL
SUPPORTED_RANSAC_MODELS = _stereo_ransac.SUPPORTED_RANSAC_MODELS
DEFAULT_PRE_RANSAC_DISTANCE_METHOD = "dom-projected"
SUPPORTED_PRE_RANSAC_DISTANCE_METHODS = ("dom-projected", "ori-spherical")
```

Add validators near `_validate_pre_ransac_ground_lookup_failure_policy`:

```python
def _parse_pre_ransac_distance_method(value: object) -> str:
    normalized = str(value).strip().lower().replace("_", "-")
    if normalized not in SUPPORTED_PRE_RANSAC_DISTANCE_METHODS:
        raise ValueError("pre_ransac_distance_method must be one of: dom-projected, ori-spherical.")
    return normalized


def _parse_ransac_model(value: object) -> str:
    normalized = str(value).strip().lower().replace("_", "-")
    if normalized not in SUPPORTED_RANSAC_MODELS:
        raise ValueError("ransac_model must be one of: affine-partial, affine, homography.")
    return normalized
```

Add config coercion entries to `load_image_match_defaults_from_config` mapping:

```python
        _config_value(
            "pre_ransac_distance_method",
            ("pre_ransac_distance_method", "preRansacDistanceMethod", "PreRansacDistanceMethod"),
            _parse_pre_ransac_distance_method,
        ),
        _config_value(
            "ransac_model",
            ("ransac_model", "ransacModel", "RansacModel"),
            _parse_ransac_model,
        ),
```

- [ ] **Step 4: Forward model into wrappers and visualization**

Extend wrapper functions in `image_match.py`:

```python
def filter_stereo_pair_keypoints_with_ransac(
    left_key_file: KeypointFile,
    right_key_file: KeypointFile,
    *,
    ransac_model: str = DEFAULT_RANSAC_MODEL,
    ransac_coordinate_space: str = "dom_pixel",
    ransac_reproj_threshold: float = DEFAULT_MATCH_VISUALIZATION_RANSAC_THRESHOLD,
    ransac_confidence: float = 0.995,
    ransac_max_iters: int = 5000,
    ransac_mode: str = "loose",
    loose_keep_pixel_threshold: float = 1.0,
) -> tuple[KeypointFile, KeypointFile, dict[str, object]]:
    return _stereo_ransac.filter_stereo_pair_keypoints_with_ransac(
        left_key_file,
        right_key_file,
        ransac_model=ransac_model,
        ransac_coordinate_space=ransac_coordinate_space,
        ransac_reproj_threshold=ransac_reproj_threshold,
        ransac_confidence=ransac_confidence,
        ransac_max_iters=ransac_max_iters,
        ransac_mode=ransac_mode,
        loose_keep_pixel_threshold=loose_keep_pixel_threshold,
    )
```

Add `ransac_model` to `_keypoints_for_match_visualization` and pass it through:

```python
    ransac_model: str = DEFAULT_RANSAC_MODEL,
    ransac_coordinate_space: str = "dom_pixel",
```

In the disabled summary returned by `_keypoints_for_match_visualization`, include:

```python
                "model": ransac_model,
                "coordinate_space": ransac_coordinate_space,
```

Forward in the active call:

```python
        ransac_model=ransac_model,
        ransac_coordinate_space=ransac_coordinate_space,
```

Add `ransac_model: str = DEFAULT_RANSAC_MODEL` to `match_dom_pair_to_key_files` and pass to both `_keypoints_for_match_visualization` calls:

```python
                ransac_model=ransac_model,
                ransac_coordinate_space="dom_pixel",
```

- [ ] **Step 5: Add CLI flags**

In `build_argument_parser`, add:

```python
    parser.add_argument("--pre-ransac-distance-method", type=_parse_pre_ransac_distance_method, default=DEFAULT_PRE_RANSAC_DISTANCE_METHOD, help="Pre-RANSAC distance filter method: dom-projected or ori-spherical. Default: dom-projected.")
    parser.add_argument("--ransac-model", type=_parse_ransac_model, default=DEFAULT_RANSAC_MODEL, help="RANSAC model for match visualization/control filtering: affine-partial, affine, or homography. Default: affine-partial.")
```

In `main`, forward:

```python
        pre_ransac_distance_method=args.pre_ransac_distance_method,
        ransac_model=args.ransac_model,
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingTest.test_match_dom_pair_to_key_files_visualization_forwards_affine_partial_ransac_model -v
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
python -m unittest tests.unitTest.test_match_preset_config -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add examples/image_match/image_match.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: default image match ransac to affine partial"
```

---

### Task 5: Add ORI DOM-Projected Validation Surface

**Files:**
- Modify: `examples/image_match/image_match.py`
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Write failing ORI validation tests**

Add these tests near existing ORI matching tests in `tests/unitTest/controlnet_construct_matching_unit_test.py`:

```python
    def test_match_ori_pair_default_dom_projected_requires_corresponding_doms(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            left_key = tmp_path / "left.key"
            right_key = tmp_path / "right.key"

            with self.assertRaisesRegex(ValueError, "left_corresponding_dom and right_corresponding_dom are required"):
                image_match_module.match_ori_pair_to_key_files(
                    "left_ori.cub",
                    "right_ori.cub",
                    left_key,
                    right_key,
                    write_match_visualization=False,
                    pre_ransac_distance_method="dom-projected",
                )

    def test_match_ori_pair_legacy_spherical_does_not_require_corresponding_doms(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            left_key = tmp_path / "left.key"
            right_key = tmp_path / "right.key"
            raw_left = KeypointFile(100, 100, (Keypoint(1.0, 1.0),))
            raw_right = KeypointFile(100, 100, (Keypoint(1.0, 1.0),))

            with mock.patch.object(image_match_module, "match_ori_pair", return_value=(raw_left, raw_right, {
                "status": "matched",
                "reason": "test",
                "point_count": 1,
                "matcher": {},
                "preparation": {"status": "prepared"},
            })), mock.patch.object(image_match_module, "filter_ori_key_files_by_ground_distance", return_value={
                "applied": False,
                "already_prefiltered": False,
                "status": "disabled",
                "distance_method": "ori_spherical",
                "space": "ori",
                "geometry_source": "ori_camera_set_image",
                "threshold_km": 0.0,
                "lookup_failure_policy": "drop",
            }):
                result = image_match_module.match_ori_pair_to_key_files(
                    "left_ori.cub",
                    "right_ori.cub",
                    left_key,
                    right_key,
                    write_match_visualization=False,
                    pre_ransac_distance_method="ori-spherical",
                    pre_ransac_max_ground_distance_km=0.0,
                )

            self.assertEqual(result["pre_ransac_ground_distance_filter"]["distance_method"], "ori_spherical")
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingTest.test_match_ori_pair_default_dom_projected_requires_corresponding_doms -v
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingTest.test_match_ori_pair_legacy_spherical_does_not_require_corresponding_doms -v
```

Expected: FAIL because `match_ori_pair_to_key_files` has no `pre_ransac_distance_method` or DOM args.

- [ ] **Step 3: Add ORI DOM parameters and validation**

In `match_ori_pair_to_key_files` signature, add:

```python
    left_corresponding_dom: str | Path | None = None,
    right_corresponding_dom: str | Path | None = None,
    pre_ransac_distance_method: str = DEFAULT_PRE_RANSAC_DISTANCE_METHOD,
    ransac_model: str = DEFAULT_RANSAC_MODEL,
```

Near the start of the function, add:

```python
    resolved_distance_method = _parse_pre_ransac_distance_method(pre_ransac_distance_method)
    resolved_ransac_model = _parse_ransac_model(ransac_model)
    if resolved_distance_method == "dom-projected":
        if left_corresponding_dom is None or right_corresponding_dom is None:
            raise ValueError("left_corresponding_dom and right_corresponding_dom are required for dom-projected ORI filtering.")
        if not Path(left_corresponding_dom).exists():
            raise ValueError(f"left_corresponding_dom does not exist: {left_corresponding_dom}")
        if not Path(right_corresponding_dom).exists():
            raise ValueError(f"right_corresponding_dom does not exist: {right_corresponding_dom}")
```

For this task, keep ORI DOM-projected implementation intentionally blocked after validation:

```python
        raise ValueError("dom-projected ORI filtering requires ORI-to-DOM coordinate mapping; implement Task 6 before running this mode.")
```

Do not add this blocking raise if Task 6 is implemented immediately in the same working tree.

For legacy spherical branch, ensure disabled summary includes:

```python
            pre_ransac_ground_distance_filter["distance_method"] = "ori_spherical"
```

- [ ] **Step 4: Add CLI flags for ORI DOM paths**

In `build_argument_parser`, add:

```python
    parser.add_argument("--left-corresponding-dom", default=None, help="DOM cube corresponding to the left ORI input; required for dom-projected ORI filtering.")
    parser.add_argument("--right-corresponding-dom", default=None, help="DOM cube corresponding to the right ORI input; required for dom-projected ORI filtering.")
```

Forward to `match_ori_pair_to_key_files` in `main`:

```python
        left_corresponding_dom=args.left_corresponding_dom,
        right_corresponding_dom=args.right_corresponding_dom,
```

- [ ] **Step 5: Run tests**

Run the two tests from Step 2.

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add examples/image_match/image_match.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: require doms for default ori filtering"
```

---

### Task 6: Implement ORI-to-DOM Coordinate Provider

**Files:**
- Modify: `examples/controlnet_construct/ground_distance_prefilter.py`
- Modify: `examples/image_match/image_match.py`
- Modify: `tests/unitTest/controlnet_construct_ground_distance_prefilter_unit_test.py`
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Write failing coordinate-provider tests**

Add this test in `GroundDistancePrefilterTest`:

```python
    def test_filter_ori_key_files_by_dom_projected_distance_uses_camera_then_dom_projection(self) -> None:
        from controlnet_construct.ground_distance_prefilter import filter_ori_key_files_by_dom_projected_distance

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            left_input = tmp_path / "left.key"
            right_input = tmp_path / "right.key"
            left_output = tmp_path / "left.filtered.key"
            right_output = tmp_path / "right.filtered.key"
            write_key_file(left_input, KeypointFile(100, 100, (Keypoint(1.0, 1.0), Keypoint(2.0, 1.0))))
            write_key_file(right_input, KeypointFile(100, 100, (Keypoint(1.0, 1.0), Keypoint(5.0, 1.0))))

            with (
                mock.patch.object(ground_distance_module, "bootstrap_runtime_environment", lambda: None),
                mock.patch.dict(sys.modules, {"isis_pybind": fake_ip}),
            ):
                summary = filter_ori_key_files_by_dom_projected_distance(
                    left_input,
                    right_input,
                    left_output,
                    right_output,
                    "left_ori.cub",
                    "right_ori.cub",
                    "left_dom.cub",
                    "right_dom.cub",
                    threshold_km=1.0,
                )

            self.assertEqual(summary["distance_method"], "dom_projected")
            self.assertEqual(summary["space"], "dom")
            self.assertEqual(summary["geometry_source"], "ori_camera_to_dom_projection_coordinate")
            self.assertEqual(summary["retained_indices"], [0])
            self.assertEqual(len(read_key_file(left_output).points), 1)
            self.assertEqual(len(read_key_file(right_output).points), 1)
```

For this test to work, update `FakeGroundMap` methods:

```python
    def universal_latitude(self) -> float:
        if self.sample in FakeGroundMap.non_finite_samples:
            return float("nan")
        return float(self.sample)

    def universal_longitude(self) -> float:
        return float(self.line)
```

Add to `FakeProjection`:

```python
    def set_universal_ground(self, latitude: float, longitude: float) -> bool:
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        return self.latitude != 99.0

    def x_coord(self) -> float:
        return self.latitude * 1000.0

    def y_coord(self) -> float:
        return self.longitude * 1000.0
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_ground_distance_prefilter_unit_test.GroundDistancePrefilterTest.test_filter_ori_key_files_by_dom_projected_distance_uses_camera_then_dom_projection -v
```

Expected: FAIL because `filter_ori_key_files_by_dom_projected_distance` is not defined.

- [ ] **Step 3: Implement ORI DOM-projected helper**

In `examples/controlnet_construct/ground_distance_prefilter.py`, add:

```python
def _lookup_from_ori_camera_to_dom_projection(camera_ground_map, dom_projection) -> ProjectedLookup:
    def lookup(sample: float, line: float) -> tuple[float, float] | None:
        if not camera_ground_map.set_image(float(sample), float(line)):
            return None
        latitude = float(camera_ground_map.universal_latitude())
        longitude = float(camera_ground_map.universal_longitude())
        if not (math.isfinite(latitude) and math.isfinite(longitude)):
            return None
        if not dom_projection.set_universal_ground(latitude, longitude):
            return None
        projected_x = float(dom_projection.x_coord())
        projected_y = float(dom_projection.y_coord())
        if not (math.isfinite(projected_x) and math.isfinite(projected_y)):
            return None
        return projected_x, projected_y

    return lookup


def filter_ori_key_files_by_dom_projected_distance(
    left_input: str | Path,
    right_input: str | Path,
    left_output: str | Path,
    right_output: str | Path,
    left_cube_path: str | Path,
    right_cube_path: str | Path,
    left_dom_cube_path: str | Path,
    right_dom_cube_path: str | Path,
    *,
    threshold_km: float,
    lookup_failure_policy: str = "drop",
    band: int = 1,
) -> dict[str, object]:
    left_ori_cube = right_ori_cube = left_dom_cube = right_dom_cube = None
    try:
        left_ori_cube, left_camera_ground_map = _open_ground_map(left_cube_path, band=band, priority_name="CameraFirst")
        right_ori_cube, right_camera_ground_map = _open_ground_map(right_cube_path, band=band, priority_name="CameraFirst")
        left_dom_cube, left_dom_projection = _open_dom_projection(left_dom_cube_path)
        right_dom_cube, right_dom_projection = _open_dom_projection(right_dom_cube_path)
        left_key_file = read_key_file(left_input)
        right_key_file = read_key_file(right_input)
        filtered_left, filtered_right, summary, retained_indices = filter_stereo_pair_keypoints_by_projected_distance(
            left_key_file,
            right_key_file,
            left_projected_lookup=_lookup_from_ori_camera_to_dom_projection(left_camera_ground_map, left_dom_projection),
            right_projected_lookup=_lookup_from_ori_camera_to_dom_projection(right_camera_ground_map, right_dom_projection),
            threshold_km=threshold_km,
            lookup_failure_policy=lookup_failure_policy,
            left_dom=left_dom_cube_path,
            right_dom=right_dom_cube_path,
        )
        summary["geometry_source"] = "ori_camera_to_dom_projection_coordinate"
        summary["left_ori"] = str(left_cube_path)
        summary["right_ori"] = str(right_cube_path)
        summary["retained_indices"] = list(retained_indices)
        write_key_file(left_output, filtered_left)
        write_key_file(right_output, filtered_right)
        return {
            **summary,
            "left_input": str(left_input),
            "right_input": str(right_input),
            "left_output": str(left_output),
            "right_output": str(right_output),
        }
    finally:
        for cube in (left_ori_cube, right_ori_cube, left_dom_cube, right_dom_cube):
            if cube is not None and cube.is_open():
                cube.close()
```

Update `__all__`:

```python
    "filter_ori_key_files_by_dom_projected_distance",
```

- [ ] **Step 4: Use helper in `match_ori_pair_to_key_files`**

Import fallback near current ground-distance imports in `image_match.py`:

```python
        filter_ori_key_files_by_dom_projected_distance,
```

In the fallback block, define:

```python
    def filter_ori_key_files_by_dom_projected_distance(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("controlnet_construct.ground_distance_prefilter is required for ORI DOM-projected filtering")
```

Replace the Task 5 blocking raise with a call:

```python
            pre_ransac_ground_distance_filter = filter_ori_key_files_by_dom_projected_distance(
                left_output_key,
                right_output_key,
                left_output_key,
                right_output_key,
                left_cube_path,
                right_cube_path,
                left_corresponding_dom,
                right_corresponding_dom,
                threshold_km=pre_ransac_ground_distance_threshold,
                lookup_failure_policy=pre_ransac_ground_lookup_failure_policy,
                band=band,
            )
```

Keep the existing `filter_ori_key_files_by_ground_distance` call only inside:

```python
        elif resolved_distance_method == "ori-spherical":
```

- [ ] **Step 5: Run tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_ground_distance_prefilter_unit_test -v
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add examples/controlnet_construct/ground_distance_prefilter.py examples/image_match/image_match.py tests/unitTest/controlnet_construct_ground_distance_prefilter_unit_test.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: filter ori matches in dom projected coordinates"
```

---

### Task 7: Wire ControlNet RANSAC and Distance Method

**Files:**
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Write failing ControlNet forwarding test**

In `tests/unitTest/controlnet_construct_pipeline_unit_test.py`, add or extend a `controlnet_stereopair` test with this assertion pattern:

```python
    def test_from_dom_forwards_affine_partial_ransac_model_and_dom_projected_distance(self):
        import controlnet_construct.controlnet_stereopair as stereo_pair

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            left_key = tmp_path / "left.key"
            right_key = tmp_path / "right.key"
            left_dom = tmp_path / "left_dom.cub"
            right_dom = tmp_path / "right_dom.cub"
            left_ori = tmp_path / "left_ori.cub"
            right_ori = tmp_path / "right_ori.cub"
            output_net = tmp_path / "pair.net"
            for path in (left_key, right_key, left_dom, right_dom, left_ori, right_ori):
                path.write_text("fixture")

            with mock.patch.object(stereo_pair, "merge_stereo_pair_key_files", return_value={
                "input_count": 4,
                "unique_count": 4,
                "duplicate_count": 0,
                "hash_strategy": "rounded_sample_line",
                "hash_coordinate_fields": ("sample", "line"),
                "hash_rounding_decimals": 2,
            }), mock.patch.object(stereo_pair, "filter_dom_key_files_by_ground_distance", return_value={
                "applied": True,
                "already_prefiltered": False,
                "status": "filtered",
                "distance_method": "dom_projected",
                "space": "dom",
                "geometry_source": "dom_projection_coordinate",
                "threshold_km": 1.0,
                "lookup_failure_policy": "drop",
                "input_count": 4,
                "retained_count": 4,
                "dropped_count": 0,
            }) as distance_mock, mock.patch.object(stereo_pair, "filter_stereo_pair_key_files_with_ransac", return_value={
                "applied": False,
                "status": "skipped_insufficient_points",
                "model": "affine-partial",
                "coordinate_space": "dom_pixel",
                "input_count": 4,
                "retained_count": 4,
                "dropped_count": 0,
                "mode": "loose",
            }) as ransac_mock, mock.patch.object(stereo_pair, "dom_keys_to_original_keys", return_value={
                "left_output_key": str(tmp_path / "left_ori.key"),
                "right_output_key": str(tmp_path / "right_ori.key"),
            }), mock.patch.object(stereo_pair, "build_controlnet_for_stereo_pair", return_value={"status": "written"}):
                result = stereo_pair.build_controlnet_for_dom_stereo_pair(
                    left_key,
                    right_key,
                    left_dom,
                    right_dom,
                    left_ori,
                    right_ori,
                    {"NetworkId": "test"},
                    output_net,
                    ransac_model="affine-partial",
                    pre_ransac_distance_method="dom-projected",
                )

            distance_mock.assert_called_once()
            self.assertEqual(ransac_mock.call_args.kwargs["ransac_model"], "affine-partial")
            self.assertEqual(ransac_mock.call_args.kwargs["ransac_coordinate_space"], "dom_pixel")
            self.assertEqual(result["ransac"]["model"], "affine-partial")
            self.assertEqual(result["pre_ransac_ground_distance_filter"]["distance_method"], "dom_projected")
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: FAIL because `build_controlnet_for_dom_stereo_pair` does not accept `ransac_model` or `pre_ransac_distance_method`.

- [ ] **Step 3: Add ControlNet parameters and defaults**

In `examples/controlnet_construct/controlnet_stereopair.py`, add constants near existing default imports:

```python
DEFAULT_PRE_RANSAC_DISTANCE_METHOD = "dom-projected"
SUPPORTED_PRE_RANSAC_DISTANCE_METHODS = ("dom-projected", "ori-spherical")
DEFAULT_RANSAC_MODEL = "affine-partial"
SUPPORTED_RANSAC_MODELS = ("affine-partial", "affine", "homography")
DEFAULT_RANSAC_REPROJ_THRESHOLD = 10.0
```

Add validators:

```python
def _normalize_pre_ransac_distance_method(value: str) -> str:
    normalized = str(value).strip().lower().replace("_", "-")
    if normalized not in SUPPORTED_PRE_RANSAC_DISTANCE_METHODS:
        raise ValueError("pre_ransac_distance_method must be one of: dom-projected, ori-spherical.")
    return normalized


def _normalize_ransac_model(value: str) -> str:
    normalized = str(value).strip().lower().replace("_", "-")
    if normalized not in SUPPORTED_RANSAC_MODELS:
        raise ValueError("ransac_model must be one of: affine-partial, affine, homography.")
    return normalized
```

Add to signatures for `build_controlnet_for_dom_stereo_pair`, `build_controlnet_for_dom_match_stereo_pair`, and `build_controlnets_for_dom_overlap_list`:

```python
    ransac_model: str = DEFAULT_RANSAC_MODEL,
    pre_ransac_distance_method: str = DEFAULT_PRE_RANSAC_DISTANCE_METHOD,
```

Change default `ransac_reproj_threshold` in these signatures to:

```python
    ransac_reproj_threshold: float = DEFAULT_RANSAC_REPROJ_THRESHOLD,
```

At the start of `build_controlnet_for_dom_stereo_pair`, resolve:

```python
    resolved_ransac_model = _normalize_ransac_model(ransac_model)
    resolved_distance_method = _normalize_pre_ransac_distance_method(pre_ransac_distance_method)
    if resolved_distance_method != "dom-projected":
        raise ValueError("from-dom ControlNet filtering supports dom-projected distance only.")
```

Pass to RANSAC call:

```python
        ransac_model=resolved_ransac_model,
        ransac_coordinate_space="dom_pixel",
```

In disabled distance summary, include:

```python
            "distance_method": "dom_projected",
            "geometry_source": "dom_projection_coordinate",
```

In upstream skip logic, skip only if:

```python
        upstream_ground_filter.get("distance_method") == "dom_projected"
        and upstream_ground_filter.get("geometry_source") == "dom_projection_coordinate"
```

If upstream metadata exists but does not match default DOM-projected fields, continue to apply the local distance filter.

- [ ] **Step 4: Add CLI args and forwarding**

Add to the parser helpers that currently add RANSAC/pre-RANSAC flags:

```python
    parser.add_argument("--pre-ransac-distance-method", choices=SUPPORTED_PRE_RANSAC_DISTANCE_METHODS, default=DEFAULT_PRE_RANSAC_DISTANCE_METHOD, help="Distance method before RANSAC. Default: dom-projected.")
    parser.add_argument("--ransac-model", choices=SUPPORTED_RANSAC_MODELS, default=DEFAULT_RANSAC_MODEL, help="RANSAC model. Default: affine-partial.")
```

Forward `args.ransac_model` and `args.pre_ransac_distance_method` in each main branch where `ransac_reproj_threshold` and `pre_ransac_max_ground_distance_km` are already forwarded.

- [ ] **Step 5: Run tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test -v
```

Expected: ControlNet tests PASS. Parameter catalog may still fail until Task 8.

- [ ] **Step 6: Commit**

```bash
git add examples/controlnet_construct/controlnet_stereopair.py tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: wire affine ransac through controlnet"
```

---

### Task 8: Forward New Flags Through Catalog and Batch Wrappers

**Files:**
- Modify: `examples/controlnet_construct/parameter_catalog.py`
- Modify: `examples/controlnet_construct/run_image_match_batch_example.sh`
- Modify: `examples/controlnet_construct/experiments/match_original_gsd_lro_dom_pairs_large.py`
- Modify: `tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Write failing parameter catalog assertions**

In `tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py`, add assertions to the catalog coverage test:

```python
        self.assertIn("pre_ransac_distance_method", parameter_names)
        self.assertIn("ransac_model", parameter_names)
```

Add this specific default test:

```python
    def test_new_filter_policy_parameters_have_expected_defaults(self):
        by_name = {parameter.name: parameter for parameter in parameter_catalog.PARAMETERS}
        self.assertEqual(by_name["pre_ransac_distance_method"].default, "dom-projected")
        self.assertEqual(by_name["pre_ransac_distance_method"].allowed_values, ("dom-projected", "ori-spherical"))
        self.assertEqual(by_name["ransac_model"].default, "affine-partial")
        self.assertEqual(by_name["ransac_model"].allowed_values, ("affine-partial", "affine", "homography"))
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test -v
```

Expected: FAIL because the new parameters are absent.

- [ ] **Step 3: Add catalog entries**

In `examples/controlnet_construct/parameter_catalog.py`, add constants:

```python
DEFAULT_PRE_RANSAC_DISTANCE_METHOD = "dom-projected"
SUPPORTED_PRE_RANSAC_DISTANCE_METHODS = ("dom-projected", "ori-spherical")
DEFAULT_RANSAC_MODEL = "affine-partial"
SUPPORTED_RANSAC_MODELS = ("affine-partial", "affine", "homography")
```

Add to `RUN_PIPELINE_CLI_PARAMETER_NAMES`:

```python
        "pre_ransac_distance_method",
        "ransac_model",
```

Add entries near existing pre-RANSAC specs:

```python
    _spec("pre_ransac_distance_method", "matching", config_path=_image_match_path("pre_ransac_distance_method"), default=DEFAULT_PRE_RANSAC_DISTANCE_METHOD, allowed_values=SUPPORTED_PRE_RANSAC_DISTANCE_METHODS, entrypoints=_PRE_RANSAC_GROUND_FILTER_ENTRYPOINTS, help="Pre-RANSAC distance method; default dom-projected uses DOM projection coordinates."),
    _spec("ransac_model", "matching", config_path=_image_match_path("ransac_model"), default=DEFAULT_RANSAC_MODEL, allowed_values=SUPPORTED_RANSAC_MODELS, entrypoints=_PRE_RANSAC_GROUND_FILTER_ENTRYPOINTS, help="RANSAC model used after distance filtering."),
```

- [ ] **Step 4: Forward shell wrapper flags**

In `examples/controlnet_construct/run_image_match_batch_example.sh`, add defaults near existing pre-RANSAC defaults:

```bash
pre_ransac_distance_method="dom-projected"
ransac_model="affine-partial"
```

Add usage lines:

```bash
  --pre-ransac-distance-method dom-projected|ori-spherical
  --ransac-model affine-partial|affine|homography
```

Add parser cases:

```bash
      --pre-ransac-distance-method)
        [[ $# -ge 2 ]] || die "missing value for --pre-ransac-distance-method"
        case "$2" in
          dom-projected|ori-spherical) pre_ransac_distance_method="$2" ;;
          *) die "--pre-ransac-distance-method must be dom-projected or ori-spherical" ;;
        esac
        shift 2
        ;;
      --ransac-model)
        [[ $# -ge 2 ]] || die "missing value for --ransac-model"
        case "$2" in
          affine-partial|affine|homography) ransac_model="$2" ;;
          *) die "--ransac-model must be affine-partial, affine, or homography" ;;
        esac
        shift 2
        ;;
```

Forward to every `image_match.py` command:

```bash
      --pre-ransac-distance-method "$pre_ransac_distance_method"
      --ransac-model "$ransac_model"
```

- [ ] **Step 5: Forward Python experiment flags**

In `examples/controlnet_construct/experiments/match_original_gsd_lro_dom_pairs_large.py`, add argparse flags:

```python
    parser.add_argument("--pre-ransac-distance-method", choices=("dom-projected", "ori-spherical"), default="dom-projected")
    parser.add_argument("--ransac-model", choices=("affine-partial", "affine", "homography"), default="affine-partial")
```

Where the script builds image-match command args, add:

```python
        "--pre-ransac-distance-method",
        args.pre_ransac_distance_method,
        "--ransac-model",
        args.ransac_model,
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test -v
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add examples/controlnet_construct/parameter_catalog.py examples/controlnet_construct/run_image_match_batch_example.sh examples/controlnet_construct/experiments/match_original_gsd_lro_dom_pairs_large.py tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: forward dom projected ransac policy flags"
```

---

### Task 9: Update RANSAC Rerender and Reporting Labels

**Files:**
- Modify: `examples/controlnet_construct/experiments/rerender_ransac_match_visualizations.py`
- Modify: `examples/controlnet_construct/experiments/plot_lro_polar_match_method_comparison.py`

- [ ] **Step 1: Add CLI and summary fields for rerender script**

In `examples/controlnet_construct/experiments/rerender_ransac_match_visualizations.py`, add parser argument:

```python
    parser.add_argument("--ransac-model", choices=("affine-partial", "affine", "homography"), default="affine-partial")
```

Forward to `filter_stereo_pair_keypoints_with_ransac`:

```python
        ransac_model=ransac_model,
        ransac_coordinate_space="dom_pixel",
```

Add columns to each row:

```python
        "ransac_model": ransac_summary.get("model"),
        "ransac_coordinate_space": ransac_summary.get("coordinate_space"),
        "ransac_matrix_type": ransac_summary.get("matrix_type"),
```

Add these names to the CSV field list.

- [ ] **Step 2: Update figure source labeling**

In `examples/controlnet_construct/experiments/plot_lro_polar_match_method_comparison.py`, when pair-level rows are built, add:

```python
            "ransac_model": row.get("ransac_model", "affine-partial"),
            "ransac_coordinate_space": row.get("ransac_coordinate_space", "dom_pixel"),
            "raw_matches": int(row["raw_match_count"]),
            "distance_retained": int(row["raw_match_count"]),
            "affine_partial_retained": int(row["ransac_retained_count"]) if row.get("ransac_model", "affine-partial") == "affine-partial" else None,
            "homography_retained": int(row["ransac_retained_count"]) if row.get("ransac_model") == "homography" else None,
```

Keep existing retained-match fields unchanged so old consumers still work.

- [ ] **Step 3: Run script help checks**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
python examples/controlnet_construct/experiments/rerender_ransac_match_visualizations.py --help | rg -- '--ransac-model'
python examples/controlnet_construct/experiments/plot_lro_polar_match_method_comparison.py --help
```

Expected: first command prints `--ransac-model`; second command exits 0.

- [ ] **Step 4: Commit**

```bash
git add examples/controlnet_construct/experiments/rerender_ransac_match_visualizations.py examples/controlnet_construct/experiments/plot_lro_polar_match_method_comparison.py
git commit -m "feat: report ransac model in benchmark outputs"
```

---

### Task 10: Final Verification

**Files:**
- No new files unless failures require fixes.

- [ ] **Step 1: Run smoke import**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tests/smoke_import.py
```

Expected:

```text
smoke import ok
```

- [ ] **Step 2: Run focused unit suite**

Run:

```bash
python -m unittest \
  tests.unitTest.controlnet_construct_ground_distance_prefilter_unit_test \
  tests.unitTest.stereo_ransac_model_unit_test \
  tests.unitTest.controlnet_construct_matching_unit_test \
  tests.unitTest.controlnet_construct_pipeline_unit_test \
  tests.unitTest.controlnet_construct_parameter_catalog_unit_test \
  -v
```

Expected: PASS. If existing tests require exact old `homography_matrix` behavior, update only those assertions to accept the new `matrix` fields while still checking `homography_matrix` for `model == "homography"`.

- [ ] **Step 3: Run broader focused suite used by this project**

Run:

```bash
python -m unittest \
  tests.unitTest.controlnet_construct_pipeline_unit_test \
  tests.unitTest.image_match_adaptive_routing_unit_test \
  tests.unitTest.image_match_deep_manifest_unit_test \
  tests.unitTest.image_match_tile_illumination_unit_test \
  -v
```

Expected: PASS with the existing expected skip count.

- [ ] **Step 4: Check working tree**

Run:

```bash
git status --short
```

Expected: only intentional files from this plan are modified or untracked. Do not stage `.gitignore` or `print.prt`.

- [ ] **Step 5: Commit final verification note if fixes were needed**

If Step 2 or Step 3 required small compatibility fixes, commit them:

```bash
git add examples tests
git commit -m "test: verify dom projected affine ransac policy"
```

If no fixes were needed after the previous commits, do not create an empty commit.

---

## Self-Review

- Spec coverage:
  - DOM-projected default distance: Tasks 1, 2, 4, 7, 8.
  - ORI default requires corresponding DOMs: Tasks 5 and 6.
  - Legacy ORI spherical path remains explicit: Task 5.
  - Affine-partial default RANSAC with 10 px threshold: Tasks 3, 4, 7, 9.
  - Homography remains available: Task 3.
  - Insufficient points keep all points: Task 3.
  - Metadata fields for distance and RANSAC model/space: Tasks 1, 3, 4, 7, 9.
  - Wrapper/config forwarding: Tasks 4, 7, 8.
  - ControlNet upstream prefilter skip only for default DOM-projected metadata: Task 7.
- Placeholder scan:
  - The plan contains no deferred-work markers or vague implementation instructions.
- Type consistency:
  - Distance method CLI spelling is `dom-projected|ori-spherical`.
  - Metadata spelling is `dom_projected|ori_spherical`.
  - RANSAC model spelling is `affine-partial|affine|homography`.
  - RANSAC coordinate space is `dom_pixel`.
