"""
Unit tests for ISIS photometry, atmospheric model, and normalization bindings

Author: Geng Xun
Created: 2026-04-04
Last Modified: 2026-04-09
Updated: 2026-04-09  Geng Xun added Hapke, ShadeAtm, TopoAtm, and expanded photometry base-class regression coverage for the rollout queue.
Updated: 2026-04-09  Geng Xun added NumericalAtmosApprox integration regression coverage for the third rollout batch.
"""
import unittest

from _unit_test_support import ip


ALBEDO_ATM_WITH_DEM_CASES = [
    (0.0800618902, -0.038529257238382665),
    (0.0797334611, -0.03922255404309969),
    (0.0794225037, -0.03987896899482936),
]


ATMOS_VARIANT_EXPECTATIONS = {
    "Anisotropic2": {
        "extra": {"Tau": "0.28"},
        "std": (0.0, 1.0, 1.0, 0.0, 1.0),
        "mid": (
            0.10247998742124259,
            0.7316630890458473,
            0.44470584594364543,
            0.16739448673717183,
            0.44470584594364543,
        ),
        "edge": (
            0.03282463848006161,
            0.14596477902101984,
            5.197187091767894e-07,
            0.16739448673717183,
            5.197187091767894e-07,
        ),
    },
    "HapkeAtm1": {
        "extra": {},
        "std": (0.0, 1.0, 1.0, 0.0, 1.0),
        "mid": (
            0.03678010353918514,
            0.8769403261151311,
            0.591403868693679,
            0.07981770238433639,
            0.513030934649242,
        ),
        "edge": (
            1.9597726032022253,
            0.10002284946669833,
            5.19718709176802e-07,
            0.07981770238433639,
            -4.7130388426890984e-05,
        ),
    },
    "HapkeAtm2": {
        "extra": {},
        "std": (0.0, 1.0, 1.0, 0.0, 1.0),
        "mid": (
            0.04445369548395528,
            0.8218323637728189,
            0.591403868693679,
            0.1260118129075133,
            0.513030934649242,
        ),
        "edge": (
            1.9682880456358216,
            0.08669757769775736,
            5.197187091768075e-07,
            0.1260118129075133,
            -4.713038842689122e-05,
        ),
    },
    "Isotropic1": {
        "extra": {},
        "std": (0.0, 1.0, 1.0, 0.0, 1.0),
        "mid": (
            0.07884891679559385,
            0.7033731754735993,
            0.44470584594364543,
            0.16508369791039956,
            0.5090978617964091,
        ),
        "edge": (
            0.13028136652354422,
            0.14619961412984,
            5.197187091767949e-07,
            0.16508369791039956,
            0.0001380846346470825,
        ),
    },
    "Isotropic2": {
        "extra": {},
        "std": (0.0, 1.0, 1.0, 0.0, 1.0),
        "mid": (
            0.08652250874036398,
            0.6541117929435937,
            0.44470584594364543,
            0.21127780843357646,
            0.49879601698771636,
        ),
        "edge": (
            0.13879680895714008,
            0.12998996637091684,
            5.197187091767949e-07,
            0.21127780843357646,
            0.00013021967769109182,
        ),
    },
}


HAPKE_EXPECTATIONS = {
    "HapkeHen": {
        "photo_name": "HapkeHen",
        "extra": {},
        "cases": (
            ((0.0, 0.0, 0.0), 0.09650974233026809),
            ((60.0, 45.0, 30.0), 0.08328830919316457),
            ((180.0, 90.0, 90.0), 0.0),
        ),
    },
    "HapkeHenConfigured": {
        "photo_name": "HapkeHen",
        "extra": {
            "Wh": "0.52",
            "B0": "1.0",
            "Hh": "1.0",
            "Theta": "30.0",
            "Hg1": "0.213",
            "Hg2": "1.0",
            "ZeroB0St": "TRUE",
        },
        "cases": (
            ((0.0, 0.0, 0.0), 0.28604794646042775),
            ((60.0, 45.0, 30.0), 0.1341996835824601),
            ((180.0, 90.0, 90.0), 0.0),
        ),
    },
    "HapkeLeg": {
        "photo_name": "HapkeLeg",
        "extra": {
            "Wh": "0.52",
            "B0": "1.0",
            "Hh": "1.0",
            "Bh": "0.0",
            "Ch": "0.0",
            "Theta": "30.0",
            "ZeroB0Standard": "FALSE",
        },
        "cases": (
            ((0.0, 0.0, 0.0), 0.16145012190027058),
            ((60.0, 45.0, 30.0), 0.11152494713005053),
            ((180.0, 90.0, 90.0), 0.0),
        ),
    },
}


