from __future__ import annotations

from collections import Counter
import csv
from functools import lru_cache
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
TODO_CSV = REPO_ROOT / "isis_pybind_standalone" / "todo_pybind11.csv"
INVENTORY_JSON = REPO_ROOT / "_tmp_pybind_inventory.json"
OUTPUT_DIR = REPO_ROOT / "isis_pybind_standalone" / "class_bind_methods_details"
SEARCH_ROOTS = [
    REPO_ROOT / "isis" / "src",
    REPO_ROOT / "SensorUtilities" / "include",
    REPO_ROOT / "SensorUtilities" / "src",
]


@dataclass
class TodoEntry:
    category: str
    class_name: str
    current_status: str
    note: str


@dataclass
class ApiItem:
    group: str
    cpp_name: str
    python_name: str
    converted: str
    notes: str


@dataclass
class BindingInfo:
    python_class_name: str | None
    methods: set[str]
    has_init: bool
    binding_files: list[str]


@dataclass
class SummaryRow:
    priority_rank: int
    suggested_priority: str
    priority_reason: str
    class_name: str
    module_category: str
    generated_csv: str
    todo_status: str
    class_symbol_status: str
    y_count: int
    n_count: int
    partial_count: int
    open_items: int
    total_items: int
    completion_percent: float
    source: str
    binding: str
    class_note: str


def camel_to_snake(name: str) -> str:
    first_pass = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    second_pass = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first_pass)
    return second_pass.replace("__", "_").lower()


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "misc"


def normalize_name(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*", "", text)
    return text


def load_todo_entries() -> list[TodoEntry]:
    with TODO_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [
            TodoEntry(
                category=row.get("模块类别", "").strip(),
                class_name=row.get("类名", "").strip(),
                current_status=row.get("当前状态", "").strip(),
                note=row.get("备注", "").strip(),
            )
            for row in reader
            if row.get("类名", "").strip()
        ]


def dedupe_todo_entries(entries: list[TodoEntry]) -> list[TodoEntry]:
    def entry_score(entry: TodoEntry, index: int) -> tuple[int, int, int, int]:
        converted_rank = 2 if entry.current_status == "已转换" else 1 if entry.current_status else 0
        note_rank = 1 if entry.note else 0
        return (converted_rank, note_rank, len(entry.note), index)

    ordered_keys: list[tuple[str, str]] = []
    seen_keys: set[tuple[str, str]] = set()
    best_entries: dict[tuple[str, str], TodoEntry] = {}
    best_scores: dict[tuple[str, str], tuple[int, int, int, int]] = {}

    for index, entry in enumerate(entries):
        key = (entry.category, entry.class_name)
        if key not in seen_keys:
            ordered_keys.append(key)
            seen_keys.add(key)

        candidate_score = entry_score(entry, index)
        if key not in best_scores or candidate_score >= best_scores[key]:
            best_scores[key] = candidate_score
            best_entries[key] = entry

    return [best_entries[key] for key in ordered_keys]


def load_inventory() -> tuple[dict[str, list[dict]], dict[str, list[str]]]:
    if not INVENTORY_JSON.exists():
        return {}, {}

    data = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
    records_by_class: dict[str, list[dict]] = {}
    for record in data.get("records", []):
        records_by_class.setdefault(record.get("class", ""), []).append(record)
    converted_map = {
        key: value for key, value in data.get("converted", {}).items() if isinstance(value, list)
    }
    return records_by_class, converted_map


@lru_cache(maxsize=None)
def discover_binding_paths(class_name: str) -> tuple[str, ...]:
    src_root = REPO_ROOT / "isis_pybind_standalone" / "src"
    if not src_root.exists():
        return ()

    pattern = re.compile(rf"py::class_<[\s\S]*?\bIsis::{re.escape(class_name)}\b", re.M)
    matches: list[str] = []

    for path in src_root.rglob("*.cpp"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            matches.append(str(path.relative_to(REPO_ROOT)))

    return tuple(matches)


def find_existing_detail_csv(entry: TodoEntry) -> Path | None:
    suffix = f"_{camel_to_snake(entry.class_name)}_methods.csv"
    candidates = sorted(OUTPUT_DIR.glob(f"*{suffix}"))

    for candidate in candidates:
        with candidate.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))

        if len(rows) < 2:
            continue

        metadata = rows[1]
        candidate_class = metadata[0].strip() if len(metadata) > 0 else ""
        candidate_category = metadata[1].strip() if len(metadata) > 1 else ""
        if candidate_class == entry.class_name and candidate_category == entry.category:
            return candidate

    return None


