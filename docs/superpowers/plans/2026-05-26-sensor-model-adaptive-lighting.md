# Sensor-Model Adaptive Lighting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make adaptive lighting read solar azimuth and solar elevation from the ISIS cube sensor model first, using `Camera.set_image()` at the image center.

**Architecture:** Keep `read_solar_geometry_from_cube()` as the public API. Internally, split the current label-reader into a label fallback helper and add a sensor-model helper that returns `SolarGeometry(source_group_name="SensorModelCenter", elevation_keyword="90-IncidenceAngle", azimuth_keyword="SunAzimuth")`. Adaptive routing continues to call the same public API, so routing code should only need regression coverage, not a new data path.

**Tech Stack:** Python 3.12, `unittest`, `unittest.mock`, PyISIS `isis_pybind`, ISIS `Camera.set_image()`, `Camera.sun_azimuth()`, `Sensor.incidence_angle()`.

---

## File Structure

- Modify `examples/image_match/lighting_difference.py`
  - Owns solar geometry reading and lighting-difference scoring.
  - Add sensor-model center geometry as the primary reader.
  - Preserve existing label keyword parsing as fallback.
- Modify `tests/unitTest/image_match_lighting_difference_unit_test.py`
  - Add fake camera and cube tests for sensor-first behavior, fallback behavior, and combined error messages.
- Modify `tests/unitTest/image_match_adaptive_routing_unit_test.py`
  - Add one routing-level regression proving finite sensor-model lighting reaches the adaptive-routing sidecar.
- No pybind C++ changes.
- No command-line API changes.
- No matcher threshold changes.

---

### Task 1: Add Failing Sensor-Model Reader Tests

**Files:**
- Modify: `tests/unitTest/image_match_lighting_difference_unit_test.py`
- Test: `tests/unitTest/image_match_lighting_difference_unit_test.py`

- [ ] **Step 1: Add fake camera support to the lighting test file**

In `tests/unitTest/image_match_lighting_difference_unit_test.py`, replace the current `_FakeCube` class with the following two classes:

```python
class _FakeCamera:
    def __init__(
        self,
        *,
        set_image_result: bool = True,
        sun_azimuth: object = 120.0,
        incidence_angle: object = 55.0,
        fail_camera_method: str | None = None,
    ):
        self.set_image_result = set_image_result
        self.sun_azimuth_value = sun_azimuth
        self.incidence_angle_value = incidence_angle
        self.fail_camera_method = fail_camera_method
        self.set_image_calls: list[tuple[float, float]] = []

    def set_image(self, sample: float, line: float) -> bool:
        self.set_image_calls.append((sample, line))
        if self.fail_camera_method == "set_image":
            raise RuntimeError("set_image failed from fake camera")
        return self.set_image_result

    def sun_azimuth(self):
        if self.fail_camera_method == "sun_azimuth":
            raise RuntimeError("sun_azimuth failed from fake camera")
        return self.sun_azimuth_value

    def incidence_angle(self):
        if self.fail_camera_method == "incidence_angle":
            raise RuntimeError("incidence_angle failed from fake camera")
        return self.incidence_angle_value


class _FakeCube:
    def __init__(
        self,
        groups: dict[str, _FakePvlGroup],
        *,
        camera: _FakeCamera | None = None,
        sample_count: int = 100,
        line_count: int = 50,
        fail_camera: bool = False,
    ):
        self._groups = groups
        self._camera = camera
        self._sample_count = sample_count
        self._line_count = line_count
        self._fail_camera = fail_camera

    def has_group(self, name: str) -> bool:
        return name in self._groups

    def group(self, name: str) -> _FakePvlGroup:
        return self._groups[name]

    def sample_count(self) -> int:
        return self._sample_count

    def line_count(self) -> int:
        return self._line_count

    def camera(self) -> _FakeCamera:
        if self._fail_camera:
            raise RuntimeError("camera initialization failed from fake cube")
        if self._camera is None:
            raise RuntimeError("fake cube has no camera")
        return self._camera
```

- [ ] **Step 2: Add sensor-model success and center-coordinate tests**

Add these methods to `ImageMatchLightingDifferenceUnitTest`:

