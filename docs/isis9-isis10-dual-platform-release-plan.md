# ISIS 9 / ISIS 10 双版本绑定与跨平台发布规划

> 状态：Linux ISIS 9/10 与 Windows ISIS 9 的 CI 构建和干净安装已通过；
> Windows ISIS 10 在 ISIS prefix 的 `mgs.dll`/SpiceQL 链接阶段阻塞。
> 当前先关闭现有绑定的双版本兼容队列，再继续新增 ISIS 10 绑定。
>
> 更新日期：2026-07-24。本规划不表示 ISIS 10 已获得稳定支持；每条产品线
> 仍需分别通过对应验收门槛。

## 1. 目标

在同一仓库和同一套绑定源码上，持续提供以下四条受控产品线：

| ISIS 版本线 | Linux x86_64 | Windows x64 |
| --- | --- | --- |
| ISIS 9.x（基线 9.0.0） | 开发环境、绑定构建、安装包 | 开发环境、绑定构建、安装包 |
| ISIS 10.x（基线 10.0.0） | 开发环境、绑定构建、安装包 | 开发环境、绑定构建、安装包；先通过源码移植门槛 |

用户侧继续使用相同的 Python import：

```python
import pyisis
import isis_pybind
```

ISIS 9 与 ISIS 10 安装在不同的 conda 环境中，不允许两个 runtime 共存于同一环境。

## 2. 当前基础与关键约束

当前仓库已经具备以下基础：

- 核心扩展为 `isis_pybind._isis_core`，由外部 `ISIS_PREFIX` 提供 ISIS 头文件和库。
- Linux 与 Windows 已有各自的 runtime staging 工具。
- Windows ISIS 9.0.0 已有源码获取、补丁、构建、安装和验证脚本。
- Windows CPython 3.12 wheel 已有 CI 原型；Linux runtime wheel 已有本地构建骨架。

需要解决的主要问题：

- README、Windows 脚本、补丁队列和 wheel 工作流目前固定在 ISIS 9.0.0。
- 主包和 runtime 包名没有 ISIS ABI 主版本维度。
- `_isis_core` 尚未导出编译时 ISIS 版本，无法检测绑定与 runtime 是否匹配。
- ISIS 9 与 ISIS 10 可能存在头文件、签名、符号和行为差异。
- 现有 Windows ISIS 补丁不能未经验证直接应用于 ISIS 10。

当前 ISIS 9 跨平台基线已经发布为 `v1.3.0rc1-isis9.0.0`。Linux wheel 使用
manylinux 构建与 `auditwheel` 修复，Windows wheel 使用 GitHub 托管 runner
和 ISIS prefix 缓存。ISIS 10 工作必须在不降低这条既有产品线的前提下推进。

## 3. 官方发行现状与规划边界

截至 2026-07-22：

- USGS 将 ISIS 10.0.0 定义为新的主版本/LTS 线，并明确主版本可能包含破坏性更新。
- USGS Anaconda channel 已提供 ISIS 10.0.0；官方包页面列出的平台包括 Linux x86_64、macOS x86_64 和 macOS arm64，没有 Windows。

因此采用以下边界：

- Linux ISIS 10：直接基于官方 conda 包进行 API 差异审计和绑定构建。
- Windows ISIS 10：从源码移植，先完成可行性验证，再承诺稳定安装包。
- Windows ISIS 10 未通过完整前缀验证前，状态标记为 `experimental`，不能与已验证产品线等同发布。

官方依据：

