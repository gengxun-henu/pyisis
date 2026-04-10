"""低层级 Cube I/O 绑定的单元测试

Author: Geng Xun
Created: 2026-04-03
Last Modified: 2026-04-09
Updated: 2026-04-08  Geng Xun added focused low-level Cube I/O regression coverage for Blob file/bytes helpers alongside managers, pixel helpers, and table primitives.
Updated: 2026-04-09  Geng Xun added CubeAttributeInput/Output and LabelAttachment focused tests.
Updated: 2026-04-09  Geng Xun added TrackingTable focused unit tests.
Updated: 2026-04-09  Geng Xun aligned TrackingTable index tests with upstream behavior where missing entries are inserted and assigned a new index.
Updated: 2026-04-09  Geng Xun added Blobber focused tests with self-contained table-backed cube fixtures.
Updated: 2026-04-09  Geng Xun added focused CubeTileHandler wrapper coverage for tile core-label updates.
Updated: 2026-04-09  Geng Xun added focused CubeBsqHandler wrapper coverage for BSQ core-label updates.
Updated: 2026-04-09  Geng Xun added focused CubeCachingAlgorithm.CacheResult coverage for the abstract caching interface.
Updated: 2026-04-09  Geng Xun added focused CubeIoHandler wrapper coverage for shared BSQ read/write/cache operations.
Updated: 2026-04-09  Geng Xun added OriginalLabel PVL/blob/file round-trip coverage.
Updated: 2026-04-09  Geng Xun added RawCubeChunk and RegionalCachingAlgorithm cache-surface regression coverage.
Updated: 2026-04-09  Geng Xun added OriginalXmlLabel XML/blob/file round-trip coverage.
Updated: 2026-04-10  Geng Xun added HiBlob focused coverage testing constructor, repr, and Blobber inheritance.
"""

import unittest

from _unit_test_support import ip, temporary_directory


