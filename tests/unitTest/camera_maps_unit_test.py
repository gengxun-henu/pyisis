"""
Unit tests for ISIS camera map bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-04-10
Updated: 2026-04-10  Geng Xun added PushFrameCameraDetectorMap, RollingShutterCameraDetectorMap, VariableLineScanCameraDetectorMap surface and API tests.
Updated: 2026-04-10  Geng Xun added GaussianStretch, PushFrameCameraGroundMap, RadarSkyMap, IrregularBodyCameraGroundMap, CSMSkyMap API tests.
Updated: 2026-04-10  Geng Xun added RadarGroundRangeMap, ReseauDistortionMap, MarciDistortionMap, RadarGroundMap, RadarPulseMap API tests.
Updated: 2026-04-10  Geng Xun added RadarSlantRangeMap API test.
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


class PushFrameCameraDetectorMapSurfaceUnitTest(unittest.TestCase):
    """Surface API tests for PushFrameCameraDetectorMap binding. Added: 2026-04-10."""

    def test_class_is_exported(self):
        """PushFrameCameraDetectorMap is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "PushFrameCameraDetectorMap"))

    def test_inherits_camera_detector_map(self):
        """PushFrameCameraDetectorMap is a subclass of CameraDetectorMap."""
        self.assertTrue(issubclass(ip.PushFrameCameraDetectorMap, ip.CameraDetectorMap))

    def test_has_expected_methods(self):
        """PushFrameCameraDetectorMap exposes required API methods."""
        self.assertTrue(hasattr(ip.PushFrameCameraDetectorMap, "set_parent"))
        self.assertTrue(hasattr(ip.PushFrameCameraDetectorMap, "set_detector"))
        self.assertTrue(hasattr(ip.PushFrameCameraDetectorMap, "framelet_rate"))
        self.assertTrue(hasattr(ip.PushFrameCameraDetectorMap, "set_framelet_rate"))
        self.assertTrue(hasattr(ip.PushFrameCameraDetectorMap, "framelet_offset"))
        self.assertTrue(hasattr(ip.PushFrameCameraDetectorMap, "set_framelet_offset"))
        self.assertTrue(hasattr(ip.PushFrameCameraDetectorMap, "framelet"))
        self.assertTrue(hasattr(ip.PushFrameCameraDetectorMap, "set_band_first_detector_line"))
        self.assertTrue(hasattr(ip.PushFrameCameraDetectorMap, "get_band_first_detector_line"))
        self.assertTrue(hasattr(ip.PushFrameCameraDetectorMap, "set_start_time"))


class RollingShutterCameraDetectorMapSurfaceUnitTest(unittest.TestCase):
    """Surface API tests for RollingShutterCameraDetectorMap binding. Added: 2026-04-10."""

    def test_class_is_exported(self):
        """RollingShutterCameraDetectorMap is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "RollingShutterCameraDetectorMap"))

    def test_inherits_camera_detector_map(self):
        """RollingShutterCameraDetectorMap is a subclass of CameraDetectorMap."""
        self.assertTrue(issubclass(ip.RollingShutterCameraDetectorMap, ip.CameraDetectorMap))

    def test_has_expected_methods(self):
        """RollingShutterCameraDetectorMap exposes required API methods."""
        self.assertTrue(hasattr(ip.RollingShutterCameraDetectorMap, "set_parent"))
        self.assertTrue(hasattr(ip.RollingShutterCameraDetectorMap, "set_detector"))
        self.assertTrue(hasattr(ip.RollingShutterCameraDetectorMap, "apply_jitter"))


class VariableLineScanCameraDetectorMapSurfaceUnitTest(unittest.TestCase):
    """Surface API tests for VariableLineScanCameraDetectorMap binding. Added: 2026-04-10."""

    def test_class_is_exported(self):
        """VariableLineScanCameraDetectorMap is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "VariableLineScanCameraDetectorMap"))

    def test_inherits_line_scan_camera_detector_map(self):
        """VariableLineScanCameraDetectorMap is a subclass of LineScanCameraDetectorMap."""
        self.assertTrue(issubclass(ip.VariableLineScanCameraDetectorMap, ip.LineScanCameraDetectorMap))

    def test_inherits_camera_detector_map(self):
        """VariableLineScanCameraDetectorMap is a subclass of CameraDetectorMap (transitive)."""
        self.assertTrue(issubclass(ip.VariableLineScanCameraDetectorMap, ip.CameraDetectorMap))

    def test_has_expected_methods(self):
        """VariableLineScanCameraDetectorMap exposes required API methods."""
        self.assertTrue(hasattr(ip.VariableLineScanCameraDetectorMap, "set_parent"))
        self.assertTrue(hasattr(ip.VariableLineScanCameraDetectorMap, "set_detector"))
        self.assertTrue(hasattr(ip.VariableLineScanCameraDetectorMap, "exposure_duration"))


