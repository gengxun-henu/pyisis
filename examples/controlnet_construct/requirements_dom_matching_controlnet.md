# DOM Matching ControlNet 代码撰写计划与架构

> 说明：当前仓库中未找到既有的同名需求正文。以下内容基于文件名 `requirements_dom_matching_controlnet` 和现有 pyisis 示例风格先给出可执行的首版开发计划与架构草案，后续可按真实业务细节细化。

## 1. 代码撰写计划（先做最小可用版本）

- [ ] **阶段 A：输入与参数层**
  - 新建示例入口：`examples/controlnet_construct/dom_matching_controlnet.py`
  - 支持 CLI 参数：左/右（或多景）cube 路径、匹配窗口、阈值、输出 control net 路径
  - 统一参数校验与报错（缺参、路径不存在、窗口非法）

- [ ] **阶段 B：几何初始化与候选点生成**
  - 基于相机几何给出初始同名点候选
  - 对候选点做影像边界与可投影性过滤

- [ ] **阶段 C：DOM/相关匹配核心**
  - 对每个候选执行匹配（像素级 + 可选亚像素）
  - 记录匹配状态、相关性分数、失败原因

- [ ] **阶段 D：ControlNet 构建与输出**
  - 将成功匹配结果写入 `ControlNet / ControlPoint / ControlMeasure`
  - 输出 `.net`（或等效 control network 文件）
  - 同时输出摘要统计（成功数、失败数、平均匹配质量）

- [ ] **阶段 E：测试与验收**
  - 新增单测：`tests/unitTest/dom_matching_controlnet_example_test.py`
  - 覆盖：参数校验、单点成功路径、失败分支、最小端到端构网流程

## 2. 架构设计（分层 + 可替换）

### 2.1 模块划分

1. **CLI / Orchestrator 层**
   - 负责解析参数、组织流程、打印结果
   - 不承载复杂匹配逻辑

2. **Data Access 层**
   - 打开 cube、读取相机、坐标转换
   - 统一处理 `ISISDATA` 与文件可用性错误

3. **Matching Core 层**
   - 提供 `match_one(seed) -> MatchResult`
   - 封装匹配算法配置（窗口、阈值、是否亚像素）

4. **ControlNet Builder 层**
   - 将 `MatchResult` 映射为 ControlPoint/Measure
   - 维护 point id、measure 状态、忽略标记

5. **Reporting 层**
   - 输出结构化统计（JSON/控制台）
   - 用于测试断言与调试追踪

### 2.2 数据流

`输入影像 + 参数`  
→ `候选点生成`  
→ `逐点匹配`  
→ `过滤有效结果`  
→ `构建 ControlNet`  
→ `写出网络 + 统计报告`

### 2.3 关键接口草案

- `build_candidate_points(left_cube, right_cube, config) -> list[SeedPoint]`
- `run_dom_matching(seed_points, cubes, config) -> list[MatchResult]`
- `build_controlnet(matches, config) -> ControlNet`
- `save_controlnet(controlnet, output_path) -> None`
- `summarize(matches) -> dict`

### 2.4 非功能与扩展点

- **可复现**：固定随机种子（如有采样）
- **可观测**：失败原因分类（几何失败/匹配失败/越界）
- **可扩展**：后续可替换匹配内核（不同相关器）而不改 ControlNet Builder

## 3. 建议的首个交付里程碑（MVP）

- 支持双景输入
- 支持基础相关匹配
- 生成可写出的 ControlNet
- 提供 1 个最小可跑通单测和 1 个失败分支单测

