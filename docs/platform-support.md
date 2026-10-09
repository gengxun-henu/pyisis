# Platform development and release support

This file is the repository's platform-support summary. The CI and release
source of truth is `docs/platform-release-policy.md`. Generated build trees and
runtime binaries are never source-controlled.

| Platform | Development input | Release layout | Current validation |
| --- | --- | --- | --- |
| Windows 11 x64 | MSVC, versioned ISIS 9/10 source and patch queues, and isolated conda environments | Version-isolated PyISIS wheels plus native ISIS APP/GUI ZIPs | ISIS 9/10 PyISIS wheels and the ISIS 10 native GUI package are release-ready; direct Windows 11 native GUI revalidation remains pending |
| Linux x86_64 | Versioned ISIS 9/10 conda environments, pinned GCC toolchain, and the PyPA manylinux container | Version-isolated PyISIS wheelhouses in the GitHub Release | Wheelhouses are clean-installed on Ubuntu 22.04, 24.04, and 26.04; see `docs/platform-release-policy.md` for the exact matrix |
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

Describe Windows support separately as PyISIS wheel support and native ISIS 9/10
GUI package support. Describe Linux support as version-isolated wheelhouses
validated on Ubuntu 22.04/24.04/26.04. Do not claim ISIS 10 Windows GUI support
until its native package passes the release gate in
`docs/platform-release-policy.md`. The validated wheelhouses may be called
GitHub Release-ready, but they are not published to PyPI by default.
