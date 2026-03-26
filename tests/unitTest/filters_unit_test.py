#!/usr/bin/env python3
# Copyright (c) 2026 Geng Xun, Henan University
# SPDX-License-Identifier: MIT

"""
Unit tests for ISIS filter and utility class bindings.

Author: Geng Xun
Created: 2026-03-25
Last Modified: 2026-03-26
"""

import os
import tempfile
import unittest

from _unit_test_support import ip


Stretch = ip.Stretch
CubeStretch = ip.CubeStretch
GaussianStretch = ip.GaussianStretch
QuickFilter = ip.QuickFilter
Kernels = ip.Kernels
CSVReader = ip.CSVReader
Pvl = ip.Pvl
PvlGroup = ip.PvlGroup
PvlKeyword = ip.PvlKeyword
Histogram = ip.Histogram


class TestStretch(unittest.TestCase):
    """Test cases for Stretch class"""

    def test_construction(self):
        """Test Stretch object construction"""
        stretch = Stretch()
        self.assertIsInstance(stretch, Stretch)
        self.assertEqual(stretch.pairs(), 0)

    def test_add_pair(self):
        """Test adding input-output pairs"""
        stretch = Stretch()
        stretch.add_pair(0.0, 0.0)
        stretch.add_pair(100.0, 255.0)
        self.assertEqual(stretch.pairs(), 2)

    def test_input_output(self):
        """Test retrieving input and output values"""
        stretch = Stretch()
        stretch.add_pair(0.0, 0.0)
        stretch.add_pair(100.0, 255.0)
        self.assertEqual(stretch.input(0), 0.0)
        self.assertEqual(stretch.output(0), 0.0)
        self.assertEqual(stretch.input(1), 100.0)
        self.assertEqual(stretch.output(1), 255.0)

    def test_map(self):
        """Test mapping values through stretch"""
        stretch = Stretch()
        stretch.add_pair(0.0, 0.0)
        stretch.add_pair(100.0, 255.0)
        # Test mapping (linear interpolation between pairs)
        result = stretch.map(50.0)
        self.assertIsInstance(result, float)

    def test_clear_pairs(self):
        """Test clearing stretch pairs"""
        stretch = Stretch()
        stretch.add_pair(0.0, 0.0)
        stretch.add_pair(100.0, 255.0)
        stretch.clear_pairs()
        self.assertEqual(stretch.pairs(), 0)

    def test_set_special_pixels(self):
        """Test setting special pixel values"""
        stretch = Stretch()
        stretch.set_null(0.0)
        stretch.set_lis(1.0)
        stretch.set_lrs(2.0)
        stretch.set_his(254.0)
        stretch.set_hrs(255.0)
        # No errors should occur

    def test_set_min_max(self):
        """Test setting minimum and maximum values"""
        stretch = Stretch()
        stretch.set_minimum(0.0)
        stretch.set_maximum(100.0)
        # No errors should occur

    def test_repr(self):
        """Test string representation"""
        stretch = Stretch()
        stretch.add_pair(0.0, 0.0)
        repr_str = repr(stretch)
        self.assertIn("Stretch", repr_str)
        self.assertIn("pairs=", repr_str)

    def test_parse_simple(self):
        """Test parsing stretch pairs from a string"""
        stretch = Stretch()
        # Parse a simple stretch string with two pairs
        stretch.parse("0:0 100:255")
        self.assertEqual(stretch.pairs(), 2)
        # Verify the pairs were parsed correctly
        self.assertEqual(stretch.input(0), 0.0)
        self.assertEqual(stretch.output(0), 0.0)
        self.assertEqual(stretch.input(1), 100.0)
        self.assertEqual(stretch.output(1), 255.0)

    def test_parse_with_histogram(self):
        """Test parsing stretch pairs with histogram reference"""
        hist = Histogram(0.0, 100.0, 256)
        # Add some data to the histogram
        for i in range(100):
            hist.add_data(float(i))

        stretch = Stretch()
        # Parse with histogram (tests the fixed lambda wrapper)
        stretch.parse("0:0 100:255", hist)
        self.assertEqual(stretch.pairs(), 2)


