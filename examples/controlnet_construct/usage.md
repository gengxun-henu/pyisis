# DOM Matching ControlNet 端到端使用说明

这份文档把 `examples/controlnet_construct/` 里的关键脚本串成一条可以顺着执行的流水线：

1. `image_overlap.py`
2. `image_match.py`
3. `controlnet_stereopair.py from-dom-batch`
4. `controlnet_merge.py`
5. （可选）`merge_control_measure.py`

目标不是只告诉你“某个命令能跑”，而是让你从输入列表开始，一步一步得到：

- `images_overlap.lis`
- per-pair DOM `.key`
- pairwise `.net`
- per-pair JSON / batch summary JSON
- `cnetmerge` shell 脚本
- 最终 merged ControlNet

> 这份说明默认你已经完成 DOM 准备阶段，即已经有与 `original_images.lis` 对齐的 `doms_scaled.lis`（或至少有 `doms.lis`）。如果你的 DOM GSD 还没有统一，建议先跑 `dom_prepare.py`。

如果你不想手工逐段执行，仓库中还提供了把这四段主流程直接串起来的示例脚本：

- `examples/controlnet_construct/run_pipeline_example.sh`
- `examples/controlnet_construct/run_image_match_batch_example.sh`
- `examples/controlnet_construct/recommended_batch_templates.md`

它默认会依次执行本文的前四个主步骤，并在最后自动执行生成的 `merge_all_controlnets.sh`。如果你希望在最终总网生成后，再自动执行一轮 `merge_control_measure.py` 后处理，可以额外加上 `--post-merge-control-measure`。如果你只想先生成 merge 脚本、不立刻执行最终 `cnetmerge`，可以给它加 `--skip-final-merge`。

从当前版本开始，这两个示例脚本还带有两个新的**默认行为**：

1. 默认开启 CPU 分块并行匹配；只有显式传 `--no-parallel-cpu` 时，才会回退到串行 tile 匹配。
2. 默认的 CPU 进程池 worker 上限是 `8`；你可以通过 `--num-worker-parallel-cpu` 改成 `1~4096` 之间的值。
3. 默认输出匹配连线可视化 PNG，而不是必须手工额外开开关。

同时，`image_match.py` 以及两个示例脚本现在还支持三组与性能和稳定性相关的新能力：

4. 可选启用**低分辨率 DOM 粗配准**，先在低分辨率层估计一组全局投影偏移，再进入全分辨率 overlap crop；
5. 可配置 `invalid-pixel-radius`，在无效像素和图像边界附近抑制 SIFT 特征点检测。
6. 可显式启用 **tile-validity prefilter**，在全分辨率 tile 读取前用 DOM 有效像素索引保守跳过明显无效的 tile。

其中两个示例脚本的可视化目录约定不同：

- `run_image_match_batch_example.sh`：默认只产出 **image_match 阶段（pre-RANSAC）** 的连线图，目录是 `work/match_viz/`；
- `run_pipeline_example.sh`：默认同时产出两套连线图：
  - `work/match_viz/`：`image_match.py` 直接输出的 **pre-RANSAC** 连线图；
  - `work/match_viz_post_ransac/`：`controlnet_stereopair.py from-dom-batch` 在 merge + RANSAC 之后输出的 **post-RANSAC** 连线图。

如果你想显式开启默认 CPU 并行标志，可以传 `--use-parallel-cpu`；如果你想关闭默认 CPU 并行，可以传 `--no-parallel-cpu`；如果你想把进程池 worker 上限改成别的值，可以传 `--num-worker-parallel-cpu 4` 之类；如果你想关闭 pre-RANSAC 连线图，可以在 `run_image_match_batch_example.sh` 后面通过 `-- --no-write-match-visualization` 把参数继续转发给 `image_match.py`。

与全分辨率 tile 读取优化相关的 `image_match.py` 参数包括：

- `--enable-tile-validity-prefilter`：显式启用 workflow 级 DOM validity-index cache，在全分辨率 tile 读取前做保守预过滤。默认关闭，方便保留现有运行作为 A/B baseline。
- `--tile-validity-cache-dir PATH`：存放可复用的 per-DOM validity index 文件。如果省略，image-match 会根据输出上下文推导 workflow 级 `tile_validity_cache` 目录。
- `--tile-validity-cell-width N` 与 `--tile-validity-cell-height N`：控制 coarse validity grid 的 cell 尺寸，默认均为 `1024`。

如果你只想专注在第 2 步批量 DOM 匹配，而不想整条流水线一起跑，那么优先看：

- `examples/controlnet_construct/run_image_match_batch_example.sh`
- `examples/controlnet_construct/recommended_batch_templates.md`

如果你当前正在调 `enable_tile_validity_prefilter`，并且想拿真实数据比较不同 coarse cell 组合的收益，而不是靠感觉拍参数，那么还可以直接跑：

- `examples/controlnet_construct/tile_validity_benchmark.py`

例如：

```bash
python examples/controlnet_construct/tile_validity_benchmark.py \
  left_dom.cub right_dom.cub \
  --config examples/controlnet_construct/controlnet_config.example.json \
  --cell-size 1024x1024 \
  --cell-size 1024x1071 \
  --cell-size 2048x1428 \
  --output work/reports/tile_validity_benchmark.json
```

