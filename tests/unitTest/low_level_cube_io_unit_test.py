"""低层级 Cube I/O 绑定的单元测试

Author: Geng Xun
Created: 2026-04-03
Last Modified: 2026-04-03
"""

import unittest

from _unit_test_support import ip, temporary_directory


class LowLevelCubeIoUnitTest(unittest.TestCase):
    def make_test_cube(self):
        temp_dir_cm = temporary_directory()
        temp_dir = temp_dir_cm.__enter__()
        self.addCleanup(temp_dir_cm.__exit__, None, None, None)

        cube_path = temp_dir / "band_manager_test.cub"
        cube = ip.Cube()
        cube.set_dimensions(4, 3, 2)
        cube.set_pixel_type(ip.PixelType.Real)
        cube.create(str(cube_path))
        self.addCleanup(cube.close)
        return cube

    def test_pixel_type_and_byte_order_helpers(self):
        self.assertEqual(ip.pixel_type_name(ip.PixelType.Real), "Real")
        self.assertEqual(ip.pixel_type_enumeration("Real"), ip.PixelType.Real)
        self.assertEqual(ip.byte_order_name(ip.ByteOrder.Lsb), "Lsb")
        self.assertEqual(ip.byte_order_enumeration("Lsb"), ip.ByteOrder.Lsb)
        self.assertIsInstance(ip.is_lsb(), bool)
        self.assertIsInstance(ip.is_msb(), bool)

    def test_buffer_basic_indexing_and_copy(self):
        buffer = ip.Buffer(2, 2, 1, ip.PixelType.Real)
        buffer[0] = 1.5
        buffer[1] = 2.5
        buffer[2] = 3.5
        buffer[3] = 4.5

        self.assertEqual(len(buffer), 4)
        self.assertEqual(buffer.sample_dimension(), 2)
        self.assertEqual(buffer.line_dimension(), 2)
        self.assertEqual(buffer.band_dimension(), 1)
        self.assertEqual(buffer.position(3), (1, 1, 0))
        self.assertEqual(buffer.index(1, 1, 0), 3)
        self.assertEqual(buffer.at(0), 1.5)
        self.assertEqual(buffer.double_buffer(), [1.5, 2.5, 3.5, 4.5])

        other = ip.Buffer(2, 2, 1, ip.PixelType.Real)
        other.fill(9.0)
        buffer.copy(other)
        self.assertEqual(buffer.double_buffer(), [9.0, 9.0, 9.0, 9.0])

    def test_buffer_manager_iteration_state(self):
        manager = ip.BufferManager(4, 4, 1, 2, 2, 1, ip.PixelType.Real)
        self.assertTrue(manager.begin())
        self.assertFalse(manager.end())
        self.assertEqual(manager.sample(), 1)
        self.assertEqual(manager.line(), 1)
        self.assertEqual(manager.band(), 1)
        self.assertTrue(manager.next())
        self.assertEqual(manager.sample(), 3)
        self.assertEqual(manager.line(), 1)
        self.assertEqual(manager.band(), 1)

    def test_band_manager_construction_and_set_band(self):
        cube = self.make_test_cube()

        manager = ip.BandManager(cube)
        self.assertTrue(manager.begin())
        self.assertEqual(manager.sample(), 1)
        self.assertEqual(manager.line(), 1)
        self.assertEqual(manager.band(), 1)

        self.assertTrue(manager.set_band(2))
        self.assertEqual(manager.sample(), 2)
        self.assertEqual(manager.line(), 1)
        self.assertEqual(manager.band(), 1)

        self.assertTrue(manager.set_band(1, 2))
        self.assertEqual(manager.sample(), 3)
        self.assertEqual(manager.line(), 1)
        self.assertEqual(manager.band(), 1)

        self.assertIsInstance(manager.next(), bool)
        self.assertEqual(manager.sample(), 4)
        self.assertEqual(manager.line(), 1)
        self.assertEqual(manager.band(), 1)

    def test_boxcar_manager_construction_and_iteration(self):
        """Test BoxcarManager with 5x5 and 4x4 boxcars."""
        cube = self.make_test_cube()

        # Test 5x5 boxcar
        manager_5x5 = ip.BoxcarManager(cube, 5, 5)
        self.assertTrue(manager_5x5.begin())
        self.assertEqual(manager_5x5.sample_dimension(), 5)
        self.assertEqual(manager_5x5.line_dimension(), 5)
        self.assertEqual(manager_5x5.band_dimension(), 1)

        # Test basic iteration
        iteration_count = 0
        manager_5x5.begin()
        while not manager_5x5.end():
            iteration_count += 1
            # Verify that we can access dimensions at each step
            self.assertGreater(manager_5x5.sample_dimension(), 0)
            self.assertGreater(manager_5x5.line_dimension(), 0)
            manager_5x5.next()

        # BoxcarManager should iterate through entire cube (4 samples x 3 lines x 2 bands)
        expected_iterations = 4 * 3 * 2
        self.assertEqual(iteration_count, expected_iterations)

        # Test 4x4 boxcar
        manager_4x4 = ip.BoxcarManager(cube, 4, 4)
        self.assertEqual(manager_4x4.sample_dimension(), 4)
        self.assertEqual(manager_4x4.line_dimension(), 4)
        self.assertEqual(manager_4x4.band_dimension(), 1)

        # Test that begin and next work properly
        self.assertTrue(manager_4x4.begin())
        self.assertFalse(manager_4x4.end())
        self.assertTrue(manager_4x4.next())

    def test_brick_portal_and_alpha_cube(self):
        brick = ip.Brick(4, 4, 1, ip.PixelType.Real)
        brick.set_base_position(2, 3, 1)
        self.assertEqual(brick.sample(), 2)
        self.assertEqual(brick.line(), 3)
        self.assertEqual(brick.band(), 1)
        brick.resize(2, 2, 1)
        self.assertEqual(brick.sample_dimension(), 2)

        portal = ip.Portal(3, 3, ip.PixelType.Real)
        portal.set_hot_spot(0.0, 0.0)
        portal.set_position(10.0, 20.0, 1)
        self.assertEqual(portal.sample(), 10)
        self.assertEqual(portal.line(), 20)
        self.assertEqual(portal.band(), 1)

        alpha_cube = ip.AlphaCube(100, 200, 100, 200)
        self.assertEqual(alpha_cube.alpha_samples(), 100)
        self.assertEqual(alpha_cube.alpha_lines(), 200)
        self.assertEqual(alpha_cube.beta_samples(), 100)
        self.assertEqual(alpha_cube.beta_lines(), 200)
        self.assertIsInstance(alpha_cube.alpha_sample(1.0), float)
        self.assertIsInstance(alpha_cube.beta_line(10.0), float)

    def test_alpha_cube_rehash_merges_subarea_mapping(self):
        source = ip.AlphaCube(4, 8, 2, 3, 1.5, 2.5, 3.5, 5.5)
        subarea = ip.AlphaCube(2, 3, 2, 4, 1.5, 1.5, 2.5, 3.5)

        self.assertEqual(source.beta_lines(), 3)

        source.rehash(subarea)

        self.assertEqual(source.alpha_samples(), 4)
        self.assertEqual(source.alpha_lines(), 8)
        self.assertEqual(source.beta_samples(), subarea.beta_samples())
        self.assertEqual(source.beta_lines(), subarea.beta_lines())
        self.assertAlmostEqual(source.alpha_sample(0.5), 2.5)
        self.assertAlmostEqual(source.alpha_line(0.5), 3.5)
        self.assertAlmostEqual(source.alpha_sample(source.beta_samples()), 3.25)
        self.assertAlmostEqual(source.alpha_line(source.beta_lines()), 5.25)
        self.assertAlmostEqual(source.alpha_sample(source.beta_samples() + 0.5), 3.5)
        self.assertAlmostEqual(source.alpha_line(source.beta_lines() + 0.5), 5.5)
        self.assertAlmostEqual(source.beta_sample(2.5), 0.5)
        self.assertAlmostEqual(source.beta_line(3.5), 0.5)

    def test_table_field_scalar_and_text_values(self):
        numeric_field = ip.TableField("Value", ip.TableField.Type.Double)
        numeric_field.set_value(3.5)
        self.assertEqual(numeric_field.name(), "Value")
        self.assertTrue(numeric_field.is_double())
        self.assertEqual(numeric_field.value(), 3.5)
        self.assertIn("TableField", repr(numeric_field))

        text_field = ip.TableField("Name", ip.TableField.Type.Text, 8)
        text_field.set_value("MARS")
        self.assertTrue(text_field.is_text())
        self.assertEqual(text_field.value(), "MARS")
        self.assertIn("MARS", str(text_field))

    def test_table_field_vector_values(self):
        integer_field = ip.TableField("Indices", ip.TableField.Type.Integer, 3)
        integer_field.set_value([1, 2, 3])
        self.assertEqual(integer_field.value(), [1, 2, 3])

        real_field = ip.TableField("Weights", ip.TableField.Type.Real, 2)
        real_field.set_value([1.5, 2.5])
        self.assertEqual(real_field.value(), [1.5, 2.5])

    def test_table_record_access_and_string_conversion(self):
        value_field = ip.TableField("Value", ip.TableField.Type.Double)
        value_field.set_value(3.5)
        name_field = ip.TableField("Name", ip.TableField.Type.Text, 8)
        name_field.set_value("MARS")

        record = ip.TableRecord()
        record.add_field(value_field)
        record.add_field(name_field)

        self.assertEqual(len(record), 2)
        self.assertEqual(record.fields(), 2)
        self.assertEqual(record[0].value(), 3.5)
        self.assertEqual(record["Name"].value(), "MARS")
        self.assertIn("Value", record.to_string(field_names=True))
        self.assertIn("TableRecord(fields=2)", repr(record))

    def test_table_record_from_string_constructor(self):
        record = ip.TableRecord("1,2", ",", ["First", "Second"], 2)
        self.assertEqual(len(record), 2)
        self.assertEqual(record["First"].value(), 1.0)
        self.assertEqual(record["Second"].value(), 2.0)

    def test_table_basic_management(self):
        record = ip.TableRecord()
        value_field = ip.TableField("Value", ip.TableField.Type.Double)
        value_field.set_value(3.5)
        name_field = ip.TableField("Name", ip.TableField.Type.Text, 8)
        name_field.set_value("MARS")
        record.add_field(value_field)
        record.add_field(name_field)

        table = ip.Table("Example", record)
        table.add_record(record)
        self.assertEqual(len(table), 1)
        self.assertEqual(table.name(), "Example")
        self.assertEqual(table.record_fields(), 2)
        self.assertEqual(table.record_size(), record.record_size())
        self.assertEqual(table[0]["Name"].value(), "MARS")

        table.set_association(ip.Table.Association.Samples)
        self.assertTrue(table.is_sample_associated())
        self.assertFalse(table.is_line_associated())
        self.assertIn("Value", table.to_string())

        updated_record = ip.TableRecord()
        updated_value = ip.TableField("Value", ip.TableField.Type.Double)
        updated_value.set_value(7.5)
        updated_name = ip.TableField("Name", ip.TableField.Type.Text, 8)
        updated_name.set_value("PHOBOS")
        updated_record.add_field(updated_value)
        updated_record.add_field(updated_name)

        table.update(updated_record, 0)
        self.assertEqual(table[0]["Name"].value(), "PHOBOS")
        table.delete(0)
        self.assertEqual(len(table), 0)
        table.clear()
        self.assertEqual(table.records(), 0)
        self.assertIn("Table(name='Example'", repr(table))

    def test_boxcar_manager_construction(self):
        """Test BoxcarManager construction with various boxcar sizes"""
        temp_dir_cm = temporary_directory()
        temp_dir = temp_dir_cm.__enter__()
        self.addCleanup(temp_dir_cm.__exit__, None, None, None)

        cube_path = temp_dir / "boxcar_test.cub"
        cube = ip.Cube()
        cube.set_dimensions(10, 10, 1)
        cube.set_pixel_type(ip.PixelType.Real)
        cube.create(str(cube_path))
        self.addCleanup(cube.close)

        # Initialize cube data so reads work
        line_mgr = ip.LineManager(cube)
        line_mgr.begin()
        while not line_mgr.end():
            for i in range(len(line_mgr)):
                line_mgr[i] = float(line_mgr.line())
            cube.write(line_mgr)
            line_mgr.next()

        # Test 5x5 boxcar
        boxcar5 = ip.BoxcarManager(cube, 5, 5)
        self.assertEqual(boxcar5.sample_dimension(), 5)
        self.assertEqual(boxcar5.line_dimension(), 5)
        self.assertEqual(boxcar5.band_dimension(), 1)

        # Test 3x3 boxcar
        boxcar3 = ip.BoxcarManager(cube, 3, 3)
        self.assertEqual(boxcar3.sample_dimension(), 3)
        self.assertEqual(boxcar3.line_dimension(), 3)

    def test_boxcar_manager_iteration(self):
        """Test BoxcarManager iteration through cube positions"""
        temp_dir_cm = temporary_directory()
        temp_dir = temp_dir_cm.__enter__()
        self.addCleanup(temp_dir_cm.__exit__, None, None, None)

        cube_path = temp_dir / "boxcar_iteration_test.cub"
        cube = ip.Cube()
        cube.set_dimensions(6, 6, 1)
        cube.set_pixel_type(ip.PixelType.Real)
        cube.create(str(cube_path))
        self.addCleanup(cube.close)

        # Initialize cube with line manager
        line_mgr = ip.LineManager(cube)
        line_mgr.begin()
        while not line_mgr.end():
            for i in range(len(line_mgr)):
                line_mgr[i] = 10.0
            cube.write(line_mgr)
            line_mgr.next()

        # Test iteration
        boxcar = ip.BoxcarManager(cube, 3, 3)
        count = 0
        boxcar.begin()
        self.assertFalse(boxcar.end())

        while not boxcar.end():
            count += 1
            # Verify we can read at each position
            cube.read(boxcar)
            # BoxcarManager iterates pixel-by-pixel
            boxcar.next()

        # Should iterate through all pixels: 6 samples * 6 lines * 1 band
        self.assertEqual(count, 36)

    def test_boxcar_manager_edge_positions(self):
        """Test BoxcarManager handles edge positions with negative coordinates"""
        temp_dir_cm = temporary_directory()
        temp_dir = temp_dir_cm.__enter__()
        self.addCleanup(temp_dir_cm.__exit__, None, None, None)

        cube_path = temp_dir / "boxcar_edge_test.cub"
        cube = ip.Cube()
        cube.set_dimensions(4, 4, 1)
        cube.set_pixel_type(ip.PixelType.Real)
        cube.create(str(cube_path))
        self.addCleanup(cube.close)

        # Initialize data
        line_mgr = ip.LineManager(cube)
        line_mgr.begin()
        while not line_mgr.end():
            for i in range(len(line_mgr)):
                line_mgr[i] = 5.0
            cube.write(line_mgr)
            line_mgr.next()

        # 5x5 boxcar on 4x4 cube will have edge positions with negative coords
        boxcar = ip.BoxcarManager(cube, 5, 5)
        boxcar.begin()

        # At the first position, upper-left corner should have negative coords
        # Based on BoxcarManager.cpp: soff = (int)((boxSamples - 1) / 2) * -1
        # For 5x5: soff = (5-1)/2 * -1 = -2, so first sample position is 1-2 = -1
        self.assertLessEqual(boxcar.sample(), 0)
        self.assertLessEqual(boxcar.line(), 0)

        # Should still be able to read safely
        try:
            cube.read(boxcar)
        except Exception as e:
            self.fail(f"Edge position read failed: {e}")

    def test_boxcar_manager_different_sizes(self):
        """Test BoxcarManager with different boxcar dimensions"""
        temp_dir_cm = temporary_directory()
        temp_dir = temp_dir_cm.__enter__()
        self.addCleanup(temp_dir_cm.__exit__, None, None, None)

        cube_path = temp_dir / "boxcar_sizes_test.cub"
        cube = ip.Cube()
        cube.set_dimensions(8, 6, 1)
        cube.set_pixel_type(ip.PixelType.Real)
        cube.create(str(cube_path))
        self.addCleanup(cube.close)

        # Initialize
        line_mgr = ip.LineManager(cube)
        line_mgr.begin()
        while not line_mgr.end():
            for i in range(len(line_mgr)):
                line_mgr[i] = 1.0
            cube.write(line_mgr)
            line_mgr.next()

        # Test rectangular boxcar (4x4)
        boxcar44 = ip.BoxcarManager(cube, 4, 4)
        self.assertEqual(boxcar44.sample_dimension(), 4)
        self.assertEqual(boxcar44.line_dimension(), 4)

        # Test asymmetric boxcar (3x5)
        boxcar35 = ip.BoxcarManager(cube, 3, 5)
        self.assertEqual(boxcar35.sample_dimension(), 3)
        self.assertEqual(boxcar35.line_dimension(), 5)

        # Verify both can iterate
        boxcar44.begin()
        self.assertFalse(boxcar44.end())
        cube.read(boxcar44)

        boxcar35.begin()
        self.assertFalse(boxcar35.end())
        cube.read(boxcar35)


if __name__ == "__main__":
    unittest.main()
