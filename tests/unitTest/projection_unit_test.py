"""
Unit tests for ISIS projection and ProjectionFactory bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-04-12
Updated: 2026-04-12  Geng Xun added focused tests for all concrete projection type bindings
  (Sinusoidal, Mercator, Robinson, Orthographic, Mollweide, LambertConformal,
  LambertAzimuthalEqualArea, ObliqueCylindrical, PointPerspective,
  PolarStereographic, TransverseMercator, UpturnedEllipsoidTransverseAzimuthal,
  Planar, LunarAzimuthalEqualArea) covering name/version/set_ground/set_coordinate/
  xy_range/mapping and class-specific methods.
"""

import unittest

from _unit_test_support import (
    ip,
    make_equirectangular_label,
    make_lambert_azimuthal_label,
    make_lambert_conformal_label,
    make_mercator_label,
    make_mollweide_label,
    make_oblique_cylindrical_label,
    make_orthographic_label,
    make_planar_label,
    make_point_perspective_label,
    make_polar_stereographic_label,
    make_ring_cylindrical_label,
    make_robinson_label,
    make_simple_cylindrical_label,
    make_sinusoidal_label,
    make_transverse_mercator_label,
)


class ProjectionUnitTest(unittest.TestCase):
    def test_equirectangular_requires_center_keywords_without_defaults(self):
        """Test that Equirectangular requires CenterLongitude and CenterLatitude when defaults not allowed"""
        label = make_equirectangular_label(include_center_longitude=False)

        with self.assertRaises(Exception):
            ip.Equirectangular(label)

        label = make_equirectangular_label(include_center_latitude=False)

        with self.assertRaises(Exception):
            ip.Equirectangular(label)

    def test_equirectangular_allow_defaults_matches_cpp_default_path(self):
        """Test that Equirectangular computes default center values when allowed"""
        label = make_equirectangular_label(
            include_center_longitude=False,
            include_center_latitude=False
        )

        projection = ip.Equirectangular(label, True)

        self.assertEqual(projection.name(), "Equirectangular")
        self.assertEqual(projection.version(), "1.0")
        self.assertTrue(projection.is_equatorial_cylindrical())

        # Default center latitude should be 0.0 (middle of -65 to 65)
        # Default center longitude should be 0.0 (middle of -180 to 180)
        self.assertAlmostEqual(projection.true_scale_latitude(), 0.0, places=8)

    def test_equirectangular_ground_and_coordinate_round_trip(self):
        """Test round-trip conversion between ground and coordinate"""
        projection = ip.Equirectangular(make_equirectangular_label())

        # Test setting ground coordinates
        self.assertTrue(projection.set_ground(30.0, 45.0))
        self.assertAlmostEqual(projection.latitude(), 30.0, places=10)
        self.assertAlmostEqual(projection.longitude(), 45.0, places=10)

        x = projection.x_coord()
        y = projection.y_coord()

        # Test setting coordinate from the same X/Y
        self.assertTrue(projection.set_coordinate(x, y))
        self.assertAlmostEqual(projection.latitude(), 30.0, places=8)
        self.assertAlmostEqual(projection.longitude(), 45.0, places=8)

    def test_equirectangular_xy_range_export(self):
        """Test that xy_range returns valid min/max values"""
        projection = ip.Equirectangular(make_equirectangular_label())

        xy_range = projection.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)

        minX, maxX, minY, maxY = xy_range
        self.assertLess(minX, maxX)
        self.assertLess(minY, maxY)

    def test_equirectangular_mapping_methods(self):
        """Test mapping, mapping_latitudes, and mapping_longitudes methods"""
        projection = ip.Equirectangular(make_equirectangular_label())

        mapping = projection.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        self.assertTrue(mapping.has_keyword("CenterLongitude"))
        self.assertTrue(mapping.has_keyword("CenterLatitude"))

        mapping_latitudes = projection.mapping_latitudes()
        self.assertTrue(mapping_latitudes.has_keyword("MinimumLatitude"))
        self.assertTrue(mapping_latitudes.has_keyword("CenterLatitude"))

        mapping_longitudes = projection.mapping_longitudes()
        self.assertTrue(mapping_longitudes.has_keyword("MinimumLongitude"))
        self.assertTrue(mapping_longitudes.has_keyword("CenterLongitude"))

    def test_equirectangular_near_pole_raises_exception(self):
        """Test that setting center latitude near pole raises exception"""
        # Create a label with center latitude very close to 90 degrees
        lines = [
            "Group = Mapping",
            "  EquatorialRadius = 3396190.0",
            "  PolarRadius = 3376200.0",
            "  LatitudeType = Planetographic",
            "  LongitudeDirection = PositiveEast",
            "  LongitudeDomain = 360",
            "  ProjectionName = Equirectangular",
            "  CenterLongitude = 0.0",
            "  CenterLatitude = 89.9999999",  # Very close to pole
            "  MinimumLatitude = -65.0",
            "  MaximumLatitude = 65.0",
            "  MinimumLongitude = -180.0",
            "  MaximumLongitude = 180.0",
            "EndGroup",
            "End",
        ]

        pvl = ip.Pvl()
        pvl.from_string("\n".join(lines) + "\n")

        with self.assertRaises(Exception):
            ip.Equirectangular(pvl)

    def test_simple_cylindrical_requires_center_longitude_without_defaults(self):
        label = make_simple_cylindrical_label(include_center_longitude=False)

        with self.assertRaises(Exception):
            ip.SimpleCylindrical(label)

    def test_simple_cylindrical_allow_defaults_matches_cpp_default_path(self):
        label = make_simple_cylindrical_label(include_center_longitude=False)

        projection = ip.SimpleCylindrical(label, True)

        self.assertEqual(projection.name(), "SimpleCylindrical")
        self.assertTrue(projection.set_ground(-50.0, -75.0))
        self.assertAlmostEqual(projection.latitude(), -50.0, places=10)
        self.assertAlmostEqual(projection.longitude(), -75.0, places=10)

    def test_simple_cylindrical_ground_and_coordinate_round_trip(self):
        projection = ip.SimpleCylindrical(make_simple_cylindrical_label())

        self.assertTrue(projection.set_ground(-50.0, -75.0))
        self.assertAlmostEqual(projection.latitude(), -50.0, places=10)
        self.assertAlmostEqual(projection.longitude(), -75.0, places=10)

        self.assertTrue(projection.set_coordinate(0.2617993877991494, -0.8726646259971648))
        self.assertAlmostEqual(projection.latitude(), -1.4722380078853067e-05, places=10)
        self.assertAlmostEqual(projection.longitude(), 220.00000441671403, places=8)

    def test_simple_cylindrical_mapping_and_xy_range_exports(self):
        projection = ip.SimpleCylindrical(make_simple_cylindrical_label())

        xy_range = projection.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)
        self.assertLess(xy_range[0], xy_range[1])
        self.assertLess(xy_range[2], xy_range[3])

        mapping = projection.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        self.assertTrue(mapping.has_keyword("CenterLongitude"))
        self.assertTrue(projection.mapping_latitudes().has_keyword("MinimumLatitude"))
        self.assertTrue(projection.mapping_longitudes().has_keyword("MinimumLongitude"))

    def test_simple_cylindrical_is_equatorial_cylindrical(self):
        projection = ip.SimpleCylindrical(make_simple_cylindrical_label())
        self.assertTrue(projection.is_equatorial_cylindrical())

    def test_simple_cylindrical_name_and_version(self):
        projection = ip.SimpleCylindrical(make_simple_cylindrical_label())
        self.assertEqual(projection.name(), "SimpleCylindrical")
        self.assertIsInstance(projection.version(), str)

    def test_projection_factory_create_from_cube_label_requires_cube_keywords(self):
        label = make_simple_cylindrical_label(include_pixel_resolution=False, include_upper_left=False)

        with self.assertRaises(Exception):
            ip.ProjectionFactory.create_from_cube_label(label)

        label = make_simple_cylindrical_label(include_pixel_resolution=True, include_upper_left=False)
        with self.assertRaises(Exception):
            ip.ProjectionFactory.create_from_cube_label(label)

        label = make_simple_cylindrical_label(include_pixel_resolution=True, include_upper_left=True)
        projection = ip.ProjectionFactory.create_from_cube_label(label)
        self.assertEqual(projection.name(), "SimpleCylindrical")
        self.assertTrue(projection.set_world(245.0, 355.0))
        self.assertAlmostEqual(projection.latitude(), 22.82592837302989, places=8)
        self.assertAlmostEqual(projection.longitude(), 227.94605488817228, places=8)

    def test_projection_factory_create_for_cube_computes_cube_shape(self):
        label = make_simple_cylindrical_label(include_pixel_resolution=True, include_upper_left=False)

        projection, samples, lines = ip.ProjectionFactory.create_for_cube(label)

        self.assertEqual(projection.name(), "SimpleCylindrical")
        self.assertGreater(samples, 0)
        self.assertGreater(lines, 0)

        mapping = label.find_group("Mapping")
        self.assertTrue(mapping.has_keyword("UpperLeftCornerX"))
        self.assertTrue(mapping.has_keyword("UpperLeftCornerY"))

    def test_ring_cylindrical_requires_center_keywords_without_defaults(self):
        missing_longitude = make_ring_cylindrical_label(include_center_longitude=False)
        with self.assertRaises(Exception):
            ip.RingCylindrical(missing_longitude)

        missing_radius = make_ring_cylindrical_label(include_center_radius=False)
        with self.assertRaises(Exception):
            ip.RingCylindrical(missing_radius)

    def test_ring_cylindrical_default_constructor_path_and_round_trip(self):
        label = make_ring_cylindrical_label(include_center_longitude=False, include_center_radius=False)
        projection = ip.RingCylindrical(label, True)

        self.assertEqual(projection.name(), "RingCylindrical")
        self.assertTrue(projection.mapping().has_keyword("CenterRingLongitude"))
        self.assertTrue(projection.mapping().has_keyword("CenterRingRadius"))

        configured = ip.RingCylindrical(make_ring_cylindrical_label())
        self.assertTrue(configured.set_ground(20000.0, 45.0))
        self.assertAlmostEqual(configured.ring_radius(), 20000.0, places=8)
        self.assertAlmostEqual(configured.ring_longitude(), 45.0, places=8)

        self.assertTrue(configured.set_coordinate(-157079.6326794896, 180000.0))
        self.assertAlmostEqual(configured.ring_radius(), 20000.0, places=8)
        self.assertAlmostEqual(configured.ring_longitude(), 45.0, places=8)

    def test_ring_cylindrical_range_and_direction_helpers(self):
        configured = ip.RingCylindrical(make_ring_cylindrical_label())

        self.assertEqual(configured.ring_longitude_direction_string(), "Clockwise")
        self.assertEqual(configured.ring_longitude_domain_string(), "180")
        self.assertEqual(configured.true_scale_ring_radius(), 200000.0)

        self.assertFalse(configured.set_coordinate(-157079.6326794896, -20000001.0))
        self.assertFalse(configured.set_coordinate(-1570.6326794896, 184000.5))
        self.assertAlmostEqual(configured.ring_radius(), 15999.5, places=8)

        xy_range = configured.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)

        counter_clockwise = ip.RingCylindrical(
            make_ring_cylindrical_label(
                include_center_longitude=False,
                include_center_radius=False,
                direction="CounterClockwise",
                domain="360",
            ),
            True,
        )
        self.assertEqual(counter_clockwise.ring_longitude_direction_string(), "CounterClockwise")
        self.assertEqual(counter_clockwise.ring_longitude_domain_string(), "360")
        self.assertFalse(counter_clockwise.set_ground(-1000.0, 45.0))
        self.assertFalse(counter_clockwise.set_ground(0.0, 45.0))

    # --- RingCylindrical: newly bound method tests ---
    def test_ring_cylindrical_name_version(self):
        proj = ip.RingCylindrical(make_ring_cylindrical_label())
        self.assertEqual(proj.name(), "RingCylindrical")
        self.assertIsInstance(proj.version(), str)

    def test_ring_cylindrical_center_accessors(self):
        proj = ip.RingCylindrical(make_ring_cylindrical_label())
        self.assertAlmostEqual(proj.center_ring_longitude(), 0.0, places=8)
        self.assertAlmostEqual(proj.center_ring_radius(), 200000.0, places=8)

    def test_ring_cylindrical_is_equatorial_cylindrical(self):
        proj = ip.RingCylindrical(make_ring_cylindrical_label())
        self.assertTrue(proj.is_equatorial_cylindrical())

    def test_ring_cylindrical_mapping_ring_methods(self):
        proj = ip.RingCylindrical(make_ring_cylindrical_label())
        mapping = proj.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        radii = proj.mapping_ring_radii()
        self.assertTrue(radii.has_keyword("MinimumRingRadius"))
        longitudes = proj.mapping_ring_longitudes()
        self.assertTrue(longitudes.has_keyword("MinimumRingLongitude"))


