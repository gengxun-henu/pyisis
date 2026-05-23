# Raw Original Image Adaptive Official Deep Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable adaptive texture/lighting routing in the raw/original image ControlNet path, using classic SIFT fallback plus official LightGlue and external official LoFTR presets.

**Architecture:** Reuse the existing `match_ori_pair()` -> `match_dom_pair(image_space="ori")` path and add an adaptive route branch that uses original cubes as diagnostic sources when no DOM preview cubes exist. Then expose the existing adaptive/deep config fields through `controlnet_stereopair.py from-ori-match` and `run_ori_match_pipeline_example.sh`, while documenting the official preset surface and deprecating legacy preset recommendations.

**Tech Stack:** Bash wrappers, Python `argparse`, ISIS `ip.Cube`, existing `examples/image_match` adaptive routing helpers, `unittest`, JSON config/preset files.

---

## File Structure

- Modify `examples/image_match/image_match.py`
  - Add raw-source adaptive route support inside `_resolve_adaptive_route_for_pair`.
  - Pass `image_space`, left/right input paths, and diagnostic source metadata from `match_dom_pair`.
  - Keep DOM behavior unchanged.
- Modify `examples/controlnet_construct/controlnet_stereopair.py`
  - Add `from-ori-match` parser flags for adaptive routing, deep config path, and adaptive deep preset mapping.
  - Forward those values to `match_ori_pair_to_key_files`.
  - Include adaptive/deep metadata in the per-pair report through the existing `match` payload.
- Modify `examples/controlnet_construct/run_ori_match_pipeline_example.sh`
  - Stop rejecting adaptive/deep direct flags.
  - Parse config values from `ImageMatch` with the same precedence pattern used by DOM wrappers.
  - Forward adaptive/deep direct options into each `from-ori-match` command.
  - Include adaptive/deep fields in `ori_match_batch_summary.json`.
- Modify `examples/controlnet_construct/usage.md`
  - Replace the first-version limitation text with raw adaptive usage and official preset guidance.
  - Mark `loftr_default.json` as Kornia compatibility, not the official LoFTR route.
- Modify `examples/controlnet_construct/recommended_batch_templates.md`
  - Point recommended learned matching examples to official LightGlue and external LoFTR presets.
- Modify `examples/controlnet_construct/experiments/matcher_comparison.example.json`
  - Remove recommended references to non-official LightGlue and SuperGlue presets from the example method set.
