"""Compatibility wrapper for the shared `.key` helpers.

Author: Geng Xun
Created: 2026-05-11
Updated: 2026-05-14  Geng Xun switched this compatibility shim to a true shared-module alias so keypoint classes stay identical across imports.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_SHARED_MODULE = import_module("image_match.keypoints")
sys.modules[__name__] = _SHARED_MODULE