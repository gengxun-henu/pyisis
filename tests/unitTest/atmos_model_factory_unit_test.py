"""
Unit tests for ISIS PhotoModelFactory, AtmosModelFactory, NormModelFactory, and AlbedoAtm bindings

Author: Geng Xun
Created: 2026-04-04
Last Modified: 2026-04-06
Updated: 2026-04-06  Geng Xun added focused factory-chain and AlbedoAtm regression coverage for photometric model bindings.
"""
import unittest

from _unit_test_support import ip


ALBEDO_ATM_WITH_DEM_CASES = [
    (0.0800618902, -0.038529257238382665),
    (0.0797334611, -0.03922255404309969),
    (0.0794225037, -0.03987896899482936),
]


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

    @classmethod
    def _make_photo_atmos_norm_pvl(cls, photo_name="Lambert", atmos_name="Anisotropic1", norm_name="AlbedoAtm"):
        """Create PVL with PhotoModel, AtmosModel, and NormModel configuration."""
        pvl = cls._make_photo_atmos_pvl(photo_name, atmos_name)

        # Add specific atmospheric parameters for Anisotropic1
        if atmos_name == "Anisotropic1":
            atmos_obj = pvl.find_object("AtmosphericModel")
            atmos_algo = atmos_obj.find_group("Algorithm")
            atmos_algo.add_keyword(ip.PvlKeyword("Bha", "0.85"))
            atmos_algo.add_keyword(ip.PvlKeyword("Tau", "0.28"))
            atmos_algo.add_keyword(ip.PvlKeyword("Wha", "0.95"))
            atmos_algo.add_keyword(ip.PvlKeyword("Hga", "0.68"))
            atmos_algo.add_keyword(ip.PvlKeyword("Tauref", "0.0"))
            atmos_algo.add_keyword(ip.PvlKeyword("Hnorm", "0.003"))

        # Add normalization model
        norm = ip.PvlObject("NormalizationModel")
        norm_algo = ip.PvlGroup("Algorithm")
        norm_algo.add_keyword(ip.PvlKeyword("Name", norm_name))
        norm_algo.add_keyword(ip.PvlKeyword("Incref", "0.0"))
        norm_algo.add_keyword(ip.PvlKeyword("Thresh", "30.0"))
        norm.add_group(norm_algo)
        pvl.add_object(norm)

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


