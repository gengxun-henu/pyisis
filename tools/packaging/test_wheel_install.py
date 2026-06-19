"""Verify usgs-pyisis wheels from a clean virtual environment."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
import venv


def _python_executable(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _path_contains(path_text: str, roots: tuple[Path, ...]) -> bool:
    try:
        path = Path(path_text).resolve()
    except OSError:
        return False

    return any(path == root or path.is_relative_to(root) for root in roots)


def _verification_environment() -> dict[str, str]:
    env = os.environ.copy()
    root_names = ("ISIS_PREFIX", "ISISROOT", "PYISIS_DEP_PREFIX")
    roots = tuple(
        Path(env[name]).resolve()
        for name in root_names
        if env.get(name)
    )

    for name in (*root_names, "ISISDATA", "PYTHONPATH", "CONDA_PREFIX"):
        env.pop(name, None)

    path_parts = [
        part
        for part in env.get("PATH", "").split(os.pathsep)
        if part and not _path_contains(part, roots)
    ]
    env["PATH"] = os.pathsep.join(path_parts)
    return env


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, check=True, env=env)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheelhouse", required=True, type=Path)
    parser.add_argument("--venv", required=True, type=Path)
    args = parser.parse_args()

    if args.venv.exists():
        raise FileExistsError(f"Refusing to reuse existing venv: {args.venv}")

    venv.EnvBuilder(with_pip=True).create(args.venv)
    python = _python_executable(args.venv)

    run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            str(args.wheelhouse),
            "usgs-pyisis",
        ]
    )
    run(
        [
            str(python),
            "-c",
            (
                "import os, pyisis, isis_pybind; "
                "status = pyisis.data_status(); "
                "print(status.message); "
                "assert os.environ.get('ISISROOT'); "
                "assert status.usable_for_smoke_tests"
            ),
        ],
        env=_verification_environment(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
