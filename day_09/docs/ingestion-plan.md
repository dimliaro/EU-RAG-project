# Automatic EU Regulatory Document Ingestion Plan

This branch focuses on automatic ingestion of official EU regulatory documents
from public sources.

## Objective

Build a reliable ingestion path that can discover, download, extract, chunk, and
index official regulatory documents without manual file handling.

Target public sources include:

| Source | Example content |
|---|---|
| EUR-Lex | EU regulations, directives, decisions, and consolidated legal texts. |
| EBA | Banking guidelines, technical standards, Q&A publications, reports. |
| ESMA | Securities and markets guidance, technical standards, public statements. |
| ECB | Supervisory guidance, opinions, regulations, and policy documents. |

## Target Flow

```text
Official source -> Document fetcher -> Databricks Volume -> Smart chunking
-> gdpr_bronze_chunks -> gdpr_silver_enriched_chunks -> gdpr_gold_index_ready
-> Vector Search sync -> gdpr_vector_index -> RAG retrieval
```

## Planned Work

1. Define source-specific fetchers for official EU regulatory sources.
2. Store downloaded documents in the existing Databricks Volume structure.
3. Preserve source metadata such as title, URL, publication date, document type,
   and originating institution.
4. Reuse the existing smart chunker for structure-aware EU regulation chunking.
5. Write chunks into the active Databricks tables without changing table names.
6. Trigger or document the Vector Search sync step after ingestion completes.
7. Run retrieval evaluation after each ingestion update.

## Constraints

Do not rename active Databricks assets during this branch.

Active assets remain:

| Asset | Role |
|---|---|
| `gdpr_bronze_chunks` | Bronze chunk table. |
| `gdpr_silver_enriched_chunks` | Silver enriched chunk table. |
| `gdpr_gold_index_ready` | Gold index-ready source table. |
| `gdpr_vector_index` | Delta Sync Vector Search index. |
| `gdpr_rag_query_logs` | RAG query/audit log table. |

## Success Criteria

The automatic ingestion flow is successful when:

1. At least one official source can be ingested end to end.
2. Downloaded documents are traceable to their original public URL.
3. Smart chunking is used with fallback safety.
4. The Vector Search source table is refreshed.
5. Retrieval evaluation can be rerun against the updated index.
