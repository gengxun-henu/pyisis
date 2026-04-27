name: pyisis-pr-writeup
description: 'Generate repository-aware commit notes, PR descriptions, and change summaries for this pyisis workspace. Use when the user asks for 提交说明, PR 描述, 变更摘要, commit message, PR title, reviewer summary, release-note-style summary, 当前分支改动总结, or wants a polished writeup for pybind/tests/examples changes.'
argument-hint: '[optional focus] e.g. image_match refactor, pybind binding summary, concise PR text, bilingual summary'
user-invocable: true
disable-model-invocation: false
---

# PyISIS PR / Commit Writeup

Use this skill when the user wants a polished, repository-aware writeup for current changes in this workspace, especially for:

- 提交说明
- PR 描述
- 变更摘要
- commit message / PR title 候选
- reviewer-facing summary
- 简版 / 完整版 / 双语版变更说明

This skill is specialized for the `pyisis` repository. It should produce text that reflects this repo's real structure, validation style, and terminology instead of generic GitHub prose.

This is the **workspace-specific companion** to any user-level generic PR/commit writeup prompt. When both could apply, prefer this skill's repository-aware framing for `pyisis` details while still returning a directly copyable result.

Reference the default output skeleton in [assets/default-output-template.md](./assets/default-output-template.md) when a reusable markdown shape helps.

## Example Invocations

This skill should work well for prompts like:

- `帮我整理这次实现的提交说明 / PR 描述 / 变更摘要`
- `总结一下当前分支相对 main 的改动，给 reviewer 一版中文说明`
- `给我一版简洁 commit message + 完整 PR 描述，强调本地验证`
- `按 pyisis 仓库语境写，不要泛泛而谈`
- `给我一版双语 PR 描述，中文在前，英文在后`
- `按这个仓库的 pybind / unittest / smoke 语境来写`
- `把本地验证写准确一点，不要吹成 CI 全绿`

## What to Inspect First

Before drafting, gather the smallest useful evidence set from the current workspace:

1. current branch and default branch context
2. changed files or diff summary relative to the default branch when available
3. recent validation evidence already visible in the session (focused unit tests, smoke import, build results, terminal history)
4. any user-provided implementation notes, goals, caveats, or reviewer emphasis
5. if needed, the most relevant changed source or test files for wording accuracy

Typical high-value evidence in this repository includes items such as:

- `PYTHONUNBUFFERED=1 "$CONDA_PREFIX/bin/python" -X faulthandler -m unittest discover -s tests/unitTest -p "*_unit_test.py" -v`
- `ctest --test-dir build -R python-unit-tests --output-on-failure`
- `"$CONDA_PREFIX/bin/python" tests/smoke_import.py`
- focused `tests.unitTest.<module>` execution
- `examples/controlnet_construct/*.sh` or `*.py` pipeline runs explicitly mentioned by the user or present in session context

Prefer concrete evidence over vague summaries. If evidence is partial, write conservatively.

If the session already contains recent build/test/output evidence, prefer reusing it instead of rerunning commands just to make the prose sound stronger.

## Repository-Specific Framing

When summarizing changes in this repo, prefer the real project language used here, such as:

- pybind11 binding / Python exposure / wrapper / lambda adapter
- `tests/unitTest/` focused validation
- `tests/smoke_import.py` smoke coverage
- `pybind_progress_log.md` progress updates
- `todo_pybind11.csv` / method inventory synchronization
- `examples/controlnet_construct/` pipeline scripts and image matching stages
- build / import / runtime distinctions when reporting validation

Do not flatten these into generic phrases like “updated backend logic” if a more specific repo-accurate phrase is available.

Also preserve the distinction between these common validation buckets when relevant:

- CMake configure/build succeeded
- focused `tests/unitTest/...` passed
- repo-wide `unittest discover` passed
- `ctest --test-dir build -R python-unit-tests` passed
- `tests/smoke_import.py` passed
- local example / pipeline command completed