class SinusoidalUnitTest(unittest.TestCase):
    """Tests for Sinusoidal projection binding. Added: 2026-04-12."""

    def test_sinusoidal_construction_and_name(self):
        proj = ip.Sinusoidal(make_sinusoidal_label())
        self.assertEqual(proj.name(), "Sinusoidal")
        self.assertIsInstance(proj.version(), str)

    def test_sinusoidal_allow_defaults(self):
        proj = ip.Sinusoidal(make_sinusoidal_label(include_center_longitude=False), True)
        self.assertEqual(proj.name(), "Sinusoidal")

    def test_sinusoidal_requires_center_longitude(self):
        with self.assertRaises(Exception):
            ip.Sinusoidal(make_sinusoidal_label(include_center_longitude=False))

    def test_sinusoidal_ground_coordinate_round_trip(self):
        proj = ip.Sinusoidal(make_sinusoidal_label())
        self.assertTrue(proj.set_ground(30.0, -90.0))
        self.assertAlmostEqual(proj.latitude(), 30.0, places=8)
        self.assertAlmostEqual(proj.longitude(), -90.0, places=8)
        x, y = proj.x_coord(), proj.y_coord()
        self.assertTrue(proj.set_coordinate(x, y))
        self.assertAlmostEqual(proj.latitude(), 30.0, places=6)
        self.assertAlmostEqual(proj.longitude(), -90.0, places=6)

    def test_sinusoidal_xy_range(self):
        proj = ip.Sinusoidal(make_sinusoidal_label())
        xy_range = proj.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)
        self.assertLess(xy_range[0], xy_range[1])

    def test_sinusoidal_mapping_methods(self):
        proj = ip.Sinusoidal(make_sinusoidal_label())
        mapping = proj.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        self.assertTrue(proj.mapping_latitudes().has_keyword("MinimumLatitude"))
        self.assertTrue(proj.mapping_longitudes().has_keyword("MinimumLongitude"))


