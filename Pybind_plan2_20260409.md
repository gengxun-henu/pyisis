# Pybind Plan 2（2026-04-09）

## 目的

基于以下台账与约束，确定下一步优先推进的 10 个 pybind 绑定类，并形成可直接执行的 rollout 队列：

1. `todo_pybind11.csv`
2. `class_bind_methods_details/methods_inventory_summary.csv`
3. `reference/notes/base_inventory_rollout_order_2026-04-08.md`
4. `pybind_progress_log.md`

本计划遵循 `.github/skills/pybind-rollout-execution/SKILL.md` 的核心规则：

- **候选来源** 以 `todo_pybind11.csv` 与 `methods_inventory_summary.csv` 为准；
- **阶段与顺序** 受 `reference/notes/base_inventory_rollout_order_2026-04-08.md` 约束；
- **批次大小** 本次按用户要求给出 **10 类队列**；
- **执行单位** 仍然必须是 **1 次只做 1 个类**，每个类完成“绑定 + focused unit test + smoke + 台账同步”后，再进入下一个类。

---

## 当前阶段判断

根据 `pybind_progress_log.md`：

- 第二阶段基础类已基本完成；
- 第三阶段 photometry 队列已完成；
- 第四阶段后端 / 桥接 / 工具类中，已完成：
  - `Blobber`
  - `CubeBsqHandler`
  - `CubeCachingAlgorithm`
  - `CubeIoHandler`
  - `RegionalCachingAlgorithm`
  - `RawCubeChunk`
  - `OriginalLabel`
  - `OriginalXmlLabel`
- 因此下一步应继续**第四阶段剩余未完成项**，而不是跳去新阶段或重新打散优先级。

这意味着：本次优先 10 类应直接从第四阶段未完成队列中，按既定顺序向后取前 10 个。

---

## 选型原则

本次队列选择使用以下过滤逻辑：

1. 在 `todo_pybind11.csv` 中必须仍为 `未转换`；
2. 在 `methods_inventory_summary.csv` 中必须仍为 `Class Symbol Status = N` 或未完成状态；
3. 必须属于**当前 active phase（第四阶段）**；
4. 同阶段内不重新发明全局顺序，按 rollout note 既定顺序取前 10 个；
5. 优先形成“同类问题集中处理”的桥接/解析批次，减少实现风格来回切换成本。

---

## Active Queue（10 类）

> 说明：这是 **queue**，不是并行实施列表。实际执行时仍按 1 → 10 逐个收口。

| Queue | Class | Module Category | Summary Open Items | 选择原因 | 主要风险 / 备注 |
|---|---|---:|---:|---|---|
| 1 | `CubeTileHandler` | Low Level Cube I/O | 3 | 第四阶段剩余队列中的首个未完成类；与已完成的 `CubeBsqHandler` / `CubeIoHandler` 同属 cube handler 链，复用现有实现模式最多 | 小型 handler 包装类，但需处理 `QFile`/owned wrapper 与 `update_labels(...)` 行为一致性 |
| 2 | `Plugin` | System | 3 | 紧随 handler 链后的阶段 4 工具类；接口面极小，适合作为本批次中的 quick win | `QFunctionPointer` 对 Python 不友好，需谨慎决定导出表面，可能只能做有限稳定封装 |
| 3 | `FileList` | Parsing | 6 | 第四阶段解析/翻译子组的起点；API 小、概念清晰，适合开启 parsing 子批次 | `istream/ostream` 重载不适合直接暴露，可能需优先落地 `FileName`/路径版与 Python-friendly 文本 helper |
| 4 | `CSVReader` | Parsing | 26 | 当前 parsing 子组中的基础读取器；后续表格/翻译工具可能复用其数据表面 | 抽象基类/纯虚接口；需要先确认是否仅导出基类符号与稳定查询面，避免不安全构造 |
| 5 | `IString` | Parsing | 39 | 属于 ISIS 解析工具核心字符串助手；一旦稳定导出，可反哺多个 parsing/translation 类测试 | 方法数较多，且静态/实例重载密集；应分稳定子集逐步补齐，避免一次性铺太大 |
| 6 | `LabelTranslationManager` | Parsing | 5 | 翻译管理器体系的基类入口，位于 `Pvl*TranslationManager` 之前，顺序合理 | 抽象基类；更适合先导出类符号 + 稳定 helper，而非强开完整可实例化路径 |
| 7 | `PvlTokenizer` | Parsing | 5 | 与 `PvlToken` 紧密耦合，且接口较小；适合作为 PVL 解析链路的先手类 | 返回 `std::vector<PvlToken> &`，要谨慎处理生命周期与复制/引用语义 |
| 8 | `PvlToken` | Parsing | 11 | `PvlTokenizer` 的直接数据节点，完成后可支撑 token list 的 Python 侧可检查性 | `QString`/`vector<QString>` 适配需要统一成 Python `str` / `list[str]` |
| 9 | `PvlTranslationTable` | Parsing | 8 | 是多个 translation manager 的共同基础表；先做它可降低后续 manager 类复杂度 | `istream` 重载、`PvlKeyword` 返回值与翻译缺省逻辑需按上游行为校准 |
| 10 | `PvlToPvlTranslationManager` | Parsing | 8 | 在 translation table 之后推进最自然；可作为 manager 层第一类具体落地对象 | 依赖 `PvlTranslationTable` / `LabelTranslationManager` 语义，宜在前 9 类完成后再开工 |

