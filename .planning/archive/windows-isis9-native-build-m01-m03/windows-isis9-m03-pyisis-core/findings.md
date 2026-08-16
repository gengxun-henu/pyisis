# Windows ISIS 9.0.0 and PyISIS Native Build Milestones

# Findings: Build and test isis_pybind._isis_core

## Verified Facts

- Milestone ID: `windows-isis9-m03-pyisis-core`.
- The milestone is active on repository-root `main` at commit `9eb48c6a`;
  `print.prt` is a preserved, unrelated ISIS side effect.
- The declared source plans require configuring and building the CPython 3.12
  extension against `build/windows/isis-prefix`, followed by the repository
  Windows smoke-import and basic-test scripts.
- `D:\pyisis-win-env\python.exe`, `build/windows/isis-prefix/lib/isis.dll`,
  and `build/windows/isis-prefix/lib/isis.lib` exist.
- Fresh CMake configure created `build/windows/pyisis-build` successfully with
  MSVC 19.39, Python 3.12.13, pybind11 3.1.0, ISIS 9.0.0, and Qt5. ASP/VW
  camera libraries and Embree shape bindings are disabled.
- `configure_pyisis.ps1` resolves the ISIS headers, import library, runtime DLL,
  and `Camera.plugin` from the installed prefix, while dependency headers and
  libraries come from the active `CONDA_PREFIX` before the ISIS prefix.
- The Windows basic gate contains nine focused unittest modules covering value
  types, PVL, geometry, math, and filters. Both test scripts set `PYTHONPATH`,
  `ISISROOT`, `ISIS_PREFIX`, `ISISDATA`, and the runtime DLL search path.
- The first preflight found MSVC, Git, CMake, and Ninja but omitted the base
  Conda command. Adding `C:\Users\gx\miniconda3\Scripts` made the repository
  prerequisite check pass; Python reports 3.12.13 and cache tag `cpython-312`.
- Fresh ISIS prefix hashes still match M2 completion evidence: `isis.dll`
  `7291ff4ae9683bdae8c758ae9e615eb9f5cfb23da9253ad15d45a69583044420`
  and `isis.lib`
  `1582d80acd2d5d9b479cee1b24ee88065b37399be712cc92ab119051e2216a3d`.
- The 24-job Ninja build completed all 42 steps with exit code 0 in about 150
  seconds; no compiler or linker failure occurred.
- The required `_isis_core.cp312-win_amd64.pyd` exists at 5,595,648 bytes with
  SHA-256 `66465d02a0a365eb2a821b63505f14fe4e856c5a1ad18024a461dd1a2ad3536b`.
- The repository smoke-import script completed in a fresh Python process with
  exit code 0 and reported `smoke import ok` using the mock ISISDATA.
- A direct fresh-process import resolved `_isis_core.__file__` to
  `build/windows/pyisis-build/python/isis_pybind/_isis_core.cp312-win_amd64.pyd`.
- All nine Windows basic modules passed: 329 tests, 0 failures, 0 skips, and one
  expected failure reported by `math_unit_test`.

## Evidence-Based Inference

- None recorded.

## Unresolved Items

- None; only the manager-owned completion transition remains.

## Decisions

| Decision | Rationale |
|---|---|

## Resources

- Canonical registry: `.planning/milestones.v1.json`
