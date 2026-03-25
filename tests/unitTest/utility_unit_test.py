"""
Unit tests for ISIS utility classes: Column
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


if __name__ == '__main__':
    unittest.main()
