# Pip Wheel Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make pyisis installable with `pip install pyisis` by producing prebuilt wheels that can import `pyisis` and `isis_pybind._isis_core` without a user-managed conda ISIS environment.

**Architecture:** Add a scikit-build-core based `pyproject.toml` for the main CMake/pybind package, split the Windows ISIS runtime into a platform wheel named `pyisis-runtime-win64`, and package the existing mock ISISDATA tree as `pyisis-isisdata-minimal`. The main package discovers the runtime and data packages at import time, configures `ISISROOT`/`ISIS_PREFIX`/`ISISDATA`, and registers Windows DLL directories before `_isis_core` is imported.

**Tech Stack:** Python packaging standards, scikit-build-core, CMake, pybind11, PowerShell, Python `unittest`, cibuildwheel, delvewheel, twine

---

## File Structure

| Action | File | Responsibility |
| --- | --- | --- |
| Create | `pyproject.toml` | Main `pyisis` wheel metadata and scikit-build-core configuration. |
| Modify | `CMakeLists.txt` | Make CMake install into scikit-build-core wheel staging dirs when `SKBUILD` is active. |
| Create | `python/pyisis/_runtime.py` | Runtime discovery and environment setup shared by `pyisis` and `isis_pybind`. |
| Modify | `python/pyisis/__init__.py` | Re-export runtime helpers and use them before lazy core import. |
| Modify | `python/isis_pybind/__init__.py` | Configure packaged runtime before importing `_isis_core` directly. |
| Create | `packaging/runtime-win64/README.md` | Document the Windows runtime wheel contract and staging inputs. |
| Create | `packaging/runtime-win64/pyproject.toml` | Template metadata for the `pyisis-runtime-win64` wheel. |
| Create | `packaging/runtime-win64/src/pyisis_runtime/__init__.py` | Runtime package API: `prefix()`, `dll_directories()`, and `configure_environment()`. |
| Create | `packaging/isisdata-minimal/README.md` | Document the minimal ISISDATA wheel and its smoke-test purpose. |
| Create | `packaging/isisdata-minimal/pyproject.toml` | Pure Python/data wheel metadata for `pyisis-isisdata-minimal`. |
| Create | `packaging/isisdata-minimal/src/pyisis_isisdata_minimal/__init__.py` | Data package API exposing `data_path()`. |
| Create | `tools/packaging/stage_runtime_win64.py` | Copy a verified Windows ISIS prefix into a generated runtime wheel build tree. |
| Create | `tools/packaging/build_wheels.ps1` | Local Windows wheel build harness for main, runtime, and data wheels. |
| Create | `tools/packaging/test_wheel_install.py` | Clean venv smoke verification for installed wheels. |
| Create | `tests/unitTest/python_packaging_unit_test.py` | Metadata and scikit-build configuration tests. |
| Create | `tests/unitTest/pyisis_runtime_unit_test.py` | Runtime discovery tests without requiring real Windows DLLs. |
| Create | `tests/unitTest/runtime_wheel_script_unit_test.py` | Runtime staging script tests using a fake ISIS prefix. |
| Create | `.github/workflows/wheels.yml` | Build and smoke-test Windows wheels in CI after local flow is proven. |
| Modify | `README.md` | Add user-facing pip install notes and packaging limitations. |

---

## Task 1: Add Packaging Metadata Tests

**Files:**
- Create: `tests/unitTest/python_packaging_unit_test.py`
- Create later: `pyproject.toml`

- [ ] **Step 1: Write the failing metadata tests**

Create `tests/unitTest/python_packaging_unit_test.py` with this content:

```python
"""Unit tests for pip wheel packaging metadata.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-06-18
Updated: 2026-06-18  Geng Xun added packaging metadata coverage for pip wheels.
"""

from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = PROJECT_ROOT / "pyproject.toml"


class PythonPackagingUnitTest(unittest.TestCase):
    """Test suite for Python wheel packaging metadata."""

    def _pyproject(self):
        self.assertTrue(PYPROJECT.is_file(), f"Missing packaging metadata: {PYPROJECT}")
        return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    def test_main_package_uses_scikit_build_core(self):
        config = self._pyproject()

        build_system = config["build-system"]
        self.assertEqual(build_system["build-backend"], "scikit_build_core.build")
        self.assertTrue(
            any(requirement.startswith("scikit-build-core") for requirement in build_system["requires"])
        )
        self.assertTrue(any(requirement.startswith("pybind11") for requirement in build_system["requires"]))

    def test_project_metadata_declares_pyisis_distribution(self):
        config = self._pyproject()
        project = config["project"]

        self.assertEqual(project["name"], "pyisis")
        self.assertEqual(project["version"], "1.2.0")
        self.assertIn("README.md", project["readme"])
        self.assertIn(">=3.10", project["requires-python"])

    def test_project_depends_on_platform_runtime_and_minimal_data(self):
        dependencies = self._pyproject()["project"]["dependencies"]

        self.assertIn(
            'pyisis-runtime-win64==1.2.0; platform_system == "Windows" and platform_machine == "AMD64"',
            dependencies,
        )
        self.assertIn("pyisis-isisdata-minimal==1.2.0", dependencies)

    def test_scikit_build_installs_from_cmake_only(self):
        tool = self._pyproject()["tool"]["scikit-build"]

        self.assertEqual(tool["minimum-version"], "build-system.requires")
        self.assertEqual(tool["wheel"]["packages"], [])
        self.assertTrue(tool["wheel"]["platlib"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing metadata tests**

Run:

```powershell
python -m unittest tests.unitTest.python_packaging_unit_test -v
```

Expected: FAIL because `pyproject.toml` does not exist yet.

- [ ] **Step 3: Add the main package `pyproject.toml`**

Create `pyproject.toml` with this content:

```toml
[build-system]
requires = [
  "scikit-build-core>=0.11",
  "pybind11>=2.11",
]
build-backend = "scikit_build_core.build"

