"""Focused unit tests for DOM matching SIFT helpers and invalid-value handling.

Author: Geng Xun
Created: 2026-04-16
Last Modified: 2026-04-16
Updated: 2026-04-16  Geng Xun added focused regression coverage for DOM cube block matching, global coordinate reassembly, and extreme special-pixel masking.
Updated: 2026-04-17  Geng Xun added regression coverage for tiled DOM matching when the paired DOM cubes differ slightly in raster size.
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

import cv2
import numpy as np


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import ip, make_test_cube, temporary_directory, workspace_test_data_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.image_match import match_dom_pair


REAL_DOM_LEFT = workspace_test_data_path("hidtmgen", "ortho", "PSP_002118_1510_1m_o_forPDS_cropped.cub")
REAL_DOM_RIGHT = workspace_test_data_path("hidtmgen", "ortho", "PSP_002118_1510_25cm_o_forPDS_cropped.cub")
SPECIAL_PIXEL = -1.797693134862315e308


def _write_array_to_cube(cube: ip.Cube, values: np.ndarray) -> None:
    manager = ip.LineManager(cube)
    manager.begin()
    while not manager.end():
        line_index = manager.line() - 1
        for index in range(len(manager)):
            manager[index] = float(values[line_index, index])
        cube.write(manager)
        manager.next()


def _build_textured_test_image(width: int, height: int) -> np.ndarray:
    image = np.zeros((height, width), dtype=np.uint8)
    cv2.circle(image, (width // 4, height // 4), 12, 180, thickness=-1)
    cv2.circle(image, (3 * width // 4, height // 4), 10, 220, thickness=2)
    cv2.rectangle(image, (20, height // 2), (width // 2, height - 20), 140, thickness=3)
    cv2.line(image, (0, height - 1), (width - 1, 0), 255, thickness=2)
    cv2.putText(image, "ISIS", (width // 3, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 200, 2)
    return image.astype(np.float64)


class ControlNetConstructMatchingUnitTest(unittest.TestCase):
    def test_match_dom_pair_uses_shared_extent_for_unequal_dom_sizes(self):
        left_width = 128
        right_width = 120
        height = 128
        left_image = _build_textured_test_image(left_width, height)
        right_image = left_image[:, :right_width]

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="left_shared_extent_dom.cub", samples=left_width, lines=height, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="right_shared_extent_dom.cub", samples=right_width, lines=height, bands=1)
            try:
                _write_array_to_cube(left_cube, left_image)
                _write_array_to_cube(right_cube, right_image)
            finally:
                left_cube.close()
                right_cube.close()

            left_key_file, right_key_file, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=64,
                block_width=64,
                block_height=64,
                overlap_x=16,
                overlap_y=16,
                min_valid_pixels=32,
                ratio_test=0.8,
            )

        self.assertTrue(summary["tiling_used"])
        self.assertTrue(summary["dimension_mismatch"])
        self.assertEqual(summary["shared_extent_width"], right_width)
        self.assertEqual(summary["shared_extent_height"], height)
        self.assertGreater(summary["point_count"], 0)
        self.assertEqual(len(left_key_file.points), len(right_key_file.points))
        self.assertTrue(all(1.0 <= point.sample <= left_width for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.sample <= right_width for point in right_key_file.points))

    def test_match_dom_pair_reassembles_global_coordinates_after_tiling(self):
        width = 128
        height = 128
        image = _build_textured_test_image(width, height)

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="left_dom.cub", samples=width, lines=height, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="right_dom.cub", samples=width, lines=height, bands=1)
            try:
                _write_array_to_cube(left_cube, image)
                _write_array_to_cube(right_cube, image)
            finally:
                left_cube.close()
                right_cube.close()

            left_key_file, right_key_file, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=64,
                block_width=64,
                block_height=64,
                overlap_x=16,
                overlap_y=16,
                min_valid_pixels=32,
                ratio_test=0.8,
            )

        self.assertTrue(summary["tiling_used"])
        self.assertGreater(summary["tile_count"], 1)
        self.assertGreater(summary["point_count"], 0)
        self.assertEqual(len(left_key_file.points), len(right_key_file.points))
        self.assertTrue(any(point.sample > 64.0 or point.line > 64.0 for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.sample <= width for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.line <= height for point in left_key_file.points))

    def test_match_dom_pair_skips_invalid_only_tiles_but_keeps_valid_tile(self):
        width = 96
        height = 96
        image = np.full((height, width), SPECIAL_PIXEL, dtype=np.float64)
        image[48:96, 48:96] = _build_textured_test_image(48, 48)

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="left_invalid_dom.cub", samples=width, lines=height, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="right_invalid_dom.cub", samples=width, lines=height, bands=1)
            try:
                _write_array_to_cube(left_cube, image)
                _write_array_to_cube(right_cube, image)
            finally:
                left_cube.close()
                right_cube.close()

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=40,
                block_width=48,
                block_height=48,
                overlap_x=0,
                overlap_y=0,
                min_valid_pixels=32,
            )

        self.assertEqual(summary["tile_count"], 4)
        self.assertGreaterEqual(summary["skipped_tile_count"], 3)
        self.assertGreater(summary["point_count"], 0)
        self.assertIn(
            "skipped_insufficient_valid_pixels",
            {tile["status"] for tile in summary["tiles"]},
        )

    def test_match_dom_pair_on_real_dom_cubes_returns_in_bounds_keypoints(self):
        left_key_file, right_key_file, summary = match_dom_pair(
            REAL_DOM_LEFT,
            REAL_DOM_RIGHT,
            min_valid_pixels=16,
            ratio_test=0.85,
        )

        self.assertEqual(left_key_file.image_width, 50)
        self.assertEqual(left_key_file.image_height, 50)
        self.assertEqual(right_key_file.image_width, 50)
        self.assertEqual(right_key_file.image_height, 50)
        self.assertEqual(len(left_key_file.points), len(right_key_file.points))
        self.assertGreater(summary["point_count"], 0)
        self.assertTrue(all(1.0 <= point.sample <= 50.0 for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.line <= 50.0 for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.sample <= 50.0 for point in right_key_file.points))
        self.assertTrue(all(1.0 <= point.line <= 50.0 for point in right_key_file.points))


if __name__ == "__main__":
    unittest.main()