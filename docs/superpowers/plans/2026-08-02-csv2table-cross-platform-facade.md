# Cross-Platform `csv2table` Facade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one ISIS 10-only `csv2table()` Python API that calls the exported C++ function on Linux and the native `csv2table.exe` on Windows.

**Architecture:** A private Python module normalizes the public arguments once and dispatches a preformatted ISIS argument list to either `_isis_core._csv2table_native(arguments)` or a private shell-free application runner. The C++ adapter is compiled only for non-Windows ISIS 10, while the Windows APP manifest builds the executable used by the fallback backend.

**Tech Stack:** C++17, pybind11, ISIS 10 `UserInterface`/`csv2table`, Python 3.12/3.13, `unittest`, CMake, PowerShell, GitHub Actions.

## Global Constraints

- The public signature is `csv2table(csv, to, tablename, *, label=None, coltypes=None) -> None`.
- `coltypes` accepts only `Double`, `Integer`, `Float`, and `Text`.
- ISIS 9 must import unchanged and must not advertise `csv2table`.
- Linux must call the exported `Isis::csv2table`; Windows must call `csv2table.exe` with `shell=False` and no GUI.
- The internal runner must not be added to `isis_pybind.__all__` or `pyisis.__all__`.
- Do not expose `UserInterface`, Qt signals, Qt slots, or GUI entry points.
- Do not add production dependencies; use only the Python standard library and existing conda dependencies.
- Do not modify `.gitignore` or `print.prt`.
- Preserve all unrelated worktree changes and stage only explicit task paths.
- Commit steps below are held until the user explicitly authorizes commits.
- Before each Linux build/test command block, activate the named conda environment and set `ISIS_PREFIX` plus `ISISDATA` explicitly.

---

## File Structure

- `python/isis_pybind/_app_runner.py`: private executable discovery and shell-free process execution.
- `python/isis_pybind/_csv2table.py`: argument normalization, platform dispatch, and the public callable.
- `python/isis_pybind/__init__.py`: ISIS 10-only export registration.
- `src/bind_isis10.cpp`: Linux-only `_csv2table_native(arguments)` adapter.
- `CMakeLists.txt`: copy and install both private Python modules.
- `tests/unitTest/csv2table_facade_unit_test.py`: Python contract and Linux integration tests.
- `tests/unitTest/windows_isis_app_smoke_script_unit_test.py`: Windows manifest/smoke harness regression assertions.
- `ports/windows/isis/windows-app-manifest.json`: add the native Windows APP target.
- `ports/windows/isis/test_isis_app_batch_smoke.ps1`: exercise `csv2table` and verify the table with `tabledump`.
- `tools/dev/generate_isis10_bind_inventory.py`: record final dispositions for all three new application headers.
- `tests/unitTest/isis10_bind_inventory_unit_test.py`: inventory disposition gates.
- `reference/isis10_bind_candidates/*`: regenerated inventory outputs.
- `reference/isis10_bind_candidates/README.md`, `docs/isis9-isis10-binding-compatibility-plan.md`, and `pybind_progress_log.md`: completion documentation.

---

### Task 1: Private shell-free ISIS APP runner

**Files:**
- Create: `python/isis_pybind/_app_runner.py`
- Create: `tests/unitTest/csv2table_facade_unit_test.py`

**Interfaces:**
- Produces: `_find_isis_app_executable(app_name: str) -> str`
- Produces: `_run_isis_app(app_name: str, arguments: Sequence[str]) -> None`
- Consumes: `ISIS_PREFIX`, `ISISROOT`, and `CONDA_PREFIX` configured by the existing runtime layer.

- [x] **Step 1: Configure and build an unchanged ISIS 10 baseline**

Run:

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp370
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
cmake -S . -B build/csv2table-isis10 \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" \
  -DISIS_PREFIX="$ISIS_PREFIX" \
  -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON \
  -DCMAKE_CXX_COMPILER="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-c++"
cmake --build build/csv2table-isis10 -j2
```

Expected: the unchanged branch builds and imports before any production edit.

- [x] **Step 2: Write failing runner tests**

Create the test module with the repository metadata header and add these focused behaviors:

```python
from __future__ import annotations

