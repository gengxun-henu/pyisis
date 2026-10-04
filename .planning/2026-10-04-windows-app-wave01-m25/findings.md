# Findings & Decisions

## Requirements
- Audit Wave 0 baseline and Wave 1 anchor applications for Windows packaging.
- Preserve the rule that native APPs are distributed separately from PyISIS wheels.

## Research Findings
- `ports/windows/isis/windows-app-manifest.json` contains 150 tracked CLI APP entries.
- `reduce` and `jigsaw` are present in the manifest with explicit ISIS 9 supported and ISIS 10 experimental statuses.
- The manifest records `reduce` as compiled/installed with minimal smoke and `jigsaw` as compiled/installed with ISIS 10 startup smoke passed.
- The release test script treats `reduce`, `jigsaw`, and `qnet` as explicit GUI/startup fixtures; `qnet` is maintained outside the 150-entry CLI manifest.

## Technical Decisions
| Decision | Rationale |
|---|---|
| Treat this as an audit milestone | The Windows ISIS 10 build gate from M23/M24 remains external and unresolved; this milestone records the implementation baseline without claiming a new artifact. |

## Issues Encountered
| Issue | Resolution |
|---|---|
| Windows build cannot be rerun from Linux | Preserve manifest evidence and defer executable validation to the Windows gate. |
