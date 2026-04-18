"""Merge duplicate tie points for a single stereo pair after block matching.

Author: Geng Xun
Created: 2026-04-16
Updated: 2026-04-16  Geng Xun added an initial stereo-pair duplicate merge CLI that reads `.key` files, applies three-decimal hashing, and writes merged outputs.
Updated: 2026-04-18  Geng Xun validated merge-decimal settings and clarified that duplicate merging uses rounded stereo-pair sample/line coordinate hashes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.keypoints import read_key_file, write_key_file
    from controlnet_construct.merge import merge_duplicate_keypoints
else:
    from .keypoints import read_key_file, write_key_file
    from .merge import merge_duplicate_keypoints


MERGE_HASH_STRATEGY = "rounded_stereo_pair_coordinate_hash"
MERGE_HASH_COORDINATE_FIELDS = "left.sample,left.line,right.sample,right.line"
MERGE_HASH_DESCRIPTION = (
    "Round the left/right sample-line coordinates to a fixed decimal precision and remove exact"
    " duplicate stereo-pair coordinate tuples."
)
MIN_HASH_DECIMALS = 0
MAX_HASH_DECIMALS = 6


def validate_merge_decimals(decimals: int) -> int:
    """Validate the decimal precision used by the rounded stereo-pair coordinate hash."""
    if not MIN_HASH_DECIMALS <= decimals <= MAX_HASH_DECIMALS:
        raise ValueError(
            f"Merge hash decimals must be between {MIN_HASH_DECIMALS} and {MAX_HASH_DECIMALS}, got {decimals}."
        )
    return decimals


def merge_stereo_pair_key_files(
    left_input: str,
    right_input: str,
    left_output: str,
    right_output: str,
    *,
    decimals: int = 3,
) -> dict[str, int | str]:
    """Merge duplicate stereo correspondences using rounded left/right sample-line coordinate hashes."""
    validated_decimals = validate_merge_decimals(decimals)
    left_keypoints = read_key_file(left_input)
    right_keypoints = read_key_file(right_input)

    merged_left, merged_right, summary = merge_duplicate_keypoints(
        left_keypoints,
        right_keypoints,
        decimals=validated_decimals,
    )

    write_key_file(left_output, merged_left)
    write_key_file(right_output, merged_right)

    return {
        "left_input": left_input,
        "right_input": right_input,
        "left_output": left_output,
        "right_output": right_output,
        "input_count": summary.input_count,
        "unique_count": summary.unique_count,
        "duplicate_count": summary.duplicate_count,
        "decimals": validated_decimals,
        "hash_rounding_decimals": validated_decimals,
        "hash_strategy": MERGE_HASH_STRATEGY,
        "hash_coordinate_fields": MERGE_HASH_COORDINATE_FIELDS,
        "hash_description": MERGE_HASH_DESCRIPTION,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Merge duplicate tie points for a single stereo pair using rounded left/right sample-line"
            " coordinate hashes rather than descriptor- or geometry-based clustering."
        )
    )
    parser.add_argument("left_input", help="Input .key file for image A.")
    parser.add_argument("right_input", help="Input .key file for image B.")
    parser.add_argument("left_output", help="Output merged .key file for image A.")
    parser.add_argument("right_output", help="Output merged .key file for image B.")
    parser.add_argument(
        "--decimals",
        type=validate_merge_decimals,
        default=3,
        help=(
            "Decimal precision used by the rounded stereo-pair sample/line hash. Valid range:"
            f" {MIN_HASH_DECIMALS}-{MAX_HASH_DECIMALS}."
        ),
    )
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    result = merge_stereo_pair_key_files(
        args.left_input,
        args.right_input,
        args.left_output,
        args.right_output,
        decimals=args.decimals,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()