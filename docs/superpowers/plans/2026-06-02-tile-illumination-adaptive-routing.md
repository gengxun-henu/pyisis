# Tile Illumination Adaptive Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build tile-level physical illumination adaptive routing for LRO NAC DOM matching, using DOM representative points projected into each DOM's source camera cube to select SIFT+FLANN, SIFT+LightGlue, SuperPoint+LightGlue, or LoFTR per tile.

**Architecture:** Keep the new physical-illumination logic in focused `examples/image_match/` modules, then let `image_match.py` and `controlnet_construct` consume the resulting sidecar/manifest metadata. Use injectable geometry adapters for unit tests and a PyISIS adapter only at the boundary. Preserve prior-only routing: one matcher is selected from texture/keypoint plus physical illumination evidence, with no post-match fallback cascade.

**Tech Stack:** Python 3.12, PyISIS/ISIS camera geometry, NumPy, OpenCV SIFT, existing `unittest` suite, existing deep-match manifest handoff for the `deep-learning` conda environment.

---

## File Structure

- Create `examples/image_match/tile_illumination.py`
  - Dataclasses and pure helpers for representative points, physical illumination samples, pair summaries, angular differences, and route metadata serialization.
- Create `examples/image_match/tile_illumination_geometry.py`
  - Pixel-availability checks, deterministic candidate ordering, bounded representative-point search, and PyISIS DOM-to-ground-to-source-camera solar geometry extraction.
- Modify `examples/image_match/adaptive_routing.py`
  - Add tile-level physical route decisions and a pure route function that maps texture/keypoint/illumination evidence to one matcher.
- Modify `examples/image_match/tile_matching.py`
  - Add optional per-tile route metadata to `TileMatchTask`, serialize it, and preserve it through worker/import paths.
- Modify `examples/image_match/deep_match_manifest.py`
  - Preserve tile route and illumination diagnostics in each deep task record.
- Modify `examples/image_match/image_match.py`
  - Add source-cube metadata input, compute tile illumination before adaptive tile matching, partition tile tasks by selected matcher, export grouped deep manifests, and attach report sidecars.
- Modify `examples/controlnet_construct/run_pipeline_example.sh`
  - Forward source-cube metadata CSV/options and report deep manifest grouping instructions without changing the pipeline ownership boundary.
- Modify `examples/controlnet_construct/experiments/summarize_lro_polar_adaptive_routing_benchmark.py`
  - Summarize route distributions, projectable tile counts, skipped illumination reasons, and RANSAC-retained success.
- Modify tests:
  - `tests/unitTest/image_match_tile_illumination_unit_test.py`
  - `tests/unitTest/image_match_adaptive_routing_unit_test.py`
  - `tests/unitTest/image_match_deep_manifest_unit_test.py`
  - `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

Do not modify, delete, stage, or commit `.gitignore` or `print.prt`.

## Environment

Use this setup before running validation:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
export MPLBACKEND=Agg
export MPLCONFIGDIR=/tmp/matplotlib-pyisis-benchmark
```

Deep-learning execution is separate:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate deep-learning
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8
```

---

### Task 1: Add Tile Illumination Data Models

**Files:**
- Create: `examples/image_match/tile_illumination.py`
- Test: `tests/unitTest/image_match_tile_illumination_unit_test.py`

- [ ] **Step 1: Write failing model and math tests**

Add this new test file:

```python
from __future__ import annotations

import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from image_match.tile_illumination import (
    RepresentativePoint,
    TileIlluminationPair,
    TileIlluminationSample,
    TileWindowMetadata,
    angular_difference_degrees,
    illumination_pair_to_payload,
    summarize_tile_illumination_pairs,
)


