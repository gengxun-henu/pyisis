<!--
Adaptive lighting router implementation plan
Author: GitHub Copilot
Created: 2026-05-14
Updated: 2026-05-15  Refined the next-step plan to prefer user-facing quality profiles over exposing many low-level threshold parameters directly.
-->

# Adaptive Lighting Router Implementation Plan — 2026-05-14

## 1. 当前目标

在不重写现有 `examples/image_match/` 匹配架构的前提下，把 `adaptive_routing.py` 中已有的策略 helper 以“pair 级前置策略层 + 质量门控级联回退”的方式接入 `examples/image_match/image_match.py`。

首个 MVP 不依赖真实 DEM 渲染：

1. 复用低分辨率预览做真实纹理 probe；
2. 生成 pair 级 route decision；
3. 将首选 matcher 注入现有 tile matching 路径；
4. 对结果做质量门控；
5. 质量不足时按 fallback chain 重试；
6. 将 route / quality / final decision 写入现有 metadata sidecar。

## 2. 已完成状态（截至 2026-05-14）

### 已完成

- `adaptive_routing.py` helper 层已存在并包含：
  - `ImageTextureProbe`
  - `RenderProbe`
  - `SpiceLightingConstraints`
  - `PairRoutingDecision`
  - `MatchQualityReport`
  - `compute_real_image_texture_probe()`
  - `route_matcher_for_pair()`
  - `build_cascade_plan()`
  - `evaluate_match_quality()`
  - `decide_post_match_action()`
  - `build_pair_probe_sidecar()`
- `image_match.py` 已接入：
  - `--adaptive-routing` / `--no-adaptive-routing`
  - config key `enable_adaptive_routing` / `enableAdaptiveRouting`
  - 低分辨率 preview texture probe route
  - `matcher_method_requested` 与 `matcher_method_effective`
  - adaptive routing summary / metadata sidecar
  - fallback cascade execution
  - quality gate diagnostics
- Focused tests 已覆盖：
  - CLI/config 行为；
  - adaptive route 注入 effective matcher；
  - fallback cascade 从 `lightglue` 退到 `loftr`；
  - metadata sidecar 追加 adaptive routing 字段；
  - helper 层质量门控和 cascade 规则。

### 尚未完成

- 质量门控阈值仍主要使用 `evaluate_match_quality()` 默认值，尚未整理成用户友好的 profile / preset。
- 底层质量阈值尚未作为专家级 config override 暴露；首选不要把所有阈值直接放到普通 CLI 参数里。
- 当前质量门控的 residual summary 仍是占位式零残差；后续应接入真实 RANSAC/残差统计。
- SPICE 自动太阳几何提取尚未接入。
- DEM `shadow` / Lambertian render probe 尚未实现。
- render probe 信号尚未参与 route decision。
- 深度 matcher 真实 smoke path 仍受环境依赖影响，尚需在 `deep-learning` 环境或具备依赖的环境补验。

## 3. 分阶段计划

## Phase A — MVP 接线准备

目标：只做 pair 级 adaptive routing，不改变 `examples/controlnet_construct/` 业务语义，不做 tile 级 router，不在首轮实现真实 DEM render probe。

任务：

1. 明确 adaptive routing 默认行为：默认关闭，需显式启用。
2. 设计 CLI/config 接入面，保持 kebab-case CLI 与 config 默认继承。
3. 在 `match_dom_pair()` 的 full-resolution matching 前计算 texture probe。
4. 调用 `route_matcher_for_pair()`，输出 `PairRoutingDecision`。
5. 将 route 决策追加进 summary / metadata sidecar。

当前状态：已完成。

## Phase B — 质量门控与 cascade 闭环

目标：把单次 `matcher_method` 执行扩展为“initial matcher → quality gate → fallback matcher”的串行闭环。

任务：

1. 复用现有 tile matching dispatch，不新增第二套 matcher backend。
2. 从 tile results 中抽取统一 quality 指标。
3. 接入 `evaluate_match_quality()`。
4. 接入 `decide_post_match_action()`。
5. 按 `build_cascade_plan()` 执行 fallback chain。
6. 将 `cascade_plan`、`cascade_attempts`、`match_quality`、`final_decision` 写入 metadata。
7. 增加 focused tests。

当前状态：主链路已完成；下一步建议把质量门控 profile 化，并接入真实残差统计。

接口策略：先做少量用户可理解的质量 profile，而不是直接把所有底层 inlier / coverage / residual 阈值暴露成 CLI 参数。底层阈值应保持为内部实现细节，并记录到 metadata 以便复现；专家级 override 可后置到 config 文件。

## Phase C — SPICE 自动几何提取

目标：自动填充 `SpiceLightingConstraints`，为 render probe 和 route decision 提供真实太阳几何约束。

任务：

