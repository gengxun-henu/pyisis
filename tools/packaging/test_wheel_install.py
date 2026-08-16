"""Verify usgs-pyisis wheels from a clean virtual environment."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
import venv


UNIT_TEST_DIR = Path(__file__).resolve().parents[2] / "tests" / "unitTest"


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
    root_names = (
        "ISIS_PREFIX",
        "ISISROOT",
        "PYISIS_DEP_PREFIX",
        "PYISIS_WINDOWS_DEP_PREFIX",
        "CONDA_PREFIX",
    )
    roots = tuple(
        Path(env[name]).resolve()
        for name in root_names
        if env.get(name)
    )

    for name in (*root_names, "ISISDATA", "PYTHONPATH"):
        env.pop(name, None)

    path_parts = [
        part
        for part in env.get("PATH", "").split(os.pathsep)
        if part and not _path_contains(part, roots)
    ]
    env["PATH"] = os.pathsep.join(path_parts)
    return env


def _unit_test_environment() -> dict[str, str]:
    env = _verification_environment()
    env["PYTHONPATH"] = str(UNIT_TEST_DIR)
    return env


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, check=True, env=env)


def _command_text(command: list[str]) -> str:
    return subprocess.list2cmdline(command) if sys.platform == "win32" else shlex.join(command)


def _passed_check(check_id: str, command: list[str]) -> dict[str, object]:
    return {
        "id": check_id,
        "command": _command_text(command),
        "passed": 1,
        "failed": 0,
        "skipped": 0,
        "exit_code": 0,
    }


def _test_modules(test_list: Path) -> list[str]:
    return [
        line
        for raw_line in test_list.read_text(encoding="utf-8").splitlines()
        if (line := raw_line.strip()) and not line.startswith("#")
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheelhouse", required=True, type=Path)
    parser.add_argument("--venv", required=True, type=Path)
    parser.add_argument("--package", default="usgs-pyisis")
    parser.add_argument("--expected-isis-version")
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--test-list",
        type=Path,
        help="Optional file containing unittest modules to run after the clean-wheel smoke test.",
    )
    args = parser.parse_args()

    if args.venv.exists():
        raise FileExistsError(f"Refusing to reuse existing venv: {args.venv}")

    venv.EnvBuilder(with_pip=True).create(args.venv)
    python = _python_executable(args.venv)
    checks: list[dict[str, object]] = []

    install_command = [
        str(python),
        "-m",
        "pip",
        "install",
        "--no-index",
        "--find-links",
        str(args.wheelhouse),
        args.package,
    ]
    run(install_command)
    checks.append(_passed_check("wheel-install", install_command))
    verification_env = _verification_environment()
    if args.expected_isis_version:
        verification_env["PYISIS_EXPECTED_ISIS_VERSION"] = args.expected_isis_version
    import_command = [
        str(python),
        "-c",
        (
            "import os, pyisis, isis_pybind; "
            "status = pyisis.data_status(); "
            "print(status.message); "
            "assert os.environ.get('ISISROOT'); "
            "assert status.usable_for_smoke_tests; "
            "expected = os.environ.get('PYISIS_EXPECTED_ISIS_VERSION'); "
            "assert expected is None or isis_pybind.__isis_version__ == expected"
        ),
    ]
    run(import_command, env=verification_env)
    checks.append(_passed_check("fresh-import", import_command))
    if args.test_list:
        verification_env = _unit_test_environment()
        for module in _test_modules(args.test_list):
            module_command = [str(python), "-m", "unittest", module, "-v"]
            run(module_command, env=verification_env)
            checks.append(_passed_check(f"unit-module:{module}", module_command))
    payload = {
        "schema_version": 1,
        "package": args.package,
        "wheelhouse": str(args.wheelhouse.resolve()),
        "venv": str(args.venv.resolve()),
        "expected_isis_version": args.expected_isis_version,
        "status": "passed",
        "checks": checks,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
