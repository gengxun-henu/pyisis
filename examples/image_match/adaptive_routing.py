"""Adaptive lighting-aware matcher routing helpers for image matching examples.

Author: Geng Xun
Created: 2026-05-14
Updated: 2026-05-14  Geng Xun added first-node texture probe, SPICE-constrained elevation candidates, pair routing, and JSON sidecar helpers.
Updated: 2026-05-14  Geng Xun added pure match-quality gating and fixed cascade planning helpers.
Updated: 2026-05-14  Geng Xun allowed adaptive sidecars to serialize quality reports and final decisions directly.
Updated: 2026-05-16  Geng Xun added named adaptive-routing quality profiles for user-facing route tuning.
Updated: 2026-05-18  Geng Xun added a conservative pair router that combines pair-level texture sparseness with lighting-difference scores plus a sidecar augmentation helper.
Updated: 2026-05-19  Geng Xun added optional nested tile diagnostics to the
    sparseness/lighting sidecar augmenter.
Updated: 2026-05-20  Geng Xun extended adaptive routing decisions with preset-aware deep config selection and route confidence summaries.
Updated: 2026-06-02  Geng Xun changed adaptive routing to prior-only matcher selection without post-match fallback cascades.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import math
import statistics
from typing import Any, Iterable

import cv2
import numpy as np


SIFT_ROUTED_MATCHER_METHOD = "bf"
FLANN_MATCHER_METHOD = "flann"
LIGHTGLUE_MATCHER_METHOD = "lightglue"
LOFTR_MATCHER_METHOD = "loftr"
DEFAULT_ROUTER_FALLBACK_CHAIN = ()
DEFAULT_ADAPTIVE_ROUTING_PROFILE = "balanced"
SUPPORTED_ADAPTIVE_ROUTING_PROFILES = (
    "balanced",
    "strict",
    "relaxed",
    "fast",
)
_FLOAT32_MAX = float(np.finfo(np.float32).max)


def _coerce_probe_values(image_values: Any) -> tuple[np.ndarray, np.ndarray]:
    raw_values = np.asarray(image_values, dtype=np.float64)
    if raw_values.ndim != 2:
        raise ValueError("image_values must be a 2-D grayscale array.")
    finite_mask = np.isfinite(raw_values) & (np.abs(raw_values) <= _FLOAT32_MAX)
    values = np.where(finite_mask, raw_values, 0.0).astype(np.float32)
    return values, finite_mask


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
    mean_real_texture_score: float | None
    mean_terrain_explainability_score: float | None
    render_inferred_elevation_gap: float | None
    render_peak_sharpness: float | None
    estimated_match_difficulty: float
    deep_match_config_path: str | None = None
    route_confidence: float | None = None


@dataclass(frozen=True, slots=True)
class MatchQualityReport:
    """Summary of post-match quality gating signals for one matcher result."""

    inlier_count: int
    total_match_count: int | None
    inlier_ratio: float
    coverage: float
    residual_summary: dict[str, float | int | None]
    quality_score: float
    accepted: bool
    rejection_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AdaptiveRoutingQualityProfile:
    """Named post-match quality-gate thresholds for adaptive routing."""

    profile: str
    min_inlier_count: int
    min_inlier_ratio: float
    min_coverage: float
    max_mean_residual: float
    max_p95_residual: float


_ADAPTIVE_ROUTING_QUALITY_PROFILES: dict[str, AdaptiveRoutingQualityProfile] = {
    "balanced": AdaptiveRoutingQualityProfile(
        profile="balanced",
        min_inlier_count=24,
        min_inlier_ratio=0.35,
        min_coverage=0.20,
        max_mean_residual=2.5,
        max_p95_residual=4.0,
    ),
    "strict": AdaptiveRoutingQualityProfile(
        profile="strict",
        min_inlier_count=36,
        min_inlier_ratio=0.45,
        min_coverage=0.30,
        max_mean_residual=1.8,
        max_p95_residual=3.0,
    ),
    "relaxed": AdaptiveRoutingQualityProfile(
        profile="relaxed",
        min_inlier_count=12,
        min_inlier_ratio=0.25,
        min_coverage=0.10,
        max_mean_residual=4.0,
        max_p95_residual=7.0,
    ),
    "fast": AdaptiveRoutingQualityProfile(
        profile="fast",
        min_inlier_count=12,
        min_inlier_ratio=0.20,
        min_coverage=0.08,
        max_mean_residual=5.0,
        max_p95_residual=8.0,
    ),
}


def normalize_adaptive_routing_profile(value: object) -> str:
    """Normalize a user-facing adaptive-routing profile name."""

    normalized = str(value).strip().lower().replace("_", "-")
    if normalized not in _ADAPTIVE_ROUTING_QUALITY_PROFILES:
        supported = ", ".join(SUPPORTED_ADAPTIVE_ROUTING_PROFILES)
        raise ValueError(f"Unsupported adaptive_routing_profile: {value!r}. Supported values: {supported}.")
    return normalized


def resolve_adaptive_routing_quality_profile(value: object = DEFAULT_ADAPTIVE_ROUTING_PROFILE) -> AdaptiveRoutingQualityProfile:
    """Return the expanded quality-gate thresholds for a named profile."""

    return _ADAPTIVE_ROUTING_QUALITY_PROFILES[normalize_adaptive_routing_profile(value)]


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
    values, finite_mask = _coerce_probe_values(image_values)
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


def _interpolated_percentile(values: list[float], percentile_rank: float) -> float:
    if not values:
        raise ValueError("values must not be empty.")
    if len(values) == 1:
        return float(values[0])
    clamped_rank = _clamp(percentile_rank)
    position = clamped_rank * (len(values) - 1)
    lower_index = int(math.floor(position))
    upper_index = int(math.ceil(position))
    if lower_index == upper_index:
        return float(values[lower_index])
    fraction = position - lower_index
    return float(values[lower_index] + (values[upper_index] - values[lower_index]) * fraction)


def _summarize_residuals(
    residuals: Iterable[float] | None = None,
    residual_summary: dict[str, float | int | None] | None = None,
) -> dict[str, float | int | None]:
    if residual_summary is not None:
        summary = dict(residual_summary)
        return {
            "count": int(summary.get("count", 0) or 0),
            "mean": _finite_float(summary.get("mean")),
            "median": _finite_float(summary.get("median")),
            "p95": _finite_float(summary.get("p95")),
            "max": _finite_float(summary.get("max")),
        }

    if residuals is None:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p95": None,
            "max": None,
        }

    values: list[float] = []
    for value in residuals:
        if value is None:
            continue
        resolved = float(value)
        if not math.isfinite(resolved):
            continue
        values.append(abs(resolved))
    values.sort()
    if not values:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p95": None,
            "max": None,
        }

    return {
        "count": len(values),
        "mean": float(sum(values) / len(values)),
        "median": float(statistics.median(values)),
        "p95": _interpolated_percentile(values, 0.95),
        "max": float(values[-1]),
    }


def evaluate_match_quality(
    *,
    inlier_count: int,
    coverage: float,
    total_match_count: int | None = None,
    inlier_ratio: float | None = None,
    residuals: Iterable[float] | None = None,
    residual_summary: dict[str, float | int | None] | None = None,
    min_inlier_count: int = 24,
    min_inlier_ratio: float = 0.35,
    min_coverage: float = 0.20,
    max_mean_residual: float = 2.5,
    max_p95_residual: float = 4.0,
) -> MatchQualityReport:
    """Evaluate whether one matcher result clears the post-match quality gate."""

    resolved_inlier_count = max(0, int(inlier_count))
    resolved_total_match_count = None if total_match_count is None else max(0, int(total_match_count))
    if inlier_ratio is None:
        if resolved_total_match_count in (None, 0):
            resolved_inlier_ratio = 0.0
        else:
            resolved_inlier_ratio = resolved_inlier_count / resolved_total_match_count
    else:
        resolved_inlier_ratio = _clamp(float(inlier_ratio))

    resolved_coverage = _clamp(float(coverage))
    resolved_residual_summary = _summarize_residuals(
        residuals=residuals,
        residual_summary=residual_summary,
    )

    rejection_reasons: list[str] = []
    if resolved_inlier_count < int(min_inlier_count):
        rejection_reasons.append("insufficient_inlier_count")
    if resolved_inlier_ratio < float(min_inlier_ratio):
        rejection_reasons.append("insufficient_inlier_ratio")
    if resolved_coverage < float(min_coverage):
        rejection_reasons.append("insufficient_coverage")

    residual_mean = _finite_float(resolved_residual_summary.get("mean"))
    residual_p95 = _finite_float(resolved_residual_summary.get("p95"))
    if residual_mean is None or residual_p95 is None:
        rejection_reasons.append("missing_residual_quality")
    else:
        if residual_mean > float(max_mean_residual):
            rejection_reasons.append("mean_residual_too_large")
        if residual_p95 > float(max_p95_residual):
            rejection_reasons.append("p95_residual_too_large")

    target_inlier_count = max(int(min_inlier_count) * 2, 1)
    count_component = _clamp(resolved_inlier_count / float(target_inlier_count))
    ratio_component = _clamp(resolved_inlier_ratio)
    coverage_component = _clamp(resolved_coverage)
    if residual_mean is None:
        residual_component = 0.0
    else:
        residual_component = max(
            0.0,
            1.0 - (residual_mean / max(float(max_mean_residual), 1e-6)),
        )

    quality_score = _clamp(
        0.30 * count_component
        + 0.30 * ratio_component
        + 0.25 * coverage_component
        + 0.15 * residual_component
    )

    return MatchQualityReport(
        inlier_count=resolved_inlier_count,
        total_match_count=resolved_total_match_count,
        inlier_ratio=resolved_inlier_ratio,
        coverage=resolved_coverage,
        residual_summary=resolved_residual_summary,
        quality_score=quality_score,
        accepted=not rejection_reasons,
        rejection_reasons=tuple(rejection_reasons),
    )


def build_cascade_plan(
    *,
    initial_matcher: str,
    fallback_chain: Iterable[str] = (),
    canonical_order: Iterable[str] = DEFAULT_ROUTER_FALLBACK_CHAIN,
) -> tuple[str, ...]:
    """Return the single prior-selected matcher for no-fallback adaptive routing."""

    supported_matchers = {
        SIFT_ROUTED_MATCHER_METHOD,
        FLANN_MATCHER_METHOD,
        LIGHTGLUE_MATCHER_METHOD,
        LOFTR_MATCHER_METHOD,
        *tuple(canonical_order),
    }
    if initial_matcher not in supported_matchers:
        raise ValueError(f"Unsupported initial_matcher: {initial_matcher!r}")
    return (initial_matcher,)


def decide_post_match_action(
    *,
    current_matcher: str,
    quality_report: MatchQualityReport,
    cascade_plan: Iterable[str],
    current_index: int | None = None,
) -> dict[str, Any]:
    """Choose accept versus fallback after evaluating one matcher result."""

    plan = tuple(cascade_plan)
    if not plan:
        raise ValueError("cascade_plan must contain at least one matcher.")
    if current_matcher not in plan:
        raise ValueError("current_matcher must be present in cascade_plan.")

    resolved_current_index = plan.index(current_matcher) if current_index is None else int(current_index)
    fallback_used = resolved_current_index > 0
    if quality_report.accepted:
        return {
            "selected_matcher": current_matcher,
            "accepted": True,
            "fallback_used": fallback_used,
            "next_matcher": None,
            "stop_reason": "quality_accepted",
            "rejection_reasons": (),
        }

    return {
        "selected_matcher": current_matcher,
        "accepted": False,
        "fallback_used": fallback_used,
        "next_matcher": None,
        "stop_reason": "quality_insufficient_no_fallback",
        "rejection_reasons": quality_report.rejection_reasons,
    }


def _json_ready(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_ready(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def route_matcher_for_pair(
    *,
    left_texture_probe: ImageTextureProbe,
    right_texture_probe: ImageTextureProbe,
    left_render_probe: RenderProbe | None = None,
    right_render_probe: RenderProbe | None = None,
    spice_constraints: SpiceLightingConstraints | None = None,
) -> PairRoutingDecision:
    """Route a pair to one prior-selected matcher without post-match fallback."""

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
        initial_matcher = FLANN_MATCHER_METHOD
        reason = "rich texture and small inferred lighting gap; route to SIFT + FLANN"
    elif mean_texture >= 0.28 and medium_lighting_gap:
        initial_matcher = LIGHTGLUE_MATCHER_METHOD
        reason = "moderate texture or moderate lighting gap; route to SIFT + LightGlue"
    else:
        initial_matcher = LOFTR_MATCHER_METHOD
        reason = "weak texture or large inferred lighting gap; route to LoFTR"

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
        route_confidence=_clamp(1.0 - abs(estimated_difficulty - 0.5)),
    )


def build_pair_probe_sidecar(
    *,
    left_texture_probe: ImageTextureProbe,
    right_texture_probe: ImageTextureProbe,
    route_decision: PairRoutingDecision,
    left_render_probe: RenderProbe | None = None,
    right_render_probe: RenderProbe | None = None,
    spice_constraints: SpiceLightingConstraints | None = None,
    match_quality: MatchQualityReport | dict[str, Any] | None = None,
    final_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable adaptive-route sidecar payload."""

    left_render_probe = left_render_probe or RenderProbe()
    right_render_probe = right_render_probe or RenderProbe()
    spice_constraints = spice_constraints or SpiceLightingConstraints()
    return _json_ready({
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
        "match_quality": match_quality or {},
        "final_decision": final_decision or {},
    })


