# -*- coding: utf-8 -*-
"""
code/04_export_docx.py
======================
角色：Reporter（报告撰写智能体）产物 —— Markdown → Word 导出
输入：outputs/零售销售数据分析报告.md
输出：outputs/零售销售数据分析报告.docx

实现说明：
  不依赖 pandoc / LibreOffice，用 python-docx 直接构建版式，保证在无外网、
  无 Office 环境的机器上也能一键复现。支持报告中实际用到的语法子集：
  标题（1—3 级）、段落、无序/有序列表、引用块、表格、图片、行内加粗/代码、分隔线。
  中文字体通过 w:eastAsia 显式指定（西文 Calibri，中文宋体/微软雅黑），
  否则 Word 会回落到西文字体导致中文显示异常。

运行：
    python code/04_export_docx.py
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BASE_DIR = Path(__file__).resolve().parent.parent
MD_PATH = BASE_DIR / "outputs" / "零售销售数据分析报告.md"
DOCX_PATH = BASE_DIR / "outputs" / "零售销售数据分析报告.docx"

FONT_CN_BODY = "宋体"
FONT_CN_HEAD = "微软雅黑"
FONT_EN = "Calibri"
COLOR_DARK = RGBColor(0x0D, 0x13, 0x26)
COLOR_BLUE = RGBColor(0x1E, 0x3A, 0x8A)
COLOR_GRAY = RGBColor(0x59, 0x5F, 0x6B)
HEADER_FILL = "DCE9FB"
ZEBRA_FILL = "F4F8FE"


# ----------------------------------------------------------------------
# 底层工具
# ----------------------------------------------------------------------
def set_run_font(run, cn: str = FONT_CN_BODY, en: str = FONT_EN, size: float | None = None,
                 bold: bool | None = None, color: RGBColor | None = None) -> None:
    """同时设置西文与中文字体（中文必须走 w:eastAsia，否则不生效）。"""
    run.font.name = en
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), en)
    rfonts.set(qn("w:hAnsi"), en)
    rfonts.set(qn("w:eastAsia"), cn)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


def shade_cell(cell, fill: str) -> None:
    tcpr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


def set_cell_margins(table, top=60, bottom=60, left=90, right=90) -> None:
    tblpr = table._element.tblPr
    mar = OxmlElement("w:tblCellMar")
    for tag, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{tag}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblpr.append(mar)


def add_page_number_footer(section) -> None:
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("第 ")
    set_run_font(r, size=9, color=COLOR_GRAY)
    for instr in ("PAGE",):
        fld = OxmlElement("w:fldSimple")
        fld.set(qn("w:instr"), instr)
        inner = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.text = "1"
        inner.append(t)
        fld.append(inner)
        p._p.append(fld)
    r2 = p.add_run(" 页")
    set_run_font(r2, size=9, color=COLOR_GRAY)


INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")


def add_inline(paragraph, text: str, size: float = 10.5, color: RGBColor | None = None) -> None:
    """解析行内 **加粗** / `代码` / [链接](url)。"""
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            r = paragraph.add_run(part[2:-2])
            set_run_font(r, size=size, bold=True, color=color)
        elif part.startswith("`") and part.endswith("`"):
            r = paragraph.add_run(part[1:-1])
            set_run_font(r, cn=FONT_CN_BODY, en="Consolas", size=size - 0.5, color=RGBColor(0xB0, 0x2A, 0x2A))
        elif part.startswith("[") and "](" in part:
            label = part[1: part.index("]")]
            url = part[part.index("](") + 2: -1]
            r = paragraph.add_run(f"{label}（{url}）" if not url.startswith("#") else label)
            set_run_font(r, size=size, color=COLOR_BLUE)
            r.font.underline = True
        else:
            r = paragraph.add_run(part)
            set_run_font(r, size=size, color=color)


# ----------------------------------------------------------------------
# 块级渲染
# ----------------------------------------------------------------------
def render_heading(doc: Document, text: str, level: int) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16 if level == 2 else 10)
    p.paragraph_format.space_after = Pt(8 if level == 2 else 6)
    p.paragraph_format.keep_with_next = True
    if level == 1:
        r = p.add_run(text)
        set_run_font(r, cn=FONT_CN_HEAD, size=22, bold=True, color=COLOR_DARK)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif level == 2:
        r = p.add_run(text)
        set_run_font(r, cn=FONT_CN_HEAD, size=15, bold=True, color=COLOR_BLUE)
        # 二级标题加下边框
        ppr = p._p.get_or_add_pPr()
        pbdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "8")
        bottom.set(qn("w:space"), "4")
        bottom.set(qn("w:color"), "2563EB")
        pbdr.append(bottom)
        ppr.append(pbdr)
    else:
        r = p.add_run(text)
        set_run_font(r, cn=FONT_CN_HEAD, size=12, bold=True, color=COLOR_DARK)


def render_paragraph(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.first_line_indent = Pt(0)
    pf.space_after = Pt(6)
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    add_inline(p, text)


def render_quote(doc: Document, lines: list[str]) -> None:
    """引用块：整块加浅底纹与左侧竖线，模拟“报告信息框”。"""
    for i, line in enumerate(lines):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Cm(0.6)
        pf.space_after = Pt(2 if i < len(lines) - 1 else 8)
        pf.space_before = Pt(6 if i == 0 else 0)
        add_inline(p, line, size=9.5, color=COLOR_GRAY)
        ppr = p._p.get_or_add_pPr()
        pbdr = OxmlElement("w:pBdr")
        left = OxmlElement("w:left")
        left.set(qn("w:val"), "single")
        left.set(qn("w:sz"), "18")
        left.set(qn("w:space"), "8")
        left.set(qn("w:color"), "9DB8E8")
        pbdr.append(left)
        ppr.append(pbdr)
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:fill"), "F6F9FE")
        ppr.append(shd)


def render_code_block(doc: Document, lines: list[str]) -> None:
    for line in lines:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.6)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.space_before = Pt(0)
        r = p.add_run(line if line else " ")
        set_run_font(r, en="Consolas", size=9)
        ppr = p._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:fill"), "F2F4F7")
        ppr.append(shd)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def render_list(doc: Document, items: list[tuple[str, str]]) -> None:
    """items: [(marker, text)]，marker 为 '•' 或 '1.'"""
    for marker, text in items:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Cm(0.9)
        pf.first_line_indent = Cm(-0.45)
        pf.space_after = Pt(3)
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        r = p.add_run(f"{marker} ")
        set_run_font(r, size=10.5, bold=marker not in ("•",))
        add_inline(p, text)


def render_table(doc: Document, rows: list[list[str]]) -> None:
    header, body = rows[0], rows[1:]
    ncol = len(header)
    table = doc.add_table(rows=1, cols=ncol)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    set_cell_margins(table)

    hdr = table.rows[0]
    for i, text in enumerate(header):
        cell = hdr.cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.space_before = Pt(2)
        add_inline(p, text, size=9.5)
        for r in p.runs:
            r.font.bold = True
            r.font.color.rgb = COLOR_DARK
        shade_cell(cell, HEADER_FILL)

    # 表格首行重复（跨页时表头再现）
    trpr = hdr._tr.get_or_add_trPr()
    tblheader = OxmlElement("w:tblHeader")
    trpr.append(tblheader)

    for ridx, row in enumerate(body):
        cells = table.add_row().cells
        for i in range(ncol):
            text = row[i] if i < len(row) else ""
            cell = cells[i]
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.space_before = Pt(2)
            # 纯数字/百分比列右对齐更易读
            if re.fullmatch(r"[\d,.\-%±−+ ]+", text or ""):
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            add_inline(p, text, size=9.5)
            if ridx % 2 == 1:
                shade_cell(cell, ZEBRA_FILL)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def render_image(doc: Document, alt: str, rel: str) -> None:
    img_path = (MD_PATH.parent / rel).resolve()
    if not img_path.exists():
        print(f"  ⚠ 图片缺失，跳过：{rel}")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(3)
    p.add_run().add_picture(str(img_path), width=Cm(15.2))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(10)
    r = cap.add_run(alt)
    set_run_font(r, cn=FONT_CN_HEAD, size=9, color=COLOR_GRAY)


# ----------------------------------------------------------------------
# Markdown 解析主循环
# ----------------------------------------------------------------------
def convert() -> None:
    lines = MD_PATH.read_text(encoding="utf-8").splitlines()
    doc = Document()

    # 页面设置：A4 + 2.4cm 页边距
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2.2)
    sec.left_margin = sec.right_margin = Cm(2.4)
    add_page_number_footer(sec)

    # Normal 样式基线
    normal = doc.styles["Normal"]
    normal.font.name = FONT_EN
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN_BODY)

    i = 0
    in_code = False
    code_buf: list[str] = []
    title_done = False

    while i < len(lines):
        line = lines[i].rstrip()

        # 代码块
        if line.startswith("```"):
            if in_code:
                render_code_block(doc, code_buf)
                code_buf, in_code = [], False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # 空行 / 分隔线
        if not line.strip():
            i += 1
            continue
        if line.strip() in ("---", "***"):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(4)
            ppr = p._p.get_or_add_pPr()
            pbdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "6")
            bottom.set(qn("w:space"), "1")
            bottom.set(qn("w:color"), "C9D6EA")
            pbdr.append(bottom)
            ppr.append(pbdr)
            i += 1
            continue

        # 标题
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            render_heading(doc, m.group(2).strip(), level)
            if level == 1 and not title_done:
                title_done = True
                sub = doc.add_paragraph()
                sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = sub.add_run("—— 基于多智能体协作流水线的自动化交付成果")
                set_run_font(r, cn=FONT_CN_HEAD, size=11, color=COLOR_GRAY)
                sub.paragraph_format.space_after = Pt(14)
            i += 1
            continue

        # 图片
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line)
        if m:
            render_image(doc, m.group(1), m.group(2))
            i += 1
            continue

        # 表格（连续以 | 开头的块）
        if line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            rows = []
            for row in block:
                if re.fullmatch(r"\|[\s:\-\|]+\|", row):   # 分隔行
                    continue
                cells = [c.strip() for c in row.strip("|").split("|")]
                rows.append(cells)
            if rows:
                render_table(doc, rows)
            continue

        # 引用块（连续以 > 开头）
        if line.startswith(">"):
            block = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(lines[i].strip().lstrip(">").strip())
                i += 1
            # 去掉分隔线
            block = [b for b in block if b and b not in ("---", "***")]
            render_quote(doc, block)
            continue

        # 列表
        if re.match(r"^[-*]\s+", line) or re.match(r"^\d+\.\s+", line):
            items = []
            while i < len(lines):
                cur = lines[i].rstrip()
                mo = re.match(r"^[-*]\s+(.*)$", cur)
                mn = re.match(r"^(\d+)\.\s+(.*)$", cur)
                indented = cur.startswith("   ") and items
                if mo:
                    items.append(("•", mo.group(1)))
                elif mn:
                    items.append((f"{mn.group(1)}.", mn.group(2)))
                elif indented:
                    # 续行并入上一条
                    marker, text = items[-1]
                    items[-1] = (marker, text + cur.strip())
                else:
                    break
                i += 1
            render_list(doc, items)
            continue

        # 普通段落
        render_paragraph(doc, line.strip())
        i += 1

    if code_buf:
        render_code_block(doc, code_buf)

    # 文档属性
    doc.core_properties.title = "2024—2025 区域零售销售数据分析报告"
    doc.core_properties.author = "Reporter (多智能体协作流水线 R001)"
    doc.core_properties.subject = "多智能体协作与 AgentOps 课程实践交付物"

    DOCX_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.save(DOCX_PATH)
    size_kb = DOCX_PATH.stat().st_size / 1024
    print(f"已导出 Word：{DOCX_PATH.relative_to(BASE_DIR)}（{size_kb:.0f} KB）")


if __name__ == "__main__":
    convert()
