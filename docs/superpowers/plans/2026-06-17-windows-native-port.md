# Windows Native Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first Windows-native pyisis milestone by creating a reproducible ISIS 9.0.0 SDK/runtime prefix workflow and making pyisis consume that Windows prefix.

**Architecture:** Use a two-stage prefix-driven port. `ports/windows/isis/` prepares and verifies a Windows ISIS prefix; pyisis CMake and `ports/windows/pyisis/` consume that prefix to build `_isis_core*.pyd` and run smoke/basic tests. Generated source, build, and prefix directories default to `build/windows/...` so existing repository ignore rules keep local artifacts out of commits.

**Tech Stack:** CMake, pybind11, MSVC, Ninja, PowerShell, conda-forge, Python `unittest`

---

## File Structure

| Action | File | Responsibility |
| --- | --- | --- |
| Create | `ports/windows/README.md` | Top-level Windows port workflow, prerequisites, and two-stage commands. |
| Create | `ports/windows/activate_msvc.ps1` | Load `vcvars64.bat` output into the current PowerShell process when the user is not already in an MSVC shell. |
| Create | `ports/windows/check_prereqs.ps1` | Diagnose missing conda, CMake, Ninja, Git, and MSVC shell setup before running the port workflow. |
| Create | `ports/windows/env/pyisis-isis-win64.yml` | Initial conda-forge environment definition for MSVC/Ninja/CMake/Python/pybind11/Qt-side development dependencies. |
| Create | `ports/windows/isis/README.md` | ISIS SDK/runtime subset workflow and prefix contract. |
| Create | `ports/windows/isis/common.ps1` | Shared PowerShell helpers for paths, logging, command checks, and repository root detection. |
| Create | `ports/windows/isis/fetch_isis_900.ps1` | Fetch ISIS 9.0.0 source into a local generated directory. |
| Create | `ports/windows/isis/apply_patches.ps1` | Apply tracked patch files to the local ISIS source checkout. |
| Create | `ports/windows/isis/configure_isis.ps1` | Configure ISIS with MSVC/Ninja into a local generated build directory. |
| Create | `ports/windows/isis/build_isis.ps1` | Build the ISIS SDK/runtime subset. |
| Create | `ports/windows/isis/install_isis.ps1` | Install the ISIS SDK/runtime subset into a local prefix. |
| Create | `ports/windows/isis/verify_isis_prefix.ps1` | Validate prefix shape and key Windows runtime files. |
| Create | `ports/windows/isis/patches/README.md` | Patch queue conventions and initial placeholder-free patch inventory policy. |
| Create | `ports/windows/pyisis/README.md` | pyisis Windows configure/build/test workflow. |
| Create | `ports/windows/pyisis/common.ps1` | Shared pyisis PowerShell helpers for `ISIS_PREFIX`, `PYTHONPATH`, `ISISDATA`, and `PATH`. |
| Create | `ports/windows/pyisis/configure_pyisis.ps1` | Configure pyisis against a Windows `ISIS_PREFIX`. |
| Create | `ports/windows/pyisis/build_pyisis.ps1` | Build pyisis and verify the package directory exists. |
| Create | `ports/windows/pyisis/test_pyisis_smoke.ps1` | Run `tests/smoke_import.py` with Windows runtime paths. |
| Create | `ports/windows/pyisis/test_pyisis_basic.ps1` | Run curated Windows basic unit tests from a text manifest. |
| Create | `ports/windows/pyisis/basic_tests.txt` | Initial curated basic test module list. |
| Modify | `CMakeLists.txt` | Add platform-aware ISIS prefix, library, runtime, Qt, plugin, and test environment detection while preserving Linux behavior. |

---

## Task 1: Add Windows Port Scaffolding

**Files:**
- Create: `ports/windows/README.md`
- Create: `ports/windows/check_prereqs.ps1`
- Create: `ports/windows/env/pyisis-isis-win64.yml`
- Create: `ports/windows/isis/README.md`
- Create: `ports/windows/isis/patches/README.md`
- Create: `ports/windows/pyisis/README.md`
- Create: `ports/windows/pyisis/basic_tests.txt`

- [ ] **Step 1: Add the top-level Windows workflow document**

Create `ports/windows/README.md` with this content:

