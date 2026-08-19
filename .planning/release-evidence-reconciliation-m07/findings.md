# Findings: Release evidence reconciliation (M07)

## Verified Facts

- The canonical milestone registry verifies successfully and contains only the completed M06 milestone.
- The legacy `.planning/isis10-expansion` plan still lists a Windows ISIS 10 `mgs.dll`/SpiceQL blocker.
- Current committed Windows scripts contain a SpiceQL export patch, a `dumpbin` export assertion, and an MSVC downstream link probe for `SpiceQL::strSclkToEt`.
- The committed csv2table matrix records an ISIS 10 Windows native-APP result of 3 passed, 0 failed, and 0 skipped.
- The local `build/windows/` tree contains no ISIS 10 wheelhouse, final wheel validation report, or wheel checksum set. That absence is expected after build cleanup and does not establish that the wheel lane failed.
- `.github/workflows/wheels.yml` defines the Windows ISIS 10 CPython 3.13 prefix build, wheel build, isolated installation, metadata, DLL-dependency, and artifact-upload gates.
- GitHub release `v1.4.0rc2-isis10.0.0` is a published prerelease targeting `91c6c262c419985dac59e599405e0c6bbd5a35a5`; it contains the Windows CPython 3.13 wheelhouse with asset SHA-256 `16ec22857800231099921605e546f9fbeb358d9e1f7e970c393a6e95cf398b71`.
- The historical Wheels run `30066283510` failed on 2026-07-24 before the prerelease. The later Windows ISIS APP run `32043735505` completed successfully on 2026-08-17.
- The current HEAD includes M06-era Python/native-APP boundary changes after the prerelease commit, so historical release evidence must not be presented as a current-HEAD wheel validation.

## Unresolved Items

- Whether durable evidence exists for the separate Windows ISIS 10 CPython 3.13 PyISIS wheel build, clean install, import, focused tests, and DLL/import-library audit.
- Whether legacy planning records should be archived or amended after the evidence classification.

## Conclusion

- No current source change is justified for the historical SpiceQL/mgs failure: its patch and downstream link probe are already present.
- The next implementation milestone is `post-m06-dual-version-wheel-revalidation-m08`, not a PvlObject or SpiceQL repair. It must revalidate Linux/Windows × ISIS 9/10 wheels at the current HEAD, retain fresh output hashes and install reports, and only then determine release readiness.

## Errors

| Error | Attempt | Resolution |
|---|---:|---|
| Browser connector returned a non-iterable result while opening GitHub release and Actions pages | 1 | Used a public GitHub REST query instead; do not infer run outcomes from workflow definitions. |

## Decisions

| Decision | Rationale |
|---|---|
| Treat native APP validation and PyISIS wheel validation as separate lanes | Passing `csv2table` native behavior does not itself establish wheel install/import evidence. |
