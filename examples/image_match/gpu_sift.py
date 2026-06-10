"""GPU-accelerated SIFT feature extraction and BF matching.

Uses OpenCV CUDA SIFT when available, otherwise LightGlue's pycolmap CUDA SIFT
frontend with OpenCV CUDA BF matching. Falls back to CPU cv2.SIFT when CUDA is
unavailable.

Author: Geng Xun
Created: 2026-05-06
Updated: 2026-06-09  Geng Xun added LightGlue CUDA SIFT extraction with OpenCV CUDA BF matching.
"""

from __future__ import annotations

import logging
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_SUPPORTED_MATCHER_METHODS = {"bf", "flann"}
DEFAULT_GPU_BATCH_SIZE = 4


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

def _has_cuda_bf_matcher() -> bool:
    try:
        return (
            cv2.cuda.getCudaEnabledDeviceCount() > 0
            and hasattr(cv2.cuda, "DescriptorMatcher_createBFMatcher")
        )
    except Exception:
        return False


def _has_opencv_cuda_sift() -> bool:
    try:
        return cv2.cuda.getCudaEnabledDeviceCount() > 0 and hasattr(cv2.cuda, "SIFT_create")
    except Exception:
        return False


def _has_lightglue_cuda_sift() -> bool:
    try:
        import pycolmap  # type: ignore[import-not-found]
        import torch  # type: ignore[import-not-found]
        from lightglue import SIFT as _LightGlueSIFT  # type: ignore[import-not-found]
    except Exception:
        return False
    return bool(torch.cuda.is_available() and getattr(pycolmap, "has_cuda", False) and _LightGlueSIFT)


HAS_GPU_BF_MATCHER = _has_cuda_bf_matcher()
HAS_GPU_SIFT = _has_opencv_cuda_sift() or (HAS_GPU_BF_MATCHER and _has_lightglue_cuda_sift())


def _lightglue_sift_config(sift_kwargs: dict[str, int | float]) -> dict[str, int | float | str | bool]:
    nfeatures = int(sift_kwargs.get("nfeatures", 0) or 0)
    octave_layers = max(1, int(sift_kwargs.get("nOctaveLayers", 3) or 3))
    contrast_threshold = float(sift_kwargs.get("contrastThreshold", 0.04))
    return {
        "backend": "pycolmap_cuda",
        "rootsift": False,
        "max_num_keypoints": nfeatures if nfeatures > 0 else 4096,
        "detection_threshold": contrast_threshold / max(1, octave_layers * 2),
        "edge_threshold": float(sift_kwargs.get("edgeThreshold", 10.0)),
    }


def _extract_lightglue_cuda_sift_one(
    image: np.ndarray,
    mask: np.ndarray | None,
    sift_kwargs: dict[str, int | float],
) -> tuple[list[cv2.KeyPoint], np.ndarray | None]:
    import torch  # type: ignore[import-not-found]
    from lightglue import SIFT as LightGlueSIFT  # type: ignore[import-not-found]

    source_array = np.asarray(image)
    image_array = source_array.astype(np.float32, copy=False)
    scale = 255.0 if source_array.dtype == np.uint8 else float(np.max(np.abs(image_array))) if image_array.size else 0.0
    if scale > 0.0:
        image_array = image_array / scale
    image_tensor = torch.from_numpy(np.ascontiguousarray(image_array))[None, None].to(
        device="cuda",
        dtype=torch.float32,
    )

    extractor = LightGlueSIFT(**_lightglue_sift_config(sift_kwargs)).eval().to("cuda")
    with torch.no_grad():
        features = extractor.extract(image_tensor)

    keypoint_array = features["keypoints"][0].detach().cpu().numpy().astype(np.float32, copy=False)
    descriptor_array = features["descriptors"][0].detach().cpu().numpy().astype(np.float32, copy=False)
    scale_array = features.get("scales")
    if scale_array is not None:
        scales = scale_array[0].detach().cpu().numpy().astype(np.float32, copy=False)
    else:
        scales = np.ones((len(keypoint_array),), dtype=np.float32)

    if mask is not None and len(keypoint_array) > 0:
        mask_array = np.asarray(mask)
        rounded = np.rint(keypoint_array).astype(np.int64, copy=False)
        valid = (
            (rounded[:, 0] >= 0)
            & (rounded[:, 0] < mask_array.shape[1])
            & (rounded[:, 1] >= 0)
            & (rounded[:, 1] < mask_array.shape[0])
        )
        valid_indices = np.flatnonzero(valid)
        if len(valid_indices) > 0:
            rounded_valid = rounded[valid_indices]
            mask_valid = mask_array[rounded_valid[:, 1], rounded_valid[:, 0]] != 0
            valid_indices = valid_indices[mask_valid]
        keypoint_array = keypoint_array[valid_indices]
        descriptor_array = descriptor_array[valid_indices]
        scales = scales[valid_indices]

    keypoints = [
        cv2.KeyPoint(float(x), float(y), float(max(size, 1.0)))
        for (x, y), size in zip(keypoint_array, scales, strict=True)
    ]
    if len(keypoints) == 0:
        return [], None
    return keypoints, np.ascontiguousarray(descriptor_array, dtype=np.float32)


