# Adaptive Fast Pipeline Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the existing texture/lighting adaptive `SIFT+FLANN` path as a reproducible adaptive fast pipeline release candidate with summary reporting, docs, tests, and real-data validation.

**Architecture:** Keep ControlNet matching behavior unchanged. Add a small experiment wrapper for the real `pipe_test2` adaptive fast run, a focused summary extractor that reads existing output JSON files, and docs that explain when this fast path should be preferred over deep matchers.

**Tech Stack:** Bash experiment wrapper, Python 3 standard library, existing `run_pipeline_example.sh`, existing adaptive routing JSON outputs, `unittest`, conda environment `asp360_new`.

---

## Scope

This plan implements the release-candidate packaging described in `docs/superpowers/specs/2026-05-27-adaptive-fast-pipeline-performance-design.md`.

It does not change default matcher behavior, adaptive-routing thresholds, deep matcher presets, or ControlNet construction internals.

## File Structure

- Create `examples/controlnet_construct/experiments/summarize_adaptive_fast_pipeline.py`
  - Reads an existing pipeline output directory.
  - Extracts stage timings, pair timings, adaptive route decisions, texture/lighting diagnostics, point counts, batch ControlNet counts, and merged-net existence.
  - Writes JSON by default and optional Markdown.

- Create `examples/controlnet_construct/experiments/run_pipe_test2_adaptive_fast_pipeline.sh`
  - Reproducible wrapper for the real `pipe_test2` adaptive fast pipeline.
  - Uses `flann`, `--adaptive-routing`, `--adaptive-routing-profile balanced`, and existing run-pipeline plumbing.
  - Optionally runs final merge.
  - Runs the summary extractor after the pipeline.

- Modify `examples/controlnet_construct/experiments/README.md`
  - Documents the adaptive fast pipeline command and expected outputs.
  - States that deep matchers are quality/escalation paths, not the CPU speed default.

- Modify `examples/controlnet_construct/PRESETS_README.md`
  - Adds a short note distinguishing classic `SIFT+FLANN` adaptive fast routing from `lightglue_official_sift.json`.

- Create `tests/unitTest/controlnet_construct_adaptive_fast_pipeline_unit_test.py`
  - Tests the summary extractor with synthetic output files.
  - Tests missing-file behavior.
  - Tests the experiment script contains the required adaptive flags and invokes the summary extractor.

## Task 1: Add Adaptive Fast Summary Extractor

**Files:**
- Create: `examples/controlnet_construct/experiments/summarize_adaptive_fast_pipeline.py`
- Test in Task 3: `tests/unitTest/controlnet_construct_adaptive_fast_pipeline_unit_test.py`

- [ ] **Step 1: Create the script skeleton**

Add `examples/controlnet_construct/experiments/summarize_adaptive_fast_pipeline.py`:

```python
#!/usr/bin/env python3
"""Summarize adaptive fast ControlNet pipeline outputs.

Reads output produced by run_pipeline_example.sh and reports the fields needed
to compare the adaptive SIFT/FLANN fast path with deep-matcher alternatives.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload
```

- [ ] **Step 2: Add timing extraction**

Append these helpers:

```python
def _summarize_timing(root: Path) -> dict[str, Any]:
    timing_path = root / "reports" / "pipeline_timing.json"
    timing = _read_json(timing_path)
    steps = timing.get("steps", [])
    pair_matches = timing.get("pair_matches", [])
    return {
        "path": str(timing_path),
        "pipeline": timing.get("pipeline", {}),
        "steps": [
            {
                "name": step.get("name"),
                "status": step.get("status"),
                "duration_seconds": step.get("duration_seconds"),
            }
            for step in steps
            if isinstance(step, dict)
        ],
        "pair_matches": [
            {
                "name": str(pair.get("name", "")).split(":", 1)[-1],
                "status": pair.get("status"),
                "duration_seconds": pair.get("duration_seconds"),
            }
            for pair in pair_matches
            if isinstance(pair, dict)
        ],
    }
```

- [ ] **Step 3: Add pair result extraction**

Append:

```python
def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _route_sidecar(adaptive: dict[str, Any]) -> dict[str, Any]:
    sidecar = adaptive.get("sidecar")
    if isinstance(sidecar, dict):
        return sidecar
    return {}


def _summarize_pair_result(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    adaptive = payload.get("adaptive_routing")
    if not isinstance(adaptive, dict):
        adaptive = {}
    sidecar = _route_sidecar(adaptive)
    texture = sidecar.get("texture_sparseness")
    if not isinstance(texture, dict):
        texture = adaptive.get("texture_sparseness") if isinstance(adaptive.get("texture_sparseness"), dict) else {}
    lighting = sidecar.get("lighting_difference")
    if not isinstance(lighting, dict):
        lighting = adaptive.get("lighting_difference") if isinstance(adaptive.get("lighting_difference"), dict) else {}

    return {
        "pair": path.stem,
        "path": str(path),
        "status": payload.get("status"),
        "matched_point_count": _first_present(
            payload.get("matched_point_count"),
            payload.get("point_count"),
            payload.get("match_count"),
        ),
        "tile_count": payload.get("tile_count"),
        "matched_tile_count": payload.get("matched_tile_count"),
        "skipped_tile_count": payload.get("skipped_tile_count"),
        "adaptive_routing": {
            "status": adaptive.get("status"),
            "selected_initial_matcher": adaptive.get("selected_initial_matcher"),
            "selected_final_matcher": adaptive.get("selected_final_matcher"),
            "route_reason": _first_present(adaptive.get("route_reason"), adaptive.get("reason")),
            "profile": payload.get("adaptive_routing_profile"),
            "pair_texture_sparseness": texture.get("pair_texture_sparseness"),
            "texture_weaker_side": texture.get("weaker_side"),
            "lighting_difference_score": lighting.get("lighting_difference_score"),
            "lighting_reason": lighting.get("reason"),
        },
    }


def _summarize_pairs(root: Path) -> list[dict[str, Any]]:
    match_dir = root / "match_results"
    return [_summarize_pair_result(path) for path in sorted(match_dir.glob("*.json"))]
```

- [ ] **Step 4: Add batch and merged-net extraction**

Append:

```python
def _summarize_batch(root: Path) -> dict[str, Any]:
    batch_path = root / "reports" / "controlnet_batch_summary.json"
    batch = _read_json(batch_path)
    return {
        "path": str(batch_path),
        "pair_count": batch.get("pair_count"),
        "total_merge_point_count": batch.get("total_merge_point_count"),
        "total_dom2ori_retained_count": batch.get("total_dom2ori_retained_count"),
        "total_final_control_point_count": batch.get("total_final_control_point_count"),
        "average_dom2ori_retention_rate": batch.get("average_dom2ori_retention_rate"),
        "overall_dom2ori_retention_rate": batch.get("overall_dom2ori_retention_rate"),
    }


def _summarize_merged_net(root: Path) -> dict[str, Any]:
    net_path = root / "merge" / "dom_matching_merged.net"
    exists = net_path.exists()
    return {
        "path": str(net_path),
        "exists": exists,
        "size_bytes": net_path.stat().st_size if exists else None,
    }
```

- [ ] **Step 5: Add top-level summary and output writers**

Append:

```python
def summarize_output(root: str | Path) -> dict[str, Any]:
    resolved_root = Path(root).expanduser().resolve()
    if not resolved_root.is_dir():
        raise FileNotFoundError(f"pipeline output directory not found: {resolved_root}")
    pairs = _summarize_pairs(resolved_root)
    return {
        "output_root": str(resolved_root),
        "timing": _summarize_timing(resolved_root),
        "controlnet_batch": _summarize_batch(resolved_root),
        "merged_net": _summarize_merged_net(resolved_root),
        "pairs": pairs,
        "route_counts": _route_counts(pairs),
    }


def _route_counts(pairs: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for pair in pairs:
        route = pair.get("adaptive_routing", {})
        if not isinstance(route, dict):
            route = {}
        initial = str(route.get("selected_initial_matcher") or "unknown")
        final = str(route.get("selected_final_matcher") or "unknown")
        key = f"{initial}->{final}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _markdown_table(summary: dict[str, Any]) -> str:
    lines = [
        "# Adaptive Fast Pipeline Summary",
        "",
        f"Output root: `{summary['output_root']}`",
        "",
        "## Stage Timing",
        "",
        "| Stage | Status | Seconds |",
        "|---|---|---:|",
    ]
    for step in summary["timing"]["steps"]:
        lines.append(f"| {step['name']} | {step['status']} | {step['duration_seconds']} |")

    lines.extend(
        [
            "",
            "## Pair Routing",
            "",
            "| Pair | Points | Route | Texture Sparseness | Lighting Difference |",
            "|---|---:|---|---:|---:|",
        ]
    )
    for pair in summary["pairs"]:
        route = pair["adaptive_routing"]
        route_label = f"{route.get('selected_initial_matcher')} -> {route.get('selected_final_matcher')}"
        lines.append(
            "| {pair} | {points} | {route_label} | {texture} | {lighting} |".format(
                pair=pair["pair"],
                points=pair.get("matched_point_count"),
                route_label=route_label,
                texture=route.get("pair_texture_sparseness"),
                lighting=route.get("lighting_difference_score"),
            )
        )
    batch = summary["controlnet_batch"]
    lines.extend(
        [
            "",
            "## ControlNet",
            "",
            f"Final control points: `{batch.get('total_final_control_point_count')}`",
            f"Merged net exists: `{summary['merged_net']['exists']}`",
            f"Merged net path: `{summary['merged_net']['path']}`",
            "",
        ]
    )
    return "\n".join(lines)
```

- [ ] **Step 6: Add CLI**

Append:

```python
def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize an adaptive fast ControlNet pipeline output directory."
    )
    parser.add_argument(
        "output_root",
        help="Pipeline output root, for example /tmp/pipe_test2_adaptive_fast_pipeline/balanced.",
    )
    parser.add_argument(
        "--json-output",
        default=None,
        help="Optional path to write the JSON summary. Default: print JSON to stdout.",
    )
    parser.add_argument(
        "--markdown-output",
        default=None,
        help="Optional path to write a Markdown summary table.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    summary = summarize_output(args.output_root)
    json_text = json.dumps(summary, indent=2, sort_keys=True)
    if args.json_output:
        json_path = Path(args.json_output).expanduser().resolve()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json_text + "\n", encoding="utf-8")
    else:
        print(json_text)
    if args.markdown_output:
        markdown_path = Path(args.markdown_output).expanduser().resolve()
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(_markdown_table(summary) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 7: Smoke-check the CLI help**

Run:

```bash
python examples/controlnet_construct/experiments/summarize_adaptive_fast_pipeline.py --help
```

Expected: exits 0 and prints usage containing `output_root`, `--json-output`, and `--markdown-output`.

- [ ] **Step 8: Commit Task 1**

```bash
git add examples/controlnet_construct/experiments/summarize_adaptive_fast_pipeline.py
git commit -m "feat: summarize adaptive fast pipeline outputs"
```

## Task 2: Add `pipe_test2` Adaptive Fast Experiment Wrapper

**Files:**
- Create: `examples/controlnet_construct/experiments/run_pipe_test2_adaptive_fast_pipeline.sh`
- Modify in Task 3: `tests/unitTest/controlnet_construct_adaptive_fast_pipeline_unit_test.py`

- [ ] **Step 1: Create the script header and defaults**

Create `examples/controlnet_construct/experiments/run_pipe_test2_adaptive_fast_pipeline.sh`:

```bash
#!/usr/bin/env bash
# Reproduce the pipe_test2 adaptive fast ControlNet pipeline.
#
# This wrapper uses classic OpenCV SIFT/FLANN as the requested matcher and
# enables existing texture/sensor-model-lighting adaptive routing. Deep matchers
# remain escalation/reference paths; this script packages the fast CPU path.

set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/../../.." && pwd)