```python
    def test_read_solar_geometry_prefers_sensor_model_center(self):
        camera = _FakeCamera(sun_azimuth=164.25, incidence_angle=56.5)
        cube = _FakeCube(
            {
                "Instrument": _FakePvlGroup(
                    {
                        "SolarElevation": [10.0],
                        "SolarAzimuth": [20.0],
                    }
                )
            },
            camera=camera,
            sample_count=100,
            line_count=50,
        )

        geometry = read_solar_geometry_from_cube(cube)

        self.assertEqual(camera.set_image_calls, [(50.5, 25.5)])
        self.assertAlmostEqual(geometry.solar_azimuth_degrees, 164.25)
        self.assertAlmostEqual(geometry.solar_elevation_degrees, 33.5)
        self.assertEqual(geometry.source_group_name, "SensorModelCenter")
        self.assertEqual(geometry.elevation_keyword, "90-IncidenceAngle")
        self.assertEqual(geometry.azimuth_keyword, "SunAzimuth")

    def test_read_solar_geometry_accepts_sensor_model_azimuth_only(self):
        camera = _FakeCamera(
            sun_azimuth=75.0,
            incidence_angle=None,
            fail_camera_method="incidence_angle",
        )
        cube = _FakeCube({}, camera=camera, sample_count=9, line_count=9)

        geometry = read_solar_geometry_from_cube(cube)

        self.assertEqual(camera.set_image_calls, [(5.0, 5.0)])
        self.assertIsNone(geometry.solar_elevation_degrees)
        self.assertAlmostEqual(geometry.solar_azimuth_degrees, 75.0)
        self.assertEqual(geometry.source_group_name, "SensorModelCenter")
        self.assertIsNone(geometry.elevation_keyword)
        self.assertEqual(geometry.azimuth_keyword, "SunAzimuth")
```

- [ ] **Step 3: Add fallback and combined-error tests**

Add these methods to `ImageMatchLightingDifferenceUnitTest`:

```python
    def test_read_solar_geometry_sensor_failure_falls_back_to_label_keywords(self):
        cube = _FakeCube(
            {
                "Instrument": _FakePvlGroup(
                    {
                        "SolarElevation": [35.5],
                        "SubSolarAzimuth": [120.25],
                    }
                ),
            },
            camera=_FakeCamera(set_image_result=False),
        )

        geometry = read_solar_geometry_from_cube(cube)

        self.assertAlmostEqual(geometry.solar_elevation_degrees, 35.5)
        self.assertAlmostEqual(geometry.solar_azimuth_degrees, 120.25)
        self.assertEqual(geometry.elevation_keyword, "SolarElevation")
        self.assertEqual(geometry.azimuth_keyword, "SubSolarAzimuth")
        self.assertEqual(geometry.source_group_name, "Instrument")

    def test_read_solar_geometry_error_mentions_sensor_and_label_failures(self):
        cube = _FakeCube(
            {"Mapping": _FakePvlGroup({"CenterLatitude": [0.0]})},
            fail_camera=True,
        )

        with self.assertRaises(SolarGeometryFieldMissing) as context:
            read_solar_geometry_from_cube(cube)

        message = str(context.exception)
        self.assertIn("sensor model", message)
        self.assertIn("camera initialization failed from fake cube", message)
        self.assertIn("label fallback", message)
        self.assertIn("Could not resolve solar elevation or azimuth", message)
```

