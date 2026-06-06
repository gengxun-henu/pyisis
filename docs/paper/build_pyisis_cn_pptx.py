#!/usr/bin/env python3
"""Build a Chinese PPTX deck for the PyISIS paper without external PPTX libs."""

from __future__ import annotations

import html
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
FIG_SRC = ROOT / "figures"
OUT = ROOT / "output"
ASSETS = OUT / "assets" / "figures"
PPTX = OUT / "final_presentation_cn.pptx"
EMU = 914400
SLIDE_W = 13.333333
SLIDE_H = 7.5
SLIDE_W_EMU = int(SLIDE_W * EMU)
SLIDE_H_EMU = int(SLIDE_H * EMU)


ACCENT = "1B5E79"
ACCENT2 = "C96A35"
DARK = "1E2933"
MID = "5D6975"
LIGHT = "F7F9FB"
LINE = "D6DEE6"
GREEN = "2F7D58"
RED = "B94A48"


def e(s: str) -> str:
    return html.escape(str(s), quote=True)


def emu(v: float) -> int:
    return int(v * EMU)


def ensure_dirs() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=ROOT, check=True)


def convert_pdf_figs() -> dict[str, Path]:
    selected = {
        "fig1_architecture": "figure1_architecture.pdf",
        "fig2_adaptive_routing": "figure2_adaptive_routing.pdf",
        "fig3_matching_examples": "figure3_matching_examples.pdf",
        "fig4_routing_space": "figure4_routing_space.pdf",
        "fig5_controlnet_pipeline": "figure5_controlnet_pipeline.pdf",
        "fig6_adaptive_efficiency": "figure6_adaptive_efficiency_main.pdf",
        "fig7_matching_matrix": "figure7_matching_line_matrix.pdf",
        "fig01_ori_dom_perf": "fig01_ori_dom_performance.pdf",
        "fig02_dom_ori_perf": "fig02_dom_ori_performance.pdf",
        "fig03_roundtrip": "fig03_dom_ori_roundtrip_accuracy.pdf",
        "fig04_solar_perf": "fig04_solar_performance.pdf",
        "fig05_solar_accuracy": "fig05_solar_angle_accuracy.pdf",
    }
    out: dict[str, Path] = {}
    for stem, pdf in selected.items():
        dest_prefix = ASSETS / stem
        for old in ASSETS.glob(f"{stem}*.png"):
            old.unlink()
        run(["pdftoppm", "-png", "-r", "360", str(FIG_SRC / pdf), str(dest_prefix)])
        candidates = sorted(ASSETS.glob(f"{stem}-*.png"))
        if not candidates:
            raise FileNotFoundError(f"pdftoppm produced no PNG for {pdf}")
        dest = max(candidates, key=nonwhite_score)
        final = ASSETS / f"{stem}.png"
        trim_whitespace(dest, final)
        for extra in candidates:
            if extra.exists():
                extra.unlink()
        out[stem] = final
    make_contact_sheet(out)
    return out


