# `csv2table` Native APP Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the exceptional PyISIS `csv2table` facade and validate `csv2table` as an ordinary native ISIS APP on ISIS 9/10 across Windows/Linux.

**Architecture:** PyISIS exports only library bindings; it no longer discovers, launches, or links `csv2table`. The existing native APP manifest, source build, XML contract, and direct process smoke path become the sole implementation boundary. Generated API inventories classify the ISIS 10 header as `native-app`, while platform-specific validation records native help and `csv2table -> tabledump` behavior without translating diagnostics into Python exceptions.

**Tech Stack:** C++17/pybind11, Python 3 standard library and `unittest`, CMake, PowerShell 5.1+, native ISIS command-line applications, conda environments `asp360_new` and `asp370`.

## Global Constraints

- Do not expose `isis_pybind.csv2table`, `pyisis.csv2table`, `_isis_core._csv2table_native`, or a generic Python APP runner.
- Treat `csv2table` as a normal native APP in ISIS 9 Windows, ISIS 9 Linux, ISIS 10 Windows, and ISIS 10 Linux.
- Preserve native `KEY=VALUE` arguments, exit codes, stdout, and stderr; do not add Python error translation.
- Keep the Windows native APP archive separate from all PyISIS wheels.
- Use only conda-managed/build-provided dependencies; do not add pip or npm workflows.
- Keep automatically discovered API differences separate from curated binding disposition; classify `csv2table.h` as `native-app`, not `bound`.
- Do not promote manifest evidence beyond checks actually run for that exact ISIS version and operating system.
- Required platform cells pass with zero failures and zero skips before cross-platform support is declared complete.
- Do not modify `.gitignore` or `print.prt`; preserve unrelated work and stage only task files.
- Before editing matched paths, read every applicable `.github/instructions/*.instructions.md` file identified by `AGENTS.md`.

## File Responsibility Map

- `python/isis_pybind/__init__.py`: stop publishing the optional ISIS 10 facade.
- `python/isis_pybind/_csv2table.py`: delete the obsolete public facade implementation.
- `python/isis_pybind/_app_runner.py`: delete the csv2table-only process helper.
- `src/bind_isis10.cpp`: retain ISIS 10 class bindings while deleting the in-process APP adapter and csv2table-only metadata/includes.
- `CMakeLists.txt`: stop copying and installing both deleted Python modules.
- `tests/unitTest/csv2table_native_app_contract_unit_test.py`: enforce the negative PyISIS API/package boundary and positive native APP manifest contract.
- `tools/dev/generate_isis10_bind_inventory.py`: make `native-app` the regeneration source of truth for `csv2table`.
- `reference/isis10_bind_candidates/*`: generated ISIS 10 API inventory with no Python binding claim.
- `ports/windows/isis/windows-app-manifest.json`: per-version native APP build/smoke evidence only.
- `ports/windows/isis/windows-app-priority.csv` and `windows-app-priority.md`: regenerated 150-APP current-manifest view.
- `ports/windows/isis/test_isis_app_batch_smoke.ps1`: existing direct-process Windows help and `csv2table -> tabledump` behavior gate.
- `tools/dev/test_csv2table_native_app.py`: cross-platform development/CI validator that launches native executables and writes a version/OS-bound JSON result.
- `tests/unitTest/csv2table_native_app_smoke_unit_test.py`: fake-executable tests for the cross-platform validator's argument, exit-code, content, and report contract.
- Current README and compatibility documents: native invocation, migration, and supersession guidance.

---

### Task 1: Remove the PyISIS facade and in-process binding

**Files:**
- Create: `tests/unitTest/csv2table_native_app_contract_unit_test.py`
- Delete: `tests/unitTest/csv2table_facade_unit_test.py`
- Delete: `python/isis_pybind/_csv2table.py`
- Delete: `python/isis_pybind/_app_runner.py`
- Modify: `python/isis_pybind/__init__.py:532-540`
- Modify: `src/bind_isis10.cpp:1-153`
- Modify: `CMakeLists.txt:476-492,755-765`
- Modify: `tests/smoke_import.py:test_basic_symbols_present`

