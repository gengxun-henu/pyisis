# Tile-Level Physical Illumination Adaptive Routing Plan

## Goal

Redesign the LRO NAC adaptive-routing benchmark so matcher selection can use tile-level physical solar geometry instead of pair-level or grayscale-proxy lighting only, while preserving a pair-center fallback for compact lower-latitude stereo pairs.

## Current Status

Status: Phase 2 design SPEC drafted and implementation plan written; ready for execution approach selection.

The previous polar adaptive-routing plan remains useful as baseline context, but this is a new architecture task because illumination evidence, tile routing, deep-learning manifest grouping, reporting, and paper figures all need changes.

## Success Criteria

- Adaptive routing supports automatic illumination granularity:
  - tiled long-strip DOM matching uses one representative valid point per tile;
  - compact/non-tiled pair matching uses one representative valid point per pair overlap.
- Tile representative point selection is bounded:
  - use center if pixel-available and source-camera-projectable;
  - otherwise use the nearest pixel-available and source-camera-projectable point;
  - skip illumination/routing for a tile with no source-projectable representative point.
- Physical illumination metadata is computed from the source/original camera geometry corresponding to each DOM:
  - the source cube may be full original resolution or REDUCED, depending on how that DOM was generated;
  - do not assume every DOM maps back to a `REDUCED_*.cub` input.
  - solar azimuth;
  - incidence angle;
  - solar elevation as `90.0 - incidence_angle`;
  - left/right azimuth, elevation, and incidence differences.
- Deep-learning execution remains grouped by selected method rather than launching one process per tile.
- RANSAC-filtered success metrics and tile-level method-selection diagnostics are available for final Nature-style figures.

## Phase 1: Architecture Audit

Status: complete

- [x] Inspect existing pair-level adaptive routing and sidecar flow.
- [x] Inspect tile task and deep-match manifest organization.
- [x] Identify affected modules and experiment outputs.
- [x] Confirm current PyISIS camera/projection API calls needed for DOM tile center -> original image solar geometry.
- [x] Confirm where each DOM's source/original cube path is preserved in DOM pair metadata for both fixed and adaptive runs.

## Phase 2: Design the Illumination Data Model

Status: complete

- [x] Define `TileIlluminationSample` fields for representative point, coordinate basis, validity status, original-image sample/line, and solar geometry.
- [x] Define pair-center metadata fields for compact non-tiled pairs.
- [x] Define aggregate pair summary fields for reporting route distributions and figure source data.
- [x] Define JSON compatibility policy so older sidecars without tile illumination still load.

## Phase 3: Implement Bounded Representative-Point Selection

Status: pending

- [ ] Add `pixel_available` checks for finite DOM pixels and true ISIS no-data/special pixels.
- [ ] Keep `radiometric_valid_for_matching` separate for matching, texture, keypoint, and visualization masks.
- [ ] Add center-first source-projectable check using DOM-to-ground-to-source-camera projection.
- [ ] Add nearest pixel-available and source-projectable fallback with deterministic tie breaking.
- [ ] Add skip status for no projectable representative point.
- [ ] Add focused tests for center projectable, shadowed-but-projectable center, center projection fallback, no-projectable skip, and coordinate basis.

## Phase 4: Implement Physical Solar Geometry Extraction

Status: pending

- [ ] Convert DOM sample/line representative point to ground coordinates using DOM projection/UniversalGroundMap.
- [ ] Project ground point into the corresponding source/original left/right cubes using CameraFirst ground map.
- [ ] Compute solar azimuth, incidence angle, and elevation at original-image pixel positions.
- [ ] Record failure reasons separately for DOM ground failure, original projection failure, and camera solar-geometry failure.
- [ ] Add smoke tests on existing SPICE-initialized fixture or real-data dry-run sample.

## Phase 5: Route Per Tile and Group Work by Matcher

Status: pending

- [ ] Change adaptive routing from one pair-level route to per-tile route decisions when multiple tiles exist.
- [ ] Keep pair-center routing when there is one tile or matching is not tiled.
- [ ] Preserve current prior-only semantics: do not cascade to another matcher after failure.
- [ ] Group tile tasks by selected matcher and execution environment:
  - first stay in `asp360_new` and complete all SIFT+FLANN matching, physical illumination metadata, manifest export, and non-deep bookkeeping for the stereo pair batch;
  - then switch once to `deep-learning` and run all required SIFT+LightGlue, SuperPoint+LightGlue, and LoFTR grouped manifests for the relevant stereo pair batch;
  - avoid repeated conda switching inside per-tile or per-method loops.
