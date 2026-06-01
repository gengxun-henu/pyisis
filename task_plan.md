# 任务计划：Adaptive Routing ControlNet 执行阶段

## 目标

基于已批准 SPEC `docs/superpowers/specs/2026-06-01-adaptive-routing-controlnet-design.md` 和执行基线 `docs/superpowers/plans/2026-06-01-adaptive-routing-controlnet.md`，实现 opt-in 的 ORI/DOM ControlNet adaptive routing matcher 选择、路由审计元数据、DOM 端到端入口、批处理聚合与文档验证。

## 当前阶段

Phase 1：Task 1 - ORI route audit 测试，状态：pending。

## 执行基线

- 设计基线：`docs/superpowers/specs/2026-06-01-adaptive-routing-controlnet-design.md`
- 实施基线：`docs/superpowers/plans/2026-06-01-adaptive-routing-controlnet.md`
- 关键约束：不重新做需求探索、方案比较、SPEC 编写或 implementation planning；仅在代码现实与基线冲突时记录差异并最少量澄清。

## 阶段

### Phase 0：恢复上下文并转化为执行台账

- [x] 调用 `planning-with-files-zh`
- [x] 检查根目录 `task_plan.md`、`findings.md`、`progress.md`
- [x] 读取已批准 SPEC
- [x] 读取 implementation plan
- [x] 读取关键代码现实
- [x] 建立执行阶段进度台账
- 状态：complete

### Phase 1：Task 1 - ORI route audit 测试

- [ ] 按 implementation plan 更新 `tests/unitTest/controlnet_construct_pipeline_unit_test.py` 元数据
- [ ] 添加 `test_controlnet_from_ori_match_writes_json_safe_route_audit`
- [ ] 运行单测并确认预期失败
- [ ] 记录失败输出与原因
- 状态：pending

### Phase 2：Task 2 - ORI route audit 实现

- [ ] 在 `examples/controlnet_construct/controlnet_stereopair.py` 添加 route audit helper
- [ ] 改造 `from-ori-match` 使用 `match_summary` 而非原始 tuple
- [ ] 运行 ORI focused tests
- [ ] 记录验证结果
- 状态：pending

### Phase 3：Task 3 - DOM 端到端 helper 测试

- [ ] 更新测试 import
- [ ] 添加 DOM match 成功路径测试
- [ ] 添加 DOM match 失败边界测试
- [ ] 运行单测并确认预期失败
- 状态：pending

### Phase 4：Task 4 - DOM 端到端 helper 实现

- [ ] 导入 `match_dom_pair_to_key_files`
- [ ] 添加 `build_controlnet_for_dom_match_stereo_pair`
- [ ] 运行 DOM helper focused tests
- 状态：pending

### Phase 5：Task 5 - `from-dom-match` CLI

- [ ] 添加 parser/dispatch failing tests
- [ ] 实现 parser 与 main dispatch
- [ ] 运行 CLI focused tests
- 状态：pending

### Phase 6：Task 6 - DOM match batch 聚合

- [ ] 添加 batch 聚合 failing test
- [ ] 实现 `build_controlnets_for_dom_match_overlap_list`
- [ ] 运行 batch focused test
- 状态：pending

### Phase 7：Task 7 - 文档与最终验证

- [ ] 添加 usage 文档覆盖测试
- [ ] 更新 `examples/controlnet_construct/usage.md`
- [ ] 运行 focused regression set
- [ ] 运行 `python tests/smoke_import.py`
- [ ] 确认不提交 `print.prt`
- 状态：pending

## 决策记录

| 决策 | 原因 |
|---|---|
| SPEC 作为设计基线 | 用户确认 brainstorming/SPEC 已完成并批准。 |
| implementation plan 作为执行基线 | 用户确认 writing-plans 已完成且 plan 已存在。 |
| 不重新规划 | 用户明确要求不要重新做需求探索、方案比较、SPEC 编写或 implementation planning。 |
| 使用根目录规划文件 | `planning-with-files-zh` 要求项目目录持久化 `task_plan.md`、`findings.md`、`progress.md`。 |

## 风险与冲突

| 风险/冲突 | 状态 | 处理 |
|---|---|---|
| implementation plan 中测试 alias 名称可能与现有 `build_controlnet_stereopair_argument_parser` 用途混淆 | open | 执行 Task 5 前在 `findings.md` 记录并按代码现实调整最小实现。 |
| 工作树存在用户/其他任务改动的可能性 | open | 每次提交前使用 clean-commit 思路只纳入当前任务相关文件，避免误提交。 |

## 错误记录

| 错误 | 尝试次数 | 解决 |
|---|---:|---|
| 无 | 0 | 暂无错误。 |
