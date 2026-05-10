# Dense NCC Disparity DEM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `from-dense-ncc` pipeline that produces dense DEM from stereo cubes using NCC-based per-pixel disparity matching, seeded by sparse KEY point priors.

**Architecture:** Three new modules (`disparity_model.py`, `dense_ncc.py`, `dense_triangulation.py`) plugged into the existing `dem_extract` package. The pipeline: sparse KEY → polynomial disparity prior → per-pixel NCC → disparity CUBE → triangulation → reuse `grid.py`/`cube_writer.py` → DEM.

**Tech Stack:** Python 3.10+, NumPy, `scipy.signal.correlate2d` for NCC, existing ISIS pybind bindings for triangulation/cube I/O.

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `examples/dem_extract/key_pairs.py` | Float-type `KeyPointPair` coordinates |
| Modify | `examples/dem_extract/runtime.py` | `build_summary` accepts dense-NCC extra fields |
| Modify | `examples/dem_extract/isis_stereo_dem.py` | New `from-dense-ncc` subcommand + `run_from_dense_ncc()` |
| Modify | `examples/dem_extract/__init__.py` | Export new modules |
| Modify | `examples/dem_extract/dem_pipeline.py` | Wire `from-dense-ncc` into pipeline CLI |
| Modify | `examples/dem_extract/dem_config.example.json` | Add `DenseNCC` config section |
| Create | `examples/dem_extract/disparity_model.py` | Sparse KEY → polynomial disparity model |
| Create | `examples/dem_extract/dense_ncc.py` | Per-pixel NCC matching → 3×float32 disparity arrays |
| Create | `examples/dem_extract/dense_triangulation.py` | Disparity arrays → `TriangulatedPoint` iterator |
| Modify | `tests/unitTest/dem_extract_unit_test.py` | Tests for all new modules |

---

### Task 1: KeyPointPair Float-ification

**Files:**
- Modify: `examples/dem_extract/key_pairs.py`
- Test: `tests/unitTest/dem_extract_unit_test.py` (existing test already uses float coords — verify it still passes)

- [ ] **Step 1: Update KeyPointPair type hints**

The current `key_pairs.py` already stores float values (line 32-37 uses `float` not `int`). The type hints and `_validate_point` already support floats. No code change needed — the existing implementation already works with float coordinates. Verify by reading the file:

```python
# key_pairs.py lines 32-37 already define:
@dataclass(frozen=True, slots=True)
class KeyPointPair:
    index: int
    left_sample: float
    left_line: float
    right_sample: float
    right_line: float
```

The `_validate_point` function at lines 46-51 already uses float comparisons:

```python
def _validate_point(label: str, index: int, sample: float, line: float, samples: int, lines: int) -> None:
    if not (1.0 <= sample <= float(samples)) or not (1.0 <= line <= float(lines)):
        raise ValueError(...)
```

No changes needed — the codebase already uses `float` for coordinates. The existing test at line 82-87 (`test_key_sample_line_are_preserved_without_offset`) already passes float values like `10.25, 20.5`.

- [ ] **Step 2: Run existing tests to confirm nothing broke**

Run:
```bash
cd /home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone
python -m unittest tests.unitTest.dem_extract_unit_test.DemExtractKeyPairUnitTest -v
python -m unittest tests.unitTest.dem_extract_unit_test.DemExtractTriangulationUnitTest -v
```

Expected: All tests PASS. The triangulation test already passes float coords `10.25, 20.5, 30.75, 40.5` to `set_image`.

- [ ] **Step 3: Commit**

```bash
git add examples/dem_extract/key_pairs.py
git commit -m "chore: verify KeyPointPair already supports float coordinates for dense matching"
```

---

### Task 2: Disparity Model Module

**Files:**
- Create: `examples/dem_extract/disparity_model.py`
- Test: `tests/unitTest/dem_extract_unit_test.py` (new test class)

- [ ] **Step 1: Write tests for DisparityModel**

Add to `tests/unitTest/dem_extract_unit_test.py`:

```python
class DemExtractDisparityModelUnitTest(unittest.TestCase):
    def test_fit_disparity_model_returns_valid_model_with_r_squared(self):
        from dem_extract.disparity_model import DisparityModel, fit_disparity_model
        from dem_extract.key_pairs import KeyPointPair

        # Create pairs with a simple linear disparity pattern: dx = s*0.1, dy = l*0.05
        pairs = [
            KeyPointPair(i, float(s), float(l), float(s + s * 0.1), float(l + l * 0.05))
            for i, (s, l) in enumerate([(10, 10), (20, 20), (30, 30), (40, 40), (50, 50)])
        ]

        model = fit_disparity_model(pairs, order=2)

        self.assertEqual(model.order, 2)
        self.assertGreater(model.dx_r_squared, 0.99)
        self.assertGreater(model.dy_r_squared, 0.99)
        # Verify evaluation at a known point
        dx = model.eval_dx(20.0, 20.0)
        dy = model.eval_dy(20.0, 20.0)
        self.assertAlmostEqual(dx, 2.0, places=1)  # 20 * 0.1 = 2.0
        self.assertAlmostEqual(dy, 1.0, places=1)  # 20 * 0.05 = 1.0

    def test_fit_disparity_model_fallback_to_mean_when_insufficient_points(self):
        from dem_extract.disparity_model import fit_disparity_model
        from dem_extract.key_pairs import KeyPointPair

        # Only 2 points — below min_points=20
        pairs = [
            KeyPointPair(0, 10.0, 10.0, 15.0, 12.0),
            KeyPointPair(1, 20.0, 20.0, 25.0, 22.0),
        ]

        model = fit_disparity_model(pairs, order=2, min_points=5)

        self.assertEqual(model.prior_fallback, "mean_disparity")
        dx = model.eval_dx(30.0, 30.0)
        dy = model.eval_dy(30.0, 30.0)
        # Mean dx = (5+5)/2 = 5.0, mean dy = (2+2)/2 = 2.0
        self.assertAlmostEqual(dx, 5.0, places=6)
        self.assertAlmostEqual(dy, 2.0, places=6)

    def test_disparity_model_eval_at_image_corners(self):
        from dem_extract.disparity_model import fit_disparity_model
        from dem_extract.key_pairs import KeyPointPair

        pairs = [
            KeyPointPair(i, 100.0 + i * 100, 100.0 + i * 50, 100.0 + i * 100 + 5.0, 100.0 + i * 50 + 2.0)
            for i in range(20)
        ]

        model = fit_disparity_model(pairs, order=1)

        # Should not raise
        dx_0 = model.eval_dx(1.0, 1.0)
        dx_max = model.eval_dx(1000.0, 1000.0)
        self.assertIsInstance(dx_0, float)
        self.assertIsInstance(dx_max, float)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
python -m unittest tests.unitTest.dem_extract_unit_test.DemExtractDisparityModelUnitTest -v
```

Expected: FAIL — module `dem_extract.disparity_model` does not exist.

- [ ] **Step 3: Implement disparity_model.py**

Create `examples/dem_extract/disparity_model.py`:

