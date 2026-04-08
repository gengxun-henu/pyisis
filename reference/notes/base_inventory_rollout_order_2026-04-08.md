# Base 非 GUI 类 inventory / pybind 推进顺序（2026-04-08）

这份文档用于固化 `base` 目录下非 GUI 类的后续补齐顺序，作为后续 inventory 纳入、方法清单生成、pybind 绑定实现与测试推进的统一参考。

## 背景

前期核对 `reference/upstream_isis/src/base/objs/` 与当前 `todo_pybind11.csv`、`class_bind_methods_details/` 后，已经确认：

- `Stereo` 是明确存在于上游的有效类；
- 它缺失于当前 inventory 的直接原因，不是 GUI 过滤，而是 **todo / inventory 同步遗漏**；
- `base` 下还存在一批明确非 GUI、且有实际绑定价值的类，尚未纳入当前推进主线。

因此，后续补齐工作按“先小而关键，再批量扩展”的顺序推进。

## 总体推进顺序

### 第一阶段：优先补 `Stereo`

先补 `Stereo`，把它作为当前 inventory 补漏与后续绑定推进的第一优先级。

原因：

- 上游位置明确：`reference/upstream_isis/src/base/objs/Stereo/`
- 类职责明确，属于重要基础几何/立体相关工具类
- 已确认属于“应在 inventory 中但目前遗漏”的代表性案例
- 先补它有利于验证后续“inventory -> 细项 CSV -> 绑定 -> 测试”这一整条链路

## 第二阶段：补一批“高价值且明确非 GUI”的基础类

在 `Stereo` 之后，按下列顺序推进：

1. `Angle`
2. `Blob`
3. `CameraPointInfo`
4. `Centroid`
5. `CollectorMap`
6. `CubeAttribute`
7. `Environment`
8. `IException`
9. `Intercept`
10. `Message`
11. `Progress`
12. `Resource`
13. `Ransac`
14. `Target`
15. `TrackingTable`

这一批的定位是：

- 明确属于非 GUI 基础类；
- 具备较高复用价值，能为后续其它 binding 提供支撑；
- 很多类本身就适合作为 Python 侧常用基础对象或辅助工具；
- 比 shape / photometry 大批量类更适合作为第二波稳定推进对象。

## 第三阶段：补 shape / photometry 一批

完成上述基础类后，再进入 shape / photometry 方向的一批类。

当前先明确纳入这一阶段、且仍属于“待绑定 inventory”的类如下：

1. `Anisotropic2`
2. `HapkeAtm1`
3. `HapkeAtm2`
4. `Isotropic1`
5. `Isotropic2`
6. `ShadeAtm`
7. `TopoAtm`
8. `Hapke`
9. `PhotoModel`
10. `AtmosModel`
11. `NumericalAtmosApprox`
12. `SurfaceModel`

补充说明：

- `NormModel` 已在当前仓库中完成绑定、顶层导出与测试覆盖，因此不再作为本阶段“待绑定”对象重复登记。
- `ShapeModel` 也已在当前仓库中完成绑定、顶层导出与测试覆盖，因此不再作为本阶段“待绑定”对象重复登记。
- 本阶段先继续做 inventory / methods CSV / summary 同步，不在这一轮直接展开 pybind 实现。

这一阶段的工作特点：

- 类之间继承、工厂和算法关系更复杂；
- 更依赖上游 `.cpp` 行为阅读，而不只是 `.h` 签名；
- 更容易出现“类符号已导出但行为不完整”或“工厂路径可用但直接类未暴露”的情况；
- 需要更严格地区分：
  - inventory 已纳入但未绑定
  - 已绑定但 class symbol 未稳定导出
  - 已导出但缺少 focused 单测

建议这一阶段仍按“小批次提交”的方式推进，而不要一次性全面铺开。

## 第四阶段：最后纳入后端 / 桥接 / 工具类

最后再处理更偏后端、桥接层、内部工具性质的类。

当前先明确纳入这一阶段、且仍属于“待绑定 inventory”的类如下。

### 子组 A：低层 cube 后端 / handler 链

1. `Blobber`
2. `CubeBsqHandler`
3. `CubeCachingAlgorithm`
4. `CubeIoHandler`
5. `CubeTileHandler`
6. `RegionalCachingAlgorithm`
7. `RawCubeChunk`
8. `OriginalLabel`
9. `OriginalXmlLabel`