[project]
name = "pyisis"
version = "1.2.0"
description = "Standalone pybind11 bindings and a Python facade for selected USGS ISIS APIs."
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
authors = [
  { name = "Geng Xun" },
]
classifiers = [
  "Development Status :: 3 - Alpha",
  "Intended Audience :: Science/Research",
  "Programming Language :: C++",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Topic :: Scientific/Engineering",
]
dependencies = [
  'pyisis-runtime-win64==1.2.0; platform_system == "Windows" and platform_machine == "AMD64"',
  "pyisis-isisdata-minimal==1.2.0",
]

[project.urls]
Homepage = "https://github.com/guderianXu/pyisis"
Source = "https://github.com/guderianXu/pyisis"

[tool.scikit-build]
minimum-version = "build-system.requires"
build-dir = "build/{wheel_tag}"
wheel.packages = []
wheel.platlib = true
wheel.license-files = ["LICENSE"]

[tool.scikit-build.cmake.define]
PYISIS_BUILD_BENCHMARKS = "OFF"
ISIS_EXCLUDE_ASP_VW_CAMERA_LIBS = "ON"

[tool.cibuildwheel]
build = "cp312-win_amd64"
test-command = "python -c \"import pyisis; import isis_pybind; print(pyisis.data_status().message)\""
```

- [ ] **Step 4: Run metadata tests again**

Run:

```powershell
python -m unittest tests.unitTest.python_packaging_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add pyproject.toml tests/unitTest/python_packaging_unit_test.py
git commit -m "test: add pip packaging metadata coverage"
```

---

## Task 2: Make CMake Wheel-Staging Aware

**Files:**
- Modify: `CMakeLists.txt`
- Modify: `tests/unitTest/python_packaging_unit_test.py`

- [ ] **Step 1: Add failing CMake install tests**

Append these test methods to `PythonPackagingUnitTest` in `tests/unitTest/python_packaging_unit_test.py`:

```python
    def test_cmake_uses_development_module_for_extension_builds(self):
        cmake_lists = (PROJECT_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")

        self.assertIn("find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)", cmake_lists)
        self.assertNotIn("find_package(Python3 REQUIRED COMPONENTS Interpreter Development)", cmake_lists)

    def test_cmake_honors_scikit_build_wheel_staging_paths(self):
        cmake_lists = (PROJECT_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")

        self.assertIn("if(SKBUILD)", cmake_lists)
        self.assertIn('set(PYISIS_INSTALL_SITELIB ".")', cmake_lists)
        self.assertIn('set(PYISIS_INSTALL_SITEARCH ".")', cmake_lists)
        self.assertIn(
            'set(PYISIS_INSTALL_SITELIB "${PYISIS_DEFAULT_SITELIB}" CACHE PATH',
            cmake_lists,
        )
        self.assertIn(
            'set(PYISIS_INSTALL_SITEARCH "${PYISIS_DEFAULT_SITEARCH}" CACHE PATH',
            cmake_lists,
        )
```

- [ ] **Step 2: Run the failing CMake packaging tests**

Run:

```powershell
python -m unittest tests.unitTest.python_packaging_unit_test -v
```

Expected: FAIL because `CMakeLists.txt` still uses `Development` and absolute Python install dirs by default.

- [ ] **Step 3: Use Python extension-only development headers**

Change the existing Python package discovery line in `CMakeLists.txt` from:

```cmake
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)
```

to:

```cmake
find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
```

- [ ] **Step 4: Add a benchmark build option**

Wrap the benchmark target in `CMakeLists.txt` with an option so pip wheels do not compile unrelated tools:

```cmake
option(PYISIS_BUILD_BENCHMARKS "Build pyisis developer benchmark executables" ON)
```

Then surround the `add_executable(isis_cpp_benchmark ...)` block and its target properties with:

```cmake
if(PYISIS_BUILD_BENCHMARKS)
  add_executable(isis_cpp_benchmark
    tools/benchmarks/isis_cpp_benchmark.cpp)

  # Keep the existing include, link, and RPATH logic inside this block.
endif()
```

- [ ] **Step 5: Teach install paths about scikit-build-core**

Replace the current `Python3_SITELIB` / `Python3_SITEARCH` default block in `CMakeLists.txt` with:

```cmake
if(SKBUILD)
  set(PYISIS_INSTALL_SITELIB ".")
  set(PYISIS_INSTALL_SITEARCH ".")
else()
  if(NOT Python3_SITELIB)
    execute_process(
      COMMAND "${Python3_EXECUTABLE}" -c "import sysconfig; print(sysconfig.get_path('purelib'))"
      OUTPUT_VARIABLE Python3_SITELIB
      OUTPUT_STRIP_TRAILING_WHITESPACE)
  endif()

  if(NOT Python3_SITEARCH)
    execute_process(
      COMMAND "${Python3_EXECUTABLE}" -c "import sysconfig; print(sysconfig.get_path('platlib'))"
      OUTPUT_VARIABLE Python3_SITEARCH
      OUTPUT_STRIP_TRAILING_WHITESPACE)
  endif()

  set(PYISIS_DEFAULT_SITELIB "${Python3_SITELIB}")
  set(PYISIS_DEFAULT_SITEARCH "${Python3_SITEARCH}")
  set(PYISIS_INSTALL_SITELIB "${PYISIS_DEFAULT_SITELIB}" CACHE PATH
    "Python purelib install directory for the pyisis facade package")
  set(PYISIS_INSTALL_SITEARCH "${PYISIS_DEFAULT_SITEARCH}" CACHE PATH
    "Python platlib install directory for the compiled isis_pybind package")
endif()
```

- [ ] **Step 6: Run the focused tests**

Run:

```powershell
python -m unittest tests.unitTest.python_packaging_unit_test -v
```

Expected: PASS.

- [ ] **Step 7: Run a local configure smoke check**

Run from a shell with the existing Windows environment:

```powershell
$env:ISIS_PREFIX = "$PWD\build\windows\isis-prefix"
$env:ISISROOT = $env:ISIS_PREFIX
$env:PYISIS_DEP_PREFIX = "E:\code\pyisis-win-env"
python -m pip install -U build scikit-build-core pybind11
python -m build --wheel --no-isolation --skip-dependency-check
```

Expected: a `dist\pyisis-1.2.0-*.whl` is produced. `--skip-dependency-check`
keeps `python -m build --no-isolation` from requiring Python `cmake` and
`ninja` wheels when the active conda environment already supplies the
executables. If this fails before linking, fix CMake install or dependency
discovery before moving on.

- [ ] **Step 8: Commit**

Run:

```powershell
git add CMakeLists.txt tests/unitTest/python_packaging_unit_test.py pyproject.toml
git commit -m "build: add scikit-build wheel packaging"
```

---

## Task 3: Add Runtime Discovery Inside Python

**Files:**
- Create: `python/pyisis/_runtime.py`
- Modify: `python/pyisis/__init__.py`
- Modify: `python/isis_pybind/__init__.py`
- Create: `tests/unitTest/pyisis_runtime_unit_test.py`

- [ ] **Step 1: Write failing runtime discovery tests**

Create `tests/unitTest/pyisis_runtime_unit_test.py` with this content:

```python
"""Unit tests for pyisis pip runtime discovery.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-06-18
Updated: 2026-06-18  Geng Xun added runtime package discovery coverage for pip wheels.
"""

from __future__ import annotations

from pathlib import Path
import os
import sys
from types import ModuleType
from unittest import mock
import unittest


class PyisisRuntimeUnitTest(unittest.TestCase):
    """Test suite for packaged runtime discovery."""

    def tearDown(self):
        sys.modules.pop("pyisis_runtime", None)
        sys.modules.pop("pyisis_isisdata_minimal", None)

    def test_configure_runtime_prefers_existing_environment(self):
        from pyisis._runtime import configure_runtime

        with mock.patch.dict(os.environ, {"ISIS_PREFIX": r"C:\external\isis"}, clear=True):
            config = configure_runtime(register_dll_directories=False)

        self.assertEqual(config.isis_prefix, r"C:\external\isis")
        self.assertEqual(config.isisroot, r"C:\external\isis")

    def test_configure_runtime_uses_packaged_runtime_when_environment_is_missing(self):
        fake_runtime = ModuleType("pyisis_runtime")
        fake_runtime.prefix = lambda: r"C:\venv\Lib\site-packages\pyisis_runtime\vendor\isis"
        fake_runtime.dll_directories = lambda: [
            r"C:\venv\Lib\site-packages\pyisis_runtime\vendor\isis\bin",
        ]
        sys.modules["pyisis_runtime"] = fake_runtime

        from pyisis._runtime import configure_runtime

        with mock.patch.dict(os.environ, {}, clear=True):
            config = configure_runtime(register_dll_directories=False)

        self.assertEqual(os.environ["ISIS_PREFIX"], fake_runtime.prefix())
        self.assertEqual(os.environ["ISISROOT"], fake_runtime.prefix())
        self.assertEqual(config.isis_prefix, fake_runtime.prefix())
        self.assertEqual(
            config.dll_directories,
            (r"C:\venv\Lib\site-packages\pyisis_runtime\vendor\isis\bin",),
        )

    def test_configure_runtime_uses_minimal_data_package_when_isisdata_is_missing(self):
        fake_data = ModuleType("pyisis_isisdata_minimal")
        fake_data.data_path = lambda: Path(r"C:\venv\Lib\site-packages\pyisis_isisdata_minimal\data")
        sys.modules["pyisis_isisdata_minimal"] = fake_data

        from pyisis._runtime import configure_runtime

        with mock.patch.dict(os.environ, {}, clear=True):
            config = configure_runtime(register_dll_directories=False)

        self.assertEqual(os.environ["ISISDATA"], str(fake_data.data_path()))
        self.assertEqual(config.isisdata, str(fake_data.data_path()))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing runtime discovery tests**

Run:

```powershell
python -m unittest tests.unitTest.pyisis_runtime_unit_test -v
```

Expected: FAIL because `python/pyisis/_runtime.py` does not exist.

- [ ] **Step 3: Add the shared runtime helper**

Create `python/pyisis/_runtime.py` with this content:

```python
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
        key = path_text.lower()
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

    runtime = _runtime_module()
    packaged_prefix = _path_text(runtime.prefix()) if runtime and hasattr(runtime, "prefix") else None

    isis_prefix = _setdefault_path_env("ISIS_PREFIX", packaged_prefix)
    isisroot = _setdefault_path_env("ISISROOT", isis_prefix)
    isisdata = _setdefault_path_env("ISISDATA", _minimal_data_path())

    dll_directories = []
    if runtime and hasattr(runtime, "dll_directories"):
        dll_directories.extend(_path_text(path) for path in runtime.dll_directories())
    dll_directories.extend(_candidate_dll_directories(isis_prefix))

    deduped_dll_directories = tuple(dict.fromkeys(dll_directories))
    if register_dll_directories:
        _register_windows_dll_directories(list(deduped_dll_directories))

    return RuntimeDiscovery(
        isis_prefix=isis_prefix,
        isisroot=isisroot,
        isisdata=isisdata,
        dll_directories=deduped_dll_directories,
    )
```

- [ ] **Step 4: Wire `pyisis` facade to the helper**

Modify `python/pyisis/__init__.py`:

```python
from ._runtime import RuntimeDiscovery, configure_runtime
```

Then replace the body of `_register_windows_dll_directories()` with:

```python
    configure_runtime(register_dll_directories=True)
```

Add these names to `__all__`:

```python
    "RuntimeDiscovery",
    "configure_runtime",
```

- [ ] **Step 5: Wire direct `isis_pybind` imports to the helper**

In `python/isis_pybind/__init__.py`, replace the existing Windows-only runtime configuration block with:

```python
try:
    from pyisis._runtime import configure_runtime as _configure_pyisis_runtime
except ImportError:
    _configure_pyisis_runtime = None

if _configure_pyisis_runtime is not None:
    _configure_pyisis_runtime()
```

Keep the `from ._isis_core import (...)` section after this block.

- [ ] **Step 6: Run runtime discovery tests**

Run:

```powershell
python -m unittest tests.unitTest.pyisis_runtime_unit_test -v
python -m unittest tests.unitTest.pyisis_facade_unit_test -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add python/pyisis/_runtime.py python/pyisis/__init__.py python/isis_pybind/__init__.py tests/unitTest/pyisis_runtime_unit_test.py
git commit -m "feat: discover packaged pyisis runtime"
```

---

## Task 4: Add Minimal ISISDATA Pip Package

**Files:**
- Create: `packaging/isisdata-minimal/README.md`
- Create: `packaging/isisdata-minimal/pyproject.toml`
- Create: `packaging/isisdata-minimal/src/pyisis_isisdata_minimal/__init__.py`
- Modify: `tests/unitTest/python_packaging_unit_test.py`

- [ ] **Step 1: Add failing minimal data package metadata tests**

Append this method to `PythonPackagingUnitTest`:

```python
    def test_minimal_isisdata_package_metadata_exists(self):
        data_pyproject = PROJECT_ROOT / "packaging" / "isisdata-minimal" / "pyproject.toml"
        self.assertTrue(data_pyproject.is_file())

        config = tomllib.loads(data_pyproject.read_text(encoding="utf-8"))
        self.assertEqual(config["project"]["name"], "pyisis-isisdata-minimal")
        self.assertEqual(config["project"]["version"], "1.2.0")
        self.assertIn("tests/data/isisdata/mockup", str(config["tool"]["setuptools"]["package-data"]))
```

- [ ] **Step 2: Run the failing data package test**

Run:

```powershell
python -m unittest tests.unitTest.python_packaging_unit_test -v
```

Expected: FAIL because `packaging/isisdata-minimal/pyproject.toml` does not exist.

- [ ] **Step 3: Add the minimal data package README**

Create `packaging/isisdata-minimal/README.md`:

```markdown
# pyisis-isisdata-minimal

This package contains the small ISISDATA mockup tree used by pyisis smoke tests.
It is not a replacement for production USGS ISISDATA.

The package exposes:

```python
import pyisis_isisdata_minimal
print(pyisis_isisdata_minimal.data_path())
```
```

- [ ] **Step 4: Add the minimal data package metadata**

Create `packaging/isisdata-minimal/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "pyisis-isisdata-minimal"
version = "1.2.0"
description = "Minimal ISISDATA tree for pyisis smoke tests."
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"

[tool.setuptools]
package-dir = { "" = "src" }
packages = ["pyisis_isisdata_minimal"]
include-package-data = false

[tool.setuptools.package-data]
pyisis_isisdata_minimal = ["data/**/*"]
```

- [ ] **Step 5: Add the minimal data package module**

Create `packaging/isisdata-minimal/src/pyisis_isisdata_minimal/__init__.py`:

```python
"""Minimal ISISDATA package for pyisis smoke tests."""

# Copyright (c) 2026 Geng Xun, Henan University
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path


def data_path() -> Path:
    """Return the packaged minimal ISISDATA root."""

    return Path(__file__).resolve().parent / "data"


__all__ = ["data_path"]
```

- [ ] **Step 6: Add the data staging command to the local build flow**

The implementation worker should copy the existing mockup data into the package source tree before building:

```powershell
$dataTarget = "packaging\isisdata-minimal\src\pyisis_isisdata_minimal\data"
if (Test-Path $dataTarget) { Remove-Item -LiteralPath $dataTarget -Recurse -Force }
Copy-Item -LiteralPath "tests\data\isisdata\mockup" -Destination $dataTarget -Recurse
```

Do not commit generated copies if they become large or duplicate tracked test data. If duplication is unacceptable, replace this command with a small Python build helper that stages into `build\packaging\isisdata-minimal` instead.

- [ ] **Step 7: Build and inspect the data wheel**

Run:

```powershell
python -m build packaging\isisdata-minimal --wheel
python -m pip install --force-reinstall packaging\isisdata-minimal\dist\pyisis_isisdata_minimal-1.2.0-py3-none-any.whl
python -c "import pyisis_isisdata_minimal as d; print(d.data_path()); assert (d.data_path() / 'base' / 'kernels' / 'lsk' / 'naif0012.tls').is_file()"
```

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```powershell
git add packaging/isisdata-minimal tests/unitTest/python_packaging_unit_test.py
git commit -m "build: add minimal ISISDATA wheel package"
```

---

## Task 5: Add Windows Runtime Wheel Staging

**Files:**
- Create: `packaging/runtime-win64/README.md`
- Create: `packaging/runtime-win64/pyproject.toml`
- Create: `packaging/runtime-win64/src/pyisis_runtime/__init__.py`
- Create: `tools/packaging/stage_runtime_win64.py`
- Create: `tests/unitTest/runtime_wheel_script_unit_test.py`

- [ ] **Step 1: Write failing runtime staging tests**

Create `tests/unitTest/runtime_wheel_script_unit_test.py`:

```python
"""Unit tests for Windows runtime wheel staging.

Author: Geng Xun
Created: 2026-06-18
Last Modified: 2026-06-18
Updated: 2026-06-18  Geng Xun added runtime wheel staging coverage.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STAGING_SCRIPT = PROJECT_ROOT / "tools" / "packaging" / "stage_runtime_win64.py"


class RuntimeWheelScriptUnitTest(unittest.TestCase):
    """Test suite for runtime wheel staging."""

    def test_stage_runtime_copies_runtime_files_and_excludes_sdk_files(self):
        with TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            prefix = temp / "isis-prefix"
            (prefix / "bin" / "xml").mkdir(parents=True)
            (prefix / "lib").mkdir(parents=True)
            (prefix / "include" / "isis").mkdir(parents=True)
            (prefix / "bin" / "isis.dll").write_bytes(b"dll")
            (prefix / "bin" / "Qt5Core.dll").write_bytes(b"qt")
            (prefix / "bin" / "xml" / "stats.xml").write_text("<application />", encoding="utf-8")
            (prefix / "lib" / "Camera.plugin").write_text("Plugin", encoding="utf-8")
            (prefix / "lib" / "isis.lib").write_bytes(b"import library")
            (prefix / "include" / "isis" / "Cube.h").write_text("// header", encoding="utf-8")

            stage = temp / "runtime-stage"
            subprocess.run(
                [
                    sys.executable,
                    str(STAGING_SCRIPT),
                    "--isis-prefix",
                    str(prefix),
                    "--stage-dir",
                    str(stage),
                ],
                check=True,
                cwd=PROJECT_ROOT,
            )

            vendor = stage / "src" / "pyisis_runtime" / "vendor" / "isis"
            self.assertTrue((vendor / "bin" / "isis.dll").is_file())
            self.assertTrue((vendor / "bin" / "Qt5Core.dll").is_file())
            self.assertTrue((vendor / "bin" / "xml" / "stats.xml").is_file())
            self.assertTrue((vendor / "lib" / "Camera.plugin").is_file())
            self.assertFalse((vendor / "lib" / "isis.lib").exists())
            self.assertFalse((vendor / "include" / "isis" / "Cube.h").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing runtime staging test**

Run:

```powershell
python -m unittest tests.unitTest.runtime_wheel_script_unit_test -v
```

Expected: FAIL because the staging script does not exist.

- [ ] **Step 3: Add the runtime package README**

Create `packaging/runtime-win64/README.md`:

```markdown
# pyisis-runtime-win64

This package contains the Windows x64 runtime files needed by pyisis wheels.
It is generated from a verified ISIS 9.0.0 Windows prefix and intentionally
excludes SDK headers, import libraries, CMake metadata, and local build files.

The package exposes:

```python
import pyisis_runtime
print(pyisis_runtime.prefix())
print(pyisis_runtime.dll_directories())
```
```

- [ ] **Step 4: Add runtime package metadata**

Create `packaging/runtime-win64/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "pyisis-runtime-win64"
version = "1.2.0"
description = "Windows x64 ISIS runtime for pyisis."
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"

[tool.setuptools]
package-dir = { "" = "src" }
packages = ["pyisis_runtime"]
include-package-data = false

[tool.setuptools.package-data]
pyisis_runtime = ["vendor/isis/**/*"]
```

- [ ] **Step 5: Add the runtime package API**

Create `packaging/runtime-win64/src/pyisis_runtime/__init__.py`:

```python
"""Windows x64 runtime package for pyisis."""

# Copyright (c) 2026 Geng Xun, Henan University
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


_DLL_HANDLES: list[Any] = []


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
            _DLL_HANDLES.append(os.add_dll_directory(str(dll_dir)))
    return root


__all__ = ["configure_environment", "dll_directories", "prefix"]
```

- [ ] **Step 6: Add the runtime staging script**

Create `tools/packaging/stage_runtime_win64.py`:

```python
"""Stage a Windows ISIS prefix into a pyisis-runtime-win64 wheel tree."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


RUNTIME_PATTERNS = (
    "bin/**/*.dll",
    "bin/**/*.exe",
    "bin/xml/**/*.xml",
    "lib/**/*.dll",
    "lib/**/*.plugin",
    "Library/bin/**/*.dll",
    "Library/bin/**/*.exe",
    "Library/bin/xml/**/*.xml",
    "Library/lib/**/*.dll",
    "Library/lib/**/*.plugin",
)


def _copy_file(source: Path, source_root: Path, target_root: Path) -> None:
    relative = source.relative_to(source_root)
    target = target_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def stage_runtime(isis_prefix: Path, stage_dir: Path) -> Path:
    """Copy redistributable runtime files into a generated package stage."""

    if not (isis_prefix / "bin").exists() and not (isis_prefix / "Library").exists():
        raise FileNotFoundError(f"ISIS prefix does not look like a runtime prefix: {isis_prefix}")

    template_root = Path(__file__).resolve().parents[2] / "packaging" / "runtime-win64"
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    shutil.copytree(template_root, stage_dir)

    vendor_root = stage_dir / "src" / "pyisis_runtime" / "vendor" / "isis"
    for pattern in RUNTIME_PATTERNS:
        for source in isis_prefix.glob(pattern):
            if source.is_file():
                _copy_file(source, isis_prefix, vendor_root)

    if not any(vendor_root.glob("**/isis.dll")):
        raise FileNotFoundError("Staged runtime is missing isis.dll")

    camera_plugin = list(vendor_root.glob("**/Camera.plugin"))
    if not camera_plugin:
        raise FileNotFoundError("Staged runtime is missing Camera.plugin")

    return stage_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--isis-prefix", required=True, type=Path)
    parser.add_argument("--stage-dir", required=True, type=Path)
    args = parser.parse_args()

    stage_runtime(args.isis_prefix.resolve(), args.stage_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 7: Run runtime staging tests**

Run:

```powershell
python -m unittest tests.unitTest.runtime_wheel_script_unit_test -v
```

Expected: PASS.

- [ ] **Step 8: Build the generated runtime wheel locally**

Run:

```powershell
$env:ISIS_PREFIX = "$PWD\build\windows\isis-prefix"
python tools\packaging\stage_runtime_win64.py --isis-prefix $env:ISIS_PREFIX --stage-dir build\packaging\pyisis-runtime-win64
python -m build build\packaging\pyisis-runtime-win64 --wheel
python -m wheel tags --platform-tag win_amd64 --remove build\packaging\pyisis-runtime-win64\dist\pyisis_runtime_win64-1.2.0-py3-none-any.whl
```

Expected: a wheel tagged `py3-none-win_amd64` remains in `build\packaging\pyisis-runtime-win64\dist`.

- [ ] **Step 9: Commit**

Run:

```powershell
git add packaging/runtime-win64 tools/packaging/stage_runtime_win64.py tests/unitTest/runtime_wheel_script_unit_test.py
git commit -m "build: add Windows runtime wheel staging"
```

---

## Task 6: Add Local Wheel Build and Clean-Venv Verification

**Files:**
- Create: `tools/packaging/build_wheels.ps1`
- Create: `tools/packaging/test_wheel_install.py`

- [ ] **Step 1: Add the local wheel build harness**

Create `tools/packaging/build_wheels.ps1`:

```powershell
param(
    [string]$IsisPrefix = "$PWD\build\windows\isis-prefix",
    [string]$OutputDir = "$PWD\wheelhouse",
    [string]$PythonExecutable = "python"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $IsisPrefix)) {
    throw "ISIS prefix not found: $IsisPrefix"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

& $PythonExecutable -m pip install -U build scikit-build-core pybind11 wheel
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:ISIS_PREFIX = (Resolve-Path $IsisPrefix).Path
$env:ISISROOT = $env:ISIS_PREFIX

& $PythonExecutable tools\packaging\stage_runtime_win64.py `
    --isis-prefix $env:ISIS_PREFIX `
    --stage-dir build\packaging\pyisis-runtime-win64
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $PythonExecutable -m build build\packaging\pyisis-runtime-win64 --wheel --outdir $OutputDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$runtimeAnyWheel = Get-ChildItem -LiteralPath $OutputDir -Filter "pyisis_runtime_win64-*-py3-none-any.whl" | Select-Object -First 1
if ($runtimeAnyWheel) {
    & $PythonExecutable -m wheel tags --platform-tag win_amd64 --remove $runtimeAnyWheel.FullName
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $PythonExecutable -m build packaging\isisdata-minimal --wheel --outdir $OutputDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $PythonExecutable -m build . --wheel --no-isolation --skip-dependency-check --outdir $OutputDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Get-ChildItem -LiteralPath $OutputDir -Filter "*.whl" | Sort-Object Name | ForEach-Object {
    Write-Host $_.FullName
}
```

- [ ] **Step 2: Add the clean venv verification script**

Create `tools/packaging/test_wheel_install.py`:

```python
"""Verify pyisis wheels from a clean virtual environment."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
import venv


def _python_executable(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheelhouse", required=True, type=Path)
    parser.add_argument("--venv", required=True, type=Path)
    args = parser.parse_args()

    if args.venv.exists():
        raise FileExistsError(f"Refusing to reuse existing venv: {args.venv}")

    venv.EnvBuilder(with_pip=True).create(args.venv)
    python = _python_executable(args.venv)

    run([str(python), "-m", "pip", "install", "--no-index", "--find-links", str(args.wheelhouse), "pyisis"])
    run(
        [
            str(python),
            "-c",
            (
                "import os, pyisis, isis_pybind; "
                "status = pyisis.data_status(); "
                "print(status.message); "
                "assert os.environ.get('ISISROOT'); "
                "assert status.usable_for_smoke_tests"
            ),
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Build wheels locally**

Run:

```powershell
.\tools\packaging\build_wheels.ps1 -IsisPrefix "$PWD\build\windows\isis-prefix" -OutputDir "$PWD\wheelhouse"
```

Expected: `wheelhouse` contains wheels for `pyisis`, `pyisis-runtime-win64`, and `pyisis-isisdata-minimal`.

- [ ] **Step 4: Verify the wheels in a clean venv**

Run:

```powershell
python tools\packaging\test_wheel_install.py --wheelhouse wheelhouse --venv build\packaging\pip-smoke-venv
```

Expected: PASS and the subprocess prints a usable minimal ISISDATA status message.

- [ ] **Step 5: Commit**

Run:

```powershell
git add tools/packaging/build_wheels.ps1 tools/packaging/test_wheel_install.py
git commit -m "build: add local pip wheel verification"
```

---

## Task 7: Add CI Wheel Build Workflow

**Files:**
- Create: `.github/workflows/wheels.yml`
- Modify: `README.md`

- [ ] **Step 1: Add a Windows-only wheel workflow**

Create `.github/workflows/wheels.yml`:

```yaml
name: wheels

on:
  workflow_dispatch:
  pull_request:
    paths:
      - "CMakeLists.txt"
      - "pyproject.toml"
      - "python/**"
      - "src/**"
      - "packaging/**"
      - "tools/packaging/**"
      - ".github/workflows/wheels.yml"

jobs:
  windows-cp312:
    runs-on: windows-2022
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install build tools
        run: python -m pip install -U build wheel

      - name: Build ISIS prefix
        shell: pwsh
        run: |
          $env:CONDA_PREFIX = "E:\code\pyisis-win-env"
          .\ports\windows\isis\fetch_isis_900.ps1
          .\ports\windows\isis\apply_patches.ps1
          .\ports\windows\isis\configure_isis.ps1
          .\ports\windows\isis\build_isis.ps1
          .\ports\windows\isis\install_isis.ps1
          .\ports\windows\isis\verify_isis_prefix.ps1

      - name: Build wheels
        shell: pwsh
        run: .\tools\packaging\build_wheels.ps1 -IsisPrefix "$PWD\build\windows\isis-prefix" -OutputDir "$PWD\wheelhouse"

      - name: Test wheel install
        shell: pwsh
        run: python tools\packaging\test_wheel_install.py --wheelhouse wheelhouse --venv build\packaging\pip-smoke-venv

      - uses: actions/upload-artifact@v4
        with:
          name: pyisis-windows-wheels
          path: wheelhouse/*.whl
```

If GitHub-hosted runners cannot build ISIS within the time limit, replace the `Build ISIS prefix` step with a cached artifact or a release asset download that is produced by a separate runtime-prefix workflow.

- [ ] **Step 2: Document pip install status**

Add this section to `README.md`:

```markdown
## pip Wheels

The pip packaging path is Windows-first. The intended user experience is:

```powershell
pip install pyisis
python -c "import pyisis; import isis_pybind; print(pyisis.data_status().message)"
```

The `pyisis` wheel contains the Python facade and `_isis_core` extension. The
Windows ISIS runtime is split into `pyisis-runtime-win64`, and the smoke-test
ISISDATA tree is split into `pyisis-isisdata-minimal`.

Production ISISDATA is not bundled in the main wheel. Use a real `ISISDATA`
directory for mission workflows beyond smoke tests.
```

- [ ] **Step 3: Run local tests**

Run:

```powershell
python -m unittest tests.unitTest.python_packaging_unit_test tests.unitTest.pyisis_runtime_unit_test tests.unitTest.runtime_wheel_script_unit_test -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```powershell
git add .github/workflows/wheels.yml README.md
git commit -m "ci: add Windows wheel build workflow"
```

---

## Task 8: TestPyPI Publishing Dry Run

**Files:**
- No tracked files unless the dry run finds documentation gaps.

- [ ] **Step 1: Build final local wheelhouse**

Run:

```powershell
Remove-Item -LiteralPath wheelhouse -Recurse -Force -ErrorAction SilentlyContinue
.\tools\packaging\build_wheels.ps1 -IsisPrefix "$PWD\build\windows\isis-prefix" -OutputDir "$PWD\wheelhouse"
```

Expected: wheelhouse contains exactly one wheel per distribution for the current Python/platform build.

- [ ] **Step 2: Check wheel metadata**

Run:

```powershell
python -m pip install -U twine
python -m twine check wheelhouse\*.whl
```

Expected: PASS for all wheels.

- [ ] **Step 3: Verify clean local install one last time**

Run:

```powershell
Remove-Item -LiteralPath build\packaging\pip-smoke-venv -Recurse -Force -ErrorAction SilentlyContinue
python tools\packaging\test_wheel_install.py --wheelhouse wheelhouse --venv build\packaging\pip-smoke-venv
```

Expected: PASS.

- [ ] **Step 4: Upload to TestPyPI**

Run only after credentials are configured outside the repository:

```powershell
python -m twine upload --repository testpypi wheelhouse\*.whl
```

Expected: TestPyPI accepts all three distributions.

- [ ] **Step 5: Verify TestPyPI install**

Run in a brand-new venv:

```powershell
python -m venv build\packaging\testpypi-venv
build\packaging\testpypi-venv\Scripts\python.exe -m pip install `
  --index-url https://test.pypi.org/simple `
  --extra-index-url https://pypi.org/simple `
  pyisis
build\packaging\testpypi-venv\Scripts\python.exe -c "import pyisis, isis_pybind; print(pyisis.data_status().message)"
```

Expected: import succeeds and minimal ISISDATA is usable.

---

## Self-Review

- Spec coverage: This plan covers main wheel metadata, CMake wheel staging, runtime discovery, Windows runtime wheel staging, minimal ISISDATA packaging, clean venv verification, CI, and TestPyPI dry run.
- Placeholder scan: No unfinished marker patterns are present. The only conditional branch is the explicit CI fallback for long ISIS builds.
- Type consistency: Runtime helper names are consistent across tasks: `configure_runtime`, `RuntimeDiscovery`, `pyisis_runtime.prefix`, `pyisis_runtime.dll_directories`, and `pyisis_isisdata_minimal.data_path`.
- Risk callout: The runtime wheel may exceed PyPI's default 100 MB file limit after staging. If that happens, reduce copied runtime files first; if still too large, publish runtime wheels through GitHub Releases or a custom simple index while keeping `pyisis` metadata on PyPI.
