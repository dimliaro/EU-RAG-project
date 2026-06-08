"""
Extracts text from PDF, DOCX, TXT, CSV, and HTML files into a uniform list of page dicts:
  {"source_file": str, "page_number": int, "text": str}

For PDFs each page is one entry; for other formats entries are logical units
(paragraphs / rows / sections) numbered sequentially.
"""

import csv
from pathlib import Path

try:
    import pymupdf as fitz  # PyMuPDF >= 1.24
except ImportError:
    import fitz
from bs4 import BeautifulSoup
from docx import Document


def _extract_pdf(file_path: str) -> list[dict]:
    doc = fitz.open(file_path)
    chunks = []
    for page_number, page in enumerate(doc, start=1):
        text = page.get_text("text")
        if text and text.strip():
            chunks.append({"source_file": file_path, "page_number": page_number, "text": text.strip()})
    return chunks


def _extract_docx(file_path: str) -> list[dict]:
    doc = Document(file_path)
    chunks = []
    chunk_number = 1
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            chunks.append({"source_file": file_path, "page_number": chunk_number, "text": text})
            chunk_number += 1
    return chunks


def _extract_txt(file_path: str) -> list[dict]:
    text = Path(file_path).read_text(encoding="utf-8", errors="replace")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return [
        {"source_file": file_path, "page_number": i, "text": p}
        for i, p in enumerate(paragraphs, start=1)
    ]


def _extract_csv(file_path: str) -> list[dict]:
    chunks = []
    with open(file_path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            text = "  |  ".join(f"{k}: {v}" for k, v in row.items() if v)
            if text:
                chunks.append({"source_file": file_path, "page_number": i, "text": text})
    return chunks


def _extract_html(file_path: str) -> list[dict]:
    raw = Path(file_path).read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "head"]):
        tag.decompose()
    paragraphs = [t.get_text(" ", strip=True) for t in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6"]) if t.get_text(strip=True)]
    if not paragraphs:
        body = soup.get_text("\n")
        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    return [
        {"source_file": file_path, "page_number": i, "text": p}
        for i, p in enumerate(paragraphs, start=1)
    ]


_EXTRACTORS = {
    ".pdf":  _extract_pdf,
    ".docx": _extract_docx,
    ".txt":  _extract_txt,
    ".csv":  _extract_csv,
    ".html": _extract_html,
    ".htm":  _extract_html,
}


def extract_pages(file_path: str) -> list[dict[str, str | int]]:
    """Route extraction to the correct handler based on file extension."""
    suffix = Path(file_path).suffix.lower()
    extractor = _EXTRACTORS.get(suffix)
    if extractor is None:
        raise ValueError(f"Unsupported file type '{suffix}'. Supported: {list(_EXTRACTORS)}")
    return extractor(file_path)


# Backward-compatible alias
def extract_pdf_pages(pdf_path: str) -> list[dict[str, str | int]]:
    return _extract_pdf(pdf_path)