import os
import importlib.util
from pathlib import Path
import subprocess
import tempfile
from unittest import mock
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = PROJECT_ROOT / "python" / "isis_pybind" / "_app_runner.py"
RUNNER_SPEC = importlib.util.spec_from_file_location(
    "csv2table_test_app_runner", RUNNER_PATH
)
assert RUNNER_SPEC and RUNNER_SPEC.loader
_app_runner = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(_app_runner)


class IsisAppRunnerTest(unittest.TestCase):
    def test_configured_prefix_precedes_path_lookup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "bin" / "csv2table.exe"
            executable.parent.mkdir()
            executable.touch()
            with mock.patch.dict(os.environ, {"ISIS_PREFIX": temp_dir}, clear=True), \
                 mock.patch.object(
                     _app_runner, "_executable_name", return_value="csv2table.exe"
                 ), mock.patch.object(_app_runner.shutil, "which") as which:
                resolved = _app_runner._find_isis_app_executable("csv2table")
        self.assertEqual(resolved, str(executable))
        which.assert_not_called()

    def test_runner_uses_argument_list_without_shell(self):
        completed = subprocess.CompletedProcess([], 0, stdout="ok", stderr="")
        with mock.patch.object(
            _app_runner,
            "_find_isis_app_executable",
            return_value=r"C:\\isis\\bin\\csv2table.exe",
        ), mock.patch.object(
            _app_runner.subprocess, "run", return_value=completed
        ) as run:
            result = _app_runner._run_isis_app(
                "csv2table", ["CSV=input file.csv", "TO=target.cub"]
            )
        self.assertIsNone(result)
        run.assert_called_once_with(
            [
                r"C:\\isis\\bin\\csv2table.exe",
                "CSV=input file.csv",
                "TO=target.cub",
            ],
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )

    def test_runner_reports_native_failure_context(self):
        completed = subprocess.CompletedProcess(
            [], 7, stdout="native output", stderr="bad table"
        )
        with mock.patch.object(
            _app_runner,
            "_find_isis_app_executable",
            return_value="csv2table.exe",
        ), mock.patch.object(
            _app_runner.subprocess, "run", return_value=completed
        ):
            with self.assertRaisesRegex(RuntimeError, "exit code 7.*bad table"):
                _app_runner._run_isis_app("csv2table", ["CSV=input.csv"])
```

- [x] **Step 3: Run the test and verify RED**

Run:

```bash
ISIS_PYBIND_BUILD_DIR="$PWD/build/csv2table-isis10/python" \
python -m unittest tests.unitTest.csv2table_facade_unit_test.IsisAppRunnerTest -v
```

Expected: FAIL because the source file `python/isis_pybind/_app_runner.py` does not exist.

- [x] **Step 4: Implement the minimal private runner**

Create `python/isis_pybind/_app_runner.py` with file metadata and this behavior:

```python
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
        raise ValueError("ISIS application name must be alphanumeric or underscore")
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
    raise FileNotFoundError(f"ISIS application executable not found: {executable_name}")


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
    message = f"ISIS application {app_name} failed with exit code {completed.returncode}"
    if diagnostic:
        message += f": {diagnostic}"
    raise RuntimeError(message)
```

- [x] **Step 5: Verify GREEN against the new source module**

The test loads the private source module directly, so no temporary package copy is required before Task 2 adds the permanent CMake packaging rules:

```bash
ISIS_PYBIND_BUILD_DIR="$PWD/build/csv2table-isis10/python" \
python -m unittest tests.unitTest.csv2table_facade_unit_test.IsisAppRunnerTest -v
```

Expected: all runner tests pass.

- [x] **Step 6: Hold the commit pending explicit authorization**

Intended paths if authorization is later granted:

```bash
git add python/isis_pybind/_app_runner.py tests/unitTest/csv2table_facade_unit_test.py
git commit -m "feat: add private ISIS app runner"
```

---

### Task 2: Public `csv2table` facade and package installation

**Files:**
- Create: `python/isis_pybind/_csv2table.py`
- Modify: `python/isis_pybind/__init__.py`
- Modify: `CMakeLists.txt`
- Modify: `tests/unitTest/csv2table_facade_unit_test.py`

**Interfaces:**
- Consumes: `_run_isis_app(app_name, arguments)` from Task 1.
- Produces: `_build_csv2table_arguments(csv, to, tablename, *, label=None, coltypes=None) -> list[str]`.
- Produces: `csv2table(csv, to, tablename, *, label=None, coltypes=None) -> None`.
- Produces: private lazy `_native_csv2table(arguments)` dispatch to `_isis_core._csv2table_native`.

- [x] **Step 1: Add failing normalization and dispatch tests**

Add to `tests/unitTest/csv2table_facade_unit_test.py`:

```python
from isis_pybind import _csv2table


