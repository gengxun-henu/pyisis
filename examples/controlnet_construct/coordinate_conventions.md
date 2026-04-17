# DOM Matching ControlNet 坐标基准参考

> 本文档是 `requirements_dom_matching_controlnet.md` 中“坐标基准约定（0-based / 1-based 对照）”章节的开发侧展开版。
> 目标是给 `examples/controlnet_construct/` 的维护者一个随手可查的坐标约定说明，减少 +1/-1 回归错误。

## 为什么需要这份文档

这条流程里同时存在三类坐标：

1. **0-based 数组 / 偏移坐标**
   - Python / NumPy / OpenCV 常用
   - 典型范围：`0..width-1`、`0..height-1`
2. **1-based ISIS sample/line 坐标**
   - ISIS 几何接口、`.key` 文件、ControlNet 常用
   - 典型范围：`1..width`、`1..height`
3. **投影 / 地图坐标**
   - 例如 `min_x/max_x/min_y/max_y`
   - 不是像素索引，不能套用 0-based 或 1-based 像素规则

最常见的 bug 就出在这三类坐标被“脑补成同一种东西”。

## 一句话记忆版

- **NumPy/OpenCV tile 坐标**：默认按 **0-based** 理解
- **`.key` / sample / line / ControlMeasure`**：默认按 **1-based** 理解
- **投影范围 / X/Y / GSD**：默认按 **地图坐标** 理解，不谈 0-based / 1-based

## 核心换算公式

### 0-based 局部像素 -> 1-based ISIS 像素

若某个 tile 或 crop 内局部坐标为 `(x, y)`，则对应 ISIS sample/line 为：

- `sample = x + 1`
- `line = y + 1`

### 0-based tile 局部像素 -> 整图 1-based ISIS 像素

若 tile 在整图中的 0-based 起点偏移为 `(start_x, start_y)`，局部点为 `(x_local, y_local)`，则：

- `sample = start_x + x_local + 1`
- `line = start_y + y_local + 1`

### 1-based ISIS 裁剪起点 -> 0-based 偏移

若裁剪窗口左上角在 ISIS 图像空间中的起点为 `(start_sample, start_line)`，则：

- `offset_sample = start_sample - 1`
- `offset_line = start_line - 1`

## 当前实现对照表

| 模块 / 对象 | 代表字段或调用 | 坐标基准 | 说明 |
| --- | --- | --- | --- |
| `tiling.py` | `TileWindow.start_x/start_y` | 0-based | Python 侧 tile 起点偏移 |
| `tiling.py` | `TileWindow.end_x/end_y` | 0-based 半开区间 | 语义更接近数组切片右边界 |
| `image_match.py` | `window.start_x + 1`, `window.start_y + 1` | 0 -> 1 转换 | 写入 `Brick.set_base_position(...)` 前必须 `+1` |
| `image_match.py` | `cv2.KeyPoint.pt` | 0-based 浮点 | OpenCV 在 tile/crop 局部图像中的坐标 |
| `image_match.py` | `_keypoint_to_isis_coordinates()` | 1-based | 输出整图 sample/line，写入 `.key` |
| `dom_prepare.py` | `CropWindow.start_sample/start_line` | 1-based | 裁剪窗口左上角的 ISIS 像素坐标 |
| `dom_prepare.py` | `CropWindow.offset_sample/offset_line` | 0-based | 显式等于 `start_sample - 1` / `start_line - 1` |
| `keypoints.py` | `Keypoint.sample/line` | 1-based | `.key` 交换格式采用的坐标语义 |
| `dom2ori.py` | `_is_point_in_bounds()` | 1-based | 允许 `1..width`、`1..height`，拒绝 0 |
| `dom2ori.py` | `UniversalGroundMap.set_image(sample, line)` | 1-based | 直接消费 `.key` 坐标 |
| `dom2ori.py` | `original_ground_map.sample()/line()` | 1-based | 返回结果继续写回 `.key` |
| `image_overlap.py` | `_linspace_positions()` | 1-based | 采样网格从 `1.0` 到 `max_value`，服务于 `camera.set_image(...)` |
| `controlnet_stereopair.py` | `ControlMeasure.set_coordinate(sample, line)` | 1-based | 直接使用 `.key` 里的 sample/line |
| `dom_prepare.py` | `projected_min_x/max_x/min_y/max_y` | 投影坐标 | 地图坐标，不是数组索引 |

## 维护规则

### 什么时候必须 `+1`

下列场景中，通常必须显式 `+1`：

- 从 `TileWindow.start_x/start_y` 传入 ISIS `Brick` 或相似 sample/line API
- 从 OpenCV / NumPy 的局部坐标写回 `.key`
- 从数组下标恢复到 ISIS sample/line

### 什么时候必须 `-1`

下列场景中，通常必须显式 `-1`：

- 从 ISIS `start_sample/start_line` 恢复 Python 数组偏移
- 把 sample/line 写成 `offset_*` sidecar 字段
- 用 ISIS 起点去构造 `TileWindow.start_x/start_y`

## 容易踩坑的地方

### 1. `.key` 文件不是 NumPy 下标

`.key` 文件中的 `sample,line` 不是 `image[y, x]` 的直接索引值；它们属于 ISIS 图像坐标。

### 2. `width` / `height` 的边界判断是 inclusive

在当前 `dom2ori.py` 中，合法点满足：

- `1.0 <= sample <= width`
- `1.0 <= line <= height`

所以 `sample = width` 是合法边界点，而不是越界。

### 3. 投影坐标不能和 sample/line 混算

`projection.xy_range()`、公共 overlap 范围、扩边距离这些都属于地图/投影空间。只有在回到图像像素空间时，才谈 sample/line 或 offset。

## 回归测试建议

如果后续继续扩展这条流程，优先保留以下测试护栏：

1. tile 局部 keypoint -> 整图 `.key` 的 `+1` 转换测试
2. `CropWindow.start_sample/start_line` 与 `offset_sample/offset_line` 的 `-1` 一致性测试
3. `dom2ori._is_point_in_bounds()` 对 `0` 和 `width/height` 边界的测试
4. `image_overlap._linspace_positions()` 是否从 `1.0` 开始采样的测试

## 调试建议

当你怀疑某段流程存在偏一像素问题时，优先问自己这三个问题：

1. 当前变量是 **数组偏移**、**ISIS sample/line**，还是 **投影坐标**？
2. 这一步是不是刚好跨越了 Python/OpenCV 与 ISIS 的边界？
3. 这里需要的是 `+1`、`-1`，还是根本不该做像素坐标换算？

只要先把这三问问清楚，很多“神秘歪一列/歪一行”都会瞬间失去神秘感。
