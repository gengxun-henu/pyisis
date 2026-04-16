"""Focused unit tests for the DOM matching ControlNet foundation helpers.

Author: Geng Xun
Created: 2026-04-16
Last Modified: 2026-04-16
Updated: 2026-04-16  Geng Xun added initial regression coverage for list parsing, .key IO, duplicate tie-point merging, tiling, and grayscale stretch helpers.
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import temporary_directory

EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.keypoints import Keypoint, KeypointFile, read_key_file, write_key_file
from controlnet_construct.listing import (
    StereoPair,
    canonicalize_stereo_pair,
    read_path_list,
    read_stereo_pair_list,
    unique_stereo_pairs,
    validate_paired_path_lists,
    write_stereo_pair_list,
)
from controlnet_construct.merge import merge_duplicate_keypoints
from controlnet_construct.preprocess import stretch_to_byte
from controlnet_construct.tiling import generate_tiles, requires_tiling


class ControlNetConstructFoundationUnitTest(unittest.TestCase):
    def test_read_path_list_skips_blank_lines(self):
        with temporary_directory() as temp_dir:
            listing_path = temp_dir / "doms.lis"
            listing_path.write_text("a.cub\n\n  b.cub  \n", encoding="utf-8")

            self.assertEqual(read_path_list(listing_path), ["a.cub", "b.cub"])

    def test_validate_paired_path_lists_requires_equal_lengths(self):
        with self.assertRaises(ValueError):
            validate_paired_path_lists(["a.cub"], ["a_dom.cub", "b_dom.cub"])

    def test_stereo_pair_canonicalization_is_unordered(self):
        self.assertEqual(
            canonicalize_stereo_pair("B.cub", "A.cub"),
            StereoPair("A.cub", "B.cub"),
        )

    def test_unique_stereo_pairs_preserves_first_seen_order(self):
        pairs = unique_stereo_pairs(
            [
                ("B.cub", "A.cub"),
                ("A.cub", "B.cub"),
                ("C.cub", "D.cub"),
            ]
        )

        self.assertEqual(pairs, [StereoPair("A.cub", "B.cub"), StereoPair("C.cub", "D.cub")])

    def test_write_and_read_stereo_pair_list_roundtrip(self):
        with temporary_directory() as temp_dir:
            pair_path = temp_dir / "images_overlap.lis"
            expected_pairs = [StereoPair("A.cub", "B.cub"), StereoPair("C.cub", "D.cub")]

            write_stereo_pair_list(pair_path, expected_pairs)
            actual_pairs = read_stereo_pair_list(pair_path)

            self.assertEqual(actual_pairs, expected_pairs)

    def test_write_and_read_key_file_roundtrip(self):
        key_file = KeypointFile(
            image_width=2048,
            image_height=1024,
            points=(Keypoint(10.5, 20.25), Keypoint(30.0, 40.75)),
        )

        with temporary_directory() as temp_dir:
            key_path = temp_dir / "A__B_A.key"
            write_key_file(key_path, key_file)
            loaded = read_key_file(key_path)

            self.assertEqual(loaded, key_file)

    def test_read_key_file_rejects_wrong_point_count(self):
        with temporary_directory() as temp_dir:
            key_path = temp_dir / "broken.key"
            key_path.write_text("2\n100\n200\n1.0, 2.0,\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                read_key_file(key_path)

    def test_merge_duplicate_keypoints_uses_three_decimal_hashes(self):
        left_points = KeypointFile(
            image_width=100,
            image_height=100,
            points=(
                Keypoint(10.0004, 20.0004),
                Keypoint(10.00049, 20.00049),
                Keypoint(12.5, 24.5),
            ),
        )
        right_points = KeypointFile(
            image_width=100,
            image_height=100,
            points=(
                Keypoint(30.0004, 40.0004),
                Keypoint(30.00049, 40.00049),
                Keypoint(32.5, 44.5),
            ),
        )

        merged_left, merged_right, summary = merge_duplicate_keypoints(left_points, right_points)

        self.assertEqual(len(merged_left.points), 2)
        self.assertEqual(len(merged_right.points), 2)
        self.assertEqual(summary.input_count, 3)
        self.assertEqual(summary.unique_count, 2)
        self.assertEqual(summary.duplicate_count, 1)

    def test_generate_tiles_covers_large_image(self):
        tiles = generate_tiles(2500, 2100, block_width=1024, block_height=1024, overlap_x=128, overlap_y=128)

        self.assertGreater(len(tiles), 1)
        self.assertEqual(tiles[0].start_x, 0)
        self.assertEqual(tiles[0].start_y, 0)
        self.assertTrue(any(tile.end_x == 2500 for tile in tiles))
        self.assertTrue(any(tile.end_y == 2100 for tile in tiles))

    def test_requires_tiling_uses_default_threshold(self):
        self.assertFalse(requires_tiling(3000, 3000))
        self.assertTrue(requires_tiling(3001, 3000))

    def test_stretch_to_byte_excludes_invalid_values_from_statistics(self):
        values = np.array([
            [0.0, 1.0, 2.0],
            [3.0, 4.0, 9999.0],
            [np.nan, 5.0, np.inf],
        ])

        stretched, invalid_mask, stats = stretch_to_byte(values, minimum_value=0.0, maximum_value=5.0, invalid_values=(9999.0,))

        self.assertEqual(stretched.dtype, np.uint8)
        self.assertEqual(stretched[0, 0], 0)
        self.assertEqual(stretched[2, 1], 255)
        self.assertEqual(stretched[1, 2], 0)
        self.assertTrue(invalid_mask[1, 2])
        self.assertTrue(invalid_mask[2, 0])
        self.assertTrue(invalid_mask[2, 2])
        self.assertEqual(stats.valid_pixel_count, 6)
        self.assertEqual(stats.invalid_pixel_count, 3)

    def test_stretch_to_byte_uses_percentile_bounds_when_manual_bounds_absent(self):
        values = np.array([0.0, 10.0, 20.0, 30.0, 40.0], dtype=np.float64)

        stretched, invalid_mask, stats = stretch_to_byte(values, lower_percent=0.0, upper_percent=100.0)

        self.assertFalse(invalid_mask.any())
        self.assertEqual(int(stretched[0]), 0)
        self.assertEqual(int(stretched[-1]), 255)
        self.assertEqual(stats.minimum_value, 0.0)
        self.assertEqual(stats.maximum_value, 40.0)


if __name__ == "__main__":
    unittest.main()