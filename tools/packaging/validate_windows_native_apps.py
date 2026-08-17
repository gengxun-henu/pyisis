"""Validate a Windows ISIS native-APP archive and its retained evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
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
    from tools.packaging.windows_pe_dependencies import _is_system_dependency
except ModuleNotFoundError:
    from windows_native_app_manifest import ReleaseContract, load_release_contract
    from windows_pe_dependencies import _is_system_dependency


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
WINDOWS_FORBIDDEN_CHARACTERS = frozenset('<>:"|?*')
WINDOWS_RESERVED_BASENAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
)
EXPECTED_RUNTIME_COUNTS = {
    "archive-extract": 1,
    "cli-help": 150,
    "real-operations": 9,
    "gui-launch": 3,
    "external-isisdata": 1,
    "negative-launcher": 2,
}
REAL_OPERATION_APPS = (
    "stats",
    "getkey",
    "catlab",
    "campt",
    "reduce",
    "cam2map",
    "isis2std",
    "cubeit",
    "fx",
)


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


def _require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ValueError(
            f"{label} keys mismatch: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


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
    for component in raw_parts:
        if (
            any(ord(character) < 32 for character in component)
            or any(character in WINDOWS_FORBIDDEN_CHARACTERS for character in component)
            or component.endswith((".", " "))
            or component.split(".", 1)[0].rstrip(" .").casefold()
            in WINDOWS_RESERVED_BASENAMES
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


def _windows_canonical_member(member: PurePosixPath) -> str:
    return "/".join(component.casefold() for component in member.parts)


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
                folded = _windows_canonical_member(member)
                if folded in folded_names:
                    raise ValueError(
                        "case-insensitive ZIP member collision: "
                        f"{folded_names[folded]} and {info.filename}"
                    )
                exact_names.add(info.filename)
                folded_names[folded] = info.filename
                mode = (info.external_attr >> 16) & 0xFFFF
                if (
                    info.is_dir()
                    or bool(info.external_attr & 0x10)
                    or (mode and not stat.S_ISREG(mode))
                ):
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

    # ISIS derives its application-definition filename from argv[0]. On
    # Windows that executable identity includes the .exe suffix.
    expected_xml = {f"bin/xml/{name}.exe.xml" for name in contract.public_cli_apps}
    actual_xml = {
        name for name in members if name.casefold().startswith("bin/xml/") and name.casefold().endswith(".xml")
    }
    if actual_xml != expected_xml:
        raise ValueError(
            "CLI XML inventory mismatch: "
            f"missing={sorted(expected_xml - actual_xml)}, extra={sorted(actual_xml - expected_xml)}"
        )

    plugin_patterns: list[str] = []
    for required_pattern in contract.qt_plugin_globs:
        relative_pattern = required_pattern
        prefix = "Library/plugins/"
        if relative_pattern.startswith(prefix):
            relative_pattern = "plugins/" + relative_pattern[len(prefix):]
        plugin_patterns.append(relative_pattern)
        if not any(fnmatch.fnmatchcase(name, relative_pattern) for name in members):
            raise ValueError(f"required Qt plugin pattern matched no archive member: {required_pattern}")
    for name, content in members.items():
        path = PurePosixPath(name)
        if (
            name.casefold().startswith("plugins/")
            and path.suffix.casefold() == ".dll"
            and not any(fnmatch.fnmatchcase(name, pattern) for pattern in plugin_patterns)
        ):
            raise ValueError(f"undeclared Qt plugin archive member: {name}")
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


def _safe_dependency_name(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or not value
        or "/" in value
        or "\\" in value
        or any(ord(character) < 32 for character in value)
        or any(character in WINDOWS_FORBIDDEN_CHARACTERS for character in value)
        or value.endswith((".", " "))
        or value.split(".", 1)[0].casefold() in WINDOWS_RESERVED_BASENAMES
    ):
        raise ValueError(f"unsafe {label}: {value}")
    return value


def _safe_dependency_source(value: Any) -> str:
    if type(value) is not str or not value or "\\" in value or value.startswith("/"):
        raise ValueError(f"unsafe dependency source: {value}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts) or any(
        DRIVE_COMPONENT_RE.match(part) for part in parts
    ):
        raise ValueError(f"unsafe dependency source: {value}")
    return PurePosixPath(value).as_posix()


def _validate_dependencies(
    payload: dict[str, Any], members: dict[str, bytes], contract: ReleaseContract
) -> int:
    _require_exact_keys(
        payload,
        {"schema_version", "binaries", "files", "unresolved"},
        "dependency report",
    )
    _require_schema_one(payload, "dependency report")
    unresolved = payload.get("unresolved")
    if type(unresolved) is not list or any(type(name) is not str for name in unresolved):
        raise ValueError("dependency report unresolved must be a list of strings")
    if len({name.casefold() for name in unresolved}) != len(unresolved):
        raise ValueError("dependency report unresolved contains duplicate names")
    if unresolved:
        raise ValueError(f"unresolved dependencies: {unresolved}")
    files = payload.get("files")
    binaries = payload.get("binaries")
    if type(files) is not list or type(binaries) is not list:
        raise ValueError("dependency report files and binaries must be lists")
    binary_names: dict[str, str] = {}
    import_edges: dict[tuple[str, str], str] = {}
    for index, binary in enumerate(binaries):
        if type(binary) is not dict:
            raise ValueError(f"dependency report binaries[{index}] must be an object")
        _require_exact_keys(binary, {"binary", "imports"}, "dependency binary")
        binary_name = _safe_dependency_name(binary["binary"], "dependency binary name")
        normalized_binary = binary_name.casefold()
        if normalized_binary in binary_names:
            raise ValueError(f"duplicate dependency binary: {binary_name}")
        binary_names[normalized_binary] = binary_name
        imports = binary["imports"]
        if type(imports) is not list:
            raise ValueError("dependency binary imports must be a list")
        import_names: set[str] = set()
        for imported in imports:
            if type(imported) is not dict:
                raise ValueError("dependency import must be an object")
            _require_exact_keys(
                imported,
                {"name", "import_kind", "classification"},
                "dependency import",
            )
            imported_name = _safe_dependency_name(
                imported["name"], "dependency import name"
            )
            if PureWindowsPath(imported_name).suffix.casefold() != ".dll":
                raise ValueError(f"dependency import name is not a DLL: {imported_name}")
            normalized_import = imported_name.casefold()
            if normalized_import in import_names:
                raise ValueError(f"duplicate dependency import: {imported_name}")
            import_names.add(normalized_import)
            if type(imported["import_kind"]) is not str or imported["import_kind"] not in {
                "direct",
                "forwarder",
            }:
                raise ValueError(
                    f"dependency import_kind is invalid: {imported['import_kind']}"
                )
            if type(imported["classification"]) is not str or imported["classification"] not in {
                "system",
                "packaged",
                "resolved",
                "unresolved",
            }:
                raise ValueError(
                    "dependency import classification is invalid: "
                    f"{imported['classification']}"
                )
            if imported["classification"] == "unresolved":
                raise ValueError("dependency report contains an unresolved import")
            classified_system = imported["classification"] == "system"
            expected_system = _is_system_dependency(imported_name)
            if classified_system != expected_system:
                raise ValueError(
                    "dependency system classification mismatch for "
                    f"{imported_name}: {imported['classification']}"
                )
            import_edges[(normalized_binary, normalized_import)] = imported[
                "classification"
            ]

    seen_names: set[str] = set()
    seen_sources: set[str] = set()
    seen_targets: set[str] = set()
    closure_names: set[str] = set()
    closure_targets: set[str] = set()
    closure_parents: dict[str, set[str]] = {}
    for index, item in enumerate(files):
        if type(item) is not dict:
            raise ValueError(f"dependency report files[{index}] must be an object")
        _require_exact_keys(
            item,
            {"name", "source", "target", "import_kind", "parents", "sha256"},
            "dependency file",
        )
        target = _safe_report_target(item.get("target"))
        if not target.casefold().startswith("lib/") or PurePosixPath(target).suffix.casefold() != ".dll":
            raise ValueError(f"dependency target must be a lib DLL: {target}")
        dependency_name = _safe_dependency_name(item.get("name"), "dependency name")
        source = _safe_dependency_source(item.get("source"))
        if target.casefold() != f"lib/{dependency_name}".casefold():
            raise ValueError(f"dependency target/name binding mismatch: {target}")
        normalized_name = dependency_name.casefold()
        normalized_source = source.casefold()
        if normalized_name in seen_names:
            raise ValueError(f"duplicate dependency name: {dependency_name}")
        if normalized_source in seen_sources:
            raise ValueError(f"duplicate dependency source: {source}")
        if target.casefold() in seen_targets:
            raise ValueError(f"duplicate dependency target: {target}")
        seen_names.add(normalized_name)
        seen_sources.add(normalized_source)
        seen_targets.add(target.casefold())
        closure_names.add(normalized_name)
        closure_targets.add(target.casefold())
        if type(item["import_kind"]) is not str or item["import_kind"] not in {
            "direct",
            "forwarder",
        }:
            raise ValueError(f"dependency file import_kind is invalid: {item['import_kind']}")
        parents = item["parents"]
        if type(parents) is not list or not parents or any(
            type(parent) is not str for parent in parents
        ):
            raise ValueError("dependency file parents must be a non-empty string list")
        checked_parents = [
            _safe_dependency_name(parent, "dependency parent") for parent in parents
        ]
        normalized_parents = [parent.casefold() for parent in checked_parents]
        if len(set(normalized_parents)) != len(normalized_parents):
            raise ValueError(f"duplicate dependency parent for {dependency_name}")
        if not set(normalized_parents) <= set(binary_names):
            raise ValueError(f"unknown dependency parent for {dependency_name}")
        closure_parents[normalized_name] = set(normalized_parents)
        if target not in members:
            raise ValueError(f"dependency target is missing from archive: {target}")
        digest = item.get("sha256")
        if type(digest) is not str or not SHA256_RE.fullmatch(digest):
            raise ValueError(f"invalid dependency hash for {target}")
        actual = _sha256(members[target])
        if digest != actual:
            raise ValueError(f"dependency hash mismatch for {target}")
    authoritative_seeds = {
        f"{name}.exe".casefold()
        for name in (*contract.public_apps, *contract.runtime_helpers)
    }
    authoritative_seeds.add("isis.dll")
    plugin_dll_names = {
        PurePosixPath(name).name.casefold()
        for name in members
        if name.casefold().startswith("plugins/") and name.casefold().endswith(".dll")
    }
    authoritative_seeds.update(plugin_dll_names)
    expected_binaries = set(authoritative_seeds)
    expected_binaries.update(closure_names)
    actual_binaries = set(binary_names)
    if actual_binaries != expected_binaries:
        raise ValueError(
            "dependency binary inventory mismatch: "
            f"missing={sorted(expected_binaries - actual_binaries)}, "
            f"extra={sorted(actual_binaries - expected_binaries)}"
        )

    known_packaged_dlls = {"isis.dll", *plugin_dll_names, *closure_names}
    resolved_edges_by_name: dict[str, set[str]] = {
        name: set() for name in closure_names
    }
    closure_edges_by_name: dict[str, set[str]] = {
        name: set() for name in closure_names
    }
    for (parent, imported_name), classification in import_edges.items():
        if classification == "resolved":
            if imported_name not in closure_names:
                raise ValueError(
                    f"resolved import {imported_name} has no unique closure file"
                )
            if imported_name not in binary_names:
                raise ValueError(
                    f"resolved import {imported_name} has no dependency binary"
                )
            resolved_edges_by_name[imported_name].add(parent)
            closure_edges_by_name[imported_name].add(parent)
        elif classification == "packaged":
            if imported_name not in known_packaged_dlls:
                raise ValueError(
                    f"packaged import {imported_name} has no known staged DLL"
                )
            if imported_name in closure_names:
                closure_edges_by_name[imported_name].add(parent)

    for name in sorted(closure_names):
        resolved_parents = resolved_edges_by_name[name]
        if not resolved_parents:
            raise ValueError(f"orphaned dependency file without resolved edge: {name}")
        declared_parents = closure_parents[name]
        edge_parents = closure_edges_by_name[name]
        if declared_parents != edge_parents:
            raise ValueError(
                f"dependency parent/import disagreement for {name}: "
                f"declared={sorted(declared_parents)}, edges={sorted(edge_parents)}"
            )

    reachable_binaries = set(authoritative_seeds)
    pending = list(sorted(authoritative_seeds))
    while pending:
        parent = pending.pop(0)
        for (edge_parent, imported_name), classification in import_edges.items():
            if (
                edge_parent == parent
                and classification in {"resolved", "packaged"}
                and imported_name in closure_names
                and imported_name in binary_names
                and imported_name not in reachable_binaries
            ):
                reachable_binaries.add(imported_name)
                pending.append(imported_name)
    unreachable = sorted(closure_names - reachable_binaries)
    if unreachable:
        raise ValueError(
            "dependency closure files are not reachable from authoritative seeds: "
            f"{unreachable}"
        )

    actual_archive_dlls = {
        name.casefold()
        for name in members
        if PurePosixPath(name).suffix.casefold() == ".dll"
    }
    expected_archive_dlls = {"lib/isis.dll", *closure_targets}
    expected_archive_dlls.update(
        name.casefold()
        for name in members
        if name.casefold().startswith("plugins/") and name.casefold().endswith(".dll")
    )
    if actual_archive_dlls != expected_archive_dlls:
        raise ValueError(
            "archive DLL inventory mismatch: "
            f"missing={sorted(expected_archive_dlls - actual_archive_dlls)}, "
            f"extra={sorted(actual_archive_dlls - expected_archive_dlls)}"
        )
    return len(files)


def _nonnegative_integer(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _looks_like_absolute_path(value: str) -> bool:
    return (
        PureWindowsPath(value).is_absolute()
        or PurePosixPath(value).is_absolute()
        or re.search(r"(?i)(?:^|[\s=\"])(?:[a-z]:[\\/]|\\\\)", value)
        is not None
    )


def _reject_absolute_strings(
    value: Any, label: str, path: tuple[str, ...] = (), exempt: set[tuple[str, ...]] | None = None
) -> None:
    exempt = exempt or set()
    if type(value) is str:
        if path not in exempt and _looks_like_absolute_path(value):
            raise ValueError(f"{label} contains an absolute path outside extraction_path")
        return
    if type(value) is dict:
        for key, child in value.items():
            _reject_absolute_strings(child, label, (*path, str(key)), exempt)
    elif type(value) is list:
        for index, child in enumerate(value):
            _reject_absolute_strings(child, label, (*path, str(index)), exempt)


def _validate_clean_extraction_path(value: Any) -> str:
    if type(value) is not str or not value:
        raise ValueError("runtime extraction_path must be a non-empty string")
    path = PureWindowsPath(value)
    if not path.is_absolute() or not path.drive or path.name != "native package with spaces":
        raise ValueError("runtime extraction_path must be a clean absolute Windows path")
    forbidden_components = {
        "build",
        "src",
        "source",
        "sources",
        ".worktrees",
        "conda",
        "miniconda",
        "miniconda3",
        "pyisis-win-env",
    }
    components = [component for component in path.parts if component not in {path.anchor, path.drive}]
    for component in components:
        normalized = component.casefold()
        if (
            normalized in forbidden_components
            or normalized.startswith(
                ("build-", "build_", "conda-", "miniconda-", "source-", "source_")
            )
            or normalized.endswith(("-source", "_source"))
            or any(ord(character) < 32 for character in component)
            or any(character in WINDOWS_FORBIDDEN_CHARACTERS for character in component)
            or component.endswith((".", " "))
            or component.split(".", 1)[0].rstrip(" .").casefold()
            in WINDOWS_RESERVED_BASENAMES
        ):
            raise ValueError("runtime extraction_path must be a clean absolute Windows path")
    return value


def canonical_runtime_commands(
    contract: ReleaseContract,
) -> dict[str, tuple[str, ...]]:
    """Return the frozen package-relative identities for the Task 6 probes."""

    return {
        "archive-extract": ("archive-extract",),
        "cli-help": tuple(
            f"launch/isis-app.cmd {name} -HELP"
            for name in sorted(contract.public_cli_apps)
        ),
        "real-operations": tuple(
            f"launch/isis-app.cmd {name} mode=real-operation"
            for name in REAL_OPERATION_APPS
        ),
        "gui-launch": (
            "launch/isis-app.cmd reduce -gui",
            "launch/isis-app.cmd jigsaw -gui",
            "launch/qnet.cmd",
        ),
        "external-isisdata": (
            "launch/isis-app.cmd stats isisdata=external",
        ),
        "negative-launcher": (
            "launch/isis-app.cmd __undeclared_app__ isisdata=bundled",
            "launch/isis-app.cmd stats isisdata=missing",
        ),
    }


def _validate_runtime(
    payload: dict[str, Any],
    archive_name: str,
    archive_sha256: str,
    contract: ReleaseContract,
) -> tuple[int, int, int]:
    _require_exact_keys(
        payload,
        {
            "schema_version",
            "artifact",
            "host",
            "extraction_path",
            "scrubbed_environment",
            "checks",
            "summary",
        },
        "runtime report",
    )
    _require_schema_one(payload, "runtime report")
    _reject_absolute_strings(
        payload,
        "runtime report",
        exempt={("extraction_path",)},
    )
    artifact = payload.get("artifact")
    if type(artifact) is not dict:
        raise ValueError("runtime report artifact must be an object")
    _require_exact_keys(
        artifact, {"archive_name", "archive_sha256"}, "runtime artifact"
    )
    if artifact.get("archive_name") != archive_name:
        raise ValueError("runtime report archive name mismatch")
    if type(artifact.get("archive_sha256")) is not str or not SHA256_RE.fullmatch(
        artifact["archive_sha256"]
    ):
        raise ValueError("runtime report archive SHA-256 is invalid")
    if artifact.get("archive_sha256") != archive_sha256:
        raise ValueError("runtime report archive SHA-256 mismatch (stale artifact binding)")
    host = payload.get("host")
    if type(host) is not dict:
        raise ValueError("runtime report host must be an object")
    _require_exact_keys(host, {"os", "version", "architecture"}, "runtime host")
    if (
        type(host.get("os")) is not str
        or host["os"].casefold() != "windows 11"
    ):
        raise ValueError("runtime report host must be Windows 11")
    if (
        type(host.get("version")) is not str
        or re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}", host["version"]) is None
    ):
        raise ValueError("runtime report host version is not a reasonable Windows version")
    if type(host.get("architecture")) is not str or host["architecture"] not in {
        "x64",
        "AMD64",
    }:
        raise ValueError("runtime report host architecture must be x64")
    _validate_clean_extraction_path(payload["extraction_path"])

    scrubbed = payload["scrubbed_environment"]
    if type(scrubbed) is not dict:
        raise ValueError("runtime scrubbed_environment must be an object")
    _require_exact_keys(
        scrubbed,
        {"variables", "path_entries_removed"},
        "runtime scrubbed_environment",
    )
    expected_variables = (
        "CONDA_PREFIX",
        "ISISROOT",
        "ISIS_PREFIX",
        "ISISDATA",
        "QT_PLUGIN_PATH",
    )
    variables = _require_string_list(
        scrubbed["variables"], "runtime scrubbed variables"
    )
    if variables != expected_variables:
        raise ValueError(
            f"runtime scrubbed variables mismatch: expected {list(expected_variables)}"
        )
    _nonnegative_integer(
        scrubbed["path_entries_removed"], "runtime path_entries_removed"
    )

    checks = payload.get("checks")
    if type(checks) is not dict:
        raise ValueError("runtime report checks must be an object")
    if set(checks) != set(REQUIRED_CHECK_GROUPS):
        raise ValueError(
            "runtime check groups mismatch: "
            f"missing={sorted(set(REQUIRED_CHECK_GROUPS) - set(checks))}, "
            f"extra={sorted(set(checks) - set(REQUIRED_CHECK_GROUPS))}"
        )
    totals = [0, 0, 0]
    expected_commands = canonical_runtime_commands(contract)
    for name in REQUIRED_CHECK_GROUPS:
        check = checks[name]
        if type(check) is not dict:
            raise ValueError(f"required check {name} must be an object")
        _require_exact_keys(
            check,
            {"commands", "passed", "failed", "skipped", "exit_codes"},
            f"required check {name}",
        )
        expected_count = EXPECTED_RUNTIME_COUNTS[name]
        passed = _nonnegative_integer(check.get("passed"), f"required check {name} passed")
        failed = _nonnegative_integer(check.get("failed"), f"required check {name} failed")
        skipped = _nonnegative_integer(check.get("skipped"), f"required check {name} skipped")
        if passed != expected_count:
            raise ValueError(
                f"required check {name} must record exactly {expected_count} passes, found {passed}"
            )
        if failed:
            raise ValueError(f"required check {name} failed")
        if skipped:
            raise ValueError(f"required check {name} skipped")
        commands = check["commands"]
        if (
            type(commands) is not list
            or any(type(command) is not str or not command for command in commands)
            or len(commands) != expected_count
        ):
            raise ValueError(
                f"required check {name} commands must contain exactly {expected_count} strings"
            )
        if len({command.casefold() for command in commands}) != len(commands):
            raise ValueError(f"required check {name} commands contain duplicates")
        if any(
            any(ord(character) < 32 for character in command)
            for command in commands
        ):
            raise ValueError(f"required check {name} command contains a control character")
        if any(
            _looks_like_absolute_path(command)
            or re.search(r"(?:^|[\\/])\.\.(?:[\\/]|$)", command) is not None
            for command in commands
        ):
            raise ValueError("runtime report contains an absolute path outside extraction_path")
        if tuple(commands) != expected_commands[name]:
            raise ValueError(f"required check {name} command identities mismatch")
        exit_codes = check.get("exit_codes")
        if (
            type(exit_codes) is not list
            or any(type(code) is not int for code in exit_codes)
            or len(exit_codes) != expected_count
        ):
            raise ValueError(
                f"required check {name} exit_codes must contain exactly {expected_count} integers"
            )
        expected_exit_codes = [4, 3] if name == "negative-launcher" else [0] * expected_count
        if exit_codes != expected_exit_codes:
            if name == "negative-launcher":
                raise ValueError("required check negative-launcher expected exit codes [4, 3]")
            raise ValueError(f"required check {name} contains a nonzero exit code")
        totals[0] += passed
        totals[1] += failed
        totals[2] += skipped

    summary = payload["summary"]
    if type(summary) is not dict:
        raise ValueError("runtime summary must be an object")
    _require_exact_keys(summary, {"passed", "failed", "skipped"}, "runtime summary")
    expected_summary = {"passed": 166, "failed": 0, "skipped": 0}
    if any(type(summary.get(key)) is not int for key in expected_summary) or summary != expected_summary:
        raise ValueError(
            f"runtime summary mismatch: expected {expected_summary}, found {summary}"
        )
    if tuple(totals) != (166, 0, 0):
        raise ValueError(f"runtime check totals mismatch: {totals}")
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
    _reject_absolute_strings(dependencies, "dependency report")
    dependency_count = _validate_dependencies(
        dependencies, members, release_contract
    )
    runtime, runtime_content = _read_json(Path(runtime_report), "runtime report")
    passed, failed, skipped = _validate_runtime(
        runtime, archive.name, archive_sha256, release_contract
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
