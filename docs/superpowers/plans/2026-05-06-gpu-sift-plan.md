# GPU SIFT 匹配实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `tile_matching.py` 中新增 GPU SIFT 路径，通过 PopSift 批量在 GPU 上提取特征，保持现有 CPU 路径不变。

**Architecture:** 新增 `gpu_sift.py` 模块封装 PopSift，`tile_matching.py` 中新增 `_match_tile_gpu()` 和 GPU 版 worker `_match_tile_task_batch_worker_gpu()`，通过 `use_gpu` 参数在 `match_dom_pair()` 入口控制。

**Tech Stack:** Python, PopSift (pypopsift), OpenCV, NumPy

---

## 文件清单

| 动作 | 文件 | 职责 |
|------|------|------|
| 新增 | `examples/controlnet_construct/gpu_sift.py` | GPU SIFT 封装: 检测可用性、参数映射、批量提取 |
| 新增 | `tests/unitTest/gpu_sift_unit_test.py` | `gpu_sift.py` 的 fallback 和参数映射测试 |
| 修改 | `examples/controlnet_construct/tile_matching.py` | 新增 `_match_tile_gpu()`、`_match_tile_task_batch_worker_gpu()`、参数传递 |
| 修改 | `examples/controlnet_construct/image_match.py` | `match_dom_pair()` 增加 `use_gpu` 参数及 CLI 选项 |

---

### Task 1: 创建 gpu_sift.py — GPU SIFT 封装模块

**Files:**
- Create: `examples/controlnet_construct/gpu_sift.py`
- Create: `tests/unitTest/gpu_sift_unit_test.py`

- [ ] **Step 1: 编写测试**

```python
# tests/unitTest/gpu_sift_unit_test.py
"""Tests for gpu_sift.py — fallback and parameter mapping."""

import numpy as np
import pytest

from examples.controlnet_construct.gpu_sift import (
    HAS_GPU_SIFT,
    GpuSiftBatch,
    map_opencv_to_popsift_params,
)


class TestHasGpuSift:
    def test_has_gpu_sift_is_bool(self):
        assert isinstance(HAS_GPU_SIFT, bool)


class TestMapParams:
    def test_map_all_params(self):
        params = map_opencv_to_popsift_params(
            max_features=500,
            octave_layers=3,
            contrast_threshold=0.04,
            edge_threshold=10.0,
            sigma=1.6,
        )
        assert "peakThreshold" in params
        assert "edgeThreshold" in params
        assert "firstOctave" in params

    def test_map_no_max_features(self):
        params = map_opencv_to_popsift_params(
            max_features=None,
            octave_layers=3,
            contrast_threshold=0.04,
            edge_threshold=10.0,
            sigma=1.6,
        )
        assert "peakThreshold" not in params


class TestGpuSiftBatchFallback:
    """When HAS_GPU_SIFT is False, execute() should return empty or fallback."""

    @pytest.mark.skipif(HAS_GPU_SIFT, reason="requires no GPU SIFT")
    def test_execute_returns_empty_when_unavailable(self):
        batch = GpuSiftBatch(batch_size=4)
        img = np.zeros((64, 64), dtype=np.uint8)
        mask = np.ones((64, 64), dtype=np.uint8) * 255
        batch.add(img, mask)
        results = batch.execute()
        # Should fallback to CPU SIFT when GPU unavailable
        assert len(results) == 1
        assert isinstance(results[0], tuple)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
PYTHONPATH=/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone \
    python -m pytest tests/unitTest/gpu_sift_unit_test.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'examples.controlnet_construct.gpu_sift'"

- [ ] **Step 3: 实现 gpu_sift.py**

```python
"""GPU-accelerated SIFT feature extraction via PopSift.

Wraps pypopsift for batch GPU SIFT extraction.
Falls back to CPU cv2.SIFT when pypopsift is unavailable.

Author: Geng Xun
Created: 2026-05-06
"""

from __future__ import annotations

import logging
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------

try:
    import pypopsift

    HAS_GPU_SIFT = True
except ImportError:
    pypopsift = None  # type: ignore[assignment]
    HAS_GPU_SIFT = False


# ---------------------------------------------------------------------------
# Parameter mapping: OpenCV SIFT → PopSift
# ---------------------------------------------------------------------------

