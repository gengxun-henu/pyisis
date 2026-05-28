# Select ISIS Cubes Usage Helper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pure `build_usage_examples()` helper to `examples/utility/select_isis_cubes.py` and expose its example block through the CLI `--help` output.

**Architecture:** Keep the change small and local to the existing selector script and its focused unit test module. Add one pure helper that returns example text, wire it into `argparse` via `epilog`, and extend the unit tests to verify both the helper content and help-text integration.

**Tech Stack:** Python 3.12, standard library (`argparse`, `io`, `contextlib.redirect_stdout`, `unittest`)

---

## File Structure

- Modify: `examples/utility/select_isis_cubes.py`
  - Add `build_usage_examples() -> str`
  - Reuse it from `parse_args()` through `ArgumentParser(..., epilog=...)`
  - Preserve existing selector behavior
- Modify: `tests/unitTest/select_isis_cubes_unit_test.py`
  - Add focused tests for helper content and `--help` integration
  - Preserve existing metadata block and update it for the new coverage

## Task 1: Add the pure usage helper and verify its content

**Files:**
- Modify: `examples/utility/select_isis_cubes.py`
- Modify: `tests/unitTest/select_isis_cubes_unit_test.py`

- [ ] **Step 1: Write the failing helper-content test**

```python
class UsageHelperTest(unittest.TestCase):
    def test_build_usage_examples_returns_examples_block_with_public_flags(self):
        module = load_select_isis_cubes_module()

        examples_text = module.build_usage_examples()

        self.assertIn("Examples:", examples_text)
        self.assertIn("--caminfo-list", examples_text)
        self.assertIn("--output-dir", examples_text)
        self.assertIn("--dry-run", examples_text)
        self.assertTrue(
            "--min-sub-solar-azimuth" in examples_text
            or "--max-sub-solar-azimuth" in examples_text
        )
```

- [ ] **Step 2: Run the focused helper test to verify it fails**

Run: `/home/gengxun/miniconda3/envs/asp360_new/bin/python -m unittest tests.unitTest.select_isis_cubes_unit_test.UsageHelperTest.test_build_usage_examples_returns_examples_block_with_public_flags -v`
Expected: FAIL with `AttributeError` because `build_usage_examples` does not yet exist.

- [ ] **Step 3: Implement the minimal pure helper in the selector script**

```python
def build_usage_examples() -> str:
    return "\n".join(
        [
            "Examples:",
            "  # Preview matches inside a latitude/longitude box without moving files",
            "  python examples/utility/select_isis_cubes.py --caminfo-list caminfo_files.txt --output-dir selected --min-latitude -10 --max-latitude 10 --min-longitude 120 --max-longitude 150 --dry-run",
            "",
            "  # Select cubes by sub-solar azimuth range",
            "  python examples/utility/select_isis_cubes.py --caminfo-list caminfo_files.txt --output-dir selected --min-sub-solar-azimuth 90 --max-sub-solar-azimuth 180",
            "",
            "  # Select cubes near a center point within a maximum degree distance",
            "  python examples/utility/select_isis_cubes.py --caminfo-list caminfo_files.txt --output-dir selected --center-latitude 5 --center-longitude 135 --max-center-distance-deg 2.5",
        ]
    )
```

- [ ] **Step 4: Re-run the focused helper test to verify it passes**

Run: `/home/gengxun/miniconda3/envs/asp360_new/bin/python -m unittest tests.unitTest.select_isis_cubes_unit_test.UsageHelperTest.test_build_usage_examples_returns_examples_block_with_public_flags -v`
Expected: PASS

- [ ] **Step 5: Commit the helper content change**

```bash
git add examples/utility/select_isis_cubes.py tests/unitTest/select_isis_cubes_unit_test.py
git commit -m "feat: add select-isis-cubes usage examples helper"
```

## Task 2: Wire the helper into `--help` and verify integration

**Files:**
- Modify: `examples/utility/select_isis_cubes.py`
- Modify: `tests/unitTest/select_isis_cubes_unit_test.py`

- [ ] **Step 1: Write the failing help-integration test**

```python
class UsageHelperTest(unittest.TestCase):
    def test_parse_args_help_includes_usage_examples_block(self):
        module = load_select_isis_cubes_module()
        stdout_buffer = io.StringIO()

        with self.assertRaises(SystemExit) as context:
            with redirect_stdout(stdout_buffer):
                module.parse_args(["--help"])

        self.assertEqual(context.exception.code, 0)
        help_text = stdout_buffer.getvalue()
        self.assertIn("Examples:", help_text)
        self.assertIn("--dry-run", help_text)
        self.assertIn("--min-sub-solar-azimuth", help_text)
```

- [ ] **Step 2: Run the focused help-integration test to verify it fails**

Run: `/home/gengxun/miniconda3/envs/asp360_new/bin/python -m unittest tests.unitTest.select_isis_cubes_unit_test.UsageHelperTest.test_parse_args_help_includes_usage_examples_block -v`
Expected: FAIL because the parser help text does not yet include the examples block.

- [ ] **Step 3: Wire the helper into `ArgumentParser` while preserving line breaks**

```python
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select ISIS cubes from caminfo metadata files and move matches.",
        epilog=build_usage_examples(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
```

Keep the existing public CLI flags unchanged.

- [ ] **Step 4: Run the focused help-integration test, then the full selector test module**

Run: `/home/gengxun/miniconda3/envs/asp360_new/bin/python -m unittest tests.unitTest.select_isis_cubes_unit_test.UsageHelperTest -v`
Expected: PASS

Run: `/home/gengxun/miniconda3/envs/asp360_new/bin/python -m unittest tests.unitTest.select_isis_cubes_unit_test -v`
Expected: PASS

Run: `/home/gengxun/miniconda3/envs/asp360_new/bin/python examples/utility/select_isis_cubes.py --help`
Expected: PASS with an `Examples:` block in the help output.

- [ ] **Step 5: Commit the help integration**

```bash
git add examples/utility/select_isis_cubes.py tests/unitTest/select_isis_cubes_unit_test.py
git commit -m "test: cover select-isis-cubes usage helper"
```

## Self-Review

### Spec coverage

- Pure helper function returning a string: covered in Task 1.
- `argparse` help integration through `epilog`: covered in Task 2.
- Example content includes representative supported flags: covered in Task 1 tests and implementation.
- No behavior changes to selection/move logic: both tasks stay scoped to help-text-only changes.
- Focused tests for helper content and `--help` integration: covered in Tasks 1 and 2.

No uncovered spec requirement remains.

### Placeholder scan

- No `TODO`, `TBD`, or deferred placeholders remain.
- Each task includes exact file paths, commands, and implementation snippets.

### Type consistency

- Shared names are consistent across the plan: `build_usage_examples`, `parse_args`, `UsageHelperTest`.
- CLI flags remain kebab-case throughout.

## Notes For Execution

- Keep this change scoped to the main worktree file the user is currently editing unless you intentionally choose the feature worktree for continued isolated implementation.
- Do not refactor parsing, filtering, move execution, or reporting while adding the help examples.
- Preserve the existing top-of-file metadata style in both the script and the test file.
