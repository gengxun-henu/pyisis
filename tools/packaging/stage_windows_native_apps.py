"""Stage the curated Windows ISIS native-application payload."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import stat
from tempfile import TemporaryDirectory
import uuid

try:
    from tools.packaging.windows_native_app_manifest import (
        ReleaseContract,
        load_release_contract,
    )
    from tools.packaging.windows_pe_dependencies import copy_dependency_closure
except ModuleNotFoundError:
    from windows_native_app_manifest import ReleaseContract, load_release_contract
    from windows_pe_dependencies import copy_dependency_closure


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LAUNCH_SOURCE = REPOSITORY_ROOT / "packaging" / "native-apps-win64" / "launch"
VALIDATION_DATA_SOURCE = REPOSITORY_ROOT / "tests" / "data" / "mosrange"
VALIDATION_DATA_FILES = ("EN0108828322M_iof.cub", "equi.map")
LAUNCH_FILES = (
    "isis-app.cmd",
    "isis-env.cmd",
    "isis-launch.ps1",
    "isis-shell.cmd",
    "qnet.cmd",
)
TEXT_SUFFIXES = {"", ".cmd", ".json", ".md", ".plugin", ".ps1", ".sha256", ".txt", ".xml"}
FORBIDDEN_ABSOLUTE_RE = re.compile(
    rb"(?i)[a-z]:[\\/](?:[^\\/\x00\r\n]+[\\/])*"
    rb"(?:build|conda|miniconda|pyisis-win-env)"
    rb"(?=[\\/ \t\r\n\"',;}\]]|$)"
)


@dataclass(frozen=True)
class StageResult:
    root: Path
    apps_manifest: Path
    files_manifest: Path
    dependency_report: Path


def _is_reparse_point(path: Path) -> bool:
    attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _reject_reparse_below(path: Path, root: Path, label: str) -> None:
    current = Path(path).absolute()
    root = Path(root).absolute()
    try:
        current.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} escapes declared source root: {path}") from error
    while True:
        if os.path.lexists(current) and _is_reparse_point(current):
            raise ValueError(f"{label} contains a symlink or reparse point: {current}")
        if current == root:
            return
        current = current.parent


def _reject_reparse_tree(path: Path, label: str) -> None:
    if _is_reparse_point(path):
        raise ValueError(f"{label} contains a symlink or reparse point: {path}")
    if Path(path).is_dir():
        for entry in Path(path).rglob("*"):
            if _is_reparse_point(entry):
                raise ValueError(
                    f"{label} contains a symlink or reparse point: {entry}"
                )


def _unique_sibling(path: Path, kind: str) -> Path:
    return path.parent / f".{path.name}.{kind}-{uuid.uuid4().hex}"


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


def _require_direct_child(path: Path, parent: Path, label: str) -> None:
    if path.parent != parent or path.name in {"", ".", ".."}:
        raise ValueError(f"{label} is not a safe sibling temporary path: {path}")


def _publish_outputs(outputs: tuple[tuple[Path, Path], ...]) -> None:
    records: list[dict[str, object]] = []
    try:
        for candidate, final in outputs:
            candidate = candidate.absolute()
            final = final.absolute()
            _require_direct_child(candidate, final.parent, "publish candidate")
            if not os.path.lexists(candidate):
                raise FileNotFoundError(f"publish candidate does not exist: {candidate}")
            backup: Path | None = None
            record: dict[str, object] = {
                "final": final,
                "backup": backup,
                "published": False,
            }
            records.append(record)
            if os.path.lexists(final):
                backup = _unique_sibling(final, "backup")
                _require_direct_child(backup, final.parent, "publish backup")
                os.replace(final, backup)
                record["backup"] = backup
            os.replace(candidate, final)
            record["published"] = True
    except BaseException:
        rollback_error: BaseException | None = None
        for record in reversed(records):
            final = record["final"]
            backup = record["backup"]
            try:
                if record["published"] and os.path.lexists(final):
                    _remove_path(final)
                if isinstance(backup, Path) and os.path.lexists(backup):
                    os.replace(backup, final)
            except BaseException as error:
                rollback_error = rollback_error or error
        if rollback_error is not None:
            raise RuntimeError("failed to restore previous published outputs") from rollback_error
        raise
    else:
        for record in records:
            backup = record["backup"]
            if isinstance(backup, Path):
                _remove_path(backup)


def _existing_directory(path: Path, label: str) -> Path:
    try:
        resolved = Path(path).resolve(strict=True)
    except OSError as error:
        raise FileNotFoundError(f"{label} not found: {path}") from error
    if not resolved.is_dir():
        raise NotADirectoryError(f"{label} is not a directory: {path}")
    return resolved


def _require_below(path: Path, root: Path, label: str) -> Path:
    _reject_reparse_below(path, root, label)
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} escapes declared source root: {path}") from error
    return resolved


def _destination(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe staging destination: {relative}")
    target = root.joinpath(*relative.parts)
    try:
        target.resolve(strict=False).relative_to(root)
    except ValueError as error:
        raise ValueError(f"staging destination escapes package root: {relative}") from error
    return target


def _copy_file(source: Path, source_root: Path, stage_root: Path, relative: Path) -> Path:
    source = _require_below(source, source_root, "payload file")
    if not source.is_file():
        raise FileNotFoundError(f"required payload file not found: {source}")
    target = _destination(stage_root, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def _copy_tree(source: Path, source_root: Path, target_root: Path) -> None:
    source = _require_below(source, source_root, "payload directory")
    if not source.is_dir():
        raise FileNotFoundError(f"required payload directory not found: {source}")
    for item in sorted(source.rglob("*"), key=lambda value: value.relative_to(source).as_posix()):
        if item.is_symlink():
            _require_below(item, source_root, "payload symlink")
        if item.is_file():
            relative = item.relative_to(source)
            _copy_file(item, source_root, target_root, relative)


def write_apps_manifest(root: Path, contract: ReleaseContract) -> Path:
    path = root / "manifest" / "apps.json"
    payload = {
        "schema_version": 1,
        "distribution": contract.distribution,
        "isis_version": contract.isis_version,
        "platform": contract.platform,
        "public_cli_apps": list(contract.public_cli_apps),
        "public_gui_apps": list(contract.public_gui_apps),
        "public_apps": list(contract.public_apps),
        "runtime_helpers": list(contract.runtime_helpers),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_build_metadata(root: Path, contract: ReleaseContract) -> Path:
    path = root / "manifest" / "build-metadata.json"
    payload = {
        "schema_version": 1,
        "distribution": contract.distribution,
        "isis_version": contract.isis_version,
        "platform": contract.platform,
        "public_app_count": len(contract.public_apps),
        "runtime_helpers": list(contract.runtime_helpers),
        "generated_manifests_hashed": [
            "manifest/apps.json",
            "manifest/build-metadata.json",
        ],
        "files_manifest_excludes": ["manifest/files.sha256"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_package_readme(root: Path, contract: ReleaseContract) -> Path:
    path = root / "README.md"
    path.write_text(
        f"# USGS ISIS {contract.isis_version} native APPs for Windows 11 x64\n\n"
        "Run `launch\\isis-shell.cmd` for an initialized command prompt, "
        "`launch\\isis-app.cmd <name> [arguments]` for a public APP, or "
        "`launch\\qnet.cmd` for qnet. The bundled minimal data is used unless "
        "ISISDATA already names an existing external data directory.\n",
        encoding="utf-8",
    )
    return path


def _write_files_manifest(root: Path) -> Path:
    path = root / "manifest" / "files.sha256"
    members = sorted(
        (
            item
            for item in root.rglob("*")
            if item.is_file() and item != path
        ),
        key=lambda item: item.relative_to(root).as_posix(),
    )
    lines = [
        f"{hashlib.sha256(item.read_bytes()).hexdigest()}  {item.relative_to(root).as_posix()}"
        for item in members
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _enrich_dependency_report(report: dict[str, object], lib_root: Path) -> None:
    for item in report.get("files", []):
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError("dependency report contains an invalid file entry")
        target = lib_root / item["name"]
        if not target.is_file():
            raise FileNotFoundError(f"staged dependency missing: {item['name']}")
        item["target"] = f"lib/{item['name']}"
        item["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()


def _reject_forbidden_content(root: Path, contract: ReleaseContract) -> None:
    for pattern in contract.forbidden_globs:
        matches = [path for path in root.glob(pattern) if path.exists()]
        if matches:
            raise ValueError(f"forbidden staged content matches {pattern}: {matches[0]}")
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            if FORBIDDEN_ABSOLUTE_RE.search(path.read_bytes()):
                raise ValueError(f"staged file contains an absolute build/conda path: {path}")


def stage_native_apps(
    isis_prefix: Path,
    dependency_prefixes: tuple[Path, ...],
    minimal_data_root: Path,
    release_contract: ReleaseContract,
    stage_parent: Path,
    dependency_report: Path,
) -> StageResult:
    """Create one fail-closed portable payload below *stage_parent*."""

    isis_prefix = _existing_directory(isis_prefix, "ISIS prefix")
    minimal_data_root = _existing_directory(minimal_data_root, "minimal data root")
    validation_data_source = _existing_directory(
        VALIDATION_DATA_SOURCE, "validation data source"
    )
    dependency_prefixes = tuple(
        _existing_directory(path, "dependency prefix") for path in dependency_prefixes
    )
    stage_parent = Path(stage_parent)
    stage_parent.mkdir(parents=True, exist_ok=True)
    stage_parent = stage_parent.resolve(strict=True)

    root_name = release_contract.root_name
    if not root_name or Path(root_name).name != root_name or root_name in {".", ".."}:
        raise ValueError(f"unsafe release root_name: {root_name!r}")
    final_root = _destination(stage_parent, Path(root_name))
    if os.path.lexists(final_root):
        _reject_reparse_tree(final_root, "staging root")
        if not final_root.is_dir():
            raise NotADirectoryError(f"staging root is not a directory: {final_root}")

    dependency_report = Path(dependency_report).absolute()
    resolved_report = dependency_report.resolve(strict=False)
    try:
        resolved_report.relative_to(final_root.resolve(strict=False))
    except ValueError:
        pass
    else:
        raise ValueError("dependency report must be outside the staged package")
    dependency_report.parent.mkdir(parents=True, exist_ok=True)
    dependency_report = (
        dependency_report.parent.resolve(strict=True) / dependency_report.name
    )
    if os.path.lexists(dependency_report):
        if _is_reparse_point(dependency_report):
            raise ValueError(
                "dependency report contains a symlink or reparse point: "
                f"{dependency_report}"
            )
        if not dependency_report.is_file():
            raise ValueError(
                f"dependency report output is not a file: {dependency_report}"
            )

    root = _unique_sibling(final_root, "tmp")
    _require_direct_child(root, stage_parent, "stage candidate")
    root.mkdir()
    temporary_dependency_report = _unique_sibling(dependency_report, "tmp")
    _require_direct_child(
        temporary_dependency_report,
        dependency_report.parent,
        "dependency report candidate",
    )

    try:
        bin_source = isis_prefix / "bin"
        seeds: list[Path] = []
        for app in release_contract.public_apps:
            source = bin_source / f"{app}.exe"
            _copy_file(
                source,
                isis_prefix,
                root,
                Path("bin") / f"{app}.exe",
            )
            seeds.append(source)
        for helper in release_contract.runtime_helpers:
            source = bin_source / f"{helper}.exe"
            _copy_file(
                source,
                isis_prefix,
                root,
                Path("bin") / f"{helper}.exe",
            )
            seeds.append(source)
        for app in release_contract.public_cli_apps:
            _copy_file(
                bin_source / "xml" / f"{app}.xml",
                isis_prefix,
                root,
                Path("bin") / "xml" / f"{app}.xml",
            )

        isis_dll = isis_prefix / "lib" / "isis.dll"
        _copy_file(
            isis_dll,
            isis_prefix,
            root,
            Path("lib") / "isis.dll",
        )
        seeds.append(isis_dll)
        for plugin in sorted(
            (isis_prefix / "lib").glob("*.plugin"),
            key=lambda path: path.name.lower(),
        ):
            _copy_file(plugin, isis_prefix, root, Path("lib") / plugin.name)

        _copy_file(
            isis_prefix / "IsisPreferences",
            isis_prefix,
            root,
            Path("IsisPreferences"),
        )
        _copy_file(isis_prefix / "LICENSE.md", isis_prefix, root, Path("LICENSE.md"))
        _copy_tree(isis_prefix / "appdata", isis_prefix, root / "appdata")
        _copy_tree(minimal_data_root, minimal_data_root, root / "data")
        for name in VALIDATION_DATA_FILES:
            _copy_file(
                validation_data_source / name,
                validation_data_source,
                root,
                Path("validation-data") / name,
            )
        _write_package_readme(root, release_contract)
        for name in LAUNCH_FILES:
            _copy_file(
                LAUNCH_SOURCE / name,
                REPOSITORY_ROOT,
                root,
                Path("launch") / name,
            )

        for pattern in release_contract.qt_plugin_globs:
            matches: list[tuple[Path, Path]] = []
            for prefix in dependency_prefixes:
                matches.extend(
                    (source, prefix)
                    for source in prefix.glob(pattern)
                    if source.is_file()
                )
            if not matches:
                raise FileNotFoundError(
                    f"Qt plugin pattern matched no files: {pattern}"
                )
            for source, prefix in sorted(
                matches,
                key=lambda item: (item[0].name.lower(), str(item[0]).lower()),
            ):
                relative = source.relative_to(prefix / "Library" / "plugins")
                _copy_file(source, prefix, root, Path("plugins") / relative)
                seeds.append(source)

        with TemporaryDirectory(
            prefix="native-app-deps-", dir=stage_parent
        ) as closure_dir:
            closure_root = Path(closure_dir)
            report = copy_dependency_closure(
                tuple(seeds),
                (isis_prefix, *dependency_prefixes),
                closure_root,
                temporary_dependency_report,
            )
            for item in report.get("files", []):
                if not isinstance(item, dict) or not isinstance(
                    item.get("target"), str
                ):
                    raise ValueError("dependency report contains an invalid file entry")
                source = closure_root / Path(item["target"])
                name = item.get("name")
                if not isinstance(name, str) or Path(name).name != name:
                    raise ValueError("dependency report contains an unsafe DLL name")
                _copy_file(source, closure_root, root, Path("lib") / name)

        _enrich_dependency_report(report, root / "lib")
        temporary_dependency_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if FORBIDDEN_ABSOLUTE_RE.search(temporary_dependency_report.read_bytes()):
            raise ValueError("dependency report contains an absolute build/conda path")

        expected_executables = {
            f"{name}.exe"
            for name in (
                *release_contract.public_apps,
                *release_contract.runtime_helpers,
            )
        }
        actual_executables = {path.name for path in (root / "bin").glob("*.exe")}
        if actual_executables != expected_executables:
            raise ValueError(
                "staged executable inventory does not match the release contract"
            )

        write_apps_manifest(root, release_contract)
        _write_build_metadata(root, release_contract)
        _reject_forbidden_content(root, release_contract)
        _write_files_manifest(root)
        _publish_outputs(
            (
                (root, final_root),
                (temporary_dependency_report, dependency_report),
            )
        )
    finally:
        _remove_path(root)
        _remove_path(temporary_dependency_report)

    return StageResult(
        final_root,
        final_root / "manifest" / "apps.json",
        final_root / "manifest" / "files.sha256",
        dependency_report,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--isis-prefix", required=True, type=Path)
    parser.add_argument("--dependency-prefix", action="append", default=[], type=Path)
    parser.add_argument("--minimal-data-root", required=True, type=Path)
    parser.add_argument("--release", required=True, type=Path)
    parser.add_argument("--cli-manifest", required=True, type=Path)
    parser.add_argument("--stage-parent", required=True, type=Path)
    parser.add_argument("--dependency-report", required=True, type=Path)
    args = parser.parse_args()
    contract = load_release_contract(args.release, args.cli_manifest)
    result = stage_native_apps(
        args.isis_prefix,
        tuple(args.dependency_prefix),
        args.minimal_data_root,
        contract,
        args.stage_parent,
        args.dependency_report,
    )
    print(result.root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
