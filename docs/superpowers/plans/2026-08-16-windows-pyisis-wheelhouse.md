# Windows PyISIS Wheelhouse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and release-validate the three-wheel Windows CPython 3.12 / ISIS 9.0.0 PyISIS wheelhouse without packaging standalone ISIS applications.

**Architecture:** Reuse `tools/packaging/build_wheels.ps1` for the runtime, minimal-data, and binding wheels. Add machine-readable clean-install evidence to the existing isolated-install tool and a focused Windows wheelhouse validator that enforces exact filenames, payload boundaries, dependency closure, and SHA-256 reporting.

**Tech Stack:** PowerShell, CPython 3.12, `venv`, `pip`, `build`, scikit-build-core, pybind11, MSVC `dumpbin`, `zipfile`, JSON, `unittest`.

## Global Constraints

- Target Windows 11 x64, CPython 3.12, ISIS 9.0.0, package version `1.3.0rc2`, and platform tag `win_amd64`.
- Use `D:\pyisis-win-env\python.exe`, `D:\pyisis-win-env` as the dependency prefix, and `build/windows/isis-prefix` as the verified ISIS prefix.
- Produce exactly the binding, runtime, and minimal-data wheels declared by the approved SPEC.
- Keep ISIS APP executables and APP XML out of every PyISIS wheel.
- Do not upload to PyPI/TestPyPI or create a GitHub release.
- Do not build Linux wheels in M04; Linux and native APP release work remain follow-up milestones.
- Preserve the modified `print.prt`; never stage, restore, delete, or modify it.
- Retain final wheels and reports; remove only disposable staging and clean-install environments after verification.
- Use existing conda-managed dependencies; do not introduce a new pip/npm workflow.

---

## File Structure

- Modify `tools/packaging/test_wheel_install.py`
  - Add `--report` and emit machine-readable clean-install/check evidence.
- Create `tools/packaging/validate_windows_wheelhouse.py`
  - Validate exact wheel names, dependency closure, required/forbidden payloads, and hashes; combine clean-install evidence into the final report.
- Modify `tests/unitTest/packaging_tools_unit_test.py`
  - Cover the new clean-install report contract and update authored metadata.
- Create `tests/unitTest/windows_wheelhouse_validation_unit_test.py`
  - Cover success, missing/unexpected artifacts, unresolved DLLs, and APP payload rejection.
- Modify `ports/windows/pyisis/README.md`
  - Document the local M04 build, validation, output, and non-APP boundary.
- Create at build time `build/windows/reports/pyisis-wheel-install-isis9.json`
  - Clean-install command/check evidence; retained but ignored by Git.
- Create at build time `build/windows/reports/pyisis-wheelhouse-isis9-validation.json`
  - Final release-grade artifact and hash report; retained but ignored by Git.

---

### Task 1: Add structured clean-install evidence

**Files:**
- Modify: `tools/packaging/test_wheel_install.py`
- Modify: `tests/unitTest/packaging_tools_unit_test.py`
- Test: `tests/unitTest/packaging_tools_unit_test.py`

**Interfaces:**
- Consumes: existing `--wheelhouse`, `--venv`, `--package`, `--expected-isis-version`, and `--test-list` CLI arguments.
- Produces: optional `--report PATH`; JSON object with `schema_version`, `package`, `wheelhouse`, `venv`, `expected_isis_version`, `status`, and `checks`. Every check has `id`, `command`, `passed`, `failed`, `skipped`, and `exit_code`.

- [ ] **Step 1: Update test metadata and add a failing CLI contract test**

In `tests/unitTest/packaging_tools_unit_test.py`, change `Last Modified` to `2026-08-16`, append:

```text
Updated: 2026-08-16  Geng Xun added structured Windows wheel clean-install evidence coverage.
```

Extend `test_clean_venv_install_script_installs_from_wheelhouse` with exact source-contract assertions:

```python
self.assertIn('parser.add_argument("--report", type=Path)', script)
self.assertIn('"schema_version": 1', script)
self.assertIn('"status": "passed"', script)
self.assertIn('"checks": checks', script)
self.assertIn('args.report.write_text(', script)
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```powershell
& "D:\pyisis-win-env\python.exe" -m unittest `
  tests.unitTest.packaging_tools_unit_test.PackagingToolsUnitTest.test_clean_venv_install_script_installs_from_wheelhouse -v
```

