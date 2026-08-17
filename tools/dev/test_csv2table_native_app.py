"""Validate csv2table and tabledump through installed native ISIS applications."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
from typing import Any


TABLE_NAME = "PyIsisNativeAppProbe"
PROBE_CSV_NAME = "csv2table_native_app_probe.csv"
PROBE_CUBE_NAME = "csv2table_native_app_input.cub"
PROBE_DUMP_NAME = "csv2table_native_app_probe.txt"


@dataclass(frozen=True)
class ValidationConfig:
    """Paths and ISIS version requested for one native-process validation run."""

    isis_version: str
    input_cube_path: Path
    work_dir: Path
    report_path: Path
    bin_dir: Path | None = None

    @property
    def csv_path(self) -> Path:
        return self.work_dir / PROBE_CSV_NAME

    @property
    def cube_path(self) -> Path:
        return self.work_dir / PROBE_CUBE_NAME

    @property
    def table_dump_path(self) -> Path:
        return self.work_dir / PROBE_DUMP_NAME

    @property
    def csv2table_executable(self) -> Path:
        return _configured_executable_path("csv2table", self.bin_dir)

    @property
    def tabledump_executable(self) -> Path:
        return _configured_executable_path("tabledump", self.bin_dir)


def _configured_executable_path(name: str, bin_dir: Path | None) -> Path:
    if bin_dir is not None:
        return bin_dir / name
    found = shutil.which(name)
    return Path(found) if found is not None else Path(name)


def _resolve_executable(name: str, bin_dir: Path | None) -> Path | None:
    if bin_dir is None:
        found = shutil.which(name)
        return Path(found) if found is not None else None

    candidates = [bin_dir / name]
    if os.name == "nt":
        candidates.extend((bin_dir / f"{name}.exe", bin_dir / f"{name}.cmd"))
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_record(path: Path) -> dict[str, str | None]:
    return {"path": str(path), "sha256": _sha256(path)}


def _reported_isis_version(help_output: str) -> str | None:
    match = re.search(r"\bISIS\s+(\d+(?:\.\d+){1,3})\b", help_output, re.IGNORECASE)
    return match.group(1) if match else None


def _write_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = report_path.with_name(f"{report_path.name}.tmp")
    temporary_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary_path, report_path)


def validate_csv2table(config: ValidationConfig) -> dict[str, Any]:
    """Run the native csv2table probe and return its schema-1 JSON report."""
    csv2table_executable = _resolve_executable("csv2table", config.bin_dir)
    tabledump_executable = _resolve_executable("tabledump", config.bin_dir)
    xml_directory = (
        config.bin_dir / "xml"
        if config.bin_dir is not None
        else (
            csv2table_executable.parent / "xml"
            if csv2table_executable is not None
            else None
        )
    )
    xml_path = xml_directory / "csv2table.xml" if xml_directory is not None else None
    report: dict[str, Any] = {
        "schema": 1,
        "platform": {"os": platform.system(), "architecture": platform.machine()},
        "isis_version": {"requested": config.isis_version, "reported": None},
        "paths": {
            "csv2table_executable": (
                str(csv2table_executable) if csv2table_executable is not None else None
            ),
            "tabledump_executable": (
                str(tabledump_executable) if tabledump_executable is not None else None
            ),
            "csv2table_xml": str(xml_path) if xml_path is not None else None,
        },
        "commands": [],
        "files": {},
        "failures": [],
        "summary": {"passed": 0, "failed": 0, "skipped": 0},
    }

    def fail(message: str) -> None:
        report["summary"]["failed"] += 1
        report["failures"].append(message)

    if csv2table_executable is None:
        fail("missing csv2table executable")
    if tabledump_executable is None:
        fail("missing tabledump executable")
    if xml_path is None or not xml_path.is_file():
        fail("missing csv2table XML")
    if report["summary"]["failed"]:
        report["files"] = {
            "source_cube": _file_record(config.input_cube_path),
            "csv": _file_record(config.csv_path),
            "working_cube": _file_record(config.cube_path),
            "tabledump": _file_record(config.table_dump_path),
        }
        _write_report(config.report_path, report)
        return report

    try:
        config.work_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config.input_cube_path, config.cube_path)
        config.csv_path.write_text(
            "Sample,Line,Name\n1.0,2,alpha\n3.5,4,beta\n", encoding="utf-8"
        )
    except OSError as error:
        fail(f"failed to prepare probe inputs: {error}")
        report["files"] = {
            "source_cube": _file_record(config.input_cube_path),
            "csv": _file_record(config.csv_path),
            "working_cube": _file_record(config.cube_path),
            "tabledump": _file_record(config.table_dump_path),
        }
        _write_report(config.report_path, report)
        return report

    def run_required(name: str, arguments: list[str]) -> tuple[bool, subprocess.CompletedProcess[str] | None]:
        try:
            completed = subprocess.run(
                arguments, shell=False, text=True, capture_output=True
            )
        except OSError as error:
            report["commands"].append(
                {
                    "name": name,
                    "arguments": arguments,
                    "exit_code": None,
                    "stdout": "",
                    "stderr": str(error),
                }
            )
            fail(f"{name} could not start: {error}")
            return False, None

        report["commands"].append(
            {
                "name": name,
                "arguments": arguments,
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
        if completed.returncode != 0:
            fail(f"{name} exited with code {completed.returncode}: {completed.stderr}")
            return False, completed
        report["summary"]["passed"] += 1
        return True, completed

    help_arguments = [str(csv2table_executable), "-HELP"]
    successful, completed = run_required("csv2table-help", help_arguments)
    if successful and completed is not None:
        report["isis_version"]["reported"] = _reported_isis_version(completed.stdout)

    if successful:
        csv2table_arguments = [
            str(csv2table_executable),
            f"CSV={config.csv_path}",
            f"TO={config.cube_path}",
            f"TABLENAME={TABLE_NAME}",
        ]
        successful, _ = run_required("csv2table", csv2table_arguments)

    if successful:
        tabledump_arguments = [
            str(tabledump_executable),
            f"FROM={config.cube_path}",
            f"NAME={TABLE_NAME}",
            f"TO={config.table_dump_path}",
        ]
        successful, _ = run_required("tabledump", tabledump_arguments)
        if successful:
            try:
                dump_text = config.table_dump_path.read_text(encoding="utf-8")
            except OSError as error:
                report["summary"]["passed"] -= 1
                fail(f"tabledump output could not be read: {error}")
            else:
                if TABLE_NAME not in dump_text:
                    report["summary"]["passed"] -= 1
                    fail(f"tabledump output does not contain {TABLE_NAME}")

    report["files"] = {
        "source_cube": _file_record(config.input_cube_path),
        "csv": _file_record(config.csv_path),
        "working_cube": _file_record(config.cube_path),
        "tabledump": _file_record(config.table_dump_path),
    }
    _write_report(config.report_path, report)
    return report


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--isis-version", required=True)
    parser.add_argument("--input-cube", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--bin-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    report = validate_csv2table(
        ValidationConfig(
            isis_version=arguments.isis_version,
            input_cube_path=arguments.input_cube,
            work_dir=arguments.work_dir,
            report_path=arguments.report,
            bin_dir=arguments.bin_dir,
        )
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
