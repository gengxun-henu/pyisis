"""Focused unit tests for DOM matching SIFT helpers and invalid-value handling.

Author: Geng Xun
Created: 2026-04-16
Last Modified: 2026-05-28
Updated: 2026-04-16  Geng Xun added focused regression coverage for DOM cube block matching, global coordinate reassembly, and extreme special-pixel masking.
Updated: 2026-04-17  Geng Xun added regression coverage for tiled DOM matching when the paired DOM cubes differ slightly in raster size.
Updated: 2026-04-17  Geng Xun added focused regression coverage for configurable OpenCV SIFT CLI and detector parameters.
Updated: 2026-04-18  Geng Xun added focused regression coverage for merge-stage RANSAC filtering and default drawMatches visualization output naming.
Updated: 2026-04-18  Geng Xun added optional configurable real LRO DOM matching coverage while preserving repository fixture regressions.
Updated: 2026-04-19  Geng Xun added regression coverage for default image-match visualization output and the explicit no-write CLI switch.
Updated: 2026-04-21  Geng Xun added focused regression coverage for tile valid-pixel ratio filtering, 8-bit zero masking, and the new CLI threshold option.
Updated: 2026-04-22  Geng Xun added focused regression coverage for the default CPU process-pool tile-matching path and the new parallel opt-out CLI flags.
Updated: 2026-04-22  Geng Xun added focused regression coverage for configurable CPU process-pool worker limits in image_match.py.
Updated: 2026-04-23  Geng Xun added regression coverage for invalid-pixel-radius parsing and default low-resolution offset summary fields.
Updated: 2026-04-23  Geng Xun added focused regression coverage for batched projected keypoint conversion so low-resolution offset estimation no longer reopens the same cube for every retained point.
Updated: 2026-04-23  Geng Xun added regression coverage for ISIS reduce-based low-resolution DOM generation and fallback summary propagation.
Updated: 2026-04-24  Geng Xun added regression coverage for configurable low-resolution trimmed-mean fractions through the Python API, CLI, and config defaults.
Updated: 2026-04-26  Geng Xun added regression coverage for BF/FLANN matcher selection and low-resolution reprojection-error gating.
Updated: 2026-04-27  Geng Xun added regression coverage for minimum retained low-resolution matches and projected-offset magnitude gating.
Updated: 2026-05-01  Geng Xun added regression coverage for shell formatting helpers and config default lookup aliases.
Updated: 2026-05-01  Geng Xun added regression coverage for the CLI print-config-default helper path.
Updated: 2026-05-02  Geng Xun added regression coverage for precomputed low-resolution DOM reuse without repeated reduce calls.
Updated: 2026-05-02  Geng Xun added regression coverage for full-resolution image-match tile progress reporting.
Updated: 2026-05-02  Geng Xun added regression coverage for tile-validity prefilter config defaults and summary reporting.
Updated: 2026-05-02  Geng Xun adjusted tile-validity default config keys and prefilter default coverage.
Updated: 2026-05-02  Geng Xun refined tile-validity prefilter fixture to avoid degenerate valid tiles.
Updated: 2026-05-03  Geng Xun added regression coverage for batched parallel tile matching diagnostics.
Updated: 2026-05-03  Geng Xun added regression coverage for tile-validity metadata sidecar output.
Updated: 2026-05-03  Geng Xun added regression coverage for visualization option resolution and target-long-edge reduce levels.
Updated: 2026-05-04  Geng Xun added boundary regression coverage for integer-safe reduce-level calculation.
Updated: 2026-05-04  Geng Xun added regression coverage for crop-window visualization bounds and empty-point validation.
Updated: 2026-05-04  Geng Xun corrected crop-window clamping expectations for 0-based bounds.
Updated: 2026-05-05  Geng Xun added fractional crop-window coverage plus negative margin and out-of-bounds clamp tests.
Updated: 2026-05-06  Geng Xun updated crop-window negative-margin validation label expectations.
Updated: 2026-05-06  Geng Xun added auto full vs cropped visualization rendering coverage.
Updated: 2026-05-07  Geng Xun added visualization default-mode diagnostics and cropped offset assertions.
Updated: 2026-05-08  Geng Xun stabilized visualization reduced-mode guards and default full-mode mocks.
Updated: 2026-05-09  Geng Xun ensured full-mode visualization skips dimension probes and added explicit-full coverage.
Updated: 2026-05-10  Geng Xun added fail-fast coverage for reduced-cropped visualization mode.
Updated: 2026-05-11  Geng Xun added reduced-preview cache coverage for visualization rendering.
Updated: 2026-05-12  Geng Xun hardened reduced preview cache diagnostics and reduced-cropped window assertions.
Updated: 2026-05-12  Geng Xun added regression coverage for preview cache hash-key path normalization.
Updated: 2026-05-12  Geng Xun added cache-hit validation assertions for reduced preview cache reuse.
Updated: 2026-05-12  Geng Xun added regression coverage for corrupt preview cache regeneration.
Updated: 2026-05-14  Geng Xun added preview cache metadata validation coverage and regeneration diagnostics.
Updated: 2026-05-15  Geng Xun added reduced preview cache validation-failure regeneration tests.
Updated: 2026-05-16  Geng Xun added preview cache fingerprint and metadata corruption validation coverage.
Updated: 2026-05-16  Geng Xun added coverage for non-object preview cache metadata regeneration.
Updated: 2026-05-17  Geng Xun added parser/config coverage for visualization options and low-resolution target-long-edge matching.
Updated: 2026-05-18  Geng Xun added regression coverage for legacy positional API compatibility and visualization metadata sidecar output.
Updated: 2026-05-19  Geng Xun added regression coverage for visualization failure metadata sidecar output.
Updated: 2026-05-19  Geng Xun added regression coverage for shared deep matcher config path parsing and forwarding.
Updated: 2026-05-19  Geng Xun added runtime deep matcher config parsing and conflict detection coverage.
Updated: 2026-05-20  Geng Xun added GPU SIFT integration smoke coverage for tile_matching CPU/GPU shared API and GpuSiftBatch fallback.
Updated: 2026-05-20  Geng Xun added regression coverage for GPU tile matching delegation through the shared matcher.
Updated: 2026-05-20  Geng Xun added GPU tile no-feature contract regression coverage.
Updated: 2026-05-20  Geng Xun added config parser coverage for dynamic GPU batch defaults.
Updated: 2026-05-20  Geng Xun added CLI regression coverage for disabling dynamic GPU tile batching.
Updated: 2026-05-20  Geng Xun added prepared GPU tile payload prefilter coverage.
Updated: 2026-05-20  Geng Xun added GPU-only tile task routing coverage for the dedicated pipeline hook.
Updated: 2026-05-20  Geng Xun added regression coverage for GPU tile progress callbacks.
Updated: 2026-05-20  Geng Xun added stable GPU tile result ordering coverage.
Updated: 2026-05-20  Geng Xun added regression coverage for clamped dynamic GPU batch defaults.
Updated: 2026-05-20  Geng Xun added GPU tile status contract regression coverage.
Updated: 2026-05-20  Geng Xun added regression coverage for dynamic GPU batch option wiring.
Updated: 2026-05-20  Geng Xun added regression coverage for GPU backend summary diagnostics and cube cleanup on open failure.
Updated: 2026-05-20  Geng Xun added regression coverage for GPU summary configuration fields.
Updated: 2026-05-20  Geng Xun added regression coverage for conservative GPU batch defaults and effective GPU route gating.
Updated: 2026-05-20  Geng Xun added GPU fallback statistics regression coverage for dynamic batch feedback.
Updated: 2026-05-20  Geng Xun added regression coverage for batched GPU pair matcher dispatch.
Updated: 2026-05-20  Geng Xun added review regression coverage for effective GPU summaries and benchmark counts.
Updated: 2026-05-20  Geng Xun added runtime fallback coverage for effective GPU summary reporting.
Updated: 2026-05-20  Geng Xun added deep-adapter scaffolding regression coverage for cross-method fallback rejection and explicit dependency errors.
Updated: 2026-05-20  Geng Xun added deep matcher dispatch regression coverage for lightglue routing and loftr GPU-preferred fallback calls.
Updated: 2026-05-20  Geng Xun added deep adapter normalization coverage for canonical keypoint/match triplet outputs.
Updated: 2026-05-20  Geng Xun added regression coverage ensuring lightweight deep fallback frontends and matchers emit deterministic non-empty correspondences for non-empty inputs.
Updated: 2026-05-21  Geng Xun replaced synthetic deep correspondences assertions with explicit missing-dependency error coverage.
Updated: 2026-05-22  Geng Xun added deep dependency normalization and deep adapter reuse regression coverage for tile dispatch.
Updated: 2026-05-22  Geng Xun added ori-space entrypoint regression coverage for superpoint routing and fail-fast dependency errors.
Updated: 2026-05-22  Geng Xun added regression coverage for dom/ori image-space backend construction helpers.
Updated: 2026-05-22  Geng Xun added ORI key export regression coverage for pair-level `.key` output summaries.
Updated: 2026-05-22  Geng Xun tightened ORI delegation and `.key` file readability regression coverage for Task 3 review fixes.
Updated: 2026-05-22  Geng Xun added matcher preset option resolution and constructor-forwarding regression coverage.
Updated: 2026-05-27  Geng Xun added metadata regression coverage for ImageMatch tile block alignment modes.
Updated: 2026-05-27  Geng Xun added regression coverage for non-ready DOM preparation with tile block alignment enabled.
Updated: 2026-05-27  Geng Xun added metadata regression coverage for tile cache diagnostics.
Updated: 2026-05-27  Geng Xun added regression coverage for worker-local parallel tile cache metadata.
Updated: 2026-05-22  Geng Xun added fail-fast matcher and extractor compatibility regression coverage for deep presets.
Updated: 2026-05-14  Geng Xun added regression coverage for adaptive-routing parser defaults, config loading, execution-time matcher overrides, and metadata sidecars.
Updated: 2026-05-14  Geng Xun added regression coverage for adaptive fallback cascade execution after failed quality gating.
Updated: 2026-05-16  Geng Xun added regression coverage for adaptive-routing profile CLI/config defaults and expanded metadata.
Updated: 2026-05-27  Geng Xun added parser/config regression coverage for the new --opencv-num-threads CLI option and ImageMatch config alias validation.
Updated: 2026-05-27  Geng Xun added worker-shard regression coverage for applying explicit OpenCV thread limits.
Updated: 2026-05-28  Geng Xun aligned adaptive-routing serial tile mocks with TileMatchBatchResult return contracts.
"""

from __future__ import annotations

import hashlib
import inspect
import io
import importlib
from datetime import datetime
import json
import os
import sys
import tempfile
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock

import cv2
import numpy as np


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import attach_dom_like_projection_mapping, ip, make_test_cube, make_tile_test_cube, temporary_directory, workspace_test_data_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

image_match = importlib.import_module("controlnet_construct.image_match")
controlnet_stereopair_module = importlib.import_module("controlnet_construct.controlnet_stereopair")
deep_match_config_module = importlib.import_module("controlnet_construct.deep_match_config")
match_visualization_module = importlib.import_module("controlnet_construct.match_visualization")
lowres_offset_module = importlib.import_module("controlnet_construct.lowres_offset")
from image_match.adaptive_routing import ImageTextureProbe
from image_match.lighting_difference import SolarGeometry
from image_match.texture_sparseness import ImageSparsenessSummary

build_image_match_argument_parser = image_match.build_argument_parser
build_argument_parser = build_image_match_argument_parser
build_controlnet_stereopair_argument_parser = controlnet_stereopair_module.build_argument_parser
default_match_visualization_path = image_match.default_match_visualization_path
filter_stereo_pair_keypoints_with_ransac = image_match.filter_stereo_pair_keypoints_with_ransac
match_dom_pair = image_match.match_dom_pair
match_dom_pair_to_key_files = image_match.match_dom_pair_to_key_files
write_stereo_pair_match_visualization_from_key_files = image_match.write_stereo_pair_match_visualization_from_key_files

tile_matching_module = importlib.import_module("controlnet_construct.tile_matching")


def _tile_match_batch_result(*results):
    return tile_matching_module.TileMatchBatchResult(results=list(results))
tile_matching = tile_matching_module
TileWindow = tile_matching_module.TileWindow

keypoints_module = importlib.import_module("controlnet_construct.keypoints")
Keypoint = keypoints_module.Keypoint
KeypointFile = keypoints_module.KeypointFile
write_key_file = keypoints_module.write_key_file
read_key_file = keypoints_module.read_key_file


FIXTURE_DOM_LEFT = workspace_test_data_path("hidtmgen", "ortho", "PSP_002118_1510_1m_o_forPDS_cropped.cub")
FIXTURE_DOM_RIGHT = workspace_test_data_path("hidtmgen", "ortho", "PSP_002118_1510_25cm_o_forPDS_cropped.cub")
REAL_LRO_DOM_LEFT_ENV = "ISIS_PYBIND_MATCHING_REAL_DOM_LEFT_CUBE"
REAL_LRO_DOM_RIGHT_ENV = "ISIS_PYBIND_MATCHING_REAL_DOM_RIGHT_CUBE"
DEFAULT_REAL_LRO_DOM_LEFT = Path("/media/gengxun/Elements/data/lro/test_controlnet_python/dom_M104311715LE.cub")
DEFAULT_REAL_LRO_DOM_RIGHT = Path("/media/gengxun/Elements/data/lro/test_controlnet_python/dom_M104318871RE.cub")
SPECIAL_PIXEL = -1.797693134862315e308


class _EvalToDeviceModule:
    def __init__(self) -> None:
        self.device: str | None = None
        self.dtype = None

    def eval(self):
        return self

    def to(self, device: str | None = None, *, dtype=None):
        if device is not None:
            self.device = device
        if dtype is not None:
            self.dtype = dtype
        return self


