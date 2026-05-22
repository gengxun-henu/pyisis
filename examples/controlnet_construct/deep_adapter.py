"""Compatibility wrapper for deep matcher adapter routing.

Author: Geng Xun / Codex
Created: 2026-05-11
Updated: 2026-05-22  Geng Xun / Codex converted this module to re-export the image_match runtime implementation.
"""

from __future__ import annotations

import sys

from image_match import deep_adapter as _deep_adapter

_deep_adapter.__all__ = [
    "DeepMatcherAdapter",
    "DeepDependencyError",
    "DeepFrontendError",
    "LoFTRFrontend",
    "SuperPointFrontend",
    "normalize_deep_method",
    "resolve_torch_device",
    "DeepMatchResult",
    "DeepMatcherError",
    "_default_feature_extractor_for_matcher",
    "build_deep_matcher",
    "_filter_feature_dict_by_invalid_mask",
    "_runtime_feature_extractor_method",
    "_valid_mask_keep",
    "_validate_runtime_matcher_compatibility",
]

sys.modules[__name__] = _deep_adapter
