# DOM Matching ControlNet 正式需求说明

> 本文件是对 `examples/controlnet_construct/requirements_dom_matching_controlnet-draft.md` 的结构化与细化版本。
> `requirements_dom_matching_controlnet-draft.md` 保留为原始需求记录，不做修改；本文件用于后续代码实现、测试设计与架构拆分。

## 目标

实现一个基于 **CUBE 格式正射影像（DOM）进行 SIFT 匹配**、并进一步建立 **ISIS ControlNet** 的示例流程。该流程面向“由原始影像生成 DOM，再把 DOM 上的匹配点回投到原始影像空间”的工作链路，而不是直接在原始影像上做传统相关匹配。

最终目标是：

1. 从原始影像列表中计算重叠立体像对；
2. 在正式匹配前完成 DOM GSD 检查、必要的重采样，以及基于投影坐标的公共范围裁剪；
3. 在公共 DOM 范围上执行 SIFT 匹配；
4. 将 DOM 匹配点转换回原始影像像素坐标；
5. 生成单个立体像对的 ISIS 控制网文件；
6. 自动生成后续把多个立体像对控制网合并成整体控制网的 `cnetmerge` shell 脚本；
7. 为 per-pair 与 batch 统计结果提供稳定 JSON 报告输出，便于回归比较；
8. 全流程以可拆分、可测试、可逐步实现的方式组织。

### ControlPoint 命名空间与批处理约束

1. 单个立体像对输出的 `ControlPoint` ID 默认仍可采用 `PointIdPrefix + 8 位序号` 的兼容格式；
2. 当多个立体像对的 pairwise `.net` 需要再通过 `cnetmerge` 合并时，必须为不同立体像对提供彼此独立的 point-id 命名空间，避免不同 pair 上的 `P00000001` 被误视为同一个控制点；
3. `controlnet_stereopair.py` 的配置应支持可选 `PairId`（或等价字段）用于单 pair 场景，例如生成 `P_S1_00000001`；
4. 当采用 batch 入口批量处理 `images_overlap.lis` 时，应由程序自动为每个立体像对分配 `S1`、`S2`、`S3` 这类短 ID，而不要求用户手工逐对传入 `--pair-id`；
5. 自动分配的 pair ID 必须写入 per-pair JSON sidecar 或等价输出摘要，以便后续排查 `cnetmerge` 输入来源。

## 前提与约束

### DOM 与原始影像的一致性约束

1. `doms.lis` 中的每一景 DOM 必须由 `original_images.lis` 中对应的原始影像正射纠正得到；
2. DOM 正射纠正时所使用的参考 DEM，必须来自对应原始影像在 `spiceinit` 中关联的 `shapemodel`；
3. 在本流程执行期间，**不允许更换该 shapemodel**。若 DOM 生成时依赖的 shapemodel 与当前环境不一致，应视为输入不合法并中止或报错；
4. 正式实现中需要保留针对该前提的检查入口，即使首版只能先做配置级校验或日志提示，也必须在接口设计中体现该约束。

### 技术栈约束

- Python 环境：`asp360_new` conda 环境中的 Python 3.12；
- 特征匹配：OpenCV 提供的 SIFT；
- ISIS 相关处理：使用 `isis_pybind` 完成坐标转换、ControlNet 生成等工作；
- DOM GSD 不一致时允许调用 `gdal_translate` 做自动重采样；
- 当前主流程 **明确采用 SIFT**，不以 `MaximumCorrelation` 或其它相关匹配算法作为本需求的主匹配路径。

## 输入与输出

### 输入

1. `original_images.lis`
	- 内容为 CUBE 格式原始影像路径列表；
	- 一行一个文件名；
	- 文件名以相对路径存储。

