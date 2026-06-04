"""Pure ground-distance prefilter helpers for aligned stereo `.key` files."""

from __future__ import annotations

import math
from pathlib import Path
from statistics import median
from typing import Callable

try:
    from image_match.keypoints import Keypoint, KeypointFile, read_key_file, write_key_file
except ImportError:  # pragma: no cover - exercised when imported as a local package fallback.
    from .keypoints import Keypoint, KeypointFile, read_key_file, write_key_file


LUNAR_MEAN_RADIUS_KM = 1737.4
PREFILTER_METADATA_KEY = "pre_ransac_ground_distance_filter"
GroundLookup = Callable[[float, float], tuple[float, float] | None]


def _validate_threshold(threshold_km: float) -> float:
    threshold = float(threshold_km)
    if not math.isfinite(threshold) or threshold < 0.0:
        raise ValueError("Ground-distance threshold must be a finite, non-negative value.")
    return threshold


def _normalize_longitude_delta_degrees(delta: float) -> float:
    return ((float(delta) + 180.0) % 360.0) - 180.0


def _validate_finite_coordinate(value: float, name: str) -> float:
    coordinate = float(value)
    if not math.isfinite(coordinate):
        raise ValueError(f"{name} must be finite.")
    return coordinate


def ground_distance_km(
    left_lat: float,
    left_lon: float,
    right_lat: float,
    right_lon: float,
    *,
    radius_km: float = LUNAR_MEAN_RADIUS_KM,
) -> float:
    """Return spherical haversine distance in kilometers with longitude wrap."""
    radius = float(radius_km)
    if not math.isfinite(radius) or radius <= 0.0:
        raise ValueError("radius_km must be a finite, positive value.")

    left_latitude = _validate_finite_coordinate(left_lat, "left_lat")
    left_longitude = _validate_finite_coordinate(left_lon, "left_lon")
    right_latitude = _validate_finite_coordinate(right_lat, "right_lat")
    right_longitude = _validate_finite_coordinate(right_lon, "right_lon")

    lat1 = math.radians(left_latitude)
    lat2 = math.radians(right_latitude)
    delta_lat = math.radians(right_latitude - left_latitude)
    delta_lon = math.radians(_normalize_longitude_delta_degrees(right_longitude - left_longitude))

    sin_half_lat = math.sin(delta_lat / 2.0)
    sin_half_lon = math.sin(delta_lon / 2.0)
    haversine = sin_half_lat**2 + math.cos(lat1) * math.cos(lat2) * sin_half_lon**2
    central_angle = 2.0 * math.asin(min(1.0, math.sqrt(haversine)))
    return radius * central_angle


def _distance_summary(distances: list[float]) -> dict[str, object]:
    if not distances:
        return {
            "count": 0,
            "min": None,
            "mean": None,
            "median": None,
            "p90": None,
            "max": None,
        }

    sorted_distances = sorted(distances)
    p90_index = math.ceil(0.9 * len(sorted_distances)) - 1
    return {
        "count": len(sorted_distances),
        "min": sorted_distances[0],
        "mean": sum(sorted_distances) / len(sorted_distances),
        "median": median(sorted_distances),
        "p90": sorted_distances[p90_index],
        "max": sorted_distances[-1],
    }


def _disabled_summary(
    left_key_file: KeypointFile,
    right_key_file: KeypointFile,
    threshold_km: float,
    lookup_failure_policy: str,
    lunar_radius_km: float,
) -> dict[str, object]:
    return {
        "applied": False,
        "already_prefiltered": False,
        "status": "disabled",
        "threshold_km": threshold_km,
        "lookup_failure_policy": lookup_failure_policy,
        "lunar_radius_km": lunar_radius_km,
        "input_count": len(left_key_file.points),
        "retained_count": len(left_key_file.points),
        "dropped_count": 0,
        "dropped_ground_distance_count": 0,
        "ground_lookup_failure_count": 0,
        "distance_summary_km": _distance_summary([]),
        "max_ground_distance_km": None,
    }


def _validate_lookup_failure_policy(lookup_failure_policy: str) -> str:
    if lookup_failure_policy not in {"drop", "keep"}:
        raise ValueError("lookup_failure_policy must be 'drop' or 'keep'.")
    return lookup_failure_policy