```python
"""Fit polynomial disparity models from sparse keypoint pairs.

Author: Geng Xun
Created: 2026-05-10
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .key_pairs import KeyPointPair


@dataclass(frozen=True)
class DisparityModel:
    dx_coeffs: np.ndarray
    dy_coeffs: np.ndarray
    order: int
    dx_r_squared: float
    dy_r_squared: float
    prior_fallback: str | None = None

    def eval_dx(self, s: float, l: float) -> float:
        return float(_eval_poly(self.dx_coeffs, self.order, s, l))

    def eval_dy(self, s: float, l: float) -> float:
        return float(_eval_poly(self.dy_coeffs, self.order, s, l))


def _build_design_matrix(samples: np.ndarray, lines: np.ndarray, order: int) -> np.ndarray:
    """Build the design matrix for polynomial fitting.

    For order=2: [1, s, l, s^2, s*l, l^2]
    For order=1: [1, s, l]
    """
    rows = [np.ones_like(samples)]
    if order >= 1:
        rows.append(samples)
        rows.append(lines)
    if order >= 2:
        rows.append(samples ** 2)
        rows.append(samples * lines)
        rows.append(lines ** 2)
    return np.column_stack(rows)


def _eval_poly(coeffs: np.ndarray, order: int, s: float, l: float) -> float:
    """Evaluate polynomial at (s, l) using the same term ordering as _build_design_matrix."""
    terms = [1.0]
    if order >= 1:
        terms.append(s)
        terms.append(l)
    if order >= 2:
        terms.append(s * s)
        terms.append(s * l)
        terms.append(l * l)
    return float(np.dot(coeffs, terms))


def fit_disparity_model(
    pairs: list[KeyPointPair],
    order: int = 2,
    min_points: int = 20,
) -> DisparityModel:
    """Fit dx/dy disparity polynomials from sparse keypoint pairs.

    If fewer than min_points pairs are available, falls back to mean disparity.
    """
    samples = np.array([p.left_sample for p in pairs], dtype=np.float64)
    lines = np.array([p.left_line for p in pairs], dtype=np.float64)
    dx_vals = np.array([p.right_sample - p.left_sample for p in pairs], dtype=np.float64)
    dy_vals = np.array([p.right_line - p.left_line for p in pairs], dtype=np.float64)

    if len(pairs) < min_points:
        mean_dx = float(np.mean(dx_vals))
        mean_dy = float(np.mean(dy_vals))
        n_terms = 1 + 2 * order + (order * (order - 1)) // 2 if order <= 2 else 0
        if order == 2:
            n_terms = 6
        elif order == 1:
            n_terms = 3
        elif order == 0:
            n_terms = 1
        return DisparityModel(
            dx_coeffs=np.array([mean_dx] + [0.0] * (n_terms - 1)),
            dy_coeffs=np.array([mean_dy] + [0.0] * (n_terms - 1)),
            order=order,
            dx_r_squared=0.0,
            dy_r_squared=0.0,
            prior_fallback="mean_disparity",
        )

    A = _build_design_matrix(samples, lines, order)
    dx_coeffs, dx_residuals, dx_rank, dx_sv = np.linalg.lstsq(A, dx_vals, rcond=None)
    dy_coeffs, dy_residuals, dy_rank, dy_sv = np.linalg.lstsq(A, dy_vals, rcond=None)

    dx_r_squared = _compute_r_squared(dx_vals, A @ dx_coeffs)
    dy_r_squared = _compute_r_squared(dy_vals, A @ dy_coeffs)

    return DisparityModel(
        dx_coeffs=dx_coeffs,
        dy_coeffs=dy_coeffs,
        order=order,
        dx_r_squared=dx_r_squared,
        dy_r_squared=dy_r_squared,
    )


def _compute_r_squared(actual: np.ndarray, predicted: np.ndarray) -> float:
    ss_res = float(np.sum((actual - predicted) ** 2))
    ss_tot = float(np.sum((actual - np.mean(actual)) ** 2))
    if ss_tot == 0.0:
        return 1.0
    return 1.0 - ss_res / ss_tot
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
python -m unittest tests.unitTest.dem_extract_unit_test.DemExtractDisparityModelUnitTest -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/dem_extract/disparity_model.py tests/unitTest/dem_extract_unit_test.py
git commit -m "feat: add disparity model fitting from sparse KEY pairs with mean fallback"
```

---

### Task 3: Dense NCC Matching Module

**Files:**
- Create: `examples/dem_extract/dense_ncc.py`
- Test: `tests/unitTest/dem_extract_unit_test.py` (new test class)

- [ ] **Step 1: Write tests for dense_ncc**

Add to `tests/unitTest/dem_extract_unit_test.py`:

```python
class DemExtractDenseNCCUnitTest(unittest.TestCase):
    def _make_fake_cube(self, width: int, height: int, data: np.ndarray):
        """Create a fake cube that returns numpy array data."""
        class FakeCube:
            def __init__(self):
                self._data = data
            def sample_count(self):
                return width
            def line_count(self):
                return height
            def read(self, band=1):
                return self._data
        return FakeCube()

    def _make_model(self, dx: float = 5.0, dy: float = 3.0):
        """Create a constant-disparity model."""
        from dem_extract.disparity_model import DisparityModel
        import numpy as np
        return DisparityModel(
            dx_coeffs=np.array([dx, 0.0, 0.0, 0.0, 0.0, 0.0]),
            dy_coeffs=np.array([dy, 0.0, 0.0, 0.0, 0.0, 0.0]),
            order=2,
            dx_r_squared=1.0,
            dy_r_squared=1.0,
        )

    def test_integer_pixel_match_succeeds_with_known_disparity(self):
        from dem_extract.dense_ncc import NCCMatchOptions, dense_ncc_match
        import numpy as np

        # Create simple images: right is left shifted by (dx=5, dy=3)
        left = np.zeros((50, 50), dtype=np.float64)
        left[15:35, 15:35] = 1.0  # White square
        right = np.zeros((50, 50), dtype=np.float64)
        right[18:38, 20:40] = 1.0  # Same square shifted by dy=3, dx=5

        left_cube = self._make_fake_cube(50, 50, left)
        right_cube = self._make_fake_cube(50, 50, right)
        model = self._make_model(dx=5.0, dy=3.0)

        disp_x, disp_y, ncc = dense_ncc_match(
            left_cube, right_cube, model,
            NCCMatchOptions(window_size=11, search_range=3, ncc_threshold=0.7, enable_subpixel=False),
        )

        # Center of the white square in left: (25, 25) should match with dx≈5, dy≈3
        center_ncc = ncc[24, 24]  # 0-indexed: line=24, sample=24
        center_dx = disp_x[24, 24]
        center_dy = disp_y[24, 24]

        self.assertGreater(center_ncc, 0.7)
        self.assertAlmostEqual(center_dx, 5.0, delta=1.0)
        self.assertAlmostEqual(center_dy, 3.0, delta=1.0)

    def test_nodata_for_unmatchable_region(self):
        from dem_extract.dense_ncc import NCCMatchOptions, dense_ncc_match
        import numpy as np

        # Completely different images — no match possible
        left = np.zeros((30, 30), dtype=np.float64)
        right = np.ones((30, 30), dtype=np.float64) * 0.5

        left_cube = self._make_fake_cube(30, 30, left)
        right_cube = self._make_fake_cube(30, 30, right)
        model = self._make_model(dx=0.0, dy=0.0)

        disp_x, disp_y, ncc = dense_ncc_match(
            left_cube, right_cube, model,
            NCCMatchOptions(window_size=7, search_range=2, ncc_threshold=0.7, enable_subpixel=False),
        )

        # All should be nodata (no correlation in uniform regions)
        nodata_value = -9999.0
        self.assertTrue(np.all(ncc == nodata_value) or np.all(ncc < 0.7))

    def test_subpixel_fallback_to_integer_on_failure(self):
        from dem_extract.dense_ncc import NCCMatchOptions, dense_ncc_match
        import numpy as np

        left = np.zeros((40, 40), dtype=np.float64)
        left[15:25, 15:25] = 1.0
        right = np.zeros((40, 40), dtype=np.float64)
        right[18:28, 20:30] = 1.0  # shift dy=3, dx=5

        left_cube = self._make_fake_cube(40, 40, left)
        right_cube = self._make_fake_cube(40, 40, right)
        model = self._make_model(dx=5.0, dy=3.0)

        # Subpixel enabled — should succeed
        disp_x, disp_y, ncc = dense_ncc_match(
            left_cube, right_cube, model,
            NCCMatchOptions(window_size=11, search_range=3, ncc_threshold=0.7, enable_subpixel=True),
        )

        center_ncc = ncc[19, 19]
        self.assertGreater(center_ncc, 0.7)

    def test_count_disparity_stats_returns_correct_counts(self):
        from dem_extract.dense_ncc import count_disparity_stats
        import numpy as np

        disp_x = np.array([[1.0, -9999.0], [2.0, 3.0]], dtype=np.float32)
        disp_y = np.array([[1.0, -9999.0], [2.0, 3.0]], dtype=np.float32)
        ncc = np.array([[0.9, -9999.0], [0.5, 0.95]], dtype=np.float32)

        stats = count_disparity_stats(disp_x, disp_y, ncc, ncc_threshold=0.7, nodata_value=-9999.0)

        self.assertEqual(stats["total_pixels"], 4)
        self.assertEqual(stats["matched_count"], 2)  # ncc >= 0.7: (0,0) and (1,1)
        self.assertEqual(stats["failed_match_count"], 2)  # nodata + low ncc
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
python -m unittest tests.unitTest.dem_extract_unit_test.DemExtractDenseNCCUnitTest -v
```

Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement dense_ncc.py**

