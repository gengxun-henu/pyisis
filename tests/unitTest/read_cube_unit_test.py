# Test reading ISIS cube image dimensions
import unittest

from _unit_test_support import ip, workspace_test_data_path

class ReadCubeUnitTest(unittest.TestCase):
    def test_read_cube_dimensions(self):
        """Test reading cube dimensions from a test file"""
        cube = ip.Cube()
        strPath = "./tests/data/lronaccal/truth/M1333276014R.near.crop.cub"
        cube.open(strPath, "r")
        self.addCleanup(cube.close)

        # Verify we can read dimensions (actual values depend on test file)
        self.assertIsInstance(cube.sample_count(), int)
        self.assertIsInstance(cube.line_count(), int)
        self.assertIsInstance(cube.band_count(), int)
        self.assertGreater(cube.sample_count(), 0)
        self.assertGreater(cube.line_count(), 0)
        self.assertGreater(cube.band_count(), 0)

        print(f"Cube dimensions: {cube.sample_count()} samples x {cube.line_count()} lines x {cube.band_count()} bands")


if __name__ == "__main__":
    unittest.main()
