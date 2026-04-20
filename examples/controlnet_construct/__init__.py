"""Shared helpers for the DOM matching ControlNet example workflow."""

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
from .dom_prepare import (
    CropWindow,
    DomProjectionInfo,
    GsdNormalizationRecord,
    PairPreparationMetadata,
    normalize_dom_list_gsd,
    prepare_dom_pair_for_matching,
    read_dom_projection_info,
    write_pair_preparation_metadata,
)
from .keypoints import Keypoint, KeypointFile, read_key_file, write_key_file
from .listing import StereoPair, read_path_list, read_stereo_pair_list, write_stereo_pair_list
from .merge import MergeSummary, merge_duplicate_keypoints
from .preprocess import StretchStats, build_invalid_mask, stretch_to_byte
from .tiling import TileWindow, generate_tiles, requires_tiling
from .image_overlap import GeoBounds, extract_camera_ground_bounds, find_overlapping_image_pairs
from .image_match import (
    default_match_visualization_path,
    filter_stereo_pair_key_files_with_ransac,
    filter_stereo_pair_keypoints_with_ransac,
    match_dom_pair,
    match_dom_pair_to_key_files,
    write_stereo_pair_match_visualization,
    write_stereo_pair_match_visualization_from_key_files,
)
from .tie_point_merge_in_overlap import merge_stereo_pair_key_files
from .controlnet_stereopair import (
    ControlNetConfig,
    build_controlnets_for_dom_overlap_list,
    build_controlnet_for_dom_stereo_pair,
    build_controlnet_for_stereo_pair,
    default_controlnet_report_path,
    write_controlnet_result_report,
)
from .dom2ori import (
    DomToOriginalFailure,
    DomToOriginalSummary,
    convert_dom_key_file_via_ground_functions,
    convert_dom_keypoints_to_original,
)

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