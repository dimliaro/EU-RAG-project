"""
file: chunking.py
This module provides functionality to chunk text extracted from PDF pages.


"""
from hashlib import sha256

#helper function to chunk text into smaller pieces with overlap
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    """
    Simple word-based chunking.

    Later you can replace this with:
    - token-based chunking
    - semantic chunking
    - structure-aware chunking
    """

    words = text.split()
    chunks = []

    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])

        if chunk.strip():
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def create_chunks(pages, chunk_size: int, overlap: int) -> list[dict[str, str | int]]:
    chunk_rows = []

    for page in pages:
        page_number = page["page_number"]
        source_file = page["source_file"]
        text = page["text"]

        chunks = chunk_text(
            text=text,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for chunk_index, chunk in enumerate(chunks):
            chunk_id = sha256(
                f"{source_file}|{page_number}|{chunk_index}|{chunk}".encode("utf-8")
            ).hexdigest()

            chunk_rows.append(
                {
                    "chunk_id": chunk_id,
                    "source_file": source_file,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "content": chunk,
                }
            )

    return chunk_rows