这份 JSON 会同时记录：

- 左右 DOM validity index 的 cold / warm build 时间；
- 每组 `cell_width / cell_height` 对应的 coarse grid 大小；
- `pair_preparation` 成功后可参与 prefilter 的 tile 数；
- 每组参数的 prefilter 保留比例与 skip reasons。

如果你更想扫一组宽高网格，而不是手工一条条写 `--cell-size`，可以改用：

```bash
python examples/controlnet_construct/tile_validity_benchmark.py \
  left_dom.cub right_dom.cub \
  --cell-width 1024 --cell-width 2048 \
  --cell-height 1024 --cell-height 1071 --cell-height 1428
```

它会自动做 width × height 的组合笛卡尔积，并去重输出。对于 tiled ISIS cube，建议优先把 `cell_height` 试到内部 `TileLines` 的整数倍附近，而不是只改一个 strip 思路然后祈祷性能自己变好。

## 模块结构（维护者速览）

从当前版本开始，`image_match.py` 已经不再承载所有内部实现细节，而是缩成了一个**兼容层 + 编排层**：

- 对外仍保留原来的 CLI 和主入口，例如：
  - `match_dom_pair(...)`
  - `match_dom_pair_to_key_files(...)`
  - `write_stereo_pair_match_visualization(...)`
- 对内则把原本耦合在一个文件里的几块职责拆到了更明确的模块中。

建议把这几份文件理解成下面这张“职责地图”：

- `image_match.py`
  - 角色：**公开入口 / 配置解析 / 流程编排 / 兼容 façade**
  - 负责：
    - CLI 参数与 `--config` 默认值装配
    - 调用 projected-overlap crop 准备逻辑
    - 组织低分辨率粗配准、tile 匹配、结果汇总与 sidecar 输出
    - 为现有脚本和单测继续保留历史函数名与导出面
- `lowres_offset.py`
  - 角色：**低分辨率粗配准模块**
  - 负责：
    - 生成低分辨率 DOM（当前通过 ISIS `reduce`）
    - 低分辨率 keypoint 的投影坐标转换
    - 估计 projected global offset，并在失败时回退到零偏移
- `match_visualization.py`
  - 角色：**匹配连线可视化模块**
  - 负责：
    - `cv2.drawMatches` 预览图输出
    - 默认 PNG 命名规则
    - 从 `.key` 文件直接生成可视化
- `tile_matching.py`
  - 角色：**SIFT / tile / 并行匹配核心模块**
  - 负责：
    - tile 切分与 shared extent window 组织
    - 灰度拉伸后图像准备与 mask 处理
    - SIFT 检测、ratio-test 过滤
    - 串行 / CPU 进程池 tile 匹配执行
    - tile 级统计数据结构（如 `TileMatchStats`、`TileMatchResult`）
- `stereo_ransac.py`
  - 角色：**立体像对 RANSAC 过滤模块**
  - 负责：
    - 对左右 `.key` 做 homography RANSAC 过滤
    - strict / loose 两种保留策略
    - 输出 retained / dropped / soft-outlier 等诊断摘要

如果你只是**使用**这条流水线，那么仍然可以把 `image_match.py` 当成第 2 步的唯一 CLI 入口。

如果你是在**维护**代码，推荐遵循下面这个判断规则：

- 改匹配参数、CLI 行为、sidecar 汇总字段、流程顺序：优先看 `image_match.py`
- 改低分辨率粗配准：优先看 `lowres_offset.py`
- 改 pre-RANSAC / post-RANSAC 连线图输出：优先看 `match_visualization.py`
- 改 tile/SIFT/并行执行细节：优先看 `tile_matching.py`
- 改 RANSAC 内点/软外点策略：优先看 `stereo_ransac.py`

当前仍保留 `image_match.py` 里的若干兼容 wrapper / alias，主要是为了让历史脚本、下游导入和 focused unit tests 不需要在同一次重构里整体迁移。换句话说：**模块已经拆开了，但门牌号暂时还保留着旧地址**。

## 0. 前提准备

### 0.1 运行环境

推荐使用本仓库默认的 `asp360_new` 环境，并确保 Python 可以导入 `isis_pybind`。

如果你已经把绑定安装进当前环境，直接运行即可；如果你只是从构建目录临时使用，请先让 Python 看到 `build/python`。

```bash
export PYTHONPATH="$PWD/build/python${PYTHONPATH:+:$PYTHONPATH}"
python -c "import isis_pybind as ip; print(ip.__file__)"
```

### 0.2 需要准备的输入文件

至少准备好下面三类输入：

1. `original_images.lis`
   - 每行一个原始 ISIS cube 路径；
   - 供 `image_overlap.py` 和 `controlnet_stereopair.py from-dom-batch` 使用。

2. `doms_scaled.lis` 或 `doms.lis`
   - 每行一个与原图一一对应的 DOM cube 路径；
   - 行顺序必须与 `original_images.lis` 完全一致；
   - 推荐优先使用 `dom_prepare.py` 产出的 `doms_scaled.lis`。

