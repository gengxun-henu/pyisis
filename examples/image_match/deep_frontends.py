"""Frontend helpers for model-backed deep matcher pipelines.

Author: Geng Xun
Created: 2026-05-11
Updated: 2026-05-19  Geng Xun added runtime-configured SuperPoint frontend options and explicit ignored-parameter tracking.
"""

from __future__ import annotations

import inspect
from typing import Any

import numpy as np


SUPPORTED_DEEP_METHODS = ("superglue", "lightglue", "loftr")


class DeepFrontendError(RuntimeError):
    """Raised when deep frontend setup fails."""


class DeepDependencyError(RuntimeError):
    """Raised when deep matcher dependencies are unavailable."""

    def __init__(self, method: str, reason: str) -> None:
        self.method = str(method).strip().lower()
        self.reason = str(reason).strip()
        super().__init__(f"Deep matcher dependency unavailable for '{self.method}': {self.reason}")


def _raise_missing_dependency(*, method: str, missing: str, install_hint: str) -> None:
    raise DeepDependencyError(
        method,
        f"missing optional dependency '{missing}'. Install with `{install_hint}`.",
    )


def _require_kornia_feature(*, method: str, feature_name: str, install_hint: str):
    try:
        import kornia.feature as kf
    except Exception:
        _raise_missing_dependency(
            method=method,
            missing="kornia",
            install_hint=install_hint,
        )

    if not hasattr(kf, feature_name):
        _raise_missing_dependency(
            method=method,
            missing=f"kornia.feature.{feature_name}",
            install_hint=install_hint,
        )
    return kf


def _callable_accepts_var_keyword(callable_object: Any) -> bool:
    try:
        signature = inspect.signature(callable_object)
    except (TypeError, ValueError):
        return False
    return any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values())


def _callable_parameter_names(callable_object: Any) -> set[str]:
    try:
        signature = inspect.signature(callable_object)
    except (TypeError, ValueError):
        return set()
    return {
        name
        for name, parameter in signature.parameters.items()
        if parameter.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }


class SuperPointFrontend:
    _SUPPORTED_PARAMETER_ALIASES = {
        "max_keypoints": ("max_keypoints", "max_num_keypoints", "num_keypoints"),
        "keypoint_threshold": ("keypoint_threshold",),
        "nms_radius": ("nms_radius",),
    }

    def __init__(self, *, runtime_config: Any | None = None, feature_options: dict[str, Any] | None = None) -> None:
        self._runtime_config = runtime_config
        self.requested_parameters = self._resolve_requested_parameters(runtime_config, feature_options)
        self.ignored_parameters = self._initial_ignored_parameters(runtime_config, feature_options)
        self._extractor = None

    def _resolve_requested_parameters(
        self,
        runtime_config: Any | None,
        feature_options: dict[str, Any] | None,
    ) -> dict[str, Any]:
        raw_options: dict[str, Any] = {}
        if runtime_config is not None:
            raw_config = getattr(runtime_config, "raw_config", {}) or {}
            extractor_config = raw_config.get("feature_extractor", {}) if isinstance(raw_config, dict) else {}
            if isinstance(extractor_config, dict):
                raw_options.update(extractor_config)
        if feature_options:
            raw_options.update(feature_options)

        return {
            key: raw_options[key]
            for key in self._SUPPORTED_PARAMETER_ALIASES
            if key in raw_options
        }

    def _initial_ignored_parameters(
        self,
        runtime_config: Any | None,
        feature_options: dict[str, Any] | None,
    ) -> dict[str, str]:
        raw_options: dict[str, Any] = {}
        if runtime_config is not None:
            raw_config = getattr(runtime_config, "raw_config", {}) or {}
            extractor_config = raw_config.get("feature_extractor", {}) if isinstance(raw_config, dict) else {}
            if isinstance(extractor_config, dict):
                raw_options.update(extractor_config)
        if feature_options:
            raw_options.update(feature_options)

        return {
            key: "not supported by the Stage 3 SuperPoint frontend"
            for key in raw_options
            if key not in self._SUPPORTED_PARAMETER_ALIASES and key != "method"
        }

    def _build_superpoint_kwargs(self, superpoint_constructor: Any) -> dict[str, Any]:
        accepts_var_keyword = _callable_accepts_var_keyword(superpoint_constructor)
        parameter_names = _callable_parameter_names(superpoint_constructor)
        constructor_kwargs: dict[str, Any] = {}

        if accepts_var_keyword or "pretrained" in parameter_names:
            constructor_kwargs["pretrained"] = "superpoint_v1"

        for canonical_name, value in self.requested_parameters.items():
            aliases = self._SUPPORTED_PARAMETER_ALIASES[canonical_name]
            selected_name = None
            if accepts_var_keyword:
                selected_name = aliases[0]
            else:
                selected_name = next((alias for alias in aliases if alias in parameter_names), None)
            if selected_name is None:
                self.ignored_parameters[canonical_name] = "not accepted by kornia.feature.SuperPoint in this environment"
                continue
            constructor_kwargs[selected_name] = value
        return constructor_kwargs

    def extract(self, image, device: str):
        try:
            import torch
        except Exception:
            _raise_missing_dependency(
                method="superglue/lightglue",
                missing="torch",
                install_hint="pip install torch kornia",
            )

        kf = _require_kornia_feature(
            method="superglue/lightglue",
            feature_name="SuperPoint",
            install_hint="pip install kornia",
        )

        image_array = np.asarray(image, dtype=np.float32)
        if image_array.size <= 0:
            return {"keypoints": np.zeros((0, 2), dtype=np.float32), "descriptors": np.zeros((0, 256), dtype=np.float32)}

        if image_array.ndim == 0:
            image_plane = image_array.reshape(1, 1)
        elif image_array.ndim == 1:
            image_plane = image_array.reshape(1, -1)
        elif image_array.ndim == 2:
            image_plane = image_array
        else:
            image_plane = np.mean(image_array, axis=-1)

        image_plane = np.nan_to_num(image_plane, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32, copy=False)
        scale = float(np.max(np.abs(image_plane))) if image_plane.size > 0 else 0.0
        if scale > 0.0:
            image_plane = image_plane / scale
        image_tensor = torch.from_numpy(image_plane).to(dtype=torch.float32)[None, None, :, :].to(device)

        if self._extractor is None:
            self._extractor = kf.SuperPoint(**self._build_superpoint_kwargs(kf.SuperPoint))
        self._extractor = self._extractor.to(device).eval()

        with torch.no_grad():
            scores, keypoints, descriptors = self._extractor(image_tensor)
        keypoint_array = keypoints[0].detach().cpu().numpy().astype(np.float32, copy=False)
        descriptor_array = descriptors[0].detach().cpu().numpy().T.astype(np.float32, copy=False)
        _ = scores
        return {"keypoints": keypoint_array, "descriptors": descriptor_array}


