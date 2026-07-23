# PyISIS v1.3.0rc1 (USGS ISIS 9.0.0)

This is the current cross-platform release candidate for the USGS ISIS 9.0.0
binding line.

## Support scope

- Windows x64 with CPython 3.12
- Linux x86_64 with CPython 3.12 and `manylinux_2_35`
- minimal packaged ISISDATA for import and smoke tests

Linux wheels are clean-install tested on Ubuntu 22.04 and Ubuntu 24.04.
macOS, ARM64, and other Python ABIs are not included.

## GitHub Release identity

- Tag: `v1.3.0rc1-isis9.0.0`
- Title: `PyISIS v1.3.0rc1 (USGS ISIS 9.0.0)`
- State: prerelease

## Assets

- `pyisis-v1.3.0rc1-isis9.0.0-linux-x86_64-cp312-manylinux_2_35-wheelhouse.zip`
- `pyisis-v1.3.0rc1-isis9.0.0-windows-x64-cp312-wheelhouse.zip`
- `SHA256SUMS.txt`

Extract the platform archive and follow its `INSTALL.md`. The packages are
installed with pip from the downloaded local wheelhouse; this release does not
publish them to PyPI.

## Documentation

- [Full release notes](docs/releases/v1.3.0rc1-isis9.0.0.md)
- [Linux installation](docs/releases/INSTALL-LINUX-ISIS9.0.0.md)
- [Windows installation](docs/releases/INSTALL-WINDOWS-ISIS9.0.0.md)
- [Cross-platform release plan](docs/cross-platform-github-release-plan.md)

Real camera, SPICE, calibration, and mission workflows require a complete
external ISISDATA tree.
