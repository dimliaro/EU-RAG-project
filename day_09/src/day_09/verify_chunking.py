"""
Verification script — sanity-checks the smart chunker on real documents.

Run:
    cd day_09/
    uv run python -m day_09.verify_chunking

Expected results for GDPR (Regulation (EU) 2016/679):
    ~173 recitals,  ~99 articles.
If recitals >> 200 the "(N)" anchoring is wrong and splitting mid-sentence.
"""

from pathlib import Path

from day_09.config import CHUNK_OVERLAP, CHUNK_SIZE, DATA_DIR, MAX_ARTICLE_CHARS
from day_09.core.smart_chunker import detect_document_kind, route_and_chunk
from day_09.ingestion.local_loader import extract_pages


# ── helpers ───────────────────────────────────────────────────────────────────

def _preview(text: str, n: int = 120) -> str:
    return text[:n].replace("\n", " ") + ("…" if len(text) > n else "")


# ── regulation test ───────────────────────────────────────────────────────────

def verify_regulation(path: Path) -> None:
    print(f"\n{'=' * 64}")
    print(f"REGULATION:  {path.name}")
    print("=" * 64)

    pages     = extract_pages(str(path))
    full_text = "\n\n".join(p["text"] for p in pages)
    kind      = detect_document_kind(full_text)

    print(f"Detected kind : {kind}")
    assert kind == "eu_regulation", f"Expected eu_regulation, got {kind}"

    chunks   = route_and_chunk(
        pages=pages,
        source_file=str(path),
        chunk_size=CHUNK_SIZE,
        overlap=CHUNK_OVERLAP,
        max_article_chars=MAX_ARTICLE_CHARS,
    )
    recitals = [c for c in chunks if c["structure_type"] == "recital"]
    articles = [c for c in chunks if c["structure_type"] == "article"]

    print(f"\nTotal chunks  : {len(chunks)}")
    print(f"Recitals      : {len(recitals)}")
    print(f"Articles      : {len(articles)}")

    if len(recitals) > 250:
        print("\n⚠  WARNING: recital count suspiciously high — check the "(N)" regex!")

    print("\n── First 3 recitals ─────────────────────────────────────────")
    for r in recitals[:3]:
        print(f"  ({r['number']})  {_preview(r['content'])}")

    print("\n── Last 3 recitals ──────────────────────────────────────────")
    for r in recitals[-3:]:
        print(f"  ({r['number']})  {_preview(r['content'])}")

    print("\n── First 3 articles (with metadata) ────────────────────────")
    seen: set[int] = set()
    shown = 0
    for a in articles:
        if a["number"] not in seen:
            seen.add(a["number"])
            print(
                f"\n  Article {a['number']}"
                f"  |  chapter={a['chapter']!r}"
                f"  |  title={a['title']!r}"
                f"\n  regulation={a['regulation']!r}"
                f"\n  {_preview(a['content'])}"
            )
            shown += 1
            if shown >= 3:
                break


# ── generic test ──────────────────────────────────────────────────────────────

def verify_generic(path: Path) -> None:
    print(f"\n{'=' * 64}")
    print(f"GENERIC:  {path.name}")
    print("=" * 64)

    pages     = extract_pages(str(path))
    full_text = "\n\n".join(p["text"] for p in pages)
    kind      = detect_document_kind(full_text)

    print(f"Detected kind : {kind}")
    assert kind == "generic", f"Expected generic, got {kind}"

    chunks = route_and_chunk(
        pages=pages,
        source_file=str(path),
        chunk_size=CHUNK_SIZE,
        overlap=CHUNK_OVERLAP,
    )
    print(f"Total chunks  : {len(chunks)}")
    print(f"doc_kind set  : {set(c['doc_kind'] for c in chunks)}")

    print("\n── First 3 chunks ───────────────────────────────────────────")
    for c in chunks[:3]:
        print(f"  chunk_index={c['chunk_index']}  doc_kind={c['doc_kind']!r}")
        print(f"  {_preview(c['content'])}")


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    gdpr_path = DATA_DIR / "32016R0679_EN.pdf"
    csv_path  = DATA_DIR / "2020-2021.csv"

    if gdpr_path.exists():
        verify_regulation(gdpr_path)
        print(f"\n  ✓  GDPR: expect ~173 recitals and ~99 articles.")
    else:
        print(f"⚠  GDPR PDF not found at {gdpr_path}")

    if csv_path.exists():
        verify_generic(csv_path)
        print(f"\n  ✓  Generic fallback confirmed.")
    else:
        print(f"⚠  Generic test file not found at {csv_path}")

    print("\n✓  Verification done.\n")
