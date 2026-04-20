"""Archive workflow placeholder for Baidu Netdisk integration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArchiveRequest:
    job_id: str
    source_path: str
    provider: str = "baidu_pan"


@dataclass(frozen=True, slots=True)
class ArchiveResult:
    status: str
    remote_path: str | None = None
    share_url: str | None = None
    message: str = "prototype placeholder"


class ArchiveService:
    """Prototype archive facade.

    The real implementation should encapsulate retries, large-file chunk upload,
    remote naming rules, and persistence of archive state transitions.
    """

    def submit(self, request: ArchiveRequest) -> ArchiveResult:
        return ArchiveResult(
            status="queued",
            remote_path=f"/pyisis/{request.job_id}",
            message="Archive request accepted by prototype placeholder.",
        )