3. `controlnet_config.example.json` 风格的配置 JSON
   - 至少包含 `NetworkId`、`TargetName`、`UserName`；
   - `PointIdPrefix` 可选；
   - `PairId` 在 batch 模式下会被自动分配的 `S1`、`S2`、`S3`... 覆盖，不需要手工逐对填写。
  - 从当前版本开始，`image_match.py` 本身支持 `--config`，会读取配置文件里的 `ImageMatch` 段作为匹配默认值；`run_pipeline_example.sh` 和 `run_image_match_batch_example.sh` 也会把这段配置一起转发给 `image_match.py`。
  - 因此除了 `valid_pixel_percent_threshold` 与 `num_worker_parallel_cpu` 之外，你也可以把 tile 尺寸、overlap、灰度拉伸、SIFT 参数、crop/range 参数、并行开关、预览图开关，以及新增的 `invalid_pixel_radius` / `enable_low_resolution_offset_estimation` / `low_resolution_level` 等 DOM 匹配参数统一写进 `ImageMatch`。

仓库自带的示例配置位于：

- `examples/controlnet_construct/controlnet_config.example.json`

当前示例配置里的 `ImageMatch` 已经覆盖常用匹配参数，例如：

```json
"ImageMatch": {
  "band": 1,
  "max_image_dimension": 3000,
  "sub_block_size_x": 1024,
  "sub_block_size_y": 1024,
  "overlap_size_x": 128,
  "overlap_size_y": 128,
  "lower_percent": 0.5,
  "upper_percent": 99.5,
  "min_valid_pixels": 64,
  "valid_pixel_percent_threshold": 0.05,
  "enable_tile_validity_prefilter": false,
  "tile_validity_cell_width": 1024,
  "tile_validity_cell_height": 1024,
  "matcher_method": "bf",
  "ratio_test": 0.75,
  "crop_expand_pixels": 100,
  "min_overlap_size": 16,
  "use_parallel_cpu": true,
  "num_worker_parallel_cpu": 8,
  "invalid_pixel_radius": 1,
  "enable_low_resolution_offset_estimation": false,
  "low_resolution_level": 3,
  "low_resolution_max_mean_reprojection_error_pixels": 3.0,
  "write_match_visualization": true,
  "match_visualization_scale": 0.3333333333333333
}
```

`run_pipeline_example.sh` 会把这段配置转发给第 2 步的 `image_match.py`；如果你是手工直接调用 `image_match.py`，也可以直接传：

```bash
python examples/controlnet_construct/image_match.py \
  --config examples/controlnet_construct/controlnet_config.example.json \
  left_dom.cub right_dom.cub left.key right.key
```

如果你又在命令行里显式传了某个匹配参数，例如 `--ratio-test 0.8`、`--matcher-method flann` 或 `--num-worker-parallel-cpu 4`，则命令行值会覆盖配置文件中的默认值。

维护者提示：`image_match.py --config CONFIG --print-config-default FIELD` 是给示例 shell wrapper 使用的轻量 helper，用于从同一套 Python 配置解析逻辑中读取单个 `ImageMatch` 默认值；普通用户仍应优先通过 `--config` 和显式 CLI 参数运行匹配。

#### 可视化预览模式与缩放优先级

DOM 匹配连线图的预览可以裁剪，或在显式 reduced 模式下使用降采样预览 cube，以避免超大 DOM 直接全分辨率可视化导致的内存压力。相关字段在 JSON 里是 snake_case，CLI 里对应 kebab-case：

- `visualization_mode` / `--visualization-mode`：`full`、`cropped`、`auto`、`reduced`、`reduced_cropped`。`auto` 只在全图与裁剪之间自动选择；如需使用降采样预览 cube，需显式选择 `reduced` 或 `reduced_cropped`。
- `memory_profile` / `--memory-profile`：`high-memory`、`balanced`、`low-memory`。仅在未显式设置 `visualization_target_long_edge` 时决定默认目标长边。
- `visualization_target_long_edge` / `--visualization-target-long-edge`：预览目标长边像素，显式指定时优先级最高。
- `low_resolution_matching_target_long_edge` / `--low-resolution-matching-target-long-edge`：仅在未显式设置 `low_resolution_level` / `--low-resolution-level` 时用于推导低分辨率粗配准的 reduce 等级。
- `preview_crop_margin_pixels` / `--preview-crop-margin-pixels`：裁剪模式下在关键点外扩的像素边距。
- `preview_cache_source` / `--preview-cache-source`：预览图复用来源，常用 `auto` 即可。

示例配置为了保持可复现实验结果仍显式设置了 `low_resolution_level`；此时 `low_resolution_matching_target_long_edge` 不会改变粗配准等级。若希望按目标长边自动推导低分辨率等级，请确保没有显式设置 `low_resolution_level`：从配置中移除 `low_resolution_level`，并且不要在 CLI 里传 `--low-resolution-level`。

### 0.3 推荐工作目录

下面命令统一假设你在仓库根目录下执行，并把中间产物写到 `work/`：

