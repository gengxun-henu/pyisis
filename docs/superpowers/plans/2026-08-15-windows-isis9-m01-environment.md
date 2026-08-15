# Windows ISIS 9.0.0 M1 Environment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create and verify the short-path Windows x64 conda/MSVC build environment required to compile ISIS 9.0.0 and PyISIS.

**Architecture:** Use the repository's pinned conda environment file with `C:\Users\gx\miniconda3\Scripts\conda.exe --solver classic`, storing the environment at `D:\pyisis-win-env` and its package cache at `D:\conda-pkgs\pyisis-isis9`. Load the Visual Studio 2022 x64 environment through `ports/windows/activate_msvc.ps1`, run the repository prerequisite checker, and persist a machine-readable readiness report under `build/windows/reports/`.

**Tech Stack:** Windows 11 x64, PowerShell 7, micromamba, conda-forge, CPython 3.12, CMake, Ninja, Visual Studio 2022 MSVC.

## Global Constraints

- Use only conda-managed dependencies; do not introduce pip or npm workflows.
- Use `ports/windows/env/pyisis-isis-win64.yml` as the dependency authority.
- Preserve `.gitignore`, `print.prt`, unrelated local changes, and prior `.planning` directories.
- Work only on milestone `windows-isis9-m01-environment` in this session.
- The exact environment prefix is `D:\pyisis-win-env`.
- The exact Conda package cache is `D:\conda-pkgs\pyisis-isis9`.
- Do not disable endpoint protection; this host must use Conda classic instead
  of Micromamba for UCRT extraction.

---

### Task 1: Create the pinned Windows dependency environment

**Files:**
- Consume: `ports/windows/env/pyisis-isis-win64.yml`
- Create: `D:\pyisis-win-env\conda-meta\history`

**Interfaces:**
- Consumes: `C:\Users\gx\miniconda3\Scripts\conda.exe` and the conda-forge channel declared in the environment file.
- Produces: a CPython 3.12 Windows x64 prefix used by every later native build command.

- [ ] **Step 1: Confirm that the target paths do not already contain an unrelated environment**

Run:

```powershell
@('D:\pyisis-win-env', 'D:\conda-pkgs\pyisis-isis9') |
  ForEach-Object { [pscustomobject]@{ Path = $_; Exists = Test-Path -LiteralPath $_ } }
```

Expected: both paths are absent before the first creation attempt, or an existing prefix is positively identified as this task's matching environment before reuse.

- [ ] **Step 2: Create the environment from the repository YAML**

Run:

```powershell
$env:CONDA_PKGS_DIRS = 'D:\conda-pkgs\pyisis-isis9'
$env:CONDARC = (Resolve-Path 'build\windows\conda\condarc').Path
& 'C:\Users\gx\miniconda3\Scripts\conda.exe' env create `
  --yes --solver classic `
  --prefix 'D:\pyisis-win-env' `
  --file 'ports\windows\env\pyisis-isis-win64.yml'
```

Expected: exit code 0 and `D:\pyisis-win-env\conda-meta\history` exists.

The command-scoped condarc contains only `channels: [conda-forge]` and an empty
`default_channels` list. It prevents the user's global `defaults` channel from
introducing unrelated Anaconda ToS requirements.

- [ ] **Step 3: Verify the key package versions and native build tools**

Run:

```powershell
& 'C:\Users\gx\miniconda3\Scripts\conda.exe' list `
  --prefix 'D:\pyisis-win-env' | `
  Select-String '^(python|cmake|ninja|pybind11|csm)\s'