NORM_VARIANT_EXPECTATIONS = {
    "ShadeAtm": {
        "extra": {"Albedo": "0.0690507"},
        "cases": (
            ((86.7226722, 51.7002388, 38.9414439, 51.7002388, 38.9414439, 0.0800618902),
             (0.13132892899196003, 0.0, 0.0)),
            ((86.7207248, 51.7031305, 38.9372914, 51.7031305, 38.9372914, 0.0797334611),
             (0.1313224639422052, 0.0, 0.0)),
            ((86.7187773, 51.7060221, 38.9331391, 51.7060221, 38.9331391, 0.0794225037),
             (0.13131599948310124, 0.0, 0.0)),
        ),
    },
    "TopoAtm": {
        "extra": {"Albedo": "0.0690507", "Incref": "30.0"},
        "cases": (
            ((86.7226722, 51.7002388, 38.9414439, 51.7002388, 38.9414439, 0.0800618902),
             (0.015895813414930668, 0.0, 0.0)),
            ((86.7207248, 51.7031305, 38.9372914, 51.7031305, 38.9372914, 0.0797334611),
             (0.015884491176448433, 0.0, 0.0)),
            ((86.7187773, 51.7060221, 38.9331391, 51.7060221, 38.9331391, 0.0794225037),
             (0.01587400500180055, 0.0, 0.0)),
        ),
    },
}


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
    def _make_photo_atmos_pvl(cls, photo_name="Lambert", atmos_name="Isotropic1", extra_atmos_keywords=None):
        pvl = cls._make_photo_pvl(photo_name)
        atmospheric = ip.PvlObject("AtmosphericModel")
        algorithm = ip.PvlGroup("Algorithm")
        algorithm.add_keyword(ip.PvlKeyword("Name", atmos_name))
        for key, value in (extra_atmos_keywords or {}).items():
            algorithm.add_keyword(ip.PvlKeyword(key, value))
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

    def test_photo_model_extended_base_api(self):
        """PhotoModel base helpers should expose their configured parameters."""
        pvl = self._make_photo_pvl("Lambert")
        photo_model = ip.PhotoModelFactory.create(pvl)

        photo_model.set_photo_l(0.25)
        photo_model.set_photo_k(0.75)
        photo_model.set_photo_hg1(-0.2)
        photo_model.set_photo_hg2(0.4)
        photo_model.set_photo_bh(0.1)
        photo_model.set_photo_ch(0.2)
        photo_model.set_photo_wh(0.8)
        photo_model.set_photo_hh(0.3)
        photo_model.set_photo_b0(0.6)
        photo_model.set_photo_theta(12.0)
        photo_model.set_photo0_b0_standard("TRUE")

        self.assertAlmostEqual(photo_model.photo_l(), 0.25, places=12)
        self.assertAlmostEqual(photo_model.photo_k(), 0.75, places=12)
        self.assertAlmostEqual(photo_model.photo_hg1(), -0.2, places=12)
        self.assertAlmostEqual(photo_model.photo_hg2(), 0.4, places=12)
        self.assertAlmostEqual(photo_model.photo_bh(), 0.1, places=12)
        self.assertAlmostEqual(photo_model.photo_ch(), 0.2, places=12)
        self.assertAlmostEqual(photo_model.photo_wh(), 0.8, places=12)
        self.assertAlmostEqual(photo_model.photo_hh(), 0.3, places=12)
        self.assertAlmostEqual(photo_model.photo_b0(), 0.6, places=12)
        self.assertAlmostEqual(photo_model.photo_theta(), 12.0, places=12)
        self.assertEqual(photo_model.photo0_b0_standard(), "TRUE")
        self.assertEqual(photo_model.photo_phase_list(), [])
        self.assertEqual(photo_model.photo_k_list(), [])
        self.assertEqual(photo_model.photo_l_list(), [])
        self.assertEqual(photo_model.photo_phase_curve_list(), [])
        self.assertAlmostEqual(photo_model.hfunc(0.4, 0.8), (1.0 + 2.0 * 0.4) / (1.0 + 2.0 * 0.4 * 0.8), places=12)
        self.assertAlmostEqual(ip.PhotoModel.pht_acos(0.999999939), 0.00034928498585345947, places=12)

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
        self.assertIsInstance(atmos_model, ip.Isotropic1)
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

        self.assertIn("Isotropic1", repr(atmos_model))

    def test_atmos_model_factory_missing_atmospheric_model_raises(self):
        """AtmosModelFactory.create should raise IException when AtmosphericModel is absent."""
        pvl = self._make_photo_pvl("Lambert")
        photo_model = ip.PhotoModelFactory.create(pvl)

        with self.assertRaises(ip.IException):
            ip.AtmosModelFactory.create(pvl, photo_model)