data_dir="/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2"
output_root="/tmp/pipe_test2_adaptive_fast_pipeline"
python_executable="${PYTHON_EXECUTABLE:-python}"
profile="balanced"
adaptive_profile="balanced"
run_final_merge=0
validate_only=0
```

- [ ] **Step 2: Add usage and helpers**

Append:

```bash
usage() {
  cat <<'EOF'
Usage:
  examples/controlnet_construct/experiments/run_pipe_test2_adaptive_fast_pipeline.sh [options]

Run the pipe_test2 adaptive fast ControlNet pipeline:
  - requested matcher: flann
  - adaptive routing: enabled
  - adaptive profile: balanced by default
  - final cnetmerge: skipped unless --run-final-merge is provided

Options:
  --data-dir PATH       Directory with original_images.lis and doms.lis.
  --output-root PATH    Output root. Default: /tmp/pipe_test2_adaptive_fast_pipeline
  --python PATH         Python executable forwarded to run_pipeline_example.sh.
  --parameter-profile NAME
                        ControlNet parameter profile. Default: balanced.
  --adaptive-routing-profile NAME
                        Adaptive routing profile. Default: balanced.
  --validate-only       Validate resolved parameters and exit.
  --run-final-merge     Execute final cnetmerge.
  -h, --help            Show this help.

Runtime setup:
  source "$HOME/miniconda3/etc/profile.d/conda.sh"
  conda activate asp360_new
  export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
  export ISISDATA="$PWD/tests/data/isisdata/mockup"
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_option_value() {
  local option_name=$1
  local value=${2-}
  if [[ -z "$value" || "$value" == --* ]]; then
    die "missing value for $option_name"
  fi
}
```

- [ ] **Step 3: Add argument parsing**

Append:

```bash
while [[ $# -gt 0 ]]; do
  case "$1" in
    --data-dir)
      require_option_value "$1" "${2-}"
      data_dir=$2
      shift 2
      ;;
    --output-root)
      require_option_value "$1" "${2-}"
      output_root=$2
      shift 2
      ;;
    --python)
      require_option_value "$1" "${2-}"
      python_executable=$2
      shift 2
      ;;
    --parameter-profile)
      require_option_value "$1" "${2-}"
      profile=$2
      shift 2
      ;;
    --adaptive-routing-profile)
      require_option_value "$1" "${2-}"
      adaptive_profile=$2
      shift 2
      ;;
    --validate-only)
      validate_only=1
      shift
      ;;
    --run-final-merge)
      run_final_merge=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      die "unknown argument: $1"
      ;;
  esac
done
```

- [ ] **Step 4: Add command construction**

Append:

```bash
original_list="$data_dir/original_images.lis"
dom_list="$data_dir/doms.lis"
work_dir="$output_root/$profile"
logs_dir="$output_root/logs"
summary_json="$work_dir/reports/adaptive_fast_summary.json"
summary_md="$work_dir/reports/adaptive_fast_summary.md"

[[ -f "$original_list" ]] || die "missing original list: $original_list"
[[ -f "$dom_list" ]] || die "missing DOM list: $dom_list"
mkdir -p "$logs_dir"

command=(
  bash "$repo_root/examples/controlnet_construct/run_pipeline_example.sh"
  --work-dir "$work_dir"
  --original-list "$original_list"
  --dom-list "$dom_list"
  --python "$python_executable"
  --parameter-profile "$profile"
  --matcher-method flann
  --adaptive-routing
  --adaptive-routing-profile "$adaptive_profile"
)

if [[ "$validate_only" == "1" ]]; then
  command+=(--validate-parameters-only)
elif [[ "$run_final_merge" != "1" ]]; then
  command+=(--skip-final-merge)
fi
```

- [ ] **Step 5: Add execution and summary generation**

Append:

```bash
printf '===== pipe_test2 adaptive fast pipeline =====\n'
printf 'Command:'
printf ' %q' "${command[@]}"
printf '\n'

if [[ "$validate_only" == "1" ]]; then
  "${command[@]}"
else
  /usr/bin/time -p "${command[@]}" 2>&1 | tee "$logs_dir/adaptive_fast_pipeline.log"
  status=${PIPESTATUS[0]}
  printf '===== adaptive fast pipeline done status=%s log=%s =====\n' "$status" "$logs_dir/adaptive_fast_pipeline.log"
  [[ "$status" -eq 0 ]] || exit "$status"

  "$python_executable" "$repo_root/examples/controlnet_construct/experiments/summarize_adaptive_fast_pipeline.py" \
    "$work_dir" \
    --json-output "$summary_json" \
    --markdown-output "$summary_md"

  printf 'Summary JSON: %s\n' "$summary_json"
  printf 'Summary Markdown: %s\n' "$summary_md"
