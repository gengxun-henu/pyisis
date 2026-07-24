# ISIS 9.0.0 → ISIS 10.0.0 已安装 C++ API/ABI 系统对比

> 自动生成。头文件声明提取是机械指纹，不替代完整 C++ AST 审查；`libisis` 导出符号是实际 Linux 运行库证据。

- ISIS 9: `USGS ISIS 9.0.0 h1f94ec8_0 (linux-64, CPython 3.12)`
- ISIS 10: `USGS ISIS 10.0.0 h1f94ec8_1 (linux-64, CPython 3.13)`

## 结论摘要

| 层次 | ISIS 9 → ISIS 10 结果 |
| --- | --- |
| 头文件 | 新增 13，删除 1，字节完全一致 997 |
| 同名头文件 | 声明指纹变化 147，只有注释/格式/内联实现等非声明变化 18 |
| `libisis` 导出 | ISIS 9 为 16878，ISIS 10 为 16406；新增 283，移除 755，不变 16123 |
| 同名 callable 组 | 185 组的重载/参数/const 等导出签名集合发生变化 |

此前的“178 个文件变化”是旧 ASP prefix 的字节级结果。这里已经按当前 USGS 正式包重新计算，并将字节变化、声明变化与二进制符号变化分开。

## 新增头文件

- `Chandrayaan2OhrcCamera.h`
- `Chandrayaan2TmcCamera.h`
- `DskSegmentBuffer.hpp`
- `GdalIoHandler.h`
- `IEndian.h`
- `IProj.h`
- `ImageIoHandler.h`
- `OsirisRexOcamsOpenCVDistortionMap.h`
- `RestfulSpice.h`
- `csv2table.h`
- `eisstitch.h`
- `ocams2isis.h`
- `restincurl.h`

## 删除或重命名头文件

- `Endian.h`

`Endian.h` 在 ISIS 10 中对应 `IEndian.h`，需按重命名而非功能整体删除处理。

## 机械识别的新增类

- `Chandrayaan2OhrcCamera`
- `Chandrayaan2TmcCamera`
- `DskSegmentBuffer`
- `GdalIoHandler`
- `IProj`
- `ImageIoHandler`
- `OsirisRexOcamsOpenCVDistortionMap`

## 机械识别的删除类

- 无

## 同名但声明或导出发生变化的类

