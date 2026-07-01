#!/usr/bin/env python3
"""Remove control points that reference rejected images.

The script converts an ISIS binary control network to PVL, removes any complete
ControlPoint containing a measure serial number from the removed-image list, and
converts the filtered PVL back to a binary control network.

TODO:to be continue, should only remove control measure instead of control point in the future.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Iterable, TextIO


SERIAL_RE = re.compile(r"^\s*SerialNumber\s*=\s*(.+?)\s*$")
OBJECT_RE = re.compile(r"^\s*Object\s*=")
END_OBJECT_RE = re.compile(r"^\s*End_Object\s*$")
CONTROL_POINT_RE = re.compile(r"^\s*Object\s*=\s*ControlPoint\s*$")


@dataclass
class FilterSummary:
    total_points: int = 0
    kept_points: int = 0
    removed_points: int = 0
    matched_removed_serials: set[str] = field(default_factory=set)


def image_id_from_path(path_text: str) -> str:
    return Path(path_text.strip()).name


def read_image_list(path: Path) -> list[str]:
    images: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line and not line.startswith("#"):
                images.append(line)
    return images


def clean_pvl_value(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value


def extract_serials(lines: Iterable[str]) -> set[str]:
    serials: set[str] = set()
    for line in lines:
        match = SERIAL_RE.match(line)
        if match:
            serials.add(clean_pvl_value(match.group(1)))
    return serials


def collect_control_point(first_line: str, source: TextIO) -> list[str]:
    lines = [first_line]
    depth = 1
    for line in source:
        lines.append(line)
        if OBJECT_RE.match(line):
            depth += 1
        elif END_OBJECT_RE.match(line):
            depth -= 1
            if depth == 0:
                break
    if depth != 0:
        raise ValueError("Unterminated ControlPoint block in input PVL")
    return lines


def filter_controlnet_pvl_stream(
    source: TextIO,
    destination: TextIO,
    removed_serials: set[str],
) -> FilterSummary:
    summary = FilterSummary()
    for line in source:
        if not CONTROL_POINT_RE.match(line):
            destination.write(line)
            continue

        point_lines = collect_control_point(line, source)
        summary.total_points += 1
        point_serials = extract_serials(point_lines)
        matched = point_serials.intersection(removed_serials)
        if matched:
            summary.removed_points += 1
            summary.matched_removed_serials.update(matched)
            continue

        summary.kept_points += 1
        destination.writelines(point_lines)
    return summary


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def require_command(name: str) -> str:
    resolved = shutil.which(name)
    if not resolved:
        raise RuntimeError(f"Required ISIS command not found in PATH: {name}")
    return resolved


def cube_serial(cube_path: Path) -> str:
    result = run_command(["getsn", f"from={cube_path}"])
    serial = result.stdout.strip().splitlines()[-1].strip()
    if not serial:
        raise RuntimeError(f"getsn returned an empty serial for {cube_path}")
    return serial


def build_serial_map(images: Iterable[str], base_dir: Path) -> dict[str, str]:
    serials: dict[str, str] = {}
    for image in images:
        cube_path = Path(image)
        if not cube_path.is_absolute():
            cube_path = base_dir / cube_path
        serials[image_id_from_path(image)] = cube_serial(cube_path)
    return serials


def convert_bin_to_pvl(input_cnet: Path, output_pvl: Path) -> None:
    run_command(["cnetbin2pvl", f"from={input_cnet}", f"to={output_pvl}"])


def convert_pvl_to_bin(input_pvl: Path, output_cnet: Path) -> None:
    run_command(["cnetpvl2bin", f"from={input_pvl}", f"to={output_cnet}"])


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove ISIS control points that reference rejected images."
    )
    parser.add_argument("--input-cnet", required=True, type=Path)
    parser.add_argument("--valid-list", required=True, type=Path)
    parser.add_argument("--removed-list", required=True, type=Path)
    parser.add_argument("--output-cnet", required=True, type=Path)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Directory for intermediate PVL files. Defaults to a temporary directory.",
    )
    parser.add_argument(
        "--keep-pvl",
        action="store_true",
        help="Keep intermediate original/filtered PVL files in --work-dir.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    for command in ("getsn", "cnetbin2pvl", "cnetpvl2bin"):
        require_command(command)

    base_dir = args.valid_list.resolve().parent
    valid_images = read_image_list(args.valid_list)
    removed_images = read_image_list(args.removed_list)
    valid_ids = {image_id_from_path(image) for image in valid_images}
    removed_ids = {image_id_from_path(image) for image in removed_images}
    overlap = valid_ids.intersection(removed_ids)
    if overlap:
        joined = ", ".join(sorted(overlap))
        raise RuntimeError(f"Removed images still appear in valid list: {joined}")

    removed_serial_map = build_serial_map(removed_images, base_dir)
    removed_serials = set(removed_serial_map.values())

    context = (
        tempfile.TemporaryDirectory(prefix="filter_controlnet_")
        if args.work_dir is None
        else None
    )
    work_dir = Path(context.name) if context else args.work_dir
    work_dir.mkdir(parents=True, exist_ok=True)

    original_pvl = work_dir / f"{args.input_cnet.name}.pvl"
    filtered_pvl = work_dir / f"{args.output_cnet.name}.pvl"

    try:
        convert_bin_to_pvl(args.input_cnet, original_pvl)
        with original_pvl.open("r", encoding="utf-8") as source, filtered_pvl.open(
            "w", encoding="utf-8"
        ) as destination:
            summary = filter_controlnet_pvl_stream(source, destination, removed_serials)

        args.output_cnet.parent.mkdir(parents=True, exist_ok=True)
        convert_pvl_to_bin(filtered_pvl, args.output_cnet)
    finally:
        if context is not None:
            context.cleanup()
        elif not args.keep_pvl:
            for path in (original_pvl, filtered_pvl):
                path.unlink(missing_ok=True)

    print(f"Input control network: {args.input_cnet}")
    print(f"Output control network: {args.output_cnet}")
    print(f"Valid images: {len(valid_images)}")
    print(f"Removed images: {len(removed_images)}")
    print(f"Control points total: {summary.total_points}")
    print(f"Control points kept: {summary.kept_points}")
    print(f"Control points removed: {summary.removed_points}")
    print(f"Removed-image serials matched: {len(summary.matched_removed_serials)}")
    for image_id, serial in sorted(removed_serial_map.items()):
        marker = "matched" if serial in summary.matched_removed_serials else "not-present"
        print(f"  {marker}: {image_id} -> {serial}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