class TestGaussianStretch(unittest.TestCase):
    """Test cases for GaussianStretch class"""

    def test_construction(self):
        """Test GaussianStretch object construction"""
        # GaussianStretch requires a Histogram object
        hist = Histogram(0.0, 100.0, 256)
        # Add some data to the histogram
        hist.add_data(50.0)
        stretch = GaussianStretch(hist)
        self.assertIsInstance(stretch, GaussianStretch)

    def test_map(self):
        """Test mapping values through Gaussian stretch"""
        # GaussianStretch requires a Histogram object
        hist = Histogram(0.0, 100.0, 256)
        # Add some data to the histogram
        hist.add_data(50.0)
        stretch = GaussianStretch(hist)
        result = stretch.map(50.0)
        self.assertIsInstance(result, float)

    def test_repr(self):
        """Test string representation"""
        # GaussianStretch requires a Histogram object
        hist = Histogram(0.0, 100.0, 256)
        # Add some data to the histogram
        hist.add_data(50.0)
        stretch = GaussianStretch(hist)
        repr_str = repr(stretch)
        self.assertIn("GaussianStretch", repr_str)


class TestCubeStretch(unittest.TestCase):
    """Test cases for CubeStretch class. Added: 2026-03-26."""

    def test_construction_defaults(self):
        """Test CubeStretch default construction metadata."""
        stretch = CubeStretch()
        self.assertIsInstance(stretch, CubeStretch)
        self.assertEqual(stretch.get_name(), "DefaultStretch")
        self.assertEqual(stretch.get_type(), "Default")
        self.assertEqual(stretch.get_band_number(), 1)
        self.assertEqual(stretch.pairs(), 0)

    def test_construction_with_metadata(self):
        """Test CubeStretch construction with explicit metadata."""
        stretch = CubeStretch("PreviewStretch", "Manual", 3)
        self.assertEqual(stretch.get_name(), "PreviewStretch")
        self.assertEqual(stretch.get_type(), "Manual")
        self.assertEqual(stretch.get_band_number(), 3)

    def test_construct_from_stretch(self):
        """Test CubeStretch construction from Stretch preserves pairs."""
        base = Stretch()
        base.add_pair(0.0, 0.0)
        base.add_pair(100.0, 255.0)

        stretch = CubeStretch(base, "Linear")
        self.assertEqual(stretch.get_type(), "Linear")
        self.assertEqual(stretch.pairs(), 2)
        self.assertEqual(stretch.input(0), 0.0)
        self.assertEqual(stretch.output(1), 255.0)

    def test_setters_and_equality(self):
        """Test CubeStretch metadata mutation and equality."""
        left = CubeStretch("A", "Manual", 1)
        left.add_pair(0.0, 0.0)
        left.add_pair(10.0, 20.0)

        right = CubeStretch(left)
        self.assertTrue(left == right)

        right.set_name("B")
        right.set_type("Binary")
        right.set_band_number(2)

        self.assertEqual(right.get_name(), "B")
        self.assertEqual(right.get_type(), "Binary")
        self.assertEqual(right.get_band_number(), 2)
        self.assertFalse(left == right)

    def test_repr(self):
        """Test CubeStretch string representation."""
        stretch = CubeStretch("DisplayStretch", "Linear", 2)
        stretch.add_pair(0.0, 0.0)
        repr_str = repr(stretch)
        self.assertIn("CubeStretch", repr_str)
        self.assertIn("DisplayStretch", repr_str)
        self.assertIn("Linear", repr_str)
        self.assertIn("band_number=2", repr_str)


