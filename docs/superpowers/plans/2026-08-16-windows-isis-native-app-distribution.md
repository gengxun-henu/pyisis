# Windows ISIS 9 Native APP Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and validate one zero-install Windows 11 x64 ZIP containing exactly the tracked 150 ISIS 9 CLI APPs plus `qnet`, their curated runtime closure, launchers, and minimum ISISDATA.

**Architecture:** A tracked release contract composes the existing 150-APP manifest with `qnet` and the `isisui` helper. A manifest-driven stager reuses a shared PE dependency walker, copies only approved runtime/resources, generates relative-path launchers and hashes, and feeds a deterministic archiver. Static validation and a scrubbed clean-extraction PowerShell matrix jointly produce the release report.

**Tech Stack:** Python 3.12 standard library, PowerShell 5.1+, MSVC `dumpbin`, `unittest`, JSON schema-1 reports, deterministic ZIP, SHA-256.

## Global Constraints

- Target only ISIS 9.0.0 on Windows 11 x64; do not claim Windows 10 or ARM64 support.
- Use conda-managed/build-provided dependencies; do not introduce pip or npm workflows.
- The public inventory is exactly the 150 names in `ports/windows/isis/windows-app-manifest.json` at normalized-LF SHA-256 `bca645e1bf9ba3594ef48be0cb3fbec642a98da1e6f1b91b31a4aaa9519987d5`, plus `qnet`. Normalize CRLF/CR to LF before hashing so the contract is stable across Git checkout platforms.
- Keep standalone APP executables and XML out of all PyISIS wheels.
- Produce one ZIP; do not copy the complete development prefix or split the release across dependent archives.
- Bundle repository-owned minimal ISISDATA and preserve a valid external `ISISDATA` override.
- Use `isis-shell.cmd`, `isis-app.cmd <name> [arguments]`, and `qnet.cmd`; do not generate 151 wrappers or require manual PATH edits.
- Fail on unresolved non-system DLLs, missing resources, inventory drift, unexpected public EXEs, forbidden content, unsafe ZIP paths, absolute build/conda paths, or hash mismatches.
- Do not modify `.gitignore` or `print.prt`; preserve unrelated work and stage only task files.
- Before editing `tests/unitTest/**/*.py`, follow `.github/instructions/pybind-python-test-metadata.instructions.md` and `.github/instructions/pybind-metadata-common.instructions.md`.

## File Responsibility Map

- `tools/packaging/windows_pe_dependencies.py`: shared dumpbin parsing and recursive dependency report/copy engine.
- `tools/packaging/stage_runtime_win64.py`: existing wheel stager changed only to consume the shared PE helper.
- `packaging/native-apps-win64/release.json`: release identity, source-manifest binding, GUI APP/helper lists, plugin allowlist, forbidden paths.
- `tools/packaging/windows_native_app_manifest.py`: typed release-contract validation and 151-APP composition.
- `packaging/native-apps-win64/launch/*.cmd`: relative environment, shell, generic APP, and qnet launch templates.
- `packaging/native-apps-win64/launch/isis-launch.ps1`: internal argv-preserving worker used by the public APP and qnet CMD shims; it never evaluates a reconstructed command string.
- `tools/packaging/stage_windows_native_apps.py`: curated payload staging and generated manifests.
- `tools/packaging/archive_windows_native_apps.py`: normalized hashes and deterministic ZIP creation.
- `tools/packaging/validate_windows_native_apps.py`: ZIP, boundary, evidence, inventory, dependency, and hash validation.
- `ports/windows/isis/test_isis_native_app_package.ps1`: clean extraction, CLI/GUI/data/negative runtime matrix.
- `tools/packaging/build_windows_native_apps.ps1`: stage/archive/test/validate orchestration and guarded cleanup.
- Four focused `tests/unitTest/windows_native_app*_unit_test.py` modules: manifest, staging, validation, and PowerShell workflow contracts.
- `ports/windows/README.md` and `ports/windows/isis/README.md`: developer and end-user instructions.

---

### Task 1: Extract the shared Windows PE dependency engine

**Files:**
- Create: `tools/packaging/windows_pe_dependencies.py`
- Modify: `tools/packaging/stage_runtime_win64.py`
- Modify: `tests/unitTest/runtime_wheel_script_unit_test.py`

**Interfaces:**
- Produces: `dumpbin_dependencies(Path) -> tuple[str, ...]`.
- Produces: `dumpbin_forwarded_dependencies(Path) -> tuple[str, ...]`.
- Produces: `copy_dependency_closure(seed_files, dependency_prefixes, target_root, dependency_report=None) -> dict[str, object]`.
- Preserves the three existing underscore-prefixed names in `stage_runtime_win64.py` as compatibility aliases.

