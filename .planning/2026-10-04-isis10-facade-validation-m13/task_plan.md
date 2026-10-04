# Task Plan: ISIS 10 facade validation M13

## Goal
在官方 `asp370` 环境完成现有 ISIS 10 专属 Python facade 的构建、导入和聚焦行为验证，并把兼容计划台账更新到真实状态。

## Next Step
提交 M13 计划与 ISIS 10 台账更新，创建并合并 PR 后同步本地 `main`。

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
- [x] Add/adjust only tests or binding glue required by the observed ISIS 10 behavior
- [x] Update ISIS 10 expansion plan and session evidence
- **Status:** complete

### Phase 4: Testing & Verification
- [x] Build `asp370` extension
- [x] Run ISIS 10 focused tests and smoke import
- [x] Run relevant ISIS 9 regression tests
- **Status:** complete

### Phase 5: Delivery
- [ ] Commit task-scoped files
- [ ] Push branch and open/merge PR
- [ ] Synchronize local `main`
- **Status:** in_progress

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Validate the existing ISIS 10 facade before adding another class | The bindings and tests already exist; the missing milestone evidence is official `asp370` execution. |
| Keep the work scoped to validation, focused test hardening, and auditable plan updates | Avoid speculative API expansion while Windows ISIS 10 remains blocked by the upstream prefix. |

## Errors Encountered
| Error | Resolution |
|-------|------------|
