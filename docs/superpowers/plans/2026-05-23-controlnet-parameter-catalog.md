# ControlNet Parameter Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared ControlNet parameter catalog and validation layer so pipeline users can inspect grouped options and validate CLI/config/preset combinations before running expensive work.

**Architecture:** Add focused Python modules under `examples/controlnet_construct/`: one catalog module for parameter metadata, one validation module for merge/provenance/warnings/errors, and one small CLI for shell-wrapper integration. Connect `run_pipeline_example.sh` first, then align overlapping validators in `image_match.py` and `controlnet_stereopair.py` without changing existing defaults or output paths.

**Tech Stack:** Python 3.12 stdlib (`argparse`, `dataclasses`, `json`, `math`, `pathlib`, `shlex`), Bash, existing `unittest` suite, existing ControlNet and ImageMatch helper modules.

---

## File Structure

- Create: `examples/controlnet_construct/parameter_catalog.py`
  - Owns parameter group order, parameter records, allowed values, known ranges, config mappings, and entrypoint membership.
- Create: `examples/controlnet_construct/parameter_validation.py`
  - Owns value source precedence, normalized values, structured warnings/errors, strict mode, and shell-assignment formatting.
- Create: `examples/controlnet_construct/print_parameter_catalog.py`
  - Provides grouped help, JSON catalog output, JSON validation, and shell-assignment output for wrapper scripts.
- Modify: `examples/controlnet_construct/run_pipeline_example.sh`
  - Adds `--print-parameter-groups`, `--validate-parameters-only`, and `--strict-parameter-validation`.
  - Calls the Python validator after config/preset defaults are resolved.
  - Keeps current downstream command forwarding and output layout.
- Modify: `examples/image_match/image_match.py`
  - Reuses shared parsing validators for overlapping allowed values and numeric ranges.
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`
  - Reuses shared parsing validators for overlapping matcher, execution, and visualization values.
- Create: `tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py`
  - Covers catalog shape and runtime-constant alignment.
- Create: `tests/unitTest/controlnet_construct_parameter_validation_unit_test.py`
  - Covers precedence, hard errors, warnings, and strict mode.
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
  - Covers shell wrapper integration flags and validation behavior.
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`
  - Covers Python CLI compatibility where parser helpers are replaced.
- Modify: `examples/controlnet_construct/PRESETS_README.md`
  - Documents grouped parameters and validation-only workflow.

---

### Task 1: Add Catalog Shape and Runtime Constant Tests

**Files:**
- Create: `tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py`
- Later Create: `examples/controlnet_construct/parameter_catalog.py`

- [ ] **Step 1: Write failing catalog tests**

Create `tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py`:

```python
"""Tests for the shared ControlNet parameter catalog."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = PROJECT_ROOT / "examples"
if str(EXAMPLES_ROOT) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_ROOT))


class ControlNetParameterCatalogUnitTest(unittest.TestCase):
    def test_required_groups_are_declared_in_expected_order(self):
        from controlnet_construct.parameter_catalog import PARAMETER_GROUPS

        self.assertEqual(
            tuple(group.name for group in PARAMETER_GROUPS),
            (
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
            ),
        )

    def test_core_fields_have_group_cli_config_and_entrypoints(self):
        from controlnet_construct.parameter_catalog import PARAMETER_BY_NAME

        matcher = PARAMETER_BY_NAME["matcher_method"]
        self.assertEqual(matcher.group, "matching")
        self.assertEqual(matcher.cli_flag, "--matcher-method")
        self.assertEqual(matcher.config_path, "ImageMatch.matcher_method")
        self.assertIn("run_pipeline_example", matcher.entrypoints)
        self.assertIn("image_match", matcher.entrypoints)
        self.assertIn("controlnet_stereopair.from-ori-match", matcher.entrypoints)

        low_res = PARAMETER_BY_NAME["low_resolution_level"]
        self.assertEqual(low_res.group, "low_resolution")
        self.assertEqual(low_res.cli_flag, "--low-resolution-level")
        self.assertEqual(low_res.config_path, "ImageMatch.low_resolution_level")
        self.assertEqual(low_res.min_value, 0)

        strict = PARAMETER_BY_NAME["strict_parameter_validation"]
        self.assertEqual(strict.group, "reporting")
        self.assertEqual(strict.cli_flag, "--strict-parameter-validation")
        self.assertIn("run_pipeline_example", strict.entrypoints)

    def test_allowed_values_match_runtime_constants(self):
        from controlnet_construct.parameter_catalog import PARAMETER_BY_NAME
        from image_match.adaptive_routing import SUPPORTED_ADAPTIVE_ROUTING_PROFILES
        from image_match.image_match import SUPPORTED_DEEP_MATCH_MODES
        from image_match.match_visualization import (
            SUPPORTED_MEMORY_PROFILES,
            SUPPORTED_PREVIEW_CACHE_SOURCES,
            SUPPORTED_VISUALIZATION_MODES,
        )
        from image_match.tile_matching import SUPPORTED_MATCHER_METHODS

        self.assertEqual(PARAMETER_BY_NAME["matcher_method"].allowed_values, tuple(SUPPORTED_MATCHER_METHODS))
        self.assertEqual(PARAMETER_BY_NAME["deep_match_mode"].allowed_values, tuple(SUPPORTED_DEEP_MATCH_MODES))
        self.assertEqual(
            PARAMETER_BY_NAME["adaptive_routing_profile"].allowed_values,
            tuple(SUPPORTED_ADAPTIVE_ROUTING_PROFILES),
        )
        self.assertEqual(PARAMETER_BY_NAME["visualization_mode"].allowed_values, tuple(SUPPORTED_VISUALIZATION_MODES))
        self.assertEqual(PARAMETER_BY_NAME["memory_profile"].allowed_values, tuple(SUPPORTED_MEMORY_PROFILES))
        self.assertEqual(
            PARAMETER_BY_NAME["preview_cache_source"].allowed_values,
            tuple(SUPPORTED_PREVIEW_CACHE_SOURCES),
        )

    def test_grouped_catalog_filters_by_entrypoint(self):
        from controlnet_construct.parameter_catalog import grouped_parameters_for_entrypoint

        grouped = grouped_parameters_for_entrypoint("run_pipeline_example")
        self.assertIn("matching", grouped)
        self.assertIn("matcher_method", [parameter.name for parameter in grouped["matching"]])
        self.assertIn("pipeline", grouped)
        self.assertIn("deep_match_mode", [parameter.name for parameter in grouped["pipeline"]])

        image_match_grouped = grouped_parameters_for_entrypoint("image_match")
        self.assertNotIn("controlnet", image_match_grouped)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run failing catalog tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'controlnet_construct.parameter_catalog'`.

- [ ] **Step 3: Implement the catalog module**

Create `examples/controlnet_construct/parameter_catalog.py`:

```python
"""Shared parameter catalog for ControlNet construction entry points."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

try:
    from image_match.adaptive_routing import SUPPORTED_ADAPTIVE_ROUTING_PROFILES
    from image_match.match_visualization import (
        DEFAULT_MEMORY_PROFILE,
        DEFAULT_PREVIEW_CACHE_SOURCE,
        DEFAULT_PREVIEW_CROP_MARGIN_PIXELS,
        DEFAULT_VISUALIZATION_MODE,
        SUPPORTED_MEMORY_PROFILES,
        SUPPORTED_PREVIEW_CACHE_SOURCES,
        SUPPORTED_VISUALIZATION_MODES,
    )
    from image_match.tile_matching import DEFAULT_GPU_BATCH_SIZE, DEFAULT_MATCHER_METHOD, SUPPORTED_MATCHER_METHODS
except ImportError:
    SUPPORTED_ADAPTIVE_ROUTING_PROFILES = ("balanced", "strict", "relaxed", "fast")
    DEFAULT_MEMORY_PROFILE = "balanced"
    DEFAULT_PREVIEW_CACHE_SOURCE = "auto"
    DEFAULT_PREVIEW_CROP_MARGIN_PIXELS = 256
    DEFAULT_VISUALIZATION_MODE = "auto"
    SUPPORTED_MEMORY_PROFILES = ("high-memory", "balanced", "low-memory")
    SUPPORTED_PREVIEW_CACHE_SOURCES = ("auto", "matching_cache", "visualization_cache", "disabled")
    SUPPORTED_VISUALIZATION_MODES = ("auto", "full", "reduced", "cropped", "reduced_cropped")
    DEFAULT_GPU_BATCH_SIZE = 4
    DEFAULT_MATCHER_METHOD = "bf"
    SUPPORTED_MATCHER_METHODS = ("bf", "flann", "superpoint", "superglue", "lightglue", "loftr")

DEFAULT_DEEP_MATCH_MODE = "direct"
DEFAULT_LOW_RESOLUTION_LEVEL = 3
DEFAULT_NUM_WORKER_PARALLEL_CPU = 8
MAX_NUM_WORKER_PARALLEL_CPU = 4096
SUPPORTED_DEEP_MATCH_MODES = ("direct", "export", "import")


RUN_PIPELINE = "run_pipeline_example"
IMAGE_MATCH = "image_match"
FROM_ORI_MATCH = "controlnet_stereopair.from-ori-match"
FROM_DOM = "controlnet_stereopair.from-dom"
FROM_DOM_BATCH = "controlnet_stereopair.from-dom-batch"


@dataclass(frozen=True, slots=True)
class ParameterGroup:
    name: str
    title: str
    description: str


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    name: str
    group: str
    cli_flag: str | None
    config_path: str | None
    value_type: str
    default: Any = None
    allowed_values: tuple[Any, ...] = ()
    min_value: int | float | None = None
    max_value: int | float | None = None
    entrypoints: tuple[str, ...] = ()
    help: str = ""


PARAMETER_GROUPS: tuple[ParameterGroup, ...] = (
    ParameterGroup("inputs", "Inputs", "Input lists, config files, work directories, and interpreter selection."),
    ParameterGroup("pipeline", "Pipeline", "Pipeline mode and stage-control options."),
    ParameterGroup("matching", "Matching", "Matcher, preset, and feature extraction options."),
    ParameterGroup("tile", "Tile", "Tiling and tile-validity options."),
    ParameterGroup("low_resolution", "Low Resolution", "Low-resolution coarse offset estimation options."),
    ParameterGroup("adaptive_routing", "Adaptive Routing", "Adaptive matcher routing options."),
    ParameterGroup("execution", "Execution", "CPU/GPU execution and batching options."),
    ParameterGroup("visualization", "Visualization", "Pre- and post-RANSAC visualization options."),
    ParameterGroup("controlnet", "ControlNet", "ControlNet IDs, merge paths, and output format options."),
    ParameterGroup("reporting", "Reporting", "Reports, stdout detail, logging, and validation controls."),
)


def _spec(
    name: str,
    group: str,
    cli_flag: str | None,
    value_type: str,
    *,
    config_path: str | None = None,
    default: Any = None,
    allowed_values: tuple[Any, ...] = (),
    min_value: int | float | None = None,
    max_value: int | float | None = None,
    entrypoints: tuple[str, ...],
    help: str,
) -> ParameterSpec:
    return ParameterSpec(
        name=name,
        group=group,
        cli_flag=cli_flag,
        config_path=config_path,
        value_type=value_type,
        default=default,
        allowed_values=tuple(allowed_values),
        min_value=min_value,
        max_value=max_value,
        entrypoints=entrypoints,
        help=help,
    )


PARAMETERS: tuple[ParameterSpec, ...] = (
    _spec("work_dir", "inputs", "--work-dir", "path", default="work", entrypoints=(RUN_PIPELINE,), help="Root working directory."),
    _spec("original_list", "inputs", "--original-list", "path", entrypoints=(RUN_PIPELINE,), help="original_images.lis path."),
    _spec("dom_list", "inputs", "--dom-list", "path", entrypoints=(RUN_PIPELINE,), help="DOM list path."),
    _spec("config", "inputs", "--config", "path", entrypoints=(RUN_PIPELINE, IMAGE_MATCH, FROM_ORI_MATCH, FROM_DOM, FROM_DOM_BATCH), help="ControlNet or ImageMatch config JSON path."),
    _spec("python", "inputs", "--python", "path", entrypoints=(RUN_PIPELINE,), help="Python interpreter used by shell wrappers."),
    _spec("deep_match_mode", "pipeline", "--deep-match-mode", "choice", config_path="ImageMatch.deep_match_mode", default=DEFAULT_DEEP_MATCH_MODE, allowed_values=tuple(SUPPORTED_DEEP_MATCH_MODES), entrypoints=(RUN_PIPELINE, IMAGE_MATCH), help="Deep-match execution mode."),
    _spec("deep_match_temp_root_dir", "pipeline", "--deep-match-temp-root-dir", "path", entrypoints=(RUN_PIPELINE, IMAGE_MATCH), help="Export workspace root for deep-match manifests."),
    _spec("deep_match_manifest_dir", "pipeline", "--deep-match-manifest-dir", "path", entrypoints=(RUN_PIPELINE,), help="Import-mode manifest directory."),
    _spec("deep_match_manifest_summary", "pipeline", "--deep-match-manifest-summary", "path", entrypoints=(RUN_PIPELINE,), help="Deep-match manifest summary JSON path."),
    _spec("skip_final_merge", "pipeline", "--skip-final-merge", "bool", default=False, entrypoints=(RUN_PIPELINE,), help="Generate merge script but skip cnetmerge execution."),
    _spec("post_merge_control_measure", "pipeline", "--post-merge-control-measure", "bool", default=False, entrypoints=(RUN_PIPELINE,), help="Run merge_control_measure.py after cnetmerge."),
    _spec("post_merge_output", "pipeline", "--post-merge-output", "path", entrypoints=(RUN_PIPELINE,), help="Post-merge ControlNet output path."),
    _spec("post_merge_decimals", "pipeline", "--post-merge-decimals", "int", default=1, min_value=0, entrypoints=(RUN_PIPELINE,), help="Rounded hash decimals for post-merge control-measure merging."),
    _spec("matcher_method", "matching", "--matcher-method", "choice", config_path="ImageMatch.matcher_method", default=DEFAULT_MATCHER_METHOD, allowed_values=tuple(SUPPORTED_MATCHER_METHODS), entrypoints=(RUN_PIPELINE, IMAGE_MATCH, FROM_ORI_MATCH), help="Matcher backend."),
    _spec("match_preset_path", "matching", "--match-preset-path", "path", config_path="ImageMatch.match_preset_path", entrypoints=(RUN_PIPELINE, IMAGE_MATCH), help="Neutral match preset JSON path."),
    _spec("deep_match_config_path", "matching", "--deep-match-config-path", "path", config_path="ImageMatch.deep_matcher_config_path", entrypoints=(RUN_PIPELINE, IMAGE_MATCH, FROM_ORI_MATCH), help="Deep matcher preset JSON path."),
    _spec("ratio_test", "matching", "--ratio-test", "float", config_path="ImageMatch.ratio_test", default=0.75, min_value=0.0, max_value=1.0, entrypoints=(IMAGE_MATCH, FROM_ORI_MATCH), help="Lowe ratio-test threshold."),
    _spec("max_features", "matching", "--max-features", "int", config_path="ImageMatch.max_features", min_value=1, entrypoints=(IMAGE_MATCH, FROM_ORI_MATCH), help="Maximum SIFT features."),
    _spec("sift_octave_layers", "matching", "--sift-octave-layers", "int", config_path="ImageMatch.sift_octave_layers", default=3, min_value=1, entrypoints=(IMAGE_MATCH,), help="OpenCV SIFT octave layers."),
    _spec("sift_contrast_threshold", "matching", "--sift-contrast-threshold", "float", config_path="ImageMatch.sift_contrast_threshold", default=0.04, min_value=0.0, entrypoints=(IMAGE_MATCH,), help="OpenCV SIFT contrast threshold."),
    _spec("sift_edge_threshold", "matching", "--sift-edge-threshold", "float", config_path="ImageMatch.sift_edge_threshold", default=10.0, min_value=0.0, entrypoints=(IMAGE_MATCH,), help="OpenCV SIFT edge threshold."),
    _spec("sift_sigma", "matching", "--sift-sigma", "float", config_path="ImageMatch.sift_sigma", default=1.6, min_value=0.0, entrypoints=(IMAGE_MATCH,), help="OpenCV SIFT sigma."),
    _spec("max_image_dimension", "tile", "--max-image-dimension", "int", config_path="ImageMatch.max_image_dimension", default=3000, min_value=1, entrypoints=(IMAGE_MATCH,), help="Maximum dimension before tiling."),
    _spec("sub_block_size_x", "tile", "--sub-block-size-x", "int", config_path="ImageMatch.sub_block_size_x", default=1024, min_value=1, entrypoints=(IMAGE_MATCH,), help="Tile width."),
    _spec("sub_block_size_y", "tile", "--sub-block-size-y", "int", config_path="ImageMatch.sub_block_size_y", default=1024, min_value=1, entrypoints=(IMAGE_MATCH,), help="Tile height."),
    _spec("overlap_size_x", "tile", "--overlap-size-x", "int", config_path="ImageMatch.overlap_size_x", default=128, min_value=0, entrypoints=(IMAGE_MATCH,), help="Horizontal tile overlap."),
    _spec("overlap_size_y", "tile", "--overlap-size-y", "int", config_path="ImageMatch.overlap_size_y", default=128, min_value=0, entrypoints=(IMAGE_MATCH,), help="Vertical tile overlap."),
    _spec("enable_tile_validity_prefilter", "tile", "--enable-tile-validity-prefilter", "bool", config_path="ImageMatch.enable_tile_validity_prefilter", default=False, entrypoints=(IMAGE_MATCH,), help="Enable DOM validity prefilter."),
    _spec("tile_validity_cache_dir", "tile", "--tile-validity-cache-dir", "path", config_path="ImageMatch.tile_validity_cache_dir", entrypoints=(IMAGE_MATCH,), help="Tile-validity cache directory."),
    _spec("tile_validity_cell_width", "tile", "--tile-validity-cell-width", "int", config_path="ImageMatch.tile_validity_cell_width", default=1024, min_value=1, entrypoints=(IMAGE_MATCH,), help="Tile-validity cell width."),
    _spec("tile_validity_cell_height", "tile", "--tile-validity-cell-height", "int", config_path="ImageMatch.tile_validity_cell_height", default=1024, min_value=1, entrypoints=(IMAGE_MATCH,), help="Tile-validity cell height."),
    _spec("enable_low_resolution_offset_estimation", "low_resolution", "--enable-low-resolution-offset-estimation", "bool", config_path="ImageMatch.enable_low_resolution_offset_estimation", default=False, entrypoints=(RUN_PIPELINE, IMAGE_MATCH), help="Enable low-resolution coarse offset estimation."),
    _spec("low_resolution_level", "low_resolution", "--low-resolution-level", "int", config_path="ImageMatch.low_resolution_level", default=DEFAULT_LOW_RESOLUTION_LEVEL, min_value=0, entrypoints=(RUN_PIPELINE, IMAGE_MATCH), help="ISIS reduce pyramid level."),
    _spec("low_resolution_matching_target_long_edge", "low_resolution", "--low-resolution-matching-target-long-edge", "int", config_path="ImageMatch.low_resolution_matching_target_long_edge", min_value=1, entrypoints=(IMAGE_MATCH,), help="Target long-edge size for deriving low-resolution level."),
    _spec("low_resolution_trim_fraction_each_side", "low_resolution", "--low-resolution-trim-fraction-each-side", "float", config_path="ImageMatch.low_resolution_trim_fraction_each_side", min_value=0.0, max_value=0.499999, entrypoints=(IMAGE_MATCH,), help="Trim fraction for projected offset averaging."),
    _spec("low_resolution_max_mean_reprojection_error_pixels", "low_resolution", "--low-resolution-max-mean-reprojection-error-pixels", "float", config_path="ImageMatch.low_resolution_max_mean_reprojection_error_pixels", default=3.0, min_value=0.0, entrypoints=(RUN_PIPELINE, IMAGE_MATCH), help="Low-resolution RANSAC reprojection gate."),
    _spec("low_resolution_min_retained_match_count", "low_resolution", "--low-resolution-min-retained-match-count", "int", config_path="ImageMatch.low_resolution_min_retained_match_count", min_value=1, entrypoints=(RUN_PIPELINE, IMAGE_MATCH), help="Minimum retained low-resolution matches."),
    _spec("low_resolution_max_mean_projected_offset_meters", "low_resolution", "--low-resolution-max-mean-projected-offset-meters", "float", config_path="ImageMatch.low_resolution_max_mean_projected_offset_meters", min_value=0.0, entrypoints=(RUN_PIPELINE, IMAGE_MATCH), help="Projected-offset magnitude gate."),
    _spec("left_low_resolution_dom", "low_resolution", "--left-low-resolution-dom", "path", entrypoints=(IMAGE_MATCH,), help="Precomputed left low-resolution DOM."),
    _spec("right_low_resolution_dom", "low_resolution", "--right-low-resolution-dom", "path", entrypoints=(IMAGE_MATCH,), help="Precomputed right low-resolution DOM."),
    _spec("enable_adaptive_routing", "adaptive_routing", "--adaptive-routing", "bool", config_path="ImageMatch.enable_adaptive_routing", default=False, entrypoints=(RUN_PIPELINE, IMAGE_MATCH, FROM_ORI_MATCH), help="Enable adaptive matcher routing."),
    _spec("adaptive_routing_profile", "adaptive_routing", "--adaptive-routing-profile", "choice", config_path="ImageMatch.adaptive_routing_profile", default="balanced", allowed_values=tuple(SUPPORTED_ADAPTIVE_ROUTING_PROFILES), entrypoints=(RUN_PIPELINE, IMAGE_MATCH, FROM_ORI_MATCH), help="Adaptive routing quality profile."),
    _spec("adaptive_routing_deep_presets", "adaptive_routing", None, "mapping", config_path="ImageMatch.adaptive_routing_deep_presets", entrypoints=(RUN_PIPELINE, IMAGE_MATCH), help="Preset map used by adaptive deep routes."),
    _spec("use_parallel_cpu", "execution", "--use-parallel-cpu", "bool", config_path="ImageMatch.use_parallel_cpu", default=True, entrypoints=(RUN_PIPELINE, IMAGE_MATCH, FROM_ORI_MATCH), help="Enable CPU process-pool matching."),
    _spec("num_worker_parallel_cpu", "execution", "--num-worker-parallel-cpu", "int", config_path="ImageMatch.num_worker_parallel_cpu", default=DEFAULT_NUM_WORKER_PARALLEL_CPU, min_value=1, max_value=MAX_NUM_WORKER_PARALLEL_CPU, entrypoints=(RUN_PIPELINE, IMAGE_MATCH, FROM_ORI_MATCH), help="CPU worker limit."),
    _spec("use_gpu", "execution", "--use-gpu", "bool", config_path="ImageMatch.use_gpu", default=False, entrypoints=(IMAGE_MATCH, FROM_ORI_MATCH), help="Enable GPU route where supported."),
    _spec("gpu_batch_size", "execution", "--gpu-batch-size", "int", config_path="ImageMatch.gpu_batch_size", default=DEFAULT_GPU_BATCH_SIZE, min_value=1, entrypoints=(IMAGE_MATCH, FROM_ORI_MATCH), help="GPU batch size."),
    _spec("gpu_dynamic_batch", "execution", "--gpu-dynamic-batch", "bool", config_path="ImageMatch.gpu_dynamic_batch", default=True, entrypoints=(IMAGE_MATCH, FROM_ORI_MATCH), help="Enable dynamic GPU batch sizing."),
    _spec("gpu_min_batch_size", "execution", "--gpu-min-batch-size", "int", config_path="ImageMatch.gpu_min_batch_size", default=2, min_value=1, entrypoints=(IMAGE_MATCH, FROM_ORI_MATCH), help="Minimum dynamic GPU batch size."),
    _spec("gpu_max_batch_size", "execution", "--gpu-max-batch-size", "int", config_path="ImageMatch.gpu_max_batch_size", default=16, min_value=1, entrypoints=(IMAGE_MATCH, FROM_ORI_MATCH), help="Maximum dynamic GPU batch size."),
    _spec("write_match_visualization", "visualization", "--write-match-visualization", "bool", config_path="ImageMatch.write_match_visualization", default=True, entrypoints=(RUN_PIPELINE, IMAGE_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Write match visualization images."),
    _spec("match_visualization_output_path", "visualization", "--match-visualization-output-path", "path", entrypoints=(IMAGE_MATCH, FROM_DOM), help="Explicit visualization PNG path."),
    _spec("match_visualization_output_dir", "visualization", "--match-visualization-output-dir", "path", entrypoints=(RUN_PIPELINE, IMAGE_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Visualization PNG output directory."),
    _spec("match_visualization_scale", "visualization", "--match-visualization-scale", "float", config_path="ImageMatch.match_visualization_scale", default=1.0 / 3.0, min_value=0.0, entrypoints=(IMAGE_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Visualization scale factor."),
    _spec("visualization_mode", "visualization", "--visualization-mode", "choice", config_path="ImageMatch.visualization_mode", default=DEFAULT_VISUALIZATION_MODE, allowed_values=tuple(SUPPORTED_VISUALIZATION_MODES), entrypoints=(RUN_PIPELINE, IMAGE_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Visualization mode."),
    _spec("memory_profile", "visualization", "--memory-profile", "choice", config_path="ImageMatch.memory_profile", default=DEFAULT_MEMORY_PROFILE, allowed_values=tuple(SUPPORTED_MEMORY_PROFILES), entrypoints=(RUN_PIPELINE, IMAGE_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Visualization memory profile."),
    _spec("visualization_target_long_edge", "visualization", "--visualization-target-long-edge", "int", config_path="ImageMatch.visualization_target_long_edge", min_value=1, entrypoints=(RUN_PIPELINE, IMAGE_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Target long edge for reduced previews."),
    _spec("max_preview_pixels", "visualization", "--max-preview-pixels", "int", config_path="ImageMatch.max_preview_pixels", min_value=1, entrypoints=(IMAGE_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Maximum preview pixels."),
    _spec("preview_crop_margin_pixels", "visualization", "--preview-crop-margin-pixels", "int", config_path="ImageMatch.preview_crop_margin_pixels", default=DEFAULT_PREVIEW_CROP_MARGIN_PIXELS, min_value=0, entrypoints=(RUN_PIPELINE, IMAGE_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Preview crop margin."),
    _spec("preview_cache_dir", "visualization", "--preview-cache-dir", "path", config_path="ImageMatch.preview_cache_dir", entrypoints=(IMAGE_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Preview cache directory."),
    _spec("preview_cache_source", "visualization", "--preview-cache-source", "choice", config_path="ImageMatch.preview_cache_source", default=DEFAULT_PREVIEW_CACHE_SOURCE, allowed_values=tuple(SUPPORTED_PREVIEW_CACHE_SOURCES), entrypoints=(RUN_PIPELINE, IMAGE_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Preview cache source."),
    _spec("preview_force_regenerate", "visualization", "--preview-force-regenerate", "bool", default=False, entrypoints=(IMAGE_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Force preview cache regeneration."),
    _spec("preview_level", "visualization", "--preview-level", "int", min_value=0, entrypoints=(IMAGE_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Explicit reduced preview level."),
    _spec("pair_id", "controlnet", "--pair-id", "string", entrypoints=(FROM_ORI_MATCH, FROM_DOM), help="Explicit stereo pair ID."),
    _spec("pair_id_prefix", "controlnet", "--pair-id-prefix", "string", default="S", entrypoints=(RUN_PIPELINE, FROM_DOM_BATCH), help="Batch pair ID prefix."),
    _spec("pair_id_start", "controlnet", "--pair-id-start", "int", default=1, min_value=1, entrypoints=(RUN_PIPELINE, FROM_DOM_BATCH), help="Batch pair ID starting integer."),
    _spec("network_id", "controlnet", "--network-id", "string", config_path="NetworkId", entrypoints=(RUN_PIPELINE,), help="Merged network ID."),
    _spec("description", "controlnet", "--description", "string", config_path="Description", entrypoints=(RUN_PIPELINE,), help="Merged network description."),
    _spec("binary", "controlnet", "--binary", "bool", default=False, entrypoints=(FROM_ORI_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Write binary ControlNet."),
    _spec("merged_net", "controlnet", "--merged-net", "path", entrypoints=(RUN_PIPELINE,), help="Final merged ControlNet path."),
    _spec("merge_script", "controlnet", "--merge-script", "path", entrypoints=(RUN_PIPELINE,), help="Generated cnetmerge shell path."),
    _spec("merge_log", "controlnet", "--merge-log", "path", entrypoints=(RUN_PIPELINE,), help="cnetmerge log path."),
    _spec("pair_list", "controlnet", "--pair-list", "path", entrypoints=(RUN_PIPELINE,), help="cnetmerge pair list path."),
    _spec("cnetmerge", "controlnet", "--cnetmerge", "path", entrypoints=(RUN_PIPELINE,), help="cnetmerge executable path."),
    _spec("metadata_output", "reporting", "--metadata-output", "path", entrypoints=(IMAGE_MATCH,), help="ImageMatch metadata JSON path."),
    _spec("result_output", "reporting", "--result-output", "path", entrypoints=(IMAGE_MATCH,), help="ImageMatch full result JSON path."),
    _spec("report_path", "reporting", "--report-path", "path", entrypoints=(FROM_ORI_MATCH, FROM_DOM), help="Per-pair result report path."),
    _spec("report_dir", "reporting", "--report-dir", "path", entrypoints=(FROM_DOM_BATCH,), help="Batch report directory."),
    _spec("timing_json", "reporting", "--timing-json", "path", entrypoints=(RUN_PIPELINE,), help="Pipeline timing JSON path."),
    _spec("omit_tile_details", "reporting", "--omit-tile-details", "bool", config_path="ImageMatch.omit_tile_details", default=False, entrypoints=(IMAGE_MATCH,), help="Omit per-tile detail records from stdout."),
    _spec("omit_detail_records", "reporting", "--omit-detail-records", "bool", default=True, entrypoints=(FROM_ORI_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Omit verbose ControlNet detail records from stdout."),
    _spec("log_level", "reporting", "--log-level", "choice", default="INFO", allowed_values=("DEBUG", "INFO", "WARNING", "ERROR"), entrypoints=(FROM_ORI_MATCH, FROM_DOM, FROM_DOM_BATCH), help="Logging verbosity."),
    _spec("print_parameter_groups", "reporting", "--print-parameter-groups", "bool", default=False, entrypoints=(RUN_PIPELINE,), help="Print grouped parameter help and exit."),
    _spec("validate_parameters_only", "reporting", "--validate-parameters-only", "bool", default=False, entrypoints=(RUN_PIPELINE,), help="Validate effective parameters and exit before running pipeline steps."),
    _spec("strict_parameter_validation", "reporting", "--strict-parameter-validation", "bool", default=False, entrypoints=(RUN_PIPELINE,), help="Promote parameter warnings to errors."),
)


PARAMETER_BY_NAME: dict[str, ParameterSpec] = {parameter.name: parameter for parameter in PARAMETERS}
GROUP_BY_NAME: dict[str, ParameterGroup] = {group.name: group for group in PARAMETER_GROUPS}


def parameters_for_entrypoint(entrypoint: str) -> tuple[ParameterSpec, ...]:
    return tuple(parameter for parameter in PARAMETERS if entrypoint in parameter.entrypoints)


def grouped_parameters_for_entrypoint(entrypoint: str) -> dict[str, tuple[ParameterSpec, ...]]:
    grouped: dict[str, tuple[ParameterSpec, ...]] = {}
    entrypoint_parameters = parameters_for_entrypoint(entrypoint)
    for group in PARAMETER_GROUPS:
        members = tuple(parameter for parameter in entrypoint_parameters if parameter.group == group.name)
        if members:
            grouped[group.name] = members
    return grouped


def parameter_catalog_as_dict(*, entrypoint: str | None = None) -> dict[str, Any]:
    selected = PARAMETERS if entrypoint is None else parameters_for_entrypoint(entrypoint)
    return {
        "groups": [asdict(group) for group in PARAMETER_GROUPS],
        "parameters": [asdict(parameter) for parameter in selected],
    }
```

