"""Create a byte-reproducible ZIP from a staged Windows native APP payload."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import uuid
import zipfile


# Historical timestamps make some unsigned ISIS executables, notably
# lronacecho.exe, hang under Windows compatibility/security handling after
# extraction. A fixed recent timestamp preserves byte reproducibility.
ARCHIVE_TIMESTAMP = (2025, 1, 1, 0, 0, 0)


def _is_reparse_point(path: Path) -> bool:
    attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _reject_reparse_tree(path: Path, label: str) -> None:
    if _is_reparse_point(path):
        raise ValueError(f"{label} contains a symlink or reparse point: {path}")
    for entry in Path(path).rglob("*"):
        if _is_reparse_point(entry):
            raise ValueError(f"{label} contains a symlink or reparse point: {entry}")


def _remove_path(path: Path) -> None:
    if not os.path.lexists(path):
        return
    if _is_reparse_point(path):
        if path.is_dir():
            os.rmdir(path)
        else:
            path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def create_deterministic_zip(stage_root: Path, archive_path: Path) -> dict[str, object]:
    """Archive *stage_root* with one fixed root and normalized ZIP metadata."""

    _reject_reparse_tree(stage_root, "stage root")
    stage_root = Path(stage_root).resolve(strict=True)
    if not stage_root.is_dir() or stage_root.name in {"", ".", ".."}:
        raise ValueError(f"invalid stage root: {stage_root}")
    archive_path = Path(archive_path).absolute()
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path = archive_path.parent.resolve(strict=True) / archive_path.name
    if os.path.lexists(archive_path):
        if _is_reparse_point(archive_path):
            raise ValueError(
                f"archive path contains a symlink or reparse point: {archive_path}"
            )
        if not archive_path.is_file():
            raise ValueError(f"archive output is not a file: {archive_path}")
    try:
        archive_path.relative_to(stage_root)
    except ValueError:
        pass
    else:
        raise ValueError("archive path must be outside the stage root")

    entries = list(stage_root.rglob("*"))
    members = sorted(
        (path for path in entries if path.is_file()),
        key=lambda path: path.relative_to(stage_root.parent).as_posix(),
    )
    temporary_archive = archive_path.parent / (
        f".{archive_path.name}.tmp-{uuid.uuid4().hex}"
    )
    if temporary_archive.parent != archive_path.parent:
        raise ValueError("archive temporary path escaped its output directory")
    try:
        with zipfile.ZipFile(
            temporary_archive,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for source in members:
                name = source.relative_to(stage_root.parent).as_posix()
                if (
                    name.startswith("/")
                    or ".." in Path(name).parts
                    or name.split("/", 1)[0] != stage_root.name
                ):
                    raise ValueError(f"unsafe archive member: {name}")
                info = zipfile.ZipInfo(name, ARCHIVE_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                archive.writestr(
                    info,
                    source.read_bytes(),
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                )
        digest = hashlib.sha256(temporary_archive.read_bytes()).hexdigest()
        size = temporary_archive.stat().st_size
        os.replace(temporary_archive, archive_path)
    finally:
        _remove_path(temporary_archive)
    return {
        "path": str(archive_path),
        "root_name": stage_root.name,
        "size": size,
        "sha256": digest,
        "members": len(members),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-root", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            create_deterministic_zip(args.stage_root, args.archive),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
