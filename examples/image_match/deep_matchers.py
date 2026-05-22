"""Model-backed matcher wrappers for deep matcher methods.

Author: Geng Xun
Created: 2026-05-11
Updated: 2026-05-11  Geng Xun added top-of-file metadata so example helper modules follow the repository's example-file header convention.
Updated: 2026-05-19  Geng Xun applied preset matcher parameters for LightGlue, SuperGlue, and LoFTR model construction.
Updated: 2026-05-20  Geng Xun added fail-fast matcher and feature-extractor compatibility checks before model construction.
"""

from __future__ import annotations

import copy
import importlib
import math
from pathlib import Path
import sys
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


_MATCHER_FEATURE_EXTRACTOR_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "lightglue": ("superpoint",),
    "superglue": ("superpoint",),
    "loftr": ("loftr",),
}

LOFTR_BACKENDS = {"kornia", "external", ""}
LOFTR_SUPPORTED_MODEL_TYPES = {"indoor", "outdoor"}
LOFTR_SUPPORTED_GEOMETRIC_FILTERS = {"none", "homography", "fundamental"}
LOFTR_DEFAULT_SAMPLE_CHECKPOINTS = {
    "indoor": ("weights/indoor.ckpt", "weights/indoor_ds.ckpt", "weights/indoor_ds_new.ckpt"),
    "outdoor": ("weights/outdoor.ckpt", "weights/outdoor_ds.ckpt"),
}


def _default_feature_extractor_for_matcher(matcher_method: str) -> str:
    normalized_matcher = str(matcher_method or "").strip().lower()
    supported_extractors = _MATCHER_FEATURE_EXTRACTOR_REQUIREMENTS.get(normalized_matcher)
    if supported_extractors is None:
        return "superpoint"
    return supported_extractors[0]


def _validate_feature_extractor_compatibility(
    *, matcher_method: str, feature_extractor_method: str | None
) -> str:
    normalized_matcher = str(matcher_method or "").strip().lower()
    if feature_extractor_method is None:
        normalized_extractor = _default_feature_extractor_for_matcher(normalized_matcher)
    else:
        normalized_extractor = str(feature_extractor_method).strip().lower()
    supported_extractors = _MATCHER_FEATURE_EXTRACTOR_REQUIREMENTS.get(normalized_matcher)
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


def _valid_external_loftr_root(candidate: Path) -> bool:
    return candidate.is_dir() and (candidate / "src" / "loftr" / "__init__.py").is_file()


def _find_external_loftr_root(explicit_root: str | Path | None) -> Path:
    if explicit_root not in (None, ""):
        candidate = Path(explicit_root).expanduser().resolve()
        if _valid_external_loftr_root(candidate):
            return candidate
        raise DeepMatcherError(f"Invalid external LoFTR root: {candidate}")

    checked: set[Path] = set()
    search_starts = [Path.cwd(), Path(__file__).resolve().parent]
    for start in search_starts:
        for ancestor in [start, *start.parents]:
            for candidate in (ancestor / "LoFTR", ancestor.parent / "LoFTR"):
                resolved = candidate.resolve()
                if resolved in checked:
                    continue
                checked.add(resolved)
                if _valid_external_loftr_root(resolved):
                    return resolved
    raise DeepMatcherError(
        "Could not locate an external LoFTR repository. Set matcher.loftr_root to the LoFTR checkout."
    )


def _checkpoint_option(options: dict[str, Any]) -> Any:
    if "checkpoint" in options and "checkpoint_path" in options:
        raise DeepMatcherError("External LoFTR options must not include both 'checkpoint' and 'checkpoint_path'.")
    if "checkpoint" in options:
        return options.get("checkpoint")
    return options.get("checkpoint_path")


def _resolve_external_loftr_checkpoint(checkpoint: Any, loftr_root: Path, model_type: str) -> Path:
    if checkpoint not in (None, ""):
        candidate = Path(checkpoint).expanduser()
        if not candidate.is_absolute():
            candidate = loftr_root / candidate
        resolved = candidate.resolve()
        if not resolved.is_file():
            raise DeepMatcherError(f"External LoFTR checkpoint does not exist: {resolved}")
        return resolved

    checked = []
    for relative_path in LOFTR_DEFAULT_SAMPLE_CHECKPOINTS[model_type]:
        candidate = (loftr_root / relative_path).resolve()
        checked.append(candidate)
        if candidate.is_file():
            return candidate
    checked_display = "\n  - ".join(str(path) for path in checked)
    raise DeepMatcherError(
        f"Could not find a default external LoFTR {model_type} checkpoint. Checked:\n  - {checked_display}"
    )


