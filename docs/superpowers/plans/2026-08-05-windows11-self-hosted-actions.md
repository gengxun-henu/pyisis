# Windows 11 Self-Hosted Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provision this Windows 11 workstation as a repository-level GitHub Actions service and route trusted PyISIS Windows wheel validation to it without exposing the host to untrusted pull requests.

**Architecture:** Keep `.github/workflows/wheels.yml` as the single packaging matrix and resolve its Windows runner dynamically: trusted same-repository owner PRs and default manual runs use the labeled Windows 11 host, while every other PR uses `windows-2022`. Harden Windows runtime packaging so missing DLLs fail with an audit report, and harden clean-wheel tests so no Conda DLL directory can mask an incomplete wheelhouse.

**Tech Stack:** GitHub Actions YAML, GitHub self-hosted runner, PowerShell 7, Micromamba, MSVC 2022, Python `unittest`, CPython 3.12/3.13, CMake/Ninja, `dumpbin`.

## Global Constraints

- Host operating system is Windows 11 x64; runner name is `pyisis-windows11`.
- Runner labels are `self-hosted`, `Windows`, `X64`, `pyisis`, and `windows-11`.
- Runner application directory is `D:\actions-runner-pyisis`; Micromamba executable is `D:\tools\micromamba\micromamba.exe`; Micromamba root is `D:\mamba\pyisis-runner`.
- The runner is repository-scoped to `gengxun-henu/pyisis` and runs as an automatically started Windows service.
- Only same-repository PRs whose actor is exactly `gengxun-henu` may execute PR code on the local runner; never use `pull_request_target`.
- ISIS 9 uses CPython 3.12; ISIS 10 uses CPython 3.13.
- Conda-forge environment files remain the dependency authority; do not install ISIS dependencies with pip.
- Never store or print a GitHub runner registration token, password, or machine secret.
- Do not modify `.gitignore` or `print.prt`.
- Preserve unrelated local changes and commits.

---

### Task 1: Provision PowerShell 7 and Micromamba

**Files:**
- Local machine state: `C:\Program Files\PowerShell\7\pwsh.exe`
- Local machine state: `D:\tools\micromamba\micromamba.exe`
- Local machine state: `D:\mamba\pyisis-runner`

**Interfaces:**
- Consumes: Windows 11 x64, administrator elevation, outbound HTTPS.
- Produces: `pwsh` available system-wide and a standalone Micromamba executable with `MAMBA_ROOT_PREFIX=D:\mamba\pyisis-runner` available to the future runner service.

- [ ] **Step 1: Record the pre-install state**

Run in elevated Windows PowerShell:

```powershell
Get-Command pwsh,micromamba -ErrorAction SilentlyContinue
winget --version
```

Expected: `pwsh` and `micromamba` are absent; `winget` reports a version.

- [ ] **Step 2: Install PowerShell 7 from Microsoft's winget package**

```powershell
winget install --id Microsoft.PowerShell --exact --source winget `
  --accept-source-agreements --accept-package-agreements
```

Expected: installation succeeds without changing Windows PowerShell 5.1.

- [ ] **Step 3: Verify PowerShell 7 from its machine path**

```powershell
& 'C:\Program Files\PowerShell\7\pwsh.exe' -NoLogo -NoProfile -Command '$PSVersionTable.PSVersion.ToString()'
```

Expected: a supported PowerShell 7 version is printed.

- [ ] **Step 4: Download Micromamba from the official Windows endpoint**

```powershell
$downloadDir = Join-Path $env:TEMP 'pyisis-micromamba-download'
New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null
Invoke-WebRequest `
  -Uri 'https://micro.mamba.pm/api/micromamba/win-64/latest' `
  -OutFile (Join-Path $downloadDir 'micromamba.tar.bz2')
tar -xf (Join-Path $downloadDir 'micromamba.tar.bz2') -C $downloadDir
New-Item -ItemType Directory -Force -Path 'D:\tools\micromamba' | Out-Null
Copy-Item -LiteralPath (Join-Path $downloadDir 'Library\bin\micromamba.exe') `
  -Destination 'D:\tools\micromamba\micromamba.exe' -Force
```

Expected: the executable exists at the fixed design path. Remove only the task-created temporary download directory after verification.

- [ ] **Step 5: Configure machine-level paths for the service**

