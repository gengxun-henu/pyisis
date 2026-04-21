"""Pydantic request/response schemas for the online platform prototype API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..domain.models import JobStatus, JobType, StepStatus


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    service: str = Field(examples=["online_platform_prototype"])


class UploadCreateRequest(BaseModel):
    filename: str = Field(min_length=1, examples=["M123456789LE.IMG"])
    size_bytes: int = Field(default=0, ge=0)
    mission: str | None = Field(default="LRO")
    sensor_type: str | None = Field(default="NAC")


class UploadCreateResponse(BaseModel):
    upload_id: str
    filename: str
    size_bytes: int
    mission: str | None = None
    sensor_type: str | None = None
    status: str = Field(examples=["accepted"])
    message: str


class SingleSceneParameters(BaseModel):
    run_spiceinit: bool = True
    run_calibration: bool = True
    run_orthorectification: bool = True
    shape_model: str = Field(default="lro_wac_global_dtm_100m")
    map_template: str = Field(default="default_lunar_polar")
    archive_to_baidu: bool = False
    notes: str | None = None


class SingleSceneWorkflowRequest(BaseModel):
    target_body: str = Field(default="Moon", min_length=1)
    input_upload_id: str = Field(min_length=1)
    parameters: SingleSceneParameters = Field(default_factory=SingleSceneParameters)


class JobCreateRequest(BaseModel):
    job_type: JobType
    target_body: str = Field(min_length=1)
    input_upload_ids: list[str] = Field(min_length=1)
    parameter_json: dict[str, Any] = Field(default_factory=dict)


class JobStepResponse(BaseModel):
    name: str
    order: int
    status: StepStatus
    log_path: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)


class ArtifactResponse(BaseModel):
    artifact_type: str
    path: str
    is_final_output: bool = False
    preview_path: str | None = None


class JobResponse(BaseModel):
    id: str
    job_type: JobType
    target_body: str
    input_upload_ids: list[str]
    parameter_json: dict[str, Any]
    status: JobStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_summary: str | None = None
    steps: list[JobStepResponse] = Field(default_factory=list)
    artifacts: list[ArtifactResponse] = Field(default_factory=list)


class SingleSceneWorkflowPreviewResponse(BaseModel):
    workflow_name: str = Field(default="single_scene_prototype")
    target_body: str
    input_upload_id: str
    job_type: JobType = Field(default=JobType.SINGLE_SCENE)
    selected_features: dict[str, bool]
    step_names: list[str]
    expected_artifacts: list[str]
    prototype_notes: list[str]


class WorkflowSubmissionResponse(BaseModel):
    workflow_name: str = Field(default="single_scene_prototype")
    execution_mode: str = Field(examples=["inline-prototype"])
    job: JobResponse
    layout: dict[str, str]
