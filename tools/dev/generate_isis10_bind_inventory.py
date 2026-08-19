"""Generate the complete installed-header diff and curated ISIS 10 inventory.

Author: Geng Xun
Created: 2026-07-23
Updated: 2026-07-24  Geng Xun added automatic prefix diff and classification gates.
Updated: 2026-07-24  Geng Xun aligned discovery with the official USGS ISIS 10 package.
Updated: 2026-07-24  Geng Xun recorded curated bindings and intentional API exclusions.
Updated: 2026-08-02  Geng Xun closed ISIS 10 application-entry-point dispositions.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ISIS9_ROOT = PROJECT_ROOT / "reference" / "upstream_isis" / "9.0.0"
DEFAULT_ISIS10_ROOT = PROJECT_ROOT / "reference" / "upstream_isis" / "10.0.0"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reference" / "isis10_bind_candidates"


@dataclass(frozen=True)
class ApiItem:
    group: str
    cpp_signature: str
    python_name: str
    note: str
    converted: str | None = None


@dataclass(frozen=True)
class ClassCandidate:
    priority_rank: int
    priority: str
    class_name: str
    category: str
    header: str
    runtime_library: str
    risk: str
    recommendation: str
    reason: str
    api: tuple[ApiItem, ...]


@dataclass(frozen=True)
class FunctionCandidate:
    priority_rank: int
    priority: str
    function_name: str
    category: str
    header: str
    signature: str
    runtime_library: str
    risk: str
    proposed_python_name: str
    recommendation: str
    reason: str


@dataclass(frozen=True)
class HeaderClassification:
    kind: str
    disposition: str
    symbols: str
    reason: str


def _api(
    group: str,
    signature: str,
    python_name: str,
    note: str = "ISIS 10-only candidate; not bound yet",
    converted: str | None = None,
) -> ApiItem:
    return ApiItem(group, signature, python_name, note, converted)


CLASS_CANDIDATES = (
    ClassCandidate(
        1,
        "High",
        "IProj",
        "Map Projection",
        "isis/src/base/objs/IProj/IProj.h",
        "libisis",
        "Medium",
        "已绑定并完成 ISIS 9 缺席/ISIS 10 行为验证；复用 TProjection/Pvl 包装并以 tuple 返回 XYRange",
        "通过 PROJ 支持通用投影，适用范围比新增任务专用类更广。",
        (
            _api("Construction/Enum", "IProj(Pvl &label, bool allowDefaults = false)", "isis_pybind.IProj()", "Bound with Pvl reference and allow_defaults"),
            _api("Public API", "QString Name() const", "isis_pybind.IProj.name", "Converted to Python str"),
            _api("Public API", "QString Version() const", "isis_pybind.IProj.version", "Converted to Python str"),
            _api("Public API", "PvlGroup Mapping()", "isis_pybind.IProj.mapping", "Returns bound PvlGroup"),
            _api("Mutation/Configuration", "bool SetGround(double lat, double lon)", "isis_pybind.IProj.set_ground", "Bound"),
            _api("Mutation/Configuration", "bool SetCoordinate(double x, double y)", "isis_pybind.IProj.set_coordinate", "Bound"),
            _api("Public API", "bool XYRange(double &minX, double &maxX, double &minY, double &maxY)", "isis_pybind.IProj.xy_range", "Returns Python 4-tuple and raises on failure"),
        ),
    ),
    ClassCandidate(
        2,
        "High",
        "Chandrayaan2OhrcCamera",
        "Chandrayaan-2",
        "isis/src/chandrayaan2/objs/Chandrayaan2OhrcCamera/Chandrayaan2OhrcCamera.h",
        "libChandrayaan2OhrcCamera",
        "Low",
        "已绑定并完成 ISIS 9 缺席/ISIS 10 继承验证；沿用 mission camera 的 Cube 生命周期与 SPICE ID 模式",
        "公开面小，可补齐 Chandrayaan-2 OHRC 几何模型。",
        (
            _api("Construction/Enum", "Chandrayaan2OhrcCamera(Cube &cube)", "isis_pybind.Chandrayaan2OhrcCamera()", "Bound with Cube keep_alive"),
            _api("Public API", "virtual int CkFrameId() const", "isis_pybind.Chandrayaan2OhrcCamera.ck_frame_id", "Bound"),
            _api("Public API", "virtual int CkReferenceId() const", "isis_pybind.Chandrayaan2OhrcCamera.ck_reference_id", "Bound"),
            _api("Public API", "virtual int SpkReferenceId() const", "isis_pybind.Chandrayaan2OhrcCamera.spk_reference_id", "Bound"),
        ),
    ),
    ClassCandidate(
        3,
        "High",
        "Chandrayaan2TmcCamera",
        "Chandrayaan-2",
        "isis/src/chandrayaan2/objs/Chandrayaan2TmcCamera/Chandrayaan2TmcCamera.h",
        "libChandrayaan2TmcCamera",
        "Low",
        "已绑定并完成 ISIS 9 缺席/ISIS 10 继承验证；沿用 mission camera 的 Cube 生命周期与 SPICE ID 模式",
        "公开面小，可补齐 Chandrayaan-2 TMC 几何模型。",
        (
            _api("Construction/Enum", "Chandrayaan2TmcCamera(Cube &cube)", "isis_pybind.Chandrayaan2TmcCamera()", "Bound with Cube keep_alive"),
            _api("Public API", "virtual int CkFrameId() const", "isis_pybind.Chandrayaan2TmcCamera.ck_frame_id", "Bound"),
            _api("Public API", "virtual int CkReferenceId() const", "isis_pybind.Chandrayaan2TmcCamera.ck_reference_id", "Bound"),
            _api("Public API", "virtual int SpkReferenceId() const", "isis_pybind.Chandrayaan2TmcCamera.spk_reference_id", "Bound"),
        ),
    ),
    ClassCandidate(
        4,
        "Medium",
        "OsirisRexOcamsOpenCVDistortionMap",
        "OSIRIS-REx",
        "isis/src/osirisrex/objs/OsirisRexOcamsCamera/OsirisRexOcamsOpenCVDistortionMap.h",
        "libOsirisRexOcamsCamera",
        "Medium",
        "已绑定；显式转换 QString、拒绝空 Camera，并用 keep_alive 保持父相机生命周期",
        "提供 ISIS 10 新增的 OCAMS OpenCV 标定模型，对 OSIRIS-REx 数据有直接价值。",
        (
            _api("Construction/Enum", "OsirisRexOcamsOpenCVDistortionMap(Camera *parent, int naifIkCode, int functionIkCode, const QString &filtername, double zdir = 1.0)", "isis_pybind.OsirisRexOcamsOpenCVDistortionMap()", "Camera uses keep_alive; Python str is converted to QString; null Camera raises ValueError"),
            _api("Mutation/Configuration", "void SetCameraTemperature(double temp)", "isis_pybind.OsirisRexOcamsOpenCVDistortionMap.set_camera_temperature", "Bound"),
            _api("Mutation/Configuration", "virtual bool SetFocalPlane(double dx, double dy)", "isis_pybind.OsirisRexOcamsOpenCVDistortionMap.set_focal_plane", "Bound"),
            _api("Mutation/Configuration", "virtual bool SetUndistortedFocalPlane(double ux, double uy)", "isis_pybind.OsirisRexOcamsOpenCVDistortionMap.set_undistorted_focal_plane", "Bound"),
        ),
    ),
    ClassCandidate(
        5,
        "Medium",
        "GdalIoHandler",
        "Image I/O",
        "isis/src/base/objs/ImageIoHandler/GdalIoHandler.h",
        "libisis",
        "High",
        "已绑定 Python 友好 facade；预检路径和波段，映射 PixelType，默认只读且不暴露 GDALDataset*",
        "GDAL 后端具有通用价值，但原始构造器和缓冲区接口不适合作为稳定 Python API。",
        (
            _api("Construction/Enum", "GdalIoHandler(QString &dataFilePath, const QList<int> *virtualBandList, GDALDataType pixelType = GDT_Float64, GDALAccess eAccess = GA_ReadOnly)", "isis_pybind.GdalIoHandler()", "Bound as path, Python band list, PixelType, and writable flag; validates file and bands"),
            _api("Construction/Enum", "GdalIoHandler(GDALDataset *geodataSet, const QList<int> *virtualBandList, GDALDataType pixelType = GDT_Float64)", "isis_pybind.GdalIoHandler.from_dataset", "Intentionally excluded: raw GDALDataset pointer ownership is unsafe", "N"),
            _api("Public API", "void init()", "isis_pybind.GdalIoHandler.init", "Intentionally excluded: the public constructor initializes the handler", "N"),
            _api("Read/Write IO", "virtual void read(Buffer &bufferToFill) const", "isis_pybind.GdalIoHandler.read", "Bound and tested with Brick"),
            _api("Read/Write IO", "virtual void write(const Buffer &bufferToWrite)", "isis_pybind.GdalIoHandler.write", "Bound"),
            _api("Query", "virtual BigInt getDataSize() const", "isis_pybind.GdalIoHandler.get_data_size", "Bound"),
            _api("Mutation/Configuration", "virtual void updateLabels(Pvl &labels)", "isis_pybind.GdalIoHandler.update_labels", "Bound and tested with a GTiff label"),
            _api("Mutation/Configuration", "virtual void clearCache(bool blockForWriteCache = false)", "isis_pybind.GdalIoHandler.clear_cache", "Bound on the derived handler"),
        ),
    ),
    ClassCandidate(
        6,
        "Low",
        "ImageIoHandler",
        "Image I/O",
        "isis/src/base/objs/ImageIoHandler/ImageIoHandler.h",
        "libisis",
        "High",
        "已注册抽象基类并暴露共享 I/O 方法；排除裸所有权、Qt mutex 和无操作基类缓存接口",
        "主要是底层抽象和 Qt 指针生命周期接口，直接 Python 使用价值有限。",
        (
            _api("Construction/Enum", "ImageIoHandler(const QList<int> *virtualBandList)", "isis_pybind.ImageIoHandler()", "Intentionally excluded: abstract base is not directly constructible", "N"),
            _api("Read/Write IO", "virtual void read(Buffer &bufferToFill) const = 0", "isis_pybind.ImageIoHandler.read", "Bound as the inherited I/O contract"),
            _api("Read/Write IO", "virtual void write(const Buffer &bufferToWrite) = 0", "isis_pybind.ImageIoHandler.write", "Bound as the inherited I/O contract"),
            _api("Mutation/Configuration", "virtual void addCachingAlgorithm(CubeCachingAlgorithm *algorithm)", "isis_pybind.ImageIoHandler.add_caching_algorithm", "Intentionally excluded: raw algorithm ownership is unclear", "N"),
            _api("Mutation/Configuration", "virtual void clearCache(bool blockForWriteCache = true) const", "isis_pybind.ImageIoHandler.clear_cache", "Intentionally excluded: base implementation is a no-op; derived clear_cache is exposed", "N"),
            _api("Query", "virtual BigInt getDataSize() const = 0", "isis_pybind.ImageIoHandler.get_data_size", "Bound"),
            _api("Mutation/Configuration", "void setVirtualBands(const QList<int> *virtualBandList)", "isis_pybind.ImageIoHandler.set_virtual_bands", "Bound through a copied Python list"),
            _api("Mutation/Configuration", "virtual void updateLabels(Pvl &labels) = 0", "isis_pybind.ImageIoHandler.update_labels", "Bound"),
            _api("Public API", "QMutex *dataFileMutex()", "isis_pybind.ImageIoHandler.data_file_mutex", "Intentionally excluded: Qt synchronization primitive", "N"),
        ),
    ),
)


FUNCTION_CANDIDATES = (
    FunctionCandidate(
        1,
        "High",
        "csv2table",
        "Table I/O",
        "isis/src/base/apps/csv2table/csv2table.h",
        "void csv2table(UserInterface &ui, Pvl *log = nullptr)",
        "libisis",
        "Medium",
        "N/A (native ISIS APP)",
        "采用原生 ISIS APP 执行边界；ISIS 9/10 与 Windows/Linux 均不新增 Python wrapper 或进程内绑定",
        "CSV 到 ISIS Table 的转换由安装的 csv2table 可执行程序提供。",
    ),
    FunctionCandidate(
        2,
        "Medium",
        "ocams2isis",
        "OSIRIS-REx",
        "isis/src/osirisrex/apps/ocams2isis/ocams2isis.h",
        "void ocams2isis(UserInterface &ui, Pvl *log = nullptr); void ocams2isis(FileName &fitsFileName, UserInterface &ui)",
        "libosirisrex",
        "High",
        "N/A (native ISIS APP)",
        "采用原生 ISIS APP 执行边界；不绑定 UserInterface 引用，也不新增逐程序 Python wrapper",
        "直接覆盖 OSIRIS-REx OCAMS FITS 入库；现有原生 APP 已满足跨平台处理边界。",
    ),
    FunctionCandidate(
        3,
        "Medium",
        "eisstitch",
        "Europa Clipper",
        "isis/src/clipper/apps/eisstitch/eisstitch.h",
        "void eisstitch(UserInterface &ui)",
        "libclipper",
        "High",
        "N/A (native ISIS APP)",
        "采用原生 ISIS APP 执行边界；不绑定 UserInterface 引用，也不新增逐程序 Python wrapper",
        "支持 Europa Clipper EIS 拼接；现有原生 APP 已满足跨平台处理边界。",
    ),
)


EXCLUDED_HEADERS = (
    ("Fixtures.h", "上游测试 fixture，不是运行时 API"),
    ("IEndian.h", "Endian.h 的重命名兼容项，功能已由现有 ByteOrder 绑定覆盖"),
    ("RestfulSpice.h", "当前公开内容为注释占位，没有可绑定的有效声明"),
    ("restincurl.h", "第三方内部 HTTP 实现，不应成为 isis_pybind 公共 API"),
)


# This table classifies the automatically discovered installed-header diff.
# It is intentionally separate from CLASS_CANDIDATES/FUNCTION_CANDIDATES:
# discovery must remain complete even while detailed API review is unfinished.
HEADER_CLASSIFICATIONS = {
    "Chandrayaan2OhrcCamera.h": HeaderClassification(
        "class",
        "complete",
        "Chandrayaan2OhrcCamera",
        "ISIS 10-only mission camera; dual-version compatibility review closed",
    ),
    "Chandrayaan2TmcCamera.h": HeaderClassification(
        "class",
        "complete",
        "Chandrayaan2TmcCamera",
        "ISIS 10-only mission camera; dual-version compatibility review closed",
    ),
    "DskSegmentBuffer.hpp": HeaderClassification(
        "internal",
        "excluded",
        "DskSegmentBuffer",
        "Header marks this DSK mesh buffer internal; do not expose it as public API",
    ),
    "GdalIoHandler.h": HeaderClassification(
        "class",
        "candidate",
        "GdalIoHandler",
        "Public image-I/O class; curated Python facade is complete",
    ),
    "IEndian.h": HeaderClassification(
        "compatibility",
        "excluded",
        "ByteOrder",
        "Endian.h rename/compatibility surface already covered by the existing binding",
    ),
    "IProj.h": HeaderClassification(
        "class",
        "complete",
        "IProj",
        "ISIS 10-only projection class; dual-version compatibility review closed",
    ),
    "ImageIoHandler.h": HeaderClassification(
        "class",
        "candidate",
        "ImageIoHandler",
        "Abstract image-I/O base registered for the completed GdalIoHandler facade",
    ),
    "OsirisRexOcamsOpenCVDistortionMap.h": HeaderClassification(
        "class",
        "candidate",
        "OsirisRexOcamsOpenCVDistortionMap",
        "Public OCAMS OpenCV distortion model with mission-specific value",
    ),
    "RestfulSpice.h": HeaderClassification(
        "placeholder",
        "excluded",
        "",
        "Installed header contains no bindable public declaration",
    ),
    "csv2table.h": HeaderClassification(
        "function",
        "native-app",
        "csv2table",
        "Use the native ISIS APP in every supported version/OS cell; do not bind UserInterface",
    ),
    "eisstitch.h": HeaderClassification(
        "function",
        "native-app",
        "eisstitch",
        "Use the native ISIS APP; raw UserInterface binding is intentionally excluded",
    ),
    "ocams2isis.h": HeaderClassification(
        "function",
        "native-app",
        "ocams2isis",
        "Use the native ISIS APP; raw UserInterface binding is intentionally excluded",
    ),
    "restincurl.h": HeaderClassification(
        "internal",
        "excluded",
        "restincurl implementation types",
        "Third-party HTTP implementation must not become public isis_pybind API",
    ),
}

COMPLETE_CLASS_BINDINGS = {
    "IProj",
    "Chandrayaan2OhrcCamera",
    "Chandrayaan2TmcCamera",
    "OsirisRexOcamsOpenCVDistortionMap",
    "GdalIoHandler",
    "ImageIoHandler",
}


def _normalized(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _camel_to_snake(name: str) -> str:
    first_pass = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first_pass).lower()


def _header_path(root: Path, relative_header: str) -> Path:
    return root / relative_header


def _installed_header_names(prefix: Path) -> set[str]:
    header_dir = prefix / "include" / "isis"
    if not header_dir.is_dir():
        raise FileNotFoundError(f"ISIS include directory not found: {header_dir}")
    return {
        path.name
        for path in header_dir.iterdir()
        if path.is_file() and path.suffix in {".h", ".hpp"}
    }


def _discover_new_installed_headers(
    isis9_prefix: Path, isis10_prefix: Path
) -> list[str]:
    return sorted(
        _installed_header_names(isis10_prefix)
        - _installed_header_names(isis9_prefix)
    )


def _validate_header_classifications(
    discovered_headers: list[str],
    classifications: dict[str, HeaderClassification],
) -> None:
    discovered = set(discovered_headers)
    classified = set(classifications)
    missing = sorted(discovered - classified)
    stale = sorted(classified - discovered)
    errors = []
    if missing:
        errors.append(f"Unclassified ISIS 10 headers: {', '.join(missing)}")
    if stale:
        errors.append(
            "Classifications not present in installed ISIS 10 diff: "
            + ", ".join(stale)
        )
    if errors:
        raise ValueError("\n".join(errors))


def _validate_candidate_installation(discovered_headers: list[str]) -> None:
    discovered = set(discovered_headers)
    candidate_headers = {
        Path(candidate.header).name
        for candidate in (*CLASS_CANDIDATES, *FUNCTION_CANDIDATES)
    }
    missing = sorted(candidate_headers - discovered)
    if missing:
        raise ValueError(
            "Curated candidates not present in installed ISIS 10 diff: "
            + ", ".join(missing)
        )


def _validate_candidates(isis9_root: Path, isis10_root: Path) -> None:
    errors: list[str] = []
    for candidate in (*CLASS_CANDIDATES, *FUNCTION_CANDIDATES):
        isis10_header = _header_path(isis10_root, candidate.header)
        if not isis10_header.is_file():
            errors.append(f"ISIS 10 header missing: {candidate.header}")
            continue
        isis9_header = _header_path(isis9_root, candidate.header)
        if isis9_header.exists():
            errors.append(f"candidate is not ISIS 10-only: {candidate.header}")
        text = _normalized(isis10_header.read_text(encoding="utf-8", errors="replace"))
        symbol = (
            candidate.class_name
            if isinstance(candidate, ClassCandidate)
            else candidate.function_name
        )
        if symbol not in text:
            errors.append(f"symbol {symbol} not found in {candidate.header}")
    if errors:
        raise ValueError("\n".join(errors))


def _is_prefix_installed(prefix: Path | None, header: str) -> str:
    if prefix is None:
        return "not_checked"
    return "yes" if (prefix / "include" / "isis" / Path(header).name).is_file() else "no"


def _current_binding(class_name: str) -> str:
    matches = []
    for path in sorted((PROJECT_ROOT / "src").rglob("*.cpp")):
        if re.search(rf"\bIsis::{re.escape(class_name)}\b", path.read_text(encoding="utf-8", errors="replace")):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    return ";".join(matches) if matches else "N/A"


def _write_class_detail(output_dir: Path, candidate: ClassCandidate) -> str:
    filename = _camel_to_snake(candidate.class_name) + "_methods.csv"
    path = output_dir / "class_details" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            ["Class", "Module Category", "Source", "Binding", "Status Legend", "Python Naming Note", "Class Note"]
        )
        writer.writerow(
            [
                candidate.class_name,
                candidate.category,
                candidate.header,
                _current_binding(candidate.class_name),
                "Y = converted; N = not converted; Partial = partially converted",
                "Unconverted entries use the proposed Python name",
                candidate.recommendation,
            ]
        )
        writer.writerow([])
        writer.writerow(["Group", "C++ Method/Content", "Python Class/Function Name", "Converted", "Notes"])
        converted = "Y" if candidate.class_name in COMPLETE_CLASS_BINDINGS else "N"
        class_note = (
            "ISIS 10-only binding; tested against the target ISIS 10 environment"
            if converted == "Y"
            else candidate.reason
        )
        writer.writerow(
            ["Class Symbol", candidate.class_name, f"isis_pybind.{candidate.class_name}", converted, class_note]
        )
        for item in candidate.api:
            item_converted = item.converted if item.converted is not None else converted
            writer.writerow(
                [item.group, item.cpp_signature, item.python_name, item_converted, item.note]
            )
    return path.name


def _write_summary(
    output_dir: Path,
    prefix: Path | None,
    detail_files: dict[str, str],
) -> None:
    fields = [
        "Priority Rank",
        "Suggested Priority",
        "Class",
        "Module Category",
        "Generated CSV",
        "Source",
        "Installed in ISIS 10 Prefix",
        "ISIS 9 Same Path",
        "Current Binding",
        "Public API Items",
        "Runtime Library",
        "Binding Risk",
        "Recommendation",
        "Priority Reason",
    ]
    with (output_dir / "classes_inventory_summary.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for candidate in CLASS_CANDIDATES:
            writer.writerow(
                {
                    "Priority Rank": candidate.priority_rank,
                    "Suggested Priority": candidate.priority,
                    "Class": candidate.class_name,
                    "Module Category": candidate.category,
                    "Generated CSV": f"class_details/{detail_files[candidate.class_name]}",
                    "Source": candidate.header,
                    "Installed in ISIS 10 Prefix": _is_prefix_installed(prefix, candidate.header),
                    "ISIS 9 Same Path": "no",
                    "Current Binding": (
                        "ISIS 10-only (complete)"
                        if candidate.class_name in COMPLETE_CLASS_BINDINGS
                        else _current_binding(candidate.class_name)
                    ),
                    "Public API Items": len(candidate.api),
                    "Runtime Library": candidate.runtime_library,
                    "Binding Risk": candidate.risk,
                    "Recommendation": candidate.recommendation,
                    "Priority Reason": candidate.reason,
                }
            )


def _write_functions(output_dir: Path, prefix: Path | None) -> None:
    fields = [
        "Priority Rank",
        "Suggested Priority",
        "Function",
        "Module Category",
        "Source",
        "C++ Signature",
        "Proposed Python Name",
        "Installed in ISIS 10 Prefix",
        "Runtime Library",
        "Binding Risk",
        "Recommendation",
        "Priority Reason",
    ]
    with (output_dir / "functions_inventory.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for candidate in FUNCTION_CANDIDATES:
            writer.writerow(
                {
                    "Priority Rank": candidate.priority_rank,
                    "Suggested Priority": candidate.priority,
                    "Function": candidate.function_name,
                    "Module Category": candidate.category,
                    "Source": candidate.header,
                    "C++ Signature": candidate.signature,
                    "Proposed Python Name": candidate.proposed_python_name,
                    "Installed in ISIS 10 Prefix": _is_prefix_installed(prefix, candidate.header),
                    "Runtime Library": candidate.runtime_library,
                    "Binding Risk": candidate.risk,
                    "Recommendation": candidate.recommendation,
                    "Priority Reason": candidate.reason,
                }
            )


def _write_exclusions(output_dir: Path) -> None:
    with (output_dir / "excluded_new_headers.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["Header", "Reason"])
        writer.writerows(EXCLUDED_HEADERS)


def _write_raw_header_diff(
    output_dir: Path,
    discovered_headers: list[str],
    classifications: dict[str, HeaderClassification],
) -> None:
    fields = ["Header", "Kind", "Disposition", "Symbols", "Reason"]
    with (output_dir / "raw_new_headers.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for header in discovered_headers:
            classification = classifications[header]
            writer.writerow(
                {
                    "Header": header,
                    "Kind": classification.kind,
                    "Disposition": classification.disposition,
                    "Symbols": classification.symbols,
                    "Reason": classification.reason,
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the curated ISIS 10-only class and function inventory."
    )
    parser.add_argument("--isis9-root", type=Path, default=DEFAULT_ISIS9_ROOT)
    parser.add_argument("--isis10-root", type=Path, default=DEFAULT_ISIS10_ROOT)
    parser.add_argument("--isis9-prefix", type=Path, required=True)
    parser.add_argument("--isis10-prefix", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    discovered_headers = _discover_new_installed_headers(
        args.isis9_prefix, args.isis10_prefix
    )
    _validate_header_classifications(
        discovered_headers, HEADER_CLASSIFICATIONS
    )
    _validate_candidate_installation(discovered_headers)
    if args.isis9_root.is_dir() and args.isis10_root.is_dir():
        _validate_candidates(args.isis9_root, args.isis10_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    details = {
        candidate.class_name: _write_class_detail(args.output_dir, candidate)
        for candidate in CLASS_CANDIDATES
    }
    _write_summary(args.output_dir, args.isis10_prefix, details)
    _write_functions(args.output_dir, args.isis10_prefix)
    _write_exclusions(args.output_dir)
    _write_raw_header_diff(
        args.output_dir, discovered_headers, HEADER_CLASSIFICATIONS
    )
    print(
        f"wrote {len(discovered_headers)} discovered headers, "
        f"{len(CLASS_CANDIDATES)} class candidates and "
        f"{len(FUNCTION_CANDIDATES)} function candidates to {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