- Modify tests in `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
  - Add raw wrapper dry-run forwarding tests.
  - Add `from-ori-match` parser and dispatch forwarding tests.
  - Update prior rejection test to reject only export/import deep modes, not direct adaptive/deep config.
- Modify tests in `tests/unitTest/controlnet_construct_matching_unit_test.py`
  - Add direct `match_ori_pair` adaptive routing tests using mocks.
- No preset files are deleted in this implementation phase.

---

### Task 1: Add Raw Adaptive Route Resolution

**Files:**
- Modify: `examples/image_match/image_match.py`
- Test: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Write failing tests for raw adaptive route behavior**

Add these imports near the existing image-match imports in `tests/unitTest/controlnet_construct_matching_unit_test.py`:

```python
from image_match.lighting_difference import SolarGeometry
from image_match.texture_sparseness import ImageSparsenessSummary
```

Add these tests to `ControlNetConstructMatchingUnitTest`:

```python
    def test_match_ori_pair_uses_raw_inputs_for_adaptive_routing(self):
        image = _build_textured_test_image(96, 96)
        accepted_points = tuple(Keypoint(float(index), float(index)) for index in range(40))
        fake_tile_result = tile_matching_module.TileMatchResult(
            stats=tile_matching_module.TileMatchStats(
                0, 0, 96, 96, 0, 0, 0, 0, 96 * 96, 96 * 96,
                1.0, 1.0, 40, 40, 40, "matched",
            ),
            left_points=accepted_points,
            right_points=accepted_points,
        )

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_raw_adaptive.cub",
                right_name="right_raw_adaptive.cub",
            )

            with mock.patch.object(
                image_match,
                "_compute_texture_probe_from_cube_path",
                return_value=image_match.ImageTextureProbe(
                    keypoint_count=200,
                    valid_pixel_count=96 * 96,
                    total_pixel_count=96 * 96,
                    keypoint_density=0.02,
                    mean_gradient=24.0,
                    laplacian_variance=180.0,
                    entropy=3.5,
                    valid_pixel_ratio=1.0,
                    real_texture_score=0.6,
                ),
            ), mock.patch.object(
                image_match,
                "_compute_texture_sparseness_and_geometry_from_cube_path",
                side_effect=[
                    (
                        ImageSparsenessSummary(
                            image_width=96,
                            image_height=96,
                            tile_total_count=1,
                            tile_valid_count=1,
                            image_texture_sparseness=0.25,
                            sparseness_quantiles={"p10": 0.25, "p50": 0.25, "p90": 0.25, "max": 0.25},
                            tile_metrics=(),
                            min_valid_pixel_ratio=0.3,
                        ),
                        SolarGeometry(30.0, 10.0, "Instrument", "SolarElevation", "SolarAzimuth"),
                        None,
                    ),
                    (
                        ImageSparsenessSummary(
                            image_width=96,
                            image_height=96,
                            tile_total_count=1,
                            tile_valid_count=1,
                            image_texture_sparseness=0.30,
                            sparseness_quantiles={"p10": 0.30, "p50": 0.30, "p90": 0.30, "max": 0.30},
                            tile_metrics=(),
                            min_valid_pixel_ratio=0.3,
                        ),
                        SolarGeometry(33.0, 15.0, "Instrument", "SolarElevation", "SolarAzimuth"),
                        None,
                    ),
                ],
            ) as diag_mock, mock.patch.object(
                image_match,
                "_run_serial_tile_match_tasks",
                return_value=[fake_tile_result],
            ) as serial_mock:
                _, _, summary = image_match.match_ori_pair(
                    left_path,
                    right_path,
                    matcher_method="flann",
                    enable_adaptive_routing=True,
                    adaptive_routing_profile="balanced",
                    adaptive_routing_deep_presets={
                        "lightglue": "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                        "loftr": "examples/controlnet_construct/presets/loftr_external_outdoor.json",
                    },
                    use_parallel_cpu=False,
                    max_image_dimension=512,
                    min_valid_pixels=32,
                )

        self.assertEqual(diag_mock.call_args_list[0].args[0], left_path)
        self.assertEqual(diag_mock.call_args_list[1].args[0], right_path)
        self.assertEqual(serial_mock.call_args.kwargs["matcher_method"], "flann")
        adaptive = summary["adaptive_routing"]
        self.assertEqual(adaptive["status"], "routed")
        self.assertEqual(adaptive["preview_sources"]["left"], str(left_path))
        self.assertEqual(adaptive["preview_sources"]["right"], str(right_path))
        self.assertEqual(adaptive["preview_sources"]["source_type"], "raw_original_cube")
        self.assertEqual(adaptive["sidecar"]["texture_sparseness"]["pair_texture_sparseness"], 0.30)
        self.assertIsNotNone(adaptive["sidecar"]["lighting_difference"]["lighting_difference_score"])

    def test_match_ori_pair_adaptive_routing_falls_back_to_requested_matcher_when_raw_diagnostics_fail(self):
        image = _build_textured_test_image(96, 96)
        accepted_points = tuple(Keypoint(float(index), float(index)) for index in range(20))
        fake_tile_result = tile_matching_module.TileMatchResult(
            stats=tile_matching_module.TileMatchStats(
                0, 0, 96, 96, 0, 0, 0, 0, 96 * 96, 96 * 96,
                1.0, 1.0, 20, 20, 20, "matched",
            ),
            left_points=accepted_points,
            right_points=accepted_points,
        )

        with temporary_directory() as temp_dir:
            left_path, right_path = _write_projected_dom_pair(
                temp_dir,
                image,
                pixel_type=ip.PixelType.UnsignedByte,
                left_name="left_raw_adaptive_error.cub",
                right_name="right_raw_adaptive_error.cub",
            )

            with mock.patch.object(
                image_match,
                "_compute_texture_probe_from_cube_path",
                side_effect=RuntimeError("synthetic diagnostic failure"),
            ), mock.patch.object(
                image_match,
                "_run_serial_tile_match_tasks",
                return_value=[fake_tile_result],
            ) as serial_mock:
                _, _, summary = image_match.match_ori_pair(
                    left_path,
                    right_path,
                    matcher_method="flann",
                    enable_adaptive_routing=True,
                    use_parallel_cpu=False,
                    max_image_dimension=512,
                    min_valid_pixels=32,
                )

        self.assertEqual(serial_mock.call_args.kwargs["matcher_method"], "flann")
        self.assertEqual(summary["adaptive_routing"]["status"], "routing_failed")
        self.assertEqual(summary["adaptive_routing"]["selected_initial_matcher"], "flann")
        self.assertIn("synthetic diagnostic failure", summary["adaptive_routing"]["reason"])
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_ori_pair_uses_raw_inputs_for_adaptive_routing tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_ori_pair_adaptive_routing_falls_back_to_requested_matcher_when_raw_diagnostics_fail -v
```

Expected: the first test fails because raw adaptive routing reports `skipped_missing_previews` instead of using the original cube paths.

- [ ] **Step 3: Implement raw diagnostic source support**

In `examples/image_match/image_match.py`, change `_resolve_adaptive_route_for_pair` signature to:

```python
def _resolve_adaptive_route_for_pair(
    *,
    enable_adaptive_routing: bool,
    requested_matcher_method: str,
    adaptive_routing_deep_presets: dict[str, str] | None,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    low_resolution_offset_summary: dict[str, object],
    left_low_resolution_dom: str | Path | None,
    right_low_resolution_dom: str | Path | None,
    image_space: str = "dom",
    left_source_path: str | Path | None = None,
    right_source_path: str | Path | None = None,
) -> tuple[str, dict[str, object] | None]:
```

Replace the preview-source resolution block with:

```python
    summary_left_preview = str(low_resolution_offset_summary.get("left_low_resolution_dom", "") or "")
    summary_right_preview = str(low_resolution_offset_summary.get("right_low_resolution_dom", "") or "")
    resolved_left_preview = summary_left_preview or (str(left_low_resolution_dom) if left_low_resolution_dom is not None else "")
    resolved_right_preview = summary_right_preview or (str(right_low_resolution_dom) if right_low_resolution_dom is not None else "")
    normalized_image_space = str(image_space or "dom").strip().lower()
    preview_source_type = "low_resolution_dom"
    if normalized_image_space == "ori" and (not resolved_left_preview or not resolved_right_preview):
        resolved_left_preview = str(left_source_path) if left_source_path is not None else ""
        resolved_right_preview = str(right_source_path) if right_source_path is not None else ""
        preview_source_type = "raw_original_cube"

    if not resolved_left_preview or not resolved_right_preview:
        return requested_matcher_method, {
            "enabled": True,
            "status": "skipped_missing_previews",
            "requested_matcher": requested_matcher_method,
            "selected_initial_matcher": requested_matcher_method,
            "selected_deep_match_config_path": None,
            "route_reason": (
                "Adaptive routing requires low-resolution preview DOMs for DOM-space matching "
                "or original cube paths for raw image-space matching."
            ),
            "reason": (
                "Adaptive routing requires low-resolution preview DOMs for DOM-space matching "
                "or original cube paths for raw image-space matching."
            ),
        }
