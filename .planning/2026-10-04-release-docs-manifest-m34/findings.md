# Findings & Decisions

## Requirements
- Consolidate current Release matrix and artifact identity requirements.
- State the PyISIS wheel versus native ISIS APP boundary.
- Preserve the exact Windows and runner blockers.

## Research Findings
- Existing release notes are version-specific and describe historical candidates.
- The new readiness page provides a current status without rewriting historical release notes.
- The page points to the validated packaging contract suite and records run `37190432546` as the current runner evidence.

## Technical Decisions
| Decision | Rationale |
|---|---|
| Add a current readiness page instead of rewriting historical notes | Historical release notes remain immutable context; current gates need one living status page. |