def route_matcher_for_pair_with_sparseness(
    *,
    pair_texture_sparseness: float | None,
    lighting_difference_score: float | None,
    left_texture_probe: ImageTextureProbe | None = None,
    right_texture_probe: ImageTextureProbe | None = None,
    sparseness_low_threshold: float = 0.35,
    sparseness_high_threshold: float = 0.65,
    lighting_low_threshold: float = 0.20,
    lighting_high_threshold: float = 0.55,
    min_texture_probe_keypoints: int = 12,
    min_texture_probe_keypoint_density: float = 1.0e-5,
    traditional_matcher: str = FLANN_MATCHER_METHOD,
    adaptive_routing_deep_presets: dict[str, str] | None = None,
) -> PairRoutingDecision:
    """Conservative Phase-7 router using pair texture sparseness and lighting difference.

    Semantics:
        - ``pair_texture_sparseness``: ``0 = rich, 1 = sparse``
        - ``lighting_difference_score``: ``0 = identical lighting, 1 = opposite``

    Rules:
        - low sparseness and low lighting difference -> SIFT+FLANN
        - moderate texture/lighting -> SIFT+LightGlue as the primary deep route
        - weak-to-moderate texture without extreme lighting -> SuperPoint+LightGlue
        - high sparseness and high lighting difference, or either extreme -> LoFTR
    """

    resolved_sparseness = _finite_float(pair_texture_sparseness)
    resolved_lighting = _finite_float(lighting_difference_score)
    texture_probes = tuple(probe for probe in (left_texture_probe, right_texture_probe) if probe is not None)
    low_probe_keypoints = bool(texture_probes) and any(
        int(probe.keypoint_count) < int(min_texture_probe_keypoints)
        for probe in texture_probes
    )
    low_probe_density = bool(texture_probes) and any(
        float(probe.keypoint_density) < float(min_texture_probe_keypoint_density)
        for probe in texture_probes
    )
    preset_map = {
        str(key).strip().lower(): str(value)
        for key, value in (adaptive_routing_deep_presets or {}).items()
        if value not in (None, "")
    }
    route_confidence = 0.5

    if low_probe_keypoints or low_probe_density:
        initial_matcher = LOFTR_MATCHER_METHOD
        reason = (
            "texture probe extracted too few keypoints on at least one image; "
            "route directly to LoFTR"
        )
        route_confidence = 0.85
    elif resolved_sparseness is None and resolved_lighting is None:
        initial_matcher = LIGHTGLUE_MATCHER_METHOD
        reason = (
            "pair-level texture sparseness and lighting difference are both unavailable; "
            "route to SIFT + LightGlue as the default deep matcher"
        )
        route_confidence = 0.5
    else:
        is_sparse_low = resolved_sparseness is not None and resolved_sparseness <= float(sparseness_low_threshold)
        is_sparse_high = resolved_sparseness is not None and resolved_sparseness >= float(sparseness_high_threshold)
        is_lighting_low = resolved_lighting is not None and resolved_lighting <= float(lighting_low_threshold)
        is_lighting_high = resolved_lighting is not None and resolved_lighting >= float(lighting_high_threshold)

        if is_sparse_high and is_lighting_high:
            initial_matcher = LOFTR_MATCHER_METHOD
            reason = "high texture sparseness and large lighting difference; route to LoFTR"
            sparseness_confidence = 0.0 if resolved_sparseness is None else _clamp(
                (resolved_sparseness - float(sparseness_high_threshold))
                / max(1.0 - float(sparseness_high_threshold), 1e-6)
            )
            lighting_confidence = 0.0 if resolved_lighting is None else _clamp(
                (resolved_lighting - float(lighting_high_threshold))
                / max(1.0 - float(lighting_high_threshold), 1e-6)
            )
            route_confidence = _clamp(0.75 + 0.25 * max(sparseness_confidence, lighting_confidence))
        elif (
            resolved_sparseness is not None
            and resolved_sparseness >= 0.85
        ) or (
            resolved_lighting is not None
            and resolved_lighting >= 0.75
        ):
            initial_matcher = LOFTR_MATCHER_METHOD
            reason = "extreme texture sparseness or extreme lighting difference; route to LoFTR"
            route_confidence = 0.80
        elif is_sparse_low and (resolved_lighting is None or is_lighting_low):
            initial_matcher = FLANN_MATCHER_METHOD
            reason = "rich texture and small lighting difference; route to SIFT + FLANN"
            sparseness_confidence = 1.0 if resolved_sparseness is None else _clamp(
                1.0 - (resolved_sparseness / max(float(sparseness_low_threshold), 1e-6))
            )
            lighting_confidence = 1.0 if resolved_lighting is None else _clamp(
                1.0 - (resolved_lighting / max(float(lighting_low_threshold), 1e-6))
            )
            route_confidence = _clamp(0.70 + 0.30 * min(sparseness_confidence, lighting_confidence))
        elif resolved_sparseness is not None and resolved_sparseness >= 0.58 and not is_lighting_high:
            initial_matcher = LIGHTGLUE_MATCHER_METHOD
            reason = "weak-to-moderate texture with non-extreme lighting; route to SuperPoint + LightGlue"
            route_confidence = 0.62
        else:
            initial_matcher = LIGHTGLUE_MATCHER_METHOD
            reason = "moderate texture or moderate lighting difference; route to SIFT + LightGlue"
            midpoint_sparseness = (
                0.5
                if resolved_sparseness is None
                else min(
                    abs(resolved_sparseness - float(sparseness_low_threshold)),
                    abs(float(sparseness_high_threshold) - resolved_sparseness),
                )
            )
            midpoint_lighting = (
                0.5
                if resolved_lighting is None
                else min(
                    abs(resolved_lighting - float(lighting_low_threshold)),
                    abs(float(lighting_high_threshold) - resolved_lighting),
                )
            )
            route_confidence = _clamp(0.55 + 0.15 * max(midpoint_sparseness, midpoint_lighting))

    fallback_chain = ()

    deep_match_config_path = None
    if initial_matcher == LIGHTGLUE_MATCHER_METHOD:
        if "SuperPoint + LightGlue" in reason:
            deep_match_config_path = (
                preset_map.get("superpoint_lightglue")
                or preset_map.get("lightglue_superpoint")
                or preset_map.get(LIGHTGLUE_MATCHER_METHOD)
            )
        else:
            deep_match_config_path = (
                preset_map.get("sift_lightglue")
                or preset_map.get(LIGHTGLUE_MATCHER_METHOD)
            )
    elif initial_matcher == LOFTR_MATCHER_METHOD:
        deep_match_config_path = preset_map.get(LOFTR_MATCHER_METHOD)

    # Use the pair sparseness (0..1) as a proxy "1 - mean_real_texture_score" for
    # legacy sidecar compatibility. When no valid texture tiles are available,
    # keep the value missing instead of manufacturing neutral evidence.
    mean_real_texture_score = (
        None if resolved_sparseness is None else _clamp(1.0 - resolved_sparseness)
    )
    estimated_difficulty = _clamp(
        (0.0 if resolved_sparseness is None else resolved_sparseness)
        + 0.5 * (0.0 if resolved_lighting is None else resolved_lighting)
    )

    return PairRoutingDecision(
        initial_matcher=initial_matcher,
        fallback_chain=fallback_chain,
        route_reason=reason,
        mean_real_texture_score=mean_real_texture_score,
        mean_terrain_explainability_score=None,
        render_inferred_elevation_gap=None,
        render_peak_sharpness=None,
        estimated_match_difficulty=estimated_difficulty,
        deep_match_config_path=deep_match_config_path,
        route_confidence=route_confidence,
    )


