# ISIS `shadow` / `shade` 与 `gdaldem hillshade` 太阳方位角、高度角定义对比

- Author: GitHub Copilot
- Created: 2026-05-13
- Updated: 2026-05-13
- Purpose: 说明 USGS ISIS `shadow` / `shade` 与 `gdaldem hillshade` 在太阳方位角（azimuth）和太阳高度角 / 天顶角（altitude / zenith）定义上的一致点、差异点和换算关系，避免参数混淆。

## 结论摘要

如果只比较“外部输入参数的定义”：

- **方位角（azimuth）**：ISIS 与 `gdaldem hillshade` **基本一致**。
  - 0° = 北
  - 顺时针增加
  - 东 90°，南 180°，西 270°
- **高度角 / 天顶角**：两者**不一致**。
  - `gdaldem -alt`：0° = 地平线，90° = 头顶
  - ISIS `shade` / `Hillshade` 中使用的 `ZENITH` / `zenith`：0° = 头顶，90° = 地平线

因此：

- `gdaldem` 的 **azimuth 可直接照搬到 ISIS**
- `gdaldem` 的 **altitude 不能直接照搬**，需要转成 ISIS 的 `zenith`

换算关系：

$$
\text{ISIS\_zenith} = 90^\circ - \text{GDAL\_altitude}
$$

反过来：

$$
\text{GDAL\_altitude} = 90^\circ - \text{ISIS\_zenith}
$$

## 方位角：两者为何可以直接对应

### `gdaldem hillshade`

`gdaldem` 文档定义：

- `-az <azimuth>`
- 0° 表示光从栅格上方（通常即北）来
- 90° 表示从东来
- 顺时针增加

也就是常见地图制图定义：

- 北 0°
- 东 90°
- 南 180°
- 西 270°

### ISIS `shade` / `Hillshade`

上游 ISIS 源码与应用 XML 的公开定义一致：

- `reference/upstream_isis/src/base/apps/shade/shade.xml`
- `reference/upstream_isis/src/base/objs/Hillshade/Hillshade.cpp`

对应说明可概括为：

- `AZIMUTH` / `azimuth` 是太阳方向
- 0° = 北（12 点钟方向）
- 顺时针增加

因此外部输入层面：

$$
\text{ISIS\_azimuth} = \text{GDAL\_azimuth}
$$

## 高度角：两者为何不能直接对应

### `gdaldem -alt`

`gdaldem` 的 `-alt` 表示**太阳高度角**：

- 0° = 地平线掠射光
- 90° = 太阳在头顶

这是最常见的地形光照参数定义。

### ISIS `ZENITH` / `zenith`

ISIS 的命名容易让人误会。虽然文档里有时把它写成 solar elevation，但从源码和参数解释看，它实际是：

- 0° = 头顶
- 90° = 地平线

也就是说，ISIS 实际使用的是**从局部法线 / 天顶往下量的角**，即常见意义上的 **zenith angle** 或 **离法线角**。

所以：

- `gdaldem -alt 10`（太阳很低）
  - 对应 ISIS `ZENITH = 80`
- `gdaldem -alt 80`（太阳很高）
  - 对应 ISIS `ZENITH = 10`

## 两个容易混淆的示例

### 示例 1

`gdaldem -az 315 -alt 10`

含义：

- 光从**西北方向**来
- 太阳很低，接近地平线

换到 ISIS：

- `AZIMUTH = 315`
- `ZENITH = 80`

说明：

- 315 没变，是因为 **方位角定义一致**
- 10 变 80，是因为 **altitude 与 zenith 互补**

### 示例 2

`gdaldem -az 135 -alt 80`

含义：

- 光从**东南方向**来
- 太阳很高

换到 ISIS：

- `AZIMUTH = 135`
- `ZENITH = 10`

说明：

- 135 没变，同样因为 **方位角定义一致**
- 80 变 10，是因为 **altitude 与 zenith 互补**

### 为什么一个例子写 315，另一个写 135？

不是换算后“一个变成 315，另一个变成 135”，而是这两个例子**本来就选了两个不同的太阳方位**：

- 315° = 西北光
- 135° = 东南光

这两个方向本来就相差 180°，方向相反。

真正的换算规则只有：

- **azimuth 不变**
- **altitude 变成 `90 - altitude`**

## ISIS 内部实现中的“3 点钟方向”转换

虽然 ISIS 对外公开参数定义与 `gdaldem` 一致，但在内部公式实现时会做一次参考方向转换。

在 `reference/upstream_isis/src/base/objs/Hillshade/Hillshade.cpp` 中，大意为：

- 用户输入 azimuth：0° 在北，顺时针
- 内部算法使用 `azimuthFromThree`
- 即把用户角度转换到：0° 在 3 点钟方向（东），再代入公式

