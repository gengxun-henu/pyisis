# 进度记录：DOM/ORI、太阳角与 ControlNet 读取基准对比

## 会话：2026-06-01

### Phase 0：恢复上下文并建立独立计划

- 开始时间：2026-06-01 Asia/Shanghai
- 状态：complete

已完成：

- 按用户要求使用 `planning-with-files`。
- 读取项目根目录现有 `task_plan.md`、`findings.md`、`progress.md`，确认它们属于 Adaptive Routing ControlNet 执行任务。
- 检索 repo memory，确认本仓库 `.gitignore` 和 `print.prt` 是本地例外；后续不主动修改、删除、提交它们。
- 初步读取 benchmark 相关文件：
  - `examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py`
  - `tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py`
  - `tools/benchmarks/isis_cpp_benchmark.cpp`
  - `examples/controlnet_construct/dom2ori.py`
  - `src/bind_camera.cpp`
  - `tests/unitTest/image_match_lighting_difference_unit_test.py`
- 用 `find` 检查用户指定 ControlNet 文件路径和实际 byte size。
- 创建独立计划文件：
  - `.planning/2026-06-01-dom-ori-solar-controlnet-benchmark/task_plan.md`
  - `.planning/2026-06-01-dom-ori-solar-controlnet-benchmark/findings.md`
  - `.planning/2026-06-01-dom-ori-solar-controlnet-benchmark/progress.md`

### 用户补充：PAPER-use 影像目录

- 时间：2026-06-01 Asia/Shanghai
- 状态：complete

已完成：

- 用户补充 `/media/gengxun/Elements/data/lro/test_controlnet_python/PAPER-use` 有已 SPICE 初始化影像，可用于测试。
- 检查该目录，确认包含 4 个 `REDUCED_M104...echo.cal.cub` 原始影像、4 个 `dom_M104...cub` DOM，以及 `original_images.lis`、`doms.lis`、`images_overlap.lis`。
- 读取三个 list 文件；发现 list 内容指向 `/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2/...` 下同名 cube。
- 快速确认 list 中 `pipe_test2` 路径均存在。
- 更新 `task_plan.md` 输入数据和 Phase 1 待办；更新 `findings.md` 的 LRO 影像数据源记录。

## 测试与验证

| 时间 | 命令 | 结果 | 说明 |
|---|---|---|---|
| 2026-06-01 | `find /media/gengxun/Elements/data/lro/test_controlnet_python/PAPER-use ...` | pass | 确认 PAPER-use 中 cube/list 文件存在。 |
| 2026-06-01 | list 路径存在性检查 | pass | `original_images.lis` 与 `doms.lis` 指向的 `pipe_test2` cube 均存在。 |
| 2026-06-01 | focused unittest RED run | expected fail | 新增测试因缺少 `DomOriTaskConfig`、`SolarGeometryTaskConfig`、regular-grid sampler、summary 新列、C++ file size / throughput 字段失败。 |
| 2026-06-01 | focused unittest GREEN run | pass | 49 tests passed. |
| 2026-06-01 | `cmake --build build --target isis_cpp_benchmark -j$(nproc)` | pass | 首次 sandbox 内失败于 ccache read-only；提升权限后 C++ target 编译/链接成功。 |
| 2026-06-01 | LRO PAPER-use config dry-run | pass | 输出 `/tmp/isis_cpp_pyisis_benchmark_dry_run/lro_paper_use_pyisis_cpp_million_points_20260601`。 |
| 2026-06-01 | C++ 10 点 DOM/ORI smoke | pass | 1/10 成功，9/10 original projection failed；输出 schema 正常。 |
| 2026-06-01 | C++ 10 点 solar smoke | pass | 10/10 成功。 |
| 2026-06-01 | PyISIS 10 点 DOM/ORI smoke | pass | 1/10 成功，9/10 original projection failed；与 C++ 失败模式一致。 |
| 2026-06-01 | PyISIS 10 点 solar smoke | pass | 10/10 成功。 |
| 2026-06-01 | C++/PyISIS 3.8MB ControlNet smoke | pass | 两端均得到 `point_count=17123`、`measure_count=34246`、`file_size_bytes=3815584`。 |
| 2026-06-01 | `python tests/smoke_import.py` | pass | `smoke import ok`。 |
| 2026-06-01 | final focused unittest | pass | 49 tests passed in 2.467s. |
| 2026-06-01 | `git diff --check` on touched files | pass | No whitespace errors reported. |
| 2026-06-01 | `git status --short -- .gitignore print.prt` | pass | No output; neither local exception file was touched. |