class _FakeTorchTensor:
    def __init__(self, array) -> None:
        self.array = np.asarray(array)
        self.device = None
        self.dtype = None

    def __getitem__(self, key):
        return _FakeTorchTensor(self.array[key])

    def to(self, *args, **kwargs):
        if args:
            self.device = args[0]
        if "device" in kwargs:
            self.device = kwargs["device"]
        if "dtype" in kwargs:
            self.dtype = kwargs["dtype"]
        return self

    def detach(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.array


class _FakeTorchNoGrad:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


def _fake_torch_module():
    return _stub_module(
        "torch",
        from_numpy=lambda array: _FakeTorchTensor(array),
        no_grad=lambda: _FakeTorchNoGrad(),
    )


def _stub_module(name: str, **attributes):
    module = ModuleType(name)
    if name == "torch":
        attributes.setdefault("float32", "torch.float32")
        attributes.setdefault("float16", "torch.float16")
        attributes.setdefault("bfloat16", "torch.bfloat16")
    for key, value in attributes.items():
        setattr(module, key, value)
    return module


def _configured_real_lro_dom_pair() -> tuple[Path, Path]:
    left_dom = Path(os.environ.get(REAL_LRO_DOM_LEFT_ENV, str(DEFAULT_REAL_LRO_DOM_LEFT))).expanduser()
    right_dom = Path(os.environ.get(REAL_LRO_DOM_RIGHT_ENV, str(DEFAULT_REAL_LRO_DOM_RIGHT))).expanduser()
    return left_dom, right_dom


def _write_array_to_cube(cube: ip.Cube, values: np.ndarray) -> None:
    manager = ip.LineManager(cube)
    manager.begin()
    while not manager.end():
        line_index = manager.line() - 1
        for index in range(len(manager)):
            manager[index] = float(values[line_index, index])
        cube.write(manager)
        manager.next()


def _build_textured_test_image(width: int, height: int) -> np.ndarray:
    image = np.zeros((height, width), dtype=np.uint8)
    cv2.circle(image, (width // 4, height // 4), 12, 180, thickness=-1)
    cv2.circle(image, (3 * width // 4, height // 4), 10, 220, thickness=2)
    cv2.rectangle(image, (20, height // 2), (width // 2, height - 20), 140, thickness=3)
    cv2.line(image, (0, height - 1), (width - 1, 0), 255, thickness=2)
    cv2.putText(image, "ISIS", (width // 3, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 200, 2)
    return image.astype(np.float64)


def _write_preview_cache_metadata(
    preview_path: Path,
    *,
    source_hash_key: str,
    level: int,
    source_path: str | Path,
    source_fingerprint: dict[str, int] | None = None,
) -> Path:
    resolved_fingerprint = (
        source_fingerprint
        if source_fingerprint is not None
        else match_visualization_module._preview_cache_source_fingerprint(source_path)
    )
    metadata = {
        "source_hash_key": source_hash_key,
        "level": int(level),
        "source_path": str(source_path),
        "source_fingerprint": resolved_fingerprint,
        "preview_path": str(preview_path),
    }
    metadata_path = match_visualization_module._preview_cache_metadata_path(preview_path)
    metadata_path.write_text(json.dumps(metadata, sort_keys=True, indent=2), encoding="utf-8")
    return metadata_path


def _write_projected_dom_pair(
    temp_dir: Path,
    left_values: np.ndarray,
    right_values: np.ndarray | None = None,
    *,
    pixel_type=ip.PixelType.Real,
    left_name: str = "left_dom.cub",
    right_name: str = "right_dom.cub",
) -> tuple[Path, Path]:
    left_array = np.asarray(left_values, dtype=np.float64)
    right_array = left_array if right_values is None else np.asarray(right_values, dtype=np.float64)
    height, width = left_array.shape

    left_cube, left_path = make_test_cube(
        temp_dir,
        name=left_name,
        samples=width,
        lines=height,
        bands=1,
        pixel_type=pixel_type,
    )
    right_cube, right_path = make_test_cube(
        temp_dir,
        name=right_name,
        samples=right_array.shape[1],
        lines=right_array.shape[0],
        bands=1,
        pixel_type=pixel_type,
    )
    try:
        _write_array_to_cube(left_cube, left_array)
        _write_array_to_cube(right_cube, right_array)
        attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
        attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(right_array.shape[0]))
    finally:
        left_cube.close()
        right_cube.close()

    return left_path, right_path


class ControlNetConstructMatchingUnitTest(unittest.TestCase):
    def test_create_low_resolution_dom_uses_isis_reduce_scale_mode(self):
        with temporary_directory() as temp_dir:
            source_path = temp_dir / "source_input.cub"
            output_path = temp_dir / "reduced_output.cub"
            source_path.write_bytes(b"fake cube bytes")

            with mock.patch.object(image_match, "_run_command") as run_command_mock, mock.patch.object(
                image_match,
                "_validate_projection_ready_cube",
                return_value=10.0,
            ) as validate_mock:
                result = image_match._create_low_resolution_dom(source_path, output_path, level=3)

        self.assertEqual(result, output_path)
        run_command_mock.assert_called_once_with(
            [
                "reduce",
                f"from={source_path}",
                f"to={output_path}",
                "mode=scale",
                "sscale=8",
                "lscale=8",
                "algorithm=AVERAGE",
            ]
        )
        validate_mock.assert_called_once_with(output_path)

    def test_create_low_resolution_dom_level_zero_copies_source_without_reduce(self):
        with temporary_directory() as temp_dir:
            source_path = temp_dir / "source_level_zero.cub"
            output_path = temp_dir / "copied_level_zero.cub"
            source_path.write_bytes(b"level-zero-copy")

            with mock.patch.object(image_match, "_run_command") as run_command_mock, mock.patch.object(
                image_match,
                "_validate_projection_ready_cube",
                return_value=10.0,
            ) as validate_mock:
                result = image_match._create_low_resolution_dom(source_path, output_path, level=0)

            self.assertEqual(result, output_path)
            self.assertEqual(output_path.read_bytes(), b"level-zero-copy")

        run_command_mock.assert_not_called()
        validate_mock.assert_called_once_with(output_path)

    def test_estimate_low_resolution_projected_offset_reuses_precomputed_doms_without_reduce(self):
        with temporary_directory() as temp_dir:
            left_precomputed = temp_dir / "left_cached_low.cub"
            right_precomputed = temp_dir / "right_cached_low.cub"
            left_pair_local = temp_dir / "left_pair_low.cub"
            right_pair_local = temp_dir / "right_pair_low.cub"
            left_precomputed.write_bytes(b"left-low")
            right_precomputed.write_bytes(b"right-low")

            create_mock = mock.Mock(side_effect=AssertionError("reduce should not run for precomputed DOMs"))
            copy_mock = mock.Mock(side_effect=[left_pair_local, right_pair_local])

            summary = image_match._estimate_low_resolution_projected_offset(
                "left_dom.cub",
                "right_dom.cub",
                enabled=True,
                low_resolution_level=3,
                low_resolution_output_dir=temp_dir,
                band=1,
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=64,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=1,
                matcher_method="bf",
                ratio_test=0.75,
                max_features=None,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                low_resolution_trim_fraction_each_side=0.05,
                left_low_resolution_dom=left_precomputed,
                right_low_resolution_dom=right_precomputed,
                match_dom_pair_func=mock.Mock(
                    return_value=(KeypointFile(10, 10, ()), KeypointFile(10, 10, ()), {"status": "matched_no_points"})
                ),
                filter_stereo_pair_keypoints_with_ransac_func=mock.Mock(
                    return_value=(KeypointFile(10, 10, ()), KeypointFile(10, 10, ()), {"applied": False})
                ),
                write_stereo_pair_match_visualization_func=mock.Mock(),
                require_command_func=mock.Mock(),
                create_low_resolution_dom_func=create_mock,
                copy_precomputed_low_resolution_dom_func=copy_mock,
            )

        create_mock.assert_not_called()
        copy_mock.assert_has_calls(
            [
                mock.call(left_precomputed, temp_dir / "left_dom__level3.cub"),
                mock.call(right_precomputed, temp_dir / "right_dom__level3.cub"),
            ]
        )
        self.assertEqual(summary["status"], "fallback_zero")
        self.assertEqual(summary["failure_reason_code"], "no_matches")
        self.assertEqual(summary["left_low_resolution_dom"], str(left_pair_local))
        self.assertEqual(summary["right_low_resolution_dom"], str(right_pair_local))
        self.assertEqual(summary["low_resolution_dom_sources"]["left"]["mode"], "precomputed_copy")
        self.assertEqual(summary["low_resolution_dom_sources"]["left"]["cache_dom"], str(left_precomputed))

    def test_estimate_low_resolution_projected_offset_reports_reduce_generation_failure(self):
        with temporary_directory() as temp_dir:
            with mock.patch.object(image_match, "_require_command") as require_command_mock, mock.patch.object(
                image_match,
                "_create_low_resolution_dom",
                side_effect=RuntimeError("reduce failed for synthetic test"),
            ):
                summary = image_match._estimate_low_resolution_projected_offset(
                    "left_dom.cub",
                    "right_dom.cub",
                    enabled=True,
                    low_resolution_level=3,
                    low_resolution_output_dir=temp_dir,
                    band=1,
                    minimum_value=None,
                    maximum_value=None,
                    lower_percent=0.5,
                    upper_percent=99.5,
                    invalid_values=(),
                    special_pixel_abs_threshold=1.0e300,
                    min_valid_pixels=64,
                    valid_pixel_percent_threshold=0.0,
                    invalid_pixel_radius=1,
                    matcher_method="bf",
                    ratio_test=0.75,
                    max_features=None,
                    sift_octave_layers=3,
                    sift_contrast_threshold=0.04,
                    sift_edge_threshold=10.0,
                    sift_sigma=1.6,
                    low_resolution_trim_fraction_each_side=0.05,
                )

        require_command_mock.assert_called_once_with("reduce")
        self.assertTrue(summary["enabled"])
        self.assertEqual(summary["status"], "fallback_zero")
        self.assertTrue(summary["fallback_offset_zero"])
        self.assertIn("reduce failed for synthetic test", summary["reason"])
        self.assertEqual(summary["delta_x_projected"], 0.0)
        self.assertEqual(summary["delta_y_projected"], 0.0)
        self.assertEqual(summary["retained_match_count"], 0)
        self.assertEqual(summary["trim_fraction_each_side"], 0.05)

    def test_trimmed_mean_allows_custom_fraction_and_rejects_invalid_values(self):
        self.assertAlmostEqual(
            image_match._trimmed_mean([1.0, 2.0, 3.0, 100.0], trim_ratio=0.25),
            2.5,
        )

        with self.assertRaisesRegex(ValueError, r"trim_fraction_each_side must be within \[0\.0, 0\.5\)"):
            image_match._trimmed_mean([1.0, 2.0, 3.0], trim_ratio=0.5)

    def test_format_image_match_default_for_shell_normalizes_scalars(self):
        self.assertEqual(image_match.format_image_match_default_for_shell(True), "1")
        self.assertEqual(image_match.format_image_match_default_for_shell(False), "0")
        self.assertEqual(image_match.format_image_match_default_for_shell(6), "6")
        self.assertEqual(image_match.format_image_match_default_for_shell(0.05), "0.05")
        self.assertEqual(image_match.format_image_match_default_for_shell("bf"), "bf")

    def test_print_image_match_config_default_reads_existing_parser_aliases(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "validPixelPercentThreshold": 0.07,
                            "useParallelCpu": False,
                            "numWorkerParallelCpu": 4,
                            "matcherMethod": "flann",
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                image_match.print_image_match_config_default(config_path, "valid_pixel_percent_threshold"),
                "0.07",
            )
            self.assertEqual(image_match.print_image_match_config_default(config_path, "use_parallel_cpu"), "0")
            self.assertEqual(image_match.print_image_match_config_default(config_path, "num_worker_parallel_cpu"), "4")
            self.assertEqual(image_match.print_image_match_config_default(config_path, "matcher_method"), "flann")

    def test_print_image_match_config_default_reads_tile_validity_fields(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "enableTileValidityPrefilter": True,
                            "tileValidityCellWidth": 256,
                        }
                    }
                ),
                encoding="utf-8",
            )
            enabled = image_match.print_image_match_config_default(config_path, "enable_tile_validity_prefilter")
            cell_width = image_match.print_image_match_config_default(config_path, "tile_validity_cell_width")

        self.assertEqual(enabled, "1")
        self.assertEqual(cell_width, "256")

    def test_print_image_match_config_default_reads_gpu_dynamic_batch_fields(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "useGpu": True,
                            "gpuBatchSize": 8,
                            "gpuDynamicBatch": True,
                            "gpuMinBatchSize": 2,
                            "gpuMaxBatchSize": 16,
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(image_match.print_image_match_config_default(config_path, "use_gpu"), "1")
            self.assertEqual(image_match.print_image_match_config_default(config_path, "gpu_batch_size"), "8")
            self.assertEqual(image_match.print_image_match_config_default(config_path, "gpu_dynamic_batch"), "1")
            self.assertEqual(image_match.print_image_match_config_default(config_path, "gpu_min_batch_size"), "2")
            self.assertEqual(image_match.print_image_match_config_default(config_path, "gpu_max_batch_size"), "16")

    def test_print_image_match_config_default_reads_omit_tile_details_flag(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "omitTileDetails": True,
                        }
                    }
                ),
                encoding="utf-8",
            )

            omit_tile_details = image_match.print_image_match_config_default(config_path, "omit_tile_details")

        self.assertEqual(omit_tile_details, "1")

    def test_print_image_match_config_default_returns_empty_string_for_missing_field(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(json.dumps({"ImageMatch": {}}), encoding="utf-8")

            self.assertEqual(image_match.print_image_match_config_default(config_path, "low_resolution_level"), "")

    def test_image_match_cli_print_config_default_exits_before_positional_args(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps({"ImageMatch": {"enableLowResolutionOffsetEstimation": True}}),
                encoding="utf-8",
            )

            with mock.patch("sys.stdout") as stdout_mock:
                image_match.main(
                    [
                        "--config",
                        str(config_path),
                        "--print-config-default",
                        "enable_low_resolution_offset_estimation",
                    ]
                )

        stdout_mock.write.assert_any_call("1")

    def test_projected_xy_from_keypoints_opens_cube_once_and_preserves_input_order(self):
        class FakeProjection:
            def __init__(self):
                self.calls: list[tuple[float, float]] = []
                self._sample = 0.0
                self._line = 0.0

            def set_world(self, sample: float, line: float) -> bool:
                self.calls.append((sample, line))
                self._sample = sample
                self._line = line
                return True

            def x_coord(self) -> float:
                return self._sample + 1000.0

            def y_coord(self) -> float:
                return self._line + 2000.0

        class FakeCube:
            def __init__(self):
                self.open_calls: list[tuple[str, str]] = []
                self.close_call_count = 0
                self._is_open = False
                self._projection = FakeProjection()

            def open(self, path: str, mode: str) -> None:
                self.open_calls.append((path, mode))
                self._is_open = True

            def projection(self) -> FakeProjection:
                return self._projection

            def is_open(self) -> bool:
                return self._is_open

            def close(self) -> None:
                self.close_call_count += 1
                self._is_open = False

        fake_cube = FakeCube()
        points = (
            Keypoint(10.5, 20.5),
            Keypoint(30.25, 40.75),
            Keypoint(5.0, 6.0),
        )

        with mock.patch.object(image_match.ip, "Cube", return_value=fake_cube):
            projected_points = image_match._projected_xy_from_keypoints("fake_lowres.cub", points)

        self.assertEqual(fake_cube.open_calls, [("fake_lowres.cub", "r")])
        self.assertEqual(fake_cube.close_call_count, 1)
        self.assertEqual(fake_cube._projection.calls, [(10.5, 20.5), (30.25, 40.75), (5.0, 6.0)])
        self.assertEqual(
            projected_points,
            (
                (1010.5, 2020.5),
                (1030.25, 2040.75),
                (1005.0, 2006.0),
            ),
        )

    def test_projected_xy_from_keypoints_in_open_cube_raises_with_failed_point_context(self):
        class FakeProjection:
            def set_world(self, sample: float, line: float) -> bool:
                return (sample, line) != (8.0, 9.0)

            def x_coord(self) -> float:
                return 0.0

            def y_coord(self) -> float:
                return 0.0

        class FakeCube:
            def __init__(self):
                self.projection_call_count = 0

            def projection(self) -> FakeProjection:
                self.projection_call_count += 1
                return FakeProjection()

        fake_cube = FakeCube()

        with self.assertRaisesRegex(
            RuntimeError,
            r"Failed to convert keypoint sample/line to projected coordinates for failing_lowres\.cub: \(8\.0, 9\.0\)",
        ):
            image_match._projected_xy_from_keypoints_in_open_cube(
                fake_cube,
                "failing_lowres.cub",
                (Keypoint(1.0, 2.0), Keypoint(8.0, 9.0)),
            )

        self.assertEqual(fake_cube.projection_call_count, 1)

    def test_default_match_visualization_path_uses_auto_timestamped_name(self):
        timestamp = datetime(2026, 4, 18, 18, 44, 32)

        output_path = default_match_visualization_path(
            "left/A.cub",
            "right/B.cub",
            output_directory="/tmp/rendered",
            timestamp=timestamp,
        )

        self.assertEqual(str(output_path), "/tmp/rendered/A__B__20260418T184432.png")

    def test_filter_stereo_pair_keypoints_with_ransac_strict_drops_marked_outlier(self):
        left_key_file = KeypointFile(
            100,
            100,
            (
                Keypoint(1.0, 1.0),
                Keypoint(11.0, 1.0),
                Keypoint(1.0, 11.0),
                Keypoint(11.0, 11.0),
                Keypoint(6.0, 6.0),
            ),
        )
        right_key_file = KeypointFile(
            100,
            100,
            (
                Keypoint(3.0, 4.0),
                Keypoint(13.0, 4.0),
                Keypoint(3.0, 14.0),
                Keypoint(13.0, 14.0),
                Keypoint(30.0, 30.0),
            ),
        )
        homography = np.array([[1.0, 0.0, 2.0], [0.0, 1.0, 3.0], [0.0, 0.0, 1.0]], dtype=np.float64)
        mask = np.array([[1], [1], [1], [1], [0]], dtype=np.uint8)

        with mock.patch.object(image_match.cv2, "findHomography", return_value=(homography, mask)):
            filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_with_ransac(
                left_key_file,
                right_key_file,
                ransac_mode="strict",
            )

        self.assertEqual(summary["mode"], "strict")
        self.assertEqual(summary["retained_count"], 4)
        self.assertEqual(summary["dropped_count"], 1)
        self.assertEqual(summary["opencv_outlier_count"], 1)
        self.assertEqual(summary["retained_soft_outlier_count"], 0)
        self.assertEqual(len(filtered_left.points), 4)
        self.assertEqual(len(filtered_right.points), 4)

    def test_filter_stereo_pair_keypoints_with_ransac_loose_keeps_small_reprojection_soft_outlier(self):
        left_key_file = KeypointFile(
            100,
            100,
            (
                Keypoint(1.0, 1.0),
                Keypoint(11.0, 1.0),
                Keypoint(1.0, 11.0),
                Keypoint(11.0, 11.0),
                Keypoint(6.0, 6.0),
            ),
        )
        right_key_file = KeypointFile(
            100,
            100,
            (
                Keypoint(3.0, 4.0),
                Keypoint(13.0, 4.0),
                Keypoint(3.0, 14.0),
                Keypoint(13.0, 14.0),
                Keypoint(8.6, 9.4),
            ),
        )
        homography = np.array([[1.0, 0.0, 2.0], [0.0, 1.0, 3.0], [0.0, 0.0, 1.0]], dtype=np.float64)
        mask = np.array([[1], [1], [1], [1], [0]], dtype=np.uint8)

        with mock.patch.object(image_match.cv2, "findHomography", return_value=(homography, mask)):
            filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_with_ransac(
                left_key_file,
                right_key_file,
                ransac_mode="loose",
                loose_keep_pixel_threshold=1.0,
            )

        self.assertEqual(summary["mode"], "loose")
        self.assertEqual(summary["retained_count"], 5)
        self.assertEqual(summary["dropped_count"], 0)
        self.assertEqual(summary["opencv_outlier_count"], 1)
        self.assertEqual(summary["retained_soft_outlier_count"], 1)
        self.assertEqual(summary["soft_outlier_original_indices"], [4])
        self.assertEqual(summary["retained_soft_outlier_positions"], [4])
        self.assertEqual(len(filtered_left.points), 5)
        self.assertEqual(len(filtered_right.points), 5)

    def test_build_argument_parser_accepts_custom_sift_parameters(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--max-features",
                "4096",
                "--sift-octave-layers",
                "5",
                "--sift-contrast-threshold",
                "0.02",
                "--sift-edge-threshold",
                "15.5",
                "--sift-sigma",
                "1.2",
            ]
        )

        self.assertEqual(args.max_features, 4096)
        self.assertEqual(args.sift_octave_layers, 5)
        self.assertAlmostEqual(args.sift_contrast_threshold, 0.02)
        self.assertAlmostEqual(args.sift_edge_threshold, 15.5)
        self.assertAlmostEqual(args.sift_sigma, 1.2)

    def test_build_argument_parser_defaults_to_writing_match_visualization_and_allows_disabling_it(self):
        parser = build_argument_parser()

        default_args = parser.parse_args(["left.cub", "right.cub", "left.key", "right.key"])
        disabled_args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--no-write-match-visualization",
            ]
        )

        self.assertTrue(default_args.write_match_visualization)
        self.assertFalse(disabled_args.write_match_visualization)

    def test_build_argument_parser_defaults_to_parallel_cpu_and_allows_disabling_it(self):
        parser = build_argument_parser()

        default_args = parser.parse_args(["left.cub", "right.cub", "left.key", "right.key"])
        disabled_args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--no-parallel-cpu",
            ]
        )
        explicit_enabled_args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--use-parallel-cpu",
            ]
        )

        self.assertTrue(default_args.use_parallel_cpu)
        self.assertEqual(default_args.num_worker_parallel_cpu, 8)
        self.assertFalse(disabled_args.use_parallel_cpu)
        self.assertTrue(explicit_enabled_args.use_parallel_cpu)

    def test_build_argument_parser_defaults_to_adaptive_routing_off_and_allows_switching_it(self):
        parser = build_argument_parser()

        default_args = parser.parse_args(["left.cub", "right.cub", "left.key", "right.key"])
        enabled_args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--adaptive-routing",
            ]
        )
        disabled_args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--adaptive-routing",
                "--no-adaptive-routing",
            ]
        )

        self.assertFalse(default_args.enable_adaptive_routing)
        self.assertTrue(enabled_args.enable_adaptive_routing)
        self.assertFalse(disabled_args.enable_adaptive_routing)
        self.assertEqual(default_args.adaptive_routing_profile, "balanced")

    def test_build_argument_parser_accepts_adaptive_routing_profile(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--adaptive-routing-profile",
                "strict",
            ]
        )

        self.assertEqual(args.adaptive_routing_profile, "strict")

    def test_image_match_parser_uses_shared_parameter_value_rules(self):
        parser = build_image_match_argument_parser()

        valid_args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--matcher-method",
                "lightglue",
                "--deep-match-mode",
                "export",
                "--adaptive-routing-profile",
                "relaxed",
                "--visualization-mode",
                "reduced-cropped",
                "--memory-profile",
                "low-memory",
                "--preview-cache-source",
                "matching-cache",
            ]
        )

        self.assertEqual(valid_args.matcher_method, "lightglue")
        self.assertEqual(valid_args.deep_match_mode, "export")
        self.assertEqual(valid_args.adaptive_routing_profile, "relaxed")
        self.assertEqual(valid_args.visualization_mode, "reduced_cropped")
        self.assertEqual(valid_args.memory_profile, "low-memory")
        self.assertEqual(valid_args.preview_cache_source, "matching_cache")

        for flag, value in (
            ("--matcher-method", "unknown"),
            ("--deep-match-mode", "bad"),
            ("--adaptive-routing-profile", "bad"),
            ("--visualization-mode", "bad"),
            ("--memory-profile", "bad"),
            ("--preview-cache-source", "bad"),
        ):
            with self.subTest(flag=flag, value=value), self.assertRaises(SystemExit):
                parser.parse_args(["left.cub", "right.cub", "left.key", "right.key", flag, value])

    def test_controlnet_stereopair_parser_uses_shared_visualization_rules(self):
        parser = build_controlnet_stereopair_argument_parser()

        parsed = parser.parse_args(
            [
                "from-dom-batch",
                "overlap.lis",
                "original.lis",
                "doms.lis",
                "dom_keys",
                "config.json",
                "pair_nets",
                "--visualization-mode",
                "reduced-cropped",
                "--memory-profile",
                "low-memory",
                "--preview-cache-source",
                "matching-cache",
            ]
        )

        self.assertEqual(parsed.visualization_mode, "reduced_cropped")
        self.assertEqual(parsed.memory_profile, "low-memory")
        self.assertEqual(parsed.preview_cache_source, "matching_cache")

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "from-dom-batch",
                    "overlap.lis",
                    "original.lis",
                    "doms.lis",
                    "dom_keys",
                    "config.json",
                    "pair_nets",
                    "--visualization-mode",
                    "bad",
                ]
            )

    def test_build_argument_parser_accepts_deep_match_config_path(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "--deep-match-config-path",
                "examples/controlnet_construct/presets/lightglue_default.json",
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
            ]
        )

        self.assertEqual(
            str(args.deep_match_config_path),
            "examples/controlnet_construct/presets/lightglue_default.json",
        )

    def test_build_argument_parser_accepts_custom_parallel_worker_limit(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--num-worker-parallel-cpu",
                "32",
            ]
        )

        self.assertEqual(args.num_worker_parallel_cpu, 32)

    def test_build_argument_parser_rejects_out_of_range_parallel_worker_limit(self):
        parser = build_argument_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--num-worker-parallel-cpu",
                    "0",
                ]
            )

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--num-worker-parallel-cpu",
                    "4097",
                ]
            )

    def test_build_argument_parser_accepts_opencv_num_threads(self):
        parser = build_argument_parser()

        default_args = parser.parse_args(["left.cub", "right.cub", "left.key", "right.key"])
        explicit_args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--opencv-num-threads",
                "1",
            ]
        )

        self.assertIsNone(default_args.opencv_num_threads)
        self.assertEqual(explicit_args.opencv_num_threads, 1)

    def test_build_argument_parser_rejects_invalid_opencv_num_threads(self):
        parser = build_argument_parser()

        for value in ("0", "-1", "1.5", "auto"):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                parser.parse_args(
                    [
                        "left.cub",
                        "right.cub",
                        "left.key",
                        "right.key",
                        "--opencv-num-threads",
                        value,
                    ]
                )

    def test_print_image_match_config_default_reads_opencv_num_threads(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps({"ImageMatch": {"opencvNumThreads": 2}}),
                encoding="utf-8",
            )

            self.assertEqual(
                image_match.print_image_match_config_default(config_path, "opencv_num_threads"),
                "2",
            )

    def test_image_match_config_rejects_invalid_opencv_num_threads(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps({"ImageMatch": {"opencv_num_threads": 0}}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "opencv_num_threads"):
                image_match.load_image_match_defaults_from_config(config_path)

    def test_apply_opencv_thread_config_skips_when_unset(self):
        calls = []
        original_set = image_match.cv2.setNumThreads
        original_get = image_match.cv2.getNumThreads
        original_optimized = image_match.cv2.useOptimized
        image_match.cv2.setNumThreads = lambda value: calls.append(value)
        image_match.cv2.getNumThreads = lambda: 8
        image_match.cv2.useOptimized = lambda: True
        try:
            summary = image_match._apply_opencv_thread_config(None)
        finally:
            image_match.cv2.setNumThreads = original_set
            image_match.cv2.getNumThreads = original_get
            image_match.cv2.useOptimized = original_optimized

        self.assertEqual(calls, [])
        self.assertFalse(summary["opencv_num_threads_configured"])
        self.assertIsNone(summary["opencv_num_threads_requested"])
        self.assertEqual(summary["opencv_num_threads_effective"], 8)
        self.assertTrue(summary["opencv_use_optimized"])

    def test_apply_opencv_thread_config_sets_positive_value(self):
        calls = []
        original_set = image_match.cv2.setNumThreads
        original_get = image_match.cv2.getNumThreads
        original_optimized = image_match.cv2.useOptimized
        image_match.cv2.setNumThreads = lambda value: calls.append(value)
        image_match.cv2.getNumThreads = lambda: calls[-1]
        image_match.cv2.useOptimized = lambda: True
        try:
            summary = image_match._apply_opencv_thread_config(2)
        finally:
            image_match.cv2.setNumThreads = original_set
            image_match.cv2.getNumThreads = original_get
            image_match.cv2.useOptimized = original_optimized

        self.assertEqual(calls, [2])
        self.assertTrue(summary["opencv_num_threads_configured"])
        self.assertEqual(summary["opencv_num_threads_requested"], 2)
        self.assertEqual(summary["opencv_num_threads_effective"], 2)

    def test_build_argument_parser_accepts_valid_pixel_percent_threshold(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--valid-pixel-percent-threshold",
                "0.35",
            ]
        )

        self.assertAlmostEqual(args.valid_pixel_percent_threshold, 0.35)

    def test_build_argument_parser_accepts_tile_validity_prefilter_options(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--enable-tile-validity-prefilter",
                "--tile-validity-cache-dir",
                "work/tile_validity_cache",
                "--tile-validity-cell-width",
                "512",
                "--tile-validity-cell-height",
                "256",
            ]
        )

        self.assertTrue(args.enable_tile_validity_prefilter)
        self.assertEqual(args.tile_validity_cache_dir, "work/tile_validity_cache")
        self.assertEqual(args.tile_validity_cell_width, 512)
        self.assertEqual(args.tile_validity_cell_height, 256)

    def test_build_argument_parser_accepts_result_output_and_tile_detail_stdout_controls(self):
        parser = build_argument_parser(config_defaults={"omit_tile_details": True})

        default_args = parser.parse_args(["left.cub", "right.cub", "left.key", "right.key"])
        included_args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--include-tile-details",
                "--result-output",
                "work/full_result.json",
            ]
        )
        omitted_args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--omit-tile-details",
            ]
        )

        self.assertTrue(default_args.omit_tile_details)
        self.assertFalse(included_args.omit_tile_details)
        self.assertEqual(included_args.result_output, "work/full_result.json")
        self.assertTrue(omitted_args.omit_tile_details)

    def test_build_argument_parser_defaults_to_gpu_dynamic_batch_and_allows_disabling_it(self):
        parser = build_argument_parser()

        default_args = parser.parse_args(["left.cub", "right.cub", "left.key", "right.key"])
        disabled_args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--no-gpu-dynamic-batch",
            ]
        )

        self.assertTrue(default_args.gpu_dynamic_batch)
        self.assertFalse(disabled_args.gpu_dynamic_batch)
        self.assertEqual(default_args.gpu_batch_size, 4)

    def test_build_argument_parser_accepts_invalid_pixel_radius_and_low_resolution_options(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--invalid-pixel-radius",
                "2",
                "--matcher-method",
                "flann",
                "--enable-low-resolution-offset-estimation",
                "--low-resolution-level",
                "4",
                "--low-resolution-trim-fraction-each-side",
                "0.1",
                "--low-resolution-max-mean-reprojection-error-pixels",
                "2.5",
                "--low-resolution-min-retained-match-count",
                "5",
                "--low-resolution-max-mean-projected-offset-meters",
                "2000",
                "--left-low-resolution-dom",
                "left_low.cub",
                "--right-low-resolution-dom",
                "right_low.cub",
            ]
        )

        self.assertEqual(args.invalid_pixel_radius, 2)
        self.assertEqual(args.matcher_method, "flann")
        self.assertTrue(args.enable_low_resolution_offset_estimation)
        self.assertEqual(args.low_resolution_level, 4)
        self.assertAlmostEqual(args.low_resolution_trim_fraction_each_side, 0.1)
        self.assertAlmostEqual(args.low_resolution_max_mean_reprojection_error_pixels, 2.5)
        self.assertEqual(args.low_resolution_min_retained_match_count, 5)
        self.assertAlmostEqual(args.low_resolution_max_mean_projected_offset_meters, 2000.0)
        self.assertEqual(args.left_low_resolution_dom, "left_low.cub")
        self.assertEqual(args.right_low_resolution_dom, "right_low.cub")

    def test_build_argument_parser_accepts_visualization_preview_options(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--visualization-mode",
                "reduced",
                "--memory-profile",
                "low-memory",
                "--visualization-target-long-edge",
                "1024",
                "--max-preview-pixels",
                "1000000",
                "--preview-crop-margin-pixels",
                "128",
                "--preview-cache-dir",
                "work/preview_cache",
                "--preview-cache-source",
                "visualization-cache",
                "--preview-force-regenerate",
                "--preview-level",
                "3",
                "--low-resolution-matching-target-long-edge",
                "1024",
            ]
        )

        self.assertEqual(args.visualization_mode, "reduced")
        self.assertEqual(args.memory_profile, "low-memory")
        self.assertEqual(args.visualization_target_long_edge, 1024)
        self.assertEqual(args.max_preview_pixels, 1000000)
        self.assertEqual(args.preview_crop_margin_pixels, 128)
        self.assertEqual(args.preview_cache_dir, "work/preview_cache")
        self.assertEqual(args.preview_cache_source, "visualization_cache")
        self.assertTrue(args.preview_force_regenerate)
        self.assertEqual(args.preview_level, 3)
        self.assertEqual(args.low_resolution_matching_target_long_edge, 1024)

    def test_build_argument_parser_accepts_matching_cache_preview_source(self):
        parser = build_argument_parser()

        args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--preview-cache-source",
                "matching-cache",
            ]
        )

        self.assertEqual(args.preview_cache_source, "matching_cache")

    def test_build_argument_parser_rejects_invalid_low_resolution_match_count_and_offset_threshold(self):
        parser = build_argument_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--low-resolution-min-retained-match-count",
                    "0",
                ]
            )

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--low-resolution-max-mean-projected-offset-meters",
                    "-1",
                ]
            )

    def test_build_argument_parser_rejects_out_of_range_invalid_pixel_radius(self):
        parser = build_argument_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--invalid-pixel-radius",
                    "-1",
                ]
            )

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--invalid-pixel-radius",
                    "101",
                ]
            )

    def test_build_argument_parser_rejects_out_of_range_low_resolution_level(self):
        parser = build_argument_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--low-resolution-level",
                    "-1",
                ]
            )

    def test_build_argument_parser_rejects_out_of_range_low_resolution_trim_fraction_each_side(self):
        parser = build_argument_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--low-resolution-trim-fraction-each-side",
                    "-0.01",
                ]
            )

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--low-resolution-trim-fraction-each-side",
                    "0.5",
                ]
            )

    def test_load_image_match_defaults_from_config_accepts_low_resolution_trim_fraction(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "image_match_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "lowResolutionTrimFractionEachSide": 0.12,
                            "matcherMethod": "flann",
                            "lowResolutionMaxMeanReprojectionErrorPixels": 2.25,
                            "lowResolutionMinRetainedMatchCount": 6,
                            "lowResolutionMaxMeanProjectedOffsetMeters": 2000.0,
                        }
                    }
                ),
                encoding="utf-8",
            )

            defaults = image_match.load_image_match_defaults_from_config(config_path)

        self.assertAlmostEqual(defaults["low_resolution_trim_fraction_each_side"], 0.12)
        self.assertEqual(defaults["matcher_method"], "flann")
        self.assertAlmostEqual(defaults["low_resolution_max_mean_reprojection_error_pixels"], 2.25)
        self.assertEqual(defaults["low_resolution_min_retained_match_count"], 6)
        self.assertAlmostEqual(defaults["low_resolution_max_mean_projected_offset_meters"], 2000.0)

    def test_load_image_match_defaults_from_config_accepts_deep_matcher_config_path(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "image_match_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "deep_matcher_config_path": "examples/controlnet_construct/presets/lightglue_default.json",
                        }
                    }
                ),
                encoding="utf-8",
            )

            defaults = image_match.load_image_match_defaults_from_config(config_path)

        self.assertEqual(
            defaults["deep_match_config_path"],
            "examples/controlnet_construct/presets/lightglue_default.json",
        )

    def test_image_match_main_forwards_deep_match_config_path_to_key_file_runner(self):
        stdout = io.StringIO()

        with (
            mock.patch("controlnet_construct.image_match.match_dom_pair_to_key_files", return_value={"status": "matched"}) as match_mock,
            mock.patch.object(sys, "stdout", stdout),
        ):
            image_match.main(
                [
                    "--deep-match-config-path",
                    "examples/controlnet_construct/presets/lightglue_default.json",
                    "left_dom.cub",
                    "right_dom.cub",
                    "left.key",
                    "right.key",
                    "--no-write-match-visualization",
                ]
            )

        self.assertEqual(
            match_mock.call_args.kwargs["deep_match_config_path"],
            Path("examples/controlnet_construct/presets/lightglue_default.json"),
        )

    def test_match_dom_pair_validates_deep_match_config_path_before_opening_cubes(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "invalid_deep_match.json"
            config_path.write_text(json.dumps({}), encoding="utf-8")

            with mock.patch.object(image_match.ip, "Cube") as cube_mock:
                with self.assertRaisesRegex(ValueError, "feature_extractor"):
                    image_match.match_dom_pair(
                        "left_dom.cub",
                        "right_dom.cub",
                        deep_match_config_path=config_path,
                    )

        cube_mock.return_value.open.assert_not_called()

    def test_resolve_deep_match_runtime_config_reads_lightglue_default(self):
        runtime = deep_match_config_module.resolve_deep_match_runtime_config(
            PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "lightglue_default.json"
        )

        self.assertEqual(runtime.matcher_method, "lightglue")
        self.assertEqual(runtime.feature_extractor_method, "superpoint")
        self.assertTrue(runtime.prefer_gpu)
        self.assertEqual(runtime.device_dtype, "float32")
        self.assertEqual(runtime.fallback_on_error, "sift_flann")
        self.assertEqual(runtime.raw_config["matcher"]["method"], "lightglue")
        self.assertEqual(getattr(runtime, "feature_options", None), {"max_keypoints": 4096, "keypoint_threshold": 0.0005, "remove_borders": 4, "detect_keypoints": True})
        self.assertEqual(
            getattr(runtime, "matcher_options", None),
            {"weights": "superpoint_lightglue", "weights_path": None, "flash": True, "prune_threshold": 4},
        )
        self.assertEqual(getattr(runtime, "device_options", None), {"prefer_gpu": True, "dtype": "float32", "batch_inference": True})

    def test_resolve_deep_match_runtime_config_reads_loftr_pretrained_default(self):
        runtime = deep_match_config_module.resolve_deep_match_runtime_config(
            PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "loftr_default.json"
        )

        self.assertEqual(runtime.matcher_method, "loftr")
        self.assertEqual(getattr(runtime, "matcher_options", {}).get("pretrained"), "outdoor")

    def test_validate_deep_match_config_rejects_incompatible_matcher_extractor_pairs(self):
        for matcher_method, extractor_method, supported_method in (
            ("lightglue", "disk", "superpoint"),
            ("superglue", "aliked", "superpoint"),
            ("loftr", "superpoint", "loftr"),
        ):
            with self.subTest(matcher=matcher_method, extractor=extractor_method):
                with self.assertRaisesRegex(
                    ValueError,
                    rf"matcher\.method='{matcher_method}'.*feature_extractor\.method.*'{supported_method}'.*'{extractor_method}'",
                ):
                    deep_match_config_module.validate_deep_match_config(
                        {
                            "feature_extractor": {"method": extractor_method},
                            "matcher": {"method": matcher_method},
                        }
                    )

    def test_lightglue_matcher_uses_preset_feature_and_matcher_options(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")
        runtime = deep_match_config_module.resolve_deep_match_runtime_config(
            PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "lightglue_default.json"
        )
        lightglue_constructor = mock.Mock(return_value=_EvalToDeviceModule())
        torch_module = _stub_module("torch")
        lightglue_module = _stub_module("lightglue", LightGlue=lightglue_constructor)

        with mock.patch.dict(sys.modules, {"torch": torch_module, "lightglue": lightglue_module}, clear=False):
            matcher = deep_matchers_module.build_deep_matcher(
                runtime.matcher_method,
                device="cpu",
                feature_extractor_method=runtime.feature_extractor_method,
                matcher_options=getattr(runtime, "matcher_options", {}),
                feature_options=getattr(runtime, "feature_options", {}),
                device_options=getattr(runtime, "device_options", {}),
            )
            matcher._load_matcher()

        lightglue_constructor.assert_called_once_with(
            features="superpoint",
            weights="superpoint_lightglue",
            flash=True,
            prune_threshold=4,
        )

    def test_official_lightglue_matcher_uses_official_options_and_frontend_name(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")
        lightglue_constructor = mock.Mock(return_value=_EvalToDeviceModule())
        torch_module = _stub_module("torch")
        lightglue_module = _stub_module("lightglue", LightGlue=lightglue_constructor)

        with mock.patch.dict(sys.modules, {"torch": torch_module, "lightglue": lightglue_module}, clear=False):
            matcher = deep_matchers_module.build_deep_matcher(
                "lightglue",
                device="cpu",
                feature_extractor_method="lightglue_sift",
                matcher_options={
                    "backend": "official",
                    "weights_path": None,
                    "filter_threshold": 0.05,
                    "depth_confidence": -1,
                    "width_confidence": -1,
                    "flash": True,
                    "mp": False,
                },
                feature_options={"max_features": 128},
                device_options={"dtype": "float32"},
            )
            matcher._load_matcher()

        lightglue_constructor.assert_called_once_with(
            features="sift",
            filter_threshold=0.05,
            depth_confidence=-1,
            width_confidence=-1,
            flash=True,
            mp=False,
        )

    def test_official_lightglue_matcher_preserves_frontend_metadata_fields(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")
        captured_inputs = []

        class CapturingLightGlue(_EvalToDeviceModule):
            def __call__(self, inputs):
                captured_inputs.append(inputs)
                return {
                    "matches": _FakeTorchTensor(np.array([[[0, 0]]], dtype=np.int64)),
                    "scores": _FakeTorchTensor(np.array([[0.9]], dtype=np.float32)),
                }

        lightglue_module = _stub_module("lightglue", LightGlue=mock.Mock(return_value=CapturingLightGlue()))
        features_left = {
            "keypoints": np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32),
            "descriptors": np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32),
            "scales": np.array([1.5, 2.5], dtype=np.float32),
            "oris": np.array([0.25, 0.75], dtype=np.float32),
            "image_size": np.array([640.0, 480.0], dtype=np.float32),
        }
        features_right = {
            "keypoints": np.array([[5.0, 6.0], [7.0, 8.0]], dtype=np.float32),
            "descriptors": np.array([[0.5, 0.6], [0.7, 0.8]], dtype=np.float32),
            "scales": np.array([3.5, 4.5], dtype=np.float32),
            "oris": np.array([1.25, 1.75], dtype=np.float32),
            "image_size": np.array([640.0, 480.0], dtype=np.float32),
        }

        with mock.patch.dict(sys.modules, {"torch": _fake_torch_module(), "lightglue": lightglue_module}, clear=False):
            matcher = deep_matchers_module.build_deep_matcher(
                "lightglue",
                device="cpu",
                feature_extractor_method="lightglue_sift",
                matcher_options={"backend": "official", "filter_threshold": 0.05},
                device_options={"dtype": "float32"},
            )
            matcher.match(features_left=features_left, features_right=features_right, device="cpu")

        self.assertEqual(len(captured_inputs), 1)
        self.assertIn("scales", captured_inputs[0]["image0"])
        self.assertIn("oris", captured_inputs[0]["image0"])
        self.assertIn("image_size", captured_inputs[0]["image0"])
        np.testing.assert_allclose(captured_inputs[0]["image0"]["scales"].array, np.array([[1.5, 2.5]], dtype=np.float32))
        np.testing.assert_allclose(captured_inputs[0]["image0"]["oris"].array, np.array([[0.25, 0.75]], dtype=np.float32))
        np.testing.assert_allclose(captured_inputs[0]["image0"]["image_size"].array, np.array([[640.0, 480.0]], dtype=np.float32))
        np.testing.assert_allclose(captured_inputs[0]["image1"]["scales"].array, np.array([[3.5, 4.5]], dtype=np.float32))
        np.testing.assert_allclose(captured_inputs[0]["image1"]["oris"].array, np.array([[1.25, 1.75]], dtype=np.float32))

    def test_superglue_matcher_uses_preset_matcher_options(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")
        runtime = deep_match_config_module.resolve_deep_match_runtime_config(
            PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "superglue_default.json"
        )
        matching_constructor = mock.Mock(return_value=_EvalToDeviceModule())
        torch_module = _stub_module("torch")
        matching_module = _stub_module("models.matching", Matching=matching_constructor)
        models_module = _stub_module("models", matching=matching_module)

        with mock.patch.dict(
            sys.modules,
            {"torch": torch_module, "models": models_module, "models.matching": matching_module},
            clear=False,
        ):
            matcher = deep_matchers_module.build_deep_matcher(
                runtime.matcher_method,
                device="cpu",
                feature_extractor_method=runtime.feature_extractor_method,
                matcher_options=getattr(runtime, "matcher_options", {}),
                feature_options=getattr(runtime, "feature_options", {}),
                device_options=getattr(runtime, "device_options", {}),
            )
            matcher._load_model()

        config = matching_constructor.call_args.args[0]
        self.assertEqual(config["superglue"]["weights"], "outdoor")
        self.assertEqual(config["superglue"]["sinkhorn_iterations"], 20)
        self.assertAlmostEqual(config["superglue"]["match_threshold"], 0.2)

    def test_loftr_matcher_uses_preset_pretrained_option(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")
        runtime = deep_match_config_module.resolve_deep_match_runtime_config(
            PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "loftr_default.json"
        )
        loftr_constructor = mock.Mock(return_value=_EvalToDeviceModule())
        torch_module = _stub_module("torch")
        kornia_feature_module = _stub_module("kornia.feature", LoFTR=loftr_constructor)
        kornia_module = _stub_module("kornia", feature=kornia_feature_module)

        with mock.patch.dict(
            sys.modules,
            {"torch": torch_module, "kornia": kornia_module, "kornia.feature": kornia_feature_module},
            clear=False,
        ):
            matcher = deep_matchers_module.build_deep_matcher(
                runtime.matcher_method,
                device="cpu",
                feature_extractor_method=runtime.feature_extractor_method,
                matcher_options=getattr(runtime, "matcher_options", {}),
                feature_options=getattr(runtime, "feature_options", {}),
                device_options=getattr(runtime, "device_options", {}),
            )
            matcher._load_matcher()

        loftr_constructor.assert_called_once_with(pretrained="outdoor")

    def test_external_loftr_matcher_loads_external_repo_checkpoint_and_config(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "LoFTR"
            (root / "src" / "loftr").mkdir(parents=True)
            (root / "src" / "loftr" / "__init__.py").write_text("", encoding="utf-8")
            checkpoint = root / "weights" / "outdoor.ckpt"
            checkpoint.parent.mkdir()
            checkpoint.write_bytes(b"stub")

            loaded_state = {"state_dict": {"matcher.weight": object()}}
            matcher_instance = _EvalToDeviceModule()
            matcher_instance.load_state_dict = mock.Mock()
            matcher_constructor = mock.Mock(return_value=matcher_instance)
            loftr_module = _stub_module(
                "src.loftr",
                LoFTR=matcher_constructor,
                default_cfg={"coarse": {"temp_bug_fix": False, "d_model": 256}, "match_coarse": {}, "resolution": (8, 2)},
            )
            torch_module = _stub_module("torch", float32="torch.float32", load=mock.Mock(return_value=loaded_state))

            with mock.patch.dict(sys.modules, {"torch": torch_module, "src.loftr": loftr_module}, clear=False):
                matcher = deep_matchers_module.build_deep_matcher(
                    "loftr",
                    device="cpu",
                    feature_extractor_method="loftr",
                    matcher_options={
                        "backend": "external",
                        "loftr_root": str(root),
                        "checkpoint": str(checkpoint),
                        "model_type": "outdoor",
                        "temp_bug_fix": "true",
                        "coarse_threshold": 0.3,
                    },
                    device_options={"dtype": "float32"},
                )
                matcher._load_matcher()

        matcher_constructor.assert_called_once()
        config = matcher_constructor.call_args.kwargs["config"]
        self.assertIs(config["coarse"]["temp_bug_fix"], True)
        self.assertAlmostEqual(config["match_coarse"]["thr"], 0.3)
        torch_module.load.assert_called_once_with(checkpoint, map_location="cpu", weights_only=True)
        matcher_instance.load_state_dict.assert_called_once_with(loaded_state["state_dict"], strict=True)

    def test_external_loftr_matcher_filters_top_k_and_scales_points(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")

        class _InferenceMode:
            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc, traceback):
                return False

        class _ExternalMatcher:
            config = {"resolution": (8, 2), "coarse": {"d_model": 256, "temp_bug_fix": False}}
            pos_encoding = SimpleNamespace(pe=np.zeros((1, 1, 8, 8), dtype=np.float32))

            def __call__(self, batch):
                batch["mkpts0_f"] = SimpleNamespace(detach=lambda: SimpleNamespace(cpu=lambda: SimpleNamespace(numpy=lambda: np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32))))
                batch["mkpts1_f"] = SimpleNamespace(detach=lambda: SimpleNamespace(cpu=lambda: SimpleNamespace(numpy=lambda: np.array([[2.0, 3.0], [4.0, 5.0], [6.0, 7.0]], dtype=np.float32))))
                batch["mconf"] = SimpleNamespace(detach=lambda: SimpleNamespace(cpu=lambda: SimpleNamespace(numpy=lambda: np.array([0.2, 0.9, 0.5], dtype=np.float32))))

        matcher = deep_matchers_module.LoFTRMatcher(
            device="cpu",
            matcher_options={"backend": "external", "min_confidence": 0.3, "top_k": 1},
        )
        matcher._matcher = _ExternalMatcher()

        torch_module = _stub_module("torch", inference_mode=lambda: _InferenceMode(), no_grad=lambda: _InferenceMode())
        with mock.patch.object(matcher, "_load_matcher", return_value=(torch_module, matcher._matcher)):
            left_points, right_points, scores = matcher.match(
                left_image=object(),
                right_image=object(),
                left_meta={"scale": (2.0, 3.0)},
                right_meta={"scale": (4.0, 5.0)},
            )

        np.testing.assert_allclose(left_points, np.array([[6.0, 12.0]], dtype=np.float32))
        np.testing.assert_allclose(right_points, np.array([[16.0, 25.0]], dtype=np.float32))
        np.testing.assert_allclose(scores, np.array([0.9], dtype=np.float32))

    def test_external_loftr_matcher_downsamples_masks_to_coarse_resolution(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")
        captured_batches = []

        class _InferenceMode:
            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc, traceback):
                return False

        class _TensorStub:
            def __init__(self, array):
                self.array = np.asarray(array)
                self.shape = self.array.shape

            def to(self, *args, **kwargs):
                return self

            def detach(self):
                return self

            def cpu(self):
                return self

            def numpy(self):
                return self.array

        class _ExternalMatcher:
            config = {"resolution": (8, 2), "coarse": {"d_model": 256, "temp_bug_fix": False}}
            pos_encoding = SimpleNamespace(pe=np.zeros((1, 1, 2, 3), dtype=np.float32))

            def __call__(self, batch):
                captured_batches.append(dict(batch))
                batch["mkpts0_f"] = _TensorStub(np.zeros((0, 2), dtype=np.float32))
                batch["mkpts1_f"] = _TensorStub(np.zeros((0, 2), dtype=np.float32))
                batch["mconf"] = _TensorStub(np.zeros((0,), dtype=np.float32))

        matcher = deep_matchers_module.LoFTRMatcher(
            device="cpu",
            matcher_options={"backend": "external"},
        )
        matcher._matcher = _ExternalMatcher()

        torch_module = _stub_module("torch", inference_mode=lambda: _InferenceMode(), no_grad=lambda: _InferenceMode())
        with mock.patch.object(matcher, "_load_matcher", return_value=(torch_module, matcher._matcher)):
            matcher.match(
                left_image=_TensorStub(np.zeros((1, 1, 16, 24), dtype=np.float32)),
                right_image=_TensorStub(np.zeros((1, 1, 16, 24), dtype=np.float32)),
                left_mask=_TensorStub(np.ones((16, 24), dtype=bool)),
                right_mask=_TensorStub(np.ones((16, 24), dtype=bool)),
            )

        self.assertEqual(captured_batches[0]["mask0"].shape, (1, 2, 3))
        self.assertEqual(captured_batches[0]["mask1"].shape, (1, 2, 3))

    def test_external_loftr_matcher_applies_geometric_filter_before_top_k(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")

        class _InferenceMode:
            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc, traceback):
                return False

        class _TensorStub:
            def __init__(self, array):
                self.array = np.asarray(array)
                self.shape = self.array.shape

            def detach(self):
                return self

            def cpu(self):
                return self

            def numpy(self):
                return self.array

        class _ExternalMatcher:
            config = {"resolution": (8, 2), "coarse": {"d_model": 256, "temp_bug_fix": False}}
            pos_encoding = SimpleNamespace(pe=np.zeros((1, 1, 8, 8), dtype=np.float32))

            def __call__(self, batch):
                batch["mkpts0_f"] = _TensorStub(np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=np.float32))
                batch["mkpts1_f"] = _TensorStub(np.array([[0.0, 0.0], [2.0, 0.0], [0.0, 2.0], [2.0, 2.0]], dtype=np.float32))
                batch["mconf"] = _TensorStub(np.array([0.9, 0.8, 0.7, 0.6], dtype=np.float32))

        matcher = deep_matchers_module.LoFTRMatcher(
            device="cpu",
            matcher_options={"backend": "external", "geometric_filter": "homography", "top_k": 1},
        )
        matcher._matcher = _ExternalMatcher()
        torch_module = _stub_module("torch", inference_mode=lambda: _InferenceMode(), no_grad=lambda: _InferenceMode())
        cv2_module = _stub_module(
            "cv2",
            RANSAC=8,
            findHomography=mock.Mock(
                return_value=(np.eye(3), np.array([[0], [1], [1], [1]], dtype=np.uint8))
            ),
        )

        with mock.patch.dict(sys.modules, {"cv2": cv2_module}, clear=False), mock.patch.object(
            matcher,
            "_load_matcher",
            return_value=(torch_module, matcher._matcher),
        ):
            left_points, right_points, scores = matcher.match(left_image=object(), right_image=object())

        cv2_module.findHomography.assert_called_once()
        np.testing.assert_allclose(left_points, np.array([[1.0, 0.0]], dtype=np.float32))
        np.testing.assert_allclose(right_points, np.array([[2.0, 0.0]], dtype=np.float32))
        np.testing.assert_allclose(scores, np.array([0.8], dtype=np.float32))

    def test_external_loftr_import_reloads_stale_module_from_different_root(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")
        with tempfile.TemporaryDirectory() as tmp_dir:
            stale_root = Path(tmp_dir) / "stale" / "LoFTR"
            root = Path(tmp_dir) / "fresh" / "LoFTR"
            (stale_root / "src" / "loftr").mkdir(parents=True)
            (root / "src" / "loftr").mkdir(parents=True)
            (root / "src" / "loftr" / "__init__.py").write_text("", encoding="utf-8")
            checkpoint = root / "weights" / "outdoor.ckpt"
            checkpoint.parent.mkdir()
            checkpoint.write_bytes(b"stub")

            stale_module = _stub_module("src.loftr")
            stale_module.__file__ = str(stale_root / "src" / "loftr" / "__init__.py")
            fresh_matcher = _EvalToDeviceModule()
            fresh_matcher.load_state_dict = mock.Mock()
            fresh_module = _stub_module(
                "src.loftr",
                LoFTR=mock.Mock(return_value=fresh_matcher),
                default_cfg={"coarse": {"temp_bug_fix": False, "d_model": 256}, "match_coarse": {}, "resolution": (8, 2)},
            )
            torch_module = _stub_module("torch", float32="torch.float32", load=mock.Mock(return_value={}))

            with mock.patch.dict(sys.modules, {"torch": torch_module, "src.loftr": stale_module}, clear=False), mock.patch(
                "importlib.import_module",
                return_value=fresh_module,
            ) as import_mock:
                matcher = deep_matchers_module.LoFTRMatcher(
                    device="cpu",
                    matcher_options={"backend": "external", "loftr_root": str(root), "checkpoint": str(checkpoint)},
                )
                matcher._load_matcher()
                self.assertIsNot(sys.modules.get("src.loftr"), stale_module)

        import_mock.assert_called_once_with("src.loftr")
        fresh_module.LoFTR.assert_called_once()

    def test_external_loftr_import_error_includes_underlying_exception(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "LoFTR"
            (root / "src" / "loftr").mkdir(parents=True)
            (root / "src" / "loftr" / "__init__.py").write_text("", encoding="utf-8")
            checkpoint = root / "weights" / "outdoor.ckpt"
            checkpoint.parent.mkdir()
            checkpoint.write_bytes(b"stub")
            torch_module = _stub_module("torch", float32="torch.float32")

            with mock.patch.dict(sys.modules, {"torch": torch_module}, clear=False), mock.patch(
                "importlib.import_module",
                side_effect=ImportError("No module named 'einops'"),
            ):
                matcher = deep_matchers_module.LoFTRMatcher(
                    device="cpu",
                    matcher_options={"backend": "external", "loftr_root": str(root), "checkpoint": str(checkpoint)},
                )
                with self.assertRaisesRegex(deep_matchers_module.DeepMatcherError, "einops"):
                    matcher._load_matcher()

    def test_external_loftr_position_encoding_resize_failure_is_reported(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")

        class _TensorStub:
            shape = (1, 1, 32, 32)

        matcher = deep_matchers_module.LoFTRMatcher(
            device="cpu",
            matcher_options={"backend": "external"},
        )
        external_matcher = SimpleNamespace(
            config={"resolution": (8, 2), "coarse": {"d_model": 256, "temp_bug_fix": False}},
            pos_encoding=SimpleNamespace(pe=np.zeros((1, 1, 1, 1), dtype=np.float32)),
        )
        position_module = _stub_module(
            "src.loftr.utils.position_encoding",
            PositionEncodingSine=mock.Mock(side_effect=RuntimeError("position encoding failed")),
        )

        with mock.patch("importlib.import_module", return_value=position_module):
            with self.assertRaisesRegex(deep_matchers_module.DeepMatcherError, "position encoding failed"):
                matcher._ensure_external_position_encoding(
                    torch=object(),
                    matcher=external_matcher,
                    batch={"image0": _TensorStub()},
                )

    def test_external_loftr_position_encoding_resize_preserves_dtype(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")

        class _TensorStub:
            shape = (1, 1, 32, 32)

        class _PositionEncodingStub:
            def __init__(self):
                self.to_calls = []

            def to(self, **kwargs):
                self.to_calls.append(kwargs)
                return self

        position_encoding = _PositionEncodingStub()
        matcher = deep_matchers_module.LoFTRMatcher(
            device="cpu",
            matcher_options={"backend": "external"},
            device_options={"dtype": "float16"},
        )
        external_matcher = SimpleNamespace(
            config={"resolution": (8, 2), "coarse": {"d_model": 256, "temp_bug_fix": False}},
            pos_encoding=SimpleNamespace(pe=np.zeros((1, 1, 1, 1), dtype=np.float32)),
        )
        position_module = _stub_module(
            "src.loftr.utils.position_encoding",
            PositionEncodingSine=mock.Mock(return_value=position_encoding),
        )
        torch_module = _stub_module("torch", float16="torch.float16")

        with mock.patch("importlib.import_module", return_value=position_module):
            matcher._ensure_external_position_encoding(
                torch=torch_module,
                matcher=external_matcher,
                batch={"image0": _TensorStub()},
            )

        self.assertEqual(position_encoding.to_calls, [{"device": "cpu", "dtype": "torch.float16"}])
        self.assertIs(external_matcher.pos_encoding, position_encoding)

    def test_external_loftr_position_encoding_resize_uses_larger_right_image(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")

        class _LeftTensorStub:
            shape = (1, 1, 16, 16)

        class _RightTensorStub:
            shape = (1, 1, 40, 56)

        position_encoding = SimpleNamespace(to=lambda **_kwargs: position_encoding)
        matcher = deep_matchers_module.LoFTRMatcher(
            device="cpu",
            matcher_options={"backend": "external"},
        )
        external_matcher = SimpleNamespace(
            config={"resolution": (8, 2), "coarse": {"d_model": 256, "temp_bug_fix": False}},
            pos_encoding=SimpleNamespace(pe=np.zeros((1, 1, 2, 2), dtype=np.float32)),
        )
        position_module = _stub_module(
            "src.loftr.utils.position_encoding",
            PositionEncodingSine=mock.Mock(return_value=position_encoding),
        )
        torch_module = _stub_module("torch")

        with mock.patch("importlib.import_module", return_value=position_module):
            matcher._ensure_external_position_encoding(
                torch=torch_module,
                matcher=external_matcher,
                batch={"image0": _LeftTensorStub(), "image1": _RightTensorStub()},
            )

        position_module.PositionEncodingSine.assert_called_once_with(
            256,
            max_shape=(5, 7),
            temp_bug_fix=False,
        )

    def test_build_deep_matcher_defaults_loftr_extractor_for_loftr(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")

        matcher = deep_matchers_module.build_deep_matcher("loftr", device="cpu")

        self.assertEqual(matcher.feature_extractor_method, "loftr")

    def test_loftr_matcher_options_reject_non_null_checkpoint_path(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")
        matcher = deep_matchers_module.build_deep_matcher(
            "loftr",
            device="cpu",
            feature_extractor_method="loftr",
            matcher_options={"checkpoint_path": "custom_loftr.ckpt"},
        )

        with self.assertRaisesRegex(deep_matchers_module.DeepMatcherError, "checkpoint_path"):
            matcher._load_matcher()

    def test_loftr_matcher_options_validate_before_dependency_import(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")
        matcher = deep_matchers_module.build_deep_matcher(
            "loftr",
            device="cpu",
            feature_extractor_method="loftr",
            matcher_options={"checkpoint_path": "custom_loftr.ckpt"},
        )

        with mock.patch.dict(sys.modules, {"torch": None}, clear=False):
            with self.assertRaisesRegex(deep_matchers_module.DeepMatcherError, "checkpoint_path"):
                matcher._load_matcher()

    def test_deep_matchers_apply_dtype_and_surface_ignored_device_options(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")

        for method, feature_extractor_method, matcher_options, modules, loader_name in (
            (
                "lightglue",
                "superpoint",
                {"weights": "superpoint_lightglue"},
                {"lightglue": _stub_module("lightglue", LightGlue=mock.Mock(return_value=_EvalToDeviceModule()))},
                "_load_matcher",
            ),
            (
                "superglue",
                "superpoint",
                {"weights": "outdoor"},
                {
                    "models.matching": _stub_module("models.matching", Matching=mock.Mock(return_value=_EvalToDeviceModule())),
                    "models": None,
                },
                "_load_model",
            ),
            (
                "loftr",
                "loftr",
                {"pretrained": "outdoor"},
                {
                    "kornia.feature": _stub_module("kornia.feature", LoFTR=mock.Mock(return_value=_EvalToDeviceModule())),
                    "kornia": None,
                },
                "_load_matcher",
            ),
        ):
            with self.subTest(method=method):
                torch_module = _stub_module("torch", float16="torch.float16")
                patched_modules = {"torch": torch_module}
                patched_modules.update(modules)
                if "models.matching" in patched_modules:
                    patched_modules["models"] = _stub_module("models", matching=patched_modules["models.matching"])
                if "kornia.feature" in patched_modules:
                    patched_modules["kornia"] = _stub_module("kornia", feature=patched_modules["kornia.feature"])

                with mock.patch.dict(sys.modules, patched_modules, clear=False):
                    matcher = deep_matchers_module.build_deep_matcher(
                        method,
                        device="cpu",
                        feature_extractor_method=feature_extractor_method,
                        matcher_options=matcher_options,
                        device_options={"dtype": "float16", "batch_inference": True},
                    )
                    getattr(matcher, loader_name)()

                backend = getattr(matcher, "_matcher", None) or getattr(matcher, "_model", None)
                self.assertEqual(backend.device, "cpu")
                self.assertEqual(backend.dtype, "torch.float16")
                self.assertIn("device.batch_inference", matcher.ignored_parameters)

    def test_match_dom_pair_rejects_deep_config_matcher_conflict_before_opening_cubes(self):
        config_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "lightglue_default.json"

        with mock.patch.object(image_match.ip, "Cube") as cube_mock:
            with self.assertRaisesRegex(
                ValueError,
                "matcher_method 'loftr' conflicts with deep_match_config matcher.method 'lightglue'",
            ):
                image_match.match_dom_pair(
                    "left_dom.cub",
                    "right_dom.cub",
                    matcher_method="loftr",
                    deep_match_config_path=config_path,
                )

        cube_mock.return_value.open.assert_not_called()

    def test_build_tile_match_tasks_carries_deep_match_runtime_config(self):
        runtime = deep_match_config_module.resolve_deep_match_runtime_config(
            PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "lightglue_default.json"
        )
        windows = [
            image_match.tile_matching_module.PairedTileWindow(
                local_window=TileWindow(0, 0, 16, 16),
                left_window=TileWindow(0, 0, 16, 16),
                right_window=TileWindow(1, 1, 16, 16),
            )
        ]

        tasks = image_match.tile_matching_module._build_tile_match_tasks(
            windows,
            left_dom_path="left.cub",
            right_dom_path="right.cub",
            image_space="dom",
            band=1,
            minimum_value=None,
            maximum_value=None,
            lower_percent=0.5,
            upper_percent=99.5,
            invalid_values=(),
            special_pixel_abs_threshold=1.0e300,
            min_valid_pixels=1,
            valid_pixel_percent_threshold=0.0,
            invalid_pixel_radius=0,
            ratio_test=0.75,
            matcher_method="lightglue",
            max_features=None,
            sift_octave_layers=3,
            sift_contrast_threshold=0.04,
            sift_edge_threshold=10.0,
            sift_sigma=1.6,
            deep_match_runtime_config=runtime,
        )

        self.assertIs(tasks[0].deep_match_runtime_config, runtime)

    def test_serial_tile_match_tasks_accepts_deep_match_runtime_config(self):
        signature = inspect.signature(image_match.tile_matching_module._run_serial_tile_match_tasks)

        self.assertIn("deep_match_runtime_config", signature.parameters)

    def test_load_image_match_defaults_from_config_reads_tile_validity_fields(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "enableTileValidityPrefilter": True,
                            "tileValidityCacheDir": "work/tile_validity_cache",
                            "tileValidityCellWidth": 512,
                            "tileValidityCellHeight": 256,
                        }
                    }
                ),
                encoding="utf-8",
            )
            defaults = image_match.load_image_match_defaults_from_config(config_path)

        self.assertTrue(defaults["enable_tile_validity_prefilter"])
        self.assertEqual(defaults["tile_validity_cache_dir"], "work/tile_validity_cache")
        self.assertEqual(defaults["tile_validity_cell_width"], 512)
        self.assertEqual(defaults["tile_validity_cell_height"], 256)

    def test_load_image_match_defaults_from_config_reads_omit_tile_details_field(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "omitTileDetails": True,
                        }
                    }
                ),
                encoding="utf-8",
            )
            defaults = image_match.load_image_match_defaults_from_config(config_path)

        self.assertTrue(defaults["omit_tile_details"])

    def test_load_image_match_defaults_from_config_reads_visualization_fields(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "visualizationMode": "reduced",
                            "memoryProfile": "low-memory",
                            "visualizationTargetLongEdge": 1024,
                            "maxPreviewPixels": 1000000,
                            "previewCropMarginPixels": 128,
                            "previewCacheDir": "work/preview_cache",
                            "previewCacheSource": "visualization-cache",
                            "previewForceRegenerate": True,
                            "previewLevel": 3,
                            "lowResolutionMatchingTargetLongEdge": 1024,
                        }
                    }
                ),
                encoding="utf-8",
            )
            defaults = image_match.load_image_match_defaults_from_config(config_path)

        self.assertEqual(defaults["visualization_mode"], "reduced")
        self.assertEqual(defaults["memory_profile"], "low-memory")
        self.assertEqual(defaults["visualization_target_long_edge"], 1024)
        self.assertEqual(defaults["max_preview_pixels"], 1000000)
        self.assertEqual(defaults["preview_crop_margin_pixels"], 128)
        self.assertEqual(defaults["preview_cache_dir"], "work/preview_cache")
        self.assertEqual(defaults["preview_cache_source"], "visualization_cache")
        self.assertTrue(defaults["preview_force_regenerate"])
        self.assertEqual(defaults["preview_level"], 3)
        self.assertEqual(defaults["low_resolution_matching_target_long_edge"], 1024)

    def test_load_image_match_defaults_from_config_reads_adaptive_routing_flag(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "enableAdaptiveRouting": True,
                        }
                    }
                ),
                encoding="utf-8",
            )
            defaults = image_match.load_image_match_defaults_from_config(config_path)

        self.assertTrue(defaults["enable_adaptive_routing"])

    def test_load_image_match_defaults_from_config_reads_adaptive_routing_profile(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "adaptiveRoutingProfile": "relaxed",
                        }
                    }
                ),
                encoding="utf-8",
            )
            defaults = image_match.load_image_match_defaults_from_config(config_path)

        self.assertEqual(defaults["adaptive_routing_profile"], "relaxed")

    def test_create_descriptor_matcher_supports_bf_and_flann(self):
        fake_bf_matcher = object()
        fake_flann_matcher = object()

        with mock.patch.object(tile_matching_module.cv2, "BFMatcher", return_value=fake_bf_matcher) as bf_mock, mock.patch.object(
            tile_matching_module.cv2,
            "FlannBasedMatcher",
            return_value=fake_flann_matcher,
        ) as flann_mock:
            self.assertIs(tile_matching_module._create_descriptor_matcher("bf"), fake_bf_matcher)
            self.assertIs(tile_matching_module._create_descriptor_matcher("flann"), fake_flann_matcher)

        bf_mock.assert_called_once_with(tile_matching_module.cv2.NORM_L2, crossCheck=False)
        flann_mock.assert_called_once_with(
            {"algorithm": 1, "trees": tile_matching_module.DEFAULT_FLANN_TREES},
            {"checks": tile_matching_module.DEFAULT_FLANN_CHECKS},
        )

    def test_create_descriptor_matcher_rejects_deep_methods(self):
        for matcher_method in ("superglue", "lightglue", "loftr"):
            with self.assertRaisesRegex(ValueError, "descriptor matcher path"):
                tile_matching_module._create_descriptor_matcher(matcher_method)


    def test_normalize_matcher_method_accepts_deep_methods(self):
        self.assertEqual(tile_matching_module._normalize_matcher_method("superpoint"), "superpoint")
        self.assertEqual(tile_matching_module._normalize_matcher_method("superglue"), "superglue")
        self.assertEqual(tile_matching_module._normalize_matcher_method("  LIGHTGLUE  "), "lightglue")
        self.assertEqual(tile_matching_module._normalize_matcher_method("LOFTR"), "loftr")

    def test_match_ori_pair_routes_through_match_pair_generic_with_ori_space(self):
        expected = ("left-key", "right-key", {"status": "matched"})

        with mock.patch.object(image_match, "_match_pair_generic", return_value=expected) as match_pair_generic_mock:
            result = image_match.match_ori_pair(
                "left.cub",
                "right.cub",
                matcher_method="bf",
                max_features=64,
            )

        self.assertEqual(result, expected)
        match_pair_generic_mock.assert_called_once_with(
            "left.cub",
            "right.cub",
            image_space="ori",
            matcher_method="bf",
            max_features=64,
        )

    def test_match_ori_pair_deep_dependency_missing_fails_fast(self):
        deep_frontends_module = importlib.import_module("controlnet_construct.deep_frontends")

        with mock.patch.object(
            deep_frontends_module.SuperPointFrontend,
            "extract",
            side_effect=deep_frontends_module.DeepDependencyError("superpoint", "missing optional dependency 'torch'."),
        ), mock.patch.object(
            image_match,
            "match_dom_pair",
            side_effect=AssertionError("match_dom_pair should not run when deep dependencies are unavailable"),
        ):
            with self.assertRaisesRegex(RuntimeError, "superpoint|dependency|torch"):
                image_match.match_ori_pair(
                    "left.cub",
                    "right.cub",
                    matcher_method="superpoint",
                )

    def test_match_ori_pair_to_key_files_writes_ori_keys(self):
        with temporary_directory() as temp_dir:
            left_key = temp_dir / "left_ori.key"
            right_key = temp_dir / "right_ori.key"
            expected_left_key_file = KeypointFile(32, 32, (Keypoint(1.5, 2.5), Keypoint(3.5, 4.5)))
            expected_right_key_file = KeypointFile(32, 32, (Keypoint(5.5, 6.5), Keypoint(7.5, 8.5)))

            with mock.patch.object(
                image_match,
                "match_ori_pair",
                return_value=(
                    expected_left_key_file,
                    expected_right_key_file,
                    {
                        "status": "matched_no_points",
                        "matcher": {"matcher_method_requested": "sift"},
                    },
                ),
            ):
                result = image_match.match_ori_pair_to_key_files(
                    "left.cub",
                    "right.cub",
                    left_key,
                    right_key,
                )

            self.assertEqual(result["left_output_key"], str(left_key))
            self.assertEqual(result["right_output_key"], str(right_key))
            self.assertTrue(left_key.is_file())
            self.assertTrue(right_key.is_file())
            self.assertEqual(read_key_file(left_key), expected_left_key_file)
            self.assertEqual(read_key_file(right_key), expected_right_key_file)

    def test_build_image_backend_accepts_ori_space(self):
        backend = tile_matching.build_image_backend("ori")
        self.assertEqual(backend.space, "ori")

    def test_build_image_backend_accepts_dom_space(self):
        backend = tile_matching.build_image_backend("dom")
        self.assertEqual(backend.space, "dom")

    def test_build_image_backend_rejects_invalid_image_space(self):
        with self.assertRaisesRegex(ValueError, "Unsupported image_space"):
            tile_matching.build_image_backend("map")

    def test_normalize_matcher_method_rejects_unknown_method(self):
        with self.assertRaisesRegex(ValueError, "Unsupported matcher_method"):
            tile_matching_module._normalize_matcher_method("unknown-matcher")

    def test_controlnet_deep_adapter_reexports_image_match_adapter_api(self):
        controlnet_adapter = importlib.import_module("controlnet_construct.deep_adapter")
        image_match_adapter = importlib.import_module("image_match.deep_adapter")
        image_match_frontends = importlib.import_module("image_match.deep_frontends")
        image_match_matchers = importlib.import_module("image_match.deep_matchers")

        expected_exports = {
            "DeepMatcherAdapter": image_match_adapter.DeepMatcherAdapter,
            "DeepDependencyError": image_match_frontends.DeepDependencyError,
            "DeepFrontendError": image_match_frontends.DeepFrontendError,
            "LoFTRFrontend": image_match_frontends.LoFTRFrontend,
            "SuperPointFrontend": image_match_frontends.SuperPointFrontend,
            "normalize_deep_method": image_match_frontends.normalize_deep_method,
            "resolve_torch_device": image_match_frontends.resolve_torch_device,
            "DeepMatchResult": image_match_matchers.DeepMatchResult,
            "DeepMatcherError": image_match_matchers.DeepMatcherError,
            "_default_feature_extractor_for_matcher": image_match_matchers._default_feature_extractor_for_matcher,
            "build_deep_matcher": image_match_matchers.build_deep_matcher,
            "_filter_feature_dict_by_invalid_mask": image_match_adapter._filter_feature_dict_by_invalid_mask,
            "_runtime_feature_extractor_method": image_match_adapter._runtime_feature_extractor_method,
            "_valid_mask_keep": image_match_adapter._valid_mask_keep,
            "_validate_runtime_matcher_compatibility": image_match_adapter._validate_runtime_matcher_compatibility,
        }
        for name, expected in expected_exports.items():
            with self.subTest(name=name):
                self.assertIs(getattr(controlnet_adapter, name), expected)
                self.assertIn(name, controlnet_adapter.__all__)

    def test_controlnet_deep_frontends_reexports_image_match_frontend_api(self):
        controlnet_frontends = importlib.import_module("controlnet_construct.deep_frontends")
        image_match_frontends = importlib.import_module("image_match.deep_frontends")

        for name in (
            "DeepDependencyError",
            "DeepFrontendError",
            "LoFTRFrontend",
            "SUPPORTED_DEEP_METHODS",
            "SuperPointFrontend",
            "normalize_deep_method",
            "resolve_torch_device",
        ):
            with self.subTest(name=name):
                self.assertIs(getattr(controlnet_frontends, name), getattr(image_match_frontends, name))
                self.assertIn(name, controlnet_frontends.__all__)

    def test_controlnet_deep_matchers_reexports_image_match_matcher_api(self):
        controlnet_matchers = importlib.import_module("controlnet_construct.deep_matchers")
        image_match_matchers = importlib.import_module("image_match.deep_matchers")

        for name in (
            "DeepMatchResult",
            "DeepMatcherError",
            "LightGlueMatcher",
            "LoFTRMatcher",
            "SuperGlueMatcher",
            "_default_feature_extractor_for_matcher",
            "build_deep_matcher",
        ):
            with self.subTest(name=name):
                self.assertIs(getattr(controlnet_matchers, name), getattr(image_match_matchers, name))
                self.assertIn(name, controlnet_matchers.__all__)

    def test_deep_adapter_rejects_cross_method_fallback(self):
        deep_adapter_module = importlib.import_module("controlnet_construct.deep_adapter")
        adapter = deep_adapter_module.DeepMatcherAdapter()

        with self.assertRaisesRegex(RuntimeError, "same method"):
            adapter._raise_cross_method_fallback_error("loftr", "bf")

    def test_deep_adapter_missing_dependency_error_is_explicit(self):
        deep_adapter_module = importlib.import_module("controlnet_construct.deep_adapter")
        error = deep_adapter_module.DeepDependencyError("lightglue", "torch not installed")
        self.assertIn("lightglue", str(error))
        self.assertIn("torch not installed", str(error))

    def test_deep_dependency_error_is_pickle_round_trippable(self):
        import pickle

        deep_adapter_module = importlib.import_module("controlnet_construct.deep_adapter")
        error = deep_adapter_module.DeepDependencyError("lightglue", "torch not installed")

        restored = pickle.loads(pickle.dumps(error))

        self.assertIsInstance(restored, deep_adapter_module.DeepDependencyError)
        self.assertEqual(restored.method, "lightglue")
        self.assertEqual(restored.reason, "torch not installed")

    def test_deep_adapter_normalizes_outputs_to_match_triplet(self):
        deep_adapter_module = importlib.import_module("controlnet_construct.deep_adapter")

        adapter = deep_adapter_module.DeepMatcherAdapter()
        left_kps, right_kps, matches = adapter._normalize_matches(
            left_points=np.array([[1.0, 2.0]], dtype=np.float32),
            right_points=np.array([[3.0, 4.0]], dtype=np.float32),
            scores=np.array([0.9], dtype=np.float32),
        )
        self.assertEqual(len(left_kps), 1)
        self.assertEqual(len(right_kps), 1)
        self.assertEqual(len(matches), 1)

    def test_superpoint_frontend_extract_raises_dependency_error_without_torch(self):
        deep_frontends_module = importlib.import_module("controlnet_construct.deep_frontends")
        frontend = deep_frontends_module.SuperPointFrontend()
        image = np.arange(25, dtype=np.float32).reshape(5, 5)

        with self.assertRaisesRegex(RuntimeError, "superglue|lightglue|dependency|torch"):
            frontend.extract(image, device="cpu")

    def test_deep_adapter_superglue_and_lightglue_raise_dependency_error_without_optional_deps(self):
        deep_adapter_module = importlib.import_module("controlnet_construct.deep_adapter")
        image = np.arange(64, dtype=np.float32).reshape(8, 8)

        adapter = deep_adapter_module.DeepMatcherAdapter(prefer_gpu=False)
        for method in ("superglue", "lightglue"):
            with self.subTest(method=method):
                with self.assertRaises(deep_adapter_module.DeepDependencyError):
                    adapter.match_pair_with_fallback(
                        matcher_method=method,
                        left_image=image,
                        right_image=image + 1.0,
                        prefer_gpu=False,
                    )

    def test_deep_adapter_loftr_raises_dependency_error_without_optional_deps(self):
        deep_adapter_module = importlib.import_module("controlnet_construct.deep_adapter")
        image = np.arange(100, dtype=np.float32).reshape(10, 10)
        kornia_feature_module = _stub_module("kornia.feature")
        kornia_module = _stub_module("kornia", feature=kornia_feature_module)

        adapter = deep_adapter_module.DeepMatcherAdapter(prefer_gpu=False)
        with mock.patch.dict(
            sys.modules,
            {"kornia": kornia_module, "kornia.feature": kornia_feature_module},
            clear=False,
        ):
            with self.assertRaises(deep_adapter_module.DeepDependencyError):
                adapter.match_pair_with_fallback(
                    matcher_method="loftr",
                    left_image=image,
                    right_image=image,
                    prefer_gpu=False,
                )

    def test_deep_adapter_defaults_loftr_extractor_without_runtime_config(self):
        deep_adapter_module = importlib.import_module("controlnet_construct.deep_adapter")
        image = np.arange(100, dtype=np.float32).reshape(10, 10)
        prepared = {"left": object(), "right": object()}

        class _CapturingLoFTRMatcher:
            def match(self, **_kwargs):
                return (
                    np.zeros((0, 2), dtype=np.float32),
                    np.zeros((0, 2), dtype=np.float32),
                    np.zeros((0,), dtype=np.float32),
                )

        adapter = deep_adapter_module.DeepMatcherAdapter(prefer_gpu=False)
        with mock.patch.object(adapter._loftr_frontend, "prepare", return_value=prepared), mock.patch.object(
            deep_adapter_module,
            "build_deep_matcher",
            return_value=_CapturingLoFTRMatcher(),
        ) as build_matcher_mock:
            adapter.match_pair(
                matcher_method="loftr",
                left_image=image,
                right_image=image,
            )

        build_matcher_mock.assert_called_once_with(
            "loftr",
            device="cpu",
            feature_extractor_method="loftr",
            matcher_options={},
            feature_options={},
            device_options={},
        )

    def test_deep_adapter_wraps_matcher_dependency_error_as_deep_dependency_error(self):
        deep_adapter_module = importlib.import_module("controlnet_construct.deep_adapter")
        image = np.arange(64, dtype=np.float32).reshape(8, 8)

        class _RaisingMatcher:
            def match(self, **_kwargs):
                raise deep_adapter_module.DeepMatcherError(
                    "Deep matcher 'lightglue' dependency unavailable: missing 'lightglue'. "
                    "Install with `pip install lightglue`."
                )

        adapter = deep_adapter_module.DeepMatcherAdapter(prefer_gpu=False)
        with mock.patch.object(
            deep_adapter_module,
            "build_deep_matcher",
            return_value=_RaisingMatcher(),
        ), mock.patch.object(
            adapter._superpoint,
            "extract",
            return_value={"keypoints": np.array([[1.0, 2.0]], dtype=np.float32), "descriptors": np.zeros((1, 256), dtype=np.float32)},
        ):
            with self.assertRaises(deep_adapter_module.DeepDependencyError) as raised:
                adapter.match_pair(
                    matcher_method="lightglue",
                    left_image=image,
                    right_image=image,
                )
        self.assertEqual(raised.exception.method, "lightglue")
        self.assertIn("missing", raised.exception.reason.lower())

    def test_match_tile_dispatches_to_deep_adapter_for_lightglue(self):
        calls = []
        keypoint = cv2.KeyPoint(1.0, 1.0, 1.0)
        gradient = np.arange(256, dtype=np.float64).reshape(16, 16)
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")

        class _StubAdapter:
            def match_pair_with_fallback(self, **kwargs):
                calls.append(kwargs["matcher_method"])
                return deep_matchers_module.DeepMatchResult(
                    left_keypoints=(keypoint,),
                    right_keypoints=(keypoint,),
                    matches=(),
                )

        with mock.patch.object(tile_matching_module, "_DEEP_MATCHER_ADAPTER_CACHE", {}, create=True), mock.patch(
            "controlnet_construct.tile_matching.DeepMatcherAdapter",
            return_value=_StubAdapter(),
            create=True,
        ):
            tile_matching_module._match_tile_from_window_values(
                left_values=gradient,
                right_values=gradient + 1.0,
                local_window=TileWindow(0, 0, 16, 16),
                left_window=TileWindow(0, 0, 16, 16),
                right_window=TileWindow(0, 0, 16, 16),
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                left_invalid_values=(),
                right_invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=1,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=0,
                ratio_test=0.75,
                matcher_method="lightglue",
                max_features=None,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                use_gpu=True,
            )
        self.assertEqual(calls, ["lightglue"])

    def test_match_tile_deep_gpu_failure_falls_back_to_cpu_same_method(self):
        keypoint = cv2.KeyPoint(1.0, 1.0, 1.0)
        gradient = np.arange(256, dtype=np.float64).reshape(16, 16)
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")

        class _StubAdapter:
            def __init__(self):
                self.calls = []

            def match_pair_with_fallback(self, **kwargs):
                self.calls.append((kwargs["matcher_method"], kwargs["prefer_gpu"]))
                return deep_matchers_module.DeepMatchResult(
                    left_keypoints=(keypoint,),
                    right_keypoints=(keypoint,),
                    matches=(),
                )

        stub = _StubAdapter()
        with mock.patch.object(tile_matching_module, "_DEEP_MATCHER_ADAPTER_CACHE", {}, create=True), mock.patch(
            "controlnet_construct.tile_matching.DeepMatcherAdapter",
            return_value=stub,
            create=True,
        ):
            tile_matching_module._match_tile_from_window_values(
                left_values=gradient,
                right_values=gradient + 1.0,
                local_window=TileWindow(0, 0, 16, 16),
                left_window=TileWindow(0, 0, 16, 16),
                right_window=TileWindow(0, 0, 16, 16),
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                left_invalid_values=(),
                right_invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=1,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=0,
                ratio_test=0.75,
                matcher_method="loftr",
                max_features=None,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                use_gpu=True,
            )
        self.assertEqual(stub.calls[0][0], "loftr")
        self.assertTrue(stub.calls[0][1])

    def test_match_tile_reuses_deep_adapter_instance_for_repeated_dispatch(self):
        deep_matchers_module = importlib.import_module("controlnet_construct.deep_matchers")
        gradient = np.arange(256, dtype=np.float64).reshape(16, 16)
        constructor_calls = 0

        class _StubAdapter:
            def match_pair_with_fallback(self, **_kwargs):
                keypoint = cv2.KeyPoint(1.0, 1.0, 1.0)
                return deep_matchers_module.DeepMatchResult(
                    left_keypoints=(keypoint,),
                    right_keypoints=(keypoint,),
                    matches=(),
                )

        def _build_stub_adapter(*_args, **_kwargs):
            nonlocal constructor_calls
            constructor_calls += 1
            return _StubAdapter()

        with mock.patch.object(tile_matching_module, "_DEEP_MATCHER_ADAPTER_CACHE", {}, create=True), mock.patch(
            "controlnet_construct.tile_matching.DeepMatcherAdapter",
            side_effect=_build_stub_adapter,
            create=True,
        ):
            for _ in range(2):
                tile_matching_module._match_tile_from_window_values(
                    left_values=gradient,
                    right_values=gradient + 1.0,
                    local_window=TileWindow(0, 0, 16, 16),
                    left_window=TileWindow(0, 0, 16, 16),
                    right_window=TileWindow(0, 0, 16, 16),
                    minimum_value=None,
                    maximum_value=None,
                    lower_percent=0.5,
                    upper_percent=99.5,
                    left_invalid_values=(),
                    right_invalid_values=(),
                    special_pixel_abs_threshold=1.0e300,
                    min_valid_pixels=1,
                    valid_pixel_percent_threshold=0.0,
                    invalid_pixel_radius=0,
                    ratio_test=0.75,
                    matcher_method="lightglue",
                    max_features=None,
                    sift_octave_layers=3,
                    sift_contrast_threshold=0.04,
                    sift_edge_threshold=10.0,
                    sift_sigma=1.6,
                    use_gpu=True,
                )
        self.assertEqual(constructor_calls, 1)

    def test_match_dom_pair_passes_matcher_method_into_parallel_tile_tasks(self):
        width = 128
        height = 128
        image = _build_textured_test_image(width, height)

        synthetic_tile_results = [
            image_match.TileMatchResult(
                stats=image_match.TileMatchStats(
                    local_start_x=0,
                    local_start_y=0,
                    width=64,
                    height=64,
                    left_start_x=0,
                    left_start_y=0,
                    right_start_x=0,
                    right_start_y=0,
                    left_valid_pixel_count=4096,
                    right_valid_pixel_count=4096,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=5,
                    right_feature_count=5,
                    match_count=1,
                    status="matched",
                ),
                left_points=(Keypoint(10.0, 10.0),),
                right_points=(Keypoint(10.5, 10.5),),
            ),
        ]

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_matcher_method.cub",
                right_name="right_matcher_method.cub",
            )

            with mock.patch.object(
                image_match,
                "_run_parallel_tile_match_tasks",
                return_value=synthetic_tile_results,
            ) as parallel_mock:
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    max_image_dimension=64,
                    block_width=64,
                    block_height=64,
                    overlap_x=0,
                    overlap_y=0,
                    min_valid_pixels=16,
                    matcher_method="flann",
                )

        submitted_tasks = parallel_mock.call_args.args[0]
        self.assertTrue(submitted_tasks)
        self.assertTrue(all(task.matcher_method == "flann" for task in submitted_tasks))
        self.assertEqual(summary["matcher"]["matcher_method_requested"], "flann")
        self.assertEqual(summary["matcher"]["matcher_method_used"], "flann")
        self.assertEqual(summary["matcher"]["flann_index_params"]["algorithm"], "KDTree")

    def test_match_dom_pair_forwards_custom_low_resolution_trim_fraction(self):
        image = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_lowres_trim_forward.cub",
                right_name="right_lowres_trim_forward.cub",
            )

            with mock.patch.object(
                image_match,
                "_estimate_low_resolution_projected_offset",
                return_value={
                    "enabled": True,
                    "status": "succeeded",
                    "fallback_offset_zero": False,
                    "reason": "ok",
                    "delta_x_projected": 0.0,
                    "delta_y_projected": 0.0,
                    "retained_match_count": 0,
                    "trim_fraction_each_side": 0.12,
                    "min_retained_match_count": 5,
                    "max_mean_projected_offset_meters": 2000.0,
                    "mean_projected_offset_meters": 0.0,
                },
            ) as estimate_mock:
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    min_valid_pixels=16,
                    enable_low_resolution_offset_estimation=True,
                    low_resolution_trim_fraction_each_side=0.12,
                )

        self.assertAlmostEqual(summary["low_resolution_trim_fraction_each_side"], 0.12)
        self.assertAlmostEqual(summary["low_resolution_offset"]["trim_fraction_each_side"], 0.12)
        self.assertAlmostEqual(
            estimate_mock.call_args.kwargs["low_resolution_trim_fraction_each_side"],
            0.12,
        )

    def test_match_dom_pair_forwards_low_resolution_min_match_count_and_offset_threshold(self):
        image = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_lowres_threshold_forward.cub",
                right_name="right_lowres_threshold_forward.cub",
            )

            with mock.patch.object(
                image_match,
                "_estimate_low_resolution_projected_offset",
                return_value={
                    "enabled": True,
                    "status": "fallback_zero",
                    "fallback_offset_zero": True,
                    "reason": "thresholded",
                    "delta_x_projected": 0.0,
                    "delta_y_projected": 0.0,
                    "retained_match_count": 4,
                    "trim_fraction_each_side": 0.05,
                    "min_retained_match_count": 5,
                    "max_mean_projected_offset_meters": 2000.0,
                    "mean_projected_offset_meters": None,
                },
            ) as estimate_mock:
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    min_valid_pixels=16,
                    enable_low_resolution_offset_estimation=True,
                    low_resolution_min_retained_match_count=5,
                    low_resolution_max_mean_projected_offset_meters=2000.0,
                )

        self.assertEqual(summary["low_resolution_offset"]["min_retained_match_count"], 5)
        self.assertAlmostEqual(summary["low_resolution_offset"]["max_mean_projected_offset_meters"], 2000.0)
        self.assertEqual(
            estimate_mock.call_args.kwargs["low_resolution_min_retained_match_count"],
            5,
        )
        self.assertAlmostEqual(
            estimate_mock.call_args.kwargs["low_resolution_max_mean_projected_offset_meters"],
            2000.0,
        )

    def test_match_dom_pair_derives_low_resolution_level_from_target_long_edge(self):
        image = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_lowres_target.cub",
                right_name="right_lowres_target.cub",
            )
            expected_level = lowres_offset_module.reduce_level_for_pair_target_long_edge(
                left_width=64,
                left_height=64,
                right_width=64,
                right_height=64,
                target_long_edge=32,
            )
            with mock.patch.object(
                image_match,
                "_estimate_low_resolution_projected_offset",
                return_value={
                    "enabled": True,
                    "status": "succeeded",
                    "fallback_offset_zero": False,
                    "reason": "ok",
                    "delta_x_projected": 0.0,
                    "delta_y_projected": 0.0,
                    "retained_match_count": 0,
                    "trim_fraction_each_side": 0.05,
                    "min_retained_match_count": 5,
                    "max_mean_projected_offset_meters": 0.0,
                    "mean_projected_offset_meters": 0.0,
                },
            ) as estimate_mock:
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    min_valid_pixels=16,
                    enable_low_resolution_offset_estimation=True,
                    low_resolution_matching_target_long_edge=32,
                )

        self.assertEqual(summary["low_resolution_matching_target_long_edge"], 32)
        self.assertEqual(summary["resolved_low_resolution_level"], expected_level)
        self.assertEqual(estimate_mock.call_args.kwargs["low_resolution_level"], expected_level)

    def test_match_dom_pair_explicit_low_resolution_level_overrides_target_long_edge(self):
        image = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_lowres_override.cub",
                right_name="right_lowres_override.cub",
            )
            with mock.patch.object(
                image_match,
                "_estimate_low_resolution_projected_offset",
                return_value={
                    "enabled": True,
                    "status": "succeeded",
                    "fallback_offset_zero": False,
                    "reason": "ok",
                    "delta_x_projected": 0.0,
                    "delta_y_projected": 0.0,
                    "retained_match_count": 0,
                    "trim_fraction_each_side": 0.05,
                    "min_retained_match_count": 5,
                    "max_mean_projected_offset_meters": 0.0,
                    "mean_projected_offset_meters": 0.0,
                },
            ) as estimate_mock:
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    min_valid_pixels=16,
                    enable_low_resolution_offset_estimation=True,
                    low_resolution_level=2,
                    low_resolution_matching_target_long_edge=32,
                )

        self.assertEqual(summary["low_resolution_matching_target_long_edge"], 32)
        self.assertEqual(summary["resolved_low_resolution_level"], 2)
        self.assertEqual(estimate_mock.call_args.kwargs["low_resolution_level"], 2)

    def test_match_dom_pair_prefilters_invalid_tiles_and_reports_summary(self):
        values = np.zeros((32, 64), dtype=np.float64)
        values[:, :32] = _build_textured_test_image(32, 32)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                values,
                pixel_type=ip.PixelType.Real,
                left_name="left_prefilter.cub",
                right_name="right_prefilter.cub",
            )
            cache_dir = temp_dir / "tile_validity_cache"
            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=32,
                block_width=32,
                block_height=32,
                overlap_x=0,
                overlap_y=0,
                invalid_values=(0.0,),
                invalid_pixel_radius=0,
                valid_pixel_percent_threshold=0.2,
                min_valid_pixels=16,
                use_parallel_cpu=False,
                enable_tile_validity_prefilter=True,
                tile_validity_cache_dir=cache_dir,
                tile_validity_cell_width=32,
                tile_validity_cell_height=32,
            )

        self.assertTrue(summary["tile_validity_prefilter_enabled"])
        self.assertEqual(summary["tile_count"], 2)
        self.assertEqual(summary["tile_count_before_preindex_filter"], 2)
        self.assertEqual(summary["tile_count_after_preindex_filter"], 1)
        self.assertEqual(summary["preindexed_skipped_tile_count"], 1)
        self.assertEqual(summary["tile_validity_cache_dir"], str(cache_dir))
        self.assertEqual(
            summary["full_resolution_skipped_tile_count"],
            summary["skipped_tile_count"] - summary["preindexed_skipped_tile_count"],
        )
        self.assertIn(summary["left_tile_validity_index"]["status"], {"rebuilt", "hit"})
        self.assertIn(summary["right_tile_validity_index"]["status"], {"rebuilt", "hit"})

    def test_match_dom_pair_keeps_prefilter_disabled_by_default(self):
        values = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                values,
                pixel_type=ip.PixelType.Real,
                left_name="left_prefilter_default.cub",
                right_name="right_prefilter_default.cub",
            )
            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=32,
                block_width=32,
                block_height=32,
                overlap_x=0,
                overlap_y=0,
                valid_pixel_percent_threshold=0.2,
                invalid_pixel_radius=0,
                use_parallel_cpu=False,
            )

        self.assertFalse(summary["tile_validity_prefilter_enabled"])
        self.assertEqual(summary["tile_count_before_preindex_filter"], summary["tile_count"])
        self.assertEqual(summary["tile_count_after_preindex_filter"], summary["tile_count"])
        self.assertEqual(summary["preindexed_skipped_tile_count"], 0)
        self.assertIsNone(summary["tile_validity_cache_dir"])

    def test_estimate_low_resolution_projected_offset_rejects_large_reprojection_error(self):
        with temporary_directory() as temp_dir:
            left_low_res_dom, right_low_res_dom = _write_projected_dom_pair(
                temp_dir,
                _build_textured_test_image(32, 32),
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_low_res_reproj.cub",
                right_name="right_low_res_reproj.cub",
            )

            filtered_left = KeypointFile(
                32,
                32,
                (
                    Keypoint(5.0, 5.0),
                    Keypoint(10.0, 5.0),
                    Keypoint(5.0, 10.0),
                    Keypoint(10.0, 10.0),
                ),
            )
            filtered_right = KeypointFile(
                32,
                32,
                (
                    Keypoint(25.0, 25.0),
                    Keypoint(30.0, 25.0),
                    Keypoint(25.0, 30.0),
                    Keypoint(30.0, 30.0),
                ),
            )

            summary = image_match._estimate_low_resolution_projected_offset(
                left_low_res_dom,
                right_low_res_dom,
                enabled=True,
                low_resolution_level=3,
                low_resolution_output_dir=temp_dir,
                band=1,
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=64,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=1,
                matcher_method="bf",
                ratio_test=0.75,
                max_features=None,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                low_resolution_trim_fraction_each_side=0.0,
                low_resolution_max_mean_reprojection_error_pixels=3.0,
                low_resolution_min_retained_match_count=4,
                low_resolution_max_mean_projected_offset_meters=0.0,
                match_dom_pair_func=mock.Mock(return_value=(filtered_left, filtered_right, {"status": "matched"})),
                filter_stereo_pair_keypoints_with_ransac_func=mock.Mock(
                    return_value=(
                        filtered_left,
                        filtered_right,
                        {
                            "applied": True,
                            "status": "filtered",
                            "homography_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                        },
                    )
                ),
                write_stereo_pair_match_visualization_func=mock.Mock(return_value={"output_path": "ignored.png"}),
                require_command_func=mock.Mock(),
                create_low_resolution_dom_func=mock.Mock(side_effect=[left_low_res_dom, right_low_res_dom]),
            )

        self.assertEqual(summary["status"], "fallback_zero")
        self.assertTrue(summary["fallback_offset_zero"])
        self.assertEqual(summary["failure_reason_code"], "reprojection_error_above_threshold")
        self.assertGreater(summary["trimmed_mean_reprojection_error_pixels"], 3.0)
        self.assertEqual(summary["delta_x_projected"], 0.0)
        self.assertEqual(summary["delta_y_projected"], 0.0)

    def test_estimate_low_resolution_projected_offset_rejects_retained_match_count_below_threshold(self):
        with temporary_directory() as temp_dir:
            fake_left_dom = temp_dir / "left_min_matches.cub"
            fake_right_dom = temp_dir / "right_min_matches.cub"
            fake_left_dom.write_bytes(b"left")
            fake_right_dom.write_bytes(b"right")
            filtered_left = KeypointFile(
                32,
                32,
                (
                    Keypoint(5.0, 5.0),
                    Keypoint(10.0, 5.0),
                    Keypoint(5.0, 10.0),
                    Keypoint(10.0, 10.0),
                ),
            )
            filtered_right = KeypointFile(
                32,
                32,
                (
                    Keypoint(15.0, 15.0),
                    Keypoint(20.0, 15.0),
                    Keypoint(15.0, 20.0),
                    Keypoint(20.0, 20.0),
                ),
            )

            summary = image_match._estimate_low_resolution_projected_offset(
                fake_left_dom,
                fake_right_dom,
                enabled=True,
                low_resolution_level=3,
                low_resolution_output_dir=temp_dir,
                band=1,
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=64,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=1,
                matcher_method="bf",
                ratio_test=0.75,
                max_features=None,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                low_resolution_trim_fraction_each_side=0.05,
                low_resolution_max_mean_reprojection_error_pixels=3.0,
                low_resolution_min_retained_match_count=5,
                low_resolution_max_mean_projected_offset_meters=0.0,
                match_dom_pair_func=mock.Mock(return_value=(filtered_left, filtered_right, {"status": "matched"})),
                filter_stereo_pair_keypoints_with_ransac_func=mock.Mock(
                    return_value=(
                        filtered_left,
                        filtered_right,
                        {
                            "applied": True,
                            "status": "filtered",
                            "homography_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                        },
                    )
                ),
                write_stereo_pair_match_visualization_func=mock.Mock(return_value={"output_path": "ignored.png"}),
                require_command_func=mock.Mock(),
                create_low_resolution_dom_func=mock.Mock(side_effect=[fake_left_dom, fake_right_dom]),
            )

        self.assertEqual(summary["status"], "fallback_zero")
        self.assertTrue(summary["fallback_offset_zero"])
        self.assertEqual(summary["failure_reason_code"], "retained_match_count_below_threshold")
        self.assertEqual(summary["retained_match_count"], 4)
        self.assertEqual(summary["min_retained_match_count"], 5)
        self.assertIsNone(summary["trimmed_mean_reprojection_error_pixels"])
        self.assertIsNone(summary["mean_projected_offset_meters"])

    def test_estimate_low_resolution_projected_offset_rejects_large_mean_projected_offset(self):
        with temporary_directory() as temp_dir:
            left_cube, left_low_res_dom = make_test_cube(
                temp_dir,
                name="left_low_res_offset_threshold.cub",
                samples=32,
                lines=32,
                bands=1,
                pixel_type=ip.PixelType.UnsignedByte,
            )
            right_cube, right_low_res_dom = make_test_cube(
                temp_dir,
                name="right_low_res_offset_threshold.cub",
                samples=32,
                lines=32,
                bands=1,
                pixel_type=ip.PixelType.UnsignedByte,
            )
            try:
                _write_array_to_cube(left_cube, _build_textured_test_image(32, 32))
                _write_array_to_cube(right_cube, _build_textured_test_image(32, 32))
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=32.0)
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=5000.0, upper_left_y=32.0)
            finally:
                left_cube.close()
                right_cube.close()

            filtered_left = KeypointFile(
                32,
                32,
                (
                    Keypoint(5.0, 5.0),
                    Keypoint(10.0, 5.0),
                    Keypoint(5.0, 10.0),
                    Keypoint(10.0, 10.0),
                    Keypoint(12.0, 12.0),
                ),
            )
            filtered_right = KeypointFile(
                32,
                32,
                (
                    Keypoint(5.0, 5.0),
                    Keypoint(10.0, 5.0),
                    Keypoint(5.0, 10.0),
                    Keypoint(10.0, 10.0),
                    Keypoint(12.0, 12.0),
                ),
            )

            summary = image_match._estimate_low_resolution_projected_offset(
                left_low_res_dom,
                right_low_res_dom,
                enabled=True,
                low_resolution_level=3,
                low_resolution_output_dir=temp_dir,
                band=1,
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=64,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=1,
                matcher_method="bf",
                ratio_test=0.75,
                max_features=None,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                low_resolution_trim_fraction_each_side=0.0,
                low_resolution_max_mean_reprojection_error_pixels=3.0,
                low_resolution_min_retained_match_count=5,
                low_resolution_max_mean_projected_offset_meters=2000.0,
                match_dom_pair_func=mock.Mock(return_value=(filtered_left, filtered_right, {"status": "matched"})),
                filter_stereo_pair_keypoints_with_ransac_func=mock.Mock(
                    return_value=(
                        filtered_left,
                        filtered_right,
                        {
                            "applied": True,
                            "status": "filtered",
                            "homography_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                        },
                    )
                ),
                write_stereo_pair_match_visualization_func=mock.Mock(return_value={"output_path": "ignored.png"}),
                require_command_func=mock.Mock(),
                create_low_resolution_dom_func=mock.Mock(side_effect=[left_low_res_dom, right_low_res_dom]),
            )

        self.assertEqual(summary["status"], "fallback_zero")
        self.assertTrue(summary["fallback_offset_zero"])
        self.assertEqual(summary["failure_reason_code"], "mean_projected_offset_above_threshold")
        self.assertGreater(summary["mean_projected_offset_meters"], 2000.0)
        self.assertEqual(summary["delta_x_projected"], 0.0)
        self.assertEqual(summary["delta_y_projected"], 0.0)

    def test_estimate_low_resolution_projected_offset_rejects_insufficient_points_for_homography(self):
        with temporary_directory() as temp_dir:
            fake_left_dom = temp_dir / "left_insufficient.cub"
            fake_right_dom = temp_dir / "right_insufficient.cub"
            fake_left_dom.write_bytes(b"left")
            fake_right_dom.write_bytes(b"right")
            filtered_left = KeypointFile(32, 32, (Keypoint(1.0, 1.0), Keypoint(2.0, 2.0), Keypoint(3.0, 3.0)))
            filtered_right = KeypointFile(32, 32, (Keypoint(1.5, 1.5), Keypoint(2.5, 2.5), Keypoint(3.5, 3.5)))

            summary = image_match._estimate_low_resolution_projected_offset(
                fake_left_dom,
                fake_right_dom,
                enabled=True,
                low_resolution_level=3,
                low_resolution_output_dir=temp_dir,
                band=1,
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=64,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=1,
                matcher_method="bf",
                ratio_test=0.75,
                max_features=None,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                low_resolution_trim_fraction_each_side=0.05,
                low_resolution_max_mean_reprojection_error_pixels=3.0,
                low_resolution_min_retained_match_count=3,
                low_resolution_max_mean_projected_offset_meters=0.0,
                match_dom_pair_func=mock.Mock(return_value=(filtered_left, filtered_right, {"status": "matched"})),
                filter_stereo_pair_keypoints_with_ransac_func=mock.Mock(
                    return_value=(
                        filtered_left,
                        filtered_right,
                        {
                            "applied": False,
                            "status": "skipped_insufficient_points",
                            "homography_matrix": None,
                        },
                    )
                ),
                write_stereo_pair_match_visualization_func=mock.Mock(return_value={"output_path": "ignored.png"}),
                require_command_func=mock.Mock(),
                create_low_resolution_dom_func=mock.Mock(side_effect=[fake_left_dom, fake_right_dom]),
            )

        self.assertEqual(summary["status"], "fallback_zero")
        self.assertTrue(summary["fallback_offset_zero"])
        self.assertEqual(summary["failure_reason_code"], "insufficient_points_for_homography")
        self.assertIsNone(summary["trimmed_mean_reprojection_error_pixels"])

    def test_build_argument_parser_rejects_out_of_range_valid_pixel_percent_threshold(self):
        parser = build_argument_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left.cub",
                    "right.cub",
                    "left.key",
                    "right.key",
                    "--valid-pixel-percent-threshold",
                    "1.5",
                ]
            )

    def test_build_sift_detector_forwards_custom_parameters_to_opencv(self):
        fake_detector = object()

        with mock.patch.object(image_match.cv2, "SIFT_create", return_value=fake_detector) as sift_create:
            detector = image_match._build_sift_detector(
                max_features=2048,
                octave_layers=5,
                contrast_threshold=0.03,
                edge_threshold=12.0,
                sigma=1.8,
            )

        self.assertIs(detector, fake_detector)
        sift_create.assert_called_once_with(
            nfeatures=2048,
            nOctaveLayers=5,
            contrastThreshold=0.03,
            edgeThreshold=12.0,
            sigma=1.8,
        )

    def test_match_dom_pair_uses_shared_extent_for_unequal_dom_sizes(self):
        left_width = 128
        right_width = 120
        height = 128
        left_image = _build_textured_test_image(left_width, height)
        right_image = left_image[:, :right_width]

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="left_shared_extent_dom.cub", samples=left_width, lines=height, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="right_shared_extent_dom.cub", samples=right_width, lines=height, bands=1)
            try:
                _write_array_to_cube(left_cube, left_image)
                _write_array_to_cube(right_cube, right_image)
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
            finally:
                left_cube.close()
                right_cube.close()

            left_key_file, right_key_file, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=64,
                block_width=64,
                block_height=64,
                overlap_x=16,
                overlap_y=16,
                min_valid_pixels=32,
                ratio_test=0.8,
            )

        self.assertTrue(summary["tiling_used"])
        self.assertTrue(summary["dimension_mismatch"])
        self.assertEqual(summary["shared_extent_width"], right_width)
        self.assertEqual(summary["shared_extent_height"], height)
        self.assertGreater(summary["point_count"], 0)
        self.assertEqual(len(left_key_file.points), len(right_key_file.points))
        self.assertTrue(all(1.0 <= point.sample <= left_width for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.sample <= right_width for point in right_key_file.points))

    def test_match_dom_pair_reassembles_global_coordinates_after_tiling(self):
        width = 128
        height = 128
        image = _build_textured_test_image(width, height)

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="left_dom.cub", samples=width, lines=height, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="right_dom.cub", samples=width, lines=height, bands=1)
            try:
                _write_array_to_cube(left_cube, image)
                _write_array_to_cube(right_cube, image)
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
            finally:
                left_cube.close()
                right_cube.close()

            left_key_file, right_key_file, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=64,
                block_width=64,
                block_height=64,
                overlap_x=16,
                overlap_y=16,
                min_valid_pixels=32,
                ratio_test=0.8,
            )

        self.assertTrue(summary["tiling_used"])
        self.assertGreater(summary["tile_count"], 1)
        self.assertGreater(summary["point_count"], 0)
        self.assertEqual(len(left_key_file.points), len(right_key_file.points))
        self.assertTrue(any(point.sample > 64.0 or point.line > 64.0 for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.sample <= width for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.line <= height for point in left_key_file.points))

    def test_match_dom_pair_uses_parallel_helper_for_multi_tile_runs_by_default(self):
        width = 128
        height = 128
        image = _build_textured_test_image(width, height)

        synthetic_tile_results = [
            image_match.TileMatchResult(
                stats=image_match.TileMatchStats(
                    local_start_x=0,
                    local_start_y=0,
                    width=64,
                    height=64,
                    left_start_x=0,
                    left_start_y=0,
                    right_start_x=0,
                    right_start_y=0,
                    left_valid_pixel_count=4096,
                    right_valid_pixel_count=4096,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=5,
                    right_feature_count=5,
                    match_count=1,
                    status="matched",
                ),
                left_points=(Keypoint(10.0, 10.0),),
                right_points=(Keypoint(10.5, 10.5),),
            ),
            image_match.TileMatchResult(
                stats=image_match.TileMatchStats(
                    local_start_x=64,
                    local_start_y=0,
                    width=64,
                    height=64,
                    left_start_x=64,
                    left_start_y=0,
                    right_start_x=64,
                    right_start_y=0,
                    left_valid_pixel_count=4096,
                    right_valid_pixel_count=4096,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=5,
                    right_feature_count=5,
                    match_count=1,
                    status="matched",
                ),
                left_points=(Keypoint(80.0, 20.0),),
                right_points=(Keypoint(80.5, 20.5),),
            ),
        ]

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_parallel_default.cub",
                right_name="right_parallel_default.cub",
            )

            with mock.patch.object(
                image_match,
                "_run_parallel_tile_match_tasks",
                return_value=synthetic_tile_results,
            ) as parallel_mock:
                left_key_file, right_key_file, summary = match_dom_pair(
                    left_path,
                    right_path,
                    max_image_dimension=64,
                    block_width=64,
                    block_height=64,
                    overlap_x=0,
                    overlap_y=0,
                    min_valid_pixels=16,
                )

        parallel_mock.assert_called_once()
        self.assertEqual(parallel_mock.call_args.kwargs["max_workers"], 4)
        self.assertTrue(summary["parallel_cpu_requested"])
        self.assertEqual(summary["num_worker_parallel_cpu"], 8)
        self.assertTrue(summary["parallel_cpu_used"])
        self.assertEqual(summary["parallel_cpu_backend"], "process_pool_batched_cube_reuse")
        self.assertEqual(summary["tile_match_backend"], "process_pool_batched_cube_reuse")
        self.assertEqual(summary["parallel_cpu_worker_count"], 4)
        self.assertEqual(summary["point_count"], 2)
        self.assertEqual(len(left_key_file.points), 2)
        self.assertEqual(len(right_key_file.points), 2)

    def test_match_dom_pair_respects_requested_parallel_worker_limit(self):
        width = 128
        height = 128
        image = _build_textured_test_image(width, height)

        synthetic_tile_results = [
            image_match.TileMatchResult(
                stats=image_match.TileMatchStats(
                    local_start_x=0,
                    local_start_y=0,
                    width=64,
                    height=64,
                    left_start_x=0,
                    left_start_y=0,
                    right_start_x=0,
                    right_start_y=0,
                    left_valid_pixel_count=4096,
                    right_valid_pixel_count=4096,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=5,
                    right_feature_count=5,
                    match_count=1,
                    status="matched",
                ),
                left_points=(Keypoint(10.0, 10.0),),
                right_points=(Keypoint(10.5, 10.5),),
            ),
        ]

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_parallel_cap.cub",
                right_name="right_parallel_cap.cub",
            )

            with mock.patch.object(
                image_match,
                "_run_parallel_tile_match_tasks",
                return_value=synthetic_tile_results,
            ) as parallel_mock:
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    max_image_dimension=64,
                    block_width=64,
                    block_height=64,
                    overlap_x=0,
                    overlap_y=0,
                    min_valid_pixels=16,
                    num_worker_parallel_cpu=2,
                )

        parallel_mock.assert_called_once()
        self.assertEqual(parallel_mock.call_args.kwargs["max_workers"], 2)
        self.assertEqual(summary["num_worker_parallel_cpu"], 2)
        self.assertTrue(summary["parallel_cpu_used"])
        self.assertEqual(summary["tile_match_backend"], "process_pool_batched_cube_reuse")
        self.assertEqual(summary["parallel_cpu_worker_count"], 2)

    def test_match_dom_pair_reports_serial_backend_when_parallel_cpu_is_disabled(self):
        image = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_parallel_disabled.cub",
                right_name="right_parallel_disabled.cub",
            )

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                min_valid_pixels=16,
                use_parallel_cpu=False,
            )

        self.assertFalse(summary["parallel_cpu_requested"])
        self.assertEqual(summary["num_worker_parallel_cpu"], 8)
        self.assertFalse(summary["parallel_cpu_used"])
        self.assertEqual(summary["parallel_cpu_backend"], "serial")
        self.assertEqual(summary["tile_match_backend"], "serial")
        self.assertEqual(summary["parallel_cpu_worker_count"], 1)

    def test_match_dom_pair_progress_reports_full_resolution_tile_count_and_completion(self):
        image = _build_textured_test_image(128, 128)

        def fake_serial_tile_match_tasks(windows, **kwargs):
            progress_callback = kwargs.get("progress_callback")
            tile_results = []
            for paired_window in windows:
                if progress_callback is not None:
                    progress_callback()
                tile_results.append(
                    image_match.TileMatchResult(
                        stats=image_match.TileMatchStats(
                            local_start_x=paired_window.local_window.start_x,
                            local_start_y=paired_window.local_window.start_y,
                            width=paired_window.local_window.width,
                            height=paired_window.local_window.height,
                            left_start_x=paired_window.left_window.start_x,
                            left_start_y=paired_window.left_window.start_y,
                            right_start_x=paired_window.right_window.start_x,
                            right_start_y=paired_window.right_window.start_y,
                            left_valid_pixel_count=paired_window.local_window.width * paired_window.local_window.height,
                            right_valid_pixel_count=paired_window.local_window.width * paired_window.local_window.height,
                            left_valid_pixel_ratio=1.0,
                            right_valid_pixel_ratio=1.0,
                            left_feature_count=0,
                            right_feature_count=0,
                            match_count=0,
                            status="skipped_no_matches",
                        ),
                        left_points=(),
                        right_points=(),
                    )
                )
            return tile_matching_module.TileMatchBatchResult(results=tile_results)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_progress.cub",
                right_name="right_progress.cub",
            )
            stderr = io.StringIO()

            with mock.patch.object(image_match.sys, "stderr", stderr), mock.patch.object(
                image_match,
                "_run_serial_tile_match_tasks",
                side_effect=fake_serial_tile_match_tasks,
            ) as serial_mock:
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    max_image_dimension=64,
                    block_width=64,
                    block_height=64,
                    overlap_x=0,
                    overlap_y=0,
                    min_valid_pixels=16,
                    use_parallel_cpu=False,
                    show_progress=True,
                )

        progress_output = stderr.getvalue()
        self.assertEqual(summary["tile_count"], 4)
        self.assertIn("4 TILE(s) to process at full resolution", progress_output)
        self.assertIn("4/4 TILE(s) done", progress_output)
        self.assertIsNotNone(serial_mock.call_args.kwargs["progress_callback"])

    def test_image_match_main_omits_tile_details_from_stdout_and_writes_full_result_output(self):
        fake_result = {
            "status": "matched",
            "point_count": 12,
            "tile_count": 2,
            "matched_tile_count": 1,
            "skipped_tile_count": 1,
            "tiles": [
                {
                    "local_start_x": 0,
                    "status": "matched",
                }
            ],
        }

        with temporary_directory() as temp_dir:
            result_output_path = temp_dir / "result" / "image_match_full.json"
            stdout = io.StringIO()

            with mock.patch.object(image_match, "match_dom_pair_to_key_files", return_value=fake_result):
                with mock.patch.object(sys, "stdout", stdout):
                    image_match.main(
                        [
                            "left.cub",
                            "right.cub",
                            "left.key",
                            "right.key",
                            "--omit-tile-details",
                            "--result-output",
                            str(result_output_path),
                        ]
                    )

            stdout_payload = json.loads(stdout.getvalue())
            full_result_payload = json.loads(result_output_path.read_text(encoding="utf-8"))

        self.assertNotIn("tiles", stdout_payload)
        self.assertEqual(stdout_payload["result_output"], str(result_output_path))
        self.assertEqual(full_result_payload["tiles"], fake_result["tiles"])
        self.assertEqual(full_result_payload["status"], "matched")

    def test_match_dom_pair_skips_invalid_only_tiles_but_keeps_valid_tile(self):
        width = 96
        height = 96
        image = np.full((height, width), SPECIAL_PIXEL, dtype=np.float64)
        image[48:96, 48:96] = _build_textured_test_image(48, 48)

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="left_invalid_dom.cub", samples=width, lines=height, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="right_invalid_dom.cub", samples=width, lines=height, bands=1)
            try:
                _write_array_to_cube(left_cube, image)
                _write_array_to_cube(right_cube, image)
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
            finally:
                left_cube.close()
                right_cube.close()

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=40,
                block_width=48,
                block_height=48,
                overlap_x=0,
                overlap_y=0,
                min_valid_pixels=32,
            )

        self.assertEqual(summary["tile_count"], 4)
        self.assertGreaterEqual(summary["skipped_tile_count"], 3)
        self.assertGreater(summary["point_count"], 0)
        self.assertIn(
            "skipped_insufficient_valid_pixels",
            {tile["status"] for tile in summary["tiles"]},
        )

    def test_match_dom_pair_skips_tile_when_valid_ratio_is_below_threshold(self):
        image = np.zeros((48, 48), dtype=np.float64)
        image[12:36, 12:36] = 100.0

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_ratio_skip.cub",
                right_name="right_ratio_skip.cub",
            )

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                min_valid_pixels=32,
                valid_pixel_percent_threshold=0.3,
                invalid_pixel_radius=0,
            )

        self.assertEqual(summary["point_count"], 0)
        self.assertEqual(summary["valid_pixel_percent_threshold"], 0.3)
        self.assertEqual(summary["tile_count"], 1)
        self.assertEqual(summary["tiles"][0]["status"], "skipped_valid_pixel_ratio_below_threshold")
        self.assertAlmostEqual(summary["tiles"][0]["left_valid_pixel_ratio"], 0.25, places=6)
        self.assertAlmostEqual(summary["tiles"][0]["right_valid_pixel_ratio"], 0.25, places=6)

    def test_match_dom_pair_reports_valid_pixel_ratio_fields_in_summary(self):
        image = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_ratio_summary.cub",
                right_name="right_ratio_summary.cub",
            )

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                min_valid_pixels=16,
                valid_pixel_percent_threshold=0.0,
            )

        self.assertIn("valid_pixel_percent_threshold", summary)
        self.assertIn("min_valid_pixels", summary)
        self.assertIn("left_valid_pixel_ratio", summary["tiles"][0])
        self.assertIn("right_valid_pixel_ratio", summary["tiles"][0])
        self.assertGreaterEqual(summary["tiles"][0]["left_valid_pixel_ratio"], 0.0)
        self.assertLessEqual(summary["tiles"][0]["left_valid_pixel_ratio"], 1.0)

    def test_match_dom_pair_reports_tile_block_alignment_off_by_default(self):
        image = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_alignment_default.cub",
                right_name="right_alignment_default.cub",
            )

            _, _, summary = match_dom_pair(left_path, right_path, min_valid_pixels=8)

        alignment = summary["tile_block_alignment"]
        self.assertEqual(alignment["mode"], "off")
        self.assertFalse(alignment["aligned"])
        self.assertEqual(alignment["requested_block_width"], 1024)
        self.assertEqual(alignment["effective_block_width"], 1024)

    def test_match_dom_pair_auto_alignment_records_effective_geometry(self):
        image = _build_textured_test_image(128, 128)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_alignment_auto.cub",
                right_name="right_alignment_auto.cub",
            )

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                block_width=30,
                block_height=30,
                overlap_x=4,
                overlap_y=4,
                min_valid_pixels=8,
                tile_block_alignment_mode="auto",
            )

        alignment = summary["tile_block_alignment"]
        self.assertEqual(alignment["mode"], "auto")
        self.assertIn("aligned", alignment)
        self.assertEqual(alignment["requested_block_width"], 30)
        self.assertEqual(alignment["requested_block_height"], 30)
        self.assertGreaterEqual(alignment["effective_block_width"], 30)
        self.assertGreaterEqual(alignment["effective_block_height"], 30)
        self.assertIn("left_storage_tile_width", alignment)
        self.assertIn("block_alignment_reason", summary)

    def test_match_dom_pair_reports_tile_cache_diagnostics_when_enabled(self):
        image = _build_textured_test_image(96, 96)

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_tile_test_cube(
                temp_dir,
                image,
                tile_samples=32,
                tile_lines=32,
                name="left_cache_diag.cub",
            )
            right_cube, right_path = make_tile_test_cube(
                temp_dir,
                image,
                tile_samples=32,
                tile_lines=32,
                name="right_cache_diag.cub",
            )
            try:
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=96.0)
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=96.0)
            finally:
                left_cube.close()
                right_cube.close()

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                max_image_dimension=32,
                block_width=48,
                block_height=48,
                overlap_x=0,
                overlap_y=0,
                min_valid_pixels=8,
                use_parallel_cpu=False,
                use_tile_cache=True,
            )

        cache_summary = summary["tile_cache"]
        self.assertTrue(cache_summary["enabled"])
        self.assertIn("left", cache_summary)
        self.assertIn("right", cache_summary)
        self.assertGreaterEqual(cache_summary["left"]["read_window_count"], 1)
        self.assertGreaterEqual(cache_summary["right"]["read_window_count"], 1)
        self.assertTrue(cache_summary["summary_available"])
        self.assertEqual(cache_summary["scope"], "serial")

    def test_match_dom_pair_reports_worker_local_tile_cache_metadata_for_parallel_path(self):
        image = _build_textured_test_image(128, 128)
        synthetic_tile_results = [
            image_match.TileMatchResult(
                stats=image_match.TileMatchStats(
                    local_start_x=0,
                    local_start_y=0,
                    width=64,
                    height=64,
                    left_start_x=0,
                    left_start_y=0,
                    right_start_x=0,
                    right_start_y=0,
                    left_valid_pixel_count=4096,
                    right_valid_pixel_count=4096,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=5,
                    right_feature_count=5,
                    match_count=1,
                    status="matched",
                ),
                left_points=(Keypoint(10.0, 10.0),),
                right_points=(Keypoint(10.5, 10.5),),
            )
        ]

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_parallel_cache_metadata.cub",
                right_name="right_parallel_cache_metadata.cub",
            )
            with mock.patch.object(
                image_match,
                "_run_parallel_tile_match_tasks",
                return_value=synthetic_tile_results,
            ) as parallel_mock:
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    max_image_dimension=64,
                    block_width=64,
                    block_height=64,
                    overlap_x=0,
                    overlap_y=0,
                    min_valid_pixels=16,
                    num_worker_parallel_cpu=2,
                    use_tile_cache=True,
                )

        parallel_mock.assert_called_once()
        self.assertTrue(parallel_mock.call_args.kwargs["use_tile_cache"])
        self.assertTrue(summary["parallel_cpu_used"])
        cache_summary = summary["tile_cache"]
        self.assertTrue(cache_summary["enabled"])
        self.assertFalse(cache_summary["summary_available"])
        self.assertEqual(cache_summary["scope"], "parallel_worker_local")
        self.assertIn("worker-local", cache_summary["reason"])
        self.assertIn("not aggregated", cache_summary["reason"])

    def test_tile_cache_metadata_does_not_claim_none_summaries_available(self):
        cache_summary = image_match._tile_cache_metadata(
            use_tile_cache=True,
            aggregate_summary={
                "enabled": True,
                "left": None,
                "right": None,
            },
        )

        self.assertTrue(cache_summary["enabled"])
        self.assertFalse(cache_summary["summary_available"])
        self.assertNotEqual(cache_summary.get("scope"), "serial")

    def test_match_dom_pair_auto_alignment_preserves_failed_preparation_status(self):
        image = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_tile_test_cube(
                temp_dir,
                image,
                tile_samples=16,
                tile_lines=16,
                name="left_alignment_failed_preparation.cub",
            )
            right_cube, right_path = make_tile_test_cube(
                temp_dir,
                image,
                tile_samples=16,
                tile_lines=16,
                name="right_alignment_failed_preparation.cub",
            )
            try:
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=64.0)
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=64.0)
                right_mapping = right_cube.group("Mapping")
                right_mapping.delete_keyword("CenterLongitude")
                right_mapping.add_keyword(ip.PvlKeyword("CenterLongitude", "10.0"))
                right_cube.put_group(right_mapping)
            finally:
                left_cube.close()
                right_cube.close()

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                min_valid_pixels=8,
                tile_block_alignment_mode="auto",
            )

        self.assertEqual(summary["status"], "skipped_incompatible_projection")
        self.assertIn("CenterLongitude", summary["reason"])
        self.assertEqual(summary["shared_extent_width"], 0)
        self.assertEqual(summary["shared_extent_height"], 0)
        self.assertEqual(summary["tile_count"], 0)
        self.assertEqual(summary["point_count"], 0)

    def test_match_dom_pair_reports_disabled_low_resolution_offset_summary_by_default(self):
        image = _build_textured_test_image(64, 64)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_lowres_default.cub",
                right_name="right_lowres_default.cub",
            )

            _, _, summary = match_dom_pair(
                left_path,
                right_path,
                min_valid_pixels=16,
            )

        low_resolution_summary = summary["low_resolution_offset"]
        self.assertFalse(low_resolution_summary["enabled"])
        self.assertEqual(low_resolution_summary["status"], "disabled")
        self.assertFalse(low_resolution_summary["fallback_offset_zero"])
        self.assertEqual(low_resolution_summary["delta_x_projected"], 0.0)
        self.assertEqual(low_resolution_summary["delta_y_projected"], 0.0)
        self.assertEqual(low_resolution_summary["retained_match_count"], 0)

    def test_match_dom_pair_treats_zero_as_invalid_for_8bit_images(self):
        image = np.zeros((48, 48), dtype=np.float64)
        image[8:40, 8:40] = np.tile(np.arange(1.0, 33.0, dtype=np.float64), (32, 1))

        with temporary_directory() as temp_dir:
            byte_left_path, byte_right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_byte_zero_invalid.cub",
                right_name="right_byte_zero_invalid.cub",
            )
            real_left_path, real_right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.Real,
                left_name="left_real_zero_valid.cub",
                right_name="right_real_zero_valid.cub",
            )

            _, _, byte_summary = match_dom_pair(
                byte_left_path,
                byte_right_path,
                min_valid_pixels=16,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=0,
            )
            _, _, real_summary = match_dom_pair(
                real_left_path,
                real_right_path,
                min_valid_pixels=16,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=0,
            )

        self.assertLess(byte_summary["tiles"][0]["left_valid_pixel_ratio"], 1.0)
        self.assertAlmostEqual(real_summary["tiles"][0]["left_valid_pixel_ratio"], 1.0, places=6)

    def test_match_dom_pair_on_real_dom_cubes_returns_in_bounds_keypoints(self):
        left_key_file, right_key_file, summary = match_dom_pair(
            FIXTURE_DOM_LEFT,
            FIXTURE_DOM_RIGHT,
            min_valid_pixels=16,
            ratio_test=0.85,
            invalid_pixel_radius=0,
        )

        self.assertEqual(left_key_file.image_width, 50)
        self.assertEqual(left_key_file.image_height, 50)
        self.assertEqual(right_key_file.image_width, 50)
        self.assertEqual(right_key_file.image_height, 50)
        self.assertEqual(len(left_key_file.points), len(right_key_file.points))
        self.assertGreater(summary["point_count"], 0)
        self.assertTrue(all(1.0 <= point.sample <= 50.0 for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.line <= 50.0 for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.sample <= 50.0 for point in right_key_file.points))
        self.assertTrue(all(1.0 <= point.line <= 50.0 for point in right_key_file.points))

    def test_match_dom_pair_supports_configurable_real_lro_dom_pair_when_available(self):
        real_left_dom, real_right_dom = _configured_real_lro_dom_pair()
        if not real_left_dom.exists() or not real_right_dom.exists():
            self.skipTest(
                "Real LRO DOM pair is unavailable. "
                f"Configure {REAL_LRO_DOM_LEFT_ENV} and {REAL_LRO_DOM_RIGHT_ENV} if needed."
            )

        left_key_file, right_key_file, summary = match_dom_pair(
            real_left_dom,
            real_right_dom,
            min_valid_pixels=16,
            ratio_test=0.85,
        )

        self.assertEqual(len(left_key_file.points), len(right_key_file.points))
        self.assertGreater(summary["point_count"], 0)
        self.assertGreater(left_key_file.image_width, 0)
        self.assertGreater(left_key_file.image_height, 0)
        self.assertGreater(right_key_file.image_width, 0)
        self.assertGreater(right_key_file.image_height, 0)
        self.assertTrue(all(1.0 <= point.sample <= left_key_file.image_width for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.line <= left_key_file.image_height for point in left_key_file.points))
        self.assertTrue(all(1.0 <= point.sample <= right_key_file.image_width for point in right_key_file.points))
        self.assertTrue(all(1.0 <= point.line <= right_key_file.image_height for point in right_key_file.points))

    def test_write_stereo_pair_match_visualization_from_key_files_writes_default_png(self):
        width = 24
        height = 24
        image = _build_textured_test_image(width, height)

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="A.cub", samples=width, lines=height, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="B.cub", samples=width, lines=height, bands=1)
            try:
                _write_array_to_cube(left_cube, image)
                _write_array_to_cube(right_cube, image)
            finally:
                left_cube.close()
                right_cube.close()

            left_key_path = temp_dir / "left.key"
            right_key_path = temp_dir / "right.key"
            write_key_file(left_key_path, KeypointFile(width, height, (Keypoint(5.0, 5.0), Keypoint(10.0, 12.0))))
            write_key_file(right_key_path, KeypointFile(width, height, (Keypoint(6.0, 6.0), Keypoint(11.0, 13.0))))

            result = write_stereo_pair_match_visualization_from_key_files(
                left_path,
                right_path,
                left_key_path,
                right_key_path,
                output_directory=temp_dir,
                timestamp=datetime(2026, 4, 18, 18, 44, 32),
                scale_factor=3.0,
                highlight_match_indices=[1],
            )
            output_exists = Path(result["output_path"]).exists()

        self.assertTrue(result["output_path"].endswith("A__B__20260418T184432.png"))
        self.assertEqual(result["point_count"], 2)
        self.assertEqual(result["highlighted_match_count"], 1)
        self.assertTrue(output_exists)

    def test_write_match_visualization_auto_uses_reduced_mode_for_large_images(self):
        left_key_file = KeypointFile(4000, 3000, (Keypoint(100.0, 100.0), Keypoint(120.0, 120.0)))
        right_key_file = KeypointFile(4000, 3000, (Keypoint(105.0, 105.0), Keypoint(125.0, 125.0)))
        read_windows: list[object | None] = []
        captured_keypoints: dict[str, list[tuple[float, float]]] = {}
        reduced_paths: list[str] = []

        def fake_read(cube_path, *, window=None, **kwargs):
            read_windows.append(window)
            reduced_paths.append(str(cube_path))
            return np.full((64, 64), 128, dtype=np.uint8)

        def fake_create(source, output, *, level, **kwargs):
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text("preview", encoding="utf-8")
            return Path(output)

        def fake_draw_matches(
            left_image,
            left_keypoints,
            right_image,
            right_keypoints,
            matches,
            out_image,
            **kwargs,
        ):
            captured_keypoints["left"] = [keypoint.pt for keypoint in left_keypoints]
            captured_keypoints["right"] = [keypoint.pt for keypoint in right_keypoints]
            return np.zeros((10, 10, 3), dtype=np.uint8)

        with temporary_directory() as temp_dir, mock.patch.object(
            match_visualization_module,
            "_cube_dimensions",
            return_value=(4000, 3000),
        ) as cube_dimensions_mock, mock.patch.object(
            match_visualization_module,
            "create_low_resolution_dom",
            side_effect=fake_create,
        ), mock.patch.object(
            match_visualization_module,
            "_read_cube_as_stretched_byte",
            side_effect=fake_read,
        ), mock.patch.object(
            match_visualization_module.cv2,
            "drawMatches",
            side_effect=fake_draw_matches,
        ):
            result = match_visualization_module.write_stereo_pair_match_visualization(
                "left.cub",
                "right.cub",
                left_key_file,
                right_key_file,
                output_path=temp_dir / "viz.png",
                visualization_mode="auto",
                max_preview_pixels=10_000,
                preview_crop_margin_pixels=10,
                visualization_target_long_edge=1024,
                preview_cache_dir=temp_dir / "preview_cache",
            )

        self.assertEqual(result["visualization_mode_requested"], "auto")
        self.assertEqual(result["visualization_mode_used"], "reduced")
        self.assertEqual(result["preview_level"], 2)
        self.assertIsNone(result["crop_window"])
        self.assertEqual(cube_dimensions_mock.call_count, 2)
        self.assertEqual(read_windows, [None, None])
        self.assertTrue(all("preview_cache" in path for path in reduced_paths))
        self.assertAlmostEqual(captured_keypoints["left"][0][0], (24.75) / 3.0, places=4)
        self.assertAlmostEqual(captured_keypoints["left"][0][1], (24.75) / 3.0, places=4)
        self.assertAlmostEqual(captured_keypoints["right"][0][0], (26.0) / 3.0, places=4)
        self.assertAlmostEqual(captured_keypoints["right"][0][1], (26.0) / 3.0, places=4)

    def test_write_match_visualization_cropped_requires_keypoints(self):
        empty_left = KeypointFile(4000, 3000, ())
        empty_right = KeypointFile(4000, 3000, ())

        with temporary_directory() as temp_dir, mock.patch.object(
            match_visualization_module,
            "_read_cube_as_stretched_byte",
        ) as read_mock:
            with self.assertRaisesRegex(ValueError, "requires at least one keypoint"):
                match_visualization_module.write_stereo_pair_match_visualization(
                    "left.cub",
                    "right.cub",
                    empty_left,
                    empty_right,
                    output_path=temp_dir / "viz.png",
                    visualization_mode="cropped",
                )

        read_mock.assert_not_called()

    def test_write_match_visualization_auto_large_empty_keypoints_uses_reduced_without_full_read(self):
        empty_left = KeypointFile(4000, 3000, ())
        empty_right = KeypointFile(4000, 3000, ())
        read_windows: list[object | None] = []

        def fake_create(source, output, *, level, **kwargs):
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text("preview", encoding="utf-8")
            return Path(output)

        def fake_read(cube_path, *, window=None, **kwargs):
            read_windows.append(window)
            return np.full((32, 32), 128, dtype=np.uint8)

        def fake_draw_matches(*args, **kwargs):
            return np.zeros((10, 10, 3), dtype=np.uint8)

        with temporary_directory() as temp_dir, mock.patch.object(
            match_visualization_module,
            "_cube_dimensions",
            return_value=(4000, 3000),
        ) as cube_dimensions_mock, mock.patch.object(
            match_visualization_module,
            "create_low_resolution_dom",
            side_effect=fake_create,
        ), mock.patch.object(
            match_visualization_module,
            "_read_cube_as_stretched_byte",
            side_effect=fake_read,
        ), mock.patch.object(
            match_visualization_module.cv2,
            "drawMatches",
            side_effect=fake_draw_matches,
        ), mock.patch.object(
            match_visualization_module.cv2,
            "imwrite",
            return_value=True,
        ):
            result = match_visualization_module.write_stereo_pair_match_visualization(
                "left.cub",
                "right.cub",
                empty_left,
                empty_right,
                output_path=temp_dir / "viz.png",
                visualization_mode="auto",
                max_preview_pixels=10_000,
                visualization_target_long_edge=1024,
                preview_cache_dir=temp_dir / "preview_cache",
            )

        self.assertEqual(cube_dimensions_mock.call_count, 2)
        self.assertEqual(result["visualization_mode_used"], "reduced")
        self.assertEqual(result["point_count"], 0)
        self.assertEqual(read_windows, [None, None])

    def test_write_match_visualization_defaults_to_auto_mode_for_large_images(self):
        left_key_file = KeypointFile(4000, 3000, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4000, 3000, (Keypoint(105.0, 105.0),))
        read_windows: list[object | None] = []

        def fake_read(cube_path, *, window=None, **kwargs):
            read_windows.append(window)
            return np.full((32, 32), 128, dtype=np.uint8)

        def fake_create(source, output, *, level, **kwargs):
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text("preview", encoding="utf-8")
            return Path(output)

        def fake_draw_matches(*args, **kwargs):
            return np.zeros((10, 10, 3), dtype=np.uint8)

        with temporary_directory() as temp_dir, mock.patch.object(
            match_visualization_module,
            "_cube_dimensions",
            return_value=(4000, 3000),
        ) as cube_dimensions_mock, mock.patch.object(
            match_visualization_module,
            "create_low_resolution_dom",
            side_effect=fake_create,
        ), mock.patch.object(
            match_visualization_module,
            "_read_cube_as_stretched_byte",
            side_effect=fake_read,
        ), mock.patch.object(
            match_visualization_module.cv2,
            "drawMatches",
            side_effect=fake_draw_matches,
        ), mock.patch.object(
            match_visualization_module.cv2,
            "imwrite",
            return_value=True,
        ):
            result = match_visualization_module.write_stereo_pair_match_visualization(
                "left.cub",
                "right.cub",
                left_key_file,
                right_key_file,
                output_path=temp_dir / "viz.png",
            )

        self.assertEqual(result["visualization_mode_requested"], "auto")
        self.assertEqual(result["visualization_mode_used"], "reduced")
        self.assertEqual(result["preview_level"], 1)
        self.assertEqual(cube_dimensions_mock.call_count, 2)
        self.assertEqual(read_windows, [None, None])

    def test_write_match_visualization_explicit_full_mode_skips_dimension_probe(self):
        left_key_file = KeypointFile(4000, 3000, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4000, 3000, (Keypoint(105.0, 105.0),))
        read_windows: list[object | None] = []

        def fake_read(cube_path, *, window=None, **kwargs):
            read_windows.append(window)
            return np.full((32, 32), 128, dtype=np.uint8)

        def fake_draw_matches(*args, **kwargs):
            return np.zeros((10, 10, 3), dtype=np.uint8)

        with temporary_directory() as temp_dir, mock.patch.object(
            match_visualization_module,
            "_cube_dimensions",
            return_value=(4000, 3000),
        ) as cube_dimensions_mock, mock.patch.object(
            match_visualization_module,
            "_read_cube_as_stretched_byte",
            side_effect=fake_read,
        ), mock.patch.object(
            match_visualization_module.cv2,
            "drawMatches",
            side_effect=fake_draw_matches,
        ), mock.patch.object(
            match_visualization_module.cv2,
            "imwrite",
            return_value=True,
        ):
            result = match_visualization_module.write_stereo_pair_match_visualization(
                "left.cub",
                "right.cub",
                left_key_file,
                right_key_file,
                output_path=temp_dir / "viz.png",
                visualization_mode="full",
            )

        self.assertEqual(result["visualization_mode_requested"], "full")
        self.assertEqual(result["visualization_mode_used"], "full")
        cube_dimensions_mock.assert_not_called()
        self.assertEqual(read_windows, [None, None])

    def test_preview_cache_path_includes_source_hash(self):
        cache_dir = Path("preview_cache")
        left_path = "/a/left.cub"
        right_path = "/b/left.cub"

        left_cache = match_visualization_module._preview_cache_path(cache_dir, left_path, level=2)
        right_cache = match_visualization_module._preview_cache_path(cache_dir, right_path, level=2)

        left_digest = hashlib.sha256(match_visualization_module._preview_cache_hash_key(left_path).encode("utf-8")).hexdigest()
        right_digest = hashlib.sha256(match_visualization_module._preview_cache_hash_key(right_path).encode("utf-8")).hexdigest()

        self.assertNotEqual(left_cache, right_cache)
        self.assertEqual(left_cache.name, f"left__{left_digest}.cub")
        self.assertEqual(right_cache.name, f"left__{right_digest}.cub")

    def test_preview_cache_hash_key_normalizes_paths(self):
        source_path = Path("preview/../left.cub")
        expected = Path(source_path).expanduser().resolve(strict=False).as_posix()
        if os.name == "nt":
            expected = expected.casefold()

        actual = match_visualization_module._preview_cache_hash_key(source_path)

        self.assertEqual(actual, expected)

    def test_write_match_visualization_reduced_mode_rejects_preview_cache_disabled(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(120.0, 120.0),))

        with temporary_directory() as temp_dir, self.assertRaises(ValueError):
            match_visualization_module.write_stereo_pair_match_visualization(
                "left.cub",
                "right.cub",
                left_key_file,
                right_key_file,
                output_path=temp_dir / "viz.png",
                visualization_mode="reduced",
                preview_cache_source="disabled",
            )

    def test_write_match_visualization_matching_cache_requires_matching_preview_pair(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(120.0, 120.0),))

        with temporary_directory() as temp_dir, self.assertRaises(ValueError):
            match_visualization_module.write_stereo_pair_match_visualization(
                "left.cub",
                "right.cub",
                left_key_file,
                right_key_file,
                output_path=temp_dir / "viz.png",
                visualization_mode="reduced",
                preview_cache_source="matching_cache",
            )

    def test_write_match_visualization_reduced_mode_reuses_matching_cache(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(120.0, 120.0),))
        read_paths: list[str] = []

        def fake_read(cube_path, *, window=None, **kwargs):
            read_paths.append(str(cube_path))
            return np.full((64, 64), 128, dtype=np.uint8)

        def fake_draw_matches(*args, **kwargs):
            return np.zeros((10, 10, 3), dtype=np.uint8)

        with temporary_directory() as temp_dir, mock.patch.object(
            match_visualization_module,
            "_cube_dimensions",
            return_value=(1024, 1024),
        ), mock.patch.object(
            match_visualization_module,
            "_read_cube_as_stretched_byte",
            side_effect=fake_read,
        ), mock.patch.object(
            match_visualization_module.cv2,
            "drawMatches",
            side_effect=fake_draw_matches,
        ), mock.patch.object(
            match_visualization_module.cv2,
            "imwrite",
            return_value=True,
        ):
            result = match_visualization_module.write_stereo_pair_match_visualization(
                "left.cub",
                "right.cub",
                left_key_file,
                right_key_file,
                output_path=temp_dir / "viz.png",
                visualization_mode="reduced",
                preview_cache_source="matching_cache",
                left_matching_preview_dom=temp_dir / "matching_left_level2.cub",
                right_matching_preview_dom=temp_dir / "matching_right_level2.cub",
                matching_preview_level=2,
                preview_level=2,
            )

        self.assertEqual(result["visualization_mode_used"], "reduced")
        self.assertEqual(result["preview_cache_source"], "matching_cache")
        self.assertTrue(result["preview_cache_hit"])
        self.assertEqual(read_paths, [str(temp_dir / "matching_left_level2.cub"), str(temp_dir / "matching_right_level2.cub")])

    def test_write_match_visualization_reduced_mode_generates_preview_cache(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(120.0, 120.0),))
        generated: list[tuple[str, str, int]] = []

        def fake_create(source, output, *, level, **kwargs):
            generated.append((str(source), str(output), level))
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text("preview", encoding="utf-8")
            return Path(output)

        def fake_draw_matches(*args, **kwargs):
            return np.zeros((10, 10, 3), dtype=np.uint8)

        with temporary_directory() as temp_dir, mock.patch.object(
            match_visualization_module,
            "_cube_dimensions",
            return_value=(4096, 4096),
        ), mock.patch.object(
            match_visualization_module,
            "create_low_resolution_dom",
            side_effect=fake_create,
        ), mock.patch.object(
            match_visualization_module,
            "_read_cube_as_stretched_byte",
            return_value=np.full((64, 64), 128, dtype=np.uint8),
        ), mock.patch.object(
            match_visualization_module.cv2,
            "drawMatches",
            side_effect=fake_draw_matches,
        ), mock.patch.object(
            match_visualization_module.cv2,
            "imwrite",
            return_value=True,
        ):
            result = match_visualization_module.write_stereo_pair_match_visualization(
                "left.cub",
                "right.cub",
                left_key_file,
                right_key_file,
                output_path=temp_dir / "viz.png",
                visualization_mode="reduced",
                preview_cache_dir=temp_dir / "preview_cache",
                visualization_target_long_edge=1024,
            )
            for source, output, level in generated:
                metadata_path = match_visualization_module._preview_cache_metadata_path(output)
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                self.assertEqual(metadata["source_hash_key"], match_visualization_module._preview_cache_hash_key(source))
                self.assertEqual(metadata["level"], level)
                self.assertEqual(
                    metadata["source_fingerprint"],
                    match_visualization_module._preview_cache_source_fingerprint(source),
                )

        self.assertEqual(result["visualization_mode_used"], "reduced")
        self.assertEqual(result["preview_level"], 2)
        self.assertFalse(result["preview_cache_hit"])
        self.assertFalse(result["preview_cache_hit_left"])
        self.assertFalse(result["preview_cache_hit_right"])
        self.assertIsNone(result["preview_cache_validation_left"])
        self.assertIsNone(result["preview_cache_validation_right"])
        self.assertEqual(result["preview_cache_source"], "visualization_cache")
        self.assertEqual(len(generated), 2)

    def test_write_match_visualization_reduced_mode_reuses_preview_cache(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(120.0, 120.0),))
        read_windows: list[object | None] = []

        def fake_read(cube_path, *, window=None, **kwargs):
            read_windows.append(window)
            return np.full((64, 64), 128, dtype=np.uint8)

        with temporary_directory() as temp_dir:
            preview_root = temp_dir / "preview_cache"
            left_preview = match_visualization_module._preview_cache_path(
                preview_root,
                "left.cub",
                level=2,
            )
            right_preview = match_visualization_module._preview_cache_path(
                preview_root,
                "right.cub",
                level=2,
            )
            left_preview.parent.mkdir(parents=True, exist_ok=True)
            right_preview.parent.mkdir(parents=True, exist_ok=True)
            left_preview.write_text("cached", encoding="utf-8")
            right_preview.write_text("cached", encoding="utf-8")
            _write_preview_cache_metadata(
                left_preview,
                source_hash_key=match_visualization_module._preview_cache_hash_key("left.cub"),
                level=2,
                source_path="left.cub",
            )
            _write_preview_cache_metadata(
                right_preview,
                source_hash_key=match_visualization_module._preview_cache_hash_key("right.cub"),
                level=2,
                source_path="right.cub",
            )

            with mock.patch.object(
                match_visualization_module,
                "_cube_dimensions",
                return_value=(4096, 4096),
            ) as cube_dimensions_mock, mock.patch.object(
                match_visualization_module,
                "create_low_resolution_dom",
            ) as create_mock, mock.patch.object(
                match_visualization_module,
                "_read_cube_as_stretched_byte",
                side_effect=fake_read,
            ), mock.patch.object(
                match_visualization_module.cv2,
                "drawMatches",
                return_value=np.zeros((10, 10, 3), dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "imwrite",
                return_value=True,
            ):
                result = match_visualization_module.write_stereo_pair_match_visualization(
                    "left.cub",
                    "right.cub",
                    left_key_file,
                    right_key_file,
                    output_path=temp_dir / "viz.png",
                    visualization_mode="reduced",
                    preview_cache_dir=preview_root,
                    preview_force_regenerate=False,
                    visualization_target_long_edge=1024,
                )

        create_mock.assert_not_called()
        cube_dimensions_mock.assert_any_call(left_preview)
        cube_dimensions_mock.assert_any_call(right_preview)
        self.assertTrue(result["preview_cache_hit"])
        self.assertTrue(result["preview_cache_hit_left"])
        self.assertTrue(result["preview_cache_hit_right"])
        self.assertIsNone(result["preview_cache_validation_left"])
        self.assertIsNone(result["preview_cache_validation_right"])
        self.assertEqual(result["preview_cache_source"], "visualization_cache")
        self.assertEqual(result["left_preview_path"], str(left_preview))
        self.assertEqual(result["right_preview_path"], str(right_preview))
        self.assertEqual(read_windows, [None, None])

    def test_write_match_visualization_reduced_mode_regenerates_invalid_cache(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(120.0, 120.0),))
        generated: list[Path] = []

        def fake_create(source, output, *, level, **kwargs):
            generated.append(Path(output))
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text("preview", encoding="utf-8")
            return Path(output)

        with temporary_directory() as temp_dir:
            preview_root = temp_dir / "preview_cache"
            for name in ("left.cub", "right.cub"):
                preview_path = match_visualization_module._preview_cache_path(preview_root, name, level=2)
                preview_path.parent.mkdir(parents=True, exist_ok=True)
                preview_path.write_text("cached", encoding="utf-8")

            with mock.patch.object(
                match_visualization_module,
                "_cube_dimensions",
                return_value=(4096, 4096),
            ), mock.patch.object(
                match_visualization_module,
                "create_low_resolution_dom",
                side_effect=fake_create,
            ), mock.patch.object(
                match_visualization_module,
                "_read_cube_as_stretched_byte",
                return_value=np.full((64, 64), 128, dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "drawMatches",
                return_value=np.zeros((10, 10, 3), dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "imwrite",
                return_value=True,
            ):
                result = match_visualization_module.write_stereo_pair_match_visualization(
                    "left.cub",
                    "right.cub",
                    left_key_file,
                    right_key_file,
                    output_path=temp_dir / "viz.png",
                    visualization_mode="reduced",
                    preview_cache_dir=preview_root,
                    preview_level=2,
                    visualization_target_long_edge=1024,
                )

        self.assertFalse(result["preview_cache_hit"])
        self.assertFalse(result["preview_cache_hit_left"])
        self.assertFalse(result["preview_cache_hit_right"])
        self.assertEqual(result["preview_cache_validation_left"], "metadata_missing")
        self.assertEqual(result["preview_cache_validation_right"], "metadata_missing")
        self.assertEqual(len(generated), 2)

    def test_write_match_visualization_reduced_mode_regenerates_corrupt_metadata(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(120.0, 120.0),))
        generated: list[Path] = []

        def fake_create(source, output, *, level, **kwargs):
            generated.append(Path(output))
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text("preview", encoding="utf-8")
            return Path(output)

        with temporary_directory() as temp_dir:
            preview_root = temp_dir / "preview_cache"
            for name in ("left.cub", "right.cub"):
                preview_path = match_visualization_module._preview_cache_path(preview_root, name, level=2)
                preview_path.parent.mkdir(parents=True, exist_ok=True)
                preview_path.write_text("cached", encoding="utf-8")
                metadata_path = match_visualization_module._preview_cache_metadata_path(preview_path)
                metadata_path.write_text("not-json", encoding="utf-8")

            with mock.patch.object(
                match_visualization_module,
                "_cube_dimensions",
                return_value=(4096, 4096),
            ), mock.patch.object(
                match_visualization_module,
                "create_low_resolution_dom",
                side_effect=fake_create,
            ), mock.patch.object(
                match_visualization_module,
                "_read_cube_as_stretched_byte",
                return_value=np.full((64, 64), 128, dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "drawMatches",
                return_value=np.zeros((10, 10, 3), dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "imwrite",
                return_value=True,
            ):
                result = match_visualization_module.write_stereo_pair_match_visualization(
                    "left.cub",
                    "right.cub",
                    left_key_file,
                    right_key_file,
                    output_path=temp_dir / "viz.png",
                    visualization_mode="reduced",
                    preview_cache_dir=preview_root,
                    preview_level=2,
                    visualization_target_long_edge=1024,
                )

        self.assertFalse(result["preview_cache_hit"])
        self.assertFalse(result["preview_cache_hit_left"])
        self.assertFalse(result["preview_cache_hit_right"])
        self.assertEqual(result["preview_cache_validation_left"], "metadata_corrupt")
        self.assertEqual(result["preview_cache_validation_right"], "metadata_corrupt")
        self.assertEqual(len(generated), 2)

    def test_write_match_visualization_reduced_mode_regenerates_non_object_metadata_cache(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(120.0, 120.0),))
        generated: list[Path] = []

        def fake_create(source, output, *, level, **kwargs):
            generated.append(Path(output))
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text("preview", encoding="utf-8")
            return Path(output)

        with temporary_directory() as temp_dir:
            preview_root = temp_dir / "preview_cache"
            for name in ("left.cub", "right.cub"):
                preview_path = match_visualization_module._preview_cache_path(preview_root, name, level=2)
                preview_path.parent.mkdir(parents=True, exist_ok=True)
                preview_path.write_text("cached", encoding="utf-8")
                metadata_path = match_visualization_module._preview_cache_metadata_path(preview_path)
                metadata_path.write_text("[]", encoding="utf-8")

            with mock.patch.object(
                match_visualization_module,
                "_cube_dimensions",
                return_value=(4096, 4096),
            ), mock.patch.object(
                match_visualization_module,
                "create_low_resolution_dom",
                side_effect=fake_create,
            ), mock.patch.object(
                match_visualization_module,
                "_read_cube_as_stretched_byte",
                return_value=np.full((64, 64), 128, dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "drawMatches",
                return_value=np.zeros((10, 10, 3), dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "imwrite",
                return_value=True,
            ):
                result = match_visualization_module.write_stereo_pair_match_visualization(
                    "left.cub",
                    "right.cub",
                    left_key_file,
                    right_key_file,
                    output_path=temp_dir / "viz.png",
                    visualization_mode="reduced",
                    preview_cache_dir=preview_root,
                    preview_level=2,
                    visualization_target_long_edge=1024,
                )

        self.assertFalse(result["preview_cache_hit"])
        self.assertFalse(result["preview_cache_hit_left"])
        self.assertFalse(result["preview_cache_hit_right"])
        self.assertEqual(result["preview_cache_validation_left"], "metadata_corrupt")
        self.assertEqual(result["preview_cache_validation_right"], "metadata_corrupt")
        self.assertEqual(len(generated), 2)

    def test_write_match_visualization_reduced_mode_regenerates_cache_on_cube_validation_failure(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(120.0, 120.0),))
        generated: list[Path] = []

        def fake_create(source, output, *, level, **kwargs):
            generated.append(Path(output))
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text("preview", encoding="utf-8")
            return Path(output)

        with temporary_directory() as temp_dir:
            preview_root = temp_dir / "preview_cache"
            left_preview = match_visualization_module._preview_cache_path(preview_root, "left.cub", level=2)
            right_preview = match_visualization_module._preview_cache_path(preview_root, "right.cub", level=2)
            left_preview.parent.mkdir(parents=True, exist_ok=True)
            right_preview.parent.mkdir(parents=True, exist_ok=True)
            left_preview.write_text("cached", encoding="utf-8")
            right_preview.write_text("cached", encoding="utf-8")
            _write_preview_cache_metadata(
                left_preview,
                source_hash_key=match_visualization_module._preview_cache_hash_key("left.cub"),
                level=2,
                source_path="left.cub",
            )
            _write_preview_cache_metadata(
                right_preview,
                source_hash_key=match_visualization_module._preview_cache_hash_key("right.cub"),
                level=2,
                source_path="right.cub",
            )

            def fake_dimensions(path):
                if Path(path) in {left_preview, right_preview}:
                    raise RuntimeError("preview validation failed")
                return (4096, 4096)

            with mock.patch.object(
                match_visualization_module,
                "_cube_dimensions",
                side_effect=fake_dimensions,
            ), mock.patch.object(
                match_visualization_module,
                "create_low_resolution_dom",
                side_effect=fake_create,
            ), mock.patch.object(
                match_visualization_module,
                "_read_cube_as_stretched_byte",
                return_value=np.full((64, 64), 128, dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "drawMatches",
                return_value=np.zeros((10, 10, 3), dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "imwrite",
                return_value=True,
            ):
                result = match_visualization_module.write_stereo_pair_match_visualization(
                    "left.cub",
                    "right.cub",
                    left_key_file,
                    right_key_file,
                    output_path=temp_dir / "viz.png",
                    visualization_mode="reduced",
                    preview_cache_dir=preview_root,
                    preview_level=2,
                    visualization_target_long_edge=1024,
                )

        self.assertFalse(result["preview_cache_hit"])
        self.assertFalse(result["preview_cache_hit_left"])
        self.assertFalse(result["preview_cache_hit_right"])
        self.assertEqual(result["preview_cache_validation_left"], "cube_validation_failed")
        self.assertEqual(result["preview_cache_validation_right"], "cube_validation_failed")
        self.assertEqual(result["preview_cache_source"], "visualization_cache")
        self.assertEqual(len(generated), 2)

    def test_write_match_visualization_reduced_mode_reports_regeneration_failure_after_cache_validation_failure(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(120.0, 120.0),))
        regeneration_error = RuntimeError("reduce failed")

        with temporary_directory() as temp_dir:
            preview_root = temp_dir / "preview_cache"
            left_preview = match_visualization_module._preview_cache_path(preview_root, "left.cub", level=2)
            right_preview = match_visualization_module._preview_cache_path(preview_root, "right.cub", level=2)
            left_preview.parent.mkdir(parents=True, exist_ok=True)
            right_preview.parent.mkdir(parents=True, exist_ok=True)
            left_preview.write_text("cached", encoding="utf-8")
            right_preview.write_text("cached", encoding="utf-8")
            _write_preview_cache_metadata(
                left_preview,
                source_hash_key=match_visualization_module._preview_cache_hash_key("left.cub"),
                level=2,
                source_path="left.cub",
            )
            _write_preview_cache_metadata(
                right_preview,
                source_hash_key=match_visualization_module._preview_cache_hash_key("right.cub"),
                level=2,
                source_path="right.cub",
            )

            def fake_dimensions(path):
                if Path(path) in {left_preview, right_preview}:
                    raise RuntimeError("preview validation failed")
                return (4096, 4096)

            with mock.patch.object(
                match_visualization_module,
                "_cube_dimensions",
                side_effect=fake_dimensions,
            ), mock.patch.object(
                match_visualization_module,
                "create_low_resolution_dom",
                side_effect=regeneration_error,
            ):
                with self.assertRaises(RuntimeError) as context:
                    match_visualization_module.write_stereo_pair_match_visualization(
                        "left.cub",
                        "right.cub",
                        left_key_file,
                        right_key_file,
                        output_path=temp_dir / "viz.png",
                        visualization_mode="reduced",
                        preview_cache_dir=preview_root,
                        preview_level=2,
                        visualization_target_long_edge=1024,
                    )

        message = str(context.exception)
        self.assertIn("cube_validation_failed", message)
        self.assertIn("regeneration failed", message)
        self.assertIn("left.cub", message)
        self.assertIn("level 2", message)
        self.assertIs(context.exception.__cause__, regeneration_error)

    def test_write_match_visualization_reduced_mode_regenerates_mismatched_metadata(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(120.0, 120.0),))
        generated: list[Path] = []

        def fake_create(source, output, *, level, **kwargs):
            generated.append(Path(output))
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text("preview", encoding="utf-8")
            return Path(output)

        with temporary_directory() as temp_dir:
            preview_root = temp_dir / "preview_cache"
            for name in ("left.cub", "right.cub"):
                preview_path = match_visualization_module._preview_cache_path(preview_root, name, level=2)
                preview_path.parent.mkdir(parents=True, exist_ok=True)
                preview_path.write_text("cached", encoding="utf-8")
                _write_preview_cache_metadata(
                    preview_path,
                    source_hash_key="invalid-hash",
                    level=1,
                    source_path="other.cub",
                )

            with mock.patch.object(
                match_visualization_module,
                "_cube_dimensions",
                return_value=(4096, 4096),
            ), mock.patch.object(
                match_visualization_module,
                "create_low_resolution_dom",
                side_effect=fake_create,
            ), mock.patch.object(
                match_visualization_module,
                "_read_cube_as_stretched_byte",
                return_value=np.full((64, 64), 128, dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "drawMatches",
                return_value=np.zeros((10, 10, 3), dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "imwrite",
                return_value=True,
            ):
                result = match_visualization_module.write_stereo_pair_match_visualization(
                    "left.cub",
                    "right.cub",
                    left_key_file,
                    right_key_file,
                    output_path=temp_dir / "viz.png",
                    visualization_mode="reduced",
                    preview_cache_dir=preview_root,
                    preview_level=2,
                    visualization_target_long_edge=1024,
                )

        self.assertFalse(result["preview_cache_hit"])
        self.assertEqual(result["preview_cache_validation_left"], "metadata_mismatch")
        self.assertEqual(result["preview_cache_validation_right"], "metadata_mismatch")
        self.assertEqual(len(generated), 2)

    def test_write_match_visualization_reduced_mode_regenerates_on_source_fingerprint_change(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(120.0, 120.0),))
        generated: list[Path] = []

        def fake_create(source, output, *, level, **kwargs):
            generated.append(Path(output))
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text("preview", encoding="utf-8")
            return Path(output)

        with temporary_directory() as temp_dir:
            left_source = temp_dir / "left.cub"
            right_source = temp_dir / "right.cub"
            left_source.write_text("left", encoding="utf-8")
            right_source.write_text("right", encoding="utf-8")
            preview_root = temp_dir / "preview_cache"
            left_preview = match_visualization_module._preview_cache_path(preview_root, left_source, level=2)
            right_preview = match_visualization_module._preview_cache_path(preview_root, right_source, level=2)
            left_preview.parent.mkdir(parents=True, exist_ok=True)
            right_preview.parent.mkdir(parents=True, exist_ok=True)
            left_preview.write_text("cached", encoding="utf-8")
            right_preview.write_text("cached", encoding="utf-8")
            left_fingerprint = match_visualization_module._preview_cache_source_fingerprint(left_source)
            right_fingerprint = match_visualization_module._preview_cache_source_fingerprint(right_source)
            stale_fingerprint = (
                {"size_bytes": 0, "mtime_ns": 0}
                if left_fingerprint is None
                else {**left_fingerprint, "size_bytes": left_fingerprint["size_bytes"] + 1}
            )
            _write_preview_cache_metadata(
                left_preview,
                source_hash_key=match_visualization_module._preview_cache_hash_key(left_source),
                level=2,
                source_path=left_source,
                source_fingerprint=stale_fingerprint,
            )
            _write_preview_cache_metadata(
                right_preview,
                source_hash_key=match_visualization_module._preview_cache_hash_key(right_source),
                level=2,
                source_path=right_source,
                source_fingerprint=right_fingerprint,
            )

            with mock.patch.object(
                match_visualization_module,
                "_cube_dimensions",
                return_value=(4096, 4096),
            ), mock.patch.object(
                match_visualization_module,
                "create_low_resolution_dom",
                side_effect=fake_create,
            ), mock.patch.object(
                match_visualization_module,
                "_read_cube_as_stretched_byte",
                return_value=np.full((64, 64), 128, dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "drawMatches",
                return_value=np.zeros((10, 10, 3), dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "imwrite",
                return_value=True,
            ):
                result = match_visualization_module.write_stereo_pair_match_visualization(
                    left_source,
                    right_source,
                    left_key_file,
                    right_key_file,
                    output_path=temp_dir / "viz.png",
                    visualization_mode="reduced",
                    preview_cache_dir=preview_root,
                    preview_level=2,
                    visualization_target_long_edge=1024,
                )

        self.assertFalse(result["preview_cache_hit"])
        self.assertFalse(result["preview_cache_hit_left"])
        self.assertTrue(result["preview_cache_hit_right"])
        self.assertEqual(result["preview_cache_validation_left"], "source_changed")
        self.assertIsNone(result["preview_cache_validation_right"])
        self.assertEqual(len(generated), 1)

    def test_write_match_visualization_reduced_mode_partial_cache_hit(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(120.0, 120.0),))

        def fake_create(source, output, *, level, **kwargs):
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text("preview", encoding="utf-8")
            return Path(output)

        with temporary_directory() as temp_dir:
            preview_root = temp_dir / "preview_cache"
            left_preview = match_visualization_module._preview_cache_path(
                preview_root,
                "left.cub",
                level=2,
            )
            left_preview.parent.mkdir(parents=True, exist_ok=True)
            left_preview.write_text("cached", encoding="utf-8")
            _write_preview_cache_metadata(
                left_preview,
                source_hash_key=match_visualization_module._preview_cache_hash_key("left.cub"),
                level=2,
                source_path="left.cub",
            )
            right_preview = match_visualization_module._preview_cache_path(
                preview_root,
                "right.cub",
                level=2,
            )
            right_preview.parent.mkdir(parents=True, exist_ok=True)
            right_preview.write_text("cached", encoding="utf-8")

            with mock.patch.object(
                match_visualization_module,
                "_cube_dimensions",
                return_value=(4096, 4096),
            ), mock.patch.object(
                match_visualization_module,
                "create_low_resolution_dom",
                side_effect=fake_create,
            ) as create_mock, mock.patch.object(
                match_visualization_module,
                "_read_cube_as_stretched_byte",
                return_value=np.full((64, 64), 128, dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "drawMatches",
                return_value=np.zeros((10, 10, 3), dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "imwrite",
                return_value=True,
            ):
                result = match_visualization_module.write_stereo_pair_match_visualization(
                    "left.cub",
                    "right.cub",
                    left_key_file,
                    right_key_file,
                    output_path=temp_dir / "viz.png",
                    visualization_mode="reduced",
                    preview_cache_dir=preview_root,
                    visualization_target_long_edge=1024,
                )

        self.assertFalse(result["preview_cache_hit"])
        self.assertTrue(result["preview_cache_hit_left"])
        self.assertFalse(result["preview_cache_hit_right"])
        self.assertIsNone(result["preview_cache_validation_left"])
        self.assertEqual(result["preview_cache_validation_right"], "metadata_missing")
        self.assertEqual(result["preview_cache_source"], "visualization_cache")
        create_mock.assert_called_once()

    def test_write_match_visualization_reduced_mode_force_regenerate_marks_cache_miss(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0),))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(120.0, 120.0),))

        def fake_create(source, output, *, level, **kwargs):
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text("preview", encoding="utf-8")
            return Path(output)

        with temporary_directory() as temp_dir:
            preview_root = temp_dir / "preview_cache"
            for source_name in ("left.cub", "right.cub"):
                preview_path = match_visualization_module._preview_cache_path(
                    preview_root,
                    source_name,
                    level=2,
                )
                preview_path.parent.mkdir(parents=True, exist_ok=True)
                preview_path.write_text("cached", encoding="utf-8")

            with mock.patch.object(
                match_visualization_module,
                "_cube_dimensions",
                return_value=(4096, 4096),
            ), mock.patch.object(
                match_visualization_module,
                "create_low_resolution_dom",
                side_effect=fake_create,
            ) as create_mock, mock.patch.object(
                match_visualization_module,
                "_read_cube_as_stretched_byte",
                return_value=np.full((64, 64), 128, dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "drawMatches",
                return_value=np.zeros((10, 10, 3), dtype=np.uint8),
            ), mock.patch.object(
                match_visualization_module.cv2,
                "imwrite",
                return_value=True,
            ):
                result = match_visualization_module.write_stereo_pair_match_visualization(
                    "left.cub",
                    "right.cub",
                    left_key_file,
                    right_key_file,
                    output_path=temp_dir / "viz.png",
                    visualization_mode="reduced",
                    preview_cache_dir=preview_root,
                    preview_force_regenerate=True,
                    visualization_target_long_edge=1024,
                )

        self.assertFalse(result["preview_cache_hit"])
        self.assertFalse(result["preview_cache_hit_left"])
        self.assertFalse(result["preview_cache_hit_right"])
        self.assertIsNone(result["preview_cache_validation_left"])
        self.assertIsNone(result["preview_cache_validation_right"])
        self.assertEqual(result["preview_cache_source"], "visualization_cache")
        self.assertEqual(create_mock.call_count, 2)

    def test_write_match_visualization_reduced_cropped_mode_reads_preview_window(self):
        left_key_file = KeypointFile(4096, 4096, (Keypoint(100.0, 100.0), Keypoint(120.0, 120.0)))
        right_key_file = KeypointFile(4096, 4096, (Keypoint(110.0, 110.0), Keypoint(130.0, 130.0)))
        read_windows: list[tuple[int, int, int, int]] = []
        captured_keypoints: dict[str, list[tuple[float, float]]] = {}

        def fake_dimensions(path):
            if "preview_cache" in str(path):
                return (1024, 1024)
            return (4096, 4096)

        def fake_read(cube_path, *, window=None, **kwargs):
            read_windows.append((window.start_x, window.start_y, window.width, window.height))
            return np.full((window.height, window.width), 128, dtype=np.uint8)

        def fake_create(source, output, *, level, **kwargs):
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text("preview", encoding="utf-8")
            return Path(output)

        def fake_draw_matches(
            left_image,
            left_keypoints,
            right_image,
            right_keypoints,
            matches,
            out_image,
            **kwargs,
        ):
            captured_keypoints["left"] = [keypoint.pt for keypoint in left_keypoints]
            captured_keypoints["right"] = [keypoint.pt for keypoint in right_keypoints]
            return np.zeros((10, 10, 3), dtype=np.uint8)

        with temporary_directory() as temp_dir, mock.patch.object(
            match_visualization_module,
            "_cube_dimensions",
            side_effect=fake_dimensions,
        ), mock.patch.object(
            match_visualization_module,
            "create_low_resolution_dom",
            side_effect=fake_create,
        ), mock.patch.object(
            match_visualization_module,
            "_read_cube_as_stretched_byte",
            side_effect=fake_read,
        ), mock.patch.object(
            match_visualization_module.cv2,
            "drawMatches",
            side_effect=fake_draw_matches,
        ), mock.patch.object(
            match_visualization_module.cv2,
            "imwrite",
            return_value=True,
        ):
            result = match_visualization_module.write_stereo_pair_match_visualization(
                "left.cub",
                "right.cub",
                left_key_file,
                right_key_file,
                output_path=temp_dir / "viz.png",
                visualization_mode="reduced_cropped",
                preview_cache_dir=temp_dir / "preview_cache",
                visualization_target_long_edge=1024,
            )

        source_scale = 1.0 / 4.0
        scaled_left_points = tuple(
            Keypoint((point.sample - 1.0) * source_scale + 1.0, (point.line - 1.0) * source_scale + 1.0)
            for point in left_key_file.points
        )
        scaled_right_points = tuple(
            Keypoint((point.sample - 1.0) * source_scale + 1.0, (point.line - 1.0) * source_scale + 1.0)
            for point in right_key_file.points
        )
        expected_left_window = match_visualization_module.crop_window_for_keypoints(
            scaled_left_points,
            image_width=1024,
            image_height=1024,
            margin_pixels=match_visualization_module.DEFAULT_PREVIEW_CROP_MARGIN_PIXELS,
        )
        expected_right_window = match_visualization_module.crop_window_for_keypoints(
            scaled_right_points,
            image_width=1024,
            image_height=1024,
            margin_pixels=match_visualization_module.DEFAULT_PREVIEW_CROP_MARGIN_PIXELS,
        )
        expected_crop_window = {
            "left": {
                "start_x": expected_left_window.start_x,
                "start_y": expected_left_window.start_y,
                "width": expected_left_window.width,
                "height": expected_left_window.height,
            },
            "right": {
                "start_x": expected_right_window.start_x,
                "start_y": expected_right_window.start_y,
                "width": expected_right_window.width,
                "height": expected_right_window.height,
            },
        }
        expected_left_pts = [
            (
                (point.sample - expected_left_window.start_x - 1.0) / 3.0,
                (point.line - expected_left_window.start_y - 1.0) / 3.0,
            )
            for point in scaled_left_points
        ]
        expected_right_pts = [
            (
                (point.sample - expected_right_window.start_x - 1.0) / 3.0,
                (point.line - expected_right_window.start_y - 1.0) / 3.0,
            )
            for point in scaled_right_points
        ]

        self.assertEqual(result["visualization_mode_used"], "reduced_cropped")
        self.assertEqual(result["preview_cache_source"], "visualization_cache")
        self.assertEqual(result["crop_window"], expected_crop_window)
        self.assertEqual(result["source_scale_factor"], source_scale)
        self.assertEqual(
            read_windows,
            [
                (
                    expected_left_window.start_x,
                    expected_left_window.start_y,
                    expected_left_window.width,
                    expected_left_window.height,
                ),
                (
                    expected_right_window.start_x,
                    expected_right_window.start_y,
                    expected_right_window.width,
                    expected_right_window.height,
                ),
            ],
        )
        for actual, expected in zip(captured_keypoints["left"], expected_left_pts):
            self.assertAlmostEqual(actual[0], expected[0], places=4)
            self.assertAlmostEqual(actual[1], expected[1], places=4)
        for actual, expected in zip(captured_keypoints["right"], expected_right_pts):
            self.assertAlmostEqual(actual[0], expected[0], places=4)
            self.assertAlmostEqual(actual[1], expected[1], places=4)

    def test_write_match_visualization_preserves_full_mode_for_small_images(self):
        left_key_file = KeypointFile(32, 32, (Keypoint(10.0, 10.0),))
        right_key_file = KeypointFile(32, 32, (Keypoint(11.0, 11.0),))
        read_windows: list[object | None] = []

        def fake_read(cube_path, *, window=None, **kwargs):
            read_windows.append(window)
            return np.full((32, 32), 128, dtype=np.uint8)

        with temporary_directory() as temp_dir, mock.patch.object(
            match_visualization_module,
            "_cube_dimensions",
            return_value=(32, 32),
        ) as cube_dimensions_mock, mock.patch.object(
            match_visualization_module,
            "_read_cube_as_stretched_byte",
            side_effect=fake_read,
        ):
            result = match_visualization_module.write_stereo_pair_match_visualization(
                "left.cub",
                "right.cub",
                left_key_file,
                right_key_file,
                output_path=temp_dir / "viz.png",
                visualization_mode="auto",
                max_preview_pixels=4096,
            )

        self.assertEqual(result["visualization_mode_used"], "full")
        self.assertEqual(cube_dimensions_mock.call_count, 2)
        self.assertEqual(read_windows, [None, None])

    def test_match_dom_pair_to_key_files_writes_default_match_visualization_next_to_key_outputs(self):
        width = 96
        height = 96
        image = _build_textured_test_image(width, height)

        with temporary_directory() as temp_dir:
            left_cube, left_path = make_test_cube(temp_dir, name="left_stage.cub", samples=width, lines=height, bands=1)
            right_cube, right_path = make_test_cube(temp_dir, name="right_stage.cub", samples=width, lines=height, bands=1)
            try:
                _write_array_to_cube(left_cube, image)
                _write_array_to_cube(right_cube, image)
                attach_dom_like_projection_mapping(left_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
                attach_dom_like_projection_mapping(right_cube, pixel_resolution=1.0, upper_left_x=0.0, upper_left_y=float(height))
            finally:
                left_cube.close()
                right_cube.close()

            left_key_path = temp_dir / "left_stage.key"
            right_key_path = temp_dir / "right_stage.key"
            result = match_dom_pair_to_key_files(
                left_path,
                right_path,
                left_key_path,
                right_key_path,
                max_image_dimension=64,
                block_width=64,
                block_height=64,
                overlap_x=16,
                overlap_y=16,
                min_valid_pixels=32,
                ratio_test=0.8,
            )
            visualization_output_path = Path(result["match_visualization"]["output_path"])
            visualization_output_exists = visualization_output_path.exists()
            visualization_output_parent = visualization_output_path.parent

        self.assertGreater(result["point_count"], 0)
        self.assertIn("match_visualization", result)
        self.assertTrue(visualization_output_exists)
        self.assertEqual(visualization_output_parent, Path(left_key_path).parent)

    def test_match_dom_pair_to_key_files_accepts_legacy_positional_show_progress(self):
        width = 96
        height = 96
        image = _build_textured_test_image(width, height)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_legacy_progress.cub",
                right_name="right_legacy_progress.cub",
            )
            left_key_path = temp_dir / "left_legacy_progress.key"
            right_key_path = temp_dir / "right_legacy_progress.key"
            result = match_dom_pair_to_key_files(
                left_path,
                right_path,
                left_key_path,
                right_key_path,
                None,
                True,
                None,
                None,
                1.0 / 3.0,
                True,
                max_image_dimension=64,
                block_width=64,
                block_height=64,
                overlap_x=16,
                overlap_y=16,
                min_valid_pixels=32,
                ratio_test=0.8,
            )
            visualization_output_path = Path(result["match_visualization"]["output_path"])
            visualization_output_exists = visualization_output_path.exists()

        self.assertIn("match_visualization", result)
        self.assertTrue(visualization_output_exists)

    def test_match_dom_pair_uses_adaptive_routed_matcher_when_enabled(self):
        image = _build_textured_test_image(96, 96)
        accepted_points = tuple(Keypoint(float(index), float(index)) for index in range(40))
        fake_tile_result = tile_matching_module.TileMatchResult(
            stats=tile_matching_module.TileMatchStats(
                0,
                0,
                96,
                96,
                0,
                0,
                0,
                0,
                96 * 96,
                96 * 96,
                1.0,
                1.0,
                40,
                40,
                40,
                "matched",
            ),
            left_points=accepted_points,
            right_points=accepted_points,
        )

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_adaptive_route.cub",
                right_name="right_adaptive_route.cub",
            )

            with mock.patch.object(
                image_match,
                "_estimate_low_resolution_projected_offset",
                return_value={
                    "enabled": False,
                    "status": "disabled",
                    "delta_x_projected": 0.0,
                    "delta_y_projected": 0.0,
                },
            ), mock.patch.object(
                image_match,
                "_resolve_adaptive_route_for_pair",
                return_value=(
                    "lightglue",
                    {
                        "enabled": True,
                        "status": "routed",
                        "requested_matcher": "bf",
                        "selected_initial_matcher": "lightglue",
                        "reason": "synthetic route for focused regression",
                    },
                ),
            ), mock.patch.object(
                image_match,
                "_run_serial_tile_match_tasks",
                return_value=_tile_match_batch_result(fake_tile_result),
            ) as serial_mock:
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    matcher_method="bf",
                    enable_adaptive_routing=True,
                    adaptive_routing_profile="strict",
                    use_parallel_cpu=False,
                    max_image_dimension=512,
                    min_valid_pixels=32,
                )

        self.assertEqual(serial_mock.call_args.kwargs["matcher_method"], "lightglue")
        self.assertEqual(summary["matcher_method_requested"], "bf")
        self.assertEqual(summary["matcher_method_effective"], "lightglue")
        self.assertEqual(summary["matcher"]["matcher_method_requested"], "bf")
        self.assertEqual(summary["matcher"]["matcher_method_effective"], "lightglue")
        self.assertEqual(summary["adaptive_routing"]["selected_initial_matcher"], "lightglue")

    def test_match_ori_pair_uses_raw_inputs_for_adaptive_routing(self):
        image = _build_textured_test_image(96, 96)
        accepted_points = tuple(Keypoint(float(index), float(index)) for index in range(40))
        fake_tile_result = tile_matching_module.TileMatchResult(
            stats=tile_matching_module.TileMatchStats(
                0, 0, 96, 96, 0, 0, 0, 0, 96 * 96, 96 * 96,
                1.0, 1.0, 40, 40, 40, "matched",
            ),
            left_points=accepted_points,
            right_points=accepted_points,
        )

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_raw_adaptive.cub",
                right_name="right_raw_adaptive.cub",
            )

            with mock.patch.object(
                image_match,
                "_compute_texture_probe_from_cube_path",
                return_value=ImageTextureProbe(
                    keypoint_count=200,
                    valid_pixel_count=96 * 96,
                    total_pixel_count=96 * 96,
                    keypoint_density=0.02,
                    mean_gradient=24.0,
                    laplacian_variance=180.0,
                    entropy=3.5,
                    valid_pixel_ratio=1.0,
                    real_texture_score=0.6,
                ),
            ), mock.patch.object(
                image_match,
                "_compute_texture_sparseness_and_geometry_from_cube_path",
                side_effect=[
                    (
                        ImageSparsenessSummary(
                            tile_total_count=1,
                            tile_valid_count=1,
                            tile_size=256,
                            tile_step=128,
                            min_valid_pixel_ratio=0.3,
                            aggregation_quantile=0.90,
                            image_texture_sparseness=0.25,
                            sparseness_quantiles={"p10": 0.25, "p50": 0.25, "p90": 0.25, "max": 0.25},
                            tile_metrics=(),
                        ),
                        SolarGeometry(30.0, 10.0, "Instrument", "SolarElevation", "SolarAzimuth"),
                        None,
                    ),
                    (
                        ImageSparsenessSummary(
                            tile_total_count=1,
                            tile_valid_count=1,
                            tile_size=256,
                            tile_step=128,
                            min_valid_pixel_ratio=0.3,
                            aggregation_quantile=0.90,
                            image_texture_sparseness=0.30,
                            sparseness_quantiles={"p10": 0.30, "p50": 0.30, "p90": 0.30, "max": 0.30},
                            tile_metrics=(),
                        ),
                        SolarGeometry(33.0, 15.0, "Instrument", "SolarElevation", "SolarAzimuth"),
                        None,
                    ),
                ],
            ) as diag_mock, mock.patch.object(
                image_match,
                "_run_serial_tile_match_tasks",
                return_value=_tile_match_batch_result(fake_tile_result),
            ) as serial_mock:
                _, _, summary = image_match.match_ori_pair(
                    left_path,
                    right_path,
                    matcher_method="flann",
                    enable_adaptive_routing=True,
                    adaptive_routing_profile="balanced",
                    adaptive_routing_deep_presets={
                        "lightglue": "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                        "loftr": "examples/controlnet_construct/presets/loftr_external_outdoor.json",
                    },
                    use_parallel_cpu=False,
                    max_image_dimension=512,
                    min_valid_pixels=32,
                )

        adaptive = summary["adaptive_routing"]
        self.assertEqual(adaptive["status"], "routed")
        self.assertEqual(diag_mock.call_args_list[0].args[0], str(left_path))
        self.assertEqual(diag_mock.call_args_list[1].args[0], str(right_path))
        self.assertEqual(serial_mock.call_args.kwargs["matcher_method"], "flann")
        self.assertEqual(adaptive["preview_sources"]["left"], str(left_path))
        self.assertEqual(adaptive["preview_sources"]["right"], str(right_path))
        self.assertEqual(adaptive["preview_sources"]["source_type"], "raw_original_cube")
        self.assertEqual(adaptive["sidecar"]["texture_sparseness"]["pair_texture_sparseness"], 0.30)
        self.assertIsNotNone(adaptive["sidecar"]["lighting_difference"]["lighting_difference_score"])

    def test_match_ori_pair_adaptive_routing_falls_back_to_requested_matcher_when_raw_diagnostics_fail(self):
        image = _build_textured_test_image(96, 96)
        accepted_points = tuple(Keypoint(float(index), float(index)) for index in range(20))
        fake_tile_result = tile_matching_module.TileMatchResult(
            stats=tile_matching_module.TileMatchStats(
                0, 0, 96, 96, 0, 0, 0, 0, 96 * 96, 96 * 96,
                1.0, 1.0, 20, 20, 20, "matched",
            ),
            left_points=accepted_points,
            right_points=accepted_points,
        )

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_raw_adaptive_error.cub",
                right_name="right_raw_adaptive_error.cub",
            )

            with mock.patch.object(
                image_match,
                "_compute_texture_probe_from_cube_path",
                side_effect=RuntimeError("synthetic diagnostic failure"),
            ), mock.patch.object(
                image_match,
                "_run_serial_tile_match_tasks",
                return_value=_tile_match_batch_result(fake_tile_result),
            ) as serial_mock:
                _, _, summary = image_match.match_ori_pair(
                    left_path,
                    right_path,
                    matcher_method="flann",
                    enable_adaptive_routing=True,
                    use_parallel_cpu=False,
                    max_image_dimension=512,
                    min_valid_pixels=32,
                )

        self.assertEqual(serial_mock.call_args.kwargs["matcher_method"], "flann")
        self.assertEqual(summary["adaptive_routing"]["status"], "routing_failed")
        self.assertEqual(summary["adaptive_routing"]["selected_initial_matcher"], "flann")
        self.assertIn("synthetic diagnostic failure", summary["adaptive_routing"]["reason"])

    def test_match_dom_pair_falls_back_through_adaptive_cascade_after_failed_quality_gate(self):
        image = _build_textured_test_image(96, 96)
        accepted_points = tuple(Keypoint(float(index), float(index)) for index in range(40))
        weak_tile_result = tile_matching_module.TileMatchResult(
            stats=tile_matching_module.TileMatchStats(
                0,
                0,
                96,
                96,
                0,
                0,
                0,
                0,
                96 * 96,
                96 * 96,
                1.0,
                1.0,
                0,
                0,
                0,
                "skipped_no_matches",
            ),
            left_points=(),
            right_points=(),
        )
        accepted_tile_result = tile_matching_module.TileMatchResult(
            stats=tile_matching_module.TileMatchStats(
                0,
                0,
                96,
                96,
                0,
                0,
                0,
                0,
                96 * 96,
                96 * 96,
                1.0,
                1.0,
                40,
                40,
                40,
                "matched",
            ),
            left_points=accepted_points,
            right_points=accepted_points,
        )

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_adaptive_cascade.cub",
                right_name="right_adaptive_cascade.cub",
            )

            with mock.patch.object(
                image_match,
                "_estimate_low_resolution_projected_offset",
                return_value={
                    "enabled": False,
                    "status": "disabled",
                    "delta_x_projected": 0.0,
                    "delta_y_projected": 0.0,
                },
            ), mock.patch.object(
                image_match,
                "_resolve_adaptive_route_for_pair",
                return_value=(
                    "lightglue",
                    {
                        "enabled": True,
                        "status": "routed",
                        "requested_matcher": "bf",
                        "selected_initial_matcher": "lightglue",
                        "reason": "synthetic cascade route for focused regression",
                        "sidecar": {
                            "pair_route": {
                                "initial_matcher": "lightglue",
                                "fallback_chain": ["loftr"],
                            }
                        },
                    },
                ),
            ), mock.patch.object(
                image_match,
                "_run_serial_tile_match_tasks",
                side_effect=[
                    _tile_match_batch_result(weak_tile_result),
                    _tile_match_batch_result(accepted_tile_result),
                ],
            ) as serial_mock:
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    matcher_method="bf",
                    enable_adaptive_routing=True,
                    adaptive_routing_profile="strict",
                    use_parallel_cpu=False,
                    max_image_dimension=512,
                    min_valid_pixels=32,
                )

        called_matchers = [call.kwargs["matcher_method"] for call in serial_mock.call_args_list]
        self.assertEqual(called_matchers, ["lightglue", "loftr"])
        self.assertEqual(summary["point_count"], len(accepted_points))
        self.assertEqual(summary["matcher_method_effective"], "loftr")
        self.assertEqual(summary["matcher"]["matcher_method_effective"], "loftr")
        adaptive_summary = summary["adaptive_routing"]
        self.assertEqual(summary["adaptive_routing_profile"], "strict")
        self.assertEqual(summary["adaptive_routing_quality_gate"]["min_inlier_count"], 36)
        self.assertEqual(adaptive_summary["profile"], "strict")
        self.assertEqual(adaptive_summary["quality_gate"]["max_p95_residual"], 3.0)
        self.assertEqual(adaptive_summary["cascade_plan"], ["lightglue", "loftr"])
        self.assertEqual(adaptive_summary["selected_final_matcher"], "loftr")
        self.assertEqual(len(adaptive_summary["cascade_attempts"]), 2)
        self.assertEqual(adaptive_summary["cascade_attempts"][0]["decision"]["next_matcher"], "loftr")
        self.assertTrue(adaptive_summary["final_decision"]["accepted"])
        self.assertTrue(adaptive_summary["final_decision"]["fallback_used"])

    def test_match_dom_pair_to_key_files_metadata_includes_visualization(self):
        width = 96
        height = 96
        image = _build_textured_test_image(width, height)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_metadata_viz.cub",
                right_name="right_metadata_viz.cub",
            )
            left_key = temp_dir / "left_metadata_viz.key"
            right_key = temp_dir / "right_metadata_viz.key"
            metadata_output = temp_dir / "match_metadata" / "pair.json"
            metadata_output.parent.mkdir(parents=True)

            result = match_dom_pair_to_key_files(
                left_path,
                right_path,
                left_key,
                right_key,
                metadata_output=metadata_output,
                max_image_dimension=64,
                block_width=64,
                block_height=64,
                overlap_x=16,
                overlap_y=16,
                min_valid_pixels=32,
                ratio_test=0.8,
            )

            payload = json.loads(metadata_output.read_text(encoding="utf-8"))

        visualization_payload = payload["match_visualization"]
        self.assertIn("visualization_mode_used", visualization_payload)
        self.assertEqual(visualization_payload["output_path"], result["match_visualization"]["output_path"])

    def test_match_dom_pair_to_key_files_metadata_includes_adaptive_routing(self):
        summary = {
            "status": "matched_no_points",
            "reason": "synthetic focused metadata regression",
            "point_count": 0,
            "tile_count": 1,
            "tile_count_before_preindex_filter": 1,
            "tile_count_after_preindex_filter": 1,
            "preindexed_skipped_tile_count": 0,
            "full_resolution_skipped_tile_count": 1,
            "matched_tile_count": 0,
            "skipped_tile_count": 1,
            "tile_validity_prefilter_enabled": False,
            "tile_validity_cache_dir": None,
            "tile_validity_cell_width": 256,
            "tile_validity_cell_height": 256,
            "tile_block_alignment_mode": "off",
            "block_alignment_reason": "alignment_disabled",
            "tile_block_alignment": {
                "mode": "off",
                "status": "disabled",
                "reason": "alignment_disabled",
            },
            "tile_validity_skip_reasons": {},
            "left_tile_validity_index": None,
            "right_tile_validity_index": None,
            "tiling_used": False,
            "valid_pixel_percent_threshold": 0.0,
            "invalid_pixel_radius": 1,
            "matcher": {
                "matcher_method_requested": "bf",
                "matcher_method_effective": "lightglue",
                "matcher_method_used": "lightglue",
                "ratio_test": 0.75,
            },
            "parallel_cpu_requested": False,
            "num_worker_parallel_cpu": 1,
            "parallel_cpu_used": False,
            "parallel_cpu_backend": "serial",
            "parallel_cpu_worker_count": 1,
            "tile_match_backend": "serial",
            "low_resolution_offset": {
                "enabled": False,
                "status": "disabled",
                "delta_x_projected": 0.0,
                "delta_y_projected": 0.0,
            },
            "low_resolution_matching_target_long_edge": None,
            "resolved_low_resolution_level": 3,
            "adaptive_routing": {
                "enabled": True,
                "status": "routed",
                "requested_matcher": "bf",
                "selected_initial_matcher": "lightglue",
                "reason": "synthetic route for metadata regression",
            },
            "preparation": {
                "status": "ready",
                "reason": "ready",
            },
        }

        with temporary_directory() as temp_dir:
            left_key = temp_dir / "left_adaptive_metadata.key"
            right_key = temp_dir / "right_adaptive_metadata.key"
            metadata_output = temp_dir / "match_metadata" / "pair.json"
            metadata_output.parent.mkdir(parents=True)

            with mock.patch.object(
                image_match,
                "match_dom_pair",
                return_value=(KeypointFile(10, 10, ()), KeypointFile(10, 10, ()), summary),
            ):
                match_dom_pair_to_key_files(
                    "left.cub",
                    "right.cub",
                    left_key,
                    right_key,
                    metadata_output=metadata_output,
                    write_match_visualization=False,
                )

            payload = json.loads(metadata_output.read_text(encoding="utf-8"))

        self.assertIn("adaptive_routing", payload["image_match"])
        self.assertEqual(payload["image_match"]["adaptive_routing"]["selected_initial_matcher"], "lightglue")

    def test_match_dom_pair_to_key_files_metadata_records_visualization_failure(self):
        width = 96
        height = 96
        image = _build_textured_test_image(width, height)
        sentinel_error = RuntimeError("sentinel visualization failure")

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_metadata_viz_failure.cub",
                right_name="right_metadata_viz_failure.cub",
            )
            left_key = temp_dir / "left_metadata_viz_failure.key"
            right_key = temp_dir / "right_metadata_viz_failure.key"
            metadata_output = temp_dir / "match_metadata" / "pair.json"
            metadata_output.parent.mkdir(parents=True)

            with mock.patch.object(
                image_match,
                "write_stereo_pair_match_visualization",
                side_effect=sentinel_error,
            ):
                with self.assertRaises(RuntimeError) as raised:
                    match_dom_pair_to_key_files(
                        left_path,
                        right_path,
                        left_key,
                        right_key,
                        metadata_output=metadata_output,
                        max_image_dimension=64,
                        block_width=64,
                        block_height=64,
                        overlap_x=16,
                        overlap_y=16,
                        min_valid_pixels=32,
                        ratio_test=0.8,
                    )

            self.assertIs(raised.exception, sentinel_error)
            payload = json.loads(metadata_output.read_text(encoding="utf-8"))

        match_visualization_payload = payload["match_visualization"]
        self.assertEqual(match_visualization_payload["status"], "failed")
        self.assertEqual(match_visualization_payload["error_type"], "RuntimeError")
        self.assertIn("sentinel visualization failure", match_visualization_payload["error"])
        self.assertIn("point_count", payload["image_match"])
        self.assertIn("tile_count", payload["image_match"])

    def test_parallel_tile_batch_worker_reuses_open_cubes_for_task_shard(self):
        open_paths: list[str] = []
        close_count = 0
        progress_events: list[int] = []

        class FakeCube:
            def __init__(self):
                self._open = False

            def open(self, path, mode):
                open_paths.append(str(path))
                self._open = True

            def is_open(self):
                return self._open

            def close(self):
                nonlocal close_count
                close_count += 1
                self._open = False

        tasks = [
            tile_matching_module.IndexedTileMatchTask(
                index=0,
                task=tile_matching_module.TileMatchTask(
                    left_dom_path="left.cub",
                    right_dom_path="right.cub",
                    band=1,
                    paired_window=tile_matching_module.PairedTileWindow(
                        local_window=tile_matching_module.TileWindow(0, 0, 8, 8),
                        left_window=tile_matching_module.TileWindow(0, 0, 8, 8),
                        right_window=tile_matching_module.TileWindow(0, 0, 8, 8),
                    ),
                    minimum_value=None,
                    maximum_value=None,
                    lower_percent=0.5,
                    upper_percent=99.5,
                    invalid_values=(),
                    special_pixel_abs_threshold=1.0e300,
                    min_valid_pixels=1,
                    valid_pixel_percent_threshold=0.0,
                    invalid_pixel_radius=0,
                    ratio_test=0.75,
                    matcher_method="bf",
                    max_features=None,
                    sift_octave_layers=3,
                    sift_contrast_threshold=0.04,
                    sift_edge_threshold=10.0,
                    sift_sigma=1.6,
                ),
            ),
            tile_matching_module.IndexedTileMatchTask(
                index=1,
                task=tile_matching_module.TileMatchTask(
                    left_dom_path="left.cub",
                    right_dom_path="right.cub",
                    band=1,
                    paired_window=tile_matching_module.PairedTileWindow(
                        local_window=tile_matching_module.TileWindow(8, 0, 8, 8),
                        left_window=tile_matching_module.TileWindow(8, 0, 8, 8),
                        right_window=tile_matching_module.TileWindow(8, 0, 8, 8),
                    ),
                    minimum_value=None,
                    maximum_value=None,
                    lower_percent=0.5,
                    upper_percent=99.5,
                    invalid_values=(),
                    special_pixel_abs_threshold=1.0e300,
                    min_valid_pixels=1,
                    valid_pixel_percent_threshold=0.0,
                    invalid_pixel_radius=0,
                    ratio_test=0.75,
                    matcher_method="bf",
                    max_features=None,
                    sift_octave_layers=3,
                    sift_contrast_threshold=0.04,
                    sift_edge_threshold=10.0,
                    sift_sigma=1.6,
                ),
            ),
        ]

        def fake_match_task_with_open_cubes(task, **kwargs):
            return tile_matching_module.TileMatchResult(
                stats=tile_matching_module.TileMatchStats(
                    local_start_x=task.paired_window.local_window.start_x,
                    local_start_y=task.paired_window.local_window.start_y,
                    width=task.paired_window.local_window.width,
                    height=task.paired_window.local_window.height,
                    left_start_x=task.paired_window.left_window.start_x,
                    left_start_y=task.paired_window.left_window.start_y,
                    right_start_x=task.paired_window.right_window.start_x,
                    right_start_y=task.paired_window.right_window.start_y,
                    left_valid_pixel_count=64,
                    right_valid_pixel_count=64,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=0,
                    right_feature_count=0,
                    match_count=0,
                    status="skipped_insufficient_matches",
                ),
                left_points=(),
                right_points=(),
            )

        with mock.patch.object(tile_matching_module.ip, "Cube", FakeCube), mock.patch.object(
            tile_matching_module,
            "_resolved_invalid_values_for_cube",
            return_value=(),
        ), mock.patch.object(
            tile_matching_module,
            "_match_tile_task_with_open_cubes",
            side_effect=fake_match_task_with_open_cubes,
        ):
            class RecordingQueue:
                def put(self, value):
                    progress_events.append(int(value))

            results = tile_matching_module._match_tile_task_batch_worker(
                tuple(tasks),
                progress_queue=RecordingQueue(),
            )

        self.assertEqual(open_paths, ["left.cub", "right.cub"])
        self.assertEqual(close_count, 2)
        self.assertEqual([index for index, _ in results], [0, 1])
        self.assertEqual(progress_events, [1, 1])

    def test_parallel_tile_batch_worker_applies_opencv_thread_config_once(self):
        set_thread_calls: list[int] = []

        class FakeCube:
            def __init__(self):
                self._open = False

            def open(self, path, mode):
                self._open = True

            def is_open(self):
                return self._open

            def close(self):
                self._open = False

        task = tile_matching_module.IndexedTileMatchTask(
            index=0,
            task=tile_matching_module.TileMatchTask(
                left_dom_path="left.cub",
                right_dom_path="right.cub",
                band=1,
                paired_window=tile_matching_module.PairedTileWindow(
                    local_window=tile_matching_module.TileWindow(0, 0, 8, 8),
                    left_window=tile_matching_module.TileWindow(0, 0, 8, 8),
                    right_window=tile_matching_module.TileWindow(0, 0, 8, 8),
                ),
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=1,
                valid_pixel_percent_threshold=0.0,
                invalid_pixel_radius=0,
                ratio_test=0.75,
                matcher_method="bf",
                max_features=None,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                opencv_num_threads=1,
            ),
        )
        fake_result = tile_matching_module.TileMatchResult(
            stats=tile_matching_module.TileMatchStats(
                local_start_x=0,
                local_start_y=0,
                width=8,
                height=8,
                left_start_x=0,
                left_start_y=0,
                right_start_x=0,
                right_start_y=0,
                left_valid_pixel_count=64,
                right_valid_pixel_count=64,
                left_valid_pixel_ratio=1.0,
                right_valid_pixel_ratio=1.0,
                left_feature_count=0,
                right_feature_count=0,
                match_count=0,
                status="skipped_insufficient_matches",
            ),
            left_points=(),
            right_points=(),
        )

        with mock.patch.object(tile_matching_module.ip, "Cube", FakeCube), mock.patch.object(
            tile_matching_module.cv2,
            "setNumThreads",
            side_effect=lambda value: set_thread_calls.append(int(value)),
        ), mock.patch.object(
            tile_matching_module,
            "_resolved_invalid_values_for_cube",
            return_value=(),
        ), mock.patch.object(
            tile_matching_module,
            "_match_tile_task_with_open_cubes",
            return_value=fake_result,
        ):
            results = tile_matching_module._match_tile_task_batch_worker((task,))

        self.assertEqual(set_thread_calls, [1])
        self.assertEqual(results, ((0, fake_result),))

    def test_run_parallel_tile_match_tasks_drains_progress_queue_before_future_completion(self):
        progress_call_order: list[str] = []

        def build_result(local_start_x: int):
            return tile_matching_module.TileMatchResult(
                stats=tile_matching_module.TileMatchStats(
                    local_start_x=local_start_x,
                    local_start_y=0,
                    width=8,
                    height=8,
                    left_start_x=local_start_x,
                    left_start_y=0,
                    right_start_x=local_start_x,
                    right_start_y=0,
                    left_valid_pixel_count=64,
                    right_valid_pixel_count=64,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=0,
                    right_feature_count=0,
                    match_count=0,
                    status="skipped_insufficient_matches",
                ),
                left_points=(),
                right_points=(),
            )

        result_zero = build_result(0)
        result_one = build_result(8)

        class FakeQueue:
            def __init__(self):
                self._items: list[int] = []

            def put(self, value):
                self._items.append(int(value))

            def get_nowait(self):
                if not self._items:
                    raise tile_matching_module.queue.Empty()
                return self._items.pop(0)

        class FakeManager:
            def __init__(self, queue_instance):
                self._queue_instance = queue_instance
                self.shutdown_called = False

            def Queue(self):
                return self._queue_instance

            def shutdown(self):
                self.shutdown_called = True

        class FakeFuture:
            def __init__(self, label: str, indexed_results):
                self._label = label
                self._indexed_results = indexed_results

            def result(self):
                progress_call_order.append(f"result:{self._label}")
                return self._indexed_results

        fake_queue = FakeQueue()
        fake_manager = FakeManager(fake_queue)
        future_a = FakeFuture("a", ((0, result_zero),))
        future_b = FakeFuture("b", ((1, result_one),))
        submitted_queues: list[object] = []
        wait_call_count = 0

        class FakeExecutor:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def submit(self, fn, chunk, progress_queue):
                submitted_queues.append(progress_queue)
                if chunk == ((0, {"chunk": "a"}),):
                    return future_a
                return future_b

        def fake_wait(pending_futures, timeout, return_when):
            nonlocal wait_call_count
            wait_call_count += 1
            if wait_call_count == 1:
                fake_queue.put(1)
                return set(), set(pending_futures)
            if wait_call_count == 2:
                fake_queue.put(1)
                return {future_a}, set(pending_futures) - {future_a}
            return {future_b}, set()

        def progress_callback():
            progress_call_order.append(f"progress:{len([item for item in progress_call_order if item.startswith('progress:')]) + 1}")

        with mock.patch.object(
            tile_matching_module,
            "_chunk_tile_match_task_payloads",
            return_value=[((0, {"chunk": "a"}),), ((1, {"chunk": "b"}),)],
        ), mock.patch.object(
            tile_matching_module,
            "ProcessPoolExecutor",
            FakeExecutor,
        ), mock.patch.object(
            tile_matching_module,
            "wait",
            side_effect=fake_wait,
        ), mock.patch.object(
            tile_matching_module.mp,
            "Manager",
            return_value=fake_manager,
        ):
            results = tile_matching_module._run_parallel_tile_match_tasks(
                [object(), object()],
                max_workers=2,
                progress_callback=progress_callback,
            )

        self.assertEqual(results, [result_zero, result_one])
        self.assertEqual(submitted_queues, [fake_queue, fake_queue])
        self.assertTrue(fake_manager.shutdown_called)
        self.assertEqual(
            [entry for entry in progress_call_order if entry.startswith("progress:")],
            ["progress:1", "progress:2"],
        )
        self.assertLess(
            progress_call_order.index("progress:1"),
            progress_call_order.index("result:a"),
        )

    def test_match_dom_pair_reports_batched_parallel_backend(self):
        image = _build_textured_test_image(128, 128)
        synthetic_tile_results = [
            image_match.TileMatchResult(
                stats=image_match.TileMatchStats(
                    local_start_x=0,
                    local_start_y=0,
                    width=64,
                    height=64,
                    left_start_x=0,
                    left_start_y=0,
                    right_start_x=0,
                    right_start_y=0,
                    left_valid_pixel_count=4096,
                    right_valid_pixel_count=4096,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=5,
                    right_feature_count=5,
                    match_count=1,
                    status="matched",
                ),
                left_points=(Keypoint(10.0, 10.0),),
                right_points=(Keypoint(10.5, 10.5),),
            )
        ]

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_batched_parallel.cub",
                right_name="right_batched_parallel.cub",
            )
            with mock.patch.object(
                image_match,
                "_run_parallel_tile_match_tasks",
                return_value=synthetic_tile_results,
            ):
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    max_image_dimension=64,
                    block_width=64,
                    block_height=64,
                    overlap_x=0,
                    overlap_y=0,
                    min_valid_pixels=16,
                    num_worker_parallel_cpu=2,
                )

        self.assertTrue(summary["parallel_cpu_used"])
        self.assertEqual(summary["parallel_cpu_backend"], "process_pool_batched_cube_reuse")
        self.assertEqual(summary["tile_match_backend"], "process_pool_batched_cube_reuse")
        self.assertEqual(summary["parallel_cpu_worker_count"], 2)

    def test_match_dom_pair_forwards_dynamic_gpu_batch_options_to_parallel_tasks(self):
        image = _build_textured_test_image(128, 128)
        synthetic_tile_results = [
            image_match.TileMatchResult(
                stats=image_match.TileMatchStats(
                    local_start_x=0,
                    local_start_y=0,
                    width=64,
                    height=64,
                    left_start_x=0,
                    left_start_y=0,
                    right_start_x=0,
                    right_start_y=0,
                    left_valid_pixel_count=4096,
                    right_valid_pixel_count=4096,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=0,
                    right_feature_count=0,
                    match_count=0,
                    status="skipped_no_features",
                ),
                left_points=(),
                right_points=(),
            )
        ]

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_gpu_batch_options.cub",
                right_name="right_gpu_batch_options.cub",
            )
            with mock.patch.object(
                image_match,
                "_run_parallel_tile_match_tasks",
                return_value=synthetic_tile_results,
            ) as parallel_mock, mock.patch.object(
                image_match,
                "_can_use_dedicated_gpu_tile_route",
                return_value=True,
            ):
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    max_image_dimension=64,
                    block_width=64,
                    block_height=64,
                    overlap_x=0,
                    overlap_y=0,
                    min_valid_pixels=16,
                    num_worker_parallel_cpu=2,
                    use_gpu=True,
                    gpu_dynamic_batch=False,
                    gpu_min_batch_size=3,
                    gpu_max_batch_size=7,
                )

        self.assertFalse(parallel_mock.call_args.kwargs["gpu_dynamic_batch"])
        self.assertEqual(parallel_mock.call_args.kwargs["gpu_min_batch_size"], 3)
        self.assertEqual(parallel_mock.call_args.kwargs["gpu_max_batch_size"], 7)
        self.assertFalse(summary["parallel_cpu_used"])
        self.assertEqual(summary["parallel_cpu_backend"], "gpu_tile_pipeline")
        self.assertEqual(summary["tile_match_backend"], "gpu_tile_pipeline")
        self.assertEqual(summary["parallel_cpu_worker_count"], 0)

    def test_match_dom_pair_reports_gpu_disabled_when_runtime_falls_back_to_cpu(self):
        image = _build_textured_test_image(128, 128)
        synthetic_tile_results = [
            image_match.TileMatchResult(
                stats=image_match.TileMatchStats(
                    local_start_x=0,
                    local_start_y=0,
                    width=64,
                    height=64,
                    left_start_x=0,
                    left_start_y=0,
                    right_start_x=0,
                    right_start_y=0,
                    left_valid_pixel_count=4096,
                    right_valid_pixel_count=4096,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=0,
                    right_feature_count=0,
                    match_count=0,
                    status="skipped_no_features",
                ),
                left_points=(),
                right_points=(),
            )
        ]

        def cpu_fallback_parallel_tasks(*_args, **kwargs):
            stats = kwargs["gpu_stats"]
            stats.record_pair_result(used_cpu_fallback=True)
            stats.record_gpu_failure()
            return synthetic_tile_results

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_gpu_runtime_fallback.cub",
                right_name="right_gpu_runtime_fallback.cub",
            )
            with mock.patch.object(
                image_match,
                "_run_parallel_tile_match_tasks",
                side_effect=cpu_fallback_parallel_tasks,
            ), mock.patch.object(
                image_match,
                "_can_use_dedicated_gpu_tile_route",
                return_value=True,
            ):
                _, _, summary = match_dom_pair(
                    left_path,
                    right_path,
                    max_image_dimension=64,
                    block_width=64,
                    block_height=64,
                    overlap_x=0,
                    overlap_y=0,
                    min_valid_pixels=16,
                    num_worker_parallel_cpu=2,
                    use_gpu=True,
                )

        self.assertEqual(summary["tile_match_backend"], "gpu_tile_pipeline")
        self.assertTrue(summary["gpu"]["requested"])
        self.assertFalse(summary["gpu"]["enabled"])
        self.assertEqual(summary["gpu"]["runtime"]["gpu_batch_count"], 0)
        self.assertEqual(summary["gpu"]["runtime"]["cpu_fallback_pair_count"], 1)

    def test_match_dom_pair_to_key_files_writes_tile_validity_metadata(self):
        values = np.zeros((32, 64), dtype=np.float64)
        values[:, :32] = _build_textured_test_image(32, 32)

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                values,
                pixel_type=ip.PixelType.Real,
                left_name="left_prefilter_metadata.cub",
                right_name="right_prefilter_metadata.cub",
            )
            left_key = temp_dir / "dom_keys" / "left.key"
            right_key = temp_dir / "dom_keys" / "right.key"
            metadata_output = temp_dir / "match_metadata" / "pair.json"
            left_key.parent.mkdir(parents=True)
            metadata_output.parent.mkdir(parents=True)

            match_dom_pair_to_key_files(
                left_path,
                right_path,
                left_key,
                right_key,
                metadata_output=metadata_output,
                write_match_visualization=False,
                max_image_dimension=32,
                block_width=32,
                block_height=32,
                overlap_x=0,
                overlap_y=0,
                invalid_values=(0.0,),
                invalid_pixel_radius=0,
                valid_pixel_percent_threshold=0.2,
                min_valid_pixels=16,
                use_parallel_cpu=False,
                enable_tile_validity_prefilter=True,
                tile_validity_cell_width=32,
                tile_validity_cell_height=32,
            )

            payload = json.loads(metadata_output.read_text(encoding="utf-8"))

        image_match_payload = payload["image_match"]
        self.assertTrue(image_match_payload["tile_validity_prefilter_enabled"])
        self.assertEqual(image_match_payload["preindexed_skipped_tile_count"], 1)
        self.assertEqual(image_match_payload["tile_count_before_preindex_filter"], 2)
        self.assertEqual(image_match_payload["tile_count_after_preindex_filter"], 1)
        self.assertTrue(str(image_match_payload["tile_validity_cache_dir"]).endswith("tile_validity_cache"))

    def test_visualization_memory_profile_resolves_target_long_edges(self):
        high = match_visualization_module.resolve_visualization_options(memory_profile="high-memory")
        balanced = match_visualization_module.resolve_visualization_options(memory_profile="balanced")
        low = match_visualization_module.resolve_visualization_options(memory_profile="low-memory")

        self.assertEqual(high.visualization_target_long_edge, 4096)
        self.assertEqual(balanced.visualization_target_long_edge, 2048)
        self.assertEqual(low.visualization_target_long_edge, 1024)
        self.assertEqual(balanced.visualization_mode, "auto")
        self.assertEqual(balanced.preview_cache_source, "auto")

    def test_visualization_option_validation_rejects_invalid_values(self):
        with self.assertRaisesRegex(ValueError, "visualization_mode"):
            match_visualization_module.resolve_visualization_options(visualization_mode="huge")
        with self.assertRaisesRegex(ValueError, "memory_profile"):
            match_visualization_module.resolve_visualization_options(memory_profile="tiny")
        with self.assertRaisesRegex(ValueError, "visualization_target_long_edge must be positive"):
            match_visualization_module.resolve_visualization_options(visualization_target_long_edge=0)
        with self.assertRaisesRegex(ValueError, "preview_crop_margin_pixels must be >= 0"):
            match_visualization_module.resolve_visualization_options(preview_crop_margin_pixels=-1)

    def test_reduce_level_from_target_long_edge_uses_pair_common_longest_edge(self):
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(8192, 4096), 1)
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(8192, 2048), 2)
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(1000, 2048), 0)
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(4096, 4096), 0)
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(4097, 4096), 1)
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(4097, 2048), 2)
        self.assertEqual(lowres_offset_module.reduce_level_for_target_long_edge(2049, 2048), 1)
        self.assertEqual(
            lowres_offset_module.reduce_level_for_pair_target_long_edge(
                left_width=2048,
                left_height=1024,
                right_width=16384,
                right_height=512,
                target_long_edge=2048,
            ),
            3,
        )

    def test_visualization_crop_window_uses_keypoint_bounds_and_margin(self):
        points = (Keypoint(20.0, 30.0), Keypoint(80.0, 90.0))

        window = match_visualization_module.crop_window_for_keypoints(
            points,
            image_width=100,
            image_height=120,
            margin_pixels=10,
        )

        self.assertEqual((window.start_x, window.start_y, window.width, window.height), (9, 19, 81, 81))

    def test_visualization_crop_window_fractional_keypoints(self):
        points = (Keypoint(20.2, 30.7), Keypoint(80.9, 90.1))

        window = match_visualization_module.crop_window_for_keypoints(
            points,
            image_width=100,
            image_height=120,
            margin_pixels=10,
        )

        self.assertEqual((window.start_x, window.start_y, window.width, window.height), (9, 19, 82, 82))

    def test_visualization_crop_window_clips_to_image_start(self):
        points = (Keypoint(1.0, 1.0),)

        window = match_visualization_module.crop_window_for_keypoints(
            points,
            image_width=100,
            image_height=100,
            margin_pixels=10,
        )

        self.assertEqual((window.start_x, window.start_y), (0, 0))
        self.assertEqual((window.width, window.height), (11, 11))

    def test_visualization_crop_window_clips_to_image_end(self):
        points = (Keypoint(100.0, 100.0),)

        window = match_visualization_module.crop_window_for_keypoints(
            points,
            image_width=100,
            image_height=100,
            margin_pixels=10,
        )

        self.assertEqual((window.start_x, window.start_y), (89, 89))
        self.assertEqual((window.start_x + window.width, window.start_y + window.height), (100, 100))

    def test_visualization_crop_window_clips_out_of_bounds_point(self):
        points = (Keypoint(1000.0, 1000.0),)

        window = match_visualization_module.crop_window_for_keypoints(
            points,
            image_width=100,
            image_height=100,
            margin_pixels=10,
        )

        self.assertEqual((window.start_x, window.start_y), (99, 99))
        self.assertEqual((window.width, window.height), (1, 1))

    def test_visualization_crop_window_clips_out_of_bounds_negative_point(self):
        points = (Keypoint(-100.0, -100.0),)

        window = match_visualization_module.crop_window_for_keypoints(
            points,
            image_width=100,
            image_height=100,
            margin_pixels=0,
        )

        self.assertEqual((window.start_x, window.start_y), (0, 0))
        self.assertEqual((window.width, window.height), (1, 1))
        self.assertEqual((window.start_x + window.width, window.start_y + window.height), (1, 1))

    def test_visualization_crop_window_rejects_invalid_dimensions(self):
        points = (Keypoint(1.0, 1.0),)

        with self.assertRaisesRegex(ValueError, "image_width"):
            match_visualization_module.crop_window_for_keypoints(
                points,
                image_width=0,
                image_height=100,
                margin_pixels=0,
            )
        with self.assertRaisesRegex(ValueError, "image_height"):
            match_visualization_module.crop_window_for_keypoints(
                points,
                image_width=100,
                image_height=0,
                margin_pixels=0,
            )

    def test_visualization_crop_window_rejects_negative_margin(self):
        points = (Keypoint(1.0, 1.0),)

        with self.assertRaisesRegex(ValueError, r"^margin_pixels must be >= 0\.$"):
            match_visualization_module.crop_window_for_keypoints(
                points,
                image_width=100,
                image_height=100,
                margin_pixels=-1,
            )

    def test_visualization_crop_window_rejects_empty_points(self):
        with self.assertRaisesRegex(ValueError, "At least one keypoint"):
            match_visualization_module.crop_window_for_keypoints(
                (),
                image_width=100,
                image_height=100,
                margin_pixels=10,
            )


