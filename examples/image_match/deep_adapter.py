"""Scaffolding adapter for deep matcher method routing.

Author: Geng Xun
Created: 2026-05-19
Updated: 2026-05-19  Geng Xun added runtime config storage for deep matcher execution.
Updated: 2026-05-19  Geng Xun made feature extractor runtime config explicit for LightGlue and SuperGlue routing.
Updated: 2026-05-19  Geng Xun forwarded matcher/feature/device runtime options into deep matcher construction.
Updated: 2026-05-20  Geng Xun added early runtime-config compatibility checks for deep matcher and extractor pairs.
"""

from __future__ import annotations

import json
from typing import Any

import cv2
import numpy as np

from .deep_frontends import (
    DeepDependencyError,
    DeepFrontendError,
    LoFTRFrontend,
    OfficialLightGlueFrontend,
    SuperPointFrontend,
    normalize_deep_method,
    resolve_torch_device,
)
from .deep_matchers import (
    DeepMatchResult,
    DeepMatcherError,
    OFFICIAL_LIGHTGLUE_FRONTEND_METHODS,
    _default_feature_extractor_for_matcher,
    build_deep_matcher,
)


def _runtime_feature_extractor_method(runtime_config: Any | None, matcher_method: str) -> str:
    configured_method = (
        getattr(runtime_config, "feature_extractor_method", None)
        if runtime_config is not None
        else None
    )
    if configured_method is None:
        return _default_feature_extractor_for_matcher(matcher_method)
    normalized_method = str(configured_method).strip().lower()
    return normalized_method or _default_feature_extractor_for_matcher(matcher_method)


def _runtime_matcher_backend(runtime_config: Any | None) -> str | None:
    if runtime_config is None:
        return None
    matcher_options = getattr(runtime_config, "matcher_options", {}) or {}
    backend_value = matcher_options.get("backend")
    if backend_value is None:
        return None
    normalized_backend = str(backend_value).strip().lower()
    return normalized_backend or None


def _validate_runtime_matcher_compatibility(runtime_config: Any | None) -> None:
    if runtime_config is None:
        return
    matcher_method = str(getattr(runtime_config, "matcher_method", "") or "").strip().lower()
    feature_extractor_method = _runtime_feature_extractor_method(runtime_config, matcher_method)
    backend = _runtime_matcher_backend(runtime_config)
    if matcher_method == "lightglue" and backend == "official":
        if feature_extractor_method in OFFICIAL_LIGHTGLUE_FRONTEND_METHODS:
            return
        supported_display = ", ".join(repr(method) for method in sorted(OFFICIAL_LIGHTGLUE_FRONTEND_METHODS))
        raise ValueError(
            f"matcher.method='lightglue' with backend='official' requires feature_extractor.method to be one of "
            f"({supported_display}); got {feature_extractor_method!r}."
        )
    supported_extractors = {
        "lightglue": ("superpoint",),
        "superglue": ("superpoint",),
        "loftr": ("loftr",),
    }.get(matcher_method)
    if supported_extractors is None or feature_extractor_method in supported_extractors:
        return
    supported_display = ", ".join(repr(method) for method in supported_extractors)
    raise ValueError(
        f"matcher.method={matcher_method!r} requires feature_extractor.method to be one of "
        f"({supported_display}); got {feature_extractor_method!r}."
    )


def _as_invalid_mask(mask_value: np.ndarray | None) -> np.ndarray | None:
    if mask_value is None:
        return None
    mask = np.asarray(mask_value)
    if mask.dtype == np.bool_:
        return mask
    return mask == 0


def _valid_mask_keep(points: np.ndarray, invalid_mask: np.ndarray | None) -> np.ndarray:
    if points.size <= 0:
        return np.zeros((0,), dtype=bool)
    mask = _as_invalid_mask(invalid_mask)
    if mask is None:
        return np.ones((points.shape[0],), dtype=bool)
    height, width = mask.shape[:2]
    rounded_x = np.rint(points[:, 0]).astype(np.int64, copy=False)
    rounded_y = np.rint(points[:, 1]).astype(np.int64, copy=False)
    inside = (rounded_x >= 0) & (rounded_x < width) & (rounded_y >= 0) & (rounded_y < height)
    keep = np.zeros((points.shape[0],), dtype=bool)
    keep[inside] = ~mask[rounded_y[inside], rounded_x[inside]]
    return keep