**Interfaces:**
- Produces: `isis_pybind` and `_isis_core` imports with no `csv2table` symbol on every ISIS version.
- Preserves: all existing ISIS 10-only class exports and their optional import behavior.
- Consumes: the native APP record named `csv2table` in `ports/windows/isis/windows-app-manifest.json`.

- [ ] **Step 1: Read the scoped pybind and Python-test instructions**

```powershell
Get-Content -Raw .github/instructions/pybind-cpp-metadata.instructions.md
Get-Content -Raw .github/instructions/pybind-file-header.instructions.md
Get-Content -Raw .github/instructions/isis-cpp-naming.instructions.md
Get-Content -Raw .github/instructions/pybind-python-test-metadata.instructions.md
Get-Content -Raw .github/instructions/pybind-metadata-common.instructions.md
Get-Content -Raw .github/instructions/pybind-testing.instructions.md
Get-Content -Raw .github/instructions/pybind-upstream-source-reading.instructions.md
Get-Content -Raw .github/instructions/pybind-conda-api-precedence.instructions.md
```

- [ ] **Step 2: Replace facade tests with a failing negative-boundary contract**

Create `csv2table_native_app_contract_unit_test.py` with repository metadata and these checks:

```python
class Csv2TableNativeAppContractUnitTest(unittest.TestCase):
    def test_python_facade_sources_are_absent(self) -> None:
        self.assertFalse((PROJECT_ROOT / "python/isis_pybind/_csv2table.py").exists())
        self.assertFalse((PROJECT_ROOT / "python/isis_pybind/_app_runner.py").exists())

    def test_build_does_not_package_facade_sources(self) -> None:
        cmake = (PROJECT_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        self.assertNotIn("_csv2table.py", cmake)
        self.assertNotIn("_app_runner.py", cmake)

    def test_cpp_binding_has_no_csv2table_adapter(self) -> None:
        source = (PROJECT_ROOT / "src/bind_isis10.cpp").read_text(encoding="utf-8")
        self.assertNotIn("_csv2table_native", source)
        self.assertNotIn("runCsv2TableNative", source)
        self.assertNotIn('#include "csv2table.h"', source)
        self.assertNotIn('#include "UserInterface.h"', source)

    def test_manifest_keeps_csv2table_as_a_native_app(self) -> None:
        payload = json.loads((PROJECT_ROOT / "ports/windows/isis/windows-app-manifest.json").read_text(encoding="utf-8"))
        app = next(item for item in payload["apps"] if item["name"] == "csv2table")
        self.assertEqual(app["xml"], "isis/src/base/apps/csv2table/csv2table.xml")
        self.assertEqual(set(app["versions"]), {"9.0.0", "10.0.0"})
```

Add to `tests/smoke_import.py::test_basic_symbols_present`:

```python
assert not hasattr(ip, "csv2table")
assert "csv2table" not in ip.__all__
assert not hasattr(ip._isis_core, "_csv2table_native")
```

- [ ] **Step 3: Run the new contract and verify it fails for the old facade**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.csv2table_native_app_contract_unit_test -v
```

Expected: FAIL because both Python modules, CMake entries, and C++ adapter still exist.

- [ ] **Step 4: Delete the exceptional facade and adapter**

Use `apply_patch` to delete both Python modules and the old facade test. Remove the `if _core_isis_major >= 10:` import block from `__init__.py`. In `bind_isis10.cpp`, remove only:

```cpp
// csv2table source metadata and 2026-08-02 update line
#include <vector>  // retain if another binding below still needs it
#include <QVector>
#include "csv2table.h"
#include "FileName.h"
#include "UserInterface.h"
void runCsv2TableNative(...)
m.def("_csv2table_native", ...)
```

Before removing shared headers such as `<vector>`, confirm remaining uses with:

```powershell
rg -n "std::vector|QVector|FileName|UserInterface|csv2table" src/bind_isis10.cpp
```

Remove every `_app_runner.py` and `_csv2table.py` build-tree copy/install entry from `CMakeLists.txt`; do not alter unrelated package files.

- [ ] **Step 5: Run the source-boundary test**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.csv2table_native_app_contract_unit_test -v
git diff --check
```

