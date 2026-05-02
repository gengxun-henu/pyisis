<div align="right">

[English](./README.md) | [简体中文](./README.zh-CN.md)

</div>

欢迎使用 USGS ISIS Python Bindings（即 PyISIS）！
本项目为强大的 USGS ISIS（v9.0.0）摄影测量软件提供 Python 绑定，使其能够更顺畅地集成到行星影像处理工作流中。

🛠️ 安装说明：你可以通过 Conda 或 Mamba 安装 USGS ISIS。分步安装指南请参见 [Environment Setup Guide](https://astrogeology.usgs.gov/docs/how-to-guides/environment-setup-and-maintenance/installing-isis-via-anaconda/)。

📚 学习资源：使用 ISIS 处理行星影像有一定学习门槛，建议先阅读 [Getting Started Guide](https://astrogeology.usgs.gov/docs/how-to-guides/image-processing/)，以便更快上手。

# pyISIS / `isis_pybind_standalone`

本仓库基于 `pybind11` 为 **USGS ISIS 9.0.0** 提供 Python 绑定，目前主要交付面向 Linux 的 `isis_pybind` 扩展模块。

本仓库的目标范围非常明确：

- 使用**已经安装好的 ISIS 环境**作为外部 SDK / 运行时
- 构建可被 Python 导入的扩展模块 `isis_pybind._isis_core`
- 向 Python 暴露行星遥感、摄影测量、控制网、相机模型、投影与几何处理等相关 API

> 当前推荐的分发方式是 **GitHub Release + 安装说明 + Linux 构建产物**。
> 这个项目并不适合被包装成一个“纯 Python、直接 `pip install` 即可”的软件包，因为它依赖外部 ISIS、Qt 以及相关共享库。

## 当前支持范围

目前推荐并已验证的兼容范围如下：

| 项目 | 当前推荐 / 已验证范围 |
| --- | --- |
| 操作系统 | Linux x86_64 |
| Python | CPython 3.12 |
| ISIS | USGS ISIS 9.0.0 运行时 / 开发环境 |
| 分发方式 | GitHub Release、源码构建、安装到已激活的 conda 环境 |
| 是否建议首发为直接 PyPI 包 | 当前不建议 |

## 本仓库会构建什么

成功构建后，核心 Python 包目录通常位于：

- `build/python/isis_pybind/`

它一般包含以下内容：

- `build/python/isis_pybind/__init__.py`
- `build/python/isis_pybind/_isis_core.cpython-312-x86_64-linux-gnu.so`
- `build/python/isis_pybind/LICENSE`

真正的绑定共享库是：

- `_isis_core.cpython-312-x86_64-linux-gnu.so`

不过，**不要只单独复制这个 `.so` 文件来使用**。它应该和 `__init__.py` 一起保存在 `isis_pybind/` 包目录中。

## 请先安装 USGS ISIS

这个绑定项目不会替你安装 ISIS。你需要先准备一个**可正常工作的 ISIS 环境**，最好通过 conda / mamba 管理。

### 推荐方式

先准备一个已经包含 ISIS 9.0.0 运行时与开发文件的环境，例如当前本地使用的环境：

- `asp360_new`

本项目假设该环境至少提供：

- `${CONDA_PREFIX}/include/isis`
- `${CONDA_PREFIX}/lib/libisis.so`
- `${CONDA_PREFIX}/lib/Camera.plugin`

换句话说，只要某个 ISIS 环境提供了这些关键内容，就可以用于构建本绑定。

### 建议的 ISIS 安装路径

1. 使用 **USGS ISIS / Astrogeology 官方**安装方式，或使用你所在实验室 / 团队已经验证过的 conda 配方。
2. 激活该环境。
3. 确认以下关键路径存在：
	- `include/isis`
	- `lib/libisis.so`
	- `lib/Camera.plugin`

如果这三项缺失，本项目就无法顺利完成配置与链接。

### 关于 `ISISDATA`

- 很多真实的相机、时间和几何处理流程在运行时仍然依赖 `ISISDATA`
- 本仓库测试会尝试回退到 `tests/data/isisdata/mockup/` 这个最小 mock 环境
- 但如果你要处理自己的真实影像和相机模型，仍然建议配置完整可用的真实 `ISISDATA`

## 安装本绑定：推荐方式

### 方式 A：从源码构建并安装到当前 Python 环境

这是目前**最推荐**、也最可靠的安装方式。

如果你想用仓库里最短、最直接的标准 build + test + smoke 入口，优先使用：

```bash
scripts/build_test_smoke.sh full
```

1. 激活你已经准备好的 ISIS conda 环境。
2. 将该环境同时作为：
	- Python 解释器来源
	- ISIS 头文件与库文件来源
3. 配置并构建本仓库。
4. 通过 `cmake --install` 将其安装到当前环境的 `site-packages` 中。

标准流程示例如下：

```bash
export ISIS_PREFIX="$CONDA_PREFIX"
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" \
  -DISIS_PREFIX="$ISIS_PREFIX"
cmake --build build -j"$(nproc)"
cmake --install build
```

如果你希望在配置阶段排除 ASP / VW 相机库参与链接，可以启用下面这个 CMake 选项：

```bash
cmake -S . -B build \
	-DCMAKE_BUILD_TYPE=Release \
	-DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" \
	-DISIS_PREFIX="$ISIS_PREFIX" \
	-DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON
```

启用 `-DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON` 后，构建时会从额外的 ISIS 相机库链接集合中排除 `libAsp*` 和 `libVw*`；如果省略该选项或设置为 `OFF`，则保持默认行为不变。

安装完成后，`isis_pybind` 将被复制到当前 Python 环境的 `site-packages` 中。

### 方式 B：直接从构建目录临时使用

如果你只是想开发、调试，或者快速试跑一次，也可以先不安装，直接从构建目录使用该包：

```bash
export PYTHONPATH="$PWD/build/python${PYTHONPATH:+:$PYTHONPATH}"
python -c "import isis_pybind; print(isis_pybind.__file__)"
```

这种方式适合：

- 本地开发
- 快速 smoke 测试
- 临时验证示例或单元测试

但对于终端用户来说，这并不是正式安装的推荐方式。

## 关于共享库安装：真正重要的是什么

在本项目中，生成的绑定共享库是 `isis_pybind/_isis_core*.so`。

### 推荐的安装方式

优先使用：

```bash
cmake --install build
```

原因如下：

- 它会把 `__init__.py` 和 `_isis_core*.so` 一起安装到正确位置
- 它也会一并包含 `LICENSE`
- 能避免“`.so` 文件在，但 Python 包结构不完整”这种很常见的坑

### 手动安装方式

如果你从 GitHub Release 下载的是**预编译二进制产物**，并且该产物已经包含完整的包目录，例如：

```text
isis_pybind/
  __init__.py
  _isis_core.cpython-312-x86_64-linux-gnu.so
  LICENSE
```

那么你可以把整个 `isis_pybind/` 目录复制到目标 Python 环境的 `site-packages` 目录下。

对于 Linux 上的 conda 环境，目标路径通常类似于：

```text
$CONDA_PREFIX/lib/pythonX.Y/site-packages/isis_pybind/
```

例如，如果目标环境是一个使用 CPython 3.12 的 conda ISIS 环境，那么最终路径通常类似：

```text
/home/你的用户名/miniconda3/envs/你的环境名/lib/python3.12/site-packages/isis_pybind/
```

如果你是从本仓库本地构建结果中手动复制，优先复制这个完整的构建后包目录：

```text
build/python/isis_pybind/
```

而不是只复制源码侧目录：

```text
python/isis_pybind/
```

因为构建后的目录同时包含 `__init__.py` 和编译得到的扩展模块 `_isis_core*.so`。

你也可以直接在目标环境里查询它自己的 `site-packages` 路径：

```bash
python -c "import sysconfig; print(sysconfig.get_path('purelib'))"
```

然后把整个构建后的 `isis_pybind/` 目录复制进去，最终应形成类似结构：

```text
<site-packages>/isis_pybind/__init__.py
<site-packages>/isis_pybind/_isis_core.cpython-312-x86_64-linux-gnu.so
<site-packages>/isis_pybind/LICENSE
```

同时请确认目标环境的 Python ABI 与构建产物匹配。例如，文件名 `_isis_core.cpython-312-x86_64-linux-gnu.so` 表示它是为 CPython 3.12 构建的，不应直接复制到 Python 3.11 或 3.13 环境中使用。

> 不建议只单独复制 `_isis_core*.so`。

### 共享库加载要求

即使 Python 包本身安装成功，运行时仍然需要目标机器能正确解析外部依赖，例如：

- `libisis.so`
- Qt 共享库
- 所需的相机 / 投影 / Bullet 等相关库

因此，**当前的预编译二进制产物主要面向已经具备兼容 ISIS 环境的 Linux 用户**。

## 如何验证安装是否成功

至少建议执行以下三项检查。

如果你是在仓库内做代码修改后的本地回归，也可以直接先跑：

```bash
scripts/build_test_smoke.sh full
```

### 1. 验证 Python 能导入该包

```bash
python -c "import isis_pybind as ip; print(ip.__file__)"
```

### 2. 验证核心扩展是否已加载

```bash
python -c "import isis_pybind as ip; print(hasattr(ip, 'Cube'), hasattr(ip, 'Camera'))"
```

### 3. 运行最小 smoke 流程

```bash
python tests/smoke_import.py
```

如果这三项都通过，通常说明：

- `isis_pybind` 的包路径正确
- `_isis_core` 能被 Python 正常加载
- 基础运行时依赖可用

## 示例：前方交会

仓库中已经提供了可直接参考的示例：

- `examples/forward_intersection.py`
- 使用说明：`examples/forward_intersection_usage.md`

这个示例演示了如何：

- 打开两幅 ISIS cube
- 提供左影像点位
- 自动估计 / 匹配右影像中的同名点
- 调用 `Stereo.elevation(...)` 执行前方交会

使用仓库自带测试数据的示例命令如下：

```bash
python examples/forward_intersection.py \
  tests/data/mosrange/EN0108828322M_iof.cub \
  tests/data/mosrange/EN0108828327M_iof.cub \
  64.0 \
  512.0
```

如果你想直接从构建目录运行该示例，请确保 Python 能看到 `build/python` 下的包，或者先通过 `cmake --install build` 完成安装。

## 示例：DOM matching ControlNet 工作流

仓库中也提供了一套从 DOM 匹配点生成 ISIS 控制网的示例流程，位于：

- `examples/controlnet_construct/`
- 端到端使用说明：`examples/controlnet_construct/usage.md`
- 详细需求 / 工作流说明：`examples/controlnet_construct/requirements_dom_matching_controlnet.md`
- 示例配置：`examples/controlnet_construct/controlnet_config.example.json`

这套流程面向下面这种常见摄影测量链路：

1. 在正射 DOM 上提取并匹配同名点；
2. 把 DOM 空间 `.key` 回投到原始影像坐标；
3. 输出单个立体像对的 ISIS `ControlNet`；
4. 最后再把多个 pairwise `.net` 用 `cnetmerge` 汇总成整体控制网。

如果你想按“`image_overlap.py` → `image_match.py` → `controlnet_stereopair.py from-dom-batch` → `controlnet_merge.py`”的顺序一步一步跑完整流水线，优先查看：`examples/controlnet_construct/usage.md`。

对于 DOM 匹配阶段，建议把 `ImageMatch` 里的主要参数明确设出来，而不是完全依赖原始默认值。一个常用起步组合是：

```json
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
	"write_match_visualization": true,
	"match_visualization_scale": 0.3333333333333333
}
```

其中：

- `valid_pixel_percent_threshold = 0.05` 表示某个 tile 的有效像素比例低于 $5\%$ 时直接跳过匹配；
- `num_worker_parallel_cpu = 8` 表示 CPU 进程池 worker 上限从一个保守但实用的值起步，实际运行时仍会按 tile 数自动收敛。

仓库示例配置 `examples/controlnet_construct/controlnet_config.example.json` 已经给出这组推荐值，而 `examples/controlnet_construct/run_pipeline_example.sh` 与 `examples/controlnet_construct/run_image_match_batch_example.sh` 会把其中的 `ImageMatch` 段作为默认匹配参数继续转发给 `image_match.py`。`image_match.py` 本身现在也支持 `--config`，所以如果你手工调用它，也可以直接复用同一份配置文件，而不是把所有参数都重写一遍。

例如：

```bash
python examples/controlnet_construct/image_match.py \
	--config examples/controlnet_construct/controlnet_config.example.json \
	left_dom.cub right_dom.cub left.key right.key
```

如果你同时又显式传了某个 CLI 参数，例如 `--ratio-test 0.8` 或 `--num-worker-parallel-cpu 4`，那么命令行参数仍然会覆盖配置文件中的默认值。

如果你希望直接复制一段能跑的批处理模板，不想自己拼参数，`examples/controlnet_construct/usage.md` 现在新增了更显眼的“推荐参数模板”小节，包含：

- 示例流水线脚本模板
- 手工批量 `image_match.py` 模板
- `0.05 / 0.03 / 0.1` 的简短调参建议

如果你更希望要一个独立、短小、可复用的 snippet 入口，现在还可以直接使用：

- `examples/controlnet_construct/recommended_batch_templates.md`
- `examples/controlnet_construct/run_image_match_batch_example.sh`

从当前这一版工作流开始，示例封装脚本对下面这些默认行为也已经明确固定下来：

- CPU 分块并行匹配默认开启；如果你想回退到串行 tile 匹配，可显式传 `--no-parallel-cpu`；
- `run_image_match_batch_example.sh` 默认把 **pre-RANSAC** 匹配连线图写到 `work/match_viz/`；
- `run_pipeline_example.sh` 默认同时写两套图：
	- `work/match_viz/`：**pre-RANSAC**；
	- `work/match_viz_post_ransac/`：**post-RANSAC**。

如果你在使用批量匹配封装脚本时想关闭 pre-RANSAC 连线图，可通过 `-- --no-write-match-visualization` 把参数继续转发给 `image_match.py`。

### 单个立体像对

如果你已经为某个立体像对准备好了 DOM 空间 `.key` 文件，可以这样生成单对控制网：

```bash
python examples/controlnet_construct/controlnet_stereopair.py from-dom \
	left_pair_A.key \
	left_pair_B.key \
	left_dom.cub \
	right_dom.cub \
	left_original.cub \
	right_original.cub \
	examples/controlnet_construct/controlnet_config.example.json \
	pair_outputs/left__right.net \
	--pair-id S1 \
	--report-path pair_outputs/left__right.summary.json
```

说明：

- `PointIdPrefix` 来自配置 JSON；
- `--pair-id S1` 会把控制点 ID 命名空间扩展成类似 `P_S1_00000001`，这样后续多个 pairwise `.net` 再用 `cnetmerge` 合并时，不同立体像对里的 `PointId` 不会意外撞名；
- 如果不传 `--pair-id`，脚本会回退到配置中的可选 `PairId`；如果两者都没有，则保持兼容旧行为，继续生成 `P00000001` 这种格式。

### 基于 `images_overlap.lis` 的批处理

如果你已经为 `images_overlap.lis` 中的每个立体像对都生成了 DOM 空间 `.key` 文件，那么可以直接批量构建全部 pairwise ControlNet，并自动分配立体像对 ID：

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

在这个 batch 模式下：

- 脚本会按 `images_overlap.lis` 的顺序逐对处理；
- 它会在 `work/dom_keys/` 中寻找对应的 DOM `.key` 文件，命名约定为 `A__B_A.key` 和 `A__B_B.key`；
- 它会自动给每个立体像对分配 `S1`、`S2`、`S3`……，因此用户不需要为每一对手工传 `--pair-id`；
- pairwise `.net` 会写入 `work/pair_nets/`；
- per-pair JSON sidecar 与 batch summary JSON 会写入 `work/reports/`。

生成的 per-pair 报告中会记录 `pair_id`、`point_id_namespace` 以及示例控制点 ID，后续如果需要排查 `cnetmerge` 输入来源，会比“盯着一堆 `P00000001` 发呆”轻松很多。

## 单元测试：也是实用的 API 参考

本仓库中的测试不仅用于回归校验，也可作为实际 API 使用方式的参考。

关键入口包括：

- `tests/smoke_import.py`：快速 smoke 验证
- `tests/unitTest/_unit_test_support.py`：共享测试辅助函数和环境初始化逻辑
- `tests/unitTest/forward_intersection_example_test.py`：针对前方交会示例的聚焦回归测试
- `tests/unitTest/`：按类 / 模块组织的详细用法示例

### 运行完整单元测试套件

```bash
python -m unittest discover -s tests/unitTest -p "*_unit_test.py"
```

### 运行示例相关测试

```bash
python -m unittest tests.unitTest.forward_intersection_example_test
```

### 通过 CTest 运行

如果你已经用 CMake 配置过项目，也可以执行：

```bash
ctest --output-on-failure -R python-unit-tests
```

## Release 发布建议

一个 GitHub Release 理想情况下至少应包含以下内容：

1. **源码包**
	- GitHub 自动生成的仓库源码归档（`zip` / `tar.gz`）即可。
2. **Linux 构建产物**
	- 例如：`isis_pybind-linux-x86_64-cp312-isis9.0.0.tar.gz`
	- 应包含完整的 `isis_pybind/` 包目录，而不是单独一个裸 `.so` 文件。
3. **安装说明**
	- 可以放在本 README、Release 页面，或单独的 `INSTALL.md` 中。
4. **版本兼容说明**
	- 提供 Linux / Python / ISIS 版本矩阵。
5. **校验信息**
	- `SHA256SUMS.txt`

### 推荐的 Release 产物命名

建议在产物名中包含以下关键信息：

- 平台：`linux-x86_64`
- Python ABI：`cp312`
- ISIS 版本：`isis9.0.0`
- 项目版本：例如 `v1.2.0`

例如：

```text
isis_pybind-v1.0.0-linux-x86_64-cp312-isis9.0.0.tar.gz
SHA256SUMS.txt
```

## 校验和建议

发布二进制产物时，也建议一并上传校验文件：

```text
SHA256SUMS.txt
```

下载后，用户可以执行：

```bash
sha256sum -c SHA256SUMS.txt
```

这样可以确认：

- 产物完整且未损坏
- 下载过程未被截断
- 用户拿到的就是你发布的确切构建结果

## 常见问题

### 1. `import isis_pybind` 失败，或者 `_isis_core` 缺失

优先检查：

- 当前 Python 是否为 **CPython 3.12**
- `isis_pybind` 是否来自你期望的构建 / 安装环境
- 是否意外拾取到了旧的 `build/python` 产物

### 2. 找不到 `libisis.so` 或其他共享库

这通常意味着：

- 目标机器没有安装兼容的 ISIS 环境
- 或者当前 shell / Python 运行时没有指向正确的 conda 环境

### 3. 示例或测试报 `ISISDATA` 相关错误

- 对真实工作流，请配置完整 `ISISDATA`
- 仓库测试通常会自动尝试 `tests/data/isisdata/mockup/`
- 但并不是所有真实场景都能依赖 mock 数据运行

### 4. 这个项目能作为普通 `pip install` 包来支持吗？

目前不建议把本项目描述成一个普通的、只靠 pip 即可安装的软件包。

原因在于它依赖：

- 外部 ISIS 运行时
- Qt 和其他 C++ 共享库
- 特定的 Python ABI 与系统环境

因此，当前更现实的分发模型是：

- GitHub Release
- 源码构建
- 或面向已具备兼容 ISIS conda 环境用户的二进制分发

## 许可证

本仓库中自行编写的绑定层代码和 Python 入口代码基于以下许可证发布：

- `MIT License`

参见：

- `LICENSE`

上游 ISIS 源码、第三方依赖和外部共享库仍遵循其各自许可证。