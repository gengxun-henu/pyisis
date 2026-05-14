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
sys.modules[__name__] = _SHARED_MODULE
