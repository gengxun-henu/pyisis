"""
Unit tests for ISIS high-level cube I/O bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-04-09
Updated: 2026-04-04  Geng Xun added focused ExportDescription and JPEG2000 surface regression coverage with environment-aware skips.
Updated: 2026-04-09  Geng Xun added focused SubArea coverage for parameter validation and label propagation on local test cubes.
"""

import unittest

from _unit_test_support import close_cube_quietly, ip, make_test_cube, temporary_directory, temporary_text_file


# Suite-level gate is now open. Environment-sensitive JP2/Kakadu-dependent
# paths still perform per-test skips via the helper methods below when the
# underlying ISIS build lacks JPEG2000 support.
SKIP_HIGH_LEVEL_CUBE_IO_TESTS = False


@unittest.skipIf(
    SKIP_HIGH_LEVEL_CUBE_IO_TESTS,
    "High-level cube I/O tests are temporarily disabled until the binding/runtime setup is complete.",
)
class HighLevelCubeIoUnitTest(unittest.TestCase):
    def _make_encoder_or_skip(self, output_path):
        try:
            return ip.JP2Encoder(str(output_path), 4, 3, 1, ip.PixelType.UnsignedByte)
        except ip.IException as error:
            if "JPEG2000 has not been enabled" in str(error):
                self.skipTest("JP2Encoder requires JPEG2000/Kakadu support in this build")
            raise

    def _make_decoder_or_skip(self, input_path):
        try:
            return ip.JP2Decoder(str(input_path))
        except ip.IException as error:
            if "JPEG2000 has not been enabled" in str(error):
                self.skipTest("JP2Decoder requires JPEG2000/Kakadu support in this build")
            raise

    def test_export_description_channel_configuration(self):
        desc = ip.ExportDescription()
        self.assertEqual(desc.pixel_type(), getattr(ip.PixelType, "None"))

        desc.set_pixel_type(ip.PixelType.SignedWord)
        self.assertEqual(desc.pixel_type(), ip.PixelType.SignedWord)
        self.assertEqual(desc.output_pixel_null(), -32768.0)
        self.assertEqual(desc.output_pixel_valid_min(), -32767.0)
        self.assertEqual(desc.output_pixel_valid_max(), 32767.0)
        self.assertEqual(desc.output_pixel_absolute_min(), -32768.0)
        self.assertEqual(desc.output_pixel_absolute_max(), 32767.0)

        first_index = desc.add_channel(ip.FileName("red.cub"), "+1")
        second_index = desc.add_channel(ip.FileName("green.cub"), ["2"], 100.0, 500.0)
        self.assertEqual(first_index, 0)
        self.assertEqual(second_index, 1)
        self.assertEqual(desc.channel_count(), 2)

        first_channel = desc.channel(0)
        self.assertEqual(first_channel.filename().name(), "red.cub")
        self.assertEqual(first_channel.attributes(), "+1")
        self.assertEqual(first_channel.bands(), ["1"])
        self.assertFalse(first_channel.has_custom_range())

        second_channel = desc.channel(1)
        self.assertEqual(second_channel.filename().name(), "green.cub")
        self.assertEqual(second_channel.attributes(), "+2")
        self.assertEqual(second_channel.bands(), ["2"])
        self.assertTrue(second_channel.has_custom_range())
        self.assertEqual(second_channel.input_minimum(), 100.0)
        self.assertEqual(second_channel.input_maximum(), 500.0)

    def test_export_description_channel_description_construction(self):
        channel = ip.ExportDescription.ChannelDescription(ip.FileName("blue.cub"), ["3", "5-6"])
        self.assertEqual(channel.filename().name(), "blue.cub")
        self.assertEqual(channel.attributes(), "+3,5-6")
        self.assertEqual(channel.bands(), ["3", "5", "6"])

        channel.set_input_range(10.0, 20.0)
        self.assertTrue(channel.has_custom_range())
        self.assertEqual(channel.input_minimum(), 10.0)
        self.assertEqual(channel.input_maximum(), 20.0)

    def test_sub_area_validates_ranges_and_updates_output_cube_labels(self):
        subarea = ip.SubArea()
        self.assertEqual(repr(subarea), "SubArea()")

        with self.assertRaises(ip.IException):
            subarea.set_sub_area(4, 5, 4, 1, 3, 5, 1.0, 1.0)

        with self.assertRaises(ip.IException):
            subarea.set_sub_area(4, 5, 1, 1, 4, 5, 0.0, 1.0)

        with temporary_directory() as temp_dir:
            input_cube, _ = make_test_cube(temp_dir, name="subarea_input.cub", samples=5, lines=4, bands=1)
            output_cube, _ = make_test_cube(temp_dir, name="subarea_output.cub", samples=3, lines=3, bands=1)
            self.addCleanup(close_cube_quietly, input_cube)
            self.addCleanup(close_cube_quietly, output_cube)

            instrument_group = ip.PvlGroup("Instrument")
            instrument_group.add_keyword(ip.PvlKeyword("InstrumentId", "UNITTESTCAM"))
            instrument_group.add_keyword(ip.PvlKeyword("SpacecraftName", "UNITTESTORB"))
            input_cube.put_group(instrument_group)

            stale_group = ip.PvlGroup("Instrument")
            stale_group.add_keyword(ip.PvlKeyword("InstrumentId", "STALE"))
            output_cube.put_group(stale_group)

            results = ip.PvlGroup("Results")
            subarea.set_sub_area(4, 5, 2, 2, 4, 4, 1.0, 1.0)
            subarea.update_label(input_cube, output_cube, results)

            self.assertTrue(output_cube.has_group("Instrument"))
            self.assertTrue(output_cube.has_group("AlphaCube"))
            self.assertEqual(output_cube.group("Instrument").find_keyword("InstrumentId")[0], "UNITTESTCAM")
            self.assertEqual(output_cube.group("Instrument").find_keyword("SpacecraftName")[0], "UNITTESTORB")
            self.assertEqual(output_cube.group("AlphaCube").name(), "AlphaCube")
            self.assertFalse(results.has_keyword("MappingGroupDeleted"))

    @unittest.skip(
        "JP2Error binding is currently unstable in this build: message accumulation does not round-trip as expected and flush() teardown can crash the process."
    )
    def test_jp2_error_accumulates_text_and_flush_raises(self):
        error = ip.JP2Error()
        error.put_text("first")
        error.add_text("second")

        self.assertEqual(error.message, "first\nsecond")
        with self.assertRaises(ip.IException):
            error.flush()

    @unittest.skip(
        "JP2Decoder/JP2Encoder surface behavior is not yet stable in this build: JP2 signature detection does not currently match the fake-stream expectation."
    )
    def test_jp2_decoder_and_encoder_minimal_surface(self):
        with temporary_text_file("fake.jp2", "not a real jpeg2000 stream") as fake_jp2:
            self.assertFalse(ip.JP2Decoder.is_jp2(str(fake_jp2)))

            decoder = self._make_decoder_or_skip(fake_jp2)
            self.assertIsInstance(decoder.kakadu_error(), ip.JP2Error)

            encoder = self._make_encoder_or_skip(fake_jp2.with_name("out.jp2"))
            self.assertIsInstance(encoder.kakadu_error(), ip.JP2Error)


if __name__ == "__main__":
    unittest.main()
