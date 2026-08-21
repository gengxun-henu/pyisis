"""Stage a Windows ISIS prefix into a usgs-pyisis-runtime-win64 wheel tree."""

from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
from pathlib import Path

try:
    from tools.packaging import windows_pe_dependencies as _pe_dependencies
except ModuleNotFoundError as error:
    if error.name != "tools":
        raise
    dependency_module_path = Path(__file__).with_name("windows_pe_dependencies.py")
    dependency_spec = importlib.util.spec_from_file_location(
        "windows_pe_dependencies",
        dependency_module_path,
    )
    if dependency_spec is None or dependency_spec.loader is None:
        raise ImportError(f"Unable to load {dependency_module_path}") from error
    _pe_dependencies = importlib.util.module_from_spec(dependency_spec)
    dependency_spec.loader.exec_module(_pe_dependencies)


copy_dependency_closure = _pe_dependencies.copy_dependency_closure
dumpbin_dependencies = _pe_dependencies.dumpbin_dependencies
dumpbin_forwarded_dependencies = _pe_dependencies.dumpbin_forwarded_dependencies

_copy_dependency_closure = copy_dependency_closure
_dumpbin_dependencies = dumpbin_dependencies
_dumpbin_forwarded_dependencies = dumpbin_forwarded_dependencies


RUNTIME_PATTERNS = (
    "IsisPreferences",
    "isis_version.txt",
    "LICENSE.md",
    "bin/**/*.dll",
    "lib/**/*.dll",
    "lib/**/*.plugin",
    "Library/bin/**/*.dll",
    "Library/lib/**/*.dll",
    "Library/lib/**/*.plugin",
)

DEPENDENCY_PATTERN_GLOBS = (
    "Library/bin/**/*.dll",
    "bin/**/*.dll",
    "Library/lib/**/*.dll",
    "Library/plugins/**/*.dll",
)


def _copy_file(source: Path, source_root: Path, target_root: Path) -> None:
    relative = source.relative_to(source_root)
    target = target_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _copy_patterns(source_root: Path, target_root: Path, patterns: tuple[str, ...]) -> None:
    for pattern in patterns:
        for source in source_root.glob(pattern):
            if source.is_file():
                _copy_file(source, source_root, target_root)


def _set_project_identity(
    stage_dir: Path,
    distribution_name: str,
    package_version: str,
) -> None:
    pyproject = stage_dir / "pyproject.toml"
    payload = pyproject.read_text(encoding="utf-8")
    payload, name_count = re.subn(
        r'(?m)^name = "[^"]+"$',
        f'name = "{distribution_name}"',
        payload,
        count=1,
    )
    payload, version_count = re.subn(
        r'(?m)^version = "[^"]+"$',
        f'version = "{package_version}"',
        payload,
        count=1,
    )
    if name_count != 1 or version_count != 1:
        raise ValueError(f"Unable to update runtime project identity in {pyproject}")
    pyproject.write_text(payload, encoding="utf-8")


def stage_runtime(
    isis_prefix: Path,
    stage_dir: Path,
    dependency_prefixes: tuple[Path, ...] = (),
    dependency_copy_mode: str = "closure",
    distribution_name: str = "usgs-pyisis-runtime-win64",
    package_version: str = "1.3.0rc3",
    dependency_report: Path | None = None,
) -> Path:
    """Copy redistributable runtime files into a generated package stage."""

    if not (isis_prefix / "bin").exists() and not (isis_prefix / "Library").exists():
        raise FileNotFoundError(
            f"ISIS prefix does not look like a runtime prefix: {isis_prefix}"
        )
    for dependency_prefix in dependency_prefixes:
        if not dependency_prefix.exists():
            raise FileNotFoundError(f"Dependency prefix not found: {dependency_prefix}")

    template_root = Path(__file__).resolve().parents[2] / "packaging" / "runtime-win64"
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    shutil.copytree(template_root, stage_dir)
    _set_project_identity(stage_dir, distribution_name, package_version)

    vendor_root = stage_dir / "src" / "pyisis_runtime" / "vendor" / "isis"
    _copy_patterns(isis_prefix, vendor_root, RUNTIME_PATTERNS)
    if dependency_copy_mode == "pattern":
        for dependency_prefix in dependency_prefixes:
            _copy_patterns(dependency_prefix, vendor_root, DEPENDENCY_PATTERN_GLOBS)
    elif dependency_copy_mode == "closure":
        seed_files = tuple(
            path
            for path in vendor_root.rglob("*")
            if path.is_file() and path.suffix.lower() in {".dll", ".plugin"}
        )
        _copy_dependency_closure(
            seed_files,
            dependency_prefixes,
            vendor_root,
            dependency_report,
        )
    else:
        raise ValueError(f"Unsupported dependency copy mode: {dependency_copy_mode}")

    if not any(vendor_root.glob("**/isis.dll")):
        raise FileNotFoundError("Staged runtime is missing isis.dll")

    if not (vendor_root / "IsisPreferences").is_file():
        raise FileNotFoundError("Staged runtime is missing IsisPreferences")

    if not any(vendor_root.glob("**/Camera.plugin")):
        raise FileNotFoundError("Staged runtime is missing Camera.plugin")

    return stage_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--isis-prefix", required=True, type=Path)
    parser.add_argument("--dependency-prefix", action="append", default=[], type=Path)
    parser.add_argument(
        "--dependency-copy-mode",
        choices=("closure", "pattern"),
        default="closure",
    )
    parser.add_argument("--stage-dir", required=True, type=Path)
    parser.add_argument(
        "--distribution-name",
        default="usgs-pyisis-runtime-win64",
    )
    parser.add_argument("--package-version", default="1.3.0rc3")
    parser.add_argument("--dependency-report", type=Path)
    args = parser.parse_args()

    stage_runtime(
        args.isis_prefix.resolve(),
        args.stage_dir.resolve(),
        tuple(path.resolve() for path in args.dependency_prefix),
        dependency_copy_mode=args.dependency_copy_mode,
        distribution_name=args.distribution_name,
        package_version=args.package_version,
        dependency_report=(
            args.dependency_report.resolve() if args.dependency_report else None
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
