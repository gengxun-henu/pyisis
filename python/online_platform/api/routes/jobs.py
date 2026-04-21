"""Job routes for the online platform backend prototype."""

from __future__ import annotations

from typing import Any

try:
    from fastapi import APIRouter, HTTPException, status
except ImportError:  # pragma: no cover - optional during skeleton stage
    APIRouter = None  # type: ignore[assignment]

from ...config import OnlinePlatformSettings
from ...services.job_service import InMemoryJobService
from ...services.storage_service import StorageService

_settings = OnlinePlatformSettings.from_env()
_job_service = InMemoryJobService(storage_service=StorageService(_settings))

if APIRouter is not None:
    from ..schemas import (
        JobCreateRequest,
        JobResponse,
        SingleSceneWorkflowPreviewResponse,
        SingleSceneWorkflowRequest,
        WorkflowSubmissionResponse,
    )

    router: Any = APIRouter(prefix="/jobs", tags=["jobs"])

    @router.get("/", response_model=list[JobResponse])
    def list_jobs() -> list[JobResponse]:
        return [JobResponse.model_validate(_job_service.serialize_job(job)) for job in _job_service.list_jobs()]

    @router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
    def create_job(payload: JobCreateRequest) -> JobResponse:
        job = _job_service.create_job(
            job_type=payload.job_type,
            target_body=payload.target_body,
            input_upload_ids=payload.input_upload_ids,
            parameter_json=payload.parameter_json,
        )
        return JobResponse.model_validate(_job_service.serialize_job(job))

    @router.get("/{job_id}", response_model=JobResponse)
    def get_job(job_id: str) -> JobResponse:
        job = _job_service.get_job(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_id}' was not found.",
            )
        return JobResponse.model_validate(_job_service.serialize_job(job))

    @router.post(
        "/single-scene/preview",
        response_model=SingleSceneWorkflowPreviewResponse,
        status_code=status.HTTP_200_OK,
    )
    def preview_single_scene_workflow(
        payload: SingleSceneWorkflowRequest,
    ) -> SingleSceneWorkflowPreviewResponse:
        preview = _job_service.preview_single_scene_job(
            target_body=payload.target_body,
            input_upload_id=payload.input_upload_id,
            parameter_json=payload.parameters.model_dump(),
        )
        return SingleSceneWorkflowPreviewResponse.model_validate(preview)

    @router.post(
        "/single-scene/run",
        response_model=WorkflowSubmissionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def run_single_scene_workflow(
        payload: SingleSceneWorkflowRequest,
    ) -> WorkflowSubmissionResponse:
        job, layout = _job_service.submit_single_scene_job(
            target_body=payload.target_body,
            input_upload_id=payload.input_upload_id,
            parameter_json=payload.parameters.model_dump(),
        )
        return WorkflowSubmissionResponse(
            execution_mode="inline-prototype",
            job=JobResponse.model_validate(_job_service.serialize_job(job)),
            layout=layout,
        )
else:
    router = None