这属于**内部数学坐标变换**，不影响用户输入接口。

因此不要把这一步误解为：

- 用户给 ISIS 的 `AZIMUTH` 要额外改写

用户层面仍然应该直接传：

- 北 0°
- 东 90°
- 南 180°
- 西 270°

## `shadow` 输出日志中的角度，与用户参数定义不完全相同

在 `reference/upstream_isis/src/base/apps/shadow/ShadowFunctor.cpp` 的统计输出中：

- `AverageAzimuth` 注释说明的是：
  - **从 3 点钟方向开始**
  - **顺时针**
- `AverageElevation` 注释说明的是：
  - **从 normal（法线）开始量**
  - **0° = 头顶，90° = 地平线**

因此：

- `shadow` 的统计日志里的 azimuth **不是** `gdaldem -az` 直接同义的那个角
- `shadow` 的统计日志里的 elevation 也**不是** `gdaldem -alt`

如果要与 `gdaldem` 参数对应，需先理解它们是内部统计坐标，而不是直接复用用户参数定义。

## 公式层面的关系

ISIS `Hillshade` 使用的是 Horn (1982) 风格 hillshade 表达式。源码中以局部梯度 $p, q$ 和光源参数 $p_0, q_0$ 表示：

$$
\text{shade} =
\frac{1 + p_0 p + q_0 q}
{\sqrt{1 + p^2 + q^2} \sqrt{1 + p_0^2 + q_0^2}}
$$

其中：

$$
p_0 = -\cos(\alpha) \tan(\theta), \quad q_0 = -\sin(\alpha) \tan(\theta)
$$

这里：

- $\alpha$ 是 ISIS 内部转换后的方位角
- $\theta$ 是 ISIS 使用的 `zenith`（0 顶部，90 地平线）

而 `gdaldem` 常见公式写法更倾向于：

$$
I = \sin(\text{alt})\cos(\text{slope}) +
\cos(\text{alt})\sin(\text{slope})\cos(\text{azimuth} - \text{aspect}')
$$

在角度参考经过一致换算后，两者在**局部照明**意义上是兼容的；真正更大的差异来自下一节的“阴影投射”。

## 为什么 ISIS `shadow` 的结果通常不会和 `gdaldem hillshade` 一模一样

即使角度换算正确，ISIS `shadow` 的结果通常也不会与 `gdaldem hillshade` 常规输出完全一致。原因是：

### `gdaldem hillshade`

通常主要做：

- 基于 DEM 局部坡度 / 坡向
- 计算一个局部明暗值

它更像是**局部 hillshade**。

### ISIS `shadow`

除了 hillshade 外，还会：

- 根据 SPICE / MATCH 影像计算真实太阳位置
- 进行 3D 光线追踪
- 判断某像元是否被地形遮挡
- 可选择把光线追到太阳边缘（`SUNEDGE`）而不是太阳中心

因此 ISIS `shadow` 更接近：

- **带真实投影阴影的天体表面照明渲染**

而不是仅仅做局部坡面明暗。

## 一页对照表

| 概念 | `gdaldem hillshade` | ISIS `shade` / `Hillshade` | 是否一致 |
|---|---|---|---|
| 方位角 0° 基准 | 北 | 北 | 是 |
| 方位角增加方向 | 顺时针 | 顺时针 | 是 |
| 高度角 0° | 地平线 | 头顶 | 否 |
| 高度角 90° | 头顶 | 地平线 | 否 |
| 外部方位角换算 | 不变 | 不变 | 是 |
| 外部高度角换算 | `alt` | `zenith = 90 - alt` | 否 |
| 是否做遮挡阴影 | 常规模式通常不做 | 做 | 否 |

## 实用规则

如果你要把一组 `gdaldem hillshade` 参数转换到 ISIS：

1. **直接保留 azimuth**
2. **把 altitude 改成 `90 - altitude`**
3. 若使用 ISIS `shadow` 而非 `shade`，要额外意识到：
   - `shadow` 的太阳位置通常来自真实几何 / SPICE
   - 输出结果会包含遮挡阴影，不能简单等同于普通 hillshade

## 参考源码 / 文档

- `reference/upstream_isis/src/base/apps/shadow/shadow.cpp`
- `reference/upstream_isis/src/base/apps/shadow/shadow.xml`
- `reference/upstream_isis/src/base/apps/shadow/ShadowFunctor.cpp`
- `reference/upstream_isis/src/base/apps/shade/shade.xml`
- `reference/upstream_isis/src/base/objs/Hillshade/Hillshade.cpp`
- `reference/upstream_isis/src/base/objs/Hillshade/Hillshade.h`
- `https://gdal.org/en/stable/programs/gdaldem.html`
- `https://gdal.org/en/stable/programs/gdal_raster_hillshade.html`
