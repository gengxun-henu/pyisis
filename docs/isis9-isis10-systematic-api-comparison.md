# ISIS 9.0.0 与 ISIS 10.0.0 系统 API/ABI 对比

> 更新日期：2026-07-24  
> 对比对象：Linux x86_64 正式 conda prefix，而不是旧 NASA ASP `asp_4`
> 预发布环境。

## 1. 对比基线

| 项目 | ISIS 9 | ISIS 10 |
|---|---|---|
| conda 环境 | `asp360_new` | `asp370` |
| conda 包 | `isis 9.0.0 h1f94ec8_0` | `isis 10.0.0 h1f94ec8_1` |
| channel | `usgs-astrogeology` | `usgs-astrogeology` |
| Python ABI | CPython 3.12 | CPython 3.13 |
| 核心库 | `libisis9.0.0.so` | `libisis10.0.0.so` |
| 头文件数 | 1163 | 1175 |

ISIS 10 环境固定 `csm 3.0.3.3`。不受约束的 `csm 3.1.0` 缺少
ISIS 10 二进制所需的 `libcsmapi.so.3` 链接名。

## 2. 为什么原来的“178 个文件变化”需要重算

原来的 178 是旧 ASP `asp_4` prefix 中同名头文件的字节级变化数。它有两个
限制：

1. ASP build 包含 ShadowCam、AspMapProjection 等 USGS 正式包没有的内容；
2. 文件字节变化可能只是注释、格式、include 或 inline 实现变化，不等于
   类、函数或 ABI 一定发生变化。

基于当前 USGS 正式包重新计算：

| 文件级结果 | 数量 |
|---|---:|
| ISIS 10 新增头文件 | 13 |
| ISIS 10 删除头文件 | 1 |
| 同名且字节完全一致 | 997 |
| 同名且公开声明指纹变化 | 147 |
| 同名但只有非声明文本变化 | 18 |
| 同名头文件字节变化合计 | 165 |

因此当前正式基线应使用 **165**，不是 178。其中真正进入声明复核队列的是
147 个，另外 18 个不应自动解释为公共 API 变化。

## 3. 新增内容

### 3.1 新增头文件的完整分类

| 头文件 | 主要内容 | 分类 | 当前处理 |
|---|---|---|---|
| `IProj.h` | `IProj` | 公共投影类 | 已绑定 |
| `Chandrayaan2OhrcCamera.h` | `Chandrayaan2OhrcCamera` | 任务相机类 | 已绑定 |
| `Chandrayaan2TmcCamera.h` | `Chandrayaan2TmcCamera` | 任务相机类 | 已绑定 |
| `OsirisRexOcamsOpenCVDistortionMap.h` | OCAMS OpenCV 畸变模型 | 公共任务类 | 已绑定 |
| `GdalIoHandler.h` | GDAL Cube I/O 后端 | 公共底层类 | 已绑定 Python facade |
| `ImageIoHandler.h` | 图像 I/O 抽象基类 | 公共抽象类 | 已注册安全共享接口 |
| `csv2table.h` | `csv2table` | 应用函数 | 待设计 `UserInterface` facade |
| `eisstitch.h` | `eisstitch` | Europa Clipper 应用函数 | 待绑定 |
| `ocams2isis.h` | `ocams2isis` | OSIRIS-REx 应用函数 | 待绑定 |
| `DskSegmentBuffer.hpp` | DSK mesh buffer | 明确标记 `@internal` | 排除公共绑定 |
| `IEndian.h` | 原 `Endian.h` 内容 | 重命名兼容 | 复用现有 ByteOrder 绑定 |
| `RestfulSpice.h` | 全部内容被注释 | 占位头 | 排除 |
| `restincurl.h` | RESTinCurl 实现类型 | 第三方内部实现 | 排除 |

### 3.2 动态库导出验证

新增公共候选均已在正式 ISIS 10 Linux 库中找到实际导出：

| API | 已验证动态库 |
|---|---|
| `IProj` | `libisis10.0.0.so` |
| `GdalIoHandler` | `libisis10.0.0.so` |
| `ImageIoHandler` | `libisis10.0.0.so` |
| `Chandrayaan2OhrcCamera` | `libChandrayaan2OhrcCamera.so`、`libchandrayaan2.so` |
| `Chandrayaan2TmcCamera` | `libChandrayaan2TmcCamera.so`、`libchandrayaan2.so` |
| `OsirisRexOcamsOpenCVDistortionMap` | `libOsirisRexOcamsCamera.so`、`libosirisrex.so` |
| `csv2table` | `libisis10.0.0.so` |
| `eisstitch` | `libclipper.so` |
| `ocams2isis` | `libosirisrex.so` |

