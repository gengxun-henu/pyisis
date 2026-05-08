"""Scaffolding frontends for deep matcher methods."""

from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_DEEP_METHODS = ("superglue", "lightglue", "loftr")


def normalize_deep_method(method: str) -> str:
    normalized = str(method).strip().lower()
    if normalized not in SUPPORTED_DEEP_METHODS:
        raise ValueError(f"Unsupported deep matcher method {method!r}. Expected one of {SUPPORTED_DEEP_METHODS}.")
    return normalized


def resolve_inference_device(*, prefer_gpu: bool = True, gpu_available: bool = False) -> str:
    if prefer_gpu and gpu_available:
        return "cuda"
    return "cpu"


@dataclass(frozen=True, slots=True)
class SuperPointFrontend:
    device: str = "cpu"


@dataclass(frozen=True, slots=True)
class LoFTRFrontend:
    device: str = "cpu"
