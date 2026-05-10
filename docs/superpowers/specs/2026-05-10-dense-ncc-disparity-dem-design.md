# Dense NCC Disparity DEM 管线设计

## 1. 背景与目标

现有 `examples/dem_extract` 已实现从稀疏 `.key` 点对到 DEM 的最小闭环（`from-key`、`from-ori-match-dem`、`from-dom-match` 三条路径）。本设计在此架构上新增一条**密集逐像素 NCC 匹配**路径：

1. 利用稀疏 KEY 点对拟合视差先验多项式模型
2. 逐像素密集 NCC 匹配生成 3-band float32 视差 CUBE（X/Y 视差 + NCC 相关系数）
3. 从视差 CUBE 反算左右像素坐标，调用 `Stereo.elevation` 前方交会
4. 复用现有 `grid.py` 分箱聚合和 `cube_writer.py` 写出 DEM

现有 `from-key` 等稀疏路径完全保留，不改动。

## 2. 范围与非目标

### 2.1 In Scope

1. 新增 `from-dense-ncc` 子命令，端到端完成：稀疏 KEY 先验 → 密集 NCC → 视差 CUBE → triangulation → DEM
2. 可选 `--save-disparity` 落盘视差 CUBE 供调试
3. 复用现有 `grid.py` 栅格化和 `cube_writer.py` 写出逻辑
4. `KeyPointPair` 浮点化（整数 → int | float），支持子像素坐标
5. 新增 `--use-left-projection` 模式，无需额外 map template

### 2.2 Out of Scope

1. 自适应窗口、LOFTR 初始化等高级匹配策略（设计预留接口，后续实现）
2. 3D 体素内插或规则 3D CUBE 生成
3. DEM 补洞/插值（复用现有保守分箱策略）
4. TIFF/GeoTIFF 输出（由用户自行转换）
5. 多视角立体融合

## 3. 总体架构与数据流

### 3.1 数据流

```
left.cub + right.cub + left.key + right.key
  │
  ├─ ① 稀疏 KEY 拟合视差先验多项式（disparity_model.py）
  │     dx ≈ f(s, l), dy ≈ g(s, l)
  │
  ├─ ② 逐像素密集 NCC 匹配（dense_ncc.py）
  │     左图每个像素 (s, l) → 预测右图搜索中心 → 固定窗口 NCC
  │     → 整像素匹配成功？→ 继续子像素匹配
  │       → 子像素成功？记录子像素 (dx, dy, ncc)
  │       → 子像素失败？记录整像素 (dx, dy, ncc)
  │     → 整像素失败？写 nodata
  │     → 输出：3-band float32 disparity CUBE
  │         band1=dx (sample offset)
  │         band2=dy (line offset)
  │         band3=ncc (NCC correlation coefficient)
  │
  ├─ ③ dense_triangulate_from_disparity()（dense_triangulation.py）
  │     遍历视差 CUBE 有效像素
  │     左相机 set_image(s, l)
  │     右相机 set_image(s+dx, l+dy)
  │     → Stereo.elevation(...)
  │     → TriangulatedPoint 流（复用 FilterOptions）
  │
  ├─ ④ grid.py → rasterize_points() ← 完全复用
  │
  └─ ⑤ cube_writer → write_radius_cube() ← 完全复用
       → output_dem.cub
```

### 3.2 文件布局

```
examples/dem_extract/
  __init__.py          # 新增导出
  key_pairs.py         # 小改：KeyPointPair 浮点化
  triangulation.py     # 零改
  grid.py              # 零改
  cube_writer.py       # 零改
  runtime.py           # 小改：summary 计数器扩展
  isis_stereo_dem.py   # 零改
  dem_pipeline.py      # 改：新增 from-dense-ncc 子命令
  disparity_model.py   # 新增：稀疏 KEY → 视差多项式
  dense_ncc.py         # 新增：逐像素 NCC 密集匹配
  dense_triangulation.py  # 新增：视差 CUBE → TriangulatedPoint 流
```

