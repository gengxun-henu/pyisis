"""Measure-level DOM-space RANSAC filter for ControlNet.

Projects original-image ControlMeasure coordinates to DOM pixels, runs
pair-parallel RANSAC, marks outlier measures ignored, and writes auditable
reports.

Author: Geng Xun
Created: 2026-07-02
"""

from __future__ import annotations

import argparse
import json
import math
import sys

import numpy as np
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.stereo_ransac import compute_ransac_retained_mask
else:
    from .stereo_ransac import compute_ransac_retained_mask

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class MeasureKey:
    point_index: int
    point_id: str
    measure_index: int
    serial: str


@dataclass(frozen=True, slots=True)
class MeasureRecord:
    key: MeasureKey
    sample: float
    line: float


@dataclass(frozen=True, slots=True)
class PairRecord:
    left: MeasureRecord
    right: MeasureRecord


def _serial_pair_key(left_serial: str, right_serial: str) -> tuple[str, str]:
    return (left_serial, right_serial) if left_serial <= right_serial else (right_serial, left_serial)


def group_measure_pairs_by_serial_pair(records: list[MeasureRecord]) -> dict[tuple[str, str], list[PairRecord]]:
    by_point: dict[tuple[int, str], list[MeasureRecord]] = defaultdict(list)
    for record in records:
        by_point[(record.key.point_index, record.key.point_id)].append(record)

    grouped: dict[tuple[str, str], list[PairRecord]] = defaultdict(list)
    for point_records in by_point.values():
        if len(point_records) < 2:
            continue
        for left_index in range(len(point_records)):
            for right_index in range(left_index + 1, len(point_records)):
                left = point_records[left_index]
                right = point_records[right_index]
                if left.key.serial == right.key.serial:
                    continue
                key = _serial_pair_key(left.key.serial, right.key.serial)
                if key[0] == left.key.serial:
                    grouped[key].append(PairRecord(left, right))
                else:
                    grouped[key].append(PairRecord(right, left))
    return dict(grouped)


def extract_active_measure_records(net) -> list[MeasureRecord]:
    records: list[MeasureRecord] = []
    for point_index in range(net.get_num_points()):
        point = net.get_point(point_index)
        if point.is_ignored():
            continue
        point_id = point.get_id()
        for measure_index in range(point.get_num_measures()):
            measure = point.get_measure(measure_index)
            if measure.is_ignored():
                continue
            serial = measure.get_cube_serial_number()
            records.append(
                MeasureRecord(
                    key=MeasureKey(point_index, point_id, measure_index, serial),
                    sample=float(measure.get_sample()),
                    line=float(measure.get_line()),
                )
            )
    return records


def apply_ignored_measures(net, outlier_keys: set[MeasureKey]) -> int:
    changed = 0
    for key in sorted(outlier_keys, key=lambda item: (item.point_index, item.measure_index, item.serial)):
        point = net.get_point(key.point_index)
        if point.get_id() != key.point_id:
            raise ValueError(
                f"Point index/key mismatch at index {key.point_index}: expected {key.point_id!r}, got {point.get_id()!r}."
            )
        measure = point.get_measure(key.measure_index)
        if measure.get_cube_serial_number() != key.serial:
            raise ValueError(
                f"Measure index/key mismatch for point {key.point_id}: expected {key.serial!r}, got {measure.get_cube_serial_number()!r}."
            )
        if not measure.is_ignored():
            measure.set_ignored(True)
            changed += 1
    return changed


def _read_lis(path: Path) -> list[Path]:
    base = path.parent
    entries: list[Path] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        candidate = Path(value)
        entries.append(candidate if candidate.is_absolute() else base / candidate)
    return entries


def read_aligned_cube_lists(original_list: Path, dom_list: Path) -> list[tuple[Path, Path]]:
    originals = _read_lis(original_list)
    doms = _read_lis(dom_list)
    if len(originals) != len(doms):
        raise ValueError(
            f"Original and DOM list length mismatch: {original_list} has {len(originals)}, {dom_list} has {len(doms)}."
        )
    return list(zip(originals, doms, strict=True))


class BoundedCubeCache:
    def __init__(self, *, max_open: int, factory: Callable[[str], T]):
        if max_open <= 0:
            raise ValueError("max_open must be positive.")
        self._max_open = max_open
        self._factory = factory
        self._items: OrderedDict[str, T] = OrderedDict()

    def get(self, path: str) -> T:
        if path in self._items:
            value = self._items.pop(path)
            self._items[path] = value
            return value
        value = self._factory(path)
        self._items[path] = value
        while len(self._items) > self._max_open:
            _, evicted = self._items.popitem(last=False)
            close = getattr(evicted, "close", None)
            if close is not None:
                close()
        return value

    def close_all(self) -> None:
        while self._items:
            _, value = self._items.popitem(last=False)
            close = getattr(value, "close", None)
            if close is not None:
                close()


