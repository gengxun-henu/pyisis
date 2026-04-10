"""
Unit tests for SpicePosition, SpiceRotation, and SpacecraftPosition bindings.

Author: Geng Xun
Created: 2026-04-10
Last Modified: 2026-04-10
Updated: 2026-04-10  Geng Xun added focused unit tests for SpicePosition, SpiceRotation,
         and SpacecraftPosition covering constructor, time-bias, aberration correction,
         and cached-state queries that do not require NAIF kernel data.
"""
import math
import unittest

from _unit_test_support import ip


class SpicePositionUnitTest(unittest.TestCase):
    """Focused unit tests for SpicePosition binding. Added: 2026-04-10."""

    # Earth (NAIF 399) observed from MRO (-94) is a typical test pair.
    TARGET_CODE = 399      # Earth
    OBSERVER_CODE = -94    # MRO spacecraft

    def test_construct(self):
        """SpicePosition(target, observer) constructs without error."""
        sp = ip.SpicePosition(self.TARGET_CODE, self.OBSERVER_CODE)
        self.assertIsNotNone(sp)

    def test_get_time_bias_default(self):
        """get_time_bias() returns 0.0 for a newly constructed SpicePosition."""
        sp = ip.SpicePosition(self.TARGET_CODE, self.OBSERVER_CODE)
        self.assertAlmostEqual(sp.get_time_bias(), 0.0)

    def test_set_get_time_bias(self):
        """set_time_bias()/get_time_bias() round-trip correctly."""
        sp = ip.SpicePosition(self.TARGET_CODE, self.OBSERVER_CODE)
        sp.set_time_bias(2.5)
        self.assertAlmostEqual(sp.get_time_bias(), 2.5)

    def test_is_cached_initial_false(self):
        """is_cached() returns False for a newly constructed SpicePosition."""
        sp = ip.SpicePosition(self.TARGET_CODE, self.OBSERVER_CODE)
        self.assertFalse(sp.is_cached())

    def test_cache_size_initial_zero(self):
        """cache_size() returns 0 for a newly constructed SpicePosition."""
        sp = ip.SpicePosition(self.TARGET_CODE, self.OBSERVER_CODE)
        self.assertEqual(sp.cache_size(), 0)

    def test_has_velocity_initial_false(self):
        """has_velocity() returns False before loading kernel data."""
        sp = ip.SpicePosition(self.TARGET_CODE, self.OBSERVER_CODE)
        self.assertFalse(sp.has_velocity())

    def test_get_aberration_correction_default(self):
        """get_aberration_correction() returns 'LT+S' by default."""
        sp = ip.SpicePosition(self.TARGET_CODE, self.OBSERVER_CODE)
        corr = sp.get_aberration_correction()
        self.assertIsInstance(corr, str)
        # The default correction is LT+S (with light time and stellar aberration)
        self.assertEqual(corr, "LT+S")

    def test_set_get_aberration_correction(self):
        """set_aberration_correction()/get_aberration_correction() round-trip."""
        sp = ip.SpicePosition(self.TARGET_CODE, self.OBSERVER_CODE)
        sp.set_aberration_correction("NONE")
        self.assertEqual(sp.get_aberration_correction(), "NONE")

    def test_source_enum_accessible(self):
        """SpicePositionSource enum values are accessible."""
        self.assertIsNotNone(ip.SpicePositionSource.Spice)
        self.assertIsNotNone(ip.SpicePositionSource.Memcache)
        self.assertIsNotNone(ip.SpicePositionSource.HermiteCache)
        self.assertIsNotNone(ip.SpicePositionSource.PolyFunction)
        self.assertIsNotNone(ip.SpicePositionSource.PolyFunctionOverHermiteConstant)

    def test_partial_type_enum_accessible(self):
        """SpicePositionPartialType enum values are accessible."""
        self.assertIsNotNone(ip.SpicePositionPartialType.WRT_X)
        self.assertIsNotNone(ip.SpicePositionPartialType.WRT_Y)
        self.assertIsNotNone(ip.SpicePositionPartialType.WRT_Z)

    def test_repr(self):
        """__repr__ contains 'SpicePosition'."""
        sp = ip.SpicePosition(self.TARGET_CODE, self.OBSERVER_CODE)
        self.assertIn("SpicePosition", repr(sp))


