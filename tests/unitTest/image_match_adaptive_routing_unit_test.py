"""Unit tests for adaptive image-match routing helpers.

Author: Geng Xun
Created: 2026-05-14
Last Modified: 2026-05-20
Updated: 2026-05-14  Geng Xun added first-node regression coverage for texture probes, SPICE-constrained elevation candidates, and matcher routing sidecars.
Updated: 2026-05-14  Geng Xun added focused coverage for match-quality gating and fixed cascade decisions.
Updated: 2026-05-14  Geng Xun added sidecar serialization coverage for quality reports and final decisions.
Updated: 2026-05-14  Geng Xun clarified the interpolated p95 quality-gate regression so the expected accepted case also passes the mean-residual gate.
Updated: 2026-05-16  Geng Xun added coverage for named adaptive-routing quality profiles.
Updated: 2026-05-18  Geng Xun added focused coverage for the sparseness/lighting-aware conservative router and the sidecar diagnostics augmenter.
Updated: 2026-05-19  Geng Xun added coverage for optional nested tile diagnostics in adaptive sidecars.
Updated: 2026-05-20  Geng Xun added preset-aware adaptive-routing coverage for deep preset selection and sidecar serialization.
Updated: 2026-06-02  Geng Xun changed adaptive routing to prior-only matcher selection with no post-match fallback cascade.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
import unittest
import warnings
from unittest.mock import patch

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from image_match.adaptive_routing import (
    ImageTextureProbe,
    MatchQualityReport,
    PairRoutingDecision,
    RenderProbe,
    SpiceLightingConstraints,
    TileRoutingDecision,
    build_pair_probe_sidecar,
    build_cascade_plan,
    build_spice_constrained_elevation_candidates,
    compute_real_image_texture_probe,
    decide_post_match_action,
    evaluate_match_quality,
    normalize_adaptive_routing_profile,
    resolve_adaptive_routing_quality_profile,
    route_matcher_for_pair,
    route_matcher_for_tile,
)


class ImageMatchAdaptiveRoutingUnitTest(unittest.TestCase):
    def test_resolve_adaptive_routing_quality_profiles_expand_expected_thresholds(self):
        balanced = resolve_adaptive_routing_quality_profile("balanced")
        strict = resolve_adaptive_routing_quality_profile("strict")
        relaxed = resolve_adaptive_routing_quality_profile("relaxed")
        fast = resolve_adaptive_routing_quality_profile("fast")

        self.assertEqual(balanced.min_inlier_count, 24)
        self.assertGreater(strict.min_inlier_count, balanced.min_inlier_count)
        self.assertGreater(strict.min_coverage, balanced.min_coverage)
        self.assertLess(strict.max_mean_residual, balanced.max_mean_residual)
        self.assertLess(relaxed.min_inlier_ratio, balanced.min_inlier_ratio)
        self.assertGreater(relaxed.max_p95_residual, balanced.max_p95_residual)
        self.assertLessEqual(fast.min_inlier_count, balanced.min_inlier_count)
        self.assertGreater(fast.max_mean_residual, balanced.max_mean_residual)

    def test_normalize_adaptive_routing_profile_rejects_unknown_value(self):
        self.assertEqual(normalize_adaptive_routing_profile("STRICT"), "strict")

        with self.assertRaises(ValueError):
            normalize_adaptive_routing_profile("unsafe")

    def test_spice_constrained_elevation_candidates_stay_near_real_value_and_inside_bounds(self):
        candidates = build_spice_constrained_elevation_candidates(
            real_solar_elevation=32.0,
            solar_elevation_min=24.0,
            solar_elevation_max=38.0,
        )

        self.assertEqual(candidates, (26.0, 30.0, 32.0, 34.0, 38.0))

    def test_texture_probe_scores_structured_image_above_blank_image(self):
        blank = np.zeros((96, 96), dtype=np.float32)
        structured = np.indices((96, 96)).sum(axis=0).astype(np.float32) % 16
        structured[24:72, 24:72] += 80.0

        blank_probe = compute_real_image_texture_probe(blank)
        structured_probe = compute_real_image_texture_probe(structured)

        self.assertEqual(blank_probe.valid_pixel_ratio, 1.0)
        self.assertGreater(structured_probe.mean_gradient, blank_probe.mean_gradient)
        self.assertGreater(structured_probe.laplacian_variance, blank_probe.laplacian_variance)
        self.assertGreater(structured_probe.real_texture_score, blank_probe.real_texture_score)

    def test_texture_probe_ignores_overflow_sized_special_pixels_without_warning(self):
        image = np.full((96, 96), 120.0, dtype=np.float64)
        image[0, 0] = 1.0e300

        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            probe = compute_real_image_texture_probe(image)

        self.assertEqual(probe.total_pixel_count, image.size)
        self.assertEqual(probe.valid_pixel_count, image.size - 1)

    def test_rich_pair_routes_to_sift_descriptor_matching_first(self):
        texture = ImageTextureProbe(
            keypoint_count=250,
            valid_pixel_count=10000,
            total_pixel_count=10000,
            keypoint_density=0.025,
            mean_gradient=42.0,
            laplacian_variance=650.0,
            entropy=4.2,
            valid_pixel_ratio=1.0,
            real_texture_score=0.72,
        )

        decision = route_matcher_for_pair(
            left_texture_probe=texture,
            right_texture_probe=texture,
            left_render_probe=RenderProbe(best_render_elevation=31.0, terrain_explainability_score=0.6),
            right_render_probe=RenderProbe(best_render_elevation=36.0, terrain_explainability_score=0.55),
        )

        self.assertEqual(decision.initial_matcher, "flann")
        self.assertEqual(decision.fallback_chain, ())
        self.assertLess(decision.estimated_match_difficulty, 0.5)

    def test_weak_or_large_lighting_gap_pair_routes_to_loftr_first(self):
        weak_texture = ImageTextureProbe(
            keypoint_count=4,
            valid_pixel_count=10000,
            total_pixel_count=10000,
            keypoint_density=0.0004,
            mean_gradient=5.0,
            laplacian_variance=20.0,
            entropy=1.0,
            valid_pixel_ratio=1.0,
            real_texture_score=0.12,
        )

        decision = route_matcher_for_pair(
            left_texture_probe=weak_texture,
            right_texture_probe=weak_texture,
            left_render_probe=RenderProbe(best_render_elevation=12.0, terrain_explainability_score=0.2),
            right_render_probe=RenderProbe(best_render_elevation=58.0, terrain_explainability_score=0.3),
        )

        self.assertEqual(decision.initial_matcher, "loftr")
        self.assertEqual(decision.fallback_chain, ())
        self.assertGreater(decision.estimated_match_difficulty, 0.8)

    def test_pair_probe_sidecar_keeps_expected_top_level_sections(self):
        texture = ImageTextureProbe(
            keypoint_count=10,
            valid_pixel_count=100,
            total_pixel_count=100,
            keypoint_density=0.1,
            mean_gradient=10.0,
            laplacian_variance=100.0,
            entropy=2.0,
            valid_pixel_ratio=1.0,
            real_texture_score=0.4,
        )
        constraints = SpiceLightingConstraints(
            solar_elevation_min=24.0,
            solar_elevation_max=38.0,
            real_estimated_elevation_left=31.0,
            real_estimated_elevation_right=34.0,
            render_probe_elevation_candidates=(26.0, 30.0, 32.0, 34.0, 38.0),
        )
        decision = route_matcher_for_pair(
            left_texture_probe=texture,
            right_texture_probe=texture,
            spice_constraints=constraints,
        )

        payload = build_pair_probe_sidecar(
            left_texture_probe=texture,
            right_texture_probe=texture,
            spice_constraints=constraints,
            route_decision=decision,
            match_quality={"inlier_count": 42},
            final_decision={"accepted": True},
        )

        self.assertEqual(
            set(payload),
            {
                "left_image_probe",
                "right_image_probe",
                "spice_constraints",
                "pair_route",
                "match_quality",
                "final_decision",
            },
        )
        self.assertEqual(payload["pair_route"]["initial_matcher"], "lightglue")
        self.assertEqual(payload["match_quality"]["inlier_count"], 42)
        self.assertTrue(payload["final_decision"]["accepted"])

    def test_pair_probe_sidecar_accepts_quality_report_and_final_action(self):
        texture = ImageTextureProbe(
            keypoint_count=18,
            valid_pixel_count=100,
            total_pixel_count=100,
            keypoint_density=0.18,
            mean_gradient=12.0,
            laplacian_variance=90.0,
            entropy=2.2,
            valid_pixel_ratio=1.0,
            real_texture_score=0.45,
        )
        decision = route_matcher_for_pair(
            left_texture_probe=texture,
            right_texture_probe=texture,
        )
        quality = evaluate_match_quality(
            inlier_count=32,
            total_match_count=40,
            coverage=0.42,
            residuals=(0.4, 0.7, 0.9, 1.1),
        )
        action = decide_post_match_action(
            current_matcher=decision.initial_matcher,
            quality_report=quality,
            cascade_plan=build_cascade_plan(
                initial_matcher=decision.initial_matcher,
                fallback_chain=decision.fallback_chain,
            ),
        )

        payload = build_pair_probe_sidecar(
            left_texture_probe=texture,
            right_texture_probe=texture,
            route_decision=decision,
            match_quality=quality,
            final_decision=action,
        )

        json.dumps(payload)
        self.assertEqual(payload["pair_route"]["fallback_chain"], [])
        self.assertEqual(payload["match_quality"]["inlier_count"], 32)
        self.assertEqual(payload["match_quality"]["rejection_reasons"], [])
        self.assertTrue(payload["final_decision"]["accepted"])
        self.assertIsNone(payload["final_decision"]["next_matcher"])

    def test_pair_probe_sidecar_serializes_preset_aware_route_fields(self):
        texture = ImageTextureProbe(
            keypoint_count=10,
            valid_pixel_count=100,
            total_pixel_count=100,
            keypoint_density=0.1,
            mean_gradient=10.0,
            laplacian_variance=100.0,
            entropy=2.0,
            valid_pixel_ratio=1.0,
            real_texture_score=0.4,
        )
        decision = PairRoutingDecision(
            initial_matcher="lightglue",
            fallback_chain=(),
            route_reason="moderate texture and moderate lighting gap",
            mean_real_texture_score=0.4,
            mean_terrain_explainability_score=None,
            render_inferred_elevation_gap=None,
            render_peak_sharpness=None,
            estimated_match_difficulty=0.55,
            deep_match_config_path="examples/controlnet_construct/presets/lightglue_default.json",
            route_confidence=0.82,
        )

        payload = build_pair_probe_sidecar(
            left_texture_probe=texture,
            right_texture_probe=texture,
            route_decision=decision,
        )

        self.assertEqual(
            payload["pair_route"]["deep_match_config_path"],
            "examples/controlnet_construct/presets/lightglue_default.json",
        )
        self.assertAlmostEqual(payload["pair_route"]["route_confidence"], 0.82)

    def test_evaluate_match_quality_accepts_balanced_low_residual_result(self):
        report = evaluate_match_quality(
            inlier_count=48,
            total_match_count=60,
            coverage=0.62,
            residuals=(0.3, 0.6, 0.8, 1.0, 1.2),
        )

        self.assertTrue(report.accepted)
        self.assertAlmostEqual(report.inlier_ratio, 0.8)
        self.assertEqual(report.rejection_reasons, ())
        self.assertAlmostEqual(report.residual_summary["p95"], 1.16)
        self.assertGreater(report.quality_score, 0.7)

    def test_evaluate_match_quality_rejects_sparse_high_residual_result(self):
        report = evaluate_match_quality(
            inlier_count=12,
            total_match_count=50,
            coverage=0.08,
            residuals=(1.0, 3.0, 4.5, 5.0, 6.5),
        )

        self.assertFalse(report.accepted)
        self.assertIn("insufficient_inlier_count", report.rejection_reasons)
        self.assertIn("insufficient_inlier_ratio", report.rejection_reasons)
        self.assertIn("insufficient_coverage", report.rejection_reasons)
        self.assertIn("mean_residual_too_large", report.rejection_reasons)
        self.assertIn("p95_residual_too_large", report.rejection_reasons)

    def test_evaluate_match_quality_uses_interpolated_p95_residual(self):
        report = evaluate_match_quality(
            inlier_count=30,
            total_match_count=36,
            coverage=0.35,
            residuals=(1.0, 2.0, 4.0, 8.0),
            max_mean_residual=4.0,
            max_p95_residual=8.0,
        )

        self.assertAlmostEqual(report.residual_summary["p95"], 7.4)
        self.assertTrue(report.accepted)

    def test_build_cascade_plan_returns_only_the_prior_selected_matcher(self):
        plan = build_cascade_plan(
            initial_matcher="bf",
            fallback_chain=("loftr", "lightglue"),
        )

        self.assertEqual(plan, ("bf",))
        self.assertEqual(build_cascade_plan(initial_matcher="lightglue"), ("lightglue",))
        self.assertEqual(build_cascade_plan(initial_matcher="loftr"), ("loftr",))

    def test_build_cascade_plan_accepts_flann_in_public_adaptive_flow(self):
        plan = build_cascade_plan(
            initial_matcher="flann",
            fallback_chain=("loftr", "lightglue"),
        )

        self.assertEqual(plan, ("flann",))

    def test_decide_post_match_action_does_not_request_fallback_after_failed_gate(self):
        plan = build_cascade_plan(initial_matcher="bf")
        report = MatchQualityReport(
            inlier_count=10,
            total_match_count=40,
            inlier_ratio=0.25,
            coverage=0.12,
            residual_summary={"count": 4, "mean": 3.2, "median": 3.0, "p95": 4.8, "max": 5.0},
            quality_score=0.29,
            accepted=False,
            rejection_reasons=("insufficient_inlier_count", "insufficient_coverage"),
        )

        action = decide_post_match_action(
            current_matcher="bf",
            quality_report=report,
            cascade_plan=plan,
        )

        self.assertFalse(action["accepted"])
        self.assertFalse(action["fallback_used"])
        self.assertIsNone(action["next_matcher"])
        self.assertEqual(action["stop_reason"], "quality_insufficient_no_fallback")

    def test_decide_post_match_action_accepts_successful_fallback(self):
        accepted_report = MatchQualityReport(
            inlier_count=36,
            total_match_count=44,
            inlier_ratio=36 / 44,
            coverage=0.41,
            residual_summary={"count": 6, "mean": 0.8, "median": 0.75, "p95": 1.3, "max": 1.3},
            quality_score=0.76,
            accepted=True,
            rejection_reasons=(),
        )

        action = decide_post_match_action(
            current_matcher="lightglue",
            quality_report=accepted_report,
            cascade_plan=("lightglue",),
        )

        self.assertTrue(action["accepted"])
        self.assertFalse(action["fallback_used"])
        self.assertIsNone(action["next_matcher"])
        self.assertEqual(action["selected_matcher"], "lightglue")
        self.assertEqual(action["stop_reason"], "quality_accepted")

    def test_tile_router_uses_flann_for_rich_texture_small_physical_lighting_gap(self):
        decision = route_matcher_for_tile(
            tile_index=2,
            texture_sparseness=0.12,
            lighting_difference_score=0.05,
            texture_probe_keypoint_count_left=250,
            texture_probe_keypoint_count_right=240,
            texture_probe_keypoint_density_left=0.002,
            texture_probe_keypoint_density_right=0.002,
            illumination={"status": "ok", "illumination_difference_score": 0.05},
            adaptive_routing_deep_presets={},
        )

        self.assertIsInstance(decision, TileRoutingDecision)
        self.assertEqual(decision.selected_matcher, "flann")
        self.assertEqual(decision.selected_execution_environment, "asp360_new")
        self.assertTrue(decision.no_post_match_fallback)

    def test_tile_router_uses_loftr_for_low_keypoint_density_hard_rule(self):
        decision = route_matcher_for_tile(
            tile_index=3,
            texture_sparseness=0.25,
            lighting_difference_score=0.10,
            texture_probe_keypoint_count_left=4,
            texture_probe_keypoint_count_right=80,
            texture_probe_keypoint_density_left=1.0e-7,
            texture_probe_keypoint_density_right=1.0e-4,
            illumination={"status": "ok", "illumination_difference_score": 0.10},
            adaptive_routing_deep_presets={"loftr": "examples/controlnet_construct/presets/loftr_default.json"},
        )

        self.assertEqual(decision.selected_matcher, "loftr")
        self.assertEqual(decision.selected_execution_environment, "deep-learning")
        self.assertEqual(decision.deep_match_config_path, "examples/controlnet_construct/presets/loftr_default.json")

    def test_tile_router_uses_superpoint_lightglue_for_weak_non_extreme_texture(self):
        decision = route_matcher_for_tile(
            tile_index=4,
            texture_sparseness=0.62,
            lighting_difference_score=0.30,
            texture_probe_keypoint_count_left=90,
            texture_probe_keypoint_count_right=95,
            texture_probe_keypoint_density_left=2.0e-5,
            texture_probe_keypoint_density_right=2.5e-5,
            illumination={"status": "ok", "illumination_difference_score": 0.30},
            adaptive_routing_deep_presets={
                "superpoint_lightglue": "examples/controlnet_construct/presets/lightglue_official_superpoint.json"
            },
        )

        self.assertEqual(decision.selected_matcher, "lightglue")
        self.assertEqual(
            decision.deep_match_config_path,
            "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
        )
        self.assertIn("SuperPoint", decision.route_reason)


class ImageMatchAdaptiveRoutingSparsenessLightingUnitTest(unittest.TestCase):
    def test_resolve_adaptive_route_sidecar_uses_sensor_model_lighting(self):
        image_match_module = importlib.import_module("image_match.image_match")
        from image_match.lighting_difference import SolarGeometry

        texture_probe = ImageTextureProbe(
            keypoint_count=100,
            valid_pixel_count=1000,
            total_pixel_count=1000,
            keypoint_density=0.10,
            mean_gradient=120.0,
            laplacian_variance=2500.0,
            entropy=4.2,
            valid_pixel_ratio=1.0,
            real_texture_score=0.85,
        )
        left_geometry = SolarGeometry(
            solar_elevation_degrees=33.5,
            solar_azimuth_degrees=164.0,
            source_group_name="SensorModelCenter",
            elevation_keyword="90-IncidenceAngle",
            azimuth_keyword="SunAzimuth",
        )
        right_geometry = SolarGeometry(
            solar_elevation_degrees=33.0,
            solar_azimuth_degrees=165.0,
            source_group_name="SensorModelCenter",
            elevation_keyword="90-IncidenceAngle",
            azimuth_keyword="SunAzimuth",
        )

        with (
            patch.object(
                image_match_module,
                "_compute_texture_probe_from_cube_path",
                return_value=texture_probe,
            ),
            patch.object(
                image_match_module,
                "_compute_texture_sparseness_and_geometry_from_cube_path",
                side_effect=[
                    ("left_sparseness", left_geometry, None),
                    ("right_sparseness", right_geometry, None),
                ],
            ),
            patch.object(
                image_match_module,
                "aggregate_pair_texture_sparseness",
                return_value="pair_sparseness",
            ),
            patch.object(
                image_match_module,
                "pair_summary_to_diagnostic_dict",
                return_value={"pair_texture_sparseness": 0.12, "weaker_side": "left"},
            ),
        ):
            selected, summary = image_match_module._resolve_adaptive_route_for_pair(
                enable_adaptive_routing=True,
                requested_matcher_method="flann",
                adaptive_routing_deep_presets=None,
                band=1,
                invalid_values=(),
                special_pixel_abs_threshold=1e300,
                low_resolution_offset_summary={
                    "left_low_resolution_dom": "left_preview.cub",
                    "right_low_resolution_dom": "right_preview.cub",
                },
                left_low_resolution_dom=None,
                right_low_resolution_dom=None,
            )

        self.assertEqual(selected, "flann")
        self.assertIsNotNone(summary)
        lighting = summary["sidecar"]["lighting_difference"]
        score = lighting["lighting_difference_score"]
        self.assertIsNotNone(score)
        self.assertTrue(np.isfinite(score))
        self.assertEqual(lighting["left_solar_geometry"]["source_group_name"], "SensorModelCenter")
        self.assertEqual(lighting["right_solar_geometry"]["source_group_name"], "SensorModelCenter")
        self.assertEqual(lighting["left_solar_geometry"]["elevation_keyword"], "90-IncidenceAngle")
        self.assertEqual(lighting["left_solar_geometry"]["azimuth_keyword"], "SunAzimuth")
        self.assertEqual(lighting["right_solar_geometry"]["elevation_keyword"], "90-IncidenceAngle")
        self.assertEqual(lighting["right_solar_geometry"]["azimuth_keyword"], "SunAzimuth")

    def test_resolve_adaptive_route_uses_actual_dom_for_texture_when_matching_dom(self):
        image_match_module = importlib.import_module("image_match.image_match")

        texture_probe = ImageTextureProbe(
            keypoint_count=100,
            valid_pixel_count=1000,
            total_pixel_count=1000,
            keypoint_density=0.10,
            mean_gradient=120.0,
            laplacian_variance=2500.0,
            entropy=4.2,
            valid_pixel_ratio=1.0,
            real_texture_score=0.85,
        )

        with (
            patch.object(
                image_match_module,
                "_compute_texture_probe_from_cube_path",
                return_value=texture_probe,
            ) as probe_mock,
            patch.object(
                image_match_module,
                "_compute_texture_sparseness_and_geometry_from_cube_path",
                side_effect=[
                    ("left_sparseness", None, "missing solar"),
                    ("right_sparseness", None, "missing solar"),
                ],
            ) as sparseness_mock,
            patch.object(
                image_match_module,
                "aggregate_pair_texture_sparseness",
                return_value="pair_sparseness",
            ),
            patch.object(
                image_match_module,
                "pair_summary_to_diagnostic_dict",
                return_value={"pair_texture_sparseness": 0.12, "weaker_side": "left"},
            ),
        ):
            selected, summary = image_match_module._resolve_adaptive_route_for_pair(
                enable_adaptive_routing=True,
                requested_matcher_method="flann",
                adaptive_routing_deep_presets=None,
                band=1,
                invalid_values=(),
                special_pixel_abs_threshold=1e300,
                low_resolution_offset_summary={
                    "left_low_resolution_dom": "left_preview.cub",
                    "right_low_resolution_dom": "right_preview.cub",
                },
                left_low_resolution_dom=None,
                right_low_resolution_dom=None,
                image_space="dom",
                left_source_path="left_actual_dom.cub",
                right_source_path="right_actual_dom.cub",
            )

        self.assertEqual(selected, "flann")
        self.assertIsNotNone(summary)
        self.assertEqual(probe_mock.call_args_list[0].args[0], "left_actual_dom.cub")
        self.assertEqual(probe_mock.call_args_list[1].args[0], "right_actual_dom.cub")
        self.assertEqual(sparseness_mock.call_args_list[0].args[0], "left_actual_dom.cub")
        self.assertEqual(sparseness_mock.call_args_list[1].args[0], "right_actual_dom.cub")
        self.assertEqual(summary["preview_sources"]["source_type"], "matched_dom")
        self.assertFalse(summary["preview_sources"]["fallback_used"])

    def test_route_matcher_for_pair_with_sparseness_picks_flann_for_low_signals(self):
        from image_match.adaptive_routing import (
            FLANN_MATCHER_METHOD,
            route_matcher_for_pair_with_sparseness,
        )

        decision = route_matcher_for_pair_with_sparseness(
            pair_texture_sparseness=0.15,
            lighting_difference_score=0.10,
        )

        self.assertEqual(decision.initial_matcher, FLANN_MATCHER_METHOD)
        self.assertIn("rich texture", decision.route_reason)
        self.assertEqual(decision.fallback_chain, ())

    def test_adaptive_routing_deep_presets_keep_requested_flann_without_deep_preset(self):
        from image_match.adaptive_routing import route_matcher_for_pair_with_sparseness

        decision = route_matcher_for_pair_with_sparseness(
            pair_texture_sparseness=0.15,
            lighting_difference_score=0.10,
            traditional_matcher="flann",
            adaptive_routing_deep_presets={
                "lightglue": "examples/controlnet_construct/presets/lightglue_default.json",
                "lightglue_high_recall": "examples/controlnet_construct/presets/lightglue_high_recall.json",
                "loftr": "examples/controlnet_construct/presets/loftr_default.json",
            },
        )

        self.assertEqual(decision.initial_matcher, "flann")
        self.assertEqual(decision.fallback_chain, ())
        self.assertIsNone(decision.deep_match_config_path)
        self.assertGreater(decision.route_confidence, 0.7)

    def test_route_matcher_for_pair_with_sparseness_picks_lightglue_for_high_sparseness_only(self):
        from image_match.adaptive_routing import (
            LIGHTGLUE_MATCHER_METHOD,
            route_matcher_for_pair_with_sparseness,
        )

        decision = route_matcher_for_pair_with_sparseness(
            pair_texture_sparseness=0.80,
            lighting_difference_score=0.10,
        )

        self.assertEqual(decision.initial_matcher, LIGHTGLUE_MATCHER_METHOD)
        self.assertEqual(decision.fallback_chain, ())

    def test_adaptive_routing_deep_presets_route_medium_pair_to_lightglue_default(self):
        from image_match.adaptive_routing import route_matcher_for_pair_with_sparseness

        preset_map = {
            "lightglue": "examples/controlnet_construct/presets/lightglue_default.json",
            "lightglue_high_recall": "examples/controlnet_construct/presets/lightglue_high_recall.json",
            "loftr": "examples/controlnet_construct/presets/loftr_default.json",
        }
        decision = route_matcher_for_pair_with_sparseness(
            pair_texture_sparseness=0.45,
            lighting_difference_score=0.30,
            adaptive_routing_deep_presets=preset_map,
        )

        self.assertEqual(decision.initial_matcher, "lightglue")
        self.assertEqual(decision.deep_match_config_path, preset_map["lightglue"])
        self.assertGreater(decision.route_confidence, 0.5)

    def test_route_matcher_for_pair_with_sparseness_picks_lightglue_for_high_lighting_only(self):
        from image_match.adaptive_routing import (
            LIGHTGLUE_MATCHER_METHOD,
            route_matcher_for_pair_with_sparseness,
        )

        decision = route_matcher_for_pair_with_sparseness(
            pair_texture_sparseness=0.15,
            lighting_difference_score=0.70,
        )

        self.assertEqual(decision.initial_matcher, LIGHTGLUE_MATCHER_METHOD)

    def test_adaptive_routing_deep_presets_route_sparse_pair_to_loftr_default(self):
        from image_match.adaptive_routing import route_matcher_for_pair_with_sparseness

        preset_map = {
            "lightglue": "examples/controlnet_construct/presets/lightglue_default.json",
            "lightglue_high_recall": "examples/controlnet_construct/presets/lightglue_high_recall.json",
            "loftr": "examples/controlnet_construct/presets/loftr_default.json",
        }
        decision = route_matcher_for_pair_with_sparseness(
            pair_texture_sparseness=0.78,
            lighting_difference_score=0.70,
            adaptive_routing_deep_presets=preset_map,
        )

        self.assertEqual(decision.initial_matcher, "loftr")
        self.assertEqual(decision.deep_match_config_path, preset_map["loftr"])
        self.assertGreater(decision.route_confidence, 0.7)

    def test_route_matcher_for_pair_with_sparseness_routes_low_probe_keypoints_to_loftr(self):
        from image_match.adaptive_routing import route_matcher_for_pair_with_sparseness

        preset_map = {
            "lightglue": "examples/controlnet_construct/presets/lightglue_official_sift.json",
            "loftr": "examples/controlnet_construct/presets/loftr_default.json",
        }
        low_probe = ImageTextureProbe(
            keypoint_count=4,
            valid_pixel_count=1000,
            total_pixel_count=1000,
            keypoint_density=0.004,
            mean_gradient=20.0,
            laplacian_variance=50.0,
            entropy=2.0,
            valid_pixel_ratio=1.0,
            real_texture_score=0.2,
        )
        rich_probe = ImageTextureProbe(
            keypoint_count=200,
            valid_pixel_count=1000,
            total_pixel_count=1000,
            keypoint_density=0.2,
            mean_gradient=120.0,
            laplacian_variance=2500.0,
            entropy=4.5,
            valid_pixel_ratio=1.0,
            real_texture_score=0.9,
        )

        decision = route_matcher_for_pair_with_sparseness(
            pair_texture_sparseness=0.20,
            lighting_difference_score=0.10,
            left_texture_probe=low_probe,
            right_texture_probe=rich_probe,
            adaptive_routing_deep_presets=preset_map,
        )

        self.assertEqual(decision.initial_matcher, "loftr")
        self.assertEqual(decision.deep_match_config_path, preset_map["loftr"])
        self.assertIn("too few keypoints", decision.route_reason)

    def test_route_matcher_for_pair_with_sparseness_picks_lightglue_in_middle(self):
        from image_match.adaptive_routing import (
            LIGHTGLUE_MATCHER_METHOD,
            route_matcher_for_pair_with_sparseness,
        )

        decision = route_matcher_for_pair_with_sparseness(
            pair_texture_sparseness=0.50,
            lighting_difference_score=0.30,
        )

        self.assertEqual(decision.initial_matcher, LIGHTGLUE_MATCHER_METHOD)
        self.assertEqual(decision.fallback_chain, ())

    def test_route_matcher_for_pair_with_sparseness_uses_superpoint_lightglue_for_weak_non_extreme_pair(self):
        from image_match.adaptive_routing import route_matcher_for_pair_with_sparseness

        preset_map = {
            "lightglue": "examples/controlnet_construct/presets/lightglue_official_sift.json",
            "superpoint_lightglue": "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
            "loftr": "examples/controlnet_construct/presets/loftr_default.json",
        }
        decision = route_matcher_for_pair_with_sparseness(
            pair_texture_sparseness=0.62,
            lighting_difference_score=0.25,
            adaptive_routing_deep_presets=preset_map,
        )

        self.assertEqual(decision.initial_matcher, "lightglue")
        self.assertEqual(decision.deep_match_config_path, preset_map["superpoint_lightglue"])
        self.assertIn("SuperPoint", decision.route_reason)

    def test_route_matcher_for_pair_with_sparseness_falls_back_when_both_missing(self):
        from image_match.adaptive_routing import (
            LIGHTGLUE_MATCHER_METHOD,
            route_matcher_for_pair_with_sparseness,
        )

        decision = route_matcher_for_pair_with_sparseness(
            pair_texture_sparseness=None,
            lighting_difference_score=None,
        )

        self.assertEqual(decision.initial_matcher, LIGHTGLUE_MATCHER_METHOD)
        self.assertIn("unavailable", decision.route_reason)
        self.assertIsNone(decision.mean_real_texture_score)

    def test_augment_pair_probe_sidecar_keeps_schema_shape(self):
        from image_match.adaptive_routing import (
            augment_pair_probe_sidecar_with_sparseness_lighting,
        )

        base_sidecar = {"pair_route": {"initial_matcher": "loftr"}}
        augmented = augment_pair_probe_sidecar_with_sparseness_lighting(
            base_sidecar,
            pair_sparseness_summary={"pair_texture_sparseness": 0.42, "weaker_side": "left"},
            lighting_difference_summary={"lighting_difference_score": 0.18, "reason": "test"},
            routing_thresholds={"sparseness_low": 0.35, "sparseness_high": 0.65},
        )

        self.assertEqual(augmented["pair_route"], {"initial_matcher": "loftr"})
        self.assertEqual(augmented["texture_sparseness"]["pair_texture_sparseness"], 0.42)
        self.assertEqual(augmented["lighting_difference"]["lighting_difference_score"], 0.18)
        self.assertEqual(augmented["routing_thresholds"]["sparseness_low"], 0.35)
        # Original sidecar must not be mutated in place.
        self.assertNotIn("texture_sparseness", base_sidecar)

    def test_augment_pair_probe_sidecar_defaults_to_empty_diagnostics(self):
        from image_match.adaptive_routing import (
            augment_pair_probe_sidecar_with_sparseness_lighting,
        )

        augmented = augment_pair_probe_sidecar_with_sparseness_lighting({"a": 1})

        self.assertEqual(augmented["texture_sparseness"], {})
        self.assertEqual(augmented["lighting_difference"], {})

    def test_augment_pair_probe_sidecar_adds_nested_tile_diagnostics(self):
        from image_match.adaptive_routing import (
            augment_pair_probe_sidecar_with_sparseness_lighting,
        )

        base_sidecar = {"pair_route": {"initial_matcher": "lightglue"}}
        augmented = augment_pair_probe_sidecar_with_sparseness_lighting(
            base_sidecar,
            pair_sparseness_summary={"pair_texture_sparseness": 0.41},
            lighting_difference_summary={"lighting_difference_score": 0.22},
            tile_diagnostics_summary={
                "texture_sparseness": {"tile_valid_count": 7},
                "lighting": {"tile_valid_count": 5},
            },
        )

        self.assertEqual(augmented["texture_sparseness"]["pair_texture_sparseness"], 0.41)
        self.assertEqual(augmented["lighting_difference"]["lighting_difference_score"], 0.22)
        self.assertEqual(augmented["tile_diagnostics"]["texture_sparseness"]["tile_valid_count"], 7)
        self.assertEqual(augmented["tile_diagnostics"]["lighting"]["tile_valid_count"], 5)
        self.assertNotIn("tile_diagnostics", base_sidecar)


if __name__ == "__main__":
    unittest.main()