### 执行恢复：nature-figure Python + TDD

- 时间：2026-06-01 Asia/Shanghai
- 状态：in_progress

已完成：

- 读取 active plan、`findings.md`、`progress.md`。
- 读取 `nature-figure` manifest、core contract、Python backend fragment；本任务使用 Python/matplotlib 且不使用 R。
- 读取 Superpowers TDD 与 verification-before-completion 规则；后续实现按 test-first 执行。
- 检查 `git status --short`，发现已有大量无关 docs 删除/新增，以及根目录旧规划文件；后续只触碰 benchmark 相关文件和当前 `.planning` 目录。

### PLAN 优化：ORI-seeded DOM/ORI round-trip

- 时间：2026-06-01 Asia/Shanghai
- 状态：complete

已完成：

- 读取 active plan、`findings.md`、`progress.md`，恢复当前 benchmark 设计状态。
- 按用户建议将 DOM/ORI 主实验从 direct DOM full-grid sampling 调整为 ORI seed -> DOM -> ORI round-trip。
- 在 `task_plan.md` 新增 Phase 3A、Phase 4A、Phase 8，明确后续实现 PyISIS/C++ 等价 runner、config/report/figure 更新和验证路线。
- 在 `findings.md` 记录新增证据链、失败分类、性能指标和反投影精度指标。
- 明确 direct DOM -> ORI 全幅采样保留为覆盖/失败率诊断，不再作为论文 Panel A/B 的主精度实验。
- 本次只更新规划文件，未修改实现代码，未运行 benchmark。

### Phase 3A/4A：实现 ORI-seeded DOM/ORI round-trip

- 时间：2026-06-01 Asia/Shanghai
- 状态：complete

已完成：

- 按 TDD 增加 focused unit tests，先验证 RED：缺少 `sampling_mode`、round-trip 输出字段、CSV 列和 C++ 命令参数。
- 实现 `DomOriTaskConfig.sampling_mode`，默认 `ori_roundtrip`，并保留 `direct_dom` 作为旧 direct DOM-grid 诊断模式。
- 实现 PyISIS ORI seed -> DOM -> ORI round-trip runner：
  - ORI seed 规则网格采样。
  - ORI -> DOM 阶段耗时与失败分类。
  - DOM -> ORI 阶段耗时与失败分类。
  - sample/line/pixel error 聚合统计与 top-N errors。
- 实现 C++ benchmark 等价 ORI-seeded round-trip runner，并增加 `--sampling-mode` CLI 参数。
- 更新 LRO PAPER-use config，DOM/ORI 任务显式使用 `sampling_mode: "ori_roundtrip"`。
- 更新报告输出：
  - `summary.csv` 增加 round-trip 成功率、阶段耗时、pixel error 等字段。
  - 新增 `precision_comparison.json`。
  - Nature-style figure 改为 A-E 五个 panel，并继续导出 SVG/PDF/TIFF。
- 更新 README，说明 `ori_roundtrip` 是主实验，`direct_dom` 是覆盖/失败率诊断。

验证：

| 时间 | 命令 | 结果 | 说明 |
|---|---|---|---|
| 2026-06-01 | focused unittest RED | expected fail | 缺少 `sampling_mode`、round-trip schema、summary CSV 字段。 |
| 2026-06-01 | focused unittest GREEN | pass | 50 tests passed in 2.531s。 |
| 2026-06-01 | `cmake --build build --target isis_cpp_benchmark -j$(nproc)` | pass | C++ target 编译/链接成功。 |
| 2026-06-01 | LRO PAPER-use DOM/ORI dry-run | pass | command.sh 包含 `--sampling-mode ori_roundtrip`。 |
| 2026-06-01 | C++ 10 点 ORI-seeded round-trip smoke | pass | 8/10 成功，2 个 DOM 越界，`pixel_error_abs_max ~= 2.56e-4` px。 |
| 2026-06-01 | PyISIS 10 点 ORI-seeded round-trip smoke | pass | 8/10 成功，2 个 DOM 越界，精度统计与 C++ 一致。 |
| 2026-06-01 | final focused unittest | pass | 50 tests passed in 3.965s。 |
| 2026-06-01 | final C++ build | pass | ninja: no work to do。 |
| 2026-06-01 | `python tests/smoke_import.py` | pass | `smoke import ok`。 |
| 2026-06-01 | `git diff --check` on touched files | pass | No whitespace errors reported。 |