- [ ] **Step 1: Write the failing shared-helper regression test**

Update test metadata, load the new helper, fake direct/forwarded dumpbin results, and assert provenance:

```python
def test_shared_pe_closure_records_forwarder_provenance(self):
    module = self._load_module("windows_pe_dependencies", WINDOWS_PE_SCRIPT)
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        prefix = root / "deps"
        target = root / "stage"
        seed = root / "reduce.exe"
        (prefix / "bin").mkdir(parents=True)
        target.mkdir()
        seed.write_bytes(b"exe")
        (prefix / "bin" / "isis.dll").write_bytes(b"isis")
        (prefix / "bin" / "openblas.dll").write_bytes(b"blas")
        direct = {"reduce.exe": ("isis.dll",), "isis.dll": ()}
        forwarded = {"reduce.exe": ("openblas.dll",), "openblas.dll": ()}
        with mock.patch.object(module, "dumpbin_dependencies", side_effect=lambda p: direct.get(p.name, ())), mock.patch.object(module, "dumpbin_forwarded_dependencies", side_effect=lambda p: forwarded.get(p.name, ())):
            report = module.copy_dependency_closure((seed,), (prefix,), target)
        self.assertEqual(report["unresolved"], [])
        openblas = next(item for item in report["files"] if item["name"] == "openblas.dll")
        self.assertEqual(openblas["import_kind"], "forwarder")
        self.assertEqual(openblas["parents"], ["reduce.exe"])
```

- [ ] **Step 2: Run the test and verify the missing-module failure**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.runtime_wheel_script_unit_test -v
```

Expected: FAIL because `windows_pe_dependencies.py` does not exist.

- [ ] **Step 3: Move the existing tolerant dumpbin and closure logic into public helpers**

Keep the current system-DLL allowlist and UTF-8 `errors="replace"`. Make report ordering deterministic and add source/import provenance:

```python
report = {
    "schema_version": 1,
    "binaries": sorted(binaries, key=lambda item: item["binary"].lower()),
    "files": sorted(files.values(), key=lambda item: item["name"].lower()),
    "unresolved": sorted(unresolved, key=str.lower),
}
if dependency_report is not None:
    dependency_report.parent.mkdir(parents=True, exist_ok=True)
    dependency_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
if unresolved:
    raise FileNotFoundError("Unresolved Windows runtime dependencies: " + ", ".join(report["unresolved"]))
return report
```

Import and alias in `stage_runtime_win64.py`. Use the package import for unit
tests and the sibling import when the file runs directly; update existing mocks
to patch the shared module functions instead of assuming closure-local globals:

```python
try:
    from tools.packaging.windows_pe_dependencies import copy_dependency_closure, dumpbin_dependencies, dumpbin_forwarded_dependencies
except ModuleNotFoundError:
    from windows_pe_dependencies import copy_dependency_closure, dumpbin_dependencies, dumpbin_forwarded_dependencies

_copy_dependency_closure = copy_dependency_closure
_dumpbin_dependencies = dumpbin_dependencies
_dumpbin_forwarded_dependencies = dumpbin_forwarded_dependencies
```

- [ ] **Step 4: Run Windows runtime staging regressions**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.runtime_wheel_script_unit_test tests.unitTest.packaging_tools_unit_test -v
```

Expected: all selected tests PASS, including unresolved and forwarder cases.

- [ ] **Step 5: Commit**

```powershell
git add tools/packaging/windows_pe_dependencies.py tools/packaging/stage_runtime_win64.py tests/unitTest/runtime_wheel_script_unit_test.py
git commit -m "refactor: share Windows PE dependency closure"
```

### Task 2: Lock and validate the 151-APP release contract

**Files:**
- Create: `packaging/native-apps-win64/release.json`
- Create: `packaging/native-apps-win64/README.md`
- Create: `tools/packaging/windows_native_app_manifest.py`
- Create: `tests/unitTest/windows_native_app_manifest_unit_test.py`

**Interfaces:**
- Produces immutable `ReleaseContract` fields for identity, CLI/GUI APPs, helpers, plugin globs, and forbidden globs.
- Produces `load_release_contract(release_path: Path, cli_manifest_path: Path) -> ReleaseContract`.

- [ ] **Step 1: Write fail-closed release-contract tests**