Expected: contract PASS and no whitespace errors. Do not run the import assertion
against a stale extension/package copy before Step 6 rebuilds it.

- [ ] **Step 6: Reconfigure/rebuild the active Windows target and repeat smoke import**

Use the same `Python3_EXECUTABLE`, `ISIS_PREFIX`, generator, architecture, and compiler recorded by the existing build tree. If its CMake cache is incompatible, use the corresponding documented Windows configure command rather than changing dependencies. Then run:

```powershell
cmake --build build --config Release --parallel 24
$env:ISISDATA = (Resolve-Path tests/data/isisdata/mockup)
$env:ISIS_PYBIND_BUILD_DIR = (Resolve-Path build/python)
D:/pyisis-win-env/python.exe tests/smoke_import.py
```

Expected: build succeeds and all three csv2table absence assertions pass.

- [ ] **Step 7: Commit the API-boundary change**

```powershell
git add CMakeLists.txt python/isis_pybind/__init__.py src/bind_isis10.cpp tests/smoke_import.py tests/unitTest/csv2table_native_app_contract_unit_test.py
git add -u -- python/isis_pybind/_csv2table.py python/isis_pybind/_app_runner.py tests/unitTest/csv2table_facade_unit_test.py
git commit -m "refactor: make csv2table a native app only"
```

### Task 2: Make generated inventories preserve `native-app` disposition

**Files:**
- Modify: `tests/unitTest/isis10_bind_inventory_unit_test.py:53-70`
- Modify: `tools/dev/generate_isis10_bind_inventory.py:197-216,309-315`
- Regenerate: `reference/isis10_bind_candidates/functions_inventory.csv`
- Regenerate: `reference/isis10_bind_candidates/raw_new_headers.csv`
- Modify: `reference/isis10_bind_candidates/README.md`
- Modify: `docs/isis9-isis10-binding-compatibility-plan.md`
- Modify: `docs/isis9-isis10-systematic-api-comparison.md`
- Modify: `README.md:210-230`

**Interfaces:**
- Produces: `HEADER_CLASSIFICATIONS["csv2table.h"].disposition == "native-app"`.
- Produces: a function inventory row whose Python binding is `N/A (native ISIS APP)`.
- Preserves: `csv2table` in the complete discovered ISIS 10 function/header inventory.

- [ ] **Step 1: Change the inventory test to the approved disposition**

```python
def test_application_headers_have_final_dispositions(self) -> None:
    classifications = inventory.HEADER_CLASSIFICATIONS
    for header in ("csv2table.h", "ocams2isis.h", "eisstitch.h"):
        self.assertEqual(classifications[header].disposition, "native-app")

def test_csv2table_inventory_does_not_advertise_a_python_binding(self) -> None:
    candidate = next(item for item in inventory.FUNCTION_CANDIDATES if item.function_name == "csv2table")
    self.assertEqual(candidate.proposed_python_name, "N/A (native ISIS APP)")
    self.assertIn("不新增", candidate.recommendation)
```

