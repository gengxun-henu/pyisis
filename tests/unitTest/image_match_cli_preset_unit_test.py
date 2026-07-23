"""Focused unit tests for image-match CLI preset resolution.

Author: Geng Xun
Created: 2026-07-23
Last Modified: 2026-07-23
Updated: 2026-07-23  Geng Xun split image-match preset coverage from pipeline orchestration tests.
"""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import temporary_directory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.image_match import (
    build_argument_parser as build_image_match_argument_parser,
    main as image_match_main,
)
from image_match.image_match import load_image_match_defaults_from_config


class ImageMatchCliPresetUnitTest(unittest.TestCase):
    def test_image_match_parser_accepts_deep_matcher_method(self):
        parser = build_image_match_argument_parser()
        parsed = parser.parse_args(
            [
                "left_dom.cub",
                "right_dom.cub",
                "left.key",
                "right.key",
                "--matcher-method",
                "lightglue",
            ]
        )
        self.assertEqual(parsed.matcher_method, "lightglue")

    def test_image_match_config_match_preset_overrides_legacy_matcher_fields(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            preset_path = (
                PROJECT_ROOT
                / "examples"
                / "controlnet_construct"
                / "presets"
                / "classic_sift_bf.json"
            )
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "match_preset_path": str(preset_path),
                            "matcher_method": "lightglue",
                            "deep_matcher_config_path": (
                                "examples/controlnet_construct/presets/lightglue_default.json"
                            ),
                        }
                    }
                ),
                encoding="utf-8",
            )

            defaults = load_image_match_defaults_from_config(config_path)

        self.assertEqual(defaults["match_preset_path"], str(preset_path.resolve()))
        self.assertEqual(defaults["matcher_method"], "bf")
        self.assertIsNone(defaults["deep_match_config_path"])
        self.assertEqual(defaults["max_features"], 1000)

    def test_image_match_parser_accepts_match_preset_path_cli(self):
        parser = build_image_match_argument_parser()
        preset_path = (
            PROJECT_ROOT
            / "examples"
            / "controlnet_construct"
            / "presets"
            / "classic_sift_flann.json"
        )

        parsed = parser.parse_args(
            [
                "left_dom.cub",
                "right_dom.cub",
                "left.key",
                "right.key",
                "--match-preset-path",
                str(preset_path),
            ]
        )

        self.assertEqual(parsed.match_preset_path, str(preset_path.resolve()))
        self.assertEqual(parsed.matcher_method, "flann")
        self.assertEqual(parsed.max_features, 1000)

    def test_image_match_config_match_preset_allows_cli_ratio_override(self):
        fake_result = {"status": "matched", "point_count": 0, "tile_count": 0}
        stdout = io.StringIO()

        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            preset_path = (
                PROJECT_ROOT
                / "examples"
                / "controlnet_construct"
                / "presets"
                / "classic_sift_bf.json"
            )
            config_path.write_text(
                json.dumps({"ImageMatch": {"match_preset_path": str(preset_path)}}),
                encoding="utf-8",
            )

            with (
                patch(
                    "controlnet_construct.image_match.match_dom_pair_to_key_files",
                    return_value=fake_result,
                ) as match_mock,
                patch.object(sys, "stdout", stdout),
            ):
                image_match_main(
                    [
                        "--config",
                        str(config_path),
                        "left_dom.cub",
                        "right_dom.cub",
                        "left.key",
                        "right.key",
                        "--ratio-test",
                        "0.9",
                    ]
                )

        self.assertEqual(match_mock.call_args.kwargs["matcher_method"], "bf")
        self.assertEqual(match_mock.call_args.kwargs["ratio_test"], 0.9)

    def test_image_match_cli_match_preset_allows_later_ratio_override(self):
        fake_result = {"status": "matched", "point_count": 0, "tile_count": 0}
        stdout = io.StringIO()
        preset_path = (
            PROJECT_ROOT
            / "examples"
            / "controlnet_construct"
            / "presets"
            / "classic_sift_bf.json"
        )

        with (
            patch(
                "controlnet_construct.image_match.match_dom_pair_to_key_files",
                return_value=fake_result,
            ) as match_mock,
            patch.object(sys, "stdout", stdout),
        ):
            image_match_main(
                [
                    "left_dom.cub",
                    "right_dom.cub",
                    "left.key",
                    "right.key",
                    "--match-preset-path",
                    str(preset_path),
                    "--ratio-test",
                    "0.9",
                ]
            )

        self.assertEqual(match_mock.call_args.kwargs["matcher_method"], "bf")
        self.assertEqual(match_mock.call_args.kwargs["ratio_test"], 0.9)

    def test_image_match_cli_match_preset_allows_earlier_ratio_override(self):
        fake_result = {"status": "matched", "point_count": 0, "tile_count": 0}
        stdout = io.StringIO()
        preset_path = (
            PROJECT_ROOT
            / "examples"
            / "controlnet_construct"
            / "presets"
            / "classic_sift_bf.json"
        )

        with (
            patch(
                "controlnet_construct.image_match.match_dom_pair_to_key_files",
                return_value=fake_result,
            ) as match_mock,
            patch.object(sys, "stdout", stdout),
        ):
            image_match_main(
                [
                    "left_dom.cub",
                    "right_dom.cub",
                    "left.key",
                    "right.key",
                    "--ratio-test",
                    "0.9",
                    "--match-preset-path",
                    str(preset_path),
                ]
            )

        self.assertEqual(match_mock.call_args.kwargs["matcher_method"], "bf")
        self.assertEqual(match_mock.call_args.kwargs["ratio_test"], 0.9)

    def test_image_match_cli_rejects_match_preset_with_explicit_matcher_method(self):
        preset_path = (
            PROJECT_ROOT
            / "examples"
            / "controlnet_construct"
            / "presets"
            / "classic_sift_bf.json"
        )
        stderr = io.StringIO()

        with patch.object(sys, "stderr", stderr), self.assertRaises(SystemExit):
            image_match_main(
                [
                    "left_dom.cub",
                    "right_dom.cub",
                    "left.key",
                    "right.key",
                    "--match-preset-path",
                    str(preset_path),
                    "--matcher-method",
                    "flann",
                ]
            )

        self.assertIn("--match-preset-path conflicts with --matcher-method", stderr.getvalue())

    def test_image_match_cli_rejects_match_preset_with_explicit_deep_config_path(self):
        preset_path = (
            PROJECT_ROOT
            / "examples"
            / "controlnet_construct"
            / "presets"
            / "classic_sift_bf.json"
        )
        stderr = io.StringIO()

        with patch.object(sys, "stderr", stderr), self.assertRaises(SystemExit):
            image_match_main(
                [
                    "left_dom.cub",
                    "right_dom.cub",
                    "left.key",
                    "right.key",
                    "--match-preset-path",
                    str(preset_path),
                    "--deep-match-config-path",
                    "examples/controlnet_construct/presets/lightglue_default.json",
                ]
            )

        self.assertIn("--match-preset-path conflicts with --deep-match-config-path", stderr.getvalue())

    def test_image_match_cli_match_preset_path_prefers_caller_cwd_over_repo_relative(self):
        parser = build_image_match_argument_parser()

        with temporary_directory() as temp_dir:
            caller_dir = temp_dir / "caller"
            local_preset = (
                caller_dir
                / "examples"
                / "controlnet_construct"
                / "presets"
                / "classic_sift_bf.json"
            )
            local_preset.parent.mkdir(parents=True)
            local_preset.write_text(
                json.dumps(
                    {
                        "feature_extractor": {
                            "method": "classic_sift",
                            "max_features": 77,
                            "octave_layers": 3,
                            "contrast_threshold": 0.04,
                            "edge_threshold": 10.0,
                            "sigma": 1.6,
                        },
                        "matcher": {
                            "method": "bf",
                            "ratio_test": 0.61,
                        },
                    }
                ),
                encoding="utf-8",
            )
            previous_cwd = Path.cwd()
            try:
                os.chdir(caller_dir)
                parsed = parser.parse_args(
                    [
                        "left_dom.cub",
                        "right_dom.cub",
                        "left.key",
                        "right.key",
                        "--match-preset-path",
                        "examples/controlnet_construct/presets/classic_sift_bf.json",
                    ]
                )
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(parsed.match_preset_path, str(local_preset.resolve()))
        self.assertEqual(parsed.max_features, 77)
        self.assertEqual(parsed.ratio_test, 0.61)

    def test_image_match_parser_rejects_invalid_match_preset_path_cleanly(self):
        parser = build_image_match_argument_parser()
        stderr = io.StringIO()

        with patch.object(sys, "stderr", stderr), self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "left_dom.cub",
                    "right_dom.cub",
                    "left.key",
                    "right.key",
                    "--match-preset-path",
                    "does-not-exist.json",
                ]
            )


if __name__ == "__main__":
    unittest.main()
