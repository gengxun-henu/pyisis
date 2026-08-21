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

### Next Step

Commit the validated temporary workflow and tests, merge them to `main`, then dispatch the read-only probe.

### Reboot Check

- Where: Phase 2, publish maintenance workflow.
- Goal: Docker-capable `pyisis-ubuntu26` with Actions job-container proof.
- Next: inspect workflows/instructions and package support.
- Known blocker: no direct SSH; GitHub Actions is the maintenance channel.
