# Windows ISIS 9 Native APP Implementation Milestone

# Task Plan: Build and validate the Windows ISIS native APP release

## Goal

Complete milestone `windows-isis9-m06-native-app-implementation` and satisfy its declared evidence gate.

## Scope

- Work only on this milestone and its declared source-plan tasks.
- Preserve unrelated changes and prior experiment outputs.

## Source Plans

- `docs/superpowers/plans/2026-08-17-csv2table-native-app-unification.md`
- `docs/superpowers/plans/2026-08-16-windows-isis-native-app-distribution.md`

## Dependencies

- None

## Completion Gate

The csv2table Python and in-process binding exception is removed; native csv2table behavior is verified for ISIS 9 and ISIS 10 on Windows and Linux; and one deterministic Windows 11 x64 portable ZIP containing the tracked 150 ISIS 9 CLI APPs plus qnet passes unit, dependency-closure, clean-extraction CLI/GUI/data, hash, inventory, and zero-skip validation with the declared retained reports.

## Next Step

Extract the shared Windows PE dependency engine for the portable native APP distribution.

## Current Phase

Phase 1: csv2table native APP unification

## Phases

### Phase 1: csv2table native APP unification

- [x] Remove the Python facade, private APP runner, and in-process ISIS 10 adapter
- [x] Classify csv2table as native-app in generated ISIS 10 inventories and current documentation
- [x] Complete independent review of the synchronized 150-APP Windows baseline
- [x] Add the cross-platform native-process behavior validator
- [x] Collect ISIS 9/10 × Windows/Linux native csv2table evidence
- **Status:** complete

### Phase 2: Windows native APP portable distribution

- [ ] Extract the shared Windows PE dependency engine
- [ ] Lock and validate the 151-APP release contract
- [ ] Add package-relative launchers
- [ ] Stage the curated payload and create a deterministic archive
- [ ] Add strict archive and evidence validation
- [ ] Implement the clean-extraction runtime matrix and orchestrator
- **Status:** in_progress

### Phase 3: Release artifact and milestone closure

- [ ] Build the Windows ISIS 9 portable ZIP and retained reports
- [ ] Pass clean Windows 11 x64 validation with zero required skips
- [ ] Produce fresh structured milestone evidence and close M06
- **Status:** pending

## Decisions Made

| Decision | Rationale |
|---|---|
| Treat csv2table only as a native APP | ISIS 9/10 and Windows/Linux share the executable/XML boundary; PyISIS publishes no special facade or runner. |
| Preserve M05 as an immutable archived prerequisite | Completed milestone state cannot be reopened; M06 owns implementation. |
| Permit deterministic manifest-only priority refresh | Fixed upstream source downloads repeatedly truncated; the approved mode updates only membership fields while preserving all source-derived fields and ranking policy. |
| Accept the ISIS 10 PROJ full-suite error as an unrelated environment concern | Both ISIS 10 extension build/import and the focused csv2table validator passed; the sole broad-suite error is IProj failing to open the missing `asp370/share/proj` data directory. |
| Bind the native distribution to the current manifest's normalized-LF hash | The earlier design hash predates the reviewed csv2table manifest synchronization; LF normalization preserves one exact content identity across Windows and Linux checkouts. |
| Use an internal PowerShell argv worker behind public CMD launchers | Native CMD `shift` does not alter `%*`, `%1..%9` truncates arguments, and `call` re-expands metacharacters; array splatting preserves argv without string evaluation. |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| Windows ISIS 9 prefix verification could not initially load `isis.dll` | 1 | Diagnose with `dumpbin`; provide the complete conda runtime PATH before rerunning. The 150-APP batch then passed. |
| Fixed ISIS 10 source restore repeatedly reset, stalled, or produced truncated archives | 1-4 | Reject incomplete inputs and add the user-approved tested `--refresh-manifest-only` path; generated inventory changed only csv2table membership fields. |
