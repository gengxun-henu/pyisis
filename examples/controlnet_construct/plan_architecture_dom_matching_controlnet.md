# DOM Matching ControlNet 实施计划与架构

> 本文件与 `examples/controlnet_construct/requirements_dom_matching_controlnet.md` 配套使用。
> 目标不是产出一个“左右图直接匹配的简化 MVP”，而是按需求文档落地一条 **DOM GSD 归一化 → 投影公共范围裁剪 → DOM 上 SIFT 匹配 → DOM 点去重 → DOM→原图回投 → 单立体像对 ControlNet 输出 → 全局 cnetmerge 脚本生成** 的可实施开发路径。

## 实施原则

1. **严格以需求文档为准**，不再擅自改写技术路线；
2. 主匹配算法固定为 **OpenCV SIFT**；
3. 外部工作流按 CLI 工具串联，但内部实现尽量共享模块；
4. 裁剪偏移通过 sidecar 元数据承载，不破坏既有 `.key` 交换格式；
5. per-pair 统计与 batch summary 应优先使用稳定 JSON 结构，便于回归比较；
6. 采用 TDD，小步实现、小步验证，避免长时间不可运行；
7. 每个阶段都应保持代码可解释、接口可冻结、日志可检查。

## 总体架构

### 外部工作流

```text
original_images.lis
      │
      ▼
 image_overlap.py
      │
      ▼
 images_overlap.lis + doms.lis
      │
      ▼
  dom_prepare.py
      │
      ▼
images_gsd.txt + doms_scaled.lis
      │
      ▼
  image_match.py
      │
      ▼
DOM 空间 .key 文件 + 裁剪 sidecar
      │
      ▼
tie_point_merge_in_overlap.py
      │
      ▼
去重后的 DOM 空间 .key 文件
      │
      ▼
    dom2ori.py
      │
      ▼
原始影像空间 .key 文件
      │
      ▼
controlnet_stereopair.py
      │
      ▼
pairwise ISIS ControlNet + per-pair JSON
      │
      ▼
controlnet_merge.py
      │
      ▼
merge_all_controlnets.sh + merged ControlNet + batch summary JSON
```

### 内部模块划分

建议在 `examples/controlnet_construct/` 对应实现区域中按职责拆分共享模块。模块名可根据最终代码组织微调，但职责边界建议固定：

1. `io/listing.py`
  - 读取 `original_images.lis`、`doms.lis`、`images_overlap.lis`；
  - 负责相对路径解析、配对校验、错误提示。

2. `image/preprocess.py`
  - CUBE 数据读取；
  - 非 BYTE 影像灰度拉伸到 `0–255`；
  - 百分位拉伸与手工范围拉伸；
  - 无效值/特殊像元掩膜生成。

3. `image/dom_prepare.py`
  - 读取 DOM 投影与 GSD；
  - 生成 `images_gsd.txt`；
  - 以全局平均 GSD 做重采样决策；
  - 输出 `doms_scaled.lis`；
  - 计算投影公共范围与外扩裁剪窗口；
  - 写出 sidecar 偏移元数据。

4. `image/tiling.py`
  - 按阈值判断是否分块；
  - 生成带重叠边的子块窗口；
  - 记录子块到裁剪图与原图的起始偏移；
  - 将子块坐标回拼到原始 DOM 整图坐标。

5. `match/sift_match.py`
  - 对单景或单对子块执行 SIFT；
  - 负责描述子匹配与基础筛选；
  - 输出 DOM 空间匹配点。

6. `keypoints/io.py`
  - `.key` 文件读写；
  - 文件头与点数量校验；
  - 顺序一致性检查。

7. `keypoints/merge.py`
  - 按小数点后三位 HASH 去重；
  - 输出去重前后统计。

8. `projection/dom2ori.py`
  - 封装基于 `isis_pybind` 的 DOM→原始影像坐标转换；
  - 统一管理转换失败原因与日志。

9. `controlnet/build.py`
  - 根据原始影像空间 `.key` 文件构建 ControlNet；
  - 写出 PVL 或二进制控制网；
  - 维护 point id、网络元数据与来源信息；
  - 可选输出 per-pair JSON sidecar。

