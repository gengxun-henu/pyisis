"""Compatibility wrapper for deep matcher frontend helpers.

Author: Geng Xun / Codex
Created: 2026-05-11
Updated: 2026-05-22  Geng Xun / Codex converted this module to re-export the image_match runtime implementation.
"""

from __future__ import annotations

import sys

from image_match import deep_frontends as _deep_frontends

_deep_frontends.__all__ = [
    "SUPPORTED_DEEP_METHODS",
    "DeepDependencyError",
    "DeepFrontendError",
    "LoFTRFrontend",
    "SuperPointFrontend",
    "normalize_deep_method",
    "resolve_torch_device",
]

sys.modules[__name__] = _deep_frontends
