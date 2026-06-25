# Windows Native Port Design

## Summary

The first Windows milestone is local, test-level native support for pyisis.
The project will maintain an ISIS 9.0.0 Windows SDK/runtime subset inside the
pyisis fork as a reproducible porting workflow, then build pyisis against that
installed Windows prefix.

This design uses the selected route: a two-stage prefix-driven port.

1. Build and install a Windows-native ISIS 9.0.0 SDK/runtime subset.
2. Configure, build, and test pyisis against that installed `ISIS_PREFIX`.

The first milestone uses MSVC, Ninja, and conda-forge dependencies. It does not
require GitHub Actions, full ISIS CLI coverage, real production `ISISDATA`, or
complete upstream ISIS test coverage.

## Goals

- Provide a reproducible Windows local developer workflow in the pyisis fork.
- Keep ISIS source, ISIS patches, pyisis build logic, and generated artifacts
  separated.
- Produce a Windows-native `ISIS_PREFIX` with the headers, import libraries,
  DLLs, plugin metadata, and runtime dependencies needed by pyisis.
- Build `isis_pybind._isis_core` as a Windows Python extension module (`.pyd`).
- Run `tests/smoke_import.py` and a curated set of basic unit tests on Windows.
- Preserve the existing Linux build path and distribution assumptions.

## Non-Goals

- Do not vendor the full ISIS source tree into tracked pyisis files.
- Do not make the first milestone a one-command superbuild.
- Do not make conda packaging or GitHub Actions a first-milestone blocker.
- Do not promise full ISIS CLI, GUI, app-test, or production `ISISDATA`
  support in the first milestone.
- Do not change the pyisis binding target away from ISIS 9.0.0.

## Architecture

The Windows port is split into two layers.

The ISIS layer lives under `ports/windows/isis/`. It is responsible for getting
ISIS 9.0.0 source code, applying Windows patches, configuring CMake for MSVC and
Ninja, building the SDK/runtime subset, installing into a local prefix, and
validating that prefix.

The pyisis layer lives in the existing top-level build plus helper scripts under
`ports/windows/pyisis/`. It consumes the installed ISIS prefix. It does not
build ISIS itself.

This separation keeps failure boundaries clear:

- ISIS configure, compile, install, or prefix-shape failures belong to
  `ports/windows/isis/`.
- pyisis configure, link, import, and unit-test failures belong to pyisis CMake,
  bindings, or test setup.
- Runtime DLL and plugin lookup failures are classified separately from both
  compile/link failures and Python behavior failures.

## Repository Layout

Tracked files:

```text
ports/windows/
  README.md
  env/
    pyisis-isis-win64.yml
  isis/
    README.md
    fetch_isis_900.ps1
    apply_patches.ps1
    configure_isis.ps1
    build_isis.ps1
    install_isis.ps1
    verify_isis_prefix.ps1
    patches/
      0001-windows-cmake-sdk-runtime-subset.patch
      0002-windows-path-plugin-loading.patch
  pyisis/
    configure_pyisis.ps1
    build_pyisis.ps1
    test_pyisis_smoke.ps1
    test_pyisis_basic.ps1
    basic_tests.txt
```

Generated or downloaded local paths:

```text
_external/isis-9.0.0-src/
_build/isis-win64/
_prefix/isis-win64/
```

The generated paths should be ignored by git. The tracked patch set is the
source of truth for ISIS Windows modifications; the downloaded ISIS source tree
is disposable and reproducible.

## ISIS Windows SDK/Runtime Prefix

The first ISIS milestone provides only the SDK/runtime surface needed by pyisis.
The installed prefix should provide, at minimum:

- ISIS headers under `include/isis` or `Library/include/isis`.
- MSVC import libraries, including `isis.lib`, under `lib` or `Library/lib`.
- Runtime DLLs, including `isis.dll`, under `bin` or `Library/bin`.
- Import libraries and DLLs for camera/projection libraries linked by pyisis.
- Qt and third-party runtime DLLs required for importing `_isis_core.pyd`.
- A usable `Camera.plugin` or Windows-equivalent camera plugin discovery path.
- Any projection or plugin metadata needed by the curated pyisis smoke/basic
  tests.

The ISIS verification script should check:

- required directories exist;
- key headers exist;
- key `.lib` and `.dll` files exist;
- camera/projection plugin files are discoverable;
- runtime DLLs are locatable through the expected Windows runtime path;
- a minimal MSVC C++ smoke program can compile, link against `isis.lib`, and
  start successfully.

The first milestone should continue using `tests/data/isisdata/mockup` for
pyisis validation. Real mission data and full SPICE/NAIF runtime workflows are
outside the first milestone.

## pyisis CMake Changes

The top-level CMake should become platform-aware while preserving the current
Linux behavior.

On Linux:

- Continue preferring the active conda ISIS prefix.
- Continue looking for `include/isis`, `lib/libisis.so`, `Camera.plugin`, and
  extra `.so` camera/projection libraries.
