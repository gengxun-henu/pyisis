---
description: "同步 pybind 台账与实际绑定进度。Use when: sync pybind ledgers, sync binding tracker, 同步台账, 同步 pybind 进度, 更新 todo_pybind11.csv, 更新 methods_inventory_summary.csv, 更新 *_methods.csv, ledger sync, progress sync, 同步所有未同步类, 同步所有未同步方法, all"
name: "sync-pybind-ledgers"
argument-hint: "可选：audit-only | apply-ledger-sync | all | class=<ClassName> | module=<Module Category>"
agent: "agent"
---

同步当前工作区中 pybind 绑定台账与实际开发进度，但**本任务只允许修改台账层文件，不允许修改绑定实现代码**。

目标：

- 让 `todo_pybind11.csv`
- `class_bind_methods_details/methods_inventory_summary.csv`
- 相关 `class_bind_methods_details/*_methods.csv`
- `pybind_progress_log.md`

与当前真实绑定状态保持一致。

## 模式

- `audit-only`：只审计差异并汇报，不修改任何文件。
- `apply-ledger-sync`：允许修改台账文件，但仍**禁止修改** `src/` 下绑定实现、`tests/` 下测试实现、以及其他无关代码文件。
- `all`：把范围显式设为“所有当前未同步的类与方法”，按证据链批量处理全局落后台账；可与 `audit-only` 或 `apply-ledger-sync` 组合使用。
- `class=<ClassName>`：只处理指定类。
- `module=<Module Category>`：只处理指定模块类别。
- 若未给出范围参数：
  - 默认先做全局差异审计。
  - 若用户明确要求“开始同步/开始实施/直接更新台账”，则可在确认范围后执行 `apply-ledger-sync`。
- 若给出 `all` 但未显式给出模式：
  - 若用户明确要求“同步所有未同步项/全部更新/直接全量同步”，则默认执行 `apply-ledger-sync` + `all`。
  - 否则默认执行 `audit-only` + `all`。

## 事实源优先级

同步时必须按以下优先级判断真实状态，**不要把 CSV 当作唯一真相来源**：

1. `src/module.cpp` 的顶层注册情况
2. `src/` 中相关 pybind 绑定实现文件
3. `python/isis_pybind/__init__.py` 的顶层 Python 导出
4. focused unit tests 是否覆盖相关绑定
5. `tests/smoke_import.py` 是否检查相关顶层符号
6. 现有台账文件（`todo_pybind11.csv`、`methods_inventory_summary.csv`、`*_methods.csv`、`pybind_progress_log.md`）

## 必查文件顺序

每次同步必须按这个顺序核对：

1. `todo_pybind11.csv`
2. `class_bind_methods_details/methods_inventory_summary.csv`
3. 目标类对应的 `class_bind_methods_details/*_methods.csv`
4. `pybind_progress_log.md`
5. `src/module.cpp`
6. 相关 `src/` 绑定文件
7. `python/isis_pybind/__init__.py`
8. 相关 focused unit tests（若存在）
9. `tests/smoke_import.py`

## 判定规则

### 允许判为“台账落后”的典型情况

- 绑定代码已经存在，但 `todo_pybind11.csv` 仍写未转换或旧备注。
- 类明细 `*_methods.csv` 仍大面积 `N`，但实际公开方法已暴露。
- `methods_inventory_summary.csv` 的 `Y Count / N Count / Partial Count / Completion Percent / Class Symbol Status` 与类明细或真实导出面不一致。
- `pybind_progress_log.md` 已记录某类已完成或补齐，但明细 CSV 或 summary 仍未同步。

### 必须谨慎处理、不得机械覆盖的情况

以下情况**不得**简单地把方法或类标成“未完成”，必须在备注里写清原因：

- 抽象基类或纯虚接口，仅导出基础符号/层级关系
- Qt `signals` / `slots` / `emit*` / `QVariant` 事件型接口
- 上游头文件声明存在，但 linked runtime 未导出对应符号
- 使用本地 wrapper 替代上游直接成员绑定的情况
- 故意不在 `__init__.py` 顶层重导出的类型
- 因生命周期、所有权、GIL、事件循环或 ABI 风险而刻意跳过的 API

### 不允许做的事

- 不允许修改 `src/` 下任何 C++ 绑定代码
- 不允许修改 `tests/` 下的测试实现
- 不允许擅自扩大为“补绑定/补测试/修编译”任务
- 不允许把“ledger sync”伪装成“新增绑定实现”
- 不允许删除 `pybind_progress_log.md` 既有历史记录，只能追加

## 输出与修改要求

### 如果是 `audit-only`

输出必须包含：

1. 差异摘要
2. 每个差异项的证据链：
   - 类名 / 模块类别
   - 相关绑定文件
   - 是否在 `src/module.cpp` 注册
   - 是否在 `python/isis_pybind/__init__.py` 导出
   - 是否被 focused unit test 或 `smoke_import.py` 反映
   - 哪个 ledger 文件落后
3. 建议修改哪些 ledger 文件
4. 哪些项需要人工判断

### 如果是 `apply-ledger-sync`

在完成核对后，只允许修改以下文件：

- `todo_pybind11.csv`
- `class_bind_methods_details/methods_inventory_summary.csv`
- 对应 `class_bind_methods_details/*_methods.csv`
- `pybind_progress_log.md`

并且必须：

- 先同步类明细 `*_methods.csv`
- 再同步 `methods_inventory_summary.csv`
- 再同步 `todo_pybind11.csv`
- 最后在 `pybind_progress_log.md` 追加一条简短记录，明确写明这是 **ledger sync**，不是新增 binding implementation
- 若范围为 `all`，只同步“已有充分证据证明台账落后”的类与方法；对证据不足或存在歧义的项，保留原状态并在汇报中列为“仍需人工判断”。

## 建议的汇报格式

请使用以下结构汇报：

- 本次模式：`audit-only` 或 `apply-ledger-sync`
- 范围：全局 / 某模块 / 某类
- 已核对的事实源
- 发现的差异
- 已更新的 ledger 文件（若有）
- 仍需人工判断的项
- 建议下一步（例如是否再补脚本化校验）

## 执行风格要求

- 先小范围核对，再批量同步；避免一口气改太多没有证据链的台账。
- 若用户明确使用 `all`，允许在一次任务中覆盖多个模块，但仍要按“类明细 → summary → todo → progress log”的顺序逐层同步，不要跳步。
- 若发现 `summary` 与 `__init__.py`、`smoke_import.py`、`pybind_progress_log.md` 冲突，优先回到 `src/` 实现核实。
- 若类级状态变化明显，必须同步对应 `*_methods.csv`，不要只改顶层台账。
- 若只能确认“顶层类可见”，但无法确认全部方法已完成，请诚实保留 `N` 或备注，不要凑整到 100%。
