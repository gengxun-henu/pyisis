---
name: merge-pr-sync-main
description: "Use when a staged PR is ready for remote main and local main sync. Keywords: merge PR, sync main, PR合并, 同步main, 阶段PR收尾, Stage PR, worktree cleanup."
---

# Merge PR and Sync Main

## Overview

Safely finish a staged PR by merging it through GitHub, then fast-forwarding local `main` to `origin/main`. Prefer the PR surface over local merges so local history matches the repository's protected-branch workflow.

## When to Use

Use this when:

- a stage branch has already been pushed;
- a GitHub PR exists;
- CI/review is expected to be green;
- the user wants the PR merged into remote `main` and local `main` updated.

Do not use this for unpushed work, failing PRs, draft PRs, or branches with unclear base history.

## Safety Rules

- Never merge if checks are failing or pending.
- Never merge a draft PR unless the user explicitly asks.
- Never overwrite local changes.
- Never use `git reset --hard` automatically.
- Prefer `gh pr merge` over local `git merge` into `main`.
- Sync local `main` with `git pull --ff-only origin main`.
- Keep feature worktrees by default until the PR is merged and no follow-up fixes are needed.

## Workflow

### 1. Inspect PR and Worktree

Run from the stage worktree or repository root:

```bash
git status --short --branch
gh pr view <PR_NUMBER_OR_BRANCH> --json number,url,state,isDraft,baseRefName,headRefName,title,mergeStateStatus,statusCheckRollup
gh pr checks <PR_NUMBER_OR_BRANCH>
```

Continue only if:

- PR is `OPEN`;
- `isDraft` is `false`;
- `baseRefName` is `main`;
- `mergeStateStatus` is clean/mergeable;
- checks are successful, with only intentional skips allowed;
- worktree is clean.

### 2. Merge Remote PR

Use the repository's normal merge strategy. For this repository, use merge commits unless the user or repository policy says otherwise:

```bash
gh pr merge <PR_NUMBER> --merge
```

If GitHub refuses because the branch is stale or conflicted, stop and report the reason.

### 3. Sync Local Main

After merge succeeds:

```bash
git fetch origin --prune
git switch main
git pull --ff-only origin main
```

Verify:

```bash
git status --short --branch
git log --oneline --decorate -5
```

Expected: local `main` is clean and aligned with `origin/main`.

### 4. Optional Cleanup

Only clean up when the user asks or when the next workflow explicitly needs it.

```bash
git worktree list
git worktree remove <WORKTREE_PATH>
git branch --merged main
git branch -d <FEATURE_BRANCH>
```

Delete the remote branch only with explicit user approval:

```bash
git push origin --delete <FEATURE_BRANCH>
```

## Failure Handling

### Checks Failed

Stop. Report failing checks and do not merge.

### Local Main Cannot Fast-Forward

Stop. Report that manual inspection is required. Do not reset automatically.

### Worktree Has Local Changes

Stop. Report changed files. Ask whether to commit, stash, or discard.

## Report Format

```text
完成：
- PR #<number> 已合并到远程 main
- 本地 main 已通过 git pull --ff-only 同步到 origin/main
- 当前 main 最新提交：<short-sha> <subject>
- 工作区状态：clean

验证：
- gh pr checks <PR>
- git status --short --branch
- git log --oneline --decorate -5

后续：
- 可以从最新 main 创建下一阶段分支
```
