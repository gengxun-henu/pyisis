"""Runtime discovery helpers for pip-installed pyisis wheels."""

# Copyright (c) 2026 Geng Xun, Henan University
# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass
import importlib
import os
from os import PathLike
from pathlib import Path
from typing import Any


_DLL_DIRECTORY_HANDLES: list[Any] = []
_REGISTERED_DLL_DIRECTORIES: set[str] = set()


@dataclass(frozen=True)
class RuntimeDiscovery:
    """Runtime paths discovered from environment variables or pip packages."""

    isis_prefix: str | None
    isisroot: str | None
    isisdata: str | None
    dll_directories: tuple[str, ...]


def _path_text(value: str | PathLike[str]) -> str:
    return os.fspath(value)


def _setdefault_path_env(name: str, value: str | PathLike[str] | None) -> str | None:
    existing = os.environ.get(name)
    if existing:
        return existing
    if value is None:
        return None
    text = _path_text(value)
    os.environ[name] = text
    return text


def _runtime_module():
    try:
        return importlib.import_module("pyisis_runtime")
    except ImportError:
        return None


def _minimal_data_path() -> str | None:
    try:
        data_module = importlib.import_module("pyisis_isisdata_minimal")
    except ImportError:
        return None
    return _path_text(data_module.data_path())


def _candidate_dll_directories(prefix_text: str | None) -> list[str]:
    if not prefix_text:
        return []

    prefix = Path(prefix_text)
    return [
        str(path)
        for path in (
            prefix / "Library" / "bin",
            prefix / "Library" / "lib",
            prefix / "bin",
            prefix / "lib",
        )
        if path.exists()
    ]


def _register_windows_dll_directories(paths: list[str]) -> None:
    if os.name != "nt":
        return

    for path_text in paths:
        key = os.path.normcase(os.path.normpath(path_text))
        if key in _REGISTERED_DLL_DIRECTORIES:
            continue
        try:
            handle = os.add_dll_directory(path_text)
        except OSError:
            continue
        _REGISTERED_DLL_DIRECTORIES.add(key)
        _DLL_DIRECTORY_HANDLES.append(handle)


def configure_runtime(*, register_dll_directories: bool = True) -> RuntimeDiscovery:
    """Configure environment variables and DLL lookup for the best available runtime."""

    explicit_prefix = os.environ.get("ISIS_PREFIX") or os.environ.get("ISISROOT")
    runtime = None
    packaged_prefix = None
    if explicit_prefix is None:
        runtime = _runtime_module()
        packaged_prefix = (
            _path_text(runtime.prefix()) if runtime and hasattr(runtime, "prefix") else None
        )
    prefix_candidate = explicit_prefix or packaged_prefix

    isis_prefix = _setdefault_path_env("ISIS_PREFIX", prefix_candidate)
    isisroot = _setdefault_path_env("ISISROOT", isis_prefix or prefix_candidate)
    minimal_data = None if os.environ.get("ISISDATA") else _minimal_data_path()
    isisdata = _setdefault_path_env("ISISDATA", minimal_data)

    dll_directories = []
    if runtime and hasattr(runtime, "dll_directories"):
        dll_directories.extend(_path_text(path) for path in runtime.dll_directories())

    for prefix_text in (isis_prefix, isisroot, os.environ.get("CONDA_PREFIX")):
        dll_directories.extend(_candidate_dll_directories(prefix_text))

    deduped_dll_directories = tuple(dict.fromkeys(dll_directories))
    if register_dll_directories:
        _register_windows_dll_directories(list(deduped_dll_directories))

    return RuntimeDiscovery(
        isis_prefix=isis_prefix,
        isisroot=isisroot,
        isisdata=isisdata,
        dll_directories=deduped_dll_directories,
    )


__all__ = ["RuntimeDiscovery", "configure_runtime"]