class MercatorUnitTest(unittest.TestCase):
    """Tests for Mercator projection binding. Added: 2026-04-12."""

    def test_mercator_construction_and_name(self):
        proj = ip.Mercator(make_mercator_label())
        self.assertEqual(proj.name(), "Mercator")
        self.assertIsInstance(proj.version(), str)

    def test_mercator_true_scale_latitude(self):
        proj = ip.Mercator(make_mercator_label())
        self.assertAlmostEqual(proj.true_scale_latitude(), 0.0, places=8)

    def test_mercator_is_equatorial_cylindrical(self):
        proj = ip.Mercator(make_mercator_label())
        self.assertTrue(proj.is_equatorial_cylindrical())

    def test_mercator_ground_coordinate_round_trip(self):
        proj = ip.Mercator(make_mercator_label())
        self.assertTrue(proj.set_ground(30.0, -90.0))
        x, y = proj.x_coord(), proj.y_coord()
        self.assertTrue(proj.set_coordinate(x, y))
        self.assertAlmostEqual(proj.latitude(), 30.0, places=4)
        self.assertAlmostEqual(proj.longitude(), -90.0, places=4)

    def test_mercator_xy_range(self):
        proj = ip.Mercator(make_mercator_label())
        xy_range = proj.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)

    def test_mercator_mapping_methods(self):
        proj = ip.Mercator(make_mercator_label())
        mapping = proj.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        self.assertTrue(mapping.has_keyword("CenterLatitude"))
        self.assertTrue(proj.mapping_latitudes().has_keyword("MinimumLatitude"))
        self.assertTrue(proj.mapping_longitudes().has_keyword("MinimumLongitude"))


