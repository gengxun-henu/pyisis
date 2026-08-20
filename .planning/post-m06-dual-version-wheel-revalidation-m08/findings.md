# Findings: Post-M06 dual-version wheel revalidation (M08)

## Verified Facts

- M06 is complete and current-HEAD behavior must be validated independently of the earlier rc2 release.
- The authoritative workflow is `.github/workflows/wheels.yml`.
- The Windows ISIS 10 workflow lane includes the existing SpiceQL 1.4.1 export and downstream MSVC link probe.

## Unresolved Items

- The fresh four-lane outcomes and artifacts for the frozen M08 commit.

## Decisions

| Decision | Rationale |
|---|---|
| Use the existing workflow unchanged | Its lanes already exercise the required package, installation, metadata, and runtime-closure contracts. |
