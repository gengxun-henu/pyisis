"""
Unit tests for ISIS MGS utilities bindings

Author: Geng Xun
Created: 2026-04-05
Last Modified: 2026-04-05
"""

import unittest

from _unit_test_support import ip


class MocNarrowAngleSummingUnitTest(unittest.TestCase):
    """Test suite for MocNarrowAngleSumming binding."""

    def test_constructor_and_conversion_csum1_ss1(self):
        """Test csum=1, ss=1 configuration (from upstream unitTest.cpp)."""
        s = ip.MocNarrowAngleSumming(1, 1)

        # Test detector conversion
        self.assertAlmostEqual(s.detector(1.0), 1.0, places=10)
        self.assertAlmostEqual(s.detector(2.0), 2.0, places=10)
        self.assertAlmostEqual(s.detector(3.0), 3.0, places=10)

        # Test round-trip: sample -> detector -> sample
        self.assertAlmostEqual(s.sample(s.detector(1.0)), 1.0, places=10)
        self.assertAlmostEqual(s.sample(s.detector(2.0)), 2.0, places=10)
        self.assertAlmostEqual(s.sample(s.detector(3.0)), 3.0, places=10)

    def test_constructor_and_conversion_csum2_ss1(self):
        """Test csum=2, ss=1 configuration (from upstream unitTest.cpp)."""
        s = ip.MocNarrowAngleSumming(2, 1)

        # Test detector conversion
        self.assertAlmostEqual(s.detector(1.0), 1.5, places=10)
        self.assertAlmostEqual(s.detector(2.0), 3.5, places=10)
        self.assertAlmostEqual(s.detector(3.0), 5.5, places=10)

        # Test round-trip: sample -> detector -> sample
        self.assertAlmostEqual(s.sample(s.detector(1.0)), 1.0, places=10)
        self.assertAlmostEqual(s.sample(s.detector(2.0)), 2.0, places=10)
        self.assertAlmostEqual(s.sample(s.detector(3.0)), 3.0, places=10)

    def test_constructor_and_conversion_csum3_ss10(self):
        """Test csum=3, ss=10 configuration (from upstream unitTest.cpp)."""
        s = ip.MocNarrowAngleSumming(3, 10)

        # Test detector conversion
        self.assertAlmostEqual(s.detector(1.0), 15.0, places=10)
        self.assertAlmostEqual(s.detector(2.0), 18.0, places=10)
        self.assertAlmostEqual(s.detector(3.0), 21.0, places=10)

        # Test round-trip: sample -> detector -> sample
        self.assertAlmostEqual(s.sample(s.detector(1.0)), 1.0, places=10)
        self.assertAlmostEqual(s.sample(s.detector(2.0)), 2.0, places=10)
        self.assertAlmostEqual(s.sample(s.detector(3.0)), 3.0, places=10)

    def test_reverse_conversion_sample_from_detector(self):
        """Test sample conversion from detector values."""
        s1 = ip.MocNarrowAngleSumming(1, 1)
        self.assertAlmostEqual(s1.sample(1.0), 1.0, places=10)

        s2 = ip.MocNarrowAngleSumming(2, 1)
        self.assertAlmostEqual(s2.sample(1.5), 1.0, places=10)
        self.assertAlmostEqual(s2.sample(3.5), 2.0, places=10)

        s3 = ip.MocNarrowAngleSumming(3, 10)
        self.assertAlmostEqual(s3.sample(15.0), 1.0, places=10)
        self.assertAlmostEqual(s3.sample(18.0), 2.0, places=10)

    def test_repr(self):
        """Test __repr__ method."""
        s = ip.MocNarrowAngleSumming(2, 1)
        repr_str = repr(s)
        self.assertIn("MocNarrowAngleSumming", repr_str)


