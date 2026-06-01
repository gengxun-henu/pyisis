# 任务计划：DOM/ORI、太阳角与 ControlNet 读取基准对比

## 目标

在现有 ISIS C++ vs PyISIS benchmark 框架中添加三类大规模对比任务：

1. DOM/ORI 坐标转换效率对比与精度对比，主实验改为 ORI seed -> DOM -> ORI 反投影 round-trip，规模 1,000,000 个 ORI seed 点；直接 DOM -> ORI 全幅采样保留为失败率/覆盖诊断。
2. 根据像素坐标计算太阳方位角、高度角的效率对比与精度对比，规模 1,000,000 个点。
3. ControlNet 读取效率对比，并遍历每一个 measure，覆盖 3.8MB、21MB、82MB 三个真实 `.net` 文件。

## 当前阶段

Phase 8：完整 1,000,000 点 DOM/ORI round-trip、solar geometry 与三档 ControlNet 全量 benchmark 已完成；最终合并报告与 A-E Figure 已生成。

## 输入数据

| 用途 | 路径 | 当前文件大小观察 |
|---|---|---:|
| LRO 测试影像目录 | `/media/gengxun/Elements/data/lro/test_controlnet_python/PAPER-use` | 含 4 个 SPICE 初始化原始影像、4 个 DOM、3 个 list 文件 |
| 原始影像列表 | `/media/gengxun/Elements/data/lro/test_controlnet_python/PAPER-use/original_images.lis` | 4 entries，当前指向 `pipe_test2` 同名 SPICE 初始化 cube |
| DOM 列表 | `/media/gengxun/Elements/data/lro/test_controlnet_python/PAPER-use/doms.lis` | 4 entries，当前指向 `pipe_test2` 同名 DOM cube |
| overlap 列表 | `/media/gengxun/Elements/data/lro/test_controlnet_python/PAPER-use/images_overlap.lis` | 6 原始影像 pair |
| ControlNet 小文件 | `/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2/old/merge/dom_matching_merged.net` | 3,815,584 bytes |
| ControlNet 中文件 | `/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test/merge/dom_matching_merged.net` | 21,730,222 bytes |
| ControlNet 大文件 | `/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2/disk_lightglue_cnet/merge/ba1_dom_matching_merged.net` | 84,190,068 bytes |

## 阶段

### Phase 0：恢复上下文并建立独立计划

- [x] 使用 `planning-with-files`
- [x] 读取根目录现有规划文件，确认其属于 Adaptive Routing 任务
- [x] 创建独立计划目录，避免覆盖根目录规划
- [x] 初步检索 benchmark、DOM/ORI、太阳角、ControlNet 遍历相关代码
- 状态：complete

### Phase 1：调研现有 benchmark 框架与真实 API

- [x] 确认 `examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py` 当前 camera/controlnet task 的输出 schema 与报告格式
- [x] 确认 `tools/benchmarks/isis_cpp_benchmark.cpp` 当前 C++ camera/controlnet 模式，并决定扩展新 mode 且保留旧 mode 兼容
- [x] 确认 PyISIS 侧 DOM projection / original camera 的真实调用链：`UniversalGroundMap(ProjectionFirst)` -> lat/lon -> `UniversalGroundMap(CameraFirst)`
- [x] 确认 C++ 侧 DOM projection / original camera 的等价 ISIS 调用链
- [x] 确认太阳高度角定义：使用 `90.0 - IncidenceAngle()`；太阳方位角使用 `SunAzimuth()`
- [x] 确认 1,000,000 点采样策略：规则网格，浮点 linspace，包含边界，记录失败点统计
- [x] 验证 `PAPER-use` 本目录 cube 与 `original_images.lis`/`doms.lis` 中 `pipe_test2` 路径均存在
- [x] 建立 DOM cube 与 original cube 的配对规则：按 image id 后缀 `M104...LE/RE` 同名配对
- 状态：complete

### Phase 2：扩展配置模型与单元测试

- [x] 在 benchmark JSON schema 中加入 DOM/ORI 转换任务类型
- [x] 在 benchmark JSON schema 中加入 solar geometry 任务类型
- [x] 保留并扩展现有 `controlnet_tasks`
- [x] 为 1,000,000 点支持添加 `point_count`
- [x] 添加/更新 `tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py`
- [x] 覆盖 path resolution、label uniqueness、invalid config、dry-run command generation
- 状态：complete

### Phase 3：实现 PyISIS 侧 DOM/ORI 与太阳角任务

