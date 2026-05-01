# ControlNet Config Helper Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce duplicated `ImageMatch` config parsing in the ControlNet example shell wrappers without changing the public pipeline behavior.

**Architecture:** Keep `image_match.py` as the authoritative parser for `ImageMatch` defaults, then add a narrow machine-readable helper mode that shell wrappers can call for individual scalar config values. Replace repeated Python here-doc extractors in `run_pipeline_example.sh` and `run_image_match_batch_example.sh` with one shell function that delegates to that helper.

**Tech Stack:** Python 3.12, `argparse`, JSON config files, Bash wrapper scripts, `unittest`, existing `asp360_new` environment.

---

## File structure

- Modify `examples/controlnet_construct/image_match.py`
  - Add `format_image_match_default_for_shell(value)` and `print_image_match_config_default(config_path, field_name)`.
  - Add an early `--print-config-default FIELD` mode that requires `--config` and exits before positional DOM arguments are parsed.
  - Keep all existing public matching CLI flags unchanged.
- Modify `examples/controlnet_construct/run_pipeline_example.sh`
  - Replace repeated `extract_*_from_config()` Python here-doc functions for `ImageMatch` fields with one generic `extract_image_match_config_value FIELD` helper.
  - Keep `extract_network_id_from_config()` unchanged because it reads ControlNet-level config, not `ImageMatch`.
- Modify `examples/controlnet_construct/run_image_match_batch_example.sh`
  - Replace repeated `extract_*_from_config()` Python here-doc functions with the same generic helper.
- Modify `tests/unitTest/controlnet_construct_matching_unit_test.py`
  - Add direct Python tests for the helper mode and value formatting.
