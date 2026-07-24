# Windows ISIS 行星摄影测量 APP 开发需求与路线图

> 状态：future / planned-after-release  
> 基线：USGS ISIS 10.0.0 `h1f94ec8_1`，`asp370` 正式 conda prefix  
> 执行时机：完成当前 ISIS 9/10 绑定兼容、四平台发布链和正式 Release 之后

## 1. 定位

该阶段的目标不是把 ISIS 应用算法重写为 Python，也不是一次性把全部 ISIS
应用移植到 Windows。目标是复用 USGS 源码，为 Windows 提供行星摄影测量
常用的原生命令行 APP，并在确有跨平台 Python 使用价值时增加轻量 facade。

Linux 官方 ISIS 环境已经直接提供这些命令，因此不逐个增加 pybind 绑定。
Linux 和 Windows 可共同提供一个可选的通用 `pyisis.apps.run()` 启动接口，
但它只负责参数、环境、日志和异常处理，不复制应用算法。

## 2. 对原始需求的调整

用户提出的总体顺序是合理的：

1. PDS/任务数据导入 ISIS Cube；
2. 辐射检校、噪声和仪器效应校正；
3. SPICE、几何和投影；
4. 控制网生成、编辑和自动量测；
5. bundle adjustment、GUI 和重型工具。

需要做三项调整：

- `jigsaw` 是命令行 bundle adjustment，不是 Qt GUI。它仍放在后期，但原因
  是依赖范围、计算资源和真实控制网验收成本较高。
- `qnet`、`qview`、`qmos` 才是 Qt GUI，应单独打包并作为最后阶段，不阻塞
  命令行摄影测量工作流。
- `*2isis` 不全是任务影像导入。正式 ISIS 10 中54个此类应用包含45个
  任务/仪器入口和9个通用格式、旧格式或 DSK 入口，开发清单必须分开维护。

## 3. 强制工程原则

1. 不重写 `spiceinit`、任务导入、辐射检校和控制网科学算法。
2. 应用实现以对应 ISIS tag/source 和安装 XML 为真值。
3. 不把所有 APP 合入一个 export-all DLL。当前 ISIS 10 Windows 精简的直接
   原因就是单体 import library 超过 MSVC 的65,535成员限制。
4. 每个 APP 使用独立 executable target，或使用可控的小型 object/static
   target 后链接公共 ISIS runtime。
5. 构建由显式 allowlist 驱动，不默认扫描并启用全部 `apps/`。
6. APP 必须同时安装 `.exe`、XML、模板、插件和必要 runtime DLL；完整
   ISISDATA/任务数据不塞入 wheel。
7. ISIS 9 与 ISIS 10 共用 manifest schema 和构建框架，允许按版本声明
   `supported`、`experimental`、`unavailable`。
8. Python facade 不是 APP 可用性的前提；Windows 原生命令能够稳定运行是
   第一验收门。

## 4. 正式 ISIS 10 导入应用基线

### 4.1 任务与仪器导入：45个

| 任务/系列 | APP |
|---|---|
| Apollo | `apollo2isis` |
| Hayabusa | `amica2isis`、`nirs2isis` |
| Hayabusa2 | `hyb2onc2isis` |
| OSIRIS-REx | `ocams2isis`、`tagcams2isis` |
| Rosetta | `rososiris2isis`、`rosvirtis2isis` |
| NEAR | `msi2isis` |
| Dawn | `dawnfc2isis`、`dawnvir2isis` |
| Galileo | `gllssi2isis`、`gllnims2isis` |
| Cassini | `ciss2isis`、`vims2isis` |
| Voyager | `voy2isis` |
| New Horizons | `lorri2isis`、`leisa2isis`、`mvic2isis` |
| Juno | `junocam2isis` |
| Europa Clipper | `eis2isis` |
| MESSENGER | `mdis2isis` |
| Lunar Reconnaissance Orbiter | `lronac2isis`、`lrowac2isis`、`lrolola2isis`、`mrf2isis` |
| Chandrayaan-1 | `chan1m32isis`、`mrf2isis` |
| Kaguya/SELENE | `kaguyami2isis`、`kaguyatc2isis`、`mimap2isis`、`kaguyasp2isis` |
| Clementine | `clem2isis` |
| Lunar Orbiter | `lo2isis` |
| Mars Express | `hrsc2isis` |
| Mars Reconnaissance Orbiter | `hi2isis`、`hirdr2isis`、`mroctx2isis`、`marci2isis`、`crism2isis` |
| Mars Global Surveyor | `moc2isis` |
| Mars Odyssey | `thm2isis` |
| Mars Exploration Rover | `mer2isis` |
| Viking | `vik2isis` |
| Mariner 10 | `mar102isis` |
| ExoMars TGO | `tgocassis2isis` |