### 子组 B：解析 / 翻译 / 插件桥接

10. `Plugin`
11. `FileList`
12. `CSVReader`
13. `IString`
14. `LabelTranslationManager`
15. `PvlTokenizer`
16. `PvlToken`
17. `PvlTranslationTable`
18. `PvlToPvlTranslationManager`
19. `PvlToXmlTranslationManager`
20. `XmlToPvlTranslationManager`
21. `PvlFormat`
22. `PvlFormatPds`

补充说明：

- 这一阶段不再重复纳入第二阶段中已经提前登记的工具类，例如 `Environment`、`IException`、`Message`、`Progress`、`CollectorMap`、`CubeAttribute`、`Blob`、`Ransac`。
- 这一阶段也不再混入第三阶段的 shape / photometry 类，例如 `PhotoModel`、`AtmosModel`、`Hapke`、`SurfaceModel`。
- mission camera、control-network 主线和 SensorUtilities 轻量值类型暂不并入本阶段，以免把“后端 / 桥接 / 工具类”批次再次拉散。
- 本阶段先继续做 inventory / methods CSV / summary 同步，不在这一轮直接展开 pybind 实现。

这一阶段通常包括以下特点的对象：

- 对最终 Python 用户不一定直接友好；
- 更可能依赖内部生命周期、缓存、桥接结构或复杂上下文；
- 绑定价值存在，但优先级低于前面三阶段；
- 更适合在前面基础能力补齐后，再作为完善性工作来收尾。

## 执行规则

后续按本路线推进时，建议每个类都遵循下面的最小闭环：

1. 先在 `todo_pybind11.csv` 中登记或校正状态；
2. 补对应的 `class_bind_methods_details/*_methods.csv`；
3. 同步 `class_bind_methods_details/methods_inventory_summary.csv`；
4. 再做 pybind 实现；
5. 补最小必要的 focused 单测；
6. 必要时补最小 smoke 覆盖；
7. 最后更新 `pybind_progress_log.md`。

## 具体推进建议

### 建议的提交粒度

优先采用以下粒度，而不是一次处理太多类：

- `Stereo` 单独一个提交或一个小批次
- 第二阶段基础类按 2 到 4 个类为一组推进
- 第三阶段 shape / photometry 按同一子方向分组推进
- 第四阶段后端 / 桥接 / 工具类按依赖关系分组推进

### 建议的优先判断标准

如果同一阶段内还要继续细排优先级，优先考虑：

1. 是否已确认上游有稳定 `unitTest.cpp`
2. 是否为多个绑定/测试场景的公共依赖
3. 是否 API 面较小、容易快速形成闭环
4. 是否能作为后续一串类的基础设施

## 本文档的用途

这不是一次性的讨论记录，而是后续推进 `base` 非 GUI 类 inventory 与 pybind 工作的顺序说明。

如果后续实践中发现某些类应前移或后移，应直接更新本文档，而不是只在聊天记录里口头约定。

## 当前确认版顺序

- 第一阶段：`Stereo`
- 第二阶段：`Angle` -> `Blob` -> `CameraPointInfo` -> `Centroid` -> `CollectorMap` -> `CubeAttribute` -> `Environment` -> `IException` -> `Intercept` -> `Message` -> `Progress` -> `Resource` -> `Ransac` -> `Target` -> `TrackingTable`
- 第三阶段：`Anisotropic2` -> `HapkeAtm1` -> `HapkeAtm2` -> `Isotropic1` -> `Isotropic2` -> `ShadeAtm` -> `TopoAtm` -> `Hapke` -> `PhotoModel` -> `AtmosModel` -> `NumericalAtmosApprox` -> `SurfaceModel`
- 第四阶段：`Blobber` -> `CubeBsqHandler` -> `CubeCachingAlgorithm` -> `CubeIoHandler` -> `CubeTileHandler` -> `RegionalCachingAlgorithm` -> `RawCubeChunk` -> `OriginalLabel` -> `OriginalXmlLabel` -> `Plugin` -> `FileList` -> `CSVReader` -> `IString` -> `LabelTranslationManager` -> `PvlTokenizer` -> `PvlToken` -> `PvlTranslationTable` -> `PvlToPvlTranslationManager` -> `PvlToXmlTranslationManager` -> `XmlToPvlTranslationManager` -> `PvlFormat` -> `PvlFormatPds`