```text
work/
  original_images.lis
  doms_scaled.lis
  images_overlap.lis
  dom_keys/
  match_metadata/
  match_viz/
  tile_validity_cache/
  low_resolution/
  match_viz_post_ransac/
  pair_nets/
  reports/
  merge/
```

先创建这些目录：

```bash
mkdir -p work/dom_keys work/match_metadata work/match_viz work/low_resolution work/match_viz_post_ransac work/pair_nets work/reports work/merge
```

其中：

- `work/match_viz/`：保存 `image_match.py` 输出的 **pre-RANSAC** 连线图；
- `work/low_resolution_doms/level<N>/`：当启用低分辨率粗配准时，按当前 DOM 列表一次性缓存通过 ISIS `reduce` 生成的低分辨率 DOM；对应列表写到 `work/doms_low_resolution_level<N>.lis`，后续多个 pair 复用同一景 DOM 的低分辨率结果；
- `work/low_resolution/`：按 pair 保存从上述缓存复制来的低分辨率 DOM、低分辨率 key 文件、RANSAC 后 key 文件以及低分辨率阶段的可视化与诊断产物；
- `work/match_viz_post_ransac/`：保存 `run_pipeline_example.sh` / `controlnet_stereopair.py from-dom-batch` 输出的 **post-RANSAC** 连线图。

### 0.4 推荐参数模板（先抄这个版本）

如果你想要更短、更适合复制到自己实验记录里的版本，也可以直接看独立文档：`examples/controlnet_construct/recommended_batch_templates.md`。

如果你只是想先跑通一版，而且你的 DOM 数据存在明显的大面积无效背景，那么建议先直接使用下面这套“保守但实用”的模板。

这套模板的核心建议是：

- `valid_pixel_percent_threshold=0.05`
- 含义：某个 tile 的有效像素比例低于 $5\%$ 时，直接跳过匹配
- 典型适用场景：DOM 有效区域只占局部、边角很多 0、裁剪后外框仍然较大

#### 模板 A：直接跑示例流水线脚本

如果你使用 `run_pipeline_example.sh`，推荐优先让配置文件固化这个值：

```json
{
  "NetworkId": "dom_matching_example",
  "TargetName": "Moon",
  "UserName": "gengxun",
  "PointIdPrefix": "P",
  "ImageMatch": {
    "band": 1,
    "max_image_dimension": 3000,
    "sub_block_size_x": 1024,
    "sub_block_size_y": 1024,
    "overlap_size_x": 128,
    "overlap_size_y": 128,
    "lower_percent": 0.5,
    "upper_percent": 99.5,
    "min_valid_pixels": 64,
    "valid_pixel_percent_threshold": 0.05,
    "ratio_test": 0.75,
    "crop_expand_pixels": 100,
    "min_overlap_size": 16,
    "use_parallel_cpu": true,
    "num_worker_parallel_cpu": 8,
    "invalid_pixel_radius": 1,
    "enable_low_resolution_offset_estimation": false,
    "low_resolution_level": 3,
    "write_match_visualization": true,
    "match_visualization_scale": 0.3333333333333333
  }
}
```

然后直接跑：

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir work \
  --skip-final-merge
```

这条命令默认还会：

- 开启 CPU 分块并行匹配；
- 默认把 CPU 进程池 worker 上限设为 `8`；
- 把 pre-RANSAC 连线图写到 `work/match_viz/`；
- 把 post-RANSAC 连线图写到 `work/match_viz_post_ransac/`。

如果你希望整条流水线跑完后，自动再做一轮最终总网的量测坐标去重，可以改成：

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir work \
  --post-merge-control-measure \
  --post-merge-decimals 1
```

如果你不想改配置文件，或者想临时覆盖配置里的值，就显式传：

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir work \
  --valid-pixel-percent-threshold 0.05 \
  --skip-final-merge
```

如果你想显式关闭默认 CPU 并行，可以附加：

```bash
  --no-parallel-cpu
```

如果你想限制第 2 步最多只启 4 个 worker，可以附加：

```bash
  --num-worker-parallel-cpu 4
```

如果你已经把 `ImageMatch.num_worker_parallel_cpu` 写进配置文件，`run_pipeline_example.sh` 会自动读取；如果你想临时覆盖配置里的值，就继续显式传 `--num-worker-parallel-cpu` 即可。

如果你想进一步减少边界或无效区附近的伪特征，可以显式加上：

```bash
  --invalid-pixel-radius 2
```

如果你想把 SIFT 描述子匹配后端切到 FLANN，可以显式加上：

```bash
  --matcher-method flann
```

如果你的两景 DOM 存在较明显的整体投影平移，也可以先启用低分辨率粗配准：

```bash
  --enable-low-resolution-offset-estimation \
  --low-resolution-level 3
```

如果你已经启用了低分辨率粗配准，并希望更严格地拒绝几何不稳定的粗配准结果，还可以补一个重投影误差门槛：

```bash
  --low-resolution-max-mean-reprojection-error-pixels 2.5
