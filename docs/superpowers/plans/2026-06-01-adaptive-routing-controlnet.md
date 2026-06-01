# Adaptive Routing ControlNet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build opt-in ORI and DOM ControlNet construction flows that select matching methods through existing adaptive routing and persist route audit metadata.

**Architecture:** Keep adaptive routing logic in `examples/image_match/`; `examples/controlnet_construct/controlnet_stereopair.py` becomes a thin orchestration layer that calls existing match APIs, converts key files, writes ControlNets, and reports route summaries. Add explicit DOM end-to-end entry points while preserving existing precomputed DOM key workflows.

**Tech Stack:** Python `argparse`, existing `examples/image_match.image_match` APIs, ISIS `isis_pybind`, JSON sidecar summaries, `unittest`, focused mocks for fast controlnet pipeline tests.

---

## File Structure

- Modify `examples/controlnet_construct/controlnet_stereopair.py`
  - Import `match_dom_pair_to_key_files` next to `match_ori_pair_to_key_files`.
  - Add route audit helpers that extract stable audit fields from image-match summaries.
  - Refactor `from-ori-match` dispatch to unpack match return values and include JSON-safe routing metadata.
  - Add `build_controlnet_for_dom_match_stereo_pair()` for DOM image matching followed by existing DOM key conversion and ControlNet writing.
  - Add `from-dom-match` CLI parser and dispatch branch.
  - Add `build_controlnets_for_dom_match_overlap_list()` so batch callers can aggregate end-to-end DOM match route summaries.
- Modify `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
  - Add focused unit tests for ORI route audit metadata.
  - Add focused unit tests for DOM end-to-end helper behavior and failure boundaries.
  - Add parser/dispatch tests for `from-dom-match`.
  - Add batch summary tests for route audit aggregation.
  - Update module metadata `Last Modified` and append one short `Updated:` line.
- Modify `examples/controlnet_construct/usage.md`
  - Document `from-dom-match`, adaptive routing flags, and the distinction from legacy `from-dom` precomputed-key mode.

---

### Task 1: Add ORI route audit tests

**Files:**
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Update test metadata**

Change the module metadata near the top of `tests/unitTest/controlnet_construct_pipeline_unit_test.py`:

```python
Last Modified: 2026-06-01
Updated: 2026-06-01  Geng Xun added adaptive-routing ControlNet orchestration coverage for ORI and DOM matching flows.
```

- [ ] **Step 2: Add failing ORI JSON-safe match summary test**

Add this test method inside `ControlNetConstructPipelineUnitTest` near the existing `from-ori-match` tests:

```python
    def test_controlnet_from_ori_match_writes_json_safe_route_audit(self):
        fake_match_summary = {
            "status": "matched",
            "point_count": 7,
            "matcher": {
                "matcher_method_requested": "flann",
                "matcher_method_effective": "lightglue",
                "ratio_test": 0.75,
            },
            "adaptive_routing_profile": "balanced",
            "adaptive_routing": {
                "status": "routed",
                "selected_initial_matcher": "lightglue",
                "selected_final_matcher": "flann",
                "fallback_chain": ["lightglue", "flann", "bf"],
                "cascade_steps": [
                    {"matcher": "lightglue", "status": "failed_quality_gate"},
                    {"matcher": "flann", "status": "accepted"},
                ],
                "match_quality": {"accepted": True, "inlier_count": 7},
                "final_decision": "accepted",
            },
            "deep_match_config_path": "presets/lightglue_official_superpoint.json",
        }
        fake_controlnet = {
            "output_path": "pair.net",
            "point_count": 7,
            "measure_count": 14,
        }
        stdout = io.StringIO()

        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            report_path = temp_dir / "pair.summary.json"
            output_net = temp_dir / "pair.net"
            config_path.write_text(
                json.dumps({"NetworkId": "route_unit", "TargetName": "Mars", "UserName": "unit"}) + "\n",
                encoding="utf-8",
            )

            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.match_ori_pair_to_key_files",
                    return_value=("left-key-object", "right-key-object", fake_match_summary),
                ),
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnet_for_stereo_pair",
                    return_value=fake_controlnet,
                ),
                patch.object(sys, "stdout", stdout),
            ):
                controlnet_stereopair_main(
                    [
                        "from-ori-match",
                        "left.cub",
                        "right.cub",
                        str(config_path),
                        str(output_net),
                        "--report-path",
                        str(report_path),
                        "--adaptive-routing",
                    ]
                )

            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(report["mode"], "from-ori-match")
        self.assertEqual(report["match"]["point_count"], 7)
        self.assertEqual(report["routing_audit"]["requested_matcher"], "flann")
        self.assertEqual(report["routing_audit"]["effective_matcher"], "lightglue")
        self.assertEqual(report["routing_audit"]["adaptive_routing_profile"], "balanced")
        self.assertEqual(report["routing_audit"]["selected_initial_matcher"], "lightglue")
        self.assertEqual(report["routing_audit"]["selected_final_matcher"], "flann")
        self.assertEqual(report["routing_audit"]["match_count"], 7)
        json.dumps(json.loads(stdout.getvalue()))
```

- [ ] **Step 3: Run the new ORI test and verify it fails**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_controlnet_from_ori_match_writes_json_safe_route_audit -v
```

Expected: FAIL because `from-ori-match` currently stores the raw tuple return under `match` and does not expose `routing_audit`.

- [ ] **Step 4: Commit the failing test**

