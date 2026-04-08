# Metadata Audit — 2026-04-08

This note captures a repository-wide audit of top-of-file metadata completeness for pybind C++ binding files under `src/` and Python unit test files under `tests/unitTest/`.

## Scope

Scanned paths:

- `src/**/*.cpp`
- `src/**/*.h`
- `tests/unitTest/**/*.py`

Audit date:

- `2026-04-08`

## Status update after Batch 1 normalization

Applied on `2026-04-08`:

- C++ update-summary normalization completed for:
  - `src/base/bind_auto_reg_factory.cpp`
  - `src/base/bind_base_ground_map.cpp`
  - `src/base/bind_base_math.cpp`
  - `src/base/bind_base_pattern.cpp`
  - `src/base/bind_base_photometry.cpp`
  - `src/base/bind_base_utility.cpp`
  - `src/control/bind_interest_operator_factory.cpp`
  - `src/lro/bind_lro_utilities.cpp`
  - `src/mgs/bind_mgs_utilities.cpp`
- Python unit-test `Updated:` summaries completed for:
  - `tests/unitTest/cube_unit_test.py`
  - `tests/unitTest/math_unit_test.py`
  - `tests/unitTest/pattern_unit_test.py`

Post-Batch-1 spot re-scan for the update-summary rule:

- C++ files still missing who/date/what `Updated:` summaries: `0`
- Python unit test files still needing `Updated:` summaries: `0`

Completed in the immediate follow-up pass on `2026-04-08`:

- `tests/unitTest/atmos_model_factory_unit_test.py`
- `tests/unitTest/filters_unit_test.py`
- `tests/unitTest/line_equation_unit_test.py`
- `tests/unitTest/low_level_cube_io_unit_test.py`
- `tests/unitTest/utility_unit_test.py`

The repository totals below remain the original baseline counts from the first full audit pass.

## Status update after Batch 2 and Batch 3 header completion

Applied on `2026-04-08`:

- Batch 2 core C++ full-header completion:
  - `src/module.cpp`
  - `src/bind_low_level_cube_io.cpp`
  - `src/bind_camera.cpp`
  - `src/bind_camera_factory.cpp`
  - `src/bind_statistics.cpp`
- Batch 3 foundational Python unit-test module metadata completion:
  - `tests/unitTest/_unit_test_support.py`
  - `tests/unitTest/camera_unit_test.py`
  - `tests/unitTest/projection_unit_test.py`
  - `tests/unitTest/statistics_unit_test.py`
  - `tests/unitTest/high_level_cube_io_unit_test.py`

These updates close the first planned representative passes for:

- core C++ binding aggregators that previously lacked full top-of-file metadata
- foundational Python unit tests that previously lacked module docstrings and baseline metadata

## Status update after Batch 4 base C++ header completion

Applied on `2026-04-08`:

- Batch 4 base C++ full-header completion:
  - `src/base/bind_base_geometry.cpp`
  - `src/base/bind_base_projection.cpp`
  - `src/base/bind_base_projection_types.cpp`
  - `src/base/bind_base_pvl.cpp`
  - `src/base/bind_base_shape.cpp`

These updates continue reducing the remaining backlog of C++ binding files that were missing near-complete top-of-file metadata, with this pass focused on foundational geometry, projection, PVL, and shape-model bindings.

## Status update after Batch 5 support and camera-hierarchy header completion

Applied on `2026-04-08`:

- Batch 5 C++ full-header completion:
  - `src/base/bind_base_shape_support.cpp`
  - `src/base/bind_base_support.cpp`
  - `src/base/bind_base_surface.cpp`
  - `src/base/bind_base_target.cpp`
  - `src/bind_camera_hierarchy.cpp`

These updates extend the full-header cleanup to support utilities, surface and target abstractions, target-shape helper bindings, and the derived camera hierarchy layer.

## Status update after Batch 6 camera-io and helper header completion

Applied on `2026-04-08`:

- Batch 6 C++ full-header completion:
  - `src/bind_camera_maps.cpp`
  - `src/bind_high_level_cube_io.cpp`
  - `src/bind_sensor.cpp`
  - `src/control/bind_bundle_advanced.cpp`
  - `src/helpers.h`

These updates extend the full-header cleanup to camera map helpers, high-level cube I/O workflows, the Sensor base binding, the currently disabled advanced bundle-adjustment binding file, and the shared pybind helper header.

## Post-Batch-6 remaining backlog

Re-scanned on `2026-04-08` after completing Batches 1 through 6.

### Current remaining totals