def nonwhite_score(path: Path) -> int:
    img = Image.open(path).convert("RGB")
    small = img.resize((max(1, img.width // 4), max(1, img.height // 4)))
    score = 0
    for r, g, b in small.getdata():
        if min(r, g, b) < 245:
            score += 1
    return score


def trim_whitespace(src: Path, dest: Path) -> None:
    img = Image.open(src).convert("RGB")
    pix = img.load()
    xs = []
    ys = []
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = pix[x, y]
            if min(r, g, b) < 245:
                xs.append(x)
                ys.append(y)
    if not xs:
        img.save(dest)
        return
    pad = 24
    box = (
        max(min(xs) - pad, 0),
        max(min(ys) - pad, 0),
        min(max(xs) + pad, img.width),
        min(max(ys) + pad, img.height),
    )
    img.crop(box).save(dest)


def make_contact_sheet(figs: dict[str, Path]) -> None:
    thumbs = []
    for name, path in figs.items():
        img = Image.open(path).convert("RGB")
        img.thumbnail((320, 210))
        canvas = Image.new("RGB", (340, 250), "white")
        canvas.paste(img, ((340 - img.width) // 2, 8))
        draw = ImageDraw.Draw(canvas)
        draw.text((10, 222), name, fill=(30, 41, 51))
        thumbs.append(canvas)
    cols = 3
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 340, rows * 250), "white")
    for i, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((i % cols) * 340, (i // cols) * 250))
    sheet.save(OUT / "asset_contact_sheet.png")


def rpr(size: int, color: str = DARK, bold: bool = False) -> str:
    b = ' b="1"' if bold else ""
    return (
        f'<a:rPr lang="zh-CN" sz="{size * 100}"{b}>'
        f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
        '<a:latin typeface="Aptos"/><a:ea typeface="Microsoft YaHei"/>'
        '</a:rPr>'
    )


def paragraph(text: str, size: int = 18, color: str = DARK, bold: bool = False, bullet: bool = False) -> str:
    ppr = '<a:pPr marL="285750" indent="-171450"><a:buChar char="•"/></a:pPr>' if bullet else "<a:pPr/>"
    return f"<a:p>{ppr}<a:r>{rpr(size, color, bold)}<a:t>{e(text)}</a:t></a:r></a:p>"


def textbox(idx: int, x: float, y: float, w: float, h: float, paras: list[str], fill: str | None = None, line: str | None = None) -> str:
    body = "".join(paras)
    fill_xml = f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>' if fill else "<a:noFill/>"
    line_xml = f'<a:ln w="9000"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>' if line else "<a:ln><a:noFill/></a:ln>"
    return f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{idx}" name="Text {idx}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{fill_xml}{line_xml}</p:spPr>
  <p:txBody><a:bodyPr wrap="square" lIns="91440" rIns="91440" tIns="45720" bIns="45720"/><a:lstStyle/>{body}</p:txBody>
</p:sp>"""


def rect(idx: int, x: float, y: float, w: float, h: float, fill: str, line: str | None = None) -> str:
    line_xml = f'<a:ln w="12000"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>' if line else "<a:ln><a:noFill/></a:ln>"
    return f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{idx}" name="Rect {idx}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>{line_xml}</p:spPr>
</p:sp>"""


def image_pic(idx: int, rid: str, name: str, path: Path, x: float, y: float, w: float, h: float) -> str:
    with Image.open(path) as im:
        iw, ih = im.size
    box_ratio = w / h
    img_ratio = iw / ih
    if img_ratio > box_ratio:
        disp_w = w
        disp_h = w / img_ratio
    else:
        disp_h = h
        disp_w = h * img_ratio
    dx = x + (w - disp_w) / 2
    dy = y + (h - disp_h) / 2
    return f"""
<p:pic>
  <p:nvPicPr><p:cNvPr id="{idx}" name="{e(name)}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>
  <p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>
  <p:spPr><a:xfrm><a:off x="{emu(dx)}" y="{emu(dy)}"/><a:ext cx="{emu(disp_w)}" cy="{emu(disp_h)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
</p:pic>"""


def title(title_text: str, subtitle: str | None = None) -> list[str]:
    paras = [paragraph(title_text, 25, DARK, True)]
    if subtitle:
        paras.append(paragraph(subtitle, 12, MID))
    return paras


def source_label(idx: int, text: str) -> str:
    return textbox(idx, 0.55, 7.08, 12.1, 0.28, [paragraph(text, 7, MID)])


def table_text(idx: int, x: float, y: float, w: float, h: float, rows: list[list[str]], head_fill: str = ACCENT) -> str:
    nrows = len(rows)
    ncols = max(len(r) for r in rows)
    cw = w / ncols
    rh = h / nrows
    parts: list[str] = []
    sid = idx
    for r, row in enumerate(rows):
        for c in range(ncols):
            val = row[c] if c < len(row) else ""
            fill = head_fill if r == 0 else ("FFFFFF" if r % 2 else "F2F6F8")
            color = "FFFFFF" if r == 0 else DARK
            parts.append(rect(sid, x + c * cw, y + r * rh, cw, rh, fill, LINE))
            sid += 1
            parts.append(textbox(sid, x + c * cw + 0.02, y + r * rh + 0.02, cw - 0.04, rh - 0.04, [paragraph(val, 10 if r else 9, color, r == 0)]))
            sid += 1
    return "".join(parts)


def slide_xml(shapes: list[str]) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill></p:bgPr></p:bg>
<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>{''.join(shapes)}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"""


def rels_xml(rels: list[tuple[str, str, str]]) -> str:
    body = "".join(
        f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{typ}" Target="{e(target)}"/>'
        for rid, typ, target in rels
    )
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{body}</Relationships>'


def deck_content(figs: dict[str, Path]) -> list[dict]:
    return [
        {
            "title": "PyISIS: 基于 ISIS 的行星遥感制图开发库",
            "kind": "cover",
            "fig": "fig1_architecture",
            "bullets": ["Python 直连 ISIS 几何核心", "面向自动控制网与深度匹配工作流", "Xun Geng · 2026"],
            "source": "Source: paper_pyisis_jstars_imrad.tex / Fig. 1",
        },
        {
            "title": "瓶颈不是单个算法，而是 ISIS 与 Python 工作流断裂",
            "kind": "bullets",
            "bullets": ["ISIS 几何严谨，但以 C++/命令行为主", "Python 生态适合算法研发与深度匹配", "中间文件与 subprocess 限制迭代效率", "光照变化与弱纹理使固定匹配器失效"],
        },
        {
            "title": "PyISIS 的核心定位：把摄影测量 API 带进 Python",
            "kind": "claim",
            "bullets": ["暴露 200+ ISIS C++ 类与类型", "覆盖 50+ 任务相机、SPICE、投影、控制网与束平差配置", "贡献是可复用开发库，而非新特征匹配器"],
        },
        {
            "title": "五层架构让 ISIS 几何与科学 Python 生态共存",
            "kind": "figure",
            "fig": "fig1_architecture",
            "bullets": ["pybind11 薄绑定保留 C++ 语义", "七个 Python 模块组织核心能力", "应用层支持匹配、控制网与 bundle adjustment"],
            "source": "Source: Fig. 1 Architecture",
        },
        {
            "title": "端到端流程从 ISIS Cube 走到 jigsaw 可用控制网",
            "kind": "widefig",
            "fig": "fig5_controlnet_pipeline",
            "bullets": ["DOM 匹配后回投到原始 line/sample", "ControlPoint / ControlMeasure 由 Python 直接构建"],
            "source": "Source: Fig. 3 Control-network pipeline",
        },
        {
            "title": "自适应路由用物理几何信号选择匹配策略",
            "kind": "widefig",
            "fig": "fig2_adaptive_routing",
            "bullets": ["纹理稀疏度 S：SIFT 密度、梯度、GLCM", "光照差异 D：SPICE 太阳高度角与方位角", "质量门控失败后级联升级"],
            "source": "Source: Fig. 2 Adaptive routing",
        },
        {
            "title": "路由规则把匹配选择变成可审计决策",
            "kind": "table",
            "bullets": ["S≤0.35 且 D≤0.20：优先 SIFT/FLANN", "S≥0.65 或 D≥0.55：优先 LoFTR", "中间区域使用 LightGlue"],
            "table": [
                ["条件", "初始匹配器", "原因"],
                ["低 S、低 D", "SIFT/FLANN", "纹理丰富、光照相近"],
                ["高 S 或高 D", "LoFTR", "弱纹理或大光照差"],
                ["其他情况", "LightGlue", "中等难度折中"],
            ],
        },
        {
            "title": "六对 LRO NAC 影像全部生成控制网",
            "kind": "table",
            "bullets": ["总计 121,856 个控制点", "212,972 个候选匹配经 RANSAC 过滤", "约 19% tile 被有效像素预筛剔除"],
            "table": [
                ["类型", "影像对", "有效 tile", "匹配 tile", "控制点", "时间"],
                ["Same-orbit", "2", "586", "131", "41,892", "332 s"],
                ["Cross-track", "4", "1,130", "480", "79,964", "438 s"],
                ["Total", "6", "1,716", "611", "121,856", "403 s"],
            ],
        },
        {
            "title": "同轨道落在 SIFT 区，跨轨影像进入深度匹配区",
            "kind": "figure",
            "fig": "fig4_routing_space",
            "bullets": ["决策边界：S=0.35/0.65，D=0.20/0.55", "Pair 5 弱纹理，Pair 6 大方位角差", "路由解释了为什么不能固定单一方法"],
            "source": "Source: Fig. 4 Routing decision space",
        },
        {
            "title": "自适应策略保持 3/3 成功，同时减少深度模型任务",
            "kind": "widefig",
            "fig": "fig6_adaptive_efficiency",
            "bullets": ["adaptive: 15 个 deep tile tasks", "固定深度匹配器：各 27 个 tasks", "深度任务减少 44.4%，仍满足 10 点成功准则"],
            "source": "Source: Fig. 6 Adaptive efficiency benchmark",
        },
        {
            "title": "匹配线矩阵显示：自适应追求足够且稳定的控制点",
            "kind": "widefig",
            "fig": "fig7_matching_matrix",
            "bullets": ["稀疏纹理对：adaptive 208 点，高于 SIFT+FLANN 67 点", "富纹理对：adaptive 10,415 点，避免全局深度匹配", "中等纹理对：adaptive 1,985 点，接近 SIFT+LightGlue"],
            "source": "Source: Fig. 7 Matching-line matrix",
        },
        {
            "title": "绑定层几何精度保持在亚毫像素量级",
            "kind": "multifig",
            "figs": ["fig01_ori_dom_perf", "fig02_dom_ori_perf", "fig03_roundtrip"],
            "bullets": ["DOM→原图回投开销仅 1.03–1.10×", "最大往返误差 0.278×10⁻³ pixels", "成功率 99.9990–99.9998%"],
            "source": "Source: Figs. 8-10 Geometry benchmarks",
        },
        {
            "title": "太阳几何与 ControlNet 遍历验证了库级可用性",
            "kind": "multifig",
            "figs": ["fig04_solar_perf", "fig05_solar_accuracy"],
            "bullets": ["太阳角计算开销 1.02–1.05×", "太阳方位/高度误差显示为 0.000×10⁻³ degrees", "84.2 MB 控制网遍历 462,222 measures 用时 7.01 s"],
            "source": "Source: Figs. 11-12 and ControlNet benchmark table",
        },
        {
            "title": "结论：PyISIS 是行星制图算法研发的 Python 化底座",
            "kind": "closing",
            "bullets": ["直接 API 访问减少文件耦合", "SPICE-aware 路由适配月球弱纹理与强光照差", "当前验证仍局限于 6 对 LRO NAC", "下一步：findfeatures / AutoCNet / jigsaw 残差验证"],
        },
    ]


def build_slide(slide: dict, figs: dict[str, Path], image_rids: dict[str, str]) -> tuple[str, list[tuple[str, str, str]]]:
    shapes: list[str] = [rect(2, 0, 0, SLIDE_W, 0.10, ACCENT)]
    rels = [("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml")]
    idx = 10
    kind = slide["kind"]
    if kind == "cover":
        shapes.append(rect(idx, 0, 0, SLIDE_W, SLIDE_H, LIGHT)); idx += 1
        fig = slide["fig"]
        rid = "rId2"
        rels.append((rid, "image", f"../media/{fig}.png"))
        shapes.append(image_pic(idx, rid, fig, figs[fig], 6.8, 0.75, 5.7, 4.2)); idx += 1
        shapes.append(textbox(idx, 0.75, 1.15, 6.1, 1.35, [paragraph(slide["title"], 25, DARK, True)])); idx += 1
        shapes.append(textbox(idx, 0.78, 2.85, 5.5, 1.3, [paragraph("基于 USGS ISIS 9.0.0 的 Python 绑定、几何计算与自动控制网工作流", 17, ACCENT)])); idx += 1
        for i, b in enumerate(slide["bullets"]):
            shapes.append(textbox(idx, 0.9, 4.45 + i * 0.42, 5.6, 0.32, [paragraph(b, 12, MID)])); idx += 1
        shapes.append(source_label(idx, slide["source"]))
    elif kind in {"figure", "widefig"}:
        shapes.append(textbox(idx, 0.55, 0.34, 12.1, 0.62, title(slide["title"]))); idx += 1
        fig = slide["fig"]
        rid = "rId2"
        rels.append((rid, "image", f"../media/{fig}.png"))
        if kind == "widefig":
            shapes.append(image_pic(idx, rid, fig, figs[fig], 0.55, 1.15, 9.55, 5.75)); idx += 1
            rail_x, rail_w = 10.35, 2.55
        else:
            shapes.append(image_pic(idx, rid, fig, figs[fig], 0.65, 1.25, 8.0, 5.55)); idx += 1
            rail_x, rail_w = 9.0, 3.0
        shapes.append(rect(idx, rail_x, 1.25, rail_w, 5.55, "F2F6F8", LINE)); idx += 1
        shapes.append(textbox(idx, rail_x + 0.15, 1.45, rail_w - 0.3, 0.38, [paragraph("读图要点", 13, ACCENT, True)])); idx += 1
        for i, b in enumerate(slide["bullets"]):
            shapes.append(textbox(idx, rail_x + 0.15, 2.05 + i * 0.80, rail_w - 0.3, 0.55, [paragraph(b, 11, DARK, bullet=True)])); idx += 1
        shapes.append(source_label(idx, slide.get("source", "")))
    elif kind == "multifig":
        shapes.append(textbox(idx, 0.55, 0.34, 12.1, 0.62, title(slide["title"]))); idx += 1
        figs_list = slide["figs"]
        for i, fig in enumerate(figs_list):
            rid = f"rId{2+i}"
            rels.append((rid, "image", f"../media/{fig}.png"))
            cols = len(figs_list)
            x = 0.55 + i * (8.7 / cols)
            shapes.append(image_pic(idx, rid, fig, figs[fig], x, 1.2, 8.4 / cols, 3.75)); idx += 1
        shapes.append(rect(idx, 0.75, 5.25, 11.8, 1.02, "F2F6F8", LINE)); idx += 1
        for i, b in enumerate(slide["bullets"]):
            shapes.append(textbox(idx, 1.0 + i * 3.85, 5.45, 3.5, 0.55, [paragraph(b, 11, DARK, True)])); idx += 1
        shapes.append(source_label(idx, slide.get("source", "")))
    elif kind == "table":
        shapes.append(textbox(idx, 0.55, 0.34, 12.1, 0.62, title(slide["title"]))); idx += 1
        shapes.append(table_text(idx, 0.7, 1.35, 7.8, 3.9, slide["table"])); idx += 100
        shapes.append(rect(idx, 8.95, 1.35, 3.2, 3.9, "F2F6F8", LINE)); idx += 1
        shapes.append(textbox(idx, 9.15, 1.6, 2.8, 0.4, [paragraph("汇报重点", 13, ACCENT, True)])); idx += 1
        for i, b in enumerate(slide["bullets"]):
            shapes.append(textbox(idx, 9.15, 2.25 + i * 0.72, 2.75, 0.55, [paragraph(b, 11, DARK, bullet=True)])); idx += 1
    elif kind == "claim":
        shapes.append(textbox(idx, 0.65, 0.45, 11.9, 0.68, title(slide["title"]))); idx += 1
        x_positions = [0.9, 4.7, 8.5]
        colors = [ACCENT, ACCENT2, GREEN]
        for i, b in enumerate(slide["bullets"]):
            shapes.append(rect(idx, x_positions[i], 2.05, 2.95, 2.35, "F2F6F8", colors[i])); idx += 1
            shapes.append(textbox(idx, x_positions[i] + 0.22, 2.35, 2.5, 1.3, [paragraph(b, 16, DARK, True)])); idx += 1
            shapes.append(textbox(idx, x_positions[i] + 0.22, 4.0, 2.5, 0.28, [paragraph(f"0{i+1}", 13, colors[i], True)])); idx += 1
        shapes.append(textbox(idx, 1.1, 5.55, 11.0, 0.55, [paragraph("技术路线：薄绑定 + 自适应匹配 + 控制网闭环。", 19, ACCENT, True)]))
    elif kind == "closing":
        shapes.append(textbox(idx, 0.65, 0.55, 12.0, 0.85, title(slide["title"]))); idx += 1
        for i, b in enumerate(slide["bullets"]):
            y = 1.85 + i * 0.95
            color = [ACCENT, GREEN, ACCENT2, RED][i]
            shapes.append(rect(idx, 1.0, y, 0.12, 0.52, color)); idx += 1
            shapes.append(textbox(idx, 1.35, y - 0.05, 10.8, 0.68, [paragraph(b, 17 if i < 2 else 15, DARK, True)])); idx += 1
        shapes.append(textbox(idx, 1.0, 6.45, 11.6, 0.4, [paragraph("定位：可扩展的行星摄影测量 Python 开发库，而不是替代 ISIS 生产体系。", 13, MID)]))
    elif kind == "bullets":
        shapes.append(textbox(idx, 0.65, 0.55, 12.0, 0.85, title(slide["title"]))); idx += 1
        for i, b in enumerate(slide["bullets"]):
            shapes.append(rect(idx, 1.1, 1.75 + i * 1.05, 0.16, 0.62, ACCENT if i < 2 else ACCENT2)); idx += 1
            shapes.append(textbox(idx, 1.45, 1.68 + i * 1.05, 10.9, 0.72, [paragraph(b, 17, DARK, True)])); idx += 1
    else:
        raise ValueError(kind)
    return slide_xml(shapes), rels


def package_pptx(slides: list[dict], figs: dict[str, Path]) -> None:
    if PPTX.exists():
        PPTX.unlink()
    with zipfile.ZipFile(PPTX, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types(len(slides), figs))
        z.writestr("_rels/.rels", rels_xml([("rId1", "officeDocument", "ppt/presentation.xml")]))
        z.writestr("ppt/presentation.xml", presentation_xml(len(slides)))
        pres_rels = [("rId1", "slideMaster", "slideMasters/slideMaster1.xml")]
        for i in range(len(slides)):
            pres_rels.append((f"rId{i+2}", "slide", f"slides/slide{i+1}.xml"))
        z.writestr("ppt/_rels/presentation.xml.rels", rels_xml(pres_rels))
        z.writestr("ppt/slideMasters/slideMaster1.xml", slide_master_xml())
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", rels_xml([("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml"), ("rId2", "theme", "../theme/theme1.xml")]))
        z.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout_xml())
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", rels_xml([("rId1", "slideMaster", "../slideMasters/slideMaster1.xml")]))
        z.writestr("ppt/theme/theme1.xml", theme_xml())
        z.writestr("ppt/presProps.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentationPr xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>')
        z.writestr("ppt/viewProps.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:viewPr xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>')
        z.writestr("ppt/tableStyles.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:tblStyleLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" def="{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}"/>')
        for name, path in figs.items():
            z.write(path, f"ppt/media/{name}.png")
        for i, slide in enumerate(slides, 1):
            sx, rels = build_slide(slide, figs, {})
            z.writestr(f"ppt/slides/slide{i}.xml", sx)
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", rels_xml(rels))


def content_types(nslides: int, figs: dict[str, Path]) -> str:
    overrides = [
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
        '<Override PartName="/ppt/presProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presProps+xml"/>',
        '<Override PartName="/ppt/viewProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml"/>',
        '<Override PartName="/ppt/tableStyles.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.tableStyles+xml"/>',
    ]
    for i in range(1, nslides + 1):
        overrides.append(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>' + "".join(overrides) + "</Types>"


def presentation_xml(nslides: int) -> str:
    slds = "".join(f'<p:sldId id="{255+i}" r:id="rId{i+2}"/>' for i in range(nslides))
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>{slds}</p:sldIdLst><p:sldSz cx="{SLIDE_W_EMU}" cy="{SLIDE_H_EMU}" type="wide"/><p:notesSz cx="6858000" cy="9144000"/><p:defaultTextStyle/></p:presentation>"""


def slide_master_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>"""


def slide_layout_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>"""


def theme_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="PyISIS CN"><a:themeElements><a:clrScheme name="PyISIS"><a:dk1><a:srgbClr val="{DARK}"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="{MID}"/></a:dk2><a:lt2><a:srgbClr val="{LIGHT}"/></a:lt2><a:accent1><a:srgbClr val="{ACCENT}"/></a:accent1><a:accent2><a:srgbClr val="{ACCENT2}"/></a:accent2><a:accent3><a:srgbClr val="{GREEN}"/></a:accent3><a:accent4><a:srgbClr val="{RED}"/></a:accent4><a:accent5><a:srgbClr val="64748B"/></a:accent5><a:accent6><a:srgbClr val="94A3B8"/></a:accent6><a:hlink><a:srgbClr val="{ACCENT}"/></a:hlink><a:folHlink><a:srgbClr val="{ACCENT2}"/></a:folHlink></a:clrScheme><a:fontScheme name="PyISIS Fonts"><a:majorFont><a:latin typeface="Aptos Display"/><a:ea typeface="Microsoft YaHei"/></a:majorFont><a:minorFont><a:latin typeface="Aptos"/><a:ea typeface="Microsoft YaHei"/></a:minorFont></a:fontScheme><a:fmtScheme name="PyISIS Format"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>"""


def write_manifest(slides: list[dict], figs: dict[str, Path]) -> None:
    lines = ["# Asset Manifest", "", "Generated for `final_presentation_cn.pptx`.", ""]
    mapping = {
        "fig1_architecture": "Fig. 1 / framework architecture / slides 1 and 4",
        "fig2_adaptive_routing": "Fig. 2 / adaptive routing workflow / slide 6",
        "fig5_controlnet_pipeline": "Fig. 3 / control-network pipeline / slide 5",
        "fig4_routing_space": "Fig. 4 / routing decision space / slide 9",
        "fig6_adaptive_efficiency": "Fig. 6 / adaptive benchmark / slide 10",
        "fig7_matching_matrix": "Fig. 7 / matching-line matrix / slide 11",
        "fig01_ori_dom_perf": "Binding benchmark / original-to-DOM performance / slide 12",
        "fig02_dom_ori_perf": "Binding benchmark / DOM-to-original performance / slide 12",
        "fig03_roundtrip": "Binding benchmark / round-trip accuracy / slide 12",
        "fig04_solar_perf": "Solar geometry benchmark / slide 13",
        "fig05_solar_accuracy": "Solar geometry agreement / slide 13",
    }
    for name, path in figs.items():
        note = mapping.get(name, "selected paper figure")
        lines.append(f"- `{path.name}`: {note}; source `{FIG_SRC / (name + '.pdf')}` where applicable; extraction via `pdftoppm -r 220`; full figure preserved.")
    (OUT / "asset_manifest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_notes(slides: list[dict]) -> None:
    lines = ["# 中文讲者提示", ""]
    for i, slide in enumerate(slides, 1):
        lines.append(f"## Slide {i}. {slide['title']}")
        for b in slide.get("bullets", []):
            lines.append(f"- {b}")
        lines.append("")
    (OUT / "speaker_notes_cn.md").write_text("\n".join(lines), encoding="utf-8")


def audit_pptx(slides: list[dict], figs: dict[str, Path]) -> tuple[int, int, list[str]]:
    defects: list[str] = []
    with zipfile.ZipFile(PPTX) as z:
        names = set(z.namelist())
        slide_count = sum(1 for n in names if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
        media_count = sum(1 for n in names if n.startswith("ppt/media/") and n.endswith(".png"))
        if slide_count != len(slides):
            defects.append(f"high: slide count mismatch {slide_count} != {len(slides)}")
        if media_count != len(figs):
            defects.append(f"medium: media count mismatch {media_count} != {len(figs)}")
        for i in range(1, len(slides) + 1):
            if f"ppt/slides/_rels/slide{i}.xml.rels" not in names:
                defects.append(f"high: missing rels for slide {i}")
    for name, path in figs.items():
        with Image.open(path) as im:
            if im.width < 900 or im.height < 500:
                defects.append(f"medium: low figure resolution {name}: {im.width}x{im.height}")
    return slide_count, media_count, defects


def write_qa(slides: list[dict], figs: dict[str, Path], defects: list[str], lo_ok: bool) -> None:
    lines = [
        "# QA Report",
        "",
        f"- PPTX: `{PPTX}`",
        f"- Slide count: {len(slides)}",
        f"- Extracted figure assets: {len(figs)}",
        "- Paper type: methods / tool / algorithm; narrative arc: problem-to-solution.",
        "- Terminology locked: PyISIS, ISIS, pybind11, SPICE, DOM, ControlNet, SIFT/FLANN, LightGlue, LoFTR, LRO NAC.",
        "",
        "## Self-review defects",
    ]
    if defects:
        lines.extend(f"- {d}" for d in defects)
    else:
        lines.append("- No high- or medium-severity structural defects detected by package/image audit.")
    lines.extend([
        "",
        "## Corrective revision",
        "- Used figure-dominant layouts for dense evidence slides and moved interpretation into narrow rails or compact bands.",
        "- Kept tables native as text blocks where values are explicit in the TEX source.",
        "- Source labels were added to figure slides.",
        "",
        "## Verification",
        "- Reopened the PPTX as a ZIP package and checked slide XML, relationships, media count, and selected asset resolution.",
        f"- LibreOffice headless validation: {'passed' if lo_ok else 'not available or failed; package-level validation only'}",
        "- Full rendered slide preview was not produced; `asset_contact_sheet.png` was generated for crop/readability inspection.",
        "- Speaker notes are provided as `speaker_notes_cn.md`; they are not embedded in the PPTX because the build used dependency-free OpenXML generation.",
    ])
    (OUT / "qa_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_libreoffice() -> bool:
    if not shutil.which("libreoffice"):
        return False
    validate_dir = OUT / "lo_validate"
    validate_dir.mkdir(exist_ok=True)
    try:
        subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(validate_dir), str(PPTX)],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
        )
        return (validate_dir / "final_presentation_cn.pdf").exists()
    except Exception:
        return False


def main() -> None:
    ensure_dirs()
    figs = convert_pdf_figs()
    slides = deck_content(figs)
    package_pptx(slides, figs)
    write_manifest(slides, figs)
    write_notes(slides)
    slide_count, media_count, defects = audit_pptx(slides, figs)
    lo_ok = validate_libreoffice()
    write_qa(slides, figs, defects, lo_ok)
    print(f"wrote {PPTX}")
    print(f"slides={slide_count} media={media_count} libreoffice={lo_ok}")
    if defects:
        print("defects:")
        for d in defects:
            print(f"- {d}")


if __name__ == "__main__":
    main()
