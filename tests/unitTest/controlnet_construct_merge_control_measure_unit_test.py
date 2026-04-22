"""Focused tests for post-merge ControlNet duplicate-measure collapsing.

Author: Geng Xun
Created: 2026-04-21
Last Modified: 2026-04-21
Updated: 2026-04-21  Geng Xun added unit and lightweight integration coverage for rounded per-image ControlNet measure deduplication after cnetmerge-style network assembly.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import unittest


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import ip, temporary_directory, workspace_test_data_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.merge_control_measure import (
    _default_output_path,
    merge_control_measure_file,
    merge_controlnet_duplicate_points_in_place,
    main as merge_control_measure_main,
)


LEFT_CUBE_PATH = workspace_test_data_path("mosrange", "EN0108828322M_iof.cub")
MIDDLE_CUBE_PATH = workspace_test_data_path("mosrange", "EN0108828327M_iof.cub")
RIGHT_CUBE_PATH = workspace_test_data_path("mosrange", "EN0108828332M_iof.cub")


def _make_measure(serial_number: str, sample: float, line: float) -> ip.ControlMeasure:
    measure = ip.ControlMeasure()
    measure.set_cube_serial_number(serial_number)
    measure.set_coordinate(sample, line)
    measure.set_type(ip.ControlMeasure.MeasureType.Manual)
    return measure


def _make_point(
    point_id: str,
    measures: list[ip.ControlMeasure],
    *,
    point_type: ip.ControlPoint.PointType = ip.ControlPoint.PointType.Free,
    edit_lock: bool = False,
    ignored: bool = False,
) -> ip.ControlPoint:
    point = ip.ControlPoint(point_id)
    point.set_type(point_type)
    point.set_edit_lock(edit_lock)
    point.set_ignored(ignored)
    for measure in measures:
        point.add_measure(measure)
    point.set_ref_measure(0)
    return point


def _make_serial_lookup(*serial_numbers: str) -> dict[str, str]:
    return {serial_number: f"/synthetic/{serial_number}.cub" for serial_number in serial_numbers}


class ControlNetConstructMergeControlMeasureUnitTest(unittest.TestCase):
    def test_default_output_path_appends_merged_measure_suffix(self):
        input_path = Path("/tmp/example/control.net")
        self.assertEqual(
            _default_output_path(input_path),
            Path("/tmp/example/control_merged_measures.net"),
        )

    def test_merge_controlnet_duplicate_points_in_place_merges_transitively_and_keeps_first_point_properties(self):
        serial_a = "SN-A"
        serial_b = "SN-B"
        serial_c = "SN-C"
        serial_d = "SN-D"

        net = ip.ControlNet()
        net.add_point(
            _make_point(
                "P1",
                [
                    _make_measure(serial_a, 10.04, 20.04),
                    _make_measure(serial_b, 30.00, 40.00),
                ],
                point_type=ip.ControlPoint.PointType.Fixed,
                edit_lock=True,
            )
        )
        net.add_point(
            _make_point(
                "P2",
                [
                    _make_measure(serial_a, 10.03, 20.02),
                    _make_measure(serial_c, 50.04, 60.04),
                ],
            )
        )
        net.add_point(
            _make_point(
                "P3",
                [
                    _make_measure(serial_c, 50.03, 60.03),
                    _make_measure(serial_d, 70.04, 80.04),
                ],
            )
        )

        summary = merge_controlnet_duplicate_points_in_place(
            net,
            _make_serial_lookup(serial_a, serial_b, serial_c, serial_d),
            decimals=1,
        )

        self.assertEqual(summary["point_count_before"], 3)
        self.assertEqual(summary["point_count_after"], 1)
        self.assertEqual(summary["measure_count_before"], 6)
        self.assertEqual(summary["measure_count_after"], 4)
        self.assertEqual(summary["duplicate_point_count"], 2)
        self.assertEqual(summary["merged_point_count"], 2)
        self.assertEqual(summary["matched_measure_count"], 2)
        self.assertEqual(summary["merged_measure_candidate_count"], 4)
        self.assertEqual(summary["added_measure_count"], 2)
        self.assertEqual(summary["skipped_existing_serial_count"], 2)
        self.assertEqual(summary["merged_point_ids"], ("P2", "P3"))

        self.assertTrue(net.contains_point("P1"))
        self.assertFalse(net.contains_point("P2"))
        self.assertFalse(net.contains_point("P3"))

        canonical_point = net.get_point("P1")
        self.assertEqual(canonical_point.get_type(), ip.ControlPoint.PointType.Fixed)
        self.assertTrue(canonical_point.is_edit_locked())
        self.assertCountEqual(
            [measure.get_cube_serial_number() for measure in canonical_point.get_measures()],
            [serial_a, serial_b, serial_c, serial_d],
        )

    def test_merge_controlnet_duplicate_points_in_place_requires_same_serial_track(self):
        net = ip.ControlNet()
        net.add_point(_make_point("P1", [_make_measure("SN-A", 10.0, 20.0)]))
        net.add_point(_make_point("P2", [_make_measure("SN-B", 10.0, 20.0)]))

        summary = merge_controlnet_duplicate_points_in_place(
            net,
            _make_serial_lookup("SN-A", "SN-B"),
            decimals=1,
        )

        self.assertEqual(summary["duplicate_point_count"], 0)
        self.assertEqual(summary["point_count_after"], 2)
        self.assertEqual(summary["measure_count_after"], 2)
        self.assertTrue(net.contains_point("P1"))
        self.assertTrue(net.contains_point("P2"))

    def test_merge_control_measure_file_writes_new_output_without_overwriting_input(self):
        serial_left = ip.SerialNumber.compose(str(LEFT_CUBE_PATH))
        serial_middle = ip.SerialNumber.compose(str(MIDDLE_CUBE_PATH))
        serial_right = ip.SerialNumber.compose(str(RIGHT_CUBE_PATH))

        with temporary_directory() as temp_dir:
            original_images = temp_dir / "original_images.lis"
            original_images.write_text(
                "\n".join([str(LEFT_CUBE_PATH), str(MIDDLE_CUBE_PATH), str(RIGHT_CUBE_PATH)]) + "\n",
                encoding="utf-8",
            )

            input_net_path = temp_dir / "control.net"
            input_net = ip.ControlNet()
            input_net.add_point(
                _make_point(
                    "P1",
                    [
                        _make_measure(serial_left, 100.04, 200.04),
                        _make_measure(serial_middle, 300.00, 400.00),
                    ],
                    point_type=ip.ControlPoint.PointType.Fixed,
                    edit_lock=True,
                )
            )
            input_net.add_point(
                _make_point(
                    "P2",
                    [
                        _make_measure(serial_left, 100.03, 200.02),
                        _make_measure(serial_right, 500.04, 600.04),
                    ],
                )
            )
            input_net.write(str(input_net_path))

            summary = merge_control_measure_file(original_images, input_net_path, decimals=1)

            output_net_path = _default_output_path(input_net_path)
            self.assertEqual(summary["input_control_net"], str(input_net_path))
            self.assertEqual(summary["output_control_net"], str(output_net_path))
            self.assertTrue(output_net_path.exists())
            self.assertEqual(summary["point_count_before"], 2)
            self.assertEqual(summary["point_count_after"], 1)
            self.assertEqual(summary["measure_count_before"], 4)
            self.assertEqual(summary["measure_count_after"], 3)
            self.assertEqual(summary["added_measure_count"], 1)
            self.assertEqual(summary["skipped_existing_serial_count"], 1)
            self.assertEqual(summary["merged_point_ids"], ("P2",))

            original_net = ip.ControlNet(str(input_net_path))
            self.assertEqual(original_net.get_num_points(), 2)
            self.assertEqual(original_net.get_num_measures(), 4)

            merged_net = ip.ControlNet(str(output_net_path))
            self.assertEqual(merged_net.get_num_points(), 1)
            self.assertEqual(merged_net.get_num_measures(), 3)
            merged_point = merged_net.get_point("P1")
            self.assertEqual(merged_point.get_type(), ip.ControlPoint.PointType.Fixed)
            self.assertTrue(merged_point.is_edit_locked())
            self.assertCountEqual(
                [measure.get_cube_serial_number() for measure in merged_point.get_measures()],
                [serial_left, serial_middle, serial_right],
            )

    def test_cli_main_prints_json_summary_for_default_output(self):
        serial_left = ip.SerialNumber.compose(str(LEFT_CUBE_PATH))
        serial_middle = ip.SerialNumber.compose(str(MIDDLE_CUBE_PATH))
        serial_right = ip.SerialNumber.compose(str(RIGHT_CUBE_PATH))

        with temporary_directory() as temp_dir:
            original_images = temp_dir / "original_images.lis"
            original_images.write_text(
                "\n".join([str(LEFT_CUBE_PATH), str(MIDDLE_CUBE_PATH), str(RIGHT_CUBE_PATH)]) + "\n",
                encoding="utf-8",
            )

            input_net_path = temp_dir / "control.net"
            input_net = ip.ControlNet()
            input_net.add_point(
                _make_point(
                    "P1",
                    [
                        _make_measure(serial_left, 10.04, 20.04),
                        _make_measure(serial_middle, 30.00, 40.00),
                    ],
                )
            )
            input_net.add_point(
                _make_point(
                    "P2",
                    [
                        _make_measure(serial_left, 10.03, 20.02),
                        _make_measure(serial_right, 50.04, 60.04),
                    ],
                )
            )
            input_net.write(str(input_net_path))

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = merge_control_measure_main([str(original_images), str(input_net_path), "--decimals", "1"])

            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["output_control_net"], result["output_control_net"])
            self.assertEqual(payload["point_count_after"], result["point_count_after"])
            self.assertEqual(payload["measure_count_after"], result["measure_count_after"])
            self.assertEqual(payload["merged_point_ids"], ["P2"])
            self.assertEqual(result["merged_point_ids"], ("P2",))
            self.assertEqual(payload["output_control_net"], str(_default_output_path(input_net_path)))
            self.assertEqual(payload["point_count_after"], 1)
            self.assertEqual(payload["measure_count_after"], 3)


if __name__ == "__main__":
    unittest.main()