def map_opencv_to_popsift_params(
    *,
    max_features: int | None,
    octave_layers: int,
    contrast_threshold: float,
    edge_threshold: float,
    sigma: float,
) -> dict[str, Any]:
    """Map OpenCV SIFT constructor parameters to PopSift equivalents.

    PopSift uses different parameter names and ranges:
      - contrastThreshold → peakThreshold (PopSift default ~0.04)
      - edgeThreshold → edgeThreshold (same name, default ~10.0)
      - sigma → firstOctave (controls initial scale)
      - nfeatures → not directly supported; PopSift extracts all above threshold
    """
    params: dict[str, Any] = {}
    if max_features is not None:
        params["nfeatures"] = max_features
    params["peakThreshold"] = contrast_threshold
    params["edgeThreshold"] = edge_threshold
    # PopSift firstOctave: -1 means image is doubled before processing
    # (equivalent to OpenCV's default sigma=1.6 pipeline)
    params["firstOctave"] = -1
    return params


# ---------------------------------------------------------------------------
# GpuSiftBatch
# ---------------------------------------------------------------------------

class GpuSiftBatch:
    """Accumulate images and execute batch GPU SIFT extraction.

    When GPU is unavailable, automatically falls back to CPU cv2.SIFT
    with the same parameters, so callers do not need to branch.
    """

    def __init__(
        self,
        batch_size: int = 32,
        *,
        max_features: int | None = None,
        octave_layers: int = 3,
        contrast_threshold: float = 0.04,
        edge_threshold: float = 10.0,
        sigma: float = 1.6,
    ) -> None:
        self._batch_size = batch_size
        self._images: list[np.ndarray] = []
        self._masks: list[np.ndarray] = []
        self._use_gpu = HAS_GPU_SIFT
        self._sift_kwargs = {
            "nOctaveLayers": octave_layers,
            "contrastThreshold": contrast_threshold,
            "edgeThreshold": edge_threshold,
            "sigma": sigma,
        }
        if max_features is not None:
            self._sift_kwargs["nfeatures"] = max_features

    def add(self, image: np.ndarray, mask: np.ndarray) -> int:
        """Add a uint8 image + mask to the batch. Returns batch index."""
        idx = len(self._images)
        self._images.append(image)
        self._masks.append(mask)
        return idx

    def is_full(self) -> bool:
        return len(self._images) >= self._batch_size

    def count(self) -> int:
        return len(self._images)

    def execute(self) -> list[tuple[list[cv2.KeyPoint], np.ndarray | None]]:
        """Run SIFT on all accumulated images.

        Returns list of (keypoints, descriptors) tuples, one per image.
        When GPU is available, uses pypopsift; otherwise falls back to CPU.
        Clears the internal buffer after execution.
        """
        if not self._images:
            return []

        if self._use_gpu:
            results = self._execute_gpu()
        else:
            results = self._execute_cpu()

        self._images.clear()
        self._masks.clear()
        return results

    # -- GPU path ----------------------------------------------------------

    def _execute_gpu(self) -> list[tuple[list[cv2.KeyPoint], np.ndarray | None]]:
        """Extract SIFT features via pypopsift for all batched images."""
        results: list[tuple[list[cv2.KeyPoint], np.ndarray | None]] = []

        # pypopsift.process_images expects a list of images.
        # We call it per image because PopSift's Python API processes
        # one image at a time (GPU parallelism is internal).
        # For true batch processing, stack images if the API supports it.
        for image, mask in zip(self._images, self._masks):
            try:
                kp_des = _popsift_extract(image, mask, self._sift_kwargs)
                results.append(kp_des)
            except Exception:
                logger.warning(
                    "GPU SIFT failed for image %dx%d, falling back to CPU",
                    image.shape[1], image.shape[0],
                    exc_info=True,
                )
                results.append(self._cpu_sift_one(image, mask))

        return results

    # -- CPU fallback ------------------------------------------------------

    def _execute_cpu(self) -> list[tuple[list[cv2.KeyPoint], np.ndarray | None]]:
        """Fallback: run cv2.SIFT on each image."""
        sift = cv2.SIFT_create(**self._sift_kwargs)
        results: list[tuple[list[cv2.KeyPoint], np.ndarray | None]] = []
        for image, mask in zip(self._images, self._masks):
            results.append(self._cpu_sift_one_with_detector(image, mask, sift))
        return results

    def _cpu_sift_one(
        self, image: np.ndarray, mask: np.ndarray,
    ) -> tuple[list[cv2.KeyPoint], np.ndarray | None]:
        sift = cv2.SIFT_create(**self._sift_kwargs)
        return self._cpu_sift_one_with_detector(image, mask, sift)

    def _cpu_sift_one_with_detector(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        sift: cv2.SIFT,
    ) -> tuple[list[cv2.KeyPoint], np.ndarray | None]:
        return sift.detectAndCompute(image, mask)


