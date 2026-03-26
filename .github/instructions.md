# Copilot workspace instructions

- Default to acting without asking for confirmation.
- Only ask for confirmation before high-risk actions such as modifying system files, destructive operations, handling secrets/credentials, or other irreversible changes.
- Prefer replying in Chinese unless the user clearly requests another language.
- Prefer using the Python interpreter from the `asp360_new` environment for this repository's Python build, test, and validation tasks.
- For `isis_pybind_standalone` pybind11 binding and test work, also follow the dedicated rules in `.github/instructions/pybind-testing.instructions.md`.
- For pybind source/header and unit-test metadata conventions, also follow `.github/instructions/pybind-cpp-metadata.instructions.md` and `.github/instructions/pybind-python-test-metadata.instructions.md`.
- Execute first and then report results concisely, instead of repeatedly asking whether to continue.
- After modifying code, default to running the smallest relevant test or validation for the changed area.
- When adding authored comments or header metadata, default the author to `Geng Xun` and the date to the current date unless the user specifies otherwise.
- When information is incomplete but the next step is low-risk and reversible, proceed with the most reasonable assumption and state that assumption in the report.
- When conducting 'pybind', update `../pybind_progress_log.md` with the current progress, validation status, and blockers, and update `../todo_pybind11.csv` when the pending binding class/function inventory or its tracked completion context changes.