- [x] 添加 DOM/ORI PyISIS runner：DOM `SetImage` -> lat/lon -> ORI `SetUniversalGround` -> original sample/line
- [x] 添加 DOM/ORI 输出：success/failure count、throughput、sample/line stats fields、top errors field
- [x] 添加 solar PyISIS runner：camera `set_image(sample,line)` -> `sun_azimuth()` + `incidence_angle()` -> elevation
- [x] 添加 solar 输出：success/failure count、throughput、azimuth/elevation stats fields、top errors field
- [x] 对 1,000,000 点任务默认不保存全部 point records；通过 `keep_point_records` 配置开启
- 状态：complete

### Phase 3A：实现 PyISIS 侧 ORI-seeded DOM/ORI round-trip 任务

- [x] 添加 ORI seed 采样：在 original image 上生成 1,000,000 个规则网格像素点，作为唯一主实验输入点
- [x] 添加 ORI -> ground -> DOM 投影阶段，保留成功 DOM sample/line，并分别统计 ORI 取地面点失败、DOM 投影失败、DOM 越界等失败类型
- [x] 添加 DOM -> ground -> ORI 反投影阶段，用得到的 DOM sample/line 回投到 original image
- [x] 将反投影 ORI sample/line 与原始 ORI seed sample/line 比较，输出 sample/line/pixel error 聚合统计和 top-N errors
- [x] 输出阶段拆分耗时：`ori_to_dom_seconds`、`dom_to_ori_seconds`、`core_seconds`、`roundtrip_points_per_second`
- [x] 默认不保存所有逐点记录；只保存聚合统计、失败计数、top-N errors，debug 配置才开启完整 records
- 状态：complete

### Phase 4：实现 C++ benchmark 等价任务

- [x] 扩展 `tools/benchmarks/isis_cpp_benchmark.cpp` 参数解析与 mode
- [x] 添加 C++ DOM/ORI runner，与 PyISIS 侧采样顺序和失败分类保持一致
- [x] 添加 C++ solar runner，与 PyISIS 侧角度定义保持一致
- [x] 确保 JSON 输出 schema 与 PyISIS 对齐
- [x] 保留现有 camera/controlnet 行为兼容
- 状态：complete

### Phase 4A：实现 C++ 侧 ORI-seeded DOM/ORI round-trip 任务

- [x] 添加与 PyISIS 完全相同的 ORI seed 规则网格采样
- [x] 添加 C++ ORI -> DOM -> ORI round-trip runner，并与 PyISIS 对齐失败分类、耗时字段和精度字段
- [x] 保留旧 direct DOM -> ORI mode，用于覆盖诊断和回归兼容
- [x] 单元测试覆盖 C++ 命令生成、schema 字段、top-N error 限制和 debug record 开关
- 状态：complete

### Phase 5：ControlNet 三档真实文件读取与遍历

- [x] 在 LRO PAPER-use config 中加入三档真实 `.net` 文件任务
- [x] 确认 C++ 与 PyISIS 侧都把 `ControlNet` 加载时间和遍历时间分开计量
- [x] 遍历每一个 point 和每一个 measure，并读取 serial/sample/line/type/ignored/edit_locked 等字段
- [x] 输出 point_count、measure_count、valid counts、serial_measure_counts、load_seconds、traverse_seconds、core_seconds、file_size_bytes、measures_per_second
- [x] 对真实文件运行前确认路径可读；dry-run/real-run missing path 会报错
- 状态：complete

### Phase 6：报告、示例配置与运行脚本

- [x] 新增 LRO 大规模 benchmark config：`isis_cpp_pyisis_benchmark.lro_paper_use.json`
- [x] 更新 README 使用说明：conda 环境、build、dry-run、full run、输出文件解释
- [x] 汇总报告加入 DOM/ORI、solar、controlnet 三类任务 CSV/JSON 字段
- [x] 明确 1,000,000 点运行建议输出目录
- 状态：complete

### Phase 7：验证

- [x] 运行 focused unit test：`python -m unittest tests.unitTest.controlnet_construct_isis_cpp_pyisis_benchmark_unit_test -v`
- [x] 构建 C++ benchmark：使用 conda compiler 的 CMake build
- [x] 运行 smoke：`python tests/smoke_import.py`
- [x] 先用 dry-run 验证 LRO PAPER-use 输出 schema 与命令生成
- [x] 运行 C++/PyISIS 10 点 DOM/ORI 与 solar 真实数据 smoke
- [x] 运行 3.8MB ControlNet C++/PyISIS 真实数据 smoke
- [x] 运行 C++/PyISIS 10 点 ORI-seeded DOM/ORI round-trip 真实数据 smoke
- [x] 运行完整 1,000,000 点 DOM/ORI 与 solar 真实 benchmark
- [x] 运行三档 ControlNet 真实文件完整 benchmark
- [x] 检查工作树中未触碰 `.gitignore` 或 `print.prt`
- 状态：complete

