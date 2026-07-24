# 发现记录：ISIS 10 新增能力审计、绑定与双版本发布

## 当前事实

- `asp360_new/include/isis` 安装 1163 个头文件。
- 官方 `asp370/include/isis` 安装 1175 个头文件。
- 按 `.h`/`.hpp` basename 比较，ISIS 10 新增 13 个头文件、移除 1 个。
- 当前人工候选清单包含 6 个类，其中 3 个已绑定。
- 正式包新增类候选为 IProj、Chandrayaan-2 两个相机类、
  GdalIoHandler、ImageIoHandler 和 OsirisRexOcamsOpenCVDistortionMap。
- `tools/dev/generate_isis10_bind_inventory.py` 当前使用硬编码
  `CLASS_CANDIDATES` / `FUNCTION_CANDIDATES`，只验证已列候选，不自动发现遗漏。
- 当前 worktree 中 ISIS 10 上游镜像存在，ISIS 9 上游镜像已清理；两个 conda
  prefix 均存在，可直接作为已安装 API 差异依据。
- 双向正式 prefix 比较结果：ISIS 10 新增 13 个头文件、移除
  `Endian.h`；同名声明差异仍需 Phase 1 完整重算。
- `Endian.h` 到 `IEndian.h` 是内容保持一致的文件名变化；其中
  `IsLittleEndian()` 和 `IsBigEndian()` 本身带 `@deprecated`。
- 本机 ISIS 10 包已替换为 USGS channel 的
  `isis 10.0.0 h1f94ec8_1`。
- 官方 `10.0.0` tag 为 commit `524eec10...`，自带 `CHANGELOG.md`。
- 官方 Changelog 明确列出 IProj、GeoTIFF/GDAL、Chandrayaan-2 相机、
  eisstitch、SpiceQL 等变化，并列出 Qt 6 导致 isisminer 不再支持 MySQL。
- 旧 `asp_4` 安装过 ShadowCam、AspMapProjection 等 11 个正式包没有的
  新增头文件；这些内容不再进入 USGS ISIS 10 正式绑定候选。
- 官方 Changelog 是重要线索，但不是完整 API/ABI 清单；ShadowCam 差异就是
  不能只依赖 Changelog 的直接例子。
- USGS 官方 conda channel 已发布 Linux 正式包
  `isis 10.0.0 h1f94ec8_1`，时间戳为 2026-06-22。
- 该正式包固定依赖 CPython 3.13 ABI，因此 ISIS 10 wheel 构建需要转为
  CPython 3.13；不能继续复用 ISIS 9 当前的 CPython 3.12 ABI。
- 官方仓库 `environment.yml` 的 channel 顺序为 `conda-forge` 后
  `usgs-astrogeology`；USGS channel 没有 `current_repodata.json`。
- `isis` 包对 `csm` 未限制版本；2026-07 的 `csm 3.1.0` 缺少 ISIS
  二进制依赖的 `libcsmapi.so.3` 链接名，开发环境固定 `csm 3.0.3.3`。
- 正式环境中 `libisis9.0.0.so` 有 16,289 个 `Isis::` 导出项，
  `libisis10.0.0.so` 有 15,763 个；数量下降不等于简单删除，需按完整
  demangled signature 做新增/移除集合并识别构造/析构等 ABI 噪声。
- 正式 ISIS 9/10 prefix 分别有 1,230/1,453 个实际 `.so*` 文件；核心
  `libisis` 与任务插件库需要分层审计，不能只比较一个总文件数。
- USGS 正式 prefix 重新核算后，同名头文件的字节变化不是 178，而是 165：
  147 个有机械声明指纹变化，18 个只有非声明文本变化；另有 13 新增、1 删除。
- 初次类名汇总混入 Qt 前置声明和 `restincurl` 第三方类，因此正式报告按
  “头文件 basename 对应主类”给出新增/删除类，所有原始声明仍保留在 CSV。
- 初次符号集合允许任意包含 `Isis::` 的模板实例，混入 `QList<Isis::...>` 和
  `std::...`；已收紧为 ISIS namespace、ISIS type metadata 与 ISIS thunk。