@dataclass(frozen=True, slots=True)
class SerialPathMaps:
    original_by_serial: dict[str, Path]
    dom_by_serial: dict[str, Path]
    dom_serial_by_original_serial: dict[str, str]


@dataclass(frozen=True, slots=True)
class ProjectionFailure:
    measure_key: MeasureKey
    original_sample: float
    original_line: float
    failure_stage: str
    message: str


def build_serial_path_maps(aligned_pairs: list[tuple[Path, Path]], *, ip_module) -> SerialPathMaps:
    original_by_serial: dict[str, Path] = {}
    dom_by_serial: dict[str, Path] = {}
    dom_serial_by_original_serial: dict[str, str] = {}
    for original_path, dom_path in aligned_pairs:
        original_serial = ip_module.SerialNumber.compose(str(original_path))
        dom_serial = ip_module.SerialNumber.compose(str(dom_path))
        original_by_serial[original_serial] = original_path
        dom_by_serial[dom_serial] = dom_path
        dom_serial_by_original_serial[original_serial] = dom_serial
    return SerialPathMaps(
        original_by_serial=original_by_serial,
        dom_by_serial=dom_by_serial,
        dom_serial_by_original_serial=dom_serial_by_original_serial,
    )


def project_measure_to_dom(record: MeasureRecord, camera, projection) -> tuple[float, float] | ProjectionFailure:
    if not (math.isfinite(record.sample) and math.isfinite(record.line)):
        return ProjectionFailure(record.key, record.sample, record.line, "invalid_original_coordinate", "Sample/line is not finite.")
    if not camera.set_image(record.sample, record.line):
        return ProjectionFailure(record.key, record.sample, record.line, "camera_set_image_failed", "Camera failed to set image coordinate.")
    latitude = float(camera.universal_latitude())
    longitude = float(camera.universal_longitude())
    if not (math.isfinite(latitude) and math.isfinite(longitude)):
        return ProjectionFailure(record.key, record.sample, record.line, "invalid_ground_coordinate", "Camera returned non-finite ground coordinate.")
    if not projection.set_universal_ground(latitude, longitude):
        return ProjectionFailure(record.key, record.sample, record.line, "dom_set_universal_ground_failed", "DOM projection failed to set universal ground.")
    dom_sample = float(projection.world_x())
    dom_line = float(projection.world_y())
    if not (math.isfinite(dom_sample) and math.isfinite(dom_line)):
        return ProjectionFailure(record.key, record.sample, record.line, "invalid_dom_coordinate", "DOM projection returned non-finite sample/line.")
    return dom_sample, dom_line


class WorkerProjectorCache:
    def __init__(self, serial_maps: SerialPathMaps, *, max_open: int, ip_module):
        self._ip = ip_module
        self._serial_maps = serial_maps
        self._cube_cache = BoundedCubeCache(max_open=max_open, factory=self._open_cube)
        self._camera_cache: dict[str, object] = {}
        self._projection_cache: dict[str, object] = {}

    def _open_cube(self, path: str):
        cube = self._ip.Cube()
        cube.open(path, "r")
        return cube

    def _ensure_camera(self, serial: str):
        if serial in self._camera_cache:
            return
        path = self._serial_maps.original_by_serial.get(serial)
        if path is None:
            raise KeyError(f"Serial {serial!r} not found in original path maps.")
        cube = self._cube_cache.get(str(path))
        self._camera_cache[serial] = cube.camera()

    def _ensure_projection(self, serial: str):
        if serial in self._projection_cache:
            return
        dom_serial = self._serial_maps.dom_serial_by_original_serial.get(serial)
        if dom_serial is None:
            raise KeyError(f"Serial {serial!r} has no DOM counterpart.")
        dom_path = self._serial_maps.dom_by_serial.get(dom_serial)
        if dom_path is None:
            raise KeyError(f"DOM serial {dom_serial!r} not found in DOM path maps.")
        cube = self._cube_cache.get(str(dom_path))
        self._projection_cache[serial] = cube.projection()

    def camera_for_serial(self, serial: str):
        return self._camera_cache[serial]

    def projection_for_serial(self, serial: str):
        return self._projection_cache[serial]

    def resolve(self, serial: str) -> None:
        self._ensure_camera(serial)
        self._ensure_projection(serial)

    def close_all(self) -> None:
        self._cube_cache.close_all()


@dataclass(frozen=True, slots=True)
class RansacOptions:
    model: str = "affine-partial"
    reproj_threshold: float = 10.0
    confidence: float = 0.995
    max_iters: int = 5000
    mode: str = "loose"
    loose_keep_pixel_threshold: float = 1.0


@dataclass(frozen=True, slots=True)
class PairTask:
    serial_pair: tuple[str, str]
    records: list[PairRecord]


