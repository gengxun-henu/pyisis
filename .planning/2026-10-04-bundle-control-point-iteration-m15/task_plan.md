# Task Plan: Bundle control-point iteration M15

## Goal
为 `BundleControlPoint` 暴露稳定的 Python `getitem/iter` 访问，使其中的 `BundleMeasure` 可按 ISIS 顺序读取。

## Next Step
提交 M15 代码与测试，创建并合并 PR 后同步本地 `main`。

## Current Phase
Phase 1

## Phases

### Phase 1: Requirements & Discovery
- [x] Understand user intent
- [x] Identify constraints
- [x] Document in findings.md
- **Status:** complete

### Phase 2: Planning & Structure
- [x] Define approach
- [x] Create project structure
- **Status:** complete

### Phase 3: Implementation
- [x] Add bounds-checked `__getitem__` and snapshot `__iter__`
- [x] Add focused tests and metadata
- **Status:** complete

### Phase 4: Testing & Verification
- [x] Run ISIS 9 focused test and smoke
- [x] Build/run ISIS 10 focused test and smoke
- **Status:** complete

### Phase 5: Delivery
- [x] Commit, push, PR, merge, and sync local `main`
- **Status:** complete

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Return existing `BundleMeasureQsp` values from a Python snapshot | Preserves ISIS shared ownership and avoids exposing QVector iterators. |
| Support negative indices in `__getitem__` | Matches normal Python sequence behavior while retaining explicit bounds errors. |

## Errors Encountered
| Error | Resolution |
|-------|------------|
