# pyISIS packaging and release guide

日期：2026-03-17  
作者：Geng Xun（默认元数据）

本文件聚焦 `isis_pybind_standalone` 的安装、打包、发布与兼容性策略。

## 1. 目标

发布目标不是“开发机能 import”，而是：

- 用户能稳定安装
- 依赖关系可表达
- Python / ABI 兼容范围清晰
- 运行时动态库可解析
- 发布后问题能快速定位

## 2. 当前项目形态

`isis_pybind_standalone` 当前是外挂式构建：

- 不直接并入主 ISIS CMake 构建
- 将现有 ISIS 安装视为外部 SDK / runtime
- 通过 `ISIS_PREFIX` 指向外部 ISIS 环境

因此，它天然更适合先作为**独立 conda 包**演进，而不是直接依赖手工拷贝。

## 3. 为什么“手工拷贝即用”不适合作为正式方案

虽然在内部临时使用中，用户可能可以把构建出的包目录或 `.so` 拷到某个环境中，但正式发布不建议这样做，因为风险包括：

- Python ABI 不匹配
- C++ ABI 不匹配
- `libstdc++` / 编译器 runtime 差异
- `libisis.so` 无法解析
- Qt / Bullet / camera / projection 相关库冲突
- build-tree 可用但 install-tree 或用户环境失败

结论：

- **内部临时使用**：可以接受
- **正式对外分发**：不推荐

## 4. 推荐分发路线

### 4.1 短中期：独立 conda 包

建议将 `isis_pybind_standalone` 做成独立包，例如：

- `isis-pybind`

并在运行时依赖中显式依赖：

- 对应版本范围的 `isis` 主包

优点：

- 可表达依赖关系
- 可绑定 Python 与 ISIS 版本
- 用户安装路径清晰
- 更适合科研用户与 conda 环境

### 4.2 长期：评估并入主 ISIS 包

如果将来绑定层稳定、用户群体明确、维护成本可控，可以再评估：

- 将 Python 绑定并入主 ISIS 包统一构建和发布

## 5. Conda 发布建议

### 5.1 先做自有 channel

在考虑 `conda-forge` 之前，建议先：

- 编写独立 recipe
- 在自有 channel 上完成打包与安装验证
- 稳定 1~2 个版本
- 明确依赖 pinning 与兼容矩阵

### 5.2 独立包建议

- 包名：`isis-pybind`
- 首发平台：`linux-64`
- Python：只支持已验证 ABI 的版本
- ISIS：与主包版本严格绑定或小范围兼容绑定

### 5.3 必须验证的内容

- build-tree import
- install-tree import
- `_isis_core` 加载
- `libisis.so` / Qt / Bullet / camera / projection 库解析
- 干净 conda 环境中的真实安装流程

## 6. conda-forge 策略

`conda-forge` 可以作为目标，但不建议作为第一步。

适合进入 `conda-forge` 的前提：

- recipe 已稳定
- 依赖链清晰
- 许可证与第三方依赖可公开分发
- 构建流程标准化
- CI 可稳定产出

推荐节奏：

1. 先在自有 channel 跑通
2. 再评估 `conda-forge`
3. 避免过早增加维护复杂度

## 7. 发布前必须确认的兼容项

### Python / ABI

- 目标 Python 版本与扩展 ABI 一致
- 若切换 Python 主版本，必须重新构建并重新验证

### ISIS / runtime

- `ISIS_PREFIX` 指向正确的 ISIS 环境
- `libisis.so` 可解析
- `Camera.plugin` 路径有效
- 需要的 camera / projection 动态库可解析

### 安装路径

- `cmake --install` 后 `site-packages` 中能正常导入
- 安装后的 `isis_pybind` 包目录中应显式包含 `LICENSE`
- 不仅 build tree 可用，install tree 也必须可用

## 8. 推荐发布验证流程

1. 在 ABI 匹配解释器中完成构建
2. 运行 focused unit tests 与 smoke test
3. 执行 `cmake --install`
4. 在安装后的环境中验证 `import isis_pybind`
5. 确认安装后的 `isis_pybind` 包目录中存在 `LICENSE`
5. 在干净 conda 环境中安装并运行最小工作流
6. 核对文档、版本、变更说明

## 9. 与 CI / 模板的关系

建议每次涉及以下内容时，使用专门的 PR / Issue 模板：

- 打包方式变化
- 依赖 pinning 变化
- Python 版本切换
- ISIS 版本兼容范围变化
- import / loader / runtime 解析问题

相关文件：

- `.github/PULL_REQUEST_TEMPLATE/pyisis_release_and_packaging.md`
- `.github/ISSUE_TEMPLATE/5_pyisis_packaging_release_issue.md`

## 10. 相关文件

- `CMakeLists.txt`
- `README.md`
- `pyisis-发布前检查清单.md`
- `pyisis-开发测试指标原则.md`
- `testing.md`
