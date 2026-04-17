"""Generate a cnetmerge shell script from pairwise stereo ControlNet outputs.

Author: Geng Xun
Created: 2026-04-17
Updated: 2026-04-17  Geng Xun added pairwise `.net` list generation plus a reproducible cnetmerge shell wrapper for the DOM matching workflow.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from dataclasses import dataclass
import json
from pathlib import Path
import shlex
import sys


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.listing import StereoPair, read_stereo_pair_list
else:
    from .listing import StereoPair, read_stereo_pair_list


@dataclass(frozen=True, slots=True)
class MergeScriptSummary:
    overlap_pair_count: int
    included_count: int
    skipped_missing_count: int
    pair_list_path: str
    script_path: str
    output_net: str
    included_pairs: tuple[str, ...]
    skipped_pairs: tuple[str, ...]
    included_nets: tuple[str, ...]


def pair_controlnet_filename(pair: StereoPair, *, suffix: str = ".net") -> str:
    return f"{Path(pair.left).stem}__{Path(pair.right).stem}{suffix}"


def generate_cnetmerge_shell_script(
    overlap_list_path: str | Path,
    pair_net_directory: str | Path,
    output_net_path: str | Path,
    script_path: str | Path,
    *,
    network_id: str,
    description: str = "Merged DOM matching ControlNet",
    log_path: str | Path | None = None,
    pair_list_path: str | Path | None = None,
    pair_net_suffix: str = ".net",
    cnetmerge_executable: str = "cnetmerge",
    skip_missing: bool = True,
) -> dict[str, object]:
    overlap_pairs = read_stereo_pair_list(overlap_list_path)
    if not overlap_pairs:
        raise ValueError("The overlap pair list is empty.")

    pair_dir = Path(pair_net_directory)
    pair_list = Path(pair_list_path) if pair_list_path is not None else Path(script_path).with_suffix(".lis")
    output_net = Path(output_net_path)
    script = Path(script_path)

    included_pairs: list[str] = []
    skipped_pairs: list[str] = []
    included_nets: list[str] = []
    for pair in overlap_pairs:
        expected_net = pair_dir / pair_controlnet_filename(pair, suffix=pair_net_suffix)
        if expected_net.exists():
            included_pairs.append(pair.as_csv_line())
            included_nets.append(str(expected_net))
            continue
        if skip_missing:
            skipped_pairs.append(pair.as_csv_line())
            continue
        raise FileNotFoundError(f"Expected pairwise ControlNet is missing: {expected_net}")

    if not included_nets:
        raise ValueError("No pairwise ControlNet files were available to merge.")

    pair_list.write_text("\n".join(included_nets) + "\n", encoding="utf-8")

    command_parts = [
        cnetmerge_executable,
        "INPUTTYPE=list",
        f"CLIST={str(pair_list)}",
        f"ONET={str(output_net)}",
        "DUPLICATEPOINTS=merge",
        f"NETWORKID={network_id}",
        f"DESCRIPTION={description}",
    ]
    if log_path is not None:
        command_parts.append(f"LOG={str(log_path)}")

    shell_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        f"# Auto-generated from {Path(overlap_list_path)}",
        f"# Included pairwise networks: {len(included_nets)}",
    ]
    if skipped_pairs:
        shell_lines.append(f"# Skipped missing pairwise networks: {len(skipped_pairs)}")
    shell_lines.extend(
        [
            "",
            " \\\n  ".join(shlex.quote(part) for part in command_parts),
            "",
        ]
    )
    script.write_text("\n".join(shell_lines), encoding="utf-8")
    script.chmod(0o755)

    summary = MergeScriptSummary(
        overlap_pair_count=len(overlap_pairs),
        included_count=len(included_nets),
        skipped_missing_count=len(skipped_pairs),
        pair_list_path=str(pair_list),
        script_path=str(script),
        output_net=str(output_net),
        included_pairs=tuple(included_pairs),
        skipped_pairs=tuple(skipped_pairs),
        included_nets=tuple(included_nets),
    )
    return asdict(summary)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a shell script that merges pairwise ControlNet files with cnetmerge.")
    parser.add_argument("overlap_list", help="Path to images_overlap.lis.")
    parser.add_argument("pair_net_directory", help="Directory containing pairwise stereo-pair .net files.")
    parser.add_argument("output_net", help="Output merged ControlNet path.")
    parser.add_argument("script_path", help="Output shell script path.")
    parser.add_argument("--network-id", required=True, help="NetworkId passed to cnetmerge.")
    parser.add_argument("--description", default="Merged DOM matching ControlNet", help="Description passed to cnetmerge.")
    parser.add_argument("--log", default=None, help="Optional cnetmerge log path.")
    parser.add_argument("--pair-list", default=None, help="Optional path for the generated cnetmerge input list.")
    parser.add_argument("--pair-net-suffix", default=".net", help="Filename suffix used for pairwise ControlNet files.")
    parser.add_argument("--cnetmerge", default="cnetmerge", help="Path to the cnetmerge executable.")
    parser.add_argument("--strict", action="store_true", help="Fail if any overlap pair is missing a pairwise .net file.")
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    result = generate_cnetmerge_shell_script(
        args.overlap_list,
        args.pair_net_directory,
        args.output_net,
        args.script_path,
        network_id=args.network_id,
        description=args.description,
        log_path=args.log,
        pair_list_path=args.pair_list,
        pair_net_suffix=args.pair_net_suffix,
        cnetmerge_executable=args.cnetmerge,
        skip_missing=not args.strict,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