### Phase 8：完整 benchmark 执行启动

- 时间：2026-06-01 Asia/Shanghai
- 状态：in_progress

已完成：

- 重新读取 active plan、`task_plan.md`、`findings.md`、`progress.md`。
- 确认当前 active plan 是 `.planning/2026-06-01-dom-ori-solar-controlnet-benchmark/`。
- 检查本任务相关工作树状态；`.gitignore` 和 `print.prt` 未出现在状态输出中，后续仍不触碰。
- 快速验证：
  - `python -m unittest tests.unitTest.controlnet_construct_isis_cpp_pyisis_benchmark_unit_test -v`：pass，50 tests in 6.356s。
  - `cmake --build build --target isis_cpp_benchmark -j$(nproc)`：pass，`ninja: no work to do`。
  - `python tests/smoke_import.py`：pass，`smoke import ok`。

执行策略：

- 因 benchmark runner 会重建同一 `run_id` 目录，分阶段实验将使用不同 `output-root`，避免后续阶段覆盖前一阶段结果。
- 阶段输出计划：
  - 单 DOM/ORI：`work/isis_cpp_pyisis_benchmark_phase8_single_dom`
  - 其余 DOM/ORI：`work/isis_cpp_pyisis_benchmark_phase8_remaining_dom`
  - 全 solar：`work/isis_cpp_pyisis_benchmark_phase8_solar`
  - 全 ControlNet：`work/isis_cpp_pyisis_benchmark_phase8_controlnet`

### Phase 8：单 DOM/ORI 100 万点 benchmark

- 时间：2026-06-01 Asia/Shanghai
- 状态：complete
- 输出目录：`work/isis_cpp_pyisis_benchmark_phase8_single_dom/lro_paper_use_pyisis_cpp_million_points_20260601`
- 运行任务：`dom_ori_M104311715LE`
- wall time：约 104.59 s

输出文件检查：

- `reports/summary.json`：存在
- `reports/summary.csv`：存在
- `reports/precision_comparison.json`：存在
- `reports/controlnet_summary.json`：存在
- `reports/benchmark_figure.svg`：存在
- `reports/benchmark_figure.pdf`：存在
- `reports/benchmark_figure.tiff`：存在

结果摘要：

| implementation | success | roundtrip_successful_count | roundtrip_success_rate | failed_count | core_seconds | points/s | pixel_error_abs_max |
|---|---:|---:|---:|---:|---:|---:|---:|
| PyISIS | yes | 999,990 | 0.99999 | 10 | 49.7296788476 | 20,108.5151397 | 0.000278015694399 |
| C++ | yes | 999,990 | 0.99999 | 10 | 42.7062242040 | 23,415.5563653 | 0.000278015694399 |

说明：

- PyISIS 与 C++ 成功计数、失败计数和 pixel error 聚合统计一致。
- 本阶段已证明单配对 100 万点完整任务可运行；后续按“不重跑已成功阶段”原则，DOM/ORI 全量阶段只运行剩余 3 个配对。

### Phase 8：剩余 DOM/ORI 100 万点 benchmark

- 时间：2026-06-01 Asia/Shanghai
- 状态：complete
- 输出目录：`work/isis_cpp_pyisis_benchmark_phase8_remaining_dom/lro_paper_use_pyisis_cpp_million_points_20260601`
- 运行任务：`dom_ori_M104311715RE`、`dom_ori_M104318871LE`、`dom_ori_M104318871RE`
- wall time：约 324.00 s

输出文件检查：