class RobinsonUnitTest(unittest.TestCase):
    """Tests for Robinson projection binding. Added: 2026-04-12."""

    def test_robinson_construction_and_name(self):
        proj = ip.Robinson(make_robinson_label())
        self.assertEqual(proj.name(), "Robinson")
        self.assertIsInstance(proj.version(), str)

    def test_robinson_ground_coordinate_round_trip(self):
        proj = ip.Robinson(make_robinson_label())
        self.assertTrue(proj.set_ground(45.0, 90.0))
        x, y = proj.x_coord(), proj.y_coord()
        self.assertTrue(proj.set_coordinate(x, y))
        self.assertAlmostEqual(proj.latitude(), 45.0, places=4)
        self.assertAlmostEqual(proj.longitude(), 90.0, places=4)

    def test_robinson_xy_range(self):
        proj = ip.Robinson(make_robinson_label())
        xy_range = proj.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)

    def test_robinson_mapping_methods(self):
        proj = ip.Robinson(make_robinson_label())
        mapping = proj.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        self.assertTrue(proj.mapping_latitudes().has_keyword("MinimumLatitude"))
        self.assertTrue(proj.mapping_longitudes().has_keyword("MinimumLongitude"))


class OrthographicUnitTest(unittest.TestCase):
    """Tests for Orthographic projection binding. Added: 2026-04-12."""

    def test_orthographic_construction_and_name(self):
        proj = ip.Orthographic(make_orthographic_label())
        self.assertEqual(proj.name(), "Orthographic")

    def test_orthographic_true_scale_latitude(self):
        proj = ip.Orthographic(make_orthographic_label())
        self.assertAlmostEqual(proj.true_scale_latitude(), 40.0, places=8)

    def test_orthographic_ground_coordinate_round_trip(self):
        proj = ip.Orthographic(make_orthographic_label())
        self.assertTrue(proj.set_ground(40.0, -100.0))
        x, y = proj.x_coord(), proj.y_coord()
        self.assertTrue(proj.set_coordinate(x, y))
        self.assertAlmostEqual(proj.latitude(), 40.0, places=4)

    def test_orthographic_xy_range(self):
        proj = ip.Orthographic(make_orthographic_label())
        xy_range = proj.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)

    def test_orthographic_mapping_methods(self):
        proj = ip.Orthographic(make_orthographic_label())
        mapping = proj.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        self.assertTrue(proj.mapping_latitudes().has_keyword("MinimumLatitude"))
        self.assertTrue(proj.mapping_longitudes().has_keyword("MinimumLongitude"))


