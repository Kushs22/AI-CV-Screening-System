"""The downloaded report contains the same score the screen shows."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from src.report import build_docx, build_pdf
from src.screen import screen_text


ROOT = Path(__file__).resolve().parents[1]


def test_word_and_pdf_reports_include_the_ats_score():
    cv = (ROOT / "data" / "samples" / "admin_cv.txt").read_text(encoding="utf-8")
    job = (ROOT / "data" / "job_descriptions" / "job_description.txt").read_text(encoding="utf-8")
    result = screen_text(cv, job)

    docx_bytes = build_docx(result)
    pdf_bytes = build_pdf(result)

    assert docx_bytes[:2] == b"PK"
    assert pdf_bytes.startswith(b"%PDF")

    document = Document(BytesIO(docx_bytes))
    word_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    for table in document.tables:
        for row in table.rows:
            word_text += "\n" + " ".join(cell.text for cell in row.cells)
    assert result.verdict in word_text
    assert f"{result.fit_score}" in word_text
    assert "ATS score" in word_text

    reader = PdfReader(BytesIO(pdf_bytes))
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert result.verdict in pdf_text
    assert "ATS score" in pdf_text
    assert str(result.fit_score) in pdf_text
