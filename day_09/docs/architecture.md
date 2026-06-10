# EU RAG Databricks Architecture

This document describes the current Databricks production architecture used by
the EU RAG project.

## Active Flow

```text
Raw PDF Volume -> Bronze -> Silver -> Gold -> Vector Search Index -> Retrieval
```

## Active Assets

| Physical name | Logical layer | Purpose |
|---|---|---|
| `/Volumes/accenture2026dbcks/team6/volume/pdfs` | Raw PDF Volume | Stores official source PDFs before Spark ingestion. |
| `accenture2026dbcks.team6.gdpr_bronze_chunks` | Bronze table | Stores ingested and smart-chunked document content. |
| `accenture2026dbcks.team6.gdpr_silver_enriched_chunks` | Silver table | Stores enriched chunks, including Databricks embedding vectors. |
| `accenture2026dbcks.team6.gdpr_gold_index_ready` | Gold table | Stores records shaped for Vector Search indexing. |
| `accenture2026dbcks.team6.gdpr_vector_index` | Vector Search Index | Databricks Vector Search index used for retrieval. |
| `accenture2026dbcks.team6.gdpr_rag_query_logs` | Query logs | Planned Delta table for RAG query/audit logging. |

## Code References

| File | Usage |
|---|---|
| `src/day_09/config.py` | Central source for Databricks table, volume, and index names. |
| `databricks.yml` | Databricks bundle job names, task parameters, and retry settings. |
| `src/day_09/databricks/spark_ingester.py` | Reads PDFs from the raw Volume and writes Bronze/Gold tables. |
| `src/day_09/databricks/enrichment_job.py` | Reads Bronze chunks and writes Silver enriched chunks. |
| `src/day_09/databricks/vector_search_setup.py` | Creates the Databricks Vector Search endpoint/index. |
| `src/day_09/retrieval/databricks_retriever.py` | Runtime retrieval for `/query-databricks`. |
| `src/day_09/evaluation/evaluate_retrieval.py` | Retrieval evaluation against the configured Vector Search index. |

## Setup

The helper script `src/day_09/databricks/setup_databricks_assets.py` creates or
documents the Unity Catalog schema, raw document Volume, Bronze/Silver/Gold
tables, and query log table.

The Vector Search index still requires the Databricks Vector Search setup step
after the source table exists.
