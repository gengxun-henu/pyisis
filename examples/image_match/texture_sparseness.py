"""Tile-level texture sparseness metrics for adaptive matcher routing.

Author: Geng Xun
Created: 2026-05-18
Updated: 2026-05-18  Geng Xun added tile-level texture sparseness, image-level P90
    aggregation, and pair weak-side aggregation with a lightweight 16-level GLCM
    implementation, SIFT density, and gradient-magnitude sub-scores.

The semantic convention is "0 = texture-rich, 1 = texture-sparse" so a higher
sparseness score means a harder image for descriptor-based matching. This is
deliberately the opposite polarity of the legacy ``real_texture_score`` exposed
by :mod:`adaptive_routing`, which keeps "0 = poor, 1 = rich" semantics. Callers
that mix the two should keep them clearly named.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import math

import cv2
import numpy as np


DEFAULT_TILE_SIZE = 256
DEFAULT_TILE_STEP = 128
DEFAULT_MIN_VALID_PIXEL_RATIO = 0.30
DEFAULT_GLCM_LEVELS = 16
DEFAULT_GLCM_DISTANCE = 1
DEFAULT_GLCM_ANGLE_RADIANS = 0.0
DEFAULT_IMAGE_AGGREGATION_QUANTILE = 0.90

# Sub-score weights for combining SIFT density, gradient magnitude, and GLCM
# into the tile-level sparseness main score. The plan fixes these as
# ``SIFT 0.45 + gradient 0.30 + GLCM 0.25`` to keep the initial release stable
# and explainable.
DEFAULT_SIFT_WEIGHT = 0.45
DEFAULT_GRADIENT_WEIGHT = 0.30
DEFAULT_GLCM_WEIGHT = 0.25

# Empirical thresholds used to map raw tile metrics to [0, 1] sparseness
# sub-scores. They mirror the order-of-magnitude defaults already used in the
# legacy ``compute_real_image_texture_probe`` mapping so behaviour stays
# consistent with the existing real-texture probe.
_SIFT_DENSITY_RICH_THRESHOLD = 0.002
_GRADIENT_RICH_THRESHOLD = 64.0
_GLCM_CONTRAST_RICH_THRESHOLD = 60.0


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))


@dataclass(frozen=True, slots=True)
class TileSparsenessMetrics:
    """Per-tile texture metrics and the derived sparseness score."""

    start_x: int
    start_y: int
    width: int
    height: int
    valid_pixel_count: int
    valid_pixel_ratio: float
    sift_keypoint_count: int
    sift_keypoint_density: float
    mean_gradient: float
    glcm_contrast: float
    glcm_energy: float
    sift_sparseness_subscore: float
    gradient_sparseness_subscore: float
    glcm_sparseness_subscore: float
    texture_sparseness: float


@dataclass(frozen=True, slots=True)
class ImageSparsenessSummary:
    """Image-level aggregation of tile sparseness."""

    tile_total_count: int
    tile_valid_count: int
    tile_size: int
    tile_step: int
    min_valid_pixel_ratio: float
    aggregation_quantile: float
    image_texture_sparseness: float | None
    sparseness_quantiles: dict[str, float | None] = field(default_factory=dict)
    tile_metrics: tuple[TileSparsenessMetrics, ...] = ()


@dataclass(frozen=True, slots=True)
class PairSparsenessSummary:
    """Pair-level weak-side aggregation of two image sparseness summaries."""

    left: ImageSparsenessSummary
    right: ImageSparsenessSummary
    pair_texture_sparseness: float | None
    weaker_side: str | None


def _normalize_image_to_uint8(
    image_values: Any,
    invalid_mask: Any | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Unify normalization so tile-level metrics are comparable across tiles.

    Returns the full-image uint8 normalized array plus the boolean valid-pixel
    mask. Normalization uses a per-image 1-99 percentile stretch so dim tiles
    are not crushed to zero just because the overall image has high outliers.
    """

    values = np.asarray(image_values, dtype=np.float32)
    if values.ndim != 2:
        raise ValueError("image_values must be a 2-D grayscale array.")
    finite_mask = np.isfinite(values)
    if invalid_mask is not None:
        invalid_array = np.asarray(invalid_mask, dtype=bool)
        if invalid_array.shape != values.shape:
            raise ValueError("invalid_mask shape must match image_values shape.")
        finite_mask &= ~invalid_array

    valid_values = values[finite_mask]
    if valid_values.size == 0:
        return np.zeros(values.shape, dtype=np.uint8), finite_mask

    lower, upper = np.percentile(valid_values, [1.0, 99.0])
    lower_f = float(lower)
    upper_f = float(upper)
    if not math.isfinite(lower_f) or not math.isfinite(upper_f) or upper_f <= lower_f:
        lower_f = float(valid_values.min())
        upper_f = float(valid_values.max())
    if upper_f <= lower_f:
        normalized = np.zeros(values.shape, dtype=np.uint8)
    else:
        scaled = (np.clip(values, lower_f, upper_f) - lower_f) * (255.0 / (upper_f - lower_f))
        normalized = np.where(finite_mask, scaled, 0.0).astype(np.uint8)
    return normalized, finite_mask


