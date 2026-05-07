# GPU Tile Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a throughput-oriented GPU tile matching pipeline that uses one GPU-owning process for SIFT extraction and descriptor matching, while keeping CPU preprocessing, ratio test/RANSAC compatibility, and safe CPU fallback.

**Architecture:** Add GPU matching primitives and dynamic batch control in `gpu_sift.py`, then introduce a bounded producer/GPU-consumer path in `tile_matching.py`. `image_match.py` exposes dynamic batch settings and reports GPU execution statistics without changing existing CPU defaults.

**Tech Stack:** Python 3.12, OpenCV CUDA (`cv2.cuda.SIFT_create`, `cv2.cuda.DescriptorMatcher_createBFMatcher` when available), NumPy, multiprocessing queues, existing `unittest`/`pytest` tests, `asp360_new` conda environment.

---

## File map

| File | Action | Responsibility |
|---|---|---|
| `examples/controlnet_construct/gpu_sift.py` | Modify | GPU SIFT/matcher primitives, serializable result types, dynamic batch controller, fallback stats |
| `examples/controlnet_construct/tile_matching.py` | Modify | Prepared tile payloads, CPU preparation worker, single GPU-owner pipeline, result reconstruction |
| `examples/controlnet_construct/image_match.py` | Modify | Config/CLI defaults for dynamic batch and GPU stats in summary |
| `examples/controlnet_construct/controlnet_config.example.json` | Modify | Example GPU settings with dynamic batch defaults |
| `tests/unitTest/gpu_sift_unit_test.py` | Modify | Focused tests for GPU matching primitives and dynamic batch controller |
| `tests/unitTest/controlnet_construct_matching_unit_test.py` | Modify | Config parsing, GPU routing, result-shape, and fallback tests |
| `scripts/benchmark_gpu_tile_pipeline.py` | Create | Optional A/B benchmark entrypoint for CPU vs GPU pipeline on the same DOM pair |

---

## Task 1: Add test coverage for GPU matcher primitives and dynamic batch policy

**Files:**
- Modify: `tests/unitTest/gpu_sift_unit_test.py`
- Modify in later task: `examples/controlnet_construct/gpu_sift.py`

- [ ] **Step 1: Add failing tests for serializable GPU match results**

Append these tests to `tests/unitTest/gpu_sift_unit_test.py`:

```python
class TestGpuSiftMatchResult:
    def test_match_result_tracks_cpu_fallback_flag(self):
        result = _gpu_sift_module.GpuSiftMatchResult(
            left_keypoints=[],
            right_keypoints=[],
            matches=[],
            used_gpu=True,
            used_cpu_fallback=False,
            failure_reason=None,
        )

        assert result.used_gpu is True
        assert result.used_cpu_fallback is False
        assert result.failure_reason is None

    def test_match_stats_counts_fallbacks_and_batches(self):
        stats = _gpu_sift_module.GpuSiftStats()
        stats.record_batch(batch_size=4, used_gpu=True)
        stats.record_pair_result(used_cpu_fallback=False)
        stats.record_pair_result(used_cpu_fallback=True)

        assert stats.gpu_batch_count == 1
        assert stats.gpu_pair_count == 2
        assert stats.cpu_fallback_pair_count == 1
        assert stats.batch_size_histogram == {4: 1}
```

- [ ] **Step 2: Add failing tests for dynamic batch controller**

Append:

```python
class TestDynamicBatchController:
    def test_starts_at_initial_batch_and_clamps_to_limits(self):
        controller = _gpu_sift_module.DynamicGpuBatchController(
            initial_batch_size=4,
            min_batch_size=2,
            max_batch_size=16,
        )

        assert controller.current_batch_size == 4

    def test_reduces_batch_after_pressure_signal(self):
        controller = _gpu_sift_module.DynamicGpuBatchController(
            initial_batch_size=8,
            min_batch_size=2,
            max_batch_size=16,
        )

        controller.record_batch(success=True, memory_pressure=True, elapsed_seconds=0.5)

        assert controller.current_batch_size == 4

    def test_increases_batch_after_stable_successes(self):
        controller = _gpu_sift_module.DynamicGpuBatchController(
            initial_batch_size=4,
            min_batch_size=2,
            max_batch_size=16,
            stable_successes_to_grow=2,
        )

        controller.record_batch(success=True, memory_pressure=False, elapsed_seconds=0.5)
        controller.record_batch(success=True, memory_pressure=False, elapsed_seconds=0.5)

        assert controller.current_batch_size == 8
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
conda run -n asp360_new python -m pytest -q tests/unitTest/gpu_sift_unit_test.py
```

Expected: FAIL with missing attributes such as `GpuSiftMatchResult`, `GpuSiftStats`, or `DynamicGpuBatchController`.

- [ ] **Step 4: Commit failing tests**

```bash
git add tests/unitTest/gpu_sift_unit_test.py
git commit -m "test: cover GPU SIFT match stats and dynamic batch policy" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 2: Implement GPU match result types and dynamic batch controller

**Files:**
- Modify: `examples/controlnet_construct/gpu_sift.py`
- Test: `tests/unitTest/gpu_sift_unit_test.py`

- [ ] **Step 1: Add serializable result and stats dataclasses**

Add near the top of `gpu_sift.py`, after `logger = logging.getLogger(__name__)`:

```python
from dataclasses import dataclass, field


@dataclass(slots=True)
class GpuSiftMatchResult:
    left_keypoints: list[cv2.KeyPoint]
    right_keypoints: list[cv2.KeyPoint]
    matches: list[cv2.DMatch]
    used_gpu: bool
    used_cpu_fallback: bool
    failure_reason: str | None = None


