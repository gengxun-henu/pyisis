"""Celery application factory placeholder for the online platform backend prototype."""

from __future__ import annotations

from typing import Any

try:
    from celery import Celery
except ImportError:  # pragma: no cover - optional during skeleton stage
    Celery = None  # type: ignore[assignment]

from ..config import OnlinePlatformSettings


def create_celery_app(settings: OnlinePlatformSettings | None = None) -> Any:
    resolved_settings = settings or OnlinePlatformSettings.from_env()
    if Celery is None:
        raise RuntimeError(
            "Celery is not installed. Install asynchronous worker dependencies before "
            "running the online platform prototype workers."
        )
    app = Celery("online_platform", broker=resolved_settings.redis_url, backend=resolved_settings.redis_url)
    app.conf.task_default_queue = "online-platform"
    return app