class SpiceRotationUnitTest(unittest.TestCase):
    """Focused unit tests for SpiceRotation binding. Added: 2026-04-10."""

    # MRO instrument frame code
    FRAME_CODE = -94000

    def test_construct_single(self):
        """SpiceRotation(frame_code) constructs without error."""
        sr = ip.SpiceRotation(self.FRAME_CODE)
        self.assertIsNotNone(sr)

    def test_frame(self):
        """frame() returns the frame code set at construction."""
        sr = ip.SpiceRotation(self.FRAME_CODE)
        self.assertEqual(sr.frame(), self.FRAME_CODE)

    def test_set_frame(self):
        """set_frame(code) updates the frame code."""
        sr = ip.SpiceRotation(self.FRAME_CODE)
        sr.set_frame(-94001)
        self.assertEqual(sr.frame(), -94001)

    def test_set_time_bias(self):
        """set_time_bias() executes without error."""
        sr = ip.SpiceRotation(self.FRAME_CODE)
        sr.set_time_bias(1.0)  # just confirm it does not raise

    def test_is_cached_initial_false(self):
        """is_cached() returns False for newly constructed SpiceRotation."""
        sr = ip.SpiceRotation(self.FRAME_CODE)
        self.assertFalse(sr.is_cached())

    def test_cache_size_initial_zero(self):
        """cache_size() returns 0 for newly constructed SpiceRotation."""
        sr = ip.SpiceRotation(self.FRAME_CODE)
        self.assertEqual(sr.cache_size(), 0)

    def test_has_angular_velocity_false(self):
        """has_angular_velocity() returns False before loading kernel data."""
        sr = ip.SpiceRotation(self.FRAME_CODE)
        self.assertFalse(sr.has_angular_velocity())

    def test_source_enum_accessible(self):
        """SpiceRotationSource enum values are accessible."""
        self.assertIsNotNone(ip.SpiceRotationSource.Spice)
        self.assertIsNotNone(ip.SpiceRotationSource.Nadir)
        self.assertIsNotNone(ip.SpiceRotationSource.Memcache)
        self.assertIsNotNone(ip.SpiceRotationSource.PolyFunction)
        self.assertIsNotNone(ip.SpiceRotationSource.PolyFunctionOverSpice)
        self.assertIsNotNone(ip.SpiceRotationSource.PckPolyFunction)

    def test_partial_type_enum_accessible(self):
        """SpiceRotationPartialType enum values are accessible."""
        self.assertIsNotNone(ip.SpiceRotationPartialType.WRT_RightAscension)
        self.assertIsNotNone(ip.SpiceRotationPartialType.WRT_Declination)
        self.assertIsNotNone(ip.SpiceRotationPartialType.WRT_Twist)

    def test_downsize_status_enum_accessible(self):
        """SpiceRotationDownsizeStatus enum values are accessible."""
        self.assertIsNotNone(ip.SpiceRotationDownsizeStatus.Yes)
        self.assertIsNotNone(ip.SpiceRotationDownsizeStatus.Done)
        self.assertIsNotNone(ip.SpiceRotationDownsizeStatus.No)

    def test_frame_type_enum_accessible(self):
        """SpiceRotationFrameType enum values are accessible."""
        self.assertIsNotNone(ip.SpiceRotationFrameType.UNKNOWN)
        self.assertIsNotNone(ip.SpiceRotationFrameType.INERTL)
        self.assertIsNotNone(ip.SpiceRotationFrameType.PCK)
        self.assertIsNotNone(ip.SpiceRotationFrameType.CK)
        self.assertIsNotNone(ip.SpiceRotationFrameType.TK)

    def test_repr(self):
        """__repr__ contains 'SpiceRotation'."""
        sr = ip.SpiceRotation(self.FRAME_CODE)
        self.assertIn("SpiceRotation", repr(sr))


