"""
Unit tests for ISIS utility classes: Column, Environment, LineEquation

Author: Geng Xun
Created: 2026-03-24
Last Modified: 2026-04-09
Updated: 2026-04-09  Geng Xun added Message namespace regression coverage for standardized ISIS text templates.
Updated: 2026-04-09  Geng Xun added CollectorMap focused coverage for unique and duplicate key policies.
Updated: 2026-04-08  Geng Xun added Environment regression coverage alongside existing Column and LineEquation helpers.
"""
import os
import tempfile
import unittest
from unittest import mock

from _unit_test_support import ip


class CollectorMapUnitTest(unittest.TestCase):
    """Focused tests for the Python-facing CollectorMap specialization."""

    def test_default_constructor_uses_unique_keys(self):
        collector = ip.CollectorMap()
        collector.add(1, "One")
        collector.add(1, "Uno")

        self.assertEqual(len(collector), 1)
        self.assertEqual(collector.count(1), 1)
        self.assertEqual(collector.get(1), "Uno")
        self.assertEqual(collector.index(1), 0)

    def test_duplicate_key_policy_preserves_multiple_values(self):
        collector = ip.CollectorMap(ip.CollectorMap.KeyPolicy.DuplicateKeys)
        collector.add(1, "One")
        collector.add(1, "One #2")
        collector.add(2, "Two")

        self.assertEqual(len(collector), 3)
        self.assertEqual(collector.count(1), 2)
        self.assertEqual(collector.get(1), "One")
        self.assertEqual(collector.get_nth(1), "One #2")
        self.assertEqual(collector.key(2), 2)

    def test_exists_contains_and_remove_follow_current_contents(self):
        collector = ip.CollectorMap(ip.CollectorMap.KeyPolicy.DuplicateKeys)
        collector.add(4, "Four")
        collector.add(4, "Four #2")

        self.assertTrue(collector.exists(4))
        self.assertIn(4, collector)
        self.assertEqual(collector.remove(4), 2)
        self.assertFalse(collector.exists(4))
        self.assertEqual(collector.index(4), -1)

    def test_copy_constructor_preserves_entries(self):
        collector = ip.CollectorMap(ip.CollectorMap.KeyPolicy.DuplicateKeys)
        collector.add(7, "Seven")
        collector.add(8, "Eight")

        copied = ip.CollectorMap(collector)
        self.assertEqual(copied.items(), [(7, "Seven"), (8, "Eight")])
        self.assertEqual(repr(copied), "CollectorMap(size=2)")

    def test_missing_key_and_out_of_range_raise_iexception(self):
        collector = ip.CollectorMap()

        with self.assertRaises(ip.IException):
            collector.get(5)

        with self.assertRaises(ip.IException):
            collector.get_nth(0)

        with self.assertRaises(ip.IException):
            collector.key(0)

    def test_iteration_returns_key_value_pairs_in_order(self):
        collector = ip.CollectorMap(ip.CollectorMap.KeyPolicy.DuplicateKeys)
        collector.add(1, "One")
        collector.add(1, "One #2")
        collector.add(3, "Three")

        self.assertEqual(list(collector), [(1, "One"), (1, "One #2"), (3, "Three")])
        self.assertEqual(collector.items(), [(1, "One"), (1, "One #2"), (3, "Three")])


