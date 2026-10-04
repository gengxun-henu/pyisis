# Progress Log

## Session: 2026-10-04

### Current Status
- **Phase:** 5 - Delivery
- **Started:** 2026-10-04

### Findings
- Windows ISIS 10 failure: `mgs.dll` unresolved decorated `SpiceQL::strSclkToEt` symbol.
- Self-hosted failure: checkout cleanup cannot remove existing files and reports a stale submodule mapping.
- Linux local builds remain green but cannot validate MSVC import-library resolution.

### Required Next Validation
- Run `dumpbin` symbol comparison and a clean Windows prefix build.
- Recreate/fix runner workspace ownership and rerun the workflow from a clean checkout.
