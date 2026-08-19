"""Rank pinned ISIS applications for staged native Windows porting."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re


HIGH_IMPORTANCE = {
    "automos",
    "cam2map",
    "caminfo",
    "campt",
    "camrange",
    "findfeatures",
    "footprintinit",
    "footprintmerge",
    "jigsaw",
    "map2map",
    "mapmos",
    "mappt",
    "maptemplate",
    "mosrange",
    "pointreg",
    "spicefit",
    "spiceinit",
}

IMPORTANT = {
    "ascii2isis",
    "autoseed",
    "camstats",
    "catlab",
    "cnetadd",
    "cnetcheck",
    "cnetdiff",
    "cnetedit",
    "cnetextract",
    "cnethist",
    "cnetmerge",
    "cnetref",
    "cnetstats",
    "crop",
    "cubeatt",
    "cubediff",
    "cubeit",
    "dsk2isis",
    "findimageoverlaps",
    "fits2isis",
    "fx",
    "getkey",
    "hrsc2isis",
    "isis2fits",
    "isis2pds",
    "isis2std",
    "lronac2isis",
    "lronaccal",
    "lronacecho",
    "lrowac2isis",
    "lrowaccal",
    "makecube",
    "map2cam",
    "mapgrid",
    "maplab",
    "maptrim",
    "pds2isis",
    "qmos",
    "qnet",
    "qview",
    "raw2isis",
    "reduce",
    "stats",
    "std2isis",
    "table2cube",
    "tabledump",
}

GENERAL_PROCESSING_TOKENS = (
    "cal",
    "clean",
    "crop",
    "cube",
    "filter",
    "hist",
    "map",
    "mos",
    "project",
    "spice",
    "stats",
    "stretch",
    "trim",
    "warp",
)

GUI_NAMES = {"cneteditor", "ipce", "qmos", "qnet", "qtie", "qview"}

BLOCKER_PATTERNS = {
    "posix_api": re.compile(
        r"#\s*include\s*[<\"](?:unistd\.h|sys/|dirent\.h)|"
        r"\b(?:fork|execv?p?|mkstemp|readlink|symlink)\s*\("
    ),
    "external_process": re.compile(
        r"\b(?:system|popen)\s*\(|\bQProcess\b|/bin/(?:sh|bash)"
    ),
    "platform_branch": re.compile(r"_WIN32|_MSC_VER|Q_OS_WIN"),
    "optional_stack": re.compile(
        r"#\s*include\s*[<\"](?:opencv|pcl|embree|hdf|gdal|netcdf|Python\.h)"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank every pinned ISIS APP for native Windows porting."
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        help="Pinned ISIS source root containing isis/src.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Tracked Windows APP manifest.",
    )
    parser.add_argument("--csv-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument(
        "--refresh-manifest-only",
        action="store_true",
        help="Refresh manifest membership from an existing priority CSV.",
    )
    return parser.parse_args()


def source_text(app_dir: Path) -> tuple[str, int, int]:
    chunks: list[str] = []
    source_files = 0
    source_lines = 0
    for path in sorted(app_dir.iterdir()):
        if path.suffix.lower() not in {".c", ".cc", ".cpp", ".h", ".hpp"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        chunks.append(text)
        source_files += 1
        source_lines += text.count("\n") + 1
    return "\n".join(chunks), source_files, source_lines


def importance(app: str, module: str) -> tuple[int, str]:
    if app in HIGH_IMPORTANCE:
        return 5, "核心导航制图、几何或控制网能力"
    if app in IMPORTANT:
        return 4, "常用数据处理、导入导出或任务支撑能力"
    if app in GUI_NAMES or module == "qisis":
        return 3, "重要交互工具，但 CLI/核心能力优先"
    if module in {"base", "control", "system"}:
        if any(token in app for token in GENERAL_PROCESSING_TOKENS):
            return 3, "通用处理或基础设施能力"
        return 2, "通用但使用频率或链路位置较低"
    if app.endswith("2isis") or app.endswith("cal"):
        return 3, "任务数据导入或标定能力"
    return 2, "任务专用或较窄用途能力"


def portability(
    app: str,
    module: str,
    text: str,
    source_lines: int,
) -> tuple[int, list[str]]:
    score = 5
    reasons: list[str] = []
    for label, pattern in BLOCKER_PATTERNS.items():
        if not pattern.search(text):
            continue
        reasons.append(label)
        if label in {"posix_api", "external_process"}:
            score -= 2
        elif label == "optional_stack":
            score -= 1
    if module == "qisis" or app in GUI_NAMES:
        score = min(score, 2)
        reasons.append("qt_gui")
    if source_lines > 3000:
        score -= 1
        reasons.append("large_source")
    if module not in {"base", "control", "system", "qisis"}:
        score -= 1
        reasons.append("mission_runtime_data")
    return max(1, min(5, score)), sorted(set(reasons))


def wave(portability_score: int, importance_score: int, gui: bool) -> str:
    if gui:
        return "W5-GUI"
    if importance_score >= 4 and portability_score >= 4:
        return "W1-high-value-easy"
    if importance_score >= 4 and portability_score == 3:
        return "W2-high-value-medium"
    if importance_score >= 3 and portability_score >= 4:
        return "W3-general-easy"
    if portability_score >= 3:
        return "W4-medium"
    return "W5-blocked-or-specialized"


def write_summary(
    rows: list[dict[str, object]],
    expected_commit: str,
    summary_output: Path,
) -> None:
    wave_counts: dict[str, int] = {}
    for row in rows:
        key = str(row["recommended_wave"])
        wave_counts[key] = wave_counts.get(key, 0) + 1
    top_rows = rows[:40]
    summary = [
        "# ISIS 10 Windows APP 移植优先级",
        "",
        f"- 固定源码提交：`{expected_commit}`",
        f"- APP 总数：{len(rows)}",
        "- 便利性和重要性均采用 1–5 分；综合分为 `重要性×10+便利性`，"
        "因此任务价值优先、同等级再优先选择易移植项。",
        "- 该表是源码级规划清单，不等同于 Windows 编译或科学结果验证。",
        "",
        "## 建议批次统计",
        "",
        "| 批次 | 数量 |",
        "|---|---:|",
    ]
    summary.extend(
        f"| {name} | {count} |"
        for name, count in sorted(wave_counts.items())
    )
    summary.extend(
        [
            "",
            "## 综合优先级前 40",
            "",
            "| 排名 | APP | 模块 | 便利性 | 重要性 | 建议批次 | 阻塞因素 |",
            "|---:|---|---|---:|---:|---|---|",
        ]
    )
    summary.extend(
        "| {overall_rank} | {app} | {module} | {portability_score} | "
        "{importance_score} | {recommended_wave} | {detected_blockers} |".format(
            **row
        )
        for row in top_rows
    )
    summary.extend(
        [
            "",
            "## 使用说明",
            "",
            "- `W1`：高价值且预计容易移植，优先进入下一批。",
            "- `W2`：高价值但存在中等平台风险，应单独编译定位。",
            "- `W3`：通用、易移植，可用于扩大覆盖面。",
            "- `W4`：中等优先级，等待核心链路稳定后推进。",
            "- `W5-GUI`：Qt GUI 单独成线，不与 CLI 批次混编。",
            "- `W5-blocked-or-specialized`：存在直接平台阻塞或任务用途较窄。",
            "",
            "完整 365 项及源码证据见 `windows-app-priority.csv`。",
        ]
    )
    summary_output.write_text("\n".join(summary) + "\n", encoding="utf-8")


def refresh_manifest_only(
    csv_output: Path,
    summary_output: Path,
    selected: set[str],
    expected_commit: str,
) -> int:
    with csv_output.open(encoding="utf-8", newline="") as priority_file:
        reader = csv.DictReader(priority_file)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if fieldnames is None:
        raise ValueError(f"priority CSV has no header: {csv_output}")
    required_fields = {
        "app",
        "module",
        "portability_score",
        "importance_score",
        "recommended_wave",
        "current_manifest",
    }
    missing_fields = required_fields - set(fieldnames)
    if missing_fields:
        raise ValueError(
            "priority CSV is missing required fields: "
            + ", ".join(sorted(missing_fields))
        )
    available = {row["app"] for row in rows}
    missing_apps = selected - available
    if missing_apps:
        raise ValueError(
            "priority CSV is missing manifest APPs: "
            + ", ".join(sorted(missing_apps))
        )

    for row in rows:
        app = row["app"]
        if app in selected:
            row["current_manifest"] = "yes"
            row["recommended_wave"] = "W0-current-batch"
        else:
            row["current_manifest"] = "no"
            row["recommended_wave"] = wave(
                int(row["portability_score"]),
                int(row["importance_score"]),
                row["module"] == "qisis" or app in GUI_NAMES,
            )

    with csv_output.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    write_summary(rows, expected_commit, summary_output)
    print(f"refreshed manifest membership for {len(rows)} ISIS APPs")
    return 0


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    selected = {app["name"] for app in manifest["apps"]}
    expected_commit = manifest["source_baselines"]["10.0.0"]["commit"]
    if args.refresh_manifest_only:
        return refresh_manifest_only(
            args.csv_output,
            args.summary_output,
            selected,
            expected_commit,
        )
    if args.source_root is None:
        raise ValueError("--source-root is required unless --refresh-manifest-only is used")
    source_root = args.source_root.resolve()

    app_dirs = sorted(
        path
        for path in (source_root / "isis" / "src").glob("*/apps/*")
        if path.is_dir()
        and (path / "main.cpp").is_file()
        and (path / f"{path.name}.xml").is_file()
    )
    rows: list[dict[str, object]] = []
    for app_dir in app_dirs:
        app = app_dir.name
        module = app_dir.parents[1].name
        text, source_files, source_lines = source_text(app_dir)
        importance_score, importance_reason = importance(app, module)
        portability_score, blockers = portability(
            app,
            module,
            text,
            source_lines,
        )
        rows.append(
            {
                "app": app,
                "module": module,
                "source_dir": app_dir.relative_to(source_root).as_posix(),
                "portability_score": portability_score,
                "importance_score": importance_score,
                "combined_score": importance_score * 10 + portability_score,
                "recommended_wave": (
                    "W0-current-batch"
                    if app in selected
                    else wave(
                        portability_score,
                        importance_score,
                        module == "qisis" or app in GUI_NAMES,
                    )
                ),
                "current_manifest": "yes" if app in selected else "no",
                "source_files": source_files,
                "source_lines": source_lines,
                "detected_blockers": ";".join(blockers) if blockers else "none",
                "importance_reason": importance_reason,
            }
        )

    rows.sort(
        key=lambda row: (
            -int(row["combined_score"]),
            -int(row["importance_score"]),
            -int(row["portability_score"]),
            str(row["module"]),
            str(row["app"]),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["overall_rank"] = index

    fieldnames = [
        "overall_rank",
        "app",
        "module",
        "portability_score",
        "importance_score",
        "combined_score",
        "recommended_wave",
        "current_manifest",
        "source_files",
        "source_lines",
        "detected_blockers",
        "importance_reason",
        "source_dir",
    ]
    args.csv_output.parent.mkdir(parents=True, exist_ok=True)
    with args.csv_output.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    write_summary(rows, expected_commit, args.summary_output)
    print(f"ranked {len(rows)} ISIS APPs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
