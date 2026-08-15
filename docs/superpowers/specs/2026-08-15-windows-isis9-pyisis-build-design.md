# Windows ISIS 9.0.0 and PyISIS Native Build Design

## Goal

Build USGS ISIS 9.0.0 from source on this Windows 11 x64 workstation, install
and verify a reusable native SDK/runtime prefix, then compile and test
`isis_pybind._isis_core` against that exact prefix with CPython 3.12.

## Selected Approach

Use the repository-owned Windows port under `ports/windows/`. Create a fresh
short-path micromamba environment from
`ports/windows/env/pyisis-isis-win64.yml`, activate the Visual Studio 2022 x64
MSVC toolchain, fetch the upstream `9.0.0` tag, apply the tracked Windows patch
queue, and build with CMake and Ninja. This reuses the path already documented
and previously verified by the repository instead of introducing a parallel
manual CMake workflow or downloading CI binaries.

The dependency environment will use `D:\pyisis-win-env`, with micromamba state
under `D:\mamba\pyisis-isis9`. Generated source, build, installation, and test
outputs will remain under the repository-ignored `build/windows/` hierarchy so
the existing scripts and validation paths remain authoritative.

## Milestones

1. **Windows build environment**: create the conda environment, activate MSVC,
   and pass the repository prerequisite checks.
2. **ISIS 9.0.0 native prefix**: fetch the pinned source, apply all tracked
   patches, configure, build with `-j 1`, install, verify the prefix, and run
   representative ISIS application smoke tests.
3. **PyISIS core extension**: configure and build the pybind11 extension against
   the verified prefix, then pass smoke import and the Windows basic test set.

Each milestone has one active session at a time. Later milestones cannot start
until the predecessor has structured fresh completion evidence.

## Failure Handling

Treat repository scripts, the active conda headers/libraries, and MSVC linker
output as the source of truth. On failure, preserve logs, identify the first
root-cause error, and apply the smallest targeted correction. Any product-code
or build-script fix must follow the repository's scoped instructions and gain a
focused regression test before the build resumes.

## Validation and Artifacts

The required durable outputs are the verified ISIS DLL/import library and the
CPython 3.12 `_isis_core` extension. Validation consists of the Windows
prerequisite checker, ISIS prefix verification, representative ISIS APP smoke
tests, Python smoke import, and the repository's Windows basic unit-test list.
Completion evidence records exact commands, pass/fail/skip counts, artifact
hashes, prerequisite paths, and classified Git state.

After all validation succeeds, preserve the installed ISIS prefix, extension,
and reports. Remove only disposable caches or staging trees whose exact paths
have been resolved and whose contents are not needed for incremental recovery.

