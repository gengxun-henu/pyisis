"""Stage a Windows ISIS prefix into a pyisis-runtime-win64 wheel tree."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


RUNTIME_PATTERNS = (
    "IsisPreferences",
    "isis_version.txt",
    "LICENSE.md",
    "bin/**/*.dll",
    "bin/**/*.exe",
    "bin/xml/**/*.xml",
    "lib/**/*.dll",
    "lib/**/*.plugin",
    "Library/bin/**/*.dll",
    "Library/bin/**/*.exe",
    "Library/bin/xml/**/*.xml",
    "Library/lib/**/*.dll",
    "Library/lib/**/*.plugin",
)

DEPENDENCY_RUNTIME_PATTERNS = (
    "Library/bin/**/*.dll",
    "Library/bin/**/*.exe",
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


def stage_runtime(
    isis_prefix: Path,
    stage_dir: Path,
    dependency_prefixes: tuple[Path, ...] = (),
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

    vendor_root = stage_dir / "src" / "pyisis_runtime" / "vendor" / "isis"
    _copy_patterns(isis_prefix, vendor_root, RUNTIME_PATTERNS)
    for dependency_prefix in dependency_prefixes:
        _copy_patterns(dependency_prefix, vendor_root, DEPENDENCY_RUNTIME_PATTERNS)

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
    parser.add_argument("--stage-dir", required=True, type=Path)
    args = parser.parse_args()

    stage_runtime(
        args.isis_prefix.resolve(),
        args.stage_dir.resolve(),
        tuple(path.resolve() for path in args.dependency_prefix),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
