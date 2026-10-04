# Task Plan: ControlPointList sequence M18

## Goal
将 `ControlPointList` 的 ISIS `QVector/QStringList` 风格列表统一为 Python 可索引、可迭代的稳定序列。

## Next Step
提交 M18 代码与测试，创建并合并 PR 后同步本地 `main`。

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
- [x] Run ISIS 9/10 control-core tests and smoke
- **Status:** complete

### Phase 5: Delivery
- [ ] Commit, push, PR, merge, and sync local `main`
- **Status:** in_progress

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Return string IDs from a Python snapshot | `ControlPointList` is a file-backed ID sequence, so Python should receive immutable strings rather than Qt containers. |

## Errors Encountered
| Error | Resolution |
|-------|------------|
