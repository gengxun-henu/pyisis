# Pybind workflow guide

This directory currently contains two different workflow roles.

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
- triggered manually with `workflow_dispatch`
- task-scoped inputs such as `issue_number`, `target_scope`, `attempt`, and optional `unit_test_target`
- validates build + unit + smoke in sequence
- comments on the issue and adds blocker labels when the retry budget is exhausted

## How they should work together

Recommended usage:

1. Open one issue using the pybind task issue template
2. Keep the issue scope to one class or one method cluster only
3. Let the GitHub agent work on a PR for that issue
4. Use `agent-pybind-task-draft.yml` to validate each repair attempt
5. Keep `ci-pybind.yml` as the broad repository-level CI gate on PRs and merges

In short:
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

`agent-pybind-task-draft.yml` is a draft task workflow. Keep it manual until the task template, labels, and failure handling pattern are stable enough for broader automation.
