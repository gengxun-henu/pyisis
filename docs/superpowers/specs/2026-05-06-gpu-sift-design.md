# GPU SIFT 匹配设计

## 背景

当前 `tile_matching.py` 使用 `cv2.SIFT_create()` 在 CPU 上逐 tile 执行 SIFT 特征提取。目标是通过 GPU 加速 SIFT 检测阶段，减少整体匹配时间，同时最小化代码改动量。

## 选型

- **GPU SIFT 库**: OpenCV CUDA (`cv2.cuda.SIFT`)，来自 `opencv-contrib-python` 模块
  - OpenCV 官方维护，与 CPU SIFT API 高度一致
  - 无需额外第三方库，仅需 `opencv-contrib-python`（需带 CUDA 编译）
  - 参数与 CPU 版完全兼容（`nfeatures`、`contrastThreshold`、`edgeThreshold`、`sigma`）
- **传输策略**: 批量 16-32 个 tile 一次传入 GPU，而非逐 tile 传输
  - 逐 tile 传输时 H2D/D2H + kernel launch 开销占计算时间 10-20%，收益有限
  - 批量传输摊薄 overhead，GPU 可并行处理多张图像

## 架构

### 新增文件

**`examples/controlnet_construct/gpu_sift.py`** — GPU SIFT 封装模块

职责：
- 封装 `cv2.cuda.SIFT` 初始化和批量 SIFT 检测
- 提供与当前 `_build_sift_detector()` 语义一致的接口
- 处理 CPU/GPU 数据传输（numpy ↔ `cv2.cuda_GpuMat`）
- 当 GPU 不可用或 `opencv-contrib-python` 未安装时 fallback 到 CPU

核心接口：
```python
class GpuSiftBatch:
    """累积 tile 并批量执行 GPU SIFT。"""

    def __init__(self, batch_size: int = 32, **sift_params):
        # OpenCV CUDA SIFT 参数与 CPU 版完全一致
        sift_params: nfeatures, contrastThreshold, edgeThreshold, sigma 等
        ...

    def add(self, image: np.ndarray, mask: np.ndarray) -> int:
        """添加一张 uint8 图像到批次，返回批次内索引。"""
        ...

    def execute(self) -> list[tuple[list[cv2.KeyPoint], np.ndarray]]:
        """执行批量 SIFT，返回每个 tile 的 (keypoints, descriptors)。"""
        ...
```

### 修改文件

**`examples/controlnet_construct/tile_matching.py`**

1. 在 `_match_tile()` 函数上方新增 `_match_tile_gpu()` 函数：
   - 接收 `left_image`, `right_image`, `left_mask`, `right_mask` 等参数
   - 内部使用 `GpuSiftBatch` 批量处理
   - 返回格式与 `_match_tile()` 一致（keypoints + descriptors）

2. 在 `match_dom_pair()` 或顶层调用处增加 `use_gpu: bool = False` 参数

3. 在 `_match_tile_from_window_values()` 中根据 `use_gpu` 选择调用 `_match_tile()` 或 `_match_tile_gpu()`

### 批处理在 worker 中的位置

在 `_match_tile_task_batch_worker()` 内部，现有流程是逐 tile 调 `_match_tile_task_with_open_cubes()`，该函数内部读取 tile 后立即调 SIFT。

改动方案：新增一个 GPU 版 worker 函数 `_match_tile_task_batch_worker_gpu()`，在同一个 for 循环中：

```
# GPU worker 流程:
# 阶段1: 累积 — 读 tile → 预处理 → 加入 GPU batch，不执行 SIFT
gpu_batch = GpuSiftBatch(batch_size=batch_size)
pending = []  # (indexed_task, left_image, left_mask, right_image, right_mask, ...)
for indexed_task in resolved_indexed_tasks:
    left_image, left_mask, ... = prepare_tile(left_values, ...)
    right_image, right_mask, ... = prepare_tile(right_values, ...)
    gpu_batch.add(left_image, left_mask)
    gpu_batch.add(right_image, right_mask)
    pending.append((indexed_task, left_stats, right_stats, ...))

    if len(pending) >= batch_size:
        _flush_gpu_batch(gpu_batch, pending, results)
        gpu_batch = GpuSiftBatch(batch_size=batch_size)
        pending = []

# 阶段2: flush 剩余
if pending:
    _flush_gpu_batch(gpu_batch, pending, results)
```

`_flush_gpu_batch()` 内部：
1. `gpu_batch.execute()` → 批量 GPU SIFT
2. 对每个 tile，用返回的 keypoints + descriptors 做 CPU 描述子匹配
3. 构建 `TileMatchResult` 并 append 到 results

### 数据流