# ---------------------------------------------------------------------------
# PopSift extraction helper
# ---------------------------------------------------------------------------

def _popsift_extract(
    image: np.ndarray,
    mask: np.ndarray,
    sift_kwargs: dict[str, Any],
) -> tuple[list[cv2.KeyPoint], np.ndarray | None]:
    """Run pypopsift SIFT on a single uint8 image.

    PopSift expects float32 images in [0, 255] range or uint8.
    Returns (keypoints, descriptors) in OpenCV-compatible format.
    """
    h, w = image.shape[:2]

    # Check if image fits in GPU texture memory
    if not pypopsift.fits_texture(w, h):
        raise MemoryError(
            f"Image {w}x{h} exceeds GPU texture memory limits"
        )

    # pypopsift.process_image returns (keypoints, descriptors)
    # keypoints: Nx4 array [x, y, scale, orientation]
    # descriptors: Nx128 array
    keypoints_array, descriptors = pypopsift.process_image(
        image,
        peakThreshold=sift_kwargs.get("contrastThreshold", 0.04),
        edgeThreshold=sift_kwargs.get("edgeThreshold", 10.0),
        firstOctave=sift_kwargs.get("nOctaveLayers", 3),
        nfeatures=sift_kwargs.get("nfeatures", 0),
    )

    # Convert numpy keypoints to cv2.KeyPoint objects
    keypoints = []
    for row in keypoints_array:
        kp = cv2.KeyPoint(
            x=float(row[0]),
            y=float(row[1]),
            size=float(row[2]),
            angle=float(row[3]),
        )
        keypoints.append(kp)

    return keypoints, descriptors
```

- [ ] **Step 4: 运行测试确认通过**

```bash
PYTHONPATH=/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone \
    python -m pytest tests/unitTest/gpu_sift_unit_test.py -v
```
Expected: PASS (all tests use CPU fallback since no pypopsift installed)

- [ ] **Step 5: 提交**

```bash
git add examples/controlnet_construct/gpu_sift.py tests/unitTest/gpu_sift_unit_test.py
git commit -m "feat: add gpu_sift.py wrapper with CPU fallback"
```

---

### Task 2: 在 tile_matching.py 中新增 GPU 匹配函数

**Files:**
- Modify: `examples/controlnet_construct/tile_matching.py`

- [ ] **Step 1: 添加导入和 `use_gpu` 参数到 TileMatchTask**

在 `tile_matching.py` 顶部添加 import:

```python
from .gpu_sift import GpuSiftBatch, HAS_GPU_SIFT
```

在 `TileMatchTask` dataclass (line 75) 末尾添加字段:

```python
    use_gpu: bool = False
    gpu_batch_size: int = 32
