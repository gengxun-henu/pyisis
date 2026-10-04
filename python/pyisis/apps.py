"""Safe subprocess launcher for native ISIS applications."""

# Copyright (c) 2026 Geng Xun, Henan University
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
from os import PathLike
import subprocess
from typing import Mapping, Sequence


def run(
    name: str | PathLike[str],
    *args: str | PathLike[str],
    env: Mapping[str, str | PathLike[str]] | None = None,
    cwd: str | PathLike[str] | None = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a native ISIS application without shell argument interpolation."""

    command = [os.fspath(name), *(os.fspath(arg) for arg in args)]
    process_env = os.environ.copy()
    if env is not None:
        process_env.update({key: os.fspath(value) for key, value in env.items()})

    result = subprocess.run(
        command,
        cwd=None if cwd is None else os.fspath(cwd),
        env=process_env,
        check=False,
        capture_output=capture_output,
        text=True,
    )
    if check and result.returncode:
        from . import PyisisError

        detail = (result.stderr or "").strip()
        suffix = f": {detail}" if detail else ""
        raise PyisisError(
            f"ISIS application {command[0]!r} exited with exit code "
            f"{result.returncode}{suffix}"
        )
    return result


__all__ = ["run"]
