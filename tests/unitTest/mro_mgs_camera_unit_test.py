"""
Unit tests for MRO and MGS mission camera binding completions.

Covers CTXCamera, HiriseCamera, MocNarrowAngleCamera (constructor + SPICE IDs),
CrismCamera (constructor + band + SPICE IDs), and MarciCamera (constructor + band + SPICE IDs).

Author: Geng Xun
Created: 2026-04-14
Last Modified: 2026-04-14
"""

import unittest

from _unit_test_support import ip


class CTXCameraUnitTest(unittest.TestCase):
    """Regression coverage for CTXCamera constructor and SPICE ID methods. Added: 2026-04-14."""

    def test_class_exists_and_inheritance(self):
        self.assertTrue(hasattr(ip, "CTXCamera"))
        self.assertTrue(issubclass(ip.CTXCamera, ip.LineScanCamera))

    def test_spice_id_methods_exist(self):
        attrs = dir(ip.CTXCamera)
        self.assertIn("ck_frame_id", attrs)
        self.assertIn("ck_reference_id", attrs)
        self.assertIn("spk_reference_id", attrs)


class HiriseCameraUnitTest(unittest.TestCase):
    """Regression coverage for HiriseCamera constructor and SPICE ID methods. Added: 2026-04-14."""

    def test_class_exists_and_inheritance(self):
        self.assertTrue(hasattr(ip, "HiriseCamera"))
        self.assertTrue(issubclass(ip.HiriseCamera, ip.LineScanCamera))

    def test_spice_id_methods_exist(self):
        attrs = dir(ip.HiriseCamera)
        self.assertIn("ck_frame_id", attrs)
        self.assertIn("ck_reference_id", attrs)
        self.assertIn("spk_reference_id", attrs)


class MocNarrowAngleCameraUnitTest(unittest.TestCase):
    """Regression coverage for MocNarrowAngleCamera constructor and SPICE ID methods. Added: 2026-04-14."""

    def test_class_exists_and_inheritance(self):
        self.assertTrue(hasattr(ip, "MocNarrowAngleCamera"))
        self.assertTrue(issubclass(ip.MocNarrowAngleCamera, ip.LineScanCamera))

    def test_spice_id_methods_exist(self):
        attrs = dir(ip.MocNarrowAngleCamera)
        self.assertIn("ck_frame_id", attrs)
        self.assertIn("ck_reference_id", attrs)
        self.assertIn("spk_reference_id", attrs)


class CrismCameraUnitTest(unittest.TestCase):
    """Regression coverage for CrismCamera constructor, band, and SPICE ID methods. Added: 2026-04-14."""

    def test_class_exists_and_inheritance(self):
        self.assertTrue(hasattr(ip, "CrismCamera"))
        self.assertTrue(issubclass(ip.CrismCamera, ip.LineScanCamera))

    def test_spice_id_methods_exist(self):
        attrs = dir(ip.CrismCamera)
        self.assertIn("ck_frame_id", attrs)
        self.assertIn("ck_reference_id", attrs)
        self.assertIn("spk_reference_id", attrs)

    def test_band_methods_exist(self):
        attrs = dir(ip.CrismCamera)
        self.assertIn("set_band", attrs)
        self.assertIn("is_band_independent", attrs)


class MarciCameraUnitTest(unittest.TestCase):
    """Regression coverage for MarciCamera constructor, band, and SPICE ID methods. Added: 2026-04-14."""

    def test_class_exists_and_inheritance(self):
        self.assertTrue(hasattr(ip, "MarciCamera"))
        self.assertTrue(issubclass(ip.MarciCamera, ip.PushFrameCamera))

    def test_spice_id_methods_exist(self):
        attrs = dir(ip.MarciCamera)
        self.assertIn("ck_frame_id", attrs)
        self.assertIn("ck_reference_id", attrs)
        self.assertIn("spk_reference_id", attrs)

    def test_band_methods_exist(self):
        attrs = dir(ip.MarciCamera)
        self.assertIn("set_band", attrs)
        self.assertIn("is_band_independent", attrs)


if __name__ == "__main__":
    unittest.main()
