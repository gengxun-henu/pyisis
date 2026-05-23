# Raw Image Space ControlNet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an independent raw/original image space ControlNet pipeline wrapper that batch-runs existing `from-ori-match` pair construction and prepares the final merge.

**Architecture:** Keep the first version wrapper-driven. Add one new shell entry point that reuses `image_overlap.py`, `controlnet_stereopair.py from-ori-match`, and `controlnet_merge.py`; add focused dry-run tests that verify command generation and validation without requiring real image matching. Do not change the existing DOM pipeline.

**Tech Stack:** Bash, Python `unittest`, existing PyISIS/ISIS command-line wrappers, conda `asp360_new`.

---

## File Structure

- Create `examples/controlnet_construct/run_ori_match_pipeline_example.sh`
  - Responsibility: parse raw image pipeline CLI options, create stable work directories, generate and run overlap/match/merge commands, support deterministic `--dry-run`, and write compact batch summaries.
- Modify `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
  - Responsibility: add wrapper-level regression coverage for dry-run command generation and argument validation.
- Modify `examples/controlnet_construct/usage.md`
  - Responsibility: document the new raw image space wrapper as a separate path from the DOM pipeline.
- Modify `docs/superpowers/plans/2026-05-23-raw-image-space-controlnet.md`
  - Responsibility: check off tasks as implementation proceeds.

No changes should be made to `examples/controlnet_construct/run_pipeline_example.sh`, `examples/image_match/image_match.py`, or `controlnet_stereopair.py` unless a test exposes a narrow missing capability. The expected first version only adds orchestration.

## Task 1: Add Dry-Run Command Generation Contract

**Files:**
- Create: `examples/controlnet_construct/run_ori_match_pipeline_example.sh`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [x] **Step 1: Add the wrapper path constant to the test file**

In `tests/unitTest/controlnet_construct_pipeline_unit_test.py`, add this near the existing `RUN_PIPELINE_EXAMPLE_PATH` constants:

```python
RUN_ORI_MATCH_PIPELINE_EXAMPLE_PATH = PROJECT_ROOT / "examples" / "controlnet_construct" / "run_ori_match_pipeline_example.sh"
```

- [x] **Step 2: Write the failing dry-run command-generation test**

Add this method to `ControlNetConstructPipelineUnitTest`:

```python
    def test_run_ori_match_pipeline_dry_run_writes_expected_commands(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work_ori"
            work_dir.mkdir()
            inputs_dir = temp_dir / "inputs"
            inputs_dir.mkdir()
            left = inputs_dir / "left.cub"
            right = inputs_dir / "right.cub"
            left.write_text("left placeholder\n", encoding="utf-8")
            right.write_text("right placeholder\n", encoding="utf-8")
            original_list = work_dir / "original_images.lis"
            original_list.write_text(f"{left}\n{right}\n", encoding="utf-8")
            overlap_list = work_dir / "images_overlap.lis"
            overlap_list.write_text(f"{left},{right}\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "raw_ori_unit",
                        "TargetName": "Mars",
                        "UserName": "unit",
                        "Description": "raw image unit test",
                    }
                )
                + "\n",
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
                    "--matcher-method",
                    "flann",
                    "--ratio-test",
                    "0.8",
                    "--max-features",
                    "1200",
                    "--pair-id-prefix",
                    "R",
                    "--pair-id-start",
                    "7",
                    "--num-worker-parallel-cpu",
                    "2",
                    "--dry-run",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            command_script = work_dir / "command.sh"
            self.assertTrue(command_script.exists())
            command_text = command_script.read_text(encoding="utf-8")

        self.assertIn("image_overlap.py", command_text)
        self.assertIn("controlnet_stereopair.py", command_text)
        self.assertIn("from-ori-match", command_text)
        self.assertIn("controlnet_merge.py", command_text)
        self.assertIn(str(left), command_text)
        self.assertIn(str(right), command_text)
        self.assertIn("--pair-id", command_text)
        self.assertIn("R7", command_text)
        self.assertIn("--left-output-key", command_text)
        self.assertIn("ori_keys/left__right_A.key", command_text)
        self.assertIn("ori_keys/left__right_B.key", command_text)
        self.assertIn("ori_pair_nets/left__right.net", command_text)
        self.assertIn("--matcher-method", command_text)
        self.assertIn("flann", command_text)
        self.assertIn("--ratio-test", command_text)
        self.assertIn("0.8", command_text)
        self.assertIn("--max-features", command_text)
        self.assertIn("1200", command_text)
        self.assertIn("--num-worker-parallel-cpu", command_text)
        self.assertIn("2", command_text)
        self.assertIn("merge_all_controlnets.sh", command_text)
