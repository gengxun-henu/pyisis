"""
Unit tests for ISIS Cube bindings

Author: Geng Xun
Created: 2026-03-27
Last Modified: 2026-03-29
"""

import unittest

from _unit_test_support import (
    close_cube_quietly,
    ip,
    make_closed_test_cube,
    make_filled_cube,
    make_test_cube,
    open_cube,
    temporary_directory,
)


class CubeConstructionAndLifecycleTest(unittest.TestCase):
    """Regression coverage for construction, create/open/close, and access modes."""

    def test_default_constructor_starts_closed(self):
        cube = ip.Cube()
        self.assertFalse(cube.is_open())

    def test_format_enum_values_exist(self):
        self.assertTrue(hasattr(ip.Cube.Format, "Bsq"))
        self.assertTrue(hasattr(ip.Cube.Format, "Tile"))

    def test_construct_from_filename_opens_existing_cube(self):
        with temporary_directory() as temp_dir:
            cube_path = make_closed_test_cube(temp_dir, name="from_filename.cub", samples=4, lines=4, bands=1)
            file_name = ip.FileName(str(cube_path))
            cube = ip.Cube(file_name, "r")
            self.addCleanup(close_cube_quietly, cube)
            self.assertTrue(cube.is_open())
            self.assertTrue(cube.is_read_only())

    def test_create_close_and_reopen_access_modes(self):
        with temporary_directory() as temp_dir:
            cube, cube_path = make_test_cube(temp_dir, name="lifecycle.cub", samples=10, lines=7, bands=3)
            self.addCleanup(close_cube_quietly, cube)

            self.assertTrue(cube.is_open())
            self.assertTrue(cube.is_read_write())
            self.assertEqual(cube.sample_count(), 10)
            self.assertEqual(cube.line_count(), 7)
            self.assertEqual(cube.band_count(), 3)

            cube.close()
            self.assertFalse(cube.is_open())

            reopened = open_cube(cube_path)
            self.addCleanup(close_cube_quietly, reopened)
            self.assertTrue(reopened.is_open())
            self.assertTrue(reopened.is_read_only())
            self.assertFalse(reopened.is_read_write())

    def test_reopen_switches_between_readonly_and_readwrite(self):
        with temporary_directory() as temp_dir:
            cube_path = make_closed_test_cube(temp_dir, name="reopen.cub", samples=4, lines=4, bands=1)
            cube = open_cube(cube_path, "r")
            self.addCleanup(close_cube_quietly, cube)

            self.assertTrue(cube.is_read_only())
            cube.reopen("rw")
            self.assertTrue(cube.is_read_write())
            cube.reopen("r")
            self.assertTrue(cube.is_read_only())

    def test_reopen_without_open_raises(self):
        cube = ip.Cube()
        with self.assertRaises(ip.IException):
            cube.reopen("rw")

    def test_close_with_remove_deletes_cube_file(self):
        with temporary_directory() as temp_dir:
            cube, cube_path = make_test_cube(temp_dir, name="remove_me.cub")
            self.assertTrue(cube_path.exists())
            cube.close(remove=True)
            self.assertFalse(cube.is_open())
            self.assertFalse(cube_path.exists())

    def test_precreate_configuration_round_trip(self):
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(
                temp_dir,
                name="configured.cub",
                samples=6,
                lines=5,
                bands=2,
                pixel_type=ip.PixelType.SignedWord,
                cube_format=ip.Cube.Format.Tile,
                byte_order=ip.ByteOrder.Msb,
                base_multiplier=(10.5, 2.5),
            )
            self.addCleanup(close_cube_quietly, cube)

            self.assertEqual(cube.pixel_type(), ip.PixelType.SignedWord)
            self.assertEqual(cube.format(), ip.Cube.Format.Tile)
            self.assertEqual(cube.byte_order(), ip.ByteOrder.Msb)
            self.assertAlmostEqual(cube.base(), 10.5, places=10)
            self.assertAlmostEqual(cube.multiplier(), 2.5, places=10)

    def test_detached_labels_configuration_sets_precreate_flag(self):
        cube = ip.Cube()
        cube.set_labels_attached(False)

        self.assertFalse(cube.labels_attached())


