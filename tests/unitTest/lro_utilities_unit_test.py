"""
Unit tests for ISIS LRO (Lunar Reconnaissance Orbiter) camera utilities bindings

Author: Geng Xun
Created: 2026-04-06
Last Modified: 2026-04-06
"""

import unittest
import sys
import os

# Add the build directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'build'))

try:
    import isis_pybind as ip
except ImportError as e:
    print(f"Error importing isis_pybind: {e}")
    print(f"Python path: {sys.path}")
    raise


class TestLroNarrowAngleCamera(unittest.TestCase):
    """Test suite for LroNarrowAngleCamera binding"""

    def test_class_exists(self):
        """Test that LroNarrowAngleCamera class is accessible"""
        self.assertTrue(hasattr(ip, 'LroNarrowAngleCamera'))

    def test_ck_frame_id(self):
        """Test ck_frame_id method returns expected constant"""
        # Note: These methods require a Camera instance which needs a Cube
        # Testing without actual data would require mocking or test fixtures
        # For now, we verify the method exists
        self.assertTrue(hasattr(ip.LroNarrowAngleCamera, 'ck_frame_id'))

    def test_ck_reference_id(self):
        """Test ck_reference_id method exists"""
        self.assertTrue(hasattr(ip.LroNarrowAngleCamera, 'ck_reference_id'))

    def test_spk_reference_id(self):
        """Test spk_reference_id method exists"""
        self.assertTrue(hasattr(ip.LroNarrowAngleCamera, 'spk_reference_id'))


class TestLroWideAngleCamera(unittest.TestCase):
    """Test suite for LroWideAngleCamera binding"""

    def test_class_exists(self):
        """Test that LroWideAngleCamera class is accessible"""
        self.assertTrue(hasattr(ip, 'LroWideAngleCamera'))

    def test_set_band(self):
        """Test set_band method exists"""
        self.assertTrue(hasattr(ip.LroWideAngleCamera, 'set_band'))

    def test_is_band_independent(self):
        """Test is_band_independent method exists"""
        self.assertTrue(hasattr(ip.LroWideAngleCamera, 'is_band_independent'))

    def test_ck_frame_id(self):
        """Test ck_frame_id method exists"""
        self.assertTrue(hasattr(ip.LroWideAngleCamera, 'ck_frame_id'))

    def test_ck_reference_id(self):
        """Test ck_reference_id method exists"""
        self.assertTrue(hasattr(ip.LroWideAngleCamera, 'ck_reference_id'))

    def test_spk_reference_id(self):
        """Test spk_reference_id method exists"""
        self.assertTrue(hasattr(ip.LroWideAngleCamera, 'spk_reference_id'))


class TestMiniRF(unittest.TestCase):
    """Test suite for MiniRF radar camera binding"""

    def test_class_exists(self):
        """Test that MiniRF class is accessible"""
        self.assertTrue(hasattr(ip, 'MiniRF'))

    def test_ck_frame_id(self):
        """Test ck_frame_id method exists (throws exception in actual use)"""
        self.assertTrue(hasattr(ip.MiniRF, 'ck_frame_id'))

    def test_ck_reference_id(self):
        """Test ck_reference_id method exists (throws exception in actual use)"""
        self.assertTrue(hasattr(ip.MiniRF, 'ck_reference_id'))

    def test_spk_target_id(self):
        """Test spk_target_id method exists"""
        self.assertTrue(hasattr(ip.MiniRF, 'spk_target_id'))

    def test_spk_reference_id(self):
        """Test spk_reference_id method exists"""
        self.assertTrue(hasattr(ip.MiniRF, 'spk_reference_id'))


class TestLroNarrowAngleDistortionMap(unittest.TestCase):
    """Test suite for LroNarrowAngleDistortionMap binding"""

    def test_class_exists(self):
        """Test that LroNarrowAngleDistortionMap class is accessible"""
        self.assertTrue(hasattr(ip, 'LroNarrowAngleDistortionMap'))

    def test_set_distortion(self):
        """Test set_distortion method exists"""
        self.assertTrue(hasattr(ip.LroNarrowAngleDistortionMap, 'set_distortion'))

    def test_set_focal_plane(self):
        """Test set_focal_plane method exists"""
        self.assertTrue(hasattr(ip.LroNarrowAngleDistortionMap, 'set_focal_plane'))

    def test_set_undistorted_focal_plane(self):
        """Test set_undistorted_focal_plane method exists"""
        self.assertTrue(hasattr(ip.LroNarrowAngleDistortionMap, 'set_undistorted_focal_plane'))

    def test_repr(self):
        """Test __repr__ method exists"""
        self.assertTrue(hasattr(ip.LroNarrowAngleDistortionMap, '__repr__'))


class TestLroWideAngleCameraDistortionMap(unittest.TestCase):
    """Test suite for LroWideAngleCameraDistortionMap binding"""

    def test_class_exists(self):
        """Test that LroWideAngleCameraDistortionMap class is accessible"""
        self.assertTrue(hasattr(ip, 'LroWideAngleCameraDistortionMap'))

    def test_add_filter(self):
        """Test add_filter method exists"""
        self.assertTrue(hasattr(ip.LroWideAngleCameraDistortionMap, 'add_filter'))

    def test_set_band(self):
        """Test set_band method exists"""
        self.assertTrue(hasattr(ip.LroWideAngleCameraDistortionMap, 'set_band'))

    def test_set_focal_plane(self):
        """Test set_focal_plane method exists"""
        self.assertTrue(hasattr(ip.LroWideAngleCameraDistortionMap, 'set_focal_plane'))

    def test_set_undistorted_focal_plane(self):
        """Test set_undistorted_focal_plane method exists"""
        self.assertTrue(hasattr(ip.LroWideAngleCameraDistortionMap, 'set_undistorted_focal_plane'))

    def test_repr(self):
        """Test __repr__ method exists"""
        self.assertTrue(hasattr(ip.LroWideAngleCameraDistortionMap, '__repr__'))


class TestLroWideAngleCameraFocalPlaneMap(unittest.TestCase):
    """Test suite for LroWideAngleCameraFocalPlaneMap binding"""

    def test_class_exists(self):
        """Test that LroWideAngleCameraFocalPlaneMap class is accessible"""
        self.assertTrue(hasattr(ip, 'LroWideAngleCameraFocalPlaneMap'))

    def test_add_filter(self):
        """Test add_filter method exists"""
        self.assertTrue(hasattr(ip.LroWideAngleCameraFocalPlaneMap, 'add_filter'))

    def test_set_band(self):
        """Test set_band method exists"""
        self.assertTrue(hasattr(ip.LroWideAngleCameraFocalPlaneMap, 'set_band'))

    def test_repr(self):
        """Test __repr__ method exists"""
        self.assertTrue(hasattr(ip.LroWideAngleCameraFocalPlaneMap, '__repr__'))


if __name__ == '__main__':
    unittest.main()
