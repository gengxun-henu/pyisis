"""Script entry point for matcher comparison experiments."""

from __future__ import annotations

from pathlib import Path
import sys


EXAMPLES_ROOT = Path(__file__).resolve().parents[2]
if str(EXAMPLES_ROOT) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_ROOT))

from controlnet_construct.experiments.matcher_comparison import main


if __name__ == "__main__":
    raise SystemExit(main())