class MollweideUnitTest(unittest.TestCase):
    """Tests for Mollweide projection binding. Added: 2026-04-12."""

    def test_mollweide_construction_and_name(self):
        proj = ip.Mollweide(make_mollweide_label())
        self.assertEqual(proj.name(), "Mollweide")

    def test_mollweide_ground_coordinate_round_trip(self):
        proj = ip.Mollweide(make_mollweide_label())
        self.assertTrue(proj.set_ground(45.0, 90.0))
        x, y = proj.x_coord(), proj.y_coord()
        self.assertTrue(proj.set_coordinate(x, y))
        self.assertAlmostEqual(proj.latitude(), 45.0, places=4)

    def test_mollweide_newton_rapheson(self):
        proj = ip.Mollweide(make_mollweide_label())
        result = proj.newton_rapheson(0.5)
        self.assertIsInstance(result, float)

    def test_mollweide_xy_range(self):
        proj = ip.Mollweide(make_mollweide_label())
        xy_range = proj.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)

    def test_mollweide_mapping_methods(self):
        proj = ip.Mollweide(make_mollweide_label())
        mapping = proj.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        self.assertTrue(proj.mapping_latitudes().has_keyword("MinimumLatitude"))
        self.assertTrue(proj.mapping_longitudes().has_keyword("MinimumLongitude"))


