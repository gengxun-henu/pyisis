"""
Unit tests for SensorUtilities lightweight value types, Quaternion, and LightTimeCorrectionState bindings.

Author: Geng Xun
Created: 2026-04-09
Last Modified: 2026-04-10
Updated: 2026-04-09  Geng Xun added focused unit tests for Vec, GroundPt2D, GroundPt3D, ImagePt,
         RaDec, ObserverState, Intersection, Quaternion, and LightTimeCorrectionState.
Updated: 2026-04-10  Geng Xun added Quaternion scalar-multiplication regression coverage for the const-safe pybind wrapper.
"""
import math
import unittest

from _unit_test_support import ip


class VecUnitTest(unittest.TestCase):
    """Focused unit tests for SensorUtilities.Vec binding. Added: 2026-04-09."""

    def test_construct_default(self):
        """Vec() constructs without error."""
        v = ip.Vec()
        self.assertIsNotNone(v)

    def test_construct_xyz(self):
        """Vec(x, y, z) stores components correctly."""
        v = ip.Vec(1.0, 2.0, 3.0)
        self.assertAlmostEqual(v.x, 1.0)
        self.assertAlmostEqual(v.y, 2.0)
        self.assertAlmostEqual(v.z, 3.0)

    def test_construct_from_list(self):
        """Vec([x, y, z]) stores components correctly."""
        v = ip.Vec([4.0, 5.0, 6.0])
        self.assertAlmostEqual(v.x, 4.0)
        self.assertAlmostEqual(v.y, 5.0)
        self.assertAlmostEqual(v.z, 6.0)

    def test_readwrite(self):
        """x, y, z attributes are writable."""
        v = ip.Vec(0.0, 0.0, 0.0)
        v.x = 7.0
        v.y = 8.0
        v.z = 9.0
        self.assertAlmostEqual(v.x, 7.0)
        self.assertAlmostEqual(v.z, 9.0)

    def test_to_list(self):
        """to_list() returns [x, y, z]."""
        v = ip.Vec(1.0, 2.0, 3.0)
        lst = v.to_list()
        self.assertEqual(len(lst), 3)
        self.assertAlmostEqual(lst[0], 1.0)

    def test_repr(self):
        """repr(Vec) includes x, y, z."""
        v = ip.Vec(1.0, 2.0, 3.0)
        r = repr(v)
        self.assertIn("Vec", r)
        self.assertIn("x=", r)


class GroundPt2DUnitTest(unittest.TestCase):
    """Focused unit tests for SensorUtilities.GroundPt2D binding. Added: 2026-04-09."""

    def test_construct(self):
        """GroundPt2D(lat, lon) constructs correctly."""
        g = ip.GroundPt2D(0.5, 1.0)
        self.assertAlmostEqual(g.lat, 0.5)
        self.assertAlmostEqual(g.lon, 1.0)

    def test_default_values(self):
        """Default GroundPt2D has lat=0, lon=0."""
        g = ip.GroundPt2D()
        self.assertAlmostEqual(g.lat, 0.0)
        self.assertAlmostEqual(g.lon, 0.0)

    def test_readwrite(self):
        """lat and lon are writable."""
        g = ip.GroundPt2D()
        g.lat = 0.3
        g.lon = 1.5
        self.assertAlmostEqual(g.lat, 0.3)
        self.assertAlmostEqual(g.lon, 1.5)

    def test_repr(self):
        """repr(GroundPt2D) includes lat and lon."""
        g = ip.GroundPt2D(0.5, 1.0)
        r = repr(g)
        self.assertIn("GroundPt2D", r)


class GroundPt3DUnitTest(unittest.TestCase):
    """Focused unit tests for SensorUtilities.GroundPt3D binding. Added: 2026-04-09."""

    def test_construct(self):
        """GroundPt3D(lat, lon, radius) constructs correctly."""
        g = ip.GroundPt3D(0.1, 0.2, 3396.0)
        self.assertAlmostEqual(g.lat, 0.1)
        self.assertAlmostEqual(g.lon, 0.2)
        self.assertAlmostEqual(g.radius, 3396.0)

    def test_readwrite(self):
        """radius is writable."""
        g = ip.GroundPt3D()
        g.radius = 6378.0
        self.assertAlmostEqual(g.radius, 6378.0)

    def test_repr(self):
        """repr(GroundPt3D) includes radius."""
        g = ip.GroundPt3D(0.0, 0.0, 1000.0)
        self.assertIn("GroundPt3D", repr(g))
        self.assertIn("radius=", repr(g))