```markdown
# Windows Native Port

This directory contains the local Windows-native port workflow for pyisis.

The first milestone is intentionally local and prefix-driven:

1. Build and verify a Windows-native ISIS 9.0.0 SDK/runtime prefix.
2. Build and test pyisis against that prefix.

The default generated directories are under `build/windows/` so they are covered
by the repository's existing build artifact ignore rule:

- `build/windows/external/isis-9.0.0-src`
- `build/windows/isis-build`
- `build/windows/isis-prefix`
- `build/windows/pyisis-build`

The scripts accept explicit path parameters when a developer wants another
layout.

## Prerequisites

- Windows 10 or newer
- Visual Studio Build Tools with the MSVC C++ toolchain
- Conda or Mamba
- Ninja and CMake from the active conda environment

Create the initial environment with:

```powershell
conda env create -f ports\windows\env\pyisis-isis-win64.yml
conda activate pyisis-isis-win64
```

## Stage 1: ISIS Prefix

```powershell
.\ports\windows\isis\fetch_isis_900.ps1
.\ports\windows\isis\apply_patches.ps1
.\ports\windows\isis\configure_isis.ps1
.\ports\windows\isis\build_isis.ps1
.\ports\windows\isis\install_isis.ps1
.\ports\windows\isis\verify_isis_prefix.ps1
```

## Stage 2: pyisis

```powershell
$env:ISIS_PREFIX = "$PWD\build\windows\isis-prefix"
.\ports\windows\pyisis\configure_pyisis.ps1
.\ports\windows\pyisis\build_pyisis.ps1
.\ports\windows\pyisis\test_pyisis_smoke.ps1
.\ports\windows\pyisis\test_pyisis_basic.ps1
```

The first milestone does not promise full ISIS CLI support, production
`ISISDATA`, GitHub Actions, or conda packaging.
```

- [ ] **Step 1a: Add the prerequisite diagnostic script**

Create `ports/windows/check_prereqs.ps1` with this content:

```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Check {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "[windows-prereqs] $Message"
}

function Test-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        Write-Check "found ${Name}: $($command.Source)"
        return $true
    }
    Write-Check "missing ${Name}"
    return $false
}

$missing = New-Object System.Collections.Generic.List[string]

if (-not (Test-Command git)) { $missing.Add("git") }
if (-not (Test-Command cmake)) { $missing.Add("cmake") }
if (-not (Test-Command ninja)) { $missing.Add("ninja") }

$hasConda = Test-Command conda
$hasMamba = Test-Command mamba
if (-not ($hasConda -or $hasMamba)) {
    $missing.Add("conda or mamba")
}

$hasCl = Test-Command cl
if (-not $hasCl) {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswhere) {
        Write-Check "found vswhere: $vswhere"
        Write-Check "MSVC cl.exe is not on PATH; run from an x64 Native Tools prompt or call vcvars64.bat."
    } else {
        Write-Check "Visual Studio Build Tools were not detected via vswhere."
    }
    $missing.Add("MSVC cl.exe on PATH")
}

if ($env:CONDA_PREFIX) {
    Write-Check "CONDA_PREFIX: $env:CONDA_PREFIX"
} else {
    Write-Check "CONDA_PREFIX is not set; activate pyisis-isis-win64 before configuring ISIS or pyisis."
    $missing.Add("active conda environment")
}

if ($missing.Count -gt 0) {
    Write-Error "Windows port prerequisites missing: $($missing -join ', ')"
    exit 1
}

Write-Check "all prerequisite commands are available"
```

- [ ] **Step 2: Add the initial conda environment definition**

Create `ports/windows/env/pyisis-isis-win64.yml` with this content:

```yaml
name: pyisis-isis-win64
channels:
  - conda-forge
dependencies:
  - python=3.12
  - cmake
  - ninja
  - git
  - pybind11
  - qt-main=5.*
  - eigen
  - bullet
  - cspice
  - numpy
```

- [ ] **Step 3: Add ISIS workflow documentation**

Create `ports/windows/isis/README.md` with this content:

```markdown
# ISIS 9.0.0 Windows SDK/Runtime Prefix

This directory owns the ISIS side of the Windows native pyisis port.

The scripts fetch ISIS 9.0.0 source code into a generated local directory, apply
tracked patches, configure with MSVC and Ninja, build the SDK/runtime subset,
install it into a local prefix, and verify the installed prefix.

Default local paths:

- source: `build/windows/external/isis-9.0.0-src`
- build: `build/windows/isis-build`
- prefix: `build/windows/isis-prefix`

The prefix is considered usable for the first pyisis milestone when
`verify_isis_prefix.ps1` passes.
```

- [ ] **Step 4: Add patch queue documentation**

Create `ports/windows/isis/patches/README.md` with this content:

```markdown
# ISIS Windows Patch Queue

Patch files in this directory are applied in lexical order by
`ports/windows/isis/apply_patches.ps1`.

Patch naming convention:

```text
0001-short-description.patch
0002-short-description.patch
```

Each patch should solve one explainable Windows porting issue, such as CMake
library naming, plugin discovery, path separators, or MSVC compile errors.
Keep patch context narrow so the queue can be rebased against ISIS 9.0.0 source
without mixing unrelated changes.
```

- [ ] **Step 5: Add pyisis workflow documentation**

Create `ports/windows/pyisis/README.md` with this content:

```markdown
# pyisis Windows Build and Test

These scripts configure, build, and test pyisis against a Windows-native
`ISIS_PREFIX`.

Set `ISIS_PREFIX` before running the scripts:

```powershell
$env:ISIS_PREFIX = "$PWD\build\windows\isis-prefix"
```

The scripts set `PYTHONPATH`, `ISISDATA`, and `PATH` so Python can find the
built pyisis package and Windows can find ISIS/Qt runtime DLLs.
```

- [ ] **Step 6: Add the initial curated unit test manifest**

Create `ports/windows/pyisis/basic_tests.txt` with this content:

```text
tests.unitTest.angle_unit_test
tests.unitTest.distance_unit_test
tests.unitTest.displacement_unit_test
tests.unitTest.latitude_unit_test
tests.unitTest.longitude_unit_test
tests.unitTest.pvl_unit_test
tests.unitTest.geometry_unit_test
tests.unitTest.math_unit_test
tests.unitTest.filters_unit_test
```

- [ ] **Step 7: Verify the scaffolding diff**

Run:

```powershell
git diff --check -- ports\windows
```

Expected: no output and exit code 0.

- [ ] **Step 8: Commit**

```powershell
git add -- ports/windows
git commit -m "docs: add windows port scaffolding"
```

---

## Task 2: Add ISIS PowerShell Workflow Scripts

**Files:**
- Create: `ports/windows/isis/common.ps1`
- Create: `ports/windows/isis/fetch_isis_900.ps1`
- Create: `ports/windows/isis/apply_patches.ps1`
- Create: `ports/windows/isis/configure_isis.ps1`
- Create: `ports/windows/isis/build_isis.ps1`
- Create: `ports/windows/isis/install_isis.ps1`
- Create: `ports/windows/isis/verify_isis_prefix.ps1`

- [ ] **Step 1: Add shared ISIS PowerShell helpers**

Create `ports/windows/isis/common.ps1` with this content:

```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    $scriptDir = Split-Path -Parent $PSScriptRoot
    return (Resolve-Path (Join-Path $scriptDir "..\..")).Path
}

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "[windows-isis] $Message"
}

function Fail {
    param([Parameter(Mandatory = $true)][string]$Message)
    throw "[windows-isis] $Message"
}

function Require-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Fail "required command not found: $Name"
    }
}

function Get-DefaultIsisSourceDir {
    $repoRoot = Get-RepoRoot
    return Join-Path $repoRoot "build\windows\external\isis-9.0.0-src"
}

function Get-DefaultIsisBuildDir {
    $repoRoot = Get-RepoRoot
    return Join-Path $repoRoot "build\windows\isis-build"
}

function Get-DefaultIsisPrefix {
    $repoRoot = Get-RepoRoot
    return Join-Path $repoRoot "build\windows\isis-prefix"
}

function Resolve-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }
    return $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
}
```

- [ ] **Step 2: Add ISIS source fetch script**

Create `ports/windows/isis/fetch_isis_900.ps1` with this content:

```powershell
param(
    [string]$SourceDir,
    [string]$Repository = "https://github.com/DOI-USGS/ISIS3.git",
    [string]$Ref = "9.0.0"
)

. "$PSScriptRoot\common.ps1"

Require-Command git

if (-not $SourceDir) {
    $SourceDir = Get-DefaultIsisSourceDir
}
$SourceDir = Resolve-FullPath $SourceDir

if (Test-Path (Join-Path $SourceDir ".git")) {
    Write-Step "source checkout already exists: $SourceDir"
    git -C $SourceDir fetch --tags --prune
    git -C $SourceDir checkout $Ref
} else {
    Write-Step "cloning ISIS source to $SourceDir"
    git clone --branch $Ref --depth 1 $Repository $SourceDir
}

Write-Step "ISIS source is ready at $SourceDir"
```

- [ ] **Step 3: Add ISIS patch application script**

Create `ports/windows/isis/apply_patches.ps1` with this content:

```powershell
param([string]$SourceDir)

. "$PSScriptRoot\common.ps1"

Require-Command git

if (-not $SourceDir) {
    $SourceDir = Get-DefaultIsisSourceDir
}
$SourceDir = Resolve-FullPath $SourceDir
$patchDir = Join-Path $PSScriptRoot "patches"

if (-not (Test-Path (Join-Path $SourceDir ".git"))) {
    Fail "ISIS source checkout not found: $SourceDir"
}

$patches = Get-ChildItem -Path $patchDir -Filter "*.patch" | Sort-Object Name
if ($patches.Count -eq 0) {
    Write-Step "no patch files found in $patchDir"
    exit 0
}

foreach ($patch in $patches) {
    Write-Step "applying $($patch.Name)"
    git -C $SourceDir apply --check $patch.FullName
    git -C $SourceDir apply $patch.FullName
}
```

- [ ] **Step 4: Add ISIS configure script**

Create `ports/windows/isis/configure_isis.ps1` with this content:

```powershell
param(
    [string]$SourceDir,
    [string]$BuildDir,
    [string]$Prefix,
    [string]$BuildType = "Release"
)

. "$PSScriptRoot\common.ps1"

Require-Command cmake
Require-Command ninja

if (-not $SourceDir) { $SourceDir = Get-DefaultIsisSourceDir }
if (-not $BuildDir) { $BuildDir = Get-DefaultIsisBuildDir }
if (-not $Prefix) { $Prefix = Get-DefaultIsisPrefix }

$SourceDir = Resolve-FullPath $SourceDir
$BuildDir = Resolve-FullPath $BuildDir
$Prefix = Resolve-FullPath $Prefix

Write-Step "configuring ISIS"
cmake -S $SourceDir -B $BuildDir -G Ninja `
    -DCMAKE_BUILD_TYPE=$BuildType `
    -DCMAKE_INSTALL_PREFIX=$Prefix `
    -DCMAKE_PREFIX_PATH=$env:CONDA_PREFIX
