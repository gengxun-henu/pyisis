#!/usr/bin/env python3
"""Build Nature-style comparison inputs and figures for LRO polar match methods."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import median
from typing import Any

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


METHOD_ORDER = ("loftr", "superpoint_lightglue", "sift_lightglue", "sift_flann", "adaptive")
METHOD_LABELS = {
    "loftr": "LoFTR",
    "superpoint_lightglue": "SuperPoint+LG",
    "sift_lightglue": "SIFT+LG",
    "sift_flann": "SIFT+FLANN",
    "adaptive": "Adaptive",
}
METHOD_COLORS = {
    "loftr": "#6C8EBF",
    "superpoint_lightglue": "#B58AC6",
    "sift_lightglue": "#64A889",
    "sift_flann": "#C9A24A",
    "adaptive": "#D67C63",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _finite_int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _metadata_value(metadata: dict[str, Any], key: str) -> Any:
    if key in metadata:
        return metadata.get(key)
    image_match = metadata.get("image_match")
    if isinstance(image_match, dict) and key in image_match:
        return image_match.get(key)
    return None


def _method_pair_metadata_index(method_dir: Path, method: str) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    metadata_dir = method_dir / "match_metadata"
    if metadata_dir.exists():
        for metadata_path in sorted(metadata_dir.glob("*.json")):
            try:
                index[metadata_path.stem] = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue

    summary_path = method_dir / f"{method}_large_dom_match_summary.json"
    if summary_path.exists():
        try:
            rows = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            rows = []
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                pair_tag = row.get("pair_tag")
                if isinstance(pair_tag, str) and pair_tag:
                    index.setdefault(pair_tag, row)
    return index


def _parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _deep_runtime_seconds(method_dir: Path) -> tuple[float | None, dict[str, Any]]:
    summaries = sorted((method_dir / "deep_match_workspaces").glob("*/deep_match_run_summary.json"))
    if not summaries:
        return None, {
            "runtime_source": "not_available",
            "deep_summary_count": 0,
            "deep_task_count": 0,
            "deep_succeeded_task_count": 0,
            "deep_failed_task_count": 0,
        }

    task_seconds = 0.0
    task_count = 0
    succeeded = 0
    failed = 0
    manifest_wall_seconds = 0.0
    for summary_path in summaries:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        started = _parse_utc(summary.get("started_at_utc"))
        finished = _parse_utc(summary.get("finished_at_utc"))
        if started and finished and finished >= started:
            manifest_wall_seconds += (finished - started).total_seconds()
        task_count += int(summary.get("task_count") or 0)
        succeeded += int(summary.get("succeeded_task_count") or 0)
        failed += int(summary.get("failed_task_count") or 0)
        for task in summary.get("tasks", []):
            task_started = _parse_utc(task.get("started_at_utc"))
            task_finished = _parse_utc(task.get("finished_at_utc"))
            if task_started and task_finished and task_finished >= task_started:
                task_seconds += (task_finished - task_started).total_seconds()

    return task_seconds, {
        "runtime_source": "deep_task_started_finished_sum",
        "deep_summary_count": len(summaries),
        "deep_task_count": task_count,
        "deep_succeeded_task_count": succeeded,
        "deep_failed_task_count": failed,
        "deep_manifest_wall_seconds_sum": manifest_wall_seconds,
    }


def _mtime_runtime_seconds(method_dir: Path, method: str) -> tuple[float | None, dict[str, Any]]:
    command_path = method_dir / "command.json"
    summary_path = method_dir / f"{method}_large_dom_match_summary.json"
    if not command_path.exists() or not summary_path.exists():
        return None, {"runtime_source": "not_available"}
    seconds = summary_path.stat().st_mtime - command_path.stat().st_mtime
    return max(0.0, seconds), {
        "runtime_source": "command_to_method_summary_mtime_proxy",
        "command_json": str(command_path),
        "method_summary_json": str(summary_path),
    }


def _adaptive_runtime_seconds(method_dir: Path) -> tuple[float | None, dict[str, Any]]:
    deep_seconds, deep_meta = _deep_runtime_seconds(method_dir)
    classic_seconds, classic_meta = _mtime_runtime_seconds(method_dir, "adaptive")
    components = []
    total = 0.0
    if deep_seconds is not None:
        total += deep_seconds
        components.append("deep_task_started_finished_sum")
    if classic_seconds is not None:
        total += classic_seconds
        components.append("command_to_method_summary_mtime_proxy")
    if not components:
        return None, {"runtime_source": "not_available"}
    return total, {
        **deep_meta,
        "runtime_source": "adaptive_" + "_plus_".join(components),
        "adaptive_deep_runtime_seconds": deep_seconds,
        "adaptive_classic_runtime_seconds": classic_seconds,
        "classic_runtime_meta": classic_meta,
    }


def build_source_data(output_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = _read_csv(output_root / "ransac_match_visualization_summary.csv")
    metadata_indexes = {
        method: _method_pair_metadata_index(output_root / method, method)
        for method in METHOD_ORDER
    }
    pair_rows: list[dict[str, Any]] = []
    for row in rows:
        method = row["method"]
        pair_tag = row["pair_tag"]
        pair_metadata = metadata_indexes.get(method, {}).get(pair_tag, {})
        left_feature_count = _finite_int_or_none(_metadata_value(pair_metadata, "left_feature_count_total"))
        right_feature_count = _finite_int_or_none(_metadata_value(pair_metadata, "right_feature_count_total"))
        feature_count = _finite_int_or_none(_metadata_value(pair_metadata, "feature_count_total"))
        if feature_count is None and left_feature_count is not None and right_feature_count is not None:
            feature_count = left_feature_count + right_feature_count
        tile_match_count = _finite_int_or_none(_metadata_value(pair_metadata, "tile_match_count_total"))
        pair_rows.append(
            {
                "method": method,
                "method_label": METHOD_LABELS.get(method, method),
                "pair_tag": pair_tag,
                "left_feature_count_total": left_feature_count,
                "right_feature_count_total": right_feature_count,
                "feature_count_total": feature_count,
                "tile_match_count_total": tile_match_count,
                "raw_match_count": int(row["raw_match_count"] or 0),
                "ransac_retained_count": int(row["ransac_retained_count"] or 0),
                "ransac_dropped_count": int(row["ransac_dropped_count"] or 0),
                "ransac_retained_fraction": float(row["ransac_retained_fraction"] or 0.0),
                "ransac_model": row.get("ransac_model", "affine-partial"),
                "ransac_coordinate_space": row.get("ransac_coordinate_space", "dom_pixel"),
                "raw_matches": int(row["raw_match_count"] or 0),
                "distance_retained": int(row["raw_match_count"] or 0),
                "affine_partial_retained": int(row["ransac_retained_count"] or 0)
                if row.get("ransac_model", "affine-partial") == "affine-partial"
                else None,
                "homography_retained": int(row["ransac_retained_count"] or 0)
                if row.get("ransac_model") == "homography"
                else None,
                "ransac_status": row.get("ransac_status") or "",
                "visualization_output_path": row.get("visualization_output_path") or "",
            }
        )

    method_rows: list[dict[str, Any]] = []
    for method in METHOD_ORDER:
        method_pair_rows = [row for row in pair_rows if row["method"] == method]
        if not method_pair_rows:
            continue
        raw = sum(row["raw_match_count"] for row in method_pair_rows)
        retained = sum(row["ransac_retained_count"] for row in method_pair_rows)
        dropped = raw - retained
        retained_values = [row["ransac_retained_count"] for row in method_pair_rows]
        raw_values = [row["raw_match_count"] for row in method_pair_rows]
        feature_values = [
            int(row["feature_count_total"])
            for row in method_pair_rows
            if row.get("feature_count_total") is not None
        ]
        tile_match_values = [
            int(row["tile_match_count_total"])
            for row in method_pair_rows
            if row.get("tile_match_count_total") is not None
        ]
        method_dir = output_root / method
        if method in {"loftr", "superpoint_lightglue", "sift_lightglue"}:
            runtime_seconds, runtime_meta = _deep_runtime_seconds(method_dir)
        elif method == "adaptive":
            runtime_seconds, runtime_meta = _adaptive_runtime_seconds(method_dir)
        else:
            runtime_seconds, runtime_meta = _mtime_runtime_seconds(method_dir, method)
        method_rows.append(
            {
                "method": method,
                "method_label": METHOD_LABELS.get(method, method),
                "pair_count": len(method_pair_rows),
                "raw_match_count": raw,
                "ransac_retained_count": retained,
                "ransac_dropped_count": dropped,
                "ransac_retained_fraction": (retained / raw) if raw else 0.0,
                "raw_nonzero_pair_count": sum(1 for row in method_pair_rows if row["raw_match_count"] > 0),
                "ransac_nonzero_pair_count": sum(
                    1 for row in method_pair_rows if row["ransac_retained_count"] > 0
                ),
                "feature_count_total": sum(feature_values) if feature_values else None,
                "feature_count_pair_count": len(feature_values),
                "median_feature_count_total": median(feature_values) if feature_values else None,
                "tile_match_count_total": sum(tile_match_values) if tile_match_values else None,
                "median_raw_match_count": median(raw_values) if raw_values else 0,
                "median_ransac_retained_count": median(retained_values) if retained_values else 0,
                "runtime_seconds": runtime_seconds,
                "runtime_minutes": (runtime_seconds / 60.0) if runtime_seconds is not None else None,
                **runtime_meta,
            }
        )
    return pair_rows, method_rows


def _format_count(value: float) -> str:
    if value >= 1000:
        return f"{value / 1000:.1f}k"
    return f"{int(value)}"


def plot_method_comparison(method_rows: list[dict[str, Any]], output_prefix: Path) -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
        }
    )

    labels = [row["method_label"] for row in method_rows]
    methods = [row["method"] for row in method_rows]
    colors = [METHOD_COLORS.get(method, "#777777") for method in methods]
    x = np.arange(len(method_rows))
    width = 0.36

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.3), constrained_layout=True)
    ax = axes[0, 0]
    raw = np.array([row["raw_match_count"] for row in method_rows], dtype=float)
    retained = np.array([row["ransac_retained_count"] for row in method_rows], dtype=float)
    ax.bar(x - width / 2, raw, width, color="#D7DCE2", label="Raw")
    ax.bar(x + width / 2, retained, width, color=colors, label="RANSAC retained")
    ax.set_yscale("log")
    ax.set_ylabel("Connections (log10)")
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.legend(loc="upper right")
    for xpos, value in zip(x + width / 2, retained):
        ax.text(xpos, value * 1.08 if value > 0 else 1, _format_count(value), ha="center", va="bottom", fontsize=6)
    ax.text(-0.12, 1.06, "A", transform=ax.transAxes, fontweight="bold", fontsize=10)
    ax.set_title("RANSAC reduces raw correspondences")

    ax = axes[0, 1]
    retained_fraction = np.array([row["ransac_retained_fraction"] * 100.0 for row in method_rows])
    ax.bar(x, retained_fraction, color=colors)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Retained after RANSAC (%)")
    ax.set_xticks(x, labels, rotation=25, ha="right")
    for xpos, value in zip(x, retained_fraction):
        ax.text(xpos, value + 2, f"{value:.1f}", ha="center", va="bottom", fontsize=6)
    ax.text(-0.12, 1.06, "B", transform=ax.transAxes, fontweight="bold", fontsize=10)
    ax.set_title("Geometric consistency differs by method")

    ax = axes[1, 0]
    nonzero = np.array([row["ransac_nonzero_pair_count"] for row in method_rows], dtype=float)
    pair_count = np.array([row["pair_count"] for row in method_rows], dtype=float)
    ax.bar(x, pair_count, color="#E8EAED", label="Attempted pairs")
    ax.bar(x, nonzero, color=colors, label="Pairs with retained matches")
    ax.set_ylim(0, max(pair_count) + 2)
    ax.set_ylabel("Pair count")
    ax.set_xticks(x, labels, rotation=25, ha="right")
    for xpos, ok, total in zip(x, nonzero, pair_count):
        ax.text(xpos, ok + 0.35, f"{int(ok)}/{int(total)}", ha="center", va="bottom", fontsize=6)
    ax.text(-0.12, 1.06, "C", transform=ax.transAxes, fontweight="bold", fontsize=10)
    ax.set_title("Selected-pair coverage")

    ax = axes[1, 1]
    minutes = np.array(
        [row["runtime_minutes"] if row["runtime_minutes"] is not None else np.nan for row in method_rows],
        dtype=float,
    )
    ax.bar(x, minutes, color=colors)
    ax.set_ylabel("Runtime (min)")
    ax.set_xticks(x, labels, rotation=25, ha="right")
    for xpos, value in zip(x, minutes):
        if np.isfinite(value):
            ax.text(xpos, value * 1.02 + 0.03, f"{value:.1f}", ha="center", va="bottom", fontsize=6)
    ax.text(-0.12, 1.06, "D", transform=ax.transAxes, fontweight="bold", fontsize=10)
    ax.set_title("Runtime: deep core vs classic wall proxy")

    fig.suptitle("LRO polar DOM matching benchmark", x=0.01, ha="left", fontsize=9, fontweight="bold")
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{output_prefix}.svg", bbox_inches="tight")
    fig.savefig(f"{output_prefix}.pdf", bbox_inches="tight")
    fig.savefig(f"{output_prefix}.tiff", dpi=600, bbox_inches="tight")
    fig.savefig(f"{output_prefix}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    output_root = args.output_root
    output_dir = args.output_dir or (output_root / "nature_figure_inputs")
    pair_rows, method_rows = build_source_data(output_root)

    pair_fields = [
        "method",
        "method_label",
        "pair_tag",
        "left_feature_count_total",
        "right_feature_count_total",
        "feature_count_total",
        "tile_match_count_total",
        "raw_match_count",
        "ransac_retained_count",
        "ransac_dropped_count",
        "ransac_retained_fraction",
        "ransac_model",
        "ransac_coordinate_space",
        "raw_matches",
        "distance_retained",
        "affine_partial_retained",
        "homography_retained",
        "ransac_status",
        "visualization_output_path",
    ]
    method_fields = [
        "method",
        "method_label",
        "pair_count",
        "raw_match_count",
        "ransac_retained_count",
        "ransac_dropped_count",
        "ransac_retained_fraction",
        "raw_nonzero_pair_count",
        "ransac_nonzero_pair_count",
        "feature_count_total",
        "feature_count_pair_count",
        "median_feature_count_total",
        "tile_match_count_total",
        "median_raw_match_count",
        "median_ransac_retained_count",
        "runtime_seconds",
        "runtime_minutes",
        "runtime_source",
        "deep_summary_count",
        "deep_task_count",
        "deep_succeeded_task_count",
        "deep_failed_task_count",
        "deep_manifest_wall_seconds_sum",
    ]
    _write_csv(output_dir / "five_method_pair_summary.csv", pair_rows, pair_fields)
    _write_csv(output_dir / "five_method_method_summary.csv", method_rows, method_fields)
    _write_json(
        output_dir / "five_method_match_comparison_source_data.json",
        {
            "output_root": str(output_root),
            "figure_contract": {
                "core_conclusion": (
                    "Adaptive routing and SIFT+LightGlue retain more geometrically consistent "
                    "matches than fixed classical or dense deep baselines on the selected LRO "
                    "polar DOM pairs, while runtime provenance differs between deep and classic runs."
                ),
                "archetype": "quantitative grid",
                "runtime_note": (
                    "Deep-learning runtime is summed from task started/finished timestamps; "
                    "SIFT+FLANN and adaptive runtime uses command-to-summary mtime proxy."
                ),
            },
            "method_summary": method_rows,
            "pair_summary": pair_rows,
        },
    )
    plot_method_comparison(method_rows, output_dir / "five_method_match_comparison")
    print(json.dumps({"output_dir": str(output_dir), "methods": method_rows}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