## 4. 核心算法

### 4.1 稀疏 KEY 视差先验模型（`disparity_model.py`）

```python
@dataclass
class DisparityModel:
    dx_coeffs: np.ndarray  # 多项式系数
    dy_coeffs: np.ndarray
    order: int             # 默认 2（二阶）
    dx_r_squared: float    # 拟合优度
    dy_r_squared: float
```

对每个 KEY 点对计算视差：

```
dx_i = right_sample_i - left_sample_i
dy_i = right_line_i  - left_line_i
```

拟合二阶多项式（6 个系数）：

```
dx ≈ a0 + a1*s + a2*l + a3*s² + a4*s*l + a5*l²
dy ≈ b0 + b1*s + b2*l + b3*s² + b4*s*l + b5*l²
```

**先验不足时的 Fallback：** 如果 KEY 点数量 < `min_key_points`（默认 20），多项式拟合不稳定，回退到均值视差：

```python
dx = mean(dx_i for all pairs)
dy = mean(dy_i for all pairs)
```

在 summary 中记录 `prior_fallback: "mean_disparity"`。

### 4.2 逐像素密集 NCC 匹配（`dense_ncc.py`）

**配置接口：**

```python
@dataclass
class NCCMatchOptions:
    window_size: int = 21           # 匹配窗口大小（奇数）
    search_range: int = 5           # 搜索半径（±N 像素）
    ncc_threshold: float = 0.70     # NCC 相关系数阈值
    enable_subpixel: bool = True    # 是否开启子像素匹配
    enable_gruen: bool = False      # 是否开启 GRUN 细化
    chunk_size_lines: int = 100     # 每次处理的行数（内存控制）
```

**匹配逻辑（逐像素）：**

```
左图像素 (s, l)
  → pred_dx = model.eval_dx(s, l)
  → pred_dy = model.eval_dy(s, l)
  → search_center_s = s + pred_dx
  → search_center_l = l + pred_dy

  → 以 (s, l) 为中心取左图 window_size×window_size 窗口
  → 以 (search_center_s ± search_range, search_center_l ± search_range)
    为搜索区域计算 NCC

  → 整像素匹配成功（ncc >= threshold）？
      → 记录整像素结果 (dx_int, dy_int, ncc_int)
      → enable_subpixel？
          → 在整像素最佳位置周围做子像素细化
          → 子像素成功？→ 记录子像素结果 (dx_sub, dy_sub, ncc_sub)
          → 子像素失败？→ 保留整像素结果
      → enable_subpixel = False？
          → 保留整像素结果
  → 整像素匹配失败？
      → 写 nodata
```

**返回值：**

```python
def dense_ncc_match(
    left_cube, right_cube,
    model: DisparityModel,
    options: NCCMatchOptions,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    返回 (disparity_x, disparity_y, ncc_score) 三个 H×W 的 float32 数组。
    匹配失败的位置填 nodata 值（-9999.0）。
    """
```

**性能策略：** 按块处理（`chunk_size_lines`），每次处理 100 行，避免全图加载到内存。后续可用 `numba` 或 C++ 绑定的 `MaximumCorrelation` 加速。

### 4.3 Dense Triangulation（`dense_triangulation.py`）

```python
def dense_triangulate_from_disparity(
    left_cube, right_cube,
    disparity_x: np.ndarray,  # H×W float32
    disparity_y: np.ndarray,  # H×W float32
    ncc_score: np.ndarray,    # H×W float32
    filters: FilterOptions,
    ncc_threshold: float = 0.70,
    nodata_value: float = -9999.0,
) -> Iterator[TriangulatedPoint]:
    """
    遍历视差有效像素，调用 Stereo.elevation，产出 TriangulatedPoint。
    使用迭代器模式，内存友好。
    """
```

核心逻辑：

