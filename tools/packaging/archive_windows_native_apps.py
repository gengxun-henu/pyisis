"""Create a byte-reproducible ZIP from a staged Windows native APP payload."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def create_deterministic_zip(stage_root: Path, archive_path: Path) -> dict[str, object]:
    """Archive *stage_root* with one fixed root and normalized ZIP metadata."""

    stage_root = Path(stage_root).resolve(strict=True)
    if not stage_root.is_dir() or stage_root.name in {"", ".", ".."}:
        raise ValueError(f"invalid stage root: {stage_root}")
    archive_path = Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path = archive_path.resolve(strict=False)
    try:
        archive_path.relative_to(stage_root)
    except ValueError:
        pass
    else:
        raise ValueError("archive path must be outside the stage root")

    members = sorted(
        (path for path in stage_root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(stage_root.parent).as_posix(),
    )
    with zipfile.ZipFile(
        archive_path,
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
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info,
                source.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )

    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    return {
        "path": str(archive_path),
        "root_name": stage_root.name,
        "size": archive_path.stat().st_size,
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
