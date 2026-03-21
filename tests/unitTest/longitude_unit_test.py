import math
import unittest

from _unit_test_support import DEGREES, RADIANS, ip


class LongitudeUnitTest(unittest.TestCase):
    def test_default_constructor_matches_cpp_unit_test(self):
        longitude = ip.Longitude()
        self.assertFalse(longitude.is_valid())

    def test_basic_constructors(self):
        longitude = ip.Longitude(180.0, DEGREES)
        self.assertTrue(longitude.is_valid())
        self.assertAlmostEqual(longitude.degrees(), 180.0, places=12)

        positive_west = ip.Longitude(
            -90.0,
            DEGREES,
            ip.Longitude.Direction.PositiveWest,
            ip.Longitude.Domain.Domain180,
        )
        self.assertAlmostEqual(positive_west.positive_west(DEGREES), -90.0, places=12)

    def test_copy_constructor_and_setters(self):
        longitude = ip.Longitude(270.0, DEGREES)
        longitude.set_positive_east(90.0, DEGREES)
        self.assertAlmostEqual(longitude.positive_east(DEGREES), 90.0, places=12)

        copied = ip.Longitude(longitude)
        copied.set_positive_west(90.0, DEGREES)
        self.assertAlmostEqual(copied.positive_west(DEGREES), 90.0, places=12)
        self.assertAlmostEqual(longitude.positive_east(DEGREES), 90.0, places=12)

    def test_get_methods(self):
        longitude = ip.Longitude(90.0, DEGREES)
        self.assertAlmostEqual(longitude.positive_east(DEGREES), 90.0, places=12)
        self.assertAlmostEqual(longitude.positive_east(RADIANS), math.pi / 2.0, places=12)
        self.assertAlmostEqual(longitude.positive_west(DEGREES), 270.0, places=12)

        wrapped = ip.Longitude(450.0, DEGREES)
        self.assertAlmostEqual(wrapped.degrees(), 450.0, places=12)
        self.assertAlmostEqual(wrapped.force_360_domain().degrees(), 90.0, places=12)

    def test_force_domain_methods(self):
        longitude = ip.Longitude(270.0, DEGREES)
        self.assertAlmostEqual(longitude.force_180_domain().degrees(), -90.0, places=12)
        self.assertAlmostEqual(longitude.force_360_domain().degrees(), 270.0, places=12)

    def test_in_range(self):
        longitude = ip.Longitude(45.0, DEGREES)
        minimum = ip.Longitude(30.0, DEGREES)
        maximum = ip.Longitude(90.0, DEGREES)
        self.assertTrue(longitude.in_range(minimum, maximum))


if __name__ == "__main__":
    unittest.main()