Expected: FAIL because `test_wheel_install.py` does not define `--report` or write structured evidence.

- [ ] **Step 3: Implement the report contract**

In `tools/packaging/test_wheel_install.py`:

1. Import `json` and `shlex`.
2. Add:

```python
def _command_text(command: list[str]) -> str:
    return subprocess.list2cmdline(command) if sys.platform == "win32" else shlex.join(command)


def _passed_check(check_id: str, command: list[str]) -> dict[str, object]:
    return {
        "id": check_id,
        "command": _command_text(command),
        "passed": 1,
        "failed": 0,
        "skipped": 0,
        "exit_code": 0,
    }
```

3. Add `parser.add_argument("--report", type=Path)`.
4. Accumulate one check for wheel installation, one for fresh-process import/version validation, and one for each test module after its subprocess returns successfully. Use stable IDs `wheel-install`, `fresh-import`, and `unit-module:<module>`.
5. After all checks pass, write:

```python
payload = {
    "schema_version": 1,
    "package": args.package,
    "wheelhouse": str(args.wheelhouse.resolve()),
    "venv": str(args.venv.resolve()),
    "expected_isis_version": args.expected_isis_version,
    "status": "passed",
    "checks": checks,
}
if args.report:
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
```

Do not catch `CalledProcessError`; failed install/import/tests must retain the existing nonzero exit behavior and must not produce a passed report.

- [ ] **Step 4: Run focused packaging-tool tests**

Run:

```powershell
& "D:\pyisis-win-env\python.exe" -m unittest `
  tests.unitTest.packaging_tools_unit_test.PackagingToolsUnitTest.test_clean_venv_install_script_installs_from_wheelhouse `
  tests.unitTest.packaging_tools_unit_test.PackagingToolsUnitTest.test_clean_venv_install_script_selects_platform_python_path `
  tests.unitTest.packaging_tools_unit_test.PackagingToolsUnitTest.test_clean_venv_unit_test_environment_exposes_only_test_helpers `
  tests.unitTest.packaging_tools_unit_test.PackagingToolsUnitTest.test_clean_venv_verification_environment_removes_external_runtime -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit the clean-install evidence change**

```powershell
git add -- tools/packaging/test_wheel_install.py tests/unitTest/packaging_tools_unit_test.py
git commit -m "feat: report clean Windows wheel installs"
```

---

### Task 2: Add the Windows wheelhouse validator

**Files:**
- Create: `tools/packaging/validate_windows_wheelhouse.py`
- Create: `tests/unitTest/windows_wheelhouse_validation_unit_test.py`
- Test: `tests/unitTest/windows_wheelhouse_validation_unit_test.py`

**Interfaces:**
- Consumes: `validate_wheelhouse(wheelhouse: Path, clean_install_report: Path, package_version: str = "1.3.0rc2", python_abi: str = "cp312", platform_tag: str = "win_amd64", expected_isis_version: str = "9.0.0") -> dict[str, object]`.
- Produces: CLI `--wheelhouse`, `--clean-install-report`, `--report`, `--package-version`, `--python-abi`, `--platform-tag`, and `--expected-isis-version`; final JSON contains `schema_version`, target metadata, `status`, clean-install evidence, dependency evidence, and an `artifacts` list with path, size, and SHA-256.

- [ ] **Step 1: Create the unit-test metadata and fixture helper**

Create `tests/unitTest/windows_wheelhouse_validation_unit_test.py` with:

```python
"""Unit tests for Windows PyISIS wheelhouse release validation.

Author: Geng Xun
Created: 2026-08-16
Last Modified: 2026-08-16
Updated: 2026-08-16  Geng Xun added exact wheel, DLL closure, payload-boundary, and hash-report coverage.
"""
```

Load the validator with `importlib.util.spec_from_file_location`. Add a helper that creates three ZIP-format wheel fixtures with these payloads:

```python
main_members = ["isis_pybind/_isis_core.cp312-win_amd64.pyd"]
runtime_members = [
    "pyisis_runtime/vendor/isis/bin/isis.dll",
    "pyisis_runtime/vendor/isis/lib/Camera.plugin",
]
data_members = [
    "pyisis_isisdata_minimal/data/base/kernels/lsk/naif0012.tls",
]
```

Also write a dependency report with `{"schema_version": 1, "unresolved": []}` and a clean-install report with `status: "passed"`, `expected_isis_version: "9.0.0"`, and at least the `wheel-install` and `fresh-import` checks.

- [ ] **Step 2: Add four failing validator tests**

Add these concrete tests, using `_write_valid_fixture(root: Path) -> tuple[Path, Path]` to return the wheelhouse and clean-install report paths:

```python
def test_validate_wheelhouse_reports_exact_artifacts_and_hashes(self):
    with TemporaryDirectory() as temp_dir:
        wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
        report = self.validator.validate_wheelhouse(wheelhouse, clean_report)
    self.assertEqual(report["status"], "passed")
    self.assertEqual(len(report["artifacts"]), 4)
    self.assertTrue(
        all(re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) for item in report["artifacts"])
    )