class GpuSiftIntegrationUnitTest(unittest.TestCase):
    """Verify GPU SIFT integration shares result structure with the CPU path."""

    def test_gpu_path_returns_same_structure(self):
        """When use_gpu=False, results should be valid TileMatchResult."""
        rng = np.random.default_rng(seed=20260506)
        left = rng.integers(0, 255, (256, 256), dtype=np.uint8)
        right = left.copy()  # identical -> should match

        left_mask = np.full((256, 256), 255, dtype=np.uint8)
        right_mask = left_mask.copy()

        kp_left, kp_right, matches = tile_matching_module._match_tile(
            left,
            right,
            left_mask=left_mask,
            right_mask=right_mask,
            ratio_test=0.75,
            matcher_method="bf",
            max_features=None,
            sift_octave_layers=3,
            sift_contrast_threshold=0.04,
            sift_edge_threshold=10.0,
            sift_sigma=1.6,
        )
        self.assertIsInstance(kp_left, list)
        self.assertIsInstance(kp_right, list)
        self.assertIsInstance(matches, list)

    def test_gpu_batch_cpu_fallback(self):
        """GpuSiftBatch should work without GPU hardware via CPU fallback."""
        gpu_sift_module = importlib.import_module("controlnet_construct.gpu_sift")
        rng = np.random.default_rng(seed=20260506)
        batch = gpu_sift_module.GpuSiftBatch(batch_size=4)
        img = rng.integers(0, 255, (128, 128), dtype=np.uint8)
        mask = np.full((128, 128), 255, dtype=np.uint8)
        batch.add(img, mask)
        batch.add(img, mask)
        results = batch.execute()
        self.assertEqual(len(results), 2)
        for kp, desc in results:
            self.assertIsInstance(kp, (list, tuple))
            # desc can be None if no keypoints found
            if desc is not None:
                self.assertEqual(desc.shape[1], 128)