1. 从 ISIS cube label / SPICE 导航能力中提取左右影像真实太阳高度角估计。
2. 估计当前区域时间跨度内的太阳高度角 min/max。
3. 构造 conservative elevation candidate list。
4. 自动提取失败时降级为空约束，不阻塞基础 routing。
5. 写入 sidecar：
   - `solar_elevation_min`
   - `solar_elevation_max`
   - `real_estimated_elevation_left`
   - `real_estimated_elevation_right`
   - `render_probe_elevation_candidates`

当前状态：未开始。

## Phase D — DEM render probe

目标：用低成本 `shadow` / Lambertian render probe 评估真实纹理是否受地形阴影主导，并将信号纳入 route decision。

任务：

1. 新增独立 `render_probe.py` 或同级模块。
2. 使用低分辨率 DEM 和候选太阳几何生成 render previews。
3. 对真实图与 render preview 做结构 probe。
4. 输出 `RenderProbe` 字段：
   - `best_render_azimuth`
   - `best_render_elevation`
   - `best_render_score`
   - `render_peak_sharpness`
   - `terrain_explainability_score`
   - `render_score_curve`
5. 将 `RenderProbe` 接入 `route_matcher_for_pair()`。
6. 增加 lighting gap 回归测试。

当前状态：未开始。

## Phase E — 数据驱动阈值与高级增强

目标：基于积累的 sidecar 数据沉淀 DOM / ORI 任务特化阈值，并保留 tile 级策略、Hapke、lightweight router 扩展口。

任务：

1. 统计一批真实 pair 的 route / quality / final decision sidecar。
2. 区分 DOM matching 与 ORI matching 的默认阈值。
3. 再考虑 tile 级局部策略。
4. 再考虑 edge / gradient / shadow mask 多表征 probe。
5. 最后再考虑 Hapke 与 learned router。

当前状态：未开始。

## 4. 文件级 checklist

### `examples/image_match/adaptive_routing.py`

- 保持 dataclass schema 稳定。
- 后续优先补 quality profile / quality gate config helper。
- 将 `balanced`、`strict`、`fast`、`relaxed` 等 profile 映射到底层阈值，避免调用侧散落硬编码阈值。
- 不把 ISIS/SPICE 读取和 DEM render 扫描放入本文件，保持 helper 纯函数性质。

### `examples/image_match/image_match.py`

- 已接入 adaptive routing CLI/config。
- 已接入 route decision 与 fallback cascade。
- 下一步建议：暴露少量高层 quality profile / fallback mode 到 CLI/config。
- 暂不把每个底层 quality gate 阈值作为普通 CLI 参数暴露；如需调参，后续仅作为专家级 config override。
- 后续建议：将真实 RANSAC/残差统计接入 `_quality_report_for_tile_results()`。

### `examples/image_match/tile_matching.py`

- 继续复用现有 matcher dispatch。
- 如后续需要真实 residual/inlier 统计，可考虑在 tile result 或后处理 helper 中增加统一结果摘要。

### `examples/image_match/lowres_offset.py`

- 继续作为低分辨率 preview 产物来源。
- 避免重复生成低分辨率 cube。

### `tests/unitTest/image_match_adaptive_routing_unit_test.py`

- 维护 helper 层规则和 schema 回归。
- 后续补 quality profile 到 threshold 映射、未知 profile 拒绝、metadata 阈值记录等回归。

### `tests/unitTest/controlnet_construct_matching_unit_test.py`

- 维护 `image_match.py` 集成回归。
- 后续补 quality profile / fallback mode 的 CLI/config 回归。

## 5. 推荐下一步

优先推进“质量门控 profile 化”，而不是直接暴露全部底层阈值。目标是让普通用户选择策略意图，让高级用户在确有需要时再碰专家级阈值。

1. 在 `adaptive_routing.py` 增加 quality profile helper，例如 `resolve_quality_gate_profile()`。
2. 内置少量 profile：
   - `balanced`：默认策略，兼顾召回和稳定性；
   - `strict`：更保守，适合宁可少匹配也要高置信度的控制网场景；
   - `fast`：更偏速度和少回退，适合预筛或交互式试跑；
   - `relaxed`：更高召回，适合弱纹理或需要人工复核的批处理。
3. 在 CLI/config 只新增少量高层字段：
   - `adaptive-quality-profile`，默认 `balanced`；
   - `adaptive-fallback-mode`，可选 `auto` / `off` / `strict`，默认 `auto`。
4. 将 profile 解析出的底层阈值传入 `_quality_report_for_tile_results()` → `evaluate_match_quality()`。
5. 在 summary/metadata 记录：
   - 使用的 profile；
   - fallback mode；
   - profile 展开后的实际底层阈值。
6. 后续如确有生产调参需求，再在 config 文件中支持专家级 `adaptive_quality.thresholds` override；不作为首批普通 CLI 参数。
7. 补 focused tests，覆盖 profile 映射、CLI/config 继承、metadata 记录、fallback mode 行为。

这个增量仍然风险低、可测试，同时避免把研发调参细节直接推给普通用户。底层阈值继续保留在 metadata 中，既能复现实验，也能为后续数据驱动阈值沉淀留口子。