2. `doms.lis`
	- 内容为 CUBE 格式正射影像路径列表；
	- 一行一个文件名；
	- 文件名以相对路径存储；
	- 与 `original_images.lis` 保持一一对应关系。

		- `Moon`
		- `Mars`
		- `Earth`
		- `Ryugu`
		- `Bennu`
	5. 设计上允许继续扩充到 ISIS 支持的其他目标体；
	6. 控制点编号、来源立体像对信息、写盘格式等应具备可追踪性；
	7. 应支持可选 JSON sidecar 报告输出；
	8. 若启用 sidecar 输出，推荐默认文件名与输出 `.net` 同名主干、扩展名为 `.summary.json`；
	9. per-pair JSON 至少应包含以下字段：
		- `pair`：立体像对标识，推荐格式 `A,B`；
		- `match.point_count` 或等价字段：DOM 匹配点数；
		- `merge.unique_count` 或等价字段：DOM 去重点数；
		- `left_conversion.output_count`：左像 dom2ori 保留点数；
		- `right_conversion.output_count`：右像 dom2ori 保留点数；
		- `controlnet.point_count`：最终 control point 数；
		- `dom2ori_retention_rate`：若直接写出该字段，应明确定义为保留点数相对于 merge 点数的比值；
		- `report_path`：若运行时自动落盘，应返回实际写出的报告路径。
	- 每行格式为 `相对路径<TAB>GSD`；
	- GSD 单位为 `m/pixel`。

3. `doms_scaled.lis`
	- 当 DOM GSD 超出允许差异时生成；
	- 后续实际匹配应优先使用该列表，而不是原始 `doms.lis`。

4. DOM 裁剪 sidecar 元数据
	- 记录每个立体像对左右 DOM 的裁剪窗口、相对原图偏移、投影公共范围、外扩像素数，以及是否因图像边界发生截断；
	- 推荐使用 JSON。

5. DOM 空间连接点文件
	- 由 `image_match.py` 输出为 `.key` 文件；
	- 对于立体像对 `A__B`，文件名格式为：
	  - `A__B_A.key`
	  - `A__B_B.key`

6. 原始影像空间连接点文件
	- 由 `dom2ori.py` 生成；
	- 内容为回投到原始影像空间后的像素坐标。

7. ISIS 控制网文件
	- 由 `controlnet_stereopair.py` 生成；
	- 支持 PVL 或二进制格式。

8. 全局控制网合并脚本
	- 根据 `image_overlap.lis` 中实际产出的 pairwise `.net` 自动生成；
	- 使用 ISIS `cnetmerge` 工具，将多个立体像对控制网合并为一个整体控制网。

9. 日志与统计结果
	- 记录匹配成功数、失败数、失败原因、被跳过的子块、去重前后点数等。

10. per-pair JSON 报告与 batch summary JSON
	- 为便于自动回归比较，流程应支持把单个立体像对的统计结果落盘为固定命名 JSON sidecar；
	- 在 batch 级别应支持从多个 per-pair JSON 报告聚合出一个固定命名的 batch summary 总表；
	- 推荐命名约定：
	  - pairwise `.net` 为 `A__B.net` 时，其 sidecar JSON 为 `A__B.summary.json`；
	  - batch summary JSON 固定命名为 `controlnet_batch_summary.json`；
	- JSON 编码统一使用 UTF-8，推荐使用 pretty-print 形式以便版本比较与人工审查。

## 总体处理流程

完整流程分为 8 个程序步骤：

1. `image_overlap.py`
2. `dom_prepare.py`
3. `image_match.py`
4. `tie_point_merge_in_overlap.py`
5. `keypoints_io.py`
6. `dom2ori.py`
7. `controlnet_stereopair.py`
8. `controlnet_merge.py`

这些程序对外表现为 CLI 工具；内部实现允许共享公共模块，但不能改变该工作流的外部逻辑含义。

## 坐标基准约定（0-based / 1-based 对照）

更适合开发时随手查阅的独立版本见：`examples/controlnet_construct/coordinate_conventions.md`。