- [ ] **Step 2: Run the focused test and verify the old `bound` value fails**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.isis10_bind_inventory_unit_test -v
```

Expected: FAIL because `csv2table.h` is still `bound` and the candidate still names `isis_pybind.csv2table`.

- [ ] **Step 3: Update the generator source of truth and regenerate outputs**

Set the csv2table function candidate fields to:

```python
"N/A (native ISIS APP)",
"采用原生 ISIS APP 执行边界；ISIS 9/10 与 Windows/Linux 均不新增 Python wrapper 或进程内绑定",
"CSV 到 ISIS Table 的转换由安装的 csv2table 可执行程序提供。",
```

Set `HEADER_CLASSIFICATIONS["csv2table.h"]` to:

```python
HeaderClassification(
    "function",
    "native-app",
    "csv2table",
    "Use the native ISIS APP in every supported version/OS cell; do not bind UserInterface",
)
```

Regenerate with the exact installed ISIS 9/10 prefixes available on the executor:

```powershell
D:/pyisis-win-env/python.exe tools/dev/generate_isis10_bind_inventory.py --help
```

Use the displayed required prefix/source arguments and write to `reference/isis10_bind_candidates`. Do not hand-edit generated CSV fields after generation.

- [ ] **Step 4: Update current documentation and migration text**

Replace public Python examples with:

```text
Linux:  csv2table CSV=input.csv TO=target.cub TABLENAME=MyTable
Windows portable archive: launch\isis-app.cmd csv2table CSV=input.csv TO=target.cub TABLENAME=MyTable
```

State explicitly that Python orchestration may use the standard library's `subprocess`, but PyISIS publishes no helper. Mark `2026-08-02-csv2table-cross-platform-facade-design.md` historical/superseded without rewriting it.

- [ ] **Step 5: Verify regeneration and stale-current-doc removal**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.isis10_bind_inventory_unit_test -v
rg -n "isis_pybind\.csv2table|pyisis\.csv2table|_csv2table_native|跨平台 Python facade" README.md docs/isis9-isis10-binding-compatibility-plan.md docs/isis9-isis10-systematic-api-comparison.md reference/isis10_bind_candidates tools/dev/generate_isis10_bind_inventory.py
git diff --check
```

Expected: tests PASS; the search returns no active/current API claim. Historical spec/plan matches are allowed and are not edited.

- [ ] **Step 6: Commit inventory and documentation**

```powershell
git add README.md docs/isis9-isis10-binding-compatibility-plan.md docs/isis9-isis10-systematic-api-comparison.md reference/isis10_bind_candidates tools/dev/generate_isis10_bind_inventory.py tests/unitTest/isis10_bind_inventory_unit_test.py
git commit -m "docs: classify csv2table as native app"
```

### Task 3: Align the 150-APP Windows manifest baseline

**Approved execution amendment (2026-08-17):** If the pinned ISIS source
cannot be restored after bounded, integrity-checked attempts, extend
`rank_isis_apps.py` with `--refresh-manifest-only` and use the existing tracked
CSV as its source. This mode must update only `current_manifest` and
`recommended_wave`, recompute the summary from the resulting rows, preserve
all other CSV fields and row order byte-for-value, and fail if the existing CSV
does not contain every manifest APP. For newly selected rows set
`recommended_wave=W0-current-batch`; for deselected rows recover the wave by
calling the existing `wave()` function with the row's recorded portability,
importance, and GUI/module values. This is a deterministic derived-data refresh,
not permission to hand-edit generated artifacts or change ranking policy.

**Files:**
- Modify when the approved fallback is needed: `ports/windows/isis/rank_isis_apps.py`
- Modify: `tests/unitTest/packaging_tools_unit_test.py:300-315,500-595`
- Regenerate: `ports/windows/isis/windows-app-priority.csv`
- Regenerate: `ports/windows/isis/windows-app-priority.md`
- Modify only with evidence: `ports/windows/isis/windows-app-manifest.json:813-833`

**Interfaces:**
- Produces: exactly 150 `windows-app-manifest.json` application names, including `csv2table`.
- Produces: priority CSV row `csv2table.current_manifest == "yes"` and aggregate current-manifest count 150.
- Preserves: Windows batch smoke minimum of 150 and direct native `csv2table -> tabledump` checks.

- [ ] **Step 1: Update stale assertions to the tracked 150-APP contract**

Change only expectations derived from the manifest:

```python
self.assertEqual(len(apps), 150)
self.assertIn("$appNames.Count -lt 150", batch_smoke)
self.assertIn("Build and smoke-test 150 ISIS 10 APPs", workflow)
self.assertEqual(sum(row["current_manifest"] == "yes" for row in rows), 150)
self.assertIn("W0-current-batch | 150", summary)
```

Add:

```python
csv2table = next(row for row in rows if row["app"] == "csv2table")
self.assertEqual(csv2table["current_manifest"], "yes")
```

