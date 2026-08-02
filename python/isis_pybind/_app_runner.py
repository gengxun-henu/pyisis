"""Private helpers for running native ISIS applications without a shell."""

# Copyright (c) 2026 Geng Xun, Henan University
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import Sequence


def _executable_name(app_name: str) -> str:
    return f"{app_name}.exe" if os.name == "nt" else app_name


def _find_isis_app_executable(app_name: str) -> str:
    if not app_name or not app_name.replace("_", "").isalnum():
        raise ValueError(
            "ISIS application name must be alphanumeric or underscore"
        )

    executable_name = _executable_name(app_name)
    for variable in ("ISIS_PREFIX", "ISISROOT", "CONDA_PREFIX"):
        prefix = os.environ.get(variable)
        if not prefix:
            continue
        for relative in (("bin",), ("Library", "bin")):
            candidate = Path(prefix).joinpath(*relative, executable_name)
            if candidate.is_file():
                return str(candidate)

    resolved = shutil.which(executable_name)
    if resolved:
        return resolved
    raise FileNotFoundError(
        f"ISIS application executable not found: {executable_name}"
    )


def _run_isis_app(app_name: str, arguments: Sequence[str]) -> None:
    executable = _find_isis_app_executable(app_name)
    completed = subprocess.run(
        [executable, *arguments],
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )
    if completed.returncode == 0:
        return

    diagnostic = completed.stderr.strip() or completed.stdout.strip()
    message = (
        f"ISIS application {app_name} failed with exit code "
        f"{completed.returncode}"
    )
    if diagnostic:
        message += f": {diagnostic}"
    raise RuntimeError(message)