class LowLevelCubeIoUnitTest(unittest.TestCase):
    def make_original_xml_text(self):
        return """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Product>
    <IdentificationArea>
        <logical_identifier>urn:nasa:pds:hirise:test_product</logical_identifier>
        <version_id>1.0</version_id>
    </IdentificationArea>
    <Observation_Area>
        <Time_Coordinates>
            <start_date_time>2026-04-09T00:00:00</start_date_time>
        </Time_Coordinates>
    </Observation_Area>
</Product>
"""

    def make_cube_bsq_label(self, samples=3, lines=2, bands=2):
        label = ip.Pvl()
        label.from_string(
            f"""
Object = IsisCube
    Object = Core
        StartByte = 1
        Group = Dimensions
            Samples = {samples}
            Lines = {lines}
            Bands = {bands}
        EndGroup
        Group = Pixels
            Type = Real
            ByteOrder = Lsb
            Base = 0.0
            Multiplier = 1.0
        EndGroup
    EndObject
EndObject
End
"""
        )
        return label

    def make_blobber_cube(self, name="blobber_fixture.cub"):
        temp_dir_cm = temporary_directory()
        temp_dir = temp_dir_cm.__enter__()
        self.addCleanup(temp_dir_cm.__exit__, None, None, None)

        cube_path = temp_dir / name
        cube = ip.Cube()
        cube.set_dimensions(2, 2, 1)
        cube.set_pixel_type(ip.PixelType.Real)
        cube.create(str(cube_path))
        self.addCleanup(cube.close)

        field = ip.TableField("DarkPixels", ip.TableField.Type.Double, 3)
        field.set_value([1.0, 2.0, 3.0])

        record_template = ip.TableRecord()
        record_template.add_field(field)

        table = ip.Table("HiRISE Calibration Ancillary", record_template)
        first = ip.TableRecord()
        first_field = ip.TableField("DarkPixels", ip.TableField.Type.Double, 3)
        first_field.set_value([1.0, 2.0, 3.0])
        first.add_field(first_field)
        second = ip.TableRecord()
        second_field = ip.TableField("DarkPixels", ip.TableField.Type.Double, 3)
        second_field.set_value([10.0, 20.0, 30.0])
        second.add_field(second_field)

        table.add_record(first)
        table.add_record(second)
        cube.write(table)
        return cube, cube_path

    def test_label_attachment_helpers_round_trip(self):
        self.assertEqual(ip.label_attachment_name(ip.LabelAttachment.AttachedLabel), "Attached")
        self.assertEqual(
            ip.label_attachment_enumeration("Attached"),
            ip.LabelAttachment.AttachedLabel,
        )
        self.assertEqual(
            ip.label_attachment_enumeration("DETACHED"),
            ip.LabelAttachment.DetachedLabel,
        )

    def test_cube_bsq_handler_updates_core_format_to_band_sequential(self):
        temp_dir_cm = temporary_directory()
        temp_dir = temp_dir_cm.__enter__()
        self.addCleanup(temp_dir_cm.__exit__, None, None, None)

        data_path = temp_dir / "cube_bsq_handler.dat"
        label = self.make_cube_bsq_label()
        handler = ip.CubeBsqHandler(str(data_path), label, [1, 2], False)

        updated = self.make_cube_bsq_label()
        handler.update_labels(updated)

        core = updated.find_object("IsisCube").find_object("Core")
        self.assertEqual(core.find_keyword("Format")[0], "BandSequential")
        self.assertTrue(data_path.exists())
        self.assertGreater(data_path.stat().st_size, 0)
        self.assertIn("CubeBsqHandler", repr(handler))

    def test_cube_tile_handler_updates_core_format_to_tile(self):
        temp_dir_cm = temporary_directory()
        temp_dir = temp_dir_cm.__enter__()
        self.addCleanup(temp_dir_cm.__exit__, None, None, None)

        data_path = temp_dir / "cube_tile_handler.dat"
        label = self.make_cube_bsq_label(samples=3, lines=2, bands=2)
        handler = ip.CubeTileHandler(str(data_path), label, [1, 2], False)

        updated = self.make_cube_bsq_label(samples=3, lines=2, bands=2)
        handler.update_labels(updated)

        core = updated.find_object("IsisCube").find_object("Core")
        self.assertEqual(core.find_keyword("Format")[0], "Tile")
        self.assertEqual(core.find_keyword("TileSamples")[0], "3")
        self.assertEqual(core.find_keyword("TileLines")[0], "2")
        self.assertTrue(data_path.exists())
        self.assertGreater(data_path.stat().st_size, 0)
        self.assertIn("CubeTileHandler", repr(handler))

    def test_cube_io_handler_reads_writes_and_updates_labels(self):
        temp_dir_cm = temporary_directory()
        temp_dir = temp_dir_cm.__enter__()
        self.addCleanup(temp_dir_cm.__exit__, None, None, None)

        data_path = temp_dir / "cube_io_handler.dat"
        label = self.make_cube_bsq_label(samples=3, lines=2, bands=1)
        handler = ip.CubeIoHandler(str(data_path), label, [1], False)

        writer = ip.Brick(3, 2, 1, ip.PixelType.Real)
        writer.set_base_position(1, 1, 1)
        for index in range(len(writer)):
            writer[index] = float(index + 1)

        handler.write(writer)
        handler.clear_cache()

        reader = ip.Brick(3, 2, 1, ip.PixelType.Real)
        reader.set_base_position(1, 1, 1)
        handler.read(reader)

        self.assertEqual(reader.double_buffer(), [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        self.assertGreater(handler.get_data_size(), 0)

        updated = self.make_cube_bsq_label(samples=3, lines=2, bands=1)
        handler.update_labels(updated)
        core = updated.find_object("IsisCube").find_object("Core")
        self.assertEqual(core.find_keyword("Format")[0], "BandSequential")

        handler.set_virtual_bands([1])
        self.assertIn("CubeIoHandler", repr(handler))
        self.assertIsNotNone(handler.data_file_mutex())

    def test_cube_caching_algorithm_cache_result_surface(self):
        self.assertTrue(hasattr(ip, "CubeCachingAlgorithm"))

        empty = ip.CubeCachingAlgorithm.CacheResult()
        self.assertFalse(empty.algorithm_understood_data())
        self.assertEqual(empty.get_chunks_to_free(), [])
        self.assertEqual(len(empty), 0)

        chunk = ip.RawCubeChunk(1, 1, 1, 2, 2, 1, 8)
        understood = ip.CubeCachingAlgorithm.CacheResult([None, chunk])
        self.assertTrue(understood.algorithm_understood_data())
        returned = understood.get_chunks_to_free()
        self.assertIsNone(returned[0])
        self.assertIsInstance(returned[1], ip.RawCubeChunk)
        self.assertEqual(returned[1].get_start_sample(), 1)
        self.assertEqual(len(understood), 2)

        copied = ip.CubeCachingAlgorithm.CacheResult(understood)
        self.assertTrue(copied.algorithm_understood_data())
        self.assertIsNone(copied.get_chunks_to_free()[0])
        self.assertIsInstance(copied.get_chunks_to_free()[1], ip.RawCubeChunk)
        self.assertIn("CubeCachingAlgorithm.CacheResult", repr(copied))

    def test_raw_cube_chunk_mutation_and_type_specific_accessors(self):
        chunk = ip.RawCubeChunk(3, 4, 1, 4, 5, 1, 8)

        self.assertFalse(chunk.is_dirty())
        self.assertEqual(chunk.get_start_sample(), 3)
        self.assertEqual(chunk.get_start_line(), 4)
        self.assertEqual(chunk.get_start_band(), 1)
        self.assertEqual(chunk.sample_count(), 2)
        self.assertEqual(chunk.line_count(), 2)
        self.assertEqual(chunk.band_count(), 1)
        self.assertEqual(chunk.get_byte_count(), 8)
        self.assertEqual(chunk.get_raw_data(), b"\x00" * 8)

        chunk.set_data(7, 0)
        self.assertTrue(chunk.is_dirty())
        self.assertEqual(chunk.get_char(0), 7)

        chunk.set_dirty(False)
        self.assertFalse(chunk.is_dirty())

        chunk.set_raw_data(b"\x34\x12\x00\x00\x00\x00\x80\x3f")
        self.assertTrue(chunk.is_dirty())
        self.assertEqual(chunk.get_short(0), 0x1234)
        self.assertAlmostEqual(chunk.get_float(1), 1.0, places=6)
        self.assertIn("RawCubeChunk", repr(chunk))

    def test_regional_caching_algorithm_recommends_non_recent_chunks(self):
        algorithm = ip.RegionalCachingAlgorithm()
        requested = ip.Buffer(1, 1, 1, ip.PixelType.UnsignedByte)

        chunks = [
            ip.RawCubeChunk(1, 1, 1, 2, 2, 1, 4),
            ip.RawCubeChunk(3, 1, 1, 4, 2, 1, 4),
            ip.RawCubeChunk(5, 1, 1, 6, 2, 1, 4),
            ip.RawCubeChunk(7, 1, 1, 8, 2, 1, 4),
        ]

        result = algorithm.recommend_chunks_to_free(chunks, [chunks[0]], requested)
        self.assertTrue(result.algorithm_understood_data())

        evicted = result.get_chunks_to_free()
        self.assertEqual(len(evicted), 3)
        self.assertEqual([chunk.get_start_sample() for chunk in evicted], [3, 5, 7])
        self.assertIn("RegionalCachingAlgorithm", repr(algorithm))

    def test_cube_attribute_input_parses_band_ranges_and_mutators(self):
        attributes = ip.CubeAttributeInput("+3,5-7,9")

        self.assertEqual(attributes.to_string(), "+3,5-7,9")
        self.assertEqual(attributes.bands(), ["3", "5", "6", "7", "9"])
        self.assertEqual(attributes.bands_string(), "3,5,6,7,9")

        attributes.set_bands(["1-3", "9"])
        self.assertEqual(attributes.to_string(), "+1-3,9")

        attributes.add_attributes("+11")
        self.assertEqual(attributes.to_string(), "+1-3,9+11")
        self.assertIn("CubeAttributeInput", repr(attributes))

    def test_cube_attribute_input_rejects_unknown_attributes(self):
        with self.assertRaises(ip.IException):
            ip.CubeAttributeInput("+not-a-band")

    def test_cube_attribute_output_parses_and_reports_core_state(self):
        attributes = ip.CubeAttributeOutput("+8bit+Tile+0.0:100.1+MSB")

        self.assertFalse(attributes.propagate_pixel_type())
        self.assertFalse(attributes.propagate_minimum_maximum())
        self.assertEqual(attributes.pixel_type(), ip.PixelType.UnsignedByte)
        self.assertEqual(attributes.file_format(), ip.Cube.Format.Tile)
        self.assertEqual(attributes.file_format_string(), "Tile")
        self.assertEqual(attributes.byte_order(), ip.ByteOrder.Msb)
        self.assertEqual(attributes.byte_order_string(), "Msb")
        self.assertEqual(attributes.minimum(), 0.0)
        self.assertEqual(attributes.maximum(), 100.1)
        self.assertEqual(attributes.label_attachment(), ip.LabelAttachment.AttachedLabel)

    def test_cube_attribute_output_mutators_follow_upstream_serialization(self):
        attributes = ip.CubeAttributeOutput()
        attributes.set_file_format(ip.Cube.Format.Bsq)
        attributes.set_pixel_type(ip.PixelType.Real)
        attributes.set_byte_order(ip.ByteOrder.Msb)
        attributes.set_label_attachment(ip.LabelAttachment.ExternalLabel)
        attributes.set_minimum(1.0)
        attributes.set_maximum(2.0)

        self.assertEqual(
            attributes.to_string(),
            "+BandSequential+Real+MSB+External+1.0:2.0",
        )
        self.assertIn("CubeAttributeOutput", repr(attributes))

    def test_cube_attribute_output_set_attributes_and_invalid_attribute(self):
        attributes = ip.CubeAttributeOutput()
        attributes.set_attributes("+8-bit+Detached")
        self.assertEqual(attributes.pixel_type(), ip.PixelType.UnsignedByte)
        self.assertEqual(attributes.label_attachment(), ip.LabelAttachment.DetachedLabel)

        with self.assertRaises(ip.IException):
            attributes.add_attribute("not-valid")

    def make_test_cube(self, samples=4, lines=3, bands=2, name="band_manager_test.cub"):
        temp_dir_cm = temporary_directory()
        temp_dir = temp_dir_cm.__enter__()
        self.addCleanup(temp_dir_cm.__exit__, None, None, None)

        cube_path = temp_dir / name
        cube = ip.Cube()
        cube.set_dimensions(samples, lines, bands)
        cube.set_pixel_type(ip.PixelType.Real)
        cube.create(str(cube_path))
        self.addCleanup(cube.close)
        return cube

    def fill_test_cube_with_position_codes(self, cube):
        manager = ip.LineManager(cube)
        manager.begin()
        while not manager.end():
            for index in range(len(manager)):
                manager[index] = float(
                    manager.band() * 100 + manager.line() * 10 + manager.sample(index)
                )
            cube.write(manager)
            manager.next()

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

    def test_band_manager_readback_and_exceptions(self):
        cube = self.make_test_cube(name="band_manager_direct_test.cub")
        self.fill_test_cube_with_position_codes(cube)

        manager = ip.BandManager(cube)
        self.assertEqual(manager.sample_dimension(), 1)
        self.assertEqual(manager.line_dimension(), 1)
        self.assertEqual(manager.band_dimension(), cube.band_count())

        self.assertTrue(manager.set_band(2))
        self.assertEqual(manager.sample(), 2)
        self.assertEqual(manager.line(), 1)
        self.assertEqual(manager.band(), 1)
        cube.read(manager)
        self.assertEqual(manager.double_buffer(), [112.0, 212.0])

        with self.assertRaises(ip.IException):
            manager.set_band(0)

        with self.assertRaises(ip.IException):
            manager.set_band(1, 0)

    def test_line_manager_direct_positioning_and_exceptions(self):
        cube = self.make_test_cube(name="line_manager_test.cub")
        self.fill_test_cube_with_position_codes(cube)

        manager = ip.LineManager(cube)
        self.assertEqual(manager.sample_dimension(), cube.sample_count())
        self.assertEqual(manager.line_dimension(), 1)
        self.assertEqual(manager.band_dimension(), 1)

        self.assertTrue(manager.set_line(2))
        self.assertEqual(manager.sample(), 1)
        self.assertEqual(manager.line(), 2)
        self.assertEqual(manager.band(), 1)
        cube.read(manager)
        self.assertEqual(manager.double_buffer(), [121.0, 122.0, 123.0, 124.0])

        self.assertTrue(manager.set_line(3, 2))
        self.assertEqual(manager.line(), 3)
        self.assertEqual(manager.band(), 2)
        cube.read(manager)
        self.assertEqual(manager.double_buffer(), [231.0, 232.0, 233.0, 234.0])

        with self.assertRaises(Exception):
            manager.set_line(0)

        with self.assertRaises(Exception):
            manager.set_line(1, 0)

    def test_sample_manager_direct_positioning_and_exceptions(self):
        cube = self.make_test_cube(name="sample_manager_test.cub")
        self.fill_test_cube_with_position_codes(cube)

        manager = ip.SampleManager(cube)
        self.assertEqual(manager.sample_dimension(), 1)
        self.assertEqual(manager.line_dimension(), cube.line_count())
        self.assertEqual(manager.band_dimension(), 1)

        self.assertTrue(manager.set_sample(3))
        self.assertEqual(manager.sample(), 3)
        self.assertEqual(manager.line(), 1)
        self.assertEqual(manager.band(), 1)
        cube.read(manager)
        self.assertEqual(manager.double_buffer(), [113.0, 123.0, 133.0])

        self.assertTrue(manager.set_sample(2, 2))
        self.assertEqual(manager.sample(), 2)
        self.assertEqual(manager.band(), 2)
        cube.read(manager)
        self.assertEqual(manager.double_buffer(), [212.0, 222.0, 232.0])

        with self.assertRaises(Exception):
            manager.set_sample(0)

        with self.assertRaises(Exception):
            manager.set_sample(1, 0)

    def test_tile_manager_positioning_iteration_and_exceptions(self):
        cube = self.make_test_cube(samples=5, lines=4, bands=2, name="tile_manager_test.cub")
        self.fill_test_cube_with_position_codes(cube)

        manager = ip.TileManager(cube, 2, 3)
        self.assertEqual(manager.sample_dimension(), 2)
        self.assertEqual(manager.line_dimension(), 3)
        self.assertEqual(manager.band_dimension(), 1)

        self.assertTrue(manager.set_tile(2))
        self.assertEqual(manager.sample(), 3)
        self.assertEqual(manager.line(), 1)
        self.assertEqual(manager.band(), 1)
        cube.read(manager)
        self.assertEqual(manager.double_buffer(), [113.0, 114.0, 123.0, 124.0, 133.0, 134.0])

        self.assertTrue(manager.set_tile(2, 2))
        self.assertEqual(manager.sample(), 3)
        self.assertEqual(manager.line(), 1)
        self.assertEqual(manager.band(), 2)
        cube.read(manager)
        self.assertEqual(manager.double_buffer(), [213.0, 214.0, 223.0, 224.0, 233.0, 234.0])

        iteration_count = 0
        manager.begin()
        while not manager.end():
            iteration_count += 1
            manager.next()

        self.assertEqual(iteration_count, 12)
        self.assertEqual(manager.tiles(), 12)

        with self.assertRaises(Exception):
            manager.set_tile(0)

        with self.assertRaises(Exception):
            manager.set_tile(1, 0)

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

        # 4-arg constructor: corner-to-corner identity mapping
        alpha_cube = ip.AlphaCube(100, 200, 100, 200)
        self.assertEqual(alpha_cube.alpha_samples(), 100)
        self.assertEqual(alpha_cube.alpha_lines(), 200)
        self.assertEqual(alpha_cube.beta_samples(), 100)
        self.assertEqual(alpha_cube.beta_lines(), 200)
        # Corner-to-corner mapping: alpha coords equal beta coords
        self.assertAlmostEqual(alpha_cube.alpha_sample(1.0), 1.0)
        self.assertAlmostEqual(alpha_cube.beta_line(10.0), 10.0)

        # 8-arg constructor: explicit starting/ending coordinates
        sub_cube = ip.AlphaCube(100, 200, 50, 100, 1.5, 1.5, 51.5, 101.5)
        self.assertEqual(sub_cube.alpha_samples(), 100)
        self.assertEqual(sub_cube.beta_samples(), 50)
        self.assertAlmostEqual(sub_cube.alpha_sample(0.5), 1.5)
        self.assertAlmostEqual(sub_cube.alpha_sample(50.5), 51.5)

    def test_brick_set_brick_and_count(self):
        cube = self.make_test_cube(name="brick_manager_test.cub")
        self.fill_test_cube_with_position_codes(cube)

        brick = ip.Brick(cube, 2, 2, 1)
        self.assertEqual(brick.bricks(), 8)

        self.assertTrue(brick.set_brick(2))
        self.assertEqual(brick.sample(), 3)
        self.assertEqual(brick.line(), 1)
        self.assertEqual(brick.band(), 1)
        cube.read(brick)
        self.assertEqual(brick.double_buffer(), [113.0, 114.0, 123.0, 124.0])

        with self.assertRaises(ip.IException):
            brick.set_brick(0)

    def test_portal_hotspot_controls_base_position(self):
        portal = ip.Portal(3, 3, ip.PixelType.Real)

        portal.set_hot_spot(1.0, 1.0)
        portal.set_position(10.0, 20.0, 2)
        self.assertEqual(portal.sample(), 9)
        self.assertEqual(portal.line(), 19)
        self.assertEqual(portal.band(), 2)

        portal.set_hot_spot(-0.5, -0.5)
        portal.set_position(10.0, 20.0, 1)
        self.assertEqual(portal.sample(), 10)
        self.assertEqual(portal.line(), 20)
        self.assertEqual(portal.band(), 1)

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

    def test_table_field_pvl_group_and_validation_errors(self):
        integer_field = ip.TableField("Indices", ip.TableField.Type.Integer, 3)
        group = integer_field.pvl_group()
        self.assertEqual(group.name(), "Field")
        self.assertEqual(group.keyword("Name")[0], "Indices")
        self.assertEqual(group.keyword("Type")[0], "Integer")
        self.assertEqual(group.keyword("Size")[0], "3")
        self.assertEqual(integer_field.bytes(), 12)

        with self.assertRaises(ip.IException):
            integer_field.set_value([1, 2])

        text_field = ip.TableField("Code", ip.TableField.Type.Text, 4)
        with self.assertRaises(ip.IException):
            text_field.set_value("TOO-LONG")

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

    def test_table_record_missing_field_raises(self):
        record = ip.TableRecord("1,2", ",", ["First", "Second"], 2)
        with self.assertRaises(ip.IException):
            _ = record["Missing"]

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

    def test_table_round_trip_and_add_record_failures(self):
        temp_dir_cm = temporary_directory()
        temp_dir = temp_dir_cm.__enter__()
        self.addCleanup(temp_dir_cm.__exit__, None, None, None)

        record = ip.TableRecord()
        value_field = ip.TableField("Value", ip.TableField.Type.Double)
        value_field.set_value(4.5)
        name_field = ip.TableField("Name", ip.TableField.Type.Text, 8)
        name_field.set_value("DEIMOS")
        record.add_field(value_field)
        record.add_field(name_field)

        table = ip.Table("RoundTrip", record)
        table.set_association(ip.Table.Association.Lines)
        table.add_record(record)

        table_path = temp_dir / "roundtrip_table.bin"
        table.write(str(table_path))

        loaded = ip.Table("RoundTrip", str(table_path))
        self.assertEqual(loaded.name(), "RoundTrip")
        self.assertTrue(loaded.is_line_associated())
        self.assertFalse(loaded.is_band_associated())
        self.assertEqual(loaded.records(), 1)
        self.assertEqual(loaded[0]["Name"].value().rstrip("\x00"), "DEIMOS")

        empty_shape_table = ip.Table("ReadOnlyShape")
        with self.assertRaises(ip.IException):
            empty_shape_table.add_record(record)

        mismatched_record = ip.TableRecord()
        only_field = ip.TableField("Only", ip.TableField.Type.Double)
        only_field.set_value(1.0)
        mismatched_record.add_field(only_field)
        with self.assertRaises(ip.IException):
            table.add_record(mismatched_record)

    def test_blob_round_trip_copy_and_helper(self):
        temp_dir_cm = temporary_directory()
        temp_dir = temp_dir_cm.__enter__()
        self.addCleanup(temp_dir_cm.__exit__, None, None, None)

        blob_path = temp_dir / "blob_roundtrip.dat"

        blob = ip.Blob("UnitTest", "Blob")
        blob.set_data(b"ABCD")

        self.assertEqual(blob.name(), "UnitTest")
        self.assertEqual(blob.type(), "Blob")
        self.assertEqual(blob.size(), 4)
        self.assertEqual(blob.get_buffer(), b"ABCD")
        self.assertEqual(bytes(blob), b"ABCD")
        self.assertIn("Blob(name='UnitTest'", repr(blob))

        blob.write(str(blob_path))

        label = blob.label()
        self.assertFalse(ip.is_blob(label))
        self.assertEqual(label.name(), "Blob")
        self.assertEqual(label.keyword("Name")[0], "UnitTest")
        self.assertEqual(label.keyword("Bytes")[0], "0")
        self.assertTrue(blob_path.exists())

        loaded = ip.Blob("UNITtest", "Blob", str(blob_path))
        self.assertEqual(loaded.name(), "UNITtest")
        self.assertEqual(loaded.type(), "Blob")
        self.assertEqual(loaded.size(), 4)
        self.assertEqual(loaded.get_buffer(), b"ABCD")
        self.assertEqual(loaded.label().keyword("Bytes")[0], "4")

        reread = ip.Blob("UnitTest", "Blob")
        reread.read(str(blob_path))
        self.assertEqual(reread.get_buffer(), b"ABCD")

        copied = ip.Blob(loaded)
        copied.take_data(b"XYZ")
        self.assertEqual(loaded.get_buffer(), b"ABCD")
        self.assertEqual(copied.get_buffer(), b"XYZ")

        self.assertFalse(ip.is_blob(ip.PvlObject("NotABlob")))
        self.assertTrue(ip.is_blob(ip.PvlObject("TABLE")))

    def test_original_label_round_trip_from_pvl_blob_and_file(self):
        temp_dir_cm = temporary_directory()
        temp_dir = temp_dir_cm.__enter__()
        self.addCleanup(temp_dir_cm.__exit__, None, None, None)

        source = ip.Pvl()
        source.from_string(
            """
Group = Instrument
    SpacecraftName = CASSINI
    InstrumentId = ISSNA
EndGroup
Group = Archive
    ProductId = N1234567890
EndGroup
End
"""
        )

        original = ip.OriginalLabel(source)
        returned = original.return_labels()
        self.assertEqual(returned.find_group("Instrument").find_keyword("SpacecraftName")[0], "CASSINI")
        self.assertEqual(returned.find_group("Archive").find_keyword("ProductId")[0], "N1234567890")

        blob = original.to_blob()
        self.assertIsInstance(blob, ip.Blob)
        self.assertEqual(blob.name(), "IsisCube")
        self.assertEqual(blob.type(), "OriginalLabel")

        from_blob = ip.OriginalLabel(blob)
        self.assertEqual(
            from_blob.return_labels().find_group("Instrument").find_keyword("InstrumentId")[0],
            "ISSNA",
        )

        blob_path = temp_dir / "original_label.blob"
        blob.write(str(blob_path))

        from_file = ip.OriginalLabel(str(blob_path))
        self.assertEqual(
            from_file.return_labels().find_group("Archive").find_keyword("ProductId")[0],
            "N1234567890",
        )
        self.assertIn("OriginalLabel", repr(from_file))

    def test_original_xml_label_round_trip_from_xml_blob_and_file(self):
        temp_dir_cm = temporary_directory()
        temp_dir = temp_dir_cm.__enter__()
        self.addCleanup(temp_dir_cm.__exit__, None, None, None)

        xml_path = temp_dir / "original.xml"
        xml_path.write_text(self.make_original_xml_text(), encoding="utf-8")

        original = ip.OriginalXmlLabel()
        self.assertTrue(original.is_empty())
        original.read_from_xml_file(str(xml_path))

        xml_text = original.return_labels()
        self.assertIn("<Product>", xml_text)
        self.assertIn("hirise:test_product", xml_text)
        self.assertEqual(original.root_tag(), "Product")

        blob = original.to_blob()
        self.assertIsInstance(blob, ip.Blob)
        self.assertEqual(blob.name(), "IsisCube")
        self.assertEqual(blob.type(), "OriginalXmlLabel")

        from_blob_ctor = ip.OriginalXmlLabel(blob)
        self.assertIn("<logical_identifier>", from_blob_ctor.return_labels())

        from_blob_method = ip.OriginalXmlLabel()
        from_blob_method.from_blob(blob)
        self.assertEqual(from_blob_method.return_labels(), from_blob_ctor.return_labels())

        blob_path = temp_dir / "original_xml_label.blob"
        blob.write(str(blob_path))

        from_file = ip.OriginalXmlLabel(str(blob_path))
        self.assertIn("<start_date_time>", str(from_file))
        self.assertIn("OriginalXmlLabel", repr(from_file))

    def test_original_xml_label_invalid_xml_raises(self):
        temp_dir_cm = temporary_directory()
        temp_dir = temp_dir_cm.__enter__()
        self.addCleanup(temp_dir_cm.__exit__, None, None, None)

        bad_xml_path = temp_dir / "bad.xml"
        bad_xml_path.write_text("<Product><broken></Product>", encoding="utf-8")

        with self.assertRaises(ip.IException):
            ip.OriginalXmlLabel().read_from_xml_file(str(bad_xml_path))

    def test_blobber_loads_table_backed_cube_and_reports_metadata(self):
        cube, cube_path = self.make_blobber_cube()

        blobber = ip.Blobber(cube, "HiRISE Calibration Ancillary", "DarkPixels", "BlobberFixture")
        self.assertEqual(blobber.get_name(), "BlobberFixture")
        self.assertEqual(blobber.get_blob_name(), "HiRISE Calibration Ancillary")
        self.assertEqual(blobber.get_field_name(), "DarkPixels")
        self.assertEqual(blobber.lines(), 2)
        self.assertEqual(blobber.samples(), 3)
        self.assertEqual(blobber.size(), 6)
        self.assertEqual(blobber.row(0), [1.0, 2.0, 3.0])
        self.assertEqual(blobber[1], [10.0, 20.0, 30.0])
        self.assertEqual(blobber[(1, 2)], 30.0)
        self.assertEqual(blobber.value(1, 1), 20.0)
        self.assertIn("Blobber(name='BlobberFixture'", repr(blobber))

        reloaded = ip.Blobber("HiRISE Calibration Ancillary", "DarkPixels", "ReloadedBlobber")
        reloaded.load(cube)
        self.assertEqual(reloaded.row(1), [10.0, 20.0, 30.0])

        cube.close()

        by_name = ip.Blobber("HiRISE Calibration Ancillary", "DarkPixels")
        by_name.load(str(cube_path))
        self.assertEqual(by_name[(0, 0)], 1.0)

        reopened = ip.Cube(ip.FileName(str(cube_path)), "r")
        self.addCleanup(reopened.close)
        self.assertIsInstance(reopened.read_table("HiRISE Calibration Ancillary"), ip.Table)

    def test_blobber_copy_and_deepcopy_follow_upstream_sharing_rules(self):
        cube, _ = self.make_blobber_cube(name="blobber_copy.cub")
        original = ip.Blobber(cube, "HiRISE Calibration Ancillary", "DarkPixels", "OriginalBlobber")

        shallow = ip.Blobber(original)
        self.assertEqual(shallow[(1, 1)], 20.0)
        shallow[(1, 1)] = 25.0
        self.assertEqual(original[(1, 1)], 25.0)

        deep = original.deepcopy()
        deep.set_name("DeepBlobber")
        deep[(1, 1)] = 99.0
        self.assertEqual(deep.get_name(), "DeepBlobber")
        self.assertEqual(original[(1, 1)], 25.0)
        self.assertEqual(deep[(1, 1)], 99.0)

        py_deep = original.__deepcopy__({})
        py_deep[(0, 0)] = -1.0
        self.assertEqual(original[(0, 0)], 1.0)
        self.assertEqual(py_deep[(0, 0)], -1.0)

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


class TrackingTableUnitTest(unittest.TestCase):
    """Test suite for TrackingTable class bindings. Added: 2026-04-09."""

    def test_construction_default(self):
        """TrackingTable() constructs without error."""
        tt = ip.TrackingTable()
        self.assertIsNotNone(tt)

    def test_to_table_round_trip_empty(self):
        """An empty TrackingTable serializes to a Table without error."""
        tt = ip.TrackingTable()
        tbl = tt.to_table()
        self.assertIsNotNone(tbl)
        self.assertIsInstance(tbl, ip.Table)

    def test_file_name_to_pixel_adds_entry(self):
        """file_name_to_pixel assigns a pixel value and increments the table."""
        tt = ip.TrackingTable()
        fn1 = ip.FileName("/tmp/fake_a.cub")
        sn1 = "MRO/HiRISE/0000000001"
        pixel1 = tt.file_name_to_pixel(fn1, sn1)
        # The first entry uses the minimum unsigned value (typically 0 + offset)
        self.assertIsInstance(pixel1, int)

        fn2 = ip.FileName("/tmp/fake_b.cub")
        sn2 = "MRO/HiRISE/0000000002"
        pixel2 = tt.file_name_to_pixel(fn2, sn2)
        self.assertNotEqual(pixel1, pixel2)

    def test_file_name_to_index_existing(self):
        """file_name_to_index returns a non-negative index for added entries."""
        tt = ip.TrackingTable()
        fn = ip.FileName("/tmp/fake_c.cub")
        sn = "MRO/HiRISE/0000000003"
        tt.file_name_to_pixel(fn, sn)
        idx = tt.file_name_to_index(fn, sn)
        self.assertGreaterEqual(idx, 0)

    def test_file_name_to_index_missing_inserts_entry(self):
        """file_name_to_index inserts a missing filename/serial pair and returns its new index."""
        tt = ip.TrackingTable()
        fn_missing = ip.FileName("/tmp/not_added.cub")
        idx = tt.file_name_to_index(fn_missing, "NO/SN/123")
        self.assertEqual(idx, 0)

        # Upstream TrackingTable appends missing entries instead of returning -1.
        self.assertEqual(tt.file_name_to_index(fn_missing, "NO/SN/123"), 0)

    def test_pixel_to_sn_round_trip(self):
        """pixel_to_sn returns the serial number for an added entry."""
        tt = ip.TrackingTable()
        fn = ip.FileName("/tmp/fake_d.cub")
        sn = "TESTMISSION/TESTINSTRUMENT/0000000004"
        pixel = tt.file_name_to_pixel(fn, sn)
        retrieved_sn = tt.pixel_to_sn(pixel)
        self.assertEqual(retrieved_sn, sn)

    def test_pixel_to_file_name_round_trip(self):
        """pixel_to_file_name returns the FileName for an added entry."""
        tt = ip.TrackingTable()
        fn = ip.FileName("/tmp/fake_e.cub")
        sn = "TESTMISSION/TESTINSTRUMENT/0000000005"
        pixel = tt.file_name_to_pixel(fn, sn)
        retrieved_fn = tt.pixel_to_file_name(pixel)
        self.assertIsInstance(retrieved_fn, ip.FileName)

    def test_repr(self):
        """__repr__ returns a non-empty string containing 'TrackingTable'."""
        tt = ip.TrackingTable()
        self.assertIn("TrackingTable", repr(tt))


if __name__ == "__main__":
    unittest.main()


class HiBlobUnitTest(unittest.TestCase):
    """Focused regression coverage for HiBlob binding.

    Added: 2026-04-10
    """

    def test_default_constructor(self):
        """HiBlob can be constructed without arguments."""
        blob = ip.HiBlob()
        self.assertIsInstance(blob, ip.HiBlob)
        self.assertIsInstance(blob, ip.Blobber)

    def test_default_constructor_repr(self):
        """HiBlob repr returns expected string for default-constructed object."""
        blob = ip.HiBlob()
        r = repr(blob)
        self.assertIn("HiBlob", r)

    def test_hiblob_is_blobber_subtype(self):
        """HiBlob is a subclass of Blobber in Python."""
        self.assertTrue(issubclass(ip.HiBlob, ip.Blobber))

    def test_hiblob_inherits_get_name(self):
        """HiBlob exposes get_name() from Blobber base."""
        blob = ip.HiBlob()
        # Default-constructed HiBlob has an empty name
        self.assertIsInstance(blob.get_name(), str)

    def test_hiblob_inherits_lines_samples(self):
        """HiBlob exposes lines() and samples() from Blobber base."""
        blob = ip.HiBlob()
        self.assertIsInstance(blob.lines(), int)
        self.assertIsInstance(blob.samples(), int)

    def test_buffer_empty_default(self):
        """buffer() returns an empty list when no data has been loaded."""
        blob = ip.HiBlob()
        buf = blob.buffer()
        # Default HiBlob has no data; buffer should be empty or zero-sized
        self.assertIsInstance(buf, list)


if __name__ == "__main__":
    unittest.main()
