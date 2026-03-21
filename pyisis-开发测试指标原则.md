# pyISIS 开发测试指标原则

日期：2026-03-17  
作者：Geng Xun（默认元数据）

适用范围：`ISIS3-9.0.0-ext / isis_pybind_standalone`

## 目标

本文件定义 `pyISIS`（基于 `pybind11` 的 ISIS Python 绑定）在开发、测试、发布与维护中的工程原则。

目标不是仅做到“本地能跑”，而是做到：

1. **可验证**：能区分功能正确、环境缺失、ABI 不兼容、打包错误等问题。
2. **可发布**：能对外提供稳定、可重复安装的分发方式。
3. **可维护**：在增加绑定、升级 ISIS、升级 Python 后，能快速定位回归。
4. **可演进**：支持从当前外挂式绑定项目平滑过渡到更成熟的发布模式。

## 核心判断

### smoke test + unit test 不能单独证明“库没问题”

对 `pybind11` 绑定层而言，风险不仅来自业务逻辑，还来自：

- Python ABI
- C++ ABI
- 动态库加载
- 安装路径
- 运行时数据依赖
- 异常翻译
- 生命周期与 ownership
- 插件与工厂机制

因此，测试体系必须分层，不能把所有验证都寄托在 smoke test 或单元测试上。

## 测试分层原则

### 1. Smoke Test

**目标**

- 验证模块可导入
- 验证关键符号存在
- 验证少量最小可用调用链已打通

**要求**

- 快速
- 稳定
- 不承担详细行为验证职责
- 不堆积复杂业务断言

**当前对应文件**

- `isis_pybind_standalone/tests/smoke_import.py`

### 2. Focused Unit Test

**目标**

- 验证单个绑定类或函数的明确行为
- 验证构造函数、访问器、修改器、异常翻译、枚举、字符串表示等
- 验证 Python 暴露接口与当前实际绑定签名一致

**建议优先覆盖**

- value-like types：`Angle`、`Distance`、`Latitude`、`Longitude`、`Displacement`
- resource-owning classes：`Cube`、`Buffer`、`Portal`、`Table`
- IO bindings：low-level cube IO、high-level IO、`ProcessImport`
- factories / plugins：`CameraFactory`、`ProjectionFactory`
- exception translation：C++ 异常到 Python 异常
- Python-facing helpers：`__repr__`、`to_string()`、辅助静态函数

**要求**

- 小而专注
- 单文件职责明确
- 失败后能快速定位原因

**当前参考位置**

- `isis_pybind_standalone/tests/unitTest/`
- `isis_pybind_standalone/tests/unitTest/_unit_test_support.py`

### 3. 安装后验证

**目标**

防止“构建目录可导入，但安装后不可用”。

**必须区分**

- build-tree import：从 `build/python` 下导入
- install-tree import：执行安装后，从 `site-packages` 正常导入

**必测内容**

- `import isis_pybind` 是否成功
- `_isis_core` 是否可加载
- 安装后路径与运行时依赖是否完整

### 4. Integration Test

**目标**

验证多个 ISIS 组件在 Python 层串联使用时是否可工作。

**典型场景**

- `Cube + CameraFactory`
- `ProjectionFactory + Pvl`
- `ProcessImport + 输入数据`
- 依赖 kernels、plugin、camera/projection 动态库的能力

**要求**

- 与 unit test 分层，不混淆职责
- 对环境依赖敏感的测试允许 skip
- 明确区分“环境未准备好”与“绑定实现回归”

### 5. ABI / Packaging Validation

**目标**

保证打包产物在目标环境中可实际使用。

**必查项**

- Python ABI 匹配
- `libisis.so` 可解析
- Qt / Bullet / projection / camera 相关动态库可解析
- 插件文件可访问
- 安装后的 import 与最小功能调用通过

**原则**

- 能编译，不等于能发布
- 能在开发机导入，不等于用户环境可用

## 解释器与环境原则

### 解释器选择

当前 `isis_pybind_standalone` 测试与验证应优先使用：

`/home/gengxun/miniconda3/envs/asp360_new/bin/python`

### 原因

- 当前构建出的扩展模块面向 CPython 3.12
- 若使用 `base` 环境或其他 Python 版本，可能出现 ABI 不匹配
- 若 `import isis_pybind` 成功但 `_isis_core` 缺失，应先怀疑 Python 版本不匹配，而不是立即判断为绑定回归

### 原则

- 测试必须优先在 ABI 匹配的 Python 下执行
- 跨 Python 版本失败时，先排除解释器/ABI 问题

## 环境依赖处理原则

某些 ISIS API 依赖外部运行时数据，例如：

- leap second kernels
- SPICE / NAIF 数据
- `Camera.plugin`
- mission-specific camera libraries
- projection libraries
- 外部 cube / label / 原始输入数据

对这类测试：

