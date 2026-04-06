"""
Unit tests for ISIS TGO (Trace Gas Orbiter) CaSSIS mission camera bindings

Author: Geng Xun
Created: 2026-04-06
Last Modified: 2026-04-06
"""

import unittest

from _unit_test_support import ip


class TgoCassisCameraBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for TGO CaSSIS camera binding surfaces."""

    def test_tgo_cassis_camera_is_importable(self):
        self.assertTrue(hasattr(ip, "TgoCassisCamera"))

    def test_tgo_cassis_distortion_map_is_importable(self):
        self.assertTrue(hasattr(ip, "TgoCassisDistortionMap"))

    def test_tgo_cassis_camera_inherits_framing_camera(self):
        self.assertTrue(issubclass(ip.TgoCassisCamera, ip.FramingCamera))

    def test_tgo_cassis_distortion_map_inherits_camera_distortion_map(self):
        self.assertTrue(
            issubclass(ip.TgoCassisDistortionMap, ip.CameraDistortionMap)
        )

    def test_tgo_cassis_camera_methods_exist(self):
        self.assertTrue(hasattr(ip.TgoCassisCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.TgoCassisCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.TgoCassisCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.TgoCassisCamera, "spk_target_id"))
        self.assertTrue(hasattr(ip.TgoCassisCamera, "spk_reference_id"))

    def test_tgo_cassis_distortion_map_methods_exist(self):
        self.assertTrue(hasattr(ip.TgoCassisDistortionMap, "set_focal_plane"))
        self.assertTrue(
            hasattr(ip.TgoCassisDistortionMap, "set_undistorted_focal_plane")
        )
        self.assertTrue(hasattr(ip.TgoCassisDistortionMap, "__repr__"))

    def test_tgo_cassis_distortion_map_inherits_base_methods(self):
        """Inherited from CameraDistortionMap base class."""
        self.assertTrue(
            hasattr(ip.TgoCassisDistortionMap, "focal_plane_x")
        )
        self.assertTrue(
            hasattr(ip.TgoCassisDistortionMap, "focal_plane_y")
        )
        self.assertTrue(
            hasattr(ip.TgoCassisDistortionMap, "undistorted_focal_plane_x")
        )
        self.assertTrue(
            hasattr(ip.TgoCassisDistortionMap, "undistorted_focal_plane_y")
        )


if __name__ == "__main__":
    unittest.main()
