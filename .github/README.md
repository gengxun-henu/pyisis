Welcome to the USGS ISIS Python Bindings!
This project wraps the powerful USGS ISIS (v9.0.0) photogrammetric software, enabling seamless integration with Python for planetary image processing.
🛠️ Installation: You can easily install this package using Conda or Mamba. For step-by-step instructions, please see our Environment Setup Guide.
📚 Learning Resources: Processing planetary images with ISIS can be complex. We strongly suggest checking out the Getting Started Guide to navigate the learning curve effectively.

# GitHub Customization Quick Reference

This is the short human-facing map for the repository's Copilot customization files.

If you only need to know **where a rule should live**, start here.
If you need the detailed rationale and maintenance notes, see:

- `reference/notes/instruction-architecture-maintenance-2026-04-08.md`

## Fast ownership guide

| Need to change | Primary file |
| --- | --- |
| Repository-wide working style or always-on behavior | `.github/copilot-instructions.md` |
| Shared metadata defaults across pybind C++ and Python tests | `.github/instructions/pybind-metadata-common.instructions.md` |
| Metadata maintenance for existing C++ pybind files | `.github/instructions/pybind-cpp-metadata.instructions.md` |
| Header structure for new or heavily rewritten C++ pybind files | `.github/instructions/pybind-file-header.instructions.md` |
| Metadata layout for Python unit tests | `.github/instructions/pybind-python-test-metadata.instructions.md` |
| Testing behavior, interpreter rules, smoke vs unit boundaries | `.github/instructions/pybind-testing.instructions.md` |
| Upstream ISIS reading order and lifecycle/debugging guidance | `.github/instructions/pybind-upstream-source-reading.instructions.md` |
| `reference/` vs `tests/data/` placement rules | `.github/instructions/reference-data-layout.instructions.md` |
| C++ naming conventions | `.github/instructions/isis-cpp-naming.instructions.md` |
| Main pybind workflow and task order | `.github/skills/isis-pybind/SKILL.md` |

## Three-layer mental model

### Root layer

Use `.github/copilot-instructions.md` for repository-wide defaults that should stay effectively always-on.

### File-scoped instruction layer

Use `.github/instructions/*.instructions.md` for focused rules with a clear `applyTo` scope.

### Workflow layer

Use `.github/skills/isis-pybind/SKILL.md` for multi-step pybind task procedure, validation order, and progress-tracking workflow.

## Quick guardrails

Before adding a new rule, ask:

1. Is this truly repository-wide?
   - yes -> `.github/copilot-instructions.md`
2. Is this specific to one file family or one kind of edit?
   - yes -> `.github/instructions/...`
3. Does this read like a step-by-step pybind procedure?
   - yes -> `.github/skills/isis-pybind/SKILL.md`

## Anti-duplication reminders

- Do not turn `.github/copilot-instructions.md` into a second workflow manual.
- Do not repeat shared metadata defaults in multiple language-specific instruction files.
- Do not duplicate `reference/` vs `tests/data/` rules outside `reference-data-layout.instructions.md` unless a short pointer is enough.
- Keep `applyTo` as narrow as practical.

## Related paths

- `.github/copilot-instructions.md`
- `.github/instructions/`
- `.github/skills/isis-pybind/SKILL.md`
- `reference/notes/instruction-architecture-maintenance-2026-04-08.md`
