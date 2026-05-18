## Plan: Tile Texture and Lighting Routing

在 image_match 下新增两个共享模块：一个负责基于 tile 的纹理稀疏度计算，一个负责立体像对光照差异计算；然后把二者接入现有 `adaptive_routing` / image_match.py 预路由流程。推荐方案是复用现有自适应路由骨架，只替换/扩展纹理评分逻辑，并新增一个显式的光照差异评分模块与诊断输出。首发版本以稳定、可解释、低依赖为主：GLCM 使用仓库内轻量 NumPy/OpenCV 实现，默认 16 灰度级；纹理稀疏度主分数为 `0=丰富, 1=稀疏`，tile 级计算后按每幅图 `P90` 汇总，pair 级取更稀疏的一侧；光照差异先使用 Cube 标签中的太阳高度角与方位角，采用归一化线性加权和；路由策略首发偏保守，只有明显稀疏或明显光照差异大时才优先切到 LoFTR。

**Steps**
1. Phase 1 — 固化模块边界与数据结构。定义两个新模块的职责与返回对象：`texture_sparseness.py` 负责整图归一化、tile 划分、tile 纹理指标、图级汇总、pair 级纹理稀疏度；`lighting_difference.py` 负责从 cube 标签读取太阳高度角/方位角、计算 pair 级光照差异、输出诊断字段。*blocks steps 2-5*
2. Phase 2 — 设计纹理稀疏度 API。新增面向 import 的数据类/字典结构，至少区分：tile 原始指标、tile 纹理稀疏度、图级 `P90` 稀疏度、pair 级弱侧稀疏度、诊断字段（保留现有 entropy / laplacian variance 但不进入主公式）。主语义统一为 `texture sparseness` 而不是 `texture richness`。*depends on 1*
3. Phase 3 — 设计 tile 级纹理特征计算。沿用现有整图统一归一化思路，再切 `256x256`、步长 `128` 的 tile；先基于现有 invalid-mask / special-pixel 逻辑筛掉有效像素比例 `< 0.30` 的 tile；每个有效 tile 计算三项主特征：SIFT 密度、平均梯度幅值、GLCM `contrast` / `energy`。GLCM 默认 16 级灰度量化，优先实现单距离、单方向的轻量版（例如距离 1、方向 0°），接口保留未来扩展多方向平均的余地。*depends on 2*
4. Phase 4 — 设计纹理稀疏度映射公式。先把每个 tile 的三项特征映射到 `[0,1]` 稀疏度子分数，再用线性加权和合成主分数：`SIFT 0.45 + gradient 0.30 + GLCM 0.25`。SIFT 密度先用经验阈值映射；梯度项使用“梯度越弱越稀疏”的单调归一化；GLCM 项使用 `contrast` 越低越稀疏、`energy` 越高越稀疏的组合。图级汇总使用 `P90` 稀疏度；pair 级取 `max(left, right)`。*depends on 3*
5. Phase 5 — 设计光照差异 API 与公式。新增读取/解析 cube 标签太阳几何的 helper，首发只计算 `solar elevation` 与 `solar azimuth`；输出结构既包含原始角度，也包含归一化角度差与最终 `lighting_difference_score`。方位角差必须处理 360° 环绕；主分数使用归一化线性加权和，初始建议方位角权重略高于高度角。接口层预留未来并入 `incidence / emission / phase` 的字段，但首发不纳入主公式。*parallel with step 4 after step 1*
6. Phase 6 — 与现有自适应路由整合。将现有 adaptive_routing.py 中的 `compute_real_image_texture_probe(...)` 逻辑改为调用新纹理模块，或在该文件中增加桥接层，把新模块输出映射进现有 sidecar / route 决策结构；同时把光照差异模块接入 pair-level route 决策，替代或补充当前基于推断照明 gap 的条件分支。保持 image_match.py 的现有 CLI / JSON sidecar 兼容性，避免破坏已有 adaptive-routing 入口。*depends on 4 and 5*
7. Phase 7 — 设计首发保守型路由规则。把 pair 级 `texture_sparseness` 与 `lighting_difference_score` 显式写入决策：低稀疏度且低光照差异优先 SIFT/BF；中间区域走 LightGlue；仅在高稀疏度或高光照差异时优先 LoFTR。首发阈值允许采用经验默认值，并将阈值集中定义为常量或 profile 配置，便于后续样本标定。*depends on 6*
8. Phase 8 — 诊断与 sidecar 扩展。为 pair sidecar 增加新字段：tile 计数、有效 tile 计数、tile 稀疏度分位数、左右图图级稀疏度、pair 弱侧稀疏度、太阳角原值、角度差、最终光照差异分数、命中的路由阈值说明。诊断输出应支持后续调参与论文图表，而不要求首发就暴露单独 CLI。*depends on 6 and 7*
9. Phase 9 — focused tests 与样例验证。新增针对轻量 GLCM、tile 过滤、图级 `P90` 汇总、pair 弱侧聚合、方位角环绕差、标签缺字段错误处理的 focused 单测；再补一个最小集成验证，确保 image_match.py 在开启 adaptive routing 时能够产出新 sidecar 字段且仍能完成 matcher 选择。*depends on 8*

