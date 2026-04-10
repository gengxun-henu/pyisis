User: 这个前方交会程序的代码怎么使用？

GitHub Copilot: 我先快速读一下这个仓库里和 pybind 工作流相关的说明，以及通用安全自治规则，这样后面给你的用法说明会更贴合这个项目，不会“看着像对，其实差半拍”。

Read [](vscode-userdata:/home/gengxun/.config/Code/User/prompts/safe-autonomy.instructions.md)

Read skill [isis-pybind](file:///home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/.github/skills/isis-pybind/SKILL.md?vscodeLinkType%3Dskill)

我再顺手查一下仓库里有没有这个示例的配套数据、相关调用或说明，这样我能把“怎么跑”和“输入该填什么”讲得更接地气一点。

Searched for regex `Stereo\.elevation|forward_intersection|MaximumCorrelation` (`**/*.{py,md,cpp}`), 100 results

Read [](file:///home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/examples)

Read [](file:///home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/tests/data)

我已经定位到一个专门测试这个示例的单元测试和 data 说明；接下来我读这两处，把可直接照抄的调用方式和数据前提整理给你。

Read [](file:///home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/tests/unitTest/forward_intersection_example_test.py)

Read [](file:///home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/tests/data/README.md)

Read [](file:///home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/tests/unitTest/stereo_unit_test.py)

可以，这个 forward_intersection.py 本质上是一个**“两张 ISIS 影像 + 左图已知点 → 自动找右图同名点 → 做前方交会 → 输出三维点”** 的示例程序。

它既可以当**命令行脚本**跑，也可以当**Python 函数**调用。

## 先说它在做什么

这个示例的主流程在 forward_intersection.py 里的 `forward_intersection(...)`：

1. 打开左右两个 cube：`open_cube(...)`
2. 左图给一个已知像点：`left_sample`, `left_line`
3. 如果你**没提供右图初值**，它会先用  
   `estimate_right_point_from_camera_geometry(...)`  
   做一个类似 pointreg 的几何反投影初值
4. 默认再用 `ip.MaximumCorrelation(...)` 做一次 SHIFT 风格的相关匹配，细化右图点
5. 然后对左右相机分别做 `camera.set_image(...)`
6. 最后调用 `ip.Stereo.elevation(left_camera, right_camera)` 做前方交会
7. 输出 JSON 结果

一句话版：**左图给点，右图可自动找点，然后返回三维坐标和交会误差。**

---

## 最直接的用法：命令行运行

在仓库根目录下运行：

```bash
python examples/forward_intersection.py <left_cube> <right_cube> <left_sample> <left_line>
```

比如仓库里的测试数据就有现成样例。对应测试文件 forward_intersection_example_test.py 用的是：

- 左图：EN0108828322M_iof.cub
- 右图：EN0108828327M_iof.cub
- 左图点：`64.0, 512.0`

所以你可以直接这样试：

```bash
python forward_intersection.py \
  EN0108828322M_iof.cub \
  EN0108828327M_iof.cub \
  64.0 \
  512.0
```

这时脚本会：

- 自动加载 `build/python` 下的 `isis_pybind`
- 自动检查 `ISISDATA`
- 如果系统里没配好 leap second kernel，它会尝试回退到  
  `tests/data/isisdata/mockup`

这个小设计挺贴心，属于“能自己兜底一点就兜一点”。

---

## 如果你已经知道右图同名点

你可以跳过 SHIFT 匹配，直接把右图点喂进去：

```bash
python forward_intersection.py \
  EN0108828322M_iof.cub \
  EN0108828327M_iof.cub \
  64.0 \
  512.0 \
  --right-sample 70.5 \
  --right-line 510.2 \
  --no-shift-match
```

这里的规则是：

- **用了 `--no-shift-match`**
- 那就**必须同时提供** `--right-sample` 和 `--right-line`

否则代码会抛 `ValueError`。这在 `forward_intersection(...)` 里写得很明确。

---

## 如果你想让它自动找右图点

这是默认行为，不加 `--no-shift-match` 就行。

```bash
python forward_intersection.py \
  EN0108828322M_iof.cub \
  EN0108828327M_iof.cub \
  64.0 \
  512.0
```

默认参数大概是：

- pattern chip：`31 x 31`
- search chip：`81 x 81`
- tolerance：`0.70`
- 开启 subpixel

你也可以自己调：

```bash
python forward_intersection.py \
  EN0108828322M_iof.cub \
  EN0108828327M_iof.cub \
  64.0 \
  512.0 \
  --pattern-samples 41 \
  --pattern-lines 41 \
  --search-samples 101 \
  --search-lines 101 \
  --tolerance 0.75
```

如果你不想做亚像素匹配，可以加：

```bash
--pixel-only
```

---

## 输出结果怎么看

程序最后会打印一个 JSON，对应数据类 `ForwardIntersectionResult`。

主要字段有：

- `left_cube`, `right_cube`：输入影像
- `left_sample`, `left_line`：左图点
- `right_sample`, `right_line`：右图最终点
- `matched_by_shift`：是否通过 SHIFT/相关匹配得到右图点
- `match_status`：匹配状态，比如 `SuccessPixel` / `SuccessSubPixel`
- `goodness_of_fit`：匹配质量
- `radius_meters`：目标点半径
- `latitude_degrees`, `longitude_degrees`：经纬度
- `separation_angle_degrees`：交会夹角
- `error_meters`：交会误差
- `x_km`, `y_km`, `z_km`：笛卡尔坐标，单位 km

你可以把它理解成：

- `lat/lon/radius` 是球坐标结果
- `x_km/y_km/z_km` 是直角坐标结果
- `error_meters` 越小通常越好
- `separation_angle_degrees` 太小说明几何交会条件可能不太理想

---

## 也可以在 Python 里直接调用

如果你想把它嵌到自己的流程里，可以直接 import：

```python
from examples.forward_intersection import forward_intersection

result = forward_intersection(
    "tests/data/mosrange/EN0108828322M_iof.cub",
    "tests/data/mosrange/EN0108828327M_iof.cub",
    64.0,
    512.0,
)

print(result)
print(result.latitude_degrees, result.longitude_degrees, result.radius_meters)
```

如果你已经有右图初值，也可以传：

```python
result = forward_intersection(
    "left.cub",
    "right.cub",
    64.0,
    512.0,
    right_sample=70.5,
    right_line=510.2,
    use_shift_match=True,
)
```

或者完全不用匹配：

```python
result = forward_intersection(
    "left.cub",
    "right.cub",
    64.0,
    512.0,
    right_sample=70.5,
    right_line=510.2,
    use_shift_match=False,
)
```

---

## 参数怎么选

### 1. 左图点 `left_sample`, `left_line`

这是程序**唯一必须知道的 tie point 起点**。  
要确保这个点：

- 在左图影像范围内
- `left_cube.camera().set_image(sample, line)` 能成功
- 有有效地表交点

否则 `_set_camera_image_or_raise(...)` 会直接报错。

### 2. 右图点初值 `--right-sample`, `--right-line`

可选。

- 不给：先走几何投影估计
- 给了：作为 `MaximumCorrelation` 的搜索中心
- 如果你加了 `--no-shift-match`，那这两个就必须给

### 3. 匹配窗口

- `pattern_*`：模板块大小
- `search_*`：搜索块大小

代码里还做了检查：

- pattern 必须 > 0
- search 必须不小于 pattern

不满足会在 `_build_maximum_correlation_pvl(...)` 里报 `ValueError`。

---

## 一个很实用的建议

如果你第一次跑，建议按这个顺序：

1. **先用仓库自带测试数据**
2. **先用默认参数**
3. 如果匹配失败，再逐步：
   - 提供右图初值
   - 放大 `search_*`
   - 调整 `pattern_*`
   - 略微调整 `--tolerance`

因为相关匹配这东西，有时候不是代码坏了，是影像内容在“礼貌地拒绝合作”。

---

## 常见报错你可以怎么理解

### `set_image(...) failed`

说明你给的像点：

- 不在图像内
- 或对应位置没有有效地表交点

### `SHIFT/MaximumCorrelation matching failed`

说明右图同名点搜索没成功，常见原因：

- 右图初值太偏
- 搜索窗太小
- 图像纹理弱
- 左右图局部差异太大

### `Stereo.elevation(...) returned success=False`

说明即使左右相机都初始化了，最终交会还是失败了。  
这一般更偏几何条件或观测质量问题。

---

## 这个示例在仓库里已经有可参考的“标准答案”

你可以直接看这两个文件来对照理解：

- forward_intersection.py  
  主示例代码
- forward_intersection_example_test.py  
  最小可运行示例，包含已验证的输入数据和参数

其中测试里已经验证：

- 几何初值投影能落到右图内
- 完整前方交会流程能跑通
- 匹配状态应为 `SuccessPixel` 或 `SuccessSubPixel`
- `goodness_of_fit > 0.8`

---

## 你现在最值得直接复制的一条命令

```bash
python examples/forward_intersection.py \
  tests/data/mosrange/EN0108828322M_iof.cub \
  tests/data/mosrange/EN0108828327M_iof.cub \
  64.0 \
  512.0
```

如果这条能跑通，说明：

- `isis_pybind` 导入没问题
- `Stereo.elevation(...)` 绑定可用
- `MaximumCorrelation` 匹配流程可用
- 示例整体链路正常

---

## 完成情况

- [x] 读了仓库里的 pybind 工作流和安全说明
- [x] 读了 forward_intersection.py 的实现逻辑
- [x] 查到了该示例对应的测试文件 forward_intersection_example_test.py
- [x] 提取了仓库内已验证的样例输入数据与参数
- [x] 整理了命令行、Python 调用、参数含义、输出解释和常见报错说明

如果你愿意，我下一步可以直接帮你写一版**“按你自己的两景影像数据来跑”**的具体命令，只要你把左右 `.cub` 路径和一个左图点给我。

python examples/forward_intersection.py \
  /media/gengxun/Elements/data/lro/testdata2/REDUCED_M104311715LE.echo.cal.cub \
  /media/gengxun/Elements/data/lro/testdata2/REDUCED_M104318871LE.echo.cal.cub  \
  129 \
  590

  python examples/forward_intersection.py \
  /media/gengxun/Elements/data/lro/testdata2/REDUCED_M104311715LE.echo.cal.cub \
  /media/gengxun/Elements/data/lro/testdata2/REDUCED_M104318871LE.echo.cal.cub  \
  129 \
  590 \
 --right-sample 125 \
  --right-line 603 \
  --no-shift-match