"""Batch sweep of LightGlue parameters: filter_threshold, width_confidence, depth_confidence.

Extracts features once, then runs the LightGlue matcher across a grid of
parameter combinations. Reports matched point counts and timing to both
a terminal table and a CSV file.

Author: Geng Xun
Created: 2026-05-12
"""

import argparse
import csv
import itertools
import sys
import time
from pathlib import Path

import torch

# Ensure the parent directory is importable so we can reuse functions from simple-lightglue.py
sys.path.insert(0, str(Path(__file__).parent))
import importlib.util

_lg_path = Path(__file__).parent / "simple-lightglue.py"
_lg_spec = importlib.util.spec_from_file_location("simple_lightglue", _lg_path)
simple_lightglue = importlib.util.module_from_spec(_lg_spec)
_lg_spec.loader.exec_module(simple_lightglue)

build_extractor = simple_lightglue.build_extractor
resolve_device = simple_lightglue.resolve_device

TESTDIR = "/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test"
DEFAULT_LEFT_IMAGE = TESTDIR + "/REDUCED_scale4_M104311715RE.echo.cal.tif"
DEFAULT_RIGHT_IMAGE = TESTDIR + "/REDUCED_scale4_M104318871RE.echo.cal.tif"

FILTER_THRESHOLDS = [0.01, 0.02, 0.05, 0.08, 0.1, 0.15, 0.2, 0.3, 0.4]
WIDTH_CONFIDENCES = [-1, 0.5, 0.8, 0.9, 0.95, 0.99]
DEPTH_CONFIDENCES = [-1, 0.5, 0.8, 0.9, 0.95, 0.99]
MAX_FEATURES = 2048
#FEATURE_METHOD = "superpoint"
FEATURE_METHOD = "doghardnet"

CSV_COLUMNS = [
    "filter_threshold",
    "width_confidence",
    "depth_confidence",
    "matched_points",
    "possible_pairs",
    "left_keypoints",
    "right_keypoints",
    "match_ratio_pct",
    "match_time_ms",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep LightGlue parameters and report matched point counts."
    )
    parser.add_argument(
        "--left-image",
        default=DEFAULT_LEFT_IMAGE,
        help="Path to the left input image.",
    )
    parser.add_argument(
        "--right-image",
        default=DEFAULT_RIGHT_IMAGE,
        help="Path to the right input image.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path. Defaults to a timestamped file in the script directory.",
    )
    parser.add_argument(
        "--device",
        choices=("auto", "cpu", "cuda"),
        default="auto",
        help="Execution device. Default: auto (prefer CUDA).",
    )
    return parser.parse_args()


def build_output_csv_path(output: str | None) -> str:
    if output is not None:
        return output
    parent = Path(__file__).parent / "sweep_results"
    parent.mkdir(parents=True, exist_ok=True)
    return str(parent / f"sweep_{time.strftime('%Y%m%d_%H%M%S')}.csv")


def print_header(device: torch.device, total: int) -> None:
    print("=" * 85)
    print("LightGlue Parameter Sweep")
    print(f"  Device: {device}")
    print(f"  Feature method: {FEATURE_METHOD}")
    print(f"  Max features: {MAX_FEATURES}")
    print(f"  filter_threshold: {FILTER_THRESHOLDS}")
    print(f"  width_confidence: {WIDTH_CONFIDENCES}")
    print(f"  depth_confidence: {DEPTH_CONFIDENCES}")
    print(f"  Total combinations: {total}")
    print("=" * 85)


def print_progress(done: int, total: int, ft: float, wc: int, dc: int, count: int, elapsed_ms: float) -> None:
    pct = done / total * 100
    print(
        f"  [{done:4d}/{total}] {pct:5.1f}% | "
        f"ft={ft:.3f}  wc={wc:+.2f}  dc={dc:+.2f} | "
        f"matches={count:5d}  time={elapsed_ms:6.1f}ms"
    )


