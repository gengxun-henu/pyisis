# M06 完成后的新会话启动提示词

## 新会话启动提示词

请在 `D:\code\pyisis\pyisis\.worktrees\m04-windows-pyisis-wheelhouse` 工作树继续工作。

先读取并遵守仓库根目录 `AGENTS.md`，然后使用 `milestone-session-manager` 检查：

- `.planning/milestones.v1.json`
- `.planning/milestone-index.md`
- `.planning/windows-isis9-m06-native-app-implementation/task_plan.md`
- `.planning/windows-isis9-m06-native-app-implementation/progress.md`
- `.planning/windows-isis9-m06-native-app-implementation/findings.md`
- `docs/superpowers/plans/2026-08-17-csv2table-native-app-unification.md`
- `docs/superpowers/plans/2026-08-16-windows-isis-native-app-distribution.md`
- `.superpowers/sdd/2026-08-16-windows-isis-native-app-distribution/final-review.md`

确认 milestone `windows-isis9-m06-native-app-implementation` 已是 `complete`，不要重新打开、重复执行或把后续工作写回 M06。当前 registry 没有 dependency-ready 的 pending milestone；请根据仓库现状和用户后续目标识别或创建下一个 milestone。开始修改代码前，先向用户汇报新 milestone 的建议 ID、范围、依赖、完成门槛和第一项具体行动。

必须保留以下既有事实：

- csv2table 已统一为原生 ISIS APP，不提供 `pyisis.csv2table` 或进程内绑定便利函数。
- ISIS 9/10 × Windows/Linux 的 csv2table 矩阵为 12/0/0。
- Windows ISIS 9 便携发行包含 150 个 CLI APP 加 qnet；clean Windows 11 runtime 为 166/0/0。
- M06 最终实现与里程碑关闭提交分别为 `e7365943` 和 `84721a86`，均已推送到 `feature/m04-windows-pyisis-wheelhouse`。
- 正式 ZIP、dependency report、validation report 和归档 clean-host raw report位于 `build/windows/`；不要无理由重建或删除。
- `print.prt` 是预存 guardrail 修改，禁止修改、恢复、删除或提交。
- `pyisis-windows11` runner 当前由 `D:\actions-runner-pyisis\run.cmd` 手动启动；本会话结束时 listener 正在运行。自动服务安装因缺少管理员权限尚未完成，不能假定重启后仍在线。
- 开发机存在被 clean-host workflow 明确禁止的 ISIS prefix，因此不能把本机 self-hosted Actions 结果冒充 isolated clean-host 证据。
- 已批准延期的唯一 csv2table Minor 是 `rank_isis_apps.py` 在缺少 `--source-root` 时显示原始 `ValueError`；除非新 milestone 明确纳入，否则不要顺手修改。

不要进入下一 milestone 的实现，直到完成上述读取、核对当前 Git 状态并向用户报告建议范围。

## Session checkpoint

- Primary workflow: Superpowers（由 `docs/superpowers/plans/2026-08-16-windows-isis-native-app-distribution.md` 检测得出）
- CWD: `D:\code\pyisis\pyisis\.worktrees\m04-windows-pyisis-wheelhouse`
- Branch/worktree: `feature/m04-windows-pyisis-wheelhouse` / `.worktrees/m04-windows-pyisis-wheelhouse`
- Goal: 在不重开 M06 的前提下识别、定义并启动下一个 milestone
- Current phase or plan task: M06 已完成；当前没有 active milestone 或 dependency-ready pending milestone
- Completed: csv2table 原生 APP 统一、四平台验证、Windows ISIS 9 便携 ZIP、clean-host 166/0/0、双层独立审查、structured completion evidence、registry closure、远端推送和约 40 GB 临时构建清理
- Files changed: 本交接文件；此前 M06 关闭记录已提交于 `84721a86`
- Validation completed: milestone verification PASS；csv2table focused 47/0/1 加矩阵 12/0/0；Windows native 73/73；clean Windows 11 166/0/0；最终审查 Ready 且 0 findings
- Review status: csv2table final review Ready；Task 7 review Ready；native-distribution final review Ready
- Running processes: `D:\actions-runner-pyisis\bin\Runner.Listener.exe run`（会话结束前已核对；新会话必须重新检查，不能假定仍存活）
- Do not repeat: 不重开 M06；不重复 QEMU clean-host；不重建已验证 ZIP；不修改或提交 `print.prt`
- Remaining risks: runner 未安装自动启动服务；开发机不是 isolated clean host；批准延期的 rank CLI raw `ValueError` Minor 仍存在
- Exact next action: 读取 registry 和本交接引用文件，核对 `git status --short --branch`，然后向用户提出下一个 milestone 的 ID、范围、依赖与完成门槛
- Recommended resume skill: `milestone-session-manager`
