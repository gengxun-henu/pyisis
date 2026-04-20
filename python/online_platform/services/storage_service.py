"""Storage planning helpers for the online platform backend prototype."""

from __future__ import annotations

from pathlib import Path

from ..config import OnlinePlatformSettings


class StorageService:
    """Plan local/object-storage layout for uploaded files and generated artifacts."""

    def __init__(self, settings: OnlinePlatformSettings) -> None:
        self._settings = settings

    def upload_workspace(self, job_id: str) -> Path:
        return self._settings.workspace_path / job_id / "uploads"

    def processing_workspace(self, job_id: str) -> Path:
        return self._settings.workspace_path / job_id / "processing"

    def artifact_workspace(self, job_id: str) -> Path:
        return self._settings.workspace_path / job_id / "artifacts"

    def ensure_local_layout(self, job_id: str) -> dict[str, str]:
        paths = {
            "uploads": self.upload_workspace(job_id),
            "processing": self.processing_workspace(job_id),
            "artifacts": self.artifact_workspace(job_id),
        }
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
        return {key: str(value) for key, value in paths.items()}
