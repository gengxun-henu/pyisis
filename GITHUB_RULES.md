# GitHub Branch Rules Checklist

本文档用于为 `pyisis` 仓库配置 GitHub Branch Rules，按 GitHub 设置页的常见显示顺序整理，目标是做到：**打开设置页后照着勾选即可**。

## 适用分支

优先对以下分支启用：

- `main`

如果后续增加发布分支，可复制同样规则到：

- `release/**`

---

## 推荐目标

针对 `main`，推荐采用：

- 禁止直接推送
- 必须走 Pull Request
- 必须通过核心 CI 检查
- 禁止 force push
- 保持线性历史
- 对创建、更新、删除主分支增加 bypass 保护

---

## 按设置页顺序逐项勾选

### 1. Branch name pattern

填写：

- `main`

如果后续为发布分支单独建规则：

- `release/**`

### 2. Restrict creations

建议：**开启**

含义：

- 只允许具有 bypass permission 的用户创建匹配该规则的 ref。

推荐配置：

- 对 `main` 开启
- bypass 列表仅保留仓库管理员或你明确授权的维护者

### 3. Restrict updates

建议：**开启**

含义：

- 只允许具有 bypass permission 的用户直接更新匹配 ref。

推荐配置：

- 对 `main` 开启
- 普通贡献者通过功能分支 + PR 提交，不直接 push 到 `main`

### 4. Restrict deletions

建议：**开启**

含义：

- 只允许具有 bypass permission 的用户删除匹配 ref。

推荐配置：

- 对 `main` 开启
- 作为防误删保护，强烈建议保留

### 5. Require linear history

建议：**开启**

含义：

- 禁止向匹配分支推送 merge commit，保持提交历史线性。

配套建议：

- 在仓库合并方式中关闭 **Merge commit**
- 保留 **Squash merge**
- 可选保留 **Rebase merge**

### 6. Require deployments to succeed

建议：**暂不开启**

原因：

- 当前仓库主要依赖构建、smoke、metadata、unit test 校验
- 目前没有明确的 deployment environment 作为必过门槛

何时再开启：

- 当仓库已经稳定配置 GitHub Environments，例如：`staging`、`docs-preview`、`release-validation`
- 并且这些环境部署确实是合并前必须成功的条件

### 7. Require signed commits

建议：**按团队习惯决定**

如果满足以下条件，可开启：

- 维护者都已稳定配置 GPG 或 SSH commit signing
- 机器人/自动化提交也不会因此被阻塞

如果当前目标是减少协作摩擦，建议：

- 先不启用
- 待签名流程稳定后再补上

### 8. Require a pull request before merging

建议：**开启**

这是 `main` 的核心保护规则。

推荐子配置：

- Require pull request before merging: **开启**
- Required approvals: **1**
- Dismiss stale approvals when new commits are pushed: **开启**
- Require review from Code Owners: **如果仓库维护了 `CODEOWNERS`，则开启**

说明：

- 所有改动应先进入非目标分支
- 再通过 Pull Request 合并进 `main`

### 9. Require status checks to pass

建议：**开启**

应选择为 required 的核心检查项：

- `Metadata audit`
- `Build and smoke gate / github_hosted / Reusable build`
- `Build and smoke gate / github_hosted / Reusable smoke import`
- `Python unit-test gate`

不建议设为 required 的检查项：

- `Resolve runner mode / Resolve runner configuration`
- `Prepare PR context`
- `Build and smoke gate / self_hosted`

原因：

- 前两项更偏流程准备步骤，不适合作为最终合并门槛
- `self_hosted` 可能出现 `neutral`，不适合当作稳定的必过条件

### 10. Block force pushes

建议：**开启**

含义：

- 阻止具有 push 权限的用户对匹配分支进行 force push。

推荐配置：

- 对 `main` 开启
- 除非你明确需要在极少数紧急维护场景下重写历史，否则不建议放开

### 11. Require code scanning results

建议：**暂不开启**

原因：

- 只有在仓库已经稳定启用 CodeQL 或其他 code scanning 工具，并且每次相关更新都能回传结果时，这项才适合打开
- 当前仓库的核心门槛仍以构建和测试为主

### 12. Require code quality results

建议：**暂不开启**

原因：

- 只有在仓库已经有稳定的 code quality 平台或 PR 质量分析结果时，这项才有意义
- 否则会形成“规则已开、结果却无稳定来源”的阻塞项

### 13. Automatically request Copilot code review

建议：**开启**

原因：

- 对新 PR 自动请求 Copilot code review，适合当前仓库这种持续迭代的 C++ / pybind11 / Python 测试型开发模式
- 有助于尽早发现漏测、导出不一致、机械性修改遗漏等问题

注意：

- 它是自动辅助审查，不替代人工 review

---

## 推荐的最终勾选结果（`main`）

### 建议开启

- [x] Restrict creations
- [x] Restrict updates
- [x] Restrict deletions
- [x] Require linear history
- [x] Require a pull request before merging
- [x] Require status checks to pass
- [x] Block force pushes
- [x] Automatically request Copilot code review

### 视情况开启

- [ ] Require signed commits

### 暂不建议开启

- [ ] Require deployments to succeed
- [ ] Require code scanning results
- [ ] Require code quality results

---

## 必选状态检查清单

将以下 checks 设为 required：

- [x] `Metadata audit`
- [x] `Build and smoke gate / github_hosted / Reusable build`
- [x] `Build and smoke gate / github_hosted / Reusable smoke import`
- [x] `Python unit-test gate`

不要设为 required：

- [ ] `Resolve runner mode / Resolve runner configuration`
- [ ] `Prepare PR context`
- [ ] `Build and smoke gate / self_hosted`

---

## 配套仓库设置建议

如果启用了 **Require linear history**，建议在仓库的 merge options 中同步调整：

- 关闭 **Allow merge commits**
- 开启 **Allow squash merging**
- 可选开启 **Allow rebase merging**

这样可以避免规则与合并方式互相冲突。

---

## 一句话版本

对 `main` 采用 **PR-only + 必过核心 CI + 禁止 force push + 线性历史 + bypass 保护** 的组合，是当前这个仓库最稳妥、维护成本也最低的方案。
