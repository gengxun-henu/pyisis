"""Estimate stereo-pair overlap using sampled geographic bounds from original cubes.

Author: Geng Xun
Created: 2026-04-16
Updated: 2026-04-16  Geng Xun added a non-ISIS overlap workflow that samples original-image camera geometry and writes canonical stereo-pair lists.
Updated: 2026-04-18  Geng Xun tightened overlap semantics to require positive-area intersections, raised the default sampling density to 11x11, and added a Polar Stereographic fallback for high-latitude imagery.
Updated: 2026-04-19  Geng Xun expanded the module-level documentation with a clearer processing flow, runtime assumptions, and overlap-decision constraints.

Overview:
    This utility estimates candidate stereo pairs directly from original ISIS cubes by
    sampling camera geometry rather than by generating DOMs, extracting keypoints, or
    running image matching first. It is intended as a lightweight pre-filter in the
    ControlNet workflow so that obviously non-overlapping image pairs can be excluded
    before more expensive downstream processing.

Primary responsibilities:
    1. Read a list of original cube paths.
    2. Sample each cube through its ISIS camera model.
    3. Convert sampled image positions to ground points.
    4. Build geographic bounding intervals from sampled latitudes/longitudes.
    5. Detect dateline wrapping in a stable way.
    6. For high-latitude imagery, build an auxiliary Polar Stereographic bounding box.
    7. Test every unordered image pair for positive-area overlap.
    8. Write the canonical stereo-pair list and emit JSON diagnostics.

Main processing flow:
    Step 1. Bootstrap the runtime environment so `isis_pybind` and related ISIS runtime
        dependencies are available before the main logic executes.
    Step 2. Read `original_images.lis`-style input paths and keep the input order stable.
    Step 3. For each cube, open it through `ip.Cube`, obtain the camera model, and sample
        a regular grid over image sample/line space.
    Step 4. For each sampled image coordinate, call the camera model to test whether a
        valid surface intersection exists; discard invalid image positions.
    Step 5. Aggregate the valid surface points into latitude, longitude, and local-radius
        samples, then summarize them into a `GeoBounds` record.
    Step 6. Normalize longitudes into the [0, 360) domain and compute the minimal
        longitude interval so dateline-spanning footprints are not misinterpreted.
    Step 7. If a footprint reaches the configured polar zone threshold, project the
        sampled ground points into Polar Stereographic coordinates and build a planar
        auxiliary bounding box for more stable overlap decisions near the poles.
    Step 8. Compare every unordered image pair. Geographic bounds are used by default;
        when both images have compatible polar auxiliary bounds, the polar bounding
        boxes take precedence.
    Step 9. Record overlapping pairs as `StereoPair` entries, write the output list, and
        print a JSON summary containing per-image bounds for debugging and auditing.

Why this file exists:
    In the DOM Matching ControlNet workflow, full image matching is relatively expensive.
    This file provides a geometry-first screening stage that can reject obviously unrelated
    image pairs before the pipeline spends time on DOM preparation, feature extraction,
    tie-point generation, or network merging.

Key dependencies and runtime assumptions:
    - `isis_pybind` must import successfully and be able to access the underlying ISIS
      runtime and camera models.
    - The input files must be original ISIS cubes whose camera models can compute valid
      ground intersections for at least part of the image.
    - This tool estimates overlap from sampled camera geometry; it does not guarantee the
      same answer as dense pixel-level masks or full geometric intersection analysis.

Important overlap rules and constraints:
    - Boundary-only contact does not count as overlap when `tolerance == 0`.
    - A positive tolerance relaxes the geographic fallback test, but the default behavior
      intentionally requires a positive-area intersection.
    - Longitude-based reasoning becomes unstable in extreme polar regions, so the polar
      auxiliary bounding box is used to avoid false overlap decisions caused by longitude
      convergence near ±90° latitude.
    - The result is a candidate-pair filter, not a final photogrammetric validity test.

Outputs:
    - A stereo-pair list suitable for downstream ControlNet stages.
    - A JSON summary containing overlap counts and per-image sampled bounds, which is
      useful for debugging footprint coverage and understanding why a pair was accepted
      or rejected.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import itertools
import json
import logging
import math
from pathlib import Path
import sys


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.listing import StereoPair, read_path_list, write_stereo_pair_list
    from controlnet_construct.runtime import bootstrap_runtime_environment
else:
    from .listing import StereoPair, read_path_list, write_stereo_pair_list
    from .runtime import bootstrap_runtime_environment


bootstrap_runtime_environment()

import isis_pybind as ip


DEFAULT_GRID_SAMPLES = 11
DEFAULT_GRID_LINES = 11
POLAR_LATITUDE_THRESHOLD_DEGREES = 80.0
POLAR_TRUE_SCALE_LATITUDE_DEGREES = 71.0
POLAR_CENTER_LONGITUDE_DEGREES = 0.0


@dataclass(frozen=True, slots=True)
class PolarStereoBounds:
    pole: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    mean_local_radius_meters: float


@dataclass(frozen=True, slots=True)
class GeoBounds:
    path: str
    latitude_min: float
    latitude_max: float
    longitude_start: float
    longitude_end: float
    wraps_dateline: bool
    valid_points: int
    sampled_points: int
    polar_bounds: PolarStereoBounds | None = None


def _ranges_overlap(left_min: float, left_max: float, right_min: float, right_max: float, *, tolerance: float = 0.0) -> bool:
    return not (left_max <= right_min - tolerance or right_max <= left_min - tolerance)


def _linspace_positions(max_value: int, count: int) -> list[float]:
    if count <= 0:
        raise ValueError("The number of grid samples must be positive.")
    if max_value <= 0:
        raise ValueError("Image dimensions must be positive.")
    if count == 1:
        return [(1.0 + float(max_value)) / 2.0]
    step = (float(max_value) - 1.0) / float(count - 1)
    return [1.0 + index * step for index in range(count)]


def _normalize_longitude(longitude: float) -> float:
    normalized = longitude % 360.0
    if normalized < 0.0:
        normalized += 360.0
    return normalized


def _minimal_longitude_interval(longitudes: list[float]) -> tuple[float, float, bool]:
    normalized = sorted(_normalize_longitude(longitude) for longitude in longitudes)
    if not normalized:
        raise ValueError("At least one longitude is required.")

    if len(normalized) == 1:
        value = normalized[0]
        return value, value, False

    extended = normalized + [normalized[0] + 360.0]
    largest_gap = -1.0
    largest_gap_index = 0
    for index in range(len(normalized)):
        gap = extended[index + 1] - extended[index]
        if gap > largest_gap:
            largest_gap = gap
            largest_gap_index = index

    start = normalized[(largest_gap_index + 1) % len(normalized)]
    end = normalized[largest_gap_index]
    wraps = start > end
    return start, end, wraps


def _expand_interval(start: float, end: float, wraps: bool) -> list[tuple[float, float]]:
    if wraps:
        return [(start, 360.0), (0.0, end)]
    return [(start, end)]


def _select_polar_projection_pole(
    latitudes: list[float],
    *,
    threshold: float = POLAR_LATITUDE_THRESHOLD_DEGREES,
) -> str | None:
    if not latitudes:
        return None

    reaches_north_polar_zone = any(latitude >= threshold for latitude in latitudes)
    reaches_south_polar_zone = any(latitude <= -threshold for latitude in latitudes)

    if reaches_north_polar_zone and reaches_south_polar_zone:
        return None
    if reaches_north_polar_zone:
        return "north"
    if reaches_south_polar_zone:
        return "south"
    return None


def _make_polar_stereographic_projection(pole: str, *, local_radius_meters: float) -> ip.PolarStereographic:
    """为指定极区构造 PolarStereographic 投影，并使用局部半径生成稳定的 Mapping 标签。

    Build a PolarStereographic projection for the requested pole and use the local radius
    to generate a stable Mapping label for high-latitude overlap checks.
    """
    if pole not in {"north", "south"}:
        raise ValueError("Polar projection pole must be 'north' or 'south'.")

    safe_local_radius_meters = local_radius_meters if local_radius_meters > 0.0 else 1.0
    center_latitude = POLAR_TRUE_SCALE_LATITUDE_DEGREES if pole == "north" else -POLAR_TRUE_SCALE_LATITUDE_DEGREES
    minimum_latitude = 0.0 if pole == "north" else -90.0
    maximum_latitude = 90.0 if pole == "north" else 0.0

    label = ip.Pvl()
    label.from_string(
        "\n".join(
            [
                "Group = Mapping",
                f"  EquatorialRadius = {safe_local_radius_meters}",
                f"  PolarRadius = {safe_local_radius_meters}",
                "  LatitudeType = Planetocentric",
                "  LongitudeDirection = PositiveEast",
                "  LongitudeDomain = 360",
                f"  MinimumLatitude = {minimum_latitude}",
                f"  MaximumLatitude = {maximum_latitude}",
                "  MinimumLongitude = 0.0",
                "  MaximumLongitude = 360.0",
                "  ProjectionName = PolarStereographic",
                f"  CenterLongitude = {POLAR_CENTER_LONGITUDE_DEGREES}",
                f"  CenterLatitude = {center_latitude}",
                "EndGroup",
                "End",
            ]
        )
        + "\n"
    )
    return ip.PolarStereographic(label)


def _polar_stereo_bounds_from_samples(
    latitudes: list[float],
    longitudes: list[float],
    *,
    local_radius_meters: float,
    pole: str | None = None,
) -> PolarStereoBounds | None:
    """Build an auxiliary polar-planar bounding box from sampled ground points.

    This helper is used only for footprints that enter a north-polar or south-polar
    zone, where longitude intervals become a weak proxy for planar separation. The
    function first decides which pole-specific Polar Stereographic projection to use,
    then reprojects every valid latitude/longitude sample into projected x/y space,
    and finally summarizes those projected coordinates as a simple axis-aligned
    bounding box.

    Returns:
        A `PolarStereoBounds` record when enough projected samples are available to
        define a stable planar extent. Returns `None` when the samples do not belong
        to a single supported polar zone or when too few projected coordinates are
        valid for a meaningful bounding box.
    """
    if not latitudes or not longitudes:
        return None
    if len(latitudes) != len(longitudes):
        raise ValueError("Latitude and longitude sample lists must have the same length.")

    selected_pole = pole if pole is not None else _select_polar_projection_pole(latitudes)
    if selected_pole is None:
        return None

    projection = _make_polar_stereographic_projection(selected_pole, local_radius_meters=local_radius_meters)
    x_values: list[float] = []
    y_values: list[float] = []
    for latitude, longitude in zip(latitudes, longitudes):
        if not projection.set_ground(latitude, _normalize_longitude(longitude)):
            continue
        x_values.append(projection.x_coord())
        y_values.append(projection.y_coord())

    if len(x_values) < 2 or len(y_values) < 2:
        return None

    return PolarStereoBounds(
        pole=selected_pole,
        x_min=min(x_values),
        x_max=max(x_values),
        y_min=min(y_values),
        y_max=max(y_values),
        mean_local_radius_meters=local_radius_meters,
    )


def geographic_bounds_overlap(left: GeoBounds, right: GeoBounds, *, tolerance: float = 0.0) -> bool:
    latitudes_overlap = _ranges_overlap(
        left.latitude_min,
        left.latitude_max,
        right.latitude_min,
        right.latitude_max,
        tolerance=tolerance,
    )
    if not latitudes_overlap:
        return False

    left_intervals = _expand_interval(left.longitude_start, left.longitude_end, left.wraps_dateline)
    right_intervals = _expand_interval(right.longitude_start, right.longitude_end, right.wraps_dateline)

    for left_start, left_end in left_intervals:
        for right_start, right_end in right_intervals:
            if _ranges_overlap(left_start, left_end, right_start, right_end, tolerance=tolerance):
                return True

    return False


def polar_stereo_bounds_overlap(left: PolarStereoBounds, right: PolarStereoBounds) -> bool:
    if left.pole != right.pole:
        return False
    return _ranges_overlap(left.x_min, left.x_max, right.x_min, right.x_max) and _ranges_overlap(
        left.y_min,
        left.y_max,
        right.y_min,
        right.y_max,
    )


def bounds_overlap(left: GeoBounds, right: GeoBounds, *, tolerance: float = 0.0) -> bool:
    """Decide whether two sampled image footprints should be treated as overlapping.

    The overlap policy is intentionally two-stage. If both images provide compatible
    polar auxiliary bounds, the function prefers those projected bounds because they
    are more stable near the poles than raw longitude intervals. Otherwise, it falls
    back to the geographic latitude/longitude test with the caller-provided tolerance.

    This makes the decision rule easy to follow at the pipeline level: use the more
    geometry-stable polar representation when available, and use the geographic
    representation everywhere else.
    """
    if left.polar_bounds is not None and right.polar_bounds is not None:
        return polar_stereo_bounds_overlap(left.polar_bounds, right.polar_bounds)
    return geographic_bounds_overlap(left, right, tolerance=tolerance)


def extract_camera_ground_bounds(
    cube_path: str | Path,
    *,
    grid_samples: int = DEFAULT_GRID_SAMPLES,
    grid_lines: int = DEFAULT_GRID_LINES,
    min_valid_points: int = 4,
) -> GeoBounds | None:
    """Estimate one image footprint by sampling the cube through its camera model.

    Processing flow:
        1. Open the cube and obtain its ISIS camera model.
        2. Generate a regular sample/line grid over image space.
        3. For each grid location, attempt an image-to-ground intersection.
        4. Keep only valid surface points and collect latitude, longitude, and local
           radius samples.
        5. Summarize the valid samples into a geographic bounding interval.
        6. Optionally derive a Polar Stereographic auxiliary bounding box for high-
           latitude imagery.

    Returns:
        A `GeoBounds` record when the camera model yields at least `min_valid_points`
        valid surface intersections. Returns `None` when the image does not provide
        enough valid ground samples to support a reliable overlap estimate.

    Notes:
        The returned structure always contains geographic bounds and may also include a
        Polar Stereographic auxiliary bounding box so later overlap checks remain more
        stable for imagery near the poles.
    """
    cube = ip.Cube()
    cube.open(str(cube_path), "r")
    try:
        camera = cube.camera()
        sample_positions = _linspace_positions(camera.samples(), grid_samples)
        line_positions = _linspace_positions(camera.lines(), grid_lines)

        latitudes: list[float] = []
        longitudes: list[float] = []
        local_radii_meters: list[float] = []
        sampled_points = len(sample_positions) * len(line_positions)

        for sample, line in itertools.product(sample_positions, line_positions):
            if not camera.set_image(sample, line):
                continue
            if not camera.has_surface_intersection():
                continue
            surface_point = camera.get_surface_point()
            if not surface_point.valid():
                continue
            latitudes.append(surface_point.get_latitude().degrees())
            longitudes.append(surface_point.get_longitude().degrees())
            local_radii_meters.append(surface_point.get_local_radius().meters())

        if len(latitudes) < min_valid_points:
            return None

        longitude_start, longitude_end, wraps_dateline = _minimal_longitude_interval(longitudes)
        mean_local_radius_meters = (
            sum(local_radii_meters) / float(len(local_radii_meters)) if local_radii_meters else 1.0
        )
        polar_bounds = _polar_stereo_bounds_from_samples(
            latitudes,
            longitudes,
            local_radius_meters=mean_local_radius_meters,
        )
        return GeoBounds(
            path=str(cube_path),
            latitude_min=min(latitudes),
            latitude_max=max(latitudes),
            longitude_start=longitude_start,
            longitude_end=longitude_end,
            wraps_dateline=wraps_dateline,
            valid_points=len(latitudes),
            sampled_points=sampled_points,
            polar_bounds=polar_bounds,
        )
    finally:
        if cube.is_open():
            cube.close()


def find_overlapping_image_pairs(
    image_paths: list[str],
    *,
    grid_samples: int = DEFAULT_GRID_SAMPLES,
    grid_lines: int = DEFAULT_GRID_LINES,
    min_valid_points: int = 4,
    tolerance: float = 0.0,
) -> tuple[list[StereoPair], dict[str, GeoBounds | None]]:
    """Find all unordered image pairs whose sampled bounds satisfy the overlap rule.

    Processing flow:
        1. Estimate per-image bounds for every input path with
           `extract_camera_ground_bounds`.
        2. Keep a lookup table from image path to its sampled `GeoBounds` result.
        3. Enumerate every unordered image pair exactly once.
        4. Skip pairs whose left or right image could not produce valid bounds.
        5. Apply `bounds_overlap` to decide whether the pair is a candidate stereo pair.
        6. Return both the accepted pair list and the full per-image bounds map so the
           caller can inspect accepted, rejected, and invalid images uniformly.

    Notes:
        Geographic bounds are the default representation, while compatible polar
        auxiliary bounds take precedence for high-latitude pairs.
    """
    bounds_by_path = {
        path: extract_camera_ground_bounds(
            path,
            grid_samples=grid_samples,
            grid_lines=grid_lines,
            min_valid_points=min_valid_points,
        )
        for path in image_paths
    }

    invalid_paths = [p for p, b in bounds_by_path.items() if b is None]
    if invalid_paths:
        for p in invalid_paths:
            logging.warning(
                "Image %s has no valid camera ground bounds and will be excluded from overlap detection.",
                p,
            )

    overlapping_pairs: list[StereoPair] = []
    for left_path, right_path in itertools.combinations(image_paths, 2):
        left_bounds = bounds_by_path[left_path]
        right_bounds = bounds_by_path[right_path]
        if left_bounds is None or right_bounds is None:
            continue
        if bounds_overlap(left_bounds, right_bounds, tolerance=tolerance):
            overlapping_pairs.append(StereoPair(left_path, right_path))

    return overlapping_pairs, bounds_by_path


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estimate overlapping stereo pairs from original ISIS cubes using sampled geographic bounds, with a Polar Stereographic fallback for high-latitude imagery."
    )
    parser.add_argument("input_list", help="Path to original_images.lis.")
    parser.add_argument("output_list", help="Path to write images_overlap.lis.")
    parser.add_argument("--grid-samples", type=int, default=DEFAULT_GRID_SAMPLES, help="Number of sample positions to evaluate per image axis.")
    parser.add_argument("--grid-lines", type=int, default=DEFAULT_GRID_LINES, help="Number of line positions to evaluate per image axis.")
    parser.add_argument("--min-valid-points", type=int, default=4, help="Minimum valid camera intersections required to accept an image footprint.")
    parser.add_argument("--tolerance", type=float, default=0.0, help="Latitude/longitude overlap tolerance in degrees for the geographic fallback path. Boundary-only contact is excluded when tolerance is zero.")
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    image_paths = read_path_list(args.input_list)
    overlapping_pairs, bounds_by_path = find_overlapping_image_pairs(
        image_paths,
        grid_samples=args.grid_samples,
        grid_lines=args.grid_lines,
        min_valid_points=args.min_valid_points,
        tolerance=args.tolerance,
    )
    write_stereo_pair_list(args.output_list, overlapping_pairs)

    print(
        json.dumps(
            {
                "input_count": len(image_paths),
                "overlap_pair_count": len(overlapping_pairs),
                "output_list": args.output_list,
                "bounds": {
                    path: (None if bounds is None else asdict(bounds))
                    for path, bounds in bounds_by_path.items()
                },
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()