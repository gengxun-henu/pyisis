# Findings: Post-M06 dual-version wheel revalidation (M08)

## Verified Facts

- M06 is complete and current-HEAD behavior must be validated independently of the earlier rc2 release.
- The authoritative workflow is `.github/workflows/wheels.yml`.
- The Windows ISIS 10 workflow lane includes the existing SpiceQL 1.4.1 export and downstream MSVC link probe.
- Failed M08 validation run `32373382592` used `b50506e365b1af6d80fdbefbba919d70b5779197` on `feature/m04-windows-pyisis-wheelhouse`; no release was published.
- Pre-remote Git classification was only the guarded pre-existing unstaged `print.prt`; `git diff --check` produced no whitespace errors.
- Before dispatch, the workflow contract suite passed 33 tests. After the repair, `python -m unittest tests.unitTest.wheel_workflow_unit_test tests.unitTest.packaging_tools_unit_test -v` passed 35 tests (0 failed, 0 skipped), including package-specific distribution metadata and Windows bootstrap/runtime checks.
- The four required lanes map to workflow job IDs: `linux-isis9` → `linux-cp312-build` + `linux-cp312-clean-install`; `linux-isis10-cp313` → `linux-isis10-cp313-build` + `linux-isis10-cp313-clean-install`; `windows-cp312` → `windows-cp312`; `windows-isis10-cp313` → `windows-isis10-cp313`.

## Unresolved Items

- Fresh four-lane outcomes and artifacts for the repaired commit.

## Failed-run evidence (run 32373382592)

- Both Linux wheel builds succeeded, but all six Linux clean-install jobs failed in `tools/packaging/test_wheel_install.py`: its generated metadata probe always requested `usgs-pyisis`, `usgs-pyisis-runtime-win64`, and `usgs-pyisis-isisdata-minimal`. Linux ISIS 9 therefore looked for the absent Windows runtime package, while Linux ISIS 10 first looked for the absent ISIS 9 distribution.
- Windows cp312 failed before build in `actions/setup-python`: Python 3.12 was absent from the local tool cache and repeated download attempts for the Windows Python archive ended with `ECONNRESET`.
- Windows ISIS 10 cp313 failed before build in `actions/checkout`: action archive acquisition initially hit DNS failure, then repository fetch exhausted three attempts because `github.com:443` was unreachable.
- The Windows self-hosted runner service is installed, automatic, online, and idle after the run. These Windows failures are bootstrap/network failures, not compile or packaging results.

## Decisions

| Decision | Rationale |
|---|---|
| Keep the existing four-lane workflow structure | The repair changes only clean-install expectations and removes a redundant Windows bootstrap; package, installation, metadata, and runtime-closure gates remain intact. |
| Dispatch with `release_line=isis10`, `publish_testpypi=false`, and `publish_github_release=false` | `release_line=none` is unsupported. These supported, explicit non-publishing inputs preserve the four-lane validation scope; the GitHub-release job is additionally restricted to `main`, so the feature-branch dispatch cannot create a release. |
| Use `windows_runner=windows-2022` for the replacement run | The self-hosted runner failed before compilation because its GitHub route was unstable. The workflow already supports the hosted runner; this isolates product validation from workstation network state. |
| Remove Windows `actions/setup-python` | The subsequent version-pinned setup-miniconda environments provide the interpreters actually used by build and packaging commands; the redundant action caused an unused Python download to fail. |
