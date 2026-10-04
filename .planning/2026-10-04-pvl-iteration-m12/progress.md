# Progress: PVL Python Collection Iteration (M12)

## Session 2026-10-04

- Started M12 after M11 merged and local `main` synchronized.
- Read the ISIS 10 expansion queue and active conda ISIS 9 headers.
- Confirmed the PVL classes already have the count/index APIs needed for a shared Python iteration surface.
- Wrote the implementation plan at `docs/superpowers/plans/2026-10-04-pvl-iteration-m12.md`.

## Next Step

Added the four iteration assertions and observed the expected RED failures.
- Implemented list-backed `__iter__` for `PvlKeyword`, `PvlContainer`, and `PvlObject`, plus `PvlObject.objects_iter()`.
- Rebuilt `_isis_core` successfully.
- Focused iteration tests: 3 passed.
- Added README usage example.

Full PVL module: 85 passed.
- Smoke import: passed.
- Full unit suite: 2730 run, 0 failed, 52 skipped, 1 expected failure.

Next step: commit and push the PVL iteration changes, open the PR, and merge it when checks permit.