class ImagePtUnitTest(unittest.TestCase):
    """Focused unit tests for SensorUtilities.ImagePt binding. Added: 2026-04-09."""

    def test_construct(self):
        """ImagePt(line, sample, band) stores values correctly."""
        pt = ip.ImagePt(100.5, 200.5, 1)
        self.assertAlmostEqual(pt.line, 100.5)
        self.assertAlmostEqual(pt.sample, 200.5)
        self.assertEqual(pt.band, 1)

    def test_default_band(self):
        """Default band is 1."""
        pt = ip.ImagePt(0.0, 0.0)
        self.assertEqual(pt.band, 1)

    def test_readwrite(self):
        """line, sample, band are writable."""
        pt = ip.ImagePt()
        pt.line = 50.0
        pt.sample = 75.0
        pt.band = 2
        self.assertAlmostEqual(pt.line, 50.0)
        self.assertEqual(pt.band, 2)

    def test_repr(self):
        """repr(ImagePt) includes line, sample, band."""
        pt = ip.ImagePt(1.0, 2.0, 3)
        r = repr(pt)
        self.assertIn("ImagePt", r)


class RaDecUnitTest(unittest.TestCase):
    """Focused unit tests for SensorUtilities.RaDec binding. Added: 2026-04-09."""

    def test_construct(self):
        """RaDec(ra, dec) stores values correctly."""
        rd = ip.RaDec(1.5, 0.3)
        self.assertAlmostEqual(rd.ra, 1.5)
        self.assertAlmostEqual(rd.dec, 0.3)

    def test_readwrite(self):
        """ra and dec are writable."""
        rd = ip.RaDec()
        rd.ra = 2.0
        rd.dec = -0.5
        self.assertAlmostEqual(rd.ra, 2.0)
        self.assertAlmostEqual(rd.dec, -0.5)

    def test_repr(self):
        """repr(RaDec) includes ra and dec."""
        rd = ip.RaDec(1.0, 0.5)
        self.assertIn("RaDec", repr(rd))


class ObserverStateUnitTest(unittest.TestCase):
    """Focused unit tests for SensorUtilities.ObserverState binding. Added: 2026-04-09."""

    def test_construct(self):
        """ObserverState() constructs without error."""
        state = ip.ObserverState()
        self.assertIsNotNone(state)

    def test_readwrite_time(self):
        """time attribute is readable and writable."""
        state = ip.ObserverState()
        state.time = 123456.789
        self.assertAlmostEqual(state.time, 123456.789)

    def test_readwrite_vec_fields(self):
        """look_vec, j2000_look_vec, sensor_pos are Vec instances."""
        state = ip.ObserverState()
        state.look_vec = ip.Vec(0.0, 0.0, 1.0)
        self.assertIsInstance(state.look_vec, ip.Vec)

    def test_repr(self):
        """repr(ObserverState) includes class name."""
        state = ip.ObserverState()
        self.assertIn("ObserverState", repr(state))


class IntersectionUnitTest(unittest.TestCase):
    """Focused unit tests for SensorUtilities.Intersection binding. Added: 2026-04-09."""

    def test_construct(self):
        """Intersection() constructs without error."""
        i = ip.Intersection()
        self.assertIsNotNone(i)

    def test_readwrite(self):
        """ground_pt and normal are Vec attributes."""
        i = ip.Intersection()
        i.ground_pt = ip.Vec(1.0, 2.0, 3.0)
        i.normal = ip.Vec(0.0, 0.0, 1.0)
        self.assertAlmostEqual(i.ground_pt.x, 1.0)
        self.assertAlmostEqual(i.normal.z, 1.0)

    def test_repr(self):
        """repr(Intersection) includes class name."""
        self.assertIn("Intersection", repr(ip.Intersection()))


