# 进度记录：Adaptive Routing ControlNet 执行阶段

## 会话：2026-06-01

### Phase 0：恢复上下文并转化为执行台账

- 开始时间：2026-06-01 09:13 +08:00
- 状态：complete

已完成：

- 按用户要求调用 `planning-with-files-zh`。
- 检查根目录规划文件；未发现现有 `task_plan.md`、`findings.md`、`progress.md`。
- 运行 `planning-with-files-zh` catchup；未返回需同步上下文。
- 读取 SPEC：`docs/superpowers/specs/2026-06-01-adaptive-routing-controlnet-design.md`。
- 读取 implementation plan：`docs/superpowers/plans/2026-06-01-adaptive-routing-controlnet.md`。
- 读取关键代码现实：
  - `examples/controlnet_construct/controlnet_stereopair.py`
  - `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
- 创建根目录执行阶段规划文件：
  - `task_plan.md`
  - `findings.md`
  - `progress.md`
- Phase 0 已完成；下一执行入口为 Phase 1 / Task 1：ORI route audit 测试。

## 测试与验证

| 时间 | 命令 | 结果 | 说明 |
|---|---|---|---|
| 2026-06-01 09:13 +08:00 | 未运行 | N/A | 当前仅恢复并建立执行台账，尚未改代码。 |

## 错误记录

| 时间 | 错误 | 尝试次数 | 处理 |
|---|---|---:|---|
| 2026-06-01 09:13 +08:00 | 无 | 0 | 暂无错误。 |

## 五问重启测试

| 问题 | 答案 |
|---|---|
| 我在哪里？ | Phase 0：恢复上下文并转化为执行台账。 |
| 我要去哪里？ | Phase 1 开始执行 implementation plan Task 1，先写 ORI route audit failing test。 |
| 目标是什么？ | 实现 opt-in ORI/DOM ControlNet adaptive routing matcher 选择与 route audit 汇总。 |
| 我学到了什么？ | 见 `findings.md`。 |
| 我做了什么？ | 创建根目录规划文件，并把已批准 SPEC/plan 转为执行阶段台账。 |

## 会话：2026-09-29

### Phase 1/2：ORI route audit 节点核验

- 发现旧计划落后于代码现实：ORI route audit 测试与实现已经存在。
- 未重复修改业务代码；核验了 `_route_audit_from_match_summary()`、
  `from-ori-match` JSON `routing_audit` 输出，以及现有 ORI focused tests。
- 运行结果：3/3 focused tests 通过。
- 计划状态已推进到 Phase 3：DOM 端到端 helper 测试。

## 测试与验证（2026-09-29）

| 命令 | 结果 | 说明 |
|---|---|---|
| `python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_controlnet_from_ori_match_writes_json_safe_route_audit -v` | PASS | 1/1 通过 |
| ORI 三项 focused tests | PASS | 3/3 通过 |

## 五问重启测试（2026-09-29）

| 问题 | 答案 |
|---|---|
| 我在哪里？ | ORI route audit 节点已完成，当前进入 Phase 3。 |
| 我要去哪里？ | 验证 DOM 端到端 helper 测试并处理其缺口。 |
| 目标是什么？ | 完成 adaptive routing ControlNet 的 ORI/DOM 工作流。 |
| 我学到了什么？ | 旧计划落后于代码；ORI 功能已存在且 focused tests 通过。 |
| 我做了什么？ | 同步 `task_plan.md`、`findings.md`、`progress.md` 并完成 ORI 核验。 |

## 会话：2026-09-29（续）

### Phase 3/4：DOM 端到端 helper 节点核验

- 发现 DOM helper、匹配入口、失败边界和 `from-dom-match` dispatch 已经存在。
- 未重复修改业务代码；完成 4 项 DOM focused tests 验证。
- 运行结果：4/4 通过。
- 计划状态已推进到 Phase 5：`from-dom-match` CLI。

## 测试与验证（2026-09-29，DOM 节点）

| 命令 | 结果 | 说明 |
|---|---|---|
| DOM helper 成功、参数转发、失败边界、CLI 报告四项 focused tests | PASS | 4/4 通过 |

## 五问重启测试（2026-09-29，DOM 节点）

| 问题 | 答案 |
|---|---|
| 我在哪里？ | DOM 端到端 helper 节点已完成，当前进入 Phase 5。 |
| 我要去哪里？ | 核验 `from-dom-match` CLI parser 与 dispatch 节点。 |
| 目标是什么？ | 完成 adaptive routing ControlNet 的 ORI/DOM 工作流。 |
| 我学到了什么？ | DOM helper 与其 focused tests 已经存在且通过。 |
| 我做了什么？ | 同步计划与进度，并完成 DOM helper 节点核验。 |

## 会话：2026-09-29（再次续）

### Phase 5：`from-dom-match` CLI 节点核验

- 确认 parser、adaptive routing 参数、deep preset、RANSAC/pre-RANSAC 参数和
  `main()` dispatch 已实现。
- 运行 parser 与 dispatch 两项 focused tests。
- 运行结果：2/2 通过。
- 计划状态已推进到 Phase 6：DOM match batch 聚合。

## 测试与验证（2026-09-29，CLI 节点）

| 命令 | 结果 | 说明 |
|---|---|---|
| `test_controlnet_stereopair_parser_accepts_from_dom_match_adaptive_flags` | PASS | parser 参数覆盖通过 |
| `test_controlnet_stereopair_from_dom_match_dispatches_helper_and_writes_report` | PASS | dispatch/report 覆盖通过 |

## 五问重启测试（2026-09-29，CLI 节点）

| 问题 | 答案 |
|---|---|
| 我在哪里？ | `from-dom-match` CLI 节点已完成，当前进入 Phase 6。 |
| 我要去哪里？ | 核验 DOM match batch 聚合。 |
| 目标是什么？ | 完成 adaptive routing ControlNet 的 ORI/DOM 工作流。 |
| 我学到了什么？ | CLI parser 和 dispatch 已存在且 focused tests 通过。 |
| 我做了什么？ | 同步计划与进度，并完成 CLI 节点核验。 |
