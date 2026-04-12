"""
Unit tests for ISIS geometry helper bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-04-12
Updated: 2026-04-09  Geng Xun fixed Intercept SurfacePoint regression expectations to match NAIF kilometer coordinates
Updated: 2026-04-10  Geng Xun added Area3D binding focused unit tests
Updated: 2026-04-10  Geng Xun aligned Area3D unit tests with exported Distance and Displacement enum names
Updated: 2026-04-12  Geng Xun added focused regression coverage for Longitude.to360_range() and Latitude.add() overloads.
"""

import math
import unittest

from _unit_test_support import ip, workspace_test_data_path


MDIS_CUBE = workspace_test_data_path("mosrange", "EN0108828322M_iof.cub")


class GeometryUnitTest(unittest.TestCase):
    def open_cube_or_skip(self):
        if not MDIS_CUBE.exists():
            self.skipTest(f"Required cube is unavailable in this environment: {MDIS_CUBE}")

        cube = ip.Cube()
        cube.open(str(MDIS_CUBE), "r")
        self.addCleanup(cube.close)
        return cube

    def test_transform_default_behavior_matches_wrapper_contract(self):
        transform = ip.Transform()

        self.assertEqual(transform.output_samples(), 0)
        self.assertEqual(transform.output_lines(), 0)

        success, in_sample, in_line = transform.xform(12.5, 7.5)
        self.assertTrue(success)
        self.assertEqual(in_sample, 0.0)
        self.assertEqual(in_line, 0.0)
        self.assertIn("Transform(", repr(transform))

    def test_interpolator_requires_type_before_dimension_queries(self):
        interpolator = ip.Interpolator()

        with self.assertRaises(ip.IException):
            interpolator.samples()

        with self.assertRaises(ip.IException):
            interpolator.lines()

    def test_interpolator_nearest_neighbor_and_bilinear_paths(self):
        nearest = ip.Interpolator(ip.Interpolator.InterpType.NearestNeighborType)
        self.assertEqual(nearest.samples(), 1)
        self.assertEqual(nearest.lines(), 1)
        self.assertAlmostEqual(nearest.hot_sample(), -0.5, places=12)
        self.assertAlmostEqual(nearest.hot_line(), -0.5, places=12)
        self.assertAlmostEqual(nearest.interpolate(10.2, 20.7, [42.5]), 42.5, places=12)

        bilinear = ip.Interpolator(ip.Interpolator.InterpType.BiLinearType)
        self.assertEqual(bilinear.samples(), 2)
        self.assertEqual(bilinear.lines(), 2)
        self.assertAlmostEqual(bilinear.hot_sample(), 0.0, places=12)
        self.assertAlmostEqual(bilinear.hot_line(), 0.0, places=12)

        value = bilinear.interpolate(1.25, 2.75, [10.0, 20.0, 30.0, 50.0])
        self.assertAlmostEqual(value, 29.375, places=12)

    def test_interpolator_cubic_metadata_and_buffer_validation(self):
        cubic = ip.Interpolator()
        cubic.set_type(ip.Interpolator.InterpType.CubicConvolutionType)

        self.assertEqual(cubic.samples(), 4)
        self.assertEqual(cubic.lines(), 4)
        self.assertAlmostEqual(cubic.hot_sample(), 1.0, places=12)
        self.assertAlmostEqual(cubic.hot_line(), 1.0, places=12)

        with self.assertRaisesRegex(RuntimeError, "buffer size mismatch"):
            cubic.interpolate(1.25, 1.25, [1.0] * 15)

    def test_enlarge_construction_xform_and_subarea(self):
        cube = self.open_cube_or_skip()

        enlarge = ip.Enlarge(cube, 2.0, 1.5)

        self.assertIsInstance(enlarge, ip.Transform)
        self.assertEqual(enlarge.output_samples(), 2048)
        self.assertEqual(enlarge.output_lines(), 1536)

        success, in_sample, in_line = enlarge.xform(1.0, 1.0)
        self.assertTrue(success)
        self.assertAlmostEqual(in_sample, 0.75, places=12)
        self.assertAlmostEqual(in_line, 0.8333333333333334, places=12)

        enlarge.set_input_area(101, 200, 51, 150)
        self.assertEqual(enlarge.output_samples(), 200)
        self.assertEqual(enlarge.output_lines(), 150)

        success, in_sample, in_line = enlarge.xform(1.0, 1.0)
        self.assertTrue(success)
        self.assertAlmostEqual(in_sample, 100.75, places=12)
        self.assertAlmostEqual(in_line, 50.833333333333336, places=12)

        with self.assertRaises(ip.IException):
            enlarge.set_input_area(10, 5, 1, 2)

        self.assertIn("Enlarge(", repr(enlarge))

    def test_reduce_construction_and_boundary_mutator(self):
        cube = self.open_cube_or_skip()

        reduce_obj = ip.Reduce(cube, 2.0, 4.0)

        reduce_obj.set_input_boundary(101, 500, 21, 220)

        self.assertIn("Reduce(", repr(reduce_obj))

    def test_intercept_manual_construction_clones_shape_and_point(self):
        plate = ip.TriangularPlate(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
            ],
            5,
        )
        surface_point = ip.SurfacePoint(
            ip.Displacement(1.0, ip.Displacement.Units.Meters),
            ip.Displacement(2.0, ip.Displacement.Units.Meters),
            ip.Displacement(3.0, ip.Displacement.Units.Meters),
        )

        intercept = ip.Intercept(
            [0.0, 0.0, 10.0],
            [0.0, 0.0, -1.0],
            surface_point,
            plate,
        )

        self.assertTrue(intercept.is_valid())
        self.assertEqual(intercept.observer(), [0.0, 0.0, 10.0])
        self.assertEqual(intercept.look_direction_ray(), [0.0, 0.0, -1.0])

        location = intercept.location().to_naif_array()
        self.assertAlmostEqual(location[0], 0.001, places=8)
        self.assertAlmostEqual(location[1], 0.002, places=8)
        self.assertAlmostEqual(location[2], 0.003, places=8)

        point = intercept.location()
        self.assertAlmostEqual(point.get_x().meters(), 1.0, places=8)
        self.assertAlmostEqual(point.get_y().meters(), 2.0, places=8)
        self.assertAlmostEqual(point.get_z().meters(), 3.0, places=8)

        shape = intercept.shape()
        self.assertIsNotNone(shape)
        self.assertIsNot(shape, plate)
        self.assertEqual(shape.name(), "TriangularPlate")

        normal = intercept.normal()
        self.assertEqual(len(normal), 3)
        separation = intercept.separation_angle([0.0, 0.0, -1.0])
        self.assertAlmostEqual(separation.degrees(), 180.0, places=8)
        emission = intercept.emission()
        self.assertTrue(math.isfinite(emission.degrees()))