- 头文件主类声明变化：127 个。完整类名如下：
- `APrioriLatitudeFilter`
- `APrioriLatitudeSigmaFilter`
- `APrioriLongitudeFilter`
- `APrioriLongitudeSigmaFilter`
- `APrioriRadiusFilter`
- `APrioriRadiusSigmaFilter`
- `APrioriXFilter`
- `APrioriXSigmaFilter`
- `APrioriYFilter`
- `APrioriYSigmaFilter`
- `APrioriZFilter`
- `APrioriZSigmaFilter`
- `AbstractFilter`
- `AbstractNullDataItem`
- `AbstractTreeModel`
- `AdjustedLatitudeFilter`
- `AdjustedLatitudeSigmaFilter`
- `AdjustedLongitudeFilter`
- `AdjustedLongitudeSigmaFilter`
- `AdjustedRadiusFilter`
- `AdjustedRadiusSigmaFilter`
- `AdjustedXFilter`
- `AdjustedXSigmaFilter`
- `AdjustedYFilter`
- `AdjustedYSigmaFilter`
- `AdjustedZFilter`
- `AdjustedZSigmaFilter`
- `Application`
- `Blob`
- `BulletShapeModel`
- `BulletTargetShape`
- `BundleResults`
- `BusyLeafItem`
- `Calculator`
- `CameraFactory`
- `CameraFocalPlaneMap`
- `ChooserNameFilter`
- `Color`
- `ControlList`
- `ControlMeasure`
- `ControlNet`
- `ControlPoint`
- `Cube`
- `CubeAttribute`
- `CubeCalculator`
- `CubeDataThread`
- `CubeDataThreadTester`
- `CubeIoHandler`
- `DemShape`
- `EllipsoidShape`
- `EmbreeShapeModel`
- `Environment`
- `FeatureNomenclatureTool`
- `FileName`
- `FilterWidget`
- `FindTool`
- `GoodnessOfFitFilter`
- `GridPolygonSeeder`
- `GroupedStatistics`
- `GuiCameraList`
- `GuiParameter`
- `HistogramItem`
- `IException`
- `ImageIdFilter`
- `ImageList`
- `ImageListActionWorkOrder`
- `ImageReader`
- `LineFilter`
- `LineResidualFilter`
- `LineShiftFilter`
- `MatchToolNewPointDialog`
- `MeasureCountFilter`
- `MeasureIgnoredFilter`
- `MeasureJigsawRejectedFilter`
- `MeasureTableModel`
- `MeasureTypeFilter`
- `MeasureValidationResults`
- `NaifDskShape`
- `NewControlPointDialog`
- `NirsImportFits`
- `OsirisRexDistortionMap`
- `OsirisRexOcamsCamera`
- `PlotWindow`
- `PointCloudSearchResult`
- `PointEditLockedFilter`
- `PointIdFilter`
- `PointIgnoredFilter`
- `PointJigsawRejectedFilter`
- `PointTableModel`
- `PointTypeFilter`
- `Preference`
- `ProcessByBrick`
- `ProjectItemModel`
- `Pvl`
- `PvlContainer`
- `PvlFormat`
- `PvlKeyword`
- `PvlObject`
- `QnetFixedPointDialog`
- `QnetNewMeasureDialog`
- `QnetSetAprioriDialog`
- `ResidualMagnitudeFilter`
- `RootItem`
- `SampleFilter`
- `SampleResidualFilter`
- `SampleShiftFilter`
- `ScatterPlotConfigDialog`
- `ScatterPlotData`
- `ScatterPlotTool`
- `ShadowFunctor`
- `ShapeList`
- `ShapeModel`
- `ShapeReader`
- `SpatialPlotTool`
- `Spice`
- `SpiceClient`
- `SpkKernelWriter`
- `Strategy`
- `TabBar`
- `Table`
- `TableColumnList`
- `TableViewHeader`
- `TargetBody`
- `TargetBodyList`
- `Tool`
- `UniversalGroundMap`
- `Workspace`

- `libisis` 方法签名集合变化涉及：129 个类。完整映射见 callable CSV。

## 同名自由函数签名集合变化

- `Isis::ExtractLatLonRange`
- `Isis::ExtractPointList`
- `Isis::WriteResults`
- `Isis::getCameraPointInfo`
- `Isis::getProjPointInfo`
- `Isis::operator<<`
- `Isis::operator>>`
- `Isis::toString`

## 核心库导出变化分类

| 类型 | 新增导出 | 移除导出 |
| --- | ---: | ---: |
| data | 21 | 26 |
| function | 6 | 38 |
| method | 244 | 670 |
| thunk | 0 | 9 |
| type_metadata | 12 | 12 |

## Deprecated 声明线索

- ISIS 10 新增 deprecated 声明指纹：0 条。
- ISIS 9 中存在、ISIS 10 不再出现的 deprecated 声明指纹：0 条。
- 在重命名头文件间保持一致的 deprecated 声明指纹：2 条。
- 完整声明见 header diff CSV 的 `deprecated_added` 和 `deprecated_removed` 字段；消失可能表示删除、重命名或文档迁移，不能单凭该字段判断。

## 如何阅读“修改”

- 同一 callable 名称的签名集合有增有减，表示参数、const、重载或 ABI 签名发生变化，完整记录见 `isis9-isis10-core-callable-changes.csv`。
- 头文件声明变化但导出不变，可能是 inline/template、默认参数、枚举、访问限定或仅编译期 API 变化，见 `isis9-isis10-installed-header-diff.csv`。
- 导出变化但头文件机械指纹未捕获，可能来自私有实现、模板实例、thunk、类型信息或解析器边界，必须人工复核。

## 完整明细

- `isis9-isis10-installed-header-diff.csv`：全部头文件及类/枚举/callable 声明差异。
- `isis9-isis10-core-symbol-diff.csv`：全部 `libisis` demangled 导出集合。
- `isis9-isis10-core-callable-changes.csv`：同名 callable 的签名集合变化。
