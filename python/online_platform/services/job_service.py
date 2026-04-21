"""In-memory job service used by the backend prototype."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from ..domain.models import JobStatus, JobType, ProcessingJob
from ..services.storage_service import StorageService
from ..tasks.workflows import (
    build_steps_for_job_type,
    preview_single_scene_workflow,
    run_single_scene_workflow_prototype,
)


class InMemoryJobService:
    """Minimal in-memory repository/service used during prototype design.

    This is intentionally simple. It gives the API layer something concrete to call
    before the real PostgreSQL persistence layer is introduced.
    """

    def __init__(self, storage_service: StorageService | None = None) -> None:
        self._jobs: dict[str, ProcessingJob] = {}
        self._storage_service = storage_service

    def create_job(
        self,
        *,
        job_type: JobType,
        target_body: str,
        input_upload_ids: list[str],
        parameter_json: dict[str, Any],
    ) -> ProcessingJob:
        job = ProcessingJob(
            job_type=job_type,
            target_body=target_body,
            input_upload_ids=input_upload_ids,
            parameter_json=parameter_json,
        )
        job.steps = build_steps_for_job_type(job_type)
        job.status = JobStatus.QUEUED
        self._jobs[job.id] = job
        return job

    def list_jobs(self) -> list[ProcessingJob]:
        return list(self._jobs.values())

    def get_job(self, job_id: str) -> ProcessingJob | None:
        return self._jobs.get(job_id)

    def mark_running(self, job_id: str) -> ProcessingJob | None:
        job = self.get_job(job_id)
        if job is None:
            return None
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        return job

    def preview_single_scene_job(
        self,
        *,
        target_body: str,
        input_upload_id: str,
        parameter_json: dict[str, Any],
    ) -> dict[str, Any]:
        preview = preview_single_scene_workflow(input_upload_id, parameter_json)
        preview["target_body"] = target_body
        return preview

    def submit_single_scene_job(
        self,
        *,
        target_body: str,
        input_upload_id: str,
        parameter_json: dict[str, Any],
    ) -> tuple[ProcessingJob, dict[str, str]]:
        job = self.create_job(
            job_type=JobType.SINGLE_SCENE,
            target_body=target_body,
            input_upload_ids=[input_upload_id],
            parameter_json=parameter_json,
        )
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)

        layout = {}
        if self._storage_service is not None:
            layout = self._storage_service.ensure_local_layout(job.id)

        steps, artifacts = run_single_scene_workflow_prototype(
            job_id=job.id,
            workspace_layout=layout
            or {
                "uploads": f"runtime/workspaces/{job.id}/uploads",
                "processing": f"runtime/workspaces/{job.id}/processing",
                "artifacts": f"runtime/workspaces/{job.id}/artifacts",
            },
            parameters=parameter_json,
        )
        job.steps = steps
        job.artifacts = artifacts
        job.status = JobStatus.SUCCEEDED
        job.finished_at = datetime.now(timezone.utc)
        return job, layout

    def serialize_job(self, job: ProcessingJob) -> dict[str, Any]:
        return asdict(job)
