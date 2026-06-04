# DOM-Coordinate Distance Prefilter and Affine RANSAC Design

## Goal

Update the gross-error and RANSAC filtering policy for DOM and ORI matching so both paths use DOM geometry as the default geometric reference.

Default filtering order:

```text
raw aligned keypoints
 -> DOM-projected distance prefilter
 -> affine-partial RANSAC in DOM pixel coordinates
 -> filtered aligned keypoints
```

The existing spherical ORI ground-distance filter and homography RANSAC remain available for explicit legacy or diagnostic use, but they are not the default path for new matching and ControlNet runs.

## Motivation

The previous default combined a kilometer-scale spherical distance prefilter with homography RANSAC. The distance filter is useful for removing obvious gross errors, but homography RANSAC can be too brittle for LRO NAC polar DOM products when matches span several local geometry regimes. Some stereo pairs retain most points under the homography model, while representative low-texture or high-lighting-difference pairs can collapse from thousands of raw matches to only a few retained points.

The desired production behavior is:

- Reject physically implausible correspondences first.
- Use the same DOM geometric frame for DOM and ORI workflows.
- Prefer a constrained affine-partial model over a full homography for DOM-space consistency.
- Preserve sparse but plausible points when the RANSAC model cannot be estimated.

## Non-Goals

- Do not delete the existing homography RANSAC implementation.
- Do not delete the existing ORI spherical lat/lon distance implementation.
- Do not automatically generate DOM products for ORI matching.
- Do not add MAP PVL projection handling for this change.
- Do not make local or tile-level RANSAC the default, because sparse tiles may not have enough points.
- Do not silently fall back from the new DOM-based ORI path to the old ORI spherical path.

## Geometry Policy

### Default Distance Space

The default pre-RANSAC distance filter uses DOM projected coordinates.

DOM matching:

```text
DOM key sample/line -> DOM projection coordinate -> projected distance
```

ORI matching:

```text
ORI key sample/line
 -> original cube camera ground point
 -> user-provided corresponding DOM projection/image coordinate
 -> DOM projection coordinate
 -> projected distance
```

The ORI path requires the user to provide the corresponding left and right DOMs. If either DOM is missing, nonexistent, or cannot be opened for the required mapping, the program must fail with an actionable error. It must not auto-create a DOM and must not silently fall back to the spherical ORI method.

### Default RANSAC Space

All default RANSAC filtering uses DOM pixel coordinates.

Metadata records:

```json
{
  "ransac_coordinate_space": "dom_pixel"
}
```

For DOM matching, the keypoint sample/line values are already DOM pixel coordinates.

For ORI matching, the ORI keypoints are mapped to user-provided DOM pixel coordinates only for filtering. The final keep/drop mask is then applied back to the original ORI keypoint files so left/right correspondence alignment is preserved.

## Distance Filtering

The default distance method is projected DOM distance:

- Use each side's DOM map projection to resolve a projected ground coordinate.
- Compute planar distance in projected units and report kilometers.
- Drop a correspondence when the projected distance exceeds `pre_ransac_max_ground_distance_km`.
- Keep `--pre-ransac-max-ground-distance-km 0` as the disabled mode.
- Keep the default threshold at `1.0 km`.

The summary should continue to use the existing metadata key:

```text
pre_ransac_ground_distance_filter
```

Add or refine fields so the default path is explicit:

- `distance_method`: `dom_projected`
- `space`: `dom`
- `geometry_source`: `dom_projection_coordinate`
- `threshold_km`
- `input_count`
- `retained_count`
- `dropped_count`
- `dropped_ground_distance_count`
- `ground_lookup_failure_count`
- `distance_summary_km`
- `left_dom`
- `right_dom`

The existing ORI spherical method remains available as:

```text
distance_method = ori_spherical
geometry_source = ori_camera_set_image
```

It must be selected explicitly and must not be the default when DOMs are available or required.

## Affine-Partial RANSAC

Replace the default RANSAC model with OpenCV `estimateAffinePartial2D`.

Default:

```text
--ransac-model affine-partial
--ransac-reproj-threshold 10
```

The threshold is in DOM pixels. For 10 m DOM products, the default corresponds to roughly 100 m in map space. This is a geometric consistency filter after the 1 km gross-error filter, not a replacement for the distance filter.

Supported models:

- `affine-partial`: default, uses `cv2.estimateAffinePartial2D`.
- `affine`: optional, uses `cv2.estimateAffine2D`.
- `homography`: legacy/diagnostic, uses the existing `cv2.findHomography` path.

Minimum-point behavior:

- `affine-partial` requires enough points to estimate the model.
- `affine` requires enough points to estimate the model.
- `homography` keeps the existing minimum-point behavior.
- If there are not enough points for the selected model, RANSAC is skipped and all distance-filtered points are retained.
- The summary must report `status: skipped_insufficient_points`, `applied: false`, and `retained_count == input_count`.

Estimation-failure behavior:

- If OpenCV returns no model or no mask despite enough input points, keep the existing conservative behavior: retain all input points and report a skipped/failed status.
- Do not convert model-estimation failure into a pair failure after the distance filter has already removed gross errors.

## Filtering Data Flow

### DOM Matching

```text
match DOM pair
 -> write raw aligned DOM keys
 -> DOM projected distance filter
 -> affine-partial RANSAC in DOM pixel coordinates
 -> write filtered DOM keys and metadata
```

### ORI Matching