10. `controlnet/merge.py`
  - 根据 `image_overlap.lis` 和 pairwise `.net` 生成 `cnetmerge` 输入列表；
  - 自动生成整体 merge shell 脚本；
  - 记录缺失 pairwise `.net` 的跳过清单；
  - 聚合 per-pair JSON 为 batch summary JSON。

11. `common/logging.py` / `common/config.py`
  - 统一 CLI 参数解析后的配置对象；
  - 输出统计与失败原因；
  - 便于集成测试复现参数。

### CLI 与共享库的边界

每个 CLI 脚本只负责：

1. 解析命令行参数；
2. 调用共享模块；
3. 输出日志、统计与结果文件；
4. 返回可测试的退出状态。

每个 CLI 脚本不应重复实现：

- GSD 统计与重采样决策；
- 投影公共范围裁剪；
- CUBE 灰度拉伸；
- 无效值判定；
- 分块逻辑；
- `.key` 文件读写；
- `cnetmerge` 列表与 shell 生成；
- per-pair JSON 与 batch summary JSON 结构；
- 失败统计格式。

## 分阶段实施计划

### Phase 0：需求冻结与接口草图

目标：先把“做什么”钉牢，防止后续实现阶段跑偏。

工作内容：

1. 冻结 CLI 工具名与职责；
2. 明确所有输入输出文件名约定；
3. 冻结关键参数：
  - `--sub_block_size_x`
  - `--sub_block_size_y`
  - `--overlap_size_x`
  - `--overlap_size_y`
  - `--crop_expand_pixels`
  - `--min_overlap_size`
  - `--tolerance_ratio`
  - 灰度拉伸范围参数
  - ControlNet 元数据参数
4. 明确 `shapemodel` 一致性约束在接口层如何表达；
5. 建立最小测试骨架。

完成标志：

- 需求与计划文档稳定；
- CLI 参数表初稿完成；
- 最小测试目录与模块名确定。

### Phase 1：共享基础模块骨架

目标：先把公共积木搭起来，让后续 CLI 只拼装不造轮子。

工作内容：

1. 完成列表读取与路径解析；
2. 完成 `.key` 文件对象模型与读写接口；
3. 完成日志与统计结果结构；
4. 定义 per-pair JSON 与 batch summary JSON 字段口径；
5. 定义分块窗口数据结构；
6. 定义无效值掩膜、灰度拉伸配置对象；
7. 搭建 `isis_pybind` 几何转换包装接口；
8. 定义 DOM GSD 记录与裁剪 sidecar 数据结构。

优先测试：

- `.lis` 文件读取；
- `.key` 文件读写往返；
- 参数对象校验；
- sidecar 元数据 round-trip。

### Phase 2：`image_overlap.py`

目标：先把立体像对列表跑通，因为后续所有步骤都依赖它。

工作内容：

1. 读取 `original_images.lis`；
2. 计算两两重叠关系；
3. 使用无向对去重；
4. 输出 `images_overlap.lis`。

优先测试：

- 重叠对唯一性；
- `A,B` 与 `B,A` 去重；
- 空输入与异常输入处理。

### Phase 3：`dom_prepare.py`

目标：在进入匹配前统一 DOM 分辨率、记录 GSD，并把 pair 级裁剪窗口固定下来。

工作内容：

1. 读取 `doms.lis`；
2. 统计每景 DOM 的 GSD；
3. 输出 `images_gsd.txt`；
4. 以全局平均 GSD 作为目标分辨率；
5. 对超出容差的 DOM 生成 `gdal_translate` 重采样结果；
6. 输出 `doms_scaled.lis`；
7. 提供 pair 级公共投影范围与外扩裁剪窗口计算能力。

优先测试：

- GSD 统计正确；
- 平均 GSD 目标计算正确；
- 超容差时命令生成正确；
- dry-run 不执行外部命令但仍产出清单与摘要。

### Phase 4：`image_match.py`

目标：完成 DOM 上的 SIFT 主匹配链路，这是整个流程的核心阶段。

工作内容：