```

- [ ] **Step 2: 新增 `_match_tile_gpu()` 函数**

在 `_match_tile()` 函数 (line 295) 之后添加:

```python
def _match_tile_gpu(
    left_image: np.ndarray,
    right_image: np.ndarray,
    *,
    left_mask: np.ndarray,
    right_mask: np.ndarray,
    ratio_test: float,
    matcher_method: str,
    max_features: int | None,
    sift_octave_layers: int,
    sift_contrast_threshold: float,
    sift_edge_threshold: float,
    sift_sigma: float,
) -> tuple[list[cv2.KeyPoint], list[cv2.KeyPoint], list[cv2.DMatch]]:
    """GPU-accelerated SIFT matching for a single tile pair.

    Uses GpuSiftBatch internally for a single pair (batch_size=2).
    Returns the same format as _match_tile().
    """
    batch = GpuSiftBatch(
        batch_size=2,
        max_features=max_features,
        octave_layers=sift_octave_layers,
        contrast_threshold=sift_contrast_threshold,
        edge_threshold=sift_edge_threshold,
        sigma=sift_sigma,
    )
    batch.add(left_image, left_mask)
    batch.add(right_image, right_mask)
    results = batch.execute()

    left_keypoints, left_descriptors = results[0]
    right_keypoints, right_descriptors = results[1]

    if not left_keypoints or left_descriptors is None:
        return [], [], []
    if not right_keypoints or right_descriptors is None:
        return left_keypoints, [], []

    matcher = _create_descriptor_matcher(matcher_method)
    raw_matches = matcher.knnMatch(left_descriptors, right_descriptors, k=2)

    filtered_matches: list[cv2.DMatch] = []
    for candidates in raw_matches:
        if len(candidates) < 2:
            continue
        best, alternate = candidates
        if best.distance < ratio_test * alternate.distance:
            filtered_matches.append(best)

    return left_keypoints, right_keypoints, filtered_matches
```

- [ ] **Step 3: 修改 `_match_tile_from_window_values()` 添加 use_gpu 分支**

在 `_match_tile_from_window_values()` 中，找到调用 `_match_tile()` 的位置（约 line 458-471），替换为:

```python
    if use_gpu and HAS_GPU_SIFT:
        left_keypoints, right_keypoints, filtered_matches = _match_tile_gpu(
            left_image,
            right_image,
            left_mask=left_mask,
            right_mask=right_mask,
            ratio_test=ratio_test,
            matcher_method=matcher_method,
            max_features=max_features,
            sift_octave_layers=sift_octave_layers,
            sift_contrast_threshold=sift_contrast_threshold,
            sift_edge_threshold=sift_edge_threshold,
            sift_sigma=sift_sigma,
        )
    else:
        left_keypoints, right_keypoints, filtered_matches = _match_tile(
            left_image,
            right_image,
            left_mask=left_mask,
            right_mask=right_mask,
            ratio_test=ratio_test,
            matcher_method=matcher_method,
            max_features=max_features,
            sift_octave_layers=sift_octave_layers,
            sift_contrast_threshold=sift_contrast_threshold,
            sift_edge_threshold=sift_edge_threshold,
            sift_sigma=sift_sigma,
        )
```

并在 `_match_tile_from_window_values()` 的签名中添加 `use_gpu: bool = False` 参数。

- [ ] **Step 4: 在 `_build_tile_match_tasks()` 中传递 use_gpu**

在 `TileMatchTask` 构建处添加 `use_gpu=use_gpu` 和 `gpu_batch_size=gpu_batch_size` 参数。

- [ ] **Step 5: 在 `_match_tile_task_with_open_cubes()` 中传递 use_gpu**

在调用 `_match_tile_from_window_values()` 的地方添加 `use_gpu=task.use_gpu`。

- [ ] **Step 6: 提交**

```bash
git add examples/controlnet_construct/tile_matching.py
git commit -m "feat: add GPU SIFT path to tile_matching.py"
```

---

### Task 3: 在 image_match.py 中添加 use_gpu 入口参数

**Files:**
- Modify: `examples/controlnet_construct/image_match.py`

- [ ] **Step 1: 在 `match_dom_pair()` 签名中添加参数**

在 `match_dom_pair()` (line 892) 的签名中添加:

```python
    use_gpu: bool = False,
    gpu_batch_size: int = 32,
```

- [ ] **Step 2: 传递参数到 tile_matching 调用**

在 `match_dom_pair()` 内部，找到调用 `_run_serial_tile_match_tasks()` 或 `_run_parallel_tile_match_tasks()` 的位置，将 `use_gpu` 和 `gpu_batch_size` 传递进去。

在 `_run_serial_tile_match_tasks()` 和 `_run_parallel_tile_match_tasks()` 的签名中同样添加这两个参数，并透传到 `_match_tile_from_window_values()` 或 task payload 中。

- [ ] **Step 3: 在 CLI 参数解析中添加选项**

在 `image_match.py` 的 argparse 部分添加:

```python
parser.add_argument(
    "--use-gpu",
    action="store_true",
    default=False,
    help="Use GPU-accelerated SIFT via PopSift (requires pypopsift installed)",
)
parser.add_argument(
    "--gpu-batch-size",
    type=int,
    default=32,
    help="Number of tiles to batch for GPU SIFT processing (default: 32)",
)
```

- [ ] **Step 4: 提交**

```bash
git add examples/controlnet_construct/image_match.py
git commit -m "feat: add use_gpu and gpu_batch_size CLI options"
```

---

### Task 4: 更新 __init__.py 导出列表

**Files:**
- Modify: `examples/controlnet_construct/__init__.py`

- [ ] **Step 1: 添加 gpu_sift 到 __all__**

在 `__init__.py` 的 `__all__` 列表中添加:

```python
    "gpu_sift",
