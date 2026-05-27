"""Compatibility wrapper for shared ISIS tile-block alignment helpers.

Author: Geng Xun
Created: 2026-05-27
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_SHARED_MODULE = import_module("image_match.tile_block_alignment")
sys.modules[__name__] = _SHARED_MODULE