def locate_header(class_name: str, inventory_records: list[dict]) -> tuple[str | None, str | None]:
    for record in inventory_records:
        header = record.get("header")
        if header:
            header_path = REPO_ROOT / header
            if header_path.exists():
                return str(header_path.relative_to(REPO_ROOT)), record.get("scope")

    candidates: list[Path] = []
    for root in SEARCH_ROOTS:
        if root.exists():
            candidates.extend(root.rglob(f"{class_name}.h"))
    if candidates:
        candidates.sort(key=lambda path: (len(path.parts), str(path)))
        rel = str(candidates[0].relative_to(REPO_ROOT))
        scope = candidates[0].parts[len(REPO_ROOT.parts)] if len(candidates[0].parts) > len(REPO_ROOT.parts) else "misc"
        return rel, scope
    return None, None


def extract_class_block(header_text: str, class_name: str) -> str | None:
    patterns = [
        rf"\bclass\s+{re.escape(class_name)}\b[^;{{]*{{",
        rf"\bstruct\s+{re.escape(class_name)}\b[^;{{]*{{",
    ]
    for pattern in patterns:
        match = re.search(pattern, header_text)
        if not match:
            continue
        start = header_text.find("{", match.start())
        if start == -1:
            continue
        depth = 0
        for idx in range(start, len(header_text)):
            char = header_text[idx]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return header_text[start + 1:idx]
    return None


def normalize_signature(statement: str) -> str:
    statement = re.sub(r"\s+", " ", statement).strip()
    statement = statement.rstrip(";").strip()
    return statement


def find_statement_end(text: str, start_index: int) -> int:
    paren_depth = 0
    brace_depth = 0
    bracket_depth = 0
    in_string = False
    string_delim = ""
    escape = False

    for idx in range(start_index, len(text)):
        char = text[idx]

        if in_string:
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == string_delim:
                in_string = False
            continue

        if char in {'"', "'"}:
            in_string = True
            string_delim = char
            continue
        if char == "(":
            paren_depth += 1
            continue
        if char == ")":
            paren_depth = max(paren_depth - 1, 0)
            continue
        if char == "{":
            brace_depth += 1
            continue
        if char == "}":
            brace_depth = max(brace_depth - 1, 0)
            continue
        if char == "[":
            bracket_depth += 1
            continue
        if char == "]":
            bracket_depth = max(bracket_depth - 1, 0)
            continue
        if char == ";" and paren_depth == 0 and brace_depth == 0 and bracket_depth == 0:
            return idx

    return -1


def classify_method(name: str, signature: str, is_static: bool) -> str:
    lower = name.lower()
    if is_static or lower in {"create", "clone", "factory"} or " factory" in signature.lower():
        return "Static/Factory"
    if lower.startswith(("read", "write", "load", "save", "import", "export", "open", "close")):
        return "Read/Write IO"
    if lower.startswith(("is", "has", "can", "count", "size", "valid", "exists")):
        return "Query"
    if lower.startswith(("set", "add", "clear", "delete", "remove", "put", "attach", "detach")):
        return "Mutation/Configuration"
    return "Public API"


