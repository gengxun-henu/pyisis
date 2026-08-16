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
- **Status:** pending

## Decisions Made

| Decision | Rationale |
|---|---|
| Make M05 a design milestone before implementation | ZIP versus installer, exact APP inventory, launchers, and release mechanics were intentionally deferred until after M04; fixing them in an approved design prevents premature artifact contracts. |
| Require at least `reduce`, `jigsaw`, and `qnet` | These are the user-approved minimum native APP surface and remain outside all PyISIS wheels. |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
