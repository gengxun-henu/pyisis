"""
Unit tests for ISIS support utility bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-05-03
Updated: 2026-04-09  Geng Xun added focused FileList regression coverage for file and string based list parsing.
Updated: 2026-05-03  Geng Xun added IException static helper coverage.
"""

import unittest
from pathlib import Path
import sys

try:
    from _unit_test_support import temporary_directory, temporary_text_file, ip
except ModuleNotFoundError:
    unit_test_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(unit_test_dir))
    from _unit_test_support import temporary_directory, temporary_text_file, ip


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


class FileListUnitTest(unittest.TestCase):
    def test_filelist_reads_list_file_and_preserves_first_column_rules(self):
        with temporary_directory() as temp_dir:
            list_path = temp_dir / "inputs.lis"
            list_path.write_text(
                """
# ignore me
   // ignore me too
alpha.cub trailing columns
beta.cub,ignored_attribute
"gamma,file.cub"
""".lstrip(),
                encoding="utf-8",
            )

            file_list = ip.FileList(ip.FileName(str(list_path)))

            self.assertEqual(len(file_list), 3)
            self.assertEqual(file_list[0].to_string(), "alpha.cub")
            self.assertEqual(file_list[1].to_string(), "beta.cub")
            self.assertEqual(file_list[2].to_string(), "gamma,file.cub")
            self.assertIn("FileList(size=3)", repr(file_list))

    def test_filelist_read_from_string_and_write_round_trip(self):
        file_list = ip.FileList()
        file_list.read_from_string("delta.cub\nepsilon.cub extra\n")

        self.assertFalse(file_list.empty())
        self.assertEqual(file_list.size(), 2)
        self.assertEqual(file_list.to_string(), "delta.cub\nepsilon.cub\n")

        with temporary_directory() as temp_dir:
            output_path = temp_dir / "outputs.lis"
            file_list.write(str(output_path))
            self.assertEqual(output_path.read_text(encoding="utf-8"), "delta.cub\nepsilon.cub\n")

    def test_filelist_append_supports_python_friendly_population(self):
        file_list = ip.FileList()
        file_list.append("one.cub")
        file_list.append(ip.FileName("two.cub"))

        self.assertEqual(len(file_list), 2)
        self.assertEqual(file_list[0].name(), "one.cub")
        self.assertEqual(file_list[1].name(), "two.cub")

    def test_filelist_raises_on_empty_stream_and_missing_file(self):
        file_list = ip.FileList()

        with self.assertRaises(ip.IException) as empty_error:
            file_list.read_from_string("\n")
        self.assertIn("Input Stream Empty", str(empty_error.exception))

        with self.assertRaises(ip.IException) as missing_error:
            file_list.read("/definitely/not/present/filelist.lis")
        self.assertIn("Unable to open", str(missing_error.exception))


class IExceptionUnitTest(unittest.TestCase):
    def test_error_type_to_string_returns_upstream_messages(self):
        self.assertEqual(ip.IException.error_type_to_string(ip.IExceptionErrorType.Unknown), "ERROR")
        self.assertEqual(ip.IException.error_type_to_string(ip.IExceptionErrorType.User), "USER ERROR")
        self.assertEqual(
            ip.IException.error_type_to_string(ip.IExceptionErrorType.Programmer),
            "PROGRAMMER ERROR",
        )
        self.assertEqual(ip.IException.error_type_to_string(ip.IExceptionErrorType.Io), "I/O ERROR")


if __name__ == "__main__":
    unittest.main()