class ConcreteAtmosModelBindingUnitTest(unittest.TestCase):
    """Regression coverage for concrete atmospheric model bindings. Added: 2026-04-09."""

    @staticmethod
    def _make_variant_pvl(atmos_name):
        config = ATMOS_VARIANT_EXPECTATIONS[atmos_name]
        return AtmosModelFactoryUnitTest._make_photo_atmos_pvl(
            photo_name="Lambert",
            atmos_name=atmos_name,
            extra_atmos_keywords=config["extra"],
        )

    def _assert_effect_tuple(self, actual, expected):
        self.assertIsInstance(actual, tuple)
        self.assertEqual(len(actual), 5)
        for actual_value, expected_value in zip(actual, expected):
            self.assertAlmostEqual(actual_value, expected_value, places=8)

    def test_direct_constructors_and_repr(self):
        for atmos_name in ATMOS_VARIANT_EXPECTATIONS:
            with self.subTest(atmos_name=atmos_name):
                pvl = self._make_variant_pvl(atmos_name)
                photo_model = ip.PhotoModelFactory.create(pvl)
                atmos_class = getattr(ip, atmos_name)
                atmos_model = atmos_class(pvl, photo_model)

                self.assertIsInstance(atmos_model, ip.AtmosModel)
                self.assertEqual(atmos_model.algorithm_name(), "Unknown")
                self.assertIn(atmos_name, repr(atmos_model))
                self.assertIn("Unknown", repr(atmos_model))

    def test_factory_returns_concrete_variants(self):
        for atmos_name in ATMOS_VARIANT_EXPECTATIONS:
            with self.subTest(atmos_name=atmos_name):
                pvl = self._make_variant_pvl(atmos_name)
                photo_model = ip.PhotoModelFactory.create(pvl)
                atmos_model = ip.AtmosModelFactory.create(pvl, photo_model)

                self.assertIsInstance(atmos_model, getattr(ip, atmos_name))
                self.assertEqual(atmos_model.algorithm_name(), "Unknown")

    def test_calc_atm_effect_matches_upstream_truth(self):
        for atmos_name, config in ATMOS_VARIANT_EXPECTATIONS.items():
            with self.subTest(atmos_name=atmos_name):
                pvl = self._make_variant_pvl(atmos_name)
                photo_model = ip.PhotoModelFactory.create(pvl)
                atmos_model = getattr(ip, atmos_name)(pvl, photo_model)

                atmos_model.set_standard_conditions(True)
                self._assert_effect_tuple(
                    atmos_model.calc_atm_effect(0.0, 0.0, 0.0),
                    config["std"],
                )

                atmos_model.set_standard_conditions(False)
                self._assert_effect_tuple(
                    atmos_model.calc_atm_effect(86.7226722, 51.7002388, 38.9414439),
                    config["mid"],
                )
                self._assert_effect_tuple(
                    atmos_model.calc_atm_effect(180.0, 90.0, 90.0),
                    config["edge"],
                )


