"""用于 DOM 匹配的灰度值预处理辅助函数。

Gray-value preprocessing helpers for DOM matching.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class StretchStats:
    minimum_value: float
    maximum_value: float
    valid_pixel_count: int
    invalid_pixel_count: int


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
) -> tuple[np.ndarray, np.ndarray, StretchStats]:
    """将数值数组拉伸到 uint8 灰度范围，同时保留无效像素掩膜。

    Stretch numeric values to uint8 while preserving an invalid-pixel mask.
    """
    array = np.asarray(values, dtype=np.float64)
    invalid_mask = build_invalid_mask(
        array,
        invalid_values=invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
    )
    min_value, max_value = _resolve_stretch_bounds(
        array,
        invalid_mask=invalid_mask,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        lower_percent=lower_percent,
        upper_percent=upper_percent,
    )

    clipped = np.clip(array, min_value, max_value)
    scaled = (clipped - min_value) / (max_value - min_value) * 255.0
    scaled = np.where(invalid_mask, 0.0, scaled)
    stretched = np.rint(scaled).astype(np.uint8)

    stats = StretchStats(
        minimum_value=min_value,
        maximum_value=max_value,
        valid_pixel_count=int((~invalid_mask).sum()),
        invalid_pixel_count=int(invalid_mask.sum()),
    )
    return stretched, invalid_mask, stats