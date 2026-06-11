"""Deep-learning matcher preset loading, validation, and runtime resolution.

Author: Geng Xun
Created: 2026-05-16
Updated: 2026-05-19  Geng Xun added runtime config resolution for matcher execution layers.
Updated: 2026-05-19  Geng Xun added matcher/feature/device option dictionaries for reproducible deep matcher construction.
Updated: 2026-05-20  Geng Xun added fail-fast matcher and feature-extractor compatibility validation for deep presets.
Updated: 2026-05-20  Geng Xun added dependency preflight checks and runtime-config rehydration helpers for exported deep-match manifests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import json
import math
from pathlib import Path
from typing import Any

# 支持的深度学习匹配器
DEEP_MATCHER_METHODS = ("superglue", "lightglue", "loftr")

# 支持的特征提取器（loftr 使用内置特征提取，不需要独立提取器）
SUPPORTED_EXTRACTOR_METHODS = ("superpoint", "disk", "aliked", "doghardnet", "lightglue_sift", "loftr")
LIGHTGLUE_BACKENDS = (None, "official")
OFFICIAL_LIGHTGLUE_EXTRACTOR_METHODS = ("superpoint", "disk", "aliked", "doghardnet", "lightglue_sift")
OFFICIAL_LIGHTGLUE_FEATURE_OPTIONS = {"method", "max_features", "max_keypoints"}
OFFICIAL_LIGHTGLUE_MATCHER_OPTIONS = {
    "method",
    "backend",
    "filter_threshold",
    "depth_confidence",
    "width_confidence",
    "flash",
    "mp",
}
LOFTR_BACKENDS = (None, "kornia", "external")
EXTERNAL_LOFTR_MODEL_TYPES = ("indoor", "outdoor")
EXTERNAL_LOFTR_TEMP_BUG_FIX_VALUES = ("auto", "true", "false")
EXTERNAL_LOFTR_PREPROCESS_MODES = ("pad", "resize")
EXTERNAL_LOFTR_GEOMETRIC_FILTERS = ("none", "homography", "fundamental")
EXTERNAL_LOFTR_FEATURE_OPTIONS = {"method", "preprocess_mode", "resize_width", "resize_height"}
EXTERNAL_LOFTR_MATCHER_OPTIONS = {
    "method",
    "backend",
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
}
MATCHER_EXTRACTOR_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "lightglue": ("superpoint",),
    "superglue": ("superpoint",),
    "loftr": ("loftr",),
}


@dataclass(frozen=True, slots=True)
class DeepMatchRuntimeConfig:
    """Resolved deep matcher preset values consumed by execution layers."""

    matcher_method: str
    feature_extractor_method: str
    prefer_gpu: bool
    device_dtype: str
    fallback_on_error: str | None
    raw_config: dict[str, Any]
    matcher_options: dict[str, Any] = field(default_factory=dict)
    feature_options: dict[str, Any] = field(default_factory=dict)
    device_options: dict[str, Any] = field(default_factory=dict)


def _section_options(section: dict[str, Any] | None) -> dict[str, Any]:
    section_dict = dict(section or {})
    section_dict.pop("method", None)
    return section_dict


def _payload_options(
    mapping: dict[str, Any],
    key: str,
    *,
    raw_config: dict[str, Any],
    raw_section: str,
) -> dict[str, Any]:
    options = mapping.get(key)
    if isinstance(options, dict):
        return dict(options)
    section = raw_config.get(raw_section)
    if isinstance(section, dict):
        return _section_options(section)
    return {}


def _normalized_backend(matcher: dict[str, Any]) -> str | None:
    backend_value = matcher.get("backend")
    if backend_value is None:
        return None
    normalized_backend = str(backend_value).strip().lower()
    return normalized_backend or None


def _normalized_lightglue_backend(matcher: dict[str, Any]) -> str | None:
    return _normalized_backend(matcher)


def _validate_positive_number(*, section_name: str, field_name: str, value: Any) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{section_name}.{field_name} must be a positive number.")


def _validate_probability(*, section_name: str, field_name: str, value: Any) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 < value <= 1
    ):
        raise ValueError(f"{section_name}.{field_name} must be in (0, 1].")


def _validate_positive_int(*, section_name: str, field_name: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{section_name}.{field_name} must be a positive integer.")


def _validate_option_choice(
    *,
    section_name: str,
    field_name: str,
    value: Any,
    allowed_values: tuple[str, ...],
) -> None:
    normalized_value = str(value).strip().lower()
    if normalized_value not in allowed_values:
        supported_display = ", ".join(repr(option) for option in allowed_values)
        raise ValueError(
            f"{section_name}.{field_name} must be one of ({supported_display}); "
            f"got {value!r}."
        )


def _reject_unknown_options(
    *,
    section_name: str,
    section: dict[str, Any],
    allowed_options: set[str],
    backend_label: str = "official LightGlue",
) -> None:
    unknown_options = sorted(set(section) - allowed_options)
    if unknown_options:
        raise ValueError(
            f"unknown {section_name} option(s) for {backend_label} backend: "
            f"{', '.join(unknown_options)}"
        )


def _validate_official_lightglue_options(
    *,
    matcher: dict[str, Any],
    feature_extractor: dict[str, Any],
) -> None:
    _reject_unknown_options(
        section_name="feature_extractor",
        section=feature_extractor,
        allowed_options=OFFICIAL_LIGHTGLUE_FEATURE_OPTIONS,
    )
    if "max_features" in feature_extractor and "max_keypoints" in feature_extractor:
        raise ValueError(
            "official LightGlue feature_extractor options must not include both "
            "max_features and max_keypoints."
        )
    _reject_unknown_options(
        section_name="matcher",
        section=matcher,
        allowed_options=OFFICIAL_LIGHTGLUE_MATCHER_OPTIONS,
    )


def _validate_external_loftr_options(
    *,
    matcher: dict[str, Any],
    feature_extractor: dict[str, Any],
) -> None:
    _reject_unknown_options(
        section_name="feature_extractor",
        section=feature_extractor,
        allowed_options=EXTERNAL_LOFTR_FEATURE_OPTIONS,
        backend_label="external LoFTR",
    )
    _reject_unknown_options(
        section_name="matcher",
        section=matcher,
        allowed_options=EXTERNAL_LOFTR_MATCHER_OPTIONS,
        backend_label="external LoFTR",
    )

    if "checkpoint" in matcher and "checkpoint_path" in matcher:
        raise ValueError(
            "external LoFTR matcher options must not include both checkpoint "
            "and checkpoint_path."
        )

    if "preprocess_mode" in feature_extractor:
        _validate_option_choice(
            section_name="feature_extractor",
            field_name="preprocess_mode",
            value=feature_extractor["preprocess_mode"],
            allowed_values=EXTERNAL_LOFTR_PREPROCESS_MODES,
        )

    resize_width_present = "resize_width" in feature_extractor
    resize_height_present = "resize_height" in feature_extractor
    if resize_width_present != resize_height_present:
        raise ValueError(
            "external LoFTR feature_extractor options must include resize_width "
            "and resize_height together."
        )
    if resize_width_present:
        _validate_positive_int(
            section_name="feature_extractor",
            field_name="resize_width",
            value=feature_extractor["resize_width"],
        )
        _validate_positive_int(
            section_name="feature_extractor",
            field_name="resize_height",
            value=feature_extractor["resize_height"],
        )

    for field_name, allowed_values in (
        ("model_type", EXTERNAL_LOFTR_MODEL_TYPES),
        ("temp_bug_fix", EXTERNAL_LOFTR_TEMP_BUG_FIX_VALUES),
        ("geometric_filter", EXTERNAL_LOFTR_GEOMETRIC_FILTERS),
    ):
        if field_name in matcher:
            _validate_option_choice(
                section_name="matcher",
                field_name=field_name,
                value=matcher[field_name],
                allowed_values=allowed_values,
            )

    for field_name in (
        "coarse_threshold",
        "min_confidence",
        "ransac_reproj_threshold",
    ):
        if field_name in matcher:
            _validate_positive_number(
                section_name="matcher",
                field_name=field_name,
                value=matcher[field_name],
            )

    if "ransac_confidence" in matcher:
        _validate_probability(
            section_name="matcher",
            field_name="ransac_confidence",
            value=matcher["ransac_confidence"],
        )

    for field_name in ("top_k", "ransac_max_iters"):
        if field_name in matcher:
            _validate_positive_int(
                section_name="matcher",
                field_name=field_name,
                value=matcher[field_name],
            )


def validate_matcher_feature_compatibility(
    *,
    matcher_method: str,
    feature_extractor_method: str,
    matcher: dict[str, Any] | None = None,
    feature_extractor: dict[str, Any] | None = None,
) -> None:
    """Reject matcher/extractor combinations that the runtime cannot execute."""
    normalized_matcher = str(matcher_method or "").strip().lower()
    normalized_extractor = str(feature_extractor_method or "").strip().lower()
    matcher_dict = dict(matcher or {})
    feature_extractor_dict = dict(feature_extractor or {})

    if normalized_matcher == "lightglue":
        backend = _normalized_lightglue_backend(matcher_dict)
        if backend not in LIGHTGLUE_BACKENDS:
            raise ValueError(
                f"unsupported lightglue matcher.backend={backend!r}; "
                "supported backends: official"
            )
        if backend == "official":
            if normalized_extractor not in OFFICIAL_LIGHTGLUE_EXTRACTOR_METHODS:
                supported_display = ", ".join(repr(method) for method in OFFICIAL_LIGHTGLUE_EXTRACTOR_METHODS)
                raise ValueError(
                    f"matcher.method='lightglue' with backend='official' requires "
                    f"feature_extractor.method to be one of ({supported_display}); "
                    f"got {normalized_extractor!r}."
                )
            _validate_official_lightglue_options(
                matcher=matcher_dict,
                feature_extractor=feature_extractor_dict,
            )
            return

    if normalized_matcher == "loftr":
        backend = _normalized_backend(matcher_dict)
        if backend not in LOFTR_BACKENDS:
            raise ValueError(
                f"unsupported LoFTR matcher.backend={backend!r}; "
                "supported backends: kornia, external"
            )
        if normalized_extractor != "loftr":
            raise ValueError(
                f"matcher.method='loftr' requires feature_extractor.method='loftr'; "
                f"got {normalized_extractor!r}."
            )
        if backend == "external":
            _validate_external_loftr_options(
                matcher=matcher_dict,
                feature_extractor=feature_extractor_dict,
            )
        return

    supported_extractors = MATCHER_EXTRACTOR_REQUIREMENTS.get(normalized_matcher)
    if supported_extractors is None or normalized_extractor in supported_extractors:
        return
    supported_display = ", ".join(repr(method) for method in supported_extractors)
    raise ValueError(
        f"matcher.method={normalized_matcher!r} requires feature_extractor.method to be one of "
        f"({supported_display}); got {normalized_extractor!r}."
    )


def deep_match_runtime_config_from_payload(
    payload: DeepMatchRuntimeConfig | dict[str, Any] | None,
    *,
    matcher_method: str | None = None,
    prefer_gpu: bool | None = None,
) -> DeepMatchRuntimeConfig | None:
    """Rehydrate a runtime config from serialized manifest payload data."""

    if isinstance(payload, DeepMatchRuntimeConfig):
        return payload

    mapping = dict(payload or {})
    resolved_matcher_method = str(mapping.get("matcher_method") or matcher_method or "").strip().lower()
    if not resolved_matcher_method:
        return None

    default_extractor = "loftr" if resolved_matcher_method == "loftr" else "superpoint"
    prefer_gpu_value = mapping.get("prefer_gpu")
    resolved_prefer_gpu = bool(prefer_gpu_value) if prefer_gpu_value is not None else bool(prefer_gpu)
    raw_config = mapping.get("raw_config")
    if not isinstance(raw_config, dict):
        raw_config = {}

    return DeepMatchRuntimeConfig(
        matcher_method=resolved_matcher_method,
        feature_extractor_method=str(mapping.get("feature_extractor_method") or default_extractor).strip().lower(),
        prefer_gpu=resolved_prefer_gpu,
        device_dtype=str(mapping.get("device_dtype", "float32")).strip().lower(),
        fallback_on_error=(
            None if mapping.get("fallback_on_error") is None else str(mapping.get("fallback_on_error"))
        ),
        raw_config=dict(raw_config),
        matcher_options=_payload_options(
            mapping,
            "matcher_options",
            raw_config=raw_config,
            raw_section="matcher",
        ),
        feature_options=_payload_options(
            mapping,
            "feature_options",
            raw_config=raw_config,
            raw_section="feature_extractor",
        ),
        device_options=_payload_options(
            mapping,
            "device_options",
            raw_config=raw_config,
            raw_section="device",
        ),
    )


def load_deep_match_config(config_path: str | Path) -> dict[str, Any]:
    """加载并校验深度学习匹配预设 JSON 文件。

    Args:
        config_path: 预设 JSON 文件路径。

    Returns:
        解析后的配置字典（已通过必填字段校验）。

    Raises:
        ValueError: 文件不存在、JSON 解析失败或必填字段缺失。
    """
    resolved = Path(config_path)
    if not resolved.exists():
        raise ValueError(f"深度学习配置文件未找到: {resolved}")

    try:
        config = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"深度学习配置文件 JSON 解析失败: {resolved}: {exc}") from exc

    validate_deep_match_config(config)
    return config


def resolve_deep_match_runtime_config(config_path: str | Path) -> DeepMatchRuntimeConfig:
    """Resolve a validated deep matcher preset into execution-facing values."""
    config = load_deep_match_config(config_path)
    extractor = config["feature_extractor"]
    matcher = config["matcher"]
    device = config.get("device", {})
    fallback = config.get("fallback", {})

    prefer_gpu_value = device.get("prefer_gpu")
    device_type = str(device.get("type", "auto")).strip().lower()
    prefer_gpu = bool(prefer_gpu_value) if prefer_gpu_value is not None else device_type != "cpu"

    return DeepMatchRuntimeConfig(
        matcher_method=str(matcher["method"]).strip().lower(),
        feature_extractor_method=str(extractor["method"]).strip().lower(),
        prefer_gpu=prefer_gpu,
        device_dtype=str(device.get("dtype", "float32")).strip().lower(),
        fallback_on_error=fallback.get("on_error"),
        matcher_options=_section_options(matcher),
        feature_options=_section_options(extractor),
        device_options=dict(device),
        raw_config=config,
    )


def _missing_dependency_message(name: str) -> str:
    return f"missing {name}"


def _check_import(module_name: str, *, attribute_name: str | None = None, missing_name: str | None = None) -> str | None:
    try:
        module = importlib.import_module(module_name)
    except (ImportError, ModuleNotFoundError):
        return _missing_dependency_message(missing_name or module_name)

    if attribute_name is None:
        return None
    if hasattr(module, attribute_name):
        return None
    return _missing_dependency_message(missing_name or f"{module_name}.{attribute_name}")


def check_deep_match_dependencies(runtime_config: DeepMatchRuntimeConfig) -> list[str]:
    """Return human-readable missing dependency messages for the selected matcher."""

    method = str(runtime_config.matcher_method).strip().lower()
    missing_messages: list[str] = []
    if method == "lightglue":
        for message in (
            _check_import("torch"),
            _check_import("lightglue"),
            _check_import("kornia"),
        ):
            if message is not None:
                missing_messages.append(message)
        return missing_messages

    if method == "loftr":
        dependency_checks = [_check_import("torch")]
        if _normalized_backend(runtime_config.matcher_options) != "external":
            dependency_checks.append(
                _check_import("kornia.feature", attribute_name="LoFTR", missing_name="kornia.feature.LoFTR")
            )
        for message in dependency_checks:
            if message is not None:
                missing_messages.append(message)
        return missing_messages

    if method == "superglue":
        for message in (
            _check_import("torch"),
            _check_import("models.matching"),
        ):
            if message is not None:
                missing_messages.append(message)
        return missing_messages

    return missing_messages


def validate_deep_match_config(config: dict[str, Any]) -> None:
    """校验深度学习匹配配置字典的必填字段。

    Args:
        config: 解析后的 JSON 配置字典。

    Raises:
        ValueError: 必填字段缺失或值不合法。
    """
    # 校验 feature_extractor
    extractor = config.get("feature_extractor")
    if extractor is None:
        raise ValueError("配置缺少 'feature_extractor' 字段")
    extractor_method = str(extractor.get("method", "")).strip().lower()
    if not extractor_method:
        raise ValueError("feature_extractor 缺少必填字段 'method'")
    if extractor_method not in SUPPORTED_EXTRACTOR_METHODS:
        raise ValueError(
            f"不支持的特征提取器方法 '{extractor_method}'。"
            f"支持的提取器: {', '.join(SUPPORTED_EXTRACTOR_METHODS)}"
        )

    # 校验 matcher
    matcher = config.get("matcher")
    if matcher is None:
        raise ValueError("配置缺少 'matcher' 字段")
    matcher_method = str(matcher.get("method", "")).strip().lower()
    if not matcher_method:
        raise ValueError("matcher 缺少必填字段 'method'")
    if matcher_method not in DEEP_MATCHER_METHODS:
        raise ValueError(
            f"不支持的匹配器方法 '{matcher_method}'。"
            f"支持的匹配器: {', '.join(DEEP_MATCHER_METHODS)}"
        )
    validate_matcher_feature_compatibility(
        matcher_method=matcher_method,
        feature_extractor_method=extractor_method,
        matcher=matcher,
        feature_extractor=extractor,
    )

    # 可选校验 device 和 fallback（如果提供了但值不合法）
    device = config.get("device")
    if device is not None:
        dtype = device.get("dtype", "float32")
        if dtype not in ("float32", "float16", "bfloat16"):
            raise ValueError(
                f"不支持的 dtype '{dtype}'。支持的 dtype: float32, float16, bfloat16"
            )

    fallback = config.get("fallback")
    if fallback is not None:
        on_error = fallback.get("on_error")
        if on_error is not None and on_error not in ("sift_bf", None):
            raise ValueError(
                f"不支持的 fallback 方法 '{on_error}'。"
                f"支持的 fallback: sift_bf, null"
            )


def is_deep_matcher(matcher_method: str) -> bool:
    """判断指定的匹配方法是否为深度学习匹配器。

    Args:
        matcher_method: 匹配方法名（如 "lightglue", "flann"）。

    Returns:
        True 如果是深度学习匹配器，否则 False。
    """
    return str(matcher_method).strip().lower() in DEEP_MATCHER_METHODS


def require_deep_config(matcher_method: str, config_path: str | None) -> None:
    """如果匹配器是深度学习匹配器，则要求配置文件路径不为空。

    Args:
        matcher_method: 匹配方法名。
        config_path: 深度学习配置文件路径，可为 None 或空字符串。

    Raises:
        ValueError: 深度学习匹配器但未指定配置文件。
    """
    if is_deep_matcher(matcher_method):
        if not config_path or not config_path.strip():
            raise ValueError(
                f"匹配方法 '{matcher_method}' 是深度学习匹配器，必须指定 "
                f"deep_matcher_config_path 配置文件。"
            )