### 3.3 当前 Python 导出面的实际差异

2026-07-24 使用 `asp360_new` 和 `asp370` 的实际 `_isis_core` 运行时快照
对比，而不是从 C++ 头文件数量推断：

- ISIS 10 新增 6 个 Python 类：
  `IProj`、`Chandrayaan2OhrcCamera`、`Chandrayaan2TmcCamera`、
  `OsirisRexOcamsOpenCVDistortionMap`、`ImageIoHandler` 和
  `GdalIoHandler`。
- 这 6 个类当前包含 30 个已绑定构造/方法入口；连同 6 个类符号，候选
  detail 台账共有 36 个已完成条目。
- 既有类新增 15 个可调用入口：`Blob` 2 个、`CubeAttributeOutput` 1 个、
  `PvlKeyword` 5 个、`PvlContainer` 1 个构造入口、`Pvl` 2 个、
  `Environment` 1 个、`UniversalGroundMap` 3 个。
- 新增 2 个枚举值：`LabelAttachment.GdalLabel` 和 `Cube.Format.GTiff`。
- `OsirisRexDistortionMap.set_distortion()`有 1 处版本化签名/返回值变化：
  ISIS 10 的 filter 可省略且返回 `bool`，ISIS 9 保持必填 filter 和
  `None` 返回。
- ISIS 10 没有从当前 ISIS 9 Python 顶层导出面删除类，也没有删除既有类
  的 Python 方法。

因此按 Python 用户实际可调用的口径，当前为 **6 个新增类、45 个新增
构造/方法入口、2 个新增枚举值、1 个变更方法**。`csv2table`、
`eisstitch` 和 `ocams2isis` 是已发现但按当前范围尚未绑定的应用函数，
不计入已发布 Python API。

## 4. 删除、重命名和过时内容

### 4.1 头文件层

- 唯一消失的头文件是 `Endian.h`。
- ISIS 10 新增的 `IEndian.h` 保留对应 ByteOrder 枚举和 endian helpers，
  所以这是重命名兼容，不是功能整体删除。
- 机械比较没有发现一个“头文件主类”在 ISIS 10 中整体删除。
- `IsLittleEndian()`、`IsBigEndian()` 等旧 helper 本身已有 deprecated 标记，
  Python 侧继续优先保留稳定的 ByteOrder/`IsLsb`/`IsMsb` 接口。

### 4.2 官方 Changelog 明确删除项

ISIS 10.0.0 Changelog 的 Removed 部分只明确列出：Qt 6 不再提供 MySQL
支持，因此 `isisminer` 不再支持 MySQL。这属于应用/依赖能力变化，不是当前
非 GUI pybind 核心绑定的直接删除项。

### 4.3 为什么核心库有大量“移除符号”

`libisis` 的完整 demangled 集合为：

| 项目 | 数量 |
|---|---:|
| ISIS 9 导出 | 16878 |
| ISIS 10 导出 | 16406 |
| 保持不变 | 16123 |
| 新增 | 283 |
| 移除 | 755 |

755 个移除导出不能直接解释为 755 个公共函数被删除。这里包含：

- Qt 5 → Qt 6 容器类型变化造成的旧签名消失；
- Protobuf 生成代码变化；
- 构造/析构、typeinfo、vtable 和 thunk；
- 私有实现或非绑定目标；
- 同一函数旧重载消失、对应新重载增加。

完整逐符号集合见
`reference/compatibility/isis9-isis10-core-symbol-diff.csv`。

## 5. 修改内容

### 5.1 主要 ABI 迁移模式

185 组同名 callable 的导出签名集合发生变化，其中 177 组是类方法，8 组是
自由函数。主要模式为：

| 变化模式 | 同名 callable 组数 | 影响 |
|---|---:|---|
| `QVector<T>` → `QList<T>` | 40 | 容器转换、返回值与参数 wrapper 需复核 |
| `QPair<A,B>` → `std::pair<A,B>` | 66 | Python tuple/pair 适配需按版本处理 |
| Protobuf `MergeImpl` 变化 | 21 | 主要是生成代码 ABI，不建议直接绑定 |
| `QStringRef` 相关移除 | 1 | Qt 6 字符串接口迁移 |

这与官方 Changelog 中“Qt 更新到 6.x”一致，但 Changelog 没有逐项列出所有
C++ 签名变化，因此仍必须依赖安装头文件和导出符号。

### 5.2 同名自由函数变化

下列 8 组自由函数存在重载或参数集合变化：

- `ExtractLatLonRange`
- `ExtractPointList`
- `WriteResults`
- `getCameraPointInfo`
- `getProjPointInfo`
- `operator<<`
- `operator>>`
- `toString`