```

- [ ] **Step 5: Add ISIS build script**

Create `ports/windows/isis/build_isis.ps1` with this content:

```powershell
param(
    [string]$BuildDir,
    [int]$Jobs = 0
)

. "$PSScriptRoot\common.ps1"

Require-Command cmake

if (-not $BuildDir) { $BuildDir = Get-DefaultIsisBuildDir }
$BuildDir = Resolve-FullPath $BuildDir

if ($Jobs -gt 0) {
    cmake --build $BuildDir --parallel $Jobs
} else {
    cmake --build $BuildDir
}
```

- [ ] **Step 6: Add ISIS install script**

Create `ports/windows/isis/install_isis.ps1` with this content:

```powershell
param([string]$BuildDir)

. "$PSScriptRoot\common.ps1"

Require-Command cmake

if (-not $BuildDir) { $BuildDir = Get-DefaultIsisBuildDir }
$BuildDir = Resolve-FullPath $BuildDir

Write-Step "installing ISIS from $BuildDir"
cmake --install $BuildDir
```

- [ ] **Step 7: Add ISIS prefix verification script**

Create `ports/windows/isis/verify_isis_prefix.ps1` with this content:

```powershell
param([string]$Prefix)

. "$PSScriptRoot\common.ps1"

if (-not $Prefix) { $Prefix = Get-DefaultIsisPrefix }
$Prefix = Resolve-FullPath $Prefix

$includeCandidates = @(
    Join-Path $Prefix "include\isis",
    Join-Path $Prefix "Library\include\isis"
)
$libCandidates = @(
    Join-Path $Prefix "lib",
    Join-Path $Prefix "Library\lib"
)
$binCandidates = @(
    Join-Path $Prefix "bin",
    Join-Path $Prefix "Library\bin"
)

$includeDir = $includeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$libDir = $libCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$binDir = $binCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $includeDir) { Fail "missing ISIS include directory under $Prefix" }
if (-not $libDir) { Fail "missing ISIS import library directory under $Prefix" }
if (-not $binDir) { Fail "missing ISIS runtime DLL directory under $Prefix" }

$coreHeader = Join-Path $includeDir "Cube.h"
$coreLib = Join-Path $libDir "isis.lib"
$coreDll = Join-Path $binDir "isis.dll"

if (-not (Test-Path $coreHeader)) { Fail "missing core header: $coreHeader" }
if (-not (Test-Path $coreLib)) { Fail "missing core import library: $coreLib" }
if (-not (Test-Path $coreDll)) { Fail "missing core runtime DLL: $coreDll" }

$cameraPlugin = @(
    Join-Path $libDir "Camera.plugin",
    Join-Path $binDir "Camera.plugin"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $cameraPlugin) {
    Fail "missing Camera.plugin under $libDir or $binDir"
}

Write-Step "ISIS prefix verified: $Prefix"
Write-Step "include: $includeDir"
Write-Step "lib: $libDir"
Write-Step "bin: $binDir"
```

- [ ] **Step 8: Verify scripts parse**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ports\windows\isis\verify_isis_prefix.ps1 -Prefix build\windows\missing-prefix
```

Expected: fails with a clear message that the include directory is missing. This verifies the script parses and reports the prefix layer.

- [ ] **Step 9: Commit**

```powershell
git add -- ports/windows/isis
git commit -m "build: add windows isis prefix scripts"
```

---

## Task 3: Make CMake Consume Windows ISIS Prefixes

**Files:**
- Modify: `CMakeLists.txt`

- [ ] **Step 1: Guard the Linux-only conda compiler auto-selection**

Replace the opening compiler block with:

```cmake
if(NOT WIN32 AND NOT DEFINED CMAKE_CXX_COMPILER AND DEFINED ENV{CONDA_PREFIX})
  find_program(CONDA_CXX_COMPILER
    NAMES x86_64-conda-linux-gnu-c++
    HINTS
      "$ENV{CONDA_PREFIX}/bin"
      "$ENV{CONDA_PREFIX}/../bin"
      "$ENV{CONDA_PREFIX}/../../bin")

  if(CONDA_CXX_COMPILER)
    set(CMAKE_CXX_COMPILER "${CONDA_CXX_COMPILER}" CACHE FILEPATH
      "C++ compiler selected from the active conda toolchain" FORCE)
  endif()
endif()
```

- [ ] **Step 2: Add a small first-existing helper**

After `find_package(pybind11 CONFIG REQUIRED)`, add:

```cmake
function(pyisis_first_existing_path out_var)
  foreach(candidate IN LISTS ARGN)
    if(candidate AND EXISTS "${candidate}")
      set(${out_var} "${candidate}" PARENT_SCOPE)
      return()
    endif()
  endforeach()
  set(${out_var} "" PARENT_SCOPE)
endfunction()
```

