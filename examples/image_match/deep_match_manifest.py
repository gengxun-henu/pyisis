"""Manifest helpers for cross-environment deep image matching workflows.

Author: Geng Xun
Created: 2026-05-16
Updated: 2026-05-16  Geng Xun added pair-manifest helpers for exporting deep-matching tile tasks, workspace layouts, and result file conventions.
Updated: 2026-05-16  Geng Xun added standardized NPZ result helpers for deep-learning manifest executors and later import stages.
Updated: 2026-05-20  Geng Xun added stage-6 provenance fields so exported task manifests preserve runtime config, config path, and execution-environment hints.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import numpy as np
from pathlib import Path
import sys
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .tile_matching import TileMatchTask


DEEP_MATCH_MANIFEST_FORMAT_VERSION = 1
DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME = "tmp_deep_match"


def _tile_match_task_to_payload(tile_task: Any) -> dict[str, Any]:
    if isinstance(tile_task, dict):
        return dict(tile_task)
    from .tile_matching import tile_match_task_to_payload

    return tile_match_task_to_payload(tile_task)


def _tile_match_task_from_payload(payload: dict[str, Any]) -> Any:
    try:
        from .tile_matching import tile_match_task_from_payload
    except Exception:
        return dict(payload)
    return tile_match_task_from_payload(dict(payload))


@dataclass(frozen=True, slots=True)
class DeepMatchWorkspacePaths:
    """Resolved workspace layout for one exported deep-matching pair."""

    pair_id: str
    root_dir: Path
    images_dir: Path
    results_dir: Path
    logs_dir: Path
    manifest_path: Path


@dataclass(frozen=True, slots=True)
class DeepMatchTaskRecord:
    """Serializable description of one exported tile-matching job."""

    task_index: int
    left_image_path: str
    right_image_path: str
    left_mask_path: str
    right_mask_path: str
    result_path: str
    log_path: str
    tile_task: TileMatchTask
    deep_match_config_path: str | None = None
    deep_match_runtime_config: dict[str, Any] | None = None
    matcher_method: str | None = None
    feature_extractor_method: str | None = None
    tile_window: dict[str, Any] | None = None
    invalid_mask_summary: dict[str, Any] | None = None
    normalization: dict[str, Any] | None = None
    created_by_python: str | None = None
    created_at_utc: str | None = None


@dataclass(frozen=True, slots=True)
class DeepMatchPairManifest:
    """Top-level manifest for a deep-learning pair exported from asp360_new."""

    format_version: int
    pair_id: str
    workspace_root: str
    left_dom_path: str
    right_dom_path: str
    image_space: str
    matcher_method: str
    requested_device: str
    band: int
    created_at_utc: str
    tasks: tuple[DeepMatchTaskRecord, ...]
    metadata: dict[str, Any]


def default_deep_match_pair_id(
    *,
    left_dom_path: str | Path,
    right_dom_path: str | Path,
    matcher_method: str,
    band: int,
    image_space: str,
) -> str:
    """Build a stable pair identifier for deep-match export directories."""

    identity_text = "\n".join(
        [
            str(Path(left_dom_path)),
            str(Path(right_dom_path)),
            str(matcher_method).strip().lower(),
            str(int(band)),
            str(image_space).strip().lower(),
        ]
    )
    digest = hashlib.sha256(identity_text.encode("utf-8")).hexdigest()[:16]
    left_stem = Path(left_dom_path).stem or "left"
    right_stem = Path(right_dom_path).stem or "right"
    return f"{left_stem}__{right_stem}__{digest}"


def resolve_deep_match_workspace(
    *,
    temp_root_dir: str | Path,
    pair_id: str,
) -> DeepMatchWorkspacePaths:
    """Resolve the directory layout used by one exported deep-matching pair."""

    root_dir = Path(temp_root_dir).expanduser().resolve() / pair_id
    return DeepMatchWorkspacePaths(
        pair_id=pair_id,
        root_dir=root_dir,
        images_dir=root_dir / "images",
        results_dir=root_dir / "results",
        logs_dir=root_dir / "logs",
        manifest_path=root_dir / "tasks.json",
    )


def ensure_deep_match_workspace(paths: DeepMatchWorkspacePaths) -> DeepMatchWorkspacePaths:
    """Create the standard workspace directories for an exported pair."""

    paths.images_dir.mkdir(parents=True, exist_ok=True)
    paths.results_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    return paths


def build_deep_match_task_record(
    *,
    task_index: int,
    tile_task: TileMatchTask,
    workspace: DeepMatchWorkspacePaths,
    deep_match_config_path: str | Path | None = None,
    deep_match_runtime_config: Any | None = None,
    created_by_python: str | None = None,
    created_at_utc: str | None = None,
) -> DeepMatchTaskRecord:
    """Create one task record with deterministic artifact paths."""

    runtime_config_payload = _runtime_config_to_payload(
        tile_task.deep_match_runtime_config if tile_task.deep_match_runtime_config is not None else deep_match_runtime_config
    )
    stem = f"task_{int(task_index):05d}"
    return DeepMatchTaskRecord(
        task_index=int(task_index),
        left_image_path=str(workspace.images_dir / f"{stem}_left.npy"),
        right_image_path=str(workspace.images_dir / f"{stem}_right.npy"),
        left_mask_path=str(workspace.images_dir / f"{stem}_left_mask.npy"),
        right_mask_path=str(workspace.images_dir / f"{stem}_right_mask.npy"),
        result_path=str(workspace.results_dir / f"{stem}_matches.npz"),
        log_path=str(workspace.logs_dir / f"{stem}.log"),
        tile_task=tile_task,
        deep_match_config_path=(
            None if deep_match_config_path is None else str(Path(deep_match_config_path))
        ),
        deep_match_runtime_config=runtime_config_payload,
        matcher_method=str(tile_task.matcher_method).strip().lower(),
        feature_extractor_method=(
            None if runtime_config_payload is None else str(runtime_config_payload.get("feature_extractor_method"))
        ),
        tile_window=asdict(tile_task.paired_window),
        invalid_mask_summary={
            "invalid_values": list(tile_task.invalid_values),
            "special_pixel_abs_threshold": float(tile_task.special_pixel_abs_threshold),
            "min_valid_pixels": int(tile_task.min_valid_pixels),
            "valid_pixel_percent_threshold": float(tile_task.valid_pixel_percent_threshold),
            "invalid_pixel_radius": int(tile_task.invalid_pixel_radius),
        },
        normalization={
            "minimum_value": tile_task.minimum_value,
            "maximum_value": tile_task.maximum_value,
            "lower_percent": float(tile_task.lower_percent),
            "upper_percent": float(tile_task.upper_percent),
        },
        created_by_python=created_by_python,
        created_at_utc=created_at_utc,
    )


def build_deep_match_pair_manifest(
    *,
    tasks: list[TileMatchTask] | tuple[TileMatchTask, ...],
    left_dom_path: str | Path,
    right_dom_path: str | Path,
    matcher_method: str,
    band: int,
    image_space: str,
    temp_root_dir: str | Path,
    requested_device: str = "cuda",
    pair_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    created_at_utc: str | None = None,
    deep_match_config_path: str | Path | None = None,
    deep_match_runtime_config: Any | None = None,
    created_by_python: str | None = None,
) -> DeepMatchPairManifest:
    """Build a top-level manifest for later deep-learning execution."""

    resolved_pair_id = pair_id or default_deep_match_pair_id(
        left_dom_path=left_dom_path,
        right_dom_path=right_dom_path,
        matcher_method=matcher_method,
        band=band,
        image_space=image_space,
    )
    workspace = resolve_deep_match_workspace(
        temp_root_dir=temp_root_dir,
        pair_id=resolved_pair_id,
    )
    timestamp = created_at_utc or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    task_records = tuple(
        build_deep_match_task_record(
            task_index=index,
            tile_task=task,
            workspace=workspace,
            deep_match_config_path=deep_match_config_path,
            deep_match_runtime_config=deep_match_runtime_config,
            created_by_python=created_by_python or sys.executable,
            created_at_utc=timestamp,
        )
        for index, task in enumerate(tasks)
    )
    return DeepMatchPairManifest(
        format_version=DEEP_MATCH_MANIFEST_FORMAT_VERSION,
        pair_id=resolved_pair_id,
        workspace_root=str(workspace.root_dir),
        left_dom_path=str(left_dom_path),
        right_dom_path=str(right_dom_path),
        image_space=str(image_space).strip().lower(),
        matcher_method=str(matcher_method).strip().lower(),
        requested_device=str(requested_device).strip().lower(),
        band=int(band),
        created_at_utc=timestamp,
        tasks=task_records,
        metadata=dict(metadata or {}),
    )


def deep_match_task_record_to_payload(record: DeepMatchTaskRecord) -> dict[str, Any]:
    """Serialize a task record to a JSON-friendly payload."""

    return {
        "task_index": record.task_index,
        "left_image_path": record.left_image_path,
        "right_image_path": record.right_image_path,
        "left_mask_path": record.left_mask_path,
        "right_mask_path": record.right_mask_path,
        "result_path": record.result_path,
        "log_path": record.log_path,
        "tile_task": _tile_match_task_to_payload(record.tile_task),
        "deep_match_config_path": record.deep_match_config_path,
        "deep_match_runtime_config": record.deep_match_runtime_config,
        "matcher_method": record.matcher_method,
        "feature_extractor_method": record.feature_extractor_method,
        "tile_window": record.tile_window,
        "invalid_mask_summary": record.invalid_mask_summary,
        "normalization": record.normalization,
        "created_by_python": record.created_by_python,
        "created_at_utc": record.created_at_utc,
    }


def deep_match_task_record_from_payload(payload: dict[str, Any]) -> DeepMatchTaskRecord:
    """Deserialize one task record from a JSON payload."""

    return DeepMatchTaskRecord(
        task_index=int(payload["task_index"]),
        left_image_path=str(payload["left_image_path"]),
        right_image_path=str(payload["right_image_path"]),
        left_mask_path=str(payload["left_mask_path"]),
        right_mask_path=str(payload["right_mask_path"]),
        result_path=str(payload["result_path"]),
        log_path=str(payload["log_path"]),
        tile_task=_tile_match_task_from_payload(dict(payload["tile_task"])),
        deep_match_config_path=payload.get("deep_match_config_path"),
        deep_match_runtime_config=dict(payload["deep_match_runtime_config"])
        if isinstance(payload.get("deep_match_runtime_config"), dict)
        else payload.get("deep_match_runtime_config"),
        matcher_method=payload.get("matcher_method"),
        feature_extractor_method=payload.get("feature_extractor_method"),
        tile_window=dict(payload["tile_window"]) if isinstance(payload.get("tile_window"), dict) else payload.get("tile_window"),
        invalid_mask_summary=dict(payload["invalid_mask_summary"])
        if isinstance(payload.get("invalid_mask_summary"), dict)
        else payload.get("invalid_mask_summary"),
        normalization=dict(payload["normalization"])
        if isinstance(payload.get("normalization"), dict)
        else payload.get("normalization"),
        created_by_python=payload.get("created_by_python"),
        created_at_utc=payload.get("created_at_utc"),
    )


def _runtime_config_to_payload(runtime_config: Any | None) -> dict[str, Any] | None:
    if runtime_config is None:
        return None
    if isinstance(runtime_config, dict):
        return dict(runtime_config)
    if is_dataclass(runtime_config):
        return asdict(runtime_config)
    if hasattr(runtime_config, "__dict__"):
        return dict(vars(runtime_config))
    raise TypeError(f"Unsupported deep_match_runtime_config payload type: {type(runtime_config)!r}")


def deep_match_pair_manifest_to_payload(manifest: DeepMatchPairManifest) -> dict[str, Any]:
    """Serialize a pair manifest to a JSON-friendly payload."""

    return {
        "format_version": manifest.format_version,
        "pair_id": manifest.pair_id,
        "workspace_root": manifest.workspace_root,
        "left_dom_path": manifest.left_dom_path,
        "right_dom_path": manifest.right_dom_path,
        "image_space": manifest.image_space,
        "matcher_method": manifest.matcher_method,
        "requested_device": manifest.requested_device,
        "band": manifest.band,
        "created_at_utc": manifest.created_at_utc,
        "tasks": [deep_match_task_record_to_payload(record) for record in manifest.tasks],
        "metadata": dict(manifest.metadata),
    }


def deep_match_pair_manifest_from_payload(payload: dict[str, Any]) -> DeepMatchPairManifest:
    """Deserialize a pair manifest from a JSON payload."""

    return DeepMatchPairManifest(
        format_version=int(payload["format_version"]),
        pair_id=str(payload["pair_id"]),
        workspace_root=str(payload["workspace_root"]),
        left_dom_path=str(payload["left_dom_path"]),
        right_dom_path=str(payload["right_dom_path"]),
        image_space=str(payload["image_space"]),
        matcher_method=str(payload["matcher_method"]),
        requested_device=str(payload["requested_device"]),
        band=int(payload["band"]),
        created_at_utc=str(payload["created_at_utc"]),
        tasks=tuple(
            deep_match_task_record_from_payload(dict(record_payload))
            for record_payload in payload.get("tasks", [])
        ),
        metadata=dict(payload.get("metadata", {})),
    )


def write_deep_match_pair_manifest(
    manifest: DeepMatchPairManifest,
    *,
    output_path: str | Path | None = None,
) -> Path:
    """Write a pair manifest to disk and create its workspace directories."""

    workspace = resolve_deep_match_workspace(
        temp_root_dir=Path(manifest.workspace_root).parent,
        pair_id=manifest.pair_id,
    )
    ensure_deep_match_workspace(workspace)
    manifest_path = workspace.manifest_path if output_path is None else Path(output_path).expanduser().resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(deep_match_pair_manifest_to_payload(manifest), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def read_deep_match_pair_manifest(manifest_path: str | Path) -> DeepMatchPairManifest:
    """Read and deserialize a pair manifest from disk."""

    payload = json.loads(Path(manifest_path).expanduser().resolve().read_text(encoding="utf-8"))
    return deep_match_pair_manifest_from_payload(payload)


def write_deep_match_task_arrays(
    record: DeepMatchTaskRecord,
    *,
    left_image: np.ndarray,
    right_image: np.ndarray,
    left_mask: np.ndarray,
    right_mask: np.ndarray,
) -> dict[str, Path]:
    """Persist prepared tile arrays for later deep-learning execution."""

    artifact_paths = {
        "left_image": Path(record.left_image_path).expanduser().resolve(),
        "right_image": Path(record.right_image_path).expanduser().resolve(),
        "left_mask": Path(record.left_mask_path).expanduser().resolve(),
        "right_mask": Path(record.right_mask_path).expanduser().resolve(),
    }
    for path in artifact_paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    np.save(artifact_paths["left_image"], np.asarray(left_image))
    np.save(artifact_paths["right_image"], np.asarray(right_image))
    np.save(artifact_paths["left_mask"], np.asarray(left_mask))
    np.save(artifact_paths["right_mask"], np.asarray(right_mask))
    return artifact_paths


def read_deep_match_task_arrays(record: DeepMatchTaskRecord) -> dict[str, np.ndarray]:
    """Load persisted tile arrays for one deep-learning task record."""

    return {
        "left_image": np.load(Path(record.left_image_path).expanduser().resolve(), allow_pickle=False),
        "right_image": np.load(Path(record.right_image_path).expanduser().resolve(), allow_pickle=False),
        "left_mask": np.load(Path(record.left_mask_path).expanduser().resolve(), allow_pickle=False),
        "right_mask": np.load(Path(record.right_mask_path).expanduser().resolve(), allow_pickle=False),
    }


def write_deep_match_task_result(
    record: DeepMatchTaskRecord,
    *,
    left_points: np.ndarray,
    right_points: np.ndarray,
    scores: np.ndarray | None = None,
    status: str = "matched",
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Write one standardized deep-match task result NPZ file."""

    result_path = Path(record.result_path).expanduser().resolve()
    result_path.parent.mkdir(parents=True, exist_ok=True)
    left_array = np.asarray(left_points, dtype=np.float32).reshape(-1, 2)
    right_array = np.asarray(right_points, dtype=np.float32).reshape(-1, 2)
    pair_count = min(left_array.shape[0], right_array.shape[0])
    left_array = left_array[:pair_count]
    right_array = right_array[:pair_count]
    if scores is None:
        score_array = np.ones((pair_count,), dtype=np.float32)
    else:
        score_array = np.asarray(scores, dtype=np.float32).reshape(-1)[:pair_count]
        if score_array.shape[0] < pair_count:
            padded_scores = np.ones((pair_count,), dtype=np.float32)
            padded_scores[: score_array.shape[0]] = score_array
            score_array = padded_scores
    payload_metadata = {
        "status": str(status),
        "match_count": int(pair_count),
        **dict(metadata or {}),
    }
    np.savez_compressed(
        result_path,
        left_points=left_array,
        right_points=right_array,
        scores=score_array,
        metadata_json=np.asarray(json.dumps(payload_metadata, ensure_ascii=False)),
    )
    return result_path


