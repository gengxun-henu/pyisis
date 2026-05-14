<!--
初步方案：自适应光照感知匹配策略
Author: GitHub Copilot
Created: 2026-05-13
Updated: 2026-05-13  初步整理基于 ISIS/SPICE/DEM 渲染的自适应匹配选路方案，纳入 shadow/Lambertian probe 与 SPICE 约束太阳高度角搜索范围设计。
-->

# optimze-match-auto-lighting-20260513

## 1. 方案目标

本方案的目标不是直接替换现有 `examples/image_match/image_match.py` 的匹配实现，而是在其前面增加一层**自适应感知与匹配器选路策略层**，使系统能够在处理月球立体像对时，根据：

1. 影像纹理丰富程度；
2. 两景之间的光照一致性；
3. 影像纹理是否主要由地形阴影/坡向驱动；
4. 低成本探测匹配阶段的几何稳定性；

自动决定优先采用：

- `SIFT`
- `SuperPoint + LightGlue / SuperGlue`
- `LoFTR`

并在初次策略失败时，按级联方式自动回退到更强鲁棒的深度匹配方法。

本方案优先服务于以下场景：

- 月球原始像对或 DOM 像对的控制网构建；
- 在效率、匹配点密度、空间分布均匀性之间做平衡；
- 在大批量 pair 中避免统一使用单一 matcher 带来的过度保守或过度昂贵。

---

## 2. 设计原则

### 2.1 先探测、再匹配

不直接对每个 pair 固定使用某一个 matcher，而是先做低成本 probe，再决定最终 matcher。

### 2.2 先便宜后昂贵

优先尝试便宜方法；仅在质量不足时再升级到深度模型：

- 第一优先：`SIFT`
- 第二优先：`SuperPoint + LightGlue / SuperGlue`
- 第三优先：`LoFTR`

### 2.3 物理先验只做“辅助信号”，不做唯一真理

基于 DEM 渲染出的影像与真实影像之间始终存在 domain gap，因此渲染匹配结果只作为**路由参考信号**，而不是唯一决策依据。

### 2.4 优先使用简单稳健的光照渲染

对于 matcher 选路问题，优先采用：

- ISIS `shadow` 模块；
- 或 Lambertian 式 DEM 光照渲染；

将 Hapke 模型保留为后续增强版候选，而不是第一阶段默认方案。

原因是 `shadow/Lambertian`：

- 参数更少；
- 计算更快；
- 更适合做大规模角度扫描；
- 更适合判断“这幅图的纹理是否主要受地形阴影控制”。

---

## 3. 核心思路概览

整体流程分为五层。

### 第 0 层：基础输入准备

对每个待处理 pair，准备以下基础信息：

- 左右影像（ORI 或 DOM）；
- 对应区域的低分辨率 LOLA DEM（如 10 m）；
- 该区域几何范围；
- 左右影像的成像时间；
- SPICE 可提供的太阳几何先验范围。

### 第 1 层：真实影像自身纹理 probe

对每幅真实影像的低分辨率版本计算：

- `SIFT keypoint density`
- `gradient energy`
- `Laplacian variance`
- `local entropy`
- `valid pixel ratio`

得到每幅影像的 `real_texture_score`。

### 第 2 层：DEM 渲染 probe

使用 ISIS `shadow` 或 Lambertian 渲染，在一组候选太阳方位角/高度角下，对 DEM 生成低分辨率渲染图。

然后将真实影像与这些渲染图做低成本匹配探测，得到：

- `best_render_azimuth`
- `best_render_elevation`
- `best_render_score`
- `render_peak_sharpness`
- `terrain_explainability_score`

### 第 3 层：pair 级光照/难度评估

对左右影像的 probe 结果进行合并，得到 pair 级指标：

- `render_inferred_lighting_gap`
- `mean_real_texture_score`
- `mean_terrain_explainability_score`
- `estimated_match_difficulty`

### 第 4 层：匹配器路由

根据上述指标初步选择 matcher：

- `SIFT`
- `LightGlue / SuperGlue`
- `LoFTR`

### 第 5 层：质量门控与级联回退

