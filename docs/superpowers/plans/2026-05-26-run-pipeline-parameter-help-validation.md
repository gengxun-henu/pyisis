# Run Pipeline Parameter Help And Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden `run_pipeline_example.sh` help and parameter validation around the existing catalog without changing pipeline behavior.

**Architecture:** Keep shell parsing and orchestration in `run_pipeline_example.sh`. Use `parameter_catalog.py` as the declarative source for groups and allowed values, `parameter_validation.py` for merged-value validation, and `print_parameter_catalog.py` for detailed catalog rendering and wrapper validation calls.

**Tech Stack:** Bash, Python 3.12, `unittest`, `subprocess`, existing `controlnet_construct` and `image_match` example packages.

---

## File Structure

- Modify `examples/controlnet_construct/run_pipeline_example.sh`: add compact help group index, add missing explicit-source markers, export those markers, and include additional wrapper-owned fields in the validation payload.
- Modify `examples/controlnet_construct/parameter_validation.py`: make inactive explicit CLI parameters errors while keeping inactive config/profile/preset values as warnings.
- Modify `examples/controlnet_construct/print_parameter_catalog.py`: improve detailed text output if needed so the catalog view exposes canonical names, allowed values, defaults, and config paths.
- Modify `tests/unitTest/controlnet_construct_pipeline_unit_test.py`: wrapper subprocess regressions for help, validate-only, explicit CLI conflicts, and strict behavior.
- Modify `tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py`: catalog coverage and grouped output regressions.
- Modify `tests/unitTest/controlnet_construct_parameter_validation_unit_test.py`: source-provenance severity regressions.

## Task 1: Add Compact Group Index To Normal Help

**Files:**
- Modify: `examples/controlnet_construct/run_pipeline_example.sh`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Write the failing help-index test**

Add this test to `ControlNetConstructPipelineUnitTest` near the existing `test_run_pipeline_example_prints_parameter_groups` test:

```python
    def test_run_pipeline_example_help_shows_compact_parameter_group_index(self):
        result = subprocess.run(
            [
                "bash",
                str(RUN_PIPELINE_EXAMPLE_PATH),
                "--help",
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Parameter groups:", result.stdout)
        for group_name in (
            "inputs",
            "pipeline",
            "matching",
            "tile",
            "low_resolution",
            "adaptive_routing",
            "execution",
            "visualization",
            "controlnet",
            "reporting",
        ):
            self.assertIn(group_name, result.stdout)
        self.assertIn("--print-parameter-groups", result.stdout)
        self.assertIn("full catalog", result.stdout)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_pipeline_example_help_shows_compact_parameter_group_index -v
```

Expected: FAIL because normal `--help` does not yet contain `Parameter groups:`.

- [ ] **Step 3: Add the compact group index to the usage heredoc**

In `examples/controlnet_construct/run_pipeline_example.sh`, inside `usage()`, insert this block after the "Default behavior:" paragraph and before the long "Options:" list:

```bash
Parameter groups:
  inputs: work/config/list paths and the Python executable
    common flags: --work-dir, --original-list, --dom-list, --config
  pipeline: high-level pipeline mode and deep-match manifest handoff
    common flags: --deep-match-mode, --skip-final-merge, --parameter-profile
  matching: matcher selection, presets, and deep matcher config
    common flags: --matcher-method, --match-preset-path, --deep-match-config-path
  tile: tile size, overlap, validity filtering, and invalid-pixel suppression
    common flags: --valid-pixel-percent-threshold, --invalid-pixel-radius
  low_resolution: coarse low-resolution offset estimation and gates
    common flags: --enable-low-resolution-offset-estimation, --low-resolution-level
  adaptive_routing: pair-level adaptive matcher routing controls
    common flags: --adaptive-routing, --adaptive-routing-profile
  execution: CPU/GPU execution controls
    common flags: --use-parallel-cpu, --no-parallel-cpu, --num-worker-parallel-cpu
  visualization: pre/post-RANSAC preview behavior and memory profile
    common flags: --visualization-mode, --memory-profile, --preview-cache-source
  controlnet: pair IDs, cnetmerge, final network paths, and merge behavior
    common flags: --merged-net, --merge-script, --network-id, --cnetmerge
  reporting: timing, validation, and report output controls
    common flags: --timing-json, --validate-parameters-only, --strict-parameter-validation

For the full catalog with allowed values, defaults, and config paths:
  bash examples/controlnet_construct/run_pipeline_example.sh --print-parameter-groups
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_pipeline_example_help_shows_compact_parameter_group_index -v
```

