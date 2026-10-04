# Findings & Decisions

## Requirements
- Verify the required Linux/Windows × ISIS-version release matrix status.
- Preserve exact CI evidence for any unresolved gate.

## Research Findings
- Historical wheels run `30066283510`: ISIS 10 Linux, ISIS 9 Linux, and ISIS 9 Windows build/test jobs passed.
- The ISIS 10 Windows CPython 3.13 job failed while linking `mgs.dll` because `SpiceQL::strSclkToEt` was unresolved (`LNK2019`, then `LNK1120`).
- Newer `ci-pybind` runs through M21 also fail before meaningful build validation on the self-hosted runner because checkout cleanup encounters permission errors and a stale `.deps/opencv-cuda/src/opencv` submodule mapping.
- Local ISIS 9 and ISIS 10 extension imports and focused tests remain green; these do not replace the Windows release gate.

## Technical Decisions
| Decision | Rationale |
|---|---|
| Treat Windows ISIS 10 as an external release blocker | The failure is in the Windows upstream dependency link and cannot be validated or fixed from the Linux checkout alone. |
| Track self-hosted CI hygiene separately | Permission/submodule cleanup failures are runner/repository-state issues, distinct from binding behavior. |

## Issues Encountered
| Issue | Resolution |
|---|---|
| ISIS 10 Windows `mgs.dll` unresolved `SpiceQL::strSclkToEt` | Preserve as M24 release gate blocker; no speculative source change. |
| Latest self-hosted CI checkout cleanup fails with EACCES and stale submodule mapping | Record as CI infrastructure blocker; retain local validation evidence. |

## Resources
- `.github/workflows/wheels.yml`
- `.github/workflows/ci-pybind.yml`
- `docs/releases/v1.4.0rc3-isis10.0.0.md`
- GitHub Actions run `30066283510`
- GitHub Actions run `37179630887`
