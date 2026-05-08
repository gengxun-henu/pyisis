"""Scaffolding matcher interfaces for deep matcher methods."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .deep_frontends import normalize_deep_method


@dataclass(frozen=True, slots=True)
class DeepMatchResult:
    left_keypoints: tuple[Any, ...] = ()
    right_keypoints: tuple[Any, ...] = ()
    matches: tuple[Any, ...] = ()


@dataclass(frozen=True, slots=True)
class _BaseDeepMatcher:
    method_name: str
    device: str = "cpu"

    def match(self, _left_image: Any, _right_image: Any) -> DeepMatchResult:
        raise NotImplementedError(f"{self.method_name} scaffolding is not implemented yet.")


class SuperGlueMatcher(_BaseDeepMatcher):
    def __init__(self, *, device: str = "cpu") -> None:
        super().__init__(method_name="superglue", device=device)


class LightGlueMatcher(_BaseDeepMatcher):
    def __init__(self, *, device: str = "cpu") -> None:
        super().__init__(method_name="lightglue", device=device)


class LoFTRMatcher(_BaseDeepMatcher):
    def __init__(self, *, device: str = "cpu") -> None:
        super().__init__(method_name="loftr", device=device)


def build_deep_matcher(method: str, *, device: str = "cpu") -> _BaseDeepMatcher:
    normalized = normalize_deep_method(method)
    if normalized == "superglue":
        return SuperGlueMatcher(device=device)
    if normalized == "lightglue":
        return LightGlueMatcher(device=device)
    if normalized == "loftr":
        return LoFTRMatcher(device=device)
    raise ValueError(f"Unsupported deep matcher method {method!r}.")