```

- [x] **Step 3: Run the new test and verify it fails**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_ori_match_pipeline_dry_run_writes_expected_commands -v
```

Expected: `FAIL` or `ERROR` because `run_ori_match_pipeline_example.sh` does not exist yet.

- [x] **Step 4: Add the minimal shell wrapper skeleton**

Create `examples/controlnet_construct/run_ori_match_pipeline_example.sh` with:

```bash
#!/usr/bin/env bash

# End-to-end raw/original image matching ControlNet pipeline example runner.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/../.." && pwd)

DEFAULT_CONFIG_RELATIVE="examples/controlnet_construct/controlnet_config.example.json"
DEFAULT_WORK_DIR_RELATIVE="work_ori"
DEFAULT_PAIR_ID_PREFIX="S"
DEFAULT_PAIR_ID_START="1"
PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-python}"

log() {
  printf '[ori-match-pipeline] %s\n' "$*"
}

die() {
  printf '[ori-match-pipeline] error: %s\n' "$*" >&2
  exit 1
}

quote_cmd() {
  local quoted=()
  local arg
  for arg in "$@"; do
    quoted+=("$(printf '%q' "$arg")")
  done
  printf '%s\n' "${quoted[*]}"
}

append_command() {
  quote_cmd "$@" >> "$COMMAND_SCRIPT"
}

pair_tag_from_paths() {
  local left=$1
  local right=$2
  local left_stem
  local right_stem
  left_stem=$(basename "${left%.*}")
  right_stem=$(basename "${right%.*}")
  printf '%s__%s\n' "$left_stem" "$right_stem"
}

usage() {
  cat <<'EOF'
Usage:
  examples/controlnet_construct/run_ori_match_pipeline_example.sh [options]

Run raw/original image matching ControlNet construction:
  1. image_overlap.py
  2. controlnet_stereopair.py from-ori-match for every overlap pair
  3. controlnet_merge.py and optionally the generated merge script

Options:
  --work-dir PATH                Work directory. Default: work_ori
  --original-list PATH           original_images.lis path. Default: <work-dir>/original_images.lis
  --images-overlap-list PATH     images_overlap.lis path. Default: <work-dir>/images_overlap.lis
  --config PATH                  ControlNet config JSON. Default: examples/controlnet_construct/controlnet_config.example.json
  --matcher-method NAME          Matcher method forwarded to from-ori-match. Default: flann
  --band N                       Band forwarded to from-ori-match. Default: 1
  --ratio-test FLOAT             Ratio test threshold. Default: 0.75
  --max-features N               Optional SIFT max_features.
  --pair-id-prefix VALUE         Pair id prefix. Default: S
  --pair-id-start N              Pair id start. Default: 1
  --num-worker-parallel-cpu N    CPU worker count. Default: 8
  --use-parallel-cpu             Enable parallel CPU matching. Default.
  --no-parallel-cpu              Disable parallel CPU matching.
  --use-gpu                      Enable GPU route when supported.
  --gpu-batch-size N             GPU batch size. Default: 4
  --gpu-dynamic-batch            Enable dynamic GPU batch sizing. Default.
  --no-gpu-dynamic-batch         Disable dynamic GPU batch sizing.
  --gpu-min-batch-size N         Minimum dynamic GPU batch size. Default: 2
  --gpu-max-batch-size N         Maximum dynamic GPU batch size. Default: 16
  --skip-final-merge             Generate but do not execute merge shell.
  --dry-run                      Write command.sh and summary without executing commands.
  --log-level VALUE              from-ori-match log level. Default: INFO
  -h, --help                     Show this help.
EOF
}

WORK_DIR=""
ORIGINAL_LIST=""
IMAGES_OVERLAP_LIST=""
CONFIG_PATH=""
MATCHER_METHOD="flann"
BAND="1"
RATIO_TEST="0.75"
MAX_FEATURES=""
PAIR_ID_PREFIX="$DEFAULT_PAIR_ID_PREFIX"
PAIR_ID_START="$DEFAULT_PAIR_ID_START"
NUM_WORKER_PARALLEL_CPU="8"
USE_PARALLEL_CPU="1"
USE_GPU="0"
GPU_BATCH_SIZE="4"
GPU_DYNAMIC_BATCH="1"
GPU_MIN_BATCH_SIZE="2"
GPU_MAX_BATCH_SIZE="16"
SKIP_FINAL_MERGE="0"
DRY_RUN="0"
LOG_LEVEL="INFO"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --work-dir) [[ $# -ge 2 ]] || die "missing value for --work-dir"; WORK_DIR=$2; shift 2 ;;
    --original-list) [[ $# -ge 2 ]] || die "missing value for --original-list"; ORIGINAL_LIST=$2; shift 2 ;;
    --images-overlap-list) [[ $# -ge 2 ]] || die "missing value for --images-overlap-list"; IMAGES_OVERLAP_LIST=$2; shift 2 ;;
    --config) [[ $# -ge 2 ]] || die "missing value for --config"; CONFIG_PATH=$2; shift 2 ;;
    --matcher-method) [[ $# -ge 2 ]] || die "missing value for --matcher-method"; MATCHER_METHOD=$2; shift 2 ;;
    --band) [[ $# -ge 2 ]] || die "missing value for --band"; BAND=$2; shift 2 ;;
    --ratio-test) [[ $# -ge 2 ]] || die "missing value for --ratio-test"; RATIO_TEST=$2; shift 2 ;;
    --max-features) [[ $# -ge 2 ]] || die "missing value for --max-features"; MAX_FEATURES=$2; shift 2 ;;
    --pair-id-prefix) [[ $# -ge 2 ]] || die "missing value for --pair-id-prefix"; PAIR_ID_PREFIX=$2; shift 2 ;;
    --pair-id-start) [[ $# -ge 2 ]] || die "missing value for --pair-id-start"; PAIR_ID_START=$2; shift 2 ;;
    --num-worker-parallel-cpu) [[ $# -ge 2 ]] || die "missing value for --num-worker-parallel-cpu"; NUM_WORKER_PARALLEL_CPU=$2; shift 2 ;;
    --use-parallel-cpu) USE_PARALLEL_CPU="1"; shift ;;
    --no-parallel-cpu) USE_PARALLEL_CPU="0"; shift ;;
    --use-gpu) USE_GPU="1"; shift ;;
    --gpu-batch-size) [[ $# -ge 2 ]] || die "missing value for --gpu-batch-size"; GPU_BATCH_SIZE=$2; shift 2 ;;
    --gpu-dynamic-batch) GPU_DYNAMIC_BATCH="1"; shift ;;
    --no-gpu-dynamic-batch) GPU_DYNAMIC_BATCH="0"; shift ;;
    --gpu-min-batch-size) [[ $# -ge 2 ]] || die "missing value for --gpu-min-batch-size"; GPU_MIN_BATCH_SIZE=$2; shift 2 ;;
    --gpu-max-batch-size) [[ $# -ge 2 ]] || die "missing value for --gpu-max-batch-size"; GPU_MAX_BATCH_SIZE=$2; shift 2 ;;
    --skip-final-merge) SKIP_FINAL_MERGE="1"; shift ;;
    --dry-run) DRY_RUN="1"; shift ;;
    --log-level) [[ $# -ge 2 ]] || die "missing value for --log-level"; LOG_LEVEL=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    --deep-match-config-path|--deep-match-mode|--adaptive-routing|--no-adaptive-routing)
      die "$1 is not supported by the raw image space wrapper first version"
      ;;
    *) die "unknown option: $1" ;;
  esac
done

case "$PAIR_ID_START" in
  ''|*[!0-9]*) die "--pair-id-start must be a positive integer" ;;
esac
if [[ "$PAIR_ID_START" -lt 1 ]]; then
  die "--pair-id-start must be at least 1"
fi

WORK_DIR="${WORK_DIR:-$REPO_ROOT/$DEFAULT_WORK_DIR_RELATIVE}"
CONFIG_PATH="${CONFIG_PATH:-$REPO_ROOT/$DEFAULT_CONFIG_RELATIVE}"
ORIGINAL_LIST="${ORIGINAL_LIST:-$WORK_DIR/original_images.lis}"
IMAGES_OVERLAP_LIST="${IMAGES_OVERLAP_LIST:-$WORK_DIR/images_overlap.lis}"

WORK_DIR=$(cd -- "$(dirname -- "$WORK_DIR")" && pwd)/$(basename -- "$WORK_DIR")
CONFIG_PATH=$(cd -- "$(dirname -- "$CONFIG_PATH")" && pwd)/$(basename -- "$CONFIG_PATH")
ORIGINAL_LIST=$(cd -- "$(dirname -- "$ORIGINAL_LIST")" && pwd)/$(basename -- "$ORIGINAL_LIST")
IMAGES_OVERLAP_LIST=$(cd -- "$(dirname -- "$IMAGES_OVERLAP_LIST")" && pwd)/$(basename -- "$IMAGES_OVERLAP_LIST")

ORI_KEYS_DIR="$WORK_DIR/ori_keys"
PAIR_NETS_DIR="$WORK_DIR/ori_pair_nets"
REPORTS_DIR="$WORK_DIR/reports"
MERGE_DIR="$WORK_DIR/merge"
COMMAND_SCRIPT="$WORK_DIR/command.sh"
BATCH_REPORT_PATH="$REPORTS_DIR/ori_match_batch_summary.json"
OVERLAP_REPORT_PATH="$REPORTS_DIR/image_overlap_summary.json"
MERGE_OUTPUT_NET="$MERGE_DIR/ori_matching_merged.net"
MERGE_SCRIPT_PATH="$MERGE_DIR/merge_all_controlnets.sh"
MERGE_PAIR_LIST_PATH="$MERGE_DIR/merge_all_controlnets.lis"
MERGE_REPORT_PATH="$MERGE_DIR/controlnet_merge_summary.json"

mkdir -p "$WORK_DIR" "$ORI_KEYS_DIR" "$PAIR_NETS_DIR" "$REPORTS_DIR" "$MERGE_DIR"
: > "$COMMAND_SCRIPT"
chmod 755 "$COMMAND_SCRIPT"

[[ -f "$ORIGINAL_LIST" ]] || die "original image list not found: $ORIGINAL_LIST"
[[ -f "$CONFIG_PATH" ]] || die "controlnet config not found: $CONFIG_PATH"

append_command "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_overlap.py" \
  "$ORIGINAL_LIST" "$IMAGES_OVERLAP_LIST" --report-json "$OVERLAP_REPORT_PATH"

pair_index=0
if [[ -f "$IMAGES_OVERLAP_LIST" ]]; then
  while IFS=, read -r left right; do
    [[ -n "$left" ]] || continue
    [[ -n "$right" ]] || die "invalid overlap pair line missing right-hand entry"
    pair_index=$((pair_index + 1))
    pair_id="${PAIR_ID_PREFIX}$((PAIR_ID_START + pair_index - 1))"
    pair_tag=$(pair_tag_from_paths "$left" "$right")
    match_args=(
      "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/controlnet_stereopair.py" from-ori-match
      "$left" "$right" "$CONFIG_PATH" "$PAIR_NETS_DIR/${pair_tag}.net"
      --pair-id "$pair_id"
      --left-output-key "$ORI_KEYS_DIR/${pair_tag}_A.key"
      --right-output-key "$ORI_KEYS_DIR/${pair_tag}_B.key"
      --report-path "$REPORTS_DIR/${pair_tag}.summary.json"
      --matcher-method "$MATCHER_METHOD"
      --band "$BAND"
      --ratio-test "$RATIO_TEST"
      --num-worker-parallel-cpu "$NUM_WORKER_PARALLEL_CPU"
      --gpu-batch-size "$GPU_BATCH_SIZE"
      --gpu-min-batch-size "$GPU_MIN_BATCH_SIZE"
      --gpu-max-batch-size "$GPU_MAX_BATCH_SIZE"
      --log-level "$LOG_LEVEL"
    )
    [[ -z "$MAX_FEATURES" ]] || match_args+=(--max-features "$MAX_FEATURES")
    [[ "$USE_PARALLEL_CPU" == "1" ]] && match_args+=(--use-parallel-cpu) || match_args+=(--no-parallel-cpu)
    [[ "$USE_GPU" == "1" ]] && match_args+=(--use-gpu)
    [[ "$GPU_DYNAMIC_BATCH" == "1" ]] && match_args+=(--gpu-dynamic-batch) || match_args+=(--no-gpu-dynamic-batch)
    append_command "${match_args[@]}"
  done < "$IMAGES_OVERLAP_LIST"
fi

append_command "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/controlnet_merge.py" \
  "$IMAGES_OVERLAP_LIST" "$PAIR_NETS_DIR" "$MERGE_OUTPUT_NET" "$MERGE_SCRIPT_PATH" \
  --network-id "raw_image_matching" \
  --description "Merged raw image matching ControlNet" \
  --pair-list "$MERGE_PAIR_LIST_PATH" \
  --report-json "$MERGE_REPORT_PATH"

if [[ "$SKIP_FINAL_MERGE" != "1" ]]; then
  append_command bash "$MERGE_SCRIPT_PATH"
fi

if [[ "$DRY_RUN" == "1" ]]; then
  log "dry run complete: $COMMAND_SCRIPT"
  exit 0
fi

die "execution mode is not implemented yet"
```

