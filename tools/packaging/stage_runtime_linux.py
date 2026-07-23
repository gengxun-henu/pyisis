"""Stage a Linux ISIS prefix into a usgs-pyisis-runtime-linux-x86_64 wheel tree."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


SHARED_LIBRARY_RE = re.compile(r"^[A-Za-z0-9_.+\-]+\.so(?:\.[A-Za-z0-9_.+\-]+)*$")

RUNTIME_ROOT_FILES = frozenset(
    {
        "IsisPreferences",
        "isis_version.txt",
        "LICENSE.md",
    }
)

FALLBACK_RUNTIME_PATTERNS = (
    "IsisPreferences",
    "isis_version.txt",
    "LICENSE.md",
    "appdata/**/*",
    "etc/isis/**/*",
    "lib/*.plugin",
    "lib/libisis.so*",
    "lib/lib*Camera.so*",
    "lib/libMiniRF.so*",
    "lib64/*.plugin",
    "lib64/libisis.so*",
    "lib64/lib*Camera.so*",
    "lib64/libMiniRF.so*",
    "share/isis/**/*",
)

DEPENDENCY_PATTERN_GLOBS = (
    "lib/**/*.so",
    "lib/**/*.so.*",
    "lib64/**/*.so",
    "lib64/**/*.so.*",
    "plugins/**/*.so",
    "plugins/**/*.so.*",
)


def _copy_file(source: Path, source_root: Path, target_root: Path) -> None:
    relative = source.relative_to(source_root)
    target = target_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        resolved_source = source.resolve(strict=True)
        try:
            resolved_relative = resolved_source.relative_to(source_root.resolve())
        except ValueError as exc:
            raise ValueError(
                f"Runtime symlink escapes its source prefix: {source}"
            ) from exc
        _copy_file(resolved_source, source_root.resolve(), target_root)
        if target.exists() or target.is_symlink():
            target.unlink()
        staged_target = target_root / resolved_relative
        target.symlink_to(os.path.relpath(staged_target, target.parent))
        return
    shutil.copy2(source, target)


def _copy_dependency_alias(
    source: Path,
    source_root: Path,
    target_root: Path,
    dependency_name: str,
) -> None:
    relative = source.relative_to(source_root)
    target = target_root / relative.parent / dependency_name
    target.parent.mkdir(parents=True, exist_ok=True)
    copied_source = target_root / relative
    if target.exists() or target.is_symlink():
        target.unlink()
    target.symlink_to(os.path.relpath(copied_source, target.parent))


def _copy_patterns(source_root: Path, target_root: Path, patterns: tuple[str, ...]) -> None:
    for pattern in patterns:
        for source in source_root.glob(pattern):
            if source.is_file():
                _copy_file(source, source_root, target_root)


def _is_isis_runtime_path(relative: Path) -> bool:
    if relative.as_posix() in RUNTIME_ROOT_FILES:
        return True
    if not relative.parts:
        return False
    if relative.parts[0] == "appdata":
        return True
    if relative.parts[:2] == ("etc", "isis"):
        return True
    if relative.parts[0] not in {"lib", "lib64", "plugins"}:
        return False
    return bool(SHARED_LIBRARY_RE.match(relative.name) or relative.suffix == ".plugin")


def _conda_isis_runtime_files(isis_prefix: Path) -> tuple[Path, ...]:
    metadata_root = isis_prefix / "conda-meta"
    if not metadata_root.is_dir():
        return ()

    for metadata_path in sorted(metadata_root.glob("isis-*.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("name") != "isis":
            continue
        runtime_files = []
        for value in metadata.get("files", ()):
            relative = Path(value)
            source = isis_prefix / relative
            if _is_isis_runtime_path(relative) and source.is_file():
                runtime_files.append(source)
        return tuple(runtime_files)
    return ()


def _plugin_library_names(plugin_files: tuple[Path, ...]) -> tuple[str, ...]:
    names: set[str] = set()
    for plugin_file in plugin_files:
        for line in plugin_file.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^\s*Library\s*=\s*([^\s#]+)", line)
            if match:
                names.add(match.group(1))
    return tuple(sorted(names))


def _copy_fallback_isis_runtime(isis_prefix: Path, vendor_root: Path) -> None:
    _copy_patterns(isis_prefix, vendor_root, FALLBACK_RUNTIME_PATTERNS)
    plugin_files = tuple(
        path
        for path in isis_prefix.glob("lib*/*.plugin")
        if path.is_file()
    )
    for library_name in _plugin_library_names(plugin_files):
        _copy_patterns(
            isis_prefix,
            vendor_root,
            (
                f"lib/lib{library_name}.so*",
                f"lib64/lib{library_name}.so*",
            ),
        )


def _copy_isis_runtime(isis_prefix: Path, vendor_root: Path) -> str:
    manifest_files = _conda_isis_runtime_files(isis_prefix)
    if manifest_files:
        for source in manifest_files:
            _copy_file(source, isis_prefix, vendor_root)
        return "conda-manifest"

    _copy_fallback_isis_runtime(isis_prefix, vendor_root)
    return "fallback"


def _dependency_search_roots(dependency_prefix: Path) -> tuple[Path, ...]:
    return (
        dependency_prefix / "lib",
        dependency_prefix / "lib64",
        dependency_prefix / "bin",
        dependency_prefix / "plugins",
    )


def _dependency_index(dependency_prefixes: tuple[Path, ...]) -> dict[str, tuple[Path, Path]]:
    index: dict[str, tuple[Path, Path]] = {}
    for dependency_prefix in dependency_prefixes:
        for root in _dependency_search_roots(dependency_prefix):
            if not root.exists():
                continue
            for source in root.rglob("*"):
                if source.is_file() and ".so" in source.name:
                    index.setdefault(source.name, (source, dependency_prefix))
    return index


def _resolve_dependency(
    index: dict[str, tuple[Path, Path]],
    dependency_name: str,
) -> tuple[Path, Path] | None:
    exact = index.get(dependency_name)
    if exact is not None:
        return exact

    versioned_prefix = f"{dependency_name}."
    compatible_names = sorted(
        name for name in index if name.startswith(versioned_prefix)
    )
    if not compatible_names:
        return None
    return index[compatible_names[0]]


def _ldd_dependencies(binary: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ["ldd", str(binary)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ()

    dependencies = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if "=>" in stripped:
            name = stripped.split("=>", 1)[0].strip()
        else:
            name = stripped.split(" ", 1)[0].strip()
        if SHARED_LIBRARY_RE.match(name):
            dependencies.append(name)
    return tuple(dependencies)


def _copy_dependency_closure(
    seed_files: tuple[Path, ...],
    dependency_prefixes: tuple[Path, ...],
    vendor_root: Path,
) -> None:
    index = _dependency_index(dependency_prefixes)
    queue = list(seed_files)
    visited: set[str] = set()

    while queue:
        binary = queue.pop(0)
        binary_key = str(binary.resolve())
        if binary_key in visited:
            continue
        visited.add(binary_key)

        for dependency_name in _ldd_dependencies(binary):
            resolved = _resolve_dependency(index, dependency_name)
            if resolved is None:
                continue

            source, dependency_prefix = resolved
            _copy_file(source, dependency_prefix, vendor_root)
            if source.name != dependency_name:
                _copy_dependency_alias(
                    source,
                    dependency_prefix,
                    vendor_root,
                    dependency_name,
                )
            if str(source.resolve()) not in visited:
                queue.append(source)


def _missing_runtime_dependencies(binary: Path, vendor_root: Path) -> tuple[str, ...]:
    library_dirs = sorted(
        {
            str(path.parent)
            for path in vendor_root.rglob("*")
            if path.is_file() and ".so" in path.name
        }
    )
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = os.pathsep.join(library_dirs)

    result = subprocess.run(
        ["ldd", str(binary)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    missing = []
    for line in result.stdout.splitlines():
        if "=> not found" not in line:
            continue
        name = line.split("=>", 1)[0].strip()
        if SHARED_LIBRARY_RE.match(name):
            missing.append(name)
    return tuple(missing)


def _verify_runtime_closure(vendor_root: Path) -> None:
    libisis = next(iter(sorted(vendor_root.glob("lib/libisis.so*"))), None)
    if libisis is None:
        return
    missing = _missing_runtime_dependencies(libisis, vendor_root)
    if missing:
        names = ", ".join(sorted(set(missing)))
        raise FileNotFoundError(f"Staged Linux runtime has unresolved dependencies: {names}")


def _runtime_size_bytes(vendor_root: Path) -> int:
    return sum(path.lstat().st_size for path in vendor_root.rglob("*") if path.is_file())


def stage_runtime(
    isis_prefix: Path,
    stage_dir: Path,
    dependency_prefixes: tuple[Path, ...] = (),
    dependency_copy_mode: str = "closure",
    max_runtime_bytes: int | None = None,
) -> Path:
    """Copy redistributable Linux runtime files into a generated package stage."""

    if not (isis_prefix / "lib").exists() and not (isis_prefix / "lib64").exists():
        raise FileNotFoundError(
            f"ISIS prefix does not look like a Linux runtime prefix: {isis_prefix}"
        )
    for dependency_prefix in dependency_prefixes:
        if not dependency_prefix.exists():
            raise FileNotFoundError(f"Dependency prefix not found: {dependency_prefix}")

    template_root = (
        Path(__file__).resolve().parents[2] / "packaging" / "runtime-linux-x86_64"
    )
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    shutil.copytree(template_root, stage_dir)

    vendor_root = stage_dir / "src" / "pyisis_runtime" / "vendor" / "isis"
    _copy_isis_runtime(isis_prefix, vendor_root)
    if dependency_copy_mode == "pattern":
        for dependency_prefix in dependency_prefixes:
            _copy_patterns(dependency_prefix, vendor_root, DEPENDENCY_PATTERN_GLOBS)
    elif dependency_copy_mode == "closure":
        seed_files = tuple(
            path
            for path in vendor_root.rglob("*")
            if path.is_file() and (".so" in path.name or path.suffix == ".plugin")
        )
        search_prefixes = tuple(dict.fromkeys((isis_prefix, *dependency_prefixes)))
        _copy_dependency_closure(seed_files, search_prefixes, vendor_root)
    else:
        raise ValueError(f"Unsupported dependency copy mode: {dependency_copy_mode}")

    if not any(vendor_root.glob("**/libisis.so*")):
        raise FileNotFoundError("Staged runtime is missing libisis.so")

    if not (vendor_root / "IsisPreferences").is_file():
        raise FileNotFoundError("Staged runtime is missing IsisPreferences")

    if not any(vendor_root.glob("**/Camera.plugin")):
        raise FileNotFoundError("Staged runtime is missing Camera.plugin")

    for excluded_directory in ("bin", "include", "make", "scripts"):
        if (vendor_root / excluded_directory).exists():
            raise ValueError(
                f"Staged binding runtime unexpectedly contains {excluded_directory}/"
            )

    _verify_runtime_closure(vendor_root)

    runtime_size = _runtime_size_bytes(vendor_root)
    if max_runtime_bytes is not None and runtime_size > max_runtime_bytes:
        raise ValueError(
            "Staged Linux runtime exceeds its size budget: "
            f"{runtime_size} > {max_runtime_bytes} bytes"
        )

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
    parser.add_argument("--max-runtime-bytes", type=int)
    args = parser.parse_args()

    stage_runtime(
        args.isis_prefix.resolve(),
        args.stage_dir.resolve(),
        tuple(path.resolve() for path in args.dependency_prefix),
        args.dependency_copy_mode,
        args.max_runtime_bytes,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
