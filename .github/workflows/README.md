# Pybind workflow guide

This directory currently contains three different workflow roles.

## `ci-pybind.yml`

Use this as the repository-level baseline CI.

Purpose:
- validate normal pushes and pull requests
- verify that the repository can configure, build, run the unit-test suite, and run `tests/smoke_import.py`
- act as the broad regression gate for ongoing development

Characteristics:
- triggered by push and pull_request
- broad repository coverage
- not task-budget aware
- not tied to one specific upstream class or one specific issue

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

Characteristics:
- triggered by the `issues` event when the `ready-for-agent` label is added
- only acts on open issues that also have the `pybind-task` label
- leaves malformed issues in human-review state instead of silently dispatching a bad run

## How they should work together

Recommended usage:

1. Open one issue using the pybind task issue template
2. Keep the issue scope to one class or one method cluster only
3. Review the issue quickly and add `ready-for-agent` only when the scope is actionable
4. Let `dispatch-pybind-task-from-issue.yml` queue `agent-pybind-task.yml`
5. Let the GitHub agent work on a PR for that issue
6. Let `agent-pybind-pr-gate.yml` act as the narrow PR gate for agent-task changes
7. Keep `ci-pybind.yml` as the broad repository-level CI gate on PRs and merges

In short:
- `dispatch-pybind-task-from-issue.yml` = queue bridge from issue form to task workflow
- `agent-pybind-task.yml` = primary narrow task loop with retry budget
- `agent-pybind-pr-gate.yml` = PR-only automatic gate for task-related changes
- `agent-pybind-task-draft.yml` = deprecated legacy fallback during migration
- `ci-pybind.yml` = broad repository regression check

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
