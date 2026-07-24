"""Vendor private Linux C++ toolchain libraries into a wheel."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import zipfile


TOOLCHAIN_RENAMES = {
    "libstdc++.so.6": "libpyisis_stdc++.so.6",
    "libgcc_s.so.1": "libpyisis_gcc_s.so.1",
}
RUNTIME_LIBRARY_DIR = Path("pyisis_runtime/vendor/isis/lib")


def _is_elf(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open("rb") as stream:
        return stream.read(4) == b"\x7fELF"


def _patchelf(
    executable: str,
    *arguments: str,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [executable, *arguments],
        check=True,
        capture_output=capture_output,
        text=True,
    )


def patch_toolchain_dependencies(root: Path, patchelf: str = "patchelf") -> int:
    """Rename bundled toolchain libraries and redirect every ELF consumer."""

    library_dir = root / RUNTIME_LIBRARY_DIR
    if not library_dir.is_dir():
        raise FileNotFoundError(f"Linux runtime library directory not found: {library_dir}")

    for original_name, private_name in TOOLCHAIN_RENAMES.items():
        original = library_dir / original_name
        private = library_dir / private_name
        if not original.is_file():
            raise FileNotFoundError(f"Bundled toolchain library not found: {original}")
        if private.exists():
            raise FileExistsError(f"Private toolchain library already exists: {private}")
        original.replace(private)
        _patchelf(patchelf, "--set-soname", private_name, str(private))

    replacements = 0
    for candidate in root.rglob("*"):
        if not _is_elf(candidate):
            continue
        needed = _patchelf(
            patchelf,
            "--print-needed",
            str(candidate),
            capture_output=True,
        ).stdout.splitlines()
        for original_name, private_name in TOOLCHAIN_RENAMES.items():
            if original_name not in needed:
                continue
            _patchelf(
                patchelf,
                "--replace-needed",
                original_name,
                private_name,
                str(candidate),
            )
            replacements += 1

    if replacements == 0:
        raise RuntimeError("No Linux toolchain dependencies were redirected")
    verify_toolchain_dependencies(root, patchelf)
    return replacements


def verify_toolchain_dependencies(root: Path, patchelf: str = "patchelf") -> int:
    """Require private toolchain payloads and reject system toolchain links."""

    library_dir = root / RUNTIME_LIBRARY_DIR
    for original_name, private_name in TOOLCHAIN_RENAMES.items():
        if (library_dir / original_name).exists():
            raise RuntimeError(
                f"System-named toolchain library remains in wheel: {original_name}"
            )
        if not (library_dir / private_name).is_file():
            raise FileNotFoundError(
                f"Private toolchain library not found: {library_dir / private_name}"
            )

    private_dependencies: set[str] = set()
    system_dependencies: list[tuple[Path, str]] = []
    elf_files = 0
    for candidate in root.rglob("*"):
        if not _is_elf(candidate):
            continue
        elf_files += 1
        needed = _patchelf(
            patchelf,
            "--print-needed",
            str(candidate),
            capture_output=True,
        ).stdout.splitlines()
        for original_name, private_name in TOOLCHAIN_RENAMES.items():
            if original_name in needed:
                system_dependencies.append((candidate, original_name))
            if private_name in needed:
                private_dependencies.add(private_name)

    if system_dependencies:
        details = ", ".join(
            f"{path.relative_to(root)} -> {dependency}"
            for path, dependency in system_dependencies[:10]
        )
        raise RuntimeError(f"System toolchain dependencies remain: {details}")
    missing = set(TOOLCHAIN_RENAMES.values()) - private_dependencies
    if missing:
        raise RuntimeError(
            f"Private toolchain dependencies are unused: {sorted(missing)}"
        )
    return elf_files


def verify_wheel_toolchain(
    wheel_path: Path,
    patchelf: str = "patchelf",
) -> int:
    """Verify private toolchain dependencies in an already packed wheel."""

    wheel_path = wheel_path.resolve()
    with TemporaryDirectory(prefix="pyisis-toolchain-verify-") as temp_dir:
        root = Path(temp_dir)
        with zipfile.ZipFile(wheel_path) as archive:
            archive.extractall(root)
        return verify_toolchain_dependencies(root, patchelf)


def vendor_wheel_toolchain(
    wheel_path: Path,
    patchelf: str = "patchelf",
) -> int:
    """Rewrite a wheel with private libstdc++ and libgcc_s dependencies."""

    wheel_path = wheel_path.resolve()
    if not wheel_path.is_file():
        raise FileNotFoundError(f"Wheel not found: {wheel_path}")

    with TemporaryDirectory(prefix="pyisis-toolchain-wheel-") as temp_dir:
        temp_root = Path(temp_dir)
        unpacked = temp_root / "unpacked"
        packed = temp_root / "packed"
        unpacked.mkdir()
        packed.mkdir()
        with zipfile.ZipFile(wheel_path) as archive:
            archive.extractall(unpacked)

        replacements = patch_toolchain_dependencies(unpacked, patchelf)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "wheel",
                "pack",
                str(unpacked),
                "--dest-dir",
                str(packed),
            ],
            check=True,
        )
        packed_wheels = list(packed.glob("*.whl"))
        if len(packed_wheels) != 1:
            raise RuntimeError(
                f"Expected one repacked wheel, found {len(packed_wheels)}"
            )
        shutil.move(str(packed_wheels[0]), wheel_path)
    return replacements


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--patchelf", default="patchelf")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        elf_files = verify_wheel_toolchain(args.wheel, args.patchelf)
        print(f"Verified private toolchain dependencies across {elf_files} ELF files")
        return 0
    replacements = vendor_wheel_toolchain(args.wheel, args.patchelf)
    print(f"Redirected {replacements} ELF toolchain dependencies in {args.wheel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
