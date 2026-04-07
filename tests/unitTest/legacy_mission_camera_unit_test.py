"""
Unit tests for ISIS Viking, Mars Odyssey, Messenger, and Mariner mission bindings

Author: Geng Xun
Created: 2026-04-07
Last Modified: 2026-04-07
"""

import unittest

from _unit_test_support import ip


class VikingAndMarinerMissionBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for Viking and Mariner mission camera bindings."""

    def test_viking_camera_binding_surface(self):
        self.assertTrue(hasattr(ip, "VikingCamera"))
        self.assertTrue(issubclass(ip.VikingCamera, ip.FramingCamera))
        self.assertTrue(hasattr(ip.VikingCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.VikingCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.VikingCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.VikingCamera, "spk_target_id"))
        self.assertTrue(hasattr(ip.VikingCamera, "spk_reference_id"))

    def test_mariner10_camera_binding_surface(self):
        self.assertTrue(hasattr(ip, "Mariner10Camera"))
        self.assertTrue(issubclass(ip.Mariner10Camera, ip.FramingCamera))
        self.assertTrue(hasattr(ip.Mariner10Camera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.Mariner10Camera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.Mariner10Camera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.Mariner10Camera, "spk_reference_id"))


class MarsOdysseyMissionBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for THEMIS camera and distortion-map bindings."""

    def test_themis_camera_classes_are_importable(self):
        self.assertTrue(hasattr(ip, "ThemisIrCamera"))
        self.assertTrue(hasattr(ip, "ThemisIrDistortionMap"))
        self.assertTrue(hasattr(ip, "ThemisVisCamera"))
        self.assertTrue(hasattr(ip, "ThemisVisDistortionMap"))

    def test_themis_ir_camera_methods_exist(self):
        self.assertTrue(issubclass(ip.ThemisIrCamera, ip.LineScanCamera))
        self.assertTrue(hasattr(ip.ThemisIrCamera, "set_band"))
        self.assertTrue(hasattr(ip.ThemisIrCamera, "is_band_independent"))
        self.assertTrue(hasattr(ip.ThemisIrCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.ThemisIrCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.ThemisIrCamera, "spk_reference_id"))

    def test_themis_vis_camera_methods_exist(self):
        self.assertTrue(issubclass(ip.ThemisVisCamera, ip.PushFrameCamera))
        self.assertTrue(hasattr(ip.ThemisVisCamera, "set_band"))
        self.assertTrue(hasattr(ip.ThemisVisCamera, "band_ephemeris_time_offset"))
        self.assertTrue(hasattr(ip.ThemisVisCamera, "is_band_independent"))
        self.assertTrue(hasattr(ip.ThemisVisCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.ThemisVisCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.ThemisVisCamera, "spk_reference_id"))

    def test_themis_ir_distortion_map_methods_exist(self):
        self.assertTrue(issubclass(ip.ThemisIrDistortionMap, ip.CameraDistortionMap))
        self.assertTrue(hasattr(ip.ThemisIrDistortionMap, "set_band"))
        self.assertTrue(hasattr(ip.ThemisIrDistortionMap, "set_focal_plane"))
        self.assertTrue(
            hasattr(ip.ThemisIrDistortionMap, "set_undistorted_focal_plane")
        )
        self.assertTrue(hasattr(ip.ThemisIrDistortionMap, "focal_plane_x"))
        self.assertTrue(hasattr(ip.ThemisIrDistortionMap, "undistorted_focal_plane_x"))

    def test_themis_vis_distortion_map_methods_exist(self):
        self.assertTrue(issubclass(ip.ThemisVisDistortionMap, ip.CameraDistortionMap))
        self.assertTrue(hasattr(ip.ThemisVisDistortionMap, "set_focal_plane"))
        self.assertTrue(
            hasattr(ip.ThemisVisDistortionMap, "set_undistorted_focal_plane")
        )
        self.assertTrue(hasattr(ip.ThemisVisDistortionMap, "focal_plane_x"))
        self.assertTrue(hasattr(ip.ThemisVisDistortionMap, "undistorted_focal_plane_x"))


class MessengerTaylorDistortionBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for the Messenger Taylor distortion-map helper."""

    def test_taylor_camera_distortion_map_binding_surface(self):
        self.assertTrue(hasattr(ip, "TaylorCameraDistortionMap"))
        self.assertTrue(
            issubclass(ip.TaylorCameraDistortionMap, ip.CameraDistortionMap)
        )
        self.assertTrue(hasattr(ip.TaylorCameraDistortionMap, "set_distortion"))
        self.assertTrue(hasattr(ip.TaylorCameraDistortionMap, "set_focal_plane"))
        self.assertTrue(
            hasattr(ip.TaylorCameraDistortionMap, "set_undistorted_focal_plane")
        )

    def test_taylor_camera_distortion_map_inherits_base_methods(self):
        self.assertTrue(hasattr(ip.TaylorCameraDistortionMap, "focal_plane_x"))
        self.assertTrue(hasattr(ip.TaylorCameraDistortionMap, "focal_plane_y"))
        self.assertTrue(
            hasattr(ip.TaylorCameraDistortionMap, "undistorted_focal_plane_x")
        )
        self.assertTrue(
            hasattr(ip.TaylorCameraDistortionMap, "undistorted_focal_plane_y")
        )


if __name__ == "__main__":
    unittest.main()
