"""Merge duplicate tie points for a single stereo pair after block matching.

Author: Geng Xun
Created: 2026-04-16
Updated: 2026-04-16  Geng Xun added an initial stereo-pair duplicate merge CLI that reads `.key` files, applies three-decimal hashing, and writes merged outputs.
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


def merge_stereo_pair_key_files(
    left_input: str,
    right_input: str,
    left_output: str,
    right_output: str,
    *,
    decimals: int = 3,
) -> dict[str, int | str]:
    left_keypoints = read_key_file(left_input)
    right_keypoints = read_key_file(right_input)

    merged_left, merged_right, summary = merge_duplicate_keypoints(
        left_keypoints,
        right_keypoints,
        decimals=decimals,
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
        "decimals": decimals,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge duplicate tie points for a single stereo pair using rounded pixel-coordinate hashes."
    )
    parser.add_argument("left_input", help="Input .key file for image A.")
    parser.add_argument("right_input", help="Input .key file for image B.")
    parser.add_argument("left_output", help="Output merged .key file for image A.")
    parser.add_argument("right_output", help="Output merged .key file for image B.")
    parser.add_argument(
        "--decimals",
        type=int,
        default=3,
        help="Number of decimal places used when generating duplicate hashes.",
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