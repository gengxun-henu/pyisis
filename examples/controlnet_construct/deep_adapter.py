"""Scaffolding adapter for deep matcher method routing."""

from __future__ import annotations

from typing import Any

from .deep_frontends import normalize_deep_method, resolve_inference_device
from .deep_matchers import DeepMatchResult, build_deep_matcher


class DeepDependencyError(RuntimeError):
    """Raised when a deep matcher dependency is unavailable."""


class DeepMatcherAdapter:
    def __init__(self, *, prefer_gpu: bool = True, gpu_available: bool = False) -> None:
        self._device = resolve_inference_device(prefer_gpu=prefer_gpu, gpu_available=gpu_available)

    def resolve_fallback_method(self, *, requested_method: str, fallback_method: str) -> str:
        requested = normalize_deep_method(requested_method)
        fallback = str(fallback_method).strip().lower()
        if fallback != requested:
            raise ValueError(
                "Cross-method fallback is not allowed for deep matchers: "
                f"requested={requested!r}, fallback={fallback!r}."
            )
        return fallback

    def missing_dependency_error(
        self,
        *,
        requested_method: str,
        dependency_name: str,
        install_hint: str | None = None,
    ) -> DeepDependencyError:
        method = normalize_deep_method(requested_method)
        detail = f"Missing dependency '{dependency_name}' for deep matcher method '{method}'."
        if install_hint:
            detail = f"{detail} {install_hint}".strip()
        return DeepDependencyError(detail)

    def require_dependency(
        self,
        *,
        requested_method: str,
        dependency_name: str,
        available: bool,
        install_hint: str | None = None,
    ) -> None:
        if not available:
            raise self.missing_dependency_error(
                requested_method=requested_method,
                dependency_name=dependency_name,
                install_hint=install_hint,
            )

    def match_pair(self, *, matcher_method: str, left_image: Any, right_image: Any) -> DeepMatchResult:
        method = normalize_deep_method(matcher_method)
        matcher = build_deep_matcher(method, device=self._device)
        return matcher.match(left_image, right_image)
