# Findings & Decisions

## Requirements
- Expose explicit `__iter__` for `ControlNet` and `ControlPoint`.
- Support positive and negative integer indices with `IndexError` bounds.
- Keep parent-owned pointer lifetimes through `reference_internal`.

## Research Findings
- Both classes already expose `__len__` and integer `__getitem__` but no explicit `__iter__`.
- Existing `pointsToPyList` and `measuresToPyList` helpers provide safe parent-linked Python wrappers.
- RED tests confirmed `hasattr(instance, "__iter__")` was false before the change.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Use snapshot Python lists for iteration | Avoids exposing Qt/ISIS iterators and keeps parent ownership explicit. |

## Issues Encountered
| Issue | Resolution |
|-------|------------|

## Resources
-
