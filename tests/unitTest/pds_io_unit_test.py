"""
Unit tests for ISIS PDS table I/O bindings (ImportPdsTable, ExportPdsTable).

Author: Geng Xun
Created: 2026-04-10
Last Modified: 2026-04-10
Updated: 2026-04-10  Geng Xun initial binding and API tests for ImportPdsTable and ExportPdsTable.
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

    def test_class_exists(self):
        """ExportPdsTable is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "ExportPdsTable"))

    def test_has_expected_methods(self):
        """ExportPdsTable exposes format_pds_table_name and format_pds_table_name_from."""
        self.assertTrue(hasattr(ip.ExportPdsTable, "format_pds_table_name"))
        self.assertTrue(hasattr(ip.ExportPdsTable, "format_pds_table_name_from"))

    def test_static_format_name(self):
        """format_pds_table_name_from converts ISIS table name to PDS format."""
        result = ip.ExportPdsTable.format_pds_table_name_from("SomeTable")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)


if __name__ == "__main__":
    unittest.main()
