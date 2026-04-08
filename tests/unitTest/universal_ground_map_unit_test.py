"""
Unit tests for ISIS UniversalGroundMap bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-03-25
Updated: 2026-03-25  Geng Xun added camera-backed and projection-backed UniversalGroundMap round-trip coverage.
"""

import math
import unittest

from _unit_test_support import ip, workspace_test_data_path


CAMERA_CUBE = workspace_test_data_path("mosrange", "EN0108828322M_iof.cub")
PROJECTED_CUBE = workspace_test_data_path(
    "map2map", "WAC_GLD100_V1.0_GLOBAL_with_LOLA_30M_POLE.10km_cropped.cub"
)


class UniversalGroundMapUnitTest(unittest.TestCase):
    def open_cube(self, path):
        cube = ip.Cube()
        cube.open(str(path), "r")
        self.addCleanup(cube.close)
        return cube

    def test_camera_backed_ground_map_round_trip(self):
        cube = self.open_cube(CAMERA_CUBE)
        ground_map = ip.UniversalGroundMap(cube)

        self.assertTrue(ground_map.has_camera())
        self.assertFalse(ground_map.has_projection())
        self.assertIsInstance(ground_map.camera(), ip.Camera)
        self.assertIsNone(ground_map.projection())

        center_sample = cube.sample_count() / 2.0
        center_line = cube.line_count() / 2.0
        self.assertTrue(ground_map.set_image(center_sample, center_line))

        latitude = ground_map.universal_latitude()
        longitude = ground_map.universal_longitude()
        self.assertTrue(math.isfinite(latitude))
        self.assertTrue(math.isfinite(longitude))
        self.assertGreater(ground_map.resolution(), 0.0)

        ground_map.set_band(1)
        self.assertTrue(ground_map.set_universal_ground(latitude, longitude))
        self.assertAlmostEqual(ground_map.sample(), center_sample, places=3)
        self.assertAlmostEqual(ground_map.line(), center_line, places=3)

        surface_point = ground_map.camera().get_surface_point()
        self.assertTrue(surface_point.valid())
        self.assertTrue(ground_map.set_ground(surface_point))

    def test_projection_backed_ground_map_round_trip(self):
        cube = self.open_cube(PROJECTED_CUBE)
        ground_map = ip.UniversalGroundMap(cube)

        self.assertFalse(ground_map.has_camera())
        self.assertTrue(ground_map.has_projection())
        self.assertIsNone(ground_map.camera())
        self.assertIsInstance(ground_map.projection(), ip.Projection)

        sample = 100.0
        line = 100.0
        self.assertTrue(ground_map.set_image(sample, line))

        latitude = ground_map.universal_latitude()
        longitude = ground_map.universal_longitude()
        self.assertTrue(math.isfinite(latitude))
        self.assertTrue(math.isfinite(longitude))
        self.assertGreater(ground_map.resolution(), 0.0)

        self.assertTrue(ground_map.set_universal_ground(latitude, longitude))
        self.assertAlmostEqual(ground_map.sample(), sample, places=6)
        self.assertAlmostEqual(ground_map.line(), line, places=6)

        projection = ground_map.projection()
        self.assertFalse(projection.has_ground_range())

        # The projected cube fixture does not expose an intrinsic ground range.
        # Asking UniversalGroundMap to estimate one from the cube perimeter can
        # become prohibitively expensive for this dataset, so keep the test on
        # the stable, non-estimating path.
        self.assertIsNone(ground_map.ground_range(cube, False))

        self.assertTrue(projection.set_universal_ground(latitude, longitude))
        self.assertAlmostEqual(projection.world_x(), sample, places=6)
        self.assertAlmostEqual(projection.world_y(), line, places=6)


if __name__ == "__main__":
    unittest.main()