`kaguyasp2isis` 在正式 XML 中标记 deprecated，保留在兼容清单，但默认不进入
第一批新发布；优先推荐官方替代数据路径。

### 4.2 通用、旧格式和辅助入口：9个

| 类型 | APP |
|---|---|
| PDS/ISIS2 | `pds2isis`、`rolo2isis` |
| FITS/VICAR | `fits2isis`、`vicar2isis` |
| RAW/ASCII/DDD | `raw2isis`、`ascii2isis`、`ddd2isis` |
| 常见图像格式 | `std2isis` |
| NAIF DSK | `dsk2isis` |

这些入口有助于通用数据接入，但 `dsk2isis` 属于形状模型处理，应与普通相机
影像导入分别测试。

## 5. 辐射检校和任务预处理基线

| 任务/仪器 | 优先 APP |
|---|---|
| Hayabusa AMICA | `amicacal` |
| Hayabusa2 ONC | `hyb2onccal` |
| Apollo 15 Metric | `apollocal` |
| Cassini ISS/VIMS | `cisscal`、`vimscal` |
| Clementine | `clemhirescal`、`clemnircal`、`clemuvviscal`、`clemnirclean`、`clemnirnoise` |
| Galileo SSI | `gllssical` |
| MRO CTX | `ctxcal` |
| MRO HiRISE | `hical`、`hicalproc`、`hidestripe`、`hinoise`、`higlob`、`histitch` |
| MRO MARCI | `marcical` |
| LRO NAC | `lronaccal`、`lronacecho` |
| LRO WAC | `lrowaccal` |
| Mariner 10 | `mar10cal`、`mar10clean`、`mar10nonoise`、`mar10restore` |
| MESSENGER MDIS | `mdiscal`、`mdisproc` |
| MER MI | `mical` |
| MGS MOC | `moccal`、`mocnoise50`、`mocproc` |
| Mars Odyssey THEMIS | `thmproc`、`thmdriftcor`、`thmvisflat` |
| Viking | `vikcal`、`vikclean` |
| Voyager | `voycal`、`voyramp` |

没有独立 `*cal` 的任务不能自动判定为“缺失”。部分导入程序接受已校正产品，
部分校正步骤包含在任务 pipeline 中，也可能由数据生产方完成。实施时需为
每个任务记录输入产品级别、推荐处理链和所需 calibration ISISDATA。

## 6. SPICE、几何、投影与镶嵌

### P0：基础几何

- `spiceinit`
- `campt`
- `camrange`
- `camstats`
- `caminfo`
- `footprintinit`

`spiceinit` 是最高优先级。验收必须区分本地 kernel 模式和需要网络的
`web=true` 模式；CI 不能只依赖外部网络。

### P1：投影和常用影像操作

- `cam2map`、`cam2cam`
- `maptemplate`、`map2map`、`maptrim`
- `crop`、`reduce`、`enlarge`
- `automos`、`mapmos`、`noseam`
- `isis2std`、`cubeit`、`fx`

### P2：姿态和高级 SPICE

- `spicefit`
- `spkwriter`
- 其他 kernel/pointing 工具在真实需求和数据测试具备后加入 allowlist

## 7. 控制网 APP 队列

### P1：控制网构建主链

- `seedgrid`
- `footprintinit`
- `findimageoverlaps`
- `autoseed`
- `cnetadd`
- `cnetref`
- `pointreg`

其中 `seedgrid` 直接按经纬度范围生成控制网；影像重叠驱动的典型链路是：

```text
footprintinit
  → findimageoverlaps
  → autoseed
  → cnetref
  → pointreg
```

`cnetadd` 用于向已有控制网加入 Level 1/2 影像，不是上述新建链的必经步骤。

### P2：控制网质量和维护

- `cnetcheck`
- `cnetedit`
- `cnetextract`
- `cnetmerge`
- `cnetstats`
- `cnetthinner`

### P3：重型求解

- `jigsaw`

`jigsaw` 保持命令行应用，不要求 Qt GUI。它独立验收线程、内存、求解器依赖、
日志、输出 kernel/控制网，以及 Windows 与 Linux 数值结果的容差一致性。

### P4：GUI，最后处理

- `qnet`
- `qview`
- `qmos`

GUI 包不得成为 core、任务导入、检校、控制网 CLI 或 `jigsaw` 的依赖。

## 8. 建议发布组件

