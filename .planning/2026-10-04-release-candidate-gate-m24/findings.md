# Findings & Decisions

## Requirements
- Record the release candidate identity, supported Python ABIs, and required matrix evidence.
- Keep publication gated until every required platform/version lane passes.

## Research Findings
- Candidate lines are ISIS 9 / CPython 3.12 and ISIS 10 / CPython 3.13.
- Linux manylinux wheel lanes and ISIS 9 Windows historical lane are available from run `30066283510`.
- ISIS 10 Windows is not release-ready because the upstream `mgs.dll` link fails on `SpiceQL::strSclkToEt`.
- Local dual-version imports and focused suites are green, but do not substitute for Windows wheel validation.

## Technical Decisions
| Decision | Rationale |
|---|---|
| Use a gate record instead of a release tag | It makes the remaining missing evidence explicit without publishing an invalid binary set. |

## Issues Encountered
| Issue | Resolution |
|---|---|
| Required Windows ISIS 10 wheel evidence missing | Keep candidate status BLOCKED and proceed to independent application planning. |
