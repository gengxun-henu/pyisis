# Classic SIFT Match Presets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add preset-driven classic OpenCV SIFT matching so ControlNet users can select `classic_sift_flann.json` or `classic_sift_bf.json` with the same preset workflow used by learning matchers.

**Architecture:** Add a small neutral preset resolver in `examples/controlnet_construct/match_preset_config.py`. `image_match.py` consumes resolved preset defaults directly, while the shell wrappers use the same resolver only for path resolution, logging, and deep/classic routing decisions. Existing `matcher_method` and `deep_matcher_config_path` remain valid.

**Tech Stack:** Python 3.12 stdlib dataclasses/json/pathlib, existing `controlnet_construct.deep_match_config`, Bash wrappers, `unittest`.

---

## File Structure

- Create `examples/controlnet_construct/match_preset_config.py`
  - Owns neutral match preset loading, validation, path resolution, and shell assignment output.
  - Keeps classic SIFT validation separate from `deep_match_config.py`.
- Modify `examples/image_match/image_match.py`
  - Adds `match_preset_path` to config defaults and CLI defaults.
  - Applies preset-derived matcher defaults before parsing final CLI arguments.
- Modify `examples/controlnet_construct/run_pipeline_example.sh`
  - Adds `--match-preset-path`.
  - Resolves `ImageMatch.match_preset_path`.
  - Prevents CLI `--match-preset-path` from being mixed with `--matcher-method` or `--deep-match-config-path`.
  - Forwards `--match-preset-path` to `image_match.py`.
- Modify `examples/controlnet_construct/run_image_match_batch_example.sh`
  - Mirrors the same interface and forwarding behavior as `run_pipeline_example.sh`.
- Create `examples/controlnet_construct/presets/classic_sift_flann.json`
- Create `examples/controlnet_construct/presets/classic_sift_bf.json`
- Modify `examples/controlnet_construct/PRESETS_README.md`
  - Documents classic SIFT presets separately from LightGlue SIFT.
- Modify `examples/controlnet_construct/controlnet_config.example.json`
  - Adds `ImageMatch.match_preset_path` as a nullable field near existing matcher config.
- Modify `tests/unitTest/test_match_preset_config.py`
  - Unit tests for preset validation and runtime mapping.
