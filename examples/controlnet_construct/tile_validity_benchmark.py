"""Benchmark DOM tile-validity cell-size combinations for index-build cost and prefilter effect.

Author: Geng Xun
Created: 2026-05-04
Updated: 2026-05-04  Geng Xun added a benchmark CLI for comparing tile-validity cell-size combinations against real DOM pairs.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Sequence


DEFAULT_CELL_SIZE = (1024, 1024)


@dataclass(frozen=True, slots=True)
class CellSizeSpec:
    width: int
    height: int

    @property
    def label(self) -> str:
        return f"{self.width}x{self.height}"


def _positive_int(value: int | str, *, field_name: str) -> int:
    resolved_value = int(value)
    if resolved_value <= 0:
        raise ValueError(f"{field_name} must be positive.")
    return resolved_value


def parse_cell_size_spec(value: str) -> CellSizeSpec:
    raw_value = str(value).strip().lower().replace("×", "x")
    parts = [part.strip() for part in raw_value.split("x")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"Invalid --cell-size value {value!r}. Expected WIDTHxHEIGHT, for example 1024x1071."
        )
    return CellSizeSpec(
        width=_positive_int(parts[0], field_name="cell_width"),
        height=_positive_int(parts[1], field_name="cell_height"),
    )


def _parse_cell_size_arg(value: str) -> CellSizeSpec:
    try:
        return parse_cell_size_spec(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_positive_int_arg(value: str, *, field_name: str) -> int:
    try:
        return _positive_int(value, field_name=field_name)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def resolve_cell_size_specs(
    *,
    explicit_sizes: Sequence[CellSizeSpec] | None,
    widths: Sequence[int] | None,
    heights: Sequence[int] | None,
) -> list[CellSizeSpec]:
    resolved_specs: list[CellSizeSpec] = []

    if explicit_sizes:
        resolved_specs.extend(explicit_sizes)

    resolved_widths = [int(value) for value in (widths or [])]
    resolved_heights = [int(value) for value in (heights or [])]
    if resolved_widths or resolved_heights:
        if not resolved_widths or not resolved_heights:
            raise ValueError("--cell-width and --cell-height must be provided together when using width/height grids.")
        for width in resolved_widths:
            for height in resolved_heights:
                resolved_specs.append(CellSizeSpec(width=width, height=height))

    if not resolved_specs:
        resolved_specs.append(CellSizeSpec(width=DEFAULT_CELL_SIZE[0], height=DEFAULT_CELL_SIZE[1]))

    deduped_specs: list[CellSizeSpec] = []
    seen: set[tuple[int, int]] = set()
    for spec in resolved_specs:
        key = (spec.width, spec.height)
        if key in seen:
            continue
        seen.add(key)
        deduped_specs.append(spec)
    return deduped_specs


def _resolved_setting(args: argparse.Namespace, config_defaults: dict[str, object], field_name: str, fallback: Any) -> Any:
    value = getattr(args, field_name)
    if value is not None:
        return value
    if field_name in config_defaults:
        return config_defaults[field_name]
    return fallback


def _json_default(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "tolist"):
        return value.tolist()
    return str(value)


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark tile-validity cell-size combinations for DOM validity-index build cost "
            "and workflow-level prefilter retention."
        )
    )
    parser.add_argument("left_dom", help="Left DOM cube path.")
    parser.add_argument("right_dom", help="Right DOM cube path.")
    parser.add_argument("--config", default=None, help="Optional image-match config JSON used to seed benchmark defaults from ImageMatch.")
    parser.add_argument("--output", default=None, help="Optional JSON output path for the benchmark summary.")
    parser.add_argument("--cache-dir", default=None, help="Optional benchmark cache root directory. Each cell-size combination gets its own subdirectory.")
    parser.add_argument("--cell-size", dest="cell_sizes", action="append", default=None, type=_parse_cell_size_arg, help="Explicit cell-size combination in WIDTHxHEIGHT form. Repeat for multiple combinations.")
    parser.add_argument("--cell-width", dest="cell_widths", action="append", default=None, type=lambda value: _parse_positive_int_arg(value, field_name="cell_width"), help="Grid benchmark width candidate. Repeat to combine with all provided --cell-height values.")
    parser.add_argument("--cell-height", dest="cell_heights", action="append", default=None, type=lambda value: _parse_positive_int_arg(value, field_name="cell_height"), help="Grid benchmark height candidate. Repeat to combine with all provided --cell-width values.")
    parser.add_argument("--band", type=int, default=None, help="Cube band index used for validity-index construction and tile generation.")
    parser.add_argument("--max-image-dimension", type=int, default=None, help="Maximum shared extent dimension before tiling is enabled.")
    parser.add_argument("--sub-block-size-x", type=int, default=None, help="Tile width used when shared-extent tiling is required.")
    parser.add_argument("--sub-block-size-y", type=int, default=None, help="Tile height used when shared-extent tiling is required.")
    parser.add_argument("--overlap-size-x", type=int, default=None, help="Horizontal overlap between adjacent full-resolution tiles.")
    parser.add_argument("--overlap-size-y", type=int, default=None, help="Vertical overlap between adjacent full-resolution tiles.")
    parser.add_argument("--crop-expand-pixels", type=int, default=None, help="Projected-overlap expansion margin passed to DOM pair preparation.")
    parser.add_argument("--min-overlap-size", type=int, default=None, help="Minimum shared overlap size, in pixels, required before tiling is considered ready.")
    parser.add_argument("--valid-pixel-percent-threshold", type=float, default=None, help="Positive threshold used by the coarse validity prefilter.")
    parser.add_argument("--invalid-pixel-radius", type=int, default=None, help="Invalid-pixel radius used by validity-index construction.")
    parser.add_argument("--special-pixel-abs-threshold", type=float, default=None, help="Absolute-value threshold used to treat large-magnitude pixels as invalid.")
    parser.add_argument("--invalid-value", action="append", default=None, type=float, help="Additional invalid sentinel value. Repeat for multiple values.")
    return parser


def benchmark_tile_validity_pair(args: argparse.Namespace) -> dict[str, object]:
    if __package__ in {None, ""}:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from controlnet_construct.dom_prepare import prepare_dom_pair_for_matching
        from controlnet_construct.image_match import load_image_match_defaults_from_config
        from controlnet_construct.runtime import bootstrap_runtime_environment
        from controlnet_construct.tile_matching import _paired_windows, _resolved_invalid_values_for_cube
        from controlnet_construct.tile_validity import default_tile_validity_cache_dir, ensure_dom_validity_index, prefilter_paired_windows_by_validity
    else:
        from .dom_prepare import prepare_dom_pair_for_matching
        from .image_match import load_image_match_defaults_from_config
        from .runtime import bootstrap_runtime_environment
        from .tile_matching import _paired_windows, _resolved_invalid_values_for_cube
        from .tile_validity import default_tile_validity_cache_dir, ensure_dom_validity_index, prefilter_paired_windows_by_validity

    bootstrap_runtime_environment()
    import isis_pybind as ip

    left_dom_path = Path(args.left_dom).expanduser().resolve()
    right_dom_path = Path(args.right_dom).expanduser().resolve()
    config_path = Path(args.config).expanduser().resolve() if args.config is not None else None
    output_path = Path(args.output).expanduser().resolve() if args.output is not None else None

    config_defaults: dict[str, object] = {}
    if config_path is not None:
        config_defaults = load_image_match_defaults_from_config(str(config_path))

    band = int(_resolved_setting(args, config_defaults, "band", 1))
    max_image_dimension = int(_resolved_setting(args, config_defaults, "max_image_dimension", 3000))
    sub_block_size_x = int(_resolved_setting(args, config_defaults, "sub_block_size_x", 1024))
    sub_block_size_y = int(_resolved_setting(args, config_defaults, "sub_block_size_y", 1024))
    overlap_size_x = int(_resolved_setting(args, config_defaults, "overlap_size_x", 128))
    overlap_size_y = int(_resolved_setting(args, config_defaults, "overlap_size_y", 128))
    crop_expand_pixels = int(_resolved_setting(args, config_defaults, "crop_expand_pixels", 100))
    min_overlap_size = int(_resolved_setting(args, config_defaults, "min_overlap_size", 16))
    valid_pixel_percent_threshold = float(_resolved_setting(args, config_defaults, "valid_pixel_percent_threshold", 0.0))
    invalid_pixel_radius = int(_resolved_setting(args, config_defaults, "invalid_pixel_radius", 1))
    special_pixel_abs_threshold = float(_resolved_setting(args, config_defaults, "special_pixel_abs_threshold", 1.0e300))
    invalid_values = tuple(float(value) for value in (_resolved_setting(args, config_defaults, "invalid_value", ()) or ()))

    cell_specs = resolve_cell_size_specs(
        explicit_sizes=args.cell_sizes,
        widths=args.cell_widths,
        heights=args.cell_heights,
    )

    cache_root = (
        Path(args.cache_dir).expanduser().resolve()
        if args.cache_dir is not None
        else default_tile_validity_cache_dir(metadata_output=str(output_path) if output_path is not None else None) / "benchmark"
    )
    cache_root.mkdir(parents=True, exist_ok=True)

    left_cube = ip.Cube()
    right_cube = ip.Cube()
    left_cube.open(str(left_dom_path), "r")
    right_cube.open(str(right_dom_path), "r")
    try:
        if band <= 0 or band > min(left_cube.band_count(), right_cube.band_count()):
            raise ValueError(f"Band {band} is out of range for the provided DOM pair.")

        left_invalid_values = _resolved_invalid_values_for_cube(left_cube, invalid_values)
        right_invalid_values = _resolved_invalid_values_for_cube(right_cube, invalid_values)
        preparation = prepare_dom_pair_for_matching(
            str(left_dom_path),
            str(right_dom_path),
            expand_pixels=crop_expand_pixels,
            min_overlap_size=min_overlap_size,
        )

        if preparation.status == "ready":
            windows = _paired_windows(
                left_offset_x=preparation.left.offset_sample,
                left_offset_y=preparation.left.offset_line,
                right_offset_x=preparation.right.offset_sample,
                right_offset_y=preparation.right.offset_line,
                common_width=preparation.shared_width,
                common_height=preparation.shared_height,
                max_image_dimension=max_image_dimension,
                block_width=sub_block_size_x,
                block_height=sub_block_size_y,
                overlap_x=overlap_size_x,
                overlap_y=overlap_size_y,
            )
        else:
            windows = []

        benchmark_results: list[dict[str, object]] = []
        for cell_spec in cell_specs:
            cell_cache_dir = cache_root / cell_spec.label
            if cell_cache_dir.exists():
                shutil.rmtree(cell_cache_dir)
            cell_cache_dir.mkdir(parents=True, exist_ok=True)

            left_cold_start = time.perf_counter()
            left_index, left_cold_diagnostics = ensure_dom_validity_index(
                cache_dir=cell_cache_dir,
                dom_path=str(left_dom_path),
                cube=left_cube,
                band=band,
                invalid_values=left_invalid_values,
                special_pixel_abs_threshold=special_pixel_abs_threshold,
                invalid_pixel_radius=invalid_pixel_radius,
                cell_width=cell_spec.width,
                cell_height=cell_spec.height,
            )
            left_cold_seconds = time.perf_counter() - left_cold_start

            right_cold_start = time.perf_counter()
            right_index, right_cold_diagnostics = ensure_dom_validity_index(
                cache_dir=cell_cache_dir,
                dom_path=str(right_dom_path),
                cube=right_cube,
                band=band,
                invalid_values=right_invalid_values,
                special_pixel_abs_threshold=special_pixel_abs_threshold,
                invalid_pixel_radius=invalid_pixel_radius,
                cell_width=cell_spec.width,
                cell_height=cell_spec.height,
            )
            right_cold_seconds = time.perf_counter() - right_cold_start

            left_warm_start = time.perf_counter()
            _, left_warm_diagnostics = ensure_dom_validity_index(
                cache_dir=cell_cache_dir,
                dom_path=str(left_dom_path),
                cube=left_cube,
                band=band,
                invalid_values=left_invalid_values,
                special_pixel_abs_threshold=special_pixel_abs_threshold,
                invalid_pixel_radius=invalid_pixel_radius,
                cell_width=cell_spec.width,
                cell_height=cell_spec.height,
            )
            left_warm_seconds = time.perf_counter() - left_warm_start

            right_warm_start = time.perf_counter()
            _, right_warm_diagnostics = ensure_dom_validity_index(
                cache_dir=cell_cache_dir,
                dom_path=str(right_dom_path),
                cube=right_cube,
                band=band,
                invalid_values=right_invalid_values,
                special_pixel_abs_threshold=special_pixel_abs_threshold,
                invalid_pixel_radius=invalid_pixel_radius,
                cell_width=cell_spec.width,
                cell_height=cell_spec.height,
            )
            right_warm_seconds = time.perf_counter() - right_warm_start

            if windows:
                prefilter_result = prefilter_paired_windows_by_validity(
                    windows,
                    left_index=left_index,
                    right_index=right_index,
                    valid_pixel_percent_threshold=valid_pixel_percent_threshold,
                )
                prefilter_summary: dict[str, object] = {
                    "tile_count_before": len(windows),
                    "tile_count_after": len(prefilter_result.kept_windows),
                    "preindexed_skipped_tile_count": prefilter_result.preindexed_skipped_tile_count,
                    "retained_ratio": (
                        0.0 if not windows else len(prefilter_result.kept_windows) / float(len(windows))
                    ),
                    "skip_reasons": dict(prefilter_result.skip_reasons),
                }
            else:
                prefilter_summary = {
                    "tile_count_before": 0,
                    "tile_count_after": 0,
                    "preindexed_skipped_tile_count": 0,
                    "retained_ratio": 0.0,
                    "skip_reasons": {},
                    "unavailable_reason": preparation.reason,
                }

            benchmark_results.append(
                {
                    "cell_width": cell_spec.width,
                    "cell_height": cell_spec.height,
                    "cell_label": cell_spec.label,
                    "cache_dir": str(cell_cache_dir),
                    "left_index": {
                        "cold_seconds": left_cold_seconds,
                        "warm_seconds": left_warm_seconds,
                        "cold_status": left_cold_diagnostics.get("status"),
                        "warm_status": left_warm_diagnostics.get("status"),
                        "grid_width": left_index.grid_width,
                        "grid_height": left_index.grid_height,
                    },
                    "right_index": {
                        "cold_seconds": right_cold_seconds,
                        "warm_seconds": right_warm_seconds,
                        "cold_status": right_cold_diagnostics.get("status"),
                        "warm_status": right_warm_diagnostics.get("status"),
                        "grid_width": right_index.grid_width,
                        "grid_height": right_index.grid_height,
                    },
                    "combined_cold_seconds": left_cold_seconds + right_cold_seconds,
                    "combined_warm_seconds": left_warm_seconds + right_warm_seconds,
                    "prefilter": prefilter_summary,
                }
            )

        summary: dict[str, object] = {
            "left_dom": str(left_dom_path),
            "right_dom": str(right_dom_path),
            "config": str(config_path) if config_path is not None else None,
            "band": band,
            "invalid_values": list(invalid_values),
            "special_pixel_abs_threshold": special_pixel_abs_threshold,
            "invalid_pixel_radius": invalid_pixel_radius,
            "valid_pixel_percent_threshold": valid_pixel_percent_threshold,
            "max_image_dimension": max_image_dimension,
            "sub_block_size_x": sub_block_size_x,
            "sub_block_size_y": sub_block_size_y,
            "overlap_size_x": overlap_size_x,
            "overlap_size_y": overlap_size_y,
            "crop_expand_pixels": crop_expand_pixels,
            "min_overlap_size": min_overlap_size,
            "pair_preparation": asdict(preparation),
            "requested_cell_sizes": [spec.label for spec in cell_specs],
            "benchmark_results": benchmark_results,
        }
    finally:
        if left_cube.is_open():
            left_cube.close()
        if right_cube.is_open():
            right_cube.close()

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=_json_default) + "\n", encoding="utf-8")
    return summary


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_argument_parser()
    args = parser.parse_args(argv)
    result = benchmark_tile_validity_pair(args)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=_json_default))


if __name__ == "__main__":
    main()