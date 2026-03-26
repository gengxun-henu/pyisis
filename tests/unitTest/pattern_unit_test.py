"""
Unit tests for ISIS pattern matching classes: Chip and AutoReg
"""
import unittest

from _unit_test_support import ip, workspace_test_data_path


MDIS_CUBE = workspace_test_data_path("mosrange", "EN0108828322M_iof.cub")


class ChipUnitTest(unittest.TestCase):
    """Test suite for Chip class bindings"""

    def test_chip_construction(self):
        """Test basic Chip construction"""
        chip = ip.Chip()
        self.assertIsNotNone(chip)
        self.assertIn("Chip", repr(chip))

    def test_chip_set_size(self):
        """Test setting chip size"""
        chip = ip.Chip()
        chip.set_size(10, 15)
        self.assertEqual(chip.samples(), 10)
        self.assertEqual(chip.lines(), 15)

    def test_chip_set_and_get_value(self):
        """Test setting and getting individual chip values"""
        chip = ip.Chip()
        chip.set_size(5, 5)
        chip.set_value(3, 3, 42.5)
        value = chip.get_value(3, 3)
        self.assertAlmostEqual(value, 42.5, places=12)

    def test_chip_set_all_values(self):
        """Test setting all chip values to a constant"""
        chip = ip.Chip()
        chip.set_size(5, 5)
        chip.set_all_values(10.0)

        # Check a few sample values
        self.assertAlmostEqual(chip.get_value(1, 1), 10.0, places=12)
        self.assertAlmostEqual(chip.get_value(3, 3), 10.0, places=12)
        self.assertAlmostEqual(chip.get_value(5, 5), 10.0, places=12)

    def test_chip_is_inside_chip(self):
        """Test checking if coordinates are inside chip"""
        chip = ip.Chip()
        chip.set_size(10, 10)

        self.assertTrue(chip.is_inside_chip(5.0, 5.0))
        self.assertTrue(chip.is_inside_chip(1.0, 1.0))
        self.assertFalse(chip.is_inside_chip(0.0, 0.0))
        self.assertFalse(chip.is_inside_chip(11.0, 11.0))

    def test_chip_set_valid_range(self):
        """Test setting valid pixel range"""
        chip = ip.Chip()
        chip.set_size(5, 5)

        # Set valid range and test with values
        chip.set_valid_range(0.0, 100.0)
        chip.set_value(3, 3, 50.0)
        self.assertTrue(chip.is_valid(3, 3))

    def test_chip_tack_cube(self):
        """Test tacking chip to cube position"""
        chip = ip.Chip()
        chip.set_size(5, 5)
        chip.tack_cube(100.0, 200.0)

        self.assertEqual(chip.tack_sample(), 100)
        self.assertEqual(chip.tack_line(), 200)

    def test_chip_set_chip_position(self):
        """Test setting chip position"""
        chip = ip.Chip()
        chip.set_size(10, 10)
        chip.set_chip_position(5.0, 7.0)

        self.assertAlmostEqual(chip.chip_sample(), 5.0, places=12)
        self.assertAlmostEqual(chip.chip_line(), 7.0, places=12)

    def test_chip_set_cube_position(self):
        """Test setting cube position"""
        chip = ip.Chip()
        chip.set_size(10, 10)
        chip.set_cube_position(100.0, 200.0)

        self.assertAlmostEqual(chip.cube_sample(), 100.0, places=12)
        self.assertAlmostEqual(chip.cube_line(), 200.0, places=12)

    def test_chip_repr(self):
        """Test chip representation"""
        chip = ip.Chip()
        chip.set_size(8, 12)
        repr_str = repr(chip)

        self.assertIn("Chip", repr_str)
        self.assertIn("8", repr_str)
        self.assertIn("12", repr_str)


class AutoRegUnitTest(unittest.TestCase):
    """Test suite for AutoReg class bindings"""

    def test_autoreg_register_status_enum(self):
        """Test AutoReg RegisterStatus enum values are accessible"""
        self.assertIsNotNone(ip.AutoReg.RegisterStatus.SuccessPixel)
        self.assertIsNotNone(ip.AutoReg.RegisterStatus.SuccessSubPixel)
        self.assertIsNotNone(ip.AutoReg.RegisterStatus.PatternChipNotEnoughValidData)
        self.assertIsNotNone(ip.AutoReg.RegisterStatus.FitChipNoData)
        self.assertIsNotNone(ip.AutoReg.RegisterStatus.FitChipToleranceNotMet)
        self.assertIsNotNone(ip.AutoReg.RegisterStatus.SurfaceModelNotEnoughValidData)
        self.assertIsNotNone(ip.AutoReg.RegisterStatus.SurfaceModelSolutionInvalid)
        self.assertIsNotNone(ip.AutoReg.RegisterStatus.SurfaceModelDistanceInvalid)
        self.assertIsNotNone(ip.AutoReg.RegisterStatus.PatternZScoreNotMet)
        self.assertIsNotNone(ip.AutoReg.RegisterStatus.AdaptiveAlgorithmFailed)

    def test_autoreg_gradient_filter_type_enum(self):
        """Test AutoReg GradientFilterType enum values are accessible"""
        self.assertIsNotNone(ip.AutoReg.GradientFilterType.NoFilter)  # Renamed from None to avoid Python keyword
        self.assertIsNotNone(ip.AutoReg.GradientFilterType.Sobel)


if __name__ == '__main__':
    unittest.main()
