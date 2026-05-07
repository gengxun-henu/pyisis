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

_SUPPORTED_MATCHER_METHODS = {"bf", "flann"}


def _normalize_matcher_method(matcher_method: str) -> str:
    if not isinstance(matcher_method, str):
        raise ValueError("unsupported matcher_method: expected one of bf, flann")
    normalized = matcher_method.strip().lower()
    if normalized not in _SUPPORTED_MATCHER_METHODS:
        raise ValueError(
            f"unsupported matcher_method {matcher_method!r}: expected one of bf, flann"
        )
    return normalized


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
        self._sift_kwargs: dict[str, int | float] = {
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
                gpu_image = cv2.cuda_GpuMat()
                gpu_image.upload(image)

                if mask is not None:
                    gpu_mask = cv2.cuda_GpuMat()
                    gpu_mask.upload(mask)
                else:
                    gpu_mask = None

                keypoints, descriptors = sift.detectAndCompute(
                    gpu_image, gpu_mask
                )

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
        kp, desc = sift.detectAndCompute(image, mask)
        return list(kp) if kp else [], desc


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
    matcher_method = _normalize_matcher_method(matcher_method)
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
    matcher_method = _normalize_matcher_method(matcher_method)
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

    if matcher_method == "flann":
        return _cpu_match_sift_pair(
            left_image,
            right_image,
            left_mask=left_mask,
            right_mask=right_mask,
            ratio_test=ratio_test,
            matcher_method=matcher_method,
            sift_kwargs=sift_kwargs,
            failure_reason="gpu_flann_unsupported",
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
