# ControlNet Construct Example Code Review Design

## Problem

`examples/controlnet_construct/` now contains a functional DOM matching ControlNet construction workflow, but the workflow has grown across Python modules, shell wrappers, JSON configuration, reports, and tests. The review goal is to judge whether the current code remains clear and to identify focused improvement areas without changing behavior prematurely.

## Current assessment

The code is generally clear and logically organized. The end-to-end workflow is understandable from `examples/controlnet_construct/usage.md`:

1. `image_overlap.py` finds overlapping original-image pairs.
2. `image_match.py` matches paired DOM cubes and writes DOM-space `.key` files.
3. `controlnet_stereopair.py from-dom-batch` merges duplicates, applies RANSAC, converts DOM coordinates to original-image coordinates, and writes pairwise ControlNets.
4. `controlnet_merge.py` generates a `cnetmerge` shell script for the pairwise networks.
5. `merge_control_measure.py` can optionally post-process the merged network.

The workflow is strongest where it has explicit intermediate products: DOM keys, pre/post-RANSAC visualizations, metadata sidecars, batch summaries, timing JSON, pairwise `.net` files, and a generated merge script. These artifacts make the pipeline easier to debug than a single opaque command.

## What is already clear

| Area | Assessment |
| --- | --- |
| Pipeline shape | The stage order is explicit and matches the usage documentation. |
| Module boundaries | Matching, low-resolution offset estimation, tile matching, RANSAC, visualization, DOM-to-original conversion, and merge-script generation are mostly separated. |
| Coordinate semantics | Coordinate-basis metadata and conventions help avoid 0-based/1-based sample-line ambiguity. |
| Diagnostics | JSON sidecars, timing summaries, and visualizations make failures inspectable. |
| Regression coverage | Focused unit tests cover matching, pipeline wrappers, DOM-to-original conversion, coordinate conventions, and optional E2E paths. |

## Improvement opportunities

### 1. Reduce duplicated config parsing in shell wrappers

`run_pipeline_example.sh` and `run_image_match_batch_example.sh` repeat many small Python here-doc extractors for `ImageMatch` fields. This duplicates logic already present in `image_match.py` and creates a synchronization risk for defaults, aliases, and validation.

Recommended direction: move shared config extraction into a Python helper or CLI entrypoint and let shell scripts only orchestrate files and commands.

### 2. Replace long parameter chains with option objects

`image_match.py` and `controlnet_stereopair.py` are understandable but still rely on long argument lists and repeated CLI-to-function forwarding. This makes it easy to forget a parameter when adding a new option.

Recommended direction: introduce small dataclass option objects such as `ImageMatchOptions`, `LowResolutionOffsetOptions`, and `DomControlNetOptions`, then pass those through internal functions.

### 3. Keep one source of truth for defaults

Several defaults are reflected in multiple places: Python CLI defaults, JSON example config, shell wrapper defaults, and usage documentation. The current state works, but every new option increases drift risk.

Recommended direction: make Python constants/dataclasses the authoritative defaults. Shell and docs should either read from Python helpers or explicitly state that they mirror Python defaults.

### 4. Split `from-dom` into smaller pipeline stages

`build_controlnet_for_dom_stereo_pair()` has a clear order, but it performs duplicate merge, RANSAC, optional visualization, DOM-to-original conversion, and ControlNet writing in one function.

Recommended direction: keep the public API stable, but extract internal stage helpers with clear inputs and result dictionaries. This preserves behavior while making each stage easier to test and reason about.

### 5. Keep generated files out of the example tree

The example directory contains `__pycache__` outputs in the working tree. These are not part of the intended workflow and distract from the source layout.

Recommended direction: ensure generated Python cache files are ignored and remove them from the working tree if they are tracked or accidentally staged.

## Recommended implementation sequence

1. **Config helper first**: add a Python-side config/default extraction helper and update shell wrappers to use it. This has the highest maintainability payoff and lowest conceptual risk.
2. **Option dataclasses second**: refactor `image_match.py` and `controlnet_stereopair.py` internal parameter passing without changing public CLI behavior.
3. **Stage extraction third**: split the DOM-to-ControlNet chain into named internal stages while preserving existing public functions and tests.
4. **Cleanup last**: remove or ignore generated cache artifacts and update documentation only where behavior or maintenance entrypoints change.

## Behavior and compatibility constraints

- Preserve current public CLI flags, especially the kebab-case option names.
- Preserve the current default pipeline outputs and directory layout under `work/`.
- Preserve JSON report fields unless a migration is explicitly documented.
- Keep focused tests for shell argument forwarding, config precedence, and stage result summaries.
- Do not change matching, RANSAC, or coordinate-conversion semantics during the first cleanup step.

## Testing strategy

Use the existing focused tests before broad validation:

1. Run pipeline-wrapper tests that assert shell forwarding and timing JSON behavior.
2. Run matching tests that cover config defaults, matcher selection, CPU parallel flags, and low-resolution offset gates.
3. Run DOM-to-original and coordinate-convention tests after any stage extraction.
4. Run optional E2E tests only when the external data environment is configured.

## Decision

Proceed with documentation and planning before implementation. The current code is not confused or broken, but it is at the point where future feature additions should first reduce orchestration duplication and parameter plumbing. The next step is to write an implementation plan for the config-helper cleanup, then apply later refactors incrementally.
