# Pybind workflow guide

This directory currently contains several workflow roles.

## Shared checkout rule

Workflow runner behavior is now selected from `.github/runner-config.yml`.

Supported modes:

- `self-hosted`
- `github-hosted`

Supported named profiles:

- `self-hosted-http` — self-hosted HTTPS path for plain direct network access when unattended GitHub connectivity is stable enough
- `self-hosted-watt` — current default self-hosted HTTPS path for WATT/Hosts-accelerated GitHub access
- `self-hosted-ssh` — self-hosted SSH checkout fallback over `ssh.github.com:443`
- `github-hosted` — GitHub-hosted baseline runner with micromamba environment setup

In `self-hosted` mode, workflows follow the checkout transport configured in `.github/runner-config.yml` and reuse the pre-provisioned local conda/ISIS environment. The current recommended default is HTTPS so self-hosted runners can benefit from local proxy or acceleration tools when available.

In `github-hosted` mode, workflows use the configured GitHub-hosted runner image (currently `ubuntu-22.04` by default), checkout over normal HTTPS, and create a micromamba-based build environment inside the workflow.

The shared runner resolution pipeline is:

- `.github/runner-config.yml` — top-level switch and mode-specific defaults
- `.github/actions/resolve-runner-config/action.yml` — normalizes the selected mode into reusable outputs
- `.github/workflows/reusable-runner-config.yml` — bootstrap workflow used by top-level workflows before scheduling mode-dependent jobs

The GitHub-hosted environment spec lives in `.github/conda/pybind-ci-environment.yml`.

All workflows that clone this repository are expected to follow the transport selected by `.github/runner-config.yml`.

Required repository or organization secret:

- `ACTIONS_CHECKOUT_SSH_KEY`: private SSH key with read access to this repository

Note: this secret is required only when the active runner mode uses SSH checkout.

Implementation notes:

- when the resolved checkout transport is `ssh`, workflows configure `~/.ssh/config` so `github.com` is routed to `ssh.github.com` on port `443`
- when the resolved checkout transport is `ssh`, `actions/checkout@v4` receives `ssh-key: ${{ secrets.ACTIONS_CHECKOUT_SSH_KEY }}` to avoid fallback to HTTPS
- when the resolved checkout transport is `https`, workflows skip the SSH setup step and use the default HTTPS checkout flow
- reusable workflows that need checkout still receive secrets via `secrets: inherit`, but they only require `ACTIONS_CHECKOUT_SSH_KEY` when the resolved checkout transport requests SSH checkout

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
- consumes normalized runner settings from `reusable-runner-config.yml`
- supports both reused local conda/ISIS environments and workflow-created micromamba environments

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
- validate either the dispatched SHA or an explicit bootstrap task branch created from an issue
- enforce the retry budget for task execution on the existing self-hosted conda/ISIS environment

Characteristics:
- triggered by `workflow_dispatch`, either manually or via the issue dispatcher workflow
- centered on `target_class`, with optional issue, PR, git-ref, and unit-test override inputs
- validates build + unit + smoke + progress consistency
- now follows `.github/runner-config.yml` and can either reuse the local conda/ISIS environment or create a GitHub-hosted micromamba environment

## `bridge-pybind-issue-to-pr.yml`

Use this as the explicit bridge between an actionable issue and an editable draft PR.

Purpose:
- consume the parsed issue context after `ready-for-agent`
- create or reuse a stable bootstrap branch for that task
- open or refresh a draft PR that carries the issue context forward into the coding phase
- dispatch `agent-pybind-task.yml` against the bootstrap branch so validation targets the same work branch

Characteristics:
- triggered by `workflow_dispatch`, normally from `dispatch-pybind-task-from-issue.yml`
- idempotent for the same issue number and target class
- writes a backlink comment on the issue with the draft PR URL and branch name
- keeps the issue queue and PR lane explicitly connected inside the repository automation
- the bridge workflow itself is lightweight and should prefer `github-hosted`; any `runner_profile` input is forwarded to the downstream `agent-pybind-task.yml` dispatch rather than forcing the bridge job onto self-hosted infrastructure

## `agent-pybind-pr-gate.yml`

Use this as the PR-only automatic gate.

Purpose:
- validate pull requests that change bindings, tests, workflow logic, or progress metadata
- ensure the repository still builds and passes smoke/unit checks on the existing local environment

Characteristics:
- triggered by `pull_request`
- gate/checker only; it does not dispatch tasks or comment on issues
- reuses the build artifact across smoke/unit jobs
- now resolves its runner mode from `.github/runner-config.yml`

## `dispatch-pybind-task-from-issue.yml`

Use this as the queue bridge between the issue form and the task workflow.

Purpose:
- watch for a reviewed pybind issue to receive `ready-for-agent`
- parse the issue-form sections needed by the branch/PR bridge workflow
- dispatch `bridge-pybind-issue-to-pr.yml`
- switch the issue from `ready-for-agent` to `agent-active`

Characteristics:
- lightweight issue-queue workflow; prefer `github-hosted` so label handling and dispatch are not blocked by self-hosted checkout/network instability

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
- now uses the shared runner configuration bootstrap before scheduling its job
- this workflow is intentionally lightweight and should prefer `github-hosted` so issue autofill is not blocked by self-hosted WATT checkout problems

## `runner-host-sanity-check.yml`

