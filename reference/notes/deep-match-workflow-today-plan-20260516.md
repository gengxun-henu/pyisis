# Deep-match manifest workflow plan — 2026-05-16

## 背景

`examples/image_match` 已经具备 deep-match `direct` / `export` / `import` 模式，`examples/learning_methods/run_deep_match_manifest.py` 已经可以在深度学习环境中执行导出的 manifest 并写回标准 `.npz` 结果。下一步目标是把这条跨 conda 工作流整理成可复现、可维护、可分阶段交付的路线。

## 今日交付范围

今天先完成第 1、2 项，并单独提交 PR：

1. **ignore 清理**
   - 忽略 `examples/learning_methods/sweep_results/` 下的参数 sweep 输出，避免把本地实验 CSV 当成代码变更提交。
   - 不再使用宽泛的 `reference/notes/*` ignore 规则；计划、说明和长期参考文档仍可按需纳入版本管理。
   - 旧的本地草稿 notes 在提交时选择性排除，不写入仓库级 ignore 规则。

2. **deep-match workflow 文档**
   - 在 `examples/learning_methods/README.md` 记录三阶段 handoff：
     1. `asp360_new` 中 export DOM tile arrays 和 `tasks.json`。
     2. `deep-learning` 中运行 manifest executor，生成 `results/*.npz`。
     3. 回到 `asp360_new` 中 import `.npz` 为 `.key`。
   - 说明目录职责、artifact 结构、坐标约定、验证建议和常见注意事项。

## 后续阶段（本 PR 之后）

3. **controlnet_construct 示例集成**
   - 在 controlnet batch 示例或说明中展示如何把 `deep_match_mode=export/import` 接到控制网构建流程。
   - 输出 manifest 路径汇总，方便在 `deep-learning` 环境中批量执行。

4. **import 边界测试增强**
   - 覆盖缺失 `.npz`、`failed` 任务、`matched_no_points`、多 task 合并和 scores 长度不一致等边界。
   - 保持验证集中在小型 synthetic fixtures，避免依赖真实大型影像。

5. **adaptive routing profile 化**
   - 增加高层策略，例如 `balanced` / `strict` / `relaxed` / `fast`。
   - 将 profile 展开的质量门控阈值写入 metadata，普通用户不直接面对过多底层参数。

## 验证计划

今日 PR 的最小验证：

- Markdown / `.gitignore` 静态诊断。
- `git status --ignored` 或等价检查，确认 sweep CSV 被忽略而计划文档可追踪。
- 复用本地已知验证事实：PR #244 的 build、smoke import、metadata audit 和 python unit-test gate 已通过。

## 不纳入今日 PR

- 不修改核心匹配算法。
- 不新增 controlnet wrapper。
- 不提交本地 sweep CSV 输出。
- 不提交长篇研究草稿，除非后续单独整理成正式 reference 文档。
