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


if __name__ == '__main__':
    unittest.main()
