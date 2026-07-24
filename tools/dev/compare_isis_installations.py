"""Compare installed ISIS C++ headers and core-library exports.

Author: Geng Xun
Created: 2026-07-24

This is a mechanical API/ABI inventory, not a full C++ semantic parser.
Header declaration fingerprints locate review targets; demangled exported
symbols provide an independent check against the installed runtime.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reference" / "compatibility"
HEADER_SUFFIXES = {".h", ".hpp"}
COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
CLASS_RE = re.compile(
    r"\b(?:class|struct)\s+(?:(?:[A-Z][A-Z0-9_]*|[A-Za-z0-9_]+_EXPORT)\s+)?"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*(?=[:{;])"
)
ENUM_RE = re.compile(
    r"\benum\s+(?:class\s+|struct\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(?=[:{])"
)
CALLABLE_RE = re.compile(r"([^;{}]*\([^;{}]*\)[^;{}]*;)", re.MULTILINE)
DEPRECATED_COMMENT_RE = re.compile(
    r"/\*.*?(?:@deprecated|\\deprecated).*?\*/\s*([^;{}]+[;{])",
    re.DOTALL | re.IGNORECASE,
)
DEPRECATED_ATTRIBUTE_RE = re.compile(
    r"([^;\n]*(?:Q_DECL_DEPRECATED|ISIS_DEPRECATED|\[\[\s*deprecated[^\]]*\]\])"
    r"[^;{}]*;)",
    re.IGNORECASE,
)
CONTROL_PREFIXES = ("if", "for", "while", "switch", "catch", "return", "sizeof")
NM_LINE_RE = re.compile(r"^[0-9A-Fa-f]+\s+([A-Za-z])\s+(.+)$")


@dataclass(frozen=True)
class HeaderApi:
    classes: frozenset[str]
    enums: frozenset[str]
    callables: frozenset[str]
    deprecated: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ExportedSymbol:
    symbol_type: str
    symbol: str
    kind: str
    callable_key: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strip_comments(text: str) -> str:
    return COMMENT_RE.sub("", text)


def _normalize_declaration(text: str) -> str:
    text = re.sub(r"^\s*#.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(?:public|protected|private|signals|slots)\s*:\s*", "", text)
    text = re.sub(r"\s*([(),*&=<>:])\s*", r"\1", text)
    return text


def extract_header_api(path: Path) -> HeaderApi:
    """Extract stable declaration fingerprints from one installed header."""

    original_text = _read_text(path)
    deprecated = {
        _normalize_declaration(match)
        for match in (
            DEPRECATED_COMMENT_RE.findall(original_text)
            + DEPRECATED_ATTRIBUTE_RE.findall(original_text)
        )
        if _normalize_declaration(match)
    }
    text = _strip_comments(original_text)
    enums = frozenset(ENUM_RE.findall(text))
    classes = frozenset(set(CLASS_RE.findall(text)) - set(enums))
    callables: set[str] = set()
    for match in CALLABLE_RE.finditer(text):
        declaration = _normalize_declaration(match.group(1))
        prefix = declaration.split("(", 1)[0].strip()
        if not prefix or prefix.startswith(CONTROL_PREFIXES):
            continue
        if "typedef" in prefix or "using " in prefix:
            continue
        callables.add(declaration)
    return HeaderApi(classes, enums, frozenset(callables), frozenset(deprecated))


def header_index(prefix: Path) -> dict[str, Path]:
    header_dir = prefix / "include" / "isis"
    if not header_dir.is_dir():
        raise FileNotFoundError(f"ISIS header directory not found: {header_dir}")
    return {
        path.name: path
        for path in header_dir.iterdir()
        if path.is_file() and path.suffix in HEADER_SUFFIXES
    }


def _joined(values: set[str] | frozenset[str]) -> str:
    return "\n".join(sorted(values))


def compare_headers(
    isis9_prefix: Path,
    isis10_prefix: Path,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    isis9 = header_index(isis9_prefix)
    isis10 = header_index(isis10_prefix)
    counts = {
        "added": 0,
        "removed": 0,
        "identical": 0,
        "changed_declarations": 0,
        "changed_non_declaration": 0,
    }
    rows: list[dict[str, str]] = []

    for name in sorted(set(isis9) | set(isis10)):
        path9 = isis9.get(name)
        path10 = isis10.get(name)
        api9 = extract_header_api(path9) if path9 else HeaderApi(frozenset(), frozenset(), frozenset())
        api10 = extract_header_api(path10) if path10 else HeaderApi(frozenset(), frozenset(), frozenset())
        if path9 is None:
            status = "added"
        elif path10 is None:
            status = "removed"
        elif _sha256(path9) == _sha256(path10):
            status = "identical"
        elif api9 == api10:
            status = "changed_non_declaration"
        else:
            status = "changed_declarations"
        counts[status] += 1
        rows.append(
            {
                "header": name,
                "status": status,
                "isis9_sha256": _sha256(path9) if path9 else "",
                "isis10_sha256": _sha256(path10) if path10 else "",
                "classes_added": _joined(set(api10.classes) - set(api9.classes)),
                "classes_removed": _joined(set(api9.classes) - set(api10.classes)),
                "classes_common": _joined(set(api9.classes) & set(api10.classes)),
                "enums_added": _joined(set(api10.enums) - set(api9.enums)),
                "enums_removed": _joined(set(api9.enums) - set(api10.enums)),
                "enums_common": _joined(set(api9.enums) & set(api10.enums)),
                "callables_added": _joined(set(api10.callables) - set(api9.callables)),
                "callables_removed": _joined(set(api9.callables) - set(api10.callables)),
                "deprecated_added": _joined(set(api10.deprecated) - set(api9.deprecated)),
                "deprecated_removed": _joined(set(api9.deprecated) - set(api10.deprecated)),
            }
        )
    return rows, counts


def _callable_key(symbol: str) -> str:
    if "(" not in symbol:
        return ""
    return symbol.split("(", 1)[0].removeprefix("non-virtual thunk to ").removeprefix(
        "virtual thunk to "
    )


def _symbol_kind(symbol: str) -> str:
    if symbol.startswith(("vtable for ", "typeinfo for ", "typeinfo name for ", "VTT for ")):
        return "type_metadata"
    if symbol.startswith(("non-virtual thunk to ", "virtual thunk to ")):
        return "thunk"
    if "(" not in symbol:
        return "data"
    key = _callable_key(symbol)
    return "method" if key.count("::") >= 2 else "function"


def parse_nm_output(text: str) -> dict[str, ExportedSymbol]:
    symbols: dict[str, ExportedSymbol] = {}
    for line in text.splitlines():
        match = NM_LINE_RE.match(line.strip())
        if not match:
            continue
        symbol_type, symbol = match.groups()
        if not symbol.startswith(
            (
                "Isis::",
                "vtable for Isis::",
                "typeinfo for Isis::",
                "typeinfo name for Isis::",
                "VTT for Isis::",
                "non-virtual thunk to Isis::",
                "virtual thunk to Isis::",
            )
        ):
            continue
        symbol = re.sub(r"\s+\[clone [^\]]+\]$", "", symbol)
        symbols[symbol] = ExportedSymbol(
            symbol_type=symbol_type,
            symbol=symbol,
            kind=_symbol_kind(symbol),
            callable_key=_callable_key(symbol),
        )
    return symbols


def exported_symbols(library: Path, nm: str = "nm") -> dict[str, ExportedSymbol]:
    result = subprocess.run(
        [nm, "-D", "--defined-only", "--demangle", str(library)],
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_nm_output(result.stdout)


def resolve_libisis(prefix: Path) -> Path:
    link = prefix / "lib" / "libisis.so"
    if not link.exists():
        raise FileNotFoundError(f"libisis.so not found: {link}")
    return link.resolve()


def compare_exports(
    isis9_library: Path,
    isis10_library: Path,
    nm: str = "nm",
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, int]]:
    symbols9 = exported_symbols(isis9_library, nm)
    symbols10 = exported_symbols(isis10_library, nm)
    rows: list[dict[str, str]] = []
    counts: dict[str, int] = {
        "isis9_total": len(symbols9),
        "isis10_total": len(symbols10),
        "added": 0,
        "removed": 0,
        "unchanged": 0,
    }
    for symbol in sorted(set(symbols9) | set(symbols10)):
        item9 = symbols9.get(symbol)
        item10 = symbols10.get(symbol)
        if item9 is None:
            status = "added"
            item = item10
        elif item10 is None:
            status = "removed"
            item = item9
        else:
            status = "unchanged"
            item = item10
        assert item is not None
        counts[status] += 1
        rows.append(
            {
                "status": status,
                "kind": item.kind,
                "callable_key": item.callable_key,
                "symbol": item.symbol,
                "isis9_symbol_type": item9.symbol_type if item9 else "",
                "isis10_symbol_type": item10.symbol_type if item10 else "",
            }
        )

    by_key9: dict[str, set[str]] = {}
    by_key10: dict[str, set[str]] = {}
    for item in symbols9.values():
        if item.callable_key:
            by_key9.setdefault(item.callable_key, set()).add(item.symbol)
    for item in symbols10.values():
        if item.callable_key:
            by_key10.setdefault(item.callable_key, set()).add(item.symbol)
    callable_changes = []
    for key in sorted(set(by_key9) & set(by_key10)):
        removed = by_key9[key] - by_key10[key]
        added = by_key10[key] - by_key9[key]
        if removed or added:
            callable_changes.append(
                {
                    "callable_key": key,
                    "kind": "method" if key.count("::") >= 2 else "function",
                    "owner": key.split("::")[1] if key.count("::") >= 2 else "",
                    "removed_signatures": _joined(removed),
                    "added_signatures": _joined(added),
                }
            )
    counts["changed_callable_groups"] = len(callable_changes)
    return rows, callable_changes, counts


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"cannot determine CSV fields from empty rows: {path}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _markdown_items(values: list[str], empty: str = "无") -> list[str]:
    return [f"- `{value}`" for value in values] or [f"- {empty}"]


def write_report(
    path: Path,
    header_rows: list[dict[str, str]],
    header_counts: dict[str, int],
    symbol_rows: list[dict[str, str]],
    callable_changes: list[dict[str, str]],
    symbol_counts: dict[str, int],
    isis9_label: str,
    isis10_label: str,
) -> None:
    added_headers = [row["header"] for row in header_rows if row["status"] == "added"]
    removed_headers = [row["header"] for row in header_rows if row["status"] == "removed"]
    def primary_class(row: dict[str, str], field: str) -> str:
        stem = Path(row["header"]).stem
        return stem if stem in row[field].splitlines() else ""

    added_classes = sorted(
        value
        for row in header_rows
        if row["status"] == "added"
        if (value := primary_class(row, "classes_added"))
    )
    removed_classes = sorted(
        value
        for row in header_rows
        if row["status"] == "removed"
        if (value := primary_class(row, "classes_removed"))
    )
    modified_header_classes = sorted(
        value
        for row in header_rows
        if row["status"] == "changed_declarations"
        if (value := primary_class(row, "classes_common"))
    )
    modified_export_classes = sorted(
        {row["owner"] for row in callable_changes if row["kind"] == "method"}
    )
    modified_free_functions = sorted(
        row["callable_key"] for row in callable_changes if row["kind"] == "function"
    )
    deprecated_added_set = {
        item
        for row in header_rows
        for item in row["deprecated_added"].splitlines()
        if item
    }
    deprecated_removed_set = {
        item
        for row in header_rows
        for item in row["deprecated_removed"].splitlines()
        if item
    }
    renamed_deprecated = deprecated_added_set & deprecated_removed_set
    deprecated_added = sorted(deprecated_added_set - renamed_deprecated)
    deprecated_removed = sorted(deprecated_removed_set - renamed_deprecated)
    added_symbols_by_kind: dict[str, int] = {}
    removed_symbols_by_kind: dict[str, int] = {}
    for row in symbol_rows:
        target = (
            added_symbols_by_kind
            if row["status"] == "added"
            else removed_symbols_by_kind
            if row["status"] == "removed"
            else None
        )
        if target is not None:
            target[row["kind"]] = target.get(row["kind"], 0) + 1

    lines = [
        "# ISIS 9.0.0 → ISIS 10.0.0 已安装 C++ API/ABI 系统对比",
        "",
        "> 自动生成。头文件声明提取是机械指纹，不替代完整 C++ AST 审查；"
        "`libisis` 导出符号是实际 Linux 运行库证据。",
        "",
        f"- ISIS 9: `{isis9_label}`",
        f"- ISIS 10: `{isis10_label}`",
        "",
        "## 结论摘要",
        "",
        "| 层次 | ISIS 9 → ISIS 10 结果 |",
        "| --- | --- |",
        f"| 头文件 | 新增 {header_counts['added']}，删除 {header_counts['removed']}，"
        f"字节完全一致 {header_counts['identical']} |",
        f"| 同名头文件 | 声明指纹变化 {header_counts['changed_declarations']}，"
        f"只有注释/格式/内联实现等非声明变化 {header_counts['changed_non_declaration']} |",
        f"| `libisis` 导出 | ISIS 9 为 {symbol_counts['isis9_total']}，"
        f"ISIS 10 为 {symbol_counts['isis10_total']}；新增 {symbol_counts['added']}，"
        f"移除 {symbol_counts['removed']}，不变 {symbol_counts['unchanged']} |",
        f"| 同名 callable 组 | {symbol_counts['changed_callable_groups']} 组的"
        "重载/参数/const 等导出签名集合发生变化 |",
        "",
        "此前的“178 个文件变化”是旧 ASP prefix 的字节级结果。这里已经按当前"
        " USGS 正式包重新计算，并将字节变化、声明变化与二进制符号变化分开。",
        "",
        "## 新增头文件",
        "",
        *_markdown_items(added_headers),
        "",
        "## 删除或重命名头文件",
        "",
        *_markdown_items(removed_headers),
        "",
        "`Endian.h` 在 ISIS 10 中对应 `IEndian.h`，需按重命名而非功能整体删除处理。",
        "",
        "## 机械识别的新增类",
        "",
        *_markdown_items(added_classes),
        "",
        "## 机械识别的删除类",
        "",
        *_markdown_items(removed_classes),
        "",
        "## 同名但声明或导出发生变化的类",
        "",
        f"- 头文件主类声明变化：{len(modified_header_classes)} 个。完整类名如下：",
        *_markdown_items(modified_header_classes),
        "",
        f"- `libisis` 方法签名集合变化涉及：{len(modified_export_classes)} 个类。"
        "完整映射见 callable CSV。",
        "",
        "## 同名自由函数签名集合变化",
        "",
        *_markdown_items(modified_free_functions),
        "",
        "## 核心库导出变化分类",
        "",
        "| 类型 | 新增导出 | 移除导出 |",
        "| --- | ---: | ---: |",
    ]
    for kind in sorted(set(added_symbols_by_kind) | set(removed_symbols_by_kind)):
        lines.append(
            f"| {kind} | {added_symbols_by_kind.get(kind, 0)} | "
            f"{removed_symbols_by_kind.get(kind, 0)} |"
        )
    lines.extend(
        [
            "",
            "## Deprecated 声明线索",
            "",
            f"- ISIS 10 新增 deprecated 声明指纹：{len(deprecated_added)} 条。",
            f"- ISIS 9 中存在、ISIS 10 不再出现的 deprecated 声明指纹："
            f"{len(deprecated_removed)} 条。",
            f"- 在重命名头文件间保持一致的 deprecated 声明指纹："
            f"{len(renamed_deprecated)} 条。",
            "- 完整声明见 header diff CSV 的 `deprecated_added` 和 "
            "`deprecated_removed` 字段；消失可能表示删除、重命名或文档迁移，"
            "不能单凭该字段判断。",
            "",
            "## 如何阅读“修改”",
            "",
            "- 同一 callable 名称的签名集合有增有减，表示参数、const、重载或 ABI "
            "签名发生变化，完整记录见 `isis9-isis10-core-callable-changes.csv`。",
            "- 头文件声明变化但导出不变，可能是 inline/template、默认参数、枚举、"
            "访问限定或仅编译期 API 变化，见 `isis9-isis10-installed-header-diff.csv`。",
            "- 导出变化但头文件机械指纹未捕获，可能来自私有实现、模板实例、thunk、"
            "类型信息或解析器边界，必须人工复核。",
            "",
            "## 完整明细",
            "",
            "- `isis9-isis10-installed-header-diff.csv`：全部头文件及类/枚举/callable 声明差异。",
            "- `isis9-isis10-core-symbol-diff.csv`：全部 `libisis` demangled 导出集合。",
            "- `isis9-isis10-core-callable-changes.csv`：同名 callable 的签名集合变化。",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare installed ISIS 9 and ISIS 10 headers and libisis exports."
    )
    parser.add_argument("--isis9-prefix", type=Path, required=True)
    parser.add_argument("--isis10-prefix", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--isis9-label", default="USGS ISIS 9.0.0")
    parser.add_argument("--isis10-label", default="USGS ISIS 10.0.0")
    parser.add_argument("--nm", default="nm")
    args = parser.parse_args()

    header_rows, header_counts = compare_headers(
        args.isis9_prefix, args.isis10_prefix
    )
    symbol_rows, callable_changes, symbol_counts = compare_exports(
        resolve_libisis(args.isis9_prefix),
        resolve_libisis(args.isis10_prefix),
        args.nm,
    )
    output_dir = args.output_dir
    write_csv(output_dir / "isis9-isis10-installed-header-diff.csv", header_rows)
    write_csv(output_dir / "isis9-isis10-core-symbol-diff.csv", symbol_rows)
    write_csv(
        output_dir / "isis9-isis10-core-callable-changes.csv", callable_changes
    )
    write_report(
        output_dir / "isis9-isis10-installed-api-comparison.md",
        header_rows,
        header_counts,
        symbol_rows,
        callable_changes,
        symbol_counts,
        args.isis9_label,
        args.isis10_label,
    )
    print(f"headers: {header_counts}")
    print(f"symbols: {symbol_counts}")
    print(f"report: {output_dir / 'isis9-isis10-installed-api-comparison.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
