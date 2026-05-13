---
name: clean-commit
description: 'Inspect the current git diff, separate relevant changes from unrelated working-tree noise, stage only the intended files, and create one clean local commit. Use when the user asks for 自动commit, 整理成一条干净 commit, 看 diff 顺手提交, clean commit, 拆分提交, 只提交相关改动, or wants the agent to review git changes before committing.'
argument-hint: '[optional focus] e.g. build_test_smoke fix, image_match refactor, only staged pybind changes'
user-invocable: true
disable-model-invocation: false
---

# Clean Commit Workflow

Use this skill when the user wants the agent to turn current workspace changes into a **single clean local commit** instead of blindly committing the entire working tree.

This skill is intentionally review-first. It is designed for the kind of workflow where the agent should:

- inspect the current diff
- identify which files belong to the requested change
- leave unrelated experiments, notes, generated files, or scratch edits out of the commit
- stage only the intended subset
- write an accurate commit message
- create a **local commit only**

This skill is a better fit than a shell script when commit scope depends on semantic judgment rather than filename-only rules.

## Use Cases

Typical prompts that should trigger this skill:

- `看一下这些修改的 git diff，顺手整理成一条干净 commit`
- `帮我自动 commit，但只提交这次修复相关的内容`
- `把当前改动整理成一个 clean commit`
- `先看 diff，再帮我 commit`
- `拆掉工作区里不相关的改动，只提交这部分`
- `给我做一条本地提交，不要 push`
- `只把 build/test 修复提交掉，别带上实验脚本`

## Default Safety Contract

This skill should:

- default to creating a **local** commit only
- **not** push, open a PR, or publish anything unless the user explicitly asks
- avoid staging unrelated files when the working tree contains mixed work
- prefer leaving extra files unstaged over accidentally over-including them
- keep generated artifacts, logs, scratch notes, or experiments out of the commit unless the user explicitly wants them included

If the working tree is obviously mixed, the skill should still proceed autonomously by selecting the clean subset that best matches the user’s request.

## What to Inspect First

Before staging anything, inspect the smallest evidence set that defines commit scope:

1. `git status --short`
2. `git diff --stat`
3. focused file diffs for the files most likely related to the user’s request
4. recent validation evidence already present in the session
5. if needed, the current branch and default-branch context

Prefer using session context if the agent has already just fixed/tested something. Avoid redoing work only to sound more confident.

## Standard Procedure

### 1. Identify the intended commit slice

Determine what change the user most likely wants committed.

Examples:

- the fix just completed in this session
- only pybind binding work
- only `examples/controlnet_construct/` bug fixes
- only a docs update

If there are unrelated working-tree changes, classify them explicitly as:

- **in scope**: belongs in this commit
- **out of scope**: should remain unstaged
- **uncertain**: inspect further before deciding

### 2. Review the diff before touching the index

Do not start with `git add .`.

Instead:

- inspect status and diff summary first
- read the most relevant file diffs
- confirm the commit boundary from real evidence

If the user said “像刚才那种自动 commit”, bias strongly toward the files changed for the just-finished fix, not all currently modified files.

### 3. Stage only the intended files

Stage only the files that match the requested change.

Preferred behavior:

- stage exact paths when possible
- avoid globbing broad directories if the working tree is mixed
- if generated files or logs appeared during testing, leave them unstaged unless they are intentionally tracked deliverables

### 4. Verify staged scope

Before committing, inspect staged content with:

- `git diff --cached --stat`
- `git diff --cached --name-only`

Optionally inspect a focused staged diff when message wording depends on it.

The agent should confirm that the staged set is coherent and does not accidentally include unrelated files.

### 5. Write the commit message

Generate an accurate, conservative commit message based on the staged diff.

Good commit messages should reflect:

- what changed
- why it changed
- the real subsystem names

Avoid vague messages like:

- `update files`
- `fix stuff`
- `WIP`

Prefer concise messages such as:

- `Fix controlnet compatibility module shims`
- `Refine image_match preview cache routing`
- `Add focused tests for Cube pre-create setters`

A short subject plus 2 to 4 explanatory bullets in the body is usually ideal when the change is mixed-but-coherent.

### 6. Create the local commit

Create the commit locally.

After commit:

- show the new commit hash
- show remaining `git status --short`
- briefly summarize what was included and what was intentionally left out

## Repo-Specific Guidance for This Workspace

In this `pyisis` repository, watch especially for mixed working trees containing combinations like:

- verified fixes under `examples/controlnet_construct/`, `examples/image_match/`, `tests/unitTest/`, or `src/`
- unrelated experiment scripts under `examples/experiment_methods/`
- generated artifacts such as `print.prt`
- notes under `reference/notes/`
- temporary test outputs or sweep result CSVs

Unless the user explicitly asks otherwise:

- treat `examples/experiment_methods/*` as likely out-of-scope when the session was about fixing tests/builds elsewhere
- treat `print.prt` as likely generated output, not commit-worthy
- treat `reference/notes/*` as separate docs work unless they were the main deliverable

## Truthfulness Rules

- Never claim a file was intentionally part of the change unless it was actually staged.
- Never say the commit is “clean” unless unrelated files were truly excluded.
- Never claim tests passed unless there is real evidence in the current session or user input.
- If validation only covered a subset, say so accurately when summarizing.

## When Not to Use Blind Automation

Do **not** reduce this workflow to:

- `git add . && git commit -m ...`

unless the user explicitly asks to commit everything in the working tree.

This skill exists precisely to avoid that blunt-instrument behavior.

## Recommended Output After Success

After completing the commit, provide a short result summary including:

- created commit hash
- commit title
- which files were included in scope
- which notable files were intentionally left unstaged

Example shape:

- created local commit `abcdef12` with title `Fix ...`
- included 9 files for the verified controlnet compatibility fix
- left experiment scripts, notes, and generated outputs unstaged

## Good Outcomes

A successful run of this skill should leave the repo in a state where:

- the intended change is captured in one coherent local commit
- unrelated modifications still remain in the working tree, unstaged
- the user can immediately continue with follow-up commits or cleanup

## Anti-Patterns

Avoid these mistakes:

- staging all files without diff review
- mixing bug fixes and experiments into one commit
- including generated outputs by accident
- writing a commit message from memory instead of from the staged diff
- pushing automatically when the user only asked for a commit
