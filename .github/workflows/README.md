# Pybind workflow guide

This directory currently contains several workflow roles.

## Shared checkout rule

Workflow runner behavior is now selected from `.github/runner-config.yml`.

Supported modes:

- `self-hosted`
- `github-hosted`

Supported named profiles:

- `pyisis-ubuntu26-isis9` — repository-dedicated Ubuntu 26.04 / ISIS 9 runner with 16-way builds and a 20G compiler cache
- `pyisis-ubuntu26-isis10` — the same Ubuntu 26.04 host using the pre-provisioned `asp370` / ISIS 10 / CPython 3.13 environment
- `self-hosted-http` — self-hosted HTTPS path for plain direct network access when unattended GitHub connectivity is stable enough
- `self-hosted-watt` — current default self-hosted HTTPS path for WATT/Hosts-accelerated GitHub access
- `self-hosted-ssh` — self-hosted SSH checkout fallback over `ssh.github.com:443`
- `github-hosted` — GitHub-hosted baseline runner with micromamba environment setup

In `self-hosted` mode, workflows follow the checkout transport configured in `.github/runner-config.yml` and reuse the pre-provisioned local conda/ISIS environment. The current recommended default is HTTPS so self-hosted runners can benefit from local proxy or acceleration tools when available.

In `github-hosted` mode, workflows use the configured GitHub-hosted runner image (currently `ubuntu-22.04` by default), checkout over normal HTTPS, and create a micromamba-based build environment inside the workflow.

The shared runner resolution pipeline is:

- `.github/runner-config.yml` — top-level switch and mode-specific defaults
- `.github/scripts/resolve_runner_config.py` — parses and validates runner profiles
- `.github/actions/resolve-runner-config/action.yml` — exposes normalized outputs to workflows
- `.github/workflows/reusable-runner-config.yml` — bootstrap workflow used by top-level workflows before scheduling mode-dependent jobs

The GitHub-hosted environment spec lives in `.github/conda/pybind-ci-environment.yml`.

All workflows that clone this repository are expected to follow the transport selected by `.github/runner-config.yml`.

Required repository or organization secret:

- `ACTIONS_CHECKOUT_SSH_KEY`: private SSH key with read access to this repository

Note: this secret is required only when the active runner mode uses SSH checkout.

Implementation notes:

- `./.github/actions/normalized-safe-checkout` now supports a post-checkout mode via `skip-checkout: "true"`, so workflows can do a plain `actions/checkout@v7` first and then reuse the local action for transport cleanup validation and diagnostics
- heavyweight build/test workflows are being migrated to that pattern: explicit checkout in the workflow, then `normalized-safe-checkout` as a non-first-step local action
- lightweight `github-hosted` issue/PR helper workflows should prefer plain `actions/checkout@v7` instead of calling a checkout-owning local action as the first step, because local actions are resolved from the checked-out workspace
- when the resolved checkout transport is `ssh`, workflows configure `~/.ssh/config` so `github.com` is routed to `ssh.github.com` on port `443`
- when the resolved checkout transport is `ssh`, `actions/checkout@v7` receives `ssh-key: ${{ secrets.ACTIONS_CHECKOUT_SSH_KEY }}` to avoid fallback to HTTPS
- when the resolved checkout transport is `https`, workflows skip the SSH setup step and use the default HTTPS checkout flow
- reusable workflows that need checkout still receive secrets via `secrets: inherit`, but they only require `ACTIONS_CHECKOUT_SSH_KEY` when the resolved checkout transport requests SSH checkout
- workflows that still need pre-checkout normalization/preflight/self-heal should keep those steps in the workflow job before `actions/checkout@v7`, then invoke `normalized-safe-checkout` in post-checkout mode for diagnostics

## `ci-pybind.yml`

Use this as the repository-level baseline CI.

Purpose:
- validate normal pushes to `main` and manual CI dispatches
- verify that the repository can configure, build, run the unit-test suite, and run `tests/smoke_import.py`
- act as the broad regression gate for ongoing development after changes land on the mainline

Characteristics:
- triggered by push and workflow_dispatch
- broad repository coverage
- builds and smoke-tests both ISIS 9 (`asp360_new`) and ISIS 10 (`asp370`) on the dedicated self-hosted runner, then runs the complete CTest suite independently against each cached build
- binding inventory reporting and build/smoke start in parallel after runner resolution, so inventory logging does not delay the build path
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
- when the resolved mode is `self-hosted`, the reusable path now prefers a persistent cross-run local build cache plus incremental reconfigure/build instead of forcing a clean build every time
- when `ccache` is available on the self-hosted machine or fallback conda prefix, it is configured automatically to accelerate repeated C++/pybind compilations

## `wheels.yml`

Use this as the platform packaging and release matrix, not as the daily PyISIS
development gate.