```python
for l in range(lines):
    for s in range(samples):
        dx = disparity_x[l, s]
        dy = disparity_y[l, s]
        ncc = ncc_score[l, s]

        if ncc < ncc_threshold or is_nodata(dx, dy, ncc, nodata_value):
            continue

        right_s = s + dx   # 浮点子像素坐标
        right_l = l + dy

        left_camera.set_image(s, l)
        right_camera.set_image(right_s, right_l)

        success, radius, lat, lon, sepang, error = Stereo.elevation(...)

        if not success:
            continue

        if passes_filters(radius, sepang, error, filters):
            yield TriangulatedPoint(
                index=l * samples + s,
                left_sample=s,
                left_line=l,
                right_sample=right_s,
                right_line=right_l,
                radius_m=radius,
                latitude_deg=lat,
                longitude_deg=lon,
                sepang_deg=sepang,
                intersection_error_m=error,
                x_km=..., y_km=..., z_km=...,
                status="success"
            )
```

**`set_image` 浮点坐标兼容性：** 需要验证 ISIS `camera.set_image(sample, line)` 是否接受浮点数。如果不支持，triangulation 阶段取整：`set_image(round(right_s), round(right_l))`。子像素精度在 NCC 阶段已经获得，取整对 triangulation 影响有限。

## 5. DEM 投影策略

### 5.1 两种模式

**模式 A：map template（与现有路径一致）**

```bash
--map-template-cube template.cub
```

从已有投影 cube 读取 projection 和 DEM 网格定义。

**模式 B：复用左图投影（密集匹配新增）**

```bash
--use-left-projection
```

直接用左图像的 projection 作为 DEM 投影。因为密集匹配逐像素处理，DEM 的像素位置和左图一一对应，左图的投影天然定义了规则网格。

两种模式二选一。`dem_pipeline.py` 在参数解析时校验互斥性。

### 5.2 `use-left-projection` 实现

```python
def build_left_projection_grid(template_cube):
    """
    从左图投影构建 GridSpec。
    使用左图的投影将经纬度转换为 world_x/world_y，
    grid 尺寸为左图的 sample_count × line_count。
    """
    samples = template_cube.sample_count()
    lines = template_cube.line_count()
    return GridSpec(samples=samples, lines=lines, nodata_value=-9999.0)
```

## 6. CLI 接口

### 6.1 新增子命令

```bash
python dem_pipeline.py from-dense-ncc \
  left.cub right.cub \
  left.key right.key \
  output_dem.cub \
  [--map-template-cube template.cub | --use-left-projection] \
  [--ncc-window 21] \
  [--ncc-search-range 5] \
  [--ncc-threshold 0.70] \
  [--no-subpixel] \
  [--enable-gruen] \
  [--save-disparity disparity.cub] \
  [--datum-radius-m 3396190] \
  [--aggregation median] \
  [--nodata-value -9999.0] \
  [--point-cloud-output points.csv] \
  [--summary-output summary.json] \
  [--disparity-options config.json]
```

### 6.2 参数说明

**位置参数（5个）：**

| # | 参数 | 说明 |
|---|---|---|
| 1 | `left_cube` | 左图像 cube |
| 2 | `right_cube` | 右图像 cube |
| 3 | `left_key` | 左 KEY 文件（稀疏点对，用于拟合先验） |
| 4 | `right_key` | 右 KEY 文件 |
| 5 | `output_dem_cube` | 输出 DEM cube |

**必需标志（二选一）：**

| 标志 | 说明 |
|---|---|
| `--map-template-cube` | 提供投影模板 cube |
| `--use-left-projection` | 复用左图像的投影 |