def _cuda_bf_knn_match(
    left_descriptors: np.ndarray,
    right_descriptors: np.ndarray,
    *,
    matcher: Any | None = None,
) -> list[object]:
    gpu_left_descriptors = cv2.cuda_GpuMat()
    gpu_right_descriptors = cv2.cuda_GpuMat()
    gpu_left_descriptors.upload(np.ascontiguousarray(left_descriptors, dtype=np.float32))
    gpu_right_descriptors.upload(np.ascontiguousarray(right_descriptors, dtype=np.float32))
    cuda_matcher = matcher or cv2.cuda.DescriptorMatcher_createBFMatcher(cv2.NORM_L2)
    return cuda_matcher.knnMatch(gpu_left_descriptors, gpu_right_descriptors, k=2)


class GpuSiftBatch:
    """Accumulate images and execute batch GPU SIFT extraction."""

    def __init__(
        self,
        batch_size: int = DEFAULT_GPU_BATCH_SIZE,
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
        idx = len(self._images)
        self._images.append(image)
        self._masks.append(mask)
        return idx

    def is_full(self) -> bool:
        return len(self._images) >= self._batch_size

    def count(self) -> int:
        return len(self._images)

    def execute(self) -> list[tuple[list[cv2.KeyPoint], np.ndarray | None]]:
        if not self._images:
            return []

        if self._use_gpu:
            results = self._execute_gpu()
        else:
            results = self._execute_cpu()

        self._images.clear()
        self._masks.clear()
        return results

    def _execute_gpu(self) -> list[tuple[list[cv2.KeyPoint], np.ndarray | None]]:
        results: list[tuple[list[cv2.KeyPoint], np.ndarray | None]] = []
        sift = cv2.cuda.SIFT_create(**self._sift_kwargs) if hasattr(cv2.cuda, "SIFT_create") else None

        for image, mask in zip(self._images, self._masks):
            try:
                if sift is None:
                    results.append(_extract_lightglue_cuda_sift_one(image, mask, self._sift_kwargs))
                    continue

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

    def _execute_cpu(self) -> list[tuple[list[cv2.KeyPoint], np.ndarray | None]]:
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
        sift = cv2.cuda.SIFT_create(**sift_kwargs) if hasattr(cv2.cuda, "SIFT_create") else None
        matcher = cv2.cuda.DescriptorMatcher_createBFMatcher(cv2.NORM_L2)
        if sift is None:
            left_keypoints, left_descriptors = _extract_lightglue_cuda_sift_one(
                left_image,
                left_mask,
                sift_kwargs,
            )
            right_keypoints, right_descriptors = _extract_lightglue_cuda_sift_one(
                right_image,
                right_mask,
                sift_kwargs,
            )
            if left_descriptors is None or right_descriptors is None:
                return GpuSiftMatchResult(
                    left_keypoints=left_keypoints,
                    right_keypoints=right_keypoints,
                    matches=[],
                    used_gpu=True,
                    used_cpu_fallback=False,
                    failure_reason=None,
                )
            raw_gpu_matches = _cuda_bf_knn_match(left_descriptors, right_descriptors, matcher=matcher)
            return GpuSiftMatchResult(
                left_keypoints=left_keypoints,
                right_keypoints=right_keypoints,
                matches=_filter_ratio_matches(raw_gpu_matches, ratio_test),
                used_gpu=True,
                used_cpu_fallback=False,
                failure_reason=None,
            )

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
        raw_gpu_matches = matcher.knnMatch(left_descriptors, right_descriptors, k=2)
        return GpuSiftMatchResult(
            left_keypoints=list(left_keypoints) if left_keypoints else [],
            right_keypoints=list(right_keypoints) if right_keypoints else [],
            matches=_filter_ratio_matches(raw_gpu_matches, ratio_test),
            used_gpu=True,
            used_cpu_fallback=False,
            failure_reason=None,
        )
    except Exception as exc:
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


def match_sift_pairs(
    pairs: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
    *,
    ratio_test: float,
    matcher_method: str,
    sift_kwargs: dict[str, int | float],
    use_gpu: bool = True,
) -> list[GpuSiftMatchResult]:
    matcher_method = _normalize_matcher_method(matcher_method)
    if not use_gpu or not HAS_GPU_SIFT or matcher_method == "flann":
        failure_reason = None if use_gpu else "gpu_disabled"
        if use_gpu and matcher_method == "flann":
            failure_reason = "gpu_flann_unsupported"
        return [
            _cpu_match_sift_pair(
                left_image,
                right_image,
                left_mask=left_mask,
                right_mask=right_mask,
                ratio_test=ratio_test,
                matcher_method=matcher_method,
                sift_kwargs=sift_kwargs,
                failure_reason=failure_reason,
            )
            for left_image, right_image, left_mask, right_mask in pairs
        ]

    try:
        sift = cv2.cuda.SIFT_create(**sift_kwargs) if hasattr(cv2.cuda, "SIFT_create") else None
        matcher = cv2.cuda.DescriptorMatcher_createBFMatcher(cv2.NORM_L2)
    except Exception as exc:
        logger.warning("GPU SIFT batch setup failed, falling back to CPU", exc_info=True)
        return [
            _cpu_match_sift_pair(
                left_image,
                right_image,
                left_mask=left_mask,
                right_mask=right_mask,
                ratio_test=ratio_test,
                matcher_method=matcher_method,
                sift_kwargs=sift_kwargs,
                failure_reason=str(exc),
            )
            for left_image, right_image, left_mask, right_mask in pairs
        ]

    results: list[GpuSiftMatchResult] = []
    for left_image, right_image, left_mask, right_mask in pairs:
        try:
            if sift is None:
                left_keypoints, left_descriptors = _extract_lightglue_cuda_sift_one(
                    left_image,
                    left_mask,
                    sift_kwargs,
                )
                right_keypoints, right_descriptors = _extract_lightglue_cuda_sift_one(
                    right_image,
                    right_mask,
                    sift_kwargs,
                )
                if left_descriptors is None or right_descriptors is None:
                    results.append(
                        GpuSiftMatchResult(
                            left_keypoints=left_keypoints,
                            right_keypoints=right_keypoints,
                            matches=[],
                            used_gpu=True,
                            used_cpu_fallback=False,
                            failure_reason=None,
                        )
                    )
                    continue
                raw_gpu_matches = _cuda_bf_knn_match(left_descriptors, right_descriptors, matcher=matcher)
                results.append(
                    GpuSiftMatchResult(
                        left_keypoints=left_keypoints,
                        right_keypoints=right_keypoints,
                        matches=_filter_ratio_matches(raw_gpu_matches, ratio_test),
                        used_gpu=True,
                        used_cpu_fallback=False,
                        failure_reason=None,
                    )
                )
                continue

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
                results.append(
                    GpuSiftMatchResult(
                        left_keypoints=list(left_keypoints) if left_keypoints else [],
                        right_keypoints=list(right_keypoints) if right_keypoints else [],
                        matches=[],
                        used_gpu=True,
                        used_cpu_fallback=False,
                        failure_reason=None,
                    )
                )
                continue
            raw_gpu_matches = matcher.knnMatch(left_descriptors, right_descriptors, k=2)
            results.append(
                GpuSiftMatchResult(
                    left_keypoints=list(left_keypoints) if left_keypoints else [],
                    right_keypoints=list(right_keypoints) if right_keypoints else [],
                    matches=_filter_ratio_matches(raw_gpu_matches, ratio_test),
                    used_gpu=True,
                    used_cpu_fallback=False,
                    failure_reason=None,
                )
            )
        except Exception as exc:
            logger.warning("GPU SIFT pair matching failed, falling back to CPU", exc_info=True)
            results.append(
                _cpu_match_sift_pair(
                    left_image,
                    right_image,
                    left_mask=left_mask,
                    right_mask=right_mask,
                    ratio_test=ratio_test,
                    matcher_method=matcher_method,
                    sift_kwargs=sift_kwargs,
                    failure_reason=str(exc),
                )
            )
    return results
