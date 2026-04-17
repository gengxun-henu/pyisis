"""Focused regression tests for DOM matching coordinate-basis conventions.

Author: Geng Xun
Created: 2026-04-17
Last Modified: 2026-04-17
Updated: 2026-04-17  Geng Xun added focused regression coverage to lock down 0-based tile offsets versus 1-based ISIS sample/line conversions.
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.dom2ori import _is_point_in_bounds
from controlnet_construct.dom_prepare import CropWindow
from controlnet_construct.image_match import _keypoint_to_isis_coordinates
from controlnet_construct.image_overlap import _linspace_positions
from controlnet_construct.keypoints import Keypoint
from controlnet_construct.tiling import TileWindow


class ControlNetConstructCoordinateConventionsUnitTest(unittest.TestCase):
    def test_keypoint_conversion_maps_tile_local_zero_based_to_image_one_based(self):
        keypoint = cv2.KeyPoint(x=0.0, y=0.0, size=1.0)
        tile = TileWindow(start_x=9, start_y=19, width=128, height=128)

        converted = _keypoint_to_isis_coordinates(keypoint, tile)

        self.assertEqual(converted, Keypoint(10.0, 20.0))

    def test_keypoint_conversion_preserves_fractional_precision_while_adding_one(self):
        keypoint = cv2.KeyPoint(x=3.25, y=4.75, size=1.0)
        tile = TileWindow(start_x=100, start_y=200, width=64, height=64)

        converted = _keypoint_to_isis_coordinates(keypoint, tile)

        self.assertAlmostEqual(converted.sample, 104.25, places=6)
        self.assertAlmostEqual(converted.line, 205.75, places=6)

    def test_crop_window_exposes_one_based_starts_and_zero_based_offsets_consistently(self):
        window = CropWindow(
            path="synthetic.cub",
            start_sample=11,
            start_line=21,
            width=30,
            height=40,
            offset_sample=10,
            offset_line=20,
            projected_min_x=1.0,
            projected_max_x=2.0,
            projected_min_y=3.0,
            projected_max_y=4.0,
            clipped_by_image_bounds=False,
        )

        self.assertEqual(window.start_x, 10)
        self.assertEqual(window.start_y, 20)
        self.assertEqual(window.offset_sample, window.start_sample - 1)
        self.assertEqual(window.offset_line, window.start_line - 1)
        self.assertEqual(window.end_sample, 40)
        self.assertEqual(window.end_line, 60)

    def test_dom2ori_bounds_are_one_based_and_inclusive(self):
        self.assertFalse(_is_point_in_bounds(0.0, 1.0, 100, 200))
        self.assertFalse(_is_point_in_bounds(1.0, 0.0, 100, 200))
        self.assertTrue(_is_point_in_bounds(1.0, 1.0, 100, 200))
        self.assertTrue(_is_point_in_bounds(100.0, 200.0, 100, 200))
        self.assertFalse(_is_point_in_bounds(100.1, 200.0, 100, 200))
        self.assertFalse(_is_point_in_bounds(100.0, 200.1, 100, 200))

    def test_image_overlap_sampling_positions_start_at_one_and_end_at_image_extent(self):
        positions = _linspace_positions(101, 3)

        self.assertEqual(positions[0], 1.0)
        self.assertEqual(positions[-1], 101.0)
        self.assertEqual(positions[1], 51.0)


if __name__ == "__main__":
    unittest.main()
