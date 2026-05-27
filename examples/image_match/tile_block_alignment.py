"""ISIS storage-tile block alignment helpers for DOM matching."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .tiling import TileWindow

SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES = ("off", "auto", "isis-storage")
DEFAULT_TILE_BLOCK_ALIGNMENT_MODE = "off"


@dataclass(frozen=True, slots=True)
class StorageTileShape:
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class TileBlockAlignmentResult:
    mode: str
    aligned: bool
    requested_block_width: int
    requested_block_height: int
    requested_overlap_x: int
    requested_overlap_y: int
    effective_block_width: int
    effective_block_height: int
    effective_overlap_x: int
    effective_overlap_y: int
    left_storage_tile_width: int | None
    left_storage_tile_height: int | None
    right_storage_tile_width: int | None
    right_storage_tile_height: int | None
    left_offset_remainder_x: int | None
    left_offset_remainder_y: int | None
    right_offset_remainder_x: int | None
    right_offset_remainder_y: int | None
    fallback_reason_code: str | None
    reason: str
    local_windows: tuple[TileWindow, ...] | None = None

    def to_metadata(self) -> dict[str, object]:
        payload = asdict(self)
        payload["local_windows"] = None if self.local_windows is None else [asdict(window) for window in self.local_windows]
        return payload


def normalize_tile_block_alignment_mode(mode: str) -> str:
    normalized = str(mode).strip().lower().replace("_", "-")
    if normalized not in SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES:
        raise ValueError(
            "tile_block_alignment_mode must be one of "
            f"{SUPPORTED_TILE_BLOCK_ALIGNMENT_MODES}; got {mode!r}."
        )
    return normalized


def storage_tile_shape_from_cube(cube: Any) -> StorageTileShape | None:
    try:
        core = cube.group("Core")
        width = int(core.find_keyword("TileSamples")[0])
        height = int(core.find_keyword("TileLines")[0])
    except Exception:
        return None
    if width <= 0 or height <= 0:
        return None
    return StorageTileShape(width=width, height=height)


def _ceil_to_multiple(value: int, multiple: int) -> int:
    if value <= 0:
        raise ValueError("value must be positive.")
    if multiple <= 0:
        raise ValueError("multiple must be positive.")
    return ((value + multiple - 1) // multiple) * multiple


def _round_overlap_to_multiple(value: int, multiple: int, block_size: int) -> int:
    if value < 0:
        raise ValueError("overlap must be non-negative.")
    rounded = _ceil_to_multiple(max(1, value), multiple) if value > 0 else 0
    if rounded >= block_size:
        rounded = max(0, block_size - multiple)
    return rounded


def _compatible_axis_remainders(
    *,
    left_offset: int,
    right_offset: int,
    left_tile_size: int,
    right_tile_size: int,
) -> bool:
    return _first_aligned_start(
        left_offset=left_offset,
        right_offset=right_offset,
        left_tile_size=left_tile_size,
        right_tile_size=right_tile_size,
    ) is not None


def _first_aligned_start(
    *,
    left_offset: int,
    right_offset: int,
    left_tile_size: int,
    right_tile_size: int,
) -> int | None:
    limit = left_tile_size * right_tile_size
    for local_start in range(0, limit, min(left_tile_size, right_tile_size)):
        if (left_offset + local_start) % left_tile_size == 0 and (right_offset + local_start) % right_tile_size == 0:
            return local_start
    return None


def _shared_tile_size(left_size: int, right_size: int) -> int | None:
    larger = max(left_size, right_size)
    smaller = min(left_size, right_size)
    if larger % smaller != 0:
        return None
    return larger


def generate_aligned_axis_starts(
    *,
    size: int,
    block_size: int,
    overlap_size: int,
    left_offset: int,
    right_offset: int,
    left_tile_size: int,
    right_tile_size: int,
) -> list[int]:
    if size <= 0:
        raise ValueError("size must be positive.")
    if block_size <= 0:
        raise ValueError("block_size must be positive.")
    if overlap_size < 0 or overlap_size >= block_size:
        raise ValueError("overlap_size must be within [0, block_size).")
    if size <= block_size:
        return [0]

    first = _first_aligned_start(
        left_offset=left_offset,
        right_offset=right_offset,
        left_tile_size=left_tile_size,
        right_tile_size=right_tile_size,
    )
    if first is None:
        raise ValueError("Offsets cannot align both DOM windows to storage tile boundaries.")

    step = block_size - overlap_size
    last_start = size - block_size
    starts = [0]
    current = first if first > 0 and first < last_start else step
    while current < last_start:
        if current > starts[-1]:
            starts.append(current)
        current += step
    if starts[-1] != last_start:
        starts.append(last_start)
    return starts


def resolve_tile_aligned_block_config(
    *,
    mode: str,
    left_shape: StorageTileShape | None,
    right_shape: StorageTileShape | None,
    left_offset_x: int,
    left_offset_y: int,
    right_offset_x: int,
    right_offset_y: int,
    requested_block_width: int,
    requested_block_height: int,
    requested_overlap_x: int,
    requested_overlap_y: int,
    common_width: int,
    common_height: int,
) -> TileBlockAlignmentResult:
    resolved_mode = normalize_tile_block_alignment_mode(mode)
    base_kwargs = {
        "mode": resolved_mode,
        "requested_block_width": int(requested_block_width),
        "requested_block_height": int(requested_block_height),
        "requested_overlap_x": int(requested_overlap_x),
        "requested_overlap_y": int(requested_overlap_y),
        "effective_block_width": int(requested_block_width),
        "effective_block_height": int(requested_block_height),
        "effective_overlap_x": int(requested_overlap_x),
        "effective_overlap_y": int(requested_overlap_y),
        "left_storage_tile_width": None if left_shape is None else left_shape.width,
        "left_storage_tile_height": None if left_shape is None else left_shape.height,
        "right_storage_tile_width": None if right_shape is None else right_shape.width,
        "right_storage_tile_height": None if right_shape is None else right_shape.height,
        "left_offset_remainder_x": None if left_shape is None else int(left_offset_x) % left_shape.width,
        "left_offset_remainder_y": None if left_shape is None else int(left_offset_y) % left_shape.height,
        "right_offset_remainder_x": None if right_shape is None else int(right_offset_x) % right_shape.width,
        "right_offset_remainder_y": None if right_shape is None else int(right_offset_y) % right_shape.height,
    }
    if resolved_mode == "off":
        return TileBlockAlignmentResult(aligned=False, fallback_reason_code=None, reason="Tile block alignment is disabled.", local_windows=None, **base_kwargs)
    if left_shape is None or right_shape is None:
        if resolved_mode == "isis-storage":
            raise ValueError("tile_block_alignment_mode='isis-storage' requires valid ISIS storage tile metadata.")
        return TileBlockAlignmentResult(aligned=False, fallback_reason_code="missing_storage_tile_metadata", reason="Storage tile metadata is unavailable; using requested block geometry.", local_windows=None, **base_kwargs)

    shared_w = _shared_tile_size(left_shape.width, right_shape.width)
    shared_h = _shared_tile_size(left_shape.height, right_shape.height)
    compatible_x = _compatible_axis_remainders(left_offset=left_offset_x, right_offset=right_offset_x, left_tile_size=left_shape.width, right_tile_size=right_shape.width)
    compatible_y = _compatible_axis_remainders(left_offset=left_offset_y, right_offset=right_offset_y, left_tile_size=left_shape.height, right_tile_size=right_shape.height)
    if shared_w is None or shared_h is None or not compatible_x or not compatible_y:
        reason = "Requested crop offsets cannot align both DOM windows to ISIS storage tile boundaries."
        if resolved_mode == "isis-storage":
            raise ValueError(reason)
        code = "incompatible_storage_tile_sizes" if shared_w is None or shared_h is None else "incompatible_offset_remainders"
        return TileBlockAlignmentResult(aligned=False, fallback_reason_code=code, reason=reason, local_windows=None, **base_kwargs)

    effective_block_width = _ceil_to_multiple(requested_block_width, shared_w)
    effective_block_height = _ceil_to_multiple(requested_block_height, shared_h)
    effective_overlap_x = _round_overlap_to_multiple(requested_overlap_x, shared_w, effective_block_width)
    effective_overlap_y = _round_overlap_to_multiple(requested_overlap_y, shared_h, effective_block_height)
    x_starts = generate_aligned_axis_starts(size=common_width, block_size=effective_block_width, overlap_size=effective_overlap_x, left_offset=left_offset_x, right_offset=right_offset_x, left_tile_size=left_shape.width, right_tile_size=right_shape.width)
    y_starts = generate_aligned_axis_starts(size=common_height, block_size=effective_block_height, overlap_size=effective_overlap_y, left_offset=left_offset_y, right_offset=right_offset_y, left_tile_size=left_shape.height, right_tile_size=right_shape.height)
    local_windows = tuple(
        TileWindow(start_x=x, start_y=y, width=min(effective_block_width, common_width - x), height=min(effective_block_height, common_height - y))
        for y in y_starts
        for x in x_starts
    )
    return TileBlockAlignmentResult(
        aligned=True,
        fallback_reason_code=None,
        reason="Using ISIS storage-tile-aligned matching blocks.",
        local_windows=local_windows,
        **{
            **base_kwargs,
            "effective_block_width": effective_block_width,
            "effective_block_height": effective_block_height,
            "effective_overlap_x": effective_overlap_x,
            "effective_overlap_y": effective_overlap_y,
        },
    )
