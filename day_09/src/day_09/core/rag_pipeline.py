"""
Orchestrates the full RAG pipeline in two modes:

LOCAL mode  (ingest / ask)
  file → extract → chunk → ChromaDB → LLM

DATABRICKS mode  (ingest_databricks / ask_databricks)
  URL/file → fetch → upload to Volume → [bundle job runs spark_ingester]
           → Vector Search → LLM → results written to Delta table
"""

from day_09.ingestion.local_loader import extract_pages
from day_09.core.chunking import create_chunks
from day_09.core.smart_chunker import route_and_chunk


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
    ):
        self.file_path = file_path
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.llm = llm
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k
        self.delta_target = delta_target

    # ── Local pipeline ────────────────────────────────────────────────────────

    def ingest(self):
        """Local ingestion: file → extract → chunk → embed → ChromaDB."""
        print("Reading file...")
        pages = extract_pages(str(self.file_path))
        print(f"Extracted {len(pages)} chunks.")

        print("Creating chunks...")
        try:
            chunks = route_and_chunk(
                pages=pages,
                source_file=str(self.file_path),
                chunk_size=self.chunk_size,
                overlap=self.chunk_overlap,
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

        print("Saving to Chroma...")
        self.vector_store.add_chunks(chunks=chunks, embeddings=embeddings)
        print("Ingestion completed.")

    def retrieve(self, question: str) -> list[dict]:
        query_embedding = self.embedding_model.embed_query(question)
        return self.vector_store.search(query_embedding=query_embedding, top_k=self.top_k)

    def build_context(self, retrieved_chunks: list[dict]) -> str:
        blocks = []
        for item in retrieved_chunks:
            meta = item["metadata"]
            blocks.append(
                f"Source: {meta['source_file']}\n"
                f"Page: {meta['page_number']}  Chunk: {meta['chunk_index']}\n\n"
                f"{item['content']}"
            )
        return "\n---\n".join(blocks)

    def ask(self, question: str) -> dict:
        retrieved = self.retrieve(question)
        context = self.build_context(retrieved)
        answer = self.llm.generate(question=question, context=context)
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
