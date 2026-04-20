"""Upload routes for the online platform backend prototype."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

try:
    from fastapi import APIRouter, status
except ImportError:  # pragma: no cover - optional during skeleton stage
    APIRouter = None  # type: ignore[assignment]

if APIRouter is not None:
    from ..schemas import UploadCreateRequest, UploadCreateResponse

    router: Any = APIRouter(prefix="/uploads", tags=["uploads"])

    @router.post("/", response_model=UploadCreateResponse, status_code=status.HTTP_202_ACCEPTED)
    def create_upload_placeholder(payload: UploadCreateRequest) -> UploadCreateResponse:
        return UploadCreateResponse(
            upload_id=str(uuid4()),
            filename=payload.filename,
            size_bytes=payload.size_bytes,
            mission=payload.mission,
            sensor_type=payload.sensor_type,
            status="accepted",
            message="Prototype placeholder only; real multipart upload is not implemented yet.",
        )
else:
    router = None
