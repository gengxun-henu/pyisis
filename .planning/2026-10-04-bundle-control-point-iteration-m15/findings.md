# Findings & Decisions

## Requirements
- Expose `BundleControlPoint[index]` and `for measure in bundle_point`.
- Preserve fixture order: `SN-001`, then `SN-002`.
- Raise `IndexError` for positive and negative out-of-range indices.

## Research Findings
- `BundleControlPoint` inherits `QVector<BundleMeasureQsp>` and already exposes `numberOfMeasures()` as Python `__len__`.
- Existing `bundle_advanced_unit_test.py` constructs a point with two measures and verifies the wrapper lifetime.
- No Python index or iteration binding currently exists.
- RED test confirmed `BundleControlPoint` was not subscriptable before the change.
- Returning copied `BundleMeasure` objects matches the repository's existing snapshot-container policy and keeps the QSharedPointer holder private.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
-| | |
| Use `self[index]` after normalizing negative indices | It keeps the binding aligned with the existing ISIS QVector storage and explicit Python error semantics. |

## Issues Encountered
| Issue | Resolution |
|-------|------------|

## Resources
-