```python
def test_repository_contract_resolves_exact_public_inventory(self):
    contract = self.module.load_release_contract(RELEASE_CONFIG, CLI_MANIFEST)
    self.assertEqual(contract.isis_version, "9.0.0")
    self.assertEqual(len(contract.public_cli_apps), 150)
    self.assertEqual(contract.public_gui_apps, ("qnet",))
    self.assertEqual(len(contract.public_apps), 151)
    self.assertTrue({"reduce", "jigsaw", "qnet"} <= set(contract.public_apps))
    self.assertEqual(contract.runtime_helpers, ("isisui",))

def test_cli_manifest_hash_drift_is_fatal(self):
    with TemporaryDirectory() as temp_dir:
        changed = Path(temp_dir) / "windows-app-manifest.json"
        changed.write_text('{"schema_version": 1, "apps": []}\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.module.load_release_contract(RELEASE_CONFIG, changed)
```

- [ ] **Step 2: Run tests and verify the missing contract/parser failure**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.windows_native_app_manifest_unit_test -v
```

Expected: FAIL because the release config/parser do not exist.

- [ ] **Step 3: Add the schema-1 contract and strict typed parser**

`release.json` must contain this identity/boundary:

```json
{
  "schema_version": 1,
  "distribution": "usgs-isis-native-apps",
  "isis_version": "9.0.0",
  "platform": "win64",
  "archive_name": "usgs-isis-native-apps-9.0.0-win64.zip",
  "root_name": "usgs-isis-native-apps-9.0.0-win64",
  "cli_manifest": "ports/windows/isis/windows-app-manifest.json",
  "cli_manifest_sha256": "bca645e1bf9ba3594ef48be0cb3fbec642a98da1e6f1b91b31a4aaa9519987d5",
  "public_gui_apps": ["qnet"],
  "runtime_helpers": ["isisui"],
  "mandatory_apps": ["reduce", "jigsaw", "qnet"],
  "qt_plugin_globs": ["Library/plugins/platforms/qwindows.dll", "Library/plugins/imageformats/*.dll", "Library/plugins/styles/*.dll"],
  "forbidden_globs": ["include/**", "lib/**/*.lib", "lib/**/*.a", "lib/cmake/**", "make/**", "**/*.whl", "**/CMakeCache.txt"]
}
```

The parser validates exact keys/types, manifest hash, 150 unique lower-case names, ISIS 9 `supported` plus `compiled_installed`, no overlap with GUI/helper names, and mandatory membership.

```python
@dataclass(frozen=True)
class ReleaseContract:
    distribution: str
    isis_version: str
    platform: str
    archive_name: str
    root_name: str
    public_cli_apps: tuple[str, ...]
    public_gui_apps: tuple[str, ...]
    runtime_helpers: tuple[str, ...]
    mandatory_apps: tuple[str, ...]
    qt_plugin_globs: tuple[str, ...]
    forbidden_globs: tuple[str, ...]

    @property
    def public_apps(self) -> tuple[str, ...]:
        return tuple(sorted((*self.public_cli_apps, *self.public_gui_apps)))
```

- [ ] **Step 4: Run tests and the CLI contract check**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.windows_native_app_manifest_unit_test -v
D:/pyisis-win-env/python.exe tools/packaging/windows_native_app_manifest.py --release packaging/native-apps-win64/release.json --cli-manifest ports/windows/isis/windows-app-manifest.json --check
```

Expected: PASS and `151 public APPs validated`.

- [ ] **Step 5: Commit**

```powershell
git add packaging/native-apps-win64 tools/packaging/windows_native_app_manifest.py tests/unitTest/windows_native_app_manifest_unit_test.py
git commit -m "feat: define Windows native app release contract"
```

### Task 3: Add package-relative launchers

**Files:**
- Create: `packaging/native-apps-win64/launch/isis-env.cmd`
- Create: `packaging/native-apps-win64/launch/isis-shell.cmd`
- Create: `packaging/native-apps-win64/launch/isis-app.cmd`
- Create: `packaging/native-apps-win64/launch/qnet.cmd`
- Create: `packaging/native-apps-win64/launch/isis-launch.ps1`
- Create: `tests/unitTest/windows_native_app_staging_unit_test.py`

**Interfaces:**
- `isis-env.cmd` applies package-relative runtime variables and fails for an explicitly invalid `ISISDATA`.
- `isis-app.cmd <name> [arguments]` validates exact public membership and invokes without string re-evaluation.
- `isis-shell.cmd` opens an initialized shell; `qnet.cmd` delegates to the generic launcher.
- With delayed expansion disabled, each public CMD shim captures the already parsed `%~1` values into indexed environment slots and then launches `isis-launch.ps1` without reinserting `%*` into another command line. The worker rebuilds the argv array from those slots and launches with PowerShell splatting, preserving arbitrary argument counts, empty values, literal quotes, backslashes, and metacharacters without `call`, `cmd /c`, or string evaluation.

