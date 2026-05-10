# 原始影像空间直接匹配并构建 ControlNet 设计

## 1. 背景与目标

当前 `examples/controlnet_construct` 主流程以 DOM 空间匹配为核心，再经 `dom2ori` 转换到原始影像空间后构网。新需求是在尽量复用现有架构前提下，支持**原始影像空间直接匹配并生成连接点控制网**，并支持：

- SIFT
- SuperPoint（独立方法）
- SuperGlue
- LoFTR

首版范围：**单对影像闭环**（直接输出原始空间 `.key` 与 `.net`），不要求批处理首发同步上线。

## 2. 范围与非目标

### 2.1 In Scope

1. 在现有入口扩展原始影像直接匹配能力（不新建独立主脚本）。
2. 新增原始影像匹配到构网的一体化子命令（建议 `from-ori-match`）。
3. 复用现有分块调度、并行、GPU 路由、统计摘要与 JSON sidecar 风格。
4. deep 依赖缺失时立即报错退出（不跨算法回退）。

### 2.2 Out of Scope

1. 首版不做 overlap 列表批处理。
2. 不改变既有 `from-dom` / `from-dom-batch` 语义。
3. 不做与本需求无关的大规模重构。

## 3. 方案概览（选定方案 B：架构复用型）

### 3.1 模块边界

1. `image_match.py`
   - 新增原始影像入口函数（如 `match_ori_pair` / `match_ori_pair_to_key_files`）。
   - 参数风格与 `match_dom_pair` 对齐，降低学习成本与配置迁移成本。

2. `tile_matching.py`
   - 抽象“影像读取后端”，使窗口匹配执行器可复用于 DOM 与 ORI。
   - 复用已有能力：分块、并行、GPU pipeline、deep matcher 适配、汇总统计。

3. `controlnet_stereopair.py`
   - 新增子命令（建议 `from-ori-match`）。
   - 内部流程：原始影像匹配产出 `.key` → 调用现有 `build_controlnet_for_stereo_pair` 构建 `.net`。

### 3.2 兼容策略

1. 默认行为保持不变，不影响现有 DOM 主流程。
2. 新能力通过新增函数/子命令启用，避免破坏旧脚本参数兼容。

## 4. 数据流与算法流程

### 4.1 原始影像匹配主链路

1. 低分辨率全局配准  
   在原始影像上先进行低分辨率粗匹配，估计初始位移/几何先验。

2. 重叠窗口生成与分块精匹配  
   参考现有 low-res offset + paired windows 思路，把粗配准结果注入窗口裁剪与偏移，执行分块匹配。

3. 匹配方法插件化  
   - `sift`：现有 SIFT 路径  
   - `superpoint`：独立方法（SuperPoint 特征 + 通用匹配）  
   - `superglue`：复用 SuperPoint 前端特征  
   - `loftr`：LoFTR 直接匹配

4. 结果落地与构网  
   直接写原始空间 `.key`，再调用现有 ControlNet 构建函数写 `.net`，不经过 `dom2ori`。

## 5. 错误处理与运行时策略

1. deep 方法依赖检查（`torch` / `kornia` / 对应 matcher 包）失败时立即抛错并退出。
2. 不做跨算法自动回退（例如 `superglue -> sift` 禁止）。
3. 可保留同算法内设备层回退（GPU -> CPU）逻辑，但不改变算法语义。
4. 统一失败输出结构，保持当前 JSON summary 习惯，新增 ORI 匹配阶段字段：
   - `matcher_method`
   - `tile_match_backend`
   - `low_resolution_offset`
   - `point_count`
   - `status` / `reason`

## 6. CLI 与配置设计

### 6.1 新子命令

在 `controlnet_stereopair.py` 增加 `from-ori-match`，输入至少包含：

1. `left_cube`, `right_cube`
2. `config`
3. `output_net`
4. 可选中间输出：`left_output_key`, `right_output_key`, `report_path`
5. 匹配参数（matcher_method、tile 参数、low-res 参数、并行/GPU参数）

### 6.2 参数对齐原则

尽量沿用 `image_match.py` 既有参数名与语义，减少重复定义与配置分裂。

## 7. 测试与验收

### 7.1 单测改动

1. `tests/unitTest/controlnet_construct_matching_unit_test.py`
   - 覆盖 ORI 匹配入口。
   - 覆盖 `superpoint` 独立方法分发和结果结构。
   - 覆盖 deep 依赖缺失即失败行为。

2. `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
   - 覆盖 `from-ori-match` CLI 参数转发。
   - 覆盖“匹配 -> .key -> .net”闭环。

### 7.2 回归要求

1. 既有 DOM 匹配与 from-dom 构网链路无行为回归。
2. 新增 ORI 流程在依赖满足时可稳定产出 `.key` 与 `.net`。

## 8. 风险与缓解

1. **风险：** ORI 空间纹理与几何变化大，粗配准失败率可能高于 DOM。  
   **缓解：** 保留低分辨率估计与 RANSAC 过滤参数可调，并在 summary 中输出失败原因。

2. **风险：** deep 依赖安装环境差异导致运行失败。  
   **缓解：** 启动前做依赖检查并给出明确安装提示，严格 fail-fast。

3. **风险：** 复用过程中 DOM/ORI 读取语义差异引入隐性 bug。  
   **缓解：** 通过后端抽象隔离读取层，并补充针对窗口坐标与输出坐标基准的一致性测试。
