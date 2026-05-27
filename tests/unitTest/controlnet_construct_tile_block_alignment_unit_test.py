"""Unit tests for ISIS storage-tile block alignment helpers.

Author: Geng Xun
Created: 2026-05-27
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

alignment = importlib.import_module("controlnet_construct.tile_block_alignment")
StorageTileShape = alignment.StorageTileShape
resolve_tile_aligned_block_config = alignment.resolve_tile_aligned_block_config
generate_aligned_axis_starts = alignment.generate_aligned_axis_starts


class TestTileBlockAlignmentResolver(unittest.TestCase):
    def test_off_preserves_requested_values(self):
        result = resolve_tile_aligned_block_config(
            mode="off",
            left_shape=StorageTileShape(width=128, height=128),
            right_shape=StorageTileShape(width=128, height=128),
            left_offset_x=7,
            left_offset_y=9,
            right_offset_x=13,
            right_offset_y=15,
            requested_block_width=1000,
            requested_block_height=900,
            requested_overlap_x=120,
            requested_overlap_y=80,
            common_width=5000,
            common_height=4000,
        )

        self.assertEqual(result.mode, "off")
        self.assertFalse(result.aligned)
        self.assertEqual(result.effective_block_width, 1000)
        self.assertEqual(result.effective_block_height, 900)
        self.assertEqual(result.effective_overlap_x, 120)
        self.assertEqual(result.effective_overlap_y, 80)
        self.assertIsNone(result.local_windows)

    def test_auto_aligns_when_offsets_share_storage_remainder(self):
        result = resolve_tile_aligned_block_config(
            mode="auto",
            left_shape=StorageTileShape(width=128, height=128),
            right_shape=StorageTileShape(width=128, height=128),
            left_offset_x=256,
            left_offset_y=128,
            right_offset_x=512,
            right_offset_y=384,
            requested_block_width=1000,
            requested_block_height=900,
            requested_overlap_x=120,
            requested_overlap_y=80,
            common_width=2600,
            common_height=1800,
        )

        self.assertEqual(result.mode, "auto")
        self.assertTrue(result.aligned)
        self.assertEqual(result.effective_block_width, 1024)
        self.assertEqual(result.effective_block_height, 1024)
        self.assertEqual(result.effective_overlap_x, 128)
        self.assertEqual(result.effective_overlap_y, 128)
        self.assertGreater(len(result.local_windows or ()), 1)
        for window in result.local_windows:
            if window.start_x == 2600 - result.effective_block_width or window.start_y == 1800 - result.effective_block_height:
                continue
            self.assertEqual((256 + window.start_x) % 128, 0)
            self.assertEqual((512 + window.start_x) % 128, 0)
            self.assertEqual((128 + window.start_y) % 128, 0)
            self.assertEqual((384 + window.start_y) % 128, 0)

    def test_auto_falls_back_when_offset_remainders_conflict(self):
        result = resolve_tile_aligned_block_config(
            mode="auto",
            left_shape=StorageTileShape(width=128, height=128),
            right_shape=StorageTileShape(width=128, height=128),
            left_offset_x=0,
            left_offset_y=0,
            right_offset_x=64,
            right_offset_y=0,
            requested_block_width=512,
            requested_block_height=512,
            requested_overlap_x=128,
            requested_overlap_y=128,
            common_width=2048,
            common_height=2048,
        )

        self.assertFalse(result.aligned)
        self.assertEqual(result.fallback_reason_code, "incompatible_offset_remainders")
        self.assertIsNone(result.local_windows)

    def test_required_mode_raises_when_offset_remainders_conflict(self):
        with self.assertRaisesRegex(ValueError, "cannot align both DOM windows"):
            resolve_tile_aligned_block_config(
                mode="isis-storage",
                left_shape=StorageTileShape(width=128, height=128),
                right_shape=StorageTileShape(width=128, height=128),
                left_offset_x=0,
                left_offset_y=0,
                right_offset_x=64,
                right_offset_y=0,
                requested_block_width=512,
                requested_block_height=512,
                requested_overlap_x=128,
                requested_overlap_y=128,
                common_width=2048,
                common_height=2048,
            )

    def test_generate_aligned_axis_starts_keeps_full_coverage(self):
        starts = generate_aligned_axis_starts(
            size=2300,
            block_size=512,
            overlap_size=128,
            left_offset=256,
            right_offset=512,
            left_tile_size=128,
            right_tile_size=128,
        )

        self.assertEqual(starts[0], 0)
        self.assertEqual(starts[-1], 1788)
        for start in starts[:-1]:
            self.assertEqual((256 + start) % 128, 0)
            self.assertEqual((512 + start) % 128, 0)

    def test_generate_tiles_from_explicit_starts(self):
        tiling = importlib.import_module("image_match.tiling")
        tiles = tiling.generate_tiles_from_starts(
            image_width=1000,
            image_height=900,
            x_starts=[0, 384, 488],
            y_starts=[0, 384],
            block_width=512,
            block_height=512,
        )

        self.assertEqual([(tile.start_x, tile.start_y, tile.width, tile.height) for tile in tiles], [
            (0, 0, 512, 512),
            (384, 0, 512, 512),
            (488, 0, 512, 512),
            (0, 384, 512, 512),
            (384, 384, 512, 512),
            (488, 384, 512, 512),
        ])

    def test_paired_windows_accept_precomputed_local_windows(self):
        tile_matching = importlib.import_module("image_match.tile_matching")
        tiling = importlib.import_module("image_match.tiling")
        local_windows = [
            tiling.TileWindow(start_x=0, start_y=0, width=512, height=512),
            tiling.TileWindow(start_x=384, start_y=0, width=512, height=512),
        ]

        paired = tile_matching._paired_windows(
            left_offset_x=128,
            left_offset_y=256,
            right_offset_x=384,
            right_offset_y=512,
            common_width=1024,
            common_height=512,
            max_image_dimension=1,
            block_width=100,
            block_height=100,
            overlap_x=10,
            overlap_y=10,
            local_windows=local_windows,
        )

        self.assertEqual(len(paired), 2)
        self.assertEqual(paired[0].left_window.start_x, 128)
        self.assertEqual(paired[0].right_window.start_x, 384)
        self.assertEqual(paired[1].left_window.start_x, 512)
        self.assertEqual(paired[1].right_window.start_x, 768)


if __name__ == "__main__":
    unittest.main()
