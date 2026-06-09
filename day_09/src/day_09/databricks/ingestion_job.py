"""
Scans a Databricks Volume directory, chunks every supported file,
and writes all chunks to a single Delta table.

Supported: .pdf, .csv, .docx, .txt

Run locally (with DatabricksConnect) or as a Databricks job.
"""

from databricks.connect import DatabricksSession
from databricks.sdk import WorkspaceClient
import pandas as pd
from pathlib import Path

from day_09.databricks.chunker import chunk_file
from day_09.config import DELTA_CATALOG, DELTA_SCHEMA, DELTA_TABLE

VOLUME_DIR = f"/Volumes/{DELTA_CATALOG}/team6/volume/pdfs"
SUPPORTED  = {".pdf", ".csv", ".docx", ".txt"}


def list_volume_files(volume_dir: str) -> list[str]:
    """List all supported files in a Databricks Volume directory."""
    client = WorkspaceClient()
    files  = client.files.list_directory_contents(volume_dir)
    return [
        f.path for f in files
        if Path(f.path).suffix.lower() in SUPPORTED
    ]


def main():
    spark = DatabricksSession.builder.serverless(True).getOrCreate()

    files = list_volume_files(VOLUME_DIR)
    print(f"Found {len(files)} files in {VOLUME_DIR}: {[Path(f).name for f in files]}")

    all_chunks = []
    for path in files:
        document_id = Path(path).stem
        print(f"  Chunking: {Path(path).name} ...")
        chunks = chunk_file(path, document_id=document_id)
        all_chunks.extend(chunks)
        print(f"    → {len(chunks)} chunks")

    print(f"\nTotal chunks: {len(all_chunks)}")

    df       = pd.DataFrame(all_chunks)
    spark_df = spark.createDataFrame(df)

    table = f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{DELTA_TABLE}"
    (
        spark_df.write
        .format("delta")
        .mode("overwrite")
        .saveAsTable(table)
    )
    print(f"Written to Delta table: {table}")


if __name__ == "__main__":
    main()