```powershell
New-Item -ItemType Directory -Force -Path 'D:\mamba\pyisis-runner' | Out-Null
[Environment]::SetEnvironmentVariable('MAMBA_ROOT_PREFIX', 'D:\mamba\pyisis-runner', 'Machine')
$machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
$required = @('C:\Program Files\PowerShell\7', 'D:\tools\micromamba')
$parts = @($machinePath -split ';' | Where-Object { $_ })
foreach ($entry in $required) {
    if ($parts -notcontains $entry) { $parts += $entry }
}
[Environment]::SetEnvironmentVariable('Path', ($parts -join ';'), 'Machine')
```

Expected: future services receive both executable directories and the Micromamba root without editing a user profile.

- [ ] **Step 6: Verify Micromamba with the exact service environment values**

```powershell
$env:MAMBA_ROOT_PREFIX = 'D:\mamba\pyisis-runner'
& 'D:\tools\micromamba\micromamba.exe' --version
& 'D:\tools\micromamba\micromamba.exe' info
```

Expected: Micromamba reports a version and root prefix `D:\mamba\pyisis-runner`.

### Task 2: Remove Build-Prefix DLL Leakage from Clean-Wheel Tests

**Files:**
- Modify: `tests/unitTest/packaging_tools_unit_test.py:577`
- Modify: `tools/packaging/test_wheel_install.py:28`

**Interfaces:**
- Consumes: process environment variables and `PATH`.
- Produces: `_verification_environment() -> dict[str, str]` that removes all captured runtime/build prefixes, including `CONDA_PREFIX` and `PYISIS_WINDOWS_DEP_PREFIX`.

- [ ] **Step 1: Update test metadata and write the failing regression test**

In `tests/unitTest/packaging_tools_unit_test.py`, set `Last Modified: 2026-08-05`, append an `Updated:` line describing Windows dependency-prefix isolation, and change the environment fixture to use distinct roots:

```python
conda_root = PROJECT_ROOT / "fake-conda"
windows_dependency_root = PROJECT_ROOT / "windows-dependencies"
path = module.os.pathsep.join(
    [
        str(runtime_root / "bin"),
        str(conda_root / "Library" / "bin"),
        str(windows_dependency_root / "Library" / "bin"),
        str(safe_path),
    ]
)
```

Set both variables in `mock.patch.dict`:

```python
"CONDA_PREFIX": str(conda_root),
"PYISIS_WINDOWS_DEP_PREFIX": str(windows_dependency_root),
```

Assert both names are absent and only `safe_path` remains.

- [ ] **Step 2: Run the focused test and confirm the leak**

Run:

```powershell
py -3.12 -m unittest tests.unitTest.packaging_tools_unit_test.PackagingToolsUnitTest.test_clean_venv_verification_environment_removes_external_runtime -v
```

Expected: FAIL because one or both dependency-prefix directories remain in `PATH`.

- [ ] **Step 3: Implement complete prefix capture before environment removal**

In `tools/packaging/test_wheel_install.py`, replace the root-name setup with:

```python
root_names = (
    "ISIS_PREFIX",
    "ISISROOT",
    "PYISIS_DEP_PREFIX",
    "PYISIS_WINDOWS_DEP_PREFIX",
    "CONDA_PREFIX",
)
roots = tuple(Path(env[name]).resolve() for name in root_names if env.get(name))

for name in (*root_names, "ISISDATA", "PYTHONPATH"):
    env.pop(name, None)
```

Keep `_path_contains()` and the existing `PATH` reconstruction unchanged.

- [ ] **Step 4: Run the focused packaging tests**

```powershell
py -3.12 -m unittest `
  tests.unitTest.packaging_tools_unit_test.PackagingToolsUnitTest.test_clean_venv_verification_environment_removes_external_runtime `
  tests.unitTest.packaging_tools_unit_test.PackagingToolsUnitTest.test_clean_venv_unit_test_environment_exposes_only_test_helpers -v
```

Expected: PASS.

- [ ] **Step 5: Commit the isolation fix**

```powershell
git add tools/packaging/test_wheel_install.py tests/unitTest/packaging_tools_unit_test.py
git commit -m "fix: isolate Windows wheel DLL validation"
```

### Task 3: Make Windows DLL Closure Auditing Fail Closed

**Files:**
- Modify: `tests/unitTest/runtime_wheel_script_unit_test.py:135`
- Modify: `tests/unitTest/packaging_tools_unit_test.py:64`
- Modify: `tools/packaging/stage_runtime_win64.py:113`
- Modify: `tools/packaging/build_wheels.ps1:1`

