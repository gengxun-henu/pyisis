"""Focused unit tests for deep adapter invalid-mask propagation.

Author: Geng Xun
Created: 2026-05-19
Last Modified: 2026-05-19
Updated: 2026-05-19  Geng Xun added focused coverage for pre-match feature filtering and LoFTR mask passthrough.
Updated: 2026-05-19  Geng Xun added runtime config storage coverage for deep matcher adapters.
Updated: 2026-05-19  Geng Xun added feature extractor runtime config coverage for SuperPoint and explicit unsupported extractor errors.
Updated: 2026-05-19  Geng Xun added matcher runtime option forwarding coverage for LightGlue/LoFTR/SuperGlue adapters.
Updated: 2026-05-19  Geng Xun added regression coverage for deep matcher device dtype application and surfaced ignored device options.
Updated: 2026-05-19  Geng Xun added fail-fast compatibility coverage for invalid matcher and extractor combinations.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import sys
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
for import_path in (PROJECT_ROOT, EXAMPLES_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from image_match.deep_adapter import DeepMatcherAdapter
from image_match.deep_frontends import DeepFrontendError, OfficialLightGlueFrontend, SuperPointFrontend
from controlnet_construct.deep_match_config import DeepMatchRuntimeConfig


class _CapturingFeatureMatcher:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def match(self, **kwargs):
        self.calls.append(kwargs)
        features_left = kwargs["features_left"]
        features_right = kwargs["features_right"]
        left_points = np.asarray(features_left["keypoints"], dtype=np.float32).reshape(-1, 2)
        right_points = np.asarray(features_right["keypoints"], dtype=np.float32).reshape(-1, 2)
        pair_count = min(left_points.shape[0], right_points.shape[0])
        return (
            left_points[:pair_count],
            right_points[:pair_count],
            np.ones((pair_count,), dtype=np.float32),
        )


class _CapturingLoFTRMatcher:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def match(self, **kwargs):
        self.calls.append(kwargs)
        return (
            np.zeros((0, 2), dtype=np.float32),
            np.zeros((0, 2), dtype=np.float32),
            np.zeros((0,), dtype=np.float32),
        )


class _DTypeTrackingModule:
    def __init__(self) -> None:
        self.device: object | None = None
        self.dtype: object | None = None

    def eval(self):
        return self

    def to(self, *args, **kwargs):
        if args:
            self.device = args[0]
        if "device" in kwargs:
            self.device = kwargs["device"]
        if "dtype" in kwargs:
            self.dtype = kwargs["dtype"]
        return self


class _OfficialExtractorStub:
    instances: list["_OfficialExtractorStub"] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.device = None
        self.constructor_name = None
        self.input_shapes: list[tuple[int, ...]] = []
        type(self).instances.append(self)

    def eval(self):
        return self

    def to(self, device):
        self.device = device
        return self

    def extract(self, image):
        import torch

        self.input_shapes.append(tuple(image.shape))
        return {
            "keypoints": torch.tensor([[[1.0, 2.0], [3.0, 4.0]]], dtype=torch.float32, device=image.device),
            "descriptors": torch.tensor([[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]], dtype=torch.float32, device=image.device),
            "scores": torch.tensor([[0.7, 0.8]], dtype=torch.float32, device=image.device),
        }


class ImageMatchDeepAdapterUnitTest(unittest.TestCase):
    def test_official_lightglue_frontend_builds_expected_extractors_and_channel_shapes(self):
        import torch

        def build_constructor(constructor_name):
            def constructor(**kwargs):
                extractor = _OfficialExtractorStub(**kwargs)
                extractor.constructor_name = constructor_name
                return extractor

            return constructor

        fake_lightglue = SimpleNamespace(
            SuperPoint=build_constructor("SuperPoint"),
            DISK=build_constructor("DISK"),
            ALIKED=build_constructor("ALIKED"),
            DoGHardNet=build_constructor("DoGHardNet"),
            SIFT=build_constructor("SIFT"),
        )

        for method, expected_constructor, expected_channels in (
            ("superpoint", "SuperPoint", 1),
            ("disk", "DISK", 3),
            ("aliked", "ALIKED", 3),
            ("doghardnet", "DoGHardNet", 1),
            ("lightglue_sift", "SIFT", 1),
        ):
            with self.subTest(method=method):
                _OfficialExtractorStub.instances = []
                with mock.patch.dict(sys.modules, {"torch": torch, "lightglue": fake_lightglue}, clear=False):
                    frontend = OfficialLightGlueFrontend(
                        feature_extractor_method=method,
                        feature_options={"max_features": 123},
                    )
                    features = frontend.extract(np.arange(16, dtype=np.float32).reshape(4, 4), device="cpu")

                self.assertEqual(len(_OfficialExtractorStub.instances), 1)
                extractor = _OfficialExtractorStub.instances[0]
                self.assertEqual(extractor.constructor_name, expected_constructor)
                self.assertEqual(extractor.kwargs["max_num_keypoints"], 123)
                self.assertEqual(extractor.device, "cpu")
                self.assertEqual(extractor.input_shapes, [(1, expected_channels, 4, 4)])
                self.assertEqual(features["keypoints"].shape, (2, 2))
                self.assertEqual(features["descriptors"].shape[0], 2)

    def test_official_lightglue_frontend_rejects_feature_alias_conflict(self):
        with self.assertRaisesRegex(ValueError, r"max_features.*max_keypoints"):
            OfficialLightGlueFrontend(
                feature_extractor_method="superpoint",
                feature_options={"max_features": 123, "max_keypoints": 456},
            )

    def test_superpoint_frontend_reads_runtime_config_parameters(self):
        runtime = DeepMatchRuntimeConfig(
            matcher_method="lightglue",
            feature_extractor_method="superpoint",
            prefer_gpu=False,
            device_dtype="float32",
            fallback_on_error="sift_flann",
            raw_config={
                "feature_extractor": {
                    "method": "superpoint",
                    "max_keypoints": 4096,
                    "keypoint_threshold": 0.0005,
                    "nms_radius": 4,
                    "remove_borders": 4,
                }
            },
        )

        frontend = SuperPointFrontend(runtime_config=runtime)

        self.assertEqual(frontend.requested_parameters["max_keypoints"], 4096)
        self.assertAlmostEqual(frontend.requested_parameters["keypoint_threshold"], 0.0005)
        self.assertEqual(frontend.requested_parameters["nms_radius"], 4)
        self.assertIn("remove_borders", frontend.ignored_parameters)

    def test_deep_matcher_adapter_passes_runtime_config_to_superpoint_frontend(self):
        runtime = DeepMatchRuntimeConfig(
            matcher_method="lightglue",
            feature_extractor_method="superpoint",
            prefer_gpu=False,
            device_dtype="float32",
            fallback_on_error="sift_flann",
            raw_config={"feature_extractor": {"method": "superpoint", "max_keypoints": 4096}},
        )

        with mock.patch("image_match.deep_adapter.SuperPointFrontend") as frontend_constructor:
            adapter = DeepMatcherAdapter(prefer_gpu=True, runtime_config=runtime)

        frontend_constructor.assert_called_once_with(runtime_config=runtime)
        self.assertIs(adapter._runtime_config, runtime)

    def test_deep_matcher_adapter_stores_runtime_config(self):
        runtime = DeepMatchRuntimeConfig(
            matcher_method="lightglue",
            feature_extractor_method="superpoint",
            prefer_gpu=False,
            device_dtype="float32",
            fallback_on_error="sift_flann",
            raw_config={"matcher": {"method": "lightglue"}},
        )

        adapter = DeepMatcherAdapter(prefer_gpu=True, runtime_config=runtime)

        self.assertIs(adapter._runtime_config, runtime)
        self.assertEqual(adapter._device, "cpu")

    def test_deep_matcher_adapter_passes_matcher_options_to_matcher_builder(self):
        runtime = SimpleNamespace(
            prefer_gpu=False,
            matcher_method="lightglue",
            feature_extractor_method="superpoint",
            matcher_options={"weights": "superpoint_lightglue", "flash": False, "prune_threshold": 2},
            feature_options={"max_keypoints": 4096, "keypoint_threshold": 0.0005},
            device_options={"prefer_gpu": False, "dtype": "float32", "batch_inference": True},
        )
        adapter = DeepMatcherAdapter(prefer_gpu=True, runtime_config=runtime)
        matcher = _CapturingFeatureMatcher()
        left_features = {"keypoints": np.array([[1.0, 1.0]], dtype=np.float32)}
        right_features = {"keypoints": np.array([[2.0, 2.0]], dtype=np.float32)}

        with mock.patch.object(adapter._superpoint, "extract", side_effect=[left_features, right_features]), mock.patch(
            "image_match.deep_adapter.build_deep_matcher",
            return_value=matcher,
        ) as build_matcher_mock:
            adapter.match_pair(
                matcher_method="lightglue",
                left_image=np.zeros((8, 8), dtype=np.float32),
                right_image=np.zeros((8, 8), dtype=np.float32),
            )

        build_matcher_mock.assert_called_once_with(
            "lightglue",
            device="cpu",
            feature_extractor_method="superpoint",
            matcher_options={"weights": "superpoint_lightglue", "flash": False, "prune_threshold": 2},
            feature_options={"max_keypoints": 4096, "keypoint_threshold": 0.0005},
            device_options={"prefer_gpu": False, "dtype": "float32", "batch_inference": True},
        )

    def test_deep_matcher_adapter_uses_official_lightglue_frontend_when_backend_is_official(self):
        runtime = SimpleNamespace(
            prefer_gpu=False,
            matcher_method="lightglue",
            feature_extractor_method="disk",
            matcher_options={"backend": "official", "filter_threshold": 0.05},
            feature_options={"max_features": 64},
            device_options={"prefer_gpu": False, "dtype": "float32"},
        )
        matcher = _CapturingFeatureMatcher()
        frontend = mock.Mock()
        left_features = {
            "keypoints": np.array([[1.0, 1.0], [4.0, 4.0]], dtype=np.float32),
            "descriptors": np.array([[10.0, 11.0], [20.0, 21.0]], dtype=np.float32),
            "scales": np.array([1.5, 2.5], dtype=np.float32),
            "image_size": np.array([8.0, 8.0], dtype=np.float32),
            "scores": np.array([0.1, 0.2], dtype=np.float32),
        }
        right_features = {
            "keypoints": np.array([[2.0, 2.0], [5.0, 5.0]], dtype=np.float32),
            "descriptors": np.array([[12.0, 13.0], [22.0, 23.0]], dtype=np.float32),
            "scales": np.array([3.5, 4.5], dtype=np.float32),
            "image_size": np.array([8.0, 8.0], dtype=np.float32),
            "scores": np.array([0.4, 0.5], dtype=np.float32),
        }
        frontend.extract.side_effect = [left_features, right_features]
        left_mask = np.zeros((8, 8), dtype=bool)
        left_mask[4, 4] = True

        with mock.patch("image_match.deep_adapter.OfficialLightGlueFrontend", return_value=frontend) as frontend_constructor, mock.patch(
            "image_match.deep_adapter.build_deep_matcher",
            return_value=matcher,
        ) as build_matcher_mock:
            adapter = DeepMatcherAdapter(prefer_gpu=True, runtime_config=runtime)
            adapter.match_pair(
                matcher_method="lightglue",
                left_image=np.zeros((8, 8), dtype=np.float32),
                right_image=np.zeros((8, 8), dtype=np.float32),
                left_mask=left_mask,
            )

        frontend_constructor.assert_called_once_with(
            feature_extractor_method="disk",
            feature_options={"max_features": 64},
        )
        self.assertEqual(frontend.extract.call_count, 2)
        for extract_call in frontend.extract.call_args_list:
            np.testing.assert_allclose(extract_call.args[0], np.zeros((8, 8), dtype=np.float32))
            self.assertEqual(extract_call.kwargs["device"], "cpu")
        build_matcher_mock.assert_called_once_with(
            "lightglue",
            device="cpu",
            feature_extractor_method="disk",
            matcher_options={"backend": "official", "filter_threshold": 0.05},
            feature_options={"max_features": 64},
            device_options={"prefer_gpu": False, "dtype": "float32"},
        )
        self.assertEqual(len(matcher.calls), 1)
        np.testing.assert_allclose(matcher.calls[0]["features_left"]["keypoints"], np.array([[1.0, 1.0]], dtype=np.float32))
        np.testing.assert_allclose(matcher.calls[0]["features_left"]["scales"], np.array([1.5], dtype=np.float32))
        np.testing.assert_allclose(matcher.calls[0]["features_left"]["image_size"], left_features["image_size"])
        np.testing.assert_allclose(matcher.calls[0]["features_right"]["keypoints"], right_features["keypoints"])

    def test_image_match_lightglue_applies_dtype_and_surfaces_ignored_device_options(self):
        deep_matchers_module = __import__("image_match.deep_matchers", fromlist=["build_deep_matcher"])
        lightglue_backend = _DTypeTrackingModule()
        lightglue_constructor = mock.Mock(return_value=lightglue_backend)
        torch_module = SimpleNamespace(float32="torch.float32")
        lightglue_module = SimpleNamespace(LightGlue=lightglue_constructor)

        with mock.patch.dict(sys.modules, {"torch": torch_module, "lightglue": lightglue_module}, clear=False):
            matcher = deep_matchers_module.build_deep_matcher(
                "lightglue",
                device="cpu",
                feature_extractor_method="superpoint",
                matcher_options={"weights": "superpoint_lightglue"},
                device_options={"dtype": "float32", "batch_inference": True},
            )
            matcher._load_matcher()

        self.assertEqual(lightglue_backend.device, "cpu")
        self.assertEqual(lightglue_backend.dtype, "torch.float32")
        self.assertIn("device.batch_inference", matcher.ignored_parameters)

    def test_build_deep_matcher_rejects_incompatible_extractor_combinations(self):
        deep_matchers_module = __import__("image_match.deep_matchers", fromlist=["build_deep_matcher"])

        for matcher_method, extractor_method, supported in (
            ("lightglue", "disk", "superpoint"),
            ("superglue", "aliked", "superpoint"),
            ("loftr", "superpoint", "loftr"),
        ):
            with self.subTest(matcher=matcher_method, extractor=extractor_method):
                with self.assertRaisesRegex(
                    deep_matchers_module.DeepMatcherError,
                    rf"matcher\.method='{matcher_method}'.*feature_extractor\.method.*'{supported}'.*'{extractor_method}'",
                ):
                    deep_matchers_module.build_deep_matcher(
                        matcher_method,
                        device="cpu",
                        feature_extractor_method=extractor_method,
                    )

    def test_build_deep_matcher_defaults_loftr_extractor_for_loftr(self):
        deep_matchers_module = __import__("image_match.deep_matchers", fromlist=["build_deep_matcher"])

        matcher = deep_matchers_module.build_deep_matcher("loftr", device="cpu")

        self.assertEqual(matcher.feature_extractor_method, "loftr")

    def test_deep_matcher_adapter_rejects_invalid_runtime_config_early(self):
        runtime = SimpleNamespace(
            prefer_gpu=False,
            matcher_method="loftr",
            feature_extractor_method="superpoint",
            matcher_options={"pretrained": "outdoor"},
            feature_options={"max_keypoints": 2048},
            device_options={"prefer_gpu": False, "dtype": "float32"},
        )

        with self.assertRaisesRegex(
            ValueError,
            r"matcher\.method='loftr'.*feature_extractor\.method.*'loftr'.*'superpoint'",
        ):
            DeepMatcherAdapter(prefer_gpu=False, runtime_config=runtime)

    def test_lightglue_non_superpoint_presets_fail_during_config_resolution(self):
        config_module = __import__("controlnet_construct.deep_match_config", fromlist=["resolve_deep_match_runtime_config"])

        for preset_name, extractor_method in (
            ("lightglue_aliked.json", "aliked"),
            ("lightglue_disk.json", "disk"),
            ("lightglue_doghardnet.json", "doghardnet"),
        ):
            with self.subTest(preset=preset_name):
                with self.assertRaisesRegex(
                    ValueError,
                    rf"matcher\.method='lightglue'.*feature_extractor\.method.*'superpoint'.*'{extractor_method}'",
                ):
                    config_module.resolve_deep_match_runtime_config(
                        PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / preset_name
                    )

    def test_match_pair_filters_superpoint_features_before_matching(self):
        adapter = DeepMatcherAdapter(prefer_gpu=False)
        left_features = {
            "keypoints": np.array([[1.0, 1.0], [4.0, 4.0], [7.0, 7.0]], dtype=np.float32),
            "descriptors": np.array(
                [[10.0, 11.0], [20.0, 21.0], [30.0, 31.0]],
                dtype=np.float32,
            ),
            "scores": np.array([0.1, 0.2, 0.3], dtype=np.float32),
        }
        right_features = {
            "keypoints": np.array([[2.0, 2.0], [5.0, 5.0], [8.0, 8.0]], dtype=np.float32),
            "descriptors": np.array(
                [[12.0, 13.0], [22.0, 23.0], [32.0, 33.0]],
                dtype=np.float32,
            ),
            "scores": np.array([0.4, 0.5, 0.6], dtype=np.float32),
        }
        matcher = _CapturingFeatureMatcher()
        left_mask = np.zeros((10, 10), dtype=bool)
        left_mask[4, 4] = True

        with mock.patch.object(adapter._superpoint, "extract", side_effect=[left_features, right_features]), mock.patch(
            "image_match.deep_adapter.build_deep_matcher",
            return_value=matcher,
        ):
            result = adapter.match_pair(
                matcher_method="lightglue",
                left_image=np.zeros((10, 10), dtype=np.float32),
                right_image=np.zeros((10, 10), dtype=np.float32),
                left_mask=left_mask,
                right_mask=np.zeros((10, 10), dtype=bool),
            )

        self.assertEqual(len(matcher.calls), 1)
        filtered_left = matcher.calls[0]["features_left"]
        filtered_right = matcher.calls[0]["features_right"]
        np.testing.assert_allclose(filtered_left["keypoints"], np.array([[1.0, 1.0], [7.0, 7.0]], dtype=np.float32))
        np.testing.assert_allclose(filtered_left["descriptors"], np.array([[10.0, 11.0], [30.0, 31.0]], dtype=np.float32))
        np.testing.assert_allclose(filtered_left["scores"], np.array([0.1, 0.3], dtype=np.float32))
        np.testing.assert_allclose(filtered_right["keypoints"], right_features["keypoints"])
        self.assertEqual(len(result.left_keypoints), 2)
        self.assertEqual(len(result.right_keypoints), 2)
        self.assertEqual(len(result.matches), 2)

    def test_match_pair_passes_prepared_loftr_masks_into_matcher(self):
        adapter = DeepMatcherAdapter(prefer_gpu=False)
        matcher = _CapturingLoFTRMatcher()
        prepared = {
            "left": object(),
            "right": object(),
            "left_mask": object(),
            "right_mask": object(),
        }
        left_mask = np.zeros((6, 6), dtype=bool)
        right_mask = np.zeros((6, 6), dtype=bool)

        with mock.patch.object(adapter._loftr_frontend, "prepare", return_value=prepared) as prepare_mock, mock.patch(
            "image_match.deep_adapter.build_deep_matcher",
            return_value=matcher,
        ) as build_matcher_mock:
            adapter.match_pair(
                matcher_method="loftr",
                left_image=np.ones((6, 6), dtype=np.float32),
                right_image=np.ones((6, 6), dtype=np.float32),
                left_mask=left_mask,
                right_mask=right_mask,
            )

        prepare_mock.assert_called_once()
        build_matcher_mock.assert_called_once_with(
            "loftr",
            device="cpu",
            feature_extractor_method="loftr",
            matcher_options={},
            feature_options={},
            device_options={},
        )
        self.assertIs(prepare_mock.call_args.kwargs["left_mask"], left_mask)
        self.assertIs(prepare_mock.call_args.kwargs["right_mask"], right_mask)
        self.assertEqual(len(matcher.calls), 1)
        self.assertIs(matcher.calls[0]["left_mask"], prepared["left_mask"])
        self.assertIs(matcher.calls[0]["right_mask"], prepared["right_mask"])


if __name__ == "__main__":
    unittest.main()