- [ ] **Step 2: Run packaging tests and verify stale generated priority data fails**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.packaging_tools_unit_test -v
```

Expected: only priority CSV/summary assertions fail until regeneration; the tracked manifest already contains 150 apps.

- [ ] **Step 3: Regenerate priority artifacts from the tracked manifest**

Read the tool's required source/ref arguments, then run it without modifying ranking policy:

```powershell
D:/pyisis-win-env/python.exe ports/windows/isis/rank_isis_apps.py --help
```

Pass the pinned upstream ISIS source, `ports/windows/isis/windows-app-manifest.json`, and the two tracked output paths. Confirm:

```powershell
Import-Csv ports/windows/isis/windows-app-priority.csv | Where-Object app -eq csv2table | Format-List app,current_manifest,recommended_wave
```

Expected: `current_manifest: yes`.

When fixed-source restoration has failed and the approved fallback is used,
first add a test fixture that snapshots every non-membership field, run it RED,
then invoke:

```powershell
D:/pyisis-win-env/python.exe ports/windows/isis/rank_isis_apps.py `
  --refresh-manifest-only `
  --manifest ports/windows/isis/windows-app-manifest.json `
  --csv-output ports/windows/isis/windows-app-priority.csv `
  --summary-output ports/windows/isis/windows-app-priority.md
```

Expected: 365 rows remain in the same order; only `csv2table` changes from
`current_manifest=no` to `yes` and from `W4-medium` to `W0-current-batch`;
the summary reports `W0-current-batch | 150`.

- [ ] **Step 4: Verify the Windows ISIS 9 executable before promoting its evidence**

```powershell
Test-Path build/windows/isis-prefix/bin/csv2table.exe
Test-Path build/windows/isis-prefix/bin/xml/csv2table.xml
.portswindowsisis	est_isis_app_batch_smoke.ps1 `
  -Prefix buildwindowsisis-prefix `
  -IsisVersion 9.0.0 `
  -InputCube testsdatahidtmgenorthoPSP_002118_1510_1m_o_forPDS_cropped.cub `
  -WorkDir buildwindowscsv2table-isis9-smoke
```

Expected: both files exist; all required batch checks pass, including direct `csv2table` and `tabledump` with exit code 0. Only then set ISIS 9 `build_status`/`smoke_status` to the repository's existing values representing installed and behavior-passed evidence. Leave ISIS 10 unchanged until its own run.

- [ ] **Step 5: Run focused baseline suites**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.packaging_tools_unit_test tests.unitTest.windows_isis_app_smoke_script_unit_test tests.unitTest.csv2table_native_app_contract_unit_test -v
git diff --check
```

Expected: all selected tests PASS.

- [ ] **Step 6: Commit the synchronized Windows baseline**

```powershell
git add tests/unitTest/packaging_tools_unit_test.py ports/windows/isis/windows-app-priority.csv ports/windows/isis/windows-app-priority.md ports/windows/isis/windows-app-manifest.json
git commit -m "fix: synchronize 150 app Windows inventory"
```

### Task 4: Add a native-process behavior validator

**Files:**
- Create: `tools/dev/test_csv2table_native_app.py`
- Create: `tests/unitTest/csv2table_native_app_smoke_unit_test.py`

**Interfaces:**
- Produces CLI: `test_csv2table_native_app.py --isis-version VERSION --input-cube PATH --work-dir PATH --report PATH [--bin-dir PATH]`.
- Executes: `csv2table -HELP`, then `csv2table CSV=... TO=... TABLENAME=PyIsisNativeAppProbe`, then `tabledump FROM=... NAME=PyIsisNativeAppProbe TO=...`.
- Produces schema-1 JSON containing OS, architecture, requested/reported ISIS version, resolved executable/XML paths, exact argument arrays, exit codes, pass/fail/skip counts, and SHA-256 of inputs/outputs.

- [ ] **Step 1: Read the scoped CLI/example instructions applicable to `tools/dev`**

Check the `applyTo` front matter. If `tools/dev/**` is not matched, follow repository Python style without importing unrelated example conventions.

```powershell
Get-Content -Raw .github/instructions/python-example-cli-naming.instructions.md
Get-Content -Raw .github/instructions/example-file-metadata.instructions.md
```

- [ ] **Step 2: Write failing fake-executable tests**

