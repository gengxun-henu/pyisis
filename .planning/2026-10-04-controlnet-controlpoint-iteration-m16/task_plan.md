# Task Plan: ControlNet ControlPoint iteration M16

## Goal
为 `ControlNet` 和 `ControlPoint` 提供稳定的 Python `getitem/iter` 协议，并在 ISIS 9/10 中验证。

## Next Step
提交 M16 代码与测试，创建并合并 PR 后同步本地 `main`。

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
- [ ] Commit, push, PR, merge, and sync local `main`
- **Status:** in_progress

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Return reference-internal pointers from snapshot iterators | Existing helpers already preserve parent lifetime for ControlNet/ControlPoint-owned objects. |
| Normalize negative indices in the binding boundary | Provides normal Python sequence behavior independent of Qt container semantics. |

## Errors Encountered
| Error | Resolution |
|-------|------------|
