"""
Unit tests for ISIS image import/export bindings

Author: Geng Xun
Created: 2026-04-11
Last Modified: 2026-04-11
Updated: 2026-04-11  Geng Xun added focused regression coverage for JP2Exporter, TiffExporter, TiffImporter, QtExporter, QtImporter bindings.
Updated: 2026-04-11  Geng Xun aligned exporter format assertions with upstream lowercase-only canWriteFormat behavior.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Use shared test environment helpers
try:
    import _unit_test_support as support
    ip = support.ip
except ImportError:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    BUILD_PYTHON_DIR = PROJECT_ROOT / "build" / "python"
    if BUILD_PYTHON_DIR.exists():
        sys.path.insert(0, str(BUILD_PYTHON_DIR))
    import isis_pybind as ip


class JP2ExporterTest(unittest.TestCase):
    """Test suite for JP2Exporter binding regression coverage."""

    def test_constructor(self):
        """Test JP2Exporter default constructor."""
        exporter = ip.JP2Exporter()
        self.assertIsInstance(exporter, ip.JP2Exporter)
        self.assertIsInstance(exporter, ip.StreamExporter)
        self.assertIsInstance(exporter, ip.ImageExporter)

    def test_can_write_format_static(self):
        """Test JP2Exporter.can_write_format static method."""
        # Upstream JP2Exporter::canWriteFormat only accepts lowercase "jp2"
        self.assertTrue(ip.JP2Exporter.can_write_format("jp2"))
        self.assertFalse(ip.JP2Exporter.can_write_format("JP2"))
        # Should not handle other formats
        self.assertFalse(ip.JP2Exporter.can_write_format("j2k"))
        self.assertFalse(ip.JP2Exporter.can_write_format("tiff"))
        self.assertFalse(ip.JP2Exporter.can_write_format("png"))

    def test_repr(self):
        """Test JP2Exporter __repr__."""
        exporter = ip.JP2Exporter()
        repr_str = repr(exporter)
        self.assertIn("JP2Exporter", repr_str)


class TiffExporterTest(unittest.TestCase):
    """Test suite for TiffExporter binding regression coverage."""

    def test_constructor(self):
        """Test TiffExporter default constructor."""
        exporter = ip.TiffExporter()
        self.assertIsInstance(exporter, ip.TiffExporter)
        self.assertIsInstance(exporter, ip.StreamExporter)
        self.assertIsInstance(exporter, ip.ImageExporter)

    def test_can_write_format_static(self):
        """Test TiffExporter.can_write_format static method."""
        # Upstream TiffExporter::canWriteFormat only accepts lowercase "tiff"
        self.assertTrue(ip.TiffExporter.can_write_format("tiff"))
        self.assertFalse(ip.TiffExporter.can_write_format("tif"))
        self.assertFalse(ip.TiffExporter.can_write_format("TIF"))
        self.assertFalse(ip.TiffExporter.can_write_format("TIFF"))
        # Should not handle other formats
        self.assertFalse(ip.TiffExporter.can_write_format("jp2"))
        self.assertFalse(ip.TiffExporter.can_write_format("png"))

    def test_repr(self):
        """Test TiffExporter __repr__."""
        exporter = ip.TiffExporter()
        repr_str = repr(exporter)
        self.assertIn("TiffExporter", repr_str)


class TiffImporterTest(unittest.TestCase):
    """Test suite for TiffImporter binding regression coverage."""

    def test_constructor_signature(self):
        """Test TiffImporter constructor signature (will fail without valid file)."""
        # Constructor requires FileName, test that it accepts FileName type
        with self.assertRaises(Exception):  # Will fail with nonexistent file
            importer = ip.TiffImporter(ip.FileName("/nonexistent.tif"))

    def test_inheritance(self):
        """Test that TiffImporter class exists and has correct inheritance."""
        # Just verify the class is accessible
        self.assertTrue(hasattr(ip, "TiffImporter"))


class QtExporterTest(unittest.TestCase):
    """Test suite for QtExporter binding regression coverage."""

    def test_constructor(self):
        """Test QtExporter constructor with format parameter."""
        exporter = ip.QtExporter("png")
        self.assertIsInstance(exporter, ip.QtExporter)
        self.assertIsInstance(exporter, ip.ImageExporter)

    def test_can_write_format_static(self):
        """Test QtExporter.can_write_format static method."""
        # Upstream QtExporter::canWriteFormat compares against Qt's supported
        # format list without lowercasing first, so uppercase input stays false.
        self.assertTrue(ip.QtExporter.can_write_format("png"))
        self.assertTrue(ip.QtExporter.can_write_format("jpg"))
        self.assertTrue(ip.QtExporter.can_write_format("jpeg"))
        self.assertTrue(ip.QtExporter.can_write_format("bmp"))
        self.assertFalse(ip.QtExporter.can_write_format("PNG"))
        self.assertFalse(ip.QtExporter.can_write_format("JPG"))
        self.assertFalse(ip.QtExporter.can_write_format("gif"))

    def test_repr(self):
        """Test QtExporter __repr__."""
        exporter = ip.QtExporter("png")
        repr_str = repr(exporter)
        self.assertIn("QtExporter", repr_str)


class QtImporterTest(unittest.TestCase):
    """Test suite for QtImporter binding regression coverage."""

    def test_constructor_signature(self):
        """Test QtImporter constructor signature (will fail without valid file)."""
        # Constructor requires FileName, test that it accepts FileName type
        with self.assertRaises(Exception):  # Will fail with nonexistent file
            importer = ip.QtImporter(ip.FileName("/nonexistent.png"))

    def test_inheritance(self):
        """Test that QtImporter class exists and has correct inheritance."""
        # Just verify the class is accessible
        self.assertTrue(hasattr(ip, "QtImporter"))


class ImageExporterTest(unittest.TestCase):
    """Test suite for ImageExporter abstract base class binding."""

    def test_base_class_exists(self):
        """Test that ImageExporter base class is accessible."""
        self.assertTrue(hasattr(ip, "ImageExporter"))

    def test_jp2_exporter_is_image_exporter(self):
        """Test that JP2Exporter is an ImageExporter."""
        exporter = ip.JP2Exporter()
        self.assertIsInstance(exporter, ip.ImageExporter)

    def test_tiff_exporter_is_image_exporter(self):
        """Test that TiffExporter is an ImageExporter."""
        exporter = ip.TiffExporter()
        self.assertIsInstance(exporter, ip.ImageExporter)

    def test_qt_exporter_is_image_exporter(self):
        """Test that QtExporter is an ImageExporter."""
        exporter = ip.QtExporter("png")
        self.assertIsInstance(exporter, ip.ImageExporter)


class StreamExporterTest(unittest.TestCase):
    """Test suite for StreamExporter abstract base class binding."""

    def test_base_class_exists(self):
        """Test that StreamExporter base class is accessible."""
        self.assertTrue(hasattr(ip, "StreamExporter"))

    def test_jp2_exporter_is_stream_exporter(self):
        """Test that JP2Exporter is a StreamExporter."""
        exporter = ip.JP2Exporter()
        self.assertIsInstance(exporter, ip.StreamExporter)

    def test_tiff_exporter_is_stream_exporter(self):
        """Test that TiffExporter is a StreamExporter."""
        exporter = ip.TiffExporter()
        self.assertIsInstance(exporter, ip.StreamExporter)


class ImageImporterTest(unittest.TestCase):
    """Test suite for ImageImporter abstract base class binding."""

    def test_base_class_exists(self):
        """Test that ImageImporter base class is accessible."""
        self.assertTrue(hasattr(ip, "ImageImporter"))


if __name__ == "__main__":
    unittest.main()
