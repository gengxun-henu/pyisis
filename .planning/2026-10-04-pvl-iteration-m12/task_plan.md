# Task Plan: PVL Python Collection Iteration (M12)

## Goal

Make the existing ISIS PVL bindings naturally iterable from Python while preserving stable value and object ownership semantics across ISIS 9 and ISIS 10.

## Scope

- Add `__iter__` to `PvlKeyword`, `PvlContainer`, and `PvlObject`.
- Cover empty and populated collections with focused tests.
- Document the Python usage and validate the shared binding in ISIS 9.
- Complete through a PR and synchronize local `main`.

## Source Plans

- `docs/superpowers/plans/2026-10-04-pvl-iteration-m12.md`
- `.planning/isis10-expansion/task_plan.md`
- `AGENTS.md`

## Dependencies

- M11 merged at `48322a59`.
- Existing PVL bindings and local ISIS 9 build are available.

## Completion Gate

Python iteration over PVL values, keywords, groups, and nested objects passes focused and full validation; documentation and planning evidence are committed; the PR is merged; and local `main` is synchronized without touching `print.prt`.

## Next Step

None — M12 is complete and merged as `2b9e22149b564bd281ffab24b80fc8e6b987b19a`.

## Current Phase

Phase 4: PR integration and synchronization

## Phases

### Phase 1: Requirements and regression tests

- [x] Add focused iteration tests.
- [x] Run the focused PVL module and observe the expected RED failures.
- **Status:** complete 2026-10-04

### Phase 2: Shared binding implementation

- [x] Add stable list-backed `__iter__` methods in `src/base/bind_base_pvl.cpp`.
- [x] Rebuild `_isis_core` and make the focused tests pass.
- **Status:** complete 2026-10-04

### Phase 3: Documentation and verification

- [x] Document iteration examples.
- [x] Run focused tests, smoke import, full unit suite, and `git diff --check`.
- **Status:** complete 2026-10-04

### Phase 4: PR integration and synchronization

- [x] Commit and push the task-scoped changes.
- [x] Open and merge the PR.
- [x] Synchronize local `main` and record evidence.
- **Status:** complete 2026-10-04

## Decisions

- Materialize Python lists from indexed APIs instead of exposing Qt iterator types.
- Keep existing indexed access and version-gated JSON/GDAL APIs unchanged.
- Use shared binding code for ISIS 9/10 because the count/index methods are compatible.

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Canonical M06 registry verification still lacks its historical ZIP | 1 | Keep this legacy evidence issue separate from M12; do not mutate completed registry data. |

## Reboot Check

- **Where am I?** Phase 1, before test edits.
- **Where am I going?** Shared PVL iteration API, merged PR, synchronized `main`.
- **Goal?** Python-friendly, version-compatible PVL collection traversal.
- **What have I learned?** Existing count/index methods are sufficient; no new ISIS dependency is needed.
- **Next step?** Add and run the failing focused tests.

## Completion Evidence

- PR #385 merged as `2b9e22149b564bd281ffab24b80fc8e6b987b19a`.
- Focused PVL module: 85 passed, 0 failed, 0 skipped.
- Smoke import: passed.
- Full unit suite: 2730 run, 0 failed, 52 skipped, 1 expected failure.
- Local `main`: synchronized with `origin/main`; `print.prt` untouched.
