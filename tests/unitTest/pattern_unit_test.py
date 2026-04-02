"""
Unit tests for ISIS pattern matching classes: Chip, AutoReg, and MaximumCorrelation

Author: Geng Xun
Created: 2026-03-24
Last Modified: 2026-04-02
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
        chip.tack_cube(100.0, 200.0)

        self.assertTrue(chip.is_inside_chip(100.0, 200.0))
        self.assertTrue(chip.is_inside_chip(96.0, 196.0))
        self.assertFalse(chip.is_inside_chip(95.0, 195.0))
        self.assertFalse(chip.is_inside_chip(105.0, 205.0))

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
        chip.set_chip_position(chip.tack_sample(), chip.tack_line())

        self.assertEqual(chip.tack_sample(), 3)
        self.assertEqual(chip.tack_line(), 3)
        self.assertAlmostEqual(chip.cube_sample(), 100.0, places=12)
        self.assertAlmostEqual(chip.cube_line(), 200.0, places=12)

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


class MaximumCorrelationUnitTest(unittest.TestCase):
    """Test suite for MaximumCorrelation class bindings.

    Added: 2026-04-02
    """

    def test_maximum_correlation_construction(self):
        """Test MaximumCorrelation construction with PVL configuration"""
        # Create PVL configuration for MaximumCorrelation
        pvl = ip.Pvl()
        autoreg_obj = ip.PvlObject("AutoRegistration")

        # Algorithm group
        alg_group = ip.PvlGroup("Algorithm")
        alg_group.add_keyword(ip.PvlKeyword("Name", "MaximumCorrelation"))
        alg_group.add_keyword(ip.PvlKeyword("Tolerance", "0.7"))
        alg_group.add_keyword(ip.PvlKeyword("SubpixelAccuracy", "True"))
        autoreg_obj.add_group(alg_group)

        # PatternChip group
        pattern_group = ip.PvlGroup("PatternChip")
        pattern_group.add_keyword(ip.PvlKeyword("Samples", "15"))
        pattern_group.add_keyword(ip.PvlKeyword("Lines", "15"))
        pattern_group.add_keyword(ip.PvlKeyword("ValidPercent", "50"))
        autoreg_obj.add_group(pattern_group)

        # SearchChip group
        search_group = ip.PvlGroup("SearchChip")
        search_group.add_keyword(ip.PvlKeyword("Samples", "35"))
        search_group.add_keyword(ip.PvlKeyword("Lines", "35"))
        autoreg_obj.add_group(search_group)

        pvl.add_object(autoreg_obj)

        # Construct MaximumCorrelation
        max_corr = ip.MaximumCorrelation(pvl)
        self.assertIsNotNone(max_corr)
        self.assertIn("MaximumCorrelation", repr(max_corr))

    def test_maximum_correlation_inherited_methods(self):
        """Test that MaximumCorrelation inherits AutoReg methods"""
        # Create PVL configuration
        pvl = ip.Pvl()
        autoreg_obj = ip.PvlObject("AutoRegistration")

        alg_group = ip.PvlGroup("Algorithm")
        alg_group.add_keyword(ip.PvlKeyword("Name", "MaximumCorrelation"))
        alg_group.add_keyword(ip.PvlKeyword("Tolerance", "0.7"))
        autoreg_obj.add_group(alg_group)

        pattern_group = ip.PvlGroup("PatternChip")
        pattern_group.add_keyword(ip.PvlKeyword("Samples", "15"))
        pattern_group.add_keyword(ip.PvlKeyword("Lines", "15"))
        autoreg_obj.add_group(pattern_group)

        search_group = ip.PvlGroup("SearchChip")
        search_group.add_keyword(ip.PvlKeyword("Samples", "35"))
        search_group.add_keyword(ip.PvlKeyword("Lines", "35"))
        autoreg_obj.add_group(search_group)

        pvl.add_object(autoreg_obj)

        max_corr = ip.MaximumCorrelation(pvl)

        # Test inherited chip access methods
        self.assertIsNotNone(max_corr.pattern_chip())
        self.assertIsNotNone(max_corr.search_chip())
        self.assertIsNotNone(max_corr.fit_chip())

        # Test inherited configuration methods
        self.assertTrue(max_corr.sub_pixel_accuracy())
        self.assertAlmostEqual(max_corr.tolerance(), 0.7, places=6)

    def test_maximum_correlation_repr(self):
        """Test MaximumCorrelation __repr__"""
        pvl = ip.Pvl()
        autoreg_obj = ip.PvlObject("AutoRegistration")

        alg_group = ip.PvlGroup("Algorithm")
        alg_group.add_keyword(ip.PvlKeyword("Name", "MaximumCorrelation"))
        alg_group.add_keyword(ip.PvlKeyword("Tolerance", "0.7"))
        autoreg_obj.add_group(alg_group)

        pattern_group = ip.PvlGroup("PatternChip")
        pattern_group.add_keyword(ip.PvlKeyword("Samples", "15"))
        pattern_group.add_keyword(ip.PvlKeyword("Lines", "15"))
        autoreg_obj.add_group(pattern_group)

        search_group = ip.PvlGroup("SearchChip")
        search_group.add_keyword(ip.PvlKeyword("Samples", "35"))
        search_group.add_keyword(ip.PvlKeyword("Lines", "35"))
        autoreg_obj.add_group(search_group)

        pvl.add_object(autoreg_obj)

        max_corr = ip.MaximumCorrelation(pvl)
        repr_str = repr(max_corr)

        self.assertIn("MaximumCorrelation", repr_str)
        self.assertIn("status=", repr_str)
        self.assertIn("goodness_of_fit=", repr_str)


if __name__ == '__main__':
    unittest.main()
