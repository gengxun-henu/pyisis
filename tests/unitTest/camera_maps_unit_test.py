"""
Unit tests for ISIS camera map bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-03-21
"""

import math
import unittest

from _unit_test_support import DEGREES, ip, workspace_test_data_path


MDIS_CUBE = workspace_test_data_path("mosrange", "EN0108828322M_iof.cub")


class CameraMapsUnitTest(unittest.TestCase):
    def open_cube(self, path):
        cube = ip.Cube()
        cube.open(str(path), "r")
        self.addCleanup(cube.close)
        return cube

    def open_camera_with_center_geometry(self):
        cube = self.open_cube(MDIS_CUBE)
        camera = cube.camera()
        center_sample = camera.samples() / 2.0
        center_line = camera.lines() / 2.0
        self.assertTrue(camera.set_image(center_sample, center_line))
        return cube, camera, center_sample, center_line

    def test_camera_exposes_base_map_accessors(self):
        _, camera, _, _ = self.open_camera_with_center_geometry()

        self.assertIsInstance(camera.distortion_map(), ip.CameraDistortionMap)
        self.assertIsInstance(camera.detector_map(), ip.CameraDetectorMap)
        self.assertIsInstance(camera.focal_plane_map(), ip.CameraFocalPlaneMap)
        self.assertIsInstance(camera.ground_map(), ip.CameraGroundMap)
        self.assertIsInstance(camera.sky_map(), ip.CameraSkyMap)

    def test_distortion_map_round_trip_local_mdis_geometry(self):
        _, camera, center_sample, center_line = self.open_camera_with_center_geometry()
        detector_map = camera.detector_map()
        focal_plane_map = camera.focal_plane_map()
        distortion_map = camera.distortion_map()

        self.assertTrue(detector_map.set_parent(center_sample, center_line))
        self.assertTrue(
            focal_plane_map.set_detector(
                detector_map.detector_sample(),
                detector_map.detector_line(),
            )
        )

        distorted_x = focal_plane_map.focal_plane_x()
        distorted_y = focal_plane_map.focal_plane_y()
        self.assertTrue(distortion_map.set_focal_plane(distorted_x, distorted_y))
        self.assertTrue(math.isfinite(distortion_map.undistorted_focal_plane_x()))
        self.assertTrue(math.isfinite(distortion_map.undistorted_focal_plane_y()))
        self.assertTrue(math.isfinite(distortion_map.undistorted_focal_plane_z()))

        undistorted_x = distortion_map.undistorted_focal_plane_x()
        undistorted_y = distortion_map.undistorted_focal_plane_y()
        self.assertTrue(distortion_map.set_undistorted_focal_plane(undistorted_x, undistorted_y))
        self.assertAlmostEqual(distortion_map.focal_plane_x(), distorted_x, places=6)
        self.assertAlmostEqual(distortion_map.focal_plane_y(), distorted_y, places=6)
        coefficients = distortion_map.optical_distortion_coefficients()
        self.assertIsInstance(coefficients, list)
        self.assertIn(distortion_map.z_direction(), (-1.0, 1.0))

    def test_detector_and_focal_plane_maps_round_trip_local_mdis_geometry(self):
        _, camera, center_sample, center_line = self.open_camera_with_center_geometry()
        detector_map = camera.detector_map()
        focal_plane_map = camera.focal_plane_map()

        self.assertTrue(detector_map.set_parent(center_sample, center_line))
        self.assertAlmostEqual(detector_map.parent_sample(), center_sample, places=6)
        self.assertAlmostEqual(detector_map.parent_line(), center_line, places=6)
        self.assertTrue(math.isfinite(detector_map.detector_sample()))
        self.assertTrue(math.isfinite(detector_map.detector_line()))
        self.assertGreater(detector_map.sample_scale_factor(), 0.0)
        self.assertGreater(detector_map.line_scale_factor(), 0.0)

        detector_sample = detector_map.detector_sample()
        detector_line = detector_map.detector_line()
        self.assertTrue(focal_plane_map.set_detector(detector_sample, detector_line))
        self.assertTrue(math.isfinite(focal_plane_map.focal_plane_x()))
        self.assertTrue(math.isfinite(focal_plane_map.focal_plane_y()))

        focal_plane_x = focal_plane_map.focal_plane_x()
        focal_plane_y = focal_plane_map.focal_plane_y()
        self.assertTrue(focal_plane_map.set_focal_plane(focal_plane_x, focal_plane_y))
        self.assertAlmostEqual(focal_plane_map.detector_sample(), detector_sample, places=6)
        self.assertAlmostEqual(focal_plane_map.detector_line(), detector_line, places=6)
        self.assertEqual(len(focal_plane_map.trans_x()), 3)
        self.assertEqual(len(focal_plane_map.trans_y()), 3)
        self.assertEqual(len(focal_plane_map.trans_s()), 3)
        self.assertEqual(len(focal_plane_map.trans_l()), 3)
        self.assertIn(focal_plane_map.focal_plane_x_dependency(), (1, 2))
        self.assertIn(focal_plane_map.sign_most_sig_x(), (-1.0, 1.0))
        self.assertIn(focal_plane_map.sign_most_sig_y(), (-1.0, 1.0))

    def test_detector_map_exposure_duration_raises_for_framing_case(self):
        _, camera, center_sample, center_line = self.open_camera_with_center_geometry()
        detector_map = camera.detector_map()
        detector_map.set_parent(center_sample, center_line)

        with self.assertRaises(Exception):
            detector_map.exposure_duration(center_sample, center_line, 1)

    def test_line_scan_detector_map_standalone_configuration(self):
        detector_map = ip.LineScanCameraDetectorMap(None, 123.5, 2.6)

        self.assertIsInstance(detector_map, ip.CameraDetectorMap)
        self.assertAlmostEqual(detector_map.start_time(), 123.5)
        self.assertAlmostEqual(detector_map.line_rate(), 2.6)
        self.assertAlmostEqual(detector_map.exposure_duration(1.0, 1.0, 1), 2.6)

        detector_map.set_start_time(456.25)
        detector_map.set_line_rate(1.75)
        self.assertAlmostEqual(detector_map.start_time(), 456.25)
        self.assertAlmostEqual(detector_map.line_rate(), 1.75)
        self.assertAlmostEqual(detector_map.exposure_duration(5.0, 10.0, 1), 1.75)

    def test_ground_and_sky_maps_accept_camera_derived_geometry(self):
        _, camera, _, _ = self.open_camera_with_center_geometry()
        ground_map = camera.ground_map()
        sky_map = camera.sky_map()

        latitude = ip.Latitude(camera.universal_latitude(), DEGREES)
        longitude = ip.Longitude(camera.universal_longitude(), DEGREES)
        self.assertTrue(ground_map.set_ground(latitude, longitude))
        self.assertTrue(math.isfinite(ground_map.focal_plane_x()))
        self.assertTrue(math.isfinite(ground_map.focal_plane_y()))

        self.assertTrue(sky_map.set_sky(camera.right_ascension(), camera.declination()))
        self.assertTrue(math.isfinite(sky_map.focal_plane_x()))
        self.assertTrue(math.isfinite(sky_map.focal_plane_y()))


if __name__ == "__main__":
    unittest.main()