fi
```

- [ ] **Step 6: Make the script executable**

Run:

```bash
chmod +x examples/controlnet_construct/experiments/run_pipe_test2_adaptive_fast_pipeline.sh
```

- [ ] **Step 7: Validate script help**

Run:

```bash
examples/controlnet_construct/experiments/run_pipe_test2_adaptive_fast_pipeline.sh --help
```

Expected: exits 0 and prints the adaptive fast usage block.

- [ ] **Step 8: Commit Task 2**

```bash
git add examples/controlnet_construct/experiments/run_pipe_test2_adaptive_fast_pipeline.sh
git commit -m "feat: add pipe_test2 adaptive fast pipeline runner"
```

## Task 3: Add Unit Coverage for Summary and Runner Packaging

**Files:**
- Create: `tests/unitTest/controlnet_construct_adaptive_fast_pipeline_unit_test.py`
- Test: `tests/unitTest/controlnet_construct_adaptive_fast_pipeline_unit_test.py`

- [ ] **Step 1: Create the test module imports and fixture helper**

Create `tests/unitTest/controlnet_construct_adaptive_fast_pipeline_unit_test.py`:

```python
"""Tests for adaptive fast pipeline experiment packaging."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = PROJECT_ROOT / "examples"
if str(EXAMPLES_ROOT) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_ROOT))

from controlnet_construct.experiments import summarize_adaptive_fast_pipeline as summary_module  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
```

- [ ] **Step 2: Add a complete synthetic output tree test**

Append:

```python
class AdaptiveFastPipelineSummaryTest(unittest.TestCase):
    def test_summarize_output_reports_timing_routes_and_controlnet_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_json(
                root / "reports" / "pipeline_timing.json",
                {
                    "pipeline": {"status": "success"},
                    "steps": [
                        {"name": "image_overlap", "status": "success", "duration_seconds": 1},
                        {"name": "image_match_batch", "status": "success", "duration_seconds": 37},
                    ],
                    "pair_matches": [
                        {
                            "name": "image_match:left__right",
                            "status": "success",
                            "duration_seconds": 5,
                        }
                    ],
                },
            )
            _write_json(
                root / "reports" / "controlnet_batch_summary.json",
                {
                    "pair_count": 1,
                    "total_merge_point_count": 120,
                    "total_dom2ori_retained_count": 100,
                    "total_final_control_point_count": 100,
                    "average_dom2ori_retention_rate": 0.8,
                    "overall_dom2ori_retention_rate": 0.833333,
                },
            )
            _write_json(
                root / "match_results" / "left__right.json",
                {
                    "status": "success",
                    "matched_point_count": 42,
                    "tile_count": 10,
                    "matched_tile_count": 7,
                    "skipped_tile_count": 3,
                    "adaptive_routing_profile": "balanced",
                    "adaptive_routing": {
                        "status": "routed",
                        "selected_initial_matcher": "flann",
                        "selected_final_matcher": "flann",
                        "route_reason": "rich texture and small lighting difference",
                        "sidecar": {
                            "texture_sparseness": {
                                "pair_texture_sparseness": 0.14,
                                "weaker_side": "left",
                            },
                            "lighting_difference": {
                                "lighting_difference_score": 0.006,
                                "reason": "weighted sum",
                            },
                        },
                    },
                },
            )
            merged_net = root / "merge" / "dom_matching_merged.net"
            merged_net.parent.mkdir(parents=True)
            merged_net.write_bytes(b"net")

            summary = summary_module.summarize_output(root)

        self.assertEqual(summary["controlnet_batch"]["total_final_control_point_count"], 100)
        self.assertEqual(summary["merged_net"]["exists"], True)
        self.assertEqual(summary["route_counts"], {"flann->flann": 1})
        self.assertEqual(summary["timing"]["steps"][1]["duration_seconds"], 37)
        self.assertEqual(summary["pairs"][0]["matched_point_count"], 42)
        self.assertEqual(summary["pairs"][0]["adaptive_routing"]["pair_texture_sparseness"], 0.14)
        self.assertEqual(summary["pairs"][0]["adaptive_routing"]["lighting_difference_score"], 0.006)
```

- [ ] **Step 3: Add missing output directory behavior test**

Append:

```python
    def test_summarize_output_rejects_missing_root(self):
        missing = Path(tempfile.gettempdir()) / "missing-adaptive-fast-output-for-unit-test"
        if missing.exists():
            self.skipTest(f"unexpected existing path: {missing}")
        with self.assertRaises(FileNotFoundError):
            summary_module.summarize_output(missing)
```

- [ ] **Step 4: Add Markdown output coverage**

Append:

```python
    def test_markdown_table_contains_pair_and_controlnet_count(self):
        summary = {
            "output_root": "/tmp/example",
            "timing": {
                "steps": [
                    {"name": "image_match_batch", "status": "success", "duration_seconds": 37}
                ]
            },
            "controlnet_batch": {"total_final_control_point_count": 37455},
            "merged_net": {"exists": True, "path": "/tmp/example/merge/dom_matching_merged.net"},
            "pairs": [
                {
                    "pair": "left__right",
                    "matched_point_count": 42,
                    "adaptive_routing": {
                        "selected_initial_matcher": "flann",
                        "selected_final_matcher": "flann",
                        "pair_texture_sparseness": 0.14,
                        "lighting_difference_score": 0.006,
                    },
                }
            ],
        }
        markdown = summary_module._markdown_table(summary)
        self.assertIn("| image_match_batch | success | 37 |", markdown)
        self.assertIn("| left__right | 42 | flann -> flann | 0.14 | 0.006 |", markdown)
        self.assertIn("Final control points: `37455`", markdown)
```

- [ ] **Step 5: Add shell wrapper text regression**

Append:

```python
class AdaptiveFastPipelineRunnerTest(unittest.TestCase):
    def test_runner_uses_flann_adaptive_balanced_and_summary_extractor(self):
        script_path = (
            PROJECT_ROOT
            / "examples"
            / "controlnet_construct"
            / "experiments"
            / "run_pipe_test2_adaptive_fast_pipeline.sh"
        )
        text = script_path.read_text(encoding="utf-8")
        self.assertIn("--matcher-method flann", text)
        self.assertIn("--adaptive-routing", text)
        self.assertIn("--adaptive-routing-profile", text)
        self.assertIn('adaptive_profile="balanced"', text)
        self.assertIn("summarize_adaptive_fast_pipeline.py", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: Run the new test module and verify it passes**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_adaptive_fast_pipeline_unit_test -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit Task 3**

```bash
git add tests/unitTest/controlnet_construct_adaptive_fast_pipeline_unit_test.py
git commit -m "test: cover adaptive fast pipeline packaging"
```

## Task 4: Document the Adaptive Fast Release Candidate

**Files:**
- Modify: `examples/controlnet_construct/experiments/README.md`
- Modify: `examples/controlnet_construct/PRESETS_README.md`

- [ ] **Step 1: Add an experiments README section**

Append this section near other `pipe_test2` experiment descriptions in `examples/controlnet_construct/experiments/README.md`:

```markdown
## pipe_test2 Adaptive Fast Pipeline

`run_pipe_test2_adaptive_fast_pipeline.sh` packages the current recommended
CPU fast path for LRO-style DOM ControlNet construction. It requests classic
OpenCV `SIFT+FLANN`, enables texture and sensor-model-lighting adaptive routing,
and uses the `balanced` adaptive-routing profile by default.

This path is intentionally different from `lightglue_official_sift.json`.
`lightglue_official_sift.json` uses the official LightGlue SIFT frontend plus
the LightGlue neural matcher. On CPU, that path can be orders of magnitude
slower per 512 x 512 tile than OpenCV `SIFT+FLANN`.

Runtime setup:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
```

Validation-only run:

```bash
examples/controlnet_construct/experiments/run_pipe_test2_adaptive_fast_pipeline.sh \
  --validate-only
```

Real-data run with final merge:

```bash
examples/controlnet_construct/experiments/run_pipe_test2_adaptive_fast_pipeline.sh \
  --output-root /tmp/pipe_test2_adaptive_fast_pipeline \
  --run-final-merge
```

Key outputs:

- `<output-root>/balanced/reports/pipeline_timing.json`
- `<output-root>/balanced/match_results/*.json`
- `<output-root>/balanced/reports/controlnet_batch_summary.json`
- `<output-root>/balanced/reports/adaptive_fast_summary.json`
- `<output-root>/balanced/reports/adaptive_fast_summary.md`
- `<output-root>/balanced/merge/dom_matching_merged.net`

The summary extractor can also be run on any compatible output directory:

```bash
python examples/controlnet_construct/experiments/summarize_adaptive_fast_pipeline.py \
  /tmp/pipe_test2_adaptive_fast_pipeline/balanced \
  --json-output /tmp/pipe_test2_adaptive_fast_pipeline/balanced/reports/adaptive_fast_summary.json \
  --markdown-output /tmp/pipe_test2_adaptive_fast_pipeline/balanced/reports/adaptive_fast_summary.md
```
```

- [ ] **Step 2: Add a PRESETS README note**

In `examples/controlnet_construct/PRESETS_README.md`, add this note near the classic SIFT or official LightGlue SIFT discussion:

```markdown
### Adaptive Fast Classic SIFT/FLANN

For CPU throughput on LRO-style DOM matching, the recommended fast path is not a
deep matcher preset. Use classic OpenCV `SIFT+FLANN` with adaptive routing:

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir /tmp/pipe_test2_adaptive_fast_pipeline/balanced \
  --original-list /media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2/original_images.lis \
  --dom-list /media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2/doms.lis \
  --parameter-profile balanced \
  --matcher-method flann \
  --adaptive-routing \
  --adaptive-routing-profile balanced
```

The adaptive router records texture sparseness and sensor-model lighting
difference in each image-match result JSON. It can keep rich, low-lighting-
difference pairs on `flann` and reserve deep matchers for harder cases.

`lightglue_official_sift.json` is a different path: it uses the official
LightGlue SIFT frontend and the neural LightGlue matcher. It is useful as a
quality-reference deep matcher, but it is not the CPU speed default.
```

- [ ] **Step 3: Run documentation text checks**

Run:

```bash
rg -n "Adaptive Fast|run_pipe_test2_adaptive_fast_pipeline|summarize_adaptive_fast_pipeline|lightglue_official_sift" examples/controlnet_construct/experiments/README.md examples/controlnet_construct/PRESETS_README.md
```

Expected: both README files contain the new documentation references.

- [ ] **Step 4: Commit Task 4**

```bash
git add examples/controlnet_construct/experiments/README.md examples/controlnet_construct/PRESETS_README.md
git commit -m "docs: document adaptive fast pipeline runner"
```

## Task 5: Focused Verification

**Files:**
- No new files expected.
- May update code from earlier tasks only if a verification failure proves a bug in those tasks.

- [ ] **Step 1: Run the new unit tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_adaptive_fast_pipeline_unit_test -v
```

Expected: all tests pass.

- [ ] **Step 2: Run adaptive-routing and pipeline regression tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest \
  tests.unitTest.image_match_adaptive_routing_unit_test \
  tests.unitTest.controlnet_construct_pipeline_unit_test \
  tests.unitTest.controlnet_construct_matching_unit_test \
  -v
```

Expected: all tests pass.

- [ ] **Step 3: Run wrapper validation-only check**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
examples/controlnet_construct/experiments/run_pipe_test2_adaptive_fast_pipeline.sh \
  --output-root /tmp/pipe_test2_adaptive_fast_pipeline_validate \
  --validate-only
```

Expected: exits 0 and prints resolved run-pipeline settings with `Matcher method: flann`, `Adaptive routing: enabled`, and `Adaptive routing profile: balanced`.

- [ ] **Step 4: Commit any verification fixes**

If Steps 1-3 required fixes, commit them:

```bash
git add examples/controlnet_construct/experiments/summarize_adaptive_fast_pipeline.py \
  examples/controlnet_construct/experiments/run_pipe_test2_adaptive_fast_pipeline.sh \
  tests/unitTest/controlnet_construct_adaptive_fast_pipeline_unit_test.py \
  examples/controlnet_construct/experiments/README.md \
  examples/controlnet_construct/PRESETS_README.md
git commit -m "fix: stabilize adaptive fast pipeline packaging"
```

If no fixes were needed, do not create an empty commit.

## Task 6: Real `pipe_test2` Release-Candidate Run

**Files:**
- No repo files expected.
- Outputs under `/tmp/pipe_test2_adaptive_fast_pipeline_release_candidate`.

- [ ] **Step 1: Run the real adaptive fast pipeline**

This command uses multiprocessing and real ISIS data. If it fails in a restricted sandbox with `multiprocessing.Manager()` socket permission errors, rerun outside the sandbox with approval.

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
examples/controlnet_construct/experiments/run_pipe_test2_adaptive_fast_pipeline.sh \
  --output-root /tmp/pipe_test2_adaptive_fast_pipeline_release_candidate \
  --run-final-merge
```

Expected: exits 0 and writes:

- `/tmp/pipe_test2_adaptive_fast_pipeline_release_candidate/balanced/reports/adaptive_fast_summary.json`
- `/tmp/pipe_test2_adaptive_fast_pipeline_release_candidate/balanced/reports/adaptive_fast_summary.md`
- `/tmp/pipe_test2_adaptive_fast_pipeline_release_candidate/balanced/merge/dom_matching_merged.net`

- [ ] **Step 2: Inspect the summary**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path
summary = json.loads(Path("/tmp/pipe_test2_adaptive_fast_pipeline_release_candidate/balanced/reports/adaptive_fast_summary.json").read_text())
print("route_counts", summary["route_counts"])
print("final_points", summary["controlnet_batch"]["total_final_control_point_count"])
print("merged_net", summary["merged_net"])
for step in summary["timing"]["steps"]:
    print(step["name"], step["status"], step["duration_seconds"])
PY
```

Expected:

- `route_counts` is present.
- `final_points` is a positive integer.
- `merged_net.exists` is `True`.
- every stage status is `success`.

- [ ] **Step 3: Record release-candidate evidence in final response**

Do not commit `/tmp` outputs. Summarize:

- total runtime,
- route counts,
- final control points,
- merged net path and size,
- any warnings or environment caveats.

## Task 7: Final Branch State and PR Readiness

**Files:**
- No new files expected unless a changelog file exists and the user explicitly asks to update it.

- [ ] **Step 1: Check git status**

Run:

```bash
git status --short --branch
```

Expected:

- Feature files are committed.
- `.gitignore` and `print.prt` may remain as local unstaged files and must not be staged unless explicitly requested.

- [ ] **Step 2: Review commit list**

Run:

```bash
git log --oneline --decorate -8
```

Expected: recent commits include:

- `feat: summarize adaptive fast pipeline outputs`
- `feat: add pipe_test2 adaptive fast pipeline runner`
- `test: cover adaptive fast pipeline packaging`
- `docs: document adaptive fast pipeline runner`

- [ ] **Step 3: Report integration options**

If all verification passes, report:

1. Create PR and merge to `origin/main`.
2. Run one more hard-case dataset before PR.
3. Keep branch local for review.

Do not perform GitHub publication unless the user requests it.

## Self-Review Checklist

- Spec coverage: The plan covers experiment script, summary extractor, documentation, focused tests, real `pipe_test2` validation, and release-candidate evidence.
- Scope control: The plan avoids changing default matcher behavior, adaptive thresholds, deep matcher presets, or ControlNet internals.
- Type consistency: The summary extractor consistently uses `dict[str, Any]`, `Path`, and JSON-safe values.
- Local-file rule: The plan explicitly avoids staging `.gitignore` and `print.prt`.
- Sandbox caveat: The real-data task documents the known multiprocessing socket permission issue and the need for approved rerun outside restricted sandbox.