---

## 为什么这 10 个比其他未完成类更优先

### 1. 它们符合 rollout 规则里的“当前 phase 向前推进”

当前不是重新选“全仓最小 10 类”，而是继续推进第四阶段剩余队列。按规则，这比跳到别的模块更优先。

### 2. 它们构成一个连续的技术子链

本批 10 类实际上分成两段：

- **cube handler 尾项**：`CubeTileHandler`
- **parsing / translation 主链起步**：`Plugin`、`FileList`、`CSVReader`、`IString`、`LabelTranslationManager`、`PvlTokenizer`、`PvlToken`、`PvlTranslationTable`、`PvlToPvlTranslationManager`

这样做的好处是：

- 绑定代码位置更集中；
- 单测风格更集中；
- 生命周期 / Qt / string / PVL 适配问题会重复出现，修一次能连带受益多个类。

### 3. 它们比仍未入队的后续第四阶段类更靠前

本次未纳入但仍属于第四阶段后续候选的类包括：

1. `PvlToXmlTranslationManager`
2. `XmlToPvlTranslationManager`
3. `PvlFormat`
4. `PvlFormatPds`

这些类并不是不重要，而是按当前阶段顺序排在本次 10 类之后，应作为下一批递延对象。

---

## 建议的执行顺序与收口策略

### 执行模型

- **Queue size**：10
- **Execution unit**：1
- **当前执行起点**：`CubeTileHandler`

### 推荐收口顺序

1. `CubeTileHandler`
2. `Plugin`
3. `FileList`
4. `CSVReader`
5. `IString`
6. `LabelTranslationManager`
7. `PvlTokenizer`
8. `PvlToken`
9. `PvlTranslationTable`
10. `PvlToPvlTranslationManager`

### 每类最小闭环

每个类都按以下闭环完成后再进入下一类：

1. 读取 `todo_pybind11.csv`
2. 读取 `methods_inventory_summary.csv`
3. 读取对应 `*_methods.csv`
4. 查找相似 binding / tests
5. 读上游 `.h` / `.cpp` / `unitTest.cpp`
6. 做最小稳定 pybind 暴露
7. 补 focused unit test
8. 构建
9. 跑 focused unit test
10. 跑 `tests/smoke_import.py`
11. 同步更新：
   - `todo_pybind11.csv`
   - 目标 `*_methods.csv`
   - `methods_inventory_summary.csv`
   - `pybind_progress_log.md`

---

## 每类的具体建议

### 1. `CubeTileHandler`

- **目标定位**：补全 low-level cube handler 链最后一个明显缺口。
- **实现建议**：优先复用 `CubeBsqHandler` / `CubeIoHandler` 的 QFile-owned wrapper 方案。
- **测试建议**：最小 label + data file 场景，验证构造与 `update_labels(...)`。
- **优先级结论**：本批次的首类，应该最先做。

### 2. `Plugin`

- **目标定位**：补一个系统层小接口 quick win。
- **实现建议**：先确认上游 `QFunctionPointer` 是否值得导出；若不能稳定映射，优先导出类符号与受限 helper，避免过度承诺。
- **测试建议**：以最小构造与错误路径为主，不强求函数指针可调用。

