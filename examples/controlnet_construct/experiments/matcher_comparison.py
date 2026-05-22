"""Wrapper-driven matcher comparison experiment runner.

Author: Geng Xun
Created: 2026-05-22
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
from typing import Any


DEEP_MATCHER_METHODS = {"lightglue", "loftr", "superglue"}
SUPPORTED_MATCHER_METHODS = ("bf", "flann", "superpoint", "superglue", "lightglue", "loftr")
SAFE_PATH_COMPONENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


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
        return self.matcher_method.strip().lower() in DEEP_MATCHER_METHODS


@dataclass(frozen=True)
class ExperimentConfig:
    run_id: str
    description: str
    inputs: ExperimentInputs
    execution: ExecutionConfig
    methods: tuple[MethodConfig, ...]
    config_path: Path


@dataclass(frozen=True)
class ExperimentRunResult:
    run_dir: Path
    manifest_path: Path


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
    run_id = _validate_path_component(run_id.strip(), "run_id")

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
        asp360_env=_optional_string(execution_payload, "asp360_env", ExecutionConfig.asp360_env),
        deep_learning_env=_optional_string(
            execution_payload,
            "deep_learning_env",
            ExecutionConfig.deep_learning_env,
        ),
        device=_optional_string(execution_payload, "device", ExecutionConfig.device),
        skip_final_merge=_optional_bool(
            execution_payload,
            "skip_final_merge",
            ExecutionConfig.skip_final_merge,
        ),
        keep_going=_optional_bool(execution_payload, "keep_going", ExecutionConfig.keep_going),
        resume=_optional_bool(execution_payload, "resume", ExecutionConfig.resume),
    )

    methods_payload = payload.get("methods")
    if not isinstance(methods_payload, list) or not methods_payload:
        raise ValueError("methods must be a non-empty array")

    methods: list[MethodConfig] = []
    labels: set[str] = set()
    for index, method_payload in enumerate(methods_payload):
        if not isinstance(method_payload, dict):
            raise ValueError(f"methods[{index}] must be an object")

        label = _validate_path_component(_require_string(method_payload, "label"), "label")
        if label in labels:
            raise ValueError(f"Duplicate method label: {label}")
        labels.add(label)

        matcher_method = _require_string(method_payload, "matcher_method").lower()
        if matcher_method not in SUPPORTED_MATCHER_METHODS:
            supported = ", ".join(SUPPORTED_MATCHER_METHODS)
            raise ValueError(f"Unsupported matcher_method {matcher_method!r}; supported values: {supported}")
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
        run_id=run_id,
        description=_optional_string(payload, "description", ""),
        inputs=inputs,
        execution=execution,
        methods=tuple(methods),
        config_path=config_path,
    )


def prepare_method_workspace(
    method_dir: str | Path,
    *,
    original_images_list: str | Path,
    doms_list: str | Path,
) -> Path:
    method_dir = Path(method_dir).expanduser().resolve()
    work_dir = method_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(Path(original_images_list).expanduser(), work_dir / "original_images.lis")
    shutil.copyfile(Path(doms_list).expanduser(), work_dir / "doms_scaled.lis")

    return work_dir


def _prepare_dry_run_workspace(
    method_dir: str | Path,
    *,
    original_images_list: str | Path,
    doms_list: str | Path,
) -> list[str]:
    method_dir = Path(method_dir).expanduser().resolve()
    work_dir = method_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    dry_run_inputs = (
        (Path(original_images_list).expanduser(), work_dir / "original_images.lis"),
        (Path(doms_list).expanduser(), work_dir / "doms_scaled.lis"),
    )
    for source_path, target_path in dry_run_inputs:
        if source_path.exists():
            shutil.copyfile(source_path, target_path)
        else:
            target_path.unlink(missing_ok=True)
            warnings.append(f"Dry-run input list missing; not copied: {source_path}")

    return warnings


def build_method_command(
    config: ExperimentConfig,
    method: MethodConfig,
    *,
    method_dir: str | Path,
    repo_root: str | Path,
    keep_going: bool | None = None,
) -> list[str]:
    repo_root = Path(repo_root).expanduser().resolve()
    method_dir = Path(method_dir).expanduser().resolve()
    work_dir = method_dir / "work"
    effective_keep_going = config.execution.keep_going if keep_going is None else keep_going

    if method.is_deep_method:
        script_path = repo_root / "examples/controlnet_construct/run_deep_match_pipeline.sh"
        command = [
            "bash",
            str(script_path),
            "--work-dir",
            str(work_dir),
            "--config",
            str(config.inputs.controlnet_config),
            "--matcher-method",
            method.matcher_method,
            "--asp360-env",
            config.execution.asp360_env,
            "--deep-learning-env",
            config.execution.deep_learning_env,
            "--device",
            config.execution.device,
        ]
        if method.deep_match_config_path is not None:
            command.extend(["--deep-match-config-path", str(method.deep_match_config_path)])
        if effective_keep_going:
            command.extend(["--no-fail-fast", "--continue-on-deep-failure"])
    else:
        script_path = repo_root / "examples/controlnet_construct/run_pipeline_example.sh"
        command = [
            "bash",
            str(script_path),
            "--work-dir",
            str(work_dir),
            "--config",
            str(config.inputs.controlnet_config),
            "--matcher-method",
            method.matcher_method,
        ]

    if config.execution.skip_final_merge:
        command.append("--skip-final-merge")

    return command


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _shell_quote_args(command: list[str]) -> str:
    import shlex

    return " ".join(shlex.quote(part) for part in command)


def _write_command_script(path: str | Path, command: list[str]) -> None:
    path = Path(path)
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n\n"
        f"{_shell_quote_args(command)}\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _existing_success(metrics_path: str | Path, command: list[str]) -> bool:
    metrics_path = Path(metrics_path)
    if not metrics_path.exists():
        return False

    try:
        with metrics_path.open(encoding="utf-8") as metrics_file:
            payload = json.load(metrics_file)
    except (OSError, json.JSONDecodeError):
        return False

    return isinstance(payload, dict) and payload.get("status") == "success" and payload.get("command") == command


def _method_manifest_entry(
    method: MethodConfig,
    method_dir: str | Path,
    command: list[str] | None,
    status: str,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    method_dir = Path(method_dir)
    return {
        "label": method.label,
        "matcher_method": method.matcher_method,
        "deep_match_config_path": (
            str(method.deep_match_config_path) if method.deep_match_config_path is not None else None
        ),
        "method_dir": str(method_dir),
        "work_dir": str(method_dir / "work"),
        "command": command,
        "status": status,
        "warnings": warnings or [],
    }


def run_experiment(
    config_path: str | Path,
    *,
    output_root: str | Path,
    repo_root: str | Path | None = None,
    dry_run: bool = False,
    only_labels: set[str] | None = None,
    resume: bool | None = None,
    keep_going: bool | None = None,
) -> ExperimentRunResult:
    if repo_root is None:
        repo_root_path = Path(__file__).resolve().parents[3]
    else:
        repo_root_path = Path(repo_root).expanduser().resolve()

    config = load_experiment_config(config_path, repo_root=repo_root_path)
    effective_resume = config.execution.resume if resume is None else resume
    effective_keep_going = config.execution.keep_going if keep_going is None else keep_going

    configured_labels = {method.label for method in config.methods}
    if only_labels is None:
        selected_methods = config.methods
    else:
        unknown_labels = sorted(only_labels - configured_labels)
        if unknown_labels:
            raise ValueError(f"Unknown method label(s): {', '.join(unknown_labels)}")
        selected_methods = tuple(method for method in config.methods if method.label in only_labels)

    if not dry_run:
        raise NotImplementedError("Real matcher comparison execution will be implemented in Task 4")

    run_dir = Path(output_root).expanduser() / config.run_id
    methods_dir = run_dir / "methods"
    reports_dir = run_dir / "reports"
    methods_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(config.config_path, run_dir / "experiment_config.json")

    method_entries: list[dict[str, Any]] = []
    for method in selected_methods:
        method_dir = methods_dir / method.label
        metrics_path = method_dir / "metrics.json"
        command = build_method_command(
            config,
            method,
            method_dir=method_dir,
            repo_root=repo_root_path,
            keep_going=effective_keep_going,
        )
        if effective_resume and _existing_success(metrics_path, command):
            method_entries.append(
                _method_manifest_entry(
                    method,
                    method_dir,
                    command,
                    "skipped_success",
                )
            )
            continue

        warnings = _prepare_dry_run_workspace(
            method_dir,
            original_images_list=config.inputs.original_images_list,
            doms_list=config.inputs.doms_list,
        )
        _write_command_script(method_dir / "command.sh", command)
        method_entries.append(
            _method_manifest_entry(
                method,
                method_dir,
                command,
                "dry_run" if dry_run else "pending",
                warnings,
            )
        )
    manifest_path = run_dir / "experiment_manifest.json"
    manifest = {
        "run_id": config.run_id,
        "description": config.description,
        "created_at_utc": _utc_now_iso(),
        "dry_run": dry_run,
        "resume": effective_resume,
        "keep_going": effective_keep_going,
        "methods": method_entries,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return ExperimentRunResult(run_dir=run_dir, manifest_path=manifest_path)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a ControlNet matcher comparison experiment.")
    parser.add_argument("config", help="Path to the matcher comparison experiment JSON config.")
    parser.add_argument(
        "--output-root",
        default="work/matcher_comparison",
        help="Directory where run outputs are created.",
    )
    parser.add_argument("--repo-root", help="Repository root used to resolve repo-relative paths.")
    parser.add_argument("--resume", dest="resume", action="store_true", default=None)
    parser.add_argument("--no-resume", dest="resume", action="store_false")
    parser.add_argument("--only", help="Comma-separated method labels to run.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare manifests and command scripts only.")
    parser.add_argument("--keep-going", dest="keep_going", action="store_true", default=None)
    parser.add_argument("--fail-fast", dest="keep_going", action="store_false")
    return parser


def _parse_only(value: str | None) -> set[str] | None:
    if value is None:
        return None
    labels = {label.strip() for label in value.split(",") if label.strip()}
    if not labels:
        raise ValueError("--only must include at least one method label")
    return labels or None


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    result = run_experiment(
        args.config,
        output_root=args.output_root,
        repo_root=args.repo_root,
        dry_run=args.dry_run,
        only_labels=_parse_only(args.only),
        resume=args.resume,
        keep_going=args.keep_going,
    )
    print(f"Experiment manifest: {result.manifest_path}")
    return 0


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _validate_path_component(value: str, field_name: str) -> str:
    if (
        not value
        or Path(value).is_absolute()
        or ".." in value
        or "/" in value
        or "\\" in value
        or not SAFE_PATH_COMPONENT_RE.fullmatch(value)
    ):
        raise ValueError(f"{field_name} must match [A-Za-z0-9][A-Za-z0-9._-]* and be a safe path component")
    return value


def _optional_string(payload: dict[str, Any], key: str, default: str) -> str:
    value = payload.get(key, default)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value.strip()


def _optional_bool(payload: dict[str, Any], key: str, default: bool) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
