"""Minimal matcher scaffolding for deep matcher methods."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .deep_frontends import normalize_deep_method


class DeepMatcherError(RuntimeError):
    """Raised for unsupported deep matcher operations."""


@dataclass(frozen=True, slots=True)
class DeepMatchResult:
    left_keypoints: tuple[Any, ...] = ()
    right_keypoints: tuple[Any, ...] = ()
    matches: tuple[Any, ...] = ()


class SuperGlueMatcher:
    method = "superglue"

    def __init__(self, *, device: str = "cpu") -> None:
        self.device = device

    def match(self, _left_image: Any, _right_image: Any) -> DeepMatchResult:
        raise DeepMatcherError(f"{self.method} scaffolding is not implemented yet.")


class LightGlueMatcher:
    method = "lightglue"

    def __init__(self, *, device: str = "cpu") -> None:
        self.device = device

    def match(self, _left_image: Any, _right_image: Any) -> DeepMatchResult:
        raise DeepMatcherError(f"{self.method} scaffolding is not implemented yet.")


class LoFTRMatcher:
    method = "loftr"

    def __init__(self, *, device: str = "cpu") -> None:
        self.device = device

    def match(self, _left_image: Any, _right_image: Any) -> DeepMatchResult:
        raise DeepMatcherError(f"{self.method} scaffolding is not implemented yet.")


def build_deep_matcher(method: str, *, device: str = "cpu") -> SuperGlueMatcher | LightGlueMatcher | LoFTRMatcher:
    normalized = normalize_deep_method(method)
    if normalized == "superglue":
        return SuperGlueMatcher(device=device)
    if normalized == "lightglue":
        return LightGlueMatcher(device=device)
    if normalized == "loftr":
        return LoFTRMatcher(device=device)
    raise DeepMatcherError(f"Unsupported deep matcher method {method!r}.")
