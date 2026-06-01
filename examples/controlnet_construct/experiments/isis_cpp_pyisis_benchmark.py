"""Config model for ISIS C++ vs PyISIS benchmark experiments."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
import math
import os
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
class DomOriTaskConfig:
    label: str
    dom_path: Path
    original_path: Path
    point_count: int = 1_000_000
    top_error_count: int = 50
    keep_point_records: bool = False
    sampling_mode: str = "ori_roundtrip"


@dataclass(frozen=True)
class SolarGeometryTaskConfig:
    label: str
    cube_path: Path
    point_count: int = 1_000_000
    top_error_count: int = 50
    keep_point_records: bool = False


@dataclass(frozen=True)
class BenchmarkConfig:
    run_id: str
    description: str
    execution: ExecutionConfig
    camera_tasks: tuple[CameraTaskConfig, ...]
    controlnet_tasks: tuple[ControlNetTaskConfig, ...]
    dom_ori_tasks: tuple[DomOriTaskConfig, ...]
    solar_geometry_tasks: tuple[SolarGeometryTaskConfig, ...]
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


def _optional_sampling_mode(payload: dict[str, Any], key: str, default: str) -> str:
    value = payload.get(key, default)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    if value not in {"ori_roundtrip", "direct_dom"}:
        raise ValueError(f"{key} must be ori_roundtrip or direct_dom")
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
    repeat_count = _optional_positive_int(execution_payload, "repeat_count", 1)
    if repeat_count != 1:
        raise ValueError("repeat_count values other than 1 are not supported until repeat execution is implemented")
    keep_intermediate_json = _optional_bool(execution_payload, "keep_intermediate_json", True)
    if not keep_intermediate_json:
        raise ValueError("keep_intermediate_json=false is not supported until cleanup support is implemented")

    execution = ExecutionConfig(
        cpp_benchmark_path=_resolve_path(
            _require_string(execution_payload, "cpp_benchmark_path"),
            config_path.parent,
            repo_root_path,
        ),
        repeat_count=repeat_count,
        keep_intermediate_json=keep_intermediate_json,
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

    dom_ori_tasks: list[DomOriTaskConfig] = []
    for task_payload in _load_task_list(payload, "dom_ori_tasks"):
        label = _validate_path_component(_require_string(task_payload, "label"), "label")
        _add_label(label, labels)
        dom_ori_tasks.append(
            DomOriTaskConfig(
                label=label,
                dom_path=_resolve_path(
                    _require_string(task_payload, "dom_path"),
                    config_path.parent,
                    repo_root_path,
                ),
                original_path=_resolve_path(
                    _require_string(task_payload, "original_path"),
                    config_path.parent,
                    repo_root_path,
                ),
                point_count=_optional_positive_int(task_payload, "point_count", 1_000_000),
                top_error_count=_optional_positive_int(task_payload, "top_error_count", 50),
                keep_point_records=_optional_bool(task_payload, "keep_point_records", False),
                sampling_mode=_optional_sampling_mode(task_payload, "sampling_mode", "ori_roundtrip"),
            )
        )

    solar_geometry_tasks: list[SolarGeometryTaskConfig] = []
    for task_payload in _load_task_list(payload, "solar_geometry_tasks"):
        label = _validate_path_component(_require_string(task_payload, "label"), "label")
        _add_label(label, labels)
        solar_geometry_tasks.append(
            SolarGeometryTaskConfig(
                label=label,
                cube_path=_resolve_path(
                    _require_string(task_payload, "cube_path"),
                    config_path.parent,
                    repo_root_path,
                ),
                point_count=_optional_positive_int(task_payload, "point_count", 1_000_000),
                top_error_count=_optional_positive_int(task_payload, "top_error_count", 50),
                keep_point_records=_optional_bool(task_payload, "keep_point_records", False),
            )
        )

    if not camera_tasks and not controlnet_tasks and not dom_ori_tasks and not solar_geometry_tasks:
        raise ValueError(
            "At least one camera task or controlnet task is required, "
            "or provide a dom/ori task or solar geometry task"
        )

    return BenchmarkConfig(
        run_id=_validate_path_component(_require_string(payload, "run_id"), "run_id"),
        description=_optional_string(payload, "description", ""),
        execution=execution,
        camera_tasks=tuple(camera_tasks),
        controlnet_tasks=tuple(controlnet_tasks),
        dom_ori_tasks=tuple(dom_ori_tasks),
        solar_geometry_tasks=tuple(solar_geometry_tasks),
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


def _linspace_axis(count: int, steps: int, name: str) -> list[float]:
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError(f"{name}_count must be an integer")
    if count <= 0:
        raise ValueError(f"{name}_count must be positive")
    if steps <= 0:
        raise ValueError(f"{name}_steps must be positive")
    if steps == 1:
        return [(float(count) + 1.0) / 2.0]
    return [1.0 + (float(count) - 1.0) * index / float(steps - 1) for index in range(steps)]


def generate_regular_grid_samples(
    *,
    sample_count: int,
    line_count: int,
    point_count: int,
) -> tuple[CameraSample, ...]:
    if not isinstance(point_count, int) or isinstance(point_count, bool):
        raise ValueError("point_count must be an integer")
    if point_count <= 0:
        raise ValueError("point_count must be positive")

    columns = max(1, int(math.ceil(math.sqrt(point_count))))
    rows = max(1, int(math.ceil(point_count / columns)))
    sample_positions = _linspace_axis(sample_count, columns, "sample")
    line_positions = _linspace_axis(line_count, rows, "line")

    samples: list[CameraSample] = []
    for line in line_positions:
        for sample in sample_positions:
            samples.append(CameraSample(len(samples), sample, line))
            if len(samples) >= point_count:
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


def _zero_stats(prefixes: tuple[str, ...]) -> dict[str, float]:
    stats: dict[str, float] = {}
    for prefix in prefixes:
        stats[f"{prefix}_abs_max"] = 0.0
        stats[f"{prefix}_abs_mean"] = 0.0
        stats[f"{prefix}_abs_rms"] = 0.0
    return stats


@dataclass
class _RunningAbsStats:
    count: int = 0
    total: float = 0.0
    total_sq: float = 0.0
    max_value: float = 0.0

    def add(self, value: float) -> None:
        abs_value = abs(float(value))
        self.count += 1
        self.total += abs_value
        self.total_sq += abs_value * abs_value
        self.max_value = max(self.max_value, abs_value)

    def as_fields(self, prefix: str) -> dict[str, float]:
        if self.count == 0:
            return {
                f"{prefix}_abs_max": 0.0,
                f"{prefix}_abs_mean": 0.0,
                f"{prefix}_abs_rms": 0.0,
            }
        return {
            f"{prefix}_abs_max": self.max_value,
            f"{prefix}_abs_mean": self.total / self.count,
            f"{prefix}_abs_rms": math.sqrt(self.total_sq / self.count),
        }


def _points_per_second(successful_point_count: int, core_seconds: float) -> float | None:
    if successful_point_count <= 0 or core_seconds <= 0.0:
        return None
    return successful_point_count / core_seconds


def _push_top_error(top_errors: list[dict[str, Any]], row: dict[str, Any], limit: int) -> None:
    if limit <= 0:
        return
    top_errors.append(row)
    top_errors.sort(key=lambda item: float(item["pixel_error"]), reverse=True)
    del top_errors[limit:]


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
        "file_size_bytes": task.net_path.stat().st_size if task.net_path.exists() else None,
        "point_count": point_count,
        "measure_count": measure_count,
        "valid_point_count": int(valid_point_count) if valid_point_count is not None else None,
        "valid_measure_count": int(valid_measure_count) if valid_measure_count is not None else None,
        "serial_measure_counts": dict(serial_measure_counts),
        "load_seconds": load_seconds,
        "traverse_seconds": traverse_seconds,
        "core_seconds": load_seconds + traverse_seconds,
        "measures_per_second": measure_count / traverse_seconds if traverse_seconds > 0.0 else None,
    }


def _run_pyisis_dom_ori_direct_task(task: DomOriTaskConfig, *, ip_module=None) -> dict[str, Any]:
    ip = ip_module or _import_isis_pybind()
    dom_cube = ip.Cube()
    original_cube = ip.Cube()
    failed_dom_lookup_count = 0
    failed_original_projection_count = 0
    point_records: list[dict[str, Any]] = []
    core_seconds = 0.0

    try:
        dom_cube.open(str(task.dom_path), "r")
        original_cube.open(str(task.original_path), "r")
        dom_ground_map = ip.UniversalGroundMap(
            dom_cube,
            ip.UniversalGroundMap.CameraPriority.ProjectionFirst,
        )
        original_ground_map = ip.UniversalGroundMap(
            original_cube,
            ip.UniversalGroundMap.CameraPriority.CameraFirst,
        )
        samples = generate_regular_grid_samples(
            sample_count=int(dom_cube.sample_count()),
            line_count=int(dom_cube.line_count()),
            point_count=task.point_count,
        )

        for sample in samples:
            operation_start = time.perf_counter()
            if not dom_ground_map.set_image(sample.sample, sample.line):
                core_seconds += time.perf_counter() - operation_start
                failed_dom_lookup_count += 1
                continue

            latitude = dom_ground_map.universal_latitude()
            longitude = dom_ground_map.universal_longitude()
            if not original_ground_map.set_universal_ground(latitude, longitude):
                core_seconds += time.perf_counter() - operation_start
                failed_original_projection_count += 1
                continue

            output_sample = original_ground_map.sample()
            output_line = original_ground_map.line()
            core_seconds += time.perf_counter() - operation_start
            if task.keep_point_records:
                point_records.append(
                    {
                        "index": sample.index,
                        "input_sample": sample.sample,
                        "input_line": sample.line,
                        "latitude": latitude,
                        "longitude": longitude,
                        "output_sample": output_sample,
                        "output_line": output_line,
                    }
                )
    finally:
        original_cube.close()
        dom_cube.close()

    failed_count = failed_dom_lookup_count + failed_original_projection_count
    successful_point_count = task.point_count - failed_count
    result: dict[str, Any] = {
        "task_type": "dom_ori",
        "implementation": "pyisis",
        "label": task.label,
        "sampling_mode": "direct_dom",
        "dom_path": str(task.dom_path),
        "original_path": str(task.original_path),
        "input_point_count": task.point_count,
        "successful_point_count": successful_point_count,
        "failed_count": failed_count,
        "failed_dom_lookup_count": failed_dom_lookup_count,
        "failed_original_projection_count": failed_original_projection_count,
        "core_seconds": core_seconds,
        "points_per_second": _points_per_second(successful_point_count, core_seconds),
        "top_errors": [],
        **_zero_stats(("sample", "line")),
    }
    if task.keep_point_records:
        result["points"] = point_records
    return result


def run_pyisis_dom_ori_task(task: DomOriTaskConfig, *, ip_module=None) -> dict[str, Any]:
    if task.sampling_mode == "direct_dom":
        return _run_pyisis_dom_ori_direct_task(task, ip_module=ip_module)

    ip = ip_module or _import_isis_pybind()
    dom_cube = ip.Cube()
    original_cube = ip.Cube()
    failed_ori_set_image_count = 0
    failed_ori_ground_not_finite_count = 0
    failed_ori_to_dom_projection_count = 0
    failed_dom_point_out_of_bounds_count = 0
    failed_dom_lookup_count = 0
    failed_dom_to_ori_projection_count = 0
    ori_to_dom_successful_count = 0
    dom_ori_successful_count = 0
    point_records: list[dict[str, Any]] = []
    top_errors: list[dict[str, Any]] = []
    sample_stats = _RunningAbsStats()
    line_stats = _RunningAbsStats()
    pixel_error_stats = _RunningAbsStats()
    ori_to_dom_seconds = 0.0
    dom_to_ori_seconds = 0.0

    try:
        dom_cube.open(str(task.dom_path), "r")
        original_cube.open(str(task.original_path), "r")
        original_camera = original_cube.camera()
        dom_ground_map = ip.UniversalGroundMap(
            dom_cube,
            ip.UniversalGroundMap.CameraPriority.ProjectionFirst,
        )
        original_ground_map = ip.UniversalGroundMap(
            original_cube,
            ip.UniversalGroundMap.CameraPriority.CameraFirst,
        )
        samples = generate_regular_grid_samples(
            sample_count=int(original_cube.sample_count()),
            line_count=int(original_cube.line_count()),
            point_count=task.point_count,
        )
        dom_sample_count = int(dom_cube.sample_count())
        dom_line_count = int(dom_cube.line_count())

        for sample in samples:
            stage_start = time.perf_counter()
            if not original_camera.set_image(sample.sample, sample.line):
                ori_to_dom_seconds += time.perf_counter() - stage_start
                failed_ori_set_image_count += 1
                continue

            latitude = original_camera.universal_latitude()
            longitude = original_camera.universal_longitude()
            if not math.isfinite(latitude) or not math.isfinite(longitude):
                ori_to_dom_seconds += time.perf_counter() - stage_start
                failed_ori_ground_not_finite_count += 1
                continue

            if not dom_ground_map.set_universal_ground(latitude, longitude):
                ori_to_dom_seconds += time.perf_counter() - stage_start
                failed_ori_to_dom_projection_count += 1
                continue

            dom_sample = dom_ground_map.sample()
            dom_line = dom_ground_map.line()
            if not (1.0 <= dom_sample <= float(dom_sample_count) and 1.0 <= dom_line <= float(dom_line_count)):
                ori_to_dom_seconds += time.perf_counter() - stage_start
                failed_dom_point_out_of_bounds_count += 1
                continue

            ori_to_dom_seconds += time.perf_counter() - stage_start
            ori_to_dom_successful_count += 1

            stage_start = time.perf_counter()
            if not dom_ground_map.set_image(dom_sample, dom_line):
                dom_to_ori_seconds += time.perf_counter() - stage_start
                failed_dom_lookup_count += 1
                continue

            dom_latitude = dom_ground_map.universal_latitude()
            dom_longitude = dom_ground_map.universal_longitude()
            if not original_ground_map.set_universal_ground(dom_latitude, dom_longitude):
                dom_to_ori_seconds += time.perf_counter() - stage_start
                failed_dom_to_ori_projection_count += 1
                continue

            output_sample = original_ground_map.sample()
            output_line = original_ground_map.line()
            dom_to_ori_seconds += time.perf_counter() - stage_start
            dom_ori_successful_count += 1

            sample_error = output_sample - sample.sample
            line_error = output_line - sample.line
            pixel_error = math.hypot(sample_error, line_error)
            sample_stats.add(sample_error)
            line_stats.add(line_error)
            pixel_error_stats.add(pixel_error)
            error_row = {
                "index": sample.index,
                "input_sample": sample.sample,
                "input_line": sample.line,
                "dom_sample": dom_sample,
                "dom_line": dom_line,
                "output_sample": output_sample,
                "output_line": output_line,
                "sample_abs": abs(sample_error),
                "line_abs": abs(line_error),
                "pixel_error": pixel_error,
            }
            _push_top_error(top_errors, error_row, task.top_error_count)
            if task.keep_point_records:
                point_records.append(error_row)
    finally:
        original_cube.close()
        dom_cube.close()

    ori_to_dom_failed_count = (
        failed_ori_set_image_count
        + failed_ori_ground_not_finite_count
        + failed_ori_to_dom_projection_count
        + failed_dom_point_out_of_bounds_count
    )
    dom_ori_failed_count = failed_dom_lookup_count + failed_dom_to_ori_projection_count
    failed_count = ori_to_dom_failed_count + dom_ori_failed_count
    core_seconds = ori_to_dom_seconds + dom_to_ori_seconds
    result = {
        "task_type": "dom_ori",
        "implementation": "pyisis",
        "label": task.label,
        "sampling_mode": "ori_roundtrip",
        "dom_path": str(task.dom_path),
        "original_path": str(task.original_path),
        "input_point_count": task.point_count,
        "ori_seed_point_count": task.point_count,
        "successful_point_count": dom_ori_successful_count,
        "roundtrip_successful_count": dom_ori_successful_count,
        "roundtrip_success_rate": dom_ori_successful_count / task.point_count if task.point_count else None,
        "failed_count": failed_count,
        "ori_to_dom_successful_count": ori_to_dom_successful_count,
        "ori_to_dom_failed_count": ori_to_dom_failed_count,
        "dom_ori_successful_count": dom_ori_successful_count,
        "dom_ori_failed_count": dom_ori_failed_count,
        "failed_ori_set_image_count": failed_ori_set_image_count,
        "failed_ori_ground_not_finite_count": failed_ori_ground_not_finite_count,
        "failed_ori_to_dom_projection_count": failed_ori_to_dom_projection_count,
        "failed_dom_point_out_of_bounds_count": failed_dom_point_out_of_bounds_count,
        "failed_dom_lookup_count": failed_dom_lookup_count,
        "failed_dom_to_ori_projection_count": failed_dom_to_ori_projection_count,
        "ori_to_dom_seconds": ori_to_dom_seconds,
        "dom_to_ori_seconds": dom_to_ori_seconds,
        "core_seconds": core_seconds,
        "points_per_second": _points_per_second(dom_ori_successful_count, core_seconds),
        "roundtrip_points_per_second": _points_per_second(dom_ori_successful_count, core_seconds),
        "top_errors": top_errors,
        **sample_stats.as_fields("sample"),
        **line_stats.as_fields("line"),
        **pixel_error_stats.as_fields("pixel_error"),
    }
    if task.keep_point_records:
        result["points"] = point_records
    return result


def run_pyisis_solar_geometry_task(task: SolarGeometryTaskConfig, *, ip_module=None) -> dict[str, Any]:
    ip = ip_module or _import_isis_pybind()
    cube = ip.Cube()
    failed_set_image_count = 0
    point_records: list[dict[str, Any]] = []
    core_seconds = 0.0

    try:
        cube.open(str(task.cube_path), "r")
        camera = cube.camera()
        samples = generate_regular_grid_samples(
            sample_count=int(cube.sample_count()),
            line_count=int(cube.line_count()),
            point_count=task.point_count,
        )
        for sample in samples:
            operation_start = time.perf_counter()
            if not camera.set_image(sample.sample, sample.line):
                core_seconds += time.perf_counter() - operation_start
                failed_set_image_count += 1
                continue
            azimuth = camera.sun_azimuth()
            elevation = 90.0 - camera.incidence_angle()
            core_seconds += time.perf_counter() - operation_start
            if task.keep_point_records:
                point_records.append(
                    {
                        "index": sample.index,
                        "input_sample": sample.sample,
                        "input_line": sample.line,
                        "sun_azimuth": azimuth,
                        "solar_elevation": elevation,
                    }
                )
    finally:
        cube.close()

    successful_point_count = task.point_count - failed_set_image_count
    result: dict[str, Any] = {
        "task_type": "solar_geometry",
        "implementation": "pyisis",
        "label": task.label,
        "cube_path": str(task.cube_path),
        "input_point_count": task.point_count,
        "successful_point_count": successful_point_count,
        "failed_count": failed_set_image_count,
        "failed_set_image_count": failed_set_image_count,
        "core_seconds": core_seconds,
        "points_per_second": _points_per_second(successful_point_count, core_seconds),
        "top_errors": [],
        **_zero_stats(("azimuth", "elevation")),
    }
    if task.keep_point_records:
        result["points"] = point_records
    return result


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


def build_cpp_dom_ori_command(
    cpp_path: str | Path,
    task: DomOriTaskConfig,
    output_path: str | Path,
) -> list[str]:
    return [
        str(cpp_path),
        "dom-ori",
        "--label",
        task.label,
        "--dom",
        str(task.dom_path),
        "--original",
        str(task.original_path),
        "--point-count",
        str(task.point_count),
        "--top-error-count",
        str(task.top_error_count),
        "--sampling-mode",
        task.sampling_mode,
        "--output",
        str(output_path),
    ]


def build_cpp_solar_geometry_command(
    cpp_path: str | Path,
    task: SolarGeometryTaskConfig,
    output_path: str | Path,
) -> list[str]:
    return [
        str(cpp_path),
        "solar-geometry",
        "--label",
        task.label,
        "--cube",
        str(task.cube_path),
        "--point-count",
        str(task.point_count),
        "--top-error-count",
        str(task.top_error_count),
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
        "tasks": (
            [task.label for task in config.camera_tasks]
            + [task.label for task in config.controlnet_tasks]
            + [task.label for task in config.dom_ori_tasks]
            + [task.label for task in config.solar_geometry_tasks]
        ),
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
    return (
        {task.label for task in config.camera_tasks}
        | {task.label for task in config.controlnet_tasks}
        | {task.label for task in config.dom_ori_tasks}
        | {task.label for task in config.solar_geometry_tasks}
    )


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

    for task in config.dom_ori_tasks:
        if not _is_selected(task.label, selected_labels):
            continue
        command = build_cpp_dom_ori_command(
            config.execution.cpp_benchmark_path,
            task,
            run_dir / "cpp" / f"{task.label}.json",
        )
        _write_command(run_dir / "cpp" / task.label / "command.sh", command)

    for task in config.solar_geometry_tasks:
        if not _is_selected(task.label, selected_labels):
            continue
        command = build_cpp_solar_geometry_command(
            config.execution.cpp_benchmark_path,
            task,
            run_dir / "cpp" / f"{task.label}.json",
        )
        _write_command(run_dir / "cpp" / task.label / "command.sh", command)


def _exception_message(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


def _record_pyisis_result(
    path: Path,
    task_runner,
    task,
    *,
    task_type: str,
    label: str,
    keep_going: bool,
) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        result = task_runner(task)
    except Exception as error:
        wall_seconds = time.perf_counter() - start
        if not keep_going:
            raise
        error_message = _exception_message(error)
        result = {
            "status": "failed",
            "implementation": "pyisis",
            "label": label,
            "task_type": task_type,
            "error": error_message,
            "stderr": error_message,
            "wall_seconds": wall_seconds,
        }
        _write_json(path, result)
        return result

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

    try:
        cpp_result = load_cpp_result(path)
    except (OSError, ValueError) as error:
        error_message = f"Failed to load C++ result from {path}: {error}"
        if not keep_going:
            raise RuntimeError(error_message) from error
        failure_result = {
            "task_type": task_type,
            "implementation": "cpp",
            "label": label,
            **execution_result,
            "status": "failed",
            "error": error_message,
            "stderr": execution_result.get("stderr") or error_message,
        }
        _write_json(path, failure_result)
        return failure_result

    cpp_result = dict(cpp_result)
    cpp_result["status"] = "success"
    cpp_result["return_code"] = execution_result["return_code"]
    cpp_result["stdout"] = execution_result["stdout"]
    cpp_result["stderr"] = execution_result["stderr"]
    cpp_result["command"] = execution_result["command"]
    cpp_result["wall_seconds"] = execution_result["wall_seconds"]
    return cpp_result


def _validate_real_run_inputs(config: BenchmarkConfig, selected_labels: set[str] | None) -> None:
    missing_paths: list[str] = []
    for task in config.camera_tasks:
        if _is_selected(task.label, selected_labels) and not task.cube_path.exists():
            missing_paths.append(f"camera {task.label} cube_path={task.cube_path}")
    for task in config.controlnet_tasks:
        if _is_selected(task.label, selected_labels) and not task.net_path.exists():
            missing_paths.append(f"controlnet {task.label} net_path={task.net_path}")
    for task in config.dom_ori_tasks:
        if _is_selected(task.label, selected_labels) and not task.dom_path.exists():
            missing_paths.append(f"dom_ori {task.label} dom_path={task.dom_path}")
        if _is_selected(task.label, selected_labels) and not task.original_path.exists():
            missing_paths.append(f"dom_ori {task.label} original_path={task.original_path}")
    for task in config.solar_geometry_tasks:
        if _is_selected(task.label, selected_labels) and not task.cube_path.exists():
            missing_paths.append(f"solar_geometry {task.label} cube_path={task.cube_path}")
    if missing_paths:
        raise ValueError(f"Missing benchmark input path(s): {'; '.join(missing_paths)}")


def collect_provenance(config: BenchmarkConfig, run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    pyisis_import_path = None
    try:
        ip_module = _import_isis_pybind()
        module_path = getattr(ip_module, "__file__", None)
        if module_path is not None:
            pyisis_import_path = str(module_path)
    except Exception:
        pyisis_import_path = None

    repo_root = Path(__file__).resolve().parents[3]
    git_commit = None
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode == 0:
            git_commit = completed.stdout.strip() or None
    except OSError:
        git_commit = None

    return {
        "config_snapshot": str(run_dir / "experiment_config.json"),
        "pyisis_import_path": pyisis_import_path,
        "cpp_benchmark_path": str(config.execution.cpp_benchmark_path),
        "ISISDATA": os.environ.get("ISISDATA"),
        "CONDA_DEFAULT_ENV": os.environ.get("CONDA_DEFAULT_ENV"),
        "git_commit": git_commit,
    }


def run_benchmark(
    config: BenchmarkConfig,
    *,
    output_root: str | Path,
    dry_run: bool,
    only: set[str] | None,
    keep_going: bool,
) -> Path:
    selected_labels = _selected_labels(config, only)
    if not dry_run:
        _validate_real_run_inputs(config, selected_labels)
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
            task_type="camera",
            label=task.label,
            keep_going=keep_going,
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
        if pyisis_result.get("status") == "success" and cpp_result.get("status") == "success":
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
            task_type="controlnet",
            label=task.label,
            keep_going=keep_going,
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

    for task in config.dom_ori_tasks:
        if not _is_selected(task.label, selected_labels):
            continue

        pyisis_result = _record_pyisis_result(
            run_dir / "pyisis" / f"{task.label}.json",
            run_pyisis_dom_ori_task,
            task,
            task_type="dom_ori",
            label=task.label,
            keep_going=keep_going,
        )
        results.append(pyisis_result)

        cpp_output_path = run_dir / "cpp" / f"{task.label}.json"
        cpp_command = build_cpp_dom_ori_command(config.execution.cpp_benchmark_path, task, cpp_output_path)
        _write_command(run_dir / "cpp" / task.label / "command.sh", cpp_command)
        cpp_result = _record_cpp_result(
            cpp_output_path,
            cpp_command,
            task_type="dom_ori",
            label=task.label,
            keep_going=keep_going,
        )
        results.append(cpp_result)

    for task in config.solar_geometry_tasks:
        if not _is_selected(task.label, selected_labels):
            continue

        pyisis_result = _record_pyisis_result(
            run_dir / "pyisis" / f"{task.label}.json",
            run_pyisis_solar_geometry_task,
            task,
            task_type="solar_geometry",
            label=task.label,
            keep_going=keep_going,
        )
        results.append(pyisis_result)

        cpp_output_path = run_dir / "cpp" / f"{task.label}.json"
        cpp_command = build_cpp_solar_geometry_command(config.execution.cpp_benchmark_path, task, cpp_output_path)
        _write_command(run_dir / "cpp" / task.label / "command.sh", cpp_command)
        cpp_result = _record_cpp_result(
            cpp_output_path,
            cpp_command,
            task_type="solar_geometry",
            label=task.label,
            keep_going=keep_going,
        )
        results.append(cpp_result)

    write_summary_reports(run_dir, results, camera_comparisons, provenance=collect_provenance(config, run_dir))
    return run_dir


def write_summary_reports(
    run_dir: str | Path,
    results: list[dict[str, Any]],
    camera_comparisons: list[dict[str, Any]],
    *,
    provenance: dict[str, Any] | None = None,
) -> None:
    reports_dir = Path(run_dir) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "results": results,
        "camera_comparisons": camera_comparisons,
        "provenance": provenance or {},
    }
    (reports_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_summary_csv(reports_dir / "summary.csv", results, camera_comparisons)
    _write_camera_top_errors(reports_dir / "camera_top_errors.csv", camera_comparisons)
    _write_precision_comparison(reports_dir / "precision_comparison.json", results, provenance or {})
    write_benchmark_figure(reports_dir, results, camera_comparisons)

    controlnet_results = [result for result in results if result.get("task_type") == "controlnet"]
    (reports_dir / "controlnet_summary.json").write_text(
        json.dumps({"results": controlnet_results, "provenance": provenance or {}}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_precision_comparison(path: Path, results: list[dict[str, Any]], provenance: dict[str, Any]) -> None:
    dom_fields = [
        "label",
        "implementation",
        "sampling_mode",
        "input_point_count",
        "roundtrip_successful_count",
        "roundtrip_success_rate",
        "sample_abs_max",
        "sample_abs_mean",
        "sample_abs_rms",
        "line_abs_max",
        "line_abs_mean",
        "line_abs_rms",
        "pixel_error_abs_max",
        "pixel_error_abs_mean",
        "pixel_error_abs_rms",
        "top_errors",
    ]
    solar_fields = [
        "label",
        "implementation",
        "input_point_count",
        "successful_point_count",
        "azimuth_abs_max",
        "azimuth_abs_mean",
        "azimuth_abs_rms",
        "elevation_abs_max",
        "elevation_abs_mean",
        "elevation_abs_rms",
        "top_errors",
    ]

    def project(row: dict[str, Any], fields: list[str]) -> dict[str, Any]:
        return {field: row.get(field) for field in fields if field in row}

    payload = {
        "dom_ori": [
            project(row, dom_fields)
            for row in results
            if row.get("status") == "success" and row.get("task_type") == "dom_ori"
        ],
        "solar_geometry": [
            project(row, solar_fields)
            for row in results
            if row.get("status") == "success" and row.get("task_type") == "solar_geometry"
        ],
        "provenance": provenance,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
        "file_size_bytes",
        "points_per_second",
        "roundtrip_points_per_second",
        "measures_per_second",
        "successful_point_count",
        "roundtrip_successful_count",
        "roundtrip_success_rate",
        "ori_to_dom_seconds",
        "dom_to_ori_seconds",
        "matched_point_count",
        "missing_in_pyisis_count",
        "missing_in_cpp_count",
        "latitude_abs_max",
        "longitude_abs_max",
        "sample_abs_max",
        "line_abs_max",
        "pixel_error_abs_max",
        "azimuth_abs_max",
        "elevation_abs_max",
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


def write_benchmark_figure(
    reports_dir: str | Path,
    results: list[dict[str, Any]],
    camera_comparisons: list[dict[str, Any]],
) -> None:
    reports_dir = Path(reports_dir)
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
        }
    )

    successful = [result for result in results if result.get("status") == "success"]
    fig, axes_grid = plt.subplots(2, 3, figsize=(7.2, 4.4), constrained_layout=True)
    axes = list(axes_grid.ravel())
    panel_specs = [
        ("A  DOM/ORI speed", "dom_ori", "roundtrip_points_per_second", "points/s"),
        ("B  DOM/ORI precision", "dom_ori", "pixel_error_abs_max", "max pixel error"),
        ("C  Solar speed", "solar_geometry", "points_per_second", "points/s"),
        ("D  Solar precision", "solar_geometry", "azimuth_abs_max", "max angle error"),
        ("E  ControlNet traversal", "controlnet", "measures_per_second", "measures/s"),
    ]
    colors = {"pyisis": "#4C78A8", "cpp": "#F58518"}
    for axis, (title, task_type, metric, ylabel) in zip(axes, panel_specs):
        rows = [result for result in successful if result.get("task_type") == task_type]
        labels = [f"{row.get('label')}\n{row.get('implementation')}" for row in rows]
        values = [float(row.get(metric) or 0.0) for row in rows]
        bar_colors = [colors.get(str(row.get("implementation")), "#6B7280") for row in rows]
        axis.bar(range(len(rows)), values, color=bar_colors, width=0.72)
        axis.set_title(title, loc="left", fontweight="bold")
        axis.set_ylabel(ylabel)
        axis.set_xticks(range(len(rows)), labels, rotation=35, ha="right")
        if not rows:
            axis.text(0.5, 0.5, "No data", transform=axis.transAxes, ha="center", va="center", color="#666666")
    axes[-1].axis("off")

    figure_base = reports_dir / "benchmark_figure"
    fig.savefig(f"{figure_base}.svg", bbox_inches="tight")
    fig.savefig(f"{figure_base}.pdf", bbox_inches="tight")
    fig.savefig(f"{figure_base}.tiff", dpi=600, bbox_inches="tight")
    plt.close(fig)


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
        help="Record task failures and continue writing reports",
    )
    failure_group.add_argument(
        "--fail-fast",
        action="store_false",
        dest="keep_going",
        help="Raise on the first C++ command failure",
    )
    parser.set_defaults(keep_going=True)
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
