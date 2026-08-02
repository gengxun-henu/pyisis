#!/usr/bin/env python3
"""Read-only readiness checks for the PyISIS self-hosted runner.

Author: Geng Xun
Created: 2026-08-01
Updated: 2026-08-01  Geng Xun added ISIS 9 host resource and ABI validation.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Sequence


MINIMUM_MEMORY_BYTES = 16 * 1024**3
MINIMUM_AVAILABLE_BYTES = 20 * 1024**3


def _memory_total_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemTotal:"):
            return int(line.split()[1]) * 1024
    return 0


def _read_isis_version(conda_prefix: Path) -> str:
    candidates = sorted((conda_prefix / "conda-meta").glob("isis-*.json"))
    for candidate in candidates:
        try:
            metadata = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if metadata.get("name") == "isis" and metadata.get("version"):
            return str(metadata["version"])
    return ""


def _read_python_version(conda_prefix: Path) -> tuple[int, int, int] | None:
    python_bin = conda_prefix / "bin" / "python"
    if not python_bin.is_file():
        return None
    result = subprocess.run(
        [str(python_bin), "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        parts = tuple(int(part) for part in result.stdout.strip().split("."))
    except ValueError:
        return None
    return parts if len(parts) == 3 else None


def _check(ok: bool, detail: str) -> dict[str, object]:
    return {"ok": ok, "detail": detail}


def _find_tool(conda_prefix: Path, name: str) -> str | None:
    prefix_candidate = conda_prefix / "bin" / name
    if prefix_candidate.is_file() and os.access(prefix_candidate, os.X_OK):
        return str(prefix_candidate)
    return shutil.which(name)


def inspect_host(
    conda_prefix: Path,
    expected_jobs: int,
    expected_isis_major: int,
    expected_python: tuple[int, int],
    *,
    cpu_count: int | None = None,
    memory_bytes: int | None = None,
    available_bytes: int | None = None,
    isis_version: str | None = None,
    python_version: tuple[int, int, int] | None = None,
    require_ccache: bool = False,
) -> dict[str, object]:
    """Inspect host capacity and the selected Conda prefix without changing state."""

    conda_prefix = conda_prefix.resolve()
    visible_cpus = os.cpu_count() if cpu_count is None else cpu_count
    visible_cpus = visible_cpus or 0
    total_memory = _memory_total_bytes() if memory_bytes is None else memory_bytes
    disk_probe = conda_prefix if conda_prefix.exists() else conda_prefix.parent
    if available_bytes is None:
        try:
            free_disk = shutil.disk_usage(disk_probe).free
        except FileNotFoundError:
            free_disk = 0
    else:
        free_disk = available_bytes

    required_paths = (
        conda_prefix / "include" / "isis",
        conda_prefix / "lib" / "libisis.so",
        conda_prefix / "lib" / "Camera.plugin",
    )
    prefix_shape_ok = all(path.exists() for path in required_paths)
    compiler = conda_prefix / "bin" / "x86_64-conda-linux-gnu-c++"
    resolved_isis_version = isis_version if isis_version is not None else _read_isis_version(conda_prefix)
    resolved_python_version = (
        python_version if python_version is not None else _read_python_version(conda_prefix)
    )
    cmake_bin = _find_tool(conda_prefix, "cmake")
    ninja_bin = _find_tool(conda_prefix, "ninja")
    ccache_bin = _find_tool(conda_prefix, "ccache")

    checks = {
        "cpu_capacity": _check(
            visible_cpus >= expected_jobs,
            f"visible={visible_cpus}, required={expected_jobs}",
        ),
        "memory_capacity": _check(
            total_memory >= MINIMUM_MEMORY_BYTES,
            f"bytes={total_memory}, required={MINIMUM_MEMORY_BYTES}",
        ),
        "disk_capacity": _check(
            free_disk >= MINIMUM_AVAILABLE_BYTES,
            f"available_bytes={free_disk}, required={MINIMUM_AVAILABLE_BYTES}",
        ),
        "isis_prefix_shape": _check(
            prefix_shape_ok,
            ", ".join(str(path) for path in required_paths),
        ),
        "isis_version": _check(
            resolved_isis_version.split(".", 1)[0] == str(expected_isis_major),
            f"actual={resolved_isis_version or 'unresolved'}, expected_major={expected_isis_major}",
        ),
        "python_version": _check(
            resolved_python_version is not None
            and resolved_python_version[:2] == expected_python,
            "actual={} expected={}.{}".format(
                ".".join(map(str, resolved_python_version))
                if resolved_python_version
                else "unresolved",
                *expected_python,
            ),
        ),
        "cmake": _check(cmake_bin is not None, cmake_bin or "not found"),
        "ninja": _check(ninja_bin is not None, ninja_bin or "not found"),
        "conda_compiler": _check(
            compiler.is_file() and os.access(compiler, os.X_OK), str(compiler)
        ),
        "ccache": _check(
            ccache_bin is not None or not require_ccache,
            ccache_bin or "optional; not found",
        ),
    }
    return {
        "ok": all(bool(check["ok"]) for check in checks.values()),
        "conda_prefix": str(conda_prefix),
        "expected_jobs": expected_jobs,
        "expected_isis_major": expected_isis_major,
        "expected_python": ".".join(map(str, expected_python)),
        "checks": checks,
    }


def _python_minor(value: str) -> tuple[int, int]:
    try:
        major, minor = (int(part) for part in value.split(".", 1))
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("expected MAJOR.MINOR, for example 3.12") from exc
    return major, minor


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conda-prefix", required=True, type=Path)
    parser.add_argument("--expected-jobs", required=True, type=int)
    parser.add_argument("--expected-isis-major", required=True, type=int)
    parser.add_argument("--expected-python", required=True, type=_python_minor)
    parser.add_argument("--require-ccache", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.expected_jobs < 1 or args.expected_isis_major < 1:
        parser.error("expected jobs and ISIS major must be positive integers")

    report = inspect_host(
        args.conda_prefix,
        args.expected_jobs,
        args.expected_isis_major,
        args.expected_python,
        require_ccache=args.require_ccache,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for name, check in report["checks"].items():
            status = "PASS" if check["ok"] else "FAIL"
            print(f"[{status}] {name}: {check['detail']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
