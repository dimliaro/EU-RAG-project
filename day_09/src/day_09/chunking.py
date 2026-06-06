"""
file: chunking.py
Paragraph-aware chunking: splits on natural paragraph breaks first, then
word-splits only paragraphs that exceed chunk_size. Overlap is applied by
carrying the tail of the previous chunk into the next one.
"""
from hashlib import sha256


def _word_count(text: str) -> int:
    return len(text.split())


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    # Split any paragraph that exceeds chunk_size into word-count sub-chunks
    segments: list[str] = []
    for para in paragraphs:
        words = para.split()
        if len(words) <= chunk_size:
            segments.append(para)
        else:
            start = 0
            while start < len(words):
                segments.append(" ".join(words[start : start + chunk_size]))
                start += chunk_size - overlap

    # Merge short segments up to chunk_size, then apply overlap between chunks
    chunks: list[str] = []
    current_words: list[str] = []

    for seg in segments:
        seg_words = seg.split()
        if current_words and _word_count(" ".join(current_words)) + len(seg_words) > chunk_size:
            chunks.append(" ".join(current_words))
            # carry overlap tail into next chunk
            current_words = current_words[-overlap:] if overlap else []
        current_words.extend(seg_words)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


def create_chunks(pages: list[dict], chunk_size: int, overlap: int) -> list[dict[str, str | int]]:
    chunk_rows = []

    for page in pages:
        page_number = page["page_number"]
        source_file = page["source_file"]
        text = page["text"]

        chunks = chunk_text(text=text, chunk_size=chunk_size, overlap=overlap)

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