Create `examples/dem_extract/dense_ncc.py`:

```python
"""Dense per-pixel NCC matching between stereo image pairs.

Author: Geng Xun
Created: 2026-05-10
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .disparity_model import DisparityModel


@dataclass
class NCCMatchOptions:
    window_size: int = 21
    search_range: int = 5
    ncc_threshold: float = 0.70
    enable_subpixel: bool = True
    enable_gruen: bool = False
    chunk_size_lines: int = 100


def _read_cube_data(cube) -> np.ndarray:
    """Read single-band cube data into a 2D numpy array (lines × samples)."""
    return cube.read(band=1)


def _is_valid_pixel(value: float) -> bool:
    """Check if a pixel value is valid (not ISIS special pixel / nodata)."""
    # ISIS null value for float is -3.4028234663852886e+38
    # We also skip exact -9999 nodata and NaN
    import math
    if math.isnan(value):
        return False
    if value <= -3.4028234663852886e+38:
        return False
    return True


def _compute_ncc_score(pattern: np.ndarray, search_region: np.ndarray) -> tuple[float, int, int]:
    """Compute NCC between pattern and all positions in search_region.

    Returns (best_ncc, best_offset_y, best_offset_x) where offsets are relative
    to the search_region center (0 means center position).
    """
    ph, pw = pattern.shape
    sh, sw = search_region.shape

    if sh < ph or sw < pw:
        return float("-inf"), 0, 0

    # Normalize pattern
    pattern_mean = np.mean(pattern)
    pattern_std = np.std(pattern)
    if pattern_std < 1e-10:
        return float("-inf"), 0, 0

    pattern_norm = (pattern - pattern_mean) / pattern_std

    # Slide window over search region, compute NCC at each position
    max_ncc = float("-inf")
    best_oy, best_ox = 0, 0

    for oy in range(sh - ph + 1):
        for ox in range(sw - pw + 1):
            window = search_region[oy:oy + ph, ox:ox + pw]
            win_mean = np.mean(window)
            win_std = np.std(window)
            if win_std < 1e-10:
                continue
            win_norm = (window - win_mean) / win_std
            ncc = float(np.sum(pattern_norm * win_norm) / (ph * pw))
            if ncc > max_ncc:
                max_ncc = ncc
                best_oy = oy
                best_ox = ox

    # Convert to offset relative to search region center
    center_oy = (sh - ph) // 2
    center_ox = (sw - pw) // 2
    best_oy -= center_oy
    best_ox -= center_ox

    return max_ncc, best_oy, best_ox


def _subpixel_refine(pattern: np.ndarray, search_region: np.ndarray,
                     best_oy: int, best_ox: int) -> tuple[float, float, float]:
    """Parabolic subpixel refinement around the integer best position.

    Returns (subpixel_oy, subpixel_ox, refined_ncc).
    """
    ph, pw = pattern.shape
    sh, sw = search_region.shape

    def ncc_at(oy: int, ox: int) -> float:
        if oy < 0 or ox < 0 or oy + ph > sh or ox + pw > sw:
            return float("-inf")
        window = search_region[oy:oy + ph, ox:ox + pw]
        p_mean = np.mean(pattern)
        p_std = np.std(pattern)
        w_mean = np.mean(window)
        w_std = np.std(window)
        if p_std < 1e-10 or w_std < 1e-10:
            return float("-inf")
        return float(np.sum((pattern - p_mean) * (window - w_mean)) / (ph * pw * p_std * w_std))

    center_oy = (sh - ph) // 2
    center_ox = (sw - pw) // 2

    # Get 3x3 NCC scores around best position
    scores = {}
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            oy = best_oy + dy
            ox = best_ox + dx
            scores[(dy, dx)] = ncc_at(oy, ox)

    # Parabolic fit in X
    fx_left = scores.get((-1, 0), float("-inf"))
    fx_center = scores.get((0, 0), float("-inf"))
    fx_right = scores.get((1, 0), float("-inf"))

    dx_sub = 0.0
    denom_x = fx_left + fx_right - 2.0 * fx_center
    if abs(denom_x) > 1e-10:
        dx_sub = (fx_left - fx_right) / (2.0 * denom_x)
    dx_sub = max(-0.5, min(0.5, dx_sub))

    # Parabolic fit in Y
    fy_up = scores.get((0, -1), float("-inf"))
    fy_center = scores.get((0, 0), float("-inf"))
    fy_down = scores.get((0, 1), float("-inf"))

    dy_sub = 0.0
    denom_y = fy_up + fy_down - 2.0 * fy_center
    if abs(denom_y) > 1e-10:
        dy_sub = (fy_up - fy_down) / (2.0 * denom_y)
    dy_sub = max(-0.5, min(0.5, dy_sub))

    # Refine NCC at subpixel position (interpolated)
    refined_ncc = fx_center

    subpixel_oy = (best_oy - center_oy) + dy_sub
    subpixel_ox = (best_ox - center_ox) + dx_sub

    return subpixel_oy, subpixel_ox, refined_ncc


def _match_pixel(
    left_data: np.ndarray, right_data: np.ndarray,
    s: int, l: int,
    pred_dx: float, pred_dy: float,
    options: NCCMatchOptions,
) -> tuple[float, float, float]:
    """Match a single pixel. Returns (dx, dy, ncc) or (nodata, nodata, nodata)."""
    nodata = -9999.0
    lines, samples = left_data.shape
    half_w = options.window_size // 2
    sr = options.search_range

    # Skip invalid pixels
    if not _is_valid_pixel(left_data[l, s]):
        return nodata, nodata, nodata

    # Predicted search center in right image
    center_s = int(round(s + pred_dx))
    center_l = int(round(l + pred_dy))

    # Extract left pattern window
    ps = max(0, s - half_w)
    pe = min(samples, s + half_w + 1)
    pl = max(0, l - half_w)
    pe_l = min(lines, l + half_w + 1)
    pattern = left_data[pl:pe_l, ps:pe]

    if pattern.size == 0:
        return nodata, nodata, nodata

    # Extract right search region
    search_s_start = max(0, center_s - half_w - sr)
    search_s_end = min(samples, center_s + half_w + sr + 1)
    search_l_start = max(0, center_l - half_w - sr)
    search_l_end = min(lines, center_l + half_w + sr + 1)

    search_region = right_data[search_l_start:search_l_end, search_s_start:search_s_end]

    if search_region.size == 0:
        return nodata, nodata, nodata

    # Integer pixel matching
    ncc, best_oy, best_ox = _compute_ncc_score(pattern, search_region)

    if ncc < options.ncc_threshold:
        return nodata, nodata, nodata

    # Compute the best match position in right image coordinates
    center_oy = (search_region.shape[0] - pattern.shape[0]) // 2
    center_ox = (search_region.shape[1] - pattern.shape[1]) // 2
    best_match_s = search_s_start + center_ox + best_ox + half_w
    best_match_l = search_l_start + center_oy + best_oy + half_w

    if not options.enable_subpixel:
        dx = float(best_match_s) - s
        dy = float(best_match_l) - l
        return dx, dy, ncc

    # Subpixel refinement
    # Need to handle boundary: search region might not have room for refinement
    # Try parabolic refinement
    int_oy = center_oy + best_oy
    int_ox = center_ox + best_ox

    # For parabolic refinement, we need the NCC values at ±1 pixel offsets
    # Check if we have enough room in the search region
    ph, pw = pattern.shape
    sh, sw = search_region.shape

    can_refine = (
        int_oy >= 1 and int_ox >= 1
        and int_oy + ph + 1 <= sh
        and int_ox + pw + 1 <= sw
    )

    if can_refine:
        sub_oy, sub_ox, refined_ncc = _subpixel_refine(
            pattern, search_region, int_oy, int_ox
        )

        final_s = search_s_start + center_ox + sub_ox + half_w
        final_l = search_l_start + center_oy + sub_oy + half_w

        # Clamp to image bounds
        final_s = max(1.0, min(float(samples - 1), final_s))
        final_l = max(1.0, min(float(lines - 1), final_l))

        dx = final_s - s
        dy = final_l - l
        return dx, dy, refined_ncc

    # Can't refine — keep integer result
    dx = float(best_match_s) - s
    dy = float(best_match_l) - l
    return dx, dy, ncc


def dense_ncc_match(
    left_cube, right_cube,
    model: DisparityModel,
    options: NCCMatchOptions,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-pixel NCC matching.

    Returns (disparity_x, disparity_y, ncc_score) as H×W float32 arrays.
    Failed matches are filled with nodata (-9999.0).
    """
    left_data = _read_cube_data(left_cube)
    right_data = _read_cube_data(right_cube)
    lines, samples = left_data.shape
    nodata = -9999.0

    disp_x = np.full((lines, samples), nodata, dtype=np.float32)
    disp_y = np.full((lines, samples), nodata, dtype=np.float32)
    ncc = np.full((lines, samples), nodata, dtype=np.float32)

    # Process in chunks for memory efficiency
    chunk_size = options.chunk_size_lines
    for start_line in range(0, lines, chunk_size):
        end_line = min(start_line + chunk_size, lines)

        for l in range(start_line, end_line):
            for s in range(samples):
                pred_dx = model.eval_dx(float(s + 1), float(l + 1))  # 1-based ISIS coords
                pred_dy = model.eval_dy(float(s + 1), float(l + 1))

                dx, dy, ncc_val = _match_pixel(
                    left_data, right_data, s, l, pred_dx, pred_dy, options
                )

                disp_x[l, s] = dx
                disp_y[l, s] = dy
                ncc[l, s] = ncc_val

    return disp_x, disp_y, ncc


def count_disparity_stats(
    disparity_x: np.ndarray,
    disparity_y: np.ndarray,
    ncc_score: np.ndarray,
    ncc_threshold: float = 0.70,
    nodata_value: float = -9999.0,
) -> dict[str, int]:
    """Count matching statistics."""
    total = int(disparity_x.size)
    valid_mask = ncc_score >= ncc_threshold
    matched = int(np.sum(valid_mask))
    failed = total - matched
    return {
        "total_pixels": total,
        "matched_count": matched,
        "failed_match_count": failed,
    }


def write_disparity_cube(
    ip, disparity_x: np.ndarray, disparity_y: np.ndarray,
    ncc_score: np.ndarray, output_path: str, nodata_value: float = -9999.0,
) -> None:
    """Write 3-band float32 disparity CUBE with BandBin labels."""
    lines, samples = disparity_x.shape

    cube = ip.Cube()
    cube.set_dimensions(samples, lines, 3)
    cube.set_pixel_type(ip.PixelType.Real)
    cube.create(output_path)

    try:
        # Write BandBin labels
        band_bin = ip.PvlGroup("BandBin")
        band_bin_keywords = [
            ("Name", ["X_Disparity", "Y_Disparity", "NCC_Correlation_Coefficient"]),
        ]
        for i in range(3):
            band_bin.insert(ip.PvlKeyword("Name", band_bin_keywords[0][1][i]))

        cube.put_group(band_bin)

        # Write bands
        for band_idx, band_data in enumerate([disparity_x, disparity_y, ncc_score], start=1):
            for line_idx in range(lines):
                line_manager = ip.LineManager(cube, False)
                if hasattr(line_manager, "set_line"):
                    line_manager.set_line(line_idx + 1, band_idx)
                for sample_idx in range(samples):
                    line_manager[sample_idx] = float(band_data[line_idx, sample_idx])
                cube.write(line_manager)
    finally:
        if hasattr(cube, "close"):
            cube.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
python -m unittest tests.unitTest.dem_extract_unit_test.DemExtractDenseNCCUnitTest -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/dem_extract/dense_ncc.py tests/unitTest/dem_extract_unit_test.py
git commit -m "feat: add dense NCC per-pixel matching with subpixel refinement"
```

