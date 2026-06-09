# Auto-Ingestion Architecture

## Current Branch

`auto-ingestion`

## Purpose

The auto-ingestion branch adds automatic and cached ingestion support for
official EU regulatory documents. The goal is to make it easy to bring official
documents into the existing Databricks-backed RAG pipeline without manually
placing every file in the Volume.

The implementation supports two practical modes:

1. Online CELEX-based ingestion from EUR-Lex URLs.
2. Offline-safe cached PDF upload for presentations and demos.

## Current Implemented Flow

The current auto-ingestion implementation supports:

1. CELEX discovery for known EU legal documents.
2. TXT and PDF URL generation for EUR-Lex documents.
3. PDF download with validation.
4. Databricks Volume upload.
5. Cached local-file demo mode.
6. Handoff to the existing `spark_ingester.py`, which processes files already
   present in the Databricks Volume.

The auto-ingestion code does not call `spark_ingester.py` directly. It prepares
the Volume contents. The existing Databricks ingestion job remains responsible
for extraction, smart chunking, Delta table writes, and Vector Search source
table refresh.

## Important Modules

| Module | Responsibility |
|---|---|
| `src/day_09/ingestion/auto/cli.py` | CLI entrypoint for CELEX discovery and cached local PDF upload. |
| `src/day_09/ingestion/auto/pipeline.py` | Orchestrates CELEX discovery, PDF download, and Volume upload. |
| `src/day_09/ingestion/auto/models.py` | Shared dataclasses for discovered, downloaded, and ingested documents. |
| `src/day_09/ingestion/auto/sources/eurlex.py` | EUR-Lex CELEX discovery, TXT/PDF URL generation, and PDF download helper. |
| `src/day_09/ingestion/auto/downloaders/http_downloader.py` | Reusable HTTP downloader with checksum and content-type validation. |
| `src/day_09/ingestion/auto/storage/volume_writer.py` | Writes local files to a Databricks Unity Catalog Volume. |
| `src/day_09/ingestion/auto/storage/manifest_store.py` | Local JSON manifest for tracking discovered documents. |

## CLI Examples

### CELEX Discovery Only

```bash
uv run python -m day_09.ingestion.auto.cli \
  --celex 32016R0679
```

Example output includes the official EUR-Lex TXT and PDF URLs for the CELEX ID.

### Cached Local PDF Upload

Use this mode for presentations and offline-safe demos. It does not call
EUR-Lex.

```bash
uv run python -m day_09.ingestion.auto.cli \
  --local-file demo_documents/32016R0679_GDPR.pdf \
  --volume-dir /Volumes/accenture2026dbcks/team6/volume/pdfs
```

Expected output shape:

```text
Uploaded: demo_documents/32016R0679_GDPR.pdf
Volume path: /Volumes/accenture2026dbcks/team6/volume/pdfs/32016R0679_GDPR.pdf
```

### Online CELEX Download And Upload

The orchestration API supports online CELEX download and Volume upload:

```python
from day_09.ingestion.auto.pipeline import AutoIngestionPipeline

pipeline = AutoIngestionPipeline()
result = pipeline.ingest_celex_pdf(
    celex_id="32016R0679",
    target_volume_dir="/Volumes/accenture2026dbcks/team6/volume/pdfs",
    overwrite=False,
)

print(result.celex_id)
print(result.title)
print(result.local_path)
print(result.volume_path)
print(result.source_url)
print(result.pdf_url)
```

## Known Limitation

EUR-Lex may block headless online requests with anti-bot or WAF protection. In
that case, online CELEX PDF download can fail even when the generated official
URL is correct.

For presentations and demos, use cached official PDFs and the `--local-file`
upload mode.

## End-To-End Databricks Flow

```text
cached/online PDF
-> Databricks Volume
-> spark_ingester.py
-> team6_panos
-> team6_panos_index_ready
-> Vector Search sync
-> team6_panos_index
-> RAG retrieval
```

## Active Assets

| Asset | Role |
|---|---|
| `team6_panos` | Main Delta table containing ingested and chunked document content. |
| `team6_panos_index_ready` | Index-ready source table for Vector Search. |
| `team6_panos_index` | Databricks Delta Sync Vector Search index. |
| `team6_panos_vs` | Logical retrieval layer used by the RAG application. |