```bash
git add tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "test: cover ORI adaptive route audit summary" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 2: Implement ORI route audit extraction

**Files:**
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Add route audit helpers**

Insert these helpers after `_parse_adaptive_routing_deep_preset_entries()`:

```python
def _safe_mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _route_audit_from_match_summary(match_summary: dict[str, object]) -> dict[str, object]:
    matcher = _safe_mapping(match_summary.get("matcher"))
    adaptive = _safe_mapping(match_summary.get("adaptive_routing"))
    requested_matcher = matcher.get("matcher_method_requested") or matcher.get("requested_matcher")
    effective_matcher = matcher.get("matcher_method_effective") or matcher.get("effective_matcher")
    selected_initial = adaptive.get("selected_initial_matcher") or adaptive.get("initial_matcher")
    selected_final = adaptive.get("selected_final_matcher") or adaptive.get("final_matcher") or effective_matcher
    return {
        "requested_matcher": requested_matcher,
        "effective_matcher": effective_matcher,
        "adaptive_routing_profile": match_summary.get("adaptive_routing_profile"),
        "adaptive_routing_status": adaptive.get("status"),
        "selected_initial_matcher": selected_initial,
        "selected_final_matcher": selected_final,
        "fallback_chain": adaptive.get("fallback_chain"),
        "cascade_steps": adaptive.get("cascade_steps"),
        "quality_gate": adaptive.get("match_quality") or adaptive.get("quality_gate"),
        "final_decision": adaptive.get("final_decision"),
        "deep_match_config_path": match_summary.get("deep_match_config_path"),
        "match_count": match_summary.get("point_count"),
    }
```

- [ ] **Step 2: Make `from-ori-match` store the match summary, not raw key objects**

In `main()`, replace the `match_result = match_ori_pair_to_key_files(...)` assignment with tuple unpacking:

```python
        _, _, match_summary = match_ori_pair_to_key_files(
            args.left_cube,
            args.right_cube,
            left_output_key,
            right_output_key,
            matcher_method=args.matcher_method,
            band=args.band,
            ratio_test=args.ratio_test,
            max_features=args.max_features,
            show_progress=args.show_progress,
            use_gpu=args.use_gpu,
            gpu_batch_size=args.gpu_batch_size,
            gpu_dynamic_batch=args.gpu_dynamic_batch,
            gpu_min_batch_size=args.gpu_min_batch_size,
            gpu_max_batch_size=args.gpu_max_batch_size,
            num_worker_parallel_cpu=args.num_worker_parallel_cpu,
            use_parallel_cpu=args.use_parallel_cpu,
            enable_adaptive_routing=args.enable_adaptive_routing,
            adaptive_routing_profile=args.adaptive_routing_profile,
            adaptive_routing_deep_presets=adaptive_routing_deep_presets,
            deep_match_config_path=args.deep_match_config_path,
            deep_match_mode="direct",
        )
```

Then replace the `result` payload in that branch with:

```python
        result = {
            "mode": "from-ori-match",
            "match": match_summary,
            "routing_audit": _route_audit_from_match_summary(match_summary),
            "left_output_key": str(left_output_key),
            "right_output_key": str(right_output_key),
            "controlnet": controlnet_result,
        }
```

- [ ] **Step 3: Run the ORI test and verify it passes**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_controlnet_from_ori_match_writes_json_safe_route_audit -v
```

Expected: PASS.

- [ ] **Step 4: Run existing ORI adaptive wrapper coverage**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_ori_match_pipeline_forwards_official_deep_and_adaptive_flags tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_ori_match_pipeline_forwards_adaptive_and_official_deep_presets -v
```

Expected: PASS.

- [ ] **Step 5: Commit ORI route audit implementation**

```bash
git add examples/controlnet_construct/controlnet_stereopair.py tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: report ORI adaptive route audit metadata" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 3: Add DOM end-to-end helper tests

**Files:**
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Add import expectation for the new helper**

Extend the existing import from `controlnet_construct.controlnet_stereopair`:

```python
from controlnet_construct.controlnet_stereopair import (
    ControlNetConfig,
    build_argument_parser as build_controlnet_stereopair_parser,
    build_controlnet_for_dom_match_stereo_pair,
    build_controlnets_for_dom_overlap_list,
    build_controlnet_for_dom_stereo_pair,
    build_controlnet_for_stereo_pair,
    default_controlnet_report_path,
    main as controlnet_stereopair_main,
    read_controlnet_config,
    write_controlnet_result_report,
)
```

- [ ] **Step 2: Add failing DOM helper success test**

Add this test near the existing `build_controlnet_for_dom_stereo_pair` tests:

