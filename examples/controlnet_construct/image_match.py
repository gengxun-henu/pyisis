"""Compatibility wrapper for the shared image_match CLI and API with deep match config validation.

Author: Geng Xun
Created: 2026-05-11
Updated: 2026-05-11  Geng Xun added top-of-file metadata so example compatibility wrappers follow the repository's example-file header convention.
Updated: 2026-05-16  Geng Xun added deep match config path validation before delegating to shared image_match module.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Deep match config validation
_deep_matcher_config_path = None
for i, arg in enumerate(sys.argv):
    if arg == "--deep-match-config-path" and i + 1 < len(sys.argv):
        _deep_matcher_config_path = sys.argv[i + 1]
        break

if _deep_matcher_config_path is not None:
    from deep_match_config import load_deep_match_config
    try:
        load_deep_match_config(_deep_matcher_config_path)
    except ValueError as exc:
        print(f"ERROR: Deep match config validation failed: {exc}", file=sys.stderr)
        sys.exit(1)

_IMAGE_MATCH_MODULE = import_module("image_match.image_match")
sys.modules[__name__] = _IMAGE_MATCH_MODULE


if __name__ == "__main__":
    _IMAGE_MATCH_MODULE.main()
