"""Word and PDF reports for one screening result."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from fpdf import FPDF

from src.matcher import RequirementResult, ScreenResult


FONT_PATH = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "DejaVuSans.ttf"
DISCLAIMER = (
    "This score is evidence for a shortlist. It is not a hiring decision, "
    "and it is not a prediction of one employer's applicant tracking system."
)


def split_findings(result: ScreenResult) -> dict[str, list[RequirementResult]]:
    supported: list[RequirementResult] = []
    gaps: list[RequirementResult] = []
    preferred: list[RequirementResult] = []
    for item in result.results:
        if item.priority == "required" and item.status == "met" and not item.advice:
            supported.append(item)
        elif item.priority == "required":
            gaps.append(item)
        elif item.status != "met":
            preferred.append(item)
    return {"supported": supported, "gaps": gaps, "preferred": preferred}


def build_docx(result: ScreenResult) -> bytes:
    document = Document()
    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor(0x1C, 0x24, 0x30)

    _heading(document, "CV screening report", 0)
    document.add_paragraph(result.verdict)
    lead = result.summary.split(" What is missing")[0].strip()
    document.add_paragraph(lead or result.summary)

    preferred = (
        f"{result.preferred_met} of {result.preferred_total}"
        if result.preferred_total
        else "None listed"
    )
    document.add_paragraph(
        f"ATS score: {result.fit_score}%. "
        f"Required skills supported: {result.required_met} of {result.required_total}. "
        f"Preferred items supported: {preferred}."
    )

    findings = split_findings(result)
    _item_section(
        document,
        "Supported",
        findings["supported"],
        empty="No required item is fully supported.",
        with_advice=False,
    )
    _item_section(
        document,
        "Missing, and what to add",
        findings["gaps"],
        empty="Nothing required is missing.",
        with_advice=True,
    )
    if findings["preferred"]:
        _item_section(
            document,
            "Preferred items still open",
            findings["preferred"],
            empty="",
            with_advice=True,
        )

    _heading(document, "Line by line", 1)
    if result.results:
        table = document.add_table(rows=1, cols=4)
        table.style = "Table Grid"
        headers = ("Requirement", "Result", "Evidence from the CV", "What to add")
        for cell, title in zip(table.rows[0].cells, headers):
            cell.text = title
            _shade(cell, "0E6B5C")
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                    run.font.size = Pt(10)
        for item in result.results:
            row = table.add_row().cells
            values = (
                f"{item.text} ({item.priority})",
                f"{item.status}; {item.match_type}",
                item.evidence or "—",
                item.advice or "—",
            )
            for cell, value in zip(row, values):
                cell.text = value
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(10)
        for column, width in zip(table.columns, (2.0, 1.3, 2.2, 1.8)):
            for cell in column.cells:
                cell.width = Inches(width)
    else:
        document.add_paragraph("No requirements could be checked.")

    profile = result.profile
    if profile is not None:
        _heading(document, "What was read from the CV", 1)
        sections = ", ".join(profile.sections) if profile.sections else "No section headings found"
        document.add_paragraph(f"Words read: {profile.word_count}")
        document.add_paragraph(f"Sections: {sections}")
        if profile.email:
            document.add_paragraph(f"Email found: {profile.email}")
        if profile.years_experience is not None:
            document.add_paragraph(
                f"Employment dates add up to about {profile.years_experience} years."
            )

    note = document.add_paragraph(DISCLAIMER)
    for run in note.runs:
        run.italic = True
        run.font.color.rgb = RGBColor(0x3E, 0x4C, 0x59)

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def build_pdf(result: ScreenResult) -> bytes:
    if not FONT_PATH.is_file():
        raise FileNotFoundError(f"Report font is missing: {FONT_PATH}")

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_font("DejaVu", "", str(FONT_PATH))
    pdf.add_page()
    pdf.set_margins(16, 16, 16)

    _pdf_line(pdf, "CV screening report", size=18, gap=9, color=(20, 32, 43))
    _pdf_line(pdf, result.verdict, size=13, gap=7, color=(14, 107, 92))
    lead = result.summary.split(" What is missing")[0].strip()
    _pdf_line(pdf, lead or result.summary, size=11)

    preferred = (
        f"{result.preferred_met} of {result.preferred_total}"
        if result.preferred_total
        else "None listed"
    )
    _pdf_line(
        pdf,
        f"ATS score: {result.fit_score}%\n"
        f"Required skills supported: {result.required_met} of {result.required_total}\n"
        f"Preferred items supported: {preferred}",
        size=11,
    )

    findings = split_findings(result)
    _pdf_items(pdf, "Supported", findings["supported"], "No required item is fully supported.", False)
    _pdf_items(pdf, "Missing, and what to add", findings["gaps"], "Nothing required is missing.", True)
    if findings["preferred"]:
        _pdf_items(pdf, "Preferred items still open", findings["preferred"], "", True)

    _pdf_line(pdf, "Line by line", size=14, gap=8, color=(20, 32, 43))
    if not result.results:
        _pdf_line(pdf, "No requirements could be checked.")
    for item in result.results:
        _pdf_line(pdf, item.text, size=11, gap=5, color=(20, 32, 43))
        _pdf_line(
            pdf,
            f"{item.priority} · {item.status} · {item.match_type}",
            size=9,
            gap=4,
            color=(92, 107, 115),
        )
        if item.evidence:
            _pdf_line(pdf, f"Evidence: {item.evidence}", size=10, gap=5)
        if item.advice:
            _pdf_line(pdf, f"Add: {item.advice}", size=10, gap=5)
        pdf.ln(1)

    profile = result.profile
    if profile is not None:
        _pdf_line(pdf, "What was read from the CV", size=14, gap=8, color=(20, 32, 43))
        sections = ", ".join(profile.sections) if profile.sections else "No section headings found"
        _pdf_line(pdf, f"Words read: {profile.word_count}", size=11)
        _pdf_line(pdf, f"Sections: {sections}", size=11)
        if profile.email:
            _pdf_line(pdf, f"Email found: {profile.email}", size=11)
        if profile.years_experience is not None:
            _pdf_line(
                pdf,
                f"Employment dates add up to about {profile.years_experience} years.",
                size=11,
            )

    pdf.ln(2)
    _pdf_line(pdf, DISCLAIMER, size=9, gap=5, color=(62, 76, 89))
    return bytes(pdf.output())


def _heading(document: Document, text: str, level: int):
    paragraph = document.add_heading(text, level=level)
    for run in paragraph.runs:
        run.font.color.rgb = RGBColor(0x14, 0x20, 0x2B)
    return paragraph


def _item_section(document, title, items, empty: str, with_advice: bool) -> None:
    _heading(document, title, 1)
    if not items:
        if empty:
            document.add_paragraph(empty)
        return
    for item in items:
        paragraph = document.add_paragraph()
        run = paragraph.add_run(item.text)
        run.bold = True
        if item.evidence:
            document.add_paragraph(item.evidence)
        if with_advice:
            document.add_paragraph(item.advice or "Add a line that shows this.")


def _shade(cell, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    shading.set(qn("w:val"), "clear")
    properties.append(shading)


def _pdf_line(pdf: FPDF, text: str, size: int = 11, gap: float = 6, color=(28, 36, 48)) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("DejaVu", size=size)
    pdf.set_text_color(*color)
    pdf.multi_cell(0, gap, _pdf_safe(text))


def _pdf_items(pdf, title, items, empty: str, with_advice: bool) -> None:
    _pdf_line(pdf, title, size=14, gap=8, color=(20, 32, 43))
    if not items:
        if empty:
            _pdf_line(pdf, empty)
        return
    for item in items:
        _pdf_line(pdf, item.text, size=11, gap=5, color=(20, 32, 43))
        if item.evidence:
            _pdf_line(pdf, item.evidence, size=10, gap=5, color=(62, 76, 89))
        if with_advice:
            _pdf_line(
                pdf,
                item.advice or "Add a line that shows this.",
                size=10,
                gap=5,
            )
        pdf.ln(1)


def _pdf_safe(text: str) -> str:
    cleaned = (text or "").replace("\u00a0", " ").replace("\t", " ")
    # DejaVu covers the letters this report uses. Drop anything outside it
    # so one unusual character cannot stop the file from being built.
    kept = []
    for char in cleaned:
        if char == "\n" or ord(char) >= 32:
            kept.append(char)
    return "".join(kept)
