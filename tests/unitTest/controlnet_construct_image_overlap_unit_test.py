"""Focused unit tests for controlnet image-overlap helper geometry.

Author: Geng Xun
Created: 2026-04-18
Last Modified: 2026-04-18
Updated: 2026-04-18  Geng Xun added regression coverage for 0/360° wrap handling, strict boundary semantics, Polar Stereographic fallback bounds, and 11x11 default sampling.
"""

from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.image_overlap import (
    DEFAULT_GRID_LINES,
    DEFAULT_GRID_SAMPLES,
    GeoBounds,
    PolarStereoBounds,
    _expand_interval,
    _linspace_positions,
    _minimal_longitude_interval,
    _polar_stereo_bounds_from_samples,
    _select_polar_projection_pole,
    bounds_overlap,
    build_argument_parser,
    geographic_bounds_overlap,
)


def _geo_bounds(
    path: str,
    latitude_min: float,
    latitude_max: float,
    longitude_start: float,
    longitude_end: float,
    wraps_dateline: bool,
    *,
    polar_bounds: PolarStereoBounds | None = None,
) -> GeoBounds:
    return GeoBounds(
        path=path,
        latitude_min=latitude_min,
        latitude_max=latitude_max,
        longitude_start=longitude_start,
        longitude_end=longitude_end,
        wraps_dateline=wraps_dateline,
        valid_points=9,
        sampled_points=121,
        polar_bounds=polar_bounds,
    )


class ControlNetConstructImageOverlapUnitTest(unittest.TestCase):
    def test_minimal_longitude_interval_detects_dateline_wrap(self):
        start, end, wraps = _minimal_longitude_interval([359.0, 0.5, 1.2])

        self.assertTrue(wraps)
        self.assertAlmostEqual(start, 359.0)
        self.assertAlmostEqual(end, 1.2)

    def test_expand_interval_splits_wrapped_longitudes(self):
        self.assertEqual(_expand_interval(359.0, 1.0, True), [(359.0, 360.0), (0.0, 1.0)])

    def test_geographic_overlap_detects_dateline_overlap(self):
        left = _geo_bounds("left", -10.0, 10.0, 359.0, 1.0, True)
        right = _geo_bounds("right", -5.0, 5.0, 0.2, 0.8, False)

        self.assertTrue(geographic_bounds_overlap(left, right))

    def test_geographic_overlap_rejects_longitude_boundary_touch(self):
        left = _geo_bounds("left", -10.0, 10.0, 359.0, 1.0, True)
        right = _geo_bounds("right", -5.0, 5.0, 1.0, 20.0, False)

        self.assertFalse(geographic_bounds_overlap(left, right))

    def test_geographic_overlap_rejects_latitude_boundary_touch(self):
        left = _geo_bounds("left", -10.0, 0.0, 10.0, 20.0, False)
        right = _geo_bounds("right", 0.0, 15.0, 12.0, 18.0, False)

        self.assertFalse(geographic_bounds_overlap(left, right))

    def test_geographic_overlap_tolerance_can_bridge_small_gap(self):
        left = _geo_bounds("left", -10.0, 10.0, 359.0, 0.95, True)
        right = _geo_bounds("right", -5.0, 5.0, 1.0, 20.0, False)

        self.assertFalse(geographic_bounds_overlap(left, right, tolerance=0.0))
        self.assertTrue(geographic_bounds_overlap(left, right, tolerance=0.1))

    def test_linspace_positions_with_eleven_samples_hits_edges_and_midpoint(self):
        positions = _linspace_positions(101, 11)

        self.assertEqual(len(positions), 11)
        self.assertAlmostEqual(positions[0], 1.0)
        self.assertAlmostEqual(positions[5], 51.0)
        self.assertAlmostEqual(positions[-1], 101.0)

    def test_argument_parser_defaults_to_eleven_by_eleven_sampling(self):
        parser = build_argument_parser()
        args = parser.parse_args(["input.lis", "output.lis"])

        self.assertEqual(args.grid_samples, DEFAULT_GRID_SAMPLES)
        self.assertEqual(args.grid_lines, DEFAULT_GRID_LINES)
        self.assertEqual(DEFAULT_GRID_SAMPLES, 11)
        self.assertEqual(DEFAULT_GRID_LINES, 11)

    def test_select_polar_projection_pole_distinguishes_north_and_south(self):
        self.assertEqual(_select_polar_projection_pole([82.0, 84.0, 79.0]), "north")
        self.assertEqual(_select_polar_projection_pole([-88.0, -81.0, -75.0]), "south")
        self.assertIsNone(_select_polar_projection_pole([30.0, 40.0, 50.0]))

    def test_polar_stereo_bounds_from_samples_projects_south_pole_points(self):
        bounds = _polar_stereo_bounds_from_samples(
            [-89.2, -89.0, -88.8],
            [355.0, 0.0, 5.0],
            local_radius_meters=1_737_400.0,
        )

        self.assertIsNotNone(bounds)
        assert bounds is not None
        self.assertEqual(bounds.pole, "south")
        self.assertTrue(math.isfinite(bounds.x_min))
        self.assertTrue(math.isfinite(bounds.x_max))
        self.assertTrue(math.isfinite(bounds.y_min))
        self.assertTrue(math.isfinite(bounds.y_max))
        self.assertLess(bounds.x_min, bounds.x_max)
        self.assertLess(bounds.y_min, bounds.y_max)

    def test_bounds_overlap_uses_polar_projection_when_available(self):
        left_polar = _polar_stereo_bounds_from_samples(
            [-89.2, -89.0, -88.8],
            [355.0, 0.0, 5.0],
            local_radius_meters=1_737_400.0,
        )
        right_polar = _polar_stereo_bounds_from_samples(
            [-89.1, -88.95, -88.7],
            [358.0, 3.0, 8.0],
            local_radius_meters=1_737_400.0,
        )

        assert left_polar is not None
        assert right_polar is not None

        left = _geo_bounds("left", -89.2, -88.8, 355.0, 5.0, True, polar_bounds=left_polar)
        right = _geo_bounds("right", -89.1, -88.7, 358.0, 8.0, True, polar_bounds=right_polar)

        self.assertTrue(bounds_overlap(left, right))

    def test_bounds_overlap_rejects_polar_boundary_only_contact(self):
        left = _geo_bounds(
            "left",
            -89.5,
            -88.5,
            350.0,
            10.0,
            True,
            polar_bounds=PolarStereoBounds(
                pole="south",
                x_min=-10.0,
                x_max=0.0,
                y_min=-5.0,
                y_max=5.0,
                mean_local_radius_meters=1_737_400.0,
            ),
        )
        right = _geo_bounds(
            "right",
            -89.5,
            -88.5,
            5.0,
            20.0,
            False,
            polar_bounds=PolarStereoBounds(
                pole="south",
                x_min=0.0,
                x_max=8.0,
                y_min=-5.0,
                y_max=5.0,
                mean_local_radius_meters=1_737_400.0,
            ),
        )

        self.assertFalse(bounds_overlap(left, right))


if __name__ == "__main__":
    unittest.main()