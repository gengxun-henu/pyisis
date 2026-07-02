"""Measure-level DOM-space RANSAC filter for ControlNet.

Projects original-image ControlMeasure coordinates to DOM pixels, runs
pair-parallel RANSAC, marks outlier measures ignored, and writes auditable
reports.

Author: Geng Xun
Created: 2026-07-02
"""

from __future__ import annotations

import math

from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar

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
    for original_path, dom_path in aligned_pairs:
        original_serial = ip_module.SerialNumber.compose(str(original_path))
        dom_serial = ip_module.SerialNumber.compose(str(dom_path))
        original_by_serial[original_serial] = original_path
        dom_by_serial[dom_serial] = dom_path
    return SerialPathMaps(original_by_serial=original_by_serial, dom_by_serial=dom_by_serial)


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

    def _ensure_cube(self, serial: str, path: Path):
        path_str = str(path)
        cube = self._cube_cache.get(path_str)
        if serial not in self._camera_cache:
            self._camera_cache[serial] = cube.camera()
            self._projection_cache[serial] = cube.projection()

    def camera_for_serial(self, serial: str):
        return self._camera_cache[serial]

    def projection_for_serial(self, serial: str):
        return self._projection_cache[serial]

    def resolve(self, serial: str) -> None:
        if serial in self._camera_cache:
            return
        if serial in self._serial_maps.original_by_serial:
            self._ensure_cube(serial, self._serial_maps.original_by_serial[serial])
        elif serial in self._serial_maps.dom_by_serial:
            self._ensure_cube(serial, self._serial_maps.dom_by_serial[serial])
        else:
            raise KeyError(f"Serial {serial!r} not found in original or DOM path maps.")

    def close_all(self) -> None:
        self._cube_cache.close_all()
