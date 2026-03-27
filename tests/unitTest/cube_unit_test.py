"""
Unit tests for ISIS Cube binding class

Author: Geng Xun
Created: 2026-03-27
Last Modified: 2026-03-27
"""

import unittest

from _unit_test_support import ip, temporary_directory


def make_test_cube(temp_dir, name="test.cub", samples=8, lines=6, bands=2, pixel_type=None):
    """Helper: create a minimal cube in temp_dir and return it open for read/write."""
    if pixel_type is None:
        pixel_type = ip.PixelType.Real
    cube_path = temp_dir / name
    cube = ip.Cube()
    cube.set_dimensions(samples, lines, bands)
    cube.set_pixel_type(pixel_type)
    cube.create(str(cube_path))
    return cube, cube_path


class CubeConstructionTest(unittest.TestCase):
    """Test suite for Cube construction and initial state. Added: 2026-03-27."""

    def test_default_constructor(self):
        """Cube can be constructed without arguments."""
        cube = ip.Cube()
        self.assertIsNotNone(cube)

    def test_new_cube_is_not_open(self):
        """A freshly constructed Cube is not open."""
        cube = ip.Cube()
        self.assertFalse(cube.is_open())

    def test_format_enum_values_exist(self):
        """Cube.Format enum has Bsq and Tile values."""
        self.assertTrue(hasattr(ip.Cube.Format, "Bsq"))
        self.assertTrue(hasattr(ip.Cube.Format, "Tile"))

    def test_construct_from_filename(self):
        """Cube can be constructed from a FileName object pointing to a real file."""
        with temporary_directory() as temp_dir:
            cube_path = temp_dir / "from_filename.cub"
            # First create the file
            creator = ip.Cube()
            creator.set_dimensions(4, 4, 1)
            creator.create(str(cube_path))
            creator.close()

            # Now open via FileName constructor
            fname = ip.FileName(str(cube_path))
            cube = ip.Cube(fname, "r")
            self.assertTrue(cube.is_open())
            cube.close()


class CubeCreateCloseTest(unittest.TestCase):
    """Test suite for Cube create/close lifecycle. Added: 2026-03-27."""

    def test_create_makes_cube_open(self):
        """create() leaves the cube in open state."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            self.assertTrue(cube.is_open())

    def test_close_makes_cube_not_open(self):
        """close() transitions cube to closed state."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            cube.close()
            self.assertFalse(cube.is_open())

    def test_close_with_remove_deletes_file(self):
        """close(remove=True) deletes the underlying file."""
        import os
        with temporary_directory() as temp_dir:
            cube, cube_path = make_test_cube(temp_dir, name="removeme.cub")
            self.assertTrue(cube_path.exists())
            cube.close(remove=True)
            self.assertFalse(cube_path.exists())

    def test_create_newly_created_cube_is_read_write(self):
        """A cube opened via create() is read/write."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            self.assertTrue(cube.is_read_write())
            self.assertFalse(cube.is_read_only())


class CubeDimensionsTest(unittest.TestCase):
    """Test suite for Cube dimension accessors. Added: 2026-03-27."""

    def test_set_and_get_dimensions(self):
        """set_dimensions is reflected by sample_count, line_count, band_count."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir, samples=10, lines=7, bands=3)
            self.addCleanup(cube.close)
            self.assertEqual(cube.sample_count(), 10)
            self.assertEqual(cube.line_count(), 7)
            self.assertEqual(cube.band_count(), 3)

    def test_dimensions_are_positive_integers(self):
        """Dimension accessors return positive integers."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            self.assertIsInstance(cube.sample_count(), int)
            self.assertIsInstance(cube.line_count(), int)
            self.assertIsInstance(cube.band_count(), int)
            self.assertGreater(cube.sample_count(), 0)
            self.assertGreater(cube.line_count(), 0)
            self.assertGreater(cube.band_count(), 0)

    def test_single_band_cube(self):
        """Cube can be created with a single band."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir, samples=5, lines=5, bands=1)
            self.addCleanup(cube.close)
            self.assertEqual(cube.band_count(), 1)