为避免 DOM 裁剪、分块匹配、`.key` 写盘、`dom2ori` 几何回投、以及 ControlNet 写入阶段发生坐标基准混淆，本流程明确区分以下三类坐标：

1. **0-based 数组 / 窗口偏移坐标**
	- 主要用于 Python / NumPy / OpenCV 图像数组访问，以及分块窗口起点偏移；
	- 典型范围为 `0..width-1`、`0..height-1`；
	- `TileWindow.start_x/start_y`、裁剪 sidecar 中的 `offset_sample/offset_line` 属于此类。

2. **1-based ISIS 像素坐标（sample/line）**
	- 主要用于 ISIS 几何接口、`.key` 文件、`dom2ori.py` 输入输出、ControlMeasure 写入；
	- 典型范围为 `1..width`、`1..height`；
	- `camera.set_image(sample, line)`、`UniversalGroundMap.set_image(sample, line)`、`ControlMeasure.set_coordinate(sample, line)` 均按此约定工作。

3. **投影坐标 / 地图坐标**
	- 例如 `min_x/max_x/min_y/max_y`、公共投影范围、GSD 对应的地图单位；
	- 这类值不是像素索引，因此不应套用 0-based / 1-based 规则；
	- 只有在回到图像空间时，才需要再转换为 sample/line 或数组偏移。

### 统一换算规则

- 若某点在 NumPy / OpenCV / tile 局部数组中的横纵坐标为 `(x, y)`，则对应 ISIS 像素坐标为：
	- `sample = x + 1`
	- `line = y + 1`
- 若某裁剪窗口左上角的 ISIS 坐标为 `(start_sample, start_line)`，则其 0-based 偏移为：
	- `offset_sample = start_sample - 1`
	- `offset_line = start_line - 1`
- 若某 tile 内部的 OpenCV 特征点局部坐标为 `(x_local, y_local)`，tile 在整图中的 0-based 起点为 `(start_x, start_y)`，则整图 ISIS 坐标应为：
	- `sample = start_x + x_local + 1`
	- `line = start_y + y_local + 1`

### 当前实现中的坐标基准对照表

| 模块 / 数据对象 | 坐标字段 | 基准 | 说明 |
| --- | --- | --- | --- |
| `tiling.py` `TileWindow.start_x/start_y` | tile 起点 | 0-based | 用于 Python 侧窗口偏移；`end_x/end_y` 为半开区间右边界风格，即 `start + size`。 |
| `image_match.py` `_read_cube_window()` | `window.start_x + 1`, `window.start_y + 1` | 从 0-based 转 1-based | 传给 `Brick.set_base_position(...)` 前必须 `+1`。 |
| `image_match.py` OpenCV `keypoint.pt` | tile 内局部点坐标 | 0-based 浮点 | 属于当前 tile / crop 局部图像坐标。 |
| `image_match.py` `_keypoint_to_isis_coordinates()` | `.key` 输出点 | 1-based | 通过 `window.start_x + keypoint.pt[0] + 1`、`window.start_y + keypoint.pt[1] + 1` 转成整图 sample/line。 |
| `dom_prepare.py` `CropWindow.start_sample/start_line` | 裁剪窗口左上角 | 1-based | 面向 ISIS 图像空间定义，便于直接与 sample/line 语义对齐。 |
| `dom_prepare.py` `CropWindow.offset_sample/offset_line` | 裁剪偏移 | 0-based | 显式定义为 `start_sample - 1`、`start_line - 1`，用于数组窗口和 sidecar 回拼。 |
| `keypoints.py` `Keypoint.sample/line` 与 `.key` 文件正文 | tie point 坐标 | 1-based | `.key` 文件交换格式按 ISIS 像素坐标保存，不按 NumPy 下标保存。 |
| `dom2ori.py` `_is_point_in_bounds()` | 输入/输出边界判断 | 1-based | 当前实现明确使用 `1.0 <= sample <= width`、`1.0 <= line <= height`。 |
| `dom2ori.py` `UniversalGroundMap.set_image()` 输入 | DOM 点坐标 | 1-based | 直接消费 `.key` 中的 sample/line。 |
| `dom2ori.py` `original_ground_map.sample()/line()` 输出 | 原始影像点坐标 | 1-based | 返回结果继续写回 `.key`，不额外减 1。 |
| `image_overlap.py` `_linspace_positions()` | 相机采样网格 | 1-based | 采样位置从 `1.0` 到 `max_value`，用于 `camera.set_image(sample, line)`。 |
| `controlnet_stereopair.py` `ControlMeasure.set_coordinate()` | ControlMeasure 像素坐标 | 1-based | 直接写入 `.key` 中的 sample/line，不再做偏移换算。 |
| `dom_prepare.py` `projected_min_x/max_x/min_y/max_y`、重叠范围 | 投影坐标 | 非像素基准 | 属于地图投影空间，不应用 0-based / 1-based 像素规则解释。 |

