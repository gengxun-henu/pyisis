# Findings: Dual-version wheel release (M09)

## Verified Facts

- PR #371 is merged into `main` as `addb839dc0b2622931926c60265c6c47aedd650f`.
- Actions run `32447419640` completed successfully without publishing a GitHub release or TestPyPI package.
- That run passed Windows ISIS 9/cp312, Windows ISIS 10/cp313, Linux ISIS 9/cp312, Linux ISIS 10/cp313, and all six Ubuntu clean-install jobs.
- The guarded local `print.prt` remains modified and must not be staged, restored, deleted, or otherwise changed.
- `wheels.yml` publishes exactly one selected release line per manual dispatch and requires `publish_github_release=true` on `main`.
- The workflow assembles two platform ZIP assets plus `SHA256SUMS.txt`, then creates a GitHub prerelease from `packaging/releases/<release_line>.toml`.
- TestPyPI publication is independently controlled by `publish_testpypi`; it is not required for a GitHub release.
- Both currently configured release identities already exist remotely:
  - `v1.3.0rc2-isis9.0.0` / “PyISIS v1.3.0rc2 (USGS ISIS 9.0.0)”
  - `v1.4.0rc2-isis10.0.0` / “PyISIS v1.4.0rc2 (USGS ISIS 10.0.0)”
- The release job deliberately refuses to overwrite an existing release, so dispatching the current manifests with publishing enabled would fail.
- The successful M08 run was a pull-request run; the release job is intentionally skipped outside a manual dispatch on `main`.
- The current release contract uses shared minimal-data versioning: ISIS 9 binding/runtime/data are `1.3.0rc*`; ISIS 10 binding/runtime are `1.4.0rc*` and depend on the shared `1.3.0rc*` minimal-data wheel.
- The delta since the rc2 release commits includes the M08 PE-closure, Windows Conda storage/cache, self-hosted performance, Ninja build-directory, and Linux/Windows matrix repairs.

## Evidence-based Inference

- A fresh publishing run may rebuild artifacts rather than promote run `32447419640`; the tracked workflow contract must decide this.
- A new publication requires new release identities, most naturally the next prereleases after the existing rc2 lines; this must be implemented consistently across manifests and hard-coded packaging expectations before dispatch.

## Unresolved Items

- None for M09. Installing Docker on `pyisis-ubuntu26` remains a separate runner-maintenance improvement.

## Decisions

- Do not guess release inputs or create a tag manually before inspecting the tracked contract and existing remote state.
- Do not overwrite or mutate the existing rc2 releases.
- Freeze M09 identities as `v1.3.0rc3-isis9.0.0` and `v1.4.0rc3-isis10.0.0`; freeze the shared minimal-data version as `1.3.0rc3`.
- Retain old rc2 release-note files unchanged and add new rc3 release notes.
- Publish GitHub prereleases only; keep TestPyPI disabled.
- Bind both releases to merge commit `977b106c9321f2154684f1a8fa10e0e72b9d1229` and execute the two release lines sequentially.

## Published Outcome

- ISIS 9: https://github.com/gengxun-henu/pyisis/releases/tag/v1.3.0rc3-isis9.0.0
- ISIS 10: https://github.com/gengxun-henu/pyisis/releases/tag/v1.4.0rc3-isis10.0.0
- Formal workflow runs `32474949786` and `32477095364` both completed successfully at the exact release commit.
- Published ZIP SHA-256 values:
  - ISIS 9 Linux: `c110eb967bf9d5388357d2d26488999b24d6bce786c2b4415c8d66f28519daec`
  - ISIS 9 Windows: `57c761463cb6db967e90a743848ad7f76dded3d4055365119fa0a9951ade2fc2`
  - ISIS 10 Linux: `f2891770a13cf2bf8215c89358746ac594f11cb724e3ff5c79ac8cc6ca712ef6`
  - ISIS 10 Windows: `ed2da3c371c4924e9b50880fca18c0656732db3d36cf036e2b2738bb5c48be34`
- Downloaded hashes matched both `SHA256SUMS.txt` files and GitHub's asset digests.
- Fresh installation from each published Windows ZIP passed 330 checks, 0 failed, 0 skipped, and 1 expected failure.

## Resources

- `.github/workflows/wheels.yml`
- `.planning/post-m06-dual-version-wheel-revalidation-m08/`
- GitHub PR #371 and Actions run `32447419640`
