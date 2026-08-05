# PyISIS 与原生 ISIS APP 跨平台发布拆分设计

## 1. 背景

本仓库同时承担两类不同工作：

1. 将选定的 ISIS C++ API 通过 pybind11 暴露给 Python；
2. 将 ISIS 原生动态库和 APP 移植到 Windows。

两类工作当前共享 ISIS 源码、补丁、构建 prefix 和部分打包工具，但面向的
用户、ABI、验证要求和发布节奏不同。Windows runtime staging 目前会收集
`bin/**/*.exe`，可能把原生 APP 混入服务于 Python 的 runtime wheel；另一边，
Windows APP 已有独立 manifest 和构建工作流，但工作流只上传 smoke 日志，
没有发布可安装的 runtime 或 APP 包。

Linux 不存在相同的 APP 分发缺口。Linux 用户可以通过官方 conda ISIS 获得
原生 runtime 和 APP，因此本项目不重复发布 Linux Native Apps 二进制包。
Linux 官方 conda ISIS 仍作为 Windows 移植的行为和数值对比基线。

## 2. 目标

- 将 PyISIS Python bindings、PyISIS minimal native runtime 和 ISIS Native Apps
  定义为职责清晰的发布单元。
- 保持 PyISIS wheelhouse 安装后即可导入，不要求用户预装系统 ISIS。
- 为 Windows 原生 runtime 和 APP 建立独立于 PyISIS 的版本与发布流程。
- 在 Linux 和 Windows 上采用统一的 APP inventory、状态和测试语义。
- 使用官方 Linux conda ISIS 作为 APP 基线，但第一阶段只发布 Windows Native
  Apps 二进制资产。
- 防止 PyISIS 发布被完整 APP 矩阵阻塞，也防止 APP 发布被无关 Python 测试阻塞。

## 3. 非目标

- 不在第一阶段移植 `qview`、`qnet` 或 `qmos`。
- 不重新发布官方 Linux ISIS APP 套件。
- 不把完整 ISISDATA 放进 PyISIS wheelhouse 或 Native Apps 包。
- 不在本次拆分中增加新的 ISIS APP 或 pybind 类。
- 不立即大规模迁移现有仓库目录。

## 4. 产品边界

### 4.1 PyISIS Python bindings

该产品包含：

- `pyisis` 高层接口；
- `isis_pybind` 直接绑定接口；
- `_isis_core.pyd` 或 `_isis_core.so`；
- Python facade、版本元数据和必要的 Python 支持文件。

它不包含通用 ISIS APP、GUI APP 或完整 ISISDATA。其兼容身份由 PyISIS 版本、
Python ABI、ISIS ABI、操作系统和架构共同决定。

### 4.2 PyISIS minimal native runtime

该产品是 PyISIS wheelhouse 的内部依赖，包含 `_isis_core` 实际运行所需的：

- `isis.dll` 或 `libisis.so`；
- Camera 和其他必要插件；
- SPICE、CSM、Qt 等依赖闭包；
- `IsisPreferences` 和导入、smoke 所需资源。

它明确排除：

- `reduce.exe`、`cam2map.exe` 等 APP；
- APP XML 帮助文件；
- 开发头文件、静态库和 import library；
- GUI APP；
- 完整 ISISDATA。

PyISIS wheelhouse 继续自动携带该 runtime，使用户安装后能够直接
`import isis_pybind`。Linux 和 Windows 使用相同的产品边界，但允许采用不同的
wheel 内部布局和动态库修复机制。

### 4.3 ISIS Native Runtime

Windows Native Runtime 是不依赖 Python 的独立发布物，包含运行已发布 Windows
APP 所需的公共 DLL、插件、配置和基础资源。它可以比 PyISIS minimal runtime
更完整，因为全部 APP 的动态依赖闭包通常大于 `_isis_core` 的依赖闭包。

PyISIS minimal runtime 与 Windows Native Runtime 可以从同一个已验证 build
prefix 生成，但不是同一个发布包，也不得互相隐式替代。

### 4.4 ISIS Native Apps

Windows Native Apps 包含原生 `.exe`、对应 APP XML、APP 专属插件和组件清单，
不包含 Python 模块，也不依赖 Python ABI。

APP 分为：

- `apps-base`：通用处理、投影、统计和基础输入输出；
- `apps-control`：控制网和 bundle adjustment；
- `apps-mission`：任务导入、检校和任务 pipeline；
- `apps-gui`：`qview`、`qnet`、`qmos` 及 GUI 专属依赖，后续发布。

组件包不重复携带公共 runtime，而是声明准确的 Native Runtime 依赖。发布流程
可以机械合并 runtime 和已验证组件，生成方便最终用户使用的 CLI suite ZIP；
组合包不是新的构建或版本来源。

### 4.5 ISISDATA

