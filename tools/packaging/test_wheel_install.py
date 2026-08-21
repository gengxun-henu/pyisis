"""Verify usgs-pyisis wheels from a clean virtual environment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
import venv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UNIT_TEST_DIR = PROJECT_ROOT / "tests" / "unitTest"
MINIMAL_DATA_DISTRIBUTION = "usgs-pyisis-isisdata-minimal"
SANITIZED_VARIABLE_NAMES = (
    "CONDA_PREFIX",
    "ISIS_PREFIX",
    "ISISROOT",
    "ISISDATA",
    "PYISIS_DEP_PREFIX",
    "PYISIS_WINDOWS_DEP_PREFIX",
    "PYTHONHOME",
    "PYTHONPATH",
)
PIP_INSTALL_FLAGS = ("--isolated", "--no-cache-dir", "--no-index", "--find-links")


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
    roots = tuple(Path(env[name]).resolve() for name in root_names if env.get(name))

    for name in tuple(env):
        if name in SANITIZED_VARIABLE_NAMES or name.upper().startswith("PIP_"):
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
    env["ISIS_PYBIND_BUILD_DIR"] = str(PROJECT_ROOT / ".clean-wheel-no-build-python")
    return env


def _environment_delta(env: dict[str, str]) -> dict[str, object]:
    removed = sorted(
        name
        for name in os.environ
        if name not in env
        and (name in SANITIZED_VARIABLE_NAMES or name.upper().startswith("PIP_"))
    )
    set_values = {
        name: env[name]
        for name in (
            "ISIS_PYBIND_BUILD_DIR",
            "PYISIS_EXPECTED_ISIS_VERSION",
            "PYISIS_INSTALL_METADATA_REPORT",
            "PYTHONPATH",
        )
        if env.get(name) != os.environ.get(name)
    }
    before_path = [part for part in os.environ.get("PATH", "").split(os.pathsep) if part]
    after_path = {part.casefold() for part in env.get("PATH", "").split(os.pathsep) if part}
    return {
        "removed": removed,
        "set": set_values,
        "path_entries_removed": [
            part for part in before_path if part.casefold() not in after_path
        ],
    }


def run(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> None:
    subprocess.run(command, check=True, env=env, cwd=cwd)


def _run_unittest(
    command: list[str],
    *,
    env: dict[str, str],
    cwd: Path,
) -> tuple[int, int, int, int]:
    result = subprocess.run(
        command,
        check=False,
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    sys.stdout.write(result.stdout)
    sys.stdout.flush()
    sys.stderr.write(result.stderr)
    sys.stderr.flush()
    counts = _parse_unittest_summary(result.stdout + "\n" + result.stderr)
    if result.returncode:
        raise subprocess.CalledProcessError(result.returncode, command)
    return counts


def _parse_unittest_summary(output: str) -> tuple[int, int, int, int]:
    ran_matches = list(re.finditer(r"^Ran (\d+) tests? in .+$", output, re.MULTILINE))
    status_matches = list(
        re.finditer(r"^(OK|FAILED)(?: \(([^)]*)\))?$", output, re.MULTILINE)
    )
    if not ran_matches or not status_matches:
        raise ValueError("Unable to parse unittest run summary")

    ran = int(ran_matches[-1].group(1))
    status = status_matches[-1]
    details = {
        key.strip(): int(value)
        for key, value in re.findall(r"([a-z ]+)=(\d+)", status.group(2) or "")
    }
    failed = (
        details.get("failures", 0)
        + details.get("errors", 0)
        + details.get("unexpected successes", 0)
    )
    skipped = details.get("skipped", 0)
    expected_failures = details.get("expected failures", 0)
    passed = ran - failed - skipped - expected_failures
    if passed < 0 or (status.group(1) == "OK" and failed):
        raise ValueError("Inconsistent unittest run summary")
    return passed, failed, skipped, expected_failures


def _command_text(command: list[str]) -> str:
    return subprocess.list2cmdline(command) if sys.platform == "win32" else shlex.join(command)


def _check(
    check_id: str,
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    passed: int,
    failed: int = 0,
    skipped: int = 0,
    expected_failures: int = 0,
    exit_code: int = 0,
) -> dict[str, object]:
    return {
        "id": check_id,
        "command": _command_text(command),
        "cwd": str(cwd.resolve()),
        "environment": _environment_delta(env),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "expected_failures": expected_failures,
        "exit_code": exit_code,
    }


def _test_modules(test_list: Path) -> list[str]:
    return [
        line
        for raw_line in test_list.read_text(encoding="utf-8").splitlines()
        if (line := raw_line.strip()) and not line.startswith("#")
    ]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _wheel_artifacts(wheelhouse: Path) -> list[dict[str, object]]:
    return [
        {
            "name": wheel.name,
            "size": wheel.stat().st_size,
            "sha256": _sha256_file(wheel),
        }
        for wheel in sorted(wheelhouse.glob("*.whl"), key=lambda path: path.name)
    ]


def _expected_distributions(
    package: str,
    additional_distributions: tuple[str, ...],
) -> tuple[str, ...]:
    distribution = re.split(r"[<>=!~;\s\[]", package, maxsplit=1)[0]
    if not distribution:
        raise ValueError(f"Unable to resolve distribution name from package: {package!r}")
    return tuple(
        dict.fromkeys((distribution, MINIMAL_DATA_DISTRIBUTION, *additional_distributions))
    )


def _installed_distribution_command(
    python: Path,
    expected_distributions: tuple[str, ...],
) -> list[str]:
    script = "\n".join(
        (
            "import json, os",
            "from importlib import metadata",
            "from pathlib import Path",
            "import pyisis, isis_pybind",
            "status = pyisis.data_status()",
            "print(status.message)",
            "assert os.environ.get('ISISROOT')",
            "assert status.usable_for_smoke_tests",
            "expected = os.environ.get('PYISIS_EXPECTED_ISIS_VERSION')",
            "assert expected is None or isis_pybind.__isis_version__ == expected",
            f"names = {expected_distributions!r}",
            "origins = []",
            "for requested_name in names:",
            "    distribution = metadata.distribution(requested_name)",
            "    origins.append({'name': distribution.metadata['Name'], 'version': distribution.version, 'location': str(Path(distribution.locate_file('')).resolve())})",
            "Path(os.environ['PYISIS_INSTALL_METADATA_REPORT']).write_text(json.dumps(origins), encoding='utf-8')",
        )
    )
    return [str(python), "-c", script]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheelhouse", required=True, type=Path)
    parser.add_argument("--venv", required=True, type=Path)
    parser.add_argument("--package", default="usgs-pyisis")
    parser.add_argument(
        "--additional-distribution",
        action="append",
        default=[],
        help="Additional installed distribution metadata to verify; may be repeated.",
    )
    parser.add_argument("--expected-isis-version")
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--test-list",
        type=Path,
        help="Optional file containing unittest modules to run after the clean-wheel smoke test.",
    )
    args = parser.parse_args()

    if args.report:
        args.report.unlink(missing_ok=True)

    wheelhouse = args.wheelhouse.resolve()
    clean_venv = args.venv.resolve()
    test_list = args.test_list.resolve() if args.test_list else None
    if clean_venv.exists():
        raise FileExistsError(f"Refusing to reuse existing venv: {clean_venv}")

    wheel_artifacts = _wheel_artifacts(wheelhouse)
    basic_tests = None
    modules: list[str] = []
    if test_list:
        modules = _test_modules(test_list)
        basic_tests = {
            "path": str(test_list),
            "sha256": _sha256_file(test_list),
            "modules": modules,
        }

    venv.EnvBuilder(with_pip=True).create(clean_venv)
    python = _python_executable(clean_venv)
    checks: list[dict[str, object]] = []

    install_env = _verification_environment()
    install_command = [
        str(python),
        "-m",
        "pip",
        "--isolated",
        "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links",
        str(wheelhouse),
        args.package,
    ]
    run(install_command, env=install_env, cwd=clean_venv)
    checks.append(
        _check(
            "wheel-install",
            install_command,
            cwd=clean_venv,
            env=install_env,
            passed=1,
        )
    )

    metadata_report = clean_venv / "installed-distributions.json"
    verification_env = _verification_environment()
    verification_env["PYISIS_INSTALL_METADATA_REPORT"] = str(metadata_report)
    if args.expected_isis_version:
        verification_env["PYISIS_EXPECTED_ISIS_VERSION"] = args.expected_isis_version
    expected_distributions = _expected_distributions(
        args.package,
        tuple(args.additional_distribution),
    )
    import_command = _installed_distribution_command(python, expected_distributions)
    run(import_command, env=verification_env, cwd=clean_venv)
    checks.append(
        _check(
            "fresh-import",
            import_command,
            cwd=clean_venv,
            env=verification_env,
            passed=1,
        )
    )
    installed_distributions = json.loads(metadata_report.read_text(encoding="utf-8"))
    metadata_report.unlink()

    if test_list:
        unit_env = _unit_test_environment()
        for module in modules:
            module_command = [str(python), "-m", "unittest", module, "-v"]
            passed, failed, skipped, expected_failures = _run_unittest(
                module_command,
                env=unit_env,
                cwd=PROJECT_ROOT,
            )
            checks.append(
                _check(
                    f"unit-module:{module}",
                    module_command,
                    cwd=PROJECT_ROOT,
                    env=unit_env,
                    passed=passed,
                    failed=failed,
                    skipped=skipped,
                    expected_failures=expected_failures,
                )
            )

    payload = {
        "schema_version": 1,
        "package": args.package,
        "wheelhouse": str(wheelhouse),
        "venv": str(clean_venv),
        "expected_isis_version": args.expected_isis_version,
        "expected_distributions": list(expected_distributions),
        "pip_install_flags": list(PIP_INSTALL_FLAGS),
        "sanitized_environment": {
            "removed_variable_names": list(SANITIZED_VARIABLE_NAMES),
            "remove_all_pip_variables": True,
        },
        "wheel_artifacts": wheel_artifacts,
        "basic_tests": basic_tests,
        "installed_distributions": installed_distributions,
        "status": "passed",
        "checks": checks,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
