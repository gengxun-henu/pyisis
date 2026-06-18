"""High-level Python facade for the standalone ISIS pybind bindings."""

# Copyright (c) 2026 Geng Xun, Henan University
# SPDX-License-Identifier: MIT

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import importlib
import os
from os import PathLike
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator


_CORE_MODULE: ModuleType | None = None
_DLL_DIRECTORY_HANDLES: list[Any] = []
_REGISTERED_DLL_DIRECTORIES: set[str] = set()


class PyisisError(RuntimeError):
    """Raised when a high-level pyisis helper cannot complete its operation."""


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime environment paths used by ISIS and the pybind extension."""

    isis_prefix: str | None
    isisroot: str | None
    isisdata: str | None
    conda_prefix: str | None


@dataclass(frozen=True)
class IsisDataStatus:
    """Basic diagnostics for the configured ISISDATA tree."""

    path: str | None
    exists: bool
    has_leap_second_kernels: bool
    leap_second_kernels: tuple[str, ...]
    kernel_database_count: int
    usable_for_smoke_tests: bool
    message: str


@dataclass(frozen=True)
class CubeDimensions:
    """Sample, line, and band dimensions for an ISIS cube."""

    samples: int
    lines: int
    bands: int


@dataclass(frozen=True)
class GroundPoint:
    """Ground location derived from a camera image coordinate."""

    latitude: float
    longitude: float
    radius_meters: float | None = None


def _path_text(value: str | PathLike[str]) -> str:
    return os.fspath(value)


def _set_path_env(name: str, value: str | PathLike[str] | None) -> str | None:
    if value is None:
        return os.environ.get(name)
    text = _path_text(value)
    os.environ[name] = text
    return text


def _register_windows_dll_directories() -> None:
    if os.name != "nt":
        return

    for env_name in ("ISISROOT", "ISIS_PREFIX", "CONDA_PREFIX"):
        prefix_text = os.environ.get(env_name)
        if not prefix_text:
            continue
        prefix = Path(prefix_text)
        if not prefix.exists():
            continue
        for relative in ("Library/bin", "Library/lib", "bin", "lib"):
            dll_dir = prefix / relative
            key = str(dll_dir).lower()
            if key in _REGISTERED_DLL_DIRECTORIES or not dll_dir.exists():
                continue
            try:
                handle = os.add_dll_directory(str(dll_dir))
            except OSError:
                continue
            _REGISTERED_DLL_DIRECTORIES.add(key)
            _DLL_DIRECTORY_HANDLES.append(handle)


def configure(
    *,
    isis_prefix: str | PathLike[str] | None = None,
    isisroot: str | PathLike[str] | None = None,
    isisdata: str | PathLike[str] | None = None,
    conda_prefix: str | PathLike[str] | None = None,
) -> RuntimeConfig:
    """Configure the process environment used by ISIS and the pybind module."""

    resolved_isis_prefix = _set_path_env("ISIS_PREFIX", isis_prefix)
    if isisroot is None and resolved_isis_prefix:
        isisroot = resolved_isis_prefix
    resolved_isisroot = _set_path_env("ISISROOT", isisroot)
    resolved_isisdata = _set_path_env("ISISDATA", isisdata)
    resolved_conda_prefix = _set_path_env("CONDA_PREFIX", conda_prefix)

    _register_windows_dll_directories()

    return RuntimeConfig(
        isis_prefix=resolved_isis_prefix,
        isisroot=resolved_isisroot,
        isisdata=resolved_isisdata,
        conda_prefix=resolved_conda_prefix,
    )


def _leap_second_kernel_names(data_root: Path) -> tuple[str, ...]:
    lsk_dir = data_root / "base" / "kernels" / "lsk"
    if not lsk_dir.is_dir():
        return ()

    names = [
        child.name
        for child in lsk_dir.iterdir()
        if child.is_file()
        and child.name.lower().startswith("naif")
        and child.name.lower().endswith(".tls")
    ]
    return tuple(sorted(names, key=str.lower))


def _kernel_database_count(data_root: Path) -> int:
    return sum(
        1
        for child in data_root.rglob("*")
        if child.is_file()
        and child.name.lower().startswith("kernels.")
        and child.suffix.lower() == ".db"
    )


def data_status(isisdata: str | PathLike[str] | None = None) -> IsisDataStatus:
    """Return lightweight diagnostics for an ISISDATA directory."""

    path_text = _path_text(isisdata) if isisdata is not None else os.environ.get("ISISDATA")
    if not path_text:
        return IsisDataStatus(
            path=None,
            exists=False,
            has_leap_second_kernels=False,
            leap_second_kernels=(),
            kernel_database_count=0,
            usable_for_smoke_tests=False,
            message="ISISDATA is not configured; set ISISDATA or install pyisis-isisdata-minimal.",
        )

    data_root = Path(path_text).expanduser()
    normalized_path = str(data_root)
    if not data_root.exists():
        return IsisDataStatus(
            path=normalized_path,
            exists=False,
            has_leap_second_kernels=False,
            leap_second_kernels=(),
            kernel_database_count=0,
            usable_for_smoke_tests=False,
            message=f"ISISDATA path does not exist: {normalized_path}",
        )

    leap_second_kernels = _leap_second_kernel_names(data_root)
    kernel_database_count = _kernel_database_count(data_root)
    has_leap_second_kernels = bool(leap_second_kernels)
    if not has_leap_second_kernels:
        return IsisDataStatus(
            path=normalized_path,
            exists=True,
            has_leap_second_kernels=False,
            leap_second_kernels=(),
            kernel_database_count=kernel_database_count,
            usable_for_smoke_tests=False,
            message=(
                "ISISDATA exists, but no leap-second kernels were found under "
                "base/kernels/lsk."
            ),
        )

    return IsisDataStatus(
        path=normalized_path,
        exists=True,
        has_leap_second_kernels=True,
        leap_second_kernels=leap_second_kernels,
        kernel_database_count=kernel_database_count,
        usable_for_smoke_tests=True,
        message=(
            f"ISISDATA is usable for pyisis smoke tests: {normalized_path} "
            f"({len(leap_second_kernels)} leap-second kernels, "
            f"{kernel_database_count} kernel database files)."
        ),
    )


def core() -> ModuleType:
    """Return the low-level `isis_pybind` module, importing it lazily."""

    global _CORE_MODULE
    if _CORE_MODULE is None:
        _register_windows_dll_directories()
        _CORE_MODULE = importlib.import_module("isis_pybind")
    return _CORE_MODULE


class CubeSession:
    """Context manager that opens an ISIS cube and closes it on exit."""

    def __init__(self, path: str | PathLike[str], access: str = "r") -> None:
        self.path = _path_text(path)
        self.access = access
        self._cube: Any | None = None

    def __enter__(self) -> Any:
        if self._cube is None:
            cube = core().Cube()
            cube.open(self.path, self.access)
            self._cube = cube
        return self._cube

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        self.close()
        return False

    def close(self) -> None:
        if self._cube is None:
            return
        cube = self._cube
        self._cube = None
        cube.close()


def open_cube(path: str | PathLike[str], access: str = "r") -> CubeSession:
    """Open an ISIS cube as a context manager."""

    return CubeSession(path, access)


@contextmanager
def _cube_context(cube_or_path: Any) -> Iterator[Any]:
    ip = core()
    if isinstance(cube_or_path, ip.Cube):
        yield cube_or_path
        return

    with open_cube(cube_or_path) as cube:
        yield cube


@contextmanager
def _camera_context(cube_camera_or_path: Any) -> Iterator[Any]:
    ip = core()
    if isinstance(cube_camera_or_path, ip.Camera):
        yield cube_camera_or_path
        return
    if isinstance(cube_camera_or_path, ip.Cube):
        yield cube_camera_or_path.camera()
        return

    with open_cube(cube_camera_or_path) as cube:
        yield cube.camera()


def cube_dimensions(cube_or_path: Any) -> CubeDimensions:
    """Return dimensions for an open cube or cube file path."""

    with _cube_context(cube_or_path) as cube:
        return CubeDimensions(
            samples=int(cube.sample_count()),
            lines=int(cube.line_count()),
            bands=int(cube.band_count()),
        )


def ground_at(cube_camera_or_path: Any, sample: float, line: float) -> GroundPoint:
    """Return camera ground coordinates at a sample/line image position."""

    with _camera_context(cube_camera_or_path) as camera:
        if not camera.set_image(float(sample), float(line)):
            raise PyisisError(f"camera.set_image({sample}, {line}) failed")

        radius_meters = None
        if camera.has_surface_intersection():
            surface_point = camera.get_surface_point()
            if surface_point.valid():
                radius_meters = float(surface_point.get_local_radius().meters())

        return GroundPoint(
            latitude=float(camera.universal_latitude()),
            longitude=float(camera.universal_longitude()),
            radius_meters=radius_meters,
        )


def ground_at_center(cube_camera_or_path: Any) -> GroundPoint:
    """Return camera ground coordinates at the center of a cube or camera."""

    with _camera_context(cube_camera_or_path) as camera:
        return ground_at(
            camera,
            sample=float(camera.samples()) / 2.0,
            line=float(camera.lines()) / 2.0,
        )


def __getattr__(name: str) -> Any:
    return getattr(core(), name)


def __dir__() -> list[str]:
    names = set(globals())
    if _CORE_MODULE is not None:
        names.update(dir(_CORE_MODULE))
    return sorted(names)


__all__ = [
    "CubeDimensions",
    "CubeSession",
    "GroundPoint",
    "IsisDataStatus",
    "PyisisError",
    "RuntimeConfig",
    "configure",
    "core",
    "cube_dimensions",
    "data_status",
    "ground_at",
    "ground_at_center",
    "open_cube",
]
