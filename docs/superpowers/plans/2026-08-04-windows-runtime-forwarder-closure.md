# Windows Runtime Forwarder Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the shared ISIS 9/ISIS 10 Windows runtime staging closure copy DLLs referenced by PE export forwarders, including the omitted `openblas.dll` target.

**Architecture:** Add a focused `dumpbin /EXPORTS` parser and merge its results into the existing breadth-first dependency closure. Preserve relative copy locations, system-DLL filtering, pattern mode, package identities, and wheel versions.

**Tech Stack:** Python 3.12, `pathlib`, `re`, `subprocess`, `unittest`, `unittest.mock`, MSVC `dumpbin`.

## Global Constraints

- Apply through the shared script to both `usgs-pyisis-runtime-win64` and `usgs-pyisis-runtime-isis10-win64`.
- Discover forwarder targets generically; do not hard-code `openblas.dll`.
- Do not change versions, build wheels, publish releases, or replace assets.
- Do not change pattern-copy mode or copy the complete dependency prefix.
- Preserve current system-DLL filtering and discovery order.
- Set test metadata to `Last Modified: 2026-08-04` and append an `Updated:` line attributed to Geng Xun.

---

### Task 1: Parse PE export-forwarder targets

**Files:**
- Modify: `tests/unitTest/runtime_wheel_script_unit_test.py:1-180`
- Modify: `tools/packaging/stage_runtime_win64.py:51-134`

**Interfaces:**
- Consumes: a `Path` plus `SYSTEM_DLL_PREFIXES`, `SYSTEM_DLL_NAMES`, and `DEPENDENCY_NAME_RE`.
- Produces: `_dumpbin_forwarded_dependencies(binary: Path) -> tuple[str, ...]`.

- [ ] **Step 1: Write the failing parser test**

Update the test metadata and add this focused case using the file's existing dynamic-import pattern:

```python
def test_dumpbin_forwarded_dependencies_extracts_unique_non_system_dlls(self):
    spec = importlib.util.spec_from_file_location(
        "stage_runtime_win64_forwarder_parser",
        WINDOWS_STAGING_SCRIPT,
    )
    self.assertIsNotNone(spec)
    self.assertIsNotNone(spec.loader)
    stage_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage_module)
    completed = subprocess.CompletedProcess(
        ["dumpbin", "/EXPORTS", "libcblas.dll"],
        0,
        stdout=(
            "3 2 00000000 cblas_caxpy = openblas.dll.cblas_caxpy\n"
            "4 3 00000000 cblas_ccopy = openblas.dll.cblas_ccopy\n"
            "5 4 00000000 forwarded = KERNEL32.dll.Sleep\n"
        ),
        stderr="",
    )
    with mock.patch.object(stage_module.subprocess, "run", return_value=completed):
        result = stage_module._dumpbin_forwarded_dependencies(Path("libcblas.dll"))
    self.assertEqual(result, ("openblas.dll",))
```

- [ ] **Step 2: Verify RED**

```powershell
py -3.12 -m unittest tests.unitTest.runtime_wheel_script_unit_test.RuntimeWheelScriptUnitTest.test_dumpbin_forwarded_dependencies_extracts_unique_non_system_dlls -v
```

Expected: error because `_dumpbin_forwarded_dependencies` does not exist.

- [ ] **Step 3: Implement the minimal parser**

```python
FORWARDED_DLL_RE = re.compile(
    r"\b([A-Za-z0-9_.+\-]+\.dll)\.",
    re.IGNORECASE,
)


def _dumpbin_forwarded_dependencies(binary: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ["dumpbin", "/EXPORTS", str(binary)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ()

    dependencies = []
    seen = set()
    for match in FORWARDED_DLL_RE.finditer(result.stdout):
        name = match.group(1)
        normalized = name.lower()
        if normalized.startswith(SYSTEM_DLL_PREFIXES) or normalized in SYSTEM_DLL_NAMES:
            continue
        if normalized not in seen:
            seen.add(normalized)
            dependencies.append(name)
    return tuple(dependencies)
```

- [ ] **Step 4: Verify GREEN and commit**

Run the Step 2 command, then:

```powershell
git add tools/packaging/stage_runtime_win64.py tests/unitTest/runtime_wheel_script_unit_test.py
git commit -m "fix: parse Windows DLL export forwarders"
```

---

### Task 2: Traverse forwarded dependencies for ISIS 9 and ISIS 10

**Files:**
- Modify: `tests/unitTest/runtime_wheel_script_unit_test.py:135-200`
- Modify: `tools/packaging/stage_runtime_win64.py:135-161`