class OfficialLightGlueFrontend:
    _EXTRACTOR_CLASS_NAMES = {
        "superpoint": "SuperPoint",
        "disk": "DISK",
        "aliked": "ALIKED",
        "doghardnet": "DoGHardNet",
        "lightglue_sift": "SIFT",
    }
    _RGB_FRONTENDS = {"disk", "aliked"}

    def __init__(
        self,
        *,
        feature_extractor_method: str,
        feature_options: dict[str, Any] | None = None,
    ) -> None:
        self.feature_extractor_method = str(feature_extractor_method).strip().lower()
        if self.feature_extractor_method not in self._EXTRACTOR_CLASS_NAMES:
            supported = tuple(self._EXTRACTOR_CLASS_NAMES)
            raise DeepFrontendError(
                f"Unsupported official LightGlue frontend {feature_extractor_method!r}. Expected one of {supported}."
            )

        self.feature_options = dict(feature_options or {})
        self.max_num_keypoints = self._resolve_max_num_keypoints(self.feature_options)
        self._extractor = None

    def _resolve_max_num_keypoints(self, feature_options: dict[str, Any]) -> Any:
        has_max_features = "max_features" in feature_options
        has_max_keypoints = "max_keypoints" in feature_options
        if has_max_features and has_max_keypoints:
            raise ValueError("Specify only one of max_features or max_keypoints for official LightGlue frontends.")
        if has_max_features:
            return feature_options["max_features"]
        if has_max_keypoints:
            return feature_options["max_keypoints"]
        return 2048

    def extract(self, image, device: str):
        try:
            import torch
        except Exception:
            _raise_missing_dependency(
                method="lightglue",
                missing="torch",
                install_hint="pip install torch lightglue",
            )

        try:
            import lightglue
        except Exception:
            _raise_missing_dependency(
                method="lightglue",
                missing="lightglue",
                install_hint="pip install lightglue",
            )

        image_tensor = self._as_tensor(image, device=device, torch_module=torch)
        extractor = self._load_extractor(lightglue_module=lightglue, device=device)

        with torch.no_grad():
            features = extractor.extract(image_tensor)
        return self._normalize_features(features)

    def _load_extractor(self, *, lightglue_module: Any, device: str):
        if self._extractor is None:
            constructor_name = self._EXTRACTOR_CLASS_NAMES[self.feature_extractor_method]
            if not hasattr(lightglue_module, constructor_name):
                _raise_missing_dependency(
                    method="lightglue",
                    missing=f"lightglue.{constructor_name}",
                    install_hint="pip install lightglue",
                )
            constructor = getattr(lightglue_module, constructor_name)
            self._extractor = constructor(max_num_keypoints=self.max_num_keypoints).eval().to(device)
        else:
            self._extractor = self._extractor.to(device)
        return self._extractor

    def _as_tensor(self, image, *, device: str, torch_module: Any):
        image_array = np.asarray(image, dtype=np.float32)
        if image_array.ndim == 0:
            image_array = image_array.reshape(1, 1)
        elif image_array.ndim == 1:
            image_array = image_array.reshape(1, -1)

        image_array = np.nan_to_num(image_array, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32, copy=False)
        scale = float(np.max(np.abs(image_array))) if image_array.size > 0 else 0.0
        if scale > 0.0:
            image_array = image_array / scale

        channel_count = 3 if self.feature_extractor_method in self._RGB_FRONTENDS else 1
        image_chw = self._to_chw(image_array, channel_count=channel_count)
        return torch_module.from_numpy(np.ascontiguousarray(image_chw)).to(dtype=torch_module.float32)[None, :, :, :].to(device)

    def _to_chw(self, image_array: np.ndarray, *, channel_count: int) -> np.ndarray:
        if image_array.ndim == 2:
            image_plane = image_array
            if channel_count == 1:
                return image_plane[None, :, :]
            return np.repeat(image_plane[None, :, :], 3, axis=0)

        if channel_count == 1:
            return np.mean(image_array, axis=-1, dtype=np.float32)[None, :, :]

        if image_array.shape[-1] >= 3:
            return np.moveaxis(image_array[..., :3], -1, 0)
        if image_array.shape[-1] == 1:
            return np.repeat(np.moveaxis(image_array, -1, 0), 3, axis=0)

        padding_shape = image_array.shape[:-1] + (3 - image_array.shape[-1],)
        padded = np.concatenate((image_array, np.zeros(padding_shape, dtype=np.float32)), axis=-1)
        return np.moveaxis(padded, -1, 0)

    def _normalize_features(self, features: Any) -> dict[str, Any]:
        normalized_features = {}
        for key, value in dict(features).items():
            normalized_features[key] = self._unbatch_feature_value(value)

        keypoints = np.asarray(normalized_features.get("keypoints", np.zeros((0, 2), dtype=np.float32)), dtype=np.float32)
        normalized_features["keypoints"] = keypoints.reshape(-1, 2) if keypoints.size > 0 else np.zeros((0, 2), dtype=np.float32)
        return normalized_features

    def _unbatch_feature_value(self, value: Any) -> Any:
        if hasattr(value, "detach"):
            value = value.detach().cpu().numpy()
        elif isinstance(value, (list, tuple)):
            value = np.asarray(value)

        if isinstance(value, np.ndarray):
            if value.ndim > 0 and value.shape[0] == 1:
                value = value[0]
            if np.issubdtype(value.dtype, np.floating):
                return value.astype(np.float32, copy=False)
        return value


