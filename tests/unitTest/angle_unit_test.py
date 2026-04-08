"""
Unit tests for ISIS Angle bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-03-21
"""

import math
import unittest

from _unit_test_support import DEGREES, RADIANS, ip


class AngleUnitTest(unittest.TestCase):
    def test_default_constructor_matches_cpp_unit_test(self):
        angle = ip.Angle()
        self.assertFalse(angle.is_valid())

    def test_degree_and_radian_constructors(self):
        angle_from_degrees = ip.Angle(30.0, DEGREES)
        self.assertTrue(angle_from_degrees.is_valid())
        self.assertAlmostEqual(angle_from_degrees.degrees(), 30.0, places=12)
        self.assertAlmostEqual(angle_from_degrees.radians(), math.pi / 6.0, places=12)

        angle_from_radians = ip.Angle(math.pi / 6.0, RADIANS)
        self.assertAlmostEqual(angle_from_radians.degrees(), 30.0, places=12)

    def test_copy_constructor_and_mutators(self):
        original = ip.Angle(30.0, DEGREES)
        copied = ip.Angle(original)

        self.assertAlmostEqual(copied.degrees(), 30.0, places=12)

        copied.set_degrees(180.0)
        self.assertAlmostEqual(copied.degrees(), 180.0, places=12)

        copied.set_radians(math.pi)
        self.assertAlmostEqual(copied.radians(), math.pi, places=12)
        self.assertAlmostEqual(original.degrees(), 30.0, places=12)

    def test_string_constructor_cases_from_cpp_unit_test(self):
        cases = [
            ("-70 15 30.125", -(70.0 + 15.0 / 60.0 + 30.125 / 3600.0)),
            ("  +70  30 11     ", 70.0 + 30.0 / 60.0 + 11.0 / 3600.0),
            ("100 00 00", 100.0),
        ]

        for angle_text, expected_degrees in cases:
            with self.subTest(angle_text=angle_text):
                angle = ip.Angle(angle_text)
                self.assertTrue(angle.is_valid())
                self.assertAlmostEqual(angle.degrees(), expected_degrees, places=10)

    def test_invalid_string_constructor_raises(self):
        with self.assertRaises(ip.IException):
            ip.Angle("this 79 should 00 fail 0.111")

        with self.assertRaises(ip.IException):
            ip.Angle("100")

        with self.assertRaises(ip.IException):
            ip.Angle("70 11")

    def test_full_rotation(self):
        full_rotation = ip.Angle.full_rotation()
        self.assertTrue(full_rotation.is_valid())
        self.assertAlmostEqual(full_rotation.degrees(), 360.0, places=12)


if __name__ == "__main__":
    unittest.main()