```python
    def test_build_controlnet_for_dom_match_stereo_pair_matches_then_converts(self):
        config = ControlNetConfig(
            network_id="dom_match_unit",
            target_name="Mars",
            user_name="unit",
            description="",
            point_id_prefix="P",
            pair_id=None,
        )
        fake_match_summary = {
            "status": "matched",
            "point_count": 5,
            "matcher": {
                "matcher_method_requested": "flann",
                "matcher_method_effective": "loftr",
            },
            "adaptive_routing_profile": "strict",
            "adaptive_routing": {
                "status": "routed",
                "selected_initial_matcher": "loftr",
                "selected_final_matcher": "loftr",
                "final_decision": "accepted",
            },
            "deep_match_config_path": "presets/loftr_external_outdoor.json",
        }
        fake_controlnet = {
            "mode": "from-dom",
            "controlnet": {"output_path": "pair.net", "point_count": 5},
        }

        with temporary_directory() as temp_dir:
            output_net = temp_dir / "pair.net"
            left_dom_key = temp_dir / "pair_left_dom_match.key"
            right_dom_key = temp_dir / "pair_right_dom_match.key"
            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.match_dom_pair_to_key_files",
                    return_value=fake_match_summary,
                ) as match_mock,
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnet_for_dom_stereo_pair",
                    return_value=fake_controlnet,
                ) as build_mock,
            ):
                result = build_controlnet_for_dom_match_stereo_pair(
                    "left_dom.cub",
                    "right_dom.cub",
                    "left_original.cub",
                    "right_original.cub",
                    config,
                    output_net,
                    left_dom_match_key_path=left_dom_key,
                    right_dom_match_key_path=right_dom_key,
                    matcher_method="flann",
                    enable_adaptive_routing=True,
                    adaptive_routing_profile="strict",
                    adaptive_routing_deep_presets={"loftr": "presets/loftr_external_outdoor.json"},
                    deep_match_config_path="presets/loftr_external_outdoor.json",
                    write_match_visualization=False,
                )

        self.assertEqual(result["mode"], "from-dom-match")
        self.assertEqual(result["match"], fake_match_summary)
        self.assertEqual(result["routing_audit"]["selected_final_matcher"], "loftr")
        self.assertEqual(result["routing_audit"]["match_count"], 5)
        self.assertEqual(match_mock.call_args.args[:4], ("left_dom.cub", "right_dom.cub", left_dom_key, right_dom_key))
        self.assertTrue(match_mock.call_args.kwargs["enable_adaptive_routing"])
        self.assertEqual(match_mock.call_args.kwargs["adaptive_routing_profile"], "strict")
        self.assertEqual(build_mock.call_args.args[:6], (left_dom_key, right_dom_key, "left_dom.cub", "right_dom.cub", "left_original.cub", "right_original.cub"))
```

- [ ] **Step 3: Add failing DOM failure-boundary test**

Add this test after the success test:

```python
    def test_build_controlnet_for_dom_match_stereo_pair_does_not_convert_after_match_failure(self):
        config = ControlNetConfig(
            network_id="dom_match_failure_unit",
            target_name="Mars",
            user_name="unit",
            description="",
            point_id_prefix="P",
            pair_id=None,
        )

        with temporary_directory() as temp_dir:
            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.match_dom_pair_to_key_files",
                    side_effect=RuntimeError("all routed matchers failed"),
                ),
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnet_for_dom_stereo_pair",
                ) as build_mock,
            ):
                with self.assertRaisesRegex(RuntimeError, "all routed matchers failed"):
                    build_controlnet_for_dom_match_stereo_pair(
                        "left_dom.cub",
                        "right_dom.cub",
                        "left_original.cub",
                        "right_original.cub",
                        config,
                        temp_dir / "pair.net",
                        enable_adaptive_routing=True,
                    )

        build_mock.assert_not_called()
```

- [ ] **Step 4: Run DOM helper tests and verify they fail**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_build_controlnet_for_dom_match_stereo_pair_matches_then_converts tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_build_controlnet_for_dom_match_stereo_pair_does_not_convert_after_match_failure -v
```

Expected: FAIL because `build_controlnet_for_dom_match_stereo_pair` does not exist.

- [ ] **Step 5: Commit failing DOM helper tests**

```bash
git add tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "test: cover DOM match ControlNet orchestration" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 4: Implement DOM end-to-end helper

**Files:**
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Import the DOM match API**

Change both import branches in `examples/controlnet_construct/controlnet_stereopair.py` from:

```python
    from image_match.image_match import match_ori_pair_to_key_files
```

to:

```python
    from image_match.image_match import match_dom_pair_to_key_files, match_ori_pair_to_key_files
```

- [ ] **Step 2: Add the DOM match orchestration helper**

Insert this function after `build_controlnet_for_dom_stereo_pair()`:

```python
def build_controlnet_for_dom_match_stereo_pair(
    left_dom_cube_path: str | Path,
    right_dom_cube_path: str | Path,
    left_cube_path: str | Path,
    right_cube_path: str | Path,
    config: ControlNetConfig,
    output_path: str | Path,
    *,
    left_dom_match_key_path: str | Path | None = None,
    right_dom_match_key_path: str | Path | None = None,
    matcher_method: str = "sift",
    band: int = 1,
    ratio_test: float = 0.75,
    max_features: int | None = None,
    show_progress: bool = False,
    use_gpu: bool = False,
    gpu_batch_size: int = 4,
    gpu_dynamic_batch: bool = True,
    gpu_min_batch_size: int = 2,
    gpu_max_batch_size: int = 16,
    num_worker_parallel_cpu: int = 8,
    use_parallel_cpu: bool = True,
    enable_adaptive_routing: bool = False,
    adaptive_routing_profile: str = "balanced",
    adaptive_routing_deep_presets: dict[str, str] | None = None,
    deep_match_config_path: str | Path | None = None,
    deep_match_mode: str = "direct",
    write_match_visualization: bool = True,
    match_visualization_output_path: str | Path | None = None,
    match_visualization_output_dir: str | Path | None = None,
    match_visualization_scale: float = 1.0 / 3.0,
    left_merged_dom_key_path: str | Path | None = None,
    right_merged_dom_key_path: str | Path | None = None,
    left_ransac_dom_key_path: str | Path | None = None,
    right_ransac_dom_key_path: str | Path | None = None,
    left_output_key_path: str | Path | None = None,
    right_output_key_path: str | Path | None = None,
    merge_decimals: int = 3,
    skip_merge: bool = False,
    ransac_reproj_threshold: float = 3.0,
    ransac_confidence: float = 0.995,
    ransac_max_iters: int = 5000,
    ransac_mode: str = "loose",
    loose_ransac_keep_threshold: float = 1.0,
    pvl_format: bool = True,
    logger: logging.Logger | None = None,
) -> dict[str, object]:
    left_dom_match_key = (
        Path(left_dom_match_key_path)
        if left_dom_match_key_path is not None
        else _default_intermediate_key_path(output_path, "left", "dom_match")
    )
    right_dom_match_key = (
        Path(right_dom_match_key_path)
        if right_dom_match_key_path is not None
        else _default_intermediate_key_path(output_path, "right", "dom_match")
    )
    match_summary = match_dom_pair_to_key_files(
        left_dom_cube_path,
        right_dom_cube_path,
        left_dom_match_key,
        right_dom_match_key,
        write_match_visualization=write_match_visualization,
        match_visualization_output_path=match_visualization_output_path,
        match_visualization_output_dir=match_visualization_output_dir,
        match_visualization_scale=match_visualization_scale,
        show_progress=show_progress,
        matcher_method=matcher_method,
        band=band,
        ratio_test=ratio_test,
        max_features=max_features,
        use_gpu=use_gpu,
        gpu_batch_size=gpu_batch_size,
        gpu_dynamic_batch=gpu_dynamic_batch,
        gpu_min_batch_size=gpu_min_batch_size,
        gpu_max_batch_size=gpu_max_batch_size,
        num_worker_parallel_cpu=num_worker_parallel_cpu,
        use_parallel_cpu=use_parallel_cpu,
        enable_adaptive_routing=enable_adaptive_routing,
        adaptive_routing_profile=adaptive_routing_profile,
        adaptive_routing_deep_presets=adaptive_routing_deep_presets or {},
        deep_match_config_path=deep_match_config_path,
        deep_match_mode=deep_match_mode,
    )
    controlnet_result = build_controlnet_for_dom_stereo_pair(
        left_dom_match_key,
        right_dom_match_key,
        left_dom_cube_path,
        right_dom_cube_path,
        left_cube_path,
        right_cube_path,
        config,
        output_path,
        left_merged_dom_key_path=left_merged_dom_key_path,
        right_merged_dom_key_path=right_merged_dom_key_path,
        left_ransac_dom_key_path=left_ransac_dom_key_path,
        right_ransac_dom_key_path=right_ransac_dom_key_path,
        left_output_key_path=left_output_key_path,
        right_output_key_path=right_output_key_path,
        merge_decimals=merge_decimals,
        skip_merge=skip_merge,
        ransac_reproj_threshold=ransac_reproj_threshold,
        ransac_confidence=ransac_confidence,
        ransac_max_iters=ransac_max_iters,
        ransac_mode=ransac_mode,
        loose_ransac_keep_threshold=loose_ransac_keep_threshold,
        write_match_visualization=False,
        pvl_format=pvl_format,
        logger=logger,
    )
    return {
        "mode": "from-dom-match",
        "match": match_summary,
        "routing_audit": _route_audit_from_match_summary(match_summary),
        "left_dom_match_key": str(left_dom_match_key),
        "right_dom_match_key": str(right_dom_match_key),
        "controlnet": controlnet_result,
    }
```

- [ ] **Step 3: Run DOM helper tests and verify they pass**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_build_controlnet_for_dom_match_stereo_pair_matches_then_converts tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_build_controlnet_for_dom_match_stereo_pair_does_not_convert_after_match_failure -v
```

Expected: PASS.

- [ ] **Step 4: Commit DOM helper implementation**

```bash
git add examples/controlnet_construct/controlnet_stereopair.py tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: add DOM match ControlNet orchestration" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 5: Add `from-dom-match` CLI

**Files:**
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Add failing parser and dispatch tests**

Add this parser test:

```python
    def test_controlnet_stereopair_parser_accepts_from_dom_match_adaptive_flags(self):
        parser = build_controlnet_stereopair_parser()
        parsed = parser.parse_args(
            [
                "from-dom-match",
                "left_dom.cub",
                "right_dom.cub",
                "left.cub",
                "right.cub",
                "config.json",
                "pair.net",
                "--adaptive-routing",
                "--adaptive-routing-profile",
                "fast",
                "--adaptive-routing-deep-preset",
                "loftr=presets/loftr_external_outdoor.json",
                "--matcher-method",
                "flann",
            ]
        )

        self.assertEqual(parsed.command, "from-dom-match")
        self.assertTrue(parsed.enable_adaptive_routing)
        self.assertEqual(parsed.adaptive_routing_profile, "fast")
        self.assertEqual(parsed.adaptive_routing_deep_preset, ["loftr=presets/loftr_external_outdoor.json"])
        self.assertEqual(parsed.matcher_method, "flann")
```

Add this dispatch test:

```python
    def test_controlnet_stereopair_from_dom_match_dispatches_helper_and_writes_report(self):
        fake_result = {
            "mode": "from-dom-match",
            "routing_audit": {"selected_final_matcher": "loftr", "match_count": 9},
            "match": {"point_count": 9},
            "controlnet": {"controlnet": {"point_count": 9}},
        }
        stdout = io.StringIO()

        with temporary_directory() as temp_dir:
            config_path = temp_dir / "config.json"
            report_path = temp_dir / "pair.summary.json"
            output_net = temp_dir / "pair.net"
            config_path.write_text(
                json.dumps({"NetworkId": "dom_match_cli", "TargetName": "Mars", "UserName": "unit"}) + "\n",
                encoding="utf-8",
            )

            with (
                patch(
                    "controlnet_construct.controlnet_stereopair.build_controlnet_for_dom_match_stereo_pair",
                    return_value=fake_result,
                ) as build_mock,
                patch.object(sys, "stdout", stdout),
            ):
                controlnet_stereopair_main(
                    [
                        "from-dom-match",
                        "left_dom.cub",
                        "right_dom.cub",
                        "left.cub",
                        "right.cub",
                        str(config_path),
                        str(output_net),
                        "--report-path",
                        str(report_path),
                        "--adaptive-routing",
                        "--adaptive-routing-profile",
                        "fast",
                        "--adaptive-routing-deep-preset",
                        "loftr=presets/loftr_external_outdoor.json",
                    ]
                )

            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(report["mode"], "from-dom-match")
        self.assertEqual(report["routing_audit"]["selected_final_matcher"], "loftr")
        self.assertEqual(build_mock.call_args.args[:6], ("left_dom.cub", "right_dom.cub", "left.cub", "right.cub", read_controlnet_config(config_path), output_net))
        self.assertTrue(build_mock.call_args.kwargs["enable_adaptive_routing"])
        self.assertEqual(build_mock.call_args.kwargs["adaptive_routing_profile"], "fast")
        self.assertEqual(
            build_mock.call_args.kwargs["adaptive_routing_deep_presets"],
            {"loftr": "presets/loftr_external_outdoor.json"},
        )
        json.dumps(json.loads(stdout.getvalue()))
```

- [ ] **Step 2: Run the CLI tests and verify they fail**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_controlnet_stereopair_parser_accepts_from_dom_match_adaptive_flags tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_controlnet_stereopair_from_dom_match_dispatches_helper_and_writes_report -v
```

Expected: FAIL because the parser does not know `from-dom-match`.

- [ ] **Step 3: Implement the parser**

Add `"from-dom-match"` to `_normalize_cli_argv()`:

```python
    if argv and argv[0] not in {"from-ori", "from-ori-match", "from-dom", "from-dom-match", "from-dom-batch", "-h", "--help"}:
```

Add this function after `_build_from_dom_parser()`:

```python
def _build_from_dom_match_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "from-dom-match",
        help="Match DOM cubes, convert matched DOM keys to original-image coordinates, and build a ControlNet.",
    )
    parser.add_argument("left_dom_cube", help="DOM cube path for image A.")
    parser.add_argument("right_dom_cube", help="DOM cube path for image B.")
    parser.add_argument("left_cube", help="Original cube path for image A.")
    parser.add_argument("right_cube", help="Original cube path for image B.")
    parser.add_argument("config", help="JSON config file containing NetworkId, TargetName, and UserName.")
    parser.add_argument("output_net", help="Output ControlNet path.")
    parser.add_argument("--report-path", default=None, help="Optional JSON path used to persist the per-pair result summary.")
    parser.add_argument("--pair-id", default=None, help="Optional stereo-pair ID appended to the point-id namespace.")
    parser.add_argument("--left-dom-match-key", default=None, help="Optional path to persist the matched DOM-space .key for image A.")
    parser.add_argument("--right-dom-match-key", default=None, help="Optional path to persist the matched DOM-space .key for image B.")
    parser.add_argument("--left-output-key", default=None, help="Optional path to persist the converted original-image .key for image A.")
    parser.add_argument("--right-output-key", default=None, help="Optional path to persist the converted original-image .key for image B.")
    parser.add_argument("--matcher-method", default="sift", help="Matcher method forwarded to image_match.")
    parser.add_argument("--band", type=int, default=1, help="Band index used for DOM matching.")
    parser.add_argument("--ratio-test", type=float, default=0.75, help="Ratio test threshold forwarded to image_match.")
    parser.add_argument("--max-features", type=int, default=None, help="Optional SIFT max_features forwarded to image_match.")
    parser.add_argument("--show-progress", action="store_true", help="Show tile matching progress output.")
    parser.add_argument("--use-gpu", action="store_true", help="Enable GPU matching route when supported.")
    parser.add_argument("--gpu-batch-size", type=int, default=4, help="GPU batch size for matching.")
    parser.add_argument("--gpu-dynamic-batch", action="store_true", default=True, help="Enable dynamic GPU batch sizing.")
    parser.add_argument("--no-gpu-dynamic-batch", dest="gpu_dynamic_batch", action="store_false", help="Disable dynamic GPU batch sizing.")
    parser.add_argument("--gpu-min-batch-size", type=int, default=2, help="Minimum dynamic GPU batch size.")
    parser.add_argument("--gpu-max-batch-size", type=int, default=16, help="Maximum dynamic GPU batch size.")
    parser.add_argument("--num-worker-parallel-cpu", type=int, default=8, help="CPU worker count for parallel matching.")
    parser.add_argument("--use-parallel-cpu", action="store_true", default=True, help="Enable parallel CPU matching.")
    parser.add_argument("--no-parallel-cpu", dest="use_parallel_cpu", action="store_false", help="Disable parallel CPU matching.")
    parser.set_defaults(enable_adaptive_routing=False)
    parser.add_argument("--adaptive-routing", dest="enable_adaptive_routing", action="store_true", help="Enable adaptive texture/lighting routing for DOM matching.")
    parser.add_argument("--no-adaptive-routing", dest="enable_adaptive_routing", action="store_false", help="Disable adaptive texture/lighting routing for DOM matching.")
    parser.add_argument("--adaptive-routing-profile", default="balanced", choices=("balanced", "strict", "relaxed", "fast"), help="Adaptive routing quality profile.")
    parser.add_argument("--deep-match-config-path", default=None, help="Optional deep matcher preset JSON path for DOM matching.")
    parser.add_argument("--adaptive-routing-deep-preset", action="append", default=[], help="Adaptive deep preset mapping in KEY=PATH form. Repeat for lightglue and loftr.")
    parser.add_argument("--merge-decimals", type=validate_merge_decimals, default=3, help="Decimal precision used when merging duplicate DOM tie points.")
    parser.add_argument("--skip-merge", action="store_true", help="Skip DOM-space duplicate merge and pass matched DOM keys straight to dom2ori.")
    parser.add_argument("--ransac-reproj-threshold", type=float, default=3.0, help="Reprojection threshold passed to OpenCV homography RANSAC.")
    parser.add_argument("--ransac-confidence", type=float, default=0.995, help="Confidence passed to OpenCV homography RANSAC.")
    parser.add_argument("--ransac-max-iters", type=int, default=5000, help="Maximum iteration count passed to OpenCV homography RANSAC.")
    parser.add_argument("--ransac-mode", choices=("strict", "loose"), default="loose", help="RANSAC outlier handling mode.")
    parser.add_argument("--loose-ransac-keep-threshold", type=float, default=1.0, help="Loose-mode pixel threshold used to keep soft outliers.")
    parser.add_argument("--binary", action="store_true", help="Write the ControlNet in binary format instead of PVL.")
    parser.add_argument("--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR"), help="Logging verbosity for runtime diagnostics.")
    _add_stdout_detail_control_arguments(parser)
