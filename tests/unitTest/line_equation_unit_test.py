"""
Unit tests for ISIS LineEquation bindings

Author: Geng Xun
Created: 2026-03-30
Last Modified: 2026-03-30
"""

import unittest
import sys
from pathlib import Path

# Add build directory to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILD_PYTHON_DIR = PROJECT_ROOT / "build" / "python"
if BUILD_PYTHON_DIR.exists():
    sys.path.insert(0, str(BUILD_PYTHON_DIR))

import isis_pybind as ip


class TestLineEquationConstruction(unittest.TestCase):
    """Test LineEquation construction methods. Added: 2026-03-30."""

    def test_default_constructor(self):
        """Test default constructor creates an undefined line equation."""
        line_eq = ip.LineEquation()
        self.assertFalse(line_eq.defined())
        self.assertFalse(line_eq.have_slope())
        self.assertFalse(line_eq.have_intercept())
        self.assertEqual(line_eq.points(), 0)

    def test_two_point_constructor(self):
        """Test constructor with two points."""
        line_eq = ip.LineEquation(1.0, 2.0, 3.0, 4.0)
        self.assertTrue(line_eq.defined())
        self.assertTrue(line_eq.have_slope())
        self.assertTrue(line_eq.have_intercept())
        self.assertEqual(line_eq.points(), 2)
        self.assertAlmostEqual(line_eq.slope(), 1.0)
        self.assertAlmostEqual(line_eq.intercept(), 1.0)

    def test_constructor_with_vertical_line_raises(self):
        """Test that vertical line (same x values) raises exception."""
        with self.assertRaises(RuntimeError) as context:
            ip.LineEquation(1.0, 1.0, 1.0, 5.0)
        self.assertIn("identical", str(context.exception).lower())


class TestLineEquationAddPoint(unittest.TestCase):
    """Test LineEquation add_point method. Added: 2026-03-30."""

    def test_add_single_point(self):
        """Test adding a single point."""
        line_eq = ip.LineEquation()
        line_eq.add_point(1.0, 2.0)
        self.assertEqual(line_eq.points(), 1)
        self.assertFalse(line_eq.defined())
        self.assertFalse(line_eq.have_slope())
        self.assertFalse(line_eq.have_intercept())

    def test_add_two_points(self):
        """Test adding two points defines the line."""
        line_eq = ip.LineEquation()
        line_eq.add_point(1.0, 2.0)
        line_eq.add_point(3.0, 4.0)
        self.assertTrue(line_eq.defined())
        self.assertEqual(line_eq.points(), 2)

    def test_add_third_point_raises(self):
        """Test that adding a third point raises an exception."""
        line_eq = ip.LineEquation()
        line_eq.add_point(1.0, 2.0)
        line_eq.add_point(3.0, 4.0)
        with self.assertRaises(RuntimeError) as context:
            line_eq.add_point(5.0, 6.0)
        self.assertIn("already defined", str(context.exception).lower())

    def test_points_with_identical_x_values(self):
        """Test that adding points with identical x values causes error on slope/intercept."""
        line_eq = ip.LineEquation()
        line_eq.add_point(1.0, 1.0)
        line_eq.add_point(1.0, 5.0)
        self.assertTrue(line_eq.defined())
        with self.assertRaises(RuntimeError) as context:
            _ = line_eq.slope()
        self.assertIn("identical", str(context.exception).lower())


class TestLineEquationSlopeIntercept(unittest.TestCase):
    """Test LineEquation slope and intercept methods. Added: 2026-03-30."""

    def test_slope_simple_line(self):
        """Test slope calculation for y = x."""
        line_eq = ip.LineEquation(0.0, 0.0, 1.0, 1.0)
        self.assertAlmostEqual(line_eq.slope(), 1.0)

    def test_intercept_simple_line(self):
        """Test intercept calculation for y = x."""
        line_eq = ip.LineEquation(0.0, 0.0, 1.0, 1.0)
        self.assertAlmostEqual(line_eq.intercept(), 0.0)

    def test_slope_and_intercept_y_equals_2x_plus_3(self):
        """Test slope and intercept for y = 2x + 3."""
        # Points: (0, 3) and (1, 5)
        line_eq = ip.LineEquation(0.0, 3.0, 1.0, 5.0)
        self.assertAlmostEqual(line_eq.slope(), 2.0)
        self.assertAlmostEqual(line_eq.intercept(), 3.0)

    def test_negative_slope(self):
        """Test negative slope calculation."""
        # Points: (0, 5) and (5, 0) -> slope = -1
        line_eq = ip.LineEquation(0.0, 5.0, 5.0, 0.0)
        self.assertAlmostEqual(line_eq.slope(), -1.0)
        self.assertAlmostEqual(line_eq.intercept(), 5.0)

    def test_slope_before_defined_raises(self):
        """Test that calling slope before line is defined raises exception."""
        line_eq = ip.LineEquation()
        with self.assertRaises(RuntimeError) as context:
            _ = line_eq.slope()
        self.assertIn("undefined", str(context.exception).lower())

    def test_intercept_before_defined_raises(self):
        """Test that calling intercept before line is defined raises exception."""
        line_eq = ip.LineEquation()
        with self.assertRaises(RuntimeError) as context:
            _ = line_eq.intercept()
        self.assertIn("undefined", str(context.exception).lower())

    def test_slope_computed_once(self):
        """Test that slope is cached after first computation."""
        line_eq = ip.LineEquation(1.0, 2.0, 3.0, 4.0)
        self.assertFalse(line_eq.have_slope())
        slope1 = line_eq.slope()
        self.assertTrue(line_eq.have_slope())
        slope2 = line_eq.slope()
        self.assertEqual(slope1, slope2)

    def test_intercept_computed_once(self):
        """Test that intercept is cached after first computation."""
        line_eq = ip.LineEquation(1.0, 2.0, 3.0, 4.0)
        self.assertFalse(line_eq.have_intercept())
        intercept1 = line_eq.intercept()
        self.assertTrue(line_eq.have_intercept())
        intercept2 = line_eq.intercept()
        self.assertEqual(intercept1, intercept2)