**Interfaces:**
- Consumes: `dumpbin /DEPENDENTS`, ISIS prefix, dependency prefixes.
- Produces: `_dumpbin_dependencies(binary: Path) -> tuple[str, ...]` that raises on inspection failure; `_copy_dependency_closure(...) -> dict[str, object]` with `binaries` and `unresolved`; CLI option `--dependency-report PATH`.

- [ ] **Step 1: Add failing `dumpbin` and unresolved-DLL tests**

Update `tests/unitTest/runtime_wheel_script_unit_test.py` metadata for 2026-08-05. Add tests that mock `subprocess.run` with a nonzero result and assert:

```python
with self.assertRaisesRegex(RuntimeError, "dumpbin failed"):
    stage_module._dumpbin_dependencies(Path("isis.dll"))
```

Add a closure test whose fake dependency list returns `("missing.dll",)` and assert:

```python
with self.assertRaisesRegex(FileNotFoundError, "missing.dll"):
    stage_module.stage_runtime(
        prefix,
        stage,
        (dep_prefix,),
        dependency_copy_mode="closure",
        dependency_report=report,
    )
self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["unresolved"], ["missing.dll"])
```

- [ ] **Step 2: Run the new tests and confirm current silent behavior**

```powershell
py -3.12 -m unittest tests.unitTest.runtime_wheel_script_unit_test.RuntimeWheelScriptUnitTest -v
```

Expected: the new failure-mode tests FAIL because `dumpbin` errors and unresolved imports are currently ignored.

- [ ] **Step 3: Implement strict dependency inspection and JSON evidence**

In `stage_runtime_win64.py`:

- import `json`;
- make `_dumpbin_dependencies` raise `RuntimeError` containing the binary and stderr when `returncode != 0`;
- keep system DLL classification in `_copy_dependency_closure` using `SYSTEM_DLL_PREFIXES` and `SYSTEM_DLL_NAMES`;
- record one entry per inspected binary with dependency names classified as `system`, `packaged`, `resolved`, or `unresolved`;
- write `{"schema_version": 1, "binaries": [...], "unresolved": [...]}` to `dependency_report` before raising;
- raise `FileNotFoundError` listing sorted unresolved non-system names;
- add `dependency_report: Path | None = None` to `stage_runtime` and CLI `--dependency-report`.

The existing resolved closure test must continue to copy only `needed.dll` and `cspice.dll`; `KERNEL32.dll` must be reported as `system` and never copied.

- [ ] **Step 4: Wire the report into the wheelhouse output**

In `build_wheels.ps1`, define:

```powershell
$DependencyReport = Join-Path $OutputDir "$RuntimeDistribution-dll-dependencies.json"
```

Pass it to staging:

```powershell
--dependency-report $DependencyReport
```

Extend `test_build_wheels_script_runs_all_local_wheel_steps` to assert both `--dependency-report` and `dll-dependencies.json` occur in the script.

- [ ] **Step 5: Run runtime and packaging-tool tests**

```powershell
py -3.12 -m unittest tests.unitTest.runtime_wheel_script_unit_test tests.unitTest.packaging_tools_unit_test -v
```

Expected: PASS.

- [ ] **Step 6: Commit strict Windows DLL auditing**

```powershell
git add tools/packaging/stage_runtime_win64.py tools/packaging/build_wheels.ps1 tests/unitTest/runtime_wheel_script_unit_test.py tests/unitTest/packaging_tools_unit_test.py
git commit -m "build: fail closed on missing Windows DLLs"
```

### Task 4: Add Windows 11 Runner Routing and Readiness Gates

**Files:**
- Modify: `tests/unitTest/wheel_workflow_unit_test.py:1`
- Modify: `tests/unitTest/packaging_tools_unit_test.py:1`
- Modify: `.github/workflows/wheels.yml:3`
- Create: `tools/packaging/check_windows_runner.ps1`
- Modify: `.github/workflows/README.md`

**Interfaces:**
- Consumes: `workflow_dispatch.inputs.windows_runner`, PR repository identity, PR actor, and runner labels.
- Produces: scope output `windows_runs_on_json`; readiness script parameters `-MicromambaExecutable` and `-ExpectedWindows11`.

- [ ] **Step 1: Write failing workflow-routing assertions**

Update `wheel_workflow_unit_test.py` metadata for 2026-08-05. Replace the fixed-runner assertion with checks for:

