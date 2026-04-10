# pyISIS / `isis_pybind_standalone`

面向 **USGS ISIS 9.0.0** 的 Python 绑定项目，基于 `pybind11` 构建，当前主要提供 Linux 平台上的 `isis_pybind` 扩展模块。

这个仓库的定位很明确：

- 使用 **已经安装好的 ISIS 环境** 作为外部 SDK / runtime
- 编译生成 Python 可导入的扩展模块 `isis_pybind._isis_core`
- 为行星遥感、摄影测量、控制网、相机模型、投影与几何处理提供 Python 调用入口

> 当前最推荐的发布方式是 **GitHub Release + 安装说明 + Linux 构建产物**。
> 这不是“纯 Python、`pip install` 即可通吃”的那类项目；它依赖外部 ISIS、Qt 与相关动态库。

## 适用范围

当前建议按下面的兼容范围使用与发布：

| 项目 | 当前建议 / 已验证范围 |
| --- | --- |
| 操作系统 | Linux x86_64 |
| Python | CPython 3.12 |
| ISIS | USGS ISIS 9.0.0 运行/开发环境 |
| 分发方式 | GitHub Release、源码构建、活动 conda 环境内安装 |
| 是否建议直接发 PyPI | 暂不建议作为首发渠道 |

## 仓库会产出什么

构建完成后，核心 Python 包目录位于：

- `build/python/isis_pybind/`

其中通常包含：

- `build/python/isis_pybind/__init__.py`
- `build/python/isis_pybind/_isis_core.cpython-312-x86_64-linux-gnu.so`
- `build/python/isis_pybind/LICENSE`

其中真正的绑定动态库就是：

- `_isis_core.cpython-312-x86_64-linux-gnu.so`

但请注意：**不要只单独拷贝这个 `.so` 文件使用**。它应与 `__init__.py` 一起位于 `isis_pybind/` 包目录中。

## 先安装 USGS ISIS

这个绑定项目不会替你安装 ISIS。本项目要求你先准备一个**可工作的 ISIS 环境**，推荐使用 conda / mamba 管理。

### 推荐方式

准备一个已经包含 ISIS 9.0.0 运行时与开发文件的环境，例如你本地常用的：

- `asp360_new`

本项目只假设该环境满足以下条件：

- `${CONDA_PREFIX}/include/isis` 存在
- `${CONDA_PREFIX}/lib/libisis.so` 存在
- `${CONDA_PREFIX}/lib/Camera.plugin` 存在

也就是说，只要你的 ISIS 环境能提供这些内容，就可以拿来构建本绑定。

### 建议的 ISIS 安装思路

1. 使用 **官方 USGS ISIS / Astrogeology** 的安装方案，或你所在实验室已经验证过的 conda 配方。
2. 激活该环境。
3. 确认下面三类关键文件已经存在：
   - `include/isis`
   - `lib/libisis.so`
   - `lib/Camera.plugin`

如果这三项不存在，本项目无法完成配置和链接。

### 关于 `ISISDATA`

- 对很多真实相机、时间、几何相关工作流，运行时仍需要 `ISISDATA`。
- 仓库内测试会尽量回退到 `tests/data/isisdata/mockup/` 作为最小 mock 环境。
- 但如果你要在真实任务中处理自己的影像与相机模型，请优先配置真实的 `ISISDATA`。

## 安装本绑定：推荐方式

### 方式 A：从源码构建并安装到当前 Python 环境

这是当前**最推荐**、也最稳妥的安装方式。

1. 激活你已经准备好的 ISIS conda 环境。
2. 将该环境同时作为：
   - Python 解释器来源
   - ISIS 头文件 / 库来源
3. 配置并编译本仓库。
4. 通过 `cmake --install` 安装到当前环境的 `site-packages`。

一个标准流程如下：

```bash
export ISIS_PREFIX="$CONDA_PREFIX"
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" \
  -DISIS_PREFIX="$ISIS_PREFIX"
cmake --build build -j"$(nproc)"
cmake --install build
```

安装完成后，`isis_pybind` 会被复制到当前 Python 环境的 `site-packages` 中。

### 方式 B：仅在构建目录中临时使用

如果你只是想开发、调试或快速试运行，也可以不安装，直接使用构建树里的包：

```bash
export PYTHONPATH="$PWD/build/python${PYTHONPATH:+:$PYTHONPATH}"
python -c "import isis_pybind; print(isis_pybind.__file__)"
```

这种方式适合：

- 本地开发
- 快速 smoke test
- 临时验证 example / unit test

但它不适合作为正式对外安装方案。

## 安装动态库：你真正需要知道的事

这个项目里的“绑定后的动态库”就是 `isis_pybind/_isis_core*.so`。

### 推荐安装方式

优先使用：

```bash
cmake --install build
```

原因：

- 会把 `__init__.py` 与 `_isis_core*.so` 一起安装到正确位置
- 会同时带上 `LICENSE`
- 不容易出现“`.so` 在，但 Python 包结构不完整”的问题

### 手工安装方式

如果你在 GitHub Release 中下载的是**预编译二进制附件**，并且附件内已经包含完整包目录，例如：

```text
isis_pybind/
  __init__.py
  _isis_core.cpython-312-x86_64-linux-gnu.so
  LICENSE
```

那么可以把整个 `isis_pybind/` 目录复制到目标 Python 环境的 `site-packages` 目录中。