- 清洗后的核心库集合：ISIS 9 为 16,878、ISIS 10 为 16,406；16,123 不变，
  283 新增，755 移除，185 组同名 callable 的签名集合变化。
- 185 组 callable 变化中，40 组含 `QVector→QList`、66 组含
  `QPair→std::pair`、21 组是 Protobuf `MergeImpl` 变化。
- 当前 binding 源码引用 381 个唯一 ISIS 头文件：328 文本一致、48 需复核、
  1 个重命名、4 个仅 ISIS 10 存在、0 个在 ISIS 10 无替代缺失。
- 6 个新增公共类和 3 个应用函数均已在正式 ISIS 10 对应 `.so` 中找到导出；
  `DskSegmentBuffer` 标记为 internal，不进入公共绑定。
- Deprecated 指纹比较没有发现新增或真正消失项；`Endian.h→IEndian.h` 间
  保持了 2 条相同 deprecated inline helper 声明。

## 初步分类

- class：6
- function/application headers：3
- compatibility/internal/placeholder/third-party excluded：4

详细分类将在 Phase 1 由生成器输出并由测试锁定。

## 绑定架构结论

- 现有单 `_isis_core`、公共源文件列表、CMake 版本探测和
  `src/bind_isis10.cpp` 的总体结构适合继续维护，不需要按 ISIS 9/10
  复制两套 `src/`。
- “48 个需复核头文件”不是“48 个类都要重写”。应只比较当前 pybind
  实际调用的声明；未触及的 ISIS 内部变化不进入绑定修改。
- 高频差异是 Qt6 容器迁移：40 组 callable 涉及 `QVector→QList`，
  66 组涉及 `QPair→std::pair`。Python 层应保持稳定容器语义，差异在
  C++ 边界消化。
- 兼容代码按 `shared-no-change`、`shared-wrapper`、`version-guarded`、
  `isis10-only` 和 `excluded` 五类闭环。
- 优先审计 Cube/PVL、Control/Bundle、Shape、Camera/Spice、
  OSIRIS-REx；低风险工具类在确认绑定所用签名一致后保持原代码。
- 最新 CI 表明 Linux ISIS 9/10 和 Windows ISIS 9 已通过构建及干净安装；
  Windows ISIS 10 失败发生在 ISIS 自身 `mgs.dll` 链接阶段，错误为
  `SpiceQL::strSclkToEt(...)` 未解析，并非当前 PyISIS 绑定编译失败。

## 审计层次

1. conda prefix 文件级新增/删除/同名变化。
2. C++ 声明级类、方法、函数、枚举及弃用标记差异。
3. 官方 Changelog 的 Added/Changed/Deprecated/Removed/Breaking 线索。
4. 官方 tag 源码与实际 USGS conda build 差异；ASP build 仅作历史对照。
5. Linux/Windows 动态库导出符号及链接验证。
6. 现有 Python 绑定在 ISIS 9/10 下的编译、导入和行为测试。

## Windows APP 后续扩展基线

- 正式 `asp370` ISIS 10.0.0 prefix 安装 366 个应用 XML，其中 54 个名称
  匹配 `*2isis`；需要进一步区分任务仪器导入、通用格式导入和 DSK 等
  非摄影测量影像入口。
- ISIS 9 Windows 已能构建 CLI/GUI 应用；当前 smoke 默认覆盖 9 个常用
  应用，并为 `lronac2isis→spiceinit→lronaccal→lronacecho` 保留真实
  LRO 数据可选流程。
- ISIS 10 Windows 的精简补丁在 MSVC 下排除所有模块 `apps` 目录，原因是
  将全部应用实现合入单一 export-all DLL 会超过 65,535 个 import-library
  成员。因此未来应用扩展必须使用按应用独立目标或小型任务包。
- `spiceinit`、`hrsc2isis`、`lronac2isis` 等正式安装头文件提供
  `UserInterface` 形式的 C++ 入口；未来应复用 USGS 实现，不能重写算法。
- 用户提出的流程分层合理：任务导入/校正和 SPICE 优先，控制网工具其次，
  `qnet/qview/qmos` 等 GUI 最后。需要修正的是 `jigsaw` 本身是重型
  非 GUI bundle adjustment，不应与 Qt GUI 等同，但因依赖广、验收成本高，
  仍适合放在后期独立阶段。