def extract_public_api(header_path: Path, class_name: str) -> tuple[list[str], list[str]]:
    text = strip_comments(header_path.read_text(encoding="utf-8", errors="ignore"))
    block = extract_class_block(text, class_name)
    if not block:
        return [], []

    block = re.sub(
        r"}\s+(?=(?:virtual|static|inline|explicit|friend|const|[A-Za-z_][A-Za-z0-9_:<>*&\s]*\())",
        "}\n",
        block,
    )

    methods: list[str] = []
    enums: list[str] = []
    access = "private"
    statement_parts: list[str] = []

    def flush_statement() -> None:
        nonlocal statement_parts, methods, enums, access
        if access != "public":
            statement_parts = []
            return
        statement = normalize_signature(" ".join(statement_parts))
        statement_parts = []
        if not statement:
            return
        if statement.startswith(("typedef ", "using ", "friend ", "Q_OBJECT", "Q_DECLARE")):
            return
        if statement.startswith("enum ") or statement.startswith("enum class "):
            enum_match = re.search(r"enum(?: class)?\s+(\w+)", statement)
            if enum_match:
                enum_name = enum_match.group(1)
                values_match = re.search(r"\{(.*)\}", statement)
                values = ""
                if values_match:
                    raw_values = values_match.group(1)
                    tokens = []
                    for token in raw_values.split(","):
                        cleaned = token.strip()
                        if not cleaned:
                            continue
                        cleaned = cleaned.split("=")[0].strip()
                        if cleaned:
                            tokens.append(cleaned)
                    if tokens:
                        values = ", ".join(tokens[:10])
                label = f"{enum_name} enum"
                if values:
                    label += f" ({values})"
                enums.append(label)
            return
        if "(" not in statement or ")" not in statement:
            return
        if "operator" in statement:
            return
        name_match = re.search(r"(~?\w+)\s*\([^()]*\)\s*(?:const|override|final|noexcept|=\s*0|=\s*default|=\s*delete|\{|$)", statement)
        if not name_match:
            return
        name = name_match.group(1)
        if name.startswith("~"):
            return
        if name == class_name:
            methods.append(f"{class_name}()")
            return
        methods.append(statement)

    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"public\s*:", line):
            flush_statement()
            access = "public"
            continue
        if re.match(r"protected\s*:", line):
            flush_statement()
            access = "protected"
            continue
        if re.match(r"private\s*:", line):
            flush_statement()
            access = "private"
            continue
        if re.match(r"signals\s*:", line) or re.match(r"public slots\s*:", line) or re.match(r"private slots\s*:", line):
            flush_statement()
            access = "private"
            continue
        statement_parts.append(line)
        if line.endswith(";") or line.endswith("}"):
            flush_statement()

    flush_statement()
    dedup_enums = list(dict.fromkeys(enums))
    dedup_methods = list(dict.fromkeys(methods))
    return dedup_enums, dedup_methods


def find_matching_method_name(cpp_name: str, bound_names: Iterable[str]) -> str | None:
    method_match = re.search(r"(~?\w+)\s*\(", cpp_name)
    method_name = method_match.group(1) if method_match else cpp_name
    snake = camel_to_snake(method_name)
    candidates = {method_name, snake}
    normalized_target = normalize_name(method_name)

    exact_matches = [name for name in bound_names if name in candidates]
    if exact_matches:
        return sorted(exact_matches, key=len)[0]

    normalized_matches = [name for name in bound_names if normalize_name(name) == normalized_target]
    if len(normalized_matches) == 1:
        return normalized_matches[0]

    return None


def parse_bindings(binding_paths: list[str], class_name: str) -> BindingInfo:
    methods: set[str] = set()
    has_init = False
    python_class_name: str | None = None
    existing_files: list[str] = []

    class_decl_pattern = re.compile(
        r"py::class_<(?P<inner>[\s\S]*?)>\s*(?:(?P<var>\w+)\s*)?\(\s*m\s*,\s*\"(?P<pyname>[^\"]+)\"\s*\)",
        re.M,
    )

    for rel_path in binding_paths:
        path = REPO_ROOT / rel_path
        if not path.exists():
            continue
        existing_files.append(rel_path)
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in class_decl_pattern.finditer(text):
            inner = match.group("inner")
            cpp_match = re.search(rf"Isis::{re.escape(class_name)}\b", inner)
            if not cpp_match:
                continue
            python_class_name = match.group("pyname")
            var_name = match.group("var")
            stmt_end = find_statement_end(text, match.end())
            if stmt_end != -1:
                statement = text[match.start():stmt_end + 1]
                methods.update(re.findall(r'\.def\(\s*\"([^\"]+)\"', statement))
                has_init = has_init or bool(re.search(r"\.def\(\s*py::init", statement))
            if var_name:
                methods.update(re.findall(rf"\b{re.escape(var_name)}\s*\.def\(\s*\"([^\"]+)\"", text))
                has_init = has_init or bool(re.search(rf"\b{re.escape(var_name)}\s*\.def\(\s*py::init", text))

    return BindingInfo(
        python_class_name=python_class_name,
        methods=methods,
        has_init=has_init,
        binding_files=existing_files,
    )