PyISIS wheelhouse 只携带 import 和 smoke 所需的 minimal ISISDATA。真实相机、
SPICE、辐射检校和任务处理要求用户配置完整外部 ISISDATA。Native Apps 的安装
诊断必须区分“程序或 DLL 缺失”和“业务数据缺失”。

## 5. 平台策略

### 5.1 Linux

- 本项目发布 PyISIS bindings 和其自包含 minimal runtime。
- Linux Native Apps 和完整 native runtime 由官方 conda ISIS 提供。
- 本项目记录作为权威基线的 conda channel、subdir、版本、build string、平台
  和包身份。
- Linux 官方 APP 用于参数、帮助、行为和数值基线生成。
- 本项目不发布重复的 Linux Native Apps ZIP、TAR 或 conda 包。

### 5.2 Windows

- 本项目发布 PyISIS wheelhouse，其中包含 PyISIS minimal runtime。
- 本项目独立发布 Windows ISIS Native Runtime。
- 本项目独立发布 Windows Native Apps 组件和可选组合包。
- CLI 与 GUI 分开，GUI 不得成为 core、PyISIS 或 CLI 组件的依赖。
- Windows APP 使用同版本 Linux 官方 conda ISIS 作为对比基线。

## 6. 版本与资产命名

### 6.1 PyISIS 发布线

PyISIS 使用独立语义版本，例如 `1.4.0rc2`。资产继续编码 ISIS 版本、平台、
架构和 Python ABI，例如：

```text
pyisis-v1.4.0rc2-isis10.0.0-linux-x86_64-cp313-wheelhouse.zip
pyisis-v1.4.0rc2-isis10.0.0-windows-x64-cp313-wheelhouse.zip
```

只修改 Python facade 时可以提升 PyISIS 版本而不发布新的 Native Apps。

### 6.2 Native Windows 发布线

Native Windows 使用“上游 ISIS 版本 + Windows port revision”，例如
`10.0.0-r1`。建议发布标签：

```text
isis-native-windows-10.0.0-r1
```

建议资产：

```text
isis-native-runtime-10.0.0-windows-x64-r1.zip
isis-native-apps-base-10.0.0-windows-x64-r1.zip
isis-native-apps-control-10.0.0-windows-x64-r1.zip
isis-native-apps-mission-10.0.0-windows-x64-r1.zip
isis-native-apps-gui-10.0.0-windows-x64-r1.zip
isis-native-cli-suite-10.0.0-windows-x64-r1.zip
SHA256SUMS.txt
compatibility-manifest.json
```

`apps-gui` 只在 GUI 验收完成后生成。APP component 必须声明准确的
`requires_runtime`。不同 port revision 默认不允许混用，除非兼容性清单明确
记录验证证据。

### 6.3 兼容身份

每个发布物至少记录：

- 上游 ISIS tag 和 commit；
- conda 参考包的 channel、subdir、version 和 build string；
- Windows patch queue 身份；
- Windows port revision；
- OS、架构和 Python ABI（如适用）；
- 文件哈希和构建 provenance。

## 7. 构建与打包数据流

Windows 构建生成一个包含 headers、libraries、DLL、EXE、XML 和资源的完整内部
prefix。该 prefix 仅作为 CI 中间产物，不得直接发布。

```text
ISIS source + Windows patches + conda build environment
                         |
                         v
               complete build prefix
                  /       |       \
                 v        v        v
         PyISIS build  native    native APP
                       runtime    components
```

### 7.1 PyISIS 路径

1. 使用 SDK prefix 编译 `_isis_core`。
2. 从 `_isis_core` 计算实际 DLL/shared-library 依赖闭包。
3. 加入必需插件、配置和 smoke 资源。
4. 拒绝任何 APP executable 和 APP XML 进入 minimal runtime。
5. 生成并 clean-install 测试 wheelhouse。

### 7.2 Native Runtime 路径

1. 根据独立 runtime manifest 从完整 prefix 选择文件。
2. 验证 DLL closure、插件和配置。
3. 生成与 Python 无关的 runtime ZIP。
4. 在空目录解压并执行 load probe。

### 7.3 Native Apps 路径

1. 根据 component manifest 选择 EXE、XML 和专属资源。
2. 验证每个 APP 都属于唯一且明确的组件。
3. 验证 APP 声明的 runtime revision。
4. 分别生成 component ZIP。
5. 机械合并 runtime 与 release-ready components，生成可选 CLI suite。

## 8. Manifest 与状态模型

跨平台信息分为两层：

1. 产品清单：APP 名称、component、数据要求、是否 GUI；
2. 平台证据：Linux conda 身份、Windows build 状态、smoke、行为与数值结果。

统一状态为：

```text
discovered
implementation_ready
compiled
installed
startup_passed
behavior_passed
cross_platform_passed
release_ready
```

状态必须单向推进，并由机器可读证据支持。只有 `release_ready` 的 APP 进入正式
组件资产。未达到该状态的 APP 可以进入明确标识的 experimental 资产，但不得
被描述为正式支持。

