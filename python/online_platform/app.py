"""FastAPI application factory for the online platform backend prototype."""

from __future__ import annotations

from typing import Any

try:
    from fastapi import FastAPI
except ImportError:  # pragma: no cover - optional during skeleton stage
    FastAPI = None  # type: ignore[assignment]

from .api.routes.health import router as health_router
from .api.routes.jobs import router as jobs_router
from .api.routes.uploads import router as uploads_router
from .config import OnlinePlatformSettings


def create_app(settings: OnlinePlatformSettings | None = None) -> Any:
    """Create the FastAPI application when the dependency is available.

    The current repository does not yet declare runtime web dependencies, so this
    factory gracefully explains what is missing if FastAPI has not been installed.
    """
    resolved_settings = settings or OnlinePlatformSettings.from_env()

    if FastAPI is None:
        raise RuntimeError(
            "FastAPI is not installed. Install the web backend dependencies before "
            "running the online platform prototype."
        )

    app = FastAPI(title=resolved_settings.api_title, version=resolved_settings.api_version)
    app.state.settings = resolved_settings

    for candidate_router in (health_router, uploads_router, jobs_router):
        if candidate_router is not None:
            app.include_router(candidate_router)

    return app
