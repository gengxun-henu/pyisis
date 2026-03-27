"""
Unit tests for ISIS utility classes: Column, IString

Author: Geng Xun
Created: 2026-03-24
Last Modified: 2026-03-27
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


class IStringUnitTest(unittest.TestCase):
    """Test suite for IString class bindings

    Added: 2026-03-27
    """

    def test_istring_default_construction(self):
        """Test default IString construction"""
        s = ip.IString()
        self.assertIsNotNone(s)
        self.assertEqual(str(s), "")
        self.assertIn("IString", repr(s))

    def test_istring_construction_from_string(self):
        """Test IString construction from std::string"""
        s = ip.IString("Hello World")
        self.assertEqual(str(s), "Hello World")
        self.assertEqual(s, "Hello World")

    def test_istring_construction_from_int(self):
        """Test IString construction from integer"""
        s = ip.IString(42)
        self.assertEqual(str(s), "42")
        self.assertEqual(s.to_integer(), 42)

    def test_istring_construction_from_double(self):
        """Test IString construction from double"""
        s = ip.IString(3.14159)
        self.assertIn("3.14159", str(s))

    def test_istring_construction_from_double_with_precision(self):
        """Test IString construction from double with precision"""
        s = ip.IString(3.14159, 2)
        # Check that the string representation is short
        self.assertTrue(len(str(s)) < 10)

    def test_istring_copy_construction(self):
        """Test IString copy construction"""
        s1 = ip.IString("Test")
        s2 = ip.IString(s1)
        self.assertEqual(str(s1), str(s2))

    def test_istring_trim(self):
        """Test trim method"""
        s = ip.IString("  Hello World  ")
        trimmed = s.trim(" ")
        self.assertEqual(str(trimmed), "Hello World")

    def test_istring_trim_head(self):
        """Test trim_head method"""
        s = ip.IString("  Hello World  ")
        trimmed = s.trim_head(" ")
        self.assertEqual(str(trimmed), "Hello World  ")

    def test_istring_trim_tail(self):
        """Test trim_tail method"""
        s = ip.IString("  Hello World  ")
        trimmed = s.trim_tail(" ")
        self.assertEqual(str(trimmed), "  Hello World")

    def test_istring_up_case(self):
        """Test up_case method"""
        s = ip.IString("Hello World")
        upper = s.up_case()
        self.assertEqual(str(upper), "HELLO WORLD")

    def test_istring_down_case(self):
        """Test down_case method"""
        s = ip.IString("Hello World")
        lower = s.down_case()
        self.assertEqual(str(lower), "hello world")

    def test_istring_compress(self):
        """Test compress method"""
        s = ip.IString("Hello    World")
        compressed = s.compress()
        # Should have fewer consecutive spaces
        self.assertTrue(len(str(compressed)) <= len(str(s)))

    def test_istring_replace(self):
        """Test replace method"""
        s = ip.IString("Hello World")
        replaced = s.replace("World", "Python")
        self.assertEqual(str(replaced), "Hello Python")

    def test_istring_convert(self):
        """Test convert method"""
        s = ip.IString("Hello World")
        converted = s.convert("o", "0")
        self.assertEqual(str(converted), "Hell0 W0rld")

    def test_istring_convert_white_space(self):
        """Test convert_white_space method"""
        s = ip.IString("Hello\tWorld\nTest")
        converted = s.convert_white_space()
        # Should convert tabs and newlines to spaces
        self.assertNotIn("\t", str(converted))
        self.assertNotIn("\n", str(converted))

    def test_istring_remove(self):
        """Test remove method"""
        s = ip.IString("Hello World")
        removed = s.remove("o")
        self.assertEqual(str(removed), "Hell Wrld")

    def test_istring_token(self):
        """Test token method"""
        s = ip.IString("one,two,three")
        token1 = s.token(",")
        self.assertEqual(str(token1), "one")

    def test_istring_to_integer(self):
        """Test to_integer method"""
        s = ip.IString("42")
        self.assertEqual(s.to_integer(), 42)

    def test_istring_to_double(self):
        """Test to_double method"""
        s = ip.IString("3.14159")
        self.assertAlmostEqual(s.to_double(), 3.14159, places=5)

    def test_istring_to_qt(self):
        """Test to_qt method"""
        s = ip.IString("Hello")
        qt_str = s.to_qt()
        self.assertEqual(qt_str, "Hello")

    def test_istring_static_trim(self):
        """Test static trim method"""
        result = ip.IString.trim_static(" ", "  Hello  ")
        self.assertEqual(result, "Hello")

    def test_istring_static_up_case(self):
        """Test static up_case method"""
        result = ip.IString.up_case_static("hello")
        self.assertEqual(result, "HELLO")

    def test_istring_static_down_case(self):
        """Test static down_case method"""
        result = ip.IString.down_case_static("HELLO")
        self.assertEqual(result, "hello")

    def test_istring_static_to_integer(self):
        """Test static to_integer method"""
        result = ip.IString.to_integer_static("42")
        self.assertEqual(result, 42)

    def test_istring_static_to_double(self):
        """Test static to_double method"""
        result = ip.IString.to_double_static("3.14159")
        self.assertAlmostEqual(result, 3.14159, places=5)

    def test_istring_static_compress(self):
        """Test static compress method"""
        result = ip.IString.compress_static("Hello    World")
        self.assertTrue(len(result) <= len("Hello    World"))

    def test_istring_static_replace(self):
        """Test static replace method"""
        result = ip.IString.replace_static("Hello World", "World", "Python")
        self.assertEqual(result, "Hello Python")

    def test_istring_static_convert(self):
        """Test static convert method"""
        result = ip.IString.convert_static("Hello", "o", "0")
        self.assertEqual(result, "Hell0")

    def test_istring_static_remove(self):
        """Test static remove method"""
        result = ip.IString.remove_static("o", "Hello World")
        self.assertEqual(result, "Hell Wrld")

    def test_istring_static_split(self):
        """Test static split method"""
        tokens = ip.IString.split(",", "one,two,three")
        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[0], "one")
        self.assertEqual(tokens[1], "two")
        self.assertEqual(tokens[2], "three")

    def test_istring_static_split_with_empty(self):
        """Test static split with empty entries"""
        tokens = ip.IString.split(",", "one,,three", True)
        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[0], "one")
        self.assertEqual(tokens[1], "")
        self.assertEqual(tokens[2], "three")

    def test_istring_static_split_without_empty(self):
        """Test static split without empty entries"""
        tokens = ip.IString.split(",", "one,,three", False)
        # Should skip empty entries
        self.assertTrue(len(tokens) <= 3)

    def test_istring_static_equal(self):
        """Test static equal method"""
        self.assertTrue(ip.IString.equal("hello", "hello"))
        self.assertFalse(ip.IString.equal("hello", "world"))

    def test_istring_equal(self):
        """Test instance equal method"""
        s = ip.IString("hello")
        self.assertTrue(s.equal("hello"))
        self.assertFalse(s.equal("world"))

    def test_istring_python_int_conversion(self):
        """Test Python __int__ conversion"""
        s = ip.IString("42")
        self.assertEqual(int(s), 42)

    def test_istring_python_float_conversion(self):
        """Test Python __float__ conversion"""
        s = ip.IString("3.14159")
        self.assertAlmostEqual(float(s), 3.14159, places=5)

    def test_istring_python_str_conversion(self):
        """Test Python __str__ conversion"""
        s = ip.IString("Hello")
        self.assertEqual(str(s), "Hello")

    def test_istring_python_repr(self):
        """Test Python __repr__"""
        s = ip.IString("Test")
        r = repr(s)
        self.assertIn("IString", r)
        self.assertIn("Test", r)

    def test_helper_to_bool(self):
        """Test standalone to_bool helper function"""
        self.assertTrue(ip.to_bool("true"))
        self.assertTrue(ip.to_bool("TRUE"))
        self.assertTrue(ip.to_bool("yes"))
        self.assertFalse(ip.to_bool("false"))
        self.assertFalse(ip.to_bool("FALSE"))
        self.assertFalse(ip.to_bool("no"))

    def test_helper_to_int(self):
        """Test standalone to_int helper function"""
        self.assertEqual(ip.to_int("42"), 42)
        self.assertEqual(ip.to_int("-123"), -123)

    def test_helper_to_double(self):
        """Test standalone to_double helper function"""
        self.assertAlmostEqual(ip.to_double("3.14159"), 3.14159, places=5)
        self.assertAlmostEqual(ip.to_double("-2.5"), -2.5, places=1)

    def test_helper_to_string_bool(self):
        """Test standalone to_string helper for bool"""
        # Note: to_string for bool returns QString converted to string
        result = ip.to_string(True)
        self.assertIsInstance(result, str)

    def test_helper_to_string_int(self):
        """Test standalone to_string helper for int"""
        result = ip.to_string(42)
        self.assertIsInstance(result, str)

    def test_helper_to_string_double(self):
        """Test standalone to_string helper for double"""
        result = ip.to_string(3.14159)
        self.assertIsInstance(result, str)
        self.assertIn("3.14159", result)

    def test_helper_to_string_double_with_precision(self):
        """Test standalone to_string helper for double with precision"""
        result = ip.to_string(3.14159, 2)
        self.assertIsInstance(result, str)


if __name__ == '__main__':
    unittest.main()
