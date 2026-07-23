# PyISIS cross-platform GitHub Release plan

## Purpose

This document fixes the release contract for the current USGS ISIS 9.0.0
binding and leaves a clear path for a parallel ISIS 10.0.0 line. GitHub
Releases are the primary binary distribution channel; generated wheelhouses
remain outside Git.

The current Linux wheelhouse is expected to exceed PyPI's default 100 MB
per-file limit. GitHub Releases allow individual assets below 2 GiB and do not
impose a total release-size limit, so they are the practical primary channel
for these binaries. See the official
[PyPI storage limits](https://docs.pypi.org/project-management/storage-limits/)
and
[GitHub Release limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

## Version identity

Python package versions and USGS ISIS compatibility versions are separate:

| Identity | Current ISIS 9 release | Future ISIS 10 example |
| --- | --- | --- |
| Python package version | `1.3.0rc1` | independently selected, for example `2.0.0rc1` |
| Supported USGS ISIS | `9.0.0` | `10.0.0` |
| Git tag | `v1.3.0rc1-isis9.0.0` | `v2.0.0rc1-isis10.0.0` |
| Release title | `PyISIS v1.3.0rc1 (USGS ISIS 9.0.0)` | `PyISIS v2.0.0rc1 (USGS ISIS 10.0.0)` |

The ISIS suffix is deliberately not placed inside the Python package version.
This keeps package metadata PEP 440 compliant while allowing ISIS 9 and ISIS
10 assets to coexist visibly on the Releases page.

The machine-readable identity for the current line is
`packaging/release.toml`. All active package metadata must match its
`package_version`.

## Supported binary matrix

| Platform | Python ABI | Runtime basis | Validation |
| --- | --- | --- | --- |
| Linux x86_64 | CPython 3.12 | ISIS 9.0.0 conda environment; `manylinux_2_35_x86_64` wheel | ABI audit plus clean installation on Ubuntu 22.04 and 24.04 |
| Windows x64 | CPython 3.12 | Patched ISIS 9.0.0 MSVC prefix and conda dependency environment | Clean wheel installation and basic binding test list on `windows-2022` |

macOS, ARM64, and Python ABIs other than CPython 3.12 are not part of this
release.

## Release assets

`v1.3.0rc1-isis9.0.0` contains:

- `pyisis-v1.3.0rc1-isis9.0.0-linux-x86_64-cp312-manylinux_2_35-wheelhouse.zip`
- `pyisis-v1.3.0rc1-isis9.0.0-windows-x64-cp312-wheelhouse.zip`
- `SHA256SUMS.txt`

Each platform archive contains a `wheelhouse/` directory, its platform
installation guide, the repository license, and third-party notices. GitHub
also generates source archives from the release tag.

## Publication gate

The `wheels` workflow exposes a manual `publish_github_release` input. The
release job runs only when:

1. the workflow is dispatched from `main`;
2. `publish_github_release` is enabled;
3. Linux wheels build and pass ABI/policy checks;
4. the Linux wheelhouse installs on Ubuntu 22.04 and Ubuntu 24.04;
5. Windows wheels build, pass metadata checks, and install in an isolated
   environment;
6. expected wheel names and counts match the release manifest.

The workflow then assembles both archives, creates `SHA256SUMS.txt`, and creates
the prerelease using the tag and title from `packaging/release.toml`.
TestPyPI/PyPI upload is a separate opt-in path and is not part of this release.

## Installation boundary

The downloadable archives support offline-style installation with pip:

```text
python -m pip install --no-index --find-links wheelhouse usgs-pyisis==1.3.0rc1
```

`usgs-pyisis-isisdata-minimal` contains only enough ISISDATA for import and
smoke tests. Camera models, SPICE, calibration, and real mission processing
still require a complete external ISISDATA tree.

## ISIS 10.0.0 follow-up

ISIS 10 support should be added as a separate compatibility line:

1. add pinned Linux and Windows ISIS 10 build inputs;
2. keep ISIS 9 patches isolated from ISIS 10 patches;
3. use versioned cache keys and artifact names;
4. run the same Linux ABI and two-Ubuntu clean-install gates;
5. run the same Windows clean-install gate;
6. publish an ISIS 10-specific tag and assets without replacing ISIS 9 assets;
7. retain maintenance workflows for both lines until ISIS 9 support is
   explicitly retired.

Do not silently rebuild an existing ISIS 9 tag with ISIS 10 libraries.

## Release checklist

- [ ] Update `packaging/release.toml` and all package versions together.
- [ ] Update release notes and platform installation guides.
- [ ] Run focused packaging and workflow tests.
- [ ] Merge the release change to `main`.
- [ ] Dispatch `wheels` with `publish_github_release=true`.
- [ ] Confirm all Linux and Windows gates pass.
- [ ] Verify the tag, prerelease state, asset names, sizes, and SHA-256 file.
- [ ] Keep the workflow run URL with the release record.
