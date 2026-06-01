# 发现记录：DOM/ORI、太阳角与 ControlNet 读取基准对比

## 已确认代码事实

- 仓库已有 benchmark 框架：`examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.py`。
- 对应单元测试：`tests/unitTest/controlnet_construct_isis_cpp_pyisis_benchmark_unit_test.py`。
- 对应 C++ benchmark：`tools/benchmarks/isis_cpp_benchmark.cpp`。
- 现有 Python config 模型包含：
  - `CameraTaskConfig`
  - `ControlNetTaskConfig`
  - `ExecutionConfig`
  - `BenchmarkConfig`
- 现有 PyISIS camera runner 做的是 `set_image -> universal_latitude/longitude -> set_universal_ground -> sample/line` round-trip。
- 现有 PyISIS controlnet runner 已经分开计量 `load_seconds` 与 `traverse_seconds`，并遍历每个 point 的每个 measure。
- 现有 C++ benchmark 目前支持 `camera` 与 `controlnet` 两种 mode。
- `src/bind_camera.cpp` 已绑定：
  - `set_image`
  - `set_universal_ground`
  - `universal_latitude`
  - `universal_longitude`
  - `sun_azimuth`
  - `north_azimuth`
  - `spacecraft_azimuth`
- `src/bind_sensor.cpp` 也暴露了 incidence/phase/emission/local solar time 等 sensor 方法。
- 现有 lighting 测试中太阳高度角按 `90.0 - IncidenceAngle` 处理，并把字段名标为 `90-IncidenceAngle`。
- `examples/controlnet_construct/dom2ori.py` 已实现 DOM sample/line -> ground -> original sample/line 的业务逻辑，可作为接口语义参考。

## 用户指定 ControlNet 文件

| 用户档位 | 路径 | 本次 `find` 观测大小 |
|---|---|---:|
| 3.8MB | `/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2/old/merge/dom_matching_merged.net` | 3,815,584 bytes |
| 21MB | `/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test/merge/dom_matching_merged.net` | 21,730,222 bytes |
| 82MB | `/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2/disk_lightglue_cnet/merge/ba1_dom_matching_merged.net` | 84,190,068 bytes |

## 用户补充 LRO 影像测试目录

用户指出 `/media/gengxun/Elements/data/lro/test_controlnet_python/PAPER-use` 目录有影像，而且已经过 SPICE 初始化，可以用于测试。

本次检查到该目录包含：

| 类型 | 文件 | 观测大小 |
|---|---|---:|
| 原始影像 | `REDUCED_M104318871RE.echo.cal.cub` | 10,684,524 bytes |
| 原始影像 | `REDUCED_M104318871LE.echo.cal.cub` | 10,686,918 bytes |
| 原始影像 | `REDUCED_M104311715RE.echo.cal.cub` | 10,682,348 bytes |
| 原始影像 | `REDUCED_M104311715LE.echo.cal.cub` | 10,684,742 bytes |
| DOM | `dom_M104318871RE.cub` | 81,828,385 bytes |
| DOM | `dom_M104318871LE.cub` | 79,517,664 bytes |
| DOM | `dom_M104311715RE.cub` | 86,618,529 bytes |
| DOM | `dom_M104311715LE.cub` | 86,618,528 bytes |
| list | `original_images.lis` | 404 bytes |
| list | `doms.lis` | 352 bytes |
| list | `images_overlap.lis` | 1,212 bytes |

`original_images.lis` 与 `doms.lis` 当前内容指向 `/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2/...` 下的同名 cube；已快速确认这些 list 路径存在。`PAPER-use` 下也存在同名 cube，因此 Phase 1 需要确认实际 benchmark 使用 list 路径还是本目录路径，并检查两处文件是否一致。

建议 DOM/ORI 和 solar 100 万点任务先用以下同名 image id 配对：

- `dom_M104311715LE.cub` -> `REDUCED_M104311715LE.echo.cal.cub`
- `dom_M104311715RE.cub` -> `REDUCED_M104311715RE.echo.cal.cub`
- `dom_M104318871LE.cub` -> `REDUCED_M104318871LE.echo.cal.cub`
- `dom_M104318871RE.cub` -> `REDUCED_M104318871RE.echo.cal.cub`

## 可复用验证命令

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_isis_cpp_pyisis_benchmark_unit_test -v
```

Smoke：

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tests/smoke_import.py
```

## 待确认

