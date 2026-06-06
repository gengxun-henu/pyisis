#!/usr/bin/env python3
"""Rerender existing deep-match visualizations after RANSAC filtering.

This utility reuses preserved DOM `.key` outputs and pair metadata. It does not
rerun the deep matcher and does not overwrite the original `match_viz` images.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from image_match.keypoints import read_key_file  # noqa: E402
from image_match.match_visualization import write_stereo_pair_match_visualization  # noqa: E402
from image_match.stereo_ransac import filter_stereo_pair_keypoints_with_ransac  # noqa: E402


DEFAULT_METHODS = ("loftr", "superpoint_lightglue", "sift_lightglue")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pair_tag_from_left_key(left_key: Path) -> str:
    suffix = "_A.key"
    name = left_key.name
    if not name.endswith(suffix):
        raise ValueError(f"Unexpected left key filename: {left_key}")
    return name[: -len(suffix)]


def _safe_float(value: Any, default: float) -> float:
    if value is None:
        return default
    return float(value)


def _safe_int(value: Any, default: int | None) -> int | None:
    if value is None:
        return default
    return int(value)


def _old_visualization_payload(metadata: dict[str, Any]) -> dict[str, Any]:
    payload = metadata.get("match_visualization")
    if isinstance(payload, dict):
        return payload
    image_match = metadata.get("image_match")
    if isinstance(image_match, dict):
        payload = image_match.get("match_visualization")
        if isinstance(payload, dict):
            return payload
    return {}


def _metadata_path_value(metadata: dict[str, Any], section: str) -> str | None:
    payload = metadata.get(section)
    if isinstance(payload, dict):
        value = payload.get("path")
        if isinstance(value, str) and value:
            return value
    image_match = metadata.get("image_match")
    if isinstance(image_match, dict):
        preparation = image_match.get("preparation")
        if isinstance(preparation, dict):
            payload = preparation.get(section)
            if isinstance(payload, dict):
                value = payload.get("path")
                if isinstance(value, str) and value:
                    return value
    return None


def _manifest_dom_path_value(metadata: dict[str, Any], section: str) -> str | None:
    image_match = metadata.get("image_match")
    if not isinstance(image_match, dict):
        return None
    deep_import = image_match.get("deep_match_import")
    if not isinstance(deep_import, dict):
        return None
    manifest_path = deep_import.get("manifest_path")
    if not isinstance(manifest_path, str) or not manifest_path:
        return None
    manifest = Path(manifest_path)
    if not manifest.exists():
        return None
    try:
        payload = _load_json(manifest)
    except (OSError, json.JSONDecodeError):
        return None
    tasks = payload.get("tasks") if isinstance(payload, dict) else payload
    if not isinstance(tasks, list):
        return None
    key = f"{section}_dom_path"
    for task in tasks:
        if not isinstance(task, dict):
            continue
        tile_task = task.get("tile_task")
        if not isinstance(tile_task, dict):
            continue
        value = tile_task.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _resolve_output_path(
    *,
    pair_tag: str,
    old_visualization: dict[str, Any],
    output_dir: Path,
) -> Path:
    old_output = old_visualization.get("output_path")
    if isinstance(old_output, str) and old_output:
        old_name = Path(old_output).name
        return output_dir / f"{Path(old_name).stem}__ransac.png"
    return output_dir / f"{pair_tag}__ransac.png"


def _row_for_pair(
    *,
    method: str,
    method_dir: Path,
    left_key_path: Path,
    right_key_path: Path,
    output_dir: Path,
    ransac_reproj_threshold: float,
    ransac_confidence: float,
    ransac_max_iters: int,
    ransac_model: str,
    ransac_mode: str,
    loose_keep_pixel_threshold: float,
    dry_run: bool,
) -> dict[str, Any]:
    pair_tag = _pair_tag_from_left_key(left_key_path)
    metadata_path = method_dir / "match_metadata" / f"{pair_tag}.json"
    metadata = _load_json(metadata_path) if metadata_path.exists() else {}
    old_visualization = _old_visualization_payload(metadata)
    left_dom = (
        old_visualization.get("left_dom")
        or _metadata_path_value(metadata, "left")
        or _manifest_dom_path_value(metadata, "left")
    )
    right_dom = (
        old_visualization.get("right_dom")
        or _metadata_path_value(metadata, "right")
        or _manifest_dom_path_value(metadata, "right")
    )
    if not isinstance(left_dom, str) or not isinstance(right_dom, str):
        raise ValueError(f"Metadata lacks match_visualization left/right DOM paths: {metadata_path}")

    left_key = read_key_file(left_key_path)
    right_key = read_key_file(right_key_path)
    filtered_left, filtered_right, ransac_summary = filter_stereo_pair_keypoints_with_ransac(
        left_key,
        right_key,
        ransac_reproj_threshold=ransac_reproj_threshold,
        ransac_confidence=ransac_confidence,
        ransac_max_iters=ransac_max_iters,
        ransac_model=ransac_model,
        ransac_coordinate_space="dom_pixel",
        ransac_mode=ransac_mode,
        loose_keep_pixel_threshold=loose_keep_pixel_threshold,
    )

    output_path = _resolve_output_path(
        pair_tag=pair_tag,
        old_visualization=old_visualization,
        output_dir=output_dir,
    )
    visualization_result: dict[str, Any] | None = None
    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        old_output_path = old_visualization.get("output_path")
        old_preview_cache = None
        if isinstance(old_output_path, str) and old_output_path:
            old_preview_cache = Path(old_output_path).parent / "preview_cache"
        visualization_result = write_stereo_pair_match_visualization(
            left_dom,
            right_dom,
            filtered_left,
            filtered_right,
            output_path=output_path,
            scale_factor=_safe_float(old_visualization.get("scale_factor"), 1.0 / 3.0),
            visualization_mode=str(old_visualization.get("visualization_mode_requested") or "auto"),
            memory_profile=str(old_visualization.get("memory_profile") or "low-memory"),
            preview_level=_safe_int(old_visualization.get("preview_level"), None),
            preview_cache_dir=old_preview_cache,
            preview_cache_source=str(old_visualization.get("preview_cache_source") or "visualization_cache"),
            highlight_match_indices=tuple(ransac_summary.get("retained_soft_outlier_positions", ())),
        )
        visualization_result["ransac"] = ransac_summary

    raw_count = len(left_key.points)
    retained_count = len(filtered_left.points)
    dropped_count = raw_count - retained_count
    retained_fraction = (retained_count / raw_count) if raw_count else 0.0
    row = {
        "method": method,
        "pair_tag": pair_tag,
        "status": "dry_run" if dry_run else "written",
        "left_key": str(left_key_path),
        "right_key": str(right_key_path),
        "left_dom": left_dom,
        "right_dom": right_dom,
        "raw_match_count": raw_count,
        "ransac_retained_count": retained_count,
        "ransac_dropped_count": dropped_count,
        "ransac_retained_fraction": retained_fraction,
        "ransac_status": ransac_summary.get("status"),
        "ransac_applied": ransac_summary.get("applied"),
        "ransac_model": ransac_summary.get("model"),
        "ransac_coordinate_space": ransac_summary.get("coordinate_space"),
        "ransac_matrix_type": ransac_summary.get("matrix_type"),
        "ransac_mode": ransac_summary.get("mode"),
        "opencv_inlier_count": ransac_summary.get("opencv_inlier_count"),
        "opencv_outlier_count": ransac_summary.get("opencv_outlier_count"),
        "retained_soft_outlier_count": ransac_summary.get("retained_soft_outlier_count"),
        "visualization_output_path": str(output_path),
        "old_visualization_output_path": old_visualization.get("output_path"),
        "metadata_path": str(metadata_path),
        "ransac_summary": ransac_summary,
        "visualization_result": visualization_result,
    }
    return row


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "method",
        "pair_tag",
        "status",
        "raw_match_count",
        "ransac_retained_count",
        "ransac_dropped_count",
        "ransac_retained_fraction",
        "ransac_status",
        "ransac_applied",
        "ransac_model",
        "ransac_coordinate_space",
        "ransac_matrix_type",
        "ransac_mode",
        "opencv_inlier_count",
        "opencv_outlier_count",
        "retained_soft_outlier_count",
        "visualization_output_path",
        "old_visualization_output_path",
        "left_key",
        "right_key",
        "left_dom",
        "right_dom",
        "metadata_path",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    raw_total = sum(int(row["raw_match_count"]) for row in rows)
    retained_total = sum(int(row["ransac_retained_count"]) for row in rows)
    dropped_total = raw_total - retained_total
    return {
        "pair_count": len(rows),
        "raw_match_count": raw_total,
        "ransac_retained_count": retained_total,
        "ransac_dropped_count": dropped_total,
        "ransac_retained_fraction": (retained_total / raw_total) if raw_total else 0.0,
    }


def rerender_root(
    *,
    output_root: Path,
    methods: tuple[str, ...],
    ransac_reproj_threshold: float,
    ransac_confidence: float,
    ransac_max_iters: int,
    ransac_model: str,
    ransac_mode: str,
    loose_keep_pixel_threshold: float,
    dry_run: bool,
) -> dict[str, Any]:
    combined_rows: list[dict[str, Any]] = []
    method_summaries: dict[str, Any] = {}
    for method in methods:
        method_dir = output_root / method
        key_dir = method_dir / "dom_keys"
        if not key_dir.exists():
            continue
        output_dir = method_dir / "match_viz_ransac"
        rows: list[dict[str, Any]] = []
        for left_key_path in sorted(key_dir.glob("*_A.key")):
            right_key_path = left_key_path.with_name(left_key_path.name.replace("_A.key", "_B.key"))
            if not right_key_path.exists():
                rows.append(
                    {
                        "method": method,
                        "pair_tag": _pair_tag_from_left_key(left_key_path),
                        "status": "missing_right_key",
                        "left_key": str(left_key_path),
                        "right_key": str(right_key_path),
                        "raw_match_count": 0,
                        "ransac_retained_count": 0,
                        "ransac_dropped_count": 0,
                        "ransac_retained_fraction": 0.0,
                    }
                )
                continue
            rows.append(
                _row_for_pair(
                    method=method,
                    method_dir=method_dir,
                    left_key_path=left_key_path,
                    right_key_path=right_key_path,
                    output_dir=output_dir,
                    ransac_reproj_threshold=ransac_reproj_threshold,
                    ransac_confidence=ransac_confidence,
                    ransac_max_iters=ransac_max_iters,
                    ransac_model=ransac_model,
                    ransac_mode=ransac_mode,
                    loose_keep_pixel_threshold=loose_keep_pixel_threshold,
                    dry_run=dry_run,
                )
            )
        method_summaries[method] = _summarize_rows(rows)
        method_summaries[method]["output_dir"] = str(output_dir)
        if not dry_run:
            _write_csv(method_dir / "ransac_match_visualization_summary.csv", rows)
            _write_json(
                method_dir / "ransac_match_visualization_summary.json",
                {
                    "method": method,
                    "summary": method_summaries[method],
                    "rows": rows,
                },
            )
        combined_rows.extend(rows)

    combined_summary = {
        "output_root": str(output_root),
        "methods": method_summaries,
        "combined": _summarize_rows(combined_rows),
        "ransac_parameters": {
            "ransac_reproj_threshold": ransac_reproj_threshold,
            "ransac_confidence": ransac_confidence,
            "ransac_max_iters": ransac_max_iters,
            "ransac_model": ransac_model,
            "ransac_mode": ransac_mode,
            "loose_keep_pixel_threshold": loose_keep_pixel_threshold,
        },
        "dry_run": dry_run,
    }
    if not dry_run:
        _write_csv(output_root / "ransac_match_visualization_summary.csv", combined_rows)
        _write_json(
            output_root / "ransac_match_visualization_summary.json",
            {
                "summary": combined_summary,
                "rows": combined_rows,
            },
        )
    return combined_summary


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path, help="Deep-match benchmark output root.")
    parser.add_argument(
        "--methods",
        default=",".join(DEFAULT_METHODS),
        help=f"Comma-separated method directories. Default: {','.join(DEFAULT_METHODS)}.",
    )
    parser.add_argument("--ransac-reproj-threshold", type=float, default=3.0)
    parser.add_argument("--ransac-confidence", type=float, default=0.995)
    parser.add_argument("--ransac-max-iters", type=int, default=5000)
    parser.add_argument("--ransac-model", choices=("affine-partial", "affine", "homography"), default="affine-partial")
    parser.add_argument("--ransac-mode", choices=("strict", "loose"), default="loose")
    parser.add_argument("--loose-ransac-keep-threshold", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_argument_parser().parse_args(argv)
    methods = tuple(method.strip() for method in args.methods.split(",") if method.strip())
    summary = rerender_root(
        output_root=args.output_root,
        methods=methods,
        ransac_reproj_threshold=args.ransac_reproj_threshold,
        ransac_confidence=args.ransac_confidence,
        ransac_max_iters=args.ransac_max_iters,
        ransac_model=args.ransac_model,
        ransac_mode=args.ransac_mode,
        loose_keep_pixel_threshold=args.loose_ransac_keep_threshold,
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