- [ ] **Step 4: Run the focused failing tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_lighting_difference_unit_test -v
```

Expected now: the new sensor-model tests fail because `read_solar_geometry_from_cube()` still reads label keywords first and does not call `cube.camera()`.

- [ ] **Step 5: Commit the failing tests**

Run:

```bash
git add tests/unitTest/image_match_lighting_difference_unit_test.py
git commit -m "test: cover sensor-model solar geometry reader"
```

---

### Task 2: Implement Sensor-Model First Solar Geometry

**Files:**
- Modify: `examples/image_match/lighting_difference.py`
- Test: `tests/unitTest/image_match_lighting_difference_unit_test.py`

- [ ] **Step 1: Add sensor-model constants**

In `examples/image_match/lighting_difference.py`, after the normalizer constants, add:

```python
SENSOR_MODEL_SOURCE_NAME = "SensorModelCenter"
SENSOR_MODEL_ELEVATION_KEYWORD = "90-IncidenceAngle"
SENSOR_MODEL_AZIMUTH_KEYWORD = "SunAzimuth"
```

- [ ] **Step 2: Extract the current label reader into a private helper**

Replace the body of `read_solar_geometry_from_cube()` with a call structure in later steps. First, move the current label-reading logic into this helper below `_resolve_keyword()`:

```python
def _read_label_solar_geometry_from_cube(
    cube: Any,
    *,
    group_names: Iterable[str] = DEFAULT_INSTRUMENT_GROUP_NAMES,
    elevation_keywords: Iterable[str] = DEFAULT_SOLAR_ELEVATION_KEYWORDS,
    azimuth_keywords: Iterable[str] = DEFAULT_SOLAR_AZIMUTH_KEYWORDS,
) -> SolarGeometry:
    """Extract solar elevation/azimuth from cube label keywords."""

    resolved_group_names = tuple(group_names)
    has_group = getattr(cube, "has_group", None)
    group_getter = getattr(cube, "group", None)
    if has_group is None or group_getter is None:
        raise SolarGeometryFieldMissing(
            "cube object does not expose has_group/group; cannot read label solar geometry."
        )

    resolved_elevation: tuple[str, float] | None = None
    resolved_azimuth: tuple[str, float] | None = None
    resolved_group_name: str | None = None
    for candidate_group_name in resolved_group_names:
        if not has_group(candidate_group_name):
            continue
        group = group_getter(candidate_group_name)
        if resolved_elevation is None:
            resolved_elevation = _resolve_keyword(group, elevation_keywords)
            if resolved_elevation is not None:
                resolved_group_name = candidate_group_name
        if resolved_azimuth is None:
            resolved_azimuth = _resolve_keyword(group, azimuth_keywords)
            if resolved_azimuth is not None and resolved_group_name is None:
                resolved_group_name = candidate_group_name
        if resolved_elevation is not None and resolved_azimuth is not None:
            break

    if resolved_elevation is None and resolved_azimuth is None:
        raise SolarGeometryFieldMissing(
            "Could not resolve solar elevation or azimuth from any of the candidate groups: "
            f"{resolved_group_names!r}."
        )

    return SolarGeometry(
        solar_elevation_degrees=None if resolved_elevation is None else resolved_elevation[1],
        solar_azimuth_degrees=None if resolved_azimuth is None else resolved_azimuth[1],
        source_group_name=resolved_group_name,
        elevation_keyword=None if resolved_elevation is None else resolved_elevation[0],
        azimuth_keyword=None if resolved_azimuth is None else resolved_azimuth[0],
    )