class TestGpuTileMatchingPath(unittest.TestCase):
    def _call_match_tile_gpu(self, left: np.ndarray, right: np.ndarray, mask: np.ndarray):
        return tile_matching._match_tile_gpu(
            left,
            right,
            left_mask=mask,
            right_mask=mask,
            ratio_test=0.75,
            matcher_method="bf",
            max_features=100,
            sift_octave_layers=3,
            sift_contrast_threshold=0.04,
            sift_edge_threshold=10.0,
            sift_sigma=1.6,
        )

    def test_match_tile_gpu_reuses_shared_gpu_sift_pair_matcher(self):
        left = np.zeros((64, 64), dtype=np.uint8)
        right = np.zeros((64, 64), dtype=np.uint8)
        mask = np.ones((64, 64), dtype=np.uint8) * 255
        fake_result = tile_matching.GpuSiftMatchResult(
            left_keypoints=[],
            right_keypoints=[],
            matches=[],
            used_gpu=True,
            used_cpu_fallback=False,
            failure_reason=None,
        )

        with mock.patch.object(tile_matching, "match_sift_pair", return_value=fake_result) as match_mock:
            left_keypoints, right_keypoints, matches = tile_matching._match_tile_gpu(
                left,
                right,
                left_mask=mask,
                right_mask=mask,
                ratio_test=0.75,
                matcher_method="bf",
                max_features=100,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
            )

        self.assertEqual(left_keypoints, [])
        self.assertEqual(right_keypoints, [])
        self.assertEqual(matches, [])
        match_mock.assert_called_once()
        self.assertEqual(match_mock.call_args.kwargs["sift_kwargs"]["nfeatures"], 100)

    def test_match_tile_gpu_returns_empty_triplet_when_left_has_no_features(self):
        left = np.zeros((64, 64), dtype=np.uint8)
        right = np.zeros((64, 64), dtype=np.uint8)
        mask = np.ones((64, 64), dtype=np.uint8) * 255
        fake_right_keypoint = cv2.KeyPoint(1.0, 1.0, 1.0)
        fake_result = tile_matching.GpuSiftMatchResult(
            left_keypoints=[],
            right_keypoints=[fake_right_keypoint],
            matches=[],
            used_gpu=True,
            used_cpu_fallback=False,
            failure_reason=None,
        )

        with mock.patch.object(tile_matching, "match_sift_pair", return_value=fake_result):
            left_keypoints, right_keypoints, matches = self._call_match_tile_gpu(left, right, mask)

        self.assertEqual(left_keypoints, [])
        self.assertEqual(right_keypoints, [])
        self.assertEqual(matches, [])

    def test_match_tile_gpu_preserves_left_features_when_right_has_no_features(self):
        left = np.zeros((64, 64), dtype=np.uint8)
        right = np.zeros((64, 64), dtype=np.uint8)
        mask = np.ones((64, 64), dtype=np.uint8) * 255
        fake_left_keypoint = cv2.KeyPoint(1.0, 1.0, 1.0)
        fake_result = tile_matching.GpuSiftMatchResult(
            left_keypoints=[fake_left_keypoint],
            right_keypoints=[],
            matches=[],
            used_gpu=True,
            used_cpu_fallback=False,
            failure_reason=None,
        )

        with mock.patch.object(tile_matching, "match_sift_pair", return_value=fake_result):
            left_keypoints, right_keypoints, matches = self._call_match_tile_gpu(left, right, mask)

        self.assertEqual(left_keypoints, [fake_left_keypoint])
        self.assertEqual(right_keypoints, [])
        self.assertEqual(matches, [])


