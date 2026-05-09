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
            descriptors = np.zeros((0, 256), dtype=np.float32)
        else:
            if image_array.ndim == 0:
                feature_plane = image_array.reshape(1, 1)
            elif image_array.ndim == 1:
                feature_plane = image_array.reshape(1, -1)
            elif image_array.ndim == 2:
                feature_plane = image_array
            else:
                feature_plane = np.mean(image_array, axis=-1)
            feature_plane = np.asarray(feature_plane, dtype=np.float32)
            height, width = feature_plane.shape[:2]
            center_y = (height - 1) / 2.0
            center_x = (width - 1) / 2.0
            keypoints = np.array([[center_x, center_y]], dtype=np.float32)
            center_value = float(feature_plane[int(round(center_y)), int(round(center_x))])
            descriptors = np.full((1, 256), center_value, dtype=np.float32)
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