class HapkeBindingUnitTest(unittest.TestCase):
    """Regression coverage for Hapke concrete photometric bindings. Added: 2026-04-09."""

    @staticmethod
    def _make_hapke_pvl(case_name):
        config = HAPKE_EXPECTATIONS[case_name]
        pvl = AtmosModelFactoryUnitTest._make_photo_pvl(config["photo_name"])
        algorithm = pvl.find_object("PhotometricModel").find_group("Algorithm")
        for key, value in config["extra"].items():
            algorithm.add_keyword(ip.PvlKeyword(key, value))
        return pvl

    def test_hapke_direct_constructor_and_factory_dispatch(self):
        for case_name in HAPKE_EXPECTATIONS:
            with self.subTest(case_name=case_name):
                pvl = self._make_hapke_pvl(case_name)
                direct_model = ip.Hapke(pvl)
                factory_model = ip.PhotoModelFactory.create(pvl)

                self.assertIsInstance(direct_model, ip.Hapke)
                self.assertIsInstance(factory_model, ip.Hapke)
                self.assertEqual(direct_model.algorithm_name(), factory_model.algorithm_name())
                self.assertIn("Hapke", repr(direct_model))

    def test_hapke_regression_values(self):
        for case_name, config in HAPKE_EXPECTATIONS.items():
            with self.subTest(case_name=case_name):
                hapke_model = ip.Hapke(self._make_hapke_pvl(case_name))
                for args, expected in config["cases"]:
                    self.assertAlmostEqual(hapke_model.calc_surf_albedo(*args), expected, places=12)
                    self.assertAlmostEqual(hapke_model.photo_model_algorithm(*args), expected, places=12)

    def test_hapke_specific_setters(self):
        hapke_model = ip.Hapke(self._make_hapke_pvl("HapkeHen"))
        hapke_model.set_photo_hg1(0.2)
        hapke_model.set_photo_hg2(0.7)
        hapke_model.set_photo_bh(0.1)
        hapke_model.set_photo_ch(-0.1)
        hapke_model.set_photo_wh(0.52)
        hapke_model.set_photo_hh(1.0)
        hapke_model.set_photo_b0(0.8)
        hapke_model.set_photo_theta(30.0)
        hapke_model.set_old_theta(29.0)
        hapke_model.set_photo0_b0_standard("FALSE")

        self.assertAlmostEqual(hapke_model.photo_hg1(), 0.2, places=12)
        self.assertAlmostEqual(hapke_model.photo_hg2(), 0.7, places=12)
        self.assertAlmostEqual(hapke_model.photo_bh(), 0.1, places=12)
        self.assertAlmostEqual(hapke_model.photo_ch(), -0.1, places=12)
        self.assertAlmostEqual(hapke_model.photo_wh(), 0.52, places=12)
        self.assertAlmostEqual(hapke_model.photo_hh(), 1.0, places=12)
        self.assertAlmostEqual(hapke_model.photo_b0(), 0.8, places=12)
        self.assertAlmostEqual(hapke_model.photo_theta(), 30.0, places=12)
        self.assertEqual(hapke_model.photo0_b0_standard(), "FALSE")


class ExpandedAtmosModelBindingUnitTest(unittest.TestCase):
    """Regression coverage for expanded AtmosModel base APIs. Added: 2026-04-09."""

    @staticmethod
    def _make_anisotropic1_pvl():
        return AtmosModelFactoryUnitTest._make_photo_atmos_pvl(
            photo_name="Lambert",
            atmos_name="Anisotropic1",
            extra_atmos_keywords={"Bha": "0.85"},
        )

    def test_atmos_model_static_helpers(self):
        self.assertAlmostEqual(ip.AtmosModel.en(1, 0.28), 0.9573083004722877, places=12)
        self.assertAlmostEqual(ip.AtmosModel.en(1, 0.733615937), 0.3508604962328475, places=12)
        self.assertAlmostEqual(ip.AtmosModel.ei(0.234), -0.6267852357739978, places=12)
        self.assertAlmostEqual(ip.AtmosModel.ei(1.5), 3.3012854415604567, places=12)
        self.assertAlmostEqual(ip.AtmosModel.g11_prime(0.28), 0.7913402927011793, places=12)
        self.assertAlmostEqual(ip.AtmosModel.g11_prime(1.5836), 0.21716703935808004, places=12)

    def test_atmos_model_extended_getters_setters_and_tables(self):
        pvl = self._make_anisotropic1_pvl()
        photo_model = ip.PhotoModelFactory.create(pvl)
        atmos_model = ip.AtmosModelFactory.create(pvl, photo_model)

        atmos_model.set_atmos_tau(0.31)
        atmos_model.set_atmos_wha(0.98)
        atmos_model.set_atmos_hga(0.55)
        atmos_model.set_atmos_bha(0.6)
        atmos_model.set_atmos_tauref(0.11)
        atmos_model.set_atmos_hnorm(0.004)
        atmos_model.set_atmos_inc(30.0)
        atmos_model.set_atmos_phi(45.0)
        atmos_model.set_atmos_nulneg("YES")
        atmos_model.set_atmos_iord("YES")
        atmos_model.set_atmos_est_tau("NO")
        atmos_model.set_atmos_atm_switch(1)

        self.assertAlmostEqual(atmos_model.atmos_tau(), 0.31, places=12)
        self.assertAlmostEqual(atmos_model.atmos_wha(), 0.98, places=12)
        self.assertAlmostEqual(atmos_model.atmos_hga(), 0.55, places=12)
        self.assertAlmostEqual(atmos_model.atmos_bha(), 0.6, places=12)
        self.assertAlmostEqual(atmos_model.atmos_tauref(), 0.11, places=12)
        self.assertAlmostEqual(atmos_model.atmos_hnorm(), 0.004, places=12)
        self.assertTrue(atmos_model.atmos_nulneg())
        self.assertTrue(atmos_model.atmos_additive_offset())
        self.assertAlmostEqual(atmos_model.atmos_munot(), 0.8660254037844387, places=12)

        atmos_model.generate_ah_table()
        self.assertEqual(len(atmos_model.atmos_inc_table()), atmos_model.atmos_ninc())
        self.assertEqual(len(atmos_model.atmos_ah_table()), atmos_model.atmos_ninc())
        self.assertGreaterEqual(atmos_model.atmos_ab(), 0.0)

        atmos_model.generate_hahg_tables()
        self.assertEqual(len(atmos_model.atmos_hahgt_table()), atmos_model.atmos_ninc())
        self.assertEqual(len(atmos_model.atmos_hahgt0_table()), atmos_model.atmos_ninc())
        self.assertAlmostEqual(atmos_model.atmos_hahgsb(), -0.07494197697057361, places=12)

        atmos_model.generate_hahg_tables_shadow()
        self.assertAlmostEqual(atmos_model.atmos_hahgsb(), -0.074853393005592, places=12)


