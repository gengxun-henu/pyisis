"""Coarse DOM tile-validity cache helpers for conservative prefiltering.

These helpers keep the validity decision independent from the full tile-matching
integration so tests can exercise cache keys and window filtering without ISIS files.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from math import ceil
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .preprocess import expand_invalid_mask_for_radius, summarize_valid_pixels
from .tiling import TileWindow

CACHE_FORMAT_VERSION = 1
DEFAULT_TILE_VALIDITY_CELL_WIDTH = 1024
DEFAULT_TILE_VALIDITY_CELL_HEIGHT = 1024


@dataclass(frozen=True, slots=True)
class TileValidityIndex:
    dom_path: str
    image_width: int
    image_height: int
    cell_width: int
    cell_height: int
    grid_width: int
    grid_height: int
    valid_counts: np.ndarray
    total_counts: np.ndarray
    uncertain: np.ndarray
    manifest: dict[str, Any]


@dataclass(frozen=True, slots=True)
class TileValidityUpperBound:
    valid_pixel_upper_bound: int
    window_pixel_count: int
    valid_ratio_upper_bound: float
    has_uncertain_cells: bool


@dataclass(frozen=True, slots=True)
class TileValidityPrefilterResult:
    kept_windows: list[Any]
    skipped_windows: list[Any]
    preindexed_skipped_tile_count: int
    skip_reasons: dict[str, int]


@dataclass(frozen=True, slots=True)
class DomPathMetadata:
    path: str
    size_bytes: int
    mtime_ns: int

    @classmethod
    def from_path(cls, path: str | Path) -> "DomPathMetadata":
        resolved_path = Path(path).expanduser()
        stat_result = resolved_path.stat()
        return cls(
            path=str(resolved_path),
            size_bytes=int(stat_result.st_size),
            mtime_ns=int(stat_result.st_mtime_ns),
        )


@dataclass(frozen=True, slots=True)
class DomValidityCacheKey:
    path: str
    size_bytes: int
    mtime_ns: int
    band: int
    coarse_cell_size: int
    invalid_values: tuple[float, ...]
    special_pixel_abs_threshold: float
    invalid_pixel_radius: int
    min_valid_pixels: int
    valid_pixel_percent_threshold: float


@dataclass(frozen=True, slots=True)
class WindowValidityDecision:
    should_skip: bool
    reason: str
    covered_cell_count: int
    below_threshold_cell_count: int
    uncertain_cell_count: int
    minimum_valid_ratio: float | None


@dataclass(frozen=True, slots=True)
class TileValidityFilterSummary:
    total_window_count: int
    kept_window_count: int
    skipped_window_count: int
    uncertain_window_count: int
    decisions: tuple[WindowValidityDecision, ...]


class DomValidityCache:
    """In-memory per-DOM validity-grid cache keyed by path metadata and parameters."""

    def __init__(self) -> None:
        self._grids: dict[DomValidityCacheKey, DomValidityGrid] = {}

    def get_or_build(self, key: DomValidityCacheKey, builder) -> "DomValidityGrid":
        if key not in self._grids:
            self._grids[key] = builder()
        return self._grids[key]

    def clear(self) -> None:
        self._grids.clear()

    def __len__(self) -> int:
        return len(self._grids)


@dataclass(frozen=True, slots=True)
class DomValidityGrid:
    image_width: int
    image_height: int
    coarse_cell_size: int
    valid_counts: np.ndarray
    total_counts: np.ndarray

    @classmethod
    def from_valid_counts(
        cls,
        *,
        image_width: int,
        image_height: int,
        coarse_cell_size: int,
        valid_counts: Iterable[Iterable[int]],
        total_counts: Iterable[Iterable[int]] | None = None,
    ) -> "DomValidityGrid":
        resolved_width, resolved_height, resolved_cell_size = _validate_grid_dimensions(
            image_width,
            image_height,
            coarse_cell_size,
        )
        valid_array = np.asarray(tuple(tuple(row) for row in valid_counts), dtype=np.int64)
        expected_shape = (
            ceil(resolved_height / resolved_cell_size),
            ceil(resolved_width / resolved_cell_size),
        )
        if valid_array.shape != expected_shape:
            raise ValueError(f"valid_counts shape must be {expected_shape}, got {valid_array.shape}.")

        if total_counts is None:
            total_array = _default_total_counts(resolved_width, resolved_height, resolved_cell_size)
        else:
            total_array = np.asarray(tuple(tuple(row) for row in total_counts), dtype=np.int64)
            if total_array.shape != expected_shape:
                raise ValueError(f"total_counts shape must be {expected_shape}, got {total_array.shape}.")

        if np.any(valid_array < 0):
            raise ValueError("valid_counts cannot contain negative values.")
        if np.any(total_array <= 0):
            raise ValueError("total_counts must be positive for every coarse cell.")
        if np.any(valid_array > total_array):
            raise ValueError("valid_counts cannot exceed total_counts.")

        return cls(
            image_width=resolved_width,
            image_height=resolved_height,
            coarse_cell_size=resolved_cell_size,
            valid_counts=valid_array,
            total_counts=total_array,
        )

    @classmethod
    def from_valid_mask(
        cls,
        valid_mask,
        *,
        coarse_cell_size: int,
    ) -> "DomValidityGrid":
        mask = np.asarray(valid_mask, dtype=bool)
        if mask.ndim != 2:
            raise ValueError("valid_mask must be a 2D array.")
        image_height, image_width = mask.shape
        _validate_grid_dimensions(image_width, image_height, coarse_cell_size)
        rows = ceil(image_height / coarse_cell_size)
        cols = ceil(image_width / coarse_cell_size)
        valid_counts = np.zeros((rows, cols), dtype=np.int64)
        total_counts = np.zeros((rows, cols), dtype=np.int64)
        for row in range(rows):
            for col in range(cols):
                y0, y1, x0, x1 = _cell_bounds(row, col, image_width, image_height, coarse_cell_size)
                cell_mask = mask[y0:y1, x0:x1]
                valid_counts[row, col] = int(cell_mask.sum())
                total_counts[row, col] = int(cell_mask.size)
        return cls.from_valid_counts(
            image_width=image_width,
            image_height=image_height,
            coarse_cell_size=coarse_cell_size,
            valid_counts=valid_counts,
            total_counts=total_counts,
        )

    @property
    def shape(self) -> tuple[int, int]:
        return self.valid_counts.shape

    @property
    def valid_ratios(self) -> np.ndarray:
        return self.valid_counts.astype(np.float64) / self.total_counts.astype(np.float64)

    def decide_window(
        self,
        window: TileWindow,
        *,
        min_valid_pixels: int,
        valid_pixel_percent_threshold: float,
    ) -> WindowValidityDecision:
        resolved_min_valid_pixels = int(min_valid_pixels)
        resolved_threshold = float(valid_pixel_percent_threshold)
        if resolved_min_valid_pixels < 0:
            raise ValueError("min_valid_pixels must be >= 0.")
        if not (0.0 <= resolved_threshold <= 1.0):
            raise ValueError("valid_pixel_percent_threshold must be within [0.0, 1.0].")
        if window.width <= 0 or window.height <= 0:
            raise ValueError("TileWindow dimensions must be positive.")

        if window.start_x < 0 or window.start_y < 0 or window.end_x > self.image_width or window.end_y > self.image_height:
            return WindowValidityDecision(
                should_skip=False,
                reason="uncertain_window_outside_grid",
                covered_cell_count=0,
                below_threshold_cell_count=0,
                uncertain_cell_count=1,
                minimum_valid_ratio=None,
            )

        covered_cell_count = 0
        below_threshold_cell_count = 0
        uncertain_cell_count = 0
        minimum_valid_ratio: float | None = None

        for row, col in self._covered_cell_indices(window):
            y0, y1, x0, x1 = _cell_bounds(row, col, self.image_width, self.image_height, self.coarse_cell_size)
            if x1 - x0 != self.coarse_cell_size or y1 - y0 != self.coarse_cell_size:
                uncertain_cell_count += 1
                continue
            if window.start_x > x0 or window.end_x < x1 or window.start_y > y0 or window.end_y < y1:
                uncertain_cell_count += 1
                continue

            covered_cell_count += 1
            valid_count = int(self.valid_counts[row, col])
            valid_ratio = float(self.valid_ratios[row, col])
            minimum_valid_ratio = valid_ratio if minimum_valid_ratio is None else min(minimum_valid_ratio, valid_ratio)
            if valid_count < resolved_min_valid_pixels or valid_ratio < resolved_threshold:
                below_threshold_cell_count += 1

        if uncertain_cell_count > 0:
            return WindowValidityDecision(
                should_skip=False,
                reason="uncertain_partial_cell_overlap",
                covered_cell_count=covered_cell_count,
                below_threshold_cell_count=below_threshold_cell_count,
                uncertain_cell_count=uncertain_cell_count,
                minimum_valid_ratio=minimum_valid_ratio,
            )
        if covered_cell_count == 0:
            return WindowValidityDecision(
                should_skip=False,
                reason="no_confident_cells_covered",
                covered_cell_count=0,
                below_threshold_cell_count=0,
                uncertain_cell_count=0,
                minimum_valid_ratio=None,
            )
        if below_threshold_cell_count == covered_cell_count:
            return WindowValidityDecision(
                should_skip=True,
                reason="all_confident_cells_below_threshold",
                covered_cell_count=covered_cell_count,
                below_threshold_cell_count=below_threshold_cell_count,
                uncertain_cell_count=0,
                minimum_valid_ratio=minimum_valid_ratio,
            )
        return WindowValidityDecision(
            should_skip=False,
            reason="contains_cell_at_or_above_threshold",
            covered_cell_count=covered_cell_count,
            below_threshold_cell_count=below_threshold_cell_count,
            uncertain_cell_count=0,
            minimum_valid_ratio=minimum_valid_ratio,
        )

    def _covered_cell_indices(self, window: TileWindow) -> tuple[tuple[int, int], ...]:
        start_col = window.start_x // self.coarse_cell_size
        end_col = (window.end_x - 1) // self.coarse_cell_size
        start_row = window.start_y // self.coarse_cell_size
        end_row = (window.end_y - 1) // self.coarse_cell_size
        return tuple((row, col) for row in range(start_row, end_row + 1) for col in range(start_col, end_col + 1))


def build_dom_validity_cache_key(
    dom_path: str | Path,
    *,
    band: int,
    coarse_cell_size: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    invalid_pixel_radius: int,
    min_valid_pixels: int,
    valid_pixel_percent_threshold: float,
    metadata: DomPathMetadata | None = None,
) -> DomValidityCacheKey:
    resolved_metadata = metadata if metadata is not None else DomPathMetadata.from_path(dom_path)
    if int(band) <= 0:
        raise ValueError("band must be positive.")
    if int(coarse_cell_size) <= 0:
        raise ValueError("coarse_cell_size must be positive.")
    if int(invalid_pixel_radius) < 0:
        raise ValueError("invalid_pixel_radius must be >= 0.")
    if int(min_valid_pixels) < 0:
        raise ValueError("min_valid_pixels must be >= 0.")
    threshold = float(valid_pixel_percent_threshold)
    if not (0.0 <= threshold <= 1.0):
        raise ValueError("valid_pixel_percent_threshold must be within [0.0, 1.0].")

    metadata_path = Path(resolved_metadata.path).expanduser()
    return DomValidityCacheKey(
        path=str(metadata_path),
        size_bytes=int(resolved_metadata.size_bytes),
        mtime_ns=int(resolved_metadata.mtime_ns),
        band=int(band),
        coarse_cell_size=int(coarse_cell_size),
        invalid_values=tuple(float(value) for value in invalid_values),
        special_pixel_abs_threshold=float(special_pixel_abs_threshold),
        invalid_pixel_radius=int(invalid_pixel_radius),
        min_valid_pixels=int(min_valid_pixels),
        valid_pixel_percent_threshold=threshold,
    )


def build_dom_validity_grid_from_values(
    values,
    *,
    coarse_cell_size: int,
    invalid_values: tuple[float, ...] = (),
    special_pixel_abs_threshold: float = 1.0e300,
    invalid_pixel_radius: int = 0,
) -> DomValidityGrid:
    invalid_mask, _ = summarize_valid_pixels(
        values,
        invalid_values=invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
    )
    expanded_invalid_mask = expand_invalid_mask_for_radius(
        invalid_mask,
        invalid_pixel_radius=invalid_pixel_radius,
    )
    return DomValidityGrid.from_valid_mask(~expanded_invalid_mask, coarse_cell_size=coarse_cell_size)


def filter_windows_by_validity(
    grid: DomValidityGrid,
    windows: Iterable[TileWindow],
    *,
    min_valid_pixels: int,
    valid_pixel_percent_threshold: float,
) -> tuple[tuple[TileWindow, ...], TileValidityFilterSummary]:
    kept_windows: list[TileWindow] = []
    decisions: list[WindowValidityDecision] = []
    uncertain_window_count = 0

    for window in windows:
        decision = grid.decide_window(
            window,
            min_valid_pixels=min_valid_pixels,
            valid_pixel_percent_threshold=valid_pixel_percent_threshold,
        )
        decisions.append(decision)
        if decision.uncertain_cell_count > 0:
            uncertain_window_count += 1
        if not decision.should_skip:
            kept_windows.append(window)

    skipped_window_count = sum(1 for decision in decisions if decision.should_skip)
    summary = TileValidityFilterSummary(
        total_window_count=len(decisions),
        kept_window_count=len(kept_windows),
        skipped_window_count=skipped_window_count,
        uncertain_window_count=uncertain_window_count,
        decisions=tuple(decisions),
    )
    return tuple(kept_windows), summary


def validate_tile_validity_cell_size(value: int, *, field_name: str) -> int:
    resolved_value = int(value)
    if resolved_value <= 0:
        raise ValueError(f"{field_name} must be positive.")
    return resolved_value


def _covered_cell_range(start: int, length: int, cell_size: int, grid_size: int) -> range:
    if length <= 0:
        return range(0)
    first = max(0, start // cell_size)
    last = min(grid_size - 1, (start + length - 1) // cell_size)
    if first > last:
        return range(0)
    return range(first, last + 1)


def window_valid_upper_bound(index: TileValidityIndex, window: TileWindow) -> TileValidityUpperBound:
    x_cells = _covered_cell_range(window.start_x, window.width, index.cell_width, index.grid_width)
    y_cells = _covered_cell_range(window.start_y, window.height, index.cell_height, index.grid_height)
    valid_upper_bound = 0
    has_uncertain_cells = False
    for cell_y in y_cells:
        for cell_x in x_cells:
            valid_upper_bound += int(index.valid_counts[cell_y, cell_x])
            has_uncertain_cells = has_uncertain_cells or bool(index.uncertain[cell_y, cell_x])
    window_pixel_count = int(window.width * window.height)
    valid_ratio_upper_bound = 0.0 if window_pixel_count <= 0 else float(valid_upper_bound) / float(window_pixel_count)
    return TileValidityUpperBound(
        valid_pixel_upper_bound=valid_upper_bound,
        window_pixel_count=window_pixel_count,
        valid_ratio_upper_bound=valid_ratio_upper_bound,
        has_uncertain_cells=has_uncertain_cells,
    )


def _side_skip_reason(
    upper_bound: TileValidityUpperBound,
    *,
    side_name: str,
    valid_pixel_percent_threshold: float,
) -> str | None:
    if upper_bound.has_uncertain_cells:
        return None
    if valid_pixel_percent_threshold > 0.0 and upper_bound.valid_ratio_upper_bound < valid_pixel_percent_threshold:
        return f"{side_name}_valid_upper_bound_below_threshold"
    return None


def prefilter_paired_windows_by_validity(
    windows: list[Any],
    *,
    left_index: TileValidityIndex,
    right_index: TileValidityIndex,
    valid_pixel_percent_threshold: float,
) -> TileValidityPrefilterResult:
    if valid_pixel_percent_threshold <= 0.0:
        return TileValidityPrefilterResult(
            kept_windows=list(windows),
            skipped_windows=[],
            preindexed_skipped_tile_count=0,
            skip_reasons={},
        )

    kept_windows: list[Any] = []
    skipped_windows: list[Any] = []
    skip_reasons: dict[str, int] = {}
    for paired_window in windows:
        left_upper_bound = window_valid_upper_bound(left_index, paired_window.left_window)
        right_upper_bound = window_valid_upper_bound(right_index, paired_window.right_window)
        reason = _side_skip_reason(
            left_upper_bound,
            side_name="left",
            valid_pixel_percent_threshold=valid_pixel_percent_threshold,
        ) or _side_skip_reason(
            right_upper_bound,
            side_name="right",
            valid_pixel_percent_threshold=valid_pixel_percent_threshold,
        )
        if reason is None:
            kept_windows.append(paired_window)
            continue
        skipped_windows.append(paired_window)
        skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

    return TileValidityPrefilterResult(
        kept_windows=kept_windows,
        skipped_windows=skipped_windows,
        preindexed_skipped_tile_count=len(skipped_windows),
        skip_reasons=skip_reasons,
    )


def default_tile_validity_cache_dir(
    *,
    metadata_output: str | Path | None = None,
    left_output_key: str | Path | None = None,
) -> Path:
    if metadata_output is not None:
        return Path(metadata_output).parent.parent / "tile_validity_cache"
    if left_output_key is not None:
        return Path(left_output_key).parent.parent / "tile_validity_cache"
    return Path.cwd() / "tile_validity_cache"


def _dom_file_fingerprint(dom_path: str | Path) -> dict[str, object]:
    resolved_path = Path(dom_path)
    stat_result = resolved_path.stat()
    return {
        "path": str(resolved_path.resolve()),
        "size": int(stat_result.st_size),
        "mtime_ns": int(stat_result.st_mtime_ns),
    }


def _index_manifest(
    *,
    dom_path: str | Path,
    image_width: int,
    image_height: int,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    invalid_pixel_radius: int,
    cell_width: int,
    cell_height: int,
) -> dict[str, object]:
    return {
        "format_version": CACHE_FORMAT_VERSION,
        "dom": _dom_file_fingerprint(dom_path),
        "image_width": int(image_width),
        "image_height": int(image_height),
        "band": int(band),
        "invalid_values": [float(value) for value in invalid_values],
        "special_pixel_abs_threshold": float(special_pixel_abs_threshold),
        "invalid_pixel_radius": int(invalid_pixel_radius),
        "cell_width": int(cell_width),
        "cell_height": int(cell_height),
        "grid_width": int(ceil(image_width / cell_width)),
        "grid_height": int(ceil(image_height / cell_height)),
    }


def _cache_key_for_manifest(manifest: dict[str, object]) -> str:
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_paths(cache_dir: str | Path, cache_key: str) -> tuple[Path, Path]:
    resolved_cache_dir = Path(cache_dir)
    return resolved_cache_dir / f"{cache_key}.json", resolved_cache_dir / f"{cache_key}.npz"


def _load_index_from_cache(manifest_path: Path, data_path: Path) -> TileValidityIndex:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    with np.load(data_path) as payload:
        valid_counts = np.asarray(payload["valid_counts"], dtype=np.int64)
        total_counts = np.asarray(payload["total_counts"], dtype=np.int64)
        uncertain = np.asarray(payload["uncertain"], dtype=bool)
    return TileValidityIndex(
        dom_path=str(manifest["dom"]["path"]),
        image_width=int(manifest["image_width"]),
        image_height=int(manifest["image_height"]),
        cell_width=int(manifest["cell_width"]),
        cell_height=int(manifest["cell_height"]),
        grid_width=int(manifest["grid_width"]),
        grid_height=int(manifest["grid_height"]),
        valid_counts=valid_counts,
        total_counts=total_counts,
        uncertain=uncertain,
        manifest=manifest,
    )


def _save_index_to_cache(index: TileValidityIndex, manifest_path: Path, data_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(index.manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    np.savez_compressed(
        data_path,
        valid_counts=index.valid_counts,
        total_counts=index.total_counts,
        uncertain=index.uncertain,
    )


def _build_index_from_open_cube(
    *,
    dom_path: str | Path,
    cube,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    invalid_pixel_radius: int,
    cell_width: int,
    cell_height: int,
    manifest: dict[str, object],
) -> TileValidityIndex:
    image_width = int(manifest["image_width"])
    image_height = int(manifest["image_height"])
    grid_width = int(manifest["grid_width"])
    grid_height = int(manifest["grid_height"])
    valid_counts = np.zeros((grid_height, grid_width), dtype=np.int64)
    total_counts = np.zeros((grid_height, grid_width), dtype=np.int64)
    uncertain = np.zeros((grid_height, grid_width), dtype=bool)
    resolved_invalid_values = _resolved_invalid_values_for_cube(__import__("isis_pybind"), cube, invalid_values)

    for cell_y in range(grid_height):
        for cell_x in range(grid_width):
            start_x = cell_x * cell_width
            start_y = cell_y * cell_height
            width = min(cell_width, image_width - start_x)
            height = min(cell_height, image_height - start_y)
            window = TileWindow(start_x=start_x, start_y=start_y, width=width, height=height)
            values = _read_cube_window_values(__import__("isis_pybind"), cube, window, band=band)
            invalid_mask, _ = summarize_valid_pixels(
                values,
                invalid_values=resolved_invalid_values,
                special_pixel_abs_threshold=special_pixel_abs_threshold,
            )
            expanded_mask = expand_invalid_mask_for_radius(
                invalid_mask,
                invalid_pixel_radius=invalid_pixel_radius,
            )
            total = int(width * height)
            valid_counts[cell_y, cell_x] = total - int(expanded_mask.sum())
            total_counts[cell_y, cell_x] = total

    return TileValidityIndex(
        dom_path=str(Path(dom_path)),
        image_width=image_width,
        image_height=image_height,
        cell_width=cell_width,
        cell_height=cell_height,
        grid_width=grid_width,
        grid_height=grid_height,
        valid_counts=valid_counts,
        total_counts=total_counts,
        uncertain=uncertain,
        manifest=manifest,
    )


def ensure_dom_validity_index(
    *,
    cache_dir: str | Path,
    dom_path: str | Path,
    cube,
    band: int,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
    invalid_pixel_radius: int,
    cell_width: int,
    cell_height: int,
) -> tuple[TileValidityIndex, dict[str, object]]:
    resolved_cell_width = validate_tile_validity_cell_size(cell_width, field_name="tile_validity_cell_width")
    resolved_cell_height = validate_tile_validity_cell_size(cell_height, field_name="tile_validity_cell_height")
    manifest = _index_manifest(
        dom_path=dom_path,
        image_width=int(cube.sample_count()),
        image_height=int(cube.line_count()),
        band=band,
        invalid_values=tuple(float(value) for value in invalid_values),
        special_pixel_abs_threshold=special_pixel_abs_threshold,
        invalid_pixel_radius=invalid_pixel_radius,
        cell_width=resolved_cell_width,
        cell_height=resolved_cell_height,
    )
    cache_key = _cache_key_for_manifest(manifest)
    manifest_path, data_path = _cache_paths(cache_dir, cache_key)
    diagnostics = {
        "cache_key": cache_key,
        "manifest_path": str(manifest_path),
        "data_path": str(data_path),
        "cell_width": resolved_cell_width,
        "cell_height": resolved_cell_height,
    }
    if manifest_path.exists() and data_path.exists():
        return _load_index_from_cache(manifest_path, data_path), {**diagnostics, "status": "hit"}

    index = _build_index_from_open_cube(
        dom_path=dom_path,
        cube=cube,
        band=band,
        invalid_values=tuple(float(value) for value in invalid_values),
        special_pixel_abs_threshold=special_pixel_abs_threshold,
        invalid_pixel_radius=invalid_pixel_radius,
        cell_width=resolved_cell_width,
        cell_height=resolved_cell_height,
        manifest=manifest,
    )
    _save_index_to_cache(index, manifest_path, data_path)
    return index, {**diagnostics, "status": "rebuilt"}


def build_dom_validity_grid_from_cube(
    dom_path: str | Path,
    *,
    band: int,
    coarse_cell_size: int,
    invalid_values: tuple[float, ...] = (),
    special_pixel_abs_threshold: float = 1.0e300,
    invalid_pixel_radius: int = 0,
) -> DomValidityGrid:
    """Build a coarse validity grid by opening one DOM cube once and scanning cells.

    Each coarse cell is read sequentially. When ``invalid_pixel_radius`` is nonzero,
    the read window is padded by that radius and cropped back after mask expansion so
    neighboring invalid pixels can conservatively affect the cell edge.
    """
    from .runtime import bootstrap_runtime_environment

    bootstrap_runtime_environment()
    import isis_pybind as ip

    resolved_band = int(band)
    if resolved_band <= 0:
        raise ValueError("band must be positive.")
    resolved_cell_size = int(coarse_cell_size)
    if resolved_cell_size <= 0:
        raise ValueError("coarse_cell_size must be positive.")
    resolved_radius = int(invalid_pixel_radius)
    if resolved_radius < 0:
        raise ValueError("invalid_pixel_radius must be >= 0.")

    cube = ip.Cube()
    cube.open(str(dom_path), "r")
    try:
        image_width = int(cube.sample_count())
        image_height = int(cube.line_count())
        rows = ceil(image_height / resolved_cell_size)
        cols = ceil(image_width / resolved_cell_size)
        valid_counts = np.zeros((rows, cols), dtype=np.int64)
        total_counts = np.zeros((rows, cols), dtype=np.int64)
        resolved_invalid_values = _resolved_invalid_values_for_cube(ip, cube, invalid_values)

        for row in range(rows):
            for col in range(cols):
                y0, y1, x0, x1 = _cell_bounds(row, col, image_width, image_height, resolved_cell_size)
                read_x0 = max(0, x0 - resolved_radius)
                read_y0 = max(0, y0 - resolved_radius)
                read_x1 = min(image_width, x1 + resolved_radius)
                read_y1 = min(image_height, y1 + resolved_radius)
                values = _read_cube_window_values(
                    ip,
                    cube,
                    TileWindow(
                        start_x=read_x0,
                        start_y=read_y0,
                        width=read_x1 - read_x0,
                        height=read_y1 - read_y0,
                    ),
                    band=resolved_band,
                )
                invalid_mask, _ = summarize_valid_pixels(
                    values,
                    invalid_values=resolved_invalid_values,
                    special_pixel_abs_threshold=special_pixel_abs_threshold,
                )
                expanded_invalid_mask = expand_invalid_mask_for_radius(
                    invalid_mask,
                    invalid_pixel_radius=resolved_radius,
                )
                crop_y0 = y0 - read_y0
                crop_y1 = crop_y0 + (y1 - y0)
                crop_x0 = x0 - read_x0
                crop_x1 = crop_x0 + (x1 - x0)
                cell_valid_mask = ~expanded_invalid_mask[crop_y0:crop_y1, crop_x0:crop_x1]
                valid_counts[row, col] = int(cell_valid_mask.sum())
                total_counts[row, col] = int(cell_valid_mask.size)
    finally:
        if cube.is_open():
            cube.close()

    return DomValidityGrid.from_valid_counts(
        image_width=image_width,
        image_height=image_height,
        coarse_cell_size=resolved_cell_size,
        valid_counts=valid_counts,
        total_counts=total_counts,
    )


def _validate_grid_dimensions(image_width: int, image_height: int, coarse_cell_size: int) -> tuple[int, int, int]:
    resolved_width = int(image_width)
    resolved_height = int(image_height)
    resolved_cell_size = int(coarse_cell_size)
    if resolved_width <= 0 or resolved_height <= 0:
        raise ValueError("image dimensions must be positive.")
    if resolved_cell_size <= 0:
        raise ValueError("coarse_cell_size must be positive.")
    return resolved_width, resolved_height, resolved_cell_size


def _default_total_counts(image_width: int, image_height: int, coarse_cell_size: int) -> np.ndarray:
    rows = ceil(image_height / coarse_cell_size)
    cols = ceil(image_width / coarse_cell_size)
    total_counts = np.zeros((rows, cols), dtype=np.int64)
    for row in range(rows):
        for col in range(cols):
            y0, y1, x0, x1 = _cell_bounds(row, col, image_width, image_height, coarse_cell_size)
            total_counts[row, col] = (y1 - y0) * (x1 - x0)
    return total_counts


def _cell_bounds(row: int, col: int, image_width: int, image_height: int, coarse_cell_size: int) -> tuple[int, int, int, int]:
    y0 = row * coarse_cell_size
    x0 = col * coarse_cell_size
    y1 = min(y0 + coarse_cell_size, image_height)
    x1 = min(x0 + coarse_cell_size, image_width)
    return y0, y1, x0, x1


def _read_cube_window_values(ip, cube, window: TileWindow, *, band: int) -> np.ndarray:
    brick = ip.Brick(cube, window.width, window.height, 1)
    brick.set_base_position(window.start_x + 1, window.start_y + 1, band)
    cube.read(brick)
    return np.asarray(brick.double_buffer(), dtype=np.float64).reshape((window.height, window.width))


def _resolved_invalid_values_for_cube(ip, cube, invalid_values: tuple[float, ...]) -> tuple[float, ...]:
    resolved_invalid_values = list(invalid_values)
    zero_invalid_pixel_types = {
        getattr(ip.PixelType, "UnsignedByte", None),
        getattr(ip.PixelType, "SignedByte", None),
    }
    if cube.pixel_type() in zero_invalid_pixel_types and 0.0 not in resolved_invalid_values:
        resolved_invalid_values.append(0.0)
    return tuple(resolved_invalid_values)


__all__ = [
    "DomPathMetadata",
    "DomValidityCacheKey",
    "DomValidityCache",
    "DomValidityGrid",
    "CACHE_FORMAT_VERSION",
    "DEFAULT_TILE_VALIDITY_CELL_HEIGHT",
    "DEFAULT_TILE_VALIDITY_CELL_WIDTH",
    "TileValidityFilterSummary",
    "TileValidityIndex",
    "TileValidityPrefilterResult",
    "TileValidityUpperBound",
    "WindowValidityDecision",
    "build_dom_validity_cache_key",
    "build_dom_validity_grid_from_cube",
    "build_dom_validity_grid_from_values",
    "default_tile_validity_cache_dir",
    "ensure_dom_validity_index",
    "filter_windows_by_validity",
    "prefilter_paired_windows_by_validity",
    "validate_tile_validity_cell_size",
    "window_valid_upper_bound",
]