**Interfaces:**
- Consumes: `_dumpbin_dependencies(Path)` and `_dumpbin_forwarded_dependencies(Path)`.
- Produces: `_copy_dependency_closure(...)` that copies and recursively scans both dependency kinds.

- [ ] **Step 1: Write the failing closure test**

Add this complete regression test:

```python
def test_stage_runtime_closure_copies_forwarded_dependencies_for_both_windows_runtimes(self):
    spec = importlib.util.spec_from_file_location(
        "stage_runtime_win64_forwarder_closure",
        WINDOWS_STAGING_SCRIPT,
    )
    self.assertIsNotNone(spec)
    self.assertIsNotNone(spec.loader)
    stage_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage_module)

    with TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        prefix = temp / "isis-prefix"
        (prefix / "bin").mkdir(parents=True)
        (prefix / "lib").mkdir(parents=True)
        (prefix / "IsisPreferences").write_text(
            "Group = DataDirectory",
            encoding="utf-8",
        )
        (prefix / "lib" / "isis.dll").write_bytes(b"isis")
        (prefix / "lib" / "Camera.plugin").write_bytes(b"camera")

        dep_prefix = temp / "dep-prefix"
        dep_bin = dep_prefix / "Library" / "bin"
        dep_bin.mkdir(parents=True)
        (dep_bin / "libcblas.dll").write_bytes(b"cblas-forwarder")
        (dep_bin / "openblas.dll").write_bytes(b"openblas")
        (dep_bin / "vcruntime140.dll").write_bytes(b"vcruntime")

        def fake_dependencies(binary):
            if binary.name == "isis.dll":
                return ("libcblas.dll",)
            if binary.name == "openblas.dll":
                return ("vcruntime140.dll",)
            return ()

        def fake_forwarded_dependencies(binary):
            return ("openblas.dll",) if binary.name == "libcblas.dll" else ()

        releases = (
            ("usgs-pyisis-runtime-win64", "1.3.0rc2"),
            ("usgs-pyisis-runtime-isis10-win64", "1.4.0rc2"),
        )
        for distribution_name, package_version in releases:
            with self.subTest(distribution_name=distribution_name):
                stage = temp / distribution_name
                with (
                    mock.patch.object(
                        stage_module,
                        "_dumpbin_dependencies",
                        fake_dependencies,
                    ),
                    mock.patch.object(
                        stage_module,
                        "_dumpbin_forwarded_dependencies",
                        fake_forwarded_dependencies,
                    ),
                ):
                    stage_module.stage_runtime(
                        prefix,
                        stage,
                        (dep_prefix,),
                        dependency_copy_mode="closure",
                        distribution_name=distribution_name,
                        package_version=package_version,
                    )

                vendor_bin = (
                    stage
                    / "src"
                    / "pyisis_runtime"
                    / "vendor"
                    / "isis"
                    / "Library"
                    / "bin"
                )
                self.assertTrue((vendor_bin / "libcblas.dll").is_file())
                self.assertTrue((vendor_bin / "openblas.dll").is_file())
                self.assertTrue((vendor_bin / "vcruntime140.dll").is_file())
```

- [ ] **Step 2: Verify RED**

```powershell
py -3.12 -m unittest tests.unitTest.runtime_wheel_script_unit_test.RuntimeWheelScriptUnitTest.test_stage_runtime_closure_copies_forwarded_dependencies_for_both_windows_runtimes -v
```

Expected: failure because `openblas.dll` is absent.

- [ ] **Step 3: Merge both dependency sources**

```python
dependencies = dict.fromkeys(
    (*_dumpbin_dependencies(binary), *_dumpbin_forwarded_dependencies(binary))
)
for dependency_name in dependencies:
    resolved = index.get(dependency_name.lower())
    if resolved is None:
        continue
    source, dependency_prefix = resolved
    _copy_file(source, dependency_prefix, vendor_root)
    if str(source.resolve()).lower() not in visited:
        queue.append(source)
```

- [ ] **Step 4: Verify GREEN and the full staging module**

```powershell
py -3.12 -m unittest tests.unitTest.runtime_wheel_script_unit_test.RuntimeWheelScriptUnitTest.test_stage_runtime_closure_copies_forwarded_dependencies_for_both_windows_runtimes -v
py -3.12 -m unittest tests.unitTest.runtime_wheel_script_unit_test -v
```

Update `test_stage_runtime_closure_copies_only_resolved_dependency_dlls` so its existing patch block also contains:

```python
mock.patch.object(
    stage_module,
    "_dumpbin_forwarded_dependencies",
    return_value=(),
)
```

- [ ] **Step 5: Commit**

```powershell
git add tools/packaging/stage_runtime_win64.py tests/unitTest/runtime_wheel_script_unit_test.py
git commit -m "fix: stage forwarded Windows DLL dependencies"
```

---

### Task 3: Record the correction

**Files:**
- Modify: `packaging/runtime-win64/README.md:1-15`
- Modify: `docs/releases/v1.3.0rc2-isis9.0.0.md:24-36`
- Modify: `docs/releases/v1.4.0rc2-isis10.0.0.md:37-49`

**Interfaces:**
- Consumes: corrected shared staging behavior.
- Produces: packaging contract plus accurate ISIS 9/10 release-candidate records.

- [ ] **Step 1: Update the runtime README**

Add:

```markdown
## Dependency closure

The generated Windows runtime wheel includes the recursive closure of normal PE
imports and PE export-forwarder targets. Forwarder DLLs such as `libblas.dll`,
`libcblas.dll`, and `liblapack.dll` therefore also bring in their implementation
DLL, such as `openblas.dll`.
```

- [ ] **Step 2: Update the ISIS 9 rc2 record**

Add:

```markdown
## Windows runtime packaging correction

The original ISIS 9 rc2 Windows asset omitted `openblas.dll` because runtime
staging followed normal PE imports but not PE export-forwarder targets. Clean
installations could therefore fail while importing `isis_pybind._isis_core`.
The shared staging source now follows both dependency forms. This source-only
correction does not replace the archived rc2 wheelhouse.
```

- [ ] **Step 3: Update the ISIS 10 rc2 record**

Add:

```markdown
## Windows runtime packaging correction

The ISIS 10 Windows runtime used the same staging implementation that omitted
PE export-forwarder targets, so it was exposed to the same missing-runtime-DLL
class as the confirmed ISIS 9 `openblas.dll` failure. The shared staging source
now follows both normal imports and forwarded targets. This source-only
correction does not replace the archived rc2 wheelhouse; an ISIS 10 clean-install
failure was not separately reproduced for this record.
```

- [ ] **Step 4: Validate and commit documentation**

```powershell
rg -n "export-forwarder|openblas|source-only|archived" packaging/runtime-win64/README.md docs/releases/v1.3.0rc2-isis9.0.0.md docs/releases/v1.4.0rc2-isis10.0.0.md
git diff --check
git add packaging/runtime-win64/README.md docs/releases/v1.3.0rc2-isis9.0.0.md docs/releases/v1.4.0rc2-isis10.0.0.md
git commit -m "docs: record Windows runtime forwarder fix"
```

---

### Task 4: Final regression and scope verification

**Files:**
- Verify: `tools/packaging/stage_runtime_win64.py`
- Verify: `tests/unitTest/runtime_wheel_script_unit_test.py`
- Verify: `packaging/runtime-win64/README.md`
- Verify: `docs/releases/v1.3.0rc2-isis9.0.0.md`
- Verify: `docs/releases/v1.4.0rc2-isis10.0.0.md`

**Interfaces:**
- Consumes: Tasks 1-3.
- Produces: evidence that the fix is regression-safe and limited to scope.

- [ ] **Step 1: Run focused and full tests**

```powershell
py -3.12 -m unittest tests.unitTest.runtime_wheel_script_unit_test -v
py -3.12 -m unittest discover -s tests/unitTest -p "*_unit_test.py" -v
```

Expected: zero failures and errors. Report unrelated environment failures instead of changing unrelated code.

- [ ] **Step 2: Check syntax and diff quality**

```powershell
py -3.12 -m py_compile tools/packaging/stage_runtime_win64.py tests/unitTest/runtime_wheel_script_unit_test.py
git diff --check
git status --short --branch
git diff HEAD~3 -- tools/packaging/stage_runtime_win64.py tests/unitTest/runtime_wheel_script_unit_test.py packaging/runtime-win64/README.md docs/releases/v1.3.0rc2-isis9.0.0.md docs/releases/v1.4.0rc2-isis10.0.0.md
```

- [ ] **Step 3: Confirm release assets were not mutated**

Verify package versions, `wheelhouse/`, release ZIP files, and GitHub release assets were not modified or generated.

- [ ] **Step 4: Report completion evidence**

Report commit hashes, focused/full test counts, the generic forwarder fix, confirmed ISIS 9 impact, shared ISIS 10 coverage, and the absence of rebuilt assets.
