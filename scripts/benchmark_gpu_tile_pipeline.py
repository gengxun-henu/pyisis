#!/usr/bin/env python3
"""Compare CPU and GPU DOM tile matching throughput for one image pair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from examples.controlnet_construct.image_match import match_dom_pair


def _run_case(args: argparse.Namespace, *, use_gpu: bool) -> dict[str, object]:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    _, _, summary = match_dom_pair(
        args.left_dom,
        args.right_dom,
        use_gpu=use_gpu,
        gpu_batch_size=args.gpu_batch_size,
        gpu_dynamic_batch=args.gpu_dynamic_batch,
        gpu_min_batch_size=args.gpu_min_batch_size,
        gpu_max_batch_size=args.gpu_max_batch_size,
        block_width=args.tile_size,
        block_height=args.tile_size,
        overlap_x=args.overlap,
        overlap_y=args.overlap,
        max_features=args.max_features,
    )
    elapsed = time.perf_counter() - start
    return {
        "use_gpu": use_gpu,
        "elapsed_seconds": elapsed,
        "matched_tile_count": summary.get("matched_tile_count"),
        "total_match_count": summary.get("total_match_count"),
        "gpu": summary.get("gpu"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left_dom")
    parser.add_argument("right_dom")
    parser.add_argument("--output-dir", default="gpu_tile_benchmark_output")
    parser.add_argument("--tile-size", type=int, default=1024)
    parser.add_argument("--overlap", type=int, default=128)
    parser.add_argument("--max-features", type=int, default=1000)
    parser.add_argument("--gpu-batch-size", type=int, default=4)
    parser.add_argument("--gpu-dynamic-batch", action="store_true", default=True)
    parser.add_argument("--no-gpu-dynamic-batch", dest="gpu_dynamic_batch", action="store_false")
    parser.add_argument("--gpu-min-batch-size", type=int, default=2)
    parser.add_argument("--gpu-max-batch-size", type=int, default=16)
    parser.add_argument("--output-json", default=None)
    args = parser.parse_args()

    result = {
        "cpu": _run_case(args, use_gpu=False),
        "gpu": _run_case(args, use_gpu=True),
    }
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