### 开发约束

1. 任何从 NumPy/OpenCV 局部图像坐标写回 `.key`、ISIS 几何接口、或 ControlNet 前，必须显式完成 `+1` 转换；
2. 任何从 ISIS `start_sample/start_line` 写入 Python 窗口偏移、tile 起点、或 sidecar offset 字段前，必须显式完成 `-1` 转换；
3. 文档、日志、JSON sidecar、以及测试断言中，必须明确标注字段属于：
	- 0-based offset
	- 1-based sample/line
	- projected/map coordinate
4. 若后续新增模块混用上述三类坐标，必须在接口文档中写明输入/输出坐标基准，不能依赖调用方“默认理解”。

## 详细功能需求

### 1. `image_overlap.py`

职责：根据原始影像列表计算两两重叠的立体像对，并输出到 `images_overlap.lis`。

要求：

1. 输入为 `original_images.lis`；
2. 输出为 `images_overlap.lis`；
3. 每个立体像对按 `A,B` 一行存储；
4. `A,B` 与 `B,A` 必须使用 HASH 或等价唯一性策略去重，只保留一个；
5. 该步骤输出的是后续 DOM 匹配与 pairwise ControlNet 生成所需的无向立体像对集合；
6. 若影像不存在、列表为空、或无法建立重叠关系，应输出明确错误或空结果说明。

### 2. `dom_prepare.py`

职责：在 DOM 正式匹配前，检查所有 DOM 的分辨率是否一致，必要时自动重采样，并输出新的 DOM 列表与 GSD 报告。

要求：

1. 必须读取每景 DOM 的 GSD 并输出 `images_gsd.txt`；
2. `images_gsd.txt` 每行应记录原列表中的文件名与其 GSD；
3. 默认认为相对 GSD 差异在 `5%` 以内可视为一致；
4. 当某景 DOM 的 GSD 超出阈值时，应自动按平均 GSD 使用 `gdal_translate` 重采样；
5. 平均 GSD 默认按整个 `doms.lis` 统计，而不是单个像对单独统计；
6. 重采样后必须输出新的 `doms_scaled.lis`，后续匹配应优先使用该列表；
7. CLI 应支持 dry-run，以便仅验证计划命令与输出清单而不真正执行重采样。

### 3. `image_match.py`

职责：针对某个立体像对对应的两幅 DOM，使用 OpenCV SIFT 进行匹配，并输出 DOM 空间 `.key` 文件。

#### 3.0 配置文件默认值接入

1. `image_match.py` 应支持可选配置文件输入（例如 `--config`），用于读取 DOM 匹配阶段的默认参数；
2. 配置文件中的匹配参数应集中放在 `ImageMatch`（或等价兼容键名）下，而不是散落在顶层；
3. 通过配置文件提供的默认值，至少应覆盖：分块大小、overlap、灰度拉伸、无效值、有效像素阈值、SIFT 参数、公共范围扩张、CPU 并行、可视化输出等主要匹配参数；
4. 当同一参数同时在配置文件与命令行中给出时，命令行值优先；
5. 示例批处理脚本若存在配置文件入口，也应将该配置默认值转发给 `image_match.py`，以避免示例脚本与底层 CLI 使用两套不一致的参数来源。