```python
self.assertIn("windows_runner:", workflow)
self.assertIn("windows11-self-hosted", workflow)
self.assertIn("windows-2022", workflow)
self.assertIn("windows_runs_on_json", scope)
self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", scope)
self.assertIn("github.actor == 'gengxun-henu'", scope)
self.assertIn('["self-hosted", "Windows", "X64", "pyisis", "windows-11"]', scope)
self.assertNotIn("pull_request_target:", workflow)
```

For both Windows job blocks, assert:

```python
self.assertIn("runs-on: ${{ fromJSON(needs.scope.outputs.windows_runs_on_json) }}", job)
self.assertIn("check_windows_runner.ps1", job)
```

- [ ] **Step 2: Write the failing readiness-script contract test**

In `packaging_tools_unit_test.py`, add a `WINDOWS_RUNNER_CHECK` path and a test asserting the new script checks:

```python
for required in ("Windows 11", "pwsh", "micromamba", "activate_msvc.ps1", "dumpbin", "cmake", "ninja", "git"):
    self.assertIn(required, script)
```

- [ ] **Step 3: Run the focused tests and verify they fail**

```powershell
py -3.12 -m unittest tests.unitTest.wheel_workflow_unit_test tests.unitTest.packaging_tools_unit_test -v
```

Expected: FAIL because routing outputs and readiness tooling do not exist.

- [ ] **Step 4: Implement trusted dynamic routing in `wheels.yml`**

Add a manual choice input:

```yaml
windows_runner:
  description: "Windows validation runner"
  required: false
  default: windows11-self-hosted
  type: choice
  options:
    - windows11-self-hosted
    - windows-2022
```

Add `windows_runs_on_json` to scope outputs. In `actions/github-script`, select the local labels only for manual default selection or when both trusted-PR predicates are true; otherwise select the string `windows-2022`. Emit it with `JSON.stringify(selectedWindowsRunner)`. Change both Windows jobs to:

```yaml
runs-on: ${{ fromJSON(needs.scope.outputs.windows_runs_on_json) }}
```

Do not change Linux runner selection.

- [ ] **Step 5: Implement the fail-fast PowerShell readiness check**

Create `tools/packaging/check_windows_runner.ps1` with `ErrorActionPreference = "Stop"`, parameters:

```powershell
param(
    [string]$MicromambaExecutable = 'D:\tools\micromamba\micromamba.exe',
    [switch]$ExpectedWindows11
)
```

It must verify Windows x64, optionally require a caption containing `Windows 11`, locate `pwsh`, the explicit Micromamba executable, Git, CMake, and Ninja, dot-source `ports\windows\activate_msvc.ps1`, then locate `cl.exe` and `dumpbin.exe`. Print versions/paths only; do not print environment secrets.

Invoke it after Micromamba environment setup and before ISIS prefix restore/build in both Windows jobs.

- [ ] **Step 6: Upload DLL reports and document operations**

Extend each Windows artifact path to include its runtime `*-dll-dependencies.json` report. Update `.github/workflows/README.md` with runner name, labels, trust routing, manual fallback, service status command, fixed tool paths, and the rule that registration tokens are never persisted.

- [ ] **Step 7: Run workflow and packaging tests**

```powershell
py -3.12 -m unittest tests.unitTest.wheel_workflow_unit_test tests.unitTest.packaging_tools_unit_test tests.unitTest.runtime_wheel_script_unit_test -v
```

Expected: PASS.

- [ ] **Step 8: Commit runner routing and readiness changes**

```powershell
git add .github/workflows/wheels.yml .github/workflows/README.md tools/packaging/check_windows_runner.ps1 tests/unitTest/wheel_workflow_unit_test.py tests/unitTest/packaging_tools_unit_test.py
git commit -m "ci: add trusted Windows 11 wheel runner"
```

### Task 5: Install and Register the Repository Runner Service

**Files:**
- Local machine state: `D:\actions-runner-pyisis`
- External GitHub state: repository runner registration for `gengxun-henu/pyisis`

**Interfaces:**
- Consumes: authenticated `gh` session with repository administration permission and an elevated PowerShell 7 process.
- Produces: online service-backed runner `pyisis-windows11` with the exact label set used by `wheels.yml`.

- [ ] **Step 1: Verify GitHub authentication without displaying credentials**

```powershell
gh auth status
gh api repos/gengxun-henu/pyisis --jq '.full_name + " permission=" + .permissions.admin'
```

Expected: authenticated account can administer `gengxun-henu/pyisis`.

