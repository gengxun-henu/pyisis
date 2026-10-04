# Findings & Decisions

## Requirements
- Ensure the release job depends on all six build/clean-install gates.
- Ensure the release contract does not introduce `continue-on-error` for platform jobs.
- Ensure Windows ISIS 10 keeps the SpiceQL preflight step.

## Research Findings
- The workflow already has the correct six-job `needs` list and manual main-branch publish condition.
- The existing unit test covered presence, but not the absence of softened failures.
- Added tests now protect both the dependency list and the Windows SpiceQL step.

## Technical Decisions
| Decision | Rationale |
|---|---|
| Test workflow text contract instead of executing Actions locally | GitHub Actions and Windows/MSVC are unavailable in this environment; static checks catch accidental gate weakening before dispatch. |