**Relevant files**
- adaptive_routing.py — 现有 `ImageTextureProbe`、`route_matcher_for_pair(...)`、`build_pair_probe_sidecar(...)` 的复用与桥接主入口。
- image_match.py — 现有 `_compute_texture_probe_from_cube_path(...)`、`_resolve_adaptive_route_for_pair(...)` 与 adaptive-routing sidecar 接线点。
- preprocess.py — 复用 invalid-mask / valid-pixel 统计，避免重复实现特殊像素筛选。
- tile_matching.py — 参考现有 tile/window 划分与共享 extent 处理模式，统一 tile 几何风格。
- __init__.py — 如需对外暴露新 helper，可用 lazy export 方式避免循环导入。
- `/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/examples/image_match/texture_sparseness.py` — 新文件；实现 tile 级纹理稀疏度、图级/像对级汇总与诊断输出。
- `/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/examples/image_match/lighting_difference.py` — 新文件；实现太阳角读取、光照差异计算与诊断输出。
- unitTest 下对应 image-match / adaptive-routing 测试文件 — 新增 focused 单测，覆盖 GLCM、tile 汇总、太阳角差与路由阈值。

**Verification**
1. 为 `texture_sparseness.py` 添加 focused 单测：验证无效 tile 跳过、`P90` 汇总、pair 弱侧聚合、SIFT/gradient/GLCM 子分数单调性、16 级量化输出稳定性。
2. 为 `lighting_difference.py` 添加 focused 单测：验证高度角差归一化、方位角 360° 环绕、缺失标签字段时的报错/回退行为。
3. 为 adaptive_routing.py / image_match.py 添加集成级 focused 测试：给定构造的左右图探针与太阳角，断言 SIFT / LightGlue / LoFTR 的首发路由符合保守规则。
4. 运行最小相关单测而不是全量验证，优先使用仓库推荐 Python 环境与 focused test 入口。
5. 如有可用小样本 cube 对，做一次实际 sidecar 验证，确认输出包含左右图纹理诊断、pair 纹理稀疏度、太阳角差、最终光照差异与 route reason。

**Decisions**
- 包含范围：新增两个共享模块、接入现有 adaptive routing、保留 raw metrics 与 sidecar diagnostics、首发直接参与 matcher 选择。
- 明确不包含：tile 级动态 matcher 切换、基于 SPICE/camera 的完整光照几何替代路径、基于数据集统计自动学习权重、首发即引入外部 `scikit-image` 依赖。
- 纹理主分数语义固定为 `0=丰富, 1=稀疏`，避免与现有 `real_texture_score` 的“越大越丰富”语义混淆；桥接时应显式命名或同步重构字段含义。
- GLCM 首发采用仓库内轻量实现，默认 16 灰度级，优先少依赖与可移植性。
- 默认 tile 形状/步长：`256x256` / `128`；有效像素比例阈值：`0.30`；首发路由策略偏保守。

**Further Considerations**
1. 现有 `ImageTextureProbe.real_texture_score` 与新 `texture_sparseness` 语义相反；实施时需要决定是保留旧字段并新增新字段，还是统一改名/重定义。推荐首发保留旧兼容字段，同时新增明确命名的新字段，避免一次性破坏下游。
2. Cube 标签中的太阳角字段名可能存在 mission 差异；实施时应先做字段名适配层或允许显式回退键名列表，避免把标签差异误判成业务失败。
3. 若后续样本表明单方向 GLCM 对地貌方向性过敏，可在不改主 API 的前提下升级为多方向平均（0°/45°/90°/135°）。

## 当前清单

- [x] 已确认纹理主语义、tile 粒度、聚合策略、权重和 GLCM 默认量化级
- [x] 已确认光照差异首发使用太阳高度角与方位角
- [x] 已确认模块放在 image_match
- [x] 已确认首发不引入 `scikit-image`，改走轻量实现
- [x] 已生成正式实施计划并写入 `/memories/session/plan.md`
- [x] 当前轮次无需继续补充阻塞性问题
- [x] 可进入 handoff / implementation 阶段
- [x] 本轮无跳过项
- [x] 本轮无阻塞项
