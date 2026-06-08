"""
One-time setup script: creates the Databricks Vector Search endpoint and a
Delta Sync index on the enriched chunks table.

Run once — from your local machine with DatabricksConnect, or as a notebook:
    uv run python -m day_09.databricks.vector_search_setup

What it creates:
  - Vector Search endpoint  (VECTOR_SEARCH_ENDPOINT)
  - Delta Sync index        (VECTOR_SEARCH_INDEX)
      source : eu_chunks_enriched  (must exist — run enrich_chunks bundle job first)
      key    : chunk_id
      vector : embedding column (pre-computed by enrichment_job.py)

After this runs, the index auto-syncs whenever eu_chunks_enriched changes.
"""

from databricks.vector_search.client import VectorSearchClient

from day_09.config import (
    DELTA_CATALOG,
    DELTA_ENRICHED_TABLE,
    DELTA_SCHEMA,
    EMBEDDING_DIMENSION,
    VECTOR_SEARCH_ENDPOINT,
    VECTOR_SEARCH_INDEX,
)


def _create_endpoint_if_missing(vsc: VectorSearchClient) -> None:
    existing = {ep["name"] for ep in vsc.list_endpoints().get("endpoints", [])}
    if VECTOR_SEARCH_ENDPOINT in existing:
        print(f"  Endpoint '{VECTOR_SEARCH_ENDPOINT}' already exists — skipping.")
        return
    print(f"  Creating endpoint '{VECTOR_SEARCH_ENDPOINT}'...")
    vsc.create_endpoint(name=VECTOR_SEARCH_ENDPOINT, endpoint_type="STANDARD")
    print("  Endpoint created.")


def _create_index_if_missing(vsc: VectorSearchClient) -> None:
    try:
        vsc.get_index(endpoint_name=VECTOR_SEARCH_ENDPOINT, index_name=VECTOR_SEARCH_INDEX)
        print(f"  Index '{VECTOR_SEARCH_INDEX}' already exists — skipping.")
        return
    except Exception:
        pass  # does not exist yet

    source_table = f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{DELTA_ENRICHED_TABLE}"
    print(f"  Creating Delta Sync index on '{source_table}'...")

    # pipeline_type="TRIGGERED" means you manually call .sync() to refresh.
    # Change to "CONTINUOUS" for near-real-time auto-sync (costs more).
    vsc.create_delta_sync_index(
        endpoint_name=VECTOR_SEARCH_ENDPOINT,
        index_name=VECTOR_SEARCH_INDEX,
        source_table_name=source_table,
        pipeline_type="TRIGGERED",
        primary_key="chunk_id",
        embedding_dimension=EMBEDDING_DIMENSION,
        embedding_vector_column="embedding",  # pre-computed column from enrichment_job.py
    )
    print(f"  Index '{VECTOR_SEARCH_INDEX}' created and initial sync started.")


def main():
    print("Setting up Databricks Vector Search...\n")
    vsc = VectorSearchClient()

    print("[1/2] Endpoint")
    _create_endpoint_if_missing(vsc)

    print("[2/2] Index")
    _create_index_if_missing(vsc)

    print("\nVector Search ready.")
    print(f"  Endpoint : {VECTOR_SEARCH_ENDPOINT}")
    print(f"  Index    : {VECTOR_SEARCH_INDEX}")
    print("\nTo query it, use DatabricksVectorStore in databricks/retriever.py.")


if __name__ == "__main__":
    main()
