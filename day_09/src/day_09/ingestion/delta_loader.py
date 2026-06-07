"""
Reads chunks from the Databricks Delta table via DatabricksConnect
and returns them in the format expected by the rest of the pipeline.

Called once on API startup (if ChromaDB is empty) to populate the local vector store.
"""

from databricks.connect import DatabricksSession
from day_09.config import DELTA_CATALOG, DELTA_SCHEMA, DELTA_TABLE


def load_chunks_from_delta() -> list[dict]:
    """
    Read all chunks from the Delta table and return them as a list of dicts
    compatible with vector_store.add_chunks().

    Returns:
        [{"chunk_id", "source_file", "page_number", "chunk_index", "content"}, ...]
    """
    spark = DatabricksSession.builder.serverless(True).getOrCreate()

    table = f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{DELTA_TABLE}"
    df = spark.sql(f"SELECT * FROM {table}")

    rows = df.collect()
    chunks = []

    for row in rows:
        chunks.append(
            {
                "chunk_id":    str(row["chunk_id"]),
                "source_file": str(row["document_id"]),
                "page_number": int(row["page_number"]) if row["page_number"] is not None else 0,
                "chunk_index": int(row["chunk_id"]),
                "content":     str(row["chunk_text"]),
            }
        )

    print(f"Loaded {len(chunks)} chunks from {table}.")
    return chunks
