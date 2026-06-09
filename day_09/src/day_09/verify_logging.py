"""
Verification script for the query audit log.

Runs 4 real queries through the pipeline, then demonstrates:
  - recent(5)  → shows the Q&A audit trail with article/recital citations
  - search()   → keyword search over past queries
  - Confirms Chroma chunk count is unchanged (audit log never touches it)

Prerequisites: ChromaDB must already be populated (run the API server once first,
or run `uv run python -m day_09.verify_chunking` and the full ingest flow).

Run:
    cd day_09/
    uv run python -m day_09.verify_logging
"""

from day_09.config import (
    CHROMA_PATH,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    QUERY_LOG_DB,
    TOP_K,
    VOLUME_FILE_PATH,
)
from day_09.core.embeddings import LocalEmbeddingModel
from day_09.core.llm import AzureOpenAIChatLLM
from day_09.core.query_logger import SqliteQueryLogger
from day_09.core.rag_pipeline import RAGPipeline
from day_09.core.vector_store import ChromaVectorStore


QUESTIONS = [
    "What are the rights of data subjects under GDPR?",
    "What obligations does DORA impose on ICT service providers?",
    "How is personal data defined in the GDPR?",
    "What must happen in case of a personal data breach?",
]


def _sep(title: str = "") -> None:
    line = "─" * 64
    print(f"\n{line}")
    if title:
        print(f"  {title}")
        print(line)


def run() -> None:
    # ── Build pipeline ─────────────────────────────────────────────────────────
    logger          = SqliteQueryLogger(db_path=QUERY_LOG_DB)
    embedding_model = LocalEmbeddingModel(model_name=EMBEDDING_MODEL_NAME)
    vector_store    = ChromaVectorStore(persist_path=CHROMA_PATH, collection_name=COLLECTION_NAME)
    llm             = AzureOpenAIChatLLM()

    chroma_count_before = vector_store.collection.count()

    pipeline = RAGPipeline(
        file_path=VOLUME_FILE_PATH,
        embedding_model=embedding_model,
        vector_store=vector_store,
        llm=llm,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        top_k=TOP_K,
        logger=logger,
    )

    if chroma_count_before == 0:
        print("⚠  ChromaDB is empty — run the API server first to populate it.")
        print("   uv run uvicorn day_09.api.app:app --port 8080")
        return

    # ── Run queries ────────────────────────────────────────────────────────────
    _sep("Running 4 test queries through the pipeline")
    for q in QUESTIONS:
        print(f"\n  Q: {q}")
        result = pipeline.ask(q)
        # Print just the first 140 chars of the answer so output stays readable
        snippet = result["answer"].replace("\n", " ")[:140]
        print(f"  A: {snippet}…")

    # ── recent(5) — audit trail ────────────────────────────────────────────────
    _sep("recent(5) — 5 most recent Q&A records (newest first)")
    for rec in logger.recent(5):
        print(f"\n  [{rec['timestamp']}]  latency={rec['latency_ms']} ms")
        print(f"  Query  : {rec['query']}")
        ans_snip = rec["answer"].replace("\n", " ")[:120]
        print(f"  Answer : {ans_snip}…")
        citations = []
        for r in rec["retrieved"]:
            st  = r.get("structure_type", "") or "chunk"
            num = r.get("number") or ""
            reg = (r.get("regulation") or "")[:35]
            citations.append(f"{st} {num} [{reg}]".strip())
        print(f"  Grounded in: {citations}")

    # ── search("breach") ──────────────────────────────────────────────────────
    _sep('search("breach") — keyword match over past queries')
    matches = logger.search("breach")
    if matches:
        for m in matches:
            print(f"\n  [{m['timestamp']}]")
            print(f"  Query: {m['query']}")
    else:
        print("  No matches found for 'breach'.")

    # ── Chroma unchanged ───────────────────────────────────────────────────────
    _sep("Verifying Chroma vector store is untouched")
    chroma_count_after = vector_store.collection.count()
    status = "✓ unchanged" if chroma_count_after == chroma_count_before else "✗ CHANGED — BUG"
    print(f"\n  Chunks before: {chroma_count_before}")
    print(f"  Chunks after : {chroma_count_after}   {status}")

    print(f"\n  Audit log stored at: {QUERY_LOG_DB}\n")
    _sep("Verification complete")
    print()


if __name__ == "__main__":
    run()