1. 对一对 DOM 读取 pair 级裁剪元数据；
2. 根据投影公共范围生成左右裁剪窗口；
3. 以默认 `100` 像素外扩公共范围；
4. 若裁剪后宽或高小于默认 `16` 像素，则返回 `skipped_small_overlap`；
5. 对有效窗口判断是否超过 `3000 x 3000` 阈值；
6. 若需要，则按 `1024 x 1024` 默认块大小与 `128` 默认重叠边生成子块；
7. 对每个子块完成：
  - 灰度映射；
  - 无效值掩膜；
  - SIFT 特征提取与匹配；
  - 子块坐标回拼到裁剪图坐标；
  - 再恢复到原始 DOM 整图坐标；
8. 输出 DOM 空间 `.key` 文件与裁剪 sidecar。

必须明确的实现要点：

1. 百分位拉伸统计时排除特殊像元与 `NaN/Inf`；
2. 当块内有效像素过少时允许跳过；
3. 失败日志要区分“无效值过多”“纹理不足”“匹配为空”；
4. 当前阶段不做块间重复点消解，只做原样汇总；
5. `.key` 中保存的仍是原始 DOM 整图坐标。

优先测试：

- 拉伸结果落在 `0–255`；
- 手工灰度范围覆盖默认百分位逻辑；
- 子块偏移回拼正确；
- 无效值块被正确跳过；
- 小重叠被正确跳过；
- sidecar 记录的裁剪偏移与窗口尺寸正确。

### Phase 5：`tie_point_merge_in_overlap.py`

目标：解决单个立体像对内部因块重叠导致的重复点问题。

工作内容：

1. 读取 `image_match.py` 输出的 DOM 空间 `.key` 文件；
2. 将点坐标格式化到小数点后三位；
3. 以坐标字符串构造 HASH；
4. 检测并合并重复点；
5. 输出去重后的 `.key` 文件与统计。

优先测试：

- 三位小数 HASH 行为；
- 重复点被合并；
- 非重复点保持顺序。

### Phase 6：`dom2ori.py`

目标：把 DOM 空间同名点可靠回投到原始影像空间。

工作内容：

1. 读取 DOM 空间 `.key` 文件；
2. 需要时读取裁剪 sidecar 以辅助调试；
3. 打开对应 DOM 与原始 CUBE；
4. 借助 `isis_pybind` 完成坐标转换；
5. 对转换失败点分类；
6. 输出原始影像空间 `.key` 文件。

关键风险：

1. DOM 与原始影像不一致；
2. 由于 `shapemodel` 不一致导致几何反算失败；
3. 点反投影后超出原始影像范围。

优先测试：

- 成功点顺序保持一致；
- 失败点被正确记录；
- 输出文件数量与内容自洽。

### Phase 7：`controlnet_stereopair.py`

目标：根据原始影像空间连接点生成单个立体像对 ControlNet。

工作内容：

1. 读取 `ori_A.key` 与 `ori_B.key`；
2. 读取 `NetworkId`、`TargetName`、`UserName`；
3. 校验 `TargetName` 配置来源；
4. 用 `isis_pybind` 构建 ControlNet / ControlPoint / ControlMeasure；
5. 支持 PVL 或二进制格式写盘；
6. 支持输出 per-pair JSON sidecar。

优先测试：

- 必填元数据缺失时报错；
- 点数与 measure 数量一致；
- 输出 ControlNet 文件可生成。

### Phase 8：`controlnet_merge.py`

目标：把多个立体像对的 `.net` 汇总到一个整体控制网，避免人工逐条敲 `cnetmerge`。

工作内容：

1. 读取 `image_overlap.lis`；
2. 查找每个 pair 对应的 `.net` 是否已经生成；
3. 自动生成 `cnetmerge` 使用的控制网列表文件；
4. 自动生成 merge shell 脚本；
5. 对缺失的 pairwise `.net` 记录跳过清单；
6. 聚合所有 per-pair JSON 为 batch summary JSON。

优先测试：

1. 列表文件顺序与 `image_overlap.lis` 一致；
2. 缺失 `.net` 时默认跳过且有摘要；
3. 输出 shell 脚本可执行且命令参数完整。

### Phase 9：端到端样例与回归验证

