# ISIS 9 / ISIS 10 绑定兼容与重新审计清单

## 1. 结论

ISIS 9 与 ISIS 10 继续共用同一套 pybind11 主体源码。新比较结果用于确定
“哪些现有绑定必须重新审计”，不等于为两个版本复制两套绑定，也不等于
把所有变化头文件全部重写。

当前绑定引用 384 个唯一 ISIS 头文件：

- 328 个在 ISIS 9/10 中相同，维持共享实现；
- 48 个声明有变化，已逐项核对绑定实际使用的签名；
- 1 个是 `Endian.h` 到 `IEndian.h` 的兼容性重命名；
- 7 个只在 ISIS 10 中被当前源码引用；
- 没有发现 ISIS 10 中缺失且无替代的当前绑定头文件。

按“非文本一致或含Qt observer元数据”的conda风险口径，共57个唯一头文件；
`reference/compatibility/isis9-isis10-binding-review.csv`已关闭57个，剩余0个。

完整机械清单见
`reference/compatibility/isis9-isis10-symbol-report.md`，本文件定义人工执行顺序
和代码架构约束。

## 2. 兼容实现原则

1. 保持一个 `_isis_core`、一份公共 CMake 源文件列表和一套 Python import。
2. 共有能力继续放在原有绑定文件中，不建立 `src/isis9/` 与 `src/isis10/`
   两份平行实现。
3. Python 可见的名称、参数语义和返回类型尽量保持一致。
4. `QVector/QList`、`QPair/std::pair` 等变化在 C++/pybind 边界归一化为
   `list`、`tuple` 或 `std::vector/std::pair`，不泄漏 Qt5/Qt6 差异。
5. 单点差异优先使用绑定文件内的小型 lambda 或局部适配；同类转换在至少
   三处重复后，再抽取到现有 helper/compat 层。
6. 只有无法使用同一 C++ 表达式编译的 API 才使用能力宏或版本门，并把门
   限制在最小代码块内。
7. ISIS 10 独有能力集中注册在 `src/bind_isis10.cpp`；公共类即使内部签名
   有变化，也不迁入该文件。
8. QObject 派生类默认只绑定稳定数据 API，不绑定 signals/slots。
9. conda prefix 中的正式头文件和链接库是编译真值；上游源码和 Changelog
   只用于解释行为与发现线索。

## 3. 现有绑定兼容队列

“重新绑定”在本计划中表示重新核对当前暴露面并按需适配。只有检查发现
现有表达式无法双版本编译，或 Python 行为不一致时，才修改绑定代码。

### P0：核心数据与控制网络

| 组 | 需审计的主要类/头文件 | 验收重点 |
|---|---|---|
| Cube/I/O | `Cube`、`CubeAttribute`、`Blob`、`Table`、`ProcessByBrick`、`PixelType` | 构造函数、所有权、读写参数和容器返回值 |
| PVL | `Pvl`、`PvlObject`、`PvlContainer`、`PvlFormat`、`PvlKeyword`、各 TranslationManager | Qt 容器、迭代与字符串转换是否保持相同 Python 行为 |
| Control | `ControlNet`、`ControlPoint`、`ControlMeasure`、`MeasureValidationResults` | QObject observer API 排除、所有权和集合返回值 |
| Bundle | `BundleResults`、`BundleSettings`、`BundleSolutionInfo`、`ImageList` | `QList/QVector` 与 `QPair/std::pair` 变化、生命周期 |

### P1：几何、形状与导航

| 组 | 需审计的主要类/头文件 | 验收重点 |
|---|---|---|
| Shape | `ShapeModel`、`BulletShapeModel`、`BulletTargetShape`、`DemShape`、`EllipsoidShape`、`EmbreeShapeModel`、`NaifDskShape` | 虚函数签名、返回对象所有权和 ISIS 10 条件能力 |
| Camera/Map | `CameraFocalPlaneMap`、`CameraFactory`、`UniversalGroundMap`、`Projection`、`TProjection` | 工厂返回策略、投影接口和版本特有相机注册 |
| Spice | `Spice`、`SpiceRotation` | 容器参数、时钟/姿态接口和底层库可链接性 |
| OSIRIS-REx | `OsirisRexDistortionMap`、`OsirisRexOcamsCamera` | 与 ISIS 10 新 OpenCV distortion 类的职责边界 |

