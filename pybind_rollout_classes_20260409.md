# Pybind Rollout Campaign 2026-04-09

本文档记录 2026-04-09 启动的 pybind 滚动绑定任务队列。
文档提供足够的摘要信息，供后续会话快速恢复上下文。

---

## 仓库状态快照（2026-04-09）

- `todo_pybind11.csv` 共 397 行
- `class_bind_methods_details/methods_inventory_summary.csv` 共 397 行
- rollout 顺序参考：`reference/notes/base_inventory_rollout_order_2026-04-08.md`
- 进度日志：`pybind_progress_log.md`

**第二阶段已完成：** Stereo, Angle, Blob, CameraPointInfo, Centroid, Intercept, Environment, Progress, IException, CollectorMap, CubeAttribute, Message, Resource, Ransac, Target, TrackingTable
**第二阶段待绑定：** 无（当前 rollout 台账范围内）
**第三阶段已完成：** Anisotropic2, HapkeAtm1/2, Isotropic1/2, ShadeAtm, TopoAtm, Hapke, PhotoModel, AtmosModel, AlbedoAtm, NumericalAtmosApprox
**第三阶段已完成补充：** SurfaceModel
**第三阶段待绑定：** 无
**第四阶段当前队列：** CubeBsqHandler, CubeCachingAlgorithm, CubeIoHandler（与第三批剩余队列合并推进）
**IException 状态说明：** `bind_base_support.cpp` 中已做 `py::register_exception<Isis::IException>(m, "IException")`，但未作完整类绑定（无 ErrorType enum, 无 toString 等方法），todo 标记仍为 `未转换`。

---

## 20 个候选类队列（优先级降序）

| 序号 | 类名 | 阶段 | 上游路径 | 复杂度 | 关键依赖 | 估计方法数 | 备注 |
|------|------|------|----------|--------|----------|------------|------|
| 1 | Progress | Phase 2 | `reference/upstream_isis/src/base/objs/Progress/` | 低 | Preference (需 DisableAutomaticDisplay) | 8 | constructor 依赖 Preference.Preferences()；绑定时需用 lambda |
| 2 | IException | Phase 2 | `reference/upstream_isis/src/base/objs/IException/` | 低-中 | FileName | 12 | 已有 register_exception；需补 ErrorType enum + 实例方法 |
| 3 | SurfaceModel | Phase 3 | `reference/upstream_isis/src/base/objs/SurfaceModel/` | 低 | LeastSquares, PolynomialBivariate（均已绑定） | 6 | 纯数学曲面拟合类 |
| 4 | TrackingTable | Phase 2 | `reference/upstream_isis/src/base/objs/TrackingTable/` | 低-中 | Table, FileName（均已绑定） | 7 | mosaic tracking；Table 已绑定 |
| 5 | Resource | Phase 2 | `reference/upstream_isis/src/base/objs/Resource/` | 中 | PvlFlatMap, PvlKeyword, GisGeometry | 20+ | 跳过 GisGeometry 相关方法，先绑定 PVL/name 核心 |
| 6 | CubeAttribute | Phase 2 | `reference/upstream_isis/src/base/objs/CubeAttribute/` | 中 | Cube, Endian, PixelType | 15+ | 含 LabelAttachment enum；模板类 CubeAttributeInput/Output |
| 7 | RegionalCachingAlgorithm | Phase 4 | upstream/base/objs/RegionalCachingAlgorithm/ | 低 | CubeCachingAlgorithm | 3 | 简单缓存算法 |
| 8 | OriginalLabel | Phase 4 | upstream/base/objs/OriginalLabel/ | 低-中 | Pvl, Table | 5 | cube 原始标签存取 |
| 9 | RawCubeChunk | Phase 4 | upstream/base/objs/RawCubeChunk/ | 中 | 无显著外部依赖 | 8 | 原始 DN 数据块 |
| 10 | SubArea | High Level | upstream/base/objs/SubArea/ | 低-中 | Cube | 5 | cube 子区域操作 |
| 11 | IssNACamera | Cassini | upstream/cassini/objs/IssNACamera/ | 低 | LineScanCamera | 6 | Cassini ISS 相机 |
| 12 | IssWACamera | Cassini | upstream/cassini/objs/IssWACamera/ | 低 | LineScanCamera | 6 | Cassini ISS 宽角相机 |
| 13 | NumericalAtmosApprox | Phase 3 | upstream/base/objs/NumericalAtmosApprox/ | 中 | AtmosModel | 10+ | 大气数值近似，待确认上游实现 |
| 14 | CollectorMap | Phase 2 | `reference/upstream_isis/src/base/objs/CollectorMap/` | 高 | 无（header-only 模板） | N/A | C++ 模板类；需为特定类型实例化 |
| 15 | Target | Phase 2 | `reference/upstream_isis/src/base/objs/Target/` | 高 | Spice, ShapeModel, Pvl, Distance, Angle | 15+ | SPICE 依赖重；需运行时数据 |
| 16 | Ransac | Phase 2 | `reference/upstream_isis/src/base/objs/Ransac/` | 中 | 无（namespace free functions） | 3 | 纯 free function API；用 m.def 暴露 |
| 17 | GainNonLinearity | MRO | upstream/mro/objs/GainNonLinearity/ | 低-中 | HiBlob, Pvl | 5 | MRO 工具类 |
| 18 | GainTemperature | MRO | upstream/mro/objs/GainTemperature/ | 低-中 | HiBlob, Pvl | 5 | MRO 工具类 |
| 19 | GainUnitConversion | MRO | upstream/mro/objs/GainUnitConversion/ | 低-中 | HiBlob, Pvl | 5 | MRO 工具类 |
| 20 | OriginalXmlLabel | Phase 4 | upstream/base/objs/OriginalXmlLabel/ | 中 | Pvl, Qt XML | 5 | XML 标签存取 |

