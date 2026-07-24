# 进度记录：ISIS 10 新增能力审计、绑定与双版本发布

## 会话：2026-07-24

### Phase 1：自动差异清单与分类质量门

- 状态：in_progress
- 已确认用户发布门槛：先完成新增能力，再验证 Linux/Windows 的 ISIS 9/10，
  最后发布。
- 已重新比较 `asp360_new` 与旧 ASP `asp370`，曾确认 23 个新增头文件。
- 已识别当前人工候选机制会遗漏未显式列出的新增内容。
- 下一步：为生成器增加 prefix 自动差异输出和未分类失败测试。
- 首次运行发现测试类级 `setUp()` 会在 ISIS 9 上游镜像缺失时跳过所有测试；
  已将 skip 缩小到源码路径验证用例。
- 根据用户复核意见扩展 Phase 1：不再只做新增头文件名比较，增加删除项、
  同名 API 差异、弃用标记、Changelog、导出符号和 build provenance。
- 已确认官方 ISIS 10.0.0 Release/Changelog 存在；同时确认本机 ASP
  `asp_4` 构建包含官方 tag 中不存在的 ShadowCam 头文件。
- 已将版本扩展流程固化为 `docs/isis-version-expansion-policy.md`，并在
  `AGENTS.md` 与 `CLAUDE.md` 中加入强制入口和核心发布门槛。
- 用户决定删除 NASA ASP 预发布 `asp370`，改用 USGS 官方 ISIS 10 conda
  包重建同名环境；删除前先验证官方 channel/build 与安装命令。
- 已删除旧 `asp370`，重建为 USGS `isis 10.0.0 h1f94ec8_1`、Python
  3.13.14，并安装 pybind11、CMake、Ninja 与 conda GCC 13 工具链。
- 发现并修复官方包的开放式 `csm` 依赖漂移：固定 `csm 3.0.3.3` 后
  `campt -help` 正常启动。
- 正式 prefix 对比结果为新增 13 个 `.h/.hpp`、移除 `Endian.h`；清单已
  移除旧 ASP-only 的 ShadowCam、AspMapProjection 等候选。
- 用户要求将 Phase 1 扩展为系统 API 对比，明确重新核算此前“178 个变化
  文件”，并整理新增、删除、修改的类、方法、自由函数、枚举及导出符号。
- 已新增 `tools/dev/compare_isis_installations.py`，生成完整 header、core
  symbol、callable signature 三层 CSV 和自动 Markdown 汇总。
- 已生成中文系统报告 `docs/isis9-isis10-systematic-api-comparison.md`，
  合并正式包 provenance、Changelog、动态库导出和当前 PyISIS 影响范围。
- Phase 1 的 Linux 自动审计与文档已完成；剩余未关闭项是 Windows ISIS
  9/10 DLL/import-library 对比，Phase 1 因此继续保持 `in_progress`。
- 根据系统对比结果重新评估总体顺序：在继续增加 ISIS 10 能力前，插入
  “现有绑定兼容闭环”阶段。当前 381 个绑定依赖头文件中，328 个相同、
  48 个需复核、1 个兼容重命名、4 个 ISIS 10 独有。
- 已新增 `docs/isis9-isis10-binding-compatibility-plan.md`，明确公共绑定主体、
  局部适配、最小版本门和 Python API 归一化原则，并按 P0/P1/P2 整理队列。
- 已核对最新 GitHub Actions 发布矩阵：Linux ISIS 9/10 和 Windows ISIS 9
  均已成功；Windows ISIS 10 在 ISIS prefix 的 `mgs.dll` 链接阶段失败，
  尚未进入 PyISIS wheel 构建。
- 当前执行阶段更新为 Phase 2。Windows DLL/import-library 对比移动到
  Phase 4，待 Windows ISIS 10 prefix 可完整构建后再关闭。
- 用户要求把 Windows 行星摄影测量应用支持作为当前大计划完成后的工作。
  已新增 Phase 6，不改变当前 Phase 2–5 的执行顺序。
- 已从正式 ISIS 10 prefix 核对 366 个应用 XML、54 个 `*2isis` 导入入口，
  并确认 Windows 10 当前精简补丁排除应用实现是为规避 MSVC 单体导入库
  成员上限。未来方案确定为复用 USGS 源码、按应用独立构建。
- 已创建 `docs/windows-planetary-photogrammetry-app-roadmap.md`：
  系统列出45个任务/仪器导入、9个通用/辅助入口、任务检校与预处理、
  SPICE/投影/镶嵌、控制网、`jigsaw` 和 GUI 队列。
- 已将用户原始分层优化为 Wave 0–6：重新基线、三个端到端样板、全部任务
  导入、检校、控制网 CLI、`jigsaw`、GUI；明确 Linux 不逐 APP 重复绑定。
- 用户将当前执行范围重新锁定为 Phase 2–5，Phase 6 Windows APP 仅保留
  未来计划。已启动首批兼容队列：
  `Cube→CubeAttribute→Blob→Table→ProcessByBrick`。
