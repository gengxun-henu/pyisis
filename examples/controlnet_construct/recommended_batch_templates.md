# DOM Matching 推荐批处理模板

这份文档把 `examples/controlnet_construct/` 里最常用的批处理入口收敛成几段可复用 snippet，目标很直接：**少翻文档，直接复制，先跑起来**。

从当前版本开始，两个推荐入口脚本还共享三个新的默认行为：

- 默认开启 CPU 分块并行匹配；只有显式传 `--no-parallel-cpu` 时才回退到串行 tile 匹配；
- 默认把 CPU 进程池 worker 上限设为 `8`；可用 `--num-worker-parallel-cpu` 改到 `1~4096`；
- 默认输出匹配连线可视化 PNG，不再需要额外手工打开可视化开关。

其中可视化目录约定要特别注意：

- `work/match_viz/`：保存 `image_match.py` 直接输出的 **pre-RANSAC** 连线图；
- `work/match_viz_post_ransac/`：保存 `controlnet_stereopair.py from-dom-batch` 输出的 **post-RANSAC** 连线图；这个目录默认只会在整条流水线脚本 `run_pipeline_example.sh` 中生成。

如果你只记一个推荐值，先记这个：

- `valid_pixel_percent_threshold = 0.05`

它的含义是：当某个 tile 的有效像素比例低于 $5\%$ 时，直接跳过该 tile，不做 SIFT 匹配。

这通常适合：

- DOM 有效区域只占整幅影像的一小部分
- 影像四角或边界有大量 0 / 无效背景
- 想减少“几乎全空 tile”带来的无效匹配开销

## 维护者补充：`image_match.py` 现在只是 façade

如果你是来复制命令的，这一节可以直接跳过。

如果你是来维护 `examples/controlnet_construct/` 的，这里给一个短版结构图：

- `image_match.py`
  - 公开 CLI / 参数解析 / 编排层 / 兼容入口
- `lowres_offset.py`
  - 低分辨率粗配准、`reduce` 生成低分辨率 DOM、投影偏移估计
- `match_visualization.py`
  - `cv2.drawMatches` 可视化、默认 PNG 命名、从 `.key` 文件直接画图
- `tile_matching.py`
  - tile 切分、SIFT、ratio-test、串行/并行匹配、tile 统计结构
- `stereo_ransac.py`
  - 左右 `.key` 的 homography RANSAC 过滤与摘要输出

也就是说，当前用户仍然通过 `image_match.py` 跑第 2 步，但内部实现已经按职责拆分。想改哪一层，就优先改对应模块，而不是下意识继续把所有逻辑往 `image_match.py` 里塞回去。

## 模板 1：整条流水线直接跑

如果你已经准备好了：

- `work/original_images.lis`
- `work/doms_scaled.lis` 或 `work/doms.lis`
- `examples/controlnet_construct/controlnet_config.example.json`

优先推荐用整条流水线脚本：

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir work \
  --skip-final-merge
```

这条模板命令默认还会：

- 开启 CPU 分块并行匹配；
- 默认把 CPU 进程池 worker 上限设为 `8`；
- 把 pre-RANSAC 连线图写到 `work/match_viz/`；
- 把 post-RANSAC 连线图写到 `work/match_viz_post_ransac/`。

如果你希望把推荐参数直接固化进配置文件，可以这样写：

从当前版本开始，`image_match.py` 本身也支持 `--config`，会把配置里的 `ImageMatch` 段当作默认匹配参数；两个推荐批处理脚本也会把这段配置继续转发进去。因此你现在可以把常用的 tile、overlap、灰度拉伸、SIFT、crop、并行和可视化参数统一写在这里，而不只是写阈值和 worker 数。

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
    "minimum_value": null,
    "maximum_value": null,
    "lower_percent": 0.5,
    "upper_percent": 99.5,
    "invalid_values": [],
    "special_pixel_abs_threshold": 1e300,
    "min_valid_pixels": 64,
    "valid_pixel_percent_threshold": 0.05,
    "matcher_method": "bf",
    "ratio_test": 0.75,
    "max_features": null,
    "sift_octave_layers": 3,
    "sift_contrast_threshold": 0.04,
    "sift_edge_threshold": 10.0,
    "sift_sigma": 1.6,
    "crop_expand_pixels": 100,
    "min_overlap_size": 16,
    "use_parallel_cpu": true,
    "num_worker_parallel_cpu": 8,
    "low_resolution_max_mean_reprojection_error_pixels": 3.0,
    "write_match_visualization": true,
    "match_visualization_scale": 0.3333333333333333
  }
}
```

如果你在脚本命令行里又显式传了某个 `image_match.py` 参数，例如 `--ratio-test 0.8` 或 `--num-worker-parallel-cpu 4`，则命令行值会覆盖配置文件里的默认值。

如果你想显式覆盖阈值，直接传：

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir work \
  --valid-pixel-percent-threshold 0.05 \
  --skip-final-merge
```

如果你想临时关闭默认 CPU 并行，可以改成：

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir work \
  --no-parallel-cpu \
  --skip-final-merge
```

如果你想显式把 worker 上限改成 4，可以直接：

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir work \
  --num-worker-parallel-cpu 4 \
  --skip-final-merge
