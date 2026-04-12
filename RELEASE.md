# PyISIS v1.0.0

首个稳定 GitHub Release，面向已经具备 **USGS ISIS 9.0.0** 运行环境的 Linux 用户。

## 支持范围

- 平台：Linux x86_64
- Python：CPython 3.12
- ISIS：USGS ISIS 9.0.0
- 分发方式：GitHub Release + 源码构建 + Linux 二进制资产

## Release 资产

GitHub 会自动附带源码压缩包：

- `Source code (zip)`
- `Source code (tar.gz)`

本项目手工上传的资产建议为：

- `isis_pybind-v1.0.0-linux-x86_64-cp312-isis9.0.0.tar.gz`
- `SHA256SUMS.txt`

其中二进制包应包含完整的 `isis_pybind/` 包目录，而不只是 `_isis_core*.so`。

## 安装方式

### 方式 1：使用 Release 二进制包

解压后，将完整的 `isis_pybind/` 目录放入目标 Python 环境可见路径中，或临时设置 `PYTHONPATH`。

```bash
tar xzf isis_pybind-v1.0.0-linux-x86_64-cp312-isis9.0.0.tar.gz
export PYTHONPATH="$PWD/isis_pybind-v1.0.0-linux-x86_64-cp312-isis9.0.0${PYTHONPATH:+:$PYTHONPATH}"
python -c "import isis_pybind as ip; print(ip.__version__, hasattr(ip, 'Cube'))"
python tests/smoke_import.py
```

### 方式 2：从源码构建并安装

```bash
export ISIS_PREFIX="$CONDA_PREFIX"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" \
  -DISIS_PREFIX="$ISIS_PREFIX"
cmake --build build -j"$(nproc)"
cmake --install build
```

安装后可验证：

```bash
python -c "import isis_pybind as ip; print(ip.__version__, hasattr(ip, 'Cube'))"
python tests/smoke_import.py
```

## 运行时依赖与限制

- 目标机器仍需提供可解析的 `libisis.so`；
- 需要 Qt 相关共享库与相机/投影插件；
- 许多真实工作流仍需要正确配置 `ISISDATA`；
- 当前不承诺 Windows / macOS / 通用 PyPI wheel 支持。

## 校验建议

下载二进制资产后可执行：

```bash
sha256sum -c SHA256SUMS.txt
```

## 说明

如果你只需要该版本源码，直接使用 GitHub Release 自动生成的源码压缩包即可；通常不需要额外手工上传源码 `tar.gz`。
