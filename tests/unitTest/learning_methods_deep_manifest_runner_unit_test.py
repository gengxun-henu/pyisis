"""Focused unit tests for the learning_methods deep-match manifest runner.

Author: Geng Xun
Created: 2026-05-16
Last Modified: 2026-05-20
Updated: 2026-05-16  Geng Xun added regression coverage for manifest execution with a fake deep matcher adapter and standardized NPZ results.
Updated: 2026-05-20  Geng Xun added stage-6 regression coverage for manifest runtime-config preflight and adapter provenance handoff.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

import numpy as np


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import temporary_directory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
LEARNING_METHODS_DIR = EXAMPLES_DIR / "learning_methods"
for import_path in (EXAMPLES_DIR, LEARNING_METHODS_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from image_match.deep_match_manifest import (
    DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
    build_deep_match_pair_manifest,
    read_deep_match_task_result,
    write_deep_match_pair_manifest,
    write_deep_match_task_arrays,
)
import controlnet_construct.deep_match_config as deep_match_config_module
from image_match.tile_matching import PairedTileWindow, TileMatchTask, TileWindow
from controlnet_construct.deep_match_config import DeepMatchRuntimeConfig
from run_deep_match_manifest import build_argument_parser, run_manifest


def _make_tile_task() -> TileMatchTask:
    return TileMatchTask(
        left_dom_path="left_dom.cub",
        right_dom_path="right_dom.cub",
        band=1,
        paired_window=PairedTileWindow(
            local_window=TileWindow(start_x=0, start_y=0, width=8, height=8),
            left_window=TileWindow(start_x=10, start_y=20, width=8, height=8),
            right_window=TileWindow(start_x=30, start_y=40, width=8, height=8),
        ),
        minimum_value=None,
        maximum_value=None,
        lower_percent=0.5,
        upper_percent=99.5,
        invalid_values=(),
        special_pixel_abs_threshold=1.0e300,
        min_valid_pixels=4,
        valid_pixel_percent_threshold=0.0,
        invalid_pixel_radius=1,
        ratio_test=0.75,
        matcher_method="lightglue",
        max_features=128,
        sift_octave_layers=3,
        sift_contrast_threshold=0.04,
        sift_edge_threshold=10.0,
        sift_sigma=1.6,
        image_space="dom",
        use_gpu=False,
        gpu_batch_size=4,
    )


def _make_runtime_config(*, prefer_gpu: bool = False) -> DeepMatchRuntimeConfig:
    return DeepMatchRuntimeConfig(
        matcher_method="lightglue",
        feature_extractor_method="superpoint",
        prefer_gpu=prefer_gpu,
        device_dtype="float32",
        fallback_on_error=None,
        raw_config={"matcher": {"method": "lightglue"}},
    )


class FakeDeepMatcherAdapter:
    def __init__(self, *, prefer_gpu: bool, runtime_config=None) -> None:
        self.prefer_gpu = prefer_gpu
        self.runtime_config = runtime_config
        self._device = "cuda" if prefer_gpu else "cpu"

    def match_pair(self, *, matcher_method: str, left_image, right_image, left_mask=None, right_mask=None):
        self.matcher_method = matcher_method
        self.left_shape = tuple(left_image.shape)
        self.right_shape = tuple(right_image.shape)
        self.left_mask_shape = None if left_mask is None else tuple(left_mask.shape)
        self.right_mask_shape = None if right_mask is None else tuple(right_mask.shape)
        return SimpleNamespace(
            left_keypoints=(np.array([1.0, 1.0]), np.array([4.0, 4.0]), np.array([7.0, 7.0])),
            right_keypoints=(np.array([2.0, 2.0]), np.array([5.0, 5.0]), np.array([7.0, 7.0])),
            matches=(
                SimpleNamespace(queryIdx=0, trainIdx=0, distance=0.1),
                SimpleNamespace(queryIdx=1, trainIdx=1, distance=0.2),
                SimpleNamespace(queryIdx=2, trainIdx=2, distance=0.3),
            ),
        )


class LearningMethodsDeepManifestRunnerUnitTest(unittest.TestCase):
    def test_run_manifest_passes_manifest_runtime_config_into_adapter_factory(self):
        with temporary_directory() as temp_dir:
            runtime_config = _make_runtime_config()
            manifest = build_deep_match_pair_manifest(
                tasks=[replace(_make_tile_task(), deep_match_runtime_config=runtime_config)],
                left_dom_path="left_dom.cub",
                right_dom_path="right_dom.cub",
                matcher_method="lightglue",
                band=1,
                image_space="dom",
                temp_root_dir=Path(temp_dir) / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
                requested_device="cpu",
                created_at_utc="2026-05-16T00:00:00Z",
            )
            record = manifest.tasks[0]
            write_deep_match_task_arrays(
                record,
                left_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                right_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                left_mask=np.zeros((8, 8), dtype=bool),
                right_mask=np.zeros((8, 8), dtype=bool),
            )
            manifest_path = write_deep_match_pair_manifest(manifest)

            captured_kwargs = {}

            def _adapter_factory(**kwargs):
                captured_kwargs.update(kwargs)
                return FakeDeepMatcherAdapter(**kwargs)

            with patch("run_deep_match_manifest.check_deep_match_dependencies", return_value=[]):
                run_manifest(
                    manifest_path,
                    device="cpu",
                    adapter_factory=_adapter_factory,
                )

            self.assertEqual(captured_kwargs["runtime_config"], runtime_config)
            self.assertEqual(captured_kwargs["runtime_config"].matcher_method, "lightglue")

    def test_preflight_check_deep_match_dependencies_reports_human_readable_missing_modules(self):
        runtime_config = _make_runtime_config()

        def _fake_import(name: str, package=None):
            if name in {"torch", "lightglue", "kornia"}:
                raise ModuleNotFoundError(name=name)
            return object()

        with patch.object(deep_match_config_module.importlib, "import_module", side_effect=_fake_import):
            self.assertEqual(
                deep_match_config_module.check_deep_match_dependencies(runtime_config),
                ["missing torch", "missing lightglue", "missing kornia"],
            )

    def test_preflight_check_deep_match_dependencies_reports_loftr_and_superglue_missing_modules(self):
        dependency_scenarios = (
            (
                DeepMatchRuntimeConfig(
                    matcher_method="loftr",
                    feature_extractor_method="loftr",
                    prefer_gpu=False,
                    device_dtype="float32",
                    fallback_on_error=None,
                    raw_config={"matcher": {"method": "loftr"}},
                ),
                {"torch", "kornia.feature"},
                ["missing torch", "missing kornia.feature.LoFTR"],
            ),
            (
                DeepMatchRuntimeConfig(
                    matcher_method="superglue",
                    feature_extractor_method="superpoint",
                    prefer_gpu=False,
                    device_dtype="float32",
                    fallback_on_error=None,
                    raw_config={"matcher": {"method": "superglue"}},
                ),
                {"torch", "models.matching"},
                ["missing torch", "missing models.matching"],
            ),
        )

        for runtime_config, missing_modules, expected_messages in dependency_scenarios:
            with self.subTest(matcher_method=runtime_config.matcher_method):
                def _fake_import(name: str, package=None):
                    if name in missing_modules:
                        raise ModuleNotFoundError(name=name)
                    return object()

                with patch.object(deep_match_config_module.importlib, "import_module", side_effect=_fake_import):
                    self.assertEqual(
                        deep_match_config_module.check_deep_match_dependencies(runtime_config),
                        expected_messages,
                    )

    def test_build_argument_parser_accepts_manifest_runner_options(self):
        parser = build_argument_parser()

        parsed = parser.parse_args(
            [
                "manifest.json",
                "--device",
                "cuda",
                "--summary-output",
                "summary.json",
                "--fail-fast",
                "--skip-existing",
                "--num-workers",
                "3",
                "--torch-num-threads",
                "2",
            ]
        )

        self.assertEqual(parsed.manifest, "manifest.json")
        self.assertEqual(parsed.device, "cuda")
        self.assertEqual(parsed.summary_output, "summary.json")
        self.assertTrue(parsed.fail_fast)
        self.assertTrue(parsed.skip_existing)
        self.assertEqual(parsed.num_workers, 3)
        self.assertEqual(parsed.torch_num_threads, 2)

    def test_build_argument_parser_rejects_invalid_worker_counts(self):
        parser = build_argument_parser()

        for value in ("0", "65"):
            with self.subTest(num_workers=value):
                with self.assertRaises(SystemExit) as context:
                    parser.parse_args(["manifest.json", "--num-workers", value])
                self.assertEqual(context.exception.code, 2)

    def test_build_argument_parser_rejects_invalid_torch_num_threads(self):
        parser = build_argument_parser()

        with self.assertRaises(SystemExit) as context:
            parser.parse_args(["manifest.json", "--torch-num-threads", "0"])

        self.assertEqual(context.exception.code, 2)

    def test_build_argument_parser_rejects_skip_existing_with_force_rerun(self):
        parser = build_argument_parser()

        with self.assertRaises(SystemExit) as context:
            parser.parse_args(["manifest.json", "--skip-existing", "--force-rerun"])

        self.assertEqual(context.exception.code, 2)

    def test_run_manifest_writes_standard_result_npz_and_filters_invalid_mask_matches(self):
        with temporary_directory() as temp_dir:
            manifest = build_deep_match_pair_manifest(
                tasks=[_make_tile_task()],
                left_dom_path="left_dom.cub",
                right_dom_path="right_dom.cub",
                matcher_method="lightglue",
                band=1,
                image_space="dom",
                temp_root_dir=Path(temp_dir) / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
                requested_device="cpu",
                created_at_utc="2026-05-16T00:00:00Z",
            )
            record = manifest.tasks[0]
            left_mask = np.zeros((8, 8), dtype=bool)
            right_mask = np.zeros((8, 8), dtype=bool)
            left_mask[4, 4] = True
            write_deep_match_task_arrays(
                record,
                left_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                right_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                left_mask=left_mask,
                right_mask=right_mask,
            )
            manifest_path = write_deep_match_pair_manifest(manifest)

            summary = run_manifest(
                manifest_path,
                device="cpu",
                adapter_factory=FakeDeepMatcherAdapter,
            )
            result = read_deep_match_task_result(record)

            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["task_count"], 1)
            self.assertEqual(summary["succeeded_task_count"], 1)
            self.assertEqual(summary["failed_task_count"], 0)
            self.assertEqual(summary["tasks"][0]["raw_match_count"], 3)
            self.assertEqual(summary["tasks"][0]["invalid_mask_removed_count"], 1)
            self.assertEqual(result["metadata"]["status"], "matched")
            self.assertEqual(result["metadata"]["match_count"], 2)
            np.testing.assert_allclose(result["left_points"], np.array([[1.0, 1.0], [7.0, 7.0]], dtype=np.float32))
            np.testing.assert_allclose(result["right_points"], np.array([[2.0, 2.0], [7.0, 7.0]], dtype=np.float32))
            np.testing.assert_allclose(result["scores"], np.array([0.9, 0.7], dtype=np.float32), rtol=1e-6)
            self.assertTrue(Path(record.log_path).exists())

    def test_run_manifest_treats_uint8_masks_as_opencv_valid_pixel_masks(self):
        with temporary_directory() as temp_dir:
            manifest = build_deep_match_pair_manifest(
                tasks=[_make_tile_task()],
                left_dom_path="left_dom.cub",
                right_dom_path="right_dom.cub",
                matcher_method="lightglue",
                band=1,
                image_space="dom",
                temp_root_dir=Path(temp_dir) / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
                requested_device="cpu",
                created_at_utc="2026-05-16T00:00:00Z",
            )
            record = manifest.tasks[0]
            left_mask = np.full((8, 8), 255, dtype=np.uint8)
            right_mask = np.full((8, 8), 255, dtype=np.uint8)
            left_mask[4, 4] = 0
            right_mask[5, 5] = 0
            write_deep_match_task_arrays(
                record,
                left_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                right_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                left_mask=left_mask,
                right_mask=right_mask,
            )
            manifest_path = write_deep_match_pair_manifest(manifest)

            summary = run_manifest(
                manifest_path,
                device="cpu",
                adapter_factory=FakeDeepMatcherAdapter,
            )
            result = read_deep_match_task_result(record)

            self.assertEqual(summary["tasks"][0]["raw_match_count"], 3)
            self.assertEqual(summary["tasks"][0]["invalid_mask_removed_count"], 1)
            np.testing.assert_allclose(result["left_points"], np.array([[1.0, 1.0], [7.0, 7.0]], dtype=np.float32))
            np.testing.assert_allclose(result["right_points"], np.array([[2.0, 2.0], [7.0, 7.0]], dtype=np.float32))

    def test_run_manifest_passes_invalid_masks_into_adapter(self):
        with temporary_directory() as temp_dir:
            manifest = build_deep_match_pair_manifest(
                tasks=[_make_tile_task()],
                left_dom_path="left_dom.cub",
                right_dom_path="right_dom.cub",
                matcher_method="lightglue",
                band=1,
                image_space="dom",
                temp_root_dir=Path(temp_dir) / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
                requested_device="cpu",
                created_at_utc="2026-05-16T00:00:00Z",
            )
            record = manifest.tasks[0]
            left_mask = np.zeros((8, 8), dtype=bool)
            right_mask = np.zeros((8, 8), dtype=bool)
            left_mask[2, 2] = True
            right_mask[6, 6] = True
            write_deep_match_task_arrays(
                record,
                left_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                right_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                left_mask=left_mask,
                right_mask=right_mask,
            )
            manifest_path = write_deep_match_pair_manifest(manifest)
            created_adapters: list[FakeDeepMatcherAdapter] = []

            def _adapter_factory(*, prefer_gpu: bool, runtime_config=None):
                adapter = FakeDeepMatcherAdapter(prefer_gpu=prefer_gpu, runtime_config=runtime_config)
                created_adapters.append(adapter)
                return adapter

            run_manifest(
                manifest_path,
                device="cpu",
                adapter_factory=_adapter_factory,
            )

            self.assertEqual(len(created_adapters), 1)
            self.assertEqual(created_adapters[0].left_mask_shape, (8, 8))
            self.assertEqual(created_adapters[0].right_mask_shape, (8, 8))

    def test_run_manifest_preflight_failure_reports_python_and_stops_before_adapter_creation(self):
        with temporary_directory() as temp_dir:
            runtime_config = _make_runtime_config()
            task = replace(_make_tile_task(), deep_match_runtime_config=runtime_config)
            manifest = build_deep_match_pair_manifest(
                tasks=[task],
                left_dom_path="left_dom.cub",
                right_dom_path="right_dom.cub",
                matcher_method="lightglue",
                band=1,
                image_space="dom",
                temp_root_dir=Path(temp_dir) / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
                requested_device="cpu",
                created_at_utc="2026-05-16T00:00:00Z",
            )
            record = manifest.tasks[0]
            write_deep_match_task_arrays(
                record,
                left_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                right_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                left_mask=np.zeros((8, 8), dtype=bool),
                right_mask=np.zeros((8, 8), dtype=bool),
            )
            manifest_path = write_deep_match_pair_manifest(manifest)

            with patch(
                "run_deep_match_manifest.check_deep_match_dependencies",
                return_value=["missing lightglue"],
                create=True,
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    rf"Deep matcher preflight failed for 'lightglue' using Python {sys.executable}: missing lightglue",
                ):
                    run_manifest(
                        manifest_path,
                        device="cpu",
                        adapter_factory=lambda **kwargs: self.fail("adapter should not be created when preflight fails"),
                    )

    def test_run_manifest_rejects_manifest_and_runtime_config_matcher_mismatch(self):
        with temporary_directory() as temp_dir:
            runtime_config = _make_runtime_config()
            manifest = build_deep_match_pair_manifest(
                tasks=[replace(_make_tile_task(), deep_match_runtime_config=runtime_config)],
                left_dom_path="left_dom.cub",
                right_dom_path="right_dom.cub",
                matcher_method="loftr",
                band=1,
                image_space="dom",
                temp_root_dir=Path(temp_dir) / DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME,
                requested_device="cpu",
                created_at_utc="2026-05-16T00:00:00Z",
            )
            record = manifest.tasks[0]
            write_deep_match_task_arrays(
                record,
                left_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                right_image=np.arange(64, dtype=np.uint8).reshape(8, 8),
                left_mask=np.zeros((8, 8), dtype=bool),
                right_mask=np.zeros((8, 8), dtype=bool),
            )
            manifest_path = write_deep_match_pair_manifest(manifest)

            with self.assertRaisesRegex(
                ValueError,
                "Manifest matcher_method 'loftr' conflicts with runtime_config.matcher_method 'lightglue'",
            ):
                run_manifest(
                    manifest_path,
                    device="cpu",
                    adapter_factory=lambda **kwargs: self.fail("adapter should not be created on config mismatch"),
                )


if __name__ == "__main__":
    unittest.main()
