"""Compatibility wrapper for the shared match-visualization helpers.

Author: Geng Xun
Created: 2026-05-11
Updated: 2026-05-11  Geng Xun added top-of-file metadata so example compatibility wrappers follow the repository's example-file header convention.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_SHARED_MODULE = import_module("image_match.match_visualization")
_EXPORTED_NAMES = [name for name in dir(_SHARED_MODULE) if not name.startswith("__")]

globals().update({name: getattr(_SHARED_MODULE, name) for name in _EXPORTED_NAMES})
__all__ = list(_EXPORTED_NAMES)