class NumericalAtmosApproxUnitTest(unittest.TestCase):
    """Regression coverage for NumericalAtmosApprox integration helpers. Added: 2026-04-09."""

    @staticmethod
    def _make_anisotropic1_pvl():
        return AtmosModelFactoryUnitTest._make_photo_atmos_pvl(
            photo_name="Lambert",
            atmos_name="Anisotropic1",
            extra_atmos_keywords={
                "Bha": "0.85",
                "Tau": "0.28",
                "Wha": "0.95",
                "Hga": "0.68",
                "Tauref": "0.0",
                "Hnorm": "0.003",
            },
        )

    def _make_atmos_model(self):
        pvl = self._make_anisotropic1_pvl()
        photo_model = ip.PhotoModelFactory.create(pvl)
        atmos_model = ip.AtmosModelFactory.create(pvl, photo_model)
        return pvl, photo_model, atmos_model

    def test_symbol_enums_and_constructor(self):
        approx = ip.NumericalAtmosApprox()
        self.assertIn("NumericalAtmosApprox", repr(approx))

        spline = ip.NumericalAtmosApprox(ip.NumericalAtmosApprox.InterpType.PolynomialNeville)
        self.assertIsInstance(spline, ip.NumericalAtmosApprox)
        self.assertEqual(
            ip.NumericalAtmosApprox.IntegFunc.OuterFunction.name,
            "OuterFunction",
        )
        self.assertEqual(
            ip.NumericalAtmosApprox.IntegFunc.InnerFunction.name,
            "InnerFunction",
        )

    def test_inner_function_invalid_switch_raises(self):
        _, _, atmos_model = self._make_atmos_model()
        with self.assertRaises(ip.IException):
            atmos_model.set_atmos_atm_switch(99)

    def test_integration_helpers_match_upstream_regression_values(self):
        _, _, atmos_model = self._make_atmos_model()
        approx = ip.NumericalAtmosApprox(ip.NumericalAtmosApprox.InterpType.PolynomialNeville)

        atmos_model.set_atmos_atm_switch(1)
        atmos_model.set_atmos_inc(0.0)
        atmos_model.set_atmos_phi(0.0)
        atmos_model.set_atmos_hga(0.68)
        atmos_model.set_atmos_tau(0.28)

        self.assertAlmostEqual(
            ip.NumericalAtmosApprox.inr_func2_bint(atmos_model, 1.0e-6),
            -5.260328797107054e-07,
            places=12,
        )
        self.assertAlmostEqual(
            ip.NumericalAtmosApprox.outr_func2_bint(atmos_model, 0.0),
            0.1953435404362085,
            places=12,
        )
        self.assertAlmostEqual(
            approx.refine_extended_trap(
                atmos_model,
                ip.NumericalAtmosApprox.IntegFunc.OuterFunction,
                0.0,
                180.0,
                0.0,
                1,
            ),
            35.16183727851753,
            places=12,
        )
        self.assertAlmostEqual(
            approx.rombergs_method(
                atmos_model,
                ip.NumericalAtmosApprox.IntegFunc.OuterFunction,
                0.0,
                180.0,
            ),
            35.16183727851753,
            places=12,
        )

        atmos_model.set_atmos_atm_switch(2)
        atmos_model.set_atmos_inc(3.0)
        atmos_model.set_atmos_phi(78.75)
        atmos_model.set_atmos_hga(0.68)
        atmos_model.set_atmos_tau(0.28)

        self.assertAlmostEqual(
            ip.NumericalAtmosApprox.inr_func2_bint(atmos_model, 0.75000025),
            -0.17742641067474454,
            places=12,
        )
        self.assertAlmostEqual(
            ip.NumericalAtmosApprox.outr_func2_bint(atmos_model, 78.75),
            -0.1405840868479181,
            places=12,
        )

        running_sum = 0.0
        expected_refinements = (
            -25.255292326051478,
            -25.259588463295287,
            -25.259590275445944,
            -25.25959027544632,
            -25.25959027544632,
        )
        for iteration, expected in enumerate(expected_refinements, start=1):
            running_sum = approx.refine_extended_trap(
                atmos_model,
                ip.NumericalAtmosApprox.IntegFunc.OuterFunction,
                0.0,
                180.0,
                running_sum,
                iteration,
            )
            self.assertAlmostEqual(running_sum, expected, places=12)

        self.assertAlmostEqual(
            approx.rombergs_method(
                atmos_model,
                ip.NumericalAtmosApprox.IntegFunc.OuterFunction,
                0.0,
                180.0,
            ),
            -25.259590270353364,
            places=12,
        )