class Csv2TableFacadeTest(unittest.TestCase):
    def test_arguments_preserve_paths_and_encode_optional_values(self):
        arguments = _csv2table._build_csv2table_arguments(
            Path("input files/measurements.csv"),
            Path("output files/target.cub"),
            "Measurements",
            label=Path("labels/table label.pvl"),
            coltypes=["Double", "Text"],
        )
        self.assertEqual(
            arguments,
            [
                "CSV=input files/measurements.csv",
                "TO=output files/target.cub",
                "TABLENAME=Measurements",
                "LABEL=labels/table label.pvl",
                "COLTYPES=(Double,Text)",
            ],
        )

    def test_empty_table_name_and_invalid_coltype_are_rejected(self):
        with self.assertRaises(ValueError):
            _csv2table._build_csv2table_arguments("a.csv", "b.cub", "   ")
        with self.assertRaisesRegex(ValueError, "Unsupported COLTYPES value"):
            _csv2table._build_csv2table_arguments(
                "a.csv", "b.cub", "T", coltypes=["Complex"]
            )

    def test_windows_dispatch_uses_private_runner(self):
        with mock.patch(
            "isis_pybind._csv2table._is_windows", return_value=True
        ), mock.patch("isis_pybind._csv2table._run_isis_app") as runner:
            result = _csv2table.csv2table("a.csv", "b.cub", "T")
        self.assertIsNone(result)
        runner.assert_called_once_with(
            "csv2table", ["CSV=a.csv", "TO=b.cub", "TABLENAME=T"]
        )

    def test_linux_dispatch_uses_native_entry_point(self):
        with mock.patch(
            "isis_pybind._csv2table._is_windows", return_value=False
        ), mock.patch("isis_pybind._csv2table._native_csv2table") as native:
            _csv2table.csv2table("a.csv", "b.cub", "T")
        native.assert_called_once_with(
            ["CSV=a.csv", "TO=b.cub", "TABLENAME=T"]
        )
```

- [x] **Step 2: Run the test and verify RED**

Run the focused class. Expected: FAIL because `_csv2table` does not exist.

```bash
ISIS_PYBIND_BUILD_DIR="$PWD/build/csv2table-isis10/python" \
python -m unittest tests.unitTest.csv2table_facade_unit_test.Csv2TableFacadeTest -v
```

- [x] **Step 3: Implement argument normalization and dispatch**

Create `python/isis_pybind/_csv2table.py` with repository file metadata and the following minimum implementation:

```python
from __future__ import annotations

import os
from os import PathLike
from typing import Sequence

from ._app_runner import _run_isis_app


_ALLOWED_COLTYPES = {"Double", "Integer", "Float", "Text"}


def _is_windows() -> bool:
    return os.name == "nt"


def _build_csv2table_arguments(
    csv: str | PathLike[str],
    to: str | PathLike[str],
    tablename: str,
    *,
    label: str | PathLike[str] | None = None,
    coltypes: Sequence[str] | None = None,
) -> list[str]:
    if not isinstance(tablename, str) or not tablename.strip():
        raise ValueError("tablename must be a non-empty string")
    arguments = [
        f"CSV={os.fspath(csv)}",
        f"TO={os.fspath(to)}",
        f"TABLENAME={tablename}",
    ]
    if label is not None:
        arguments.append(f"LABEL={os.fspath(label)}")
    if coltypes is not None:
        values = list(coltypes)
        invalid = [value for value in values if value not in _ALLOWED_COLTYPES]
        if invalid:
            raise ValueError(f"Unsupported COLTYPES value: {invalid[0]}")
        if values:
            arguments.append(f"COLTYPES=({','.join(values)})")
    return arguments


def _native_csv2table(arguments: Sequence[str]) -> None:
    from ._isis_core import _csv2table_native

    _csv2table_native(list(arguments))


