"""Load and validate the Windows ISIS native APP release contract."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


_RELEASE_KEYS = {
    "schema_version",
    "distribution",
    "isis_version",
    "platform",
    "archive_name",
    "root_name",
    "cli_manifest",
    "cli_manifest_sha256",
    "public_gui_apps",
    "runtime_helpers",
    "mandatory_apps",
    "qt_plugin_globs",
    "forbidden_globs",
}
_STRING_FIELDS = {
    "distribution",
    "isis_version",
    "platform",
    "archive_name",
    "root_name",
    "cli_manifest",
    "cli_manifest_sha256",
}
_STRING_LIST_FIELDS = {
    "public_gui_apps",
    "runtime_helpers",
    "mandatory_apps",
    "qt_plugin_globs",
    "forbidden_globs",
}


@dataclass(frozen=True)
class ReleaseContract:
    distribution: str
    isis_version: str
    platform: str
    archive_name: str
    root_name: str
    public_cli_apps: tuple[str, ...]
    public_gui_apps: tuple[str, ...]
    runtime_helpers: tuple[str, ...]
    mandatory_apps: tuple[str, ...]
    qt_plugin_globs: tuple[str, ...]
    forbidden_globs: tuple[str, ...]

    @property
    def public_apps(self) -> tuple[str, ...]:
        return tuple(sorted((*self.public_cli_apps, *self.public_gui_apps)))


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"unable to read JSON from {path}: {error}") from error
    if type(value) is not dict:
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"{label} keys mismatch: missing={missing}, extra={extra}")


def _require_string_list(value: Any, field: str) -> tuple[str, ...]:
    if type(value) is not list or any(type(item) is not str for item in value):
        raise ValueError(f"{field} must be a list of strings")
    result = tuple(value)
    if len(result) != len(set(result)):
        raise ValueError(f"{field} must not contain duplicates")
    return result


def _normalized_sha256(path: Path) -> str:
    try:
        content = path.read_bytes()
    except OSError as error:
        raise ValueError(f"unable to read CLI manifest {path}: {error}") from error
    normalized = content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def _validate_release_data(value: dict[str, Any]) -> dict[str, Any]:
    _require_exact_keys(value, _RELEASE_KEYS, "release contract")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("schema_version must be integer 1")
    for field in _STRING_FIELDS:
        if type(value[field]) is not str or not value[field]:
            raise ValueError(f"{field} must be a non-empty string")
    if value["isis_version"] != "9.0.0":
        raise ValueError("isis_version must be 9.0.0")
    if value["platform"] != "win64":
        raise ValueError("platform must be win64")
    for field in _STRING_LIST_FIELDS:
        value[field] = _require_string_list(value[field], field)
    return value


def _manifest_cli_apps(value: dict[str, Any], isis_version: str) -> tuple[str, ...]:
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ValueError("CLI manifest schema_version must be integer 1")
    apps = value.get("apps")
    if type(apps) is not list:
        raise ValueError("CLI manifest apps must be a list")
    if len(apps) != 150:
        raise ValueError(f"CLI manifest must contain exactly 150 APPs, found {len(apps)}")

    names: list[str] = []
    for index, app in enumerate(apps):
        if type(app) is not dict:
            raise ValueError(f"CLI manifest apps[{index}] must be an object")
        name = app.get("name")
        if type(name) is not str or not name or name != name.lower():
            raise ValueError(f"CLI manifest apps[{index}].name must be lower-case")
        if not name.isascii() or not name.isalnum():
            raise ValueError(f"CLI manifest APP name is invalid: {name!r}")
        versions = app.get("versions")
        if type(versions) is not dict:
            raise ValueError(f"CLI manifest APP {name} versions must be an object")
        version = versions.get(isis_version)
        if type(version) is not dict:
            raise ValueError(f"CLI manifest APP {name} lacks ISIS {isis_version} status")
        if version.get("status") != "supported":
            raise ValueError(f"CLI manifest APP {name} is not supported for ISIS {isis_version}")
        if version.get("build_status") != "compiled_installed":
            raise ValueError(
                f"CLI manifest APP {name} is not compiled_installed for ISIS {isis_version}"
            )
        names.append(name)

    if len(names) != len(set(names)):
        raise ValueError("CLI manifest APP names must be unique")
    return tuple(sorted(names))


def load_release_contract(release_path: Path, cli_manifest_path: Path) -> ReleaseContract:
    """Load a release contract and fail closed if its pinned CLI inventory drifts."""

    release_path = Path(release_path)
    cli_manifest_path = Path(cli_manifest_path)
    release = _validate_release_data(_load_json(release_path))
    actual_sha256 = _normalized_sha256(cli_manifest_path)
    if actual_sha256 != release["cli_manifest_sha256"]:
        raise ValueError(
            "CLI manifest SHA-256 mismatch: "
            f"expected {release['cli_manifest_sha256']}, found {actual_sha256}"
        )

    public_cli_apps = _manifest_cli_apps(
        _load_json(cli_manifest_path), release["isis_version"]
    )
    public_gui_apps = release["public_gui_apps"]
    runtime_helpers = release["runtime_helpers"]
    cli = set(public_cli_apps)
    gui = set(public_gui_apps)
    helpers = set(runtime_helpers)
    overlaps = {
        "CLI/GUI": sorted(cli & gui),
        "CLI/helper": sorted(cli & helpers),
        "GUI/helper": sorted(gui & helpers),
    }
    active_overlaps = {key: value for key, value in overlaps.items() if value}
    if active_overlaps:
        raise ValueError(f"release APP/helper overlap: {active_overlaps}")

    public_apps = cli | gui
    missing_mandatory = sorted(set(release["mandatory_apps"]) - public_apps)
    if missing_mandatory:
        raise ValueError(f"mandatory APPs are not public: {missing_mandatory}")

    return ReleaseContract(
        distribution=release["distribution"],
        isis_version=release["isis_version"],
        platform=release["platform"],
        archive_name=release["archive_name"],
        root_name=release["root_name"],
        public_cli_apps=public_cli_apps,
        public_gui_apps=public_gui_apps,
        runtime_helpers=runtime_helpers,
        mandatory_apps=release["mandatory_apps"],
        qt_plugin_globs=release["qt_plugin_globs"],
        forbidden_globs=release["forbidden_globs"],
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--cli-manifest", type=Path, required=True)
    parser.add_argument("--check", action="store_true", required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    contract = load_release_contract(args.release, args.cli_manifest)
    print(f"{len(contract.public_apps)} public APPs validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
