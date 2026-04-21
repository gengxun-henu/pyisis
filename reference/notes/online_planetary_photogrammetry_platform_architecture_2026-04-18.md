# 面向网页端的行星摄影测量在线处理平台架构方案

> 日期：2026-04-18  
> 作者：Geng Xun / GitHub Copilot  
> 关联现有实现：`examples/controlnet_construct/`、`isis_pybind`、ISIS CLI 工具链  
> 文档性质：架构与实施参考，属于可读性参考资料，非运行时输入

## 1. 目标与定位

目标是把当前仓库已经具备的 **ISIS / `isis_pybind` / DOM Matching ControlNet** 能力，向上包装成一个 **网页端在线行星摄影测量处理平台**。

面向首期场景，用户只需要：

1. 上传 LRO NAC 的 PDS `IMG` 原始影像；
2. 选择少量处理参数；
3. 在线发起任务；
4. 在网页端查看进度、日志与结果；
5. 在处理完成后下载结果，或自动归档到百度网盘。

平台首期建议覆盖两条主线：

- **单景处理链**：导入 → `spiceinit` → 基础校正 → 正射纠正；
- **多景联合处理链**：影像导入 → 单景预处理 → 重叠分析 → 控制网生成 → 光束法平差（bundle adjustment）→ 平差后几何纠正 / 正射成果输出。

这不是简单把 ISIS 命令搬到网页上，而是做成一个 **“任务编排 + 参数约束 + 结果可追踪 + 云端存储”** 的在线工作平台。

## 2. 与当前仓库的关系

当前仓库已经具备几类关键基础：

1. **`isis_pybind`**：可以从 Python 侧访问 ISIS 的 ControlNet、Camera、几何转换等能力；
2. **`examples/controlnet_construct/`**：已经形成 DOM Matching → `dom2ori` → `ControlNet` 构建 → merge 的离线工作流雏形；
3. **测试体系**：已有 focused unit tests，可作为在线服务封装后的算法回归基础。

因此，建议新平台采用：

- **底层继续复用 ISIS / `isis_pybind` / 已有 Python workflow**；
- **上层新增 Web API、任务编排、任务状态机、对象存储与结果归档模块**。

一句话：

> 现有仓库负责“会算”，在线平台负责“让人方便地上传、调度、观察、下载、归档”。

## 3. 首期业务能力边界

### 3.1 首期必须支持

#### A. 单景在线处理

针对单幅 LRO NAC `IMG`：

1. 上传原始 `IMG`；
2. 任务端自动识别任务类型与传感器；
3. 执行 mission-specific ingest（例如 LRO NAC 建议走 `lronac2isis`）；
4. 执行 `spiceinit`；
5. 执行基础辐射 / 几何预处理（视场景可选 `lronaccal`、`lronacecho` 等）；
6. 执行正射纠正：
   - 基础地图投影：`cam2map`
   - 或基于 DEM 的更严格正射：`mapproject`
7. 输出：
   - ISIS cube
   - 正射 DOM / GeoTIFF
   - 任务日志
   - 处理参数摘要 JSON

#### B. 多景联合在线处理

针对多幅 LRO NAC `IMG`：

1. 批量上传原始影像；
2. 自动完成单景 ingest + `spiceinit` + 基础预处理；
3. 自动建立候选重叠影像对；
4. 自动生成控制网（首期建议优先使用当前 `examples/controlnet_construct/` 这条 DOM-based 路线）；
5. 运行光束法平差（ISIS 体系内建议优先对接 `jigsaw`）；
6. 读取 bundle adjustment 输出结果；
7. 基于平差结果重新执行几何纠正 / 正射纠正；
8. 输出：
   - pairwise / merged ControlNet
   - bundle adjustment 报告
   - 平差后 DOM
   - 质量评估报告
   - 下载包与百度网盘归档链接

### 3.2 首期尽量少让用户手工配置

网页端应尽量只暴露少量高价值参数，例如：

1. **目标体**：Moon / Mars / Earth / Bennu / Ryugu（首期至少 Moon）；
2. **shape model / DEM**：
   - 使用系统默认
   - 或允许高级用户选择指定 DEM 产品
3. **控制网生成方法**：
   - 默认：DOM Matching + SIFT
   - 可选：相关匹配 / 外部匹配器（后续）
4. **平差方法**：
   - 默认：标准 bundle adjustment
   - 可选：仅生成控制网、不平差
5. **输出投影模板**：
   - 默认月球常用投影
   - 或允许上传 PVL 模板（高级模式）

原则是：

