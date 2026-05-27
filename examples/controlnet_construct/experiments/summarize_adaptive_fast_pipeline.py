#!/usr/bin/env python3
"""Summarize adaptive fast ControlNet pipeline outputs.

Reads output produced by run_pipeline_example.sh and reports the fields needed
to compare the adaptive SIFT/FLANN fast path with deep-matcher alternatives.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _summarize_timing(root: Path) -> dict[str, Any]:
    timing_path = root / "reports" / "pipeline_timing.json"
    timing = _read_json(timing_path)
    steps = timing.get("steps", [])
    pair_matches = timing.get("pair_matches", [])
    return {
        "path": str(timing_path),
        "pipeline": timing.get("pipeline", {}),
        "steps": [
            {
                "name": step.get("name"),
                "status": step.get("status"),
                "duration_seconds": step.get("duration_seconds"),
            }
            for step in steps
            if isinstance(step, dict)
        ],
        "pair_matches": [
            {
                "name": str(pair.get("name", "")).split(":", 1)[-1],
                "status": pair.get("status"),
                "duration_seconds": pair.get("duration_seconds"),
            }
            for pair in pair_matches
            if isinstance(pair, dict)
        ],
    }


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _route_sidecar(adaptive: dict[str, Any]) -> dict[str, Any]:
    sidecar = adaptive.get("sidecar")
    if isinstance(sidecar, dict):
        return sidecar
    return {}


def _summarize_pair_result(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    adaptive = payload.get("adaptive_routing")
    if not isinstance(adaptive, dict):
        adaptive = {}
    sidecar = _route_sidecar(adaptive)
    texture = sidecar.get("texture_sparseness")
    if not isinstance(texture, dict):
        texture = adaptive.get("texture_sparseness") if isinstance(adaptive.get("texture_sparseness"), dict) else {}
    lighting = sidecar.get("lighting_difference")
    if not isinstance(lighting, dict):
        lighting = adaptive.get("lighting_difference") if isinstance(adaptive.get("lighting_difference"), dict) else {}

    return {
        "pair": path.stem,
        "path": str(path),
        "status": payload.get("status"),
        "matched_point_count": _first_present(
            payload.get("matched_point_count"),
            payload.get("point_count"),
            payload.get("match_count"),
        ),
        "tile_count": payload.get("tile_count"),
        "matched_tile_count": payload.get("matched_tile_count"),
        "skipped_tile_count": payload.get("skipped_tile_count"),
        "adaptive_routing": {
            "status": adaptive.get("status"),
            "selected_initial_matcher": adaptive.get("selected_initial_matcher"),
            "selected_final_matcher": adaptive.get("selected_final_matcher"),
            "route_reason": _first_present(adaptive.get("route_reason"), adaptive.get("reason")),
            "profile": payload.get("adaptive_routing_profile"),
            "pair_texture_sparseness": texture.get("pair_texture_sparseness"),
            "texture_weaker_side": texture.get("weaker_side"),
            "lighting_difference_score": lighting.get("lighting_difference_score"),
            "lighting_reason": lighting.get("reason"),
        },
    }


def _summarize_pairs(root: Path) -> list[dict[str, Any]]:
    match_dir = root / "match_results"
    if not match_dir.is_dir():
        raise FileNotFoundError(f"pair-result directory not found: {match_dir}")
    return [_summarize_pair_result(path) for path in sorted(match_dir.glob("*.json"))]


def _summarize_batch(root: Path) -> dict[str, Any]:
    batch_path = root / "reports" / "controlnet_batch_summary.json"
    batch = _read_json(batch_path)
    return {
        "path": str(batch_path),
        "pair_count": batch.get("pair_count"),
        "total_merge_point_count": batch.get("total_merge_point_count"),
        "total_dom2ori_retained_count": batch.get("total_dom2ori_retained_count"),
        "total_final_control_point_count": batch.get("total_final_control_point_count"),
        "average_dom2ori_retention_rate": batch.get("average_dom2ori_retention_rate"),
        "overall_dom2ori_retention_rate": batch.get("overall_dom2ori_retention_rate"),
    }


def _summarize_merged_net(root: Path) -> dict[str, Any]:
    net_path = root / "merge" / "dom_matching_merged.net"
    exists = net_path.exists()
    return {
        "path": str(net_path),
        "exists": exists,
        "size_bytes": net_path.stat().st_size if exists else None,
    }


def summarize_output(root: str | Path) -> dict[str, Any]:
    resolved_root = Path(root).expanduser().resolve()
    if not resolved_root.is_dir():
        raise FileNotFoundError(f"pipeline output directory not found: {resolved_root}")
    pairs = _summarize_pairs(resolved_root)
    return {
        "output_root": str(resolved_root),
        "timing": _summarize_timing(resolved_root),
        "controlnet_batch": _summarize_batch(resolved_root),
        "merged_net": _summarize_merged_net(resolved_root),
        "pairs": pairs,
        "route_counts": _route_counts(pairs),
    }


def _route_counts(pairs: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for pair in pairs:
        route = pair.get("adaptive_routing", {})
        if not isinstance(route, dict):
            route = {}
        initial = str(route.get("selected_initial_matcher") or "unknown")
        final = str(route.get("selected_final_matcher") or "unknown")
        key = f"{initial}->{final}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _markdown_cell(value: Any) -> str:
    if value is None:
        return ""
    return (
        str(value)
        .replace("|", "\\|")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "<br>")
    )


def _markdown_table(summary: dict[str, Any]) -> str:
    lines = [
        "# Adaptive Fast Pipeline Summary",
        "",
        f"Output root: `{_markdown_cell(summary['output_root'])}`",
        "",
        "## Stage Timing",
        "",
        "| Stage | Status | Seconds |",
        "|---|---|---:|",
    ]
    for step in summary["timing"]["steps"]:
        lines.append(
            "| {name} | {status} | {seconds} |".format(
                name=_markdown_cell(step.get("name")),
                status=_markdown_cell(step.get("status")),
                seconds=_markdown_cell(step.get("duration_seconds")),
            )
        )

    lines.extend(
        [
            "",
            "## Pair Routing",
            "",
            "| Pair | Points | Route | Texture Sparseness | Lighting Difference |",
            "|---|---:|---|---:|---:|",
        ]
    )
    for pair in summary["pairs"]:
        route = pair["adaptive_routing"]
        route_label = f"{route.get('selected_initial_matcher')} -> {route.get('selected_final_matcher')}"
        lines.append(
            "| {pair} | {points} | {route_label} | {texture} | {lighting} |".format(
                pair=_markdown_cell(pair["pair"]),
                points=_markdown_cell(pair.get("matched_point_count")),
                route_label=_markdown_cell(route_label),
                texture=_markdown_cell(route.get("pair_texture_sparseness")),
                lighting=_markdown_cell(route.get("lighting_difference_score")),
            )
        )
    batch = summary["controlnet_batch"]
    lines.extend(
        [
            "",
            "## ControlNet",
            "",
            "Final control points: "
            f"`{_markdown_cell(batch.get('total_final_control_point_count'))}`",
            f"Merged net exists: `{_markdown_cell(summary['merged_net']['exists'])}`",
            f"Merged net path: `{_markdown_cell(summary['merged_net']['path'])}`",
            "",
        ]
    )
    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize an adaptive fast ControlNet pipeline output directory."
    )
    parser.add_argument(
        "output_root",
        help="Pipeline output root, for example /tmp/pipe_test2_adaptive_fast_pipeline/balanced.",
    )
    parser.add_argument(
        "--json-output",
        default=None,
        help="Optional path to write the JSON summary. Default: print JSON to stdout.",
    )
    parser.add_argument(
        "--markdown-output",
        default=None,
        help="Optional path to write a Markdown summary table.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    summary = summarize_output(args.output_root)
    json_text = json.dumps(summary, indent=2, sort_keys=True)
    if args.json_output:
        json_path = Path(args.json_output).expanduser().resolve()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json_text + "\n", encoding="utf-8")
    else:
        print(json_text)
    if args.markdown_output:
        markdown_path = Path(args.markdown_output).expanduser().resolve()
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(_markdown_table(summary) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
