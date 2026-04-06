"""
Unit tests for ISIS Anisotropic1 atmospheric model binding

Author: Geng Xun
Created: 2026-04-06
Last Modified: 2026-04-06
"""
import unittest

from _unit_test_support import ip


ANISOTROPIC1_PVL = """
Object = PhotometricModel
  Group = Algorithm
    Name = Lambert
  End_Group
End_Object

Object = AtmosphericModel
  Group = Algorithm
    Name  = Anisotropic1
    Tau   = 0.28
    Bha   = 0.85
    Hnorm = 0.003
  End_Group
End_Object
End
"""


def make_anisotropic1_pvl():
    pvl = ip.Pvl()
    pvl.from_string(ANISOTROPIC1_PVL)
    return pvl


class Anisotropic1UnitTest(unittest.TestCase):
    """Focused tests for the Anisotropic1 atmospheric model binding."""

    def _create_models(self):
        pvl = make_anisotropic1_pvl()
        photo_model = ip.PhotoModelFactory.create(pvl)
        self.assertIsNotNone(photo_model)

        return ip.Anisotropic1(pvl, photo_model)

    def test_algorithm_name_and_repr(self):
        atmos_model = self._create_models()
        self.assertEqual(atmos_model.algorithm_name(), "Anisotropic1")
        self.assertIn("Anisotropic1", repr(atmos_model))

    def test_calc_atm_effect_matches_truth_values(self):
        atmos_model = self._create_models()

        atmos_model.set_standard_conditions(True)
        pstd, trans, trans0, sbar, transs = atmos_model.calc_atm_effect(0.0, 0.0, 0.0)
        self.assertAlmostEqual(pstd, 0.0, places=7)
        self.assertAlmostEqual(trans, 1.0, places=7)
        self.assertAlmostEqual(trans0, 1.0, places=7)
        self.assertAlmostEqual(sbar, 0.0, places=7)
        self.assertAlmostEqual(transs, trans0, places=7)

        atmos_model.set_standard_conditions(False)
        pstd, trans, trans0, sbar, transs = atmos_model.calc_atm_effect(
            86.7226722, 51.7002388, 38.9414439
        )
        self.assertAlmostEqual(pstd, 0.0983183, places=6)
        self.assertAlmostEqual(trans, 0.764393, places=6)
        self.assertAlmostEqual(trans0, 0.444706, places=6)
        self.assertAlmostEqual(sbar, 0.130632, places=6)
        self.assertAlmostEqual(transs, trans0, places=6)

        pstd, trans, trans0, sbar, transs = atmos_model.calc_atm_effect(180.0, 90.0, 90.0)
        self.assertAlmostEqual(pstd, 0.0266486, places=6)
        self.assertAlmostEqual(trans, 0.159184, places=6)
        self.assertAlmostEqual(trans0, 5.19719e-07, places=9)
        self.assertAlmostEqual(sbar, 0.130632, places=6)
        self.assertAlmostEqual(transs, trans0, places=9)

    def test_factory_returns_anisotropic1_instance(self):
        pvl = make_anisotropic1_pvl()
        photo_model = ip.PhotoModelFactory.create(pvl)
        atmos_model = ip.AtmosModelFactory.create(pvl, photo_model)

        self.assertIsInstance(atmos_model, ip.Anisotropic1)
        self.assertEqual(atmos_model.algorithm_name(), "Anisotropic1")


if __name__ == "__main__":
    unittest.main()
