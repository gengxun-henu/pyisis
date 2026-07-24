"""Runtime discovery helpers for pip-installed pyisis wheels."""

# Copyright (c) 2026 Geng Xun, Henan University
# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass
import importlib
import os
from os import PathLike
from pathlib import Path
import re
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
    isis_version: str | None


_ISIS_VERSION_RE = re.compile(r"^\s*(\d+)\.(\d+)\.(\d+)")


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


def read_isis_version(prefix: str | PathLike[str] | None) -> str | None:
    """Read the semantic ISIS version from a runtime prefix."""

    if prefix is None:
        return None
    version_file = Path(prefix) / "isis_version.txt"
    try:
        first_line = version_file.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, IndexError):
        return None
    match = _ISIS_VERSION_RE.match(first_line)
    if match is None:
        return None
    return ".".join(match.groups())


def validate_runtime_version(
    expected_version: str,
    expected_major: int,
    *,
    discovery: RuntimeDiscovery | None = None,
) -> str:
    """Reject a runtime prefix from another ISIS ABI major version."""

    runtime = discovery or configure_runtime(register_dll_directories=True)
    prefix = runtime.isis_prefix or runtime.isisroot
    actual_version = runtime.isis_version or read_isis_version(prefix)
    if actual_version is None:
        raise RuntimeError(
            "Unable to verify the ISIS runtime version because "
            f"{prefix or 'the selected prefix'} has no readable isis_version.txt. "
            f"PyISIS was built for ISIS {expected_version}."
        )
    actual_major = int(actual_version.split(".", 1)[0])
    if actual_major != expected_major:
        raise RuntimeError(
            f"PyISIS was built for ISIS {expected_version}, but the selected "
            f"runtime is ISIS {actual_version} at {prefix}. Use separate "
            "environments for the ISIS 9 and ISIS 10 package lines."
        )
    return actual_version


def _configure_packaged_runtime(runtime: Any | None) -> str | None:
    if runtime is None:
        return None
    if hasattr(runtime, "configure_environment"):
        configured_prefix = runtime.configure_environment()
        if configured_prefix is not None:
            return _path_text(configured_prefix)
    return _path_text(runtime.prefix()) if hasattr(runtime, "prefix") else None


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
        packaged_prefix = _configure_packaged_runtime(runtime)
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
        isis_version=read_isis_version(isis_prefix or isisroot),
    )


__all__ = [
    "RuntimeDiscovery",
    "configure_runtime",
    "read_isis_version",
    "validate_runtime_version",
]
