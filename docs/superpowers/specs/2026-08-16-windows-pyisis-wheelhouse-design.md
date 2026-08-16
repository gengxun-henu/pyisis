# Windows PyISIS Wheelhouse and Native APP Roadmap Design

## Purpose

Complete a release-grade local Windows wheelhouse for the existing CPython
3.12 / ISIS 9.0.0 PyISIS build while preserving a strict boundary between the
Python distribution and standalone ISIS applications. Record the separate
native-application product as the follow-up M05 milestone.

## Scope

M04 is Windows-only and targets the verified local environment:

- Windows 11 x64
- CPython 3.12 from `D:\pyisis-win-env\python.exe`
- ISIS 9.0.0 from `build/windows/isis-prefix`
- package version `1.3.0rc2`
- wheel platform `win_amd64`

M04 builds and verifies a complete local wheelhouse. It does not upload to
PyPI or TestPyPI, create a GitHub release, build Linux wheels, or package ISIS
CLI/GUI applications.

## Product Boundary

The Windows PyISIS wheelhouse contains three distributions:

1. `usgs-pyisis`
   - Python facade and low-level Python package
   - `_isis_core.cp312-win_amd64.pyd`
2. `usgs-pyisis-runtime-win64`
   - `isis.dll` and its recursive non-system PE dependency closure
   - Qt, SPICE, plugins, ISIS preferences, and runtime configuration needed by
     the Python extension
3. `usgs-pyisis-isisdata-minimal`
   - minimum ISISDATA required by import and the declared basic tests

The runtime wheel intentionally excludes ISIS APP executables and APP XML.
Programs such as `reduce.exe`, `jigsaw.exe`, and `qnet.exe` remain part of the
separate ISIS Native Windows product line.

## Architecture and Data Flow

M04 reuses the repository's existing packaging path rather than adding a
parallel build system:

1. `tools/packaging/build_wheels.ps1` receives the verified ISIS prefix,
   CPython executable, dependency prefix, output directory, and package
   version.
2. `tools/packaging/stage_runtime_win64.py` stages the runtime wheel and walks
   normal PE imports plus export-forwarder targets with MSVC `dumpbin`.
3. The script builds the runtime, minimal-data, and binding wheels into
   `build/windows/wheelhouse-isis9`.
4. The dependency-closure report is written next to the wheels and must contain
   no unresolved non-system DLL.
5. `tools/packaging/test_wheel_install.py` creates a fresh disposable virtual
   environment, installs only from the generated wheelhouse, validates imports
   and ISIS version, and runs the repository's declared basic test list.
6. A final report records wheel filenames, sizes, SHA-256 hashes, dependency
   closure status, test counts, interpreter ABI, ISIS version, OS, and
   architecture.

The clean-install process must not obtain Python modules from the repository
source tree or `build/windows/pyisis-build`, and it must not rely on the build
environment's ISIS/Qt/SPICE DLL directories. Native dependencies must resolve
from the installed runtime wheel.

## Completion Artifacts

The retained M04 artifacts are:

- `build/windows/wheelhouse-isis9/usgs_pyisis-1.3.0rc2-cp312-cp312-win_amd64.whl`
- `build/windows/wheelhouse-isis9/usgs_pyisis_runtime_win64-1.3.0rc2-py3-none-win_amd64.whl`
- `build/windows/wheelhouse-isis9/usgs_pyisis_isisdata_minimal-1.3.0rc2-py3-none-any.whl`
- `build/windows/wheelhouse-isis9/usgs-pyisis-runtime-win64-dll-dependencies.json`
- `build/windows/reports/pyisis-wheelhouse-isis9-validation.json`

Filename normalization follows Python wheel conventions. Validation must fail
if a required artifact is absent, an unexpected wheel is present, or any hash
cannot be reproduced.

## Validation Gate

M04 is complete only when all of the following are freshly verified:

- focused unit tests for Windows runtime staging, Python packaging, wheel
  workflow selection, and wheel-install tooling pass
- all three expected wheels are built with the declared version and tags
- the dependency report has an empty `unresolved` collection
- a new virtual environment installs `usgs-pyisis==1.3.0rc2` using only the
  local wheelhouse
- `import pyisis` and `import isis_pybind` succeed in a fresh process
- the installed extension reports ISIS 9.0.0
- the declared Windows basic test list passes with explicit pass/fail/skip
  counts
- all retained artifacts have recorded SHA-256 hashes

The existing modified `print.prt` is unrelated local state and must remain
unstaged and unmodified.

## Failure Handling

- An unresolved non-system DLL stops the build; do not copy arbitrary files or
  broaden runtime globs to suppress the error.
- A missing wheel or incorrect tag stops validation before installation.
- A clean-install import failure is diagnosed from the installed wheel payload
  and PE dependency report, not masked with conda or build-tree PATH entries.
- Packaging-script defects discovered by the build receive focused regression
  tests and surgical fixes before the build is retried.
- Disposable staging directories and virtual environments are removed only
  after the retained artifacts and validation report are resolved and verified.

## M05: Native ISIS Windows APP Distribution

M05 is a separate follow-up product milestone. It begins after M04 and does not
change the PyISIS wheel contents.

M05 will design and produce a redistributable Windows application package that:

- includes ISIS APP executables, APP XML, required DLLs, plugins, preferences,
  and launcher/runtime environment support
- guarantees at least `reduce`, `jigsaw`, and `qnet`
- evaluates whether the first release contains the verified 150-APP set or a
  smaller explicitly named subset
- compares ZIP, installer, and other native distribution formats before
  selecting one
- verifies representative CLI applications and launches the three required GUI
  applications from a clean extracted or installed location without the build
  prefix

The M05 format and exact APP inventory require their own design approval. M04
must not pre-empt those decisions by embedding APP files in a wheel.

## Planning Workflow

The current canonical milestone registry contains completed M01 through M03,
and the installed milestone manager has no append operation. M04 therefore uses
a dedicated `planning-with-files` execution plan derived from this approved
SPEC. M05 remains a documented follow-up until its separate design session.
The existing canonical registry and generated milestone index must not be
edited manually.