- [ ] **Step 3: Make `ISIS_PREFIX` autodetection platform-aware**

Replace the existing `ISIS_PREFIX` autodetection block with:

```cmake
set(ISIS_PREFIX "$ENV{ISIS_PREFIX}" CACHE PATH "Prefix of an external ISIS installation or conda environment")
if(NOT ISIS_PREFIX AND DEFINED ENV{CONDA_PREFIX})
  if(WIN32)
    if((EXISTS "$ENV{CONDA_PREFIX}/Library/include/isis" OR EXISTS "$ENV{CONDA_PREFIX}/include/isis")
       AND (EXISTS "$ENV{CONDA_PREFIX}/Library/lib/isis.lib" OR EXISTS "$ENV{CONDA_PREFIX}/lib/isis.lib"))
      set(ISIS_PREFIX "$ENV{CONDA_PREFIX}" CACHE PATH "Prefix of an external ISIS installation or conda environment" FORCE)
    endif()
  else()
    if(EXISTS "$ENV{CONDA_PREFIX}/include/isis" AND EXISTS "$ENV{CONDA_PREFIX}/lib/libisis.so")
      set(ISIS_PREFIX "$ENV{CONDA_PREFIX}" CACHE PATH "Prefix of an external ISIS installation or conda environment" FORCE)
    endif()
  endif()
endif()
```

- [ ] **Step 4: Make Qt CMake root platform-aware**

Replace:

```cmake
set(_qt5_cmake_root "${ISIS_PREFIX}/lib/cmake")
```

with:

```cmake
if(WIN32)
  pyisis_first_existing_path(_qt5_cmake_root
    "${ISIS_PREFIX}/Library/lib/cmake"
    "${ISIS_PREFIX}/lib/cmake")
else()
  set(_qt5_cmake_root "${ISIS_PREFIX}/lib/cmake")
endif()
```

- [ ] **Step 5: Make ISIS include/library/runtime/plugin paths platform-aware**

Replace the current `ISIS_INCLUDE_DIR` through `ISIS_PLUGIN_FILE` definitions with:

```cmake
if(WIN32)
  pyisis_first_existing_path(_default_isis_include_dir
    "${ISIS_PREFIX}/Library/include/isis"
    "${ISIS_PREFIX}/include/isis")
  pyisis_first_existing_path(_default_isis_dep_include_dir
    "${ISIS_PREFIX}/Library/include"
    "${ISIS_PREFIX}/include")
  pyisis_first_existing_path(_default_isis_library_dir
    "${ISIS_PREFIX}/Library/lib"
    "${ISIS_PREFIX}/lib")
  pyisis_first_existing_path(_default_isis_runtime_dir
    "${ISIS_PREFIX}/Library/bin"
    "${ISIS_PREFIX}/bin")
  pyisis_first_existing_path(_default_isis_core_library
    "${_default_isis_library_dir}/isis.lib")
  pyisis_first_existing_path(_default_isis_plugin_file
    "${_default_isis_library_dir}/Camera.plugin"
    "${_default_isis_runtime_dir}/Camera.plugin")
else()
  set(_default_isis_include_dir "${ISIS_PREFIX}/include/isis")
  set(_default_isis_dep_include_dir "${ISIS_PREFIX}/include")
  set(_default_isis_library_dir "${ISIS_PREFIX}/lib")
  set(_default_isis_runtime_dir "${ISIS_PREFIX}/lib")
  set(_default_isis_core_library "${_default_isis_library_dir}/libisis.so")
  set(_default_isis_plugin_file "${_default_isis_library_dir}/Camera.plugin")
endif()

set(ISIS_INCLUDE_DIR "${_default_isis_include_dir}" CACHE PATH "Directory containing ISIS headers")
set(ISIS_DEP_INCLUDE_DIR "${_default_isis_dep_include_dir}" CACHE PATH "Directory containing external ISIS dependencies such as CSPICE and Qt headers")
set(ISIS_LIBRARY_DIR "${_default_isis_library_dir}" CACHE PATH "Directory containing ISIS import/shared libraries")
set(ISIS_RUNTIME_DIR "${_default_isis_runtime_dir}" CACHE PATH "Directory containing ISIS runtime shared libraries")
set(ISIS_CORE_LIBRARY "${_default_isis_core_library}" CACHE FILEPATH "Path to the ISIS core import/shared library")
set(ISIS_PLUGIN_FILE "${_default_isis_plugin_file}" CACHE FILEPATH "Path to Camera.plugin")
```

- [ ] **Step 6: Update path validation for runtime dir**

Replace:

```cmake
foreach(required_path IN ITEMS ISIS_INCLUDE_DIR ISIS_DEP_INCLUDE_DIR ISIS_LIBRARY_DIR ISIS_CORE_LIBRARY ISIS_PLUGIN_FILE)
```

with:

```cmake
foreach(required_path IN ITEMS ISIS_INCLUDE_DIR ISIS_DEP_INCLUDE_DIR ISIS_LIBRARY_DIR ISIS_RUNTIME_DIR ISIS_CORE_LIBRARY ISIS_PLUGIN_FILE)
```