- [USGS ISIS Release Schedule](https://astrogeology.usgs.gov/docs/how-to-guides/software-management/isis-release-schedule/)
- [USGS Astrogeology ISIS conda package](https://anaconda.org/usgs-astrogeology/isis)

## 4. 总体架构

详细的 381 个当前绑定头文件影响范围、48 个变化头文件分组和重新审计顺序见
`docs/isis9-isis10-binding-compatibility-plan.md`。

### 4.1 单一主线、共享源码

推荐继续使用一条 `main` 开发主线，不复制 `src/`，也不长期维护 `isis9`、`isis10` 两份绑定分支。

版本差异集中到小范围兼容层：

```text
src/
  compat/
    isis_version.h
    api_compat.h
    capabilities.cpp
  ...现有绑定文件...
cmake/
  DetectIsisVersion.cmake
```

设计规则：

- CMake 从 `ISIS_PREFIX` 的版本文件、头文件或 ISIS 可执行程序探测精确版本。
- 生成 `PYISIS_ISIS_VERSION_MAJOR`、`MINOR`、`PATCH` 编译定义。
- 只有真实 API 差异进入 `src/compat/`；普通绑定文件保持版本无关。
- 禁止在大量绑定文件中散布未经说明的 `#if ISIS_VERSION...`。
- 两个版本共有的 API 保持相同 Python 名称和行为。
- 仅某一版本存在的 API 必须登记到能力清单，并有对应版本测试。

### 4.2 运行时一致性检查

扩展模块应导出：

```python
isis_pybind.__version__       # PyISIS 自身版本
isis_pybind.__isis_version__  # 构建时 ISIS 精确版本
isis_pybind.__isis_major__    # 9 或 10
```

runtime 包同时携带机器可读元数据，例如：

```json
{
  "isis_version": "10.0.0",
  "isis_major": 10,
  "platform": "win-64",
  "build_id": "..."
}
```

导入时至少校验 ISIS 主版本一致。精确 patch 版本不同时默认给出清晰错误或受控警告，策略由兼容性测试决定，不能静默加载不匹配的动态库。

### 4.3 参考源码管理

`reference/upstream_isis/` 继续保持不受 Git 跟踪。建议改为双版本本地布局：

```text
reference/upstream_isis/
  9.0.0/
  10.0.0/
reference/upstream_isis-9.lock.json
reference/upstream_isis-10.lock.json
```

同步工具增加 `--isis-version 9.0.0|10.0.0`，按锁定 tag 和 commit 获取源码。参考源码只用于行为和实现阅读，实际编译签名仍以对应 conda/Windows prefix 中的头文件为准。

## 5. 开发环境设计

### 5.1 建议目录

```text
environments/
  isis9/
    linux-64.yml
    linux-64.lock.yml
    win-64.yml
    win-64.lock.yml
  isis10/
    linux-64.yml
    linux-64.lock.yml
    win-64.yml
    win-64.lock.yml
```

其中：

- `*.yml` 是便于维护的顶层依赖声明。
- `*.lock.yml` 或 conda explicit 文件记录实际解析结果，用于 CI 和可复现发布。
- 四套环境使用不同名称，例如 `pyisis-isis9-linux64`、`pyisis-isis10-win64`。
- 环境文件固定 Python、编译器、Qt、GDAL、OpenCV、protobuf 等 ABI 敏感依赖。
- 只允许通过 conda/mamba 管理 ISIS 及其编译依赖。

### 5.2 Linux 环境

ISIS 9 与 ISIS 10 分别从 USGS channel 安装精确版本，随后校验：

- `${CONDA_PREFIX}/include/isis`
- `${CONDA_PREFIX}/lib/libisis.so`
- `${CONDA_PREFIX}/lib/Camera.plugin`
- ISIS 精确版本和依赖清单
- conda C++ 编译器与目标 manylinux ABI 的兼容性

Linux 开发环境与最终 manylinux wheel 构建环境分开：开发环境用于日常编译测试，manylinux 容器用于正式发行兼容性验证。

截至 2026-07-24，本机已有两套可直接用于对比的开发环境：

- `asp360_new`：Python 3.12.2、ISIS 9.0.0 `h1f94ec8_0`
  (`usgs-astrogeology`)；
- `asp370`：Python 3.13.14、ISIS 10.0.0 `h1f94ec8_1`
  (`usgs-astrogeology`)；为保持该二进制所需的
  `libcsmapi.so.3` ABI，固定 `csm 3.0.3.3`。

切换产品线时必须同时把 `ISISROOT` 指向对应 conda prefix，并设置匹配的
`ISISDATA` 和 binding build 目录。只更换 Python 解释器会继承 shell 中
另一 ISIS 主版本的 plugin、ALE 和偏好路径，形成运行时混用。

USGS ISIS 10.0.0 `h1f94ec8_1` 依赖 CPython 3.13。因此第一轮 ISIS 10
Linux 编译验证直接使用 `asp370`，而 CPython 3.12 wheel 不能在未解决
runtime prefix 与 Python ABI 解耦前直接承诺。
可选路线是构建独立 ISIS 10 runtime prefix，或先把 ISIS 10 wheel 产品线
调整到 CPython 3.13，二者需通过实际构建结果再决定。

### 5.3 Windows 环境

Windows 环境分为两层：

1. conda 依赖环境：MSVC 配套依赖、Qt、OpenCV、protobuf 等。
2. ISIS SDK/runtime prefix：由相应 ISIS 源码 tag 构建并安装。

Windows 脚本需要从固定 9.0.0 名称改成参数化入口：

```powershell
./ports/windows/isis/fetch_isis.ps1 -Version 9.0.0
./ports/windows/isis/fetch_isis.ps1 -Version 10.0.0
```

补丁按版本隔离：

```text
ports/windows/isis/patches/
  9.0.0/
  10.0.0/
```

共有修改可以由生成脚本复用，但每个补丁必须在相应 tag 上独立验证，不能以文件复制代替重放和测试。

## 6. Python 与 conda 包命名

### 6.1 推荐方案：发行名区分 ISIS ABI

Python import 名不变，发行包名显式区分 ISIS 主版本：

| 内容 | ISIS 9 | ISIS 10 |
| --- | --- | --- |
| 主绑定包 | `usgs-pyisis-isis9` | `usgs-pyisis-isis10` |
| Windows runtime | `usgs-pyisis-runtime-isis9-win64` | `usgs-pyisis-runtime-isis10-win64` |
| Linux runtime | `usgs-pyisis-runtime-isis9-linux-x86_64` | `usgs-pyisis-runtime-isis10-linux-x86_64` |
| 最小数据包 | `usgs-pyisis-isisdata-isis9-minimal` | `usgs-pyisis-isisdata-isis10-minimal` |

两个主绑定包都安装 `pyisis` 和 `isis_pybind`，因此必须声明为互斥，文档也必须要求使用不同环境。

不建议采用以下方案：

- 只在 wheel 文件名末尾写 `isis9`/`isis10`：依赖解析器无法可靠表达 ABI。
- 仅用 Python extras，例如 `usgs-pyisis[isis10]`：extras 不能解决两个不同的编译扩展选择问题。
- 两个版本继续依赖同名 runtime 包：升级时容易被另一条 ABI 线覆盖。

### 6.2 现有 `usgs-pyisis` 的兼容处理

建议分两个发布周期迁移：

1. 当前 `usgs-pyisis` 继续代表 ISIS 9，并发布弃用/迁移提示。
2. 新增显式的 `usgs-pyisis-isis9` 与 `usgs-pyisis-isis10`。
3. 验证用户迁移后，停止发布无 ABI 后缀的新版本；不要让无后缀包自动切换到 ISIS 10。

### 6.3 conda 包

conda 侧建议使用两个明确包名或 build variant：

- `pyisis-isis9`
- `pyisis-isis10`

两者分别精确依赖 `isis >=9,<10` 和 `isis >=10,<11`，并增加互斥约束。正式 recipe 需要按 Linux/Windows 分别验证；Windows 若仍使用自建 ISIS prefix，则可先通过内部 channel 或 GitHub Release 提供环境包，不虚构官方 Windows ISIS 依赖。

## 7. CI 与发布矩阵

当前双版本核心绑定发布完成后的 Windows 行星摄影测量 APP 扩展，单独按
`docs/windows-planetary-photogrammetry-app-roadmap.md` 推进。该工作不阻塞
本规划的首个 ISIS 9/10 核心绑定 Release。

### 7.1 最小矩阵

| OS | ISIS | Python | PR 检查 | 正式发布 |
| --- | --- | --- | --- | --- |
| Linux x86_64 | 9.0.0 | 3.12 | 编译、聚焦测试、smoke | manylinux wheelhouse、干净安装、完整基础测试 |
| Linux x86_64 | 10.0.0 | 3.13（官方 conda build）；3.12 待验证 | 编译、API 差异测试、smoke | manylinux wheelhouse、干净安装、完整基础测试 |
| Windows x64 | 9.0.0 | 3.12 | prefix 缓存、编译、基础测试 | win_amd64 wheelhouse、干净安装、基础测试 |
| Windows x64 | 10.0.0 | 3.12 | 移植阶段先手动/定时；稳定后纳入 PR | 通过发布门槛后才生成稳定 wheelhouse |

ISIS 9 和现有 wheel 继续以 CPython 3.12 为稳定基线。ISIS 10 Linux
第一阶段先使用官方 conda build 要求的 CPython 3.13 完成源码兼容验证；
正式 wheel 的 Python ABI 在 runtime prefix 路线确认后再冻结。除这两个
必要版本外，暂不扩展 Python 3.10、3.11 等更多维度。

### 7.2 CI 分层

- PR 快速层：Linux 9/10 必跑，Windows 9 必跑；Windows 10 在移植期使用定时或手动工作流。
- nightly 层：四条线执行更广的单元测试和 runtime 依赖检查。
- release 层：构建四个独立 wheelhouse，执行 `twine check`、内容白名单、体积预算、SBOM/许可清单和干净安装。
- 发布产物名必须包含 PyISIS 版本、ISIS 精确版本、Python ABI 和平台。

示例：

```text
pyisis-1.3.0-isis9.0.0-cp312-linux-x86_64/
pyisis-1.3.0-isis9.0.0-cp312-win64/
pyisis-1.3.0-isis10.0.0-cp312-linux-x86_64/
pyisis-1.3.0-isis10.0.0-cp312-win64/
```

### 7.3 发布前门槛

每条产品线独立满足：

- 编译时 ISIS 版本和 runtime 元数据一致。
- 主包不能解析到另一 ISIS 主版本的 runtime。
- wheel 在无源码树、无开发 conda 环境的干净环境中可导入。
- `Camera.plugin`、`IsisPreferences` 和最小 ISISDATA 可用。
- Windows 使用 DLL 依赖闭包检查；Linux 使用 `auditwheel` 和 SO 依赖检查。
- 发行物不包含上游源码、测试大数据、构建缓存或规划文件。
- runtime 中所有再分发依赖都有许可清单；若 PyPI 体积或许可不允许，则改发 GitHub Release/专用 wheel index，不强行上传 PyPI。

## 8. ISIS 9 → ISIS 10 API 差异审计

在修改绑定前生成机器可读差异表：

```text
reference/compatibility/
  isis9-isis10-api-matrix.csv
  isis9-isis10-symbol-report.md
```

建议字段：

| 字段 | 含义 |
| --- | --- |
| `binding_group` | 对应绑定模块 |
| `cpp_symbol` | ISIS C++ 类或函数 |
| `isis9_status` | 头文件、签名和链接状态 |
| `isis10_status` | 头文件、签名和链接状态 |
| `python_api` | 当前 Python 导出 |
| `compat_action` | 无需处理、兼容 wrapper、条件编译或停止导出 |
| `tests` | 两个版本对应测试 |

审计顺序：

1. 从当前已绑定的头文件清单出发，而不是扫描整个 ISIS。
2. 比较 ISIS 9/10 实际 prefix 中的头文件。
3. 对直接成员函数指针检查链接符号是否存在。
4. 先保证现有公共 Python API 在 ISIS 10 下编译。
5. 再绑定 ISIS 10 新增 API，不与兼容迁移混在同一个 PR。

### 8.1 ISIS 10 新增绑定候选

ISIS 10 新增类和函数使用独立目录维护：

```text
reference/isis10_bind_candidates/
  README.md
  classes_inventory_summary.csv
  class_details/
  functions_inventory.csv
  excluded_new_headers.csv
```

该目录只记录 ISIS 10 相对 ISIS 9 新增的能力，不重复登记 ISIS 9 已绑定
类。第一批建议评估 `IProj`、`Chandrayaan2OhrcCamera` 和
`Chandrayaan2TmcCamera`；第二批再评估
`OsirisRexOcamsOpenCVDistortionMap`、`csv2table`、`ocams2isis` 和
`eisstitch`。`GdalIoHandler` 先设计 Python facade，不直接暴露裸
`GDALDataset*`/Qt 指针接口。

## 9. 分阶段实施路线

### 阶段 0：冻结基线和命名决策

交付：

- 锁定 ISIS 9.0.0、ISIS 10.0.0 的 tag、commit 和 conda build。
- 确认发行包命名与无后缀包迁移策略。
- 记录四条产品线的支持状态。

完成标准：相同输入能重建相同开发环境，且用户确认包命名。

### 阶段 1：Linux 双版本编译

交付：

- 两套 Linux conda 环境和锁定文件。
- ISIS 版本探测、编译定义和 Python 版本元数据。
- ISIS 9/10 API 差异表。
- Linux 9/10 的编译与 smoke CI。

完成标准：同一 commit 分别对 ISIS 9 和 ISIS 10 完成构建、导入和聚焦测试。

### 阶段 2：共享兼容层

交付：

- `src/compat/` 小范围适配。
- 公共 API 的双版本测试。
- 版本特有能力清单和查询接口。

完成标准：现有 ISIS 9 测试不回退，ISIS 10 的不兼容项均有明确处置，不存在无说明的静默缺失。

### 阶段 3：Windows ISIS 9 参数化重构

交付：

- 将固定 9.0.0 的 fetch/build/install 脚本改造成带版本参数的公共框架。
- ISIS 9 补丁移入独立版本目录。
- 保持 Windows ISIS 9 prefix 和 wheel 回归通过。

完成标准：重构前后的 ISIS 9 安装包行为一致。

### 阶段 4：Windows ISIS 10 移植可行性

按以下门槛推进：

1. ISIS 10 源码可配置。
2. 核心 `isis` 库和必要插件可编译。
3. 可安装出独立 prefix。
4. ISIS CLI smoke 通过。
5. PyISIS 可链接、导入并运行基础测试。

每个 ISIS 10 Windows 修复都形成独立补丁和说明。若任一关键第三方依赖无法合法、稳定地在 Windows 构建，则停止在 `experimental` 状态并记录阻塞，不伪造稳定支持。

### 阶段 5：四套 wheelhouse 与 conda 发行

交付：

- 四套主 binding/runtime/minimal-data 安装包。
- 发行物白名单、体积预算、依赖闭包和许可报告。
- 四套干净安装测试。
- GitHub Release 资产和校验文件；符合条件后再考虑 PyPI/TestPyPI。

完成标准：用户选择任一受支持 OS/ISIS 组合，都能通过明确命令创建隔离环境并安装正确版本。

### 阶段 6：维护与补丁升级

- 对 ISIS 9.x 和 10.x 分别维护可接受版本范围。
- patch 版本升级先跑 ABI/API 报告，再更新 lock 和产物。
- 新增绑定必须至少在 Linux ISIS 9/10 编译；平台相关绑定再进入 Windows 矩阵。
- 当 USGS 结束 ISIS 9 支持后，本项目另行制定弃用周期，不自动停止发布。

## 10. 建议的 PR 拆分

| PR | 内容 | 风险 |
| --- | --- | --- |
| PR 1 | 双版本锁文件、环境目录、版本探测和元数据测试 | 低 |
| PR 2 | Linux ISIS 9/10 编译矩阵与 API 差异报告 | 中 |
| PR 3 起 | 按绑定模块逐批加入 ISIS 10 兼容层 | 中 |
| PR 4 | Windows ISIS 9 脚本参数化，保持 9.0.0 回归 | 中 |
| 独立实验分支/PR | Windows ISIS 10 补丁移植 | 高 |
| 后续 PR | ABI 分版包名、四套 wheelhouse 和发布治理 | 高 |

Windows ISIS 10 移植适合使用独立 worktree 和功能分支，确认可行后再合入主线。

## 11. 验收标准

项目达到双版本正式支持需同时满足：

- 同一主线源码可对 ISIS 9 和 ISIS 10 编译。
- 四套开发环境均有锁定文件和重建说明。
- 四种 OS/ISIS 组合都有独立、不可混装的安装包。
- `isis_pybind` 可报告 PyISIS 版本和构建时 ISIS 版本。
- runtime 主版本错误时导入明确失败。
- 公共 API 双版本测试通过，版本特有 API 有能力清单。
- Linux 产物经过真实 manylinux 验证。
- Windows 产物经过干净 Windows runner 安装验证。
- ISIS 9 回归测试不因 ISIS 10 适配而下降。
- 发布资产包含 SHA-256、环境锁、依赖清单和许可信息。

## 12. 主要风险与应对

| 风险 | 应对 |
| --- | --- |
| ISIS 10 C++ API 大幅变化 | 先做已绑定 API 差异表，再按模块适配 |
| 两个 runtime 被安装到同一环境 | ABI 分版包名、互斥依赖和导入校验 |
| Windows ISIS 10 无官方包 | 独立源码移植门槛，未通过前保持 experimental |
| Windows 补丁队列失控 | 按 ISIS 版本隔离，尽量向上游反馈通用修复 |
| CI 矩阵耗时过长 | PR 快速层、nightly 层和 release 层分离 |
| runtime wheel 过大或许可受限 | 优先 GitHub Release/专用 index，保留 conda 安装路线 |
| ISIS patch 更新导致 ABI 漂移 | 锁定 conda build，并在升级时运行符号/API 报告 |
| 最小 ISISDATA 在两个版本间不兼容 | 初期分版，验证完全一致后再考虑合并 |

## 13. 已确认的实施原则

2026-07-23 已确认按以下原则推进：

- [x] 使用“单一主线 + 共享绑定源码 + 小范围兼容层”。
- [x] ISIS 9 与 ISIS 10 使用不同 conda 环境，禁止同环境共存。
- [x] 发行名显式区分 ISIS 主版本；最终名称在真正修改包元数据前再次核对
  PyPI 和 conda 可用性。
- [x] 先完成 Linux ISIS 10，再推进 Windows ISIS 10 源码移植。
- [x] Windows ISIS 10 在全部门槛通过前标记为 `experimental`。
- [x] ISIS 9 保持 CPython 3.12；ISIS 10 Linux 先按官方 conda build 使用
  CPython 3.13 验证，正式 wheel ABI 由 runtime prefix 实测决定。
- [x] 正式 runtime 包优先发布到 GitHub Release，许可和体积审核通过后再
  决定 PyPI。

## 14. 当前进度与下一项实施工作

2026-07-23 已在隔离分支和 worktree 完成：

1. 锁定 ISIS 9.0.0 与 ISIS 10.0.0 的源码 commit，并生成当前绑定头文件
   差异报告。
2. CMake 从所选 Python 环境解析 pybind11，禁止静默混入另一个 conda
   环境。
3. 按目标 ISIS prefix 自动选择 Qt5/Qt6；ISIS 10 补充
   `Qt6::Core5Compat`。
4. 适配 `Endian.h`/`IEndian.h`、Cube label attachment、
   `storesDnData()`、JP2Error/Kakadu 和 shape-model normal API 差异。
5. 同一份源码在 `asp360_new`（ISIS 9/Python 3.12/Qt5）和 `asp370`
   （ISIS 10/Python 3.13/Qt6）均完成 `_isis_core` 编译、链接、导入及
   Cube I/O 聚焦测试。
6. 建立独立的 ISIS 10 新增类/函数候选目录，不把工作限制为迁移 ISIS 9
   已绑定 API。

下一环节建议拆成两个独立 PR，避免把兼容基线和新增能力耦合：

1. 先提交本轮双版本锁文件、审计工具、Linux 兼容层、候选目录和测试。
2. 再建立 Linux 双版本 GitHub Actions 矩阵，并让日志明确输出 Python、
   ISIS、Qt 和扩展产物路径。
3. CI 稳定后，按候选目录先绑定 `IProj`，再绑定两项 Chandrayaan-2
   camera；每一批分别在 ISIS 9/10 下验证公共导入面。
4. Linux ISIS 10 稳定后，再进入 Windows ISIS 9 脚本参数化和 Windows
   ISIS 10 实验性源码移植。
