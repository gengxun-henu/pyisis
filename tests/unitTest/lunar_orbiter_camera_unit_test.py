"""
Unit tests for ISIS Lunar Orbiter camera bindings

Author: Geng Xun
Created: 2026-04-07
Last Modified: 2026-04-07
"""

import unittest

from _unit_test_support import ip


class LoCameraFiducialMapBindingsUnitTest(unittest.TestCase):
    """Regression coverage for Lunar Orbiter fiducial map helper binding."""

    def test_lo_camera_fiducial_map_is_importable(self):
        self.assertTrue(hasattr(ip, "LoCameraFiducialMap"))

    def test_lo_camera_fiducial_map_has_repr(self):
        self.assertTrue(hasattr(ip.LoCameraFiducialMap, "__repr__"))


class LoHighCameraBindingsUnitTest(unittest.TestCase):
    """Regression coverage for Lunar Orbiter high-resolution camera binding."""

    def test_lo_high_camera_is_importable(self):
        self.assertTrue(hasattr(ip, "LoHighCamera"))

    def test_lo_high_camera_inherits_framing_camera(self):
        self.assertTrue(issubclass(ip.LoHighCamera, ip.FramingCamera))

    def test_lo_high_camera_methods_exist(self):
        self.assertTrue(hasattr(ip.LoHighCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.LoHighCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.LoHighCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.LoHighCamera, "spk_reference_id"))


class LoHighDistortionMapBindingsUnitTest(unittest.TestCase):
    """Regression coverage for Lunar Orbiter high-resolution distortion map binding."""

    def test_lo_high_distortion_map_is_importable(self):
        self.assertTrue(hasattr(ip, "LoHighDistortionMap"))

    def test_lo_high_distortion_map_inherits_camera_distortion_map(self):
        self.assertTrue(issubclass(ip.LoHighDistortionMap, ip.CameraDistortionMap))

    def test_lo_high_distortion_map_methods_exist(self):
        self.assertTrue(hasattr(ip.LoHighDistortionMap, "set_distortion"))
        self.assertTrue(hasattr(ip.LoHighDistortionMap, "set_focal_plane"))
        self.assertTrue(hasattr(ip.LoHighDistortionMap, "set_undistorted_focal_plane"))
        self.assertTrue(hasattr(ip.LoHighDistortionMap, "__repr__"))


class LoMediumCameraBindingsUnitTest(unittest.TestCase):
    """Regression coverage for Lunar Orbiter medium-resolution camera binding."""

    def test_lo_medium_camera_is_importable(self):
        self.assertTrue(hasattr(ip, "LoMediumCamera"))

    def test_lo_medium_camera_inherits_framing_camera(self):
        self.assertTrue(issubclass(ip.LoMediumCamera, ip.FramingCamera))

    def test_lo_medium_camera_methods_exist(self):
        self.assertTrue(hasattr(ip.LoMediumCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.LoMediumCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.LoMediumCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.LoMediumCamera, "spk_reference_id"))

    def test_lo_medium_camera_focal_plane_map_type_enum_exists(self):
        self.assertTrue(hasattr(ip.LoMediumCamera, "FocalPlaneMapType"))
        self.assertTrue(hasattr(ip.LoMediumCamera.FocalPlaneMapType, "Fiducial"))
        self.assertTrue(hasattr(ip.LoMediumCamera.FocalPlaneMapType, "Boresight"))
        self.assertTrue(hasattr(ip.LoMediumCamera.FocalPlaneMapType, "None"))


class LoMediumDistortionMapBindingsUnitTest(unittest.TestCase):
    """Regression coverage for Lunar Orbiter medium-resolution distortion map binding."""

    def test_lo_medium_distortion_map_is_importable(self):
        self.assertTrue(hasattr(ip, "LoMediumDistortionMap"))

    def test_lo_medium_distortion_map_inherits_camera_distortion_map(self):
        self.assertTrue(
            issubclass(ip.LoMediumDistortionMap, ip.CameraDistortionMap)
        )

    def test_lo_medium_distortion_map_methods_exist(self):
        self.assertTrue(hasattr(ip.LoMediumDistortionMap, "set_distortion"))
        self.assertTrue(hasattr(ip.LoMediumDistortionMap, "set_focal_plane"))
        self.assertTrue(
            hasattr(ip.LoMediumDistortionMap, "set_undistorted_focal_plane")
        )
        self.assertTrue(hasattr(ip.LoMediumDistortionMap, "__repr__"))


if __name__ == "__main__":
    unittest.main()
