import unittest

from _unit_test_support import KILOMETERS, METERS, SOLAR_RADII, ip


class DistanceUnitTest(unittest.TestCase):
    def test_default_constructor_matches_cpp_unit_test(self):
        distance = ip.Distance()
        self.assertFalse(distance.is_valid())

    def test_basic_constructors_and_accessors(self):
        meters_distance = ip.Distance(1500.5, METERS)
        self.assertAlmostEqual(meters_distance.meters(), 1500.5, places=12)

        kilometers_distance = ip.Distance(1.5005, KILOMETERS)
        self.assertAlmostEqual(kilometers_distance.meters(), 1500.5, places=9)
        self.assertAlmostEqual(kilometers_distance.kilometers(), 1.5005, places=12)

        solar_distance = ip.Distance(2.0, SOLAR_RADII)
        self.assertAlmostEqual(solar_distance.solar_radii(), 2.0, places=12)
        self.assertGreater(solar_distance.meters(), 0.0)

    def test_copy_constructor_and_mutators(self):
        original = ip.Distance(1500.5, METERS)
        copied = ip.Distance(original)
        self.assertAlmostEqual(copied.meters(), 1500.5, places=12)

        copied.set_meters(250.0)
        self.assertAlmostEqual(copied.meters(), 250.0, places=12)

        copied.set_kilometers(1.25)
        self.assertAlmostEqual(copied.kilometers(), 1.25, places=12)

        copied.set_solar_radii(3.0)
        self.assertAlmostEqual(copied.solar_radii(), 3.0, places=12)
        self.assertAlmostEqual(original.meters(), 1500.5, places=12)

    def test_pixel_based_constructor_and_accessors(self):
        distance = ip.Distance(100.0, 10.0)
        self.assertAlmostEqual(distance.meters(), 10.0, places=12)
        self.assertAlmostEqual(distance.pixels(10.0), 100.0, places=12)

        distance.set_pixels(25.0, 5.0)
        self.assertAlmostEqual(distance.meters(), 5.0, places=12)
        self.assertAlmostEqual(distance.pixels(5.0), 25.0, places=12)

    def test_negative_distance_raises(self):
        with self.assertRaises(ip.IException):
            ip.Distance(-1.0, METERS)

        with self.assertRaises(ip.IException):
            ip.Distance(-1.0, KILOMETERS)

        distance = ip.Distance(1.0, KILOMETERS)

        with self.assertRaises(ip.IException):
            distance.set_meters(-1.0)

        with self.assertRaises(ip.IException):
            distance.set_kilometers(-1.0)


if __name__ == "__main__":
    unittest.main()