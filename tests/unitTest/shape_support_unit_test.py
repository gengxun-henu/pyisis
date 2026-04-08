"""
Unit tests for ISIS shape-support bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-03-21
"""

import math
import unittest

from _unit_test_support import DEGREES, ip


class ShapeSupportUnitTest(unittest.TestCase):
    def setUp(self):
        self.plate = ip.TriangularPlate(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            2,
        )

    def test_triangular_plate_basic_geometry(self):
        self.assertEqual(self.plate.name(), "TriangularPlate")
        self.assertEqual(self.plate.id(), 2)
        self.assertGreater(self.plate.min_radius().meters(), 0.0)
        self.assertGreaterEqual(self.plate.max_radius().meters(), self.plate.min_radius().meters())
        self.assertGreater(self.plate.area(), 0.0)

        center = self.plate.center()
        normal = self.plate.normal()
        vertex = self.plate.vertex(0)

        self.assertEqual(len(center), 3)
        self.assertEqual(len(normal), 3)
        self.assertEqual(vertex, [1.0, 0.0, 0.0])

    def test_triangular_plate_intercept_miss_cases_from_cpp_unit_test(self):
        self.assertFalse(self.plate.has_intercept([0.0, 0.0, 1.0], [1.0, 1.0, 1.0]))
        self.assertIsNone(self.plate.intercept([0.0, 0.0, 1.0], [1.0, 1.0, 1.0]))

        self.assertFalse(self.plate.has_intercept([0.0, 0.0, 2.0], [0.0, 0.0, 1.0]))
        self.assertIsNone(self.plate.intercept([0.0, 0.0, 2.0], [0.0, 0.0, 1.0]))

    def test_triangular_plate_intercept_hit_matches_cpp_path(self):
        intercept = self.plate.intercept([0.0, 0.0, 0.0], [1.0, 1.0, 1.0])

        self.assertIsNotNone(intercept)
        self.assertTrue(intercept.is_valid())
        self.assertEqual(intercept.shape().name(), "TriangularPlate")
        self.assertEqual(intercept.observer(), [0.0, 0.0, 0.0])
        self.assertEqual(intercept.look_direction_ray(), [1.0, 1.0, 1.0])

        location = intercept.location().to_naif_array()
        self.assertAlmostEqual(location[0], 1.0 / 3.0, places=8)
        self.assertAlmostEqual(location[1], 1.0 / 3.0, places=8)
        self.assertAlmostEqual(location[2], 1.0 / 3.0, places=8)

        normal = intercept.normal()
        emission = intercept.emission()
        separation_angle = intercept.separation_angle([1.0, 1.0, 1.0])
        self.assertEqual(len(normal), 3)
        self.assertTrue(math.isfinite(emission.degrees()))
        self.assertTrue(math.isfinite(separation_angle.degrees()))

    def test_triangular_plate_point_lookup_and_vertex_errors(self):
        south_pole = ip.Latitude(-90.0, DEGREES)
        equator = ip.Latitude(0.0, DEGREES)
        longitude = ip.Longitude(0.0, DEGREES)

        self.assertFalse(self.plate.has_point(south_pole, longitude))
        self.assertIsNone(self.plate.point(south_pole, longitude))

        self.assertTrue(self.plate.has_point(equator, longitude))
        point = self.plate.point(equator, longitude)
        self.assertTrue(point.valid())

        with self.assertRaises(Exception):
            self.plate.vertex(-1)

        with self.assertRaises(Exception):
            self.plate.vertex(5)

    def test_intercept_default_invalid_state(self):
        intercept = ip.Intercept()

        self.assertFalse(intercept.is_valid())
        with self.assertRaises(Exception):
            intercept.location()


if __name__ == "__main__":
    unittest.main()