class Area3DUnitTest(unittest.TestCase):
    """Focused unit tests for Area3D binding. Added: 2026-04-10."""

    def _make_area(self, x0=0.0, y0=0.0, z0=0.0, w=1.0, h=1.0, d=1.0):
        """Helper: create an Area3D from origin + dimensions."""
        start_x = ip.Displacement(x0, ip.Displacement.Units.Meters)
        start_y = ip.Displacement(y0, ip.Displacement.Units.Meters)
        start_z = ip.Displacement(z0, ip.Displacement.Units.Meters)
        width   = ip.Distance(w, ip.Distance.Units.Meters)
        height  = ip.Distance(h, ip.Distance.Units.Meters)
        depth   = ip.Distance(d, ip.Distance.Units.Meters)
        return ip.Area3D(start_x, start_y, start_z, width, height, depth)

    def test_default_constructor_is_invalid(self):
        """Default-constructed Area3D reports is_valid() == False."""
        area = ip.Area3D()
        self.assertFalse(area.is_valid())

    def test_construct_with_dimensions(self):
        """Area3D constructed with positive dimensions is valid."""
        area = self._make_area()
        self.assertTrue(area.is_valid())

    def test_get_width(self):
        """get_width returns the Distance passed to constructor."""
        area = self._make_area(w=5.0)
        self.assertAlmostEqual(area.get_width().meters(), 5.0)

    def test_get_height(self):
        """get_height returns the Distance passed to constructor."""
        area = self._make_area(h=3.0)
        self.assertAlmostEqual(area.get_height().meters(), 3.0)

    def test_get_depth(self):
        """get_depth returns the Distance passed to constructor."""
        area = self._make_area(d=7.0)
        self.assertAlmostEqual(area.get_depth().meters(), 7.0)

    def test_get_start_x(self):
        """get_start_x returns the Displacement passed to constructor."""
        area = self._make_area(x0=2.0)
        self.assertAlmostEqual(area.get_start_x().meters(), 2.0)

    def test_set_and_get_width(self):
        """set_width updates the width Distance."""
        area = self._make_area(w=1.0)
        area.set_width(ip.Distance(10.0, ip.Distance.Units.Meters))
        self.assertAlmostEqual(area.get_width().meters(), 10.0)

    def test_intersect_with_overlapping_area(self):
        """Two overlapping areas produce a non-null intersection."""
        a = self._make_area(x0=0.0, y0=0.0, z0=0.0, w=2.0, h=2.0, d=2.0)
        b = self._make_area(x0=1.0, y0=1.0, z0=1.0, w=2.0, h=2.0, d=2.0)
        intersection = a.intersect(b)
        self.assertTrue(intersection.is_valid())

    def test_intersect_non_overlapping_is_invalid(self):
        """Non-overlapping areas produce an invalid intersection."""
        a = self._make_area(x0=0.0, y0=0.0, z0=0.0, w=1.0, h=1.0, d=1.0)
        b = self._make_area(x0=5.0, y0=5.0, z0=5.0, w=1.0, h=1.0, d=1.0)
        intersection = a.intersect(b)
        self.assertFalse(intersection.is_valid())

    def test_copy_constructor(self):
        """Area3D copy constructor produces an equal independent copy."""
        a = self._make_area(w=4.0)
        b = ip.Area3D(a)
        self.assertAlmostEqual(b.get_width().meters(), 4.0)

    def test_end_constructor(self):
        """Area3D constructed with end displacements is valid."""
        start_x = ip.Displacement(0.0, ip.Displacement.Units.Meters)
        start_y = ip.Displacement(0.0, ip.Displacement.Units.Meters)
        start_z = ip.Displacement(0.0, ip.Displacement.Units.Meters)
        end_x   = ip.Displacement(2.0, ip.Displacement.Units.Meters)
        end_y   = ip.Displacement(3.0, ip.Displacement.Units.Meters)
        end_z   = ip.Displacement(4.0, ip.Displacement.Units.Meters)
        area = ip.Area3D(start_x, start_y, start_z, end_x, end_y, end_z)
        self.assertTrue(area.is_valid())

    def test_repr(self):
        """repr of valid Area3D contains 'Area3D'."""
        area = self._make_area()
        r = repr(area)
        self.assertIn("Area3D", r)