class TestLineEquationStatusMethods(unittest.TestCase):
    """Test LineEquation status query methods. Added: 2026-03-30."""

    def test_defined_status_progression(self):
        """Test defined status changes as points are added."""
        line_eq = ip.LineEquation()
        self.assertFalse(line_eq.defined())
        line_eq.add_point(1.0, 2.0)
        self.assertFalse(line_eq.defined())
        line_eq.add_point(3.0, 4.0)
        self.assertTrue(line_eq.defined())

    def test_have_slope_after_computation(self):
        """Test have_slope returns True after slope is computed."""
        line_eq = ip.LineEquation(1.0, 2.0, 3.0, 4.0)
        self.assertFalse(line_eq.have_slope())
        _ = line_eq.slope()
        self.assertTrue(line_eq.have_slope())

    def test_have_intercept_after_computation(self):
        """Test have_intercept returns True after intercept is computed."""
        line_eq = ip.LineEquation(1.0, 2.0, 3.0, 4.0)
        self.assertFalse(line_eq.have_intercept())
        _ = line_eq.intercept()
        self.assertTrue(line_eq.have_intercept())

    def test_points_count(self):
        """Test points count matches number of added points."""
        line_eq = ip.LineEquation()
        self.assertEqual(line_eq.points(), 0)
        line_eq.add_point(1.0, 2.0)
        self.assertEqual(line_eq.points(), 1)
        line_eq.add_point(3.0, 4.0)
        self.assertEqual(line_eq.points(), 2)


class TestLineEquationRepr(unittest.TestCase):
    """Test LineEquation __repr__ method. Added: 2026-03-30."""

    def test_repr_undefined(self):
        """Test repr for undefined line equation."""
        line_eq = ip.LineEquation()
        repr_str = repr(line_eq)
        self.assertIn("LineEquation", repr_str)
        self.assertIn("defined=False", repr_str)
        self.assertIn("points=0", repr_str)

    def test_repr_defined_without_slope_intercept(self):
        """Test repr for defined line without computed slope/intercept."""
        line_eq = ip.LineEquation(1.0, 2.0, 3.0, 4.0)
        # Don't call slope() or intercept() yet
        repr_str = repr(line_eq)
        self.assertIn("LineEquation", repr_str)
        self.assertIn("defined=True", repr_str)
        self.assertIn("points=2", repr_str)

    def test_repr_with_slope_and_intercept(self):
        """Test repr after slope and intercept have been computed."""
        line_eq = ip.LineEquation(1.0, 2.0, 3.0, 4.0)
        _ = line_eq.slope()
        _ = line_eq.intercept()
        repr_str = repr(line_eq)
        self.assertIn("LineEquation", repr_str)
        self.assertIn("defined=True", repr_str)
        self.assertIn("points=2", repr_str)
        self.assertIn("slope=", repr_str)
        self.assertIn("intercept=", repr_str)


class TestLineEquationEdgeCases(unittest.TestCase):
    """Test LineEquation edge cases and error conditions. Added: 2026-03-30."""

    def test_horizontal_line(self):
        """Test horizontal line (zero slope)."""
        line_eq = ip.LineEquation(1.0, 5.0, 3.0, 5.0)
        self.assertAlmostEqual(line_eq.slope(), 0.0)
        self.assertAlmostEqual(line_eq.intercept(), 5.0)

    def test_large_values(self):
        """Test with large coordinate values."""
        line_eq = ip.LineEquation(1000000.0, 2000000.0, 3000000.0, 4000000.0)
        self.assertTrue(line_eq.defined())
        self.assertAlmostEqual(line_eq.slope(), 1.0)

    def test_negative_values(self):
        """Test with negative coordinate values."""
        line_eq = ip.LineEquation(-5.0, -10.0, -3.0, -6.0)
        self.assertTrue(line_eq.defined())
        self.assertAlmostEqual(line_eq.slope(), 2.0)
        self.assertAlmostEqual(line_eq.intercept(), 0.0)

    def test_fractional_values(self):
        """Test with fractional coordinate values."""
        line_eq = ip.LineEquation(0.5, 1.5, 1.5, 3.5)
        self.assertTrue(line_eq.defined())
        self.assertAlmostEqual(line_eq.slope(), 2.0)
        self.assertAlmostEqual(line_eq.intercept(), 0.5)


if __name__ == "__main__":
    unittest.main()
