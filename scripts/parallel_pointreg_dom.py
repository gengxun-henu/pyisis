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
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


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


def discover_chunk_files(work_dir: str, prefix: str = "chunk") -> list[str]:
    chunks = sorted(str(p) for p in Path(work_dir).glob(f"{prefix}*.net"))
    if not chunks:
        raise FileNotFoundError(
            f"No chunk files found matching '{prefix}*.net' in {work_dir}. "
            f"cnetsplit may have failed."
        )
    return chunks


_LOG_PREFIX = "[parallel_pointreg_dom]"


def run_cnetsplit(cnetsplit_path: str, cnet: str, work_dir: str, num_output: int) -> None:
    subprocess.run(
        [
            cnetsplit_path,
            f"CNET={cnet}",
            f"ONET_PREFIX={str(Path(work_dir) / 'chunk')}",
            f"NUM_OUTPUT_FILES={num_output}",
        ],
        check=True,
    )


def _run_subprocess(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=False)


def dispatch_workers(
    worker_commands: list[list[str]],
    num_processes: int,
) -> list[tuple[int, subprocess.CompletedProcess]]:
    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        futures = {
            executor.submit(_run_subprocess, cmd): index
            for index, cmd in enumerate(worker_commands)
        }
        results = []
        for future in as_completed(futures):
            index = futures[future]
            results.append((index, future.result()))
    return sorted(results, key=lambda pair: pair[0])


def run_cnetmerge(
    cnetmerge_path: str,
    result_files: list[str],
    onet: str,
    work_dir: str,
) -> None:
    list_path = str(Path(work_dir) / "results.lis")
    Path(list_path).write_text("\n".join(result_files) + "\n", encoding="utf-8")
    subprocess.run(
        [
            cnetmerge_path,
            "INPUTTYPE=list",
            f"CLIST={list_path}",
            f"ONET={onet}",
            "DUPLICATEPOINTS=merge",
        ],
        check=True,
    )


def run_parallel_pointreg_dom(args: argparse.Namespace) -> int:
    script_path = str(Path(__file__).resolve().parent / "pointreg_dom.py")
    python_executable = sys.executable

    auto_work_dir = args.work_dir is None
    work_dir = args.work_dir if args.work_dir else tempfile.mkdtemp(prefix="pointreg_dom_")
    Path(work_dir).mkdir(parents=True, exist_ok=True)

    start_time = time.monotonic()

    # Step 1: Split
    try:
        run_cnetsplit(args.cnetsplit, args.cnet, work_dir, args.num_processes)
    except subprocess.CalledProcessError:
        print(f"{_LOG_PREFIX} cnetsplit failed.", file=sys.stderr, flush=True)
        if auto_work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)
        return 1

    chunk_files = discover_chunk_files(work_dir)
    print(f"{_LOG_PREFIX} split into {len(chunk_files)} chunks.", file=sys.stderr, flush=True)

    # Step 2: Dispatch workers
    worker_commands = []
    result_files = []
    for index, chunk_path in enumerate(chunk_files):
        result_path = str(Path(work_dir) / f"result_{index:03d}.net")
        cmd = build_worker_command(python_executable, script_path, chunk_path, result_path, args)
        worker_commands.append(cmd)
        result_files.append(result_path)

    worker_results = dispatch_workers(worker_commands, args.num_processes)

    failed_workers = [(i, r) for i, r in worker_results if r.returncode != 0]
    succeeded = len(worker_results) - len(failed_workers)
    elapsed = time.monotonic() - start_time

    for index, completed in worker_results:
        status = "done" if completed.returncode == 0 else "FAILED"
        chunk_name = Path(chunk_files[index]).name
        result_name = Path(result_files[index]).name
        print(
            f"{_LOG_PREFIX} worker {index + 1}/{len(chunk_files)} {status} "
            f"({chunk_name} -> {result_name}) exit={completed.returncode}",
            file=sys.stderr,
            flush=True,
        )

    if failed_workers:
        print(
            f"{_LOG_PREFIX} {len(failed_workers)} worker(s) failed. "
            f"Work dir preserved: {work_dir}",
            file=sys.stderr,
            flush=True,
        )
        return 2

    print(
        f"{_LOG_PREFIX} {succeeded}/{len(chunk_files)} workers succeeded in {elapsed:.1f}s",
        file=sys.stderr,
        flush=True,
    )

    # Step 3: Merge
    print(
        f"{_LOG_PREFIX} merging {len(result_files)} result chunks -> {args.onet}",
        file=sys.stderr,
        flush=True,
    )
    try:
        run_cnetmerge(args.cnetmerge, result_files, args.onet, work_dir)
    except subprocess.CalledProcessError:
        print(
            f"{_LOG_PREFIX} cnetmerge failed. Work dir preserved: {work_dir}",
            file=sys.stderr,
            flush=True,
        )
        return 3

    total_time = time.monotonic() - start_time
    print(f"{_LOG_PREFIX} done. total_time={total_time:.1f}s", file=sys.stderr, flush=True)

    # Step 4: Cleanup
    if auto_work_dir:
        shutil.rmtree(work_dir, ignore_errors=True)
    else:
        print(f"{_LOG_PREFIX} work dir preserved: {work_dir}", file=sys.stderr, flush=True)

    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(
        normalize_isis_style_args(argv or sys.argv[1:])
    )
    if args.num_processes < 1:
        parser = build_argument_parser()
        parser.error("--num-processes must be >= 1")
    if args.num_processes == 1:
        script_path = str(Path(__file__).resolve().parent / "pointreg_dom.py")
        forwarded = normalize_isis_style_args(argv or sys.argv[1:])
        cmd = [sys.executable, script_path] + [
            t for i, t in enumerate(forwarded)
            if not (
                t == "--num-processes"
                or t.startswith("--num-processes=")
                or (i > 0 and forwarded[i - 1] == "--num-processes")
            )
        ]
        result = subprocess.run(cmd, check=False)
        return result.returncode
    return run_parallel_pointreg_dom(args)


if __name__ == "__main__":
    raise SystemExit(main())