class LoFTRFrontend:
    def __init__(self) -> None:
        self._torch = None

    def prepare(
        self,
        left_image,
        right_image,
        device: str,
        left_mask: np.ndarray | None = None,
        right_mask: np.ndarray | None = None,
    ):
        try:
            import torch
        except Exception:
            _raise_missing_dependency(
                method="loftr",
                missing="torch",
                install_hint="pip install torch kornia",
            )

        _require_kornia_feature(
            method="loftr",
            feature_name="SuperPoint",
            install_hint="pip install \"kornia[loftr]\"",
        )

        self._torch = torch
        return {
            "left": self._as_tensor(left_image, device=device),
            "right": self._as_tensor(right_image, device=device),
            "left_mask": self._as_mask_tensor(left_mask, device=device),
            "right_mask": self._as_mask_tensor(right_mask, device=device),
        }

    def _as_tensor(self, image, *, device: str):
        image_array = np.asarray(image, dtype=np.float32)
        if image_array.ndim == 0:
            image_plane = image_array.reshape(1, 1)
        elif image_array.ndim == 1:
            image_plane = image_array.reshape(1, -1)
        elif image_array.ndim == 2:
            image_plane = image_array
        else:
            image_plane = np.mean(image_array, axis=-1)

        image_plane = np.nan_to_num(image_plane, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32, copy=False)
        scale = float(np.max(np.abs(image_plane))) if image_plane.size > 0 else 0.0
        if scale > 0.0:
            image_plane = image_plane / scale
        return self._torch.from_numpy(image_plane).to(dtype=self._torch.float32)[None, None, :, :].to(device)

    def _as_mask_tensor(self, invalid_mask, *, device: str):
        if invalid_mask is None:
            return None
        mask_array = ~np.asarray(invalid_mask, dtype=bool)
        return self._torch.from_numpy(mask_array)[None, :, :].to(device)


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
