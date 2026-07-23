"""Require auditwheel reports to satisfy a configured manylinux policy."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


POLICY_RE = re.compile(
    r'is\s+consistent\s+with\s+the\s+following\s+platform\s+tag:\s+"([^"]+)"\.'
)
LEGACY_POLICIES = {
    "manylinux1": (2, 5),
    "manylinux2010": (2, 12),
    "manylinux2014": (2, 17),
}


def _parse_target(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)", value)
    if match is None:
        raise ValueError(f"Expected manylinux target MAJOR.MINOR, got: {value}")
    return int(match.group(1)), int(match.group(2))


def _policy_version(policy: str, architecture: str) -> tuple[int, int]:
    suffix = f"_{architecture}"
    if not policy.endswith(suffix):
        raise ValueError(
            f"auditwheel policy architecture does not match {architecture}: {policy}"
        )
    base = policy[: -len(suffix)]
    if base in LEGACY_POLICIES:
        return LEGACY_POLICIES[base]
    match = re.fullmatch(r"manylinux_(\d+)_(\d+)", base)
    if match is None:
        raise ValueError(f"auditwheel did not certify a manylinux policy: {policy}")
    return int(match.group(1)), int(match.group(2))


def validate_report(
    report_path: Path,
    target: tuple[int, int],
    architecture: str,
) -> str:
    report = report_path.read_text(encoding="utf-8")
    match = POLICY_RE.search(report)
    if match is None:
        raise ValueError(f"Missing auditwheel policy result in {report_path}")
    policy = match.group(1)
    version = _policy_version(policy, architecture)
    if version > target:
        raise ValueError(
            f"auditwheel policy {policy} exceeds target manylinux_"
            f"{target[0]}_{target[1]}_{architecture}"
        )
    return policy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="append", required=True, type=Path)
    parser.add_argument("--target", default="2.28")
    parser.add_argument("--architecture", default="x86_64")
    args = parser.parse_args()

    target = _parse_target(args.target)
    for report_path in args.report:
        policy = validate_report(report_path, target, args.architecture)
        print(f"{report_path}: {policy}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
