"""Compatibility wrapper for shared DOM preparation helpers.

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

_IMAGE_MATCH_MODULE = import_module("image_match.dom_prepare")
sys.modules[__name__] = _IMAGE_MATCH_MODULE


if __name__ == "__main__":
    _IMAGE_MATCH_MODULE.main()
