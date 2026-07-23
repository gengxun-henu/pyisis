# 仓库结构优化进度与后续计划

> 状态：第一轮优化已完成；测试数据暂时保留，下一阶段转入 ISIS 10
> 兼容性准备。
>
> 更新日期：2026-07-23。

## 1. 已完成的工作

### 1.1 开发参考源码与 Git 解耦

- `reference/upstream_isis/` 仅作为开发时的源码参考，不再由 Git 跟踪。
- 上游版本通过锁定信息和 `tools/dev/sync_upstream_isis.py` 恢复。
- 实际绑定签名仍以目标 conda 环境或 Windows ISIS prefix 中的头文件和库
  为准。
- 源码包和发行物不包含上游源码镜像及本地规划目录。

### 1.2 Windows、Linux 与发行链路

- Windows ISIS 9.0.0 已具备源码获取、补丁、构建、prefix 验证和 PyISIS
  构建入口。
- Windows wheel 使用 GitHub 托管的 Windows runner，并缓存已验证的 ISIS
  prefix。
- Linux wheel 在 manylinux 环境中构建和修复，使用 `auditwheel` 检查动态库
  依赖和平台标签。
- GitHub Release 已按 ISIS 9.0.0 标识预发布版本，并提供 Linux、Windows
  安装说明。

### 1.3 停止跟踪生成物

PR #344 完成以下清理：

- `.deps/` 中约 254 MB 的 OpenCV CUDA 构建和安装产物不再由 Git 跟踪。
- `.tmp_install/` 中约 7.2 MB 的安装暂存文件不再由 Git 跟踪。
- 新增 `tools/dev/build_opencv_cuda.sh` 和开发说明，使 OpenCV CUDA 依赖在
  仓库外的用户缓存中按固定版本重建。
- 新检出不再下载上述约 261 MB 的平台相关生成物。

这些文件仍存在于旧 Git 历史中。本阶段不重写历史，也不强制清理开发者的
本地缓存。

### 1.4 大文件第一轮拆分

本轮按职责抽取而不是机械切割：

| 原文件 | 优化前 | 优化后 | 已抽取内容 |
| --- | ---: | ---: | --- |
| `examples/image_match/image_match.py` | 5,455 行 | 5,233 行 | 进度显示、配置 I/O、CLI 参数转发 |
| `tests/unitTest/controlnet_construct_matching_unit_test.py` | 8,561 行 | 8,332 行 | GPU matching 测试 |
| `tests/unitTest/controlnet_construct_pipeline_unit_test.py` | 10,169 行 | 9,927 行 | ImageMatch preset 测试 |
| `examples/controlnet_construct/run_pipeline_example.sh` | 2,154 行 | 2,042 行 | 五类 JSON 报告摘要 |

新增聚焦模块：

- `examples/image_match/progress.py`
- `examples/image_match/config_io.py`
- `examples/image_match/cli_runtime.py`
- `examples/controlnet_construct/pipeline_report_summary.py`
- `tests/unitTest/controlnet_construct_gpu_matching_unit_test.py`
- `tests/unitTest/image_match_cli_preset_unit_test.py`

验证结果保持原测试数量：matching 拆分后合计 227 项通过、1 项按环境跳过；
新增 GPU 测试 9 项和 preset 测试 10 项均通过。

## 2. 当前保留项

### 2.1 测试数据

`tests/` 当前约 291 MB。用户已确认 200–300 MB 的测试数据可以继续进入
Git，因此暂不开展 Git LFS、Release 附件或对象存储迁移。

后续只有在以下情况出现时才重新评估：

- GitHub 克隆、CI checkout 或发布明显受到体积影响；
- 单个数据文件接近 GitHub 普通 Git 文件限制；
- 数据许可或来源要求独立归档；
- 测试数据增长失去边界。

在重新评估前，不应仅凭目录大小或文本搜索结果删除测试数据。

### 2.2 Git 历史

本地 `.git` 仍包含旧生成物对象。历史重写会改变提交 ID，并要求所有协作者
重新同步，因此不属于常规优化 PR。

默认不执行 `git filter-repo`、强制推送或批量历史清理。只有在重新克隆体积
成为实际问题且用户单独授权后，才制定备份、对象清单、协作者通知和恢复方案。

### 2.3 本地规划文件

`.planning/` 是本地任务过程记录，不属于正式发行文档。默认保持未暂存，
不与代码或文档 PR 混合提交。

## 3. 下一阶段优先级

### 优先级 1：ISIS 10 参考源码与版本锁定

建立 ISIS 9.0.0、ISIS 10.0.0 独立参考目录和锁文件，并使同步工具支持显式
版本参数。参考目录继续不进入 Git。

验收标准：

- 两个版本均有明确 tag、commit 和来源；
- 可以独立下载、校验和恢复；
- ISIS 9 的现有恢复方式保持兼容；
- 同步操作不会覆盖另一版本目录。

### 优先级 2：非 GUI API 差异审计

从当前已经绑定的头文件和类出发，对比 ISIS 9/10 实际开发 prefix：

- 排除 QWidget、Qt signals/slots 和 GUI/事件观察接口；
- 记录头文件、类、枚举、方法签名和链接符号差异；
- 输出机器可读 API 矩阵和人工审阅报告；
- 将结果分类为直接兼容、兼容包装、条件编译、版本特有和暂不支持。

在差异报告完成前，不批量修改绑定实现。

### 优先级 3：Linux ISIS 10 最小构建验证

- 建立独立的 ISIS 10 conda 开发环境；
- 探测并导出编译时 ISIS 精确版本；
- 在同一源码提交上分别完成 ISIS 9/10 配置、构建、导入和聚焦测试；
- 先验证 Linux，再确定 Windows ISIS 10 的真实补丁工作量。

### 优先级 4：Windows ISIS 9 参数化与 ISIS 10 移植

- 先把现有固定 ISIS 9.0.0 的 Windows 脚本改成版本化框架；
- 保持 ISIS 9 构建、prefix 和 wheel 回归不变；
- 将 ISIS 9、ISIS 10 补丁放入独立目录；
- ISIS 10 Windows 在完整 prefix 和 PyISIS 基础测试通过前保持
  `experimental`。

### 优先级 5：继续拆分大型文件

大型文件仍需分批优化，但不与 ISIS 10 基线建立混在同一个 PR。推荐顺序：

1. 从 `controlnet_construct_pipeline_unit_test.py` 继续按 pipeline 阶段拆分；
2. 从 `controlnet_construct_matching_unit_test.py` 拆分深度匹配和 manifest
   编排测试；
3. 在依赖方向明确后抽取 `image_match.py` 的深度匹配编排；
4. 继续减少 `run_pipeline_example.sh` 中可独立测试的嵌入式逻辑。

每次拆分必须保持 CLI、Python API、测试数量和输出格式兼容，并使用独立 PR。

## 4. 下一项实施工作

下一项工作使用独立分支和 worktree：

```text
branch: agent/isis10-source-audit
worktree: .worktrees/isis10-source-audit
```

第一项 PR 只完成：

1. ISIS 9/10 源码版本锁定；
2. 双版本参考目录同步机制；
3. 当前非 GUI 绑定头文件清单；
4. API 差异报告的生成入口和空白数据结构。

该 PR 不修改 Windows ISIS 补丁、不承诺 ISIS 10 Windows 稳定支持，也不改变
现有 ISIS 9 发布包。