- 缺依赖时优先 skip 或给出明确环境错误说明
- 不应将环境缺失误判为绑定逻辑失败
- 回归判断必须建立在环境已满足的前提下

## 覆盖矩阵建议

建议按以下维度维护测试覆盖矩阵：

### 构造行为

- 默认构造
- 合法构造
- 非法构造
- 枚举构造
- 工厂构造

### 核心行为

- getter / setter
- 数值转换
- 单位转换
- 基础计算
- 文件读写

### Python 侧接口

- `repr` / `str`
- list / array 输入输出
- 容器索引行为
- enum 暴露
- 类型检查

### 异常行为

- 参数错误
- 非法状态
- 文件不存在
- 标签不合法
- 运行时库缺失

### 集成行为

- 对象串联
- 工厂与插件加载
- 数据文件导入导出
- 环境数据依赖
- 安装后最小工作流

## 发布原则

### 正式发布优先选择可重复安装的分发方式

推荐路线：

1. **短中期**：将 `isis_pybind_standalone` 做成独立 conda 包，例如 `isis-pybind`
2. **长期**：待稳定后评估是否并入主 ISIS 包统一发布

### 为什么优先 conda 包

- 可以表达对 `isis` 主包的依赖关系
- 可以 pin Python 版本与运行时依赖
- 用户安装路径清晰
- 更适合科研用户的实际环境

### 为什么不推荐“手工拷贝即可用”作为正式方案

因为存在以下高风险：

- Python ABI 不匹配
- C++ ABI 不匹配
- `libstdc++` / 编译器版本差异
- 动态库搜索路径问题
- Qt / OpenCV / Bullet 等依赖冲突
- 本地可用但用户环境崩溃

**结论**

- “手工拷贝使用”可作为内部临时方案
- 不适合作为面向正式用户的发布方案

## Conda 发布原则

### 推荐策略

在正式考虑 `conda-forge` 前，优先：

- 编写独立 recipe
- 在自有 channel 上验证安装体验
- 稳定至少 1~2 个版本
- 明确版本 pinning 与依赖链

### 独立包建议

- 包名建议：`isis-pybind`
- 运行时依赖建议：严格依赖对应版本范围的 `isis` 主包
- 首发平台建议：`linux-64` 优先

### 发布矩阵建议

- Python：只支持已验证 ABI 的版本
- 平台：优先 Linux，后续视资源增加 macOS
- ISIS 版本：建议与主包版本严格绑定或小范围兼容绑定

## Conda-forge 原则

`conda-forge` 可以作为目标，但不建议作为第一步。

建议在以下条件满足后再评估：

- recipe 已稳定
- 依赖链清晰
- 许可证与第三方依赖可公开分发
- 构建脚本标准化
- CI 能稳定产出

建议路径：

1. 先在自有 channel 跑通
2. 再评估 `conda-forge`
3. 避免一开始就把维护复杂度拉满

## 用户安装体验原则

### 理想体验

1. 安装 ISIS 主环境
2. 通过 conda 安装 `isis-pybind`
3. 直接在目标 Python 中 `import isis_pybind`
4. 运行 smoke test 或最小示例确认成功

### 不推荐体验

1. 用户自己下载某个 `.so`
2. 手工拷入 `site-packages`
3. 手工修补环境变量
4. 遇到导入错误后无法判断是版本、路径还是 ABI 问题

## 实施优先级

### 第一优先级

1. 明确 smoke test 与 unit test 职责边界
2. 补 install-tree import 验证
3. 补 ABI 与依赖加载验证
4. 对环境依赖型测试加入 skip 策略

### 第二优先级

1. 扩充 focused unit tests
2. 建立最小 integration tests
3. 编写独立 conda recipe

### 第三优先级

1. 建立发布矩阵
2. 接入自动化构建与测试
3. 评估 `conda-forge`
4. 评估是否并入主 ISIS 包

## 核心结论

1. `smoke test + 单元测试` 不能单独证明 pyISIS 绑定已达到可靠发布标准。
2. 对 `pybind11` 绑定层，还必须补：
   - 安装后验证
   - ABI 验证
   - 运行时依赖验证
   - 环境感知集成测试
   - 发布环境安装验证
3. 正式分发的优先方案是：**独立 conda 包 + 明确依赖 ISIS 主包**。
4. GitHub 下载可作为预览或内部试用方式。
5. 用户“装好 ISIS 后直接拷贝使用”不适合作为正式发布方案。

## 参考文件

- `isis_pybind_standalone/tests/smoke_import.py`
- `isis_pybind_standalone/tests/unitTest/`
- `isis_pybind_standalone/tests/unitTest/_unit_test_support.py`
- `isis_pybind_standalone/CMakeLists.txt`
- `isis_pybind_standalone/README.md`
- `recipe/meta.yaml`
- 仓库根目录：`pyisis-开发测试指标原则.txt`