class SpacecraftPositionUnitTest(unittest.TestCase):
    """Focused unit tests for SpacecraftPosition binding. Added: 2026-04-10."""

    TARGET_CODE = 399      # Earth
    OBSERVER_CODE = -94    # MRO

    def test_construct_two_arg(self):
        """SpacecraftPosition(target, observer) constructs without error."""
        scp = ip.SpacecraftPosition(self.TARGET_CODE, self.OBSERVER_CODE)
        self.assertIsNotNone(scp)

    def test_construct_with_lt_state(self):
        """SpacecraftPosition(target, observer, lt_state, radius) constructs."""
        lt = ip.LightTimeCorrectionState()
        r = ip.Distance(0.0, ip.Distance.Meters)
        scp = ip.SpacecraftPosition(self.TARGET_CODE, self.OBSERVER_CODE, lt, r)
        self.assertIsNotNone(scp)

    def test_inherits_time_bias(self):
        """SpacecraftPosition inherits set/get_time_bias from SpicePosition."""
        scp = ip.SpacecraftPosition(self.TARGET_CODE, self.OBSERVER_CODE)
        scp.set_time_bias(3.0)
        self.assertAlmostEqual(scp.get_time_bias(), 3.0)

    def test_inherits_is_cached(self):
        """SpacecraftPosition inherits is_cached() from SpicePosition."""
        scp = ip.SpacecraftPosition(self.TARGET_CODE, self.OBSERVER_CODE)
        self.assertFalse(scp.is_cached())

    def test_get_distance_light_time_static(self):
        """get_distance_light_time(distance) returns positive time for positive distance."""
        d = ip.Distance(3e8, ip.Distance.Meters)   # 300 million meters ~ 1 second
        lt = ip.SpacecraftPosition.get_distance_light_time(d)
        self.assertGreater(lt, 0.0)

    def test_aberration_correction(self):
        """set/get_aberration_correction round-trip for SpacecraftPosition."""
        scp = ip.SpacecraftPosition(self.TARGET_CODE, self.OBSERVER_CODE)
        scp.set_aberration_correction("NONE")
        self.assertEqual(scp.get_aberration_correction(), "NONE")

    def test_repr(self):
        """__repr__ contains 'SpacecraftPosition'."""
        scp = ip.SpacecraftPosition(self.TARGET_CODE, self.OBSERVER_CODE)
        self.assertIn("SpacecraftPosition", repr(scp))


class SensorMatrixUnitTest(unittest.TestCase):
    """Focused unit tests for SensorUtilities::Matrix (SensorMatrix) binding. Added: 2026-04-10."""

    def test_construct_default(self):
        """SensorMatrix() constructs a zero matrix without error."""
        m = ip.SensorMatrix()
        self.assertIsNotNone(m)

    def test_default_rows_are_zero(self):
        """Default SensorMatrix has all-zero rows."""
        m = ip.SensorMatrix()
        for attr in ('a', 'b', 'c'):
            row = getattr(m, attr)
            self.assertAlmostEqual(row.x, 0.0)
            self.assertAlmostEqual(row.y, 0.0)
            self.assertAlmostEqual(row.z, 0.0)

    def test_construct_from_vecs(self):
        """SensorMatrix(a, b, c) stores Vec rows correctly."""
        a = ip.Vec(1.0, 0.0, 0.0)
        b = ip.Vec(0.0, 1.0, 0.0)
        c = ip.Vec(0.0, 0.0, 1.0)
        mat = ip.SensorMatrix(a, b, c)
        self.assertAlmostEqual(mat.a.x, 1.0)
        self.assertAlmostEqual(mat.b.y, 1.0)
        self.assertAlmostEqual(mat.c.z, 1.0)

    def test_readwrite_fields(self):
        """Rows a, b, c are read-writable."""
        mat = ip.SensorMatrix()
        mat.a = ip.Vec(2.0, 0.0, 0.0)
        self.assertAlmostEqual(mat.a.x, 2.0)

    def test_identity_mat_vec_product(self):
        """Identity SensorMatrix * Vec returns Vec unchanged."""
        a = ip.Vec(1.0, 0.0, 0.0)
        b = ip.Vec(0.0, 1.0, 0.0)
        c = ip.Vec(0.0, 0.0, 1.0)
        mat = ip.SensorMatrix(a, b, c)
        v = ip.Vec(3.0, 5.0, 7.0)
        result = mat.mat_vec_product(v)
        self.assertAlmostEqual(result.x, 3.0)
        self.assertAlmostEqual(result.y, 5.0)
        self.assertAlmostEqual(result.z, 7.0)

    def test_repr(self):
        """__repr__ contains 'SensorMatrix'."""
        mat = ip.SensorMatrix()
        self.assertIn("SensorMatrix", repr(mat))


if __name__ == '__main__':
    unittest.main()
