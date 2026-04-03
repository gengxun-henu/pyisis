"""
Unit tests for ISIS utility classes: Column, LineEquation

Author: Geng Xun
Created: 2026-03-24
Last Modified: 2026-04-03
"""
import unittest

from _unit_test_support import ip


class ColumnUnitTest(unittest.TestCase):
    """Test suite for Column class bindings"""

    def test_column_construction(self):
        """Test basic Column construction"""
        column = ip.Column()
        self.assertIsNotNone(column)
        self.assertIn("Column", repr(column))

    def test_column_set_name(self):
        """Test setting and getting column name"""
        column = ip.Column()
        column.set_name("TestColumn")
        self.assertEqual(column.name(), "TestColumn")

    def test_column_set_name_rejects_name_wider_than_width(self):
        """Test setting a name wider than the configured width raises"""
        column = ip.Column()
        column.set_width(5)

        with self.assertRaises(ip.IException):
            column.set_name("TooLongName")

    def test_column_set_width(self):
        """Test setting and getting column width"""
        column = ip.Column()
        column.set_width(20)
        self.assertEqual(column.width(), 20)

    def test_column_set_width_rejects_existing_name_that_is_too_wide(self):
        """Test shrinking width below the current name length raises"""
        column = ip.Column()
        column.set_name("LongName")

        with self.assertRaises(ip.IException):
            column.set_width(4)

    def test_column_set_type(self):
        """Test setting and getting column type"""
        column = ip.Column()
        column.set_type(ip.Column.Type.Integer)
        self.assertEqual(column.data_type(), ip.Column.Type.Integer)

        column.set_type(ip.Column.Type.Real)
        self.assertEqual(column.data_type(), ip.Column.Type.Real)

        column.set_type(ip.Column.Type.String)
        self.assertEqual(column.data_type(), ip.Column.Type.String)

    def test_column_set_alignment(self):
        """Test setting and getting column alignment"""
        column = ip.Column()
        column.set_alignment(ip.Column.Align.Right)
        self.assertEqual(column.alignment(), ip.Column.Align.Right)

        column.set_alignment(ip.Column.Align.Left)
        self.assertEqual(column.alignment(), ip.Column.Align.Left)

        column.set_alignment(ip.Column.Align.Decimal)
        self.assertEqual(column.alignment(), ip.Column.Align.Decimal)

    def test_column_set_alignment_rejects_decimal_for_string_type(self):
        """Test decimal alignment is rejected for string columns"""
        column = ip.Column()
        column.set_type(ip.Column.Type.String)

        with self.assertRaises(ip.IException):
            column.set_alignment(ip.Column.Align.Decimal)

    def test_column_set_precision(self):
        """Test setting and getting column precision"""
        column = ip.Column()
        column.set_type(ip.Column.Type.Real)
        column.set_alignment(ip.Column.Align.Decimal)
        column.set_precision(5)
        self.assertEqual(column.precision(), 5)

    def test_column_set_precision_requires_real_or_pixel_type(self):
        """Test precision raises for unsupported column types"""
        column = ip.Column()

        with self.assertRaises(ip.IException):
            column.set_precision(5)

    def test_column_full_configuration(self):
        """Test configuring a column with all parameters"""
        column = ip.Column()
        column.set_name("SampleData")
        column.set_width(15)
        column.set_type(ip.Column.Type.Real)
        column.set_alignment(ip.Column.Align.Decimal)
        column.set_precision(3)

        self.assertEqual(column.name(), "SampleData")
        self.assertEqual(column.width(), 15)
        self.assertEqual(column.data_type(), ip.Column.Type.Real)
        self.assertEqual(column.alignment(), ip.Column.Align.Decimal)
        self.assertEqual(column.precision(), 3)

        repr_str = repr(column)
        self.assertIn("Column", repr_str)
        self.assertIn("SampleData", repr_str)

    def test_column_align_enum_values(self):
        """Test Column Align enum values are accessible"""
        self.assertIsNotNone(ip.Column.Align.NoAlign)
        self.assertIsNotNone(ip.Column.Align.Right)
        self.assertIsNotNone(ip.Column.Align.Left)
        self.assertIsNotNone(ip.Column.Align.Decimal)

    def test_column_type_enum_values(self):
        """Test Column Type enum values are accessible"""
        self.assertIsNotNone(ip.Column.Type.NoType)
        self.assertIsNotNone(ip.Column.Type.Integer)
        self.assertIsNotNone(ip.Column.Type.Real)
        self.assertIsNotNone(ip.Column.Type.String)
        self.assertIsNotNone(ip.Column.Type.Pixel)


