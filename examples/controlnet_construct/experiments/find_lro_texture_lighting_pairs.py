"""Find LRO NAC stereo-pair candidates by latitude, texture, and lighting.

Author: Geng Xun
Created: 2026-05-29
Updated: 2026-05-29  Geng Xun added reusable batch selection for latitude-banded
    LRO NAC CUBE pairs using texture-sparseness and lighting-difference metrics.
"""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import Any, Iterable

import numpy as np


EXAMPLES_DIR = Path(__file__).resolve().parents[2]
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from image_match.lighting_difference import SolarGeometry, compute_lighting_difference
from image_match.preprocess import summarize_valid_pixels
from image_match.texture_sparseness import (
    ImageSparsenessSummary,
    compute_image_texture_sparseness_from_reader,
)
from image_match.tile_matching import _read_cube_window, _resolved_invalid_values_for_cube
from image_match.tiling import TileWindow


import isis_pybind as ip


DEFAULT_INPUT_DIR = Path("/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S")
DEFAULT_OUTPUT_DIR_NAME = "texture_lighting_pair_selection"
DEFAULT_CUBE_PATTERN = "REDUCED_*.echo.cal.cub"
DEFAULT_LATITUDE_BANDS = (
    ("south-85-to-89.9", -89.9, -85.0),
    ("south-80-to-82", -82.0, -80.0),
)
DEFAULT_INVALID_SPECIAL_PIXEL_ABS_THRESHOLD = 1.0e300
DEFAULT_MAX_CENTER_LATITUDE_GAP_DEGREES = 1.0
DEFAULT_MAX_CENTER_LONGITUDE_GAP_DEGREES = 3.0
DEFAULT_CONSISTENT_LIGHTING_MAX = 0.02
DEFAULT_INCONSISTENT_LIGHTING_MIN = 0.20
PRODUCT_RE = re.compile(r"^REDUCED_(?P<base>.+?)(?P<eye>[LR]E)\.echo\.cal\.cub$")


@dataclass(frozen=True, slots=True)
class LatitudeBand:
    name: str
    minimum_latitude: float
    maximum_latitude: float

    def contains(self, latitude: float | None) -> bool:
        if latitude is None or not math.isfinite(latitude):
            return False
        return self.minimum_latitude <= latitude <= self.maximum_latitude


@dataclass(frozen=True, slots=True)
class ImageMetric:
    cube_path: str
    product_id: str
    observation_id: str
    eye: str | None
    sample_count: int
    line_count: int
    center_sample: float | None
    center_line: float | None
    center_latitude: float | None
    center_longitude: float | None
    latitude_min: float | None
    latitude_max: float | None
    longitude_min: float | None
    longitude_max: float | None
    solar_elevation_degrees: float | None
    solar_azimuth_degrees: float | None
    incidence_degrees: float | None
    emission_degrees: float | None
    phase_degrees: float | None
    image_texture_sparseness: float | None
    texture_tile_valid_count: int
    texture_tile_total_count: int
    status: str
    error: str | None


@dataclass(frozen=True, slots=True)
class PairMetric:
    latitude_band: str
    left_cube_path: str
    right_cube_path: str
    left_product_id: str
    right_product_id: str
    left_observation_id: str
    right_observation_id: str
    left_eye: str | None
    right_eye: str | None
    center_latitude_gap_degrees: float | None
    center_longitude_gap_degrees: float | None
    pair_texture_sparseness: float | None
    weaker_texture_side: str | None
    lighting_difference_score: float | None
    solar_elevation_difference_degrees: float | None
    solar_azimuth_difference_degrees: float | None
    left_center_latitude: float | None
    right_center_latitude: float | None
    left_center_longitude: float | None
    right_center_longitude: float | None
    left_texture_sparseness: float | None
    right_texture_sparseness: float | None
    left_solar_elevation_degrees: float | None
    right_solar_elevation_degrees: float | None
    left_solar_azimuth_degrees: float | None
    right_solar_azimuth_degrees: float | None


def _finite_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(resolved):
        return None
    return resolved


