"""Summarize and plot the LRO polar adaptive-routing benchmark.

Author: Geng Xun
Created: 2026-06-01
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import json
import math
from pathlib import Path
import statistics
from typing import Any


METHODS: tuple[tuple[str, str], ...] = (
    ("sift_flann", "SIFT+FLANN"),
    ("adaptive", "Adaptive"),
    ("loftr", "LoFTR"),
    ("superpoint_lightglue", "SuperPoint+LightGlue"),
    ("sift_lightglue", "SIFT+LightGlue"),
)


@dataclass(frozen=True, slots=True)
class ExpectedPair:
    pair_folder: str
    pair_tag: str
    latitude_band: str
    texture_class: str
    lighting_class: str
    left_product_id: str
    right_product_id: str


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _parse_pair_category(pair_folder: str) -> tuple[str, str, str]:
    parts = pair_folder.split("_")
    if len(parts) < 3:
        return "", "", ""
    category = parts[1]
    texture_lighting = parts[2]
    texture, _, lighting = texture_lighting.partition("-")
    return category, texture, lighting


def _pair_tag_from_cube_paths(left_path: str, right_path: str) -> str:
    left = Path(left_path).stem
    right = Path(right_path).stem
    return f"{left}__{right}"


def _expected_pairs(pair_paths_csv: Path) -> list[ExpectedPair]:
    grouped: dict[str, dict[str, dict[str, str]]] = {}
    with pair_paths_csv.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            grouped.setdefault(row["pair_folder"], {})[row["side"].lower()] = row

    pairs: list[ExpectedPair] = []
    for pair_folder in sorted(grouped):
        sides = grouped[pair_folder]
        if "left" not in sides or "right" not in sides:
            continue
        latitude_band, texture_class, lighting_class = _parse_pair_category(pair_folder)
        left = sides["left"]
        right = sides["right"]
        pairs.append(
            ExpectedPair(
                pair_folder=pair_folder,
                pair_tag=_pair_tag_from_cube_paths(left["echo_cal_cube"], right["echo_cal_cube"]),
                latitude_band=latitude_band,
                texture_class=texture_class,
                lighting_class=lighting_class,
                left_product_id=left["product_id"],
                right_product_id=right["product_id"],
            )
        )
    return pairs


def _method_run_summary(output_root: Path, method: str) -> dict[str, Any]:
    method_dir = output_root / method
    summary_path = method_dir / f"{method}_large_dom_match_summary.json"
    rows: list[dict[str, Any]] = []
    if summary_path.exists():
        try:
            payload = _read_json(summary_path)
            rows = payload if isinstance(payload, list) else []
        except json.JSONDecodeError:
            rows = []

    global_path = output_root / "large_dom_match_methods_summary.json"
    global_rows = []
    if global_path.exists():
        try:
            payload = _read_json(global_path)
            global_rows = payload if isinstance(payload, list) else []
        except json.JSONDecodeError:
            global_rows = []
    global_by_method = {str(row.get("method")): row for row in global_rows if isinstance(row, dict)}

    return {
        "method_summary_path": str(summary_path) if summary_path.exists() else "",
        "method_summary_rows": rows,
        "global_summary": global_by_method.get(method, {}),
        "command_path": str(method_dir / "command.json") if (method_dir / "command.json").exists() else "",
    }


def _quality_from_adaptive(adaptive: Any) -> dict[str, Any]:
    if not isinstance(adaptive, dict):
        return {}
    quality = adaptive.get("match_quality")
    if not isinstance(quality, dict):
        attempts = adaptive.get("cascade_attempts")
        if isinstance(attempts, list) and attempts:
            last = attempts[-1]
            quality = last.get("match_quality") if isinstance(last, dict) else {}
    if not isinstance(quality, dict):
        return {}
    residual = quality.get("residual_summary")
    if not isinstance(residual, dict):
        residual = {}
    decision = adaptive.get("final_decision")
    if not isinstance(decision, dict):
        decision = {}
    return {
        "inlier_count": quality.get("inlier_count"),
        "total_match_count": quality.get("total_match_count"),
        "inlier_ratio": quality.get("inlier_ratio"),
        "coverage": quality.get("coverage"),
        "quality_score": quality.get("quality_score"),
        "residual_mean": residual.get("mean"),
        "residual_p95": residual.get("p95"),
        "residual_max": residual.get("max"),
        "quality_accepted": quality.get("accepted"),
        "fallback_used": decision.get("fallback_used"),
        "stop_reason": decision.get("stop_reason"),
    }


def _row_from_metadata(
    *,
    method: str,
    display_name: str,
    expected: ExpectedPair,
    metadata_path: Path,
    run_summary: dict[str, Any],
) -> dict[str, Any]:
    base = {
        "method": method,
        "display_name": display_name,
        "pair_folder": expected.pair_folder,
        "pair_tag": expected.pair_tag,
        "latitude_band": expected.latitude_band,
        "texture_class": expected.texture_class,
        "lighting_class": expected.lighting_class,
        "left_product_id": expected.left_product_id,
        "right_product_id": expected.right_product_id,
        "metadata_path": str(metadata_path) if metadata_path.exists() else "",
    }
    if not metadata_path.exists():
        global_summary = run_summary.get("global_summary") or {}
        return {
            **base,
            "run_status": global_summary.get("status") or "missing_metadata",
            "return_code": global_summary.get("return_code"),
            "status": "missing_metadata",
            "success": False,
        }
    try:
        metadata = _read_json(metadata_path)
    except json.JSONDecodeError as exc:
        return {**base, "status": "metadata_json_error", "success": False, "error": str(exc)}

    image_match = metadata.get("image_match")
    if not isinstance(image_match, dict):
        image_match = {}
    matcher = image_match.get("matcher")
    if not isinstance(matcher, dict):
        matcher = {}
    adaptive = image_match.get("adaptive_routing")
    adaptive_dict = adaptive if isinstance(adaptive, dict) else {}
    quality = _quality_from_adaptive(adaptive)
    status = str(image_match.get("status") or metadata.get("status") or "")
    point_count = image_match.get("point_count")
    success = status in {"matched", "imported"} and isinstance(point_count, int) and point_count > 0

    return {
        **base,
        "run_status": (run_summary.get("global_summary") or {}).get("status"),
        "return_code": (run_summary.get("global_summary") or {}).get("return_code"),
        "status": status,
        "reason": image_match.get("reason") or metadata.get("reason"),
        "success": success,
        "point_count": point_count,
        "tile_count": image_match.get("tile_count"),
        "matched_tile_count": image_match.get("matched_tile_count"),
        "skipped_tile_count": image_match.get("skipped_tile_count"),
        "tile_count_after_preindex_filter": image_match.get("tile_count_after_preindex_filter"),
        "matcher_requested": matcher.get("matcher_method_requested"),
        "matcher_effective": matcher.get("matcher_method_effective") or matcher.get("matcher_method_used"),
        "deep_match_mode": image_match.get("deep_match_mode"),
        "deep_imported_task_count": (
            image_match.get("deep_match_import", {}).get("imported_task_count")
            if isinstance(image_match.get("deep_match_import"), dict)
            else None
        ),
        "deep_failed_task_count": (
            image_match.get("deep_match_import", {}).get("failed_task_count")
            if isinstance(image_match.get("deep_match_import"), dict)
            else None
        ),
        "parallel_cpu_used": image_match.get("parallel_cpu_used"),
        "parallel_cpu_worker_count": image_match.get("parallel_cpu_worker_count"),
        "adaptive_enabled": adaptive_dict.get("enabled") if adaptive_dict else False,
        "adaptive_status": adaptive_dict.get("status"),
        "adaptive_route_reason": adaptive_dict.get("route_reason") or adaptive_dict.get("reason"),
        "adaptive_selected_initial_matcher": adaptive_dict.get("selected_initial_matcher"),
        "adaptive_selected_final_matcher": adaptive_dict.get("selected_final_matcher"),
        "adaptive_cascade_plan": ",".join(str(item) for item in adaptive_dict.get("cascade_plan", []))
        if isinstance(adaptive_dict.get("cascade_plan"), list)
        else "",
        **quality,
    }


def build_pair_rows(output_root: Path, pair_paths_csv: Path) -> list[dict[str, Any]]:
    expected_pairs = _expected_pairs(pair_paths_csv)
    rows: list[dict[str, Any]] = []
    for method, display_name in METHODS:
        run_summary = _method_run_summary(output_root, method)
        for expected in expected_pairs:
            metadata_path = output_root / method / "match_metadata" / f"{expected.pair_tag}.json"
            rows.append(
                _row_from_metadata(
                    method=method,
                    display_name=display_name,
                    expected=expected,
                    metadata_path=metadata_path,
                    run_summary=run_summary,
                )
            )
    return rows


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def build_method_summary(pair_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for method, display_name in METHODS:
        rows = [row for row in pair_rows if row["method"] == method]
        successes = [row for row in rows if row.get("success") is True]
        points = [float(row["point_count"]) for row in successes if isinstance(row.get("point_count"), int)]
        coverage = [float(row["coverage"]) for row in successes if isinstance(row.get("coverage"), (int, float))]
        inlier_ratio = [float(row["inlier_ratio"]) for row in successes if isinstance(row.get("inlier_ratio"), (int, float))]
        status_counts: dict[str, int] = {}
        for row in rows:
            status_counts[str(row.get("status") or "unknown")] = status_counts.get(str(row.get("status") or "unknown"), 0) + 1
        summary.append(
            {
                "method": method,
                "display_name": display_name,
                "expected_pair_count": len(rows),
                "successful_pair_count": len(successes),
                "success_rate": len(successes) / len(rows) if rows else None,
                "total_point_count": int(sum(points)),
                "mean_point_count": _mean(points),
                "median_point_count": _median(points),
                "mean_inlier_ratio": _mean(inlier_ratio),
                "mean_coverage": _mean(coverage),
                "status_counts": status_counts,
            }
        )
    return summary


def build_category_summary(pair_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = ("method", "display_name", "latitude_band", "texture_class", "lighting_class")
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in pair_rows:
        groups.setdefault(tuple(row.get(key) for key in keys), []).append(row)
    rows: list[dict[str, Any]] = []
    for group_key, group_rows in sorted(groups.items()):
        successes = [row for row in group_rows if row.get("success") is True]
        points = [float(row["point_count"]) for row in successes if isinstance(row.get("point_count"), int)]
        rows.append(
            {
                **dict(zip(keys, group_key, strict=True)),
                "expected_pair_count": len(group_rows),
                "successful_pair_count": len(successes),
                "success_rate": len(successes) / len(group_rows) if group_rows else None,
                "mean_point_count": _mean(points),
                "median_point_count": _median(points),
            }
        )
    return rows


def _finite(value: Any) -> float | None:
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def _save_figure(fig: Any, path: Path) -> None:
    dpi = 600 if path.suffix.lower() in {".png", ".tif", ".tiff"} else None
    fig.savefig(path, dpi=dpi, bbox_inches="tight")


def _adaptive_outcome_label(row: dict[str, Any]) -> str:
    status = str(row.get("adaptive_status") or "unknown")
    final = str(row.get("adaptive_selected_final_matcher") or "").upper()
    if status == "skipped_missing_previews":
        return f"No preview route; {final or 'FLANN'}"
    if status == "routed":
        return f"Routed; {final or 'selected'}"
    return f"{status.replace('_', ' ')}; {final}" if final else status.replace("_", " ")


def make_figures(pair_rows: list[dict[str, Any]], method_summary: list[dict[str, Any]], output_dir: Path) -> list[str]:
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7,
            "axes.linewidth": 0.6,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    colors = {
        "sift_flann": "#4C78A8",
        "adaptive": "#F58518",
        "loftr": "#54A24B",
        "superpoint_lightglue": "#B279A2",
        "sift_lightglue": "#E45756",
    }

    generated: list[str] = []

    # Figure 1: method availability and success rate.
    fig, ax = plt.subplots(figsize=(3.5, 2.2), constrained_layout=True)
    labels = [row["display_name"] for row in method_summary]
    rates = [(_finite(row.get("success_rate")) or 0.0) * 100.0 for row in method_summary]
    bar_colors = [colors[row["method"]] for row in method_summary]
    ax.bar(range(len(labels)), rates, color=bar_colors, width=0.72)
    ax.set_ylabel("Successful pairs (%)")
    ax.set_ylim(0, 105)
    ax.set_xticks(range(len(labels)), labels, rotation=35, ha="right")
    for idx, row in enumerate(method_summary):
        ax.text(idx, rates[idx] + 3, f"{row['successful_pair_count']}/{row['expected_pair_count']}", ha="center", va="bottom", fontsize=6)
    ax.set_title("Method success on reduced LRO polar DOM pairs")
    for ext in ("svg", "pdf", "png", "tiff"):
        path = output_dir / f"method_success.{ext}"
        _save_figure(fig, path)
        generated.append(str(path))
    plt.close(fig)

    # Figure 2: match count distribution for methods with successful metadata.
    fig, ax = plt.subplots(figsize=(3.5, 2.3), constrained_layout=True)
    plotted_labels: list[str] = []
    data: list[list[float]] = []
    plotted_colors: list[str] = []
    for method, display_name in METHODS:
        values = [
            float(row["point_count"])
            for row in pair_rows
            if row["method"] == method and row.get("success") is True and isinstance(row.get("point_count"), int)
        ]
        if values:
            data.append(values)
            plotted_labels.append(display_name)
            plotted_colors.append(colors[method])
    if data:
        parts = ax.violinplot(data, showmedians=True, showextrema=False)
        for body, color in zip(parts["bodies"], plotted_colors, strict=False):
            body.set_facecolor(color)
            body.set_edgecolor("#333333")
            body.set_alpha(0.75)
        parts["cmedians"].set_color("#111111")
        ax.set_xticks(range(1, len(plotted_labels) + 1), plotted_labels, rotation=25, ha="right")
    ax.set_ylabel("Matched DOM points")
    ax.set_title("Match yield distribution")
    for ext in ("svg", "pdf", "png", "tiff"):
        path = output_dir / f"match_yield_distribution.{ext}"
        _save_figure(fig, path)
        generated.append(str(path))
    plt.close(fig)

    # Figure 3: adaptive routing outcome.
    adaptive_rows = [row for row in pair_rows if row["method"] == "adaptive" and row.get("metadata_path")]
    route_counts: dict[str, int] = {}
    for row in adaptive_rows:
        label = _adaptive_outcome_label(row)
        route_counts[label] = route_counts.get(label, 0) + 1
    fig, ax = plt.subplots(figsize=(3.5, 2.0), constrained_layout=True)
    if route_counts:
        labels = list(route_counts)
        values = [route_counts[label] for label in labels]
        ax.barh(range(len(labels)), values, color=colors["adaptive"])
        ax.set_yticks(range(len(labels)), labels)
        ax.set_xlabel("Pair count")
        for idx, value in enumerate(values):
            ax.text(value + 0.1, idx, str(value), va="center", fontsize=6)
    ax.set_title("Adaptive routing outcomes")
    for ext in ("svg", "pdf", "png", "tiff"):
        path = output_dir / f"adaptive_routing_outcomes.{ext}"
        _save_figure(fig, path)
        generated.append(str(path))
    plt.close(fig)

    return generated


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize LRO polar adaptive-routing benchmark outputs.")
    parser.add_argument("--benchmark-root", type=Path, default=Path("work/lro_polar_adaptive_routing_match_benchmark"))
    parser.add_argument("--pair-paths-csv", type=Path, default=Path("work/lro_polar_adaptive_routing_preprocess/reduced_selected_pair_paths.csv"))
    parser.add_argument("--reports-dir", type=Path, default=None)
    parser.add_argument("--make-figures", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    benchmark_root = args.benchmark_root.expanduser().resolve()
    pair_paths_csv = args.pair_paths_csv.expanduser().resolve()
    reports_dir = (args.reports_dir or benchmark_root / "reports").expanduser().resolve()

    pair_rows = build_pair_rows(benchmark_root, pair_paths_csv)
    method_summary = build_method_summary(pair_rows)
    category_summary = build_category_summary(pair_rows)

    _write_csv(reports_dir / "pair_summary.csv", pair_rows)
    _write_json(reports_dir / "pair_summary.json", pair_rows)
    _write_csv(reports_dir / "method_summary.csv", method_summary)
    _write_json(reports_dir / "method_summary.json", method_summary)
    _write_csv(reports_dir / "category_summary.csv", category_summary)
    _write_json(reports_dir / "category_summary.json", category_summary)

    generated_figures: list[str] = []
    if args.make_figures:
        generated_figures = make_figures(pair_rows, method_summary, reports_dir / "figures")

    manifest = {
        "benchmark_root": str(benchmark_root),
        "pair_paths_csv": str(pair_paths_csv),
        "reports_dir": str(reports_dir),
        "pair_summary_csv": str(reports_dir / "pair_summary.csv"),
        "method_summary_csv": str(reports_dir / "method_summary.csv"),
        "category_summary_csv": str(reports_dir / "category_summary.csv"),
        "generated_figures": generated_figures,
    }
    _write_json(reports_dir / "report_manifest.json", manifest)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
