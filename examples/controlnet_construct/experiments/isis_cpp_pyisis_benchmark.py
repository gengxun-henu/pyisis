"""Config model for ISIS C++ vs PyISIS benchmark experiments."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import time
from typing import Any


SAFE_PATH_COMPONENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


@dataclass(frozen=True)
class CameraSample:
    index: int
    sample: float
    line: float


@dataclass(frozen=True)
class ExecutionConfig:
    cpp_benchmark_path: Path
    repeat_count: int = 1
    keep_intermediate_json: bool = True


@dataclass(frozen=True)
class CameraTaskConfig:
    label: str
    cube_path: Path
    sample_step: int = 10
    line_step: int = 10
    max_points: int | None = None
    top_error_count: int = 50


@dataclass(frozen=True)
class ControlNetTaskConfig:
    label: str
    net_path: Path


@dataclass(frozen=True)
class BenchmarkConfig:
    run_id: str
    description: str
    execution: ExecutionConfig
    camera_tasks: tuple[CameraTaskConfig, ...]
    controlnet_tasks: tuple[ControlNetTaskConfig, ...]
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
    return value


def _optional_bool(payload: dict[str, Any], key: str, default: bool) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _optional_positive_int(payload: dict[str, Any], key: str, default: int) -> int:
    value = payload.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    if value <= 0:
        raise ValueError(f"{key} must be positive")
    return value


def _optional_positive_int_or_none(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    if value <= 0:
        raise ValueError(f"{key} must be positive")
    return value


def _load_task_list(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f"{key} must be an array")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{key}[{index}] must be an object")
    return value


def _add_label(label: str, labels: set[str]) -> None:
    if label in labels:
        raise ValueError(f"Duplicate task label: {label}")
    labels.add(label)


def load_benchmark_config(config_path: str | Path, *, repo_root: str | Path | None = None) -> BenchmarkConfig:
    config_path = Path(config_path).expanduser().resolve()
    if repo_root is None:
        repo_root_path = Path(__file__).resolve().parents[3]
    else:
        repo_root_path = Path(repo_root).expanduser().resolve()

    with config_path.open(encoding="utf-8") as config_file:
        payload = json.load(config_file)

    if not isinstance(payload, dict):
        raise ValueError("Benchmark config must be a JSON object")

    execution_payload = _require_mapping(payload, "execution")
    execution = ExecutionConfig(
        cpp_benchmark_path=_resolve_path(
            _require_string(execution_payload, "cpp_benchmark_path"),
            config_path.parent,
            repo_root_path,
        ),
        repeat_count=_optional_positive_int(execution_payload, "repeat_count", 1),
        keep_intermediate_json=_optional_bool(execution_payload, "keep_intermediate_json", True),
    )

    labels: set[str] = set()
    camera_tasks: list[CameraTaskConfig] = []
    for task_payload in _load_task_list(payload, "camera_tasks"):
        label = _validate_path_component(_require_string(task_payload, "label"), "label")
        _add_label(label, labels)
        camera_tasks.append(
            CameraTaskConfig(
                label=label,
                cube_path=_resolve_path(
                    _require_string(task_payload, "cube_path"),
                    config_path.parent,
                    repo_root_path,
                ),
                sample_step=_optional_positive_int(task_payload, "sample_step", 10),
                line_step=_optional_positive_int(task_payload, "line_step", 10),
                max_points=_optional_positive_int_or_none(task_payload, "max_points"),
                top_error_count=_optional_positive_int(task_payload, "top_error_count", 50),
            )
        )

    controlnet_tasks: list[ControlNetTaskConfig] = []
    for task_payload in _load_task_list(payload, "controlnet_tasks"):
        label = _validate_path_component(_require_string(task_payload, "label"), "label")
        _add_label(label, labels)
        controlnet_tasks.append(
            ControlNetTaskConfig(
                label=label,
                net_path=_resolve_path(
                    _require_string(task_payload, "net_path"),
                    config_path.parent,
                    repo_root_path,
                ),
            )
        )

    if not camera_tasks and not controlnet_tasks:
        raise ValueError("At least one camera task or controlnet task is required")

    return BenchmarkConfig(
        run_id=_validate_path_component(_require_string(payload, "run_id"), "run_id"),
        description=_optional_string(payload, "description", ""),
        execution=execution,
        camera_tasks=tuple(camera_tasks),
        controlnet_tasks=tuple(controlnet_tasks),
        config_path=config_path,
    )


def _axis_positions(count: int, step: int, name: str) -> list[float]:
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError(f"{name}_count must be an integer")
    if count <= 0:
        raise ValueError(f"{name}_count must be positive")
    if not isinstance(step, int) or isinstance(step, bool):
        raise ValueError(f"{name}_step must be an integer")
    if step <= 0:
        raise ValueError(f"{name}_step must be positive")

    positions = [float(position) for position in range(1, count + 1, step)]
    edge = float(count)
    if positions[-1] != edge:
        positions.append(edge)
    return positions


def generate_camera_samples(
    *,
    sample_count: int,
    line_count: int,
    sample_step: int,
    line_step: int,
    max_points: int | None = None,
) -> tuple[CameraSample, ...]:
    if max_points is not None:
        if not isinstance(max_points, int) or isinstance(max_points, bool):
            raise ValueError("max_points must be an integer")
        if max_points <= 0:
            raise ValueError("max_points must be positive")

    samples: list[CameraSample] = []
    for line in _axis_positions(line_count, line_step, "line"):
        for sample in _axis_positions(sample_count, sample_step, "sample"):
            samples.append(CameraSample(len(samples), sample, line))
            if max_points is not None and len(samples) >= max_points:
                return tuple(samples)
    return tuple(samples)


def _import_isis_pybind():
    import isis_pybind as ip

    return ip


def _optional_call(obj: object, method_name: str, default=None):
    method = getattr(obj, method_name, None)
    if method is None:
        return default
    return method()


def run_pyisis_camera_task(task: CameraTaskConfig, *, ip_module=None) -> dict[str, Any]:
    ip = ip_module or _import_isis_pybind()
    cube = ip.Cube()
    failed_set_image_count = 0
    failed_set_universal_ground_count = 0
    successful_point_count = 0
    input_point_count = 0
    first_point_index: int | None = None
    point_records: list[dict[str, Any]] = []
    core_seconds = 0.0

    try:
        cube.open(str(task.cube_path), "r")
        camera = cube.camera()
        samples = generate_camera_samples(
            sample_count=int(camera.samples()),
            line_count=int(camera.lines()),
            sample_step=task.sample_step,
            line_step=task.line_step,
            max_points=task.max_points,
        )
        input_point_count = len(samples)
        if samples:
            first_point_index = samples[0].index

        for sample in samples:
            operation_start = time.perf_counter()
            if not camera.set_image(sample.sample, sample.line):
                core_seconds += time.perf_counter() - operation_start
                failed_set_image_count += 1
                continue

            latitude = camera.universal_latitude()
            longitude = camera.universal_longitude()
            if not camera.set_universal_ground(latitude, longitude):
                core_seconds += time.perf_counter() - operation_start
                failed_set_universal_ground_count += 1
                continue

            roundtrip_sample = camera.sample()
            roundtrip_line = camera.line()
            core_seconds += time.perf_counter() - operation_start
            point_records.append(
                {
                    "index": sample.index,
                    "input_sample": sample.sample,
                    "input_line": sample.line,
                    "latitude": latitude,
                    "longitude": longitude,
                    "roundtrip_sample": roundtrip_sample,
                    "roundtrip_line": roundtrip_line,
                }
            )
            successful_point_count += 1
    finally:
        cube.close()

    return {
        "task_type": "camera",
        "implementation": "pyisis",
        "label": task.label,
        "cube_path": str(task.cube_path),
        "input_point_count": input_point_count,
        "successful_point_count": successful_point_count,
        "failed_set_image_count": failed_set_image_count,
        "failed_set_universal_ground_count": failed_set_universal_ground_count,
        "first_point_index": first_point_index,
        "points": point_records,
        "core_seconds": core_seconds,
        "average_successful_point_seconds": core_seconds / len(point_records) if point_records else None,
    }


def run_pyisis_controlnet_task(task: ControlNetTaskConfig, *, ip_module=None) -> dict[str, Any]:
    ip = ip_module or _import_isis_pybind()

    load_start = time.perf_counter()
    control_net = ip.ControlNet(str(task.net_path))
    load_seconds = time.perf_counter() - load_start

    traverse_start = time.perf_counter()
    point_count = int(control_net.get_num_points())
    measure_count = 0
    serial_measure_counts: Counter[str] = Counter()

    for point_index in range(point_count):
        point = control_net.get_point(point_index)
        _optional_call(point, "get_id")
        _optional_call(point, "get_type")
        _optional_call(point, "is_ignored", False)
        _optional_call(point, "is_edit_locked", False)

        point_measure_count = int(point.get_num_measures())
        for measure_index in range(point_measure_count):
            measure = point.get_measure(measure_index)
            measure_count += 1

            serial = _optional_call(measure, "get_cube_serial_number", "")
            _optional_call(measure, "get_sample")
            _optional_call(measure, "get_line")
            _optional_call(measure, "get_type")
            _optional_call(measure, "is_ignored", False)
            _optional_call(measure, "is_edit_locked", False)

            if serial:
                serial_measure_counts[str(serial)] += 1

    traverse_seconds = time.perf_counter() - traverse_start
    valid_point_count = _optional_call(control_net, "get_num_valid_points")
    valid_measure_count = _optional_call(control_net, "get_num_valid_measures")

    return {
        "task_type": "controlnet",
        "implementation": "pyisis",
        "label": task.label,
        "net_path": str(task.net_path),
        "point_count": point_count,
        "measure_count": measure_count,
        "valid_point_count": int(valid_point_count) if valid_point_count is not None else None,
        "valid_measure_count": int(valid_measure_count) if valid_measure_count is not None else None,
        "serial_measure_counts": dict(serial_measure_counts),
        "load_seconds": load_seconds,
        "traverse_seconds": traverse_seconds,
        "core_seconds": load_seconds + traverse_seconds,
    }


def build_cpp_camera_command(
    cpp_path: str | Path,
    task: CameraTaskConfig,
    output_path: str | Path,
) -> list[str]:
    command = [
        str(cpp_path),
        "camera",
        "--label",
        task.label,
        "--cube",
        str(task.cube_path),
        "--sample-step",
        str(task.sample_step),
        "--line-step",
        str(task.line_step),
        "--output",
        str(output_path),
    ]
    if task.max_points is not None:
        command.extend(["--max-points", str(task.max_points)])
    return command


def build_cpp_controlnet_command(
    cpp_path: str | Path,
    task: ControlNetTaskConfig,
    output_path: str | Path,
) -> list[str]:
    return [
        str(cpp_path),
        "controlnet",
        "--label",
        task.label,
        "--net",
        str(task.net_path),
        "--output",
        str(output_path),
    ]


def run_cpp_command(
    command: list[str],
    *,
    keep_going: bool,
    task_type: str = "",
    label: str = "",
) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
    except OSError as error:
        wall_seconds = time.perf_counter() - start
        result = {
            "status": "failed",
            "return_code": None,
            "stdout": "",
            "stderr": str(error),
            "command": command,
            "wall_seconds": wall_seconds,
            "implementation": "cpp",
            "label": label,
            "task_type": task_type,
        }
        if not keep_going:
            raise RuntimeError(f"Failed to launch C++ benchmark command: {error}") from error
        return result

    wall_seconds = time.perf_counter() - start
    result = {
        "status": "success" if completed.returncode == 0 else "failed",
        "return_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "command": command,
        "wall_seconds": wall_seconds,
        "implementation": "cpp",
        "label": label,
        "task_type": task_type,
    }
    if completed.returncode != 0 and not keep_going:
        raise subprocess.CalledProcessError(
            completed.returncode,
            command,
            output=completed.stdout,
            stderr=completed.stderr,
        )
    return result


def load_cpp_result(path: str | Path) -> dict[str, Any]:
    path = Path(path).expanduser().resolve()
    with path.open(encoding="utf-8") as result_file:
        payload = json.load(result_file)
    if not isinstance(payload, dict) or payload.get("implementation") != "cpp":
        raise ValueError("Expected cpp result")
    return payload


def compare_camera_results(
    label: str,
    pyisis_result: dict[str, Any],
    cpp_result: dict[str, Any],
    *,
    top_error_count: int,
) -> dict[str, Any]:
    py_points = {int(point["index"]): point for point in pyisis_result.get("points", [])}
    cpp_points = {int(point["index"]): point for point in cpp_result.get("points", [])}
    matched_indices = sorted(set(py_points) & set(cpp_points))
    missing_in_pyisis = sorted(set(cpp_points) - set(py_points))
    missing_in_cpp = sorted(set(py_points) - set(cpp_points))

    error_rows: list[dict[str, Any]] = []
    for index in matched_indices:
        py_point = py_points[index]
        cpp_point = cpp_points[index]
        row = {
            "label": label,
            "index": index,
            "latitude_abs": abs(float(py_point["latitude"]) - float(cpp_point["latitude"])),
            "longitude_abs": abs(float(py_point["longitude"]) - float(cpp_point["longitude"])),
            "sample_abs": abs(float(py_point["roundtrip_sample"]) - float(cpp_point["roundtrip_sample"])),
            "line_abs": abs(float(py_point["roundtrip_line"]) - float(cpp_point["roundtrip_line"])),
        }
        row["combined_error"] = (
            row["latitude_abs"]
            + row["longitude_abs"]
            + row["sample_abs"]
            + row["line_abs"]
        )
        error_rows.append(row)

    return {
        "label": label,
        "matched_point_count": len(matched_indices),
        "missing_in_pyisis": missing_in_pyisis,
        "missing_in_cpp": missing_in_cpp,
        "stats": _camera_error_stats(error_rows),
        "top_errors": sorted(error_rows, key=lambda row: row["combined_error"], reverse=True)[:top_error_count],
    }


def _camera_error_stats(rows: list[dict[str, Any]]) -> dict[str, float | None]:
    stats: dict[str, float | None] = {}
    for key in ("latitude_abs", "longitude_abs", "sample_abs", "line_abs"):
        values = [float(row[key]) for row in rows]
        if values:
            stats[f"{key}_max"] = max(values)
            stats[f"{key}_mean"] = sum(values) / len(values)
            stats[f"{key}_rms"] = math.sqrt(sum(value * value for value in values) / len(values))
        else:
            stats[f"{key}_max"] = None
            stats[f"{key}_mean"] = None
            stats[f"{key}_rms"] = None
    return stats


def _remove_benchmark_owned_path(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def prepare_run_directory(config: BenchmarkConfig, *, output_root: str | Path, dry_run: bool) -> Path:
    output_root = Path(output_root).expanduser().resolve()
    run_dir = output_root / config.run_id
    if run_dir.is_symlink():
        run_dir.unlink()
    run_dir.mkdir(parents=True, exist_ok=True)
    for child_name in ("pyisis", "cpp", "reports"):
        _remove_benchmark_owned_path(run_dir / child_name)
    for file_name in ("experiment_config.json", "experiment_manifest.json"):
        _remove_benchmark_owned_path(run_dir / file_name)
    for child_name in ("pyisis", "cpp", "reports"):
        (run_dir / child_name).mkdir(exist_ok=True)

    shutil.copyfile(config.config_path, run_dir / "experiment_config.json")
    manifest = {
        "run_id": config.run_id,
        "description": config.description,
        "dry_run": dry_run,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tasks": [task.label for task in config.camera_tasks] + [task.label for task in config.controlnet_tasks],
        "cpp_benchmark_path": str(config.execution.cpp_benchmark_path),
    }
    (run_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return run_dir


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _task_labels(config: BenchmarkConfig) -> set[str]:
    return {task.label for task in config.camera_tasks} | {task.label for task in config.controlnet_tasks}


def _selected_labels(config: BenchmarkConfig, only: set[str] | None) -> set[str] | None:
    if only is None:
        return None
    unknown_labels = sorted(only - _task_labels(config))
    if unknown_labels:
        raise ValueError(f"Unknown task label(s): {', '.join(unknown_labels)}")
    return only


def _is_selected(task_label: str, selected_labels: set[str] | None) -> bool:
    return selected_labels is None or task_label in selected_labels


def _write_command(path: str | Path, command: list[str]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"{shlex.join(command)}\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _write_dry_run_commands(
    config: BenchmarkConfig,
    run_dir: str | Path,
    *,
    only: set[str] | None,
) -> None:
    run_dir = Path(run_dir)
    selected_labels = _selected_labels(config, only)
    for task in config.camera_tasks:
        if not _is_selected(task.label, selected_labels):
            continue
        command = build_cpp_camera_command(
            config.execution.cpp_benchmark_path,
            task,
            run_dir / "cpp" / f"{task.label}.json",
        )
        _write_command(run_dir / "cpp" / task.label / "command.sh", command)

    for task in config.controlnet_tasks:
        if not _is_selected(task.label, selected_labels):
            continue
        command = build_cpp_controlnet_command(
            config.execution.cpp_benchmark_path,
            task,
            run_dir / "cpp" / f"{task.label}.json",
        )
        _write_command(run_dir / "cpp" / task.label / "command.sh", command)


def _record_pyisis_result(path: Path, task_runner, task) -> dict[str, Any]:
    start = time.perf_counter()
    result = task_runner(task)
    result = dict(result)
    result["status"] = "success"
    result.setdefault("wall_seconds", time.perf_counter() - start)
    _write_json(path, result)
    return result


def _record_cpp_result(
    path: Path,
    command: list[str],
    *,
    task_type: str,
    label: str,
    keep_going: bool,
) -> dict[str, Any]:
    execution_result = run_cpp_command(command, keep_going=keep_going, task_type=task_type, label=label)
    if execution_result["status"] != "success":
        failure_result = {
            "task_type": task_type,
            "implementation": "cpp",
            "label": label,
            **execution_result,
        }
        _write_json(path, failure_result)
        return failure_result

    cpp_result = load_cpp_result(path)
    cpp_result = dict(cpp_result)
    cpp_result["status"] = "success"
    cpp_result["return_code"] = execution_result["return_code"]
    cpp_result["stdout"] = execution_result["stdout"]
    cpp_result["stderr"] = execution_result["stderr"]
    cpp_result["command"] = execution_result["command"]
    cpp_result["wall_seconds"] = execution_result["wall_seconds"]
    return cpp_result


def run_benchmark(
    config: BenchmarkConfig,
    *,
    output_root: str | Path,
    dry_run: bool,
    only: set[str] | None,
    keep_going: bool,
) -> Path:
    selected_labels = _selected_labels(config, only)
    run_dir = prepare_run_directory(config, output_root=output_root, dry_run=dry_run)
    if dry_run:
        _write_dry_run_commands(config, run_dir, only=selected_labels)
        return run_dir

    results: list[dict[str, Any]] = []
    camera_comparisons: list[dict[str, Any]] = []

    for task in config.camera_tasks:
        if not _is_selected(task.label, selected_labels):
            continue

        pyisis_result = _record_pyisis_result(
            run_dir / "pyisis" / f"{task.label}.json",
            run_pyisis_camera_task,
            task,
        )
        results.append(pyisis_result)

        cpp_output_path = run_dir / "cpp" / f"{task.label}.json"
        cpp_command = build_cpp_camera_command(config.execution.cpp_benchmark_path, task, cpp_output_path)
        _write_command(run_dir / "cpp" / task.label / "command.sh", cpp_command)
        cpp_result = _record_cpp_result(
            cpp_output_path,
            cpp_command,
            task_type="camera",
            label=task.label,
            keep_going=keep_going,
        )
        results.append(cpp_result)
        if cpp_result.get("status") == "success":
            camera_comparisons.append(
                compare_camera_results(
                    task.label,
                    pyisis_result,
                    cpp_result,
                    top_error_count=task.top_error_count,
                )
            )

    for task in config.controlnet_tasks:
        if not _is_selected(task.label, selected_labels):
            continue

        pyisis_result = _record_pyisis_result(
            run_dir / "pyisis" / f"{task.label}.json",
            run_pyisis_controlnet_task,
            task,
        )
        results.append(pyisis_result)

        cpp_output_path = run_dir / "cpp" / f"{task.label}.json"
        cpp_command = build_cpp_controlnet_command(config.execution.cpp_benchmark_path, task, cpp_output_path)
        _write_command(run_dir / "cpp" / task.label / "command.sh", cpp_command)
        cpp_result = _record_cpp_result(
            cpp_output_path,
            cpp_command,
            task_type="controlnet",
            label=task.label,
            keep_going=keep_going,
        )
        results.append(cpp_result)

    write_summary_reports(run_dir, results, camera_comparisons)
    return run_dir


def write_summary_reports(
    run_dir: str | Path,
    results: list[dict[str, Any]],
    camera_comparisons: list[dict[str, Any]],
) -> None:
    reports_dir = Path(run_dir) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "results": results,
        "camera_comparisons": camera_comparisons,
    }
    (reports_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_summary_csv(reports_dir / "summary.csv", results, camera_comparisons)
    _write_camera_top_errors(reports_dir / "camera_top_errors.csv", camera_comparisons)

    controlnet_results = [result for result in results if result.get("task_type") == "controlnet"]
    (reports_dir / "controlnet_summary.json").write_text(
        json.dumps({"results": controlnet_results}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_summary_csv(
    path: Path,
    results: list[dict[str, Any]],
    camera_comparisons: list[dict[str, Any]],
) -> None:
    columns = [
        "label",
        "task_type",
        "implementation",
        "status",
        "core_seconds",
        "wall_seconds",
        "point_count",
        "measure_count",
        "successful_point_count",
        "matched_point_count",
        "missing_in_pyisis_count",
        "missing_in_cpp_count",
        "latitude_abs_max",
        "longitude_abs_max",
        "sample_abs_max",
        "line_abs_max",
    ]
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        for result in results:
            writer.writerow({column: result.get(column) for column in columns})
        for comparison in camera_comparisons:
            stats = comparison.get("stats", {})
            writer.writerow(
                {
                    "label": comparison.get("label"),
                    "task_type": "camera_comparison",
                    "implementation": "comparison",
                    "matched_point_count": comparison.get("matched_point_count"),
                    "missing_in_pyisis_count": len(comparison.get("missing_in_pyisis", [])),
                    "missing_in_cpp_count": len(comparison.get("missing_in_cpp", [])),
                    "latitude_abs_max": stats.get("latitude_abs_max"),
                    "longitude_abs_max": stats.get("longitude_abs_max"),
                    "sample_abs_max": stats.get("sample_abs_max"),
                    "line_abs_max": stats.get("line_abs_max"),
                }
            )


def _write_camera_top_errors(path: Path, camera_comparisons: list[dict[str, Any]]) -> None:
    columns = [
        "label",
        "index",
        "combined_error",
        "latitude_abs",
        "longitude_abs",
        "sample_abs",
        "line_abs",
    ]
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        for comparison in camera_comparisons:
            for row in comparison.get("top_errors", []):
                writer.writerow({column: row.get(column) for column in columns})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run ISIS C++ vs PyISIS benchmark experiments.")
    parser.add_argument("config", help="Path to benchmark JSON config")
    parser.add_argument(
        "--output-root",
        default="work/isis_cpp_pyisis_benchmark",
        help="Directory under which the benchmark run directory is created",
    )
    parser.add_argument("--dry-run", action="store_true", help="Write C++ command scripts without executing tasks")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Task label to run. Repeat or pass comma-separated labels.",
    )
    failure_group = parser.add_mutually_exclusive_group()
    failure_group.add_argument(
        "--keep-going",
        action="store_true",
        help="Record C++ command failures and continue writing reports",
    )
    failure_group.add_argument(
        "--fail-fast",
        action="store_false",
        dest="keep_going",
        help="Raise on the first C++ command failure",
    )
    parser.set_defaults(keep_going=False)
    parser.add_argument(
        "--cpp-benchmark-path",
        help="Override execution.cpp_benchmark_path from the config",
    )
    args = parser.parse_args(argv)

    config = load_benchmark_config(args.config)
    if args.cpp_benchmark_path:
        config = replace(
            config,
            execution=replace(
                config.execution,
                cpp_benchmark_path=Path(args.cpp_benchmark_path).expanduser().resolve(),
            ),
        )

    only = _parse_only_labels(args.only)
    run_dir = run_benchmark(
        config,
        output_root=args.output_root,
        dry_run=args.dry_run,
        only=only,
        keep_going=args.keep_going,
    )
    print(run_dir)
    return 0


def _parse_only_labels(values: list[str]) -> set[str] | None:
    labels: set[str] = set()
    for value in values:
        for label in value.split(","):
            stripped = label.strip()
            if stripped:
                labels.add(stripped)
    return labels or None


if __name__ == "__main__":
    raise SystemExit(main())