```
tile 读取 (CPU)
  → stretch_to_byte (CPU, 现有逻辑不变)
  → mask 生成 (CPU, 现有逻辑不变)
  → 累积 batch_size 个 tile
  → 批量 H2D 传输 (cv2.cuda_GpuMat.upload)
  → cv2.cuda.SIFT.detectAndCompute (GPU)
  → 批量 D2H 传输 (cv2.cuda_GpuMat.download)
  → 描述子匹配 (CPU, BFMatcher/FLANN, 现有逻辑不变)
```

**为什么描述子匹配留在 CPU？**
- `cv2.cuda.SIFT` 只负责特征提取（detect + compute）
- 描述子匹配涉及左右图跨 tile 的关系，批量模式复杂
- BFMatcher/FLANN 在 CPU 上对少量描述子（通常 <500/tile）足够快
- 这保持了最小改动原则：匹配逻辑完全不变

## OpenCV CUDA SIFT 参数映射

OpenCV CUDA SIFT (`cv2.cuda.SIFT_create()`) 与 CPU SIFT 参数完全一致，无需特殊映射：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `nfeatures` | int | 0 | 保留的最佳特征数量（0 表示不限制） |
| `nOctaveLayers` | int | 3 | 每组 octave 的层数 |
| `contrastThreshold` | float | 0.04 | 对比度阈值，用于过滤弱关键点 |
| `edgeThreshold` | float | 10.0 | 边缘阈值，用于过滤边缘响应 |
| `sigma` | float | 1.6 | 高斯模糊 sigma |

直接透传即可：
```python
# CPU 版
detector = cv2.SIFT_create(nfeatures=500, contrastThreshold=0.04, edgeThreshold=10.0, sigma=1.6)

# GPU 版 — 参数完全相同
detector = cv2.cuda.SIFT_create(nfeatures=500, contrastThreshold=0.04, edgeThreshold=10.0, sigma=1.6)
```

## 依赖与安装

> **注意**: pip 预编译的 `opencv-contrib-python` wheel **不包含 CUDA 模块**（`cv2.cuda` 不可用）。
> 要在 GPU 机器上使用 `cv2.cuda.SIFT_create()`，必须从源码编译带 CUDA 支持的 OpenCV。

### 开发环境（无 GPU）

开发机只需安装普通版本，用于编写代码和测试 CPU fallback 路径：

```bash
pip install opencv-contrib-python
```

### 运行环境（有 GPU + CUDA）

需要在目标 GPU 机器上从源码编译：

```bash
# 1. 安装 CUDA toolkit >= 11.0
# 2. 下载 opencv + opencv_contrib 源码（版本需一致）
git clone --branch 4.x https://github.com/opencv/opencv.git
git clone --branch 4.x https://github.com/opencv/opencv_contrib.git
cd opencv && mkdir build && cd build

# 3. 编译时启用 OPENCV_ENABLE_NONFREE 和 CUDA 支持
cmake -DOPENCV_EXTRA_MODULES_PATH=../../opencv_contrib/modules \
      -DOPENCV_ENABLE_NONFREE=ON \
      -DWITH_CUDA=ON \
      -DENABLE_CXX11=ON \
      -DCMAKE_BUILD_TYPE=Release \
      ..
make -j$(nproc)
make install

# 4. 安装 Python 绑定
cd python_loader && pip install .
```

当前代码不直接引入 GPU SIFT 导入，而是在运行时检测：

```python
try:
    # 检查是否有 CUDA 支持
    if cv2.cuda.getCudaEnabledDeviceCount() > 0:
        HAS_GPU_SIFT = True
    else:
        HAS_GPU_SIFT = False
except Exception:
    HAS_GPU_SIFT = False
```

## 错误处理

- GPU 不可用 / `opencv-contrib-python` 未安装 CUDA 版本 → 自动 fallback 到 CPU SIFT，输出 warning
- GPU OOM → 自动回退到更小的 batch size，重试；仍失败则 fallback 到 CPU
- OpenCV CUDA SIFT 对某些特殊图像（全黑、全无效值）行为需测试，fallback 到 CPU

## 测试

- 单元测试：`GpuSiftBatch` 的 add/execute 流程
- 集成测试：对比 GPU 和 CPU SIFT 输出（关键点数量、匹配率差异在可接受范围）
- 性能测试：不同 batch size (8/16/32/64) 的端到端耗时对比
- 回退测试：无 GPU 环境下自动使用 CPU 路径

## 不需要改动的部分

- `tile_cache.py` — 读取逻辑不变
- `tiling.py` — tile 生成不变
- `preprocess.py` — 图像预处理不变
- 描述子匹配逻辑（BFMatcher/FLANN）不变
- `.key` 文件输出格式不变
- ControlNet 构建逻辑不变
