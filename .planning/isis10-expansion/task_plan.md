# 任务计划：ISIS 10 新增能力审计、绑定与双版本发布

## 目标

完整审计 ISIS 10.0.0 相对 ISIS 9.0.0 新增的已安装公开 API，完成适合
Python 的非 GUI 绑定或明确排除理由，并在 Linux/Windows 上分别验证
ISIS 9.0.0 与 ISIS 10.0.0 后再发布两个版本。

## 当前阶段

Phase 2：现有绑定兼容闭环，状态：in_progress。

系统差异发现机制在 Linux 正式 prefix 上已经完成。Windows 导出符号对比
暂不能独立关闭，因为 ISIS 10 Windows prefix 仍在构建阶段失败；该项转入
Phase 4，与 Windows 10 移植一起验收，不再阻塞现有绑定兼容分析。

## 阶段

### Phase 1：自动差异清单与分类质量门

- [x] 自动比较 ISIS 9/10 conda prefix 中的新增、删除和同名变更头文件
- [x] 区分字节变化、去注释声明变化和实际导出符号变化
- [x] 输出完整双向原始差异台账及中文系统对比报告
- [x] 提取同名头文件中的类、方法、函数和枚举签名变化
- [x] 扫描 `@deprecated`、弃用宏及官方 Changelog 的 Deprecated/Removed/Breaking
- [ ] 核对 Linux `.so` 与 Windows `.dll/.lib` 的实际导出符号
  - [x] Linux `libisis` 与新增候选所在任务库
  - [ ] Windows ISIS 9/10 DLL/import library（移入 Phase 4；不阻塞 Phase 2）
- [x] 记录官方 tag 与实际 conda build 的来源和差异
- [x] 对每个新增头文件记录 class/function/constants/excluded 分类
- [x] 未分类新增头文件使验证失败
- [x] 补充 focused unit tests 与文档
- 状态：complete_for_linux；Windows 子项随 Phase 4 关闭

### Phase 2：现有绑定兼容闭环

- [x] 找出当前绑定引用的 381 个 ISIS 头文件
- [x] 分类为 328 个相同、48 个需复核、1 个重命名、4 个 ISIS 10 独有
- [x] 建立共享源码优先的兼容策略和分组队列
- [x] 首批队列：`Cube`（closed）→ `CubeAttribute`（closed）→
      `Blob`（closed）→ `Table`（closed）→ `ProcessByBrick`（closed）
- [ ] 下一队列：`Pvl` → `PvlObject` → `PvlKeyword` → `PvlContainer`；
      `Pvl`（closed）；当前目标：`PvlObject`
- [ ] 对 48 个头文件逐项映射“绑定实际使用签名”与 ISIS 9/10 声明
- [ ] 优先关闭 Cube/PVL、Control/Bundle、Shape、Camera/Spice 和
      OSIRIS-REx 高风险组
- [ ] 对 Python 可见容器统一返回稳定类型，Qt 容器差异在 C++ 边界转换
- [ ] 只有无法用公共表达式兼容的差异才增加局部能力宏
- [ ] 在 ISIS 9 与 ISIS 10 正式环境分别编译、导入并运行对应聚焦测试
- 状态：in_progress

### Phase 3：ISIS 10 新增类和函数审计与绑定

- [x] 以 USGS `h1f94ec8_1` 的 13 个新增头文件为正式候选基线
- [x] 分类出 6 个公开类、3 个应用函数和 4 个排除项
- [x] 已实现 IProj、Chandrayaan2OhrcCamera、Chandrayaan2TmcCamera
- [ ] 用正式 `asp370` 重建并复核上述 3 个现有 ISIS 10 绑定
- [ ] 审计并实现 OsirisRexOcamsOpenCVDistortionMap
- [ ] 评估 GdalIoHandler/ImageIoHandler 是否应直接绑定或提供更稳定 facade
- [ ] 为 csv2table、eisstitch、ocams2isis 设计 Python-friendly facade
- [ ] 为每个不适合绑定的内容记录可审计排除理由
- [ ] 添加 ISIS 9 不导出、ISIS 10 导出的版本门测试
- [ ] 同步 inventory、详情 CSV 和进度日志
- 状态：partially_complete；等待 Phase 2 高风险兼容组关闭后继续

