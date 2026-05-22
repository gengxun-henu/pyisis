"""Compatibility wrapper for deep matcher runtime implementations.

Author: Geng Xun / Codex
Created: 2026-05-19
Updated: 2026-05-22  Geng Xun / Codex converted this module to re-export the image_match runtime implementation.
"""

from __future__ import annotations

import sys

from image_match import deep_matchers as _deep_matchers

_deep_matchers.__all__ = [
    "DeepMatchResult",
    "DeepMatcherError",
    "LightGlueMatcher",
    "LoFTRMatcher",
    "SuperGlueMatcher",
    "_default_feature_extractor_for_matcher",
    "build_deep_matcher",
]

sys.modules[__name__] = _deep_matchers