Expected: PASS.

- [ ] **Step 5: Run focused pipeline wrapper tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add examples/controlnet_construct/run_pipeline_example.sh tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "docs: add run pipeline help group index"
```

## Task 2: Tighten Catalog Detail And Coverage For Run Pipeline

**Files:**
- Modify: `examples/controlnet_construct/print_parameter_catalog.py`
- Modify: `examples/controlnet_construct/parameter_catalog.py`
- Test: `tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py`

- [ ] **Step 1: Write catalog detail and coverage tests**

Add these tests to `ControlNetParameterCatalogUnitTest`:

```python
    def test_catalog_text_prints_canonical_names_defaults_allowed_values_and_config_paths(self):
        script_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "print_parameter_catalog.py"

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--entrypoint",
                "run_pipeline_example",
                "--format",
                "text",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--matcher-method", result.stdout)
        self.assertIn("name: matcher_method", result.stdout)
        self.assertIn("allowed: bf", result.stdout)
        self.assertIn("config: ImageMatch.matcher_method", result.stdout)
        self.assertIn("--strict-parameter-validation", result.stdout)
        self.assertIn("default: False", result.stdout)

    def test_run_pipeline_catalog_covers_wrapper_validation_surface(self):
        from controlnet_construct.parameter_catalog import PARAMETER_BY_NAME

        expected_fields = {
            "deep_match_mode",
            "deep_match_temp_root_dir",
            "deep_match_manifest_dir",
            "deep_match_manifest_summary",
            "match_preset_path",
            "matcher_method",
            "deep_match_config_path",
            "valid_pixel_percent_threshold",
            "invalid_pixel_radius",
            "enable_low_resolution_offset_estimation",
            "low_resolution_level",
            "low_resolution_max_mean_reprojection_error_pixels",
            "low_resolution_min_retained_match_count",
            "low_resolution_max_mean_projected_offset_meters",
            "adaptive_routing_profile",
            "use_parallel_cpu",
            "num_worker_parallel_cpu",
            "visualization_mode",
            "memory_profile",
            "visualization_target_long_edge",
            "preview_crop_margin_pixels",
            "preview_cache_source",
            "pair_id_start",
            "merged_net",
            "merge_script",
            "merge_log",
            "pair_list",
            "timing_json",
            "skip_final_merge",
            "post_merge_control_measure",
            "post_merge_output",
            "post_merge_decimals",
            "strict_parameter_validation",
        }

        missing = sorted(field for field in expected_fields if field not in PARAMETER_BY_NAME)
        self.assertEqual(missing, [])
        for field in expected_fields:
            self.assertIn("run_pipeline_example", PARAMETER_BY_NAME[field].entrypoints, field)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test -v
```

Expected: FAIL because catalog text does not yet include `name: matcher_method`. It may also reveal missing catalog fields; keep the failure list.

- [ ] **Step 3: Update detailed catalog text rendering**

In `examples/controlnet_construct/print_parameter_catalog.py`, update `format_grouped_help()` so each parameter includes the canonical name:

```python
        for parameter in parameters:
            display_name = parameter.cli_flag or parameter.name
            details = [parameter.help, f"name: {parameter.name}"]
            if parameter.allowed_values is not None:
                allowed_values = ", ".join(str(value) for value in parameter.allowed_values)
                details.append(f"allowed: {allowed_values}")
            if parameter.config_path:
                details.append(f"config: {parameter.config_path}")
            if parameter.default is not None:
                details.append(f"default: {parameter.default}")
            lines.append(f"  {display_name}: {'; '.join(details)}")
