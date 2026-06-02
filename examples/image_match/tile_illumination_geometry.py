"""Representative-point geometry for tile-level illumination sampling."""

from __future__ import annotations

from collections.abc import Callable, Iterator
import math
from pathlib import Path
from typing import Any

import numpy as np

from .tile_illumination import RepresentativePoint, TileIlluminationSample, TileWindowMetadata


ProjectionResult = dict[str, float]
DEFAULT_SPECIAL_PIXEL_ABS_THRESHOLD = float(np.finfo(np.float32).max)


def pixel_available(
    value: float,
    *,
    special_pixel_abs_threshold: float | None = DEFAULT_SPECIAL_PIXEL_ABS_THRESHOLD,
) -> bool:
    """Return whether a DOM pixel exists for representative-point selection."""
    resolved = float(value)
    if not math.isfinite(resolved):
        return False
    if special_pixel_abs_threshold is not None and abs(resolved) >= float(special_pixel_abs_threshold):
        return False
    return True


def representative_candidate_offsets(width: int, height: int) -> Iterator[tuple[int, int]]:
    """Yield center-first candidate offsets with deterministic distance ordering."""
    if width <= 0 or height <= 0:
        return
    center_x = width // 2
    center_y = height // 2
    candidates = [(x, y) for y in range(height) for x in range(width)]
    candidates.sort(
        key=lambda xy: (
            (xy[0] - center_x) ** 2 + (xy[1] - center_y) ** 2,
            xy[1],
            xy[0],
        )
    )
    yield from candidates