def build_api_rows(
    entry: TodoEntry,
    header_rel: str | None,
    binding_info: BindingInfo,
) -> list[ApiItem]:
    rows: list[ApiItem] = []
    python_class_name = binding_info.python_class_name or entry.class_name
    class_symbol_status = "Y" if binding_info.binding_files or entry.current_status == "已转换" else "N"
    symbol_note = "Python class symbol is exported" if class_symbol_status == "Y" else "Python class symbol not found in current binding files"
    if class_symbol_status == "Y" and not binding_info.has_init:
        symbol_note = "Python class symbol is exported; constructor exposure may be limited"
    if entry.note:
        symbol_note = f"{symbol_note}; {entry.note}"

    rows.append(
        ApiItem(
            group="Class Symbol",
            cpp_name=entry.class_name,
            python_name=f"isis_pybind.{python_class_name}",
            converted=class_symbol_status,
            notes=symbol_note,
        )
    )

    if not header_rel:
        rows.append(
            ApiItem(
                group="Public API",
                cpp_name="Header not located",
                python_name=f"isis_pybind.{python_class_name}",
                converted="N",
                notes="Unable to locate the header automatically",
            )
        )
        return rows

    enums, methods = extract_public_api(REPO_ROOT / header_rel, entry.class_name)

    for enum_label in enums:
        rows.append(
            ApiItem(
                group="Construction/Enum",
                cpp_name=enum_label,
                python_name=f"isis_pybind.{python_class_name}.{enum_label.split()[0]}",
                converted="N",
                notes=entry.note or "Enum exposure not detected in current binding files",
            )
        )

    if not methods:
        if class_symbol_status == "Y":
            rows.append(
                ApiItem(
                    group="Public API",
                    cpp_name="No public methods parsed",
                    python_name=f"isis_pybind.{python_class_name}",
                    converted="Partial",
                    notes="Class is bound, but methods may be inherited, helper-bound, or parsing needs review",
                )
            )
        return rows

    for method_sig in methods:
        method_match = re.search(r"(~?\w+)\s*\(", method_sig)
        method_name = method_match.group(1) if method_match else method_sig
        if method_name == entry.class_name:
            converted = "Y" if binding_info.has_init else "N"
            note = "Constructor is explicitly bound" if converted == "Y" else "Constructor binding not detected in current binding files"
            if converted == "N" and entry.note:
                note = entry.note
            rows.append(
                ApiItem(
                    group="Construction/Enum",
                    cpp_name=method_sig,
                    python_name=f"isis_pybind.{python_class_name}()",
                    converted=converted,
                    notes=note,
                )
            )
            continue

        actual_bound_name = find_matching_method_name(method_sig, binding_info.methods)
        is_static = " static " in f" {method_sig} " or method_sig.startswith("static ")
        group = classify_method(method_name, method_sig, is_static)
        proposed_python = f"isis_pybind.{python_class_name}.{camel_to_snake(method_name)}"
        if actual_bound_name:
            python_name = f"isis_pybind.{python_class_name}.{actual_bound_name}"
            note = "Current Python name"
            converted = "Y"
        else:
            python_name = proposed_python
            converted = "N"
            note = entry.note or "Method not found in current binding files"
        rows.append(
            ApiItem(
                group=group,
                cpp_name=method_sig,
                python_name=python_name,
                converted=converted,
                notes=note,
            )
        )

    return rows


def write_csv(
    entry: TodoEntry,
    output_path: Path,
    header_rel: str | None,
    binding_info: BindingInfo,
    rows: list[ApiItem],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    binding_value = "; ".join(binding_info.binding_files) if binding_info.binding_files else "N/A"
    header_value = header_rel or "N/A"
    class_note = entry.note or ""

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Class",
            "Module Category",
            "Source",
            "Binding",
            "Status Legend",
            "Python Naming Note",
            "Class Note",
        ])
        writer.writerow([
            entry.class_name,
            entry.category,
            header_value,
            binding_value,
            "Y = converted; N = not converted; Partial = partially converted",
            "Converted entries use the current Python name; unconverted entries use the proposed Python name",
            class_note,
        ])
        writer.writerow([])
        writer.writerow([
            "Group",
            "C++ Method/Content",
            "Python Class/Function Name",
            "Converted",
            "Notes",
        ])
        for row in rows:
            writer.writerow([row.group, row.cpp_name, row.python_name, row.converted, row.notes])