- Modify `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
  - Wrapper and parser integration tests.

---

### Task 1: Add Failing Unit Tests for Match Preset Resolution

**Files:**
- Create: `tests/unitTest/test_match_preset_config.py`
- Later Create: `examples/controlnet_construct/match_preset_config.py`

- [x] **Step 1: Write the failing tests**

Create `tests/unitTest/test_match_preset_config.py` with this complete content:

```python
"""Tests for neutral ControlNet match preset resolution."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTROLNET_EXAMPLES = PROJECT_ROOT / "examples" / "controlnet_construct"
if str(CONTROLNET_EXAMPLES) not in sys.path:
    sys.path.insert(0, str(CONTROLNET_EXAMPLES))


class MatchPresetConfigUnitTest(unittest.TestCase):
    def _write_preset(self, payload: dict[str, object]) -> Path:
        temp_dir = Path(tempfile.mkdtemp(prefix="match_preset_test_"))
        preset_path = temp_dir / "preset.json"
        preset_path.write_text(json.dumps(payload), encoding="utf-8")
        return preset_path

    def test_classic_sift_flann_preset_maps_to_image_match_defaults(self):
        from match_preset_config import resolve_match_preset_runtime_config

        preset_path = self._write_preset(
            {
                "feature_extractor": {
                    "method": "classic_sift",
                    "max_features": 1000,
                    "octave_layers": 3,
                    "contrast_threshold": 0.04,
                    "edge_threshold": 10.0,
                    "sigma": 1.6,
                },
                "matcher": {"method": "flann", "ratio_test": 0.75},
            }
        )

        runtime = resolve_match_preset_runtime_config(preset_path)

        self.assertFalse(runtime.is_deep_matcher)
        self.assertEqual(runtime.matcher_method, "flann")
        self.assertIsNone(runtime.deep_match_config_path)
        self.assertEqual(
            runtime.image_match_defaults,
            {
                "match_preset_path": str(preset_path),
                "matcher_method": "flann",
                "deep_match_config_path": None,
                "max_features": 1000,
                "sift_octave_layers": 3,
                "sift_contrast_threshold": 0.04,
                "sift_edge_threshold": 10.0,
                "sift_sigma": 1.6,
                "ratio_test": 0.75,
            },
        )

    def test_classic_sift_bf_preset_maps_to_bf_matcher(self):
        from match_preset_config import resolve_match_preset_runtime_config

        preset_path = self._write_preset(
            {
                "feature_extractor": {
                    "method": "classic_sift",
                    "max_features": 2048,
                    "octave_layers": 4,
                    "contrast_threshold": 0.03,
                    "edge_threshold": 12.0,
                    "sigma": 1.4,
                },
                "matcher": {"method": "bf", "ratio_test": 0.8},
            }
        )

        runtime = resolve_match_preset_runtime_config(preset_path)

        self.assertFalse(runtime.is_deep_matcher)
        self.assertEqual(runtime.matcher_method, "bf")
        self.assertEqual(runtime.image_match_defaults["matcher_method"], "bf")
        self.assertEqual(runtime.image_match_defaults["ratio_test"], 0.8)

    def test_deep_preset_maps_to_existing_deep_config_path(self):
        from match_preset_config import resolve_match_preset_runtime_config

        preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "lightglue_official_superpoint.json"

        runtime = resolve_match_preset_runtime_config(preset_path)

        self.assertTrue(runtime.is_deep_matcher)
        self.assertEqual(runtime.matcher_method, "lightglue")
        self.assertEqual(runtime.deep_match_config_path, str(preset_path))
        self.assertEqual(runtime.image_match_defaults["matcher_method"], "lightglue")
        self.assertEqual(runtime.image_match_defaults["deep_match_config_path"], str(preset_path))

    def test_classic_sift_rejects_lightglue_sift_name(self):
        from match_preset_config import MatchPresetConfigError, resolve_match_preset_runtime_config

        preset_path = self._write_preset(
            {
                "feature_extractor": {"method": "lightglue_sift", "max_features": 1000},
                "matcher": {"method": "flann", "ratio_test": 0.75},
            }
        )

        with self.assertRaisesRegex(MatchPresetConfigError, "classic_sift"):
            resolve_match_preset_runtime_config(preset_path)

    def test_classic_sift_rejects_invalid_ratio_test(self):
        from match_preset_config import MatchPresetConfigError, resolve_match_preset_runtime_config

        preset_path = self._write_preset(
            {
                "feature_extractor": {
                    "method": "classic_sift",
                    "max_features": 1000,
                    "octave_layers": 3,
                    "contrast_threshold": 0.04,
                    "edge_threshold": 10.0,
                    "sigma": 1.6,
                },
                "matcher": {"method": "flann", "ratio_test": 1.5},
            }
        )

        with self.assertRaisesRegex(MatchPresetConfigError, "ratio_test"):
            resolve_match_preset_runtime_config(preset_path)

    def test_classic_sift_rejects_deep_only_sections(self):
        from match_preset_config import MatchPresetConfigError, resolve_match_preset_runtime_config

        preset_path = self._write_preset(
            {
                "feature_extractor": {
                    "method": "classic_sift",
                    "max_features": 1000,
                    "octave_layers": 3,
                    "contrast_threshold": 0.04,
                    "edge_threshold": 10.0,
                    "sigma": 1.6,
                },
                "matcher": {"method": "flann", "ratio_test": 0.75},
                "device": {"prefer_gpu": True},
            }
        )

        with self.assertRaisesRegex(MatchPresetConfigError, "deep-only"):
            resolve_match_preset_runtime_config(preset_path)

    def test_resolve_match_preset_path_prefers_config_relative_path(self):
        from match_preset_config import resolve_match_preset_path

        temp_dir = Path(tempfile.mkdtemp(prefix="match_preset_path_test_"))
        config_dir = temp_dir / "configs"
        preset_dir = config_dir / "presets"
        preset_dir.mkdir(parents=True)
        config_path = config_dir / "controlnet_config.json"
        preset_path = preset_dir / "classic_sift_flann.json"
        config_path.write_text("{}", encoding="utf-8")
        preset_path.write_text("{}", encoding="utf-8")

        resolved = resolve_match_preset_path(
            "presets/classic_sift_flann.json",
            config_path=config_path,
            repo_root=PROJECT_ROOT,
        )

        self.assertEqual(resolved, preset_path.resolve())


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run the failing tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.test_match_preset_config -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'match_preset_config'`.

- [x] **Step 3: Implement `match_preset_config.py`**

Create `examples/controlnet_construct/match_preset_config.py`:

```python
"""Neutral ControlNet match preset loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
import shlex
from typing import Any

from deep_match_config import DEEP_MATCHER_METHODS, load_deep_match_config


CLASSIC_SIFT_FEATURE_METHOD = "classic_sift"
CLASSIC_SIFT_MATCHER_METHODS = ("bf", "flann")
CLASSIC_SIFT_FEATURE_OPTIONS = {
    "method",
    "max_features",
    "octave_layers",
    "contrast_threshold",
    "edge_threshold",
    "sigma",
}
CLASSIC_SIFT_MATCHER_OPTIONS = {"method", "ratio_test"}
DEEP_ONLY_TOP_LEVEL_SECTIONS = {"device", "fallback"}


class MatchPresetConfigError(ValueError):
    """Raised when a match preset cannot be loaded or validated."""


@dataclass(frozen=True, slots=True)
class MatchPresetRuntimeConfig:
    """Resolved match preset values consumed by wrappers and image_match.py."""

    preset_path: str
    matcher_method: str
    is_deep_matcher: bool
    deep_match_config_path: str | None
    image_match_defaults: dict[str, object]
    raw_config: dict[str, Any]