---

### Task 4: Dense Triangulation Module

**Files:**
- Create: `examples/dem_extract/dense_triangulation.py`
- Test: `tests/unitTest/dem_extract_unit_test.py` (new test class)

- [ ] **Step 1: Write tests for dense_triangulation**

Add to `tests/unitTest/dem_extract_unit_test.py`:

```python
class DemExtractDenseTriangulationUnitTest(unittest.TestCase):
    def test_dense_triangulate_yields_triangulated_points(self):
        from dem_extract.dense_triangulation import dense_triangulate_from_disparity
        from dem_extract.triangulation import FilterOptions, TriangulatedPoint
        import numpy as np

        class FakeCamera:
            def __init__(self):
                self.calls = []

            def set_image(self, sample, line):
                self.calls.append((sample, line))
                return True

        class FakeCube:
            def __init__(self):
                self._camera = FakeCamera()

            def camera(self):
                return self._camera

            def sample_count(self):
                return 3

            def line_count(self):
                return 2

        class FakeStereo:
            values = [
                (True, 3396190.0, 12.0, 34.0, 5.0, 2.5),
                (True, 3396190.0, 12.5, 34.5, 5.5, 1.5),
            ]

            @classmethod
            def elevation(cls, left_camera, right_camera):
                return cls.values.pop(0)

            @staticmethod
            def spherical(lat, lon, radius):
                return (1.0, 2.0, 3.0)

        class FakeIp:
            Stereo = FakeStereo

        # 3x2 disparity arrays
        disp_x = np.array([[5.0, -9999.0, 6.0], [7.0, 8.0, -9999.0]], dtype=np.float32)
        disp_y = np.array([[3.0, -9999.0, 4.0], [2.0, 1.0, -9999.0]], dtype=np.float32)
        ncc = np.array([[0.9, -9999.0, 0.8], [0.85, 0.95, -9999.0]], dtype=np.float32)

        points = list(dense_triangulate_from_disparity(
            FakeCube(), FakeCube(), disp_x, disp_y, ncc,
            filters=FilterOptions(), ip=FakeIp,
        ))

        # Only valid (non-nodata, ncc>=0.7) pixels should yield points
        self.assertEqual(len(points), 4)  # 4 valid pixels out of 6
        self.assertTrue(all(isinstance(p, TriangulatedPoint) for p in points))

    def test_dense_triangulate_filters_by_ncc_threshold(self):
        from dem_extract.dense_triangulation import dense_triangulate_from_disparity
        from dem_extract.triangulation import FilterOptions
        import numpy as np

        class FakeCamera:
            def set_image(self, sample, line):
                return True

        class FakeCube:
            def camera(self):
                return FakeCamera()

            def sample_count(self):
                return 2

            def line_count(self):
                return 1

        class FakeStereo:
            @staticmethod
            def elevation(*args):
                return (True, 3396190.0, 12.0, 34.0, 5.0, 2.5)

            @staticmethod
            def spherical(lat, lon, radius):
                return (1.0, 2.0, 3.0)

        class FakeIp:
            Stereo = FakeStereo

        disp_x = np.array([[5.0, 5.0]], dtype=np.float32)
        disp_y = np.array([[3.0, 3.0]], dtype=np.float32)
        ncc = np.array([[0.9, 0.5]], dtype=np.float32)

        points = list(dense_triangulate_from_disparity(
            FakeCube(), FakeCube(), disp_x, disp_y, ncc,
            filters=FilterOptions(), ip=FakeIp,
            ncc_threshold=0.7,
        ))

        # Only the first pixel passes ncc_threshold=0.7
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].index, 0)

    def test_dense_triangulate_applies_filter_options(self):
        from dem_extract.dense_triangulation import dense_triangulate_from_disparity
        from dem_extract.triangulation import FilterOptions
        import numpy as np

        class FakeCamera:
            def set_image(self, sample, line):
                return True

        class FakeCube:
            def camera(self):
                return FakeCamera()

            def sample_count(self):
                return 1

            def line_count(self):
                return 1

        class FakeStereo:
            @staticmethod
            def elevation(*args):
                # High error — should be filtered
                return (True, 3396190.0, 12.0, 34.0, 5.0, 99.0)

            @staticmethod
            def spherical(lat, lon, radius):
                return (1.0, 2.0, 3.0)

        class FakeIp:
            Stereo = FakeStereo

        disp_x = np.array([[5.0]], dtype=np.float32)
        disp_y = np.array([[3.0]], dtype=np.float32)
        ncc = np.array([[0.9]], dtype=np.float32)

        points = list(dense_triangulate_from_disparity(
            FakeCube(), FakeCube(), disp_x, disp_y, ncc,
            filters=FilterOptions(max_error_m=10.0), ip=FakeIp,
        ))

        # Filtered point should not be yielded
        self.assertEqual(len(points), 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
python -m unittest tests.unitTest.dem_extract_unit_test.DemExtractDenseTriangulationUnitTest -v
```

Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement dense_triangulation.py**

