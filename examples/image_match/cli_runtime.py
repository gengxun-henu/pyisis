"""Translate image-match CLI arguments into orchestration keyword arguments.

Author: Geng Xun
Created: 2026-07-23
Updated: 2026-07-23  Geng Xun extracted CLI-to-API argument forwarding.
"""

from __future__ import annotations

from argparse import Namespace
from collections.abc import Callable
from pathlib import Path


_PASSTHROUGH_ARGUMENTS = (
    "metadata_output",
    "band",
    "max_image_dimension",
    "tile_block_alignment_mode",
    "minimum_value",
    "maximum_value",
    "lower_percent",
    "upper_percent",
    "valid_intensity_lower_percent",
    "valid_intensity_upper_percent",
    "special_pixel_abs_threshold",
    "min_valid_pixels",
    "valid_pixel_percent_threshold",
    "invalid_pixel_radius",
    "enable_tile_validity_prefilter",
    "tile_validity_cache_dir",
    "tile_validity_cell_width",
    "tile_validity_cell_height",
    "pre_ransac_max_ground_distance_km",
    "pre_ransac_ground_lookup_failure_policy",
    "pre_ransac_distance_method",
    "ransac_model",
    "matcher_method",
    "ratio_test",
    "max_features",
    "sift_octave_layers",
    "sift_contrast_threshold",
    "sift_edge_threshold",
    "sift_sigma",
    "crop_expand_pixels",
    "min_overlap_size",
    "use_parallel_cpu",
    "num_worker_parallel_cpu",
    "enable_low_resolution_offset_estimation",
    "enable_adaptive_routing",
    "adaptive_routing_profile",
    "dom_source_metadata_csv",
    "low_resolution_level",
    "low_resolution_matching_target_long_edge",
    "low_resolution_trim_fraction_each_side",
    "low_resolution_max_mean_reprojection_error_pixels",
    "low_resolution_min_retained_match_count",
    "low_resolution_max_mean_projected_offset_meters",
    "left_low_resolution_dom",
    "right_low_resolution_dom",
    "write_match_visualization",
    "show_progress",
    "match_visualization_output_path",
    "match_visualization_output_dir",
    "match_visualization_scale",
    "match_visualization_ransac",
    "match_visualization_ransac_threshold",
    "match_visualization_ransac_confidence",
    "match_visualization_ransac_max_iters",
    "match_visualization_ransac_mode",
    "match_visualization_loose_ransac_keep_threshold",
    "visualization_mode",
    "memory_profile",
    "visualization_target_long_edge",
    "max_preview_pixels",
    "preview_crop_margin_pixels",
    "preview_cache_dir",
    "preview_cache_source",
    "preview_force_regenerate",
    "preview_level",
    "use_gpu",
    "gpu_batch_size",
    "gpu_dynamic_batch",
    "gpu_min_batch_size",
    "gpu_max_batch_size",
    "deep_match_config_path",
    "deep_match_mode",
    "deep_match_manifest",
    "classic_left_key",
    "classic_right_key",
    "use_tile_cache",
    "tile_cache_max_mb",
    "adaptive_warmup_count",
    "adaptive_throughput_threshold_mbps",
    "adaptive_recheck_every",
    "opencv_num_threads",
)


def build_match_dom_pair_kwargs(
    args: Namespace,
    *,
    dom_source_metadata_lookup: object,
    default_deep_match_temp_root_dir: Callable[..., str | Path],
) -> dict[str, object]:
    """Build keyword arguments for ``match_dom_pair_to_key_files``."""

    kwargs = {name: getattr(args, name) for name in _PASSTHROUGH_ARGUMENTS}
    kwargs.update(
        block_width=args.sub_block_size_x,
        block_height=args.sub_block_size_y,
        overlap_x=args.overlap_size_x,
        overlap_y=args.overlap_size_y,
        invalid_values=tuple(args.invalid_value),
        adaptive_routing_deep_presets=getattr(args, "adaptive_routing_deep_presets", None),
        dom_source_metadata_lookup=dom_source_metadata_lookup,
        grouped_deep_match_manifests=args.grouped_deep_match_manifest,
        deep_match_temp_root_dir=(
            args.deep_match_temp_root_dir
            if args.deep_match_temp_root_dir is not None
            else default_deep_match_temp_root_dir(
                metadata_output=args.metadata_output,
                left_output_key=args.left_output_key,
            )
        ),
    )
    return kwargs
