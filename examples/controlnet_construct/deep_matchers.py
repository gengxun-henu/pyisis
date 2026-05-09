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
        _ = (left_image, right_image, device)
        return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)


def build_deep_matcher(method: str, *, device: str = "cpu") -> SuperGlueMatcher | LightGlueMatcher | LoFTRMatcher:
    normalized = normalize_deep_method(method)
    if normalized == "superglue":
        return SuperGlueMatcher(device=device)
    if normalized == "lightglue":
        return LightGlueMatcher(device=device)
    if normalized == "loftr":
        return LoFTRMatcher(device=device)
    raise DeepMatcherError(f"Unsupported deep matcher method {method!r}.")
