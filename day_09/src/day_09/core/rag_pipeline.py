"""
Orchestrates the full RAG pipeline in two modes:

LOCAL mode  (ingest / ask)
  file → extract → chunk → vector store → LLM

DATABRICKS mode  (ingest_databricks / ask_databricks)
  URL/file → fetch → upload to Volume → [bundle job runs spark_ingester]
           → Vector Search → LLM → results written to Delta table
"""

from __future__ import annotations

import time
import uuid
import warnings
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from day_09.ingestion.local_loader import extract_pages
from day_09.core.chunking import create_chunks
from day_09.core.smart_chunker import route_and_chunk

if TYPE_CHECKING:
    from day_09.core.query_logger import QueryLogger


class RAGPipeline:
    def __init__(
        self,
        file_path,
        embedding_model,
        vector_store,
        llm,
        chunk_size: int,
        chunk_overlap: int,
        top_k: int,
        delta_target: str | None = None,
        logger: QueryLogger | None = None,
    ):
        self.file_path = file_path
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.llm = llm
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k
        self.delta_target = delta_target
        self.logger = logger  # QueryLogger | None — audit log, NOT the vector store

    # ── Local pipeline ────────────────────────────────────────────────────────

    def ingest(self):
        """Local ingestion: file → extract → route_and_chunk → embed → vector store."""
        from day_09.config import MAX_ARTICLE_CHARS

        print("Reading file...")
        pages = extract_pages(str(self.file_path))
        print(f"Extracted {len(pages)} pages/sections.")

        print("Routing and chunking...")
        try:
            chunks = route_and_chunk(
                pages=pages,
                source_file=str(self.file_path),
                chunk_size=self.chunk_size,
                overlap=self.chunk_overlap,
                max_article_chars=MAX_ARTICLE_CHARS,
            )
        except Exception as e:
            print(f"Warning: smart chunker failed: {e}. Falling back to create_chunks.")
            chunks = create_chunks(
                pages=pages,
                chunk_size=self.chunk_size,
                overlap=self.chunk_overlap,
            )
        print(f"Created {len(chunks)} chunks.")

        print("Creating embeddings...")
        texts = [chunk["content"] for chunk in chunks]
        embeddings = self.embedding_model.embed_documents(texts)

        print("Saving to vector store...")
        self.vector_store.add_chunks(chunks=chunks, embeddings=embeddings)
        print("Ingestion completed.")

    def retrieve(self, question: str) -> list[dict]:
        query_embedding = self.embedding_model.embed_query(question)
        return self.vector_store.search(
            query_embedding=query_embedding,
            top_k=self.top_k,
            query_text=question,
        )

    def build_context(self, retrieved_chunks: list[dict]) -> str:
        blocks = []
        for item in retrieved_chunks:
            meta = item["metadata"]
            structure_type = meta.get("structure_type", "")
            number         = meta.get("number", "")
            regulation     = meta.get("regulation", "")
            chapter        = meta.get("chapter", "")
            title          = meta.get("title", "")

            # Build a header line that the LLM can use for citations
            if structure_type == "article":
                label = f"[ARTICLE {number}{(' — ' + title) if title else ''}]"
                if chapter:
                    label += f"  {chapter}"
                if regulation:
                    label += f"  ({regulation})"
            elif structure_type == "recital":
                label = f"[RECITAL {number}]"
                if regulation:
                    label += f"  ({regulation})"
            else:
                label = f"Source: {meta.get('source_file', '')}"

            blocks.append(f"{label}\n\n{item['content']}")
        return "\n---\n".join(blocks)

    def ask(self, question: str) -> dict:
        # Time the full retrieve + generate cycle for the audit record.
        t0 = time.monotonic()
        retrieved = self.retrieve(question)
        context   = self.build_context(retrieved)
        answer    = self.llm.generate(question=question, context=context)
        latency_ms = int((time.monotonic() - t0) * 1000)

        # ── Audit log (side effect — must not alter the return value) ──────────
        if self.logger is not None:
            try:
                from day_09.config import AZURE_OPENAI_DEPLOYMENT_NAME
                record = {
                    "id":         str(uuid.uuid4()),
                    "timestamp":  datetime.now(timezone.utc).isoformat(),
                    "query":      question,
                    "answer":     answer,
                    "model":      AZURE_OPENAI_DEPLOYMENT_NAME or "unknown",
                    "k":          self.top_k,
                    "filters":    None,
                    "latency_ms": latency_ms,
                    # retrieved carries the audit trail — which specific articles/
                    # recitals grounded this answer — but NOTHING writes this back
                    # into the vector store.
                    "retrieved": [
                        {
                            "chunk_id":       r["chunk_id"],
                            "structure_type": r["metadata"].get("structure_type", ""),
                            "number":         r["metadata"].get("number", 0),
                            "regulation":     r["metadata"].get("regulation", ""),
                            "score":          r["distance"],
                        }
                        for r in retrieved
                    ],
                }
                self.logger.log(record)
            except Exception as exc:
                # Logging must never crash the pipeline — warn and continue.
                warnings.warn(
                    f"QueryLogger.log() failed — audit record lost: {exc}",
                    stacklevel=2,
                )
        # ──────────────────────────────────────────────────────────────────────

        return {"question": question, "answer": answer, "retrieved_chunks": retrieved}

    # ── Databricks pipeline ───────────────────────────────────────────────────

    def ingest_databricks(self, file_url: str) -> None:
        """
        Full Databricks ingestion flow:
          1. Fetch file from URL/API
          2. Upload raw file to Databricks Unity Catalog Volume
          3. Trigger the bundle job (spark_ingester) via CLI or SDK

        Note: step 3 is run separately with:
            databricks bundle run ingest_chunks
        """
        from day_09.databricks.data_fetcher import fetch_file
        from day_09.databricks.volume_uploader import upload_to_volume
        from day_09.config import VOLUME_FILE_PATH

        print(f"Fetching file from: {file_url}")
        local_path = fetch_file(url=file_url)

        print("Uploading to Databricks Volume...")
        upload_to_volume(local_path=local_path, volume_path=VOLUME_FILE_PATH)

        print(
            "File uploaded. Run the Databricks bundle job to ingest:\n"
            "  databricks bundle run ingest_chunks"
        )

    def ask_databricks(self, question: str) -> dict:
        """
        Query pipeline for Databricks:
          1. Embed the question
          2. Search Databricks Vector Search index
          3. Build context and call LLM
          4. Write Q&A result to Delta results table
        """
        retrieved = self.retrieve(question)
        context = self.build_context(retrieved)
        answer = self.llm.generate(question=question, context=context)

        result = {"question": question, "answer": answer, "retrieved_chunks": retrieved}
        self._write_result_to_delta(result)
        return result

    def _write_result_to_delta(self, result: dict) -> None:
        """Append a Q&A result row to the results Delta table."""
        try:
            from databricks.sdk import WorkspaceClient
            from day_09.config import DELTA_CATALOG, DELTA_SCHEMA, DELTA_RESULTS_TABLE
            import json
            from datetime import datetime, timezone

            row = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "question": result["question"],
                "answer": result["answer"],
                "num_chunks_retrieved": len(result["retrieved_chunks"]),
                "sources": json.dumps([
                    c["metadata"]["source_file"] for c in result["retrieved_chunks"]
                ]),
            }

            table_name = f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{DELTA_RESULTS_TABLE}"
            client = WorkspaceClient()
            client.statement_execution.execute_statement(
                warehouse_id=None,  # set DATABRICKS_WAREHOUSE_ID in .env
                statement=(
                    f"INSERT INTO {table_name} VALUES "
                    f"('{row['timestamp']}', :question, :answer, {row['num_chunks_retrieved']}, :sources)"
                ),
                parameters=[
                    {"name": "question", "value": row["question"], "type": "STRING"},
                    {"name": "answer",   "value": row["answer"],   "type": "STRING"},
                    {"name": "sources",  "value": row["sources"],  "type": "STRING"},
                ],
            )
            print(f"Result written to Delta table '{table_name}'.")
        except Exception as e:
            print(f"Warning: could not write result to Delta: {e}")
