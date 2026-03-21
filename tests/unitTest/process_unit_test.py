import unittest

from _unit_test_support import ip


class ProcessUnitTest(unittest.TestCase):
    def test_progress_basic_state(self):
        progress = ip.Progress()
        progress.set_text("Working")
        progress.set_maximum_steps(5)
        progress.add_steps(2)
        progress.disable_automatic_display()

        self.assertEqual(progress.text(), "Working")
        self.assertEqual(progress.maximum_steps(), 7)
        progress.check_status()
        self.assertIsInstance(progress.current_step(), int)

    def test_process_progress_and_propagation_controls(self):
        process = ip.Process()
        process.propagate_labels(False)
        process.propagate_tables(False)
        process.propagate_polygons(False)
        process.propagate_history(False)
        process.propagate_original_label(False)

        self.assertIsInstance(process.progress(), ip.Progress)
        self.assertIsNone(process.clear_cubes())
        self.assertIsNone(process.clear_input_cubes())
        self.assertIsNone(process.clear_output_cubes())

    def test_process_by_brick_configuration(self):
        by_brick = ip.ProcessByBrick()
        by_brick.set_wrap(True)
        by_brick.set_processing_direction(ip.ProcessByBrick.ProcessingDirection.BandsFirst)
        by_brick.set_output_requirements(ip.OneBand)
        by_brick.set_brick_size(2, 3, 1)
        by_brick.set_input_brick_size(2, 3, 1)
        by_brick.set_output_brick_size(2, 3, 1)

        self.assertTrue(by_brick.wraps())
        self.assertEqual(by_brick.get_processing_direction(), ip.ProcessByBrick.ProcessingDirection.BandsFirst)

    def test_process_by_brick_cube_set_enums_exist(self):
        self.assertEqual(ip.ProcessByBrick.IOCubes.InPlace, ip.ProcessByBrick.IOCubes.InPlace)
        self.assertEqual(ip.ProcessByBrick.IOCubes.InputOutput, ip.ProcessByBrick.IOCubes.InputOutput)
        self.assertEqual(ip.ProcessByBrick.IOCubes.InputOutputList, ip.ProcessByBrick.IOCubes.InputOutputList)

    def test_process_by_line_sample_spectra_and_tile_types(self):
        by_line = ip.ProcessByLine()
        by_sample = ip.ProcessBySample()
        by_spectra = ip.ProcessBySpectra(ip.ProcessBySpectra.BySample)
        by_tile = ip.ProcessByTile()
        by_tile.set_tile_size(4, 4)

        self.assertIsInstance(by_line, ip.ProcessByBrick)
        self.assertIsInstance(by_sample, ip.ProcessByBrick)
        self.assertIsInstance(by_tile, ip.ProcessByBrick)
        self.assertEqual(by_spectra.type(), ip.ProcessBySpectra.BySample)

        by_spectra.set_type(ip.ProcessBySpectra.ByLine)
        self.assertEqual(by_spectra.type(), ip.ProcessBySpectra.ByLine)

    def test_process_by_boxcar_and_quickfilter_configuration(self):
        boxcar = ip.ProcessByBoxcar()
        boxcar.set_boxcar_size(3, 3)
        boxcar.finalize()

        quick_filter = ip.ProcessByQuickFilter()
        quick_filter.set_filter_parameters(5, 5, -10.0, 10.0, 3)

        self.assertIsInstance(boxcar, ip.Process)
        self.assertIsInstance(quick_filter, ip.Process)


if __name__ == "__main__":
    unittest.main()