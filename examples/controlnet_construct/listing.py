"""Path-list and stereo-pair helpers for DOM matching ControlNet workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class StereoPair:
    """A canonical unordered stereo pair."""

    left: str
    right: str

    def as_csv_line(self) -> str:
        return f"{self.left},{self.right}"


def read_path_list(file_path: str | Path) -> list[str]:
    """Read a newline-delimited path list, skipping blank lines."""
    path = Path(file_path)
    entries = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [entry for entry in entries if entry]


def validate_paired_path_lists(original_paths: list[str], dom_paths: list[str]) -> list[tuple[str, str]]:
    """Validate that original and DOM lists are aligned one-to-one."""
    if not original_paths:
        raise ValueError("The original image list is empty.")

    if not dom_paths:
        raise ValueError("The DOM image list is empty.")

    if len(original_paths) != len(dom_paths):
        raise ValueError(
            "The original image list and DOM image list must contain the same number of entries."
        )

    return list(zip(original_paths, dom_paths, strict=True))


def canonicalize_stereo_pair(left: str, right: str) -> StereoPair:
    """Return a stable unordered stereo-pair representation."""
    normalized_left = left.strip()
    normalized_right = right.strip()

    if not normalized_left or not normalized_right:
        raise ValueError("Stereo pair entries must be non-empty.")

    if normalized_left == normalized_right:
        raise ValueError("A stereo pair cannot contain the same image twice.")

    ordered = tuple(sorted((normalized_left, normalized_right)))
    return StereoPair(*ordered)


def unique_stereo_pairs(pairs: list[tuple[str, str]]) -> list[StereoPair]:
    """Deduplicate stereo pairs while preserving first-seen order."""
    unique_pairs: list[StereoPair] = []
    seen: set[StereoPair] = set()

    for left, right in pairs:
        pair = canonicalize_stereo_pair(left, right)
        if pair in seen:
            continue
        seen.add(pair)
        unique_pairs.append(pair)

    return unique_pairs


def read_stereo_pair_list(file_path: str | Path) -> list[StereoPair]:
    """Read an `images_overlap.lis`-style stereo pair list."""
    raw_lines = read_path_list(file_path)
    pairs: list[StereoPair] = []

    for line in raw_lines:
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 2:
            raise ValueError(f"Invalid stereo pair line: {line!r}")
        pairs.append(canonicalize_stereo_pair(parts[0], parts[1]))

    return pairs


def write_stereo_pair_list(file_path: str | Path, pairs: list[StereoPair]) -> None:
    """Write a canonical stereo-pair list."""
    path = Path(file_path)
    contents = "\n".join(pair.as_csv_line() for pair in pairs)
    if contents:
        contents += "\n"
    path.write_text(contents, encoding="utf-8")