```

In the returned routed and failed summaries, change `preview_sources` to include the source type:

```python
            "preview_sources": {
                "left": resolved_left_preview,
                "right": resolved_right_preview,
                "source_type": preview_source_type,
            },
```

In `match_dom_pair`, update the `_resolve_adaptive_route_for_pair(...)` call:

```python
        resolved_matcher_method, adaptive_routing_summary = _resolve_adaptive_route_for_pair(
            enable_adaptive_routing=bool(enable_adaptive_routing),
            requested_matcher_method=resolved_requested_matcher_method,
            adaptive_routing_deep_presets=resolved_adaptive_routing_deep_presets,
            band=band,
            invalid_values=invalid_values,
            special_pixel_abs_threshold=special_pixel_abs_threshold,
            low_resolution_offset_summary=low_resolution_offset_summary,
            left_low_resolution_dom=resolved_left_low_resolution_dom,
            right_low_resolution_dom=resolved_right_low_resolution_dom,
            image_space=image_backend.space,
            left_source_path=left_dom_path,
            right_source_path=right_dom_path,
        )
```

- [ ] **Step 4: Run focused tests and verify they pass**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_ori_pair_uses_raw_inputs_for_adaptive_routing tests.unitTest.controlnet_construct_matching_unit_test.ControlNetConstructMatchingUnitTest.test_match_ori_pair_adaptive_routing_falls_back_to_requested_matcher_when_raw_diagnostics_fail -v
```

Expected: both tests pass.

