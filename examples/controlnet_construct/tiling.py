"""Image tiling helpers for large DOM matching jobs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TileWindow:
    start_x: int
    start_y: int
    width: int
    height: int

    @property
    def end_x(self) -> int:
        return self.start_x + self.width

    @property
    def end_y(self) -> int:
        return self.start_y + self.height


def requires_tiling(image_width: int, image_height: int, *, max_dimension: int = 3000) -> bool:
    return image_width > max_dimension or image_height > max_dimension


def _generate_axis_starts(size: int, block_size: int, overlap_size: int) -> list[int]:
    if size <= 0:
        raise ValueError("Image dimensions must be positive.")
    if block_size <= 0:
        raise ValueError("Block size must be positive.")
    if overlap_size < 0:
        raise ValueError("Overlap size cannot be negative.")
    if overlap_size >= block_size:
        raise ValueError("Overlap size must be smaller than the block size.")

    if size <= block_size:
        return [0]

    starts = [0]
    step = block_size - overlap_size
    last_start = size - block_size

    while starts[-1] < last_start:
        next_start = min(starts[-1] + step, last_start)
        if next_start == starts[-1]:
            break
        starts.append(next_start)

    return starts


def generate_tiles(
    image_width: int,
    image_height: int,
    *,
    block_width: int = 1024,
    block_height: int = 1024,
    overlap_x: int = 128,
    overlap_y: int = 128,
) -> list[TileWindow]:
    """Generate a full-coverage tile layout with overlap."""
    x_starts = _generate_axis_starts(image_width, block_width, overlap_x)
    y_starts = _generate_axis_starts(image_height, block_height, overlap_y)

    tiles: list[TileWindow] = []
    for start_y in y_starts:
        tile_height = min(block_height, image_height - start_y)
        for start_x in x_starts:
            tile_width = min(block_width, image_width - start_x)
            tiles.append(TileWindow(start_x=start_x, start_y=start_y, width=tile_width, height=tile_height))

    return tiles