class CubePixelTypeTest(unittest.TestCase):
    """Test suite for Cube pixel type. Added: 2026-03-27."""

    def test_real_pixel_type(self):
        """Cube created with Real pixel type reports Real."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir, pixel_type=ip.PixelType.Real)
            self.addCleanup(cube.close)
            self.assertEqual(cube.pixel_type(), ip.PixelType.Real)

    def test_signed_word_pixel_type(self):
        """Cube created with SignedWord pixel type reports SignedWord."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir, pixel_type=ip.PixelType.SignedWord)
            self.addCleanup(cube.close)
            self.assertEqual(cube.pixel_type(), ip.PixelType.SignedWord)

    def test_unsigned_byte_pixel_type(self):
        """Cube created with UnsignedByte pixel type reports UnsignedByte."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir, pixel_type=ip.PixelType.UnsignedByte)
            self.addCleanup(cube.close)
            self.assertEqual(cube.pixel_type(), ip.PixelType.UnsignedByte)


class CubeFormatTest(unittest.TestCase):
    """Test suite for Cube format (Bsq vs Tile). Added: 2026-03-27."""

    def test_default_format_is_bsq(self):
        """Cube created without explicit format defaults to Bsq."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            self.assertEqual(cube.format(), ip.Cube.Format.Bsq)

    def test_set_tile_format(self):
        """Cube can be created with Tile format."""
        with temporary_directory() as temp_dir:
            cube_path = temp_dir / "tile.cub"
            cube = ip.Cube()
            cube.set_dimensions(16, 16, 1)
            cube.set_pixel_type(ip.PixelType.Real)
            cube.set_format(ip.Cube.Format.Tile)
            cube.create(str(cube_path))
            self.addCleanup(cube.close)
            self.assertEqual(cube.format(), ip.Cube.Format.Tile)

    def test_set_bsq_format_explicitly(self):
        """Cube can be explicitly set to Bsq format."""
        with temporary_directory() as temp_dir:
            cube_path = temp_dir / "bsq.cub"
            cube = ip.Cube()
            cube.set_dimensions(8, 8, 1)
            cube.set_format(ip.Cube.Format.Bsq)
            cube.create(str(cube_path))
            self.addCleanup(cube.close)
            self.assertEqual(cube.format(), ip.Cube.Format.Bsq)


class CubeByteOrderTest(unittest.TestCase):
    """Test suite for Cube byte order. Added: 2026-03-27."""

    def test_set_lsb_byte_order(self):
        """Cube created with Lsb byte order reports Lsb."""
        with temporary_directory() as temp_dir:
            cube_path = temp_dir / "lsb.cub"
            cube = ip.Cube()
            cube.set_dimensions(4, 4, 1)
            cube.set_byte_order(ip.ByteOrder.Lsb)
            cube.create(str(cube_path))
            self.addCleanup(cube.close)
            self.assertEqual(cube.byte_order(), ip.ByteOrder.Lsb)

    def test_set_msb_byte_order(self):
        """Cube created with Msb byte order reports Msb."""
        with temporary_directory() as temp_dir:
            cube_path = temp_dir / "msb.cub"
            cube = ip.Cube()
            cube.set_dimensions(4, 4, 1)
            cube.set_byte_order(ip.ByteOrder.Msb)
            cube.create(str(cube_path))
            self.addCleanup(cube.close)
            self.assertEqual(cube.byte_order(), ip.ByteOrder.Msb)


class CubeAccessModeTest(unittest.TestCase):
    """Test suite for Cube open access modes. Added: 2026-03-27."""

    def _make_on_disk_cube(self, temp_dir, name="access_test.cub"):
        cube, cube_path = make_test_cube(temp_dir, name=name)
        cube.close()
        return cube_path

    def test_open_readonly(self):
        """open() with 'r' access makes cube read-only."""
        with temporary_directory() as temp_dir:
            cube_path = self._make_on_disk_cube(temp_dir)
            cube = ip.Cube()
            cube.open(str(cube_path), "r")
            self.addCleanup(cube.close)
            self.assertTrue(cube.is_open())
            self.assertTrue(cube.is_read_only())
            self.assertFalse(cube.is_read_write())

    def test_open_readwrite(self):
        """open() with 'rw' access makes cube read-write."""
        with temporary_directory() as temp_dir:
            cube_path = self._make_on_disk_cube(temp_dir)
            cube = ip.Cube()
            cube.open(str(cube_path), "rw")
            self.addCleanup(cube.close)
            self.assertTrue(cube.is_open())
            self.assertTrue(cube.is_read_write())
            self.assertFalse(cube.is_read_only())

    def test_open_default_is_readonly(self):
        """open() without explicit access defaults to read-only."""
        with temporary_directory() as temp_dir:
            cube_path = self._make_on_disk_cube(temp_dir)
            cube = ip.Cube()
            cube.open(str(cube_path))
            self.addCleanup(cube.close)
            self.assertTrue(cube.is_read_only())