- [ ] **Step 4: Run catalog tests and commit**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test -v
```

Expected: PASS.

Commit:

```bash
git add examples/controlnet_construct/parameter_catalog.py tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py
git commit -m "feat: add ControlNet parameter catalog"
```

---

### Task 2: Add Validation Model, Precedence, Errors, and Warnings

**Files:**
- Create: `tests/unitTest/controlnet_construct_parameter_validation_unit_test.py`
- Create: `examples/controlnet_construct/parameter_validation.py`
- Modify: `examples/controlnet_construct/parameter_catalog.py`

- [ ] **Step 1: Write failing validation tests**

Create `tests/unitTest/controlnet_construct_parameter_validation_unit_test.py`:

```python
"""Tests for shared ControlNet parameter validation."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = PROJECT_ROOT / "examples"
if str(EXAMPLES_ROOT) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_ROOT))


class ControlNetParameterValidationUnitTest(unittest.TestCase):
    def test_cli_values_override_preset_config_and_defaults_with_provenance(self):
        from controlnet_construct.parameter_validation import validate_parameters

        result = validate_parameters(
            "run_pipeline_example",
            cli_values={"matcher_method": "flann", "num_worker_parallel_cpu": 12},
            config_values={"matcher_method": "bf", "num_worker_parallel_cpu": 4},
            preset_values={"matcher_method": "lightglue"},
        )

        self.assertFalse(result.has_errors)
        self.assertEqual(result.values["matcher_method"], "flann")
        self.assertEqual(result.provenance["matcher_method"], "cli")
        self.assertEqual(result.values["num_worker_parallel_cpu"], 12)
        self.assertEqual(result.provenance["num_worker_parallel_cpu"], "cli")

    def test_deep_matcher_requires_deep_config(self):
        from controlnet_construct.parameter_validation import validate_parameters

        result = validate_parameters("run_pipeline_example", cli_values={"matcher_method": "lightglue"})

        self.assertTrue(result.has_errors)
        self.assertIn("deep matcher", result.error_text())
        self.assertIn("deep_match_config_path", result.error_text())

    def test_match_preset_conflicts_with_explicit_matcher_and_deep_config(self):
        from controlnet_construct.parameter_validation import validate_parameters

        matcher_conflict = validate_parameters(
            "run_pipeline_example",
            cli_values={"match_preset_path": "preset.json", "matcher_method": "flann"},
        )
        config_conflict = validate_parameters(
            "run_pipeline_example",
            cli_values={"match_preset_path": "preset.json", "deep_match_config_path": "deep.json"},
        )

        self.assertIn("match_preset_path conflicts with matcher_method", matcher_conflict.error_text())
        self.assertIn("match_preset_path conflicts with deep_match_config_path", config_conflict.error_text())

    def test_inactive_low_resolution_warning_becomes_strict_error(self):
        from controlnet_construct.parameter_validation import validate_parameters

        result = validate_parameters(
            "run_pipeline_example",
            cli_values={
                "enable_low_resolution_offset_estimation": False,
                "low_resolution_level": 4,
            },
        )
        strict_result = validate_parameters(
            "run_pipeline_example",
            cli_values={
                "enable_low_resolution_offset_estimation": False,
                "low_resolution_level": 4,
                "strict_parameter_validation": True,
            },
        )

        self.assertFalse(result.has_errors)
        self.assertTrue(result.warnings)
        self.assertIn("low_resolution_level", result.warning_text())
        self.assertTrue(strict_result.has_errors)
        self.assertIn("strict parameter validation", strict_result.error_text())

    def test_gpu_batch_consistency_is_hard_error(self):
        from controlnet_construct.parameter_validation import validate_parameters

        result = validate_parameters(
            "image_match",
            cli_values={"gpu_min_batch_size": 8, "gpu_max_batch_size": 4},
        )

        self.assertTrue(result.has_errors)
        self.assertIn("gpu_min_batch_size", result.error_text())
        self.assertIn("gpu_max_batch_size", result.error_text())

    def test_shell_assignments_quote_normalized_values(self):
        from controlnet_construct.parameter_validation import validate_parameters

        result = validate_parameters(
            "run_pipeline_example",
            cli_values={"matcher_method": "bf", "work_dir": "work with space"},
        )

        text = result.to_shell_assignments(["matcher_method", "work_dir"])

        self.assertIn("MATCHER_METHOD=bf", text)
        self.assertIn("WORK_DIR='work with space'", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run failing validation tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_parameter_validation_unit_test -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'controlnet_construct.parameter_validation'`.

- [ ] **Step 3: Implement validation module**

Create `examples/controlnet_construct/parameter_validation.py`:

```python
"""Shared validation and normalization for ControlNet pipeline parameters."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
import shlex
from typing import Any

