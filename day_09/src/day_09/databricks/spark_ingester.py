"""
Databricks job file — runs as a spark_python_task inside the bundle.
`spark` is injected by the Databricks runtime (intentionally unresolved locally).

What this job does:
  1. Reads the raw file directly from a Unity Catalog Volume path
  2. Extracts text (PDF, DOCX, TXT, CSV, HTML)
  3. Creates paragraph-aware chunks
  4. Writes chunks to Bronze and Gold Delta tables in Unity Catalog

Bundle commands:
    databricks bundle validate
    databricks bundle deploy
    databricks bundle run ingest_gdpr_chunks
"""

import argparse
import glob
import os
import sys
from pathlib import Path

# Databricks runs spark_python_task via exec(), so __file__ is not set.
# The bundle always deploys to /Workspace/Users/<user>/.bundle/<bundle>/<target>/files/
# We glob for the src/ directory that contains the day_09 package.
for _src in glob.glob("/Workspace/Users/*/.bundle/gdpr-rag-pipeline/*/files/src"):
    if os.path.isdir(os.path.join(_src, "day_09")) and _src not in sys.path:
        sys.path.insert(0, _src)
        break

from databricks.sdk import WorkspaceClient
from pyspark.sql.types import DoubleType, IntegerType, LongType, StringType, StructField, StructType

_path_candidates = []
if "__file__" in globals():
    _path_candidates.append(Path(__file__).resolve())
if sys.argv and sys.argv[0]:
    _path_candidates.append(Path(sys.argv[0]).resolve())
_path_candidates.append(Path.cwd().resolve())

for path in _path_candidates:
    search_roots = [path if path.is_dir() else path.parent]
    search_roots.extend(search_roots[0].parents)
    for root in search_roots:
        if root.name == "src" and (root / "day_09").exists():
            sys.path.insert(0, str(root))
            break
        if (root / "src" / "day_09").exists():
            sys.path.insert(0, str(root / "src"))
            break
    else:
        continue
    break

from day_09.ingestion.local_loader import extract_pages
from day_09.core.chunking import create_chunks
from day_09.core.smart_chunker import route_and_chunk

CHUNKS_SCHEMA = StructType(
    [
        StructField("chunk_id", StringType(), nullable=False),
        StructField("source_file", StringType(), nullable=False),
        StructField("page_number", IntegerType(), nullable=False),
        StructField("chunk_index", IntegerType(), nullable=False),
        StructField("content", StringType(), nullable=False),
    ]
)

INDEX_READY_SCHEMA = StructType(
    [
        StructField("document_id", StringType(), nullable=False),
        StructField("chunk_id", LongType(), nullable=False),
        StructField("content", StringType(), nullable=False),
        StructField("page_number", DoubleType(), nullable=True),
        StructField("source_file", StringType(), nullable=False),
        StructField("chunk_index", LongType(), nullable=False),
        StructField("id", StringType(), nullable=False),
    ]
)

SUPPORTED = {".pdf", ".docx", ".txt", ".csv", ".html", ".htm"}


def _list_volume_files(volume_file_path: str) -> list[str]:
    volume_dir = str(Path(volume_file_path).parent)
    client = WorkspaceClient()
    paths = [
        f.path
        for f in client.files.list_directory_contents(volume_dir)
        if Path(f.path).suffix.lower() in SUPPORTED
    ]
    return paths or [volume_file_path]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog")
    parser.add_argument("--schema")
    parser.add_argument("--table", help="Deprecated alias for --bronze-table")
    parser.add_argument("--bronze-table")
    parser.add_argument("--gold-table")
    args = parser.parse_args()

    if args.catalog:
        os.environ["DELTA_CATALOG"] = args.catalog
    if args.schema:
        os.environ["DELTA_SCHEMA"] = args.schema
    bronze_table = args.bronze_table or args.table
    if bronze_table:
        os.environ["DELTA_BRONZE_TABLE"] = bronze_table
        os.environ["DELTA_TABLE"] = bronze_table
    if args.gold_table:
        os.environ["DELTA_GOLD_TABLE"] = args.gold_table

    from day_09.config import (
        CHUNK_OVERLAP,
        CHUNK_SIZE,
        DELTA_BRONZE_TABLE,
        DELTA_CATALOG,
        DELTA_GOLD_TABLE,
        DELTA_SCHEMA,
        VOLUME_FILE_PATH,
    )

    files = _list_volume_files(VOLUME_FILE_PATH)
    print(f"Found {len(files)} files in Volume.")

    chunks = []
    for file_path in files:
        document_id = Path(file_path).stem
        print(f"Reading file from Volume: {file_path}")
        pages = extract_pages(file_path)
        print(f"Extracted {len(pages)} pages/sections.")

        try:
            file_chunks = route_and_chunk(
                pages=pages,
                source_file=document_id,
                chunk_size=CHUNK_SIZE,
                overlap=CHUNK_OVERLAP,
            )
        except Exception as e:
            print(f"Warning: smart chunker failed for {document_id}: {e}. Falling back to create_chunks.")
            file_chunks = create_chunks(pages=pages, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)

        for chunk_index, chunk in enumerate(file_chunks):
            chunk["source_file"] = document_id
            chunk["chunk_index"] = chunk_index

        chunks.extend(file_chunks)
        print(f"Created {len(file_chunks)} chunks for {document_id}.")

    print(f"Created {len(chunks)} total chunks.")

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

    table_name = f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{DELTA_BRONZE_TABLE}"
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(table_name)
    )

    print(f"Saved {df.count()} chunks to Delta table '{table_name}'.")

    index_rows = [
        (
            c["source_file"],
            int(c["chunk_index"]),
            c["content"],
            float(c["page_number"]) if c["page_number"] is not None else None,
            c["source_file"],
            int(c["chunk_index"]),
            f"{c['source_file']}_{int(c['chunk_index'])}",
        )
        for c in chunks
    ]

    index_df = spark.createDataFrame(index_rows, schema=INDEX_READY_SCHEMA)  # noqa: F821
    index_table_name = f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{DELTA_GOLD_TABLE}"
    (
        index_df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(index_table_name)
    )

    print(f"Saved {index_df.count()} chunks to Vector Search source table '{index_table_name}'.")


if __name__ == "__main__":
    main()