- [ ] **Step 5: Run DOM adaptive regression tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -k adaptive -v
```

Expected: existing DOM adaptive tests still pass.

- [ ] **Step 6: Commit**

```bash
git add examples/image_match/image_match.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "feat: route raw image adaptive diagnostics"
```

---

### Task 2: Forward Adaptive and Deep Direct Options Through `from-ori-match`

**Files:**
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Write parser and dispatch tests**

Add these tests near the existing `from-ori-match` tests in `tests/unitTest/controlnet_construct_pipeline_unit_test.py`:

```python
    def test_controlnet_stereopair_parser_accepts_from_ori_match_adaptive_and_deep_config(self):
        parser = importlib.import_module("controlnet_construct.controlnet_stereopair").build_argument_parser()
        parsed = parser.parse_args(
            [
                "from-ori-match",
                "left.cub",
                "right.cub",
                "config.json",
                "out.net",
                "--adaptive-routing",
                "--adaptive-routing-profile",
                "strict",
                "--deep-match-config-path",
                "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                "--adaptive-routing-deep-preset",
                "lightglue=examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                "--adaptive-routing-deep-preset",
                "loftr=examples/controlnet_construct/presets/loftr_external_outdoor.json",
            ]
        )

        self.assertEqual(parsed.command, "from-ori-match")
        self.assertTrue(parsed.enable_adaptive_routing)
        self.assertEqual(parsed.adaptive_routing_profile, "strict")
        self.assertEqual(
            parsed.deep_match_config_path,
            "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
        )
        self.assertEqual(
            parsed.adaptive_routing_deep_preset,
            [
                "lightglue=examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                "loftr=examples/controlnet_construct/presets/loftr_external_outdoor.json",
            ],
        )

    def test_controlnet_stereopair_main_from_ori_match_forwards_adaptive_and_deep_options(self):
        with temporary_directory() as temp_dir:
            left = temp_dir / "left.cub"
            right = temp_dir / "right.cub"
            config = temp_dir / "config.json"
            output_net = temp_dir / "out.net"
            left.write_text("left", encoding="utf-8")
            right.write_text("right", encoding="utf-8")
            config.write_text(
                json.dumps({"NetworkId": "raw_adaptive", "TargetName": "Moon", "UserName": "tester"}),
                encoding="utf-8",
            )

            with mock.patch(
                "controlnet_construct.controlnet_stereopair.match_ori_pair_to_key_files",
                return_value={
                    "status": "matched",
                    "point_count": 4,
                    "adaptive_routing": {"status": "routed"},
                    "deep_match_config_path": "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                    "left_output_key": str(temp_dir / "left.key"),
                    "right_output_key": str(temp_dir / "right.key"),
                },
            ) as match_mock, mock.patch(
                "controlnet_construct.controlnet_stereopair.build_controlnet_for_stereo_pair",
                return_value={"point_count": 4, "output_net": str(output_net)},
            ):
                controlnet_stereopair_main(
                    [
                        "from-ori-match",
                        str(left),
                        str(right),
                        str(config),
                        str(output_net),
                        "--adaptive-routing",
                        "--adaptive-routing-profile",
                        "strict",
                        "--deep-match-config-path",
                        "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                        "--adaptive-routing-deep-preset",
                        "lightglue=examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                        "--adaptive-routing-deep-preset",
                        "loftr=examples/controlnet_construct/presets/loftr_external_outdoor.json",
                    ]
                )

        kwargs = match_mock.call_args.kwargs
        self.assertTrue(kwargs["enable_adaptive_routing"])
        self.assertEqual(kwargs["adaptive_routing_profile"], "strict")
        self.assertEqual(
            kwargs["deep_match_config_path"],
            "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
        )
        self.assertEqual(
            kwargs["adaptive_routing_deep_presets"],
            {
                "lightglue": "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                "loftr": "examples/controlnet_construct/presets/loftr_external_outdoor.json",
            },
        )
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_controlnet_stereopair_parser_accepts_from_ori_match_adaptive_and_deep_config tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_controlnet_stereopair_main_from_ori_match_forwards_adaptive_and_deep_options -v
```

Expected: parser rejects the new options.

- [ ] **Step 3: Add parser flags and preset map parser**

In `examples/controlnet_construct/controlnet_stereopair.py`, add this helper near parser helpers:

```python
def _parse_adaptive_routing_deep_preset_entries(entries: list[str] | None) -> dict[str, str]:
    presets: dict[str, str] = {}
    for entry in entries or []:
        if "=" not in entry:
            raise ValueError(
                "--adaptive-routing-deep-preset entries must use KEY=PATH, "
                f"got {entry!r}."
            )
        key, value = entry.split("=", 1)
        normalized_key = key.strip().lower()
        resolved_value = value.strip()
        if not normalized_key or not resolved_value:
            raise ValueError(
                "--adaptive-routing-deep-preset entries must include both key and path, "
                f"got {entry!r}."
            )
        presets[normalized_key] = resolved_value
    return presets
```

In `_build_from_original_match_parser`, add:

```python
    parser.set_defaults(enable_adaptive_routing=False)
    parser.add_argument("--adaptive-routing", dest="enable_adaptive_routing", action="store_true", help="Enable adaptive texture/lighting routing for raw image matching.")
    parser.add_argument("--no-adaptive-routing", dest="enable_adaptive_routing", action="store_false", help="Disable adaptive texture/lighting routing for raw image matching.")
    parser.add_argument("--adaptive-routing-profile", default="balanced", choices=("balanced", "strict", "relaxed", "fast"), help="Adaptive routing quality profile.")
    parser.add_argument("--deep-match-config-path", default=None, help="Optional deep matcher preset JSON path for direct raw image matching.")
    parser.add_argument(
        "--adaptive-routing-deep-preset",
        action="append",
        default=[],
        help="Adaptive deep preset mapping in KEY=PATH form. Repeat for lightglue and loftr.",
    )
```

- [ ] **Step 4: Forward values to `match_ori_pair_to_key_files`**

In the `args.command == "from-ori-match"` block, add before `match_ori_pair_to_key_files(...)`:

```python
        try:
            adaptive_routing_deep_presets = _parse_adaptive_routing_deep_preset_entries(
                args.adaptive_routing_deep_preset
            )
        except ValueError as exc:
            parser.error(str(exc))
```

Add these kwargs to the `match_ori_pair_to_key_files(...)` call:

```python
            enable_adaptive_routing=args.enable_adaptive_routing,
            adaptive_routing_profile=args.adaptive_routing_profile,
            adaptive_routing_deep_presets=adaptive_routing_deep_presets,
            deep_match_config_path=args.deep_match_config_path,
            deep_match_mode="direct",
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_controlnet_stereopair_parser_accepts_from_ori_match_adaptive_and_deep_config tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_controlnet_stereopair_main_from_ori_match_forwards_adaptive_and_deep_options -v
```

Expected: both tests pass.

- [ ] **Step 6: Run existing from-ori tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -k from_ori_match -v
```

