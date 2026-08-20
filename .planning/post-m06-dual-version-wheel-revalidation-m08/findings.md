# Findings: Post-M06 dual-version wheel revalidation (M08)

## Verified Facts

- M06 is complete and current-HEAD behavior must be validated independently of the earlier rc2 release.
- The authoritative workflow is `.github/workflows/wheels.yml`.
- The Windows ISIS 10 workflow lane includes the existing SpiceQL 1.4.1 export and downstream MSVC link probe.
- The immutable M08 validation input is `07b87e389c09ad838b65dae3456927d66b289cd8` on `feature/m04-windows-pyisis-wheelhouse`.
- Pre-remote Git classification was only the guarded pre-existing unstaged `print.prt`; `git diff --check` produced no whitespace errors.
- `python -m unittest tests.unitTest.wheel_workflow_unit_test tests.unitTest.packaging_tools_unit_test -v` passed 33 tests (0 failed, 0 skipped). Its contract coverage includes the Windows ISIS 10 cp313 SpiceQL `1.4.1` build, prefix construction, isolated installation, and wheel/DLL-report uploads.
- The four required lanes map to workflow job IDs: `linux-isis9` → `linux-cp312-build` + `linux-cp312-clean-install`; `linux-isis10-cp313` → `linux-isis10-cp313-build` + `linux-isis10-cp313-clean-install`; `windows-cp312` → `windows-cp312`; `windows-isis10-cp313` → `windows-isis10-cp313`.

## Unresolved Items

- The fresh four-lane outcomes and artifacts for the frozen M08 commit.

## Decisions

| Decision | Rationale |
|---|---|
| Use the existing workflow unchanged | Its lanes already exercise the required package, installation, metadata, and runtime-closure contracts. |