- DOM/ORI 与 solar 1,000,000 点任务优先使用 `PAPER-use`/`pipe_test2` 同名 cube；仍需确认使用本目录路径还是 list 中 `pipe_test2` 路径。
- 是否需要与外部 ISIS C++ 应用结果对比，还是只需要 repo 内 C++ benchmark executable 与 PyISIS wrapper 对比。
- 大规模任务是否需要保存逐点误差明细；建议默认只保存聚合统计和 top-N。

## 实现与验证发现

- 新增 benchmark config：`examples/controlnet_construct/experiments/isis_cpp_pyisis_benchmark.lro_paper_use.json`，包含 4 个 DOM/ORI 任务、4 个 solar geometry 任务、3 个 ControlNet 任务。
- C++ benchmark 新增 `dom-ori` 和 `solar-geometry` mode；`controlnet` mode 额外输出 `file_size_bytes` 与 `measures_per_second`。
- PyISIS benchmark 新增 `DomOriTaskConfig`、`SolarGeometryTaskConfig`、`generate_regular_grid_samples()`、`run_pyisis_dom_ori_task()`、`run_pyisis_solar_geometry_task()`。
- Python/matplotlib 报告导出 `benchmark_figure.svg`、`benchmark_figure.pdf`、`benchmark_figure.tiff`。
- 真实 10 点 smoke：`dom_M104311715LE.cub` -> `REDUCED_M104311715LE.echo.cal.cub` 的 DOM/ORI 全幅规则网格只有 1/10 点成功投影回原始影像；失败集中在 original projection。这说明完整 1,000,000 点全幅采样会反映大量非重叠/越界点，后续论文图应把 failure rate 作为主要质量字段，或进一步增加 overlap-aware sampling。
- 真实 10 点 solar smoke：C++ 与 PyISIS 均可运行，10/10 成功。
- 真实 3.8MB ControlNet smoke：C++ 与 PyISIS 都读取到 `point_count=17123`、`measure_count=34246`、`file_size_bytes=3815584`，serial counts 一致。

## PLAN 优化：ORI-seeded DOM/ORI round-trip

用户提出 DOM/ORI 坐标转换效率和精度比较应先从 ORI 像素点出发，得到 DOM 上的有效点坐标，再执行 DOM -> ORI 反投影。该设计替代直接在 DOM 全幅规则网格采样作为 Panel A/B 主实验。

建议证据链：

1. 在 original image 上生成 1,000,000 个 ORI seed pixel。
2. ORI `set_image(sample,line)` -> lat/lon。
3. lat/lon -> DOM sample/line，筛掉投影失败或 DOM 越界点。
4. 对保留下来的 DOM sample/line 执行 DOM -> ground -> ORI。
5. 将反投影得到的 ORI sample/line 与原始 ORI seed sample/line 比较。

该方案的好处：

- 减少 direct DOM -> ORI 全幅采样中的非重叠/越界失败，使性能比较更多反映 PyISIS binding 开销而不是数据覆盖差异。
- 精度比较有天然 ground truth：原始 ORI seed 像素。
- 可以同时测试反投影闭环误差，即 ORI -> DOM -> ORI 的 reverse projection accuracy。
- 直接 DOM -> ORI 模式仍有价值，但应定位为覆盖/失败率诊断或压力测试，不作为主精度结论。

建议新增/更新指标：

- `ori_seed_point_count`
- `ori_to_dom_successful_count`
- `ori_to_dom_failed_count`
- `dom_ori_successful_count`
- `dom_ori_failed_count`
- `roundtrip_successful_count`
- `roundtrip_success_rate`
- `ori_to_dom_seconds`
- `dom_to_ori_seconds`
- `core_seconds`
- `roundtrip_points_per_second`
- `sample_abs_max`、`sample_abs_mean`、`sample_rms`
- `line_abs_max`、`line_abs_mean`、`line_rms`
- `pixel_error_abs_max`、`pixel_error_abs_mean`、`pixel_error_rms`
- `top_errors`

建议失败分类：

- `ori_set_image_failed`
- `ori_ground_not_finite`
- `ori_to_dom_projection_failed`
- `dom_point_out_of_bounds`
- `dom_lookup_failed`
- `dom_to_ori_projection_failed`

Figure 影响：

