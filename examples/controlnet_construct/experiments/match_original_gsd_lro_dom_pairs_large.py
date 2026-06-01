"""Batch-match original-GSD LRO NAC DOM pairs through the tiled large-image pipeline.

Author: Geng Xun
Created: 2026-05-29
Updated: 2026-05-30  Geng Xun added incomplete-output cleanup for resumable
    original-GSD DOM matching.
Updated: 2026-05-29  Geng Xun added a selected-pair DOM batch orchestrator
    that delegates large CUBE matching to run_image_match_batch_example.sh.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTROLNET_DIR = REPO_ROOT / "examples" / "controlnet_construct"
DEFAULT_DATA_ROOT = Path("/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S")
DEFAULT_ORIGINAL_GSD_ROOT = DEFAULT_DATA_ROOT / "texture_lighting_pair_selection" / "original_gsd"
DEFAULT_PAIR_PATHS = DEFAULT_ORIGINAL_GSD_ROOT / "selected_pair_original_gsd_paths.csv"
DEFAULT_OUTPUT_ROOT = DEFAULT_ORIGINAL_GSD_ROOT / "large_dom_match"
DEFAULT_PYTHON = Path("/home/gengxun/miniconda3/envs/asp360_new/bin/python")
DEFAULT_BATCH_RUNNER = CONTROLNET_DIR / "run_image_match_batch_example.sh"
DEFAULT_PRESET_DIR = CONTROLNET_DIR / "presets"
DEFAULT_METHODS = (
    "sift_flann",
    "adaptive",
    "loftr",
    "superpoint_lightglue",
    "sift_lightglue",
)


@dataclass(frozen=True, slots=True)
class PairSidePath:
    pair_folder: str
    side: str
    product_id: str
    echo_cal_cube: Path
    dom_cube: Path


@dataclass(frozen=True, slots=True)
class PairPaths:
    pair_folder: str
    left: PairSidePath
    right: PairSidePath


@dataclass(frozen=True, slots=True)
class MethodSpec:
    name: str
    display_name: str
    matcher_method: str | None = None
    match_preset_path: Path | None = None
    adaptive_routing: bool = False
    config_path: Path | None = None


@dataclass(frozen=True, slots=True)
class MethodRunSummary:
    method: str
    display_name: str
    work_dir: str
    pair_count: int
    command: list[str]
    return_code: int | None
    status: str
    metadata_count: int
    failed_metadata_count: int
    summary_csv: str
    summary_json: str


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _read_pair_paths(pair_paths_csv: Path) -> list[PairPaths]:
    if not pair_paths_csv.exists():
        raise FileNotFoundError(f"pair path CSV not found: {pair_paths_csv}")

    grouped: dict[str, dict[str, PairSidePath]] = {}
    with pair_paths_csv.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            pair_folder = str(row["pair_folder"])
            side = str(row["side"]).strip().lower()
            if side not in {"left", "right"}:
                raise ValueError(f"Unsupported side {side!r} in {pair_paths_csv}")
            entry = PairSidePath(
                pair_folder=pair_folder,
                side=side,
                product_id=str(row["product_id"]),
                echo_cal_cube=Path(row["echo_cal_cube"]),
                dom_cube=Path(row["dom_cube"]),
            )
            grouped.setdefault(pair_folder, {})[side] = entry

    pairs: list[PairPaths] = []
    for pair_folder in sorted(grouped):
        sides = grouped[pair_folder]
        if "left" not in sides or "right" not in sides:
            raise ValueError(f"Pair {pair_folder!r} is missing a left or right side in {pair_paths_csv}")
        for side_name, side_path in sides.items():
            if not side_path.echo_cal_cube.exists():
                raise FileNotFoundError(f"Missing {side_name} echo-cal cube: {side_path.echo_cal_cube}")
            if not side_path.dom_cube.exists():
                raise FileNotFoundError(f"Missing {side_name} DOM cube: {side_path.dom_cube}")
        pairs.append(PairPaths(pair_folder=pair_folder, left=sides["left"], right=sides["right"]))
    return pairs


def _method_specs(args: argparse.Namespace) -> dict[str, MethodSpec]:
    preset_dir = args.preset_dir.expanduser().resolve()
    adaptive_config = args.output_root.expanduser().resolve() / "adaptive_image_match_config.json"
    adaptive_config.parent.mkdir(parents=True, exist_ok=True)
    adaptive_payload = {
        "ImageMatch": {
            "adaptive_routing_deep_presets": {
                "lightglue": str((preset_dir / "lightglue_official_superpoint.json").resolve()),
                "loftr": str((preset_dir / "loftr_default.json").resolve()),
            },
        }
    }
    adaptive_config.write_text(json.dumps(adaptive_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "sift_flann": MethodSpec(
            name="sift_flann",
            display_name="Classic SIFT+FLANN",
            match_preset_path=preset_dir / "classic_sift_flann.json",
            adaptive_routing=False,
        ),
        "adaptive": MethodSpec(
            name="adaptive",
            display_name="Adaptive routing",
            matcher_method="flann",
            adaptive_routing=True,
            config_path=adaptive_config,
        ),
        "loftr": MethodSpec(
            name="loftr",
            display_name="LoFTR",
            match_preset_path=preset_dir / "loftr_default.json",
            adaptive_routing=False,
        ),
        "superpoint_lightglue": MethodSpec(
            name="superpoint_lightglue",
            display_name="SuperPoint+LightGlue",
            match_preset_path=preset_dir / "lightglue_official_superpoint.json",
            adaptive_routing=False,
        ),
        "sift_lightglue": MethodSpec(
            name="sift_lightglue",
            display_name="SIFT+LightGlue",
            match_preset_path=preset_dir / "lightglue_official_sift.json",
            adaptive_routing=False,
        ),
    }


def _parse_methods(raw_methods: str, available: dict[str, MethodSpec]) -> list[MethodSpec]:
    normalized = [item.strip().lower() for item in raw_methods.split(",") if item.strip()]
    if not normalized or normalized == ["all"]:
        normalized = list(DEFAULT_METHODS)
    specs: list[MethodSpec] = []
    for method in normalized:
        if method == "sift+flann":
            method = "sift_flann"
        elif method == "superpoint+lightglue":
            method = "superpoint_lightglue"
        elif method == "sift+lightglue":
            method = "sift_lightglue"
        if method not in available:
            raise ValueError(f"Unsupported method {method!r}; expected one of: {', '.join(sorted(available))}, all")
        specs.append(available[method])
    return specs


def _write_method_lists(work_dir: Path, pairs: list[PairPaths]) -> dict[str, Path]:
    work_dir.mkdir(parents=True, exist_ok=True)
    original_list = work_dir / "original_images.lis"
    dom_list = work_dir / "doms.lis"
    pair_list = work_dir / "images_overlap.lis"
    pair_manifest = work_dir / "selected_pairs_for_matching.csv"

    dom_by_original: dict[str, str] = {}
    for pair in pairs:
        for side in (pair.left, pair.right):
            dom_by_original[str(side.echo_cal_cube)] = str(side.dom_cube)

    with original_list.open("w", encoding="utf-8") as original_stream, dom_list.open("w", encoding="utf-8") as dom_stream:
        for original_path in sorted(dom_by_original):
            original_stream.write(original_path + "\n")
            dom_stream.write(dom_by_original[original_path] + "\n")

    with pair_list.open("w", encoding="utf-8") as pair_stream:
        for pair in pairs:
            pair_stream.write(f"{pair.left.echo_cal_cube},{pair.right.echo_cal_cube}\n")

    with pair_manifest.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "pair_folder",
                "left_product_id",
                "right_product_id",
                "left_echo_cal_cube",
                "right_echo_cal_cube",
                "left_dom_cube",
                "right_dom_cube",
            ],
        )
        writer.writeheader()
        for pair in pairs:
            writer.writerow(
                {
                    "pair_folder": pair.pair_folder,
                    "left_product_id": pair.left.product_id,
                    "right_product_id": pair.right.product_id,
                    "left_echo_cal_cube": str(pair.left.echo_cal_cube),
                    "right_echo_cal_cube": str(pair.right.echo_cal_cube),
                    "left_dom_cube": str(pair.left.dom_cube),
                    "right_dom_cube": str(pair.right.dom_cube),
                }
            )

    return {
        "original_list": original_list,
        "dom_list": dom_list,
        "pair_list": pair_list,
        "pair_manifest": pair_manifest,
    }


def _pair_tag(pair: PairPaths) -> str:
    return f"{pair.left.echo_cal_cube.stem}__{pair.right.echo_cal_cube.stem}"


def _cleanup_incomplete_existing_outputs(method_dir: Path, pairs: list[PairPaths]) -> int:
    """Remove key-only partial outputs that would fool --skip-existing.

    The shell batch runner intentionally skips a pair when both key files exist.
    If a previous run was interrupted after key writing but before metadata JSON
    writing, that check can skip an incomplete result.  Treat metadata JSON as
    the completion marker for this experiment and delete only the pair's key
    files when metadata is absent or unreadable, allowing the pair to be rerun.
    """

    key_dir = method_dir / "dom_keys"
    metadata_dir = method_dir / "match_metadata"
    removed_count = 0
    for pair in pairs:
        tag = _pair_tag(pair)
        left_key = key_dir / f"{tag}_A.key"
        right_key = key_dir / f"{tag}_B.key"
        metadata_path = metadata_dir / f"{tag}.json"
        has_key_pair = left_key.exists() and right_key.exists()
        if not has_key_pair:
            continue

        metadata_complete = False
        if metadata_path.exists():
            try:
                json.loads(metadata_path.read_text(encoding="utf-8"))
                metadata_complete = True
            except json.JSONDecodeError:
                metadata_complete = False
        if metadata_complete:
            continue

        for key_path in (left_key, right_key):
            if key_path.exists():
                key_path.unlink()
                removed_count += 1
    return removed_count


def _build_batch_command(
    *,
    spec: MethodSpec,
    method_dir: Path,
    list_paths: dict[str, Path],
    args: argparse.Namespace,
) -> list[str]:
    command = [
        "bash",
        str(args.batch_runner.expanduser().resolve()),
        "--work-dir",
        str(method_dir),
        "--original-list",
        str(list_paths["original_list"]),
        "--dom-list",
        str(list_paths["dom_list"]),
        "--pair-list",
        str(list_paths["pair_list"]),
        "--output-key-dir",
        str(method_dir / "dom_keys"),
        "--metadata-dir",
        str(method_dir / "match_metadata"),
        "--match-viz-dir",
        str(method_dir / "match_viz"),
        "--python",
        str(args.python.expanduser().resolve()),
        "--use-parallel-cpu",
        "--num-worker-parallel-cpu",
        str(args.num_worker_parallel_cpu),
        "--opencv-num-threads",
        str(args.opencv_num_threads),
        "--valid-pixel-percent-threshold",
        str(args.valid_pixel_percent_threshold),
        "--invalid-pixel-radius",
        str(args.invalid_pixel_radius),
    ]
    if spec.config_path is not None:
        command.extend(["--config", str(spec.config_path)])
    if spec.match_preset_path is not None:
        command.extend(["--match-preset-path", str(spec.match_preset_path.resolve())])
    elif spec.matcher_method is not None:
        command.extend(["--matcher-method", spec.matcher_method])
    else:
        raise ValueError(f"Method {spec.name!r} has neither a preset nor a matcher method")

    if spec.adaptive_routing:
        command.append("--adaptive-routing")
        command.extend(["--adaptive-routing-profile", args.adaptive_routing_profile])
    else:
        command.append("--no-adaptive-routing")

    if args.skip_existing:
        command.append("--skip-existing")
    if args.enable_low_resolution_offset_estimation:
        command.append("--enable-low-resolution-offset-estimation")
        command.extend(["--low-resolution-level", str(args.low_resolution_level)])
    if args.deep_match_mode != "direct":
        command.extend(["--deep-match-mode", args.deep_match_mode])
        if args.deep_match_mode == "export":
            temp_root = args.deep_match_temp_root_dir or (method_dir / "deep_match_workspaces")
            command.extend(["--deep-match-temp-root-dir", str(temp_root)])
        elif args.deep_match_mode == "import":
            manifest_dir = args.deep_match_manifest_dir or (method_dir / "deep_match_workspaces")
            command.extend(["--deep-match-manifest-dir", str(manifest_dir)])
        manifest_summary = args.deep_match_manifest_summary or (method_dir / "deep_match_manifests.json")
        command.extend(["--deep-match-manifest-summary", str(manifest_summary)])
    command.append("--")
    command.extend(
        [
            "--omit-tile-details",
            "--memory-profile",
            args.memory_profile,
            "--max-image-dimension",
            str(args.max_image_dimension),
            "--sub-block-size-x",
            str(args.sub_block_size_x),
            "--sub-block-size-y",
            str(args.sub_block_size_y),
            "--overlap-size-x",
            str(args.overlap_size_x),
            "--overlap-size-y",
            str(args.overlap_size_y),
            "--result-output",
            str(method_dir / "image_match_result.json"),
        ]
    )
    if args.no_write_match_visualization:
        command.append("--no-write-match-visualization")
    if args.no_progress:
        command.append("--no-progress")
    command.extend(args.image_match_extra_args)
    return command


def _metadata_status(metadata: dict[str, Any]) -> str:
    if "status" in metadata:
        return str(metadata.get("status"))
    if "point_count" in metadata:
        return "matched" if int(metadata.get("point_count") or 0) > 0 else "matched_no_points"
    if "tile_summary" in metadata:
        return "matched"
    return "unknown"


def _summarize_method_outputs(method_dir: Path, method: MethodSpec, pair_count: int, command: list[str], return_code: int | None, status: str) -> MethodRunSummary:
    metadata_dir = method_dir / "match_metadata"
    rows: list[dict[str, Any]] = []
    for metadata_path in sorted(metadata_dir.glob("*.json")):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            rows.append(
                {
                    "method": method.name,
                    "metadata_path": str(metadata_path),
                    "status": "metadata_json_error",
                    "error": str(exc),
                }
            )
            continue
        rows.append(
            {
                "method": method.name,
                "display_name": method.display_name,
                "pair_tag": metadata_path.stem,
                "metadata_path": str(metadata_path),
                "status": _metadata_status(metadata),
                "point_count": metadata.get("point_count"),
                "left_dom": metadata.get("left_dom") or metadata.get("left_dom_path"),
                "right_dom": metadata.get("right_dom") or metadata.get("right_dom_path"),
                "matcher_method": metadata.get("matcher_method"),
                "resolved_matcher_method": metadata.get("resolved_matcher_method"),
                "adaptive_routing": json.dumps(metadata.get("adaptive_routing"), ensure_ascii=False, default=str)
                if metadata.get("adaptive_routing") is not None
                else "",
                "match_visualization": json.dumps(metadata.get("match_visualization"), ensure_ascii=False, default=str)
                if metadata.get("match_visualization") is not None
                else "",
                "error": metadata.get("error"),
            }
        )

    summary_json = method_dir / f"{method.name}_large_dom_match_summary.json"
    summary_csv = method_dir / f"{method.name}_large_dom_match_summary.csv"
    summary_json.write_text(json.dumps(rows, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    if rows:
        with summary_csv.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    else:
        summary_csv.write_text("method,pair_tag,status\n", encoding="utf-8")

    failed_count = sum(1 for row in rows if str(row.get("status", "")).lower() in {"failed", "metadata_json_error"})
    return MethodRunSummary(
        method=method.name,
        display_name=method.display_name,
        work_dir=str(method_dir),
        pair_count=pair_count,
        command=command,
        return_code=return_code,
        status=status,
        metadata_count=len(rows),
        failed_metadata_count=failed_count,
        summary_csv=str(summary_csv),
        summary_json=str(summary_json),
    )


def _write_global_summary(output_root: Path, summaries: list[MethodRunSummary]) -> None:
    rows = [asdict(summary) for summary in summaries]
    json_path = output_root / "large_dom_match_methods_summary.json"
    csv_path = output_root / "large_dom_match_methods_summary.csv"
    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    if rows:
        csv_rows = [
            {
                key: (json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value)
                for key, value in row.items()
            }
            for row in rows
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(csv_rows[0].keys()))
            writer.writeheader()
            writer.writerows(csv_rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run tiled large-image matching for original-GSD selected LRO NAC DOM pairs. "
            "This script prepares batch lists and delegates matching to run_image_match_batch_example.sh."
        )
    )
    parser.add_argument("--pair-paths-csv", type=Path, default=DEFAULT_PAIR_PATHS)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--methods", default="all", help="Comma-separated methods: sift_flann, adaptive, loftr, superpoint_lightglue, sift_lightglue, or all.")
    parser.add_argument("--max-pairs", type=int, default=None, help="Optional smoke-test limit after pair sorting.")
    parser.add_argument("--python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--batch-runner", type=Path, default=DEFAULT_BATCH_RUNNER)
    parser.add_argument("--preset-dir", type=Path, default=DEFAULT_PRESET_DIR)
    parser.add_argument("--num-worker-parallel-cpu", type=int, default=4, help="Tile worker process count forwarded to image_match.py.")
    parser.add_argument("--opencv-num-threads", type=int, default=1, help="OpenCV internal thread cap per tile worker.")
    parser.add_argument("--valid-pixel-percent-threshold", type=float, default=0.05)
    parser.add_argument("--invalid-pixel-radius", type=int, default=1)
    parser.add_argument("--adaptive-routing-profile", choices=("balanced", "strict", "relaxed", "fast"), default="balanced")
    parser.add_argument("--enable-low-resolution-offset-estimation", action="store_true", help="Prepare and use low-resolution DOMs for projected-offset estimation.")
    parser.add_argument("--low-resolution-level", type=int, default=3)
    parser.add_argument("--max-image-dimension", type=int, default=3000)
    parser.add_argument("--sub-block-size-x", type=int, default=1024)
    parser.add_argument("--sub-block-size-y", type=int, default=1024)
    parser.add_argument("--overlap-size-x", type=int, default=128)
    parser.add_argument("--overlap-size-y", type=int, default=128)
    parser.add_argument("--memory-profile", choices=("high-memory", "balanced", "low-memory"), default="low-memory")
    parser.add_argument("--deep-match-mode", choices=("direct", "export", "import"), default="direct", help="Deep matcher handoff mode forwarded to the batch runner.")
    parser.add_argument("--deep-match-temp-root-dir", type=Path, default=None, help="Workspace root for exported deep-match task manifests.")
    parser.add_argument("--deep-match-manifest-dir", type=Path, default=None, help="Workspace root containing deep-match manifests for import mode.")
    parser.add_argument("--deep-match-manifest-summary", type=Path, default=None, help="JSON summary of exported/imported deep-match manifests.")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue remaining methods if one method returns non-zero.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare files and print commands without running matching.")
    parser.add_argument("--no-write-match-visualization", action="store_true")
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument("image_match_extra_args", nargs=argparse.REMAINDER, help="Arguments after -- are forwarded to image_match.py through the batch runner.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.image_match_extra_args and args.image_match_extra_args[0] == "--":
        args.image_match_extra_args = args.image_match_extra_args[1:]

    output_root = args.output_root.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    pairs = _read_pair_paths(args.pair_paths_csv.expanduser().resolve())
    if args.max_pairs is not None:
        pairs = pairs[: max(0, int(args.max_pairs))]
    if not pairs:
        raise ValueError("No selected pairs available for matching.")

    available_methods = _method_specs(args)
    selected_methods = _parse_methods(args.methods, available_methods)
    print(f"[prepare] pairs={len(pairs)} output_root={output_root}", file=sys.stderr)
    print(f"[prepare] methods={', '.join(method.name for method in selected_methods)}", file=sys.stderr)
    print(
        f"[prepare] tile workers={args.num_worker_parallel_cpu} opencv threads={args.opencv_num_threads}",
        file=sys.stderr,
    )

    run_summaries: list[MethodRunSummary] = []
    for method in selected_methods:
        method_dir = output_root / method.name
        list_paths = _write_method_lists(method_dir, pairs)
        if args.skip_existing:
            removed_count = _cleanup_incomplete_existing_outputs(method_dir, pairs)
            if removed_count:
                print(
                    f"[resume] {method.name}: removed {removed_count} key file(s) without complete metadata",
                    file=sys.stderr,
                )
        command = _build_batch_command(spec=method, method_dir=method_dir, list_paths=list_paths, args=args)
        command_log = method_dir / "command.json"
        command_log.write_text(json.dumps(command, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[method] {method.name}: {_repo_relative(method_dir)}", file=sys.stderr)
        print("[command] " + " ".join(json.dumps(part) for part in command), file=sys.stderr)
        if args.dry_run:
            run_summaries.append(
                _summarize_method_outputs(
                    method_dir,
                    method,
                    len(pairs),
                    command,
                    return_code=None,
                    status="dry_run",
                )
            )
            continue

        completed = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
        status = "completed" if completed.returncode == 0 else "failed"
        run_summaries.append(
            _summarize_method_outputs(
                method_dir,
                method,
                len(pairs),
                command,
                return_code=completed.returncode,
                status=status,
            )
        )
        if completed.returncode != 0 and not args.continue_on_error:
            _write_global_summary(output_root, run_summaries)
            return completed.returncode

    _write_global_summary(output_root, run_summaries)
    print(json.dumps([asdict(summary) for summary in run_summaries], indent=2, ensure_ascii=False), file=sys.stdout)
    return 0 if all(summary.status in {"completed", "dry_run"} for summary in run_summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