### 3. `FileList`

- **目标定位**：建立 ISIS 列表文件对象的 Python 侧可读写表面。
- **实现建议**：路径版 `read/write` 优先；流式重载可延后或做 Python 字符串 helper。
- **测试建议**：临时文件 round-trip、空列表、重复项、路径解析。

### 4. `CSVReader`

- **目标定位**：先导出抽象基类符号与稳定查询面。
- **实现建议**：不要强行构造抽象类；必要时只暴露只读配置/表面 API，配合现有或新建轻量 wrapper。
- **测试建议**：若无稳定 concrete 类型，先做 symbol-level / repr / interface-shape smoke。

### 5. `IString`

- **目标定位**：补 ISIS 常用字符串工具，提升 parsing 工具可用性。
- **实现建议**：拆成稳定子集：trim / case convert / numeric convert / replace / split，先做这些高价值接口。
- **测试建议**：对齐上游字符串边界行为，尤其空串、空白、大小写、数值转换失败路径。

### 6. `LabelTranslationManager`

- **目标定位**：给翻译管理器体系提供公共抽象基底。
- **实现建议**：先做抽象基类符号和非构造型接口；不要越级展开过多具体子类行为。
- **测试建议**：接口存在性 + 继承层级检查优先。

### 7. `PvlTokenizer`

- **目标定位**：打开 PVL 文本到 token list 的解析入口。
- **实现建议**：优先做 `load(...)`、`clear()`、`get_token_list()`；`istream` 可通过 Python-friendly 文本输入包装解决。
- **测试建议**：最小 PVL 文本解析，检查 token 数量与关键词顺序。

### 8. `PvlToken`

- **目标定位**：把 tokenizer 产物变成可检查的 Python 值对象。
- **实现建议**：优先暴露 key/value 基础表面与 `value_vector()` 的 Python list 适配。
- **测试建议**：key 大小写、value 添加/清空、多值 keyword。

### 9. `PvlTranslationTable`

- **目标定位**：建立 translation manager 依赖的基础查表能力。
- **实现建议**：先做路径版 `add_table(...)`、`translate(...)`、`input_default(...)`、`input_keyword_name(...)`。
- **测试建议**：最小 translation table 文件驱动的翻译映射与 default 路径。

### 10. `PvlToPvlTranslationManager`

- **目标定位**：作为 translation manager 首个具体对象，验证 manager 层完整闭环。
- **实现建议**：排在 `PvlTranslationTable` 之后，实现时优先选择最小可跑通的 `translate(...)` / `auto(...)` / `set_label(...)` 路径。
- **测试建议**：小型输入 PVL + translation table 的自动翻译回归。

---

## 风险分层

### 低风险（建议优先快速收口）

- `CubeTileHandler`
- `Plugin`
- `FileList`
- `PvlTokenizer`
- `PvlToken`

### 中风险（需要类型/生命周期适配）

- `PvlTranslationTable`
- `PvlToPvlTranslationManager`
- `LabelTranslationManager`

### 较高风险（抽象类 / 接口面较大）

- `CSVReader`
- `IString`

> 说明：即使 `CSVReader` 和 `IString` 风险更高，按当前 rollout 规则，它们仍在本批 10 类队列中，只是实际执行时需要严格控制单类收口范围。

---

## 本批次之外的下一顺位候选

如果本批 10 类完成，建议下一批按既定顺序继续：

1. `PvlToXmlTranslationManager`
2. `XmlToPvlTranslationManager`
3. `PvlFormat`
4. `PvlFormatPds`

完成这些后，第四阶段 parsing / translation / plugin 子组就基本收尾，可再重新评估是否切换到新的 active phase。

---

## 最终结论

按照当前 ledger 状态、阶段约束和 rollout 规则，**下一步优先绑定的 10 个类**应为：

1. `CubeTileHandler`
2. `Plugin`
3. `FileList`
4. `CSVReader`
5. `IString`
6. `LabelTranslationManager`
7. `PvlTokenizer`
8. `PvlToken`
9. `PvlTranslationTable`
10. `PvlToPvlTranslationManager`

其中，**当前应立即开工的首类**是：`CubeTileHandler`。
