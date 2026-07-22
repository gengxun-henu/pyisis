# Platform development and release support

This file is the repository's platform-support source of truth. Generated build
trees and runtime binaries are never source-controlled.

| Platform | Development input | Release layout | Current validation |
| --- | --- | --- | --- |
| Windows x64 | MSVC, the pinned ISIS 9.0.0 patch queue under `ports/windows/`, and the conda dependency environment | `usgs-pyisis`, `usgs-pyisis-runtime-win64`, and `usgs-pyisis-isisdata-minimal` wheels | CPython 3.12 wheel build/install is covered by Windows CI; the clean wheel runs the basic binding test list |
| Linux x86_64 | The pinned ISIS 9.0.0 conda environment under `ports/linux/env/` and the conda C++ compiler | `usgs-pyisis`, `usgs-pyisis-runtime-linux-x86_64`, and `usgs-pyisis-isisdata-minimal` wheels | CI is configured to build CPython 3.12 `linux_x86_64` prototypes and install them on a separate clean runner; the first remote pass, manylinux container build, and ABI audit remain required before PyPI release |
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
Linux support as a CPython 3.12 `linux_x86_64` wheel prototype with clean-runner
validation. Do not call it manylinux or PyPI-ready until the container build
and ABI audit pass. Do not claim universal cross-platform support until
additional platforms and Python ABI combinations are built and tested.