def generate_tile_windows(
    image_height: int,
    image_width: int,
    *,
    tile_size: int = DEFAULT_TILE_SIZE,
    tile_step: int = DEFAULT_TILE_STEP,
) -> list[tuple[int, int, int, int]]:
    """Generate ``(start_y, start_x, height, width)`` windows over an image.

    The layout is deliberately permissive about partial tiles at the right and
    bottom edges so small previews still produce at least one tile. Step size
    must be positive and not larger than the tile size.
    """

    if image_height <= 0 or image_width <= 0:
        raise ValueError("image dimensions must be positive.")
    if tile_size <= 0:
        raise ValueError("tile_size must be positive.")
    if tile_step <= 0:
        raise ValueError("tile_step must be positive.")
    if tile_step > tile_size:
        raise ValueError("tile_step must be <= tile_size.")

    def _axis_starts(size: int) -> list[int]:
        if size <= tile_size:
            return [0]
        starts = list(range(0, size - tile_size + 1, tile_step))
        if starts[-1] + tile_size < size:
            starts.append(size - tile_size)
        return starts

    y_starts = _axis_starts(image_height)
    x_starts = _axis_starts(image_width)

    windows: list[tuple[int, int, int, int]] = []
    for start_y in y_starts:
        height = min(tile_size, image_height - start_y)
        for start_x in x_starts:
            width = min(tile_size, image_width - start_x)
            windows.append((start_y, start_x, height, width))
    return windows


def compute_lightweight_glcm(
    tile_values: np.ndarray,
    *,
    valid_mask: np.ndarray | None = None,
    levels: int = DEFAULT_GLCM_LEVELS,
    distance: int = DEFAULT_GLCM_DISTANCE,
    angle_radians: float = DEFAULT_GLCM_ANGLE_RADIANS,
) -> tuple[float, float]:
    """Compute ``(contrast, energy)`` for one distance/angle without scikit-image.

    The tile is quantized into ``levels`` bins (default 16). Pixel pairs whose
    head or tail falls in an invalid cell are dropped before accumulation. The
    initial release implements one distance and one angle (default 0°). The
    contract is small on purpose so callers can later average across angles
    without changing the public API.
    """

    if tile_values.ndim != 2:
        raise ValueError("tile_values must be a 2-D array.")
    if levels < 2:
        raise ValueError("levels must be >= 2.")
    if distance < 1:
        raise ValueError("distance must be >= 1.")

    array = np.asarray(tile_values, dtype=np.float32)
    if valid_mask is None:
        resolved_valid = np.ones(array.shape, dtype=bool)
    else:
        resolved_valid = np.asarray(valid_mask, dtype=bool)
        if resolved_valid.shape != array.shape:
            raise ValueError("valid_mask shape must match tile_values shape.")

    if not resolved_valid.any():
        return 0.0, 1.0

    quantized = np.minimum(
        ((array.astype(np.float32) / 256.0) * levels).astype(np.int32),
        levels - 1,
    )
    quantized = np.maximum(quantized, 0)
    quantized = np.where(resolved_valid, quantized, -1)

    delta_x = int(round(math.cos(float(angle_radians)) * distance))
    delta_y = int(round(-math.sin(float(angle_radians)) * distance))
    height, width = quantized.shape

    src_y_start = max(0, -delta_y)
    src_y_end = min(height, height - delta_y)
    src_x_start = max(0, -delta_x)
    src_x_end = min(width, width - delta_x)
    if src_y_start >= src_y_end or src_x_start >= src_x_end:
        return 0.0, 1.0

    source = quantized[src_y_start:src_y_end, src_x_start:src_x_end]
    target = quantized[src_y_start + delta_y : src_y_end + delta_y,
                       src_x_start + delta_x : src_x_end + delta_x]

    pair_mask = (source >= 0) & (target >= 0)
    if not pair_mask.any():
        return 0.0, 1.0

    head = source[pair_mask].astype(np.int64)
    tail = target[pair_mask].astype(np.int64)
    flat_index = head * levels + tail
    counts = np.bincount(flat_index, minlength=levels * levels).reshape(levels, levels)
    total = counts.sum()
    if total <= 0:
        return 0.0, 1.0

    probabilities = counts.astype(np.float64) / float(total)
    indices = np.arange(levels)
    diff_squared = (indices[:, None] - indices[None, :]) ** 2
    contrast = float((probabilities * diff_squared).sum())
    energy = float((probabilities ** 2).sum())
    return contrast, energy


