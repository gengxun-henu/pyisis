# Matcher Comparison Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a wrapper-driven experiment runner that compares end-to-end ControlNet construction across SIFT+FLANN, official LightGlue feature frontends, and LoFTR, then writes reproducible metrics and reports.

**Architecture:** Add a small `examples/controlnet_construct/experiments/` package with a pure-Python core module and a thin CLI wrapper. The runner creates one isolated method work directory, copies the configured input lists into that method work directory, invokes existing pipeline wrappers, records command/log/metrics files, and aggregates final reports. Unit tests use fake commands and synthetic output files; they do not run real deep models.

**Tech Stack:** Python 3.12 standard library (`argparse`, `csv`, `dataclasses`, `json`, `subprocess`, `time`, `pathlib`), existing shell wrappers (`run_pipeline_example.sh`, `run_deep_match_pipeline.sh`), `unittest`.

---

## File Structure

- Create: `examples/controlnet_construct/experiments/__init__.py`
  - Marks the experiment runner as an importable package.
- Create: `examples/controlnet_construct/experiments/matcher_comparison.py`
  - Core dataclasses, config loading, workspace preparation, command generation, method execution, metrics collection, and report writing.
- Create: `examples/controlnet_construct/experiments/run_matcher_comparison.py`
  - CLI entry point that delegates to `matcher_comparison.main`.
- Create: `examples/controlnet_construct/experiments/matcher_comparison.example.json`
  - Default seven-method experiment config.
- Create: `examples/controlnet_construct/experiments/README.md`
  - User-facing instructions and output layout.
- Create: `tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py`
  - Unit tests for config parsing, command generation, dry-run, resume, execution failure handling, and report generation.

Important wrapper constraint: `examples/controlnet_construct/run_deep_match_pipeline.sh` does not accept `--original-list` or `--dom-list`. The experiment runner must copy configured `original_images_list` and `doms_list` into each method's `work/original_images.lis` and `work/doms_scaled.lis` before execution. This keeps deep methods compatible with existing wrapper defaults.

---

### Task 1: Package Skeleton, Config Model, and Example Config

**Files:**
- Create: `examples/controlnet_construct/experiments/__init__.py`
- Create: `examples/controlnet_construct/experiments/matcher_comparison.py`
- Create: `examples/controlnet_construct/experiments/matcher_comparison.example.json`
- Test: `tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py`

- [ ] **Step 1: Write failing config parsing tests**

Add this test file:

```python
"""Unit tests for the ControlNet matcher comparison experiment runner.

Author: Geng Xun
Created: 2026-05-22
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import unittest


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import temporary_directory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from controlnet_construct.experiments import matcher_comparison


def _write_minimal_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "run_id": "unit_run",
                "description": "unit test matcher comparison",
                "inputs": {
                    "original_images_list": "original_images.lis",
                    "doms_list": "doms_scaled.lis",
                    "controlnet_config": "examples/controlnet_construct/controlnet_config.example.json",
                },
                "execution": {
                    "asp360_env": "asp360_new",
                    "deep_learning_env": "deep-learning",
                    "device": "auto",
                    "skip_final_merge": True,
                    "keep_going": True,
                    "resume": True,
                },
                "methods": [
                    {"label": "sift_flann", "matcher_method": "flann"},
                    {
                        "label": "loftr",
                        "matcher_method": "loftr",
                        "deep_match_config_path": "examples/controlnet_construct/presets/loftr_default.json",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


class MatcherComparisonConfigUnitTest(unittest.TestCase):
    def test_load_experiment_config_expands_inputs_execution_and_methods(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)

            config = matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)

        self.assertEqual(config.run_id, "unit_run")
        self.assertEqual(config.execution.asp360_env, "asp360_new")
        self.assertEqual(config.execution.deep_learning_env, "deep-learning")
        self.assertTrue(config.execution.skip_final_merge)
        self.assertEqual(config.inputs.original_images_list, PROJECT_ROOT / "original_images.lis")
        self.assertEqual(config.inputs.doms_list, PROJECT_ROOT / "doms_scaled.lis")
        self.assertEqual(config.methods[0].label, "sift_flann")
        self.assertFalse(config.methods[0].is_deep_method)
        self.assertEqual(config.methods[1].deep_match_config_path, PROJECT_ROOT / "examples/controlnet_construct/presets/loftr_default.json")
        self.assertTrue(config.methods[1].is_deep_method)

    def test_load_experiment_config_rejects_duplicate_method_labels(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["methods"].append({"label": "sift_flann", "matcher_method": "flann"})
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Duplicate method label"):
                matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)

    def test_load_experiment_config_rejects_deep_method_without_preset(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["methods"] = [{"label": "bad_lightglue", "matcher_method": "lightglue"}]
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "requires deep_match_config_path"):
                matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new test and verify it fails**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: FAIL with `ModuleNotFoundError` or missing `load_experiment_config`.

- [ ] **Step 3: Add the package and config implementation**

Create `examples/controlnet_construct/experiments/__init__.py`:

```python
"""Experiment runners for ControlNet construction workflows."""
```

Create the initial `examples/controlnet_construct/experiments/matcher_comparison.py`:

```python
"""Wrapper-driven matcher comparison experiment runner.

Author: Geng Xun
Created: 2026-05-22
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


DEEP_MATCHER_METHODS = {"lightglue", "loftr", "superglue"}


@dataclass(frozen=True)
class ExperimentInputs:
    original_images_list: Path
    doms_list: Path
    controlnet_config: Path


@dataclass(frozen=True)
class ExecutionConfig:
    asp360_env: str = "asp360_new"
    deep_learning_env: str = "deep-learning"
    device: str = "auto"
    skip_final_merge: bool = False
    keep_going: bool = True
    resume: bool = True


@dataclass(frozen=True)
class MethodConfig:
    label: str
    matcher_method: str
    deep_match_config_path: Path | None = None

    @property
    def is_deep_method(self) -> bool:
        return self.matcher_method.strip().lower() in DEEP_MATCHER_METHODS


@dataclass(frozen=True)
class ExperimentConfig:
    run_id: str
    description: str
    inputs: ExperimentInputs
    execution: ExecutionConfig
    methods: tuple[MethodConfig, ...]
    config_path: Path


def _resolve_path(value: str | Path, *, base_dir: Path, repo_root: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    config_relative = (base_dir / path).resolve()
    if config_relative.exists():
        return config_relative
    return (repo_root / path).resolve()


def _require_mapping(payload: Any, key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Experiment config field '{key}' must be an object.")
    return value


def load_experiment_config(config_path: str | Path, *, repo_root: str | Path | None = None) -> ExperimentConfig:
    resolved_config_path = Path(config_path).expanduser().resolve()
    resolved_repo_root = Path(repo_root).expanduser().resolve() if repo_root is not None else resolved_config_path.parents[3]
    payload = json.loads(resolved_config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Experiment config must be a JSON object.")

    run_id = str(payload.get("run_id", "")).strip()
    if not run_id:
        raise ValueError("Experiment config requires a non-empty run_id.")

    inputs_payload = _require_mapping(payload, "inputs")
    execution_payload = payload.get("execution", {})
    if execution_payload is None:
        execution_payload = {}
    if not isinstance(execution_payload, dict):
        raise ValueError("Experiment config field 'execution' must be an object.")

    inputs = ExperimentInputs(
        original_images_list=_resolve_path(
            inputs_payload["original_images_list"],
            base_dir=resolved_config_path.parent,
            repo_root=resolved_repo_root,
        ),
        doms_list=_resolve_path(
            inputs_payload["doms_list"],
            base_dir=resolved_config_path.parent,
            repo_root=resolved_repo_root,
        ),
        controlnet_config=_resolve_path(
            inputs_payload["controlnet_config"],
            base_dir=resolved_config_path.parent,
            repo_root=resolved_repo_root,
        ),
    )

    execution = ExecutionConfig(
        asp360_env=str(execution_payload.get("asp360_env", "asp360_new")),
        deep_learning_env=str(execution_payload.get("deep_learning_env", "deep-learning")),
        device=str(execution_payload.get("device", "auto")),
        skip_final_merge=bool(execution_payload.get("skip_final_merge", False)),
        keep_going=bool(execution_payload.get("keep_going", True)),
        resume=bool(execution_payload.get("resume", True)),
    )

    methods_payload = payload.get("methods")
    if not isinstance(methods_payload, list) or not methods_payload:
        raise ValueError("Experiment config requires a non-empty methods array.")

    labels: set[str] = set()
    methods: list[MethodConfig] = []
    for entry in methods_payload:
        if not isinstance(entry, dict):
            raise ValueError("Each method entry must be an object.")
        label = str(entry.get("label", "")).strip()
        matcher_method = str(entry.get("matcher_method", "")).strip().lower()
        if not label:
            raise ValueError("Each method requires a non-empty label.")
        if label in labels:
            raise ValueError(f"Duplicate method label: {label}")
        if not matcher_method:
            raise ValueError(f"Method '{label}' requires matcher_method.")
        deep_path = entry.get("deep_match_config_path")
        method = MethodConfig(
            label=label,
            matcher_method=matcher_method,
            deep_match_config_path=None
            if deep_path in (None, "")
            else _resolve_path(deep_path, base_dir=resolved_config_path.parent, repo_root=resolved_repo_root),
        )
        if method.is_deep_method and method.deep_match_config_path is None:
            raise ValueError(f"Method '{label}' requires deep_match_config_path for matcher_method '{matcher_method}'.")
        labels.add(label)
        methods.append(method)

    return ExperimentConfig(
        run_id=run_id,
        description=str(payload.get("description", "")),
        inputs=inputs,
        execution=execution,
        methods=tuple(methods),
        config_path=resolved_config_path,
    )
```

- [ ] **Step 4: Add the example config**

Create `examples/controlnet_construct/experiments/matcher_comparison.example.json`:

```json
{
  "run_id": "lro_batch_20260522",
  "description": "Matcher comparison for ControlNet construction",
  "inputs": {
    "original_images_list": "work/original_images.lis",
    "doms_list": "work/doms_scaled.lis",
    "controlnet_config": "examples/controlnet_construct/controlnet_config.example.json"
  },
  "execution": {
    "asp360_env": "asp360_new",
    "deep_learning_env": "deep-learning",
    "device": "auto",
    "skip_final_merge": false,
    "keep_going": true,
    "resume": true
  },
  "methods": [
    { "label": "sift_flann", "matcher_method": "flann" },
    {
      "label": "sift_lightglue",
      "matcher_method": "lightglue",
      "deep_match_config_path": "examples/controlnet_construct/presets/lightglue_official_sift.json"
    },
    {
      "label": "disk_lightglue",
      "matcher_method": "lightglue",
      "deep_match_config_path": "examples/controlnet_construct/presets/lightglue_official_disk.json"
    },
    {
      "label": "aliked_lightglue",
      "matcher_method": "lightglue",
      "deep_match_config_path": "examples/controlnet_construct/presets/lightglue_official_aliked.json"
    },
    {
      "label": "doghardnet_lightglue",
      "matcher_method": "lightglue",
      "deep_match_config_path": "examples/controlnet_construct/presets/lightglue_official_doghardnet.json"
    },
    {
      "label": "superpoint_lightglue",
      "matcher_method": "lightglue",
      "deep_match_config_path": "examples/controlnet_construct/presets/lightglue_official_superpoint.json"
    },
    {
      "label": "loftr",
      "matcher_method": "loftr",
      "deep_match_config_path": "examples/controlnet_construct/presets/loftr_default.json"
    }
  ]
}
```

- [ ] **Step 5: Run test and verify it passes**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: PASS for the three config tests.

- [ ] **Step 6: Commit Task 1**

Run:

```bash
git add examples/controlnet_construct/experiments/__init__.py \
  examples/controlnet_construct/experiments/matcher_comparison.py \
  examples/controlnet_construct/experiments/matcher_comparison.example.json \
  tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py
git commit -m "feat: add matcher comparison config model"
```

---

### Task 2: Workspace Preparation and Command Generation

**Files:**
- Modify: `examples/controlnet_construct/experiments/matcher_comparison.py`
- Modify: `tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py`

- [ ] **Step 1: Add tests for workspace preparation and command generation**

Append these tests to `MatcherComparisonConfigUnitTest`:

```python
    def test_prepare_method_workspace_copies_input_lists_to_wrapper_default_names(self):
        with temporary_directory() as temp_dir:
            source_original = temp_dir / "source_originals.lis"
            source_doms = temp_dir / "source_doms.lis"
            source_original.write_text("left.cub\nright.cub\n", encoding="utf-8")
            source_doms.write_text("left_dom.cub\nright_dom.cub\n", encoding="utf-8")
            method_dir = temp_dir / "method"

            matcher_comparison.prepare_method_workspace(
                method_dir,
                original_images_list=source_original,
                doms_list=source_doms,
            )

            self.assertEqual((method_dir / "work" / "original_images.lis").read_text(encoding="utf-8"), "left.cub\nright.cub\n")
            self.assertEqual((method_dir / "work" / "doms_scaled.lis").read_text(encoding="utf-8"), "left_dom.cub\nright_dom.cub\n")

    def test_build_method_command_uses_plain_pipeline_for_flann(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            config = matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)
            method = config.methods[0]
            method_dir = temp_dir / "methods" / method.label

            command = matcher_comparison.build_method_command(
                config,
                method,
                method_dir=method_dir,
                repo_root=PROJECT_ROOT,
            )

        command_text = " ".join(command)
        self.assertIn("run_pipeline_example.sh", command_text)
        self.assertIn("--work-dir", command)
        self.assertIn(str(method_dir / "work"), command)
        self.assertIn("--matcher-method", command)
        self.assertIn("flann", command)
        self.assertNotIn("run_deep_match_pipeline.sh", command_text)

    def test_build_method_command_uses_deep_pipeline_for_loftr(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            config = matcher_comparison.load_experiment_config(config_path, repo_root=PROJECT_ROOT)
            method = config.methods[1]
            method_dir = temp_dir / "methods" / method.label

            command = matcher_comparison.build_method_command(
                config,
                method,
                method_dir=method_dir,
                repo_root=PROJECT_ROOT,
            )

        command_text = " ".join(command)
        self.assertIn("run_deep_match_pipeline.sh", command_text)
        self.assertIn("--asp360-env", command)
        self.assertIn("asp360_new", command)
        self.assertIn("--deep-learning-env", command)
        self.assertIn("deep-learning", command)
        self.assertIn("--device", command)
        self.assertIn("auto", command)
        self.assertIn("--matcher-method", command)
        self.assertIn("loftr", command)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: FAIL with missing `prepare_method_workspace` or `build_method_command`.

- [ ] **Step 3: Implement workspace preparation and command generation**

Add these imports to `matcher_comparison.py`:

```python
import shutil
```

Add these functions:

```python
def prepare_method_workspace(
    method_dir: str | Path,
    *,
    original_images_list: str | Path,
    doms_list: str | Path,
) -> Path:
    resolved_method_dir = Path(method_dir).expanduser().resolve()
    work_dir = resolved_method_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(original_images_list).expanduser().resolve(), work_dir / "original_images.lis")
    shutil.copyfile(Path(doms_list).expanduser().resolve(), work_dir / "doms_scaled.lis")
    return work_dir


def build_method_command(
    config: ExperimentConfig,
    method: MethodConfig,
    *,
    method_dir: str | Path,
    repo_root: str | Path,
) -> list[str]:
    resolved_repo_root = Path(repo_root).expanduser().resolve()
    resolved_method_dir = Path(method_dir).expanduser().resolve()
    method_work_dir = resolved_method_dir / "work"
    if method.is_deep_method:
        command = [
            "bash",
            str(resolved_repo_root / "examples/controlnet_construct/run_deep_match_pipeline.sh"),
            "--work-dir",
            str(method_work_dir),
            "--config",
            str(config.inputs.controlnet_config),
            "--matcher-method",
            method.matcher_method,
            "--asp360-env",
            config.execution.asp360_env,
            "--deep-learning-env",
            config.execution.deep_learning_env,
            "--device",
            config.execution.device,
        ]
        if config.execution.skip_final_merge:
            command.append("--skip-final-merge")
        return command

    command = [
        "bash",
        str(resolved_repo_root / "examples/controlnet_construct/run_pipeline_example.sh"),
        "--work-dir",
        str(method_work_dir),
        "--config",
        str(config.inputs.controlnet_config),
        "--matcher-method",
        method.matcher_method,
    ]
    if config.execution.skip_final_merge:
        command.append("--skip-final-merge")
    return command
```

- [ ] **Step 4: Run test and verify it passes**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

Run:

```bash
git add examples/controlnet_construct/experiments/matcher_comparison.py \
  tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py
git commit -m "feat: generate matcher comparison commands"
```

---

### Task 3: Dry-Run Manifest, Resume, and CLI Entry Point

**Files:**
- Create: `examples/controlnet_construct/experiments/run_matcher_comparison.py`
- Modify: `examples/controlnet_construct/experiments/matcher_comparison.py`
- Modify: `tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py`

- [ ] **Step 1: Add tests for dry-run, only filtering, and resume**

Append this test class:

```python
class MatcherComparisonRunUnitTest(unittest.TestCase):
    def test_run_experiment_dry_run_writes_manifest_and_command_scripts(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            (temp_dir / "original_images.lis").write_text("left.cub\nright.cub\n", encoding="utf-8")
            (temp_dir / "doms_scaled.lis").write_text("left_dom.cub\nright_dom.cub\n", encoding="utf-8")
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["inputs"]["original_images_list"] = str(temp_dir / "original_images.lis")
            payload["inputs"]["doms_list"] = str(temp_dir / "doms_scaled.lis")
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            result = matcher_comparison.run_experiment(
                config_path,
                output_root=temp_dir / "out",
                repo_root=PROJECT_ROOT,
                dry_run=True,
                only_labels=None,
                resume=False,
                keep_going=True,
            )

            run_dir = temp_dir / "out" / "unit_run"
            self.assertEqual(result.run_dir, run_dir)
            self.assertTrue((run_dir / "experiment_manifest.json").is_file())
            self.assertTrue((run_dir / "methods" / "sift_flann" / "command.sh").is_file())
            self.assertTrue((run_dir / "methods" / "loftr" / "command.sh").is_file())
            self.assertFalse((run_dir / "methods" / "sift_flann" / "stdout.log").exists())

    def test_run_experiment_only_limits_methods(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            (temp_dir / "original_images.lis").write_text("left.cub\nright.cub\n", encoding="utf-8")
            (temp_dir / "doms_scaled.lis").write_text("left_dom.cub\nright_dom.cub\n", encoding="utf-8")
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["inputs"]["original_images_list"] = str(temp_dir / "original_images.lis")
            payload["inputs"]["doms_list"] = str(temp_dir / "doms_scaled.lis")
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            matcher_comparison.run_experiment(
                config_path,
                output_root=temp_dir / "out",
                repo_root=PROJECT_ROOT,
                dry_run=True,
                only_labels={"loftr"},
                resume=False,
                keep_going=True,
            )

            run_dir = temp_dir / "out" / "unit_run"
            self.assertFalse((run_dir / "methods" / "sift_flann").exists())
            self.assertTrue((run_dir / "methods" / "loftr" / "command.sh").is_file())

    def test_run_experiment_resume_skips_successful_metrics(self):
        with temporary_directory() as temp_dir:
            config_path = temp_dir / "experiment.json"
            _write_minimal_config(config_path)
            (temp_dir / "original_images.lis").write_text("left.cub\nright.cub\n", encoding="utf-8")
            (temp_dir / "doms_scaled.lis").write_text("left_dom.cub\nright_dom.cub\n", encoding="utf-8")
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["inputs"]["original_images_list"] = str(temp_dir / "original_images.lis")
            payload["inputs"]["doms_list"] = str(temp_dir / "doms_scaled.lis")
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            metrics_dir = temp_dir / "out" / "unit_run" / "methods" / "sift_flann"
            metrics_dir.mkdir(parents=True)
            (metrics_dir / "metrics.json").write_text('{"status": "success"}\n', encoding="utf-8")

            matcher_comparison.run_experiment(
                config_path,
                output_root=temp_dir / "out",
                repo_root=PROJECT_ROOT,
                dry_run=True,
                only_labels=None,
                resume=True,
                keep_going=True,
            )

            metrics = json.loads((metrics_dir / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["status"], "success")
            self.assertFalse((metrics_dir / "command.sh").exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: FAIL with missing `run_experiment`.

- [ ] **Step 3: Implement dry-run orchestration and CLI**

Add these imports to `matcher_comparison.py`:

```python
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import os
```

Add these dataclasses and helpers:

```python
@dataclass(frozen=True)
class ExperimentRunResult:
    run_dir: Path
    manifest_path: Path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _shell_quote_args(command: list[str]) -> str:
    import shlex

    return " ".join(shlex.quote(part) for part in command)


def _write_command_script(path: Path, command: list[str]) -> None:
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + _shell_quote_args(command) + "\n", encoding="utf-8")
    path.chmod(0o755)


def _existing_success(metrics_path: Path) -> bool:
    if not metrics_path.is_file():
        return False
    try:
        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return payload.get("status") == "success"


def _method_manifest_entry(method: MethodConfig, method_dir: Path, command: list[str], status: str) -> dict[str, Any]:
    return {
        "label": method.label,
        "matcher_method": method.matcher_method,
        "deep_match_config_path": None if method.deep_match_config_path is None else str(method.deep_match_config_path),
        "method_dir": str(method_dir),
        "work_dir": str(method_dir / "work"),
        "command": command,
        "status": status,
    }
```

Add `run_experiment`:

```python
def run_experiment(
    config_path: str | Path,
    *,
    output_root: str | Path,
    repo_root: str | Path | None = None,
    dry_run: bool = False,
    only_labels: set[str] | None = None,
    resume: bool | None = None,
    keep_going: bool | None = None,
) -> ExperimentRunResult:
    resolved_repo_root = Path(repo_root).expanduser().resolve() if repo_root is not None else Path.cwd().resolve()
    config = load_experiment_config(config_path, repo_root=resolved_repo_root)
    effective_resume = config.execution.resume if resume is None else resume
    effective_keep_going = config.execution.keep_going if keep_going is None else keep_going
    run_dir = Path(output_root).expanduser().resolve() / config.run_id
    methods_dir = run_dir / "methods"
    reports_dir = run_dir / "reports"
    methods_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    selected_methods = [method for method in config.methods if only_labels is None or method.label in only_labels]
    if only_labels is not None:
        missing = sorted(only_labels - {method.label for method in config.methods})
        if missing:
            raise ValueError(f"Unknown method label(s): {', '.join(missing)}")

    config_snapshot = json.loads(config.config_path.read_text(encoding="utf-8"))
    (run_dir / "experiment_config.json").write_text(
        json.dumps(config_snapshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    manifest_entries: list[dict[str, Any]] = []
    for method in selected_methods:
        method_dir = methods_dir / method.label
        metrics_path = method_dir / "metrics.json"
        if effective_resume and _existing_success(metrics_path):
            manifest_entries.append(_method_manifest_entry(method, method_dir, [], "skipped_success"))
            continue
        work_dir = prepare_method_workspace(
            method_dir,
            original_images_list=config.inputs.original_images_list,
            doms_list=config.inputs.doms_list,
        )
        command = build_method_command(config, method, method_dir=method_dir, repo_root=resolved_repo_root)
        _write_command_script(method_dir / "command.sh", command)
        manifest_entries.append(_method_manifest_entry(method, method_dir, command, "dry_run" if dry_run else "pending"))
        if not dry_run:
            raise NotImplementedError("Real execution is added in the execution task.")

    manifest_path = run_dir / "experiment_manifest.json"
    manifest_payload = {
        "run_id": config.run_id,
        "description": config.description,
        "created_at_utc": _utc_now_iso(),
        "dry_run": dry_run,
        "resume": effective_resume,
        "keep_going": effective_keep_going,
        "methods": manifest_entries,
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return ExperimentRunResult(run_dir=run_dir, manifest_path=manifest_path)
```

Add CLI helpers at the bottom of `matcher_comparison.py`:

```python
def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a ControlNet matcher comparison experiment.")
    parser.add_argument("config", help="Experiment JSON config path.")
    parser.add_argument("--output-root", default="work/matcher_comparison", help="Experiment output root.")
    parser.add_argument("--repo-root", default=None, help="Repository root. Defaults to current working directory.")
    parser.add_argument("--resume", action="store_true", default=None, help="Skip methods with successful metrics.")
    parser.add_argument("--no-resume", action="store_false", dest="resume", help="Do not skip successful methods.")
    parser.add_argument("--only", default="", help="Comma-separated method labels to run.")
    parser.add_argument("--dry-run", action="store_true", help="Write commands and manifest without executing wrappers.")
    parser.add_argument("--keep-going", action="store_true", default=None, help="Continue after method failures.")
    parser.add_argument("--fail-fast", action="store_false", dest="keep_going", help="Stop after first method failure.")
    return parser


def _parse_only(value: str) -> set[str] | None:
    labels = {part.strip() for part in value.split(",") if part.strip()}
    return labels or None


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    result = run_experiment(
        args.config,
        output_root=args.output_root,
        repo_root=args.repo_root,
        dry_run=args.dry_run,
        only_labels=_parse_only(args.only),
        resume=args.resume,
        keep_going=args.keep_going,
    )
    print(f"Experiment manifest: {result.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Create `examples/controlnet_construct/experiments/run_matcher_comparison.py`:

```python
#!/usr/bin/env python3
"""CLI wrapper for the ControlNet matcher comparison experiment."""

from __future__ import annotations

from pathlib import Path
import sys


def _bootstrap_examples_imports() -> None:
    examples_root = Path(__file__).resolve().parents[1]
    root_str = str(examples_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


_bootstrap_examples_imports()

from controlnet_construct.experiments.matcher_comparison import main


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

Run:

```bash
git add examples/controlnet_construct/experiments/matcher_comparison.py \
  examples/controlnet_construct/experiments/run_matcher_comparison.py \
  tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py
git commit -m "feat: add matcher comparison dry-run orchestration"
```

---

### Task 4: Real Method Execution and Failure Recording

**Files:**
- Modify: `examples/controlnet_construct/experiments/matcher_comparison.py`
- Modify: `tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py`

- [ ] **Step 1: Add execution tests with fake commands**

Append this test class:

```python
class MatcherComparisonExecutionUnitTest(unittest.TestCase):
    def test_execute_method_writes_success_metrics_and_logs(self):
        with temporary_directory() as temp_dir:
            method_dir = temp_dir / "method"
            method_dir.mkdir()
            command = [sys.executable, "-c", "print('hello from fake method')"]

            metrics = matcher_comparison.execute_method(
                label="fake_success",
                command=command,
                method_dir=method_dir,
            )

            self.assertEqual(metrics["status"], "success")
            self.assertEqual(metrics["return_code"], 0)
            self.assertGreaterEqual(metrics["total_wall_seconds"], 0.0)
            self.assertIn("hello from fake method", (method_dir / "stdout.log").read_text(encoding="utf-8"))
            self.assertEqual((method_dir / "stderr.log").read_text(encoding="utf-8"), "")
            self.assertEqual(json.loads((method_dir / "metrics.json").read_text(encoding="utf-8"))["status"], "success")

    def test_execute_method_writes_failed_metrics_and_logs(self):
        with temporary_directory() as temp_dir:
            method_dir = temp_dir / "method"
            method_dir.mkdir()
            command = [sys.executable, "-c", "import sys; print('bad', file=sys.stderr); raise SystemExit(7)"]

            metrics = matcher_comparison.execute_method(
                label="fake_failure",
                command=command,
                method_dir=method_dir,
            )

            self.assertEqual(metrics["status"], "failed")
            self.assertEqual(metrics["return_code"], 7)
            self.assertIn("bad", (method_dir / "stderr.log").read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: FAIL with missing `execute_method`.

- [ ] **Step 3: Implement method execution**

Add these imports:

```python
import subprocess
import time
```

Add this function:

```python
def execute_method(*, label: str, command: list[str], method_dir: str | Path) -> dict[str, Any]:
    resolved_method_dir = Path(method_dir).expanduser().resolve()
    stdout_path = resolved_method_dir / "stdout.log"
    stderr_path = resolved_method_dir / "stderr.log"
    metrics_path = resolved_method_dir / "metrics.json"
    started_at = _utc_now_iso()
    start = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )
    total_wall_seconds = time.monotonic() - start
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    metrics = {
        "label": label,
        "status": "success" if completed.returncode == 0 else "failed",
        "return_code": completed.returncode,
        "started_at_utc": started_at,
        "finished_at_utc": _utc_now_iso(),
        "total_wall_seconds": total_wall_seconds,
        "command": command,
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
    }
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return metrics
```

Update `run_experiment` by replacing:

```python
        if not dry_run:
            raise NotImplementedError("Real execution is added in the execution task.")
```

with:

```python
        if not dry_run:
            metrics = execute_method(label=method.label, command=command, method_dir=method_dir)
            manifest_entries[-1]["status"] = metrics["status"]
            if metrics["status"] != "success" and not effective_keep_going:
                break
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

Run:

```bash
git add examples/controlnet_construct/experiments/matcher_comparison.py \
  tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py
git commit -m "feat: execute matcher comparison methods"
```

---

### Task 5: Metrics Collection from Pipeline Outputs

**Files:**
- Modify: `examples/controlnet_construct/experiments/matcher_comparison.py`
- Modify: `tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py`

- [ ] **Step 1: Add tests for collecting metrics from synthetic work outputs**

Append this test class:

```python
class MatcherComparisonMetricsUnitTest(unittest.TestCase):
    def test_collect_method_metrics_reads_pipeline_outputs_defensively(self):
        with temporary_directory() as temp_dir:
            method_dir = temp_dir / "method"
            reports_dir = method_dir / "work" / "reports"
            pair_nets_dir = method_dir / "work" / "pair_nets"
            merge_dir = method_dir / "work" / "merge"
            reports_dir.mkdir(parents=True)
            pair_nets_dir.mkdir(parents=True)
            merge_dir.mkdir(parents=True)
            (reports_dir / "image_overlap_summary.json").write_text('{"pair_count": 2}\n', encoding="utf-8")
            (reports_dir / "controlnet_batch_summary.json").write_text(
                json.dumps(
                    {
                        "pair_count": 2,
                        "total_final_control_point_count": 15,
                        "total_dom2ori_retained_count": 12,
                    }
                ),
                encoding="utf-8",
            )
            (reports_dir / "pipeline_timing.json").write_text(
                json.dumps({"total_seconds": 44.5, "steps": [{"label": "image-match", "seconds": 10.0}]}),
                encoding="utf-8",
            )
            (pair_nets_dir / "S1.net").write_text("net-one\n", encoding="utf-8")
            (pair_nets_dir / "S2.net").write_text("net-two\n", encoding="utf-8")
            (merge_dir / "dom_matching_merged.net").write_text("merged\n", encoding="utf-8")

            metrics = matcher_comparison.collect_method_metrics("sift_flann", method_dir)

        self.assertEqual(metrics["label"], "sift_flann")
        self.assertEqual(metrics["pair_count"], 2)
        self.assertEqual(metrics["pairwise_controlnet_count"], 2)
        self.assertTrue(metrics["merged_controlnet_exists"])
        self.assertEqual(metrics["total_final_control_point_count"], 15)
        self.assertEqual(metrics["total_dom2ori_retained_count"], 12)
        self.assertEqual(metrics["pipeline_total_seconds"], 44.5)

    def test_collect_method_metrics_tolerates_missing_optional_outputs(self):
        with temporary_directory() as temp_dir:
            method_dir = temp_dir / "method"
            (method_dir / "work").mkdir(parents=True)

            metrics = matcher_comparison.collect_method_metrics("empty", method_dir)

        self.assertEqual(metrics["label"], "empty")
        self.assertIsNone(metrics["pair_count"])
        self.assertEqual(metrics["pairwise_controlnet_count"], 0)
        self.assertFalse(metrics["merged_controlnet_exists"])
        self.assertTrue(metrics["warnings"])
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: FAIL with missing `collect_method_metrics`.

- [ ] **Step 3: Implement defensive metrics collection**

Add helpers:

```python
def _read_json_if_present(path: Path, warnings: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        warnings.append(f"missing: {path}")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        warnings.append(f"could not parse {path}: {exc}")
        return None
    if not isinstance(payload, dict):
        warnings.append(f"not an object: {path}")
        return None
    return payload


def collect_method_metrics(label: str, method_dir: str | Path) -> dict[str, Any]:
    resolved_method_dir = Path(method_dir).expanduser().resolve()
    work_dir = resolved_method_dir / "work"
    reports_dir = work_dir / "reports"
    pair_nets_dir = work_dir / "pair_nets"
    merge_dir = work_dir / "merge"
    warnings: list[str] = []

    overlap = _read_json_if_present(reports_dir / "image_overlap_summary.json", warnings)
    controlnet_batch = _read_json_if_present(reports_dir / "controlnet_batch_summary.json", warnings)
    timing = _read_json_if_present(reports_dir / "pipeline_timing.json", warnings)
    pair_net_paths = sorted(pair_nets_dir.glob("*.net")) if pair_nets_dir.is_dir() else []
    merged_net = merge_dir / "dom_matching_merged.net"

    metrics = {
        "label": label,
        "pair_count": None if overlap is None else overlap.get("pair_count", overlap.get("overlap_pair_count")),
        "pairwise_controlnet_count": len(pair_net_paths),
        "merged_controlnet_exists": merged_net.is_file(),
        "merged_controlnet_path": str(merged_net) if merged_net.is_file() else None,
        "pipeline_total_seconds": None if timing is None else timing.get("total_seconds"),
        "total_final_control_point_count": None if controlnet_batch is None else controlnet_batch.get("total_final_control_point_count"),
        "total_dom2ori_retained_count": None if controlnet_batch is None else controlnet_batch.get("total_dom2ori_retained_count"),
        "warnings": warnings,
    }
    return metrics
```

Update `execute_method` after subprocess completion:

```python
    output_metrics = collect_method_metrics(label, resolved_method_dir)
    metrics.update(output_metrics)
```

Keep `status`, `return_code`, and log fields from execution metrics if keys overlap.

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

Run:

```bash
git add examples/controlnet_construct/experiments/matcher_comparison.py \
  tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py
git commit -m "feat: collect matcher comparison metrics"
```

---

### Task 6: Summary JSON, CSV, Markdown, and Failures Report

**Files:**
- Modify: `examples/controlnet_construct/experiments/matcher_comparison.py`
- Modify: `tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py`

- [ ] **Step 1: Add report writer tests**

Append this test class:

```python
class MatcherComparisonReportUnitTest(unittest.TestCase):
    def test_write_reports_creates_json_csv_markdown_and_failures(self):
        with temporary_directory() as temp_dir:
            reports_dir = temp_dir / "reports"
            metrics = [
                {
                    "label": "sift_flann",
                    "status": "success",
                    "return_code": 0,
                    "total_wall_seconds": 12.5,
                    "pair_count": 2,
                    "pairwise_controlnet_count": 2,
                    "merged_controlnet_exists": True,
                    "total_final_control_point_count": 20,
                    "total_dom2ori_retained_count": 18,
                    "stdout_log": "stdout.log",
                    "stderr_log": "stderr.log",
                },
                {
                    "label": "loftr",
                    "status": "failed",
                    "return_code": 3,
                    "total_wall_seconds": 4.0,
                    "pair_count": None,
                    "pairwise_controlnet_count": 0,
                    "merged_controlnet_exists": False,
                    "total_final_control_point_count": None,
                    "total_dom2ori_retained_count": None,
                    "stdout_log": "loftr.stdout.log",
                    "stderr_log": "loftr.stderr.log",
                },
            ]

            matcher_comparison.write_reports(reports_dir, run_id="unit_run", metrics=metrics)

            self.assertTrue((reports_dir / "summary.json").is_file())
            self.assertTrue((reports_dir / "summary.csv").is_file())
            self.assertTrue((reports_dir / "summary.md").is_file())
            self.assertTrue((reports_dir / "failures.json").is_file())
            self.assertIn("sift_flann", (reports_dir / "summary.csv").read_text(encoding="utf-8"))
            self.assertIn("| sift_flann | success |", (reports_dir / "summary.md").read_text(encoding="utf-8"))
            failures = json.loads((reports_dir / "failures.json").read_text(encoding="utf-8"))
            self.assertEqual(failures["failures"][0]["label"], "loftr")
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: FAIL with missing `write_reports`.

- [ ] **Step 3: Implement report writers**

Add imports:

```python
import csv
```

Add functions:

```python
REPORT_COLUMNS = (
    "label",
    "status",
    "return_code",
    "total_wall_seconds",
    "pair_count",
    "pairwise_controlnet_count",
    "merged_controlnet_exists",
    "total_final_control_point_count",
    "total_dom2ori_retained_count",
    "stdout_log",
    "stderr_log",
)


def write_reports(reports_dir: str | Path, *, run_id: str, metrics: list[dict[str, Any]]) -> None:
    resolved_reports_dir = Path(reports_dir).expanduser().resolve()
    resolved_reports_dir.mkdir(parents=True, exist_ok=True)
    summary_payload = {"run_id": run_id, "methods": metrics}
    (resolved_reports_dir / "summary.json").write_text(
        json.dumps(summary_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with (resolved_reports_dir / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REPORT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in metrics:
            writer.writerow(row)

    lines = [
        f"# Matcher Comparison Summary: {run_id}",
        "",
        "| Method | Status | Return Code | Wall Seconds | Pairs | Pair Nets | Merged Net | Control Points | Retained DOM2ORI |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for row in metrics:
        lines.append(
            "| {label} | {status} | {return_code} | {total_wall_seconds} | {pair_count} | {pairwise_controlnet_count} | {merged_controlnet_exists} | {total_final_control_point_count} | {total_dom2ori_retained_count} |".format(
                label=row.get("label", ""),
                status=row.get("status", ""),
                return_code=row.get("return_code", ""),
                total_wall_seconds=row.get("total_wall_seconds", ""),
                pair_count=row.get("pair_count", ""),
                pairwise_controlnet_count=row.get("pairwise_controlnet_count", ""),
                merged_controlnet_exists=row.get("merged_controlnet_exists", ""),
                total_final_control_point_count=row.get("total_final_control_point_count", ""),
                total_dom2ori_retained_count=row.get("total_dom2ori_retained_count", ""),
            )
        )
    lines.append("")
    lines.append("## Failures")
    failures = [row for row in metrics if row.get("status") not in ("success", "skipped")]
    if failures:
        for row in failures:
            lines.append(f"- `{row.get('label')}` failed with return code `{row.get('return_code')}`. See `{row.get('stderr_log')}`.")
    else:
        lines.append("- None.")
    (resolved_reports_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    (resolved_reports_dir / "failures.json").write_text(
        json.dumps({"run_id": run_id, "failures": failures}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
```

Update `run_experiment` to collect metrics and call `write_reports`:

```python
    collected_metrics: list[dict[str, Any]] = []
```

Inside the method loop:

```python
        if effective_resume and _existing_success(metrics_path):
            existing_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            collected_metrics.append(existing_metrics)
            manifest_entries.append(_method_manifest_entry(method, method_dir, [], "skipped_success"))
            continue
```

After executing a real method:

```python
            collected_metrics.append(metrics)
```

For dry-run, do not append synthetic metrics. After writing the manifest:

```python
    if collected_metrics:
        write_reports(reports_dir, run_id=config.run_id, metrics=collected_metrics)
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 6**

Run:

```bash
git add examples/controlnet_construct/experiments/matcher_comparison.py \
  tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py
git commit -m "feat: write matcher comparison reports"
```

---

### Task 7: README and CLI Smoke Validation

**Files:**
- Create: `examples/controlnet_construct/experiments/README.md`
- Modify: `tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py`

- [ ] **Step 1: Add README and CLI smoke tests**

Append this test class:

```python
class MatcherComparisonCliDocsUnitTest(unittest.TestCase):
    def test_cli_help_mentions_core_options(self):
        completed = matcher_comparison.subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "examples/controlnet_construct/experiments/run_matcher_comparison.py"),
                "--help",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("--output-root", completed.stdout)
        self.assertIn("--dry-run", completed.stdout)
        self.assertIn("--only", completed.stdout)

    def test_experiments_readme_documents_work_semantics_and_reports(self):
        readme_path = PROJECT_ROOT / "examples/controlnet_construct/experiments/README.md"
        content = readme_path.read_text(encoding="utf-8")
        self.assertIn("work/original_images.lis", content)
        self.assertIn("work/doms_scaled.lis", content)
        self.assertIn("summary.csv", content)
        self.assertIn("sift_flann", content)
        self.assertIn("loftr", content)
```

If using `matcher_comparison.subprocess.run` looks awkward, import `subprocess` at the top of the test file and call `subprocess.run`.

- [ ] **Step 2: Run tests and verify docs test fails**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: FAIL because `README.md` does not exist yet.

- [ ] **Step 3: Create README**

Create `examples/controlnet_construct/experiments/README.md`:

```markdown
# Matcher Comparison Experiments

This directory contains wrapper-driven experiments for comparing ControlNet construction methods without changing the core matching pipeline.

## Input Semantics

The experiment runner does not choose or sample stereo pairs. Prepare the same inputs you would use for the normal pipeline:

- `work/original_images.lis`
- `work/doms_scaled.lis` or another DOM list referenced by the experiment config
- a ControlNet config JSON such as `examples/controlnet_construct/controlnet_config.example.json`

If the prepared input lists produce three stereo pairs, every matcher runs three stereo pairs. To reduce runtime, edit the input lists before starting the experiment.

## Methods

The default config compares:

- `sift_flann`
- `sift_lightglue`
- `disk_lightglue`
- `aliked_lightglue`
- `doghardnet_lightglue`
- `superpoint_lightglue`
- `loftr`

## Dry Run

```bash
python examples/controlnet_construct/experiments/run_matcher_comparison.py \
  examples/controlnet_construct/experiments/matcher_comparison.example.json \
  --output-root work/matcher_comparison \
  --dry-run
```

Dry run writes the experiment manifest and per-method `command.sh` files without running the wrappers.

## Real Run

```bash
python examples/controlnet_construct/experiments/run_matcher_comparison.py \
  examples/controlnet_construct/experiments/matcher_comparison.example.json \
  --output-root work/matcher_comparison \
  --resume \
  --keep-going
```

Each method writes logs and metrics under:

```text
work/matcher_comparison/<run_id>/methods/<method_label>/
```

Reports are written under:

```text
work/matcher_comparison/<run_id>/reports/
```

The report files are:

- `summary.json`
- `summary.csv`
- `summary.md`
- `failures.json`
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 7**

Run:

```bash
git add examples/controlnet_construct/experiments/README.md \
  tests/unitTest/controlnet_construct_matcher_comparison_unit_test.py
git commit -m "docs: document matcher comparison experiments"
```

---

### Task 8: Final Verification

**Files:**
- No code changes expected unless verification finds a bug.

- [ ] **Step 1: Run focused matcher comparison tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matcher_comparison_unit_test -v
```

Expected: all tests pass.

- [ ] **Step 2: Run related wrapper regression tests**

Run:

```bash
python -m unittest tests.unitTest.deep_match_pipeline_smoke_unit_test tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: all tests pass.

- [ ] **Step 3: Run dry-run smoke command**

Run:

```bash
python examples/controlnet_construct/experiments/run_matcher_comparison.py \
  examples/controlnet_construct/experiments/matcher_comparison.example.json \
  --output-root /tmp/matcher_comparison_dry_run \
  --dry-run
```

Expected: exits 0 and prints an `Experiment manifest:` path.

- [ ] **Step 4: Inspect generated dry-run commands**

Run:

```bash
find /tmp/matcher_comparison_dry_run -name command.sh -maxdepth 5 -print | sort
```

Expected: seven `command.sh` files, one per method.

- [ ] **Step 5: Check worktree status**

Run:

```bash
git status --short --branch
```

Expected: clean worktree on `feat/experiment-matcher-comparison-20260522`.

