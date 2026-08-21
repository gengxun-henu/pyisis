# Task Plan: Dual-version wheel release (M09)

## Goal

Publish the validated ISIS 9/10 Linux and Windows wheelhouses from an exact `main` commit, retain release-asset hashes, and verify installation from the published assets.

## Scope

- Reconcile M08 non-publishing evidence from successful Actions run `32447419640`.
- Determine the repository's supported release target, version/tag, and publishing inputs without guessing.
- Publish only through the tracked GitHub Actions release workflow.
- Verify the resulting GitHub release, asset inventory, SHA-256 hashes, and focused clean installs.
- Do not publish to PyPI or TestPyPI unless the tracked release contract explicitly requires it.

## Source Plans

- `.planning/post-m06-dual-version-wheel-revalidation-m08/`
- `.github/workflows/wheels.yml`
- Repository release metadata and existing GitHub releases/tags

## Dependencies

- PR #371 merged as `addb839dc0b2622931926c60265c6c47aedd650f`.
- Non-publishing wheel run `32447419640` completed successfully for all four build lanes and six Linux clean-install lanes.

## Completion Gate

The exact release commit has successful ISIS 9/10 Linux and Windows build/install evidence; the GitHub release and expected assets exist; downloaded published assets have retained SHA-256 hashes; focused installs from published assets pass; and Git state is classified without touching `print.prt`.

## Next Step

Commit the verified rc3 release contract, publish it through a PR, and merge it to `main` before sequential release dispatches.

## Current Phase

Phase 2: Publish

## Phases

### Phase 1: Freeze release identity and contract

- [x] Record the exact release commit, version/tag, workflow inputs, target registry, and expected assets.
- [x] Confirm no conflicting tag or release already exists.
- **Status:** completed 2026-08-21

### Phase 2: Publish

- [ ] Merge the verified rc3 release contract to `main` and freeze the resulting commit.
- [ ] Dispatch the tracked publishing workflow at the frozen commit, sequentially for ISIS 9 and ISIS 10.
- [ ] Monitor every required build, install, and publishing job to completion.
- **Status:** in progress

### Phase 3: Verify published assets

- [ ] Record the published release URL and complete asset inventory.
- [ ] Download published assets, retain SHA-256 hashes, and run focused clean-install verification.
- **Status:** pending

### Phase 4: Close milestone

- [ ] Update M08/M09 durable evidence and classify Git state.
- [ ] Commit and publish planning evidence without modifying guarded local files.
- **Status:** pending

## Decisions

- M09 is a standalone planning-with-files milestone because the verified canonical milestone registry contains only the immutable completed M06; it is not safe to hand-edit that registry.
- GitHub Actions is the only authorized publishing mechanism for this milestone.
- The two release-line dispatches must be sequential because workflow concurrency is `wheels-${{ github.ref }}` with `cancel-in-progress: true`.

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Canonical milestone registry does not include standalone M07/M08 | 1 | Preserve the verified registry and use the repository's existing standalone plan-directory convention for M09. |
| Combined 124-test local packaging run had four Linux-runtime staging errors on Windows because `ldd`/`readelf` are unavailable | 1 | Classify as host-tool mismatch, retain the 120 passing results, and run the release-contract subset locally; Linux staging remains covered by the required Linux Actions lanes. |
