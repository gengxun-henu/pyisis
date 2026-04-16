"""Estimate stereo-pair overlap using sampled geographic bounds from original cubes.

Author: Geng Xun
Created: 2026-04-16
Updated: 2026-04-16  Geng Xun added a non-ISIS overlap workflow that samples original-image camera geometry and writes canonical stereo-pair lists.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import itertools
import json
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


def _linspace_positions(max_value: int, count: int) -> list[float]:
    if count <= 0:
        raise ValueError("The number of grid samples must be positive.")
    if max_value <= 0:
        raise ValueError("Image dimensions must be positive.")
    if count == 1:
        return [float(max_value) / 2.0]
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


def geographic_bounds_overlap(left: GeoBounds, right: GeoBounds, *, tolerance: float = 0.0) -> bool:
    latitudes_overlap = not (
        left.latitude_max < right.latitude_min - tolerance
        or right.latitude_max < left.latitude_min - tolerance
    )
    if not latitudes_overlap:
        return False

    left_intervals = _expand_interval(left.longitude_start, left.longitude_end, left.wraps_dateline)
    right_intervals = _expand_interval(right.longitude_start, right.longitude_end, right.wraps_dateline)

    for left_start, left_end in left_intervals:
        for right_start, right_end in right_intervals:
            if not (left_end < right_start - tolerance or right_end < left_start - tolerance):
                return True

    return False


def extract_camera_ground_bounds(
    cube_path: str | Path,
    *,
    grid_samples: int = 5,
    grid_lines: int = 5,
    min_valid_points: int = 4,
) -> GeoBounds | None:
    """Estimate a geographic bounding box by sampling the image through its camera model."""
    cube = ip.Cube()
    cube.open(str(cube_path), "r")
    try:
        camera = cube.camera()
        sample_positions = _linspace_positions(camera.samples(), grid_samples)
        line_positions = _linspace_positions(camera.lines(), grid_lines)

        latitudes: list[float] = []
        longitudes: list[float] = []
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

        if len(latitudes) < min_valid_points:
            return None

        longitude_start, longitude_end, wraps_dateline = _minimal_longitude_interval(longitudes)
        return GeoBounds(
            path=str(cube_path),
            latitude_min=min(latitudes),
            latitude_max=max(latitudes),
            longitude_start=longitude_start,
            longitude_end=longitude_end,
            wraps_dateline=wraps_dateline,
            valid_points=len(latitudes),
            sampled_points=sampled_points,
        )
    finally:
        if cube.is_open():
            cube.close()


def find_overlapping_image_pairs(
    image_paths: list[str],
    *,
    grid_samples: int = 5,
    grid_lines: int = 5,
    min_valid_points: int = 4,
    tolerance: float = 0.0,
) -> tuple[list[StereoPair], dict[str, GeoBounds | None]]:
    """Find unordered image pairs whose sampled geographic bounds overlap."""
    bounds_by_path = {
        path: extract_camera_ground_bounds(
            path,
            grid_samples=grid_samples,
            grid_lines=grid_lines,
            min_valid_points=min_valid_points,
        )
        for path in image_paths
    }

    overlapping_pairs: list[StereoPair] = []
    for left_path, right_path in itertools.combinations(image_paths, 2):
        left_bounds = bounds_by_path[left_path]
        right_bounds = bounds_by_path[right_path]
        if left_bounds is None or right_bounds is None:
            continue
        if geographic_bounds_overlap(left_bounds, right_bounds, tolerance=tolerance):
            overlapping_pairs.append(StereoPair(left_path, right_path))

    return overlapping_pairs, bounds_by_path


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estimate overlapping stereo pairs from original ISIS cubes using sampled camera ground bounds."
    )
    parser.add_argument("input_list", help="Path to original_images.lis.")
    parser.add_argument("output_list", help="Path to write images_overlap.lis.")
    parser.add_argument("--grid-samples", type=int, default=5, help="Number of sample positions to evaluate per image axis.")
    parser.add_argument("--grid-lines", type=int, default=5, help="Number of line positions to evaluate per image axis.")
    parser.add_argument("--min-valid-points", type=int, default=4, help="Minimum valid camera intersections required to accept an image footprint.")
    parser.add_argument("--tolerance", type=float, default=0.0, help="Latitude/longitude overlap tolerance in degrees.")
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