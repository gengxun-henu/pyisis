"""
Unit tests for ISIS Stereo bindings.

Author: Geng Xun
Created: 2026-04-08
Last Modified: 2026-04-08
"""

import unittest

from _unit_test_support import ip


class StereoUnitTest(unittest.TestCase):
    def test_default_constructor_is_available(self):
        stereo = ip.Stereo()
        self.assertEqual(repr(stereo), "Stereo()")

    def test_spherical_matches_axis_aligned_case(self):
        x, y, z = ip.Stereo.spherical(0.0, 0.0, 1000.0)

        self.assertAlmostEqual(x, 1.0, places=12)
        self.assertAlmostEqual(y, 0.0, places=12)
        self.assertAlmostEqual(z, 0.0, places=12)

    def test_rectangular_matches_axis_aligned_case(self):
        latitude, longitude, radius = ip.Stereo.rectangular(1.0, 0.0, 0.0)

        self.assertAlmostEqual(latitude, 0.0, places=12)
        self.assertAlmostEqual(longitude, 0.0, places=12)
        self.assertAlmostEqual(radius, 1.0, places=12)

    def test_spherical_and_rectangular_round_trip_matches_upstream_units(self):
        latitude = 12.5
        longitude = 215.0
        radius_meters = 3_396_190.0

        x, y, z = ip.Stereo.spherical(latitude, longitude, radius_meters)
        round_trip_latitude, round_trip_longitude, round_trip_radius = ip.Stereo.rectangular(x, y, z)

        self.assertAlmostEqual(round_trip_latitude, latitude, places=10)
        self.assertAlmostEqual(round_trip_longitude, longitude, places=10)
        self.assertAlmostEqual(round_trip_radius, radius_meters / 1000.0, places=10)

    def test_polar_case_maps_to_positive_z_axis(self):
        x, y, z = ip.Stereo.spherical(90.0, 45.0, 2000.0)

        self.assertAlmostEqual(x, 0.0, places=12)
        self.assertAlmostEqual(y, 0.0, places=12)
        self.assertAlmostEqual(z, 2.0, places=12)

    def test_elevation_entry_point_is_exposed(self):
        self.assertTrue(hasattr(ip.Stereo, "elevation"))
        self.assertTrue(callable(ip.Stereo.elevation))


if __name__ == "__main__":
    unittest.main()