"""CLI helpers for reading, validating, and rewriting `.key` files.

Author: Geng Xun
Created: 2026-04-16
Updated: 2026-04-16  Geng Xun added an initial `.key` validation and rewrite CLI for the DOM matching ControlNet example workflow.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from controlnet_construct.keypoints import read_key_file, write_key_file
else:
    from .keypoints import read_key_file, write_key_file


def summarize_key_file(file_path: str) -> dict[str, object]:
    key_file = read_key_file(file_path)
    return {
        "file": str(file_path),
        "point_count": len(key_file.points),
        "image_width": key_file.image_width,
        "image_height": key_file.image_height,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate or rewrite DOM-matching `.key` files.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a .key file and print a JSON summary.")
    validate_parser.add_argument("key_file", help="Path to the .key file to validate.")

    rewrite_parser = subparsers.add_parser("rewrite", help="Read a .key file and rewrite it in canonical formatting.")
    rewrite_parser.add_argument("input_key", help="Input .key file path.")
    rewrite_parser.add_argument("output_key", help="Output .key file path.")

    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.command == "validate":
        print(json.dumps(summarize_key_file(args.key_file), indent=2, ensure_ascii=False))
        return

    if args.command == "rewrite":
        key_file = read_key_file(args.input_key)
        write_key_file(args.output_key, key_file)
        print(
            json.dumps(
                {
                    "input": args.input_key,
                    "output": args.output_key,
                    "point_count": len(key_file.points),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()