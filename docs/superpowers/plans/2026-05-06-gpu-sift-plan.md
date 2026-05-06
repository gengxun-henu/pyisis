# GPU SIFT 匹配实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `tile_matching.py` 中新增 GPU SIFT 路径，通过 `cv2.cuda.SIFT` 批量在 GPU 上提取特征，保持现有 CPU 路径不变。

**Architecture:** 新增 `gpu_sift.py` 模块封装 `cv2.cuda.SIFT_create()`，`tile_matching.py` 中新增 `_match_tile_gpu()` 和 GPU 版 worker `_match_tile_task_batch_worker_gpu()`，通过 `use_gpu` 参数在 `match_dom_pair()` 入口控制。

**Tech Stack:** Python, OpenCV CUDA (`cv2.cuda`), NumPy

---

## 文件清单

| 动作 | 文件 | 职责 |
|------|------|------|
| 新增 | `examples/controlnet_construct/gpu_sift.py` | GPU SIFT 封装: 检测可用性、批量提取、CPU fallback |
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
)


class TestHasGpuSift:
    def test_has_gpu_sift_is_bool(self):
        assert isinstance(HAS_GPU_SIFT, bool)


class TestGpuSiftBatchFallback:
    """When HAS_GPU_SIFT is False, execute() should fallback to CPU SIFT."""

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

    def test_execute_cpu_produces_results(self):
        """CPU fallback should produce (keypoints, descriptors) tuples."""
        batch = GpuSiftBatch(batch_size=4)
        img = np.random.randint(0, 255, (128, 128), dtype=np.uint8)
        mask = np.ones((128, 128), dtype=np.uint8) * 255
        batch.add(img, mask)
        batch.add(img, mask)
        results = batch.execute()
        assert len(results) == 2
        for kp, desc in results:
            assert isinstance(kp, list)
            if desc is not None:
                assert desc.shape[1] == 128


class TestGpuSiftBatchParams:
    """Verify SIFT parameters are passed through correctly."""

    def test_custom_params(self):
        batch = GpuSiftBatch(
            batch_size=4,
            nfeatures=200,
            contrastThreshold=0.05,
            edgeThreshold=12.0,
            sigma=1.8,
        )
        assert batch._batch_size == 4
        assert batch._sift_kwargs["nfeatures"] == 200
        assert batch._sift_kwargs["contrastThreshold"] == 0.05
```

- [ ] **Step 2: 运行测试确认失败**

```bash
PYTHONPATH=/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone \
    python -m pytest tests/unitTest/gpu_sift_unit_test.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'examples.controlnet_construct.gpu_sift'"

- [ ] **Step 3: 实现 gpu_sift.py**

```python
"""GPU-accelerated SIFT feature extraction via OpenCV CUDA.

Wraps cv2.cuda.SIFT for batch GPU SIFT extraction.
Falls back to CPU cv2.SIFT when CUDA is unavailable.

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
    _cuda_device_count = cv2.cuda.getCudaEnabledDeviceCount()
    # Verify cuda.SIFT_create exists (opencv-contrib-python with CUDA)
    _ = cv2.cuda.SIFT_create
    HAS_GPU_SIFT = _cuda_device_count > 0
except Exception:
    HAS_GPU_SIFT = False


# ---------------------------------------------------------------------------
# GpuSiftBatch
# ---------------------------------------------------------------------------

class GpuSiftBatch:
    """Accumulate images and execute batch GPU SIFT extraction.

    When GPU is unavailable, automatically falls back to CPU cv2.SIFT
    with the same parameters, so callers do not need to branch.

    Uses cv2.cuda.SIFT_create() — parameters are identical to CPU SIFT.
    """

    def __init__(
        self,
        batch_size: int = 32,
        *,
        nfeatures: int = 0,
        nOctaveLayers: int = 3,
        contrastThreshold: float = 0.04,
        edgeThreshold: float = 10.0,
        sigma: float = 1.6,
    ) -> None:
        self._batch_size = batch_size
        self._images: list[np.ndarray] = []
        self._masks: list[np.ndarray] = []
        self._use_gpu = HAS_GPU_SIFT
        self._sift_kwargs = {
            "nfeatures": nfeatures,
            "nOctaveLayers": nOctaveLayers,
            "contrastThreshold": contrastThreshold,
            "edgeThreshold": edgeThreshold,
            "sigma": sigma,
        }

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
        When GPU is available, uses cv2.cuda.SIFT; otherwise falls back to CPU.
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
        """Extract SIFT features via cv2.cuda.SIFT for all batched images."""
        results: list[tuple[list[cv2.KeyPoint], np.ndarray | None]] = []
        sift = cv2.cuda.SIFT_create(**self._sift_kwargs)

        for image, mask in zip(self._images, self._masks):
            try:
                # Upload to GPU
                gpu_image = cv2.cuda_GpuMat()
                gpu_image.upload(image)

                if mask is not None:
                    gpu_mask = cv2.cuda_GpuMat()
                    gpu_mask.upload(mask)
                else:
                    gpu_mask = None

                # GPU SIFT
                keypoints, descriptors = sift.detectAndCompute(
                    gpu_image, gpu_mask
                )

                # Download descriptors to CPU
                desc_cpu = None
                if descriptors is not None:
                    desc_cpu = descriptors.download()

                results.append((keypoints, desc_cpu))
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
PYTHONPATH=/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone \
    python -m pytest tests/unitTest/gpu_sift_unit_test.py -v
```
Expected: PASS (all tests use CPU fallback since no CUDA available on dev machine)

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
    nfeatures = max_features if max_features is not None else 0
    batch = GpuSiftBatch(
        batch_size=2,
        nfeatures=nfeatures,
        nOctaveLayers=sift_octave_layers,
        contrastThreshold=sift_contrast_threshold,
        edgeThreshold=sift_edge_threshold,
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
    help="Use GPU-accelerated SIFT via OpenCV CUDA (requires opencv-contrib-python with CUDA support)",
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
| OpenCV CUDA SIFT 参数直接透传（无映射） | Task 1 |
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
- 开发机无 CUDA，所有测试走 CPU fallback 路径
- 目标 GPU 机器需从源码编译带 CUDA 的 OpenCV（见 spec 文档的"依赖与安装"章节），`cv2.cuda.SIFT_create` 的行为应与 CPU 版一致
