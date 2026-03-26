#TODO: read a ISIS cube image, and get its dimensions, and print them out.
import unittest

from _unit_test_support import ip, workspace_test_data_path

class ReadCubeUnitTest(unittest.TestCase):
    def test_read_cube_dimensions(self):
        cube = ip.Cube()
        # Use workspace_test_data_path to get relative path to test data
        strPath = str(workspace_test_data_path("hayabusa2_test_data", "20180801", "hyb2_onc_20180801_211413_tpf_l2a.cal.cub"))
        cube.open(strPath, "r")
        self.addCleanup(cube.close)
        self.assertEqual(cube.sample_count(), 1024)
        self.assertEqual(cube.line_count(), 1024)
        self.assertEqual(cube.band_count(), 1)
        print(f"Cube dimensions: {cube.sample_count()} samples x {cube.line_count()} lines x {cube.band_count()} bands")


if __name__ == "__main__":
    unittest.main()