```

这一步失败时不会中断整条流水线，而是自动回退为零偏移继续执行；对应状态会写进每个 pair 的 metadata JSON 里。

当前版本的低分辨率粗配准不再依赖 GDAL，而是直接调用 ISIS 原生命令 `reduce` 生成可保留 Mapping 标签的低分辨率 `.cub`，这样后续 `cube.projection()` 能稳定读取 `PixelResolution` 等投影关键字。为了避免同一景 DOM 在多个 overlap pair 中反复降采样，两个批处理 wrapper 会先生成一次 `work/doms_low_resolution_level<N>.lis` 和 `work/low_resolution_doms/level<N>/` 缓存；每个 pair 只把缓存里的低分辨率 DOM 复制到自己的诊断目录继续处理。

注意这和 `dom_prepare.py` 的 GSD 归一化不是同一件事：`dom_prepare.py` 仍然使用 `gdal_translate -of ISIS3 -tr target target` 把不同 DOM 调整到统一 GSD；低分辨率粗配准阶段才使用 ISIS `reduce`。

#### 模板 B：手工批量跑 `image_match.py`

如果你当前只想调 DOM 匹配这一段，而不想整条流水线一起跑，推荐从下面这套批处理模板起步：

```bash
VALID_PIXEL_PERCENT_THRESHOLD=0.05

declare -A DOM_BY_ORIGINAL
while IFS=$'\t' read -r original dom; do
  DOM_BY_ORIGINAL["$original"]="$dom"
done < <(paste work/original_images.lis work/doms_scaled.lis)

while IFS=, read -r left right; do
  left_stem=$(basename "${left%.*}")
  right_stem=$(basename "${right%.*}")
  pair_tag="${left_stem}__${right_stem}"

  python examples/controlnet_construct/image_match.py \
    "${DOM_BY_ORIGINAL[$left]}" \
    "${DOM_BY_ORIGINAL[$right]}" \
    "work/dom_keys/${pair_tag}_A.key" \
    "work/dom_keys/${pair_tag}_B.key" \
    --metadata-output "work/match_metadata/${pair_tag}.json" \
    --match-visualization-output-dir work/match_viz \
    --invalid-pixel-radius 1 \
    --num-worker-parallel-cpu 8 \
    --valid-pixel-percent-threshold "$VALID_PIXEL_PERCENT_THRESHOLD"

done < work/images_overlap.lis
```

如果你改用 `run_image_match_batch_example.sh`，它会默认做和上面模板一致的事情，并把 pre-RANSAC 连线图统一写到 `work/match_viz/`。若要关闭 CPU 并行，可传 `--no-parallel-cpu`；若要关闭这套默认连线图，可把 `--no-write-match-visualization` 通过 `--` 转发给 `image_match.py`。如果需要批量启用低分辨率粗配准，可直接给这个脚本加 `--enable-low-resolution-offset-estimation --low-resolution-level 3`；如果需要更严格地抑制无效区边缘特征，可加 `--invalid-pixel-radius 2`。

#### 什么时候把它从 `0.05` 调大或调小？

- 如果仍然有很多“几乎全空”的 tile 在浪费时间：可以尝试调到 `0.08` 或 `0.1`
- 如果你的有效覆盖本来就很稀薄，担心跳过太多：可以先降到 `0.03`
- 如果你还没摸清数据分布：先用 `0.05`，通常是一个比较稳的起步点

## 1. 先算出候选立体像对：`image_overlap.py`

这一步从原始影像列表出发，计算哪些原图两两存在足够的采样几何重叠，并输出 `images_overlap.lis`。

```bash
python examples/controlnet_construct/image_overlap.py \
  work/original_images.lis \
  work/images_overlap.lis
```

如果你想更保守或更密一点，也可以附加参数，例如：

```bash
python examples/controlnet_construct/image_overlap.py \
  work/original_images.lis \
  work/images_overlap.lis \
  --grid-samples 11 \
  --grid-lines 11 \
  --min-valid-points 4 \
  --tolerance 0.0
```

运行后你会得到：

- `work/images_overlap.lis`：每行一个 `A,B` 形式的无向立体像对；
- 终端 JSON 摘要：包含总 pair 数以及每景影像的采样 bounds。

### 这一阶段的作用

这一步是整条流水线的“筛对子”阶段：先把明显不重叠的组合剔掉，后面的 DOM 匹配和 ControlNet 构建就不用对所有组合硬跑一遍了。

## 2. 对每个重叠 pair 运行 DOM 匹配：`image_match.py`

`image_match.py` 目前是**单个立体像对 CLI**，所以批处理最直接的办法是：

1. 先读入 `original_images.lis` 和 `doms_scaled.lis` 的一一对应关系；
2. 再按 `images_overlap.lis` 逐对调用 `image_match.py`；
3. 把输出统一写成 `A__B_A.key`、`A__B_B.key` 这种命名，供下一步 `from-dom-batch` 直接读取。

下面这段 Bash 会完成整个批量 DOM 匹配：

对于大多数 DOM 数据，建议把 `valid_pixel_percent_threshold` 作为一个显式参数来控制。一个很实用的起步值是 `0.05`：

- 含义：当某个 tile 的有效像素比例低于 $5\%$ 时，直接跳过该 tile，不再做 SIFT；
- 适用场景：DOM 有效区域在地理范围内呈斜条状、弯月状，或者四角/边缘存在大量 0 / 无效像素；
- 直观收益：减少大量“几乎全空 tile”的特征提取和匹配开销。

如果你的 DOM 覆盖更稀疏，可以从 `0.05` 起步，再按数据分布微调到 `0.03` 或 `0.1`。

```bash
VALID_PIXEL_PERCENT_THRESHOLD=0.05