#### 3.1 DOM 投影空间标准化对齐与裁剪

1. 匹配前必须基于投影坐标求两景 DOM 的公共部分，而不是简单按 raster 宽高取 `min(width, height)`；
2. 公共部分裁剪时默认在四周各外扩 `100` 像素；
3. 外扩像素值必须允许用户通过命令行覆盖；
4. 当公共部分或外扩后窗口被图像边界截断时，必须在 sidecar 中记录；
5. 裁剪 sidecar 至少应记录：
	- `Moon`
	- `Mars`
	- `Earth`
	- `Ryugu`
	- `Bennu`
5. 设计上允许继续扩充到 ISIS 支持的其他目标体；
6. 控制点编号、来源立体像对信息、写盘格式等应具备可追踪性；
7. 应支持可选 JSON sidecar 报告输出；
8. 若启用 sidecar 输出，推荐默认文件名与输出 `.net` 同名主干、扩展名为 `.summary.json`；
9. per-pair JSON 至少应包含以下字段：
	- `pair`：立体像对标识，推荐格式 `A,B`；
	- `match.point_count` 或等价字段：DOM 匹配点数；
	- `merge.unique_count` 或等价字段：DOM 去重点数；
	- `left_conversion.output_count`：左像 dom2ori 保留点数；
	- `right_conversion.output_count`：右像 dom2ori 保留点数；
	- `controlnet.point_count`：最终 control point 数；
	- `dom2ori_retention_rate`：若直接写出该字段，应明确定义为保留点数相对于 merge 点数的比值；
	- `report_path`：若运行时自动落盘，应返回实际写出的报告路径。
	- `--overlap-size-x = 128`
	- `--overlap-size-y = 128`
4. 上述参数必须允许用户通过命令行覆盖；
5. 每个子块必须记录其相对于裁剪窗口和原始整幅 DOM 的起始位置偏移，用于后续将子块内坐标恢复到整图坐标；
6. 首版合并时，**暂不要求解决不同重叠块之间重复连接点的问题**，该问题由后续 `tie_point_merge_in_overlap.py` 处理；
7. 输出 `.key` 时坐标必须保持原始 DOM 整图坐标，而不是裁剪图局部坐标。

#### 3.4 灰度映射与非 BYTE 数据处理

1. 如果输入 CUBE 像素类型不是 BYTE，而是 float、int 或其他非 BYTE 类型，则在匹配前必须自动转换到 `0–255` 灰度范围；
2. 默认拉伸策略为：舍去灰度值最小和最大的 `0.5%` 像素后，使用剩余区间做线性映射；
3. 也必须支持用户手工指定拉伸使用的原始灰度最小值和最大值；
4. 对于手工指定范围外的像素：
	- 小于最小值的设为 `0`
	- 大于最大值的设为 `255`
5. 灰度映射逻辑必须作为独立、可测试的功能，而不是散落在匹配代码中的隐式行为。

#### 3.5 无效值与特殊像元处理

无效值问题必须明确纳入需求，而不是留到实现阶段临时决定。至少要覆盖：

1. ISIS 特殊像元，例如 Null、LIS、LRS、HIS、HRS；
2. 浮点型中的 `NaN` 与 `Inf`；
3. 因用户指定拉伸范围导致被裁剪到边界值的像元；
4. 在计算百分位拉伸统计时，必须排除无效值与特殊像元；
5. 在 SIFT 特征提取时，无效值区域不能被当作正常纹理参与有效统计；
6. 当某个子块有效像素比例过低时，应允许跳过该块，并记录“无效值过多/有效纹理不足”的原因；
7. 失败日志中应能够区分：
	- 因无效值或特殊像元导致无法匹配；
	- 因正常纹理不足导致匹配失败；
	- 因匹配过滤后无有效点导致失败。

