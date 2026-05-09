"""Minimal frontend helpers for deep matcher scaffolding."""

from __future__ import annotations

import numpy as np


SUPPORTED_DEEP_METHODS = ("superglue", "lightglue", "loftr")


class DeepFrontendError(RuntimeError):
    """Raised when deep frontend setup fails."""


class SuperPointFrontend:
    def extract(self, image, device: str):
        _ = device
        image_array = np.asarray(image)
        if image_array.size == 0:
            keypoints = np.zeros((0, 2), dtype=np.float32)
        else:
            keypoints = np.zeros((0, 2), dtype=np.float32)
        descriptors = np.zeros((keypoints.shape[0], 256), dtype=np.float32)
        return {"keypoints": keypoints, "descriptors": descriptors}


class LoFTRFrontend:
    def prepare(self, left_image, right_image, device: str):
        _ = device
        return {
            "left": np.asarray(left_image),
            "right": np.asarray(right_image),
        }


def normalize_deep_method(method: str) -> str:
    normalized = str(method).strip().lower()
    if normalized not in SUPPORTED_DEEP_METHODS:
        raise DeepFrontendError(f"Unsupported deep matcher method {method!r}. Expected one of {SUPPORTED_DEEP_METHODS}.")
    return normalized


def resolve_torch_device(prefer_gpu: bool) -> str:
    if not prefer_gpu:
        return "cpu"

    try:
        import torch
    except Exception:
        return "cpu"

    if torch.cuda.is_available():
        return "cuda"
    return "cpu"
