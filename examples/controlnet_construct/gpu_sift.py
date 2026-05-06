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