```

- [ ] **Step 3: Add the sensor-model helper**

Add this helper below `_read_label_solar_geometry_from_cube()`:

```python
def _read_sensor_model_solar_geometry_from_cube(cube: Any) -> SolarGeometry:
    """Compute center-point solar geometry through the ISIS cube camera model."""

    camera_getter = getattr(cube, "camera", None)
    sample_count_getter = getattr(cube, "sample_count", None)
    line_count_getter = getattr(cube, "line_count", None)
    if camera_getter is None:
        raise SolarGeometryFieldMissing("cube object does not expose camera(); cannot read sensor model geometry.")
    if sample_count_getter is None or line_count_getter is None:
        raise SolarGeometryFieldMissing(
            "cube object does not expose sample_count()/line_count(); cannot choose sensor model center."
        )

    try:
        sample_count = _finite_float(sample_count_getter())
        line_count = _finite_float(line_count_getter())
    except Exception as exc:  # noqa: BLE001 - include underlying ISIS/PyISIS error in diagnostics
        raise SolarGeometryFieldMissing(f"failed reading cube dimensions for sensor model geometry: {exc}") from exc

    if sample_count is None or line_count is None or sample_count <= 0.0 or line_count <= 0.0:
        raise SolarGeometryFieldMissing(
            f"invalid cube dimensions for sensor model geometry: sample_count={sample_count!r}, line_count={line_count!r}."
        )

    center_sample = (sample_count + 1.0) / 2.0
    center_line = (line_count + 1.0) / 2.0

    try:
        camera = camera_getter()
    except Exception as exc:  # noqa: BLE001 - include underlying ISIS/PyISIS error in diagnostics
        raise SolarGeometryFieldMissing(f"failed initializing sensor model camera: {exc}") from exc

    set_image = getattr(camera, "set_image", None)
    if set_image is None:
        raise SolarGeometryFieldMissing("camera object does not expose set_image(); cannot read sensor model geometry.")

    try:
        if not set_image(center_sample, center_line):
            raise SolarGeometryFieldMissing(
                f"camera.set_image({center_sample}, {center_line}) returned false for sensor model geometry."
            )
    except SolarGeometryFieldMissing:
        raise
    except Exception as exc:  # noqa: BLE001 - include underlying ISIS/PyISIS error in diagnostics
        raise SolarGeometryFieldMissing(
            f"camera.set_image({center_sample}, {center_line}) failed for sensor model geometry: {exc}"
        ) from exc

    resolved_azimuth: float | None = None
    azimuth_error: str | None = None
    sun_azimuth = getattr(camera, "sun_azimuth", None)
    if sun_azimuth is None:
        azimuth_error = "camera object does not expose sun_azimuth()."
    else:
        try:
            resolved_azimuth = _finite_float(sun_azimuth())
        except Exception as exc:  # noqa: BLE001 - keep partial geometry when elevation works
            azimuth_error = f"camera.sun_azimuth() failed: {exc}"
        if resolved_azimuth is None and azimuth_error is None:
            azimuth_error = "camera.sun_azimuth() returned a non-finite value."

    resolved_elevation: float | None = None
    elevation_error: str | None = None
    incidence_angle = getattr(camera, "incidence_angle", None)
    if incidence_angle is None:
        elevation_error = "camera object does not expose incidence_angle()."
    else:
        try:
            incidence = _finite_float(incidence_angle())
        except Exception as exc:  # noqa: BLE001 - keep partial geometry when azimuth works
            incidence = None
            elevation_error = f"camera.incidence_angle() failed: {exc}"
        if incidence is None and elevation_error is None:
            elevation_error = "camera.incidence_angle() returned a non-finite value."
        if incidence is not None:
            resolved_elevation = 90.0 - incidence

    if resolved_elevation is None and resolved_azimuth is None:
        reasons = "; ".join(reason for reason in (elevation_error, azimuth_error) if reason)
        raise SolarGeometryFieldMissing(
            "sensor model geometry did not provide finite solar elevation or azimuth"
            + (f": {reasons}" if reasons else ".")
        )

    return SolarGeometry(
        solar_elevation_degrees=resolved_elevation,
        solar_azimuth_degrees=resolved_azimuth,
        source_group_name=SENSOR_MODEL_SOURCE_NAME,
        elevation_keyword=None if resolved_elevation is None else SENSOR_MODEL_ELEVATION_KEYWORD,
        azimuth_keyword=None if resolved_azimuth is None else SENSOR_MODEL_AZIMUTH_KEYWORD,
    )
```

- [ ] **Step 4: Replace the public reader with sensor-first logic**

Replace `read_solar_geometry_from_cube()` with:

```python
def read_solar_geometry_from_cube(
    cube: Any,
    *,
    group_names: Iterable[str] = DEFAULT_INSTRUMENT_GROUP_NAMES,
    elevation_keywords: Iterable[str] = DEFAULT_SOLAR_ELEVATION_KEYWORDS,
    azimuth_keywords: Iterable[str] = DEFAULT_SOLAR_AZIMUTH_KEYWORDS,
) -> SolarGeometry:
    """Extract solar elevation/azimuth from an open ISIS cube.

    The primary source is the ISIS sensor model positioned at the image center.
    Label keywords are retained as a fallback for lightweight fixtures and
    non-camera cube-like objects.
    """

    sensor_error: SolarGeometryFieldMissing | None = None
    try:
        return _read_sensor_model_solar_geometry_from_cube(cube)
    except SolarGeometryFieldMissing as exc:
        sensor_error = exc

    try:
        return _read_label_solar_geometry_from_cube(
            cube,
            group_names=group_names,
            elevation_keywords=elevation_keywords,
            azimuth_keywords=azimuth_keywords,
        )
    except SolarGeometryFieldMissing as label_error:
        raise SolarGeometryFieldMissing(
            "Could not resolve solar geometry from sensor model or label fallback. "
            f"sensor model error: {sensor_error}; label fallback error: {label_error}"
        ) from label_error