try:
    from .deep_match_config import load_deep_match_config
    from .parameter_catalog import PARAMETER_BY_NAME, parameters_for_entrypoint
except ImportError:
    from deep_match_config import load_deep_match_config
    from parameter_catalog import PARAMETER_BY_NAME, parameters_for_entrypoint


DEEP_MATCHER_METHODS = {"superglue", "lightglue", "loftr"}
ABSENT_VALUES = (None, "")


@dataclass(frozen=True, slots=True)
class ValidationMessage:
    field: str
    message: str


@dataclass(slots=True)
class ParameterValidationResult:
    entrypoint: str
    values: dict[str, Any]
    provenance: dict[str, str]
    warnings: list[ValidationMessage] = field(default_factory=list)
    errors: list[ValidationMessage] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def warning_text(self) -> str:
        return "\n".join(f"{warning.field}: {warning.message}" for warning in self.warnings)

    def error_text(self) -> str:
        return "\n".join(f"{error.field}: {error.message}" for error in self.errors)

    def to_shell_assignments(self, names: list[str] | tuple[str, ...] | None = None) -> str:
        selected_names = tuple(names) if names is not None else tuple(sorted(self.values))
        lines: list[str] = []
        for name in selected_names:
            if name not in self.values:
                continue
            value = self.values[name]
            shell_name = name.upper()
            if isinstance(value, bool):
                shell_value = "1" if value else "0"
            elif value is None:
                shell_value = ""
            else:
                shell_value = str(value)
            lines.append(f"{shell_name}={shlex.quote(shell_value)}")
        return "\n".join(lines)


