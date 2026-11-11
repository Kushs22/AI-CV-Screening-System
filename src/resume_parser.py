"""Read a CV from PDF, DOCX, or plain text.

Column detection is conservative. A right-aligned date is not treated as a
second column. Image-only PDFs come back empty so the scorer can say the
file could not be read, instead of inventing a low match.
"""

from __future__ import annotations

import re
from pathlib import Path


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _extract_pdf(path)
    elif suffix == ".docx":
        text = _extract_docx(path)
    elif suffix in {".txt", ".text", ".md"}:
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Upload a PDF, DOCX, or TXT CV."
        )
    return clean_text(text)


def extract_text_from_pdf(file_path: str) -> str:
    """Backward-compatible wrapper used by the original app."""
    return extract_text(file_path)


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\u00ad", "")
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("ﬀ", "ff")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_pdf(path: Path) -> str:
    text = ""
    try:
        text = _pdfplumber_text(path)
    except Exception:
        text = ""
    if len(text.strip()) < 40:
        fallback = _pypdf_text(path)
        if len(fallback.strip()) > len(text.strip()):
            text = fallback
    return text


def _pdfplumber_text(path: Path) -> str:
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pages.append(_page_text(page))
    return "\n".join(part for part in pages if part.strip())


def _page_text(page) -> str:
    try:
        words = page.extract_words(keep_blank_chars=False) or []
    except Exception:
        words = []
    if len(words) < 20:
        return page.extract_text() or ""
    split_at = _column_split(words)
    if split_at is None:
        return _words_to_lines(words)
    left = [word for word in words if word["x0"] < split_at]
    right = [word for word in words if word["x0"] >= split_at]
    if len(left) < 10 or len(right) < 10:
        return _words_to_lines(words)
    return _words_to_lines(left) + "\n" + _words_to_lines(right)


def _column_split(words: list[dict]) -> float | None:
    """Return an x position only when most lines share the same wide gap."""
    lines = _cluster_lines(words)
    gaps: list[float] = []
    for line in lines:
        ordered = sorted(line, key=lambda word: word["x0"])
        for left, right in zip(ordered, ordered[1:]):
            gap = right["x0"] - left["x1"]
            if gap > 70:
                gaps.append((left["x1"] + right["x0"]) / 2)
    if len(gaps) < max(4, int(len(lines) * 0.45)):
        return None
    median = sorted(gaps)[len(gaps) // 2]
    close = [gap for gap in gaps if abs(gap - median) < 40]
    if len(close) < max(4, int(len(lines) * 0.4)):
        return None
    return median


def _cluster_lines(words: list[dict]) -> list[list[dict]]:
    ordered = sorted(words, key=lambda word: (word["top"], word["x0"]))
    lines: list[list[dict]] = []
    current: list[dict] = []
    current_top: float | None = None
    for word in ordered:
        if current_top is None or abs(word["top"] - current_top) <= 3:
            current.append(word)
            if current_top is None:
                current_top = word["top"]
        else:
            lines.append(current)
            current = [word]
            current_top = word["top"]
    if current:
        lines.append(current)
    return lines


def _words_to_lines(words: list[dict]) -> str:
    lines = []
    for line in _cluster_lines(words):
        ordered = sorted(line, key=lambda word: word["x0"])
        lines.append(" ".join(word["text"] for word in ordered))
    return "\n".join(lines)


def _pypdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(parts)


def _extract_docx(path: Path) -> str:
    from docx import Document

    document = Document(str(path))
    parts: list[str] = []
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            parts.append(paragraph.text.strip())
    for table in document.tables:
        for row in table.rows:
            cells: list[str] = []
            for cell in row.cells:
                value = cell.text.strip()
                if value and (not cells or cells[-1] != value):
                    cells.append(value)
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)