class GaussianStretchApiTest(unittest.TestCase):
    """Tests for GaussianStretch binding. Added: 2026-04-10."""

    def _make_histogram(self, values):
        hist = ip.Histogram(min(values), max(values), len(values))
        hist.add_data(values)
        return hist

    def test_class_exists(self):
        """GaussianStretch is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "GaussianStretch"))

    def test_construction(self):
        """GaussianStretch constructs from a Histogram."""
        values = [float(i) for i in range(1, 11)]
        hist = self._make_histogram(values)
        gs = ip.GaussianStretch(hist)
        self.assertIsInstance(gs, ip.GaussianStretch)

    def test_map_returns_float(self):
        """GaussianStretch.map() returns a numeric value."""
        values = [float(i) for i in range(1, 101)]
        hist = self._make_histogram(values)
        gs = ip.GaussianStretch(hist)
        result = gs.map(50.0)
        self.assertIsInstance(result, float)

    def test_inherits_statistics(self):
        """GaussianStretch is a subclass of Statistics."""
        self.assertTrue(issubclass(ip.GaussianStretch, ip.Statistics))

    def test_repr(self):
        """repr(GaussianStretch) contains 'GaussianStretch'."""
        values = [float(i) for i in range(1, 11)]
        hist = self._make_histogram(values)
        gs = ip.GaussianStretch(hist)
        self.assertIn("GaussianStretch", repr(gs))


class PushFrameCameraGroundMapApiTest(unittest.TestCase):
    """Tests for PushFrameCameraGroundMap binding. Added: 2026-04-10."""

    def test_class_exists(self):
        """PushFrameCameraGroundMap is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "PushFrameCameraGroundMap"))

    def test_inherits_camera_ground_map(self):
        """PushFrameCameraGroundMap is a subclass of CameraGroundMap."""
        self.assertTrue(issubclass(ip.PushFrameCameraGroundMap, ip.CameraGroundMap))

    def test_has_set_ground(self):
        """PushFrameCameraGroundMap exposes set_ground method."""
        self.assertTrue(hasattr(ip.PushFrameCameraGroundMap, "set_ground"))


class RadarSkyMapApiTest(unittest.TestCase):
    """Tests for RadarSkyMap binding. Added: 2026-04-10."""

    def test_class_exists(self):
        """RadarSkyMap is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "RadarSkyMap"))

    def test_inherits_camera_sky_map(self):
        """RadarSkyMap is a subclass of CameraSkyMap."""
        self.assertTrue(issubclass(ip.RadarSkyMap, ip.CameraSkyMap))

    def test_has_expected_methods(self):
        """RadarSkyMap exposes set_focal_plane and set_sky."""
        self.assertTrue(hasattr(ip.RadarSkyMap, "set_focal_plane"))
        self.assertTrue(hasattr(ip.RadarSkyMap, "set_sky"))


class IrregularBodyCameraGroundMapApiTest(unittest.TestCase):
    """Tests for IrregularBodyCameraGroundMap binding. Added: 2026-04-10."""

    def test_class_exists(self):
        """IrregularBodyCameraGroundMap is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "IrregularBodyCameraGroundMap"))

    def test_inherits_camera_ground_map(self):
        """IrregularBodyCameraGroundMap is a subclass of CameraGroundMap."""
        self.assertTrue(issubclass(ip.IrregularBodyCameraGroundMap, ip.CameraGroundMap))

    def test_has_get_xy(self):
        """IrregularBodyCameraGroundMap exposes get_xy."""
        self.assertTrue(hasattr(ip.IrregularBodyCameraGroundMap, "get_xy"))


class CSMSkyMapApiTest(unittest.TestCase):
    """Tests for CSMSkyMap binding. Added: 2026-04-10."""

    def test_class_exists(self):
        """CSMSkyMap is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "CSMSkyMap"))

    def test_inherits_camera_sky_map(self):
        """CSMSkyMap is a subclass of CameraSkyMap."""
        self.assertTrue(issubclass(ip.CSMSkyMap, ip.CameraSkyMap))

    def test_has_set_sky(self):
        """CSMSkyMap exposes set_sky."""
        self.assertTrue(hasattr(ip.CSMSkyMap, "set_sky"))


class RadarLookDirectionApiTest(unittest.TestCase):
    """Tests for RadarLookDirection enum binding. Added: 2026-04-10."""

    def test_enum_exists(self):
        """RadarLookDirection enum is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "RadarLookDirection"))

    def test_has_left_right(self):
        """RadarLookDirection has Left and Right values."""
        self.assertTrue(hasattr(ip.RadarLookDirection, "Left"))
        self.assertTrue(hasattr(ip.RadarLookDirection, "Right"))


