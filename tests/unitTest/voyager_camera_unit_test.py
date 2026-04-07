"""
Unit tests for ISIS Voyager camera bindings

Author: Geng Xun
Created: 2026-04-07
Last Modified: 2026-04-07
"""

import unittest

from _unit_test_support import ip


class VoyagerCameraBindingsUnitTest(unittest.TestCase):
    """Focused regression coverage for Voyager camera binding surfaces."""

    def test_voyager_camera_is_importable(self):
        self.assertTrue(hasattr(ip, "VoyagerCamera"))

    def test_voyager_camera_inherits_framing_camera(self):
        self.assertTrue(issubclass(ip.VoyagerCamera, ip.FramingCamera))

    def test_voyager_camera_methods_exist(self):
        self.assertTrue(hasattr(ip.VoyagerCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.VoyagerCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.VoyagerCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.VoyagerCamera, "spk_target_id"))
        self.assertTrue(hasattr(ip.VoyagerCamera, "spk_reference_id"))


if __name__ == "__main__":
    unittest.main()