The test creates executable fixtures named `csv2table`/`tabledump` on POSIX and `.cmd` fixtures on Windows, or patches `subprocess.run` for platform-independent command assertions:

```python
def test_validator_uses_native_argument_arrays_and_writes_zero_skip_report(self):
    completed = subprocess.CompletedProcess
    side_effect = [
        completed(["csv2table", "-HELP"], 0, "help", ""),
        completed(["csv2table"], 0, "attached", ""),
        completed(["tabledump"], 0, "dumped", ""),
    ]
    with mock.patch.object(module.subprocess, "run", side_effect=side_effect) as run:
        report = module.validate_csv2table(config)
    self.assertEqual(run.call_args_list[1].args[0][1:], [
        f"CSV={config.csv_path}", f"TO={config.cube_path}", "TABLENAME=PyIsisNativeAppProbe",
    ])
    self.assertEqual(report["summary"], {"passed": 3, "failed": 0, "skipped": 0})
```

Also cover a nonzero native exit code, missing XML, missing executable, tabledump output without the expected table name, paths containing spaces, and atomic report writing.

- [ ] **Step 3: Run tests and verify missing-module failure**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.csv2table_native_app_smoke_unit_test -v
```

Expected: FAIL because the validator module does not exist.

- [ ] **Step 4: Implement the minimal validator**

Use `subprocess.run(argument_list, shell=False, text=True, capture_output=True)` and never join arguments into a shell command. Copy the input cube into `work-dir` before mutation. Write a header-bearing CSV such as:

```csv
Sample,Line,Name
1.0,2,alpha
3.5,4,beta
```

Resolve XML as `bin-dir/xml/csv2table.xml`; with no `--bin-dir`, resolve both executables using `shutil.which`. Fail if the XML cannot be resolved adjacent to the executable/runtime prefix. Treat every check as required: a missing prerequisite increments `failed`, not `skipped`. Write the report to a sibling `.tmp` and replace atomically.

- [ ] **Step 5: Run validator unit tests**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.csv2table_native_app_smoke_unit_test -v
git diff --check
```

Expected: all tests PASS and the command assertions show list arguments with `shell=False`.

- [ ] **Step 6: Commit the cross-platform native validator**

```powershell
git add tools/dev/test_csv2table_native_app.py tests/unitTest/csv2table_native_app_smoke_unit_test.py
git commit -m "test: validate native csv2table application"
```

### Task 5: Collect the four-cell build and behavior evidence

**Files:**
- Modify only after successful runs: `ports/windows/isis/windows-app-manifest.json`
- Create/retain as milestone evidence: `docs/superpowers/evidence/2026-08-17-csv2table-native-app-matrix.json`
- Modify: `README.md` or compatibility status table only to reflect completed cells.

**Interfaces:**
- Consumes: the validator from Task 4 and exact ISIS 9/10 environments/prefixes.
- Produces: four named cells `isis9-linux`, `isis9-windows`, `isis10-linux`, `isis10-windows`, each with build/package identity, OS/architecture, executable/XML SHA-256, commands, and zero-failure/zero-skip summary.

- [ ] **Step 1: Validate ISIS 9 Windows from the verified local prefix**

```powershell
D:/pyisis-win-env/python.exe tools/dev/test_csv2table_native_app.py `
  --isis-version 9.0.0 `
  --bin-dir build/windows/isis-prefix/bin `
  --input-cube tests/data/hidtmgen/ortho/PSP_002118_1510_1m_o_forPDS_cropped.cub `
  --work-dir build/windows/csv2table-matrix/isis9-windows `
  --report build/windows/csv2table-matrix/isis9-windows.json
```

Expected: report summary is exactly `passed=3, failed=0, skipped=0` and identifies Windows x86-64, ISIS 9.0.0, the executable, and XML hashes.

- [ ] **Step 2: Build/install and validate ISIS 10 Windows**

Use the existing Windows ISIS 10 source/build workflow with `csv2table` still in the 150-APP manifest:

```powershell
.portswindowsisis	est_isis_app_batch_smoke.ps1 `
  -Prefix buildwindowsisis10-app-prefix `
  -IsisVersion 10.0.0 `
  -InputCube testsdatahidtmgenorthoPSP_002118_1510_1m_o_forPDS_cropped.cub `
  -WorkDir buildwindowscsv2table-isis10-smoke
