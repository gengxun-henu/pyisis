"""Batch sweep of LoFTR parameters with optional geometric filtering.

Runs LoFTR over a grid of coarse-threshold, confidence-filter, and geometric
filter combinations. Reports raw/final match counts and timing to both the
terminal and a CSV file.

Author: Geng Xun
Created: 2026-05-12
Updated: 2026-05-12  Geng Xun added a LoFTR parameter sweep utility aligned with the LightGlue sweep style and reusing the standalone LoFTR example helpers.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import itertools
import time
from pathlib import Path

import torch


_script_dir = Path(__file__).parent
_simple_loftr_path = _script_dir / "simple-loftr.py"
_simple_loftr_spec = importlib.util.spec_from_file_location("simple_loftr", _simple_loftr_path)
simple_loftr = importlib.util.module_from_spec(_simple_loftr_spec)
assert _simple_loftr_spec.loader is not None
_simple_loftr_spec.loader.exec_module(simple_loftr)

apply_geometric_filter = simple_loftr.apply_geometric_filter
build_output_path = simple_loftr.build_output_path
describe_geometric_filter_stats = simple_loftr.describe_geometric_filter_stats
find_loftr_root = simple_loftr.find_loftr_root
filter_matches = simple_loftr.filter_matches
get_default_sample_images = simple_loftr.get_default_sample_images
load_loftr_matcher = simple_loftr.load_loftr_matcher
read_image_pair = simple_loftr.read_image_pair
resolve_checkpoint = simple_loftr.resolve_checkpoint
resolve_device = simple_loftr.resolve_device
resolve_temp_bug_fix = simple_loftr.resolve_temp_bug_fix
run_loftr_matching = simple_loftr.run_loftr_matching
scale_points_to_original = simple_loftr.scale_points_to_original
validate_ransac_args = simple_loftr.validate_ransac_args
validate_resize_args = simple_loftr.validate_resize_args


DEFAULT_COARSE_THRESHOLDS = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3]
DEFAULT_MIN_CONFIDENCES = [-1.0, 0.05, 0.1, 0.15, 0.2]
DEFAULT_GEOMETRIC_FILTERS = ["none", "fundamental", "homography"]
CSV_COLUMNS = [
    "coarse_threshold",
    "min_confidence",
    "geometric_filter",
    "raw_matches",
    "post_confidence_matches",
    "final_matches",
    "final_ratio_pct",
    "inference_time_ms",
    "post_filter_time_ms",
    "total_time_ms",
    "geometric_status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep LoFTR coarse-threshold and post-filter settings across a parameter grid."
    )
    parser.add_argument(
        "--left-image",
        default=None,
        help="Path to the left input image. Defaults to a model-specific LoFTR sample image.",
    )
    parser.add_argument(
        "--right-image",
        default=None,
        help="Path to the right input image. Defaults to a model-specific LoFTR sample image.",
    )
    parser.add_argument(
        "--loftr-root",
        default=None,
        help="Optional path to the LoFTR repository root. Auto-discovered when omitted.",
    )
    parser.add_argument(
        "--checkpoint",
        default=None,
        help="Optional path to a custom LoFTR checkpoint.",
    )
    parser.add_argument(
        "--model-type",
        choices=simple_loftr.SUPPORTED_MODEL_TYPES,
        default="outdoor",
        help="Preset checkpoint family to use when --checkpoint is omitted.",
    )
    parser.add_argument(
        "--temp-bug-fix",
        choices=("auto", "true", "false"),
        default="auto",
        help="LoFTR positional-encoding compatibility flag. Default: auto.",
    )
    parser.add_argument(
        "--device",
        choices=simple_loftr.SUPPORTED_DEVICES,
        default="auto",
        help="Execution device. Default: auto (prefer CUDA).",
    )
    parser.add_argument(
        "--resize-width",
        type=int,
        default=None,
        help="Optional inference width. Must be used together with --resize-height.",
    )
    parser.add_argument(
        "--resize-height",
        type=int,
        default=None,
        help="Optional inference height. Must be used together with --resize-width.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Optional post-confidence Top-K cap applied before geometric filtering.",
    )
    parser.add_argument(
        "--coarse-thresholds",
        type=float,
        nargs="+",
        default=DEFAULT_COARSE_THRESHOLDS,
        help="LoFTR coarse-threshold values to sweep.",
    )
    parser.add_argument(
        "--min-confidences",
        type=float,
        nargs="+",
        default=DEFAULT_MIN_CONFIDENCES,
        help=(
            "Confidence thresholds to sweep after LoFTR matching. Negative values disable "
            "confidence filtering for that row."
        ),
    )
    parser.add_argument(
        "--geometric-filters",
        nargs="+",
        choices=simple_loftr.SUPPORTED_GEOMETRIC_FILTERS,
        default=DEFAULT_GEOMETRIC_FILTERS,
        help="Geometric filters to sweep after confidence filtering.",
    )
    parser.add_argument(
        "--ransac-reproj-threshold",
        type=float,
        default=3.0,
        help="RANSAC reprojection threshold in pixels.",
    )
    parser.add_argument(
        "--ransac-confidence",
        type=float,
        default=0.999,
        help="RANSAC confidence target. Default: 0.999.",
    )
    parser.add_argument(
        "--ransac-max-iters",
        type=int,
        default=10000,
        help="Maximum RANSAC iterations. Default: 10000.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path. Defaults to a timestamped file in examples/experiment_methods/sweep_results/.",
    )
    return parser.parse_args()


def resolve_input_images(args: argparse.Namespace, loftr_root: Path) -> tuple[str, str]:
    if args.left_image and args.right_image:
        return args.left_image, args.right_image
    if args.left_image or args.right_image:
        raise ValueError("--left-image and --right-image must be provided together.")
    left_path, right_path = get_default_sample_images(loftr_root, args.model_type)
    return str(left_path), str(right_path)


def resolve_min_confidence(value: float) -> float | None:
    return None if value < 0 else float(value)


def build_output_csv_path(output: str | None) -> str:
    if output is not None:
        return output
    parent = Path(__file__).parent / "sweep_results"
    parent.mkdir(parents=True, exist_ok=True)
    return str(parent / f"loftr_sweep_{time.strftime('%Y%m%d_%H%M%S')}.csv")


def print_header(
    device: torch.device,
    model_type: str,
    checkpoint_path: Path,
    left_image: str,
    right_image: str,
    coarse_thresholds: list[float],
    min_confidences: list[float],
    geometric_filters: list[str],
    total: int,
) -> None:
    print("=" * 100)
    print("LoFTR Parameter Sweep")
    print(f"  Device: {device}")
    print(f"  Model type: {model_type}")
    print(f"  Checkpoint: {checkpoint_path}")
    print(f"  Left image: {left_image}")
    print(f"  Right image: {right_image}")
    print(f"  coarse_thresholds: {coarse_thresholds}")
    print(f"  min_confidences: {min_confidences}")
    print(f"  geometric_filters: {geometric_filters}")
    print(f"  Total combinations: {total}")
    print("=" * 100)


def print_progress(
    done: int,
    total: int,
    coarse_threshold: float,
    min_confidence: float,
    geometric_filter: str,
    raw_matches: int,
    final_matches: int,
    total_time_ms: float,
) -> None:
    pct = done / total * 100
    print(
        f"  [{done:4d}/{total}] {pct:5.1f}% | "
        f"thr={coarse_threshold:.3f}  min_conf={min_confidence:+.3f}  geom={geometric_filter:<11s} | "
        f"raw={raw_matches:5d}  kept={final_matches:5d}  time={total_time_ms:7.1f}ms"
    )


def print_summary_table(rows: list[dict]) -> None:
    print("\n" + "=" * 100)
    print("Summary Table (grouped by coarse_threshold)")
    print("-" * 100)
    print(
        f"{'thr':>7s} | {'min_conf':>8s} | {'geom':>11s} | {'raw':>6s} | {'final':>6s} | {'ratio':>7s} | {'time_ms':>8s}"
    )
    print("-" * 100)
    for row in rows:
        print(
            f"{row['coarse_threshold']:7.3f} | "
            f"{row['min_confidence']:8.3f} | "
            f"{row['geometric_filter']:>11s} | "
            f"{row['raw_matches']:6d} | "
            f"{row['final_matches']:6d} | "
            f"{row['final_ratio_pct']:6.1f}% | "
            f"{row['total_time_ms']:8.1f}"
        )
    print("=" * 100)
    if rows:
        best = max(rows, key=lambda row: row["final_matches"])
        worst = min(rows, key=lambda row: row["final_matches"])
        print(
            f"Most final matches:  {best['final_matches']}  "
            f"(thr={best['coarse_threshold']:.3f}, min_conf={best['min_confidence']:.3f}, geom={best['geometric_filter']})"
        )
        print(
            f"Fewest final matches: {worst['final_matches']}  "
            f"(thr={worst['coarse_threshold']:.3f}, min_conf={worst['min_confidence']:.3f}, geom={worst['geometric_filter']})"
        )
        print("=" * 100)


def main() -> None:
    args = parse_args()
    validate_resize_args(args.resize_width, args.resize_height)
    validate_ransac_args(
        "fundamental" if any(gf != "none" for gf in args.geometric_filters) else "none",
        args.ransac_reproj_threshold,
        args.ransac_confidence,
        args.ransac_max_iters,
    )

    device = resolve_device(args.device)
    loftr_root = find_loftr_root(args.loftr_root)
    checkpoint_path = resolve_checkpoint(args.checkpoint, loftr_root, args.model_type)
    temp_bug_fix = resolve_temp_bug_fix(args.temp_bug_fix, args.model_type)
    left_image, right_image = resolve_input_images(args, loftr_root)
    output_csv = build_output_csv_path(args.output)

    left = read_image_pair(left_image, args.resize_width, args.resize_height)
    right = read_image_pair(right_image, args.resize_width, args.resize_height)

    total = (
        len(args.coarse_thresholds)
        * len(args.min_confidences)
        * len(args.geometric_filters)
    )
    print_header(
        device,
        args.model_type,
        checkpoint_path,
        left_image,
        right_image,
        list(args.coarse_thresholds),
        list(args.min_confidences),
        list(args.geometric_filters),
        total,
    )

    rows: list[dict] = []
    done = 0

    for coarse_threshold in args.coarse_thresholds:
        matcher = load_loftr_matcher(
            loftr_root,
            checkpoint_path,
            temp_bug_fix,
            device,
            coarse_threshold=coarse_threshold,
        )

        infer_t0 = time.perf_counter()
        mkpts0_raw, mkpts1_raw, mconf_raw = run_loftr_matching(matcher, left, right, device)
        inference_time_ms = (time.perf_counter() - infer_t0) * 1000.0
        raw_match_count = int(len(mconf_raw))
        del matcher

        for min_confidence_value, geometric_filter in itertools.product(
            args.min_confidences,
            args.geometric_filters,
        ):
            post_t0 = time.perf_counter()
            min_confidence = resolve_min_confidence(min_confidence_value)
            mkpts0_filtered, mkpts1_filtered, mconf_filtered = filter_matches(
                mkpts0_raw,
                mkpts1_raw,
                mconf_raw,
                min_confidence=min_confidence,
                top_k=args.top_k,
            )
            post_confidence_matches = int(len(mconf_filtered))

            scaled_points0 = scale_points_to_original(mkpts0_filtered, left["scale"])
            scaled_points1 = scale_points_to_original(mkpts1_filtered, right["scale"])
            final_points0, final_points1, final_confidences, geometric_stats = apply_geometric_filter(
                scaled_points0,
                scaled_points1,
                mconf_filtered,
                method=geometric_filter,
                reproj_threshold=args.ransac_reproj_threshold,
                confidence=args.ransac_confidence,
                max_iters=args.ransac_max_iters,
            )
            post_filter_time_ms = (time.perf_counter() - post_t0) * 1000.0
            final_matches = int(len(final_confidences))
            total_time_ms = inference_time_ms + post_filter_time_ms
            final_ratio = final_matches / raw_match_count * 100 if raw_match_count > 0 else 0.0

            done += 1
            print_progress(
                done,
                total,
                coarse_threshold,
                min_confidence_value,
                geometric_filter,
                raw_match_count,
                final_matches,
                total_time_ms,
            )

            rows.append(
                {
                    "coarse_threshold": round(float(coarse_threshold), 6),
                    "min_confidence": round(float(min_confidence_value), 6),
                    "geometric_filter": geometric_filter,
                    "raw_matches": raw_match_count,
                    "post_confidence_matches": post_confidence_matches,
                    "final_matches": final_matches,
                    "final_ratio_pct": round(final_ratio, 2),
                    "inference_time_ms": round(inference_time_ms, 1),
                    "post_filter_time_ms": round(post_filter_time_ms, 1),
                    "total_time_ms": round(total_time_ms, 1),
                    "geometric_status": str(geometric_stats.get("status", "unknown")),
                }
            )

    rows.sort(
        key=lambda row: (
            row["coarse_threshold"],
            row["min_confidence"],
            row["geometric_filter"],
        )
    )

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nCSV saved to: {output_csv}")
    print_summary_table(rows)

    if rows:
        sample_best = max(rows, key=lambda row: row["final_matches"])
        sample_desc = describe_geometric_filter_stats(
            {
                "method": sample_best["geometric_filter"],
                "status": sample_best["geometric_status"],
                "input_count": sample_best["post_confidence_matches"],
                "output_count": sample_best["final_matches"],
                "outlier_count": sample_best["post_confidence_matches"] - sample_best["final_matches"],
            }
        )
        print(f"Best-row geometric summary: {sample_desc}")


if __name__ == "__main__":
    main()