**NCC 参数（可选，有默认值）：**

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--ncc-window` | 21 | NCC 窗口大小（奇数） |
| `--ncc-search-range` | 5 | 搜索半径（±N 像素） |
| `--ncc-threshold` | 0.70 | NCC 相关系数阈值 |
| `--no-subpixel` | - | 关闭子像素匹配 |
| `--enable-gruen` | - | 开启 GRUN 细化 |

**辅助选项：**

| 参数 | 说明 |
|---|---|
| `--save-disparity` | 落盘视差 CUBE 到指定路径 |
| `--datum-radius-m` | datum 半径，用于 height_m 模式 |
| `--aggregation` | 分箱聚合方式：median/mean/min-error |
| `--nodata-value` | nodata 值 |
| `--point-cloud-output` | 点云 sidecar 路径 |
| `--summary-output` | summary JSON 路径 |
| `--disparity-options` | 从 JSON 配置读取 NCC 参数 |

## 7. 模块改动清单

### 7.1 改动现有模块

**`key_pairs.py` — KeyPointPair 浮点化**

```python
@dataclass(frozen=True)
class KeyPointPair:
    index: int
    left_sample: int | float
    left_line: int | float
    right_sample: int | float
    right_line: int | float
```

边界校验改为允许浮点坐标：

```python
# 原来：严格整数检查
# 现在：1.0 <= coord <= dim + 0.9999
def _validate_coord(coord: int | float, dim: int) -> bool:
    return 1.0 - 0.0001 <= coord <= dim + 0.0001
```

现有 `.key` 文件读取路径不受影响（传入的仍是整数）。

**`runtime.py` — summary 扩展**

`build_summary` 新增字段：

```python
{
    "pipeline": "from-dense-ncc",
    "total_pixels": ...,
    "matched_subpixel_count": ...,
    "matched_integer_count": ...,
    "failed_match_count": ...,
    "ncc_threshold": ...,
    "polynomial_dx_r_squared": ...,
    "polynomial_dy_r_squared": ...,
    "key_points_used_for_prior": ...,
    "prior_fallback": None | "mean_disparity",
}
```

**`dem_pipeline.py` — 新增子命令入口**

新增 `from-dense-ncc` 解析器和 `run_from_dense_ncc()` 调度函数。

### 7.2 新增模块

**`disparity_model.py`**

```python
@dataclass
class DisparityModel:
    dx_coeffs: np.ndarray
    dy_coeffs: np.ndarray
    order: int
    dx_r_squared: float
    dy_r_squared: float

    def eval_dx(self, s: float, l: float) -> float: ...
    def eval_dy(self, s: float, l: float) -> float: ...

def fit_disparity_model(
    pairs: list[KeyPointPair],
    order: int = 2,
    min_points: int = 20,
) -> DisparityModel: ...
```

**`dense_ncc.py`**

```python
@dataclass
class NCCMatchOptions:
    window_size: int = 21
    search_range: int = 5
    ncc_threshold: float = 0.70
    enable_subpixel: bool = True
    enable_gruen: bool = False
    chunk_size_lines: int = 100

