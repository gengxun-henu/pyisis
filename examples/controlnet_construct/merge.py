"""Duplicate tie-point merging helpers for overlapping image blocks."""

from __future__ import annotations

from dataclasses import dataclass

from .keypoints import Keypoint, KeypointFile


@dataclass(frozen=True, slots=True)
class MergeSummary:
    input_count: int
    unique_count: int
    duplicate_count: int


def _pair_hash_key(left_point: Keypoint, right_point: Keypoint, decimals: int) -> tuple[float, float, float, float]:
    return (
        round(left_point.sample, decimals),
        round(left_point.line, decimals),
        round(right_point.sample, decimals),
        round(right_point.line, decimals),
    )


def merge_duplicate_keypoints(
    left_keypoints: KeypointFile,
    right_keypoints: KeypointFile,
    *,
    decimals: int = 3,
) -> tuple[KeypointFile, KeypointFile, MergeSummary]:
    """Merge duplicate tie points using rounded stereo-pair pixel coordinates."""
    if len(left_keypoints.points) != len(right_keypoints.points):
        raise ValueError("Left and right keypoint files must contain the same number of points.")

    unique_left: list[Keypoint] = []
    unique_right: list[Keypoint] = []
    seen: set[tuple[float, float, float, float]] = set()

    for left_point, right_point in zip(left_keypoints.points, right_keypoints.points, strict=True):
        pair_hash = _pair_hash_key(left_point, right_point, decimals)
        if pair_hash in seen:
            continue
        seen.add(pair_hash)
        unique_left.append(left_point)
        unique_right.append(right_point)

    summary = MergeSummary(
        input_count=len(left_keypoints.points),
        unique_count=len(unique_left),
        duplicate_count=len(left_keypoints.points) - len(unique_left),
    )
    return (
        KeypointFile(left_keypoints.image_width, left_keypoints.image_height, tuple(unique_left)),
        KeypointFile(right_keypoints.image_width, right_keypoints.image_height, tuple(unique_right)),
        summary,
    )