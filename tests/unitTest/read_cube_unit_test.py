"""
Unit tests for reading ISIS cube image dimensions.

Author: Geng Xun
Created: 2026-04-03
Last Modified: 2026-04-03
"""

import unittest

from _unit_test_support import ip, workspace_test_data_path


class ReadCubeUnitTest(unittest.TestCase):
    def test_read_cube_dimensions(self):
        """Test reading cube dimensions from a test file"""
        cube = ip.Cube()
        cube_path = workspace_test_data_path(
            "lronaccal",
            "truth",
            "M1333276014R.near.crop.cub",
        )
        self.assertTrue(cube_path.exists(), f"Required test cube is missing: {cube_path}")

        cube.open(str(cube_path), "r")
        self.addCleanup(cube.close)

        # Verify we can read dimensions (actual values depend on test file)
        self.assertIsInstance(cube.sample_count(), int)
        self.assertIsInstance(cube.line_count(), int)
        self.assertIsInstance(cube.band_count(), int)
        self.assertGreater(cube.sample_count(), 0)
        self.assertGreater(cube.line_count(), 0)
        self.assertGreater(cube.band_count(), 0)

        print(
            f"Cube dimensions: {cube.sample_count()} samples x {cube.line_count()} lines x {cube.band_count()} bands"
        )


if __name__ == "__main__":
    unittest.main()