class LatitudeLongitudeUnitTest(unittest.TestCase):
    """Focused unit tests for latitude/longitude helper overloads. Added: 2026-04-12."""

    def _make_mapping_group(self, latitude_type="Planetocentric"):
        mapping = ip.PvlGroup("Mapping")
        mapping.add_keyword(ip.PvlKeyword("LatitudeType", latitude_type))
        mapping.add_keyword(ip.PvlKeyword("EquatorialRadius", "3396190.0"))
        mapping.add_keyword(ip.PvlKeyword("PolarRadius", "3376200.0"))
        return mapping

    def test_longitude_to360_range_splits_wraparound_interval(self):
        start = ip.Longitude(
            -10.0,
            ip.Angle.Units.Degrees,
            ip.Longitude.Direction.PositiveEast,
            ip.Longitude.Domain.Domain180,
        )
        end = ip.Longitude(
            10.0,
            ip.Angle.Units.Degrees,
            ip.Longitude.Direction.PositiveEast,
            ip.Longitude.Domain.Domain180,
        )

        ranges = ip.Longitude.to360_range(start, end)

        self.assertEqual(len(ranges), 2)
        degrees = [
            (
                pair[0].positive_east(ip.Angle.Units.Degrees),
                pair[1].positive_east(ip.Angle.Units.Degrees),
            )
            for pair in ranges
        ]
        self.assertAlmostEqual(degrees[0][0], 0.0, places=8)
        self.assertAlmostEqual(degrees[0][1], 10.0, places=8)
        self.assertAlmostEqual(degrees[1][0], 350.0, places=8)
        self.assertAlmostEqual(degrees[1][1], 360.0, places=8)

    def test_latitude_add_with_mapping_group_uses_mapping_lat_type(self):
        equatorial_radius = ip.Distance(3396190.0, ip.Distance.Units.Meters)
        polar_radius = ip.Distance(3376200.0, ip.Distance.Units.Meters)
        latitude = ip.Latitude(
            10.0,
            equatorial_radius,
            polar_radius,
            ip.Latitude.CoordinateType.Planetocentric,
            ip.Angle.Units.Degrees,
        )
        mapping = self._make_mapping_group("Planetocentric")

        result = latitude.add(ip.Angle(5.0, ip.Angle.Units.Degrees), mapping)

        self.assertIsInstance(result, ip.Latitude)
        self.assertAlmostEqual(
            result.planetocentric(ip.Angle.Units.Degrees),
            15.0,
            places=8,
        )

    def test_latitude_add_with_explicit_radii_supports_planetographic(self):
        equatorial_radius = ip.Distance(3396190.0, ip.Distance.Units.Meters)
        polar_radius = ip.Distance(3376200.0, ip.Distance.Units.Meters)
        latitude = ip.Latitude(
            30.0,
            equatorial_radius,
            polar_radius,
            ip.Latitude.CoordinateType.Planetographic,
            ip.Angle.Units.Degrees,
        )

        result = latitude.add(
            ip.Angle(5.0, ip.Angle.Units.Degrees),
            equatorial_radius,
            polar_radius,
            ip.Latitude.CoordinateType.Planetographic,
        )

        self.assertIsInstance(result, ip.Latitude)
        self.assertAlmostEqual(
            result.planetographic(ip.Angle.Units.Degrees),
            35.0,
            places=8,
        )


if __name__ == "__main__":
    unittest.main()