Use this as the manual runner-host diagnostic workflow.

Purpose:
- inspect a self-hosted or resolved runner for git/ssh contamination that can silently pull checkout back to SSH
- summarize git `insteadof` rules, `core.sshCommand`, `~/.ssh/config`, runner service environment, proxy environment, and optional checkout probe results
- provide a low-risk manual audit path before or after changing checkout transport defaults

Characteristics:
- triggered by `workflow_dispatch`
- uses the shared runner configuration bootstrap before scheduling its diagnostic job
- can optionally fail when findings are detected
- writes the audit report to the step summary for easy copy/paste into issues or ops notes

Related reference note:
- `reference/notes/self-hosted-runner-git-ssh-pollution-checklist.md`

## How they should work together

Recommended usage:

1. Open one issue using the pybind task issue template
2. Keep the issue scope to one class or one method cluster only
3. Review the issue quickly and add `ready-for-agent` only when the scope is actionable
4. Let `dispatch-pybind-task-from-issue.yml` queue `bridge-pybind-issue-to-pr.yml`
5. Let the bridge workflow open or refresh the bootstrap draft PR and dispatch `agent-pybind-task.yml` against that task branch
6. Let the GitHub agent or a human contributor push coding changes to the draft PR branch
7. Let `agent-pybind-pr-gate.yml` act as the narrow PR gate for agent-task changes
8. Keep `ci-pybind.yml` as the broad repository-level CI gate on merges to `main` and manual dispatches

In short:
- `.github/runner-config.yml` = top-level runner mode switch for all workflows
- `dispatch-pybind-task-from-issue.yml` = queue bridge from issue form to issue/PR bridge workflow
- `bridge-pybind-issue-to-pr.yml` = explicit issue -> bootstrap branch -> draft PR bridge
- `agent-pybind-task.yml` = primary narrow task loop with retry budget, now branch-aware
- `agent-pybind-pr-gate.yml` = PR-only automatic gate for task-related changes
- `agent-pybind-task-draft.yml` = deprecated legacy fallback during migration
- `ci-pybind.yml` = broad repository regression check for pushes/manual runs
- `reusable-pybind-build.yml` = shared build/smoke plumbing for CI and PR gate
- `runner-host-sanity-check.yml` = manual host-level git/ssh/proxy hygiene audit

Practical split:

- keep heavy build/test workflows on `self-hosted-watt` when the local ISIS/conda environment and domestic-network acceleration are required
- keep lightweight issue/autofill/dispatch workflows on `github-hosted` so queue handling, issue comments, and draft PR creation do not depend on self-hosted checkout stability

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
- `dispatch-pybind-task-from-issue.yml` consumes `ready-for-agent`, adds `agent-active`, and dispatches `bridge-pybind-issue-to-pr.yml`
- `bridge-pybind-issue-to-pr.yml` creates or reuses the bootstrap branch, opens/updates the draft PR, comments back on the issue, and dispatches `agent-pybind-task.yml` against that branch

Keep `agent-pybind-task-draft.yml` only as a temporary legacy fallback for experiments or recovery runs during migration.

## Runner config quick reference

Current control file:

- `.github/runner-config.yml`

Key fields:

- `active_profile`: selected named runtime profile
- `profiles.<name>.mode`: resolved runner mode (`self-hosted` or `github-hosted`)
- `profiles.<name>.labels`: label list used for self-hosted profiles
- `profiles.<name>.github_hosted_runner`: image used by the `github-hosted` profile
- `profiles.<name>.checkout_transport`: checkout transport hint for that profile
- `profiles.<name>.environment_strategy`: environment setup hint for that profile
- `profiles.<name>.network_profile`: human-readable network hint such as `plain-http`, `watt-hosts`, or `ssh-fallback`
- `profiles.<name>.use_watt`: whether the profile is explicitly marked as using WATT/Hosts routing
- `fallback_conda_prefix`: shared fallback prefix for self-hosted environments

Recommended usage:

1. Keep `active_profile: self-hosted-watt` as the default repository setting while the local network still relies on WATT/Hosts acceleration for stable unattended GitHub access
2. Switch to `self-hosted-http` only after plain direct HTTPS has been verified stable enough for unattended automation without WATT/Hosts assistance
3. Switch to `self-hosted-ssh` only when the runner network needs the `ssh.github.com:443` fallback path for git checkout
4. Use `github-hosted` as the slow-but-stable baseline when self-hosted networking is not trustworthy
5. Keep the rest of the workflow files unchanged; they read the mode and checkout transport through the shared runner resolver outputs

## Migration note for self-hosted HTTPS checkout

The current migration strategy is intentionally conservative:

- default self-hosted checkout currently prefers the `self-hosted-watt` profile because the local network still depends on WATT/Hosts acceleration for stable GitHub access
- SSH checkout logic and the `ACTIONS_CHECKOUT_SSH_KEY` secret are retained as fallback and are not removed yet
- `self-hosted-http` remains available as the plain HTTPS fallback once direct unattended access becomes reliable enough
- observe a few workflow runs before any deeper cleanup, focusing on:
  - checkout duration
  - checkout failure rate / retry frequency
  - whether the SSH secret is still used in practice
- only after plain direct HTTPS stays stable for those runs should you consider changing the profile defaults inside `.github/runner-config.yml` or the fallback defaults inside `.github/actions/resolve-runner-config/action.yml`