def filter_stereo_pair_keypoints_by_ground_distance(
    left_key_file: KeypointFile,
    right_key_file: KeypointFile,
    *,
    left_ground_lookup: GroundLookup,
    right_ground_lookup: GroundLookup,
    threshold_km: float,
    lookup_failure_policy: str = "drop",
    lunar_radius_km: float = LUNAR_MEAN_RADIUS_KM,
    space: str | None = None,
    geometry_source: str | None = None,
) -> tuple[KeypointFile, KeypointFile, dict[str, object]]:
    if len(left_key_file.points) != len(right_key_file.points):
        raise ValueError("Left and right keypoint files must contain the same number of points.")

    threshold = _validate_threshold(threshold_km)
    radius = float(lunar_radius_km)
    if not math.isfinite(radius) or radius <= 0.0:
        raise ValueError("lunar_radius_km must be a finite, positive value.")
    policy = _validate_lookup_failure_policy(lookup_failure_policy)

    if threshold == 0.0:
        return (
            left_key_file,
            right_key_file,
            _disabled_summary(left_key_file, right_key_file, threshold, policy, radius),
        )

    retained_left_points: list[Keypoint] = []
    retained_right_points: list[Keypoint] = []
    distances: list[float] = []
    dropped_ground_distance_count = 0
    ground_lookup_failure_count = 0

    for left_point, right_point in zip(left_key_file.points, right_key_file.points, strict=True):
        left_ground = left_ground_lookup(left_point.sample, left_point.line)
        right_ground = right_ground_lookup(right_point.sample, right_point.line)
        if left_ground is None or right_ground is None:
            ground_lookup_failure_count += 1
            if policy == "keep":
                retained_left_points.append(left_point)
                retained_right_points.append(right_point)
            continue

        distance = ground_distance_km(
            left_ground[0],
            left_ground[1],
            right_ground[0],
            right_ground[1],
            radius_km=radius,
        )
        distances.append(distance)
        if distance > threshold:
            dropped_ground_distance_count += 1
            continue
        retained_left_points.append(left_point)
        retained_right_points.append(right_point)

    retained_count = len(retained_left_points)
    distance_summary = _distance_summary(distances)
    summary: dict[str, object] = {
        "applied": True,
        "already_prefiltered": False,
        "status": "filtered",
        "threshold_km": threshold,
        "lookup_failure_policy": policy,
        "lunar_radius_km": radius,
        "input_count": len(left_key_file.points),
        "retained_count": retained_count,
        "dropped_count": len(left_key_file.points) - retained_count,
        "dropped_ground_distance_count": dropped_ground_distance_count,
        "ground_lookup_failure_count": ground_lookup_failure_count,
        "distance_summary_km": distance_summary,
        "max_ground_distance_km": distance_summary["max"],
    }
    if space:
        summary["space"] = space
    if geometry_source:
        summary["geometry_source"] = geometry_source

    return (
        KeypointFile(left_key_file.image_width, left_key_file.image_height, tuple(retained_left_points)),
        KeypointFile(right_key_file.image_width, right_key_file.image_height, tuple(retained_right_points)),
        summary,
    )


def filter_stereo_pair_key_files_by_ground_distance(
    left_input: str | Path,
    right_input: str | Path,
    left_output: str | Path,
    right_output: str | Path,
    *,
    left_ground_lookup: GroundLookup,
    right_ground_lookup: GroundLookup,
    threshold_km: float,
    lookup_failure_policy: str = "drop",
    lunar_radius_km: float = LUNAR_MEAN_RADIUS_KM,
    space: str | None = None,
    geometry_source: str | None = None,
) -> dict[str, object]:
    left_key_file = read_key_file(left_input)
    right_key_file = read_key_file(right_input)
    filtered_left, filtered_right, summary = filter_stereo_pair_keypoints_by_ground_distance(
        left_key_file,
        right_key_file,
        left_ground_lookup=left_ground_lookup,
        right_ground_lookup=right_ground_lookup,
        threshold_km=threshold_km,
        lookup_failure_policy=lookup_failure_policy,
        lunar_radius_km=lunar_radius_km,
        space=space,
        geometry_source=geometry_source,
    )
    write_key_file(left_output, filtered_left)
    write_key_file(right_output, filtered_right)
    return {
        **summary,
        "left_input": str(left_input),
        "right_input": str(right_input),
        "left_output": str(left_output),
        "right_output": str(right_output),
    }


__all__ = [
    "GroundLookup",
    "LUNAR_MEAN_RADIUS_KM",
    "PREFILTER_METADATA_KEY",
    "filter_stereo_pair_key_files_by_ground_distance",
    "filter_stereo_pair_keypoints_by_ground_distance",
    "ground_distance_km",
]
