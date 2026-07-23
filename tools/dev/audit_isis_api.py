"""Generate an ISIS 9/10 header audit for the current pybind source.

Author: Geng Xun
Created: 2026-07-23
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_ROOT = PROJECT_ROOT / "src"
DEFAULT_ISIS9_ROOT = PROJECT_ROOT / "reference" / "upstream_isis" / "9.0.0"
LEGACY_ISIS9_ROOT = PROJECT_ROOT / "reference" / "upstream_isis"
DEFAULT_ISIS10_ROOT = PROJECT_ROOT / "reference" / "upstream_isis" / "10.0.0"
DEFAULT_CSV = (
    PROJECT_ROOT / "reference" / "compatibility" / "isis9-isis10-header-matrix.csv"
)
DEFAULT_REPORT = (
    PROJECT_ROOT / "reference" / "compatibility" / "isis9-isis10-symbol-report.md"
)

INCLUDE_RE = re.compile(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', re.MULTILINE)
PYBIND_CLASS_RE = re.compile(
    r"py::class_\s*<\s*(?:(?:Isis|pyisis)::)?([A-Za-z_][A-Za-z0-9_]*)"
)
GUI_BASE_RE = re.compile(
    r":\s*public\s+(?:QWidget|QDialog|QMainWindow|QGraphics[A-Za-z0-9_]*|"
    r"QAbstractItemModel|QAbstractItemView)\b"
)
QT_OBSERVER_RE = re.compile(
    r"\bQ_OBJECT\b|^\s*(?:public|protected|private)?\s*(?:Q_)?(?:signals|slots)\s*:",
    re.MULTILINE,
)
SOURCE_SUFFIXES = {".cpp", ".cc", ".cxx", ".h", ".hpp"}
HEADER_SUFFIXES = {".h", ".hpp"}
KNOWN_HEADER_RENAMES = {
    "Endian.h": "IEndian.h",
}

CSV_FIELDS = (
    "binding_file",
    "header",
    "bound_symbols",
    "gui_status",
    "isis9_status",
    "isis10_status",
    "comparison",
    "replacement_hint",
    "isis9_paths",
    "isis10_paths",
)


@dataclass(frozen=True)
class BindingReference:
    binding_file: str
    header: str
    bound_symbols: tuple[str, ...]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_binding_references(
    source_root: Path,
    project_root: Path = PROJECT_ROOT,
) -> list[BindingReference]:
    """Extract included headers and registered class names from binding files."""

    references: list[BindingReference] = []
    for source_file in sorted(source_root.rglob("*")):
        if not source_file.is_file() or source_file.suffix not in SOURCE_SUFFIXES:
            continue
        text = _read_text(source_file)
        headers = sorted(
            {
                Path(include).name
                for include in INCLUDE_RE.findall(text)
                if Path(include).suffix in HEADER_SUFFIXES
            }
        )
        symbols = tuple(sorted(set(PYBIND_CLASS_RE.findall(text))))
        binding_file = source_file.relative_to(project_root).as_posix()
        references.extend(
            BindingReference(binding_file, header, symbols) for header in headers
        )
    return references


def build_header_index(root: Path) -> dict[str, tuple[Path, ...]]:
    """Index candidate ISIS headers by basename."""

    index: dict[str, list[Path]] = defaultdict(list)
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in HEADER_SUFFIXES:
            index[path.name].append(path)
    return {name: tuple(sorted(paths)) for name, paths in index.items()}


def _relative_paths(paths: Iterable[Path], root: Path) -> str:
    return ";".join(path.relative_to(root).as_posix() for path in paths)


def _header_status(paths: tuple[Path, ...]) -> str:
    if not paths:
        return "missing"
    if len(paths) == 1:
        return "present"
    return "ambiguous"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _comparison(
    isis9_paths: tuple[Path, ...],
    isis10_paths: tuple[Path, ...],
    replacement_paths: tuple[Path, ...] = (),
) -> str:
    if not isis9_paths:
        return "missing_in_isis9"
    if not isis10_paths:
        if replacement_paths:
            return "renamed_review_required"
        return "missing_in_isis10"
    if len(isis9_paths) != 1 or len(isis10_paths) != 1:
        return "ambiguous_header"
    if _sha256(isis9_paths[0]) == _sha256(isis10_paths[0]):
        return "identical_text"
    return "changed_review_required"


def _gui_status(paths: tuple[Path, ...]) -> str:
    if not paths:
        return "unknown"
    if any("/qisis/" in f"/{path.as_posix()}/" for path in paths):
        return "gui_excluded"
    text = "\n".join(_read_text(path) for path in paths)
    if GUI_BASE_RE.search(text):
        return "gui_excluded"
    if QT_OBSERVER_RE.search(text):
        return "qt_observer_review"
    return "non_gui"


def create_audit_rows(
    source_root: Path,
    isis9_root: Path,
    isis10_root: Path,
    project_root: Path = PROJECT_ROOT,
) -> list[dict[str, str]]:
    """Create rows for headers referenced by the current binding source."""

    references = extract_binding_references(source_root, project_root)
    isis9_index = build_header_index(isis9_root)
    isis10_index = build_header_index(isis10_root)
    rows: list[dict[str, str]] = []

    for reference in references:
        isis9_paths = isis9_index.get(reference.header, ())
        isis10_paths = isis10_index.get(reference.header, ())
        replacement_header = KNOWN_HEADER_RENAMES.get(reference.header, "")
        replacement_paths = isis10_index.get(replacement_header, ())
        if not isis9_paths and not isis10_paths:
            continue
        gui_status = _gui_status(isis10_paths or isis9_paths)
        if gui_status == "gui_excluded":
            continue
        rows.append(
            {
                "binding_file": reference.binding_file,
                "header": reference.header,
                "bound_symbols": ";".join(reference.bound_symbols),
                "gui_status": gui_status,
                "isis9_status": _header_status(isis9_paths),
                "isis10_status": _header_status(isis10_paths),
                "comparison": _comparison(
                    isis9_paths,
                    isis10_paths,
                    replacement_paths,
                ),
                "replacement_hint": (
                    f"{replacement_header}:"
                    f"{_relative_paths(replacement_paths, isis10_root)}"
                    if replacement_paths
                    else ""
                ),
                "isis9_paths": _relative_paths(isis9_paths, isis9_root),
                "isis10_paths": _relative_paths(isis10_paths, isis10_root),
            }
        )
    return rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    rows: list[dict[str, str]],
    output_path: Path,
    isis9_root: Path,
    isis10_root: Path,
    isis9_label: str = "",
    isis10_label: str = "",
    matrix_name: str = "isis9-isis10-header-matrix.csv",
) -> None:
    unique_rows: dict[str, dict[str, str]] = {}
    binding_files: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        unique_rows.setdefault(row["header"], row)
        binding_files[row["header"]].add(row["binding_file"])

    counts: dict[str, int] = defaultdict(int)
    for row in unique_rows.values():
        counts[row["comparison"]] += 1
    review_rows = [
        row
        for row in unique_rows.values()
        if row["comparison"] != "identical_text"
        or row["gui_status"] == "qt_observer_review"
    ]

    def display_path(path: Path) -> str:
        resolved = path.resolve()
        try:
            return resolved.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            return resolved.as_posix()

    lines = [
        "# ISIS 9 / ISIS 10 当前绑定头文件审计",
        "",
        "> 自动生成文件。文本变化只表示需要人工 API 审阅，不等同于 ABI 不兼容。",
        "",
        f"- ISIS 9 source: `{isis9_label or display_path(isis9_root)}`",
        f"- ISIS 10 source: `{isis10_label or display_path(isis10_root)}`",
        f"- 当前 binding-header 引用行数（过滤 GUI 后）: {len(rows)}",
        f"- 当前 ISIS 头文件数: {len(unique_rows)}",
        f"- 文本一致: {counts['identical_text']}",
        f"- 需要人工复核: {counts['changed_review_required']}",
        f"- 已识别头文件重命名候选: {counts['renamed_review_required']}",
        f"- ISIS 9 缺失: {counts['missing_in_isis9']}",
        f"- ISIS 10 缺失: {counts['missing_in_isis10']}",
        f"- 路径不唯一: {counts['ambiguous_header']}",
        "",
        "## 需要复核的头文件",
        "",
        "| Bindings | Header | Comparison | Replacement | GUI status |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        "| `{bindings}` | `{header}` | `{comparison}` | `{replacement_hint}` | "
        "`{gui_status}` |".format(
            bindings=", ".join(sorted(binding_files[row["header"]])),
            **row,
        )
        for row in review_rows
    )
    if not review_rows:
        lines.append("| — | — | 无 | — | — |")
    lines.extend(
        [
            "",
            "## 使用边界",
            "",
            "- 编译签名必须继续以目标 conda 或 Windows prefix 的头文件为准。",
            "- `changed_review_required` 需要进一步比较声明、链接符号和行为。",
            "- `renamed_review_required` 是已定位的候选替代头，仍需编译验证。",
            "- `qt_observer_review` 表示类中含 Qt observer API；signals/slots 默认不绑定。",
            f"- 详细逐行数据见 `{matrix_name}`。",
            "",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _existing_isis9_default() -> Path:
    if DEFAULT_ISIS9_ROOT.is_dir():
        return DEFAULT_ISIS9_ROOT
    return LEGACY_ISIS9_ROOT


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit current pybind header references across ISIS 9 and ISIS 10."
    )
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--isis9-root", type=Path, default=_existing_isis9_default())
    parser.add_argument("--isis10-root", type=Path, default=DEFAULT_ISIS10_ROOT)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output-report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--isis9-label",
        default="",
        help="Portable source label for the generated report.",
    )
    parser.add_argument(
        "--isis10-label",
        default="",
        help="Portable source label for the generated report.",
    )
    args = parser.parse_args()

    for label, path in (
        ("binding source", args.source_root),
        ("ISIS 9 source", args.isis9_root),
        ("ISIS 10 source", args.isis10_root),
    ):
        if not path.is_dir():
            parser.error(f"{label} directory does not exist: {path}")

    rows = create_audit_rows(
        args.source_root.resolve(),
        args.isis9_root.resolve(),
        args.isis10_root.resolve(),
        PROJECT_ROOT,
    )
    write_csv(rows, args.output_csv)
    write_report(
        rows,
        args.output_report,
        args.isis9_root,
        args.isis10_root,
        args.isis9_label,
        args.isis10_label,
        args.output_csv.name,
    )
    print(f"wrote {len(rows)} binding-header rows to {args.output_csv}")
    print(f"wrote review summary to {args.output_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
