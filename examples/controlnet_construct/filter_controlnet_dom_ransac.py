"""Measure-level DOM-space RANSAC filter for ControlNet.

Projects original-image ControlMeasure coordinates to DOM pixels, runs
pair-parallel RANSAC, marks outlier measures ignored, and writes auditable
reports.

Author: Geng Xun
Created: 2026-07-02
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


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
