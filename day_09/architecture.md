# EU RAG Databricks Architecture

This document describes the active Databricks assets used by the EU RAG project.
The physical table and index names are intentionally kept as they are for now, to
avoid breaking ingestion, evaluation, or API code while the pipeline is still
evolving.

## Current Naming Policy

Do not rename the live Databricks tables or Vector Search indexes during the
active ingestion and retrieval work.

Renaming should be done later as an organized team refactor, after all code,
notebooks, bundle configuration, and Vector Search dependencies have been
audited together.

## Logical Layers

| Physical name | Logical layer | Purpose |
|---|---|---|
| `team6_panos` | Bronze/Silver Hybrid Layer | Main Delta table containing ingested and chunked document content. There is currently no separate physical Silver table. |
| `team6_panos_index_ready` | Gold Layer | Index-ready table used as the source for Vector Search indexing. |
| `team6_panos_index` | Vector Search Index | Databricks Delta Sync Vector Search index built from `team6_panos_index_ready`. |
| `team6_panos_vs` | Vector Search / Retrieval Layer | Retrieval asset used by the RAG pipeline. |

The current active architecture is:

```text
Bronze/Silver Hybrid -> Gold -> Vector Search Index -> Retrieval
```

Separate Silver tables such as `eu_chunks` or `eu_chunks_enriched` may be
introduced in a future refactor, but they are not part of the active pipeline
today.

## Current Code References

The current codebase references `team6_panos_index` directly in:

| File | Usage |
|---|---|
| `src/day_09/retrieval/databricks_retriever.py` | Runtime retrieval for `/query-databricks`. |
| `src/day_09/evaluation/evaluate_retrieval.py` | Retrieval evaluation script. |

The bundle job writes table names from bundle variables:

| File | Usage |
|---|---|
| `databricks.yml` | Passes `catalog`, `schema`, and `table` variables into `spark_ingester.py`. |
| `src/day_09/databricks/spark_ingester.py` | Writes the configured Delta table and its `_index_ready` source table. |

## Future Rename Plan

If the team later decides to rename the physical Databricks assets, do it in one
coordinated change:

1. Search the repo, notebooks, and Databricks jobs for all old names.
2. Update Python, YAML, notebooks, evaluation scripts, API config, and Vector
   Search dependencies together.
3. Rename or recreate Databricks tables and indexes in the correct dependency
   order.
4. Re-run ingestion, Vector Search sync, and retrieval evaluation.

Example SQL for a future table rename:

```sql
ALTER TABLE team6.team6_panos
RENAME TO team6.team6_bronze_documents;
```

Avoid applying this until the team has agreed on the final naming convention and
the full pipeline has stabilized.
