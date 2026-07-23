# Platform development and release support

This file is the repository's platform-support source of truth. Generated build
trees and runtime binaries are never source-controlled.

| Platform | Development input | Release layout | Current validation |
| --- | --- | --- | --- |
| Windows x64 | MSVC, the pinned ISIS 9.0.0 patch queue under `ports/windows/`, and the conda dependency environment | `usgs-pyisis`, `usgs-pyisis-runtime-win64`, and `usgs-pyisis-isisdata-minimal` wheels | CPython 3.12 wheel build/install is covered by Windows CI; the clean wheel runs the basic binding test list |
| Linux x86_64 | The pinned ISIS 9.0.0 conda environment under `ports/linux/env/`, the pinned GCC 12 toolchain, and the PyPA `manylinux_2_28_x86_64` container | `usgs-pyisis`, `usgs-pyisis-runtime-linux-x86_64`, and `usgs-pyisis-isisdata-minimal` wheels | CI builds CPython 3.12 `manylinux_2_35_x86_64` wheels, keeps a stricter GLIBC 2.28 symbol gate, enforces the auditwheel 2.35 policy, and clean-installs the same wheelhouse on Ubuntu 22.04 and 24.04; PyPI release remains blocked until that workflow passes |
| macOS | Not implemented | None | Unsupported |

## Content boundaries

Keep source, tests, small deterministic fixtures, platform recipes, and the
Windows ISIS patch queue in Git. Keep these generated or reconstructable items
out of Git:

- `reference/upstream_isis/`, restored on demand with
  `python tools/dev/sync_upstream_isis.py`
- complete ISIS build/install prefixes and complete mission `ISISDATA`
- compiled `.so`, `.pyd`, `.dll`, and `.lib` files
- wheelhouses, virtual environments, CMake build trees, caches, logs, and
  experiment outputs

The small `packaging/isisdata-minimal` package and
`tests/data/isisdata/mockup` remain tracked because routine smoke tests depend
on them.

## Claim boundary

Describe Windows support as Windows x64 / CPython 3.12 wheel support. Describe
Linux support as a configured CPython 3.12 manylinux 2.35 build with Ubuntu
22.04/24.04 clean-install validation. Do not call the artifacts PyPI-ready
until the container build and ABI/auditwheel gates pass. Do not claim universal cross-platform support until
additional platforms and Python ABI combinations are built and tested.