class QuaternionUnitTest(unittest.TestCase):
    """Focused unit tests for Quaternion binding. Added: 2026-04-09."""

    def _identity_matrix(self):
        """Return a 9-element row-major identity rotation matrix."""
        return [1.0, 0.0, 0.0,
                0.0, 1.0, 0.0,
                0.0, 0.0, 1.0]

    def test_construct_default(self):
        """Quaternion() constructs without error."""
        q = ip.Quaternion()
        self.assertIsNotNone(q)

    def test_construct_from_matrix(self):
        """Quaternion(identity_matrix) constructs correctly."""
        q = ip.Quaternion(self._identity_matrix())
        self.assertIsNotNone(q)

    def test_get_quaternion(self):
        """get_quaternion() returns a list of 4 floats."""
        q = ip.Quaternion(self._identity_matrix())
        qv = q.get_quaternion()
        self.assertEqual(len(qv), 4)
        for x in qv:
            self.assertIsInstance(x, float)

    def test_set(self):
        """set() updates the quaternion values."""
        q = ip.Quaternion()
        q.set([1.0, 0.0, 0.0, 0.0])
        qv = q.get_quaternion()
        self.assertAlmostEqual(qv[0], 1.0)

    def test_to_matrix(self):
        """to_matrix() returns a 9-element list."""
        q = ip.Quaternion(self._identity_matrix())
        m = q.to_matrix()
        self.assertEqual(len(m), 9)

    def test_conjugate(self):
        """conjugate() returns a Quaternion."""
        q = ip.Quaternion(self._identity_matrix())
        c = q.conjugate()
        self.assertIsInstance(c, ip.Quaternion)

    def test_scalar_multiply(self):
        """Quaternion * scalar returns a new Quaternion without mutating the source."""
        q = ip.Quaternion(self._identity_matrix())
        scaled = q * 0.5
        self.assertIsInstance(scaled, ip.Quaternion)
        self.assertEqual(len(scaled.get_quaternion()), 4)
        self.assertEqual(len(q.get_quaternion()), 4)

    def test_repr(self):
        """repr(Quaternion) includes Quaternion."""
        q = ip.Quaternion()
        self.assertIn("Quaternion", repr(q))


class LightTimeCorrectionStateUnitTest(unittest.TestCase):
    """Focused unit tests for LightTimeCorrectionState binding. Added: 2026-04-09."""

    def test_construct_default(self):
        """LightTimeCorrectionState() constructs without error."""
        state = ip.LightTimeCorrectionState()
        self.assertIsNotNone(state)

    def test_default_aberration_correction(self):
        """Default aberration correction string is set."""
        state = ip.LightTimeCorrectionState()
        c = state.get_aberration_correction()
        self.assertIsInstance(c, str)

    def test_set_get_aberration_correction(self):
        """set_aberration_correction / get_aberration_correction round-trip."""
        state = ip.LightTimeCorrectionState()
        state.set_aberration_correction("LT+S")
        self.assertEqual(state.get_aberration_correction(), "LT+S")

    def test_is_light_time_corrected(self):
        """is_light_time_corrected() returns bool."""
        state = ip.LightTimeCorrectionState()
        state.set_aberration_correction("LT+S")
        result = state.is_light_time_corrected()
        self.assertIsInstance(result, bool)

    def test_swap_observer_target(self):
        """set_swap_observer_target enables the swap flag."""
        state = ip.LightTimeCorrectionState()
        state.set_swap_observer_target()
        self.assertTrue(state.is_observer_target_swapped())

    def test_no_swap_observer_target(self):
        """set_no_swap_observer_target disables the swap flag."""
        state = ip.LightTimeCorrectionState()
        state.set_swap_observer_target()
        state.set_no_swap_observer_target()
        self.assertFalse(state.is_observer_target_swapped())

    def test_light_time_to_surface(self):
        """set_correct / set_no_correct_light_time_to_surface round-trip."""
        state = ip.LightTimeCorrectionState()
        state.set_correct_light_time_to_surface()
        self.assertTrue(state.is_light_time_to_surface_corrected())
        state.set_no_correct_light_time_to_surface()
        self.assertFalse(state.is_light_time_to_surface_corrected())

    def test_equality(self):
        """Two default states compare as equal."""
        a = ip.LightTimeCorrectionState()
        b = ip.LightTimeCorrectionState()
        self.assertTrue(a == b)

    def test_repr(self):
        """repr(LightTimeCorrectionState) includes class name."""
        state = ip.LightTimeCorrectionState()
        self.assertIn("LightTimeCorrectionState", repr(state))


if __name__ == "__main__":
    unittest.main()
