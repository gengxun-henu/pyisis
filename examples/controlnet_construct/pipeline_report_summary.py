"""Print compact summaries for ControlNet pipeline JSON reports.

Author: Geng Xun
Created: 2026-07-23
Updated: 2026-07-23  Geng Xun extracted report formatting from the shell pipeline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_payload(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def summarize_image_overlap(path: Path) -> str:
    payload = _load_payload(path)
    if payload is None:
        return f"image-overlap summary json: {path}"

    pair_count = payload.get("pair_count", payload.get("overlap_pair_count"))
    image_count = payload.get("image_count", payload.get("input_count"))
    parts = []
    if pair_count is not None:
        parts.append(f"pairs={pair_count}")
    if image_count is not None:
        parts.append(f"images={image_count}")
    parts.append(f"summary_json={path}")
    return "image-overlap summary: " + " ".join(parts)


def summarize_image_match(pair_tag: str, path: Path) -> str:
    payload = _load_payload(path)
    if payload is None:
        return f"image-match {pair_tag}: result_json={path}"

    parts = [f"pair={pair_tag}"]
    for key, label in (
        ("point_count", "points"),
        ("matched_tile_count", "matched_tiles"),
        ("skipped_tile_count", "skipped_tiles"),
        ("tile_count", "tiles"),
    ):
        value = payload.get(key)
        if value is not None:
            parts.append(f"{label}={value}")
    parts.append(f"result_json={path}")
    return "image-match summary: " + " ".join(parts)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    overlap_parser = subparsers.add_parser("image-overlap")
    overlap_parser.add_argument("report_path", type=Path)

    match_parser = subparsers.add_parser("image-match")
    match_parser.add_argument("pair_tag")
    match_parser.add_argument("report_path", type=Path)
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    if args.command == "image-overlap":
        print(summarize_image_overlap(args.report_path))
    elif args.command == "image-match":
        print(summarize_image_match(args.pair_tag, args.report_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
