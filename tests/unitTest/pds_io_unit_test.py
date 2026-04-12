"""
Unit tests for ISIS PDS table I/O bindings (ImportPdsTable, ExportPdsTable).

Author: Geng Xun
Created: 2026-04-10
Last Modified: 2026-04-10
Updated: 2026-04-10  Geng Xun initial binding and API tests for ImportPdsTable and ExportPdsTable.
Updated: 2026-04-12  Geng Xun added focused ExportPdsTable bytearray export coverage.
"""

import unittest

from _unit_test_support import ip


class ImportPdsTableApiTest(unittest.TestCase):
    """API tests for ImportPdsTable binding. Added: 2026-04-10."""

    def test_class_exists(self):
        """ImportPdsTable is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "ImportPdsTable"))

    def test_default_constructor(self):
        """ImportPdsTable can be constructed with no arguments."""
        t = ip.ImportPdsTable()
        self.assertIsNotNone(t)

    def test_has_expected_methods(self):
        """ImportPdsTable exposes the core API methods."""
        for method in ("load", "name", "set_name", "columns", "rows",
                       "has_column", "get_column_name", "get_column_names",
                       "get_type", "set_type", "import_table"):
            self.assertTrue(hasattr(ip.ImportPdsTable, method), f"Missing method: {method}")

    def test_default_state(self):
        """A newly constructed ImportPdsTable has 0 columns and 0 rows."""
        t = ip.ImportPdsTable()
        self.assertEqual(t.columns(), 0)
        self.assertEqual(t.rows(), 0)

    def test_repr(self):
        """ImportPdsTable __repr__ returns a non-empty string."""
        t = ip.ImportPdsTable()
        r = repr(t)
        self.assertIn("ImportPdsTable", r)


class ExportPdsTableApiTest(unittest.TestCase):
    """API tests for ExportPdsTable binding. Added: 2026-04-10."""

    def make_test_table(self):
        double_field = ip.TableField("DoubleValue", ip.TableField.Type.Double)
        integer_field = ip.TableField("IntegerValue", ip.TableField.Type.Integer)
        text_field = ip.TableField("TextValue", ip.TableField.Type.Text, 2)
        real_field = ip.TableField("RealValue", ip.TableField.Type.Real)

        record_template = ip.TableRecord()
        record_template.add_field(double_field)
        record_template.add_field(integer_field)
        record_template.add_field(text_field)
        record_template.add_field(real_field)

        table = ip.Table("TableToExport", record_template)

        first = ip.TableRecord()
        first_double = ip.TableField("DoubleValue", ip.TableField.Type.Double)
        first_double.set_value(3.14159)
        first_integer = ip.TableField("IntegerValue", ip.TableField.Type.Integer)
        first_integer.set_value(3)
        first_text = ip.TableField("TextValue", ip.TableField.Type.Text, 2)
        first_text.set_value("PI")
        first_real = ip.TableField("RealValue", ip.TableField.Type.Real)
        first_real.set_value(22.0 / 7.0)
        first.add_field(first_double)
        first.add_field(first_integer)
        first.add_field(first_text)
        first.add_field(first_real)

        second = ip.TableRecord()
        second_double = ip.TableField("DoubleValue", ip.TableField.Type.Double)
        second_double.set_value(2.71828)
        second_integer = ip.TableField("IntegerValue", ip.TableField.Type.Integer)
        second_integer.set_value(2)
        second_text = ip.TableField("TextValue", ip.TableField.Type.Text, 2)
        second_text.set_value("e")
        second_real = ip.TableField("RealValue", ip.TableField.Type.Real)
        second_real.set_value(2.5)
        second.add_field(second_double)
        second.add_field(second_integer)
        second.add_field(second_text)
        second.add_field(second_real)

        table.add_record(first)
        table.add_record(second)
        return table

    def test_class_exists(self):
        """ExportPdsTable is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "ExportPdsTable"))

    def test_has_expected_methods(self):
        """ExportPdsTable exposes format_pds_table_name and format_pds_table_name_from."""
        self.assertTrue(hasattr(ip.ExportPdsTable, "format_pds_table_name"))
        self.assertTrue(hasattr(ip.ExportPdsTable, "format_pds_table_name_from"))
        self.assertTrue(hasattr(ip.ExportPdsTable, "export_table"))

    def test_static_format_name(self):
        """format_pds_table_name_from converts ISIS table name to PDS format."""
        result = ip.ExportPdsTable.format_pds_table_name_from("SomeTable")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_export_table_fills_bytearray_and_returns_metadata(self):
        """export_table() writes binary bytes into a bytearray and returns PDS metadata."""
        table = self.make_test_table()
        exporter = ip.ExportPdsTable(table)
        record_bytes = table.record_size()
        raw = bytearray(record_bytes * len(table))

        metadata = exporter.export_table(raw, record_bytes, "LSB")

        self.assertIsInstance(metadata, ip.PvlObject)
        self.assertEqual(metadata.name(), "TABLE_TO_EXPORT_TABLE")
        self.assertEqual(metadata.find_keyword("ROWS")[0], "2")
        self.assertEqual(metadata.find_keyword("COLUMNS")[0], "4")
        self.assertEqual(len(raw), record_bytes * len(table))
        self.assertNotEqual(bytes(raw), b"\x00" * len(raw))


if __name__ == "__main__":
    unittest.main()