```

- [ ] **Step 5: Export constants for diagnostics and tests**

In the `__all__` list in `examples/image_match/lighting_difference.py`, add:

```python
    "SENSOR_MODEL_AZIMUTH_KEYWORD",
    "SENSOR_MODEL_ELEVATION_KEYWORD",
    "SENSOR_MODEL_SOURCE_NAME",
```

- [ ] **Step 6: Run the lighting tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_lighting_difference_unit_test -v
```

Expected: all lighting tests pass.

- [ ] **Step 7: Commit the implementation**

Run:

```bash
git add examples/image_match/lighting_difference.py tests/unitTest/image_match_lighting_difference_unit_test.py
git commit -m "feat: read adaptive lighting from sensor model"
```

---

### Task 3: Add Adaptive-Routing Sidecar Regression

**Files:**
- Modify: `tests/unitTest/image_match_adaptive_routing_unit_test.py`
- Test: `tests/unitTest/image_match_adaptive_routing_unit_test.py`

- [ ] **Step 1: Add test imports**

At the top of `tests/unitTest/image_match_adaptive_routing_unit_test.py`, add:

```python
import importlib
from unittest.mock import patch
```

- [ ] **Step 2: Add a routing-level sensor lighting test**

Add this method to `ImageMatchAdaptiveRoutingSparsenessLightingUnitTest`:

```python
    def test_resolve_adaptive_route_sidecar_uses_sensor_model_lighting(self):
        image_match_module = importlib.import_module("image_match.image_match")
        from image_match.lighting_difference import SolarGeometry

        texture_probe = ImageTextureProbe(
            keypoint_count=100,
            valid_pixel_count=1000,
            total_pixel_count=1000,
            keypoint_density=0.10,
            mean_gradient=120.0,
            laplacian_variance=2500.0,
            entropy=4.2,
            valid_pixel_ratio=1.0,
            real_texture_score=0.85,
        )
        left_geometry = SolarGeometry(
            solar_elevation_degrees=33.5,
            solar_azimuth_degrees=164.0,
            source_group_name="SensorModelCenter",
            elevation_keyword="90-IncidenceAngle",
            azimuth_keyword="SunAzimuth",
        )
        right_geometry = SolarGeometry(
            solar_elevation_degrees=33.0,
            solar_azimuth_degrees=165.0,
            source_group_name="SensorModelCenter",
            elevation_keyword="90-IncidenceAngle",
            azimuth_keyword="SunAzimuth",
        )

        with (
            patch.object(
                image_match_module,
                "_compute_texture_probe_from_cube_path",
                return_value=texture_probe,
            ),
            patch.object(
                image_match_module,
                "_compute_texture_sparseness_and_geometry_from_cube_path",
                side_effect=[
                    ("left_sparseness", left_geometry, None),
                    ("right_sparseness", right_geometry, None),
                ],
            ),
            patch.object(
                image_match_module,
                "aggregate_pair_texture_sparseness",
                return_value="pair_sparseness",
            ),
            patch.object(
                image_match_module,
                "pair_summary_to_diagnostic_dict",
                return_value={"pair_texture_sparseness": 0.12, "weaker_side": "left"},
            ),
        ):
            selected, summary = image_match_module._resolve_adaptive_route_for_pair(
                enable_adaptive_routing=True,
                requested_matcher_method="flann",
                adaptive_routing_deep_presets=None,
                band=1,
                invalid_values=(),
                special_pixel_abs_threshold=1e300,
                low_resolution_offset_summary={
                    "left_low_resolution_dom": "left_preview.cub",
                    "right_low_resolution_dom": "right_preview.cub",
                },
                left_low_resolution_dom=None,
                right_low_resolution_dom=None,
            )

        self.assertEqual(selected, "flann")
        self.assertIsNotNone(summary)
        lighting = summary["sidecar"]["lighting_difference"]
        self.assertIsNotNone(lighting["lighting_difference_score"])
        self.assertEqual(lighting["left_solar_geometry"]["source_group_name"], "SensorModelCenter")
        self.assertEqual(lighting["right_solar_geometry"]["source_group_name"], "SensorModelCenter")
        self.assertEqual(lighting["left_solar_geometry"]["elevation_keyword"], "90-IncidenceAngle")
        self.assertEqual(lighting["left_solar_geometry"]["azimuth_keyword"], "SunAzimuth")
```

