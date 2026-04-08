# Pybind 滚动绑定执行计划（2026-04-08 历史补录说明）

这份文档保留为 **2026-04-08 当天的历史补录说明**，用于说明当时为何额外整理了一轮“滚动推进”思路，以及它与当前仓库主工作流的关系。

它**不是**当前仓库判断待处理类、筛选执行队列或确定现行绑定流程的主参考。

## 这份文档当时的用途

在 2026-04-08 的一轮整理中，仓库先补齐了若干此前未纳入主台账的类，并同步更新了：

- `todo_pybind11.csv`
- `class_bind_methods_details/methods_inventory_summary.csv`
- 对应的 `class_bind_methods_details/*_methods.csv`

在那个上下文里，这份文档曾尝试把“分批排队、单类闭环、失败止损”的推进思路写成一份说明草案。

因此，它更接近：

- 当时的工作思路记录
- 一次 inventory / rollout 补录后的附带说明

而不是稳定、长期生效的主流程来源。

## 当前应以哪些文件为主

当前仓库在“未完成类持续绑定”场景下，应优先依赖以下文件：

1. `todo_pybind11.csv`
2. `class_bind_methods_details/methods_inventory_summary.csv`
3. 对应的 `class_bind_methods_details/*_methods.csv`
4. `pybind_progress_log.md`

其中：

- `todo_pybind11.csv` 与 `methods_inventory_summary.csv` 用于判断哪些类仍待处理
- `*_methods.csv` 用于确认当前类的方法级剩余工作面
- `pybind_progress_log.md` 用于查看历史进展、已知 blocker 与最近处理情况

## `base_inventory_rollout_order_2026-04-08.md` 的当前角色

`reference/notes/base_inventory_rollout_order_2026-04-08.md` 仍然有用，但它当前只应作为：

- 阶段划分参考
- 同阶段内的顺序约束

它不应被当作唯一的待处理类来源。

换句话说：

- **CSV 台账负责回答“哪些类还没做完”**
- **rollout note 负责回答“这些类大体先做谁、后做谁”**

## 与当前 skill 的关系

当前仓库中与滚动推进更直接相关的 workflow 已转移到：

- `.github/skills/pybind-rollout-execution/SKILL.md`

并且该 skill 现已按仓库后续整理结果改为：

- 以 CSV 台账作为 primary source of truth
- 以 rollout note 作为 phase / ordering constraint

因此，这份文档现在不再承担 active workflow reference 的角色。

## 保留这份文档的原因

保留它，是为了留下下面这些历史信息：

- 2026-04-08 当天曾经有过一轮“滚动推进制度化”的讨论与草拟
- 该草拟与 inventory 补录是同一轮背景产物
- 后续仓库已将其中真正需要长期保留的部分，收敛进更合适的位置（尤其是 skill 与 CSV-ledger-first 的流程）

## 当前处理原则

如果后续有人再次看到这份文档，建议按以下原则理解：

1. 把它当作历史说明，不当作主流程手册
2. 不要只根据这份文档筛选待处理类
3. 真正决定当前待处理队列时，优先看 CSV 台账
4. 若其中内容与当前 skill 或台账优先级冲突，以当前 skill 和 CSV 台账为准

## 结论

这份文件现在的定位是：

- **历史补录说明**
- **上下文保留文件**

而不是：

- 当前绑定推进的主参考
- 当前 skill 的直接输入来源
- 当前待处理类的 authoritative source