- 当前目标 `Cube` 已完成头文件首轮对比，发现 ISIS 10 将
  `labelsAttached/setLabelsAttached` 从 `bool` 改为 `LabelAttachment`
  枚举，并新增 GTiff/GDAL状态；下一步运行双环境行为测试并做最小适配。
- `Cube`兼容闭环完成：双版本重新构建成功，ISIS 9/10各30项聚焦测试及
  smoke通过；四类旧绑定台账和新兼容审计CSV已同步。
- `CubeAttribute`兼容闭环完成：修复ISIS 9上游External字符串枚举转换
  缺陷，按版本暴露ISIS 10新增GdalLabel、GTiff和
  `propagate_file_format()`；双版本各7项聚焦测试及smoke通过。当前目标
  切换为`Blob`。
- `Blob`兼容闭环完成：共有文件/bytes接口保持共享；ISIS 10新增
  `key/start_byte`按版本暴露；GDAL裸指针和C++流接口明确排除。双版本
  各2项聚焦测试及smoke通过。当前目标切换为`Table`。
- `Table`兼容闭环完成：ISIS 10仅删除本就未导出的无参构造；补齐共享
  `Table(Blob)`与`to_blob()`往返，并校正严重滞后的方法台账。双版本各
  8项聚焦测试及smoke通过。当前目标切换为`ProcessByBrick`。
- `ProcessByBrick`兼容闭环完成：唯一差异为QtConcurrent内部
  `QFuture<void>`到`QFuture<void*>`，不影响公开绑定签名；校正真实绑定
  台账。双版本`process_unit_test`各6/6及smoke通过。首批5类全部关闭，
  下一队列从`Pvl`开始。
- `Pvl`兼容闭环完成：ISIS 10新增`to_json()`返回Python容器与
  `read_gdal(path)`；递归引用helper明确排除。双版本`PvlUnitTest`各
  17/17及smoke通过。当前目标切换为`PvlObject`。

## 测试与验证

| 时间 | 命令 | 结果 | 说明 |
|---|---|---|---|
| 2026-07-24 | conda include header basename diff | PASS | ISIS 10 比 ISIS 9 新增 23 个头文件。 |
| 2026-07-24 | official ISIS 10 conda create | PASS | `isis 10.0.0 h1f94ec8_1` from `usgs-astrogeology`, CPython 3.13.14。 |
| 2026-07-24 | `campt -help` after `csm=3.0.3.3` | PASS | ISIS 可执行程序与 `libcsmapi.so.3` 正常加载。 |
| 2026-07-24 | official prefix `.h/.hpp` diff | PASS | 新增 13，移除 1；ASP-only 项不进入正式候选。 |
| 2026-07-24 | inventory + wheel workflow unit tests | PASS | 15 tests passed，1 个上游源码树缺失用例按设计跳过。 |
| 2026-07-24 | installation comparison focused tests | PASS | 3 tests passed；覆盖 `.hpp`/声明/弃用/符号过滤。 |
| 2026-07-24 | official installed API comparison | PASS | 13 新增、1 删除、147 声明变化、18 非声明变化、185 callable 组变化。 |
| 2026-07-24 | comparison + API audit + inventory regression | PASS | 14 tests passed，1 个可选上游源码树用例按设计跳过；CSV 计数断言与 diff check 通过。 |
| 2026-07-24 | GitHub Actions wheels run `30066283510` | PARTIAL | Linux ISIS 9/10 与 Windows ISIS 9 成功；Windows ISIS 10 在 `mgs.dll` 链接 `SpiceQL::strSclkToEt` 时失败。 |
| 2026-07-24 | Windows APP roadmap 对正式 ISIS 10 XML 清单校验 | PASS | 任务/仪器导入45、通用/辅助入口9，合计54，与安装的全部 `*2isis` 一致；第5–7节77个应用名均有 XML。 |
| 2026-07-24 | `git diff --check` | PASS | 新增路线图与计划更新无空白错误；未改动或覆盖已有任务外工作。 |
| 2026-07-24 | ISIS 9/10 Cube rebuild + focused + smoke | PASS | 两套扩展均重建；`cube_unit_test`各30/30，smoke均通过。 |
| 2026-07-24 | ISIS 9/10 CubeAttribute rebuild + focused + smoke | PASS | 两套扩展均增量重建；CubeAttribute聚焦测试各7/7，smoke均通过。 |
| 2026-07-24 | ISIS 9/10 Blob rebuild + focused + smoke | PASS | 两套扩展均增量重建；Blob聚焦测试各2/2，smoke均通过。 |
| 2026-07-24 | ISIS 9/10 Table rebuild + focused + smoke | PASS | 两套扩展均增量重建；Table/TableRecord/TableField聚焦测试各8/8，smoke均通过。 |
| 2026-07-24 | ISIS 9/10 ProcessByBrick focused + smoke | PASS | `process_unit_test`双版本各6/6；头文件差异仅为内部QtConcurrent类型。 |
| 2026-07-24 | ISIS 9/10 Pvl rebuild + focused + smoke | PASS | 新增ISIS 10 JSON/GDAL表面；`PvlUnitTest`双版本各17/17，smoke均通过。 |
