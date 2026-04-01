#!/usr/bin/env python3
"""Summarize compiler/build failures from a CMake/Ninja build log."""

from __future__ import annotations

import os
import re
import sys
from collections import deque
from pathlib import Path


SOURCE_PATTERN = re.compile(r'([^\s"\']+\.cpp)')
ERROR_PATTERN = re.compile(
    r'(fatal error:| error: |undefined reference to|collect2: error:|ninja: build stopped:)'
)
LINE_NUMBER_PATTERN = re.compile(r'([^\s:]+\.cpp):(\d+)(?::(\d+))?:')


def normalize_path(path_text: str) -> str:
    return path_text.strip().strip("\"'")


def collect_summaries(build_log: Path) -> list[dict[str, str | None]]:
    lines = build_log.read_text(encoding="utf-8", errors="replace").splitlines()
    current_cpp: str | None = None
    recent_lines: deque[str] = deque(maxlen=12)
    summaries: list[dict[str, str | None]] = []
    seen_keys: set[tuple[str, str]] = set()

    for raw_line in lines:
        line = raw_line.rstrip()
        recent_lines.append(line)

        cpp_matches = SOURCE_PATTERN.findall(line)
        if cpp_matches:
            current_cpp = normalize_path(cpp_matches[-1])

        if not ERROR_PATTERN.search(line):
            continue

        annotated_file = current_cpp or "unknown"
        annotated_line = None
        annotated_col = None

        location_match = LINE_NUMBER_PATTERN.search(line)
        if location_match:
            annotated_file = normalize_path(location_match.group(1))
            annotated_line = location_match.group(2)
            annotated_col = location_match.group(3)

        key = (annotated_file, line)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        summaries.append(
            {
                "file": annotated_file,
                "line": annotated_line,
                "col": annotated_col,
                "message": line.strip(),
                "excerpt": "\n".join(recent_lines),
            }
        )

    return summaries


def append_job_summary(summaries: list[dict[str, str | None]]) -> None:
    summary_target = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_target:
        return

    job_summary_path = Path(summary_target)
    job_summary_path.parent.mkdir(parents=True, exist_ok=True)
    with job_summary_path.open("a", encoding="utf-8") as summary_handle:
        summary_handle.write("## Build failure summary\n\n")
        summary_handle.write(
            "The CI parser extracted the following likely failing translation units and recent error context.\n\n"
        )

        for index, item in enumerate(summaries[:10], start=1):
            summary_handle.write(f"### {index}. `{item['file']}`\n\n")
            summary_handle.write(f"- Error: `{item['message']}`\n")
            if item["line"]:
                summary_handle.write(f"- Location: line `{item['line']}`")
                if item["col"]:
                    summary_handle.write(f", column `{item['col']}`")
                summary_handle.write("\n")
            summary_handle.write("\n```text\n")
            summary_handle.write(f"{item['excerpt']}\n")
            summary_handle.write("```\n\n")


def emit_console_summary(summaries: list[dict[str, str | None]]) -> None:
    print("::group::Build failure summary")
    print("Detected compiler/build errors:")
    for index, item in enumerate(summaries[:10], start=1):
        annotation = f"file={item['file']}"
        if item["line"]:
            annotation += f",line={item['line']}"
        if item["col"]:
            annotation += f",col={item['col']}"

        print(f"[{index}] {item['file']}")
        print(item["message"])
        print(item["excerpt"])
        print("-" * 80)
        print(f"::error {annotation}::{item['message']}")
    print("::endgroup::")


def main(argv: list[str]) -> int:
    build_log = Path(argv[1]) if len(argv) > 1 else Path("build/build.log")
    if not build_log.exists():
        print("::warning::Build log not found; skipping failure summary.")
        return 0

    summaries = collect_summaries(build_log)
    if not summaries:
        print(
            "::warning::Build failed, but no compiler-style error summary could be extracted from build.log."
        )
        return 0

    append_job_summary(summaries)
    emit_console_summary(summaries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
