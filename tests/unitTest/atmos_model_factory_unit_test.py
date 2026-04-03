"""
Unit tests for ISIS PhotoModelFactory and AtmosModelFactory bindings

Author: Geng Xun
Created: 2026-04-04
Last Modified: 2026-04-04
"""
import unittest

from _unit_test_support import ip


class AtmosModelFactoryUnitTest(unittest.TestCase):
    """Test suite for photometric and atmospheric factory bindings. Added: 2026-04-04."""

    @staticmethod
    def _make_photo_pvl(name="Lambert"):
        pvl = ip.Pvl()
        photometric = ip.PvlObject("PhotometricModel")
        algorithm = ip.PvlGroup("Algorithm")
        algorithm.add_keyword(ip.PvlKeyword("Name", name))
        photometric.add_group(algorithm)
        pvl.add_object(photometric)
        return pvl

    @classmethod
    def _make_photo_atmos_pvl(cls, photo_name="Lambert", atmos_name="Isotropic1"):
        pvl = cls._make_photo_pvl(photo_name)
        atmospheric = ip.PvlObject("AtmosphericModel")
        algorithm = ip.PvlGroup("Algorithm")
        algorithm.add_keyword(ip.PvlKeyword("Name", atmos_name))
        atmospheric.add_group(algorithm)
        pvl.add_object(atmospheric)
        return pvl

    def test_photo_model_factory_symbol_presence(self):
        """PhotoModelFactory should be exported with a callable create method."""
        self.assertTrue(hasattr(ip, "PhotoModelFactory"))
        self.assertTrue(hasattr(ip.PhotoModelFactory, "create"))
        self.assertTrue(callable(ip.PhotoModelFactory.create))

    def test_photo_model_factory_create_lambert(self):
        """PhotoModelFactory.create should return a working photo model instance."""
        pvl = self._make_photo_pvl("Lambert")
        photo_model = ip.PhotoModelFactory.create(pvl)

        self.assertEqual(photo_model.algorithm_name(), "Lambert")
        self.assertIsInstance(photo_model.standard_conditions(), bool)
        self.assertIsInstance(photo_model.calc_surf_albedo(0.0, 0.0, 0.0), float)
        self.assertIn("PhotoModel", repr(photo_model))

    def test_photo_model_factory_invalid_pvl_raises(self):
        """PhotoModelFactory.create should raise IException for missing model definition."""
        with self.assertRaises(ip.IException):
            ip.PhotoModelFactory.create(ip.Pvl())

    def test_atmos_model_factory_symbol_presence(self):
        """AtmosModelFactory should be exported with a callable create method."""
        self.assertTrue(hasattr(ip, "AtmosModelFactory"))
        self.assertTrue(hasattr(ip.AtmosModelFactory, "create"))
        self.assertTrue(callable(ip.AtmosModelFactory.create))

    def test_atmos_model_factory_create_isotropic1(self):
        """AtmosModelFactory.create should return a working atmosphere model instance."""
        pvl = self._make_photo_atmos_pvl()
        photo_model = ip.PhotoModelFactory.create(pvl)
        atmos_model = ip.AtmosModelFactory.create(pvl, photo_model)

        self.assertEqual(photo_model.algorithm_name(), "Lambert")
        # Upstream AtmosModel base constructor initializes algorithm name as "Unknown"
        # unless a derived implementation updates it explicitly.
        self.assertEqual(atmos_model.algorithm_name(), "Unknown")
        self.assertAlmostEqual(atmos_model.atmos_tau(), 0.28, places=6)
        self.assertAlmostEqual(atmos_model.atmos_wha(), 0.95, places=6)

        effect = atmos_model.calc_atm_effect(0.0, 0.0, 0.0)
        self.assertIsInstance(effect, tuple)
        self.assertEqual(len(effect), 5)
        for value in effect:
            self.assertIsInstance(value, float)

        self.assertIn("AtmosModel", repr(atmos_model))

    def test_atmos_model_factory_missing_atmospheric_model_raises(self):
        """AtmosModelFactory.create should raise IException when AtmosphericModel is absent."""
        pvl = self._make_photo_pvl("Lambert")
        photo_model = ip.PhotoModelFactory.create(pvl)

        with self.assertRaises(ip.IException):
            ip.AtmosModelFactory.create(pvl, photo_model)


if __name__ == "__main__":
    unittest.main()
