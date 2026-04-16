# DOM Matching ControlNet 需求（工作稿）

> 该文件为当前任务补齐的占位工作稿，用于承接“先生成代码撰写计划与架构”的后续实现。

## 目标

基于左右影像，通过 DOM 匹配生成可落盘的 `ControlNet`，并提供最小可复现统计结果。

## 最小范围（MVP）

1. 输入：左右影像路径、输出网络路径、匹配参数。
2. 处理：候选点匹配 + 质量筛选 + ControlPoint/ControlMeasure 写入。
3. 输出：`.net` 文件 + 成功/失败统计。

## 非目标

- 暂不覆盖复杂并行调度与大规模块匹配优化。
- 暂不引入新的底层绑定改动（优先复用现有 pyisis API）。

## 对应产物

- 代码计划与架构: `examples/controlnet_construct/plan_architecture_dom_matching_controlnet.md`