- [ ] **Step 3: Run the adaptive-routing focused test**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test.ImageMatchAdaptiveRoutingSparsenessLightingUnitTest.test_resolve_adaptive_route_sidecar_uses_sensor_model_lighting -v
```

Expected: pass.

- [ ] **Step 4: Run both affected unit modules**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest \
  tests.unitTest.image_match_lighting_difference_unit_test \
  tests.unitTest.image_match_adaptive_routing_unit_test \
  -v
```

Expected: all tests in both modules pass.

- [ ] **Step 5: Commit adaptive-routing regression coverage**

Run:

```bash
git add tests/unitTest/image_match_adaptive_routing_unit_test.py
git commit -m "test: cover sensor-model lighting in adaptive routing"
```

---

### Task 4: Verify On Real LRO `pipe_test2` Data

**Files:**
- No repo source files.
- Output directory under `/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2/adaptive_lighting_sensor_model_<timestamp>`.

- [ ] **Step 1: Run real-data route diagnostics for all six pairs**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="${ISISDATA:-$CONDA_PREFIX/data}"
ROOT="/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2"
RUN_DIR="$ROOT/adaptive_lighting_sensor_model_$(date +%Y%m%dT%H%M%S)"
mkdir -p "$RUN_DIR"
python - "$RUN_DIR" <<'PY'
from __future__ import annotations

from pathlib import Path
import json
import sys

from image_match.image_match import _resolve_adaptive_route_for_pair

root = Path("/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2")
run_dir = Path(sys.argv[1])
preset_map = {
    "lightglue": str(Path("examples/controlnet_construct/presets/lightglue_official_superpoint.json").resolve()),
    "lightglue_high_recall": str(Path("examples/controlnet_construct/presets/lightglue_official_superpoint.json").resolve()),
    "loftr": str(Path("examples/controlnet_construct/presets/loftr_default.json").resolve()),
}

pairs = []
for line in (root / "images_overlap.lis").read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    left, right = [Path(part.strip()) for part in line.split(",", 1)]
    selected, route = _resolve_adaptive_route_for_pair(
        enable_adaptive_routing=True,
        requested_matcher_method="flann",
        adaptive_routing_deep_presets=preset_map,
        band=1,
        invalid_values=(),
        special_pixel_abs_threshold=1e300,
        low_resolution_offset_summary={},
        left_low_resolution_dom=None,
        right_low_resolution_dom=None,
        image_space="ori",
        left_source_path=left,
        right_source_path=right,
    )
    sidecar = (route or {}).get("sidecar") or {}
    lighting = sidecar.get("lighting_difference") or {}
    pairs.append(
        {
            "left": str(left),
            "right": str(right),
            "selected": selected,
            "status": None if route is None else route.get("status"),
            "reason": None if route is None else route.get("route_reason"),
            "lighting_difference_score": lighting.get("lighting_difference_score"),
            "left_source": (lighting.get("left_solar_geometry") or {}).get("source_group_name"),
            "right_source": (lighting.get("right_solar_geometry") or {}).get("source_group_name"),
        }
    )

bad = [
    pair for pair in pairs
    if pair["lighting_difference_score"] is None
    or pair["left_source"] != "SensorModelCenter"
    or pair["right_source"] != "SensorModelCenter"
]
report = {"pair_count": len(pairs), "bad_pair_count": len(bad), "pairs": pairs}
out = run_dir / "adaptive_lighting_sensor_model_report.json"
out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(out)
print(json.dumps(report, indent=2, ensure_ascii=False))
if len(pairs) != 6 or bad:
    raise SystemExit(1)
