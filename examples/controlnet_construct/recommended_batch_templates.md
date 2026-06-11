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
  - 低分辨率粗配准、通过 ISIS `reduce` 生成/复用低分辨率 DOM、投影偏移估计
- `match_visualization.py`
  - `cv2.drawMatches` 可视化、默认 PNG 命名、从 `.key` 文件直接画图
- `tile_matching.py`
  - tile 切分、SIFT、ratio-test、串行/并行匹配、tile 统计结构
- `stereo_ransac.py`
  - 左右 `.key` 的 homography RANSAC 过滤与摘要输出

也就是说，当前用户仍然通过 `image_match.py` 跑第 2 步，但内部实现已经按职责拆分。想改哪一层，就优先改对应模块，而不是下意识继续把所有逻辑往 `image_match.py` 里塞回去。

## 模板 0：LRO NAC Step1 任务导出给 GNU Parallel / orchestrator

如果你当前还在做 LRO NAC 的前处理，而只想跑单个 Step1 阶段，可以先导出命令，再交给 GNU Parallel 批量执行：

```bash
bash examples/controlnet_construct/CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh \
  --input-dir /data/lro/img \
  --step lronac2isis \
  --output-file lronac2isis_batch.txt

cat lronac2isis_batch.txt | parallel -j 8
```

默认 `command` 输出本身**只输出任务命令，不直接执行**，因此单阶段最直接的用法就是让它直接写批处理文件，再交给 `parallel`。`--input-dir` 用来显式指定存放 `.IMG` / `.IMG*` 文件的目录，这样就不需要先 `cd` 到影像目录再生成任务；`--output-file` 则用来直接指定生成的任务文件名。

如果要一次跑多个相互依赖的 Step1 阶段，推荐改用 `--task-format orchestrator` 生成可执行脚本。它会按阶段插入屏障，保证上一阶段完成后才启动下一阶段，并默认每 80 个输入完成全链路后清理一次中间文件：

```bash
bash examples/controlnet_construct/CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh \
  --input-dir /data/lro/img \
  --step all \
  --use-reduce \
  --task-format orchestrator \
  --parallel-jobs 8 \
  --cam2map-resolution 20 \
  --cleanup-batch-size 80 \
  --output-file step1_orchestrator.sh

bash step1_orchestrator.sh
```

极区或大范围影像如果按默认 `--cam2map-resolution 1` 生成 DOM 过大，可以把该值调粗；例如已经 REDUCE 的预览/匹配用 DOM 常用 `--cam2map-resolution 20` 先生成可管理的 CUBE/TIFF。

如果某些 Step1 阶段已经跑过，希望恢复执行时跳过它们，可以传 `--skip-step`。这个参数支持两种写法：

- 重复传多次：`--skip-step lronac2isis --skip-step reduce --skip-step spiceinit`
- 单个参数里逗号分隔：`--skip-step lronac2isis,reduce,spiceinit`

这两种写法也可以混用。

如果你更喜欢直接表达“从哪一步继续”，也可以使用 `--resume-from NAME`。它会自动把该步骤之前的阶段加入跳过列表。这里的模板只保留可直接复制的命令；`--resume-from`、`--include-spiceinit` 和 `--use-reduce` 的完整语义说明，统一以 `examples/controlnet_construct/usage.md` 为准。

如果你希望在 `lronacecho` 之后接入 ISIS `reduce`，并让后续 `spiceinit`、`cam2map`、`isis2std`、`append-lists` 等阶段跟随 `REDUCED_*` echo/cal 产品链，可以开启：

```bash
bash examples/controlnet_construct/CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh \
  --input-dir /data/lro/img \
  --step all \
  --use-reduce \
  --task-format orchestrator \
  --parallel-jobs 8 \
  --cleanup-batch-size 80 \
  --output-file step1_reduced_orchestrator.sh

bash step1_reduced_orchestrator.sh
```

如果你是在断点恢复一个已经做过 `lronac2isis`、`reduce`、`spiceinit` 的目录，可以直接：

```bash
bash examples/controlnet_construct/CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh \
  --input-dir /data/lro/img \
  --step all \
  --use-reduce \
  --include-spiceinit \
  --skip-step lronac2isis,reduce \
  --skip-step spiceinit \
  --task-format orchestrator \
  --parallel-jobs 8 \
  --cleanup-batch-size 80 \
  --output-file step1_resume_orchestrator.sh

bash step1_resume_orchestrator.sh
```

如果你想直接表达“从 spiceinit 继续”，也可以写成：

```bash
bash examples/controlnet_construct/CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh \
  --input-dir /data/lro/img \
  --step all \
  --use-reduce \
  --include-spiceinit \
  --resume-from spiceinit \
  --task-format orchestrator \
  --parallel-jobs 8 \
  --cleanup-batch-size 80 \
  --output-file step1_resume_from_spiceinit.sh

bash step1_resume_from_spiceinit.sh
```