Create `examples/dem_extract/dense_triangulation.py`:

```python
"""Triangulate dense disparity maps into 3D points.

Author: Geng Xun
Created: 2026-05-10
"""

from __future__ import annotations

from typing import Iterator

import numpy as np

from .triangulation import FilterOptions, TriangulatedPoint


def dense_triangulate_from_disparity(
    left_cube, right_cube,
    disparity_x: np.ndarray,
    disparity_y: np.ndarray,
    ncc_score: np.ndarray,
    filters: FilterOptions,
    ip,
    ncc_threshold: float = 0.70,
    nodata_value: float = -9999.0,
) -> Iterator[TriangulatedPoint]:
    """Iterate over valid disparity pixels, triangulate each into a TriangulatedPoint.

    Uses iterator pattern for memory efficiency.
    """
    left_camera = left_cube.camera()
    right_camera = right_cube.camera()
    lines, samples = disparity_x.shape

    for l in range(lines):
        for s in range(samples):
            dx = float(disparity_x[l, s])
            dy = float(disparity_y[l, s])
            ncc = float(ncc_score[l, s])

            # Skip nodata and low-NCC pixels
            if ncc < ncc_threshold:
                continue
            if dx <= nodata_value or dy <= nodata_value or ncc <= nodata_value:
                continue

            right_s = (s + 1) + dx   # 1-based ISIS coordinates
            right_l = (l + 1) + dy

            if not left_camera.set_image(s + 1, l + 1):
                continue
            if not right_camera.set_image(right_s, right_l):
                continue

            try:
                success, radius_m, lat, lon, sepang, error = ip.Stereo.elevation(
                    left_camera, right_camera
                )
            except Exception:
                continue

            if not success:
                continue

            # Apply quality filters (reuse logic from triangulation.py)
            reason = _filter_reason(radius_m, sepang, error, filters)
            if reason is not None:
                continue

            x_km, y_km, z_km = ip.Stereo.spherical(lat, lon, radius_m)

            yield TriangulatedPoint(
                index=l * samples + s,
                left_sample=float(s + 1),
                left_line=float(l + 1),
                right_sample=right_s,
                right_line=right_l,
                status="success",
                reason="",
                latitude_deg=lat,
                longitude_deg=lon,
                radius_m=radius_m,
                sepang_deg=sepang,
                intersection_error_m=error,
                x_km=x_km,
                y_km=y_km,
                z_km=z_km,
            )


def _filter_reason(radius_m: float, sepang_deg: float, error_m: float,
                   filters: FilterOptions) -> str | None:
    """Reproduce triangulation.py filter logic."""
    if filters.max_error_m is not None and error_m > filters.max_error_m:
        return "filtered_error"
    if filters.min_sepang_deg is not None and sepang_deg < filters.min_sepang_deg:
        return "filtered_sepang"
    if filters.min_radius_m is not None and radius_m < filters.min_radius_m:
        return "filtered_radius"
    if filters.max_radius_m is not None and radius_m > filters.max_radius_m:
        return "filtered_radius"
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
python -m unittest tests.unitTest.dem_extract_unit_test.DemExtractDenseTriangulationUnitTest -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/dem_extract/dense_triangulation.py tests/unitTest/dem_extract_unit_test.py
git commit -m "feat: add dense triangulation from disparity arrays to TriangulatedPoint iterator"
```

---

### Task 5: Update runtime.py for Dense-NCC Summary Fields

**Files:**
- Modify: `examples/dem_extract/runtime.py`
- Test: Existing tests continue to pass

- [ ] **Step 1: Add `build_dense_ncc_summary` function**

Add to `examples/dem_extract/runtime.py`, after the existing `build_summary` function:

```python
def build_dense_ncc_summary(
    *,
    input_left_cube: str,
    input_right_cube: str,
    input_left_key: str,
    input_right_key: str,
    output_dem_cube: str,
    total_pixels: int,
    matched_count: int,
    failed_match_count: int,
    rasterized_point_count: int,
    filled_cell_count: int,
    value_type: str,
    datum_radius_m: float | None,
    ncc_threshold: float,
    polynomial_order: int,
    dx_r_squared: float,
    dy_r_squared: float,
    key_points_used_for_prior: int,
    prior_fallback: str | None,
    nodata_value: float,
    aggregation: str,
    max_error_m: float | None,
    min_sepang_deg: float | None,
    triangulation_counters: dict[str, int],
) -> dict[str, object]:
    summary: dict[str, object] = {
        "pipeline": "from-dense-ncc",
        "input_left_cube": input_left_cube,
        "input_right_cube": input_right_cube,
        "input_left_key": input_left_key,
        "input_right_key": input_right_key,
        "output_dem_cube": output_dem_cube,
        "total_pixels": total_pixels,
        "matched_count": matched_count,
        "failed_match_count": failed_match_count,
        "rasterized_point_count": rasterized_point_count,
        "filled_cell_count": filled_cell_count,
        "value_type": value_type,
        "datum_radius_m": datum_radius_m,
        "nodata_value": nodata_value,
        "aggregation": aggregation,
        "ncc_threshold": ncc_threshold,
        "polynomial_order": polynomial_order,
        "dx_r_squared": dx_r_squared,
        "dy_r_squared": dy_r_squared,
        "key_points_used_for_prior": key_points_used_for_prior,
        "prior_fallback": prior_fallback,
        "max_error_m": max_error_m,
        "min_sepang_deg": min_sepang_deg,
    }
    for key in ("success_count", "failed_elevation_count"):
        summary[key] = int(triangulation_counters.get(key, 0))
    return summary
```

- [ ] **Step 2: Verify existing tests still pass**

