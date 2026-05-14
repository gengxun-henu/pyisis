"""Shared helpers for the DOM matching ControlNet example workflow.

Author: Geng Xun
Created: 2026-05-11
Updated: 2026-05-11  Geng Xun added top-of-file metadata so example package exports follow the repository's example-file header convention.
"""

from __future__ import annotations

from importlib import import_module

from .batch_summary import (
    DEFAULT_BATCH_REPORT_NAME,
    DEFAULT_PAIR_REPORT_SUFFIX,
    build_batch_summary,
    load_pair_reports,
    pair_report_filename,
    summarize_pair_result,
    write_batch_summary_report,
)
from .controlnet_merge import generate_cnetmerge_shell_script, pair_controlnet_filename
from .keypoints import Keypoint, KeypointFile, read_key_file, write_key_file
from .listing import StereoPair, read_path_list, read_stereo_pair_list, write_stereo_pair_list
from .merge import MergeSummary, merge_duplicate_keypoints
from .tiling import TileWindow, generate_tiles, requires_tiling
from .tie_point_merge_in_overlap import merge_stereo_pair_key_files

_LAZY_CONTROLNET_STEREOPAIR_EXPORTS = {
    "ControlNetConfig",
    "build_controlnets_for_dom_overlap_list",
    "build_controlnet_for_dom_stereo_pair",
    "build_controlnet_for_stereo_pair",
    "default_controlnet_report_path",
    "write_controlnet_result_report",
}

_LAZY_DOM_PREPARE_EXPORTS = {
    "CropWindow",
    "DomProjectionInfo",
    "GsdNormalizationRecord",
    "PairPreparationMetadata",
    "normalize_dom_list_gsd",
    "prepare_dom_pair_for_matching",
    "read_dom_projection_info",
    "write_pair_preparation_metadata",
}

_LAZY_IMAGE_MATCH_EXPORTS = {
    "match_dom_pair",
    "match_dom_pair_to_key_files",
}

_LAZY_PREPROCESS_EXPORTS = {
    "StretchStats",
    "build_invalid_mask",
    "stretch_to_byte",
}

_LAZY_STEREO_RANSAC_EXPORTS = {
    "filter_stereo_pair_key_files_with_ransac",
    "filter_stereo_pair_keypoints_with_ransac",
}

_LAZY_IMAGE_OVERLAP_EXPORTS = {
    "GeoBounds",
    "extract_camera_ground_bounds",
    "find_overlapping_image_pairs",
}

_LAZY_DOM2ORI_EXPORTS = {
    "DomToOriginalFailure",
    "DomToOriginalSummary",
    "convert_dom_key_file_via_ground_functions",
    "convert_dom_keypoints_to_original",
}

_LAZY_MATCH_VIS_EXPORTS = {
    "default_match_visualization_path",
    "write_stereo_pair_match_visualization",
    "write_stereo_pair_match_visualization_from_key_files",
}


def __getattr__(name: str):
    if name in _LAZY_CONTROLNET_STEREOPAIR_EXPORTS:
        module = import_module(".controlnet_stereopair", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    if name in _LAZY_DOM_PREPARE_EXPORTS:
        module = import_module(".dom_prepare", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    if name in _LAZY_IMAGE_MATCH_EXPORTS:
        module = import_module(".image_match", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    if name in _LAZY_PREPROCESS_EXPORTS:
        module = import_module(".preprocess", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    if name in _LAZY_STEREO_RANSAC_EXPORTS:
        module = import_module(".stereo_ransac", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    if name in _LAZY_IMAGE_OVERLAP_EXPORTS:
        module = import_module(".image_overlap", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    if name in _LAZY_DOM2ORI_EXPORTS:
        module = import_module(".dom2ori", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    if name in _LAZY_MATCH_VIS_EXPORTS:
        module = import_module(".match_visualization", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    if name == "gpu_sift":
        module = import_module(".gpu_sift", __name__)
        globals()["gpu_sift"] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "Keypoint",
    "KeypointFile",
    "MergeSummary",
    "StereoPair",
    "StretchStats",
    "TileWindow",
    "GeoBounds",
    "CropWindow",
    "DomProjectionInfo",
    "GsdNormalizationRecord",
    "PairPreparationMetadata",
    "ControlNetConfig",
    "build_controlnets_for_dom_overlap_list",
    "DomToOriginalFailure",
    "DomToOriginalSummary",
    "DEFAULT_BATCH_REPORT_NAME",
    "DEFAULT_PAIR_REPORT_SUFFIX",
    "build_batch_summary",
    "build_invalid_mask",
    "gpu_sift",
    "build_controlnet_for_dom_stereo_pair",
    "build_controlnet_for_stereo_pair",
    "default_controlnet_report_path",
    "generate_cnetmerge_shell_script",
    "convert_dom_key_file_via_ground_functions",
    "convert_dom_keypoints_to_original",
    "extract_camera_ground_bounds",
    "find_overlapping_image_pairs",
    "filter_stereo_pair_key_files_with_ransac",
    "filter_stereo_pair_keypoints_with_ransac",
    "generate_tiles",
    "match_dom_pair",
    "match_dom_pair_to_key_files",
    "merge_stereo_pair_key_files",
    "merge_duplicate_keypoints",
    "normalize_dom_list_gsd",
    "load_pair_reports",
    "pair_controlnet_filename",
    "pair_report_filename",
    "prepare_dom_pair_for_matching",
    "read_key_file",
    "read_dom_projection_info",
    "read_path_list",
    "read_stereo_pair_list",
    "requires_tiling",
    "summarize_pair_result",
    "stretch_to_byte",
    "default_match_visualization_path",
    "write_batch_summary_report",
    "write_controlnet_result_report",
    "write_pair_preparation_metadata",
    "write_stereo_pair_match_visualization",
    "write_stereo_pair_match_visualization_from_key_files",
    "write_key_file",
    "write_stereo_pair_list",
]