```

- [ ] **Step 4: Fill any missing catalog fields revealed by the test**

If `test_run_pipeline_catalog_covers_wrapper_validation_surface` reports missing fields, add only those fields to `PARAMETERS` in `examples/controlnet_construct/parameter_catalog.py`. Use the existing `_spec(...)` pattern and group each field according to the design:

```python
    _spec("deep_match_temp_root_dir", "pipeline", config_path=_image_match_path("deep_match_temp_root_dir"), entrypoints=(RUN_PIPELINE, IMAGE_MATCH), help="Root directory for exported deep-match tile payloads."),
    _spec("deep_match_manifest_dir", "pipeline", config_path=_image_match_path("deep_match_manifest_dir"), entrypoints=(RUN_PIPELINE,), help="Directory containing deep-match manifests."),
    _spec("deep_match_manifest_summary", "pipeline", config_path=_image_match_path("deep_match_manifest_summary"), entrypoints=(RUN_PIPELINE,), help="Manifest summary JSON path."),
    _spec("post_merge_control_measure", "pipeline", value_type="bool", default=False, entrypoints=(RUN_PIPELINE,), help="Control measure run after merge."),
    _spec("post_merge_output", "pipeline", entrypoints=(RUN_PIPELINE,), help="Post-merge control-measure output path."),
    _spec("post_merge_decimals", "pipeline", value_type="int", min_value=0, entrypoints=(RUN_PIPELINE,), help="Decimal precision for post-merge output."),
```

Do not add unrelated fields outside the failing list.

- [ ] **Step 5: Run catalog tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add examples/controlnet_construct/print_parameter_catalog.py examples/controlnet_construct/parameter_catalog.py tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py
git commit -m "test: cover run pipeline parameter catalog details"
```

## Task 3: Make Inactive Explicit CLI Values Errors

**Files:**
- Modify: `examples/controlnet_construct/parameter_validation.py`
- Test: `tests/unitTest/controlnet_construct_parameter_validation_unit_test.py`

- [ ] **Step 1: Rewrite inactive-parameter severity tests**

In `tests/unitTest/controlnet_construct_parameter_validation_unit_test.py`, replace `test_inactive_low_resolution_values_warn_without_strict_validation` with these two tests:

```python
    def test_inactive_low_resolution_config_values_warn_without_strict_validation(self):
        from controlnet_construct.parameter_validation import validate_parameters

        result = validate_parameters(
            "run_pipeline_example",
            config_values={"enable_low_resolution_offset_estimation": False, "low_resolution_level": 4},
        )

        self.assertFalse(result.has_errors, result.error_text())
        self.assertIn("low_resolution_level", result.warning_text())
        self.assertIn("enable_low_resolution_offset_estimation is false", result.warning_text())

    def test_inactive_low_resolution_cli_values_error_without_strict_validation(self):
        from controlnet_construct.parameter_validation import validate_parameters

        result = validate_parameters(
            "run_pipeline_example",
            cli_values={"enable_low_resolution_offset_estimation": False, "low_resolution_level": 4},
        )

        self.assertTrue(result.has_errors)
        self.assertIn("low_resolution_level", result.error_text())
        self.assertIn("explicit CLI", result.error_text())
```

Add one GPU provenance test:

```python
    def test_inactive_gpu_config_values_warn_but_cli_values_error(self):
        from controlnet_construct.parameter_validation import validate_parameters

        config_result = validate_parameters(
            "run_pipeline_example",
            config_values={"use_gpu": False, "gpu_batch_size": 8},
        )
        self.assertFalse(config_result.has_errors, config_result.error_text())
        self.assertIn("gpu_batch_size", config_result.warning_text())

        cli_result = validate_parameters(
            "run_pipeline_example",
            cli_values={"use_gpu": False, "gpu_batch_size": 8},
        )
        self.assertTrue(cli_result.has_errors)
        self.assertIn("gpu_batch_size", cli_result.error_text())
        self.assertIn("explicit CLI", cli_result.error_text())
```