- `reports/summary.json`：存在
- `reports/summary.csv`：存在
- `reports/precision_comparison.json`：存在
- `reports/controlnet_summary.json`：存在
- `reports/benchmark_figure.svg`：存在
- `reports/benchmark_figure.pdf`：存在
- `reports/benchmark_figure.tiff`：存在

结果摘要：

| label | implementation | roundtrip_successful_count | roundtrip_success_rate | failed_count | core_seconds | points/s | pixel_error_abs_max |
|---|---|---:|---:|---:|---:|---:|---:|
| dom_ori_M104311715RE | PyISIS | 999,998 | 0.999998 | 2 | 51.6353836247 | 19,366.5260099 | 0.000135028401942 |
| dom_ori_M104311715RE | C++ | 999,998 | 0.999998 | 2 | 47.2246983330 | 21,175.3179014 | 0.000135028401942 |
| dom_ori_M104318871LE | PyISIS | 999,996 | 0.999996 | 4 | 51.4280481625 | 19,444.5645077 | 0.000270337085638 |
| dom_ori_M104318871LE | C++ | 999,996 | 0.999996 | 4 | 44.0759615170 | 22,688.0132749 | 0.000270337085638 |
| dom_ori_M104318871RE | PyISIS | 999,998 | 0.999998 | 2 | 51.1758207597 | 19,540.4389252 | 0.000129271733624 |
| dom_ori_M104318871RE | C++ | 999,998 | 0.999998 | 2 | 45.7428094380 | 21,861.3157409 | 0.000129271733624 |

DOM/ORI PyISIS/C++ core_seconds ratio so far:

- `dom_ori_M104311715LE`: 1.1644597427
- `dom_ori_M104311715RE`: 1.0933978500
- `dom_ori_M104318871LE`: 1.1668049066
- `dom_ori_M104318871RE`: 1.1187730135

说明：

- 四个 DOM/ORI 配对均完成 100 万点 ORI-seeded round-trip。
- 每个配对中 PyISIS 与 C++ 的成功计数、失败计数、pixel error 聚合统计一致。

### Phase 8：Solar geometry 100 万点 benchmark

- 时间：2026-06-01 Asia/Shanghai
- 状态：complete
- 输出目录：`work/isis_cpp_pyisis_benchmark_phase8_solar/lro_paper_use_pyisis_cpp_million_points_20260601`
- 运行任务：`solar_M104311715LE`、`solar_M104311715RE`、`solar_M104318871LE`、`solar_M104318871RE`
- wall time：约 470.90 s

输出文件检查：

- `reports/summary.json`：存在
- `reports/summary.csv`：存在
- `reports/precision_comparison.json`：存在
- `reports/controlnet_summary.json`：存在
- `reports/benchmark_figure.svg`：存在
- `reports/benchmark_figure.pdf`：存在
- `reports/benchmark_figure.tiff`：存在

结果摘要：

| label | implementation | successful_point_count | failed_count | core_seconds | points/s | azimuth_abs_max | elevation_abs_max |
|---|---|---:|---:|---:|---:|---:|---:|
| solar_M104311715LE | PyISIS | 1,000,000 | 0 | 59.7151684044 | 16,746.1639433 | 0.0 | 0.0 |
| solar_M104311715LE | C++ | 1,000,000 | 0 | 57.8519271660 | 17,285.5088670 | 0.0 | 0.0 |
| solar_M104311715RE | PyISIS | 1,000,000 | 0 | 59.3597176259 | 16,846.4413241 | 0.0 | 0.0 |
| solar_M104311715RE | C++ | 1,000,000 | 0 | 56.8033116590 | 17,604.6073863 | 0.0 | 0.0 |
| solar_M104318871LE | PyISIS | 1,000,000 | 0 | 58.0566977462 | 17,224.5415055 | 0.0 | 0.0 |
| solar_M104318871LE | C++ | 1,000,000 | 0 | 56.8324054840 | 17,595.5951800 | 0.0 | 0.0 |
| solar_M104318871RE | PyISIS | 1,000,000 | 0 | 57.7951528051 | 17,302.4890750 | 0.0 | 0.0 |
| solar_M104318871RE | C++ | 1,000,000 | 0 | 55.6070912710 | 17,983.3179032 | 0.0 | 0.0 |

Solar PyISIS/C++ core_seconds ratio:

- `solar_M104311715LE`: 1.0322070729
- `solar_M104311715RE`: 1.0450045234
- `solar_M104318871LE`: 1.0215421510
- `solar_M104318871RE`: 1.0393486062

说明：

- 四个 solar geometry 任务均完成 100 万点计算。
- PyISIS 与 C++ 的太阳方位角/高度角误差字段均为 0.0，说明两端数值输出一致。

### Phase 8：ControlNet 全量读取与 measure 遍历 benchmark

- 时间：2026-06-01 Asia/Shanghai
- 状态：complete
- 输出目录：`work/isis_cpp_pyisis_benchmark_phase8_controlnet/lro_paper_use_pyisis_cpp_million_points_20260601`
- 运行任务：`controlnet_3p8mb`、`controlnet_21mb`、`controlnet_82mb`
- wall time：约 23.17 s

输出文件检查：

- `reports/summary.json`：存在
- `reports/summary.csv`：存在
- `reports/precision_comparison.json`：存在
- `reports/controlnet_summary.json`：存在
- `reports/benchmark_figure.svg`：存在
- `reports/benchmark_figure.pdf`：存在
- `reports/benchmark_figure.tiff`：存在

结果摘要：

| label | implementation | file_size_bytes | point_count | measure_count | load_seconds | traverse_seconds | core_seconds | measures/s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| controlnet_3p8mb | PyISIS | 3,815,584 | 17,123 | 34,246 | 0.2515373960 | 0.2393044170 | 0.4908418130 | 143,106.426657 |
| controlnet_3p8mb | C++ | 3,815,584 | 17,123 | 34,246 | 0.1309999250 | 0.0172342950 | 0.1482342200 | 1,987,084.473139 |
| controlnet_21mb | PyISIS | 21,730,222 | 98,925 | 197,850 | 2.2926738090 | 1.1695842610 | 3.4622580700 | 169,162.673095 |
| controlnet_21mb | C++ | 21,730,222 | 98,925 | 197,850 | 0.6537639750 | 0.0931706340 | 0.7469346090 | 2,123,523.169328 |
| controlnet_82mb | PyISIS | 84,190,068 | 231,111 | 462,222 | 4.5461768540 | 2.4590495400 | 7.0052263940 | 187,967.746270 |
| controlnet_82mb | C++ | 84,190,068 | 231,111 | 462,222 | 2.2490084800 | 0.2905464620 | 2.5395549420 | 1,590,871.204620 |

ControlNet PyISIS/C++ ratio:

- `controlnet_3p8mb`: core ratio 3.3112584463，traverse ratio 13.8853615421。
- `controlnet_21mb`: core ratio 4.6352893925，traverse ratio 12.5531426672。
- `controlnet_82mb`: core ratio 2.7584464814，traverse ratio 8.4635328996。

说明：

- 三档 ControlNet 均完成读取和每个 measure 遍历。
- 每档 PyISIS 与 C++ 的 `file_size_bytes`、`point_count`、`measure_count` 一致。

### Phase 8：最终合并报告与 Figure

- 时间：2026-06-01 Asia/Shanghai
- 状态：complete
- 输出目录：`work/isis_cpp_pyisis_benchmark_phase8_final_combined/lro_paper_use_pyisis_cpp_million_points_20260601`

已完成：

- 合并以下分阶段结果：
  - `work/isis_cpp_pyisis_benchmark_phase8_single_dom/lro_paper_use_pyisis_cpp_million_points_20260601`
  - `work/isis_cpp_pyisis_benchmark_phase8_remaining_dom/lro_paper_use_pyisis_cpp_million_points_20260601`
  - `work/isis_cpp_pyisis_benchmark_phase8_solar/lro_paper_use_pyisis_cpp_million_points_20260601`
  - `work/isis_cpp_pyisis_benchmark_phase8_controlnet/lro_paper_use_pyisis_cpp_million_points_20260601`
- 生成最终合并报告，包含 22 条 success 结果。
- 检查最终报告：
  - `reports/summary.json`：存在
  - `reports/summary.csv`：存在
  - `reports/precision_comparison.json`：存在
  - `reports/controlnet_summary.json`：存在
  - `reports/benchmark_figure.svg`：存在
  - `reports/benchmark_figure.pdf`：存在
  - `reports/benchmark_figure.tiff`：存在
