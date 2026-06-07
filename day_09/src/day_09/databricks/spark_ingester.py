"""
Databricks job file — runs as a spark_python_task inside the bundle.
`spark` is injected by the Databricks runtime (intentionally unresolved locally).

What this job does:
  1. Reads the raw file directly from a Unity Catalog Volume path
  2. Extracts text (PDF, DOCX, TXT, CSV, HTML)
  3. Creates paragraph-aware chunks
  4. Writes chunks to a Delta table in Unity Catalog

Bundle commands:
    databricks bundle validate
    databricks bundle deploy
    databricks bundle run ingest_chunks
"""

import os

from pyspark.sql.types import IntegerType, StringType, StructField, StructType

from day_09.ingestion.local_loader import extract_pages
from day_09.core.chunking import create_chunks
from day_09.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DELTA_CATALOG,
    DELTA_SCHEMA,
    DELTA_TABLE,
    VOLUME_FILE_PATH,
)

CHUNKS_SCHEMA = StructType(
    [
        StructField("chunk_id", StringType(), nullable=False),
        StructField("source_file", StringType(), nullable=False),
        StructField("page_number", IntegerType(), nullable=False),
        StructField("chunk_index", IntegerType(), nullable=False),
        StructField("content", StringType(), nullable=False),
    ]
)


def main():
    print(f"Reading file from Volume: {VOLUME_FILE_PATH}")
    pages = extract_pages(VOLUME_FILE_PATH)
    print(f"Extracted {len(pages)} pages/sections.")

    chunks = create_chunks(pages=pages, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    print(f"Created {len(chunks)} chunks.")

    rows = [
        (
            c["chunk_id"],
            c["source_file"],
            int(c["page_number"]),
            int(c["chunk_index"]),
            c["content"],
        )
        for c in chunks
    ]

    df = spark.createDataFrame(rows, schema=CHUNKS_SCHEMA)  # noqa: F821 — spark injected by Databricks

    table_name = f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{DELTA_TABLE}"
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(table_name)
    )

    print(f"Saved {df.count()} chunks to Delta table '{table_name}'.")


if __name__ == "__main__":
    main()
