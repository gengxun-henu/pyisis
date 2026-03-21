import unittest

from _unit_test_support import DEGREES, METERS, ip


class LatitudeUnitTest(unittest.TestCase):
    def test_default_constructor_matches_cpp_unit_test(self):
        latitude = ip.Latitude()
        self.assertFalse(latitude.is_valid())

    def test_planetocentric_constructor_and_accessors(self):
        latitude = ip.Latitude(45.0, DEGREES)
        self.assertTrue(latitude.is_valid())
        self.assertAlmostEqual(latitude.degrees(), 45.0, places=12)
        self.assertAlmostEqual(latitude.planetocentric(DEGREES), 45.0, places=12)

    def test_planetographic_constructor_with_radii(self):
        equatorial_radius = ip.Distance(1500.0, METERS)
        polar_radius = ip.Distance(2500.0, METERS)
        latitude = ip.Latitude(
            45.0,
            equatorial_radius,
            polar_radius,
            ip.Latitude.CoordinateType.Planetographic,
            DEGREES,
        )

        self.assertTrue(latitude.is_valid())
        self.assertAlmostEqual(latitude.planetographic(DEGREES), 45.0, places=10)

    def test_copy_constructor_and_setters(self):
        equatorial_radius = ip.Distance(1400.0, METERS)
        polar_radius = ip.Distance(1500.0, METERS)
        latitude = ip.Latitude(
            0.0,
            equatorial_radius,
            polar_radius,
            ip.Latitude.CoordinateType.Planetocentric,
            DEGREES,
        )
        latitude.set_planetocentric(45.0, DEGREES)
        self.assertAlmostEqual(latitude.planetocentric(DEGREES), 45.0, places=12)

        copied = ip.Latitude(latitude)
        self.assertAlmostEqual(copied.planetocentric(DEGREES), 45.0, places=12)
        self.assertAlmostEqual(latitude.planetocentric(DEGREES), 45.0, places=12)

        latitude.set_planetographic(25.0, DEGREES)
        self.assertAlmostEqual(latitude.planetographic(DEGREES), 25.0, places=10)

    def test_in_range(self):
        latitude = ip.Latitude(25.0, DEGREES)
        minimum = ip.Latitude(20.0, DEGREES)
        maximum = ip.Latitude(30.0, DEGREES)
        self.assertTrue(latitude.in_range(minimum, maximum))

    def test_disallowed_planetographic_value_raises(self):
        equatorial_radius = ip.Distance(1500.0, METERS)
        polar_radius = ip.Distance(2500.0, METERS)

        with self.assertRaises(ip.IException):
            ip.Latitude(
                95.0,
                equatorial_radius,
                polar_radius,
                ip.Latitude.CoordinateType.Planetographic,
                DEGREES,
                ip.Latitude.ErrorChecking.ThrowAllErrors,
            )

    def test_allow_past_pole_mode(self):
        equatorial_radius = ip.Distance(1500.0, METERS)
        polar_radius = ip.Distance(2500.0, METERS)
        latitude = ip.Latitude(
            95.0,
            equatorial_radius,
            polar_radius,
            ip.Latitude.CoordinateType.Planetocentric,
            DEGREES,
            ip.Latitude.ErrorChecking.AllowPastPole,
        )

        self.assertTrue(latitude.is_valid())
        self.assertEqual(latitude.error_checking(), ip.Latitude.ErrorChecking.AllowPastPole)


if __name__ == "__main__":
    unittest.main()