#### 3.6 merge 后 RANSAC 粗差剔除

1. DOM 分块匹配结果在进入 `dom2ori.py` 之前，必须先经过 `tie_point_merge_in_overlap.py` 去重，再对 merge 后的 paired keypoints 支持基于 Homography 的 RANSAC 粗差剔除；
2. RANSAC 的常用参数必须提供默认值，同时允许用户通过命令行覆盖；推荐默认值至少包括：
	- `ransac_reproj_threshold = 3.0`
	- `ransac_confidence = 0.995`
	- `ransac_max_iters = 5000`
3. RANSAC 模式至少支持：
	- `strict`
	- `loose`
4. `strict` 模式下，被 OpenCV `findHomography(..., RANSAC, ...)` 判定为 outlier 的点必须直接剔除；
5. `loose` 模式下，被 OpenCV 判定为 outlier 的点不能立即丢弃，而应先使用拟合得到的 Homography 矩阵重新投影，并计算预测点与真实匹配点之间的像素误差；
6. 若该误差不超过 `loose_ransac_keep_threshold`，则该点即使被 OpenCV 标为 outlier，也应保留；推荐默认阈值为 `1.0` 像素；
7. RANSAC 输出的 JSON / 日志 / sidecar 至少应能区分：
	- OpenCV 原始 inlier / outlier 数量；
	- 最终 retained / dropped 数量；
	- `loose` 模式下被“软保留”的 outlier 数量；
	- 实际使用的模式、阈值与 Homography 参数状态。

#### 3.7 匹配结果连线图可视化

1. 匹配结果可视化应基于 **merge 后、RANSAC 后** 的 paired keypoints 绘制，而不是直接对未去重、未过滤的分块原始匹配点绘图；
2. 绘图实现必须放在 `image_match.py` 的共享能力中，并采用 `cv2.drawMatches` 作为核心绘制方式；
3. 默认应对左右影像先做统一缩放，再按缩放后的坐标构造并绘制匹配点；默认缩放倍数为 `3.0`，并允许用户通过参数覆盖；
4. 匹配连线图文件名不要求用户手工指定，默认应自动按如下格式生成：
	- `A__B__YYYYMMDDTHHMMSS.png`
5. 其中：
	- `A` 为左影像文件名主干；
	- `B` 为右影像文件名主干；
	- 时间戳必须使用实际处理时刻；
6. 是否生成该连线图必须由参数控制，而不是默认强制输出；
7. 若采用 `loose` RANSAC 并保留了被 OpenCV 视为 outlier 的点，则这些点在可视化中应做额外标记，以便区分普通 inlier 与“软保留”点。

### 4. `tie_point_merge_in_overlap.py`

职责：在单个立体像对内部，对分块匹配并回拼后的同名点进行去重合并。

要求：

1. 该程序在一个立体像对的所有子块匹配完成后运行；
2. 去重依据为合并后同名点的像素坐标；
3. 行、列坐标按小数点后 3 位格式化后组成字符串，并作为 HASH 值；
4. 若后续连接点产生了相同 HASH 值，则视为重复点；
5. 对重复点执行直接合并；
6. 该规则至少应在立体像对内部成立，不要求本阶段扩展为跨立体像对的全局去重。

### 5. `keypoints_io.py`

职责：统一负责连接点 `.key` 文件读写。

对于立体像对 `A__B`，连接点文件存储格式为：

- `A__B_A.key`
- `A__B_B.key`

`.key` 文件内容格式要求为：

1. 第一行：同名点数量，例如 `1500`；
2. 第二行：图像宽；
3. 第三行：图像高；
4. 第四行起：逐点写出像素坐标，例如：
	- `Sample1, Line1,`
	- `Sample2, Line2,`
	- `...`

要求：

