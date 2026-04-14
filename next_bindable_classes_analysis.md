# ISIS Pybind 下一步可绑定类分析

**生成日期**: 2026-04-14
**分析人员**: Geng Xun
**目的**: 基于当前绑定规则和完成状态，识别下一步应优先绑定的 ISIS 类

---

## 执行摘要

### 当前状态概览

根据 `class_bind_methods_details/methods_inventory_summary.csv` 分析：

- **总类数**: 396 个 ISIS 类
- **已转换类**: 382 个 (96.5%)
- **未转换类**: 14 个 (3.5%)
- **完成度 100% 的类**: 约 340+ 个
- **部分完成类** (已转换但 <100% 完成): 约 40 个

### 优先级建议

基于当前规则和项目约束，推荐以下三类绑定目标：

1. **立即可做** - 低复杂度、高价值类（投入产出比最佳）
2. **短期目标** - 部分完成类的收尾工作
3. **暂缓类** - 复杂度高或依赖未就绪的类

---

## 一、立即可做的类（推荐优先级）

这些类满足以下条件：
- 未转换或部分完成
- 公开方法数 < 20（工作量小）
- 无复杂 Qt 依赖或抽象基类问题
- 对 Python 用户价值明确

### 1.1 工具类和实用类

#### HiCalConf (Mars Reconnaissance Orbiter)
- **状态**: 未转换
- **开放项**: 19 个方法
- **位置**: `reference/upstream_isis/src/mro/objs/HiCal/HiCalConf.h`
- **价值**: HiRISE 相机校准配置，与已绑定的 HiLab 配套使用
- **复杂度**: 中等 - 主要是配置 getter/setter
- **建议**: 检查是否有 Qt 依赖，如没有则可立即绑定

#### ZeroBufferFit (Mars Reconnaissance Orbiter)
- **状态**: 未转换
- **开放项**: 20 个方法
- **位置**: `reference/upstream_isis/src/mro/objs/HiCal/ZeroBufferFit.h`
- **价值**: HiRISE 零缓冲区拟合算法
- **复杂度**: 中等
- **注意**: 可能与 HiCalConf 相关，建议一起处理

### 1.2 几何和数学辅助类

#### GSLUtility (Utility)
- **状态**: 已转换，完成度 19.05%
- **已绑定**: 4/21 方法 (singleton getInstance/success/status)
- **位置**: `src/base/bind_base_utility.cpp`
- **剩余工作**: 补齐 GSL 错误处理和数值计算辅助方法
- **价值**: 为数值计算提供更完整的 GSL 支持
- **复杂度**: 低 - 主要是静态工具方法

---

## 二、短期目标 - 部分完成类收尾

这些类已经有基础绑定，只需补齐少量方法即可达到 100% 覆盖。

### 2.1 高优先级（开放项 ≤ 3）

| 类名 | 模块 | 完成度 | 开放项 | 建议 |
|------|------|--------|--------|------|
| **Enlarge** | Geometry | 57.14% | 3 | 继承自 Transform，补齐几何放大方法 |
| **ProcessMosaic** | High Level Cube I/O | 57.14% | 3 | SetInputCube/SetOutputCube 生命周期管理问题待解决 |
| **JP2Encoder** | High Level Cube I/O | 66.67% | 2 | JPEG2000 编码器，补齐 encode 相关方法 |
| **BundleImage** | Control Networks | 71.43% | 2 | Bundle adjustment 图像，补齐元数据访问器 |
| **EndianSwapper** | Utility | 72.73% | 3 | 字节序转换，补齐剩余数据类型 |

### 2.2 中优先级（开放项 4-6）

| 类名 | 模块 | 完成度 | 开放项 | 建议 |
|------|------|--------|--------|------|
| **StreamExporter** | High Level Cube I/O | 20.00% | 4 | 抽象基类，补齐流式导出接口 |
| **BundleLidarControlPoint** | Control Networks | 66.67% | 4 | 激光雷达控制点，补齐残差和统计方法 |
| **WorldMapper** | Map Projection | 42.86% | 4 | 抽象基类，补齐投影映射接口 |
| **ProcessMapMosaic** | High Level Cube I/O | 64.29% | 5 | 地图镶嵌处理，补齐配置方法 |
| **ImageOverlap** | Control Networks | 53.85% | 6 | 图像重叠，补齐多边形和统计方法 |
| **ImageExporter** | High Level Cube I/O | 53.85% | 6 | 抽象基类，补齐导出选项 |