def _filter_feature_dict_by_invalid_mask(features: Any, invalid_mask: np.ndarray | None) -> dict[str, Any]:
    feature_map = dict(features or {})
    keypoints = np.asarray(feature_map.get("keypoints", np.zeros((0, 2), dtype=np.float32)), dtype=np.float32).reshape(-1, 2)
    keep = _valid_mask_keep(keypoints, invalid_mask)
    per_keypoint_fields = {
        "descriptors",
        "scores",
        "scales",
        "oris",
        "orientations",
        "responses",
        "keypoint_scores",
        "lafs",
    }
    filtered: dict[str, Any] = {}
    for key, value in feature_map.items():
        if key == "keypoints":
            filtered[key] = keypoints[keep].astype(np.float32, copy=False)
            continue
        array = np.asarray(value)
        if array.ndim > 0 and array.shape[0] == keypoints.shape[0] and key in per_keypoint_fields:
            filtered[key] = array[keep]
            continue
        filtered[key] = value
    filtered.setdefault("keypoints", keypoints[keep].astype(np.float32, copy=False))
    return filtered


class DeepMatcherAdapter:
    def __init__(self, *, prefer_gpu: bool = True, runtime_config: Any | None = None) -> None:
        _validate_runtime_matcher_compatibility(runtime_config)
        self._runtime_config = runtime_config
        resolved_prefer_gpu = (
            bool(getattr(runtime_config, "prefer_gpu"))
            if runtime_config is not None and hasattr(runtime_config, "prefer_gpu")
            else bool(prefer_gpu)
        )
        self._prefer_gpu = resolved_prefer_gpu
        self._device = resolve_torch_device(resolved_prefer_gpu)
        self._superpoint = SuperPointFrontend(runtime_config=runtime_config)
        self._official_lightglue_frontend = None
        self._loftr_frontend = LoFTRFrontend(
            feature_options=dict(getattr(runtime_config, "feature_options", {}) or {}),
            matcher_options=dict(getattr(runtime_config, "matcher_options", {}) or {}),
        )
        self._matcher_cache: dict[tuple[str, str, str, str, str, str], Any] = {}

    def _matcher_build_kwargs(self, *, method: str) -> dict[str, Any]:
        runtime_config = self._runtime_config
        return {
            "feature_extractor_method": _runtime_feature_extractor_method(runtime_config, method),
            "matcher_options": dict(getattr(runtime_config, "matcher_options", {}) or {}),
            "feature_options": dict(getattr(runtime_config, "feature_options", {}) or {}),
            "device_options": dict(getattr(runtime_config, "device_options", {}) or {}),
        }

    def _cacheable_options(self, options: dict[str, Any]) -> str:
        return json.dumps(options, sort_keys=True, ensure_ascii=True, default=str)

    def _raise_cross_method_fallback_error(self, requested: str, fallback_to: str) -> None:
        raise RuntimeError(
            "Deep matcher fallback must use the same method: "
            f"requested={requested!r}, fallback_to={fallback_to!r}."
        )

    def _get_official_lightglue_frontend(self, extractor_method: str) -> OfficialLightGlueFrontend:
        runtime_config = self._runtime_config
        feature_options = dict(getattr(runtime_config, "feature_options", {}) or {})
        if (
            self._official_lightglue_frontend is None
            or self._official_lightglue_frontend.feature_extractor_method != extractor_method
        ):
            self._official_lightglue_frontend = OfficialLightGlueFrontend(
                feature_extractor_method=extractor_method,
                feature_options=feature_options,
            )
        return self._official_lightglue_frontend

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
        left_mask: np.ndarray | None = None,
        right_mask: np.ndarray | None = None,
        device: str,
    ) -> DeepMatchResult:
        method = normalize_deep_method(matcher_method)
        try:
            if method in ("superglue", "lightglue"):
                extractor_method = _runtime_feature_extractor_method(self._runtime_config, method)
                backend = _runtime_matcher_backend(self._runtime_config)
                if method == "lightglue" and backend == "official":
                    frontend = self._get_official_lightglue_frontend(extractor_method)
                    features_left = frontend.extract(left_image, device=device)
                    features_right = frontend.extract(right_image, device=device)
                else:
                    if extractor_method != "superpoint":
                        raise DeepFrontendError(
                            f"feature_extractor.method={extractor_method!r} is validated but not yet implemented for {method!r}."
                        )
                    features_left = self._superpoint.extract(left_image, device=device)
                    features_right = self._superpoint.extract(right_image, device=device)
                features_left = _filter_feature_dict_by_invalid_mask(features_left, left_mask)
                features_right = _filter_feature_dict_by_invalid_mask(features_right, right_mask)
                matcher = self._get_cached_matcher(method=method, device=device)
                left_points, right_points, scores = matcher.match(
                    features_left=features_left,
                    features_right=features_right,
                    device=device,
                )
            else:
                prepared = self._loftr_frontend.prepare(
                    left_image,
                    right_image,
                    device=device,
                    left_mask=_as_invalid_mask(left_mask),
                    right_mask=_as_invalid_mask(right_mask),
                )
                matcher = self._get_cached_matcher(method=method, device=device)
                left_points, right_points, scores = matcher.match(
                    left_image=prepared["left"],
                    right_image=prepared["right"],
                    left_mask=prepared.get("left_mask"),
                    right_mask=prepared.get("right_mask"),
                    left_meta=prepared.get("left_meta"),
                    right_meta=prepared.get("right_meta"),
                    device=device,
                )
        except DeepDependencyError as error:
            raise DeepDependencyError(method, error.reason) from error
        except DeepMatcherError as error:
            dependency_error = self._normalize_dependency_error(method=method, error=error)
            if dependency_error is not None:
                raise dependency_error from error
            raise
        except (ModuleNotFoundError, ImportError) as error:
            missing = getattr(error, "name", "") or str(error)
            raise DeepDependencyError(method, f"missing optional dependency '{missing}'.") from error

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

    def _get_cached_matcher(self, *, method: str, device: str) -> Any:
        build_kwargs = self._matcher_build_kwargs(method=method)
        cache_key = (
            method,
            device,
            build_kwargs["feature_extractor_method"],
            self._cacheable_options(build_kwargs["matcher_options"]),
            self._cacheable_options(build_kwargs["feature_options"]),
            self._cacheable_options(build_kwargs["device_options"]),
        )
        matcher = self._matcher_cache.get(cache_key)
        if matcher is None:
            matcher = build_deep_matcher(method, device=device, **build_kwargs)
            self._matcher_cache[cache_key] = matcher
        return matcher

    def _normalize_dependency_error(self, *, method: str, error: DeepMatcherError) -> DeepDependencyError | None:
        reason = str(error).strip()
        lowered_reason = reason.lower()
        if "dependency unavailable" in lowered_reason or "missing optional dependency" in lowered_reason:
            return DeepDependencyError(method, reason)
        return None

    def match_pair(
        self,
        *,
        matcher_method: str,
        left_image: Any,
        right_image: Any,
        left_mask: np.ndarray | None = None,
        right_mask: np.ndarray | None = None,
    ) -> DeepMatchResult:
        return self._match_pair_on_device(
            matcher_method=matcher_method,
            left_image=left_image,
            right_image=right_image,
            left_mask=left_mask,
            right_mask=right_mask,
            device=self._device,
        )

    def match_pair_with_fallback(
        self,
        *,
        matcher_method: str,
        left_image: Any,
        right_image: Any,
        left_mask: np.ndarray | None = None,
        right_mask: np.ndarray | None = None,
        prefer_gpu: bool,
    ) -> DeepMatchResult:
        method = normalize_deep_method(matcher_method)
        resolved_prefer_gpu = self._prefer_gpu if self._runtime_config is not None else bool(prefer_gpu)
        primary_device = resolve_torch_device(resolved_prefer_gpu)
        try:
            return self._match_pair_on_device(
                matcher_method=method,
                left_image=left_image,
                right_image=right_image,
                left_mask=left_mask,
                right_mask=right_mask,
                device=primary_device,
            )
        except (DeepDependencyError, DeepMatcherError):
            raise
        except Exception:
            if not resolved_prefer_gpu:
                raise
            fallback_method = self.resolve_fallback_method(requested_method=method, fallback_method=method)
            return self._match_pair_on_device(
                matcher_method=fallback_method,
                left_image=left_image,
                right_image=right_image,
                left_mask=left_mask,
                right_mask=right_mask,
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
