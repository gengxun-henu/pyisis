"""Health-check route for the online platform backend prototype."""

from __future__ import annotations

from typing import Any

try:
    from fastapi import APIRouter
except ImportError:  # pragma: no cover - optional during skeleton stage
    APIRouter = None  # type: ignore[assignment]

if APIRouter is not None:
    from ..schemas import HealthResponse

    router: Any = APIRouter(prefix="/health", tags=["health"])

    @router.get("/", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="online_platform_prototype")
else:
    router = None