Routing policy:

- ordinary changes under `src/`, `python/`, `CMakeLists.txt`, and general tests
  are handled by `agent-pybind-pr-gate.yml` and do not trigger wheel builds
- `ports/linux/` changes run only the ISIS 9/10 Linux manylinux lanes
- `ports/windows/` changes run only the ISIS 9/10 Windows wheel lanes
- shared packaging changes under `packaging/`, `tools/packaging/`,
  `pyproject.toml`, and packaging/runtime workflow tests run both platforms
- manual dispatch runs the complete Linux and Windows release matrix; publishing
  remains restricted to `main`
- each Linux wheel is clean-installed on Ubuntu 22.04, 24.04, and 26.04 for
  both ISIS 9 and ISIS 10

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

Use this as the manual single-class validation workflow.

Purpose:
- run validation for one upstream ISIS C++ class at a time
- auto-resolve inventory/test context from local CSV files
- validate either the manually selected SHA or an explicit bootstrap task branch created from an issue
- enforce the retry budget for task execution on the existing self-hosted conda/ISIS environment

Characteristics:
- triggered by `workflow_dispatch`
- centered on `target_class`, with optional issue, PR, git-ref, and unit-test override inputs
- validates build + unit + smoke + progress consistency
- intended for manual spot-checks, focused diagnostics, or ad hoc follow-up validation rather than the default issue queue path
- now follows `.github/runner-config.yml` and can either reuse the local conda/ISIS environment or create a GitHub-hosted micromamba environment
- on `self-hosted`, it now exposes optional `clean_build`, `reuse_build_cache`, and `build_jobs` inputs so manual validation can opt into incremental rebuilds and configurable parallelism

## `bridge-pybind-issue-to-pr.yml`

Use this as the explicit bridge between an actionable issue and an editable draft PR.

Purpose:
- consume the parsed issue context after `ready-for-agent`
- create or reuse a stable bootstrap branch for that task
- open or refresh a draft PR that carries the issue context forward into the coding phase
- stop after the draft PR handoff so a human or GitHub coding agent can continue on that branch

Characteristics:
- triggered by `workflow_dispatch`, normally from `dispatch-pybind-task-from-issue.yml`
- idempotent for the same issue number and target class
- writes a backlink comment on the issue with the draft PR URL and branch name
- keeps the issue queue and PR lane explicitly connected inside the repository automation
- the bridge workflow itself is lightweight and should prefer `github-hosted` plus plain `actions/checkout@v7` so bootstrap branch and draft PR creation do not depend on self-hosted infrastructure or local-action bootstrap ordering

## `agent-pybind-pr-gate.yml`

Use this as the PR-only automatic gate.

Purpose:
- validate pull requests that change bindings, tests, workflow logic, or progress metadata
- ensure the repository still builds and passes smoke/unit checks on the existing local environment

Characteristics:
- triggered by `pull_request`
- gate/checker only; it does not dispatch tasks or comment on issues
- same-repository PRs opened by repository owner `gengxun-henu` run separate ISIS 9 and ISIS 10 build/smoke and unit-test lanes; the single physical runner executes them one at a time
- PRs opened by other collaborators, forks, or Dependabot keep the GitHub-hosted ISIS 9 path and never execute their code on the persistent self-hosted machine
- follows `.github/runner-config.yml` instead of pinning a runner profile, so the default PR gate can use the same `self-hosted-watt` profile as heavier build/test workflows
- avoids full-history checkout for change summaries and metadata audit by reading the PR changed-file list once through the GitHub API
- uses GitHub artifacts on `github-hosted`, but reuses the local build cache directly on `self-hosted` so the unit-test job does not pay artifact upload/download overhead

## `dispatch-pybind-task-from-issue.yml`

Use this as the queue bridge between the issue form and the draft-PR bridge workflow.

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
- this workflow is intentionally lightweight and should prefer `github-hosted` plus plain `actions/checkout@v7` so issue autofill is not blocked by self-hosted WATT checkout problems or local-action bootstrap failures

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
5. Let the bridge workflow open or refresh the bootstrap draft PR and stop there for handoff
6. Let the GitHub agent or a human contributor push coding changes to the draft PR branch
7. Let `agent-pybind-pr-gate.yml` act as the narrow PR gate for agent-task changes
8. Keep `ci-pybind.yml` as the broad repository-level CI gate on merges to `main` and manual dispatches