def _compute_tile_metrics(
    normalized: np.ndarray,
    valid_mask: np.ndarray,
    *,
    sift_detector: Any,
    start_y: int,
    start_x: int,
    height: int,
    width: int,
    min_valid_pixel_ratio: float,
    glcm_levels: int,
    glcm_distance: int,
    glcm_angle_radians: float,
) -> TileSparsenessMetrics | None:
    tile_values = normalized[start_y : start_y + height, start_x : start_x + width]
    tile_valid = valid_mask[start_y : start_y + height, start_x : start_x + width]
    total = int(tile_values.size)
    valid_count = int(tile_valid.sum())
    valid_ratio = 0.0 if total <= 0 else valid_count / total
    if valid_ratio < float(min_valid_pixel_ratio):
        return None

    sift_mask = np.where(tile_valid, 255, 0).astype(np.uint8)
    keypoints = sift_detector.detect(tile_values, sift_mask)
    keypoint_count = 0 if keypoints is None else len(keypoints)
    keypoint_density = 0.0 if valid_count <= 0 else keypoint_count / valid_count

    sobel_x = cv2.Sobel(tile_values, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(tile_values, cv2.CV_32F, 0, 1, ksize=3)
    gradient_magnitude = cv2.magnitude(sobel_x, sobel_y)
    mean_gradient = float(gradient_magnitude[tile_valid].mean()) if valid_count > 0 else 0.0

    contrast, energy = compute_lightweight_glcm(
        tile_values,
        valid_mask=tile_valid,
        levels=glcm_levels,
        distance=glcm_distance,
        angle_radians=glcm_angle_radians,
    )

    sift_subscore = _clamp(1.0 - (keypoint_density / _SIFT_DENSITY_RICH_THRESHOLD))
    gradient_subscore = _clamp(1.0 - (mean_gradient / _GRADIENT_RICH_THRESHOLD))
    contrast_component = _clamp(1.0 - (contrast / _GLCM_CONTRAST_RICH_THRESHOLD))
    energy_component = _clamp(float(energy))
    glcm_subscore = _clamp(0.5 * contrast_component + 0.5 * energy_component)

    sparseness = _clamp(
        DEFAULT_SIFT_WEIGHT * sift_subscore
        + DEFAULT_GRADIENT_WEIGHT * gradient_subscore
        + DEFAULT_GLCM_WEIGHT * glcm_subscore
    )

    return TileSparsenessMetrics(
        start_x=int(start_x),
        start_y=int(start_y),
        width=int(width),
        height=int(height),
        valid_pixel_count=valid_count,
        valid_pixel_ratio=valid_ratio,
        sift_keypoint_count=int(keypoint_count),
        sift_keypoint_density=float(keypoint_density),
        mean_gradient=mean_gradient,
        glcm_contrast=contrast,
        glcm_energy=energy,
        sift_sparseness_subscore=sift_subscore,
        gradient_sparseness_subscore=gradient_subscore,
        glcm_sparseness_subscore=glcm_subscore,
        texture_sparseness=sparseness,
    )


def _interpolated_quantile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("values must not be empty.")
    if len(values) == 1:
        return float(values[0])
    sorted_values = sorted(values)
    clamped = _clamp(quantile)
    position = clamped * (len(sorted_values) - 1)
    lower_index = int(math.floor(position))
    upper_index = int(math.ceil(position))
    if lower_index == upper_index:
        return float(sorted_values[lower_index])
    fraction = position - lower_index
    return float(sorted_values[lower_index] + (sorted_values[upper_index] - sorted_values[lower_index]) * fraction)


def compute_image_texture_sparseness(
    image_values: Any,
    *,
    invalid_mask: Any | None = None,
    tile_size: int = DEFAULT_TILE_SIZE,
    tile_step: int = DEFAULT_TILE_STEP,
    min_valid_pixel_ratio: float = DEFAULT_MIN_VALID_PIXEL_RATIO,
    aggregation_quantile: float = DEFAULT_IMAGE_AGGREGATION_QUANTILE,
    glcm_levels: int = DEFAULT_GLCM_LEVELS,
    glcm_distance: int = DEFAULT_GLCM_DISTANCE,
    glcm_angle_radians: float = DEFAULT_GLCM_ANGLE_RADIANS,
    sift_max_features: int | None = 500,
    sift_contrast_threshold: float = 0.04,
    keep_tile_metrics: bool = True,
) -> ImageSparsenessSummary:
    """Tile the image, compute per-tile sparseness, and aggregate to image level."""

    normalized, valid_mask = _normalize_image_to_uint8(image_values, invalid_mask=invalid_mask)
    image_height, image_width = normalized.shape
    windows = generate_tile_windows(
        image_height,
        image_width,
        tile_size=tile_size,
        tile_step=tile_step,
    )

    sift_kwargs: dict[str, int | float] = {"contrastThreshold": float(sift_contrast_threshold)}
    if sift_max_features is not None:
        sift_kwargs["nfeatures"] = int(sift_max_features)
    sift_detector = cv2.SIFT_create(**sift_kwargs)

    tile_metrics: list[TileSparsenessMetrics] = []
    for start_y, start_x, height, width in windows:
        metrics = _compute_tile_metrics(
            normalized,
            valid_mask,
            sift_detector=sift_detector,
            start_y=start_y,
            start_x=start_x,
            height=height,
            width=width,
            min_valid_pixel_ratio=min_valid_pixel_ratio,
            glcm_levels=glcm_levels,
            glcm_distance=glcm_distance,
            glcm_angle_radians=glcm_angle_radians,
        )
        if metrics is not None:
            tile_metrics.append(metrics)

    if tile_metrics:
        sparseness_values = [metric.texture_sparseness for metric in tile_metrics]
        image_sparseness = _interpolated_quantile(sparseness_values, aggregation_quantile)
        sparseness_quantiles = {
            "p10": _interpolated_quantile(sparseness_values, 0.10),
            "p50": _interpolated_quantile(sparseness_values, 0.50),
            "p90": _interpolated_quantile(sparseness_values, 0.90),
            "max": max(sparseness_values),
        }
    else:
        image_sparseness = None
        sparseness_quantiles = {"p10": None, "p50": None, "p90": None, "max": None}

    return ImageSparsenessSummary(
        tile_total_count=len(windows),
        tile_valid_count=len(tile_metrics),
        tile_size=int(tile_size),
        tile_step=int(tile_step),
        min_valid_pixel_ratio=float(min_valid_pixel_ratio),
        aggregation_quantile=float(aggregation_quantile),
        image_texture_sparseness=image_sparseness,
        sparseness_quantiles=sparseness_quantiles,
        tile_metrics=tuple(tile_metrics) if keep_tile_metrics else (),
    )


def aggregate_pair_texture_sparseness(
    left: ImageSparsenessSummary,
    right: ImageSparsenessSummary,
) -> PairSparsenessSummary:
    """Combine two image summaries into a pair-level weak-side sparseness score."""

    left_value = left.image_texture_sparseness
    right_value = right.image_texture_sparseness
    if left_value is None and right_value is None:
        pair_value: float | None = None
        weaker_side: str | None = None
    elif left_value is None:
        pair_value = float(right_value) if right_value is not None else None
        weaker_side = "right"
    elif right_value is None:
        pair_value = float(left_value)
        weaker_side = "left"
    else:
        if float(left_value) >= float(right_value):
            pair_value = float(left_value)
            weaker_side = "left"
        else:
            pair_value = float(right_value)
            weaker_side = "right"
    return PairSparsenessSummary(
        left=left,
        right=right,
        pair_texture_sparseness=pair_value,
        weaker_side=weaker_side,
    )


def image_summary_to_diagnostic_dict(summary: ImageSparsenessSummary) -> dict[str, Any]:
    """Return a JSON-serializable diagnostic view of an image summary."""

    payload = asdict(summary)
    payload["tile_metrics"] = [asdict(metric) for metric in summary.tile_metrics]
    return payload


def pair_summary_to_diagnostic_dict(summary: PairSparsenessSummary) -> dict[str, Any]:
    """Return a JSON-serializable diagnostic view of a pair summary."""

    return {
        "left_image": image_summary_to_diagnostic_dict(summary.left),
        "right_image": image_summary_to_diagnostic_dict(summary.right),
        "pair_texture_sparseness": summary.pair_texture_sparseness,
        "weaker_side": summary.weaker_side,
    }


__all__ = [
    "DEFAULT_GLCM_ANGLE_RADIANS",
    "DEFAULT_GLCM_DISTANCE",
    "DEFAULT_GLCM_LEVELS",
    "DEFAULT_GLCM_WEIGHT",
    "DEFAULT_GRADIENT_WEIGHT",
    "DEFAULT_IMAGE_AGGREGATION_QUANTILE",
    "DEFAULT_MIN_VALID_PIXEL_RATIO",
    "DEFAULT_SIFT_WEIGHT",
    "DEFAULT_TILE_SIZE",
    "DEFAULT_TILE_STEP",
    "ImageSparsenessSummary",
    "PairSparsenessSummary",
    "TileSparsenessMetrics",
    "aggregate_pair_texture_sparseness",
    "compute_image_texture_sparseness",
    "compute_lightweight_glcm",
    "generate_tile_windows",
    "image_summary_to_diagnostic_dict",
    "pair_summary_to_diagnostic_dict",
]
