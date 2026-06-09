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
-> team6_panos -> team6_panos_index_ready -> Vector Search sync
-> team6_panos_index -> RAG retrieval
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
| `team6_panos` | Main chunk table. |
| `team6_panos_index_ready` | Index-ready source table. |
| `team6_panos_index` | Delta Sync Vector Search index. |
| `team6_panos_vs` | Retrieval layer. |

## Success Criteria

The automatic ingestion flow is successful when:

1. At least one official source can be ingested end to end.
2. Downloaded documents are traceable to their original public URL.
3. Smart chunking is used with fallback safety.
4. The Vector Search source table is refreshed.
5. Retrieval evaluation can be rerun against the updated index.