def test_validate_wheelhouse_rejects_missing_or_unexpected_wheels(self):
    with TemporaryDirectory() as temp_dir:
        wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
        (wheelhouse / "usgs_pyisis_isisdata_minimal-1.3.0rc2-py3-none-any.whl").unlink()
        with self.assertRaisesRegex(FileNotFoundError, "exactly three wheels"):
            self.validator.validate_wheelhouse(wheelhouse, clean_report)
        (wheelhouse / "unexpected-1.0-py3-none-any.whl").write_bytes(b"unexpected")
        with self.assertRaisesRegex(FileNotFoundError, "exactly three wheels"):
            self.validator.validate_wheelhouse(wheelhouse, clean_report)

def test_validate_wheelhouse_rejects_unresolved_runtime_dependencies(self):
    with TemporaryDirectory() as temp_dir:
        wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
        dependency_report = wheelhouse / "usgs-pyisis-runtime-win64-dll-dependencies.json"
        dependency_report.write_text(
            json.dumps({"schema_version": 1, "unresolved": ["cspice.dll"]}),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(FileNotFoundError, "unresolved Windows runtime dependencies"):
            self.validator.validate_wheelhouse(wheelhouse, clean_report)

def test_validate_wheelhouse_rejects_app_executables_and_xml(self):
    with TemporaryDirectory() as temp_dir:
        wheelhouse, clean_report = self._write_valid_fixture(Path(temp_dir))
        runtime = wheelhouse / "usgs_pyisis_runtime_win64-1.3.0rc2-py3-none-win_amd64.whl"
        with zipfile.ZipFile(runtime, "a") as archive:
            archive.writestr("pyisis_runtime/vendor/isis/bin/reduce.exe", b"app")
        with self.assertRaisesRegex(ValueError, "forbidden ISIS APP payload"):
            self.validator.validate_wheelhouse(wheelhouse, clean_report)
```

The success test must assert status `passed`, exactly four hashed retained inputs (three wheels plus dependency JSON), and 64-character lowercase SHA-256 values. The negative tests must assert messages containing `exactly three wheels`, `unresolved Windows runtime dependencies`, and `forbidden ISIS APP payload` respectively.

- [ ] **Step 3: Run the new module and verify it fails**

Run:

```powershell
& "D:\pyisis-win-env\python.exe" -m unittest tests.unitTest.windows_wheelhouse_validation_unit_test -v
```

Expected: ERROR because `tools/packaging/validate_windows_wheelhouse.py` does not exist.

- [ ] **Step 4: Implement the validator**

Create `tools/packaging/validate_windows_wheelhouse.py`. Implement the hashing and ZIP-member helpers exactly as follows:

```python
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _wheel_members(wheel: Path) -> list[str]:
    with zipfile.ZipFile(wheel) as archive:
        return [member.filename for member in archive.infolist()]
```

Implement `_exact_artifacts` so it compares the set of `wheelhouse.glob("*.whl")` against the three exact paths below, raises `FileNotFoundError` with a message beginning `Expected exactly three wheels` for any missing or unexpected wheel, requires the dependency JSON, and returns `(binding, runtime, minimal, dependency)`.

Implement `validate_wheelhouse` with the exact signature declared in **Interfaces**. It must return a dictionary and must not write files itself; `main()` owns `--report` output.

Use these exact expected names:

```python
binding = f"usgs_pyisis-{package_version}-{python_abi}-{python_abi}-{platform_tag}.whl"
runtime = f"usgs_pyisis_runtime_win64-{package_version}-py3-none-{platform_tag}.whl"
minimal = f"usgs_pyisis_isisdata_minimal-{package_version}-py3-none-any.whl"
dependency = "usgs-pyisis-runtime-win64-dll-dependencies.json"
```

Require exactly three `*.whl` files. Require the main `.pyd`, runtime `isis.dll` and `Camera.plugin`, and minimal `naif0012.tls`. Reject runtime member names ending in `.exe` or `.xml`, or containing `/bin/xml/`. Load the dependency report and fail if `unresolved` is nonempty. Load the clean-install report and require status `passed` plus matching expected ISIS version. Hash files in 4 MiB chunks and sort artifact records by filename.

Implement the CLI to write `json.dumps(report, indent=2) + "\n"` to `--report` only after all validation succeeds.

- [ ] **Step 5: Run validator tests and adjacent staging coverage**

Run:

```powershell
& "D:\pyisis-win-env\python.exe" -m unittest `
  tests.unitTest.windows_wheelhouse_validation_unit_test `
  tests.unitTest.runtime_wheel_script_unit_test.RuntimeWheelScriptUnitTest.test_stage_runtime_copies_binding_runtime_and_excludes_apps_and_sdk_files `
  tests.unitTest.runtime_wheel_script_unit_test.RuntimeWheelScriptUnitTest.test_windows_dependency_closure_fails_on_unresolved_non_system_dll -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit the validator**

```powershell
git add -- tools/packaging/validate_windows_wheelhouse.py tests/unitTest/windows_wheelhouse_validation_unit_test.py
git commit -m "feat: validate Windows PyISIS wheelhouses"
```

---

### Task 3: Verify prerequisites and build the three-wheel wheelhouse

**Files:**
- Read: `build/windows/isis-prefix/lib/isis.dll`
- Read: `D:/pyisis-win-env/python.exe`
- Create: `build/windows/wheelhouse-isis9/*` (ignored build artifacts)

**Interfaces:**
- Consumes: verified M02 ISIS prefix and M01 CPython/MSVC environment.
- Produces: three wheel files and `usgs-pyisis-runtime-win64-dll-dependencies.json` in `build/windows/wheelhouse-isis9`.

- [ ] **Step 1: Re-read the execution goal and verify the working state**

Run:

```powershell
Get-Content -Raw docs\superpowers\specs\2026-08-16-windows-pyisis-wheelhouse-design.md
Get-Content -Raw docs\superpowers\plans\2026-08-16-windows-pyisis-wheelhouse.md
git status --short --branch
```

Expected: only M04 source changes plus the preserved unstaged `print.prt` are present.

- [ ] **Step 2: Verify exact prerequisites and hashes**

Run:

```powershell
& "D:\pyisis-win-env\python.exe" -c "import sys; assert sys.version_info[:2] == (3, 12); print(sys.version); print(sys.implementation.cache_tag)"
Get-FileHash -Algorithm SHA256 build\windows\isis-prefix\lib\isis.dll
Get-FileHash -Algorithm SHA256 D:\pyisis-win-env\python.exe
Test-Path tests\data\isisdata\mockup\base\kernels\lsk\naif0012.tls
```

Expected hashes: `isis.dll` is `7291ff4ae9683bdae8c758ae9e615eb9f5cfb23da9253ad15d45a69583044420`; Python is `32733c1f0c531b2a259a7003c9af5de6771427c4d7d90797a41d11d0ed708c90`; mock LSK exists.

- [ ] **Step 3: Run focused pre-build tests**

Run:

```powershell
& "D:\pyisis-win-env\python.exe" -m unittest `
  tests.unitTest.windows_wheelhouse_validation_unit_test `
  tests.unitTest.runtime_wheel_script_unit_test `
  tests.unitTest.python_packaging_unit_test `
  tests.unitTest.wheel_workflow_unit_test `
  tests.unitTest.packaging_tools_unit_test.PackagingToolsUnitTest.test_build_wheels_script_runs_all_local_wheel_steps `
  tests.unitTest.packaging_tools_unit_test.PackagingToolsUnitTest.test_clean_venv_install_script_installs_from_wheelhouse -v
```

Expected: all selected tests pass. Do not substitute the full `packaging_tools_unit_test` module: two pre-existing 149-versus-150 APP inventory assertions fail unchanged on the old `origin/main` baseline and are outside M04.

- [ ] **Step 4: Build the wheelhouse**

Ensure the dependency environment and MSVC tools are discoverable, then run:

```powershell
$env:CONDA_PREFIX = "D:\pyisis-win-env"
$env:PATH = "D:\pyisis-win-env;D:\pyisis-win-env\Scripts;D:\pyisis-win-env\Library\bin;D:\pyisis-win-env\Library\usr\bin;D:\pyisis-win-env\Library\mingw-w64\bin;D:\pyisis-win-env\bin;C:\Users\gx\miniconda3\Scripts;$env:PATH"
.\ports\windows\activate_msvc.ps1
& "D:\pyisis-win-env\python.exe" -c "import build, pybind11, scikit_build_core, wheel"
.\tools\packaging\build_wheels.ps1 `
  -IsisPrefix "$PWD\build\windows\isis-prefix" `
  -OutputDir "$PWD\build\windows\wheelhouse-isis9" `
  -PythonExecutable "D:\pyisis-win-env\python.exe" `
  -DependencyPrefix "D:\pyisis-win-env" `
  -BindingProjectDir "$PWD" `
  -PackageVersion "1.3.0rc2"
```

Expected: command exits 0 and prints exactly three wheels.

- [ ] **Step 5: Check artifact names and dependency closure immediately**

Run:

```powershell
Get-ChildItem build\windows\wheelhouse-isis9 -File | Sort-Object Name | Select-Object Name,Length
$dependency = Get-Content -Raw build\windows\wheelhouse-isis9\usgs-pyisis-runtime-win64-dll-dependencies.json | ConvertFrom-Json
if (@($dependency.unresolved).Count -ne 0) { throw "Unresolved DLLs: $($dependency.unresolved -join ', ')" }
```

Expected: three wheels plus one dependency JSON; unresolved count is zero.

---

### Task 4: Perform isolated install and generate final validation evidence

**Files:**
- Create: `build/windows/reports/pyisis-wheel-install-isis9.json`
- Create: `build/windows/reports/pyisis-wheelhouse-isis9-validation.json`
- Create then remove: `build/windows/pyisis-wheel-install-venv-20260816`

**Interfaces:**
- Consumes: Task 3 wheelhouse and Task 1 `--report` contract.
- Produces: clean-install and final wheelhouse JSON evidence required by the SPEC.

- [ ] **Step 1: Verify the clean venv target does not exist**

Run:

```powershell
$cleanVenv = (Join-Path $PWD "build\windows\pyisis-wheel-install-venv-20260816")
if (Test-Path -LiteralPath $cleanVenv) { throw "Refusing to reuse existing clean venv: $cleanVenv" }
```

Expected: no existing target.

- [ ] **Step 2: Run isolated wheel installation and basic tests**

Run:

```powershell
& "D:\pyisis-win-env\python.exe" tools\packaging\test_wheel_install.py `
  --wheelhouse "$PWD\build\windows\wheelhouse-isis9" `
  --venv "$PWD\build\windows\pyisis-wheel-install-venv-20260816" `
  --package "usgs-pyisis==1.3.0rc2" `
  --expected-isis-version "9.0.0" `
  --test-list tools\packaging\basic_tests.txt `
  --report "$PWD\build\windows\reports\pyisis-wheel-install-isis9.json"
```

Expected: install uses `--no-index --find-links`, fresh import succeeds, every listed module passes, and report status is `passed`.

- [ ] **Step 3: Generate the final wheelhouse validation report**

Run:

```powershell
& "D:\pyisis-win-env\python.exe" tools\packaging\validate_windows_wheelhouse.py `
  --wheelhouse "$PWD\build\windows\wheelhouse-isis9" `
  --clean-install-report "$PWD\build\windows\reports\pyisis-wheel-install-isis9.json" `
  --report "$PWD\build\windows\reports\pyisis-wheelhouse-isis9-validation.json" `
  --package-version "1.3.0rc2" `
  --python-abi "cp312" `
  --platform-tag "win_amd64" `
  --expected-isis-version "9.0.0"
```

Expected: status `passed`, exact wheel set accepted, no APP payloads, no unresolved DLLs, and all retained inputs have SHA-256 hashes.

- [ ] **Step 4: Verify the reports and wheel hashes independently**

Run:

```powershell
$install = Get-Content -Raw build\windows\reports\pyisis-wheel-install-isis9.json | ConvertFrom-Json
$final = Get-Content -Raw build\windows\reports\pyisis-wheelhouse-isis9-validation.json | ConvertFrom-Json
if ($install.status -ne "passed" -or $final.status -ne "passed") { throw "M04 validation report did not pass" }
Get-FileHash -Algorithm SHA256 build\windows\wheelhouse-isis9\*.whl
```

Expected: both reports pass and the independent hashes match the final report.

- [ ] **Step 5: Remove only the disposable clean-install venv and runtime staging**

Resolve and verify both targets are under the repository's `build` directory before removal:

```powershell
$buildRoot = (Resolve-Path "$PWD\build").Path
$targets = @(
  "$PWD\build\windows\pyisis-wheel-install-venv-20260816",
  "$PWD\build\packaging\usgs-pyisis-runtime-win64"
)
foreach ($target in $targets) {
  if (Test-Path -LiteralPath $target) {
    $resolved = (Resolve-Path -LiteralPath $target).Path
    if (-not $resolved.StartsWith($buildRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
      throw "Refusing to remove target outside build: $resolved"
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
  }
}
```

Retain the wheelhouse and both report JSON files.

---

### Task 5: Document M04 usage and run final verification

**Files:**
- Modify: `ports/windows/pyisis/README.md`
- Test: focused repository packaging tests and final artifact inspection

**Interfaces:**
- Consumes: verified commands and artifact paths from Tasks 3 and 4.
- Produces: reproducible developer instructions and final M04 completion handoff.

- [ ] **Step 1: Document build and clean-install commands**

Add a `## Windows wheelhouse` section to `ports/windows/pyisis/README.md` containing the exact Task 3 build command, Task 4 clean-install command, three expected wheel names, report paths, and this boundary statement:

```text
The PyISIS wheelhouse does not contain standalone ISIS APP executables or APP XML. Native applications such as reduce, jigsaw, and qnet are distributed separately.
```

- [ ] **Step 2: Run final focused source tests**

Run:

```powershell
& "D:\pyisis-win-env\python.exe" -m unittest `
  tests.unitTest.windows_wheelhouse_validation_unit_test `
  tests.unitTest.runtime_wheel_script_unit_test `
  tests.unitTest.python_packaging_unit_test `
  tests.unitTest.wheel_workflow_unit_test `
  tests.unitTest.packaging_tools_unit_test.PackagingToolsUnitTest.test_build_wheels_script_runs_all_local_wheel_steps `
  tests.unitTest.packaging_tools_unit_test.PackagingToolsUnitTest.test_clean_venv_install_script_installs_from_wheelhouse -v
```

Expected: all selected tests pass.

- [ ] **Step 3: Run final static and artifact checks**

Run:

```powershell
git diff --check
git status --short --branch
Get-ChildItem build\windows\wheelhouse-isis9 -File | Sort-Object Name | Select-Object Name,Length
Get-Content -Raw build\windows\reports\pyisis-wheelhouse-isis9-validation.json
```

Expected: no whitespace errors; only M04 source/docs changes and preserved `print.prt`; wheelhouse/report status remains passed.

- [ ] **Step 4: Commit documentation**

```powershell
git add -- ports/windows/pyisis/README.md
git commit -m "docs: document Windows PyISIS wheelhouse validation"
```

- [ ] **Step 5: Prepare completion evidence and checkpoint**

Record exact test pass/fail/skip counts, artifact hashes, prerequisite hashes, branch/worktree, commits, and classified Git status in the active `planning-with-files` progress file. Since the current milestone manager cannot append to the completed M01-M03 registry, do not edit `.planning/milestones.v1.json` or `.planning/milestone-index.md`; retain the M04 execution evidence in its dedicated plan directory and report this lifecycle limitation explicitly.

---

## M05 Handoff

After M04 completes, start a separate brainstorming session for the native ISIS Windows APP distribution described in `docs/superpowers/specs/2026-08-16-windows-pyisis-wheelhouse-design.md`. Do not choose ZIP versus installer, the exact APP inventory, or release mechanics during M04 execution.