- [ ] **Step 2: Resolve and download the current official runner release**

```powershell
$runnerTag = (gh api repos/actions/runner/releases/latest --jq .tag_name).Trim()
$runnerVersion = $runnerTag.TrimStart('v')
$runnerAsset = "actions-runner-win-x64-$runnerVersion.zip"
New-Item -ItemType Directory -Force -Path 'D:\actions-runner-pyisis' | Out-Null
gh release download $runnerTag --repo actions/runner --pattern $runnerAsset --dir $env:TEMP
Expand-Archive -LiteralPath (Join-Path $env:TEMP $runnerAsset) `
  -DestinationPath 'D:\actions-runner-pyisis' -Force
```

Expected: `config.cmd`, `run.cmd`, and `bin\Runner.Listener.exe` exist.

- [ ] **Step 3: Acquire a one-hour token in memory and register as a service**

From elevated PowerShell 7:

```powershell
$registrationToken = gh api --method POST `
  repos/gengxun-henu/pyisis/actions/runners/registration-token --jq .token
Push-Location 'D:\actions-runner-pyisis'
try {
    .\config.cmd --unattended `
      --url 'https://github.com/gengxun-henu/pyisis' `
      --token $registrationToken `
      --name 'pyisis-windows11' `
      --labels 'pyisis,windows-11' `
      --work '_work' `
      --runasservice
} finally {
    $registrationToken = $null
    Pop-Location
}
```

Expected: configuration creates an `actions.runner.*` Windows service. Accept the runner's default Windows service account; do not pass or log a user password.

- [ ] **Step 4: Restart and verify the service**

```powershell
$service = Get-Service 'actions.runner.*pyisis*'
Set-Service -Name $service.Name -StartupType Automatic
Restart-Service -Name $service.Name
Get-Service -Name $service.Name
```

Expected: service status is `Running` and startup type is automatic.

- [ ] **Step 5: Verify GitHub-visible runner identity and labels**

```powershell
gh api repos/gengxun-henu/pyisis/actions/runners `
  --jq '.runners[] | select(.name == "pyisis-windows11") | {name,status,busy,labels:[.labels[].name]}'
```

Expected: runner is online and exposes `self-hosted`, `Windows`, `X64`, `pyisis`, and `windows-11`.

### Task 6: Final Verification and Handoff

**Files:**
- Verify: `.github/workflows/wheels.yml`
- Verify: `tools/packaging/check_windows_runner.ps1`
- Verify: `tools/packaging/test_wheel_install.py`
- Verify: `tools/packaging/stage_runtime_win64.py`
- Verify: relevant tests and documentation

**Interfaces:**
- Consumes: completed Tasks 1–5.
- Produces: evidence-backed readiness report; no PR, push, or release publication without a separate explicit user request.

- [ ] **Step 1: Run the local host readiness check**

```powershell
& 'C:\Program Files\PowerShell\7\pwsh.exe' -NoProfile -File `
  tools\packaging\check_windows_runner.ps1 `
  -MicromambaExecutable 'D:\tools\micromamba\micromamba.exe' `
  -ExpectedWindows11
```

Expected: all host and MSVC checks pass, including `dumpbin`.

- [ ] **Step 2: Run focused unit validation**

```powershell
py -3.12 -m unittest `
  tests.unitTest.wheel_workflow_unit_test `
  tests.unitTest.packaging_tools_unit_test `
  tests.unitTest.runtime_wheel_script_unit_test -v
```

Expected: PASS.

- [ ] **Step 3: Run repository diff and guardrail checks**

```powershell
git diff --check
git status --short --branch
git diff --name-only HEAD~3..HEAD
```

Expected: no whitespace errors; `.gitignore` and `print.prt` are absent from the task changes.

- [ ] **Step 4: Re-query the service and GitHub runner state**

```powershell
Get-Service 'actions.runner.*pyisis*'
gh api repos/gengxun-henu/pyisis/actions/runners `
  --jq '.runners[] | select(.name == "pyisis-windows11") | {name,status,busy,labels:[.labels[].name]}'
```

Expected: Windows service is running and GitHub reports the runner online with all required labels.

- [ ] **Step 5: Report the live-validation boundary**

Report local tests, installed tool versions, service name/status, GitHub runner status/labels, commits, and any untracked generated artifacts. State explicitly that an end-to-end PR-triggered wheel build requires a later authorized branch push/PR and is not silently performed by this plan.