def csv2table(
    csv: str | PathLike[str],
    to: str | PathLike[str],
    tablename: str,
    *,
    label: str | PathLike[str] | None = None,
    coltypes: Sequence[str] | None = None,
) -> None:
    arguments = _build_csv2table_arguments(
        csv, to, tablename, label=label, coltypes=coltypes
    )
    try:
        if _is_windows():
            _run_isis_app("csv2table", arguments)
        else:
            _native_csv2table(arguments)
    except Exception as error:
        raise RuntimeError(f"csv2table failed: {error}") from error
```

- [x] **Step 4: Register the ISIS 10-only public export**

In `python/isis_pybind/__init__.py`, import `csv2table` only when
`_core_isis_major >= 10`, append it to `_OPTIONAL_ISIS10_EXPORTS`, and leave the
ISIS 9 path untouched:

```python
if _core_isis_major >= 10:
    from ._csv2table import csv2table
    _OPTIONAL_ISIS10_EXPORTS.append("csv2table")
```

Do not import or export `_run_isis_app`.

- [x] **Step 5: Copy and install the private Python modules through CMake**

Add source/build variables for `_app_runner.py` and `_csv2table.py`, include
them in `configure_file`, `add_custom_command(OUTPUT/DEPENDS)`,
`sync_python_package_files`, and `install(FILES ...)`. Follow the existing
explicit copy pattern used for `__init__.py` and `_runtime.py`; do not introduce
glob-based packaging.

- [x] **Step 6: Reconfigure, rebuild package files, and verify GREEN**

```bash
cmake -S . -B build/csv2table-isis10 \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" \
  -DISIS_PREFIX="$CONDA_PREFIX" \
  -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON \
  -DCMAKE_CXX_COMPILER="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-c++"
cmake --build build/csv2table-isis10 --target sync_python_package_files -j2
ISIS_PYBIND_BUILD_DIR="$PWD/build/csv2table-isis10/python" \
python -m unittest tests.unitTest.csv2table_facade_unit_test -v
```

Expected: runner and facade unit tests pass; no native integration test exists yet.

- [x] **Step 7: Hold the commit pending explicit authorization**

```bash
git add CMakeLists.txt python/isis_pybind/__init__.py \
  python/isis_pybind/_app_runner.py python/isis_pybind/_csv2table.py \
  tests/unitTest/csv2table_facade_unit_test.py
git commit -m "feat: add cross-platform csv2table facade"
```

---

### Task 3: Linux ISIS 10 native adapter and behavior test

**Files:**
- Modify: `src/bind_isis10.cpp`
- Modify: `tests/unitTest/csv2table_facade_unit_test.py`

**Interfaces:**
- Consumes: preformatted `Sequence[str]` produced by `_build_csv2table_arguments`.
- Produces: `_isis_core._csv2table_native(arguments: list[str]) -> None` on non-Windows ISIS 10 only.

- [x] **Step 1: Add the failing Linux integration test**

Use the required `_unit_test_support` import fallback and add:

```python
try:
    from ._unit_test_support import ip, make_closed_test_cube, open_cube, temporary_directory
except ImportError:
    from _unit_test_support import ip, make_closed_test_cube, open_cube, temporary_directory


@unittest.skipUnless(ip.__isis_major__ >= 10 and os.name != "nt", "Linux ISIS 10 only")
class Csv2TableLinuxIntegrationTest(unittest.TestCase):
    def test_csv_and_label_are_attached_as_typed_table(self):
        with temporary_directory() as temp_dir:
            cube_path = make_closed_test_cube(temp_dir, name="target.cub")
            csv_path = temp_dir / "measurements.csv"
            csv_path.write_text(
                "Value,Name\n1.5,MARS\n2.5,PHOBOS\n", encoding="utf-8"
            )
            label_path = temp_dir / "table.pvl"
            label_path.write_text("Source = UnitTest\nEnd\n", encoding="utf-8")

            result = ip.csv2table(
                csv_path,
                cube_path,
                "Measurements",
                label=label_path,
                coltypes=["Double", "Text"],
            )
            self.assertIsNone(result)

            cube = open_cube(cube_path)
            try:
                self.assertTrue(cube.has_table("Measurements"))
                table = cube.read_table("Measurements")
                self.assertEqual(table.records(), 2)
                self.assertEqual(table[0]["Value"].value(), 1.5)
                self.assertEqual(table[1]["Name"].value().rstrip("\x00"), "PHOBOS")
                self.assertEqual(table.label().keyword("Source")[0], "UnitTest")
            finally:
                cube.close()