def deduce_scope(entry: TodoEntry, inventory_records: list[dict], fallback_scope: str | None) -> str:
    for record in inventory_records:
        scope = record.get("scope")
        if scope:
            return slugify(scope)
    if fallback_scope:
        return slugify(fallback_scope)
    return slugify(entry.category)


def summarize_rows(
    entry: TodoEntry,
    output_path: Path,
    header_rel: str | None,
    binding_info: BindingInfo,
    rows: list[ApiItem],
) -> SummaryRow:
    counts = {"Y": 0, "N": 0, "Partial": 0}
    for row in rows:
        counts[row.converted] = counts.get(row.converted, 0) + 1

    total_items = sum(counts.values())
    open_items = counts["N"] + counts["Partial"]
    completion_percent = (counts["Y"] / total_items * 100.0) if total_items else 0.0
    class_symbol_status = next((row.converted for row in rows if row.group == "Class Symbol"), "N")
    binding_value = "; ".join(binding_info.binding_files) if binding_info.binding_files else "N/A"
    source_value = header_rel or "N/A"

    priority_rank, suggested_priority, priority_reason = compute_priority(
        class_symbol_status,
        open_items,
        total_items,
    )

    return SummaryRow(
        priority_rank=priority_rank,
        suggested_priority=suggested_priority,
        priority_reason=priority_reason,
        class_name=entry.class_name,
        module_category=entry.category,
        generated_csv=output_path.name,
        todo_status=entry.current_status,
        class_symbol_status=class_symbol_status,
        y_count=counts["Y"],
        n_count=counts["N"],
        partial_count=counts["Partial"],
        open_items=open_items,
        total_items=total_items,
        completion_percent=completion_percent,
        source=source_value,
        binding=binding_value,
        class_note=entry.note,
    )


def compute_priority(class_symbol_status: str, open_items: int, total_items: int) -> tuple[int, str, str]:
    if class_symbol_status == "Y":
        if open_items <= 10:
            return (1, "High", "Already exported in Python with a small remaining API gap")
        if open_items <= 30:
            return (2, "Medium", "Already exported in Python, but still has a moderate API gap")
        return (3, "Low", "Already exported, but the remaining API surface is large")

    if total_items <= 12:
        return (1, "High", "Not exported yet, but the class looks small enough for a quick win")
    if total_items <= 30:
        return (2, "Medium", "Not exported yet and has a moderate public API size")
    return (3, "Low", "Not exported yet and likely needs a larger binding effort")


def summarize_existing_detail_csv(
    entry: TodoEntry,
    detail_path: Path,
    header_rel: str | None,
    allow_binding_discovery: bool,
) -> SummaryRow:
    with detail_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = list(csv.reader(f))

    metadata = reader[1] if len(reader) > 1 else []
    source_value = metadata[2].strip() if len(metadata) > 2 and metadata[2].strip() else (header_rel or "N/A")
    binding_value = metadata[3].strip() if len(metadata) > 3 and metadata[3].strip() else "N/A"
    class_note = entry.note or (metadata[6].strip() if len(metadata) > 6 else "")

    if binding_value == "N/A" and allow_binding_discovery:
        discovered_paths = discover_binding_paths(entry.class_name)
        if discovered_paths:
            binding_value = "; ".join(discovered_paths)

    counts = {"Y": 0, "N": 0, "Partial": 0}
    class_symbol_status = "Y" if entry.current_status == "已转换" else "N"
    in_method_table = False

    for row in reader:
        if not row:
            continue
        if row[:5] == ["Group", "C++ Method/Content", "Python Class/Function Name", "Converted", "Notes"]:
            in_method_table = True
            continue
        if not in_method_table or len(row) < 4:
            continue

        converted = row[3].strip()
        if converted not in counts:
            continue
        counts[converted] += 1
        if row[0].strip() == "Class Symbol":
            class_symbol_status = converted

    total_items = sum(counts.values())
    open_items = counts["N"] + counts["Partial"]
    completion_percent = (counts["Y"] / total_items * 100.0) if total_items else 0.0
    priority_rank, suggested_priority, priority_reason = compute_priority(
        class_symbol_status,
        open_items,
        total_items,
    )

    return SummaryRow(
        priority_rank=priority_rank,
        suggested_priority=suggested_priority,
        priority_reason=priority_reason,
        class_name=entry.class_name,
        module_category=entry.category,
        generated_csv=detail_path.name,
        todo_status=entry.current_status,
        class_symbol_status=class_symbol_status,
        y_count=counts["Y"],
        n_count=counts["N"],
        partial_count=counts["Partial"],
        open_items=open_items,
        total_items=total_items,
        completion_percent=completion_percent,
        source=source_value,
        binding=binding_value,
        class_note=class_note,
    )


