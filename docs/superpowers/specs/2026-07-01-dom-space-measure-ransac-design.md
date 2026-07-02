# DOM-Space Measure-Level RANSAC ControlNet Filter Design

## Goal

Build a Python CLI app that filters gross outliers in an ISIS control network at
the `ControlMeasure` level by projecting original-image measures into DOM pixel
space, running DOM-space RANSAC per image pair in parallel, and writing an
auditable output control network plus reports.

The app must avoid the previous point-level behavior. A bad pairwise
correspondence marks the participating measures as ignored; it does not delete
the whole control point.

## User-Facing Command

Create:

```text
examples/controlnet_construct/filter_controlnet_dom_ransac.py
```

Primary usage:

```bash
python examples/controlnet_construct/filter_controlnet_dom_ransac.py \
  --input-net INPUT.net \
  --original-list reduced_original_images.lis \
  --dom-list dom_images.lis \
  --output-net OUTPUT.net \
  --report OUTPUT.report.json \
  --outlier-measures OUTPUT.outliers.jsonl \
  --projection-failures OUTPUT.projection_failures.jsonl \
  --ransac-model affine-partial \
  --ransac-reproj-threshold 10 \
  --num-workers 8 \
  --max-open-cubes-per-worker 16
```

Default behavior:

- Reads `ControlMeasure` sample/line as original-image coordinates.
- Converts each measure to DOM pixel coordinates through pyisis:
  original camera `set_image(sample, line)` -> latitude/longitude -> DOM
  projection `set_universal_ground(latitude, longitude)` -> DOM sample/line.
- Runs pairwise DOM RANSAC using the existing image-match RANSAC model
  semantics.
- Sets outlier `ControlMeasure` objects to ignored in the output network.
- Preserves input control points unless a cleanup option is explicitly enabled
  in a later version.
- Reports projection failures but does not ignore them by default.

## Non-Goals

- Do not assume a `_dom-M.net` filename means measures are already stored in DOM
  pixel coordinates.
- Do not delete whole `ControlPoint` objects as the default filtering action.
- Do not open all original or DOM cubes at startup.
- Do not let worker processes write or mutate the output `ControlNet`.
- Do not implement graph/block scheduling in the first version.

## Inputs and Mapping

The app receives:

- `--input-net`: ISIS binary or PVL control network.
- `--original-list`: original image cube list, one path per line.
- `--dom-list`: DOM cube list aligned one-to-one with `--original-list`.

The main process builds:

```text
serial -> original_cube_path
serial -> dom_cube_path
```

using `SerialNumber.compose(original_cube)`. DOM paths are paired by line
position with original paths. The app validates equal list lengths and reports
serials in the network that are missing from either map.

## Measure Identity

Use a stable key for every measure:

```text
point_index
point_id
measure_index
serial
```

The key is used in worker results, outlier reports, projection-failure reports,
and the final single-process output update.

`point_index` and `measure_index` are the write-back coordinates. `point_id` and
`serial` are included for auditability and diagnostics.

## Data Flow

### Stage 1: Extract Measure Metadata

The main process opens the control network once and extracts active measures.

For each non-ignored control point:

- collect non-ignored measures;
- skip points with fewer than two active measures;
- generate all unordered measure pairs inside the point;
- group pair records by `(left_serial, right_serial)`.

Each pair record contains:

```text
left_measure_key
right_measure_key
left_original_sample
left_original_line
right_original_sample
right_original_line
```

### Stage 2: Pair-Parallel Projection and RANSAC

The main process submits each serial-pair group as an independent task.

Each worker:

- opens only the original and DOM cubes required for the current pair;
- uses a per-worker LRU cache for cube/camera/projection objects;
- converts original-image measure coordinates into DOM pixel coordinates;
- records projection failures and excludes failed correspondences from RANSAC;
- runs DOM-space RANSAC on the successfully projected correspondences;
- returns outlier measure keys and per-pair summary metadata.

Workers return data only. They do not mutate `ControlNet` and do not write
`.net` files.

### Stage 3: Aggregate Outlier Measures

The main process waits for all pair tasks to finish.

Use the selected aggressive policy:

```text
If a measure is part of any pairwise RANSAC outlier correspondence,
mark that measure as an outlier.
```

This is intentionally stronger than vote-based filtering. The report must make
the policy explicit because two-view points can result in both measures being
flagged when the pair is geometrically inconsistent.

### Stage 4: Write Output

The main process reopens the input control network and applies:

```python
measure.set_ignored(True)
```

for each aggregated outlier measure key.

Then it writes:

- output control network;
- JSON summary report;
- outlier measure JSONL;
- projection failure JSONL.

The output writer is single-process and happens only after all outlier
decisions are complete.

## RANSAC Model

Reuse the existing semantics from `examples/image_match/stereo_ransac.py`:

- default model: `affine-partial`;
- supported models: `affine-partial`, `affine`, `homography`;
- default coordinate space label: `dom_pixel`;
- default reprojection threshold: `10.0` pixels;
- default confidence: `0.995`;
- default max iterations: `5000`;
- default mode: `loose`.

If a pair has too few successfully projected correspondences for the selected
model, skip RANSAC for that pair and report `skipped_insufficient_points`.

## Projection Failure Policy

Projection failures are expected to be rare for networks generated from DOM
workflows, but they are not treated as RANSAC outliers.

Default policy:

- write projection failures to report and JSONL;
- do not ignore the failed measures;
- include failure rate by pair and globally.

Projection failure records include:

```text
point_id
measure_index
serial
original_sample
original_line
failure_stage
message
```

Failure stages:

- `missing_original_serial`
- `missing_dom_serial`
- `open_original_failed`
- `open_dom_failed`
- `camera_set_image_failed`
- `invalid_ground_coordinate`
- `dom_set_universal_ground_failed`
- `invalid_dom_coordinate`

## Large-Scale Cube Handling

The app must support networks associated with more than 10,000 cubes without
opening all cubes.

Rules:

- The main process opens the control network and reads image lists only.
- The main process may call `SerialNumber.compose` while building the mapping,
  but it must not keep cube handles open.
- Workers open cubes lazily per serial pair.
- Worker cube handles are bounded by `--max-open-cubes-per-worker`.
- The cache uses least-recently-used eviction and closes evicted cubes.
- Open pyisis `Cube`, camera, and projection objects are never shared across
  processes.
- The CLI exposes `--num-workers` and `--max-open-cubes-per-worker`.

This keeps file descriptors bounded by approximately:

```text
num_workers * max_open_cubes_per_worker + main_process_overhead
```

The default `--max-open-cubes-per-worker 16` favors safety. Users can increase
it for faster repeated pair access when OS file descriptor limits allow it.

## Output Files

### Summary Report

JSON report fields:

```text
input_net
output_net
original_list
dom_list
input_point_count
input_measure_count
active_point_count
active_measure_count
pair_count_total
pair_count_ransac_attempted
outlier_measure_count
projection_failure_count
projection_failure_rate
ransac_model
ransac_reproj_threshold
ransac_confidence
ransac_max_iters
ransac_mode
num_workers
max_open_cubes_per_worker
pairs[]
```

Each pair summary includes:

```text
left_serial
right_serial
input_correspondence_count
projected_correspondence_count
projection_failure_count
status
retained_count
dropped_count
opencv_inlier_count
opencv_outlier_count
retained_soft_outlier_count
```

### Outlier Measures JSONL

Each line:

```json
{
  "point_index": 123,
  "point_id": "0000123456",
  "measure_index": 2,
  "serial": "LRO/1/...",
  "trigger_pair": ["LRO/1/...", "LRO/1/..."],
  "policy": "any_pair_outlier"
}
```

### Projection Failures JSONL

Each line follows the projection failure schema above.

## Error Handling

Fatal errors:

- input control network cannot be read;
- original and DOM lists have different lengths;
- `--ransac-model` is unsupported;
- numeric RANSAC parameters are non-finite or invalid;
- output path cannot be written.

Non-fatal per-measure or per-pair conditions:

- missing serial mapping;
- cube open failure for a pair;
- projection failure;
- insufficient pair correspondences;
- RANSAC model estimation failure.

Non-fatal conditions appear in the summary report and JSONL diagnostics.

## Testing Strategy

Unit tests:

- serial-to-path mapping validates equal list lengths;
- measure key extraction preserves point and measure indices;
- pair grouping emits all unordered measure pairs inside a point;
- projection failure records do not produce ignored measures;
- aggressive policy flags a measure when any pair reports it as outlier;
- insufficient pair counts skip RANSAC;
- LRU cache evicts and closes cube objects.

RANSAC tests:

- synthetic affine inliers and outliers produce expected outlier measure keys;
- `affine-partial`, `affine`, and `homography` route to the expected OpenCV
  model path.

CLI tests:

- mocked worker results produce an output network with only the requested
  measures ignored;
- report, outlier JSONL, and projection-failure JSONL are written;
- invalid arguments fail before reading cubes.

Integration validation:

- run on a small real ISIS network when available;
- read the output `.net` with `ip.ControlNet`;
- confirm point count is preserved by default;
- confirm ignored measure count increases by the outlier measure count.

## Future Extensions

Projection cache:

- optional SQLite cache keyed by `(serial, sample, line, dom_path_mtime)` to
  avoid reprojecting measures when tuning RANSAC thresholds.

Filtering policies:

- vote-based policy;
- minimum vote count policy;
- optional point cleanup after measure filtering.

Scheduling:

- connected-component or image-block task scheduling for very large image
  graphs.
