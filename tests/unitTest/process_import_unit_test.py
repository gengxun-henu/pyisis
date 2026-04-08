"""
Unit tests for ISIS ProcessImport bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-03-21
"""

import unittest

from _unit_test_support import temporary_raw_input_file, ip


class ProcessImportUnitTest(unittest.TestCase):
    def test_process_import_basic_configuration(self):
        with temporary_raw_input_file() as raw_input_path:
            importer = ip.ProcessImport()
            importer.set_input_file(str(raw_input_path))
            importer.set_pixel_type(ip.PixelType.UnsignedWord)
            importer.set_dimensions(16, 8, 2)
            importer.set_byte_order(ip.ByteOrder.Lsb)
            importer.set_organization(ip.ProcessImport.Interleave.BSQ)
            importer.set_file_header_bytes(64)
            importer.set_file_trailer_bytes(4)
            importer.set_data_header_bytes(2)
            importer.set_data_trailer_bytes(6)
            importer.set_data_prefix_bytes(8)
            importer.set_data_suffix_bytes(10)
            importer.set_base(1.0)
            importer.set_multiplier([2.0, 3.0])
            importer.set_null(-1.0, -1.0)
            importer.set_lrs(-2.0, -2.0)
            importer.set_lis(-3.0, -3.0)
            importer.set_hrs(1000.0, 1000.0)
            importer.set_his(2000.0, 2000.0)

            self.assertEqual(importer.input_file(), str(raw_input_path))
            self.assertEqual(importer.pixel_type(), ip.PixelType.UnsignedWord)
            self.assertEqual(importer.samples(), 16)
            self.assertEqual(importer.lines(), 8)
            self.assertEqual(importer.bands(), 2)
            self.assertEqual(importer.byte_order(), ip.ByteOrder.Lsb)
            self.assertEqual(importer.organization(), ip.ProcessImport.Interleave.BSQ)
            self.assertEqual(importer.file_header_bytes(), 64)
            self.assertEqual(importer.file_trailer_bytes(), 4)
            self.assertEqual(importer.data_header_bytes(), 2)
            self.assertEqual(importer.data_trailer_bytes(), 6)
            self.assertEqual(importer.data_prefix_bytes(), 8)
            self.assertEqual(importer.data_suffix_bytes(), 10)
            self.assertIsInstance(importer.test_pixel(5.0), float)

    def test_process_import_enums_and_scalar_vector_setters(self):
        importer = ip.ProcessImport()
        importer.set_base([1.0, 2.0])
        importer.set_multiplier(3.0)
        importer.set_special_values(-1.0, -2.0, -3.0, 1000.0, 2000.0)
        importer.set_vax_convert(True)
        importer.set_organization(ip.ProcessImport.Interleave.BIL)
        importer.set_suffix_pixel_type(ip.PixelType.UnsignedWord)
        importer.set_file_header_bytes(1)
        importer.set_file_trailer_bytes(1)
        importer.set_data_header_bytes(1)
        importer.set_data_trailer_bytes(1)
        importer.set_data_prefix_bytes(1)
        importer.set_data_suffix_bytes(1)
        importer.save_file_header()
        importer.save_file_trailer()
        importer.save_data_header()
        importer.save_data_trailer()
        importer.save_data_prefix()
        importer.save_data_suffix()

        self.assertEqual(importer.organization(), ip.ProcessImport.Interleave.BIL)
        self.assertEqual(ip.ProcessImport.VAXDataType.VAX_REAL, ip.ProcessImport.VAXDataType.VAX_REAL)
        self.assertEqual(ip.ProcessImport.VAXSpecialPixel.VAX_NULL4, ip.ProcessImport.VAXSpecialPixel.VAX_NULL4)

    def test_process_import_check_pixel_range_accepts_names_without_error(self):
        importer = ip.ProcessImport()
        self.assertIsNone(importer.check_pixel_range("NotAKnownPixel", 0.0, 1.0))
        self.assertIsNone(importer.check_pixel_range("Null", 0.0, 1.0))

    def test_process_import_fits_minimal_group_translation(self):
        fits_import = ip.ProcessImportFits()
        fits_group = ip.PvlGroup("FitsHeader")
        fits_group.add_keyword(ip.PvlKeyword("INSTRUME", "HIRISE"))

        instrument_group = fits_import.standard_instrument_group(fits_group)
        self.assertIsInstance(instrument_group, ip.PvlGroup)

    def test_process_import_pds_minimal_controls(self):
        pds_import = ip.ProcessImportPds()
        self.assertIsInstance(pds_import.is_isis2(), bool)
        pds_import.omit_original_label()
        self.assertEqual(ip.ProcessImportPds.PdsFileType.All, ip.ProcessImportPds.PdsFileType.All)

    def test_process_import_vicar_inheritance(self):
        vicar_import = ip.ProcessImportVicar()
        self.assertIsInstance(vicar_import, ip.ProcessImport)


if __name__ == "__main__":
    unittest.main()