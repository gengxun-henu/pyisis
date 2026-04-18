"""Focused unit tests for DOM matching SIFT helpers and invalid-value handling.

Author: Geng Xun
Created: 2026-04-16
Last Modified: 2026-04-17
Updated: 2026-04-16  Geng Xun added focused regression coverage for DOM cube block matching, global coordinate reassembly, and extreme special-pixel masking.
Updated: 2026-04-17  Geng Xun added regression coverage for tiled DOM matching when the paired DOM cubes differ slightly in raster size.
Updated: 2026-04-17  Geng Xun added focused regression coverage for configurable OpenCV SIFT CLI and detector parameters.
Updated: 2026-04-18  Geng Xun added focused regression coverage for merge-stage RANSAC filtering and default drawMatches visualization output naming.
"""

from __future__ import annotations

import importlib
from datetime import datetime
import sys
from pathlib import Path
import unittest
from unittest import mock

import cv2
import numpy as np


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import attach_dom_like_projection_mapping, ip, make_test_cube, temporary_directory, workspace_test_data_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

image_match = importlib.import_module("controlnet_construct.image_match")
build_argument_parser = image_match.build_argument_parser
default_match_visualization_path = image_match.default_match_visualization_path
filter_stereo_pair_keypoints_with_ransac = image_match.filter_stereo_pair_keypoints_with_ransac
match_dom_pair = image_match.match_dom_pair
write_stereo_pair_match_visualization_from_key_files = image_match.write_stereo_pair_match_visualization_from_key_files