- 54 个 `*2isis` 中有45个任务/仪器入口，覆盖 Apollo、Hayabusa 系列、
  OSIRIS-REx、Rosetta、Dawn、Galileo、Cassini、Voyager、New Horizons、
  LRO、MRO、Mars Express 等；其余9个是 PDS/FITS/VICAR/RAW/常见图像、
  ISIS2旧格式或 DSK 入口。
- `spiceinit`、`hrsc2isis`、`lronac2isis`、`lronaccal`、`footprintinit`、
  `findimageoverlaps`、`autoseed`、`pointreg`、`jigsaw` 有正式安装 C++
  header；`lronacecho`、`cnetadd`、`cnetref` 等没有同名公共 header，
  因此不能假定所有应用都适合直接 pybind，原生 executable 是公共基线。

## Phase 2 当前兼容队列

- 首批5项为 `Cube`、`CubeAttribute`、`Blob`、`Table`、
  `ProcessByBrick`，严格一次关闭一项。
- `Cube.h` 存在真实 Python 可见差异：
  - ISIS 9：`labelsAttached()` 返回 `bool`，
    `setLabelsAttached(bool)` 接受布尔值；
  - ISIS 10：二者改用 `Cube::LabelAttachment`，并新增
    `AttachedLabel/DetachedLabel/ExternalLabel/GdalLabel`；
  - ISIS 10 `Cube::Format` 新增 `GTiff`；
  - ISIS 10 删除 `storesDnData()`，当前绑定已经用
    `labelsAttached() != ExternalLabel` 做局部兼容。
- 因此同一绑定源码能编译并不足以证明 Python API兼容；需要验证
  `labels_attached()` 仍返回 `bool`、`set_labels_attached(bool)` 仍接受
  布尔值，同时可以选择性暴露 ISIS 10新增枚举能力。
- `CubeAttribute`探测发现ISIS 9的内联
  `LabelAttachmentEnumeration()`把输入转成大写后却比较`"External"`，
  因而大小写形式均无法解析；绑定边界需要稳定映射`EXTERNAL`。
- ISIS 10修复上述问题并支持`GdalLabel`枚举、`Cube::Format::GTiff`和
  `propagateFileFormat()`；`CubeAttributeOutput("+GTiff")`可用，但
  `"+Gdal"`仍不被属性解析器接受，因此只暴露真实上游能力。
- `CubeAttribute`已通过共享wrapper闭环：不复制两套绑定主体，只在公共
  字符串转换边界修复External，并对ISIS 10新增符号使用局部版本门。
- `Blob.h`的共有文件/bytes/label表面未变；ISIS 10新增`Key()`、
  `StartByte()`与GDAL读写。前两者是安全只读元数据，后者涉及
  `GDALDataset *`和可变C++字符串，当前不适合作为直接pybind接口。
- ISIS 9/10的C++ `fstream`写入签名不同，但该路径原本就未绑定，因此
  不影响现有Python契约，也不需要复制版本实现。
- `Table.h`只有无参构造在ISIS 10中被移除；现有Python绑定从未导出该
  构造，其余`Table`公开声明以及`TableRecord.h`、`TableField.h`均一致。
- `base_table_methods.csv`此前将大量已经绑定的方法误记为N；本轮按实际
  代码校正，并补齐`Table(Blob&)`和`toBlob()`这一组安全值语义接口。
- `ProcessByBrick.h`的唯一差异是受Qt5/Qt6影响的内部
  `BlockingReportProgress(QFuture<...>&)`类型；当前绑定不引用该方法，
  所有已导出的公开配置签名一致，无需版本适配。
- `ProcessByBrick`的Python回调处理不能仅凭头文件差异顺手绑定：必须先
  设计GIL、临时Buffer引用生命周期与线程策略，因此作为独立功能项保留，
  不与跨版本兼容审计混合。
- `Pvl.h`在ISIS 10新增ordered JSON和GDAL标签读取；最稳定的Python契约
  是把JSON转为标准`dict/list`并以路径字符串读取GDAL标签，而不是向
  Python泄漏`nlohmann::ordered_json`或递归引用out-param。
