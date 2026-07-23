"""Combine the Linux extension and runtime payloads into one repairable wheel."""

from __future__ import annotations

import argparse
import base64
from copy import copy
import csv
import hashlib
import io
from pathlib import Path
import zipfile


RUNTIME_DEPENDENCY = "usgs-pyisis-runtime-linux-x86_64"


def _copy_member(
    source: zipfile.ZipFile,
    target: zipfile.ZipFile,
    member: zipfile.ZipInfo,
    records: list[tuple[str, str, str]],
) -> None:
    target_info = copy(member)
    digest = hashlib.sha256()
    size = 0
    with source.open(member) as source_stream, target.open(target_info, "w") as target_stream:
        while chunk := source_stream.read(4 * 1024 * 1024):
            target_stream.write(chunk)
            digest.update(chunk)
            size += len(chunk)
    encoded = base64.urlsafe_b64encode(digest.digest()).rstrip(b"=").decode("ascii")
    records.append((member.filename, f"sha256={encoded}", str(size)))


def _metadata_without_runtime_dependency(payload: bytes) -> bytes:
    lines = payload.decode("utf-8").splitlines(keepends=True)
    return "".join(
        line
        for line in lines
        if not (
            line.lower().startswith("requires-dist:")
            and RUNTIME_DEPENDENCY in line.lower()
        )
    ).encode("utf-8")


def _write_payload(
    target: zipfile.ZipFile,
    member: zipfile.ZipInfo,
    payload: bytes,
    records: list[tuple[str, str, str]],
) -> None:
    target_info = copy(member)
    target.writestr(target_info, payload)
    digest = hashlib.sha256(payload).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    records.append((member.filename, f"sha256={encoded}", str(len(payload))))


def build_audit_bundle(extension_wheel: Path, runtime_wheel: Path, output: Path) -> Path:
    """Build a valid main wheel containing the Linux runtime payload."""

    output.parent.mkdir(parents=True, exist_ok=True)
    copied: set[str] = set()
    records: list[tuple[str, str, str]] = []
    record_path: str | None = None
    with zipfile.ZipFile(output, "w", allowZip64=True) as target:
        with zipfile.ZipFile(extension_wheel) as extension:
            for member in extension.infolist():
                if member.filename.endswith(".dist-info/RECORD"):
                    record_path = member.filename
                    continue
                if member.filename.endswith(".dist-info/METADATA"):
                    _write_payload(
                        target,
                        member,
                        _metadata_without_runtime_dependency(extension.read(member)),
                        records,
                    )
                else:
                    _copy_member(extension, target, member, records)
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
                _copy_member(runtime, target, member, records)
                copied.add(member.filename)
        if record_path is None:
            raise ValueError("Extension wheel is missing its dist-info/RECORD file")
        record_stream = io.StringIO()
        writer = csv.writer(record_stream, lineterminator="\n")
        writer.writerows(records)
        writer.writerow((record_path, "", ""))
        target.writestr(record_path, record_stream.getvalue().encode("utf-8"))
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