```

- [x] **Step 2: Run the integration test and verify RED**

```bash
ISIS_PYBIND_BUILD_DIR="$PWD/build/csv2table-isis10/python" \
python -m unittest \
  tests.unitTest.csv2table_facade_unit_test.Csv2TableLinuxIntegrationTest -v
```

Expected: FAIL with missing `_csv2table_native`, proving the public facade has reached the absent native backend.

- [x] **Step 3: Implement the native adapter**

Update the source metadata in `src/bind_isis10.cpp`. Under
`#if defined(PYISIS_ISIS10_API) && !defined(_WIN32)`, include `csv2table.h`,
`FileName.h`, and `UserInterface.h`. Add this helper in the anonymous namespace:

```cpp
void runCsv2TableNative(const std::vector<std::string> &arguments) {
  QVector<QString> uiArguments;
  uiArguments.reserve(static_cast<int>(arguments.size()));
  for (const std::string &argument : arguments) {
    uiArguments.append(stdStringToQString(argument));
  }

  const QString xmlPath =
      Isis::FileName("$ISISROOT/bin/xml/csv2table.xml").expanded();
  Isis::UserInterface ui(xmlPath, uiArguments);
  Isis::csv2table(ui, nullptr);
}
```

Register only on non-Windows ISIS 10:

```cpp
m.def("_csv2table_native",
      &runCsv2TableNative,
      py::arg("arguments"),
      "Run the ISIS 10 csv2table implementation with normalized UI arguments.");
```

- [x] **Step 4: Rebuild and verify GREEN**

```bash
cmake --build build/csv2table-isis10 -j2
export ISIS_PYBIND_BUILD_DIR="$PWD/build/csv2table-isis10/python"
python -m unittest tests.unitTest.csv2table_facade_unit_test -v
python tests/smoke_import.py
```

Expected: the focused test passes and the smoke import remains green.

- [x] **Step 5: Inspect linkage**

```bash
nm -D -C "$CONDA_PREFIX/lib/libisis10.0.0.so" | rg "Isis::csv2table"
ldd build/csv2table-isis10/python/isis_pybind/_isis_core*.so | rg "libisis10"
```

Expected: the installed library exports `Isis::csv2table`, and the extension resolves against ISIS 10.

- [x] **Step 6: Hold the commit pending explicit authorization**

```bash
git add src/bind_isis10.cpp tests/unitTest/csv2table_facade_unit_test.py
git commit -m "feat: bind ISIS 10 csv2table on Linux"
```

---

### Task 4: Windows native APP availability and hosted behavior smoke

**Files:**
- Modify: `ports/windows/isis/windows-app-manifest.json`
- Modify: `ports/windows/isis/test_isis_app_batch_smoke.ps1`
- Modify: `tests/unitTest/windows_isis_app_smoke_script_unit_test.py`
- Modify: `.github/workflows/windows-isis-apps.yml` only if its APP-count label/gate still matches the branch after rebasing.

**Interfaces:**
- Produces: installed `bin/csv2table.exe` plus `bin/xml/csv2table.xml` in the Windows ISIS 10 prefix.
- Consumes: the private Python runner's executable lookup contract.

- [x] **Step 1: Compare the latest Windows APP wave before editing the manifest**

Read-only check first:

```bash
git status --short --branch
git worktree list --porcelain
git log --oneline --decorate -5 main
```

Record the newest local APP-wave manifest count and entries. Because the design
and plan are intentionally uncommitted, do not rebase or stash here. Add the
single `csv2table` record to the current feature manifest, then replay or
rebase that narrow change onto the latest `main` only after publication is
authorized. Preserve the cumulative manifest and its current minimum-count
gate during that later integration.

- [x] **Step 2: Add failing manifest and smoke-script assertions**

Extend `WindowsIsisAppSmokeScriptUnitTest`:

```python
import json


def test_csv2table_is_allowlisted_and_behavior_smoked(self):
    manifest_path = PROJECT_ROOT / "ports" / "windows" / "isis" / "windows-app-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    apps = {item["name"]: item for item in manifest["apps"]}
    self.assertIn("csv2table", apps)
    script_text = (
        PROJECT_ROOT / "ports" / "windows" / "isis" / "test_isis_app_batch_smoke.ps1"
    ).read_text(encoding="utf-8")
    self.assertIn('Invoke-IsisApp "csv2table"', script_text)
    self.assertIn('Invoke-IsisApp "tabledump"', script_text)
```