典型变化包括 `QVector<QString>→QList<QString>`、
`QPair<double,double>→std::pair<double,double>`，以及 Qt 6 移除
`QStringRef` 后的流运算符变化。

### 5.3 类级变化

- 127 个同名头文件的“主类”存在机械声明变化；
- 129 个类在 `libisis` 中至少有一组同名方法的导出签名集合变化；
- 二者并非完全相同：inline/template/default argument 只会出现在头文件层，
  typeinfo/thunk/私有实现则可能只出现在库符号层。

完整类名和逐方法签名不在本文件重复展开，分别见：

- `reference/compatibility/isis9-isis10-installed-api-comparison.md`
- `reference/compatibility/isis9-isis10-installed-header-diff.csv`
- `reference/compatibility/isis9-isis10-core-callable-changes.csv`

## 6. 对当前 PyISIS 绑定的直接影响

当前绑定源码引用了 384 个唯一 ISIS 头文件：

| 当前绑定头文件状态 | 数量 |
|---|---:|
| ISIS 9/10 文本一致 | 328 |
| 需要人工 API 复核 | 48 |
| 已识别重命名 | 1 |
| ISIS 9 缺失、ISIS 10 新增 | 7 |
| ISIS 10 缺失 | 0 |

其中 7 个 ISIS 9 缺失项是 6 个 ISIS 10 专属类头和条件包含的
`IEndian.h`。当前没有发现“绑定源码引用的头文件在 ISIS 10 中完全无替代地
消失”，这是双版本共用一套 binding 源码的重要正面结果。

48 个重点复核头文件主要集中在：

- `Cube`、`CubeAttribute`、`Blob`、`Table` 和 I/O；
- `Pvl`、`PvlObject`、`PvlKeyword`、`PvlContainer`；
- `ControlNet`、`ControlPoint`、`ControlMeasure`、Bundle 类；
- ShapeModel、Bullet/Embree/DSK shape 类；
- CameraFocalPlaneMap、CameraFactory、Spice/SpiceRotation；
- OSIRIS-REx 相机与畸变模型；
- Calculator/CubeCalculator 和 Qt 容器接口。

逐 binding 文件影响见当前 conda 安装面报告
`reference/compatibility/isis9-isis10-conda-report.md`、矩阵
`reference/compatibility/isis9-isis10-conda-header-matrix.csv`和人工闭环
台账`reference/compatibility/isis9-isis10-binding-review.csv`。当前风险
集合为57个唯一头文件，已关闭57个，剩余0个。

## 7. 官方 Changelog 与机械审计的对应关系

官方 ISIS 10.0.0 Changelog 可确认：

- 新增 `IProj` 与 PROJ；
- 新增 Chandrayaan-2 TMC/OHRC 相机支持；
- 新增 `eisstitch`；
- 新增 GeoTIFF 读写和 GDAL SRS 传播；
- PVL 改为从 GDAL metadata 读取；
- 引入 SpiceQL，替代部分直接 CSPICE 调用；
- GDAL 更新到 3.12、Qt 更新到 6.x；
- OSIRIS-REx OCAMS 支持更新；
- `isisminer` 移除 MySQL 支持。

Changelog 用于解释“为什么变化”，安装 prefix 用于确认“实际可编译和可链接
的 API 是什么”。两者不能互相替代。

## 8. 后续绑定与兼容工作顺序

1. 当前绑定引用的57个conda风险头文件已全部关闭，继续保持人工台账与
   prefix矩阵同步。
2. 6个ISIS 10专属类已在正式USGS ISIS 10环境完成编译、导入和聚焦测试。
3. `csv2table`、`eisstitch`、`ocams2isis`按既定范围留待后续APP facade
   工作，不阻塞本轮核心绑定发布。
4. 下一门槛是运行Linux/Windows × ISIS 9/10四条wheel构建和干净安装；
   Windows结果必须来自真实DLL/import library，不能用Linux `.so`替代。
5. 四条流水线全部通过后，再分别创建ISIS 9和ISIS 10 GitHub prerelease。

## 9. 重新生成

```bash
python tools/dev/compare_isis_installations.py \
  --isis9-prefix /home/gengxun/miniconda3/envs/asp360_new \
  --isis10-prefix /home/gengxun/miniconda3/envs/asp370 \
  --isis9-label "USGS ISIS 9.0.0 h1f94ec8_0 (linux-64, CPython 3.12)" \
  --isis10-label "USGS ISIS 10.0.0 h1f94ec8_1 (linux-64, CPython 3.13)"
```

自动比较是筛选器，不是最终绑定决策器。准备绑定具体类或方法时，仍需同时
检查目标头文件、对应 `.so` 导出、上游实现、生命周期、Qt/容器转换和 focused
测试。