def _angular_gap_degrees(left: float | None, right: float | None) -> float | None:
    left_value = _finite_float(left)
    right_value = _finite_float(right)
    if left_value is None or right_value is None:
        return None
    raw = abs(left_value - right_value) % 360.0
    return float(360.0 - raw if raw > 180.0 else raw)


def _linear_gap(left: float | None, right: float | None) -> float | None:
    left_value = _finite_float(left)
    right_value = _finite_float(right)
    if left_value is None or right_value is None:
        return None
    return abs(left_value - right_value)


def _parse_product(cube_path: Path) -> tuple[str, str, str | None]:
    match = PRODUCT_RE.match(cube_path.name)
    if match:
        observation_id = match.group("base")
        eye = match.group("eye")
        return f"{observation_id}{eye}", observation_id, eye
    product_id = cube_path.stem
    return product_id, product_id, None


def _sample_points(sample_count: int, line_count: int) -> tuple[tuple[float, float], ...]:
    center_sample = (sample_count + 1.0) / 2.0
    center_line = (line_count + 1.0) / 2.0
    sample_margin = max(1.0, sample_count * 0.05)
    line_margin = max(1.0, line_count * 0.05)
    return (
        (center_sample, center_line),
        (sample_margin, line_margin),
        (max(1.0, sample_count - sample_margin + 1.0), line_margin),
        (sample_margin, max(1.0, line_count - line_margin + 1.0)),
        (max(1.0, sample_count - sample_margin + 1.0), max(1.0, line_count - line_margin + 1.0)),
    )


def _camera_geometry_from_open_cube(cube: ip.Cube) -> dict[str, float | None]:
    sample_count = int(cube.sample_count())
    line_count = int(cube.line_count())
    camera = cube.camera()
    samples: list[dict[str, float]] = []
    for sample, line in _sample_points(sample_count, line_count):
        try:
            if not camera.set_image(float(sample), float(line)):
                continue
            row = {
                "sample": float(sample),
                "line": float(line),
                "latitude": float(camera.universal_latitude()),
                "longitude": float(camera.universal_longitude()),
            }
            for output_name, method_name in (
                ("incidence", "incidence_angle"),
                ("emission", "emission_angle"),
                ("phase", "phase_angle"),
                ("sun_azimuth", "sun_azimuth"),
            ):
                method = getattr(camera, method_name, None)
                if method is None:
                    continue
                value = _finite_float(method())
                if value is not None:
                    row[output_name] = value
            samples.append(row)
        except Exception:
            continue

    if not samples:
        raise RuntimeError("camera did not return valid geometry for any sampled image point")

    center = samples[0]
    latitudes = [row["latitude"] for row in samples if _finite_float(row.get("latitude")) is not None]
    longitudes = [row["longitude"] for row in samples if _finite_float(row.get("longitude")) is not None]
    incidence = _finite_float(center.get("incidence"))
    return {
        "center_sample": _finite_float(center.get("sample")),
        "center_line": _finite_float(center.get("line")),
        "center_latitude": _finite_float(center.get("latitude")),
        "center_longitude": _finite_float(center.get("longitude")),
        "latitude_min": min(latitudes) if latitudes else None,
        "latitude_max": max(latitudes) if latitudes else None,
        "longitude_min": min(longitudes) if longitudes else None,
        "longitude_max": max(longitudes) if longitudes else None,
        "solar_elevation_degrees": None if incidence is None else 90.0 - incidence,
        "solar_azimuth_degrees": _finite_float(center.get("sun_azimuth")),
        "incidence_degrees": incidence,
        "emission_degrees": _finite_float(center.get("emission")),
        "phase_degrees": _finite_float(center.get("phase")),
    }


def _delete_shape_model_from_cube_label(cube_path: Path) -> None:
    cube = ip.Cube()
    cube.open(str(cube_path), "rw")
    try:
        if not cube.has_group("Kernels"):
            return
        kernels = cube.group("Kernels")
        if kernels.has_keyword("ShapeModel"):
            kernels.delete_keyword("ShapeModel")
            cube.put_group(kernels)
    finally:
        if cube.is_open():
            cube.close()


