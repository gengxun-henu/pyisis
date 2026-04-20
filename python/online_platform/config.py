"""Configuration helpers for the online platform backend prototype."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True, slots=True)
class OnlinePlatformSettings:
    """Container for environment-derived backend settings."""

    api_title: str = "Planetary Photogrammetry Online Platform"
    api_version: str = "0.1.0-prototype"
    environment: str = "development"
    database_url: str = "postgresql://localhost:5432/online_platform"
    redis_url: str = "redis://localhost:6379/0"
    object_storage_root: str = "./runtime/object_storage"
    workspace_root: str = "./runtime/workspaces"
    enable_archive_worker: bool = False

    @classmethod
    def from_env(cls) -> "OnlinePlatformSettings":
        """Build settings from environment variables with safe prototype defaults."""
        defaults = cls()
        return cls(
            api_title=os.environ.get("ONLINE_PLATFORM_API_TITLE", defaults.api_title),
            api_version=os.environ.get("ONLINE_PLATFORM_API_VERSION", defaults.api_version),
            environment=os.environ.get("ONLINE_PLATFORM_ENV", defaults.environment),
            database_url=os.environ.get("ONLINE_PLATFORM_DATABASE_URL", defaults.database_url),
            redis_url=os.environ.get("ONLINE_PLATFORM_REDIS_URL", defaults.redis_url),
            object_storage_root=os.environ.get(
                "ONLINE_PLATFORM_OBJECT_STORAGE_ROOT", defaults.object_storage_root
            ),
            workspace_root=os.environ.get("ONLINE_PLATFORM_WORKSPACE_ROOT", defaults.workspace_root),
            enable_archive_worker=os.environ.get("ONLINE_PLATFORM_ENABLE_ARCHIVE", "false").lower()
            in {"1", "true", "yes", "on"},
        )

    @property
    def object_storage_path(self) -> Path:
        return Path(self.object_storage_root)

    @property
    def workspace_path(self) -> Path:
        return Path(self.workspace_root)