In short:
- `.github/runner-config.yml` = top-level runner mode switch for all workflows
- `dispatch-pybind-task-from-issue.yml` = queue bridge from issue form to issue/PR bridge workflow
- `bridge-pybind-issue-to-pr.yml` = explicit issue -> bootstrap branch -> draft PR bridge
- `agent-pybind-task.yml` = manual narrow validation workflow with retry budget, now branch-aware
- `agent-pybind-pr-gate.yml` = PR-only automatic gate for task-related changes
- `agent-pybind-task-draft.yml` = deprecated legacy fallback during migration
- `ci-pybind.yml` = broad repository regression check for pushes/manual runs
- `reusable-pybind-build.yml` = shared build/smoke plumbing for CI and PR gate
- `runner-host-sanity-check.yml` = manual host-level git/ssh/proxy hygiene audit

Practical split:

- keep heavy build/test workflows on `self-hosted-watt` when the local ISIS/conda environment and domestic-network acceleration are required
- keep lightweight issue/autofill/dispatch workflows on `github-hosted` so queue handling, issue comments, and draft PR creation do not depend on self-hosted checkout stability
- let `agent-pybind-pr-gate.yml` follow `.github/runner-config.yml`; if self-hosted action bootstrap becomes flaky again, use an explicit temporary runner-profile override rather than hard-pinning the PR gate indefinitely

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
- `bridge-pybind-issue-to-pr.yml` creates or reuses the bootstrap branch, opens/updates the draft PR, comments back on the issue, and then waits for a human or GitHub coding agent to continue on that branch

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
- `profiles.<name>.build_jobs`: positive self-hosted CMake/Ninja parallelism
- `profiles.<name>.ccache_max_size`: compiler-cache capacity limit
- `profiles.<name>.isis_major`: selected ISIS major line
- `profiles.<name>.python_abi`: selected CPython ABI
- `profiles.<name>.fallback_conda_prefix`: optional per-profile conda/ISIS prefix, used by the dedicated ISIS 9 and ISIS 10 profiles
- `fallback_conda_prefix`: shared fallback prefix when the selected profile does not override it

Recommended usage:

1. Keep `active_profile: pyisis-ubuntu26-isis9` for trusted mainline and repository-owner PR builds.
2. Use `github-hosted` for PRs from other collaborators, forks, and Dependabot; they must not execute on the persistent host.
3. Switch to `self-hosted-watt` only when WATT/Hosts acceleration is running reliably for unattended automation.
4. Switch to `self-hosted-ssh` only when checkout needs the `ssh.github.com:443` fallback.
5. Keep lightweight issue/queue automation on GitHub-hosted runners.

## Repository-dedicated Ubuntu 26 runner operations

Phase 1 uses these fixed values:

```text
Repository: https://github.com/gengxun-henu/pyisis
Runner name: pyisis-ubuntu26
Runner account: pyisis-runner
Runner application: /opt/actions-runner-pyisis
Runner HOME/cache root: /var/lib/pyisis-runner
Conda prefix: /home/gengxun/miniconda3/envs/asp360_new
ISIS 10 prefix: /home/gengxun/miniconda3/envs/asp370
Labels: self-hosted,linux,x64,pyisis,ubuntu-26.04,isis9,isis10
Build jobs: 16
ccache max size: 20G
Build-cache retention: 7 days
```

Run the read-only readiness check before registration or after host changes:

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
python scripts/check_self_hosted_runner.py \
  --conda-prefix /home/gengxun/miniconda3/envs/asp360_new \
  --expected-jobs 16 \
  --expected-isis-major 9 \
  --expected-python 3.12 \
  --require-ccache \
  --json

conda activate asp370
python scripts/check_self_hosted_runner.py \
  --conda-prefix /home/gengxun/miniconda3/envs/asp370 \
  --expected-jobs 16 \
  --expected-isis-major 10 \
  --expected-python 3.13 \
  --require-ccache \
  --json
```

The host environment must provide both `ninja` and `ccache`. Install them with
Conda only after explicit approval because this mutates the shared environment.
The runner writes its build trees and compiler cache below
`/var/lib/pyisis-runner/.cache/pyisis-gha`; it treats the Conda environment as
read-only.

Manage registration under `Settings → Actions → Runners`. The one-hour
registration token must be entered interactively and must never be stored in
the repository or logs. The service needs outbound HTTPS access only; no
inbound SSH port is required.

Useful service diagnostics after registration:

```bash
cd /opt/actions-runner-pyisis
sudo ./svc.sh status
systemctl list-units --type=service | grep actions.runner
journalctl --unit 'actions.runner.*pyisis*' --since today
```

If a run fails, inspect the Actions summary and service logs first. A cache
metadata mismatch should trigger a clean rebuild, not deletion outside the
runner cache root. Do not delete the checkout, Conda prefix, `.gitignore`, or
`print.prt` as a recovery step.

The PR gate routes only same-repository PRs opened by `gengxun-henu` to this
runner. Other collaborators, forks, and Dependabot resolve to `github-hosted`;
never replace this rule with
`pull_request_target` plus execution of PR code.

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
