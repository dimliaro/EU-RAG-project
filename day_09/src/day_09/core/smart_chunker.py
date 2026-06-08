"""
smart_chunker.py — chunking router for the EU regulatory-compliance RAG pipeline.

Two-layer design (matches the project's LOADER / CHUNKER separation):
  LOADER layer  — ingestion/local_loader.py   (untouched here)
  CHUNKER layer — this file: given extracted pages, decide HOW to chunk.

Entry point:
  route_and_chunk(pages, source_file, chunk_size, overlap, max_article_chars)
      -> list[dict]   (same schema as create_chunks, plus extra metadata fields)
"""

import re
from hashlib import sha256
from pathlib import Path


# ── Detection regexes (compiled once at import time) ──────────────────────────

# Signal 1: every EU regulation contains this adoption phrase
_ADOPTION_RE = re.compile(r"have adopted this regulation", re.IGNORECASE)

# Signal 2: recital markers "(N)" at line start, N = PURE DIGITS ONLY.
# The \d+ with immediate ) means "(2016/679)" won't match ("2016/679" ≠ pure \d+)
# and "(a)" won't match ("a" ≠ \d+).
_RECITAL_DETECT_RE = re.compile(r"(?m)^\((\d+)\)\s")

# Signal 3: "Article N" at line start (at least several = structured document)
_ARTICLE_DETECT_RE = re.compile(r"(?m)^Article\s+(\d+)\b", re.IGNORECASE)

# Splits the document at the adoption marker into recitals / articles sections
_ADOPTION_SPLIT_RE = re.compile(r"HAVE ADOPTED THIS REGULATION\s*:?", re.IGNORECASE)

# Chapter headings use Roman numerals in EU regulations: "CHAPTER I", "CHAPTER IV"
_CHAPTER_RE = re.compile(r"(?m)^CHAPTER\s+[IVXLCDM\d]+\b.*")

# Numbered paragraph markers inside articles: "1.", "2." strictly at line start
_PARA_RE = re.compile(r"(?m)^\d+\.\s")

# Letter sub-points inside numbered paragraphs: "(a)", "(b)", "(c)" at line start
# Excludes "(EU)", "(EC)" etc. because those never appear at strict line start in body text
_SUBPOINT_RE = re.compile(r"(?m)^\([a-z]\)\s")


# ── Detection ─────────────────────────────────────────────────────────────────

def detect_document_kind(text: str) -> str:
    """
    Returns "eu_regulation" when at least 2 of 3 content signals are present.
    Requiring two signals avoids false positives on documents that happen to
    contain "Article" headings or numbered lists but are not EU regulations.
    """
    signals = 0

    if _ADOPTION_RE.search(text):
        signals += 1

    # Need >= 3 recitals starting from a low number (not random page references)
    recital_nums = {int(m.group(1)) for m in _RECITAL_DETECT_RE.finditer(text)}
    if len(recital_nums) >= 3 and min(recital_nums) <= 3:
        signals += 1

    article_nums = {int(m.group(1)) for m in _ARTICLE_DETECT_RE.finditer(text)}
    if len(article_nums) >= 3:
        signals += 1

    return "eu_regulation" if signals >= 2 else "generic"


# ── Regulation identity ────────────────────────────────────────────────────────

def _extract_regulation_id(text: str, source_file: str) -> str:
    """
    Generic extraction: look for "Regulation (EU) YYYY/NNNN" or
    "Regulation (EU) No NNNN/YYYY" in the document header (first 3 000 chars).
    Falls back to the filename stem so every chunk always has a regulation label.
    """
    m = re.search(
        r"Regulation\s+\(EU\)\s+(?:No\s+)?\d+/\d+",
        text[:3000],
        re.IGNORECASE,
    )
    return m.group(0).strip() if m else Path(source_file).stem


# ── Recital parsing ───────────────────────────────────────────────────────────