class MessageUnitTest(unittest.TestCase):
    """Regression tests for the Message namespace bindings."""

    def test_keyword_and_array_messages_match_upstream_templates(self):
        self.assertEqual(
            ip.Message.ArraySubscriptNotInRange(100000),
            "Array subscript [100000] is out of array bounds",
        )
        self.assertEqual(ip.Message.KeywordAmbiguous("KEY"), "Keyword [KEY] ambiguous")
        self.assertEqual(ip.Message.KeywordUnrecognized("KEY"), "Keyword [KEY] unrecognized")
        self.assertEqual(ip.Message.KeywordDuplicated("KEY"), "Keyword [KEY] duplicated")
        self.assertEqual(ip.Message.KeywordNotArray("KEY"), "Keyword [KEY] is not an array")
        self.assertEqual(
            ip.Message.KeywordNotFound("KEY"),
            "Keyword [KEY] required but was not found",
        )

    def test_block_and_value_messages_preserve_truncation_behavior(self):
        self.assertEqual(
            ip.Message.KeywordBlockInvalid("BLOCK"),
            "Keyword block [BLOCK] is invalid",
        )
        self.assertEqual(
            ip.Message.KeywordBlockStartMissing("BLOCK", "FOUND"),
            "Expecting start of keyword block [BLOCK] but found [FOUND]",
        )
        self.assertEqual(
            ip.Message.KeywordBlockEndMissing("BLOCK", "FOUND"),
            "Expecting end of keyword block [BLOCK] but found [FOUND]",
        )
        self.assertEqual(ip.Message.KeywordValueBad("KEY"), "Keyword [KEY] has bad value")
        self.assertEqual(
            ip.Message.KeywordValueBad("KEY", "abcdefghijklmnopqrstuvwxyz"),
            "Keyword [KEY] has bad value [abcdefghijklmnopqrst ...]",
        )
        self.assertEqual(
            ip.Message.KeywordValueExpected("KEY"),
            "Keyword value for [KEY] expected but was not found",
        )

    def test_range_list_delimiter_and_file_messages(self):
        self.assertEqual(
            ip.Message.KeywordValueNotInRange("KEY", "0", "(0,20]"),
            "Keyword [KEY=0] is not in the range of (0,20]",
        )
        self.assertEqual(
            ip.Message.KeywordValueNotInList("KEY", "A", ["X", "Y", "Z"]),
            "Keyword [KEY=A] must be one of [X,Y,Z]",
        )
        self.assertEqual(ip.Message.MissingDelimiter(")"), "Missing delimiter [)]")
        self.assertEqual(
            ip.Message.MissingDelimiter(")", "abcdefghijklmnopqrstuvwxyz"),
            "Missing delimiter [)] at or near [abcdefghijklmnopqrst ...]",
        )
        self.assertEqual(ip.Message.FileOpen("test.dat"), "Unable to open [test.dat]")
        self.assertEqual(ip.Message.FileCreate("test.dat"), "Unable to create [test.dat]")
        self.assertEqual(ip.Message.FileRead("test.dat"), "Unable to read [test.dat]")
        self.assertEqual(ip.Message.FileWrite("test.dat"), "Unable to write [test.dat]")
        self.assertEqual(
            ip.Message.MemoryAllocationFailed(),
            "Unable to allocate dynamic memory",
        )


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


class EnvironmentUnitTest(unittest.TestCase):
    """Test suite for Environment static utility bindings."""

    def test_get_environment_value_returns_set_value(self):
        with mock.patch.dict(os.environ, {"PYISIS_TEST_ENV_VALUE": "bound-value"}, clear=False):
            self.assertEqual(
                ip.Environment.get_environment_value("PYISIS_TEST_ENV_VALUE", "fallback"),
                "bound-value",
            )

    def test_get_environment_value_uses_default_for_missing_key(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PYISIS_TEST_ENV_MISSING", None)
            self.assertEqual(
                ip.Environment.get_environment_value("PYISIS_TEST_ENV_MISSING", "fallback"),
                "fallback",
            )

    def test_user_name_and_host_name_follow_environment(self):
        with mock.patch.dict(
            os.environ,
            {
                "USER": "environment-unit-user",
                "HOST": "environment-unit-host",
            },
            clear=False,
        ):
            self.assertEqual(ip.Environment.user_name(), "environment-unit-user")
            self.assertEqual(ip.Environment.host_name(), "environment-unit-host")

    def test_isis_version_reads_from_mock_isisroot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            version_path = os.path.join(temp_dir, "isis_version.txt")
            with open(version_path, "w", encoding="utf-8") as version_file:
                version_file.write("isis9.0.0 # comment\n")
                version_file.write("2026-04-08\n")
                version_file.write("unused line\n")
                version_file.write("beta\n")

            with mock.patch.dict(os.environ, {"ISISROOT": temp_dir}, clear=False):
                self.assertEqual(ip.Environment.isis_version(), "isis9.0.0 beta | 2026-04-08")


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