### Phase 4：双版本、双平台发布验证

- [x] Linux ISIS 9 wheel 构建与 Ubuntu 22.04/24.04 干净安装
- [x] Linux ISIS 10 wheel 构建与 Ubuntu 22.04/24.04 干净安装
- [x] Windows ISIS 9 prefix、wheel、安装和元数据验证
- [ ] Windows ISIS 10 prefix、wheel、安装和元数据验证
  - 当前阻塞：链接 `mgs.dll` 时，`MocLabels.cpp.obj` 无法解析
    `SpiceQL::strSclkToEt(...)`
- [ ] Windows ISIS 9/10 DLL/import-library 导出符号对比
- [ ] 验证 Release 资产命名、安装说明和版本对应关系
- 状态：partially_complete；Windows ISIS 10 是当前平台阻塞项

### Phase 5：正式发布

- [ ] 仅在四条发布链全部通过后创建正式 Release
- [ ] 发布 ISIS 9 与 ISIS 10 对应资产及校验信息
- 状态：pending

### Phase 6：Windows 行星摄影测量应用扩展

- [x] 以正式 ISIS 10 prefix 的应用 XML 建立任务导入、校正、SPICE、
      控制网和 GUI/重型应用基线
- [x] 确定不重写 USGS 科学算法，采用独立应用目标和可选 Python facade
- [x] 形成 `docs/windows-planetary-photogrammetry-app-roadmap.md`
      开发需求与分阶段计划
- [ ] 当前 Phase 1–5 完成后，重新核对届时 ISIS 9/10 正式 prefix
- [ ] 按 P0/P1/P2/P3 队列逐批移植、打包和真实数据验收
- 状态：planned_after_release；不阻塞当前双版本绑定 Release

## 决策记录

| 决策 | 原因 |
|---|---|
| “全部新增功能”指完整审计后的公开、可链接、适合 Python、非 GUI API | 不把测试 fixture、第三方内部实现和空占位强行作为公共 API。 |
| conda prefix 是编译面最终依据 | 与仓库 AGENTS.md 和 scoped instructions 一致。 |
| 原始发现层与人工推荐层分离 | 防止人工候选列表遗漏新增头文件。 |
| 官方 Changelog 是发现线索而不是 API 真值 | 它记录用户可见变化，但不是完整的类/方法/导出符号清单。 |
| 正式绑定只以 USGS conda build 为目标 | 已删除 ASP `asp_4` 环境；ASP-only 头文件仅保留历史差异记录。 |
| 四条发布链通过后再正式发布 | 避免 ISIS 版本或平台资产不完整。 |
| 不按 ISIS 主版本复制整套 `src/` | 共享绑定主体可避免两个版本长期漂移。 |
| 先关闭现有绑定兼容，再继续新增绑定 | 新增 API 建立在稳定的双版本公共底座上，减少返工。 |
| Python API 优先稳定，Qt5/Qt6 容器在 C++ 边界归一化 | 避免把 `QVector/QList`、`QPair/std::pair` 的实现差异泄漏给用户。 |
| Windows 符号审计随 Windows 10 prefix 移植关闭 | 当前尚无可完整链接的 ISIS 10 Windows prefix，无法给出可靠双向 ABI 结果。 |
| Windows APP 扩展放在当前双版本 Release 之后 | 先稳定核心绑定和四条发布线，避免应用移植扩大当前阻塞面。 |
| Windows APP 复用 USGS 源码并按应用独立构建 | 不重写科学算法，也不恢复会超过 MSVC import-library 成员上限的单体 DLL。 |
| Linux 不为既有 CLI 重复提供 pybind facade | Linux 官方 ISIS 已直接提供应用；只维护跨平台 Python API 确有价值的少量例外。 |

