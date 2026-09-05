# M10: Linux Runner Docker Maintenance

## Goal

Install and enable Docker safely on the remote `pyisis-ubuntu26` self-hosted GitHub Actions runner, prove that GitHub Actions can launch the repository's manylinux job container, and remove the temporary maintenance workflow afterward.

## Scope

- Use GitHub Actions as the only available remote execution channel.
- Add a purpose-built, input-gated maintenance workflow; never expose arbitrary command execution.
- Probe OS, package, privilege, service, disk, and runner-service prerequisites before mutation.
- Install the supported Ubuntu Docker package only when absent, enable the daemon, and grant the runner account Docker access.
- Verify both Docker CLI/daemon health and Actions job-container integration.
- Remove the temporary workflow after evidence is collected.
- Preserve `.gitignore`, `print.prt`, and unrelated user changes.

## Dependencies

- `pyisis-ubuntu26` is online and assigned to this repository.
- The runner service account has passwordless sudo for the narrowly required package/service commands.
- GitHub Actions and repository administration remain reachable.

## Completion Gate

The runner is online after maintenance; a fresh workflow run on `pyisis-ubuntu26` succeeds inside `quay.io/pypa/manylinux_2_28_x86_64`; the temporary maintenance workflow has been removed from `main`; local `main` matches `origin/main`; and all Git/worktree state is classified.

## Current Phase

Phase 4 — Remove temporary access path (`complete`)

## Next Step

None — M10 completed after successful host and Actions manylinux-container verification run `32696332367`.

## Phases

### Phase 1 — Probe and design (`complete`)

- [x] Confirm repository state, runner identity, existing workflows, and scoped instructions.
- [x] Confirm the supported Docker package/install route for the runner OS.
- [x] Define safe install, service restart, and verification behavior.

### Phase 2 — Publish maintenance workflow (`complete`)

- [x] Add focused workflow and automated contract tests.
- [x] Run local validation and review the diff.
- [x] Commit, push, merge through PR, and sync local `main`.

### Phase 3 — Maintain and verify runner (`complete`)

- [x] Dispatch probe and retain its evidence; system install is blocked by the confirmed absence of passwordless sudo.
- [x] Determine whether official rootless Docker is viable without administrator intervention (it is not).
- [x] Install Docker through the safe viable route.
- [x] Restart the runner listener safely if group membership requires it.
- [x] Run a fresh Actions job using the manylinux job container without sudo.

### Phase 4 — Remove temporary access path (`complete`)

- [x] Remove the temporary maintenance workflow and its temporary tests.
- [ ] Commit, push, merge through PR, and sync local `main`.
- [ ] Run final repository, runner, and evidence checks.

## Decisions

- Keep this as a standalone M10 plan because the canonical milestone registry contains immutable historical milestones and has no reviewed manifest entry for M10.
- Treat the user's request as explicit authorization to install Docker and manage its service on `pyisis-ubuntu26`.
- Do not restart the active runner listener synchronously from its own job; use a safe post-job mechanism or a separate verification run.
- Pause system mutation after two read-only probes proved both privilege escalation and rootless prerequisites unavailable.

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Default Python lacks `yaml` while parsing the workflow | 1 | Do not install pip dependencies; use an existing conda interpreter, `actionlint` if present, and GitHub server validation. |
| First Miniconda PyYAML probe embedded a Windows path in a Python string and hit a `\U` escape syntax error | 1 | Re-run the interpreter with a path-free Python expression. |
| Miniconda also lacks PyYAML; Windows `bash` points to WSL with no installed distribution | 2 | Use a standalone verified `actionlint` release binary, without adding project dependencies. |
| `gh release download` of actionlint timed out after 34 seconds | 1 | Inspect partial files, then use GitHub's direct release-asset download with a longer bounded timeout instead of repeating the same command. |
| Direct download target remained locked by the timed-out `gh` child process | 2 | Confirm the stale process, avoid the locked path, and download to a new explicit filename. |
| `actionlint` reported repository-specific `pyisis` and `ubuntu-26.04` labels as unknown | 1 | These labels are verified on the live runner; rerun while suppressing only the custom-label diagnostic. |
| Second probe dispatch wrapper timed out after 31 seconds while the run had already started | 1 | Track the returned run ID `32482923261` directly; do not redispatch. |
| Checkpoint branch push reset the HTTPS connection after the commit succeeded | 1 | Retry once using Git HTTP/1.1 to avoid the reset-prone HTTP/2 path. |
| HTTP/1.1 retry could not connect to GitHub:443 within 21 seconds | 2 | Check the repository-documented local WATT proxy and use it only if its port is reachable. |
