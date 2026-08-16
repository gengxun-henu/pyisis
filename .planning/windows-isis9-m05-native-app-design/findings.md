# Windows ISIS 9 Native APP Distribution Milestone

# Findings: Design the native Windows ISIS APP release

## Verified Facts

- Milestone ID: `windows-isis9-m05-native-app-design`.
- M04 is complete and its immutable registry, plans, and structured evidence are archived under `.planning/archive/windows-pyisis-isis9-wheelhouse-m04/`.
- The verified Windows ISIS 9 prefix already launches native APPs when the complete runtime DLL path is configured.
- The PyISIS wheelhouse intentionally contains no standalone ISIS executables or APP XML.

## Evidence-Based Inference

- None recorded.

## Unresolved Items

- Completion evidence has not yet been produced.
- Package format (portable ZIP versus installer), exact APP inventory, launcher behavior, and release artifact names are deliberately undecided until M05 brainstorming.

## Decisions

| Decision | Rationale |
|---|---|
| Keep M05 design separate from M04 wheel publication | The native APP distribution is a different product with executables/XML and a broader runtime/data contract. |

## Resources

- Canonical registry: `.planning/milestones.v1.json`
- M04 archive: `.planning/archive/windows-pyisis-isis9-wheelhouse-m04/`
- M04 completion evidence: `.planning/archive/windows-pyisis-isis9-wheelhouse-m04/windows-isis9-m04-wheelhouse/completion-evidence.json`
- Product roadmap: `docs/superpowers/specs/2026-08-16-windows-pyisis-wheelhouse-design.md`