- Panel A：DOM/ORI 效率应展示 ORI-seeded round-trip 总吞吐，并可用 stacked/annotated fields 表示 ORI->DOM 与 DOM->ORI 阶段耗时。
- Panel B：DOM/ORI 精度应展示反投影 ORI 像素误差，而不是直接 DOM 全幅采样产生的成功点误差。
- 直接 DOM 全幅采样结果如保留，应放入补充材料或诊断字段，说明覆盖/重叠失败率。

## ORI-seeded round-trip 实现发现

- `DomOriTaskConfig` 新增 `sampling_mode`，默认 `ori_roundtrip`；显式设置 `direct_dom` 可保留旧 DOM 全幅规则采样诊断模式。
- PyISIS 与 C++ 两端均输出：
  - `ori_seed_point_count`
  - `ori_to_dom_successful_count`
  - `ori_to_dom_failed_count`
  - `dom_ori_successful_count`
  - `dom_ori_failed_count`
  - `roundtrip_successful_count`
  - `roundtrip_success_rate`
  - `ori_to_dom_seconds`
  - `dom_to_ori_seconds`
  - `roundtrip_points_per_second`
  - `pixel_error_abs_max/mean/rms`
- 新增 `precision_comparison.json`，汇总 DOM/ORI 与 solar geometry 的精度字段和 top errors。
- Figure 已改为 A-E 五个 panel：DOM/ORI speed、DOM/ORI precision、solar speed、solar precision、ControlNet traversal。
- 真实 10 点 ORI-seeded round-trip smoke：`dom_M104311715LE -> REDUCED_M104311715LE` 中 C++ 与 PyISIS 均为 8/10 成功、2 个 DOM 越界，`pixel_error_abs_max` 约 `2.5599787472982633e-4` px。

## 完整 Phase 8 benchmark 结果

最终合并报告目录：

`work/isis_cpp_pyisis_benchmark_phase8_final_combined/lro_paper_use_pyisis_cpp_million_points_20260601`

该目录包含：

- `reports/summary.json`
- `reports/summary.csv`
- `reports/precision_comparison.json`
- `reports/controlnet_summary.json`
- `reports/benchmark_figure.svg`
- `reports/benchmark_figure.pdf`
- `reports/benchmark_figure.tiff`

最终合并报告包含 22 条 success 结果：

- DOM/ORI：4 个配对 x PyISIS/C++ = 8 条。
- Solar geometry：4 个影像 x PyISIS/C++ = 8 条。
- ControlNet：3 个文件 x PyISIS/C++ = 6 条。

DOM/ORI 100 万点 round-trip：

- 4 个配对全部完成。
- PyISIS 与 C++ 的成功计数、失败计数、pixel error 聚合统计逐配对一致。
- PyISIS/C++ `core_seconds` ratio 平均值：1.1358588782，范围：1.0933978500 到 1.1668049066。
- PyISIS 平均吞吐：19,615.011 points/s；C++ 平均吞吐：22,285.051 points/s。
- 最大 `pixel_error_abs_max` 约 0.000278015694399 px。

Solar geometry 100 万点：

- 4 个影像全部完成，均 1,000,000/1,000,000 成功。
- PyISIS 与 C++ 的 `azimuth_abs_*` 和 `elevation_abs_*` 均为 0.0。
- PyISIS/C++ `core_seconds` ratio 平均值：1.0345255884，范围：1.0215421510 到 1.0450045234。
- PyISIS 平均吞吐：17,029.909 points/s；C++ 平均吞吐：17,617.257 points/s。

ControlNet 全量遍历：

- 三档文件均完成，PyISIS 与 C++ 的 `file_size_bytes`、`point_count`、`measure_count` 一致。
- 文件规模：
  - 3,815,584 bytes：17,123 points，34,246 measures。
  - 21,730,222 bytes：98,925 points，197,850 measures。
  - 84,190,068 bytes：231,111 points，462,222 measures。
- PyISIS/C++ `core_seconds` ratio 平均值：3.5683314400，范围：2.7584464814 到 4.6352893925。
- PyISIS 平均遍历吞吐：166,745.615 measures/s；C++ 平均遍历吞吐：1,900,492.949 measures/s。

核心论文结论支持：

- DOM/ORI round-trip 与 solar geometry 的数值一致性成立。
- PyISIS binding 的几何计算开销较小：DOM/ORI 平均约 1.14x C++ core time，solar 平均约 1.03x C++ core time。
- ControlNet 遍历的 Python binding/对象访问开销更明显：平均约 3.57x C++ core time，measure 遍历吞吐约为 C++ 的 8.8%。