class LineEquationUnitTest(unittest.TestCase):
    """Test suite for LineEquation class bindings. Added: 2026-03-30."""

    def test_default_constructor(self):
        """Test default constructor creates an undefined LineEquation"""
        line = ip.LineEquation()
        self.assertIsNotNone(line)
        self.assertFalse(line.defined())
        self.assertFalse(line.have_slope())
        self.assertFalse(line.have_intercept())
        self.assertEqual(line.points(), 0)

    def test_two_point_constructor(self):
        """Test constructor with two points creates a defined line"""
        line = ip.LineEquation(1.0, 2.0, 3.0, 4.0)
        self.assertTrue(line.defined())
        self.assertTrue(line.have_slope())
        self.assertTrue(line.have_intercept())
        self.assertEqual(line.points(), 2)
        self.assertAlmostEqual(line.slope(), 1.0)
        self.assertAlmostEqual(line.intercept(), 1.0)

    def test_add_points_incrementally(self):
        """Test adding points one at a time"""
        line = ip.LineEquation()

        # First point
        line.add_point(1.0, 2.0)
        self.assertEqual(line.points(), 1)
        self.assertFalse(line.have_slope())
        self.assertFalse(line.have_intercept())
        self.assertFalse(line.defined())

        # Second point
        line.add_point(3.0, 4.0)
        self.assertEqual(line.points(), 2)
        self.assertFalse(line.have_slope())  # Not computed yet
        self.assertFalse(line.have_intercept())  # Not computed yet
        self.assertTrue(line.defined())

        # Compute slope and intercept
        self.assertAlmostEqual(line.slope(), 1.0)
        self.assertAlmostEqual(line.intercept(), 1.0)
        self.assertTrue(line.have_slope())
        self.assertTrue(line.have_intercept())

    def test_slope_and_intercept_calculation(self):
        """Test various slope and intercept calculations"""
        # Positive slope
        line1 = ip.LineEquation(0.0, 0.0, 2.0, 4.0)
        self.assertAlmostEqual(line1.slope(), 2.0)
        self.assertAlmostEqual(line1.intercept(), 0.0)

        # Negative slope
        line2 = ip.LineEquation(0.0, 5.0, 5.0, 0.0)
        self.assertAlmostEqual(line2.slope(), -1.0)
        self.assertAlmostEqual(line2.intercept(), 5.0)

        # Horizontal line (slope = 0)
        line3 = ip.LineEquation(1.0, 3.0, 5.0, 3.0)
        self.assertAlmostEqual(line3.slope(), 0.0)
        self.assertAlmostEqual(line3.intercept(), 3.0)

    def test_add_third_point_raises_exception(self):
        """Test that adding a third point raises an exception"""
        line = ip.LineEquation()
        line.add_point(1.0, 2.0)
        line.add_point(3.0, 4.0)

        with self.assertRaises(ip.IException) as context:
            line.add_point(5.0, 6.0)

        self.assertIn("already defined", str(context.exception).lower())

    def test_slope_undefined_line_raises_exception(self):
        """Test that getting slope of undefined line raises exception"""
        line = ip.LineEquation()

        with self.assertRaises(ip.IException) as context:
            line.slope()

        self.assertIn("undefined", str(context.exception).lower())

    def test_intercept_undefined_line_raises_exception(self):
        """Test that getting intercept of undefined line raises exception"""
        line = ip.LineEquation()

        with self.assertRaises(ip.IException) as context:
            line.intercept()

        self.assertIn("undefined", str(context.exception).lower())

    def test_vertical_line_raises_exception_on_slope(self):
        """Test that a vertical line (same x values) raises exception when computing slope"""
        line = ip.LineEquation()
        line.add_point(1.0, 2.0)
        line.add_point(1.0, 5.0)  # Same x, different y (vertical line)

        self.assertTrue(line.defined())

        with self.assertRaises(ip.IException) as context:
            line.slope()

        self.assertIn("identical", str(context.exception).lower())

    def test_vertical_line_raises_exception_on_intercept(self):
        """Test that a vertical line raises exception when computing intercept"""
        line = ip.LineEquation()
        line.add_point(1.0, 1.0)
        line.add_point(1.0, 1.0)  # Identical points (also vertical)

        self.assertTrue(line.defined())

        with self.assertRaises(ip.IException) as context:
            line.intercept()

        self.assertIn("identical", str(context.exception).lower())

    def test_vertical_line_constructor_raises_exception(self):
        """Test that constructing with vertical line points raises exception"""
        with self.assertRaises(ip.IException) as context:
            ip.LineEquation(1.0, 1.0, 1.0, 5.0)

        self.assertIn("identical", str(context.exception).lower())

    def test_repr_undefined_line(self):
        """Test __repr__ for undefined line"""
        line = ip.LineEquation()
        repr_str = repr(line)
        self.assertIn("LineEquation", repr_str)
        self.assertIn("points=0", repr_str)

    def test_repr_defined_line(self):
        """Test __repr__ for defined line with valid slope/intercept"""
        line = ip.LineEquation(0.0, 0.0, 1.0, 2.0)
        repr_str = repr(line)
        self.assertIn("LineEquation", repr_str)
        self.assertIn("slope", repr_str)
        self.assertIn("intercept", repr_str)

    def test_repr_vertical_line(self):
        """Test __repr__ for vertical line (catches exception internally)"""
        line = ip.LineEquation()
        line.add_point(1.0, 1.0)
        line.add_point(1.0, 5.0)
        repr_str = repr(line)
        self.assertIn("LineEquation", repr_str)
        self.assertIn("defined=True", repr_str)
        self.assertIn("points=2", repr_str)


if __name__ == '__main__':
    unittest.main()
