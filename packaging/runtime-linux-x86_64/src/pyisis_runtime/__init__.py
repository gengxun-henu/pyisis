"""Linux x86_64 runtime package for usgs-pyisis."""

# Copyright (c) 2026 Geng Xun, Henan University
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
from pathlib import Path


def prefix() -> Path:
    """Return the packaged ISIS runtime prefix."""

    return Path(__file__).resolve().parent / "vendor" / "isis"


def dll_directories() -> list[Path]:
    """Return existing shared-library search directories for the packaged runtime."""

    root = prefix()
    return [
        path
        for path in (
            root / "lib",
            root / "lib64",
            root / "bin",
        )
        if path.exists()
    ]


def plugin_directories() -> list[Path]:
    """Return existing Qt plugin directories for the packaged runtime."""

    root = prefix()
    return [
        path
        for path in (
            root / "plugins",
            root / "lib" / "qt5" / "plugins",
            root / "lib" / "qt6" / "plugins",
            root / "lib64" / "qt5" / "plugins",
            root / "lib64" / "qt6" / "plugins",
        )
        if path.exists()
    ]


def _prepend_env_paths(name: str, paths: list[Path]) -> None:
    path_texts = [str(path) for path in paths]
    if not path_texts:
        return

    existing_parts = [
        part
        for part in os.environ.get(name, "").split(os.pathsep)
        if part and part not in path_texts
    ]
    os.environ[name] = os.pathsep.join(path_texts + existing_parts)


def configure_environment() -> Path:
    """Set ISIS runtime environment variables for the packaged runtime."""

    root = prefix()
    os.environ.setdefault("ISIS_PREFIX", str(root))
    os.environ.setdefault("ISISROOT", str(root))
    _prepend_env_paths("QT_PLUGIN_PATH", plugin_directories())
    _prepend_env_paths("LD_LIBRARY_PATH", dll_directories())
    return root


__all__ = ["configure_environment", "dll_directories", "plugin_directories", "prefix"]
