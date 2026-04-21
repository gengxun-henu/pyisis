"""Core in-memory models for jobs, uploads, steps, and artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class JobType(StrEnum):
    SINGLE_SCENE = "single_scene"
    MULTI_SCENE_BUNDLE = "multi_scene_bundle"


class JobStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ARCHIVING = "archiving"
    ARCHIVED = "archived"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class UploadRecord:
    id: str
    filename: str
    local_path: str
    size_bytes: int = 0
    mission: str | None = None
    sensor_type: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class JobStep:
    name: str
    order: int
    status: StepStatus = StepStatus.PENDING
    log_path: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ArtifactRecord:
    artifact_type: str
    path: str
    is_final_output: bool = False
    preview_path: str | None = None


@dataclass(slots=True)
class ProcessingJob:
    job_type: JobType
    target_body: str
    input_upload_ids: list[str]
    parameter_json: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_summary: str | None = None
    steps: list[JobStep] = field(default_factory=list)
    artifacts: list[ArtifactRecord] = field(default_factory=list)
