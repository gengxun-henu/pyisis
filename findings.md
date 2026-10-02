# 发现记录：Adaptive Routing ControlNet 执行阶段

## 基线输入

- SPEC：`docs/superpowers/specs/2026-06-01-adaptive-routing-controlnet-design.md`
- Implementation plan：`docs/superpowers/plans/2026-06-01-adaptive-routing-controlnet.md`
- 用户约束：不要重新进行需求探索、方案比较、SPEC 编写或 implementation planning；只有基线与代码现实存在关键冲突或缺失必要执行信息时才最少量澄清。

## 已确认设计事实

- Adaptive routing 默认关闭，必须通过 CLI/config 显式启用。
- ORI 路径继续使用 `match_ori_pair_to_key_files()`，ControlNet 侧只做薄编排和 route audit 元数据持久化。
- DOM 端到端路径需要调用 `match_dom_pair_to_key_files()` 生成 DOM `.key`，再复用现有 DOM-to-original 转换和 ControlNet 写出。
- `from-dom` / `from-dom-batch` 作为消费预生成 DOM key 的老流程保持兼容。
- Pair summary 与 batch summary 需要聚合 requested/effective matcher、route profile、initial/final matcher、fallback/cascade、quality gate、deep config、match count 和输出路径。

## 代码现实

- `examples/controlnet_construct/controlnet_stereopair.py` 当前只从 `image_match.image_match` 导入 `match_ori_pair_to_key_files`，尚未导入 `match_dom_pair_to_key_files`。
- `controlnet_stereopair.py` 已有 `_default_intermediate_key_path()`、`write_controlnet_result_report()`、`_stdout_result_payload()`、`ControlNetConfig`、`replace` import，可支撑计划中的 DOM match helper 和 batch helper。
- `_normalize_cli_argv()` 当前支持 `from-ori`、`from-ori-match`、`from-dom`、`from-dom-batch`，尚未支持 `from-dom-match`。
- `main()` 的 `from-ori-match` 分支当前把 `match_ori_pair_to_key_files()` 返回值整体存入 `match_result`，并在 JSON payload 中写入 `"match": match_result`；这与计划中 JSON-safe `match_summary`/`routing_audit` 改造一致。
- `tests/unitTest/controlnet_construct_pipeline_unit_test.py` 现有 `Last Modified: 2026-05-28`，需要按计划更新为 `2026-06-01` 并新增 `Updated:` 行。
- 现有测试 import 中 `build_controlnet_stereopair_argument_parser` 实际来自 `controlnet_construct.image_match.build_argument_parser`，用于 image_match CLI；新增 `from-dom-match` parser 测试应从 `controlnet_construct.controlnet_stereopair` 导入 parser alias，避免覆盖现有 alias。

## 差异与风险

### 2026-09-29 计划与代码现实同步

- 原有 `task_plan.md` 停留在 Phase 1，但 `controlnet_stereopair.py` 已经包含
  `_route_audit_from_match_summary()` 和 `from-ori-match` 的
  `routing_audit` 输出。
- `controlnet_construct_pipeline_unit_test.py` 已经包含
  `test_controlnet_from_ori_match_writes_json_safe_route_audit`，因此没有重复添加
  测试或修改业务代码。
- ORI 节点的后续执行入口应从 Phase 3 DOM helper 测试开始。

### 2026-09-29 DOM helper 节点核验

- 代码已经包含 `match_dom_pair_to_key_files`、
  `build_controlnet_for_dom_match_stereo_pair` 和 `from-dom-match` dispatch。
- 测试已经覆盖成功路径、参数转发、匹配失败后不继续转换，以及 CLI 报告写出。
- 因此本节点采用“核验并同步计划”的方式完成，没有重复添加实现。

### 2026-09-29 `from-dom-match` CLI 节点核验

- CLI 已注册 `from-dom-match` 子命令，包含 adaptive routing、deep preset、
  merge、RANSAC 和 pre-RANSAC 参数。
- `main()` 已将这些参数转发到
  `build_controlnet_for_dom_match_stereo_pair()`，并写出 JSON report。
- parser 和 dispatch focused tests 均已存在并通过，因此没有重复修改代码。

### 2026-09-29 DOM batch 聚合复核

- `build_controlnets_for_dom_match_overlap_list` 已存在于
  `examples/controlnet_construct/controlnet_stereopair.py`。
- 现有 batch 测试
  `test_build_controlnets_for_dom_match_overlap_list_auto_assigns_pair_ids_and_writes_summary`
  已通过，覆盖 pair ID、参数转发、单 pair report 和 batch report。
- implementation plan 中指定的
  `test_build_controlnets_for_dom_match_overlap_list_aggregates_routing_audit`
  当前不存在；此前按该名称运行会得到 unittest 的测试加载错误。
- 下一步应补充一条真实存在的多 pair routing audit 聚合测试，而不是重复实现 helper。

### 2026-09-29 DOM batch 聚合节点完成

- `build_controlnets_for_dom_match_overlap_list()` 现已在每个 `pairs` 摘要中写出
  `routing_audit` 和 `match_count`，保留原有控制点数与报告路径字段。
- 新增双 pair focused 测试，使用不同最终 matcher（FLANN、LoFTR）验证 pair 级路由审计不会串 pair。
- 现有 batch summary 测试与新增聚合测试均通过。

### 2026-10-03 Phase 7 文档与最终验证

- `usage.md` 已覆盖 `from-dom-match` 的 routing audit 字段、batch pair 级结果隔离、
  匹配失败后停止回投/写网，以及 adaptive routing 默认关闭行为。
- 新增文档回归测试，避免实现与用户使用说明再次脱节。
- 完整 pipeline 单测 131 项通过，1 项跳过仅因真实 LRO DOM fixture 未配置；import smoke 通过。

| 项 | 影响 | 处理 |
|---|---|---|
| Implementation plan 的 Task 5 曾使用 `build_controlnet_stereopair_parser()` 新 alias；当前测试文件已有同名语义相近的 image_match parser alias。 | 容易误测错 parser。 | 执行时导入 `build_argument_parser as build_controlnet_stereopair_parser` from `controlnet_construct.controlnet_stereopair`，保留现有 `build_controlnet_stereopair_argument_parser` 不变。 |
| 计划建议多次提交，但当前用户未明确要求执行时每阶段 commit。 | 可能产生过多本地 commits。 | 若进入实现，遵循计划小步提交；提交前使用 clean-commit 思路检查 scope。 |
| 根目录新增规划文件会出现在工作树。 | 可能不属于最终功能提交。 | 作为用户明确要求的规划文件保留；功能提交时按 scope 决定是否排除。 |

## 验证命令基线

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Smoke：

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tests/smoke_import.py
```
