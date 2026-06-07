
"""
file: all_type_chunker.py

Generic, file-type-aware chunker for Databricks volumes.
Supports: .pdf, .csv, .docx, .txt

All chunkers return: list[dict] with keys
    {document_id, chunk_id, chunk_text, page_number}
(page_number is None for non-PDF formats)
"""
from io import BytesIO
from pathlib import Path
import fitz
import pymupdf
import pandas as pd
from docx import Document
from databricks.sdk import WorkspaceClient
from langchain_text_splitters import RecursiveCharacterTextSplitter


_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
    separators=["\n\n", "\n", ". ", " "],
)


def _read_bytes(path: str) -> bytes:
    w = WorkspaceClient()
    return w.files.download(path).contents.read()


def _chunk_pdf(data: bytes, document_id: str) -> list[dict]:
    doc = fitz.open(stream=data, filetype="pdf")
    out, chunk_id = [], 0
    for page_num, page in enumerate(doc, start=1):
        for piece in _splitter.split_text(page.get_text() or ""):
            out.append({
                "document_id": document_id,
                "chunk_id": chunk_id,
                "chunk_text": piece,
                "page_number": page_num,
            })
            chunk_id += 1
    doc.close()
    return out


def _chunk_csv(data: bytes, document_id: str) -> list[dict]:
    df = pd.read_csv(BytesIO(data))
    out = []
    for row_num, row in enumerate(df.to_dict(orient="records")):
        text = " | ".join(f"{k}: {v}" for k, v in row.items())
        out.append({
            "document_id": document_id,
            "chunk_id": row_num,
            "chunk_text": text,
            "page_number": None,
        })
    return out


def _chunk_docx(data: bytes, document_id: str) -> list[dict]:
    doc = Document(BytesIO(data))
    text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [
        {
            "document_id": document_id,
            "chunk_id": i,
            "chunk_text": piece,
            "page_number": None,
        }
        for i, piece in enumerate(_splitter.split_text(text))
    ]


def _chunk_txt(data: bytes, document_id: str) -> list[dict]:
    text = data.decode("utf-8", errors="replace")
    return [
        {
            "document_id": document_id,
            "chunk_id": i,
            "chunk_text": piece,
            "page_number": None,
        }
        for i, piece in enumerate(_splitter.split_text(text))
    ]


_DISPATCH = {
    ".pdf": _chunk_pdf,
    ".csv": _chunk_csv,
    ".docx": _chunk_docx,
    ".txt": _chunk_txt,
}


def chunk_file(path: str, document_id: str | None = None) -> list[dict]:
    ext = Path(path).suffix.lower()
    if ext not in _DISPATCH:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {list(_DISPATCH)}")
    document_id = document_id or Path(path).stem
    data = _read_bytes(path)
    return _DISPATCH[ext](data, document_id)