---

## 执行队列 1（当前批次，5 类）

### Class 1: Progress

**目标文件：** `src/base/bind_base_support.cpp`
**方法摘要：**
- `Progress()` — 构造（需 Preference 初始化；lambda 包装）
- `SetText(str)` / `Text() -> str`
- `SetMaximumSteps(int)` / `AddSteps(int)`
- `CheckStatus()` — 推进一步并报告（调用时会打印，可 `DisableAutomaticDisplay()` 关闭）
- `DisableAutomaticDisplay()`
- `MaximumSteps() -> int` / `CurrentStep() -> int`
- `__repr__`

**注意：** constructor 内部调用 `Isis::Preference::Preferences().findGroup("UserInterface")`，在测试时需要先 `DisableAutomaticDisplay()` 避免 stdout 输出。`CheckStatus()` 在 `p_currentStep == 0` 时打印文本，测试中先 disable 自动显示。

**单测文件：** `tests/unitTest/progress_unit_test.py`
**Smoke：** 在 `test_basic_symbols_present()` 添加 `assert hasattr(ip, 'Progress')`

---

### Class 2: IException

**目标文件：** `src/base/bind_base_support.cpp`（在 `py::register_exception` 之后补充）
**方法摘要：**
- `IException()` 默认构造
- `IException(ErrorType, str, str, int)` — 带消息构造
- `ErrorType` enum (Unknown=1, User, Programmer, Io)
- `error_type() -> ErrorType`
- `to_string() -> str`
- `what() -> str`
- `append(other)`
- `error_type_to_string(ErrorType) -> str` (static)

**注意：** 已有 `py::register_exception` 注册为 Python 异常；现在补充完整类绑定，让它既可作为 Python 异常捕获，又可直接构造。Python 侧继承 `Exception`。

**单测文件：** `tests/unitTest/iexception_unit_test.py`

---

### Class 3: SurfaceModel