> 默认用户只看见“必要的 3~5 个参数”；其余参数由平台根据传感器与任务模板自动补齐。

## 4. 总体架构建议

建议采用 **前后端分离 + 异步任务队列 + 算法工作节点** 的结构。

### 4.1 逻辑分层

1. **Web 前端层**
   - 文件上传
   - 任务创建
   - 参数配置
   - 进度查看
   - 日志查看
   - 结果预览
   - 下载 / 归档入口

2. **API 服务层**
   - 用户请求鉴权
   - 任务配置校验
   - 任务入库
   - 查询任务状态
   - 日志 / 结果元数据读取

3. **任务编排层**
   - 将“上传 + 参数”转换成标准化处理 DAG
   - 按步骤调度 ingest、`spiceinit`、控制网、bundle、正射等子任务
   - 维护状态机和失败重试

4. **算法执行层 / Worker 层**
   - 真正运行 ISIS CLI、`isis_pybind` Python 工作流、GDAL、OpenCV
   - 按容器或独立 worker 节点执行

5. **数据与存储层**
   - 原始上传区
   - 中间成果区
   - 最终成果区
   - 元数据库
   - 日志数据库 / 对象日志
   - 百度网盘归档层

### 4.2 技术栈建议

#### Web 前端

建议任选其一：

- Vue 3 + Element Plus
- React + Ant Design

前端重点不是炫技，而是：

- 文件上传稳定
- 进度可见
- 表单少而清晰
- 日志与结果可回看

#### 后端 API

建议优先：

- **FastAPI**

原因：

1. Python 生态下对接 `isis_pybind` 最自然；
2. 适合任务提交、状态查询、流式日志；
3. Pydantic 模型适合做参数模板约束。

#### 任务队列 / 编排

首期建议两种方案二选一：

- **轻量方案**：Celery + Redis
- **增强方案**：Prefect / Temporal / Argo Workflows

首期 MVP 更建议：

- **FastAPI + Celery + Redis + PostgreSQL**

原因是实现成本较低，且足以支撑中等规模异步处理。

#### 数据库

- **PostgreSQL**：任务、用户、元数据、处理配置、成果记录
- **Redis**：任务队列、缓存、进度中转

#### 对象存储

建议把原始数据和成果放在对象存储中，例如：

- MinIO（私有部署首选）
- S3 兼容对象存储
- OSS / COS（如果未来上云）

#### 算法执行容器

每个 worker 节点建议预装：

- ISIS
- `isis_pybind`
- GDAL
- OpenCV
- Python 运行环境
- 必要的 SPICE / ISISDATA 基础目录

## 5. 推荐的核心模块设计

### 5.1 前端模块

1. **数据上传页**
   - 支持单文件 / 多文件拖拽上传
   - 支持批量创建一个 processing job

2. **任务配置页**
   - 处理模式：单景 / 多景
   - 目标体选择
   - DEM / shapemodel 选择
   - 控制网方法选择
   - 平差开关
   - 输出投影选择

3. **任务监控页**
   - 当前步骤
   - 步骤完成率
   - 实时日志
   - 错误摘要

4. **成果页**
   - 结果文件列表
   - 缩略图 / 快速预览
   - 下载按钮
   - 百度网盘归档状态

### 5.2 后端 API 模块

1. **Upload API**
   - 分片上传
   - 文件校验
   - 文件去重
   - 生成 upload record

2. **Job API**
   - 创建 job
   - 查询 job 详情
   - 查询步骤状态
   - 取消 job
   - 重试 job

3. **Artifact API**
   - 获取结果列表
   - 获取下载链接
   - 获取预览元数据

4. **Archive API**
   - 发起百度网盘归档
   - 查询归档状态
   - 返回分享链接或归档记录

### 5.3 编排 / DAG 模块

建议把整条流程显式拆成 DAG 节点，而不要写成一个巨大脚本。

#### 单景 DAG

1. `ingest_raw_img`
2. `spiceinit_cube`
3. `calibrate_cube`
4. `orthorectify_cube`
5. `package_outputs`
6. `archive_to_baidu`

#### 多景 DAG

1. `batch_ingest`
2. `batch_spiceinit`
3. `batch_preprocess`
4. `compute_overlaps`
5. `generate_dom_or_scaled_dom`
6. `build_pairwise_controlnets`
7. `merge_controlnets`
8. `run_bundle_adjustment`
9. `orthorectify_adjusted_cubes`
10. `quality_assessment`
11. `package_outputs`
12. `archive_to_baidu`

### 5.4 算法 Worker 模块

建议进一步拆成独立 worker 能力：

