# Findings & Decisions

## Requirements
- Complete the four platform/version build matrix without the unhealthy self-hosted runner.
- Verify Linux clean-install jobs and retain artifact identities.

## Research Findings
- Workflow run `37215760300` on commit `185fb6ce8831f861591d48bd9e0bac7b255e5a06` completed successfully.
- Passed jobs: ISIS 9 Windows cp312, ISIS 10 Windows cp313, ISIS 9 Linux cp312, ISIS 10 Linux cp313, and six Linux clean-install jobs across Ubuntu 22.04, 24.04, and 26.04.
- Windows ISIS 10 SpiceQL 1.4.1 build and the `mgs.dll` gate passed in this run.
- Retained artifacts include both Windows wheelhouses, both Linux wheelhouses, and both Linux ABI reports.
- GitHub Release publication was skipped by design (`publish_github_release=false`).

## Artifact Summary
| Artifact | Size (bytes) |
|---|---:|
| `usgs-pyisis-windows-cp312-wheels` | 94,129,887 |
| `usgs-pyisis-isis10-windows-cp313-wheels` | 109,019,179 |
| `usgs-pyisis-linux-cp312-manylinux-wheelhouse` | 229,484,396 |
| `usgs-pyisis-isis10-linux-cp313-manylinux-wheelhouse` | 315,305,131 |
| `usgs-pyisis-linux-cp312-abi-report` | 1,737 |
| `usgs-pyisis-isis10-linux-cp313-abi-report` | 836 |

## Issues Encountered
| Issue | Resolution |
|---|---|
| Self-hosted runner unavailable | Used the workflow's GitHub-hosted fallback inputs. |