即使完成初次匹配，也必须通过质量门槛：

- RANSAC 内点数
- 内点率
- 匹配点空间覆盖率
- 残差统计

若不达标，则自动升级 matcher。

---

## 4. 真实影像纹理 probe 设计

### 4.1 目标

判断一幅影像是否：

- 纹理丰富，适合 `SIFT`；
- 纹理中等，适合 `SuperPoint + LightGlue`；
- 纹理贫乏，可能需要 `LoFTR`。

### 4.2 建议指标

每幅影像在低分辨率层计算：

1. `SIFT keypoint count`
2. `SIFT keypoint density = keypoint_count / valid_pixel_count`
3. 平均梯度幅值
4. Laplacian 方差
5. 局部熵
6. 有效像素比例

### 4.3 纹理评分建议

定义综合纹理分数：

$$
T = \alpha \cdot \mathrm{norm}(kp\_density)
+ \beta \cdot \mathrm{norm}(gradient)
+ \gamma \cdot \mathrm{norm}(entropy)
+ \delta \cdot \mathrm{norm}(laplacian)
$$

其中权重先采用经验值，后续可通过统计结果回归调整。

### 4.4 初始用途

- 作为 pair 级 matcher route 的基础因子；
- 当渲染 probe 得分不明显时，纹理 probe 可作为更高优先级参考。

---

## 5. DEM 渲染 probe 设计

## 5.1 目标

通过 DEM 渲染的参考影像，估计：

1. 真实影像是否主要受地形阴影主导；
2. 哪组太阳几何参数与真实影像外观最接近；
3. 该影像对太阳方向变化的敏感程度。

## 5.2 推荐渲染模型优先级

### 第一阶段默认

- ISIS `shadow`
- Lambertian 式月面地形渲染

### 第二阶段增强（可选）

- Hapke 渲染

第一阶段优先使用 `shadow/Lambertian`，因为其更适合做：

- 大规模角度扫描；
- 低成本探测；
- 地形纹理可解释性评估。

## 5.3 渲染输入

每幅待匹配影像对应的 probe 渲染需输入：

- 低分辨率 DEM；
- 目标区域范围；
- 一组候选太阳方位角；
- 一组候选太阳高度角；
- 可选固定观测方向简化假设。

## 5.4 渲染 probe 输出

每幅影像最终输出：

- `best_render_azimuth`
- `best_render_elevation`
- `best_render_score`
- `render_score_curve`
- `render_peak_sharpness`
- `terrain_explainability_score`

其中：

- `terrain_explainability_score` 表示真实影像有多少纹理可由 DEM + 光照解释；
- `render_peak_sharpness` 表示真实影像是否对特定太阳方向高度敏感。

---

## 6. 融入 SPICE 约束太阳高度角搜索范围

这是本次新增的重要设计点。

## 6.1 设计动机

用户指出：

- 对一个给定月面区域，可以通过 SPICE 提前计算某个时间跨度内的最大/最小太阳高度角；
- 因此在 probe 渲染阶段，没有必要扫描与真实成像高度角差异过大的范围；
- 应优先探测与真实影像高度角更接近的角度。

这一点非常重要，因为它可以显著减少：

- 无效渲染组合数量；
- 不必要的 probe 成本；
- 渲染域差带来的误导。

## 6.2 SPICE 约束的使用方式

对每个待处理 pair 所对应的区域：

1. 根据区域范围与时间跨度，利用 SPICE 计算：
   - 太阳高度角最小值；
   - 太阳高度角最大值；
   - 可选太阳方位角变化范围；
2. 根据左右影像实际成像时间附近的太阳几何，构造一个“现实可达”的 probe 搜索窗口；
3. probe 只在该窗口内采样，而非在全范围盲扫。

## 6.3 建议搜索策略

### 方位角搜索

方位角仍可采用：

- 每 10° 一档；
- 或在真实太阳方位角附近加密，例如 `±40°` 内 5° 一档，外圈 10° 一档。

### 高度角搜索

高度角不建议全局大跨度粗扫，而建议：

