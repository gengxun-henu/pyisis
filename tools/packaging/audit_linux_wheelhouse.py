"""Stream Linux wheel ELF symbol versions into a machine-readable ABI report."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path, PurePosixPath
import re
from typing import BinaryIO
import zipfile


GLIBC_VERSION_RE = re.compile(rb"GLIBC_(\d+)\.(\d+)")
ELF_MAGIC = b"\x7fELF"
SCAN_CHUNK_SIZE = 4 * 1024 * 1024


@dataclass(frozen=True)
class WheelAbi:
    filename: str
    elf_payloads: int
    unique_native_payloads: int
    scanned_bytes: int
    maximum_glibc: str | None
    maximum_glibc_file: str | None
    claims_manylinux: bool


def _parse_version(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)", value)
    if match is None:
        raise ValueError(f"Expected GLIBC version MAJOR.MINOR, got: {value}")
    return int(match.group(1)), int(match.group(2))


def _is_native_candidate(member_name: str) -> bool:
    basename = PurePosixPath(member_name).name
    return (
        "/bin/" in member_name
        or ".so" in basename
        or member_name.endswith(".plugin")
    )


def _scan_elf_versions(stream: BinaryIO) -> tuple[tuple[int, int], int]:
    maximum = (0, 0)
    scanned_bytes = 0
    overlap = b""
    while chunk := stream.read(SCAN_CHUNK_SIZE):
        scanned_bytes += len(chunk)
        data = overlap + chunk
        for match in GLIBC_VERSION_RE.finditer(data):
            maximum = max(maximum, tuple(int(part) for part in match.groups()))
        overlap = data[-32:]
    return maximum, scanned_bytes


def inspect_wheel(wheel: Path) -> WheelAbi:
    maximum = (0, 0)
    maximum_file: str | None = None
    elf_payloads = 0
    scanned_bytes = 0
    seen_payloads: set[tuple[int, int]] = set()

    with zipfile.ZipFile(wheel) as archive:
        for member in archive.infolist():
            if not _is_native_candidate(member.filename):
                continue
            identity = (member.CRC, member.file_size)
            if identity in seen_payloads:
                continue
            seen_payloads.add(identity)
            with archive.open(member) as stream:
                if stream.read(len(ELF_MAGIC)) != ELF_MAGIC:
                    continue
                elf_payloads += 1
                member_maximum, member_bytes = _scan_elf_versions(stream)
                scanned_bytes += member_bytes
            if member_maximum > maximum:
                maximum = member_maximum
                maximum_file = member.filename

    maximum_text = ".".join(str(part) for part in maximum) if maximum_file else None
    return WheelAbi(
        filename=wheel.name,
        elf_payloads=elf_payloads,
        unique_native_payloads=len(seen_payloads),
        scanned_bytes=scanned_bytes,
        maximum_glibc=maximum_text,
        maximum_glibc_file=maximum_file,
        claims_manylinux="manylinux_" in wheel.name,
    )


def _single_wheel(wheelhouse: Path, pattern: str) -> Path:
    matches = sorted(wheelhouse.glob(pattern))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected exactly one wheel matching {pattern!r} in {wheelhouse}, "
            f"found {len(matches)}"
        )
    return matches[0]


def audit_wheelhouse(
    wheelhouse: Path,
    target_glibc: tuple[int, int],
    require_target: bool = False,
) -> dict[str, object]:
    extension = inspect_wheel(_single_wheel(wheelhouse, "usgs_pyisis-*.whl"))
    wheels = (extension,)
    observed_versions = [
        _parse_version(wheel.maximum_glibc)
        for wheel in wheels
        if wheel.maximum_glibc is not None
    ]
    maximum = max(observed_versions, default=(0, 0))
    target_met = maximum <= target_glibc
    target_text = ".".join(str(part) for part in target_glibc)
    maximum_text = ".".join(str(part) for part in maximum)

    report: dict[str, object] = {
        "target_glibc": target_text,
        "maximum_glibc": maximum_text,
        "target_met": target_met,
        "wheels": [asdict(wheel) for wheel in wheels],
        "scope_note": (
            "GLIBC symbol versions are necessary but not sufficient for manylinux "
            "compliance; auditwheel policy and external-library checks are also required."
        ),
    }

    if not target_met and any(wheel.claims_manylinux for wheel in wheels):
        raise RuntimeError(
            f"Wheelhouse claims manylinux but requires GLIBC {maximum_text}, "
            f"above the configured target {target_text}"
        )
    if require_target and not target_met:
        raise RuntimeError(
            f"Wheelhouse requires GLIBC {maximum_text}, above target {target_text}"
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheelhouse", required=True, type=Path)
    parser.add_argument("--target-glibc", default="2.28")
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--require-target", action="store_true")
    args = parser.parse_args()

    report = audit_wheelhouse(
        args.wheelhouse.resolve(),
        _parse_version(args.target_glibc),
        require_target=args.require_target,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
