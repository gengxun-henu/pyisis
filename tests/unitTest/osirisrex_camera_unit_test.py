"""
Unit tests for ISIS OSIRIS-REx mission camera bindings

Author: Geng Xun
Created: 2026-04-07
Last Modified: 2026-04-07
"""

import unittest

from _unit_test_support import ip


class OsirisRexOcamsCameraBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for OSIRIS-REx OCAMS camera binding surfaces."""

    def test_osiris_rex_ocams_camera_is_importable(self):
        self.assertTrue(hasattr(ip, "OsirisRexOcamsCamera"))

    def test_osiris_rex_ocams_camera_inherits_framing_camera(self):
        self.assertTrue(issubclass(ip.OsirisRexOcamsCamera, ip.FramingCamera))

    def test_osiris_rex_ocams_camera_methods_exist(self):
        self.assertTrue(hasattr(ip.OsirisRexOcamsCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.OsirisRexOcamsCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.OsirisRexOcamsCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.OsirisRexOcamsCamera, "spk_reference_id"))


class OsirisRexDistortionMapBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for OSIRIS-REx OCAMS distortion map binding surfaces."""

    def test_osiris_rex_distortion_map_is_importable(self):
        self.assertTrue(hasattr(ip, "OsirisRexDistortionMap"))

    def test_osiris_rex_distortion_map_inherits_camera_distortion_map(self):
        self.assertTrue(
            issubclass(ip.OsirisRexDistortionMap, ip.CameraDistortionMap)
        )

    def test_osiris_rex_distortion_map_methods_exist(self):
        self.assertTrue(hasattr(ip.OsirisRexDistortionMap, "set_distortion"))
        self.assertTrue(hasattr(ip.OsirisRexDistortionMap, "set_focal_plane"))
        self.assertTrue(
            hasattr(ip.OsirisRexDistortionMap, "set_undistorted_focal_plane")
        )
        self.assertTrue(hasattr(ip.OsirisRexDistortionMap, "__repr__"))

    def test_osiris_rex_distortion_map_inherits_base_methods(self):
        """Inherited from CameraDistortionMap base class."""
        self.assertTrue(hasattr(ip.OsirisRexDistortionMap, "focal_plane_x"))
        self.assertTrue(hasattr(ip.OsirisRexDistortionMap, "focal_plane_y"))
        self.assertTrue(
            hasattr(ip.OsirisRexDistortionMap, "undistorted_focal_plane_x")
        )
        self.assertTrue(
            hasattr(ip.OsirisRexDistortionMap, "undistorted_focal_plane_y")
        )


class OsirisRexTagcamsCameraBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for OSIRIS-REx TAGCAMS camera binding surfaces."""

    def test_osiris_rex_tagcams_camera_is_importable(self):
        self.assertTrue(hasattr(ip, "OsirisRexTagcamsCamera"))

    def test_osiris_rex_tagcams_camera_inherits_framing_camera(self):
        self.assertTrue(issubclass(ip.OsirisRexTagcamsCamera, ip.FramingCamera))

    def test_osiris_rex_tagcams_camera_methods_exist(self):
        self.assertTrue(hasattr(ip.OsirisRexTagcamsCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.OsirisRexTagcamsCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.OsirisRexTagcamsCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.OsirisRexTagcamsCamera, "spk_reference_id"))


class OsirisRexTagcamsDistortionMapBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for OSIRIS-REx TAGCAMS distortion map binding surfaces."""

    def test_osiris_rex_tagcams_distortion_map_is_importable(self):
        self.assertTrue(hasattr(ip, "OsirisRexTagcamsDistortionMap"))

    def test_osiris_rex_tagcams_distortion_map_inherits_camera_distortion_map(self):
        self.assertTrue(
            issubclass(ip.OsirisRexTagcamsDistortionMap, ip.CameraDistortionMap)
        )

    def test_osiris_rex_tagcams_distortion_map_methods_exist(self):
        self.assertTrue(
            hasattr(ip.OsirisRexTagcamsDistortionMap, "set_camera_temperature")
        )
        self.assertTrue(hasattr(ip.OsirisRexTagcamsDistortionMap, "set_focal_plane"))
        self.assertTrue(
            hasattr(ip.OsirisRexTagcamsDistortionMap, "set_undistorted_focal_plane")
        )
        self.assertTrue(hasattr(ip.OsirisRexTagcamsDistortionMap, "__repr__"))

    def test_osiris_rex_tagcams_distortion_map_inherits_base_methods(self):
        """Inherited from CameraDistortionMap base class."""
        self.assertTrue(
            hasattr(ip.OsirisRexTagcamsDistortionMap, "focal_plane_x")
        )
        self.assertTrue(
            hasattr(ip.OsirisRexTagcamsDistortionMap, "focal_plane_y")
        )
        self.assertTrue(
            hasattr(ip.OsirisRexTagcamsDistortionMap, "undistorted_focal_plane_x")
        )
        self.assertTrue(
            hasattr(ip.OsirisRexTagcamsDistortionMap, "undistorted_focal_plane_y")
        )


if __name__ == "__main__":
    unittest.main()