```

Call it from `build_argument_parser()`:

```python
    _build_from_dom_match_parser(subparsers)
```

- [ ] **Step 4: Add main dispatch branch**

Insert this branch before `elif args.command == "from-dom"`:

```python
    elif args.command == "from-dom-match":
        config = _apply_cli_pair_id_override(read_controlnet_config(args.config), args.pair_id)
        try:
            adaptive_routing_deep_presets = _parse_adaptive_routing_deep_preset_entries(
                args.adaptive_routing_deep_preset
            )
        except ValueError as exc:
            parser.error(str(exc))
        result = build_controlnet_for_dom_match_stereo_pair(
            args.left_dom_cube,
            args.right_dom_cube,
            args.left_cube,
            args.right_cube,
            config,
            Path(args.output_net),
            left_dom_match_key_path=args.left_dom_match_key,
            right_dom_match_key_path=args.right_dom_match_key,
            left_output_key_path=args.left_output_key,
            right_output_key_path=args.right_output_key,
            matcher_method=args.matcher_method,
            band=args.band,
            ratio_test=args.ratio_test,
            max_features=args.max_features,
            show_progress=args.show_progress,
            use_gpu=args.use_gpu,
            gpu_batch_size=args.gpu_batch_size,
            gpu_dynamic_batch=args.gpu_dynamic_batch,
            gpu_min_batch_size=args.gpu_min_batch_size,
            gpu_max_batch_size=args.gpu_max_batch_size,
            num_worker_parallel_cpu=args.num_worker_parallel_cpu,
            use_parallel_cpu=args.use_parallel_cpu,
            enable_adaptive_routing=args.enable_adaptive_routing,
            adaptive_routing_profile=args.adaptive_routing_profile,
            adaptive_routing_deep_presets=adaptive_routing_deep_presets,
            deep_match_config_path=args.deep_match_config_path,
            merge_decimals=args.merge_decimals,
            skip_merge=args.skip_merge,
            ransac_reproj_threshold=args.ransac_reproj_threshold,
            ransac_confidence=args.ransac_confidence,
            ransac_max_iters=args.ransac_max_iters,
            ransac_mode=args.ransac_mode,
            loose_ransac_keep_threshold=args.loose_ransac_keep_threshold,
            pvl_format=not args.binary,
            logger=logger,
        )
```

- [ ] **Step 5: Run the CLI tests and verify they pass**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_controlnet_stereopair_parser_accepts_from_dom_match_adaptive_flags tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_controlnet_stereopair_from_dom_match_dispatches_helper_and_writes_report -v
```

Expected: PASS.

- [ ] **Step 6: Commit DOM CLI implementation**