如果使用 `--resume-from spiceinit`，输出里会额外包含 `isis2std-spiced`，用于在 `cam2map` 前导出 `REDUCED_<name>.tif` 或 `<name>.tif`；而 `spiceinit` 命令本身只有在同时传入 `--include-spiceinit` 时才会被重新导出。

此时命令链会变成：

- `lronac2isis ... -> <name>.cub`
- `lronaccal ... -> <name>.cal.cub`
- `lronacecho ... -> <name>.echo.cal.cub`
- `reduce ... -> REDUCED_<name>.echo.cal.cub`
- 后续基于 `REDUCED_<name>.echo.cal.cub`
- 例如后续产物会变成 `REDUCED_<name>.tif`、`dom_REDUCED_<name>.cub`

如果**不**传 `--use-reduce`，则 `reduce` 不会自动插入到 `--step all` 链中，后续仍然沿用原始 `<name>.echo.cal.cub` 版本。

### 模板：只导出 working cube 的 TIFF

```bash
bash examples/controlnet_construct/CONTROLNET_Step1_LRONAC_spiceinit_cal_echo_batch.sh \
  --input-dir /data/lro/img \
  --step isis2std-spiced \
  --use-reduce \
  --output-file step1_spiced_tif_batch.txt

cat step1_spiced_tif_batch.txt | parallel -j 8
```

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

如果配置或命令行启用了低分辨率粗配准，脚本会先把当前 DOM 列表一次性降采样到 `work/low_resolution_doms/level<N>/`，并写出对齐列表 `work/doms_low_resolution_level<N>.lis`。后续同一景 DOM 参与多个 pair 时直接复用这个缓存，再复制到各自 pair 的诊断目录，不会反复调用 `reduce`。这条链路使用 ISIS `reduce`；`dom_prepare.py` 的 GSD 归一化仍然使用 `gdal_translate -tr`。

如果你希望把推荐参数直接固化进配置文件，可以这样写：

从当前版本开始，`image_match.py` 本身也支持 `--config`，会把配置里的 `ImageMatch` 段当作默认匹配参数；两个推荐批处理脚本也会把这段配置继续转发进去。因此你现在可以把常用的 tile、overlap、灰度拉伸、SIFT、crop、并行和可视化参数统一写在这里，而不只是写阈值和 worker 数。若启用 adaptive routing，可用 `adaptive_routing_profile` 在 `balanced`、`strict`、`relaxed`、`fast` 之间切换质量门控策略；运行 metadata 会记录 profile 展开后的阈值，方便复查。

```json
{
  "NetworkId": "dom_matching_example",
  "TargetName": "Moon",
  "UserName": "gengxun",
  "PointIdPrefix": "P",
  "ImageMatch": {
    "band": 1,
    "max_image_dimension": 1024,
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
    "enable_adaptive_routing": false,
    "adaptive_routing_profile": "balanced",
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

默认 SIFT 匹配使用 BF。只有在做旧版 CPU FLANN 对照实验时，才需要显式切换：

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

批量匹配阶段默认使用统一的 SIFT+BF 路线。旧版 CPU FLANN 对照实验可以显式传：

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
  --max-image-dimension 1024 \
  --sub-block-size-x 1024 \
  --sub-block-size-y 1024 \
  --overlap-size-x 192 \
  --overlap-size-y 192
```

如果你不想通过批处理脚本中转，也可以直接把同一份配置 JSON 传给 `image_match.py`：

```bash
python examples/image_match/image_match.py \
  --config examples/controlnet_construct/controlnet_config.example.json \
  left_dom.cub right_dom.cub left.key right.key
```

同理，如果你希望在只跑批量匹配时顺手关闭默认 PNG 输出，也可以在这个透传区里附加 `--no-write-match-visualization`。

## 模板 3A：official deep matcher presets

推荐控制网构建里的 learned matching preset 先收敛到这两个入口：

```text
examples/controlnet_construct/presets/lightglue_official_superpoint.json
examples/controlnet_construct/presets/loftr_external_outdoor.json
```

`loftr_default.json` is the Kornia compatibility preset; use `loftr_external_outdoor.json` or `loftr_external_indoor.json` for the official LoFTR repository/checkpoint route.

如果你需要 raw/original image adaptive routing，可以把它们作为路由候选：

```bash
bash examples/controlnet_construct/run_ori_match_pipeline_example.sh \
  --work-dir work_ori \
  --original-list work/original_images.lis \
  --config examples/controlnet_construct/controlnet_config.example.json \
  --matcher-method bf \
  --adaptive-routing \
  --adaptive-routing-deep-preset lightglue=examples/controlnet_construct/presets/lightglue_official_superpoint.json \
  --adaptive-routing-deep-preset loftr=examples/controlnet_construct/presets/loftr_external_outdoor.json
```

## 模板 3B：跨 conda deep-match handoff

