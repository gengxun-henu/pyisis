"""Focused unit tests for the DOM matching ControlNet foundation helpers.

This module exercises the low-level helper layer that the higher-level DOM matching and
ControlNet pipeline code depends on. The covered behaviors include path-list parsing,
stereo-pair canonicalization, `.key` file round-trips, rounded-coordinate duplicate
merging, merge-parameter validation, tile generation, and grayscale stretch handling for
valid versus invalid numeric pixels.

The intent of this file is to keep foundational utility behavior stable before those
helpers are composed into larger matching, DOM-to-original conversion, and ControlNet
construction workflows. When one of these tests fails, it usually points to a small
helper-contract regression rather than a full pipeline integration break.

Author: Geng Xun
Created: 2026-04-16
Last Modified: 2026-04-19
Updated: 2026-04-16  Geng Xun added initial regression coverage for list parsing, .key IO, duplicate tie-point merging, tiling, and grayscale stretch helpers.
Updated: 2026-04-18  Geng Xun added regression coverage for rounded-coordinate merge metadata and merge-decimal validation.
Updated: 2026-04-18  Geng Xun expanded the module docstring to clarify the file's helper-layer scope and the distinction between foundational and pipeline-level regressions.
Updated: 2026-04-18  Geng Xun added optional real LRO DOM regression coverage for percentile-based grayscale stretching on an actual projected cube window.
Updated: 2026-04-19  Geng Xun added focused image-overlap regression coverage for dateline wrapping and north/south polar auxiliary bounds.
Updated: 2026-04-19  Geng Xun added regression coverage for polar-zone selection and the priority of polar auxiliary bounds over geographic fallback checks.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import temporary_directory
from _unit_test_support import ip

EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.keypoints import Keypoint, KeypointFile, read_key_file, write_key_file
from controlnet_construct.image_overlap import (
    GeoBounds,
    _minimal_longitude_interval,
    _polar_stereo_bounds_from_samples,
    _select_polar_projection_pole,
    bounds_overlap,
    geographic_bounds_overlap,
)
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
from controlnet_construct.tie_point_merge_in_overlap import merge_stereo_pair_key_files, validate_merge_decimals
from controlnet_construct.tiling import generate_tiles, requires_tiling


REAL_LRO_STRETCH_DOM_CUBE_ENV = "ISIS_PYBIND_STRETCH_REAL_DOM_CUBE"
DEFAULT_REAL_LRO_STRETCH_DOM_CUBE = Path("/media/gengxun/Elements/data/lro/test_controlnet_python/dom_M104311715RE.cub")


def _configured_real_lro_stretch_dom_cube() -> Path:
    return Path(os.environ.get(REAL_LRO_STRETCH_DOM_CUBE_ENV, str(DEFAULT_REAL_LRO_STRETCH_DOM_CUBE))).expanduser()


def _read_center_cube_window(
    path: str | Path,
    *,
    width: int | None = 256,
    height: int | None = 256,
    band: int = 1,
) -> np.ndarray:
    """Read a centered cube window, or the full 2D image when width/height are ``None``.

    This helper keeps the real-data stretch regression independent from hard-coded cube
    dimensions. Passing ``None`` for ``width`` and ``height`` promotes the request to the
    entire image plane of the chosen band, while finite values read the largest centered
    window that fits within the cube.
    """
    cube = ip.Cube()
    cube.open(str(path), "r")
    try:
        # ``None`` means "use the full image extent" for that dimension; otherwise clamp
        # the requested window size so the regression remains valid on smaller cubes.
        window_width = cube.sample_count() if width is None else min(width, cube.sample_count())
        window_height = cube.line_count() if height is None else min(height, cube.line_count())

        # Keep the finite-window behavior centered, while a full-image request naturally
        # collapses back to sample/line 1 after the max(...) guard.
        start_sample = max(1, cube.sample_count() // 2 - window_width // 2)
        start_line = max(1, cube.line_count() // 2 - window_height // 2)

        # ISIS Brick expects a band depth of 1 here because this helper reads a single 2D
        # slice from the requested band for grayscale stretch validation.
        brick = ip.Brick(cube, window_width, window_height, 1)
        brick.set_base_position(start_sample, start_line, band)
        cube.read(brick)
        return np.asarray(brick.double_buffer(), dtype=np.float64).reshape((window_height, window_width))
    finally:
        if cube.is_open():
            cube.close()


class ControlNetConstructFoundationUnitTest(unittest.TestCase):
    """Regression coverage for foundational DOM matching and overlap helper behavior."""

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

    def test_validate_merge_decimals_rejects_out_of_range_values(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 6"):
            validate_merge_decimals(-1)

        with self.assertRaisesRegex(ValueError, "between 0 and 6"):
            validate_merge_decimals(7)

        self.assertEqual(validate_merge_decimals(3), 3)

    def test_merge_stereo_pair_key_files_reports_hash_strategy_metadata(self):
        with temporary_directory() as temp_dir:
            left_input = temp_dir / "left_input.key"
            right_input = temp_dir / "right_input.key"
            left_output = temp_dir / "left_output.key"
            right_output = temp_dir / "right_output.key"

            write_key_file(
                left_input,
                KeypointFile(100, 100, (Keypoint(10.0004, 20.0004), Keypoint(10.00049, 20.00049))),
            )
            write_key_file(
                right_input,
                KeypointFile(100, 100, (Keypoint(30.0004, 40.0004), Keypoint(30.00049, 40.00049))),
            )

            result = merge_stereo_pair_key_files(left_input, right_input, left_output, right_output, decimals=3)

            self.assertEqual(result["duplicate_count"], 1)
            self.assertEqual(result["hash_strategy"], "rounded_stereo_pair_coordinate_hash")
            self.assertEqual(result["hash_coordinate_fields"], "left.sample,left.line,right.sample,right.line")
            self.assertEqual(result["hash_rounding_decimals"], 3)
            self.assertIn("fixed decimal precision", result["hash_description"])

    # image_overlap.py regressions: dateline wrapping and polar auxiliary bounds.

    def test_minimal_longitude_interval_marks_wraps_dateline_for_zero_crossing_samples(self):
        """Cross-dateline longitude samples should be represented as a wrapped interval."""
        start, end, wraps = _minimal_longitude_interval([350.0, 355.0, 2.0, 8.0])

        self.assertTrue(wraps)
        self.assertAlmostEqual(start, 350.0)
        self.assertAlmostEqual(end, 8.0)

    def test_geographic_bounds_overlap_handles_wraps_dateline_near_zero_longitude(self):
        """A wrapped longitude interval should still overlap neighbors near 0/360 degrees."""
        wrapped = GeoBounds(
            path="wrapped.cub",
            latitude_min=-5.0,
            latitude_max=5.0,
            longitude_start=350.0,
            longitude_end=8.0,
            wraps_dateline=True,
            valid_points=4,
            sampled_points=4,
        )
        nearby = GeoBounds(
            path="nearby.cub",
            latitude_min=-2.0,
            latitude_max=2.0,
            longitude_start=2.0,
            longitude_end=12.0,
            wraps_dateline=False,
            valid_points=4,
            sampled_points=4,
        )
        far = GeoBounds(
            path="far.cub",
            latitude_min=-2.0,
            latitude_max=2.0,
            longitude_start=20.0,
            longitude_end=30.0,
            wraps_dateline=False,
            valid_points=4,
            sampled_points=4,
        )

        self.assertTrue(geographic_bounds_overlap(wrapped, nearby))
        self.assertFalse(geographic_bounds_overlap(wrapped, far))

    def test_polar_stereo_bounds_from_samples_supports_north_and_south_polar_regions(self):
        """High-latitude samples should produce stable auxiliary bounds for both poles."""
        moon_radius_meters = 1_737_400.0

        north_bounds = _polar_stereo_bounds_from_samples(
            [82.0, 84.5, 86.0],
            [350.0, 355.0, 5.0],
            local_radius_meters=moon_radius_meters,
        )
        south_bounds = _polar_stereo_bounds_from_samples(
            [-82.0, -84.5, -86.0],
            [15.0, 35.0, 55.0],
            local_radius_meters=moon_radius_meters,
        )

        self.assertIsNotNone(north_bounds)
        self.assertEqual(north_bounds.pole, "north")
        self.assertLess(north_bounds.x_min, north_bounds.x_max)
        self.assertLess(north_bounds.y_min, north_bounds.y_max)
        self.assertAlmostEqual(north_bounds.mean_local_radius_meters, moon_radius_meters)

        self.assertIsNotNone(south_bounds)
        self.assertEqual(south_bounds.pole, "south")
        self.assertLess(south_bounds.x_min, south_bounds.x_max)
        self.assertLess(south_bounds.y_min, south_bounds.y_max)
        self.assertAlmostEqual(south_bounds.mean_local_radius_meters, moon_radius_meters)

    def test_select_polar_projection_pole_returns_expected_polar_zone(self):
        """High-latitude samples should resolve to the correct single polar zone."""
        self.assertEqual(_select_polar_projection_pole([80.0, 82.5, 85.0]), "north")
        self.assertEqual(_select_polar_projection_pole([-80.0, -82.5, -85.0]), "south")
        self.assertIsNone(_select_polar_projection_pole([10.0, 20.0, 30.0]))
        self.assertIsNone(_select_polar_projection_pole([85.0, -85.0]))

    def test_bounds_overlap_prefers_polar_auxiliary_bounds_over_geographic_fallback(self):
        """When both images have polar bounds, the polar overlap decision should win."""
        left = GeoBounds(
            path="left.cub",
            latitude_min=82.0,
            latitude_max=87.0,
            longitude_start=0.0,
            longitude_end=10.0,
            wraps_dateline=False,
            valid_points=4,
            sampled_points=4,
            polar_bounds=_polar_stereo_bounds_from_samples(
                [82.0, 84.0, 86.0],
                [0.0, 5.0, 10.0],
                local_radius_meters=1_737_400.0,
                pole="north",
            ),
        )
        right = GeoBounds(
            path="right.cub",
            latitude_min=82.5,
            latitude_max=87.5,
            longitude_start=0.0,
            longitude_end=10.0,
            wraps_dateline=False,
            valid_points=4,
            sampled_points=4,
            polar_bounds=_polar_stereo_bounds_from_samples(
                [82.5, 84.5, 86.5],
                [120.0, 125.0, 130.0],
                local_radius_meters=1_737_400.0,
                pole="north",
            ),
        )

        self.assertTrue(geographic_bounds_overlap(left, right))
        self.assertIsNotNone(left.polar_bounds)
        self.assertIsNotNone(right.polar_bounds)
        self.assertFalse(bounds_overlap(left, right))

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

    def test_stretch_to_byte_supports_configurable_real_lro_dom_cube_when_available(self):
        
        real_dom_cube = _configured_real_lro_stretch_dom_cube()
        if not real_dom_cube.exists():
            self.skipTest(
                "Real LRO DOM cube is unavailable. "
                f"Configure {REAL_LRO_STRETCH_DOM_CUBE_ENV} if you want to run the real-data stretch regression."
            )

        values = _read_center_cube_window(real_dom_cube, width=None, height=None)
        stretched, invalid_mask, stats = stretch_to_byte(values, lower_percent=0.5, upper_percent=99.5)
        valid_values = values[~invalid_mask]
        expected_minimum, expected_maximum = np.percentile(valid_values, [0.5, 99.5])
        
        print(f"Real LRO DOM Cube image path: {real_dom_cube.name}")
        print(stats)

        self.assertEqual(stretched.shape, values.shape)
        self.assertEqual(stretched.dtype, np.uint8)
        self.assertTrue(invalid_mask.any())
        self.assertGreater(stats.valid_pixel_count, 0)
        self.assertEqual(stats.valid_pixel_count + stats.invalid_pixel_count, values.size)
        self.assertEqual(stats.invalid_pixel_count, int(invalid_mask.sum()))
        self.assertAlmostEqual(stats.minimum_value, float(expected_minimum), places=12)
        self.assertAlmostEqual(stats.maximum_value, float(expected_maximum), places=12)
        self.assertTrue(np.all(stretched[invalid_mask] == 0))
        self.assertEqual(int(stretched[~invalid_mask].min()), 0)
        self.assertEqual(int(stretched[~invalid_mask].max()), 255)
        self.assertGreater(len(np.unique(stretched)), 32)
        self.assertGreater(int((stretched[~invalid_mask] == 0).sum()), 0)
        self.assertGreater(int((stretched[~invalid_mask] == 255).sum()), 0)


if __name__ == "__main__":
    unittest.main()