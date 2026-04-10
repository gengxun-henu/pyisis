"""
Unit tests for ISIS utility classes: Column, Environment, IString, LineEquation

Author: Geng Xun
Created: 2026-03-24
Last Modified: 2026-04-09
Updated: 2026-04-09  Geng Xun added Message namespace regression coverage for standardized ISIS text templates.
Updated: 2026-04-09  Geng Xun added CollectorMap focused coverage for unique and duplicate key policies.
Updated: 2026-04-09  Geng Xun added Plugin focused coverage for runtime plugin address resolution and failure paths.
Updated: 2026-04-08  Geng Xun added Environment regression coverage alongside existing Column and LineEquation helpers.
Updated: 2026-04-09  Geng Xun added IString and free-function helpers (to_bool/to_int/to_double/to_string) unit tests.
Updated: 2026-04-10  Geng Xun added Pixel, ID, EndianSwapper, and TextFile focused unit tests.
Updated: 2026-04-10  Geng Xun aligned ID overflow expectations with upstream placeholder-width semantics.
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


class PluginUnitTest(unittest.TestCase):
    """Focused tests for the Plugin runtime loader wrapper."""

    def make_plugin(self, library="IdealCamera", routine="IdealCameraPlugin", group="TestPlugin"):
        plugin = ip.Plugin()
        plugin_group = ip.PvlGroup(group)
        plugin_group.add_keyword(ip.PvlKeyword("Library", library))
        plugin_group.add_keyword(ip.PvlKeyword("Routine", routine))
        plugin.add_group(plugin_group)
        return plugin

    def test_get_plugin_returns_nonzero_function_address(self):
        os.environ.setdefault("ISISROOT", os.environ.get("CONDA_PREFIX", ""))

        plugin = self.make_plugin()
        self.assertEqual(plugin.groups(), 1)
        address = plugin.get_plugin("TestPlugin")

        self.assertIsInstance(address, int)
        self.assertGreater(address, 0)
        self.assertIn("Plugin(groups=1)", repr(plugin))

    def test_get_plugin_raises_for_missing_symbol(self):
        os.environ.setdefault("ISISROOT", os.environ.get("CONDA_PREFIX", ""))

        plugin = self.make_plugin(routine="DefinitelyMissingPluginRoutine")

        with self.assertRaises(ip.IException) as context:
            plugin.get_plugin("TestPlugin")

        self.assertIn("Unable to find plugin", str(context.exception))


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


class IStringUnitTest(unittest.TestCase):
    """Focused unit tests for IString binding and free-function helpers.

    Added: 2026-04-09
    """

    # ------------------------------------------------------------------
    # Free-function helpers
    # ------------------------------------------------------------------

    def test_to_bool_true_values(self):
        """to_bool recognises common truthy strings (case-insensitive)."""
        for val in ("true", "True", "TRUE", "yes", "Yes", "on", "On", "1", "t", "y"):
            self.assertTrue(ip.to_bool(val), f"Expected True for {val!r}")

    def test_to_bool_false_values(self):
        """to_bool recognises common falsy strings (case-insensitive)."""
        for val in ("false", "False", "no", "No", "off", "Off", "0", "f", "n"):
            self.assertFalse(ip.to_bool(val), f"Expected False for {val!r}")

    def test_to_bool_invalid_raises(self):
        """to_bool raises on an unrecognised string."""
        with self.assertRaises(Exception):
            ip.to_bool("maybe")

    def test_to_int_valid(self):
        """to_int converts numeric strings correctly."""
        self.assertEqual(ip.to_int("0"), 0)
        self.assertEqual(ip.to_int("42"), 42)
        self.assertEqual(ip.to_int("-7"), -7)

    def test_to_int_invalid_raises(self):
        """to_int raises on a non-integer string."""
        with self.assertRaises(Exception):
            ip.to_int("abc")

    def test_to_big_int_valid(self):
        """to_big_int converts large integer strings correctly."""
        self.assertEqual(ip.to_big_int("9223372036854775807"), 9223372036854775807)
        self.assertEqual(ip.to_big_int("-9223372036854775807"), -9223372036854775807)

    def test_to_double_valid(self):
        """to_double converts floating-point strings correctly."""
        self.assertAlmostEqual(ip.to_double("3.14"), 3.14, places=10)
        self.assertAlmostEqual(ip.to_double("-1e10"), -1e10)

    def test_to_double_invalid_raises(self):
        """to_double raises on a non-numeric string."""
        with self.assertRaises(Exception):
            ip.to_double("hello")

    def test_to_string_bool(self):
        """to_string(bool) returns 'Yes' or 'No' matching ISIS convention."""
        self.assertIsInstance(ip.to_string(True), str)
        self.assertIsInstance(ip.to_string(False), str)

    def test_to_string_int(self):
        """to_string(int) returns numeric string."""
        self.assertEqual(ip.to_string(42), "42")
        self.assertEqual(ip.to_string(-7), "-7")

    def test_to_string_double(self):
        """to_string(double) returns numeric string at default precision."""
        result = ip.to_string(3.14)
        self.assertIn("3.14", result)

    def test_to_string_double_precision(self):
        """to_string(double, precision) honours the precision argument."""
        result = ip.to_string(3.141592653589793, 5)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    # ------------------------------------------------------------------
    # IString constructors
    # ------------------------------------------------------------------

    def test_construct_default(self):
        """IString() constructs an empty string."""
        s = ip.IString()
        self.assertEqual(str(s), "")

    def test_construct_from_str(self):
        """IString(str) stores the value."""
        s = ip.IString("hello world")
        self.assertEqual(str(s), "hello world")

    def test_construct_copy(self):
        """IString copy constructor works."""
        s1 = ip.IString("copy test")
        s2 = ip.IString(s1)
        self.assertEqual(str(s2), "copy test")

    def test_construct_from_int(self):
        """IString(int) converts the integer to its string representation."""
        s = ip.IString(42)
        self.assertEqual(int(s), 42)

    def test_construct_from_double(self):
        """IString(double) converts the float to its string representation."""
        s = ip.IString(3.14)
        self.assertAlmostEqual(float(s), 3.14, places=5)

    # ------------------------------------------------------------------
    # Instance methods
    # ------------------------------------------------------------------

    def test_trim(self):
        """trim() removes leading/trailing characters from the given set."""
        s = ip.IString("ABCDefghijkBCAD")
        result = s.trim("ABCD")
        self.assertEqual(result, "efghijk")

    def test_trim_head(self):
        """trim_head() removes only leading characters from the given set."""
        s = ip.IString("ABCDefghijk")
        result = s.trim_head("DCBA")
        self.assertEqual(result, "efghijk")

    def test_trim_tail(self):
        """trim_tail() removes only trailing characters from the given set."""
        s = ip.IString("efghijkBCAD")
        result = s.trim_tail("DCBA")
        self.assertEqual(result, "efghijk")

    def test_up_case(self):
        """up_case() converts the string to uppercase."""
        s = ip.IString("hello")
        result = s.up_case()
        self.assertEqual(result, "HELLO")

    def test_down_case(self):
        """down_case() converts the string to lowercase."""
        s = ip.IString("HELLO")
        result = s.down_case()
        self.assertEqual(result, "hello")

    def test_to_integer(self):
        """to_integer() converts numeric string to int."""
        s = ip.IString("123")
        self.assertEqual(s.to_integer(), 123)

    def test_to_double_method(self):
        """to_double() converts numeric string to float."""
        s = ip.IString("9.5")
        self.assertAlmostEqual(s.to_double(), 9.5)

    def test_to_big_integer(self):
        """to_big_integer() converts large numeric string to int."""
        s = ip.IString("1000000000")
        self.assertEqual(s.to_big_integer(), 1000000000)

    def test_token(self):
        """token() extracts tokens one at a time."""
        s = ip.IString("25:255 35")
        tok1 = s.token(": ")
        self.assertEqual(tok1, "25")
        tok2 = s.token(": ")
        self.assertEqual(tok2, "255")

    def test_split_static(self):
        """split() splits a string on a separator character."""
        tokens = ip.IString.split(' ', "This is a test")
        self.assertEqual(tokens, ["This", "is", "a", "test"])

    def test_compress(self):
        """compress() collapses consecutive whitespace to single spaces."""
        s = ip.IString("  AB  CD  ")
        result = s.compress()
        self.assertEqual(result.strip(), "AB CD")

    def test_replace(self):
        """replace() substitutes occurrences of a substring."""
        s = ip.IString("Thirteen is bigger than fourteen")
        result = s.replace("bigger", "smaller")
        self.assertIn("smaller", result)
        self.assertNotIn("bigger", result)

    def test_remove(self):
        """remove() strips all occurrences of the given characters."""
        s = ip.IString("a 1 b 2 c 3 d 4")
        result = s.remove("1245")
        self.assertNotIn("1", result)
        self.assertNotIn("2", result)
        self.assertNotIn("4", result)
        self.assertNotIn("5", result)

    def test_convert_whitespace(self):
        """convert_whitespace() replaces tab/newline with space."""
        s = ip.IString("a\tb\nc")
        result = s.convert_whitespace()
        self.assertNotIn("\t", result)
        self.assertNotIn("\n", result)

    def test_equal(self):
        """equal() performs case-insensitive string comparison."""
        s = ip.IString("Hello")
        self.assertTrue(s.equal("Hello"))
        self.assertTrue(s.equal("hello"))
        self.assertFalse(s.equal("World"))

    # ------------------------------------------------------------------
    # Static methods
    # ------------------------------------------------------------------

    def test_trim_static(self):
        """trim_static() removes chars from both ends of a str."""
        result = ip.IString.trim_static("ABCD", "ABCDefghijkBCAD")
        self.assertEqual(result, "efghijk")

    def test_up_case_static(self):
        """up_case_static() returns uppercase copy of a str."""
        self.assertEqual(ip.IString.up_case_static("hello"), "HELLO")

    def test_down_case_static(self):
        """down_case_static() returns lowercase copy of a str."""
        self.assertEqual(ip.IString.down_case_static("HELLO"), "hello")

    def test_to_integer_static(self):
        """to_integer_static() converts str to int."""
        self.assertEqual(ip.IString.to_integer_static("99"), 99)

    # ------------------------------------------------------------------
    # Python protocol methods
    # ------------------------------------------------------------------

    def test_str(self):
        """str(IString) returns the string content."""
        s = ip.IString("test value")
        self.assertEqual(str(s), "test value")

    def test_repr(self):
        """repr(IString) includes IString and the string content."""
        s = ip.IString("abc")
        self.assertIn("IString", repr(s))
        self.assertIn("abc", repr(s))

    def test_len(self):
        """len(IString) returns the character count."""
        s = ip.IString("hello")
        self.assertEqual(len(s), 5)

    def test_int_conversion(self):
        """int(IString) calls to_integer()."""
        s = ip.IString("77")
        self.assertEqual(int(s), 77)

    def test_float_conversion(self):
        """float(IString) calls to_double()."""
        s = ip.IString("2.5")
        self.assertAlmostEqual(float(s), 2.5)

    def test_equality_operator(self):
        """IString == str works correctly."""
        s = ip.IString("hello")
        self.assertTrue(s == "hello")
        self.assertFalse(s == "world")


class PixelUnitTest(unittest.TestCase):
    """Focused unit tests for the Pixel class binding. Added: 2026-04-10."""

    def test_default_constructor(self):
        """Default Pixel has zero coordinates and NULL DN."""
        p = ip.Pixel()
        self.assertIsInstance(p, ip.Pixel)
        self.assertEqual(p.line(), 0)
        self.assertEqual(p.sample(), 0)
        self.assertEqual(p.band(), 0)

    def test_explicit_constructor(self):
        """Pixel(sample, line, band, dn) stores correct values."""
        p = ip.Pixel(3, 7, 2, 12.5)
        self.assertEqual(p.sample(), 3)
        self.assertEqual(p.line(), 7)
        self.assertEqual(p.band(), 2)
        self.assertAlmostEqual(p.dn(), 12.5)

    def test_repr(self):
        """repr(Pixel) includes class name and coordinates."""
        p = ip.Pixel(1, 2, 1, 5.0)
        r = repr(p)
        self.assertIn("Pixel", r)
        self.assertIn("sample=1", r)
        self.assertIn("line=2", r)

    def test_is_valid_normal_dn(self):
        """Normal DN is valid and not special."""
        p = ip.Pixel(1, 1, 1, 100.0)
        self.assertTrue(p.is_valid())
        self.assertFalse(p.is_special())

    def test_static_is_valid(self):
        """Static is_valid_value / is_special_value work on raw double."""
        self.assertTrue(ip.Pixel.is_valid_value(50.0))
        self.assertFalse(ip.Pixel.is_special_value(50.0))

    def test_default_pixel_is_null(self):
        """Default Pixel (DN=NULL) reports is_null() and is_special()."""
        p = ip.Pixel()
        self.assertTrue(p.is_null())
        self.assertTrue(p.is_special())
        self.assertFalse(p.is_valid())

    def test_to_string_instance(self):
        """to_string() returns a non-empty string for a valid DN."""
        p = ip.Pixel(1, 1, 1, 42.0)
        s = p.to_string()
        self.assertIsInstance(s, str)
        self.assertGreater(len(s), 0)

    def test_static_to_string(self):
        """Static to_string_value() works on a raw double."""
        s = ip.Pixel.to_string_value(42.0)
        self.assertIsInstance(s, str)
        self.assertGreater(len(s), 0)

    def test_to_float_instance(self):
        """to_float() on an instance returns a float."""
        p = ip.Pixel(1, 1, 1, 7.5)
        self.assertAlmostEqual(p.to_float(), 7.5, places=3)

    def test_to_double_instance(self):
        """to_double() on an instance returns the DN."""
        p = ip.Pixel(1, 1, 1, 3.14)
        self.assertAlmostEqual(p.to_double(), 3.14)


class IDUnitTest(unittest.TestCase):
    """Focused unit tests for the ID class binding. Added: 2026-04-10."""

    def test_default_start(self):
        """ID with '???' format starts at 1 and increments."""
        id_gen = ip.ID("img???")
        first = id_gen.next()
        self.assertIn("1", first)

    def test_sequential_ids(self):
        """next() returns sequentially numbered IDs."""
        id_gen = ip.ID("item??", 10)
        first = id_gen.next()
        second = id_gen.next()
        self.assertIn("10", first)
        self.assertIn("11", second)

    def test_custom_base(self):
        """ID starts at the specified base number."""
        id_gen = ip.ID("obj?????", 100)
        result = id_gen.next()
        self.assertIn("100", result)

    def test_no_placeholder_raises(self):
        """ID constructor raises when the template has no '?' placeholder."""
        with self.assertRaises(Exception):
            ip.ID("noquestion")

    def test_repr(self):
        """repr(ID) includes 'ID'."""
        id_gen = ip.ID("x?")
        r = repr(id_gen)
        self.assertIn("ID", r)


class EndianSwapperUnitTest(unittest.TestCase):
    """Focused unit tests for the EndianSwapper class binding. Added: 2026-04-10."""

    def test_construction_lsb(self):
        """EndianSwapper('LSB') constructs without error."""
        es = ip.EndianSwapper("LSB")
        self.assertIsInstance(es, ip.EndianSwapper)

    def test_construction_msb(self):
        """EndianSwapper('MSB') constructs without error."""
        es = ip.EndianSwapper("MSB")
        self.assertIsInstance(es, ip.EndianSwapper)

    def test_will_swap_bool(self):
        """will_swap() returns a boolean."""
        es = ip.EndianSwapper("LSB")
        self.assertIsInstance(es.will_swap(), bool)

    def test_repr(self):
        """repr(EndianSwapper) includes class name."""
        es = ip.EndianSwapper("LSB")
        r = repr(es)
        self.assertIn("EndianSwapper", r)

    def test_swap_double_native(self):
        """swap_double with native-endian bytes returns the correct value."""
        import struct
        import sys
        native = '<d' if sys.byteorder == 'little' else '>d'
        value = 3.14159
        buf = struct.pack(native, value)
        # LSB swapper on an LSB machine: no swap should occur, value is preserved
        es = ip.EndianSwapper("LSB")
        result = es.swap_double(buf)
        self.assertIsInstance(result, float)
        if sys.byteorder == 'little':
            # Native machine is LSB; LSB swapper should NOT swap, preserving value
            self.assertAlmostEqual(result, value, places=5)

    def test_swap_double_cross_endian(self):
        """swap_double on a MSB swapper correctly reverses LSB-encoded bytes."""
        import struct
        import sys
        if sys.byteorder != 'little':
            self.skipTest("Cross-endian test only runs on little-endian machines")
        value = 1.0
        # Pack as big-endian
        buf = struct.pack('>d', value)
        # MSB swapper on LSB machine: should swap bytes to recover little-endian 1.0
        es = ip.EndianSwapper("MSB")
        result = es.swap_double(buf)
        self.assertIsInstance(result, float)
        self.assertAlmostEqual(result, value, places=10)

    def test_swap_short_roundtrip(self):
        """swap_short on a native 2-byte buffer returns the correct integer."""
        import struct
        import sys
        native = '<h' if sys.byteorder == 'little' else '>h'
        buf = struct.pack(native, 42)
        es = ip.EndianSwapper("LSB")
        result = es.swap_short(buf)
        self.assertIsInstance(result, int)
        if sys.byteorder == 'little':
            # LSB swapper on LSB machine: no swap, value preserved
            self.assertEqual(result, 42)

    def test_swap_double_too_small_raises(self):
        """swap_double with insufficient buffer raises ValueError."""
        es = ip.EndianSwapper("LSB")
        with self.assertRaises((ValueError, Exception)):
            es.swap_double(b'\x00\x01')


class TextFileUnitTest(unittest.TestCase):
    """Focused unit tests for the TextFile class binding. Added: 2026-04-10."""

    def setUp(self):
        """Create a temporary file for tests."""
        self.tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False)
        self.tmp.write("line one\nline two\n# comment\nline three\n")
        self.tmp.close()
        self.tmp_path = self.tmp.name

    def tearDown(self):
        """Remove temporary file."""
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_default_constructor(self):
        """Default TextFile constructs without error."""
        tf = ip.TextFile()
        self.assertIsInstance(tf, ip.TextFile)

    def test_open_and_close(self):
        """TextFile can open a file and close it."""
        tf = ip.TextFile()
        tf.open(self.tmp_path, "input")
        self.assertTrue(tf.open_chk())
        tf.close()

    def test_constructor_with_filename(self):
        """Constructor with filename opens the file immediately."""
        tf = ip.TextFile(self.tmp_path, "input")
        self.assertTrue(tf.open_chk())
        tf.close()

    def test_get_file_all_lines(self):
        """get_file() returns all non-comment lines."""
        tf = ip.TextFile(self.tmp_path, "input")
        lines = tf.get_file(skip_comments=True)
        tf.close()
        self.assertIsInstance(lines, list)
        self.assertGreater(len(lines), 0)
        for l in lines:
            self.assertFalse(l.startswith("#"))

    def test_get_file_no_skip_comments(self):
        """get_file(skip_comments=False) includes comment lines."""
        tf = ip.TextFile(self.tmp_path, "input")
        lines = tf.get_file(skip_comments=False)
        tf.close()
        comment_lines = [l for l in lines if l.startswith("#")]
        self.assertGreater(len(comment_lines), 0)

    def test_get_line(self):
        """get_line() returns lines one at a time, None at EOF."""
        tf = ip.TextFile(self.tmp_path, "input")
        first = tf.get_line(skip_comments=True)
        self.assertIsNotNone(first)
        self.assertIsInstance(first, str)
        tf.close()

    def test_line_count(self):
        """line_count() returns a positive integer."""
        tf = ip.TextFile(self.tmp_path, "input")
        count = tf.line_count()
        tf.close()
        self.assertGreater(count, 0)

    def test_size(self):
        """size() returns a positive byte count."""
        tf = ip.TextFile(self.tmp_path, "input")
        sz = tf.size()
        tf.close()
        self.assertGreater(sz, 0)

    def test_write_and_read_back(self):
        """put_line / get_line round-trip through a temporary file."""
        out_tmp = tempfile.NamedTemporaryFile(
            suffix='.txt', delete=False)
        out_tmp.close()
        out_path = out_tmp.name
        try:
            tf_out = ip.TextFile(out_path, "output")
            tf_out.put_line("hello world")
            tf_out.put_line("second line")
            tf_out.close()

            tf_in = ip.TextFile(out_path, "input")
            first = tf_in.get_line(skip_comments=True)
            tf_in.close()
            self.assertIsNotNone(first)
            self.assertIn("hello world", first)
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    def test_repr(self):
        """repr(TextFile) includes class name."""
        tf = ip.TextFile()
        r = repr(tf)
        self.assertIn("TextFile", r)


if __name__ == '__main__':
    unittest.main()