1. 读写逻辑必须稳定、可逆、可单元测试；
2. 文件头与点数量必须自洽；
3. 点顺序在同一对文件之间必须保持一致；
4. 对非法格式、空文件、数量不一致等情况要有明确错误处理；
5. `.key` 主体格式不因裁剪偏移需求而改变，偏移与裁剪信息通过 sidecar 元数据承载。

### 6. `dom2ori.py`

职责：将 DOM 空间的像素坐标 `.key` 文件转换到对应原始影像空间的像素坐标 `.key` 文件。

输入：

1. DOM 像素坐标 `.key` 文件；
2. 对应的 DOM 影像文件名（CUBE）；
3. 对应的原始影像文件名（CUBE）。

输出：

1. 原始影像像素坐标 `.key` 文件。

要求：

1. 必须基于 `isis_pybind` 提供的 ISIS 几何能力完成 DOM→原始影像坐标转换；
2. 要求明确记录转换失败点，例如：
	- 无法从 DOM 坐标恢复地理位置；
	- 无法在原始影像上反投影到有效像素；
	- 超出原始影像范围；
3. 输出点顺序应与输入 `.key` 文件保持对应，除非明确记录并剔除失败点；
4. 需要在接口与日志中保留失败点统计；
5. 由于 `image_match.py` 输出的 `.key` 最终保持原始 DOM 整图坐标，因此 `dom2ori.py` 不强制依赖 sidecar 才能完成几何转换，但调试流程应保留 sidecar 引用入口。

### 7. `controlnet_stereopair.py`

职责：根据单个立体像对的原始影像空间 `.key` 文件生成 ISIS 支持的控制网格式。

输入：

1. `ori_A.key`
2. `ori_B.key`
3. 生成控制网所需配置参数。

输出：

1. ISIS 控制网文件；
2. 支持 PVL 或二进制格式；
3. 可选的 per-pair JSON sidecar 报告。

要求：

1. 控制网生成必须依赖 `isis_pybind` 中的 ControlNet 相关能力；
2. 以下参数为必填，且**无默认值**：
	- `NetworkId`
	- `TargetName`
	- `UserName`
3. `TargetName` 需要从配置文件读取；
4. 配置文件需支持至少这些目标体：
	- `Moon`
	- `Mars`
	- `Earth`
	- `Ryugu`
	- `Bennu`
5. 设计上允许继续扩充到 ISIS 支持的其他目标体；
6. 控制点编号、来源立体像对信息、写盘格式等应具备可追踪性；
7. 应支持可选 JSON sidecar 报告输出；
8. 若启用 sidecar 输出，推荐默认文件名与输出 `.net` 同名主干、扩展名为 `.summary.json`；
9. per-pair JSON 至少应包含以下字段：
	- `pair`：立体像对标识，推荐格式 `A,B`；
	- `match.point_count` 或等价字段：DOM 匹配点数；
	- `merge.unique_count` 或等价字段：DOM 去重点数；
	- `ransac.retained_count` 或等价字段：merge 后经 RANSAC 保留的点数；
	- `ransac.dropped_count` 或等价字段：merge 后经 RANSAC 剔除的点数；
	- `left_conversion.output_count`：左像 dom2ori 保留点数；
	- `right_conversion.output_count`：右像 dom2ori 保留点数；
	- `controlnet.point_count`：最终 control point 数；
		- `controlnet.point_id_prefix`：基础 point-id 前缀；
		- `controlnet.pair_id`：单 pair 配置或 batch 自动分配得到的 pair ID；
		- `controlnet.point_id_namespace`：最终使用的 point-id 命名空间前缀；
	- `dom2ori_retention_rate`：若直接写出该字段，应明确定义为保留点数相对于 merge 点数的比值；
	- `report_path`：若运行时自动落盘，应返回实际写出的报告路径。
	- `match_visualization.output_path`：若启用了匹配连线图输出，应返回实际写出的 PNG 路径。
	10. 除单 pair CLI 外，建议提供 batch 入口（例如 `from-dom-batch`），从 `images_overlap.lis`、`original_images.lis`、`doms.lis` 和 per-pair DOM `.key` 目录中自动构建所有 pairwise `.net`，并在内部自动分配 `S1/S2/S3...` 这类 pair ID。

