# Windows ISIS 9 Native APP Distribution Milestone

# Findings: Design the native Windows ISIS APP release

## Verified Facts

- Milestone ID: `windows-isis9-m05-native-app-design`.
- M04 is complete and its immutable registry, plans, and structured evidence are archived under `.planning/archive/windows-pyisis-isis9-wheelhouse-m04/`.
- The verified Windows ISIS 9 prefix already launches native APPs when the complete runtime DLL path is configured.
- The PyISIS wheelhouse intentionally contains no standalone ISIS executables or APP XML.
- M05 was activated on 2026-08-16 after `verify_milestones.py` passed on branch `feature/m04-windows-pyisis-wheelhouse` at commit `3440fc3c`.
- The approved M04 roadmap requires M05 to compare native package formats, name the first-release inventory explicitly, and validate from a clean extracted or installed location without the build prefix.
- The existing Windows APP manifest and batch-smoke path target the command-line APP set; `reduce` and `jigsaw` are present in the manifest, while `qnet` is not, so GUI packaging and validation need an explicit separate contract.
- `ports/windows/isis/windows-app-manifest.json` has exactly 150 entries. All inspected entries have ISIS 9 status `supported` and build status `compiled_installed`; `reduce` additionally records `minimal_passed`.
- The verified ISIS 9 prefix is an ignored junction to `D:/code/pyisis/pyisis/build/windows/isis-prefix` and currently contains 364 executables, including `reduce.exe`, `jigsaw.exe`, and `qnet.exe`, plus 728 XML files under `bin/xml`.
- The full installed prefix also contains development-only material (`include`, import/static libraries, CMake/make content) that a runtime application package should not inherit blindly.

## Evidence-Based Inference

- A single undifferentiated APP list would obscure materially different CLI and Qt GUI runtime needs; the design should classify at least CLI and GUI launch surfaces separately.
- A curated single-archive staging pipeline is preferable to copying the whole prefix or splitting the first release into dependent archives: it preserves the 151-APP support boundary while keeping one atomic artifact and validation contract.

## Unresolved Items

- None for M05. Building the approved distribution belongs to the subsequent implementation milestone.

## Decisions

| Decision | Rationale |
|---|---|
| Keep M05 design separate from M04 wheel publication | The native APP distribution is a different product with executables/XML and a broader runtime/data contract. |
| Target scientific/developer users with a portable ZIP for the first release | The user selected the zero-install option; the package must extract and run without administrator privileges or Windows installer integration. |
| Publish the tracked 150 CLI APPs plus `qnet` as 151 public APPs | The user selected the existing validated manifest surface plus the mandatory GUI APP; any other executable must be justified as a non-public runtime helper by dependency/launch evidence. |
| Bundle minimal bootstrap/test data and allow an external full ISISDATA override | This supports clean-machine launch verification without embedding the full mission-data corpus in the native APP archive. |
| Use a prepared shell, one generic APP launcher, and a double-clickable `qnet` launcher | This preserves a structured `bin/lib/plugins/data` layout, centralizes environment setup, and avoids 151 duplicated wrappers or flattened DLL placement. |
| Support Windows 11 x64 only in the first release | The user selected the existing verified host class; Windows 10 and ARM64 remain separate future expansion work. |
| Use one curated portable ZIP staged from explicit manifests and dependency closure | The user approved approach A; whole-prefix snapshots and split runtime/APP archives are rejected for the first release. |
| Preserve a prefix-like runtime layout with centralized launchers and embedded manifests | The user approved the package/component design: `bin`, `lib`, `plugins`, `appdata`, minimal `data`, `launch`, and `manifest`, with development artifacts excluded. |
| Use manifest-driven fail-closed staging and three fixed retained artifacts | The user approved recursive PE/export-forwarder dependency closure, explicit Qt/plugin/data inputs, stable ZIP construction, reproducible hashes, and fixed archive/dependency/validation report names. |
| Require a clean Windows 11 x64 launch matrix before the future package is releasable | The approved matrix covers all 150 CLI startup probes, representative real operations, three GUI launch surfaces, external ISISDATA override, negative launcher cases, hashes, and cleanup. |

## Resources

- Canonical registry: `.planning/milestones.v1.json`
- M04 archive: `.planning/archive/windows-pyisis-isis9-wheelhouse-m04/`
- M04 completion evidence: `.planning/archive/windows-pyisis-isis9-wheelhouse-m04/windows-isis9-m04-wheelhouse/completion-evidence.json`
- Product roadmap: `docs/superpowers/specs/2026-08-16-windows-pyisis-wheelhouse-design.md`
- Approved M05 SPEC: `docs/superpowers/specs/2026-08-16-windows-isis-native-app-distribution-design.md`
- Implementation plan: `docs/superpowers/plans/2026-08-16-windows-isis-native-app-distribution.md`
