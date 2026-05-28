"""Focused unit tests for deep-match manifest export helpers.

Author: Geng Xun
Created: 2026-05-16
Last Modified: 2026-05-16
Updated: 2026-05-16  Geng Xun added focused regression coverage for deep-match workspace resolution, task payload serialization, and manifest round-tripping.
Updated: 2026-05-16  Geng Xun added export-mode regression coverage for the image_match CLI/parser and workspace handoff flow.
Updated: 2026-05-16  Geng Xun added import-mode regression coverage for manifest NPZ result conversion back into `.key` files.
Updated: 2026-05-16  Geng Xun added import edge-case coverage for missing, failed, empty, multi-task, and score-length-mismatch results.
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np
import isis_pybind as ip


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import attach_dom_like_projection_mapping, make_test_cube, temporary_directory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from image_match.deep_match_manifest import (
    DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
    build_deep_match_pair_manifest,
    default_deep_match_pair_id,
    read_deep_match_task_arrays,
    read_deep_match_pair_manifest,
    resolve_deep_match_workspace,
    write_deep_match_task_arrays,
    write_deep_match_pair_manifest,
    write_deep_match_task_result,
)
from image_match.image_match import build_argument_parser, match_dom_pair_to_key_files
from image_match.keypoints import read_key_file
from image_match.tile_matching import PairedTileWindow, TileMatchTask, TileWindow, tile_match_task_from_payload, tile_match_task_to_payload


def _build_textured_test_image(width: int, height: int) -> np.ndarray:
    y_coords, x_coords = np.indices((height, width), dtype=np.float32)
    texture = (
        40.0 * np.sin(x_coords / 5.0)
        + 55.0 * np.cos(y_coords / 7.0)
        + 0.7 * x_coords
        + 0.4 * y_coords
    )
    texture -= float(texture.min())
    texture /= max(float(texture.max()), 1.0)
    return np.clip(texture * 255.0, 0.0, 255.0).astype(np.float32)


def _write_array_to_cube(cube: ip.Cube, array: np.ndarray) -> None:
    line_manager = ip.LineManager(cube)
    for line_index in range(array.shape[0]):
        line_manager.set_line(line_index + 1, 1)
        for sample_index in range(array.shape[1]):
            line_manager[sample_index] = float(array[line_index, sample_index])
        cube.write(line_manager)


def _make_tile_task(
    *,
    matcher_method: str = "lightglue",
    left_start_x: int = 10,
    left_start_y: int = 20,
    right_start_x: int = 30,
    right_start_y: int = 40,
    opencv_num_threads: int | None = 2,
) -> TileMatchTask:
    return TileMatchTask(
        left_dom_path="left_dom.cub",
        right_dom_path="right_dom.cub",
        band=1,
        paired_window=PairedTileWindow(
            local_window=TileWindow(start_x=0, start_y=0, width=64, height=64),
            left_window=TileWindow(start_x=left_start_x, start_y=left_start_y, width=64, height=64),
            right_window=TileWindow(start_x=right_start_x, start_y=right_start_y, width=64, height=64),
        ),
        minimum_value=None,
        maximum_value=None,
        lower_percent=0.5,
        upper_percent=99.5,
        invalid_values=(0.0,),
        special_pixel_abs_threshold=1.0e300,
        min_valid_pixels=64,
        valid_pixel_percent_threshold=0.1,
        invalid_pixel_radius=2,
        ratio_test=0.75,
        matcher_method=matcher_method,
        max_features=2048,
        sift_octave_layers=3,
        sift_contrast_threshold=0.04,
        sift_edge_threshold=10.0,
        sift_sigma=1.6,
        image_space="dom",
        use_gpu=True,
        gpu_batch_size=8,
        opencv_num_threads=opencv_num_threads,
    )


class ImageMatchDeepManifestUnitTest(unittest.TestCase):
    def test_build_argument_parser_accepts_deep_match_export_arguments(self):
        parser = build_argument_parser()

        parsed = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--matcher-method",
                "lightglue",
                "--deep-match-mode",
                "export",
                "--deep-match-temp-root-dir",
                "tmp_deep_match_workspace",
            ]
        )

        self.assertEqual(parsed.matcher_method, "lightglue")
        self.assertEqual(parsed.deep_match_mode, "export")
        self.assertEqual(parsed.deep_match_temp_root_dir, "tmp_deep_match_workspace")

    def test_build_argument_parser_accepts_deep_match_import_arguments(self):
        parser = build_argument_parser()

        parsed = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--deep-match-mode",
                "import",
                "--deep-match-manifest",
                "tmp_deep_match_workspace/pair/tasks.json",
            ]
        )

        self.assertEqual(parsed.deep_match_mode, "import")
        self.assertEqual(parsed.deep_match_manifest, "tmp_deep_match_workspace/pair/tasks.json")

    def test_match_dom_pair_to_key_files_import_mode_requires_manifest_path(self):
        with self.assertRaisesRegex(ValueError, "requires deep_match_manifest"):
            match_dom_pair_to_key_files(
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                deep_match_mode="import",
                write_match_visualization=False,
            )

    def test_default_deep_match_pair_id_is_stable_for_same_inputs(self):
        first = default_deep_match_pair_id(
            left_dom_path="left.cub",
            right_dom_path="right.cub",
            matcher_method="lightglue",
            band=1,
            image_space="dom",
        )
        second = default_deep_match_pair_id(
            left_dom_path="left.cub",
            right_dom_path="right.cub",
            matcher_method="lightglue",
            band=1,
            image_space="dom",
        )
        different = default_deep_match_pair_id(
            left_dom_path="left.cub",
            right_dom_path="right.cub",
            matcher_method="loftr",
            band=1,
            image_space="dom",
        )

        self.assertEqual(first, second)
        self.assertNotEqual(first, different)
        self.assertIn("left__right__", first)

    def test_resolve_deep_match_workspace_uses_expected_layout(self):
        with temporary_directory() as temp_dir:
            root = Path(temp_dir) / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME
            workspace = resolve_deep_match_workspace(temp_root_dir=root, pair_id="pair_001")

        self.assertEqual(workspace.pair_id, "pair_001")
        self.assertEqual(workspace.root_dir, (root / "pair_001").resolve())
        self.assertEqual(workspace.images_dir.name, "images")
        self.assertEqual(workspace.results_dir.name, "results")
        self.assertEqual(workspace.logs_dir.name, "logs")
        self.assertEqual(workspace.manifest_path.name, "tasks.json")

    def test_tile_match_task_payload_round_trip_preserves_gpu_and_window_metadata(self):
        task = _make_tile_task()

        payload = tile_match_task_to_payload(task)
        restored = tile_match_task_from_payload(payload)

        self.assertEqual(restored.left_dom_path, task.left_dom_path)
        self.assertEqual(restored.right_dom_path, task.right_dom_path)
        self.assertEqual(restored.matcher_method, task.matcher_method)
        self.assertEqual(restored.image_space, task.image_space)
        self.assertEqual(restored.use_gpu, task.use_gpu)
        self.assertEqual(restored.gpu_batch_size, task.gpu_batch_size)
        self.assertEqual(restored.paired_window.left_window.start_x, 10)
        self.assertEqual(restored.paired_window.right_window.start_y, 40)
        self.assertEqual(payload["opencv_num_threads"], 2)
        self.assertEqual(restored.opencv_num_threads, 2)

    def test_tile_match_task_payload_defaults_missing_opencv_num_threads_to_none(self):
        task = _make_tile_task(opencv_num_threads=None)
        payload = tile_match_task_to_payload(task)
        payload.pop("opencv_num_threads")

        restored = tile_match_task_from_payload(payload)

        self.assertIsNone(restored.opencv_num_threads)

    def test_manifest_build_write_and_read_round_trip_preserves_records(self):
        task = _make_tile_task(matcher_method="loftr")
        second_task = _make_tile_task(matcher_method="loftr")

        with temporary_directory() as temp_dir:
            temp_root = Path(temp_dir) / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME
            manifest = build_deep_match_pair_manifest(
                tasks=[task, second_task],
                left_dom_path="left_dom.cub",
                right_dom_path="right_dom.cub",
                matcher_method="loftr",
                band=1,
                image_space="dom",
                temp_root_dir=temp_root,
                requested_device="cuda",
                metadata={"source_stage": "image_match"},
                created_at_utc="2026-05-16T00:00:00Z",
            )
            manifest_path = write_deep_match_pair_manifest(manifest)
            self.assertTrue(manifest_path.exists())
            restored = read_deep_match_pair_manifest(manifest_path)

        self.assertEqual(restored.format_version, 1)
        self.assertEqual(restored.matcher_method, "loftr")
        self.assertEqual(restored.requested_device, "cuda")
        self.assertEqual(restored.metadata["source_stage"], "image_match")
        self.assertEqual(restored.created_at_utc, "2026-05-16T00:00:00Z")
        self.assertEqual(len(restored.tasks), 2)
        self.assertTrue(restored.tasks[0].left_image_path.endswith("task_00000_left.npy"))
        self.assertTrue(restored.tasks[0].result_path.endswith("task_00000_matches.npz"))
        self.assertTrue(restored.tasks[1].left_image_path.endswith("task_00001_left.npy"))
        self.assertEqual(restored.tasks[0].tile_task.matcher_method, "loftr")
        self.assertEqual(restored.tasks[0].tile_task.gpu_batch_size, 8)

    def test_write_and_read_deep_match_task_arrays_round_trip_numpy_artifacts(self):
        task = _make_tile_task()

        with temporary_directory() as temp_dir:
            manifest = build_deep_match_pair_manifest(
                tasks=[task],
                left_dom_path="left_dom.cub",
                right_dom_path="right_dom.cub",
                matcher_method="lightglue",
                band=1,
                image_space="dom",
                temp_root_dir=Path(temp_dir) / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
            )
            record = manifest.tasks[0]
            left_image = np.arange(16, dtype=np.uint8).reshape(4, 4)
            right_image = np.arange(16, dtype=np.uint8).reshape(4, 4) + 1
            left_mask = np.zeros((4, 4), dtype=bool)
            right_mask = np.ones((4, 4), dtype=bool)

            written = write_deep_match_task_arrays(
                record,
                left_image=left_image,
                right_image=right_image,
                left_mask=left_mask,
                right_mask=right_mask,
            )
            restored = read_deep_match_task_arrays(record)

        self.assertTrue(written["left_image"].name.endswith("task_00000_left.npy"))
        self.assertTrue(written["right_mask"].name.endswith("task_00000_right_mask.npy"))
        np.testing.assert_array_equal(restored["left_image"], left_image)
        np.testing.assert_array_equal(restored["right_image"], right_image)
        np.testing.assert_array_equal(restored["left_mask"], left_mask)
        np.testing.assert_array_equal(restored["right_mask"], right_mask)

    def test_match_dom_pair_to_key_files_export_mode_writes_manifest_workspace_without_key_files(self):
        width = 96
        height = 96
        image = _build_textured_test_image(width, height)

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="left_export.cub", samples=width, lines=height, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="right_export.cub", samples=width, lines=height, bands=1)
            try:
                _write_array_to_cube(left_cube, image)
                _write_array_to_cube(right_cube, image)
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
            finally:
                left_cube.close()
                right_cube.close()

            left_key_path = temp_dir / "left_export.key"
            right_key_path = temp_dir / "right_export.key"
            export_root = temp_dir / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME
            result = match_dom_pair_to_key_files(
                left_path,
                right_path,
                left_key_path,
                right_key_path,
                matcher_method="lightglue",
                deep_match_mode="export",
                deep_match_temp_root_dir=export_root,
                write_match_visualization=False,
                max_image_dimension=64,
                block_width=64,
                block_height=64,
                overlap_x=16,
                overlap_y=16,
                min_valid_pixels=32,
                ratio_test=0.8,
            )
            manifest_path = Path(result["deep_match_export"]["manifest_path"])
            manifest = read_deep_match_pair_manifest(manifest_path)

            self.assertTrue(manifest_path.exists())
            self.assertEqual(result["status"], "exported_for_deep_learning")
            self.assertTrue(result["export_only"])
            self.assertFalse(left_key_path.exists())
            self.assertFalse(right_key_path.exists())
            self.assertGreater(result["deep_match_export"]["exported_task_count"], 0)
            self.assertGreater(len(manifest.tasks), 0)
            self.assertTrue(Path(manifest.tasks[0].left_image_path).exists())
            self.assertTrue(Path(manifest.tasks[0].right_mask_path).exists())

    def test_match_dom_pair_to_key_files_import_mode_writes_offset_key_files_from_npz_results(self):
        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="left_import.cub", samples=96, lines=80, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="right_import.cub", samples=128, lines=112, bands=1)
            left_cube.close()
            right_cube.close()

            task = _make_tile_task(matcher_method="lightglue")
            task = tile_match_task_from_payload(
                {
                    **tile_match_task_to_payload(task),
                    "left_dom_path": str(left_path),
                    "right_dom_path": str(right_path),
                }
            )
            manifest = build_deep_match_pair_manifest(
                tasks=[task],
                left_dom_path=left_path,
                right_dom_path=right_path,
                matcher_method="lightglue",
                band=1,
                image_space="dom",
                temp_root_dir=temp_dir / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
                requested_device="cpu",
                created_at_utc="2026-05-16T00:00:00Z",
            )
            record = manifest.tasks[0]
            write_deep_match_task_result(
                record,
                left_points=np.array([[1.25, 2.5], [7.0, 8.0]], dtype=np.float32),
                right_points=np.array([[5.0, 6.0], [9.5, 10.25]], dtype=np.float32),
                scores=np.array([0.9, 0.8], dtype=np.float32),
                status="matched",
            )
            manifest_path = write_deep_match_pair_manifest(manifest)
            left_key_path = temp_dir / "nested" / "left_import.key"
            right_key_path = temp_dir / "nested" / "right_import.key"
            metadata_path = temp_dir / "import_metadata.json"

            result = match_dom_pair_to_key_files(
                left_path,
                right_path,
                left_key_path,
                right_key_path,
                metadata_output=metadata_path,
                deep_match_mode="import",
                deep_match_manifest=manifest_path,
                write_match_visualization=False,
            )
            left_key = read_key_file(left_key_path)
            right_key = read_key_file(right_key_path)

            self.assertEqual(result["status"], "imported")
            self.assertEqual(result["point_count"], 2)
            self.assertEqual(result["deep_match_import"]["imported_task_count"], 1)
            self.assertTrue(metadata_path.exists())
            self.assertEqual(left_key.image_width, 96)
            self.assertEqual(left_key.image_height, 80)
            self.assertEqual(right_key.image_width, 128)
            self.assertEqual(right_key.image_height, 112)
            self.assertAlmostEqual(left_key.points[0].sample, 12.25)
            self.assertAlmostEqual(left_key.points[0].line, 23.5)
            self.assertAlmostEqual(right_key.points[0].sample, 36.0)
            self.assertAlmostEqual(right_key.points[0].line, 47.0)

    def test_import_mode_merges_usable_tasks_and_reports_missing_failed_and_empty_results(self):
        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="left_import_edges.cub", samples=256, lines=256, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="right_import_edges.cub", samples=256, lines=256, bands=1)
            left_cube.close()
            right_cube.close()

            tasks = [
                _make_tile_task(left_start_x=0, left_start_y=0, right_start_x=10, right_start_y=10),
                _make_tile_task(left_start_x=20, left_start_y=30, right_start_x=40, right_start_y=50),
                _make_tile_task(left_start_x=60, left_start_y=70, right_start_x=80, right_start_y=90),
                _make_tile_task(left_start_x=100, left_start_y=110, right_start_x=120, right_start_y=130),
            ]
            tasks = [
                tile_match_task_from_payload(
                    {
                        **tile_match_task_to_payload(task),
                        "left_dom_path": str(left_path),
                        "right_dom_path": str(right_path),
                    }
                )
                for task in tasks
            ]
            manifest = build_deep_match_pair_manifest(
                tasks=tasks,
                left_dom_path=left_path,
                right_dom_path=right_path,
                matcher_method="lightglue",
                band=1,
                image_space="dom",
                temp_root_dir=temp_dir / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
                requested_device="cpu",
                created_at_utc="2026-05-16T00:00:00Z",
            )
            failed_record = manifest.tasks[1]
            empty_record = manifest.tasks[2]
            valid_record = manifest.tasks[3]
            write_deep_match_task_result(
                failed_record,
                left_points=np.array([[1.0, 2.0]], dtype=np.float32),
                right_points=np.array([[3.0, 4.0]], dtype=np.float32),
                scores=np.array([0.1], dtype=np.float32),
                status="failed",
                metadata={"error": "synthetic matcher failure"},
            )
            write_deep_match_task_result(
                empty_record,
                left_points=np.empty((0, 2), dtype=np.float32),
                right_points=np.empty((0, 2), dtype=np.float32),
                scores=np.empty((0,), dtype=np.float32),
                status="matched_no_points",
            )
            write_deep_match_task_result(
                valid_record,
                left_points=np.array([[0.0, 0.0], [4.5, 5.5]], dtype=np.float32),
                right_points=np.array([[1.0, 2.0], [6.0, 7.0]], dtype=np.float32),
                scores=np.array([0.95], dtype=np.float32),
                status="matched",
                metadata={"note": "scores intentionally shorter than point arrays"},
            )
            manifest_path = write_deep_match_pair_manifest(manifest)
            left_key_path = temp_dir / "left_edges.key"
            right_key_path = temp_dir / "right_edges.key"

            result = match_dom_pair_to_key_files(
                left_path,
                right_path,
                left_key_path,
                right_key_path,
                deep_match_mode="import",
                deep_match_manifest=manifest_path,
                write_match_visualization=False,
            )
            left_key = read_key_file(left_key_path)
            right_key = read_key_file(right_key_path)

        self.assertEqual(result["status"], "imported_with_missing_or_failed_tasks")
        self.assertEqual(result["point_count"], 2)
        import_summary = result["deep_match_import"]
        self.assertEqual(import_summary["task_count"], 4)
        self.assertEqual(import_summary["imported_task_count"], 1)
        self.assertEqual(import_summary["missing_result_count"], 1)
        self.assertEqual(import_summary["failed_task_count"], 1)
        self.assertEqual(import_summary["skipped_empty_task_count"], 1)
        self.assertEqual([task["status"] for task in import_summary["tasks"]], ["missing_result", "failed", "matched_no_points", "imported"])
        self.assertEqual(left_key.image_width, 256)
        self.assertEqual(right_key.image_height, 256)
        self.assertAlmostEqual(left_key.points[0].sample, 101.0)
        self.assertAlmostEqual(left_key.points[0].line, 111.0)
        self.assertAlmostEqual(right_key.points[1].sample, 127.0)
        self.assertAlmostEqual(right_key.points[1].line, 138.0)

    def test_import_mode_reports_no_usable_results_when_all_tasks_missing_or_failed(self):
        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="left_import_no_usable.cub", samples=128, lines=128, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="right_import_no_usable.cub", samples=128, lines=128, bands=1)
            left_cube.close()
            right_cube.close()

            tasks = [
                _make_tile_task(left_start_x=0, left_start_y=0, right_start_x=0, right_start_y=0),
                _make_tile_task(left_start_x=20, left_start_y=20, right_start_x=30, right_start_y=30),
            ]
            tasks = [
                tile_match_task_from_payload(
                    {
                        **tile_match_task_to_payload(task),
                        "left_dom_path": str(left_path),
                        "right_dom_path": str(right_path),
                    }
                )
                for task in tasks
            ]
            manifest = build_deep_match_pair_manifest(
                tasks=tasks,
                left_dom_path=left_path,
                right_dom_path=right_path,
                matcher_method="lightglue",
                band=1,
                image_space="dom",
                temp_root_dir=temp_dir / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
                requested_device="cpu",
            )
            write_deep_match_task_result(
                manifest.tasks[1],
                left_points=np.array([[1.0, 1.0]], dtype=np.float32),
                right_points=np.array([[2.0, 2.0]], dtype=np.float32),
                scores=np.array([0.2], dtype=np.float32),
                status="failed",
            )
            manifest_path = write_deep_match_pair_manifest(manifest)
            left_key_path = temp_dir / "left_no_usable.key"
            right_key_path = temp_dir / "right_no_usable.key"

            result = match_dom_pair_to_key_files(
                left_path,
                right_path,
                left_key_path,
                right_key_path,
                deep_match_mode="import",
                deep_match_manifest=manifest_path,
                write_match_visualization=False,
            )
            left_key = read_key_file(left_key_path)
            right_key = read_key_file(right_key_path)

        self.assertEqual(result["status"], "import_failed_no_usable_results")
        self.assertEqual(result["point_count"], 0)
        self.assertEqual(result["deep_match_import"]["missing_result_count"], 1)
        self.assertEqual(result["deep_match_import"]["failed_task_count"], 1)
        self.assertEqual(result["deep_match_import"]["imported_task_count"], 0)
        self.assertEqual(len(left_key.points), 0)
        self.assertEqual(len(right_key.points), 0)


if __name__ == "__main__":
    unittest.main()