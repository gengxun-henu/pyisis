"""
Unit tests for ISIS CubeCalculator binding.

Author: Geng Xun
Created: 2026-04-10
Last Modified: 2026-04-10
"""

import unittest

from _unit_test_support import ip


class CubeCalculatorUnitTest(unittest.TestCase):
    """Test CubeCalculator construction and basic operations."""

    @classmethod
    def setUpClass(cls):
        if not hasattr(ip, "CubeCalculator"):
            raise unittest.SkipTest("CubeCalculator not available")

    def test_class_exists(self):
        self.assertTrue(hasattr(ip, "CubeCalculator"))

    def test_default_construction(self):
        cc = ip.CubeCalculator()
        self.assertIsInstance(cc, ip.CubeCalculator)

    def test_clear(self):
        cc = ip.CubeCalculator()
        # clear should not raise on a fresh calculator
        cc.clear()

    def test_repr(self):
        cc = ip.CubeCalculator()
        r = repr(cc)
        self.assertIn("CubeCalculator", r)


if __name__ == "__main__":
    unittest.main()