- [ ] **Step 1: Write launcher safety and execution tests**

```python
def test_launchers_are_relative_and_do_not_reference_conda_or_build_prefix(self):
    for name in ("isis-env.cmd", "isis-shell.cmd", "isis-app.cmd", "qnet.cmd"):
        text = (LAUNCH_ROOT / name).read_text(encoding="utf-8")
        self.assertIn("%~dp0", text)
        self.assertNotIn("CONDA_PREFIX", text.upper())
        self.assertNotRegex(text, r"(?i)[A-Z]:\\(?:code|miniconda|pyisis-win-env)")

def test_generic_launcher_rejects_non_public_helper(self):
    package = self._write_launcher_fixture()
    result = subprocess.run(["cmd", "/d", "/c", str(package / "launch" / "isis-app.cmd"), "isisui"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    self.assertEqual(result.returncode, 4)
    self.assertIn("not a public ISIS APP", result.stderr)
```

- [ ] **Step 2: Run tests and verify missing-template failures**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.windows_native_app_staging_unit_test -v
```

Expected: FAIL because the templates do not exist.

- [ ] **Step 3: Implement one shared environment launcher and three thin callers**

Core `isis-env.cmd` content:

```batch
@echo off
set "ISIS_PACKAGE_ROOT=%~dp0.."
for %%I in ("%ISIS_PACKAGE_ROOT%") do set "ISIS_PACKAGE_ROOT=%%~fI"
if defined ISISDATA (
  if not exist "%ISISDATA%\" (
    >&2 echo Explicit ISISDATA directory does not exist: %ISISDATA%
    exit /b 3
  )
) else (
  set "ISISDATA=%ISIS_PACKAGE_ROOT%\data"
)
set "ISISROOT=%ISIS_PACKAGE_ROOT%"
set "ISIS_PREFIX=%ISIS_PACKAGE_ROOT%"
set "QT_PLUGIN_PATH=%ISIS_PACKAGE_ROOT%\plugins"
set "PATH=%ISIS_PACKAGE_ROOT%\bin;%ISIS_PACKAGE_ROOT%\lib;%PATH%"
exit /b 0
```

`isis-app.cmd` and `qnet.cmd` capture each already parsed argument into indexed
environment slots with delayed expansion disabled, then invoke the internal
`isis-launch.ps1` worker without reinserting `%*` into a new command line. The
worker validates names against `public_apps`, applies the package-relative
environment, and invokes the selected executable with array splatting.
`isis-shell.cmd` calls `isis-env.cmd` then `cmd /k`.

- [ ] **Step 4: Run launcher tests from a path containing spaces**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.windows_native_app_staging_unit_test -v
```

Expected: all tests PASS in the fixture directory `native package with spaces`.

- [ ] **Step 5: Commit**

```powershell
git add packaging/native-apps-win64/launch tests/unitTest/windows_native_app_staging_unit_test.py
git commit -m "feat: add portable ISIS app launchers"
```

### Task 4: Stage the curated payload and create a deterministic archive

**Files:**
- Create: `tools/packaging/stage_windows_native_apps.py`
- Create: `tools/packaging/archive_windows_native_apps.py`
- Modify: `tests/unitTest/windows_native_app_staging_unit_test.py`

**Interfaces:**
- Consumes `ReleaseContract` and `copy_dependency_closure` from Tasks 1-2.
- Produces `StageResult(root, apps_manifest, files_manifest, dependency_report)`.
- Produces `stage_native_apps(isis_prefix, dependency_prefixes, minimal_data_root, release_contract, stage_parent, dependency_report) -> StageResult`.
- Produces `create_deterministic_zip(stage_root, archive_path) -> dict[str, object]`.

- [ ] **Step 1: Add failing staging and deterministic-archive tests**

Construct a small prefix fixture with CLI/GUI/helper EXEs, XML, resources,
minimal data, DLLs, Qt plugins, and an unlisted EXE:

```python
def test_stage_copies_only_declared_payload_and_hashes_every_file(self):
    fixture = self._write_stage_fixture()
    with mock.patch.object(self.stage_module, "copy_dependency_closure", side_effect=self._fake_dependency_closure):
        result = self.stage_module.stage_native_apps(
            fixture.isis_prefix, (fixture.dependency_prefix,), fixture.minimal_data,
            fixture.contract, fixture.output, fixture.dependency_report,
        )
    self.assertTrue((result.root / "bin" / "reduce.exe").is_file())
    self.assertTrue((result.root / "bin" / "qnet.exe").is_file())
    self.assertTrue((result.root / "bin" / "isisui.exe").is_file())
    self.assertFalse((result.root / "bin" / "unlisted.exe").exists())
    self.assertFalse((result.root / "include").exists())
    apps = json.loads(result.apps_manifest.read_text(encoding="utf-8"))
    self.assertEqual(apps["public_apps"], ["qnet", "reduce"])
    self._assert_every_payload_file_hashed(result.root, result.files_manifest)

def test_deterministic_zip_is_byte_reproducible(self):
    stage = self._write_archive_fixture()
    first = self.archive_module.create_deterministic_zip(stage, stage.parent / "a.zip")
    second = self.archive_module.create_deterministic_zip(stage, stage.parent / "b.zip")
    self.assertEqual(first["sha256"], second["sha256"])
    self.assertEqual((stage.parent / "a.zip").read_bytes(), (stage.parent / "b.zip").read_bytes())
```

- [ ] **Step 2: Run tests and verify missing-stager failures**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.windows_native_app_staging_unit_test -v
```

Expected: FAIL because the staging and archiving modules do not exist.

- [ ] **Step 3: Implement fail-closed staging**

Resolve every source/destination and require it to remain below its declared
root. Copy all public EXEs, CLI XML to `bin/xml`, `qnet.exe`, `isisui.exe`,
`IsisPreferences`, licenses, appdata, minimal data, and explicit Qt plugins.
Seed PE closure with public/helper EXEs plus `isis.dll`. Reject forbidden globs
and absolute build/conda strings before generating `manifest/apps.json`,
`manifest/files.sha256`, and `manifest/build-metadata.json`:

```python
@dataclass(frozen=True)
class StageResult:
    root: Path
    apps_manifest: Path
    files_manifest: Path
    dependency_report: Path

