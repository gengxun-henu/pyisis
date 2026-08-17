"""Resolve and copy a fail-closed Windows PE dependency closure."""

from __future__ import annotations

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
FORWARDED_DLL_RE = re.compile(r"\b([A-Za-z0-9_.+\-]+\.dll)\.", re.IGNORECASE)


def _copy_file(source: Path, source_root: Path, target_root: Path) -> Path:
    relative = source.relative_to(source_root)
    target = target_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def _dependency_search_roots(dependency_prefix: Path) -> tuple[Path, ...]:
    return (
        dependency_prefix / "Library" / "bin",
        dependency_prefix / "Library" / "lib",
        dependency_prefix / "bin",
        dependency_prefix / "lib",
    )


def _dependency_index(
    dependency_prefixes: tuple[Path, ...],
) -> dict[str, tuple[Path, Path]]:
    index: dict[str, tuple[Path, Path]] = {}
    for dependency_prefix in dependency_prefixes:
        for root in _dependency_search_roots(dependency_prefix):
            if not root.exists():
                continue
            for source in sorted(
                root.rglob("*.dll"),
                key=lambda path: (str(path).lower(), str(path)),
            ):
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


def dumpbin_dependencies(binary: Path) -> tuple[str, ...]:
    """Return direct DLL imports reported by ``dumpbin /DEPENDENTS``."""

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

    return tuple(
        name
        for line in result.stdout.splitlines()
        if DEPENDENCY_NAME_RE.match(name := line.strip())
    )


def dumpbin_forwarded_dependencies(binary: Path) -> tuple[str, ...]:
    """Return unique DLLs referenced by forwarded PE exports."""

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

    dependencies: list[str] = []
    seen: set[str] = set()
    for match in FORWARDED_DLL_RE.finditer(result.stdout):
        name = match.group(1)
        normalized = name.lower()
        if normalized not in seen:
            seen.add(normalized)
            dependencies.append(name)
    return tuple(dependencies)


def copy_dependency_closure(
    seed_files: tuple[Path, ...],
    dependency_prefixes: tuple[Path, ...],
    target_root: Path,
    dependency_report: Path | None = None,
) -> dict[str, object]:
    """Copy all non-system PE imports into *target_root* and report provenance."""

    index = _dependency_index(dependency_prefixes)
    packaged = {
        path.name.lower() for path in target_root.rglob("*.dll") if path.is_file()
    }
    queue = sorted(
        seed_files,
        key=lambda path: (
            path.name.lower(),
            path.name,
            str(path.resolve()).lower(),
            str(path.resolve()),
        ),
    )
    visited: set[str] = set()
    binaries: list[dict[str, object]] = []
    files: dict[str, dict[str, object]] = {}
    unresolved: set[str] = set()

    while queue:
        binary = queue.pop(0)
        binary_key = str(binary.resolve()).lower()
        if binary_key in visited:
            continue
        visited.add(binary_key)

        dependencies: dict[str, str] = {}
        for name in dumpbin_dependencies(binary):
            dependencies[name.lower()] = "direct"
        for name in dumpbin_forwarded_dependencies(binary):
            dependencies.setdefault(name.lower(), "forwarder")

        imports: list[dict[str, object]] = []
        for normalized in sorted(dependencies):
            dependency_name = normalized
            import_kind = dependencies[normalized]
            import_entry: dict[str, object] = {
                "name": dependency_name,
                "import_kind": import_kind,
            }
            if _is_system_dependency(dependency_name):
                import_entry["classification"] = "system"
                imports.append(import_entry)
                continue
            if normalized in packaged:
                import_entry["classification"] = "packaged"
                imports.append(import_entry)
                existing = files.get(normalized)
                if existing is not None:
                    existing["parents"] = sorted(
                        {*existing["parents"], binary.name}, key=str.lower
                    )
                    if import_kind == "direct":
                        existing["import_kind"] = "direct"
                continue

            resolved = index.get(normalized)
            if resolved is None:
                import_entry["classification"] = "unresolved"
                imports.append(import_entry)
                unresolved.add(dependency_name)
                continue

            source, dependency_prefix = resolved
            target = _copy_file(source, dependency_prefix, target_root)
            packaged.add(normalized)
            import_entry["classification"] = "resolved"
            imports.append(import_entry)
            files[normalized] = {
                "name": dependency_name,
                "source": source.relative_to(dependency_prefix).as_posix(),
                "target": target.relative_to(target_root).as_posix(),
                "import_kind": import_kind,
                "parents": [binary.name],
            }
            if str(source.resolve()).lower() not in visited:
                queue.append(source)

        binaries.append(
            {
                "binary": binary.name,
                "imports": sorted(imports, key=lambda item: item["name"].lower()),
            }
        )

    report: dict[str, object] = {
        "schema_version": 1,
        "binaries": sorted(
            binaries,
            key=lambda item: (
                item["binary"].lower(),
                item["binary"],
                json.dumps(item["imports"], sort_keys=True),
            ),
        ),
        "files": sorted(files.values(), key=lambda item: item["name"].lower()),
        "unresolved": sorted(unresolved, key=str.lower),
    }
    if dependency_report is not None:
        dependency_report.parent.mkdir(parents=True, exist_ok=True)
        dependency_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if unresolved:
        raise FileNotFoundError(
            "Unresolved Windows runtime dependencies: "
            + ", ".join(report["unresolved"])
        )
    return report