- [ ] **Step 7: Make camera library glob platform-aware**

Replace the `file(GLOB ISIS_EXTRA_CAMERA_LIBS ...)` block with:

```cmake
if(ISIS_CAMERA_LIBS)
  set(ISIS_EXTRA_CAMERA_LIBS ${ISIS_CAMERA_LIBS})
else()
  if(WIN32)
    file(GLOB ISIS_EXTRA_CAMERA_LIBS
         "${ISIS_LIBRARY_DIR}/*Camera.lib"
         "${ISIS_LIBRARY_DIR}/MiniRF.lib")
  else()
    file(GLOB ISIS_EXTRA_CAMERA_LIBS
         "${ISIS_LIBRARY_DIR}/lib*Camera.so"
         "${ISIS_LIBRARY_DIR}/libMiniRF.so")
  endif()
  list(REMOVE_DUPLICATES ISIS_EXTRA_CAMERA_LIBS)
endif()
```

- [ ] **Step 8: Make ASP/VW filtering handle Windows paths**

Replace:

```cmake
list(FILTER ISIS_EXTRA_CAMERA_LIBS EXCLUDE REGEX "/lib(Asp|ASP|Vw|VW)[^/]*$")
```

with:

```cmake
list(FILTER ISIS_EXTRA_CAMERA_LIBS EXCLUDE REGEX "[/\\\\](lib)?(Asp|ASP|Vw|VW)[^/\\\\]*$")
```

- [ ] **Step 9: Guard Linux-only compile options**

Wrap both `set_source_files_properties(... COMPILE_OPTIONS "-fpermissive")` calls in:

```cmake
if(NOT MSVC)
  set_source_files_properties(
    src/base/bind_base_shape.cpp
    PROPERTIES COMPILE_OPTIONS "-fpermissive")

  set_source_files_properties(
    src/base/bind_base_shape_support.cpp
    PROPERTIES COMPILE_OPTIONS "-fpermissive")
endif()
```

- [ ] **Step 10: Guard `_GNU_SOURCE` definitions**

Replace both `_GNU_SOURCE` compile definition blocks with platform-aware forms:

```cmake
if(NOT WIN32)
  target_compile_definitions(_isis_core PRIVATE _GNU_SOURCE)
endif()
```

and:

```cmake
if(NOT WIN32)
  target_compile_definitions(isis_cpp_benchmark PRIVATE _GNU_SOURCE)
endif()
```

- [ ] **Step 11: Guard RPATH properties**

Replace the `_isis_core` target property block with:

```cmake
set_target_properties(_isis_core PROPERTIES
  CXX_VISIBILITY_PRESET hidden
  VISIBILITY_INLINES_HIDDEN ON
  LIBRARY_OUTPUT_DIRECTORY "${ISIS_PYBIND_BUILD_PACKAGE_DIR}")

if(NOT WIN32)
  set_target_properties(_isis_core PROPERTIES
    BUILD_RPATH "${ISIS_LIBRARY_DIR}"
    INSTALL_RPATH "${ISIS_LIBRARY_DIR}")
endif()
```

Apply the same pattern to `isis_cpp_benchmark`, keeping
`RUNTIME_OUTPUT_DIRECTORY` always set and RPATH only on non-Windows.

- [ ] **Step 12: Make CTest environment platform-aware**

Replace the `_test_ld_library_path` block and `set_tests_properties` environment
with:

```cmake
if(WIN32)
  set(_test_path "${ISIS_RUNTIME_DIR}")
  if(DEFINED ENV{PATH} AND NOT "$ENV{PATH}" STREQUAL "")
    set(_test_path "${_test_path};$ENV{PATH}")
  endif()
  set(_python_test_environment
      "PYTHONPATH=${CMAKE_CURRENT_BINARY_DIR}/python"
      "PATH=${_test_path}"
      "ISISDATA=${CMAKE_CURRENT_SOURCE_DIR}/tests/data/isisdata/mockup")
else()
  set(_test_ld_library_path "${ISIS_LIBRARY_DIR}")
  if(DEFINED ENV{LD_LIBRARY_PATH} AND NOT "$ENV{LD_LIBRARY_PATH}" STREQUAL "")
    set(_test_ld_library_path "${_test_ld_library_path}:$ENV{LD_LIBRARY_PATH}")
  endif()
  set(_python_test_environment
      "PYTHONPATH=${CMAKE_CURRENT_BINARY_DIR}/python"
      "LD_LIBRARY_PATH=${_test_ld_library_path}"
      "ISISDATA=${CMAKE_CURRENT_SOURCE_DIR}/tests/data/isisdata/mockup")
endif()

set_tests_properties(python-unit-tests PROPERTIES
  ENVIRONMENT "${_python_test_environment}")
```

- [ ] **Step 13: Add runtime-dir status output**

Add:

```cmake
message(STATUS "Using ISIS runtime dir: ${ISIS_RUNTIME_DIR}")
```

after the existing library dir status message.

- [ ] **Step 14: Verify CMake formatting**

Run:

```powershell
git diff --check -- CMakeLists.txt
```

