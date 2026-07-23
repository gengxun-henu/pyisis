"""Build a temporary wheel-shaped archive for cross-wheel auditwheel analysis."""

from __future__ import annotations

import argparse
from copy import copy
from pathlib import Path
import shutil
import zipfile


def _copy_member(
    source: zipfile.ZipFile,
    target: zipfile.ZipFile,
    member: zipfile.ZipInfo,
) -> None:
    target_info = copy(member)
    with source.open(member) as source_stream, target.open(target_info, "w") as target_stream:
        shutil.copyfileobj(source_stream, target_stream, length=4 * 1024 * 1024)


def build_audit_bundle(extension_wheel: Path, runtime_wheel: Path, output: Path) -> Path:
    """Combine installed payloads without changing the distributable wheels."""

    output.parent.mkdir(parents=True, exist_ok=True)
    copied: set[str] = set()
    with zipfile.ZipFile(output, "w", allowZip64=True) as target:
        with zipfile.ZipFile(extension_wheel) as extension:
            for member in extension.infolist():
                _copy_member(extension, target, member)
                copied.add(member.filename)

        with zipfile.ZipFile(runtime_wheel) as runtime:
            for member in runtime.infolist():
                first_component = member.filename.split("/", 1)[0]
                if first_component.endswith(".dist-info"):
                    continue
                if member.filename in copied:
                    raise ValueError(
                        f"Audit bundle payload collision: {member.filename}"
                    )
                _copy_member(runtime, target, member)
                copied.add(member.filename)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extension-wheel", required=True, type=Path)
    parser.add_argument("--runtime-wheel", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(
        build_audit_bundle(
            args.extension_wheel.resolve(),
            args.runtime_wheel.resolve(),
            args.output.resolve(),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
