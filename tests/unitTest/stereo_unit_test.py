"""
Unit tests for ISIS Stereo bindings.

Author: Geng Xun
Created: 2026-04-08
Last Modified: 2026-04-08
"""

import unittest

from _unit_test_support import ip, workspace_test_data_path


MDIS_CUBES = [
    workspace_test_data_path("mosrange", "EN0108828322M_iof.cub"),
    workspace_test_data_path("mosrange", "EN0108828327M_iof.cub"),
]


class StereoUnitTest(unittest.TestCase):
    def open_cube(self, path):
        cube = ip.Cube()
        cube.open(str(path), "r")
        self.addCleanup(cube.close)
        return cube

    def initialize_camera_at_center(self, camera):
        center_sample = camera.samples() / 2.0
        center_line = camera.lines() / 2.0
        self.assertTrue(camera.set_image(center_sample, center_line))
        self.assertTrue(camera.has_surface_intersection())

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

    def test_elevation_raises_when_both_cameras_lack_surface_intersections(self):
        cube1 = self.open_cube(MDIS_CUBES[0])
        cube2 = self.open_cube(MDIS_CUBES[1])
        cam1 = cube1.camera()
        cam2 = cube2.camera()

        self.assertFalse(cam1.has_surface_intersection())
        self.assertFalse(cam2.has_surface_intersection())

        with self.assertRaisesRegex(ip.IException, "cam1 and cam2 do not have valid surface intersections"):
            ip.Stereo.elevation(cam1, cam2)

    def test_elevation_raises_when_cam1_lacks_surface_intersection(self):
        cube1 = self.open_cube(MDIS_CUBES[0])
        cube2 = self.open_cube(MDIS_CUBES[1])
        cam1 = cube1.camera()
        cam2 = cube2.camera()

        self.initialize_camera_at_center(cam2)
        self.assertFalse(cam1.has_surface_intersection())

        with self.assertRaisesRegex(ip.IException, "cam1 does not have a valid surface intersection"):
            ip.Stereo.elevation(cam1, cam2)

    def test_elevation_raises_when_cam2_lacks_surface_intersection(self):
        cube1 = self.open_cube(MDIS_CUBES[0])
        cube2 = self.open_cube(MDIS_CUBES[1])
        cam1 = cube1.camera()
        cam2 = cube2.camera()

        self.initialize_camera_at_center(cam1)
        self.assertFalse(cam2.has_surface_intersection())

        with self.assertRaisesRegex(ip.IException, "cam2 does not have a valid surface intersection"):
            ip.Stereo.elevation(cam1, cam2)


if __name__ == "__main__":
    unittest.main()