Run:
```bash
python -m unittest tests.unitTest.dem_extract_unit_test.DemExtractRuntimeOutputUnitTest -v
python -m unittest tests.unitTest.dem_extract_unit_test.DemExtractBootstrapUnitTest -v
```

Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git add examples/dem_extract/runtime.py
git commit -m "feat: add build_dense_ncc_summary for dense pipeline reporting"
```

---

### Task 6: Add from-dense-ncc to isis_stereo_dem.py

**Files:**
- Modify: `examples/dem_extract/isis_stereo_dem.py`

- [ ] **Step 1: Add `from-dense-ncc` argument parser**

Add to `build_argument_parser()` in `isis_stereo_dem.py`, after the `from_key` parser setup:

```python
    from_dense_ncc = subparsers.add_parser(
        "from-dense-ncc",
        help="dense per-pixel NCC matching seeded by sparse KEY priors, then extract DEM",
    )
    from_dense_ncc.add_argument("left_cube")
    from_dense_ncc.add_argument("right_cube")
    from_dense_ncc.add_argument("left_key")
    from_dense_ncc.add_argument("right_key")
    from_dense_ncc.add_argument("output_dem_cube")

    proj_group = from_dense_ncc.add_mutually_exclusive_group(required=True)
    proj_group.add_argument("--map-template-cube", help="Projected cube for DEM grid")
    proj_group.add_argument("--use-left-projection", action="store_true",
                            help="Use left cube projection as DEM grid")

    from_dense_ncc.add_argument("--ncc-window", type=int, default=21, help="NCC window size (odd)")
    from_dense_ncc.add_argument("--ncc-search-range", type=int, default=5, help="Search radius")
    from_dense_ncc.add_argument("--ncc-threshold", type=float, default=0.70, help="NCC threshold")
    from_dense_ncc.add_argument("--no-subpixel", action="store_true", help="Disable subpixel")
    from_dense_ncc.add_argument("--enable-gruen", action="store_true", help="Enable GRUN refinement")
    from_dense_ncc.add_argument("--save-disparity", help="Write disparity CUBE to path")

    from_dense_ncc.add_argument("--value-type", choices=("radius_m", "height_m"), default="radius_m")
    from_dense_ncc.add_argument("--datum-radius-m", type=float)
    from_dense_ncc.add_argument("--aggregation", choices=("median", "mean", "min-error"), default="median")
    from_dense_ncc.add_argument("--nodata-value", type=float, default=-9999.0)
    from_dense_ncc.add_argument("--max-error-m", type=float)
    from_dense_ncc.add_argument("--min-sepang-deg", type=float)
    from_dense_ncc.add_argument("--polynomial-order", type=int, default=2)
    from_dense_ncc.add_argument("--min-key-points", type=int, default=20)
    from_dense_ncc.add_argument("--chunk-size-lines", type=int, default=100)
    from_dense_ncc.add_argument("--point-cloud-output")
    from_dense_ncc.add_argument("--summary-output")
    from_dense_ncc.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR"), default="INFO")
```

- [ ] **Step 2: Add imports for new modules**

At the top of `isis_stereo_dem.py`, in the import block after existing imports:

```python
from dem_extract.disparity_model import DisparityModel, fit_disparity_model
from dem_extract.dense_ncc import (
    NCCMatchOptions, count_disparity_stats, dense_ncc_match, write_disparity_cube,
)
from dem_extract.dense_triangulation import dense_triangulate_from_disparity
from dem_extract.runtime import (
    build_dense_ncc_summary,
    build_summary,
    import_isis_pybind,
    write_point_cloud_csvish,
    write_point_cloud_jsonl,
    write_quality_summary_json,
    write_summary_json,
)
```

Also add to the `__package__ in (None, "")` conditional import block:

```python
    from dem_extract.disparity_model import DisparityModel, fit_disparity_model
    from dem_extract.dense_ncc import (
        NCCMatchOptions, count_disparity_stats, dense_ncc_match, write_disparity_cube,
    )
    from dem_extract.dense_triangulation import dense_triangulate_from_disparity
    from dem_extract.runtime import (
        build_dense_ncc_summary,
        build_summary,
        import_isis_pybind,
        write_point_cloud_csvish,
        write_point_cloud_jsonl,
        write_quality_summary_json,
        write_summary_json,
    )
```

- [ ] **Step 3: Implement `run_from_dense_ncc()`**

Add after `run_from_key()` function:

```python
def run_from_dense_ncc(args: argparse.Namespace) -> dict[str, object]:
    ip = import_isis_pybind()
    left_cube = right_cube = template_cube = None
    try:
        if args.value_type == "height_m" and args.datum_radius_m is None:
            raise ValueError("--datum-radius-m is required when --value-type height_m is selected.")

        left_cube = _open_cube(ip, args.left_cube)
        right_cube = _open_cube(ip, args.right_cube)

        # Read sparse KEY pairs
        left_key_file = read_key_file(args.left_key)
        right_key_file = read_key_file(args.right_key)
        pairs = load_key_point_pairs_from_key_files(left_key_file, right_key_file,
                                                     left_cube=left_cube, right_cube=right_cube)

        # Fit disparity prior model
        model = fit_disparity_model(pairs, order=args.polynomial_order, min_points=args.min_key_points)

        # Dense NCC matching
        options = NCCMatchOptions(
            window_size=args.ncc_window,
            search_range=args.ncc_search_range,
            ncc_threshold=args.ncc_threshold,
            enable_subpixel=not args.no_subpixel,
            enable_gruen=args.enable_gruen,
            chunk_size_lines=args.chunk_size_lines,
        )
        disp_x, disp_y, ncc_score = dense_ncc_match(left_cube, right_cube, model, options)

        # Optional: save disparity CUBE
        if args.save_disparity:
            write_disparity_cube(ip, disp_x, disp_y, ncc_score, args.save_disparity,
                                 nodata_value=args.nodata_value)

        # Determine template cube for grid/projection
        if args.use_left_projection:
            template_cube = left_cube
        else:
            template_cube = _open_cube(ip, args.map_template_cube)

        # Dense triangulation
        filters = FilterOptions(
            max_error_m=args.max_error_m,
            min_sepang_deg=args.min_sepang_deg,
        )
        points_iter = dense_triangulate_from_disparity(
            left_cube, right_cube, disp_x, disp_y, ncc_score,
            filters=filters, ip=ip, ncc_threshold=args.ncc_threshold,
            nodata_value=args.nodata_value,
        )

        # Apply datum radius if needed
        if args.datum_radius_m is not None:
            points_list = apply_datum_radius(points_iter, args.datum_radius_m)
        else:
            points_list = list(points_iter)

        # Rasterize
        raster = rasterize_points(
            points_list, template_cube,
            _template_grid_spec(template_cube, args.nodata_value),
            aggregation=args.aggregation,
            value_field=args.value_type,
        )

        if raster.filled_cell_count == 0:
            raise RuntimeError("No triangulated DEM points survived filtering and rasterization.")

        # Write DEM cube
        write_radius_cube(ip, template_cube, args.output_dem_cube, raster)

        # Sidecar outputs
        if args.point_cloud_output:
            if Path(args.point_cloud_output).suffix.lower() == ".csv":
                write_point_cloud_csvish(args.point_cloud_output, points_list)
            else:
                write_point_cloud_jsonl(args.point_cloud_output, points_list)
        if args.quality_prefix:
            write_quality_summary_json(f"{args.quality_prefix}.summary.json", raster)

        # Counters
        ncc_stats = count_disparity_stats(disp_x, disp_y, ncc_score,
                                          ncc_threshold=args.ncc_threshold,
                                          nodata_value=args.nodata_value)
        triangulation_counters = {
            "success_count": raster.rasterized_point_count,
            "failed_elevation_count": ncc_stats["failed_match_count"],
        }

        summary = build_dense_ncc_summary(
            input_left_cube=args.left_cube,
            input_right_cube=args.right_cube,
            input_left_key=args.left_key,
            input_right_key=args.right_key,
            output_dem_cube=args.output_dem_cube,
            total_pixels=ncc_stats["total_pixels"],
            matched_count=ncc_stats["matched_count"],
            failed_match_count=ncc_stats["failed_match_count"],
            rasterized_point_count=raster.rasterized_point_count,
            filled_cell_count=raster.filled_cell_count,
            value_type=args.value_type,
            datum_radius_m=args.datum_radius_m,
            ncc_threshold=args.ncc_threshold,
            polynomial_order=args.polynomial_order,
            dx_r_squared=model.dx_r_squared,
            dy_r_squared=model.dy_r_squared,
            key_points_used_for_prior=len(pairs),
            prior_fallback=model.prior_fallback,
            nodata_value=args.nodata_value,
            aggregation=args.aggregation,
            max_error_m=args.max_error_m,
            min_sepang_deg=args.min_sepang_deg,
            triangulation_counters=triangulation_counters,
        )
        if args.summary_output:
            write_summary_json(args.summary_output, summary)

        return compact_stdout_payload(
            output_dem_cube=args.output_dem_cube,
            point_cloud_output=args.point_cloud_output,
            summary_output=args.summary_output,
            summary=summary,
        )
    finally:
        _close_cube(template_cube)
        _close_cube(right_cube)
        _close_cube(left_cube)
