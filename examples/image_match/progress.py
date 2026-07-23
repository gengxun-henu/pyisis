"""Render terminal progress for tiled image matching.

Author: Geng Xun
Created: 2026-07-23
Updated: 2026-07-23  Geng Xun extracted progress rendering from the image-match orchestrator.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import TextIO


class TileProgressBar:
    """Track and render completion of one full-resolution tile pass."""

    def __init__(
        self,
        *,
        left_dom_path: str | Path,
        right_dom_path: str | Path,
        total_tiles: int,
        stream: TextIO | None = None,
        width: int = 30,
    ) -> None:
        self._left_dom_path = Path(left_dom_path)
        self._right_dom_path = Path(right_dom_path)
        self._total_tiles = max(0, int(total_tiles))
        self._stream = sys.stderr if stream is None else stream
        self._width = max(10, int(width))
        self._completed_tiles = 0
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        print(
            "[image-match] "
            f"{self._left_dom_path.name} ↔ {self._right_dom_path.name}: "
            f"{self._total_tiles} TILE(s) to process at full resolution.",
            file=self._stream,
            flush=True,
        )
        self._render()

    def update(self) -> None:
        if not self._started:
            self.start()
        self._completed_tiles = min(self._completed_tiles + 1, self._total_tiles)
        self._render()

    def finish(self) -> None:
        if not self._started:
            return
        print(file=self._stream, flush=True)

    def _render(self) -> None:
        if self._total_tiles <= 0:
            bar = "-" * self._width
            percent = 100.0
        else:
            percent = 100.0 * self._completed_tiles / self._total_tiles
            filled_width = int(round(self._width * self._completed_tiles / self._total_tiles))
            bar = "#" * filled_width + "-" * (self._width - filled_width)
        print(
            "\r[image-match] "
            f"[{bar}] {self._completed_tiles}/{self._total_tiles} TILE(s) "
            f"done ({percent:5.1f}%)",
            end="",
            file=self._stream,
            flush=True,
        )