目标：确保从列表输入到控制网输出的完整链路可跑通。

工作内容：

1. 准备最小化测试数据；
2. 从 `original_images.lis` 与 `doms.lis` 开始跑完整流程；
3. 校验中间产物是否符合预期：
  - `images_overlap.lis`
  - `images_gsd.txt`
  - `doms_scaled.lis`
  - DOM 空间 `.key`
  - 裁剪 sidecar
  - 去重后 `.key`
  - 原始影像空间 `.key`
  - pairwise `.net`
  - per-pair JSON
  - merge shell
  - batch summary JSON
4. 补充 usage 文档与示例说明。

## 数据与错误流设计

### 数据流

1. 影像列表层：`original_images.lis`、`doms.lis`
2. DOM 预处理层：`images_gsd.txt`、`doms_scaled.lis`
3. 像对层：`images_overlap.lis`
4. 匹配层：DOM 空间 `.key` + 裁剪 sidecar
5. 去重层：去重后的 DOM 空间 `.key`
6. 几何层：原始影像空间 `.key`
7. 网络层：pairwise ISIS ControlNet + per-pair JSON
8. 汇总层：merge shell + batch summary JSON

### 错误分类

建议统一错误码或错误类别，至少覆盖：

1. 输入文件不存在；
2. 列表配对不一致；
3. DOM/原始影像映射关系不一致；
4. `shapemodel` 前提不满足；
5. GSD 不一致且重采样失败；
6. 投影公共范围为空；
7. 外扩后重叠窗口过小；
8. 子块有效像素不足；
9. SIFT 无特征或无匹配；
10. `.key` 文件非法；
11. DOM→原图回投失败；
12. ControlNet 元数据缺失；
13. ControlNet 写盘失败；
14. merge shell 或 pairwise `.net` 清单生成失败；
15. per-pair JSON 命名或字段不一致导致 batch 汇总失败。

## 测试策略

### 单元测试

优先给以下模块写 focused unit test：

1. `.lis` 列表解析；
2. `.key` 文件读写；
3. 百分位拉伸与手工拉伸；
4. 无效值掩膜；
5. GSD 报告输出与阈值判断；
6. 投影公共范围裁剪与偏移回拼；
7. 分块窗口生成；
8. 三位小数 HASH 去重；
9. `cnetmerge` shell 生成；
10. per-pair JSON 与 batch summary JSON 聚合。

### 集成测试

1. `dom_prepare.py`：验证真实 DOM 能正确读取 GSD 与投影范围；
2. `dom2ori.py`：依赖 `asp360_new` + `isis_pybind` 的几何能力；
3. `controlnet_stereopair.py`：依赖 `isis_pybind` 的 ControlNet 能力。

### 端到端测试

至少保留一个最小 smoke 流程，从输入列表一直到 `.net` 输出，重点验证：

1. 各阶段文件都能生成；
2. 去重后点数合理；
3. 最终 pairwise 控制网非空；
4. merge shell 能解释哪些 pair 被纳入、哪些被跳过；
5. batch summary JSON 数值与 per-pair 汇总一致；
6. 日志能解释失败点来源。

## 当前明确不做的内容

为控制首轮实现复杂度，以下内容本计划明确不纳入当前阶段：

1. 并行化分块调度；
2. 跨多个立体像对的全局点去重；
3. 基于相关匹配的二次精化或亚像素细化；
4. 为该示例新增新的底层 C++ pybind 绑定，除非后续实现被现有 `isis_pybind` 能力阻塞。

## 交付里程碑

1. **M1：文档与接口冻结**
  - 需求与计划确定；
  - CLI 参数草图确定。

2. **M2：共享模块 + 前半流程可运行**
  - `image_overlap.py`
  - `dom_prepare.py`
  - `image_match.py`
  - `tie_point_merge_in_overlap.py`

3. **M3：几何回投与控制网生成可运行**
  - `dom2ori.py`
  - `controlnet_stereopair.py`

4. **M4：整体合网辅助与验证闭环**
  - `controlnet_merge.py`
  - focused unit tests
  - 最小端到端 smoke
  - usage 文档补齐