1. **Import Worker**
   - 识别 mission / sensor
   - 运行 `lronac2isis` 等导入工具

2. **SPICE Worker**
   - 运行 `spiceinit`
   - 校验 kernel / shape model 一致性

3. **ControlNet Worker**
   - 复用 `examples/controlnet_construct/` 工作流
   - 输出 pairwise `.net` 与 summary JSON

4. **Bundle Worker**
   - 调用 `jigsaw`
   - 收集 bundle residual 与报告

5. **Orthorectification Worker**
   - 调用 `cam2map` 或 `mapproject`
   - 输出最终 DOM / GeoTIFF

6. **Archive Worker**
   - 将成果压缩打包
   - 上传到百度网盘
   - 写回归档链接和状态

## 6. 任务状态机设计

建议每个 job 和每个 step 都有显式状态。

### 6.1 Job 级状态

- `created`
- `queued`
- `running`
- `succeeded`
- `failed`
- `cancelled`
- `archiving`
- `archived`

### 6.2 Step 级状态

- `pending`
- `running`
- `retrying`
- `succeeded`
- `failed`
- `skipped`

### 6.3 前端展示建议

前端不要只显示“处理中”，而要显示：

- 当前步骤名
- 已完成步骤数 / 总步骤数
- 最近 100 行日志
- 失败步骤与失败原因
- 可重试按钮

这会极大提升平台的可用性。

## 7. 关键数据模型建议

### 7.1 UploadRecord

建议字段：

- `id`
- `user_id`
- `filename`
- `sensor_type`
- `mission`
- `local_storage_path`
- `object_storage_key`
- `checksum`
- `size_bytes`
- `created_at`

### 7.2 ProcessingJob

建议字段：

- `id`
- `user_id`
- `job_type`（single / multi）
- `target_body`
- `status`
- `parameter_json`
- `created_at`
- `started_at`
- `finished_at`
- `error_summary`

### 7.3 JobStep

建议字段：

- `id`
- `job_id`
- `step_name`
- `step_order`
- `status`
- `worker_node`
- `started_at`
- `finished_at`
- `log_path`
- `summary_json`

### 7.4 ArtifactRecord

建议字段：

- `id`
- `job_id`
- `artifact_type`
- `path`
- `preview_path`
- `size_bytes`
- `is_final_output`

### 7.5 ArchiveRecord

建议字段：

- `id`
- `job_id`
- `provider`（baidu_pan）
- `status`
- `remote_path`
- `share_url`
- `archive_started_at`
- `archive_finished_at`

## 8. 百度网盘集成建议

这是你的明确需求，需要单独设计，不建议把它直接塞进主处理 worker 里。

### 8.1 为什么要单独拆出来

百度网盘归档具有这些特点：

1. 网络上传耗时长；
2. API 限流、失败重试与结果计算不是一类问题；
3. 算法任务完成不应因为归档慢而一直占着核心计算 worker。

因此建议：

- **主处理完成后，只把成果归档任务投递给 Archive Worker**。

### 8.2 推荐流程

1. 算法任务完成；
2. 生成最终成果压缩包 / 目录清单；
3. 记录归档任务；
4. Archive Worker 读取本地成果或对象存储成果；
5. 上传至百度网盘目录；
6. 更新数据库中的归档状态、远程路径、分享链接。

### 8.3 实施建议

- 首期可以先不做“用户个人百度账号 OAuth 绑定”；
- 可以先做 **平台统一百度网盘归档账号**；
- 后期再扩展为用户绑定自己的网盘空间。

### 8.4 风险点

1. API 配额；
2. 大文件断点续传；
3. 分享链接有效期或权限管理；
4. 网盘目录命名冲突；
5. 归档失败后的补偿机制。

## 9. 与当前 `controlnet_construct` 工作流的衔接方式

这是最重要的落地点之一。

### 9.1 当前可直接复用的链路

当前 `examples/controlnet_construct/` 已经覆盖：

1. `image_overlap.py`
2. `dom_prepare.py`
3. `image_match.py`
4. `tie_point_merge_in_overlap.py`
5. `dom2ori.py`
6. `controlnet_stereopair.py`
7. `controlnet_merge.py`

因此在线平台不应该重写一套控制网构建算法，而应：

- 把这些脚本收敛为 **可编排 Python service 层**；
- 再由后端 API / worker 去调用。

### 9.2 建议新增的 service 封装层

可以新增一个在线服务适配层，例如：

- `python/online_platform/services/ingest_service.py`
- `python/online_platform/services/spice_service.py`
- `python/online_platform/services/controlnet_service.py`
- `python/online_platform/services/bundle_service.py`
- `python/online_platform/services/archive_service.py`

