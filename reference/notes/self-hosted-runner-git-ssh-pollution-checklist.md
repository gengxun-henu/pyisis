# Self-hosted runner git/ssh pollution checklist

这个文档用于排查 self-hosted GitHub Actions runner 宿主机上是否还残留会把 GitHub checkout 拉回 SSH 的全局配置污染。

## 目标状态

当仓库工作流默认走 HTTPS checkout 时，理想状态应当满足：

- `git remote get-url origin` 显示 `https://github.com/...`
- `git config --global --get-regexp '^url\..*\.insteadof$'` 为空，或至少不含 GitHub SSH 重写
- `git config --system --get-regexp '^url\..*\.insteadof$'` 为空，或至少不含 GitHub SSH 重写
- `git config --global --get core.sshCommand` 为空
- `git config --system --get core.sshCommand` 为空
- `~/.ssh/config` 中没有 `Host github.com` / `HostName ssh.github.com` 之类的全局 GitHub SSH 路由

## 优先排查项

### 1. git rewrite 规则

检查是否存在把 GitHub URL 重写到 SSH 的规则：

- `git config --global --get-regexp '^url\..*\.insteadof$'`
- `git config --system --get-regexp '^url\..*\.insteadof$'`

重点关注这些值：

- `git@github.com:`
- `git@ssh.github.com:`
- `ssh://git@github.com/`
- `ssh://git@ssh.github.com:443/`

### 2. core.sshCommand 与环境变量

检查：

- `git config --global --get core.sshCommand`
- `git config --system --get core.sshCommand`
- `env | grep -E '^(GIT_SSH|GIT_SSH_COMMAND)='`

### 3. `~/.ssh/config`

检查：

- `grep -nE 'github\.com|ssh\.github\.com|Host[[:space:]]+github\.com|ProxyCommand|IdentityFile' ~/.ssh/config || true`

如果看到：

- `Host github.com`
- `HostName ssh.github.com`
- `Hostname ssh.github.com`
- `IdentityFile ~/.ssh/...`

则说明宿主机用户 SSH 配置仍在全局劫持 GitHub SSH 行为。

### 4. systemd runner 环境

检查：

- `systemctl cat actions.runner.* 2>/dev/null || true`
- `systemctl show actions.runner.* --property=Environment 2>/dev/null || true`

重点看是否存在：

- `GIT_SSH_COMMAND=...`
- `GIT_SSH=...`
- `HOME=...`
- 明确的 `ssh.github.com` 路由环境变量

注意：仅出现 `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` 一类代理变量，并不等于 git/ssh 污染，但会影响 HTTPS checkout 路径的稳定性和排障复杂度。

### 5. 实际仓库 remote

在 runner 工作目录中的仓库执行：

- `git remote get-url origin`
- `git remote -v`

如果仍显示：

- `git@github.com:owner/repo.git`
- `ssh://git@github.com/owner/repo.git`

则说明当前工作目录仍然实际在走 SSH remote。

## 当前已观察到的实际症状（2026-04-02）

在当前 self-hosted runner 宿主机上，已经确认以下现象：

### 已确认

- `systemd` service 层未发现 `GIT_SSH_COMMAND` 之类的显式 SSH 注入
- `systemd` service 层存在常驻代理变量注入（`HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` 等）
- `~/.ssh/config` 中存在多段 `Host github.com`，并把 `github.com` 指向 `ssh.github.com`
- `~/.ssh/config` 中至少有一段包含 `IdentityFile ~/.ssh/id_ed25519`
- 当前仓库 `origin` 仍为 `git@github.com:gengxun-henu/pyisis.git`

### 结论

当前宿主机的主要污染点已经明确落在：

- 用户级 `~/.ssh/config`
- 当前仓库本地 remote URL

systemd 层更像是代理环境问题，而不是 SSH 路由污染的主根因。

## 清理建议

### 方案 A：完全切到 HTTPS 基线

适用于：仓库工作流已统一切到 HTTPS checkout，不再需要默认 SSH fallback。

建议：

- 删除 `~/.ssh/config` 中所有 `Host github.com` 的 GitHub 路由块
- 删除或改写当前仓库 `origin` 为 HTTPS
- 保留 SSH 配置给其他主机，但不要继续全局劫持 `github.com`

### 方案 B：保留 SSH 兜底，但不污染默认 `github.com`

适用于：偶尔仍需要手工 SSH 访问 GitHub。

建议：

- 不再使用 `Host github.com`
- 改为自定义别名，例如 `Host github-ssh-fallback`
- 只有在显式使用该别名时才走 `ssh.github.com:443`

## 自动体检入口

仓库内提供了手动触发的诊断工作流：

- `.github/workflows/runner-host-sanity-check.yml`

用途：

- 汇总 git rewrite / ssh config / systemd 环境 / proxy 环境 / checkout probe
- 将结果写入 GitHub Actions step summary
- 可选在检测到污染时直接失败

## 一句话总结

- `systemd` 代理变量 != git/ssh 污染
- `~/.ssh/config` 的 `Host github.com -> ssh.github.com` 才是最典型的 SSH 残留污染
- `origin` 仍是 `git@github.com:...` 时，说明当前仓库仍未完成 HTTPS 基线切换
