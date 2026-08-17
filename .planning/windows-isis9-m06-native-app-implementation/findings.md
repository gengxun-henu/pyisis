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

## Evidence-Based Inference

- The single ISIS 10 broad CTest error is isolated to missing PROJ data for IProj and does not invalidate the successful extension build/import or csv2table validator evidence.

## Unresolved Items

- All seven Windows portable-distribution implementation tasks remain pending.
- M06 completion evidence has not yet been produced.
- `rank_isis_apps.py` still exposes a raw `ValueError` when normal ranking omits `--source-root`; final csv2table review accepted this as a deferred non-blocking Minor.

## Decisions

| Decision | Rationale |
|---|---|
| One milestone owns both csv2table normalization and the Windows native APP archive | The csv2table classification and 150-APP inventory are direct inputs to the approved 151-APP release contract. |
| Do not claim a platform cell from static inventory evidence | Every required cell must execute the native help and csv2table-to-tabledump behavior path. |

## Resources

- Canonical registry: `.planning/milestones.v1.json`
- Archived M05 registry: `.planning/archive/windows-isis9-native-app-m05/milestones.v1.json`
- csv2table plan: `docs/superpowers/plans/2026-08-17-csv2table-native-app-unification.md`
- native distribution plan: `docs/superpowers/plans/2026-08-16-windows-isis-native-app-distribution.md`
- SDD ledger: `.superpowers/sdd/2026-08-17-csv2table-native-app-unification/progress.md`
