"""DOM tile-validity cache helpers for full-resolution matching prefilters.

Author: Geng Xun
Created: 2026-05-02
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

import numpy as np

from .tiling import TileWindow
if TYPE_CHECKING:
    from .tile_matching import PairedTileWindow


CACHE_FORMAT_VERSION = 1
DEFAULT_TILE_VALIDITY_CELL_WIDTH = 1024
DEFAULT_TILE_VALIDITY_CELL_HEIGHT = 1024


@dataclass(frozen=True, slots=True)
class TileValidityIndex:
    dom_path: str
    image_width: int
    image_height: int
    cell_width: int
    cell_height: int
    grid_width: int
    grid_height: int
    valid_counts: np.ndarray
    total_counts: np.ndarray
    uncertain: np.ndarray
    manifest: dict[str, Any]


@dataclass(frozen=True, slots=True)
class TileValidityUpperBound:
    valid_pixel_upper_bound: int
    window_pixel_count: int
    valid_ratio_upper_bound: float
    has_uncertain_cells: bool


@dataclass(frozen=True, slots=True)
class TileValidityPrefilterResult:
    kept_windows: list[PairedTileWindow]
    skipped_windows: list[PairedTileWindow]
    preindexed_skipped_tile_count: int
    skip_reasons: dict[str, int]


def validate_tile_validity_cell_size(value: int, *, field_name: str) -> int:
    resolved_value = int(value)
    if resolved_value <= 0:
        raise ValueError(f"{field_name} must be positive.")
    return resolved_value


def _covered_cell_range(start: int, length: int, cell_size: int, grid_size: int) -> range:
    """Return the inclusive cell index range covered by a span, or empty if none."""
    if length <= 0 or cell_size <= 0 or grid_size <= 0:
        return range(0, 0)

    start_cell = start // cell_size
    end_cell = (start + length - 1) // cell_size

    if end_cell < 0 or start_cell >= grid_size:
        return range(0, 0)

    clamped_start = max(0, start_cell)
    clamped_end = min(grid_size - 1, end_cell)
    if clamped_end < clamped_start:
        return range(0, 0)

    return range(clamped_start, clamped_end + 1)


def window_valid_upper_bound(index: TileValidityIndex, window: TileWindow) -> TileValidityUpperBound:
    """Compute a conservative upper bound for valid pixels in a window."""
    x_range = _covered_cell_range(window.start_x, window.width, index.cell_width, index.grid_width)
    y_range = _covered_cell_range(window.start_y, window.height, index.cell_height, index.grid_height)

    valid_pixel_upper_bound = 0
    has_uncertain_cells = False
    for cell_y in y_range:
        for cell_x in x_range:
            valid_pixel_upper_bound += int(index.valid_counts[cell_y, cell_x])
            if bool(index.uncertain[cell_y, cell_x]):
                has_uncertain_cells = True

    window_pixel_count = int(window.width * window.height)
    if window_pixel_count <= 0:
        valid_ratio_upper_bound = 0.0
    else:
        valid_ratio_upper_bound = min(valid_pixel_upper_bound / float(window_pixel_count), 1.0)

    return TileValidityUpperBound(
        valid_pixel_upper_bound=valid_pixel_upper_bound,
        window_pixel_count=window_pixel_count,
        valid_ratio_upper_bound=valid_ratio_upper_bound,
        has_uncertain_cells=has_uncertain_cells,
    )


def _side_skip_reason(
    upper_bound: TileValidityUpperBound,
    *,
    side_name: str,
    valid_pixel_percent_threshold: float,
) -> str | None:
    if upper_bound.has_uncertain_cells:
        return None
    if valid_pixel_percent_threshold > 0 and upper_bound.valid_ratio_upper_bound < valid_pixel_percent_threshold:
        return f"{side_name}_valid_upper_bound_below_threshold"
    return None


def prefilter_paired_windows_by_validity(
    windows: list[PairedTileWindow],
    *,
    left_index: TileValidityIndex,
    right_index: TileValidityIndex,
    valid_pixel_percent_threshold: float,
) -> TileValidityPrefilterResult:
    """Conservatively skip only when upper bounds cannot meet the [0, 1] ratio threshold."""
    if valid_pixel_percent_threshold < 0.0 or valid_pixel_percent_threshold > 1.0:
        raise ValueError("valid_pixel_percent_threshold must be within [0.0, 1.0].")
    if valid_pixel_percent_threshold <= 0:
        return TileValidityPrefilterResult(
            kept_windows=list(windows),
            skipped_windows=[],
            preindexed_skipped_tile_count=0,
            skip_reasons={},
        )

    kept_windows: list[PairedTileWindow] = []
    skipped_windows: list[PairedTileWindow] = []
    skip_reasons: dict[str, int] = {}

    for paired_window in windows:
        left_upper_bound = window_valid_upper_bound(left_index, paired_window.left_window)
        right_upper_bound = window_valid_upper_bound(right_index, paired_window.right_window)

        skip_reason = _side_skip_reason(
            left_upper_bound,
            side_name="left",
            valid_pixel_percent_threshold=valid_pixel_percent_threshold,
        )
        if skip_reason is None:
            skip_reason = _side_skip_reason(
                right_upper_bound,
                side_name="right",
                valid_pixel_percent_threshold=valid_pixel_percent_threshold,
            )

        if skip_reason is None:
            kept_windows.append(paired_window)
        else:
            skipped_windows.append(paired_window)
            skip_reasons[skip_reason] = skip_reasons.get(skip_reason, 0) + 1

    return TileValidityPrefilterResult(
        kept_windows=kept_windows,
        skipped_windows=skipped_windows,
        preindexed_skipped_tile_count=len(skipped_windows),
        skip_reasons=skip_reasons,
    )


def default_tile_validity_cache_dir(
    *,
    metadata_output: str | Path | None = None,
    left_output_key: str | Path | None = None,
) -> Path:
    if metadata_output is not None:
        return Path(metadata_output).parent.parent / "tile_validity_cache"
    if left_output_key is not None:
        return Path(left_output_key).parent.parent / "tile_validity_cache"
    return Path.cwd() / "tile_validity_cache"
