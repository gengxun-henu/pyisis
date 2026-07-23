"""Generate the curated ISIS 10-only pybind candidate inventory.

Author: Geng Xun
Created: 2026-07-23
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


def _api(
    group: str,
    signature: str,
    python_name: str,
    note: str = "ISIS 10-only candidate; not bound yet",
) -> ApiItem:
    return ApiItem(group, signature, python_name, note)


CLASS_CANDIDATES = (
    ClassCandidate(
        1,
        "High",
        "IProj",
        "Map Projection",
        "isis/src/base/objs/IProj/IProj.h",
        "libisis",
        "Medium",
        "优先绑定；复用现有 TProjection/Pvl 包装和 tuple 型 XYRange 返回值",
        "通过 PROJ 支持通用投影，适用范围比新增任务专用类更广。",
        (
            _api("Construction/Enum", "IProj(Pvl &label, bool allowDefaults = false)", "isis_pybind.IProj()"),
            _api("Public API", "QString Name() const", "isis_pybind.IProj.name"),
            _api("Public API", "QString Version() const", "isis_pybind.IProj.version"),
            _api("Public API", "PvlGroup Mapping()", "isis_pybind.IProj.mapping"),
            _api("Mutation/Configuration", "bool SetGround(double lat, double lon)", "isis_pybind.IProj.set_ground"),
            _api("Mutation/Configuration", "bool SetCoordinate(double x, double y)", "isis_pybind.IProj.set_coordinate"),
            _api("Public API", "bool XYRange(double &minX, double &maxX, double &minY, double &maxY)", "isis_pybind.IProj.xy_range", "建议返回 Python 4-tuple"),
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
        "优先绑定；沿用现有 mission camera 的 Cube 生命周期与 SPICE ID 模式",
        "公开面小，可补齐 Chandrayaan-2 OHRC 几何模型。",
        (
            _api("Construction/Enum", "Chandrayaan2OhrcCamera(Cube &cube)", "isis_pybind.Chandrayaan2OhrcCamera()"),
            _api("Public API", "virtual int CkFrameId() const", "isis_pybind.Chandrayaan2OhrcCamera.ck_frame_id"),
            _api("Public API", "virtual int CkReferenceId() const", "isis_pybind.Chandrayaan2OhrcCamera.ck_reference_id"),
            _api("Public API", "virtual int SpkReferenceId() const", "isis_pybind.Chandrayaan2OhrcCamera.spk_reference_id"),
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
        "优先绑定；沿用现有 mission camera 的 Cube 生命周期与 SPICE ID 模式",
        "公开面小，可补齐 Chandrayaan-2 TMC 几何模型。",
        (
            _api("Construction/Enum", "Chandrayaan2TmcCamera(Cube &cube)", "isis_pybind.Chandrayaan2TmcCamera()"),
            _api("Public API", "virtual int CkFrameId() const", "isis_pybind.Chandrayaan2TmcCamera.ck_frame_id"),
            _api("Public API", "virtual int CkReferenceId() const", "isis_pybind.Chandrayaan2TmcCamera.ck_reference_id"),
            _api("Public API", "virtual int SpkReferenceId() const", "isis_pybind.Chandrayaan2TmcCamera.spk_reference_id"),
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
        "第二批绑定；显式转换 QString，并复用 CameraDistortionMap 生命周期策略",
        "提供 ISIS 10 新增的 OCAMS OpenCV 标定模型，对 OSIRIS-REx 数据有直接价值。",
        (
            _api("Construction/Enum", "OsirisRexOcamsOpenCVDistortionMap(Camera *parent, int naifIkCode, int functionIkCode, const QString &filtername, double zdir = 1.0)", "isis_pybind.OsirisRexOcamsOpenCVDistortionMap()", "需要 Camera keep_alive 和 str/QString 转换"),
            _api("Mutation/Configuration", "void SetCameraTemperature(double temp)", "isis_pybind.OsirisRexOcamsOpenCVDistortionMap.set_camera_temperature"),
            _api("Mutation/Configuration", "virtual bool SetFocalPlane(double dx, double dy)", "isis_pybind.OsirisRexOcamsOpenCVDistortionMap.set_focal_plane"),
            _api("Mutation/Configuration", "virtual bool SetUndistortedFocalPlane(double ux, double uy)", "isis_pybind.OsirisRexOcamsOpenCVDistortionMap.set_undistorted_focal_plane"),
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
        "先设计 Python 友好 facade；不直接暴露 GDALDataset*、QList* 和裸所有权",
        "GDAL 后端具有通用价值，但原始构造器和缓冲区接口不适合作为稳定 Python API。",
        (
            _api("Construction/Enum", "GdalIoHandler(QString &dataFilePath, const QList<int> *virtualBandList, GDALDataType pixelType = GDT_Float64, GDALAccess eAccess = GA_ReadOnly)", "isis_pybind.GdalIoHandler()", "应包装为 path、bands、dtype、mode"),
            _api("Construction/Enum", "GdalIoHandler(GDALDataset *geodataSet, const QList<int> *virtualBandList, GDALDataType pixelType = GDT_Float64)", "isis_pybind.GdalIoHandler.from_dataset", "默认不暴露裸 GDALDataset*"),
            _api("Public API", "void init()", "isis_pybind.GdalIoHandler.init"),
            _api("Read/Write IO", "virtual void read(Buffer &bufferToFill) const", "isis_pybind.GdalIoHandler.read"),
            _api("Read/Write IO", "virtual void write(const Buffer &bufferToWrite)", "isis_pybind.GdalIoHandler.write"),
            _api("Query", "virtual BigInt getDataSize() const", "isis_pybind.GdalIoHandler.get_data_size"),
            _api("Mutation/Configuration", "virtual void updateLabels(Pvl &labels)", "isis_pybind.GdalIoHandler.update_labels"),
            _api("Mutation/Configuration", "virtual void clearCache(bool blockForWriteCache = false)", "isis_pybind.GdalIoHandler.clear_cache"),
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
        "仅作为 GdalIoHandler 的抽象基类注册；不单独提供裸指针构造",
        "主要是底层抽象和 Qt 指针生命周期接口，直接 Python 使用价值有限。",
        (
            _api("Construction/Enum", "ImageIoHandler(const QList<int> *virtualBandList)", "isis_pybind.ImageIoHandler()", "抽象类；默认不暴露构造器"),
            _api("Read/Write IO", "virtual void read(Buffer &bufferToFill) const = 0", "isis_pybind.ImageIoHandler.read"),
            _api("Read/Write IO", "virtual void write(const Buffer &bufferToWrite) = 0", "isis_pybind.ImageIoHandler.write"),
            _api("Mutation/Configuration", "virtual void addCachingAlgorithm(CubeCachingAlgorithm *algorithm)", "isis_pybind.ImageIoHandler.add_caching_algorithm", "需要明确所有权"),
            _api("Mutation/Configuration", "virtual void clearCache(bool blockForWriteCache = true) const", "isis_pybind.ImageIoHandler.clear_cache"),
            _api("Query", "virtual BigInt getDataSize() const = 0", "isis_pybind.ImageIoHandler.get_data_size"),
            _api("Mutation/Configuration", "void setVirtualBands(const QList<int> *virtualBandList)", "isis_pybind.ImageIoHandler.set_virtual_bands", "建议改为 Python list 拷贝"),
            _api("Mutation/Configuration", "virtual void updateLabels(Pvl &labels) = 0", "isis_pybind.ImageIoHandler.update_labels"),
            _api("Public API", "QMutex *dataFileMutex()", "isis_pybind.ImageIoHandler.data_file_mutex", "Qt 同步原语默认不绑定"),
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
        "isis_pybind.csv2table",
        "优先设计参数字典/argv facade，并返回可选日志；不直接暴露 UserInterface",
        "CSV 到 ISIS Table 的转换是通用数据工作流，Python 调用价值高。",
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
        "isis_pybind.ocams2isis",
        "第二批 facade；优先 path + 参数对象，不暴露 UserInterface 引用",
        "直接覆盖 OSIRIS-REx OCAMS FITS 入库，具有明确任务价值。",
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
        "isis_pybind.eisstitch",
        "第二批 facade；先核实输入产品、外部数据和异常契约",
        "支持 Europa Clipper EIS 拼接，但任务依赖和测试数据要求较高。",
    ),
)


EXCLUDED_HEADERS = (
    ("Fixtures.h", "上游测试 fixture，不是运行时 API"),
    ("IEndian.h", "Endian.h 的重命名兼容项，功能已由现有 ByteOrder 绑定覆盖"),
    ("RestfulSpice.h", "当前公开内容为注释占位，没有可绑定的有效声明"),
    ("restincurl.h", "第三方内部 HTTP 实现，不应成为 isis_pybind 公共 API"),
)


def _normalized(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _camel_to_snake(name: str) -> str:
    first_pass = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first_pass).lower()


def _header_path(root: Path, relative_header: str) -> Path:
    return root / relative_header


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
        writer.writerow(
            ["Class Symbol", candidate.class_name, f"isis_pybind.{candidate.class_name}", "N", candidate.reason]
        )
        for item in candidate.api:
            writer.writerow([item.group, item.cpp_signature, item.python_name, "N", item.note])
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
                    "Current Binding": _current_binding(candidate.class_name),
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the curated ISIS 10-only class and function inventory."
    )
    parser.add_argument("--isis9-root", type=Path, default=DEFAULT_ISIS9_ROOT)
    parser.add_argument("--isis10-root", type=Path, default=DEFAULT_ISIS10_ROOT)
    parser.add_argument("--isis10-prefix", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    _validate_candidates(args.isis9_root, args.isis10_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    details = {
        candidate.class_name: _write_class_detail(args.output_dir, candidate)
        for candidate in CLASS_CANDIDATES
    }
    _write_summary(args.output_dir, args.isis10_prefix, details)
    _write_functions(args.output_dir, args.isis10_prefix)
    _write_exclusions(args.output_dir)
    print(
        f"wrote {len(CLASS_CANDIDATES)} class candidates and "
        f"{len(FUNCTION_CANDIDATES)} function candidates to {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
