"""Compatibility wrapper for the shared image_match CLI and API.

Author: Geng Xun
Created: 2026-05-11
Updated: 2026-05-11  Geng Xun added top-of-file metadata so example compatibility wrappers follow the repository's example-file header convention.
Updated: 2026-05-16  Geng Xun added deep match config path validation before delegating to shared image_match module.
Updated: 2026-05-19  Geng Xun delegated deep match config path parsing and validation to the shared image_match CLI.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_IMAGE_MATCH_MODULE = import_module("image_match.image_match")
sys.modules[__name__] = _IMAGE_MATCH_MODULE


if __name__ == "__main__":
    _IMAGE_MATCH_MODULE.main()