## 错误记录

| 错误 | 尝试次数 | 解决 |
|---|---:|---|
| `setUp()` 因 ISIS 9 上游镜像缺失跳过了整个 inventory 测试类 | 1 | 将 skip 缩小到唯一依赖双源码树的测试，使 prefix/生成器测试始终运行。 |
| 官方包查询命令因包含 `rm -f` 临时文件清理而被安全策略拒绝 | 1 | 改为管道内解析，不创建或删除临时文件。 |
| USGS channel 不提供 `current_repodata.json`，低内存 dry-run 返回 HTTP 404 | 1 | 保持官方 channel 顺序与 strict priority，改用完整 `repodata.json`。 |
| 首次环境创建在后台下载且磁盘降至约 5 GB | 1 | 中断事务并清理可下载缓存，改为运行环境与开发工具链两阶段安装。 |
| 最新 `csm 3.1.0` 缠绕解析后缺少 ISIS 所需的 `libcsmapi.so.3` | 1 | 固定 `csm 3.0.3.3`，`campt -help` 恢复正常。 |
| 本机 `conda env create --dry-run` 继承全部全局 channel，长时间求解后被终止 | 1 | 不把本机全局配置作为 CI 证明；用已成功创建的精确环境、运行测试及环境文件 pin 验收。 |
| 声明提取器将 `enum class` 名误计为普通 class | 1 | 先提取 enum，再从 class 名集合中排除 enum 名；增加 focused regression test。 |
| 类内首个方法的声明指纹带入 `public:` 访问标签 | 1 | 在声明归一化时移除开头访问标签，使方法签名跨布局稳定。 |
| Deprecated 扫描只接受分号声明，漏掉 inline 函数定义 | 1 | 同时接受 `;` 和 `{`，并增加 inline deprecated regression test。 |
| 临时 importlib 调试脚本未把动态模块放入 `sys.modules`，触发 dataclass 导入错误 | 1 | 不属于工具入口问题；后续调试复用单元测试中的正确加载模式。 |
| 搜索命令包含不存在的 `cmake` 路径 | 1 | 后续仅搜索已存在目录，或先检查目录存在性。 |
| Windows ISIS 10 在链接 `mgs.dll` 时无法解析 `SpiceQL::strSclkToEt(...)` | 1 | 已确认发生在 ISIS prefix 构建阶段，不是 PyISIS 绑定编译错误；Phase 4 先修复 SpiceQL 的 Windows 导出/链接一致性。 |
| 首次 ISIS 10 Cube 测试继承了 shell 中的 ISIS 9 `ISISROOT/ISIS_PREFIX` | 1 | 版本保护按设计拒绝混用；后续双版本测试显式同时设置 conda env、`ISISROOT`、`ISIS_PREFIX`、`PYTHONPATH`。 |
| ISIS 10 `Cube.set_labels_attached(False)` 因参数改为 `LabelAttachment` 而抛出 `TypeError` | 1 | 保持 Python `bool` 契约，在绑定边界映射 Attached/Detached，并增加精确枚举接口和双版本测试。 |
| Cube台账批量补丁因进度日志上下文不匹配而整体未应用 | 1 | 确认无半写状态后改为小块、逐文件更新。 |
| CubeAttribute批量补丁因测试文件日期上下文不匹配而整体未应用 | 1 | 读取文件真实元数据后，继续采用逐文件小补丁。 |
| `conda run ... python -`未转发here-doc标准输入，CubeAttribute探测无输出 | 1 | 改用`python -c`传入只读探测代码。 |
| Blob ISIS 10测试最初假定`Key()`为`BlobUnitTest` | 1 | 以正式ISIS 10运行结果修正为上游真实格式`Blob_UnitTest`。 |