class ConcreteNormModelBindingUnitTest(unittest.TestCase):
    """Regression coverage for concrete normalization model bindings. Added: 2026-04-09."""

    @staticmethod
    def _make_norm_variant_pvl(norm_name):
        pvl = AtmosModelFactoryUnitTest._make_photo_atmos_pvl(
            photo_name="Lambert",
            atmos_name="Anisotropic1",
            extra_atmos_keywords={"Bha": "0.85"},
        )
        norm = ip.PvlObject("NormalizationModel")
        norm_algorithm = ip.PvlGroup("Algorithm")
        norm_algorithm.add_keyword(ip.PvlKeyword("Name", norm_name))
        for key, value in NORM_VARIANT_EXPECTATIONS[norm_name]["extra"].items():
            norm_algorithm.add_keyword(ip.PvlKeyword(key, value))
        norm.add_group(norm_algorithm)
        pvl.add_object(norm)
        return pvl

    def test_direct_constructors_and_factory_dispatch(self):
        for norm_name in NORM_VARIANT_EXPECTATIONS:
            with self.subTest(norm_name=norm_name):
                pvl = self._make_norm_variant_pvl(norm_name)
                photo_model = ip.PhotoModelFactory.create(pvl)
                atmos_model = ip.AtmosModelFactory.create(pvl, photo_model)
                norm_class = getattr(ip, norm_name)
                direct_model = norm_class(pvl, photo_model, atmos_model)
                factory_model = ip.NormModelFactory.create(pvl, photo_model, atmos_model)

                self.assertIsInstance(direct_model, ip.NormModel)
                self.assertIsInstance(factory_model, norm_class)
                self.assertIn(norm_name, repr(direct_model))

    def test_norm_regression_values(self):
        for norm_name, config in NORM_VARIANT_EXPECTATIONS.items():
            with self.subTest(norm_name=norm_name):
                pvl = self._make_norm_variant_pvl(norm_name)
                photo_model = ip.PhotoModelFactory.create(pvl)
                atmos_model = ip.AtmosModelFactory.create(pvl, photo_model)
                norm_model = getattr(ip, norm_name)(pvl, photo_model, atmos_model)

                for args, expected in config["cases"]:
                    result = norm_model.calc_nrm_albedo(*args)
                    self.assertIsInstance(result, tuple)
                    self.assertEqual(len(result), 3)
                    for actual_value, expected_value in zip(result, expected):
                        self.assertAlmostEqual(actual_value, expected_value, places=12)


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