**目标文件：** `src/base/bind_base_math.cpp`（追加在末尾）
**方法摘要：**
- `SurfaceModel()` — 构造（内部 new LeastSquares + PolynomialBivariate）
- `add_triplet(x, y, z)`
- `add_triplets(xs, ys, zs)` — vector 重载
- `solve()`
- `evaluate(x, y) -> float`
- `min_max() -> (int, x, y)` — 返回 (rc, x, y) 元组

**注意：** `MinMax` 入参为引用出参；pybind11 中用 lambda 返回 `(int, double, double)` 元组。

**单测文件：** `tests/unitTest/math_unit_test.py`（追加到现有文件）

---

### Class 4: TrackingTable

**目标文件：** `src/bind_low_level_cube_io.cpp`（追加）
**方法摘要：**
- `TrackingTable()` — 默认构造
- `TrackingTable(Table)` — 从 Table 构造
- `to_table() -> Table`
- `pixel_to_file_name(pixel) -> FileName`
- `file_name_to_pixel(FileName, sn_str) -> int`
- `file_name_to_index(FileName, sn_str) -> int`
- `pixel_to_sn(pixel) -> str`

**注意：** `pixelToFileName` 如果 pixel 超范围会抛异常。测试使用空表默认构造 + to_table 验证。

**单测文件：** `tests/unitTest/low_level_cube_io_unit_test.py`（追加）

---

### Class 5: Resource

**目标文件：** `src/base/bind_base_utility.cpp`（追加）
**方法摘要（跳过 GisGeometry 相关）：**
- `Resource()` / `Resource(name)` / `Resource(other)` 构造
- `name() -> str` / `set_name(str)`
- `is_equal(other) -> bool`
- `exists(keyword_name) -> bool`
- `count(keyword_name) -> int`
- `is_null(keyword_name, index=0) -> bool`
- `value(keyword_name, index=0) -> str` / `value(keyword_name, default, index) -> str`
- `add(keyword_name, keyword_value)` / `add(PvlKeyword)`
- `append(keyword_name, value)`
- `erase(keyword_name) -> int`
- `activate()` / `is_active() -> bool` / `discard()` / `is_discarded() -> bool`
- `has_asset(name) -> bool` / `add_asset(name, value)` / `remove_asset(name) -> int` / `clear_assets() -> int`
- `to_pvl() -> PvlObject`
- **跳过：** `add(GisGeometry*)`, `add(SharedGisGeometry&)`, `has_geometry()`, `has_valid_geometry()`, `geometry()`, `keys()`, `keyword()`

**单测文件：** `tests/unitTest/resource_unit_test.py`

---

## 执行队列 2（已完成，5 类）

6. CollectorMap, 7. CubeAttribute, 8. Message, 9. Ransac, 10. Target

---

## 执行队列 3（当前批次，5 类）

11. NumericalAtmosApprox, 12. Blobber, 13. CubeBsqHandler, 14. CubeCachingAlgorithm, 15. CubeIoHandler

### Class 11: NumericalAtmosApprox

**目标文件：** `src/base/bind_base_photometry.cpp`
**方法摘要：**
- `NumericalAtmosApprox()` / `NumericalAtmosApprox(InterpType)`
- `InterpType` enum（作为 Python 嵌套枚举暴露）
- `IntegFunc` enum (`OuterFunction`, `InnerFunction`)
- `rombergs_method(atmos_model, sub_function, a, b)`
- `refine_extended_trap(atmos_model, sub_function, a, b, previous_sum, iteration)`
- `outr_func2_bint(atmos_model, phi)`
- `inr_func2_bint(atmos_model, mu)`

**注意：** `InrFunc2Bint()` 的上游“invalid switch”分支在 Python 中优先被 `AtmosModel.set_atmos_atm_switch(...)` 参数校验截住，因此 focused 单测按 Python 可达契约验证 setter 抛错；积分真值按 `reference/upstream_isis/src/base/objs/AtmosModel/unitTest.cpp` 的两组稳定配置校准。