### 2.3 Mission-Specific 相机类（开放项 1-6，完成度 14-20%）

这些相机类已有基础绑定（构造/快门时间/SPICE ID），但缺少特定方法：

| 类名 | 任务 | 完成度 | 开放项 | 备注 |
|------|------|--------|--------|------|
| **CrismCamera** | Mars Reconnaissance Orbiter | 14.29% | 6 | CRISM 高光谱相机 |
| **MarciCamera** | Mars Reconnaissance Orbiter | 14.29% | 6 | MARCI 彩色成像相机 |
| **MdisCamera** | Messenger | 14.29% | 6 | MESSENGER MDIS 相机 |
| **CTXCamera** | Mars Reconnaissance Orbiter | 20.00% | 4 | Context Camera |
| **HiriseCamera** | Mars Reconnaissance Orbiter | 20.00% | 4 | HiRISE 高分辨率相机 |
| **MocNarrowAngleCamera** | Mars Global Surveyor | 20.00% | 4 | MOC 窄角相机 |

**建议**: 这些相机类共享类似模式，可批量处理。主要补齐：
- 波段相关方法（如适用）
- 畸变和探测器映射配置
- 特定任务的 SPICE 查询方法

---

## 三、暂缓类（不推荐立即绑定）

### 3.1 抽象基类（无直接 Python 实例化需求）

这些类是纯虚基类，已有部分符号暴露供继承使用：

- **InterestOperator** - 兴趣算子基类（18 个方法未绑定）
- **Selection** - 选择基类（16 个方法未绑定）
- **FunctionTools** - 函数工具基类（21 个方法未绑定）
- **Module** (MRO HiCal) - 模块基类（24 个方法未绑定）
- **Sensor** (SensorUtilities) - 传感器基类（38 个方法未绑定）
- **Shape** (SensorUtilities) - 形状基类（32 个方法未绑定）

**原因**: 这些类主要供 C++ 继承使用，Python 用户通常使用具体子类。

### 3.2 Qt 重度类

- **StatCumProbDistDynCalc** - Qt 信号槽较多（14 个方法）
- **ControlNetVitals** - Qt 类型/信号槽较多（32 个方法）

**原因**: 根据项目规则，默认不绑定 Qt signals/slots 和事件通知接口，除非有明确 Python 集成需求。

### 3.3 导出类（高复杂度流程接口）

- **ProcessExport** - 44 个方法，抽象基类+流程回调
- **ProcessExportPds** - 39 个方法，流程/回调接口较多

**原因**: 这些类依赖复杂的回调机制和生命周期管理，绑定投入产出比低。

### 3.4 HiCal 算法内部类（抽象基类+复杂依赖）

- **HiCalData** - 21 个方法，抽象基类
- **NonLinearLSQ** - 21 个方法，抽象基类
- **HiHistory** - 抽象基类
- **HiLineTimeEqn** - 抽象基类
- **LowPassFilter** - 抽象基类
- **SplineFill** - 抽象基类
- **ZeroBufferSmooth** - 抽象基类
- **ZeroDark** - 抽象基类
- **ZeroDarkRate** - 抽象基类
- **ZeroReverse** - 抽象基类

**原因**: 这些是 HiRISE 校准内部算法框架，Python 用户通常通过高层 API 使用，不需要直接访问。

---

## 四、基于当前规则的绑定策略

### 4.1 核心规则回顾

根据 `.github/copilot-instructions.md` 和 pybind 工作流：

1. **Qt 边界规则**:
   - 默认不绑定 Qt signals/slots
   - 不暴露 `emit*` 方法和 `QVariant` 载荷的通知接口
   - 优先暴露稳定数据方法、mutators、查询和枚举

2. **上游源码优先级**:
   - 编译时以 conda ISIS 环境为准
   - `reference/upstream_isis/` 用于实现阅读和生命周期分析
   - 如果镜像和 conda API 不一致，以 conda 为准

3. **测试要求**:
   - 使用 `asp360_new` 环境的 Python 解释器
   - 修改后运行最小相关测试
   - 优先使用 focused unit tests 而非全面验证

