# PyISIS v0.1.1 发布清单

## 构建与测试状态
- 目标提交：01792bd（添加 `__version__ = "0.1.0"` 并更新发布忽略项）
- 本地未能运行单测，原因：缺少外部 ISIS 运行时，`isis_pybind._isis_core` 无法在当前环境加载。
- 二进制包使用仓库中现有的 `_isis_core.cpython-312-x86_64-linux-gnu.so`，依赖 ISIS 9.0.0 及 Qt5/Camera 插件在目标机上可用。

## 产物路径（均已生成于 `dist/`）
- `pyisis-v0.1.0-source.tar.gz`：`git archive` 的源码包（HEAD）。
- `isis_pybind-v0.1.0-linux-x86_64-cp312-isis9.0.0.tar.gz`：完整 `isis_pybind/` 目录（`__init__.py`、`_isis_core.so`、`LICENSE`）。
- `SHA256SUMS.txt`：上述文件的校验和。

`SHA256SUMS.txt` 内容：
```
17c0de1da27db1327a57e1905147002d948567929e41e1657b5874f36c026fae  isis_pybind-v0.1.0-linux-x86_64-cp312-isis9.0.0.tar.gz
2cdac72bd0491d224506f0e8b9d1647debfec6d2f75d6ed83de5aa31d8028aab  pyisis-v0.1.0-source.tar.gz
```

## 发布上传步骤（GitHub Release 建议）
1. 标记版本：`git tag -a v0.1.0 01792bd -m "PyISIS v0.1.0"`.
2. 在 GitHub Release 创建 v0.1.0，描述中写明依赖：Linux x86_64、CPython 3.12、ISIS 9.0.0（含 Qt5、Camera *.so）。
3. 上传 `pyisis-v0.1.0-source.tar.gz`、`isis_pybind-v0.1.0-linux-x86_64-cp312-isis9.0.0.tar.gz`、`SHA256SUMS.txt`。
4. 在 Release 描述中粘贴 `SHA256SUMS.txt` 校验输出。

## 用户安装与验证（需已有 ISIS 9.0.0 环境）
### 1) 校验下载
```bash
sha256sum -c SHA256SUMS.txt
```

### 2) 直接使用二进制包
```bash
tar xzf isis_pybind-v0.1.0-linux-x86_64-cp312-isis9.0.0.tar.gz
export PYTHONPATH="$PWD/isis_pybind-v0.1.0-linux-x86_64-cp312-isis9.0.0${PYTHONPATH:+:$PYTHONPATH}"
python -c "import isis_pybind as ip; print(ip.__version__, hasattr(ip, 'Cube'))"
python tests/smoke_import.py  # 需要 ISIS 运行时及 Camera 库可被动态链接
```

### 3) 从源码构建（推荐用于可复现构建）
```bash
export ISIS_PREFIX="$CONDA_PREFIX"   # 已安装 ISIS 9.0.0 的环境
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" \
  -DISIS_PREFIX="$ISIS_PREFIX"
cmake --build build -j"$(nproc)"
cmake --install build
```
安装后再次运行：
```bash
python -c "import isis_pybind as ip; print(ip.__version__, hasattr(ip, 'Cube'))"
python tests/smoke_import.py
```

## 备注
- `_isis_core.so` 仍需目标机器提供 `libisis.so`、各 Camera 插件以及 Qt5 依赖，请确保相应路径在 `LD_LIBRARY_PATH`/`ISISROOT` 内。
- 如需重新生成二进制包，请在具备 ISIS 9.0.0 + Qt5 的 Linux x86_64 环境下重复“从源码构建”步骤，再重新打包 `isis_pybind/` 目录并更新校验和。