class NormModelFactoryUnitTest(unittest.TestCase):
    """Test suite for NormModelFactory and NormModel bindings. Added: 2026-04-06."""

    @staticmethod
    def _make_photo_atmos_norm_pvl():
        """Create minimal PVL for creating normalization models."""
        pvl = ip.Pvl()

        # PhotoModel
        photometric = ip.PvlObject("PhotometricModel")
        photo_algo = ip.PvlGroup("Algorithm")
        photo_algo.add_keyword(ip.PvlKeyword("Name", "Lambert"))
        photometric.add_group(photo_algo)
        pvl.add_object(photometric)

        # AtmosModel
        atmospheric = ip.PvlObject("AtmosphericModel")
        atmos_algo = ip.PvlGroup("Algorithm")
        atmos_algo.add_keyword(ip.PvlKeyword("Name", "Anisotropic1"))
        atmos_algo.add_keyword(ip.PvlKeyword("Bha", "0.85"))
        atmos_algo.add_keyword(ip.PvlKeyword("Tau", "0.28"))
        atmos_algo.add_keyword(ip.PvlKeyword("Wha", "0.95"))
        atmos_algo.add_keyword(ip.PvlKeyword("Hga", "0.68"))
        atmos_algo.add_keyword(ip.PvlKeyword("Tauref", "0.0"))
        atmos_algo.add_keyword(ip.PvlKeyword("Hnorm", "0.003"))
        atmospheric.add_group(atmos_algo)
        pvl.add_object(atmospheric)

        # NormModel
        norm = ip.PvlObject("NormalizationModel")
        norm_algo = ip.PvlGroup("Algorithm")
        norm_algo.add_keyword(ip.PvlKeyword("Name", "AlbedoAtm"))
        norm_algo.add_keyword(ip.PvlKeyword("Incref", "0.0"))
        norm_algo.add_keyword(ip.PvlKeyword("Thresh", "30.0"))
        norm.add_group(norm_algo)
        pvl.add_object(norm)

        return pvl

    def test_norm_model_factory_symbol_presence(self):
        """NormModelFactory should be exported with a callable create method."""
        self.assertTrue(hasattr(ip, "NormModelFactory"))
        self.assertTrue(hasattr(ip.NormModelFactory, "create"))
        self.assertTrue(callable(ip.NormModelFactory.create))

    def test_norm_model_factory_create_albedo_atm(self):
        """NormModelFactory.create should return a working AlbedoAtm normalization model."""
        pvl = self._make_photo_atmos_norm_pvl()
        photo_model = ip.PhotoModelFactory.create(pvl)
        atmos_model = ip.AtmosModelFactory.create(pvl, photo_model)
        norm_model = ip.NormModelFactory.create(pvl, photo_model, atmos_model)

        self.assertIsInstance(norm_model, ip.NormModel)
        self.assertIsInstance(norm_model, ip.AlbedoAtm)
        self.assertEqual(norm_model.algorithm_name(), "Unknown")
        self.assertIn("AlbedoAtm", repr(norm_model))
        self.assertIn("Unknown", repr(norm_model))

    def test_norm_model_calc_nrm_albedo_without_dem(self):
        """NormModel.calc_nrm_albedo should compute normalization without DEM parameters."""
        pvl = self._make_photo_atmos_norm_pvl()
        photo_model = ip.PhotoModelFactory.create(pvl)
        atmos_model = ip.AtmosModelFactory.create(pvl, photo_model)
        norm_model = ip.NormModelFactory.create(pvl, photo_model, atmos_model)

        # Test values from upstream unitTest.cpp
        phase = 86.7207248
        incidence = 51.7031305
        emission = 38.9372914
        dn = 0.0800618902

        result = norm_model.calc_nrm_albedo(phase, incidence, emission, dn)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)

        albedo, mult, base = result
        self.assertIsInstance(albedo, float)
        self.assertIsInstance(mult, float)
        self.assertIsInstance(base, float)

        # The 4-argument path currently follows the upstream default behavior
        # of leaving the result tuple at zeros for this configuration.
        self.assertAlmostEqual(albedo, 0.0, places=12)
        self.assertAlmostEqual(mult, 0.0, places=12)
        self.assertAlmostEqual(base, 0.0, places=12)

    def test_norm_model_calc_nrm_albedo_with_dem(self):
        """NormModel.calc_nrm_albedo should compute normalization with DEM parameters."""
        pvl = self._make_photo_atmos_norm_pvl()
        photo_model = ip.PhotoModelFactory.create(pvl)
        atmos_model = ip.AtmosModelFactory.create(pvl, photo_model)
        norm_model = ip.NormModelFactory.create(pvl, photo_model, atmos_model)

        # Test values from upstream unitTest.cpp
        phase = 86.7207248
        incidence = 51.7031305
        emission = 38.9372914
        dem_incidence = 51.7031305
        dem_emission = 38.9372914
        dn = 0.0800618902

        result = norm_model.calc_nrm_albedo(phase, incidence, emission,
                                            dem_incidence, dem_emission, dn)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)

        albedo, mult, base = result
        self.assertIsInstance(albedo, float)
        self.assertIsInstance(mult, float)
        self.assertIsInstance(base, float)

        self.assertAlmostEqual(albedo, -0.038529257238382665, places=12)
        self.assertAlmostEqual(mult, 0.0, places=12)
        self.assertAlmostEqual(base, 0.0, places=12)


