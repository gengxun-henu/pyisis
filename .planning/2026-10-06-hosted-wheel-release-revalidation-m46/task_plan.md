# Task Plan: GitHub-hosted release revalidation (M46)

## Goal

Validate the dual-version wheel matrix with GitHub-hosted Linux and Windows runners after the Windows self-hosted runner was taken offline, then record release readiness.

## Phases

- [x] Run ISIS 9/10 Linux and Windows wheel matrix on hosted runners
- [x] Verify Ubuntu 22.04, 24.04, and 26.04 clean-install jobs
- [x] Verify Windows wheel build and isolated install jobs
- [x] Record artifact and workflow evidence
- [ ] Commit, PR, merge, and sync local main

## Next Step

Commit this evidence, open the M46 PR, merge it, and synchronize local `main`.