def _resolve_external_temp_bug_fix(option: Any, model_type: str) -> bool:
    normalized = str(option if option is not None else "auto").strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    if normalized == "auto":
        return model_type == "indoor"
    raise DeepMatcherError(
        f"External LoFTR temp_bug_fix must be one of 'auto', 'true', or 'false'; got {option!r}."
    )


def _scale_loftr_points(points: np.ndarray, metadata: dict[str, Any] | None) -> np.ndarray:
    scaled = np.asarray(points, dtype=np.float32).reshape(-1, 2).copy()
    if scaled.size <= 0:
        return scaled
    scale = (metadata or {}).get("scale", (1.0, 1.0))
    if len(scale) != 2:
        scale = (1.0, 1.0)
    scaled[:, 0] *= float(scale[0])
    scaled[:, 1] *= float(scale[1])
    return scaled.astype(np.float32, copy=False)


def _module_file_under_root(module: Any, root: Path) -> bool | None:
    module_file = getattr(module, "__file__", None)
    if not module_file:
        return None
    try:
        resolved_file = Path(module_file).expanduser().resolve()
        resolved_root = root.expanduser().resolve()
        return resolved_file == resolved_root or resolved_file.is_relative_to(resolved_root)
    except Exception:
        return False


def _clear_stale_external_loftr_modules(loftr_root: Path) -> None:
    stale_names = []
    for module_name, module in list(sys.modules.items()):
        if module_name != "src" and not module_name.startswith("src."):
            continue
        under_root = _module_file_under_root(module, loftr_root)
        if under_root is False:
            stale_names.append(module_name)
    for module_name in stale_names:
        sys.modules.pop(module_name, None)


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
        self.backend = str(self.matcher_options.get("backend") or "kornia").strip().lower()
        if self.backend not in LOFTR_BACKENDS:
            _raise_unsupported_option(method=self.method, option_name="backend", option_value=self.matcher_options.get("backend"))
        if self.backend == "":
            self.backend = "kornia"
        self.ignored_parameters: list[str] = []
        self.device_dtype = _resolve_device_dtype(
            method=self.method,
            device_options=self.device_options,
            ignored_parameters=self.ignored_parameters,
        )
        self._matcher = None

    def _loftr_pretrained(self) -> str:
        options = _copy_options(self.matcher_options)
        backend = str(options.pop("backend", self.backend) or "kornia").strip().lower()
        if backend not in {"kornia", ""}:
            if backend == "external":
                return "external"
            _raise_unsupported_option(method=self.method, option_name="backend", option_value=backend)
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

    def _external_options(self) -> dict[str, Any]:
        options = _copy_options(self.matcher_options)
        backend = str(options.pop("backend", self.backend) or "external").strip().lower()
        if backend != "external":
            _raise_unsupported_option(method=self.method, option_name="backend", option_value=backend)
        _reject_unknown_options(
            method=self.method,
            options=options,
            allowed={
                "loftr_root",
                "checkpoint",
                "checkpoint_path",
                "model_type",
                "temp_bug_fix",
                "coarse_threshold",
                "min_confidence",
                "top_k",
                "geometric_filter",
                "ransac_reproj_threshold",
                "ransac_confidence",
                "ransac_max_iters",
            },
        )
        model_type = str(options.get("model_type") or "outdoor").strip().lower()
        if model_type not in LOFTR_SUPPORTED_MODEL_TYPES:
            _raise_unsupported_option(method=self.method, option_name="model_type", option_value=options.get("model_type"))
        options["model_type"] = model_type
        geometric_filter = str(options.get("geometric_filter") or "none").strip().lower()
        if geometric_filter not in LOFTR_SUPPORTED_GEOMETRIC_FILTERS:
            _raise_unsupported_option(
                method=self.method,
                option_name="geometric_filter",
                option_value=options.get("geometric_filter"),
            )
        options["geometric_filter"] = geometric_filter
        return options

    def _load_matcher(self):
        if self.backend == "external":
            return self._load_external_matcher()
        pretrained = self._loftr_pretrained()
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
            self._matcher = kf.LoFTR(pretrained=pretrained).eval().to(device=self.device, dtype=torch_dtype)
        return torch, self._matcher

    def _load_external_matcher(self):
        try:
            import torch
        except Exception:
            raise _missing_dependency_error(
                method=self.method,
                missing="torch",
                install_hint="pip install torch",
            )

        torch_dtype = _resolve_torch_dtype(torch=torch, method=self.method, device_dtype=self.device_dtype)
        if self._matcher is None:
            options = self._external_options()
            model_type = options["model_type"]
            loftr_root = _find_external_loftr_root(options.get("loftr_root"))
            checkpoint_path = _resolve_external_loftr_checkpoint(
                _checkpoint_option(options),
                loftr_root,
                model_type,
            )
            loftr_root_text = str(loftr_root)
            if loftr_root_text not in sys.path:
                sys.path.insert(0, loftr_root_text)
            _clear_stale_external_loftr_modules(loftr_root)
            try:
                loftr_module = importlib.import_module("src.loftr")
            except Exception as error:
                raise DeepMatcherError(
                    f"Deep matcher 'loftr' failed to import external LoFTR module from {loftr_root}: {error}"
                ) from error

            config = copy.deepcopy(loftr_module.default_cfg)
            config.setdefault("coarse", {})
            config.setdefault("match_coarse", {})
            config["coarse"]["temp_bug_fix"] = _resolve_external_temp_bug_fix(
                options.get("temp_bug_fix", "auto"),
                model_type,
            )
            if options.get("coarse_threshold") is not None:
                config["match_coarse"]["thr"] = float(options["coarse_threshold"])

            matcher = loftr_module.LoFTR(config=config)
            try:
                loaded_state = torch.load(checkpoint_path, map_location=self.device, weights_only=True)
            except TypeError:
                loaded_state = torch.load(checkpoint_path, map_location=self.device)
            state_dict = loaded_state.get("state_dict", loaded_state) if isinstance(loaded_state, dict) else loaded_state
            matcher.load_state_dict(state_dict, strict=True)
            self._matcher = matcher.eval().to(device=self.device, dtype=torch_dtype)
        return torch, self._matcher

    def match(
        self,
        *,
        left_image: Any,
        right_image: Any,
        left_mask: Any = None,
        right_mask: Any = None,
        left_meta: dict[str, Any] | None = None,
        right_meta: dict[str, Any] | None = None,
        device: str = "cpu",
    ):
        torch, matcher = self._load_matcher()
        _ = device
        if self.backend == "external":
            return self._match_external(
                torch=torch,
                matcher=matcher,
                left_image=left_image,
                right_image=right_image,
                left_mask=left_mask,
                right_mask=right_mask,
                left_meta=left_meta,
                right_meta=right_meta,
            )
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

    def _match_external(
        self,
        *,
        torch: Any,
        matcher: Any,
        left_image: Any,
        right_image: Any,
        left_mask: Any = None,
        right_mask: Any = None,
        left_meta: dict[str, Any] | None = None,
        right_meta: dict[str, Any] | None = None,
    ):
        if left_image is None or right_image is None:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)

        torch_dtype = _resolve_torch_dtype(torch=torch, method=self.method, device_dtype=self.device_dtype)
        batch = {
            "image0": left_image.to(device=self.device, dtype=torch_dtype) if hasattr(left_image, "to") else left_image,
            "image1": right_image.to(device=self.device, dtype=torch_dtype) if hasattr(right_image, "to") else right_image,
        }
        if left_mask is not None:
            batch["mask0"] = self._coarsen_external_mask(
                torch=torch,
                mask=left_mask,
                image=batch["image0"],
                matcher=matcher,
            )
        if right_mask is not None:
            batch["mask1"] = self._coarsen_external_mask(
                torch=torch,
                mask=right_mask,
                image=batch["image1"],
                matcher=matcher,
            )
        self._ensure_external_position_encoding(torch=torch, matcher=matcher, batch=batch)

        inference_context = getattr(torch, "inference_mode", None)
        if inference_context is None:
            inference_context = getattr(torch, "no_grad")
        with inference_context():
            matcher(batch)

        left_points = batch["mkpts0_f"].detach().cpu().numpy().astype(np.float32, copy=False)
        right_points = batch["mkpts1_f"].detach().cpu().numpy().astype(np.float32, copy=False)
        scores = batch["mconf"].detach().cpu().numpy().astype(np.float32, copy=False).reshape(-1)
        left_points, right_points, scores = self._filter_external_matches(left_points, right_points, scores)
        left_points, right_points, scores = self._apply_external_geometric_filter(left_points, right_points, scores)
        left_points, right_points, scores = self._sort_and_limit_external_matches(left_points, right_points, scores)
        return (
            _scale_loftr_points(left_points, left_meta),
            _scale_loftr_points(right_points, right_meta),
            scores.astype(np.float32, copy=False),
        )

    def _external_coarse_stride(self, matcher: Any) -> int:
        config = getattr(matcher, "config", {}) or {}
        resolution = config.get("resolution", (8, 2))
        if isinstance(resolution, (tuple, list)) and resolution:
            return max(1, int(resolution[0]))
        return 8

    def _coarsen_external_mask(self, *, torch: Any, mask: Any, image: Any, matcher: Any) -> Any:
        image_shape = getattr(image, "shape", None)
        if image_shape is None or len(image_shape) < 2:
            return mask.to(self.device) if hasattr(mask, "to") else mask
        stride = self._external_coarse_stride(matcher)
        image_height = int(image_shape[-2])
        image_width = int(image_shape[-1])
        coarse_height = max(1, int(math.ceil(image_height / stride)))
        coarse_width = max(1, int(math.ceil(image_width / stride)))
        batch_size = int(image_shape[0]) if len(image_shape) >= 4 else 1

        torch_nn = getattr(torch, "nn", None)
        functional = getattr(torch_nn, "functional", None)
        interpolate = getattr(functional, "interpolate", None)
        if interpolate is not None and hasattr(mask, "dim"):
            mask_tensor = mask.to(self.device) if hasattr(mask, "to") else mask
            if mask_tensor.dim() == 2:
                mask_tensor = mask_tensor[None, None].float()
            elif mask_tensor.dim() == 3:
                mask_tensor = mask_tensor[:, None].float()
            elif mask_tensor.dim() == 4:
                mask_tensor = mask_tensor.float()
            else:
                return mask_tensor
            coarse = interpolate(mask_tensor, size=(coarse_height, coarse_width), mode="nearest")
            if hasattr(coarse, "bool"):
                coarse = coarse.bool()
            return coarse[:, 0]

        mask_array = np.asarray(getattr(mask, "array", mask), dtype=bool)
        if mask_array.ndim == 2:
            mask_array = mask_array[None, :, :]
        elif mask_array.ndim == 4:
            mask_array = mask_array[:, 0, :, :]
        elif mask_array.ndim != 3:
            return mask
        if mask_array.shape[0] == 1 and batch_size > 1:
            mask_array = np.repeat(mask_array, batch_size, axis=0)
        y_indices = np.minimum(
            np.floor(np.arange(coarse_height, dtype=np.float64) * mask_array.shape[-2] / coarse_height).astype(np.int64),
            mask_array.shape[-2] - 1,
        )
        x_indices = np.minimum(
            np.floor(np.arange(coarse_width, dtype=np.float64) * mask_array.shape[-1] / coarse_width).astype(np.int64),
            mask_array.shape[-1] - 1,
        )
        return mask_array[:, y_indices][:, :, x_indices].astype(bool, copy=False)

    def _ensure_external_position_encoding(self, *, torch: Any, matcher: Any, batch: dict[str, Any]) -> None:
        pe = getattr(getattr(matcher, "pos_encoding", None), "pe", None)
        pe_shape = getattr(pe, "shape", None)
        if pe_shape is None or len(pe_shape) < 2:
            return

        config = getattr(matcher, "config", {}) or {}
        resolution = config.get("resolution", (8, 2))
        coarse_stride = int(resolution[0] if isinstance(resolution, (tuple, list)) and resolution else 8)
        required_height = 0
        required_width = 0
        for image_name in ("image0", "image1"):
            image_shape = getattr(batch.get(image_name), "shape", None)
            if image_shape is None or len(image_shape) < 2:
                continue
            image_height = int(image_shape[-2])
            image_width = int(image_shape[-1])
            required_height = max(required_height, max(1, int(math.ceil(image_height / coarse_stride))))
            required_width = max(required_width, max(1, int(math.ceil(image_width / coarse_stride))))
        if required_height <= 0 or required_width <= 0:
            return
        current_height = int(pe_shape[-2])
        current_width = int(pe_shape[-1])
        if required_height <= current_height and required_width <= current_width:
            return

        try:
            position_module = importlib.import_module("src.loftr.utils.position_encoding")
            position_encoding = position_module.PositionEncodingSine(
                int((config.get("coarse") or {}).get("d_model", 256)),
                max_shape=(max(required_height, current_height), max(required_width, current_width)),
                temp_bug_fix=bool((config.get("coarse") or {}).get("temp_bug_fix", False)),
            )
            if hasattr(position_encoding, "to"):
                torch_dtype = _resolve_torch_dtype(torch=torch, method=self.method, device_dtype=self.device_dtype)
                matcher.pos_encoding = position_encoding.to(device=self.device, dtype=torch_dtype)
            else:
                matcher.pos_encoding = position_encoding
        except Exception as error:
            raise DeepMatcherError(f"Failed to resize external LoFTR position encoding: {error}") from error

    def _filter_external_matches(
        self,
        left_points: np.ndarray,
        right_points: np.ndarray,
        scores: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        options = self._external_options()
        min_confidence = options.get("min_confidence")
        if min_confidence is not None:
            keep = scores >= float(min_confidence)
            left_points = left_points[keep]
            right_points = right_points[keep]
            scores = scores[keep]
        if scores.size <= 0:
            return left_points[:0].astype(np.float32, copy=False), right_points[:0].astype(np.float32, copy=False), scores[:0].astype(np.float32, copy=False)
        return (
            left_points.astype(np.float32, copy=False),
            right_points.astype(np.float32, copy=False),
            scores.astype(np.float32, copy=False),
        )

    def _sort_and_limit_external_matches(
        self,
        left_points: np.ndarray,
        right_points: np.ndarray,
        scores: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if scores.size <= 0:
            return left_points[:0], right_points[:0], scores[:0]
        order = np.argsort(-scores)
        top_k = self._external_options().get("top_k")
        if top_k is not None and int(top_k) > 0:
            order = order[: int(top_k)]
        return (
            left_points[order].astype(np.float32, copy=False),
            right_points[order].astype(np.float32, copy=False),
            scores[order].astype(np.float32, copy=False),
        )

    def _apply_external_geometric_filter(
        self,
        left_points: np.ndarray,
        right_points: np.ndarray,
        scores: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        options = self._external_options()
        method = str(options.get("geometric_filter") or "none").strip().lower()
        if method == "none" or scores.size <= 0:
            return left_points, right_points, scores
        required_points = 4 if method == "homography" else 8
        if scores.size < required_points:
            return left_points, right_points, scores
        try:
            import cv2
        except Exception:
            raise _missing_dependency_error(
                method=self.method,
                missing="cv2",
                install_hint="conda install opencv",
            )

        reproj_threshold = float(options.get("ransac_reproj_threshold") or 3.0)
        confidence = float(options.get("ransac_confidence") or 0.999)
        max_iters = int(options.get("ransac_max_iters") or 10000)
        if method == "homography":
            try:
                _, mask = cv2.findHomography(
                    left_points.astype(np.float64),
                    right_points.astype(np.float64),
                    method=cv2.RANSAC,
                    ransacReprojThreshold=reproj_threshold,
                    confidence=confidence,
                    maxIters=max_iters,
                )
            except TypeError:
                _, mask = cv2.findHomography(
                    left_points.astype(np.float64),
                    right_points.astype(np.float64),
                    method=cv2.RANSAC,
                    ransacReprojThreshold=reproj_threshold,
                    confidence=confidence,
                )
        else:
            method_id = getattr(cv2, "USAC_MAGSAC", getattr(cv2, "FM_RANSAC", cv2.RANSAC))
            try:
                _, mask = cv2.findFundamentalMat(
                    left_points.astype(np.float64),
                    right_points.astype(np.float64),
                    method=method_id,
                    ransacReprojThreshold=reproj_threshold,
                    confidence=confidence,
                    maxIters=max_iters,
                )
            except TypeError:
                _, mask = cv2.findFundamentalMat(
                    left_points.astype(np.float64),
                    right_points.astype(np.float64),
                    method=method_id,
                    ransacReprojThreshold=reproj_threshold,
                    confidence=confidence,
                )
        if mask is None:
            return left_points[:0], right_points[:0], scores[:0]
        keep = mask.reshape(-1).astype(bool)
        if keep.size != scores.size:
            keep = keep[: scores.size]
        return left_points[keep], right_points[keep], scores[keep]


def build_deep_matcher(
    method: str,
    *,
    device: str = "cpu",
    feature_extractor_method: str | None = None,
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
