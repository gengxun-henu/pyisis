"""Compatibility wrapper for the shared image_match CLI and API.

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

_IMAGE_MATCH_MODULE = import_module("image_match.image_match")
main = _IMAGE_MATCH_MODULE.main

_EXPORTED_NAMES = [name for name in dir(_IMAGE_MATCH_MODULE) if not name.startswith("_")]

globals().update({name: getattr(_IMAGE_MATCH_MODULE, name) for name in _EXPORTED_NAMES})
__all__ = list(_EXPORTED_NAMES)


if __name__ == "__main__":
    main()
