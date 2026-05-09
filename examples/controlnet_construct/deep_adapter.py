"""Scaffolding adapter for deep matcher method routing."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from .deep_frontends import LoFTRFrontend, SuperPointFrontend, normalize_deep_method, resolve_torch_device
from .deep_matchers import DeepMatchResult, build_deep_matcher


class DeepDependencyError(RuntimeError):
    """Raised when a deep matcher dependency is unavailable."""

    def __init__(self, method: str, reason: str) -> None:
        self.method = str(method).strip().lower()
        self.reason = str(reason).strip()
        super().__init__(f"Deep matcher dependency unavailable for '{self.method}': {self.reason}")


class DeepMatcherAdapter:
    def __init__(self, *, prefer_gpu: bool = True) -> None:
        self._device = resolve_torch_device(prefer_gpu)
        self._superpoint = SuperPointFrontend()
        self._loftr_frontend = LoFTRFrontend()

    def _raise_cross_method_fallback_error(self, requested: str, fallback_to: str) -> None:
        raise RuntimeError(
            "Deep matcher fallback must use the same method: "
            f"requested={requested!r}, fallback_to={fallback_to!r}."
        )

    def resolve_fallback_method(self, *, requested_method: str, fallback_method: str) -> str:
        requested = normalize_deep_method(requested_method)
        fallback = str(fallback_method).strip().lower()
        if fallback != requested:
            self._raise_cross_method_fallback_error(requested, fallback)
        return fallback

    def _match_pair_on_device(
        self,
        *,
        matcher_method: str,
        left_image: Any,
        right_image: Any,
        device: str,
    ) -> DeepMatchResult:
        method = normalize_deep_method(matcher_method)

        if method in ("superglue", "lightglue"):
            features_left = self._superpoint.extract(left_image, device=device)
            features_right = self._superpoint.extract(right_image, device=device)
            matcher = build_deep_matcher(method, device=device)
            left_points, right_points, scores = matcher.match(
                features_left=features_left,
                features_right=features_right,
                device=device,
            )
        else:
            prepared = self._loftr_frontend.prepare(left_image, right_image, device=device)
            matcher = build_deep_matcher(method, device=device)
            left_points, right_points, scores = matcher.match(
                left_image=prepared["left"],
                right_image=prepared["right"],
                device=device,
            )

        left_kps, right_kps, matches = self._normalize_matches(
            left_points=left_points,
            right_points=right_points,
            scores=scores,
        )
        return DeepMatchResult(
            left_keypoints=tuple(left_kps),
            right_keypoints=tuple(right_kps),
            matches=tuple(matches),
        )

    def match_pair(self, *, matcher_method: str, left_image: Any, right_image: Any) -> DeepMatchResult:
        return self._match_pair_on_device(
            matcher_method=matcher_method,
            left_image=left_image,
            right_image=right_image,
            device=self._device,
        )

    def match_pair_with_fallback(
        self,
        *,
        matcher_method: str,
        left_image: Any,
        right_image: Any,
        prefer_gpu: bool,
    ) -> DeepMatchResult:
        method = normalize_deep_method(matcher_method)
        primary_device = resolve_torch_device(prefer_gpu)
        try:
            return self._match_pair_on_device(
                matcher_method=method,
                left_image=left_image,
                right_image=right_image,
                device=primary_device,
            )
        except Exception:
            if not prefer_gpu:
                raise
            fallback_method = self.resolve_fallback_method(requested_method=method, fallback_method=method)
            return self._match_pair_on_device(
                matcher_method=fallback_method,
                left_image=left_image,
                right_image=right_image,
                device=resolve_torch_device(False),
            )

    def _normalize_matches(self, *, left_points: Any, right_points: Any, scores: Any):
        left_array = np.asarray(left_points, dtype=np.float32).reshape(-1, 2)
        right_array = np.asarray(right_points, dtype=np.float32).reshape(-1, 2)
        score_array = np.asarray(scores, dtype=np.float32).reshape(-1)

        pair_count = min(left_array.shape[0], right_array.shape[0], score_array.shape[0])
        if pair_count <= 0:
            return [], [], []

        left_kps = [cv2.KeyPoint(float(point[0]), float(point[1]), 1.0) for point in left_array[:pair_count]]
        right_kps = [cv2.KeyPoint(float(point[0]), float(point[1]), 1.0) for point in right_array[:pair_count]]
        matches = [
            cv2.DMatch(_queryIdx=index, _trainIdx=index, _distance=float(max(0.0, 1.0 - score_array[index])))
            for index in range(pair_count)
        ]
        return left_kps, right_kps, matches
