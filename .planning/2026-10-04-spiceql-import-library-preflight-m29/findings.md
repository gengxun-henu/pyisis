# Findings & Decisions

## Requirements
- Validate the exact import library selected under the Windows conda prefix.
- Fail before the expensive ISIS build when `strSclkToEt` is missing.

## Research Findings
- The existing script checks `SpiceQL.dll` exports and compiles a small downstream link probe.
- The historical failure occurs specifically while linking ISIS `mgs.dll`, so the selected `SpiceQL.lib` must also be inspected.
- The new check reports matching import-library members and fails with the library path when absent.

## Technical Decisions
| Decision | Rationale |
|---|---|
| Keep the check in `build_spiceql.ps1` | The script already owns prefix installation, export inspection, and downstream linkage. |

## Issues Encountered
| Issue | Resolution |
|---|---|
| Windows `dumpbin` unavailable on Linux | Validate the script contract with the packaging unit test; execute the actual symbol check on Windows CI. |