class TestGpuPreparedTilePayload(unittest.TestCase):
    def test_prepare_tile_payload_skips_invalid_window_before_gpu(self):
        window = tile_matching.PairedTileWindow(
            local_window=TileWindow(0, 0, 16, 16),
            left_window=TileWindow(0, 0, 16, 16),
            right_window=TileWindow(0, 0, 16, 16),
        )
        left_values = np.zeros((16, 16), dtype=np.float64)
        right_values = np.zeros((16, 16), dtype=np.float64)

        payload_or_result = tile_matching._prepare_gpu_tile_payload_from_values(
            left_values=left_values,
            right_values=right_values,
            local_window=window.local_window,
            left_window=window.left_window,
            right_window=window.right_window,
            minimum_value=None,
            maximum_value=None,
            lower_percent=0.5,
            upper_percent=99.5,
            left_invalid_values=(0.0,),
            right_invalid_values=(0.0,),
            special_pixel_abs_threshold=1.0e300,
            min_valid_pixels=64,
            valid_pixel_percent_threshold=0.05,
            invalid_pixel_radius=1,
        )

        self.assertIsInstance(payload_or_result, tile_matching.TileMatchResult)
        self.assertEqual(payload_or_result.stats.status, "skipped_valid_pixel_ratio_below_threshold")


