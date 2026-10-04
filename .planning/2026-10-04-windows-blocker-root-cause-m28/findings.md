# Findings & Decisions

## Requirements
- Preserve exact evidence for the two Windows release blockers.
- Define the smallest Windows-side checks needed before changing source or packaging.

## Research Findings
- `ports/windows/isis/build_spiceql.ps1` already applies the 1.4.1 export patch, checks that the DLL exports `strSclkToEt`, and compiles a downstream MSVC link probe.
- The historical ISIS 10 Windows failure occurs later while linking ISIS `mgs.dll`, with `LNK2019` for the decorated `SpiceQL::strSclkToEt` symbol and `LNK1120`.
- This indicates a mismatch between the import library selected by ISIS and the header/SpiceQL ABI used by the build, even though the standalone probe is intended to catch a simpler link path.
- Latest self-hosted CI failures occur during checkout cleanup: stale `.deps/opencv-cuda/src/opencv` submodule mapping and EACCES while removing the existing workspace.

## Remediation Checklist
1. On Windows, run `dumpbin /exports` on the installed `SpiceQL.dll` and `dumpbin /linkermember` on every candidate `SpiceQL.lib`.
2. Capture the exact decorated symbol from the header and compare it with the import library selected by `mgs.dll`.
3. Ensure ISIS CMake resolves the same prefix library that passed the downstream link probe.
4. Reset or recreate the self-hosted runner workspace with correct ownership, then rerun checkout before judging source changes.

## Issues Encountered
| Issue | Resolution |
|---|---|
| No Windows/MSVC toolchain in this Linux checkout | Record the checks and defer execution to the Windows runner. |

## Resources
- `ports/windows/isis/build_spiceql.ps1`
- `ports/windows/isis/patches/spiceql-1.4.1/0001-Export-SpiceQL-symbols-on-Windows.patch`
- `.github/workflows/reusable-pybind-build-self-hosted.yml`
- `.github/actions/normalized-safe-checkout/action.yml`
- GitHub Actions run `30066283510`
- GitHub Actions run `37179630887`