4. **避免过度工程**:
   - 只做直接请求或明确必要的更改
   - 不添加额外特性、重构或"改进"
   - 不为假设的未来需求设计

### 4.2 推荐工作流程

对于上述"立即可做"和"短期目标"类：

1. **准备阶段**:
   - 检查 `class_bind_methods_details/<class>_methods.csv` 确认 N 状态方法
   - 阅读 conda ISIS 头文件：`${ISIS_PREFIX}/include/isis/<Class>.h`
   - 参考镜像实现：`reference/upstream_isis/src/.../` 理解生命周期和默认值
   - 查看上游测试用例理解常见用法

2. **实现阶段**:
   - 在对应 `src/` 文件中扩展现有绑定（如已存在）
   - 遵循现有模式：构造函数、访问器、mutators、枚举、异常
   - 处理 Qt 字符串边界（`QString::fromStdString(...)` 转换）
   - 验证成员函数限定符（const 正确性）
   - 检查符号链接性（避免仅声明未实现的方法）

3. **测试阶段**:
   - 添加或扩展 `tests/unitTest/<category>_unit_test.py`
   - 运行 focused test: `python -m unittest tests.unitTest.<test_file>`
   - 更新 `tests/smoke_import.py` 添加符号导入验证
   - 验证 Python 签名与文档一致

4. **同步阶段**:
   - 更新 `class_bind_methods_details/<class>_methods.csv` (Y/N/Partial 状态)
   - 更新 `class_bind_methods_details/methods_inventory_summary.csv`
   - 更新 `todo_pybind11.csv` 备注
   - 更新 `python/isis_pybind/__init__.py` 导出（如需要）

---

## 五、具体行动建议

### 推荐批次 1: 工具和几何类收尾（预计 1-2 天）

**目标**: 完成小型实用类的绑定

1. **Enlarge** (3 个方法) - 几何放大
2. **EndianSwapper** (3 个方法) - 字节序转换
3. **JP2Encoder** (2 个方法) - JPEG2000 编码
4. **BundleImage** (2 个方法) - Bundle 图像元数据

**总计**: 10 个方法，预计难度低

### 推荐批次 2: 相机类补齐（预计 2-3 天）

**目标**: 将 Mission 相机类完成度提升到 100%

选择 3-4 个相机类（如 CTXCamera, HiriseCamera, MocNarrowAngleCamera, CrismCamera），批量补齐类似方法：

- 波段设置和查询
- 畸变映射配置
- 探测器映射参数
- 特定任务的 SPICE 查询

**总计**: 约 15-20 个方法，可重用模式

### 推荐批次 3: High Level Cube I/O 收尾（预计 2-3 天）

**目标**: 完成导出和处理类

1. **StreamExporter** (4 个方法) - 流式导出基类
2. **ImageExporter** (6 个方法) - 图像导出基类
3. **ImageImporter** 剩余方法（如有）
4. **ProcessMapMosaic** (5 个方法) - 地图镶嵌
5. **ProcessMosaic** (3 个方法，需解决 Cube 生命周期问题)

**总计**: 约 18 个方法，可能需要特殊处理生命周期

### 推荐批次 4: Control Networks 和 Bundle 收尾（预计 3-4 天）

**目标**: 完成控制网络和 Bundle adjustment 相关类

1. **ImageOverlap** (6 个方法) - 图像重叠
2. **BundleLidarControlPoint** (4 个方法) - 激光雷达控制点
3. **ControlNetValidMeasure** 剩余 9 个方法 - 测量验证
4. **ControlPoint** 剩余 1% - 几乎完成
5. **ControlMeasure** 剩余 1.39% - 几乎完成

**总计**: 约 20-25 个方法，可能涉及复杂验证逻辑

### 探索性任务: HiCal 配置类（预计 1-2 天）

**目标**: 评估 HiCalConf 和相关类的可绑定性

1. 检查 conda ISIS 环境中 HiCalConf 的可用性
2. 确认依赖链（HiLab → HiCalConf → HiCalData?）
3. 如果可行，绑定 HiCalConf 核心配置方法
4. 评估是否需要绑定更深层的 HiCal 算法类

**注意**: 这可能触及更复杂的 MRO HiCal 框架，需谨慎评估投入产出比

---

## 六、不推荐的绑定方向