如果你想在 `controlnet_construct` 批量流程中使用 official LightGlue / external LoFTR，但这些深度学习依赖只安装在 `deep-learning` conda 环境中，**推荐使用一键包装脚本**，它会自动完成三段式 handoff（export → deep-learning → import），不需要你手动切 conda 环境。

### 推荐方式：一键包装脚本

完整流水线（export → deep-learning 批量匹配 → import → ControlNet）：

```bash
bash examples/controlnet_construct/run_deep_match_pipeline.sh \
  --work-dir work \
  --matcher-method lightglue
```

仅 deep-match 段（不跑 ControlNet 后续步骤）：

```bash
bash examples/controlnet_construct/run_deep_match_pipeline.sh \
  --mode deep-match-only \
  --work-dir work \
  --matcher-method loftr
```

恢复中断的流程（例如 deep-learning 已跑完，直接从 import 继续）：

```bash
bash examples/controlnet_construct/run_deep_match_pipeline.sh \
  --work-dir work \
  --matcher-method lightglue \
  --resume-from import
```

容错模式（某个像对失败后继续 import 已成功的结果）：

```bash
bash examples/controlnet_construct/run_deep_match_pipeline.sh \
  --work-dir work \
  --matcher-method lightglue \
  --continue-on-deep-failure
```

包装脚本通过 `conda run -n <env>` 切换环境，支持自定义环境名（`--asp360-env` / `--deep-learning-env`）、设备选择（`--device`）、跳过已有结果（`--skip-existing`）等。完整选项见 `--help`。

### 手工三段式（fallback）

如果你想手动控制每一步，三段式 handoff 仍然是：

1. 在 `asp360_new` 中导出 manifest workspace：

```bash
bash examples/controlnet_construct/run_image_match_batch_example.sh \
  --work-dir work \
  --matcher-method lightglue \
  --deep-match-mode export \
  --deep-match-temp-root-dir work/deep_match_workspaces \
  --deep-match-manifest-summary work/deep_match_manifests.json \
  -- \
  --no-write-match-visualization
```

2. 切换到 `deep-learning`，执行 `examples/learning_methods/run_deep_match_manifest.py`：

```bash
python examples/learning_methods/run_deep_match_manifest.py \
  work/deep_match_workspaces/<pair-id>/tasks.json \
  --device auto
```

3. 回到 `asp360_new`，用 import 模式生成 `.key`，再继续 ControlNet：

```bash
bash examples/controlnet_construct/run_image_match_batch_example.sh \
  --work-dir work \
  --matcher-method lightglue \
  --deep-match-mode import \
  --deep-match-manifest-dir work/deep_match_workspaces
```

端到端脚本也支持同样选项。注意：`--deep-match-mode export` 会在完成 `image_match_batch` 后停止，因为 export 模式只写 manifest，不生成后续 `controlnet_stereopair.py` 需要的最终 `.key` 文件：

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir work \
  --matcher-method lightglue \
  --deep-match-mode export
```

完成 deep-learning 阶段后再继续完整流水线：

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir work \
  --matcher-method lightglue \
  --deep-match-mode import \
  --deep-match-manifest-dir work/deep_match_workspaces
```

更底层的 manifest schema、`.npz` 字段和坐标约定见 `examples/learning_methods/README.md`。

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

## 输出风格小抄

这几个入口现在都尽量按“**终端摘要、文件存详情**”来组织输出：

- `run_pipeline_example.sh`
  - 终端：只看步骤进度和一句摘要；
  - 文件：细节 JSON 在 `work/reports/` 与 `work/match_results/`。
- `run_image_match_batch_example.sh`
  - 终端：默认只看批处理进度和 pair 级简短提示，不在 wrapper 层额外展开大块 JSON；
  - 文件：每对详细诊断默认写到 `work/match_metadata/`，若你直接调用 `image_match.py` 或通过 `--` 继续转发，也可配合 `--result-output` 单独落完整 JSON。

如果你单独直接调用别的入口，也有同样的显式开关：

- `image_overlap.py`
  - 默认 stdout 只给计数和 bounds 统计；
  - `--report-json PATH` 落完整 overlap JSON；
  - `--include-bounds` 可把 per-image bounds 重新打回终端。
- `merge_control_measure.py`
  - 默认 stdout 不打印完整 `merged_point_ids`；
  - `--report-json PATH` 落完整 post-merge JSON；
  - `--include-detail-records` 可把 detail records 重新打回终端。

如果你是批量调参，建议把终端当“仪表盘”，把这些文件当“黑匣子”：

- `work/reports/image_overlap_summary.json`
- `work/match_results/<pair_tag>.json`
- `work/reports/controlnet_batch_summary.json`
- `work/reports/controlnet_merge_summary.json`
- `work/reports/merge_control_measure_summary.json`（启用 post-merge 时）

这样一来，跑批时不会被一屏一屏 JSON 淹没，但真要复盘时也不会丢细节。
