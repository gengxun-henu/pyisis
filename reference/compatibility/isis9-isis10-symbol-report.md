# ISIS 9 / ISIS 10 当前绑定头文件审计

> 自动生成文件。文本变化只表示需要人工 API 审阅，不等同于 ABI 不兼容。

- ISIS 9 source: `USGS ISIS 9.0.0 h1f94ec8_0 installed headers`
- ISIS 10 source: `USGS ISIS 10.0.0 h1f94ec8_1 installed headers`
- 当前 binding-header 引用行数（过滤 GUI 后）: 539
- 当前 ISIS 头文件数: 381
- 文本一致: 328
- 需要人工复核: 48
- 已识别头文件重命名候选: 1
- ISIS 9 缺失: 4
- ISIS 10 缺失: 0
- 路径不唯一: 0

## 需要复核的头文件

| Bindings | Header | Comparison | Replacement | GUI status |
| --- | --- | --- | --- | --- |
| `src/base/bind_auto_reg_factory.cpp, src/base/bind_base_filters.cpp, src/base/bind_base_pattern.cpp, src/base/bind_base_photometry.cpp, src/base/bind_base_polygon_seeder.cpp, src/base/bind_base_projection.cpp, src/base/bind_base_projection_types.cpp, src/base/bind_base_pvl.cpp, src/base/bind_base_support.cpp, src/base/bind_base_target.cpp, src/bind_camera_maps.cpp, src/bind_isis10.cpp, src/bind_low_level_cube_io.cpp, src/bind_mro_hical.cpp, src/bind_spice_navigation.cpp, src/control/bind_control_core.cpp, src/control/bind_interest_operator_factory.cpp, src/mission/bind_mission_cameras.cpp` | `Pvl.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_geometry.cpp, src/base/bind_base_image_polygon.cpp, src/base/bind_base_pvl.cpp, src/base/bind_base_support.cpp, src/bind_mro_hical.cpp, src/bind_spice_navigation.cpp` | `IException.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_ground_map.cpp, src/base/bind_base_math.cpp, src/base/bind_base_pattern.cpp, src/base/bind_base_projection.cpp, src/base/bind_base_support.cpp, src/bind_camera_factory.cpp, src/bind_isis10.cpp, src/bind_low_level_cube_io.cpp, src/bind_mro_hical.cpp, src/bind_spice_navigation.cpp, src/bind_statistics.cpp, src/mgs/bind_mgs_utilities.cpp, src/mission/bind_mission_cameras.cpp` | `Cube.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_ground_map.cpp, src/base/bind_base_projection.cpp, src/base/bind_base_projection_types.cpp, src/bind_low_level_cube_io.cpp` | `Projection.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_ground_map.cpp` | `UniversalGroundMap.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_image_polygon.cpp, src/bind_low_level_cube_io.cpp` | `Blob.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_math.cpp` | `Calculator.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_math.cpp` | `CubeCalculator.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_math.cpp` | `InfixToPostfix.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_pattern.cpp, src/bind_low_level_cube_io.cpp, src/bind_statistics.cpp, src/control/bind_bundle_advanced.cpp, src/control/bind_control_core.cpp` | `Statistics.h` | `identical_text` | `` | `qt_observer_review` |
| `src/base/bind_base_pds_io.cpp, src/base/bind_base_pvl.cpp, src/base/bind_base_utility.cpp, src/bind_spice_navigation.cpp, src/bind_statistics.cpp, src/control/bind_control_core.cpp` | `PvlObject.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_pds_io.cpp, src/bind_low_level_cube_io.cpp` | `Table.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_polygon_seeder.cpp` | `GridPolygonSeeder.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_projection.cpp, src/base/bind_base_projection_types.cpp, src/bind_isis10.cpp` | `TProjection.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_pvl.cpp, src/base/bind_base_support.cpp, src/bind_high_level_cube_io.cpp, src/bind_low_level_cube_io.cpp, src/control/bind_bundle_advanced.cpp, src/control/bind_control_core.cpp` | `FileName.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_pvl.cpp` | `LabelTranslationManager.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_pvl.cpp` | `PvlContainer.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_pvl.cpp` | `PvlFormat.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_pvl.cpp, src/base/bind_base_utility.cpp, src/control/bind_control_core.cpp` | `PvlKeyword.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_pvl.cpp` | `PvlToPvlTranslationManager.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_pvl.cpp` | `PvlToXmlTranslationManager.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_pvl.cpp` | `XmlToPvlTranslationManager.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_shape.cpp` | `BulletShapeModel.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_shape.cpp` | `DemShape.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_shape.cpp` | `EllipsoidShape.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_shape.cpp` | `EmbreeShapeModel.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_shape.cpp` | `NaifDskShape.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_shape.cpp, src/base/bind_base_target.cpp` | `ShapeModel.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_shape_support.cpp` | `BulletTargetShape.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_utility.cpp` | `Environment.h` | `changed_review_required` | `` | `non_gui` |
| `src/base/bind_base_utility.cpp` | `SpecialPixel.h` | `changed_review_required` | `` | `non_gui` |
| `src/bind_camera.cpp, src/bind_camera_maps.cpp, src/lro/bind_lro_utilities.cpp` | `CameraFocalPlaneMap.h` | `changed_review_required` | `` | `non_gui` |
| `src/bind_camera_factory.cpp` | `CameraFactory.h` | `changed_review_required` | `` | `non_gui` |
| `src/bind_high_level_cube_io.cpp, src/bind_low_level_cube_io.cpp` | `CubeAttribute.h` | `changed_review_required` | `` | `non_gui` |
| `src/bind_high_level_cube_io.cpp` | `ProcessByBrick.h` | `changed_review_required` | `` | `non_gui` |
| `src/bind_isis10.cpp` | `Chandrayaan2OhrcCamera.h` | `missing_in_isis9` | `` | `non_gui` |
| `src/bind_isis10.cpp` | `Chandrayaan2TmcCamera.h` | `missing_in_isis9` | `` | `non_gui` |
| `src/bind_isis10.cpp` | `IProj.h` | `missing_in_isis9` | `` | `non_gui` |
| `src/bind_low_level_cube_io.cpp` | `Endian.h` | `renamed_review_required` | `IEndian.h:IEndian.h` | `non_gui` |
| `src/bind_low_level_cube_io.cpp` | `IEndian.h` | `missing_in_isis9` | `` | `non_gui` |
| `src/bind_low_level_cube_io.cpp` | `PixelType.h` | `changed_review_required` | `` | `non_gui` |
| `src/bind_spice_navigation.cpp` | `Spice.h` | `changed_review_required` | `` | `non_gui` |
| `src/bind_spice_navigation.cpp, src/control/bind_bundle_advanced.cpp, src/control/bind_control_core.cpp` | `SpiceRotation.h` | `changed_review_required` | `` | `non_gui` |
| `src/bind_statistics.cpp` | `GroupedStatistics.h` | `changed_review_required` | `` | `non_gui` |
| `src/control/bind_bundle_advanced.cpp` | `BundleResults.h` | `changed_review_required` | `` | `qt_observer_review` |
| `src/control/bind_bundle_advanced.cpp, src/control/bind_control_core.cpp` | `BundleSettings.h` | `changed_review_required` | `` | `non_gui` |
| `src/control/bind_bundle_advanced.cpp` | `BundleSolutionInfo.h` | `changed_review_required` | `` | `qt_observer_review` |
| `src/control/bind_bundle_advanced.cpp, src/control/bind_control_core.cpp` | `ControlMeasure.h` | `changed_review_required` | `` | `qt_observer_review` |
| `src/control/bind_bundle_advanced.cpp, src/control/bind_control_core.cpp` | `ControlNet.h` | `changed_review_required` | `` | `qt_observer_review` |
| `src/control/bind_bundle_advanced.cpp, src/control/bind_control_core.cpp` | `ControlPoint.h` | `changed_review_required` | `` | `qt_observer_review` |
| `src/control/bind_bundle_advanced.cpp` | `ImageList.h` | `changed_review_required` | `` | `qt_observer_review` |
| `src/control/bind_control_core.cpp` | `MeasureValidationResults.h` | `changed_review_required` | `` | `non_gui` |
| `src/mission/bind_mission_cameras.cpp` | `OsirisRexDistortionMap.h` | `changed_review_required` | `` | `non_gui` |
| `src/mission/bind_mission_cameras.cpp` | `OsirisRexOcamsCamera.h` | `changed_review_required` | `` | `non_gui` |

## 使用边界

- 编译签名必须继续以目标 conda 或 Windows prefix 的头文件为准。
- `changed_review_required` 需要进一步比较声明、链接符号和行为。
- `renamed_review_required` 是已定位的候选替代头，仍需编译验证。
- `qt_observer_review` 表示类中含 Qt observer API；signals/slots 默认不绑定。
- 详细逐行数据见 `isis9-isis10-header-matrix.csv`。