class CubeReopenTest(unittest.TestCase):
    """Test suite for Cube reopen behavior. Added: 2026-03-27."""

    def test_reopen_from_readonly_to_readwrite(self):
        """reopen('rw') upgrades a read-only cube to read-write."""
        with temporary_directory() as temp_dir:
            cube_path = temp_dir / "reopen_test.cub"
            creator = ip.Cube()
            creator.set_dimensions(4, 4, 1)
            creator.create(str(cube_path))
            creator.close()

            cube = ip.Cube()
            cube.open(str(cube_path), "r")
            self.assertTrue(cube.is_read_only())
            cube.reopen("rw")
            self.addCleanup(cube.close)
            self.assertTrue(cube.is_read_write())

    def test_reopen_from_readwrite_to_readonly(self):
        """reopen('r') downgrades a read-write cube to read-only."""
        with temporary_directory() as temp_dir:
            cube_path = temp_dir / "reopen_rw_to_r.cub"
            cube = ip.Cube()
            cube.set_dimensions(4, 4, 1)
            cube.create(str(cube_path))
            self.assertTrue(cube.is_read_write())
            cube.reopen("r")
            self.addCleanup(cube.close)
            self.assertTrue(cube.is_read_only())


class CubeFileNameTest(unittest.TestCase):
    """Test suite for Cube file_name accessor. Added: 2026-03-27."""

    def test_file_name_matches_create_path(self):
        """file_name() returns a string matching the path given to create()."""
        with temporary_directory() as temp_dir:
            cube_path = temp_dir / "filename_check.cub"
            cube = ip.Cube()
            cube.set_dimensions(4, 4, 1)
            cube.create(str(cube_path))
            self.addCleanup(cube.close)
            fname = cube.file_name()
            self.assertIsInstance(fname, str)
            self.assertIn("filename_check.cub", fname)

    def test_file_name_after_open(self):
        """file_name() is available after open()."""
        with temporary_directory() as temp_dir:
            cube, cube_path = make_test_cube(temp_dir, name="fname_open.cub")
            cube.close()

            cube2 = ip.Cube()
            cube2.open(str(cube_path), "r")
            self.addCleanup(cube2.close)
            self.assertIn("fname_open.cub", cube2.file_name())


class CubeLabelTest(unittest.TestCase):
    """Test suite for Cube label, group accessors/mutators. Added: 2026-03-27."""

    def test_label_returns_pvl(self):
        """label() returns a Pvl object on an open cube."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            label = cube.label()
            self.assertIsInstance(label, ip.Pvl)

    def test_has_group_instrument_not_present(self):
        """has_group returns False for a group that was not added."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            self.assertFalse(cube.has_group("Instrument"))

    def test_put_group_and_has_group(self):
        """put_group adds a group visible via has_group."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            grp = ip.PvlGroup("TestGroup")
            grp.add_keyword(ip.PvlKeyword("Key", "Value"))
            cube.put_group(grp)
            self.assertTrue(cube.has_group("TestGroup"))

    def test_group_accessor_returns_pvl_group(self):
        """group() returns a PvlGroup after put_group."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            grp = ip.PvlGroup("MyGroup")
            grp.add_keyword(ip.PvlKeyword("Sensor", "Camera"))
            cube.put_group(grp)
            retrieved = cube.group("MyGroup")
            self.assertIsInstance(retrieved, ip.PvlGroup)

    def test_delete_group_removes_group(self):
        """delete_group removes a previously added group."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            grp = ip.PvlGroup("TempGroup")
            cube.put_group(grp)
            self.assertTrue(cube.has_group("TempGroup"))
            cube.delete_group("TempGroup")
            self.assertFalse(cube.has_group("TempGroup"))


class CubeBaseMultiplierTest(unittest.TestCase):
    """Test suite for Cube base/multiplier. Added: 2026-03-27."""

    def test_default_base_and_multiplier(self):
        """Newly created cube has default base=0.0 and multiplier=1.0."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            self.assertAlmostEqual(cube.base(), 0.0, places=10)
            self.assertAlmostEqual(cube.multiplier(), 1.0, places=10)

    def test_set_base_multiplier(self):
        """set_base_multiplier updates base and multiplier."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            cube.set_base_multiplier(10.5, 2.5)
            self.assertAlmostEqual(cube.base(), 10.5, places=10)
            self.assertAlmostEqual(cube.multiplier(), 2.5, places=10)

    def test_set_base_multiplier_zero_base(self):
        """set_base_multiplier with 0.0 base and non-trivial multiplier."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            cube.set_base_multiplier(0.0, 0.5)
            self.assertAlmostEqual(cube.base(), 0.0, places=10)
            self.assertAlmostEqual(cube.multiplier(), 0.5, places=10)