class LambertConformalUnitTest(unittest.TestCase):
    """Tests for LambertConformal projection binding. Added: 2026-04-12."""

    def test_lambert_conformal_construction_and_name(self):
        proj = ip.LambertConformal(make_lambert_conformal_label())
        self.assertEqual(proj.name(), "LambertConformal")

    def test_lambert_conformal_true_scale_latitude(self):
        proj = ip.LambertConformal(make_lambert_conformal_label())
        tsl = proj.true_scale_latitude()
        self.assertIsInstance(tsl, float)

    def test_lambert_conformal_ground_coordinate_round_trip(self):
        proj = ip.LambertConformal(make_lambert_conformal_label())
        self.assertTrue(proj.set_ground(40.0, -96.0))
        x, y = proj.x_coord(), proj.y_coord()
        self.assertTrue(proj.set_coordinate(x, y))
        self.assertAlmostEqual(proj.latitude(), 40.0, places=4)

    def test_lambert_conformal_xy_range(self):
        proj = ip.LambertConformal(make_lambert_conformal_label())
        xy_range = proj.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)

    def test_lambert_conformal_mapping_methods(self):
        proj = ip.LambertConformal(make_lambert_conformal_label())
        mapping = proj.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        self.assertTrue(proj.mapping_latitudes().has_keyword("MinimumLatitude"))
        self.assertTrue(proj.mapping_longitudes().has_keyword("MinimumLongitude"))


class LambertAzimuthalEqualAreaUnitTest(unittest.TestCase):
    """Tests for LambertAzimuthalEqualArea projection binding. Added: 2026-04-12."""

    def test_lambert_azimuthal_construction_and_name(self):
        proj = ip.LambertAzimuthalEqualArea(make_lambert_azimuthal_label())
        self.assertEqual(proj.name(), "LambertAzimuthalEqualArea")

    def test_lambert_azimuthal_true_scale_latitude(self):
        proj = ip.LambertAzimuthalEqualArea(make_lambert_azimuthal_label())
        self.assertAlmostEqual(proj.true_scale_latitude(), 0.0, places=8)

    def test_lambert_azimuthal_scale_factors(self):
        proj = ip.LambertAzimuthalEqualArea(make_lambert_azimuthal_label())
        proj.set_ground(30.0, 45.0)
        h = proj.relative_scale_factor_longitude()
        k = proj.relative_scale_factor_latitude()
        self.assertIsInstance(h, float)
        self.assertIsInstance(k, float)

    def test_lambert_azimuthal_ground_coordinate_round_trip(self):
        proj = ip.LambertAzimuthalEqualArea(make_lambert_azimuthal_label())
        self.assertTrue(proj.set_ground(30.0, 45.0))
        x, y = proj.x_coord(), proj.y_coord()
        self.assertTrue(proj.set_coordinate(x, y))
        self.assertAlmostEqual(proj.latitude(), 30.0, places=4)

    def test_lambert_azimuthal_xy_range(self):
        proj = ip.LambertAzimuthalEqualArea(make_lambert_azimuthal_label())
        xy_range = proj.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)

    def test_lambert_azimuthal_mapping_methods(self):
        proj = ip.LambertAzimuthalEqualArea(make_lambert_azimuthal_label())
        mapping = proj.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        self.assertTrue(proj.mapping_latitudes().has_keyword("MinimumLatitude"))
        self.assertTrue(proj.mapping_longitudes().has_keyword("MinimumLongitude"))