def read_deep_match_task_result(record_or_path: DeepMatchTaskRecord | str | Path) -> dict[str, Any]:
    """Read one standardized deep-match task result NPZ file."""

    result_path = (
        Path(record_or_path.result_path)
        if isinstance(record_or_path, DeepMatchTaskRecord)
        else Path(record_or_path)
    ).expanduser().resolve()
    with np.load(result_path, allow_pickle=False) as data:
        metadata_raw = data.get("metadata_json")
        metadata = json.loads(str(metadata_raw.item())) if metadata_raw is not None else {}
        return {
            "left_points": np.asarray(data["left_points"], dtype=np.float32).reshape(-1, 2),
            "right_points": np.asarray(data["right_points"], dtype=np.float32).reshape(-1, 2),
            "scores": np.asarray(data["scores"], dtype=np.float32).reshape(-1),
            "metadata": metadata,
            "result_path": str(result_path),
        }


__all__ = [
    "DEFAULT_DEEP_MATCH_TEMP_ROOT_NAME",
    "DEEP_MATCH_MANIFEST_FORMAT_VERSION",
    "DeepMatchPairManifest",
    "DeepMatchTaskRecord",
    "DeepMatchWorkspacePaths",
    "build_deep_match_pair_manifest",
    "build_deep_match_task_record",
    "deep_match_pair_manifest_from_payload",
    "deep_match_pair_manifest_to_payload",
    "deep_match_task_record_from_payload",
    "deep_match_task_record_to_payload",
    "default_deep_match_pair_id",
    "ensure_deep_match_workspace",
    "read_deep_match_task_arrays",
    "read_deep_match_task_result",
    "read_deep_match_pair_manifest",
    "resolve_deep_match_workspace",
    "write_deep_match_task_arrays",
    "write_deep_match_task_result",
    "write_deep_match_pair_manifest",
]
