"""Unit tests for adaptive image-match routing helpers.

Author: Geng Xun
Created: 2026-05-14
Last Modified: 2026-05-14
Updated: 2026-05-14  Geng Xun added first-node regression coverage for texture probes, SPICE-constrained elevation candidates, and matcher routing sidecars.
"""

from __future__ import annotations

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
    RenderProbe,
    SpiceLightingConstraints,
    build_pair_probe_sidecar,
    build_spice_constrained_elevation_candidates,
    compute_real_image_texture_probe,
    route_matcher_for_pair,
)


class ImageMatchAdaptiveRoutingUnitTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()