| 组件 | 内容 | 是否默认 |
|---|---|---|
| `core` | 当前 ISIS runtime、PyISIS、基础 DLL/插件 | 是 |
| `apps-ingest` | 任务导入和通用导入 APP | 是 |
| `apps-calibration` | 辐射检校、去噪和任务 pipeline | 是 |
| `apps-photogrammetry` | SPICE、投影、镶嵌和控制网 CLI | 是 |
| `apps-bundle` | `jigsaw` 及其额外求解依赖 | 可选 |
| `apps-gui` | `qnet/qview/qmos` 和 Qt GUI runtime | 可选，最后发布 |

GitHub Release 可同时提供组合安装包和分组件压缩包。wheel 继续承载 Python
绑定，不应把全部 APP、模板和任务数据无边界塞入 wheel。

## 9. Python 调用策略

优先级如下：

1. 原生 APP `.exe` 可从已激活环境直接运行；
2. 提供跨平台通用启动器，例如
   `pyisis.apps.run("spiceinit", from_="a.cub")`；
3. 仅对高频且具有稳定 C++ 入口的应用提供具名 facade；
4. 没有公共 C++ header 的应用通过子进程调用，不为绑定而复制实现。

Linux不逐个新增应用绑定。通用启动器如果实现，应在 Linux 调用官方原生命令，
在 Windows 调用随 runtime 发布的对应 `.exe`，保持调用语义一致。

## 10. 分阶段实施

### Wave 0：当前大计划完成后的重新基线

- 冻结当时正式 ISIS 9/10 tag、prefix 和应用 XML 清单。
- 生成 `windows-app-manifest`，字段至少包括版本、模块、源码目录、header、
  XML、runtime/data依赖、构建状态、测试数据和发布组件。
- 对比 ISIS 9/10 APP 新增、删除、deprecated 和参数变化。

### Wave 1：构建框架与三个端到端样板

- 建立 allowlist 驱动的 per-app target。
- 样板链1：`lronac2isis → spiceinit → lronaccal → lronacecho`。
- 样板链2：`hrsc2isis → spiceinit → campt/cam2map`。
- 样板链3：`pds2isis/fits2isis → Cube读取 → isis2std`。
- 验证安装规则不会重新触发单体 import-library 上限。

### Wave 2：全部任务导入

- 按第4节完成45个任务/仪器入口。
- 完成9个通用/辅助入口，deprecated 项允许标记为兼容可选。
- 每个 APP 至少通过 `-help/XML`、进程启动、最小输入和输出 Cube 可读检查。

### Wave 3：检校与标准任务处理链

- 按第5节逐任务加入检校、去噪、条带和拼接工具。
- 每个任务至少有一条真实或公开小样本端到端链。
- 记录并验证 calibration ISISDATA，不把完整数据包混入程序安装包。

### Wave 4：摄影测量和控制网 CLI

- 完成第6、7节 P0–P2。
- 使用多景真实 Cube 验证 footprint、overlap、seed、reference 和 registration。
- 比较 Windows/Linux 输出的关键标签、点数、量测数和统计量。

### Wave 5：`jigsaw`

- 单独解决求解器、线程、内存和数值一致性。
- 先用小控制网 smoke，再运行中等规模回归。

### Wave 6：GUI

- 独立移植 `qnet/qview/qmos`。
- 验证 Qt plugin、OpenGL/显示、字体、路径和高 DPI。
- GUI 失败不影响前五个 Wave 的稳定发布。

## 11. 验收标准

每个 APP 的状态不能只依据“编译成功”，至少需要：

1. `.exe`、XML和依赖文件安装完整；
2. `-help`/参数解析工作；
3. Windows干净环境可启动；
4. 最小输入产生可由 ISIS/PyISIS 读取的输出；
5. 异常退出码和日志可诊断；
6. 真实任务样本验证数据路径；
7. 与对应 Linux ISIS 版本比较关键标签和数值，允许有记录的浮点容差；
8. 不依赖开发机残留 DLL、源码树或构建目录；
9. 构建完成后清理临时对象和中间目录，只保留发布 prefix、日志摘要和产物。

正式支持的定义是“完整处理链通过”，不是“程序名称出现在安装目录中”。

## 12. 非目标

- 不重写 USGS算法。
- 不承诺首次迭代覆盖全部366个 ISIS应用。
- 不把完整 ISISDATA、SPICE kernel或任务 calibration 数据塞入 wheel。
- 不让 GUI成为非 GUI pipeline的发布阻塞项。
- 不因 Windows 需要 APP 就在 Linux 重复维护数百个 pybind facade。
