# PyISIS Windows Minimal Runtime Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure Windows PyISIS runtime wheels contain only the native libraries, plugins, and configuration required by `_isis_core`, never ISIS APP executables or APP XML.

**Architecture:** Keep `stage_runtime_win64.py` as the single Windows runtime-wheel staging entry point, but narrow its ISIS-prefix and dependency-prefix allowlists to DLLs, plugins, and root runtime metadata. Lock the boundary with a subprocess-level staging regression test so both pattern mode and the closure seed set reject executables and APP XML before later Native Apps packaging is introduced.

**Tech Stack:** Python 3.12/3.13, `pathlib`, `shutil`, `unittest`, PowerShell wheel orchestration, Windows PE dependency closure via `dumpbin`.

## Global Constraints

- PyISIS wheelhouse installation must remain self-contained and support direct `import isis_pybind` without a separately installed ISIS prefix.
- The minimal runtime may include `isis.dll`, required dependency DLLs, plugin files, `IsisPreferences`, `isis_version.txt`, and `LICENSE.md`.
- The minimal runtime must exclude every `.exe`, `bin/xml/**`, `Library/bin/xml/**`, SDK header, static library, and import library.
- Do not change the Linux runtime staging policy; Linux already excludes APP executables and uses official conda ISIS for native APP workflows.
- Do not add Native Runtime ZIP or Native Apps component packaging in this plan; those are separate independently testable subprojects.
- Preserve ISIS 9 and ISIS 10 distribution-name and package-version overrides.
- Update authored test metadata using `2026-08-05`, preserve earlier `Updated:` entries, and use `Geng Xun` as the author.
- Use conda-managed Python; do not introduce a new pip/npm workflow.
- Always set `ISISDATA` before running repository tests.
- Stage and commit only the files listed by the current task; never modify `.gitignore` or `print.prt`.

---

## File Structure

- Modify `tools/packaging/stage_runtime_win64.py`: narrow runtime copy patterns and dependency-closure seeds to the minimal binding runtime contract.
- Modify `tests/unitTest/runtime_wheel_script_unit_test.py`: add regression fixtures and assertions proving APP EXE/XML exclusion while preserving DLL/plugin/runtime metadata staging.
- Modify `packaging/runtime-win64/README.md`: document that the wheel is an internal PyISIS dependency and deliberately excludes Native Apps.

### Task 1: Enforce the minimal Windows runtime payload

**Files:**
- Modify: `tests/unitTest/runtime_wheel_script_unit_test.py`
- Modify: `tools/packaging/stage_runtime_win64.py`
- Modify: `packaging/runtime-win64/README.md`

**Interfaces:**
- Consumes: `stage_runtime(isis_prefix: Path, stage_dir: Path, dependency_prefixes: tuple[Path, ...] = (), dependency_copy_mode: str = "closure", distribution_name: str = "usgs-pyisis-runtime-win64", package_version: str = "1.3.0rc2") -> Path`.
- Produces: the same `stage_runtime(...) -> Path` API with a stricter payload contract; callers and CLI arguments remain unchanged.
- Produces: `RUNTIME_PATTERNS` containing only root metadata, DLLs, and plugin metadata.
- Produces: `DEPENDENCY_PATTERN_GLOBS` containing only DLL/plugin search patterns and no executable patterns.

- [ ] **Step 1: Extend the existing fixture with representative APP payloads**

In `tests/unitTest/runtime_wheel_script_unit_test.py`, preserve the existing module metadata and append:

```python
Updated: 2026-08-05  Geng Xun enforced the Windows minimal-runtime boundary against APP executables and XML.
```

Rename
`test_stage_runtime_copies_runtime_files_and_excludes_sdk_files` to
`test_stage_runtime_copies_binding_runtime_and_excludes_apps_and_sdk_files`.
In that test's ISIS prefix fixture, keep the existing `isis.exe` and
`bin/xml/stats.xml`, and add an explicit APP executable:

```python
(prefix / "bin" / "reduce.exe").write_bytes(b"app")
```

In the dependency-prefix fixture, add a non-library executable that must not be
copied by pattern mode:

```python
(dep_prefix / "Library" / "bin" / "qt-tool.exe").write_bytes(b"tool")
```

- [ ] **Step 2: Replace the old positive APP assertions with exclusion assertions**

In the same test, retain positive assertions for `isis.dll`, `Qt5Core.dll`,
`Camera.plugin`, `zlib.dll`, root metadata, distribution name, package version,
and `pyisis_runtime` discovery. Replace the existing positive assertions for
`isis.exe` and `stats.xml` with:

```python
self.assertFalse((vendor / "bin" / "isis.exe").exists())
self.assertFalse((vendor / "bin" / "reduce.exe").exists())
self.assertFalse((vendor / "bin" / "xml" / "stats.xml").exists())
self.assertFalse((vendor / "Library" / "bin" / "qt-tool.exe").exists())
self.assertEqual(list(vendor.rglob("*.exe")), [])
```

The final `rglob` assertion makes accidental executable additions fail even if
a future APP is installed under a different runtime subdirectory.

- [ ] **Step 3: Run the focused regression and confirm RED**

Run from the repository root in PowerShell:

