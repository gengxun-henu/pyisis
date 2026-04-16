"""Runtime bootstrap helpers for standalone example scripts."""

from __future__ import annotations

import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILD_PYTHON_DIR = PROJECT_ROOT / "build" / "python"
WORKSPACE_ISISDATA_MOCKUP = PROJECT_ROOT / "tests" / "data" / "isisdata" / "mockup"


def _has_leap_second_kernels(data_root: Path) -> bool:
    lsk_dir = data_root / "base" / "kernels" / "lsk"
    return lsk_dir.exists() and any(lsk_dir.glob("naif*.tls"))


def bootstrap_runtime_environment() -> None:
    """Make example scripts runnable from the repository checkout."""
    configured_isisdata = os.environ.get("ISISDATA")

    if str(BUILD_PYTHON_DIR) not in sys.path and BUILD_PYTHON_DIR.exists():
        sys.path.insert(0, str(BUILD_PYTHON_DIR))

    if configured_isisdata and _has_leap_second_kernels(Path(configured_isisdata)):
        return

    if _has_leap_second_kernels(WORKSPACE_ISISDATA_MOCKUP):
        os.environ["ISISDATA"] = str(WORKSPACE_ISISDATA_MOCKUP)