```

如果你想把 SIFT 描述子匹配切换为 FLANN，可以直接：

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir work \
  --matcher-method flann \
  --skip-final-merge
```

## 模板 2：只跑第 2 步批量 DOM 匹配

如果你当前只想专注在 `image_match.py` 这一段，而不想整条流水线都执行，推荐用单独的批处理脚本：

```bash
bash examples/controlnet_construct/run_image_match_batch_example.sh \
  --work-dir work \
  --valid-pixel-percent-threshold 0.05
```

如果你希望它从配置里自动读取阈值和 worker 上限：

```bash
bash examples/controlnet_construct/run_image_match_batch_example.sh \
  --work-dir work \
  --config examples/controlnet_construct/controlnet_config.example.json
```

现在这条命令不只是读取阈值和 worker 上限，而是会把配置文件里的整段 `ImageMatch` 默认值一起转发给 `image_match.py`；如果你把 tile 大小、overlap、SIFT 或可视化参数也写进配置文件，这里同样会生效。

这个脚本默认会：

- 读取 `work/original_images.lis`
- 优先读取 `work/doms_scaled.lis`，不存在时回退到 `work/doms.lis`
- 读取 `work/images_overlap.lis`
- 开启 CPU 分块并行匹配
- 默认把 CPU 进程池 worker 上限设为 `8`
- 输出 **pre-RANSAC** 匹配连线图
- 输出到：
  - `work/dom_keys/`
  - `work/match_metadata/`
  - `work/match_viz/`

如果你想在批量匹配阶段显式切换 SIFT 描述子匹配后端，也可以直接传：

```bash
bash examples/controlnet_construct/run_image_match_batch_example.sh \
  --work-dir work \
  --matcher-method flann
```

如果你已经启用了低分辨率粗配准，还可以继续限制其可接受的 trimmed-mean 重投影误差：

```bash
bash examples/controlnet_construct/run_image_match_batch_example.sh \
  --work-dir work \
  --enable-low-resolution-offset-estimation \
  --low-resolution-level 3 \
  --low-resolution-max-mean-reprojection-error-pixels 2.5
```

如果你想显式开启默认 CPU 并行标志：

```bash
bash examples/controlnet_construct/run_image_match_batch_example.sh \
  --work-dir work \
  --use-parallel-cpu
```

如果你想关闭默认 CPU 并行：

```bash
bash examples/controlnet_construct/run_image_match_batch_example.sh \
  --work-dir work \
  --no-parallel-cpu
```

如果你想把批量匹配阶段限制为最多 4 个 worker：

```bash
bash examples/controlnet_construct/run_image_match_batch_example.sh \
  --work-dir work \
  --num-worker-parallel-cpu 4
```

如果你想关闭这套默认的 pre-RANSAC 连线图，可以把参数继续透传给 `image_match.py`：

```bash
bash examples/controlnet_construct/run_image_match_batch_example.sh \
  --work-dir work \
  --valid-pixel-percent-threshold 0.05 \
  -- \
  --no-write-match-visualization
```

## 模板 3：给 `image_match.py` 继续透传更多参数

如果你除了阈值，还想继续调 `ratio-test`、tile 大小或 overlap，可在脚本后面通过 `--` 继续透传给 `image_match.py`：

```bash
bash examples/controlnet_construct/run_image_match_batch_example.sh \
  --work-dir work \
  --config examples/controlnet_construct/controlnet_config.example.json \
  --valid-pixel-percent-threshold 0.05 \
  -- \
  --ratio-test 0.8 \
  --sub-block-size-x 1536 \
  --sub-block-size-y 1536 \
  --overlap-size-x 192 \
  --overlap-size-y 192
```

如果你不想通过批处理脚本中转，也可以直接把同一份配置 JSON 传给 `image_match.py`：

```bash
python examples/controlnet_construct/image_match.py \
  --config examples/controlnet_construct/controlnet_config.example.json \
  left_dom.cub right_dom.cub left.key right.key
```

同理，如果你希望在只跑批量匹配时顺手关闭默认 PNG 输出，也可以在这个透传区里附加 `--no-write-match-visualization`。

## 快速调参建议

### 从 `0.05` 调大

当你发现：

- 仍然有很多几乎全空的 tile 在耗时
- 可视化结果里大量 tile 没有实际纹理

可以尝试：

- `0.08`
- `0.1`

### 从 `0.05` 调小

当你发现：

- 有效覆盖本来就比较窄
- 过多 tile 被跳过，担心漏掉边缘有效区域

可以尝试：

- `0.03`

## 一句话建议

- **第一次跑**：先用 `0.05`
- **背景无效区域特别多**：试 `0.08 ~ 0.1`
- **有效覆盖本来就稀薄**：试 `0.03`

## 相关入口

- 端到端说明：`examples/controlnet_construct/usage.md`
- 整条流水线脚本：`examples/controlnet_construct/run_pipeline_example.sh`
- 批量 DOM 匹配脚本：`examples/controlnet_construct/run_image_match_batch_example.sh`

如果你对两套可视化目录还想看更完整的解释，优先查看 `examples/controlnet_construct/usage.md` 中关于 `work/match_viz/` 和 `work/match_viz_post_ransac/` 的说明。
