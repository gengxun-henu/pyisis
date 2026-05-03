"""Reusable DOM tile-matching helpers for `image_match.py`.

Author: Geng Xun
Created: 2026-04-24
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import multiprocessing as mp
import os
from pathlib import Path

import cv2
import numpy as np

from .keypoints import Keypoint
from .preprocess import (
    StretchStats,
    ValidPixelStats,
    expand_invalid_mask_for_radius,
    summarize_valid_pixels,
    stretch_to_byte,
)
from .runtime import bootstrap_runtime_environment
from .tiling import TileWindow, generate_tiles, requires_tiling


bootstrap_runtime_environment()

import isis_pybind as ip


DEFAULT_MATCHER_METHOD = "bf"
SUPPORTED_MATCHER_METHODS = ("bf", "flann")
DEFAULT_FLANN_TREES = 5
DEFAULT_FLANN_CHECKS = 50


@dataclass(frozen=True, slots=True)
class TileMatchStats:
    local_start_x: int
    local_start_y: int
    width: int
    height: int
    left_start_x: int
    left_start_y: int
    right_start_x: int
    right_start_y: int
    left_valid_pixel_count: int
    right_valid_pixel_count: int
    left_valid_pixel_ratio: float
    right_valid_pixel_ratio: float
    left_feature_count: int
    right_feature_count: int
    match_count: int
    status: str


@dataclass(frozen=True, slots=True)
class PairedTileWindow:
    local_window: TileWindow
    left_window: TileWindow
    right_window: TileWindow


@dataclass(frozen=True, slots=True)
class TileMatchTask:
    left_dom_path: str
    right_dom_path: str
    band: int
    paired_window: PairedTileWindow
    minimum_value: float | None
    maximum_value: float | None
    lower_percent: float
    upper_percent: float
    invalid_values: tuple[float, ...]
    special_pixel_abs_threshold: float
    min_valid_pixels: int
    valid_pixel_percent_threshold: float
    invalid_pixel_radius: int
    ratio_test: float
    matcher_method: str
    max_features: int | None
    sift_octave_layers: int
    sift_contrast_threshold: float
    sift_edge_threshold: float
    sift_sigma: float


@dataclass(frozen=True, slots=True)
class TileMatchResult:
    stats: TileMatchStats
    left_points: tuple[Keypoint, ...]
    right_points: tuple[Keypoint, ...]


def _normalize_matcher_method(matcher_method: str) -> str:
    resolved_matcher_method = str(matcher_method).strip().lower()
    if resolved_matcher_method not in SUPPORTED_MATCHER_METHODS:
        raise ValueError(
            f"Unsupported matcher_method {matcher_method!r}. Expected one of {SUPPORTED_MATCHER_METHODS}."
        )
    return resolved_matcher_method


def _matcher_diagnostics_for_method(matcher_method: str) -> dict[str, object]:
    resolved_matcher_method = _normalize_matcher_method(matcher_method)
    diagnostics: dict[str, object] = {
        "matcher_method_used": resolved_matcher_method,
    }
    if resolved_matcher_method == "flann":
        diagnostics["flann_index_params"] = {
            "algorithm": "KDTree",
            "trees": DEFAULT_FLANN_TREES,
        }
        diagnostics["flann_search_params"] = {
            "checks": DEFAULT_FLANN_CHECKS,
        }
    return diagnostics


def _create_descriptor_matcher(matcher_method: str):
    resolved_matcher_method = _normalize_matcher_method(matcher_method)
    if resolved_matcher_method == "bf":
        return cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)

    flann_index_params = {
        "algorithm": 1,
        "trees": DEFAULT_FLANN_TREES,
    }
    flann_search_params = {
        "checks": DEFAULT_FLANN_CHECKS,
    }
    return cv2.FlannBasedMatcher(flann_index_params, flann_search_params)


def _full_image_window(image_width: int, image_height: int) -> TileWindow:
    return TileWindow(start_x=0, start_y=0, width=image_width, height=image_height)


def _paired_windows(
    *,
    left_offset_x: int,
    left_offset_y: int,
    right_offset_x: int,
    right_offset_y: int,
    common_width: int,
    common_height: int,
    max_image_dimension: int,
    block_width: int,
    block_height: int,
    overlap_x: int,
    overlap_y: int,
) -> list[PairedTileWindow]:
    if common_width <= 0 or common_height <= 0:
        return []

    if requires_tiling(common_width, common_height, max_dimension=max_image_dimension):
        local_windows = generate_tiles(
            common_width,
            common_height,
            block_width=block_width,
            block_height=block_height,
            overlap_x=overlap_x,
            overlap_y=overlap_y,
        )
    else:
        local_windows = [_full_image_window(common_width, common_height)]

    return [
        PairedTileWindow(
            local_window=local_window,
            left_window=TileWindow(
                start_x=left_offset_x + local_window.start_x,
                start_y=left_offset_y + local_window.start_y,
                width=local_window.width,
                height=local_window.height,
            ),
            right_window=TileWindow(
                start_x=right_offset_x + local_window.start_x,
                start_y=right_offset_y + local_window.start_y,
                width=local_window.width,
                height=local_window.height,
            ),
        )
        for local_window in local_windows
    ]


def _read_cube_window(cube: ip.Cube, window: TileWindow, *, band: int) -> np.ndarray:
    brick = ip.Brick(cube, window.width, window.height, 1)
    # TileWindow uses Python-style 0-based offsets, but ISIS Brick base positions are
    # 1-based sample/line coordinates. Keep this +1 explicit so regressions do not
    # silently shift all extracted pixels by one column/row.
    brick.set_base_position(window.start_x + 1, window.start_y + 1, band)
    cube.read(brick)
    return np.asarray(brick.double_buffer(), dtype=np.float64).reshape((window.height, window.width))


def _stats_from_mask(mask: np.ndarray) -> ValidPixelStats:
    invalid_count = int(mask.sum())
    total = int(mask.size)
    valid_count = total - invalid_count
    return ValidPixelStats(
        valid_pixel_count=valid_count,
        invalid_pixel_count=invalid_count,
        total_pixel_count=total,
        valid_pixel_ratio=0.0 if total <= 0 else valid_count / total,
    )


def _prepare_image_for_sift(
    values: np.ndarray,
    *,
    minimum_value: float | None,
    maximum_value: float | None,
    lower_percent: float,
    upper_percent: float,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    invalid_mask: np.ndarray | None = None,
    invalid_pixel_radius: int = 0,
) -> tuple[np.ndarray, np.ndarray, StretchStats]:
    if invalid_mask is not None:
        resolved_invalid_mask = np.asarray(invalid_mask, dtype=bool)
    else:
        resolved_invalid_mask, _ = summarize_valid_pixels(
            values,
            invalid_values=invalid_values,
            special_pixel_abs_threshold=special_pixel_abs_threshold,
        )
    resolved_invalid_mask = expand_invalid_mask_for_radius(
        resolved_invalid_mask,
        invalid_pixel_radius=invalid_pixel_radius,
    )
    valid_pixel_stats = _stats_from_mask(resolved_invalid_mask)
    if resolved_invalid_mask.all():
        stretched = np.zeros(values.shape, dtype=np.uint8)
        stretch_stats = StretchStats(
            minimum_value=0.0,
            maximum_value=0.0,
            valid_pixel_count=valid_pixel_stats.valid_pixel_count,
            invalid_pixel_count=valid_pixel_stats.invalid_pixel_count,
        )
        sift_mask = np.zeros(values.shape, dtype=np.uint8)
        return stretched, sift_mask, stretch_stats

    stretched, resolved_invalid_mask, stretch_stats = stretch_to_byte(
        values,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        lower_percent=lower_percent,
        upper_percent=upper_percent,
        invalid_values=invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
        invalid_mask=resolved_invalid_mask,
    )
    sift_mask = np.where(resolved_invalid_mask, 0, 255).astype(np.uint8)
    return stretched, sift_mask, stretch_stats


def _build_sift_detector(
    *,
    max_features: int | None,
    octave_layers: int,
    contrast_threshold: float,
    edge_threshold: float,
    sigma: float,
) -> cv2.SIFT:
    sift_kwargs: dict[str, int | float] = {
        "nOctaveLayers": octave_layers,
        "contrastThreshold": contrast_threshold,
        "edgeThreshold": edge_threshold,
        "sigma": sigma,
    }
    if max_features is not None:
        sift_kwargs["nfeatures"] = max_features
    return cv2.SIFT_create(**sift_kwargs)


def _match_tile(
    left_image: np.ndarray,
    right_image: np.ndarray,
    *,
    left_mask: np.ndarray,
    right_mask: np.ndarray,
    ratio_test: float,
    matcher_method: str,
    max_features: int | None,
    sift_octave_layers: int,
    sift_contrast_threshold: float,
    sift_edge_threshold: float,
    sift_sigma: float,
) -> tuple[list[cv2.KeyPoint], list[cv2.KeyPoint], list[cv2.DMatch]]:
    sift = _build_sift_detector(
        max_features=max_features,
        octave_layers=sift_octave_layers,
        contrast_threshold=sift_contrast_threshold,
        edge_threshold=sift_edge_threshold,
        sigma=sift_sigma,
    )
    left_keypoints, left_descriptors = sift.detectAndCompute(left_image, left_mask)
    right_keypoints, right_descriptors = sift.detectAndCompute(right_image, right_mask)

    if not left_keypoints or left_descriptors is None:
        return [], [], []
    if not right_keypoints or right_descriptors is None:
        return left_keypoints, [], []

    matcher = _create_descriptor_matcher(matcher_method)
    raw_matches = matcher.knnMatch(left_descriptors, right_descriptors, k=2)

    filtered_matches: list[cv2.DMatch] = []
    for candidates in raw_matches:
        if len(candidates) < 2:
            continue
        best, alternate = candidates
        if best.distance < ratio_test * alternate.distance:
            filtered_matches.append(best)

    return left_keypoints, right_keypoints, filtered_matches


def _match_tile_from_window_values(
    *,
    left_values: np.ndarray,
    right_values: np.ndarray,
    local_window: TileWindow,
    left_window: TileWindow,
    right_window: TileWindow,
    minimum_value: float | None,
    maximum_value: float | None,
    lower_percent: float,
    upper_percent: float,
    left_invalid_values: tuple[float, ...],
    right_invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    min_valid_pixels: int,
    valid_pixel_percent_threshold: float,
    invalid_pixel_radius: int,
    ratio_test: float,
    matcher_method: str,
    max_features: int | None,
    sift_octave_layers: int,
    sift_contrast_threshold: float,
    sift_edge_threshold: float,
    sift_sigma: float,
) -> TileMatchResult:
    left_invalid_mask, left_valid_pixel_stats = summarize_valid_pixels(
        left_values,
        invalid_values=left_invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
    )
    right_invalid_mask, right_valid_pixel_stats = summarize_valid_pixels(
        right_values,
        invalid_values=right_invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
    )

    left_invalid_mask = expand_invalid_mask_for_radius(
        left_invalid_mask,
        invalid_pixel_radius=invalid_pixel_radius,
    )
    right_invalid_mask = expand_invalid_mask_for_radius(
        right_invalid_mask,
        invalid_pixel_radius=invalid_pixel_radius,
    )
    left_valid_pixel_stats = _stats_from_mask(left_invalid_mask)
    right_valid_pixel_stats = _stats_from_mask(right_invalid_mask)

    if (
        left_valid_pixel_stats.valid_pixel_ratio < valid_pixel_percent_threshold
        or right_valid_pixel_stats.valid_pixel_ratio < valid_pixel_percent_threshold
    ):
        return TileMatchResult(
            stats=TileMatchStats(
                local_start_x=local_window.start_x,
                local_start_y=local_window.start_y,
                width=local_window.width,
                height=local_window.height,
                left_start_x=left_window.start_x,
                left_start_y=left_window.start_y,
                right_start_x=right_window.start_x,
                right_start_y=right_window.start_y,
                left_valid_pixel_count=left_valid_pixel_stats.valid_pixel_count,
                right_valid_pixel_count=right_valid_pixel_stats.valid_pixel_count,
                left_valid_pixel_ratio=left_valid_pixel_stats.valid_pixel_ratio,
                right_valid_pixel_ratio=right_valid_pixel_stats.valid_pixel_ratio,
                left_feature_count=0,
                right_feature_count=0,
                match_count=0,
                status="skipped_valid_pixel_ratio_below_threshold",
            ),
            left_points=(),
            right_points=(),
        )

    left_image, left_mask, left_stats = _prepare_image_for_sift(
        left_values,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        lower_percent=lower_percent,
        upper_percent=upper_percent,
        invalid_values=left_invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
        invalid_mask=left_invalid_mask,
        invalid_pixel_radius=0,
    )
    right_image, right_mask, right_stats = _prepare_image_for_sift(
        right_values,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        lower_percent=lower_percent,
        upper_percent=upper_percent,
        invalid_values=right_invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
        invalid_mask=right_invalid_mask,
        invalid_pixel_radius=0,
    )

    if left_stats.valid_pixel_count < min_valid_pixels or right_stats.valid_pixel_count < min_valid_pixels:
        return TileMatchResult(
            stats=TileMatchStats(
                local_start_x=local_window.start_x,
                local_start_y=local_window.start_y,
                width=local_window.width,
                height=local_window.height,
                left_start_x=left_window.start_x,
                left_start_y=left_window.start_y,
                right_start_x=right_window.start_x,
                right_start_y=right_window.start_y,
                left_valid_pixel_count=left_stats.valid_pixel_count,
                right_valid_pixel_count=right_stats.valid_pixel_count,
                left_valid_pixel_ratio=left_stats.valid_pixel_ratio,
                right_valid_pixel_ratio=right_stats.valid_pixel_ratio,
                left_feature_count=0,
                right_feature_count=0,
                match_count=0,
                status="skipped_insufficient_valid_pixels",
            ),
            left_points=(),
            right_points=(),
        )

    left_keypoints, right_keypoints, filtered_matches = _match_tile(
        left_image,
        right_image,
        left_mask=left_mask,
        right_mask=right_mask,
        ratio_test=ratio_test,
        matcher_method=matcher_method,
        max_features=max_features,
        sift_octave_layers=sift_octave_layers,
        sift_contrast_threshold=sift_contrast_threshold,
        sift_edge_threshold=sift_edge_threshold,
        sift_sigma=sift_sigma,
    )

    if not left_keypoints or not right_keypoints:
        return TileMatchResult(
            stats=TileMatchStats(
                local_start_x=local_window.start_x,
                local_start_y=local_window.start_y,
                width=local_window.width,
                height=local_window.height,
                left_start_x=left_window.start_x,
                left_start_y=left_window.start_y,
                right_start_x=right_window.start_x,
                right_start_y=right_window.start_y,
                left_valid_pixel_count=left_stats.valid_pixel_count,
                right_valid_pixel_count=right_stats.valid_pixel_count,
                left_valid_pixel_ratio=left_stats.valid_pixel_ratio,
                right_valid_pixel_ratio=right_stats.valid_pixel_ratio,
                left_feature_count=len(left_keypoints),
                right_feature_count=len(right_keypoints),
                match_count=0,
                status="skipped_no_features",
            ),
            left_points=(),
            right_points=(),
        )

    if not filtered_matches:
        return TileMatchResult(
            stats=TileMatchStats(
                local_start_x=local_window.start_x,
                local_start_y=local_window.start_y,
                width=local_window.width,
                height=local_window.height,
                left_start_x=left_window.start_x,
                left_start_y=left_window.start_y,
                right_start_x=right_window.start_x,
                right_start_y=right_window.start_y,
                left_valid_pixel_count=left_stats.valid_pixel_count,
                right_valid_pixel_count=right_stats.valid_pixel_count,
                left_valid_pixel_ratio=left_stats.valid_pixel_ratio,
                right_valid_pixel_ratio=right_stats.valid_pixel_ratio,
                left_feature_count=len(left_keypoints),
                right_feature_count=len(right_keypoints),
                match_count=0,
                status="skipped_no_matches",
            ),
            left_points=(),
            right_points=(),
        )

    matched_left_points = tuple(
        _keypoint_to_isis_coordinates(left_keypoints[match.queryIdx], left_window)
        for match in filtered_matches
    )
    matched_right_points = tuple(
        _keypoint_to_isis_coordinates(right_keypoints[match.trainIdx], right_window)
        for match in filtered_matches
    )
    return TileMatchResult(
        stats=TileMatchStats(
            local_start_x=local_window.start_x,
            local_start_y=local_window.start_y,
            width=local_window.width,
            height=local_window.height,
            left_start_x=left_window.start_x,
            left_start_y=left_window.start_y,
            right_start_x=right_window.start_x,
            right_start_y=right_window.start_y,
            left_valid_pixel_count=left_stats.valid_pixel_count,
            right_valid_pixel_count=right_stats.valid_pixel_count,
            left_valid_pixel_ratio=left_stats.valid_pixel_ratio,
            right_valid_pixel_ratio=right_stats.valid_pixel_ratio,
            left_feature_count=len(left_keypoints),
            right_feature_count=len(right_keypoints),
            match_count=len(filtered_matches),
            status="matched",
        ),
        left_points=matched_left_points,
        right_points=matched_right_points,
    )


def _build_tile_match_tasks(
    windows: list[PairedTileWindow],
    *,
    left_dom_path: str | Path,
    right_dom_path: str | Path,
    band: int,
    minimum_value: float | None,
    maximum_value: float | None,
    lower_percent: float,
    upper_percent: float,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    min_valid_pixels: int,
    valid_pixel_percent_threshold: float,
    invalid_pixel_radius: int,
    ratio_test: float,
    matcher_method: str,
    max_features: int | None,
    sift_octave_layers: int,
    sift_contrast_threshold: float,
    sift_edge_threshold: float,
    sift_sigma: float,
) -> list[TileMatchTask]:
    return [
        TileMatchTask(
            left_dom_path=str(left_dom_path),
            right_dom_path=str(right_dom_path),
            band=band,
            paired_window=paired_window,
            minimum_value=minimum_value,
            maximum_value=maximum_value,
            lower_percent=lower_percent,
            upper_percent=upper_percent,
            invalid_values=invalid_values,
            special_pixel_abs_threshold=special_pixel_abs_threshold,
            min_valid_pixels=min_valid_pixels,
            valid_pixel_percent_threshold=valid_pixel_percent_threshold,
            invalid_pixel_radius=invalid_pixel_radius,
            ratio_test=ratio_test,
            matcher_method=_normalize_matcher_method(matcher_method),
            max_features=max_features,
            sift_octave_layers=sift_octave_layers,
            sift_contrast_threshold=sift_contrast_threshold,
            sift_edge_threshold=sift_edge_threshold,
            sift_sigma=sift_sigma,
        )
        for paired_window in windows
    ]


def _match_tile_task_in_open_cubes(
    task: TileMatchTask,
    *,
    left_cube: ip.Cube,
    right_cube: ip.Cube,
    left_invalid_values: tuple[float, ...],
    right_invalid_values: tuple[float, ...],
) -> TileMatchResult:
    left_values = _read_cube_window(left_cube, task.paired_window.left_window, band=task.band)
    right_values = _read_cube_window(right_cube, task.paired_window.right_window, band=task.band)

    return _match_tile_from_window_values(
        left_values=left_values,
        right_values=right_values,
        local_window=task.paired_window.local_window,
        left_window=task.paired_window.left_window,
        right_window=task.paired_window.right_window,
        minimum_value=task.minimum_value,
        maximum_value=task.maximum_value,
        lower_percent=task.lower_percent,
        upper_percent=task.upper_percent,
        left_invalid_values=left_invalid_values,
        right_invalid_values=right_invalid_values,
        special_pixel_abs_threshold=task.special_pixel_abs_threshold,
        min_valid_pixels=task.min_valid_pixels,
        valid_pixel_percent_threshold=task.valid_pixel_percent_threshold,
        invalid_pixel_radius=task.invalid_pixel_radius,
        ratio_test=task.ratio_test,
        matcher_method=task.matcher_method,
        max_features=task.max_features,
        sift_octave_layers=task.sift_octave_layers,
        sift_contrast_threshold=task.sift_contrast_threshold,
        sift_edge_threshold=task.sift_edge_threshold,
        sift_sigma=task.sift_sigma,
    )


def _match_paired_window_batch_worker(tasks: tuple[TileMatchTask, ...]) -> tuple[TileMatchResult, ...]:
    if not tasks:
        return ()

    first_task = tasks[0]
    left_cube = ip.Cube()
    right_cube = ip.Cube()
    left_cube.open(first_task.left_dom_path, "r")
    right_cube.open(first_task.right_dom_path, "r")
    try:
        left_invalid_values = _resolved_invalid_values_for_cube(left_cube, first_task.invalid_values)
        right_invalid_values = _resolved_invalid_values_for_cube(right_cube, first_task.invalid_values)
        return tuple(
            _match_tile_task_in_open_cubes(
                task,
                left_cube=left_cube,
                right_cube=right_cube,
                left_invalid_values=left_invalid_values,
                right_invalid_values=right_invalid_values,
            )
            for task in tasks
        )
    finally:
        if left_cube.is_open():
            left_cube.close()
        if right_cube.is_open():
            right_cube.close()


def _match_single_paired_window_worker(task: TileMatchTask) -> TileMatchResult:
    return _match_paired_window_batch_worker((task,))[0]


def _chunk_tile_match_tasks(tasks: list[TileMatchTask], max_workers: int) -> list[tuple[int, tuple[TileMatchTask, ...]]]:
    if not tasks:
        return []
    effective_workers = max(1, min(max_workers, len(tasks)))
    chunk_size = (len(tasks) + effective_workers - 1) // effective_workers
    return [
        (start_index, tuple(tasks[start_index : start_index + chunk_size]))
        for start_index in range(0, len(tasks), chunk_size)
    ]


def _tile_match_process_pool_context() -> mp.context.BaseContext:
    preferred_context = "fork" if os.name == "posix" else "spawn"
    return mp.get_context(preferred_context)


def _run_parallel_tile_match_tasks(
    tasks: list[TileMatchTask],
    *,
    max_workers: int,
    progress_callback: Callable[[], None] | None = None,
) -> list[TileMatchResult]:
    if not tasks:
        return []
    task_chunks = _chunk_tile_match_tasks(tasks, max_workers=max_workers)
    with ProcessPoolExecutor(max_workers=max_workers, mp_context=_tile_match_process_pool_context()) as executor:
        futures = {
            executor.submit(_match_paired_window_batch_worker, task_chunk): start_index
            for start_index, task_chunk in task_chunks
        }
        ordered_results: list[TileMatchResult | None] = [None] * len(tasks)
        for future in as_completed(futures):
            start_index = futures[future]
            for offset, result in enumerate(future.result()):
                ordered_results[start_index + offset] = result
                if progress_callback is not None:
                    progress_callback()
        return [result for result in ordered_results if result is not None]


def _run_serial_tile_match_tasks(
    windows: list[PairedTileWindow],
    *,
    left_cube: ip.Cube,
    right_cube: ip.Cube,
    band: int,
    minimum_value: float | None,
    maximum_value: float | None,
    lower_percent: float,
    upper_percent: float,
    left_invalid_values: tuple[float, ...],
    right_invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    min_valid_pixels: int,
    valid_pixel_percent_threshold: float,
    invalid_pixel_radius: int,
    ratio_test: float,
    matcher_method: str,
    max_features: int | None,
    sift_octave_layers: int,
    sift_contrast_threshold: float,
    sift_edge_threshold: float,
    sift_sigma: float,
    progress_callback: Callable[[], None] | None = None,
) -> list[TileMatchResult]:
    tile_results: list[TileMatchResult] = []
    for paired_window in windows:
        left_values = _read_cube_window(left_cube, paired_window.left_window, band=band)
        right_values = _read_cube_window(right_cube, paired_window.right_window, band=band)
        tile_results.append(
            _match_tile_from_window_values(
                left_values=left_values,
                right_values=right_values,
                local_window=paired_window.local_window,
                left_window=paired_window.left_window,
                right_window=paired_window.right_window,
                minimum_value=minimum_value,
                maximum_value=maximum_value,
                lower_percent=lower_percent,
                upper_percent=upper_percent,
                left_invalid_values=left_invalid_values,
                right_invalid_values=right_invalid_values,
                special_pixel_abs_threshold=special_pixel_abs_threshold,
                min_valid_pixels=min_valid_pixels,
                valid_pixel_percent_threshold=valid_pixel_percent_threshold,
                invalid_pixel_radius=invalid_pixel_radius,
                ratio_test=ratio_test,
                matcher_method=matcher_method,
                max_features=max_features,
                sift_octave_layers=sift_octave_layers,
                sift_contrast_threshold=sift_contrast_threshold,
                sift_edge_threshold=sift_edge_threshold,
                sift_sigma=sift_sigma,
            )
        )
        if progress_callback is not None:
            progress_callback()
    return tile_results


def _keypoint_to_isis_coordinates(keypoint: cv2.KeyPoint, window: TileWindow) -> Keypoint:
    # OpenCV keypoint.pt is expressed in tile-local 0-based image coordinates, while
    # .key files and downstream ISIS geometry use 1-based sample/line coordinates in
    # the full DOM image. The +1 here is therefore required, not cosmetic.
    return Keypoint(
        sample=window.start_x + float(keypoint.pt[0]) + 1.0,
        line=window.start_y + float(keypoint.pt[1]) + 1.0,
    )


def _resolved_invalid_values_for_cube(cube: ip.Cube, invalid_values: tuple[float, ...]) -> tuple[float, ...]:
    resolved_invalid_values = list(invalid_values)
    zero_invalid_pixel_types = {
        getattr(ip.PixelType, "UnsignedByte", None),
        getattr(ip.PixelType, "SignedByte", None),
    }
    if cube.pixel_type() in zero_invalid_pixel_types and 0.0 not in resolved_invalid_values:
        resolved_invalid_values.append(0.0)
    return tuple(resolved_invalid_values)


__all__ = [
    "DEFAULT_FLANN_CHECKS",
    "DEFAULT_FLANN_TREES",
    "DEFAULT_MATCHER_METHOD",
    "PairedTileWindow",
    "SUPPORTED_MATCHER_METHODS",
    "TileMatchResult",
    "TileMatchStats",
    "TileMatchTask",
    "_build_sift_detector",
    "_build_tile_match_tasks",
    "_create_descriptor_matcher",
    "_full_image_window",
    "_keypoint_to_isis_coordinates",
    "_matcher_diagnostics_for_method",
    "_match_tile",
    "_match_tile_from_window_values",
    "_normalize_matcher_method",
    "_paired_windows",
    "_prepare_image_for_sift",
    "_read_cube_window",
    "_resolved_invalid_values_for_cube",
    "_run_parallel_tile_match_tasks",
    "_run_serial_tile_match_tasks",
    "_tile_match_process_pool_context",
]
