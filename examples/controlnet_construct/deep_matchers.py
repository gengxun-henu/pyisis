"""Minimal matcher scaffolding for deep matcher methods."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .deep_frontends import normalize_deep_method


class DeepMatcherError(RuntimeError):
    """Raised for unsupported deep matcher operations."""


@dataclass(frozen=True, slots=True)
class DeepMatchResult:
    left_keypoints: tuple[Any, ...] = ()
    right_keypoints: tuple[Any, ...] = ()
    matches: tuple[Any, ...] = ()


class SuperGlueMatcher:
    method = "superglue"

    def __init__(self, *, device: str = "cpu") -> None:
        self.device = device

    def match(self, *, features_left: Any, features_right: Any, device: str = "cpu"):
        _ = device
        left_points = np.asarray((features_left or {}).get("keypoints", np.zeros((0, 2), dtype=np.float32)), dtype=np.float32)
        right_points = np.asarray((features_right or {}).get("keypoints", np.zeros((0, 2), dtype=np.float32)), dtype=np.float32)
        pair_count = int(min(left_points.shape[0], right_points.shape[0]))
        if pair_count <= 0:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)
        scores = np.ones((pair_count,), dtype=np.float32)
        return left_points[:pair_count], right_points[:pair_count], scores


class LightGlueMatcher:
    method = "lightglue"

    def __init__(self, *, device: str = "cpu") -> None:
        self.device = device

    def match(self, *, features_left: Any, features_right: Any, device: str = "cpu"):
        _ = device
        left_points = np.asarray((features_left or {}).get("keypoints", np.zeros((0, 2), dtype=np.float32)), dtype=np.float32)
        right_points = np.asarray((features_right or {}).get("keypoints", np.zeros((0, 2), dtype=np.float32)), dtype=np.float32)
        pair_count = int(min(left_points.shape[0], right_points.shape[0]))
        if pair_count <= 0:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)
        scores = np.ones((pair_count,), dtype=np.float32)
        return left_points[:pair_count], right_points[:pair_count], scores


class LoFTRMatcher:
    method = "loftr"

    def __init__(self, *, device: str = "cpu") -> None:
        self.device = device

    def match(self, *, left_image: Any, right_image: Any, device: str = "cpu"):
        _ = device
        left_array = np.asarray(left_image)
        right_array = np.asarray(right_image)
        if left_array.size == 0 or right_array.size == 0:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)

        if left_array.ndim == 0:
            left_plane = left_array.reshape(1, 1)
        elif left_array.ndim == 1:
            left_plane = left_array.reshape(1, -1)
        elif left_array.ndim == 2:
            left_plane = left_array
        else:
            left_plane = np.mean(left_array, axis=-1)

        if right_array.ndim == 0:
            right_plane = right_array.reshape(1, 1)
        elif right_array.ndim == 1:
            right_plane = right_array.reshape(1, -1)
        elif right_array.ndim == 2:
            right_plane = right_array
        else:
            right_plane = np.mean(right_array, axis=-1)

        left_plane = np.asarray(left_plane, dtype=np.float32)
        right_plane = np.asarray(right_plane, dtype=np.float32)
        overlap_height = int(min(left_plane.shape[0], right_plane.shape[0]))
        overlap_width = int(min(left_plane.shape[1], right_plane.shape[1]))
        if overlap_height <= 0 or overlap_width <= 0:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)

        center_y = (overlap_height - 1) / 2.0
        center_x = (overlap_width - 1) / 2.0
        left_points = np.array([[center_x, center_y]], dtype=np.float32)
        right_points = np.array([[center_x, center_y]], dtype=np.float32)
        scores = np.ones((1,), dtype=np.float32)
        return left_points, right_points, scores


def build_deep_matcher(method: str, *, device: str = "cpu") -> SuperGlueMatcher | LightGlueMatcher | LoFTRMatcher:
    normalized = normalize_deep_method(method)
    if normalized == "superglue":
        return SuperGlueMatcher(device=device)
    if normalized == "lightglue":
        return LightGlueMatcher(device=device)
    if normalized == "loftr":
        return LoFTRMatcher(device=device)
    raise DeepMatcherError(f"Unsupported deep matcher method {method!r}.")