```bash
git add examples/controlnet_construct/controlnet_stereopair.py tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: add from-dom-match ControlNet CLI" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 6: Add DOM match batch aggregation

**Files:**
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Add failing batch test**

Add this test near the existing `build_controlnets_for_dom_overlap_list` tests:

```python
    def test_build_controlnets_for_dom_match_overlap_list_aggregates_routing_audit(self):
        config = ControlNetConfig(
            network_id="dom_match_batch",
            target_name="Mars",
            user_name="unit",
            description="",
            point_id_prefix="P",
            pair_id=None,
        )
        fake_pair_result = {
            "mode": "from-dom-match",
            "routing_audit": {"selected_final_matcher": "flann", "match_count": 11},
            "match": {"point_count": 11},
            "controlnet": {"controlnet": {"point_count": 11}},
        }

        with temporary_directory() as temp_dir:
            overlap_list = temp_dir / "images_overlap.lis"
            original_list = temp_dir / "original_images.lis"
            dom_list = temp_dir / "doms.lis"
            output_dir = temp_dir / "pair_nets"
            report_dir = temp_dir / "reports"
            left = temp_dir / "left.cub"
            right = temp_dir / "right.cub"
            left_dom = temp_dir / "left_dom.cub"
            right_dom = temp_dir / "right_dom.cub"
            overlap_list.write_text(f"{left},{right}\n", encoding="utf-8")
            original_list.write_text(f"{left}\n{right}\n", encoding="utf-8")
            dom_list.write_text(f"{left_dom}\n{right_dom}\n", encoding="utf-8")

            with patch(
                "controlnet_construct.controlnet_stereopair.build_controlnet_for_dom_match_stereo_pair",
                return_value=fake_pair_result,
            ) as build_mock:
                result = build_controlnets_for_dom_match_overlap_list(
                    overlap_list,
                    original_list,
                    dom_list,
                    output_dir,
                    config,
                    report_directory=report_dir,
                    enable_adaptive_routing=True,
                    adaptive_routing_profile="balanced",
                )

        self.assertEqual(result["mode"], "from-dom-match-batch")
        self.assertEqual(result["pair_count"], 1)
        self.assertEqual(result["pairs"][0]["routing_audit"]["selected_final_matcher"], "flann")
        self.assertEqual(result["pairs"][0]["match_count"], 11)
        self.assertTrue(Path(result["batch_report_path"]).exists())
        self.assertEqual(build_mock.call_args.args[0], str(left_dom))
        self.assertEqual(build_mock.call_args.args[1], str(right_dom))
        self.assertTrue(build_mock.call_args.kwargs["enable_adaptive_routing"])
        self.assertEqual(build_mock.call_args.kwargs["adaptive_routing_profile"], "balanced")
```

- [ ] **Step 2: Run the batch test and verify it fails**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_build_controlnets_for_dom_match_overlap_list_aggregates_routing_audit -v
```

Expected: FAIL because `build_controlnets_for_dom_match_overlap_list` does not exist.

- [ ] **Step 3: Implement the batch helper**

Add this helper after `build_controlnets_for_dom_overlap_list()`:

```python
def build_controlnets_for_dom_match_overlap_list(
    overlap_list_path: str | Path,
    original_list_path: str | Path,
    dom_list_path: str | Path,
    output_directory: str | Path,
    config: ControlNetConfig,
    *,
    report_directory: str | Path | None = None,
    pair_id_prefix: str = "S",
    pair_id_start: int = 1,
    pair_net_suffix: str = ".net",
    matcher_method: str = "sift",
    band: int = 1,
    ratio_test: float = 0.75,
    max_features: int | None = None,
    enable_adaptive_routing: bool = False,
    adaptive_routing_profile: str = "balanced",
    adaptive_routing_deep_presets: dict[str, str] | None = None,
    deep_match_config_path: str | Path | None = None,
    pvl_format: bool = True,
    logger: logging.Logger | None = None,
) -> dict[str, object]:
    overlap_pairs = read_stereo_pair_list(overlap_list_path)
    if not overlap_pairs:
        raise ValueError("The overlap pair list is empty.")
    dom_lookup = _build_dom_lookup(original_list_path, dom_list_path)
    net_output_dir = Path(output_directory)
    report_dir = Path(report_directory) if report_directory is not None else net_output_dir
    dom_key_dir = net_output_dir / "dom_match_keys"
    net_output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    dom_key_dir.mkdir(parents=True, exist_ok=True)

    pair_results: list[dict[str, object]] = []
    pair_report_paths: list[str] = []
    batch_pairs: list[dict[str, object]] = []
    for index, pair in enumerate(overlap_pairs, start=1):
        if pair.left not in dom_lookup or pair.right not in dom_lookup:
            raise KeyError(
                f"Unable to resolve DOM paths for stereo pair {pair.as_csv_line()} from the provided original/dom lists."
            )
        pair_id = _auto_batch_pair_id(index, prefix=pair_id_prefix, start=pair_id_start)
        pair_tag = _pair_tag(pair)
        pair_output_net = net_output_dir / pair_controlnet_filename(pair, suffix=pair_net_suffix)
        pair_report_path = report_dir / default_controlnet_report_path(pair_output_net).name
        left_dom_match_key = dom_key_dir / f"{pair_tag}_A.key"
        right_dom_match_key = dom_key_dir / f"{pair_tag}_B.key"
        pair_config = replace(config, pair_id=pair_id)
        pair_result = build_controlnet_for_dom_match_stereo_pair(
            dom_lookup[pair.left],
            dom_lookup[pair.right],
            pair.left,
            pair.right,
            pair_config,
            pair_output_net,
            left_dom_match_key_path=left_dom_match_key,
            right_dom_match_key_path=right_dom_match_key,
            matcher_method=matcher_method,
            band=band,
            ratio_test=ratio_test,
            max_features=max_features,
            enable_adaptive_routing=enable_adaptive_routing,
            adaptive_routing_profile=adaptive_routing_profile,
            adaptive_routing_deep_presets=adaptive_routing_deep_presets or {},
            deep_match_config_path=deep_match_config_path,
            pvl_format=pvl_format,
            logger=logger,
        )
        pair_result = {"pair": pair.as_csv_line(), "pair_id": pair_id, **pair_result}
        report_path = write_controlnet_result_report(pair_result, pair_output_net, report_path=pair_report_path)
        pair_result = {**pair_result, "report_path": report_path}
        pair_results.append(pair_result)
        pair_report_paths.append(report_path)
        routing_audit = _safe_mapping(pair_result.get("routing_audit"))
        controlnet_payload = _safe_mapping(pair_result.get("controlnet"))
        nested_controlnet = _safe_mapping(controlnet_payload.get("controlnet"))
        batch_pairs.append(
            {
                "pair": pair.as_csv_line(),
                "pair_id": pair_id,
                "output_net": str(pair_output_net),
                "report_path": report_path,
                "routing_audit": routing_audit,
                "match_count": routing_audit.get("match_count"),
                "control_point_count": nested_controlnet.get("point_count"),
            }
        )

    batch_report_path = report_dir / DEFAULT_BATCH_REPORT_NAME
    batch_summary = write_batch_summary_report(pair_results, batch_report_path, source_reports=pair_report_paths)
    return {
        "mode": "from-dom-match-batch",
        "overlap_list_path": str(overlap_list_path),
        "pair_count": len(overlap_pairs),
        "pair_id_prefix": pair_id_prefix,
        "pair_id_start": pair_id_start,
        "output_directory": str(net_output_dir),
        "report_directory": str(report_dir),
        "batch_report_path": str(batch_report_path),
        "pairs": batch_pairs,
        "batch_summary": batch_summary,
    }
```