class CubeLabelSizeTest(unittest.TestCase):
    """Test suite for Cube label size and labels_attached. Added: 2026-03-27."""

    def test_label_size_positive_after_create(self):
        """label_size() returns a positive integer for a created cube."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            self.assertGreater(cube.label_size(), 0)

    def test_labels_attached_default_true(self):
        """Newly created cube has labels attached by default."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            self.assertTrue(cube.labels_attached())

    def test_set_labels_attached_false(self):
        """set_labels_attached(False) before create makes labels detached."""
        with temporary_directory() as temp_dir:
            cube_path = temp_dir / "detached.cub"
            cube = ip.Cube()
            cube.set_dimensions(4, 4, 1)
            cube.set_labels_attached(False)
            cube.create(str(cube_path))
            self.addCleanup(cube.close)
            self.assertFalse(cube.labels_attached())


class CubeStoresDnDataTest(unittest.TestCase):
    """Test suite for Cube.stores_dn_data(). Added: 2026-03-27."""

    def test_stores_dn_data_true_for_normal_cube(self):
        """A standard cube stores DN data."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            self.assertTrue(cube.stores_dn_data())


class CubePhysicalBandTest(unittest.TestCase):
    """Test suite for Cube.physical_band(). Added: 2026-03-27."""

    def test_physical_band_identity_single_band(self):
        """For a 1-band cube with no virtual band map, physical_band(1) == 1."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir, bands=1)
            self.addCleanup(cube.close)
            self.assertEqual(cube.physical_band(1), 1)

    def test_physical_band_identity_multi_band(self):
        """For a 3-band cube with no virtual band map, physical_band(n) == n."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir, bands=3)
            self.addCleanup(cube.close)
            self.assertEqual(cube.physical_band(1), 1)
            self.assertEqual(cube.physical_band(2), 2)
            self.assertEqual(cube.physical_band(3), 3)


class CubeIsProjectedTest(unittest.TestCase):
    """Test suite for Cube.is_projected(). Added: 2026-03-27."""

    def test_simple_cube_is_not_projected(self):
        """A newly created cube without mapping group is not projected."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            self.assertFalse(cube.is_projected())


class CubeBlobTableTest(unittest.TestCase):
    """Test suite for has_blob / has_table. Added: 2026-03-27."""

    def test_has_blob_false_for_new_cube(self):
        """A freshly created cube has no blobs."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            self.assertFalse(cube.has_blob("SomeBlob", "Table"))

    def test_has_table_false_for_new_cube(self):
        """A freshly created cube has no tables."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            self.assertFalse(cube.has_table("SomeTable"))


