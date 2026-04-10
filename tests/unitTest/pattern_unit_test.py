"""
Unit tests for ISIS pattern matching classes: Chip, AutoReg, MaximumCorrelation, MinimumDifference, Gruen, AdaptiveGruen, and AutoRegFactory

Author: Geng Xun
Created: 2026-03-24
Last Modified: 2026-04-10
Updated: 2026-04-08  Geng Xun added focused regression coverage for Centroid chip selection bindings.
Updated: 2026-04-09  Geng Xun added MinimumDifference binding unit tests.
Updated: 2026-04-10  Geng Xun fixed MinimumDifference regression tests to use upstream-style AutoRegistration PVL objects.
Updated: 2026-04-10  Geng Xun added Gruen and AdaptiveGruen focused unit tests.
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

    @classmethod
    def _make_maximum_correlation(cls, tolerance=0.7, subpixel=True):
        """Helper to create a MaximumCorrelation instance for testing AutoReg methods."""
        pvl = ip.Pvl()
        autoreg_obj = ip.PvlObject("AutoRegistration")

        alg_group = ip.PvlGroup("Algorithm")
        alg_group.add_keyword(ip.PvlKeyword("Name", "MaximumCorrelation"))
        alg_group.add_keyword(ip.PvlKeyword("Tolerance", str(tolerance)))
        if subpixel:
            alg_group.add_keyword(ip.PvlKeyword("SubpixelAccuracy", "True"))
        autoreg_obj.add_group(alg_group)

        pattern_group = ip.PvlGroup("PatternChip")
        pattern_group.add_keyword(ip.PvlKeyword("Samples", "15"))
        pattern_group.add_keyword(ip.PvlKeyword("Lines", "15"))
        pattern_group.add_keyword(ip.PvlKeyword("ValidPercent", "50"))
        pattern_group.add_keyword(ip.PvlKeyword("MinimumZScore", "1.5"))
        autoreg_obj.add_group(pattern_group)

        search_group = ip.PvlGroup("SearchChip")
        search_group.add_keyword(ip.PvlKeyword("Samples", "35"))
        search_group.add_keyword(ip.PvlKeyword("Lines", "35"))
        autoreg_obj.add_group(search_group)

        pvl.add_object(autoreg_obj)
        return pvl, ip.MaximumCorrelation(pvl)

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

    def test_autoreg_minimum_z_score(self):
        """Test AutoReg minimum_z_score returns configured value. Added: 2026-04-03"""
        _pvl, mc = self._make_maximum_correlation()
        self.assertAlmostEqual(mc.minimum_z_score(), 1.5, places=6)

    def test_autoreg_z_scores(self):
        """Test AutoReg z_scores returns a tuple of two floats. Added: 2026-04-03"""
        _pvl, mc = self._make_maximum_correlation()
        scores = mc.z_scores()
        self.assertIsInstance(scores, tuple)
        self.assertEqual(len(scores), 2)
        # Before registration, z-scores are initialised to zero
        self.assertIsInstance(scores[0], float)
        self.assertIsInstance(scores[1], float)

    def test_autoreg_registration_statistics(self):
        """Test AutoReg registration_statistics returns a Pvl object. Added: 2026-04-03"""
        _pvl, mc = self._make_maximum_correlation()
        stats = mc.registration_statistics()
        self.assertIsInstance(stats, ip.Pvl)

    def test_autoreg_most_lenient_tolerance(self):
        """Test AutoReg most_lenient_tolerance returns a float. Added: 2026-04-03"""
        _pvl, mc = self._make_maximum_correlation()
        val = mc.most_lenient_tolerance()
        self.assertIsInstance(val, float)

    def test_autoreg_algorithm_name(self):
        """Test AutoReg algorithm_name returns the concrete algorithm name. Added: 2026-04-03"""
        _pvl, mc = self._make_maximum_correlation()
        name = mc.algorithm_name()
        self.assertEqual(name, "MaximumCorrelation")

    def test_autoreg_reg_template(self):
        """Test AutoReg reg_template returns a PvlGroup. Added: 2026-04-03"""
        _pvl, mc = self._make_maximum_correlation()
        tmpl = mc.reg_template()
        self.assertIsInstance(tmpl, ip.PvlGroup)

    def test_autoreg_updated_template(self):
        """Test AutoReg updated_template returns a PvlGroup reflecting current settings. Added: 2026-04-03"""
        _pvl, mc = self._make_maximum_correlation()
        tmpl = mc.updated_template()
        self.assertIsInstance(tmpl, ip.PvlGroup)


class CentroidUnitTest(unittest.TestCase):
    """Test suite for Centroid class bindings. Added: 2026-04-08."""

    @staticmethod
    def _make_input_chip():
        chip = ip.Chip()
        chip.set_size(5, 5)
        chip.set_all_values(0.0)
        chip.set_chip_position(3.0, 3.0)

        for sample, line in ((3, 3), (3, 2), (3, 4), (2, 3), (4, 3)):
            chip.set_value(sample, line, 10.0)

        chip.set_value(5, 5, 10.0)
        return chip

    def test_centroid_construction_and_range(self):
        """Test Centroid construction, getters, and range validation."""
        centroid = ip.Centroid()
        self.assertIn("Centroid", repr(centroid))
        self.assertEqual(centroid.get_min_dn(), 0.0)
        self.assertEqual(centroid.get_max_dn(), 0.0)

        self.assertEqual(centroid.set_dn_range(5.0, 15.0), 1)
        self.assertAlmostEqual(centroid.get_min_dn(), 5.0, places=12)
        self.assertAlmostEqual(centroid.get_max_dn(), 15.0, places=12)
        self.assertEqual(centroid.set_dn_range(20.0, 10.0), 0)

    def test_centroid_select_marks_connected_pixels(self):
        """Test Centroid.select flood-fills only the connected in-range region."""
        centroid = ip.Centroid()
        self.assertEqual(centroid.set_dn_range(5.0, 15.0), 1)

        input_chip = self._make_input_chip()
        selection_chip = ip.Chip()

        result = centroid.select(input_chip, selection_chip)
        self.assertEqual(result, 1)
        self.assertEqual(selection_chip.samples(), 5)
        self.assertEqual(selection_chip.lines(), 5)

        for sample, line in ((3, 3), (3, 2), (3, 4), (2, 3), (4, 3)):
            self.assertAlmostEqual(selection_chip.get_value(sample, line), 1.0, places=12)

        self.assertAlmostEqual(selection_chip.get_value(5, 5), 0.0, places=12)
        self.assertAlmostEqual(selection_chip.get_value(1, 1), 0.0, places=12)

    def test_centroid_select_returns_empty_when_seed_out_of_range(self):
        """Test Centroid.select returns an empty selection when the seed DN is excluded."""
        centroid = ip.Centroid()
        self.assertEqual(centroid.set_dn_range(20.0, 30.0), 1)

        input_chip = self._make_input_chip()
        selection_chip = ip.Chip()

        result = centroid.select(input_chip, selection_chip)
        self.assertEqual(result, 0)
        self.assertEqual(selection_chip.samples(), 5)
        self.assertEqual(selection_chip.lines(), 5)
        self.assertAlmostEqual(selection_chip.get_value(3, 3), 0.0, places=12)
        self.assertAlmostEqual(selection_chip.get_value(5, 5), 0.0, places=12)


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


class AutoRegFactoryUnitTest(unittest.TestCase):
    """Test suite for AutoRegFactory class bindings.

    Added: 2026-04-03
    """

    def test_auto_reg_factory_symbol_presence(self):
        """Test AutoRegFactory symbol is accessible"""
        self.assertIsNotNone(ip.AutoRegFactory)
        self.assertTrue(hasattr(ip.AutoRegFactory, 'create'))

    def test_auto_reg_factory_create_maximum_correlation(self):
        """Test creating MaximumCorrelation instance via factory"""
        # Create PVL configuration
        pvl = ip.Pvl()
        autoreg_obj = ip.PvlObject("AutoRegistration")

        # Algorithm group with MaximumCorrelation
        alg_group = ip.PvlGroup("Algorithm")
        alg_group.add_keyword(ip.PvlKeyword("Name", "MaximumCorrelation"))
        alg_group.add_keyword(ip.PvlKeyword("Tolerance", "0.7"))
        autoreg_obj.add_group(alg_group)

        # PatternChip group
        pattern_group = ip.PvlGroup("PatternChip")
        pattern_group.add_keyword(ip.PvlKeyword("Samples", "15"))
        pattern_group.add_keyword(ip.PvlKeyword("Lines", "15"))
        autoreg_obj.add_group(pattern_group)

        # SearchChip group
        search_group = ip.PvlGroup("SearchChip")
        search_group.add_keyword(ip.PvlKeyword("Samples", "35"))
        search_group.add_keyword(ip.PvlKeyword("Lines", "35"))
        autoreg_obj.add_group(search_group)

        pvl.add_object(autoreg_obj)

        # Create AutoReg instance via factory
        autoreg = ip.AutoRegFactory.create(pvl)
        self.assertIsNotNone(autoreg)

        # Verify it's an AutoReg instance with expected methods
        self.assertTrue(hasattr(autoreg, 'pattern_chip'))
        self.assertTrue(hasattr(autoreg, 'search_chip'))
        self.assertTrue(hasattr(autoreg, 'tolerance'))

        # Verify configuration was applied
        self.assertAlmostEqual(autoreg.tolerance(), 0.7, places=6)

    def test_auto_reg_factory_invalid_pvl(self):
        """Test AutoRegFactory.create with invalid PVL raises exception"""
        # Create incomplete PVL without required groups
        pvl = ip.Pvl()
        autoreg_obj = ip.PvlObject("AutoRegistration")
        pvl.add_object(autoreg_obj)

        # Should raise IException due to missing Algorithm group
        with self.assertRaises(ip.IException):
            ip.AutoRegFactory.create(pvl)

    def test_auto_reg_factory_unknown_algorithm(self):
        """Test AutoRegFactory.create with unknown algorithm raises exception"""
        pvl = ip.Pvl()
        autoreg_obj = ip.PvlObject("AutoRegistration")

        # Algorithm group with invalid/unknown algorithm name
        alg_group = ip.PvlGroup("Algorithm")
        alg_group.add_keyword(ip.PvlKeyword("Name", "NonExistentAlgorithm"))
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

        # Should raise IException for unknown algorithm
        with self.assertRaises(ip.IException):
            ip.AutoRegFactory.create(pvl)

    def test_auto_reg_factory_create_minimum_difference(self):
        """Test creating MinimumDifference instance via factory with valid AutoRegistration PVL."""
        pvl = MinimumDifferenceUnitTest._make_pvl()

        autoreg = ip.AutoRegFactory.create(pvl)

        self.assertIsNotNone(autoreg)
        self.assertIsInstance(autoreg, ip.AutoReg)
        self.assertEqual(autoreg.algorithm_name(), "MinimumDifference")
        self.assertAlmostEqual(autoreg.tolerance(), 0.01, places=6)


class MinimumDifferenceUnitTest(unittest.TestCase):
    """Focused unit tests for MinimumDifference binding. Added: 2026-04-09."""

    @staticmethod
    def _make_pvl():
        """Create a valid upstream-style AutoRegistration Pvl config for MinimumDifference."""
        pvl = ip.Pvl()

        autoreg_obj = ip.PvlObject("AutoRegistration")

        algorithm_group = ip.PvlGroup("Algorithm")
        algorithm_group.add_keyword(ip.PvlKeyword("Name", "MinimumDifference"))
        algorithm_group.add_keyword(ip.PvlKeyword("Tolerance", "0.01"))
        algorithm_group.add_keyword(ip.PvlKeyword("SubpixelAccuracy", "True"))
        autoreg_obj.add_group(algorithm_group)

        pattern_group = ip.PvlGroup("PatternChip")
        pattern_group.add_keyword(ip.PvlKeyword("Samples", "15"))
        pattern_group.add_keyword(ip.PvlKeyword("Lines", "15"))
        pattern_group.add_keyword(ip.PvlKeyword("ValidPercent", "50"))
        autoreg_obj.add_group(pattern_group)

        search_group = ip.PvlGroup("SearchChip")
        search_group.add_keyword(ip.PvlKeyword("Samples", "35"))
        search_group.add_keyword(ip.PvlKeyword("Lines", "35"))
        autoreg_obj.add_group(search_group)

        pvl.add_object(autoreg_obj)
        return pvl

    def test_construct(self):
        """MinimumDifference(pvl) constructs without error."""
        obj = ip.MinimumDifference(self._make_pvl())
        self.assertIsNotNone(obj)

    def test_is_instance_of_auto_reg(self):
        """MinimumDifference is a subtype of AutoReg."""
        obj = ip.MinimumDifference(self._make_pvl())
        self.assertIsInstance(obj, ip.AutoReg)

    def test_ideal_fit(self):
        """ideal_fit() returns 0.0 (perfect match is zero difference)."""
        obj = ip.MinimumDifference(self._make_pvl())
        self.assertAlmostEqual(obj.ideal_fit(), 0.0)

    def test_most_lenient_tolerance(self):
        """most_lenient_tolerance() returns a large positive float."""
        import math
        obj = ip.MinimumDifference(self._make_pvl())
        tol = obj.most_lenient_tolerance()
        self.assertTrue(math.isinf(tol) or tol > 1e100)

    def test_repr(self):
        """repr() includes MinimumDifference."""
        obj = ip.MinimumDifference(self._make_pvl())
        self.assertIn("MinimumDifference", repr(obj))

    def test_inherited_tolerance(self):
        """Inherited AutoReg tolerance() returns the configured tolerance."""
        obj = ip.MinimumDifference(self._make_pvl())
        self.assertAlmostEqual(obj.tolerance(), 0.01)


class GruenUnitTest(unittest.TestCase):
    """Focused unit tests for Gruen AutoReg subclass binding. Added: 2026-04-10."""

    def _make_gruen_pvl(self, alg_name="Gruen", tolerance=0.1):
        """Return a (Pvl, Gruen) pair for construction tests."""
        pvl = ip.Pvl()
        autoreg_obj = ip.PvlObject("AutoRegistration")

        alg_group = ip.PvlGroup("Algorithm")
        alg_group.add_keyword(ip.PvlKeyword("Name", alg_name))
        alg_group.add_keyword(ip.PvlKeyword("Tolerance", str(tolerance)))
        alg_group.add_keyword(ip.PvlKeyword("AffineTranslationTolerance", "0.2"))
        alg_group.add_keyword(ip.PvlKeyword("AffineScaleTolerance", "0.3"))
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
        return pvl, ip.Gruen(pvl)

    def test_gruen_class_exported(self):
        """Gruen is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "Gruen"))

    def test_gruen_construction(self):
        """Gruen constructs without error from a valid PVL."""
        _, gruen = self._make_gruen_pvl()
        self.assertIsInstance(gruen, ip.Gruen)

    def test_gruen_inherits_autoreg(self):
        """Gruen is an instance of AutoReg."""
        _, gruen = self._make_gruen_pvl()
        self.assertIsInstance(gruen, ip.AutoReg)

    def test_gruen_ideal_fit(self):
        """ideal_fit for Gruen is 0.0 (perfect affine convergence)."""
        _, gruen = self._make_gruen_pvl()
        self.assertAlmostEqual(gruen.ideal_fit(), 0.0)

    def test_gruen_algorithm_name(self):
        """algorithm_name for Gruen matches expected name."""
        _, gruen = self._make_gruen_pvl()
        name = gruen.algorithm_name()
        self.assertIn("Gruen", name)

    def test_gruen_constraint_accessors(self):
        """get_spice_constraint and get_affine_constraint return floats."""
        _, gruen = self._make_gruen_pvl()
        self.assertIsInstance(gruen.get_spice_constraint(), float)
        self.assertIsInstance(gruen.get_affine_constraint(), float)

    def test_gruen_repr(self):
        """repr(Gruen) contains 'Gruen'."""
        _, gruen = self._make_gruen_pvl()
        r = repr(gruen)
        self.assertIn("Gruen", r)


