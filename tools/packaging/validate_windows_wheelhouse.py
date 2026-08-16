"""Validate the strict artifact boundary of a Windows PyISIS wheelhouse."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _wheel_members(wheel: Path) -> list[str]:
    with zipfile.ZipFile(wheel) as archive:
        return [member.filename for member in archive.infolist()]


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
        raise FileNotFoundError(
            f"Expected exactly three wheels in {wheelhouse}{suffix}"
        )

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


def _validate_clean_install_checks(clean_install_evidence: dict[str, object]) -> None:
    checks = clean_install_evidence.get("checks")
    if not isinstance(checks, list):
        raise ValueError("Clean-install report checks are missing or malformed")

    checks_by_id: dict[str, dict[str, object]] = {}
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get("id"), str):
            raise ValueError("Clean-install report contains a malformed check")
        check_id = check["id"]
        if check_id in checks_by_id:
            raise ValueError(f"Clean-install report contains duplicate check: {check_id}")
        checks_by_id[check_id] = check
        if (
            check.get("passed") != 1
            or check.get("failed", 0) != 0
            or check.get("skipped", 0) != 0
            or check.get("exit_code", 0) != 0
        ):
            raise ValueError(f"Clean-install check {check_id} did not pass")

    for check_id in ("wheel-install", "fresh-import"):
        if check_id not in checks_by_id:
            raise ValueError(f"Required clean-install check {check_id} is missing")


def validate_wheelhouse(
    wheelhouse: Path,
    clean_install_report: Path,
    package_version: str = "1.3.0rc2",
    python_abi: str = "cp312",
    platform_tag: str = "win_amd64",
    expected_isis_version: str = "9.0.0",
) -> dict[str, object]:
    """Validate a Windows PyISIS wheelhouse and return machine-readable evidence."""
    wheelhouse = Path(wheelhouse)
    clean_install_report = Path(clean_install_report)
    binding, runtime, minimal, dependency = _exact_artifacts(
        wheelhouse,
        package_version,
        python_abi,
        platform_tag,
    )

    binding_members = _wheel_members(binding)
    expected_binding_member = f"isis_pybind/_isis_core.{python_abi}-{platform_tag}.pyd"
    if expected_binding_member not in binding_members:
        raise FileNotFoundError(
            f"Missing main PyISIS extension payload in {binding.name}"
        )

    runtime_members = _wheel_members(runtime)
    required_runtime_members = {
        "pyisis_runtime/vendor/isis/lib/isis.dll",
        "pyisis_runtime/vendor/isis/lib/Camera.plugin",
    }
    missing_runtime_members = sorted(set(required_runtime_members) - set(runtime_members))
    if missing_runtime_members:
        raise FileNotFoundError(
            f"Missing required Windows runtime payload: {', '.join(missing_runtime_members)}"
        )
    forbidden_runtime_members = [
        member
        for member in runtime_members
        if member.lower().endswith((".exe", ".xml")) or "/bin/xml/" in member.lower()
    ]
    if forbidden_runtime_members:
        raise ValueError(
            "forbidden ISIS APP payload: "
            + ", ".join(sorted(forbidden_runtime_members))
        )

    minimal_members = _wheel_members(minimal)
    if "pyisis_isisdata_minimal/data/base/kernels/lsk/naif0012.tls" not in minimal_members:
        raise FileNotFoundError(
            f"Missing minimal ISISDATA kernel payload in {minimal.name}"
        )

    dependency_evidence = _load_json(dependency)
    unresolved = dependency_evidence.get("unresolved", [])
    if unresolved:
        raise FileNotFoundError(
            "unresolved Windows runtime dependencies: "
            + ", ".join(str(item) for item in unresolved)
        )

    clean_install_evidence = _load_json(clean_install_report)
    if clean_install_evidence.get("status") != "passed":
        raise ValueError(
            f"Clean-install report status is not passed: {clean_install_report}"
        )
    if clean_install_evidence.get("expected_isis_version") != expected_isis_version:
        raise ValueError(
            "Clean-install report ISIS version does not match expected "
            f"{expected_isis_version}: {clean_install_report}"
        )
    _validate_clean_install_checks(clean_install_evidence)

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
    parser.add_argument("--package-version", default="1.3.0rc2")
    parser.add_argument("--python-abi", default="cp312")
    parser.add_argument("--platform-tag", default="win_amd64")
    parser.add_argument("--expected-isis-version", default="9.0.0")
    args = parser.parse_args()

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