class CubeMetadataAndLabelTest(unittest.TestCase):
    """Behavioral tests for Cube metadata, labels, and group helpers."""

    def test_file_name_matches_create_path_for_attached_cube(self):
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir, name="filename_check.cub")
            self.addCleanup(close_cube_quietly, cube)

            self.assertIsInstance(cube.file_name(), str)
            self.assertTrue(cube.file_name().endswith("filename_check.cub"))

    def test_label_returns_pvl_and_group_round_trip(self):
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir, name="label_group.cub")
            self.addCleanup(close_cube_quietly, cube)

            label = cube.label()
            self.assertIsInstance(label, ip.Pvl)
            self.assertFalse(cube.has_group("TestGroup"))

            group = ip.PvlGroup("TestGroup")
            group.add_keyword(ip.PvlKeyword("Key", "Value"))
            cube.put_group(group)

            self.assertTrue(cube.has_group("TestGroup"))
            self.assertIsInstance(cube.group("TestGroup"), ip.PvlGroup)

            cube.delete_group("TestGroup")
            self.assertFalse(cube.has_group("TestGroup"))

    def test_put_group_on_read_only_cube_raises(self):
        with temporary_directory() as temp_dir:
            cube_path = make_closed_test_cube(temp_dir, name="readonly_group.cub")
            cube = open_cube(cube_path, "r")
            self.addCleanup(close_cube_quietly, cube)

            with self.assertRaises(ip.IException):
                cube.put_group(ip.PvlGroup("ShouldFail"))

    def test_default_blob_table_projection_flags(self):
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir, name="default_flags.cub")
            self.addCleanup(close_cube_quietly, cube)

            self.assertFalse(cube.is_projected())
            self.assertFalse(cube.has_blob("MissingBlob", "Table"))
            self.assertFalse(cube.has_table("MissingTable"))

    def test_physical_band_identity_and_dn_storage(self):
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir, name="bands.cub", bands=3)
            self.addCleanup(close_cube_quietly, cube)

            self.assertTrue(cube.stores_dn_data())
            self.assertEqual(cube.physical_band(1), 1)
            self.assertEqual(cube.physical_band(2), 2)
            self.assertEqual(cube.physical_band(3), 3)


class CubeIoAndManagersTest(unittest.TestCase):
    """Round-trip tests for low-level Cube IO helpers and managers."""

    def test_line_manager_write_and_read_round_trip(self):
        with temporary_directory() as temp_dir:
            cube_path = make_closed_test_cube(temp_dir, name="line_rw.cub", samples=4, lines=3, bands=1)
            cube = open_cube(cube_path, "rw")
            self.addCleanup(close_cube_quietly, cube)

            writer = ip.LineManager(cube)
            writer.set_line(2, 1)
            expected = [20.0, 21.0, 22.0, 23.0]
            for index, value in enumerate(expected):
                writer[index] = value
            cube.write(writer)

            reader = ip.LineManager(cube)
            reader.set_line(2, 1)
            cube.read(reader)

            self.assertEqual([reader[index] for index in range(len(reader))], expected)

    def test_sample_manager_write_and_read_round_trip(self):
        with temporary_directory() as temp_dir:
            cube_path = make_closed_test_cube(temp_dir, name="sample_rw.cub", samples=3, lines=4, bands=1)
            cube = open_cube(cube_path, "rw")
            self.addCleanup(close_cube_quietly, cube)

            writer = ip.SampleManager(cube)
            writer.set_sample(2, 1)
            expected = [11.0, 12.0, 13.0, 14.0]
            for index, value in enumerate(expected):
                writer[index] = value
            cube.write(writer)

            reader = ip.SampleManager(cube)
            reader.set_sample(2, 1)
            cube.read(reader)

            self.assertEqual([reader[index] for index in range(len(reader))], expected)

    def test_multiband_statistics_reflect_band_specific_writes(self):
        with temporary_directory() as temp_dir:
            cube, cube_path = make_test_cube(
                temp_dir,
                name="multiband.cub",
                samples=4,
                lines=3,
                bands=3,
                pixel_type=ip.PixelType.Real,
            )

            band_values = [1.0, 2.0, 3.0]
            for band_index, fill_value in enumerate(band_values, start=1):
                manager = ip.LineManager(cube)
                for line_index in range(1, cube.line_count() + 1):
                    manager.set_line(line_index, band_index)
                    for sample_index in range(len(manager)):
                        manager[sample_index] = fill_value
                    cube.write(manager)

            cube.close()

            reopened = open_cube(cube_path, "r")
            self.addCleanup(close_cube_quietly, reopened)

            for band_index, expected in enumerate(band_values, start=1):
                stats = reopened.statistics(band=band_index)
                self.assertAlmostEqual(stats.minimum(), expected, places=5)
                self.assertAlmostEqual(stats.maximum(), expected, places=5)

    def test_clear_io_cache_does_not_raise(self):
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir, name="cache.cub")
            self.addCleanup(close_cube_quietly, cube)
            cube.clear_io_cache()


