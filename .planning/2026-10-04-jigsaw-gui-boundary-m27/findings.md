# Findings & Decisions

## Requirements
- Keep jigsaw separate from Qt GUI applications while preserving its bundle-adjustment role.
- Identify concrete Windows package probes for jigsaw and qnet.

## Research Findings
- The roadmap classifies `jigsaw` as a command-line bundle-adjustment application with separate solver/resource dependencies.
- Qt GUI applications are `qnet`, `qview`, and `qmos`; GUI packaging must remain optional and independent of core CLI workflows.
- The Windows native-app test script already probes `reduce -gui`, `jigsaw -gui`, and `qnet`, checks qnet launcher presence, and expects a 151-entry public package (150 manifest CLI apps plus qnet).
- The manifest marks jigsaw ISIS 9 supported and ISIS 10 experimental; ISIS 10 startup smoke is recorded as passed, while ISIS 9 individual smoke remains unrecorded.

## Technical Decisions
| Decision | Rationale |
|---|---|
| Preserve separate `apps-bundle` and `apps-gui` components | This limits Qt runtime coupling and lets CLI photogrammetry workflows ship independently. |
| Treat jigsaw GUI mode as a package probe, not a Python binding | The roadmap explicitly keeps native app algorithms and GUI launchers outside the pybind extension. |

## Issues Encountered
| Issue | Resolution |
|---|---|
| Windows ISIS 10 package gate is still blocked upstream | Defer executable implementation claims until the M23/M24 linker and runner blockers are resolved. |
