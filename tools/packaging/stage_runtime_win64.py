"""Stage a Windows ISIS prefix into a usgs-pyisis-runtime-win64 wheel tree."""

from __future__ import annotations

import argparse
import json
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
PYTHON_DLL_RE = re.compile(r"^python3\d{2}\.dll$", re.IGNORECASE)
FORWARDED_DLL_RE = re.compile(
    r"\b([A-Za-z0-9_.+\-]+\.dll)\.",
    re.IGNORECASE,
)

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


def _is_system_dependency(name: str) -> bool:
    normalized = name.lower()
    return (
        normalized.startswith(SYSTEM_DLL_PREFIXES)
        or normalized in SYSTEM_DLL_NAMES
        or PYTHON_DLL_RE.match(normalized) is not None
    )


def _dumpbin_dependencies(binary: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ["dumpbin", "/DEPENDENTS", str(binary)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"dumpbin failed for {binary}: {details or f'exit code {result.returncode}'}"
        )

    dependencies = []
    for line in result.stdout.splitlines():
        name = line.strip()
        if not DEPENDENCY_NAME_RE.match(name):
            continue
        dependencies.append(name)
    return tuple(dependencies)


def _dumpbin_forwarded_dependencies(binary: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ["dumpbin", "/EXPORTS", str(binary)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"dumpbin failed for {binary}: {details or f'exit code {result.returncode}'}"
        )

    dependencies = []
    seen = set()
    for match in FORWARDED_DLL_RE.finditer(result.stdout):
        name = match.group(1)
        normalized = name.lower()
        if normalized not in seen:
            seen.add(normalized)
            dependencies.append(name)
    return tuple(dependencies)


def _copy_dependency_closure(
    seed_files: tuple[Path, ...],
    dependency_prefixes: tuple[Path, ...],
    vendor_root: Path,
    dependency_report: Path | None = None,
) -> dict[str, object]:
    index = _dependency_index(dependency_prefixes)
    packaged = {
        path.name.lower()
        for path in vendor_root.rglob("*.dll")
        if path.is_file()
    }
    queue = list(seed_files)
    visited: set[str] = set()
    binaries: list[dict[str, object]] = []
    unresolved: set[str] = set()

    while queue:
        binary = queue.pop(0)
        binary_key = str(binary.resolve()).lower()
        if binary_key in visited:
            continue
        visited.add(binary_key)

        dependencies = dict.fromkeys(
            (*_dumpbin_dependencies(binary), *_dumpbin_forwarded_dependencies(binary))
        )
        imports = []
        for dependency_name in dependencies:
            normalized = dependency_name.lower()
            if _is_system_dependency(dependency_name):
                imports.append(
                    {"name": dependency_name, "classification": "system"}
                )
                continue
            if normalized in packaged:
                imports.append(
                    {"name": dependency_name, "classification": "packaged"}
                )
                continue

            resolved = index.get(normalized)
            if resolved is None:
                imports.append(
                    {"name": dependency_name, "classification": "unresolved"}
                )
                unresolved.add(dependency_name)
                continue

            source, dependency_prefix = resolved
            _copy_file(source, dependency_prefix, vendor_root)
            packaged.add(normalized)
            imports.append(
                {"name": dependency_name, "classification": "resolved"}
            )
            if str(source.resolve()).lower() not in visited:
                queue.append(source)

        binaries.append({"binary": binary.name, "imports": imports})

    report: dict[str, object] = {
        "schema_version": 1,
        "binaries": binaries,
        "unresolved": sorted(unresolved, key=str.lower),
    }
    if dependency_report is not None:
        dependency_report.parent.mkdir(parents=True, exist_ok=True)
        dependency_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if unresolved:
        missing = ", ".join(sorted(unresolved, key=str.lower))
        raise FileNotFoundError(f"Unresolved Windows runtime dependencies: {missing}")
    return report


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
    package_version: str = "1.3.0rc2",
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
    parser.add_argument("--package-version", default="1.3.0rc2")
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
