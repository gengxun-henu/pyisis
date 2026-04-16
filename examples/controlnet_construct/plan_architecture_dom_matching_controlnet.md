# DOM Matching ControlNet 代码撰写计划与架构（初稿）

> 说明：本稿基于 `examples/controlnet_construct/requirements_dom_matching_controlnet.md` 工作稿生成，先给出可执行的实现计划与架构，后续可按正式需求逐条收敛。

## 1) 代码撰写计划

- [ ] **阶段 A：需求对齐与接口冻结**
  - 明确输入：左右影像、初始匹配策略参数、ControlNet 元数据（network_id/target/description）。
  - 明确输出：`.net` 文件、匹配统计、失败点日志。
  - 冻结 Python API（函数签名 + CLI 参数）。

- [ ] **阶段 B：最小可运行主链路（MVP）**
  - 读取双影像并建立相机上下文。
  - 对候选点执行 DOM 匹配（优先复用 `Isis::MaximumCorrelation`：即 ISIS 上游的最大相关匹配算法能力 + 相机几何初值）。
  - 将成功匹配结果写入 `ControlNet`（ControlPoint/ControlMeasure）。
  - 输出最小统计（成功率、平均 goodness_of_fit、失败原因分布）。

- [ ] **阶段 C：稳定性与可维护性增强**
  - 加入参数校验（窗口大小、阈值、输入范围）。
  - 失败分级（几何不可投影 / 匹配失败 / 无效像点）。
  - 增加结构化日志与可复现实验参数落盘。

- [ ] **阶段 D：验证与回归**
  - 新增 `tests/unitTest/controlnet_construct_*_unit_test.py` 聚焦测试。
  - 保持 `examples/` 可直接运行，并补 usage 文档。

## 2) 架构设计（建议）

### 2.1 模块划分

1. **输入与配置层**
   - `load_inputs(...)`：影像路径、参数、可选初值。
   - `validate_config(...)`：参数合法性检查。

2. **匹配执行层**
   - `estimate_seed(...)`：基于相机几何估计右图初值。
   - `run_dom_match(...)`：执行 DOM/相关匹配，返回匹配状态、质量指标。

3. **ControlNet 构建层**
   - `build_control_point(...)`：组装 Point + 两侧 Measure。
   - `append_to_controlnet(...)`：写入网络并维护 point id。

4. **输出与报告层**
   - `write_controlnet(...)`：输出 `.net`。
   - `summarize_metrics(...)`：输出 JSON/控制台统计。

### 2.2 关键数据流

`输入影像 + 参数` → `候选点/初值` → `DOM 匹配` → `质量筛选` → `ControlPoint 组装` → `ControlNet 持久化 + 统计报告`

### 2.3 API 形态（建议）

- Python 函数：
  - `construct_controlnet_with_dom_matching(left_cube, right_cube, *, candidates=None, config: dict | DomMatchConfig) -> Result`
  - `config` 建议至少包含：`pattern_samples`、`pattern_lines`、`search_samples`、`search_lines`、`tolerance`、`use_subpixel`、`quality_threshold`。
  - 字段约定：`pattern_samples`、`pattern_lines`、`search_samples`、`search_lines` 为必填；`tolerance`、`use_subpixel`、`quality_threshold` 可选（可提供默认值）。
- CLI：
  - `python examples/controlnet_construct/...py --left ... --right ... --onet ...`

### 2.4 异常与边界策略

- 输入文件不存在 / 相机不可用：立即失败并给出明确错误。
- 点位越界或几何不可投影：记录并跳过该点。
- 匹配质量低于阈值：不入网，仅计入失败统计。

### 2.5 测试策略（最小增量）

- 单元测试：
  - 参数校验与异常分支。
  - 单点成功匹配时 ControlPoint/Measure 字段正确。
- 示例回归：
  - 示例脚本最小链路可执行（输入→输出文件存在且 point 数 > 0）。

## 3) 里程碑交付（建议）

- **M1**：可运行 MVP（单线程、基础统计）。
- **M2**：稳定性增强（失败分级、日志、配置化）。
- **M3**：测试与文档完善（unit test + usage）。
