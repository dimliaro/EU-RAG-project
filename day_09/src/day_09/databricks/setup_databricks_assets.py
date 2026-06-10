"""
Create the Unity Catalog assets used by the GDPR RAG Databricks pipeline.

Run inside Databricks as a notebook or spark_python_task:
    python -m day_09.databricks.setup_databricks_assets

If you run this locally, set DATABRICKS_WAREHOUSE_ID so the Databricks SDK can
execute SQL through a SQL warehouse.
"""

from __future__ import annotations

import os

from databricks.sdk import WorkspaceClient

from day_09.config import (
    DELTA_BRONZE_TABLE_FULL_NAME,
    DELTA_CATALOG,
    DELTA_GOLD_TABLE_FULL_NAME,
    DELTA_RESULTS_TABLE_FULL_NAME,
    DELTA_SCHEMA,
    DELTA_SILVER_TABLE_FULL_NAME,
    RAW_DOCUMENTS_VOLUME,
    RAW_PDF_VOLUME_DIR,
    VECTOR_SEARCH_INDEX,
)


def _execute_sql(statement: str) -> None:
    if "spark" in globals():
        spark.sql(statement)  # type: ignore[name-defined]  # Databricks injects spark.
        return

    warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
    if not warehouse_id:
        raise RuntimeError(
            "No Spark session found and DATABRICKS_WAREHOUSE_ID is not set. "
            "Run this inside Databricks or configure a SQL warehouse ID."
        )

    WorkspaceClient().statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=statement,
    )


def main() -> None:
    statements = [
        f"CREATE SCHEMA IF NOT EXISTS {DELTA_CATALOG}.{DELTA_SCHEMA}",
        (
            f"CREATE VOLUME IF NOT EXISTS "
            f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{RAW_DOCUMENTS_VOLUME}"
        ),
        f"""
        CREATE TABLE IF NOT EXISTS {DELTA_BRONZE_TABLE_FULL_NAME} (
            chunk_id STRING NOT NULL,
            document_id STRING NOT NULL,
            source_file STRING NOT NULL,
            source_path STRING NOT NULL,
            page_number INT,
            chunk_index INT,
            content STRING NOT NULL,
            doc_kind STRING,
            structure_type STRING,
            number INT,
            chapter STRING,
            title STRING,
            regulation STRING,
            ingestion_timestamp TIMESTAMP NOT NULL
        )
        USING DELTA
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {DELTA_SILVER_TABLE_FULL_NAME} (
            chunk_id STRING NOT NULL,
            document_id STRING NOT NULL,
            source_file STRING NOT NULL,
            source_path STRING NOT NULL,
            page_number INT,
            chunk_index INT,
            content STRING NOT NULL,
            doc_kind STRING,
            structure_type STRING,
            number INT,
            chapter STRING,
            title STRING,
            regulation STRING,
            ingestion_timestamp TIMESTAMP NOT NULL,
            embedding ARRAY<FLOAT>
        )
        USING DELTA
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {DELTA_GOLD_TABLE_FULL_NAME} (
            document_id STRING NOT NULL,
            chunk_id BIGINT NOT NULL,
            content STRING NOT NULL,
            page_number DOUBLE,
            source_file STRING NOT NULL,
            source_path STRING NOT NULL,
            chunk_index BIGINT NOT NULL,
            doc_kind STRING,
            structure_type STRING,
            number INT,
            chapter STRING,
            title STRING,
            regulation STRING,
            ingestion_timestamp TIMESTAMP NOT NULL,
            id STRING NOT NULL
        )
        USING DELTA
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {DELTA_RESULTS_TABLE_FULL_NAME} (
            id STRING NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            query STRING NOT NULL,
            answer STRING NOT NULL,
            model STRING NOT NULL,
            k INT NOT NULL,
            filters STRING,
            latency_ms BIGINT NOT NULL,
            retrieved STRING NOT NULL
        )
        USING DELTA
        """,
    ]

    print("Creating Databricks GDPR RAG assets...")
    for statement in statements:
        sql = " ".join(statement.split())
        print(f"SQL: {sql}")
        _execute_sql(statement)

    print("Databricks assets are ready.")
    print(f"Raw PDF Volume path: {RAW_PDF_VOLUME_DIR}")
    print(f"Bronze table: {DELTA_BRONZE_TABLE_FULL_NAME}")
    print(f"Silver table: {DELTA_SILVER_TABLE_FULL_NAME}")
    print(f"Gold table: {DELTA_GOLD_TABLE_FULL_NAME}")
    print(f"Query log table: {DELTA_RESULTS_TABLE_FULL_NAME}")
    print(f"Vector Search index name: {VECTOR_SEARCH_INDEX}")
    print("Create or refresh the Vector Search index with vector_search_setup.py.")


if __name__ == "__main__":
    main()