def augment_pair_probe_sidecar_with_sparseness_lighting(
    sidecar: dict[str, Any],
    *,
    pair_sparseness_summary: dict[str, Any] | None = None,
    lighting_difference_summary: dict[str, Any] | None = None,
    tile_diagnostics_summary: dict[str, Any] | None = None,
    routing_thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Add texture-sparseness and lighting-difference diagnostics to a sidecar.

    Backwards-compatible: missing inputs are stored as empty mappings instead
    of removed keys so downstream consumers can rely on the schema shape.
    """

    augmented = dict(sidecar)
    augmented["texture_sparseness"] = _json_ready(pair_sparseness_summary or {})
    augmented["lighting_difference"] = _json_ready(lighting_difference_summary or {})
    if tile_diagnostics_summary is not None:
        augmented["tile_diagnostics"] = _json_ready(tile_diagnostics_summary)
    if routing_thresholds:
        augmented["routing_thresholds"] = _json_ready(routing_thresholds)
    return augmented


__all__ = [
    "AdaptiveRoutingQualityProfile",
    "DEFAULT_ADAPTIVE_ROUTING_PROFILE",
    "DEFAULT_ROUTER_FALLBACK_CHAIN",
    "ImageTextureProbe",
    "LOFTR_MATCHER_METHOD",
    "LIGHTGLUE_MATCHER_METHOD",
    "MatchQualityReport",
    "PairRoutingDecision",
    "RenderProbe",
    "SIFT_ROUTED_MATCHER_METHOD",
    "SpiceLightingConstraints",
    "SUPPORTED_ADAPTIVE_ROUTING_PROFILES",
    "augment_pair_probe_sidecar_with_sparseness_lighting",
    "build_pair_probe_sidecar",
    "build_cascade_plan",
    "build_spice_constrained_elevation_candidates",
    "compute_real_image_texture_probe",
    "decide_post_match_action",
    "evaluate_match_quality",
    "normalize_adaptive_routing_profile",
    "resolve_adaptive_routing_quality_profile",
    "route_matcher_for_pair",
    "route_matcher_for_pair_with_sparseness",
]
