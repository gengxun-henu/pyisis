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

### 3.1.1 模块职责与 API 边界

`key_pairs.py` is responsible for reading left/right `.key` files, verifying
matching point counts, validating image dimensions against opened cubes, and
yielding immutable paired point records. It should reuse
`examples.controlnet_construct.keypoints.read_key_file` instead of duplicating
the parser.

`triangulation.py` opens left/right cubes once per run, fetches each camera once,
and iterates over point pairs. For every accepted pair it calls:

```python
left_camera.set_image(left_sample, left_line)
right_camera.set_image(right_sample, right_line)
success, radius_m, latitude_deg, longitude_deg, sepang_deg, error_m = (
    ip.Stereo.elevation(left_camera, right_camera)
)
x_km, y_km, z_km = ip.Stereo.spherical(latitude_deg, longitude_deg, radius_m)
```

It records failures with the point index and operation name instead of aborting
the whole run on the first bad point.

`grid.py` owns projection/grid conversion. For the first implementation, prefer
an existing projected ISIS cube template so the code can call
`template_cube.projection()` and reuse `Projection.set_universal_ground(...)`,
`Projection.world_x()`, and `Projection.world_y()` to map latitude/longitude to
DEM grid cells. Pure PVL-to-projection construction is a follow-up unless the
active conda ISIS pybind surface already exposes a reliable factory.

`cube_writer.py` creates the output cube with explicit dimensions, pixel type,
and Mapping label copied from the template. It writes one line at a time with
`ip.LineManager` and `Cube.write(...)`, using ISIS Null/nodata for empty cells
when the binding exposes a stable special-pixel value; otherwise the design must
require a documented numeric nodata value in summary metadata.

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

现有 `docs/superpowers/specs/2026-05-10-ori-space-direct-controlnet-design.md` 负责：

```text
ORI match -> left_ori.key / right_ori.key -> ControlNet .net
```

本 spec 负责新增并行 DEM 分支：

```text
left_ori.key / right_ori.key -> Stereo.elevation point cloud -> ISIS Cube DEM
```

DEM 生产是 ControlNet 构建的平行分支，不插入 `examples/controlnet_construct/controlnet_stereopair.py`。两者共享 `.key` 点对，但输出产品和验收目标不同。

## 4. 数据流与算法流程

### `.key` pair contract

- Left and right `.key` files use the existing `KeypointFile` format from
  `examples/controlnet_construct/keypoints.py`.
- Point rows are index-synchronized: row `i` in the left file corresponds to row
  `i` in the right file.
- `sample,line` are 1-based ISIS image coordinates and are passed directly to
  `Camera.set_image(sample, line)`.
- The DEM stage never adds or subtracts 1 from `.key` sample/line values.
- A point pair is rejected if either coordinate is outside `1..sample_count` or
  `1..line_count` for its cube.

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

推荐输出 CSV 或 JSONL。每条 triangulated point record 使用以下字段：

```text
index
left_sample
left_line
right_sample
right_line
status
reason
latitude_deg
longitude_deg
radius_m
sepang_deg
intersection_error_m
x_km
y_km
z_km
```

失败或被过滤的记录仍保留输入字段、`status` 和 `reason`。CSV 输出可保留空值；JSONL 输出中数值几何字段可以省略或写为 `null`。

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
failed_set_image_count
failed_elevation_count
filtered_error_count
filtered_sepang_count
filtered_radius_count
rasterized_point_count
filled_cell_count
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

首版 CLI surface 只定义 `from-key` 命令，位置参数顺序固定为：

```text
from-key \
  left_cube \
  right_cube \
  left_key \
  right_key \
  map_template_cube \
  output_dem_cube
```

### 6.3 必需参数

1. `left_cube`
2. `right_cube`
3. `left_key`
4. `right_key`
5. `map_template_cube`
6. `output_dem_cube`

### 6.4 可选参数

1. `--point-cloud-output`
2. `--summary-output`
3. `--quality-prefix`
4. `--max-error-m`
5. `--min-sepang-deg`
6. `--min-radius-m`
7. `--max-radius-m`
8. `--aggregation {median,mean,min-error}`
9. `--nodata-value`
10. `--log-level {DEBUG,INFO,WARNING,ERROR}`

### 6.5 退出行为

The CLI exits non-zero for invalid inputs, unreadable cubes, mismatched `.key`
files, unsupported template projection, or output write failure. Per-point
geometry failures are recorded in point-cloud/summary outputs and do not fail the
whole run unless every point fails before rasterization.

### 6.6 stdout 行为

CLI stdout should print a compact JSON object with status, output paths, and top
level counters. Verbose per-point records belong in `--point-cloud-output`, not
stdout.

## 7. 测试与验收

### 7.1 实现阶段单测目标

新增：

```text
tests/unitTest/dem_extract_unit_test.py
```

该测试文件应覆盖：

1. mismatched left/right `.key` point counts raise `ValueError`;
2. `.key` sample/line are passed directly to a fake camera without `+1`;
3. triangulation keeps cubes and cameras outside the per-point loop;
4. `max_error_m`, `min_sepang_deg`, and radius filters produce stable counters;
5. same-cell aggregation supports `median`, `mean`, and `min-error`;
6. empty cells become the configured nodata value or ISIS Null;
7. CLI `from-key` requires all positional inputs and exposes kebab-case options;
8. compact stdout omits per-point detail records when sidecar paths are used.

### 7.2 聚焦验证命令

实现阶段优先运行以下聚焦验证，均使用 `asp360_new` conda 环境：

```bash
conda run -n asp360_new python -m unittest tests.unitTest.dem_extract_unit_test -v
conda run -n asp360_new python -m unittest tests.unitTest.stereo_unit_test -v
conda run -n asp360_new python -m unittest tests.unitTest.forward_intersection_example_test -v
```

### 7.3 绑定风险检查点

Before implementing Cube DEM writing, verify the active conda binding supports
all required write operations: `Cube.set_dimensions`, `Cube.create`,
`Cube.put_group`, `LineManager`, and `Cube.write(LineManager)`. If Mapping label
copying or special-pixel Null is not exposed, the implementation plan must add a
minimal pybind helper or explicitly use a documented numeric nodata fallback.

### 7.4 人工验收

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
