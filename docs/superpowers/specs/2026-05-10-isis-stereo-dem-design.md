# ISIS Stereo.elevation DEM 管线设计

## 1. 背景与目标

当前 `examples/controlnet_construct` 方向已经覆盖 DOM/ORI 影像匹配、`.key` 点对输出与 ControlNet 构建。新的 DEM 需求是在**不依赖 NASA ASP** 的前提下，复用 ISIS 自身几何能力完成三维前方交会与 DEM 生产：

1. 由 LoFTR / SIFT / SuperPoint / SuperGlue / ISIS `MaximumCorrelation` / ISIS `Gruen` 等匹配链路生成左右影像对应点。
2. 使用 ISIS `Camera.set_image(...)` 初始化左右相机影像点。
3. 使用 `isis_pybind.Stereo.elevation(left_camera, right_camera)` 执行前方交会。
4. 首版可使用用户提供的已投影 ISIS cube 模板定义 DEM 网格；纯 PVL map-template 支持作为后续能力。
5. 输出 ISIS Cube 格式 DEM，由用户根据需要自行将 Cube 转换为 TIFF/GeoTIFF。

首版目标是完成**单对影像 `.key` 点对到 ISIS Cube DEM 的最小闭环**，并保留后续接入 LoFTR + ISIS NCC/Gruen 准稠密匹配的扩展点。

## 2. 范围与非目标

### 2.1 In Scope

1. 新增 `.key` 左右点对读取与逐点前方交会流程。
2. 复用已绑定的 `isis_pybind.Stereo.elevation(...)`、`Cube`、`Camera`。
3. 用户必须显式提供 `map_template`；首版可从已有投影 ISIS cube 模板读取投影，纯 PVL map-template 直接构造作为后续能力。
4. 首版 DEM 输出格式为 ISIS Cube (`.cub`)。
5. 输出点云/质量 sidecar，记录 `latitude`、`longitude`、`radius_m`、`sepang_deg`、`intersection_error_m` 等字段。
6. 支持按 `Stereo.elevation` 的交会误差、交会角等指标过滤坏点。

### 2.2 Out of Scope

1. 首版不调用 NASA ASP，不生成 ASP `D_sub.tif`，不使用 `stereo_tri` / `point2dem`。
2. 首版不直接输出 TIFF/GeoTIFF；如需 TIFF，由用户自行使用 ISIS/GDAL 工具从 `.cub` 转换。
3. 首版不强制实现逐像素 dense matching；先消费已有 `.key` 点对。
4. 首版不把 DEM 逻辑塞入 ControlNet `.net` 构建流程，避免改变既有 `.key -> .net` 语义。
5. 首版不自动推断最佳投影；投影必须来自用户指定的 `map_template`，可先采用已有投影 ISIS cube 模板。
6. 首版不做复杂补洞/插值，只做保守分箱聚合与 nodata 输出。

## 3. 方案概览

### 3.1 选定方案：独立 `examples/dem_extract` 管线

DEM 生产是与 ControlNet 构建并行的独立分支，不应插入 `examples/controlnet_construct/controlnet_stereopair.py`，也不应改变现有 `.key -> .net` 语义。首个包边界定义为：

```text
examples/dem_extract/
  __init__.py
  runtime.py
  key_pairs.py
  triangulation.py
  grid.py
  cube_writer.py
  isis_stereo_dem.py
```

该包只复用两类稳定输入约定：

1. `examples.controlnet_construct.keypoints` 产生/消费的 `.key` 文件结构。
2. `examples/controlnet_construct/coordinate_conventions.md` 记录的 1-based ISIS sample/line 坐标约定。

`examples/dem_extract` 不得反向依赖 ControlNet `.net` 构建逻辑；ControlNet 构建模块也不需要了解 DEM 输出。两条链路共享 `.key` 点对文件，但各自产生不同产品。

### 3.2 全 ISIS 几何 + ISIS Cube 输出分层

DEM 生产拆成四层：

1. **匹配点输入层**
   - 首版读取左右 `.key` 文件。
   - `.key` 文件中的 `sample,line` 语义沿用 `examples/controlnet_construct/coordinate_conventions.md`：1-based ISIS sample/line 坐标。

2. **ISIS 前方交会层**
   - 打开 `left.cub` / `right.cub`。
   - 获取并复用左右 `Camera`。
   - 对每个点对调用 `camera.set_image(...)` 与 `Stereo.elevation(...)`。

3. **投影与栅格化层**
   - 用户通过 `map_template` 传入 DEM 网格/投影来源。
   - `map_template` 首版可以是已有投影 ISIS cube 模板，因为当前 pybind API 可可靠读取 cube projection。
   - 如果当前 pybind API 不能直接从纯 PVL 构造 projection，则纯 PVL map-template 支持作为后续任务。
   - 将交会点的 `latitude, longitude, radius_m` 投入 DEM 网格 cell。