@dataclass(slots=True)
class GpuSiftStats:
    gpu_batch_count: int = 0
    gpu_pair_count: int = 0
    cpu_fallback_pair_count: int = 0
    gpu_failure_count: int = 0
    batch_size_histogram: dict[int, int] = field(default_factory=dict)

    def record_batch(self, *, batch_size: int, used_gpu: bool) -> None:
        if used_gpu:
            self.gpu_batch_count += 1
            self.batch_size_histogram[batch_size] = self.batch_size_histogram.get(batch_size, 0) + 1

    def record_pair_result(self, *, used_cpu_fallback: bool) -> None:
        self.gpu_pair_count += 1
        if used_cpu_fallback:
            self.cpu_fallback_pair_count += 1

    def record_gpu_failure(self) -> None:
        self.gpu_failure_count += 1
```

- [ ] **Step 2: Add the dynamic batch controller**

Append below the stats dataclass:

```python
class DynamicGpuBatchController:
    def __init__(
        self,
        *,
        initial_batch_size: int = 4,
        min_batch_size: int = 2,
        max_batch_size: int = 16,
        stable_successes_to_grow: int = 3,
    ) -> None:
        if min_batch_size < 1:
            raise ValueError("min_batch_size must be positive")
        if max_batch_size < min_batch_size:
            raise ValueError("max_batch_size must be >= min_batch_size")
        if initial_batch_size < min_batch_size or initial_batch_size > max_batch_size:
            raise ValueError("initial_batch_size must be within [min_batch_size, max_batch_size]")
        if stable_successes_to_grow < 1:
            raise ValueError("stable_successes_to_grow must be positive")

        self._current_batch_size = initial_batch_size
        self._min_batch_size = min_batch_size
        self._max_batch_size = max_batch_size
        self._stable_successes_to_grow = stable_successes_to_grow
        self._stable_success_count = 0

    @property
    def current_batch_size(self) -> int:
        return self._current_batch_size

    def record_batch(
        self,
        *,
        success: bool,
        memory_pressure: bool,
        elapsed_seconds: float,
    ) -> None:
        if not success or memory_pressure:
            self._current_batch_size = max(self._min_batch_size, self._current_batch_size // 2)
            self._stable_success_count = 0
            return

        self._stable_success_count += 1
        if self._stable_success_count >= self._stable_successes_to_grow:
            self._current_batch_size = min(self._max_batch_size, self._current_batch_size * 2)
            self._stable_success_count = 0
```

- [ ] **Step 3: Run focused tests and verify GREEN**

Run:

```bash
conda run -n asp360_new python -m pytest -q tests/unitTest/gpu_sift_unit_test.py
```

Expected: PASS.

- [ ] **Step 4: Commit implementation**

```bash
git add examples/controlnet_construct/gpu_sift.py tests/unitTest/gpu_sift_unit_test.py
git commit -m "feat: add GPU SIFT stats and dynamic batch control" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 3: Add GPU descriptor matching primitive with CPU fallback

**Files:**
- Modify: `tests/unitTest/gpu_sift_unit_test.py`
- Modify: `examples/controlnet_construct/gpu_sift.py`

- [ ] **Step 1: Write failing tests for pair matching fallback**

Append to `tests/unitTest/gpu_sift_unit_test.py`:

```python
class TestGpuSiftPairMatcher:
    def test_match_pair_returns_cpu_fallback_when_gpu_disabled(self):
        matcher = GpuSiftBatch(
            batch_size=2,
            nfeatures=50,
        )
        matcher._use_gpu = False
        left = np.zeros((96, 96), dtype=np.uint8)
        right = left.copy()
        mask = np.ones((96, 96), dtype=np.uint8) * 255

        result = _gpu_sift_module.match_sift_pair(
            left,
            right,
            left_mask=mask,
            right_mask=mask,
            ratio_test=0.75,
            matcher_method="bf",
            sift_kwargs=matcher._sift_kwargs,
            use_gpu=False,
        )

        assert isinstance(result, _gpu_sift_module.GpuSiftMatchResult)
        assert result.used_gpu is False
        assert result.used_cpu_fallback is True
        assert isinstance(result.left_keypoints, list)
        assert isinstance(result.right_keypoints, list)
        assert isinstance(result.matches, list)
```

- [ ] **Step 2: Run test and verify RED**

Run:

```bash
conda run -n asp360_new python -m pytest -q tests/unitTest/gpu_sift_unit_test.py::TestGpuSiftPairMatcher::test_match_pair_returns_cpu_fallback_when_gpu_disabled
```

Expected: FAIL with `AttributeError: module 'gpu_sift' has no attribute 'match_sift_pair'`.

- [ ] **Step 3: Implement CPU fallback and GPU matcher skeleton**

Append to `gpu_sift.py` after `GpuSiftBatch`:

```python
def _filter_ratio_matches(raw_matches: list[object], ratio_test: float) -> list[cv2.DMatch]:
    filtered_matches: list[cv2.DMatch] = []
    for candidates in raw_matches:
        if len(candidates) < 2:
            continue
        best, alternate = candidates
        if best.distance < ratio_test * alternate.distance:
            filtered_matches.append(best)
    return filtered_matches


def _cpu_match_sift_pair(
    left_image: np.ndarray,
    right_image: np.ndarray,
    *,
    left_mask: np.ndarray,
    right_mask: np.ndarray,
    ratio_test: float,
    matcher_method: str,
    sift_kwargs: dict[str, int | float],
    failure_reason: str | None,
) -> GpuSiftMatchResult:
    sift = cv2.SIFT_create(**sift_kwargs)
    left_keypoints_raw, left_descriptors = sift.detectAndCompute(left_image, left_mask)
    right_keypoints_raw, right_descriptors = sift.detectAndCompute(right_image, right_mask)
    left_keypoints = list(left_keypoints_raw) if left_keypoints_raw else []
    right_keypoints = list(right_keypoints_raw) if right_keypoints_raw else []
    if not left_keypoints or left_descriptors is None or not right_keypoints or right_descriptors is None:
        return GpuSiftMatchResult(
            left_keypoints=left_keypoints,
            right_keypoints=right_keypoints,
            matches=[],
            used_gpu=False,
            used_cpu_fallback=True,
            failure_reason=failure_reason,
        )
    matcher = cv2.BFMatcher() if matcher_method == "bf" else cv2.FlannBasedMatcher(
        {"algorithm": 1, "trees": 5},
        {"checks": 50},
    )
    raw_matches = matcher.knnMatch(left_descriptors, right_descriptors, k=2)
    return GpuSiftMatchResult(
        left_keypoints=left_keypoints,
        right_keypoints=right_keypoints,
        matches=_filter_ratio_matches(raw_matches, ratio_test),
        used_gpu=False,
        used_cpu_fallback=True,
        failure_reason=failure_reason,
    )


def match_sift_pair(
    left_image: np.ndarray,
    right_image: np.ndarray,
    *,
    left_mask: np.ndarray,
    right_mask: np.ndarray,
    ratio_test: float,
    matcher_method: str,
    sift_kwargs: dict[str, int | float],
    use_gpu: bool = True,
) -> GpuSiftMatchResult:
    if not use_gpu or not HAS_GPU_SIFT:
        return _cpu_match_sift_pair(
            left_image,
            right_image,
            left_mask=left_mask,
            right_mask=right_mask,
            ratio_test=ratio_test,
            matcher_method=matcher_method,
            sift_kwargs=sift_kwargs,
            failure_reason=None if use_gpu else "gpu_disabled",
        )

    try:
        sift = cv2.cuda.SIFT_create(**sift_kwargs)
        gpu_left = cv2.cuda_GpuMat()
        gpu_right = cv2.cuda_GpuMat()
        gpu_left_mask = cv2.cuda_GpuMat()
        gpu_right_mask = cv2.cuda_GpuMat()
        gpu_left.upload(left_image)
        gpu_right.upload(right_image)
        gpu_left_mask.upload(left_mask)
        gpu_right_mask.upload(right_mask)
        left_keypoints, left_descriptors = sift.detectAndCompute(gpu_left, gpu_left_mask)
        right_keypoints, right_descriptors = sift.detectAndCompute(gpu_right, gpu_right_mask)
        if left_descriptors is None or right_descriptors is None:
            return GpuSiftMatchResult(
                left_keypoints=list(left_keypoints) if left_keypoints else [],
                right_keypoints=list(right_keypoints) if right_keypoints else [],
                matches=[],
                used_gpu=True,
                used_cpu_fallback=False,
                failure_reason=None,
            )
        matcher = cv2.cuda.DescriptorMatcher_createBFMatcher(cv2.NORM_L2)
        raw_gpu_matches = matcher.knnMatch(left_descriptors, right_descriptors, k=2)
        return GpuSiftMatchResult(
            left_keypoints=list(left_keypoints) if left_keypoints else [],
            right_keypoints=list(right_keypoints) if right_keypoints else [],
            matches=_filter_ratio_matches(raw_gpu_matches, ratio_test),
            used_gpu=True,
            used_cpu_fallback=False,
            failure_reason=None,
        )
    except cv2.error as exc:
        logger.warning("GPU SIFT pair matching failed, falling back to CPU", exc_info=True)
        return _cpu_match_sift_pair(
            left_image,
            right_image,
            left_mask=left_mask,
            right_mask=right_mask,
            ratio_test=ratio_test,
            matcher_method=matcher_method,
            sift_kwargs=sift_kwargs,
            failure_reason=str(exc),
        )
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
conda run -n asp360_new python -m pytest -q tests/unitTest/gpu_sift_unit_test.py
```

Expected: PASS.

- [ ] **Step 5: Commit implementation**

```bash
git add examples/controlnet_construct/gpu_sift.py tests/unitTest/gpu_sift_unit_test.py
git commit -m "feat: add GPU SIFT pair matching primitive" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 4: Route `_match_tile_gpu` through the shared GPU matching primitive

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `examples/controlnet_construct/tile_matching.py`

- [ ] **Step 1: Write failing test that `_match_tile_gpu` delegates to `match_sift_pair`**

Append to `tests/unitTest/controlnet_construct_matching_unit_test.py`:

```python
class TestGpuTileMatchingPath(unittest.TestCase):
    def test_match_tile_gpu_reuses_shared_gpu_sift_pair_matcher(self):
        left = np.zeros((64, 64), dtype=np.uint8)
        right = np.zeros((64, 64), dtype=np.uint8)
        mask = np.ones((64, 64), dtype=np.uint8) * 255
        fake_result = tile_matching.GpuSiftMatchResult(
            left_keypoints=[],
            right_keypoints=[],
            matches=[],
            used_gpu=True,
            used_cpu_fallback=False,
            failure_reason=None,
        )

        with mock.patch.object(tile_matching, "match_sift_pair", return_value=fake_result) as match_mock:
            left_keypoints, right_keypoints, matches = tile_matching._match_tile_gpu(
                left,
                right,
                left_mask=mask,
                right_mask=mask,
                ratio_test=0.75,
                matcher_method="bf",
                max_features=100,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
            )

        self.assertEqual(left_keypoints, [])
        self.assertEqual(right_keypoints, [])
        self.assertEqual(matches, [])
        match_mock.assert_called_once()
        self.assertEqual(match_mock.call_args.kwargs["sift_kwargs"]["nfeatures"], 100)
```

- [ ] **Step 2: Run test and verify RED**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.TestGpuTileMatchingPath.test_match_tile_gpu_reuses_shared_gpu_sift_pair_matcher -v
```

Expected: FAIL because `tile_matching` does not import `GpuSiftMatchResult`/`match_sift_pair`, or `_match_tile_gpu` still constructs `GpuSiftBatch` directly.

- [ ] **Step 3: Update imports**

Change `tile_matching.py` import line:

```python
from .gpu_sift import GpuSiftBatch, HAS_GPU_SIFT
```

to:

```python
from .gpu_sift import GpuSiftBatch, GpuSiftMatchResult, HAS_GPU_SIFT, match_sift_pair
```

- [ ] **Step 4: Replace `_match_tile_gpu` internals**

Replace the body of `_match_tile_gpu` with:

```python
    nfeatures = max_features if max_features is not None else 0
    result = match_sift_pair(
        left_image,
        right_image,
        left_mask=left_mask,
        right_mask=right_mask,
        ratio_test=ratio_test,
        matcher_method=matcher_method,
        sift_kwargs={
            "nfeatures": nfeatures,
            "nOctaveLayers": sift_octave_layers,
            "contrastThreshold": sift_contrast_threshold,
            "edgeThreshold": sift_edge_threshold,
            "sigma": sift_sigma,
        },
        use_gpu=True,
    )
    return result.left_keypoints, result.right_keypoints, result.matches
```

- [ ] **Step 5: Run focused tests and verify GREEN**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.TestGpuTileMatchingPath.test_match_tile_gpu_reuses_shared_gpu_sift_pair_matcher -v
conda run -n asp360_new python -m pytest -q tests/unitTest/gpu_sift_unit_test.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add examples/controlnet_construct/tile_matching.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: reuse GPU SIFT matcher in tile matching" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 5: Add config and CLI for dynamic GPU batch defaults

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `examples/controlnet_construct/image_match.py`
- Modify: `examples/controlnet_construct/controlnet_config.example.json`

- [ ] **Step 1: Add failing config parser test**

Append to the config parser tests in `tests/unitTest/controlnet_construct_matching_unit_test.py`:

```python
    def test_print_image_match_config_default_reads_gpu_dynamic_batch_fields(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "useGpu": True,
                            "gpuBatchSize": 8,
                            "gpuDynamicBatch": True,
                            "gpuMinBatchSize": 2,
                            "gpuMaxBatchSize": 16,
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(image_match.print_image_match_config_default(config_path, "use_gpu"), "1")
            self.assertEqual(image_match.print_image_match_config_default(config_path, "gpu_batch_size"), "8")
            self.assertEqual(image_match.print_image_match_config_default(config_path, "gpu_dynamic_batch"), "1")
            self.assertEqual(image_match.print_image_match_config_default(config_path, "gpu_min_batch_size"), "2")
            self.assertEqual(image_match.print_image_match_config_default(config_path, "gpu_max_batch_size"), "16")
```

- [ ] **Step 2: Run test and verify RED**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_print_image_match_config_default_reads_gpu_dynamic_batch_fields -v
```

Expected: FAIL for missing dynamic GPU fields.

- [ ] **Step 3: Add config field specs**

In `image_match.py`, add these entries after `gpu_batch_size` in `load_image_match_defaults_from_config`:

```python
        (
            "gpu_dynamic_batch",
            ("gpu_dynamic_batch", "gpuDynamicBatch", "GpuDynamicBatch"),
            lambda value: _coerce_config_bool(value, field_name="gpu_dynamic_batch"),
        ),
        (
            "gpu_min_batch_size",
            ("gpu_min_batch_size", "gpuMinBatchSize", "GpuMinBatchSize"),
            lambda value: int(value),
        ),
        (
            "gpu_max_batch_size",
            ("gpu_max_batch_size", "gpuMaxBatchSize", "GpuMaxBatchSize"),
            lambda value: int(value),
        ),
```

- [ ] **Step 4: Add CLI options**

In `image_match.py`, after `--gpu-batch-size`, add:

```python
    parser.add_argument(
        "--gpu-dynamic-batch",
        action="store_true",
        default=True,
        help="Dynamically adjust GPU tile batch size during matching (default: enabled)",
    )
    parser.add_argument(
        "--gpu-min-batch-size",
        type=int,
        default=2,
        help="Minimum dynamic GPU batch size (default: 2)",
    )
    parser.add_argument(
        "--gpu-max-batch-size",
        type=int,
        default=16,
        help="Maximum dynamic GPU batch size for 8GB-class GPUs (default: 16)",
    )
```

- [ ] **Step 5: Update example config**

In `examples/controlnet_construct/controlnet_config.example.json`, keep GPU off by default and use conservative dynamic values:

```json
    "use_gpu": false,
    "gpu_batch_size": 4,
    "gpu_dynamic_batch": true,
    "gpu_min_batch_size": 2,
    "gpu_max_batch_size": 16,
```

- [ ] **Step 6: Run tests and JSON validation**

Run:

```bash
python -m json.tool examples/controlnet_construct/controlnet_config.example.json > /dev/null
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_print_image_match_config_default_reads_gpu_dynamic_batch_fields -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add examples/controlnet_construct/image_match.py examples/controlnet_construct/controlnet_config.example.json tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: add dynamic GPU batch configuration" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 6: Add prepared-tile payloads for GPU pipeline

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `examples/controlnet_construct/tile_matching.py`

- [ ] **Step 1: Add failing test for prepared payload creation**

Append:

```python
class TestGpuPreparedTilePayload(unittest.TestCase):
    def test_prepare_tile_payload_skips_invalid_window_before_gpu(self):
        window = tile_matching.PairedTileWindow(
            local_window=TileWindow(0, 0, 16, 16),
            left_window=TileWindow(0, 0, 16, 16),
            right_window=TileWindow(0, 0, 16, 16),
        )
        left_values = np.zeros((16, 16), dtype=np.float64)
        right_values = np.zeros((16, 16), dtype=np.float64)

        payload_or_result = tile_matching._prepare_gpu_tile_payload_from_values(
            left_values=left_values,
            right_values=right_values,
            local_window=window.local_window,
            left_window=window.left_window,
            right_window=window.right_window,
            minimum_value=None,
            maximum_value=None,
            lower_percent=0.5,
            upper_percent=99.5,
            left_invalid_values=(0.0,),
            right_invalid_values=(0.0,),
            special_pixel_abs_threshold=1.0e300,
            min_valid_pixels=64,
            valid_pixel_percent_threshold=0.05,
            invalid_pixel_radius=1,
        )

        self.assertIsInstance(payload_or_result, tile_matching.TileMatchResult)
        self.assertEqual(payload_or_result.stats.status, "skipped_valid_pixel_ratio_below_threshold")
```

- [ ] **Step 2: Run test and verify RED**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.TestGpuPreparedTilePayload.test_prepare_tile_payload_skips_invalid_window_before_gpu -v
```

Expected: FAIL because `_prepare_gpu_tile_payload_from_values` does not exist.

- [ ] **Step 3: Add dataclass and helper**

In `tile_matching.py`, add after `TileMatchResult`:

```python
@dataclass(frozen=True, slots=True)
class PreparedGpuTilePayload:
    local_window: TileWindow
    left_window: TileWindow
    right_window: TileWindow
    left_image: np.ndarray
    right_image: np.ndarray
    left_mask: np.ndarray
    right_mask: np.ndarray
    left_valid_pixel_count: int
    right_valid_pixel_count: int
    left_valid_pixel_ratio: float
    right_valid_pixel_ratio: float
```

Add helper that mirrors `_match_tile_from_window_values` up to image preparation:

```python
def _prepare_gpu_tile_payload_from_values(
    *,
    left_values: np.ndarray,
    right_values: np.ndarray,
    local_window: TileWindow,
    left_window: TileWindow,
    right_window: TileWindow,
    minimum_value: float | None,
    maximum_value: float | None,
    lower_percent: float,
    upper_percent: float,
    left_invalid_values: tuple[float, ...],
    right_invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    min_valid_pixels: int,
    valid_pixel_percent_threshold: float,
    invalid_pixel_radius: int,
) -> PreparedGpuTilePayload | TileMatchResult:
    left_invalid_mask, _ = summarize_valid_pixels(
        left_values,
        invalid_values=left_invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
    )
    right_invalid_mask, _ = summarize_valid_pixels(
        right_values,
        invalid_values=right_invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
    )
    left_invalid_mask = expand_invalid_mask_for_radius(left_invalid_mask, invalid_pixel_radius=invalid_pixel_radius)
    right_invalid_mask = expand_invalid_mask_for_radius(right_invalid_mask, invalid_pixel_radius=invalid_pixel_radius)
    left_valid_pixel_stats = _stats_from_mask(left_invalid_mask)
    right_valid_pixel_stats = _stats_from_mask(right_invalid_mask)
    if (
        left_valid_pixel_stats.valid_pixel_ratio < valid_pixel_percent_threshold
        or right_valid_pixel_stats.valid_pixel_ratio < valid_pixel_percent_threshold
    ):
        return TileMatchResult(
            stats=TileMatchStats(
                local_start_x=local_window.start_x,
                local_start_y=local_window.start_y,
                width=local_window.width,
                height=local_window.height,
                left_start_x=left_window.start_x,
                left_start_y=left_window.start_y,
                right_start_x=right_window.start_x,
                right_start_y=right_window.start_y,
                left_valid_pixel_count=left_valid_pixel_stats.valid_pixel_count,
                right_valid_pixel_count=right_valid_pixel_stats.valid_pixel_count,
                left_valid_pixel_ratio=left_valid_pixel_stats.valid_pixel_ratio,
                right_valid_pixel_ratio=right_valid_pixel_stats.valid_pixel_ratio,
                left_feature_count=0,
                right_feature_count=0,
                match_count=0,
                status="skipped_valid_pixel_ratio_below_threshold",
            ),
            left_points=(),
            right_points=(),
        )
    left_image, left_mask, left_stats = _prepare_image_for_sift(
        left_values,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        lower_percent=lower_percent,
        upper_percent=upper_percent,
        invalid_values=left_invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
        invalid_mask=left_invalid_mask,
        invalid_pixel_radius=0,
    )
    right_image, right_mask, right_stats = _prepare_image_for_sift(
        right_values,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        lower_percent=lower_percent,
        upper_percent=upper_percent,
        invalid_values=right_invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
        invalid_mask=right_invalid_mask,
        invalid_pixel_radius=0,
    )
    if left_stats.valid_pixel_count < min_valid_pixels or right_stats.valid_pixel_count < min_valid_pixels:
        return TileMatchResult(
            stats=TileMatchStats(
                local_start_x=local_window.start_x,
                local_start_y=local_window.start_y,
                width=local_window.width,
                height=local_window.height,
                left_start_x=left_window.start_x,
                left_start_y=left_window.start_y,
                right_start_x=right_window.start_x,
                right_start_y=right_window.start_y,
                left_valid_pixel_count=left_stats.valid_pixel_count,
                right_valid_pixel_count=right_stats.valid_pixel_count,
                left_valid_pixel_ratio=left_stats.valid_pixel_ratio,
                right_valid_pixel_ratio=right_stats.valid_pixel_ratio,
                left_feature_count=0,
                right_feature_count=0,
                match_count=0,
                status="skipped_insufficient_valid_pixels",
            ),
            left_points=(),
            right_points=(),
        )
    return PreparedGpuTilePayload(
        local_window=local_window,
        left_window=left_window,
        right_window=right_window,
        left_image=left_image,
        right_image=right_image,
        left_mask=left_mask,
        right_mask=right_mask,
        left_valid_pixel_count=left_stats.valid_pixel_count,
        right_valid_pixel_count=right_stats.valid_pixel_count,
        left_valid_pixel_ratio=left_stats.valid_pixel_ratio,
        right_valid_pixel_ratio=right_stats.valid_pixel_ratio,
    )
```

- [ ] **Step 4: Run focused test**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.TestGpuPreparedTilePayload.test_prepare_tile_payload_skips_invalid_window_before_gpu -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/controlnet_construct/tile_matching.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: prepare serializable GPU tile payloads" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 7: Add single GPU-owner pipeline and route `use_gpu=True`

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `examples/controlnet_construct/tile_matching.py`
- Modify: `examples/controlnet_construct/image_match.py`

- [ ] **Step 1: Add failing route test**

Append:

```python
class TestGpuPipelineRouting(unittest.TestCase):
    def test_run_parallel_tasks_uses_gpu_pipeline_when_requested(self):
        tasks = [
            tile_matching.TileMatchTask(
                left_dom_path="left.cub",
                right_dom_path="right.cub",
                band=1,
                paired_window=tile_matching.PairedTileWindow(
                    local_window=TileWindow(0, 0, 16, 16),
                    left_window=TileWindow(0, 0, 16, 16),
                    right_window=TileWindow(0, 0, 16, 16),
                ),
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=64,
                valid_pixel_percent_threshold=0.05,
                invalid_pixel_radius=1,
                ratio_test=0.75,
                matcher_method="bf",
                max_features=100,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                use_gpu=True,
                gpu_batch_size=4,
            )
        ]
        expected = []

        with mock.patch.object(tile_matching, "_run_gpu_tile_match_tasks", return_value=expected) as gpu_mock:
            result = tile_matching._run_parallel_tile_match_tasks(
                tasks,
                max_workers=2,
                show_progress=False,
            )

        self.assertIs(result, expected)
        gpu_mock.assert_called_once()
```

- [ ] **Step 2: Run test and verify RED**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.TestGpuPipelineRouting.test_run_parallel_tasks_uses_gpu_pipeline_when_requested -v
```

Expected: FAIL because `_run_gpu_tile_match_tasks` does not exist or routing is not implemented.

- [ ] **Step 3: Add GPU pipeline helper signature**

In `tile_matching.py`, add:

```python
def _run_gpu_tile_match_tasks(
    tasks: list[TileMatchTask],
    *,
    show_progress: bool = True,
    gpu_dynamic_batch: bool = True,
    gpu_min_batch_size: int = 2,
    gpu_max_batch_size: int = 16,
) -> list[TileMatchResult]:
    if not tasks:
        return []
    results: list[TileMatchResult] = []
    for task in tasks:
        results.append(_match_single_paired_window_worker(task))
    return results
```

This temporary implementation preserves correctness before replacing internals with the bounded queue path in the next task.

- [ ] **Step 4: Route all-GPU task lists**

At the start of `_run_parallel_tile_match_tasks`, before process-pool setup, add:

```python
    if tasks and all(task.use_gpu for task in tasks):
        return _run_gpu_tile_match_tasks(tasks, show_progress=show_progress)
```

- [ ] **Step 5: Run focused test**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.TestGpuPipelineRouting.test_run_parallel_tasks_uses_gpu_pipeline_when_requested -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add examples/controlnet_construct/tile_matching.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: route GPU tile tasks through dedicated pipeline" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 8: Replace temporary GPU pipeline with bounded CPU-prep/GPU-match execution

**Files:**
- Modify: `examples/controlnet_construct/tile_matching.py`
- Test: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Add test for stable result ordering**

Append:

```python
class TestGpuPipelineOrdering(unittest.TestCase):
    def test_order_gpu_results_restores_input_order(self):
        first = tile_matching.TileMatchResult(
            stats=tile_matching.TileMatchStats(0, 0, 16, 16, 0, 0, 0, 0, 16, 16, 1.0, 1.0, 0, 0, 0, "no_features"),
            left_points=(),
            right_points=(),
        )
        second = tile_matching.TileMatchResult(
            stats=tile_matching.TileMatchStats(16, 0, 16, 16, 16, 0, 16, 0, 16, 16, 1.0, 1.0, 0, 0, 0, "no_features"),
            left_points=(),
            right_points=(),
        )

        ordered = tile_matching._order_indexed_tile_results([(1, second), (0, first)])

        self.assertEqual(ordered, [first, second])
```

- [ ] **Step 2: Run test and verify RED**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.TestGpuPipelineOrdering.test_order_gpu_results_restores_input_order -v
```

Expected: FAIL because `_order_indexed_tile_results` does not exist.

- [ ] **Step 3: Add result ordering helper**

Add to `tile_matching.py`:

```python
def _order_indexed_tile_results(indexed_results: list[tuple[int, TileMatchResult]]) -> list[TileMatchResult]:
    return [result for _, result in sorted(indexed_results, key=lambda item: item[0])]
```

- [ ] **Step 4: Replace `_run_gpu_tile_match_tasks` internals with prepared payload path**

Replace `_run_gpu_tile_match_tasks` body with this single-process first version. It prepares tiles in order, batches GPU-capable payloads by `gpu_batch_size`, and preserves correctness before adding multiprocessing queues:

```python
    if not tasks:
        return []
    controller = DynamicGpuBatchController(
        initial_batch_size=tasks[0].gpu_batch_size,
        min_batch_size=gpu_min_batch_size,
        max_batch_size=gpu_max_batch_size,
    ) if gpu_dynamic_batch else None
    indexed_results: list[tuple[int, TileMatchResult]] = []
    pending_payloads: list[tuple[int, TileMatchTask, PreparedGpuTilePayload]] = []

    def flush_pending() -> None:
        nonlocal pending_payloads
        if not pending_payloads:
            return
        for index, task, payload in pending_payloads:
            left_keypoints, right_keypoints, filtered_matches = _match_tile_gpu(
                payload.left_image,
                payload.right_image,
                left_mask=payload.left_mask,
                right_mask=payload.right_mask,
                ratio_test=task.ratio_test,
                matcher_method=task.matcher_method,
                max_features=task.max_features,
                sift_octave_layers=task.sift_octave_layers,
                sift_contrast_threshold=task.sift_contrast_threshold,
                sift_edge_threshold=task.sift_edge_threshold,
                sift_sigma=task.sift_sigma,
            )
            indexed_results.append((
                index,
                _tile_result_from_matches(
                    payload=payload,
                    left_keypoints=left_keypoints,
                    right_keypoints=right_keypoints,
                    filtered_matches=filtered_matches,
                ),
            ))
        if controller is not None:
            controller.record_batch(success=True, memory_pressure=False, elapsed_seconds=0.0)
        pending_payloads = []

    for index, task in enumerate(tasks):
        left_cube = ip.Cube()
        right_cube = ip.Cube()
        left_cube.open(task.left_dom_path, "r")
        right_cube.open(task.right_dom_path, "r")
        try:
            left_values = _read_cube_window(left_cube, task.paired_window.left_window, band=task.band)
            right_values = _read_cube_window(right_cube, task.paired_window.right_window, band=task.band)
            prepared = _prepare_gpu_tile_payload_from_values(
                left_values=left_values,
                right_values=right_values,
                local_window=task.paired_window.local_window,
                left_window=task.paired_window.left_window,
                right_window=task.paired_window.right_window,
                minimum_value=task.minimum_value,
                maximum_value=task.maximum_value,
                lower_percent=task.lower_percent,
                upper_percent=task.upper_percent,
                left_invalid_values=_resolved_invalid_values_for_cube(left_cube, task.invalid_values),
                right_invalid_values=_resolved_invalid_values_for_cube(right_cube, task.invalid_values),
                special_pixel_abs_threshold=task.special_pixel_abs_threshold,
                min_valid_pixels=task.min_valid_pixels,
                valid_pixel_percent_threshold=task.valid_pixel_percent_threshold,
                invalid_pixel_radius=task.invalid_pixel_radius,
            )
        finally:
            if left_cube.is_open():
                left_cube.close()
            if right_cube.is_open():
                right_cube.close()
        if isinstance(prepared, TileMatchResult):
            indexed_results.append((index, prepared))
            continue
        pending_payloads.append((index, task, prepared))
        batch_limit = controller.current_batch_size if controller is not None else task.gpu_batch_size
        if len(pending_payloads) >= batch_limit:
            flush_pending()
    flush_pending()
    return _order_indexed_tile_results(indexed_results)
```

- [ ] **Step 5: Add helper to rebuild TileMatchResult from GPU matches**

Add:

```python
def _tile_result_from_matches(
    *,
    payload: PreparedGpuTilePayload,
    left_keypoints: list[cv2.KeyPoint],
    right_keypoints: list[cv2.KeyPoint],
    filtered_matches: list[cv2.DMatch],
) -> TileMatchResult:
    if not left_keypoints or not right_keypoints:
        status = "no_features"
    elif not filtered_matches:
        status = "no_matches"
    else:
        status = "matched"
    matched_left_points = tuple(
        _keypoint_to_isis_coordinates(left_keypoints[match.queryIdx], payload.left_window)
        for match in filtered_matches
    )
    matched_right_points = tuple(
        _keypoint_to_isis_coordinates(right_keypoints[match.trainIdx], payload.right_window)
        for match in filtered_matches
    )
    return TileMatchResult(
        stats=TileMatchStats(
            local_start_x=payload.local_window.start_x,
            local_start_y=payload.local_window.start_y,
            width=payload.local_window.width,
            height=payload.local_window.height,
            left_start_x=payload.left_window.start_x,
            left_start_y=payload.left_window.start_y,
            right_start_x=payload.right_window.start_x,
            right_start_y=payload.right_window.start_y,
            left_valid_pixel_count=payload.left_valid_pixel_count,
            right_valid_pixel_count=payload.right_valid_pixel_count,
            left_valid_pixel_ratio=payload.left_valid_pixel_ratio,
            right_valid_pixel_ratio=payload.right_valid_pixel_ratio,
            left_feature_count=len(left_keypoints),
            right_feature_count=len(right_keypoints),
            match_count=len(filtered_matches),
            status=status,
        ),
        left_points=matched_left_points,
        right_points=matched_right_points,
    )
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.TestGpuPipelineOrdering.test_order_gpu_results_restores_input_order -v
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.TestGpuPipelineRouting.test_run_parallel_tasks_uses_gpu_pipeline_when_requested -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add examples/controlnet_construct/tile_matching.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: batch GPU tile matching in a dedicated pipeline" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 9: Add GPU summary fields to match output

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify: `examples/controlnet_construct/image_match.py`
- Modify: `examples/controlnet_construct/tile_matching.py`

- [ ] **Step 1: Add summary test**

Append:

```python
class TestGpuSummaryFields(unittest.TestCase):
    def test_gpu_summary_defaults_when_gpu_disabled(self):
        summary = image_match._gpu_execution_summary(
            use_gpu=False,
            gpu_batch_size=4,
            gpu_dynamic_batch=True,
            gpu_min_batch_size=2,
            gpu_max_batch_size=16,
        )

        self.assertEqual(summary["enabled"], False)
        self.assertEqual(summary["batch_size"], 4)
        self.assertEqual(summary["dynamic_batch"], True)
        self.assertEqual(summary["min_batch_size"], 2)
        self.assertEqual(summary["max_batch_size"], 16)
```

- [ ] **Step 2: Run test and verify RED**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.TestGpuSummaryFields.test_gpu_summary_defaults_when_gpu_disabled -v
```

Expected: FAIL because `_gpu_execution_summary` does not exist.

- [ ] **Step 3: Add summary helper**

Add to `image_match.py` near other small summary helpers:

```python
def _gpu_execution_summary(
    *,
    use_gpu: bool,
    gpu_batch_size: int,
    gpu_dynamic_batch: bool,
    gpu_min_batch_size: int,
    gpu_max_batch_size: int,
) -> dict[str, object]:
    return {
        "enabled": bool(use_gpu),
        "batch_size": int(gpu_batch_size),
        "dynamic_batch": bool(gpu_dynamic_batch),
        "min_batch_size": int(gpu_min_batch_size),
        "max_batch_size": int(gpu_max_batch_size),
    }
```

- [ ] **Step 4: Add fields to `match_dom_pair` signature and summary**

Add parameters after `gpu_batch_size`:

```python
    gpu_dynamic_batch: bool = True,
    gpu_min_batch_size: int = 2,
    gpu_max_batch_size: int = 16,
```

Add to the returned summary dict:

```python
            "gpu": _gpu_execution_summary(
                use_gpu=use_gpu,
                gpu_batch_size=gpu_batch_size,
                gpu_dynamic_batch=gpu_dynamic_batch,
                gpu_min_batch_size=gpu_min_batch_size,
                gpu_max_batch_size=gpu_max_batch_size,
            ),
```

- [ ] **Step 5: Pass CLI args into `match_dom_pair`**

In `main`, add:

```python
        gpu_dynamic_batch=args.gpu_dynamic_batch,
        gpu_min_batch_size=args.gpu_min_batch_size,
        gpu_max_batch_size=args.gpu_max_batch_size,
```

- [ ] **Step 6: Run focused test**

Run:

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.TestGpuSummaryFields.test_gpu_summary_defaults_when_gpu_disabled -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add examples/controlnet_construct/image_match.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: report GPU matching configuration in summaries" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 10: Add A/B benchmark script

**Files:**
- Create: `scripts/benchmark_gpu_tile_pipeline.py`

- [ ] **Step 1: Create the benchmark script**

Create `scripts/benchmark_gpu_tile_pipeline.py`:

```python
#!/usr/bin/env python3
"""Compare CPU and GPU DOM tile matching throughput for one image pair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from examples.controlnet_construct.image_match import match_dom_pair


def _run_case(args: argparse.Namespace, *, use_gpu: bool) -> dict[str, object]:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    _, _, summary = match_dom_pair(
        args.left_dom,
        args.right_dom,
        output_dir=output_dir / ("gpu" if use_gpu else "cpu"),
        use_gpu=use_gpu,
        gpu_batch_size=args.gpu_batch_size,
        gpu_dynamic_batch=args.gpu_dynamic_batch,
        gpu_min_batch_size=args.gpu_min_batch_size,
        gpu_max_batch_size=args.gpu_max_batch_size,
        sub_block_size_x=args.tile_size,
        sub_block_size_y=args.tile_size,
        overlap_size_x=args.overlap,
        overlap_size_y=args.overlap,
        max_features=args.max_features,
        write_match_visualization=False,
        omit_tile_details=True,
    )
    elapsed = time.perf_counter() - start
    return {
        "use_gpu": use_gpu,
        "elapsed_seconds": elapsed,
        "matched_tile_count": summary.get("matched_tile_count"),
        "total_match_count": summary.get("total_match_count"),
        "gpu": summary.get("gpu"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left_dom")
    parser.add_argument("right_dom")
    parser.add_argument("--output-dir", default="gpu_tile_benchmark_output")
    parser.add_argument("--tile-size", type=int, default=1024)
    parser.add_argument("--overlap", type=int, default=128)
    parser.add_argument("--max-features", type=int, default=1000)
    parser.add_argument("--gpu-batch-size", type=int, default=4)
    parser.add_argument("--gpu-dynamic-batch", action="store_true", default=True)
    parser.add_argument("--gpu-min-batch-size", type=int, default=2)
    parser.add_argument("--gpu-max-batch-size", type=int, default=16)
    parser.add_argument("--output-json", default=None)
    args = parser.parse_args()

    result = {
        "cpu": _run_case(args, use_gpu=False),
        "gpu": _run_case(args, use_gpu=True),
    }
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run syntax check**

Run:

```bash
python -m py_compile scripts/benchmark_gpu_tile_pipeline.py
```

Expected: PASS with no output.

- [ ] **Step 3: Commit**

```bash
git add scripts/benchmark_gpu_tile_pipeline.py
git commit -m "test: add GPU tile pipeline benchmark script" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Final verification

- [ ] **Step 1: Run focused GPU tests**

```bash
conda run -n asp360_new python -m pytest -q tests/unitTest/gpu_sift_unit_test.py
```

Expected: PASS.

- [ ] **Step 2: Run focused matching tests**

```bash
conda run -n asp360_new python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Expected: PASS.

- [ ] **Step 3: Validate example config**

```bash
python -m json.tool examples/controlnet_construct/controlnet_config.example.json > /dev/null
```

Expected: PASS with no output.

- [ ] **Step 4: On a CUDA SIFT machine, run A/B benchmark**

```bash
conda run -n asp360_new python scripts/benchmark_gpu_tile_pipeline.py left_dom.cub right_dom.cub --tile-size 1024 --gpu-batch-size 4 --gpu-max-batch-size 16 --output-json gpu_tile_benchmark.json
```

Expected: JSON output with CPU and GPU elapsed seconds. GPU should be faster before changing any default to enable GPU automatically.