def dense_ncc_match(
    left_cube, right_cube,
    model: DisparityModel,
    options: NCCMatchOptions,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """返回 (disparity_x, disparity_y, ncc_score) 三个 H×W float32 数组。"""

def write_disparity_cube(
    ip, disparity_x, disparity_y, ncc_score, output_path, nodata_value=-9999.0,
) -> None:
    """写出 3-band float32 disparity CUBE，包含 BandBin label。"""

def count_disparity_stats(
    disparity_x, disparity_y, ncc_score, ncc_threshold, nodata_value,
) -> dict:
    """返回 total_pixels, matched_subpixel, matched_integer, failed_match 计数。"""
```

**`dense_triangulation.py`**

```python
def dense_triangulate_from_disparity(
    left_cube, right_cube,
    disparity_x: np.ndarray,
    disparity_y: np.ndarray,
    ncc_score: np.ndarray,
    filters: FilterOptions,
    ncc_threshold: float = 0.70,
    nodata_value: float = -9999.0,
) -> Iterator[TriangulatedPoint]: ...
```

## 8. 错误处理与边界情况

### 8.1 NCC 匹配失败表

| 情况 | 处理 |
|---|---|
| 先验模型预测的搜索中心超出右图范围 | 整像素搜索 → 失败 → nodata |
| 搜索区域内 NCC 最高值 < 阈值 | 整像素搜索 → 失败 → nodata |
| 子像素匹配返回坐标超出图像范围 | 子像素失败，保留整像素结果 |
| 左图像素为 nodata/special pixel | 跳过，直接写 nodata |

### 8.2 资源与内存

- 视差数组 float32：10000×10000 图像 = 3 × 100MB ≈ 300MB
- `dense_triangulate_from_disparity` 使用迭代器，不一次性加载所有点
- NCC 匹配按块处理（`chunk_size_lines=100`），避免全图加载

### 8.3 视差 CUBE 标签

`--save-disparity` 输出包含：

```
Object = Qube
  Group = Dimensions
    Samples = W
    Lines   = H
    Bands   = 3
  EndGroup
  Group = BandBin
    Band 1 = X_Disparity (sample offset)
    Band 2 = Y_Disparity (line offset)
    Band 3 = NCC_Correlation_Coefficient
  EndGroup
  Group = Statistics
    PixelType = Real
    Nodata    = -9999.0
  EndGroup
EndObject
```

## 9. 配置 JSON 扩展

在 `dem_config.example.json` 中新增：

```json
{
  "DenseNCC": {
    "window_size": 21,
    "search_range": 5,
    "ncc_threshold": 0.70,
    "enable_subpixel": true,
    "enable_gruen": false,
    "polynomial_order": 2,
    "min_key_points": 20,
    "chunk_size_lines": 100
  }
}
```

## 10. 测试计划

### 10.1 单元测试

在 `tests/unitTest/dem_extract_unit_test.py` 中新增：

1. `DisparityModel` 多项式拟合 — 已知点集拟合，验证系数和 R²
2. `DisparityModel` fallback — 点数不足时回退到均值
3. `dense_ncc_match` 整像素成功/子像素成功/子像素失败/整像素失败四种情况
4. `dense_triangulate_from_disparity` 迭代器模式 — 验证只产出有效点
5. `dense_triangulate_from_disparity` 过滤 — ncc_threshold 和 FilterOptions
6. `write_disparity_cube` — 验证 3-band float32 结构和 BandBin label
7. `KeyPointPair` 浮点化 — 浮点坐标通过校验
8. `from-dense-ncc` CLI 解析 — 验证互斥标志和参数默认值
9. `use-left-projection` — 从左图构建 GridSpec

### 10.2 集成验证

1. 稀疏 KEY 点拟合多项式，检查 R² 是否合理
2. 视差 CUBE 三波段值分布检查（dx/dy 在预测范围内，ncc >= threshold）
3. DEM 输出与现有 `from-key` 路径在重叠区域的一致性
4. 视差 CUBE 落盘后可用 ISIS 工具查看

## 11. 风险与缓解

| 风险 | 缓解 |
|---|---|
| `camera.set_image` 不接受浮点坐标 | triangulation 时取整，子像素精度在 NCC 阶段已获取 |
| 稀疏 KEY 不足导致先验模型不稳定 | 回退到均值视差，在 summary 中记录 |
| Python 逐像素 NCC 慢 | 按块处理，后续引入 numba 或 C++ MaximumCorrelation |
| 视差 CUBE 内存占用大 | float32 存储 + chunk_size_lines 分块 |
| 密集 triangulation 输出点极多 | 迭代器模式 + 复用 grid.py 分箱聚合，避免内存膨胀 |

## 12. 后续扩展方向

1. 自适应 NCC 窗口大小（基于纹理强度自动调整）
2. LOFTR/SuperPoint 等深度学习模型作为初始视差先验
3. 多视差模型（多项式 → 网格插值混合）
4. GPU 加速 NCC 计算
5. 密集匹配的 3D 体素输出（非 2.5D DEM）