class AlbedoAtmUnitTest(unittest.TestCase):
    """Test suite for AlbedoAtm normalization model binding. Added: 2026-04-06."""

    @staticmethod
    def _make_albedo_atm_pvl():
        """Create PVL configuration for AlbedoAtm model."""
        pvl = ip.Pvl()

        # PhotoModel
        photometric = ip.PvlObject("PhotometricModel")
        photo_algo = ip.PvlGroup("Algorithm")
        photo_algo.add_keyword(ip.PvlKeyword("Name", "Lambert"))
        photometric.add_group(photo_algo)
        pvl.add_object(photometric)

        # AtmosModel
        atmospheric = ip.PvlObject("AtmosphericModel")
        atmos_algo = ip.PvlGroup("Algorithm")
        atmos_algo.add_keyword(ip.PvlKeyword("Name", "Anisotropic1"))
        atmos_algo.add_keyword(ip.PvlKeyword("Bha", "0.85"))
        atmos_algo.add_keyword(ip.PvlKeyword("Tau", "0.28"))
        atmos_algo.add_keyword(ip.PvlKeyword("Wha", "0.95"))
        atmos_algo.add_keyword(ip.PvlKeyword("Hga", "0.68"))
        atmos_algo.add_keyword(ip.PvlKeyword("Tauref", "0.0"))
        atmos_algo.add_keyword(ip.PvlKeyword("Hnorm", "0.003"))
        atmospheric.add_group(atmos_algo)
        pvl.add_object(atmospheric)

        # NormModel
        norm = ip.PvlObject("NormalizationModel")
        norm_algo = ip.PvlGroup("Algorithm")
        norm_algo.add_keyword(ip.PvlKeyword("Name", "AlbedoAtm"))
        norm_algo.add_keyword(ip.PvlKeyword("Incref", "0.0"))
        norm_algo.add_keyword(ip.PvlKeyword("Thresh", "30.0"))
        norm.add_group(norm_algo)
        pvl.add_object(norm)

        return pvl

    def test_albedo_atm_symbol_presence(self):
        """AlbedoAtm should be exported as a class."""
        self.assertTrue(hasattr(ip, "AlbedoAtm"))
        self.assertTrue(callable(ip.AlbedoAtm))

    def test_albedo_atm_constructor(self):
        """AlbedoAtm constructor should create a working instance."""
        pvl = self._make_albedo_atm_pvl()
        photo_model = ip.PhotoModelFactory.create(pvl)
        atmos_model = ip.AtmosModelFactory.create(pvl, photo_model)

        albedo_atm = ip.AlbedoAtm(pvl, photo_model, atmos_model)

        self.assertIsInstance(albedo_atm, ip.AlbedoAtm)
        self.assertIsInstance(albedo_atm, ip.NormModel)
        self.assertEqual(albedo_atm.algorithm_name(), "Unknown")
        self.assertIn("AlbedoAtm", repr(albedo_atm))
        self.assertIn("Unknown", repr(albedo_atm))

    def test_albedo_atm_via_factory(self):
        """AlbedoAtm can be created via NormModelFactory."""
        pvl = self._make_albedo_atm_pvl()
        photo_model = ip.PhotoModelFactory.create(pvl)
        atmos_model = ip.AtmosModelFactory.create(pvl, photo_model)
        norm_model = ip.NormModelFactory.create(pvl, photo_model, atmos_model)

        self.assertIsInstance(norm_model, ip.NormModel)
        self.assertIsInstance(norm_model, ip.AlbedoAtm)
        self.assertEqual(norm_model.algorithm_name(), "Unknown")

    def test_albedo_atm_normalization_calculation(self):
        """AlbedoAtm should compute albedo normalization matching upstream behavior."""
        pvl = self._make_albedo_atm_pvl()
        photo_model = ip.PhotoModelFactory.create(pvl)
        atmos_model = ip.AtmosModelFactory.create(pvl, photo_model)
        albedo_atm = ip.AlbedoAtm(pvl, photo_model, atmos_model)

        phase = 86.7207248
        incidence = 51.7031305
        emission = 38.9372914
        results = []

        for dn, expected_albedo in ALBEDO_ATM_WITH_DEM_CASES:
            albedo, mult, base = albedo_atm.calc_nrm_albedo(
                phase, incidence, emission, incidence, emission, dn
            )
            self.assertIsInstance(albedo, float)
            self.assertAlmostEqual(albedo, expected_albedo, places=12)
            self.assertAlmostEqual(mult, 0.0, places=12)
            self.assertAlmostEqual(base, 0.0, places=12)
            results.append(albedo)

        # Different DN inputs should still produce distinct normalization outputs.
        self.assertEqual(len(set(results)), len(results))

    def test_albedo_atm_inherited_methods(self):
        """AlbedoAtm should inherit NormModel methods."""
        pvl = self._make_albedo_atm_pvl()
        photo_model = ip.PhotoModelFactory.create(pvl)
        atmos_model = ip.AtmosModelFactory.create(pvl, photo_model)
        albedo_atm = ip.AlbedoAtm(pvl, photo_model, atmos_model)

        # Test inherited algorithm_name
        self.assertEqual(albedo_atm.algorithm_name(), "Unknown")

        # Test inherited calc_nrm_albedo
        self.assertTrue(hasattr(albedo_atm, "calc_nrm_albedo"))
        self.assertTrue(callable(albedo_atm.calc_nrm_albedo))

        # Test inherited set_norm_wavelength
        self.assertTrue(hasattr(albedo_atm, "set_norm_wavelength"))
        self.assertTrue(callable(albedo_atm.set_norm_wavelength))


if __name__ == "__main__":
    unittest.main()
