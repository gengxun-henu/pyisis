"""Validate a Windows ISIS native-APP archive and its retained evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any
import uuid
import zipfile

try:
    from tools.packaging.windows_native_app_manifest import (
        ReleaseContract,
        load_release_contract,
    )
except ModuleNotFoundError:
    from windows_native_app_manifest import ReleaseContract, load_release_contract


REQUIRED_CHECK_GROUPS = (
    "archive-extract",
    "cli-help",
    "real-operations",
    "gui-launch",
    "external-isisdata",
    "negative-launcher",
)
TEXT_SUFFIXES = {"", ".cmd", ".json", ".md", ".plugin", ".ps1", ".sha256", ".txt", ".xml"}
FORBIDDEN_ABSOLUTE_RE = re.compile(
    rb"(?i)[a-z]:[\\/](?:[^\\/\x00\r\n]+[\\/])*"
    rb"(?:build|conda|miniconda|pyisis-win-env)"
    rb"(?=[\\/ \t\r\n\"',;}\]]|$)"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DRIVE_COMPONENT_RE = re.compile(r"^[A-Za-z]:")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json_bytes(content: bytes, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(
            content.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid JSON in {label}: {error}") from error
    if type(payload) is not dict:
        raise ValueError(f"{label} must contain a JSON object")
    return payload


def _read_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        content = Path(path).read_bytes()
    except OSError as error:
        raise ValueError(f"unable to read {label}: {error}") from error
    return _load_json_bytes(content, label), content


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _contains_forbidden_absolute_path(content: bytes) -> bool:
    return bool(
        FORBIDDEN_ABSOLUTE_RE.search(content)
        or FORBIDDEN_ABSOLUTE_RE.search(content.replace(b"\\\\", b"\\"))
    )


def _require_schema_one(payload: dict[str, Any], label: str) -> None:
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise ValueError(f"{label} schema_version must be integer 1")


def _require_string_list(value: Any, label: str) -> tuple[str, ...]:
    if type(value) is not list or any(type(item) is not str for item in value):
        raise ValueError(f"{label} must be a list of strings")
    result = tuple(value)
    if len({item.casefold() for item in result}) != len(result):
        raise ValueError(f"{label} contains duplicate names")
    return result


def safe_zip_member(name: str, expected_root: str) -> PurePosixPath:
    """Return a checked member path confined below one exact archive root."""

    if type(name) is not str or not name or "\\" in name:
        raise ValueError(f"unsafe ZIP member: {name}")
    raw_parts = name.split("/")
    if (
        name.startswith("/")
        or any(part in {"", ".", ".."} for part in raw_parts)
        or any(DRIVE_COMPONENT_RE.match(part) for part in raw_parts)
    ):
        raise ValueError(f"unsafe ZIP member: {name}")
    member = PurePosixPath(name)
    if member.is_absolute() or not member.parts:
        raise ValueError(f"unsafe ZIP member: {name}")
    if member.parts[0] != expected_root:
        raise ValueError(f"ZIP member outside fixed root: {name}")
    if len(member.parts) == 1:
        raise ValueError(f"unsafe ZIP member: {name}")
    return member


def _read_archive(
    archive_path: Path, contract: ReleaseContract
) -> tuple[dict[str, bytes], int]:
    if Path(archive_path).name != contract.archive_name:
        raise ValueError(
            f"archive name mismatch: expected {contract.archive_name}, found {Path(archive_path).name}"
        )
    members: dict[str, bytes] = {}
    exact_names: set[str] = set()
    folded_names: dict[str, str] = {}
    try:
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            for info in infos:
                member = safe_zip_member(info.filename, contract.root_name)
                if info.filename in exact_names:
                    raise ValueError(f"duplicate ZIP member: {info.filename}")
                folded = info.filename.casefold()
                if folded in folded_names:
                    raise ValueError(
                        "case-insensitive ZIP member collision: "
                        f"{folded_names[folded]} and {info.filename}"
                    )
                exact_names.add(info.filename)
                folded_names[folded] = info.filename
                mode = (info.external_attr >> 16) & 0xFFFF
                if info.is_dir() or (mode and not stat.S_ISREG(mode)):
                    raise ValueError(f"non-regular ZIP member: {info.filename}")
                relative = PurePosixPath(*member.parts[1:]).as_posix()
                try:
                    members[relative] = archive.read(info)
                except (OSError, RuntimeError, zipfile.BadZipFile) as error:
                    raise ValueError(f"unable to read ZIP member {info.filename}: {error}") from error
    except (OSError, zipfile.BadZipFile) as error:
        raise ValueError(f"unable to read archive {archive_path}: {error}") from error
    if not members:
        raise ValueError("archive contains no payload files")
    return members, len(infos)


def _validate_apps_manifest(
    members: dict[str, bytes], contract: ReleaseContract
) -> None:
    name = "manifest/apps.json"
    if name not in members:
        raise ValueError("missing archive APP manifest")
    payload = _load_json_bytes(members[name], name)
    _require_schema_one(payload, "APP manifest")
    expected_keys = {
        "schema_version",
        "distribution",
        "isis_version",
        "platform",
        "public_cli_apps",
        "public_gui_apps",
        "public_apps",
        "runtime_helpers",
    }
    if set(payload) != expected_keys:
        raise ValueError(
            "APP manifest keys mismatch: "
            f"missing={sorted(expected_keys - set(payload))}, "
            f"extra={sorted(set(payload) - expected_keys)}"
        )
    expected_identity = {
        "distribution": contract.distribution,
        "isis_version": contract.isis_version,
        "platform": contract.platform,
    }
    for key, expected in expected_identity.items():
        if payload.get(key) != expected:
            raise ValueError(f"APP manifest {key} mismatch")
    lists = {
        "public_cli_apps": contract.public_cli_apps,
        "public_gui_apps": contract.public_gui_apps,
        "public_apps": contract.public_apps,
        "runtime_helpers": contract.runtime_helpers,
    }
    for key, expected in lists.items():
        actual = _require_string_list(payload.get(key), f"APP manifest {key}")
        if actual != expected:
            raise ValueError(f"public APP inventory mismatch in {key}")
    if len(contract.public_apps) != 151:
        raise ValueError(
            f"release contract must contain exactly 151 public APPs, found {len(contract.public_apps)}"
        )
    missing_mandatory = sorted(set(contract.mandatory_apps) - set(contract.public_apps))
    if missing_mandatory:
        raise ValueError(f"missing mandatory APP declarations: {missing_mandatory}")


def _validate_payload_inventory(
    members: dict[str, bytes], contract: ReleaseContract
) -> None:
    executable_members = {
        name.casefold(): name for name in members if PurePosixPath(name).suffix.casefold() == ".exe"
    }
    expected_executables = {
        f"bin/{name}.exe" for name in (*contract.public_apps, *contract.runtime_helpers)
    }
    actual_executables = set(executable_members.values())
    missing_mandatory = [
        name for name in contract.mandatory_apps if f"bin/{name}.exe" not in actual_executables
    ]
    if missing_mandatory:
        raise ValueError(f"missing mandatory APP executables: {missing_mandatory}")
    unexpected = sorted(actual_executables - expected_executables)
    if unexpected:
        raise ValueError(f"unexpected executable in archive: {unexpected}")
    missing = sorted(expected_executables - actual_executables)
    if missing:
        raise ValueError(f"public APP executable inventory mismatch: missing={missing}")

    expected_xml = {f"bin/xml/{name}.xml" for name in contract.public_cli_apps}
    actual_xml = {
        name for name in members if name.casefold().startswith("bin/xml/") and name.casefold().endswith(".xml")
    }
    if actual_xml != expected_xml:
        raise ValueError(
            "CLI XML inventory mismatch: "
            f"missing={sorted(expected_xml - actual_xml)}, extra={sorted(actual_xml - expected_xml)}"
        )

    for required_pattern in contract.qt_plugin_globs:
        relative_pattern = required_pattern
        prefix = "Library/plugins/"
        if relative_pattern.startswith(prefix):
            relative_pattern = "plugins/" + relative_pattern[len(prefix):]
        if not any(fnmatch.fnmatchcase(name, relative_pattern) for name in members):
            raise ValueError(f"required Qt plugin pattern matched no archive member: {required_pattern}")
    for name, content in members.items():
        path = PurePosixPath(name)
        intrinsically_forbidden = (
            path.suffix.casefold() in {".a", ".lib", ".whl"}
            or name.casefold() == "cmakecache.txt"
            or name.casefold().endswith("/cmakecache.txt")
            or name.casefold().startswith(("include/", "make/", "lib/cmake/"))
        )
        if intrinsically_forbidden or any(
            fnmatch.fnmatchcase(name, pattern) for pattern in contract.forbidden_globs
        ):
            raise ValueError(f"forbidden archive member: {name}")
        if path.suffix.casefold() in TEXT_SUFFIXES and _contains_forbidden_absolute_path(content):
            raise ValueError(f"archive member contains an absolute build/conda path: {name}")


def _parse_files_manifest(content: bytes) -> dict[str, str]:
    try:
        text = content.decode("utf-8")
    except UnicodeError as error:
        raise ValueError("manifest/files.sha256 is not UTF-8") from error
    if not text.endswith("\n"):
        raise ValueError("manifest/files.sha256 must end with a newline")
    entries: dict[str, str] = {}
    folded: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), 1):
        if "  " not in line:
            raise ValueError(f"invalid files.sha256 line {line_number}")
        digest, name = line.split("  ", 1)
        if not SHA256_RE.fullmatch(digest) or not name:
            raise ValueError(f"invalid files.sha256 line {line_number}")
        parts = name.split("/")
        if any(part in {"", ".", ".."} for part in parts) or DRIVE_COMPONENT_RE.match(name):
            raise ValueError(f"unsafe files.sha256 path: {name}")
        key = name.casefold()
        if name in entries or key in folded:
            raise ValueError(f"duplicate files.sha256 path: {name}")
        entries[name] = digest
        folded.add(key)
    return entries


def _validate_files_manifest(members: dict[str, bytes]) -> None:
    manifest_name = "manifest/files.sha256"
    if manifest_name not in members:
        raise ValueError("archive is missing manifest/files.sha256")
    entries = _parse_files_manifest(members[manifest_name])
    expected = set(members) - {manifest_name}
    actual = set(entries)
    if actual != expected:
        raise ValueError(
            "files.sha256 inventory mismatch: "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )
    for name in sorted(expected):
        actual_digest = _sha256(members[name])
        if entries[name] != actual_digest:
            raise ValueError(
                f"payload hash mismatch for {name}: expected {entries[name]}, found {actual_digest}"
            )


def _safe_report_target(value: Any) -> str:
    if type(value) is not str or not value or "\\" in value:
        raise ValueError(f"unsafe dependency target: {value}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts) or value.startswith("/") or DRIVE_COMPONENT_RE.match(value):
        raise ValueError(f"unsafe dependency target: {value}")
    return PurePosixPath(value).as_posix()


def _validate_dependencies(
    payload: dict[str, Any], members: dict[str, bytes], contract: ReleaseContract
) -> int:
    _require_schema_one(payload, "dependency report")
    unresolved = payload.get("unresolved")
    if type(unresolved) is not list or any(type(name) is not str for name in unresolved):
        raise ValueError("dependency report unresolved must be a list of strings")
    if unresolved:
        raise ValueError(f"unresolved dependencies: {unresolved}")
    files = payload.get("files")
    binaries = payload.get("binaries")
    if type(files) is not list or type(binaries) is not list:
        raise ValueError("dependency report files and binaries must be lists")
    seen_targets: set[str] = set()
    for index, item in enumerate(files):
        if type(item) is not dict:
            raise ValueError(f"dependency report files[{index}] must be an object")
        target = _safe_report_target(item.get("target"))
        if not target.casefold().startswith("lib/") or PurePosixPath(target).suffix.casefold() != ".dll":
            raise ValueError(f"dependency target must be a lib DLL: {target}")
        dependency_name = item.get("name")
        if (
            type(dependency_name) is not str
            or PurePosixPath(target).name.casefold() != dependency_name.casefold()
        ):
            raise ValueError(f"dependency target/name binding mismatch: {target}")
        if target.casefold() in seen_targets:
            raise ValueError(f"duplicate dependency target: {target}")
        seen_targets.add(target.casefold())
        if target not in members:
            raise ValueError(f"dependency target is missing from archive: {target}")
        digest = item.get("sha256")
        if type(digest) is not str or not SHA256_RE.fullmatch(digest):
            raise ValueError(f"invalid dependency hash for {target}")
        actual = _sha256(members[target])
        if digest != actual:
            raise ValueError(f"dependency hash mismatch for {target}")
    binary_names: set[str] = set()
    for index, binary in enumerate(binaries):
        if type(binary) is not dict or type(binary.get("binary")) is not str or type(binary.get("imports")) is not list:
            raise ValueError(f"dependency report binaries[{index}] is invalid")
        binary_names.add(binary["binary"].casefold())
        for imported in binary["imports"]:
            if type(imported) is not dict or imported.get("classification") == "unresolved":
                raise ValueError("dependency report contains an unresolved import")
    expected_seeds = {
        f"{name}.exe".casefold()
        for name in (*contract.public_apps, *contract.runtime_helpers)
    }
    expected_seeds.add("isis.dll")
    expected_seeds.update(
        PurePosixPath(name).name.casefold()
        for name in members
        if name.casefold().startswith("plugins/") and name.casefold().endswith(".dll")
    )
    missing_seeds = sorted(expected_seeds - binary_names)
    if missing_seeds:
        raise ValueError(f"dependency report seed binding is incomplete: {missing_seeds}")
    return len(files)


def _nonnegative_integer(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _validate_runtime(
    payload: dict[str, Any], archive_name: str, archive_sha256: str
) -> tuple[int, int, int]:
    _require_schema_one(payload, "runtime report")
    artifact = payload.get("artifact")
    if type(artifact) is not dict:
        raise ValueError("runtime report artifact must be an object")
    if artifact.get("archive_name") != archive_name:
        raise ValueError("runtime report archive name mismatch")
    if artifact.get("archive_sha256") != archive_sha256:
        raise ValueError("runtime report archive SHA-256 mismatch (stale artifact binding)")
    host = payload.get("host")
    if (
        type(host) is not dict
        or type(host.get("os")) is not str
        or "Windows 11" not in host["os"]
    ):
        raise ValueError("runtime report host must be Windows 11")
    if host.get("architecture") not in {"x64", "AMD64"}:
        raise ValueError("runtime report host architecture must be x64")
    checks = payload.get("checks")
    if type(checks) is not dict:
        raise ValueError("runtime report checks must be an object")
    missing = [name for name in REQUIRED_CHECK_GROUPS if name not in checks]
    if missing:
        raise ValueError(f"runtime report missing required checks: {missing}")
    totals = [0, 0, 0]
    for name in REQUIRED_CHECK_GROUPS:
        check = checks[name]
        if type(check) is not dict:
            raise ValueError(f"required check {name} must be an object")
        passed = _nonnegative_integer(check.get("passed"), f"required check {name} passed")
        failed = _nonnegative_integer(check.get("failed"), f"required check {name} failed")
        skipped = _nonnegative_integer(check.get("skipped"), f"required check {name} skipped")
        if passed == 0:
            raise ValueError(f"required check {name} recorded no passing probe")
        if name == "cli-help" and passed != 150:
            raise ValueError(
                f"required check cli-help must contain exactly 150 passes, found {passed}"
            )
        if failed:
            raise ValueError(f"required check {name} failed")
        if skipped:
            raise ValueError(f"required check {name} skipped")
        exit_codes = check.get("exit_codes")
        if type(exit_codes) is not list or any(type(code) is not int for code in exit_codes):
            raise ValueError(f"required check {name} exit_codes must be a list of integers")
        if any(code != 0 for code in exit_codes):
            raise ValueError(f"required check {name} contains a nonzero exit code")
        totals[0] += passed
        totals[1] += failed
        totals[2] += skipped
    return tuple(totals)


def _contract_sha256(contract: ReleaseContract) -> str:
    payload = {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in vars(contract).items()
    }
    return _sha256(
        (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    )


def write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    """Atomically replace *path*, retaining any prior report on failure."""

    path = Path(path).absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    path = path.parent.resolve(strict=True) / path.name
    temporary = path.parent / f".{path.name}.tmp-{uuid.uuid4().hex}"
    if temporary.parent != path.parent:
        raise ValueError("report temporary path escaped its output directory")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def validate_release(
    archive: Path,
    dependency_report: Path,
    runtime_report: Path,
    release_contract: ReleaseContract,
    output_report: Path,
) -> dict[str, object]:
    """Validate all release artifacts and atomically publish schema-1 evidence."""

    archive = Path(archive)
    archive_content = archive.read_bytes()
    archive_sha256 = _sha256(archive_content)
    members, member_count = _read_archive(archive, release_contract)
    _validate_apps_manifest(members, release_contract)
    _validate_payload_inventory(members, release_contract)
    _validate_files_manifest(members)

    dependencies, dependency_content = _read_json(
        Path(dependency_report), "dependency report"
    )
    if _contains_forbidden_absolute_path(dependency_content):
        raise ValueError("dependency report contains an absolute build/conda path")
    dependency_count = _validate_dependencies(
        dependencies, members, release_contract
    )
    runtime, runtime_content = _read_json(Path(runtime_report), "runtime report")
    passed, failed, skipped = _validate_runtime(
        runtime, archive.name, archive_sha256
    )

    report: dict[str, object] = {
        "schema_version": 1,
        "validated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "distribution": release_contract.distribution,
        "isis_version": release_contract.isis_version,
        "platform": release_contract.platform,
        "archive": {
            "name": archive.name,
            "sha256": archive_sha256,
            "size": len(archive_content),
            "members": member_count,
            "payload_files": len(members),
        },
        "public_app_count": len(release_contract.public_apps),
        "public_cli_app_count": len(release_contract.public_cli_apps),
        "public_gui_app_count": len(release_contract.public_gui_apps),
        "dependency_closure": {
            "files": dependency_count,
            "unresolved": 0,
        },
        "tests": {"passed": passed, "failed": failed, "skipped": skipped},
        "inputs": {
            "release_contract_sha256": _contract_sha256(release_contract),
            "dependency_report_sha256": _sha256(dependency_content),
            "runtime_report_sha256": _sha256(runtime_content),
        },
    }
    write_json_atomic(Path(output_report), report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--dependency-report", required=True, type=Path)
    parser.add_argument("--runtime-report", required=True, type=Path)
    parser.add_argument("--release", required=True, type=Path)
    parser.add_argument("--cli-manifest", required=True, type=Path)
    parser.add_argument("--output-report", required=True, type=Path)
    args = parser.parse_args()
    contract = load_release_contract(args.release, args.cli_manifest)
    report = validate_release(
        args.archive,
        args.dependency_report,
        args.runtime_report,
        contract,
        args.output_report,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
