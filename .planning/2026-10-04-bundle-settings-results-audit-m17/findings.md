# Findings & Decisions

## Requirements
- `BundleSettings.observation_solve_settings()` must return a Python list.
- `maximum_likelihood_estimator_models()` must return stable `(enum, float)` tuples.
- `BundleSettings.bundle_target_body()` must return an isolated Python value or `None`.
- Existing `BundleResults` and `BundleSolutionInfo` safe-copy behavior must remain intact.

## Research Findings
- Current bindings already convert `QList<BundleObservationSolveSettings>` and `QList<QPair<...>>` at the C++ boundary.
- `bundle_target_body()` returns a value copy and handles a null QSharedPointer as `None`.
- `BundleSolutionInfo.bundleResults()` uses a dedicated clone helper because the upstream copy path can segfault under ISIS 9.
- RED/compatibility audit completed without a binding defect; focused assertions pass under both versions.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Treat this milestone as compatibility evidence, not new public API | The existing facade already implements the required stable Python contract. |

## Issues Encountered
| Issue | Resolution |
|-------|------------|

## Resources
-
