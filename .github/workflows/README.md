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

## `agent-pybind-task-draft.yml`

Use this as the task-scoped GitHub-agent workflow.

Purpose:
- run validation for exactly one upstream ISIS C++ class or one related method cluster
- enforce the retry budget for agent-driven repair attempts
- write blocker guidance when the task still fails on attempt 5

Characteristics:
- triggered by `workflow_dispatch`, either manually or via the issue dispatcher workflow
- task-scoped inputs such as `issue_number`, `target_scope`, `attempt`, and optional `unit_test_target`
- validates build + unit + smoke in sequence
- comments on the issue and adds blocker labels when the retry budget is exhausted

## `dispatch-pybind-task-from-issue.yml`

Use this as the queue bridge between the issue form and the task workflow.

Purpose:
- watch for a reviewed pybind issue to receive `ready-for-agent`
- parse the issue-form sections needed by `agent-pybind-task-draft.yml`
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
4. Let `dispatch-pybind-task-from-issue.yml` queue `agent-pybind-task-draft.yml`
5. Let the GitHub agent work on a PR for that issue
6. Keep `ci-pybind.yml` as the broad repository-level CI gate on PRs and merges

In short:
- `dispatch-pybind-task-from-issue.yml` = queue bridge from issue form to task workflow
- `agent-pybind-task-draft.yml` = narrow task loop with retry budget
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
- `dispatch-pybind-task-from-issue.yml` consumes `ready-for-agent`, adds `agent-active`, and dispatches `agent-pybind-task-draft.yml`

Keep manual `workflow_dispatch` available as a fallback for experiments or recovery runs.
