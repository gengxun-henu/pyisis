"""用于 DOM 匹配的灰度值预处理辅助函数。

Gray-value preprocessing helpers for DOM matching.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True, slots=True)
class ValidPixelStats:
    valid_pixel_count: int
    invalid_pixel_count: int
    total_pixel_count: int
    valid_pixel_ratio: float


@dataclass(frozen=True, slots=True)
class StretchStats:
    minimum_value: float
    maximum_value: float
    valid_pixel_count: int
    invalid_pixel_count: int

    @property
    def total_pixel_count(self) -> int:
        return self.valid_pixel_count + self.invalid_pixel_count

    @property
    def valid_pixel_ratio(self) -> float:
        if self.total_pixel_count <= 0:
            return 0.0
        return float(self.valid_pixel_count) / float(self.total_pixel_count)


def validate_invalid_pixel_radius(radius: int) -> int:
    resolved_radius = int(radius)
    if not (0 <= resolved_radius <= 100):
        raise ValueError("invalid_pixel_radius must be within [0, 100].")
    return resolved_radius


def build_invalid_mask(
    values,
    *,
    invalid_values: tuple[float, ...] = (),
    special_pixel_abs_threshold: float = 1.0e300,
) -> np.ndarray:
    """构建无效像素掩膜，覆盖非有限值、极端特殊像素和调用方指定的哨兵值。

    Build a mask for non-finite pixels, extreme special pixels, and caller-provided sentinels.
    """
    array = np.asarray(values)
    float_array = array.astype(np.float64, copy=False)
    mask = ~np.isfinite(float_array)

    if special_pixel_abs_threshold > 0.0:
        mask |= np.abs(float_array) >= special_pixel_abs_threshold

    for invalid_value in invalid_values:
        mask |= array == invalid_value

    return mask


def summarize_valid_pixels(
    values,
    *,
    invalid_values: tuple[float, ...] = (),
    special_pixel_abs_threshold: float = 1.0e300,
    invalid_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, ValidPixelStats]:
    """Return the invalid-pixel mask plus valid/invalid count and ratio summary."""
    array = np.asarray(values)
    resolved_invalid_mask = (
        build_invalid_mask(
            array,
            invalid_values=invalid_values,
            special_pixel_abs_threshold=special_pixel_abs_threshold,
        )
        if invalid_mask is None
        else np.asarray(invalid_mask, dtype=bool)
    )
    total_pixel_count = int(resolved_invalid_mask.size)
    invalid_pixel_count = int(resolved_invalid_mask.sum())
    valid_pixel_count = total_pixel_count - invalid_pixel_count
    valid_pixel_ratio = 0.0 if total_pixel_count <= 0 else float(valid_pixel_count) / float(total_pixel_count)
    return resolved_invalid_mask, ValidPixelStats(
        valid_pixel_count=valid_pixel_count,
        invalid_pixel_count=invalid_pixel_count,
        total_pixel_count=total_pixel_count,
        valid_pixel_ratio=valid_pixel_ratio,
    )


def expand_invalid_mask_for_radius(
    invalid_mask,
    *,
    invalid_pixel_radius: int = 0,
) -> np.ndarray:
    """Expand invalid regions so nearby pixels also become non-detectable.

    This implements the repository's `invalid-pixel-radius` semantics: if a
    candidate pixel lies within a square Chebyshev neighborhood of any invalid
    pixel, or is too close to the image border, it is treated as invalid for
    feature detection.
    """
    resolved_radius = validate_invalid_pixel_radius(invalid_pixel_radius)
    resolved_invalid_mask = np.asarray(invalid_mask, dtype=bool)
    if resolved_radius == 0 or resolved_invalid_mask.size == 0:
        return resolved_invalid_mask.copy()

    valid_mask = np.where(~resolved_invalid_mask, 255, 0).astype(np.uint8)
    kernel_size = 2 * resolved_radius + 1
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    eroded_valid_mask = cv2.erode(
        valid_mask,
        kernel,
        iterations=1,
        borderType=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return eroded_valid_mask == 0


def _resolve_stretch_bounds(
    array: np.ndarray,
    *,
    invalid_mask: np.ndarray,
    minimum_value: float | None,
    maximum_value: float | None,
    lower_percent: float,
    upper_percent: float,
) -> tuple[float, float]:
    valid_values = array[~invalid_mask]
    if valid_values.size == 0:
        raise ValueError("Cannot compute a stretch because all pixels are invalid.")

    if minimum_value is not None or maximum_value is not None:
        if minimum_value is None or maximum_value is None:
            raise ValueError("Both minimum_value and maximum_value must be provided together.")
        if maximum_value <= minimum_value:
            raise ValueError("maximum_value must be greater than minimum_value.")
        return float(minimum_value), float(maximum_value)

    if not (0.0 <= lower_percent < upper_percent <= 100.0):
        raise ValueError("Percent stretch bounds must satisfy 0 <= lower < upper <= 100.")

    lower_bound, upper_bound = np.percentile(valid_values, [lower_percent, upper_percent])
    if upper_bound <= lower_bound:
        raise ValueError("Resolved stretch bounds are degenerate; the valid pixels do not span a range.")

    return float(lower_bound), float(upper_bound)


def stretch_to_byte(
    values,
    *,
    minimum_value: float | None = None,
    maximum_value: float | None = None,
    lower_percent: float = 0.5,
    upper_percent: float = 99.5,
    invalid_values: tuple[float, ...] = (),
    special_pixel_abs_threshold: float = 1.0e300,
    invalid_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, StretchStats]:
    """将数值数组拉伸到 uint8 灰度范围，同时保留无效像素掩膜。

    Stretch numeric values to uint8 while preserving an invalid-pixel mask.
    """
    array = np.asarray(values, dtype=np.float64)
    resolved_invalid_mask = build_invalid_mask(
        array,
        invalid_values=invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
    )
    if invalid_mask is not None:
        resolved_invalid_mask = np.asarray(invalid_mask, dtype=bool)
    min_value, max_value = _resolve_stretch_bounds(
        array,
        invalid_mask=resolved_invalid_mask,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        lower_percent=lower_percent,
        upper_percent=upper_percent,
    )

    clipped = np.clip(array, min_value, max_value)
    scaled = (clipped - min_value) / (max_value - min_value) * 255.0
    scaled = np.where(resolved_invalid_mask, 0.0, scaled)
    stretched = np.rint(scaled).astype(np.uint8)

    stats = StretchStats(
        minimum_value=min_value,
        maximum_value=max_value,
        valid_pixel_count=int((~resolved_invalid_mask).sum()),
        invalid_pixel_count=int(resolved_invalid_mask.sum()),
    )
    return stretched, resolved_invalid_mask, stats