- [x] **Step 3: Run the test and verify RED**

```bash
python -m unittest tests.unitTest.windows_isis_app_smoke_script_unit_test -v
```

Expected: FAIL because `csv2table` is not in the manifest or behavior smoke.

- [x] **Step 4: Add the manifest record**

Insert `csv2table` in alphabetical order with:

```json
{
  "name": "csv2table",
  "component": "apps-base",
  "source_dir": "isis/src/base/apps/csv2table",
  "xml": "isis/src/base/apps/csv2table/csv2table.xml",
  "smoke_tier": "cube",
  "selection_wave": "W4-medium",
  "versions": {
    "9.0.0": {
      "status": "supported",
      "build_status": "implementation_ready",
      "smoke_status": "pending",
      "linux_comparison": "pending"
    },
    "10.0.0": {
      "status": "experimental",
      "build_status": "implementation_ready",
      "smoke_status": "pending",
      "linux_comparison": "pending"
    }
  },
  "release_component": "apps-base"
}
```

Do not reduce or replace any existing APP entry.

- [x] **Step 5: Add a real table round-trip to the batch smoke**

After `$seedCube` is created in `test_isis_app_batch_smoke.ps1`, add:

```powershell
$csvInput = Join-Path $WorkDir "csv2table-input.csv"
$tableDump = Join-Path $WorkDir "csv2table-output.txt"
Set-Content -LiteralPath $csvInput -Value @(
    "Value,Name",
    "1.5,MARS",
    "2.5,PHOBOS"
)
Invoke-IsisApp "csv2table" @(
    "csv=$csvInput", "to=$seedCube", "tablename=PyisisCsv2Table",
    "coltypes=(Double,Text)"
) "cube-csv2table.log"
Invoke-IsisApp "tabledump" @(
    "from=$seedCube", "name=PyisisCsv2Table", "to=$tableDump"
) "cube-csv2table-tabledump.log" $tableDump
```

This verifies that the executable not only starts but writes a readable ISIS table.

- [x] **Step 6: Verify GREEN and validate JSON**

```bash
python -m json.tool ports/windows/isis/windows-app-manifest.json >/dev/null
python -m unittest tests.unitTest.windows_isis_app_smoke_script_unit_test -v
```

Expected: both checks pass. Hosted Windows compilation remains pending until the branch is published with user authorization.

- [x] **Step 7: Hold the commit pending explicit authorization**

```bash
git add ports/windows/isis/windows-app-manifest.json \
  ports/windows/isis/test_isis_app_batch_smoke.ps1 \
  tests/unitTest/windows_isis_app_smoke_script_unit_test.py \
  .github/workflows/windows-isis-apps.yml
git commit -m "build: add Windows csv2table application"
```

---

### Task 5: Close the ISIS 10 function inventory and documentation

**Files:**
- Modify: `tools/dev/generate_isis10_bind_inventory.py`
- Modify: `tests/unitTest/isis10_bind_inventory_unit_test.py`
- Regenerate: `reference/isis10_bind_candidates/functions_inventory.csv`
- Regenerate: `reference/isis10_bind_candidates/raw_new_headers.csv`
- Modify: `reference/isis10_bind_candidates/README.md`
- Modify: `docs/isis9-isis10-binding-compatibility-plan.md`
- Modify: `pybind_progress_log.md`

**Interfaces:**
- Produces final classifications: `csv2table=bound`, `ocams2isis=native-app`, and `eisstitch=native-app`.
- Preserves all discovered headers with no unclassified item.

- [x] **Step 1: Add failing inventory disposition assertions**

Add:

```python
def test_application_headers_have_final_dispositions(self) -> None:
    classifications = inventory.HEADER_CLASSIFICATIONS
    self.assertEqual(classifications["csv2table.h"].disposition, "bound")
    self.assertEqual(classifications["ocams2isis.h"].disposition, "native-app")
    self.assertEqual(classifications["eisstitch.h"].disposition, "native-app")
```

- [x] **Step 2: Run the test and verify RED**

```bash
python -m unittest tests.unitTest.isis10_bind_inventory_unit_test -v
```

Expected: FAIL because the three headers are still recorded as candidates.

- [x] **Step 3: Update generator metadata and recommendations**