class ObliqueCylindricalUnitTest(unittest.TestCase):
    """Tests for ObliqueCylindrical projection binding. Added: 2026-04-12."""

    def test_oblique_cylindrical_construction_and_name(self):
        proj = ip.ObliqueCylindrical(make_oblique_cylindrical_label())
        self.assertEqual(proj.name(), "ObliqueCylindrical")

    def test_oblique_cylindrical_pole_accessors(self):
        proj = ip.ObliqueCylindrical(make_oblique_cylindrical_label())
        self.assertAlmostEqual(proj.pole_latitude(), 22.858149, places=4)
        self.assertAlmostEqual(proj.pole_longitude(), 297.158602, places=4)
        self.assertAlmostEqual(proj.pole_rotation(), 45.7832, places=4)

    def test_oblique_cylindrical_ground_coordinate_round_trip(self):
        proj = ip.ObliqueCylindrical(make_oblique_cylindrical_label())
        self.assertTrue(proj.set_ground(-40.0, 100.0))
        x, y = proj.x_coord(), proj.y_coord()
        self.assertTrue(proj.set_coordinate(x, y))
        self.assertAlmostEqual(proj.latitude(), -40.0, places=4)

    def test_oblique_cylindrical_xy_range(self):
        proj = ip.ObliqueCylindrical(make_oblique_cylindrical_label())
        xy_range = proj.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)

    def test_oblique_cylindrical_mapping_methods(self):
        proj = ip.ObliqueCylindrical(make_oblique_cylindrical_label())
        mapping = proj.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        self.assertTrue(proj.mapping_latitudes().has_keyword("MinimumLatitude"))
        self.assertTrue(proj.mapping_longitudes().has_keyword("MinimumLongitude"))


class PointPerspectiveUnitTest(unittest.TestCase):
    """Tests for PointPerspective projection binding. Added: 2026-04-12."""

    def test_point_perspective_construction_and_name(self):
        proj = ip.PointPerspective(make_point_perspective_label())
        self.assertEqual(proj.name(), "PointPerspective")

    def test_point_perspective_true_scale_latitude(self):
        proj = ip.PointPerspective(make_point_perspective_label())
        self.assertAlmostEqual(proj.true_scale_latitude(), 0.0, places=8)

    def test_point_perspective_ground_coordinate_round_trip(self):
        proj = ip.PointPerspective(make_point_perspective_label())
        self.assertTrue(proj.set_ground(20.0, 20.0))
        x, y = proj.x_coord(), proj.y_coord()
        self.assertTrue(proj.set_coordinate(x, y))
        self.assertAlmostEqual(proj.latitude(), 20.0, places=4)

    def test_point_perspective_xy_range(self):
        proj = ip.PointPerspective(make_point_perspective_label())
        xy_range = proj.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)

    def test_point_perspective_mapping_methods(self):
        proj = ip.PointPerspective(make_point_perspective_label())
        mapping = proj.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        self.assertTrue(proj.mapping_latitudes().has_keyword("MinimumLatitude"))
        self.assertTrue(proj.mapping_longitudes().has_keyword("MinimumLongitude"))


class PolarStereographicUnitTest(unittest.TestCase):
    """Tests for PolarStereographic projection binding. Added: 2026-04-12."""

    def test_polar_stereographic_construction_and_name(self):
        proj = ip.PolarStereographic(make_polar_stereographic_label())
        self.assertEqual(proj.name(), "PolarStereographic")

    def test_polar_stereographic_true_scale_latitude(self):
        proj = ip.PolarStereographic(make_polar_stereographic_label())
        tsl = proj.true_scale_latitude()
        self.assertIsInstance(tsl, float)

    def test_polar_stereographic_ground_coordinate_round_trip(self):
        proj = ip.PolarStereographic(make_polar_stereographic_label())
        self.assertTrue(proj.set_ground(-75.0, -50.0))
        x, y = proj.x_coord(), proj.y_coord()
        self.assertTrue(proj.set_coordinate(x, y))
        self.assertAlmostEqual(proj.latitude(), -75.0, places=4)

    def test_polar_stereographic_xy_range(self):
        proj = ip.PolarStereographic(make_polar_stereographic_label())
        xy_range = proj.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)

    def test_polar_stereographic_mapping_methods(self):
        proj = ip.PolarStereographic(make_polar_stereographic_label())
        mapping = proj.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        self.assertTrue(proj.mapping_latitudes().has_keyword("MinimumLatitude"))
        self.assertTrue(proj.mapping_longitudes().has_keyword("MinimumLongitude"))