class TestQuickFilter(unittest.TestCase):
    """Test cases for QuickFilter class"""

    def test_construction(self):
        """Test QuickFilter object construction"""
        # QuickFilter requires ns, width, height parameters
        qfilter = QuickFilter(100, 5, 5)
        self.assertIsInstance(qfilter, QuickFilter)

    def test_dimensions(self):
        """Test getting filter dimensions"""
        qfilter = QuickFilter(100, 5, 5)
        # Check dimensions match constructor parameters
        self.assertEqual(qfilter.width(), 5)
        self.assertEqual(qfilter.height(), 5)
        self.assertEqual(qfilter.samples(), 100)
        self.assertIsInstance(qfilter.half_width(), int)
        self.assertIsInstance(qfilter.half_height(), int)

    def test_set_min_max(self):
        """Test setting min/max valid data range"""
        qfilter = QuickFilter(100, 5, 5)
        qfilter.set_min_max(0.0, 255.0)
        self.assertEqual(qfilter.low(), 0.0)
        self.assertEqual(qfilter.high(), 255.0)

    def test_set_minimum_pixels(self):
        """Test setting minimum pixel count"""
        qfilter = QuickFilter(100, 5, 5)
        qfilter.set_minimum_pixels(5)
        self.assertEqual(qfilter.minimum_pixels(), 5)

    def test_reset(self):
        """Test resetting filter state"""
        qfilter = QuickFilter(100, 5, 5)
        qfilter.reset()
        # Should not raise any errors

    def test_repr(self):
        """Test string representation"""
        qfilter = QuickFilter(100, 5, 5)
        repr_str = repr(qfilter)
        self.assertIn("QuickFilter", repr_str)

    def test_validation_ns_positive(self):
        """Test that ns must be positive"""
        with self.assertRaises(ValueError) as context:
            QuickFilter(0, 5, 5)
        self.assertIn("ns must be positive", str(context.exception))

        with self.assertRaises(ValueError) as context:
            QuickFilter(-1, 5, 5)
        self.assertIn("ns must be positive", str(context.exception))

    def test_validation_width_height_odd(self):
        """Test that width and height must be odd numbers"""
        with self.assertRaises(ValueError) as context:
            QuickFilter(100, 4, 5)  # Even width
        self.assertIn("width and height must be odd", str(context.exception))

        with self.assertRaises(ValueError) as context:
            QuickFilter(100, 5, 4)  # Even height
        self.assertIn("width and height must be odd", str(context.exception))

        with self.assertRaises(ValueError) as context:
            QuickFilter(100, 6, 6)  # Both even
        self.assertIn("width and height must be odd", str(context.exception))

    def test_validation_width_height_positive(self):
        """Test that width and height must be positive"""
        with self.assertRaises(ValueError) as context:
            QuickFilter(100, -3, 5)  # Negative width (but odd)
        self.assertIn("width and height must be positive", str(context.exception))

        with self.assertRaises(ValueError) as context:
            QuickFilter(100, 5, -3)  # Negative height (but odd)
        self.assertIn("width and height must be positive", str(context.exception))


class TestKernels(unittest.TestCase):
    """Test cases for Kernels class"""

    def test_construction(self):
        """Test Kernels object construction"""
        kernels = Kernels()
        self.assertIsInstance(kernels, Kernels)

    def test_size(self):
        """Test getting number of kernels"""
        kernels = Kernels()
        self.assertIsInstance(kernels.size(), int)
        self.assertGreaterEqual(kernels.size(), 0)

    def test_missing(self):
        """Test getting number of missing kernels"""
        kernels = Kernels()
        self.assertIsInstance(kernels.missing(), int)
        self.assertGreaterEqual(kernels.missing(), 0)

    def test_is_managed(self):
        """Test checking if kernels are managed"""
        kernels = Kernels()
        self.assertIsInstance(kernels.is_managed(), bool)

    def test_camera_version(self):
        """Test getting camera version"""
        kernels = Kernels()
        version = kernels.camera_version()
        self.assertIsInstance(version, int)

    def test_manage_unmanage_on_empty_kernel_set(self):
        """Empty Kernels remains vacuously managed even after un_manage()."""
        kernels = Kernels()
        self.assertEqual(kernels.size(), 0)

        kernels.manage()
        self.assertTrue(kernels.is_managed())

        kernels.un_manage()
        self.assertTrue(kernels.is_managed())

    def test_clear(self):
        """Test clearing kernels"""
        kernels = Kernels()
        kernels.clear()
        self.assertEqual(kernels.size(), 0)

    def test_get_kernel_types(self):
        """Test getting kernel types"""
        kernels = Kernels()
        types = kernels.get_kernel_types()
        self.assertIsInstance(types, list)

    def test_repr(self):
        """Test string representation"""
        kernels = Kernels()
        repr_str = repr(kernels)
        self.assertIn("Kernels", repr_str)
        self.assertIn("size=", repr_str)
        self.assertIn("missing=", repr_str)


