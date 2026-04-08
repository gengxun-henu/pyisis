"""
Unit tests for ISIS support utility bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-03-21
"""

import unittest

from _unit_test_support import temporary_text_file, ip


class FileNameAndITimeUnitTest(unittest.TestCase):
    def _make_itime_or_skip(self, value):
        try:
            return ip.iTime(value)
        except ip.IException as error:
            if "Unable to load leadsecond file" in str(error):
                self.skipTest("iTime requires leap second kernel data in the runtime environment")
            raise

    def test_filename_parses_components_and_versions(self):
        file_name = ip.FileName("/tmp/example.cub")
        self.assertEqual(file_name.path(), "/tmp")
        self.assertEqual(file_name.name(), "example.cub")
        self.assertEqual(file_name.base_name(), "example")
        self.assertEqual(file_name.extension(), "cub")
        self.assertFalse(file_name.is_versioned())

    def test_filename_extension_operations_return_expected_names(self):
        file_name = ip.FileName("report.txt")

        self.assertEqual(file_name.remove_extension().name(), "report")
        self.assertEqual(file_name.set_extension("csv").name(), "report.csv")
        self.assertEqual(file_name.add_extension("bak").name(), "report.txt.bak")
        self.assertIn("FileName(", repr(file_name))
        self.assertEqual(str(file_name), file_name.to_string())

    def test_filename_file_exists_matches_real_file(self):
        with temporary_text_file("exists.lbl", "Object = Test\nEndObject\nEnd\n") as file_path:
            file_name = ip.FileName(str(file_path))
            self.assertTrue(file_name.file_exists())
            self.assertEqual(file_name.original(), str(file_path))

    def test_itime_string_constructor_and_accessors(self):
        time_value = self._make_itime_or_skip("2001-01-02T03:04:05")
        self.assertEqual(time_value.year(), 2001)
        self.assertEqual(time_value.month(), 1)
        self.assertEqual(time_value.day(), 2)
        self.assertEqual(time_value.hour(), 3)
        self.assertEqual(time_value.minute(), 4)
        self.assertAlmostEqual(time_value.second(), 5.0, places=6)
        self.assertEqual(time_value.day_of_year(), 2)
        self.assertIn("2001-01-02", time_value.utc())

    def test_itime_setters_update_both_utc_and_et_views(self):
        time_value = self._make_itime_or_skip(0.0)
        original_et = time_value.et()
        time_value.set_utc("2005-05-06T07:08:09")
        self.assertNotEqual(time_value.et(), original_et)
        self.assertEqual(time_value.year(), 2005)
        self.assertEqual(time_value.month(), 5)
        self.assertEqual(time_value.day(), 6)

        time_value.set_et(12345.0)
        self.assertAlmostEqual(time_value.et(), 12345.0, places=6)
        self.assertIn("iTime(", repr(time_value))


if __name__ == "__main__":
    unittest.main()