Do not collapse all of them into a generic “已测试通过”.

## Drafting Procedure

### 1. Identify the change type

Classify the current work before writing:

- pybind binding extension
- test addition or fix
- example or pipeline script change
- bug fix
- refactor
- documentation or config update
- mixed change

If mixed, separate the categories clearly in the final writeup.

### 2. Identify the reviewer-relevant facts

Prefer to capture these facts explicitly when available:

- what behavior changed
- why the change was needed
- what files or modules were mainly touched
- what validation was run
- what was intentionally not changed
- any residual risk, assumptions, or follow-up work

If the current branch includes mixed work (for example repo-infrastructure edits plus `examples/controlnet_construct/` changes), keep the summary centered on the user-indicated focus or the most reviewer-relevant implementation slice instead of listing every incidental file equally.

### 3. Produce reusable text blocks

By default, generate these sections in Chinese unless the user asks otherwise:

#### 提交标题建议
- 1 to 3 concise candidates
- use conventional-commit style if it fits naturally

#### 提交说明
- 3 to 6 bullets
- focus on concrete implementation and intent

#### PR 标题建议
- 1 to 2 reviewer-friendly candidates

#### PR 描述
Use a structure like:
- 背景 / 目标
- 本次改动
- 验证
- 风险 / 兼容性
- 后续事项（如适用）

#### 变更摘要
- 3 to 5 lines max
- suitable for chat, issue comment, or daily log

If the user asks for only one of the above, output only that section.

If evidence is thin but the user still wants a draft, provide the most usable conservative version and explicitly mark missing proof points with phrases like:

- `当前会话未见 CI 结果`
- `以下验证基于本地已执行命令整理`
- `若需更强表述，可补充 diff/测试范围`

## Truthfulness Rules

- Never claim tests passed unless there is actual evidence in the current session or user input.
- Never claim a file or module was updated unless supported by context.
- If the reason for a change is inferred rather than explicitly stated, phrase it conservatively.
- If validation is partial, say so directly.
- Do not present example shell snippets, scratch notes, or local ad-hoc experiments as durable product behavior changes unless the code or docs were actually updated accordingly.

## Style Rules

- Be concise, technical, and reviewer-friendly.
- Prefer “what changed + why + how verified” over generic praise.
- Avoid inflated wording.
- Prefer directly copyable output over meta commentary.
- If both a concise and a fuller version would be useful, provide both with clear labels.
- Default to Chinese unless the user explicitly asks for English or bilingual output.

## Good Output Characteristics

A good writeup for this repo usually:

- names the actual subsystem (`src/`, `tests/unitTest/`, `examples/controlnet_construct/`, etc.)
- distinguishes binding changes from test or example changes
- mentions focused validation instead of vague “tested locally” wording
- reflects whether work is feature, fix, refactor, or maintenance
- stays accurate even when the session context is incomplete

## Recommended Working Order

1. Determine whether the user wants commit text, PR text, summary text, or a bundle of all three.
2. Reuse branch/test/context evidence already present in the session.
3. Inspect only the smallest additional diff or file context needed for accuracy.
4. Draft reviewer-friendly copy using the default output skeleton.
5. Remove any claim that is not clearly supported by current evidence.

## Useful User Phrases to Match

This skill should be easy to discover for requests such as:

- 帮我整理这次实现的提交说明
- 写一下 PR 描述
- 给我一份变更摘要
- 帮我总结当前分支改动
- 生成 commit message / PR title
- 给 reviewer 一版简洁说明

## When Not to Overreach

Do not invent:

- benchmark gains
- hidden root causes not evidenced by code or user notes
- CI results not actually seen
- full compatibility guarantees when only focused tests were run

## Default Output Skeleton

Unless the user asks for a different format, prefer the section order from [assets/default-output-template.md](./assets/default-output-template.md).
