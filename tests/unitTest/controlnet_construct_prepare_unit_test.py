"""Focused unit tests for DOM preparation and ControlNet merge-shell helpers.

This module validates the DOM-side preparation utilities that run before image matching
and ControlNet assembly. The coverage focuses on projected DOM metadata inspection,
pairwise overlap preparation, coordinate-basis JSON sidecars, GSD normalization command
generation, cnetmerge shell creation, and batch-summary aggregation from per-pair
reports.

The tests intentionally mix repository fixtures with optional real LRO DOM inputs. This
keeps the default regression suite fast and reproducible while still allowing local
real-data verification when the relevant environment variables are configured.

Author: Geng Xun
Created: 2026-04-17
Last Modified: 2026-04-18
Updated: 2026-04-17  Geng Xun added regression coverage for DOM GSD inventory/normalization, projected-overlap crop metadata, and cnetmerge shell generation.
Updated: 2026-04-17  Geng Xun added regression coverage for pairwise JSON report aggregation into a fixed-name batch summary report.
Updated: 2026-04-17  Geng Xun added coordinate-basis checks for projected-overlap metadata sidecars so offset versus sample/line semantics stay explicit.
Updated: 2026-04-18  Geng Xun added optional real LRO DOM prepare coverage while preserving the existing repository fixture regressions.
Updated: 2026-04-18  Geng Xun expanded the module docstring to clarify file scope, fixture-versus-real-data coverage, and preparation-stage responsibilities.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import temporary_directory, workspace_test_data_path

EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.batch_summary import (
    DEFAULT_BATCH_REPORT_NAME,
    build_batch_summary,
    load_pair_reports,
    pair_report_filename,
    write_batch_summary_report,
)
from controlnet_construct.controlnet_merge import generate_cnetmerge_shell_script, pair_controlnet_filename
from controlnet_construct.dom_prepare import (
    normalize_dom_list_gsd,
    prepare_dom_pair_for_matching,
    read_dom_projection_info,
    write_pair_preparation_metadata,
)
from controlnet_construct.listing import StereoPair, write_stereo_pair_list


FIXTURE_DOM_LEFT = workspace_test_data_path("hidtmgen", "ortho", "PSP_002118_1510_1m_o_forPDS_cropped.cub")
FIXTURE_DOM_RIGHT = workspace_test_data_path("hidtmgen", "ortho", "PSP_002118_1510_25cm_o_forPDS_cropped.cub")

REAL_LRO_DOM_LEFT_ENV = "ISIS_PYBIND_PREPARE_REAL_DOM_LEFT_CUBE"
REAL_LRO_DOM_RIGHT_ENV = "ISIS_PYBIND_PREPARE_REAL_DOM_RIGHT_CUBE"

DEFAULT_REAL_LRO_DOM_LEFT = Path("/media/gengxun/Elements/data/lro/test_controlnet_python/dom_M104318871LE.cub")
DEFAULT_REAL_LRO_DOM_RIGHT = Path("/media/gengxun/Elements/data/lro/test_controlnet_python/dom_M104318871RE.cub")


def _configured_real_lro_dom_pair() -> tuple[Path, Path]:
    left_dom = Path(os.environ.get(REAL_LRO_DOM_LEFT_ENV, str(DEFAULT_REAL_LRO_DOM_LEFT))).expanduser()
    right_dom = Path(os.environ.get(REAL_LRO_DOM_RIGHT_ENV, str(DEFAULT_REAL_LRO_DOM_RIGHT))).expanduser()
    return left_dom, right_dom


class ControlNetConstructPrepareUnitTest(unittest.TestCase):
    def test_read_dom_projection_info_reports_resolution_and_bounds(self):
        info = read_dom_projection_info(FIXTURE_DOM_LEFT)

        self.assertGreater(info.resolution, 0.0)
        self.assertGreater(info.image_width, 0)
        self.assertGreater(info.image_height, 0)
        self.assertLess(info.min_x, info.max_x)
        self.assertLess(info.min_y, info.max_y)

    def test_read_dom_projection_info_supports_configurable_real_lro_cube_when_available(self):
        real_left_dom, _ = _configured_real_lro_dom_pair()
        if not real_left_dom.exists():
            self.skipTest(
                "Real LRO DOM cube is unavailable. "
                f"Configure {REAL_LRO_DOM_LEFT_ENV} if you want to run the real-data prepare regression."
            )

        info = read_dom_projection_info(real_left_dom)

        self.assertEqual(info.path, str(real_left_dom))
        self.assertGreater(info.resolution, 0.0)
        self.assertGreater(info.image_width, 0)
        self.assertGreater(info.image_height, 0)
        self.assertLess(info.min_x, info.max_x)
        self.assertLess(info.min_y, info.max_y)

    def test_prepare_dom_pair_for_matching_returns_crop_offsets_for_real_overlap(self):
        metadata = prepare_dom_pair_for_matching(
            FIXTURE_DOM_LEFT,
            FIXTURE_DOM_RIGHT,
            expand_pixels=32,
            min_overlap_size=16,
        )

        self.assertEqual(metadata.status, "ready")
        self.assertGreater(metadata.shared_width, 0)
        self.assertGreater(metadata.shared_height, 0)
        self.assertGreaterEqual(metadata.left.offset_sample, 0)
        self.assertGreaterEqual(metadata.left.offset_line, 0)
        self.assertGreaterEqual(metadata.right.offset_sample, 0)
        self.assertGreaterEqual(metadata.right.offset_line, 0)

    def test_prepare_dom_pair_for_matching_supports_configurable_real_lro_pair_when_available(self):
        real_left_dom, real_right_dom = _configured_real_lro_dom_pair()
        if not real_left_dom.exists() or not real_right_dom.exists():
            self.skipTest(
                "Real LRO DOM pair is unavailable. "
                f"Configure {REAL_LRO_DOM_LEFT_ENV} and {REAL_LRO_DOM_RIGHT_ENV} if needed."
            )

        metadata = prepare_dom_pair_for_matching(
            real_left_dom,
            real_right_dom,
            expand_pixels=32,
            min_overlap_size=16,
        )

        self.assertEqual(metadata.status, "ready")
        self.assertEqual(metadata.left.path, str(real_left_dom))
        self.assertEqual(metadata.right.path, str(real_right_dom))
        self.assertGreater(metadata.shared_width, 0)
        self.assertGreater(metadata.shared_height, 0)
        self.assertGreaterEqual(metadata.left.offset_sample, 0)
        self.assertGreaterEqual(metadata.left.offset_line, 0)
        self.assertGreaterEqual(metadata.right.offset_sample, 0)
        self.assertGreaterEqual(metadata.right.offset_line, 0)

    def test_write_pair_preparation_metadata_declares_coordinate_bases(self):
        metadata = prepare_dom_pair_for_matching(
            FIXTURE_DOM_LEFT,
            FIXTURE_DOM_RIGHT,
            expand_pixels=16,
            min_overlap_size=16,
        )

        with temporary_directory() as temp_dir:
            metadata_path = temp_dir / "pair_preparation.json"
            write_pair_preparation_metadata(metadata_path, metadata)
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["left"]["offset_sample"], metadata.left.offset_sample)
        self.assertIn("coordinate_conventions", payload)
        self.assertEqual(payload["coordinate_conventions"]["context"], "dom_pair_preparation_metadata")
        self.assertIn("0-based", payload["coordinate_conventions"]["field_bases"]["left.offset_sample"])
        self.assertIn("1-based", payload["coordinate_conventions"]["field_bases"]["left.start_sample"])

    def test_normalize_dom_list_gsd_writes_report_list_and_commands(self):
        entries = [
            ("left.cub", str(FIXTURE_DOM_LEFT)),
            ("right.cub", str(FIXTURE_DOM_RIGHT)),
        ]

        with temporary_directory() as temp_dir:
            output_list = temp_dir / "doms_scaled.lis"
            gsd_report = temp_dir / "images_gsd.txt"
            output_dir = temp_dir / "scaled_doms"

            with mock.patch("controlnet_construct.dom_prepare.subprocess.run") as run_mock:
                run_mock.return_value = subprocess.CompletedProcess(args=["gdal_translate"], returncode=0)
                result = normalize_dom_list_gsd(
                    entries,
                    output_list,
                    gsd_report_path=gsd_report,
                    output_directory=output_dir,
                    tolerance_ratio=0.05,
                    apply=True,
                )

            written_entries = output_list.read_text(encoding="utf-8").splitlines()
            report_lines = gsd_report.read_text(encoding="utf-8").splitlines()

        self.assertEqual(result["input_count"], 2)
        self.assertEqual(result["scaled_count"], 2)
        self.assertEqual(len(written_entries), 2)
        self.assertEqual(len(report_lines), 2)
        self.assertEqual(run_mock.call_count, 2)
        self.assertTrue(all("\t" in line for line in report_lines))
        self.assertTrue(all(line.endswith(".cub") for line in written_entries))
        self.assertTrue(all(record["scaled"] for record in result["records"]))

    def test_generate_cnetmerge_shell_script_uses_existing_pair_nets(self):
        pairs = [
            StereoPair("left1.cub", "right1.cub"),
            StereoPair("left2.cub", "right2.cub"),
            StereoPair("left3.cub", "right3.cub"),
        ]

        with temporary_directory() as temp_dir:
            overlap_list = temp_dir / "images_overlap.lis"
            write_stereo_pair_list(overlap_list, pairs)
            pair_net_dir = temp_dir / "pair_nets"
            pair_net_dir.mkdir()
            existing_pairs = pairs[:2]
            for pair in existing_pairs:
                (pair_net_dir / pair_controlnet_filename(pair)).write_text("fake net\n", encoding="utf-8")

            output_net = temp_dir / "merged.net"
            script_path = temp_dir / "merge_all_controlnets.sh"
            pair_list_path = temp_dir / "pair_controlnets.lis"
            summary = generate_cnetmerge_shell_script(
                overlap_list,
                pair_net_dir,
                output_net,
                script_path,
                network_id="dom_global_net",
                description="merge all pairwise nets",
                pair_list_path=pair_list_path,
            )
            script_text = script_path.read_text(encoding="utf-8")
            pair_list_text = pair_list_path.read_text(encoding="utf-8")

        self.assertEqual(summary["overlap_pair_count"], 3)
        self.assertEqual(summary["included_count"], 2)
        self.assertEqual(summary["skipped_missing_count"], 1)
        self.assertIn("cnetmerge", script_text)
        self.assertIn("INPUTTYPE=list", script_text)
        self.assertIn("NETWORKID=dom_global_net", script_text)
        self.assertIn(str(output_net), script_text)
        self.assertEqual(len(pair_list_text.splitlines()), 2)
        self.assertIn(str(pair_net_dir / pair_controlnet_filename(existing_pairs[0])), pair_list_text)

    def test_build_batch_summary_aggregates_per_pair_reports(self):
        pairs = [
            StereoPair("left1.cub", "right1.cub"),
            StereoPair("left2.cub", "right2.cub"),
        ]
        pair_reports = [
            {
                "pair": pairs[0].as_csv_line(),
                "match": {"point_count": 120},
                "merge": {"unique_count": 80, "applied": True},
                "left_conversion": {"output_count": 60},
                "right_conversion": {"output_count": 60},
                "controlnet": {"point_count": 60},
            },
            {
                "pair": pairs[1].as_csv_line(),
                "match": {"point_count": 70},
                "merge": {"unique_count": 40, "applied": True},
                "left_conversion": {"output_count": 20},
                "right_conversion": {"output_count": 20},
                "controlnet": {"point_count": 20},
            },
        ]

        with temporary_directory() as temp_dir:
            report_paths: list[Path] = []
            for pair, payload in zip(pairs, pair_reports, strict=True):
                report_path = temp_dir / pair_report_filename(pair)
                report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                report_paths.append(report_path)

            loaded_reports, source_reports = load_pair_reports(report_paths)
            summary = build_batch_summary(loaded_reports, source_reports=source_reports)
            batch_report_path = temp_dir / DEFAULT_BATCH_REPORT_NAME
            written_summary = write_batch_summary_report(loaded_reports, batch_report_path, source_reports=source_reports)
            on_disk_summary = json.loads(batch_report_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["pair_count"], 2)
        self.assertEqual(summary["total_match_point_count"], 190)
        self.assertEqual(summary["total_merge_point_count"], 120)
        self.assertEqual(summary["total_dom2ori_retained_count"], 80)
        self.assertEqual(summary["total_final_control_point_count"], 80)
        self.assertAlmostEqual(summary["average_dom2ori_retention_rate"], 0.625, places=6)
        self.assertAlmostEqual(summary["overall_dom2ori_retention_rate"], 80.0 / 120.0, places=6)
        self.assertEqual(summary["pairs"][0]["pair"], pairs[0].as_csv_line())
        self.assertEqual(written_summary["report_path"], str(batch_report_path))
        self.assertEqual(on_disk_summary["total_final_control_point_count"], 80)


if __name__ == "__main__":
    unittest.main()
