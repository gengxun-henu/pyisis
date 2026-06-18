"""Wrapper-driven matcher comparison experiment runner.

Author: Geng Xun
Created: 2026-05-22
Updated: 2026-06-18  Geng Xun included command paths in Windows launch-failure logs.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any


DEEP_MATCHER_METHODS = {"lightglue", "loftr", "superglue"}
SUPPORTED_MATCHER_METHODS = ("bf", "flann", "superpoint", "superglue", "lightglue", "loftr")
SAFE_PATH_COMPONENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
REPORT_COLUMNS = (
    "label",
    "status",
    "return_code",
    "total_wall_seconds",
    "pipeline_total_seconds",
    "pair_count",
    "pairwise_controlnet_count",
    "merged_controlnet_exists",
    "total_final_control_point_count",
    "total_dom2ori_retained_count",
    "stdout_log",
    "stderr_log",
)
REPORT_OUTPUT_NAMES = ("summary.json", "summary.csv", "summary.md", "failures.json")
SUCCESS_STATUSES = {"success", "skipped_success"}
RESUME_FINGERPRINT_VERSION = 1


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
    status: str


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
            command.append("--no-fail-fast")
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


def _hash_file(path: Path) -> tuple[dict[str, Any], bool]:
    path = path.expanduser()
    resolved_path = path.resolve(strict=False)
    fingerprint: dict[str, Any] = {
        "path": str(resolved_path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "size_bytes": None,
        "sha256": None,
    }
    if not path.is_file():
        return fingerprint, False

    sha256 = hashlib.sha256()
    try:
        stat = path.stat()
        with path.open("rb") as input_file:
            for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
                sha256.update(chunk)
    except OSError as exc:
        fingerprint["read_error"] = f"{type(exc).__name__}: {exc}"
        return fingerprint, False

    fingerprint["size_bytes"] = stat.st_size
    fingerprint["sha256"] = sha256.hexdigest()
    return fingerprint, True


def _resume_fingerprint(config: ExperimentConfig, method: MethodConfig) -> dict[str, Any]:
    files: dict[str, dict[str, Any] | None] = {}
    complete = True
    for key, path in (
        ("original_images_list", config.inputs.original_images_list),
        ("doms_list", config.inputs.doms_list),
        ("controlnet_config", config.inputs.controlnet_config),
    ):
        files[key], file_complete = _hash_file(path)
        complete = complete and file_complete

    deep_match_config_path = method.deep_match_config_path
    if deep_match_config_path is None:
        files["deep_match_config_path"] = None
    else:
        files["deep_match_config_path"], file_complete = _hash_file(deep_match_config_path)
        complete = complete and file_complete

    return {
        "version": RESUME_FINGERPRINT_VERSION,
        "complete": complete,
        "files": files,
    }


def _existing_success(
    metrics_path: str | Path,
    command: list[str],
    resume_fingerprint: dict[str, Any] | None,
) -> bool:
    metrics_path = Path(metrics_path)
    if not metrics_path.exists():
        return False

    try:
        with metrics_path.open(encoding="utf-8") as metrics_file:
            payload = json.load(metrics_file)
    except (OSError, json.JSONDecodeError):
        return False

    if not isinstance(payload, dict):
        return False
    if not isinstance(resume_fingerprint, dict) or not resume_fingerprint.get("complete"):
        return False
    return (
        payload.get("status") == "success"
        and payload.get("command") == command
        and payload.get("resume_fingerprint") == resume_fingerprint
    )


def _read_metrics_file(metrics_path: str | Path) -> dict[str, Any]:
    with Path(metrics_path).open(encoding="utf-8") as metrics_file:
        payload = json.load(metrics_file)
    if not isinstance(payload, dict):
        raise ValueError(f"Metrics file must contain an object: {metrics_path}")
    return payload


def _has_symlinked_parent(path: Path, root: Path) -> bool:
    if root.is_symlink():
        return True

    parent = path.parent
    while True:
        if parent.is_symlink():
            return True
        if parent == root or parent == parent.parent:
            return False
        parent = parent.parent


def _unlink_known_output(path: Path, root: Path) -> None:
    if _has_symlinked_parent(path, root):
        return
    if path.is_file() or path.is_symlink():
        path.unlink()


def _clear_collected_pipeline_outputs(method_dir: str | Path) -> None:
    method_dir = Path(method_dir)
    work_dir = method_dir / "work"
    reports_dir = work_dir / "reports"
    for output_path in (
        reports_dir / "image_overlap_summary.json",
        reports_dir / "controlnet_batch_summary.json",
        reports_dir / "pipeline_timing.json",
        work_dir / "merge/dom_matching_merged.net",
    ):
        _unlink_known_output(output_path, work_dir)

    pair_nets_dir = work_dir / "pair_nets"
    if pair_nets_dir.exists() and not pair_nets_dir.is_symlink() and not work_dir.is_symlink():
        for pair_net_path in pair_nets_dir.glob("*.net"):
            _unlink_known_output(pair_net_path, work_dir)


def _read_json_if_present(path: Path, warnings: list[str], *, root: Path | None = None) -> dict[str, Any] | None:
    if root is not None and _has_symlinked_parent(path, root):
        warnings.append(f"skipped symlinked parent path: {path}")
        return None

    if not path.exists():
        warnings.append(f"missing: {path}")
        return None

    try:
        with path.open(encoding="utf-8") as metrics_file:
            payload = json.load(metrics_file)
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"could not parse {path}: {exc}")
        return None

    if not isinstance(payload, dict):
        warnings.append(f"not an object: {path}")
        return None

    return payload


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _pipeline_total_seconds(timing_payload: dict[str, Any] | None, warnings: list[str], timing_path: Path) -> int | float | None:
    if timing_payload is None:
        return None

    total_seconds = timing_payload.get("total_seconds")
    if _is_number(total_seconds):
        return total_seconds

    steps = timing_payload.get("steps")
    if isinstance(steps, list):
        step_total = 0.0
        found_duration = False
        for step in steps:
            if not isinstance(step, dict):
                continue
            duration_seconds = step.get("duration_seconds")
            if _is_number(duration_seconds):
                step_total += duration_seconds
                found_duration = True
        if found_duration:
            return step_total

    warnings.append(f"could not derive pipeline_total_seconds: {timing_path}")
    return None


def collect_method_metrics(label: str, method_dir: str | Path) -> dict[str, Any]:
    method_dir = Path(method_dir).expanduser().resolve()
    work_dir = method_dir / "work"
    reports_dir = work_dir / "reports"
    warnings: list[str] = []

    overlap_summary = _read_json_if_present(reports_dir / "image_overlap_summary.json", warnings, root=work_dir)
    controlnet_summary = _read_json_if_present(
        reports_dir / "controlnet_batch_summary.json",
        warnings,
        root=work_dir,
    )
    pipeline_timing_path = reports_dir / "pipeline_timing.json"
    pipeline_timing = _read_json_if_present(pipeline_timing_path, warnings, root=work_dir)

    pair_count = None
    if controlnet_summary is not None:
        pair_count = controlnet_summary.get("pair_count")
    if pair_count is None and overlap_summary is not None:
        pair_count = overlap_summary.get("pair_count", overlap_summary.get("overlap_pair_count"))

    pair_nets_dir = work_dir / "pair_nets"
    if _has_symlinked_parent(pair_nets_dir / "placeholder", work_dir) or pair_nets_dir.is_symlink():
        warnings.append(f"skipped symlinked pair_nets path: {pair_nets_dir}")
        pairwise_controlnet_count = 0
    else:
        pairwise_controlnet_count = len(list(pair_nets_dir.glob("*.net"))) if pair_nets_dir.exists() else 0
    merged_controlnet_path = work_dir / "merge/dom_matching_merged.net"
    if _has_symlinked_parent(merged_controlnet_path, work_dir):
        warnings.append(f"skipped symlinked merged controlnet path: {merged_controlnet_path}")
        merged_controlnet_exists = False
    else:
        merged_controlnet_exists = merged_controlnet_path.exists()

    return {
        "label": label,
        "pair_count": pair_count,
        "pairwise_controlnet_count": pairwise_controlnet_count,
        "merged_controlnet_exists": merged_controlnet_exists,
        "merged_controlnet_path": str(merged_controlnet_path) if merged_controlnet_exists else None,
        "pipeline_total_seconds": _pipeline_total_seconds(pipeline_timing, warnings, pipeline_timing_path),
        "total_final_control_point_count": (
            controlnet_summary.get("total_final_control_point_count") if controlnet_summary is not None else None
        ),
        "total_dom2ori_retained_count": (
            controlnet_summary.get("total_dom2ori_retained_count") if controlnet_summary is not None else None
        ),
        "warnings": warnings,
    }


def execute_method(
    *,
    label: str,
    command: list[str],
    method_dir: str | Path,
    resume_fingerprint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    method_dir = Path(method_dir).expanduser().resolve()
    method_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = method_dir / "stdout.log"
    stderr_log = method_dir / "stderr.log"
    metrics_path = method_dir / "metrics.json"

    _clear_collected_pipeline_outputs(method_dir)

    started_at_utc = _utc_now_iso()
    start_time = time.monotonic()
    return_code: int | None = None
    error: OSError | None = None
    with stdout_log.open("w", encoding="utf-8") as stdout_file, stderr_log.open("w", encoding="utf-8") as stderr_file:
        try:
            result = subprocess.run(
                command,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
                check=False,
            )
            return_code = result.returncode
        except OSError as launch_error:
            error = launch_error
            command_path = command[0] if command else "<empty command>"
            stderr_file.write(f"{command_path}: {type(launch_error).__name__}: {launch_error}\n")
    total_wall_seconds = time.monotonic() - start_time
    finished_at_utc = _utc_now_iso()

    execution_metrics = {
        "label": label,
        "status": "success" if return_code == 0 else "failed",
        "return_code": return_code,
        "started_at_utc": started_at_utc,
        "finished_at_utc": finished_at_utc,
        "total_wall_seconds": total_wall_seconds,
        "command": command,
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
    }
    if resume_fingerprint is not None:
        execution_metrics["resume_fingerprint"] = resume_fingerprint
    if error is not None:
        execution_metrics["error_type"] = type(error).__name__
        execution_metrics["error_message"] = str(error)
    metrics = collect_method_metrics(label, method_dir)
    metrics.update(execution_metrics)
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics


def _failed_metrics(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [metric for metric in metrics if metric.get("status") not in SUCCESS_STATUSES]


def _markdown_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_reports(reports_dir: str | Path, *, run_id: str, metrics: list[dict[str, Any]]) -> None:
    reports_dir = Path(reports_dir).expanduser()
    reports_dir.mkdir(parents=True, exist_ok=True)

    summary_payload = {
        "run_id": run_id,
        "metrics": metrics,
    }
    (reports_dir / "summary.json").write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")

    with (reports_dir / "summary.csv").open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=REPORT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(metrics)

    failures = _failed_metrics(metrics)
    lines = [
        f"# Matcher Comparison Summary: {run_id}",
        "",
        "| " + " | ".join(REPORT_COLUMNS) + " |",
        "| " + " | ".join("---" for _ in REPORT_COLUMNS) + " |",
    ]
    for metric in metrics:
        lines.append("| " + " | ".join(_markdown_cell(metric.get(column)) for column in REPORT_COLUMNS) + " |")
    lines.extend(["", "## Failures"])
    if failures:
        lines.extend(f"- {_markdown_cell(failure.get('label'))}: {_markdown_cell(failure.get('status'))}" for failure in failures)
    else:
        lines.append("None")
    (reports_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    failures_payload = {
        "run_id": run_id,
        "failures": failures,
    }
    (reports_dir / "failures.json").write_text(json.dumps(failures_payload, indent=2) + "\n", encoding="utf-8")


def _remove_report_outputs(reports_dir: str | Path) -> None:
    reports_dir = Path(reports_dir).expanduser()
    for report_name in REPORT_OUTPUT_NAMES:
        _unlink_known_output(reports_dir / report_name, reports_dir)


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


def _experiment_status(*, dry_run: bool, method_entries: list[dict[str, Any]]) -> str:
    if dry_run:
        return "dry_run"
    if any(method_entry.get("status") == "failed" for method_entry in method_entries):
        return "failed"
    return "success"


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

    run_dir = Path(output_root).expanduser() / config.run_id
    methods_dir = run_dir / "methods"
    reports_dir = run_dir / "reports"
    methods_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    if dry_run:
        _remove_report_outputs(reports_dir)

    shutil.copyfile(config.config_path, run_dir / "experiment_config.json")

    method_entries: list[dict[str, Any]] = []
    report_metrics: list[dict[str, Any]] = []
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
        resume_fingerprint = _resume_fingerprint(config, method)
        if not dry_run and effective_resume and _existing_success(metrics_path, command, resume_fingerprint):
            if not dry_run:
                report_metrics.append(_read_metrics_file(metrics_path))
            method_entries.append(
                _method_manifest_entry(
                    method,
                    method_dir,
                    command,
                    "skipped_success",
                )
            )
            continue

        if dry_run:
            warnings = _prepare_dry_run_workspace(
                method_dir,
                original_images_list=config.inputs.original_images_list,
                doms_list=config.inputs.doms_list,
            )
        else:
            prepare_method_workspace(
                method_dir,
                original_images_list=config.inputs.original_images_list,
                doms_list=config.inputs.doms_list,
            )
            warnings = []
        _write_command_script(method_dir / "command.sh", command)
        status = "dry_run"
        if not dry_run:
            metrics = execute_method(
                label=method.label,
                command=command,
                method_dir=method_dir,
                resume_fingerprint=resume_fingerprint,
            )
            report_metrics.append(metrics)
            status = metrics["status"]
        method_entries.append(
            _method_manifest_entry(
                method,
                method_dir,
                command,
                status,
                warnings,
            )
        )
        if not dry_run and status != "success" and not effective_keep_going:
            break
    status = _experiment_status(dry_run=dry_run, method_entries=method_entries)
    manifest_path = run_dir / "experiment_manifest.json"
    manifest = {
        "run_id": config.run_id,
        "status": status,
        "description": config.description,
        "created_at_utc": _utc_now_iso(),
        "dry_run": dry_run,
        "resume": effective_resume,
        "keep_going": effective_keep_going,
        "methods": method_entries,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if not dry_run and report_metrics:
        write_reports(reports_dir, run_id=config.run_id, metrics=report_metrics)

    return ExperimentRunResult(run_dir=run_dir, manifest_path=manifest_path, status=status)


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
    if result.status == "failed":
        return 1
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
