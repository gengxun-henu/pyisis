# Instruction Architecture Maintenance Notes — 2026-04-08

This note explains the current Copilot instruction architecture for this repository after the 2026-04-08 conservative deduplication pass.

Use it as a maintenance guide when you need to update `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, or `.github/skills/isis-pybind/SKILL.md`.

## Why this note exists

The repository has accumulated several rounds of instruction updates.

That is good for coverage, but it also creates a predictable maintenance risk:

- the same rule gets copied into multiple files
- one file gets updated but the sibling rule does not
- the root workspace instruction slowly grows into a second workflow file
- file-level instructions repeat repository-wide defaults instead of focusing on their specific scope

This note records the intended separation of concerns so future cleanup can stay conservative and low-risk.

## Current architecture at a glance

### 1. Root workspace instruction

Primary file:

- `.github/copilot-instructions.md`

Purpose:

- repository-wide always-on behavior
- working style and response language preference
- default environment and validation preference
- routing users and the agent toward the correct lower-level instruction or skill

What belongs here:

- low-risk default execution style
- Chinese-by-default reply preference
- preferred Python environment (`asp360_new`)
- short pointers to specialized instructions and skills

What should not expand here:

- detailed pybind workflow steps already owned by `.github/skills/isis-pybind/SKILL.md`
- repeated metadata defaults already owned by `.github/instructions/pybind-metadata-common.instructions.md`
- language-specific formatting rules already owned by file-level instructions

Practical rule:

If a rule should apply almost everywhere in this repository, it probably belongs here.
If it is mainly about one file family or one workflow, it probably does not.

### 2. File-scoped instructions

Primary directory:

- `.github/instructions/`

Purpose:

- add focused, scope-limited rules using `applyTo`
- keep language-specific or task-specific requirements out of the root file

Current file ownership:

- `pybind-metadata-common.instructions.md`
  - shared metadata defaults across pybind C++ files and Python unit tests
  - author default, date format, short `Updated:` summary expectations
- `pybind-cpp-metadata.instructions.md`
  - maintenance rules for existing C++ pybind files under `src/`
  - when to refresh metadata, when not to churn comments
- `pybind-file-header.instructions.md`
  - header structure for new or substantially rewritten pybind C++ files
  - upstream source attribution and required header fields
- `pybind-python-test-metadata.instructions.md`
  - Python unit test module docstring structure and update-note expectations
- `pybind-testing.instructions.md`
  - testing philosophy, interpreter compatibility, smoke-vs-unit boundaries
- `pybind-upstream-source-reading.instructions.md`
  - reading order for upstream ISIS source and lifecycle/debugging guidance
- `reference-data-layout.instructions.md`
  - repository layout rules for `reference/` versus `tests/data/`
- `isis-cpp-naming.instructions.md`
  - C++ naming conventions and compatibility guidance

Practical rule:

Each instruction file should own one narrow concern clearly enough that a future editor can answer:

- why it exists
- what file set it applies to
- which nearby instruction it complements rather than duplicates

### 3. Workflow skill

Primary file:

- `.github/skills/isis-pybind/SKILL.md`

Purpose:

- main procedure for multi-step pybind work
- default file-inspection order
- progress tracking expectations
- standard implementation and validation sequence

What belongs here:

- workflow order
- task checklist
- progress artifact update rules
- references to deeper workflow documents

What should not drift here:

- repository-wide response style
- repeated language-specific metadata formatting rules
- broad rules already covered by root workspace instructions unless the skill needs a short reminder

Practical rule:

If the content reads like "when doing a pybind task, follow these steps", it likely belongs in the skill.

## The main deduplication decisions from 2026-04-08

### Shared metadata rules were centralized

Common rules that had previously been repeated across root, C++, and Python test instructions now live primarily in:

- `.github/instructions/pybind-metadata-common.instructions.md`

That file is now the default home for:

- default author metadata
- date format
- shared meaning of a short top-of-file update summary
- the rule that metadata should not churn for trivial formatting-only edits

The C++ and Python metadata instructions should now focus on format and usage differences, not repeat the common defaults in full.

### Root workflow duplication was reduced

The detailed pybind task-routing bullets were removed from the root workspace instruction and reduced to a small routing section that points to:

- `.github/skills/isis-pybind/SKILL.md`

This keeps the root file from becoming a second copy of the pybind workflow.

### Path layout guidance was narrowed

The upstream-reading instruction still points maintainers to `reference/upstream_isis/`, but broader repository layout ownership remains with:

- `.github/instructions/reference-data-layout.instructions.md`

This avoids repeating the same path-governance rule in multiple places.

## Maintenance rules for future edits

### When updating `.github/copilot-instructions.md`

Prefer adding only:

- repository-wide defaults
- short routing hints
- behavior that is useful even outside pybind implementation tasks

Before adding text, ask:

1. Is this truly always-on for the repository?
2. Is this already explained by a file-scoped instruction?
3. Is this actually a workflow step that belongs in the skill instead?

If the answer to 2 or 3 is yes, do not duplicate it in the root file.

### When updating a metadata-related instruction

First identify which level the rule belongs to:

- cross-language shared default -> `pybind-metadata-common.instructions.md`
- existing C++ file maintenance -> `pybind-cpp-metadata.instructions.md`
- new or rewritten C++ file header -> `pybind-file-header.instructions.md`
- Python unit test docstring and metadata layout -> `pybind-python-test-metadata.instructions.md`

Before adding a new example line, ask whether the example teaches something unique for that file or just repeats the common pattern.

### When updating the pybind workflow

Default home:

- `.github/skills/isis-pybind/SKILL.md`

Use the skill for:

- inspection order
- standard implementation sequence
- validation order
- progress-log update requirements

Only keep a shorter reminder in root instructions when the pointer itself is useful.

### When adding a brand-new instruction file

Before creating a new file under `.github/instructions/`, check whether the new rule can instead be handled by:

- an existing instruction with a slightly clarified scope
- the root workspace instruction
- the pybind skill

Create a new instruction only if the rule has:

- a clearly different audience or trigger
- a stable `applyTo` pattern
- enough unique content to justify separate maintenance

## Quick ownership table

| Topic | Primary owner | Secondary references |
| --- | --- | --- |
| Repository-wide behavior | `.github/copilot-instructions.md` | skill or file instructions by pointer only |
| Shared metadata defaults | `.github/instructions/pybind-metadata-common.instructions.md` | C++ and Python metadata instructions |
| Existing C++ metadata maintenance | `.github/instructions/pybind-cpp-metadata.instructions.md` | shared metadata instruction |
| New / rewritten C++ file headers | `.github/instructions/pybind-file-header.instructions.md` | shared metadata instruction |
| Python unit test metadata | `.github/instructions/pybind-python-test-metadata.instructions.md` | shared metadata instruction |
| Testing behavior and validation boundaries | `.github/instructions/pybind-testing.instructions.md` | pybind skill |
| Upstream reading order and lifecycle debugging | `.github/instructions/pybind-upstream-source-reading.instructions.md` | reference-data-layout instruction |
| Reference vs runtime data layout | `.github/instructions/reference-data-layout.instructions.md` | root workspace instruction |
| C++ naming conventions | `.github/instructions/isis-cpp-naming.instructions.md` | none |
| Pybind implementation workflow | `.github/skills/isis-pybind/SKILL.md` | root workspace instruction |

## Anti-patterns to avoid

Avoid these maintenance patterns:

1. Copying the same `Updated:` example into multiple files when only one file owns the shared convention.
2. Expanding the root workspace instruction with task steps that are already fully documented in the skill.
3. Using a file-scoped instruction to restate repository layout rules that already belong in `reference-data-layout.instructions.md`.
4. Adding a new instruction file just to save a short example or one paragraph that fits naturally into an existing file.
5. Broadening `applyTo` just to make a rule feel more visible; this increases context cost and weakens separation of concerns.

## Suggested review checklist for future instruction changes

When editing instruction architecture later, use this quick checklist:

1. Did the change introduce a second primary owner for the same rule?
2. Does the root workspace instruction still read like a root file, not a workflow manual?
3. Does each instruction still have a narrow, understandable scope?
4. Is the skill still the main home for pybind workflow ordering?
5. Are `applyTo` patterns still as narrow as practical?
6. If a note or path rule was added, is `reference-data-layout.instructions.md` still the right authority?

## Recommended future follow-up

The 2026-04-08 pass was intentionally conservative.

Future cleanup can still improve two areas if needed:

1. shorten very long concrete examples in `pybind-upstream-source-reading.instructions.md` by moving them into a separate reference note
2. periodically re-audit metadata coverage in `src/` and `tests/unitTest/` using `reference/notes/metadata_audit_2026-04-08.md` as a baseline

## Related files

- `.github/copilot-instructions.md`
- `.github/instructions/pybind-metadata-common.instructions.md`
- `.github/instructions/pybind-cpp-metadata.instructions.md`
- `.github/instructions/pybind-file-header.instructions.md`
- `.github/instructions/pybind-python-test-metadata.instructions.md`
- `.github/instructions/pybind-testing.instructions.md`
- `.github/instructions/pybind-upstream-source-reading.instructions.md`
- `.github/instructions/reference-data-layout.instructions.md`
- `.github/instructions/isis-cpp-naming.instructions.md`
- `.github/skills/isis-pybind/SKILL.md`
- `reference/notes/metadata_audit_2026-04-08.md`