- [x] **Step 5: Run the dry-run test and verify it passes**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_ori_match_pipeline_dry_run_writes_expected_commands -v
```

Expected: `OK`.

- [x] **Step 6: Commit Task 1**

```bash
git add examples/controlnet_construct/run_ori_match_pipeline_example.sh tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "test: cover raw image pipeline dry run"
```

## Task 2: Add Validation Coverage and Tighten Wrapper Parsing

**Files:**
- Modify: `examples/controlnet_construct/run_ori_match_pipeline_example.sh`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Add failing validation tests**

Add these methods to `ControlNetConstructPipelineUnitTest`:

```python
    def test_run_ori_match_pipeline_rejects_invalid_pair_id_start(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work_ori"
            work_dir.mkdir()
            original_list = work_dir / "original_images.lis"
            original_list.write_text("left.cub\nright.cub\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text('{"NetworkId":"n","TargetName":"Mars","UserName":"u"}\n', encoding="utf-8")

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
                    "--pair-id-start",
                    "0",
                    "--dry-run",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--pair-id-start must be at least 1", result.stderr)

    def test_run_ori_match_pipeline_rejects_deep_only_flags(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work_ori"
            work_dir.mkdir()
            original_list = work_dir / "original_images.lis"
            original_list.write_text("left.cub\nright.cub\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text('{"NetworkId":"n","TargetName":"Mars","UserName":"u"}\n', encoding="utf-8")

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
                    "--deep-match-config-path",
                    "examples/controlnet_construct/presets/loftr_default.json",
                    "--dry-run",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("is not supported by the raw image space wrapper first version", result.stderr)
```

- [ ] **Step 2: Run validation tests and verify expected failure**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest \
  tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_ori_match_pipeline_rejects_invalid_pair_id_start \
  tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_ori_match_pipeline_rejects_deep_only_flags \
  -v
```

Expected before tightening: at least one failure if Task 1 skeleton has drifted from the desired validation behavior.

- [ ] **Step 3: Ensure wrapper validation matches tests**

In `run_ori_match_pipeline_example.sh`, keep these exact parsing branches:

```bash
    --deep-match-config-path|--deep-match-mode|--adaptive-routing|--no-adaptive-routing)
      die "$1 is not supported by the raw image space wrapper first version"
      ;;
```

Keep this exact pair-id validation after parsing:

```bash
case "$PAIR_ID_START" in
  ''|*[!0-9]*) die "--pair-id-start must be a positive integer" ;;
esac
if [[ "$PAIR_ID_START" -lt 1 ]]; then
  die "--pair-id-start must be at least 1"
fi
```

- [ ] **Step 4: Run validation tests and verify pass**

Run the same command from Step 2.

Expected: `OK`.

- [ ] **Step 5: Commit Task 2**

```bash
git add examples/controlnet_construct/run_ori_match_pipeline_example.sh tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "test: validate raw image pipeline arguments"
```

## Task 3: Implement Execution Mode and Batch Summary

**Files:**
- Modify: `examples/controlnet_construct/run_ori_match_pipeline_example.sh`
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [ ] **Step 1: Add a fake-python execution test**

Add this method to `ControlNetConstructPipelineUnitTest`:

```python
    def test_run_ori_match_pipeline_executes_fake_pipeline_and_writes_summary(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work_ori"
            work_dir.mkdir()
            inputs_dir = temp_dir / "inputs"
            inputs_dir.mkdir()
            left = inputs_dir / "left.cub"
            right = inputs_dir / "right.cub"
            left.write_text("left placeholder\n", encoding="utf-8")
            right.write_text("right placeholder\n", encoding="utf-8")
            original_list = work_dir / "original_images.lis"
            original_list.write_text(f"{left}\n{right}\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                '{"NetworkId":"raw_image_matching","TargetName":"Mars","UserName":"unit"}\n',
                encoding="utf-8",
            )
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python_dispatcher.write_text(
                textwrap.dedent(
                    r'''
                    from __future__ import annotations

                    import json
                    from pathlib import Path
                    import sys

                    script = Path(sys.argv[1])
                    args = sys.argv[2:]

                    if script.name == "image_overlap.py":
                        input_list = Path(args[0])
                        output_list = Path(args[1])
                        report_path = Path(args[args.index("--report-json") + 1])
                        images = [line.strip() for line in input_list.read_text(encoding="utf-8").splitlines() if line.strip()]
                        output_list.write_text(f"{images[0]},{images[1]}\n", encoding="utf-8")
                        report_path.parent.mkdir(parents=True, exist_ok=True)
                        report_path.write_text(json.dumps({"pair_count": 1, "image_count": 2}) + "\n", encoding="utf-8")
                        raise SystemExit(0)

                    if script.name == "controlnet_stereopair.py" and args[0] == "from-ori-match":
                        output_net = Path(args[4])
                        left_key = Path(args[args.index("--left-output-key") + 1])
                        right_key = Path(args[args.index("--right-output-key") + 1])
                        report_path = Path(args[args.index("--report-path") + 1])
                        for path in (output_net, left_key, right_key, report_path):
                            path.parent.mkdir(parents=True, exist_ok=True)
                        output_net.write_text("pair net\n", encoding="utf-8")
                        left_key.write_text("left key\n", encoding="utf-8")
                        right_key.write_text("right key\n", encoding="utf-8")
                        report_path.write_text(json.dumps({"mode": "from-ori-match", "controlnet": {"point_count": 3}}) + "\n", encoding="utf-8")
                        raise SystemExit(0)

                    if script.name == "controlnet_merge.py":
                        pair_net_dir = Path(args[1])
                        script_path = Path(args[3])
                        pair_list = Path(args[args.index("--pair-list") + 1])
                        report_path = Path(args[args.index("--report-json") + 1])
                        output_net = Path(args[2])
                        script_path.parent.mkdir(parents=True, exist_ok=True)
                        pair_list.write_text("\n".join(str(path) for path in pair_net_dir.glob("*.net")) + "\n", encoding="utf-8")
                        script_path.write_text("#!/usr/bin/env bash\nset -euo pipefail\nprintf merged > " + str(output_net) + "\n", encoding="utf-8")
                        script_path.chmod(0o755)
                        report_path.write_text(json.dumps({"included_count": 1, "output_net": str(output_net)}) + "\n", encoding="utf-8")
                        raise SystemExit(0)

                    raise SystemExit(f"unexpected command: {sys.argv}")
                    '''
                ),
                encoding="utf-8",
            )
            fake_python = temp_dir / "fake_python"
            fake_python.write_text(
                "#!/usr/bin/env bash\n"
                f"exec {sys.executable!s} {fake_python_dispatcher!s} \"$@\"\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)

            env = {**os.environ, "PYTHON_EXECUTABLE": str(fake_python)}
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
                    "--skip-final-merge",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            summary_path = work_dir / "reports" / "ori_match_batch_summary.json"
            self.assertTrue(summary_path.exists())
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["mode"], "from-ori-match-batch-wrapper")
        self.assertEqual(summary["pair_count"], 1)
        self.assertEqual(summary["pairs"][0]["pair_id"], "S1")
        self.assertEqual(summary["pairs"][0]["pair"], f"{left},{right}")
        self.assertTrue(summary["pairs"][0]["output_net"].endswith("ori_pair_nets/left__right.net"))
        self.assertTrue(summary["merge_script_path"].endswith("merge/merge_all_controlnets.sh"))
        self.assertIn("raw image pair matching complete", result.stdout)
```

- [ ] **Step 2: Run execution test and verify it fails**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_ori_match_pipeline_executes_fake_pipeline_and_writes_summary -v
```

Expected: failure because Task 1 skeleton exits with `execution mode is not implemented yet`.

- [ ] **Step 3: Implement command execution helpers**

In `run_ori_match_pipeline_example.sh`, add:

```bash
run_command() {
  log "$1"
  shift
  append_command "$@"
  "$@"
}
```

Replace the initial overlap `append_command` with:

```bash
run_command "stage 1: discovering overlap pairs" "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_overlap.py" \
  "$ORIGINAL_LIST" "$IMAGES_OVERLAP_LIST" --report-json "$OVERLAP_REPORT_PATH"
```

For dry-run mode, keep command generation without execution by guarding execution paths:

```bash
if [[ "$DRY_RUN" == "1" ]]; then
  append_command "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_overlap.py" \
    "$ORIGINAL_LIST" "$IMAGES_OVERLAP_LIST" --report-json "$OVERLAP_REPORT_PATH"
else
  run_command "stage 1: discovering overlap pairs" "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/image_overlap.py" \
    "$ORIGINAL_LIST" "$IMAGES_OVERLAP_LIST" --report-json "$OVERLAP_REPORT_PATH"
fi
```

- [ ] **Step 4: Implement pair execution and summary writing**

Replace the current final `die "execution mode is not implemented yet"` block with logic that:

```bash
if [[ ! -s "$IMAGES_OVERLAP_LIST" ]]; then
  die "images overlap list is empty: $IMAGES_OVERLAP_LIST"
fi

pairs_json="$REPORTS_DIR/.ori_match_pairs.jsonl"
: > "$pairs_json"
pair_index=0
while IFS=, read -r left right; do
  [[ -n "$left" ]] || continue
  [[ -n "$right" ]] || die "invalid overlap pair line missing right-hand entry"
  pair_index=$((pair_index + 1))
  pair_id="${PAIR_ID_PREFIX}$((PAIR_ID_START + pair_index - 1))"
  pair_tag=$(pair_tag_from_paths "$left" "$right")
  left_key="$ORI_KEYS_DIR/${pair_tag}_A.key"
  right_key="$ORI_KEYS_DIR/${pair_tag}_B.key"
  pair_net="$PAIR_NETS_DIR/${pair_tag}.net"
  pair_report="$REPORTS_DIR/${pair_tag}.summary.json"
  match_args=(
    "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/controlnet_stereopair.py" from-ori-match
    "$left" "$right" "$CONFIG_PATH" "$pair_net"
    --pair-id "$pair_id"
    --left-output-key "$left_key"
    --right-output-key "$right_key"
    --report-path "$pair_report"
    --matcher-method "$MATCHER_METHOD"
    --band "$BAND"
    --ratio-test "$RATIO_TEST"
    --num-worker-parallel-cpu "$NUM_WORKER_PARALLEL_CPU"
    --gpu-batch-size "$GPU_BATCH_SIZE"
    --gpu-min-batch-size "$GPU_MIN_BATCH_SIZE"
    --gpu-max-batch-size "$GPU_MAX_BATCH_SIZE"
    --log-level "$LOG_LEVEL"
  )
  [[ -z "$MAX_FEATURES" ]] || match_args+=(--max-features "$MAX_FEATURES")
  [[ "$USE_PARALLEL_CPU" == "1" ]] && match_args+=(--use-parallel-cpu) || match_args+=(--no-parallel-cpu)
  [[ "$USE_GPU" == "1" ]] && match_args+=(--use-gpu)
  [[ "$GPU_DYNAMIC_BATCH" == "1" ]] && match_args+=(--gpu-dynamic-batch) || match_args+=(--no-gpu-dynamic-batch)
  run_command "stage 2: matching pair $pair_tag" "${match_args[@]}"
  "$PYTHON_EXECUTABLE" - "$pairs_json" "$left,$right" "$pair_id" "$pair_net" "$left_key" "$right_key" "$pair_report" <<'PY'
import json
import sys
from pathlib import Path

jsonl, pair, pair_id, output_net, left_key, right_key, report_path = sys.argv[1:]
record = {
    "pair": pair,
    "pair_id": pair_id,
    "output_net": output_net,
    "left_key": left_key,
    "right_key": right_key,
    "report_path": report_path,
    "status": "success",
}
with Path(jsonl).open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(record, ensure_ascii=False) + "\n")
PY
done < "$IMAGES_OVERLAP_LIST"
```

Then run merge and write summary:

```bash
run_command "stage 3: generating merge script" "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/controlnet_merge.py" \
  "$IMAGES_OVERLAP_LIST" "$PAIR_NETS_DIR" "$MERGE_OUTPUT_NET" "$MERGE_SCRIPT_PATH" \
  --network-id "raw_image_matching" \
  --description "Merged raw image matching ControlNet" \
  --pair-list "$MERGE_PAIR_LIST_PATH" \
  --report-json "$MERGE_REPORT_PATH"

if [[ "$SKIP_FINAL_MERGE" != "1" ]]; then
  run_command "stage 4: executing merge script" bash "$MERGE_SCRIPT_PATH"
fi

"$PYTHON_EXECUTABLE" - "$BATCH_REPORT_PATH" "$pairs_json" "$ORIGINAL_LIST" "$IMAGES_OVERLAP_LIST" "$PAIR_NETS_DIR" "$REPORTS_DIR" "$MERGE_OUTPUT_NET" "$MERGE_SCRIPT_PATH" "$PAIR_ID_PREFIX" "$PAIR_ID_START" "$MATCHER_METHOD" <<'PY'
import json
import sys
from pathlib import Path

(
    report_path,
    pairs_json,
    original_list,
    overlap_list,
    pair_nets_dir,
    reports_dir,
    merge_output_net,
    merge_script_path,
    pair_id_prefix,
    pair_id_start,
    matcher_method,
) = sys.argv[1:]
pairs = [
    json.loads(line)
    for line in Path(pairs_json).read_text(encoding="utf-8").splitlines()
    if line.strip()
]
payload = {
    "mode": "from-ori-match-batch-wrapper",
    "original_list": original_list,
    "images_overlap_list": overlap_list,
    "pair_count": len(pairs),
    "pair_id_prefix": pair_id_prefix,
    "pair_id_start": int(pair_id_start),
    "matcher_method": matcher_method,
    "pair_net_directory": pair_nets_dir,
    "report_directory": reports_dir,
    "merge_output_net": merge_output_net,
    "merge_script_path": merge_script_path,
    "pairs": pairs,
}
Path(report_path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
log "raw image pair matching complete: $BATCH_REPORT_PATH"
```

- [ ] **Step 5: Re-run execution test**

Run the command from Step 2.

Expected: `OK`.

- [ ] **Step 6: Re-run dry-run and validation tests**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest \
  tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_ori_match_pipeline_dry_run_writes_expected_commands \
  tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_ori_match_pipeline_rejects_invalid_pair_id_start \
  tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_ori_match_pipeline_rejects_deep_only_flags \
  tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_ori_match_pipeline_executes_fake_pipeline_and_writes_summary \
  -v
```

Expected: `OK`.

- [ ] **Step 7: Commit Task 3**

```bash
git add examples/controlnet_construct/run_ori_match_pipeline_example.sh tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: add raw image controlnet wrapper execution"
```

## Task 4: Document the Raw Image Pipeline Entry Point

**Files:**
- Modify: `examples/controlnet_construct/usage.md`

- [ ] **Step 1: Add documentation section**

Append this section near the existing end-to-end pipeline instructions in `examples/controlnet_construct/usage.md`:

````markdown
## 原始影像空间匹配流水线

如果你想跳过 DOM 匹配和 `dom2ori` 回投，可以使用独立的原始影像空间 wrapper：

```bash
bash examples/controlnet_construct/run_ori_match_pipeline_example.sh \
  --work-dir work_ori \
  --original-list work_ori/original_images.lis \
  --config examples/controlnet_construct/controlnet_config.example.json \
  --matcher-method flann \
  --num-worker-parallel-cpu 8
```

这条路径会复用：

- `image_overlap.py` 生成候选像对；
- `controlnet_stereopair.py from-ori-match` 对每个 pair 直接在原始 cube 上匹配并构建 pairwise ControlNet；
- `controlnet_merge.py` 生成并默认执行最终 merge 脚本。

默认输出位于：

- `work_ori/images_overlap.lis`
- `work_ori/ori_keys/*.key`
- `work_ori/ori_pair_nets/*.net`
- `work_ori/reports/ori_match_batch_summary.json`
- `work_ori/merge/merge_all_controlnets.sh`
- `work_ori/merge/ori_matching_merged.net`

第一版不接入 deep matcher、adaptive routing、DOM low-resolution offset 或 DOM-space RANSAC 可视化。需要这些能力时继续使用 DOM pipeline，或者后续再按小步方式扩展这个 wrapper。
````

- [ ] **Step 2: Check markdown context**

Run:

```bash
rg -n "原始影像空间匹配流水线|run_ori_match_pipeline_example|ori_match_batch_summary" examples/controlnet_construct/usage.md
```

Expected: all three strings appear.

- [ ] **Step 3: Commit Task 4**

```bash
git add examples/controlnet_construct/usage.md
git commit -m "docs: document raw image controlnet pipeline"
```

## Task 5: Final Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run targeted wrapper tests**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: `OK`.

- [ ] **Step 2: Run smoke import**

Run:

```bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tests/smoke_import.py
```

Expected: output ends with `smoke import ok`.

- [ ] **Step 3: Inspect worktree status**

Run:

```bash
git status --short --branch
```

Expected: only intended files are modified, or clean after commits.

- [ ] **Step 4: Commit verification notes if any plan checkboxes were updated**

If this plan file has checklist updates, commit them:

```bash
git add docs/superpowers/plans/2026-05-23-raw-image-space-controlnet.md
git commit -m "docs: track raw image controlnet implementation plan"
```

If no checklist changes were made during implementation, do not create an empty commit.