def _camera_geometry_with_temporary_shape_fallback(cube_path: Path, *, temp_dir: Path | None) -> dict[str, float | None]:
    cube = ip.Cube()
    cube.open(str(cube_path), "r")
    try:
        return _camera_geometry_from_open_cube(cube)
    finally:
        if cube.is_open():
            cube.close()


def _camera_geometry_from_shape_stripped_copy(cube_path: Path, *, temp_dir: Path | None) -> dict[str, float | None]:
    parent = temp_dir if temp_dir is not None else Path(tempfile.gettempdir())
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lro_pair_geom_", dir=str(parent)) as work_dir:
        copied_path = Path(work_dir) / cube_path.name
        shutil.copy2(cube_path, copied_path)
        _delete_shape_model_from_cube_label(copied_path)
        cube = ip.Cube()
        cube.open(str(copied_path), "r")
        try:
            return _camera_geometry_from_open_cube(cube)
        finally:
            if cube.is_open():
                cube.close()


def _compute_texture_sparseness_from_open_cube(
    cube: ip.Cube,
    *,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    tile_size: int,
    tile_step: int,
) -> ImageSparsenessSummary:
    resolved_invalid_values = _resolved_invalid_values_for_cube(cube, invalid_values)
    window_value_cache: dict[tuple[int, int, int, int], np.ndarray] = {}

    def read_window(start_x: int, start_y: int, width: int, height: int) -> np.ndarray:
        key = (int(start_x), int(start_y), int(width), int(height))
        values = _read_cube_window(
            cube,
            TileWindow(start_x=key[0], start_y=key[1], width=key[2], height=key[3]),
            band=band,
        )
        window_value_cache[key] = values
        return values

    def read_invalid_mask(start_x: int, start_y: int, width: int, height: int) -> np.ndarray:
        key = (int(start_x), int(start_y), int(width), int(height))
        values = window_value_cache.get(key)
        if values is None:
            values = read_window(*key)
        invalid_mask, _ = summarize_valid_pixels(
            values,
            invalid_values=resolved_invalid_values,
            special_pixel_abs_threshold=special_pixel_abs_threshold,
        )
        return invalid_mask

    return compute_image_texture_sparseness_from_reader(
        image_width=cube.sample_count(),
        image_height=cube.line_count(),
        read_window=read_window,
        invalid_mask_reader=read_invalid_mask,
        tile_size=tile_size,
        tile_step=tile_step,
        keep_tile_metrics=False,
    )


def compute_image_metric(
    cube_path_string: str,
    *,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    tile_size: int,
    tile_step: int,
    temp_dir_string: str | None,
    use_shape_model_fallback: bool,
) -> ImageMetric:
    try:
        import cv2

        cv2.setNumThreads(1)
    except Exception:
        pass

    cube_path = Path(cube_path_string)
    product_id, observation_id, eye = _parse_product(cube_path)
    temp_dir = None if temp_dir_string in (None, "") else Path(str(temp_dir_string))
    texture_summary: ImageSparsenessSummary | None = None
    sample_count = 0
    line_count = 0
    texture_error: str | None = None
    geometry_error: str | None = None

    cube = ip.Cube()
    try:
        cube.open(str(cube_path), "r")
        sample_count = int(cube.sample_count())
        line_count = int(cube.line_count())
        texture_summary = _compute_texture_sparseness_from_open_cube(
            cube,
            band=band,
            invalid_values=invalid_values,
            special_pixel_abs_threshold=special_pixel_abs_threshold,
            tile_size=tile_size,
            tile_step=tile_step,
        )
    except Exception as exc:  # noqa: BLE001 - keep per-image diagnostics in the CSV/JSON output
        texture_error = str(exc)
    finally:
        if cube.is_open():
            cube.close()

    geometry: dict[str, float | None] = {}
    try:
        geometry = _camera_geometry_with_temporary_shape_fallback(cube_path, temp_dir=temp_dir)
    except Exception as first_error:  # noqa: BLE001 - fallback handles missing local DEM ShapeModel labels
        if not use_shape_model_fallback:
            geometry_error = str(first_error)
        else:
            try:
                geometry = _camera_geometry_from_shape_stripped_copy(cube_path, temp_dir=temp_dir)
            except Exception as fallback_error:  # noqa: BLE001
                geometry_error = f"camera geometry failed: {first_error}; shape-stripped fallback failed: {fallback_error}"

    status = "ok" if texture_summary is not None and geometry and geometry_error is None else "partial"
    if texture_summary is None and not geometry:
        status = "failed"
    return ImageMetric(
        cube_path=str(cube_path),
        product_id=product_id,
        observation_id=observation_id,
        eye=eye,
        sample_count=sample_count,
        line_count=line_count,
        center_sample=geometry.get("center_sample"),
        center_line=geometry.get("center_line"),
        center_latitude=geometry.get("center_latitude"),
        center_longitude=geometry.get("center_longitude"),
        latitude_min=geometry.get("latitude_min"),
        latitude_max=geometry.get("latitude_max"),
        longitude_min=geometry.get("longitude_min"),
        longitude_max=geometry.get("longitude_max"),
        solar_elevation_degrees=geometry.get("solar_elevation_degrees"),
        solar_azimuth_degrees=geometry.get("solar_azimuth_degrees"),
        incidence_degrees=geometry.get("incidence_degrees"),
        emission_degrees=geometry.get("emission_degrees"),
        phase_degrees=geometry.get("phase_degrees"),
        image_texture_sparseness=None if texture_summary is None else texture_summary.image_texture_sparseness,
        texture_tile_valid_count=0 if texture_summary is None else texture_summary.tile_valid_count,
        texture_tile_total_count=0 if texture_summary is None else texture_summary.tile_total_count,
        status=status,
        error="; ".join(part for part in (texture_error, geometry_error) if part) or None,
    )