def write_apps_manifest(root: Path, contract: ReleaseContract) -> Path:
    path = root / "manifest" / "apps.json"
    payload = {
        "schema_version": 1,
        "distribution": contract.distribution,
        "isis_version": contract.isis_version,
        "platform": contract.platform,
        "public_cli_apps": list(contract.public_cli_apps),
        "public_gui_apps": list(contract.public_gui_apps),
        "public_apps": list(contract.public_apps),
        "runtime_helpers": list(contract.runtime_helpers),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
```

- [ ] **Step 4: Implement normalized hashes and archive members**

Sort POSIX member names, set every ZIP timestamp to 1980-01-01, normalize file
attributes, and use DEFLATE level 9:

```python
def create_deterministic_zip(stage_root: Path, archive_path: Path) -> dict[str, object]:
    members = sorted((path for path in stage_root.rglob("*") if path.is_file()), key=lambda path: path.relative_to(stage_root.parent).as_posix())
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in members:
            name = source.relative_to(stage_root.parent).as_posix()
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    return {"path": str(archive_path), "size": archive_path.stat().st_size, "sha256": digest, "members": len(members)}
```

- [ ] **Step 5: Run staging and runtime-wheel regression suites**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.windows_native_app_staging_unit_test tests.unitTest.runtime_wheel_script_unit_test -v
git diff --check
```

Expected: all selected tests PASS and diff check is clean.

- [ ] **Step 6: Commit**

```powershell
git add tools/packaging/stage_windows_native_apps.py tools/packaging/archive_windows_native_apps.py tests/unitTest/windows_native_app_staging_unit_test.py
git commit -m "feat: stage Windows ISIS native app archive"
```

### Task 5: Add strict archive and evidence validation

**Files:**
- Create: `tools/packaging/validate_windows_native_apps.py`
- Create: `tests/unitTest/windows_native_app_validation_unit_test.py`

**Interfaces:**
- Produces `validate_release(archive, dependency_report, runtime_report, release_contract, output_report) -> dict[str, object]`.
- Consumes schema-1 APP/file/dependency/runtime reports and exact retained artifact names.

- [ ] **Step 1: Write a valid fixture and boundary-failure tests**

Cover traversal, inventory drift, missing mandatory APP, unexpected EXE,
forbidden path/suffix, unresolved dependency, stale artifact binding, absolute
build path, mismatched hash, nonzero exit, and required skips:

```python
def test_valid_release_produces_hash_bound_report(self):
    fixture = self._write_valid_fixture()
    report = self.module.validate_release(**fixture.arguments)
    self.assertEqual(report["public_app_count"], 151)
    self.assertEqual(report["dependency_closure"]["unresolved"], 0)
    self.assertEqual(report["tests"]["failed"], 0)
    self.assertEqual(report["tests"]["skipped"], 0)
    self.assertEqual(report["archive"]["sha256"], fixture.archive_sha256)

def test_zip_traversal_member_is_rejected(self):
    fixture = self._write_valid_fixture()
    self._append_zip_member(fixture.archive, "../escape.dll", b"bad")
    with self.assertRaisesRegex(ValueError, "unsafe ZIP member"):
        self.module.validate_release(**fixture.arguments)

def test_skipped_required_gui_probe_is_rejected(self):
    fixture = self._write_valid_fixture()
    fixture.runtime_payload["checks"]["gui-launch"]["skipped"] = 1
    fixture.write_runtime_report()
    with self.assertRaisesRegex(ValueError, "required check.*skipped"):
        self.module.validate_release(**fixture.arguments)
```

- [ ] **Step 2: Run tests and verify missing-validator failure**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.windows_native_app_validation_unit_test -v
```

Expected: FAIL because the validator does not exist.

- [ ] **Step 3: Implement safe ZIP parsing and atomic report writing**

```python
def safe_zip_member(name: str, expected_root: str) -> PurePosixPath:
    if "\\" in name or re.match(r"^[A-Za-z]:", name):
        raise ValueError(f"unsafe ZIP member: {name}")
    member = PurePosixPath(name)
    if member.is_absolute() or any(part in {"", ".", ".."} for part in member.parts):
        raise ValueError(f"unsafe ZIP member: {name}")
    if not member.parts or member.parts[0] != expected_root:
        raise ValueError(f"ZIP member outside fixed root: {name}")
    return member

def write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
```

Validate every name, count, required check, dependency, hash, host field, and
input report binding before writing output. Record RFC3339 UTC `validated_at`.

- [ ] **Step 4: Run manifest, staging, and validator suites together**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.windows_native_app_manifest_unit_test tests.unitTest.windows_native_app_staging_unit_test tests.unitTest.windows_native_app_validation_unit_test -v
```

Expected: all selected tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add tools/packaging/validate_windows_native_apps.py tests/unitTest/windows_native_app_validation_unit_test.py
git commit -m "test: enforce native app archive release gate"
```

### Task 6: Implement the clean-extraction runtime matrix and orchestrator

**Files:**
- Create: `ports/windows/isis/test_isis_native_app_package.ps1`
- Create: `tools/packaging/build_windows_native_apps.ps1`
- Create: `tests/unitTest/windows_isis_native_app_package_script_unit_test.py`

**Interfaces:**
- Runtime inputs: `-Archive`, `-ReleaseConfig`, `-WorkDir`, `-Report`, and repeatable `-ForbiddenPath` values that must not exist on the final clean host.
- Runtime report: schema 1 with artifact hash, host, extraction path, scrubbed variables, and named pass/fail/skip/exit-code checks.
- Build inputs: `-PythonExecutable`, `-IsisPrefix`, repeatable `-DependencyPrefix`, `-MinimalDataRoot`, `-OutputDir`, `-ReportDir`, `-WorkDir`.

- [ ] **Step 1: Write PowerShell contract tests**

```python
def test_runtime_matrix_contains_all_required_gates(self):
    script = RUNTIME_SCRIPT.read_text(encoding="utf-8")
    for token in ("CONDA_PREFIX", "ISISROOT", "ISIS_PREFIX", "ISISDATA", "QT_PLUGIN_PATH", "reduce", "jigsaw", "qnet", "stats", "getkey", "catlab", "campt", "cam2map", "isis2std", "cubeit", "fx", "MainWindowTitle"):
        self.assertIn(token, script)
    self.assertIn('passed = 150', script)
    self.assertIn('skipped = 0', script)

def test_orchestrator_guards_recursive_cleanup(self):
    script = BUILD_SCRIPT.read_text(encoding="utf-8")
    self.assertIn("Resolve-FullPath $WorkDir", script)
    self.assertIn("Assert-PathWithin", script)
    self.assertNotRegex(script, r"Remove-Item\s+[^\r\n]*-[Rr]ecurse[^\r\n]*\*")
```

- [ ] **Step 2: Run tests and verify missing-script failures**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.windows_isis_native_app_package_script_unit_test -v
```

Expected: FAIL because both PowerShell scripts do not exist.

- [ ] **Step 3: Implement the scrubbed runtime matrix**

Reject every existing `-ForbiddenPath`, then extract under
`native package with spaces`; remove conda, ISIS, Qt, source-prefix, and
build-tree entries from the child environment. Run all 150 `-HELP`
commands, the nine existing real operations, external-data override, and two
negative launcher cases. Probe `reduce -gui`, `jigsaw -gui`, and `qnet`:

```powershell
function Invoke-GuiProbe {
    param([string]$Name, [string[]]$Arguments)
    $process = Start-Process -FilePath $IsisAppLauncher -ArgumentList (@($Name) + $Arguments) -PassThru
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 250
        $process.Refresh()
        if ($process.HasExited) { break }
    } while (($process.MainWindowHandle -eq 0 -or -not $process.MainWindowTitle) -and [DateTime]::UtcNow -lt $deadline)
    if ($process.HasExited -or $process.MainWindowHandle -eq 0) { throw "GUI launch probe failed for $Name" }
    $null = $process.CloseMainWindow()
    if (-not $process.WaitForExit(10000)) {
        Stop-Process -Id $process.Id
        $process.WaitForExit()
    }
}
```

Write required groups `archive-extract`, `cli-help`, `real-operations`,
`gui-launch`, `external-isisdata`, and `negative-launcher` to the runtime report.

- [ ] **Step 4: Implement stage/archive/test/validate orchestration and guarded cleanup**

```powershell
$resolvedWorkDir = Resolve-FullPath $WorkDir
Assert-PathWithin -Candidate $resolvedWorkDir -Parent (Resolve-FullPath "build\windows")
& $PythonExecutable tools\packaging\stage_windows_native_apps.py @stageArgs
if ($LASTEXITCODE -ne 0) { throw "native APP staging failed" }
& $PythonExecutable tools\packaging\archive_windows_native_apps.py @archiveArgs
if ($LASTEXITCODE -ne 0) { throw "native APP archive creation failed" }
& ports\windows\isis\test_isis_native_app_package.ps1 @runtimeArgs
if ($LASTEXITCODE -ne 0) { throw "native APP runtime matrix failed" }
& $PythonExecutable tools\packaging\validate_windows_native_apps.py @validationArgs
if ($LASTEXITCODE -ne 0) { throw "native APP release validation failed" }
Remove-Item -LiteralPath $resolvedWorkDir -Recurse -Force
```

- [ ] **Step 5: Run the complete focused suite**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.windows_isis_native_app_package_script_unit_test tests.unitTest.windows_native_app_manifest_unit_test tests.unitTest.windows_native_app_staging_unit_test tests.unitTest.windows_native_app_validation_unit_test tests.unitTest.runtime_wheel_script_unit_test -v
```

Expected: all selected tests PASS.

- [ ] **Step 6: Commit**

```powershell
git add ports/windows/isis/test_isis_native_app_package.ps1 tools/packaging/build_windows_native_apps.ps1 tests/unitTest/windows_isis_native_app_package_script_unit_test.py
git commit -m "feat: validate Windows native app package runtime"
```

### Task 7: Document, build, and verify the first release artifact

**Files:**
- Modify: `ports/windows/README.md`
- Modify: `ports/windows/isis/README.md`
- Generate/retain: `build/windows/native-apps-isis9/usgs-isis-native-apps-9.0.0-win64.zip`
- Generate/retain: `build/windows/native-apps-isis9/usgs-isis-native-apps-9.0.0-win64-dll-dependencies.json`
- Generate/retain: `build/windows/reports/isis-native-apps-9.0.0-win64-validation.json`

**Interfaces:**
- Consumes verified `build/windows/isis-prefix`, its dependency prefix, and `packaging/isisdata-minimal/src/pyisis_isisdata_minimal/data`.
- Produces exact user commands and three hash-bound ignored artifacts.

- [ ] **Step 1: Document developer build and end-user launch commands**

Include product boundary, support matrix, contents, reports, cleanup, and:

```powershell
Expand-Archive .\usgs-isis-native-apps-9.0.0-win64.zip -DestinationPath "C:\ISIS Apps"
& "C:\ISIS Apps\usgs-isis-native-apps-9.0.0-win64\launch\isis-app.cmd" reduce -HELP
& "C:\ISIS Apps\usgs-isis-native-apps-9.0.0-win64\launch\qnet.cmd"
$env:ISISDATA = "D:\isisdata"
& "C:\ISIS Apps\usgs-isis-native-apps-9.0.0-win64\launch\isis-shell.cmd"
```

- [ ] **Step 2: Run all focused unit tests before the real build**

```powershell
D:/pyisis-win-env/python.exe -m unittest tests.unitTest.windows_native_app_manifest_unit_test tests.unitTest.windows_native_app_staging_unit_test tests.unitTest.windows_native_app_validation_unit_test tests.unitTest.windows_isis_native_app_package_script_unit_test tests.unitTest.runtime_wheel_script_unit_test tests.unitTest.packaging_tools_unit_test -v
```

Expected: all tests PASS with zero failures and zero skips.

- [ ] **Step 3: Build from the verified ISIS 9 prefix**

Run in an MSVC x64 environment exposing `dumpbin`:

```powershell
.\tools\packaging\build_windows_native_apps.ps1 `
  -PythonExecutable D:\pyisis-win-env\python.exe `
  -IsisPrefix build\windows\isis-prefix `
  -DependencyPrefix $env:PYISIS_WINDOWS_DEPENDENCY_PREFIX `
  -MinimalDataRoot packaging\isisdata-minimal\src\pyisis_isisdata_minimal\data `
  -OutputDir build\windows\native-apps-isis9 `
  -ReportDir build\windows\reports `
  -WorkDir build\windows\native-apps-isis9-work
```

Expected: exit 0 and exactly the three declared retained artifacts.

- [ ] **Step 4: Repeat the runtime matrix on a clean Windows 11 x64 host**

Copy only the ZIP, `release.json`, and the runtime-test script to a clean VM or
runner where the repository source/build prefix and conda dependency prefix do
not exist. Run:

```powershell
if (Test-Path D:\code\pyisis\pyisis\build\windows\isis-prefix) { throw "source prefix is accessible on clean host" }
New-Item -ItemType Directory -Force C:\pyisis-native-clean\output | Out-Null
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned `
  -File C:\pyisis-native-input\test_isis_native_app_package.ps1 `
  -Archive C:\pyisis-native-input\usgs-isis-native-apps-9.0.0-win64.zip `
  -ReleaseConfig C:\pyisis-native-input\release.json `
  -WorkDir "C:\pyisis-native-clean\work with spaces" `
  -Report C:\pyisis-native-clean\output\runtime-validation.json `
  -ForbiddenPath D:\code\pyisis\pyisis\build\windows\isis-prefix `
  -ForbiddenPath D:\pyisis-win-env
```

Expected: exit 0; the runtime report records Windows 11 x64, 150 CLI startup
passes, three GUI passes, real operations, external-data override, negative
launcher checks, zero failures, and zero skips. Copy only this runtime report
back to `build/windows/native-apps-isis9-work/runtime-validation.json` on the
build host.

- [ ] **Step 5: Bind clean-host evidence, independently validate, and hash retained artifacts**

```powershell
D:/pyisis-win-env/python.exe tools/packaging/validate_windows_native_apps.py `
  --archive build/windows/native-apps-isis9/usgs-isis-native-apps-9.0.0-win64.zip `
  --dependency-report build/windows/native-apps-isis9/usgs-isis-native-apps-9.0.0-win64-dll-dependencies.json `
  --runtime-report build/windows/native-apps-isis9-work/runtime-validation.json `
  --release packaging/native-apps-win64/release.json `
  --cli-manifest ports/windows/isis/windows-app-manifest.json `
  --output-report build/windows/reports/isis-native-apps-9.0.0-win64-validation.json
Get-FileHash build/windows/native-apps-isis9/usgs-isis-native-apps-9.0.0-win64.zip, build/windows/native-apps-isis9/usgs-isis-native-apps-9.0.0-win64-dll-dependencies.json, build/windows/reports/isis-native-apps-9.0.0-win64-validation.json -Algorithm SHA256
Remove-Item -LiteralPath build/windows/native-apps-isis9-work -Recurse -Force
```

Expected: report records 151 public APPs, 150 CLI startup passes, three GUI
passes, zero failures/skips, empty unresolved dependencies, Windows 11 x64,
ISIS 9.0.0, and matching hashes.

- [ ] **Step 6: Verify cleanup and Git classification**

```powershell
Test-Path build\windows\native-apps-isis9-work
Get-ChildItem build\windows\native-apps-isis9
Get-Item build\windows\reports\isis-native-apps-9.0.0-win64-validation.json
git status --short --branch
```

Expected: the work directory is absent; only declared artifacts remain; tracked
changes are task-related; `.gitignore` and `print.prt` remain untouched.

- [ ] **Step 7: Commit documentation**

```powershell
git add ports/windows/README.md ports/windows/isis/README.md
git commit -m "docs: document Windows native app archive"
```

- [ ] **Step 8: Run completion verification before reporting success**

Use `superpowers:verification-before-completion`. Re-run the focused unit suite,
final archive validator, artifact SHA-256 commands, milestone verification, and
`git status --short --branch`; report exact pass/fail/skip counts and retain
only the three declared build artifacts.
