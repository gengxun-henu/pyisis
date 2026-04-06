"""
Unit tests for ISIS Hayabusa and Hayabusa2 mission camera bindings

Author: Geng Xun
Created: 2026-04-06
Last Modified: 2026-04-06
"""

import unittest

from _unit_test_support import ip


class HayabusaMissionBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for Hayabusa mission binding surfaces."""

    def test_hayabusa_camera_classes_are_importable(self):
        self.assertTrue(hasattr(ip, "HayabusaAmicaCamera"))
        self.assertTrue(hasattr(ip, "HayabusaNirsCamera"))
        self.assertTrue(hasattr(ip, "NirsDetectorMap"))
        self.assertTrue(hasattr(ip, "Hyb2OncCamera"))
        self.assertTrue(hasattr(ip, "Hyb2OncDistortionMap"))

    def test_hayabusa_amica_camera_methods_exist(self):
        self.assertTrue(hasattr(ip.HayabusaAmicaCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.HayabusaAmicaCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.HayabusaAmicaCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.HayabusaAmicaCamera, "spk_reference_id"))

    def test_hayabusa_nirs_camera_methods_exist(self):
        self.assertTrue(hasattr(ip.HayabusaNirsCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.HayabusaNirsCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.HayabusaNirsCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.HayabusaNirsCamera, "spk_reference_id"))
        self.assertTrue(hasattr(ip.HayabusaNirsCamera, "pixel_ifov_offsets"))

    def test_hayabusa2_onc_camera_methods_exist(self):
        self.assertTrue(hasattr(ip.Hyb2OncCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.Hyb2OncCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.Hyb2OncCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.Hyb2OncCamera, "spk_reference_id"))

    def test_nirs_detector_map_runtime_behavior_without_camera_parent(self):
        detector_map = ip.NirsDetectorMap(1.25, None)

        self.assertIsInstance(detector_map, ip.CameraDetectorMap)
        self.assertAlmostEqual(detector_map.exposure_duration(1.0, 2.0, 1), 1.25)

        detector_map.set_exposure_duration(2.5)
        self.assertAlmostEqual(detector_map.exposure_duration(5.0, 6.0, 2), 2.5)

    def test_hyb2_onc_distortion_map_binding_surface_exists(self):
        self.assertTrue(hasattr(ip.Hyb2OncDistortionMap, "set_focal_plane"))
        self.assertTrue(hasattr(ip.Hyb2OncDistortionMap, "set_undistorted_focal_plane"))
        self.assertTrue(hasattr(ip.Hyb2OncDistortionMap, "__repr__"))


if __name__ == "__main__":
    unittest.main()