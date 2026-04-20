"""Focused unit tests for the standalone DOM preparation helpers.

Author: Geng Xun
Created: 2026-04-19
Last Modified: 2026-04-19
Updated: 2026-04-19  Geng Xun added per-function normal, boundary, and exception coverage for dom_prepare.py helpers, metadata writing, and CLI dispatch.
Updated: 2026-04-19  Geng Xun added configurable real LRO DOM test-path overrides to match the optional user-specified input pattern used by the matching tests.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import temporary_directory, workspace_test_data_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct import dom_prepare


FIXTURE_DOM_LEFT = workspace_test_data_path("hidtmgen", "ortho", "PSP_002118_1510_1m_o_forPDS_cropped.cub")
FIXTURE_DOM_RIGHT = workspace_test_data_path("hidtmgen", "ortho", "PSP_002118_1510_25cm_o_forPDS_cropped.cub")
REAL_LRO_DOM_LEFT_ENV = "ISIS_PYBIND_PREPARE_REAL_DOM_LEFT_CUBE"
REAL_LRO_DOM_RIGHT_ENV = "ISIS_PYBIND_PREPARE_REAL_DOM_RIGHT_CUBE"
DEFAULT_REAL_LRO_DOM_LEFT = Path("/media/gengxun/Elements/data/lro/test_controlnet_python/dom_M104311715LE.cub")
DEFAULT_REAL_LRO_DOM_RIGHT = Path("/media/gengxun/Elements/data/lro/test_controlnet_python/dom_M104318871RE.cub")


def _configured_real_lro_dom_pair() -> tuple[Path, Path]:
    left_dom = Path(os.environ.get(REAL_LRO_DOM_LEFT_ENV, str(DEFAULT_REAL_LRO_DOM_LEFT))).expanduser()
    right_dom = Path(os.environ.get(REAL_LRO_DOM_RIGHT_ENV, str(DEFAULT_REAL_LRO_DOM_RIGHT))).expanduser()
    return left_dom, right_dom


class _FakeProjection:
    def __init__(self, coordinate_map: dict[tuple[float, float], tuple[float, float]]):
        self._coordinate_map = coordinate_map
        self._current: tuple[float, float] | None = None

    def set_coordinate(self, x: float, y: float) -> bool:
        key = (float(x), float(y))
        if key not in self._coordinate_map:
            self._current = None
            return False
        self._current = self._coordinate_map[key]
        return True

    def world_x(self) -> float:
        assert self._current is not None
        return self._current[0]

    def world_y(self) -> float:
        assert self._current is not None
        return self._current[1]


class _FakeCube:
    def __init__(self, projection: _FakeProjection, *, samples: int = 20, lines: int = 20):
        self._projection = projection
        self._samples = samples
        self._lines = lines
        self._is_open = False

    def open(self, path: str, access: str) -> None:
        self._is_open = True

    def projection(self) -> _FakeProjection:
        return self._projection

    def sample_count(self) -> int:
        return self._samples

    def line_count(self) -> int:
        return self._lines

    def is_open(self) -> bool:
        return self._is_open

    def close(self) -> None:
        self._is_open = False


class DomPrepareUnitTest(unittest.TestCase):
    def _make_crop_window(self, *, width: int = 8, height: int = 6) -> dom_prepare.CropWindow:
        return dom_prepare.CropWindow(
            path="example.cub",
            start_sample=3,
            start_line=5,
            width=width,
            height=height,
            offset_sample=2,
            offset_line=4,
            projected_min_x=10.0,
            projected_max_x=20.0,
            projected_min_y=30.0,
            projected_max_y=40.0,
            clipped_by_image_bounds=False,
        )

    def _make_pair_metadata(self) -> dom_prepare.PairPreparationMetadata:
        left = self._make_crop_window(width=10, height=9)
        right = dom_prepare.CropWindow(
            path="right.cub",
            start_sample=4,
            start_line=6,
            width=12,
            height=11,
            offset_sample=3,
            offset_line=5,
            projected_min_x=10.0,
            projected_max_x=20.0,
            projected_min_y=30.0,
            projected_max_y=40.0,
            clipped_by_image_bounds=True,
        )
        return dom_prepare.PairPreparationMetadata(
            left=left,
            right=right,
            overlap_min_x=11.0,
            overlap_max_x=19.0,
            overlap_min_y=31.0,
            overlap_max_y=39.0,
            expanded_min_x=10.0,
            expanded_max_x=20.0,
            expanded_min_y=30.0,
            expanded_max_y=40.0,
            expand_pixels=16,
            min_overlap_size=8,
            shared_width=10,
            shared_height=9,
            left_resolution=1.0,
            right_resolution=2.0,
            reference_resolution=2.0,
            gsd_ratio=0.5,
            status="ready",
            reason="",
        )

    def test_crop_window_properties_return_expected_coordinates(self):
        window = self._make_crop_window(width=8, height=6)

        self.assertEqual(window.start_x, 2)
        self.assertEqual(window.start_y, 4)
        self.assertEqual(window.end_sample, 10)
        self.assertEqual(window.end_line, 10)

    def test_resolve_path_entry_handles_relative_and_absolute_paths(self):
        with temporary_directory() as temp_dir:
            base_directory = temp_dir / "lists"
            base_directory.mkdir()
            relative_result = dom_prepare._resolve_path_entry("sub/left.cub", base_directory=base_directory)
            absolute_input = temp_dir / "absolute.cub"
            absolute_result = dom_prepare._resolve_path_entry(str(absolute_input), base_directory=base_directory)

        self.assertEqual(relative_result, (base_directory / "sub" / "left.cub").resolve())
        self.assertEqual(absolute_result, absolute_input)

    def test_write_lines_preserves_utf8_and_trailing_newline(self):
        with temporary_directory() as temp_dir:
            output_path = temp_dir / "lines.txt"
            dom_prepare._write_lines(output_path, ["第一行", "second line"])
            written = output_path.read_text(encoding="utf-8")

        self.assertEqual(written, "第一行\nsecond line\n")

    def test_read_dom_projection_info_reports_real_fixture_geometry(self):
        info = dom_prepare.read_dom_projection_info(FIXTURE_DOM_LEFT)

        self.assertEqual(info.path, str(FIXTURE_DOM_LEFT))
        self.assertGreater(info.image_width, 0)
        self.assertGreater(info.image_height, 0)
        self.assertGreater(info.resolution, 0.0)
        self.assertLess(info.min_x, info.max_x)
        self.assertLess(info.min_y, info.max_y)

    def test_read_dom_projection_info_supports_configurable_real_lro_cube_when_available(self):
        real_left_dom, _ = _configured_real_lro_dom_pair()
        if not real_left_dom.exists():
            self.skipTest(
                "Real LRO DOM cube is unavailable. "
                f"Configure {REAL_LRO_DOM_LEFT_ENV} if you want to run the real-data DOM prepare regression."
            )

        info = dom_prepare.read_dom_projection_info(real_left_dom)

        self.assertEqual(info.path, str(real_left_dom))
        self.assertGreater(info.image_width, 0)
        self.assertGreater(info.image_height, 0)
        self.assertGreater(info.resolution, 0.0)
        self.assertLess(info.min_x, info.max_x)
        self.assertLess(info.min_y, info.max_y)

    def test_write_images_gsd_report_handles_empty_and_nonempty_entries(self):
        with temporary_directory() as temp_dir:
            empty_report = temp_dir / "empty.txt"
            empty_infos = dom_prepare.write_images_gsd_report([], empty_report)
            empty_text = empty_report.read_text(encoding="utf-8")

            report_path = temp_dir / "images_gsd.txt"
            infos = dom_prepare.write_images_gsd_report(
                [
                    ("left.cub", str(FIXTURE_DOM_LEFT)),
                    ("right.cub", str(FIXTURE_DOM_RIGHT)),
                ],
                report_path,
            )
            lines = report_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(empty_infos, [])
        self.assertEqual(empty_text, "\n")
        self.assertEqual(len(infos), 2)
        self.assertEqual(len(lines), 2)
        self.assertTrue(all("\t" in line for line in lines))

    def test_relative_difference_supports_zero_difference_and_rejects_nonpositive_target(self):
        self.assertEqual(dom_prepare._relative_difference(2.0, 2.0), 0.0)
        self.assertAlmostEqual(dom_prepare._relative_difference(2.5, 2.0), 0.25, places=6)

        with self.assertRaisesRegex(ValueError, "target_resolution must be positive"):
            dom_prepare._relative_difference(2.5, 0.0)

    def test_format_scaled_output_path_uses_default_cub_suffix_when_missing(self):
        with temporary_directory() as temp_dir:
            output_path = dom_prepare._format_scaled_output_path(
                "relative/no_suffix",
                "/tmp/source_without_suffix",
                temp_dir,
                7,
                1.25,
            )

        self.assertEqual(output_path.parent, temp_dir)
        self.assertEqual(output_path.name, "007_no_suffix_gsd1p250000.cub")

    def test_display_path_for_output_preserves_absolute_inputs_and_relativizes_relative_entries(self):
        with temporary_directory() as temp_dir:
            output_list_path = temp_dir / "doms_scaled.lis"
            output_path = temp_dir / "scaled" / "scaled_left.cub"
            output_path.parent.mkdir()

            absolute_display = dom_prepare._display_path_for_output(
                output_path,
                output_list_path=output_list_path,
                source_entry=str(FIXTURE_DOM_LEFT),
            )
            relative_display = dom_prepare._display_path_for_output(
                output_path,
                output_list_path=output_list_path,
                source_entry="inputs/left.cub",
            )

        self.assertEqual(absolute_display, str(output_path))
        self.assertEqual(relative_display, "scaled/scaled_left.cub")

    def test_run_gdal_translate_invokes_subprocess_and_propagates_failure(self):
        command = ["gdal_translate", "input.cub", "output.cub"]
        completed_process = subprocess.CompletedProcess(args=command, returncode=0)

        with mock.patch("controlnet_construct.dom_prepare.subprocess.run", return_value=completed_process) as run_mock:
            dom_prepare._run_gdal_translate(command)

        run_mock.assert_called_once_with(command, check=True, text=True, capture_output=True)

        with mock.patch(
            "controlnet_construct.dom_prepare.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, command, stderr="boom"),
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                dom_prepare._run_gdal_translate(command)

    def test_normalize_dom_list_gsd_rejects_invalid_arguments(self):
        with self.assertRaisesRegex(ValueError, "The DOM list is empty"):
            dom_prepare.normalize_dom_list_gsd([], "doms_scaled.lis")

        with self.assertRaisesRegex(ValueError, "tolerance_ratio cannot be negative"):
            dom_prepare.normalize_dom_list_gsd([("left.cub", str(FIXTURE_DOM_LEFT))], "doms_scaled.lis", tolerance_ratio=-0.1)

        fake_info = dom_prepare.DomProjectionInfo("left.cub", 10, 10, 1.0, 0.0, 10.0, 0.0, 10.0)
        with mock.patch("controlnet_construct.dom_prepare.write_images_gsd_report", return_value=[fake_info]):
            with self.assertRaisesRegex(ValueError, "Resolved target GSD must be positive"):
                dom_prepare.normalize_dom_list_gsd(
                    [("left.cub", "/tmp/left.cub")],
                    "doms_scaled.lis",
                    target_resolution=0.0,
                )

    def test_normalize_dom_list_gsd_reuses_inputs_within_tolerance(self):
        infos = [
            dom_prepare.DomProjectionInfo("/tmp/left.cub", 10, 10, 2.0, 0.0, 1.0, 0.0, 1.0),
            dom_prepare.DomProjectionInfo("/tmp/right.cub", 10, 10, 2.02, 0.0, 1.0, 0.0, 1.0),
        ]
        entries = [("left.cub", "/tmp/left.cub"), ("right.cub", "/tmp/right.cub")]

        with temporary_directory() as temp_dir:
            output_list = temp_dir / "doms_scaled.lis"
            gsd_report = temp_dir / "images_gsd.txt"

            with (
                mock.patch("controlnet_construct.dom_prepare.write_images_gsd_report", return_value=infos),
                mock.patch("controlnet_construct.dom_prepare._run_gdal_translate") as translate_mock,
            ):
                result = dom_prepare.normalize_dom_list_gsd(
                    entries,
                    output_list,
                    gsd_report_path=gsd_report,
                    tolerance_ratio=0.05,
                    target_resolution=2.0,
                    apply=True,
                )
            written_entries = output_list.read_text(encoding="utf-8").splitlines()

        translate_mock.assert_not_called()
        self.assertEqual(written_entries, ["left.cub", "right.cub"])
        self.assertEqual(result["scaled_count"], 0)
        self.assertTrue(all(not record["scaled"] for record in result["records"]))

    def test_normalize_dom_list_gsd_resamples_out_of_tolerance_entries(self):
        infos = [
            dom_prepare.DomProjectionInfo("/tmp/left.cub", 10, 10, 1.0, 0.0, 1.0, 0.0, 1.0),
            dom_prepare.DomProjectionInfo("/tmp/right.cub", 10, 10, 4.0, 0.0, 1.0, 0.0, 1.0),
        ]
        entries = [("left.cub", "/tmp/left.cub"), ("right.cub", "/tmp/right.cub")]

        with temporary_directory() as temp_dir:
            output_list = temp_dir / "doms_scaled.lis"
            output_dir = temp_dir / "scaled"

            with (
                mock.patch("controlnet_construct.dom_prepare.write_images_gsd_report", return_value=infos),
                mock.patch("controlnet_construct.dom_prepare._run_gdal_translate") as translate_mock,
            ):
                result = dom_prepare.normalize_dom_list_gsd(
                    entries,
                    output_list,
                    output_directory=output_dir,
                    tolerance_ratio=0.10,
                    target_resolution=2.5,
                    apply=True,
                )
            written_entries = output_list.read_text(encoding="utf-8").splitlines()
            output_dir_exists = output_dir.exists()

        self.assertEqual(translate_mock.call_count, 2)
        self.assertEqual(result["scaled_count"], 2)
        self.assertTrue(all(record["scaled"] for record in result["records"]))
        self.assertEqual(len(written_entries), 2)
        self.assertTrue(all(line.endswith(".cub") for line in written_entries))
        self.assertTrue(output_dir_exists)

    def test_projected_bounds_intersection_handles_overlap_and_touching_edges(self):
        left = dom_prepare.DomProjectionInfo("left", 10, 10, 1.0, 0.0, 10.0, 0.0, 10.0)
        right = dom_prepare.DomProjectionInfo("right", 10, 10, 1.0, 5.0, 15.0, 2.0, 8.0)
        touching = dom_prepare.DomProjectionInfo("touch", 10, 10, 1.0, 10.0, 20.0, 0.0, 10.0)

        self.assertEqual(dom_prepare._projected_bounds_intersection(left, right), (5.0, 10.0, 2.0, 8.0))
        self.assertIsNone(dom_prepare._projected_bounds_intersection(left, touching))

    def test_projected_bounds_to_window_builds_window_from_projected_bounds(self):
        projection = _FakeProjection(
            {
                (0.0, 10.0): (1.2, 2.4),
                (5.0, 10.0): (5.7, 2.5),
                (0.0, 2.0): (1.4, 8.2),
                (5.0, 2.0): (5.9, 8.1),
            }
        )
        fake_cube = _FakeCube(projection, samples=20, lines=20)
        image_info = dom_prepare.DomProjectionInfo("fake.cub", 20, 20, 1.0, 0.0, 10.0, 0.0, 10.0)

        with mock.patch.object(dom_prepare.ip, "Cube", return_value=fake_cube):
            window = dom_prepare._projected_bounds_to_window(
                "fake.cub",
                requested_min_x=-2.0,
                requested_max_x=5.0,
                requested_min_y=2.0,
                requested_max_y=12.0,
                image_info=image_info,
            )

        self.assertEqual(window.start_sample, 1)
        self.assertEqual(window.start_line, 2)
        self.assertEqual(window.width, 6)
        self.assertEqual(window.height, 8)
        self.assertTrue(window.clipped_by_image_bounds)

    def test_projected_bounds_to_window_rejects_collapsed_or_unprojectable_ranges(self):
        image_info = dom_prepare.DomProjectionInfo("fake.cub", 20, 20, 1.0, 0.0, 10.0, 0.0, 10.0)

        with self.assertRaisesRegex(ValueError, "collapsed after clipping"):
            dom_prepare._projected_bounds_to_window(
                "fake.cub",
                requested_min_x=20.0,
                requested_max_x=30.0,
                requested_min_y=20.0,
                requested_max_y=30.0,
                image_info=image_info,
            )

        fake_cube = _FakeCube(_FakeProjection({}), samples=20, lines=20)
        with mock.patch.object(dom_prepare.ip, "Cube", return_value=fake_cube):
            with self.assertRaisesRegex(ValueError, "Could not convert projected crop bounds"):
                dom_prepare._projected_bounds_to_window(
                    "fake.cub",
                    requested_min_x=1.0,
                    requested_max_x=2.0,
                    requested_min_y=1.0,
                    requested_max_y=2.0,
                    image_info=image_info,
                )

    def test_projected_bounds_to_window_rejects_nonpositive_window(self):
        projection = _FakeProjection(
            {
                (1.0, 2.0): (0.2, 0.2),
                (2.0, 2.0): (0.4, 0.2),
                (1.0, 1.0): (0.2, 0.4),
                (2.0, 1.0): (0.4, 0.4),
            }
        )
        fake_cube = _FakeCube(projection, samples=0, lines=0)
        image_info = dom_prepare.DomProjectionInfo("fake.cub", 0, 0, 1.0, 0.0, 10.0, 0.0, 10.0)

        with mock.patch.object(dom_prepare.ip, "Cube", return_value=fake_cube):
            with self.assertRaisesRegex(ValueError, "non-positive image window"):
                dom_prepare._projected_bounds_to_window(
                    "fake.cub",
                    requested_min_x=1.0,
                    requested_max_x=2.0,
                    requested_min_y=1.0,
                    requested_max_y=2.0,
                    image_info=image_info,
                )

    def test_prepare_dom_pair_for_matching_rejects_invalid_arguments(self):
        with self.assertRaisesRegex(ValueError, "expand_pixels cannot be negative"):
            dom_prepare.prepare_dom_pair_for_matching("left.cub", "right.cub", expand_pixels=-1)

        with self.assertRaisesRegex(ValueError, "min_overlap_size must be positive"):
            dom_prepare.prepare_dom_pair_for_matching("left.cub", "right.cub", min_overlap_size=0)

    def test_prepare_dom_pair_for_matching_returns_structured_no_overlap_result(self):
        left_info = dom_prepare.DomProjectionInfo("left.cub", 10, 10, 1.0, 0.0, 5.0, 0.0, 5.0)
        right_info = dom_prepare.DomProjectionInfo("right.cub", 10, 10, 2.0, 10.0, 15.0, 10.0, 15.0)

        with mock.patch("controlnet_construct.dom_prepare.read_dom_projection_info", side_effect=[left_info, right_info]):
            metadata = dom_prepare.prepare_dom_pair_for_matching("left.cub", "right.cub")

        self.assertEqual(metadata.status, "skipped_no_projected_overlap")
        self.assertEqual(metadata.shared_width, 0)
        self.assertEqual(metadata.shared_height, 0)
        self.assertEqual(metadata.reference_resolution, 2.0)
        self.assertAlmostEqual(metadata.gsd_ratio, 0.5, places=6)

    def test_prepare_dom_pair_for_matching_marks_small_shared_overlap(self):
        left_info = dom_prepare.DomProjectionInfo("left.cub", 10, 10, 1.0, 0.0, 10.0, 0.0, 10.0)
        right_info = dom_prepare.DomProjectionInfo("right.cub", 10, 10, 2.0, 2.0, 12.0, 2.0, 12.0)
        left_window = self._make_crop_window(width=5, height=4)
        right_window = dom_prepare.CropWindow(
            path="right.cub",
            start_sample=1,
            start_line=1,
            width=3,
            height=4,
            offset_sample=0,
            offset_line=0,
            projected_min_x=2.0,
            projected_max_x=10.0,
            projected_min_y=2.0,
            projected_max_y=10.0,
            clipped_by_image_bounds=False,
        )

        with (
            mock.patch("controlnet_construct.dom_prepare.read_dom_projection_info", side_effect=[left_info, right_info]),
            mock.patch("controlnet_construct.dom_prepare._projected_bounds_to_window", side_effect=[left_window, right_window]),
        ):
            metadata = dom_prepare.prepare_dom_pair_for_matching(
                "left.cub",
                "right.cub",
                expand_pixels=4,
                min_overlap_size=6,
            )

        self.assertEqual(metadata.status, "skipped_small_overlap")
        self.assertEqual(metadata.shared_width, 3)
        self.assertEqual(metadata.shared_height, 4)
        self.assertIn("too small", metadata.reason)

    def test_prepare_dom_pair_for_matching_returns_ready_metadata(self):
        left_info = dom_prepare.DomProjectionInfo("left.cub", 10, 10, 1.0, 0.0, 10.0, 0.0, 10.0)
        right_info = dom_prepare.DomProjectionInfo("right.cub", 10, 10, 2.0, 2.0, 12.0, 2.0, 12.0)
        left_window = self._make_crop_window(width=9, height=8)
        right_window = dom_prepare.CropWindow(
            path="right.cub",
            start_sample=2,
            start_line=2,
            width=12,
            height=11,
            offset_sample=1,
            offset_line=1,
            projected_min_x=0.0,
            projected_max_x=12.0,
            projected_min_y=0.0,
            projected_max_y=12.0,
            clipped_by_image_bounds=True,
        )

        with (
            mock.patch("controlnet_construct.dom_prepare.read_dom_projection_info", side_effect=[left_info, right_info]),
            mock.patch("controlnet_construct.dom_prepare._projected_bounds_to_window", side_effect=[left_window, right_window]),
        ):
            metadata = dom_prepare.prepare_dom_pair_for_matching(
                "left.cub",
                "right.cub",
                expand_pixels=3,
                min_overlap_size=4,
            )

        self.assertEqual(metadata.status, "ready")
        self.assertEqual(metadata.shared_width, 9)
        self.assertEqual(metadata.shared_height, 8)
        self.assertEqual(metadata.reference_resolution, 2.0)
        self.assertEqual(metadata.expand_pixels, 3)
        self.assertAlmostEqual(metadata.expanded_min_x, -4.0, places=6)
        self.assertAlmostEqual(metadata.expanded_max_x, 16.0, places=6)

    def test_prepare_dom_pair_for_matching_supports_configurable_real_lro_pair_when_available(self):
        real_left_dom, real_right_dom = _configured_real_lro_dom_pair()
        if not real_left_dom.exists() or not real_right_dom.exists():
            self.skipTest(
                "Real LRO DOM pair is unavailable. "
                f"Configure {REAL_LRO_DOM_LEFT_ENV} and {REAL_LRO_DOM_RIGHT_ENV} if needed."
            )

        metadata = dom_prepare.prepare_dom_pair_for_matching(
            real_left_dom,
            real_right_dom,
            expand_pixels=32,
            min_overlap_size=16,
        )
        
        #
        
        print(f"metadata: {metadata}")  # Debug print to verify the metadata content

        self.assertEqual(metadata.left.path, str(real_left_dom))
        self.assertEqual(metadata.right.path, str(real_right_dom))
        self.assertIn(metadata.status, {"ready", "skipped_small_overlap", "skipped_no_projected_overlap"})
        self.assertGreaterEqual(metadata.shared_width, 0)
        self.assertGreaterEqual(metadata.shared_height, 0)
        self.assertGreater(metadata.left_resolution, 0.0)
        self.assertGreater(metadata.right_resolution, 0.0)

    def test_write_pair_preparation_metadata_supports_dataclass_and_dict_inputs(self):
        metadata = self._make_pair_metadata()

        with temporary_directory() as temp_dir:
            metadata_path = temp_dir / "pair_preparation.json"
            dom_prepare.write_pair_preparation_metadata(metadata_path, metadata)
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))

            dict_path = temp_dir / "pair_preparation_from_dict.json"
            dom_prepare.write_pair_preparation_metadata(dict_path, {"left": {"offset_sample": 0}, "right": {"start_sample": 1}})
            dict_payload = json.loads(dict_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["left"]["offset_sample"], metadata.left.offset_sample)
        self.assertEqual(payload["coordinate_conventions"]["context"], "dom_pair_preparation_metadata")
        self.assertIn("0-based", payload["coordinate_conventions"]["field_bases"]["left.offset_sample"])
        self.assertEqual(dict_payload["left"]["offset_sample"], 0)
        self.assertEqual(dict_payload["right"]["start_sample"], 1)

    def test_build_argument_parser_parses_expected_flags(self):
        parser = dom_prepare.build_argument_parser()

        args = parser.parse_args(
            [
                "input.lis",
                "output.lis",
                "--gsd-report",
                "images_gsd.txt",
                "--output-dir",
                "scaled_doms",
                "--tolerance-ratio",
                "0.1",
                "--target-resolution",
                "2.5",
                "--gdal-translate",
                "/usr/bin/gdal_translate",
                "--resampling",
                "nearest",
                "--dry-run",
            ]
        )

        self.assertEqual(args.input_list, "input.lis")
        self.assertEqual(args.output_list, "output.lis")
        self.assertEqual(args.gsd_report, "images_gsd.txt")
        self.assertEqual(args.output_dir, "scaled_doms")
        self.assertAlmostEqual(args.tolerance_ratio, 0.1, places=6)
        self.assertAlmostEqual(args.target_resolution, 2.5, places=6)
        self.assertEqual(args.gdal_translate, "/usr/bin/gdal_translate")
        self.assertEqual(args.resampling, "nearest")
        self.assertTrue(args.dry_run)

    def test_main_reads_list_and_prints_json_summary(self):
        fake_result = {"scaled_count": 1, "target_resolution": 2.5}
        stdout = io.StringIO()

        with temporary_directory() as temp_dir:
            input_list = temp_dir / "doms.lis"
            argv = [
                "dom_prepare.py",
                str(input_list),
                str(temp_dir / "doms_scaled.lis"),
                "--gsd-report",
                str(temp_dir / "images_gsd.txt"),
                "--output-dir",
                str(temp_dir / "scaled"),
                "--tolerance-ratio",
                "0.1",
                "--target-resolution",
                "2.5",
                "--gdal-translate",
                "/usr/bin/gdal_translate",
                "--resampling",
                "nearest",
                "--dry-run",
            ]

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch("controlnet_construct.dom_prepare.read_path_list", return_value=["relative_left.cub"]),
                mock.patch(
                    "controlnet_construct.dom_prepare._resolve_path_entry",
                    return_value=Path("/tmp/resolved_left.cub"),
                ) as resolve_mock,
                mock.patch("controlnet_construct.dom_prepare.normalize_dom_list_gsd", return_value=fake_result) as normalize_mock,
                redirect_stdout(stdout),
            ):
                dom_prepare.main()

        resolve_mock.assert_called_once_with("relative_left.cub", base_directory=input_list.parent)
        normalize_mock.assert_called_once_with(
            [("relative_left.cub", "/tmp/resolved_left.cub")],
            str(temp_dir / "doms_scaled.lis"),
            gsd_report_path=str(temp_dir / "images_gsd.txt"),
            output_directory=str(temp_dir / "scaled"),
            tolerance_ratio=0.1,
            target_resolution=2.5,
            gdal_translate_executable="/usr/bin/gdal_translate",
            resampling="nearest",
            apply=False,
        )
        self.assertEqual(json.loads(stdout.getvalue()), fake_result)


if __name__ == "__main__":
    unittest.main()