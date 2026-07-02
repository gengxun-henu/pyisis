#!/usr/bin/env python3
"""Parallel DOM-space point registration for ISIS ControlNets.

Splits a large ControlNet with cnetsplit, dispatches N parallel
pointreg_dom workers via subprocess, then merges results with cnetmerge.

Author: Geng Xun
Created: 2026-07-02
Updated: 2026-07-02  Geng Xun added parallel orchestration for DOM-space
    point registration using cnetsplit, subprocess workers, and cnetmerge.
"""

from __future__ import annotations

import argparse
import sys


def normalize_isis_style_args(argv: list[str]) -> list[str]:
    normalized: list[str] = []
    for token in argv:
        if token.startswith("--") or "=" not in token:
            normalized.append(token)
            continue
        key, value = token.split("=", 1)
        normalized.extend([f"--{key.strip().lower()}", value])
    return normalized


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parallel DOM-space point registration for ISIS ControlNets.",
    )
    parser.add_argument("--fromlist", required=True, help="Original-image cube list.")
    parser.add_argument("--domlist", required=True, help="DOM cube list aligned one-to-one with --fromlist.")
    parser.add_argument("--cnet", required=True, help="Input ISIS control network.")
    parser.add_argument("--deffile", required=True, help="ISIS AutoReg/pointreg registration template PVL.")
    parser.add_argument("--onet", required=True, help="Output ISIS control network.")
    parser.add_argument("--num-processes", type=int, default=1, help="Number of parallel worker processes. Default: 1.")
    parser.add_argument("--work-dir", default=None, help="Working directory for chunk files. Default: auto temp dir.")
    parser.add_argument("--cnetsplit", default="cnetsplit", help="Path to cnetsplit executable. Default: cnetsplit.")
    parser.add_argument("--cnetmerge", default="cnetmerge", help="Path to cnetmerge executable. Default: cnetmerge.")
    parser.add_argument("--dom-band", type=int, default=1, help="Band used for DOM projection and matching.")
    parser.add_argument("--original-band", type=int, default=1, help="Band used for original-image camera projection.")
    parser.add_argument("--max-open-cubes", type=int, default=64, help="Maximum number of ISIS cubes kept open at once.")
    parser.add_argument("--skip-serial-check", action="store_true", help="Allow original/DOM list rows with different serial numbers.")
    parser.add_argument("--pvl", action="store_true", help="Write output ControlNet in PVL text format.")
    return parser


def build_worker_command(
    python_executable: str,
    script_path: str,
    chunk_cnet: str,
    result_onet: str,
    args: argparse.Namespace,
) -> list[str]:
    """Build the subprocess command for a single pointreg_dom worker.

    The chunk_cnet and result_onet parameters override the --cnet and --onet
    values from the original args so each worker operates on its own chunk.
    """
    cmd = [
        python_executable,
        script_path,
        "--fromlist", args.fromlist,
        "--domlist", args.domlist,
        "--cnet", chunk_cnet,
        "--deffile", args.deffile,
        "--onet", result_onet,
        "--dom-band", str(args.dom_band),
        "--original-band", str(args.original_band),
        "--max-open-cubes", str(args.max_open_cubes),
    ]
    if args.skip_serial_check:
        cmd.append("--skip-serial-check")
    if args.pvl:
        cmd.append("--pvl")
    return cmd
