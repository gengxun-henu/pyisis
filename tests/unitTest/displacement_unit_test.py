import unittest

from _unit_test_support import (
    DISPLACEMENT_KILOMETERS,
    DISPLACEMENT_METERS,
    DISPLACEMENT_PIXELS,
    ip,
)


class DisplacementUnitTest(unittest.TestCase):
    def test_default_constructor_matches_expected_invalid_state(self):
        displacement = ip.Displacement()
        self.assertFalse(displacement.is_valid())

    def test_basic_constructors_and_accessors(self):
        meters_displacement = ip.Displacement(-15.5, DISPLACEMENT_METERS)
        self.assertTrue(meters_displacement.is_valid())
        self.assertAlmostEqual(meters_displacement.meters(), -15.5, places=12)

        kilometers_displacement = ip.Displacement(1.25, DISPLACEMENT_KILOMETERS)
        self.assertAlmostEqual(kilometers_displacement.kilometers(), 1.25, places=12)
        self.assertAlmostEqual(kilometers_displacement.meters(), 1250.0, places=12)

    def test_distance_constructor_and_mutators(self):
        distance = ip.Distance(3.0, ip.Distance.Units.Meters)
        displacement = ip.Displacement(distance)
        self.assertAlmostEqual(displacement.meters(), 3.0, places=12)

        displacement.set_meters(-12.0)
        self.assertAlmostEqual(displacement.meters(), -12.0, places=12)

        displacement.set_kilometers(0.5)
        self.assertAlmostEqual(displacement.kilometers(), 0.5, places=12)
        self.assertAlmostEqual(distance.meters(), 3.0, places=12)

    def test_pixel_based_constructor_and_setters(self):
        displacement = ip.Displacement(10.0, 2.0)
        self.assertAlmostEqual(displacement.meters(), 5.0, places=12)
        self.assertAlmostEqual(displacement.pixels(2.0), 10.0, places=12)

        displacement.set_pixels(-4.0, 2.0)
        self.assertAlmostEqual(displacement.meters(), -2.0, places=12)
        self.assertAlmostEqual(displacement.pixels(2.0), -4.0, places=12)

    def test_repr_contains_class_name_and_value(self):
        displacement = ip.Displacement(2.5, DISPLACEMENT_METERS)
        representation = repr(displacement)
        self.assertIn("Displacement(", representation)
        self.assertIn("2.500000", representation)

    def test_units_enum_is_exposed(self):
        self.assertEqual(DISPLACEMENT_METERS, ip.Displacement.Units.Meters)
        self.assertEqual(DISPLACEMENT_KILOMETERS, ip.Displacement.Units.Kilometers)
        self.assertEqual(DISPLACEMENT_PIXELS, ip.Displacement.Units.Pixels)


if __name__ == "__main__":
    unittest.main()