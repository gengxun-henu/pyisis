# Post-M06 Dual-Version Wheel Revalidation Design

## Objective

Establish fresh, current-HEAD release evidence for PyISIS after M06 changed the
Python/native-APP boundary. The milestone validates, but does not publish,
the Linux/Windows × ISIS 9/10 wheel matrix.

## Context

The published ISIS 10 rc2 release and its Windows CPython 3.13 wheelhouse are
real historical evidence. The former Windows ISIS 10 `SpiceQL::strSclkToEt`
failure predates the committed Windows export patch and downstream MSVC link
probe. M06 subsequently removed the csv2table Python/in-process exception and
therefore historical wheel evidence must not be treated as validation of the
current HEAD.

Native ISIS APP evidence and Python wheel evidence are separate. The M06
csv2table matrix establishes native behavior in all four platform/version
cells, but it does not replace wheel build, isolated-install, import, runtime
closure, or ABI evidence.

## Architecture

Use the existing `.github/workflows/wheels.yml` workflow as the single
authority for the four release lanes. It already provisions the exact version
environments, builds the Windows ISIS 10 prefix through the SpiceQL export and
downstream-link probe, builds versioned wheelhouses, runs isolated installation
checks, validates metadata, and uploads required reports.

M08 makes no product-code change before an observed failure. Its result is a
fresh evidence set associated with the current commit. A failure is classified
at the first failing layer—environment/prefix, ISIS build/link, PyISIS build,
isolated install/import, focused behavior, or runtime/ABI closure—and becomes
the input to a narrowly scoped repair milestone.

## Scope

Included:

- Linux ISIS 9 wheel build and isolated install.
- Linux ISIS 10 CPython 3.13 wheel build and clean installs.
- Windows ISIS 9 CPython 3.12 wheel build and isolated install.
- Windows ISIS 10 CPython 3.13 prefix, wheel, isolated install, metadata, and
  DLL-dependency validation.
- Fresh artifact names, SHA-256 hashes, workflow run IDs, environment/package
  identities, pass/fail/skip counts, and a reconciled four-lane report.

Excluded:

- GitHub Release creation, upload, or publication.
- M06 artifact rebuild, deletion, or reclassification.
- Windows runner service installation and any administrator-only operation.
- New native ISIS APP porting work and the deferred `rank_isis_apps.py`
  diagnostic minor.

## Evidence Contract

For each lane, retain the exact workflow run/job identifier, current HEAD,
ISIS package/source identity, Python ABI, commands, test counts, produced
wheelhouse members, and SHA-256 hashes. Windows lanes additionally retain the
DLL-dependency report; Windows ISIS 10 additionally records successful
SpiceQL export and downstream-link probes.

All required lanes must succeed with zero unclassified failures. Existing,
explicitly documented environment-dependent skips may remain only when they
are preserved in the result with their reason. A missing artifact, missing
hash, stale HEAD, or missing isolated-install result fails the milestone.

## Failure Handling

Do not patch while a matrix run is in flight. On failure, preserve the minimal
workflow logs and artifacts, identify the earliest failure layer, compare it
with the historical rc2 and M06 evidence, and propose a minimal repair design.
Do not retry by changing cache keys, dependencies, or source patches without
that diagnosis.

## Completion Criteria

M08 is complete only when the current HEAD has fresh PASS evidence for all
four lanes, the four-lane report and hashes are retained, Git state is
classified, and a release-readiness conclusion is recorded. Completion does
not authorize publication; release remains a separate user decision.