class TransverseMercatorUnitTest(unittest.TestCase):
    """Tests for TransverseMercator projection binding. Added: 2026-04-12."""

    def test_transverse_mercator_construction_and_name(self):
        proj = ip.TransverseMercator(make_transverse_mercator_label())
        self.assertEqual(proj.name(), "TransverseMercator")

    def test_transverse_mercator_ground_coordinate_round_trip(self):
        proj = ip.TransverseMercator(make_transverse_mercator_label())
        self.assertTrue(proj.set_ground(30.0, -75.0))
        x, y = proj.x_coord(), proj.y_coord()
        self.assertTrue(proj.set_coordinate(x, y))
        self.assertAlmostEqual(proj.latitude(), 30.0, places=4)

    def test_transverse_mercator_xy_range(self):
        proj = ip.TransverseMercator(make_transverse_mercator_label())
        xy_range = proj.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)

    def test_transverse_mercator_mapping_methods(self):
        proj = ip.TransverseMercator(make_transverse_mercator_label())
        mapping = proj.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        self.assertTrue(proj.mapping_latitudes().has_keyword("MinimumLatitude"))
        self.assertTrue(proj.mapping_longitudes().has_keyword("MinimumLongitude"))


class PlanarUnitTest(unittest.TestCase):
    """Tests for Planar (RingPlaneProjection) binding. Added: 2026-04-12."""

    def test_planar_construction_and_name(self):
        proj = ip.Planar(make_planar_label())
        self.assertEqual(proj.name(), "Planar")
        self.assertIsInstance(proj.version(), str)

    def test_planar_center_accessors(self):
        proj = ip.Planar(make_planar_label())
        self.assertAlmostEqual(proj.center_ring_longitude(), 0.0, places=8)
        self.assertAlmostEqual(proj.center_ring_radius(), 200000.0, places=8)

    def test_planar_true_scale_ring_radius(self):
        proj = ip.Planar(make_planar_label())
        tsr = proj.true_scale_ring_radius()
        self.assertIsInstance(tsr, float)

    def test_planar_requires_center_keywords(self):
        with self.assertRaises(Exception):
            ip.Planar(make_planar_label(include_center_longitude=False))
        with self.assertRaises(Exception):
            ip.Planar(make_planar_label(include_center_radius=False))

    def test_planar_allow_defaults(self):
        proj = ip.Planar(
            make_planar_label(include_center_longitude=False, include_center_radius=False),
            True,
        )
        self.assertEqual(proj.name(), "Planar")

    def test_planar_ground_coordinate_round_trip(self):
        proj = ip.Planar(make_planar_label())
        self.assertTrue(proj.set_ground(200000.0, 45.0))
        x, y = proj.x_coord(), proj.y_coord()
        self.assertTrue(proj.set_coordinate(x, y))
        self.assertAlmostEqual(proj.ring_radius(), 200000.0, places=4)

    def test_planar_xy_range(self):
        proj = ip.Planar(make_planar_label())
        xy_range = proj.xy_range()
        self.assertIsNotNone(xy_range)
        self.assertEqual(len(xy_range), 4)

    def test_planar_mapping_ring_methods(self):
        proj = ip.Planar(make_planar_label())
        mapping = proj.mapping()
        self.assertTrue(mapping.has_keyword("ProjectionName"))
        radii = proj.mapping_ring_radii()
        self.assertTrue(radii.has_keyword("MinimumRingRadius"))
        longitudes = proj.mapping_ring_longitudes()
        self.assertTrue(longitudes.has_keyword("MinimumRingLongitude"))


if __name__ == "__main__":
    unittest.main()