PY
```

Expected:

- command exits `0`;
- `pair_count` is `6`;
- `bad_pair_count` is `0`;
- every pair has finite `lighting_difference_score`;
- every pair has `left_source` and `right_source` equal to `SensorModelCenter`.

- [ ] **Step 2: Run the one-pair DOM image-match smoke check**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="${ISISDATA:-$CONDA_PREFIX/data}"
ROOT="/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2"
RUN_DIR="$(ls -td "$ROOT"/adaptive_lighting_sensor_model_* | head -1)"
PAIR_DIR="$RUN_DIR/dom_image_match_first_pair"
mkdir -p "$PAIR_DIR"
python - "$PAIR_DIR" <<'PY'
from pathlib import Path
import json
import sys

root = Path("/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2")
pair_dir = Path(sys.argv[1])
repo = Path("/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone")
config = json.loads((root / "controlnet_lightglue_official_superpoint.json").read_text(encoding="utf-8"))
image_match = config.setdefault("ImageMatch", {})
image_match["matcher_method"] = "flann"
image_match["enable_adaptive_routing"] = True
image_match["adaptive_routing_profile"] = "balanced"
image_match["adaptive_routing_deep_presets"] = {
    "lightglue": str(repo / "examples/controlnet_construct/presets/lightglue_official_superpoint.json"),
    "lightglue_high_recall": str(repo / "examples/controlnet_construct/presets/lightglue_official_superpoint.json"),
    "loftr": str(repo / "examples/controlnet_construct/presets/loftr_default.json"),
}
(pair_dir / "config_adaptive_presets.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
PY
python examples/image_match/image_match.py \
  --config "$PAIR_DIR/config_adaptive_presets.json" \
  "$ROOT/dom_M104311715LE.cub" \
  "$ROOT/dom_M104311715RE.cub" \
  "$PAIR_DIR/left_dom.key" \
  "$PAIR_DIR/right_dom.key" \
  --metadata-output "$PAIR_DIR/metadata.json" \
  --result-output "$PAIR_DIR/result.json" \
  --match-visualization-output-dir "$PAIR_DIR/viz" \
  --matcher-method flann \
  --adaptive-routing \
  --adaptive-routing-profile balanced \
  --no-parallel-cpu \
  --omit-tile-details \
  --no-progress
python - "$PAIR_DIR/result.json" <<'PY'
from pathlib import Path
import json
import sys

result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
lighting = result["adaptive_routing"]["sidecar"]["lighting_difference"]
print(json.dumps({
    "status": result["status"],
    "point_count": result["point_count"],
    "selected_final_matcher": result["adaptive_routing"]["selected_final_matcher"],
    "lighting_difference_score": lighting.get("lighting_difference_score"),
    "left_source": (lighting.get("left_solar_geometry") or {}).get("source_group_name"),
    "right_source": (lighting.get("right_solar_geometry") or {}).get("source_group_name"),
}, indent=2))
if result["status"] != "matched":
    raise SystemExit(1)
if result["point_count"] <= 0:
    raise SystemExit(1)
if lighting.get("lighting_difference_score") is None:
    raise SystemExit(1)
PY
```

Expected:

- image-match command exits `0`;
- result status is `matched`;
- point count is positive;
- adaptive-routing sidecar has finite `lighting_difference_score`.

- [ ] **Step 3: Run final source checks**

Run:

```bash
git diff --check
git status --short --branch
```

Expected:

- `git diff --check` exits `0`;
- status shows only planned changes plus pre-existing `.gitignore` and `print.prt` if they are still dirty.

- [ ] **Step 4: Commit real-data verification notes only if a repo artifact was added**

If no repo file was added for verification, do not commit anything in this task. If an implementation note is added under `docs/superpowers/`, commit only that note:

```bash
git add docs/superpowers/<exact-new-note-file>
git commit -m "docs: record sensor-model lighting verification"
```

---

## Self-Review Checklist

- Spec coverage:
  - Sensor-model first source is covered by Task 2.
  - Center sample/line convention is covered by Task 1 and Task 2.
  - `SunAzimuth` plus `90-IncidenceAngle` metadata is covered by Task 1 and Task 2.
  - Label fallback and combined errors are covered by Task 1 and Task 2.
  - Adaptive-routing sidecar propagation is covered by Task 3.
  - Real LRO `pipe_test2` verification is covered by Task 4.
- No pybind changes are planned.
- No matcher threshold, cascade, deep preset, or ControlNet materialization changes are planned.
