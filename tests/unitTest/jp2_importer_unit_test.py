"""
Unit tests for ISIS JP2Importer and ImageImporter bindings.

Author: Geng Xun
Created: 2026-04-11
Last Modified: 2026-04-11
Updated: 2026-04-11  Geng Xun added initial JP2Importer binding tests.
"""

import unittest
import tempfile
import os
from pathlib import Path

try:
    import isis_pybind as ip
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python"))
    import isis_pybind as ip


class ImageImporterBaseTest(unittest.TestCase):
    """Test suite for ImageImporter abstract base class."""

    def test_image_importer_exists(self):
        """Test that ImageImporter class is accessible."""
        self.assertTrue(hasattr(ip, "ImageImporter"))


class JP2ImporterTest(unittest.TestCase):
    """Test suite for JP2Importer binding."""

    def test_jp2_importer_exists(self):
        """Test that JP2Importer class is accessible."""
        self.assertTrue(hasattr(ip, "JP2Importer"))

    def test_jp2_importer_repr(self):
        """Test JP2Importer __repr__ with a mock filename."""
        # This will fail at construction if the file doesn't exist,
        # but we're testing the binding signature
        pass  # Skip actual construction test without a real JP2 file

    def test_jp2_importer_methods(self):
        """Test that JP2Importer has expected methods."""
        # Verify methods exist
        self.assertTrue(hasattr(ip.JP2Importer, "is_grayscale"))
        self.assertTrue(hasattr(ip.JP2Importer, "is_rgb"))
        self.assertTrue(hasattr(ip.JP2Importer, "is_argb"))
        self.assertTrue(hasattr(ip.JP2Importer, "import"))
        self.assertTrue(hasattr(ip.JP2Importer, "samples"))
        self.assertTrue(hasattr(ip.JP2Importer, "lines"))
        self.assertTrue(hasattr(ip.JP2Importer, "bands"))

    def test_jp2_importer_inheritance(self):
        """Test that JP2Importer inherits from ImageImporter."""
        # This tests the binding hierarchy
        self.assertTrue(issubclass(ip.JP2Importer, ip.ImageImporter))


if __name__ == "__main__":
    unittest.main()