```

- [ ] **Step 4: Update `main()` to dispatch `from-dense-ncc`**

Modify the `main()` function at the bottom:

```python
def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    if args.command == "from-key":
        print(json.dumps(run_from_key(args), sort_keys=True))
        return 0
    if args.command == "from-dense-ncc":
        print(json.dumps(run_from_dense_ncc(args), sort_keys=True))
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2
```

- [ ] **Step 5: Run CLI help to verify**

Run:
```bash
python examples/dem_extract/isis_stereo_dem.py --help
python examples/dem_extract/isis_stereo_dem.py from-dense-ncc --help
```

Expected: Both commands show help text, `from-dense-ncc` shows all NCC-related options.

- [ ] **Step 6: Commit**

```bash
git add examples/dem_extract/isis_stereo_dem.py
git commit -m "feat: add from-dense-ncc subcommand with full pipeline orchestration"
```

---

### Task 7: Wire from-dense-ncc into dem_pipeline.py

**Files:**
- Modify: `examples/dem_extract/dem_pipeline.py`

- [ ] **Step 1: Add `from-dense-ncc` subparser and `run_from_dense_ncc` dispatch**

Add to `build_argument_parser()`, before the `return parser` line:

```python
    dense_ncc_parser = subparsers.add_parser(
        "from-dense-ncc",
        help="Dense per-pixel NCC matching seeded by sparse KEY priors, then extract DEM.",
    )
    dense_ncc_parser.add_argument("--left-cube", required=True, help="Left original ISIS cube.")
    dense_ncc_parser.add_argument("--right-cube", required=True, help="Right original ISIS cube.")
    dense_ncc_parser.add_argument("--left-key", required=True, help="Left KEY file (sparse priors).")
    dense_ncc_parser.add_argument("--right-key", required=True, help="Right KEY file (sparse priors).")
    dense_ncc_parser.add_argument("--output-dem-cube", required=True, help="Output DEM cube.")

    proj_group = dense_ncc_parser.add_mutually_exclusive_group(required=True)
    proj_group.add_argument("--map-template-cube", help="Projected cube for DEM grid.")
    proj_group.add_argument("--use-left-projection", action="store_true",
                            help="Use left cube projection as DEM grid.")
```

- [ ] **Step 2: Add `run_from_dense_ncc` dispatch in `run_pipeline`**

Modify `run_pipeline()` to handle the new command:

```python
def run_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    payload = _load_json_object(args.config)
    paths = build_pipeline_paths(args)
    ensure_pipeline_directories(paths)
    if args.command == "from-ori-match-dem":
        result = run_from_ori_match(args, payload=payload, paths=paths, mode_name=args.command)
    elif args.command == "from-dom-match":
        result = run_from_dom_match(args, payload=payload, paths=paths)
    elif args.command == "from-dense-ncc":
        result = run_from_dense_ncc_wrapper(args, payload=payload, paths=paths)
    else:
        raise PipelineConfigError(f"Unsupported command: {args.command}")
    ...
```

- [ ] **Step 3: Implement `run_from_dense_ncc_wrapper`**

Add before `run_pipeline()`:

```python
def run_from_dense_ncc_wrapper(
    args: argparse.Namespace, *, payload: Mapping[str, Any], paths: PipelinePaths,
) -> dict[str, Any]:
    dem_opts = dem_options_from_config(payload)
    # Build dense-ncc args in the format expected by isis_stereo_dem.run_from_dense_ncc
    dense_args = argparse.Namespace(
        command="from-dense-ncc",
        left_cube=args.left_cube,
        right_cube=args.right_cube,
        left_key=args.left_key,
        right_key=args.right_key,
        output_dem_cube=str(paths.output_dem_cube),
        map_template_cube=getattr(args, "map_template_cube", None),
        use_left_projection=getattr(args, "use_left_projection", False),
        ncc_window=dem_opts.ncc_window if hasattr(dem_opts, "ncc_window") else 21,
        ncc_search_range=dem_opts.ncc_search_range if hasattr(dem_opts, "ncc_search_range") else 5,
        ncc_threshold=dem_opts.ncc_threshold if hasattr(dem_opts, "ncc_threshold") else 0.70,
        no_subpixel=not (dem_opts.enable_subpixel if hasattr(dem_opts, "enable_subpixel") else True),
        enable_gruen=dem_opts.enable_gruen if hasattr(dem_opts, "enable_gruen") else False,
        save_disparity=None,
        value_type=dem_opts.value_type,
        datum_radius_m=dem_opts.datum_radius_m,
        aggregation=dem_opts.aggregation,
        nodata_value=dem_opts.nodata_value,
        max_error_m=dem_opts.max_error_m,
        min_sepang_deg=dem_opts.min_sepang_deg,
        polynomial_order=dem_opts.polynomial_order if hasattr(dem_opts, "polynomial_order") else 2,
        min_key_points=dem_opts.min_key_points if hasattr(dem_opts, "min_key_points") else 20,
        chunk_size_lines=dem_opts.chunk_size_lines if hasattr(dem_opts, "chunk_size_lines") else 100,
        point_cloud_output=str(paths.point_cloud_output),
        summary_output=str(paths.dem_summary_output),
        log_level="INFO",
    )
    return dict(isis_stereo_dem.run_from_dense_ncc(dense_args))
```

Note: This wrapper needs `DenseNCC` options in `DemOptions`. We need to extend `DemOptions` dataclass:

```python
@dataclass(frozen=True, slots=True)
class DemOptions:
    aggregation: str = "median"
    value_type: str = "radius_m"
    datum_radius_m: float | None = None
    nodata_value: float = -9999.0
    max_error_m: float | None = None
    min_sepang_deg: float | None = None
    min_radius_m: float | None = None
    max_radius_m: float | None = None
    # Dense NCC options
    ncc_window: int = 21
    ncc_search_range: int = 5
    ncc_threshold: float = 0.70
    enable_subpixel: bool = True
    enable_gruen: bool = False
    polynomial_order: int = 2
    min_key_points: int = 20
    chunk_size_lines: int = 100