# Same regex as _RECITAL_DETECT_RE but with a capture group for the number.
_RECITAL_BOUNDARY_RE = re.compile(r"(?m)^\((\d+)\)\s")


def _parse_recitals(
    recitals_text: str,
    regulation: str,
    source_file: str,
    max_recital_chars: int = 2000,
) -> list[dict]:
    """
    Split recitals_text at every "(N) " marker that appears at a LINE START.

    Critical anchoring ((?m)^):
      "(1) The..." at line start          → boundary  ✓
      "(a) subject to..."                 → skipped   ✓  (\d+ fails on 'a')
      "(EU) 2016/679"                     → skipped   ✓  (\d+ fails on 'EU')
      "(2016/679)" cross-reference        → skipped   ✓  ('2016/679' ≠ \d+\))
      "(3)" appearing mid-sentence        → skipped   ✓  (^ requires line start)

    Recitals that exceed max_recital_chars are sub-split with the generic
    word-count chunker so a single very long recital never becomes a wall-of-text
    chunk that hurts retrieval quality.
    """
    from day_09.core.chunking import chunk_text

    boundaries = [
        (m.start(), int(m.group(1)))
        for m in _RECITAL_BOUNDARY_RE.finditer(recitals_text)
    ]

    chunks = []
    global_i = 0
    for i, (start, number) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(recitals_text)
        content = recitals_text[start:end].strip()
        if not content:
            continue

        if len(content) <= max_recital_chars:
            chunk_id = sha256(f"{source_file}|recital|{number}|{content}".encode()).hexdigest()
            chunks.append({
                "chunk_id":       chunk_id,
                "source_file":    source_file,
                "content":        content,
                "page_number":    0,
                "chunk_index":    global_i,
                "doc_kind":       "eu_regulation",
                "structure_type": "recital",
                "number":         number,
                "chapter":        "",
                "title":          "",
                "regulation":     regulation,
            })
            global_i += 1
        else:
            # Oversized recital: apply word-count chunking, keep recital metadata
            word_chunks = chunk_text(content, chunk_size=400, overlap=50)
            for sub_idx, wc in enumerate(word_chunks):
                chunk_id = sha256(f"{source_file}|recital|{number}|{sub_idx}|{wc}".encode()).hexdigest()
                chunks.append({
                    "chunk_id":       chunk_id,
                    "source_file":    source_file,
                    "content":        wc,
                    "page_number":    0,
                    "chunk_index":    global_i,
                    "doc_kind":       "eu_regulation",
                    "structure_type": "recital",
                    "number":         number,
                    "chapter":        "",
                    "title":          "",
                    "regulation":     regulation,
                })
                global_i += 1

    return chunks


# ── Article parsing ───────────────────────────────────────────────────────────

_ARTICLE_BOUNDARY_RE = re.compile(r"(?m)^Article\s+(\d+)\b", re.IGNORECASE)


def _article_title(article_text: str) -> str:
    """
    The article title is the first non-empty line after the 'Article N' header
    that does not look like a numbered paragraph opener ("1.", "2.", ...).
    Returns "" if no distinct title line is found.
    """
    lines = [l.strip() for l in article_text.split("\n") if l.strip()]
    # lines[0] == "Article N" — skip it
    if len(lines) > 1:
        candidate = lines[1]
        # Reject if it starts a numbered paragraph or is suspiciously long
        if not re.match(r"^\d+\.", candidate) and len(candidate) < 200:
            return candidate
    return ""