def print_summary_table(rows: list[dict], possible_pairs: int, left_kp: int, right_kp: int) -> None:
    """Print a summary table grouped by filter_threshold."""
    print("\n" + "=" * 85)
    print("Summary Table (grouped by filter_threshold)")
    print(f"  Left keypoints detected:  {left_kp}")
    print(f"  Right keypoints detected: {right_kp}")
    print(f"  Possible pairs (min):     {possible_pairs}")
    print("-" * 85)
    print(f"{'filter_t':>10s} | {'width_c':>7s} | {'depth_c':>7s} | {'matches':>8s} | {'ratio':>6s} | {'time_ms':>8s}")
    print("-" * 95)
    for r in rows:
        ratio = r["matched_points"] / possible_pairs * 100 if possible_pairs > 0 else 0
        print(
            f"{r['filter_threshold']:10.3f} | "
            f"{r['width_confidence']:7.2f} | "
            f"{r['depth_confidence']:7.2f} | "
            f"{r['matched_points']:8d} | "
            f"{ratio:5.1f}% | "
            f"{r['match_time_ms']:8.1f}"
        )
    print("=" * 85)

    # Best/worst
    if rows:
        best = max(rows, key=lambda r: r["matched_points"])
        worst = min(rows, key=lambda r: r["matched_points"])
        print(
            f"Most matches:  {best['matched_points']:d}  "
            f"(ft={best['filter_threshold']:.3f}, wc={best['width_confidence']}, dc={best['depth_confidence']})"
        )
        print(
            f"Fewest matches: {worst['matched_points']:d}  "
            f"(ft={worst['filter_threshold']:.3f}, wc={worst['width_confidence']}, dc={worst['depth_confidence']})"
        )
        print("=" * 85)


def main() -> None:
    args = parse_args()
    from lightglue import LightGlue
    from lightglue.utils import load_image, rbd

    device = resolve_device(args.device)
    output_csv = build_output_csv_path(args.output)

    # Extract features once (they don't change across parameter combinations)
    print("Extracting features (once)...")
    extractor = build_extractor(FEATURE_METHOD, device, MAX_FEATURES)
    image0 = load_image(args.left_image).to(device)
    image1 = load_image(args.right_image).to(device)
    feats0_raw = extractor.extract(image0)
    feats1_raw = extractor.extract(image1)
    left_kp_count = int(feats0_raw["keypoints"].shape[-2])
    right_kp_count = int(feats1_raw["keypoints"].shape[-2])
    possible_pairs = min(left_kp_count, right_kp_count)
    print(f"  Left keypoints:  {left_kp_count}")
    print(f"  Right keypoints: {right_kp_count}")
    print(f"  Possible pairs:  {possible_pairs}")

    total = len(FILTER_THRESHOLDS) * len(WIDTH_CONFIDENCES) * len(DEPTH_CONFIDENCES)
    print_header(device, total)

    rows = []
    done = 0

    for ft, wc, dc in itertools.product(FILTER_THRESHOLDS, WIDTH_CONFIDENCES, DEPTH_CONFIDENCES):
        matcher = LightGlue(
            features=FEATURE_METHOD,
            filter_threshold=ft,
            width_confidence=wc,
            depth_confidence=dc,
            flash=True,
            mp=True,
        ).eval().to(device)

        t0 = time.perf_counter()
        with torch.no_grad():
            matches01 = matcher({"image0": feats0_raw, "image1": feats1_raw})
        elapsed_ms = (time.perf_counter() - t0) * 1000

        _, _, matches_dict = [rbd(x) for x in [feats0_raw, feats1_raw, matches01]]
        match_count = int(matches_dict["matches"].shape[0])

        done += 1
        print_progress(done, total, ft, wc, dc, match_count, elapsed_ms)

        match_ratio = match_count / possible_pairs * 100 if possible_pairs > 0 else 0
        rows.append({
            "filter_threshold": ft,
            "width_confidence": wc,
            "depth_confidence": dc,
            "matched_points": match_count,
            "possible_pairs": possible_pairs,
            "left_keypoints": left_kp_count,
            "right_keypoints": right_kp_count,
            "match_ratio_pct": round(match_ratio, 2),
            "match_time_ms": round(elapsed_ms, 1),
        })

    # Sort by filter_threshold, then width_confidence, then depth_confidence
    rows.sort(key=lambda r: (r["filter_threshold"], r["width_confidence"], r["depth_confidence"]))

    # Write CSV
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nCSV saved to: {output_csv}")

    # Print summary
    print_summary_table(rows, possible_pairs, left_kp_count, right_kp_count)


if __name__ == "__main__":
    main()
