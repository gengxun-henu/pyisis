"""
Unit tests for ISIS Rosetta mission camera bindings

Author: Geng Xun
Created: 2026-04-07
Last Modified: 2026-04-07
"""

import unittest

from _unit_test_support import ip


class RosettaOsirisCameraBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for Rosetta OSIRIS camera binding surfaces."""

    def test_rosetta_osiris_camera_is_importable(self):
        self.assertTrue(hasattr(ip, "RosettaOsirisCamera"))

    def test_rosetta_osiris_camera_inherits_framing_camera(self):
        self.assertTrue(issubclass(ip.RosettaOsirisCamera, ip.FramingCamera))

    def test_rosetta_osiris_camera_methods_exist(self):
        self.assertTrue(hasattr(ip.RosettaOsirisCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.RosettaOsirisCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.RosettaOsirisCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.RosettaOsirisCamera, "spk_reference_id"))


class RosettaOsirisCameraDistortionMapBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for Rosetta OSIRIS distortion map binding surfaces."""

    def test_rosetta_osiris_distortion_map_is_importable(self):
        self.assertTrue(hasattr(ip, "RosettaOsirisCameraDistortionMap"))

    def test_rosetta_osiris_distortion_map_inherits_camera_distortion_map(self):
        self.assertTrue(
            issubclass(ip.RosettaOsirisCameraDistortionMap, ip.CameraDistortionMap)
        )

    def test_rosetta_osiris_distortion_map_methods_exist(self):
        self.assertTrue(
            hasattr(ip.RosettaOsirisCameraDistortionMap, "set_focal_plane")
        )
        self.assertTrue(
            hasattr(ip.RosettaOsirisCameraDistortionMap, "set_undistorted_focal_plane")
        )
        self.assertTrue(
            hasattr(ip.RosettaOsirisCameraDistortionMap, "set_un_distorted_x_matrix")
        )
        self.assertTrue(
            hasattr(ip.RosettaOsirisCameraDistortionMap, "set_un_distorted_y_matrix")
        )
        self.assertTrue(
            hasattr(ip.RosettaOsirisCameraDistortionMap, "set_boresight")
        )
        self.assertTrue(
            hasattr(ip.RosettaOsirisCameraDistortionMap, "set_pixel_pitch")
        )
        self.assertTrue(hasattr(ip.RosettaOsirisCameraDistortionMap, "__repr__"))

    def test_rosetta_osiris_distortion_map_inherits_base_methods(self):
        """Inherited from CameraDistortionMap base class."""
        self.assertTrue(
            hasattr(ip.RosettaOsirisCameraDistortionMap, "focal_plane_x")
        )
        self.assertTrue(
            hasattr(ip.RosettaOsirisCameraDistortionMap, "focal_plane_y")
        )
        self.assertTrue(
            hasattr(
                ip.RosettaOsirisCameraDistortionMap, "undistorted_focal_plane_x"
            )
        )
        self.assertTrue(
            hasattr(
                ip.RosettaOsirisCameraDistortionMap, "undistorted_focal_plane_y"
            )
        )


class RosettaVirtisCameraBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for Rosetta VIRTIS camera binding surfaces."""

    def test_rosetta_virtis_camera_is_importable(self):
        self.assertTrue(hasattr(ip, "RosettaVirtisCamera"))

    def test_rosetta_virtis_camera_inherits_line_scan_camera(self):
        self.assertTrue(issubclass(ip.RosettaVirtisCamera, ip.LineScanCamera))

    def test_rosetta_virtis_camera_methods_exist(self):
        self.assertTrue(hasattr(ip.RosettaVirtisCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.RosettaVirtisCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.RosettaVirtisCamera, "spk_reference_id"))


if __name__ == "__main__":
    unittest.main()
