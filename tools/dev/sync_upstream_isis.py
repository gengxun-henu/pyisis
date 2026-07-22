"""Restore the optional upstream ISIS source reference at its pinned revision."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCK_FILE = PROJECT_ROOT / "reference" / "upstream_isis.lock.json"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class UpstreamSpec:
    repository: str
    revision: str
    commit: str
    destination: Path


def load_spec(lock_file: Path, project_root: Path = PROJECT_ROOT) -> UpstreamSpec:
    """Load and validate the pinned upstream reference specification."""

    payload = json.loads(lock_file.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported upstream reference lock schema")

    repository = str(payload.get("repository", "")).strip()
    revision = str(payload.get("revision", "")).strip()
    commit = str(payload.get("commit", "")).strip().lower()
    destination_text = str(payload.get("destination", "")).strip()
    if not repository or not revision or not destination_text or not COMMIT_RE.fullmatch(commit):
        raise ValueError("Upstream reference lock is missing a valid repository, revision, or commit")

    resolved_root = project_root.resolve()
    destination = (resolved_root / destination_text).resolve()
    if not destination.is_relative_to(resolved_root):
        raise ValueError("Upstream reference destination must stay inside the project root")

    return UpstreamSpec(repository, revision, commit, destination)


def _git_output(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def destination_status(spec: UpstreamSpec) -> tuple[bool, str]:
    """Return whether the optional mirror is usable and a human-readable status."""

    if not spec.destination.exists():
        return False, f"missing optional upstream reference: {spec.destination}"
    if not spec.destination.is_dir():
        return False, f"upstream reference destination is not a directory: {spec.destination}"
    if not (spec.destination / ".git").exists():
        return True, (
            f"upstream reference exists as an unmanaged local snapshot: {spec.destination}; "
            f"future restores use {spec.revision} ({spec.commit})"
        )

    try:
        head = _git_output("-C", str(spec.destination), "rev-parse", "HEAD").lower()
    except (OSError, subprocess.CalledProcessError) as exc:
        return False, f"unable to inspect upstream reference checkout: {exc}"
    if head != spec.commit:
        return False, f"upstream reference is at {head}, expected {spec.commit}"
    return True, f"upstream reference is pinned at {spec.revision} ({spec.commit})"


def restore(spec: UpstreamSpec) -> None:
    """Clone the pinned reference into a missing destination without overwriting files."""

    present, message = destination_status(spec)
    if spec.destination.exists():
        if not present:
            raise RuntimeError(message)
        print(message)
        return

    spec.destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".upstream-isis-",
        dir=spec.destination.parent,
    ) as temp_dir:
        checkout = Path(temp_dir) / "checkout"
        subprocess.run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                spec.repository,
                str(checkout),
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(checkout), "checkout", "--detach", spec.commit],
            check=True,
        )
        head = _git_output("-C", str(checkout), "rev-parse", "HEAD").lower()
        if head != spec.commit:
            raise RuntimeError(f"restored upstream reference is at {head}, expected {spec.commit}")
        shutil.move(str(checkout), str(spec.destination))

    print(f"restored upstream reference {spec.revision} ({spec.commit}) to {spec.destination}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore or inspect the optional pinned upstream ISIS reference source."
    )
    parser.add_argument("--lock-file", type=Path, default=DEFAULT_LOCK_FILE)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Inspect the local reference without cloning it.",
    )
    args = parser.parse_args()

    spec = load_spec(args.lock_file)
    if args.check:
        present, message = destination_status(spec)
        print(message)
        return 0 if present else 1

    restore(spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
