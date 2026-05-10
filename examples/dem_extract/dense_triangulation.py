"""Triangulate dense disparity maps into 3D points.

Author: Geng Xun
Created: 2026-05-10
Last Modified: 2026-05-10
"""

from __future__ import annotations

from typing import Iterator

import numpy as np

from .triangulation import FilterOptions, TriangulatedPoint


def _filter_reason(
    radius_m: float,
    sepang_deg: float,
    error_m: float,
    filters: FilterOptions,
) -> str | None:
    if filters.max_error_m is not None and error_m > filters.max_error_m:
        return "filtered_error"
    if filters.min_sepang_deg is not None and sepang_deg < filters.min_sepang_deg:
        return "filtered_sepang"
    if filters.min_radius_m is not None and radius_m < filters.min_radius_m:
        return "filtered_radius"
    if filters.max_radius_m is not None and radius_m > filters.max_radius_m:
        return "filtered_radius"
    return None


def dense_triangulate_from_disparity(
    left_cube,
    right_cube,
    disparity_x: np.ndarray,
    disparity_y: np.ndarray,
    ncc_score: np.ndarray,
    filters: FilterOptions,
    ip,
    ncc_threshold: float = 0.70,
    nodata_value: float = -9999.0,
) -> Iterator[TriangulatedPoint]:
    """Iterate valid disparity pixels and triangulate each into a TriangulatedPoint.

    Uses an iterator pattern for memory efficiency.
    """
    left_camera = left_cube.camera()
    right_camera = right_cube.camera()
    lines, samples = disparity_x.shape

    for l in range(lines):
        for s in range(samples):
            dx = float(disparity_x[l, s])
            dy = float(disparity_y[l, s])
            ncc = float(ncc_score[l, s])

            if ncc < ncc_threshold:
                continue
            if dx <= nodata_value or dy <= nodata_value or ncc <= nodata_value:
                continue

            left_s = float(s + 1)  # 1-based ISIS coordinates
            left_l = float(l + 1)
            right_s = left_s + dx
            right_l = left_l + dy

            if not left_camera.set_image(left_s, left_l):
                continue
            if not right_camera.set_image(right_s, right_l):
                continue

            try:
                success, radius_m, lat, lon, sepang, error = ip.Stereo.elevation(
                    left_camera, right_camera
                )
            except Exception:
                continue
            if not success:
                continue

            if _filter_reason(radius_m, sepang, error, filters) is not None:
                continue

            x_km, y_km, z_km = ip.Stereo.spherical(lat, lon, radius_m)

            yield TriangulatedPoint(
                index=l * samples + s,
                left_sample=left_s,
                left_line=left_l,
                right_sample=right_s,
                right_line=right_l,
                status="success",
                reason="",
                latitude_deg=lat,
                longitude_deg=lon,
                radius_m=radius_m,
                sepang_deg=sepang,
                intersection_error_m=error,
                x_km=x_km,
                y_km=y_km,
                z_km=z_km,
            )