class ImageMatchTileIlluminationUnitTest(unittest.TestCase):
    def test_angular_difference_handles_wraparound(self):
        self.assertEqual(angular_difference_degrees(359.0, 1.0), 2.0)
        self.assertEqual(angular_difference_degrees(10.0, 350.0), 20.0)

    def test_pair_payload_contains_elevation_from_incidence(self):
        point = RepresentativePoint(
            status="center_projectable",
            selection_reason="center pixel projected to source camera",
            local_x_0_based=5,
            local_y_0_based=6,
            dom_sample_1_based=11.0,
            dom_line_1_based=12.0,
            pixel_available=True,
            radiometric_valid_for_matching=False,
            source_projectable=True,
            failure_reason=None,
        )
        sample = TileIlluminationSample(
            side="left",
            dom_path="left_dom.cub",
            dom_source_cube="left_source.cub",
            upstream_source_cube=None,
            tile_index=3,
            tile_window_0_based=TileWindowMetadata(start_x=0, start_y=0, width=32, height=32),
            representative_point=point,
            latitude=-88.5,
            longitude=123.0,
            source_sample_1_based=21.5,
            source_line_1_based=22.5,
            sun_azimuth_degrees=359.0,
            incidence_angle_degrees=87.0,
            solar_elevation_degrees=3.0,
        )
        pair = TileIlluminationPair.from_samples(tile_index=3, left=sample, right=sample)

        payload = illumination_pair_to_payload(pair)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["left"]["solar_elevation_degrees"], 3.0)
        self.assertEqual(payload["azimuth_difference_degrees"], 0.0)

    def test_summary_counts_projectable_and_skipped_tiles(self):
        failed_point = RepresentativePoint(
            status="no_projectable_pixel",
            selection_reason="no pixel projected to source camera",
            local_x_0_based=None,
            local_y_0_based=None,
            dom_sample_1_based=None,
            dom_line_1_based=None,
            pixel_available=False,
            radiometric_valid_for_matching=None,
            source_projectable=False,
            failure_reason="no_projectable_pixel",
        )
        failed_sample = TileIlluminationSample.failed(
            side="left",
            dom_path="left_dom.cub",
            dom_source_cube="left_source.cub",
            upstream_source_cube=None,
            tile_index=1,
            tile_window_0_based=TileWindowMetadata(start_x=0, start_y=0, width=16, height=16),
            representative_point=failed_point,
        )
        summary = summarize_tile_illumination_pairs((
            TileIlluminationPair.from_samples(tile_index=1, left=failed_sample, right=failed_sample),
        ))

        self.assertEqual(summary["tile_count"], 1)
        self.assertEqual(summary["projectable_tile_count"], 0)
        self.assertEqual(summary["skipped_tile_count"], 1)
        self.assertEqual(summary["skip_reasons"]["both_failed"], 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.unitTest.image_match_tile_illumination_unit_test -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'image_match.tile_illumination'`.

- [ ] **Step 3: Add the model implementation**

Create `examples/image_match/tile_illumination.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable


def _finite_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    resolved = float(value)
    return resolved if math.isfinite(resolved) else None


def angular_difference_degrees(left: float | None, right: float | None) -> float | None:
    left_value = _finite_or_none(left)
    right_value = _finite_or_none(right)
    if left_value is None or right_value is None:
        return None
    return abs((left_value - right_value + 180.0) % 360.0 - 180.0)


def illumination_difference_score(
    *,
    azimuth_difference_degrees: float | None,
    incidence_difference_degrees: float | None,
    elevation_difference_degrees: float | None,
) -> float | None:
    terms: list[float] = []
    if azimuth_difference_degrees is not None:
        terms.append(min(float(azimuth_difference_degrees) / 180.0, 1.0))
    if incidence_difference_degrees is not None:
        terms.append(min(abs(float(incidence_difference_degrees)) / 90.0, 1.0))
    if elevation_difference_degrees is not None:
        terms.append(min(abs(float(elevation_difference_degrees)) / 90.0, 1.0))
    if not terms:
        return None
    return max(0.0, min(1.0, sum(terms) / len(terms)))


@dataclass(frozen=True, slots=True)
class TileWindowMetadata:
    start_x: int
    start_y: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class RepresentativePoint:
    status: str
    selection_reason: str
    local_x_0_based: int | None
    local_y_0_based: int | None
    dom_sample_1_based: float | None
    dom_line_1_based: float | None
    pixel_available: bool
    radiometric_valid_for_matching: bool | None
    source_projectable: bool
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class TileIlluminationSample:
    side: str
    dom_path: str
    dom_source_cube: str
    upstream_source_cube: str | None
    tile_index: int
    tile_window_0_based: TileWindowMetadata
    representative_point: RepresentativePoint
    latitude: float | None
    longitude: float | None
    source_sample_1_based: float | None
    source_line_1_based: float | None
    sun_azimuth_degrees: float | None
    incidence_angle_degrees: float | None
    solar_elevation_degrees: float | None

    @classmethod
    def failed(
        cls,
        *,
        side: str,
        dom_path: str,
        dom_source_cube: str,
        upstream_source_cube: str | None,
        tile_index: int,
        tile_window_0_based: TileWindowMetadata,
        representative_point: RepresentativePoint,
    ) -> "TileIlluminationSample":
        return cls(
            side=side,
            dom_path=dom_path,
            dom_source_cube=dom_source_cube,
            upstream_source_cube=upstream_source_cube,
            tile_index=tile_index,
            tile_window_0_based=tile_window_0_based,
            representative_point=representative_point,
            latitude=None,
            longitude=None,
            source_sample_1_based=None,
            source_line_1_based=None,
            sun_azimuth_degrees=None,
            incidence_angle_degrees=None,
            solar_elevation_degrees=None,
        )


@dataclass(frozen=True, slots=True)
class TileIlluminationPair:
    tile_index: int
    status: str
    left: TileIlluminationSample
    right: TileIlluminationSample
    azimuth_difference_degrees: float | None
    incidence_difference_degrees: float | None
    elevation_difference_degrees: float | None
    illumination_difference_score: float | None

    @classmethod
    def from_samples(
        cls,
        *,
        tile_index: int,
        left: TileIlluminationSample,
        right: TileIlluminationSample,
    ) -> "TileIlluminationPair":
        left_ok = bool(left.representative_point.source_projectable)
        right_ok = bool(right.representative_point.source_projectable)
        if left_ok and right_ok:
            status = "ok"
        elif left_ok:
            status = "right_failed"
        elif right_ok:
            status = "left_failed"
        else:
            status = "both_failed"
        azimuth = angular_difference_degrees(left.sun_azimuth_degrees, right.sun_azimuth_degrees)
        incidence = _abs_difference(left.incidence_angle_degrees, right.incidence_angle_degrees)
        elevation = _abs_difference(left.solar_elevation_degrees, right.solar_elevation_degrees)
        score = illumination_difference_score(
            azimuth_difference_degrees=azimuth,
            incidence_difference_degrees=incidence,
            elevation_difference_degrees=elevation,
        )
        return cls(
            tile_index=tile_index,
            status=status,
            left=left,
            right=right,
            azimuth_difference_degrees=azimuth,
            incidence_difference_degrees=incidence,
            elevation_difference_degrees=elevation,
            illumination_difference_score=score,
        )


def _abs_difference(left: float | None, right: float | None) -> float | None:
    left_value = _finite_or_none(left)
    right_value = _finite_or_none(right)
    if left_value is None or right_value is None:
        return None
    return abs(left_value - right_value)


def illumination_pair_to_payload(pair: TileIlluminationPair) -> dict[str, Any]:
    return asdict(pair)


def summarize_tile_illumination_pairs(pairs: Iterable[TileIlluminationPair]) -> dict[str, Any]:
    resolved_pairs = tuple(pairs)
    skip_reasons: dict[str, int] = {}
    projectable = 0
    scores: list[float] = []
    for pair in resolved_pairs:
        if pair.status == "ok":
            projectable += 1
        else:
            skip_reasons[pair.status] = skip_reasons.get(pair.status, 0) + 1
        if pair.illumination_difference_score is not None:
            scores.append(float(pair.illumination_difference_score))
    return {
        "illumination_granularity": "tile",
        "tile_count": len(resolved_pairs),
        "projectable_tile_count": projectable,
        "skipped_tile_count": len(resolved_pairs) - projectable,
        "skip_reasons": skip_reasons,
        "illumination_difference_score_summary": _summary(scores),
    }


def _summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {
        "count": len(values),
        "min": min(values),
        "mean": sum(values) / len(values),
        "max": max(values),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.unitTest.image_match_tile_illumination_unit_test -v
```

Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add examples/image_match/tile_illumination.py tests/unitTest/image_match_tile_illumination_unit_test.py
git commit -m "feat: add tile illumination data models"
```

---

### Task 2: Add Bounded Representative-Point Geometry

**Files:**
- Create: `examples/image_match/tile_illumination_geometry.py`
- Modify: `tests/unitTest/image_match_tile_illumination_unit_test.py`

- [ ] **Step 1: Add failing representative-point tests**

Append these tests to `ImageMatchTileIlluminationUnitTest`:

```python
    def test_shadowed_pixel_can_be_selected_when_source_projectable(self):
        from image_match.tile_illumination_geometry import select_representative_point

        values = np.full((5, 5), 10.0, dtype=np.float64)
        radiometric_mask = np.ones((5, 5), dtype=bool)
        radiometric_mask[2, 2] = False

        selected = select_representative_point(
            dom_values=values,
            tile_start_x=100,
            tile_start_y=200,
            radiometric_valid_for_matching_mask=radiometric_mask,
            project_source_pixel=lambda sample, line: {
                "latitude": -88.0,
                "longitude": 123.0,
                "source_sample": 11.0,
                "source_line": 12.0,
                "sun_azimuth": 250.0,
                "incidence": 87.5,
            },
        )

        self.assertEqual(selected.representative_point.status, "center_projectable")
        self.assertFalse(selected.representative_point.radiometric_valid_for_matching)
        self.assertEqual(selected.representative_point.dom_sample_1_based, 103.0)
        self.assertEqual(selected.solar_elevation_degrees, 2.5)

    def test_center_projection_failure_uses_nearest_projectable_pixel(self):
        from image_match.tile_illumination_geometry import select_representative_point

        values = np.ones((3, 3), dtype=np.float64)
        calls = []

        def projector(sample, line):
            calls.append((sample, line))
            if (sample, line) == (2.0, 2.0):
                raise RuntimeError("center outside source camera")
            return {
                "latitude": -88.0,
                "longitude": 123.0,
                "source_sample": sample + 10.0,
                "source_line": line + 10.0,
                "sun_azimuth": 180.0,
                "incidence": 80.0,
            }

        selected = select_representative_point(
            dom_values=values,
            tile_start_x=0,
            tile_start_y=0,
            radiometric_valid_for_matching_mask=None,
            project_source_pixel=projector,
        )

        self.assertEqual(selected.representative_point.status, "nearest_projectable_pixel")
        self.assertGreaterEqual(len(calls), 2)

    def test_no_projectable_pixel_reports_failure(self):
        from image_match.tile_illumination_geometry import select_representative_point

        selected = select_representative_point(
            dom_values=np.ones((2, 2), dtype=np.float64),
            tile_start_x=0,
            tile_start_y=0,
            radiometric_valid_for_matching_mask=None,
            project_source_pixel=lambda sample, line: (_ for _ in ()).throw(RuntimeError("not covered")),
        )

        self.assertEqual(selected.representative_point.status, "no_projectable_pixel")
        self.assertEqual(selected.representative_point.failure_reason, "no_projectable_pixel")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.unitTest.image_match_tile_illumination_unit_test -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'image_match.tile_illumination_geometry'`.

- [ ] **Step 3: Add pure representative-point selection**

Create `examples/image_match/tile_illumination_geometry.py`:

```python
from __future__ import annotations

from collections.abc import Callable, Iterator
import math
from pathlib import Path
from typing import Any

import numpy as np

from .tile_illumination import RepresentativePoint, TileIlluminationSample, TileWindowMetadata


ProjectionResult = dict[str, float]


def pixel_available(value: float, *, special_pixel_abs_threshold: float | None = None) -> bool:
    resolved = float(value)
    if not math.isfinite(resolved):
        return False
    if special_pixel_abs_threshold is not None and abs(resolved) >= float(special_pixel_abs_threshold):
        return False
    return True


def representative_candidate_offsets(width: int, height: int) -> Iterator[tuple[int, int]]:
    center_x = width // 2
    center_y = height // 2
    candidates = [
        (x, y)
        for y in range(height)
        for x in range(width)
    ]
    candidates.sort(key=lambda xy: ((xy[0] - center_x) ** 2 + (xy[1] - center_y) ** 2, xy[1], xy[0]))
    yield from candidates


def select_representative_point(
    *,
    dom_values: np.ndarray,
    tile_start_x: int,
    tile_start_y: int,
    radiometric_valid_for_matching_mask: np.ndarray | None,
    project_source_pixel: Callable[[float, float], ProjectionResult],
    side: str = "left",
    dom_path: str = "",
    dom_source_cube: str = "",
    upstream_source_cube: str | None = None,
    tile_index: int = 0,
    special_pixel_abs_threshold: float | None = None,
) -> TileIlluminationSample:
    values = np.asarray(dom_values, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("dom_values must be a 2-D array.")
    height, width = values.shape
    tile_window = TileWindowMetadata(start_x=int(tile_start_x), start_y=int(tile_start_y), width=int(width), height=int(height))
    radiometric_mask = None if radiometric_valid_for_matching_mask is None else np.asarray(radiometric_valid_for_matching_mask, dtype=bool)
    if radiometric_mask is not None and radiometric_mask.shape != values.shape:
        raise ValueError("radiometric_valid_for_matching_mask must match dom_values shape.")

    first_unavailable_reason = "center_pixel_unavailable"
    for local_x, local_y in representative_candidate_offsets(width, height):
        value = float(values[local_y, local_x])
        if not pixel_available(value, special_pixel_abs_threshold=special_pixel_abs_threshold):
            continue
        dom_sample = float(tile_start_x + local_x + 1)
        dom_line = float(tile_start_y + local_y + 1)
        try:
            projected = project_source_pixel(dom_sample, dom_line)
            sun_azimuth = _finite_required(projected["sun_azimuth"], "solar_geometry_missing_or_non_finite")
            incidence = _finite_required(projected["incidence"], "solar_geometry_missing_or_non_finite")
        except Exception as exc:  # noqa: BLE001
            first_unavailable_reason = _projection_failure_reason(exc)
            continue
        status = "center_projectable" if local_x == width // 2 and local_y == height // 2 else "nearest_projectable_pixel"
        representative = RepresentativePoint(
            status=status,
            selection_reason="center pixel projected to source camera" if status == "center_projectable" else "nearest pixel projected to source camera",
            local_x_0_based=int(local_x),
            local_y_0_based=int(local_y),
            dom_sample_1_based=dom_sample,
            dom_line_1_based=dom_line,
            pixel_available=True,
            radiometric_valid_for_matching=(
                None if radiometric_mask is None else bool(radiometric_mask[local_y, local_x])
            ),
            source_projectable=True,
            failure_reason=None,
        )
        return TileIlluminationSample(
            side=side,
            dom_path=dom_path,
            dom_source_cube=dom_source_cube,
            upstream_source_cube=upstream_source_cube,
            tile_index=int(tile_index),
            tile_window_0_based=tile_window,
            representative_point=representative,
            latitude=float(projected["latitude"]),
            longitude=float(projected["longitude"]),
            source_sample_1_based=float(projected["source_sample"]),
            source_line_1_based=float(projected["source_line"]),
            sun_azimuth_degrees=sun_azimuth,
            incidence_angle_degrees=incidence,
            solar_elevation_degrees=90.0 - incidence,
        )

    representative = RepresentativePoint(
        status="no_projectable_pixel",
        selection_reason="no pixel projected to source camera",
        local_x_0_based=None,
        local_y_0_based=None,
        dom_sample_1_based=None,
        dom_line_1_based=None,
        pixel_available=False,
        radiometric_valid_for_matching=None,
        source_projectable=False,
        failure_reason="no_projectable_pixel" if first_unavailable_reason else "center_pixel_unavailable",
    )
    return TileIlluminationSample.failed(
        side=side,
        dom_path=dom_path,
        dom_source_cube=dom_source_cube,
        upstream_source_cube=upstream_source_cube,
        tile_index=int(tile_index),
        tile_window_0_based=tile_window,
        representative_point=representative,
    )


def _finite_required(value: float, reason: str) -> float:
    resolved = float(value)
    if not math.isfinite(resolved):
        raise ValueError(reason)
    return resolved


def _projection_failure_reason(exc: Exception) -> str:
    text = str(exc).lower()
    if "source" in text:
        return "source_ground_map_set_universal_ground_failed"
    if "camera" in text:
        return "source_camera_set_image_failed"
    if "solar" in text:
        return "solar_geometry_missing_or_non_finite"
    return "dom_ground_map_set_image_failed"


def build_pyisis_projector(*, dom_path: str | Path, source_cube_path: str | Path) -> Callable[[float, float], ProjectionResult]:
    from .runtime import bootstrap_runtime_environment

    bootstrap_runtime_environment()
    import isis_pybind as ip

    dom_cube = ip.Cube()
    source_cube = ip.Cube()
    dom_cube.open(str(dom_path), "r")
    source_cube.open(str(source_cube_path), "r")
    dom_ground_map = ip.UniversalGroundMap(dom_cube, ip.UniversalGroundMap.CameraPriority.ProjectionFirst)
    source_ground_map = ip.UniversalGroundMap(source_cube, ip.UniversalGroundMap.CameraPriority.CameraFirst)
    source_camera = source_cube.camera()

    def project(dom_sample: float, dom_line: float) -> ProjectionResult:
        if not dom_ground_map.set_image(float(dom_sample), float(dom_line)):
            raise RuntimeError("dom_ground_map_set_image_failed")
        latitude = float(dom_ground_map.universal_latitude())
        longitude = float(dom_ground_map.universal_longitude())
        if not source_ground_map.set_universal_ground(latitude, longitude):
            raise RuntimeError("source_ground_map_set_universal_ground_failed")
        source_sample = float(source_ground_map.sample())
        source_line = float(source_ground_map.line())
        if not source_camera.set_image(source_sample, source_line):
            raise RuntimeError("source_camera_set_image_failed")
        return {
            "latitude": latitude,
            "longitude": longitude,
            "source_sample": source_sample,
            "source_line": source_line,
            "sun_azimuth": float(source_camera.sun_azimuth()),
            "incidence": float(source_camera.incidence_angle()),
        }

    return project
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.unitTest.image_match_tile_illumination_unit_test -v
```

Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git add examples/image_match/tile_illumination_geometry.py tests/unitTest/image_match_tile_illumination_unit_test.py
git commit -m "feat: select source-projectable tile illumination points"
```

---

### Task 3: Add Source Cube Metadata Resolution

**Files:**
- Modify: `examples/image_match/tile_illumination.py`
- Modify: `tests/unitTest/image_match_tile_illumination_unit_test.py`

- [ ] **Step 1: Add failing metadata resolver test**

Append:

```python
    def test_source_metadata_resolves_reduced_pair_csv(self):
        import tempfile
        from image_match.tile_illumination import load_dom_source_metadata_csv, resolve_dom_source_metadata

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "reduced_selected_pair_paths.csv"
            csv_path.write_text(
                "source_echo_cal_cube,echo_cal_cube,source_dom_cube,dom_cube\n"
                "/full/M123.echo.cal.cub,/reduced/REDUCED_M123.echo.cal.cub,/dom/full_dom_M123.cub,/dom/dom_REDUCED_M123.cub\n",
                encoding="utf-8",
            )

            lookup = load_dom_source_metadata_csv(csv_path)
            metadata = resolve_dom_source_metadata("/dom/dom_REDUCED_M123.cub", lookup)

        self.assertEqual(metadata["dom_source_cube"], "/reduced/REDUCED_M123.echo.cal.cub")
        self.assertEqual(metadata["upstream_source_cube"], "/full/M123.echo.cal.cub")
        self.assertEqual(metadata["dom_source_kind"], "reduced")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.unitTest.image_match_tile_illumination_unit_test.ImageMatchTileIlluminationUnitTest.test_source_metadata_resolves_reduced_pair_csv -v
```

Expected: FAIL with `ImportError` for the new resolver functions.

- [ ] **Step 3: Implement CSV metadata resolver**

Append to `examples/image_match/tile_illumination.py`:

```python
import csv
from pathlib import Path


def _path_key(path: str | Path) -> str:
    return str(Path(path).expanduser())


def load_dom_source_metadata_csv(csv_path: str | Path) -> dict[str, dict[str, str | None]]:
    lookup: dict[str, dict[str, str | None]] = {}
    with Path(csv_path).expanduser().open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            dom_path = row.get("dom_cube") or row.get("dom_path")
            if not dom_path:
                continue
            dom_source_cube = row.get("echo_cal_cube") or row.get("source_cube") or row.get("source_echo_cal_cube")
            upstream_source_cube = row.get("source_echo_cal_cube") or None
            metadata = {
                "dom_path": dom_path,
                "dom_source_cube": dom_source_cube or "",
                "upstream_source_cube": upstream_source_cube,
                "dom_source_kind": "reduced" if dom_source_cube and Path(dom_source_cube).name.startswith("REDUCED_") else "unknown",
            }
            lookup[_path_key(dom_path)] = metadata
            lookup[Path(dom_path).name] = metadata
    return lookup


def resolve_dom_source_metadata(
    dom_path: str | Path,
    lookup: dict[str, dict[str, str | None]] | None,
) -> dict[str, str | None]:
    resolved_lookup = lookup or {}
    key = _path_key(dom_path)
    metadata = resolved_lookup.get(key) or resolved_lookup.get(Path(dom_path).name)
    if metadata is None:
        return {
            "dom_path": str(dom_path),
            "dom_source_cube": "",
            "upstream_source_cube": None,
            "dom_source_kind": "unknown",
        }
    return dict(metadata)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.unitTest.image_match_tile_illumination_unit_test -v
```

Expected: PASS, 7 tests.

- [ ] **Step 5: Commit**

```bash
git add examples/image_match/tile_illumination.py tests/unitTest/image_match_tile_illumination_unit_test.py
git commit -m "feat: resolve DOM source cube metadata"
```

---

### Task 4: Add Tile-Level Prior Router

**Files:**
- Modify: `examples/image_match/adaptive_routing.py`
- Modify: `tests/unitTest/image_match_adaptive_routing_unit_test.py`

- [ ] **Step 1: Write failing routing tests**

Add imports:

```python
    TileRoutingDecision,
    route_matcher_for_tile,
```

Append tests:

```python
    def test_tile_router_uses_flann_for_rich_texture_small_physical_lighting_gap(self):
        decision = route_matcher_for_tile(
            tile_index=2,
            texture_sparseness=0.12,
            lighting_difference_score=0.05,
            texture_probe_keypoint_count_left=250,
            texture_probe_keypoint_count_right=240,
            texture_probe_keypoint_density_left=0.002,
            texture_probe_keypoint_density_right=0.002,
            illumination={"status": "ok", "illumination_difference_score": 0.05},
            adaptive_routing_deep_presets={},
        )

        self.assertIsInstance(decision, TileRoutingDecision)
        self.assertEqual(decision.selected_matcher, "flann")
        self.assertEqual(decision.selected_execution_environment, "asp360_new")
        self.assertTrue(decision.no_post_match_fallback)

    def test_tile_router_uses_loftr_for_low_keypoint_density_hard_rule(self):
        decision = route_matcher_for_tile(
            tile_index=3,
            texture_sparseness=0.25,
            lighting_difference_score=0.10,
            texture_probe_keypoint_count_left=4,
            texture_probe_keypoint_count_right=80,
            texture_probe_keypoint_density_left=1.0e-7,
            texture_probe_keypoint_density_right=1.0e-4,
            illumination={"status": "ok", "illumination_difference_score": 0.10},
            adaptive_routing_deep_presets={"loftr": "examples/controlnet_construct/presets/loftr_default.json"},
        )

        self.assertEqual(decision.selected_matcher, "loftr")
        self.assertEqual(decision.selected_execution_environment, "deep-learning")
        self.assertEqual(decision.deep_match_config_path, "examples/controlnet_construct/presets/loftr_default.json")

    def test_tile_router_uses_superpoint_lightglue_for_weak_non_extreme_texture(self):
        decision = route_matcher_for_tile(
            tile_index=4,
            texture_sparseness=0.62,
            lighting_difference_score=0.30,
            texture_probe_keypoint_count_left=90,
            texture_probe_keypoint_count_right=95,
            texture_probe_keypoint_density_left=2.0e-5,
            texture_probe_keypoint_density_right=2.5e-5,
            illumination={"status": "ok", "illumination_difference_score": 0.30},
            adaptive_routing_deep_presets={"superpoint_lightglue": "examples/controlnet_construct/presets/lightglue_official_superpoint.json"},
        )

        self.assertEqual(decision.selected_matcher, "lightglue")
        self.assertEqual(decision.deep_match_config_path, "examples/controlnet_construct/presets/lightglue_official_superpoint.json")
        self.assertIn("SuperPoint", decision.route_reason)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test.ImageMatchAdaptiveRoutingUnitTest.test_tile_router_uses_flann_for_rich_texture_small_physical_lighting_gap -v
```

Expected: FAIL with `ImportError` for `TileRoutingDecision`.

- [ ] **Step 3: Implement tile route decision**

Add to `examples/image_match/adaptive_routing.py` near `PairRoutingDecision`:

```python
@dataclass(frozen=True, slots=True)
class TileRoutingDecision:
    tile_index: int
    texture_sparseness: float | None
    texture_probe_keypoint_count_left: int | None
    texture_probe_keypoint_count_right: int | None
    texture_probe_keypoint_density_left: float | None
    texture_probe_keypoint_density_right: float | None
    illumination: dict[str, Any]
    selected_matcher: str
    selected_execution_environment: str
    route_reason: str
    route_confidence: float
    no_post_match_fallback: bool
    deep_match_config_path: str | None = None
```

Add this pure function:

```python
def route_matcher_for_tile(
    *,
    tile_index: int,
    texture_sparseness: float | None,
    lighting_difference_score: float | None,
    texture_probe_keypoint_count_left: int | None,
    texture_probe_keypoint_count_right: int | None,
    texture_probe_keypoint_density_left: float | None,
    texture_probe_keypoint_density_right: float | None,
    illumination: dict[str, Any] | None,
    adaptive_routing_deep_presets: dict[str, str] | None = None,
    sparseness_low_threshold: float = 0.35,
    sparseness_high_threshold: float = 0.65,
    lighting_low_threshold: float = 0.20,
    lighting_high_threshold: float = 0.55,
    min_texture_probe_keypoints: int = 12,
    min_texture_probe_keypoint_density: float = 1.0e-5,
) -> TileRoutingDecision:
    preset_map = {
        str(key).strip().lower(): str(value)
        for key, value in (adaptive_routing_deep_presets or {}).items()
        if value not in (None, "")
    }
    counts = [
        value for value in (texture_probe_keypoint_count_left, texture_probe_keypoint_count_right)
        if value is not None
    ]
    densities = [
        value for value in (texture_probe_keypoint_density_left, texture_probe_keypoint_density_right)
        if value is not None
    ]
    low_keypoints = bool(counts) and min(int(value) for value in counts) < int(min_texture_probe_keypoints)
    low_density = bool(densities) and min(float(value) for value in densities) < float(min_texture_probe_keypoint_density)
    sparseness = _finite_float(texture_sparseness)
    lighting = _finite_float(lighting_difference_score)

    if low_keypoints or low_density:
        selected = LOFTR_MATCHER_METHOD
        reason = "texture probe keypoint count or density below hard threshold; route to LoFTR"
        confidence = 0.90
        config = preset_map.get("loftr")
    elif sparseness is not None and sparseness <= sparseness_low_threshold and (lighting is None or lighting <= lighting_low_threshold):
        selected = FLANN_MATCHER_METHOD
        reason = "rich texture and small physical illumination difference; route to SIFT + FLANN"
        confidence = 0.85
        config = None
    elif sparseness is not None and sparseness >= sparseness_high_threshold and lighting is not None and lighting >= lighting_high_threshold:
        selected = LOFTR_MATCHER_METHOD
        reason = "weak texture and large physical illumination difference; route to LoFTR"
        confidence = 0.82
        config = preset_map.get("loftr")
    elif sparseness is not None and sparseness >= 0.58 and (lighting is None or lighting < lighting_high_threshold):
        selected = LIGHTGLUE_MATCHER_METHOD
        reason = "weak-to-moderate texture with non-extreme illumination; route to SuperPoint + LightGlue"
        confidence = 0.65
        config = preset_map.get("superpoint_lightglue") or preset_map.get("lightglue_superpoint") or preset_map.get("lightglue")
    else:
        selected = LIGHTGLUE_MATCHER_METHOD
        reason = "moderate texture or moderate physical illumination difference; route to SIFT + LightGlue"
        confidence = 0.60
        config = preset_map.get("sift_lightglue") or preset_map.get("lightglue")

    environment = "asp360_new" if selected == FLANN_MATCHER_METHOD else "deep-learning"
    return TileRoutingDecision(
        tile_index=int(tile_index),
        texture_sparseness=sparseness,
        texture_probe_keypoint_count_left=texture_probe_keypoint_count_left,
        texture_probe_keypoint_count_right=texture_probe_keypoint_count_right,
        texture_probe_keypoint_density_left=texture_probe_keypoint_density_left,
        texture_probe_keypoint_density_right=texture_probe_keypoint_density_right,
        illumination=dict(illumination or {}),
        selected_matcher=selected,
        selected_execution_environment=environment,
        route_reason=reason,
        route_confidence=confidence,
        no_post_match_fallback=True,
        deep_match_config_path=config,
    )
```

Add both names to `__all__`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/image_match/adaptive_routing.py tests/unitTest/image_match_adaptive_routing_unit_test.py
git commit -m "feat: add tile-level adaptive matcher router"
```

---

### Task 5: Preserve Tile Route Metadata Through Tile Tasks and Deep Manifests

**Files:**
- Modify: `examples/image_match/tile_matching.py`
- Modify: `examples/image_match/deep_match_manifest.py`
- Modify: `tests/unitTest/image_match_deep_manifest_unit_test.py`

- [ ] **Step 1: Add failing serialization test**

Append to `tests/unitTest/image_match_deep_manifest_unit_test.py`:

```python
    def test_deep_manifest_preserves_tile_route_metadata(self):
        from image_match.deep_match_manifest import (
            build_deep_match_pair_manifest,
            deep_match_pair_manifest_from_payload,
            deep_match_pair_manifest_to_payload,
        )
        from image_match.tile_matching import PairedTileWindow, TileMatchTask
        from image_match.tiling import TileWindow

        paired = PairedTileWindow(
            local_window=TileWindow(0, 0, 32, 32),
            left_window=TileWindow(10, 20, 32, 32),
            right_window=TileWindow(30, 40, 32, 32),
        )
        task = TileMatchTask(
            left_dom_path="left.cub",
            right_dom_path="right.cub",
            band=1,
            paired_window=paired,
            minimum_value=None,
            maximum_value=None,
            lower_percent=0.5,
            upper_percent=99.5,
            invalid_values=(),
            special_pixel_abs_threshold=1.0e38,
            min_valid_pixels=4,
            valid_pixel_percent_threshold=0.0,
            invalid_pixel_radius=0,
            ratio_test=0.75,
            matcher_method="lightglue",
            max_features=100,
            sift_octave_layers=3,
            sift_contrast_threshold=0.04,
            sift_edge_threshold=10.0,
            sift_sigma=1.6,
            route_metadata={"tile_index": 7, "selected_matcher": "lightglue", "illumination": {"status": "ok"}},
        )

        manifest = build_deep_match_pair_manifest(
            tasks=[task],
            left_dom_path="left.cub",
            right_dom_path="right.cub",
            matcher_method="lightglue",
            band=1,
            image_space="dom",
            temp_root_dir="/tmp/deep",
            pair_id="pair",
        )
        payload = deep_match_pair_manifest_to_payload(manifest)
        restored = deep_match_pair_manifest_from_payload(payload)

        self.assertEqual(restored.tasks[0].tile_task.route_metadata["tile_index"], 7)
        self.assertEqual(payload["tasks"][0]["route_metadata"]["selected_matcher"], "lightglue")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.unitTest.image_match_deep_manifest_unit_test -v
```

Expected: FAIL with `TypeError: TileMatchTask.__init__() got an unexpected keyword argument 'route_metadata'`.

- [ ] **Step 3: Add `route_metadata` to tile task serialization**

In `examples/image_match/tile_matching.py`, add a field to `TileMatchTask`:

```python
    route_metadata: dict[str, Any] | None = None
```

Add this key in `_tile_task_to_payload`:

```python
        "route_metadata": None if task.route_metadata is None else dict(task.route_metadata),
```

Add this argument in `_tile_task_from_payload`:

```python
        route_metadata=(
            None if payload.get("route_metadata") is None else dict(payload["route_metadata"])
        ),
```

- [ ] **Step 4: Add route metadata to deep task records**

In `examples/image_match/deep_match_manifest.py`, add a field to `DeepMatchTaskRecord`:

```python
    route_metadata: dict[str, Any] | None = None
```

Set it in `build_deep_match_task_record`:

```python
        route_metadata=(
            None if getattr(tile_task, "route_metadata", None) is None else dict(tile_task.route_metadata)
        ),
```

Add it to `deep_match_task_record_to_payload`:

```python
        "route_metadata": None if record.route_metadata is None else dict(record.route_metadata),
```

Add it to `deep_match_task_record_from_payload`:

```python
        route_metadata=(
            None if payload.get("route_metadata") is None else dict(payload["route_metadata"])
        ),
```

- [ ] **Step 5: Run manifest tests**

Run:

```bash
python -m unittest tests.unitTest.image_match_deep_manifest_unit_test -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add examples/image_match/tile_matching.py examples/image_match/deep_match_manifest.py tests/unitTest/image_match_deep_manifest_unit_test.py
git commit -m "feat: preserve tile route metadata in manifests"
```

---

### Task 6: Integrate Physical Illumination Into `image_match.py`

**Files:**
- Modify: `examples/image_match/image_match.py`
- Modify: `tests/unitTest/image_match_adaptive_routing_unit_test.py`

- [ ] **Step 1: Add a failing pure integration test**

Append a test that does not open real cubes:

```python
    def test_build_tile_route_metadata_partitions_classic_and_deep_tiles(self):
        image_match = importlib.import_module("image_match.image_match")
        from image_match.tile_illumination import RepresentativePoint, TileIlluminationPair, TileIlluminationSample, TileWindowMetadata

        point = RepresentativePoint(
            status="center_projectable",
            selection_reason="center pixel projected to source camera",
            local_x_0_based=1,
            local_y_0_based=1,
            dom_sample_1_based=2.0,
            dom_line_1_based=2.0,
            pixel_available=True,
            radiometric_valid_for_matching=True,
            source_projectable=True,
            failure_reason=None,
        )
        sample = TileIlluminationSample(
            side="left",
            dom_path="left.cub",
            dom_source_cube="left_source.cub",
            upstream_source_cube=None,
            tile_index=0,
            tile_window_0_based=TileWindowMetadata(0, 0, 4, 4),
            representative_point=point,
            latitude=-88.0,
            longitude=123.0,
            source_sample_1_based=1.0,
            source_line_1_based=1.0,
            sun_azimuth_degrees=10.0,
            incidence_angle_degrees=87.0,
            solar_elevation_degrees=3.0,
        )
        pair = TileIlluminationPair.from_samples(tile_index=0, left=sample, right=sample)

        metadata = image_match._build_tile_route_metadata(
            tile_index=0,
            illumination_pair=pair,
            texture_sparseness=0.10,
            left_probe={"keypoint_count": 200, "keypoint_density": 0.002},
            right_probe={"keypoint_count": 210, "keypoint_density": 0.002},
            adaptive_routing_deep_presets={},
        )

        self.assertEqual(metadata["selected_matcher"], "flann")
        self.assertEqual(metadata["selected_execution_environment"], "asp360_new")
        self.assertEqual(metadata["illumination"]["status"], "ok")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test.ImageMatchAdaptiveRoutingUnitTest.test_build_tile_route_metadata_partitions_classic_and_deep_tiles -v
```

Expected: FAIL with `AttributeError` for `_build_tile_route_metadata`.

- [ ] **Step 3: Add pure tile route metadata builder**

In `examples/image_match/image_match.py`, import:

```python
from image_match.tile_illumination import illumination_pair_to_payload
```

Add helper near `_resolve_adaptive_route_for_pair`:

```python
def _build_tile_route_metadata(
    *,
    tile_index: int,
    illumination_pair: object,
    texture_sparseness: float | None,
    left_probe: dict[str, object],
    right_probe: dict[str, object],
    adaptive_routing_deep_presets: dict[str, str] | None,
) -> dict[str, object]:
    illumination_payload = illumination_pair_to_payload(illumination_pair)
    decision = route_matcher_for_tile(
        tile_index=tile_index,
        texture_sparseness=texture_sparseness,
        lighting_difference_score=illumination_payload.get("illumination_difference_score"),
        texture_probe_keypoint_count_left=_optional_int(left_probe.get("keypoint_count")),
        texture_probe_keypoint_count_right=_optional_int(right_probe.get("keypoint_count")),
        texture_probe_keypoint_density_left=_optional_float(left_probe.get("keypoint_density")),
        texture_probe_keypoint_density_right=_optional_float(right_probe.get("keypoint_density")),
        illumination=illumination_payload,
        adaptive_routing_deep_presets=adaptive_routing_deep_presets,
    )
    return {
        "tile_index": int(tile_index),
        "selected_matcher": decision.selected_matcher,
        "selected_execution_environment": decision.selected_execution_environment,
        "route_reason": decision.route_reason,
        "route_confidence": decision.route_confidence,
        "no_post_match_fallback": decision.no_post_match_fallback,
        "deep_match_config_path": decision.deep_match_config_path,
        "texture_sparseness": decision.texture_sparseness,
        "texture_probe_keypoint_count_left": decision.texture_probe_keypoint_count_left,
        "texture_probe_keypoint_count_right": decision.texture_probe_keypoint_count_right,
        "texture_probe_keypoint_density_left": decision.texture_probe_keypoint_density_left,
        "texture_probe_keypoint_density_right": decision.texture_probe_keypoint_density_right,
        "illumination": illumination_payload,
    }
```

Add helper functions:

```python
def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    resolved = float(value)
    return resolved if math.isfinite(resolved) else None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Wire helper into tile task construction**

In the tile matching branch of `examples/image_match/image_match.py`, build a list of `route_metadata_by_tile_index` before calling `_build_tile_match_tasks`. For the first implementation, compute illumination metadata for candidate windows only when adaptive routing is enabled and both source cube paths are available. If metadata is missing, keep the existing pair-level route path and mark:

```python
adaptive_routing_summary["tile_illumination"] = {
    "enabled": True,
    "status": "skipped_missing_source_metadata",
}
```

When metadata exists, pass `route_metadata` into each created `TileMatchTask` by replacing the task:

```python
from dataclasses import replace

tile_tasks = [
    replace(task, matcher_method=task.route_metadata["selected_matcher"], route_metadata=task.route_metadata)
    for task in tile_tasks
]
```

For `flann`, run in `asp360_new`; for deep selected matchers, use existing export/import/direct deep paths with grouped manifests.

- [ ] **Step 6: Run focused tests**

Run:

```bash
python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test tests.unitTest.image_match_deep_manifest_unit_test -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add examples/image_match/image_match.py tests/unitTest/image_match_adaptive_routing_unit_test.py
git commit -m "feat: build tile adaptive route metadata"
```

---

### Task 7: Add CLI and Pipeline Source Metadata Handoff

**Files:**
- Modify: `examples/image_match/image_match.py`
- Modify: `examples/controlnet_construct/run_pipeline_example.sh`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Add failing CLI order test**

Add assertions to the pipeline unit test that invokes `image_match.py`:

```python
self.assertIn("--dom-source-metadata-csv", command_text)
self.assertIn("reduced_selected_pair_paths.csv", command_text)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: FAIL because the new flag is not emitted.

- [ ] **Step 3: Add `image_match.py` CLI option**

Add parser argument:

```python
    parser.add_argument(
        "--dom-source-metadata-csv",
        default=None,
        help="CSV mapping DOM cube paths to the source/original camera cubes used to generate them.",
    )
```

Load the mapping near argument normalization:

```python
dom_source_metadata_lookup = (
    load_dom_source_metadata_csv(args.dom_source_metadata_csv)
    if args.dom_source_metadata_csv not in (None, "")
    else {}
)
```

Pass this lookup into the physical illumination helper.

- [ ] **Step 4: Forward from pipeline shell**

In `examples/controlnet_construct/run_pipeline_example.sh`, add variables and argument forwarding:

```bash
DOM_SOURCE_METADATA_CSV=""
```

In option parsing:

```bash
--dom-source-metadata-csv)
  [[ $# -ge 2 ]] || die "missing value for --dom-source-metadata-csv"
  DOM_SOURCE_METADATA_CSV=$2
  shift 2
  ;;
```

When building `match_args`:

```bash
if [[ -n "$DOM_SOURCE_METADATA_CSV" ]]; then
  match_args+=(--dom-source-metadata-csv "$DOM_SOURCE_METADATA_CSV")
fi
```

- [ ] **Step 5: Run pipeline tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add examples/image_match/image_match.py examples/controlnet_construct/run_pipeline_example.sh tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: pass DOM source metadata to image matching"
```

---

### Task 8: Add Reporting Summaries for Tile Illumination Routing

**Files:**
- Modify: `examples/controlnet_construct/experiments/summarize_lro_polar_adaptive_routing_benchmark.py`
- Test: add or extend the matching experiment unit test that covers this summarizer.

- [ ] **Step 1: Add failing summary test**

Create a temporary adaptive metadata JSON containing:

```python
metadata = {
    "adaptive_routing": {
        "tile_illumination": {
            "summary": {
                "tile_count": 2,
                "projectable_tile_count": 1,
                "skipped_tile_count": 1,
                "skip_reasons": {"left_failed": 1},
                "route_distribution_by_tile": {"flann": 1, "loftr": 1},
            }
        },
        "ransac": {
            "raw_match_count": 100,
            "ransac_inlier_count": 60,
        },
    }
}
```

Assert the summary row contains:

```python
self.assertEqual(row["tile_count"], 2)
self.assertEqual(row["projectable_tile_count"], 1)
self.assertEqual(row["ransac_inlier_count"], 60)
self.assertEqual(row["route_distribution_by_tile"]["loftr"], 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: FAIL because tile illumination fields are not summarized.

- [ ] **Step 3: Implement summary extraction**

Add an extraction helper:

```python
def _extract_tile_illumination_summary(metadata: dict[str, object]) -> dict[str, object]:
    adaptive = metadata.get("adaptive_routing")
    if not isinstance(adaptive, dict):
        return {}
    tile_illumination = adaptive.get("tile_illumination")
    if not isinstance(tile_illumination, dict):
        return {}
    summary = tile_illumination.get("summary")
    if not isinstance(summary, dict):
        return {}
    return {
        "tile_count": int(summary.get("tile_count", 0)),
        "projectable_tile_count": int(summary.get("projectable_tile_count", 0)),
        "skipped_tile_count": int(summary.get("skipped_tile_count", 0)),
        "skip_reasons": dict(summary.get("skip_reasons", {})),
        "route_distribution_by_tile": dict(summary.get("route_distribution_by_tile", {})),
    }
```

Merge those fields into each per-pair/per-method row and into the JSON source data for Nature-style figures.

- [ ] **Step 4: Run summary test**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/controlnet_construct/experiments/summarize_lro_polar_adaptive_routing_benchmark.py tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py
git commit -m "feat: summarize tile illumination adaptive routing"
```

---

### Task 9: Run Focused Validation and Real-Data Smoke

**Files:**
- Modify only `.planning/2026-06-02-tile-illumination-adaptive-routing/progress.md` after commands finish.

- [x] **Step 1: Run focused unit tests**

Run:

```bash
python -m unittest \
  tests.unitTest.image_match_tile_illumination_unit_test \
  tests.unitTest.image_match_adaptive_routing_unit_test \
  tests.unitTest.image_match_deep_manifest_unit_test \
  tests.unitTest.controlnet_construct_pipeline_unit_test \
  -v
```

Expected: PASS.

- [x] **Step 2: Run smoke import**

Run:

```bash
python tests/smoke_import.py
```

Expected: PASS and no Qt/matplotlib backend crash.

- [ ] **Step 3: Run one real-data tile illumination dry-run**

Status: deferred. Current runtime metadata records `adaptive_routing.tile_illumination.source_metadata`, but physical tile illumination `summary/pairs` are not yet computed by `image_match.py`. Connect the PyISIS representative-point geometry path into tile task construction before running this command.

Use the Phase 1 pair and metadata table:

```bash
python examples/image_match/image_match.py \
  /media/gengxun/My\ Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_preprocess/doms_10m/dom_REDUCED_M110860982RE.cub \
  /media/gengxun/My\ Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_preprocess/doms_10m/dom_REDUCED_M110881352RE.cub \
  --matcher-method flann \
  --enable-adaptive-routing \
  --dom-source-metadata-csv /media/gengxun/My\ Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_routing_preprocess/reduced_selected_pair_paths.csv \
  --block-width 1024 \
  --block-height 1024 \
  --max-image-dimension 1024 \
  --valid-intensity-lower-percent 0.1 \
  --valid-intensity-upper-percent 99.9 \
  --deep-match-mode export \
  --deep-match-temp-root-dir /media/gengxun/My\ Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/tile_illumination_smoke/tmp_deep_match \
  --metadata-output /media/gengxun/My\ Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/tile_illumination_smoke/match_metadata.json
```

Expected:

- metadata JSON exists;
- `adaptive_routing.tile_illumination.summary.tile_count` is greater than zero;
- at least one tile has `representative_point.status` equal to `center_projectable` or `nearest_projectable_pixel`;
- no matching route retries are recorded.

- [ ] **Step 4: Run deep manifest smoke in `deep-learning`**

Status: deferred until Step 3 produces real routed deep tasks from physical tile illumination.

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate deep-learning
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8
python examples/learning_methods/run_deep_match_manifest.py \
  /media/gengxun/My\ Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/tile_illumination_smoke/tmp_deep_match/*/tasks.json \
  --torch-num-threads 8 \
  --num-workers 1
```

Expected: deep result NPZ files are written for exported deep tasks. If no deep tasks are selected for this smoke pair, record `no_deep_tasks_selected` in progress and continue.

- [x] **Step 5: Update planning files**

Append to `.planning/2026-06-02-tile-illumination-adaptive-routing/progress.md`:

```markdown
- Implemented tile-level physical illumination adaptive routing.
- Validation:
  - focused unit tests: PASS
  - smoke import: PASS
  - real-data tile illumination dry-run: PASS
  - deep manifest smoke: PASS or no_deep_tasks_selected
```

- [ ] **Step 6: Commit**

Status: optional for this focused validation checkpoint; commit after deciding whether to include the planning-file update alone or continue directly into the runtime integration follow-up.

```bash
git add .planning/2026-06-02-tile-illumination-adaptive-routing/progress.md
git commit -m "test: validate tile illumination routing smoke"
```

---

## Self-Review

- Spec coverage:
  - Data model: Task 1.
  - Representative point and `pixel_available` versus `radiometric_valid_for_matching`: Task 2.
  - Source cube metadata: Task 3 and Task 7.
  - Tile routing and no post-match fallback: Task 4 and Task 6.
  - Deep manifest grouping/provenance: Task 5 and Task 6.
  - Reporting and RANSAC-oriented summaries: Task 8.
  - Real-data smoke validation: Task 9.
- Placeholder scan: no task uses unspecified implementation language; each task has concrete files, commands, expected results, and code-level changes.
- Type consistency:
  - `RepresentativePoint`, `TileIlluminationSample`, and `TileIlluminationPair` are defined before being consumed.
  - `route_metadata` is added to `TileMatchTask` before deep manifests preserve it.
  - Routing uses `selected_matcher` and `selected_execution_environment` consistently.

## Execution Notes

- Use an isolated worktree before implementation if the current dirty branch contains unrelated benchmark or paper changes.
- Keep commits focused by task.
- Do not stage `.gitignore` or `print.prt`.
- Do not treat queued GitHub gate jobs as blocking if local PyISIS validation has passed and the PR is mergeable.
