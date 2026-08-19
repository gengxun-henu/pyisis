# Windows ISIS 9 Native APP Implementation Milestone

# Findings: Build and validate the Windows ISIS native APP release

## Verified Facts

- Milestone ID: `windows-isis9-m06-native-app-implementation`.
- M05 is complete and archived under `.planning/archive/windows-isis9-native-app-m05/`; its registry contains fresh design completion evidence.
- `0a1781d2` removed `isis_pybind.csv2table`, `pyisis.csv2table`, `_isis_core._csv2table_native`, and the csv2table-only Python APP runner.
- `011f8d15` classifies `csv2table.h` as `native-app` while preserving it in the complete ISIS 10 discovered-header/function inventory.
- `251d0fb5` synchronizes the tracked Windows manifest and priority outputs at 150 CLI APPs.
- A real Windows ISIS 9 batch smoke passed all 150 executable startup probes; native `csv2table` and `tabledump` both exited 0 and produced a nonempty table dump.
- Task 3 specification and quality review passed; the reviewer recorded one deferred CLI-diagnostic Minor and no Critical/Important issue.
- Task 4 added and cleanly reviewed a native-process validator with seven passing unit tests; it publishes atomic schema-1 JSON and treats every prerequisite/behavior check as required.
- Task 5 recorded genuine 3/0/0 native validator results for all four ISIS 9/10 x Windows/Linux cells in `docs/superpowers/evidence/2026-08-17-csv2table-native-app-matrix.json`; raw-report hashes and GitHub run provenance were independently verified.
- The csv2table final review is Ready after `d8409ad2` added the explicit high-level API absence gate and corrected the ISIS 10 binding metadata.
- The original native-distribution design hash identified the pre-csv2table manifest. The current reviewed 150-APP manifest has Git/normalized-LF SHA-256 `bca645e1bf9ba3594ef48be0cb3fbec642a98da1e6f1b91b31a4aaa9519987d5`; its Windows working-tree raw hash differs only because of line endings.
- The working tree contains an unstaged ISIS-generated `print.prt`; repository guardrails prohibit modifying, restoring, deleting, or staging it.
- On the QEMU TCG clean host, GUI startup can be much slower than on hardware: `reduce.exe` first appeared after 49.856 seconds and its visible window after 126.125 seconds. A 300-second bounded timeout preserves fail-closed behavior while accommodating this measured clean-host latency.
- The isolated `cnetref` failure was an outer Windows PowerShell `0xc0000005` crash. The same ZIP and launcher passed three consecutive `cnetref -HELP` runs after a fresh extraction; Windows Defender had also logged a `0xc0000005` in this guest, supporting classification as a TCG/guest transient rather than a deterministic payload fault.
- A `Nehalem-v1` QEMU CPU profile completed 250/250 fresh PowerShell process launches with zero failures and no Application Error events. Under that stable profile, the isolated Windows 11 guest passed the full 166-test native package matrix with zero failures or skips.
- The final clean-host raw report is SHA-256 `14c3c4e55a79a577924bba9d59a880f9792d01dfcee54504cc575822ad481a8d`; it records Windows 11 10.0.26200.0 AMD64, exact group counts `1/150/9/3/1/2`, and negative exits `[4,3]`.
- Strict validation retained ZIP SHA-256 `7ea41d54ba123d9f5a4aa57491a16ac3ebf1295010ec3e11df925ae4579b9e96`, dependency-report SHA-256 `426ff10ffa084815e196ac6248b4f8d71bbc83de34bb756a9853d6c413629738`, and final-validation SHA-256 `005b2de03d11876ed73eb348d133d0d6c97cc2d92dac58b52d8956c593924dc5`; the staging work directory was removed after publication.
- The Task 7 final review and full native-distribution final review are Ready with no findings. Fresh Windows-native regression is 73/73, and the six-module cross-host command's four errors are exclusively the already documented Windows absence of Linux `ldd`/`readelf` tools.
- Starting the configured `pyisis-windows11` runner proved its registration and labels are valid. The self-hosted job failed before package execution because the development machine contains `D:/code/pyisis/pyisis/build/windows/isis-prefix`, an explicitly forbidden clean-host path; this strengthens rather than replaces the isolated QEMU provenance requirement.

## Evidence-Based Inference

- The single ISIS 10 broad CTest error is isolated to missing PROJ data for IProj and does not invalidate the successful extension build/import or csv2table validator evidence.

## Unresolved Items

- `rank_isis_apps.py` still exposes a raw `ValueError` when normal ranking omits `--source-root`; final csv2table review accepted this as a deferred non-blocking Minor.

## Decisions

| Decision | Rationale |
|---|---|
| One milestone owns both csv2table normalization and the Windows native APP archive | The csv2table classification and 150-APP inventory are direct inputs to the approved 151-APP release contract. |
| Do not claim a platform cell from static inventory evidence | Every required cell must execute the native help and csv2table-to-tabledump behavior path. |
| Do not promote the local Windows 11 run to clean-host evidence | The final retained validation must bind a runtime report produced without the source checkout, conda prefix, or build tree. |

## Resources

- Canonical registry: `.planning/milestones.v1.json`
- Archived M05 registry: `.planning/archive/windows-isis9-native-app-m05/milestones.v1.json`
- csv2table plan: `docs/superpowers/plans/2026-08-17-csv2table-native-app-unification.md`
- native distribution plan: `docs/superpowers/plans/2026-08-16-windows-isis-native-app-distribution.md`
- SDD ledger: `.superpowers/sdd/2026-08-17-csv2table-native-app-unification/progress.md`
