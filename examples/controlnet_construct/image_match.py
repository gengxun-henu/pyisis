"""Match DOM cube pairs with OpenCV SIFT and write DOM-space `.key` files.

Author: Geng Xun
Created: 2026-04-16
Updated: 2026-04-16  Geng Xun added the initial DOM-space SIFT matching CLI with block matching, grayscale stretch, invalid-value masking, and `.key` export.
Updated: 2026-04-17  Geng Xun allowed tiled DOM matching to operate on the shared raster extent when paired DOM cubes differ slightly in size.
Updated: 2026-04-17  Geng Xun upgraded DOM matching to use projected-overlap crop metadata with configurable expansion and small-overlap skipping.
Updated: 2026-04-17  Geng Xun exposed additional OpenCV SIFT detector parameters through the matching API and CLI.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from dataclasses import dataclass
import json
from pathlib import Path
import sys

import cv2
import numpy as np


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.dom_prepare import prepare_dom_pair_for_matching, write_pair_preparation_metadata
    from controlnet_construct.keypoints import Keypoint, KeypointFile, write_key_file
    from controlnet_construct.preprocess import StretchStats, build_invalid_mask, stretch_to_byte
    from controlnet_construct.runtime import bootstrap_runtime_environment
    from controlnet_construct.tiling import TileWindow, generate_tiles, requires_tiling
else:
    from .dom_prepare import prepare_dom_pair_for_matching, write_pair_preparation_metadata
    from .keypoints import Keypoint, KeypointFile, write_key_file
    from .preprocess import StretchStats, build_invalid_mask, stretch_to_byte
    from .runtime import bootstrap_runtime_environment
    from .tiling import TileWindow, generate_tiles, requires_tiling


bootstrap_runtime_environment()

import isis_pybind as ip


@dataclass(frozen=True, slots=True)
class TileMatchStats:
    local_start_x: int
    local_start_y: int
    width: int
    height: int
    left_start_x: int
    left_start_y: int
    right_start_x: int
    right_start_y: int
    left_valid_pixel_count: int
    right_valid_pixel_count: int
    left_feature_count: int
    right_feature_count: int
    match_count: int
    status: str


@dataclass(frozen=True, slots=True)
class PairedTileWindow:
    local_window: TileWindow
    left_window: TileWindow
    right_window: TileWindow


def _full_image_window(image_width: int, image_height: int) -> TileWindow:
    return TileWindow(start_x=0, start_y=0, width=image_width, height=image_height)


def _paired_windows(
    *,
    left_offset_x: int,
    left_offset_y: int,
    right_offset_x: int,
    right_offset_y: int,
    common_width: int,
    common_height: int,
    max_image_dimension: int,
    block_width: int,
    block_height: int,
    overlap_x: int,
    overlap_y: int,
) -> list[PairedTileWindow]:
    if common_width <= 0 or common_height <= 0:
        return []

    if requires_tiling(common_width, common_height, max_dimension=max_image_dimension):
        local_windows = generate_tiles(
            common_width,
            common_height,
            block_width=block_width,
            block_height=block_height,
            overlap_x=overlap_x,
            overlap_y=overlap_y,
        )
    else:
        local_windows = [_full_image_window(common_width, common_height)]

    return [
        PairedTileWindow(
            local_window=local_window,
            left_window=TileWindow(
                start_x=left_offset_x + local_window.start_x,
                start_y=left_offset_y + local_window.start_y,
                width=local_window.width,
                height=local_window.height,
            ),
            right_window=TileWindow(
                start_x=right_offset_x + local_window.start_x,
                start_y=right_offset_y + local_window.start_y,
                width=local_window.width,
                height=local_window.height,
            ),
        )
        for local_window in local_windows
    ]


def _read_cube_window(cube: ip.Cube, window: TileWindow, *, band: int) -> np.ndarray:
    brick = ip.Brick(cube, window.width, window.height, 1)
    # TileWindow uses Python-style 0-based offsets, but ISIS Brick base positions are
    # 1-based sample/line coordinates. Keep this +1 explicit so regressions do not
    # silently shift all extracted pixels by one column/row.
    brick.set_base_position(window.start_x + 1, window.start_y + 1, band)
    cube.read(brick)
    return np.asarray(brick.double_buffer(), dtype=np.float64).reshape((window.height, window.width))


def _prepare_image_for_sift(
    values: np.ndarray,
    *,
    minimum_value: float | None,
    maximum_value: float | None,
    lower_percent: float,
    upper_percent: float,
    invalid_values: tuple[float, ...],
    special_pixel_abs_threshold: float,
) -> tuple[np.ndarray, np.ndarray, StretchStats]:
    invalid_mask = build_invalid_mask(
        values,
        invalid_values=invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
    )
    if invalid_mask.all():
        stretched = np.zeros(values.shape, dtype=np.uint8)
        stretch_stats = StretchStats(
            minimum_value=0.0,
            maximum_value=0.0,
            valid_pixel_count=0,
            invalid_pixel_count=int(invalid_mask.size),
        )
        sift_mask = np.zeros(values.shape, dtype=np.uint8)
        return stretched, sift_mask, stretch_stats

    stretched, invalid_mask, stretch_stats = stretch_to_byte(
        values,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        lower_percent=lower_percent,
        upper_percent=upper_percent,
        invalid_values=invalid_values,
        special_pixel_abs_threshold=special_pixel_abs_threshold,
    )
    sift_mask = np.where(invalid_mask, 0, 255).astype(np.uint8)
    return stretched, sift_mask, stretch_stats


def _build_sift_detector(
    *,
    max_features: int | None,
    octave_layers: int,
    contrast_threshold: float,
    edge_threshold: float,
    sigma: float,
) -> cv2.SIFT:
    sift_kwargs: dict[str, int | float] = {
        "nOctaveLayers": octave_layers,
        "contrastThreshold": contrast_threshold,
        "edgeThreshold": edge_threshold,
        "sigma": sigma,
    }
    if max_features is not None:
        sift_kwargs["nfeatures"] = max_features
    return cv2.SIFT_create(**sift_kwargs)


def _match_tile(
    left_image: np.ndarray,
    right_image: np.ndarray,
    *,
    left_mask: np.ndarray,
    right_mask: np.ndarray,
    ratio_test: float,
    max_features: int | None,
    sift_octave_layers: int,
    sift_contrast_threshold: float,
    sift_edge_threshold: float,
    sift_sigma: float,
) -> tuple[list[cv2.KeyPoint], list[cv2.KeyPoint], list[cv2.DMatch]]:
    sift = _build_sift_detector(
        max_features=max_features,
        octave_layers=sift_octave_layers,
        contrast_threshold=sift_contrast_threshold,
        edge_threshold=sift_edge_threshold,
        sigma=sift_sigma,
    )
    left_keypoints, left_descriptors = sift.detectAndCompute(left_image, left_mask)
    right_keypoints, right_descriptors = sift.detectAndCompute(right_image, right_mask)

    if not left_keypoints or left_descriptors is None:
        return [], [], []
    if not right_keypoints or right_descriptors is None:
        return left_keypoints, [], []

    matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    raw_matches = matcher.knnMatch(left_descriptors, right_descriptors, k=2)

    filtered_matches: list[cv2.DMatch] = []
    for candidates in raw_matches:
        if len(candidates) < 2:
            continue
        best, alternate = candidates
        if best.distance < ratio_test * alternate.distance:
            filtered_matches.append(best)

    return left_keypoints, right_keypoints, filtered_matches


def _keypoint_to_isis_coordinates(keypoint: cv2.KeyPoint, window: TileWindow) -> Keypoint:
    # OpenCV keypoint.pt is expressed in tile-local 0-based image coordinates, while
    # .key files and downstream ISIS geometry use 1-based sample/line coordinates in
    # the full DOM image. The +1 here is therefore required, not cosmetic.
    return Keypoint(
        sample=window.start_x + float(keypoint.pt[0]) + 1.0,
        line=window.start_y + float(keypoint.pt[1]) + 1.0,
    )


def match_dom_pair(
    left_dom_path: str | Path,
    right_dom_path: str | Path,
    *,
    band: int = 1,
    max_image_dimension: int = 3000,
    block_width: int = 1024,
    block_height: int = 1024,
    overlap_x: int = 128,
    overlap_y: int = 128,
    minimum_value: float | None = None,
    maximum_value: float | None = None,
    lower_percent: float = 0.5,
    upper_percent: float = 99.5,
    invalid_values: tuple[float, ...] = (),
    special_pixel_abs_threshold: float = 1.0e300,
    min_valid_pixels: int = 64,
    ratio_test: float = 0.75,
    max_features: int | None = None,
    sift_octave_layers: int = 3,
    sift_contrast_threshold: float = 0.04,
    sift_edge_threshold: float = 10.0,
    sift_sigma: float = 1.6,
    crop_expand_pixels: int = 100,
    min_overlap_size: int = 16,
) -> tuple[KeypointFile, KeypointFile, dict[str, object]]:
    left_cube = ip.Cube()
    right_cube = ip.Cube()
    left_cube.open(str(left_dom_path), "r")
    right_cube.open(str(right_dom_path), "r")

    try:
        left_width = left_cube.sample_count()
        left_height = left_cube.line_count()
        right_width = right_cube.sample_count()
        right_height = right_cube.line_count()

        if band <= 0 or band > min(left_cube.band_count(), right_cube.band_count()):
            raise ValueError(f"Band {band} is out of range for the requested DOM cubes.")

        preparation = prepare_dom_pair_for_matching(
            left_dom_path,
            right_dom_path,
            expand_pixels=crop_expand_pixels,
            min_overlap_size=min_overlap_size,
        )

        left_points: list[Keypoint] = []
        right_points: list[Keypoint] = []
        tile_summaries: list[TileMatchStats] = []

        if preparation.status == "ready":
            windows = _paired_windows(
                left_offset_x=preparation.left.offset_sample,
                left_offset_y=preparation.left.offset_line,
                right_offset_x=preparation.right.offset_sample,
                right_offset_y=preparation.right.offset_line,
                common_width=preparation.shared_width,
                common_height=preparation.shared_height,
                max_image_dimension=max_image_dimension,
                block_width=block_width,
                block_height=block_height,
                overlap_x=overlap_x,
                overlap_y=overlap_y,
            )

            for paired_window in windows:
                local_window = paired_window.local_window
                left_window = paired_window.left_window
                right_window = paired_window.right_window

                left_values = _read_cube_window(left_cube, left_window, band=band)
                right_values = _read_cube_window(right_cube, right_window, band=band)

                left_image, left_mask, left_stats = _prepare_image_for_sift(
                    left_values,
                    minimum_value=minimum_value,
                    maximum_value=maximum_value,
                    lower_percent=lower_percent,
                    upper_percent=upper_percent,
                    invalid_values=invalid_values,
                    special_pixel_abs_threshold=special_pixel_abs_threshold,
                )
                right_image, right_mask, right_stats = _prepare_image_for_sift(
                    right_values,
                    minimum_value=minimum_value,
                    maximum_value=maximum_value,
                    lower_percent=lower_percent,
                    upper_percent=upper_percent,
                    invalid_values=invalid_values,
                    special_pixel_abs_threshold=special_pixel_abs_threshold,
                )

                if left_stats.valid_pixel_count < min_valid_pixels or right_stats.valid_pixel_count < min_valid_pixels:
                    tile_summaries.append(
                        TileMatchStats(
                            local_start_x=local_window.start_x,
                            local_start_y=local_window.start_y,
                            width=local_window.width,
                            height=local_window.height,
                            left_start_x=left_window.start_x,
                            left_start_y=left_window.start_y,
                            right_start_x=right_window.start_x,
                            right_start_y=right_window.start_y,
                            left_valid_pixel_count=left_stats.valid_pixel_count,
                            right_valid_pixel_count=right_stats.valid_pixel_count,
                            left_feature_count=0,
                            right_feature_count=0,
                            match_count=0,
                            status="skipped_insufficient_valid_pixels",
                        )
                    )
                    continue

                left_keypoints, right_keypoints, filtered_matches = _match_tile(
                    left_image,
                    right_image,
                    left_mask=left_mask,
                    right_mask=right_mask,
                    ratio_test=ratio_test,
                    max_features=max_features,
                    sift_octave_layers=sift_octave_layers,
                    sift_contrast_threshold=sift_contrast_threshold,
                    sift_edge_threshold=sift_edge_threshold,
                    sift_sigma=sift_sigma,
                )

                if not left_keypoints or not right_keypoints:
                    tile_summaries.append(
                        TileMatchStats(
                            local_start_x=local_window.start_x,
                            local_start_y=local_window.start_y,
                            width=local_window.width,
                            height=local_window.height,
                            left_start_x=left_window.start_x,
                            left_start_y=left_window.start_y,
                            right_start_x=right_window.start_x,
                            right_start_y=right_window.start_y,
                            left_valid_pixel_count=left_stats.valid_pixel_count,
                            right_valid_pixel_count=right_stats.valid_pixel_count,
                            left_feature_count=len(left_keypoints),
                            right_feature_count=len(right_keypoints),
                            match_count=0,
                            status="skipped_no_features",
                        )
                    )
                    continue

                if not filtered_matches:
                    tile_summaries.append(
                        TileMatchStats(
                            local_start_x=local_window.start_x,
                            local_start_y=local_window.start_y,
                            width=local_window.width,
                            height=local_window.height,
                            left_start_x=left_window.start_x,
                            left_start_y=left_window.start_y,
                            right_start_x=right_window.start_x,
                            right_start_y=right_window.start_y,
                            left_valid_pixel_count=left_stats.valid_pixel_count,
                            right_valid_pixel_count=right_stats.valid_pixel_count,
                            left_feature_count=len(left_keypoints),
                            right_feature_count=len(right_keypoints),
                            match_count=0,
                            status="skipped_no_matches",
                        )
                    )
                    continue

                for match in filtered_matches:
                    left_points.append(_keypoint_to_isis_coordinates(left_keypoints[match.queryIdx], left_window))
                    right_points.append(_keypoint_to_isis_coordinates(right_keypoints[match.trainIdx], right_window))

                tile_summaries.append(
                    TileMatchStats(
                        local_start_x=local_window.start_x,
                        local_start_y=local_window.start_y,
                        width=local_window.width,
                        height=local_window.height,
                        left_start_x=left_window.start_x,
                        left_start_y=left_window.start_y,
                        right_start_x=right_window.start_x,
                        right_start_y=right_window.start_y,
                        left_valid_pixel_count=left_stats.valid_pixel_count,
                        right_valid_pixel_count=right_stats.valid_pixel_count,
                        left_feature_count=len(left_keypoints),
                        right_feature_count=len(right_keypoints),
                        match_count=len(filtered_matches),
                        status="matched",
                    )
                )
        else:
            windows = []

        left_key_file = KeypointFile(left_width, left_height, tuple(left_points))
        right_key_file = KeypointFile(right_width, right_height, tuple(right_points))
        summary = {
            "left_dom": str(left_dom_path),
            "right_dom": str(right_dom_path),
            "band": band,
            "ratio_test": ratio_test,
            "status": preparation.status if preparation.status != "ready" else ("matched" if left_points else "matched_no_points"),
            "reason": preparation.reason,
            "tiling_used": len(windows) > 1,
            "shared_extent_width": preparation.shared_width,
            "shared_extent_height": preparation.shared_height,
            "dimension_mismatch": left_width != right_width or left_height != right_height,
            "tile_count": len(windows),
            "matched_tile_count": sum(1 for tile in tile_summaries if tile.status == "matched"),
            "skipped_tile_count": sum(1 for tile in tile_summaries if tile.status != "matched"),
            "point_count": len(left_points),
            "left_image_width": left_width,
            "left_image_height": left_height,
            "right_image_width": right_width,
            "right_image_height": right_height,
            "sift_parameters": {
                "max_features": max_features,
                "octave_layers": sift_octave_layers,
                "contrast_threshold": sift_contrast_threshold,
                "edge_threshold": sift_edge_threshold,
                "sigma": sift_sigma,
            },
            "preparation": asdict(preparation),
            "tiles": [asdict(tile) for tile in tile_summaries],
        }
        return left_key_file, right_key_file, summary
    finally:
        if left_cube.is_open():
            left_cube.close()
        if right_cube.is_open():
            right_cube.close()


def match_dom_pair_to_key_files(
    left_dom_path: str | Path,
    right_dom_path: str | Path,
    left_output_key: str | Path,
    right_output_key: str | Path,
    metadata_output: str | Path | None = None,
    **kwargs,
) -> dict[str, object]:
    left_key_file, right_key_file, summary = match_dom_pair(left_dom_path, right_dom_path, **kwargs)
    write_key_file(left_output_key, left_key_file)
    write_key_file(right_output_key, right_key_file)
    if metadata_output is not None:
        write_pair_preparation_metadata(
            metadata_output,
            summary["preparation"],
        )
    return {
        **summary,
        "left_output_key": str(left_output_key),
        "right_output_key": str(right_output_key),
        **({"metadata_output": str(metadata_output)} if metadata_output is not None else {}),
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Match two DOM cubes with OpenCV SIFT and write DOM-space `.key` files.")
    parser.add_argument("left_dom", help="Left DOM cube path.")
    parser.add_argument("right_dom", help="Right DOM cube path.")
    parser.add_argument("left_output_key", help="Output `.key` file for the left DOM image.")
    parser.add_argument("right_output_key", help="Output `.key` file for the right DOM image.")
    parser.add_argument("--metadata-output", default=None, help="Optional JSON sidecar path for projected-overlap crop metadata.")
    parser.add_argument("--band", type=int, default=1, help="Cube band index used for matching.")
    parser.add_argument("--max-image-dimension", type=int, default=3000, help="Maximum image dimension allowed before tiling is enabled.")
    parser.add_argument("--sub-block-size-x", type=int, default=1024, help="Tile width used when block matching is enabled.")
    parser.add_argument("--sub-block-size-y", type=int, default=1024, help="Tile height used when block matching is enabled.")
    parser.add_argument("--overlap-size-x", type=int, default=128, help="Horizontal overlap between adjacent tiles.")
    parser.add_argument("--overlap-size-y", type=int, default=128, help="Vertical overlap between adjacent tiles.")
    parser.add_argument("--minimum-value", type=float, default=None, help="Manual gray-stretch minimum value.")
    parser.add_argument("--maximum-value", type=float, default=None, help="Manual gray-stretch maximum value.")
    parser.add_argument("--lower-percent", type=float, default=0.5, help="Lower percentile used by automatic gray stretch.")
    parser.add_argument("--upper-percent", type=float, default=99.5, help="Upper percentile used by automatic gray stretch.")
    parser.add_argument("--invalid-value", action="append", default=[], type=float, help="Additional invalid pixel sentinel. Repeat for multiple values.")
    parser.add_argument("--special-pixel-abs-threshold", type=float, default=1.0e300, help="Absolute-value threshold used to treat extreme ISIS special pixels as invalid.")
    parser.add_argument("--min-valid-pixels", type=int, default=64, help="Minimum number of valid pixels required before attempting SIFT on a tile.")
    parser.add_argument("--ratio-test", type=float, default=0.75, help="Lowe ratio-test threshold used for descriptor filtering.")
    parser.add_argument("--max-features", type=int, default=None, help="Optional maximum number of SIFT features per tile.")
    parser.add_argument("--sift-octave-layers", type=int, default=3, help="Number of octave layers used by the OpenCV SIFT detector.")
    parser.add_argument("--sift-contrast-threshold", type=float, default=0.04, help="Contrast threshold used by the OpenCV SIFT detector.")
    parser.add_argument("--sift-edge-threshold", type=float, default=10.0, help="Edge threshold used by the OpenCV SIFT detector.")
    parser.add_argument("--sift-sigma", type=float, default=1.6, help="Gaussian sigma used by the OpenCV SIFT detector.")
    parser.add_argument("--crop-expand-pixels", type=int, default=100, help="Extra projected-overlap margin, expressed in pixels, added before matching.")
    parser.add_argument("--min-overlap-size", type=int, default=16, help="Skip matching when the expanded projected-overlap window is smaller than this many pixels in either direction.")
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    result = match_dom_pair_to_key_files(
        args.left_dom,
        args.right_dom,
        args.left_output_key,
        args.right_output_key,
        metadata_output=args.metadata_output,
        band=args.band,
        max_image_dimension=args.max_image_dimension,
        block_width=args.sub_block_size_x,
        block_height=args.sub_block_size_y,
        overlap_x=args.overlap_size_x,
        overlap_y=args.overlap_size_y,
        minimum_value=args.minimum_value,
        maximum_value=args.maximum_value,
        lower_percent=args.lower_percent,
        upper_percent=args.upper_percent,
        invalid_values=tuple(args.invalid_value),
        special_pixel_abs_threshold=args.special_pixel_abs_threshold,
        min_valid_pixels=args.min_valid_pixels,
        ratio_test=args.ratio_test,
        max_features=args.max_features,
        sift_octave_layers=args.sift_octave_layers,
        sift_contrast_threshold=args.sift_contrast_threshold,
        sift_edge_threshold=args.sift_edge_threshold,
        sift_sigma=args.sift_sigma,
        crop_expand_pixels=args.crop_expand_pixels,
        min_overlap_size=args.min_overlap_size,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()