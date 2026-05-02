#!/usr/bin/env python
"""Prepare an aligned list of cached low-resolution DOM cubes.

Author: Geng Xun
Created: 2026-05-02
Updated: 2026-05-02  Geng Xun added one-time ISIS reduce preparation for reusable low-resolution DOM matching inputs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.lowres_offset import create_low_resolution_dom, _validate_projection_ready_cube
else:
    from .lowres_offset import create_low_resolution_dom, _validate_projection_ready_cube


def _parse_level(value: str) -> int:
    try:
        level = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("level must be an integer >= 0") from exc
    if level < 0:
        raise argparse.ArgumentTypeError("level must be an integer >= 0")
    return level


def _read_list_entries(list_path: Path) -> list[str]:
    entries: list[str] = []
    for line in list_path.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if not entry:
            continue
        entries.append(entry)
    return entries


def _resolve_entry(entry: str, *, list_path: Path) -> Path:
    path = Path(entry).expanduser()
    if path.is_absolute():
        return path
    return (list_path.parent / path).resolve()


def _safe_output_stem(path: Path) -> str:
    return "".join(character if character.isalnum() or character in {"-", "_", "."} else "_" for character in path.stem)


def _default_output_path(source_path: Path, *, output_dir: Path, index: int, level: int) -> Path:
    return output_dir / f"{index:04d}_{_safe_output_stem(source_path)}__level{level}.cub"


def prepare_low_resolution_dom_list(
    dom_list_path: str | Path,
    output_list_path: str | Path,
    *,
    level: int,
    output_dir: str | Path | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, object]:
    resolved_level = int(level)
    if resolved_level < 0:
        raise ValueError("level must be >= 0")

    dom_list = Path(dom_list_path)
    output_list = Path(output_list_path)
    low_resolution_dir = Path(output_dir) if output_dir is not None else output_list.parent / "low_resolution_doms" / f"level{resolved_level}"
    entries = _read_list_entries(dom_list)
    if not entries:
        raise ValueError(f"DOM list is empty: {dom_list}")

    low_resolution_dir.mkdir(parents=True, exist_ok=True)
    output_list.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    output_entries: list[str] = []
    output_by_source: dict[Path, Path] = {}
    index_by_source: dict[Path, int] = {}

    for index, entry in enumerate(entries, start=1):
        source_path = _resolve_entry(entry, list_path=dom_list)
        first_index = index_by_source.setdefault(source_path, index)
        output_path = output_by_source.setdefault(
            source_path,
            _default_output_path(source_path, output_dir=low_resolution_dir, index=first_index, level=resolved_level),
        )
        action = "reused"
        reason = "existing projection-ready low-resolution DOM"

        if dry_run:
            action = "would_generate" if overwrite or not output_path.exists() else "would_reuse"
            reason = "dry run"
        elif overwrite or not output_path.exists():
            create_low_resolution_dom(source_path, output_path, level=resolved_level)
            action = "generated"
            reason = "missing output or overwrite requested"
        else:
            try:
                _validate_projection_ready_cube(output_path)
            except RuntimeError:
                create_low_resolution_dom(source_path, output_path, level=resolved_level)
                action = "regenerated"
                reason = "existing output was not projection-ready"

        output_entries.append(str(output_path.resolve()))
        records.append(
            {
                "index": index,
                "source_entry": entry,
                "source_path": str(source_path),
                "low_resolution_dom": str(output_path.resolve()),
                "level": resolved_level,
                "action": action,
                "reason": reason,
            }
        )

    output_list.write_text("\n".join(output_entries) + "\n", encoding="utf-8")
    return {
        "dom_list": str(dom_list),
        "output_list": str(output_list),
        "output_dir": str(low_resolution_dir),
        "level": resolved_level,
        "count": len(records),
        "unique_source_count": len(output_by_source),
        "generated_count": sum(1 for record in records if record["action"] == "generated"),
        "regenerated_count": sum(1 for record in records if record["action"] == "regenerated"),
        "reused_count": sum(1 for record in records if record["action"] == "reused"),
        "dry_run": dry_run,
        "records": records,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare reusable low-resolution DOM cubes and write an aligned list file.")
    parser.add_argument("dom_list", help="Input DOM list path. Entries are resolved relative to this list when not absolute.")
    parser.add_argument("output_list", help="Output list path aligned one-to-one with the input DOM list.")
    parser.add_argument("--level", type=_parse_level, required=True, help="ISIS reduce pyramid level. Scale divisor is 2**level.")
    parser.add_argument("--output-dir", default=None, help="Directory for cached low-resolution DOM cubes. Default: <output-list-dir>/low_resolution_doms/level<N>.")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate low-resolution DOMs even when projection-ready cached outputs exist.")
    parser.add_argument("--dry-run", action="store_true", help="Write the aligned list and report planned actions without running ISIS reduce.")
    parser.add_argument("--report-json", default=None, help="Optional JSON report path for generated/reused low-resolution DOMs.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        summary = prepare_low_resolution_dom_list(
            args.dom_list,
            args.output_list,
            level=args.level,
            output_dir=args.output_dir,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    if args.report_json is not None:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