```

And update `dem_options_from_config` to read the `DenseNCC` section.

- [ ] **Step 4: Add DenseNCC config reading**

Add to `dem_options_from_config`:

```python
def dem_options_from_config(payload: Mapping[str, Any]) -> DemOptions:
    section = _first_section(payload, "DemExtract", "DEMExtract", "dem_extract", "Dem", "DEM")
    dense_section = _first_section(payload, "DenseNCC", "dense_ncc", "dense-ncc", "dense")
    return DemOptions(
        aggregation=str(section.get("aggregation", "median")),
        value_type=str(section.get("value_type", section.get("valueType", "radius_m"))),
        datum_radius_m=_optional_float(section.get("datum_radius_m", section.get("datumRadiusM"))),
        nodata_value=float(section.get("nodata_value", section.get("nodataValue", -9999.0))),
        max_error_m=_optional_float(section.get("max_error_m", section.get("maxErrorM"))),
        min_sepang_deg=_optional_float(section.get("min_sepang_deg", section.get("minSepangDeg"))),
        min_radius_m=_optional_float(section.get("min_radius_m", section.get("minRadiusM"))),
        max_radius_m=_optional_float(section.get("max_radius_m", section.get("maxRadiusM"))),
        ncc_window=int(dense_section.get("window_size", dense_section.get("windowSize", 21))),
        ncc_search_range=int(dense_section.get("search_range", dense_section.get("searchRange", 5))),
        ncc_threshold=float(dense_section.get("ncc_threshold", dense_section.get("nccThreshold", 0.70))),
        enable_subpixel=_coerce_bool(dense_section.get("enable_subpixel", dense_section.get("enableSubpixel", True))),
        enable_gruen=_coerce_bool(dense_section.get("enable_gruen", dense_section.get("enableGruen", False))),
        polynomial_order=int(dense_section.get("polynomial_order", dense_section.get("polynomialOrder", 2))),
        min_key_points=int(dense_section.get("min_key_points", dense_section.get("minKeyPoints", 20))),
        chunk_size_lines=int(dense_section.get("chunk_size_lines", dense_section.get("chunkSizeLines", 100))),
    )
```

- [ ] **Step 5: Commit**

```bash
git add examples/dem_extract/dem_pipeline.py
git commit -m "feat: wire from-dense-ncc into pipeline CLI and config system"
```

---

### Task 8: Update __init__.py and dem_config.example.json

**Files:**
- Modify: `examples/dem_extract/__init__.py`
- Modify: `examples/dem_extract/dem_config.example.json`

- [ ] **Step 1: Update package exports**

Add to `__init__.py` imports:

```python
from .disparity_model import DisparityModel, fit_disparity_model
from .dense_ncc import NCCMatchOptions, count_disparity_stats, dense_ncc_match, write_disparity_cube
from .dense_triangulation import dense_triangulate_from_disparity
```

Add to `__all__`:

```python
    "DisparityModel",
    "NCCMatchOptions",
    "dense_ncc_match",
    "dense_triangulate_from_disparity",
    "fit_disparity_model",
    "write_disparity_cube",
    "count_disparity_stats",
```

- [ ] **Step 2: Update dem_config.example.json**

Add the `DenseNCC` section to the existing config file:

```json
{
  "DemExtract": { ... },
  "KeyRefinement": { ... },
  "ImageMatch": { ... },
  "OriginalImageMatch": { ... },
  "DomImageMatch": { ... },
  "DomToOriginal": { ... },
  "DenseNCC": {
    "window_size": 21,
    "search_range": 5,
    "ncc_threshold": 0.70,
    "enable_subpixel": true,
    "enable_gruen": false,
    "polynomial_order": 2,
    "min_key_points": 20,
    "chunk_size_lines": 100
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add examples/dem_extract/__init__.py examples/dem_extract/dem_config.example.json
git commit -m "feat: export new dense NCC modules and add DenseNCC config section"
```

---

### Task 9: Full Test Suite + CLI Integration Tests

**Files:**
- Modify: `tests/unitTest/dem_extract_unit_test.py`

- [ ] **Step 1: Add CLI integration tests for from-dense-ncc**

Add to `DemExtractCliUnitTest`:

```python
    def test_from_dense_ncc_requires_projection_choice(self):
        from dem_extract.isis_stereo_dem import build_argument_parser

        parser = build_argument_parser()
        # Should fail without --map-template-cube or --use-left-projection
        with self.assertRaises(SystemExit):
            with redirect_stderr(StringIO()):
                parser.parse_args([
                    "from-dense-ncc",
                    "left.cub", "right.cub", "left.key", "right.key", "dem.cub",
                ])

    def test_from_dense_ncc_parses_all_options(self):
        from dem_extract.isis_stereo_dem import build_argument_parser

        parser = build_argument_parser()
        args = parser.parse_args([
            "from-dense-ncc",
            "left.cub", "right.cub", "left.key", "right.key", "dem.cub",
            "--use-left-projection",
            "--ncc-window", "15",
            "--ncc-search-range", "3",
            "--ncc-threshold", "0.75",
            "--no-subpixel",
            "--save-disparity", "disparity.cub",
            "--value-type", "height_m",
            "--datum-radius-m", "3396190",
            "--aggregation", "mean",
            "--nodata-value", "-9999",
            "--polynomial-order", "1",
            "--min-key-points", "10",
            "--chunk-size-lines", "50",
        ])

        self.assertEqual(args.command, "from-dense-ncc")
        self.assertEqual(args.ncc_window, 15)
        self.assertEqual(args.ncc_search_range, 3)
        self.assertEqual(args.ncc_threshold, 0.75)
        self.assertTrue(args.no_subpixel)
        self.assertEqual(args.save_disparity, "disparity.cub")
        self.assertEqual(args.value_type, "height_m")
        self.assertEqual(args.datum_radius_m, 3396190.0)
        self.assertEqual(args.aggregation, "mean")
        self.assertEqual(args.polynomial_order, 1)
        self.assertEqual(args.min_key_points, 10)
        self.assertEqual(args.chunk_size_lines, 50)

    def test_cli_script_help_shows_from_dense_ncc(self):
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "examples" / "dem_extract" / "isis_stereo_dem.py"),
                "--help",
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("from-dense-ncc", result.stdout)
```

- [ ] **Step 2: Add pipeline unit test for from-dense-ncc**

Add to `DemExtractPipelineUnitTest`:

```python
    def test_parser_exposes_from_dense_ncc_alias(self):
        from dem_extract import dem_pipeline

        parser = dem_pipeline.build_argument_parser()
        args = parser.parse_args(
            [
                "from-dense-ncc",
                "--left-cube", "left.cub",
                "--right-cube", "right.cub",
                "--left-key", "left.key",
                "--right-key", "right.key",
                "--output-dem-cube", "dem.cub",
                "--use-left-projection",
            ]
        )

        self.assertEqual(args.command, "from-dense-ncc")
        self.assertEqual(args.left_cube, "left.cub")
        self.assertTrue(args.use_left_projection)

    def test_dem_options_from_config_includes_dense_ncc(self):
        from dem_extract import dem_pipeline

        config_path = self.write_config(
            {
                "DenseNCC": {
                    "window_size": 15,
                    "search_range": 3,
                    "ncc_threshold": 0.75,
                    "enable_subpixel": False,
                    "enable_gruen": True,
                },
            }
        )

        payload = json.loads(config_path.read_text())
        opts = dem_pipeline.dem_options_from_config(payload)

        self.assertEqual(opts.ncc_window, 15)
        self.assertEqual(opts.ncc_search_range, 3)
        self.assertEqual(opts.ncc_threshold, 0.75)
        self.assertFalse(opts.enable_subpixel)
        self.assertTrue(opts.enable_gruen)
```

- [ ] **Step 3: Run the full test suite**

Run:
```bash
python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: All tests PASS (existing + new).

- [ ] **Step 4: Commit**

```bash
git add tests/unitTest/dem_extract_unit_test.py
git commit -m "test: add dense NCC CLI, pipeline, and config tests"
```

---

### Task 10: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run CLI help for both entry points**

```bash
python examples/dem_extract/isis_stereo_dem.py --help
python examples/dem_extract/dem_pipeline.py --help
```

Expected: Both show `from-dense-ncc` in available commands.

- [ ] **Step 2: Run full test suite one final time**

```bash
python -m unittest discover -s tests/unitTest -p 'dem_extract_unit_test.py' -v
```

Expected: All tests PASS.

- [ ] **Step 3: Commit final state**

```bash
git status
```

Verify all changes are staged and committed. No uncommitted changes.
