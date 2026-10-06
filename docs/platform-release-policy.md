# PyISIS 平台与 Runner 发布规则

本文件是 ISIS 9.0.0 / ISIS 10.0.0 跨平台发布的执行规则。它定义发布目标、运行环境、Runner 选择和证据要求。`docs/platform-support.md` 提供面向用户的平台摘要；本文件提供 CI 和发布门禁。

## 发布目标

每个版本线都必须分别验证并记录以下产品面：

| 产品面 | 目标平台 | 发布物 | 必须验证的行为 |
| --- | --- | --- | --- |
| PyISIS | Ubuntu 22.04、24.04、26.04 x86_64 | 对应 ISIS 9/10 的 Linux wheelhouse | 安装、导入、ABI、聚焦单元测试和运行时闭包 |
| PyISIS | Windows 11 x64 | 对应 ISIS 9/10 的 Windows wheelhouse | 安装、导入、ABI、聚焦单元测试和运行时闭包 |
| ISIS 原生 APP/GUI | Windows 11 x64 | 版本隔离的 native APP ZIP | DLL 闭包、150 个 CLI APP、`qnet`、`reduce -gui`、`jigsaw -gui`、ISISDATA 和真实操作 |

ISIS 9 和 ISIS 10 必须使用独立的运行时、wheelhouse、native package 和版本标识。不得让一个版本的 DLL、conda 环境或 Python wheel 混入另一个版本。

## Runner 选择规则

1. **self-hosted 优先用于昂贵或平台特定的任务。** Linux 优先使用带有 `ubuntu-26.04` 标签的 self-hosted runner，Windows 优先使用真实 Windows 11 x64 self-hosted runner，以复用 ISIS prefix、编译缓存和 Conda 环境。
2. **GitHub-hosted 是强制可用的 fallback。** Linux fallback 使用 `ubuntu-24.04`，并继续在 Ubuntu 22.04/24.04/26.04 clean-install 矩阵验证 wheelhouse。Windows fallback 使用满足验证脚本 OS 契约的 hosted image；`windows-2022` 是 Windows Server 2022，不能冒充 Windows 11。
3. Runner 选择必须发生在构建 job 排队之前。resolver 应检查 self-hosted runner 是否在线且标签完整；不可用时选择 GitHub-hosted。self-hosted job 排队后掉线不能在同一个 job 内动态改变 `runs-on`，应由 workflow 的重试/fallback 路径重新调度 hosted job。
4. self-hosted runner 只允许受信任的 push、手动 dispatch 或受信任分支使用；不受信任的外部 PR 必须使用 GitHub-hosted。
5. 每次运行必须记录 runner 名称、OS、架构、ISIS 版本/build、Python ABI、commit SHA、artifact 名称和哈希。没有这些字段的运行不能作为发布证据。

2026-10-06 hosted fallback run `37403508140` 已验证 ISIS 9/10 Linux wheel、Windows wheel，以及 Ubuntu 22.04/24.04/26.04 安装矩阵。

## 发布门禁

- Linux wheelhouse 必须在 Ubuntu 22.04、24.04、26.04 完成 clean-install；同一 wheelhouse 必须通过 ABI 和哈希检查。
- Windows wheelhouse 必须在 Windows 11 x64 目标环境完成安装和导入验证。
- Windows native APP ZIP 必须在 Windows 11 x64 完成干净解压矩阵；报告必须包含 150 个 CLI APP、`qnet`、`reduce -gui`、`jigsaw -gui`、依赖闭包、ISISDATA 和负向启动检查。
- ISIS 9 和 ISIS 10 的 wheelhouse、native package、Release tag 和 `SHA256SUMS.txt` 必须分别命名和发布。
- GitHub-hosted 构建通过只能证明该 hosted image 的兼容性；若产品声明为 Windows 11 桌面支持，必须有真实 Windows 11 运行证据。

## 当前状态（2026-10-05）

- Linux ISIS 9/10 wheelhouse：Ubuntu 22.04/24.04/26.04 fallback 矩阵已通过。
- Windows ISIS 9 native APP/GUI：已在 Windows 2025 hosted clean-runtime 通过 M43；真实 Windows 11 self-hosted 复验仍建议保留。
- Windows ISIS 9/10 PyISIS wheelhouse：已有构建、安装和导入验证。
- Windows ISIS 10 native APP/GUI：M47 生成并验证 `usgs-isis-native-apps-10.0.0-win64.zip` 后，才可在 RC4 中声明 ISIS 10 Windows GUI 发布支持。
