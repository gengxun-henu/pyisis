"""
Unit tests for MRO HiCal gain bindings.

Author: Geng Xun
Created: 2026-04-09
Last Modified: 2026-04-09
Updated: 2026-04-09  Geng Xun added focused coverage for GainNonLinearity, GainTemperature, and GainUnitConversion using minimal local HiCal configs.
"""

from pathlib import Path
import unittest

from _unit_test_support import ip, temporary_directory


class MroHiCalUnitTest(unittest.TestCase):
    """Focused regression coverage for lightweight MRO HiCal gain wrappers."""

    @staticmethod
    def _make_hical_label(
        samples=5,
        positive_temperature=25.0,
        negative_temperature=21.0,
        exposure_duration=97.5,
    ):
        label = ip.Pvl()
        label.from_string(
            f"""
Group = Dimensions
  Samples = {samples}
  Lines = 1
  Bands = 1
EndGroup
Group = Instrument
  CpmmNumber = 0
  ChannelNumber = 1
  Tdi = 64
  Summing = 1
  FpaPositiveYTemperature = {positive_temperature}
  FpaNegativeYTemperature = {negative_temperature}
  ScanExposureDuration = {exposure_duration}
EndGroup
Group = Archive
  ProductId = TEST_PRODUCT
EndGroup
End
"""
        )
        return label

    @staticmethod
    def _write_minimal_hical_fixture(temp_dir: Path):
        non_linearity_csv = temp_dir / "gain_non_linearity.csv"
        non_linearity_csv.write_text("1.25\n", encoding="utf-8")

        fpa_gain_csv = temp_dir / "fpa_gain.csv"
        fpa_gain_csv.write_text("0.05\n", encoding="utf-8")

        conf_path = temp_dir / "minimal_hical.conf"
        conf_path.write_text(
            f"""
Object = Hical
  Name = MinimalHiCal
  LabelGroups = ( "Dimensions", "Instrument", "Archive" )
  FpaReferenceTemperature = 21.0

  Group = Profile
    Name = GainNonLinearity
    Module = GainNonLinearity
    NonLinearityGain = "{non_linearity_csv.as_posix()}"
  End_Group

  Group = Profile
    Name = GainTemperature
    Module = GainTemperature
    FpaGain = "{fpa_gain_csv.as_posix()}"
  End_Group

  Group = Profile
    Name = GainUnitConversion
    Module = GainUnitConversion
    GainUnitConversionBinFactor = 1.0
  End_Group
End_Object
End
""",
            encoding="utf-8",
        )
        return conf_path, non_linearity_csv, fpa_gain_csv

    def test_gain_non_linearity_python_wrapper_loads_factor_and_history(self):
        with temporary_directory() as temp_dir:
            conf_path, non_linearity_csv, _ = self._write_minimal_hical_fixture(temp_dir)
            label = self._make_hical_label()

            module = ip.GainNonLinearity(label, str(conf_path))

            self.assertEqual(module.name(), "GainNonLinearity")
            self.assertEqual(module.size(), 1)
            self.assertEqual(len(module), 1)
            self.assertAlmostEqual(module[0], 1.25)
            self.assertEqual(module.data(), [1.25])
            self.assertTrue(module.csv_file().endswith(non_linearity_csv.name))
            self.assertIn("GainNonLinearity", repr(module))
            self.assertTrue(any("Profile[GainNonLinearity]" in event for event in module.history()))
            self.assertTrue(any("NonLinearityGainFactor[1.25" in event for event in module.history()))

    def test_gain_temperature_python_wrapper_uses_minimal_label_and_config(self):
        with temporary_directory() as temp_dir:
            conf_path, _, fpa_gain_csv = self._write_minimal_hical_fixture(temp_dir)
            label = self._make_hical_label(samples=4, positive_temperature=25.0, negative_temperature=21.0)

            module = ip.GainTemperature(label, str(conf_path))

            self.assertEqual(module.name(), "GainTemperature")
            self.assertEqual(module.size(), 4)
            self.assertEqual(len(module), 4)
            self.assertEqual(module.csv_file(), str(fpa_gain_csv))
            self.assertTrue(all(abs(value - 0.9) < 1e-12 for value in module.data()))
            self.assertAlmostEqual(module.at(-1), 0.9)
            self.assertTrue(any("FpaTemperatureFactor[0.05" in event for event in module.history()))
            self.assertTrue(any("Correction[0.9" in event for event in module.history()))

    def test_gain_unit_conversion_supports_dn_and_dn_per_microsecond(self):
        with temporary_directory() as temp_dir:
            conf_path, _, _ = self._write_minimal_hical_fixture(temp_dir)
            label = self._make_hical_label(exposure_duration=97.5)

            dn_module = ip.GainUnitConversion(label, str(conf_path))
            dn_per_us_module = ip.GainUnitConversion(label, str(conf_path), "DN/US")

            self.assertEqual(dn_module.data(), [1.0])
            self.assertEqual(dn_module.csv_file(), "")
            self.assertTrue(any("Units[DN]" in event for event in dn_module.history()))

            self.assertEqual(dn_per_us_module.size(), 1)
            self.assertAlmostEqual(dn_per_us_module[0], 97.5)
            self.assertTrue(any("DN/uS_Factor[97.5" in event for event in dn_per_us_module.history()))
            self.assertTrue(any("Units[DNs/microsecond]" in event for event in dn_per_us_module.history()))

    def test_gain_unit_conversion_requires_cube_for_iof_mode(self):
        with temporary_directory() as temp_dir:
            conf_path, _, _ = self._write_minimal_hical_fixture(temp_dir)
            label = self._make_hical_label()

            with self.assertRaises(ValueError):
                ip.GainUnitConversion(label, str(conf_path), "IOF")

    def test_gain_wrappers_keep_default_constructors_available(self):
        non_linearity = ip.GainNonLinearity()
        temperature = ip.GainTemperature()
        unit_conversion = ip.GainUnitConversion()

        self.assertEqual(non_linearity.name(), "GainNonLinearity")
        self.assertEqual(temperature.name(), "GainTemperature")
        self.assertEqual(unit_conversion.name(), "GainUnitConversion")
        self.assertEqual(non_linearity.data(), [])
        self.assertEqual(temperature.data(), [])
        self.assertEqual(unit_conversion.data(), [])


if __name__ == "__main__":
    unittest.main()