> 不建议只复制 `_isis_core*.so` 单文件。

### 动态库加载前提

即使 Python 包安装成功，运行时仍要求目标机器上能解析以下外部依赖：

- `libisis.so`
- Qt 相关共享库
- 需要的 camera / projection / Bullet 等依赖库

因此，**预编译二进制附件默认只面向“已经有兼容 ISIS 环境”的 Linux 用户**。

## 安装后如何验证

建议至少做三步验证。

### 1. 验证 Python 可导入

```bash
python -c "import isis_pybind as ip; print(ip.__file__)"
```

### 2. 验证核心扩展已加载

```bash
python -c "import isis_pybind as ip; print(hasattr(ip, 'Cube'), hasattr(ip, 'Camera'))"
```

### 3. 验证最小 smoke 流程

```bash
python tests/smoke_import.py
```

如果以上三步都通过，说明：

- `isis_pybind` 包路径正确
- `_isis_core` 能被 Python 加载
- 基本运行时依赖可用

## Example：前方交会示例

仓库已提供一个可直接参考的示例：

- `examples/forward_intersection.py`
- 使用说明：`examples/forward_intersection_usage.md`

这个示例演示了：

- 打开两景 ISIS cube
- 给定左图像点
- 自动估计/匹配右图同名点
- 调用 `Stereo.elevation(...)` 做前方交会

基于仓库自带测试数据的示例命令：

```bash
python examples/forward_intersection.py \
  tests/data/mosrange/EN0108828322M_iof.cub \
  tests/data/mosrange/EN0108828327M_iof.cub \
  64.0 \
  512.0
```

如果只想在构建树中直接运行示例，记得先让 Python 能找到 `build/python` 下的包，或者先执行 `cmake --install build`。

## Unit Test：把测试当使用参考

仓库中的测试既是回归验证，也可以作为 API 用法参考。

重点入口包括：

- `tests/smoke_import.py`：快速 smoke 验证
- `tests/unitTest/_unit_test_support.py`：共享测试辅助与环境引导
- `tests/unitTest/forward_intersection_example_test.py`：前方交会示例的最小回归测试
- `tests/unitTest/`：按类 / 模块划分的详细用法示例

### 运行完整 unit test

```bash
python -m unittest discover -s tests/unitTest -p "*_unit_test.py"
```

### 运行示例相关测试

```bash
python -m unittest tests.unitTest.forward_intersection_example_test
```

### 通过 CTest 运行

如果你已经完成 CMake 配置，也可以在构建目录执行：

```bash
ctest --output-on-failure -R python-unit-tests
```

## Release 建议

建议 GitHub Release 至少包含以下附件：

1. **源码包**
   - 仓库源码压缩包（GitHub 自动生成的 `zip` / `tar.gz` 即可）
2. **Linux 构建产物**
   - 例如 `isis_pybind-linux-x86_64-cp312-isis9.0.0.tar.gz`
   - 内含完整 `isis_pybind/` 包目录，而不是裸 `.so`
3. **安装说明**
   - 可放在本 README、Release 页面，或单独的 `INSTALL.md`
4. **版本兼容说明**
   - Linux / Python / ISIS 版本矩阵
5. **校验信息**
   - `SHA256SUMS.txt`

### 建议的 Release 命名信息

建议在附件名中带上这些关键信息：

- 平台：`linux-x86_64`
- Python ABI：`cp312`
- ISIS 版本：`isis9.0.0`
- 项目版本：例如 `v0.1.0`

例如：

```text
isis_pybind-v0.1.0-linux-x86_64-cp312-isis9.0.0.tar.gz
SHA256SUMS.txt
```

## 校验信息建议

发布二进制附件时，建议同时上传校验文件：

```text
SHA256SUMS.txt
```

用户下载后可以执行：

```bash
sha256sum -c SHA256SUMS.txt
```

这样可以确认：

- 附件完整无损坏
- 下载过程没有截断
- 用户拿到的是与你发布时一致的构建产物

## 常见问题

### 1. `import isis_pybind` 失败，或 `_isis_core` 缺失

优先检查：

- 当前 Python 是否是 **CPython 3.12**
- `isis_pybind` 是否来自当前构建或安装环境
- 是否混用了旧的 `build/python` 产物

### 2. 找不到 `libisis.so` 或其他共享库

通常说明：

- 目标机器没有安装兼容的 ISIS 环境
- 或者当前 shell / Python 运行环境没有指向正确的 conda 环境

### 3. 示例或测试里提示 `ISISDATA` 问题

- 真实任务请配置完整 `ISISDATA`
- 仓库测试通常会自动尝试使用 `tests/data/isisdata/mockup/`
- 但不是所有真实业务场景都能依赖 mock 数据

### 4. `pip install` 能不能直接支持？

当前不建议把本项目描述成“普通 pip 包”。

原因是它依赖：

- 外部 ISIS runtime
- Qt 与其他 C++ 动态库
- 特定 Python ABI 与系统环境

因此当前更现实的发布模式是：

- GitHub Release
- 源码构建
- 或面向已有 ISIS conda 环境的二进制分发

## License

本仓库中由本项目作者编写的绑定层代码与 Python 入口代码使用：

- `MIT License`

详见：

- `LICENSE`

上游 ISIS 源码、第三方依赖与外部共享库仍遵循它们各自的许可证。
