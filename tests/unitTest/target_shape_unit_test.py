"""
Unit tests for ISIS Target and shape-model bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-03-21
"""

import unittest

from _unit_test_support import make_sky_target_label, ip


class TargetAndShapeUnitTest(unittest.TestCase):
    def test_target_sky_basics_follow_cpp_target_unit_test(self):
        label = make_sky_target_label()

        target = ip.Target(label)

        self.assertTrue(target.is_sky())
        self.assertEqual(target.name(), "Sky")
        self.assertIsNotNone(target.shape())
        self.assertEqual(target.shape().name(), "Ellipsoid")
        self.assertEqual(len(target.radii()), 3)

    def test_target_mutators_and_shape_switches(self):
        target = ip.Target(make_sky_target_label())

        target.set_name("CustomSky")
        target.set_radii(
            [
                ip.Distance(1000.0, ip.Distance.Units.Meters),
                ip.Distance(1000.0, ip.Distance.Units.Meters),
                ip.Distance(1000.0, ip.Distance.Units.Meters),
            ]
        )
        target.set_shape_ellipsoid()
        target.restore_shape()

        self.assertEqual(target.name(), "CustomSky")
        self.assertEqual(len(target.radii()), 3)
        self.assertIsNotNone(target.shape())
        self.assertEqual(target.shape().name(), "Ellipsoid")

    def test_target_static_radii_helpers_and_naif_lookup(self):
        try:
            mars_radii = ip.Target.radii_group_for_target("Mars")
        except Exception as error:
            self.skipTest(f"Target radii kernels unavailable in this environment: {error}")

        self.assertTrue(mars_radii.has_keyword("EquatorialRadius"))
        self.assertTrue(mars_radii.has_keyword("PolarRadius"))

        label = ip.Pvl()
        label.from_string(
            """
Object = IsisCube
  Group = Instrument
    TargetName = Mars
  EndGroup
EndObject
End
"""
        )
        mapping_group = ip.PvlGroup("Mapping")
        mapping_group.add_keyword(ip.PvlKeyword("TargetName", "Mars"))

        derived_radii = ip.Target.radii_group_from_label(label, mapping_group)
        self.assertEqual(derived_radii.find_keyword("TargetName")[0], "Mars")
        self.assertEqual(ip.Target.lookup_naif_body_code("Mars"), 499)

        with self.assertRaises(Exception):
            ip.Target.lookup_naif_body_code("HanSolo")

    def test_shape_model_factory_returns_ellipsoid_for_sky_target(self):
        label = make_sky_target_label(shape_model="Null")
        target = ip.Target(label)

        shape = ip.ShapeModelFactory.create(target, label)

        self.assertEqual(shape.name(), "Ellipsoid")
        self.assertFalse(shape.is_dem())

    def test_default_shape_types_and_tolerances(self):
        ellipsoid = ip.EllipsoidShape()
        dem_shape = ip.DemShape()
        plane_shape = ip.PlaneShape()
        naif_shape = ip.NaifDskShape()
        embree_shape = ip.EmbreeShapeModel()
        bullet_shape = ip.BulletShapeModel()

        embree_shape.set_tolerance(0.25)
        bullet_shape.set_tolerance(0.5)

        self.assertEqual(ellipsoid.name(), "Ellipsoid")
        self.assertEqual(dem_shape.name(), "DemShape")
        self.assertEqual(plane_shape.name(), "Plane")
        self.assertEqual(naif_shape.name(), "DSK")
        self.assertEqual(embree_shape.name(), "Embree")
        self.assertEqual(bullet_shape.name(), "Bullet")
        self.assertFalse(ellipsoid.is_dem())
        self.assertTrue(dem_shape.is_dem())
        self.assertFalse(plane_shape.is_dem())
        self.assertFalse(naif_shape.is_dem())
        self.assertFalse(embree_shape.is_dem())
        self.assertFalse(bullet_shape.is_dem())
        self.assertAlmostEqual(embree_shape.get_tolerance(), 0.25)
        self.assertAlmostEqual(bullet_shape.get_tolerance(), 0.5)

    def test_shape_surface_point_lifecycle(self):
        ellipsoid = ip.EllipsoidShape()
        surface_point = ip.SurfacePoint(
            ip.Latitude(5.0, ip.Angle.Units.Degrees),
            ip.Longitude(25.0, ip.Angle.Units.Degrees),
            ip.Distance(3396.19, ip.Distance.Units.Kilometers),
        )

        ellipsoid.set_surface_point(surface_point)
        self.assertTrue(ellipsoid.has_intersection())
        self.assertTrue(ellipsoid.surface_intersection().valid())

        ellipsoid.clear_surface_point()
        self.assertFalse(ellipsoid.has_intersection())


if __name__ == "__main__":
    unittest.main()