keypoints_module = importlib.import_module("controlnet_construct.keypoints")
Keypoint = keypoints_module.Keypoint
KeypointFile = keypoints_module.KeypointFile
write_key_file = keypoints_module.write_key_file


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
    def test_default_match_visualization_path_uses_auto_timestamped_name(self):
        timestamp = datetime(2026, 4, 18, 18, 44, 32)

        output_path = default_match_visualization_path(
            "left/A.cub",
            "right/B.cub",
            output_directory="/tmp/rendered",
            timestamp=timestamp,
        )

        self.assertEqual(str(output_path), "/tmp/rendered/A__B__20260418T184432.png")

    def test_filter_stereo_pair_keypoints_with_ransac_strict_drops_marked_outlier(self):
        left_key_file = KeypointFile(
            100,
            100,
            (
                Keypoint(1.0, 1.0),
                Keypoint(11.0, 1.0),
                Keypoint(1.0, 11.0),
                Keypoint(11.0, 11.0),
                Keypoint(6.0, 6.0),
            ),
        )
        right_key_file = KeypointFile(
            100,
            100,
            (
                Keypoint(3.0, 4.0),
                Keypoint(13.0, 4.0),
                Keypoint(3.0, 14.0),
                Keypoint(13.0, 14.0),
                Keypoint(30.0, 30.0),
            ),
        )
        homography = np.array([[1.0, 0.0, 2.0], [0.0, 1.0, 3.0], [0.0, 0.0, 1.0]], dtype=np.float64)
        mask = np.array([[1], [1], [1], [1], [0]], dtype=np.uint8)

        with mock.patch.object(image_match.cv2, "findHomography", return_value=(homography, mask)):
            filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_with_ransac(
                left_key_file,
                right_key_file,
                ransac_mode="strict",
            )

        self.assertEqual(summary["mode"], "strict")
        self.assertEqual(summary["retained_count"], 4)
        self.assertEqual(summary["dropped_count"], 1)
        self.assertEqual(summary["opencv_outlier_count"], 1)
        self.assertEqual(summary["retained_soft_outlier_count"], 0)
        self.assertEqual(len(filtered_left.points), 4)
        self.assertEqual(len(filtered_right.points), 4)

    def test_filter_stereo_pair_keypoints_with_ransac_loose_keeps_small_reprojection_soft_outlier(self):
        left_key_file = KeypointFile(
            100,
            100,
            (
                Keypoint(1.0, 1.0),
                Keypoint(11.0, 1.0),
                Keypoint(1.0, 11.0),
                Keypoint(11.0, 11.0),
                Keypoint(6.0, 6.0),
            ),
        )
        right_key_file = KeypointFile(
            100,
            100,
            (
                Keypoint(3.0, 4.0),
                Keypoint(13.0, 4.0),
                Keypoint(3.0, 14.0),
                Keypoint(13.0, 14.0),
                Keypoint(8.6, 9.4),
            ),
        )
        homography = np.array([[1.0, 0.0, 2.0], [0.0, 1.0, 3.0], [0.0, 0.0, 1.0]], dtype=np.float64)
        mask = np.array([[1], [1], [1], [1], [0]], dtype=np.uint8)

        with mock.patch.object(image_match.cv2, "findHomography", return_value=(homography, mask)):
            filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_with_ransac(
                left_key_file,
                right_key_file,
                ransac_mode="loose",
                loose_keep_pixel_threshold=1.0,
            )

        self.assertEqual(summary["mode"], "loose")
        self.assertEqual(summary["retained_count"], 5)
        self.assertEqual(summary["dropped_count"], 0)
        self.assertEqual(summary["opencv_outlier_count"], 1)
        self.assertEqual(summary["retained_soft_outlier_count"], 1)
        self.assertEqual(summary["soft_outlier_original_indices"], [4])
        self.assertEqual(summary["retained_soft_outlier_positions"], [4])
        self.assertEqual(len(filtered_left.points), 5)
        self.assertEqual(len(filtered_right.points), 5)

    def test_build_argument_parser_accepts_custom_sift_parameters(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--max-features",
                "4096",
                "--sift-octave-layers",
                "5",
                "--sift-contrast-threshold",
                "0.02",
                "--sift-edge-threshold",
                "15.5",
                "--sift-sigma",
                "1.2",
            ]
        )

        self.assertEqual(args.max_features, 4096)
        self.assertEqual(args.sift_octave_layers, 5)
        self.assertAlmostEqual(args.sift_contrast_threshold, 0.02)
        self.assertAlmostEqual(args.sift_edge_threshold, 15.5)
        self.assertAlmostEqual(args.sift_sigma, 1.2)

    def test_build_sift_detector_forwards_custom_parameters_to_opencv(self):
        fake_detector = object()

        with mock.patch.object(image_match.cv2, "SIFT_create", return_value=fake_detector) as sift_create:
            detector = image_match._build_sift_detector(
                max_features=2048,
                octave_layers=5,
                contrast_threshold=0.03,
                edge_threshold=12.0,
                sigma=1.8,
            )

        self.assertIs(detector, fake_detector)
        sift_create.assert_called_once_with(
            nfeatures=2048,
            nOctaveLayers=5,
            contrastThreshold=0.03,
            edgeThreshold=12.0,
            sigma=1.8,
        )

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
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
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
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
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
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
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

    def test_write_stereo_pair_match_visualization_from_key_files_writes_default_png(self):
        width = 24
        height = 24
        image = _build_textured_test_image(width, height)

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="A.cub", samples=width, lines=height, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="B.cub", samples=width, lines=height, bands=1)
            try:
                _write_array_to_cube(left_cube, image)
                _write_array_to_cube(right_cube, image)
            finally:
                left_cube.close()
                right_cube.close()

            left_key_path = temp_dir / "left.key"
            right_key_path = temp_dir / "right.key"
            write_key_file(left_key_path, KeypointFile(width, height, (Keypoint(5.0, 5.0), Keypoint(10.0, 12.0))))
            write_key_file(right_key_path, KeypointFile(width, height, (Keypoint(6.0, 6.0), Keypoint(11.0, 13.0))))

            result = write_stereo_pair_match_visualization_from_key_files(
                left_path,
                right_path,
                left_key_path,
                right_key_path,
                output_directory=temp_dir,
                timestamp=datetime(2026, 4, 18, 18, 44, 32),
                scale_factor=3.0,
                highlight_match_indices=[1],
            )
            output_exists = Path(result["output_path"]).exists()

        self.assertTrue(result["output_path"].endswith("A__B__20260418T184432.png"))
        self.assertEqual(result["point_count"], 2)
        self.assertEqual(result["highlighted_match_count"], 1)
        self.assertTrue(output_exists)


if __name__ == "__main__":
    unittest.main()