- C++ files still missing a full top metadata header: `0`
- C++ files still needing only a partial metadata fix: `1`
- C++ files still needing update-summary normalization: `0`
- Python unit tests still missing a full module metadata block: `18`
- Python unit tests still needing an `Updated:` summary normalization pass: `0`

### Remaining C++ partial metadata fix

- `src/base/bind_base_filters.cpp`
  - still missing `Updated:` / `Last Modified:` near the top

### Remaining Python unit tests missing a full module metadata block

- `tests/unitTest/angle_unit_test.py`
- `tests/unitTest/bundle_advanced_unit_test.py`
- `tests/unitTest/camera_maps_unit_test.py`
- `tests/unitTest/displacement_unit_test.py`
- `tests/unitTest/distance_unit_test.py`
- `tests/unitTest/filters_unit_test.py`
  - special case: only the top module docstring remains missing; summary metadata is already normalized
- `tests/unitTest/geometry_unit_test.py`
- `tests/unitTest/latitude_unit_test.py`
- `tests/unitTest/longitude_unit_test.py`
- `tests/unitTest/process_import_unit_test.py`
- `tests/unitTest/process_unit_test.py`
- `tests/unitTest/pvl_unit_test.py`
- `tests/unitTest/serial_number_unit_test.py`
- `tests/unitTest/shape_support_unit_test.py`
- `tests/unitTest/support_unit_test.py`
- `tests/unitTest/surface_point_unit_test.py`
- `tests/unitTest/target_shape_unit_test.py`
- `tests/unitTest/universal_ground_map_unit_test.py`

## Status update after Batch 8 map-support test metadata completion

Applied on `2026-04-08`:

- Python unit-test full module metadata added for:
  - `tests/unitTest/camera_maps_unit_test.py`
  - `tests/unitTest/shape_support_unit_test.py`
  - `tests/unitTest/support_unit_test.py`
  - `tests/unitTest/target_shape_unit_test.py`
  - `tests/unitTest/universal_ground_map_unit_test.py`
- Python unit-test top-of-file docstring placement corrected for:
  - `tests/unitTest/filters_unit_test.py`

These updates continue the Python metadata cleanup across camera-map, support, target-shape, and universal-ground-map regression suites, and also resolve the remaining top-of-file docstring placement issue in `filters_unit_test.py`.

## Post-Batch-8 remaining backlog

Re-scanned status after the Batch 8 edits described above:

### Current remaining totals

- C++ files still missing a full top metadata header: `0`
- C++ files still needing only a partial metadata fix: `0`
- C++ files still needing update-summary normalization: `0`
- Python unit tests still missing a full module metadata block: `5`
- Python unit tests still needing an `Updated:` summary normalization pass: `0`

### Remaining Python unit tests missing a full module metadata block

- `tests/unitTest/bundle_advanced_unit_test.py`
- `tests/unitTest/process_import_unit_test.py`
- `tests/unitTest/process_unit_test.py`
- `tests/unitTest/pvl_unit_test.py`
- `tests/unitTest/serial_number_unit_test.py`

### Interpretation

The C++ metadata backlog is now fully cleared. The remaining cleanup effort is concentrated in five older Python unit-test files that still need standardized top-of-file module metadata.

## Status update after Batch 9 final Python metadata completion

Applied on `2026-04-08`:

- Python unit-test full module metadata added for:
  - `tests/unitTest/bundle_advanced_unit_test.py`
  - `tests/unitTest/process_import_unit_test.py`
  - `tests/unitTest/process_unit_test.py`
  - `tests/unitTest/pvl_unit_test.py`
  - `tests/unitTest/serial_number_unit_test.py`

These updates complete the remaining Python unit-test metadata backlog and close the repository-wide metadata cleanup tracked in this note.

## Metadata cleanup complete

Final re-scan status after Batch 9:

### Final totals

- C++ files still missing a full top metadata header: `0`
- C++ files still needing only a partial metadata fix: `0`
- C++ files still needing update-summary normalization: `0`
- Python unit tests still missing a full module metadata block: `0`
- Python unit tests still needing an `Updated:` summary normalization pass: `0`

### Completion note

The repository-wide metadata cleanup for `src/**/*.{cpp,h}` and `tests/unitTest/**/*.py` is complete as of `2026-04-08`. Earlier backlog sections in this note are retained as historical snapshots of the cleanup sequence.

## Status update after Batch 7 filter-header cleanup and geometry-test metadata start

Applied on `2026-04-08`:

- C++ partial metadata cleanup completed for:
  - `src/base/bind_base_filters.cpp`
- Python unit-test full module metadata added for:
  - `tests/unitTest/angle_unit_test.py`
  - `tests/unitTest/displacement_unit_test.py`
  - `tests/unitTest/distance_unit_test.py`
  - `tests/unitTest/geometry_unit_test.py`
  - `tests/unitTest/latitude_unit_test.py`
  - `tests/unitTest/longitude_unit_test.py`
  - `tests/unitTest/surface_point_unit_test.py`