Expected: no output and exit code 0.

- [ ] **Step 15: Linux smoke configure validation**

On Linux with `asp360_new`:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" -DISIS_PREFIX="$ISIS_PREFIX" -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON -DCMAKE_CXX_COMPILER="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-c++"
```

Expected: configure succeeds and status output shows Linux `lib` paths.

- [ ] **Step 16: Commit**

```powershell
git add -- CMakeLists.txt
git commit -m "build: make isis prefix detection platform-aware"
```

---

## Task 4: Add pyisis Windows Build and Test Scripts

**Files:**
- Create: `ports/windows/pyisis/common.ps1`
- Create: `ports/windows/pyisis/configure_pyisis.ps1`
- Create: `ports/windows/pyisis/build_pyisis.ps1`
- Create: `ports/windows/pyisis/test_pyisis_smoke.ps1`
- Create: `ports/windows/pyisis/test_pyisis_basic.ps1`

- [ ] **Step 1: Add shared pyisis PowerShell helpers**

Create `ports/windows/pyisis/common.ps1` with this content:

```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    $scriptDir = Split-Path -Parent $PSScriptRoot
    return (Resolve-Path (Join-Path $scriptDir "..\..")).Path
}

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "[windows-pyisis] $Message"
}

function Fail {
    param([Parameter(Mandatory = $true)][string]$Message)
    throw "[windows-pyisis] $Message"
}

function Require-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Fail "required command not found: $Name"
    }
}

function Get-DefaultBuildDir {
    $repoRoot = Get-RepoRoot
    return Join-Path $repoRoot "build\windows\pyisis-build"
}

function Resolve-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }
    return $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
}

function Require-IsisPrefix {
    param([string]$Prefix)
    if (-not $Prefix) {
        $Prefix = $env:ISIS_PREFIX
    }
    if (-not $Prefix) {
        Fail "ISIS_PREFIX is not set. Set `$env:ISIS_PREFIX or pass -IsisPrefix."
    }
    return Resolve-FullPath $Prefix
}

function Add-IsisRuntimePath {
    param([Parameter(Mandatory = $true)][string]$IsisPrefix)
    $runtimeCandidates = @(
        Join-Path $IsisPrefix "Library\bin",
        Join-Path $IsisPrefix "bin"
    )
    foreach ($candidate in $runtimeCandidates) {
        if (Test-Path $candidate) {
            $env:PATH = "$candidate;$env:PATH"
        }
    }
}

function Set-PyisisTestEnvironment {
    param(
        [Parameter(Mandatory = $true)][string]$BuildDir,
        [Parameter(Mandatory = $true)][string]$IsisPrefix
    )
    $repoRoot = Get-RepoRoot
    $env:PYTHONPATH = "$BuildDir\python;$repoRoot\tests\unitTest"
    $env:ISISDATA = "$repoRoot\tests\data\isisdata\mockup"
    Add-IsisRuntimePath -IsisPrefix $IsisPrefix
}
```

- [ ] **Step 2: Add configure script**

Create `ports/windows/pyisis/configure_pyisis.ps1` with this content:

```powershell
param(
    [string]$BuildDir,
    [string]$IsisPrefix,
    [string]$BuildType = "Release",
    [string]$PythonExecutable
)

. "$PSScriptRoot\common.ps1"

Require-Command cmake
Require-Command ninja

$repoRoot = Get-RepoRoot
if (-not $BuildDir) { $BuildDir = Get-DefaultBuildDir }
$BuildDir = Resolve-FullPath $BuildDir
$IsisPrefix = Require-IsisPrefix -Prefix $IsisPrefix

if (-not $PythonExecutable) {
    $PythonExecutable = (Get-Command python).Source
}

Write-Step "configuring pyisis"
cmake -S $repoRoot -B $BuildDir -G Ninja `
    -DCMAKE_BUILD_TYPE=$BuildType `
    -DPython3_EXECUTABLE=$PythonExecutable `
    -DISIS_PREFIX=$IsisPrefix `
    -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON
```

- [ ] **Step 3: Add build script**

Create `ports/windows/pyisis/build_pyisis.ps1` with this content:

```powershell
param(
    [string]$BuildDir,
    [int]$Jobs = 0
)

. "$PSScriptRoot\common.ps1"

Require-Command cmake

if (-not $BuildDir) { $BuildDir = Get-DefaultBuildDir }
$BuildDir = Resolve-FullPath $BuildDir

if ($Jobs -gt 0) {
    cmake --build $BuildDir --parallel $Jobs
} else {
    cmake --build $BuildDir
}

$packageDir = Join-Path $BuildDir "python\isis_pybind"
$pyd = Get-ChildItem -Path $packageDir -Filter "_isis_core*.pyd" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $pyd) {
    Fail "build completed but _isis_core*.pyd was not found under $packageDir"
}
Write-Step "built $($pyd.FullName)"
```

- [ ] **Step 4: Add smoke test script**

Create `ports/windows/pyisis/test_pyisis_smoke.ps1` with this content:

```powershell
param(
    [string]$BuildDir,
    [string]$IsisPrefix,
    [string]$PythonExecutable
)