def load_skip_list(skip_list_path: Path | None) -> set[str]:
    if skip_list_path is None or not skip_list_path.exists():
        return set()
    skipped: set[str] = set()
    for line in skip_list_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        skipped.add(str(Path(stripped).name))
        skipped.add(stripped)
    return skipped


def discover_cubes(input_dir: Path, *, cube_pattern: str, skip_list_path: Path | None) -> list[Path]:
    skip_entries = load_skip_list(skip_list_path)
    cubes = []
    for cube_path in sorted(input_dir.glob(cube_pattern)):
        if cube_path.name in skip_entries or str(cube_path) in skip_entries:
            continue
        cubes.append(cube_path)
    return cubes


def load_image_cache(cache_path: Path) -> list[ImageMetric] | None:
    if not cache_path.exists():
        return None
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    records = payload.get("images", payload if isinstance(payload, list) else [])
    return [ImageMetric(**record) for record in records]


def write_image_cache(cache_path: Path, images: list[ImageMetric], *, config: dict[str, Any]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "config": config,
                "images": [asdict(image) for image in images],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def compute_image_metrics(
    cube_paths: list[Path],
    *,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    tile_size: int,
    tile_step: int,
    temp_dir: Path | None,
    use_shape_model_fallback: bool,
    num_workers: int,
) -> list[ImageMetric]:
    worker_count = max(1, int(num_workers))
    kwargs = {
        "band": int(band),
        "invalid_values": tuple(float(value) for value in invalid_values),
        "special_pixel_abs_threshold": float(special_pixel_abs_threshold),
        "tile_size": int(tile_size),
        "tile_step": int(tile_step),
        "temp_dir_string": None if temp_dir is None else str(temp_dir),
        "use_shape_model_fallback": bool(use_shape_model_fallback),
    }
    if worker_count == 1:
        return [compute_image_metric(str(cube_path), **kwargs) for cube_path in cube_paths]

    results: list[ImageMetric] = []
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        futures = {executor.submit(compute_image_metric, str(cube_path), **kwargs): cube_path for cube_path in cube_paths}
        for index, future in enumerate(as_completed(futures), start=1):
            cube_path = futures[future]
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001
                product_id, observation_id, eye = _parse_product(cube_path)
                result = ImageMetric(
                    cube_path=str(cube_path),
                    product_id=product_id,
                    observation_id=observation_id,
                    eye=eye,
                    sample_count=0,
                    line_count=0,
                    center_sample=None,
                    center_line=None,
                    center_latitude=None,
                    center_longitude=None,
                    latitude_min=None,
                    latitude_max=None,
                    longitude_min=None,
                    longitude_max=None,
                    solar_elevation_degrees=None,
                    solar_azimuth_degrees=None,
                    incidence_degrees=None,
                    emission_degrees=None,
                    phase_degrees=None,
                    image_texture_sparseness=None,
                    texture_tile_valid_count=0,
                    texture_tile_total_count=0,
                    status="failed",
                    error=str(exc),
                )
            results.append(result)
            if index == 1 or index % 25 == 0 or index == len(cube_paths):
                print(f"[image-metrics] {index}/{len(cube_paths)} {Path(result.cube_path).name}: {result.status}", file=sys.stderr)
    return sorted(results, key=lambda item: item.cube_path)


def metric_in_band(metric: ImageMetric, band: LatitudeBand, *, require_center: bool) -> bool:
    if require_center:
        return band.contains(metric.center_latitude)
    if band.contains(metric.center_latitude):
        return True
    if metric.latitude_min is None or metric.latitude_max is None:
        return False
    return max(metric.latitude_min, band.minimum_latitude) <= min(metric.latitude_max, band.maximum_latitude)


def pair_spatially_close(
    left: ImageMetric,
    right: ImageMetric,
    *,
    max_center_latitude_gap_degrees: float,
    max_center_longitude_gap_degrees: float,
) -> tuple[bool, float | None, float | None]:
    latitude_gap = _linear_gap(left.center_latitude, right.center_latitude)
    longitude_gap = _angular_gap_degrees(left.center_longitude, right.center_longitude)
    if latitude_gap is None or longitude_gap is None:
        return False, latitude_gap, longitude_gap
    return (
        latitude_gap <= max_center_latitude_gap_degrees
        and longitude_gap <= max_center_longitude_gap_degrees,
        latitude_gap,
        longitude_gap,
    )


def build_pair_metric(left: ImageMetric, right: ImageMetric, *, latitude_band: str) -> PairMetric | None:
    left_texture = _finite_float(left.image_texture_sparseness)
    right_texture = _finite_float(right.image_texture_sparseness)
    if left_texture is None or right_texture is None:
        return None
    if left_texture >= right_texture:
        pair_texture = left_texture
        weaker_side = "left"
    else:
        pair_texture = right_texture
        weaker_side = "right"

    lighting_score = None
    elevation_diff = None
    azimuth_diff = None
    if left.solar_elevation_degrees is not None or left.solar_azimuth_degrees is not None:
        if right.solar_elevation_degrees is not None or right.solar_azimuth_degrees is not None:
            lighting = compute_lighting_difference(
                SolarGeometry(
                    solar_elevation_degrees=left.solar_elevation_degrees,
                    solar_azimuth_degrees=left.solar_azimuth_degrees,
                    source_group_name="CameraSampleCenter",
                    elevation_keyword="90-IncidenceAngle",
                    azimuth_keyword="SunAzimuth",
                ),
                SolarGeometry(
                    solar_elevation_degrees=right.solar_elevation_degrees,
                    solar_azimuth_degrees=right.solar_azimuth_degrees,
                    source_group_name="CameraSampleCenter",
                    elevation_keyword="90-IncidenceAngle",
                    azimuth_keyword="SunAzimuth",
                ),
            )
            lighting_score = lighting.lighting_difference_score
            elevation_diff = lighting.elevation_difference_degrees
            azimuth_diff = lighting.azimuth_difference_degrees

    return PairMetric(
        latitude_band=latitude_band,
        left_cube_path=left.cube_path,
        right_cube_path=right.cube_path,
        left_product_id=left.product_id,
        right_product_id=right.product_id,
        left_observation_id=left.observation_id,
        right_observation_id=right.observation_id,
        left_eye=left.eye,
        right_eye=right.eye,
        center_latitude_gap_degrees=_linear_gap(left.center_latitude, right.center_latitude),
        center_longitude_gap_degrees=_angular_gap_degrees(left.center_longitude, right.center_longitude),
        pair_texture_sparseness=pair_texture,
        weaker_texture_side=weaker_side,
        lighting_difference_score=lighting_score,
        solar_elevation_difference_degrees=elevation_diff,
        solar_azimuth_difference_degrees=azimuth_diff,
        left_center_latitude=left.center_latitude,
        right_center_latitude=right.center_latitude,
        left_center_longitude=left.center_longitude,
        right_center_longitude=right.center_longitude,
        left_texture_sparseness=left_texture,
        right_texture_sparseness=right_texture,
        left_solar_elevation_degrees=left.solar_elevation_degrees,
        right_solar_elevation_degrees=right.solar_elevation_degrees,
        left_solar_azimuth_degrees=left.solar_azimuth_degrees,
        right_solar_azimuth_degrees=right.solar_azimuth_degrees,
    )


def build_candidate_pairs(
    images: list[ImageMetric],
    *,
    bands: tuple[LatitudeBand, ...],
    pair_mode: str,
    require_center_in_band: bool,
    max_center_latitude_gap_degrees: float,
    max_center_longitude_gap_degrees: float,
) -> list[PairMetric]:
    usable = [
        image for image in images
        if image.status in {"ok", "partial"}
        and image.center_latitude is not None
        and image.center_longitude is not None
        and image.image_texture_sparseness is not None
    ]
    pairs: list[PairMetric] = []
    for band in bands:
        in_band = [image for image in usable if metric_in_band(image, band, require_center=require_center_in_band)]
        for left_index, left in enumerate(in_band):
            for right in in_band[left_index + 1 :]:
                if pair_mode == "same-observation":
                    if left.observation_id != right.observation_id:
                        continue
                    if {left.eye, right.eye} != {"LE", "RE"}:
                        continue
                else:
                    close, _, _ = pair_spatially_close(
                        left,
                        right,
                        max_center_latitude_gap_degrees=max_center_latitude_gap_degrees,
                        max_center_longitude_gap_degrees=max_center_longitude_gap_degrees,
                    )
                    if not close:
                        continue
                pair = build_pair_metric(left, right, latitude_band=band.name)
                if pair is not None and pair.lighting_difference_score is not None:
                    pairs.append(pair)
    return pairs


def _class_score(pair: PairMetric, class_name: str) -> float:
    texture = _finite_float(pair.pair_texture_sparseness)
    lighting = _finite_float(pair.lighting_difference_score)
    if texture is None or lighting is None:
        return -math.inf
    if class_name == "sparse-consistent":
        return texture + (1.0 - lighting)
    if class_name == "sparse-inconsistent":
        return texture + lighting
    if class_name == "rich-consistent":
        return (1.0 - texture) + (1.0 - lighting)
    if class_name == "rich-inconsistent":
        return (1.0 - texture) + lighting
    raise ValueError(f"Unsupported class name: {class_name}")


def _strict_class_match(
    pair: PairMetric,
    class_name: str,
    *,
    rich_sparseness_max: float,
    sparse_sparseness_min: float,
    consistent_lighting_max: float,
    inconsistent_lighting_min: float,
) -> bool:
    texture = _finite_float(pair.pair_texture_sparseness)
    lighting = _finite_float(pair.lighting_difference_score)
    if texture is None or lighting is None:
        return False
    wants_sparse = class_name.startswith("sparse-")
    wants_consistent = class_name.endswith("-consistent")
    texture_ok = texture >= sparse_sparseness_min if wants_sparse else texture <= rich_sparseness_max
    lighting_ok = lighting <= consistent_lighting_max if wants_consistent else lighting >= inconsistent_lighting_min
    return texture_ok and lighting_ok


def select_pairs(
    pairs: list[PairMetric],
    *,
    bands: tuple[LatitudeBand, ...],
    pairs_per_class: int,
    rich_sparseness_max: float,
    sparse_sparseness_min: float,
    consistent_lighting_max: float,
    inconsistent_lighting_min: float,
) -> list[dict[str, Any]]:
    classes = ("sparse-consistent", "sparse-inconsistent", "rich-consistent", "rich-inconsistent")
    selected: list[dict[str, Any]] = []
    used_pair_keys_by_band: dict[str, set[tuple[str, str]]] = {band.name: set() for band in bands}
    for band in bands:
        band_pairs = [pair for pair in pairs if pair.latitude_band == band.name]
        for class_name in classes:
            strict = [
                pair for pair in band_pairs
                if _strict_class_match(
                    pair,
                    class_name,
                    rich_sparseness_max=rich_sparseness_max,
                    sparse_sparseness_min=sparse_sparseness_min,
                    consistent_lighting_max=consistent_lighting_max,
                    inconsistent_lighting_min=inconsistent_lighting_min,
                )
            ]
            ranked = sorted(strict, key=lambda pair: _class_score(pair, class_name), reverse=True)
            reason = "strict-threshold"
            if len(ranked) < pairs_per_class:
                fallback = sorted(band_pairs, key=lambda pair: _class_score(pair, class_name), reverse=True)
                existing_keys = {
                    tuple(sorted((pair.left_cube_path, pair.right_cube_path)))
                    for pair in ranked
                }
                ranked.extend(pair for pair in fallback if tuple(sorted((pair.left_cube_path, pair.right_cube_path))) not in existing_keys)
                reason = "strict-threshold-plus-ranked-fallback"

            count = 0
            for pair in ranked:
                key = tuple(sorted((pair.left_cube_path, pair.right_cube_path)))
                if key in used_pair_keys_by_band[band.name]:
                    continue
                row = asdict(pair)
                row["selection_class"] = class_name
                row["selection_rank"] = count + 1
                row["selection_score"] = _class_score(pair, class_name)
                row["selection_reason"] = reason
                selected.append(row)
                used_pair_keys_by_band[band.name].add(key)
                count += 1
                if count >= pairs_per_class:
                    break
    return selected


def parse_latitude_bands(values: Iterable[str]) -> tuple[LatitudeBand, ...]:
    bands: list[LatitudeBand] = []
    for value in values:
        parts = [part.strip() for part in str(value).split(":")]
        if len(parts) != 3:
            raise argparse.ArgumentTypeError("latitude bands must be NAME:MIN:MAX")
        name, minimum, maximum = parts
        bands.append(LatitudeBand(name=name, minimum_latitude=float(minimum), maximum_latitude=float(maximum)))
    return tuple(bands)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Find reusable LRO NAC CUBE stereo-pair candidates by texture sparseness and lighting difference.",
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--cube-pattern", default=DEFAULT_CUBE_PATTERN)
    parser.add_argument("--skip-list", type=Path, default=None)
    parser.add_argument("--latitude-band", action="append", default=[])
    parser.add_argument("--pairs-per-class", type=int, default=2)
    parser.add_argument("--pair-mode", choices=("spatial", "same-observation"), default="spatial")
    parser.add_argument("--max-center-latitude-gap-degrees", type=float, default=DEFAULT_MAX_CENTER_LATITUDE_GAP_DEGREES)
    parser.add_argument("--max-center-longitude-gap-degrees", type=float, default=DEFAULT_MAX_CENTER_LONGITUDE_GAP_DEGREES)
    parser.add_argument("--allow-band-range-intersection", action="store_true")
    parser.add_argument("--rich-sparseness-max", type=float, default=0.35)
    parser.add_argument("--sparse-sparseness-min", type=float, default=0.65)
    parser.add_argument("--consistent-lighting-max", type=float, default=DEFAULT_CONSISTENT_LIGHTING_MAX)
    parser.add_argument("--inconsistent-lighting-min", type=float, default=DEFAULT_INCONSISTENT_LIGHTING_MIN)
    parser.add_argument("--band", type=int, default=1)
    parser.add_argument("--tile-size", type=int, default=256)
    parser.add_argument("--tile-step", type=int, default=128)
    parser.add_argument("--invalid-value", type=float, action="append", default=[])
    parser.add_argument("--special-pixel-abs-threshold", type=float, default=DEFAULT_INVALID_SPECIAL_PIXEL_ABS_THRESHOLD)
    parser.add_argument("--num-workers", type=int, default=max(1, min(6, os.cpu_count() or 1)))
    parser.add_argument("--temp-dir", type=Path, default=None)
    parser.add_argument("--no-shape-model-fallback", action="store_true")
    parser.add_argument("--image-cache-json", type=Path, default=None)
    parser.add_argument("--force-recompute", action="store_true")
    parser.add_argument("--max-images", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    input_dir = args.input_dir.expanduser().resolve()
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir is not None
        else input_dir / DEFAULT_OUTPUT_DIR_NAME
    )
    skip_list = args.skip_list
    if skip_list is None:
        default_skip = input_dir / "spiceinit_failed_skip_list.txt"
        skip_list = default_skip if default_skip.exists() else None
    bands = parse_latitude_bands(args.latitude_band) if args.latitude_band else tuple(
        LatitudeBand(name, minimum, maximum) for name, minimum, maximum in DEFAULT_LATITUDE_BANDS
    )
    image_cache_json = (
        args.image_cache_json.expanduser().resolve()
        if args.image_cache_json is not None
        else output_dir / "image_metrics_cache.json"
    )

    cube_paths = discover_cubes(input_dir, cube_pattern=args.cube_pattern, skip_list_path=skip_list)
    if args.max_images is not None:
        cube_paths = cube_paths[: max(0, int(args.max_images))]
    print(f"[discover] {len(cube_paths)} cube(s) selected from {input_dir}", file=sys.stderr)

    images = None if args.force_recompute else load_image_cache(image_cache_json)
    if images is None:
        images = compute_image_metrics(
            cube_paths,
            band=args.band,
            invalid_values=tuple(args.invalid_value),
            special_pixel_abs_threshold=args.special_pixel_abs_threshold,
            tile_size=args.tile_size,
            tile_step=args.tile_step,
            temp_dir=args.temp_dir,
            use_shape_model_fallback=not args.no_shape_model_fallback,
            num_workers=args.num_workers,
        )
        write_image_cache(
            image_cache_json,
            images,
            config={
                "input_dir": str(input_dir),
                "cube_pattern": args.cube_pattern,
                "skip_list": None if skip_list is None else str(skip_list),
                "band": args.band,
                "tile_size": args.tile_size,
                "tile_step": args.tile_step,
            },
        )
    else:
        print(f"[cache] loaded {len(images)} image metric(s) from {image_cache_json}", file=sys.stderr)

    pairs = build_candidate_pairs(
        images,
        bands=bands,
        pair_mode=args.pair_mode,
        require_center_in_band=not args.allow_band_range_intersection,
        max_center_latitude_gap_degrees=args.max_center_latitude_gap_degrees,
        max_center_longitude_gap_degrees=args.max_center_longitude_gap_degrees,
    )
    selected = select_pairs(
        pairs,
        bands=bands,
        pairs_per_class=args.pairs_per_class,
        rich_sparseness_max=args.rich_sparseness_max,
        sparse_sparseness_min=args.sparse_sparseness_min,
        consistent_lighting_max=args.consistent_lighting_max,
        inconsistent_lighting_min=args.inconsistent_lighting_min,
    )

    image_rows = [asdict(image) for image in images]
    pair_rows = [asdict(pair) for pair in pairs]
    write_csv(output_dir / "image_metrics.csv", image_rows)
    write_csv(output_dir / "candidate_pairs.csv", pair_rows)
    write_csv(output_dir / "selected_pairs.csv", selected)
    summary = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "cube_count": len(cube_paths),
        "image_metric_count": len(images),
        "candidate_pair_count": len(pairs),
        "selected_pair_count": len(selected),
        "latitude_bands": [asdict(band) for band in bands],
        "pair_mode": args.pair_mode,
        "thresholds": {
            "rich_sparseness_max": args.rich_sparseness_max,
            "sparse_sparseness_min": args.sparse_sparseness_min,
            "consistent_lighting_max": args.consistent_lighting_max,
            "inconsistent_lighting_min": args.inconsistent_lighting_min,
            "max_center_latitude_gap_degrees": args.max_center_latitude_gap_degrees,
            "max_center_longitude_gap_degrees": args.max_center_longitude_gap_degrees,
        },
        "selected_pairs": selected,
    }
    (output_dir / "selected_pairs_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[done] image metrics: {output_dir / 'image_metrics.csv'}", file=sys.stderr)
    print(f"[done] candidate pairs: {output_dir / 'candidate_pairs.csv'}", file=sys.stderr)
    print(f"[done] selected pairs: {output_dir / 'selected_pairs.csv'}", file=sys.stderr)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())