# Windows ISIS 9.0.0 and PyISIS Native Build Milestones

# Findings: Prepare the Windows native build environment

## Verified Facts

- Milestone ID: `windows-isis9-m01-environment`.
- The environment solve succeeded for 196 packages and selected Python 3.12.13,
  CSM 3.0.3.3, CMake 4.3.4, Ninja 1.13.2, and pybind11 3.1.0.
- The transaction failed during package extraction in the micromamba root
  cache, before a usable target prefix was created.
- The first concrete failures were Windows DLL creation failures for
  `ucrtbase.dll` and `OpenCL.dll` under a cache path containing
  `pkgs\https\conda.anaconda.org\conda-forge\win-64`.
- `.github/workflows/README.md:400` records the same host-specific behavior:
  endpoint security permits Conda to install UCRT but prevents Micromamba from
  creating `ucrtbase.dll`; it explicitly forbids disabling protection and uses
  Conda's classic solver instead.
- A command-scoped condarc with `channels: [conda-forge]` and
  `default_channels: []` passed the ToS boundary: `conda env create --dry-run`
  entered classic solving without requesting any Anaconda defaults terms. The
  diagnostic command was stopped by its 124-second command timeout before the
  large solve completed.
- GitHub API verified that remote `main` is exactly local `origin/main` commit
  `ccea42407c2153346c2871a0fdef641bd84aae2b`; no newer main commit exists.
- The main-branch Windows APP manifest contains exactly 150 entries, all with
  ISIS 9 `supported` status. Open PR #356 instead contains 169 entries and is a
  conflicting, unmerged ISIS 10 follow-up.
- Downloaded the published ISIS 9 rc2 Windows wheelhouse to
  `build/windows/reference-releases/v1.3.0rc2-isis9.0.0/`; its 92,696,606-byte
  ZIP SHA-256 is
  `a1c793f802a2003a1b4a791d7f273b25b4ad2a06abc3327ee4c0058f7768c81e`,
  exactly matching the release `SHA256SUMS.txt`.

## Evidence-Based Inference

- None recorded.

## Unresolved Items

- None for M1. Structured completion evidence remains the final lifecycle
  action.

## Decisions

| Decision | Rationale |
|---|---|
| Switch environment creation from Micromamba 2.8.1 to Conda 26.5.3 classic solver | The exact failure and supported fallback are already documented for this workstation in the repository. |
| Use the 150-entry main manifest for the requested APP gate | It exactly matches the requested count and has ISIS 9 support metadata; the 169-entry PR is not merged and targets later ISIS 10 promotion. |
| Keep the published rc2 wheelhouse as a comparison baseline only | The user requires a fresh local source build; release binaries provide provenance and later behavior comparison, not a substitute prefix. |

## Resources

- Canonical registry: `.planning/milestones.v1.json`