@dataclass(frozen=True, slots=True)
class PairRansacResult:
    serial_pair: tuple[str, str]
    outlier_measure_keys: set[MeasureKey]
    projection_failures: list[ProjectionFailure]
    summary: dict[str, object]


def run_pair_ransac_task(
    task: PairTask,
    serial_maps: SerialPathMaps | None,
    options: RansacOptions,
    projector_cache: WorkerProjectorCache | None,
) -> PairRansacResult:
    left_serial, right_serial = task.serial_pair
    projection_failures: list[ProjectionFailure] = []
    projected_pairs: list[tuple[tuple[float, float], tuple[float, float], PairRecord]] = []

    for record in task.records:
        left_result = project_measure_to_dom(
            record.left,
            projector_cache.camera_for_serial(record.left.key.serial) if projector_cache else None,
            projector_cache.projection_for_serial(record.left.key.serial) if projector_cache else None,
        )
        if isinstance(left_result, ProjectionFailure):
            projection_failures.append(left_result)
            continue
        right_result = project_measure_to_dom(
            record.right,
            projector_cache.camera_for_serial(record.right.key.serial) if projector_cache else None,
            projector_cache.projection_for_serial(record.right.key.serial) if projector_cache else None,
        )
        if isinstance(right_result, ProjectionFailure):
            projection_failures.append(right_result)
            continue
        projected_pairs.append((left_result, right_result, record))

    if not projected_pairs:
        return PairRansacResult(
            serial_pair=task.serial_pair,
            outlier_measure_keys=set(),
            projection_failures=projection_failures,
            summary={
                "status": "skipped_no_projected_correspondences",
                "input_count": len(task.records),
                "projected_count": 0,
                "projection_failure_count": len(projection_failures),
            },
        )

    left_dom_points = np.array([p[0] for p in projected_pairs], dtype=np.float64)
    right_dom_points = np.array([p[1] for p in projected_pairs], dtype=np.float64)

    retained_mask = compute_ransac_retained_mask(
        left_dom_points,
        right_dom_points,
        ransac_model=options.model,
        ransac_reproj_threshold=options.reproj_threshold,
        ransac_confidence=options.confidence,
        ransac_max_iters=options.max_iters,
        ransac_mode=options.mode,
        loose_keep_pixel_threshold=options.loose_keep_pixel_threshold,
    )

    outlier_keys: set[MeasureKey] = set()
    dropped_count = 0
    for index, (_, _, record) in enumerate(projected_pairs):
        if not retained_mask[index]:
            outlier_keys.add(record.left.key)
            outlier_keys.add(record.right.key)
            dropped_count += 1

    summary = {
        "status": "filtered",
        "input_count": len(task.records),
        "projected_count": len(projected_pairs),
        "retained_count": int(retained_mask.sum()),
        "dropped_count": dropped_count,
        "projection_failure_count": len(projection_failures),
    }

    return PairRansacResult(
        serial_pair=task.serial_pair,
        outlier_measure_keys=outlier_keys,
        projection_failures=projection_failures,
        summary=summary,
    )


def aggregate_worker_results(
    results: list[PairRansacResult],
) -> tuple[set[MeasureKey], list[ProjectionFailure], list[dict[str, object]]]:
    outliers: set[MeasureKey] = set()
    failures: list[ProjectionFailure] = []
    summaries: list[dict[str, object]] = []
    for result in results:
        outliers.update(result.outlier_measure_keys)
        failures.extend(result.projection_failures)
        summaries.append({
            "left_serial": result.serial_pair[0],
            "right_serial": result.serial_pair[1],
            **result.summary,
        })
    return outliers, failures, summaries


def measure_key_to_dict(key: MeasureKey) -> dict[str, object]:
    return {
        "point_index": key.point_index,
        "point_id": key.point_id,
        "measure_index": key.measure_index,
        "serial": key.serial,
    }


def projection_failure_to_dict(failure: ProjectionFailure) -> dict[str, object]:
    return {
        **measure_key_to_dict(failure.measure_key),
        "original_sample": failure.original_sample,
        "original_line": failure.original_line,
        "failure_stage": failure.failure_stage,
        "message": failure.message,
    }


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_summary_report(path: Path, report: dict[str, object]) -> None:
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
        file.write("\n")


def run_pair_tasks(
    tasks: list[PairTask],
    serial_maps: SerialPathMaps,
    options: RansacOptions,
    *,
    num_workers: int,
    max_open_cubes_per_worker: int,
    ip_module=None,
) -> list[PairRansacResult]:
    if num_workers <= 1:
        cache = WorkerProjectorCache(serial_maps, max_open=max_open_cubes_per_worker, ip_module=ip_module)
        try:
            for task in tasks:
                for serial in task.serial_pair:
                    cache.resolve(serial)
            return [
                run_pair_ransac_task(task, serial_maps, options, cache)
                for task in tasks
            ]
        finally:
            cache.close_all()

    from concurrent.futures import ProcessPoolExecutor, as_completed

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(
                _run_pair_ransac_task_in_subprocess,
                task, serial_maps, options, max_open_cubes_per_worker,
            )
            for task in tasks
        ]
        return [future.result() for future in as_completed(futures)]