declare -A DOM_BY_ORIGINAL
while IFS=$'\t' read -r original dom; do
  DOM_BY_ORIGINAL["$original"]="$dom"
done < <(paste work/original_images.lis work/doms_scaled.lis)

while IFS=, read -r left right; do
  left_stem=$(basename "${left%.*}")
  right_stem=$(basename "${right%.*}")
  pair_tag="${left_stem}__${right_stem}"

  python examples/controlnet_construct/image_match.py \
    "${DOM_BY_ORIGINAL[$left]}" \
    "${DOM_BY_ORIGINAL[$right]}" \
    "work/dom_keys/${pair_tag}_A.key" \
    "work/dom_keys/${pair_tag}_B.key" \
    --metadata-output "work/match_metadata/${pair_tag}.json" \
    --match-visualization-output-dir work/match_viz \
    --invalid-pixel-radius 1 \
    --valid-pixel-percent-threshold "$VALID_PIXEL_PERCENT_THRESHOLD"

done < work/images_overlap.lis
```

如果你还没有 `doms_scaled.lis`，也可以把上面脚本中的 `work/doms_scaled.lis` 替换成 `work/doms.lis`，前提是它和 `original_images.lis` 保持严格一一对应。

### 这一步会产出什么

对 `images_overlap.lis` 中的每个 pair，例如 `A.cub,B.cub`，这一步会生成：

- `work/dom_keys/A__B_A.key`
- `work/dom_keys/A__B_B.key`
- `work/match_metadata/A__B.json`
- `work/match_viz/*.png`
- `work/low_resolution/<pair_tag>/*`（当启用低分辨率粗配准时）

其中：

- `.key` 文件保存的是 **DOM 整图坐标系下**的 tie points；
- `match_metadata/*.json` 保存投影公共范围裁剪等 sidecar 信息，并额外记录 `image_match.num_worker_parallel_cpu`、`image_match.parallel_cpu_used`、`image_match.parallel_cpu_worker_count` 等并行诊断字段；其中 `num_worker_parallel_cpu` 是请求上限，`parallel_cpu_worker_count` 是该次运行实际采用的 worker 数；
- 如果启用了低分辨率粗配准，`match_metadata/*.json` 中还会记录 `image_match.low_resolution_offset`，至少包括 `enabled`、`status`、`fallback_offset_zero`、`reason`、`delta_x_projected`、`delta_y_projected` 和 `retained_match_count`；
- `match_viz/*.png` 是 `cv2.drawMatches` 预览图，表示 **RANSAC 之前**、也就是 `image_match.py` 直接输出的匹配结果，便于快速人工检查匹配质量。

当前版本里，`image_match.py` 默认会开启这套 pre-RANSAC 可视化；如果你不想写 PNG，可以显式传 `--no-write-match-visualization`。

### 命名约定为什么重要

`controlnet_stereopair.py from-dom-batch` 会按如下规则在 `work/dom_keys/` 下查找每一对的 DOM `.key`：

- `A__B_A.key`
- `A__B_B.key`

这里的 `A` 和 `B` 不是随便起的，而是来自 `images_overlap.lis` 中左右路径的 **文件名主干**。所以前面这一步的输出命名最好严格按这个规则来，省得后面 batch 阶段找文件时“人找得到，脚本找不到”。

### 常用可调参数

如果默认匹配参数不适合你的数据，可以在循环里的 `image_match.py` 命令后继续追加这些参数：

- `--band 1`
- `--valid-pixel-percent-threshold 0.05`
- `--max-image-dimension 3000`
- `--sub-block-size-x 1024`
- `--sub-block-size-y 1024`
- `--overlap-size-x 128`
- `--overlap-size-y 128`
- `--crop-expand-pixels 100`
- `--min-overlap-size 16`
- `--ratio-test 0.75`
- `--invalid-pixel-radius 1`
- `--enable-low-resolution-offset-estimation`
- `--low-resolution-level 3`
- `--max-features ...`
- `--sift-contrast-threshold ...`
- `--no-write-match-visualization`

建议先用默认值跑通一轮，再针对问题 pair 做局部调参。

## 3. 批量生成 pairwise ControlNet：`controlnet_stereopair.py from-dom-batch`

当前一步已经把每个 pair 的 DOM `.key` 全部准备好后，就可以直接进入 batch ControlNet 构建。

```bash
python examples/controlnet_construct/controlnet_stereopair.py from-dom-batch \
  work/images_overlap.lis \
  work/original_images.lis \
  work/doms_scaled.lis \
  work/dom_keys \
  examples/controlnet_construct/controlnet_config.example.json \
  work/pair_nets \
  --report-dir work/reports \
  --pair-id-prefix S \
  --pair-id-start 1
```

如果你是手工运行这一步，而不是通过 `run_pipeline_example.sh`，并且希望像示例流水线那样保存 **post-RANSAC** 匹配预览图，可以附加：

```bash
  --write-match-visualization \
  --match-visualization-output-dir work/match_viz_post_ransac
```

`run_pipeline_example.sh` 当前已经默认附带这两个参数，因此整条示例流水线默认就会生成 `work/match_viz_post_ransac/`。

### 这一步内部做了什么

`from-dom-batch` 会按 `images_overlap.lis` 的顺序逐对处理，并为每个 pair 自动完成：

1. 读取 `work/dom_keys/A__B_A.key` / `A__B_B.key`；
2. DOM 重复点 merge；
3. merge 后 RANSAC 粗差剔除；
4. DOM → 原始影像坐标回投；
5. 构建单对 ISIS `ControlNet`；
6. 写出 per-pair JSON sidecar；
7. 汇总 batch summary JSON。

### 这一步会产出什么

- `work/pair_nets/*.net`：每个重叠 pair 对应一个 pairwise ControlNet；
- `work/reports/*.summary.json`：每个 pair 的 sidecar 报告；
- `work/reports/controlnet_batch_summary.json`：batch 总表。

### 自动分配的 pair ID

在这个 batch 模式下，脚本会自动按顺序分配：

- `S1`
- `S2`
- `S3`
- ...

因此你不需要为每个 pair 单独传 `--pair-id`。这些自动分配的 pair ID 会进入：

- per-pair JSON 报告；
- `point_id_namespace`；
- 最终 `ControlPoint` ID 命名空间。

这样多个 pairwise `.net` 后续再用 `cnetmerge` 汇总时，不同 pair 的 `PointId` 就不会互相撞车。

## 4. 生成全局 merge 脚本：`controlnet_merge.py`

当 `work/pair_nets/` 已经有了一批 pairwise `.net` 后，就可以让 `controlnet_merge.py` 自动生成 `cnetmerge` 需要的输入列表和 shell 脚本。

```bash
python examples/controlnet_construct/controlnet_merge.py \
  work/images_overlap.lis \
  work/pair_nets \
  work/merge/dom_matching_merged.net \
  work/merge/merge_all_controlnets.sh \
  --network-id dom_matching_example \
  --description "Merged DOM matching ControlNet" \
  --log work/merge/cnetmerge.log
```

如果你希望显式指定 `cnetmerge` 输入列表文件名，可以再附加：

```bash
  --pair-list work/merge/pair_nets_to_merge.lis
```

### 这一步会产出什么

- `work/merge/merge_all_controlnets.sh`：可直接执行的 merge shell；
- `work/merge/merge_all_controlnets.lis` 或你指定的 `--pair-list`：参与 merge 的 pairwise `.net` 列表；
- 终端 JSON 摘要：列出被纳入 merge 的 pairs，以及哪些 pair 因缺 `.net` 被跳过。

默认行为是：

- **有 `.net` 的 pair 纳入 merge**；
- **缺 `.net` 的 pair 记录为 skipped**；
- 不会因为少数 pair 缺失而整批失败。

如果你想改成“缺一个就报错”，可以加 `--strict`。

## 5. 执行 `cnetmerge`，得到最终总网

上一步只是**生成** merge shell，不会自动替你执行。确认脚本内容无误后，再运行：

```bash
bash work/merge/merge_all_controlnets.sh
```

执行成功后，最终总网通常会写到：

- `work/merge/dom_matching_merged.net`

如果你在上一步传了 `--log work/merge/cnetmerge.log`，还会得到：

- `work/merge/cnetmerge.log`

## 5.5 可选后处理：按量测坐标合并重复 ControlPoint

如果你已经通过 `cnetmerge` 得到了全局总网，但仍然希望再做一轮“按量测坐标去重”的后处理，可以继续运行：

```bash
python examples/controlnet_construct/merge_control_measure.py \
  work/original_images.lis \
  work/merge/dom_matching_merged.net \
  work/merge/dom_matching_merged_measure_merged.net \
  --decimals 1
```

这一步的设计目标是：

- 把 `cnetmerge` 输出的最终 `ControlNet` 作为输入；
- 以 `original_images.lis` 中影像对应的 cube serial number 为分组基准；
- 对每个 `ControlMeasure` 的 `(sample, line)` 按固定小数位进行 round-hash；
- 如果多个 `ControlPoint` 在任一同影像 serial track 上命中了同一个 rounded hash，则保留**最先出现**的 `ControlPoint`；
- 后续重复点只把其中尚未在目标点中出现过的 measure 追加进去，不改写首个点的 point-level 属性。

默认情况下，如果你不显式提供输出路径，脚本会自动写成：

- `<input_control_net_stem>_merged_measures.net`

例如：

- `dom_matching_merged.net` → `dom_matching_merged_merged_measures.net`

终端会输出一份 JSON 摘要，其中包括：

- 合并前后的 `point_count` / `measure_count`
- 被折叠的重复点数量
- 新增到保留点中的 measure 数量
- 由于目标点中已存在相同 serial 而被跳过的 measure 数量

> 这个脚本默认假设 `original_images.lis` 中的原始 cube 已经完成 `spiceinit`，且 `ISISDATA` 可用于 `SerialNumber.compose()`。如果 serial 号无法构成，脚本会直接报错，而不会悄悄继续。

## 6. 一次跑完整条流水线时，应该检查哪些产物

建议至少按下面顺序检查：

1. `work/images_overlap.lis`
   - 是否确实列出了你预期的候选 pair；

2. `work/dom_keys/*.key`
   - 是否每个 pair 都成功生成了 DOM-space `.key`；

3. `work/match_viz/*.png`
  - 是否出现明显错配、空配对、或者公共范围过小；
  - 这套图对应 **pre-RANSAC** 的 `image_match.py` 输出；

4. `work/match_viz_post_ransac/*.png`
  - 仅在 `run_pipeline_example.sh` 或手工给 `from-dom-batch` 加了 `--write-match-visualization` 时出现；
  - 这套图对应 **post-RANSAC** 的保留匹配，更适合和最终 pairwise ControlNet 对照检查；

5. `work/pair_nets/*.net`
   - pairwise ControlNet 是否非空；

6. `work/reports/*.summary.json`
   - `merge.unique_count`、`ransac.retained_count`、`controlnet.point_count` 是否合理；

7. `work/reports/controlnet_batch_summary.json`
   - batch 汇总统计是否和 per-pair 报告数量一致；

8. `work/merge/merge_all_controlnets.sh`
   - 参与 merge 的 `.net` 列表是否符合预期；

9. `work/merge/dom_matching_merged.net`
   - 最终总网是否成功生成。

## 7. 最小可复制版本

如果你已经具备：

- `work/original_images.lis`
- `work/doms_scaled.lis`
- `examples/controlnet_construct/controlnet_config.example.json`

那么你可以二选一：

1. 直接运行封装好的示例脚本；
2. 或者手工执行下面四段主干命令。

### 一键示例脚本

```bash
bash examples/controlnet_construct/run_pipeline_example.sh
```

这条一键命令默认会生成两套匹配连线图：

- `work/match_viz/`：pre-RANSAC
- `work/match_viz_post_ransac/`：post-RANSAC

如果你想显式覆盖示例配置里的推荐值，也可以直接在脚本命令行上传：

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --valid-pixel-percent-threshold 0.05
```

如果你想显式指定工作目录或先跳过最终 `cnetmerge` 执行，也可以这样：

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir work \
  --skip-final-merge
```

如果你想临时禁用默认 CPU 并行：

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir work \
  --no-parallel-cpu \
  --skip-final-merge
```

### 手工四步版本

### Step 1

```bash
python examples/controlnet_construct/image_overlap.py \
  work/original_images.lis \
  work/images_overlap.lis
```

### Step 2

```bash
VALID_PIXEL_PERCENT_THRESHOLD=0.05

declare -A DOM_BY_ORIGINAL
while IFS=$'\t' read -r original dom; do
  DOM_BY_ORIGINAL["$original"]="$dom"
done < <(paste work/original_images.lis work/doms_scaled.lis)

while IFS=, read -r left right; do
  left_stem=$(basename "${left%.*}")
  right_stem=$(basename "${right%.*}")
  pair_tag="${left_stem}__${right_stem}"

  python examples/controlnet_construct/image_match.py \
    "${DOM_BY_ORIGINAL[$left]}" \
    "${DOM_BY_ORIGINAL[$right]}" \
    "work/dom_keys/${pair_tag}_A.key" \
    "work/dom_keys/${pair_tag}_B.key" \
    --metadata-output "work/match_metadata/${pair_tag}.json" \
    --match-visualization-output-dir work/match_viz \
    --valid-pixel-percent-threshold "$VALID_PIXEL_PERCENT_THRESHOLD"

done < work/images_overlap.lis
```

### Step 3

```bash
python examples/controlnet_construct/controlnet_stereopair.py from-dom-batch \
  work/images_overlap.lis \
  work/original_images.lis \
  work/doms_scaled.lis \
  work/dom_keys \
  examples/controlnet_construct/controlnet_config.example.json \
  work/pair_nets \
  --report-dir work/reports \
  --pair-id-prefix S \
  --pair-id-start 1
```

### Step 4

```bash
python examples/controlnet_construct/controlnet_merge.py \
  work/images_overlap.lis \
  work/pair_nets \
  work/merge/dom_matching_merged.net \
  work/merge/merge_all_controlnets.sh \
  --network-id dom_matching_example \
  --description "Merged DOM matching ControlNet" \
  --log work/merge/cnetmerge.log

bash work/merge/merge_all_controlnets.sh
```

## 8. 相关参考文档

如果你想进一步看需求边界、内部模块拆分或坐标基准约定，可以继续读：

- `examples/controlnet_construct/requirements_dom_matching_controlnet.md`
- `examples/controlnet_construct/plan_architecture_dom_matching_controlnet.md`
- `examples/controlnet_construct/coordinate_conventions.md`

这样，你就可以从“我有一组原图和 DOM 列表”一路走到“我拿到了 merged ControlNet”，中间每一步产物都能对得上号。流水线终于不再是散装零件了。
