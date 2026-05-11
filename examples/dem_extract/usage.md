<!--
Sparse stereo DEM extraction pipeline usage guide.

Author: Geng Xun
Created: 2026-05-10
Last Modified: 2026-05-10
Updated: 2026-05-10  Geng Xun documented the original-image and DOM matching routes for sparse DEM extraction.
Updated: 2026-05-10  Geng Xun documented optional `.key` refinement stages between matching and triangulation.
-->

# Sparse stereo DEM extraction pipeline

This example turns a stereo image pair into a sparse ISIS DEM cube by reusing the
repository's existing matching and ISIS `Stereo.elevation(...)` helpers.

It is intentionally a **sparse tie-point DEM** workflow. It is useful for quick
geometry checks, debugging stereo intersections, and producing a small DEM-like
surface from matched features. It is not a dense ASP replacement for
`parallel_stereo` + `point2dem`.

## What is included

The pipeline supports two routes:

1. **Original-image route**
   - match the left/right original cubes directly;
   - write synchronized original-image `.key` files;
   - triangulate those key pairs with `isis_pybind.Stereo.elevation(...)`;
   - rasterize surviving points into a DEM cube.

2. **DOM route**
   - match the left/right DOM cubes;
   - write synchronized DOM-space `.key` files;
   - merge duplicate tie points;
   - run stereo-pair RANSAC filtering;
   - convert DOM coordinates back to original-image coordinates;
   - triangulate and rasterize exactly like the original-image route.

The user-facing wrapper is:

- `examples/dem_extract/run_pipeline_example.sh`

The Python orchestration entrypoint is:

- `examples/dem_extract/dem_pipeline.py`

The original-image route CLI is:

- `from-ori-match-dem`

This is now the single canonical command name for the ORI-matching-to-DEM path.

The final DEM-from-key stage remains:

- `examples/dem_extract/isis_stereo_dem.py from-key`

## Configuration

The example config is:

- `examples/dem_extract/dem_config.example.json`

Important sections:

- `DemExtract`: DEM filtering and rasterization parameters.
- `ImageMatch`: shared matching defaults, following the same style as
  `examples/controlnet_construct/controlnet_config.example.json`.
- `OriginalImageMatch`: overrides used only by the original-image route.
- `DomImageMatch`: overrides used only by the DOM route.
- `DomToOriginal`: duplicate-merge and RANSAC parameters used by the DOM route
  before converting tie points back to original-image coordinates.
- `KeyRefinement`: optional `.key` refinement stages inserted before DEM
  triangulation. Keep `stages: []` to disable, or use for example
  `"stages": ["maximum_correlation"]` and later
  `"stages": ["maximum_correlation", "gruen"]`.

The wrapper currently keeps route-specific runtime choices in the config. If you
need a one-off override, edit a copied config file rather than changing the
repository example in place.

## Inputs

### Required for both routes

- `--left-cube`: left original ISIS cube with camera geometry.
- `--right-cube`: right original ISIS cube with camera geometry.
- `--map-template-cube`: projected cube whose `Mapping` group and dimensions
  define the output DEM grid.

### Required only for DOM route

- `--left-dom`: left projected/DOM cube used for matching.
- `--right-dom`: right projected/DOM cube used for matching.

The DOM route assumes the DOM cubes project to the same planetary surface as the
original cubes and can be converted back to original image coordinates through
`examples/controlnet_construct/dom2ori.py`.

## Quick start: original-image matching

From the repository root:

```bash
bash examples/dem_extract/run_pipeline_example.sh \
  --mode ori \
  --left-cube left.cub \
  --right-cube right.cub \
  --map-template-cube left_dom.cub
```

This route is simpler and does not require DOM cubes. It is a good first smoke
check when the original images have enough texture and overlap for direct SIFT
matching.

If you want to call the Python entrypoint directly, the spec-aligned command is:

```bash
python examples/dem_extract/dem_pipeline.py from-ori-match-dem \
  --left-cube left.cub \
  --right-cube right.cub \
  --map-template-cube left_dom.cub
```

## Quick start: DOM matching

From the repository root:

```bash
bash examples/dem_extract/run_pipeline_example.sh \
  --mode dom \
  --left-dom left_dom.cub \
  --right-dom right_dom.cub \
  --left-cube left.cub \
  --right-cube right.cub \
  --map-template-cube left_dom.cub
```

This route mirrors the robust pieces of the DOM ControlNet workflow: match on
projected products, then merge/RANSAC/filter and convert the surviving points
back into original image coordinates before DEM triangulation.

## Work directory layout

The default work directory is `work/dem_extract`.

Typical outputs:

```text
work/dem_extract/
  dem/
    stereo_dem.cub
  keys_dom/
    left_dom.key
    right_dom.key
    left_dom_merged.key
    right_dom_merged.key
    left_dom_ransac.key
    right_dom_ransac.key
  keys_ori/
    left_ori.key
    right_ori.key
  keys_refined/
    left_refined.key
    right_refined.key
  match_viz/
    *.png
  point_cloud/
    stereo_points.jsonl
  quality/
    stereo_dem.summary.json
  reports/
    dem_summary.json
    dom_match_metadata.json
    dom_merge_summary.json
    dom_ransac_summary.json
    dom2ori_summary.json
    key_refinement_summary.json
    ori_match_summary.json
    pipeline_summary.json
```

The original-image route does not write `keys_dom/` or DOM conversion reports.

## Output values

The DEM cube stores radius values in meters (`radius_m`), not ellipsoid-relative
height. The output summary records:

- input cube paths;
- input `.key` paths;
- filter thresholds;
- triangulation counters;
- rasterized point count;
- filled DEM cell count;
- output DEM cube path.

The current implementation now supports two explicit value modes:

- `radius_m` (default)
- `height_m`

To write `height_m`, provide both:

- `--value-type height_m`
- `--datum-radius-m <meters>`

Example:

```bash
python examples/dem_extract/isis_stereo_dem.py from-key \
  left.cub right.cub left.key right.key template.cub dem_height.cub \
  --value-type height_m \
  --datum-radius-m 1737400.0
```

This first implementation uses an explicit user-specified datum radius in
meters. That keeps the output semantics unambiguous without yet guessing a
target-dependent local ellipsoid radius.

## Optional `.key` refinement stage

The DEM path can now insert a matcher-agnostic refinement layer **after** key
generation and **before** triangulation. This is designed for the exact use case
where upstream tie points may come from LoFTR, SIFT, SuperPoint, or any other
matcher that can export the repository-standard synchronized `.key` format.

Current stage choices:

- `maximum_correlation`
- `gruen`

Recommended rollout:

1. `maximum_correlation`
2. `maximum_correlation -> gruen`

Pipeline config example:

```json
"KeyRefinement": {
  "enabled": true,
  "stages": ["maximum_correlation", "gruen"]
}
```

Direct `from-key` example:

```bash
python examples/dem_extract/isis_stereo_dem.py from-key \
  left.cub right.cub left.key right.key template.cub dem.cub \
  --refine-stage maximum-correlation \
  --refine-stage gruen \
  --refined-left-key-output left_refined.key \
  --refined-right-key-output right_refined.key \
  --refinement-summary-output refinement_summary.json
```

Right now the refinement stages keep the left-side keypoints fixed and refine
the right-side conjugate points using the current `.key` coordinates as seeds.
If refinement fails on a particular point, the implementation keeps the
original seed for that point rather than dropping the pair.

## When to use each route

Use `--mode ori` when:

- the original images already overlap strongly;
- illumination and scale differences are manageable;
- you want the shortest possible pipeline.

Use `--mode dom` when:

- matching is more stable in projected products;
- the original images have large perspective differences;
- you already have DOMs from an earlier map-projection workflow;
- you want the same merge/RANSAC/dom2ori logic used by the ControlNet example.

## Relationship to `examples/controlnet_construct`

This DEM pipeline intentionally reuses the existing ControlNet matching stack
instead of creating another matcher:

- original-image matching uses `match_ori_pair_to_key_files(...)`;
- DOM matching uses `match_dom_pair_to_key_files(...)`;
- DOM duplicate merge uses `merge_stereo_pair_key_files(...)`;
- RANSAC filtering uses `filter_stereo_pair_key_files_with_ransac(...)`;
- DOM-to-original conversion uses `convert_paired_dom_keypoints_to_original(...)`.

The DEM-specific downstream stage then uses `isis_stereo_dem.py from-key`.

## Validation tips

Start with help/config checks:

```bash
bash examples/dem_extract/run_pipeline_example.sh --help
python examples/dem_extract/dem_pipeline.py --help
python examples/dem_extract/dem_pipeline.py from-ori-match-dem --help
python examples/dem_extract/isis_stereo_dem.py from-key --help
```

For repository development, run the focused unit tests with the `asp360_new`
Python interpreter after modifying this example.

## Known limitations

- This pipeline is sparse because it starts from feature matches, not dense
  stereo correlation.
- Output cells are only filled where surviving triangulated points rasterize
  into the map-template grid.
- Accuracy depends on camera geometry, SPICE/kernel availability, matching
  quality, intersection angle, and filtering thresholds.
- The DOM route requires DOM products whose projection metadata can be read by
  ISIS and mapped back to the original cubes.
