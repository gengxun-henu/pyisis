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
    from .coordinate_metadata import PAIR_PREPARATION_COORDINATE_FIELD_BASES, annotate_coordinate_payload
    from .listing import read_path_list
    from .runtime import bootstrap_runtime_environment


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

    该结构不仅包含左右裁剪窗口，还明确记录：
    - 原始投影重叠范围；
    - 扩张后的请求范围；
    - 最终可共享的窗口尺寸；
    - GSD 差异与是否可以进入匹配阶段。
    This structure stores not only the left/right crop windows but also:
    - the raw projected overlap extent;
    - the expanded requested extent;
    - the final shared window size;
    - the GSD difference and whether the pair is ready for matching.
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
    """记录单幅 DOM 在 GSD 统一过程中的决策结果。

    Record the normalization decision for one DOM during GSD harmonization.

    它既可作为执行日志，也可作为 dry-run 计划输出：调用方能看出某幅 DOM
    是否被重采样、目标分辨率是多少，以及若执行时将调用什么 `gdal_translate` 命令。
    It works both as an execution log and as a dry-run plan: callers can inspect
    whether a DOM was resampled, what the target resolution is, and which
    `gdal_translate` command would be executed.
    """
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
    """把列表条目解析成绝对路径。

    Resolve one list entry into an absolute path.

    输入列表允许混用绝对路径和相对路径；相对路径按列表文件所在目录解释，
    这样 `.lis` 文件在移动工作目录后仍保持稳定语义。
    The list may mix absolute and relative paths; relative paths are interpreted
    against the list file's directory so the `.lis` file keeps stable semantics
    across working directories.
    """
    path = Path(entry)
    if path.is_absolute():
        return path
    return (base_directory / path).resolve()


