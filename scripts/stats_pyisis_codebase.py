#!/usr/bin/env python3
"""PyISIS repository code statistics helper.

Created: 2026-04-13
Author: Geng Xun

统计 `src/` 和 `tests/` 的代码文件数、代码行数、模块分类、测试覆盖情况，
以及涉及到的 ISIS 类/类型名。

默认口径：
- `src/` 代码文件：`.cpp`, `.h`
- `tests/` 代码文件：`.py`, `.cpp`, `.h`
- ISIS 类（严格口径）：从 `src/` 中提取 `py::class_<Isis::...>`
- ISIS 类型名（宽口径）：再加上 `tests/` 中从 `isis_pybind` 导入或通过模块属性引用的首字母大写名字
- 单测覆盖：仅统计 `tests/unitTest/**/*.py` 中引用到的已绑定类
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

SRC_CODE_SUFFIXES = {".cpp", ".h"}
TEST_CODE_SUFFIXES = {".py", ".cpp", ".h"}
LIKELY_NON_CLASS_TEST_TYPES = {"ByteOrder", "OneBand", "PixelType"}
BINDING_PATTERN = re.compile(r"py::class_<\s*Isis::([A-Za-z_][A-Za-z0-9_]*)")
DEFAULT_MARKDOWN_REPORT = "codebase_stats.md"
MODULE_ORDER = ["base", "control", "bundle", "camera", "projection", "other"]
MODULE_DESCRIPTIONS = {
    "base": "基础通用绑定（不含投影）",
    "control": "控制网/控制点/测量相关绑定",
    "bundle": "Bundle adjustment 相关绑定",
    "camera": "相机、传感器、任务相机、导航相关绑定",
    "projection": "地图投影与投影类型绑定",
    "other": "其他顶层支持绑定与未归类文件",
}


@dataclass(frozen=True)
class LineStats:
    total_lines: int
    nonempty_lines: int


@dataclass(frozen=True)
class DirectoryStats:
    code_file_count: int
    all_file_count: int
    total_lines: int
    nonempty_lines: int


@dataclass(frozen=True)
class ModuleStats:
    file_count: int
    total_lines: int
    nonempty_lines: int
    bound_class_count: int
    bound_classes: list[str]


def iter_files(base: Path) -> list[Path]:
    return sorted(path for path in base.rglob("*") if path.is_file())


def filter_code_files(paths: Iterable[Path], suffixes: set[str]) -> list[Path]:
    return [path for path in paths if path.suffix in suffixes]


def compute_line_stats(paths: Iterable[Path]) -> LineStats:
    total_lines = 0
    nonempty_lines = 0
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        total_lines += len(lines)
        nonempty_lines += sum(1 for line in lines if line.strip())
    return LineStats(total_lines=total_lines, nonempty_lines=nonempty_lines)


def compute_directory_stats(base: Path, suffixes: set[str]) -> DirectoryStats:
    all_files = iter_files(base)
    code_files = filter_code_files(all_files, suffixes)
    line_stats = compute_line_stats(code_files)
    return DirectoryStats(
        code_file_count=len(code_files),
        all_file_count=len(all_files),
        total_lines=line_stats.total_lines,
        nonempty_lines=line_stats.nonempty_lines,
    )


def extract_bound_classes_for_file(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return set(BINDING_PATTERN.findall(text))


def classify_src_module(path: Path, src_root: Path) -> str:
    rel_path = path.relative_to(src_root).as_posix()
    name = path.name

    if rel_path.startswith("base/"):
        if "projection" in name:
            return "projection"
        return "base"

    if rel_path.startswith("control/"):
        if "bundle" in name:
            return "bundle"
        return "control"

    if rel_path.startswith(("mission/", "lro/", "mgs/")):
        return "camera"

    if name.startswith("bind_camera") or name in {"bind_sensor.cpp", "bind_spice_navigation.cpp"}:
        return "camera"

    return "other"


def build_module_stats(
    src_root: Path,
    src_code_files: Iterable[Path],
) -> tuple[dict[str, dict], dict[str, str], dict[str, list[str]]]:
    module_to_files: dict[str, list[Path]] = {name: [] for name in MODULE_ORDER}
    module_to_classes: dict[str, set[str]] = {name: set() for name in MODULE_ORDER}
    class_to_module: dict[str, str] = {}

    for path in src_code_files:
        module_name = classify_src_module(path, src_root)
        module_to_files[module_name].append(path)
        classes = extract_bound_classes_for_file(path)
        module_to_classes[module_name].update(classes)
        for class_name in classes:
            class_to_module.setdefault(class_name, module_name)

    module_stats: dict[str, dict] = {}
    for module_name in MODULE_ORDER:
        files = module_to_files[module_name]
        line_stats = compute_line_stats(files)
        module_stats[module_name] = ModuleStats(
            file_count=len(files),
            total_lines=line_stats.total_lines,
            nonempty_lines=line_stats.nonempty_lines,
            bound_class_count=len(module_to_classes[module_name]),
            bound_classes=sorted(module_to_classes[module_name]),
        ).__dict__

    return module_stats, class_to_module, {name: sorted(classes) for name, classes in module_to_classes.items()}


def split_imported_names(node: ast.ImportFrom) -> list[str]:
    names: list[str] = []
    for alias in node.names:
        if alias.name == "*":
            continue
        top = alias.asname or alias.name.split(".")[0]
        if top and top[:1].isupper():
            names.append(top)
    return names


class TestTypeVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imported_module_aliases: set[str] = set()
        self.class_like_names: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "isis_pybind":
                self.imported_module_aliases.add(alias.asname or "isis_pybind")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "isis_pybind":
            self.class_like_names.update(split_imported_names(node))
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name) and node.value.id in self.imported_module_aliases:
            if node.attr[:1].isupper():
                self.class_like_names.add(node.attr)
        self.generic_visit(node)


def extract_test_referenced_types(test_files: Iterable[Path]) -> tuple[set[str], list[dict[str, str]]]:
    names: set[str] = set()
    parse_failures: list[dict[str, str]] = []
    for path in test_files:
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError as exc:
            parse_failures.append({"file": str(path), "error": str(exc)})
            continue
        visitor = TestTypeVisitor()
        visitor.visit(tree)
        names.update(visitor.class_like_names)
    return names, parse_failures


def extract_test_type_coverage(test_files: Iterable[Path], root: Path) -> tuple[dict[str, set[str]], list[dict[str, str]]]:
    coverage: dict[str, set[str]] = {}
    parse_failures: list[dict[str, str]] = []
    for path in test_files:
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError as exc:
            parse_failures.append({"file": str(path.relative_to(root)), "error": str(exc)})
            continue
        visitor = TestTypeVisitor()
        visitor.visit(tree)
        if visitor.class_like_names:
            coverage[str(path.relative_to(root))] = set(visitor.class_like_names)
    return coverage, parse_failures


def summarize_test_coverage(
    src_classes: set[str],
    class_to_module: dict[str, str],
    unit_test_coverage: dict[str, set[str]],
) -> dict:
    tested_types = set().union(*unit_test_coverage.values()) if unit_test_coverage else set()
    bound_and_tested = src_classes & tested_types
    bound_only = src_classes - bound_and_tested
    tests_only = tested_types - src_classes

    class_to_test_files: dict[str, list[str]] = {}
    for test_file, names in unit_test_coverage.items():
        for name in sorted(names & src_classes):
            class_to_test_files.setdefault(name, []).append(test_file)

    module_view: dict[str, dict] = {}
    for module_name in MODULE_ORDER:
        bound_in_module = sorted(name for name, category in class_to_module.items() if category == module_name)
        tested_in_module = sorted(name for name in bound_and_tested if class_to_module.get(name) == module_name)
        bound_only_in_module = sorted(name for name in bound_only if class_to_module.get(name) == module_name)
        module_view[module_name] = {
            "bound_count": len(bound_in_module),
            "unit_tested_count": len(tested_in_module),
            "bound_only_count": len(bound_only_in_module),
            "bound_classes": bound_in_module,
            "unit_tested_classes": tested_in_module,
            "bound_only_classes": bound_only_in_module,
        }

    return {
        "unit_test_files": len(unit_test_coverage),
        "unit_tested_bound_classes": len(bound_and_tested),
        "bound_only_classes": len(bound_only),
        "tests_only_types": len(tests_only),
        "unit_tested_classes": sorted(bound_and_tested),
        "bound_only_class_names": sorted(bound_only),
        "tests_only_names": sorted(tests_only),
        "tests_only_likely_non_class": sorted(tests_only & LIKELY_NON_CLASS_TEST_TYPES),
        "class_to_test_files": {name: sorted(files) for name, files in sorted(class_to_test_files.items())},
        "by_module": module_view,
    }


def write_markdown_report(content: str, output_path: Path) -> None:
    output_path.write_text(content, encoding="utf-8")


def build_report(root: Path) -> dict:
    src_dir = root / "src"
    tests_dir = root / "tests"
    unit_test_dir = tests_dir / "unitTest"

    src_all_files = iter_files(src_dir)
    tests_all_files = iter_files(tests_dir)
    src_code_files = filter_code_files(src_all_files, SRC_CODE_SUFFIXES)
    tests_code_files = filter_code_files(tests_all_files, TEST_CODE_SUFFIXES)
    unit_test_code_files = filter_code_files(iter_files(unit_test_dir), {".py"}) if unit_test_dir.exists() else []

    src_stats = compute_directory_stats(src_dir, SRC_CODE_SUFFIXES)
    tests_stats = compute_directory_stats(tests_dir, TEST_CODE_SUFFIXES)

    module_stats, class_to_module, module_to_classes = build_module_stats(src_dir, src_code_files)
    src_classes = set(class_to_module)
    test_types, parse_failures = extract_test_referenced_types(tests_code_files)
    unit_test_coverage, unit_parse_failures = extract_test_type_coverage(unit_test_code_files, root)
    union_types = src_classes | test_types
    likely_class_union = union_types - LIKELY_NON_CLASS_TEST_TYPES
    coverage = summarize_test_coverage(src_classes, class_to_module, unit_test_coverage)

    return {
        "root": str(root),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "src": src_stats.__dict__,
        "tests": tests_stats.__dict__,
        "modules": module_stats,
        "classes": {
            "src_bound_unique": len(src_classes),
            "tests_referenced_unique": len(test_types),
            "union_unique": len(union_types),
            "union_likely_classes": len(likely_class_union),
            "src_only": sorted(src_classes - test_types),
            "tests_only": sorted(test_types - src_classes),
            "tests_only_likely_non_class": sorted((test_types - src_classes) & LIKELY_NON_CLASS_TEST_TYPES),
            "intersection": sorted(src_classes & test_types),
            "all_sorted": sorted(union_types),
        },
        "module_class_map": module_to_classes,
        "test_coverage": coverage,
        "parse_failures": parse_failures + unit_parse_failures,
    }


def format_markdown(report: dict, show_class_lists: bool = False, detailed: bool = False) -> str:
    src = report["src"]
    tests = report["tests"]
    classes = report["classes"]
    coverage = report["test_coverage"]
    modules = report["modules"]

    lines = [
        "# pyisis 代码规模统计",
        "",
        f"- 仓库根目录：`{report['root']}`",
        f"- 生成时间：`{report['generated_at']}`",
        "- `src/` 代码文件口径：`.cpp` + `.h`",
        "- `tests/` 代码文件口径：`.py` + `.cpp` + `.h`",
        "- ISIS 类严格口径：`src/` 中 `py::class_<Isis::...>` 去重",
        "- 宽口径：再合并 `tests/` 中从 `isis_pybind` 导入/引用的首字母大写类型名",
        "- 单测覆盖口径：`tests/unitTest/**/*.py` 中引用到的已绑定类",
        "",
        "## 代码规模",
        "",
        "| 目录 | 代码文件数 | 所有文件数 | 总行数 | 非空行数 |",
        "|---|---:|---:|---:|---:|",
        f"| `src/` | {src['code_file_count']} | {src['all_file_count']} | {src['total_lines']} | {src['nonempty_lines']} |",
        f"| `tests/` | {tests['code_file_count']} | {tests['all_file_count']} | {tests['total_lines']} | {tests['nonempty_lines']} |",
        f"| 合计 | {src['code_file_count'] + tests['code_file_count']} | {src['all_file_count'] + tests['all_file_count']} | {src['total_lines'] + tests['total_lines']} | {src['nonempty_lines'] + tests['nonempty_lines']} |",
        "",
        "## 按模块分类统计",
        "",
        "| 模块 | 说明 | 文件数 | 总行数 | 非空行数 | 绑定类数 |",
        "|---|---|---:|---:|---:|---:|",
    ]

    for module_name in MODULE_ORDER:
        module_stats = modules[module_name]
        lines.append(
            f"| `{module_name}` | {MODULE_DESCRIPTIONS[module_name]} | {module_stats['file_count']} | {module_stats['total_lines']} | {module_stats['nonempty_lines']} | {module_stats['bound_class_count']} |"
        )

    lines.extend([
        "",
        "## ISIS 类/类型覆盖",
        "",
        f"- `src/` 中明确绑定的 ISIS 类数：**{classes['src_bound_unique']}**",
        f"- `tests/` 中引用到的类型名数：**{classes['tests_referenced_unique']}**",
        f"- 宽口径并集：**{classes['union_unique']}**",
        f"- 排除明显像枚举/常量的名字后，较像“类”的并集：**{classes['union_likely_classes']}**",
        "",
        "## 测试覆盖视图",
        "",
        f"- 已绑定类：**{classes['src_bound_unique']}**",
        f"- 已写单测的已绑定类：**{coverage['unit_tested_bound_classes']}**",
        f"- 只有绑定、尚未发现单测的类：**{coverage['bound_only_classes']}**",
        f"- 解析到的单测文件数：**{coverage['unit_test_files']}**",
        f"- 单测里额外出现但未在 `src/` 明确绑定的类型名：**{coverage['tests_only_types']}**",
        "",
        "| 模块 | 已绑定类 | 已写单测 | 只有绑定未测 |",
        "|---|---:|---:|---:|",
    ])

    for module_name in MODULE_ORDER:
        module_coverage = coverage["by_module"][module_name]
        lines.append(
            f"| `{module_name}` | {module_coverage['bound_count']} | {module_coverage['unit_tested_count']} | {module_coverage['bound_only_count']} |"
        )

    tests_only = classes["tests_only"]
    if tests_only:
        lines.extend([
            "",
            "### 测试中额外出现、但 `src/` 未直接绑定的类型名",
            "",
            "- " + ", ".join(f"`{name}`" for name in tests_only),
        ])

    if classes["tests_only_likely_non_class"]:
        lines.extend([
            "",
            "### 其中较可能不是类的名字",
            "",
            "- " + ", ".join(f"`{name}`" for name in classes["tests_only_likely_non_class"]),
        ])

    if coverage["tests_only_names"]:
        lines.extend([
            "",
            "### 单测中额外出现、但 `src/` 未直接绑定的类型名",
            "",
            "- " + ", ".join(f"`{name}`" for name in coverage["tests_only_names"]),
        ])

    if coverage["tests_only_likely_non_class"]:
        lines.extend([
            "",
            "### 单测中较可能不是类的名字",
            "",
            "- " + ", ".join(f"`{name}`" for name in coverage["tests_only_likely_non_class"]),
        ])

    if report["parse_failures"]:
        lines.extend([
            "",
            "### 解析失败文件",
            "",
        ])
        for item in report["parse_failures"]:
            lines.append(f"- `{item['file']}`: {item['error']}")

    if detailed:
        lines.extend([
            "",
            "## 详细覆盖清单",
            "",
        ])
        for module_name in MODULE_ORDER:
            module_coverage = coverage["by_module"][module_name]
            lines.extend([
                f"### `{module_name}` 模块",
                "",
                f"- 说明：{MODULE_DESCRIPTIONS[module_name]}",
                f"- 已绑定类数：**{module_coverage['bound_count']}**",
                f"- 已写单测类数：**{module_coverage['unit_tested_count']}**",
                f"- 只有绑定未测类数：**{module_coverage['bound_only_count']}**",
                "",
                "#### 已写单测的类",
                "",
                (", ".join(f"`{name}`" for name in module_coverage["unit_tested_classes"]) if module_coverage["unit_tested_classes"] else "- 无"),
                "",
                "#### 只有绑定未测的类",
                "",
                (", ".join(f"`{name}`" for name in module_coverage["bound_only_classes"]) if module_coverage["bound_only_classes"] else "- 无"),
            ])

        lines.extend([
            "",
            "## 单测文件到类的对应关系",
            "",
        ])
        if coverage["class_to_test_files"]:
            for class_name, test_files in coverage["class_to_test_files"].items():
                lines.append(f"- `{class_name}` ← {', '.join(f'`{path}`' for path in test_files)}")
        else:
            lines.append("- 无")

    if show_class_lists:
        lines.extend([
            "",
            "## 所有识别到的 ISIS 类/类型名",
            "",
            ", ".join(f"`{name}`" for name in classes["all_sorted"]),
        ])

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="统计 pyisis 仓库代码规模和 ISIS 类覆盖情况")
    parser.add_argument("--root", type=Path, default=default_root, help="仓库根目录，默认取脚本上两级目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--show-class-lists", action="store_true", help="在 Markdown 中额外输出完整类/类型名列表")
    parser.add_argument(
        "--write-markdown",
        nargs="?",
        const=DEFAULT_MARKDOWN_REPORT,
        default=None,
        metavar="PATH",
        help=f"将 Markdown 报告写入文件；若不指定路径，默认写入仓库根目录下的 {DEFAULT_MARKDOWN_REPORT}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    report = build_report(root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        markdown = format_markdown(
            report,
            show_class_lists=args.show_class_lists,
            detailed=bool(args.write_markdown),
        )
        if args.write_markdown:
            output_path = Path(args.write_markdown)
            if not output_path.is_absolute():
                output_path = root / output_path
            write_markdown_report(markdown, output_path)
            print(f"Markdown report written to: {output_path}")
        else:
            print(markdown)


if __name__ == "__main__":
    main()
