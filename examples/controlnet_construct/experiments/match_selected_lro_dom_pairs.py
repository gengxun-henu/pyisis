"""Match selected LRO NAC DOM pair folders with RANSAC-only summaries.

Author: Geng Xun
Created: 2026-05-29
Updated: 2026-05-29  Geng Xun added DOM-based adaptive and SIFT+FLANN matching
    for selected pair folders with RANSAC-only visualizations and statistics.
Updated: 2026-05-29  Geng Xun switched selected DOM matching from TIFF previews
    to DOM CUBE rasters with configurable invalid-pixel filtering and fixed
    four-method comparisons.
Updated: 2026-05-29  Geng Xun added pair-index slicing so large deep-matcher
    batches can be run one pair per process without cumulative memory growth.
Updated: 2026-05-29  Geng Xun added an official local LightGlue backend option
    so SuperPoint+LightGlue can run when kornia lacks SuperPoint.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import sys
from typing import Any

import cv2
import numpy as np

EXAMPLES_DIR = Path(__file__).resolve().parents[2]
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from image_match.preprocess import expand_invalid_mask_for_radius, summarize_valid_pixels, stretch_to_byte
from image_match.tile_matching import _read_cube_window, _resolved_invalid_values_for_cube
from image_match.tiling import TileWindow
from controlnet_construct.deep_match_config import DeepMatchRuntimeConfig

import isis_pybind as ip


DEFAULT_OFFICIAL_LIGHTGLUE_ROOT = Path("/home/gengxun/PlanetaryMapping/asp360_new/LightGlue")

if __package__ in {None, ""}:
    from match_selected_lro_pairs import (  # noqa: E402
        DEEP_MATCHERS,
        DEFAULT_PAIR_ROOT,
        _finite_float,
        _load_metadata,
        _match_with_deep,
        _match_with_sift,
        _route_pair,
        _sanitize_matches,
        _write_visualization,
        discover_pair_folders,
    )
else:
    from .match_selected_lro_pairs import (
        DEEP_MATCHERS,
        DEFAULT_PAIR_ROOT,
        _finite_float,
        _load_metadata,
        _match_with_deep,
        _match_with_sift,
        _route_pair,
        _sanitize_matches,
        _write_visualization,
        discover_pair_folders,
    )


@dataclass(frozen=True, slots=True)
class DomMethodSummary:
    pair_folder: str
    method_label: str
    latitude_band: str
    selection_class: str
    left_product_id: str
    right_product_id: str
    left_dom_cube: str
    right_dom_cube: str
    left_scale: float
    right_scale: float
    left_valid_pixel_count: int
    right_valid_pixel_count: int
    left_invalid_pixel_count: int
    right_invalid_pixel_count: int
    left_valid_pixel_ratio: float
    right_valid_pixel_ratio: float
    requested_matcher: str
    effective_matcher: str
    fallback_used: bool
    fallback_reason: str | None
    route_reason: str
    route_confidence: float | None
    pair_texture_sparseness: float | None
    lighting_difference_score: float | None
    candidate_match_count_before_ransac: int
    ransac_match_count: int
    ransac_inlier_ratio: float
    left_feature_count: int | None
    right_feature_count: int | None
    visualization_path: str
    metadata_path: str
    status: str
    error: str | None


@dataclass(frozen=True, slots=True)
class CubeImage:
    path: Path
    image: np.ndarray
    valid_mask: np.ndarray
    scale: float
    valid_pixel_count: int
    invalid_pixel_count: int
    valid_pixel_ratio: float


def _find_dom_cube(pair_folder: Path, metadata: dict[str, Any], side: str, *, dom_subdir: str) -> Path:
    product_id = str(metadata[f"{side}_product_id"])
    dom_dir = pair_folder / dom_subdir
    exact = dom_dir / f"dom_REDUCED_{product_id}.cub"
    if exact.exists():
        return exact
    matches = sorted(dom_dir.glob(f"*{product_id}*.cub"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"No DOM CUBE found for {product_id} under {dom_dir}")


def _read_dom_cube_image(cube_path: Path, args: argparse.Namespace) -> CubeImage:
    cube = ip.Cube()
    try:
        cube.open(str(cube_path), "r")
        width = int(cube.sample_count())
        height = int(cube.line_count())
        values = _read_cube_window(cube, TileWindow(start_x=0, start_y=0, width=width, height=height), band=args.band)
        invalid_values = _resolved_invalid_values_for_cube(cube, tuple(args.invalid_value or ()))
    finally:
        cube.close()

    invalid_mask, valid_stats = summarize_valid_pixels(
        values,
        invalid_values=invalid_values,
        special_pixel_abs_threshold=args.special_pixel_abs_threshold,
    )
    invalid_mask = expand_invalid_mask_for_radius(invalid_mask, invalid_pixel_radius=args.invalid_pixel_radius)
    invalid_count = int(invalid_mask.sum())
    valid_count = int(invalid_mask.size) - invalid_count
    valid_ratio = 0.0 if invalid_mask.size <= 0 else valid_count / int(invalid_mask.size)

    if valid_count <= 0:
        image_u8 = np.zeros(values.shape, dtype=np.uint8)
    else:
        image_u8, invalid_mask, _ = stretch_to_byte(
            values,
            minimum_value=args.minimum_value,
            maximum_value=args.maximum_value,
            lower_percent=args.lower_percent,
            upper_percent=args.upper_percent,
            invalid_values=invalid_values,
            special_pixel_abs_threshold=args.special_pixel_abs_threshold,
            invalid_mask=invalid_mask,
        )

    scale = 1.0
    valid_mask = np.where(invalid_mask, 0, 255).astype(np.uint8)
    if args.matching_target_long_edge is not None:
        long_edge = max(image_u8.shape[:2])
        if long_edge > int(args.matching_target_long_edge):
            scale = float(args.matching_target_long_edge) / float(long_edge)
            new_width = max(1, int(round(image_u8.shape[1] * scale)))
            new_height = max(1, int(round(image_u8.shape[0] * scale)))
            image_u8 = cv2.resize(image_u8, (new_width, new_height), interpolation=cv2.INTER_AREA)
            valid_mask = cv2.resize(valid_mask, (new_width, new_height), interpolation=cv2.INTER_NEAREST)

    return CubeImage(
        path=cube_path,
        image=image_u8,
        valid_mask=valid_mask,
        scale=scale,
        valid_pixel_count=int(valid_stats.valid_pixel_count if args.invalid_pixel_radius == 0 else valid_count),
        invalid_pixel_count=int(valid_stats.invalid_pixel_count if args.invalid_pixel_radius == 0 else invalid_count),
        valid_pixel_ratio=float(valid_stats.valid_pixel_ratio if args.invalid_pixel_radius == 0 else valid_ratio),
    )


def _ransac_inlier_matches(
    left_keypoints: list[cv2.KeyPoint],
    right_keypoints: list[cv2.KeyPoint],
    matches: list[cv2.DMatch],
    *,
    ransac_reproj_threshold: float,
) -> tuple[list[cv2.DMatch], float]:
    matches = _sanitize_matches(left_keypoints, right_keypoints, matches)
    if len(matches) < 8:
        return [], 0.0
    left_points = np.float32([left_keypoints[match.queryIdx].pt for match in matches]).reshape(-1, 1, 2)
    right_points = np.float32([right_keypoints[match.trainIdx].pt for match in matches]).reshape(-1, 1, 2)
    _, mask = cv2.findFundamentalMat(
        left_points,
        right_points,
        cv2.FM_RANSAC,
        float(ransac_reproj_threshold),
        0.99,
    )
    if mask is None:
        return [], 0.0
    keep = mask.reshape(-1).astype(bool)
    inlier_matches = [match for match, accepted in zip(matches, keep, strict=False) if accepted]
    return inlier_matches, (len(inlier_matches) / len(matches) if matches else 0.0)


def _filter_matches_by_valid_masks(
    left_keypoints: list[cv2.KeyPoint],
    right_keypoints: list[cv2.KeyPoint],
    matches: list[cv2.DMatch],
    left_mask: np.ndarray,
    right_mask: np.ndarray,
) -> list[cv2.DMatch]:
    left_height, left_width = left_mask.shape[:2]
    right_height, right_width = right_mask.shape[:2]
    filtered: list[cv2.DMatch] = []
    for match in matches:
        left_point = left_keypoints[match.queryIdx].pt
        right_point = right_keypoints[match.trainIdx].pt
        left_x = int(round(float(left_point[0])))
        left_y = int(round(float(left_point[1])))
        right_x = int(round(float(right_point[0])))
        right_y = int(round(float(right_point[1])))
        if not (0 <= left_x < left_width and 0 <= left_y < left_height):
            continue
        if not (0 <= right_x < right_width and 0 <= right_y < right_height):
            continue
        if left_mask[left_y, left_x] == 0 or right_mask[right_y, right_x] == 0:
            continue
        filtered.append(match)
    return filtered


def _deep_runtime_config_for_method(matcher_method: str, args: argparse.Namespace) -> DeepMatchRuntimeConfig | None:
    if matcher_method != "lightglue":
        return None
    backend = str(args.lightglue_backend).strip().lower()
    official_root = args.official_lightglue_root.expanduser().resolve()
    if backend == "auto":
        backend = "official" if official_root.is_dir() else "kornia"
    if backend != "official":
        return None
    if str(official_root) not in sys.path:
        sys.path.insert(0, str(official_root))
    feature_options = {"max_keypoints": int(args.lightglue_max_keypoints)}
    matcher_options = {"backend": "official"}
    return DeepMatchRuntimeConfig(
        matcher_method="lightglue",
        feature_extractor_method="superpoint",
        prefer_gpu=not args.no_gpu,
        device_dtype="float32",
        fallback_on_error=None,
        raw_config={
            "matcher": {"method": "lightglue", **matcher_options},
            "feature_extractor": {"method": "superpoint", **feature_options},
        },
        matcher_options=matcher_options,
        feature_options=feature_options,
        device_options={"dtype": "float32"},
    )


def _run_matcher(
    left_image: np.ndarray,
    right_image: np.ndarray,
    left_mask: np.ndarray,
    right_mask: np.ndarray,
    *,
    matcher_method: str,
    args: argparse.Namespace,
) -> tuple[str, bool, str | None, list[cv2.KeyPoint], list[cv2.KeyPoint], list[cv2.DMatch], int | None, int | None]:
    fallback_used = False
    fallback_reason = None
    effective_matcher = matcher_method
    try:
        if matcher_method in DEEP_MATCHERS and not args.no_deep:
            deep_left_mask = None if matcher_method == "loftr" else left_mask
            deep_right_mask = None if matcher_method == "loftr" else right_mask
            runtime_config = _deep_runtime_config_for_method(matcher_method, args)
            left_keypoints, right_keypoints, matches, left_feature_count, right_feature_count = _match_with_deep(
                left_image,
                right_image,
                matcher_method=matcher_method,
                prefer_gpu=not args.no_gpu,
                left_mask=deep_left_mask,
                right_mask=deep_right_mask,
                runtime_config=runtime_config,
            )
        else:
            sift_method = matcher_method if matcher_method in {"bf", "flann"} else "bf"
            left_keypoints, right_keypoints, matches, left_feature_count, right_feature_count = _match_with_sift(
                left_image,
                right_image,
                matcher_method=sift_method,
                ratio_test=args.ratio_test,
                max_features=args.max_features,
                left_mask=left_mask,
                right_mask=right_mask,
            )
            if matcher_method in DEEP_MATCHERS:
                effective_matcher = "bf"
                fallback_used = True
                fallback_reason = "deep matching disabled by --no-deep"
    except Exception as exc:  # noqa: BLE001 - fallback keeps both requested outputs available
        fallback_used = True
        fallback_reason = f"{type(exc).__name__}: {exc}"
        effective_matcher = "bf"
        left_keypoints, right_keypoints, matches, left_feature_count, right_feature_count = _match_with_sift(
            left_image,
            right_image,
            matcher_method="bf",
            ratio_test=args.ratio_test,
            max_features=args.max_features,
            left_mask=left_mask,
            right_mask=right_mask,
        )
    filtered_matches = _filter_matches_by_valid_masks(
        left_keypoints,
        right_keypoints,
        _sanitize_matches(left_keypoints, right_keypoints, matches),
        left_mask,
        right_mask,
    )
    return (
        effective_matcher,
        fallback_used,
        fallback_reason,
        left_keypoints,
        right_keypoints,
        filtered_matches,
        left_feature_count,
        right_feature_count,
    )


def _match_one_method(
    pair_folder: Path,
    metadata: dict[str, Any],
    left_cube_image: CubeImage,
    right_cube_image: CubeImage,
    *,
    method_label: str,
    requested_matcher: str,
    route_reason: str,
    route_confidence: float | None,
    output_dir: Path,
    args: argparse.Namespace,
) -> DomMethodSummary:
    visualization_path = output_dir / f"{method_label}_ransac_lines.png"
    metadata_path = output_dir / f"{method_label}_ransac_metadata.json"
    try:
        (
            effective_matcher,
            fallback_used,
            fallback_reason,
            left_keypoints,
            right_keypoints,
            candidate_matches,
            left_feature_count,
            right_feature_count,
        ) = _run_matcher(
            left_cube_image.image,
            right_cube_image.image,
            left_cube_image.valid_mask,
            right_cube_image.valid_mask,
            matcher_method=requested_matcher,
            args=args,
        )
        inlier_matches, inlier_ratio = _ransac_inlier_matches(
            left_keypoints,
            right_keypoints,
            candidate_matches,
            ransac_reproj_threshold=args.ransac_reproj_threshold,
        )
        _write_visualization(
            visualization_path,
            left_cube_image.image,
            right_cube_image.image,
            left_keypoints,
            right_keypoints,
            inlier_matches,
            max_lines=args.max_lines,
        )
        status = "matched" if inlier_matches else "matched_no_ransac_inliers"
        summary = DomMethodSummary(
            pair_folder=str(pair_folder),
            method_label=method_label,
            latitude_band=str(metadata.get("latitude_band", "")),
            selection_class=str(metadata.get("selection_class", "")),
            left_product_id=str(metadata.get("left_product_id", "")),
            right_product_id=str(metadata.get("right_product_id", "")),
            left_dom_cube=str(left_cube_image.path),
            right_dom_cube=str(right_cube_image.path),
            left_scale=left_cube_image.scale,
            right_scale=right_cube_image.scale,
            left_valid_pixel_count=left_cube_image.valid_pixel_count,
            right_valid_pixel_count=right_cube_image.valid_pixel_count,
            left_invalid_pixel_count=left_cube_image.invalid_pixel_count,
            right_invalid_pixel_count=right_cube_image.invalid_pixel_count,
            left_valid_pixel_ratio=left_cube_image.valid_pixel_ratio,
            right_valid_pixel_ratio=right_cube_image.valid_pixel_ratio,
            requested_matcher=requested_matcher,
            effective_matcher=effective_matcher,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            route_reason=route_reason,
            route_confidence=route_confidence,
            pair_texture_sparseness=_finite_float(metadata.get("pair_texture_sparseness")),
            lighting_difference_score=_finite_float(metadata.get("lighting_difference_score")),
            candidate_match_count_before_ransac=len(candidate_matches),
            ransac_match_count=len(inlier_matches),
            ransac_inlier_ratio=inlier_ratio,
            left_feature_count=left_feature_count,
            right_feature_count=right_feature_count,
            visualization_path=str(visualization_path),
            metadata_path=str(metadata_path),
            status=status,
            error=None,
        )
    except Exception as exc:  # noqa: BLE001 - record the failed method and continue the batch
        summary = DomMethodSummary(
            pair_folder=str(pair_folder),
            method_label=method_label,
            latitude_band=str(metadata.get("latitude_band", "")),
            selection_class=str(metadata.get("selection_class", "")),
            left_product_id=str(metadata.get("left_product_id", "")),
            right_product_id=str(metadata.get("right_product_id", "")),
            left_dom_cube=str(left_cube_image.path),
            right_dom_cube=str(right_cube_image.path),
            left_scale=left_cube_image.scale,
            right_scale=right_cube_image.scale,
            left_valid_pixel_count=left_cube_image.valid_pixel_count,
            right_valid_pixel_count=right_cube_image.valid_pixel_count,
            left_invalid_pixel_count=left_cube_image.invalid_pixel_count,
            right_invalid_pixel_count=right_cube_image.invalid_pixel_count,
            left_valid_pixel_ratio=left_cube_image.valid_pixel_ratio,
            right_valid_pixel_ratio=right_cube_image.valid_pixel_ratio,
            requested_matcher=requested_matcher,
            effective_matcher="",
            fallback_used=False,
            fallback_reason=None,
            route_reason=route_reason,
            route_confidence=route_confidence,
            pair_texture_sparseness=_finite_float(metadata.get("pair_texture_sparseness")),
            lighting_difference_score=_finite_float(metadata.get("lighting_difference_score")),
            candidate_match_count_before_ransac=0,
            ransac_match_count=0,
            ransac_inlier_ratio=0.0,
            left_feature_count=None,
            right_feature_count=None,
            visualization_path=str(visualization_path),
            metadata_path=str(metadata_path),
            status="failed",
            error=f"{type(exc).__name__}: {exc}",
        )
    metadata_path.write_text(json.dumps(asdict(summary), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def match_pair_folder_dom(pair_folder: Path, args: argparse.Namespace) -> list[DomMethodSummary]:
    metadata = _load_metadata(pair_folder)
    left_dom_cube = _find_dom_cube(pair_folder, metadata, "left", dom_subdir=args.dom_subdir)
    right_dom_cube = _find_dom_cube(pair_folder, metadata, "right", dom_subdir=args.dom_subdir)
    output_dir = pair_folder / args.output_subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    left_cube_image = _read_dom_cube_image(left_dom_cube, args)
    right_cube_image = _read_dom_cube_image(right_dom_cube, args)

    route = _route_pair(
        metadata,
        lighting_low_threshold=args.lighting_low_threshold,
        lighting_high_threshold=args.lighting_high_threshold,
    )
    method_specs = [
        ("sift_flann", "flann", "SIFT+FLANN baseline requested for DOM CUBE pair", None),
        ("loftr", "loftr", "LoFTR method requested for DOM CUBE pair", None),
        ("superpoint_lightglue", "lightglue", "SuperPoint+LightGlue method requested for DOM CUBE pair", None),
        ("adaptive", route.initial_matcher, route.route_reason, route.route_confidence),
    ]
    return [
        _match_one_method(
            pair_folder,
            metadata,
            left_cube_image,
            right_cube_image,
            method_label=method_label,
            requested_matcher=requested_matcher,
            route_reason=route_reason,
            route_confidence=route_confidence,
            output_dir=output_dir,
            args=args,
        )
        for method_label, requested_matcher, route_reason, route_confidence in method_specs
    ]


def write_summary(pair_root: Path, summaries: list[DomMethodSummary], *, output_subdir: str) -> None:
    rows = [asdict(summary) for summary in summaries]
    json_path = pair_root / f"{output_subdir}_summary.json"
    csv_path = pair_root / f"{output_subdir}_summary.csv"
    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if rows:
        with csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Match selected DOM CUBE pair folders with four RANSAC-filtered methods.")
    parser.add_argument("--pair-root", type=Path, default=DEFAULT_PAIR_ROOT)
    parser.add_argument("--dom-subdir", default="dom_reduced")
    parser.add_argument("--output-subdir", default="dom_cube_match_ransac")
    parser.add_argument("--band", type=int, default=1)
    parser.add_argument("--matching-target-long-edge", type=int, default=1800)
    parser.add_argument("--max-pairs", type=int, default=None)
    parser.add_argument("--start-index", type=int, default=1, help="1-based pair-folder start index after sorting.")
    parser.add_argument("--end-index", type=int, default=None, help="Optional 1-based inclusive pair-folder end index after sorting.")
    parser.add_argument("--max-lines", type=int, default=300)
    parser.add_argument("--max-features", type=int, default=12000)
    parser.add_argument("--ratio-test", type=float, default=0.75)
    parser.add_argument("--ransac-reproj-threshold", type=float, default=3.0)
    parser.add_argument("--invalid-value", type=float, action="append", default=[], help="Additional invalid pixel value; repeat for multiple values.")
    parser.add_argument("--special-pixel-abs-threshold", type=float, default=1.0e300)
    parser.add_argument("--invalid-pixel-radius", type=int, default=0)
    parser.add_argument("--minimum-value", type=float, default=None)
    parser.add_argument("--maximum-value", type=float, default=None)
    parser.add_argument("--lower-percent", type=float, default=0.5)
    parser.add_argument("--upper-percent", type=float, default=99.5)
    parser.add_argument("--lighting-low-threshold", type=float, default=0.02)
    parser.add_argument("--lighting-high-threshold", type=float, default=0.20)
    parser.add_argument("--lightglue-backend", choices=("auto", "kornia", "official"), default="auto")
    parser.add_argument("--official-lightglue-root", type=Path, default=DEFAULT_OFFICIAL_LIGHTGLUE_ROOT)
    parser.add_argument("--lightglue-max-keypoints", type=int, default=2048)
    parser.add_argument("--no-deep", action="store_true", help="Skip optional deep matchers in the adaptive route.")
    parser.add_argument("--no-gpu", action="store_true", help="Prefer CPU for optional deep matchers.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    pair_root = args.pair_root.expanduser().resolve()
    pair_folders = discover_pair_folders(pair_root)
    start_index = max(1, int(args.start_index))
    end_index = len(pair_folders) if args.end_index is None else max(start_index, int(args.end_index))
    pair_folders = pair_folders[start_index - 1 : end_index]
    if args.max_pairs is not None:
        pair_folders = pair_folders[: max(0, int(args.max_pairs))]
    print(f"[discover] {len(pair_folders)} selected DOM pair folder(s): {pair_root}", file=sys.stderr)
    summaries: list[DomMethodSummary] = []
    for index, pair_folder in enumerate(pair_folders, start=1):
        method_summaries = match_pair_folder_dom(pair_folder, args)
        summaries.extend(method_summaries)
        status_text = ", ".join(
            f"{summary.method_label}:{summary.effective_matcher}:{summary.ransac_match_count}/{summary.candidate_match_count_before_ransac}:{summary.status}"
            for summary in method_summaries
        )
        print(f"[match] {index:02d}/{len(pair_folders):02d} {pair_folder.name}: {status_text}", file=sys.stderr)
    write_summary(pair_root, summaries, output_subdir=args.output_subdir)
    print(json.dumps([asdict(summary) for summary in summaries], indent=2, ensure_ascii=False))
    return 0 if all(summary.status != "failed" for summary in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())