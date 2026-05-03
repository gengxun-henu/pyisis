"""Focused unit tests for DOM tile-validity cache helpers.

Author: Geng Xun
Created: 2026-05-02
Last Modified: 2026-05-02
Updated: 2026-05-02  Geng Xun added core validity-grid cache and conservative prefilter coverage.
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.tile_validity import (  # noqa: E402
    DomPathMetadata,
    DomValidityCache,
    DomValidityGrid,
    TileValidityFilterSummary,
    build_dom_validity_cache_key,
    filter_windows_by_validity,
)
from controlnet_construct.tiling import TileWindow  # noqa: E402


class ControlNetConstructTileValidityUnitTest(unittest.TestCase):
    """Regression coverage for conservative DOM validity prefilter behavior."""

    def test_skips_window_when_all_fully_covered_cells_are_below_threshold(self):
        grid = DomValidityGrid.from_valid_counts(
            image_width=8,
            image_height=8,
            coarse_cell_size=4,
            valid_counts=((0, 1), (2, 3)),
        )

        decision = grid.decide_window(
            TileWindow(start_x=0, start_y=0, width=8, height=8),
            min_valid_pixels=4,
            valid_pixel_percent_threshold=0.25,
        )

        self.assertTrue(decision.should_skip)
        self.assertEqual(decision.reason, "all_confident_cells_below_threshold")
        self.assertEqual(decision.covered_cell_count, 4)
        self.assertEqual(decision.uncertain_cell_count, 0)

    def test_keeps_window_when_any_fully_covered_cell_meets_threshold(self):
        grid = DomValidityGrid.from_valid_counts(
            image_width=8,
            image_height=8,
            coarse_cell_size=4,
            valid_counts=((0, 6), (1, 2)),
        )

        decision = grid.decide_window(
            TileWindow(start_x=0, start_y=0, width=8, height=8),
            min_valid_pixels=4,
            valid_pixel_percent_threshold=0.25,
        )

        self.assertFalse(decision.should_skip)
        self.assertEqual(decision.reason, "contains_cell_at_or_above_threshold")
        self.assertEqual(decision.below_threshold_cell_count, 3)

    def test_keeps_boundary_window_when_coarse_cell_is_only_partially_covered(self):
        grid = DomValidityGrid.from_valid_counts(
            image_width=8,
            image_height=8,
            coarse_cell_size=4,
            valid_counts=((0, 0), (0, 0)),
        )

        decision = grid.decide_window(
            TileWindow(start_x=1, start_y=0, width=3, height=4),
            min_valid_pixels=1,
            valid_pixel_percent_threshold=0.01,
        )

        self.assertFalse(decision.should_skip)
        self.assertEqual(decision.reason, "uncertain_partial_cell_overlap")
        self.assertEqual(decision.uncertain_cell_count, 1)

    def test_cache_key_is_stable_for_same_metadata_and_changes_for_size_or_mtime(self):
        metadata = DomPathMetadata(path="dom.cub", size_bytes=1024, mtime_ns=100)
        key = build_dom_validity_cache_key(
            "dom.cub",
            metadata=metadata,
            band=1,
            coarse_cell_size=256,
            invalid_values=(-9999.0,),
            special_pixel_abs_threshold=1.0e300,
            invalid_pixel_radius=2,
            min_valid_pixels=64,
            valid_pixel_percent_threshold=0.35,
        )
        same_key = build_dom_validity_cache_key(
            "dom.cub",
            metadata=metadata,
            band=1,
            coarse_cell_size=256,
            invalid_values=(-9999.0,),
            special_pixel_abs_threshold=1.0e300,
            invalid_pixel_radius=2,
            min_valid_pixels=64,
            valid_pixel_percent_threshold=0.35,
        )
        changed_size = build_dom_validity_cache_key(
            "dom.cub",
            metadata=DomPathMetadata(path="dom.cub", size_bytes=2048, mtime_ns=100),
            band=1,
            coarse_cell_size=256,
            invalid_values=(-9999.0,),
            special_pixel_abs_threshold=1.0e300,
            invalid_pixel_radius=2,
            min_valid_pixels=64,
            valid_pixel_percent_threshold=0.35,
        )
        changed_mtime = build_dom_validity_cache_key(
            "dom.cub",
            metadata=DomPathMetadata(path="dom.cub", size_bytes=1024, mtime_ns=200),
            band=1,
            coarse_cell_size=256,
            invalid_values=(-9999.0,),
            special_pixel_abs_threshold=1.0e300,
            invalid_pixel_radius=2,
            min_valid_pixels=64,
            valid_pixel_percent_threshold=0.35,
        )

        self.assertEqual(key, same_key)
        self.assertNotEqual(key, changed_size)
        self.assertNotEqual(key, changed_mtime)


    def test_cache_reuses_grid_for_same_key_and_rebuilds_after_metadata_change(self):
        cache = DomValidityCache()
        calls: list[str] = []
        first_key = build_dom_validity_cache_key(
            "dom.cub",
            metadata=DomPathMetadata(path="dom.cub", size_bytes=1024, mtime_ns=100),
            band=1,
            coarse_cell_size=4,
            invalid_values=(),
            special_pixel_abs_threshold=1.0e300,
            invalid_pixel_radius=0,
            min_valid_pixels=1,
            valid_pixel_percent_threshold=0.1,
        )
        second_key = build_dom_validity_cache_key(
            "dom.cub",
            metadata=DomPathMetadata(path="dom.cub", size_bytes=1024, mtime_ns=200),
            band=1,
            coarse_cell_size=4,
            invalid_values=(),
            special_pixel_abs_threshold=1.0e300,
            invalid_pixel_radius=0,
            min_valid_pixels=1,
            valid_pixel_percent_threshold=0.1,
        )

        def builder():
            calls.append("built")
            return DomValidityGrid.from_valid_counts(
                image_width=4,
                image_height=4,
                coarse_cell_size=4,
                valid_counts=((16,),),
            )

        first_grid = cache.get_or_build(first_key, builder)
        reused_grid = cache.get_or_build(first_key, builder)
        rebuilt_grid = cache.get_or_build(second_key, builder)

        self.assertIs(first_grid, reused_grid)
        self.assertIsNot(first_grid, rebuilt_grid)
        self.assertEqual(calls, ["built", "built"])

    def test_batch_filter_summary_counts_kept_skipped_and_uncertain_windows(self):
        grid = DomValidityGrid.from_valid_counts(
            image_width=8,
            image_height=8,
            coarse_cell_size=4,
            valid_counts=((0, 6), (0, 0)),
        )
        windows = (
            TileWindow(start_x=0, start_y=0, width=4, height=4),
            TileWindow(start_x=4, start_y=0, width=4, height=4),
            TileWindow(start_x=1, start_y=4, width=3, height=4),
        )

        kept_windows, summary = filter_windows_by_validity(
            grid,
            windows,
            min_valid_pixels=4,
            valid_pixel_percent_threshold=0.25,
        )

        self.assertEqual(kept_windows, (windows[1], windows[2]))
        self.assertIsInstance(summary, TileValidityFilterSummary)
        self.assertEqual(summary.total_window_count, 3)
        self.assertEqual(summary.skipped_window_count, 1)
        self.assertEqual(summary.kept_window_count, 2)
        self.assertEqual(summary.uncertain_window_count, 1)


if __name__ == "__main__":
    unittest.main()
