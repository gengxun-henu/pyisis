---
name: push-and-pr
description: 'Push the current branch to the remote and create a GitHub pull request for this pyisis repository. Use when the user asks for 推到远程并开PR, 推当前分支到远程 PR, 自动 push branch and create PR, 发布当前分支, 提交远程审核, open PR for current branch, or wants one workflow that pushes then opens a PR.'
argument-hint: '[optional focus] e.g. current branch to main, draft PR, use current commit summary, only if working tree is clean'
user-invocable: true
disable-model-invocation: false
---

# Push Branch and Open PR

Use this skill when the user wants a **single workflow** that:

1. checks the current branch state
2. ensures the intended changes are committed
3. pushes the branch to the remote
4. creates a GitHub pull request

This skill is the repository-aware, action-taking companion to:

- `clean-commit` for local commit cleanup
- `pyisis-pr-writeup` for reviewer-facing PR text

Use this skill instead of a shell script when the workflow needs judgment about:

- whether there are uncommitted changes
- whether the current branch has an upstream
- whether the branch is already pushed
- whether a draft PR is more appropriate
- how to describe the PR accurately for this repository

## When to Use

Typical prompts that should trigger this skill:

- `帮我把当前分支推到远程并开 PR`
- `把这个分支发上去给 reviewer`
- `push 当前分支然后创建 PR`
- `自动推远程 PR`
- `发布当前分支到 GitHub 并开一个 PR`
- `推送并创建草稿 PR`
- `push this branch and open a PR against main`

## Default Safety Contract

This skill may perform **remote side effects** because the user explicitly asked for push + PR behavior.

By default it should:

- push the current branch to `origin`
- create a PR against the repo default branch unless the user specifies another base
- prefer creating a normal PR unless the user clearly wants a draft or the work is obviously not review-ready
- avoid publishing unreviewed working-tree noise by checking commit state before push

It should **not** silently push uncommitted local edits by inventing a commit. If the working tree is dirty, it should first determine whether:

- the user wants those edits included now
- the branch is already in a suitable state to open a PR without them
- the `clean-commit` workflow should be applied first

## Workspace-Specific Expectations for `pyisis`

In this repository, PR creation should reflect real repo structure and validation language. Prefer repository-accurate wording such as:

- `examples/controlnet_construct/`
- `examples/image_match/`
- `tests/unitTest/`
- `tests/smoke_import.py`
- `ctest --test-dir build -R python-unit-tests`
- pybind / examples / bug fix / refactor distinctions

Also watch for mixed working trees that may contain:

- unrelated `examples/experiment_methods/*`
- generated artifacts like `print.prt`
- scratch notes under `reference/notes/*`
- sweep outputs or temporary CSVs

If the branch is dirty and the user wants to include current edits, prefer using the `clean-commit` skill logic rather than bluntly staging everything.

## What to Inspect First

Before pushing or opening a PR, inspect the smallest evidence set that determines whether publish is safe:

1. current branch name
2. `git status --short`
3. whether there are staged/unstaged changes
4. whether the branch has an upstream
5. whether local commits are ahead of the upstream
6. whether a PR already exists for the current branch when relevant
7. recent validation evidence already available in the session

When possible, reuse session evidence instead of rerunning tests just to pad the PR description.

## Standard Procedure

### 1. Confirm the publish target

Determine:

- **head branch**: usually the current local branch
- **base branch**: default to the repository default branch unless the user asks otherwise
- **draft or not**: infer from user wording or current readiness

For this repository, the common default should be:

- head = current branch
- base = `main`

### 2. Inspect working tree and commit state

Check whether the working tree is clean.

#### Case A: clean working tree

Proceed to upstream / push checks.

#### Case B: dirty working tree

Do not blindly publish.

Instead:

- determine whether the dirty files are intended for this PR
- if yes, use the same review-first logic as `clean-commit`
- if no, leave them out and push only the already-committed branch state

If the branch has no new commits to push and the dirty changes are the only intended work, create a clean local commit first before pushing.

### 3. Ensure branch is pushable

Check whether the current branch already tracks a remote upstream.

#### If upstream exists

Push with the normal branch push flow.

#### If upstream does not exist

Push with upstream setup (for example the equivalent of setting upstream on first push).

The skill should handle the common first-push case autonomously.

### 4. Prepare PR title and description

If the user did not provide PR text, prepare it from real branch evidence.

Preferred sources:

1. branch purpose from the current session
2. staged / committed diff summary
3. recent validation evidence from the session
4. repository-aware wording from the `pyisis` repo structure

If the user asks only for “push and create PR”, the skill should still generate a sensible PR title/body instead of opening an empty PR.

Use the same truthfulness bar as `pyisis-pr-writeup`:

- do not claim CI passed unless actually seen
- do not overstate validation
- distinguish focused unit tests, smoke import, build, and local script runs accurately

### 5. Push the branch

Push the branch to `origin`.

After pushing, verify that:

- the push succeeded
- the branch name used for the PR head is the pushed branch

### 6. Create the PR

Create the PR using the pushed branch as head.

By default:

- repo owner/name should match the current repository
- base should default to `main` for this repo unless overridden
- draft should default to `false` unless the user indicates draft/WIP semantics

### 7. Report the result clearly

After success, report:

- pushed branch name
- PR title
- PR number
- PR URL
- whether it was a draft
- what validation evidence was reflected in the PR body

If the skill had to exclude dirty files from publication, say so explicitly.

## Recommended Decision Rules

### Dirty working tree + user wants everything published

Use review-first local commit handling before push.

### Dirty working tree + current branch already has the intended commits

Prefer pushing the committed branch state and explicitly mention that local uncommitted edits were left out.

### No upstream branch

Create upstream on first push automatically.

### No PR title/body given

Generate them conservatively from the branch diff and session evidence.

### Existing PR already open

Do not create a duplicate PR if the active tooling reveals an existing one for the same branch. Prefer reporting the existing PR and, if needed, just push the new commits.

## Truthfulness Rules

- Never claim a push succeeded unless it actually succeeded.
- Never claim a PR was created unless the remote tool returned success.
- Never claim the PR contains local dirty changes unless they were actually committed and pushed.
- Never imply all local changes were published if some were intentionally left out.
- Never fabricate validation results in the PR body.

## Anti-Patterns

Avoid these mistakes:

- pushing a dirty branch without reviewing what should be published
- staging all changes automatically just to make push succeed
- creating a PR with a generic title/body when repo-aware wording is available
- opening a duplicate PR for a branch that already has one
- claiming the PR is ready for review when the user clearly wanted a draft

## Good Outcome

A successful run of this skill should leave the user with:

- the current branch pushed to the remote
- a PR opened against the intended base branch
- a reviewer-friendly title and description
- no accidental inclusion of unrelated local working-tree noise

## Recommended Output After Success

After completion, report something like:

- pushed branch `feat/...` to `origin`
- created PR `#123` with title `...`
- target base branch: `main`
- PR link: `...`
- local working tree changes left out: `none` / `list if applicable`

## Recommended Output After Partial Publish

If the branch was pushed and a PR already existed, report something like:

- pushed latest commits to `origin/<branch>`
- existing PR detected / reused
- PR link: `...`
- uncommitted local files left unpublished: `...`

## Suggested Composition With Other Skills

- If commit scope is messy, apply `clean-commit` logic first.
- If PR wording needs richer text, reuse `pyisis-pr-writeup` style and evidence gathering.

This skill is meant to provide the end-to-end publish workflow after local coding work is done.