class RadarGroundRangeMapApiTest(unittest.TestCase):
    """Tests for RadarGroundRangeMap binding. Added: 2026-04-10."""

    def test_class_exists(self):
        """RadarGroundRangeMap is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "RadarGroundRangeMap"))

    def test_inherits_camera_focal_plane_map(self):
        """RadarGroundRangeMap is a subclass of CameraFocalPlaneMap."""
        self.assertTrue(issubclass(ip.RadarGroundRangeMap, ip.CameraFocalPlaneMap))

    def test_has_set_transform(self):
        """RadarGroundRangeMap exposes set_transform static method."""
        self.assertTrue(hasattr(ip.RadarGroundRangeMap, "set_transform"))


class ReseauDistortionMapApiTest(unittest.TestCase):
    """Tests for ReseauDistortionMap binding. Added: 2026-04-10."""

    def test_class_exists(self):
        """ReseauDistortionMap is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "ReseauDistortionMap"))

    def test_inherits_camera_distortion_map(self):
        """ReseauDistortionMap is a subclass of CameraDistortionMap."""
        self.assertTrue(issubclass(ip.ReseauDistortionMap, ip.CameraDistortionMap))

    def test_has_expected_methods(self):
        """ReseauDistortionMap exposes set_focal_plane and set_undistorted_focal_plane."""
        self.assertTrue(hasattr(ip.ReseauDistortionMap, "set_focal_plane"))
        self.assertTrue(hasattr(ip.ReseauDistortionMap, "set_undistorted_focal_plane"))


class MarciDistortionMapApiTest(unittest.TestCase):
    """Tests for MarciDistortionMap binding. Added: 2026-04-10."""

    def test_class_exists(self):
        """MarciDistortionMap is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "MarciDistortionMap"))

    def test_inherits_camera_distortion_map(self):
        """MarciDistortionMap is a subclass of CameraDistortionMap."""
        self.assertTrue(issubclass(ip.MarciDistortionMap, ip.CameraDistortionMap))

    def test_has_expected_methods(self):
        """MarciDistortionMap exposes set_focal_plane, set_undistorted_focal_plane, set_filter."""
        self.assertTrue(hasattr(ip.MarciDistortionMap, "set_focal_plane"))
        self.assertTrue(hasattr(ip.MarciDistortionMap, "set_undistorted_focal_plane"))
        self.assertTrue(hasattr(ip.MarciDistortionMap, "set_filter"))


class RadarGroundMapApiTest(unittest.TestCase):
    """Tests for RadarGroundMap binding. Added: 2026-04-10."""

    def test_class_exists(self):
        """RadarGroundMap is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "RadarGroundMap"))

    def test_inherits_camera_ground_map(self):
        """RadarGroundMap is a subclass of CameraGroundMap."""
        self.assertTrue(issubclass(ip.RadarGroundMap, ip.CameraGroundMap))

    def test_has_expected_methods(self):
        """RadarGroundMap exposes set_focal_plane, set_ground, sigma and wavelength methods."""
        self.assertTrue(hasattr(ip.RadarGroundMap, "set_focal_plane"))
        self.assertTrue(hasattr(ip.RadarGroundMap, "set_ground"))
        self.assertTrue(hasattr(ip.RadarGroundMap, "set_range_sigma"))
        self.assertTrue(hasattr(ip.RadarGroundMap, "range_sigma"))
        self.assertTrue(hasattr(ip.RadarGroundMap, "set_doppler_sigma"))
        self.assertTrue(hasattr(ip.RadarGroundMap, "y_scale"))
        self.assertTrue(hasattr(ip.RadarGroundMap, "wave_length"))


class RadarPulseMapApiTest(unittest.TestCase):
    """Tests for RadarPulseMap binding. Added: 2026-04-10."""

    def test_class_exists(self):
        """RadarPulseMap is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "RadarPulseMap"))

    def test_inherits_camera_detector_map(self):
        """RadarPulseMap is a subclass of CameraDetectorMap."""
        self.assertTrue(issubclass(ip.RadarPulseMap, ip.CameraDetectorMap))

    def test_has_expected_methods(self):
        """RadarPulseMap exposes start_time, line_rate, and axis-dependent methods."""
        self.assertTrue(hasattr(ip.RadarPulseMap, "set_start_time"))
        self.assertTrue(hasattr(ip.RadarPulseMap, "set_line_rate"))
        self.assertTrue(hasattr(ip.RadarPulseMap, "line_rate"))
        self.assertTrue(hasattr(ip.RadarPulseMap, "set_x_axis_time_dependent"))


if __name__ == "__main__":
    unittest.main()