def _present(value: Any) -> bool:
    return value not in ABSENT_VALUES


def _merge_values(
    entrypoint: str,
    *,
    cli_values: dict[str, Any],
    preset_values: dict[str, Any],
    config_values: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    values: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    for spec in parameters_for_entrypoint(entrypoint):
        for source_name, source_values in (
            ("cli", cli_values),
            ("preset", preset_values),
            ("config", config_values),
        ):
            if spec.name in source_values and _present(source_values[spec.name]):
                values[spec.name] = source_values[spec.name]
                provenance[spec.name] = source_name
                break
        else:
            values[spec.name] = spec.default
            provenance[spec.name] = "default"
    return values, provenance


def _coerce_choice(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def _validate_allowed_values(result: ParameterValidationResult) -> None:
    for spec in parameters_for_entrypoint(result.entrypoint):
        if not spec.allowed_values or not _present(result.values.get(spec.name)):
            continue
        normalized = _coerce_choice(result.values[spec.name])
        allowed = tuple(_coerce_choice(value) for value in spec.allowed_values)
        if normalized not in allowed:
            result.errors.append(
                ValidationMessage(
                    spec.name,
                    f"unsupported value {result.values[spec.name]!r}; allowed values are {', '.join(map(str, spec.allowed_values))}",
                )
            )
        else:
            result.values[spec.name] = normalized


def _validate_numeric_ranges(result: ParameterValidationResult) -> None:
    for spec in parameters_for_entrypoint(result.entrypoint):
        value = result.values.get(spec.name)
        if not _present(value) or spec.value_type not in {"int", "float"}:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            result.errors.append(ValidationMessage(spec.name, f"{spec.name} must be a finite {spec.value_type}."))
            continue
        if spec.value_type == "int" and not isinstance(value, int):
            result.errors.append(ValidationMessage(spec.name, f"{spec.name} must be an integer."))
            continue
        if spec.min_value is not None and value < spec.min_value:
            result.errors.append(ValidationMessage(spec.name, f"{spec.name} must be >= {spec.min_value}."))
        if spec.max_value is not None and value > spec.max_value:
            result.errors.append(ValidationMessage(spec.name, f"{spec.name} must be <= {spec.max_value}."))


def _validate_combinations(
    result: ParameterValidationResult,
    *,
    cli_values: dict[str, Any],
    strict: bool,
) -> None:
    values = result.values
    provenance = result.provenance

    if _present(cli_values.get("match_preset_path")) and _present(cli_values.get("matcher_method")):
        result.errors.append(ValidationMessage("match_preset_path", "match_preset_path conflicts with matcher_method."))
    if _present(cli_values.get("match_preset_path")) and _present(cli_values.get("deep_match_config_path")):
        result.errors.append(
            ValidationMessage("match_preset_path", "match_preset_path conflicts with deep_match_config_path.")
        )

    matcher_method = _coerce_choice(values.get("matcher_method", ""))
    deep_config_path = values.get("deep_match_config_path")
    if matcher_method in DEEP_MATCHER_METHODS:
        if not _present(deep_config_path):
            result.errors.append(
                ValidationMessage(
                    "deep_match_config_path",
                    f"deep matcher {matcher_method!r} requires deep_match_config_path.",
                )
            )
        elif Path(str(deep_config_path)).exists():
            try:
                load_deep_match_config(deep_config_path)
            except ValueError as exc:
                result.errors.append(ValidationMessage("deep_match_config_path", str(exc)))

    if values.get("deep_match_mode") == "import" and not _present(values.get("deep_match_manifest_dir")):
        result.errors.append(
            ValidationMessage("deep_match_manifest_dir", "deep_match_mode=import requires deep_match_manifest_dir.")
        )

    gpu_min = values.get("gpu_min_batch_size")
    gpu_max = values.get("gpu_max_batch_size")
    if isinstance(gpu_min, int) and isinstance(gpu_max, int) and gpu_min > gpu_max:
        result.errors.append(
            ValidationMessage(
                "gpu_min_batch_size",
                "gpu_min_batch_size must be <= gpu_max_batch_size.",
            )
        )

    if _present(values.get("left_low_resolution_dom")) != _present(values.get("right_low_resolution_dom")):
        result.errors.append(
            ValidationMessage(
                "left_low_resolution_dom",
                "left_low_resolution_dom and right_low_resolution_dom must be provided together.",
            )
        )

    if values.get("post_merge_control_measure") and values.get("skip_final_merge"):
        result.errors.append(
            ValidationMessage(
                "post_merge_control_measure",
                "post_merge_control_measure cannot be combined with skip_final_merge.",
            )
        )

    warning_specs = (
        (
            "enable_low_resolution_offset_estimation",
            False,
            (
                "low_resolution_level",
                "low_resolution_max_mean_reprojection_error_pixels",
                "low_resolution_min_retained_match_count",
                "low_resolution_max_mean_projected_offset_meters",
            ),
            "is set while low-resolution offset estimation is disabled.",
        ),
        ("use_gpu", False, ("gpu_batch_size", "gpu_dynamic_batch", "gpu_min_batch_size", "gpu_max_batch_size"), "is set while GPU execution is disabled."),
        ("use_parallel_cpu", False, ("num_worker_parallel_cpu",), "is set while CPU parallelism is disabled."),
    )
    for switch_name, inactive_value, dependent_names, message in warning_specs:
        if values.get(switch_name) != inactive_value:
            continue
        for dependent_name in dependent_names:
            if provenance.get(dependent_name) != "default" and _present(values.get(dependent_name)):
                result.warnings.append(ValidationMessage(dependent_name, f"{dependent_name} {message}"))

    if values.get("deep_match_mode") == "direct":
        for dependent_name in ("deep_match_temp_root_dir", "deep_match_manifest_dir", "deep_match_manifest_summary"):
            if provenance.get(dependent_name) != "default" and _present(values.get(dependent_name)):
                result.warnings.append(
                    ValidationMessage(dependent_name, f"{dependent_name} is set while deep_match_mode=direct.")
                )

    if not values.get("post_merge_control_measure"):
        for dependent_name in ("post_merge_output", "post_merge_decimals"):
            if provenance.get(dependent_name) != "default" and _present(values.get(dependent_name)):
                result.warnings.append(
                    ValidationMessage(dependent_name, f"{dependent_name} is set while post-merge is disabled.")
                )

    if strict and result.warnings:
        for warning in result.warnings:
            result.errors.append(
                ValidationMessage(
                    warning.field,
                    f"strict parameter validation treats warning as error: {warning.message}",
                )
            )


def validate_parameters(
    entrypoint: str,
    *,
    cli_values: dict[str, Any] | None = None,
    preset_values: dict[str, Any] | None = None,
    config_values: dict[str, Any] | None = None,
) -> ParameterValidationResult:
    resolved_cli = dict(cli_values or {})
    resolved_preset = dict(preset_values or {})
    resolved_config = dict(config_values or {})
    strict = bool(resolved_cli.get("strict_parameter_validation"))
    values, provenance = _merge_values(
        entrypoint,
        cli_values=resolved_cli,
        preset_values=resolved_preset,
        config_values=resolved_config,
    )
    result = ParameterValidationResult(entrypoint=entrypoint, values=values, provenance=provenance)
    _validate_allowed_values(result)
    _validate_numeric_ranges(result)
    _validate_combinations(result, cli_values=resolved_cli, strict=strict)
    return result
```

- [ ] **Step 4: Run validation tests and focused catalog tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test tests.unitTest.controlnet_construct_parameter_validation_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/controlnet_construct/parameter_catalog.py examples/controlnet_construct/parameter_validation.py tests/unitTest/controlnet_construct_parameter_validation_unit_test.py
git commit -m "feat: add ControlNet parameter validation"
```

---

### Task 3: Add Catalog CLI for Grouped Help and JSON Validation

**Files:**
- Modify: `tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py`
- Create: `examples/controlnet_construct/print_parameter_catalog.py`

- [ ] **Step 1: Add failing CLI tests**

Append these tests to `ControlNetParameterCatalogUnitTest` in `tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py`:

```python
    def test_catalog_cli_prints_grouped_pipeline_help(self):
        import subprocess

        command = [
            sys.executable,
            str(PROJECT_ROOT / "examples" / "controlnet_construct" / "print_parameter_catalog.py"),
            "--entrypoint",
            "run_pipeline_example",
            "--format",
            "text",
        ]
        result = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Matching", result.stdout)
        self.assertIn("--matcher-method", result.stdout)
        self.assertIn("Low Resolution", result.stdout)
        self.assertIn("--low-resolution-level", result.stdout)

    def test_catalog_cli_validates_payload_json(self):
        import json
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory(prefix="parameter_catalog_cli_") as temp_dir:
            payload_path = Path(temp_dir) / "payload.json"
            payload_path.write_text(
                json.dumps(
                    {
                        "entrypoint": "run_pipeline_example",
                        "cli_values": {
                            "matcher_method": "bf",
                            "work_dir": "work with space",
                            "validate_parameters_only": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "examples" / "controlnet_construct" / "print_parameter_catalog.py"),
                    "--validate-json",
                    str(payload_path),
                    "--shell-assignments",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("MATCHER_METHOD=bf", result.stdout)
        self.assertIn("WORK_DIR='work with space'", result.stdout)
```

- [ ] **Step 2: Run failing CLI tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test -v
```

Expected: FAIL because `print_parameter_catalog.py` is missing.

- [ ] **Step 3: Implement `print_parameter_catalog.py`**

Create `examples/controlnet_construct/print_parameter_catalog.py`:

```python
"""Print and validate the shared ControlNet parameter catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.parameter_catalog import (
        GROUP_BY_NAME,
        grouped_parameters_for_entrypoint,
        parameter_catalog_as_dict,
    )
    from controlnet_construct.parameter_validation import validate_parameters
else:
    from .parameter_catalog import GROUP_BY_NAME, grouped_parameters_for_entrypoint, parameter_catalog_as_dict
    from .parameter_validation import validate_parameters


def _format_allowed_values(values: tuple[Any, ...]) -> str:
    return ", ".join(str(value).replace("_", "-") for value in values)


def format_grouped_help(entrypoint: str) -> str:
    lines: list[str] = [f"Parameter groups for {entrypoint}", ""]
    for group_name, parameters in grouped_parameters_for_entrypoint(entrypoint).items():
        group = GROUP_BY_NAME[group_name]
        lines.append(group.title)
        lines.append("-" * len(group.title))
        lines.append(group.description)
        for parameter in parameters:
            display_name = parameter.cli_flag or parameter.name
            details: list[str] = []
            if parameter.allowed_values:
                details.append(f"values: {_format_allowed_values(parameter.allowed_values)}")
            if parameter.config_path:
                details.append(f"config: {parameter.config_path}")
            if parameter.default is not None:
                details.append(f"default: {parameter.default}")
            suffix = f" ({'; '.join(details)})" if details else ""
            lines.append(f"  {display_name}: {parameter.help}{suffix}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _load_validation_payload(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("validation payload must be a JSON object")
    return payload


def _print_validation(payload: dict[str, Any], *, shell_assignments: bool) -> int:
    entrypoint = str(payload.get("entrypoint") or "run_pipeline_example")
    result = validate_parameters(
        entrypoint,
        cli_values=dict(payload.get("cli_values") or {}),
        preset_values=dict(payload.get("preset_values") or {}),
        config_values=dict(payload.get("config_values") or {}),
    )
    for warning in result.warnings:
        print(f"warning: {warning.field}: {warning.message}", file=sys.stderr)
    if result.has_errors:
        for error in result.errors:
            print(f"error: {error.field}: {error.message}", file=sys.stderr)
        return 2
    if shell_assignments:
        print(result.to_shell_assignments())
    else:
        print(json.dumps({"values": result.values, "provenance": result.provenance}, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrypoint", default="run_pipeline_example")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--validate-json", default=None)
    parser.add_argument("--shell-assignments", action="store_true")
    args = parser.parse_args(argv)

    if args.validate_json is not None:
        try:
            return _print_validation(_load_validation_payload(args.validate_json), shell_assignments=args.shell_assignments)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            parser.error(str(exc))

    if args.format == "json":
        print(json.dumps(parameter_catalog_as_dict(entrypoint=args.entrypoint), indent=2, sort_keys=True))
    else:
        print(format_grouped_help(args.entrypoint), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run catalog CLI tests and commit**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test tests.unitTest.controlnet_construct_parameter_validation_unit_test -v
```

Expected: PASS.

Commit:

```bash
git add examples/controlnet_construct/print_parameter_catalog.py tests/unitTest/controlnet_construct_parameter_catalog_unit_test.py
git commit -m "feat: expose ControlNet parameter catalog CLI"
```

---

### Task 4: Connect `run_pipeline_example.sh` Validation-Only and Grouped Help

**Files:**
- Modify: `tests/unitTest/controlnet_construct_pipeline_unit_test.py`
- Modify: `examples/controlnet_construct/run_pipeline_example.sh`

- [ ] **Step 1: Add failing shell-wrapper tests**

Append these tests to `ControlNetConstructPipelineUnitTest` in `tests/unitTest/controlnet_construct_pipeline_unit_test.py`:

```python
    def test_run_pipeline_example_prints_parameter_groups(self):
        completed = subprocess.run(
            [
                "bash",
                str(RUN_PIPELINE_EXAMPLE_PATH),
                "--print-parameter-groups",
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Parameter groups for run_pipeline_example", completed.stdout)
        self.assertIn("Matching", completed.stdout)
        self.assertIn("--matcher-method", completed.stdout)
        self.assertIn("Low Resolution", completed.stdout)

    def test_run_pipeline_example_validate_parameters_only_reports_effective_values(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()
            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            original_list.write_text("left.cub\nright.cub\n", encoding="utf-8")
            dom_list.write_text("left_dom.cub\nright_dom.cub\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "unit",
                        "TargetName": "Moon",
                        "UserName": "unit",
                        "ImageMatch": {
                            "matcher_method": "bf",
                            "num_worker_parallel_cpu": 3,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
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

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Parameter validation passed", completed.stdout)
        self.assertIn("MATCHER_METHOD=bf", completed.stdout)
        self.assertIn("NUM_WORKER_PARALLEL_CPU=3", completed.stdout)
        self.assertNotIn("Step 1/", completed.stdout)

    def test_run_pipeline_example_strict_parameter_validation_promotes_warning(self):
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()
            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            original_list.write_text("left.cub\nright.cub\n", encoding="utf-8")
            dom_list.write_text("left_dom.cub\nright_dom.cub\n", encoding="utf-8")
            config_path = temp_dir / "controlnet_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "unit",
                        "TargetName": "Moon",
                        "UserName": "unit",
                        "ImageMatch": {"matcher_method": "bf"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    "bash",
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--low-resolution-level",
                    "4",
                    "--strict-parameter-validation",
                    "--validate-parameters-only",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("strict parameter validation", completed.stderr)
        self.assertIn("low_resolution_level", completed.stderr)
```

- [ ] **Step 2: Run failing wrapper tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: FAIL because the new wrapper flags are not parsed.

- [ ] **Step 3: Add shell flags and validation payload helper**

Modify `examples/controlnet_construct/run_pipeline_example.sh`:

Add defaults near existing defaults in `main()`:

```bash
  PRINT_PARAMETER_GROUPS="0"
  VALIDATE_PARAMETERS_ONLY="0"
  STRICT_PARAMETER_VALIDATION="0"
```

Add cases in the argument parser:

```bash
      --print-parameter-groups)
        PRINT_PARAMETER_GROUPS="1"
        shift
        ;;
      --validate-parameters-only)
        VALIDATE_PARAMETERS_ONLY="1"
        shift
        ;;
      --strict-parameter-validation)
        STRICT_PARAMETER_VALIDATION="1"
        shift
        ;;
```

Add an early grouped-help exit after `require_command "$PYTHON_EXECUTABLE"` and `cd "$REPO_ROOT"`:

```bash
  if [[ "$PRINT_PARAMETER_GROUPS" == "1" ]]; then
    "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/print_parameter_catalog.py" \
      --entrypoint run_pipeline_example \
      --format text
    return 0
  fi
```

Add a helper before `main()`:

```bash
validate_controlnet_parameters() {
  local payload_path=$1
  "$PYTHON_EXECUTABLE" "$REPO_ROOT/examples/controlnet_construct/print_parameter_catalog.py" \
    --validate-json "$payload_path" \
    --shell-assignments
}
```

After config and preset defaults are resolved, write a payload and eval normalized assignments. The payload must preserve source precedence: only fields explicitly set by this shell invocation go in `cli_values`; values read from config go in `config_values`; preset-expanded values go in `preset_values`.

```bash
  PARAMETER_VALIDATION_PAYLOAD="$REPORTS_DIR/parameter_validation_payload.json"
  "$PYTHON_EXECUTABLE" - "$PARAMETER_VALIDATION_PAYLOAD" <<PY
import json
import os
import sys
from pathlib import Path

def put_if_present(mapping, key, value):
    if value not in (None, ""):
        mapping[key] = value

def put_bool_if_explicit(mapping, key, explicit_env, value_env):
    if os.environ.get(explicit_env):
        mapping[key] = os.environ.get(value_env) == "1"

def put_int_if_explicit(mapping, key, explicit_env, value_env):
    if os.environ.get(explicit_env):
        mapping[key] = int(os.environ[value_env])

def put_float_if_explicit(mapping, key, explicit_env, value_env):
    if os.environ.get(explicit_env):
        mapping[key] = float(os.environ[value_env])

payload_path = Path(sys.argv[1])
payload_path.parent.mkdir(parents=True, exist_ok=True)
cli_values = {}
config_values = {}
preset_values = {}

put_if_present(cli_values, "work_dir", os.environ.get("WORK_DIR"))
put_if_present(cli_values, "match_preset_path", os.environ.get("EXPLICIT_MATCH_PRESET_PATH"))
put_if_present(cli_values, "matcher_method", os.environ.get("EXPLICIT_MATCHER_METHOD"))
put_if_present(cli_values, "deep_match_config_path", os.environ.get("EXPLICIT_DEEP_MATCHER_CONFIG_PATH"))
put_if_present(cli_values, "deep_match_mode", os.environ.get("EXPLICIT_DEEP_MATCH_MODE"))
put_if_present(cli_values, "deep_match_temp_root_dir", os.environ.get("EXPLICIT_DEEP_MATCH_TEMP_ROOT_DIR"))
put_if_present(cli_values, "deep_match_manifest_dir", os.environ.get("EXPLICIT_DEEP_MATCH_MANIFEST_DIR"))
put_if_present(cli_values, "deep_match_manifest_summary", os.environ.get("EXPLICIT_DEEP_MATCH_MANIFEST_SUMMARY"))
put_bool_if_explicit(cli_values, "enable_low_resolution_offset_estimation", "EXPLICIT_ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION", "ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION")
put_int_if_explicit(cli_values, "low_resolution_level", "EXPLICIT_LOW_RESOLUTION_LEVEL", "LOW_RESOLUTION_LEVEL")
put_float_if_explicit(cli_values, "low_resolution_max_mean_reprojection_error_pixels", "EXPLICIT_LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS", "LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS")
put_int_if_explicit(cli_values, "low_resolution_min_retained_match_count", "EXPLICIT_LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT", "LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT")
put_float_if_explicit(cli_values, "low_resolution_max_mean_projected_offset_meters", "EXPLICIT_LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS", "LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS")
put_bool_if_explicit(cli_values, "enable_adaptive_routing", "EXPLICIT_ADAPTIVE_ROUTING", "ADAPTIVE_ROUTING")
put_if_present(cli_values, "adaptive_routing_profile", os.environ.get("EXPLICIT_ADAPTIVE_ROUTING_PROFILE"))
put_bool_if_explicit(cli_values, "use_parallel_cpu", "EXPLICIT_USE_PARALLEL_CPU", "USE_PARALLEL_CPU")
put_int_if_explicit(cli_values, "num_worker_parallel_cpu", "EXPLICIT_NUM_WORKER_PARALLEL_CPU", "NUM_WORKER_PARALLEL_CPU")
put_if_present(cli_values, "visualization_mode", os.environ.get("EXPLICIT_VISUALIZATION_MODE"))
put_if_present(cli_values, "memory_profile", os.environ.get("EXPLICIT_MEMORY_PROFILE"))
put_if_present(cli_values, "visualization_target_long_edge", os.environ.get("EXPLICIT_VISUALIZATION_TARGET_LONG_EDGE"))
put_int_if_explicit(cli_values, "preview_crop_margin_pixels", "EXPLICIT_PREVIEW_CROP_MARGIN_PIXELS", "PREVIEW_CROP_MARGIN_PIXELS")
put_if_present(cli_values, "preview_cache_source", os.environ.get("EXPLICIT_PREVIEW_CACHE_SOURCE"))
cli_values["skip_final_merge"] = os.environ.get("SKIP_FINAL_MERGE") == "1"
cli_values["post_merge_control_measure"] = os.environ.get("POST_MERGE_CONTROL_MEASURE") == "1"
put_if_present(cli_values, "post_merge_output", os.environ.get("POST_MERGE_OUTPUT_PATH"))
cli_values["post_merge_decimals"] = int(os.environ.get("POST_MERGE_DECIMALS") or "1")
cli_values["strict_parameter_validation"] = os.environ.get("STRICT_PARAMETER_VALIDATION") == "1"
cli_values["validate_parameters_only"] = os.environ.get("VALIDATE_PARAMETERS_ONLY") == "1"

put_if_present(config_values, "matcher_method", os.environ.get("CONFIG_MATCHER_METHOD"))
put_if_present(config_values, "deep_match_config_path", os.environ.get("CONFIG_DEEP_MATCHER_CONFIG_PATH"))
put_if_present(config_values, "adaptive_routing_profile", os.environ.get("CONFIG_ADAPTIVE_ROUTING_PROFILE"))
put_if_present(config_values, "visualization_mode", os.environ.get("CONFIG_VISUALIZATION_MODE"))
put_if_present(config_values, "memory_profile", os.environ.get("CONFIG_MEMORY_PROFILE"))
put_if_present(config_values, "preview_cache_source", os.environ.get("CONFIG_PREVIEW_CACHE_SOURCE"))
put_if_present(preset_values, "match_preset_path", os.environ.get("MATCH_PRESET_PATH"))
put_if_present(preset_values, "matcher_method", os.environ.get("MATCH_PRESET_MATCHER_METHOD"))
put_if_present(preset_values, "deep_match_config_path", os.environ.get("MATCH_PRESET_DEEP_MATCHER_CONFIG_PATH"))

payload = {
    "entrypoint": "run_pipeline_example",
    "cli_values": cli_values,
    "config_values": config_values,
    "preset_values": preset_values,
}
payload_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
  validation_assignments=$(validate_controlnet_parameters "$PARAMETER_VALIDATION_PAYLOAD")
  eval "$validation_assignments"
  if [[ "$VALIDATE_PARAMETERS_ONLY" == "1" ]]; then
    log "Parameter validation passed"
    printf '%s\n' "$validation_assignments"
    return 0
  fi
```

Before running the Python payload writer, export the shell values it reads:

```bash
  export WORK_DIR MATCHER_METHOD MATCH_PRESET_PATH DEEP_MATCHER_CONFIG_PATH DEEP_MATCH_MODE
  export DEEP_MATCH_TEMP_ROOT_DIR DEEP_MATCH_MANIFEST_DIR DEEP_MATCH_MANIFEST_SUMMARY
  export SKIP_FINAL_MERGE POST_MERGE_CONTROL_MEASURE POST_MERGE_OUTPUT_PATH POST_MERGE_DECIMALS
  export ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION LOW_RESOLUTION_LEVEL
  export LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT
  export LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS ADAPTIVE_ROUTING ADAPTIVE_ROUTING_PROFILE
  export USE_PARALLEL_CPU NUM_WORKER_PARALLEL_CPU VISUALIZATION_MODE MEMORY_PROFILE
  export VISUALIZATION_TARGET_LONG_EDGE PREVIEW_CROP_MARGIN_PIXELS PREVIEW_CACHE_SOURCE
  export STRICT_PARAMETER_VALIDATION VALIDATE_PARAMETERS_ONLY
  export EXPLICIT_MATCH_PRESET_PATH EXPLICIT_MATCHER_METHOD EXPLICIT_DEEP_MATCHER_CONFIG_PATH
  export EXPLICIT_DEEP_MATCH_MODE EXPLICIT_DEEP_MATCH_TEMP_ROOT_DIR EXPLICIT_DEEP_MATCH_MANIFEST_DIR
  export EXPLICIT_DEEP_MATCH_MANIFEST_SUMMARY EXPLICIT_ENABLE_LOW_RESOLUTION_OFFSET_ESTIMATION
  export EXPLICIT_LOW_RESOLUTION_LEVEL EXPLICIT_LOW_RESOLUTION_MAX_MEAN_REPROJECTION_ERROR_PIXELS
  export EXPLICIT_LOW_RESOLUTION_MIN_RETAINED_MATCH_COUNT EXPLICIT_LOW_RESOLUTION_MAX_MEAN_PROJECTED_OFFSET_METERS
  export EXPLICIT_ADAPTIVE_ROUTING EXPLICIT_ADAPTIVE_ROUTING_PROFILE EXPLICIT_USE_PARALLEL_CPU
  export EXPLICIT_NUM_WORKER_PARALLEL_CPU EXPLICIT_VISUALIZATION_MODE EXPLICIT_MEMORY_PROFILE
  export EXPLICIT_VISUALIZATION_TARGET_LONG_EDGE EXPLICIT_PREVIEW_CROP_MARGIN_PIXELS EXPLICIT_PREVIEW_CACHE_SOURCE
  export CONFIG_MATCHER_METHOD CONFIG_DEEP_MATCHER_CONFIG_PATH CONFIG_ADAPTIVE_ROUTING_PROFILE
  export CONFIG_VISUALIZATION_MODE CONFIG_MEMORY_PROFILE CONFIG_PREVIEW_CACHE_SOURCE
  export MATCH_PRESET_MATCHER_METHOD MATCH_PRESET_DEEP_MATCHER_CONFIG_PATH
```

- [ ] **Step 4: Run focused wrapper tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_pipeline_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/controlnet_construct/run_pipeline_example.sh tests/unitTest/controlnet_construct_pipeline_unit_test.py
git commit -m "feat: validate ControlNet pipeline parameters"
```

---

### Task 5: Reuse Shared Validators in `image_match.py`

**Files:**
- Modify: `examples/image_match/image_match.py`
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Add compatibility assertions around existing parser behavior**

Add this test method to `ControlNetConstructMatchingUnitTest` in `tests/unitTest/controlnet_construct_matching_unit_test.py`:

```python
    def test_image_match_parser_uses_shared_parameter_value_rules(self):
        parser = build_controlnet_stereopair_argument_parser()

        valid_args = parser.parse_args(
            [
                "left.cub",
                "right.cub",
                "left.key",
                "right.key",
                "--matcher-method",
                "lightglue",
                "--deep-match-mode",
                "export",
                "--adaptive-routing-profile",
                "relaxed",
                "--visualization-mode",
                "reduced-cropped",
                "--memory-profile",
                "low-memory",
                "--preview-cache-source",
                "matching-cache",
            ]
        )

        self.assertEqual(valid_args.matcher_method, "lightglue")
        self.assertEqual(valid_args.deep_match_mode, "export")
        self.assertEqual(valid_args.adaptive_routing_profile, "relaxed")
        self.assertEqual(valid_args.visualization_mode, "reduced_cropped")
        self.assertEqual(valid_args.memory_profile, "low-memory")
        self.assertEqual(valid_args.preview_cache_source, "matching_cache")

        for flag, value in (
            ("--matcher-method", "unknown"),
            ("--deep-match-mode", "bad"),
            ("--adaptive-routing-profile", "bad"),
            ("--visualization-mode", "bad"),
            ("--memory-profile", "bad"),
            ("--preview-cache-source", "bad"),
        ):
            with self.subTest(flag=flag, value=value), self.assertRaises(SystemExit):
                parser.parse_args(["left.cub", "right.cub", "left.key", "right.key", flag, value])
```

- [ ] **Step 2: Run matching parser tests before refactor**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Expected: PASS before implementation refactor. This is a characterization test, not a red test.

- [ ] **Step 3: Add shared parse helpers**

Modify `examples/controlnet_construct/parameter_validation.py` by appending:

```python
def parse_catalog_choice(field_name: str, value: str) -> str:
    spec = PARAMETER_BY_NAME[field_name]
    normalized = _coerce_choice(value)
    allowed = tuple(_coerce_choice(candidate) for candidate in spec.allowed_values)
    if normalized not in allowed:
        raise ValueError(
            f"{field_name} must be one of {', '.join(str(candidate) for candidate in spec.allowed_values)}."
        )
    return normalized


def parse_catalog_number(field_name: str, value: str) -> int | float:
    spec = PARAMETER_BY_NAME[field_name]
    try:
        parsed: int | float = int(value) if spec.value_type == "int" else float(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a {spec.value_type}.") from exc
    if isinstance(parsed, bool) or not math.isfinite(float(parsed)):
        raise ValueError(f"{field_name} must be finite.")
    if spec.min_value is not None and parsed < spec.min_value:
        raise ValueError(f"{field_name} must be >= {spec.min_value}.")
    if spec.max_value is not None and parsed > spec.max_value:
        raise ValueError(f"{field_name} must be <= {spec.max_value}.")
    return parsed
```

Modify `examples/image_match/image_match.py` imports near the existing conditional imports:

```python
    from controlnet_construct.parameter_validation import parse_catalog_choice, parse_catalog_number
```

and in the package import branch:

```python
    from controlnet_construct.parameter_validation import parse_catalog_choice, parse_catalog_number
```

Replace the overlapping parser helpers with shared calls:

```python
def _parse_visualization_mode(value: str) -> str:
    try:
        return parse_catalog_choice("visualization_mode", value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_memory_profile(value: str) -> str:
    try:
        return parse_catalog_choice("memory_profile", value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_preview_cache_source(value: str) -> str:
    try:
        return parse_catalog_choice("preview_cache_source", value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_adaptive_routing_profile(value: str) -> str:
    try:
        return parse_catalog_choice("adaptive_routing_profile", value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_matcher_method(value: str) -> str:
    try:
        return parse_catalog_choice("matcher_method", value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_deep_match_mode(value: str) -> str:
    try:
        return parse_catalog_choice("deep_match_mode", value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
```

Keep existing low-resolution specialized helpers where they call domain code. Do not remove `_validate_low_resolution_dom_pair_args`.

- [ ] **Step 4: Run matching and catalog tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test tests.unitTest.controlnet_construct_parameter_catalog_unit_test tests.unitTest.controlnet_construct_parameter_validation_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/image_match/image_match.py examples/controlnet_construct/parameter_validation.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "refactor: share image match parameter validation"
```

---

### Task 6: Reuse Shared Validators in `controlnet_stereopair.py`

**Files:**
- Modify: `examples/controlnet_construct/controlnet_stereopair.py`
- Modify: `tests/unitTest/controlnet_construct_matching_unit_test.py`

- [ ] **Step 1: Add parser compatibility test for ControlNet stereo-pair options**

Add this test method to `ControlNetConstructMatchingUnitTest`:

```python
    def test_controlnet_stereopair_parser_uses_shared_visualization_rules(self):
        parser = build_controlnet_stereopair_argument_parser()

        parsed = parser.parse_args(
            [
                "from-dom-batch",
                "overlap.lis",
                "original.lis",
                "doms.lis",
                "dom_keys",
                "config.json",
                "pair_nets",
                "--visualization-mode",
                "reduced-cropped",
                "--memory-profile",
                "low-memory",
                "--preview-cache-source",
                "matching-cache",
            ]
        )

        self.assertEqual(parsed.visualization_mode, "reduced_cropped")
        self.assertEqual(parsed.memory_profile, "low-memory")
        self.assertEqual(parsed.preview_cache_source, "matching_cache")

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "from-dom-batch",
                    "overlap.lis",
                    "original.lis",
                    "doms.lis",
                    "dom_keys",
                    "config.json",
                    "pair_nets",
                    "--visualization-mode",
                    "bad",
                ]
            )
```

- [ ] **Step 2: Run characterization test**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test -v
```

Expected: PASS before refactor.

- [ ] **Step 3: Replace local visualization parse helpers**

Modify `examples/controlnet_construct/controlnet_stereopair.py` imports:

```python
    from controlnet_construct.parameter_validation import parse_catalog_choice
```

and in the package branch:

```python
    from .parameter_validation import parse_catalog_choice
```

Replace the three local parsing helpers:

```python
def _parse_visualization_mode(value: str) -> str:
    try:
        return parse_catalog_choice("visualization_mode", value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_memory_profile(value: str) -> str:
    try:
        return parse_catalog_choice("memory_profile", value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_preview_cache_source(value: str) -> str:
    try:
        return parse_catalog_choice("preview_cache_source", value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_matching_unit_test tests.unitTest.controlnet_construct_parameter_catalog_unit_test tests.unitTest.controlnet_construct_parameter_validation_unit_test -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/controlnet_construct/controlnet_stereopair.py tests/unitTest/controlnet_construct_matching_unit_test.py
git commit -m "refactor: share ControlNet stereo parameter validation"
```

---

### Task 7: Document the Grouped Parameter Workflow

**Files:**
- Modify: `examples/controlnet_construct/PRESETS_README.md`
- Modify: `docs/superpowers/specs/2026-05-23-controlnet-parameter-catalog-design.md`

- [ ] **Step 1: Add documentation section**

Append this section to `examples/controlnet_construct/PRESETS_README.md`:

```markdown
## Parameter Groups and Preflight Validation

The end-to-end ControlNet pipeline exposes many options because it coordinates
overlap discovery, DOM matching, low-resolution offset estimation, adaptive
routing, visualization, pairwise ControlNet construction, and final merging.

Use grouped help when choosing parameters:

```bash
bash examples/controlnet_construct/run_pipeline_example.sh --print-parameter-groups
```

Use validation-only mode before running expensive matching work:

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir work \
  --config examples/controlnet_construct/controlnet_config.example.json \
  --validate-parameters-only
```

The effective-value precedence is:

```text
explicit CLI value > match preset value > config JSON value > entrypoint default
```

Default validation fails on invalid combinations such as a deep matcher without
a deep matcher preset, `--match-preset-path` combined with explicit matcher
overrides, `--deep-match-mode import` without a manifest source, or an invalid
GPU batch range. Inactive options such as low-resolution thresholds while
low-resolution offset estimation is disabled are warnings by default.

Use strict mode in repeatable runs:

```bash
bash examples/controlnet_construct/run_pipeline_example.sh \
  --work-dir work \
  --config examples/controlnet_construct/controlnet_config.example.json \
  --strict-parameter-validation \
  --validate-parameters-only
```
```

Append this implementation note to `docs/superpowers/specs/2026-05-23-controlnet-parameter-catalog-design.md`:

```markdown
## Implementation Note

The implementation plan is stored at
`docs/superpowers/plans/2026-05-23-controlnet-parameter-catalog.md`.
```

- [ ] **Step 2: Run doc syntax and focused tests**

Run:

```bash
git diff --check
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test tests.unitTest.controlnet_construct_parameter_validation_unit_test -v
```

Expected: `git diff --check` exits 0 and tests PASS.

- [ ] **Step 3: Commit**

```bash
git add examples/controlnet_construct/PRESETS_README.md docs/superpowers/specs/2026-05-23-controlnet-parameter-catalog-design.md
git commit -m "docs: document ControlNet parameter validation"
```

---

### Task 8: Final Verification

**Files:**
- Read-only verification across modified files.

- [ ] **Step 1: Run the targeted verification suite**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python -m unittest \
  tests.unitTest.controlnet_construct_parameter_catalog_unit_test \
  tests.unitTest.controlnet_construct_parameter_validation_unit_test \
  tests.unitTest.controlnet_construct_pipeline_unit_test \
  tests.unitTest.controlnet_construct_matching_unit_test \
  -v
```

Expected: PASS for all listed modules.

- [ ] **Step 2: Run smoke import**

Run:

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate asp360_new
export PYTHONPATH="$PWD/build/python:$PWD/tests/unitTest"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
python tests/smoke_import.py
```

Expected: exit code 0.

- [ ] **Step 3: Check worktree state**

Run:

```bash
git status --short --branch
git log --oneline -n 8
```

Expected: clean working tree on the feature branch, with the task commits visible.

- [ ] **Step 4: Prepare completion summary**

Report:

```text
Implemented shared ControlNet parameter catalog and validation.
Verified with:
- python -m unittest tests.unitTest.controlnet_construct_parameter_catalog_unit_test tests.unitTest.controlnet_construct_parameter_validation_unit_test tests.unitTest.controlnet_construct_pipeline_unit_test tests.unitTest.controlnet_construct_matching_unit_test -v
- python tests/smoke_import.py
```
