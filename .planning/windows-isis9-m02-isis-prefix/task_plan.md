# Windows ISIS 9.0.0 and PyISIS Native Build Milestones

# Task Plan: Build and verify the ISIS 9.0.0 native prefix

## Goal

Complete milestone `windows-isis9-m02-isis-prefix` and satisfy its declared evidence gate.

## Scope

- Work only on this milestone and its declared source-plan tasks.
- Preserve unrelated changes and prior experiment outputs.

## Source Plans

- `docs/superpowers/specs/2026-08-15-windows-isis9-pyisis-build-design.md#milestones`
- `ports/windows/isis/README.md`

## Dependencies

- `windows-isis9-m01-environment`

## Completion Gate

The patched upstream ISIS 9.0.0 source builds and installs with MSVC, the prefix
verification passes, representative ISIS applications pass their smoke tests,
and all 150 main-branch Windows APP manifest entries pass the ISIS 9 batch
startup gate plus its selected real Cube operations.

## Next Step

None — milestone complete.

## Current Phase

Phase 1

## Phases

### Phase 1: Milestone execution

- [x] Fetch ISIS tag `9.0.0` at commit `950a5606ffeaa13ddb40101fbf25a8737e88902a`
- [x] Apply the tracked ISIS 9 Windows patch queue
- [x] Configure and build the complete ISIS 9 Windows target set with MSVC/Ninja and the user-requested `-j 24`
- [x] Install and pass `verify_isis_prefix.ps1`
- [x] Pass `test_isis_apps_smoke.ps1`
- [x] Confirm `windows-app-manifest.json` contains exactly 150 ISIS 9 supported APPs
- [x] Pass `test_isis_app_batch_smoke.ps1 -IsisVersion 9.0.0` for all 150 executables and selected Cube operations
- [x] Produce and verify the declared milestone evidence, including the additional 150-APP batch result
- **Status:** complete

## Decisions Made

| Decision | Rationale |
|---|---|
| Lock the expanded APP gate to the 150-entry manifest already present on `main` | The user requested 150 APPs. PR #356 is an unmerged, conflicting 169-APP ISIS 10 follow-up and is outside this ISIS 9 build scope. |
| Run Ninja with 24 jobs and make 24 the repository C++ build cap | The user explicitly replaced the original single-job build direction; defaults now use `min(24, available logical processors)` so smaller hosts use their full capacity. |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| Invoking `fetch_isis.ps1 -?` ran the script's defaults, and the inspection command timed out after 10 seconds during clone | 1 | Root cause confirmed from process and Git state: clone metadata/HEAD completed but sparse checkout/reset did not. Resume through the script's existing-checkout path; do not delete or force-recreate the source. |
| Existing-checkout resume stalled during partial-clone lazy blob fetch: established GitHub HTTPS connection, but its temporary pack remained 0 bytes for about seven minutes | 2 | Stopped only the four verified child Git processes, preserved the partial checkout, and selected the documented bounded archive fallback in a separate source directory. |
| Archive fallback exhausted four bounded curl attempts; every `github.com:443` connection timed out with exit 28 | 3 | Stop network-parameter retries under the 3-strike rule. Search read-only for a local pinned source/object copy; otherwise checkpoint the external-network blocker. |
| First checkpoint close failed structural verification because `Next Step` spanned multiple Markdown lines | 1 | Read the milestone contract and collapsed the action to exactly one plain-text line without changing its meaning. |
| A resumed archive fetch transferred intermittently, then the outer 15-minute runner timed out while an orphaned curl process truncated the archive to 0 bytes and reconnected | 4 | Verified and stopped only the orphaned curl PID. A successful HTTP 302 probe is insufficient; checkpoint until a sustained archive payload transfer is available. |
| A fresh 1 MiB `curl --range` payload probe to the ISIS archive received 0 bytes and failed with `curl: (56) Recv failure: Connection was reset` after 29.21 seconds | 5 | Do not reactivate or retry the full fetch. The exact sustained-payload blocker remains until a nonzero bounded payload probe succeeds. |
| The first `Invoke-WebRequest` download was truncated at 73,957,376 bytes because its command timeout was 10 seconds | 1 | Preserved it for diagnosis, reran to a new path with a 15-minute command timeout, and obtained a tar-valid 246,082,553-byte archive. |
| `git apply` rejected an exact upstream blob because Windows Git had checked out the patch file with CRLF line endings | 1 | Added a failing regression assertion, then made `apply_patches.ps1` use `--ignore-space-change`; all eight patches applied successfully. |
| The representative APP smoke cannot launch `catlab.exe`; the executable is removed during every first launch | 4 | Confirmed install and prefix verification pass, the build-tree executable remains intact, but original-name, renamed, and `/RELEASE` copies all disappear on launch after about 60 seconds. Windows Defender, AppLocker, and Code Integrity have no matching event; the registered third-party antivirus products are Lenovo/火绒 and 360. The local security product must allow the build/prefix executables before the gate can resume. |
| The first trust-directory claim did not yet affect execution | 1 | Inspected the actual 360 Trojan Scan trusted-area UI. After `D:\code\pyisis` appeared there at 18:07:41, a fresh reinstall and `catlab -help` both returned 0 and the executable remained present; the subsequent 9-command APP smoke passed. |
| ISIS 9 rejected `crop overhang=shrink` and `csv2table coltypes=(Double,Text)` in the shared batch gate | 2 | Verified both parameters are absent from the installed ISIS 9 APP XML. Added an installed-XML capability helper with RED/GREEN coverage; the batch now omits unsupported parameters and uses numeric-only CSV data when `COLTYPES` is unavailable. The fresh 150-APP plus Cube gate passed. |