```

Expected: Python 3.12, CMake, Ninja, pybind11, and CSM 3.0.3.3 are installed from conda-forge.

### Task 2: Activate and verify the Windows native toolchain

**Files:**
- Consume: `ports/windows/activate_msvc.ps1`
- Consume: `ports/windows/check_prereqs.ps1`
- Create: `build/windows/reports/environment-readiness.json`

**Interfaces:**
- Consumes: the Task 1 prefix and Visual Studio 2022 discovered through `vswhere.exe`.
- Produces: one passing prerequisite check and a JSON artifact recording exact OS, compiler, Python, CMake, Ninja, conda prefix, and package-source state.

- [ ] **Step 1: Build the process environment without modifying system-wide settings**

Run in one PowerShell process:

```powershell
$env:CONDA_PREFIX = 'D:\pyisis-win-env'
$env:PATH = @(
  'D:\pyisis-win-env'
  'D:\pyisis-win-env\Scripts'
  'D:\pyisis-win-env\Library\bin'
  'D:\pyisis-win-env\Library\usr\bin'
  'D:\pyisis-win-env\Library\mingw-w64\bin'
  'D:\pyisis-win-env\bin'
  'C:\Users\gx\miniconda3\Scripts'
  $env:PATH
) -join ';'
. .\ports\windows\activate_msvc.ps1
```

Expected: `Get-Command python, cmake, ninja, cl, dumpbin, conda` resolves every command, with Python/CMake/Ninja coming from `D:\pyisis-win-env` and MSVC tools from Visual Studio 2022.

- [ ] **Step 2: Run the repository prerequisite checker**

Run in the same configured process:

```powershell
.\ports\windows\check_prereqs.ps1
```

Expected: exit code 0 and final output `all prerequisite commands are available`.

- [ ] **Step 3: Write the durable readiness report**

Run in the same configured process:

```powershell
New-Item -ItemType Directory -Force 'build\windows\reports' | Out-Null
$report = [ordered]@{
  schema_version = 1
  generated_at_utc = [DateTime]::UtcNow.ToString('o')
  operating_system = (Get-CimInstance Win32_OperatingSystem).Caption
  architecture = (Get-CimInstance Win32_OperatingSystem).OSArchitecture
  conda_prefix = $env:CONDA_PREFIX
  python = (& python --version 2>&1 | Out-String).Trim()
  python_executable = (Get-Command python).Source
  cmake = (& cmake --version | Select-Object -First 1)
  cmake_executable = (Get-Command cmake).Source
  ninja = (& ninja --version | Out-String).Trim()
  ninja_executable = (Get-Command ninja).Source
  cl_executable = (Get-Command cl).Source
  dumpbin_executable = (Get-Command dumpbin).Source
  micromamba_executable = 'D:\tools\micromamba\micromamba.exe'
  environment_creator = 'conda-classic'
  conda_package_cache = 'D:\conda-pkgs\pyisis-isis9'
  environment_file = 'ports/windows/env/pyisis-isis-win64.yml'
  prerequisite_check = 'passed'
}
$report | ConvertTo-Json -Depth 3 |
  Set-Content -Encoding utf8 'build\windows\reports\environment-readiness.json'
```

Expected: the JSON parses successfully and records `prerequisite_check` as `passed`.

### Task 3: Close M1 with fresh structured evidence

**Files:**
- Modify: `.planning/windows-isis9-m01-environment/task_plan.md`
- Modify: `.planning/windows-isis9-m01-environment/findings.md`
- Modify: `.planning/windows-isis9-m01-environment/progress.md`
- Modify through lifecycle tooling: `.planning/milestones.v1.json`
- Modify through lifecycle tooling: `.planning/milestone-index.md`

**Interfaces:**
- Consumes: the passing prerequisite command, readiness JSON, live Git status, and prerequisite paths.
- Produces: schema-1 completion evidence accepted by `close_session.py` and a next-milestone handoff prompt.

- [ ] **Step 1: Record commands, results, decisions, and prerequisites in the three M1 planning files**

Expected: Task 1 and Task 2 results are recorded; the only phase checkbox is checked; current phase status is `complete`; there are no unfinished markers.

- [ ] **Step 2: Run fresh verification and hash the artifact**

Run:

```powershell
Get-FileHash -Algorithm SHA256 'build\windows\reports\environment-readiness.json'
git status --porcelain=v1
git rev-parse HEAD
```

Expected: the report hash is 64 lowercase hexadecimal characters after normalization, and Git state is explicitly classified.

- [ ] **Step 3: Close the milestone with schema-1 evidence**

Write fresh schema-1 evidence matching the manifest IDs to the ignored path
`build/windows/reports/windows-isis9-m01-completion-evidence.json`, then run:

```powershell
& 'C:\Users\gx\miniconda3\python.exe' `
  'C:\Users\gx\.codex\skills\milestone-session-manager\scripts\close_session.py' `
  --repo 'D:\code\pyisis\pyisis' `
  --outcome complete `
  --evidence 'D:\code\pyisis\pyisis\build\windows\reports\windows-isis9-m01-completion-evidence.json'
```

Expected: M1 becomes `complete`, M2 remains `pending`, verification passes, and the command prints the exact prompt for starting M2.
