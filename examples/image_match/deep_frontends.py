"""Frontend helpers for model-backed deep matcher pipelines.

Author: Geng Xun
Created: 2026-05-11
Updated: 2026-05-19  Geng Xun added runtime-configured SuperPoint frontend options and explicit ignored-parameter tracking.
"""

from __future__ import annotations

import inspect
from typing import Any

import cv2
import numpy as np


SUPPORTED_DEEP_METHODS = ("superglue", "lightglue", "loftr")
LOFTR_DIVISIBILITY = 8
LOFTR_PREPROCESS_MODES = {"pad", "resize"}


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


class LoFTRFrontend:
    def __init__(
        self,
        *,
        feature_options: dict[str, Any] | None = None,
        matcher_options: dict[str, Any] | None = None,
    ) -> None:
        self.feature_options = dict(feature_options or {})
        self.matcher_options = dict(matcher_options or {})
        self.backend = str(self.matcher_options.get("backend") or "kornia").strip().lower() or "kornia"
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

        self._torch = torch
        if self.backend == "external":
            left_prepared = self._prepare_external_image(left_image, device=device, invalid_mask=left_mask)
            right_prepared = self._prepare_external_image(right_image, device=device, invalid_mask=right_mask)
            return {
                "left": left_prepared["image"],
                "right": right_prepared["image"],
                "left_mask": left_prepared["valid_mask"],
                "right_mask": right_prepared["valid_mask"],
                "left_valid_mask": left_prepared["valid_mask"],
                "right_valid_mask": right_prepared["valid_mask"],
                "left_meta": left_prepared["meta"],
                "right_meta": right_prepared["meta"],
            }

        _require_kornia_feature(
            method="loftr",
            feature_name="LoFTR",
            install_hint="pip install \"kornia[loftr]\"",
        )

        return {
            "left": self._as_tensor(left_image, device=device),
            "right": self._as_tensor(right_image, device=device),
            "left_mask": self._as_mask_tensor(left_mask, device=device),
            "right_mask": self._as_mask_tensor(right_mask, device=device),
        }

    def _prepare_external_image(self, image, *, device: str, invalid_mask: np.ndarray | None):
        image_plane = self._as_float_plane(image)
        original_height, original_width = image_plane.shape
        resize_width = self.feature_options.get("resize_width")
        resize_height = self.feature_options.get("resize_height")
        preprocess_mode = str(self.feature_options.get("preprocess_mode") or "pad").strip().lower()
        if preprocess_mode not in LOFTR_PREPROCESS_MODES:
            preprocess_mode = "pad"

        content_plane = image_plane
        has_content = original_width > 0 and original_height > 0
        if not has_content:
            infer_width = LOFTR_DIVISIBILITY
            infer_height = LOFTR_DIVISIBILITY
            aligned_plane = np.zeros((infer_height, infer_width), dtype=np.float32)
            valid_mask = np.zeros((infer_height, infer_width), dtype=bool)
            return self._external_prepared_result(
                aligned_plane=aligned_plane,
                valid_mask=valid_mask,
                device=device,
                original_size=(original_width, original_height),
                content_size=(original_width, original_height),
                infer_size=(infer_width, infer_height),
            )

        if resize_width is not None and resize_height is not None:
            content_width = self._align_size(int(resize_width), mode="floor")
            content_height = self._align_size(int(resize_height), mode="floor")
            content_plane = self._resize_plane(content_plane, width=content_width, height=content_height)

        content_height, content_width = content_plane.shape
        valid_mask = self._valid_content_mask(
            invalid_mask,
            original_size=(original_width, original_height),
            content_size=(content_width, content_height),
        )

        if preprocess_mode == "resize":
            infer_width = self._align_size(content_width, mode="floor")
            infer_height = self._align_size(content_height, mode="floor")
            aligned_plane = self._resize_plane(content_plane, width=infer_width, height=infer_height)
            if valid_mask is not None and (infer_width, infer_height) != (content_width, content_height):
                valid_mask = self._resize_valid_mask(valid_mask, width=infer_width, height=infer_height)
            content_width = infer_width
            content_height = infer_height
        else:
            infer_width = self._align_size(content_width, mode="ceil")
            infer_height = self._align_size(content_height, mode="ceil")
            aligned_plane = np.zeros((infer_height, infer_width), dtype=np.float32)
            aligned_plane[:content_height, :content_width] = content_plane
            if valid_mask is None and (infer_width, infer_height) != (content_width, content_height):
                valid_mask = np.ones((content_height, content_width), dtype=bool)
            if valid_mask is not None:
                aligned_valid_mask = np.zeros((infer_height, infer_width), dtype=bool)
                aligned_valid_mask[:content_height, :content_width] = valid_mask
                valid_mask = aligned_valid_mask

        return self._external_prepared_result(
            aligned_plane=aligned_plane,
            valid_mask=valid_mask,
            device=device,
            original_size=(original_width, original_height),
            content_size=(content_width, content_height),
            infer_size=(infer_width, infer_height),
        )

    def _external_prepared_result(
        self,
        *,
        aligned_plane: np.ndarray,
        valid_mask: np.ndarray | None,
        device: str,
        original_size: tuple[int, int],
        content_size: tuple[int, int],
        infer_size: tuple[int, int],
    ):
        image_tensor = self._torch.from_numpy(aligned_plane)[None][None].float().to(device)
        valid_mask_tensor = None
        if valid_mask is not None:
            valid_mask_tensor = self._torch.from_numpy(valid_mask.astype(bool, copy=False)).to(device)

        original_width, original_height = original_size
        content_width, content_height = content_size
        scale_width = original_width / content_width if content_width > 0 else 1.0
        scale_height = original_height / content_height if content_height > 0 else 1.0
        return {
            "image": image_tensor,
            "valid_mask": valid_mask_tensor,
            "meta": {
                "original_size": original_size,
                "content_size": content_size,
                "infer_size": infer_size,
                "scale": (scale_width, scale_height),
            },
        }

    def _as_float_plane(self, image) -> np.ndarray:
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
        return image_plane

    def _resize_plane(self, image_plane: np.ndarray, *, width: int, height: int) -> np.ndarray:
        interpolation = cv2.INTER_AREA if width <= image_plane.shape[1] and height <= image_plane.shape[0] else cv2.INTER_LINEAR
        return cv2.resize(image_plane, (width, height), interpolation=interpolation).astype(np.float32, copy=False)

    def _valid_content_mask(
        self,
        invalid_mask,
        *,
        original_size: tuple[int, int],
        content_size: tuple[int, int],
    ) -> np.ndarray | None:
        if invalid_mask is None:
            return None
        mask_array = ~np.asarray(invalid_mask, dtype=bool)
        original_width, original_height = original_size
        content_width, content_height = content_size
        if mask_array.shape[:2] != (original_height, original_width):
            mask_array = cv2.resize(
                mask_array.astype(np.uint8, copy=False),
                (original_width, original_height),
                interpolation=cv2.INTER_NEAREST,
            ).astype(bool, copy=False)
        if (content_width, content_height) != (original_width, original_height):
            mask_array = self._resize_valid_mask(mask_array, width=content_width, height=content_height)
        return mask_array.astype(bool, copy=False)

    def _resize_valid_mask(self, mask_array: np.ndarray, *, width: int, height: int) -> np.ndarray:
        return cv2.resize(
            mask_array.astype(np.uint8, copy=False),
            (width, height),
            interpolation=cv2.INTER_NEAREST,
        ).astype(bool, copy=False)

    def _align_size(self, size: int, *, mode: str) -> int:
        size = max(1, int(size))
        if mode == "floor":
            aligned = (size // LOFTR_DIVISIBILITY) * LOFTR_DIVISIBILITY
        else:
            aligned = ((size + LOFTR_DIVISIBILITY - 1) // LOFTR_DIVISIBILITY) * LOFTR_DIVISIBILITY
        return max(LOFTR_DIVISIBILITY, aligned)

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