其中 `controlnet_service.py` 内部再调用 `examples/controlnet_construct/` 的稳定接口。

### 9.3 为什么不要直接从 API 层调用脚本

如果 API 层直接去拼 shell 命令调用 `examples/...py`，后面会越来越难维护。更好的方式是：

1. 先把 `examples/controlnet_construct/` 中稳定逻辑抽成 Python 函数层；
2. CLI 继续保留；
3. Web 平台与 worker 调函数层，而不是调 CLI 文本层。

这样后续测试也更稳定。

## 10. 推荐的实施阶段

### Phase A：MVP

目标：先让单景在线处理跑通。

范围：

1. 用户上传单景 LRO NAC `IMG`
2. 自动 ingest
3. 自动 `spiceinit`
4. 自动正射输出
5. 网页进度展示
6. 结果下载
7. 百度网盘归档

### Phase B：多景控制网

目标：让多景控制网构建跑通。

范围：

1. 批量上传
2. overlap 识别
3. 控制网生成
4. merge
5. 网页日志与中间结果查看

### Phase C：光束法平差

目标：真正形成在线摄影测量平台。

范围：

1. 接入 `jigsaw`
2. 平差报告解析
3. 平差后 DOM 重生产
4. 质量报告可视化

### Phase D：高级功能

可选后续：

1. DEM / shapemodel 版本管理
2. 用户自己的百度网盘绑定
3. 多任务排队优先级
4. GPU / 多节点调度
5. 更多 mission 支持（MRO CTX、HiRISE、Apollo、Kaguya 等）

## 11. 最小可行产品（MVP）建议

如果你现在就开始做，建议 **先别一口气做“全自动多景 bundle + 网盘归档 + 预览系统”**。更稳的路径是：

### MVP-1

- 单景上传
- ingest + `spiceinit`
- `cam2map` / `mapproject`
- 页面查看日志
- 下载成果

### MVP-2

- 多景上传
- overlap 识别
- pairwise controlnet
- merged controlnet
- 页面展示 point / measure 数量

### MVP-3

- `jigsaw`
- 平差报告
- 平差后正射成果
- 百度网盘归档

这条路线最现实，也最容易边做边验证。

## 12. 关键风险与应对

### 风险 1：ISIS 环境重

问题：

- ISIS、SPICE、ISISDATA、mission 数据依赖重。

建议：

- worker 使用预构建容器镜像；
- 明确版本锁定；
- 把 `ISISROOT` / `ISISDATA` 配置做成平台级只读基础设施。

### 风险 2：上传文件大

问题：

- 原始 IMG 和 DOM 成果都可能较大。

建议：

- 采用分片上传；
- 文件先落对象存储；
- worker 运行时按需拉取。

### 风险 3：任务耗时长

问题：

- `spiceinit`、控制网、bundle 都可能很慢。

建议：

- 强制异步；
- 前端显示 step-based progress；
- 支持失败后从中间步骤恢复。

### 风险 4：参数过多

问题：

- 如果把 ISIS 参数全暴露给用户，页面会变成“在线命令行”。

建议：

- 只暴露关键参数；
- 其余用 mission template 自动填充。

### 风险 5：百度网盘不稳定

建议：

- 主处理链与归档链解耦；
- 归档失败不影响主任务 success；
- 页面单独显示 archive status。

## 13. 建议的下一步落地动作

如果你要在这个仓库里继续推进，建议下一步不是直接写前端，而是先做下面三件事：

1. **补一份平台需求文档**
   - 明确角色、任务类型、参数模板、成果类型、存储口径。

2. **把 `controlnet_construct` 提炼成 service API**
   - 让在线平台可以通过 Python 函数直接调用，而不是只会调用脚本。

3. **做一个最小 FastAPI + Celery 原型**
   - 先支持：上传任务配置 → 创建异步任务 → worker 执行单景流程 → 页面轮询状态。

如果这三步走通，再叠多景 bundle 和百度网盘，会稳很多。

## 14. 一句话总结

这个在线平台最合适的建设方式不是“重写一个网页版 ISIS”，而是：

> **以 ISIS / `isis_pybind` / 当前 `controlnet_construct` 作为算法内核，外面包一层 Web 前端、任务编排、异步 worker、成果管理和百度网盘归档系统。**

这样既能最大化复用你当前仓库已有成果，也能把平台真正做成“用户只上传数据、少量选参数、后台自动处理、前端可追踪可下载”的在线摄影测量系统。