1. 以真实成像时刻推算出的太阳高度角为中心；
2. 用 SPICE 给出的区域时间跨度可达范围裁剪边界；
3. 在接近真实值的范围内优先采样。

例如：

- 若真实高度角约为 $32^\circ$；
- SPICE 估计本区域在相关时间跨度可达范围为 $[24^\circ, 38^\circ]$；
- 则 probe 可优先采样：
  - $26^\circ, 30^\circ, 32^\circ, 34^\circ, 38^\circ$

而不是去扫诸如 $5^\circ$、$70^\circ$ 这种明显不现实的高度角。

## 6.4 预期收益

引入 SPICE 约束后，可带来以下收益：

1. 更少的渲染样本数；
2. 更高的 probe 命中率；
3. 更符合实际成像条件；
4. 避免被明显不合理的太阳高度角渲染结果误导 matcher 路由。

## 6.5 作为路由特征的形式

建议在最终 pair-level probe 元数据中加入：

- `spice_solar_elevation_min`
- `spice_solar_elevation_max`
- `real_solar_elevation_estimated`
- `render_probe_elevation_candidates`
- `best_render_elevation`
- `render_real_elevation_gap`

其中 `render_real_elevation_gap` 可作为一个稳定特征参与路由判断。

---

## 7. 真实图与渲染图的 probe 匹配方式

## 7.1 原则

probe 阶段不一定要使用与最终生产阶段完全相同的 matcher。

因为真实图与渲染图之间存在 radiometric gap，probe 更适合比较：

- 结构
- 阴影边界
- 梯度方向
- 几何一致性

而不是绝对灰度值。

## 7.2 推荐 probe 比较对象

优先考虑以下表示：

1. 原始灰度图（baseline）
2. 梯度幅值图
3. Canny 边缘图
4. 阴影 mask（如可稳定得到）

## 7.3 推荐 probe 评分项

对每张真实图与每张渲染图，计算：

- RANSAC 后内点数
- 内点率
- 空间覆盖率
- 重投影残差
- 结构相似性附加项（可选）

可定义：

$$
S_{probe} = w_1 \cdot inlier\_count + w_2 \cdot inlier\_ratio + w_3 \cdot coverage - w_4 \cdot residual
$$

由分数最高的渲染参数作为该影像的最佳解释候选。

---

## 8. Pair 级 matcher 路由策略

## 8.1 pair 级关键特征

对左右影像合并后得到：

- `mean_real_texture_score`
- `left/right terrain_explainability_score`
- `render_inferred_azimuth_gap`
- `render_inferred_elevation_gap`
- `render_peak_sharpness`
- `estimated_match_difficulty`

## 8.2 初始经验规则

### Route A：优先 SIFT

条件倾向：

- 左右影像纹理丰富；
- render probe 分数较高；
- 左右最佳渲染光照接近；
- 预期阴影差异不大。

### Route B：优先 SuperPoint + LightGlue / SuperGlue

条件倾向：

- 纹理中等；
- 有一定可解释地形纹理；
- 左右光照差异中等；
- SIFT 可能可用，但稳定性不够高。

### Route C：优先 LoFTR

条件倾向：

- 纹理弱；
- 或 render probe 表明两景阴影差异较大；
- 或真实图自身 probe 显示传统 keypoint 稀疏；
- 或历史经验表明该类 pair 容易失败。

---

## 9. 质量门控与回退策略

## 9.1 不以“匹配点数量”作为唯一依据

matcher 结果是否合格，不应只看匹配点数，而应至少检查：

- RANSAC 内点数
- 内点率
- 点的空间覆盖均匀性
- 几何残差

## 9.2 建议回退顺序

- `SIFT` 失败或质量不足 → `LightGlue / SuperGlue`
- `LightGlue / SuperGlue` 失败或质量不足 → `LoFTR`
- `LoFTR` 结果仍需几何过滤，不能直接无条件接受。

## 9.3 覆盖率建议

控制网构建比单纯“匹配上了”要求更高，因此建议至少统计：

- 重叠区网格覆盖率；
- 有效匹配是否集中在局部；
- 是否存在大面积空洞区域。

