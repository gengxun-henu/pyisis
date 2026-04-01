# GitHub Actions 构建与测试设置步骤

本文档说明如何在当前仓库中启用并使用 `isis_pybind_standalone` 的 GitHub Actions CI。

以下说明默认 **`isis_pybind_standalone` 本身就是 GitHub 上的独立仓库根目录**，并且 workflow 主要运行在你自己的 **self-hosted runner（本机 PC）** 上。

对应 workflow 文件：`.github/workflows/ci-pybind.yml`

---

## 1. 先确认仓库里已经有这些文件

在当前仓库根目录下确认以下文件存在：

- `.github/workflows/ci-pybind.yml`
- `CMakeLists.txt`
- `tests/smoke_import.py`
- `tests/data/isisdata/mockup`

这套 CI 的前提不是编当前仓库里的 ISIS 源码，而是直接复用一个**外部 ISIS / conda 前缀**，并要求它至少包含：

- `include/isis`
- `lib/libisis.so`
- `lib/Camera.plugin`

workflow 会优先使用 runner 已经提供的 `CONDA_PREFIX`。如果 runner 没有预先设置 `CONDA_PREFIX`，当前版本会回退到：

- `/home/gengxun/miniconda3/envs/asp360_new`

---

## 2. 提交 workflow 文件到 GitHub

把以下文件提交到仓库：

- `.github/workflows/ci-pybind.yml`
- `Github_actions_build_test_steps.md`

建议提交后推送到 `main` 或一个测试分支，再让 GitHub Actions 自动触发。

---

## 3. 在 GitHub 网页里开启 Actions 权限

打开仓库页面后按下面步骤检查：

1. 进入 `Settings`
2. 打开左侧的 `Actions` → `General`
3. 确认仓库允许运行 GitHub Actions workflow
4. 在 `Workflow permissions` 中选择：
   - `Read repository contents permission`

对于当前这份 workflow，`contents: read` 就够用了，不需要额外写权限。

---

## 4. 如果仓库开启了分支保护，建议把 CI 设成必过项

如果你希望 PR 合入前必须通过 pybind CI，可以继续设置：

1. 进入 `Settings`
2. 打开 `Branches`
3. 编辑目标分支（例如 `main`）的保护规则
4. 在 required status checks 中加入：
   - `Build and test isis_pybind_standalone`

这样 PR 想合并时，必须先通过这条 workflow。

---

## 5. 这份 workflow 实际做了什么

`ci-pybind.yml` 的执行流程如下：

1. checkout 仓库（含 Git LFS）
2. 优先读取 runner 已有的 `CONDA_PREFIX`
3. 如果 `CONDA_PREFIX` 没有设置，则回退到 `/home/gengxun/miniconda3/envs/asp360_new`
4. 检查外部 ISIS 前缀是否完整：
   - `include/isis`
   - `lib/libisis.so`
   - `lib/Camera.plugin`
5. 设置运行时环境变量：
   - `ISIS_PREFIX`
   - `ISISROOT`
   - `ISISDATA`
   - `LD_LIBRARY_PATH`
   - `CMAKE_PREFIX_PATH`
   - `PYTHON_BIN`
6. 使用 CMake 配置 `isis_pybind_standalone`
7. 编译 `_isis_core`
8. 运行 `ctest --output-on-failure`
9. 单独运行 `tests/smoke_import.py`

这三层验证很重要：

- build 通过：说明能编
- `ctest` 通过：说明注册的 unit tests 通过
- `smoke_import.py` 通过：说明模块导入和基础符号检查通过

只做 build 不够，因为 unresolved symbol 和顶层导出漏项这类问题，经常要到 import 阶段才会暴露。

---

## 6. 触发方式

这份 workflow 支持 3 种触发方式：

### 方式 A：push 自动触发

当以下路径有变更并 push 到 `main` 时会触发：

- `.github/workflows/ci-pybind.yml`
- `Github_actions_build_test_steps.md`
- `CMakeLists.txt`
- `environment.yml`
- `python/**`
- `src/**`
- `tests/**`

### 方式 B：PR 自动触发

当 PR 中包含以上路径变更时会自动触发。

### 方式 C：手动触发

进入 GitHub 仓库页面：

1. 点击 `Actions`
2. 选择 `ci-pybind`
3. 点击 `Run workflow`

这个方式很适合你改完 workflow 之后手工回归一次。

---

## 7. 第一次运行后你应该看哪里

进入：`GitHub 仓库 → Actions → ci-pybind → 最新一次运行`