Change `HEADER_CLASSIFICATIONS` to the three final dispositions and update
`FUNCTION_CANDIDATES` recommendations so:

- `csv2table` records the Linux-library/Windows-executable facade as complete.
- `ocams2isis` and `eisstitch` record that native APP execution is the selected
  boundary and raw `UserInterface` binding is intentionally excluded.

Update the generator's metadata header with the 2026-08-02 change.

- [x] **Step 4: Regenerate the inventory from the active conda prefixes**

```bash
/home/gengxun/miniconda3/envs/asp370/bin/python \
  tools/dev/generate_isis10_bind_inventory.py \
  --isis9-prefix /home/gengxun/miniconda3/envs/asp360_new \
  --isis10-prefix /home/gengxun/miniconda3/envs/asp370
```

Expected: 13 discovered headers, 6 class candidates, and 3 function candidates; no classification error.

- [x] **Step 5: Update narrative documentation and progress log**

Record:

- exact Linux/Windows backend split;
- ISIS 10-only public surface;
- native-APP decision for `ocams2isis` and `eisstitch`;
- focused tests and their exact results;
- Windows hosted validation as pending until it actually runs.

Do not claim Windows success from structural tests alone.

- [x] **Step 6: Verify GREEN**

```bash
python -m unittest tests.unitTest.isis10_bind_inventory_unit_test -v
git diff --check
```

- [x] **Step 7: Hold the commit pending explicit authorization**

```bash
git add tools/dev/generate_isis10_bind_inventory.py \
  tests/unitTest/isis10_bind_inventory_unit_test.py \
  reference/isis10_bind_candidates \
  docs/isis9-isis10-binding-compatibility-plan.md \
  pybind_progress_log.md
git commit -m "docs: close ISIS 10 application API inventory"
```

---

### Task 6: Dual-version local verification and handoff

**Files:**
- Review only: all changed task paths.
- Remove after verification: disposable `build/csv2table-isis9` and `build/csv2table-isis10` trees, after preserving test logs if needed.

**Interfaces:**
- Consumes all prior tasks.
- Produces evidence for Linux ISIS 9/10 compatibility and a clear Windows hosted-validation handoff.

- [x] **Step 1: Run the complete focused ISIS 10 verification**

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp370
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
cmake --build build/csv2table-isis10 -j2
export ISIS_PYBIND_BUILD_DIR="$PWD/build/csv2table-isis10/python"
python tests/smoke_import.py
python -m unittest tests.unitTest.csv2table_facade_unit_test -v
python -m unittest tests.unitTest.isis10_bind_inventory_unit_test -v
python -m unittest tests.unitTest.windows_isis_app_smoke_script_unit_test -v
```

- [x] **Step 2: Configure and verify ISIS 9 compatibility**

```bash
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
cmake -S . -B build/csv2table-isis9 \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" \
  -DISIS_PREFIX="$ISIS_PREFIX" \
  -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON \
  -DCMAKE_CXX_COMPILER="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-c++"
cmake --build build/csv2table-isis9 -j2
export ISIS_PYBIND_BUILD_DIR="$PWD/build/csv2table-isis9/python"
python tests/smoke_import.py
python - <<'PY'
import isis_pybind
assert isis_pybind.__isis_major__ == 9
assert not hasattr(isis_pybind, "csv2table")
assert "csv2table" not in isis_pybind.__all__
PY
```

- [x] **Step 3: Review diff and protected local files**

```bash
git status --short --branch
git diff --check
git diff --stat
git diff -- .gitignore print.prt
```

Expected: no `.gitignore` or `print.prt` changes; only planned paths are modified.

- [x] **Step 4: Record the Windows boundary accurately**

Report Windows as `implementation ready, hosted validation pending` until the
GitHub Actions build installs `csv2table.exe`, runs the batch smoke, and dumps
the attached table successfully. Do not infer Windows success from Linux or
mocked tests.

- [x] **Step 5: Clean disposable build products after results are captured**

Resolve the exact directories first, then delete only the two feature-created
build trees. Preserve source, worktree, reports, and any wheel/package artifact
needed for later publication.

- [x] **Step 6: Request publication authority if remote validation is desired**

Do not commit, push, open a PR, or run the hosted workflow until the user
explicitly authorizes those operations. When authorized, stage the explicit
paths listed in Tasks 1-5, commit, push, open the PR, and run the Windows
workflow before making a dual-platform completion claim.