- [ ] Ensure imported deep results merge back into one pair-level `.key` output with per-tile provenance.

## Phase 6: Update Reports and Nature-Style Figures

Status: pending

- [ ] Extend pair and method summaries with tile-level route counts and illumination bins.
- [ ] Report success using RANSAC-retained matches, not raw imported match count.
- [ ] Regenerate five-method source data with tile-level adaptive routing.
- [ ] Generate case-study figures:
  - high texture + small physical illumination difference tile;
  - low texture + large physical illumination difference tile.
- [ ] Clearly label grayscale brightness metrics as visualization-only if retained.

## Phase 7: Full Benchmark Rerun

Status: pending

- [ ] Run focused unit tests and smoke tests in `asp360_new`.
- [ ] In `asp360_new`, complete all classic SIFT+FLANN work and export all grouped deep manifests needed for the benchmark batch.
- [ ] Switch once to `deep-learning` and run all required deep-learning grouped manifests with `torch_num_threads=8` and `num_workers=1`.
- [ ] Import results, run RANSAC filtering, and regenerate visualizations.
- [ ] Compare new tile-illumination adaptive routing against:
  - SIFT+FLANN;
  - SIFT+LightGlue;
  - SuperPoint+LightGlue;
  - LoFTR;
  - previous pair-level adaptive baseline.

## Implementation Plan

Status: written

- [x] Wrote Superpowers implementation plan:
  - `docs/superpowers/plans/2026-06-02-tile-illumination-adaptive-routing.md`
- [ ] Choose execution mode:
  - subagent-driven task execution; or
  - inline execution with checkpoints.

## Key Decisions

| Decision | Rationale |
| --- | --- |
| Use automatic illumination granularity | Tiled long-strip polar NAC images need local solar geometry; compact low/mid-latitude pairs can use a pair-center approximation. |
| Use one representative valid point per tile | Keeps solar-angle computation bounded and avoids expensive per-pixel camera calls. |
| Prefer nearest source-projectable fallback when center fails | DOM-space polar images often have black/no-data or non-projectable regions; the nearest pixel-available and source-projectable point gives bounded local physical illumination evidence. |
| Use the DOM source/original cube camera geometry for solar angles | The correct camera model is the image that generated the DOM; it may be full-resolution original or REDUCED, so routing must not hard-code REDUCED-only paths. |
| Group work by environment and matcher | Complete all `asp360_new` work first, then switch once to `deep-learning` for the required deep manifests. This preserves tile-level routing while avoiding repeated conda switching overhead. |
| Keep prior-only routing | User clarified adaptive routing means choosing a method from texture/illumination evidence, not retrying a cascade after failure. |

## Open Questions

1. Should tile-level physical illumination sample only the left/right tile representative point, or also record optional corner diagnostics for later analysis?
2. Should route thresholds use absolute solar-elevation/azimuth differences, or a normalized combined score with tunable weights?
3. Should pair-center fallback apply only when there is one generated tile, or also when the overlap footprint is below a fixed pixel-area threshold?

## Environment Notes

- Main repo: `/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone`
- Real-data root: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd`
- Reduced/DOM experiment root: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m`
- Use `asp360_new` for ISIS/PyISIS preprocessing, source-cube metadata resolution, physical illumination extraction, classic SIFT, deep manifest export/import, RANSAC summaries, and plotting.
- Use `deep-learning` for LightGlue/SuperPoint/LoFTR inference. Prefer one environment switch per benchmark batch: enter `deep-learning`, run all needed manifests, exit back to `asp360_new` for import/reporting.
- Do not modify, delete, or commit `.gitignore` or `print.prt`.

## Errors Encountered

| Error | Attempt | Resolution |
| --- | --- | --- |
| None yet | Plan initialization | N/A |
| `_resolved_invalid_values_for_cube` called with `None` or `Path` during temporary validation | 2 | The helper expects an open `ip.Cube` plus a tuple of invalid values. Temporary script was corrected to call `_resolved_invalid_values_for_cube(cube, ())`. |
| Left rich-tile center projected from DOM to ground but failed `source_ground_map.set_universal_ground` in the source cube | 1 | Recorded as an important design boundary: a representative point must be DOM-valid and source-camera-projectable, not only DOM-valid. The right tile completed the full geometry/solar chain. |