def _write_lines(file_path: str | Path, lines: list[str]) -> None:
    """按 UTF-8 写出文本行，并保证文件以换行结尾。

    Write text lines as UTF-8 and ensure the file ends with a trailing newline.
    """
    Path(file_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_dom_projection_info(cube_path: str | Path) -> DomProjectionInfo:
    """读取 DOM 的投影范围、尺寸与分辨率信息。

    Read the DOM projection extent, image size, and resolution metadata.
    """
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
    """生成影像 GSD 清单，并将结果写入文本报告。

    Build an image GSD inventory and write the results to a text report.
    """
    infos = [read_dom_projection_info(resolved_path) for _, resolved_path in entries]
    report_lines = [f"{display_entry}\t{info.resolution:.12f}" for (display_entry, _), info in zip(entries, infos, strict=True)]
    _write_lines(output_path, report_lines)
    return infos


def _relative_difference(resolution: float, target_resolution: float) -> float:
    """计算分辨率相对差值，用于判断是否超出容差。

    Compute the relative resolution difference used for tolerance checks.
    """
    if target_resolution <= 0.0:
        raise ValueError("target_resolution must be positive.")
    return abs(resolution - target_resolution) / target_resolution


def _format_scaled_output_path(source_entry: str, source_path: str, output_directory: Path, index: int, target_resolution: float) -> Path:
    """为重采样后的 DOM 生成稳定、可读的输出路径。

    Generate a stable and readable output path for a resampled DOM.

    文件名中嵌入序号、原始 stem 和目标 GSD，便于从产物反向追踪其来源与缩放目标。
    The filename embeds the sequence index, original stem, and target GSD so the
    output remains traceable back to its source and scaling target.
    """
    suffix = Path(source_path).suffix or ".cub"
    safe_resolution = f"{target_resolution:.6f}".replace(".", "p")
    stem = Path(source_entry).stem or Path(source_path).stem
    return output_directory / f"{index:03d}_{stem}_gsd{safe_resolution}{suffix}"


def _display_path_for_output(output_path: Path, *, output_list_path: Path, source_entry: str) -> str:
    """决定写回输出列表时应使用绝对路径还是相对路径。

    Decide whether the output list should store an absolute or relative path.

    如果输入条目本来是绝对路径，则保持绝对路径；否则尽量写成相对 `output_list`
    的路径，减少列表在不同机器间迁移时的路径噪声。
    If the source entry was absolute, keep the output absolute; otherwise prefer
    a path relative to `output_list` to reduce machine-specific path noise.
    """
    source_entry_path = Path(source_entry)
    if source_entry_path.is_absolute():
        return str(output_path)
    return os.path.relpath(output_path, start=output_list_path.parent)


def _run_gdal_translate(command: list[str]) -> None:
    """运行 `gdal_translate`，并把失败交给 `subprocess` 异常上抛。

    Execute `gdal_translate` and let `subprocess` raise on failure.
    """
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
    """按目标 GSD 统一 DOM 列表，并在需要时生成重采样输出。

    Normalize a DOM list to a target GSD and optionally create resampled outputs when needed.

    这个流程主要面向匹配前预处理：当左右 DOM 的 GSD 差异过大时，后续特征提取和窗口
    对齐更容易受尺度不一致影响。因此这里先统计每幅 DOM 的分辨率，再按统一目标 GSD
    生成新的列表与可选的重采样产物。
    This workflow is primarily intended for pre-matching preparation: when left
    and right DOMs differ too much in GSD, downstream feature extraction and
    window alignment become more sensitive to scale mismatch. The function first
    inventories the resolution of each DOM, then writes a normalized list and,
    when needed, resampled outputs at a shared target GSD.
    """
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
        # 这里以相对差值而非绝对差值做判定，能让同一套容差对不同量级的 GSD 更稳健。
        # Relative difference is used instead of absolute difference so the same
        # tolerance behaves more consistently across different GSD scales.
        difference = _relative_difference(info.resolution, target)
        needs_scaling = difference > tolerance_ratio
        command: tuple[str, ...] | None = None

        if needs_scaling:
            output_dir.mkdir(parents=True, exist_ok=True)
            scaled_output = _format_scaled_output_path(display_entry, resolved_path, output_dir, index, target)
            # `-tr target target` 明确把输出像元大小固定到目标 GSD；重采样方法默认
            # 用 bilinear，适合连续 DOM 灰度影像，调用方也可以按任务改成其他方法。
            # `-tr target target` explicitly fixes the output pixel size to the
            # target GSD. Bilinear is the default because it is usually suitable
            # for continuous-tone DOM imagery, but callers can override it.
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
            # 当差值仍在容差内时，直接复用原始 DOM，避免不必要的插值与 I/O 开销。
            # If the difference stays within tolerance, reuse the original DOM to
            # avoid unnecessary interpolation and extra I/O.
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
    """计算两幅 DOM 在投影坐标系中的相交边界框。

    Compute the intersection bounding box of two DOMs in projected coordinates.
    """
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
    """把投影坐标范围反算成某幅 DOM 上的图像裁剪窗口。

    Convert a projected-coordinate extent back into an image crop window on one DOM.

    这是从“地图坐标”回到“像素窗口”的关键步骤：先把请求范围裁到当前影像的有效投影边界内，
    再通过投影对象把四角反算成 world/image 坐标，最后生成 ISIS 兼容的 sample/line 窗口。
    This is the key step that moves from map coordinates back to pixel windows:
    it first clips the requested extent to the image's valid projected bounds,
    then back-projects the four corners through the projection object, and
    finally builds an ISIS-compatible sample/line window.
    """
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
        # 用四个投影角点回推像素位置，是为了把“共享地图范围”转换成该影像自己的像素框。
        # Back-projecting the four projected corners converts the shared map
        # extent into the pixel-space footprint of this specific image.
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

        # 这里用 floor/ceil 包住极值，目的是保守地覆盖整个请求区域，而不是冒险裁得过紧。
        # floor/ceil are used to conservatively cover the full requested region
        # instead of risking an overly tight crop.
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
    """为一对 DOM 计算可用于匹配的共享投影重叠裁剪窗口。

    Compute shared projected-overlap crop windows for a DOM pair that can be used for matching.

    该函数服务于“先在投影空间找公共区域，再各自裁图”的准备策略：
    1. 读取左右 DOM 的投影范围与分辨率；
    2. 计算真实重叠区；
    3. 按较粗 GSD 扩张一圈上下文像素；
    4. 将扩张后的投影范围各自映射回左右影像窗口；
    5. 判断共享窗口是否足够大，能够支撑后续 matching。

    This function implements a "find overlap in projected space first, then crop
    each image" strategy:
    1. read projected extents and resolutions for the left/right DOMs;
    2. compute the true overlap region;
    3. expand it by a context margin measured using the coarser GSD;
    4. map the expanded projected region back into per-image windows;
    5. check whether the shared usable area is large enough for matching.
    """
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
        # 没有投影重叠时直接返回结构化“跳过”结果，方便批处理阶段统一汇总，
        # 而不是把这种常见场景当成硬错误中断整个任务。
        # If there is no projected overlap, return a structured "skipped" result
        # instead of treating this common situation as a hard pipeline error.
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
    # 扩张距离按较粗分辨率换算，能保证两侧都至少拿到 expand_pixels 数量级的上下文区域。
    # The expansion distance uses the coarser resolution so both sides receive at
    # least roughly expand_pixels worth of contextual margin.
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
    # 共享宽高取两侧最小值，因为后续匹配若需要对齐窗口尺寸，真正可共同使用的区域
    # 不能超过较小的那一边。
    # The shared size uses the smaller side because any downstream matching step
    # that expects aligned windows cannot rely on area beyond the smaller crop.
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
    """将 DOM 对准备结果写出为带坐标字段说明的 JSON 元数据。

    Write DOM-pair preparation results as JSON metadata annotated with coordinate field semantics.

    写出前会补充字段坐标基准说明，避免后续流程混淆 0-based offset 与 ISIS 1-based
    sample/line 字段。
    Before writing, the payload is annotated with field-base semantics so later
    steps do not confuse 0-based offsets with ISIS 1-based sample/line fields.
    """
    payload = annotate_coordinate_payload(
        asdict(metadata) if isinstance(metadata, PairPreparationMetadata) else dict(metadata),
        context="dom_pair_preparation_metadata",
        field_bases=PAIR_PREPARATION_COORDINATE_FIELD_BASES,
    )
    Path(metadata_path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器，用于 DOM GSD 统一流程。

    Build the command-line argument parser for the DOM GSD normalization workflow.
    """
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
    """运行命令行入口，执行 DOM 列表 GSD 统一并输出结果摘要。

    Run the CLI entry point to normalize a DOM list and print the result summary.
    """
    parser = build_argument_parser()
    args = parser.parse_args()
    input_list = Path(args.input_list)
    base_directory = input_list.parent
    # 这里保留“显示路径 + 解析后绝对路径”的二元组：前者用于写回列表时尽量保持原始风格，
    # 后者用于实际访问磁盘与调用 GDAL / ISIS。
    # Keep both the display path and the resolved absolute path: the former helps
    # preserve the original list style when writing outputs, while the latter is
    # used for actual filesystem access and GDAL / ISIS operations.
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