```text
match ORI pair
 -> require left/right corresponding DOMs
 -> write raw aligned ORI keys
 -> map each ORI point to corresponding DOM pixel/projection coordinates
 -> DOM projected distance filter
 -> affine-partial RANSAC in DOM pixel coordinates
 -> apply resulting keep mask to original ORI keys
 -> write filtered ORI keys and metadata
```

### ControlNet from DOM

```text
DOM keys
 -> duplicate merge
 -> check upstream prefilter metadata
 -> optional DOM projected distance filter
 -> affine-partial RANSAC
 -> dom2ori
 -> ControlNet
```

If upstream metadata shows the default DOM-projected distance filter already ran, ControlNet skips the duplicate distance pass and records the upstream summary.

### ControlNet from ORI

```text
ORI keys
 -> require corresponding DOMs for default filtering
 -> optional DOM projected distance filter
 -> affine-partial RANSAC in DOM pixel coordinates
 -> ControlNet
```

If a caller explicitly selects the legacy ORI spherical method, the existing ORI spherical distance path may be used before RANSAC. That mode is not the default.

## CLI and Configuration

Keep existing flags:

```text
--pre-ransac-max-ground-distance-km FLOAT
--pre-ransac-ground-lookup-failure-policy drop|keep
--ransac-reproj-threshold FLOAT
--ransac-confidence FLOAT
--ransac-max-iters INT
```

Add:

```text
--pre-ransac-distance-method dom-projected|ori-spherical
--ransac-model affine-partial|affine|homography
```

Defaults:

```text
pre_ransac_distance_method = dom-projected
pre_ransac_max_ground_distance_km = 1.0
ransac_model = affine-partial
ransac_reproj_threshold = 10.0
```

ORI matching entrypoints must expose or forward the left/right corresponding DOM paths. If the default `dom-projected` method or default affine RANSAC is enabled and the ORI path lacks DOMs, argument validation fails before matching starts.

## API Shape

Extend the existing ground-distance module rather than creating a parallel filtering stack.

Add a lower-level aligned-keypoint helper that accepts projected-coordinate lookup functions:

```python
filter_stereo_pair_keypoints_by_projected_distance(
    left_key_file,
    right_key_file,
    *,
    left_projected_lookup,
    right_projected_lookup,
    threshold_km,
    lookup_failure_policy="drop",
) -> tuple[left_filtered, right_filtered, summary, retained_indices]
```

Keep the current spherical helper for legacy use.

Extend the RANSAC helper:

```python
filter_stereo_pair_keypoints_with_ransac(
    left_key_file,
    right_key_file,
    *,
    ransac_model="affine-partial",
    ransac_coordinate_space="dom_pixel",
    ransac_reproj_threshold=10.0,
    ...
)
```

For ORI filtering, use a separate coordinate-provider object or helper that returns:

- original keypoint file for output,
- DOM pixel coordinates for RANSAC,
- DOM projected coordinates for distance filtering,
- index masks to apply filtered results back to the original keypoint files.

## Summary Schema

RANSAC summary should include:

- `applied`
- `status`
- `model`: `affine-partial`, `affine`, or `homography`
- `coordinate_space`: `dom_pixel`
- `input_count`
- `retained_count`
- `dropped_count`
- `opencv_inlier_count`
- `opencv_outlier_count`
- `reproj_threshold`
- `confidence`
- `max_iters`
- `matrix`
- `matrix_type`: `affine_2x3` or `homography_3x3`
- `skipped_reason`, when skipped

The older `homography_matrix` field may remain for backward compatibility when `model == "homography"`, but new consumers should read `matrix` and `matrix_type`.

## Error Handling

Fail early when:

- `pre_ransac_max_ground_distance_km` is negative or non-finite.
- `ransac_reproj_threshold` is non-positive or non-finite.
- `ransac_model` is unsupported.
- `pre_ransac_distance_method` is unsupported.
- ORI matching uses the default DOM-projected path but left/right DOM paths are missing.
- ORI matching provides DOM paths that do not exist or cannot be opened.
- ORI-to-DOM coordinate mapping cannot be initialized.

Do not fail a pair merely because too few points remain for RANSAC after distance filtering. Keep the distance-filtered points and report the skipped RANSAC status.

## Testing

Unit tests should cover:

- Projected-distance filtering keeps and drops aligned point pairs correctly.
- Projected-distance summaries report kilometers and retained indices.
- ORI default filtering requires DOM paths and fails early without them.
- Legacy ORI spherical distance can still be selected explicitly.
- `affine-partial` calls `cv2.estimateAffinePartial2D` and applies the returned mask.
- `affine` calls `cv2.estimateAffine2D`.
- `homography` still calls `cv2.findHomography`.
- Insufficient points after distance filtering keep all remaining points and report skipped RANSAC.
- Wrapper and config forwarding for new `ransac_model` and `pre_ransac_distance_method` flags.
- Metadata contains `distance_method`, `ransac_model`, and `coordinate_space`.

Focused integration tests should cover:

- DOM matching default path: distance filter then affine-partial RANSAC.
- ORI matching default path with provided DOMs: DOM-projected distance and DOM-pixel affine RANSAC, with keep/drop masks applied back to ORI keys.
- ControlNet fallback path skips duplicate distance filtering when upstream metadata reports the default filter already ran.

## Migration and Reporting

Existing outputs using the spherical ORI filter or homography RANSAC remain readable. New benchmark reports should label retained counts by filter model:

- `raw_matches`
- `distance_retained`
- `affine_partial_retained`
- `homography_retained`, optional diagnostic

This prevents homography retained counts from being interpreted as the sole measure of geometric validity for polar DOM pairs.
