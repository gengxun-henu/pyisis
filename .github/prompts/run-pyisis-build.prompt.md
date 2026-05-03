---
description: "执行 pyisis 构建与测试流水线。默认直接调用 scripts/build_test_smoke.sh，避免每次重复分析命令说明。Use when: run-pyisis, run-pyisis-build, pyisis-build, 运行 pyisis build, 运行 build、ctest、smoke_import、verbose unittest，执行编辑器里当前选中的构建命令，或按 full/build-only/test-only/verbose-test/clean-full 模式处理。"
name: "run-pyisis-build"
argument-hint: "可选：full | build-only | test-only | verbose-test | clean-full | selected"
agent: "agent"
---

执行当前工作区的 pyisis 构建/测试流程。

核心原则：

- **默认直接调用** `scripts/build_test_smoke.sh`。
- 把 `scripts/build_test_smoke.sh` 视为唯一可执行事实来源。
- 不要为了常规 `full/build-only/test-only/verbose-test/clean-full` 模式反复读取并分析 `build_commands.md` 或其他说明文档。
- `build_commands.md` 与 `doc_development_process/how_to_build.md` 仅作为说明性后备资料，不是默认执行来源。

优先级规则：

1. 如果用户在编辑器里选中了 shell 命令，优先把**当前选中的命令块**当作待执行流程。
2. 如果没有选中命令，则直接调用 `scripts/build_test_smoke.sh` 对应模式。
3. 只有当脚本不覆盖用户需求，或用户明确要求查看展开后的原始命令时，才参考 [build_commands](./build_commands.md)。
4. 只有在 `build_commands.md` 也无法覆盖需求时，才参考仓库内其他构建说明文档作为说明性补充。

模式选择：

- `full`：执行 `scripts/build_test_smoke.sh full`。
- `build-only`：执行 `scripts/build_test_smoke.sh build-only`。
- `test-only`：执行 `scripts/build_test_smoke.sh test-only`。
- `verbose-test`：执行 `scripts/build_test_smoke.sh verbose-test`，适合定位具体 Python 单测失败。
- `clean-full`：仅在用户明确要求清理缓存或怀疑缓存失效时，执行 `scripts/build_test_smoke.sh clean-full`。
- `selected`：优先执行编辑器里当前选中的命令块。
- 未显式给模式时，默认使用 `full`，且**保留 `build/` 目录缓存**。

执行要求：

- 在仓库根目录执行。
- 优先使用 `asp360_new` 环境及其 Python。
- 对脚本模式，直接调用脚本，不要把脚本内容重新展开成新的长命令再执行。
- 默认不要删除 `build/`；只有用户明确要求 `clean-full`，或选中的命令块本身包含清理步骤时，才执行删除。
- 如果用户明确选中了命令文本，除非命令明显不完整或互相矛盾，否则优先尊重用户选中的内容。

结果输出要求：

- 成功时，简要汇报每一步是否通过。
- 失败时，停止在失败步骤，给出错误摘要，并指出建议的下一步。
- 如果本次实际执行的是脚本，请明确说明具体使用了哪个脚本模式。
- 如果本次不是走脚本，而是走了用户选中命令或展开后的 raw recipe，也请明确说明原因。

补充约束：

- 仅执行与当前 pyisis 仓库构建/测试直接相关的命令。
- 若用户请求“同步未同步类/方法”或“全量同步台账”，不要在本 prompt 中混入 ledger sync；应改用 `sync-pybind-ledgers`，并优先支持 `all` 作为全局范围参数。
- 若发现环境变量缺失，先补齐最小必要环境，再继续。
- 若用户只想“跑一下我选中的这段”，不要擅自扩展成清理重建或额外测试。
- 若用户只是要标准 build/test/smoke，不要重复做命令解释分析；优先快路径执行脚本。
