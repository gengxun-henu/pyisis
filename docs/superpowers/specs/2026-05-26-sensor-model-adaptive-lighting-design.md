# Sensor-Model Adaptive Lighting Design

Date: 2026-05-26

## Context

Adaptive matcher routing currently computes pair lighting difference through
`examples/image_match/lighting_difference.py`. The existing reader first looks
for solar elevation and azimuth keywords in ISIS cube labels, under groups such
as `Instrument` and `Photometry`.

Real LRO test data in
`/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test2` showed that
the cube labels do not contain those caminfo-style lighting geometry fields.
As a result, real-data adaptive-routing reports currently show
`lighting_difference_score: null`, even though ISIS can compute lighting
geometry from the cube sensor model.

The correct source for runtime adaptive lighting should be the ISIS camera
model, not label keywords.

## Goal

Use the ISIS cube sensor model as the primary source of solar geometry for
adaptive lighting. For each cube, position the camera at the image center with
`Camera.set_image(sample, line)`, then derive:

- `solar_azimuth_degrees` from `Camera.sun_azimuth()`
- `solar_elevation_degrees` from `90.0 - Camera.incidence_angle()`

This makes real ISIS cubes usable for lighting-aware routing without depending
on external caminfo text output or nonstandard label keywords.

## Architecture

`read_solar_geometry_from_cube()` remains the public entry point. Its internal
order becomes:

1. Try sensor-model center geometry.
2. If the sensor-model path is unavailable or fails, try the existing label
   keyword fallback.
3. If both fail, raise `SolarGeometryFieldMissing` with both causes.

The sensor-model path uses the open `ip.Cube` object:

- Get `camera = cube.camera()`.
- Compute the center coordinate with the ISIS 1-based image convention:
  `sample = (cube.sample_count() + 1) / 2.0` and
  `line = (cube.line_count() + 1) / 2.0`.
- Call `camera.set_image(sample, line)`.
- If it succeeds, read `camera.sun_azimuth()` and `camera.incidence_angle()`.
- Convert incidence angle to solar elevation as `90.0 - incidence_angle`.

The returned `SolarGeometry` should identify the source clearly:

- `source_group_name = "SensorModelCenter"`
- `elevation_keyword = "90-IncidenceAngle"`
- `azimuth_keyword = "SunAzimuth"`

The old label fallback keeps its existing metadata values so downstream JSON can
distinguish sensor-model geometry from label-derived geometry.

## Data Flow

Adaptive routing already calls `_compute_texture_sparseness_and_geometry_from_cube_path()`,
which opens each preview or original cube and calls `read_solar_geometry_from_cube()`.
No new routing entry point is needed.

For DOM-space routing, lighting geometry is computed from the low-resolution DOM
previews when those previews carry a usable sensor model. If the generated DOM
preview cannot initialize a camera, the existing fallback behavior applies.

For original-image routing, lighting geometry is computed directly from the
original ISIS cubes. This is the most important path for the LRO real-data case.

The downstream `compute_lighting_difference()` function remains unchanged. It
already supports combined elevation and azimuth scoring, azimuth-only scoring,
and elevation-only scoring.

## Error Handling

Sensor-model failures should not crash adaptive routing by themselves. The
reader should capture a concise reason for failures such as:

- cube object has no `camera()` method;
- camera initialization fails because ISISDATA or kernels are unavailable;
- cube dimensions are unavailable;
- `camera.set_image(center_sample, center_line)` returns false;
- `sun_azimuth()` or `incidence_angle()` raises or returns a non-finite value.

After a sensor-model failure, the reader tries label keywords. If label keywords
also fail, the final `SolarGeometryFieldMissing` message includes both the
sensor-model failure and the label fallback failure.

Adaptive-routing diagnostics should continue to report missing geometry in the
sidecar instead of failing the whole match.

## Testing

Unit tests should use fake cube and camera objects so they do not depend on
SPICE kernels:

- sensor model succeeds and returns `sun_azimuth` plus
  `90.0 - incidence_angle`;
- sensor model uses the expected center coordinate;
- sensor-model failure falls back to the existing label keyword reader;
- both sensor-model and label fallback failures raise
  `SolarGeometryFieldMissing` with both causes;
- adaptive-routing diagnostics produce a finite lighting score when fake sensor
  geometry is available.

Verification should also rerun the real LRO route diagnostic for
`pipe_test2`. The expected real-data outcome is:

- six pair diagnostics complete;
- `lighting_difference_score` is finite rather than null;
- route source metadata shows `SensorModelCenter`;
- low-lighting-difference LRO pairs still route to the traditional matcher when
  texture is rich.

## Out Of Scope

This design does not add new pybind bindings. The required runtime methods are
already available through `Camera.set_image()`, `Camera.sun_azimuth()`, and
`Sensor.incidence_angle()`.

This design does not parse caminfo text files. Caminfo is treated as a reporting
artifact, not as the runtime source of adaptive-lighting geometry.

This design does not change matcher thresholds, cascade ordering, deep preset
selection, or ControlNet materialization behavior.
