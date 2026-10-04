# Findings & Decisions

## Requirements
- Support `point_list[index]` and `for point_id in point_list`.
- Normalize negative indices and raise `IndexError` for out-of-range values.
- Preserve file order and return Python `str` values.

## Research Findings
- Existing binding exposes `control_point_id(index)` and `__len__` but no sequence protocol.
- The unit fixture already creates a three-ID list (`P1`, `P2`, `P3`).
- RED test confirmed the object was not subscriptable before the binding change.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Implement iteration through a copied Python list | Avoids Qt iterator exposure and matches PVL/Bundle container policy. |

## Issues Encountered
| Issue | Resolution |
|-------|------------|

## Resources
-