第一阶段保留 `ports/windows/isis/windows-app-manifest.json` 作为 Windows 构建和
状态来源，避免高风险迁移。新增发布清单放在：

```text
packaging/native-windows/
  runtime-manifest.json
  components/apps-base.json
  components/apps-control.json
  components/apps-mission.json
  components/apps-gui.json
  release-layout.json
```

Linux 基线和跨平台结果放在 `reference/native-apps/`。

## 9. CI 职责

### 9.1 PyISIS wheel workflow

现有 wheel workflow 只负责：

- Linux/Windows × ISIS 9/10 bindings；
- minimal runtime 和 minimal ISISDATA；
- clean wheel install；
- import、ABI、依赖闭包和 focused binding tests；
- PyISIS GitHub Release。

它不构建完整 Native APP 矩阵。APP 未通过不得阻塞与 APP 无关的 PyISIS 发布。

### 9.2 Windows Native ISIS workflow

Windows Native workflow 负责：

- 获取锁定的上游 ISIS 源码并应用 patch queue；
- 构建和安装 native runtime 与 manifest APP；
- 从完整 prefix 生成 runtime 和 component ZIP；
- clean-extract 验证；
- 上传候选安装包、日志、清单、哈希和 provenance。

工作流不得再只上传 smoke 日志。

### 9.3 跨平台验证 workflow

独立 workflow 在 Linux 使用锁定的官方 conda ISIS，在 Windows 使用候选 Native
Apps。双方处理相同输入，并比较：

- APP 名称、参数和帮助；
- 退出码和诊断；
- PVL 标签、表格和影像尺寸；
- 统计量和具名数值容差；
- 任务特定输出。

大型真实数据测试只在手动 dispatch、发布候选、相关 APP/patch 变更或定期验证
时运行。

## 10. 发布门禁

### 10.1 PyISIS

- Linux/Windows × ISIS 9/10 构建通过；
- clean wheel install 通过；
- `import pyisis` 和 `import isis_pybind` 通过；
- runtime ABI 和依赖闭包通过；
- focused binding tests 通过；
- wheel hash 和 provenance 已生成。

### 10.2 Native Windows

- runtime ZIP clean-extract 和 load probe 通过；
- DLL closure 完整；
- 每个正式 APP 的 startup test 通过；
- base APP 的真实 Cube smoke 通过；
- component manifest 完整；
- 关键 APP 的 Linux/Windows 行为与数值比较通过；
- ZIP hash 和 provenance 已生成。

Native Apps 发布不要求运行无关的完整 PyISIS 单元测试。修改共享 ABI、核心 DLL
或共同 patch 时，两条发布线的相关门禁都必须运行。

## 11. 激活与错误处理

Windows Native 组合包提供 `activate.ps1`，设置 `ISISROOT`、`ISIS_PREFIX`、`PATH`
和必要插件路径。它必须在修改环境前验证 runtime 与 component revision。

- PyISIS 缺少动态库时，报告缺失库和期望 runtime 身份。
- PyISIS 与 ISIS major 不匹配时，导入立即失败。
- APP 与 runtime revision 不匹配时，`activate.ps1` 拒绝激活。
- APP 未安装时，诊断指出需要的 component。
- 缺少完整 ISISDATA 时，诊断不得误报为程序安装或 DLL 问题。
- 跨平台比较失败时，APP 不得进入 `release_ready`，但不阻塞无关 PyISIS 发布。

## 12. 第一阶段实施范围

1. 修改 Windows PyISIS runtime staging，排除所有 APP EXE 和 APP XML。
2. 增加 Native Windows runtime manifest 与 component manifests。
3. 让 Windows Native workflow 上传 runtime 和 APP ZIP，而不只上传日志。
4. 以 `reduce` 建立 build、install、package、clean-extract、真实 Cube smoke 和
   Linux 对比的完整样板。
5. 样板通过后，对现有 129 个已通过 compile/install/startup 的 Windows APP
   分批补齐 behavior 和跨平台证据；只有达到 `release_ready` 的 APP 才纳入
   正式组件。
6. 其余 APP 保持实验状态，直到相应证据通过。
7. `apps-gui` 和 `qview/qnet/qmos` 留到独立后续设计与实施周期。

## 13. 验收标准

- PyISIS Windows wheelhouse 中不存在 ISIS APP executable。
- PyISIS Linux 和 Windows wheelhouse 均可在干净 Python 环境中直接导入。
- Windows Native Runtime 可在无 Python 环境中激活和加载。
- `reduce` 可从独立 Native Apps 安装包运行真实 Cube smoke。
- `reduce` 的 Windows 结果与锁定的 Linux conda ISIS 基线在定义容差内一致。
- PyISIS 和 Native Windows 使用独立标签、资产、哈希和发布说明。
- 修改纯 Python facade 不触发完整 Native APP 构建。
- 修改 Windows APP manifest 或 patch 不阻塞无关 PyISIS 发布。