- Modify `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
  - Update fake Python dispatchers so wrapper tests understand the new `image_match.py --print-config-default FIELD` calls.
  - Preserve existing assertions for forwarded kebab-case flags and config precedence.
- Optional documentation update only if help text changes: `examples/controlnet_construct/usage.md`.

## Task 1: Add Python helper tests

**Files:**
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
- Modify later: `examples/controlnet_construct/image_match.py`

- [ ] **Step 1: Add tests for shell formatting and config default lookup**

Append these methods inside `ControlNetConstructMatchingUnitTest`:

```python
    def test_format_image_match_default_for_shell_normalizes_scalars(self):
        self.assertEqual(image_match.format_image_match_default_for_shell(True), "1")
        self.assertEqual(image_match.format_image_match_default_for_shell(False), "0")
        self.assertEqual(image_match.format_image_match_default_for_shell(6), "6")
        self.assertEqual(image_match.format_image_match_default_for_shell(0.05), "0.05")
        self.assertEqual(image_match.format_image_match_default_for_shell("bf"), "bf")

    def test_print_image_match_config_default_reads_existing_parser_aliases(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "validPixelPercentThreshold": 0.07,
                            "useParallelCpu": False,
                            "numWorkerParallelCpu": 4,
                            "matcherMethod": "flann",
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                image_match.print_image_match_config_default(config_path, "valid_pixel_percent_threshold"),
                "0.07",
            )
            self.assertEqual(image_match.print_image_match_config_default(config_path, "use_parallel_cpu"), "0")
            self.assertEqual(image_match.print_image_match_config_default(config_path, "num_worker_parallel_cpu"), "4")
            self.assertEqual(image_match.print_image_match_config_default(config_path, "matcher_method"), "flann")

    def test_print_image_match_config_default_returns_empty_string_for_missing_field(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(json.dumps({"ImageMatch": {}}), encoding="utf-8")

            self.assertEqual(image_match.print_image_match_config_default(config_path, "low_resolution_level"), "")
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_format_image_match_default_for_shell_normalizes_scalars tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_print_image_match_config_default_reads_existing_parser_aliases tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_print_image_match_config_default_returns_empty_string_for_missing_field -v
```

Expected: fail with `AttributeError` because `format_image_match_default_for_shell` and `print_image_match_config_default` do not exist yet.

- [ ] **Step 3: Commit only the failing tests**

```bash
git add tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "test: cover image match config default helper" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 2: Implement Python helper mode in `image_match.py`

**Files:**
- Modify: `examples/controlnet_construct/image_match.py`
- Test: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Add formatting and lookup helpers after `load_image_match_defaults_from_config`**

Insert this code after the existing `load_image_match_defaults_from_config()` function:

```python
def format_image_match_default_for_shell(value: object) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        raise ValueError("List-valued ImageMatch defaults cannot be printed as a single shell scalar.")
    return str(value)


def print_image_match_config_default(config_path: str | Path, field_name: str) -> str:
    defaults = load_image_match_defaults_from_config(config_path)
    if field_name not in defaults:
        return ""
    return format_image_match_default_for_shell(defaults[field_name])
```

- [ ] **Step 2: Add early helper CLI handling in `main()`**

In `main(argv: list[str] | None = None)`, replace the first parser block with this exact structure:

```python
def main(argv: list[str] | None = None) -> None:
    resolved_argv = sys.argv[1:] if argv is None else list(argv)
    config_probe_parser = argparse.ArgumentParser(add_help=False)
    config_probe_parser.add_argument("--config", default=None)
    config_probe_parser.add_argument("--print-config-default", default=None)
    config_probe_args, _ = config_probe_parser.parse_known_args(resolved_argv)

    if config_probe_args.print_config_default is not None:
        if config_probe_args.config is None:
            config_probe_parser.error("--print-config-default requires --config")
        try:
            print(print_image_match_config_default(config_probe_args.config, config_probe_args.print_config_default))
        except ValueError as exc:
            config_probe_parser.error(str(exc))
        return

    config_defaults: dict[str, object] = {}
    if config_probe_args.config is not None:
        try:
            config_defaults = load_image_match_defaults_from_config(config_probe_args.config)
        except ValueError as exc:
            config_probe_parser.error(str(exc))

    parser = build_argument_parser(config_defaults=config_defaults)
    args = parser.parse_args(resolved_argv)
```

Leave the existing `result = match_dom_pair_to_key_files(...)` call unchanged below this block.

- [ ] **Step 3: Run focused helper tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_format_image_match_default_for_shell_normalizes_scalars tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_print_image_match_config_default_reads_existing_parser_aliases tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_print_image_match_config_default_returns_empty_string_for_missing_field -v
```

Expected: all three tests pass.

- [ ] **Step 4: Add a CLI-level assertion**

Append this test to `ControlNetConstructMatchingUnitTest`:

```python
    def test_image_match_cli_print_config_default_exits_before_positional_args(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps({"ImageMatch": {"enableLowResolutionOffsetEstimation": True}}),
                encoding="utf-8",
            )

            with mock.patch("sys.stdout") as stdout_mock:
                image_match.main(
                    [
                        "--config",
                        str(config_path),
                        "--print-config-default",
                        "enable_low_resolution_offset_estimation",
                    ]
                )

        stdout_mock.write.assert_any_call("1")
```

- [ ] **Step 5: Run the CLI helper test**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_image_match_cli_print_config_default_exits_before_positional_args -v
```

Expected: pass.

- [ ] **Step 6: Commit the Python helper implementation**

```bash
git add examples/controlnet_construct/image_match.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: expose image match config default helper" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 3: Refactor `run_image_match_batch_example.sh`

**Files:**
- Modify: `examples/controlnet_construct/run_image_match_batch_example.sh`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Add one generic helper in the shell script**

Replace all `extract_*_from_config()` functions in `run_image_match_batch_example.sh` with this one function:

```bash
extract_image_match_config_value() {
  local config_path=$1
  local field_name=$2
  "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_match.py" \
    --config "$config_path" \
    --print-config-default "$field_name"
}
```

- [ ] **Step 2: Update config resolution calls**

Replace calls as follows:

```bash
config_threshold=$(extract_image_match_config_value "$config_input" "valid_pixel_percent_threshold")
config_num_worker_parallel_cpu=$(extract_image_match_config_value "$config_input" "num_worker_parallel_cpu")
config_invalid_pixel_radius=$(extract_image_match_config_value "$config_input" "invalid_pixel_radius")
config_matcher_method=$(extract_image_match_config_value "$config_input" "matcher_method")
config_enable_low_resolution_offset_estimation=$(extract_image_match_config_value "$config_input" "enable_low_resolution_offset_estimation")
config_low_resolution_level=$(extract_image_match_config_value "$config_input" "low_resolution_level")
config_low_resolution_max_mean_reprojection_error_pixels=$(extract_image_match_config_value "$config_input" "low_resolution_max_mean_reprojection_error_pixels")
config_low_resolution_min_retained_match_count=$(extract_image_match_config_value "$config_input" "low_resolution_min_retained_match_count")
config_low_resolution_max_mean_projected_offset_meters=$(extract_image_match_config_value "$config_input" "low_resolution_max_mean_projected_offset_meters")
config_use_parallel_cpu=$(extract_image_match_config_value "$config_input" "use_parallel_cpu")
```

Keep the existing `if [[ -n "$config_*" ]]` checks and existing CLI override precedence.

- [ ] **Step 3: Update fake dispatcher tests for the helper mode**

In each fake `image_match.py` dispatcher used by `run_image_match_batch_example.sh` tests, add this block before the normal matching assertions:

```python
                        if script_name == "image_match.py" and "--print-config-default" in args:
                            config_path = Path(args[args.index("--config") + 1])
                            field_name = args[args.index("--print-config-default") + 1]
                            payload = json.loads(config_path.read_text(encoding="utf-8"))
                            image_match_config = payload.get("ImageMatch") or {}
                            mapping = {
                                "valid_pixel_percent_threshold": image_match_config.get("valid_pixel_percent_threshold", ""),
                                "num_worker_parallel_cpu": image_match_config.get("num_worker_parallel_cpu", ""),
                                "invalid_pixel_radius": image_match_config.get("invalid_pixel_radius", ""),
                                "matcher_method": image_match_config.get("matcher_method", ""),
                                "enable_low_resolution_offset_estimation": "1" if image_match_config.get("enable_low_resolution_offset_estimation") else "",
                                "low_resolution_level": image_match_config.get("low_resolution_level", ""),
                                "low_resolution_max_mean_reprojection_error_pixels": image_match_config.get("low_resolution_max_mean_reprojection_error_pixels", ""),
                                "low_resolution_min_retained_match_count": image_match_config.get("low_resolution_min_retained_match_count", ""),
                                "low_resolution_max_mean_projected_offset_meters": image_match_config.get("low_resolution_max_mean_projected_offset_meters", ""),
                                "use_parallel_cpu": "1" if image_match_config.get("use_parallel_cpu") is True else ("0" if image_match_config.get("use_parallel_cpu") is False else ""),
                            }
                            print(mapping.get(field_name, ""))
                            return 0
```

- [ ] **Step 4: Run batch-wrapper tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_image_match_batch_example_forwards_default_parallel_flag_and_pre_ransac_viz_dir tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_image_match_batch_example_reads_parallel_worker_limit_from_config -v
```

Expected: pass.

- [ ] **Step 5: Commit the batch wrapper refactor**

```bash
git add examples/controlnet_construct/run_image_match_batch_example.sh tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "refactor: reuse image match config helper in batch wrapper" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 4: Refactor `run_pipeline_example.sh`

**Files:**
- Modify: `examples/controlnet_construct/run_pipeline_example.sh`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Add the generic helper to `run_pipeline_example.sh`**

Keep `extract_network_id_from_config()` unchanged. Replace all `ImageMatch`-specific `extract_*_from_config()` functions with:

```bash
extract_image_match_config_value() {
  local config_path=$1
  local field_name=$2
  "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_match.py" \
    --config "$config_path" \
    --print-config-default "$field_name"
}
```

- [ ] **Step 2: Update config resolution calls**

Use the same field names listed in Task 3 Step 2. Preserve the current fallback behavior:

```bash
if [[ -z "$VALID_PIXEL_PERCENT_THRESHOLD" ]]; then
  VALID_PIXEL_PERCENT_THRESHOLD=$(extract_image_match_config_value "$CONFIG_PATH" "valid_pixel_percent_threshold")
fi
```

Apply the same pattern for `use_parallel_cpu`, `num_worker_parallel_cpu`, `invalid_pixel_radius`, `matcher_method`, and low-resolution fields.

- [ ] **Step 3: Update pipeline fake dispatchers for helper mode**

In pipeline tests where the fake Python dispatcher handles `image_match.py`, add the helper-mode block from Task 3 Step 3 before normal matching assertions.

- [ ] **Step 4: Run pipeline-wrapper tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_pipeline_example_writes_timing_json_and_logs_step_durations tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_pipeline_example_forwards_valid_pixel_threshold_from_config_to_image_match -v
```

Expected: pass.

- [ ] **Step 5: Commit the pipeline wrapper refactor**

```bash
git add examples/controlnet_construct/run_pipeline_example.sh tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "refactor: reuse image match config helper in pipeline wrapper" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 5: Validate compatibility and update docs only if needed

**Files:**
- Possibly modify: `examples/controlnet_construct/usage.md`
- Test: existing focused unit tests

- [ ] **Step 1: Run focused matching and pipeline tests**

Run:

```bash
python -m unittest \
  tests.unitTest.controlnet_construct_matching_unit_test \
  tests.unitTest.controlnet_construct_pipeline_unit_test \
  -v
```

Expected: pass.

- [ ] **Step 2: Check helper mode and public help stability**

Run:

```bash
python examples/controlnet_construct/image_match.py --config examples/controlnet_construct/controlnet_config.example.json --print-config-default num_worker_parallel_cpu
bash examples/controlnet_construct/run_pipeline_example.sh --help | grep -- '--num-worker-parallel-cpu'
bash examples/controlnet_construct/run_image_match_batch_example.sh --help | grep -- '--num-worker-parallel-cpu'
```

Expected: first command prints the configured worker count, and the second and third commands still print the existing public wrapper flags.

- [ ] **Step 3: Update docs only if maintainers should know about the hidden helper**

If reviewers decide the hidden helper should be documented for maintainers, add this note under the `ImageMatch` config section in `examples/controlnet_construct/usage.md`:

```markdown
维护者提示：`image_match.py --config CONFIG --print-config-default FIELD` 是给示例 shell wrapper 使用的轻量 helper，用于从同一套 Python 配置解析逻辑中读取单个 `ImageMatch` 默认值；普通用户仍应优先通过 `--config` 和显式 CLI 参数运行匹配。
```

- [ ] **Step 4: Commit docs if changed**

If `usage.md` changed:

```bash
git add examples/controlnet_construct/usage.md
git commit -m "docs: document image match config helper" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

If `usage.md` did not change, do not create an empty commit.

- [ ] **Step 5: Final status check**

Run:

```bash
git --no-pager status --short
```

Expected: no unexpected uncommitted changes except files intentionally left by the user.

## Self-review

- Spec coverage: this plan implements the first recommended sequence item from the design document: centralize `ImageMatch` config/default extraction and update shell wrappers to use it.
- Compatibility: public matching behavior, output layout, JSON report fields, and kebab-case CLI flags are preserved.
- Scope control: option dataclasses, DOM stage extraction, and generated-cache cleanup are intentionally deferred to later plans.
