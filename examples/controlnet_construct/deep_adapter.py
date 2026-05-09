"""Scaffolding adapter for deep matcher method routing."""

from __future__ import annotations

from typing import Any

from .deep_frontends import normalize_deep_method, resolve_torch_device
from .deep_matchers import DeepMatchResult, build_deep_matcher


class DeepDependencyError(RuntimeError):
    """Raised when a deep matcher dependency is unavailable."""

    def __init__(self, method: str, reason: str) -> None:
        self.method = str(method).strip().lower()
        self.reason = str(reason).strip()
        super().__init__(f"Deep matcher dependency unavailable for '{self.method}': {self.reason}")


class DeepMatcherAdapter:
    def __init__(self, *, prefer_gpu: bool = True) -> None:
        self._device = resolve_torch_device(prefer_gpu)

    def _raise_cross_method_fallback_error(self, requested: str, fallback_to: str) -> None:
        raise RuntimeError(
            "Deep matcher fallback must use the same method: "
            f"requested={requested!r}, fallback_to={fallback_to!r}."
        )

    def resolve_fallback_method(self, *, requested_method: str, fallback_method: str) -> str:
        requested = normalize_deep_method(requested_method)
        fallback = str(fallback_method).strip().lower()
        if fallback != requested:
            self._raise_cross_method_fallback_error(requested, fallback)
        return fallback

    def match_pair(self, *, matcher_method: str, left_image: Any, right_image: Any) -> DeepMatchResult:
        method = normalize_deep_method(matcher_method)
        matcher = build_deep_matcher(method, device=self._device)
        return matcher.match(left_image, right_image)

    def match_pair_with_fallback(
        self,
        *,
        matcher_method: str,
        left_image: Any,
        right_image: Any,
        prefer_gpu: bool,
    ) -> DeepMatchResult:
        method = normalize_deep_method(matcher_method)
        primary_device = resolve_torch_device(prefer_gpu)
        try:
            primary_matcher = build_deep_matcher(method, device=primary_device)
            return primary_matcher.match(left_image, right_image)
        except Exception:
            if not prefer_gpu:
                raise
            fallback_method = self.resolve_fallback_method(requested_method=method, fallback_method=method)
            fallback_matcher = build_deep_matcher(fallback_method, device=resolve_torch_device(False))
            return fallback_matcher.match(left_image, right_image)