def _sub_split_article(
    article_text: str,
    art_num: int,
    chapter: str,
    title: str,
    regulation: str,
    source_file: str,
    max_chars: int = 2000,
) -> list[dict]:
    """
    Three-level sub-split for oversized articles — preserves legal structure.

    Level 1  numbered paragraphs  "1.", "2.", …       (strict line-start)
    Level 2  letter sub-points    "(a)", "(b)", …     (only when L1 piece > max_chars)
    Level 3  word-count fallback                      (only when L2 also exceeds max_chars)

    The article header (everything before the first "1.") is prepended to every
    sub-chunk so that retrieval never loses the "Article N / Title" context.
    """
    from day_09.core.chunking import chunk_text

    sub_idx = 0

    def _make_chunk(content: str) -> dict:
        nonlocal sub_idx
        chunk_id = sha256(f"{source_file}|article|{art_num}|{sub_idx}|{content}".encode()).hexdigest()
        chunk = {
            "chunk_id":       chunk_id,
            "source_file":    source_file,
            "content":        content,
            "page_number":    0,
            "chunk_index":    sub_idx,
            "doc_kind":       "eu_regulation",
            "structure_type": "article",
            "number":         art_num,
            "chapter":        chapter,
            "title":          title,
            "regulation":     regulation,
        }
        sub_idx += 1
        return chunk

    def _emit(content: str, result: list) -> None:
        """Emit one content string, applying word-count fallback if still too large."""
        if len(content) <= max_chars:
            result.append(_make_chunk(content))
        else:
            for wc in chunk_text(content, chunk_size=400, overlap=50):
                result.append(_make_chunk(wc))

    # Extract the header block: "Article N\nTitle\n" before the first "1."
    first_para = _PARA_RE.search(article_text)
    header = article_text[:first_para.start()].rstrip() if first_para else ""
    para_matches = list(_PARA_RE.finditer(article_text))

    if not para_matches:
        # No numbered paragraphs at all — keep whole article as one chunk
        result: list[dict] = []
        _emit(article_text.strip(), result)
        return result

    result = []
    for j, para_match in enumerate(para_matches):
        para_start = para_match.start()
        para_end   = para_matches[j + 1].start() if j + 1 < len(para_matches) else len(article_text)
        para_text  = article_text[para_start:para_end].strip()
        if not para_text:
            continue

        # Always prepend the article header for retrieval context
        full = f"{header}\n{para_text}".strip() if header else para_text

        if len(full) <= max_chars:
            result.append(_make_chunk(full))
            continue

        # Level 2: try letter sub-points "(a)", "(b)", …
        sp_matches = list(_SUBPOINT_RE.finditer(para_text))
        if sp_matches:
            # The intro line of the paragraph before the first sub-point
            para_intro = para_text[: sp_matches[0].start()].strip()
            for k, sp_match in enumerate(sp_matches):
                sp_start = sp_match.start()
                sp_end   = sp_matches[k + 1].start() if k + 1 < len(sp_matches) else len(para_text)
                sp_text  = para_text[sp_start:sp_end].strip()
                parts    = [p for p in (header, para_intro, sp_text) if p]
                _emit("\n".join(parts), result)
        else:
            # No sub-points — word-count fallback (Level 3)
            _emit(full, result)

    return result


def _parse_articles(
    articles_text: str,
    regulation: str,
    source_file: str,
    max_article_chars: int,
) -> list[dict]:
    """
    One chunk per Article; track CHAPTER headings as they appear.
    Articles exceeding max_article_chars are sub-split by numbered paragraphs.
    """
    article_matches = list(_ARTICLE_BOUNDARY_RE.finditer(articles_text))
    # Collect chapter markers with their text position
    chapter_markers = [
        (m.start(), m.group(0).strip())
        for m in _CHAPTER_RE.finditer(articles_text)
    ]

    chunks: list[dict] = []

    for i, art_match in enumerate(article_matches):
        art_start = art_match.start()
        art_num   = int(art_match.group(1))
        art_end   = article_matches[i + 1].start() if i + 1 < len(article_matches) else len(articles_text)
        article_text = articles_text[art_start:art_end].strip()

        # The active chapter is the last chapter heading that comes before this article
        chapter = ""
        for ch_pos, ch_name in chapter_markers:
            if ch_pos <= art_start:
                chapter = ch_name

        title = _article_title(article_text)

        if len(article_text) > max_article_chars:
            sub = _sub_split_article(article_text, art_num, chapter, title, regulation, source_file, max_chars=max_article_chars)
            chunks.extend(sub)
        else:
            chunk_id = sha256(f"{source_file}|article|{art_num}|{article_text}".encode()).hexdigest()
            chunks.append({
                "chunk_id":       chunk_id,
                "source_file":    source_file,
                "content":        article_text,
                "page_number":    0,
                "chunk_index":    0,    # re-indexed globally later
                "doc_kind":       "eu_regulation",
                "structure_type": "article",
                "number":         art_num,
                "chapter":        chapter,
                "title":          title,
                "regulation":     regulation,
            })

    return chunks