class AdaptiveGruenUnitTest(unittest.TestCase):
    """Focused unit tests for AdaptiveGruen binding. Added: 2026-04-10."""

    def _make_adaptive_gruen_pvl(self, tolerance=0.1):
        pvl = ip.Pvl()
        autoreg_obj = ip.PvlObject("AutoRegistration")

        alg_group = ip.PvlGroup("Algorithm")
        alg_group.add_keyword(ip.PvlKeyword("Name", "AdaptiveGruen"))
        alg_group.add_keyword(ip.PvlKeyword("Tolerance", str(tolerance)))
        alg_group.add_keyword(ip.PvlKeyword("AffineTranslationTolerance", "0.2"))
        alg_group.add_keyword(ip.PvlKeyword("AffineScaleTolerance", "0.3"))
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
        return pvl, ip.AdaptiveGruen(pvl)

    def test_adaptive_gruen_class_exported(self):
        """AdaptiveGruen is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "AdaptiveGruen"))

    def test_adaptive_gruen_construction(self):
        """AdaptiveGruen constructs without error from a valid PVL."""
        _, ag = self._make_adaptive_gruen_pvl()
        self.assertIsInstance(ag, ip.AdaptiveGruen)

    def test_adaptive_gruen_inherits_gruen(self):
        """AdaptiveGruen is an instance of Gruen."""
        _, ag = self._make_adaptive_gruen_pvl()
        self.assertIsInstance(ag, ip.Gruen)

    def test_adaptive_gruen_inherits_autoreg(self):
        """AdaptiveGruen is an instance of AutoReg (transitive inheritance)."""
        _, ag = self._make_adaptive_gruen_pvl()
        self.assertIsInstance(ag, ip.AutoReg)

    def test_adaptive_gruen_ideal_fit(self):
        """ideal_fit for AdaptiveGruen is 0.0."""
        _, ag = self._make_adaptive_gruen_pvl()
        self.assertAlmostEqual(ag.ideal_fit(), 0.0)

    def test_adaptive_gruen_repr(self):
        """repr(AdaptiveGruen) contains 'AdaptiveGruen'."""
        _, ag = self._make_adaptive_gruen_pvl()
        r = repr(ag)
        self.assertIn("AdaptiveGruen", r)


if __name__ == '__main__':
    unittest.main()