- [ ] **Step 2: Run validation tests to verify they fail**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_parameter_validation_unit_test -v
```

Expected: FAIL because inactive explicit CLI values are still warnings.

- [ ] **Step 3: Implement provenance-driven inactive severity**

In `examples/controlnet_construct/parameter_validation.py`, change the call site:

```python
    _collect_inactive_parameter_warnings(values, provenance, spec_by_name, warnings)
```

to:

```python
    _collect_inactive_parameter_messages(values, provenance, spec_by_name, warnings, errors)
```

Replace `_collect_inactive_parameter_warnings(...)` with:

```python
def _collect_inactive_parameter_messages(
    values: dict[str, Any],
    provenance: dict[str, str],
    spec_by_name: dict[str, Any],
    warnings: list[ValidationMessage],
    errors: list[ValidationMessage],
) -> None:
    def add_inactive_message(name: str, message: str) -> None:
        if provenance.get(name) == "cli":
            errors.append(ValidationMessage(name, f"explicit CLI {message}"))
        else:
            warnings.append(ValidationMessage(name, message))

    if values.get("enable_low_resolution_offset_estimation") is False:
        for name in sorted(spec_by_name):
            if name.startswith("low_resolution_") or name in ("left_low_resolution_dom", "right_low_resolution_dom"):
                if _is_explicit_value(provenance, name):
                    add_inactive_message(
                        name,
                        f"{name} was explicitly set while enable_low_resolution_offset_estimation is false",
                    )

    if values.get("use_gpu") is False:
        for name in sorted(spec_by_name):
            if name.startswith("gpu_") and _is_explicit_value(provenance, name):
                add_inactive_message(name, f"{name} was explicitly set while use_gpu is false")

    if values.get("use_parallel_cpu") is False and _is_explicit_value(provenance, "num_worker_parallel_cpu"):
        add_inactive_message(
            "num_worker_parallel_cpu",
            "num_worker_parallel_cpu was explicitly set while use_parallel_cpu is false",
        )

    if values.get("deep_match_mode") == "direct":
        for name in (
            "deep_match_temp_root_dir",
            "deep_match_manifest_dir",
            "deep_match_manifest",
            "deep_match_manifest_summary",
        ):
            if name in spec_by_name and _is_explicit_value(provenance, name):
                add_inactive_message(
                    name,
                    f"{name} was explicitly set while deep_match_mode is direct",
                )

    if values.get("visualization_mode") == "full":
        for name in _REDUCED_PREVIEW_FIELDS:
            if name in spec_by_name and _is_explicit_value(provenance, name):
                add_inactive_message(
                    name,
                    f"{name} was explicitly set while visualization_mode is full",
                )

    if values.get("post_merge_control_measure") in (False, None, ""):
        for name in ("post_merge_output", "post_merge_decimals"):
            if name in spec_by_name and _is_explicit_value(provenance, name):
                add_inactive_message(
                    name,
                    f"{name} was explicitly set while post_merge_control_measure is false",
                )
```

- [ ] **Step 4: Run validation tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_parameter_validation_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/controlnet_construct/parameter_validation.py tests/unitTest/controlnet_construct_parameter_validation_unit_test.py
git commit -m "feat: treat inactive CLI parameters as validation errors"
```

## Task 4: Complete Wrapper Validation Payload Provenance

**Files:**
- Modify: `examples/controlnet_construct/run_pipeline_example.sh`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Write wrapper provenance tests**

Add these tests to `ControlNetConstructPipelineUnitTest`:

```python
    def test_run_pipeline_example_inactive_cli_low_resolution_value_errors_without_strict(self):
        result = self._run_pipeline_validate_parameters_only(["--low-resolution-level", "4"])

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("low_resolution_level", result.stderr)
        self.assertIn("explicit CLI", result.stderr)

    def test_run_pipeline_example_inactive_config_low_resolution_value_warns_without_strict(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()
            (work_dir / "original_images.lis").write_text("/tmp/left.cub\n/tmp/right.cub\n", encoding="utf-8")
            (work_dir / "doms.lis").write_text("/tmp/left_dom.cub\n/tmp/right_dom.cub\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "inactive_config_lowres_unit",
                        "TargetName": "Mars",
                        "UserName": "unit",
                        "ImageMatch": {
                            "matcher_method": "bf",
                            "enable_low_resolution_offset_estimation": False,
                            "low_resolution_level": 4,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--validate-parameters-only",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("warning:", result.stderr)
        self.assertIn("low_resolution_level", result.stderr)

    def test_run_pipeline_example_deep_match_manifest_dir_is_inactive_in_direct_mode(self):
        result = self._run_pipeline_validate_parameters_only(
            ["--deep-match-manifest-dir", "/tmp/deep-match-manifests"]
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("deep_match_manifest_dir", result.stderr)
        self.assertIn("deep_match_mode is direct", result.stderr)
```

- [ ] **Step 2: Run wrapper tests to verify failures**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_pipeline_example_inactive_cli_low_resolution_value_errors_without_strict tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_pipeline_example_inactive_config_low_resolution_value_warns_without_strict tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_pipeline_example_deep_match_manifest_dir_is_inactive_in_direct_mode -v
```

Expected: FAIL until the wrapper payload records these values with correct provenance.

- [ ] **Step 3: Add explicit markers for wrapper-owned pipeline fields**

In `main()` local variable declarations in `run_pipeline_example.sh`, add:

```bash
  local explicit_deep_match_mode=""
  local explicit_deep_match_temp_root_dir=""
  local explicit_deep_match_manifest_dir=""
  local explicit_deep_match_manifest_summary=""
  local explicit_skip_final_merge=""
  local explicit_post_merge_control_measure=""
  local explicit_post_merge_output=""
  local explicit_post_merge_decimals=""