4. **ISIS Cube 输出层**
   - 输出 DEM `.cub`。
   - 推荐同步输出质量 cube 或 sidecar：交会误差、每像元点数、交会角统计。
   - TIFF/GeoTIFF 转换由用户自行执行。

### 3.3 与现有 ORI ControlNet 计划的关系

现有 `docs/superpowers/plans/2026-05-10-ori-space-direct-controlnet.md` 负责：

```text
ORI match -> left_ori.key / right_ori.key -> ControlNet .net
```

本 spec 负责新增并行 DEM 分支：

```text
left_ori.key / right_ori.key -> Stereo.elevation point cloud -> ISIS Cube DEM
```

DEM 生产是 ControlNet 构建的平行分支，不插入 `examples/controlnet_construct/controlnet_stereopair.py`。两者共享 `.key` 点对，但输出产品和验收目标不同。

## 4. 数据流与算法流程

### 4.1 首版 `.key -> ISIS Cube DEM` 主链路

1. 读取输入：
   - `left_cube`
   - `right_cube`
   - `left_key`
   - `right_key`
   - `map_template.cub`（首版可为已有投影 ISIS cube 模板）
   - `output_dem.cub`

2. 校验 `.key`：
   - 左右点数必须一致。
   - 点索引一一对应，不允许单侧丢点后继续错位处理。
   - 坐标必须在对应 cube 图像范围内。

3. 批量前方交会：
   - 打开两个 cube，获取左右 camera。
   - 对第 `i` 个点对：
     - `left_camera.set_image(left_sample, left_line)`
     - `right_camera.set_image(right_sample, right_line)`
     - `Stereo.elevation(left_camera, right_camera)`
   - 保存成功点的 `radius_m`、`latitude_deg`、`longitude_deg`、`sepang_deg`、`intersection_error_m`。

4. 质量过滤：
   - `intersection_error_m <= max_error_m`，可选。
   - `sepang_deg >= min_sepang_deg`，可选。
   - `radius_m` 在用户指定或自动统计的合理范围内，可选。
   - 任意相机 `set_image` 失败或 `Stereo.elevation` 失败时跳过该点并计入 summary。

5. 投影与分箱：
   - 使用用户指定 `map_template` 定义 DEM 网格；首版可读取已有投影 ISIS cube 模板的 projection。
   - 纯 PVL map-template 支持作为后续能力，前提是可由当前 pybind API 可靠构造 projection。
   - 将 `latitude_deg, longitude_deg` 转换到输出 DEM 的投影坐标/行列位置。
   - 同一 cell 内多个点默认使用 `median(radius_m)` 聚合。
   - 没有点落入的 cell 写 ISIS Null / nodata。

6. 输出：
   - `output_dem.cub`：主 DEM，首版像元值为 `radius_m`。
   - 可选 `output_error.cub`：每像元交会误差统计，例如 median error。
   - 可选 `output_count.cub`：每像元有效点数量。
   - 可选 `output_sepang.cub`：每像元交会角统计。
   - JSON summary 与可选 CSV/JSONL 点云 sidecar。

### 4.2 后续 LoFTR + ISIS NCC/Gruen 准稠密链路

首版稳定后，可新增：

```text
LoFTR 初始对应 / flow prior
  -> ISIS MaximumCorrelation 小窗口 NCC refinement
  -> ISIS Gruen 亚像素/仿射 refinement
  -> refined .key-like 点对
  -> Stereo.elevation
  -> ISIS Cube DEM
```

该增强应先支持 `stride=16/8/4` 规则网格，再考虑 `stride=1` 逐像素。

## 5. 输出数据定义

### 5.1 主 DEM Cube

首版主输出为 ISIS Cube：

```text
output_dem.cub
```

默认像元语义：

```text
value = radius_m
```

其中 `radius_m` 是 `Stereo.elevation(...)` 返回的目标体中心到交会点距离，单位为米。

后续可扩展：

```text
value = height_m = radius_m - datum_radius_m
```

但首版不默认启用 datum 高程，避免未明确参考面时产生歧义。

### 5.2 点云 sidecar

推荐输出 CSV 或 JSONL，字段至少包含：

```text
index
left_sample
left_line
right_sample
right_line
latitude_deg
longitude_deg
radius_m
sepang_deg
intersection_error_m
status
reason
```

如果上游匹配阶段提供分数，可追加：

```text
matcher_method
match_score
refinement_method
goodness_of_fit
```

### 5.3 Summary JSON

Summary 至少包含：

```text
input_left_cube
input_right_cube
input_left_key
input_right_key
map_template
output_dem_cube
input_point_count
success_count
filtered_count
failure_counts
max_error_m
min_sepang_deg
aggregation
value_type
```

## 6. CLI 与配置设计

### 6.1 建议新增脚本

新增：

```text
examples/dem_extract/isis_stereo_dem.py
```

### 6.2 建议子命令

首版新增 `from-key`：

```text
python examples/dem_extract/isis_stereo_dem.py from-key \
  left.cub \
  right.cub \
  left_ori.key \
  right_ori.key \
  map_template.cub \
  output_dem.cub \
  --point-cloud-output output_points.jsonl \
  --summary-output output_summary.json \
  --max-error-m 10 \
  --min-sepang-deg 1 \
  --aggregation median
```