**单测文件：** `tests/unitTest/atmos_model_factory_unit_test.py`（追加 `NumericalAtmosApproxUnitTest`）
**Smoke：** 在 `test_basic_symbols_present()` 添加 `assert hasattr(ip, 'NumericalAtmosApprox')`

### 下一个活动类：CubeBsqHandler

**预计目标文件：** `src/bind_low_level_cube_io.cpp`
**阶段：** 第四阶段后端 / 桥接 / 工具类
**当前状态：** 待阅读上游 `.h/.cpp` 与本地 low-level I/O 绑定模式后决定最小可行暴露面

---

## 执行记录

| 类名 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| Progress | ✅ 完成 | 2026-04-09 | py::class_ 绑定；10 个 focused 单测 |
| IException | ✅ 完成 | 2026-04-09 | IExceptionErrorType enum 补充；IException 本体已有 register_exception |
| SurfaceModel | ✅ 完成 | 2026-04-09 | 全部方法绑定；5 个 focused 单测追加至 math_unit_test.py |
| TrackingTable | ✅ 完成 | 2026-04-09 | 全部方法绑定；7 个 focused 单测追加至 low_level_cube_io_unit_test.py |
| Resource | ✅ 完成（Partial） | 2026-04-09 | PVL/name 核心接口绑定；跳过 GisGeometry/QVariant；15 个 focused 单测 |
| CollectorMap | ✅ 完成 | 2026-04-09 | 以稳定的 `CollectorMap<int, QString>` 专用实例暴露；6 个 focused 单测 |
| CubeAttribute | ✅ 完成 | 2026-04-09 | 暴露 `LabelAttachment`、`CubeAttributeInput`、`CubeAttributeOutput` 与属性 helper；6 个 focused 单测 |
| Message | ✅ 完成 | 2026-04-09 | 以 `ip.Message` 子模块暴露全部标准消息模板 helper；3 个 focused 单测 |
| Ransac | ✅ 完成 | 2026-04-09 | 以 `ip.Ransac` 子模块暴露全部 free-function helper；4 个 focused 单测 |
| Target | ✅ 完成（Partial） | 2026-04-09 | 补齐 NAIF/frame/body-rotation accessor，并通过 `Camera.target()` 暴露运行时 target；显式 `Spice *` API 仍受独立 Spice 绑定缺失阻塞 |
| NumericalAtmosApprox | ✅ 完成 | 2026-04-09 | 暴露嵌套 `InterpType` / `IntegFunc` 与全部积分 helper；3 个 focused 单测追加至 atmos_model_factory_unit_test.py |
| Blobber | ✅ 完成 | 2026-04-09 | 暴露构造/metadata/load/deepcopy/二维索引接口；2 个 focused 单测追加至 low_level_cube_io_unit_test.py，并顺带补 `Cube.read_table()` / `Cube.write(Table)` helper |

---

## 关键路径提示

- 绑定文件 `src/base/bind_base_support.cpp`：Progress + IException 扩展
- 绑定文件 `src/base/bind_base_math.cpp`：SurfaceModel
- 绑定文件 `src/bind_low_level_cube_io.cpp`：TrackingTable
- 绑定文件 `src/base/bind_base_utility.cpp`：Resource
- 绑定文件 `src/base/bind_base_utility.cpp`：CollectorMap + Message
- 绑定文件 `src/bind_low_level_cube_io.cpp`：CubeAttribute helpers
- 绑定文件 `src/base/bind_base_math.cpp`：Ransac helpers
- 绑定文件 `src/base/bind_base_target.cpp` / `src/bind_camera.cpp`：Target + Camera.target()
- 所有新 class 须在 `python/isis_pybind/__init__.py` 中导出
- 所有新 class 须在 `tests/smoke_import.py` 补最小 assert
- 完成后更新：`todo_pybind11.csv`, `class_bind_methods_details/*_methods.csv`, `class_bind_methods_details/methods_inventory_summary.csv`, `pybind_progress_log.md`
