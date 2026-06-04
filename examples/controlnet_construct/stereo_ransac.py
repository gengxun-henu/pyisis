"""Reusable stereo-pair RANSAC helpers for DOM/original-image `.key` files.

Author: Geng Xun
Created: 2026-04-24
Updated: 2026-05-11  Geng Xun added top-of-file metadata history so example stereo RANSAC helpers stay consistent with other example modules.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .keypoints import Keypoint, KeypointFile, read_key_file, write_key_file


DEFAULT_RANSAC_MODEL = "affine-partial"
DEFAULT_RANSAC_REPROJ_THRESHOLD = 10.0
SUPPORTED_RANSAC_MODELS = ("affine-partial", "affine", "homography")


def _normalize_ransac_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in {"strict", "loose"}:
        raise ValueError(f"Unsupported RANSAC mode {mode!r}. Expected 'strict' or 'loose'.")
    return normalized


def _normalize_ransac_model(model: str) -> str:
    normalized = str(model).strip().lower()
    if normalized not in SUPPORTED_RANSAC_MODELS:
        raise ValueError("ransac_model must be one of: affine-partial, affine, homography.")
    return normalized


def _build_ransac_summary(
    *,
    applied: bool,
    status: str,
    mode: str,
    model: str,
    coordinate_space: str,
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
    matrix: list[list[float]] | None,
    matrix_type: str | None,
    homography_matrix: list[list[float]] | None,
    skipped_reason: str | None = None,
) -> dict[str, object]:
    summary = {
        "applied": applied,
        "status": status,
        "mode": mode,
        "model": model,
        "coordinate_space": coordinate_space,
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
        "matrix": matrix,
        "matrix_type": matrix_type,
        "homography_matrix": homography_matrix,
    }
    if skipped_reason is not None:
        summary["skipped_reason"] = skipped_reason
    return summary


def filter_stereo_pair_keypoints_with_ransac(
    left_key_file: KeypointFile,
    right_key_file: KeypointFile,
    *,
    ransac_model: str = DEFAULT_RANSAC_MODEL,
    ransac_coordinate_space: str = "dom_pixel",
    ransac_reproj_threshold: float = DEFAULT_RANSAC_REPROJ_THRESHOLD,
    ransac_confidence: float = 0.995,
    ransac_max_iters: int = 5000,
    ransac_mode: str = "loose",
    loose_keep_pixel_threshold: float = 1.0,
) -> tuple[KeypointFile, KeypointFile, dict[str, object]]:
    if len(left_key_file.points) != len(right_key_file.points):
        raise ValueError("Left and right keypoint files must contain the same number of points.")

    normalized_mode = _normalize_ransac_mode(ransac_mode)
    normalized_model = _normalize_ransac_model(ransac_model)
    threshold = float(ransac_reproj_threshold)
    if not np.isfinite(threshold) or threshold <= 0.0:
        raise ValueError("ransac_reproj_threshold must be finite and positive.")
    input_count = len(left_key_file.points)

    minimum_points_by_model = {
        "affine-partial": 2,
        "affine": 3,
        "homography": 4,
    }
    minimum_points = minimum_points_by_model[normalized_model]
    if input_count < minimum_points:
        summary = _build_ransac_summary(
            applied=False,
            status="skipped_insufficient_points",
            mode=normalized_mode,
            model=normalized_model,
            coordinate_space=ransac_coordinate_space,
            input_count=input_count,
            retained_count=input_count,
            dropped_count=0,
            opencv_inlier_count=input_count,
            opencv_outlier_count=0,
            retained_soft_outlier_count=0,
            soft_outlier_original_indices=[],
            retained_soft_outlier_positions=[],
            reproj_threshold=threshold,
            confidence=ransac_confidence,
            max_iters=ransac_max_iters,
            loose_keep_pixel_threshold=loose_keep_pixel_threshold,
            matrix=None,
            matrix_type=None,
            homography_matrix=None,
            skipped_reason="insufficient_points",
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
    left_xy = left_points.reshape(-1, 2)
    right_xy = right_points.reshape(-1, 2)
    if normalized_model == "affine-partial":
        model_matrix, mask = cv2.estimateAffinePartial2D(
            left_xy,
            right_xy,
            method=cv2.RANSAC,
            ransacReprojThreshold=threshold,
            confidence=float(ransac_confidence),
            maxIters=int(ransac_max_iters),
        )
        matrix_type = "affine_2x3"
        homography_matrix = None
    elif normalized_model == "affine":
        model_matrix, mask = cv2.estimateAffine2D(
            left_xy,
            right_xy,
            method=cv2.RANSAC,
            ransacReprojThreshold=threshold,
            confidence=float(ransac_confidence),
            maxIters=int(ransac_max_iters),
        )
        matrix_type = "affine_2x3"
        homography_matrix = None
    else:
        model_matrix, mask = cv2.findHomography(
            left_points,
            right_points,
            cv2.RANSAC,
            ransacReprojThreshold=threshold,
            confidence=float(ransac_confidence),
            maxIters=int(ransac_max_iters),
        )
        matrix_type = "homography_3x3"
        homography_matrix = None if model_matrix is None else model_matrix.tolist()

    if model_matrix is None or mask is None:
        summary = _build_ransac_summary(
            applied=False,
            status=f"skipped_{normalized_model.replace('-', '_')}_failed",
            mode=normalized_mode,
            model=normalized_model,
            coordinate_space=ransac_coordinate_space,
            input_count=input_count,
            retained_count=input_count,
            dropped_count=0,
            opencv_inlier_count=0,
            opencv_outlier_count=0,
            retained_soft_outlier_count=0,
            soft_outlier_original_indices=[],
            retained_soft_outlier_positions=[],
            reproj_threshold=threshold,
            confidence=ransac_confidence,
            max_iters=ransac_max_iters,
            loose_keep_pixel_threshold=loose_keep_pixel_threshold,
            matrix=None,
            matrix_type=None,
            homography_matrix=None,
            skipped_reason="model_estimation_failed",
        )
        return left_key_file, right_key_file, summary

    opencv_inlier_mask = mask.reshape(-1).astype(bool)
    retained_mask = opencv_inlier_mask.copy()
    soft_outlier_original_indices: list[int] = []

    if normalized_mode == "loose":
        if normalized_model == "homography":
            projected_right = cv2.perspectiveTransform(left_points, model_matrix).reshape(-1, 2)
        else:
            projected_right = (left_xy @ model_matrix[:, :2].T) + model_matrix[:, 2]
        right_coordinates = right_xy
        errors = np.linalg.norm(projected_right - right_coordinates, axis=1)
        outlier_mask = ~opencv_inlier_mask
        soft_outlier_mask = (errors <= float(loose_keep_pixel_threshold)) & outlier_mask
        retained_mask = opencv_inlier_mask | soft_outlier_mask
        soft_outlier_original_indices = np.where(soft_outlier_mask)[0].tolist()

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
        model=normalized_model,
        coordinate_space=ransac_coordinate_space,
        input_count=input_count,
        retained_count=len(filtered_left_points),
        dropped_count=input_count - len(filtered_left_points),
        opencv_inlier_count=int(opencv_inlier_mask.sum()),
        opencv_outlier_count=int((~opencv_inlier_mask).sum()),
        retained_soft_outlier_count=len(soft_outlier_original_indices),
        soft_outlier_original_indices=soft_outlier_original_indices,
        retained_soft_outlier_positions=retained_soft_outlier_positions,
        reproj_threshold=threshold,
        confidence=ransac_confidence,
        max_iters=ransac_max_iters,
        loose_keep_pixel_threshold=loose_keep_pixel_threshold,
        matrix=model_matrix.tolist(),
        matrix_type=matrix_type,
        homography_matrix=homography_matrix,
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
    ransac_model: str = DEFAULT_RANSAC_MODEL,
    ransac_coordinate_space: str = "dom_pixel",
    ransac_reproj_threshold: float = DEFAULT_RANSAC_REPROJ_THRESHOLD,
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
        ransac_model=ransac_model,
        ransac_coordinate_space=ransac_coordinate_space,
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
    "DEFAULT_RANSAC_MODEL",
    "DEFAULT_RANSAC_REPROJ_THRESHOLD",
    "SUPPORTED_RANSAC_MODELS",
    "filter_stereo_pair_key_files_with_ransac",
    "filter_stereo_pair_keypoints_with_ransac",
]