### 6.3 必需参数

1. `left_cube`
2. `right_cube`
3. `left_key`
4. `right_key`
5. `map_template`
6. `output_dem_cube`

### 6.4 可选参数

1. `--point-cloud-output`
2. `--summary-output`
3. `--quality-prefix`
4. `--max-error-m`
5. `--min-sepang-deg`
6. `--min-radius-m` / `--max-radius-m`
7. `--aggregation {median,mean,min-error}`
8. `--value-type {radius-m,height-m}`，首版可只支持 `radius-m`
9. `--datum-radius-m`，仅当后续启用 `height-m` 时使用

## 7. 测试与验收

### 7.1 单测建议

新增：

```text
tests/unitTest/dem_extract_isis_dem_unit_test.py
```

覆盖：

1. 左右 `.key` 点数不一致时报错。
2. `.key` sample/line 直接作为 1-based ISIS 坐标，不额外 `+1`。
3. `Stereo.elevation` 结果记录结构字段完整。
4. `max_error_m` / `min_sepang_deg` 过滤逻辑。
5. 同一 DEM cell 内多点 `median` 聚合。
6. 空 cell 写 Null/nodata。
7. CLI 解析必须要求 `map_template` 与 `output_dem_cube`。

### 7.2 回归测试

1. 运行 `tests/unitTest/stereo_unit_test.py`，确认 `Stereo` 绑定不回归。
2. 运行 `examples/controlnet_construct` 现有 `.key/.net` 相关测试，确认新增 DEM 模块不改变 ControlNet 行为。
3. 使用一个小型 `.key` fixture 验证 `.key -> point cloud -> summary` 成功。
4. 使用用户指定的已有投影 ISIS cube 模板验证可生成 `.cub` DEM；纯 PVL map-template 验证留到后续能力实现。

### 7.3 人工验收

1. 抽查若干 `.key` 点，确认其 sample/line 直接进入 `camera.set_image(...)`。
2. 检查点云中的 `radius_m` 是否处于目标体合理半径范围。
3. 检查 `intersection_error_m` 分布，确认过滤阈值有效。
4. 在 ISIS 工具中打开输出 DEM cube，确认 Mapping label 和像元值语义正确。
5. 如需 TIFF，由用户自行执行 ISIS/GDAL 转换，并验证转换后地理参考未丢失。

## 8. 风险与缓解

1. **风险：sample/line 坐标偏一像素。**  
   **缓解：** `.key` 明确为 1-based ISIS 坐标；从 OpenCV/NumPy 坐标写 `.key` 的转换只发生在匹配阶段，DEM 阶段不再额外 `+1`。

2. **风险：`Stereo.elevation` 只做单点交会，批量处理较慢。**  
   **缓解：** 首版从 `.key` 稀疏/半稠密点开始；dense 阶段再引入 tile、stride 和并行。

3. **风险：投影自动推断导致输出不符合用户期望。**  
   **缓解：** 首版强制用户提供 `map_template`，可先使用已有投影 ISIS cube 模板，不自动猜测；纯 PVL map-template 支持作为后续能力。

4. **风险：DEM 像元值 radius 与 height 混淆。**  
   **缓解：** 首版默认且明确输出 `radius_m`；summary 和 cube label/说明中记录 `value_type=radius_m`。

5. **风险：坏匹配污染 DEM。**  
   **缓解：** 使用 `intersection_error_m`、`sepang_deg`、可选匹配分数过滤，并输出质量 cube/sidecar。

6. **风险：ISIS Cube 写出 API 在 pybind 中能力不足。**  
   **缓解：** 实现阶段优先验证当前 `isis_pybind` Cube/Brick/ProcessExport 写能力；若 Python 绑定不足，新增最小 C++ pybind helper 或采用 ISIS CLI 中间流程，但仍保持最终 DEM 为 ISIS Cube。

## 9. 与 TIFF 转换的边界

本 spec 不把 TIFF/GeoTIFF 作为首版输出目标。标准交付物是：

```text
output_dem.cub
```

如果用户需要 TIFF/GeoTIFF，可自行使用 ISIS 或 GDAL 工具转换，例如按本地 ISIS 环境可用工具选择 `isis2std`、`isis2gdal` 或 GDAL 转换命令。该转换属于 DEM 产品发布/交换格式步骤，不属于首版前方交会与 DEM 生成核心链路。

## 10. 后续扩展方向

1. 支持 `from-ori-match-dem`：直接串联 ORI 匹配、`.key` 输出和 DEM cube 生成。
2. 支持 LoFTR seeded `MaximumCorrelation` / `Gruen` 准稠密 refinement。
3. 支持 `height_m` 输出与用户指定 datum/椭球参考面。
4. 支持多质量 band 或多 cube 输出：radius/error/count/sepang。
5. 支持批量 stereo pair DEM 生成与 mosaic/merge。