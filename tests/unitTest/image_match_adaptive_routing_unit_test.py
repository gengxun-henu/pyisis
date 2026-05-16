"""Unit tests for adaptive image-match routing helpers.

Author: Geng Xun
Created: 2026-05-14
Last Modified: 2026-05-14
Updated: 2026-05-14  Geng Xun added first-node regression coverage for texture probes, SPICE-constrained elevation candidates, and matcher routing sidecars.
Updated: 2026-05-14  Geng Xun added focused coverage for match-quality gating and fixed cascade decisions.
Updated: 2026-05-14  Geng Xun added sidecar serialization coverage for quality reports and final decisions.
Updated: 2026-05-14  Geng Xun clarified the interpolated p95 quality-gate regression so the expected accepted case also passes the mean-residual gate.
Updated: 2026-05-16  Geng Xun added coverage for named adaptive-routing quality profiles.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from image_match.adaptive_routing import (
    ImageTextureProbe,
    MatchQualityReport,
    RenderProbe,
    SpiceLightingConstraints,
    build_pair_probe_sidecar,
    build_cascade_plan,
    build_spice_constrained_elevation_candidates,
    compute_real_image_texture_probe,
    decide_post_match_action,
    evaluate_match_quality,
    normalize_adaptive_routing_profile,
    resolve_adaptive_routing_quality_profile,
    route_matcher_for_pair,
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

        self.assertEqual(decision.initial_matcher, "bf")
        self.assertEqual(decision.fallback_chain, ("lightglue", "loftr"))
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
        self.assertEqual(payload["pair_route"]["fallback_chain"], ["loftr"])
        self.assertEqual(payload["match_quality"]["inlier_count"], 32)
        self.assertEqual(payload["match_quality"]["rejection_reasons"], [])
        self.assertTrue(payload["final_decision"]["accepted"])
        self.assertIsNone(payload["final_decision"]["next_matcher"])

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

    def test_build_cascade_plan_preserves_fixed_matcher_order(self):
        plan = build_cascade_plan(
            initial_matcher="bf",
            fallback_chain=("loftr", "lightglue"),
        )

        self.assertEqual(plan, ("bf", "lightglue", "loftr"))
        self.assertEqual(build_cascade_plan(initial_matcher="lightglue"), ("lightglue", "loftr"))
        self.assertEqual(build_cascade_plan(initial_matcher="loftr"), ("loftr",))

    def test_decide_post_match_action_requests_next_matcher_after_failed_gate(self):
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
        self.assertEqual(action["next_matcher"], "lightglue")
        self.assertEqual(action["stop_reason"], "quality_insufficient_try_fallback")

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
            cascade_plan=("bf", "lightglue", "loftr"),
        )

        self.assertTrue(action["accepted"])
        self.assertTrue(action["fallback_used"])
        self.assertIsNone(action["next_matcher"])
        self.assertEqual(action["selected_matcher"], "lightglue")
        self.assertEqual(action["stop_reason"], "quality_accepted")


if __name__ == "__main__":
    unittest.main()