def write_summary_csv(summary_rows: list[SummaryRow]) -> Path:
    summary_path = OUTPUT_DIR / "methods_inventory_summary.csv"
    sorted_rows = sorted(
        summary_rows,
        key=lambda row: (
            row.priority_rank,
            row.open_items,
            -row.completion_percent,
            row.module_category.lower(),
            row.class_name.lower(),
        ),
    )

    with summary_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Priority Rank",
            "Suggested Priority",
            "Priority Reason",
            "Class",
            "Module Category",
            "Generated CSV",
            "Todo Status",
            "Class Symbol Status",
            "Y Count",
            "N Count",
            "Partial Count",
            "Open Items",
            "Total Items",
            "Completion Percent",
            "Source",
            "Binding",
            "Class Note",
        ])
        for row in sorted_rows:
            writer.writerow([
                row.priority_rank,
                row.suggested_priority,
                row.priority_reason,
                row.class_name,
                row.module_category,
                row.generated_csv,
                row.todo_status,
                row.class_symbol_status,
                row.y_count,
                row.n_count,
                row.partial_count,
                row.open_items,
                row.total_items,
                f"{row.completion_percent:.2f}",
                row.source,
                row.binding,
                row.class_note,
            ])

    return summary_path


def main() -> None:
    todo_entries = dedupe_todo_entries(load_todo_entries())
    records_by_class, converted_map = load_inventory()
    class_name_counts = Counter(entry.class_name for entry in todo_entries)

    generated = 0
    summary_rows: list[SummaryRow] = []

    if not INVENTORY_JSON.exists():
        for entry in todo_entries:
            inventory_records = records_by_class.get(entry.class_name, [])
            header_rel, _ = locate_header(entry.class_name, inventory_records)
            detail_path = find_existing_detail_csv(entry)

            if detail_path is not None:
                summary_rows.append(
                    summarize_existing_detail_csv(
                        entry,
                        detail_path,
                        header_rel,
                        allow_binding_discovery=class_name_counts[entry.class_name] == 1,
                    )
                )
                generated += 1
                continue

            binding_paths = list(dict.fromkeys(converted_map.get(entry.class_name, [])))
            if not binding_paths and class_name_counts[entry.class_name] == 1:
                binding_paths = list(discover_binding_paths(entry.class_name))
            binding_info = parse_bindings(binding_paths, entry.class_name)
            rows = build_api_rows(entry, header_rel, binding_info)
            output_path = OUTPUT_DIR / f"{slugify(entry.category)}_{camel_to_snake(entry.class_name)}_methods.csv"
            summary_rows.append(summarize_rows(entry, output_path, header_rel, binding_info, rows))
            generated += 1

        summary_path = write_summary_csv(summary_rows)
        print("Inventory JSON not found; rebuilt summary from existing detail CSV files.")
        print(f"Generated summary CSV at {summary_path}")
        return

    for entry in todo_entries:
        inventory_records = records_by_class.get(entry.class_name, [])
        header_rel, fallback_scope = locate_header(entry.class_name, inventory_records)
        binding_paths = list(dict.fromkeys(converted_map.get(entry.class_name, [])))
        if not binding_paths and class_name_counts[entry.class_name] == 1:
            binding_paths = list(discover_binding_paths(entry.class_name))
        binding_info = parse_bindings(binding_paths, entry.class_name)
        rows = build_api_rows(entry, header_rel, binding_info)
        scope_slug = deduce_scope(entry, inventory_records, fallback_scope)
        file_name = f"{scope_slug}_{camel_to_snake(entry.class_name)}_methods.csv"
        output_path = OUTPUT_DIR / file_name
        write_csv(entry, output_path, header_rel, binding_info, rows)
        summary_rows.append(summarize_rows(entry, output_path, header_rel, binding_info, rows))
        generated += 1

    summary_path = write_summary_csv(summary_rows)

    print(f"Generated {generated} method inventory CSV files in {OUTPUT_DIR}")
    print(f"Generated summary CSV at {summary_path}")


if __name__ == "__main__":
    main()
