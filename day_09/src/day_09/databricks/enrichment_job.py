"""
Databricks job file — runs as a spark_python_task inside the bundle.
`spark` is injected by the Databricks runtime (intentionally unresolved locally).

What this job does:
  1. Reads raw chunks from the Bronze Delta table (gdpr_bronze_chunks)
  2. Calls the Databricks Foundation Model API in batches to get embeddings
  3. Writes the Silver table (gdpr_silver_enriched_chunks) with an `embedding` column

This enriched table is what Databricks Vector Search syncs from.

Pipeline:
  spark_ingester  →  gdpr_bronze_chunks  →  [this job]  →  gdpr_silver_enriched_chunks
                                                           ↓
                                               Vector Search index (auto-sync)

Bundle command:
    databricks bundle run enrich_gdpr_chunks
"""

import argparse
import os
import sys
import glob

# Databricks runs spark_python_task via exec(), so __file__ is not set.
# The bundle always deploys to /Workspace/Users/<user>/.bundle/<bundle>/<target>/files/
# We glob for the src/ directory that contains the day_09 package.
for _src in glob.glob("/Workspace/Users/*/.bundle/gdpr-rag-pipeline/*/files/src"):
    if os.path.isdir(os.path.join(_src, "day_09")) and _src not in sys.path:
        sys.path.insert(0, _src)
        break

import pandas as pd
from pyspark.sql.functions import col, pandas_udf
from pyspark.sql.types import ArrayType, FloatType

BATCH_SIZE = 25  # Databricks Foundation Model API limit per request


@pandas_udf(ArrayType(FloatType()))
def _embed(texts: pd.Series) -> pd.Series:
    """
    Pandas UDF: each Spark partition sends its texts in batches to the
    Foundation Model API and gets back a list of float vectors.
    """
    import mlflow.deployments

    client = mlflow.deployments.get_deploy_client("databricks")
    results: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts.iloc[i : i + BATCH_SIZE].tolist()
        response = client.predict(
            endpoint=os.getenv("EMBEDDING_ENDPOINT", "databricks-gte-large-en"),
            inputs={"input": batch},
        )
        for item in response["data"]:
            results.append(item["embedding"])

    return pd.Series(results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog")
    parser.add_argument("--schema")
    parser.add_argument("--bronze-table")
    parser.add_argument("--silver-table")
    args = parser.parse_args()

    if args.catalog:
        os.environ["DELTA_CATALOG"] = args.catalog
    if args.schema:
        os.environ["DELTA_SCHEMA"] = args.schema
    if args.bronze_table:
        os.environ["DELTA_BRONZE_TABLE"] = args.bronze_table
        os.environ["DELTA_TABLE"] = args.bronze_table
    if args.silver_table:
        os.environ["DELTA_SILVER_TABLE"] = args.silver_table
        os.environ["DELTA_ENRICHED_TABLE"] = args.silver_table

    from day_09.config import (
        DELTA_BRONZE_TABLE,
        DELTA_CATALOG,
        DELTA_SCHEMA,
        DELTA_SILVER_TABLE,
        EMBEDDING_ENDPOINT,
    )

    source_table = f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{DELTA_BRONZE_TABLE}"
    target_table = f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{DELTA_SILVER_TABLE}"

    print(f"Reading chunks from: {source_table}")
    df = spark.table(source_table)  # noqa: F821 — spark injected by Databricks
    total = df.count()
    print(f"Embedding {total} chunks via endpoint '{EMBEDDING_ENDPOINT}'...")

    enriched = df.withColumn("embedding", _embed(col("content")))

    print(f"Writing enriched table to: {target_table}")
    (
        enriched.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(target_table)
    )
    print(f"Done. {total} rows written to '{target_table}'.")
    print("Next step: run vector_search_setup.py to create the index (one-time).")


if __name__ == "__main__":
    main()
