# Pre-RANSAC Ground-Distance Prefilter Design

## Goal

Add a physically grounded outlier prefilter before RANSAC in PyISIS matching and ControlNet construction. A stereo correspondence is rejected before pixel-space RANSAC when the left and right image points resolve to lunar ground coordinates whose spherical surface distance exceeds a configurable threshold.

Default behavior:

- Enable the filter by default in production matching and ControlNet paths.
- Use `--pre-ransac-max-ground-distance-km 1.0` by default.
- Treat `--pre-ransac-max-ground-distance-km 0` as disabled.
- Drop pairs when either side cannot resolve a ground coordinate by default.
- Use spherical lat/lon distance only. Do not require or support a MAP PVL file in the first version.

## Non-Goals

- Do not add a projected-coordinate or MAP-file distance mode.
- Do not replace OpenCV RANSAC; this is a pre-RANSAC gross-error gate.
- Do not change matcher scoring, adaptive-routing decisions, or tile-routing policy.
- Do not attempt DEM-aware geodesic distance. The filter is for kilometer-scale gross outliers, so a spherical lunar distance is sufficient.

## Rationale

The current RANSAC helpers operate on image or DOM pixel coordinates. This can leave obviously wrong correspondences in the RANSAC input even when their physical ground positions are far apart. A ground-distance prefilter adds a hard physical consistency check before RANSAC.

Using spherical distance keeps the feature independent of map projections:

- ORI matches can resolve `sample,line -> latitude,longitude` through camera or `UniversalGroundMap.set_image`.
- DOM matches can resolve `sample,line -> latitude,longitude` through the DOM projection/ground map.
- Both paths then use the same distance calculation.
- No user-supplied MAP PVL is required.
- Projection mismatch and polar stereographic scale issues are avoided.

## Data Flow

### Matching Stage

The matching stage is the preferred place to run the filter.

DOM matching:

```text
DOM match -> ground-distance prefilter -> RANSAC visualization/filter -> output key + metadata
```

ORI matching:

```text
ORI match -> ground-distance prefilter -> RANSAC visualization/filter -> output key + metadata
```

The output metadata records `pre_ransac_ground_distance_filter.applied=true` when filtering ran.

### ControlNet Stage

ControlNet construction keeps a fallback guard but should avoid redundant work when matching already filtered the inputs.

DOM ControlNet:

```text
DOM key -> merge -> check prefilter metadata -> optional ground-distance prefilter -> RANSAC -> dom2ori -> ControlNet
```

ORI ControlNet:

```text
ORI key -> check prefilter metadata -> optional ground-distance prefilter -> RANSAC/downstream
```

If metadata shows an earlier ground-distance prefilter was applied, ControlNet skips its own prefilter and records the earlier summary in the final report. Per user decision, this skip does not compare thresholds; any positive prior `applied=true` marker is enough.

If metadata is missing or unreadable and the current threshold is greater than zero, ControlNet runs the prefilter as a fallback.

## Ground Lookup

### ORI Points

For ORI-space keypoints, each side resolves image coordinates directly:

1. Open the corresponding original cube.
2. Set the requested band.
3. Use camera or `UniversalGroundMap` with camera-first behavior.
4. Call `set_image(sample, line)`.
5. Read `universal_latitude()` and `universal_longitude()`.

This uses the existing SPICE/DEM context configured for the cube. No DOM or MAP file is required.

### DOM Points

For DOM-space keypoints, each side resolves map-projected image coordinates:

1. Open the corresponding DOM cube.
2. Set the requested DOM band.
3. Use `UniversalGroundMap` with projection-first behavior.
4. Call `set_image(sample, line)`.
5. Read `universal_latitude()` and `universal_longitude()`.

The later DOM-to-ORI conversion still needs the paired original cubes, but the prefilter distance calculation itself only needs each DOM point's ground coordinate.

## Distance Calculation

Use haversine/great-circle distance over lunar latitude/longitude:

- Inputs are degrees.
- Longitude deltas must be normalized across wrap boundaries.
- Default radius is the lunar mean radius, `1737.4 km`.
- If a future ISIS helper exposes a reliable target radius for both sides, it may be used only if it does not make the first version more complex. The first version should keep a clear constant.

The summary reports distances in kilometers.

## Filtering Rules

For each index-aligned pair:

1. Resolve left ground coordinate.
2. Resolve right ground coordinate.
3. If either lookup fails:
   - default policy: drop the pair;
   - record `ground_lookup_failure`.
4. Compute spherical distance.
5. If distance is greater than `threshold_km`, drop the pair and record `ground_distance_exceeded`.
6. Otherwise retain both keypoints.

The outputs must preserve left/right pair alignment.

If fewer than four pairs remain, downstream RANSAC already has existing insufficient-point handling. The prefilter summary should still report the retained count so callers can explain why RANSAC was skipped or ineffective.

## API and Module Shape

Create a focused module:

```text
examples/controlnet_construct/ground_distance_prefilter.py
```

Core APIs:

```python
filter_stereo_pair_keypoints_by_ground_distance(
    left_key_file,
    right_key_file,
    *,
    left_ground_lookup,
    right_ground_lookup,
    threshold_km,
    lookup_failure_policy="drop",
    lunar_radius_km=1737.4,
) -> tuple[left_filtered, right_filtered, summary]

filter_stereo_pair_key_files_by_ground_distance(
    left_input,
    right_input,
    left_output,
    right_output,
    *,
    left_ground_lookup,
    right_ground_lookup,
    threshold_km,
    lookup_failure_policy="drop",
    lunar_radius_km=1737.4,
) -> summary
```

Geometry-specific wrappers may live in the same module or a companion helper:

- `filter_ori_key_files_by_ground_distance(...)`
- `filter_dom_key_files_by_ground_distance(...)`

The low-level keypoint function should use injected lookup functions so unit tests do not require ISIS.

## Summary Schema

Use the metadata key:

```text
pre_ransac_ground_distance_filter
```

Fields:

- `applied`
- `already_prefiltered`
- `threshold_km`
- `lookup_failure_policy`
- `lunar_radius_km`
- `input_count`
- `retained_count`
- `dropped_count`
- `dropped_ground_distance_count`
- `ground_lookup_failure_count`
- `distance_summary_km`
- `max_ground_distance_km`
- `left_input`
- `right_input`
- `left_output`
- `right_output`
- `space`: `ori` or `dom`
- `geometry_source`: `ori_camera_set_image` or `dom_projection_set_image`

`distance_summary_km` should include count, min, mean, median, p90, and max for successfully resolved pairs.

## CLI and Configuration

Add and forward:

```text
--pre-ransac-max-ground-distance-km FLOAT
```

Defaults:

- default: `1.0`
- `0`: disabled

Optional first-version flag:

```text
--pre-ransac-ground-lookup-failure-policy drop|keep
```

Default: `drop`.

Wire the threshold through:

- `controlnet_stereopair.py from-dom`
- `controlnet_stereopair.py from-dom-batch`
- `controlnet_stereopair.py from-dom-match`
- `controlnet_stereopair.py from-ori-match`
- DOM matching wrappers and batch wrappers that produce final key/metadata outputs
- ORI matching wrappers and batch wrappers
- config/default catalog entries if the existing parameter catalog pattern expects wrapper-wide flags

## Metadata Skip Rule

ControlNet checks input metadata before running fallback filtering.

Skip when:

```json
{
  "pre_ransac_ground_distance_filter": {
    "applied": true
  }
}
```

The skip rule does not compare threshold, lookup policy, radius, or space. This follows the user decision that any existing applied marker means the input has already been prefiltered.

When skipped, ControlNet report should include:

```json
{
  "pre_ransac_ground_distance_filter": {
    "applied": false,
    "already_prefiltered": true,
    "source": "input_metadata",
    "upstream_summary": { ... }
  }
}
```

## Error Handling

Hard errors:

- left/right key lengths differ;
- threshold is negative;
- required cube paths are missing when fallback filtering is enabled;
- band index is invalid for a required cube.

Recorded drops:

- one or both sides fail ground lookup;
- distance exceeds threshold;
- returned lat/lon is non-finite.

Disabled mode:

- threshold `0` returns input keypoints unchanged;
- summary records `applied=false`, `status=disabled`.

## Testing

Unit tests:

- haversine distance handles small distances and longitude wrap;
- keypoint filter keeps pairs under threshold;
- keypoint filter drops pairs over threshold;
- lookup failure is dropped by default;
- lookup failure can be kept if the optional policy is implemented;
- threshold `0` disables filtering;
- left/right length mismatch raises;
- summary counts are correct;
- ControlNet skip rule skips when metadata has `applied=true`;
- ControlNet fallback runs when metadata is missing.

Integration-style tests with mocks:

- `from-dom` call order becomes merge, ground-distance prefilter/check, RANSAC, dom2ori;
- `from-ori-match` output metadata contains the prefilter summary;
- wrappers forward `--pre-ransac-max-ground-distance-km`;
- disabled mode preserves current behavior.

Real-data tests should be opt-in only and use existing environment guards.

## Rollout Plan

1. Add pure distance/keypoint filter module with injected lookup functions and unit tests.
2. Add DOM and ORI geometry wrappers around existing ISIS ground-map patterns.
3. Wire `from-dom` ControlNet fallback after merge and before RANSAC.
4. Wire matching-stage filtering and metadata emission.
5. Add wrapper/config forwarding.
6. Add focused validation on mock tests, then optional LRO smoke.

## Open Implementation Notes

- The matching stage should be the normal producer of filtered `.key` files.
- ControlNet fallback exists for direct `.key` users and legacy metadata.
- `print.prt` and `.gitignore` are unrelated local files and must not be staged as part of this work.