- [ ] **Step 4: Run the batch test and verify it passes**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_build_controlnets_for_dom_match_overlap_list_aggregates_routing_audit -v
```

Expected: PASS.

- [ ] **Step 5: Commit batch helper implementation**

```bash
git add examples/controlnet_construct/controlnet_stereopair.py tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: aggregate DOM match routing summaries" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 7: Document and validate

**Files:**
- Modify: `examples/controlnet_construct/usage.md`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Add docs coverage test**

Add this test near the documentation coverage tests:

```python
    def test_usage_documents_from_dom_match_adaptive_routing(self):
        usage = (PROJECT_ROOT / "examples" / "controlnet_construct" / "usage.md").read_text(encoding="utf-8")

        self.assertIn("from-dom-match", usage)
        self.assertIn("--adaptive-routing", usage)
        self.assertIn("--adaptive-routing-profile", usage)
        self.assertIn("from-dom", usage)
        self.assertIn("precomputed", usage)
```

- [ ] **Step 2: Run docs test and verify it fails**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_usage_documents_from_dom_match_adaptive_routing -v
```

Expected: FAIL until the usage guide mentions the new DOM match mode.

- [ ] **Step 3: Update usage guide**

Add this section near the existing raw/original adaptive routing section in `examples/controlnet_construct/usage.md`:

```markdown
### DOM end-to-end adaptive routing in ControlNet construction

Use `controlnet_stereopair.py from-dom-match` when you want the ControlNet command to run DOM matching itself, write DOM `.key` files, convert those matched DOM points back to original-image coordinates, and then write the pairwise ControlNet.

```bash
python examples/controlnet_construct/controlnet_stereopair.py from-dom-match \
  left_dom.cub \
  right_dom.cub \
  left_original.cub \
  right_original.cub \
  examples/controlnet_construct/controlnet_config.example.json \
  pair.net \
  --matcher-method flann \
  --adaptive-routing \
  --adaptive-routing-profile balanced \
  --adaptive-routing-deep-preset lightglue=examples/controlnet_construct/presets/lightglue_official_superpoint.json \
  --adaptive-routing-deep-preset loftr=examples/controlnet_construct/presets/loftr_external_outdoor.json \
  --report-path pair.summary.json
```

`from-dom` and `from-dom-batch` remain the precomputed DOM-key workflows. Use those commands when another stage has already produced `A__B_A.key` and `A__B_B.key` files.
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_controlnet_from_ori_match_writes_json_safe_route_audit tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_build_controlnet_for_dom_match_stereo_pair_matches_then_converts tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_build_controlnet_for_dom_match_stereo_pair_does_not_convert_after_match_failure tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_controlnet_stereopair_parser_accepts_from_dom_match_adaptive_flags tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_controlnet_stereopair_from_dom_match_dispatches_helper_and_writes_report tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_build_controlnets_for_dom_match_overlap_list_aggregates_routing_audit tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_usage_documents_from_dom_match_adaptive_routing -v
```

Expected: PASS.

- [ ] **Step 5: Run smoke import**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tests/smoke_import.py
```

Expected: PASS.

- [ ] **Step 6: Commit docs and final validation coverage**

```bash
git add examples/controlnet_construct/usage.md tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "docs: describe DOM adaptive routing ControlNet flow" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Final Verification

Run the focused regression set:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest:$PWD/examples"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: PASS.

Check that no generated ISIS output is staged:

```bash
git --no-pager status --short
```

Expected: implementation files and docs only. Do not stage `print.prt`.

---

## Self-Review Notes

- Spec coverage: ORI flow is covered by Tasks 1-2; DOM single-pair flow is covered by Tasks 3-5; batch aggregation is covered by Task 6; docs and validation are covered by Task 7.
- Placeholder scan: this plan avoids deferred implementation markers and includes concrete paths, tests, commands, and code snippets for every code-changing task.
- Type consistency: the new helper names are `build_controlnet_for_dom_match_stereo_pair`, `build_controlnets_for_dom_match_overlap_list`, and `_route_audit_from_match_summary`; tests and implementation tasks use the same names.