class TestCSVReader(unittest.TestCase):
    """Test cases for CSVReader class"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_csv = os.path.join(self.temp_dir, "test.csv")

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_csv):
            os.remove(self.test_csv)
        os.rmdir(self.temp_dir)

    def test_construction(self):
        """Test CSVReader object construction"""
        reader = CSVReader()
        self.assertIsInstance(reader, CSVReader)

    def test_delimiter(self):
        """Test getting and setting delimiter"""
        reader = CSVReader()
        reader.set_delimiter(',')
        self.assertEqual(reader.get_delimiter(), ',')

    def test_header(self):
        """Test setting header flag"""
        reader = CSVReader()
        reader.set_header(True)
        self.assertTrue(reader.have_header())
        reader.set_header(False)
        self.assertFalse(reader.have_header())

    def test_skip(self):
        """Test setting skip lines"""
        reader = CSVReader()
        reader.set_skip(2)
        self.assertEqual(reader.get_skip(), 2)

    def test_keep_empty_parts(self):
        """Test keep empty parts setting"""
        reader = CSVReader()
        reader.set_keep_empty_parts()
        self.assertTrue(reader.keep_empty_parts())
        reader.set_skip_empty_parts()
        self.assertFalse(reader.keep_empty_parts())

    def test_read_csv(self):
        """Test reading a CSV file"""
        # Create a simple CSV file
        with open(self.test_csv, 'w') as f:
            f.write("col1,col2,col3\n")
            f.write("1,2,3\n")
            f.write("4,5,6\n")

        reader = CSVReader()
        reader.set_delimiter(',')
        reader.set_header(True)
        reader.read(self.test_csv)

        self.assertEqual(reader.size(), 3)  # 3 total lines
        self.assertEqual(reader.rows(), 2)   # 2 data rows (excluding header)
        self.assertEqual(reader.columns(), 3)  # 3 columns

    def test_get_header(self):
        """Test getting header row"""
        # Create a CSV file with header
        with open(self.test_csv, 'w') as f:
            f.write("Name,Age,City\n")
            f.write("Alice,30,NYC\n")

        reader = CSVReader()
        reader.set_delimiter(',')
        reader.set_header(True)
        reader.read(self.test_csv)

        header = reader.get_header()
        self.assertIsInstance(header, list)
        self.assertEqual(len(header), 3)
        self.assertEqual(header[0], "Name")
        self.assertEqual(header[1], "Age")
        self.assertEqual(header[2], "City")

    def test_get_row(self):
        """Test getting data row"""
        # Create a CSV file
        with open(self.test_csv, 'w') as f:
            f.write("col1,col2,col3\n")
            f.write("10,20,30\n")
            f.write("40,50,60\n")

        reader = CSVReader()
        reader.set_delimiter(',')
        reader.set_header(True)
        reader.read(self.test_csv)

        row = reader.get_row(0)
        self.assertIsInstance(row, list)
        self.assertEqual(len(row), 3)
        self.assertEqual(row[0], "10")
        self.assertEqual(row[1], "20")
        self.assertEqual(row[2], "30")

    def test_get_column_by_index(self):
        """Test getting column by index"""
        # Create a CSV file
        with open(self.test_csv, 'w') as f:
            f.write("A,B,C\n")
            f.write("1,2,3\n")
            f.write("4,5,6\n")

        reader = CSVReader()
        reader.set_delimiter(',')
        reader.set_header(True)
        reader.read(self.test_csv)

        col = reader.get_column(1)
        self.assertIsInstance(col, list)
        self.assertEqual(len(col), 2)
        self.assertEqual(col[0], "2")
        self.assertEqual(col[1], "5")

    def test_get_column_by_name(self):
        """Test getting column by name"""
        # Create a CSV file
        with open(self.test_csv, 'w') as f:
            f.write("Name,Value,Status\n")
            f.write("Item1,100,OK\n")
            f.write("Item2,200,OK\n")

        reader = CSVReader()
        reader.set_delimiter(',')
        reader.set_header(True)
        reader.read(self.test_csv)

        col = reader.get_column("Value")
        self.assertIsInstance(col, list)
        self.assertEqual(len(col), 2)
        self.assertEqual(col[0], "100")
        self.assertEqual(col[1], "200")

    def test_clear(self):
        """Test clearing data"""
        # Create a CSV file
        with open(self.test_csv, 'w') as f:
            f.write("A,B\n")
            f.write("1,2\n")

        reader = CSVReader()
        reader.set_delimiter(',')
        reader.set_header(True)
        reader.read(self.test_csv)

        self.assertGreater(reader.size(), 0)
        reader.clear()
        self.assertEqual(reader.size(), 0)

    def test_repr(self):
        """Test string representation"""
        reader = CSVReader()
        repr_str = repr(reader)
        self.assertIn("CSVReader", repr_str)
        self.assertIn("rows=", repr_str)
        self.assertIn("columns=", repr_str)


if __name__ == '__main__':
    unittest.main()