class CubeReadWriteTest(unittest.TestCase):
    """Test suite for Cube read/write with buffers. Added: 2026-03-27."""

    def test_write_and_read_line_manager(self):
        """Written data can be read back via LineManager."""
        with temporary_directory() as temp_dir:
            cube, cube_path = make_test_cube(temp_dir, samples=4, lines=3, bands=1)
            cube.close()

            cube = ip.Cube()
            cube.open(str(cube_path), "rw")
            self.addCleanup(cube.close)

            mgr = ip.LineManager(cube)
            mgr.set_line(1, 1)
            for i in range(len(mgr)):
                mgr[i] = float(i + 1)
            cube.write(mgr)

            mgr2 = ip.LineManager(cube)
            mgr2.set_line(1, 1)
            cube.read(mgr2)
            for i in range(len(mgr2)):
                self.assertAlmostEqual(mgr2[i], float(i + 1), places=5)

    def test_write_and_read_sample_manager(self):
        """Written data can be read back via SampleManager."""
        with temporary_directory() as temp_dir:
            cube, cube_path = make_test_cube(temp_dir, samples=3, lines=4, bands=1)
            cube.close()

            cube = ip.Cube()
            cube.open(str(cube_path), "rw")
            self.addCleanup(cube.close)

            mgr = ip.SampleManager(cube)
            mgr.set_sample(1, 1)
            for i in range(len(mgr)):
                mgr[i] = float(10 + i)
            cube.write(mgr)

            mgr2 = ip.SampleManager(cube)
            mgr2.set_sample(1, 1)
            cube.read(mgr2)
            for i in range(len(mgr2)):
                self.assertAlmostEqual(mgr2[i], float(10 + i), places=5)

    def test_fill_all_lines_and_verify(self):
        """All lines can be written and read back correctly."""
        with temporary_directory() as temp_dir:
            cube, cube_path = make_test_cube(temp_dir, samples=5, lines=3, bands=1)
            cube.close()

            cube = ip.Cube()
            cube.open(str(cube_path), "rw")
            self.addCleanup(cube.close)

            mgr = ip.LineManager(cube)
            line_num = 0
            mgr.begin()
            while not mgr.end():
                line_num += 1
                for i in range(len(mgr)):
                    mgr[i] = float(line_num * 10 + i)
                cube.write(mgr)
                mgr.next()

            mgr2 = ip.LineManager(cube)
            mgr2.set_line(2, 1)
            cube.read(mgr2)
            for i in range(len(mgr2)):
                self.assertAlmostEqual(mgr2[i], float(2 * 10 + i), places=5)


class CubeStatisticsTest(unittest.TestCase):
    """Test suite for Cube.statistics(). Added: 2026-03-27."""

    def _make_filled_cube(self, temp_dir, value=5.0, samples=4, lines=4, bands=1):
        cube_path = temp_dir / "stats_test.cub"
        cube = ip.Cube()
        cube.set_dimensions(samples, lines, bands)
        cube.set_pixel_type(ip.PixelType.Real)
        cube.create(str(cube_path))
        mgr = ip.LineManager(cube)
        mgr.begin()
        while not mgr.end():
            for i in range(len(mgr)):
                mgr[i] = value
            cube.write(mgr)
            mgr.next()
        cube.close()
        return cube_path

    def test_statistics_returns_statistics_object(self):
        """statistics() returns a Statistics object."""
        with temporary_directory() as temp_dir:
            cube_path = self._make_filled_cube(temp_dir, value=3.0)
            cube = ip.Cube()
            cube.open(str(cube_path), "r")
            self.addCleanup(cube.close)
            stats = cube.statistics()
            self.assertIsNotNone(stats)

    def test_statistics_minimum_maximum(self):
        """statistics() min and max reflect filled constant pixel value."""
        with temporary_directory() as temp_dir:
            cube_path = self._make_filled_cube(temp_dir, value=7.0)
            cube = ip.Cube()
            cube.open(str(cube_path), "r")
            self.addCleanup(cube.close)
            stats = cube.statistics()
            self.assertAlmostEqual(stats.minimum(), 7.0, places=5)
            self.assertAlmostEqual(stats.maximum(), 7.0, places=5)

    def test_statistics_with_band_argument(self):
        """statistics(band=1) works for a single-band cube."""
        with temporary_directory() as temp_dir:
            cube_path = self._make_filled_cube(temp_dir, value=2.0)
            cube = ip.Cube()
            cube.open(str(cube_path), "r")
            self.addCleanup(cube.close)
            stats = cube.statistics(band=1)
            self.assertAlmostEqual(stats.minimum(), 2.0, places=5)

    def test_statistics_with_valid_range(self):
        """statistics(band, valid_min, valid_max) filters pixel values."""
        with temporary_directory() as temp_dir:
            cube_path = self._make_filled_cube(temp_dir, value=5.0)
            cube = ip.Cube()
            cube.open(str(cube_path), "r")
            self.addCleanup(cube.close)
            stats = cube.statistics(1, 1.0, 10.0)
            self.assertIsNotNone(stats)
            self.assertAlmostEqual(stats.minimum(), 5.0, places=5)