def _load_json_object(config_path: str | Path) -> dict[str, Any]:
    resolved_path = Path(config_path)
    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MatchPresetConfigError(f"match preset not found: {resolved_path}") from exc
    except json.JSONDecodeError as exc:
        raise MatchPresetConfigError(f"failed to parse match preset {resolved_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise MatchPresetConfigError("match preset JSON must decode to an object.")
    return payload


def _require_section(payload: dict[str, Any], section_name: str) -> dict[str, Any]:
    value = payload.get(section_name)
    if not isinstance(value, dict):
        raise MatchPresetConfigError(f"match preset requires object section '{section_name}'.")
    return value


def _validate_positive_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MatchPresetConfigError(f"{field_name} must be a positive integer.")
    return value


def _validate_positive_number(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) <= 0.0:
        raise MatchPresetConfigError(f"{field_name} must be a positive number.")
    return float(value)


def _validate_probability(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MatchPresetConfigError(f"{field_name} must be in (0, 1].")
    resolved = float(value)
    if resolved <= 0.0 or resolved > 1.0:
        raise MatchPresetConfigError(f"{field_name} must be in (0, 1].")
    return resolved


def _reject_unknown_options(section: dict[str, Any], *, section_name: str, allowed: set[str]) -> None:
    unknown = sorted(set(section) - allowed)
    if unknown:
        raise MatchPresetConfigError(
            f"unknown {section_name} option(s) for classic SIFT preset: {', '.join(unknown)}"
        )


def _resolve_classic_sift_preset(
    preset_path: Path,
    payload: dict[str, Any],
    feature_extractor: dict[str, Any],
    matcher: dict[str, Any],
) -> MatchPresetRuntimeConfig:
    deep_only_sections = sorted(set(payload) & DEEP_ONLY_TOP_LEVEL_SECTIONS)
    if deep_only_sections:
        raise MatchPresetConfigError(
            f"classic SIFT preset includes deep-only section(s): {', '.join(deep_only_sections)}"
        )
    _reject_unknown_options(
        feature_extractor,
        section_name="feature_extractor",
        allowed=CLASSIC_SIFT_FEATURE_OPTIONS,
    )
    _reject_unknown_options(matcher, section_name="matcher", allowed=CLASSIC_SIFT_MATCHER_OPTIONS)

    matcher_method = str(matcher.get("method", "")).strip().lower()
    if matcher_method not in CLASSIC_SIFT_MATCHER_METHODS:
        raise MatchPresetConfigError(
            "classic SIFT matcher.method must be one of "
            f"{CLASSIC_SIFT_MATCHER_METHODS}; got {matcher.get('method')!r}."
        )

    defaults: dict[str, object] = {
        "match_preset_path": str(preset_path),
        "matcher_method": matcher_method,
        "deep_match_config_path": None,
        "max_features": _validate_positive_int(
            feature_extractor.get("max_features"),
            field_name="feature_extractor.max_features",
        ),
        "sift_octave_layers": _validate_positive_int(
            feature_extractor.get("octave_layers"),
            field_name="feature_extractor.octave_layers",
        ),
        "sift_contrast_threshold": _validate_positive_number(
            feature_extractor.get("contrast_threshold"),
            field_name="feature_extractor.contrast_threshold",
        ),
        "sift_edge_threshold": _validate_positive_number(
            feature_extractor.get("edge_threshold"),
            field_name="feature_extractor.edge_threshold",
        ),
        "sift_sigma": _validate_positive_number(
            feature_extractor.get("sigma"),
            field_name="feature_extractor.sigma",
        ),
        "ratio_test": _validate_probability(matcher.get("ratio_test"), field_name="matcher.ratio_test"),
    }
    return MatchPresetRuntimeConfig(
        preset_path=str(preset_path),
        matcher_method=matcher_method,
        is_deep_matcher=False,
        deep_match_config_path=None,
        image_match_defaults=defaults,
        raw_config=dict(payload),
    )


def resolve_match_preset_runtime_config(config_path: str | Path) -> MatchPresetRuntimeConfig:
    resolved_path = Path(config_path).expanduser().resolve()
    payload = _load_json_object(resolved_path)
    feature_extractor = _require_section(payload, "feature_extractor")
    matcher = _require_section(payload, "matcher")
    matcher_method = str(matcher.get("method", "")).strip().lower()
    feature_method = str(feature_extractor.get("method", "")).strip().lower()

    if matcher_method in DEEP_MATCHER_METHODS:
        try:
            validated = load_deep_match_config(resolved_path)
        except ValueError as exc:
            raise MatchPresetConfigError(str(exc)) from exc
        return MatchPresetRuntimeConfig(
            preset_path=str(resolved_path),
            matcher_method=matcher_method,
            is_deep_matcher=True,
            deep_match_config_path=str(resolved_path),
            image_match_defaults={
                "match_preset_path": str(resolved_path),
                "matcher_method": matcher_method,
                "deep_match_config_path": str(resolved_path),
            },
            raw_config=validated,
        )

    if feature_method != CLASSIC_SIFT_FEATURE_METHOD:
        raise MatchPresetConfigError(
            "non-deep match presets must use "
            f"feature_extractor.method='{CLASSIC_SIFT_FEATURE_METHOD}'; got {feature_method!r}."
        )
    return _resolve_classic_sift_preset(resolved_path, payload, feature_extractor, matcher)


def resolve_match_preset_path(
    raw_path: str | Path,
    *,
    config_path: str | Path | None = None,
    repo_root: str | Path | None = None,
) -> Path:
    raw = Path(raw_path).expanduser()
    if raw.is_absolute():
        return raw.resolve()

    if config_path is not None:
        config_candidate = Path(config_path).expanduser().resolve().parent / raw
        if config_candidate.is_file():
            return config_candidate.resolve()

    if repo_root is not None:
        repo_candidate = Path(repo_root).expanduser().resolve() / raw
        if repo_candidate.is_file():
            return repo_candidate.resolve()

    return raw.resolve()


def shell_assignments_for_match_preset(config_path: str | Path) -> dict[str, str]:
    runtime = resolve_match_preset_runtime_config(config_path)
    return {
        "MATCH_PRESET_PATH": runtime.preset_path,
        "MATCH_PRESET_IS_DEEP": "1" if runtime.is_deep_matcher else "0",
        "MATCHER_METHOD": runtime.matcher_method,
        "DEEP_MATCHER_CONFIG_PATH": runtime.deep_match_config_path or "",
    }


def format_shell_assignments(assignments: dict[str, str]) -> str:
    return "\n".join(f"{key}={shlex.quote(value)}" for key, value in assignments.items())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Resolve a ControlNet match preset.")
    parser.add_argument("preset_path")
    parser.add_argument("--shell-assignments", action="store_true")
    args = parser.parse_args(argv)
    if args.shell_assignments:
        print(format_shell_assignments(shell_assignments_for_match_preset(args.preset_path)))
        return
    runtime = resolve_match_preset_runtime_config(args.preset_path)
    print(json.dumps(runtime.image_match_defaults, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [x] **Step 4: Run tests again**

Run:

```bash
python -m unittest tests.unitTest.test_match_preset_config -v
```

Expected: PASS.

- [x] **Step 5: Commit**

Run:

```bash
git add examples/controlnet_construct/match_preset_config.py tests/unitTest/test_match_preset_config.py
git commit -m "feat: add match preset resolver"
```

---

### Task 2: Add Classic SIFT Preset JSON Files

**Files:**
- Create: `examples/controlnet_construct/presets/classic_sift_flann.json`
- Create: `examples/controlnet_construct/presets/classic_sift_bf.json`
- Test: `tests/unitTest/test_match_preset_config.py`

- [x] **Step 1: Create the FLANN preset**

Create `examples/controlnet_construct/presets/classic_sift_flann.json`:

```json
{
  "feature_extractor": {
    "method": "classic_sift",
    "max_features": 1000,
    "octave_layers": 3,
    "contrast_threshold": 0.04,
    "edge_threshold": 10.0,
    "sigma": 1.6
  },
  "matcher": {
    "method": "flann",
    "ratio_test": 0.75
  }
}
```

- [x] **Step 2: Create the BF preset**

Create `examples/controlnet_construct/presets/classic_sift_bf.json`:

```json
{
  "feature_extractor": {
    "method": "classic_sift",
    "max_features": 1000,
    "octave_layers": 3,
    "contrast_threshold": 0.04,
    "edge_threshold": 10.0,
    "sigma": 1.6
  },
  "matcher": {
    "method": "bf",
    "ratio_test": 0.75
  }
}
```

- [x] **Step 3: Add shared preset file tests**

Append these tests to `MatchPresetConfigUnitTest` in `tests/unitTest/test_match_preset_config.py`:

```python
    def test_shared_classic_sift_flann_preset_loads(self):
        from match_preset_config import resolve_match_preset_runtime_config

        preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_flann.json"

        runtime = resolve_match_preset_runtime_config(preset_path)

        self.assertEqual(runtime.matcher_method, "flann")
        self.assertFalse(runtime.is_deep_matcher)
        self.assertEqual(runtime.image_match_defaults["max_features"], 1000)

    def test_shared_classic_sift_bf_preset_loads(self):
        from match_preset_config import resolve_match_preset_runtime_config

        preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_bf.json"

        runtime = resolve_match_preset_runtime_config(preset_path)

        self.assertEqual(runtime.matcher_method, "bf")
        self.assertFalse(runtime.is_deep_matcher)
        self.assertEqual(runtime.image_match_defaults["ratio_test"], 0.75)
```

- [x] **Step 4: Run preset tests**

Run:

```bash
python -m unittest tests.unitTest.test_match_preset_config -v
```

Expected: PASS.

- [x] **Step 5: Commit**

Run:

```bash
git add examples/controlnet_construct/presets/classic_sift_flann.json examples/controlnet_construct/presets/classic_sift_bf.json tests/unitTest/test_match_preset_config.py
git commit -m "feat: add classic sift presets"
```

---

### Task 3: Apply Match Presets in `image_match.py`

**Files:**
- Modify: `examples/image_match/image_match.py`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [x] **Step 1: Add failing parser/config tests**

In `tests/unitTest/controlnet_construct_pipeline_unit_test.py`, add these methods near existing image-match parser/config tests:

```python
    def test_image_match_config_match_preset_overrides_legacy_matcher_fields(self):
        from image_match.image_match import load_image_match_defaults_from_config

        with temporary_directory() as temp_dir:
            config_path = temp_dir / "controlnet_config.json"
            preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_bf.json"
            config_path.write_text(
                json.dumps(
                    {
                        "ImageMatch": {
                            "match_preset_path": str(preset_path),
                            "matcher_method": "lightglue",
                            "deep_matcher_config_path": "examples/controlnet_construct/presets/lightglue_default.json",
                        }
                    }
                ),
                encoding="utf-8",
            )

            defaults = load_image_match_defaults_from_config(config_path)

        self.assertEqual(defaults["match_preset_path"], str(preset_path.resolve()))
        self.assertEqual(defaults["matcher_method"], "bf")
        self.assertIsNone(defaults["deep_match_config_path"])
        self.assertEqual(defaults["max_features"], 1000)

    def test_image_match_parser_accepts_match_preset_path_cli(self):
        parser = build_controlnet_stereopair_argument_parser()
        preset_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_flann.json"

        parsed = parser.parse_args(
            [
                "left_dom.cub",
                "right_dom.cub",
                "left.key",
                "right.key",
                "--match-preset-path",
                str(preset_path),
            ]
        )

        self.assertEqual(parsed.match_preset_path, str(preset_path.resolve()))
        self.assertEqual(parsed.matcher_method, "flann")
        self.assertEqual(parsed.max_features, 1000)
```

- [x] **Step 2: Run the failing tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_image_match_config_match_preset_overrides_legacy_matcher_fields -v
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_image_match_parser_accepts_match_preset_path_cli -v
```

Expected: FAIL because `match_preset_path` is not parsed or applied yet.

- [x] **Step 3: Add imports and helper functions**

In `examples/image_match/image_match.py`, add helper imports next to `_load_deep_match_config` helpers:

```python
def _resolve_match_preset_path(raw_path: str | Path, *, config_path: str | Path | None = None) -> Path:
    from controlnet_construct.match_preset_config import resolve_match_preset_path

    return resolve_match_preset_path(
        raw_path,
        config_path=config_path,
        repo_root=Path(__file__).resolve().parents[2],
    )


def _resolve_match_preset_defaults(raw_path: str | Path, *, config_path: str | Path | None = None) -> dict[str, object]:
    from controlnet_construct.match_preset_config import resolve_match_preset_runtime_config

    preset_path = _resolve_match_preset_path(raw_path, config_path=config_path)
    return dict(resolve_match_preset_runtime_config(preset_path).image_match_defaults)
```

- [x] **Step 4: Add `match_preset_path` to config defaults**

In `load_image_match_defaults_from_config`, add this field spec before `matcher_method`:

```python
        (
            "match_preset_path",
            ("match_preset_path", "matchPresetPath", "MatchPresetPath"),
            lambda value: str(value),
        ),
```

After the existing `for destination, candidate_keys, coercer in field_specs:` loop and before `return defaults`, add:

```python
    match_preset_path = defaults.get("match_preset_path")
    if match_preset_path not in (None, ""):
        preset_defaults = _resolve_match_preset_defaults(
            str(match_preset_path),
            config_path=resolved_path,
        )
        defaults.update(preset_defaults)
    return defaults
```

Remove the existing `return defaults` that immediately followed the loop so there is only one return.

- [x] **Step 5: Add parser support for CLI preset defaults**

In `build_argument_parser`, add this argument immediately before `--matcher-method`:

```python
    parser.add_argument(
        "--match-preset-path",
        type=lambda value: str(_resolve_match_preset_path(value)),
        default=None,
        help=(
            "Path to a neutral match preset JSON. Classic SIFT presets set OpenCV SIFT/BF/FLANN "
            "parameters; deep presets set matcher_method plus deep_match_config_path."
        ),
    )
```

In `main`, after `args = parser.parse_args(resolved_argv)` and before validation of low-resolution DOM args, add:

```python
    if args.match_preset_path not in (None, ""):
        preset_defaults = _resolve_match_preset_defaults(args.match_preset_path)
        for key, value in preset_defaults.items():
            setattr(args, key, value)
```

This makes CLI `--match-preset-path` a complete matcher selection and lets its values override parser defaults.

- [x] **Step 6: Run the focused tests**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_image_match_config_match_preset_overrides_legacy_matcher_fields -v
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_image_match_parser_accepts_match_preset_path_cli -v
```

Expected: PASS.

- [x] **Step 7: Run resolver and pipeline parser tests together**

Run:

```bash
python -m unittest tests.unitTest.test_match_preset_config tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: PASS.

- [x] **Step 8: Commit**

Run:

```bash
git add examples/image_match/image_match.py tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: apply match presets in image_match"
```

---

### Task 4: Wire `--match-preset-path` Through `run_pipeline_example.sh`

**Files:**
- Modify: `examples/controlnet_construct/run_pipeline_example.sh`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [x] **Step 1: Add failing wrapper test**

Add this method to `ControlNetConstructPipelineUnitTest` near the existing `run_pipeline_example.sh` wrapper tests:

```python
    def test_run_pipeline_example_forwards_classic_sift_match_preset_from_config(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"
            expected_preset = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_flann.json"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")
            config_path.write_text(
                json.dumps({"ImageMatch": {"match_preset_path": str(expected_preset)}}),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                _embedded_python_script(
                    f"""
                    #!{sys.executable}
                    import json
                    import sys
                    from pathlib import Path

                    EXPECTED_PRESET = {str(expected_preset)!r}

                    def _run_stdin_python() -> int:
                        code = sys.stdin.read()
                        globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                        sys.argv = ['-'] + sys.argv[2:]
                        exec(compile(code, "<stdin>", "exec"), globals_dict)
                        return 0

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]
                        if script_name == "image_match.py":
                            if "--print-config-default" in args:
                                config_path = Path(args[args.index("--config") + 1])
                                field_name = args[args.index("--print-config-default") + 1]
                                payload = json.loads(config_path.read_text(encoding="utf-8"))
                                image_match_config = payload.get("ImageMatch") or {{}}
                                print(image_match_config.get(field_name, ""))
                                return 0
                            if "--match-preset-path" not in args:
                                raise SystemExit("missing --match-preset-path")
                            preset_value = args[args.index("--match-preset-path") + 1]
                            if preset_value != EXPECTED_PRESET:
                                raise SystemExit(f"unexpected match preset: {{preset_value}}")
                            if "--deep-match-config-path" in args:
                                raise SystemExit("classic SIFT preset should not forward deep-match-config-path")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0
                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ),
                encoding="utf-8",
            )
            fake_python.write_text(
                textwrap.dedent(
                    f"""
                    #!/usr/bin/env bash
                    exec {sys.executable} "{fake_python_dispatcher}" "$@"
                    """
                ).lstrip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)

            completed = subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--python",
                    str(fake_python),
                    "--skip-final-merge",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("Match preset path:", completed.stdout)
        self.assertIn("Matcher method: flann", completed.stdout)
```

- [x] **Step 2: Run the failing test**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_pipeline_example_forwards_classic_sift_match_preset_from_config -v
```

Expected: FAIL because the wrapper does not read or forward `match_preset_path`.

- [x] **Step 3: Add wrapper helper functions**

In `examples/controlnet_construct/run_pipeline_example.sh`, add this helper after `resolve_config_relative_path`:

```bash
resolve_match_preset_shell_assignments() {
  local preset_path=$1
  "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/match_preset_config.py" \
    "$preset_path" \
    --shell-assignments
}

apply_match_preset_path() {
  local preset_path=$1
  local assignments
  assignments=$(resolve_match_preset_shell_assignments "$preset_path")
  eval "$assignments"
}
```

- [x] **Step 4: Add option state and parsing**

In `main`, add local state near `explicit_matcher_method`:

```bash
  local explicit_match_preset_path=""
  local match_preset_path=""
```

Add this option case before `--matcher-method`:

```bash
      --match-preset-path)
        [[ $# -ge 2 ]] || die "missing value for --match-preset-path"
        match_preset_path=$2
        explicit_match_preset_path=$2
        shift 2
        ;;
```

After argument parsing and before `require_command "$PYTHON_EXECUTABLE"`, add:

```bash
  if [[ -n "$explicit_match_preset_path" && -n "$explicit_matcher_method" ]]; then
    die "--match-preset-path cannot be combined with --matcher-method"
  fi
  if [[ -n "$explicit_match_preset_path" && -n "$DEEP_MATCHER_CONFIG_PATH" ]]; then
    die "--match-preset-path cannot be combined with --deep-match-config-path"
  fi
```

- [x] **Step 5: Resolve config preset and apply it**

After `require_file "$CONFIG_PATH"` and before reading `ImageMatch.matcher_method`, insert:

```bash
  if [[ -z "$match_preset_path" ]]; then
    local config_match_preset_path
    config_match_preset_path=$(extract_image_match_config_value "$CONFIG_PATH" "match_preset_path")
    if [[ -n "$config_match_preset_path" && "$config_match_preset_path" != "null" ]]; then
      match_preset_path=$(resolve_config_relative_path "$config_match_preset_path" "$CONFIG_PATH")
    fi
  fi
  if [[ -n "$match_preset_path" ]]; then
    match_preset_path=$(resolve_config_relative_path "$match_preset_path" "$CONFIG_PATH")
    apply_match_preset_path "$match_preset_path"
  fi
```

Change the existing matcher/deep config fallback blocks so they only run when no preset was selected:

```bash
  if [[ -z "$match_preset_path" && -z "$explicit_matcher_method" ]]; then
    local config_matcher_method
    config_matcher_method=$(extract_image_match_config_value "$CONFIG_PATH" "matcher_method")
    if [[ -n "$config_matcher_method" ]]; then
      MATCHER_METHOD="$config_matcher_method"
    fi
  fi
```

and:

```bash
  if [[ -z "$match_preset_path" && -z "$DEEP_MATCHER_CONFIG_PATH" ]]; then
    local config_deep_matcher_config_path
    config_deep_matcher_config_path=$(extract_image_match_config_value "$CONFIG_PATH" "deep_matcher_config_path")
    if [[ -n "$config_deep_matcher_config_path" && "$config_deep_matcher_config_path" != "null" ]]; then
      DEEP_MATCHER_CONFIG_PATH=$(resolve_config_relative_path "$config_deep_matcher_config_path" "$CONFIG_PATH")
    fi
  fi
```

- [x] **Step 6: Forward and log the preset**

In the logging area, add:

```bash
  if [[ -n "$match_preset_path" ]]; then
    log "Match preset path: $match_preset_path"
  fi
```

In `run_step_2_image_match_batch`, add `--match-preset-path` forwarding before `--matcher-method`:

```bash
    if [[ -n "$match_preset_path" ]]; then
      match_args+=(--match-preset-path "$match_preset_path")
    fi
    if [[ -z "$match_preset_path" ]]; then
      match_args+=(--matcher-method "$MATCHER_METHOD")
    fi
```

Remove the unconditional existing line:

```bash
    match_args+=(--matcher-method "$MATCHER_METHOD")
```

- [x] **Step 7: Run the focused test**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_pipeline_example_forwards_classic_sift_match_preset_from_config -v
```

Expected: PASS.

- [x] **Step 8: Commit**

Run:

```bash
git add examples/controlnet_construct/run_pipeline_example.sh tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: wire match presets through pipeline wrapper"
```

---

### Task 5: Wire `--match-preset-path` Through `run_image_match_batch_example.sh`

**Files:**
- Modify: `examples/controlnet_construct/run_image_match_batch_example.sh`
- Test: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`

- [x] **Step 1: Add failing batch wrapper test**

Add this method to `ControlNetConstructPipelineUnitTest` near existing `run_image_match_batch_example.sh` tests:

```python
    def test_run_image_match_batch_example_forwards_cli_match_preset(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()

            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            pair_list = work_dir / "images_overlap.lis"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"
            expected_preset = PROJECT_ROOT / "examples" / "controlnet_construct" / "presets" / "classic_sift_bf.json"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            pair_list.write_text("left.cub,right.cub\n", encoding="utf-8")

            fake_python_dispatcher.write_text(
                _embedded_python_script(
                    f"""
                    #!{sys.executable}
                    import sys
                    from pathlib import Path

                    EXPECTED_PRESET = {str(expected_preset)!r}

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]
                        if script_name == "image_match.py":
                            if "--match-preset-path" not in args:
                                raise SystemExit("missing --match-preset-path")
                            preset_value = args[args.index("--match-preset-path") + 1]
                            if preset_value != EXPECTED_PRESET:
                                raise SystemExit(f"unexpected match preset: {{preset_value}}")
                            if "--matcher-method" in args:
                                raise SystemExit("wrapper should not forward --matcher-method with --match-preset-path")
                            key_index = 4 if args and args[0] == "--config" else 2
                            Path(args[key_index]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[key_index + 1]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0
                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ),
                encoding="utf-8",
            )
            fake_python.write_text(
                textwrap.dedent(
                    f"""
                    #!/usr/bin/env bash
                    exec {sys.executable} "{fake_python_dispatcher}" "$@"
                    """
                ).lstrip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)

            completed = subprocess.run(
                [
                    "bash",
                    str(RUN_IMAGE_MATCH_BATCH_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--python",
                    str(fake_python),
                    "--match-preset-path",
                    str(expected_preset),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertIn("Match preset path:", completed.stdout)
        self.assertIn("Matcher method: bf", completed.stdout)
```

- [x] **Step 2: Run the failing test**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_image_match_batch_example_forwards_cli_match_preset -v
```

Expected: FAIL because the batch wrapper does not recognize `--match-preset-path`.

- [x] **Step 3: Mirror wrapper state and helpers**

In `examples/controlnet_construct/run_image_match_batch_example.sh`:

Add usage text after `--matcher-method`:

```text
  --match-preset-path PATH        Neutral match preset JSON. Classic SIFT presets select BF/FLANN and
                                  SIFT detector options; deep presets select matcher method plus deep config.
```

Add helper functions after `resolve_config_relative_path`:

```bash
resolve_match_preset_shell_assignments() {
  local preset_path=$1
  "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/match_preset_config.py" \
    "$preset_path" \
    --shell-assignments
}

apply_match_preset_path() {
  local preset_path=$1
  local assignments
  assignments=$(resolve_match_preset_shell_assignments "$preset_path")
  eval "$assignments"
}
```

Add state near other explicit flags:

```bash
  local explicit_match_preset_path=""
  local match_preset_path=""
```

Add parse case before `--matcher-method`:

```bash
      --match-preset-path)
        [[ $# -ge 2 ]] || die "missing value for --match-preset-path"
        match_preset_path=$2
        explicit_match_preset_path=$2
        shift 2
        ;;
```

Add conflict checks after parsing:

```bash
  if [[ -n "$explicit_match_preset_path" && -n "$explicit_matcher_method" ]]; then
    die "--match-preset-path cannot be combined with --matcher-method"
  fi
  if [[ -n "$explicit_match_preset_path" && -n "$explicit_deep_match_config_path" ]]; then
    die "--match-preset-path cannot be combined with --deep-match-config-path"
  fi
```

- [x] **Step 4: Resolve config preset and forward it**

Inside the `if [[ -n "$CONFIG_PATH" ]]; then` block, before reading `matcher_method`, add:

```bash
    if [[ -z "$match_preset_path" ]]; then
      local config_match_preset_path
      config_match_preset_path=$(extract_image_match_config_value "$config_input" "match_preset_path")
      if [[ -n "$config_match_preset_path" && "$config_match_preset_path" != "null" ]]; then
        match_preset_path=$(resolve_config_relative_path "$config_match_preset_path" "$CONFIG_PATH")
      fi
    fi
    if [[ -n "$match_preset_path" ]]; then
      match_preset_path=$(resolve_config_relative_path "$match_preset_path" "$CONFIG_PATH")
      apply_match_preset_path "$match_preset_path"
    fi
```

Guard existing config matcher/deep fallback reads:

```bash
    if [[ -z "$match_preset_path" && -z "$explicit_matcher_method" ]]; then
      local config_matcher_method
      config_matcher_method=$(extract_image_match_config_value "$config_input" "matcher_method")
      if [[ -n "$config_matcher_method" ]]; then
        matcher_method="$config_matcher_method"
      fi
    fi
```

and:

```bash
    if [[ -z "$match_preset_path" && -z "$explicit_deep_match_config_path" ]]; then
      local config_deep_matcher_config_path
      config_deep_matcher_config_path=$(extract_image_match_config_value "$config_input" "deep_matcher_config_path")
      if [[ -n "$config_deep_matcher_config_path" && "$config_deep_matcher_config_path" != "null" ]]; then
        deep_match_config_path=$(resolve_config_relative_path "$config_deep_matcher_config_path" "$CONFIG_PATH")
      fi
    fi
```

Add logging:

```bash
  if [[ -n "$match_preset_path" ]]; then
    log "Match preset path: $match_preset_path"
  fi
```

Change `match_args` construction so `--matcher-method` is only forwarded when no preset is active:

```bash
    if [[ -n "$match_preset_path" ]]; then
      match_args+=(--match-preset-path "$match_preset_path")
    else
      match_args+=(--matcher-method "$matcher_method")
    fi
```

Remove `--matcher-method "$matcher_method"` from the initial `match_args` array literals.

- [x] **Step 5: Run batch wrapper test**

Run:

```bash
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test.ControlNetConstructPipelineUnitTest.test_run_image_match_batch_example_forwards_cli_match_preset -v
```

Expected: PASS.

- [x] **Step 6: Commit**

Run:

```bash
git add examples/controlnet_construct/run_image_match_batch_example.sh tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: wire match presets through batch wrapper"
```

---

### Task 6: Update Example Config and Preset Documentation

**Files:**
- Modify: `examples/controlnet_construct/controlnet_config.example.json`
- Modify: `examples/controlnet_construct/PRESETS_README.md`
- Test: `tests/unitTest/test_match_preset_config.py`

- [x] **Step 1: Update example config**

In `examples/controlnet_construct/controlnet_config.example.json`, add `match_preset_path` next to existing matcher fields:

```json
    "matcher_method": "flann",
    "match_preset_path": null,
    "deep_matcher_config_path": null,
```

Keep `matcher_method` for backward compatibility.

- [x] **Step 2: Update preset catalog docs**

In `examples/controlnet_construct/PRESETS_README.md`, add these two rows near the top of the Preset Catalog:

```markdown
| `classic_sift_flann.json` | OpenCV SIFT | FLANN | Classic non-learning SIFT descriptor matching. Recommended traditional baseline. |
| `classic_sift_bf.json` | OpenCV SIFT | BF | Classic non-learning SIFT descriptor matching with brute-force L2 matching. |
```

Add a section before `## Official LightGlue Backend`:

```markdown
## Classic SIFT Presets

`classic_sift_flann.json` and `classic_sift_bf.json` use the original OpenCV
SIFT path in `examples/image_match/tile_matching.py`.

These presets are not deep-learning presets. They run in the normal
`asp360_new` environment and do not require the separate `deep-learning` conda
environment.

Use them through the neutral match preset option:

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --match-preset-path examples/controlnet_construct/presets/classic_sift_flann.json
```

or in config JSON:

```json
{
  "ImageMatch": {
    "match_preset_path": "examples/controlnet_construct/presets/classic_sift_flann.json"
  }
}
```

`classic_sift_*` means OpenCV SIFT descriptors plus BF or FLANN matching.
`lightglue_official_sift.json` means `lightglue.SIFT` plus
`lightglue.LightGlue`; it is a learning matcher preset and still follows the
deep matcher `direct`, `export`, and `import` workflows.
```

Update the existing Usage section from `deep_matcher_config_path`-only wording to mention both forms:

```markdown
For learning-only legacy configuration, specify `deep_matcher_config_path` in
`ImageMatch`. For unified classic/deep selection, prefer
`ImageMatch.match_preset_path`.
```

- [x] **Step 3: Add JSON parse regression test**

Append this test to `tests/unitTest/test_match_preset_config.py`:

```python
    def test_controlnet_example_config_declares_match_preset_path(self):
        config_path = PROJECT_ROOT / "examples" / "controlnet_construct" / "controlnet_config.example.json"
        payload = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertIn("match_preset_path", payload["ImageMatch"])
        self.assertIsNone(payload["ImageMatch"]["match_preset_path"])
```

- [x] **Step 4: Run docs/config tests**

Run:

```bash
python -m unittest tests.unitTest.test_match_preset_config -v
python -m json.tool examples/controlnet_construct/controlnet_config.example.json >/dev/null
python -m json.tool examples/controlnet_construct/presets/classic_sift_flann.json >/dev/null
python -m json.tool examples/controlnet_construct/presets/classic_sift_bf.json >/dev/null
```

Expected: all commands exit 0.

- [x] **Step 5: Commit**

Run:

```bash
git add examples/controlnet_construct/controlnet_config.example.json examples/controlnet_construct/PRESETS_README.md tests/unitTest/test_match_preset_config.py
git commit -m "docs: document classic sift match presets"
```

---

### Task 7: Run Final Verification

**Files:**
- No new files.

- [ ] **Step 1: Run focused unit tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.test_match_preset_config tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: PASS.

- [ ] **Step 2: Run image-match smoke import**

Run:

```bash
python tests/smoke_import.py
```

Expected: PASS and `_isis_core` imports successfully.

- [ ] **Step 3: Run JSON validation**

Run:

```bash
python -m json.tool examples/controlnet_construct/presets/classic_sift_flann.json >/dev/null
python -m json.tool examples/controlnet_construct/presets/classic_sift_bf.json >/dev/null
python -m json.tool examples/controlnet_construct/controlnet_config.example.json >/dev/null
```

Expected: all commands exit 0.

- [ ] **Step 4: Inspect git history and status**

Run:

```bash
git status --short --branch
git log --oneline --decorate -5
```

Expected: working tree clean, branch contains the implementation commits from this plan.

---

## Self-Review

- Spec coverage:
  - Two classic SIFT presets are covered in Task 2.
  - Neutral `match_preset_path` CLI/config interface is covered in Tasks 3, 4, and 5.
  - Classic-vs-LightGlue SIFT distinction is covered in Task 6 docs.
  - Validation for classic SIFT fields and deep-only sections is covered in Task 1.
  - Existing deep matcher behavior is preserved by resolving deep presets through `load_deep_match_config`.
- Placeholder scan:
  - The plan avoids placeholder markers and incomplete task stubs.
- Type consistency:
  - The plan consistently uses `match_preset_path`, `deep_match_config_path`, `matcher_method`, and `MatchPresetRuntimeConfig`.
  - Classic SIFT maps `octave_layers` to `sift_octave_layers`, `contrast_threshold` to `sift_contrast_threshold`, `edge_threshold` to `sift_edge_threshold`, and `sigma` to `sift_sigma`.
