"""Adaptive lighting-aware matcher routing helpers for image matching examples.

Author: Geng Xun
Created: 2026-05-14
Updated: 2026-05-14  Geng Xun added first-node texture probe, SPICE-constrained elevation candidates, pair routing, and JSON sidecar helpers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable

import cv2
import numpy as np


SIFT_ROUTED_MATCHER_METHOD = "bf"
LIGHTGLUE_MATCHER_METHOD = "lightglue"
LOFTR_MATCHER_METHOD = "loftr"
DEFAULT_ROUTER_FALLBACK_CHAIN = (
    SIFT_ROUTED_MATCHER_METHOD,
    LIGHTGLUE_MATCHER_METHOD,
    LOFTR_MATCHER_METHOD,
)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))


def _finite_float(value: float | None) -> float | None:
    if value is None:
        return None
    resolved = float(value)
    if not math.isfinite(resolved):
        return None
    return resolved


@dataclass(frozen=True, slots=True)
class ImageTextureProbe:
    """Low-cost texture metrics computed from a real image preview."""

    keypoint_count: int
    valid_pixel_count: int
    total_pixel_count: int
    keypoint_density: float
    mean_gradient: float
    laplacian_variance: float
    entropy: float
    valid_pixel_ratio: float
    real_texture_score: float


@dataclass(frozen=True, slots=True)
class RenderProbe:
    """Summary of DEM-render probe scoring for one image."""

    best_render_azimuth: float | None = None
    best_render_elevation: float | None = None
    best_render_score: float | None = None
    render_peak_sharpness: float | None = None
    terrain_explainability_score: float | None = None
    render_score_curve: tuple[dict[str, float], ...] = ()


@dataclass(frozen=True, slots=True)
class SpiceLightingConstraints:
    """SPICE-derived solar geometry constraints used to bound render probing."""

    solar_elevation_min: float | None = None
    solar_elevation_max: float | None = None
    real_estimated_elevation_left: float | None = None
    real_estimated_elevation_right: float | None = None
    render_probe_elevation_candidates: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class PairRoutingDecision:
    """Pair-level matcher route decision and sidecar-ready diagnostics."""

    initial_matcher: str
    fallback_chain: tuple[str, ...]
    route_reason: str
    mean_real_texture_score: float
    mean_terrain_explainability_score: float | None
    render_inferred_elevation_gap: float | None
    render_peak_sharpness: float | None
    estimated_match_difficulty: float


def build_spice_constrained_elevation_candidates(
    *,
    real_solar_elevation: float | None,
    solar_elevation_min: float | None = None,
    solar_elevation_max: float | None = None,
    near_offsets: Iterable[float] = (-6.0, -2.0, 0.0, 2.0, 6.0),
    fallback_step_degrees: float = 10.0,
) -> tuple[float, ...]:
    """Build a compact, reality-bounded solar elevation scan list.

    The first implementation intentionally keeps the search window conservative:
    if a real estimated elevation is available, sample near that value and clip to
    the SPICE min/max bounds. If the real value is unavailable, fall back to an
    evenly spaced range between the SPICE bounds.
    """

    lower = _finite_float(solar_elevation_min)
    upper = _finite_float(solar_elevation_max)
    real = _finite_float(real_solar_elevation)

    if lower is not None and upper is not None and lower > upper:
        raise ValueError("solar_elevation_min must be <= solar_elevation_max.")

    def clip(value: float) -> float:
        clipped = float(value)
        if lower is not None:
            clipped = max(lower, clipped)
        if upper is not None:
            clipped = min(upper, clipped)
        return clipped

    if real is not None:
        candidates = [clip(real + float(offset)) for offset in near_offsets]
    else:
        if lower is None and upper is None:
            candidates = [10.0, 20.0, 30.0, 40.0, 50.0]
        elif lower is None:
            step = abs(float(fallback_step_degrees)) or 10.0
            candidates = [upper - step * index for index in range(4, -1, -1)]
        elif upper is None:
            step = abs(float(fallback_step_degrees)) or 10.0
            candidates = [lower + step * index for index in range(5)]
        else:
            step = abs(float(fallback_step_degrees)) or 10.0
            sample_count = max(1, int(math.floor((upper - lower) / step)))
            candidates = [lower + step * index for index in range(sample_count + 1)]
            if not math.isclose(candidates[-1], upper):
                candidates.append(upper)

    rounded_unique = sorted({round(candidate, 6) for candidate in candidates})
    return tuple(rounded_unique)


def _normalize_image_for_probe(image_values: Any, invalid_mask: Any | None = None) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(image_values, dtype=np.float32)
    if values.ndim != 2:
        raise ValueError("image_values must be a 2-D grayscale array.")
    finite_mask = np.isfinite(values)
    if invalid_mask is not None:
        finite_mask &= ~np.asarray(invalid_mask, dtype=bool)

    valid_values = values[finite_mask]
    if valid_values.size == 0:
        return np.zeros(values.shape, dtype=np.uint8), finite_mask

    lower, upper = np.percentile(valid_values, [1.0, 99.0])
    if not math.isfinite(float(lower)) or not math.isfinite(float(upper)) or upper <= lower:
        lower = float(valid_values.min())
        upper = float(valid_values.max())
    if upper <= lower:
        normalized = np.zeros(values.shape, dtype=np.uint8)
    else:
        scaled = (np.clip(values, lower, upper) - lower) * (255.0 / (upper - lower))
        normalized = np.where(finite_mask, scaled, 0.0).astype(np.uint8)
    return normalized, finite_mask


def compute_real_image_texture_probe(
    image_values: Any,
    *,
    invalid_mask: Any | None = None,
    max_features: int | None = 500,
    sift_contrast_threshold: float = 0.04,
) -> ImageTextureProbe:
    """Compute the Phase-1 real-image texture probe metrics."""

    normalized, valid_mask = _normalize_image_for_probe(image_values, invalid_mask=invalid_mask)
    total_pixel_count = int(normalized.size)
    valid_pixel_count = int(valid_mask.sum())
    valid_pixel_ratio = 0.0 if total_pixel_count <= 0 else valid_pixel_count / total_pixel_count
    if valid_pixel_count <= 0:
        return ImageTextureProbe(
            keypoint_count=0,
            valid_pixel_count=0,
            total_pixel_count=total_pixel_count,
            keypoint_density=0.0,
            mean_gradient=0.0,
            laplacian_variance=0.0,
            entropy=0.0,
            valid_pixel_ratio=0.0,
            real_texture_score=0.0,
        )

    sift_kwargs: dict[str, int | float] = {"contrastThreshold": float(sift_contrast_threshold)}
    if max_features is not None:
        sift_kwargs["nfeatures"] = int(max_features)
    sift = cv2.SIFT_create(**sift_kwargs)
    sift_mask = np.where(valid_mask, 255, 0).astype(np.uint8)
    keypoints = sift.detect(normalized, sift_mask)
    keypoint_count = 0 if keypoints is None else len(keypoints)
    keypoint_density = 0.0 if valid_pixel_count <= 0 else keypoint_count / valid_pixel_count

    sobel_x = cv2.Sobel(normalized, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(normalized, cv2.CV_32F, 0, 1, ksize=3)
    gradient = cv2.magnitude(sobel_x, sobel_y)
    mean_gradient = float(gradient[valid_mask].mean()) if valid_pixel_count else 0.0
    laplacian = cv2.Laplacian(normalized, cv2.CV_32F)
    laplacian_variance = float(laplacian[valid_mask].var()) if valid_pixel_count else 0.0

    histogram, _ = np.histogram(normalized[valid_mask], bins=32, range=(0, 255), density=False)
    probabilities = histogram.astype(np.float64)
    probabilities = probabilities / probabilities.sum() if probabilities.sum() else probabilities
    nonzero_probabilities = probabilities[probabilities > 0.0]
    entropy = float(-(nonzero_probabilities * np.log2(nonzero_probabilities)).sum()) if nonzero_probabilities.size else 0.0

    keypoint_component = _clamp(keypoint_density / 0.002)
    gradient_component = _clamp(mean_gradient / 64.0)
    entropy_component = _clamp(entropy / 5.0)
    laplacian_component = _clamp(laplacian_variance / 1000.0)
    real_texture_score = valid_pixel_ratio * (
        0.35 * keypoint_component
        + 0.25 * gradient_component
        + 0.20 * entropy_component
        + 0.20 * laplacian_component
    )

    return ImageTextureProbe(
        keypoint_count=keypoint_count,
        valid_pixel_count=valid_pixel_count,
        total_pixel_count=total_pixel_count,
        keypoint_density=keypoint_density,
        mean_gradient=mean_gradient,
        laplacian_variance=laplacian_variance,
        entropy=entropy,
        valid_pixel_ratio=valid_pixel_ratio,
        real_texture_score=_clamp(real_texture_score),
    )


def _mean_present(values: Iterable[float | None]) -> float | None:
    present = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not present:
        return None
    return sum(present) / len(present)


def _absolute_gap(left: float | None, right: float | None) -> float | None:
    left_value = _finite_float(left)
    right_value = _finite_float(right)
    if left_value is None or right_value is None:
        return None
    return abs(left_value - right_value)


def route_matcher_for_pair(
    *,
    left_texture_probe: ImageTextureProbe,
    right_texture_probe: ImageTextureProbe,
    left_render_probe: RenderProbe | None = None,
    right_render_probe: RenderProbe | None = None,
    spice_constraints: SpiceLightingConstraints | None = None,
) -> PairRoutingDecision:
    """Route a pair to SIFT/BF, LightGlue, or LoFTR using Phase-1 rules."""

    left_render_probe = left_render_probe or RenderProbe()
    right_render_probe = right_render_probe or RenderProbe()
    mean_texture = (left_texture_probe.real_texture_score + right_texture_probe.real_texture_score) / 2.0
    mean_terrain = _mean_present(
        (
            left_render_probe.terrain_explainability_score,
            right_render_probe.terrain_explainability_score,
        )
    )
    render_elevation_gap = _absolute_gap(left_render_probe.best_render_elevation, right_render_probe.best_render_elevation)
    if render_elevation_gap is None and spice_constraints is not None:
        render_elevation_gap = _absolute_gap(
            spice_constraints.real_estimated_elevation_left,
            spice_constraints.real_estimated_elevation_right,
        )
    render_peak_sharpness = _mean_present(
        (
            left_render_probe.render_peak_sharpness,
            right_render_probe.render_peak_sharpness,
        )
    )

    gap_component = 0.0 if render_elevation_gap is None else _clamp(render_elevation_gap / 90.0)
    terrain_component = 0.0 if mean_terrain is None else _clamp(mean_terrain)
    estimated_difficulty = _clamp(1.0 - mean_texture + 0.45 * gap_component - 0.20 * terrain_component)

    small_lighting_gap = render_elevation_gap is None or render_elevation_gap <= 15.0
    medium_lighting_gap = render_elevation_gap is None or render_elevation_gap <= 35.0
    terrain_support = mean_terrain is None or mean_terrain >= 0.35

    if mean_texture >= 0.55 and small_lighting_gap and terrain_support:
        initial_matcher = SIFT_ROUTED_MATCHER_METHOD
        reason = "rich texture and small inferred lighting gap; route to SIFT descriptor matching first"
    elif mean_texture >= 0.28 and medium_lighting_gap:
        initial_matcher = LIGHTGLUE_MATCHER_METHOD
        reason = "moderate texture or moderate lighting gap; route to SuperPoint + LightGlue first"
    else:
        initial_matcher = LOFTR_MATCHER_METHOD
        reason = "weak texture or large inferred lighting gap; route to LoFTR first"

    fallback_chain = tuple(
        matcher for matcher in DEFAULT_ROUTER_FALLBACK_CHAIN if matcher != initial_matcher
    )
    if initial_matcher == LIGHTGLUE_MATCHER_METHOD:
        fallback_chain = (LOFTR_MATCHER_METHOD,)
    elif initial_matcher == LOFTR_MATCHER_METHOD:
        fallback_chain = ()

    return PairRoutingDecision(
        initial_matcher=initial_matcher,
        fallback_chain=fallback_chain,
        route_reason=reason,
        mean_real_texture_score=mean_texture,
        mean_terrain_explainability_score=mean_terrain,
        render_inferred_elevation_gap=render_elevation_gap,
        render_peak_sharpness=render_peak_sharpness,
        estimated_match_difficulty=estimated_difficulty,
    )


def build_pair_probe_sidecar(
    *,
    left_texture_probe: ImageTextureProbe,
    right_texture_probe: ImageTextureProbe,
    route_decision: PairRoutingDecision,
    left_render_probe: RenderProbe | None = None,
    right_render_probe: RenderProbe | None = None,
    spice_constraints: SpiceLightingConstraints | None = None,
    match_quality: dict[str, Any] | None = None,
    final_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable adaptive-route sidecar payload."""

    left_render_probe = left_render_probe or RenderProbe()
    right_render_probe = right_render_probe or RenderProbe()
    spice_constraints = spice_constraints or SpiceLightingConstraints()
    return {
        "left_image_probe": {
            **asdict(left_texture_probe),
            **asdict(left_render_probe),
        },
        "right_image_probe": {
            **asdict(right_texture_probe),
            **asdict(right_render_probe),
        },
        "spice_constraints": asdict(spice_constraints),
        "pair_route": asdict(route_decision),
        "match_quality": dict(match_quality or {}),
        "final_decision": dict(final_decision or {}),
    }


__all__ = [
    "DEFAULT_ROUTER_FALLBACK_CHAIN",
    "ImageTextureProbe",
    "LOFTR_MATCHER_METHOD",
    "LIGHTGLUE_MATCHER_METHOD",
    "PairRoutingDecision",
    "RenderProbe",
    "SIFT_ROUTED_MATCHER_METHOD",
    "SpiceLightingConstraints",
    "build_pair_probe_sidecar",
    "build_spice_constrained_elevation_candidates",
    "compute_real_image_texture_probe",
    "route_matcher_for_pair",
]