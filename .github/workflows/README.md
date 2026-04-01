# Pybind workflow guide

This directory currently contains several workflow roles.

## `ci-pybind.yml`

Use this as the repository-level baseline CI.

Purpose:
- validate normal pushes to `main` and manual CI dispatches
- verify that the repository can configure, build, run the unit-test suite, and run `tests/smoke_import.py`
- act as the broad regression gate for ongoing development after changes land on the mainline

Characteristics:
- triggered by push and workflow_dispatch
- broad repository coverage
- not task-budget aware
- not tied to one specific upstream class or one specific issue

## `reusable-pybind-build.yml`

Use this as the shared build/smoke building block for pybind CI workflows.

Purpose:
- centralize checkout + local conda/ISIS resolution + CMake configure/build + smoke import
- keep artifact naming, build-log upload, and build failure summaries consistent across workflows
- provide downstream jobs with a reusable build artifact instead of duplicating build boilerplate

Characteristics:
- triggered only through `workflow_call`
- shared by `ci-pybind.yml` and `agent-pybind-pr-gate.yml`
- uploads build logs and optional smoke logs with consistent naming

## `agent-pybind-task-draft.yml` (deprecated legacy)

Use this only as a short-term rollback reference while the split workflows stabilize.

Purpose:
- preserve the old single-workflow task loop for comparison and emergency fallback
- document the pre-split task-flow behavior while `agent-pybind-task.yml` and `agent-pybind-pr-gate.yml` take over

Characteristics:
- manual-only legacy workflow
- not the default dispatch target anymore
- kept temporarily to reduce rollback risk during migration

## `agent-pybind-task.yml`

Use this as the primary single-class task workflow.

Purpose:
- run validation for one upstream ISIS C++ class at a time
- auto-resolve inventory/test context from local CSV files
- enforce the retry budget for task execution on the existing self-hosted conda/ISIS environment

Characteristics:
- triggered by `workflow_dispatch`, either manually or via the issue dispatcher workflow
- centered on `target_class`, with optional issue and unit-test override inputs
- validates build + unit + smoke + progress consistency
- reuses the existing local conda/ISIS environment instead of recreating it

## `agent-pybind-pr-gate.yml`

Use this as the PR-only automatic gate.

Purpose:
- validate pull requests that change bindings, tests, workflow logic, or progress metadata
- ensure the repository still builds and passes smoke/unit checks on the existing local environment

Characteristics:
- triggered by `pull_request`
- gate/checker only; it does not dispatch tasks or comment on issues
- reuses the build artifact across smoke/unit jobs

## `dispatch-pybind-task-from-issue.yml`

Use this as the queue bridge between the issue form and the task workflow.

Purpose:
- watch for a reviewed pybind issue to receive `ready-for-agent`
- parse the issue-form sections needed by `agent-pybind-task.yml`
- dispatch the task workflow with attempt `1`
- switch the issue from `ready-for-agent` to `agent-active`

## `autofill-pybind-task-issue.yml`

Use this as the issue-form helper before dispatch.

Purpose:
- let a human open a `pybind-task` issue with only the target class filled in
- infer suggested scope, local context, expected changes, validation steps, and unit-test target from local inventory files
- update blank issue-form sections in place so the issue is easier to review before adding `ready-for-agent`

Characteristics:
- triggered by `issues` on open, edit, or reopen
- only acts on issues that already have the `pybind-task` label
- fills blank sections only, so manual edits are preserved on later updates
- can suggest a default issue title like `[pybind] Cube` when the title is left at the template stub

## How they should work together

Recommended usage:

1. Open one issue using the pybind task issue template
2. Keep the issue scope to one class or one method cluster only
3. Review the issue quickly and add `ready-for-agent` only when the scope is actionable
4. Let `dispatch-pybind-task-from-issue.yml` queue `agent-pybind-task.yml`
5. Let the GitHub agent work on a PR for that issue
6. Let `agent-pybind-pr-gate.yml` act as the narrow PR gate for agent-task changes
7. Keep `ci-pybind.yml` as the broad repository-level CI gate on merges to `main` and manual dispatches

In short:
- `dispatch-pybind-task-from-issue.yml` = queue bridge from issue form to task workflow
- `agent-pybind-task.yml` = primary narrow task loop with retry budget
- `agent-pybind-pr-gate.yml` = PR-only automatic gate for task-related changes
- `agent-pybind-task-draft.yml` = deprecated legacy fallback during migration
- `ci-pybind.yml` = broad repository regression check for pushes/manual runs
- `reusable-pybind-build.yml` = shared build/smoke plumbing for CI and PR gate

## Queue rule

The intended queue rule is:
- one GitHub agent task = one upstream class or one related method cluster
- every task must add the smallest relevant unit test
- every task must pass build + unit + smoke
- automated repair budget = 5 attempts maximum
- if attempt 5 still fails, write blocker summary, add blocker labels, stop the task, and select the next task from `ready-for-agent`

## Current status

The recommended queue path is now semi-automated:

- `pybind-task.yml` opens the issue with `pybind-task`
- a human review adds `ready-for-agent` when the scope is truly actionable
- `dispatch-pybind-task-from-issue.yml` consumes `ready-for-agent`, adds `agent-active`, and dispatches `agent-pybind-task.yml`

Keep `agent-pybind-task-draft.yml` only as a temporary legacy fallback for experiments or recovery runs during migration.
