"""Windows x64 runtime package for usgs-pyisis."""

# Copyright (c) 2026 Geng Xun, Henan University
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


_DLL_HANDLES: list[Any] = []
_REGISTERED_DLL_DIRECTORIES: set[str] = set()


def prefix() -> Path:
    """Return the packaged ISIS runtime prefix."""

    return Path(__file__).resolve().parent / "vendor" / "isis"


def dll_directories() -> list[Path]:
    """Return existing Windows DLL search directories for the packaged runtime."""

    root = prefix()
    return [
        path
        for path in (
            root / "Library" / "bin",
            root / "Library" / "lib",
            root / "bin",
            root / "lib",
        )
        if path.exists()
    ]


def configure_environment() -> Path:
    """Set ISIS runtime environment variables and register DLL directories."""

    root = prefix()
    os.environ.setdefault("ISIS_PREFIX", str(root))
    os.environ.setdefault("ISISROOT", str(root))
    if os.name == "nt":
        for dll_dir in dll_directories():
            key = os.path.normcase(os.path.normpath(str(dll_dir)))
            if key in _REGISTERED_DLL_DIRECTORIES:
                continue
            _DLL_HANDLES.append(os.add_dll_directory(str(dll_dir)))
            _REGISTERED_DLL_DIRECTORIES.add(key)
    return root


__all__ = ["configure_environment", "dll_directories", "prefix"]
