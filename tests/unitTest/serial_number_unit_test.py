import unittest

from _unit_test_support import ip, temporary_text_file, workspace_test_data_path


class SerialNumberUnitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cube_path = workspace_test_data_path("mosrange", "EN0108828322M_iof.cub")
        cls.cube_paths = [
            workspace_test_data_path("mosrange", "EN0108828322M_iof.cub"),
            workspace_test_data_path("mosrange", "EN0108828327M_iof.cub"),
            workspace_test_data_path("mosrange", "EN0108828332M_iof.cub"),
            workspace_test_data_path("mosrange", "EN0108828337M_iof.cub"),
        ]

    def test_serial_and_observation_compose_from_filename_and_cube(self):
        serial_from_filename = ip.SerialNumber.compose(str(self.cube_path))
        observation_from_filename = ip.ObservationNumber.compose(str(self.cube_path))

        self.assertIsInstance(serial_from_filename, str)
        self.assertIsInstance(observation_from_filename, str)
        self.assertNotEqual(serial_from_filename, "Unknown")
        self.assertNotEqual(observation_from_filename, "Unknown")

        cube = ip.Cube()
        cube.open(str(self.cube_path))
        try:
            self.assertEqual(ip.SerialNumber.compose(cube), serial_from_filename)
            self.assertEqual(ip.ObservationNumber.compose(cube), observation_from_filename)
        finally:
            cube.close()

    def test_serial_number_list_single_file_round_trip(self):
        serial_number_list = ip.SerialNumberList()
        serial_number_list.add(str(self.cube_path))

        serial_number = ip.SerialNumber.compose(str(self.cube_path))
        observation_number = ip.ObservationNumber.compose(str(self.cube_path))

        self.assertEqual(len(serial_number_list), 1)
        self.assertEqual(serial_number_list.size(), 1)
        self.assertIn(serial_number, serial_number_list)
        self.assertTrue(serial_number_list.has_serial_number(serial_number))
        self.assertEqual(serial_number_list.file_name(serial_number), str(self.cube_path))
        self.assertEqual(serial_number_list.file_name(0), str(self.cube_path))
        self.assertEqual(serial_number_list.serial_number(str(self.cube_path)), serial_number)
        self.assertEqual(serial_number_list.serial_number(0), serial_number)
        self.assertEqual(serial_number_list.observation_number(0), observation_number)
        self.assertEqual(serial_number_list.serial_number_index(serial_number), 0)
        self.assertEqual(serial_number_list.file_name_index(str(self.cube_path)), 0)
        self.assertIsInstance(serial_number_list.spacecraft_instrument_id(0), str)
        self.assertTrue(serial_number_list.spacecraft_instrument_id(0))

    def test_observation_lookup_and_compose_observation(self):
        with temporary_text_file(
            "serial_number_list.lis",
            "\n".join(str(path) for path in self.cube_paths) + "\n",
        ) as list_path:
            serial_number_list = ip.SerialNumberList(str(list_path))
            self.assertGreaterEqual(len(serial_number_list), 4)

            serial_number = serial_number_list.serial_number(0)
            observation_number = serial_number_list.observation_number(0)

            possible_from_list = serial_number_list.possible_serial_numbers(observation_number)
            self.assertIn(serial_number, possible_from_list)

            observation_helper = ip.ObservationNumber()
            possible_from_helper = observation_helper.possible_serial(observation_number, serial_number_list)
            self.assertIn(serial_number, possible_from_helper)

            self.assertEqual(
                ip.SerialNumber.compose_observation(serial_number, serial_number_list),
                observation_number,
            )

    def test_remove_updates_membership(self):
        serial_number_list = ip.SerialNumberList()
        serial_number_list.add(str(self.cube_path))
        serial_number = serial_number_list.serial_number(0)

        serial_number_list.remove(serial_number)

        self.assertEqual(len(serial_number_list), 0)
        self.assertFalse(serial_number_list.has_serial_number(serial_number))


if __name__ == "__main__":
    unittest.main()
