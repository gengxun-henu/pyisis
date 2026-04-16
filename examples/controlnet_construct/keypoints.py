"""Read and write `.key` files for stereo-pair tie points."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Keypoint:
    sample: float
    line: float


@dataclass(frozen=True, slots=True)
class KeypointFile:
    image_width: int
    image_height: int
    points: tuple[Keypoint, ...]

    def __post_init__(self) -> None:
        if self.image_width <= 0 or self.image_height <= 0:
            raise ValueError("Image width and height must both be positive.")


def _parse_point_line(line: str) -> Keypoint:
    normalized = line.strip().rstrip(",")
    parts = [part.strip() for part in normalized.split(",") if part.strip()]
    if len(parts) != 2:
        raise ValueError(f"Invalid keypoint line: {line!r}")
    return Keypoint(sample=float(parts[0]), line=float(parts[1]))


def read_key_file(file_path: str | Path) -> KeypointFile:
    """Read a `.key` file and validate its internal consistency."""
    path = Path(file_path)
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    if len(lines) < 3:
        raise ValueError("A .key file must contain at least a point count, width, and height.")

    point_count = int(lines[0])
    image_width = int(lines[1])
    image_height = int(lines[2])
    points = tuple(_parse_point_line(line) for line in lines[3:])

    if len(points) != point_count:
        raise ValueError(
            f"The .key file declares {point_count} points but contains {len(points)} point rows."
        )

    return KeypointFile(image_width=image_width, image_height=image_height, points=points)


def write_key_file(file_path: str | Path, keypoint_file: KeypointFile) -> None:
    """Write a `.key` file in the repository's agreed exchange format."""
    path = Path(file_path)
    lines = [
        str(len(keypoint_file.points)),
        str(keypoint_file.image_width),
        str(keypoint_file.image_height),
    ]
    lines.extend(f"{point.sample:.6f}, {point.line:.6f}," for point in keypoint_file.points)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")