基于当前规则和已知限制，以下方向**不推荐**作为近期目标：

### 6.1 Qt 集成
- 不绑定 StatCumProbDistDynCalc 的 Qt 信号统计
- 不绑定 ControlNetVitals 的 Qt 事件接口
- 不为 ControlMeasure/ControlPoint 添加 Qt 信号绑定

**原因**: 项目明确规定默认不暴露 Qt 观察者/事件表面

### 6.2 抽象基类深度绑定
- 不为纯虚基类（InterestOperator, Selection, FunctionTools 等）添加完整方法绑定
- 这些类的现有符号暴露已足够支持继承体系

**原因**: Python 用户不直接实例化这些类，绑定投入产出比低

### 6.3 Process 流程回调重构
- 不重新设计 ProcessExport/ProcessExportPds 的回调机制
- 不尝试深度绑定 ProcessByLine/ProcessByBrick 的回调接口

**原因**: 复杂的生命周期和回调管理，当前部分暴露已够用

### 6.4 HiCal 内部算法框架
- 不绑定所有 HiCal 抽象基类（HiCalData, NonLinearLSQ, Module 等）
- 不深入 Zero*/LowPassFilter/SplineFill 等内部算法

**原因**: 这些是内部实现细节，高层 API（如通过应用程序）已覆盖用例

---

## 七、长期考虑

### 7.1 未来可能的扩展点

当前规则下暂缓，但未来如有需求可考虑：

1. **Python-friendly 回调机制**:
   - 为 Process 族设计 Python callable 适配器
   - 允许 Python 函数作为处理回调

2. **Qt 事件可选集成**:
   - 如用户明确需要 ControlNet 变更通知
   - 设计轻量级 Python 回调 API 而非直接暴露 Qt 信号

3. **HiCal 高层配置**:
   - 如 HiCalConf 绑定成功且有用户需求
   - 可考虑暴露更高层的 HiCal 工作流配置

4. **完整 SensorUtilities 绑定**:
   - 当前 Sensor/Shape 基类暂缓
   - 如需完整几何建模支持，可重新评估

### 7.2 技术债务和已知问题

需要在未来解决的已知问题：

1. **Cube 生命周期管理**:
   - ProcessMosaic 的 SetInputCube/SetOutputCube 未绑定
   - 需要安全的 Cube 所有权转移机制

2. **部分类的符号缺失**:
   - 某些方法在头文件中声明但链接库未导出
   - 需要为这些情况设计 wrapper 策略

3. **测试数据依赖**:
   - 某些相机和算法类缺少稳定的测试 fixture
   - 需要补充最小化的 mission 数据集

4. **文档同步**:
   - Python docstrings 需要与上游 ISIS 文档同步
   - 考虑自动化文档生成工具

---

## 八、总结和建议

### 当前最佳投入产出比

基于分析，**推荐立即开始的工作**（按优先级排序）：

1. **批次 1: 小型工具类收尾** - 快速提升完成度
   - Enlarge, EndianSwapper, JP2Encoder, BundleImage
   - 预计 1-2 天，低风险高回报

2. **批次 2: 相机类批量补齐** - 提升 Mission 支持完整性
   - 3-4 个相机类，重用模式
   - 预计 2-3 天，中等回报

3. **批次 3: High Level Cube I/O** - 完善导入导出功能
   - StreamExporter, ImageExporter, ProcessMapMosaic
   - 预计 2-3 天，高用户价值

4. **探索 HiCalConf** - 如时间允许
   - 评估可行性和用户需求
   - 预计 1-2 天，潜在高价值但需验证

### 明确避免的工作

- 不绑定抽象基类的全部虚方法
- 不重构 Process 回调机制
- 不深入 HiCal 算法内部
- 不添加 Qt 信号绑定

### 成功指标

完成上述批次后，项目将达到：

- **完成度 100% 的类**: 350+ 个（当前约 340+）
- **99%+ 完成的类**: 360+ 个
- **Mission 相机覆盖**: 所有主要任务相机达到 100%
- **High Level I/O**: 导入导出链路完整

这将使 pyisis 成为一个功能完备的 Python ISIS 绑定库，覆盖绝大多数实际应用场景。

---

**下一步行动**: 从批次 1 开始，完成 Enlarge、EndianSwapper、JP2Encoder、BundleImage 四个类的绑定。
