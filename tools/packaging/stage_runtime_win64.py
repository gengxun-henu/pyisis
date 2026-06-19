"""Stage a Windows ISIS prefix into a usgs-pyisis-runtime-win64 wheel tree."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path


SYSTEM_DLL_PREFIXES = ("api-ms-", "ext-ms-")
SYSTEM_DLL_NAMES = {
    "advapi32.dll",
    "bcrypt.dll",
    "cfgmgr32.dll",
    "comdlg32.dll",
    "crypt32.dll",
    "d3d11.dll",
    "dbghelp.dll",
    "dnsapi.dll",
    "dwmapi.dll",
    "dxgi.dll",
    "gdi32.dll",
    "imm32.dll",
    "iphlpapi.dll",
    "kernel32.dll",
    "mpr.dll",
    "msvcrt.dll",
    "netapi32.dll",
    "normaliz.dll",
    "ntdll.dll",
    "ole32.dll",
    "oleaut32.dll",
    "python312.dll",
    "rpcrt4.dll",
    "secur32.dll",
    "setupapi.dll",
    "shell32.dll",
    "shlwapi.dll",
    "user32.dll",
    "userenv.dll",
    "uxtheme.dll",
    "uuid.dll",
    "version.dll",
    "winmm.dll",
    "winspool.drv",
    "wldap32.dll",
    "ws2_32.dll",
}
DEPENDENCY_NAME_RE = re.compile(r"^[A-Za-z0-9_.+\-]+\.dll$", re.IGNORECASE)

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

DEPENDENCY_PATTERN_GLOBS = (
    "Library/bin/**/*.dll",
    "Library/bin/**/*.exe",
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


def _dependency_search_roots(dependency_prefix: Path) -> tuple[Path, ...]:
    return (
        dependency_prefix / "Library" / "bin",
        dependency_prefix / "Library" / "lib",
        dependency_prefix / "bin",
        dependency_prefix / "lib",
    )


def _dependency_index(dependency_prefixes: tuple[Path, ...]) -> dict[str, tuple[Path, Path]]:
    index: dict[str, tuple[Path, Path]] = {}
    for dependency_prefix in dependency_prefixes:
        for root in _dependency_search_roots(dependency_prefix):
            if not root.exists():
                continue
            for source in root.rglob("*.dll"):
                if source.is_file():
                    index.setdefault(source.name.lower(), (source, dependency_prefix))
    return index


def _dumpbin_dependencies(binary: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ["dumpbin", "/DEPENDENTS", str(binary)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ()

    dependencies = []
    for line in result.stdout.splitlines():
        name = line.strip()
        normalized = name.lower()
        if not DEPENDENCY_NAME_RE.match(name):
            continue
        if normalized.startswith(SYSTEM_DLL_PREFIXES) or normalized in SYSTEM_DLL_NAMES:
            continue
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
        binary_key = str(binary.resolve()).lower()
        if binary_key in visited:
            continue
        visited.add(binary_key)

        for dependency_name in _dumpbin_dependencies(binary):
            resolved = index.get(dependency_name.lower())
            if resolved is None:
                continue

            source, dependency_prefix = resolved
            _copy_file(source, dependency_prefix, vendor_root)
            if str(source.resolve()).lower() not in visited:
                queue.append(source)


def stage_runtime(
    isis_prefix: Path,
    stage_dir: Path,
    dependency_prefixes: tuple[Path, ...] = (),
    dependency_copy_mode: str = "closure",
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
    if dependency_copy_mode == "pattern":
        for dependency_prefix in dependency_prefixes:
            _copy_patterns(dependency_prefix, vendor_root, DEPENDENCY_PATTERN_GLOBS)
    elif dependency_copy_mode == "closure":
        seed_files = tuple(
            path
            for path in vendor_root.rglob("*")
            if path.is_file() and path.suffix.lower() in {".dll", ".exe", ".plugin"}
        )
        _copy_dependency_closure(seed_files, dependency_prefixes, vendor_root)
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
    args = parser.parse_args()

    stage_runtime(
        args.isis_prefix.resolve(),
        args.stage_dir.resolve(),
        tuple(path.resolve() for path in args.dependency_prefix),
        args.dependency_copy_mode,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