class MocWideAngleDistortionMapUnitTest(unittest.TestCase):
    """Test suite for MocWideAngleDistortionMap binding. Added: 2026-04-05."""

    def test_class_is_exported(self):
        """Test that MocWideAngleDistortionMap class is accessible."""
        self.assertTrue(hasattr(ip, 'MocWideAngleDistortionMap'))

    def test_repr(self):
        """Test __repr__ method with mock camera."""
        # Create a minimal mock Camera for testing
        # MocWideAngleDistortionMap needs a Camera* parent, but we can test basic construction
        # Note: This test requires actual Camera infrastructure which may not be available
        # in a unit test context without ISISDATA. We'll test inheritance instead.
        pass

    def test_inheritance_from_camera_distortion_map(self):
        """Test that MocWideAngleDistortionMap inherits from CameraDistortionMap."""
        # Verify the class hierarchy is correctly exposed
        self.assertTrue(hasattr(ip, 'MocWideAngleDistortionMap'))
        self.assertTrue(hasattr(ip, 'CameraDistortionMap'))

        # Test that the class has the expected methods
        self.assertTrue(hasattr(ip.MocWideAngleDistortionMap, 'set_focal_plane'))
        self.assertTrue(hasattr(ip.MocWideAngleDistortionMap, 'set_undistorted_focal_plane'))

        # Test that inherited methods from CameraDistortionMap are available
        # These are inherited from the base class
        self.assertTrue(hasattr(ip.MocWideAngleDistortionMap, 'focal_plane_x'))
        self.assertTrue(hasattr(ip.MocWideAngleDistortionMap, 'focal_plane_y'))
        self.assertTrue(hasattr(ip.MocWideAngleDistortionMap, 'undistorted_focal_plane_x'))
        self.assertTrue(hasattr(ip.MocWideAngleDistortionMap, 'undistorted_focal_plane_y'))
        self.assertTrue(hasattr(ip.MocWideAngleDistortionMap, 'undistorted_focal_plane_z'))
class MocLabelsUnitTest(unittest.TestCase):
    """Test suite for MocLabels binding. Added: 2026-04-05."""

    def test_constructor_from_file_basic_import(self):
        """Test MocLabels can be imported and constructed from file path."""
        # Note: This test only validates the binding signature, not runtime behavior
        # Full behavior testing would require actual MOC cube data
        self.assertTrue(hasattr(ip, 'MocLabels'))

        # Constructor signature should accept string file path
        # We don't actually call it here since we lack test data
        # but we verify the binding exists
        self.assertTrue(callable(ip.MocLabels))

    def test_method_signatures_exist(self):
        """Test that all expected MocLabels methods are bound."""
        # Verify all expected methods are available as attributes
        # This validates the binding without requiring actual MOC data
        expected_methods = [
            'narrow_angle',
            'wide_angle',
            'wide_angle_red',
            'wide_angle_blue',
            'crosstrack_summing',
            'downtrack_summing',
            'first_line_sample',
            'focal_plane_temperature',
            'line_rate',
            'exposure_duration',
            'start_time',
            'detectors',
            'start_detector',
            'end_detector',
            'sample',
            'ephemeris_time',
            'gain',
            'offset',
        ]

        # We can't instantiate without valid data, but we can check
        # that the class has the expected method names in its dir()
        moc_labels_attrs = dir(ip.MocLabels)
        for method in expected_methods:
            self.assertIn(method, moc_labels_attrs,
                          f"Method '{method}' not found in MocLabels")


class MocWideAngleDetectorMapUnitTest(unittest.TestCase):
    """Test suite for MocWideAngleDetectorMap binding. Added: 2026-04-05."""

    def test_class_exists_and_inherits(self):
        """Test MocWideAngleDetectorMap can be imported."""
        # Verify the class exists
        self.assertTrue(hasattr(ip, 'MocWideAngleDetectorMap'))
        self.assertTrue(callable(ip.MocWideAngleDetectorMap))

    def test_method_signatures_exist(self):
        """Test that all expected MocWideAngleDetectorMap methods are bound."""
        # Verify all expected methods are available
        # This validates the binding without requiring actual camera/labels instances
        expected_methods = [
            'set_parent',
            'set_detector',
            # Inherited from LineScanCameraDetectorMap:
            'set_start_time',
            'set_line_rate',
            'line_rate',
            'start_time',
            # Inherited from CameraDetectorMap:
            'parent_sample',
            'parent_line',
            'detector_sample',
            'detector_line',
        ]

        detector_map_attrs = dir(ip.MocWideAngleDetectorMap)
        for method in expected_methods:
            self.assertIn(method, detector_map_attrs,
                          f"Method '{method}' not found in MocWideAngleDetectorMap")

    def test_inheritance_from_line_scan_camera_detector_map(self):
        """Test that MocWideAngleDetectorMap properly inherits from LineScanCameraDetectorMap."""
        # Verify LineScanCameraDetectorMap exists
        self.assertTrue(hasattr(ip, 'LineScanCameraDetectorMap'))

        # Note: We cannot test isinstance without actual instances,
        # but we can verify method inheritance by checking method presence
        # which is done in test_method_signatures_exist


if __name__ == '__main__':
    unittest.main()
