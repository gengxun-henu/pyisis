"""Wrapper-driven matcher comparison experiment runner.

Author: Geng Xun
Created: 2026-05-22
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


DEEP_MATCHER_METHODS = {"lightglue", "loftr", "superglue"}


@dataclass(frozen=True)
class ExperimentInputs:
    original_images_list: Path
    doms_list: Path
    controlnet_config: Path


@dataclass(frozen=True)
class ExecutionConfig:
    asp360_env: str = "asp360_new"
    deep_learning_env: str = "deep-learning"
    device: str = "auto"
    skip_final_merge: bool = False
    keep_going: bool = True
    resume: bool = True


@dataclass(frozen=True)
class MethodConfig:
    label: str
    matcher_method: str
    deep_match_config_path: Path | None = None

    @property
    def is_deep_method(self) -> bool:
        return self.matcher_method in DEEP_MATCHER_METHODS


@dataclass(frozen=True)
class ExperimentConfig:
    run_id: str
    description: str
    inputs: ExperimentInputs
    execution: ExecutionConfig
    methods: tuple[MethodConfig, ...]
    config_path: Path


def _resolve_path(value: str | Path, base_dir: Path, repo_root: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path

    config_relative = base_dir / path
    if config_relative.exists():
        return config_relative.resolve()
    return (repo_root / path).resolve()


def _require_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def load_experiment_config(config_path: str | Path, *, repo_root: str | Path | None = None) -> ExperimentConfig:
    config_path = Path(config_path).expanduser().resolve()
    if repo_root is None:
        repo_root_path = Path(__file__).resolve().parents[3]
    else:
        repo_root_path = Path(repo_root).expanduser().resolve()

    with config_path.open(encoding="utf-8") as config_file:
        payload = json.load(config_file)

    if not isinstance(payload, dict):
        raise ValueError("Experiment config must be a JSON object")

    run_id = payload.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id must be a non-empty string")

    inputs_payload = _require_mapping(payload, "inputs")
    inputs = ExperimentInputs(
        original_images_list=_resolve_path(
            _require_string(inputs_payload, "original_images_list"),
            config_path.parent,
            repo_root_path,
        ),
        doms_list=_resolve_path(
            _require_string(inputs_payload, "doms_list"),
            config_path.parent,
            repo_root_path,
        ),
        controlnet_config=_resolve_path(
            _require_string(inputs_payload, "controlnet_config"),
            config_path.parent,
            repo_root_path,
        ),
    )

    execution_payload = payload.get("execution", {})
    if not isinstance(execution_payload, dict):
        raise ValueError("execution must be an object")
    execution = ExecutionConfig(
        asp360_env=execution_payload.get("asp360_env", ExecutionConfig.asp360_env),
        deep_learning_env=execution_payload.get("deep_learning_env", ExecutionConfig.deep_learning_env),
        device=execution_payload.get("device", ExecutionConfig.device),
        skip_final_merge=execution_payload.get("skip_final_merge", ExecutionConfig.skip_final_merge),
        keep_going=execution_payload.get("keep_going", ExecutionConfig.keep_going),
        resume=execution_payload.get("resume", ExecutionConfig.resume),
    )

    methods_payload = payload.get("methods")
    if not isinstance(methods_payload, list) or not methods_payload:
        raise ValueError("methods must be a non-empty array")

    methods: list[MethodConfig] = []
    labels: set[str] = set()
    for index, method_payload in enumerate(methods_payload):
        if not isinstance(method_payload, dict):
            raise ValueError(f"methods[{index}] must be an object")

        label = _require_string(method_payload, "label")
        if label in labels:
            raise ValueError(f"Duplicate method label: {label}")
        labels.add(label)

        matcher_method = _require_string(method_payload, "matcher_method").lower()
        deep_match_config_path = method_payload.get("deep_match_config_path")
        resolved_deep_match_config_path = None
        if deep_match_config_path is not None:
            if not isinstance(deep_match_config_path, str) or not deep_match_config_path.strip():
                raise ValueError(f"Method {label} deep_match_config_path must be a non-empty string")
            resolved_deep_match_config_path = _resolve_path(
                deep_match_config_path,
                config_path.parent,
                repo_root_path,
            )

        method = MethodConfig(
            label=label,
            matcher_method=matcher_method,
            deep_match_config_path=resolved_deep_match_config_path,
        )
        if method.is_deep_method and method.deep_match_config_path is None:
            raise ValueError(f"Method {label} requires deep_match_config_path")
        methods.append(method)

    return ExperimentConfig(
        run_id=run_id.strip(),
        description=payload.get("description", ""),
        inputs=inputs,
        execution=execution,
        methods=tuple(methods),
        config_path=config_path,
    )


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()
