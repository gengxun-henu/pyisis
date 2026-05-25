"""Run exported deep-match manifest tasks in a deep-learning environment.

Author: Geng Xun
Created: 2026-05-16
Updated: 2026-05-16  Geng Xun added a manifest executor that consumes image_match exports and writes standardized NPZ match results.
Updated: 2026-05-20  Geng Xun added manifest runtime-config preflight checks and adapter runtime-config handoff for cross-environment deep matching.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Callable

import numpy as np


def _bootstrap_examples_imports() -> Path:
    examples_root = Path(__file__).resolve().parents[1]
    root_str = str(examples_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return examples_root


EXAMPLES_ROOT = _bootstrap_examples_imports()

from image_match.deep_adapter import DeepMatcherAdapter
from image_match.deep_match_manifest import (
    DeepMatchTaskRecord,
    read_deep_match_pair_manifest,
    read_deep_match_task_arrays,
    write_deep_match_task_result,
)
from controlnet_construct.deep_match_config import (
    check_deep_match_dependencies,
    deep_match_runtime_config_from_payload,
)

SUPPORTED_DEVICES = ("auto", "cpu", "cuda")
MAX_MANIFEST_WORKERS = 64


def _parse_positive_int(value: str, option_name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{option_name} must be a positive integer.") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"{option_name} must be a positive integer.")
    return parsed


def _parse_num_workers(value: str) -> int:
    parsed = _parse_positive_int(value, "--num-workers")
    if parsed > MAX_MANIFEST_WORKERS:
        raise argparse.ArgumentTypeError(f"--num-workers must be between 1 and {MAX_MANIFEST_WORKERS}.")
    return parsed


def _parse_torch_num_threads(value: str) -> int:
    return _parse_positive_int(value, "--torch-num-threads")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _resolve_prefer_gpu(device: str) -> bool:
    normalized = str(device).strip().lower()
    if normalized not in SUPPORTED_DEVICES:
        raise ValueError(f"Unsupported --device {device!r}. Expected one of {SUPPORTED_DEVICES}.")
    if normalized == "cpu":
        return False
    if normalized == "auto":
        return True

    try:
        import torch
    except Exception as exc:
        raise RuntimeError("CUDA was requested, but torch is not importable in this environment.") from exc
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested, but torch.cuda.is_available() is false.")
    return True


def _keypoints_to_xy_array(keypoints: Any) -> np.ndarray:
    points = []
    for keypoint in keypoints or []:
        if hasattr(keypoint, "pt"):
            x_value, y_value = keypoint.pt
            points.append((float(x_value), float(y_value)))
            continue
        array = np.asarray(keypoint, dtype=np.float32).reshape(-1)
        if array.size >= 2:
            points.append((float(array[0]), float(array[1])))
    return np.asarray(points, dtype=np.float32).reshape(-1, 2)


def _deep_match_result_to_arrays(result: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    left_keypoints = _keypoints_to_xy_array(getattr(result, "left_keypoints", ()))
    right_keypoints = _keypoints_to_xy_array(getattr(result, "right_keypoints", ()))
    matches = list(getattr(result, "matches", ()) or ())
    if matches:
        left_points = []
        right_points = []
        scores = []
        for match in matches:
            query_index = int(getattr(match, "queryIdx", len(left_points)))
            train_index = int(getattr(match, "trainIdx", len(right_points)))
            if query_index < 0 or train_index < 0:
                continue
            if query_index >= left_keypoints.shape[0] or train_index >= right_keypoints.shape[0]:
                continue
            left_points.append(left_keypoints[query_index])
            right_points.append(right_keypoints[train_index])
            distance = float(getattr(match, "distance", 0.0))
            scores.append(max(0.0, 1.0 - distance))
        return (
            np.asarray(left_points, dtype=np.float32).reshape(-1, 2),
            np.asarray(right_points, dtype=np.float32).reshape(-1, 2),
            np.asarray(scores, dtype=np.float32).reshape(-1),
        )

    pair_count = min(left_keypoints.shape[0], right_keypoints.shape[0])
    return (
        left_keypoints[:pair_count].astype(np.float32, copy=False),
        right_keypoints[:pair_count].astype(np.float32, copy=False),
        np.ones((pair_count,), dtype=np.float32),
    )


def _as_invalid_mask(mask_value: np.ndarray) -> np.ndarray:
    mask = np.asarray(mask_value)
    if mask.dtype == np.bool_:
        return mask
    return mask == 0


def _valid_mask_keep(points: np.ndarray, invalid_mask: np.ndarray) -> np.ndarray:
    if points.size <= 0:
        return np.zeros((0,), dtype=bool)
    mask = _as_invalid_mask(invalid_mask)
    height, width = mask.shape[:2]
    rounded_x = np.rint(points[:, 0]).astype(np.int64, copy=False)
    rounded_y = np.rint(points[:, 1]).astype(np.int64, copy=False)
    inside = (rounded_x >= 0) & (rounded_x < width) & (rounded_y >= 0) & (rounded_y < height)
    keep = np.zeros((points.shape[0],), dtype=bool)
    keep[inside] = ~mask[rounded_y[inside], rounded_x[inside]]
    return keep


def _filter_points_by_invalid_masks(
    left_points: np.ndarray,
    right_points: np.ndarray,
    scores: np.ndarray,
    *,
    left_mask: np.ndarray,
    right_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    pair_count = min(left_points.shape[0], right_points.shape[0], scores.shape[0])
    left_points = left_points[:pair_count]
    right_points = right_points[:pair_count]
    scores = scores[:pair_count]
    if pair_count <= 0:
        return left_points, right_points, scores, 0

    keep = _valid_mask_keep(left_points, left_mask) & _valid_mask_keep(right_points, right_mask)
    removed_count = int(pair_count - int(keep.sum()))
    return left_points[keep], right_points[keep], scores[keep], removed_count


def _write_task_log(record: DeepMatchTaskRecord, payload: dict[str, Any]) -> Path:
    log_path = Path(record.log_path).expanduser().resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return log_path


def _runtime_config_from_manifest(manifest: Any, *, prefer_gpu: bool) -> Any | None:
    for record in manifest.tasks:
        if record.deep_match_runtime_config is not None:
            return deep_match_runtime_config_from_payload(
                record.deep_match_runtime_config,
                matcher_method=record.matcher_method or manifest.matcher_method,
                prefer_gpu=prefer_gpu,
            )
        tile_task_runtime_config = getattr(record.tile_task, "deep_match_runtime_config", None)
        if tile_task_runtime_config is not None:
            return deep_match_runtime_config_from_payload(
                tile_task_runtime_config,
                matcher_method=record.matcher_method or manifest.matcher_method,
                prefer_gpu=prefer_gpu,
            )
    metadata_runtime_config = manifest.metadata.get("deep_match_runtime_config")
    if metadata_runtime_config is None:
        return None
    return deep_match_runtime_config_from_payload(
        metadata_runtime_config,
        matcher_method=manifest.matcher_method,
        prefer_gpu=prefer_gpu,
    )


def _validate_runtime_config_matcher_method(manifest: Any, runtime_config: Any | None) -> None:
    if runtime_config is None:
        return
    manifest_method = str(manifest.matcher_method).strip().lower()
    runtime_method = str(runtime_config.matcher_method).strip().lower()
    if manifest_method != runtime_method:
        raise ValueError(
            f"Manifest matcher_method '{manifest_method}' conflicts with "
            f"runtime_config.matcher_method '{runtime_method}'."
        )


def run_manifest(
    manifest_path: str | Path,
    *,
    device: str = "auto",
    fail_fast: bool = False,
    skip_existing: bool = False,
    force_rerun: bool = False,
    num_workers: int = 1,
    torch_num_threads: int | None = None,
    adapter_factory: Callable[..., Any] = DeepMatcherAdapter,
) -> dict[str, Any]:
    """Execute every task in an exported deep-match manifest."""

    manifest = read_deep_match_pair_manifest(manifest_path)
    prefer_gpu = _resolve_prefer_gpu(device)
    runtime_config = _runtime_config_from_manifest(manifest, prefer_gpu=prefer_gpu)
    _validate_runtime_config_matcher_method(manifest, runtime_config)
    missing_dependencies = [] if runtime_config is None else check_deep_match_dependencies(runtime_config)
    if missing_dependencies:
        raise RuntimeError(
            f"Deep matcher preflight failed for '{runtime_config.matcher_method}' using Python {sys.executable}: "
            f"{'; '.join(missing_dependencies)}. Use the deep-learning conda environment or install the dependency."
        )
    adapter = adapter_factory(prefer_gpu=prefer_gpu, runtime_config=runtime_config)
    actual_device = str(getattr(adapter, "_device", "cuda" if prefer_gpu else "cpu"))

    task_summaries: list[dict[str, Any]] = []
    succeeded_count = 0
    failed_count = 0
    skipped_existing_count = 0

    for record in manifest.tasks:
        result_path = Path(record.result_path).expanduser().resolve()
        if skip_existing and result_path.exists():
            skipped_existing_count += 1
            task_summaries.append(
                {
                    "task_index": record.task_index,
                    "status": "skipped_existing",
                    "result_path": str(result_path),
                }
            )
            continue

        started_at = _utc_now_iso()
        try:
            arrays = read_deep_match_task_arrays(record)
            match_result = adapter.match_pair(
                matcher_method=manifest.matcher_method,
                left_image=arrays["left_image"],
                right_image=arrays["right_image"],
                left_mask=arrays["left_mask"],
                right_mask=arrays["right_mask"],
            )
            left_points, right_points, scores = _deep_match_result_to_arrays(match_result)
            raw_match_count = int(min(left_points.shape[0], right_points.shape[0], scores.shape[0]))
            left_points, right_points, scores, invalid_removed_count = _filter_points_by_invalid_masks(
                left_points,
                right_points,
                scores,
                left_mask=arrays["left_mask"],
                right_mask=arrays["right_mask"],
            )
            status = "matched" if len(scores) > 0 else "matched_no_points"
            write_deep_match_task_result(
                record,
                left_points=left_points,
                right_points=right_points,
                scores=scores,
                status=status,
                metadata={
                    "task_index": record.task_index,
                    "matcher_method": manifest.matcher_method,
                    "requested_device": device,
                    "actual_device": actual_device,
                    "raw_match_count": raw_match_count,
                    "invalid_mask_removed_count": invalid_removed_count,
                    "started_at_utc": started_at,
                    "finished_at_utc": _utc_now_iso(),
                },
            )
            task_summary = {
                "task_index": record.task_index,
                "status": status,
                "match_count": int(len(scores)),
                "raw_match_count": raw_match_count,
                "invalid_mask_removed_count": invalid_removed_count,
                "result_path": str(result_path),
                "log_path": record.log_path,
            }
            _write_task_log(record, task_summary)
            succeeded_count += 1
            task_summaries.append(task_summary)
        except Exception as exc:
            failed_count += 1
            error_summary = {
                "task_index": record.task_index,
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "result_path": str(result_path),
                "log_path": record.log_path,
                "started_at_utc": started_at,
                "finished_at_utc": _utc_now_iso(),
            }
            write_deep_match_task_result(
                record,
                left_points=np.empty((0, 2), dtype=np.float32),
                right_points=np.empty((0, 2), dtype=np.float32),
                scores=np.empty((0,), dtype=np.float32),
                status="failed",
                metadata=error_summary,
            )
            _write_task_log(record, error_summary)
            task_summaries.append(error_summary)
            if fail_fast:
                break

    overall_status = "completed"
    if failed_count and succeeded_count:
        overall_status = "completed_with_failures"
    elif failed_count:
        overall_status = "failed"

    return {
        "status": overall_status,
        "manifest_path": str(Path(manifest_path).expanduser().resolve()),
        "pair_id": manifest.pair_id,
        "matcher_method": manifest.matcher_method,
        "requested_device": device,
        "actual_device": actual_device,
        "task_count": len(manifest.tasks),
        "succeeded_task_count": succeeded_count,
        "failed_task_count": failed_count,
        "skipped_existing_task_count": skipped_existing_count,
        "started_at_utc": manifest.metadata.get("created_at_utc", manifest.created_at_utc),
        "finished_at_utc": _utc_now_iso(),
        "tasks": task_summaries,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run exported image_match deep-learning tasks from a manifest and write result NPZ files."
    )
    parser.add_argument("manifest", help="Path to the exported deep-match tasks.json manifest.")
    parser.add_argument(
        "--device",
        choices=SUPPORTED_DEVICES,
        default="auto",
        help="Execution device. 'auto' prefers CUDA when available and falls back to CPU.",
    )
    parser.add_argument(
        "--summary-output",
        default=None,
        help="Optional JSON path for the full execution summary. The summary is always printed to stdout.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first task failure instead of continuing through the manifest.",
    )
    existing_result_group = parser.add_mutually_exclusive_group()
    existing_result_group.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip tasks whose result NPZ file already exists.",
    )
    existing_result_group.add_argument(
        "--force-rerun",
        action="store_true",
        help="Recompute tasks even when result NPZ files already exist.",
    )
    parser.add_argument(
        "--num-workers",
        type=_parse_num_workers,
        default=1,
        help=f"Number of manifest tasks to execute concurrently. Reserved for future use. Range: 1-{MAX_MANIFEST_WORKERS}.",
    )
    parser.add_argument(
        "--torch-num-threads",
        type=_parse_torch_num_threads,
        default=None,
        help="Optional torch CPU thread count to use during manifest execution. Reserved for future use.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    summary = run_manifest(
        args.manifest,
        device=args.device,
        fail_fast=args.fail_fast,
        skip_existing=args.skip_existing,
        force_rerun=args.force_rerun,
        num_workers=args.num_workers,
        torch_num_threads=args.torch_num_threads,
    )
    if args.summary_output is not None:
        output_path = Path(args.summary_output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
