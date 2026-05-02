"""Focused unit tests for DOM tile-validity cache and prefilter helpers.

Author: Geng Xun
Created: 2026-05-02
Last Modified: 2026-05-02
Updated: 2026-05-02  Geng Xun added regression coverage for conservative tile-validity prefilter decisions.
Updated: 2026-05-02  Geng Xun covered prefilter retention when the upper bound meets a positive threshold.
Updated: 2026-05-02  Geng Xun kept tile-validity fixtures realistic for prefilter skip decisions.
Updated: 2026-05-02  Geng Xun added import isolation and threshold validation coverage.
Updated: 2026-05-02  Geng Xun decoupled tile-validity tests from tile-matching imports.
Updated: 2026-05-02  Geng Xun added a namespace shim so helper imports skip package init.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import importlib.machinery
import sys
from pathlib import Path
import types
import unittest

import numpy as np


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

if "controlnet_construct" not in sys.modules:
    package = types.ModuleType("controlnet_construct")
    package.__path__ = [str(EXAMPLES_DIR / "controlnet_construct")]
    package.__package__ = "controlnet_construct"
    package.__spec__ = importlib.machinery.ModuleSpec(
        "controlnet_construct",
        loader=None,
        is_package=True,
    )
    sys.modules["controlnet_construct"] = package

tiling = importlib.import_module("controlnet_construct.tiling")


TileWindow = tiling.TileWindow


@dataclass(frozen=True, slots=True)
class PairedTileWindowForTest:
    local_window: TileWindow
    left_window: TileWindow
    right_window: TileWindow


def _import_tile_validity():
    return importlib.import_module("controlnet_construct.tile_validity")


class ControlNetConstructTileValidityUnitTest(unittest.TestCase):
    def test_tile_validity_import_does_not_pull_tile_matching(self):
        sys.modules.pop("controlnet_construct.tile_validity", None)
        sys.modules.pop("controlnet_construct.tile_matching", None)

        module = importlib.import_module("controlnet_construct.tile_validity")

        self.assertIs(module, sys.modules["controlnet_construct.tile_validity"])
        self.assertNotIn("controlnet_construct.tile_matching", sys.modules)

    def test_validate_tile_validity_cell_size_rejects_non_positive_values(self):
        tile_validity = _import_tile_validity()

        self.assertEqual(tile_validity.validate_tile_validity_cell_size(32, field_name="tile_validity_cell_width"), 32)
        with self.assertRaisesRegex(ValueError, "tile_validity_cell_width must be positive"):
            tile_validity.validate_tile_validity_cell_size(0, field_name="tile_validity_cell_width")
        with self.assertRaisesRegex(ValueError, "tile_validity_cell_height must be positive"):
            tile_validity.validate_tile_validity_cell_size(-1, field_name="tile_validity_cell_height")

    def test_window_upper_bound_uses_covered_cell_valid_counts(self):
        tile_validity = _import_tile_validity()

        index = tile_validity.TileValidityIndex(
            dom_path="left.cub",
            image_width=64,
            image_height=32,
            cell_width=32,
            cell_height=32,
            grid_width=2,
            grid_height=1,
            valid_counts=np.array([[32, 0]], dtype=np.int64),
            total_counts=np.array([[1024, 1024]], dtype=np.int64),
            uncertain=np.array([[False, False]], dtype=bool),
            manifest={"format_version": tile_validity.CACHE_FORMAT_VERSION},
        )

        upper_bound = tile_validity.window_valid_upper_bound(
            index,
            TileWindow(start_x=0, start_y=0, width=64, height=32),
        )

        self.assertEqual(upper_bound.valid_pixel_upper_bound, 32)
        self.assertEqual(upper_bound.window_pixel_count, 2048)
        self.assertAlmostEqual(upper_bound.valid_ratio_upper_bound, 32.0 / 2048.0)
        self.assertFalse(upper_bound.has_uncertain_cells)

    def test_prefilter_skips_only_when_upper_bound_cannot_meet_threshold(self):
        tile_validity = _import_tile_validity()

        left_index = tile_validity.TileValidityIndex(
            dom_path="left.cub",
            image_width=64,
            image_height=32,
            cell_width=32,
            cell_height=32,
            grid_width=2,
            grid_height=1,
            valid_counts=np.array([[16, 0]], dtype=np.int64),
            total_counts=np.array([[1024, 1024]], dtype=np.int64),
            uncertain=np.array([[False, False]], dtype=bool),
            manifest={"format_version": tile_validity.CACHE_FORMAT_VERSION},
        )
        right_index = tile_validity.TileValidityIndex(
            dom_path="right.cub",
            image_width=64,
            image_height=32,
            cell_width=32,
            cell_height=32,
            grid_width=2,
            grid_height=1,
            valid_counts=np.array([[1024, 1024]], dtype=np.int64),
            total_counts=np.array([[1024, 1024]], dtype=np.int64),
            uncertain=np.array([[False, False]], dtype=bool),
            manifest={"format_version": tile_validity.CACHE_FORMAT_VERSION},
        )
        windows = [
            PairedTileWindowForTest(
                local_window=TileWindow(0, 0, 64, 32),
                left_window=TileWindow(0, 0, 64, 32),
                right_window=TileWindow(0, 0, 64, 32),
            )
        ]

        result = tile_validity.prefilter_paired_windows_by_validity(
            windows,
            left_index=left_index,
            right_index=right_index,
            valid_pixel_percent_threshold=0.05,
        )

        self.assertEqual(result.kept_windows, [])
        self.assertEqual(result.skipped_windows, windows)
        self.assertEqual(result.preindexed_skipped_tile_count, 1)
        self.assertEqual(result.skip_reasons["left_valid_upper_bound_below_threshold"], 1)

    def test_prefilter_keeps_when_upper_bound_can_meet_positive_threshold(self):
        tile_validity = _import_tile_validity()

        left_index = tile_validity.TileValidityIndex(
            dom_path="left.cub",
            image_width=64,
            image_height=32,
            cell_width=32,
            cell_height=32,
            grid_width=2,
            grid_height=1,
            valid_counts=np.array([[128, 0]], dtype=np.int64),
            total_counts=np.array([[1024, 1024]], dtype=np.int64),
            uncertain=np.array([[False, False]], dtype=bool),
            manifest={"format_version": tile_validity.CACHE_FORMAT_VERSION},
        )
        right_index = tile_validity.TileValidityIndex(
            dom_path="right.cub",
            image_width=64,
            image_height=32,
            cell_width=32,
            cell_height=32,
            grid_width=2,
            grid_height=1,
            valid_counts=np.array([[256, 256]], dtype=np.int64),
            total_counts=np.array([[1024, 1024]], dtype=np.int64),
            uncertain=np.array([[False, False]], dtype=bool),
            manifest={"format_version": tile_validity.CACHE_FORMAT_VERSION},
        )
        window = PairedTileWindowForTest(
            local_window=TileWindow(0, 0, 64, 32),
            left_window=TileWindow(0, 0, 64, 32),
            right_window=TileWindow(0, 0, 64, 32),
        )

        result = tile_validity.prefilter_paired_windows_by_validity(
            [window],
            left_index=left_index,
            right_index=right_index,
            valid_pixel_percent_threshold=0.05,
        )

        self.assertEqual(result.kept_windows, [window])
        self.assertEqual(result.skipped_windows, [])
        self.assertEqual(result.preindexed_skipped_tile_count, 0)
        self.assertEqual(result.skip_reasons, {})

    def test_prefilter_keeps_threshold_zero_and_uncertain_cells(self):
        tile_validity = _import_tile_validity()

        index = tile_validity.TileValidityIndex(
            dom_path="left.cub",
            image_width=32,
            image_height=32,
            cell_width=32,
            cell_height=32,
            grid_width=1,
            grid_height=1,
            valid_counts=np.array([[0]], dtype=np.int64),
            total_counts=np.array([[1024]], dtype=np.int64),
            uncertain=np.array([[True]], dtype=bool),
            manifest={"format_version": tile_validity.CACHE_FORMAT_VERSION},
        )
        window = PairedTileWindowForTest(
            local_window=TileWindow(0, 0, 32, 32),
            left_window=TileWindow(0, 0, 32, 32),
            right_window=TileWindow(0, 0, 32, 32),
        )

        zero_threshold_result = tile_validity.prefilter_paired_windows_by_validity(
            [window],
            left_index=index,
            right_index=index,
            valid_pixel_percent_threshold=0.0,
        )
        uncertain_result = tile_validity.prefilter_paired_windows_by_validity(
            [window],
            left_index=index,
            right_index=index,
            valid_pixel_percent_threshold=0.2,
        )

        self.assertEqual(zero_threshold_result.kept_windows, [window])
        self.assertEqual(zero_threshold_result.skipped_windows, [])
        self.assertEqual(zero_threshold_result.preindexed_skipped_tile_count, 0)
        self.assertEqual(zero_threshold_result.skip_reasons, {})
        self.assertEqual(uncertain_result.kept_windows, [window])
        self.assertEqual(uncertain_result.skipped_windows, [])
        self.assertEqual(uncertain_result.preindexed_skipped_tile_count, 0)
        self.assertEqual(uncertain_result.skip_reasons, {})

    def test_prefilter_rejects_invalid_threshold(self):
        tile_validity = _import_tile_validity()

        index = tile_validity.TileValidityIndex(
            dom_path="left.cub",
            image_width=32,
            image_height=32,
            cell_width=32,
            cell_height=32,
            grid_width=1,
            grid_height=1,
            valid_counts=np.array([[0]], dtype=np.int64),
            total_counts=np.array([[1024]], dtype=np.int64),
            uncertain=np.array([[False]], dtype=bool),
            manifest={"format_version": tile_validity.CACHE_FORMAT_VERSION},
        )

        with self.assertRaisesRegex(ValueError, r"valid_pixel_percent_threshold must be within \[0.0, 1.0\]"):
            tile_validity.prefilter_paired_windows_by_validity(
                [],
                left_index=index,
                right_index=index,
                valid_pixel_percent_threshold=1.1,
            )


if __name__ == "__main__":
    unittest.main()