These updates eliminate the final known C++ metadata gap and begin the remaining Python unit-test metadata cleanup with a geometry and value-type focused batch.

## Post-Batch-7 remaining backlog

Re-scanned status after the Batch 7 edits described above:

### Current remaining totals

- C++ files still missing a full top metadata header: `0`
- C++ files still needing only a partial metadata fix: `0`
- C++ files still needing update-summary normalization: `0`
- Python unit tests still missing a full module metadata block: `11`
- Python unit tests still needing an `Updated:` summary normalization pass: `0`

### Remaining Python unit tests missing a full module metadata block

- `tests/unitTest/bundle_advanced_unit_test.py`
- `tests/unitTest/camera_maps_unit_test.py`
- `tests/unitTest/filters_unit_test.py`
  - special case: only the top module docstring remains missing; summary metadata is already normalized
- `tests/unitTest/process_import_unit_test.py`
- `tests/unitTest/process_unit_test.py`
- `tests/unitTest/pvl_unit_test.py`
- `tests/unitTest/serial_number_unit_test.py`
- `tests/unitTest/shape_support_unit_test.py`
- `tests/unitTest/support_unit_test.py`
- `tests/unitTest/target_shape_unit_test.py`
- `tests/unitTest/universal_ground_map_unit_test.py`

## Audit rules used

### C++ binding files

A C++ file was flagged when the top-of-file metadata was missing any of the following:

- `Binding author:`
- `Created:`
- `Updated:` or `Last Modified:`
- `Purpose:`

A C++ file was also flagged when it had an `Updated:` line but that line did not include a concise human-readable summary in the repository-preferred style:

- who made the update
- the date
- what was added, fixed, or completed

Example preferred style:

- `// Updated: 2026-04-07  Geng Xun completed Apollo, Cassini, Chandrayaan-1, Clementine, Clipper, Galileo, and Juno mission camera/helper bindings.`

### Python unit test files

A Python unit test file was flagged when the top-of-file module metadata was missing any of the following:

- a module docstring at the top of the file
- `Author:`
- `Created:`
- `Last Modified:`

A Python unit test file was also flagged when:

- `Created:` and `Last Modified:` differ, but there is no `Updated:` summary line
- an `Updated:` line exists but does not include a concise who/date/what summary

Example preferred style:

- `Updated: 2026-04-08  Geng Xun added ControlNetFilter regression coverage for newly exposed point/cube filters and helpers.`

## Repository summary

### C++ bindings and helper headers

- Total scanned: `32`
- Flagged: `30`

Breakdown:

- `20` files are missing a near-complete top header (`Binding author`, `Created`, `Updated`, `Purpose`)
- `9` files already have update metadata but need the newer who/date/what summary style
- `1` file is only missing a partial field set

### Python unit tests

- Total scanned: `46`
- Flagged: `30`

Breakdown:

- `22` files are missing a full top module docstring metadata block
- `1` file is missing a docstring and also needs an update-summary pass
- `8` files already have baseline metadata but need an `Updated:` summary

## C++ files needing a full header pass

These files were missing most or all of the standard header metadata fields:

- `src/base/bind_base_geometry.cpp`
- `src/base/bind_base_projection.cpp`
- `src/base/bind_base_projection_types.cpp`
- `src/base/bind_base_pvl.cpp`
- `src/base/bind_base_shape.cpp`
- `src/base/bind_base_shape_support.cpp`
- `src/base/bind_base_support.cpp`
- `src/base/bind_base_surface.cpp`
- `src/base/bind_base_target.cpp`
- `src/bind_camera.cpp`
- `src/bind_camera_factory.cpp`
- `src/bind_camera_hierarchy.cpp`
- `src/bind_camera_maps.cpp`
- `src/bind_high_level_cube_io.cpp`
- `src/bind_low_level_cube_io.cpp`
- `src/bind_sensor.cpp`
- `src/bind_statistics.cpp`
- `src/control/bind_bundle_advanced.cpp`
- `src/helpers.h`
- `src/module.cpp`

## C++ files needing update-summary normalization

These files already contain update metadata, but the `Updated:` line(s) should be refreshed to include the repository-preferred concise who/date/what summary style:

- `src/base/bind_auto_reg_factory.cpp`
- `src/base/bind_base_ground_map.cpp`
- `src/base/bind_base_math.cpp`
- `src/base/bind_base_pattern.cpp`
- `src/base/bind_base_photometry.cpp`
- `src/base/bind_base_utility.cpp`
- `src/control/bind_interest_operator_factory.cpp`
- `src/lro/bind_lro_utilities.cpp`
- `src/mgs/bind_mgs_utilities.cpp`

