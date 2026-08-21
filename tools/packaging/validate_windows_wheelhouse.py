"""Validate the strict artifact boundary of a Windows PyISIS wheelhouse."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASIC_TEST_LIST = PROJECT_ROOT / "tools" / "packaging" / "basic_tests.txt"
EXPECTED_DISTRIBUTIONS = (
    "usgs-pyisis",
    "usgs-pyisis-runtime-win64",
    "usgs-pyisis-isisdata-minimal",
)
REQUIRED_PIP_FLAGS = {"--isolated", "--no-cache-dir", "--no-index", "--find-links"}
REQUIRED_SANITIZED_NAMES = {
    "CONDA_PREFIX",
    "ISIS_PREFIX",
    "ISISROOT",
    "ISISDATA",
    "PYISIS_DEP_PREFIX",
    "PYISIS_WINDOWS_DEP_PREFIX",
    "PYTHONHOME",
    "PYTHONPATH",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_wheel_members(wheel: Path) -> dict[str, zipfile.ZipInfo]:
    with zipfile.ZipFile(wheel) as archive:
        members = archive.infolist()

    members_by_name: dict[str, zipfile.ZipInfo] = {}
    casefolded_names: dict[str, str] = {}
    for member in members:
        name = member.filename
        parts = name.split("/")
        if (
            not name
            or "\\" in name
            or name.startswith("/")
            or re.match(r"^[A-Za-z]:", name)
            or any(part in {"", ".", ".."} for part in parts)
        ):
            raise ValueError(f"unsafe wheel member in {wheel.name}: {name!r}")
        if name in members_by_name:
            raise ValueError(f"duplicate wheel member in {wheel.name}: {name}")
        normalized = name.casefold()
        if normalized in casefolded_names:
            raise ValueError(
                "case-colliding wheel member in "
                f"{wheel.name}: {casefolded_names[normalized]} and {name}"
            )
        members_by_name[name] = member
        casefolded_names[normalized] = name
    return members_by_name


def _exact_artifacts(
    wheelhouse: Path,
    package_version: str,
    python_abi: str,
    platform_tag: str,
) -> tuple[Path, Path, Path, Path]:
    binding = f"usgs_pyisis-{package_version}-{python_abi}-{python_abi}-{platform_tag}.whl"
    runtime = f"usgs_pyisis_runtime_win64-{package_version}-py3-none-{platform_tag}.whl"
    minimal = f"usgs_pyisis_isisdata_minimal-{package_version}-py3-none-any.whl"
    dependency = "usgs-pyisis-runtime-win64-dll-dependencies.json"

    expected_wheels = {
        wheelhouse / binding,
        wheelhouse / runtime,
        wheelhouse / minimal,
    }
    actual_wheels = set(wheelhouse.glob("*.whl"))
    if actual_wheels != expected_wheels:
        missing = sorted(path.name for path in expected_wheels - actual_wheels)
        unexpected = sorted(path.name for path in actual_wheels - expected_wheels)
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected: {', '.join(unexpected)}")
        suffix = f" ({'; '.join(details)})" if details else ""
        raise FileNotFoundError(f"Expected exactly three wheels in {wheelhouse}{suffix}")

    dependency_path = wheelhouse / dependency
    if not dependency_path.is_file():
        raise FileNotFoundError(
            f"Missing Windows runtime dependency report: {dependency_path}"
        )
    return (
        wheelhouse / binding,
        wheelhouse / runtime,
        wheelhouse / minimal,
        dependency_path,
    )


def _load_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _require_schema_version(payload: dict[str, object], label: str) -> None:
    schema_version = payload.get("schema_version")
    if type(schema_version) is not int or schema_version != 1:
        raise ValueError(f"{label} schema_version must be integer 1")


def _test_modules(test_list: Path) -> list[str]:
    return [
        line
        for raw_line in test_list.read_text(encoding="utf-8").splitlines()
        if (line := raw_line.strip()) and not line.startswith("#")
    ]


def _require_int(check: dict[str, object], field: str, check_id: str) -> int:
    value = check.get(field)
    if type(value) is not int:
        raise ValueError(
            f"Clean-install check {check_id} field {field} must be an integer"
        )
    if value < 0:
        raise ValueError(
            f"Clean-install check {check_id} field {field} cannot be negative"
        )
    return value


def _validate_environment_record(check: dict[str, object], check_id: str) -> None:
    cwd = check.get("cwd")
    environment = check.get("environment")
    if not isinstance(cwd, str) or not cwd:
        raise ValueError(f"Clean-install check {check_id} has malformed cwd")
    if not isinstance(environment, dict):
        raise ValueError(f"Clean-install check {check_id} has malformed environment")
    removed = environment.get("removed")
    set_values = environment.get("set")
    path_entries_removed = environment.get("path_entries_removed")
    if (
        not isinstance(removed, list)
        or any(not isinstance(item, str) for item in removed)
        or not isinstance(set_values, dict)
        or any(
            not isinstance(name, str) or not isinstance(value, str)
            for name, value in set_values.items()
        )
        or not isinstance(path_entries_removed, list)
        or any(not isinstance(item, str) for item in path_entries_removed)
    ):
        raise ValueError(
            f"Clean-install check {check_id} has malformed environment delta"
        )


def _validate_clean_install_checks(
    clean_install_evidence: dict[str, object],
    modules: list[str],
) -> None:
    checks = clean_install_evidence.get("checks")
    if not isinstance(checks, list):
        raise ValueError("Clean-install report checks are missing or malformed")

    checks_by_id: dict[str, dict[str, object]] = {}
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("Clean-install report contains a malformed check")
        check_id = check.get("id")
        command = check.get("command")
        if not isinstance(check_id, str) or not check_id:
            raise ValueError("Clean-install report contains a malformed check id")
        if not isinstance(command, str) or not command:
            raise ValueError(f"Clean-install check {check_id} has malformed command")
        if check_id in checks_by_id:
            raise ValueError(f"Clean-install report contains duplicate check: {check_id}")
        checks_by_id[check_id] = check
        _validate_environment_record(check, check_id)
        passed = _require_int(check, "passed", check_id)
        failed = _require_int(check, "failed", check_id)
        skipped = _require_int(check, "skipped", check_id)
        expected_failures = _require_int(check, "expected_failures", check_id)
        exit_code = _require_int(check, "exit_code", check_id)
        if passed + failed + skipped + expected_failures == 0:
            raise ValueError(f"Clean-install check {check_id} did not pass: no outcomes")
        if failed != 0 or exit_code != 0:
            raise ValueError(f"Clean-install check {check_id} did not pass")

    for check_id in ("wheel-install", "fresh-import"):
        if check_id not in checks_by_id:
            raise ValueError(f"Required clean-install check {check_id} is missing")

    required_ids = {
        "wheel-install",
        "fresh-import",
        *(f"unit-module:{module}" for module in modules),
    }
    if set(checks_by_id) != required_ids:
        missing = sorted(required_ids - set(checks_by_id))
        unexpected = sorted(set(checks_by_id) - required_ids)
        raise ValueError(
            "Clean-install report does not contain the exact required check set "
            f"(missing={missing}, unexpected={unexpected})"
        )


def _validate_dependency_evidence(dependency_evidence: dict[str, object]) -> None:
    _require_schema_version(dependency_evidence, "Dependency report")
    binaries = dependency_evidence.get("binaries")
    unresolved = dependency_evidence.get("unresolved")
    if not isinstance(binaries, list):
        raise ValueError("Dependency report binaries must be a list")
    if not isinstance(unresolved, list):
        raise ValueError("Dependency report unresolved must be a list")
    if unresolved:
        raise FileNotFoundError(
            "unresolved Windows runtime dependencies: "
            + ", ".join(str(item) for item in unresolved)
        )


def _wheel_records(paths: tuple[Path, ...]) -> list[dict[str, object]]:
    return [
        {
            "name": path.name,
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(paths, key=lambda item: item.name)
    ]


def _validate_clean_install_evidence(
    clean_install_evidence: dict[str, object],
    *,
    wheelhouse: Path,
    wheels: tuple[Path, ...],
    package_version: str,
    expected_isis_version: str,
) -> None:
    _require_schema_version(clean_install_evidence, "Clean-install report")
    if clean_install_evidence.get("status") != "passed":
        raise ValueError("Clean-install report status is not passed")
    expected_package = f"usgs-pyisis=={package_version}"
    if clean_install_evidence.get("package") != expected_package:
        raise ValueError(
            f"Clean-install report package must be exactly {expected_package}"
        )
    reported_wheelhouse = clean_install_evidence.get("wheelhouse")
    if not isinstance(reported_wheelhouse, str) or (
        Path(reported_wheelhouse).resolve() != wheelhouse.resolve()
    ):
        raise ValueError("Clean-install report wheelhouse does not match current wheelhouse")
    if clean_install_evidence.get("expected_isis_version") != expected_isis_version:
        raise ValueError(
            "Clean-install report ISIS version does not match expected "
            f"{expected_isis_version}"
        )

    reported_flags = clean_install_evidence.get("pip_install_flags")
    if (
        not isinstance(reported_flags, list)
        or any(not isinstance(flag, str) for flag in reported_flags)
        or not REQUIRED_PIP_FLAGS.issubset(reported_flags)
    ):
        raise ValueError("Clean-install report is missing required isolated pip flags")
    environment_policy = clean_install_evidence.get("sanitized_environment")
    if not isinstance(environment_policy, dict):
        raise ValueError("Clean-install sanitized environment policy is malformed")
    removed_names = environment_policy.get("removed_variable_names")
    if (
        environment_policy.get("remove_all_pip_variables") is not True
        or not isinstance(removed_names, list)
        or any(not isinstance(name, str) for name in removed_names)
        or not REQUIRED_SANITIZED_NAMES.issubset(removed_names)
    ):
        raise ValueError("Clean-install sanitized environment policy is incomplete")

    expected_wheels = _wheel_records(wheels)
    if clean_install_evidence.get("wheel_artifacts") != expected_wheels:
        raise ValueError("Clean-install report wheel artifact bytes do not match current wheels")

    modules = _test_modules(BASIC_TEST_LIST)
    expected_basic_tests = {
        "path": str(BASIC_TEST_LIST.resolve()),
        "sha256": sha256_file(BASIC_TEST_LIST),
        "modules": modules,
    }
    if clean_install_evidence.get("basic_tests") != expected_basic_tests:
        raise ValueError("Clean-install basic test declaration does not match basic_tests.txt")

    venv_text = clean_install_evidence.get("venv")
    if not isinstance(venv_text, str) or not venv_text:
        raise ValueError("Clean-install report venv is missing or malformed")
    venv = Path(venv_text).resolve()
    expected_origin = (venv / "Lib" / "site-packages").resolve()
    distributions = clean_install_evidence.get("installed_distributions")
    if not isinstance(distributions, list):
        raise ValueError("Clean-install installed distribution origins are malformed")
    distributions_by_name: dict[str, dict[str, object]] = {}
    for distribution in distributions:
        if not isinstance(distribution, dict):
            raise ValueError("Clean-install installed distribution origin is malformed")
        name = distribution.get("name")
        version = distribution.get("version")
        location = distribution.get("location")
        if (
            not isinstance(name, str)
            or not isinstance(version, str)
            or not isinstance(location, str)
        ):
            raise ValueError("Clean-install installed distribution origin is malformed")
        normalized_name = name.casefold().replace("_", "-")
        if normalized_name in distributions_by_name:
            raise ValueError(f"Duplicate installed distribution origin: {name}")
        distributions_by_name[normalized_name] = distribution
        resolved_location = Path(location).resolve()
        if resolved_location != expected_origin or not resolved_location.is_relative_to(venv):
            raise ValueError(f"Installed distribution {name} is outside clean venv")
        if version != package_version:
            raise ValueError(f"Installed distribution {name} has unexpected version {version}")
    if set(distributions_by_name) != set(EXPECTED_DISTRIBUTIONS):
        raise ValueError("Clean-install installed distribution set is incomplete")

    _validate_clean_install_checks(clean_install_evidence, modules)
    checks = clean_install_evidence["checks"]
    install_command = next(
        check["command"] for check in checks if check["id"] == "wheel-install"
    )
    if (
        any(flag not in install_command for flag in REQUIRED_PIP_FLAGS)
        or expected_package not in install_command
        or str(wheelhouse) not in install_command
    ):
        raise ValueError("Clean-install pip command does not match isolated wheelhouse install")


def _require_payload(
    wheel: Path,
    members: dict[str, zipfile.ZipInfo],
    required: str,
    description: str,
) -> None:
    member = members.get(required)
    if member is None or member.is_dir():
        raise FileNotFoundError(f"Missing {description} in {wheel.name}")


def validate_wheelhouse(
    wheelhouse: Path,
    clean_install_report: Path,
    package_version: str = "1.3.0rc3",
    python_abi: str = "cp312",
    platform_tag: str = "win_amd64",
    expected_isis_version: str = "9.0.0",
) -> dict[str, object]:
    """Validate a Windows PyISIS wheelhouse and return machine-readable evidence."""
    wheelhouse = Path(wheelhouse).resolve()
    clean_install_report = Path(clean_install_report)
    binding, runtime, minimal, dependency = _exact_artifacts(
        wheelhouse,
        package_version,
        python_abi,
        platform_tag,
    )

    wheel_members = {
        wheel: _validated_wheel_members(wheel)
        for wheel in (binding, runtime, minimal)
    }
    forbidden_members = [
        f"{wheel.name}:{name}"
        for wheel, members in wheel_members.items()
        for name in members
        if name.casefold().endswith((".exe", ".xml"))
        or "/bin/xml/" in f"/{name.casefold()}"
    ]
    if forbidden_members:
        raise ValueError(
            "forbidden ISIS APP payload: " + ", ".join(sorted(forbidden_members))
        )

    _require_payload(
        binding,
        wheel_members[binding],
        f"isis_pybind/_isis_core.{python_abi}-{platform_tag}.pyd",
        "main PyISIS extension payload",
    )
    for required in (
        "pyisis_runtime/vendor/isis/lib/isis.dll",
        "pyisis_runtime/vendor/isis/lib/Camera.plugin",
    ):
        _require_payload(
            runtime,
            wheel_members[runtime],
            required,
            f"required Windows runtime payload {required}",
        )
    _require_payload(
        minimal,
        wheel_members[minimal],
        "pyisis_isisdata_minimal/data/base/kernels/lsk/naif0012.tls",
        "minimal ISISDATA kernel payload",
    )

    dependency_evidence = _load_json(dependency)
    _validate_dependency_evidence(dependency_evidence)

    clean_install_evidence = _load_json(clean_install_report)
    _validate_clean_install_evidence(
        clean_install_evidence,
        wheelhouse=wheelhouse,
        wheels=(binding, runtime, minimal),
        package_version=package_version,
        expected_isis_version=expected_isis_version,
    )

    retained_inputs = (binding, runtime, minimal, dependency)
    artifacts = [
        {
            "path": str(path),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(retained_inputs, key=lambda item: item.name)
    ]
    return {
        "schema_version": 1,
        "package_version": package_version,
        "python_abi": python_abi,
        "platform_tag": platform_tag,
        "expected_isis_version": expected_isis_version,
        "status": "passed",
        "clean_install": clean_install_evidence,
        "dependency_closure": dependency_evidence,
        "artifacts": artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheelhouse", required=True, type=Path)
    parser.add_argument("--clean-install-report", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--package-version", default="1.3.0rc3")
    parser.add_argument("--python-abi", default="cp312")
    parser.add_argument("--platform-tag", default="win_amd64")
    parser.add_argument("--expected-isis-version", default="9.0.0")
    args = parser.parse_args()

    args.report.unlink(missing_ok=True)
    report = validate_wheelhouse(
        args.wheelhouse.resolve(),
        args.clean_install_report.resolve(),
        package_version=args.package_version,
        python_abi=args.python_abi,
        platform_tag=args.platform_tag,
        expected_isis_version=args.expected_isis_version,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