class TestGpuTileResultFromMatches(unittest.TestCase):
    def _payload(self) -> tile_matching.PreparedGpuTilePayload:
        window = TileWindow(0, 0, 16, 16)
        return tile_matching.PreparedGpuTilePayload(
            local_window=window,
            left_window=window,
            right_window=window,
            left_image=np.zeros((16, 16), dtype=np.uint8),
            right_image=np.zeros((16, 16), dtype=np.uint8),
            left_mask=np.ones((16, 16), dtype=np.uint8) * 255,
            right_mask=np.ones((16, 16), dtype=np.uint8) * 255,
            left_valid_pixel_count=256,
            right_valid_pixel_count=256,
            left_valid_pixel_ratio=1.0,
            right_valid_pixel_ratio=1.0,
        )

    def test_no_keypoints_preserves_skipped_no_features_status(self):
        result = tile_matching._tile_result_from_matches(
            payload=self._payload(),
            left_keypoints=[],
            right_keypoints=[],
            filtered_matches=[],
        )

        self.assertEqual(result.stats.status, "skipped_no_features")

    def test_no_filtered_matches_preserves_skipped_no_matches_status(self):
        keypoint = cv2.KeyPoint(1.0, 1.0, 1.0)

        result = tile_matching._tile_result_from_matches(
            payload=self._payload(),
            left_keypoints=[keypoint],
            right_keypoints=[keypoint],
            filtered_matches=[],
        )

        self.assertEqual(result.stats.status, "skipped_no_matches")