### 8. `controlnet_merge.py`

职责：根据 `image_overlap.lis` 和实际产出的 pairwise `.net` 文件，自动生成一个调用 `cnetmerge` 的 shell 脚本，用于将多个立体像对控制网合并为整体控制网。

要求：

1. 脚本输入集合应以 `image_overlap.lis` 中实际存在的 pairwise `.net` 为准；
2. 对缺失的 pairwise `.net`，默认允许跳过并在输出摘要中记录；
3. 生成脚本时同时生成 `cnetmerge` 所需的控制网列表文件；
4. 脚本中应明确写入 `NETWORKID`、`DESCRIPTION`、`ONET` 等关键参数；
5. 脚本文件应具备可执行权限；
6. 除 merge shell 外，建议支持读取 per-pair JSON 报告并输出 batch summary JSON；
7. batch summary 推荐固定命名为 `controlnet_batch_summary.json`；
8. batch summary 至少应包含以下字段：
	- `pair_count`；
	- `total_match_point_count`；
	- `total_merge_point_count`；
	- `total_dom2ori_retained_count`；
	- `total_final_control_point_count`；
	- `average_dom2ori_retention_rate`：所有有效 pair retention rate 的算术平均；
	- `overall_dom2ori_retention_rate`：总保留点数除以总 merge 点数，即 $\dfrac{\text{total_dom2ori_retained_count}}{\text{total_merge_point_count}}$；
	- `pairs`：逐 pair 摘要数组，至少包含 pair 名称、状态、关键点数与 retention rate；
	- `source_reports`：纳入汇总的 per-pair JSON 路径列表。

## 共享库与 CLI 组织要求

虽然外部工作流按多个 CLI 程序组织，但实现层允许采用共享库方式以减少重复代码。推荐至少拆分下列内部能力：

- 列表与路径解析；
- DOM GSD 读取与重采样决策；
- 投影公共范围计算与裁剪 sidecar 生成；
- CUBE 读取与灰度预处理；
- 无效值掩膜；
- 图像分块与块偏移记录；
- SIFT 匹配；
- `.key` 读写；
- 去重合并；
- DOM→原始影像坐标转换；
- ControlNet 构建与写盘；
- `cnetmerge` shell 与输入列表生成；
- per-pair JSON 与 batch summary JSON 聚合；
- 统一日志与统计输出。

## 测试与开发方式要求

本任务要求采用 **TDD（测试驱动开发）** 方式推进。

具体要求：

1. 先搭整体框架，保证在任意阶段代码都尽量可运行、可验证；
2. 避免一次性写入大量未经验证的实现代码；
3. 每完成一个共享模块或一个 CLI 工具，都应优先补对应的 focused test；
4. 优先验证：
	- `.key` 文件读写；
	- 灰度拉伸；
	- 无效值掩膜；
	- GSD 阈值判断与重采样命令生成；
	- 投影公共范围与裁剪偏移；
	- 分块偏移回拼；
	- HASH 去重；
	- DOM→原图坐标转换；
	- ControlNet 输出；
	- `cnetmerge` shell 生成；
	- per-pair JSON 与 batch summary JSON 聚合口径。

## 非目标

当前正式需求 **不包含** 以下内容：

1. 并行调度、集群执行或大规模任务编排；
2. 与主流程耦合的亚像素精匹配或相关匹配细化；
3. 新增底层 ISIS C++ 绑定接口，除非 `isis_pybind` 现有能力不足且后续实现阶段明确提出需要扩展。

## 对应产物

- 代码计划与架构：`examples/controlnet_construct/plan_architecture_dom_matching_controlnet.md`