def _run_pair_ransac_task_in_subprocess(
    task: PairTask,
    serial_maps: SerialPathMaps,
    options: RansacOptions,
    max_open_cubes_per_worker: int,
) -> PairRansacResult:
    import isis_pybind._isis_core as ip_module
    cache = WorkerProjectorCache(serial_maps, max_open=max_open_cubes_per_worker, ip_module=ip_module)
    try:
        for serial in task.serial_pair:
            cache.resolve(serial)
        return run_pair_ransac_task(task, serial_maps, options, cache)
    finally:
        cache.close_all()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure-level DOM-space RANSAC filter for ControlNet.",
    )
    parser.add_argument("--input-net", type=Path, required=True)
    parser.add_argument("--original-list", type=Path, required=True)
    parser.add_argument("--dom-list", type=Path, required=True)
    parser.add_argument("--output-net", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--outlier-measures", type=Path, required=True)
    parser.add_argument("--projection-failures", type=Path, required=True)
    parser.add_argument("--ransac-model", choices=("affine-partial", "affine", "homography"), default="affine-partial")
    parser.add_argument("--ransac-reproj-threshold", type=float, default=10.0)
    parser.add_argument("--ransac-confidence", type=float, default=0.995)
    parser.add_argument("--ransac-max-iters", type=int, default=5000)
    parser.add_argument("--ransac-mode", choices=("strict", "loose"), default="loose")
    parser.add_argument("--loose-ransac-keep-threshold", type=float, default=1.0)
    parser.add_argument("--num-workers", type=int, default=1)
    parser.add_argument("--max-open-cubes-per-worker", type=int, default=16)
    parser.add_argument("--pvl", action="store_true", default=False, help="Write PVL text output instead of binary.")
    return parser


def filter_controlnet_dom_ransac(args, *, ip_module) -> dict[str, object]:
    aligned = read_aligned_cube_lists(args.original_list, args.dom_list)
    serial_maps = build_serial_path_maps(aligned, ip_module=ip_module)
    net = ip_module.ControlNet(str(args.input_net))

    input_point_count = net.get_num_points()
    records = extract_active_measure_records(net)
    input_measure_count = len(records)

    grouped = group_measure_pairs_by_serial_pair(records)
    tasks = [PairTask(serial_pair, pair_records) for serial_pair, pair_records in grouped.items()]

    options = RansacOptions(
        model=args.ransac_model,
        reproj_threshold=args.ransac_reproj_threshold,
        confidence=args.ransac_confidence,
        max_iters=args.ransac_max_iters,
        mode=args.ransac_mode,
        loose_keep_pixel_threshold=args.loose_ransac_keep_threshold,
    )

    results = run_pair_tasks(
        tasks, serial_maps, options,
        num_workers=args.num_workers,
        max_open_cubes_per_worker=args.max_open_cubes_per_worker,
        ip_module=ip_module,
    )

    outlier_keys, projection_failures, pair_summaries = aggregate_worker_results(results)
    changed = apply_ignored_measures(net, outlier_keys)

    net.write(str(args.output_net), bool(args.pvl))

    sorted_outlier_keys = sorted(outlier_keys, key=lambda k: (k.point_index, k.measure_index, k.serial))
    write_jsonl(
        args.outlier_measures,
        [{"policy": "any_pair_outlier", **measure_key_to_dict(key)} for key in sorted_outlier_keys],
    )
    write_jsonl(
        args.projection_failures,
        [projection_failure_to_dict(failure) for failure in projection_failures],
    )

    report = {
        "input_point_count": input_point_count,
        "input_measure_count": input_measure_count,
        "pair_count": len(tasks),
        "outlier_measure_count": len(outlier_keys),
        "projection_failure_count": len(projection_failures),
        "changed_measure_count": changed,
        "output_net": str(args.output_net),
        "pair_summaries": pair_summaries,
    }
    write_summary_report(args.report, report)
    return report


def main(argv: list[str] | None = None) -> int:
    import isis_pybind._isis_core as ip
    args = build_argument_parser().parse_args(argv)
    report = filter_controlnet_dom_ransac(args, ip_module=ip)
    print(json.dumps({
        "input_point_count": report["input_point_count"],
        "input_measure_count": report["input_measure_count"],
        "outlier_measure_count": report["outlier_measure_count"],
        "projection_failure_count": report["projection_failure_count"],
        "output_net": report["output_net"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