class TestGpuPipelineOrdering(unittest.TestCase):
    def test_order_gpu_results_restores_input_order(self):
        first = tile_matching.TileMatchResult(
            stats=tile_matching.TileMatchStats(0, 0, 16, 16, 0, 0, 0, 0, 16, 16, 1.0, 1.0, 0, 0, 0, "no_features"),
            left_points=(),
            right_points=(),
        )
        second = tile_matching.TileMatchResult(
            stats=tile_matching.TileMatchStats(16, 0, 16, 16, 16, 0, 16, 0, 16, 16, 1.0, 1.0, 0, 0, 0, "no_features"),
            left_points=(),
            right_points=(),
        )

        ordered = tile_matching._order_indexed_tile_results([(1, second), (0, first)])

        self.assertEqual(ordered, [first, second])


class TestGpuPipelineRouting(unittest.TestCase):
    def _make_gpu_task(self) -> tile_matching.TileMatchTask:
        return tile_matching.TileMatchTask(
            left_dom_path="left.cub",
            right_dom_path="right.cub",
            band=1,
            paired_window=tile_matching.PairedTileWindow(
                local_window=TileWindow(0, 0, 16, 16),
                left_window=TileWindow(0, 0, 16, 16),
                right_window=TileWindow(0, 0, 16, 16),
            ),
            minimum_value=None,
            maximum_value=None,
            lower_percent=0.5,
            upper_percent=99.5,
            invalid_values=(),
            special_pixel_abs_threshold=1.0e300,
            min_valid_pixels=64,
            valid_pixel_percent_threshold=0.05,
            invalid_pixel_radius=1,
            ratio_test=0.75,
            matcher_method="bf",
            max_features=100,
            sift_octave_layers=3,
            sift_contrast_threshold=0.04,
            sift_edge_threshold=10.0,
            sift_sigma=1.6,
            use_gpu=True,
            gpu_batch_size=4,
        )

    def test_gpu_parallel_route_reports_gpu_backend_summary(self):
        summary = image_match._tile_execution_backend_summary(
            use_parallel_cpu=True,
            use_gpu=True,
            candidate_window_count=2,
            resolved_num_worker_parallel_cpu=8,
        )

        self.assertFalse(summary["parallel_cpu_used"])
        self.assertEqual(summary["parallel_cpu_backend"], "gpu_tile_pipeline")
        self.assertEqual(summary["tile_match_backend"], "gpu_tile_pipeline")
        self.assertEqual(summary["parallel_cpu_worker_count"], 0)

    def test_default_gpu_batch_size_is_conservative(self):
        self.assertEqual(tile_matching.TileMatchTask.__dataclass_fields__["gpu_batch_size"].default, 4)

        task = self._make_gpu_task()
        task_with_default = tile_matching.TileMatchTask(
            **{field: getattr(task, field) for field in task.__dataclass_fields__ if field != "gpu_batch_size"}
        )

        self.assertEqual(task_with_default.gpu_batch_size, 4)

    def test_effective_gpu_route_requires_cuda_bf_and_homogeneous_gpu_tasks(self):
        gpu_task = self._make_gpu_task()
        cpu_task = tile_matching.TileMatchTask(
            **{
                field: (False if field == "use_gpu" else getattr(gpu_task, field))
                for field in gpu_task.__dataclass_fields__
            }
        )
        flann_task = tile_matching.TileMatchTask(
            **{
                field: ("flann" if field == "matcher_method" else getattr(gpu_task, field))
                for field in gpu_task.__dataclass_fields__
            }
        )

        with mock.patch.object(tile_matching, "HAS_GPU_SIFT", True):
            self.assertTrue(tile_matching._can_use_dedicated_gpu_tile_route([gpu_task]))
            self.assertFalse(tile_matching._can_use_dedicated_gpu_tile_route([flann_task]))
            with self.assertRaisesRegex(ValueError, "mixed CPU/GPU"):
                tile_matching._can_use_dedicated_gpu_tile_route([gpu_task, cpu_task])

        with mock.patch.object(tile_matching, "HAS_GPU_SIFT", False):
            self.assertFalse(tile_matching._can_use_dedicated_gpu_tile_route([gpu_task]))

    def test_run_gpu_tile_match_tasks_closes_left_cube_when_right_open_fails(self):
        task = self._make_gpu_task()

        class FakeCube:
            def __init__(self, *, fail_open: bool = False):
                self.fail_open = fail_open
                self.open_called = False
                self.close_called = False
                self._open = False

            def open(self, *_args):
                self.open_called = True
                if self.fail_open:
                    raise RuntimeError("right open failed")
                self._open = True

            def is_open(self):
                return self._open

            def close(self):
                self.close_called = True
                self._open = False

        left_cube = FakeCube()
        right_cube = FakeCube(fail_open=True)

        with mock.patch.object(tile_matching.ip, "Cube", side_effect=[left_cube, right_cube]):
            with self.assertRaisesRegex(RuntimeError, "right open failed"):
                tile_matching._run_gpu_tile_match_tasks([task], show_progress=False)

        self.assertTrue(left_cube.open_called)
        self.assertTrue(right_cube.open_called)
        self.assertTrue(left_cube.close_called)
        self.assertFalse(right_cube.close_called)

    def test_match_dom_pair_closes_left_cube_when_right_open_fails(self):
        class FakeCube:
            def __init__(self, *, fail_open: bool = False):
                self.fail_open = fail_open
                self.open_called = False
                self.close_called = False
                self._open = False

            def open(self, *_args):
                self.open_called = True
                if self.fail_open:
                    raise RuntimeError("right open failed")
                self._open = True

            def is_open(self):
                return self._open

            def close(self):
                self.close_called = True
                self._open = False

        left_cube = FakeCube()
        right_cube = FakeCube(fail_open=True)

        with mock.patch.object(image_match.ip, "Cube", side_effect=[left_cube, right_cube]):
            with self.assertRaisesRegex(RuntimeError, "right open failed"):
                image_match.match_dom_pair("left.cub", "right.cub")

        self.assertTrue(left_cube.open_called)
        self.assertTrue(right_cube.open_called)
        self.assertTrue(left_cube.close_called)
        self.assertFalse(right_cube.close_called)

    def test_dynamic_gpu_batch_clamps_default_task_batch_to_maximum(self):
        task = tile_matching.TileMatchTask(
            left_dom_path="left.cub",
            right_dom_path="right.cub",
            band=1,
            paired_window=tile_matching.PairedTileWindow(
                local_window=TileWindow(0, 0, 16, 16),
                left_window=TileWindow(0, 0, 16, 16),
                right_window=TileWindow(0, 0, 16, 16),
            ),
            minimum_value=None,
            maximum_value=None,
            lower_percent=0.5,
            upper_percent=99.5,
            invalid_values=(),
            special_pixel_abs_threshold=1.0e300,
            min_valid_pixels=64,
            valid_pixel_percent_threshold=0.05,
            invalid_pixel_radius=1,
            ratio_test=0.75,
            matcher_method="bf",
            max_features=100,
            sift_octave_layers=3,
            sift_contrast_threshold=0.04,
            sift_edge_threshold=10.0,
            sift_sigma=1.6,
            use_gpu=True,
            gpu_batch_size=32,
        )
        payload = tile_matching.PreparedGpuTilePayload(
            local_window=task.paired_window.local_window,
            left_window=task.paired_window.left_window,
            right_window=task.paired_window.right_window,
            left_image=np.zeros((16, 16), dtype=np.uint8),
            right_image=np.zeros((16, 16), dtype=np.uint8),
            left_mask=np.ones((16, 16), dtype=np.uint8) * 255,
            right_mask=np.ones((16, 16), dtype=np.uint8) * 255,
            left_valid_pixel_count=256,
            right_valid_pixel_count=256,
            left_valid_pixel_ratio=1.0,
            right_valid_pixel_ratio=1.0,
        )

        class FakeCube:
            def __init__(self):
                self._open = False

            def open(self, *_args):
                self._open = True

            def is_open(self):
                return self._open

            def close(self):
                self._open = False

        with mock.patch.object(tile_matching.ip, "Cube", side_effect=[FakeCube(), FakeCube()]), mock.patch.object(
            tile_matching,
            "_read_cube_window",
            return_value=np.zeros((16, 16), dtype=np.float64),
        ), mock.patch.object(
            tile_matching,
            "_resolved_invalid_values_for_cube",
            return_value=(),
        ), mock.patch.object(
            tile_matching,
            "_prepare_gpu_tile_payload_from_values",
            return_value=payload,
        ), mock.patch.object(
            tile_matching,
            "_match_tile_gpu",
            return_value=([], [], []),
        ):
            results = tile_matching._run_gpu_tile_match_tasks(
                [task],
                show_progress=False,
                gpu_dynamic_batch=True,
                gpu_min_batch_size=2,
                gpu_max_batch_size=16,
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].stats.status, "skipped_no_features")

    def test_run_gpu_tile_match_tasks_records_fallback_stats(self):
        task = self._make_gpu_task()
        payload = tile_matching.PreparedGpuTilePayload(
            local_window=task.paired_window.local_window,
            left_window=task.paired_window.left_window,
            right_window=task.paired_window.right_window,
            left_image=np.zeros((16, 16), dtype=np.uint8),
            right_image=np.zeros((16, 16), dtype=np.uint8),
            left_mask=np.ones((16, 16), dtype=np.uint8) * 255,
            right_mask=np.ones((16, 16), dtype=np.uint8) * 255,
            left_valid_pixel_count=256,
            right_valid_pixel_count=256,
            left_valid_pixel_ratio=1.0,
            right_valid_pixel_ratio=1.0,
        )
        stats = tile_matching.GpuSiftStats()

        class FakeCube:
            def __init__(self):
                self._open = False

            def open(self, *_args):
                self._open = True

            def is_open(self):
                return self._open

            def close(self):
                self._open = False

        fallback_result = tile_matching.GpuSiftMatchResult(
            left_keypoints=[],
            right_keypoints=[],
            matches=[],
            used_gpu=False,
            used_cpu_fallback=True,
            failure_reason="CUDA out of memory",
        )

        with mock.patch.object(tile_matching.ip, "Cube", side_effect=[FakeCube(), FakeCube()]), mock.patch.object(
            tile_matching,
            "_read_cube_window",
            return_value=np.zeros((16, 16), dtype=np.float64),
        ), mock.patch.object(
            tile_matching,
            "_resolved_invalid_values_for_cube",
            return_value=(),
        ), mock.patch.object(
            tile_matching,
            "_prepare_gpu_tile_payload_from_values",
            return_value=payload,
        ), mock.patch.object(
            tile_matching,
            "match_sift_pairs",
            return_value=[fallback_result],
        ):
            tile_matching._run_gpu_tile_match_tasks(
                [task],
                show_progress=False,
                gpu_dynamic_batch=True,
                gpu_min_batch_size=2,
                gpu_max_batch_size=16,
                gpu_stats=stats,
            )

        self.assertEqual(stats.gpu_pair_count, 1)
        self.assertEqual(stats.cpu_fallback_pair_count, 1)
        self.assertEqual(stats.gpu_failure_count, 1)

    def test_run_gpu_tile_match_tasks_dispatches_homogeneous_payloads_as_batch(self):
        tasks = [self._make_gpu_task(), self._make_gpu_task()]
        payloads = [
            tile_matching.PreparedGpuTilePayload(
                local_window=task.paired_window.local_window,
                left_window=task.paired_window.left_window,
                right_window=task.paired_window.right_window,
                left_image=np.zeros((16, 16), dtype=np.uint8),
                right_image=np.zeros((16, 16), dtype=np.uint8),
                left_mask=np.ones((16, 16), dtype=np.uint8) * 255,
                right_mask=np.ones((16, 16), dtype=np.uint8) * 255,
                left_valid_pixel_count=256,
                right_valid_pixel_count=256,
                left_valid_pixel_ratio=1.0,
                right_valid_pixel_ratio=1.0,
            )
            for task in tasks
        ]
        batch_results = [
            tile_matching.GpuSiftMatchResult([], [], [], used_gpu=True, used_cpu_fallback=False),
            tile_matching.GpuSiftMatchResult([], [], [], used_gpu=True, used_cpu_fallback=False),
        ]

        class FakeCube:
            def __init__(self):
                self._open = False

            def open(self, *_args):
                self._open = True

            def is_open(self):
                return self._open

            def close(self):
                self._open = False

        with mock.patch.object(
            tile_matching.ip,
            "Cube",
            side_effect=[FakeCube(), FakeCube(), FakeCube(), FakeCube()],
        ), mock.patch.object(
            tile_matching,
            "_read_cube_window",
            return_value=np.zeros((16, 16), dtype=np.float64),
        ), mock.patch.object(
            tile_matching,
            "_resolved_invalid_values_for_cube",
            return_value=(),
        ), mock.patch.object(
            tile_matching,
            "_prepare_gpu_tile_payload_from_values",
            side_effect=payloads,
        ), mock.patch.object(
            tile_matching,
            "match_sift_pairs",
            return_value=batch_results,
        ) as batch_matcher:
            results = tile_matching._run_gpu_tile_match_tasks(
                tasks,
                show_progress=False,
                gpu_dynamic_batch=False,
            )

        self.assertEqual(len(results), 2)
        batch_matcher.assert_called_once()
        self.assertEqual(len(batch_matcher.call_args.args[0]), 2)

    def test_run_parallel_tasks_invokes_progress_callback_for_each_gpu_task(self):
        def make_gpu_task(start_x: int) -> tile_matching.TileMatchTask:
            return tile_matching.TileMatchTask(
                left_dom_path="left.cub",
                right_dom_path="right.cub",
                band=1,
                paired_window=tile_matching.PairedTileWindow(
                    local_window=TileWindow(start_x, 0, 16, 16),
                    left_window=TileWindow(start_x, 0, 16, 16),
                    right_window=TileWindow(start_x, 0, 16, 16),
                ),
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=64,
                valid_pixel_percent_threshold=0.05,
                invalid_pixel_radius=1,
                ratio_test=0.75,
                matcher_method="bf",
                max_features=100,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                use_gpu=True,
                gpu_batch_size=4,
            )

        def make_result(start_x: int) -> tile_matching.TileMatchResult:
            return tile_matching.TileMatchResult(
                stats=tile_matching.TileMatchStats(
                    local_start_x=start_x,
                    local_start_y=0,
                    width=16,
                    height=16,
                    left_start_x=start_x,
                    left_start_y=0,
                    right_start_x=start_x,
                    right_start_y=0,
                    left_valid_pixel_count=256,
                    right_valid_pixel_count=256,
                    left_valid_pixel_ratio=1.0,
                    right_valid_pixel_ratio=1.0,
                    left_feature_count=0,
                    right_feature_count=0,
                    match_count=0,
                    status="skipped_valid_pixel_ratio_below_threshold",
                ),
                left_points=(),
                right_points=(),
            )

        class FakeCube:
            def __init__(self):
                self._open = False

            def open(self, *_args):
                self._open = True

            def is_open(self):
                return self._open

            def close(self):
                self._open = False

        callback = mock.Mock()

        with mock.patch.object(tile_matching, "HAS_GPU_SIFT", True), mock.patch.object(
            tile_matching.ip, "Cube", side_effect=[FakeCube(), FakeCube(), FakeCube(), FakeCube()]
        ), mock.patch.object(
            tile_matching,
            "_read_cube_window",
            return_value=np.zeros((16, 16), dtype=np.float64),
        ), mock.patch.object(
            tile_matching,
            "_resolved_invalid_values_for_cube",
            return_value=(),
        ), mock.patch.object(
            tile_matching,
            "_prepare_gpu_tile_payload_from_values",
            side_effect=[make_result(0), make_result(16)],
        ):
            tile_matching._run_parallel_tile_match_tasks(
                [make_gpu_task(0), make_gpu_task(16)],
                max_workers=2,
                show_progress=False,
                progress_callback=callback,
            )

        self.assertEqual(callback.call_count, 2)

    def test_run_parallel_tasks_uses_gpu_pipeline_when_requested(self):
        tasks = [
            tile_matching.TileMatchTask(
                left_dom_path="left.cub",
                right_dom_path="right.cub",
                band=1,
                paired_window=tile_matching.PairedTileWindow(
                    local_window=TileWindow(0, 0, 16, 16),
                    left_window=TileWindow(0, 0, 16, 16),
                    right_window=TileWindow(0, 0, 16, 16),
                ),
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=64,
                valid_pixel_percent_threshold=0.05,
                invalid_pixel_radius=1,
                ratio_test=0.75,
                matcher_method="bf",
                max_features=100,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                use_gpu=True,
                gpu_batch_size=4,
            )
        ]
        expected = []

        with mock.patch.object(tile_matching, "HAS_GPU_SIFT", True), mock.patch.object(
            tile_matching, "_run_gpu_tile_match_tasks", return_value=expected
        ) as gpu_mock:
            result = tile_matching._run_parallel_tile_match_tasks(
                tasks,
                max_workers=2,
                show_progress=False,
            )

        self.assertIs(result, expected)
        gpu_mock.assert_called_once()

    def test_run_parallel_tasks_forwards_dynamic_gpu_batch_options(self):
        tasks = [
            tile_matching.TileMatchTask(
                left_dom_path="left.cub",
                right_dom_path="right.cub",
                band=1,
                paired_window=tile_matching.PairedTileWindow(
                    local_window=TileWindow(0, 0, 16, 16),
                    left_window=TileWindow(0, 0, 16, 16),
                    right_window=TileWindow(0, 0, 16, 16),
                ),
                minimum_value=None,
                maximum_value=None,
                lower_percent=0.5,
                upper_percent=99.5,
                invalid_values=(),
                special_pixel_abs_threshold=1.0e300,
                min_valid_pixels=64,
                valid_pixel_percent_threshold=0.05,
                invalid_pixel_radius=1,
                ratio_test=0.75,
                matcher_method="bf",
                max_features=100,
                sift_octave_layers=3,
                sift_contrast_threshold=0.04,
                sift_edge_threshold=10.0,
                sift_sigma=1.6,
                use_gpu=True,
                gpu_batch_size=4,
            )
        ]
        expected = []

        with mock.patch.object(tile_matching, "HAS_GPU_SIFT", True), mock.patch.object(
            tile_matching, "_run_gpu_tile_match_tasks", return_value=expected
        ) as gpu_mock:
            result = tile_matching._run_parallel_tile_match_tasks(
                tasks,
                max_workers=2,
                show_progress=False,
                gpu_dynamic_batch=False,
                gpu_min_batch_size=3,
                gpu_max_batch_size=7,
            )

        self.assertIs(result, expected)
        gpu_mock.assert_called_once_with(
            tasks,
            show_progress=False,
            progress_callback=None,
            gpu_dynamic_batch=False,
            gpu_min_batch_size=3,
            gpu_max_batch_size=7,
            gpu_stats=None,
        )

    def test_run_parallel_tasks_rejects_mixed_cpu_gpu_tasks(self):
        gpu_task = self._make_gpu_task()
        cpu_task = tile_matching.TileMatchTask(
            **{
                field: (False if field == "use_gpu" else getattr(gpu_task, field))
                for field in gpu_task.__dataclass_fields__
            }
        )

        with self.assertRaisesRegex(ValueError, "mixed CPU/GPU"):
            tile_matching._run_parallel_tile_match_tasks(
                [gpu_task, cpu_task],
                max_workers=2,
                show_progress=False,
            )

    def test_run_parallel_tasks_rejects_image_space_mismatch(self):
        base_task = self._make_gpu_task()
        task = tile_matching.TileMatchTask(
            **{
                field: ("ori" if field == "image_space" else getattr(base_task, field))
                for field in base_task.__dataclass_fields__
            }
        )

        with self.assertRaisesRegex(ValueError, "Mismatched image_space"):
            tile_matching._run_parallel_tile_match_tasks(
                [task],
                image_space="dom",
                max_workers=2,
                show_progress=False,
            )