```powershell
$env:ISISDATA = "$PWD\tests\data\isisdata\mockup"
python -m unittest `
  tests.unitTest.runtime_wheel_script_unit_test.RuntimeWheelScriptUnitTest.test_stage_runtime_copies_binding_runtime_and_excludes_apps_and_sdk_files `
  -v
```

Expected: FAIL because `vendor/bin/isis.exe`, `vendor/bin/reduce.exe`,
`vendor/bin/xml/stats.xml`, and `vendor/Library/bin/qt-tool.exe` are currently
copied.

- [ ] **Step 4: Narrow the Windows runtime allowlists**

In `tools/packaging/stage_runtime_win64.py`, replace `RUNTIME_PATTERNS` with:

```python
RUNTIME_PATTERNS = (
    "IsisPreferences",
    "isis_version.txt",
    "LICENSE.md",
    "bin/**/*.dll",
    "lib/**/*.dll",
    "lib/**/*.plugin",
    "Library/bin/**/*.dll",
    "Library/lib/**/*.dll",
    "Library/lib/**/*.plugin",
)
```

Replace `DEPENDENCY_PATTERN_GLOBS` with:

```python
DEPENDENCY_PATTERN_GLOBS = (
    "Library/bin/**/*.dll",
    "bin/**/*.dll",
    "Library/lib/**/*.dll",
    "Library/plugins/**/*.dll",
)
```

Do not add a filename blocklist. The positive allowlist is the contract and
continues to admit newly discovered dependency DLLs without knowing APP names.

- [ ] **Step 5: Remove executables from closure traversal seeds**

In `stage_runtime(...)`, change the closure seed predicate from:

```python
path.suffix.lower() in {".dll", ".exe", ".plugin"}
```

to:

```python
path.suffix.lower() in {".dll", ".plugin"}
```

This ensures `dumpbin` closure traversal starts only from libraries and plugin
metadata staged for `_isis_core`, not from any executable accidentally present
in a template or future source pattern.

- [ ] **Step 6: Run the focused regression and confirm GREEN**

Run:

```powershell
$env:ISISDATA = "$PWD\tests\data\isisdata\mockup"
python -m unittest `
  tests.unitTest.runtime_wheel_script_unit_test.RuntimeWheelScriptUnitTest.test_stage_runtime_copies_binding_runtime_and_excludes_apps_and_sdk_files `
  -v
```

Expected: PASS. Positive DLL/plugin assertions and all APP exclusion assertions
must succeed.

- [ ] **Step 7: Document the runtime-wheel boundary**

In `packaging/runtime-win64/README.md`, replace the opening description with:

```markdown
This package contains the minimal Windows x64 native runtime required by the
PyISIS binding wheel. It is generated from a verified ISIS prefix and includes
only the DLLs, plugins, configuration, and runtime resources needed to import
and use `isis_pybind`.

It intentionally excludes ISIS APP executables and APP XML. Native command-line
and GUI applications are built, tested, and released through the separate ISIS
Native Windows product line. It also excludes SDK headers, import libraries,
CMake metadata, and local build files.
```

Keep the existing `pyisis_runtime.prefix()` and `dll_directories()` usage
example unchanged.

- [ ] **Step 8: Run the complete runtime-staging unit module**

Run:

```powershell
$env:ISISDATA = "$PWD\tests\data\isisdata\mockup"
python -m unittest tests.unitTest.runtime_wheel_script_unit_test -v
```

Expected: all Windows and Linux runtime-staging tests PASS, including PE
forwarder closure, Linux conda allowlisting, SONAME aliases, and size-budget
checks.

- [ ] **Step 9: Run the adjacent Windows wheel-orchestration test**

Run:

```powershell
$env:ISISDATA = "$PWD\tests\data\isisdata\mockup"
python -m unittest `
  tests.unitTest.packaging_tools_unit_test.PackagingToolsUnitTest.test_build_wheels_script_runs_all_local_wheel_steps `
  -v
```

Expected: PASS, confirming that the Windows wheel builder still invokes
`stage_runtime_win64.py` with the existing ISIS prefix, dependency prefix,
distribution identity, and output-stage arguments. Do not run or change APP
manifest/workflow assertions in this runtime-boundary task; the current
149-versus-150 count mismatch belongs to the Native Apps plan.

- [ ] **Step 10: Verify the exact diff and commit**

Run:

```powershell
git diff --check
git status --short
git diff -- tools/packaging/stage_runtime_win64.py `
  tests/unitTest/runtime_wheel_script_unit_test.py `
  packaging/runtime-win64/README.md
git add -- tools/packaging/stage_runtime_win64.py `
  tests/unitTest/runtime_wheel_script_unit_test.py `
  packaging/runtime-win64/README.md
git commit -m "packaging: isolate Windows PyISIS runtime"
```

Expected: the commit contains exactly the three listed files. `.gitignore`,
`print.prt`, APP manifests, workflows, and unrelated working-tree changes are
absent.

## Follow-up Plans

Implement these as separate plans after this boundary is merged:

1. Windows Native Runtime and `reduce` APP component staging, manifests,
   activation, and clean-extract verification.
2. Linux conda versus Windows `reduce` behavioral and numerical comparison.
3. Windows Native workflow artifact assembly, hashes, provenance, and release
   publishing.
4. Gradual evidence-based promotion of the existing APP inventory; GUI remains
   a separate design and implementation cycle.
