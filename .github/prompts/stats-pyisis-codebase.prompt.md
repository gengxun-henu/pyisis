---
description: "统计 pyisis 仓库的代码文件数、代码行数、tests 数据规模、按模块分类统计，以及绑定/单测覆盖视图。Use when: stats-pyisis, codebase-stats, pyisis-stats, 统计 src/tests 行数, 统计代码量, 统计 ISIS 类数, 统计绑定类覆盖, 按模块分类统计, 统计哪些类已绑定已测试, 导出 codebase_stats.md。"
name: "stats-pyisis-codebase"
argument-hint: "可选：default | json | show-class-lists | write-markdown"
agent: "agent"
---

统计当前 pyisis 工作区的代码规模、模块分类和 ISIS 类覆盖情况。

优先执行规则：

1. 优先使用仓库脚本 `scripts/stats_pyisis_codebase.py` 进行统计，避免每次临时拼接分析逻辑。
2. 默认输出适合直接阅读/汇报的 Markdown 摘要。
3. 若用户参数为 `json`，则使用 JSON 输出。
4. 若用户参数为 `show-class-lists`，则输出完整的类/类型名列表。
5. 若用户参数为 `write-markdown`，则将详细报告导出为仓库根目录下的 `codebase_stats.md`。

统计口径要求：

- `src/` 代码文件：仅统计 `.cpp` 和 `.h`
- `tests/` 代码文件：仅统计 `.py`、`.cpp` 和 `.h`
- 同时单独说明 `tests/` 的所有文件数，因为其中包含大量测试数据
- 按模块分类统计 `base / control / bundle / camera / projection / other`
- ISIS 类严格口径：从 `src/` 中提取 `py::class_<Isis::...>` 去重计数
- 宽口径：合并 `tests/` 中从 `isis_pybind` 导入或经模块属性访问的首字母大写类型名
- 单测覆盖视图仅统计 `tests/unitTest/**/*.py` 中引用到的已绑定类
- 若测试里出现的名字明显更像枚举、常量或其他非类类型，需要在结果里单独说明，不要混淆为“确定的类数”

执行建议：

- 在仓库根目录运行脚本
- 优先使用 `asp360_new` 环境中的 Python
- 若脚本不存在，再退回到一次性分析逻辑

结果输出要求：

- 简明给出 `src/`、`tests/` 的代码文件数、总代码行数、非空行数
- 给出按模块分类的文件数、行数、绑定类数
- 明确区分“测试代码文件数”和“tests 总文件数”
- 明确给出严格口径与宽口径的 ISIS 类/类型数
- 给出“已绑定 / 已写单测 / 只有绑定未测”的覆盖视图
- 当用户要求导出报告时，优先生成 `codebase_stats.md`
- 如果用户没有要求完整列表，默认不要贴出超长类名全集
- 如果脚本执行失败，简要说明失败原因并给出下一步建议