重点看这几个 step：

### `Resolve conda-backed ISIS prefix`

如果失败，通常是：

- runner 没有传入 `CONDA_PREFIX`
- fallback 路径 `/home/gengxun/miniconda3/envs/asp360_new` 不存在
- 目标前缀中缺少 `include/isis`、`lib/libisis.so` 或 `lib/Camera.plugin`

### `Verify external ISIS prefix`

如果失败，说明装到的 ISIS 前缀不完整，重点看是否缺：

- `include/isis`
- `lib/libisis.so`
- `lib/Camera.plugin`

### `Configure CMake`

如果失败，通常重点排查：

- `pybind11` 没被找到
- `Qt5` 没被找到
- `Python3_EXECUTABLE` 与环境不一致
- `ISIS_PREFIX` 没传进去

### `Run CTest suite`

如果失败，说明 `tests/unitTest/*_unit_test.py` 中至少有一处失败。

### `Run smoke import`

如果失败，优先看：

- unresolved symbol
- 段错误 / 进程被 kill
- `__init__.py` 顶层导出缺项

---

## 8. 这份 workflow 依赖的关键环境变量

workflow 会自动设置：

- `ISIS_PREFIX=$CONDA_PREFIX`
- `ISISROOT=$CONDA_PREFIX`
- `ISISDATA=$GITHUB_WORKSPACE/tests/data/isisdata/mockup`
- `CMAKE_PREFIX_PATH=$CONDA_PREFIX`
- `PYTHON_BIN=$CONDA_PREFIX/bin/python`

其中：

- `ISIS_PREFIX`：给 CMakeLists.txt 用
- `ISISROOT`：给 ISIS 运行时逻辑用
- `ISISDATA`：给测试数据与内核查找用
- `CMAKE_PREFIX_PATH`：让 CMake 优先从目标 conda 前缀寻找 Python、pybind11、Qt 和 ISIS 相关依赖
- `PYTHON_BIN`：确保 configure、ctest 和 smoke import 使用同一个 Python 解释器

如果以后你改了 mockup 数据路径，记得同步更新 workflow。

如果你把 self-hosted runner 的启动脚本配置成总是导出正确的 `CONDA_PREFIX`，workflow 就会优先使用它；fallback 路径只是一个保底兜底方案。

---

## 9. 当前方案为什么不需要 checkout ISIS 源码

当前 `isis_pybind_standalone` 的构建方式已经确认依赖的是**已安装好的 ISIS 前缀**，不是当前仓库里的 ISIS 源码。

也就是说，CI 真正需要的是：

- 外部头文件：`include/isis`
- 外部库：`lib/libisis.so`
- 外部插件：`lib/Camera.plugin`

因此 workflow 里不需要再单独编一遍 ISIS 主工程。这样更简单，也更贴近你本地已经验证通过的工作方式。

---

## 10. 如果 CI 失败，建议排查顺序

推荐按这个顺序排：

1. 先看 `Resolve conda-backed ISIS prefix`
2. 再看 `Verify external ISIS prefix`
3. 再看 `Configure CMake`
4. 再看 `Build extension`
5. 再看 `Run CTest suite`
6. 最后看 `Run smoke import`

如果是 native 崩溃或 unresolved symbol，优先怀疑：

- 某个绑定连到了运行时不存在的符号
- 某个头文件里声明了方法，但外部 `libisis.so` 没导出
- 某个方法在源码里根本没有实现，却被误绑进来了

这一类问题通常不是 workflow 写错，而是绑定层需要继续收敛。

---

## 11. 后续建议

在这份最小可用 CI 跑稳之后，建议你下一步再加：

1. `fail-fast: false` 的多版本矩阵（如果你未来要验证多个 Python 版本）
2. 构建缓存命中率观察
3. 失败日志或测试报告归档
4. 只跑特定 unit test 文件的临时调试 workflow

当前阶段先把单 job 的主链路打通最重要，先别让矩阵把问题放大成烟花秀。

---

## 12. 一句话使用说明

你现在要做的最小动作就是：

1. 提交 `.github/workflows/ci-pybind.yml`
2. push 到 GitHub
3. 打开 `Actions` 页面
4. 看 `ci-pybind` 是否按预期完成：
   - 找到正确的 conda / ISIS 前缀
   - 找到外部 ISIS 前缀
   - CMake 配置成功
   - build 成功
   - `ctest` 成功
   - `smoke_import.py` 成功

如果这 6 项都绿了，说明这条 pybind CI 主链路已经能稳定替你守门。
