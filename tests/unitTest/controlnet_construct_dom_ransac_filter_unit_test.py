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


if __name__ == "__main__":
    unittest.main()
