"""Unit tests for DOM-space measure-level ControlNet RANSAC filtering."""

from __future__ import annotations

import unittest

from controlnet_construct.filter_controlnet_dom_ransac import (
    MeasureKey,
    MeasureRecord,
    group_measure_pairs_by_serial_pair,
)


class DomRansacFilterDataModelUnitTest(unittest.TestCase):
    def test_group_measure_pairs_by_serial_pair_emits_unordered_pairs_per_point(self):
        records = [
            MeasureRecord(MeasureKey(0, "P1", 0, "SERIAL_A"), 10.0, 20.0),
            MeasureRecord(MeasureKey(0, "P1", 1, "SERIAL_B"), 11.0, 21.0),
            MeasureRecord(MeasureKey(0, "P1", 2, "SERIAL_C"), 12.0, 22.0),
            MeasureRecord(MeasureKey(1, "P2", 0, "SERIAL_A"), 30.0, 40.0),
            MeasureRecord(MeasureKey(1, "P2", 1, "SERIAL_B"), 31.0, 41.0),
        ]

        grouped = group_measure_pairs_by_serial_pair(records)

        self.assertEqual(sorted(grouped), [
            ("SERIAL_A", "SERIAL_B"),
            ("SERIAL_A", "SERIAL_C"),
            ("SERIAL_B", "SERIAL_C"),
        ])
        self.assertEqual(len(grouped[("SERIAL_A", "SERIAL_B")]), 2)
        first = grouped[("SERIAL_A", "SERIAL_B")][0]
        self.assertEqual(first.left.key.point_id, "P1")
        self.assertEqual(first.right.key.point_id, "P1")


class FakeMeasure:
    def __init__(self, serial, sample, line, ignored=False):
        self.serial = serial
        self.sample = sample
        self.line = line
        self.ignored = ignored

    def get_cube_serial_number(self):
        return self.serial

    def get_sample(self):
        return self.sample

    def get_line(self):
        return self.line

    def is_ignored(self):
        return self.ignored

    def set_ignored(self, ignored):
        self.ignored = ignored


class FakePoint:
    def __init__(self, point_id, measures, ignored=False):
        self.point_id = point_id
        self.measures = measures
        self.ignored = ignored

    def get_id(self):
        return self.point_id

    def is_ignored(self):
        return self.ignored

    def get_num_measures(self):
        return len(self.measures)

    def get_measure(self, index):
        return self.measures[index]


class FakeNet:
    def __init__(self, points):
        self.points = points

    def get_num_points(self):
        return len(self.points)

    def get_point(self, index):
        return self.points[index]


class DomRansacFilterControlNetUnitTest(unittest.TestCase):
    def test_extract_active_measure_records_skips_ignored_points_and_measures(self):
        from controlnet_construct.filter_controlnet_dom_ransac import extract_active_measure_records

        net = FakeNet([
            FakePoint("P1", [FakeMeasure("A", 1, 2), FakeMeasure("B", 3, 4, ignored=True)]),
            FakePoint("P2", [FakeMeasure("A", 5, 6), FakeMeasure("B", 7, 8)], ignored=True),
            FakePoint("P3", [FakeMeasure("C", 9, 10), FakeMeasure("D", 11, 12)]),
        ])

        records = extract_active_measure_records(net)

        self.assertEqual([record.key.point_id for record in records], ["P1", "P3", "P3"])
        self.assertEqual(records[0].key.measure_index, 0)

    def test_apply_ignored_measures_marks_only_requested_measure_keys(self):
        from controlnet_construct.filter_controlnet_dom_ransac import apply_ignored_measures

        net = FakeNet([FakePoint("P1", [FakeMeasure("A", 1, 2), FakeMeasure("B", 3, 4)])])
        key = MeasureKey(point_index=0, point_id="P1", measure_index=1, serial="B")

        changed = apply_ignored_measures(net, {key})

        self.assertEqual(changed, 1)
        self.assertFalse(net.get_point(0).get_measure(0).is_ignored())
        self.assertTrue(net.get_point(0).get_measure(1).is_ignored())


class FakeClosableCube:
    def __init__(self, name):
        self.name = name
        self.closed = False

    def close(self):
        self.closed = True


class DomRansacFilterMappingUnitTest(unittest.TestCase):
    def test_read_aligned_cube_lists_rejects_mismatched_lengths(self):
        from _unit_test_support import temporary_directory
        from controlnet_construct.filter_controlnet_dom_ransac import read_aligned_cube_lists

        with temporary_directory() as temp_dir:
            original = temp_dir / "original.lis"
            dom = temp_dir / "dom.lis"
            original.write_text("a.cub\nb.cub\n", encoding="utf-8")
            dom.write_text("dom_a.cub\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "length"):
                read_aligned_cube_lists(original, dom)

    def test_lru_cache_closes_evicted_cubes(self):
        from controlnet_construct.filter_controlnet_dom_ransac import BoundedCubeCache

        opened = []

        def factory(path):
            cube = FakeClosableCube(path)
            opened.append(cube)
            return cube

        cache = BoundedCubeCache(max_open=2, factory=factory)
        first = cache.get("A")
        cache.get("B")
        cache.get("C")

        self.assertTrue(first.closed)
        self.assertFalse(opened[-1].closed)


class FakeCamera:
    def __init__(self, ok=True):
        self.ok = ok
        self.sample = None
        self.line = None

    def set_image(self, sample, line):
        self.sample = sample
        self.line = line
        return self.ok

    def universal_latitude(self):
        return self.line + 1.0

    def universal_longitude(self):
        return self.sample + 2.0


class FakeProjection:
    def __init__(self, ok=True):
        self.ok = ok
        self.latitude = None
        self.longitude = None

    def set_universal_ground(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude
        return self.ok

    def world_x(self):
        return self.longitude * 10.0

    def world_y(self):
        return self.latitude * 10.0


class DomRansacFilterProjectionUnitTest(unittest.TestCase):
    def test_project_measure_to_dom_returns_dom_pixel_coordinates(self):
        from controlnet_construct.filter_controlnet_dom_ransac import project_measure_to_dom

        record = MeasureRecord(MeasureKey(0, "P1", 0, "SERIAL_A"), sample=3.0, line=4.0)

        result = project_measure_to_dom(record, FakeCamera(), FakeProjection())

        self.assertEqual(result, (50.0, 50.0))

    def test_project_measure_to_dom_reports_camera_failure(self):
        from controlnet_construct.filter_controlnet_dom_ransac import project_measure_to_dom

        record = MeasureRecord(MeasureKey(0, "P1", 0, "SERIAL_A"), sample=3.0, line=4.0)

        result = project_measure_to_dom(record, FakeCamera(ok=False), FakeProjection())

        self.assertEqual(result.failure_stage, "camera_set_image_failed")


if __name__ == "__main__":
    unittest.main()