Expected: existing `from-ori-match` tests pass.

- [ ] **Step 7: Commit**

```bash
git add examples/controlnet_construct/controlnet_stereopair.py tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: forward raw adaptive match options"
```

---

### Task 3: Forward Raw Wrapper Config and CLI Options

**Files:**
- Modify: `examples/controlnet_construct/run_ori_match_pipeline_example.sh`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Replace the old rejection test**

Find `test_run_ori_match_pipeline_rejects_deep_only_flags` and replace it with:

```python
    def test_run_ori_match_pipeline_rejects_unsupported_deep_export_mode(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work_ori"
            work_dir.mkdir()
            original_list = work_dir / "original_images.lis"
            config_path = temp_dir / "config.json"
            original_list.write_text("", encoding="utf-8")
            config_path.write_text(
                json.dumps({"NetworkId": "raw_unit", "TargetName": "Moon", "UserName": "tester"}),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_ORI_MATCH_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--original-list",
                    str(original_list),
                    "--config",
                    str(config_path),
                    "--deep-match-mode",
                    "export",
                    "--dry-run",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--deep-match-mode currently supports only direct", result.stderr)
```

- [ ] **Step 2: Add raw wrapper dry-run forwarding test**

Add:

```python
    def test_run_ori_match_pipeline_forwards_adaptive_and_official_deep_presets(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work_ori"
            work_dir.mkdir()
            left = temp_dir / "left.cub"
            right = temp_dir / "right.cub"
            left.write_text("left", encoding="utf-8")
            right.write_text("right", encoding="utf-8")
            original_list = work_dir / "original_images.lis"
            overlap_list = work_dir / "images_overlap.lis"
            config_path = temp_dir / "config.json"
            original_list.write_text(f"{left}\n{right}\n", encoding="utf-8")
            overlap_list.write_text(f"{left},{right}\n", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "raw_adaptive_unit",
                        "TargetName": "Moon",
                        "UserName": "tester",
                        "ImageMatch": {
                            "enable_adaptive_routing": True,
                            "adaptive_routing_profile": "strict",
                            "matcher_method": "flann",
                            "deep_matcher_config_path": "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                            "adaptive_routing_deep_presets": {
                                "lightglue": "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
                                "loftr": "examples/controlnet_construct/presets/loftr_external_outdoor.json",
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "bash",
                    str(RUN_ORI_MATCH_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--original-list",
                    str(original_list),
                    "--images-overlap-list",
                    str(overlap_list),
                    "--config",
                    str(config_path),
                    "--dry-run",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            command_text = (work_dir / "command.sh").read_text(encoding="utf-8")
            parsed_commands = [
                shlex.split(line)
                for line in command_text.splitlines()
                if line and not line.startswith("#") and not line.startswith("set ")
            ]

        self.assertEqual(result.returncode, 0, result.stderr)
        pair_command = next(command for command in parsed_commands if "from-ori-match" in command)
        self.assertIn("--adaptive-routing", pair_command)
        self.assertIn("--adaptive-routing-profile", pair_command)
        self.assertEqual(pair_command[pair_command.index("--adaptive-routing-profile") + 1], "strict")
        self.assertIn("--deep-match-config-path", pair_command)
        self.assertEqual(
            pair_command[pair_command.index("--deep-match-config-path") + 1],
            "examples/controlnet_construct/presets/lightglue_official_superpoint.json",
        )
        preset_values = [
            pair_command[index + 1]
            for index, value in enumerate(pair_command)
            if value == "--adaptive-routing-deep-preset"
        ]
        self.assertIn(
            "lightglue=examples/controlnet_construct/presets/lightglue_official_superpoint.json",
            preset_values,
        )
        self.assertIn(
            "loftr=examples/controlnet_construct/presets/loftr_external_outdoor.json",
            preset_values,
        )
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_ori_match_pipeline_rejects_unsupported_deep_export_mode tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_ori_match_pipeline_forwards_adaptive_and_official_deep_presets -v
```

Expected: tests fail because the wrapper still rejects adaptive/deep flags and does not read those config values.

- [ ] **Step 4: Add config extraction helpers to raw wrapper**

In `examples/controlnet_construct/run_ori_match_pipeline_example.sh`, add after `resolve_path()`:

```bash
extract_image_match_config_value() {
  local config_path=$1
  local field_name=$2
  "$HOST_PYTHON_EXECUTABLE" - "$config_path" "$field_name" <<'PY'
import json
import sys
from pathlib import Path

config_path, field_name = sys.argv[1:]
payload = json.loads(Path(config_path).read_text(encoding="utf-8"))
section = payload.get("ImageMatch", {})
if not isinstance(section, dict) or field_name not in section:
    raise SystemExit(0)
value = section[field_name]
if isinstance(value, bool):
    print("1" if value else "0")
elif value is None:
    raise SystemExit(0)
elif isinstance(value, (dict, list)):
    print(json.dumps(value, ensure_ascii=False))
else:
    print(value)
PY
}

resolve_config_relative_path() {
  local value=$1
  local config_path=$2
  "$HOST_PYTHON_EXECUTABLE" - "$value" "$config_path" <<'PY'
from pathlib import Path
import sys

value, config_path = sys.argv[1:]
path = Path(value).expanduser()
if not path.is_absolute():
    path = Path(config_path).expanduser().resolve(strict=False).parent / path
print(path.resolve(strict=False))
PY
}

extract_adaptive_routing_deep_preset_args() {
  local config_path=$1
  "$HOST_PYTHON_EXECUTABLE" - "$config_path" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1]).expanduser().resolve(strict=False)
payload = json.loads(config_path.read_text(encoding="utf-8"))
section = payload.get("ImageMatch", {})
presets = section.get("adaptive_routing_deep_presets", {}) if isinstance(section, dict) else {}
if not isinstance(presets, dict):
    raise SystemExit(0)
for key, value in presets.items():
    if value in (None, ""):
        continue
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = config_path.parent / path
    print(f"{str(key).strip().lower()}={path.resolve(strict=False)}")
PY
}
```

- [ ] **Step 5: Add variables and CLI parsing**

Add variables near existing defaults:

```bash
ADAPTIVE_ROUTING="0"
ADAPTIVE_ROUTING_PROFILE="balanced"
DEEP_MATCHER_CONFIG_PATH=""
DEEP_MATCH_MODE="direct"
ADAPTIVE_ROUTING_DEEP_PRESET_ARGS=()
explicit_adaptive_routing=""
explicit_adaptive_routing_profile=""
explicit_deep_match_config_path=""
```

Add cases in the argument parser:

```bash
    --adaptive-routing) ADAPTIVE_ROUTING="1"; explicit_adaptive_routing="1"; shift ;;
    --no-adaptive-routing) ADAPTIVE_ROUTING="0"; explicit_adaptive_routing="1"; shift ;;
    --adaptive-routing-profile) [[ $# -ge 2 ]] || die "missing value for --adaptive-routing-profile"; ADAPTIVE_ROUTING_PROFILE=$2; explicit_adaptive_routing_profile="1"; shift 2 ;;
    --deep-match-config-path) [[ $# -ge 2 ]] || die "missing value for --deep-match-config-path"; DEEP_MATCHER_CONFIG_PATH=$2; explicit_deep_match_config_path="1"; shift 2 ;;
    --deep-match-mode) [[ $# -ge 2 ]] || die "missing value for --deep-match-mode"; DEEP_MATCH_MODE=$2; shift 2 ;;
    --adaptive-routing-deep-preset) [[ $# -ge 2 ]] || die "missing value for --adaptive-routing-deep-preset"; ADAPTIVE_ROUTING_DEEP_PRESET_ARGS+=("$2"); shift 2 ;;
```

Replace the old rejection case with:

```bash
    --deep-match-mode=*) DEEP_MATCH_MODE=${1#*=}; shift ;;
```

After resolving `CONFIG_PATH`, add:

```bash
case "$DEEP_MATCH_MODE" in
  direct) ;;
  *) die "--deep-match-mode currently supports only direct in the raw image space wrapper" ;;
esac

if [[ -z "$explicit_adaptive_routing" ]]; then
  config_enable_adaptive_routing=$(extract_image_match_config_value "$CONFIG_PATH" "enable_adaptive_routing")
  [[ -z "$config_enable_adaptive_routing" ]] || ADAPTIVE_ROUTING="$config_enable_adaptive_routing"
fi
if [[ -z "$explicit_adaptive_routing_profile" ]]; then
  config_adaptive_routing_profile=$(extract_image_match_config_value "$CONFIG_PATH" "adaptive_routing_profile")
  [[ -z "$config_adaptive_routing_profile" ]] || ADAPTIVE_ROUTING_PROFILE="$config_adaptive_routing_profile"
fi
if [[ -z "$explicit_deep_match_config_path" ]]; then
  config_deep_matcher_config_path=$(extract_image_match_config_value "$CONFIG_PATH" "deep_matcher_config_path")
  if [[ -n "$config_deep_matcher_config_path" ]]; then
    DEEP_MATCHER_CONFIG_PATH=$(resolve_config_relative_path "$config_deep_matcher_config_path" "$CONFIG_PATH")
  fi
elif [[ -n "$DEEP_MATCHER_CONFIG_PATH" ]]; then
  DEEP_MATCHER_CONFIG_PATH=$(resolve_path "$DEEP_MATCHER_CONFIG_PATH")
fi
if [[ "${#ADAPTIVE_ROUTING_DEEP_PRESET_ARGS[@]}" -eq 0 ]]; then
  while IFS= read -r preset_arg; do
    [[ -z "$preset_arg" ]] || ADAPTIVE_ROUTING_DEEP_PRESET_ARGS+=("$preset_arg")
  done < <(extract_adaptive_routing_deep_preset_args "$CONFIG_PATH")
fi
```

- [ ] **Step 6: Forward options in `build_match_args` and summary**

In `build_match_args`, add:

```bash
  if [[ "$ADAPTIVE_ROUTING" == "1" ]]; then
    match_args+=(--adaptive-routing)
  else
    match_args+=(--no-adaptive-routing)
  fi
  match_args+=(--adaptive-routing-profile "$ADAPTIVE_ROUTING_PROFILE")
  if [[ -n "$DEEP_MATCHER_CONFIG_PATH" ]]; then
    match_args+=(--deep-match-config-path "$DEEP_MATCHER_CONFIG_PATH")
  fi
  match_args+=(--deep-match-mode "$DEEP_MATCH_MODE")
  local preset_arg
  for preset_arg in "${ADAPTIVE_ROUTING_DEEP_PRESET_ARGS[@]}"; do
    match_args+=(--adaptive-routing-deep-preset "$preset_arg")
  done
```

Update the final summary Python invocation to pass `ADAPTIVE_ROUTING`, `ADAPTIVE_ROUTING_PROFILE`, `DEEP_MATCHER_CONFIG_PATH`, and `DEEP_MATCH_MODE`, then add these fields to `payload`:

```python
    "adaptive_routing": adaptive_routing == "1",
    "adaptive_routing_profile": adaptive_routing_profile,
    "deep_match_config_path": deep_match_config_path or None,
    "deep_match_mode": deep_match_mode,
```

- [ ] **Step 7: Run focused wrapper tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_ori_match_pipeline_rejects_unsupported_deep_export_mode tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_ori_match_pipeline_forwards_adaptive_and_official_deep_presets -v
```

Expected: both tests pass.

- [ ] **Step 8: Run all raw wrapper tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -k run_ori_match_pipeline -v
```

Expected: all raw wrapper tests pass.

- [ ] **Step 9: Commit**

```bash
git add examples/controlnet_construct/run_ori_match_pipeline_example.sh tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: expose raw adaptive wrapper options"
```

---

### Task 4: Update Official Preset Guidance and Deprecation Docs

**Files:**
- Modify: `examples/controlnet_construct/usage.md`
- Modify: `examples/controlnet_construct/recommended_batch_templates.md`
- Modify: `examples/controlnet_construct/experiments/matcher_comparison.example.json`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Add documentation guard test**

Add this test to `ControlNetConstructPipelineUnitTest`:

```python
    def test_recommended_docs_use_official_lightglue_and_external_loftr_presets(self):
        usage = (PROJECT_ROOT / "examples" / "controlnet_construct" / "usage.md").read_text(encoding="utf-8")
        templates = (PROJECT_ROOT / "examples" / "controlnet_construct" / "recommended_batch_templates.md").read_text(encoding="utf-8")
        matcher_example = json.loads(
            (PROJECT_ROOT / "examples" / "controlnet_construct" / "experiments" / "matcher_comparison.example.json").read_text(
                encoding="utf-8"
            )
        )
        combined_docs = usage + "\n" + templates

        self.assertIn("lightglue_official_superpoint.json", combined_docs)
        self.assertIn("loftr_external_outdoor.json", combined_docs)
        self.assertIn("loftr_default.json` is the Kornia compatibility preset", combined_docs)
        for legacy in (
            "lightglue_default.json",
            "lightglue_high_recall.json",
            "lightglue_disk.json",
            "lightglue_aliked.json",
            "lightglue_doghardnet.json",
            "superglue_default.json",
            "superglue_aliked.json",
        ):
            self.assertNotIn(f"presets/{legacy}", combined_docs)

        method_presets = {
            method.get("deep_match_config_path")
            for method in matcher_example.get("methods", [])
            if method.get("deep_match_config_path")
        }
        self.assertIn("examples/controlnet_construct/presets/lightglue_official_superpoint.json", method_presets)
        self.assertIn("examples/controlnet_construct/presets/loftr_external_outdoor.json", method_presets)
        self.assertNotIn("examples/controlnet_construct/presets/superglue_aliked.json", method_presets)
        self.assertNotIn("examples/controlnet_construct/presets/lightglue_disk.json", method_presets)
```

- [ ] **Step 2: Run doc guard test and verify failure**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_recommended_docs_use_official_lightglue_and_external_loftr_presets -v
```

Expected: test fails because docs/examples still contain old preset recommendations.

- [ ] **Step 3: Update raw wrapper section in `usage.md`**

In `examples/controlnet_construct/usage.md`, replace the sentence:

```text
第一版不接入 deep matcher、adaptive routing、DOM low-resolution offset 或 DOM-space RANSAC 可视化。需要这些能力时继续使用 DOM pipeline，或者后续再按小步方式扩展这个 wrapper。
```

with:

```text
当前 raw/original image wrapper 支持直接启用 adaptive routing。该路径不会依赖 DOM low-resolution preview 或 DOM-to-original 回投；纹理与光照诊断来自原始 cube 自身。默认仍使用 classic `flann`，只有显式传入 `--adaptive-routing` 或在 `ImageMatch.enable_adaptive_routing` 中启用时才进入自适应路由。

推荐的深度学习 preset 面收敛为 official LightGlue 与 external official LoFTR：

- `examples/controlnet_construct/presets/lightglue_official_superpoint.json`
- `examples/controlnet_construct/presets/loftr_external_outdoor.json`
- `examples/controlnet_construct/presets/loftr_external_indoor.json`

`loftr_default.json` is the Kornia compatibility preset, not the official LoFTR repository/checkpoint route. 旧的非 official LightGlue preset 与 `superglue_*` preset 不再作为推荐控制网构建路径；清理前仅作为兼容历史实验引用。
```

