"""
spark_uploader.py

Databricks job file — runs as a spark_python_task inside a bundle.
`spark` is injected by the Databricks runtime; it is intentionally
unresolved locally (yellow in the IDE).

Bundle command:
    databricks bundle validate
    databricks bundle deploy
    databricks bundle run upload_chunks
"""

from day_09.pdf_ingestions import extract_pages
from day_09.chunking import create_chunks
from day_09.config import (
    PDF_PATH,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    DELTA_CATALOG,
    DELTA_SCHEMA,
    DELTA_TABLE,
)

from pyspark.sql.types import IntegerType, StringType, StructField, StructType  # noqa: E402

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
    print("Reading file...")
    pages = extract_pages(str(PDF_PATH))
    print(f"Extracted {len(pages)} pages.")

    print("Creating chunks...")
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
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(table_name)

    print(f"Uploaded {df.count()} chunks to {table_name}.")


if __name__ == "__main__":
    main()
