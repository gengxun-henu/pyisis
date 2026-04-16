# DOM Matching ControlNet 实施计划与架构

> 本文件与 `examples/controlnet_construct/requirements_dom_matching_controlnet.md` 配套使用。
> 目标不是产出一个“左右图直接匹配的简化 MVP”，而是按需求文档落地一条 **DOM 上 SIFT 匹配 → DOM 点去重 → DOM→原图回投 → 单立体像对 ControlNet 输出** 的可实施开发路径。

## 实施原则

1. **严格以需求文档为准**，不再擅自改写技术路线；
2. 主匹配算法固定为 **OpenCV SIFT**；
3. 外部工作流保持为 6 个 CLI 程序；
4. 内部实现采用“共享库 + 6 个 CLI 脚本”以减少重复；
5. 采用 TDD，小步实现、小步验证，避免长时间不可运行；
6. 每个阶段都应保持代码可解释、接口可冻结、日志可检查。

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
  image_match.py
      │
      ▼
DOM 空间 .key 文件
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
ISIS ControlNet
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

3. `image/tiling.py`
  - 按阈值判断是否分块；
  - 生成带重叠边的子块窗口；
  - 记录子块到整图的起始偏移；
  - 将子块坐标回拼到整图坐标。

4. `match/sift_match.py`
  - 对单景或单对子块执行 SIFT；
  - 负责描述子匹配与基础筛选；
  - 输出 DOM 空间匹配点。

5. `keypoints/io.py`
  - `.key` 文件读写；
  - 文件头与点数量校验；
  - 顺序一致性检查。

6. `keypoints/merge.py`
  - 按小数点后三位 HASH 去重；
  - 输出去重前后统计。

7. `projection/dom2ori.py`
  - 封装基于 `isis_pybind` 的 DOM→原始影像坐标转换；
  - 统一管理转换失败原因与日志。

8. `controlnet/build.py`
  - 根据原始影像空间 `.key` 文件构建 ControlNet；
  - 写出 PVL 或二进制控制网；
  - 维护 point id、网络元数据与来源信息。

9. `common/logging.py` / `common/config.py`
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

- CUBE 灰度拉伸；
- 无效值判定；
- 分块逻辑；
- `.key` 文件读写；
- 失败统计格式。

## 分阶段实施计划

### Phase 0：需求冻结与接口草图

目标：先把“做什么”钉牢，防止后续实现阶段跑偏。

工作内容：

1. 冻结 6 个 CLI 工具名与职责；
2. 明确所有输入输出文件名约定；
3. 冻结关键参数：
  - `--sub_block_size_x`
  - `--sub_block_size_y`
  - `--overlap_size_x`
  - `--overlap_size_y`
  - 灰度拉伸范围参数
  - ControlNet 元数据参数
4. 明确 `shapemodel` 一致性约束在接口层如何表达；
5. 建立最小测试骨架。

完成标志：

- 需求与计划文档稳定；
- CLI 参数表初稿完成；
- 最小测试目录与模块名确定。

### Phase 1：共享基础模块骨架

目标：先把公共积木搭起来，让后续 6 个脚本只拼装不造轮子。

工作内容：

1. 完成列表读取与路径解析；
2. 完成 `.key` 文件对象模型与读写接口；
3. 完成日志与统计结果结构；
4. 定义分块窗口数据结构；
5. 定义无效值掩膜、灰度拉伸配置对象；
6. 搭建 `isis_pybind` 几何转换包装接口。

优先测试：

- `.lis` 文件读取；
- `.key` 文件读写往返；
- 参数对象校验。

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

### Phase 3：`image_match.py`

目标：完成 DOM 上的 SIFT 主匹配链路，这是整个流程的核心阶段。

工作内容：

1. 读取一对 DOM；
2. 判断是否超过 `3000 x 3000` 阈值；
3. 若需要，则按 `1024 x 1024` 默认块大小与 `128` 默认重叠边生成子块；
4. 对每个子块完成：
  - 灰度映射；
  - 无效值掩膜；
  - SIFT 特征提取与匹配；
  - 子块坐标回拼到整图坐标；
5. 输出 DOM 空间 `.key` 文件。

必须明确的实现要点：

1. 百分位拉伸统计时排除特殊像元与 `NaN/Inf`；
2. 当块内有效像素过少时允许跳过；
3. 失败日志要区分“无效值过多”“纹理不足”“匹配为空”；
4. 当前阶段不做块间重复点消解，只做原样汇总。

优先测试：

