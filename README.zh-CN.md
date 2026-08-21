<div align="right">

[English](./README.md) | [简体中文](./README.zh-CN.md)

</div>

# PyISIS

PyISIS 为 [USGS ISIS](https://astrogeology.usgs.gov/docs/software/isis/) 中
经过筛选、可稳定维护的非 GUI API 提供 Python 绑定，主要面向行星影像元数据、
Cube、相机模型、几何、地图投影、控制网和摄影测量处理。

项目提供两个 Python 层次：

- `pyisis`：推荐大多数用户使用的高层接口。
- `isis_pybind`：直接访问已经绑定的 ISIS C++ API。

二进制版本以 GitHub Release wheelhouse 压缩包发布，目前没有上传到 PyPI。

## 选择版本

请先选择 ISIS 版本，再下载对应操作系统的压缩包。ISIS 9 与 ISIS 10 使用不同的
Python ABI，必须安装到不同的虚拟环境中。

| ISIS 版本 | 发布状态 | Python | Linux | Windows |
| --- | --- | --- | --- | --- |
| ISIS 9.0.0 | **已发布：**[`v1.3.0rc3-isis9.0.0`](https://github.com/gengxun-henu/pyisis/releases/tag/v1.3.0rc3-isis9.0.0) | CPython 3.12 | x86_64，`manylinux_2_35` | x64，`win_amd64` |
| ISIS 10.0.0 | **已发布：**[`v1.4.0rc3-isis10.0.0`](https://github.com/gengxun-henu/pyisis/releases/tag/v1.4.0rc3-isis10.0.0) | CPython 3.13 | x86_64，`manylinux_2_35` | x64，`win_amd64` |

当前平台验证范围：

- Linux：Ubuntu 22.04 和 Ubuntu 24.04 清洁环境安装。
- Windows：Windows Server 2022 / Windows x64。
- 当前不发布 macOS、Linux ARM64 或 Windows ARM64 安装包。

## 安装 ISIS 9.0.0 版本

### 1. 下载并解压 wheelhouse

打开
[`v1.3.0rc3-isis9.0.0` Release](https://github.com/gengxun-henu/pyisis/releases/tag/v1.3.0rc3-isis9.0.0)，
根据操作系统下载一个压缩包：

- [Linux x86_64，CPython 3.12](https://github.com/gengxun-henu/pyisis/releases/download/v1.3.0rc3-isis9.0.0/pyisis-v1.3.0rc3-isis9.0.0-linux-x86_64-cp312-manylinux_2_35-wheelhouse.zip)
- [Windows x64，CPython 3.12](https://github.com/gengxun-henu/pyisis/releases/download/v1.3.0rc3-isis9.0.0/pyisis-v1.3.0rc3-isis9.0.0-windows-x64-cp312-wheelhouse.zip)
- [SHA256 校验和](https://github.com/gengxun-henu/pyisis/releases/download/v1.3.0rc3-isis9.0.0/SHA256SUMS.txt)

解压后，以下命令默认当前目录中存在 `wheelhouse/` 子目录。

### 2. Linux 安装

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --no-index --find-links wheelhouse \
  usgs-pyisis==1.3.0rc3
```

### 3. Windows 安装

在 PowerShell 中运行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --no-index --find-links wheelhouse `
  usgs-pyisis==1.3.0rc3
```

如果本机策略不允许执行 PowerShell 激活脚本，可以直接调用虚拟环境中的 Python：

```powershell
.\.venv\Scripts\python.exe -m pip install --no-index `
  --find-links wheelhouse usgs-pyisis==1.3.0rc3
```

### 4. 验证

```bash
python -c "import pyisis, isis_pybind as ip; print(ip.__version__, ip.__isis_version__); print(pyisis.data_status().message)"
```

版本信息应显示 PyISIS `1.3.0rc3` 和 ISIS `9.0.0`。

详细文档：

- [Linux / ISIS 9 安装说明](docs/releases/INSTALL-LINUX-ISIS9.0.0.md)
- [Windows / ISIS 9 安装说明](docs/releases/INSTALL-WINDOWS-ISIS9.0.0.md)
- [ISIS 9 发布说明](docs/releases/v1.3.0rc3-isis9.0.0.md)

## 安装 ISIS 10.0.0 版本

ISIS 10 使用独立分发包和 Python ABI：

| 项目 | ISIS 10 版本 |
| --- | --- |
| Release | [`v1.4.0rc3-isis10.0.0`](https://github.com/gengxun-henu/pyisis/releases/tag/v1.4.0rc3-isis10.0.0) |
| 顶层分发包 | `usgs-pyisis-isis10` |
| Python | CPython 3.13 |
| Linux 安装包 | [`pyisis-v1.4.0rc3-isis10.0.0-linux-x86_64-cp313-manylinux_2_35-wheelhouse.zip`](https://github.com/gengxun-henu/pyisis/releases/download/v1.4.0rc3-isis10.0.0/pyisis-v1.4.0rc3-isis10.0.0-linux-x86_64-cp313-manylinux_2_35-wheelhouse.zip) |
| Windows 安装包 | [`pyisis-v1.4.0rc3-isis10.0.0-windows-x64-cp313-wheelhouse.zip`](https://github.com/gengxun-henu/pyisis/releases/download/v1.4.0rc3-isis10.0.0/pyisis-v1.4.0rc3-isis10.0.0-windows-x64-cp313-wheelhouse.zip) |

下载并解压对应操作系统的压缩包。Release 同时提供
[`SHA256SUMS.txt`](https://github.com/gengxun-henu/pyisis/releases/download/v1.4.0rc3-isis10.0.0/SHA256SUMS.txt)。

Linux：

```bash
python3.13 -m venv .venv-isis10
source .venv-isis10/bin/activate
python -m pip install --upgrade pip
python -m pip install --no-index --find-links wheelhouse \
  usgs-pyisis-isis10==1.4.0rc3
```

Windows PowerShell：

```powershell
py -3.13 -m venv .venv-isis10
.\.venv-isis10\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --no-index --find-links wheelhouse `
  usgs-pyisis-isis10==1.4.0rc3
```

ISIS 10 包继续使用相同的导入名称：

```python
import pyisis
import isis_pybind
```

包内包含运行时版本保护，避免 ISIS 10 绑定错误加载 ISIS 9 运行库。请勿在同一个
环境中同时安装两个版本线。

详细文档：

- [ISIS 9/10 绑定兼容方案](docs/isis9-isis10-binding-compatibility-plan.md)
- [Linux / ISIS 10 安装说明](docs/releases/INSTALL-LINUX-ISIS10.0.0.md)
- [Windows / ISIS 10 安装说明](docs/releases/INSTALL-WINDOWS-ISIS10.0.0.md)
- [ISIS 10 发布说明](docs/releases/v1.4.0rc3-isis10.0.0.md)

## ISISDATA

每个 Release wheelhouse 只包含用于导入和 smoke test 的最小 ISISDATA。真实相机、
SPICE、辐射检校和任务数据处理仍然需要完整的外部 ISISDATA。

Linux：

```bash
export ISISDATA=/path/to/isisdata
```

Windows PowerShell：

```powershell
$env:ISISDATA = "D:\isisdata"
```

完整 ISIS 环境和数据应按照官方说明安装：

- [安装 ISIS](https://astrogeology.usgs.gov/docs/how-to-guides/environment-setup-and-maintenance/installing-isis-via-anaconda/)
- [ISIS 数据区](https://astrogeology.usgs.gov/docs/how-to-guides/environment-setup-and-maintenance/isis-data-area/)

## 基本使用

常见操作优先使用高层接口：

```python
import pyisis

with pyisis.open_cube("image.cub") as cube:
    print(pyisis.cube_dimensions(cube))
    print(pyisis.ground_at_center(cube))
```

需要直接访问绑定的 ISIS 类时使用低层包：

```python
import isis_pybind as ip

print("PyISIS:", ip.__version__)
print("编译目标 ISIS:", ip.__isis_version__)
```

[`examples/`](examples/) 中提供了相机几何、前方交会、地图投影、控制网和影像匹配等
示例。

### 深度匹配工作流

ControlNet 深度匹配支持 `direct / export / import` 三种工作流：依赖齐全时可在当前
进程中直接运行 `direct`；`asp360_new` 缺少 LightGlue、LoFTR 或 SuperGlue 等依赖
时，先用 `export` 导出任务，再进入 `deep-learning` conda 环境运行
[`run_deep_match_manifest.py`](examples/learning_methods/run_deep_match_manifest.py)，最后
回到 ISIS 环境使用 `import` 继续 ControlNet 流程。

批处理 wrapper 会把导入、导出数量和各影像对状态汇总到
`deep_match_manifests.json`。各 matcher preset 的依赖环境、运行支持和已知限制见
[`PRESETS_README.md`](examples/controlnet_construct/PRESETS_README.md)。

## Release 中包含什么

每个压缩包都是可离线安装的 wheelhouse。用户只需按照上面的命令安装顶层分发包，
pip 会在本地解析其余依赖。

- Linux：主绑定 wheel 已包含审核后的共享库运行时闭包，并带有独立的最小
  ISISDATA wheel。
- Windows：包含绑定 wheel、独立的 ISIS 运行库/依赖 wheel 和最小 ISISDATA
  wheel。

用户不需要手工逐个选择或安装依赖 wheel。

## 功能范围和限制

PyISIS 是精选 Python 接口，不是所有 ISIS C++ 类的完整 Python 镜像。

当前包含：

- 经过筛选的稳定非 GUI ISIS API。
- Python 高层辅助接口和直接低层绑定。
- 上述目标平台的 Linux 与 Windows wheelhouse。
- 对应绑定流程的测试和示例。

当前不包含：

- 完整 ISISDATA。
- 所有 ISIS C++ 类、Qt signal、slot 或 GUI 子系统。
- Windows 上完整的 ISIS 原生 APP 程序套件。
- `qview`、`qnet`、`qmos` 等原生 GUI 程序。

Linux 用户需要 `cam2map`、`spiceinit` 或任务导入程序等原生命令行 APP 时，可以
另外安装官方 ISIS。Windows 原生 ISIS APP 属于后续独立开发路线，不属于当前
PyISIS wheel 的交付范围。

维护中的支持边界见 [`docs/platform-support.md`](docs/platform-support.md)。

## 源码构建

源码构建适用于已经准备好匹配 ISIS 开发环境的开发人员。本仓库使用 conda 管理
编译器和依赖，不应混用系统编译器与 conda ISIS 库。

绑定签名和编译判断以当前 ISIS 环境中的头文件与库为准。构建前请阅读
[`AGENTS.md`](AGENTS.md)，并参考对应 ISIS 版本和操作系统的安装文档。

## 问题反馈

请在 [GitHub Issues](https://github.com/gengxun-henu/pyisis/issues) 中提供：

- 操作系统和架构；
- Python 版本；
- ISIS 版本线和 PyISIS 版本；
- wheelhouse 资产名称或源码提交；
- 完整错误输出；
- 是否已经配置完整 ISISDATA。

## 许可证

本仓库编写的绑定层和 Python 代码使用 [MIT License](LICENSE)。USGS ISIS、打包的
运行时依赖以及外部数据仍分别遵循其自身许可证。
