"""Match selected LRO NAC pair folders with adaptive texture-lighting routing.

Author: Geng Xun
Created: 2026-05-29
Updated: 2026-05-29  Geng Xun added batch matching for selected CUBE/TIFF pair
    folders with adaptive matcher routing, fallback matching, line plots, and
    CSV/JSON summaries.
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

from image_match.adaptive_routing import route_matcher_for_pair_with_sparseness


DEFAULT_PAIR_ROOT = Path(
    "/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/"
    "texture_lighting_pair_selection/selected_pair_cubes"
)
DEEP_MATCHERS = {"lightglue", "loftr", "superglue"}


@dataclass(frozen=True, slots=True)
class PairMatchSummary:
    pair_folder: str
    latitude_band: str
    selection_class: str
    left_product_id: str
    right_product_id: str
    left_image: str
    right_image: str
    requested_matcher: str
    effective_matcher: str
    fallback_used: bool
    fallback_reason: str | None
    route_reason: str
    route_confidence: float | None
    pair_texture_sparseness: float | None
    lighting_difference_score: float | None
    raw_match_count: int
    inlier_count: int
    inlier_ratio: float
    left_feature_count: int | None
    right_feature_count: int | None
    visualization_path: str
    metadata_path: str
    status: str
    error: str | None


def _finite_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(resolved):
        return None
    return resolved


def _load_metadata(pair_folder: Path) -> dict[str, Any]:
    metadata_path = pair_folder / "pair_metadata.json"
    if metadata_path.exists():
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    csv_path = pair_folder / "pair_metadata.csv"
    if csv_path.exists():
        rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
        if rows:
            return dict(rows[0])
    raise FileNotFoundError(f"No pair metadata found in {pair_folder}")


def _find_side_image(pair_folder: Path, metadata: dict[str, Any], side: str) -> Path:
    product_id = str(metadata[f"{side}_product_id"])
    tif_matches = sorted(pair_folder.glob(f"*{product_id}*.tif"))
    if tif_matches:
        return tif_matches[0]
    cube_matches = sorted(pair_folder.glob(f"*{product_id}*.cub"))
    if cube_matches:
        raise FileNotFoundError(
            f"Found CUBE but no TIFF for {product_id} in {pair_folder}. "
            "This batch matcher expects the copied TIFF previews."
        )
    raise FileNotFoundError(f"No copied TIFF/CUBE found for {product_id} in {pair_folder}")


def _normalize_to_uint8(image: np.ndarray) -> np.ndarray:
    array = np.asarray(image, dtype=np.float64)
    finite_mask = np.isfinite(array)
    if not finite_mask.any():
        return np.zeros(array.shape, dtype=np.uint8)
    valid = array[finite_mask]
    lower, upper = np.percentile(valid, [1.0, 99.0])
    if not math.isfinite(float(lower)) or not math.isfinite(float(upper)) or upper <= lower:
        lower = float(valid.min())
        upper = float(valid.max())
    if upper <= lower:
        return np.zeros(array.shape, dtype=np.uint8)
    stretched = (np.clip(array, lower, upper) - lower) * (255.0 / (upper - lower))
    return np.where(finite_mask, stretched, 0.0).astype(np.uint8)


def _read_grayscale(path: Path, *, target_long_edge: int | None) -> tuple[np.ndarray, float]:
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    if image.ndim == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image_u8 = _normalize_to_uint8(image)
    scale = 1.0
    if target_long_edge is not None:
        long_edge = max(image_u8.shape[:2])
        if long_edge > int(target_long_edge):
            scale = float(target_long_edge) / float(long_edge)
            new_width = max(1, int(round(image_u8.shape[1] * scale)))
            new_height = max(1, int(round(image_u8.shape[0] * scale)))
            image_u8 = cv2.resize(image_u8, (new_width, new_height), interpolation=cv2.INTER_AREA)
    return image_u8, scale


def _build_sift(max_features: int | None) -> cv2.SIFT:
    kwargs: dict[str, int] = {}
    if max_features is not None and int(max_features) > 0:
        kwargs["nfeatures"] = int(max_features)
    return cv2.SIFT_create(**kwargs)


def _match_with_sift(
    left_image: np.ndarray,
    right_image: np.ndarray,
    *,
    matcher_method: str,
    ratio_test: float,
    max_features: int | None,
    left_mask: np.ndarray | None = None,
    right_mask: np.ndarray | None = None,
) -> tuple[list[cv2.KeyPoint], list[cv2.KeyPoint], list[cv2.DMatch], int, int]:
    sift = _build_sift(max_features)
    left_keypoints, left_descriptors = sift.detectAndCompute(left_image, left_mask)
    right_keypoints, right_descriptors = sift.detectAndCompute(right_image, right_mask)
    left_keypoints = [] if left_keypoints is None else list(left_keypoints)
    right_keypoints = [] if right_keypoints is None else list(right_keypoints)
    if left_descriptors is None or right_descriptors is None or not left_keypoints or not right_keypoints:
        return left_keypoints, right_keypoints, [], len(left_keypoints), len(right_keypoints)

    if matcher_method == "flann":
        matcher = cv2.FlannBasedMatcher({"algorithm": 1, "trees": 5}, {"checks": 50})
    else:
        matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    knn_matches = matcher.knnMatch(left_descriptors, right_descriptors, k=2)
    good_matches: list[cv2.DMatch] = []
    for candidates in knn_matches:
        if len(candidates) < 2:
            continue
        best, second = candidates[:2]
        if best.distance < float(ratio_test) * second.distance:
            good_matches.append(best)
    return left_keypoints, right_keypoints, good_matches, len(left_keypoints), len(right_keypoints)


def _match_with_deep(
    left_image: np.ndarray,
    right_image: np.ndarray,
    *,
    matcher_method: str,
    prefer_gpu: bool,
    left_mask: np.ndarray | None = None,
    right_mask: np.ndarray | None = None,
    runtime_config: Any | None = None,
) -> tuple[list[cv2.KeyPoint], list[cv2.KeyPoint], list[cv2.DMatch], None, None]:
    from image_match.deep_adapter import DeepMatcherAdapter

    result = DeepMatcherAdapter(prefer_gpu=prefer_gpu, runtime_config=runtime_config).match_pair_with_fallback(
        matcher_method=matcher_method,
        left_image=left_image,
        right_image=right_image,
        left_mask=left_mask,
        right_mask=right_mask,
        prefer_gpu=prefer_gpu,
    )
    return list(result.left_keypoints), list(result.right_keypoints), list(result.matches), None, None


def _filter_ransac_matches(
    left_keypoints: list[cv2.KeyPoint],
    right_keypoints: list[cv2.KeyPoint],
    matches: list[cv2.DMatch],
    *,
    ransac_reproj_threshold: float,
) -> tuple[list[cv2.DMatch], int, float]:
    if len(matches) < 8:
        return matches, len(matches), 1.0 if matches else 0.0
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
        return matches, len(matches), 1.0 if matches else 0.0
    keep = mask.reshape(-1).astype(bool)
    inlier_matches = [match for match, accepted in zip(matches, keep, strict=False) if accepted]
    inlier_count = len(inlier_matches)
    inlier_ratio = 0.0 if not matches else inlier_count / len(matches)
    return inlier_matches, inlier_count, inlier_ratio


def _sanitize_matches(
    left_keypoints: list[cv2.KeyPoint],
    right_keypoints: list[cv2.KeyPoint],
    matches: list[cv2.DMatch],
) -> list[cv2.DMatch]:
    left_count = len(left_keypoints)
    right_count = len(right_keypoints)
    return [
        match
        for match in matches
        if 0 <= int(match.queryIdx) < left_count and 0 <= int(match.trainIdx) < right_count
    ]


def _write_visualization(
    output_path: Path,
    left_image: np.ndarray,
    right_image: np.ndarray,
    left_keypoints: list[cv2.KeyPoint],
    right_keypoints: list[cv2.KeyPoint],
    matches: list[cv2.DMatch],
    *,
    max_lines: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ranked_matches = sorted(matches, key=lambda match: match.distance)[: int(max_lines)]
    rendered = cv2.drawMatches(
        left_image,
        left_keypoints,
        right_image,
        right_keypoints,
        ranked_matches,
        None,
        flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
    )
    cv2.imwrite(str(output_path), rendered)


def _route_pair(metadata: dict[str, Any], *, lighting_low_threshold: float, lighting_high_threshold: float):
    return route_matcher_for_pair_with_sparseness(
        pair_texture_sparseness=_finite_float(metadata.get("pair_texture_sparseness")),
        lighting_difference_score=_finite_float(metadata.get("lighting_difference_score")),
        lighting_low_threshold=lighting_low_threshold,
        lighting_high_threshold=lighting_high_threshold,
    )


def match_pair_folder(pair_folder: Path, args: argparse.Namespace) -> PairMatchSummary:
    metadata_path = pair_folder / "adaptive_match_metadata.json"
    visualization_path = pair_folder / "adaptive_match_lines.png"
    try:
        metadata = _load_metadata(pair_folder)
        left_image_path = _find_side_image(pair_folder, metadata, "left")
        right_image_path = _find_side_image(pair_folder, metadata, "right")
        route = _route_pair(
            metadata,
            lighting_low_threshold=args.lighting_low_threshold,
            lighting_high_threshold=args.lighting_high_threshold,
        )
        requested_matcher = route.initial_matcher
        left_image, _ = _read_grayscale(left_image_path, target_long_edge=args.matching_target_long_edge)
        right_image, _ = _read_grayscale(right_image_path, target_long_edge=args.matching_target_long_edge)

        fallback_used = False
        fallback_reason = None
        effective_matcher = requested_matcher
        left_feature_count: int | None
        right_feature_count: int | None
        try:
            if requested_matcher in DEEP_MATCHERS and not args.no_deep:
                left_keypoints, right_keypoints, raw_matches, left_feature_count, right_feature_count = _match_with_deep(
                    left_image,
                    right_image,
                    matcher_method=requested_matcher,
                    prefer_gpu=not args.no_gpu,
                )
            else:
                left_keypoints, right_keypoints, raw_matches, left_feature_count, right_feature_count = _match_with_sift(
                    left_image,
                    right_image,
                    matcher_method=requested_matcher if requested_matcher in {"bf", "flann"} else "bf",
                    ratio_test=args.ratio_test,
                    max_features=args.max_features,
                )
                if requested_matcher in DEEP_MATCHERS:
                    effective_matcher = "bf"
                    fallback_used = True
                    fallback_reason = "deep matching disabled by --no-deep"
        except Exception as exc:  # noqa: BLE001 - fallback preserves a usable diagnostic image
            fallback_used = True
            fallback_reason = f"{type(exc).__name__}: {exc}"
            effective_matcher = "bf"
            left_keypoints, right_keypoints, raw_matches, left_feature_count, right_feature_count = _match_with_sift(
                left_image,
                right_image,
                matcher_method="bf",
                ratio_test=args.ratio_test,
                max_features=args.max_features,
            )

        try:
            raw_matches = _sanitize_matches(left_keypoints, right_keypoints, raw_matches)
            inlier_matches, inlier_count, inlier_ratio = _filter_ransac_matches(
                left_keypoints,
                right_keypoints,
                raw_matches,
                ransac_reproj_threshold=args.ransac_reproj_threshold,
            )
            draw_matches = inlier_matches if inlier_matches else raw_matches
            _write_visualization(
                visualization_path,
                left_image,
                right_image,
                left_keypoints,
                right_keypoints,
                draw_matches,
                max_lines=args.max_lines,
            )
        except Exception as exc:  # noqa: BLE001 - fallback keeps the batch complete
            if effective_matcher == "bf":
                raise
            fallback_used = True
            fallback_reason = f"postprocess {type(exc).__name__}: {exc}"
            effective_matcher = "bf"
            left_keypoints, right_keypoints, raw_matches, left_feature_count, right_feature_count = _match_with_sift(
                left_image,
                right_image,
                matcher_method="bf",
                ratio_test=args.ratio_test,
                max_features=args.max_features,
            )
            raw_matches = _sanitize_matches(left_keypoints, right_keypoints, raw_matches)
            inlier_matches, inlier_count, inlier_ratio = _filter_ransac_matches(
                left_keypoints,
                right_keypoints,
                raw_matches,
                ransac_reproj_threshold=args.ransac_reproj_threshold,
            )
            draw_matches = inlier_matches if inlier_matches else raw_matches
            _write_visualization(
                visualization_path,
                left_image,
                right_image,
                left_keypoints,
                right_keypoints,
                draw_matches,
                max_lines=args.max_lines,
            )
        summary = PairMatchSummary(
            pair_folder=str(pair_folder),
            latitude_band=str(metadata.get("latitude_band", "")),
            selection_class=str(metadata.get("selection_class", "")),
            left_product_id=str(metadata.get("left_product_id", "")),
            right_product_id=str(metadata.get("right_product_id", "")),
            left_image=str(left_image_path),
            right_image=str(right_image_path),
            requested_matcher=requested_matcher,
            effective_matcher=effective_matcher,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            route_reason=route.route_reason,
            route_confidence=route.route_confidence,
            pair_texture_sparseness=_finite_float(metadata.get("pair_texture_sparseness")),
            lighting_difference_score=_finite_float(metadata.get("lighting_difference_score")),
            raw_match_count=len(raw_matches),
            inlier_count=inlier_count,
            inlier_ratio=inlier_ratio,
            left_feature_count=left_feature_count,
            right_feature_count=right_feature_count,
            visualization_path=str(visualization_path),
            metadata_path=str(metadata_path),
            status="matched" if raw_matches else "matched_no_points",
            error=None,
        )
    except Exception as exc:  # noqa: BLE001 - continue other folders in batch mode
        summary = PairMatchSummary(
            pair_folder=str(pair_folder),
            latitude_band="",
            selection_class="",
            left_product_id="",
            right_product_id="",
            left_image="",
            right_image="",
            requested_matcher="",
            effective_matcher="",
            fallback_used=False,
            fallback_reason=None,
            route_reason="",
            route_confidence=None,
            pair_texture_sparseness=None,
            lighting_difference_score=None,
            raw_match_count=0,
            inlier_count=0,
            inlier_ratio=0.0,
            left_feature_count=None,
            right_feature_count=None,
            visualization_path=str(visualization_path),
            metadata_path=str(metadata_path),
            status="failed",
            error=f"{type(exc).__name__}: {exc}",
        )
    metadata_path.write_text(json.dumps(asdict(summary), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def discover_pair_folders(pair_root: Path) -> list[Path]:
    return sorted(path for path in pair_root.iterdir() if path.is_dir() and (path / "pair_metadata.json").exists())


def write_summary(pair_root: Path, summaries: list[PairMatchSummary]) -> None:
    json_path = pair_root / "adaptive_match_summary.json"
    csv_path = pair_root / "adaptive_match_summary.csv"
    rows = [asdict(summary) for summary in summaries]
    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if rows:
        with csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Match copied LRO selected pair folders and write adaptive line plots.")
    parser.add_argument("--pair-root", type=Path, default=DEFAULT_PAIR_ROOT)
    parser.add_argument("--matching-target-long-edge", type=int, default=1600)
    parser.add_argument("--max-pairs", type=int, default=None, help="Optional limit for smoke-test runs.")
    parser.add_argument("--max-lines", type=int, default=200)
    parser.add_argument("--max-features", type=int, default=8000)
    parser.add_argument("--ratio-test", type=float, default=0.75)
    parser.add_argument("--ransac-reproj-threshold", type=float, default=3.0)
    parser.add_argument("--lighting-low-threshold", type=float, default=0.02)
    parser.add_argument("--lighting-high-threshold", type=float, default=0.20)
    parser.add_argument("--no-deep", action="store_true", help="Skip LightGlue/LoFTR attempts and use SIFT fallback.")
    parser.add_argument("--no-gpu", action="store_true", help="Prefer CPU for optional deep matchers.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    pair_root = args.pair_root.expanduser().resolve()
    pair_folders = discover_pair_folders(pair_root)
    if args.max_pairs is not None:
        pair_folders = pair_folders[: max(0, int(args.max_pairs))]
    print(f"[discover] {len(pair_folders)} selected pair folder(s): {pair_root}", file=sys.stderr)
    summaries: list[PairMatchSummary] = []
    for index, pair_folder in enumerate(pair_folders, start=1):
        summary = match_pair_folder(pair_folder, args)
        summaries.append(summary)
        print(
            f"[match] {index:02d}/{len(pair_folders):02d} {pair_folder.name}: "
            f"status={summary.status} requested={summary.requested_matcher} "
            f"effective={summary.effective_matcher} raw={summary.raw_match_count} "
            f"inliers={summary.inlier_count}",
            file=sys.stderr,
        )
    write_summary(pair_root, summaries)
    print(json.dumps([asdict(summary) for summary in summaries], indent=2, ensure_ascii=False))
    return 0 if all(summary.status != "failed" for summary in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())