- 拉伸结果落在 `0–255`；
- 手工灰度范围覆盖默认百分位逻辑；
- 子块偏移回拼正确；
- 无效值块被正确跳过；
- 纯 Python 小样本可产出 `.key` 文件。

### Phase 4：`tie_point_merge_in_overlap.py` 与 `.key` 流程打通

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

### Phase 5：`dom2ori.py`

目标：把 DOM 空间同名点可靠回投到原始影像空间。

工作内容：

1. 读取 DOM 空间 `.key` 文件；
2. 打开对应 DOM 与原始 CUBE；
3. 借助 `isis_pybind` 完成坐标转换；
4. 对转换失败点分类；
5. 输出原始影像空间 `.key` 文件。

关键风险：

1. DOM 与原始影像不一致；
2. 由于 `shapemodel` 不一致导致几何反算失败；
3. 点反投影后超出原始影像范围。

优先测试：

- 成功点顺序保持一致；
- 失败点被正确记录；
- 输出文件数量与内容自洽。

### Phase 6：`controlnet_stereopair.py`

目标：根据原始影像空间连接点生成单个立体像对 ControlNet。

工作内容：

1. 读取 `ori_A.key` 与 `ori_B.key`；
2. 读取 `NetworkId`、`TargetName`、`UserName`；
3. 校验 `TargetName` 配置来源；
4. 用 `isis_pybind` 构建 ControlNet / ControlPoint / ControlMeasure；
5. 支持 PVL 或二进制格式写盘。

优先测试：

- 必填元数据缺失时报错；
- 点数与 measure 数量一致；
- 输出 ControlNet 文件可生成。

### Phase 7：端到端样例与回归验证

目标：确保从列表输入到控制网输出的完整链路可跑通。

工作内容：

1. 准备最小化测试数据；
2. 从 `original_images.lis` 与 `doms.lis` 开始跑完整流程；
3. 校验中间产物是否符合预期：
  - `images_overlap.lis`
  - DOM 空间 `.key`
  - 去重后 `.key`
  - 原始影像空间 `.key`
  - `.net`
4. 补充 usage 文档与示例说明。

## 数据与错误流设计

### 数据流

1. 影像列表层：`original_images.lis`、`doms.lis`
2. 像对层：`images_overlap.lis`
3. 匹配层：DOM 空间 `.key`
4. 去重层：去重后的 DOM 空间 `.key`
5. 几何层：原始影像空间 `.key`
6. 网络层：ISIS ControlNet

### 错误分类

建议统一错误码或错误类别，至少覆盖：

1. 输入文件不存在；
2. 列表配对不一致；
3. DOM/原始影像映射关系不一致；
4. `shapemodel` 前提不满足；
5. 子块有效像素不足；
6. SIFT 无特征或无匹配；
7. `.key` 文件非法；
8. DOM→原图回投失败；
9. ControlNet 元数据缺失；
10. ControlNet 写盘失败。

## 测试策略

### 单元测试

优先给以下模块写 focused unit test：

1. `.lis` 列表解析；
2. `.key` 文件读写；
3. 百分位拉伸与手工拉伸；
4. 无效值掩膜；
5. 分块窗口生成与偏移回拼；
6. 三位小数 HASH 去重。

### 集成测试

1. `dom2ori.py`：依赖 `asp360_new` + `isis_pybind` 的几何能力；
2. `controlnet_stereopair.py`：依赖 `isis_pybind` 的 ControlNet 能力。

### 端到端测试

至少保留一个最小 smoke 流程，从输入列表一直到 `.net` 输出，重点验证：

1. 各阶段文件都能生成；
2. 去重后点数合理；
3. 最终控制网非空；
4. 日志能解释失败点来源。

## 当前明确不做的内容

为控制首轮实现复杂度，以下内容本计划明确不纳入当前阶段：

1. 并行化分块调度；
2. 跨多个立体像对的全局点去重或全局合网；
3. 基于相关匹配的二次精化或亚像素细化；
4. 为该示例新增新的底层 C++ pybind 绑定，除非后续实现被现有 `isis_pybind` 能力阻塞。

## 交付里程碑

1. **M1：文档与接口冻结**
  - 需求与计划确定；
  - CLI 参数草图确定。

2. **M2：共享模块 + 前半流程可运行**
  - `image_overlap.py`
  - `image_match.py`
  - `tie_point_merge_in_overlap.py`

3. **M3：几何回投与控制网生成可运行**
  - `dom2ori.py`
  - `controlnet_stereopair.py`

4. **M4：测试与示例闭环**
  - focused unit tests
  - 最小端到端 smoke
  - usage 文档补齐