- Continue using RPATH where appropriate.
- Continue supporting the existing conda compiler path.

On Windows:

- Resolve `ISIS_PREFIX` from the explicit CMake option or environment variable.
- Search for headers under both `${ISIS_PREFIX}/include/isis` and
  `${ISIS_PREFIX}/Library/include/isis`.
- Search for import libraries under `${ISIS_PREFIX}/lib` and
  `${ISIS_PREFIX}/Library/lib`.
- Search for runtime DLLs under `${ISIS_PREFIX}/bin` and
  `${ISIS_PREFIX}/Library/bin`.
- Link against `isis.lib` and any required camera/projection import libraries.
- Verify the corresponding runtime DLLs exist during configuration or in a
  Windows-specific verification script.
- Do not set Linux RPATH properties on Windows.
- Let pybind11 produce `_isis_core*.pyd` in `build/python/isis_pybind/`.

The install layout remains a Python package directory containing:

```text
isis_pybind/
  __init__.py
  _isis_core*.pyd
  LICENSE
```

## Windows Test Scripts

The Windows pyisis scripts should provide predictable environment setup rather
than requiring users to memorize path details.

At test time they should set:

```powershell
$env:PYTHONPATH = "$PWD\build\python;$PWD\tests\unitTest"
$env:ISISDATA = "$PWD\tests\data\isisdata\mockup"
$env:PATH = "$env:ISIS_PREFIX\Library\bin;$env:ISIS_PREFIX\bin;$env:PATH"
```

The first validation tier is:

```powershell
python tests\smoke_import.py
```

The second validation tier is a curated list in
`ports/windows/pyisis/basic_tests.txt`. The list should start with tests that do
not require production ISIS data and should expand only when failures are
understood. Candidate areas include angle, distance, displacement, latitude,
longitude, PVL, geometry, math, statistics, and light cube/camera factory paths
that work with mock data.

The test scripts should classify common failure layers:

- ISIS prefix incomplete;
- DLL missing from `PATH`;
- plugin metadata or plugin DLL not discoverable;
- `_isis_core.pyd` import failure;
- unit-test behavior regression;
- missing or inadequate mock `ISISDATA`.

## Acceptance Criteria

The first milestone is complete only when all of the following are true on a
Windows developer machine:

1. `ports/windows/isis/verify_isis_prefix.ps1` passes for a local
   ISIS 9.0.0 Windows prefix.
2. `ports/windows/pyisis/configure_pyisis.ps1` configures pyisis with MSVC,
   Ninja, conda Python, and the Windows `ISIS_PREFIX`.
3. `ports/windows/pyisis/build_pyisis.ps1` produces
   `build/python/isis_pybind/_isis_core*.pyd`.
4. The built package directory contains `__init__.py`, `_isis_core*.pyd`, and
   `LICENSE`.
5. `ports/windows/pyisis/test_pyisis_smoke.ps1` passes.
6. `ports/windows/pyisis/test_pyisis_basic.ps1` passes for every test listed in
   `ports/windows/pyisis/basic_tests.txt`.
7. Existing Linux configure/build/test workflows continue to work.

## Risks and Mitigations

### ISIS Unix Assumptions

ISIS 9.0.0 may assume Unix shared-library names, `dlopen`, POSIX paths, shell
tools, or symbol visibility behavior. Keep patches small and numbered. Each
patch should solve one explainable Windows issue and include enough context to
rebase or upstream later.

### Dependency Availability

Some ISIS 9.0.0 dependencies may not have compatible conda-forge `win-64`
packages. Record explicit dependencies in `ports/windows/env/pyisis-isis-win64.yml`.
When a dependency is missing or ABI-incompatible, classify it as an ISIS port
blocker rather than a pyisis CMake problem.

### DLL and Plugin Loading

Windows has no RPATH equivalent for this use case. Runtime success depends on
`PATH`, plugin lookup paths, and DLL staging. The first milestone should use
script-managed `PATH`. If needed, a later milestone can add DLL staging or a
packaging workflow.

### Scope Creep

Full ISIS command-line application support, production data workflows, conda
packages, and CI are important later milestones, but they are not part of this
first implementation target. Keep the first milestone focused on the SDK/runtime
subset required by pyisis smoke and basic unit tests.

## Implementation Sequence

1. Add Windows port documentation, environment definition, script skeletons, and
   ignored generated directories.
2. Make pyisis CMake prefix detection platform-aware without changing Linux
   behavior.
3. Implement ISIS source fetch, patch application, configure, build, install,
   and prefix verification scripts.
4. Iterate on the ISIS Windows patch set until the SDK/runtime prefix verifies.
5. Build pyisis against the verified Windows prefix.
6. Run smoke and curated basic tests, expanding `basic_tests.txt` only after
   each candidate test is understood.
7. Document known gaps and next milestones.
