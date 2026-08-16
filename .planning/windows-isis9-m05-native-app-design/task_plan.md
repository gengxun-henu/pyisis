# Windows ISIS 9 Native APP Distribution Milestone

# Task Plan: Design the native Windows ISIS APP release

## Goal

Complete milestone `windows-isis9-m05-native-app-design` and satisfy its declared evidence gate.

## Scope

- Work only on this milestone and its declared source-plan tasks.
- Preserve unrelated changes and prior experiment outputs.

## Source Plans

- `docs/superpowers/specs/2026-08-16-windows-pyisis-wheelhouse-design.md#M05-Native-ISIS-Windows-APP-Distribution`

## Dependencies

- None

## Completion Gate

An approved implementation-ready design fixes the Windows package format, explicit first-release APP inventory including reduce, jigsaw, and qnet, DLL/plugin/preferences/XML/data and launcher layout, clean-machine launch matrix, artifact/report names, hashes, and cleanup rules without placing standalone APPs in the PyISIS wheels.

## Next Step

Activate M05 in a new milestone session and brainstorm the package format and explicit first-release APP inventory.

## Current Phase

Phase 1

## Phases

### Phase 1: Milestone execution

- [ ] Produce and verify the declared milestone evidence
- **Status:** in_progress

## Decisions Made

| Decision | Rationale |
|---|---|
| Make M05 a design milestone before implementation | ZIP versus installer, exact APP inventory, launchers, and release mechanics were intentionally deferred until after M04; fixing them in an approved design prevents premature artifact contracts. |
| Require at least `reduce`, `jigsaw`, and `qnet` | These are the user-approved minimum native APP surface and remain outside all PyISIS wheels. |
| Use a portable ZIP as the first-release package format | The target audience is scientific/developer users who prioritize zero-install portability. |
| Expose exactly 151 first-release APPs | The public inventory is the tracked 150 CLI APP manifest plus `qnet`; helper executables are runtime implementation details, not additional supported APPs. |
| Ship minimal bootstrap/test ISISDATA with an external override | The archive remains bounded and self-verifying while full scientific workflows can point to a separately maintained data tree. |
| Centralize launch environment setup | Ship `isis-shell.cmd`, `isis-app.cmd <name> ...`, and `qnet.cmd`; retain separate runtime directories and do not require users to configure PATH manually. |
| Limit the first-release platform to Windows 11 x64 | This matches the verified build environment and avoids unverified Windows 10 or ARM64 support claims. |
| Build one curated portable archive | Stage the declared APP/runtime/data closure into one atomic ZIP; do not copy the full development prefix or require users to compose multiple archives. |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