class CubeHistogramTest(unittest.TestCase):
    """Test suite for Cube.histogram(). Added: 2026-03-27."""

    def _make_filled_cube(self, temp_dir, value=4.0, samples=4, lines=4, bands=1):
        cube_path = temp_dir / "hist_test.cub"
        cube = ip.Cube()
        cube.set_dimensions(samples, lines, bands)
        cube.set_pixel_type(ip.PixelType.Real)
        cube.create(str(cube_path))
        mgr = ip.LineManager(cube)
        mgr.begin()
        while not mgr.end():
            for i in range(len(mgr)):
                mgr[i] = value
            cube.write(mgr)
            mgr.next()
        cube.close()
        return cube_path

    def test_histogram_returns_histogram_object(self):
        """histogram() returns a Histogram object."""
        with temporary_directory() as temp_dir:
            cube_path = self._make_filled_cube(temp_dir, value=4.0)
            cube = ip.Cube()
            cube.open(str(cube_path), "r")
            self.addCleanup(cube.close)
            hist = cube.histogram()
            self.assertIsNotNone(hist)

    def test_histogram_with_band_argument(self):
        """histogram(band=1) works for a single-band cube."""
        with temporary_directory() as temp_dir:
            cube_path = self._make_filled_cube(temp_dir, value=4.0)
            cube = ip.Cube()
            cube.open(str(cube_path), "r")
            self.addCleanup(cube.close)
            hist = cube.histogram(band=1)
            self.assertIsNotNone(hist)

    def test_histogram_with_valid_range(self):
        """histogram(band, valid_min, valid_max) works with value in range."""
        with temporary_directory() as temp_dir:
            cube_path = self._make_filled_cube(temp_dir, value=4.0)
            cube = ip.Cube()
            cube.open(str(cube_path), "r")
            self.addCleanup(cube.close)
            hist = cube.histogram(1, 0.0, 10.0)
            self.assertIsNotNone(hist)

    def test_histogram_minimum_maximum(self):
        """histogram() min and max reflect filled pixel value."""
        with temporary_directory() as temp_dir:
            cube_path = self._make_filled_cube(temp_dir, value=6.0)
            cube = ip.Cube()
            cube.open(str(cube_path), "r")
            self.addCleanup(cube.close)
            hist = cube.histogram()
            self.assertAlmostEqual(hist.minimum(), 6.0, places=4)
            self.assertAlmostEqual(hist.maximum(), 6.0, places=4)


class CubeClearIoCacheTest(unittest.TestCase):
    """Test suite for Cube.clear_io_cache(). Added: 2026-03-27."""

    def test_clear_io_cache_does_not_raise(self):
        """clear_io_cache() completes without raising an exception."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            # Should complete without error
            cube.clear_io_cache()


class CubeSetMinMaxTest(unittest.TestCase):
    """Test suite for Cube.set_min_max(). Added: 2026-03-27."""

    def test_set_min_max_does_not_raise(self):
        """set_min_max() completes without raising an exception."""
        with temporary_directory() as temp_dir:
            cube, _ = make_test_cube(temp_dir)
            self.addCleanup(cube.close)
            cube.set_min_max(0.0, 255.0)


class CubeMultiBandTest(unittest.TestCase):
    """Integration tests exercising multi-band cubes. Added: 2026-03-27."""

    def test_multi_band_write_and_read(self):
        """Each band of a 3-band cube holds independent written values."""
        with temporary_directory() as temp_dir:
            cube, cube_path = make_test_cube(
                temp_dir, samples=4, lines=4, bands=3, pixel_type=ip.PixelType.Real
            )
            band_values = [1.0, 2.0, 3.0]
            for band_idx, fill_value in enumerate(band_values, start=1):
                mgr = ip.BandManager(cube)
                mgr.set_band(1, band_idx)
                for i in range(len(mgr)):
                    mgr[i] = fill_value
                cube.write(mgr)
            cube.close()

            cube2 = ip.Cube()
            cube2.open(str(cube_path), "r")
            self.addCleanup(cube2.close)
            self.assertEqual(cube2.band_count(), 3)
            for band_idx, expected in enumerate(band_values, start=1):
                stats = cube2.statistics(band=band_idx)
                self.assertAlmostEqual(stats.minimum(), expected, places=5)
                self.assertAlmostEqual(stats.maximum(), expected, places=5)


if __name__ == "__main__":
    unittest.main()