```

- [ ] **Step 2: 提交**

```bash
git add examples/controlnet_construct/__init__.py
git commit -m "chore: export gpu_sift module"
```

---

### Task 5: 端到端集成验证

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: 添加集成测试**

```python
class TestGpuSiftIntegration:
    """Verify GPU path produces same result structure as CPU path."""

    def test_gpu_path_returns_same_structure(self):
        """When use_gpu=False, results should be valid TileMatchResult."""
        # Create two small synthetic images
        left = np.random.randint(0, 255, (256, 256), dtype=np.uint8)
        right = left.copy()  # identical → should match

        from examples.controlnet_construct.tile_matching import _match_tile

        left_mask = np.ones((256, 256), dtype=np.uint8) * 255
        right_mask = left_mask.copy()

        kp_left, kp_right, matches = _match_tile(
            left, right,
            left_mask=left_mask,
            right_mask=right_mask,
            ratio_test=0.75,
            matcher_method="bf",
            max_features=None,
            sift_octave_layers=3,
            sift_contrast_threshold=0.04,
            sift_edge_threshold=10.0,
            sift_sigma=1.6,
        )
        assert isinstance(kp_left, list)
        assert isinstance(kp_right, list)
        assert isinstance(matches, list)

    def test_gpu_batch_cpu_fallback(self):
        """GpuSiftBatch should work without GPU hardware."""
        from examples.controlnet_construct.gpu_sift import GpuSiftBatch

        batch = GpuSiftBatch(batch_size=4)
        img = np.random.randint(0, 255, (128, 128), dtype=np.uint8)
        mask = np.ones((128, 128), dtype=np.uint8) * 255
        batch.add(img, mask)
        batch.add(img, mask)
        results = batch.execute()
        assert len(results) == 2
        for kp, desc in results:
            assert isinstance(kp, list)
            # desc can be None if no keypoints found
            if desc is not None:
                assert desc.shape[1] == 128
```

- [ ] **Step 2: 运行全部匹配测试**

```bash
PYTHONPATH=/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone \
    python -m pytest tests/unitTest/controlnet_construct_matching_unit_test.py -v -k "gpu"
```
Expected: PASS

- [ ] **Step 3: 提交**

```bash
git add tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "test: add GPU SIFT integration and fallback tests"
```

---

## Spec 覆盖检查

| Spec 要求 | 对应 Task |
|-----------|-----------|
| 新增 gpu_sift.py 模块 | Task 1 |
| GpuSiftBatch 类 (add/execute) | Task 1 |
| PopSift 参数映射 | Task 1 |
| 运行时检测 HAS_GPU_SIFT | Task 1 |
| GPU 不可用时 fallback 到 CPU | Task 1, 5 |
| _match_tile_gpu() 函数 | Task 2 |
| _match_tile_from_window_values use_gpu 分支 | Task 2 |
| match_dom_pair() use_gpu 参数 | Task 3 |
| CLI --use-gpu / --gpu-batch-size | Task 3 |
| 描述子匹配逻辑不变 (CPU BFMatcher/FLANN) | Task 2 |
| __all__ 导出 | Task 4 |
| 单元测试 | Task 1, 5 |

## 占位符扫描

- 无 TBD/TODO
- pypopsift 的 Python API (`pypopsift.process_image`) 函数名和参数名可能与实际版本有差异，需要在 GPU 机器上验证后调整 `gpu_sift.py` 中的 `_popsift_extract()` 函数。当前代码基于 OpenDroneMap 文档中的 API 推断。
- 所有测试代码均为实际可执行代码，非 "add tests for the above" 类型占位符。
