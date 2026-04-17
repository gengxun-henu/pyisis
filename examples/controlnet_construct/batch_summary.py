"""Aggregate per-pair DOM matching ControlNet reports into a batch summary.

Author: Geng Xun
Created: 2026-04-17
Updated: 2026-04-17  Geng Xun added regression-friendly helpers that normalize per-pair JSON reports and write fixed-name batch summary reports.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.controlnet_merge import pair_controlnet_filename
    from controlnet_construct.listing import StereoPair
else:
    from .controlnet_merge import pair_controlnet_filename
    from .listing import StereoPair


DEFAULT_PAIR_REPORT_SUFFIX = ".summary.json"
DEFAULT_BATCH_REPORT_NAME = "controlnet_batch_summary.json"


def pair_report_filename(pair: StereoPair, *, suffix: str = DEFAULT_PAIR_REPORT_SUFFIX) -> str:
    return pair_controlnet_filename(pair, suffix=suffix)


def _nested_get(mapping: dict[str, object], *path: str) -> object | None:
    current: object = mapping
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _maybe_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _maybe_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _safe_ratio(numerator: int | None, denominator: int | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return float(numerator) / float(denominator)


def _round_rate(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 6)


def summarize_pair_result(pair_result: dict[str, object]) -> dict[str, object]:
    pair_name = str(
        pair_result.get("pair")
        or pair_result.get("pair_name")
        or pair_result.get("name")
        or "unknown_pair"
    )

    match_point_count = _maybe_int(
        pair_result.get("match_point_count")
        or _nested_get(pair_result, "match", "point_count")
    )
    merge_point_count = _maybe_int(
        pair_result.get("merge_point_count")
        or pair_result.get("merged_point_count")
        or _nested_get(pair_result, "merge", "unique_count")
        or _nested_get(pair_result, "merge", "point_count")
    )
    control_point_count = _maybe_int(
        pair_result.get("control_point_count")
        or pair_result.get("final_control_point_count")
        or _nested_get(pair_result, "controlnet", "point_count")
    )
    left_retained_count = _maybe_int(
        pair_result.get("left_dom2ori_retained_count")
        or _nested_get(pair_result, "left_conversion", "output_count")
    )
    right_retained_count = _maybe_int(
        pair_result.get("right_dom2ori_retained_count")
        or _nested_get(pair_result, "right_conversion", "output_count")
    )
    direct_retained_count = _maybe_int(pair_result.get("dom2ori_retained_count"))

    if direct_retained_count is not None:
        dom2ori_retained_count = direct_retained_count
    elif left_retained_count is not None and right_retained_count is not None:
        dom2ori_retained_count = min(left_retained_count, right_retained_count)
    elif left_retained_count is not None:
        dom2ori_retained_count = left_retained_count
    elif right_retained_count is not None:
        dom2ori_retained_count = right_retained_count
    else:
        dom2ori_retained_count = control_point_count

    direct_retention_rate = _maybe_float(pair_result.get("dom2ori_retention_rate"))
    if direct_retention_rate is None:
        side_rates = [
            rate
            for rate in (
                _safe_ratio(left_retained_count, merge_point_count),
                _safe_ratio(right_retained_count, merge_point_count),
            )
            if rate is not None
        ]
        if side_rates:
            dom2ori_retention_rate = sum(side_rates) / len(side_rates)
        else:
            dom2ori_retention_rate = _safe_ratio(dom2ori_retained_count, merge_point_count)
    else:
        dom2ori_retention_rate = direct_retention_rate

    merge_applied = _nested_get(pair_result, "merge", "applied")
    return {
        "pair": pair_name,
        "match_point_count": match_point_count or 0,
        "merge_point_count": merge_point_count or 0,
        "dom2ori_retained_count": dom2ori_retained_count or 0,
        "left_dom2ori_retained_count": left_retained_count,
        "right_dom2ori_retained_count": right_retained_count,
        "control_point_count": control_point_count or 0,
        "dom2ori_retention_rate": _round_rate(dom2ori_retention_rate),
        "match_status": pair_result.get("status") or _nested_get(pair_result, "match", "status"),
        "merge_applied": bool(merge_applied) if merge_applied is not None else None,
    }


def build_batch_summary(
    pair_results: list[dict[str, object]],
    *,
    source_reports: list[str] | None = None,
) -> dict[str, object]:
    pair_summaries = [summarize_pair_result(result) for result in pair_results]
    retention_rates = [
        rate
        for rate in (pair_summary["dom2ori_retention_rate"] for pair_summary in pair_summaries)
        if rate is not None
    ]
    total_match_point_count = sum(int(pair_summary["match_point_count"]) for pair_summary in pair_summaries)
    total_merge_point_count = sum(int(pair_summary["merge_point_count"]) for pair_summary in pair_summaries)
    total_dom2ori_retained_count = sum(int(pair_summary["dom2ori_retained_count"]) for pair_summary in pair_summaries)
    total_final_control_point_count = sum(int(pair_summary["control_point_count"]) for pair_summary in pair_summaries)
    overall_retention_rate = _safe_ratio(total_dom2ori_retained_count, total_merge_point_count)

    return {
        "report_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "pair_count": len(pair_summaries),
        "source_report_count": len(source_reports) if source_reports is not None else len(pair_summaries),
        "total_match_point_count": total_match_point_count,
        "total_merge_point_count": total_merge_point_count,
        "total_dom2ori_retained_count": total_dom2ori_retained_count,
        "total_final_control_point_count": total_final_control_point_count,
        "average_dom2ori_retention_rate": _round_rate(sum(retention_rates) / len(retention_rates)) if retention_rates else None,
        "overall_dom2ori_retention_rate": _round_rate(overall_retention_rate),
        "source_reports": list(source_reports or []),
        "pairs": pair_summaries,
    }


def write_batch_summary_report(
    pair_results: list[dict[str, object]],
    output_path: str | Path,
    *,
    source_reports: list[str] | None = None,
) -> dict[str, object]:
    report = build_batch_summary(pair_results, source_reports=source_reports)
    Path(output_path).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        **report,
        "report_path": str(output_path),
    }


def load_pair_reports(report_paths: list[str | Path]) -> tuple[list[dict[str, object]], list[str]]:
    loaded_reports: list[dict[str, object]] = []
    resolved_paths: list[str] = []
    for report_path in report_paths:
        path = Path(report_path)
        loaded_reports.append(json.loads(path.read_text(encoding="utf-8")))
        resolved_paths.append(str(path))
    return loaded_reports, resolved_paths


def _resolve_report_paths(report_paths: list[str], report_dir: str | None, pattern: str) -> list[Path]:
    resolved: list[Path] = [Path(path) for path in report_paths]
    if report_dir is not None:
        resolved.extend(sorted(Path(report_dir).glob(pattern)))

    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for path in resolved:
        resolved_path = path.resolve()
        if resolved_path in seen:
            continue
        seen.add(resolved_path)
        unique_paths.append(path)
    return unique_paths


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aggregate per-pair DOM matching JSON reports into a batch summary JSON report.")
    parser.add_argument("report_paths", nargs="*", help="Optional per-pair JSON report files.")
    parser.add_argument("--report-dir", default=None, help="Optional directory containing per-pair JSON reports.")
    parser.add_argument("--pattern", default=f"*{DEFAULT_PAIR_REPORT_SUFFIX}", help="Glob pattern used with --report-dir.")
    parser.add_argument("--output", default=None, help=f"Optional output JSON path. Defaults to <report-dir>/{DEFAULT_BATCH_REPORT_NAME} when --report-dir is set.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_argument_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    resolved_report_paths = _resolve_report_paths(args.report_paths, args.report_dir, args.pattern)
    if not resolved_report_paths:
        raise ValueError("No per-pair JSON reports were provided for batch aggregation.")

    loaded_reports, source_reports = load_pair_reports([str(path) for path in resolved_report_paths])
    output_path = args.output
    if output_path is None and args.report_dir is not None:
        output_path = str(Path(args.report_dir) / DEFAULT_BATCH_REPORT_NAME)

    if output_path is None:
        result = build_batch_summary(loaded_reports, source_reports=source_reports)
    else:
        result = write_batch_summary_report(loaded_reports, output_path, source_reports=source_reports)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()