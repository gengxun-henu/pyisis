# Select ISIS Cubes Usage Helper Design

## Goal

Add a small usage-helper function to `examples/utility/select_isis_cubes.py` that
returns a multi-line examples block for the CLI. The helper should make the
script's command-line usage easier to discover without changing the selector's
core behavior.

## Scope

In scope:

- Add a dedicated helper function that returns example command text as a string.
- Reuse that helper from the script's `argparse` help surface.
- Include a small number of representative examples covering the existing public
  CLI:
  - latitude/longitude range filtering
  - sub-solar azimuth filtering
  - center point plus max distance filtering
  - `--dry-run` preview
- Add focused unit coverage for the helper content and help integration.

Out of scope:

- Adding a second print-only helper such as `print_usage_and_exit()`.
- Adding a structured help system, config-file examples, or copy-mode examples.
- Changing the selector's filtering, move, or batch-processing behavior.
- Rewriting the existing `argparse` surface.

## Selected Design

Use a simple helper with this shape:

- `build_usage_examples() -> str`

The function should return a compact multi-line string beginning with an
`Examples:` heading and followed by 2 to 4 example command blocks.

This is preferred over a print helper because:

- it is easier to test as a pure function
- it composes directly with `ArgumentParser(..., epilog=...)`
- it keeps printing responsibility inside `argparse`

## Help Integration

The script should pass the returned string into the parser help surface through
`epilog=build_usage_examples()` and use a formatter choice that preserves the
intended line breaks.

The default `--help` output should therefore show:

- the normal option list
- the example block at the end

The helper should not itself print anything.

## Example Content Requirements

The returned text should include real public flags from the script and stay in
kebab-case.

At minimum, the content should mention:

- `--caminfo-list`
- `--output-dir`
- `--dry-run`
- `--min-sub-solar-azimuth` or `--max-sub-solar-azimuth`

The examples should reflect currently supported behavior only.

## Testing

Add focused tests that verify:

- the helper returns a string containing `Examples:`
- the string contains the expected public flags
- `parse_args(...)/--help` output includes the usage examples block

The tests should stay lightweight and not require real caminfo files.

## Acceptance Criteria

- `examples/utility/select_isis_cubes.py` exposes a `build_usage_examples()`
  helper.
- The helper returns a multi-line example string describing typical CLI usage.
- The script's `--help` output includes that example block.
- Existing CLI behavior remains unchanged apart from improved help text.
- Focused tests cover helper content and help integration.
