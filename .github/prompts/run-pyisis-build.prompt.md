---
description: "执行 pyisis 构建与测试流水线。Use when: run-pyisis, run-pyisis-build, pyisis-build, 运行 pyisis build, 运行 build、ctest、smoke_import、verbose unittest，执行编辑器里当前选中的构建命令，或按 full/build-only/test-only/verbose-test/clean-full 模式处理。"
name: "run-pyisis-build"
argument-hint: "可选：full | build-only | test-only | verbose-test | clean-full | selected"
agent: "agent"
---

执行当前工作区的 pyisis 构建/测试流程。

优先级规则：

1. 如果用户在编辑器里选中了 shell 命令，优先把**当前选中的命令块**当作待执行流程。
2. 如果没有选中命令，则优先读取 [build_commands](.github/prompts/build_commands.md) 中的纯净 recipe。
3. 只有在 `build_commands.md` 无法覆盖需求时，才参考 [how_to_build](.github/prompts/how_to_build.md) 作为说明性补充。

模式选择：

- `full`：执行 `build_commands.md` 中的 `full` recipe。
- `build-only`：只执行 `build_commands.md` 中的 `build-only` recipe，不跑测试。
- `test-only`：只执行 `build_commands.md` 中的 `test-only` recipe，即 `ctest + smoke_import.py`。
- `verbose-test`：执行 `build_commands.md` 中的 `verbose-test` recipe，即 `unittest -v + smoke_import.py`，适合定位具体 Python 单测失败。
- `clean-full`：仅在用户明确要求清理缓存或怀疑缓存失效时，执行 `build_commands.md` 中的 `clean-full` recipe。
- `selected`：优先执行编辑器里当前选中的命令块。
- 未显式给模式时，默认使用 `full`，且**保留 `build/` 目录缓存**。

执行要求：

- 在仓库根目录执行。
- 优先使用 `asp360_new` 环境及其 Python。
- 按步骤顺序执行，避免把 configure、build、ctest、smoke 混成一条不可诊断的大命令。
- 默认不要删除 `build/`；只有用户明确要求 `clean-full`，或选中的命令块本身包含清理步骤时，才执行删除。
- 如果用户明确选中了命令文本，除非命令明显不完整或互相矛盾，否则优先尊重用户选中的内容。

结果输出要求：

- 成功时，简要汇报每一步是否通过。
- 失败时，停止在失败步骤，给出错误摘要，并指出建议的下一步。
- 如果本次实际执行的是 `build_commands.md` 中的 recipe，请明确说明具体使用了哪个模式。

补充约束：

- 仅执行与当前 pyisis 仓库构建/测试直接相关的命令。
- 若发现环境变量缺失，先补齐最小必要环境，再继续。
- 若用户只想“跑一下我选中的这段”，不要擅自扩展成清理重建或额外测试。
