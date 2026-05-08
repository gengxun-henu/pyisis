# GPU 大图分块匹配设计（吞吐优先）

## 1. 问题与目标

当前 DOM 影像较大，依赖分块（tile）匹配。现有 GPU 路径只覆盖 SIFT 特征提取，且 `gpu_batch_size` 未形成真实吞吐收益。  
目标是在 **8GB 显存**约束下，以“**总耗时最短**”为主目标，构建可控、可回退、可观测的 GPU 加速链路。

### 成功标准

1. 相同输入下，GPU 方案总耗时明显低于 CPU 基线。  
2. 无 OOM，无长期抖动（吞吐大幅下降后无法恢复）。  
3. 匹配结果质量在可接受波动内（数量与几何筛选后稳定性）。

## 2. 约束与范围

### 约束

- 单进程独占 GPU（避免多进程争抢导致显存与上下文抖动）。
- 允许动态 batch（根据运行态调节，不固定写死 32）。
- OpenCV 范围内推进：RANSAC 仍使用 CPU `calib3d` 路径。

### 范围内

- GPU: SIFT 提特征 + 描述子匹配。
- CPU: ratio test（轻量） + RANSAC（几何筛选） + I/O 与预处理。

### 范围外

- 不引入非 OpenCV 的外部 GPU RANSAC 依赖。
- 不改 pybind C++ 层。

## 3. 备选方案与取舍

### A. 单进程 GPU 调度器 + 动态 batch（选定）

- CPU 多 worker 做读块/预处理，向 GPU 调度器投递任务。
- GPU 调度器集中执行 SIFT + 匹配，并动态调节 batch（如 4/8/16）。
- 优点：吞吐与稳定性平衡最好；易控制显存峰值。  
- 风险：需要额外调度层与队列管理。

### B. 最小改造，仅打通现有 `gpu_batch_size`

- 在现有流程上做局部批处理，不引入独立调度器。
- 优点：改动小。  
- 缺点：吞吐上限有限，长期维护性较弱。

### C. 多进程共享 GPU + streams

- 每个 worker 直接占用同一 GPU 并发执行。
- 优点：理论并行高。  
- 缺点：显存竞争/抖动风险高，不适合当前“稳健吞吐优先”目标。

## 4. 目标架构

### 4.1 流水线

1. CPU 侧读取左右 tile（1024x1024）并完成 invalid mask/拉伸。  
2. 形成任务对并进入有界输入队列。  
3. GPU 调度器按动态 batch 拉取任务，执行：
   - `cv2.cuda.SIFT_create(...).detectAndCompute(...)`
   - `cv2.cuda.DescriptorMatcher`（可用时）进行 KNN 匹配
4. 回传 descriptors/matches 到 CPU；执行 ratio test 与 RANSAC。  
5. 输出 `TileMatchResult`，保持现有下游接口不变。

### 4.2 动态 batch 策略

- 初始 batch=4（8GB 场景保守起步）。
- 若显存水位与批处理时延稳定，逐步升至 8/16。
- 若出现显存压力或批延时恶化，自动降档。
- 禁止直接默认 32 作为起始值。

## 5. 模块边界

### `gpu_sift.py`

- 新增调度器职责（建议 `GpuSiftScheduler`）：
  - 任务收集与批次刷新
  - GPU SIFT + GPU Matcher
  - 动态 batch 调节
  - 失败回退与统计

### `tile_matching.py`

- 改为“提交任务给调度器”，而不是每 tile 现建 `GpuSiftBatch(batch_size=2)`。
- 保持 `TileMatchResult` 与现有调用点兼容。

### `image_match.py`

- 保留 `use_gpu` / `gpu_batch_size`。
- 增加动态 batch 开关与上/下限配置（默认开启动态）。
- 在 summary 中写入 GPU 执行统计字段。

## 6. 容错与降级

- 单 tile GPU 失败：仅该 tile 回退 CPU SIFT+CPU matcher，不影响整批。
- 连续失败超阈值：整作业切 CPU 路径并记录告警字段。
- GPU 不可用（无 CUDA SIFT）：启动即切 CPU，流程继续。

## 7. 观测指标

至少记录：

- 总耗时、每千 tile 耗时
- GPU 任务数、GPU 回退数、回退率
- 动态 batch 轨迹（各档位停留次数）
- 峰值显存（外部监控或运行日志采样）

## 8. 测试与验收

### 8.1 A/B 基准

- 对同一批大图、相同 tile/window 配置执行：
  - CPU 基线
  - GPU（SIFT+匹配，RANSAC CPU）
- 对比总耗时与吞吐指标。

### 8.2 正确性

- 检查匹配数量和几何筛选后的稳定性是否在可接受波动范围。
- 验证失败回退路径不会中断作业。

### 8.3 稳定性

- 长批次运行不出现 OOM。
- 动态 batch 出现降档后可恢复，不长期卡在低效状态。

## 9. 实施顺序（高层）

1. 打通 GPU matcher（保持 RANSAC CPU）。  
2. 引入单进程 GPU 调度器与有界队列。  
3. 加入动态 batch 控制与统计。  
4. 完成 A/B 基准并固化默认参数。
