"""将 DOM 空间 tie points 转换为原始影像像素坐标。
Convert DOM-space tie points into original-image pixel coordinates.

该模块面向 ControlNet / `.key` tie-point 工作流，负责把 DOM CUBE 上的
sample/line 点先解析为地面坐标，再投影回原始 CUBE 的像素坐标。
This module targets the ControlNet / `.key` tie-point workflow and converts
sample/line positions measured on a DOM cube into ground coordinates first,
then projects them back into pixel coordinates of the original cube.

默认单景流程会用 `ProjectionFirst` 从 DOM CUBE 查询地理位置，再用
`CameraFirst` 将 latitude/longitude 投到原始 CUBE；双目流程还会保持左右
点对同步，避免单侧投影失败后破坏 stereo correspondence。
By default, the single-image workflow uses `ProjectionFirst` to query ground
location from the DOM cube, then uses `CameraFirst` to project
latitude/longitude into the original cube; the stereo workflow additionally
keeps left/right pairs synchronized so one-sided failures do not break stereo
correspondence.

Author: Geng Xun
Created: 2026-04-16
Updated: 2026-04-16  Geng Xun added an initial DOM-to-original coordinate conversion workflow using UniversalGroundMap with projection-first and camera-first backends.
Updated: 2026-04-16  Geng Xun strengthened failure classification, structured failure logs, and file-based semi-integration helpers for DOM-to-original conversion.
Updated: 2026-04-17  Geng Xun annotated dom2ori JSON sidecars with explicit 1-based sample/line field bases for failure payloads.
Updated: 2026-04-17  Geng Xun added pair-synchronized DOM-to-original conversion helpers so stereo correspondences stay aligned when one side fails projection.
Updated: 2026-04-19  Geng Xun polished existing comments into concise Chinese-first bilingual documentation and clarified the DOM CUBE to original CUBE projection flow.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from dataclasses import dataclass
import json
import logging
import math
from pathlib import Path
import sys


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.coordinate_metadata import DOM2ORI_COORDINATE_FIELD_BASES, annotate_coordinate_payload
    from controlnet_construct.keypoints import Keypoint, KeypointFile, read_key_file, write_key_file
    from controlnet_construct.runtime import bootstrap_runtime_environment
else:
    from .coordinate_metadata import DOM2ORI_COORDINATE_FIELD_BASES, annotate_coordinate_payload
    from .keypoints import Keypoint, KeypointFile, read_key_file, write_key_file
    from .runtime import bootstrap_runtime_environment


bootstrap_runtime_environment()

import isis_pybind as ip


@dataclass(frozen=True, slots=True)
class DomToOriginalFailure:
    index: int
    sample: float
    line: float
    reason: str
    category: str
    detail: str = ""
    latitude: float | None = None
    longitude: float | None = None
    projected_sample: float | None = None
    projected_line: float | None = None


@dataclass(frozen=True, slots=True)
class DomToOriginalSummary:
    input_count: int
    output_count: int
    failure_count: int
    failure_reasons: dict[str, int]
    failure_categories: dict[str, int]


def _is_point_in_bounds(sample: float, line: float, width: int, height: int) -> bool:
    # ISIS 的 sample/line 坐标以 1 为起点，且两端都按闭区间处理。
    # ISIS sample/line coordinates are 1-based and inclusive on both ends.
    # 这里故意拒绝 sample=0 或 line=0 这类 0-based 数组下标值。
    # This intentionally rejects 0-based array-style indices such as sample=0 or line=0.
    return 1.0 <= sample <= float(width) and 1.0 <= line <= float(height)


def _build_failure(
    index: int,
    sample: float,
    line: float,
    *,
    reason: str,
    category: str,
    detail: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
    projected_sample: float | None = None,
    projected_line: float | None = None,
) -> DomToOriginalFailure:
    return DomToOriginalFailure(
        index=index,
        sample=sample,
        line=line,
        reason=reason,
        category=category,
        detail=detail,
        latitude=latitude,
        longitude=longitude,
        projected_sample=projected_sample,
        projected_line=projected_line,
    )


def _append_failure(
    failures: list[DomToOriginalFailure],
    failure: DomToOriginalFailure,
    *,
    logger: logging.Logger | None,
) -> None:
    failures.append(failure)
    if logger is not None:
        logger.warning(
            "dom2ori point #%d failed [%s/%s] sample=%.6f line=%.6f detail=%s",
            failure.index,
            failure.category,
            failure.reason,
            failure.sample,
            failure.line,
            failure.detail or "-",
        )


def _build_summary(input_count: int, output_count: int, failures: list[DomToOriginalFailure]) -> DomToOriginalSummary:
    reason_counts = Counter(failure.reason for failure in failures)
    category_counts = Counter(failure.category for failure in failures)
    return DomToOriginalSummary(
        input_count=input_count,
        output_count=output_count,
        failure_count=len(failures),
        failure_reasons=dict(reason_counts),
        failure_categories=dict(category_counts),
    )


def _write_failure_log(failure_log_path: str | Path, payload: dict[str, object]) -> None:
    annotated_payload = annotate_coordinate_payload(
        payload,
        context="dom2ori_failure_log",
        field_bases=DOM2ORI_COORDINATE_FIELD_BASES,
    )
    Path(failure_log_path).write_text(json.dumps(annotated_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _convert_point_via_ground_functions(
    point: Keypoint,
    *,
    index: int,
    input_width: int,
    input_height: int,
    ground_lookup,
    image_project,
    output_width: int,
    output_height: int,
    validate_input_bounds: bool = True,
    require_output_in_bounds: bool = True,
) -> tuple[Keypoint | None, DomToOriginalFailure | None]:
    """将单个 DOM 点通过地面坐标桥接到原始影像坐标。

    Convert one DOM-space point into original-image coordinates through a
    ground-coordinate bridge.

    该函数是整个 DOM→ORI 几何转换链的最小执行单元：
    1. 先把 DOM `sample/line` 交给 `ground_lookup`，解算出对应的
       `latitude/longitude`；
    2. 再把该地面点交给 `image_project`，投影回原始 CUBE 的
       `sample/line`；
    3. 任一阶段失败时，不抛出流程级异常，而是返回结构化失败对象，便于上层批量统计、
       记录 failure log，并在 paired 模式下保持左右点对同步处理。

    This function is the smallest executable unit of the DOM→ORI geometry
    pipeline:
    1. It first sends DOM `sample/line` to `ground_lookup` to resolve
       `latitude/longitude`;
    2. It then sends that ground point to `image_project` to map it back to the
       original cube's `sample/line`;
    3. If any stage fails, it returns a structured failure object instead of
       raising a pipeline-level exception, so callers can batch statistics,
       persist failure logs, and preserve pair synchronization in paired mode.
    """
    # 输入边界检查是第一道“快速失败”门槛：如果 DOM 点本身已经超出声明的影像尺寸，
    # 后续 ground lookup 的失败就不再具有几何诊断意义。
    # Input validation is the first fast-fail gate: once the DOM point is already
    # outside declared image bounds, later lookup failures are no longer useful
    # for geometric diagnosis.
    if validate_input_bounds and not _is_point_in_bounds(
        point.sample,
        point.line,
        input_width,
        input_height,
    ):
        return None, _build_failure(
            index,
            point.sample,
            point.line,
            reason="dom_point_out_of_bounds",
            category="input_validation",
            detail=f"DOM keypoint lies outside declared image bounds {input_width}x{input_height}.",
        )

    # 第一阶段：DOM 像素 -> 地面坐标。这里把真实 ISIS / camera / projection 细节
    # 抽象到 ground_lookup 中，因此这个函数既能接真实 CUBE，也能接测试 stub。
    # Stage 1: DOM pixel -> ground coordinates. The concrete ISIS / camera /
    # projection logic is abstracted behind ground_lookup, so this function works
    # with both real cubes and lightweight test stubs.
    try:
        ground = ground_lookup(point.sample, point.line)
    except Exception as exc:  # pragma: no cover - 防御性分支，使用 stub 异常由单元测试覆盖。 / Defensive branch covered by unit tests with stub exceptions.
        return None, _build_failure(
            index,
            point.sample,
            point.line,
            reason="dom_lookup_exception",
            category="dom_lookup",
            detail=f"{type(exc).__name__}: {exc}",
        )

    if ground is None:
        return None, _build_failure(
            index,
            point.sample,
            point.line,
            reason="dom_lookup_failed",
            category="dom_lookup",
            detail="DOM cube could not resolve a valid ground location for this image coordinate.",
        )

    # 这里显式校验返回载荷形态，避免调用方误把其他对象、残缺 tuple 或 None-like
    # 结果混入几何流程，导致后续错误信息变得模糊。
    # We validate the returned payload shape explicitly so accidental non-tuple or
    # malformed values from the caller do not leak downstream as vague errors.
    try:
        latitude, longitude = ground
    except Exception as exc:
        return None, _build_failure(
            index,
            point.sample,
            point.line,
            reason="dom_lookup_invalid_payload",
            category="dom_lookup",
            detail=f"Unable to unpack ground tuple: {type(exc).__name__}: {exc}",
        )

    # 有限值检查能尽早拦截 NaN / inf。对坐标转换链来说，这类数值一旦流入后续投影，
    # 往往只会产生更难定位的连锁异常。
    # Finite-value checks stop NaN / inf early. In coordinate-conversion code,
    # letting them flow into the next projection stage usually causes noisier and
    # harder-to-diagnose downstream failures.
    if not (math.isfinite(latitude) and math.isfinite(longitude)):
        return None, _build_failure(
            index,
            point.sample,
            point.line,
            reason="dom_ground_not_finite",
            category="dom_lookup",
            detail="DOM ground lookup returned a non-finite latitude/longitude.",
            latitude=latitude,
            longitude=longitude,
        )

    # 第二阶段：地面坐标 -> 原始影像像素。这里的 image_project 通常对应
    # `set_universal_ground(latitude, longitude)` 之后读取 sample/line。
    # Stage 2: ground coordinates -> original-image pixel coordinates.
    # image_project usually corresponds to calling
    # `set_universal_ground(latitude, longitude)` and then reading sample/line.
    try:
        projected = image_project(latitude, longitude)
    except Exception as exc:  # pragma: no cover - 防御性分支，使用 stub 异常由单元测试覆盖。 / Defensive branch covered by unit tests with stub exceptions.
        return None, _build_failure(
            index,
            point.sample,
            point.line,
            reason="original_projection_exception",
            category="original_projection",
            detail=f"{type(exc).__name__}: {exc}",
            latitude=latitude,
            longitude=longitude,
        )

    if projected is None:
        return None, _build_failure(
            index,
            point.sample,
            point.line,
            reason="original_projection_failed",
            category="original_projection",
            detail="Original cube could not project the DOM ground point into image coordinates.",
            latitude=latitude,
            longitude=longitude,
        )

    # 和 ground_lookup 一样，这里也要把“调用失败”和“返回格式不合法”区分开，
    # 这样 failure category / reason 才能在日志与统计中保持可解释性。
    # As with ground_lookup, we distinguish projection failure from malformed
    # returned payloads so failure category / reason stay meaningful in logs and
    # summaries.
    try:
        projected_sample, projected_line = projected
    except Exception as exc:
        return None, _build_failure(
            index,
            point.sample,
            point.line,
            reason="original_projection_invalid_payload",
            category="original_projection",
            detail=f"Unable to unpack projected tuple: {type(exc).__name__}: {exc}",
            latitude=latitude,
            longitude=longitude,
        )

    # 这里检查输出像素是否为有限值；即便投影 API 没有显式报错，数值异常仍说明该点
    # 不能作为可靠的原图像素坐标继续参与后续匹配或 ControlNet 构建。
    # This checks whether the projected pixel is finite; even without an explicit
    # API failure, abnormal numeric output means the point is not reliable enough
    # for downstream matching or ControlNet construction.
    if not (math.isfinite(projected_sample) and math.isfinite(projected_line)):
        return None, _build_failure(
            index,
            point.sample,
            point.line,
            reason="original_pixel_not_finite",
            category="original_projection",
            detail="Original projection returned a non-finite sample/line.",
            latitude=latitude,
            longitude=longitude,
            projected_sample=projected_sample,
            projected_line=projected_line,
        )

    # 输出边界检查默认开启，用来保证返回的点既“可算出”，也“可落在有效原图范围内”。
    # 在某些调试场景下可以关闭该检查，以便观察越界投影的原始数值分布。
    # Output-bound validation is enabled by default so returned points are not
    # only computable but also usable inside the valid original-image extent. It
    # can be disabled in debugging scenarios when out-of-bounds projections are
    # still diagnostically valuable.
    if require_output_in_bounds and not _is_point_in_bounds(
        projected_sample,
        projected_line,
        output_width,
        output_height,
    ):
        return None, _build_failure(
            index,
            point.sample,
            point.line,
            reason="original_point_out_of_bounds",
            category="output_validation",
            detail=f"Projected point lies outside output image bounds {output_width}x{output_height}.",
            latitude=latitude,
            longitude=longitude,
            projected_sample=projected_sample,
            projected_line=projected_line,
        )

    # 成功路径只返回转换后的 Keypoint，不在这里附带额外状态；失败细节统一走
    # DomToOriginalFailure，能让上层循环保持简洁稳定。
    # The success path returns only the converted Keypoint. All failure detail is
    # centralized in DomToOriginalFailure so caller loops stay simple and stable.
    return Keypoint(projected_sample, projected_line), None


def _build_pair_drop_failure(
    index: int,
    point: Keypoint,
    *,
    other_side: str,
    other_failure: DomToOriginalFailure,
) -> DomToOriginalFailure:
    detail = (
        f"Dropped to preserve stereo pair alignment because the paired {other_side} point failed "
        f"[{other_failure.category}/{other_failure.reason}]"
    )
    if other_failure.detail:
        detail = f"{detail}: {other_failure.detail}"
    return _build_failure(
        index,
        point.sample,
        point.line,
        reason="paired_point_dropped",
        category="pair_synchronization",
        detail=detail,
    )


def convert_points_via_ground_functions(
    dom_key_file: KeypointFile,
    *,
    ground_lookup,
    image_project,
    output_width: int,
    output_height: int,
    logger: logging.Logger | None = None,
    validate_input_bounds: bool = True,
    require_output_in_bounds: bool = True,
) -> tuple[KeypointFile, list[DomToOriginalFailure], DomToOriginalSummary]:
    """使用注入的地面定位与影像投影回调转换点集。

    Convert points with injected ground-lookup and image-projection callables.

    该函数不直接依赖具体 CUBE 对象，而是把 DOM 端的 `sample/line -> latitude/longitude`
    和原图端的 `latitude/longitude -> sample/line` 过程抽象成可替换回调，便于单元测试、
    半集成验证以及不同几何后端的复用。
    This function does not depend on concrete cube objects directly. Instead, it
    abstracts the DOM-side `sample/line -> latitude/longitude` step and the
    original-image-side `latitude/longitude -> sample/line` step into replaceable
    callables for unit tests, semi-integration validation, and backend reuse.
    """
    output_points: list[Keypoint] = []
    failures: list[DomToOriginalFailure] = []

    for index, point in enumerate(dom_key_file.points, start=1):
        converted_point, failure = _convert_point_via_ground_functions(
            point,
            index=index,
            input_width=dom_key_file.image_width,
            input_height=dom_key_file.image_height,
            ground_lookup=ground_lookup,
            image_project=image_project,
            output_width=output_width,
            output_height=output_height,
            validate_input_bounds=validate_input_bounds,
            require_output_in_bounds=require_output_in_bounds,
        )
        if failure is not None:
            _append_failure(failures, failure, logger=logger)
            continue

        assert converted_point is not None
        output_points.append(converted_point)

    output_key_file = KeypointFile(output_width, output_height, tuple(output_points))
    summary = _build_summary(len(dom_key_file.points), len(output_points), failures)
    return output_key_file, failures, summary


def convert_point_pairs_via_ground_functions(
    left_dom_key_file: KeypointFile,
    right_dom_key_file: KeypointFile,
    *,
    left_ground_lookup,
    left_image_project,
    right_ground_lookup,
    right_image_project,
    left_output_width: int,
    left_output_height: int,
    right_output_width: int,
    right_output_height: int,
    logger: logging.Logger | None = None,
    validate_input_bounds: bool = True,
    require_output_in_bounds: bool = True,
) -> tuple[
    KeypointFile,
    KeypointFile,
    list[DomToOriginalFailure],
    list[DomToOriginalFailure],
    DomToOriginalSummary,
    DomToOriginalSummary,
]:
    """在保持左右点对同步的前提下转换双目 DOM tie points。

    Convert stereo DOM tie points while preserving left/right pair alignment.

    对双目匹配来说，左右 `.key` 文件中的第 `n` 个点必须继续表示同一对 correspondence。
    因此只要任一侧在 DOM 查询、地面坐标解算或原图投影阶段失败，两侧该点都会一起丢弃，
    以避免生成长度不一致或语义错位的输出点集。
    For stereo matching, point `n` in the left and right `.key` files must keep
    representing the same correspondence. Therefore, if either side fails during
    DOM lookup, ground resolution, or original-image projection, the pair is
    dropped on both sides so the outputs do not drift out of sync.
    """
    if len(left_dom_key_file.points) != len(right_dom_key_file.points):
        raise ValueError("Left and right DOM key files must contain the same number of points.")

    left_output_points: list[Keypoint] = []
    right_output_points: list[Keypoint] = []
    left_failures: list[DomToOriginalFailure] = []
    right_failures: list[DomToOriginalFailure] = []

    for index, (left_point, right_point) in enumerate(
        zip(left_dom_key_file.points, right_dom_key_file.points, strict=True),
        start=1,
    ):
        left_converted, left_failure = _convert_point_via_ground_functions(
            left_point,
            index=index,
            input_width=left_dom_key_file.image_width,
            input_height=left_dom_key_file.image_height,
            ground_lookup=left_ground_lookup,
            image_project=left_image_project,
            output_width=left_output_width,
            output_height=left_output_height,
            validate_input_bounds=validate_input_bounds,
            require_output_in_bounds=require_output_in_bounds,
        )
        right_converted, right_failure = _convert_point_via_ground_functions(
            right_point,
            index=index,
            input_width=right_dom_key_file.image_width,
            input_height=right_dom_key_file.image_height,
            ground_lookup=right_ground_lookup,
            image_project=right_image_project,
            output_width=right_output_width,
            output_height=right_output_height,
            validate_input_bounds=validate_input_bounds,
            require_output_in_bounds=require_output_in_bounds,
        )

        if left_failure is None and right_failure is None:
            if left_converted is None or right_converted is None:
                raise RuntimeError(
                    f"Internal invariant violated: no failure recorded but converted point is None at index {index}."
                )
            left_output_points.append(left_converted)
            right_output_points.append(right_converted)
            continue

        if left_failure is None:
            if right_failure is None:
                raise RuntimeError(f"Internal invariant violated: expected right_failure at index {index}.")
            left_failure = _build_pair_drop_failure(index, left_point, other_side="right", other_failure=right_failure)
        if right_failure is None:
            if left_failure is None:
                raise RuntimeError(f"Internal invariant violated: expected left_failure at index {index}.")
            right_failure = _build_pair_drop_failure(index, right_point, other_side="left", other_failure=left_failure)

        _append_failure(left_failures, left_failure, logger=logger)
        _append_failure(right_failures, right_failure, logger=logger)

    left_output_key_file = KeypointFile(left_output_width, left_output_height, tuple(left_output_points))
    right_output_key_file = KeypointFile(right_output_width, right_output_height, tuple(right_output_points))
    left_summary = _build_summary(len(left_dom_key_file.points), len(left_output_points), left_failures)
    right_summary = _build_summary(len(right_dom_key_file.points), len(right_output_points), right_failures)
    return (
        left_output_key_file,
        right_output_key_file,
        left_failures,
        right_failures,
        left_summary,
        right_summary,
    )


def convert_dom_key_file_via_ground_functions(
    dom_key_path: str | Path,
    output_key_path: str | Path,
    *,
    ground_lookup,
    image_project,
    output_width: int,
    output_height: int,
    failure_log_path: str | Path | None = None,
    logger: logging.Logger | None = None,
    validate_input_bounds: bool = True,
    require_output_in_bounds: bool = True,
) -> dict[str, object]:
    """通过注入的几何函数转换单个 `.key` 文件，并持久化结构化结果。

    Convert a `.key` file through injected geometry functions and persist structured results.

    当完整的 DOM / original 成对数据尚未就绪时，这个辅助函数适合做半集成测试、
    失败日志落盘以及备用接线验证。
    This helper is intended for semi-integration tests, persisted failure logs,
    and fallback wiring when a fully paired DOM/original dataset is not yet available.
    """
    dom_key_file = read_key_file(dom_key_path)
    output_key_file, failures, summary = convert_points_via_ground_functions(
        dom_key_file,
        ground_lookup=ground_lookup,
        image_project=image_project,
        output_width=output_width,
        output_height=output_height,
        logger=logger,
        validate_input_bounds=validate_input_bounds,
        require_output_in_bounds=require_output_in_bounds,
    )
    write_key_file(output_key_path, output_key_file)

    result = {
        "dom_key": str(dom_key_path),
        "output_key": str(output_key_path),
        "input_count": summary.input_count,
        "output_count": summary.output_count,
        "failure_count": summary.failure_count,
        "failure_reasons": summary.failure_reasons,
        "failure_categories": summary.failure_categories,
        "failures": [asdict(failure) for failure in failures],
    }
    if failure_log_path is not None:
        _write_failure_log(failure_log_path, result)
        result["failure_log"] = str(failure_log_path)

    return result


def convert_paired_dom_key_files_via_ground_functions(
    left_dom_key_path: str | Path,
    right_dom_key_path: str | Path,
    left_output_key_path: str | Path,
    right_output_key_path: str | Path,
    *,
    left_ground_lookup,
    left_image_project,
    right_ground_lookup,
    right_image_project,
    left_output_width: int,
    left_output_height: int,
    right_output_width: int,
    right_output_height: int,
    left_failure_log_path: str | Path | None = None,
    right_failure_log_path: str | Path | None = None,
    logger: logging.Logger | None = None,
    validate_input_bounds: bool = True,
    require_output_in_bounds: bool = True,
) -> dict[str, object]:
    """转换成对的 DOM 空间 `.key` 文件，并保持 stereo correspondences 对齐。

    Convert paired DOM-space `.key` files while keeping stereo correspondences aligned.

    该封装负责读取左右输入、分别执行几何转换、写回左右输出，并在需要时把两侧失败信息
    写入独立 JSON 日志，方便后续分析哪一步导致对应点被同步丢弃。
    This wrapper reads the left/right inputs, runs the geometric conversion for
    each side, writes paired outputs, and optionally records separate JSON failure
    logs so later analysis can pinpoint which stage caused a correspondence pair
    to be dropped in sync.
    """
    left_dom_key_file = read_key_file(left_dom_key_path)
    right_dom_key_file = read_key_file(right_dom_key_path)
    (
        left_output_key_file,
        right_output_key_file,
        left_failures,
        right_failures,
        left_summary,
        right_summary,
    ) = convert_point_pairs_via_ground_functions(
        left_dom_key_file,
        right_dom_key_file,
        left_ground_lookup=left_ground_lookup,
        left_image_project=left_image_project,
        right_ground_lookup=right_ground_lookup,
        right_image_project=right_image_project,
        left_output_width=left_output_width,
        left_output_height=left_output_height,
        right_output_width=right_output_width,
        right_output_height=right_output_height,
        logger=logger,
        validate_input_bounds=validate_input_bounds,
        require_output_in_bounds=require_output_in_bounds,
    )
    write_key_file(left_output_key_path, left_output_key_file)
    write_key_file(right_output_key_path, right_output_key_file)

    left_result = {
        "dom_key": str(left_dom_key_path),
        "output_key": str(left_output_key_path),
        "input_count": left_summary.input_count,
        "output_count": left_summary.output_count,
        "failure_count": left_summary.failure_count,
        "failure_reasons": left_summary.failure_reasons,
        "failure_categories": left_summary.failure_categories,
        "failures": [asdict(failure) for failure in left_failures],
    }
    right_result = {
        "dom_key": str(right_dom_key_path),
        "output_key": str(right_output_key_path),
        "input_count": right_summary.input_count,
        "output_count": right_summary.output_count,
        "failure_count": right_summary.failure_count,
        "failure_reasons": right_summary.failure_reasons,
        "failure_categories": right_summary.failure_categories,
        "failures": [asdict(failure) for failure in right_failures],
    }
    if left_failure_log_path is not None:
        _write_failure_log(left_failure_log_path, left_result)
        left_result["failure_log"] = str(left_failure_log_path)
    if right_failure_log_path is not None:
        _write_failure_log(right_failure_log_path, right_result)
        right_result["failure_log"] = str(right_failure_log_path)

    return {
        "left_conversion": left_result,
        "right_conversion": right_result,
        "retained_pair_count": left_summary.output_count,
    }


def convert_dom_keypoints_to_original(
    dom_key_path: str | Path,
    dom_cube_path: str | Path,
    original_cube_path: str | Path,
    output_key_path: str | Path,
    *,
    dom_band: int = 1,
    original_band: int = 1,
    failure_log_path: str | Path | None = None,
    logger: logging.Logger | None = None,
    require_output_in_bounds: bool = True,
) -> dict[str, object]:
    """使用 `UniversalGroundMap` 将 DOM 空间 keypoints 转成原始影像坐标。

    Convert DOM-space keypoints to original-image coordinates with `UniversalGroundMap`.

    这里的 CUBE 图像处理链分为三步：
    1. 在 DOM CUBE 上用 `ProjectionFirst` 和 `set_image(sample, line)` 把 DOM 像素点
       解析为稳定的地面坐标；
    2. 在原始 CUBE 上用 `CameraFirst` 和 `set_universal_ground(latitude, longitude)`
       把同一地面点重新投影到传感器原图像素坐标；
    3. 对投影结果做边界检查，并把成功点写回 `.key` 文件，把失败点写入结构化日志。

    The CUBE image-processing chain here has three stages:
    1. Use `ProjectionFirst` plus `set_image(sample, line)` on the DOM cube to
       resolve each DOM pixel into a stable ground location;
    2. Use `CameraFirst` plus `set_universal_ground(latitude, longitude)` on the
       original cube to project that same ground point back into sensor-image
       pixel coordinates;
    3. Validate projected bounds, write successful points to the output `.key`
       file, and record failures in a structured log.
    """
    dom_cube = ip.Cube()
    original_cube = ip.Cube()
    if logger is not None:
        logger.info(
            "dom2ori starting: dom_key=%s dom_cube=%s original_cube=%s output_key=%s",
            dom_key_path,
            dom_cube_path,
            original_cube_path,
            output_key_path,
        )
    dom_cube.open(str(dom_cube_path), "r")
    original_cube.open(str(original_cube_path), "r")
    try:
        if dom_band <= 0 or dom_band > dom_cube.band_count():
            raise ValueError(f"DOM band {dom_band} is out of range for cube {dom_cube_path}.")
        if original_band <= 0 or original_band > original_cube.band_count():
            raise ValueError(f"Original band {original_band} is out of range for cube {original_cube_path}.")

        dom_ground_map = ip.UniversalGroundMap(
            dom_cube,
            ip.UniversalGroundMap.CameraPriority.ProjectionFirst,
        )
        original_ground_map = ip.UniversalGroundMap(
            original_cube,
            ip.UniversalGroundMap.CameraPriority.CameraFirst,
        )
        dom_ground_map.set_band(dom_band)
        original_ground_map.set_band(original_band)

        def ground_lookup(sample: float, line: float):
            if not dom_ground_map.set_image(sample, line):
                return None
            return dom_ground_map.universal_latitude(), dom_ground_map.universal_longitude()

        def image_project(latitude: float, longitude: float):
            if not original_ground_map.set_universal_ground(latitude, longitude):
                return None
            return original_ground_map.sample(), original_ground_map.line()

        result = convert_dom_key_file_via_ground_functions(
            dom_key_path,
            output_key_path,
            ground_lookup=ground_lookup,
            image_project=image_project,
            output_width=original_cube.sample_count(),
            output_height=original_cube.line_count(),
            failure_log_path=failure_log_path,
            logger=logger,
            require_output_in_bounds=require_output_in_bounds,
        )
        result["dom_cube"] = str(dom_cube_path)
        result["original_cube"] = str(original_cube_path)
        result["dom_band"] = dom_band
        result["original_band"] = original_band
        if logger is not None:
            logger.info(
                "dom2ori completed: output_count=%s failure_count=%s",
                result["output_count"],
                result["failure_count"],
            )
        return result
    finally:
        if dom_cube.is_open():
            dom_cube.close()
        if original_cube.is_open():
            original_cube.close()


def convert_paired_dom_keypoints_to_original(
    left_dom_key_path: str | Path,
    right_dom_key_path: str | Path,
    left_dom_cube_path: str | Path,
    right_dom_cube_path: str | Path,
    left_original_cube_path: str | Path,
    right_original_cube_path: str | Path,
    left_output_key_path: str | Path,
    right_output_key_path: str | Path,
    *,
    dom_band: int = 1,
    left_original_band: int = 1,
    right_original_band: int = 1,
    left_failure_log_path: str | Path | None = None,
    right_failure_log_path: str | Path | None = None,
    logger: logging.Logger | None = None,
    require_output_in_bounds: bool = True,
) -> dict[str, object]:
    """将双目 DOM tie-point 文件转换到原始影像坐标，同时不破坏点对对齐。

    Convert stereo DOM tie-point files to original-image coordinates without breaking pair alignment.

    左右 DOM CUBE 会各自完成 `DOM 像素 -> 地面坐标 -> 原始 CUBE 像素` 的投影链，
    但输出阶段仍以“点对”为最小保留单元：只要任一侧失败，整对 correspondence 都会被同步
    丢弃，从而保证后续 ControlNet / matching 处理仍能按索引一一对应。
    The left and right DOM cubes each run their own `DOM pixel -> ground
    coordinate -> original-cube pixel` projection chain, but the output stage
    still treats a correspondence pair as the minimum retained unit: if either
    side fails, the whole pair is removed so downstream ControlNet / matching
    steps can continue to rely on index-wise alignment.
    """
    left_dom_cube = ip.Cube()
    right_dom_cube = ip.Cube()
    left_original_cube = ip.Cube()
    right_original_cube = ip.Cube()
    if logger is not None:
        logger.info(
            "dom2ori paired conversion starting: left_dom_key=%s right_dom_key=%s",
            left_dom_key_path,
            right_dom_key_path,
        )

    left_dom_cube.open(str(left_dom_cube_path), "r")
    right_dom_cube.open(str(right_dom_cube_path), "r")
    left_original_cube.open(str(left_original_cube_path), "r")
    right_original_cube.open(str(right_original_cube_path), "r")
    try:
        if dom_band <= 0 or dom_band > min(left_dom_cube.band_count(), right_dom_cube.band_count()):
            raise ValueError("DOM band is out of range for the requested DOM cubes.")
        if left_original_band <= 0 or left_original_band > left_original_cube.band_count():
            raise ValueError(f"Left original band {left_original_band} is out of range for cube {left_original_cube_path}.")
        if right_original_band <= 0 or right_original_band > right_original_cube.band_count():
            raise ValueError(f"Right original band {right_original_band} is out of range for cube {right_original_cube_path}.")

        left_dom_ground_map = ip.UniversalGroundMap(
            left_dom_cube,
            ip.UniversalGroundMap.CameraPriority.ProjectionFirst,
        )
        right_dom_ground_map = ip.UniversalGroundMap(
            right_dom_cube,
            ip.UniversalGroundMap.CameraPriority.ProjectionFirst,
        )
        left_original_ground_map = ip.UniversalGroundMap(
            left_original_cube,
            ip.UniversalGroundMap.CameraPriority.CameraFirst,
        )
        right_original_ground_map = ip.UniversalGroundMap(
            right_original_cube,
            ip.UniversalGroundMap.CameraPriority.CameraFirst,
        )
        left_dom_ground_map.set_band(dom_band)
        right_dom_ground_map.set_band(dom_band)
        left_original_ground_map.set_band(left_original_band)
        right_original_ground_map.set_band(right_original_band)

        def left_ground_lookup(sample: float, line: float):
            if not left_dom_ground_map.set_image(sample, line):
                return None
            return left_dom_ground_map.universal_latitude(), left_dom_ground_map.universal_longitude()

        def right_ground_lookup(sample: float, line: float):
            if not right_dom_ground_map.set_image(sample, line):
                return None
            return right_dom_ground_map.universal_latitude(), right_dom_ground_map.universal_longitude()

        def left_image_project(latitude: float, longitude: float):
            if not left_original_ground_map.set_universal_ground(latitude, longitude):
                return None
            return left_original_ground_map.sample(), left_original_ground_map.line()

        def right_image_project(latitude: float, longitude: float):
            if not right_original_ground_map.set_universal_ground(latitude, longitude):
                return None
            return right_original_ground_map.sample(), right_original_ground_map.line()

        result = convert_paired_dom_key_files_via_ground_functions(
            left_dom_key_path,
            right_dom_key_path,
            left_output_key_path,
            right_output_key_path,
            left_ground_lookup=left_ground_lookup,
            left_image_project=left_image_project,
            right_ground_lookup=right_ground_lookup,
            right_image_project=right_image_project,
            left_output_width=left_original_cube.sample_count(),
            left_output_height=left_original_cube.line_count(),
            right_output_width=right_original_cube.sample_count(),
            right_output_height=right_original_cube.line_count(),
            left_failure_log_path=left_failure_log_path,
            right_failure_log_path=right_failure_log_path,
            logger=logger,
            require_output_in_bounds=require_output_in_bounds,
        )
        result["left_conversion"]["dom_cube"] = str(left_dom_cube_path)
        result["left_conversion"]["original_cube"] = str(left_original_cube_path)
        result["left_conversion"]["dom_band"] = dom_band
        result["left_conversion"]["original_band"] = left_original_band
        result["right_conversion"]["dom_cube"] = str(right_dom_cube_path)
        result["right_conversion"]["original_cube"] = str(right_original_cube_path)
        result["right_conversion"]["dom_band"] = dom_band
        result["right_conversion"]["original_band"] = right_original_band
        return result
    finally:
        if left_dom_cube.is_open():
            left_dom_cube.close()
        if right_dom_cube.is_open():
            right_dom_cube.close()
        if left_original_cube.is_open():
            left_original_cube.close()
        if right_original_cube.is_open():
            right_original_cube.close()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert DOM-space tie points into original-image coordinates.")
    subparsers = parser.add_subparsers(dest="command")

    single_parser = subparsers.add_parser(
        "single",
        help="Convert one DOM-space .key file into one original-image .key file.",
    )
    single_parser.add_argument("dom_key", help="Input DOM-space .key file.")
    single_parser.add_argument("dom_cube", help="DOM cube path.")
    single_parser.add_argument("original_cube", help="Original-image cube path.")
    single_parser.add_argument("output_key", help="Output original-image .key path.")
    single_parser.add_argument("--dom-band", type=int, default=1, help="Band index to use when reading the DOM cube.")
    single_parser.add_argument("--original-band", type=int, default=1, help="Band index to use when projecting into the original cube.")
    single_parser.add_argument("--failure-log", default=None, help="Optional JSON path that records structured conversion failures.")
    single_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity for runtime diagnostics.",
    )

    paired_parser = subparsers.add_parser(
        "paired",
        help="Convert a stereo DOM-space keypoint pair into paired original-image key files.",
    )
    paired_parser.add_argument("left_dom_key", help="Input left DOM-space .key file.")
    paired_parser.add_argument("right_dom_key", help="Input right DOM-space .key file.")
    paired_parser.add_argument("left_dom_cube", help="Left DOM cube path.")
    paired_parser.add_argument("right_dom_cube", help="Right DOM cube path.")
    paired_parser.add_argument("left_original_cube", help="Left original-image cube path.")
    paired_parser.add_argument("right_original_cube", help="Right original-image cube path.")
    paired_parser.add_argument("left_output_key", help="Output left original-image .key path.")
    paired_parser.add_argument("right_output_key", help="Output right original-image .key path.")
    paired_parser.add_argument("--dom-band", type=int, default=1, help="Band index used when reading the DOM cubes.")
    paired_parser.add_argument("--left-original-band", type=int, default=1, help="Band index used when projecting into the left original cube.")
    paired_parser.add_argument("--right-original-band", type=int, default=1, help="Band index used when projecting into the right original cube.")
    paired_parser.add_argument("--left-failure-log", default=None, help="Optional JSON failure-log path for the left conversion.")
    paired_parser.add_argument("--right-failure-log", default=None, help="Optional JSON failure-log path for the right conversion.")
    paired_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity for runtime diagnostics.",
    )
    return parser


def _normalize_cli_argv(argv: list[str]) -> list[str]:
    if argv and argv[0] not in {"single", "paired", "-h", "--help"}:
        return ["single", *argv]
    return argv


def main(argv: list[str] | None = None) -> None:
    parser = build_argument_parser()
    normalized_argv = _normalize_cli_argv(sys.argv[1:] if argv is None else list(argv))
    if not normalized_argv:
        parser.print_help()
        return
    args = parser.parse_args(normalized_argv)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(message)s")
    logger = logging.getLogger("controlnet_construct.dom2ori")

    if args.command == "paired":
        result = convert_paired_dom_keypoints_to_original(
            args.left_dom_key,
            args.right_dom_key,
            args.left_dom_cube,
            args.right_dom_cube,
            args.left_original_cube,
            args.right_original_cube,
            args.left_output_key,
            args.right_output_key,
            dom_band=args.dom_band,
            left_original_band=args.left_original_band,
            right_original_band=args.right_original_band,
            left_failure_log_path=args.left_failure_log,
            right_failure_log_path=args.right_failure_log,
            logger=logger,
        )
    else:
        result = convert_dom_keypoints_to_original(
            args.dom_key,
            args.dom_cube,
            args.original_cube,
            args.output_key,
            dom_band=args.dom_band,
            original_band=args.original_band,
            failure_log_path=args.failure_log,
            logger=logger,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()