# ── Regulation chunker ────────────────────────────────────────────────────────

def chunk_regulation(text: str, source_file: str, max_article_chars: int) -> list[dict]:
    """
    Structure-aware chunking for EU regulations.

    1. Extract the regulation identity from the header.
    2. Split at "HAVE ADOPTED THIS REGULATION" into recitals / articles sections.
    3. Parse recitals (one chunk per recital number).
    4. Parse articles (one chunk per article; sub-split if oversized).
    5. Re-index chunk_index globally so it is unique across both lists.
    """
    regulation = _extract_regulation_id(text, source_file)

    split = _ADOPTION_SPLIT_RE.search(text)
    if split:
        recitals_text = text[: split.start()]
        articles_text = text[split.end() :]
    else:
        # Fallback when the adoption marker is missing or oddly formatted
        art1 = re.search(r"(?m)^Article\s+1\b", text, re.IGNORECASE)
        recitals_text = text[: art1.start()] if art1 else ""
        articles_text = text[art1.start() :] if art1 else text

    recital_chunks = _parse_recitals(recitals_text, regulation, source_file, max_recital_chars=max_article_chars)
    article_chunks = _parse_articles(articles_text, regulation, source_file, max_article_chars)

    all_chunks = recital_chunks + article_chunks
    # Assign globally unique, sequential chunk_index
    for i, chunk in enumerate(all_chunks):
        chunk["chunk_index"] = i

    return all_chunks


# ── Generic chunker ────────────────────────────────────────────────────────────

def chunk_generic(
    pages: list[dict],
    source_file: str,
    chunk_size: int,
    overlap: int,
) -> list[dict]:
    """
    Reuses the existing paragraph-aware splitter (core/chunking.py).
    Adds the unified metadata fields so generic and regulation chunks share
    the same schema in the vector store — enabling consistent metadata filtering.
    """
    from day_09.core.chunking import create_chunks

    chunks = create_chunks(pages=pages, chunk_size=chunk_size, overlap=overlap)
    for chunk in chunks:
        chunk["doc_kind"]       = "generic"
        chunk["structure_type"] = ""
        chunk["number"]         = 0
        chunk["chapter"]        = ""
        chunk["title"]          = ""
        chunk["regulation"]     = ""
    return chunks


# ── Router ────────────────────────────────────────────────────────────────────

def route_and_chunk(
    pages: list[dict],
    source_file: str,
    chunk_size: int,
    overlap: int,
    max_article_chars: int = 3000,
) -> list[dict]:
    """
    Detects the document kind from the full text, then routes to the correct
    chunker.  All returned chunks share a common metadata schema so the vector
    store, retriever, and LLM context builder can handle both kinds uniformly.
    """
    full_text = "\n\n".join(page["text"] for page in pages)
    doc_kind  = detect_document_kind(full_text)

    if doc_kind == "eu_regulation":
        print(f"[smart_chunker] EU regulation detected — using structure-aware chunker.")
        return chunk_regulation(full_text, source_file, max_article_chars)

    print(f"[smart_chunker] Generic document — using paragraph-aware chunker.")
    return chunk_generic(pages, source_file, chunk_size, overlap)
