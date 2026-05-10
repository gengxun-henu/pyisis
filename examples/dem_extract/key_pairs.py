"""Load and validate synchronized left/right `.key` point pairs.

Author: Geng Xun
Created: 2026-05-10
Last Modified: 2026-05-10
Updated: 2026-05-10  Geng Xun added `.key` pair loading and bounds validation for DEM extraction.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys


def _load_keypoint_helpers():
    keypoints_path = Path(__file__).resolve().parents[1] / "controlnet_construct" / "keypoints.py"
    spec = importlib.util.spec_from_file_location("_dem_extract_controlnet_keypoints", keypoints_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load controlnet keypoints helper from {keypoints_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.KeypointFile, module.read_key_file


KeypointFile, read_key_file = _load_keypoint_helpers()


@dataclass(frozen=True, slots=True)
class KeyPointPair:
    index: int
    left_sample: float
    left_line: float
    right_sample: float
    right_line: float


def _cube_size(cube, fallback_width: int, fallback_height: int) -> tuple[int, int]:
    if cube is None:
        return fallback_width, fallback_height
    return int(cube.sample_count()), int(cube.line_count())


def _validate_point(label: str, index: int, sample: float, line: float, samples: int, lines: int) -> None:
    if not (1.0 <= sample <= float(samples)) or not (1.0 <= line <= float(lines)):
        raise ValueError(
            f"{label} point {index} has sample/line ({sample}, {line}) outside "
            f"1..{samples}, 1..{lines}."
        )


def load_key_point_pairs_from_key_files(
    left_file: KeypointFile,
    right_file: KeypointFile,
    *,
    left_cube,
    right_cube,
) -> list[KeyPointPair]:
    if len(left_file.points) != len(right_file.points):
        raise ValueError("Left and right .key files must contain the same number of points.")

    left_samples, left_lines = _cube_size(left_cube, left_file.image_width, left_file.image_height)
    right_samples, right_lines = _cube_size(right_cube, right_file.image_width, right_file.image_height)
    pairs: list[KeyPointPair] = []
    for index, (left, right) in enumerate(zip(left_file.points, right_file.points)):
        _validate_point("left", index, left.sample, left.line, left_samples, left_lines)
        _validate_point("right", index, right.sample, right.line, right_samples, right_lines)
        pairs.append(KeyPointPair(index, left.sample, left.line, right.sample, right.line))
    return pairs


def load_key_point_pairs(
    left_key_path: str | Path,
    right_key_path: str | Path,
    *,
    left_cube,
    right_cube,
) -> list[KeyPointPair]:
    left_file = read_key_file(left_key_path)
    right_file = read_key_file(right_key_path)
    return load_key_point_pairs_from_key_files(left_file, right_file, left_cube=left_cube, right_cube=right_cube)