## C++ files needing only a partial metadata fix

- `src/base/bind_base_filters.cpp`
  - currently missing `Updated:` / `Last Modified:` style metadata near the top

## Python unit tests missing a full module metadata block

These files should receive a top module docstring with purpose, `Author:`, `Created:`, and `Last Modified:`:

- `tests/unitTest/_unit_test_support.py`
- `tests/unitTest/angle_unit_test.py`
- `tests/unitTest/bundle_advanced_unit_test.py`
- `tests/unitTest/camera_maps_unit_test.py`
- `tests/unitTest/camera_unit_test.py`
- `tests/unitTest/displacement_unit_test.py`
- `tests/unitTest/distance_unit_test.py`
- `tests/unitTest/geometry_unit_test.py`
- `tests/unitTest/high_level_cube_io_unit_test.py`
- `tests/unitTest/latitude_unit_test.py`
- `tests/unitTest/longitude_unit_test.py`
- `tests/unitTest/process_import_unit_test.py`
- `tests/unitTest/process_unit_test.py`
- `tests/unitTest/projection_unit_test.py`
- `tests/unitTest/pvl_unit_test.py`
- `tests/unitTest/serial_number_unit_test.py`
- `tests/unitTest/shape_support_unit_test.py`
- `tests/unitTest/statistics_unit_test.py`
- `tests/unitTest/support_unit_test.py`
- `tests/unitTest/surface_point_unit_test.py`
- `tests/unitTest/target_shape_unit_test.py`
- `tests/unitTest/universal_ground_map_unit_test.py`

## Python unit tests needing an `Updated:` summary

These files already have some metadata, but should add or refresh an `Updated:` line with concise who/date/what wording:

- `tests/unitTest/atmos_model_factory_unit_test.py`
- `tests/unitTest/cube_unit_test.py`
- `tests/unitTest/filters_unit_test.py`
- `tests/unitTest/line_equation_unit_test.py`
- `tests/unitTest/low_level_cube_io_unit_test.py`
- `tests/unitTest/math_unit_test.py`
- `tests/unitTest/pattern_unit_test.py`
- `tests/unitTest/utility_unit_test.py`

## Python unit tests with special note

- `tests/unitTest/filters_unit_test.py`
  - currently missing a top module docstring
  - also needs an `Updated:` summary because the file appears to have evolved beyond its original state

## Suggested cleanup order

### Batch 1 — easiest / lowest risk

Normalize files that already have metadata but need the new summary wording:

- `src/base/bind_auto_reg_factory.cpp`
- `src/base/bind_base_ground_map.cpp`
- `src/base/bind_base_math.cpp`
- `src/base/bind_base_pattern.cpp`
- `src/base/bind_base_photometry.cpp`
- `src/base/bind_base_utility.cpp`
- `src/control/bind_interest_operator_factory.cpp`
- `src/lro/bind_lro_utilities.cpp`
- `src/mgs/bind_mgs_utilities.cpp`
- `tests/unitTest/cube_unit_test.py`
- `tests/unitTest/math_unit_test.py`
- `tests/unitTest/pattern_unit_test.py`

### Batch 2 — core C++ files missing full headers

Prefer the more central aggregators first:

- `src/module.cpp`
- `src/bind_low_level_cube_io.cpp`
- `src/bind_camera.cpp`
- `src/bind_camera_factory.cpp`
- `src/bind_statistics.cpp`

### Batch 3 — older Python unit tests missing full docstrings

Prefer files that are frequently extended or act as shared foundations:

- `tests/unitTest/_unit_test_support.py`
- `tests/unitTest/camera_unit_test.py`
- `tests/unitTest/projection_unit_test.py`
- `tests/unitTest/statistics_unit_test.py`
- `tests/unitTest/high_level_cube_io_unit_test.py`

## Notes and limitations

- This audit used a top-of-file heuristic and did not attempt to infer metadata buried deep in a file.
- Some files may intentionally predate the newer metadata convention; they are still listed here if they do not match the current repository guidance.
- This note is for planning and cleanup only; it should not be treated as a build or runtime regression report.

## Follow-up recommendation

When cleaning these files in future batches:

1. Preserve any existing `Created:` date already present in the file.
2. Do not churn metadata for formatting-only edits.
3. When adding `Updated:` lines, use a compact one-line summary with author, date, and completed work.
4. Keep `reference/notes/metadata_audit_2026-04-08.md` as the baseline checklist for future cleanup passes.
