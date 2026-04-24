"""Reusable stereo-pair RANSAC helpers for DOM/original-image `.key` files.

Author: Geng Xun
Created: 2026-04-24
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .keypoints import Keypoint, KeypointFile, read_key_file, write_key_file


def _normalize_ransac_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in {"strict", "loose"}:
        raise ValueError(f"Unsupported RANSAC mode {mode!r}. Expected 'strict' or 'loose'.")
    return normalized


def _build_ransac_summary(
    *,
    applied: bool,
    status: str,
    mode: str,
    input_count: int,
    retained_count: int,
    dropped_count: int,
    opencv_inlier_count: int,
    opencv_outlier_count: int,
    retained_soft_outlier_count: int,
    soft_outlier_original_indices: list[int],
    retained_soft_outlier_positions: list[int],
    reproj_threshold: float,
    confidence: float,
    max_iters: int,
    loose_keep_pixel_threshold: float,
    homography_matrix: list[list[float]] | None,
) -> dict[str, object]:
    return {
        "applied": applied,
        "status": status,
        "mode": mode,
        "input_count": input_count,
        "retained_count": retained_count,
        "dropped_count": dropped_count,
        "opencv_inlier_count": opencv_inlier_count,
        "opencv_outlier_count": opencv_outlier_count,
        "retained_soft_outlier_count": retained_soft_outlier_count,
        "soft_outlier_original_indices": soft_outlier_original_indices,
        "retained_soft_outlier_positions": retained_soft_outlier_positions,
        "reproj_threshold": float(reproj_threshold),
        "confidence": float(confidence),
        "max_iters": int(max_iters),
        "loose_keep_pixel_threshold": float(loose_keep_pixel_threshold),
        "homography_matrix": homography_matrix,
    }


def filter_stereo_pair_keypoints_with_ransac(
    left_key_file: KeypointFile,
    right_key_file: KeypointFile,
    *,
    ransac_reproj_threshold: float = 3.0,
    ransac_confidence: float = 0.995,
    ransac_max_iters: int = 5000,
    ransac_mode: str = "loose",
    loose_keep_pixel_threshold: float = 1.0,
) -> tuple[KeypointFile, KeypointFile, dict[str, object]]:
    if len(left_key_file.points) != len(right_key_file.points):
        raise ValueError("Left and right keypoint files must contain the same number of points.")

    normalized_mode = _normalize_ransac_mode(ransac_mode)
    input_count = len(left_key_file.points)

    if input_count < 4:
        summary = _build_ransac_summary(
            applied=False,
            status="skipped_insufficient_points",
            mode=normalized_mode,
            input_count=input_count,
            retained_count=input_count,
            dropped_count=0,
            opencv_inlier_count=input_count,
            opencv_outlier_count=0,
            retained_soft_outlier_count=0,
            soft_outlier_original_indices=[],
            retained_soft_outlier_positions=[],
            reproj_threshold=ransac_reproj_threshold,
            confidence=ransac_confidence,
            max_iters=ransac_max_iters,
            loose_keep_pixel_threshold=loose_keep_pixel_threshold,
            homography_matrix=None,
        )
        return left_key_file, right_key_file, summary

    left_points = np.asarray(
        [(point.sample, point.line) for point in left_key_file.points],
        dtype=np.float32,
    ).reshape(-1, 1, 2)
    right_points = np.asarray(
        [(point.sample, point.line) for point in right_key_file.points],
        dtype=np.float32,
    ).reshape(-1, 1, 2)
    homography, mask = cv2.findHomography(
        left_points,
        right_points,
        cv2.RANSAC,
        ransacReprojThreshold=float(ransac_reproj_threshold),
        confidence=float(ransac_confidence),
        maxIters=int(ransac_max_iters),
    )

    if homography is None or mask is None:
        summary = _build_ransac_summary(
            applied=False,
            status="skipped_homography_failed",
            mode=normalized_mode,
            input_count=input_count,
            retained_count=input_count,
            dropped_count=0,
            opencv_inlier_count=0,
            opencv_outlier_count=0,
            retained_soft_outlier_count=0,
            soft_outlier_original_indices=[],
            retained_soft_outlier_positions=[],
            reproj_threshold=ransac_reproj_threshold,
            confidence=ransac_confidence,
            max_iters=ransac_max_iters,
            loose_keep_pixel_threshold=loose_keep_pixel_threshold,
            homography_matrix=None,
        )
        return left_key_file, right_key_file, summary

    opencv_inlier_mask = mask.reshape(-1).astype(bool)
    retained_mask = opencv_inlier_mask.copy()
    soft_outlier_original_indices: list[int] = []

    if normalized_mode == "loose":
        projected_right = cv2.perspectiveTransform(left_points, homography).reshape(-1, 2)
        right_coordinates = right_points.reshape(-1, 2)
        for index, (is_inlier, projected, actual) in enumerate(
            zip(opencv_inlier_mask, projected_right, right_coordinates, strict=True)
        ):
            if is_inlier:
                continue
            reprojection_error = float(np.linalg.norm(projected - actual))
            if reprojection_error <= float(loose_keep_pixel_threshold):
                retained_mask[index] = True
                soft_outlier_original_indices.append(index)

    filtered_left_points: list[Keypoint] = []
    filtered_right_points: list[Keypoint] = []
    retained_soft_outlier_positions: list[int] = []
    retained_position = 0
    soft_outlier_original_index_set = set(soft_outlier_original_indices)
    for index, (left_point, right_point, keep_point) in enumerate(
        zip(left_key_file.points, right_key_file.points, retained_mask, strict=True)
    ):
        if not keep_point:
            continue
        filtered_left_points.append(left_point)
        filtered_right_points.append(right_point)
        if index in soft_outlier_original_index_set:
            retained_soft_outlier_positions.append(retained_position)
        retained_position += 1

    summary = _build_ransac_summary(
        applied=True,
        status="filtered",
        mode=normalized_mode,
        input_count=input_count,
        retained_count=len(filtered_left_points),
        dropped_count=input_count - len(filtered_left_points),
        opencv_inlier_count=int(opencv_inlier_mask.sum()),
        opencv_outlier_count=int((~opencv_inlier_mask).sum()),
        retained_soft_outlier_count=len(soft_outlier_original_indices),
        soft_outlier_original_indices=soft_outlier_original_indices,
        retained_soft_outlier_positions=retained_soft_outlier_positions,
        reproj_threshold=ransac_reproj_threshold,
        confidence=ransac_confidence,
        max_iters=ransac_max_iters,
        loose_keep_pixel_threshold=loose_keep_pixel_threshold,
        homography_matrix=homography.tolist(),
    )
    return (
        KeypointFile(left_key_file.image_width, left_key_file.image_height, tuple(filtered_left_points)),
        KeypointFile(right_key_file.image_width, right_key_file.image_height, tuple(filtered_right_points)),
        summary,
    )


def filter_stereo_pair_key_files_with_ransac(
    left_input: str | Path,
    right_input: str | Path,
    left_output: str | Path,
    right_output: str | Path,
    *,
    ransac_reproj_threshold: float = 3.0,
    ransac_confidence: float = 0.995,
    ransac_max_iters: int = 5000,
    ransac_mode: str = "loose",
    loose_keep_pixel_threshold: float = 1.0,
) -> dict[str, object]:
    left_key_file = read_key_file(left_input)
    right_key_file = read_key_file(right_input)
    filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_with_ransac(
        left_key_file,
        right_key_file,
        ransac_reproj_threshold=ransac_reproj_threshold,
        ransac_confidence=ransac_confidence,
        ransac_max_iters=ransac_max_iters,
        ransac_mode=ransac_mode,
        loose_keep_pixel_threshold=loose_keep_pixel_threshold,
    )
    write_key_file(left_output, filtered_left)
    write_key_file(right_output, filtered_right)
    return {
        **summary,
        "left_input": str(left_input),
        "right_input": str(right_input),
        "left_output": str(left_output),
        "right_output": str(right_output),
    }


__all__ = [
    "filter_stereo_pair_key_files_with_ransac",
    "filter_stereo_pair_keypoints_with_ransac",
]
