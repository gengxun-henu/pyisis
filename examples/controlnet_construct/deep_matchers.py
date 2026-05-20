"""Model-backed matcher wrappers for deep matcher methods.

Author: Geng Xun
Created: 2026-05-11
Updated: 2026-05-11  Geng Xun added top-of-file metadata so example helper modules follow the repository's example-file header convention.
Updated: 2026-05-19  Geng Xun applied preset matcher parameters for LightGlue, SuperGlue, and LoFTR model construction.
Updated: 2026-05-20  Geng Xun added fail-fast matcher and feature-extractor compatibility checks before model construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .deep_frontends import normalize_deep_method


class DeepMatcherError(RuntimeError):
    """Raised for unsupported deep matcher operations."""


def _missing_dependency_error(*, method: str, missing: str, install_hint: str) -> DeepMatcherError:
    return DeepMatcherError(
        f"Deep matcher '{method}' dependency unavailable: missing '{missing}'. Install with `{install_hint}`."
    )


def _copy_options(options: dict[str, Any] | None) -> dict[str, Any]:
    return dict(options or {})


def _append_ignored_parameter(ignored_parameters: list[str], option_name: str) -> None:
    if option_name not in ignored_parameters:
        ignored_parameters.append(option_name)


def _raise_unsupported_option(*, method: str, option_name: str, option_value: Any) -> None:
    raise DeepMatcherError(
        f"Deep matcher '{method}' does not support critical matcher option "
        f"'{option_name}'={option_value!r}; refusing to ignore it silently."
    )


def _consume_matcher_placeholder(
    options: dict[str, Any],
    *,
    method: str,
    option_name: str,
    ignored_parameters: list[str],
) -> None:
    if option_name not in options:
        return
    option_value = options.pop(option_name)
    if option_value in (None, ""):
        ignored_parameters.append(option_name)
        return
    _raise_unsupported_option(method=method, option_name=option_name, option_value=option_value)


def _reject_unknown_options(*, method: str, options: dict[str, Any], allowed: set[str]) -> None:
    for option_name, option_value in options.items():
        if option_name not in allowed:
            _raise_unsupported_option(method=method, option_name=option_name, option_value=option_value)


def _resolve_device_dtype(*, method: str, device_options: dict[str, Any] | None, ignored_parameters: list[str]) -> str:
    options = _copy_options(device_options)
    dtype_value = options.pop("dtype", "float32")
    device_dtype = str(dtype_value or "float32").strip().lower()
    if device_dtype not in {"float32", "float16", "bfloat16"}:
        _raise_unsupported_option(method=method, option_name="dtype", option_value=dtype_value)
    options.pop("prefer_gpu", None)
    options.pop("type", None)
    for option_name in options:
        _append_ignored_parameter(ignored_parameters, f"device.{option_name}")
    return device_dtype


def _resolve_torch_dtype(*, torch: Any, method: str, device_dtype: str) -> Any:
    torch_dtype = getattr(torch, device_dtype, None)
    if torch_dtype is None:
        raise DeepMatcherError(
            f"Deep matcher '{method}' requested unsupported torch dtype {device_dtype!r}."
        )
    return torch_dtype


def _validate_feature_extractor_compatibility(*, matcher_method: str, feature_extractor_method: str) -> str:
    normalized_extractor = str(feature_extractor_method or "").strip().lower()
    normalized_matcher = str(matcher_method or "").strip().lower()
    supported_extractors = {
        "lightglue": ("superpoint",),
        "superglue": ("superpoint",),
        "loftr": ("loftr",),
    }.get(normalized_matcher)
    if supported_extractors is None or normalized_extractor in supported_extractors:
        return normalized_extractor
    supported_display = ", ".join(repr(method) for method in supported_extractors)
    raise DeepMatcherError(
        f"matcher.method={normalized_matcher!r} requires feature_extractor.method to be one of "
        f"({supported_display}); got {normalized_extractor!r}."
    )


@dataclass(frozen=True, slots=True)
class DeepMatchResult:
    left_keypoints: tuple[Any, ...] = ()
    right_keypoints: tuple[Any, ...] = ()
    matches: tuple[Any, ...] = ()


class SuperGlueMatcher:
    method = "superglue"

    def __init__(
        self,
        *,
        device: str = "cpu",
        feature_extractor_method: str = "superpoint",
        matcher_options: dict[str, Any] | None = None,
        feature_options: dict[str, Any] | None = None,
        device_options: dict[str, Any] | None = None,
    ) -> None:
        self.device = device
        self.feature_extractor_method = str(feature_extractor_method or "superpoint").strip().lower()
        self.matcher_options = _copy_options(matcher_options)
        self.feature_options = _copy_options(feature_options)
        self.device_options = _copy_options(device_options)
        self.ignored_parameters: list[str] = []
        self.device_dtype = _resolve_device_dtype(
            method=self.method,
            device_options=self.device_options,
            ignored_parameters=self.ignored_parameters,
        )
        self._model = None

    def _superpoint_config(self) -> dict[str, Any]:
        config = {"nms_radius": 4, "keypoint_threshold": 0.005, "max_keypoints": 2048}
        for option_name in ("nms_radius", "keypoint_threshold", "max_keypoints"):
            if option_name in self.feature_options:
                config[option_name] = self.feature_options[option_name]
        return config

    def _superglue_config(self) -> dict[str, Any]:
        options = _copy_options(self.matcher_options)
        _consume_matcher_placeholder(
            options,
            method=self.method,
            option_name="weights_path",
            ignored_parameters=self.ignored_parameters,
        )
        _reject_unknown_options(
            method=self.method,
            options=options,
            allowed={"weights", "sinkhorn_iterations", "match_threshold"},
        )
        config = {"weights": "outdoor", "sinkhorn_iterations": 20, "match_threshold": 0.2}
        config.update(options)
        return config

    def _load_model(self):
        if self.feature_extractor_method != "superpoint":
            raise DeepMatcherError(
                f"Deep matcher '{self.method}' currently only supports feature_extractor_method='superpoint', "
                f"got {self.feature_extractor_method!r}."
            )
        try:
            import torch
        except Exception:
            raise _missing_dependency_error(
                method=self.method,
                missing="torch",
                install_hint="pip install torch superglue-pretrained-network",
            )

        try:
            from models.matching import Matching  # type: ignore[import-not-found]
        except Exception:
            raise _missing_dependency_error(
                method=self.method,
                missing="superglue-pretrained-network",
                install_hint="pip install superglue-pretrained-network",
            )

        torch_dtype = _resolve_torch_dtype(torch=torch, method=self.method, device_dtype=self.device_dtype)
        if self._model is None:
            self._model = Matching(
                {
                    "superpoint": self._superpoint_config(),
                    "superglue": self._superglue_config(),
                }
            ).eval().to(device=self.device, dtype=torch_dtype)
        return torch, self._model

    def match(self, *, features_left: Any, features_right: Any, device: str = "cpu"):
        torch, model = self._load_model()
        _ = device
        torch_dtype = _resolve_torch_dtype(torch=torch, method=self.method, device_dtype=self.device_dtype)
        left_keypoints = np.asarray((features_left or {}).get("keypoints", np.zeros((0, 2), dtype=np.float32)), dtype=np.float32)
        right_keypoints = np.asarray((features_right or {}).get("keypoints", np.zeros((0, 2), dtype=np.float32)), dtype=np.float32)
        left_descriptors = np.asarray(
            (features_left or {}).get("descriptors", np.zeros((0, 256), dtype=np.float32)),
            dtype=np.float32,
        )
        right_descriptors = np.asarray(
            (features_right or {}).get("descriptors", np.zeros((0, 256), dtype=np.float32)),
            dtype=np.float32,
        )

        if left_keypoints.shape[0] <= 0 or right_keypoints.shape[0] <= 0:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)

        left_scores = np.asarray((features_left or {}).get("scores", np.ones((left_keypoints.shape[0],), dtype=np.float32)), dtype=np.float32).reshape(-1)
        right_scores = np.asarray((features_right or {}).get("scores", np.ones((right_keypoints.shape[0],), dtype=np.float32)), dtype=np.float32).reshape(-1)
        if left_scores.shape[0] != left_keypoints.shape[0]:
            left_scores = np.ones((left_keypoints.shape[0],), dtype=np.float32)
        if right_scores.shape[0] != right_keypoints.shape[0]:
            right_scores = np.ones((right_keypoints.shape[0],), dtype=np.float32)
        match_input = {
            "keypoints0": torch.from_numpy(left_keypoints)[None, :, :].to(device=self.device, dtype=torch_dtype),
            "keypoints1": torch.from_numpy(right_keypoints)[None, :, :].to(device=self.device, dtype=torch_dtype),
            "descriptors0": torch.from_numpy(left_descriptors.T)[None, :, :].to(device=self.device, dtype=torch_dtype),
            "descriptors1": torch.from_numpy(right_descriptors.T)[None, :, :].to(device=self.device, dtype=torch_dtype),
            "scores0": torch.from_numpy(left_scores)[None, :].to(device=self.device, dtype=torch_dtype),
            "scores1": torch.from_numpy(right_scores)[None, :].to(device=self.device, dtype=torch_dtype),
        }

        with torch.no_grad():
            prediction = model(match_input)

        matches0 = prediction["matches0"][0].detach().cpu().numpy()
        scores0 = prediction["matching_scores0"][0].detach().cpu().numpy()
        valid_indices = np.where(matches0 >= 0)[0]
        if valid_indices.size <= 0:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)
        right_indices = matches0[valid_indices].astype(np.int64, copy=False)
        return (
            left_keypoints[valid_indices].astype(np.float32, copy=False),
            right_keypoints[right_indices].astype(np.float32, copy=False),
            scores0[valid_indices].astype(np.float32, copy=False),
        )


class LightGlueMatcher:
    method = "lightglue"

    def __init__(
        self,
        *,
        device: str = "cpu",
        feature_extractor_method: str = "superpoint",
        matcher_options: dict[str, Any] | None = None,
        feature_options: dict[str, Any] | None = None,
        device_options: dict[str, Any] | None = None,
    ) -> None:
        self.device = device
        self.feature_extractor_method = str(feature_extractor_method or "superpoint").strip().lower()
        self.matcher_options = _copy_options(matcher_options)
        self.feature_options = _copy_options(feature_options)
        self.device_options = _copy_options(device_options)
        self.ignored_parameters: list[str] = []
        self.device_dtype = _resolve_device_dtype(
            method=self.method,
            device_options=self.device_options,
            ignored_parameters=self.ignored_parameters,
        )
        self._matcher = None

    def _lightglue_options(self) -> dict[str, Any]:
        options = _copy_options(self.matcher_options)
        _consume_matcher_placeholder(
            options,
            method=self.method,
            option_name="weights_path",
            ignored_parameters=self.ignored_parameters,
        )
        _reject_unknown_options(
            method=self.method,
            options=options,
            allowed={"weights", "flash", "prune_threshold", "filter_threshold", "depth_confidence", "width_confidence"},
        )
        return options

    def _load_matcher(self):
        if self.feature_extractor_method != "superpoint":
            raise DeepMatcherError(
                f"Deep matcher '{self.method}' currently only supports feature_extractor_method='superpoint', "
                f"got {self.feature_extractor_method!r}."
            )
        try:
            import torch
        except Exception:
            raise _missing_dependency_error(
                method=self.method,
                missing="torch",
                install_hint="pip install torch lightglue",
            )

        try:
            from lightglue import LightGlue  # type: ignore[import-not-found]
        except Exception:
            raise _missing_dependency_error(
                method=self.method,
                missing="lightglue",
                install_hint="pip install lightglue",
            )

        torch_dtype = _resolve_torch_dtype(torch=torch, method=self.method, device_dtype=self.device_dtype)
        if self._matcher is None:
            self._matcher = LightGlue(
                features=self.feature_extractor_method,
                **self._lightglue_options(),
            ).eval().to(device=self.device, dtype=torch_dtype)
        return torch, self._matcher

    def match(self, *, features_left: Any, features_right: Any, device: str = "cpu"):
        torch, matcher = self._load_matcher()
        _ = device
        torch_dtype = _resolve_torch_dtype(torch=torch, method=self.method, device_dtype=self.device_dtype)
        left_keypoints = np.asarray((features_left or {}).get("keypoints", np.zeros((0, 2), dtype=np.float32)), dtype=np.float32)
        right_keypoints = np.asarray((features_right or {}).get("keypoints", np.zeros((0, 2), dtype=np.float32)), dtype=np.float32)
        left_descriptors = np.asarray(
            (features_left or {}).get("descriptors", np.zeros((0, 256), dtype=np.float32)),
            dtype=np.float32,
        )
        right_descriptors = np.asarray(
            (features_right or {}).get("descriptors", np.zeros((0, 256), dtype=np.float32)),
            dtype=np.float32,
        )
        if left_keypoints.shape[0] <= 0 or right_keypoints.shape[0] <= 0:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)

        inputs = {
            "image0": {
                "keypoints": torch.from_numpy(left_keypoints)[None, :, :].to(device=self.device, dtype=torch_dtype),
                "descriptors": torch.from_numpy(left_descriptors)[None, :, :].to(device=self.device, dtype=torch_dtype),
            },
            "image1": {
                "keypoints": torch.from_numpy(right_keypoints)[None, :, :].to(device=self.device, dtype=torch_dtype),
                "descriptors": torch.from_numpy(right_descriptors)[None, :, :].to(device=self.device, dtype=torch_dtype),
            },
        }
        with torch.no_grad():
            prediction = matcher(inputs)

        if "matches0" in prediction and "matching_scores0" in prediction:
            matches0 = prediction["matches0"][0].detach().cpu().numpy()
            scores0 = prediction["matching_scores0"][0].detach().cpu().numpy()
            valid_indices = np.where(matches0 >= 0)[0]
            if valid_indices.size <= 0:
                return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)
            right_indices = matches0[valid_indices].astype(np.int64, copy=False)
            return (
                left_keypoints[valid_indices].astype(np.float32, copy=False),
                right_keypoints[right_indices].astype(np.float32, copy=False),
                scores0[valid_indices].astype(np.float32, copy=False),
            )

        if "matches" in prediction:
            matches = prediction["matches"][0].detach().cpu().numpy().astype(np.int64, copy=False)
            scores = prediction.get("scores")
            if scores is None:
                score_array = np.ones((matches.shape[0],), dtype=np.float32)
            else:
                score_array = scores[0].detach().cpu().numpy().astype(np.float32, copy=False)
            if matches.size <= 0:
                return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)
            return (
                left_keypoints[matches[:, 0]].astype(np.float32, copy=False),
                right_keypoints[matches[:, 1]].astype(np.float32, copy=False),
                score_array,
            )
        raise DeepMatcherError("LightGlue prediction did not include expected match tensors.")


class LoFTRMatcher:
    method = "loftr"

    def __init__(
        self,
        *,
        device: str = "cpu",
        feature_extractor_method: str = "loftr",
        matcher_options: dict[str, Any] | None = None,
        feature_options: dict[str, Any] | None = None,
        device_options: dict[str, Any] | None = None,
    ) -> None:
        self.device = device
        self.feature_extractor_method = str(feature_extractor_method or "loftr").strip().lower()
        self.matcher_options = _copy_options(matcher_options)
        self.feature_options = _copy_options(feature_options)
        self.device_options = _copy_options(device_options)
        self.ignored_parameters: list[str] = []
        self.device_dtype = _resolve_device_dtype(
            method=self.method,
            device_options=self.device_options,
            ignored_parameters=self.ignored_parameters,
        )
        self._matcher = None

    def _loftr_pretrained(self) -> str:
        options = _copy_options(self.matcher_options)
        _consume_matcher_placeholder(
            options,
            method=self.method,
            option_name="weights_path",
            ignored_parameters=self.ignored_parameters,
        )
        _consume_matcher_placeholder(
            options,
            method=self.method,
            option_name="checkpoint_path",
            ignored_parameters=self.ignored_parameters,
        )
        _consume_matcher_placeholder(
            options,
            method=self.method,
            option_name="checkpoint",
            ignored_parameters=self.ignored_parameters,
        )
        pretrained = str(options.pop("pretrained", "outdoor") or "outdoor").strip()
        _reject_unknown_options(method=self.method, options=options, allowed=set())
        return pretrained or "outdoor"

    def _load_matcher(self):
        try:
            import torch
        except Exception:
            raise _missing_dependency_error(
                method=self.method,
                missing="torch",
                install_hint="pip install torch kornia",
            )
        try:
            import kornia.feature as kf
        except Exception:
            raise _missing_dependency_error(
                method=self.method,
                missing="kornia",
                install_hint="pip install kornia",
            )
        torch_dtype = _resolve_torch_dtype(torch=torch, method=self.method, device_dtype=self.device_dtype)
        if self._matcher is None:
            self._matcher = kf.LoFTR(pretrained=self._loftr_pretrained()).eval().to(device=self.device, dtype=torch_dtype)
        return torch, self._matcher

    def match(
        self,
        *,
        left_image: Any,
        right_image: Any,
        left_mask: Any = None,
        right_mask: Any = None,
        device: str = "cpu",
    ):
        torch, matcher = self._load_matcher()
        _ = device
        torch_dtype = _resolve_torch_dtype(torch=torch, method=self.method, device_dtype=self.device_dtype)
        if left_image is None or right_image is None:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)
        matcher_inputs = {
            "image0": left_image.to(device=self.device, dtype=torch_dtype),
            "image1": right_image.to(device=self.device, dtype=torch_dtype),
        }
        if left_mask is not None:
            matcher_inputs["mask0"] = left_mask.to(self.device)
        if right_mask is not None:
            matcher_inputs["mask1"] = right_mask.to(self.device)
        with torch.no_grad():
            output = matcher(matcher_inputs)
        left_points = output["keypoints0"].detach().cpu().numpy().astype(np.float32, copy=False)
        right_points = output["keypoints1"].detach().cpu().numpy().astype(np.float32, copy=False)
        scores = output["confidence"].detach().cpu().numpy().astype(np.float32, copy=False)
        return left_points, right_points, scores


def build_deep_matcher(
    method: str,
    *,
    device: str = "cpu",
    feature_extractor_method: str = "superpoint",
    matcher_options: dict[str, Any] | None = None,
    feature_options: dict[str, Any] | None = None,
    device_options: dict[str, Any] | None = None,
) -> SuperGlueMatcher | LightGlueMatcher | LoFTRMatcher:
    normalized = normalize_deep_method(method)
    resolved_extractor = _validate_feature_extractor_compatibility(
        matcher_method=normalized,
        feature_extractor_method=feature_extractor_method,
    )
    constructor_kwargs = {
        "device": device,
        "feature_extractor_method": resolved_extractor,
        "matcher_options": matcher_options,
        "feature_options": feature_options,
        "device_options": device_options,
    }
    if normalized == "superglue":
        return SuperGlueMatcher(**constructor_kwargs)
    if normalized == "lightglue":
        return LightGlueMatcher(**constructor_kwargs)
    if normalized == "loftr":
        return LoFTRMatcher(**constructor_kwargs)
    raise DeepMatcherError(f"Unsupported deep matcher method {method!r}.")
