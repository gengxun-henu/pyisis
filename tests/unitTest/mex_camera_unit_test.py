"""
Unit tests for ISIS Mars Express camera bindings

Author: Geng Xun
Created: 2026-04-06
Last Modified: 2026-04-06
"""

import unittest

from _unit_test_support import ip, workspace_test_data_path


HRSC_CUBE = workspace_test_data_path("socet", "h2254_0000_s12-cropped.cub")


class HrscCameraUnitTest(unittest.TestCase):
    """Test suite for HrscCamera binding. Added: 2026-04-06."""

    def open_cube(self, path):
        cube = ip.Cube()
        cube.open(str(path), "r")
        self.addCleanup(cube.close)
        return cube

    def test_hrsc_camera_class_exists(self):
        """Test that HrscCamera class is accessible."""
        self.assertTrue(hasattr(ip, "HrscCamera"))

    def test_hrsc_camera_inherits_line_scan_camera(self):
        """Test HrscCamera inherits from LineScanCamera."""
        self.assertTrue(hasattr(ip, "LineScanCamera"))
        self.assertTrue(hasattr(ip.HrscCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.HrscCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.HrscCamera, "spk_reference_id"))

    def test_hrsc_camera_constructor_and_kernel_ids_with_local_cube(self):
        """Test direct HrscCamera construction and kernel IDs using local HRSC cube."""
        if not HRSC_CUBE.exists():
            self.skipTest(f"Local HRSC cube not found: {HRSC_CUBE}")

        cube = self.open_cube(HRSC_CUBE)
        camera = ip.HrscCamera(cube)

        self.assertIsInstance(camera, ip.HrscCamera)
        self.assertIsInstance(camera, ip.LineScanCamera)
        self.assertEqual(camera.ck_frame_id(), -41001)
        self.assertEqual(camera.ck_reference_id(), 1)
        self.assertEqual(camera.spk_reference_id(), 1)

    def test_camera_factory_returns_hrsc_camera_for_local_cube(self):
        """Test CameraFactory dispatches the local HRSC cube to HrscCamera."""
        if not HRSC_CUBE.exists():
            self.skipTest(f"Local HRSC cube not found: {HRSC_CUBE}")

        cube = self.open_cube(HRSC_CUBE)
        camera = ip.CameraFactory.create(cube)

        self.assertEqual(type(camera).__name__, "HrscCamera")
        self.assertIsInstance(camera, ip.Camera)
        self.assertIsInstance(camera, ip.LineScanCamera)
        self.assertEqual(camera.ck_frame_id(), -41001)
        self.assertEqual(camera.ck_reference_id(), 1)
        self.assertEqual(camera.spk_reference_id(), 1)


class MexHrscSrcCameraUnitTest(unittest.TestCase):
    """Test suite for MexHrscSrcCamera binding. Added: 2026-04-06."""

    def test_mex_hrsc_src_camera_class_exists(self):
        """Test that MexHrscSrcCamera class is accessible."""
        self.assertTrue(hasattr(ip, "MexHrscSrcCamera"))

    def test_mex_hrsc_src_camera_inherits_framing_camera(self):
        """Test MexHrscSrcCamera inherits from FramingCamera."""
        self.assertTrue(hasattr(ip, "FramingCamera"))
        self.assertTrue(hasattr(ip.MexHrscSrcCamera, "shutter_open_close_times"))
        self.assertTrue(hasattr(ip.MexHrscSrcCamera, "ck_frame_id"))
        self.assertTrue(hasattr(ip.MexHrscSrcCamera, "ck_reference_id"))
        self.assertTrue(hasattr(ip.MexHrscSrcCamera, "spk_reference_id"))
