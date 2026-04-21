"""Prototype workflow builders for single-scene and multi-scene jobs."""

from __future__ import annotations

from typing import Any

from ..domain.models import ArtifactRecord, JobStep, StepStatus, JobType


_SINGLE_SCENE_STEPS = [
    "ingest_raw_img",
    "spiceinit_cube",
    "calibrate_cube",
    "orthorectify_cube",
    "package_outputs",
    "archive_to_baidu",
]

_MULTI_SCENE_STEPS = [
    "batch_ingest",
    "batch_spiceinit",
    "batch_preprocess",
    "compute_overlaps",
    "build_pairwise_controlnets",
    "merge_controlnets",
    "run_bundle_adjustment",
    "orthorectify_adjusted_cubes",
    "quality_assessment",
    "package_outputs",
    "archive_to_baidu",
]


def build_steps_for_job_type(job_type: JobType) -> list[JobStep]:
    """Return ordered step placeholders for the requested job type."""
    step_names = _SINGLE_SCENE_STEPS if job_type == JobType.SINGLE_SCENE else _MULTI_SCENE_STEPS
    return [JobStep(name=name, order=index + 1) for index, name in enumerate(step_names)]


def preview_single_scene_workflow(input_upload_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
    """Return a structured prototype preview for the single-scene workflow."""
    archive_to_baidu = bool(parameters.get("archive_to_baidu", False))
    return {
        "workflow_name": "single_scene_prototype",
        "input_upload_id": input_upload_id,
        "job_type": JobType.SINGLE_SCENE,
        "selected_features": {
            "spiceinit": bool(parameters.get("run_spiceinit", True)),
            "calibration": bool(parameters.get("run_calibration", True)),
            "orthorectification": bool(parameters.get("run_orthorectification", True)),
            "archive_to_baidu": archive_to_baidu,
        },
        "step_names": list(_SINGLE_SCENE_STEPS),
        "expected_artifacts": [
            "raw_ingest_manifest.json",
            "spice_initialized.cub",
            "calibrated.cub",
            "orthorectified.tif",
            "processing_report.json",
        ]
        + (["baidu_archive_receipt.json"] if archive_to_baidu else []),
        "prototype_notes": [
            "当前接口为原型接口，步骤以内联方式模拟执行。",
            "后续可将步骤映射到 Celery DAG 或实际 ISIS/pybind 调用。",
        ],
    }


def run_single_scene_workflow_prototype(
    *,
    job_id: str,
    workspace_layout: dict[str, str],
    parameters: dict[str, Any],
) -> tuple[list[JobStep], list[ArtifactRecord]]:
    """Simulate a successful single-scene run and emit prototype artifacts."""
    steps = build_steps_for_job_type(JobType.SINGLE_SCENE)
    for step in steps:
        step.status = StepStatus.SUCCEEDED
        step.log_path = f"{workspace_layout['processing']}/{step.order:02d}_{step.name}.log"
        step.summary = {
            "prototype": True,
            "job_id": job_id,
            "message": f"Step {step.name} completed in prototype mode.",
        }

    artifacts = [
        ArtifactRecord(
            artifact_type="manifest",
            path=f"{workspace_layout['artifacts']}/raw_ingest_manifest.json",
        ),
        ArtifactRecord(
            artifact_type="cube",
            path=f"{workspace_layout['artifacts']}/spice_initialized.cub",
        ),
        ArtifactRecord(
            artifact_type="cube",
            path=f"{workspace_layout['artifacts']}/calibrated.cub",
        ),
        ArtifactRecord(
            artifact_type="ortho_image",
            path=f"{workspace_layout['artifacts']}/orthorectified.tif",
            is_final_output=True,
            preview_path=f"{workspace_layout['artifacts']}/orthorectified_preview.png",
        ),
        ArtifactRecord(
            artifact_type="report",
            path=f"{workspace_layout['artifacts']}/processing_report.json",
        ),
    ]

    if parameters.get("archive_to_baidu", False):
        artifacts.append(
            ArtifactRecord(
                artifact_type="archive_receipt",
                path=f"{workspace_layout['artifacts']}/baidu_archive_receipt.json",
            )
        )

    return steps, artifacts
