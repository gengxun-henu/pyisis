"""Deep-learning matcher preset loading, validation, and runtime resolution.

Author: Geng Xun
Created: 2026-05-16
Updated: 2026-05-19  Geng Xun added runtime config resolution for matcher execution layers.
Updated: 2026-05-20  Geng Xun added dependency preflight checks and runtime-config rehydration helpers for exported deep-match manifests.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
from pathlib import Path
from typing import Any

# 支持的深度学习匹配器
DEEP_MATCHER_METHODS = ("superglue", "lightglue", "loftr")

# 支持的特征提取器（loftr 使用内置特征提取，不需要独立提取器）
SUPPORTED_EXTRACTOR_METHODS = ("superpoint", "disk", "aliked", "doghardnet", "loftr")


@dataclass(frozen=True, slots=True)
class DeepMatchRuntimeConfig:
    """Resolved deep matcher preset values consumed by execution layers."""

    matcher_method: str
    feature_extractor_method: str
    prefer_gpu: bool
    device_dtype: str
    fallback_on_error: str | None
    raw_config: dict[str, Any]


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
        for message in (
            _check_import("torch"),
            _check_import("kornia.feature", attribute_name="LoFTR", missing_name="kornia.feature.LoFTR"),
        ):
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
        if on_error is not None and on_error not in ("sift_bf", "sift_flann", None):
            raise ValueError(
                f"不支持的 fallback 方法 '{on_error}'。"
                f"支持的 fallback: sift_bf, sift_flann, null"
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