. "$PSScriptRoot\common.ps1"

if (-not $BuildDir) { $BuildDir = Get-DefaultBuildDir }
$BuildDir = Resolve-FullPath $BuildDir
$IsisPrefix = Require-IsisPrefix -Prefix $IsisPrefix
if (-not $PythonExecutable) { $PythonExecutable = (Get-Command python).Source }

Set-PyisisTestEnvironment -BuildDir $BuildDir -IsisPrefix $IsisPrefix

$repoRoot = Get-RepoRoot
Write-Step "running smoke import"
& $PythonExecutable (Join-Path $repoRoot "tests\smoke_import.py")
```

- [ ] **Step 5: Add basic test script**

Create `ports/windows/pyisis/test_pyisis_basic.ps1` with this content:

```powershell
param(
    [string]$BuildDir,
    [string]$IsisPrefix,
    [string]$PythonExecutable,
    [string]$TestList
)

. "$PSScriptRoot\common.ps1"

if (-not $BuildDir) { $BuildDir = Get-DefaultBuildDir }
$BuildDir = Resolve-FullPath $BuildDir
$IsisPrefix = Require-IsisPrefix -Prefix $IsisPrefix
if (-not $PythonExecutable) { $PythonExecutable = (Get-Command python).Source }
if (-not $TestList) { $TestList = Join-Path $PSScriptRoot "basic_tests.txt" }

if (-not (Test-Path $TestList)) {
    Fail "test list not found: $TestList"
}

Set-PyisisTestEnvironment -BuildDir $BuildDir -IsisPrefix $IsisPrefix

$modules = Get-Content $TestList | Where-Object {
    $line = $_.Trim()
    $line -and -not $line.StartsWith("#")
}

foreach ($module in $modules) {
    Write-Step "running unittest module: $module"
    & $PythonExecutable -m unittest $module -v
    if ($LASTEXITCODE -ne 0) {
        Fail "unit test module failed: $module"
    }
}
```

- [ ] **Step 6: Parse-check scripts**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ports\windows\pyisis\test_pyisis_basic.ps1 -IsisPrefix build\windows\missing-prefix
```

Expected: fails with a clear message from the prefix/runtime layer before any unit test runs.

- [ ] **Step 7: Commit**

```powershell
git add -- ports/windows/pyisis
git commit -m "build: add windows pyisis scripts"
```

---

## Task 5: Validate Linux Preservation and Windows Script Surfaces

**Files:**
- Modify only files changed by Tasks 1 through 4 if validation exposes concrete defects.

- [ ] **Step 1: Verify whitespace and staged scope**

Run:

```powershell
git diff --check
git status --short --branch
```

Expected: no whitespace errors. Status shows only intended files until they are committed.

- [ ] **Step 2: Run Windows parse checks without a real ISIS prefix**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ports\windows\isis\verify_isis_prefix.ps1 -Prefix build\windows\missing-prefix
powershell -NoProfile -ExecutionPolicy Bypass -File ports\windows\pyisis\test_pyisis_basic.ps1 -IsisPrefix build\windows\missing-prefix
```

Expected: both fail clearly at prefix validation, proving script parsing and error classification work.

- [ ] **Step 3: Run Linux smoke validation on a Linux machine with `asp360_new`**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tests/smoke_import.py
```

Expected: smoke import still passes.

- [ ] **Step 4: Record known Windows blockers**

If ISIS 9.0.0 source does not configure or build on Windows after the script
surface is in place, create or update `ports/windows/isis/README.md` with a
section named `Known Windows ISIS 9.0.0 blockers` and list the exact failing
command and error category.

- [ ] **Step 5: Commit validation documentation changes**

```powershell
git add -- ports/windows
git commit -m "docs: record windows port validation status"
```

---

## Spec Coverage Check

| Spec requirement | Plan task |
| --- | --- |
| Reproducible Windows local developer workflow | Tasks 1, 2, 4 |
| ISIS source, patch, build, and prefix separation | Tasks 1, 2 |
| Windows-native `ISIS_PREFIX` contract | Tasks 1, 2 |
| Build `_isis_core*.pyd` | Tasks 3, 4 |
| Run smoke and curated basic tests | Tasks 1, 4, 5 |
| Preserve Linux behavior | Tasks 3, 5 |
| Avoid full ISIS source vendoring | Tasks 1, 2 |
| Avoid first-milestone superbuild | Tasks 1, 2, 4 |
| Keep GitHub Actions and packaging outside first milestone | Tasks 1, 5 |
| Keep target on ISIS 9.0.0 | Tasks 1, 2 |
| Classify ISIS prefix, DLL, plugin, import, and test failures | Tasks 2, 4, 5 |

## Self-Review Notes

- The plan uses `build/windows/...` as default generated paths to avoid editing
  repository guardrail files while still keeping generated artifacts ignored.
- The first implementation slice creates script surfaces and CMake platform
  detection. It does not pretend to have solved upstream ISIS 9.0.0 MSVC
  compile errors before those errors are observed.
- The acceptance criteria remain the full first milestone from the design spec.