```

In the argument parser cases, set those markers:

```bash
      --deep-match-mode)
        [[ $# -ge 2 ]] || die "missing value for --deep-match-mode"
        DEEP_MATCH_MODE=$2
        explicit_deep_match_mode=$2
        shift 2
        ;;
      --deep-match-temp-root-dir)
        [[ $# -ge 2 ]] || die "missing value for --deep-match-temp-root-dir"
        deep_match_temp_root_dir_input=$2
        explicit_deep_match_temp_root_dir=$2
        shift 2
        ;;
      --deep-match-manifest-dir)
        [[ $# -ge 2 ]] || die "missing value for --deep-match-manifest-dir"
        deep_match_manifest_dir_input=$2
        explicit_deep_match_manifest_dir=$2
        shift 2
        ;;
      --deep-match-manifest-summary)
        [[ $# -ge 2 ]] || die "missing value for --deep-match-manifest-summary"
        deep_match_manifest_summary_input=$2
        explicit_deep_match_manifest_summary=$2
        shift 2
        ;;
      --skip-final-merge)
        SKIP_FINAL_MERGE="1"
        explicit_skip_final_merge="1"
        shift
        ;;
      --post-merge-control-measure)
        POST_MERGE_CONTROL_MEASURE="1"
        explicit_post_merge_control_measure="1"
        shift
        ;;
      --post-merge-output)
        [[ $# -ge 2 ]] || die "missing value for --post-merge-output"
        post_merge_output_input=$2
        explicit_post_merge_output=$2
        shift 2
        ;;
      --post-merge-decimals)
        [[ $# -ge 2 ]] || die "missing value for --post-merge-decimals"
        POST_MERGE_DECIMALS=$2
        explicit_post_merge_decimals=$2
        shift 2
        ;;
```

- [ ] **Step 4: Add these fields to validation payload construction**

In `build_parameter_validation_payload()`, extend `cli_sources`:

```python
    "deep_match_mode": ("explicit_deep_match_mode", "DEEP_MATCH_MODE"),
    "deep_match_temp_root_dir": ("explicit_deep_match_temp_root_dir", "DEEP_MATCH_TEMP_ROOT_DIR"),
    "deep_match_manifest_dir": ("explicit_deep_match_manifest_dir", "DEEP_MATCH_MANIFEST_DIR"),
    "deep_match_manifest_summary": ("explicit_deep_match_manifest_summary", "DEEP_MATCH_MANIFEST_SUMMARY"),
    "skip_final_merge": ("explicit_skip_final_merge", "SKIP_FINAL_MERGE"),
    "post_merge_control_measure": ("explicit_post_merge_control_measure", "POST_MERGE_CONTROL_MEASURE"),
    "post_merge_output": ("explicit_post_merge_output", "POST_MERGE_OUTPUT_PATH"),
    "post_merge_decimals": ("explicit_post_merge_decimals", "POST_MERGE_DECIMALS"),
```

Extend `config_sources` only for fields already read from config in the wrapper. Do not invent new config extraction in this task.

- [ ] **Step 5: Export the new marker and value variables before validation**

Near the existing `export explicit_...` block, add:

```bash
  export explicit_deep_match_mode explicit_deep_match_temp_root_dir explicit_deep_match_manifest_dir explicit_deep_match_manifest_summary
  export explicit_skip_final_merge explicit_post_merge_control_measure explicit_post_merge_output explicit_post_merge_decimals
  export DEEP_MATCH_MODE DEEP_MATCH_TEMP_ROOT_DIR DEEP_MATCH_MANIFEST_DIR DEEP_MATCH_MANIFEST_SUMMARY
  export SKIP_FINAL_MERGE POST_MERGE_CONTROL_MEASURE POST_MERGE_OUTPUT_PATH POST_MERGE_DECIMALS
```

- [ ] **Step 6: Run wrapper tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add examples/controlnet_construct/run_pipeline_example.sh tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: complete run pipeline validation provenance"
```

## Task 5: Final Verification And Review Prep

**Files:**
- No new files unless earlier tasks reveal a focused documentation mismatch.

- [ ] **Step 1: Run catalog tests**

```bash
python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test -v
```

Expected: PASS.

- [ ] **Step 2: Run validation tests**

```bash
python -m unittest tests.unitTest.controlnet_construct_parameter_validation_unit_test -v
```

Expected: PASS.

- [ ] **Step 3: Run pipeline wrapper tests**

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: PASS.

- [ ] **Step 4: Run optional matching tests if any implementation touched `examples/image_match/image_match.py`**

```bash
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Expected: PASS. Skip this command only if no task changed `examples/image_match/image_match.py`.

- [ ] **Step 5: Check diff hygiene and branch state**

```bash
git diff --check
git status --short --branch
git log --oneline --decorate -8
```

Expected: `git diff --check` exits 0. Status shows only the feature branch and no unstaged changes.

- [ ] **Step 6: Commit any final docs or test-only cleanup**

Only run this if Task 5 produced an intentional file change in the run-pipeline
parameter hardening scope. Stage only the files that actually changed from this
set:

```bash
git add \
  docs/superpowers/plans/2026-05-26-run-pipeline-parameter-help-validation.md \
  docs/superpowers/specs/2026-05-26-run-pipeline-parameter-help-validation-design.md \
  examples/controlnet_construct/run_pipeline_example.sh \
  examples/controlnet_construct/parameter_catalog.py \
  examples/controlnet_construct/parameter_validation.py \
  examples/controlnet_construct/print_parameter_catalog.py \
  tests/unitTest/controlnet_construct_pipeline_unit_test.py \
  tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py \
  tests/unitTest/controlnet_construct_parameter_validation_unit_test.py
git commit -m "docs: update run pipeline parameter validation notes"
```

Expected: no commit is needed if verification produced no changes.
