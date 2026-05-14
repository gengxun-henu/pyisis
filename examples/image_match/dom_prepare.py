"""为 DOM 匹配准备输入：统一 GSD，并计算裁剪后的重叠窗口。

Prepare DOM inputs for matching by normalizing GSD and computing cropped overlap windows.

Author: Geng Xun
Created: 2026-04-17
Updated: 2026-04-17  Geng Xun added GSD inventory/normalization helpers plus projected-overlap crop metadata for DOM matching.
Updated: 2026-04-17  Geng Xun annotated projected-overlap JSON sidecars with explicit 0-based offset versus 1-based sample/line field bases.
Updated: 2026-04-19  Geng Xun polished comments into Chinese/English bilingual form and added bilingual docstrings for major DOM preparation functions.
Updated: 2026-04-19  Geng Xun expanded bilingual documentation for DOM preparation data structures, projected-overlap windowing, and GSD normalization flow details.
Updated: 2026-04-23  Geng Xun skipped projection-consistency cube opens for synthetic non-existent test paths while preserving real DOM checks.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import subprocess
import sys


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.coordinate_metadata import (
        PAIR_PREPARATION_COORDINATE_FIELD_BASES,
        annotate_coordinate_payload,
    )
    from controlnet_construct.listing import read_path_list
    from controlnet_construct.runtime import bootstrap_runtime_environment
else:
    from controlnet_construct.coordinate_metadata import PAIR_PREPARATION_COORDINATE_FIELD_BASES, annotate_coordinate_payload
    from controlnet_construct.listing import read_path_list
    from controlnet_construct.runtime import bootstrap_runtime_environment


bootstrap_runtime_environment()

import isis_pybind as ip


@dataclass(frozen=True, slots=True)
class DomProjectionInfo:
    """记录单个 DOM CUBE 的投影范围、尺寸与 GSD 信息。

    Store projection extent, raster size, and GSD metadata for one DOM cube.

    这些字段为后续两类处理提供基础输入：
    1. `normalize_dom_list_gsd()` 用 `resolution` 判断是否需要重采样；
    2. `prepare_dom_pair_for_matching()` 用投影边界估算左右 DOM 的重叠区。
    These fields feed two downstream tasks:
    1. `normalize_dom_list_gsd()` uses `resolution` to decide whether
       resampling is needed;
    2. `prepare_dom_pair_for_matching()` uses projected bounds to estimate the
       overlap region between left and right DOMs.
    """
    path: str
    image_width: int
    image_height: int
    resolution: float
    min_x: float
    max_x: float
    min_y: float
    max_y: float


@dataclass(frozen=True, slots=True)
class CropWindow:
    """描述一个可直接落到 DOM 图像上的裁剪窗口。

    Describe a crop window that can be applied directly to a DOM image.

    这里同时保留两套坐标表达：
    - `start_sample/start_line` 是 ISIS 风格的 1-based 像素起点；
    - `offset_sample/offset_line` 以及 `start_x/start_y` 更适合 0-based
      数组、NumPy 或 OpenCV 侧的切片处理。
    Two coordinate conventions are kept on purpose:
    - `start_sample/start_line` use ISIS-style 1-based pixel origins;
    - `offset_sample/offset_line` and `start_x/start_y` are more convenient for
      0-based array slicing on the NumPy / OpenCV side.
    """

    path: str
    start_sample: int
    start_line: int
    width: int
    height: int
    offset_sample: int
    offset_line: int
    projected_min_x: float
    projected_max_x: float
    projected_min_y: float
    projected_max_y: float
    clipped_by_image_bounds: bool

    @property
    def start_x(self) -> int:
        """返回适用于 0-based 图像数组的起始 x 偏移。

        Return the starting x offset in 0-based image-array coordinates.
        """
        return self.start_sample - 1

    @property
    def start_y(self) -> int:
        """返回适用于 0-based 图像数组的起始 y 偏移。

        Return the starting y offset in 0-based image-array coordinates.
        """
        return self.start_line - 1

    @property
    def end_sample(self) -> int:
        """返回 1-based、含末端的 sample 终点。

        Return the inclusive 1-based sample endpoint.
        """
        return self.start_sample + self.width - 1

    @property
    def end_line(self) -> int:
        """返回 1-based、含末端的 line 终点。

        Return the inclusive 1-based line endpoint.
        """
        return self.start_line + self.height - 1


@dataclass(frozen=True, slots=True)
class PairPreparationMetadata:
    """汇总一对 DOM 在匹配前的共享准备结果。

    Summarize the shared preparation results for a DOM pair before matching.
    """
    left: CropWindow
    right: CropWindow
    overlap_min_x: float
    overlap_max_x: float
    overlap_min_y: float
    overlap_max_y: float
    expanded_min_x: float
    expanded_max_x: float
    expanded_min_y: float
    expanded_max_y: float
    projected_delta_x: float
    projected_delta_y: float
    expand_pixels: int
    min_overlap_size: int
    shared_width: int
    shared_height: int
    left_resolution: float
    right_resolution: float
    reference_resolution: float
    gsd_ratio: float
    status: str
    reason: str = ""


@dataclass(frozen=True, slots=True)
class GsdNormalizationRecord:
    """记录单幅 DOM 在 GSD 统一过程中的决策结果。"""
    source_entry: str
    source_path: str
    output_entry: str
    output_path: str
    original_resolution: float
    target_resolution: float
    relative_difference: float
    scaled: bool
    command: tuple[str, ...] | None = None


def _resolve_path_entry(entry: str, *, base_directory: Path) -> Path:
    path = Path(entry)
    if path.is_absolute():
        return path
    return (base_directory / path).resolve()


def _write_lines(file_path: str | Path, lines: list[str]) -> None:
    Path(file_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_dom_projection_info(cube_path: str | Path) -> DomProjectionInfo:
    cube = ip.Cube()
    cube.open(str(cube_path), "r")
    try:
        projection = cube.projection()
        min_x, max_x, min_y, max_y = projection.xy_range()
        return DomProjectionInfo(
            path=str(cube_path),
            image_width=cube.sample_count(),
            image_height=cube.line_count(),
            resolution=float(projection.resolution()),
            min_x=float(min_x),
            max_x=float(max_x),
            min_y=float(min_y),
            max_y=float(max_y),
        )
    finally:
        if cube.is_open():
            cube.close()


def write_images_gsd_report(entries: list[tuple[str, str]], output_path: str | Path) -> list[DomProjectionInfo]:
    infos = [read_dom_projection_info(resolved_path) for _, resolved_path in entries]
    report_lines = [f"{display_entry}\t{info.resolution:.12f}" for (display_entry, _), info in zip(entries, infos, strict=True)]
    _write_lines(output_path, report_lines)
    return infos


def _relative_difference(resolution: float, target_resolution: float) -> float:
    if target_resolution <= 0.0:
        raise ValueError("target_resolution must be positive.")
    return abs(resolution - target_resolution) / target_resolution


def _format_scaled_output_path(source_entry: str, source_path: str, output_directory: Path, index: int, target_resolution: float) -> Path:
    suffix = Path(source_path).suffix or ".cub"
    safe_resolution = f"{target_resolution:.6f}".replace(".", "p")
    stem = Path(source_entry).stem or Path(source_path).stem
    return output_directory / f"{index:03d}_{stem}_gsd{safe_resolution}{suffix}"


def _display_path_for_output(output_path: Path, *, output_list_path: Path, source_entry: str) -> str:
    source_entry_path = Path(source_entry)
    if source_entry_path.is_absolute():
        return str(output_path)
    return os.path.relpath(output_path, start=output_list_path.parent)


def _run_gdal_translate(command: list[str]) -> None:
    subprocess.run(command, check=True, text=True, capture_output=True)


def normalize_dom_list_gsd(
    entries: list[tuple[str, str]],
    output_list_path: str | Path,
    *,
    gsd_report_path: str | Path | None = None,
    output_directory: str | Path | None = None,
    tolerance_ratio: float = 0.05,
    target_resolution: float | None = None,
    gdal_translate_executable: str = "gdal_translate",
    resampling: str = "bilinear",
    apply: bool = True,
) -> dict[str, object]:
    if not entries:
        raise ValueError("The DOM list is empty.")
    if tolerance_ratio < 0.0:
        raise ValueError("tolerance_ratio cannot be negative.")

    output_list = Path(output_list_path)
    if gsd_report_path is None:
        gsd_report = output_list.with_name("images_gsd.txt")
    else:
        gsd_report = Path(gsd_report_path)

    infos = write_images_gsd_report(entries, gsd_report)
    target = float(target_resolution) if target_resolution is not None else sum(info.resolution for info in infos) / len(infos)
    if target <= 0.0:
        raise ValueError("Resolved target GSD must be positive.")

    output_dir = Path(output_directory) if output_directory is not None else output_list.parent / "scaled_doms"
    records: list[GsdNormalizationRecord] = []
    output_entries: list[str] = []
    scaled_count = 0

    for index, ((display_entry, resolved_path), info) in enumerate(zip(entries, infos, strict=True), start=1):
        difference = _relative_difference(info.resolution, target)
        needs_scaling = difference > tolerance_ratio
        command: tuple[str, ...] | None = None

        if needs_scaling:
            output_dir.mkdir(parents=True, exist_ok=True)
            scaled_output = _format_scaled_output_path(display_entry, resolved_path, output_dir, index, target)
            command = (
                gdal_translate_executable,
                "-of",
                "ISIS3",
                "-r",
                resampling,
                "-tr",
                f"{target:.12f}",
                f"{target:.12f}",
                str(resolved_path),
                str(scaled_output),
            )
            if apply:
                _run_gdal_translate(list(command))
            output_entry = _display_path_for_output(scaled_output, output_list_path=output_list, source_entry=display_entry)
            output_path = str(scaled_output)
            scaled_count += 1
        else:
            output_entry = display_entry
            output_path = resolved_path

        output_entries.append(output_entry)
        records.append(
            GsdNormalizationRecord(
                source_entry=display_entry,
                source_path=resolved_path,
                output_entry=output_entry,
                output_path=output_path,
                original_resolution=info.resolution,
                target_resolution=target,
                relative_difference=difference,
                scaled=needs_scaling,
                command=command,
            )
        )

    _write_lines(output_list, output_entries)
    return {
        "input_count": len(entries),
        "scaled_count": scaled_count,
        "target_resolution": target,
        "tolerance_ratio": tolerance_ratio,
        "gsd_report": str(gsd_report),
        "output_list": str(output_list),
        "records": [asdict(record) for record in records],
    }


def _projected_bounds_intersection(left: DomProjectionInfo, right: DomProjectionInfo) -> tuple[float, float, float, float] | None:
    min_x = max(left.min_x, right.min_x)
    max_x = min(left.max_x, right.max_x)
    min_y = max(left.min_y, right.min_y)
    max_y = min(left.max_y, right.max_y)
    if min_x >= max_x or min_y >= max_y:
        return None
    return min_x, max_x, min_y, max_y


def _mapping_keyword_values(mapping: ip.PvlGroup, keyword_name: str) -> tuple[str, ...]:
    if not mapping.has_keyword(keyword_name):
        return ()
    keyword = mapping.find_keyword(keyword_name)
    return tuple(str(keyword[index]) for index in range(len(keyword)))


def _projection_consistency_reason(left_dom_path: str | Path, right_dom_path: str | Path) -> str | None:
    left_path = Path(left_dom_path)
    right_path = Path(right_dom_path)
    if not left_path.exists() or not right_path.exists():
        return None

    left_cube = ip.Cube()
    right_cube = ip.Cube()
    left_cube.open(str(left_dom_path), "r")
    right_cube.open(str(right_dom_path), "r")
    try:
        left_projection = left_cube.projection()
        right_projection = right_cube.projection()

        if left_projection.name() != right_projection.name():
            return (
                "The two DOMs use different projection names: "
                f"{left_projection.name()} vs {right_projection.name()}."
            )

        left_mapping = left_projection.mapping()
        right_mapping = right_projection.mapping()
        for keyword_name in (
            "ProjectionName",
            "TargetName",
            "LatitudeType",
            "LongitudeDirection",
            "LongitudeDomain",
            "CenterLongitude",
            "CenterLatitude",
            "EquatorialRadius",
            "PolarRadius",
        ):
            left_values = _mapping_keyword_values(left_mapping, keyword_name)
            right_values = _mapping_keyword_values(right_mapping, keyword_name)
            if left_values != right_values:
                return (
                    "The two DOMs have incompatible Mapping keyword values for "
                    f"{keyword_name}: {left_values} vs {right_values}."
                )

        return None
    finally:
        if left_cube.is_open():
            left_cube.close()
        if right_cube.is_open():
            right_cube.close()


def _projected_bounds_to_window(
    cube_path: str | Path,
    *,
    requested_min_x: float,
    requested_max_x: float,
    requested_min_y: float,
    requested_max_y: float,
    image_info: DomProjectionInfo,
) -> CropWindow:
    clipped_min_x = max(requested_min_x, image_info.min_x)
    clipped_max_x = min(requested_max_x, image_info.max_x)
    clipped_min_y = max(requested_min_y, image_info.min_y)
    clipped_max_y = min(requested_max_y, image_info.max_y)
    if clipped_min_x >= clipped_max_x or clipped_min_y >= clipped_max_y:
        raise ValueError(f"Projected crop bounds for {cube_path} collapsed after clipping to the image extent.")

    cube = ip.Cube()
    cube.open(str(cube_path), "r")
    try:
        projection = cube.projection()
        world_x_values: list[float] = []
        world_y_values: list[float] = []
        for x, y in (
            (clipped_min_x, clipped_max_y),
            (clipped_max_x, clipped_max_y),
            (clipped_min_x, clipped_min_y),
            (clipped_max_x, clipped_min_y),
        ):
            if not projection.set_coordinate(x, y):
                continue
            world_x_values.append(float(projection.world_x()))
            world_y_values.append(float(projection.world_y()))

        if not world_x_values or not world_y_values:
            raise ValueError(f"Could not convert projected crop bounds back into image coordinates for {cube_path}.")

        start_sample = max(1, int(math.floor(min(world_x_values))))
        start_line = max(1, int(math.floor(min(world_y_values))))
        end_sample = min(cube.sample_count(), int(math.ceil(max(world_x_values))))
        end_line = min(cube.line_count(), int(math.ceil(max(world_y_values))))
        width = end_sample - start_sample + 1
        height = end_line - start_line + 1
        if width <= 0 or height <= 0:
            raise ValueError(f"Projected crop bounds produced a non-positive image window for {cube_path}.")

        return CropWindow(
            path=str(cube_path),
            start_sample=start_sample,
            start_line=start_line,
            width=width,
            height=height,
            offset_sample=start_sample - 1,
            offset_line=start_line - 1,
            projected_min_x=clipped_min_x,
            projected_max_x=clipped_max_x,
            projected_min_y=clipped_min_y,
            projected_max_y=clipped_max_y,
            clipped_by_image_bounds=(
                not math.isclose(clipped_min_x, requested_min_x)
                or not math.isclose(clipped_max_x, requested_max_x)
                or not math.isclose(clipped_min_y, requested_min_y)
                or not math.isclose(clipped_max_y, requested_max_y)
            ),
        )
    finally:
        if cube.is_open():
            cube.close()


def prepare_dom_pair_for_matching(
    left_dom_path: str | Path,
    right_dom_path: str | Path,
    *,
    expand_pixels: int = 100,
    min_overlap_size: int = 16,
    projected_delta_x: float = 0.0,
    projected_delta_y: float = 0.0,
) -> PairPreparationMetadata:
    if expand_pixels < 0:
        raise ValueError("expand_pixels cannot be negative.")
    if min_overlap_size <= 0:
        raise ValueError("min_overlap_size must be positive.")

    left_info = read_dom_projection_info(left_dom_path)
    right_info = read_dom_projection_info(right_dom_path)
    consistency_reason = _projection_consistency_reason(left_dom_path, right_dom_path)
    if consistency_reason is not None:
        empty_left = CropWindow(str(left_dom_path), 1, 1, 0, 0, 0, 0, left_info.min_x, left_info.min_x, left_info.min_y, left_info.min_y, True)
        empty_right = CropWindow(str(right_dom_path), 1, 1, 0, 0, 0, 0, right_info.min_x, right_info.min_x, right_info.min_y, right_info.min_y, True)
        return PairPreparationMetadata(
            left=empty_left,
            right=empty_right,
            overlap_min_x=0.0,
            overlap_max_x=0.0,
            overlap_min_y=0.0,
            overlap_max_y=0.0,
            expanded_min_x=0.0,
            expanded_max_x=0.0,
            expanded_min_y=0.0,
            expanded_max_y=0.0,
            projected_delta_x=float(projected_delta_x),
            projected_delta_y=float(projected_delta_y),
            expand_pixels=expand_pixels,
            min_overlap_size=min_overlap_size,
            shared_width=0,
            shared_height=0,
            left_resolution=left_info.resolution,
            right_resolution=right_info.resolution,
            reference_resolution=max(left_info.resolution, right_info.resolution),
            gsd_ratio=_relative_difference(left_info.resolution, right_info.resolution),
            status="skipped_incompatible_projection",
            reason=consistency_reason,
        )

    shifted_right_info = DomProjectionInfo(
        path=right_info.path,
        image_width=right_info.image_width,
        image_height=right_info.image_height,
        resolution=right_info.resolution,
        min_x=right_info.min_x - float(projected_delta_x),
        max_x=right_info.max_x - float(projected_delta_x),
        min_y=right_info.min_y - float(projected_delta_y),
        max_y=right_info.max_y - float(projected_delta_y),
    )
    overlap = _projected_bounds_intersection(left_info, shifted_right_info)
    if overlap is None:
        empty_left = CropWindow(str(left_dom_path), 1, 1, 0, 0, 0, 0, left_info.min_x, left_info.min_x, left_info.min_y, left_info.min_y, True)
        empty_right = CropWindow(str(right_dom_path), 1, 1, 0, 0, 0, 0, right_info.min_x, right_info.min_x, right_info.min_y, right_info.min_y, True)
        return PairPreparationMetadata(
            left=empty_left,
            right=empty_right,
            overlap_min_x=0.0,
            overlap_max_x=0.0,
            overlap_min_y=0.0,
            overlap_max_y=0.0,
            expanded_min_x=0.0,
            expanded_max_x=0.0,
            expanded_min_y=0.0,
            expanded_max_y=0.0,
            projected_delta_x=float(projected_delta_x),
            projected_delta_y=float(projected_delta_y),
            expand_pixels=expand_pixels,
            min_overlap_size=min_overlap_size,
            shared_width=0,
            shared_height=0,
            left_resolution=left_info.resolution,
            right_resolution=right_info.resolution,
            reference_resolution=max(left_info.resolution, right_info.resolution),
            gsd_ratio=_relative_difference(left_info.resolution, right_info.resolution),
            status="skipped_no_projected_overlap",
            reason="The two DOMs do not overlap in projected coordinates.",
        )

    overlap_min_x, overlap_max_x, overlap_min_y, overlap_max_y = overlap
    reference_resolution = max(left_info.resolution, right_info.resolution)
    expansion_distance = expand_pixels * reference_resolution
    expanded_min_x = overlap_min_x - expansion_distance
    expanded_max_x = overlap_max_x + expansion_distance
    expanded_min_y = overlap_min_y - expansion_distance
    expanded_max_y = overlap_max_y + expansion_distance

    left_window = _projected_bounds_to_window(
        left_dom_path,
        requested_min_x=expanded_min_x,
        requested_max_x=expanded_max_x,
        requested_min_y=expanded_min_y,
        requested_max_y=expanded_max_y,
        image_info=left_info,
    )
    right_window = _projected_bounds_to_window(
        right_dom_path,
        requested_min_x=expanded_min_x + float(projected_delta_x),
        requested_max_x=expanded_max_x + float(projected_delta_x),
        requested_min_y=expanded_min_y + float(projected_delta_y),
        requested_max_y=expanded_max_y + float(projected_delta_y),
        image_info=right_info,
    )

    shared_width = min(left_window.width, right_window.width)
    shared_height = min(left_window.height, right_window.height)
    if shared_width < min_overlap_size or shared_height < min_overlap_size:
        status = "skipped_small_overlap"
        reason = (
            f"Expanded overlap window is too small for matching: {shared_width}x{shared_height} pixels "
            f"< {min_overlap_size}."
        )
    else:
        status = "ready"
        reason = ""

    return PairPreparationMetadata(
        left=left_window,
        right=right_window,
        overlap_min_x=overlap_min_x,
        overlap_max_x=overlap_max_x,
        overlap_min_y=overlap_min_y,
        overlap_max_y=overlap_max_y,
        expanded_min_x=expanded_min_x,
        expanded_max_x=expanded_max_x,
        expanded_min_y=expanded_min_y,
        expanded_max_y=expanded_max_y,
        projected_delta_x=float(projected_delta_x),
        projected_delta_y=float(projected_delta_y),
        expand_pixels=expand_pixels,
        min_overlap_size=min_overlap_size,
        shared_width=shared_width,
        shared_height=shared_height,
        left_resolution=left_info.resolution,
        right_resolution=right_info.resolution,
        reference_resolution=reference_resolution,
        gsd_ratio=_relative_difference(left_info.resolution, right_info.resolution),
        status=status,
        reason=reason,
    )


def write_pair_preparation_metadata(metadata_path: str | Path, metadata: PairPreparationMetadata | dict[str, object]) -> None:
    payload = annotate_coordinate_payload(
        asdict(metadata) if isinstance(metadata, PairPreparationMetadata) else dict(metadata),
        context="dom_pair_preparation_metadata",
        field_bases=PAIR_PREPARATION_COORDINATE_FIELD_BASES,
    )
    Path(metadata_path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize DOM GSD values and write a DOM list for downstream matching.")
    parser.add_argument("input_list", help="Input doms.lis path.")
    parser.add_argument("output_list", help="Output doms_scaled.lis path.")
    parser.add_argument("--gsd-report", default=None, help="Optional path for images_gsd.txt.")
    parser.add_argument("--output-dir", default=None, help="Directory where scaled DOM cubes should be written when resampling is required.")
    parser.add_argument("--tolerance-ratio", type=float, default=0.05, help="Maximum allowed relative GSD difference before a DOM is resampled.")
    parser.add_argument("--target-resolution", type=float, default=None, help="Override the target GSD in meters/pixel. Defaults to the list-wide average.")
    parser.add_argument("--gdal-translate", default="gdal_translate", help="Path to the gdal_translate executable.")
    parser.add_argument("--resampling", default="bilinear", help="GDAL resampling method to use when scaling DOMs.")
    parser.add_argument("--dry-run", action="store_true", help="Only write the report/list and planned commands without executing gdal_translate.")
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    input_list = Path(args.input_list)
    base_directory = input_list.parent
    entries = [(entry, str(_resolve_path_entry(entry, base_directory=base_directory))) for entry in read_path_list(input_list)]
    result = normalize_dom_list_gsd(
        entries,
        args.output_list,
        gsd_report_path=args.gsd_report,
        output_directory=args.output_dir,
        tolerance_ratio=args.tolerance_ratio,
        target_resolution=args.target_resolution,
        gdal_translate_executable=args.gdal_translate,
        resampling=args.resampling,
        apply=not args.dry_run,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