- `precision_comparison.json` 行数：
  - DOM/ORI rows：8
  - solar geometry rows：8
- `controlnet_summary.json` rows：6
- `.gitignore` 和 `print.prt` 状态检查：无输出，未触碰。

最终汇总：

| task_type | paired task count | all success | mean PyISIS/C++ core_seconds ratio | mean PyISIS rate | mean C++ rate |
|---|---:|---|---:|---:|---:|
| DOM/ORI round-trip | 4 | yes | 1.1358588782 | 19,615.011 points/s | 22,285.051 points/s |
| Solar geometry | 4 | yes | 1.0345255884 | 17,029.909 points/s | 17,617.257 points/s |
| ControlNet traversal | 3 | yes | 3.5683314400 | 166,745.615 measures/s | 1,900,492.949 measures/s |

结论：

- DOM/ORI round-trip 与 solar geometry 的 PyISIS/C++ 数值统计一致。
- ControlNet 三档文件的 file size、point count、measure count 在 PyISIS/C++ 两端一致。
- Phase 8 剩余完整 benchmark 工作已完成。

### Phase 9：按新要求拆分生成论文图

- 时间：2026-06-01 Asia/Shanghai
- 状态：complete
- 数据源：`work/isis_cpp_pyisis_benchmark_phase8_final_combined/lro_paper_use_pyisis_cpp_million_points_20260601/reports/summary.json`
- 输出目录：`work/isis_cpp_pyisis_benchmark_phase8_final_combined/lro_paper_use_pyisis_cpp_million_points_20260601/reports/split_figures`

已完成：

- 新增 Python/matplotlib 生成脚本：`tools/benchmarks/make_phase8_split_figures.py`
- 按主题拆分生成 5 张图：
  - `fig01_ori_dom_performance`：ORI->DOM projection performance，使用 `ori_to_dom_seconds`
  - `fig02_dom_ori_performance`：DOM->ORI back-projection performance，使用 `dom_to_ori_seconds`
  - `fig03_dom_ori_roundtrip_accuracy`：DOM/ORI round-trip accuracy，误差单位为 `x10^-3 px`
  - `fig04_solar_performance`：solar angle computation performance，使用 `core_seconds`
  - `fig05_solar_angle_accuracy`：solar angle numerical agreement，分开展示 azimuth/elevation，单位为 `x10^-3 deg`
- 每张图均导出：
  - SVG：editable text
  - PDF：vector
  - TIFF：600 dpi
  - PNG：仅用于视觉 QA
- 视觉 QA：
  - 修正 DOM/ORI 精度图中 success rate 与误差柱状图/图例重叠问题
  - 修正性能图中倍率标注与图例过近问题
  - 检查太阳角精度图，azimuth/elevation 已分列展示，当前误差均显示为 `0.000 x10^-3 deg`
- `git diff --check -- tools/benchmarks/make_phase8_split_figures.py`：通过，无输出。
- `.gitignore` 和 `print.prt` 状态检查：无输出，未触碰。

## 错误记录

| 时间 | 错误 | 尝试次数 | 处理 |
|---|---|---:|---|
| 2026-06-01 | 初始 `rg` 查询包含不存在路径 `isis_pybind` 且输出过大 | 1 | 后续改用具体文件读取和更窄检索。 |
| 2026-06-01 | 尝试读取不存在的 `src/bind_cube.cpp` | 1 | 确认 Cube 绑定实际在 `src/bind_low_level_cube_io.cpp`；后续不再读取该路径。 |

## 五问重启测试

| 问题 | 答案 |
|---|---|
| 我在哪里？ | Phase 0 已完成，已建立独立 benchmark 计划。 |
| 我要去哪里？ | Phase 1 调研真实 API 与采样/输出 schema，然后进入配置模型和实现。 |
| 目标是什么？ | 添加 DOM/ORI、太阳角、ControlNet 三类 C++ vs PyISIS 大规模效率/精度 benchmark。 |
| 我学到了什么？ | 见本计划目录的 `findings.md`。 |
| 我做了什么？ | 创建独立 `.planning` 目录并记录任务拆解、代码事实、风险和验证路线。 |
