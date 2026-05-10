"""Matcher-agnostic `.key` refinement helpers for sparse DEM extraction.

Author: Geng Xun
Created: 2026-05-10
Last Modified: 2026-05-10
Updated: 2026-05-10  Geng Xun added staged MaximumCorrelation/Gruen refinement for synchronized DEM `.key` pairs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from controlnet_construct.keypoints import Keypoint, KeypointFile

from .key_pairs import load_key_point_pairs_from_key_files


FAILURE_EXAMPLE_LIMIT = 10
STAGE_ALIASES = {
    "maximum_correlation": "maximum_correlation",
    "maximum-correlation": "maximum_correlation",
    "maxcorr": "maximum_correlation",
    "gruen": "gruen",
}


@dataclass(frozen=True, slots=True)
class AutoRegStageOptions:
    pattern_samples: int
    pattern_lines: int
    search_samples: int
    search_lines: int
    tolerance: float
    subpixel: bool = True
    affine_translation_tolerance: float | None = None
    affine_scale_tolerance: float | None = None
    maximum_iterations: int | None = None


def _default_maximum_correlation_options() -> AutoRegStageOptions:
    return AutoRegStageOptions(
        pattern_samples=31,
        pattern_lines=31,
        search_samples=81,
        search_lines=81,
        tolerance=0.70,
        subpixel=True,
    )


def _default_gruen_options() -> AutoRegStageOptions:
    return AutoRegStageOptions(
        pattern_samples=21,
        pattern_lines=21,
        search_samples=41,
        search_lines=41,
        tolerance=0.10,
        subpixel=True,
        affine_translation_tolerance=0.2,
        affine_scale_tolerance=0.3,
        maximum_iterations=30,
    )


@dataclass(frozen=True, slots=True)
class KeyRefinementOptions:
    stages: tuple[str, ...] = ()
    maximum_correlation: AutoRegStageOptions = field(default_factory=_default_maximum_correlation_options)
    gruen: AutoRegStageOptions = field(default_factory=_default_gruen_options)


def normalize_refinement_stage(name: str) -> str:
    normalized = STAGE_ALIASES.get(name.strip().lower())
    if normalized is None:
        valid = ", ".join(sorted(STAGE_ALIASES))
        raise ValueError(f"Unsupported refinement stage {name!r}. Expected one of: {valid}.")
    return normalized


def normalize_refinement_stages(stage_names: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if not stage_names:
        return ()
    return tuple(normalize_refinement_stage(name) for name in stage_names)


def _enum_name(value) -> str:
    return getattr(value, "name", str(value).split(".")[-1])


def _build_autoreg_pvl(ip, *, algorithm_name: str, options: AutoRegStageOptions):
    if options.pattern_samples <= 0 or options.pattern_lines <= 0:
        raise ValueError("Pattern chip dimensions must be positive.")
    if options.search_samples < options.pattern_samples or options.search_lines < options.pattern_lines:
        raise ValueError("Search chip dimensions must be at least as large as the pattern chip dimensions.")

    pvl = ip.Pvl()
    autoreg_obj = ip.PvlObject("AutoRegistration")

    algorithm_group = ip.PvlGroup("Algorithm")
    algorithm_group.add_keyword(ip.PvlKeyword("Name", algorithm_name))
    algorithm_group.add_keyword(ip.PvlKeyword("Tolerance", str(options.tolerance)))
    if options.subpixel:
        algorithm_group.add_keyword(ip.PvlKeyword("SubpixelAccuracy", "True"))
    if options.affine_translation_tolerance is not None:
        algorithm_group.add_keyword(
            ip.PvlKeyword("AffineTranslationTolerance", str(options.affine_translation_tolerance))
        )
    if options.affine_scale_tolerance is not None:
        algorithm_group.add_keyword(ip.PvlKeyword("AffineScaleTolerance", str(options.affine_scale_tolerance)))
    if options.maximum_iterations is not None:
        algorithm_group.add_keyword(ip.PvlKeyword("MaximumIterations", str(options.maximum_iterations)))
    autoreg_obj.add_group(algorithm_group)

    pattern_group = ip.PvlGroup("PatternChip")
    pattern_group.add_keyword(ip.PvlKeyword("Samples", str(options.pattern_samples)))
    pattern_group.add_keyword(ip.PvlKeyword("Lines", str(options.pattern_lines)))
    pattern_group.add_keyword(ip.PvlKeyword("ValidPercent", "50"))
    pattern_group.add_keyword(ip.PvlKeyword("MinimumZScore", "1.5"))
    autoreg_obj.add_group(pattern_group)

    search_group = ip.PvlGroup("SearchChip")
    search_group.add_keyword(ip.PvlKeyword("Samples", str(options.search_samples)))
    search_group.add_keyword(ip.PvlKeyword("Lines", str(options.search_lines)))
    autoreg_obj.add_group(search_group)

    pvl.add_object(autoreg_obj)
    return pvl


def _create_stage_matcher(ip, stage_name: str, options: AutoRegStageOptions):
    if stage_name == "maximum_correlation":
        return ip.MaximumCorrelation(_build_autoreg_pvl(ip, algorithm_name="MaximumCorrelation", options=options))
    if stage_name == "gruen":
        return ip.Gruen(_build_autoreg_pvl(ip, algorithm_name="Gruen", options=options))
    raise ValueError(f"Unsupported refinement stage: {stage_name}")


def _stage_options_for(options: KeyRefinementOptions, stage_name: str) -> AutoRegStageOptions:
    if stage_name == "maximum_correlation":
        return options.maximum_correlation
    if stage_name == "gruen":
        return options.gruen
    raise ValueError(f"Unsupported refinement stage: {stage_name}")


def _register_single_match(
    matcher,
    *,
    left_cube,
    right_cube,
    left_point: Keypoint,
    right_seed: Keypoint,
    success_statuses: set[Any],
    stage_name: str,
) -> Keypoint:
    pattern_chip = matcher.pattern_chip()
    pattern_chip.tack_cube(left_point.sample, left_point.line)
    pattern_chip.load(left_cube)

    search_chip = matcher.search_chip()
    search_chip.tack_cube(right_seed.sample, right_seed.line)
    search_chip.load(right_cube)

    status = matcher.register()
    status_name = _enum_name(status)
    if status not in success_statuses or not matcher.success():
        raise RuntimeError(
            f"{stage_name} failed with status {status_name} "
            f"(goodness_of_fit={matcher.goodness_of_fit():.6f})."
        )

    return Keypoint(sample=float(matcher.cube_sample()), line=float(matcher.cube_line()))


def _stage_summary(
    *,
    stage_name: str,
    input_point_count: int,
    success_count: int,
    updated_count: int,
    failures: list[dict[str, object]],
) -> dict[str, object]:
    failed_count = len(failures)
    return {
        "stage": stage_name,
        "input_point_count": input_point_count,
        "success_count": success_count,
        "failed_count": failed_count,
        "updated_count": updated_count,
        "retained_original_count": input_point_count - updated_count,
        "failure_examples": failures[:FAILURE_EXAMPLE_LIMIT],
    }


def refine_keypoint_file_pair(
    *,
    left_cube,
    right_cube,
    left_key_file: KeypointFile,
    right_key_file: KeypointFile,
    ip,
    options: KeyRefinementOptions,
) -> tuple[KeypointFile, KeypointFile, dict[str, object]]:
    stages = normalize_refinement_stages(options.stages)
    load_key_point_pairs_from_key_files(left_key_file, right_key_file, left_cube=left_cube, right_cube=right_cube)
    if not stages:
        return left_key_file, right_key_file, {"applied": False, "stages": []}

    current_left = left_key_file
    current_right = right_key_file
    stage_summaries: list[dict[str, object]] = []
    success_statuses = {
        ip.AutoReg.RegisterStatus.SuccessPixel,
        ip.AutoReg.RegisterStatus.SuccessSubPixel,
    }

    for stage_name in stages:
        matcher = _create_stage_matcher(ip, stage_name, _stage_options_for(options, stage_name))
        refined_right_points: list[Keypoint] = []
        failures: list[dict[str, object]] = []
        success_count = 0
        updated_count = 0

        for index, (left_point, right_point) in enumerate(zip(current_left.points, current_right.points)):
            try:
                refined_point = _register_single_match(
                    matcher,
                    left_cube=left_cube,
                    right_cube=right_cube,
                    left_point=left_point,
                    right_seed=right_point,
                    success_statuses=success_statuses,
                    stage_name=stage_name,
                )
            except Exception as exc:
                refined_right_points.append(right_point)
                failures.append({"index": index, "reason": str(exc)})
                continue

            success_count += 1
            if refined_point != right_point:
                updated_count += 1
            refined_right_points.append(refined_point)

        current_right = KeypointFile(
            image_width=current_right.image_width,
            image_height=current_right.image_height,
            points=tuple(refined_right_points),
        )
        stage_summaries.append(
            _stage_summary(
                stage_name=stage_name,
                input_point_count=len(current_left.points),
                success_count=success_count,
                updated_count=updated_count,
                failures=failures,
            )
        )

    return current_left, current_right, {
        "applied": True,
        "stage_count": len(stage_summaries),
        "stages": stage_summaries,
    }