class TestGpuSummaryFields(unittest.TestCase):
    def test_gpu_summary_defaults_when_gpu_disabled(self):
        summary = image_match._gpu_execution_summary(
            use_gpu=False,
            gpu_batch_size=4,
            gpu_dynamic_batch=True,
            gpu_min_batch_size=2,
            gpu_max_batch_size=16,
        )

        self.assertEqual(summary["enabled"], False)
        self.assertEqual(summary["batch_size"], 4)
        self.assertEqual(summary["dynamic_batch"], True)
        self.assertEqual(summary["min_batch_size"], 2)
        self.assertEqual(summary["max_batch_size"], 16)

    def test_gpu_summary_includes_runtime_stats_when_available(self):
        stats = tile_matching.GpuSiftStats()
        stats.record_batch(batch_size=4, used_gpu=True)
        stats.record_pair_result(used_cpu_fallback=False)
        stats.record_pair_result(used_cpu_fallback=True)
        stats.record_gpu_failure()

        summary = image_match._gpu_execution_summary(
            use_gpu=True,
            gpu_batch_size=4,
            gpu_dynamic_batch=True,
            gpu_min_batch_size=2,
            gpu_max_batch_size=16,
            gpu_stats=stats,
        )

        self.assertEqual(summary["runtime"]["gpu_batch_count"], 1)
        self.assertEqual(summary["runtime"]["gpu_pair_count"], 2)
        self.assertEqual(summary["runtime"]["cpu_fallback_pair_count"], 1)
        self.assertEqual(summary["runtime"]["gpu_failure_count"], 1)
        self.assertEqual(summary["runtime"]["batch_size_histogram"], {4: 1})

    def test_gpu_summary_distinguishes_requested_from_effective_execution(self):
        summary = image_match._gpu_execution_summary(
            use_gpu=True,
            gpu_effective=False,
            gpu_batch_size=4,
            gpu_dynamic_batch=True,
            gpu_min_batch_size=2,
            gpu_max_batch_size=16,
        )

        self.assertTrue(summary["requested"])
        self.assertFalse(summary["enabled"])


class TestGpuBenchmarkScript(unittest.TestCase):
    def test_benchmark_summary_reports_point_and_tile_match_counts_separately(self):
        spec = importlib.util.spec_from_file_location(
            "benchmark_gpu_tile_pipeline",
            PROJECT_ROOT / "scripts" / "benchmark_gpu_tile_pipeline.py",
        )
        benchmark_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(benchmark_module)

        summary = {
            "point_count": 3,
            "matched_tile_count": 2,
            "gpu": {"enabled": True},
            "tiles": [
                {"match_count": 5},
                {"match_count": 7},
            ],
        }

        result = benchmark_module._summarize_benchmark_case(
            summary,
            elapsed_seconds=1.25,
            use_gpu=True,
        )

        self.assertEqual(result["point_count"], 3)
        self.assertEqual(result["tile_match_count_total"], 12)
        self.assertNotIn("total_match_count", result)


if __name__ == "__main__":
    unittest.main()