class CubeStatisticsAndHistogramTest(unittest.TestCase):
    """Focused coverage for statistics/histogram behavior and failure modes."""

    def test_statistics_constant_cube_minimum_and_maximum(self):
        with temporary_directory() as temp_dir:
            cube_path = make_filled_cube(temp_dir, name="stats.cub", value=7.0, samples=4, lines=4, bands=1)
            cube = open_cube(cube_path, "r")
            self.addCleanup(close_cube_quietly, cube)

            stats = cube.statistics()
            self.assertAlmostEqual(stats.minimum(), 7.0, places=5)
            self.assertAlmostEqual(stats.maximum(), 7.0, places=5)

    def test_histogram_constant_cube_minimum_and_maximum(self):
        with temporary_directory() as temp_dir:
            cube_path = make_filled_cube(temp_dir, name="hist.cub", value=6.0, samples=4, lines=4, bands=1)
            cube = open_cube(cube_path, "r")
            self.addCleanup(close_cube_quietly, cube)

            histogram = cube.histogram()
            self.assertAlmostEqual(histogram.minimum(), 6.0, places=5)
            self.assertAlmostEqual(histogram.maximum(), 6.0, places=5)

    def test_statistics_invalid_band_raises(self):
        with temporary_directory() as temp_dir:
            cube_path = make_filled_cube(temp_dir, name="stats_invalid_band.cub", value=2.0, bands=1)
            cube = open_cube(cube_path, "r")
            self.addCleanup(close_cube_quietly, cube)

            with self.assertRaises(ip.IException):
                cube.statistics(band=2)

    def test_histogram_invalid_band_raises(self):
        with temporary_directory() as temp_dir:
            cube_path = make_filled_cube(temp_dir, name="hist_invalid_band.cub", value=2.0, bands=1)
            cube = open_cube(cube_path, "r")
            self.addCleanup(close_cube_quietly, cube)

            with self.assertRaises(ip.IException):
                cube.histogram(band=2)


class CubeFailureModeTest(unittest.TestCase):
    """Negative tests for lifecycle misuse and unopened/read-only behavior."""

    def test_is_read_only_on_unopened_cube_raises(self):
        cube = ip.Cube()
        with self.assertRaises(ip.IException):
            cube.is_read_only()

    def test_read_and_write_on_unopened_cube_raise(self):
        cube = ip.Cube()
        buffer = ip.Buffer(4, 1, 1, ip.PixelType.Real)

        with self.assertRaises(ip.IException):
            cube.read(buffer)

        with self.assertRaises(ip.IException):
            cube.write(buffer)

    def test_statistics_and_histogram_on_unopened_cube_raise(self):
        cube = ip.Cube()

        with self.assertRaises(ip.IException):
            cube.statistics()

        with self.assertRaises(ip.IException):
            cube.histogram()

    def test_write_on_read_only_cube_raises(self):
        with temporary_directory() as temp_dir:
            cube_path = make_filled_cube(temp_dir, name="readonly_write.cub", value=3.0, samples=4, lines=3, bands=1)
            cube = open_cube(cube_path, "r")
            self.addCleanup(close_cube_quietly, cube)

            line = ip.LineManager(cube)
            line.set_line(1, 1)
            with self.assertRaises(ip.IException):
                cube.write(line)

    def test_invalid_dimensions_raise(self):
        cube = ip.Cube()
        with self.assertRaises(ip.IException):
            cube.set_dimensions(0, 4, 1)

    def test_set_base_multiplier_after_create_raises(self):
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(
                temp_dir,
                name="after_open_base.cub",
                pixel_type=ip.PixelType.SignedWord,
            )
            self.addCleanup(close_cube_quietly, cube)

            with self.assertRaises(ip.IException):
                cube.set_base_multiplier(10.5, 2.5)

    def test_set_min_max_after_create_raises(self):
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(
                temp_dir,
                name="after_open_minmax.cub",
                pixel_type=ip.PixelType.UnsignedByte,
            )
            self.addCleanup(close_cube_quietly, cube)

            with self.assertRaises(ip.IException):
                cube.set_min_max(0.0, 255.0)


if __name__ == "__main__":
    unittest.main()