### Phase 8：按 ORI-seeded round-trip 优化论文实验设计

- [x] 将用户提出的 ORI -> DOM -> ORI 反投影主实验写入计划
- [x] 明确直接 DOM -> ORI 全幅规则采样只作为覆盖/失败率诊断，不再作为 Panel A/B 主精度证据
- [x] 实现 Phase 3A 和 Phase 4A
- [x] 更新 LRO PAPER-use config，让 Panel A/B 默认使用 ORI-seeded round-trip task
- [x] 更新 summary JSON/CSV、camera/DOM comparison JSON 和 Nature-style figure 的 Panel A/B 逻辑
- [x] 重新运行 focused unit、C++ build、smoke import、小样本真实 round-trip smoke
- [x] 再运行完整 1,000,000 点 DOM/ORI round-trip、solar 和三档 ControlNet benchmark
- 状态：complete

### Phase 9：按论文阅读逻辑拆分 Figure

- [x] 使用 Phase 8 最终合并报告作为唯一数据源，不重跑 benchmark
- [x] 生成 ORI->DOM 性能单图，使用 `ori_to_dom_seconds`，不使用 total wall time
- [x] 生成 DOM->ORI 性能单图，使用 `dom_to_ori_seconds`，不使用 total wall time
- [x] 生成 DOM/ORI round-trip 精度单图，误差按 `x10^-3 px` 展示，并保留成功率摘要
- [x] 生成 solar geometry 性能单图，使用 `core_seconds`
- [x] 生成 solar angle 精度单图，区分 azimuth 与 elevation，误差按 `x10^-3 deg` 展示
- [x] 每张图导出 SVG、PDF、TIFF，并额外导出 PNG 用于视觉 QA
- [x] 视觉 QA 检查并修正图例/标签重叠问题
- 状态：complete

## 决策记录

| 决策 | 原因 |
|---|---|
| 使用独立 `.planning/2026-06-01-dom-ori-solar-controlnet-benchmark/` | 根目录规划文件已属于另一个 Adaptive Routing 任务，不能覆盖。 |
| 优先扩展现有 `isis_cpp_pyisis_benchmark` | 仓库已有 C++/PyISIS 对比框架、配置模型、报告输出和单元测试。 |
| 1,000,000 点默认不保存完整逐点记录 | JSON 体积和内存会过大；精度比较可用流式统计与 top-N error 保留代表性误差。 |
| 太阳高度角先按 `90.0 - incidence_angle()` 定义 | 现有测试已使用 `90-IncidenceAngle` 表示 solar elevation。 |
| ControlNet 遍历继续覆盖每一个 measure | 用户明确要求遍历每一个 measure，不能只读取 header/count。 |
| DOM/ORI 主精度实验使用 ORI seed -> DOM -> ORI round-trip | 直接 DOM 全幅采样会包含大量非重叠/越界点；从 ORI 先投到 DOM 能减少无效 DOM 点，并能直接把反投影 ORI 像素与原始 ORI seed 像素比较。 |
| 保留 direct DOM -> ORI mode 作为诊断 | 小样本真实 smoke 显示 direct full-DOM sampling 只有 1/10 成功；该模式适合展示覆盖/失败率，不适合作为主精度 Panel。 |

## 风险与冲突

| 风险/冲突 | 状态 | 处理 |
|---|---|---|
| DOM/ORI 任务需要 DOM cube 与 original cube 成对输入 | mitigated | 用户补充 `PAPER-use` 目录；Phase 1 验证 list 指向的 `pipe_test2` 同名文件与本目录拷贝一致，并按 image id 配对。 |
| 1,000,000 点逐点结果会很大 | open | 使用流式精度统计 + top-N errors；只在 debug 配置中写完整 points。 |
| C++ benchmark 当前只有 `camera` 与 `controlnet` mode | open | Phase 4 扩展 mode，保持旧参数兼容。 |
| 大 ControlNet 文件实际观测约 84.19MB，不是精确 82MB | open | 报告中使用真实 byte size，同时保留用户给出的档位名称。 |
| 工作树已有大量无关 docs 删除/新增 | open | 后续实现和提交只纳入本任务相关文件；不触碰 `.gitignore` 和 `print.prt`。 |
| 直接 DOM 全幅采样的失败率会稀释 PyISIS vs C++ 数值一致性结论 | mitigated | 主实验改为 ORI-seeded round-trip；失败分类仍保留，用于说明覆盖边界而不是绑定精度。 |

## 错误记录

| 错误 | 尝试次数 | 解决 |
|---|---:|---|
| 初始 `rg` 查询包含不存在路径 `isis_pybind` 且输出过大 | 1 | 后续改为针对具体文件和目录读取。 |