D:/pyisis-win-env/python.exe tools/dev/test_csv2table_native_app.py `
  --isis-version 10.0.0 `
  --bin-dir build/windows/isis10-app-prefix/bin `
  --input-cube tests/data/hidtmgen/ortho/PSP_002118_1510_1m_o_forPDS_cropped.cub `
  --work-dir build/windows/csv2table-matrix/isis10-windows `
  --report build/windows/csv2table-matrix/isis10-windows.json
```

Expected: source build/install and both behavior gates exit 0. Only then promote the ISIS 10 Windows manifest evidence.

- [ ] **Step 3: Validate ISIS 9 Linux in `asp360_new`**

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISROOT="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tools/dev/test_csv2table_native_app.py \
  --isis-version 9.0.0 \
  --bin-dir "$CONDA_PREFIX/bin" \
  --input-cube tests/data/hidtmgen/ortho/PSP_002118_1510_1m_o_forPDS_cropped.cub \
  --work-dir build/csv2table-matrix/isis9-linux \
  --report build/csv2table-matrix/isis9-linux.json
```

Expected: `passed=3, failed=0, skipped=0`; report records the exact conda package/build identity and Linux architecture.

- [ ] **Step 4: Validate ISIS 10 Linux in `asp370`**

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp370
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISROOT="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tools/dev/test_csv2table_native_app.py \
  --isis-version 10.0.0 \
  --bin-dir "$CONDA_PREFIX/bin" \
  --input-cube tests/data/hidtmgen/ortho/PSP_002118_1510_1m_o_forPDS_cropped.cub \
  --work-dir build/csv2table-matrix/isis10-linux \
  --report build/csv2table-matrix/isis10-linux.json
```

Expected: `passed=3, failed=0, skipped=0`; the environment still uses `csm 3.0.3.3` and the report records `isis 10.0.0 h1f94ec8_1`.

- [ ] **Step 5: Assemble and verify the tracked evidence summary**

Create `docs/superpowers/evidence/2026-08-17-csv2table-native-app-matrix.json` from the four raw reports. Store repository-relative commands and hashes, not machine-specific build trees. Validate:

```powershell
D:/pyisis-win-env/python.exe -c "import json,pathlib; p=pathlib.Path('docs/superpowers/evidence/2026-08-17-csv2table-native-app-matrix.json'); d=json.loads(p.read_text()); assert set(d['cells']) == {'isis9-linux','isis9-windows','isis10-linux','isis10-windows'}; assert all(c['summary'] == {'passed':3,'failed':0,'skipped':0} for c in d['cells'].values())"
```

Expected: exit 0. If any cell cannot be run, do not create a false passing entry and do not claim matrix completion.

- [ ] **Step 6: Run the complete focused regression set**

On Windows:

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.csv2table_native_app_contract_unit_test tests.unitTest.csv2table_native_app_smoke_unit_test tests.unitTest.isis10_bind_inventory_unit_test tests.unitTest.packaging_tools_unit_test tests.unitTest.windows_isis_app_smoke_script_unit_test -v
git diff --check
git status --short --branch
```

On Linux, repeat the first three modules in both `asp360_new` and `asp370`, then rebuild/import the extension in each environment using the repository `AGENTS.md` commands. Expected: every selected test and both imports PASS.

- [ ] **Step 7: Commit verified matrix evidence and final status**

```powershell
git add docs/superpowers/evidence/2026-08-17-csv2table-native-app-matrix.json ports/windows/isis/windows-app-manifest.json README.md docs/isis9-isis10-binding-compatibility-plan.md
git commit -m "test: verify csv2table native app matrix"
```

- [ ] **Step 8: Run completion verification**

Use `superpowers:verification-before-completion`. Re-run focused suites, inspect all four evidence summaries, confirm the removed source/package symbols with `rg`, and report exact pass/fail/skip counts. Remove disposable `build/**/csv2table-*` work directories only after resolving and retaining the tracked evidence and required build artifacts.