Add this example command after the raw wrapper invocation:

```bash
bash examples/controlnet_construct/run_ori_match_pipeline_example.sh \
  --work-dir work_ori \
  --original-list work/original_images.lis \
  --config examples/controlnet_construct/controlnet_config.example.json \
  --matcher-method flann \
  --adaptive-routing \
  --adaptive-routing-profile balanced \
  --adaptive-routing-deep-preset lightglue=examples/controlnet_construct/presets/lightglue_official_superpoint.json \
  --adaptive-routing-deep-preset loftr=examples/controlnet_construct/presets/loftr_external_outdoor.json
```

- [ ] **Step 4: Update recommended templates**

In `examples/controlnet_construct/recommended_batch_templates.md`, replace recommended `lightglue_default.json`, `lightglue_disk.json`, and `superglue_*` preset references with:

```text
examples/controlnet_construct/presets/lightglue_official_superpoint.json
examples/controlnet_construct/presets/loftr_external_outdoor.json
```

When a paragraph mentions `loftr_default.json`, add the exact sentence:

```text
`loftr_default.json` is the Kornia compatibility preset; use `loftr_external_outdoor.json` or `loftr_external_indoor.json` for the official LoFTR repository/checkpoint route.
```

- [ ] **Step 5: Update matcher comparison example**

In `examples/controlnet_construct/experiments/matcher_comparison.example.json`, keep classic methods and official learned methods only. The `methods` list should include entries shaped like:

```json
{
  "label": "sift_flann",
  "matcher_method": "flann"
},
{
  "label": "official_lightglue_superpoint",
  "matcher_method": "lightglue",
  "deep_match_config_path": "examples/controlnet_construct/presets/lightglue_official_superpoint.json"
},
{
  "label": "official_loftr_external_outdoor",
  "matcher_method": "loftr",
  "deep_match_config_path": "examples/controlnet_construct/presets/loftr_external_outdoor.json"
}
```

Remove `superglue_*` and non-official `lightglue_*` method entries from this recommended example.

- [ ] **Step 6: Run doc guard test**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_recommended_docs_use_official_lightglue_and_external_loftr_presets -v
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add examples/controlnet_construct/usage.md examples/controlnet_construct/recommended_batch_templates.md examples/controlnet_construct/experiments/matcher_comparison.example.json tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "docs: recommend official deep matcher presets"
```

---

### Task 5: Final Verification

**Files:**
- No source edits unless verification exposes a defect.

- [ ] **Step 1: Run smoke import**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tests/smoke_import.py
```

Expected: smoke import succeeds.

- [ ] **Step 2: Run adaptive and raw focused tests**

Run:

```bash
python -m unittest tests.unitTest.image_match_texture_sparseness_unit_test -v
python -m unittest tests.unitTest.image_match_lighting_difference_unit_test -v
python -m unittest tests.unitTest.image_match_adaptive_routing_unit_test -v
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -k adaptive -v
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -k ori -v
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -k adaptive -v
```

Expected: all selected tests pass.

- [ ] **Step 3: Verify no recommended docs point to deprecated presets**

Run:

```bash
rg -n "presets/(lightglue_default|lightglue_high_recall|lightglue_disk|lightglue_aliked|lightglue_doghardnet|superglue_default|superglue_aliked)\\.json" \
  examples/controlnet_construct/usage.md \
  examples/controlnet_construct/recommended_batch_templates.md \
  examples/controlnet_construct/experiments/matcher_comparison.example.json
```

Expected: no matches.

- [ ] **Step 4: Check worktree status**

Run:

```bash
git status --short --branch
```

Expected: clean branch after all task commits.

- [ ] **Step 5: Commit fixes only if verification required changes**

If Step 1-3 exposed a small fix, commit it:

```bash
git add <changed-files>
git commit -m "test: verify raw adaptive official deep path"
```

If no files changed, do not create an empty commit.

---

## Self-Review Notes

- Spec coverage: raw adaptive diagnostics, official LightGlue/external LoFTR routing, wrapper CLI/config, staged cleanup, error handling, and tests are covered.
- Scope boundary: this plan does not delete presets or runtime code; it only deprecates recommendations and enables the raw adaptive direct path.
- Type consistency: new parser fields are `enable_adaptive_routing`, `adaptive_routing_profile`, `deep_match_config_path`, and `adaptive_routing_deep_preset`; forwarded matcher kwargs use the existing `match_ori_pair_to_key_files` / `match_dom_pair` names.
- Verification emphasis: focused tests avoid requiring GPU, external LightGlue, or external LoFTR downloads in the normal unit-test path.