def select_representative_point(
    *,
    dom_values: np.ndarray,
    tile_start_x: int,
    tile_start_y: int,
    radiometric_valid_for_matching_mask: np.ndarray | None = None,
    project_source_pixel: Callable[[float, float], ProjectionResult],
    side: str = "left",
    dom_path: str = "",
    dom_source_cube: str = "",
    upstream_source_cube: str | None = None,
    tile_index: int = 0,
    special_pixel_abs_threshold: float | None = DEFAULT_SPECIAL_PIXEL_ABS_THRESHOLD,
) -> TileIlluminationSample:
    """Select the nearest source-projectable DOM pixel for tile illumination."""
    values = np.asarray(dom_values, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("dom_values must be a 2-D array.")

    height, width = values.shape
    tile_window = TileWindowMetadata(
        start_x=int(tile_start_x),
        start_y=int(tile_start_y),
        width=int(width),
        height=int(height),
    )
    radiometric_mask = (
        None
        if radiometric_valid_for_matching_mask is None
        else np.asarray(radiometric_valid_for_matching_mask, dtype=bool)
    )
    if radiometric_mask is not None and radiometric_mask.shape != values.shape:
        raise ValueError("radiometric_valid_for_matching_mask must match dom_values shape.")

    for local_x, local_y in representative_candidate_offsets(width, height):
        if not pixel_available(
            values[local_y, local_x],
            special_pixel_abs_threshold=special_pixel_abs_threshold,
        ):
            continue

        dom_sample = float(tile_start_x + local_x + 1)
        dom_line = float(tile_start_y + local_y + 1)
        try:
            projected = project_source_pixel(dom_sample, dom_line)
            latitude = _finite_required(projected["latitude"], "dom_ground_map_set_image_failed")
            longitude = _finite_required(projected["longitude"], "dom_ground_map_set_image_failed")
            source_sample = _finite_required(
                projected["source_sample"],
                "source_ground_map_set_universal_ground_failed",
            )
            source_line = _finite_required(
                projected["source_line"],
                "source_ground_map_set_universal_ground_failed",
            )
            sun_azimuth = _finite_required(
                projected["sun_azimuth"],
                "solar_geometry_missing_or_non_finite",
            )
            incidence = _finite_required(
                projected["incidence"],
                "solar_geometry_missing_or_non_finite",
            )
        except Exception as exc:  # noqa: BLE001
            _projection_failure_reason(exc)
            continue

        center_x = width // 2
        center_y = height // 2
        status = (
            "center_projectable"
            if local_x == center_x and local_y == center_y
            else "nearest_projectable_pixel"
        )
        representative = RepresentativePoint(
            status=status,
            selection_reason=(
                "center pixel projected to source camera"
                if status == "center_projectable"
                else "nearest pixel projected to source camera"
            ),
            local_x_0_based=int(local_x),
            local_y_0_based=int(local_y),
            dom_sample_1_based=dom_sample,
            dom_line_1_based=dom_line,
            pixel_available=True,
            radiometric_valid_for_matching=(
                None if radiometric_mask is None else bool(radiometric_mask[local_y, local_x])
            ),
            source_projectable=True,
            failure_reason=None,
        )
        return TileIlluminationSample(
            side=side,
            dom_path=dom_path,
            dom_source_cube=dom_source_cube,
            upstream_source_cube=upstream_source_cube,
            tile_index=int(tile_index),
            tile_window_0_based=tile_window,
            representative_point=representative,
            latitude=latitude,
            longitude=longitude,
            source_sample_1_based=source_sample,
            source_line_1_based=source_line,
            sun_azimuth_degrees=sun_azimuth,
            incidence_angle_degrees=incidence,
            solar_elevation_degrees=90.0 - incidence,
        )

    representative = RepresentativePoint(
        status="no_projectable_pixel",
        selection_reason="no pixel projected to source camera",
        local_x_0_based=None,
        local_y_0_based=None,
        dom_sample_1_based=None,
        dom_line_1_based=None,
        pixel_available=False,
        radiometric_valid_for_matching=None,
        source_projectable=False,
        failure_reason="no_projectable_pixel",
    )
    return TileIlluminationSample.failed(
        side=side,
        dom_path=dom_path,
        dom_source_cube=dom_source_cube,
        upstream_source_cube=upstream_source_cube,
        tile_index=int(tile_index),
        tile_window_0_based=tile_window,
        representative_point=representative,
    )


def _finite_required(value: Any, reason: str) -> float:
    resolved = float(value)
    if not math.isfinite(resolved):
        raise ValueError(reason)
    return resolved


def _projection_failure_reason(exc: Exception) -> str:
    text = str(exc).lower()
    if "solar" in text or "sun" in text or "incidence" in text:
        return "solar_geometry_missing_or_non_finite"
    if "camera" in text:
        return "source_camera_set_image_failed"
    if "source" in text:
        return "source_ground_map_set_universal_ground_failed"
    return "dom_ground_map_set_image_failed"


def build_pyisis_projector(
    *,
    dom_path: str | Path,
    source_cube_path: str | Path,
) -> Callable[[float, float], ProjectionResult]:
    """Build a PyISIS DOM-to-source projector for tile illumination sampling."""
    from .runtime import bootstrap_runtime_environment

    bootstrap_runtime_environment()
    import isis_pybind as ip

    dom_cube = ip.Cube()
    source_cube = ip.Cube()
    dom_cube.open(str(dom_path), "r")
    source_cube.open(str(source_cube_path), "r")
    dom_ground_map = ip.UniversalGroundMap(
        dom_cube,
        ip.UniversalGroundMap.CameraPriority.ProjectionFirst,
    )
    source_ground_map = ip.UniversalGroundMap(
        source_cube,
        ip.UniversalGroundMap.CameraPriority.CameraFirst,
    )
    source_camera = source_cube.camera()

    def project(dom_sample: float, dom_line: float) -> ProjectionResult:
        if not dom_ground_map.set_image(float(dom_sample), float(dom_line)):
            raise RuntimeError("dom_ground_map_set_image_failed")
        latitude = float(dom_ground_map.universal_latitude())
        longitude = float(dom_ground_map.universal_longitude())
        if not source_ground_map.set_universal_ground(latitude, longitude):
            raise RuntimeError("source_ground_map_set_universal_ground_failed")
        source_sample = float(source_ground_map.sample())
        source_line = float(source_ground_map.line())
        if not source_camera.set_image(source_sample, source_line):
            raise RuntimeError("source_camera_set_image_failed")
        return {
            "latitude": latitude,
            "longitude": longitude,
            "source_sample": source_sample,
            "source_line": source_line,
            "sun_azimuth": float(source_camera.sun_azimuth()),
            "incidence": float(source_camera.incidence_angle()),
        }

    return project
