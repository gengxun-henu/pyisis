# PyISIS cross-platform GitHub Release plan

## Purpose

This document fixes the release contract for the USGS ISIS 9.0.0 and
ISIS 10.0.0 package lines. GitHub
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

| Identity | ISIS 9 release | ISIS 10 release |
| --- | --- | --- |
| Python package version | `1.3.0rc2` | `1.4.0rc2` |
| Supported USGS ISIS | `9.0.0` | `10.0.0` |
| Git tag | `v1.3.0rc2-isis9.0.0` | `v1.4.0rc2-isis10.0.0` |
| Release title | `PyISIS v1.3.0rc2 (USGS ISIS 9.0.0)` | `PyISIS v1.4.0rc2 (USGS ISIS 10.0.0)` |

The ISIS suffix is deliberately not placed inside the Python package version.
This keeps package metadata PEP 440 compliant while allowing ISIS 9 and ISIS
10 assets to coexist visibly on the Releases page.

The machine-readable identities are `packaging/releases/isis9.toml` and
`packaging/releases/isis10.toml`. The workflow selects one through its
`release_line` input.

## Supported binary matrix

| Platform | Python ABI | Runtime basis | Validation |
| --- | --- | --- | --- |
| Linux x86_64 | CPython 3.12 | ISIS 9.0.0 conda environment; `manylinux_2_35_x86_64` wheel | ABI audit plus clean installation on Ubuntu 22.04 and 24.04 |
| Windows x64 | CPython 3.12 | Patched ISIS 9.0.0 MSVC prefix and conda dependency environment | Clean wheel installation and basic binding test list on `windows-2022` |
| Linux x86_64 | CPython 3.13 | ISIS 10.0.0 conda environment; `manylinux_2_35_x86_64` wheel | ABI audit plus clean installation on Ubuntu 22.04 and 24.04 |
| Windows x64 | CPython 3.13 | Patched ISIS 10.0.0 MSVC prefix, source-built SpiceQL, and conda dependencies | Clean wheel installation and basic binding test list on `windows-2022` |

macOS, ARM64, and other Python ABIs are not part of these releases.

## Release assets

`v1.3.0rc2-isis9.0.0` contains:

- `pyisis-v1.3.0rc2-isis9.0.0-linux-x86_64-cp312-manylinux_2_35-wheelhouse.zip`
- `pyisis-v1.3.0rc2-isis9.0.0-windows-x64-cp312-wheelhouse.zip`
- `SHA256SUMS.txt`

Each platform archive contains a `wheelhouse/` directory, its platform
installation guide, the repository license, and third-party notices. GitHub
also generates source archives from the release tag.

`v1.4.0rc2-isis10.0.0` contains the corresponding cp313 Linux and Windows
archives named in `packaging/releases/isis10.toml`, plus `SHA256SUMS.txt`.

## Publication gate

The `wheels` workflow exposes a manual `publish_github_release` input. The
release job runs only when:

1. the workflow is dispatched from `main`;
2. `publish_github_release` is enabled and `release_line` selects `isis9` or
   `isis10`;
3. Linux wheels build and pass ABI/policy checks;
4. the Linux wheelhouse installs on Ubuntu 22.04 and Ubuntu 24.04;
5. Windows wheels build, pass metadata checks, and install in an isolated
   environment;
6. expected distribution names, runtime names, ABI, versions, and wheel counts
   match the selected release manifest.

The workflow then assembles both archives, creates `SHA256SUMS.txt`, and creates
the prerelease using the tag and title from the selected versioned manifest.
TestPyPI/PyPI upload is a separate opt-in path and is not part of this release.

## Installation boundary

The downloadable archives support offline-style installation with pip:

```text
python -m pip install --no-index --find-links wheelhouse usgs-pyisis==1.3.0rc2
```

`usgs-pyisis-isisdata-minimal` contains only enough ISISDATA for import and
smoke tests. Camera models, SPICE, calibration, and real mission processing
still require a complete external ISISDATA tree.

## Dual-line maintenance

Shared bindings remain in `src/`. Compile-time feature gates contain the small
number of ISIS 10-only APIs. Platform inputs, Windows patch queues, runtime
distribution names, artifacts, and release manifests carry an explicit ISIS
major version where their ABI differs.

Do not silently rebuild an existing ISIS 9 tag with ISIS 10 libraries.

## Release checklist

- [ ] Update the selected file under `packaging/releases/` and its package
  metadata together.
- [ ] Update release notes and platform installation guides.
- [ ] Run focused packaging and workflow tests.
- [ ] Merge the release change to `main`.
- [ ] Dispatch `wheels` with the intended `release_line` and
  `publish_github_release=true`.
- [ ] Confirm all Linux and Windows gates pass.
- [ ] Verify the tag, prerelease state, asset names, sizes, and SHA-256 file.
- [ ] Keep the workflow run URL with the release record.