### P2：工具与低风险复核

| 组 | 需审计的主要类/头文件 | 验收重点 |
|---|---|---|
| Math/Seeder | `Calculator`、`CubeCalculator`、`InfixToPostfix`、`GridPolygonSeeder` | 参数签名和容器返回 |
| Support | `FileName`、`IException`、`Environment`、`SpecialPixel`、`GroupedStatistics` | 是否只有声明布局或非绑定成员变化 |

P2 项仍需记录审计结论，但若当前绑定使用的签名在两个 prefix 中一致，应标记
为 `shared-no-change`，不制造无意义代码修改。

## 4. 每项审计结果分类

每个头文件最终只能进入以下一种主分类：

| 分类 | 含义 | 代码处理 |
|---|---|---|
| `shared-no-change` | 绑定使用的签名未变化 | 不改主体代码，补双版本证明 |
| `shared-wrapper` | C++ 签名变化但可维持相同 Python API | 在公共绑定中增加小型转换/适配 |
| `version-guarded` | 两版本无法用同一表达式编译 | 使用最小能力宏，分别测试 |
| `isis10-only` | ISIS 10 新公开能力 | 在 `bind_isis10.cpp` 注册并做版本门测试 |
| `excluded` | internal、GUI/observer、第三方、占位或不适合直接暴露 | 记录可审计理由，不绑定 |

审计台账至少记录：头文件、当前绑定文件、实际使用声明、ISIS 9 声明、
ISIS 10 声明、导出库、分类、代码改动、ISIS 9 测试和 ISIS 10 测试。

## 5. ISIS 10 新增绑定队列

### 已完成并通过正式 USGS 环境复核

- `IProj`
- `Chandrayaan2OhrcCamera`
- `Chandrayaan2TmcCamera`
- `OsirisRexOcamsOpenCVDistortionMap`
- `GdalIoHandler`
- `ImageIoHandler`

上述6个类共完成30个构造/方法入口。新增应用函数的审计边界已关闭：

- `csv2table` 已提供 ISIS 10 专属的跨平台 Python facade。Linux 后端在
  进程内调用 `libisis`，Windows 后端无 shell 调用原生
  `csv2table.exe`；不公开 `UserInterface` 或通用 APP runner。
- `ocams2isis` 与 `eisstitch` 采用原生 ISIS APP 执行边界，不再作为独立
  Python 绑定候选。

Windows 清单和行为烟测已由 GitHub Actions run `30739433903` 验证：
150 个 APP 完成编译安装，`csv2table -> tabledump` 行为烟测通过。

### 明确排除

- `DskSegmentBuffer`：ISIS internal。
- `IEndian`：兼容重命名和 deprecated helper，不作为新公共类。
- `RestfulSpice`：占位接口。
- `restincurl`：第三方实现。

## 6. 执行顺序与完成门槛

1. [x] 为conda风险集合生成并填写逐项兼容台账，57/57关闭。
2. [x] 在`asp360_new`（ISIS 9）与`asp370`（ISIS 10）完成编译、import、
   分组测试和发布基本测试。
3. [x] 完成6个ISIS 10专属类及版本门测试。
4. [ ] 运行Linux/Windows × ISIS 9/10四条发布链。
5. [ ] 解决或重新验证Windows ISIS 10 prefix的SpiceQL/mgs链接门槛。
6. [ ] 四条流水线全部通过后，分别创建两个版本的GitHub prerelease。

完成标准不是“所有差异都产生代码改动”，而是所有差异都有明确分类、需要
修改的部分实现并通过双版本验证、不需修改的部分有可复核证据。