---

## 10. 输出元数据建议

每个 pair 建议输出一份 JSON sidecar，保存 route 决策依据，便于后续分析与调参。

建议字段包括：

- `left_image_probe`
  - `real_texture_score`
  - `best_render_azimuth`
  - `best_render_elevation`
  - `best_render_score`
  - `terrain_explainability_score`
- `right_image_probe`
  - 同上
- `spice_constraints`
  - `solar_elevation_min`
  - `solar_elevation_max`
  - `real_estimated_elevation_left`
  - `real_estimated_elevation_right`
- `pair_route`
  - `initial_matcher`
  - `fallback_chain`
  - `route_reason`
- `match_quality`
  - `inlier_count`
  - `inlier_ratio`
  - `coverage`
  - `residual_summary`
- `final_decision`
  - `selected_matcher`
  - `accepted`
  - `fallback_used`

---

## 11. 初步实施阶段建议（仅方案，不编码）

## Phase 1：最小可用版本

目标：建立能落地的第一版策略层。

建议范围：

1. 只做 pair 级 route，不做 tile 级 route；
2. 只用 `shadow/Lambertian` probe，不先上 Hapke；
3. 高度角搜索使用 SPICE 约束范围；
4. 最终 matcher 先只支持：
   - `SIFT`
   - `LightGlue`
   - `LoFTR`
5. 回退顺序固定。

## Phase 2：增强版

1. probe 引入多种结构表征（edge / gradient / shadow mask）；
2. 对不同任务（DOM matching / ORI matching）分别学习 route 阈值；
3. 允许有限的 tile 级局部策略增强。

## Phase 3：高级版

1. 在 probe 中引入 Hapke；
2. 基于历史 pair 统计训练 lightweight router；
3. 形成可复用的任务报告与推荐系统。

---

## 12. 主要风险与应对

## 12.1 渲染域差风险

风险：真实图与渲染图差异可能较大。

应对：

- 渲染 probe 仅做相对评分；
- 不将其作为唯一路由依据；
- 联合真实纹理 probe 一起决策。

## 12.2 DEM 分辨率不足

风险：10 m LOLA DEM 无法表达高分辨率真实影像中的细节纹理。

应对：

- 将 render probe 定位为“中低频形貌解释性探测”；
- 不用它直接评价所有细纹理可匹配性；
- 将真实图自身纹理 probe 作为并行主信号。

## 12.3 SPICE 约束过窄

风险：若估计窗口过窄，可能错过真实最优渲染条件附近的探测点。

应对：

- 真实太阳高度角附近保留一小段缓冲；
- 初始版本采用保守的近邻窗口，而不是极限裁剪。

## 12.4 路由规则过早复杂化

风险：一开始就做 tile 级、模型级 route，工程复杂度过高。

应对：

- 第一阶段只做 pair 级决策；
- 待 JSON sidecar 积累足够实验数据后再升级。

---

## 13. 当前结论

本方案认为：

1. “纹理 probe + 光照 probe + matcher 级联回退”的总体方向是正确的；
2. DEM 渲染 probe 对 matcher 选路很有价值；
3. 对第一阶段而言，优先使用 ISIS `shadow` / Lambertian 渲染，而不是直接用 Hapke；
4. SPICE 提前约束太阳高度角搜索范围，是一个非常实用、应该纳入设计的增强点；
5. 初期先做 pair 级策略层最合适，能以较低复杂度获得最大收益。

---

## 14. 建议的后续文档拆分（下一步）

在本初步方案基础上，后续可以继续拆出以下子文档：

1. `pair-probe-design.md`
   - 详细定义 probe 输入/输出与字段
2. `render-probe-design.md`
   - 详细定义 shadow/Lambertian 渲染扫描策略
3. `matcher-routing-rules.md`
   - 详细定义 route 规则与阈值
4. `implementation-phases.md`
   - 逐步落地计划与测试方案

如果进入实现阶段，建议先从：

- probe JSON 结构；
- SPICE 约束太阳高度角窗口；
- pair 级 route 决策；

这三个最小闭环开始。
