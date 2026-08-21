# M10 Progress

## Session 2026-08-21

### Completed

- Read the milestone-session-manager contract and planning-with-files procedure.
- Ran planning session catch-up; no unsynchronized context was reported.
- Ran canonical milestone verification successfully.
- Classified initial Git state: `main...origin/main`, unrelated guarded `print.prt` modified.
- Created the standalone M10 durable plan.
- Inspected existing runner/wheel workflows and focused workflow tests.
- Confirmed from official Docker documentation that Docker Engine supports Ubuntu 26.04 and recorded the official apt-repository route.
- Confirmed from official GitHub documentation that Docker and service-account socket access are required for self-hosted job containers.
- Added the input-gated temporary maintenance workflow and five focused safety-contract tests.
- Ran the focused unit test: 5 passed, 0 failed, 0 skipped.
- Published the workflow through PR #374 and synchronized local `main` to merge commit `55b0153e915a3ed92b25039d28923524690bb459`.
- Cancelled the redundant post-merge PR gate and main CI runs to release the single Linux runner for maintenance.
- Completed read-only probe run `32482513889` successfully and retained its host evidence.
- Reviewed official rootless Docker requirements and extended the fixed probe with subordinate-ID, user-namespace, AppArmor, runtime-directory, and linger checks.

### Changed Files

- `.planning/linux-runner-docker-maintenance-m10/task_plan.md`
- `.planning/linux-runner-docker-maintenance-m10/findings.md`
- `.planning/linux-runner-docker-maintenance-m10/progress.md`

### Commands and Results

- `session-catchup.py`: exit 0, no unsynchronized context.
- `verify_milestones.py --repo <repo>`: pass.
- `git status --short --branch`: `main...origin/main`; `print.prt` modified.
- `python -m unittest tests.unitTest.linux_runner_docker_maintenance_workflow_unit_test -v`: 5 passed.
- Default-Python PyYAML parse: not run because the `yaml` module is absent; no dependency was installed.
- Downloaded actionlint v1.7.12 and verified its release ZIP SHA-256 against the publisher checksum; initial lint reached semantic validation and reported only the two live repository-specific labels as unknown.
- `actionlint` with only the verified custom-label diagnostic ignored: pass.
- PR #374: merged.
- Probe run `32482513889`: success; Ubuntu 26.04/x86_64, 74 GB free, Docker absent, runner service identified, passwordless sudo denied.
- Extended workflow `actionlint`: pass; focused tests: 6 passed, 0 failed, 0 skipped.

### Next Step

Evaluate official rootless Docker prerequisites; proceed only if it can safely satisfy Actions job-container requirements without administrator access.

### Reboot Check

- Where: Phase 3, maintain and verify runner.
- Goal: Docker-capable `pyisis-ubuntu26` with Actions job-container proof.
- Next: inspect workflows/instructions and package support.
- Known blocker: no direct SSH and no passwordless sudo; rootless viability is under evaluation.
