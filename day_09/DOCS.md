# DAY_09 — EU RAG Pipeline — Documentation

A Retrieval-Augmented Generation (RAG) pipeline for querying legal documents (PDF, DOCX, TXT, CSV, HTML) using natural language. Runs locally with ChromaDB + SentenceTransformers. Ingestion pipeline targets Databricks Unity Catalog.

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [How to Run](#2-how-to-run)
3. [File Reference](#3-file-reference)
4. [API Reference](#4-api-reference)
5. [Configuration Reference](#5-configuration-reference)
6. [Environment Variables (.env)](#6-environment-variables)
7. [Databricks Migration Checklist](#7-databricks-migration-checklist)

---

## 1. Architecture Overview

### Ingestion (run once per document set)

```
/Volumes/accenture2026dbcks/team6/volume/pdfs/   ← Databricks Volume
         │
         ▼
all_type_chunker.chunk_file()    ← reads bytes from Volume, splits into chunks
         │
         ▼
all_type_ingestion.py            ← writes chunks to Delta table via DatabricksConnect
         │
         ▼
accenture2026dbcks.team6.eu_chunks  (Delta table on Databricks)
```

### Local fallback ingestion (when Databricks is unreachable)

```
day_09/data/   ← local folder (drop any PDF/DOCX/TXT/CSV/HTML here)
         │
         ▼
pdf_ingestions.extract_pages()   ← extracts text, one dict per page/paragraph
         │
         ▼
chunking.create_chunks()         ← paragraph-aware word chunks with overlap
         │
         ▼
embeddings.embed_documents()     ← 384-dim vectors via MiniLM (local model)
         │
         ▼
ChromaDB (persisted at src/day_09/chroma_db/)
```

### Query (every user question)

```
rag.html  →  POST /query  →  ragAPI.py
                                  │
                          embed_query(question)       ← MiniLM local model
                                  │
                          ChromaDB.search(top_k=5)   ← cosine similarity
                                  │
                          build_context(chunks)       ← format source + text
                                  │
                          AzureOpenAI.generate()      ← cloud LLM call
                                  │
                          { question, answer, retrieved_chunks }
```

---

## 2. How to Run

### Prerequisites

```bash
cd day_09/
uv sync          # install all dependencies
```

Create a `.env` file at `day_09/` with the values from [Section 6](#6-environment-variables).

### Step 1 — Ingestion (Databricks path)

Run once to chunk all files from the Databricks Volume and write to the Delta table:

```bash
uv run python src/day_09/all_type_ingestion.py
```

Requires `DATABRICKS_HOST` and `DATABRICKS_TOKEN` in `.env`.

### Step 1 — Ingestion (local fallback)

Drop files into `day_09/data/` — the API ingests them automatically on startup if ChromaDB is empty. Supported formats: `.pdf`, `.docx`, `.txt`, `.csv`, `.html`.

To force a full re-ingest (e.g. after adding new files):

```bash
rm -rf src/day_09/chroma_db
```

### Step 2 — Start the API

```bash
uv run uvicorn day_09.ragAPI:app --host 0.0.0.0 --port 8001 --reload
```

On startup the server will:
1. Try to load chunks from the Databricks Delta table → embed → store in ChromaDB
2. If Databricks is unreachable → scan `data/` folder → embed → store in ChromaDB
3. If ChromaDB already has data → skip ingestion

### Step 3 — Open the frontend

Open `src/frontend/rag.html` in your browser. The API endpoint field defaults to `http://127.0.0.1:8001`.

---

## 3. File Reference

### Active files (do not delete)

| File | Role |
|---|---|
| `config.py` | All settings and paths — single source of truth |
| `all_type_chunker.py` | Reads files from Databricks Volume, chunks by type |
| `all_type_ingestion.py` | Orchestrates ingestion → writes to Delta table |
| `all_type_loader.py` | Reads chunks from Delta table at API startup |
| `pdf_ingestions.py` | Local multi-format text extractor (PDF/DOCX/TXT/CSV/HTML) |
| `chunking.py` | Paragraph-aware chunker with word overlap |
| `embeddings.py` | Local SentenceTransformer embedding model |
| `vector_store.py` | ChromaDB wrapper (cosine similarity search) |
| `llm.py` | Azure OpenAI LLM wrapper |
| `rag_pipeline.py` | Orchestrates the full RAG pipeline |
| `ragAPI.py` | FastAPI server — the entry point for queries |
| `src/frontend/rag.html` | Browser UI |

### Module details

#### `config.py`
| Variable | Default | Description |
|---|---|---|
| `DATA_DIR` | `day_09/data/` | Local folder scanned for files |
| `PDF_PATH` | `data/32016R0679_EN.pdf` | Single-file local fallback path |
| `CHROMA_PATH` | `src/day_09/chroma_db/` | ChromaDB storage location |
| `COLLECTION_NAME` | `pdf_rag_collection` | ChromaDB collection name |
| `EMBEDDING_MODEL_NAME` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model |
| `CHUNK_SIZE` | `500` | Max words per chunk |
| `CHUNK_OVERLAP` | `80` | Overlap words between chunks |
| `TOP_K` | `5` | Chunks returned per query |
| `DELTA_CATALOG` | `accenture2026dbcks` | Databricks catalog |
| `DELTA_SCHEMA` | `team6` | Databricks schema |
| `DELTA_TABLE` | `eu_chunks` | Delta table for chunks |
| `VOLUME_FILE_PATH` | `/Volumes/.../pdfs/32016R0679_EN.pdf` | Volume file path |

#### `all_type_chunker.py`
| Function | Description |
|---|---|
| `chunk_file(path, document_id)` | Downloads file bytes from Databricks Volume via SDK, detects extension, routes to correct chunker. Returns `[{document_id, chunk_id, chunk_text, page_number}]` |
| `_chunk_pdf(data, document_id)` | PyMuPDF + RecursiveCharacterTextSplitter (1000 chars, 150 overlap) |
| `_chunk_csv(data, document_id)` | One chunk per row: `col: val \| col: val` |
| `_chunk_docx(data, document_id)` | Joins paragraphs, then splits |
| `_chunk_txt(data, document_id)` | Splits raw text |

#### `pdf_ingestions.py` (local extractor)
| Function | Description |
|---|---|
| `extract_pages(file_path)` | Auto-detects extension, routes to correct extractor. Returns `[{source_file, page_number, text}]` |
| `_extract_pdf` | PyMuPDF, one dict per page |
| `_extract_docx` | python-docx, one dict per paragraph |
| `_extract_txt` | Split on `\n\n` |
| `_extract_csv` | One dict per row |
| `_extract_html` | BeautifulSoup, strips scripts/styles |

#### `chunking.py`
| Function | Description |
|---|---|
| `chunk_text(text, chunk_size, overlap)` | 1) Split on `\n\n`. 2) Word-split paragraphs > chunk_size. 3) Merge short paragraphs. 4) Apply overlap at boundaries. |
| `create_chunks(pages, chunk_size, overlap)` | Calls `chunk_text` per page, returns `[{chunk_id, source_file, page_number, chunk_index, content}]`. `chunk_id` is SHA-256. |

#### `embeddings.py`
| Method | Description |
|---|---|
| `LocalEmbeddingModel(model_name)` | Loads SentenceTransformer locally |
| `.embed_documents(texts)` | Batch embed list of strings → `list[list[float]]` |
| `.embed_query(text)` | Embed single string → `list[float]` (384 dimensions) |

#### `vector_store.py`
| Method | Description |
|---|---|
| `ChromaVectorStore(persist_path, collection_name)` | Opens or creates ChromaDB collection with cosine similarity |
| `.add_chunks(chunks, embeddings)` | Upserts chunks + vectors. Safe to call multiple times. |
| `.search(query_embedding, top_k)` | Returns top-k closest chunks: `[{chunk_id, content, metadata, distance}]` |

#### `llm.py`
| Method | Description |
|---|---|
| `AzureOpenAIChatLLM()` | Initialises `AzureChatOpenAI` from `.env` credentials |
| `.generate(question, context)` | Sends grounded prompt to Azure OpenAI. Returns answer string. If answer not in context, model says so explicitly. |

#### `rag_pipeline.py`
| Method | Description |
|---|---|
| `RAGPipeline(file_path, embedding_model, vector_store, llm, ...)` | Wires all components together |
| `.ingest()` | Local: extract → chunk → embed → ChromaDB |
| `.retrieve(question)` | Embed question → ChromaDB search → top-k chunks |
| `.build_context(chunks)` | Format chunks as `Source / Page / text` blocks |
| `.ask(question)` | retrieve → build_context → LLM → `{question, answer, retrieved_chunks}` |
| `.ingest_databricks(file_url)` | Fetch file from URL → upload to Databricks Volume |

---

## 4. API Reference

**Base URL:** `http://127.0.0.1:8001`

**Interactive docs:** `http://127.0.0.1:8001/docs` (auto-generated by FastAPI)

---

### `POST /query-databricks`

Ask a question against the Databricks Vector Search index.

This endpoint retrieves relevant regulatory chunks from Databricks Vector Search and sends them as context to the LLM.

**Request**

```json
{
  "question": "What does GDPR say about personal data?"
}
{
  "question": "What does GDPR say about personal data?",
  "answer": "The GDPR defines personal data as any information relating to an identified or identifiable natural person...",
  "retrieved_chunks": [
    {
      "chunk_id": "32016R0679_EN_207",
      "content": "...",
      "metadata": {
        "source_file": "32016R0679_EN",
        "page_number": 33,
        "chunk_index": 207
      },
      "distance": null
    }
  ]
}

### `POST /query`

Ask a question against the ingested documents.

**Request**

```http
POST /query
Content-Type: application/json
```

```json
{
  "question": "What are the rights of data subjects under GDPR?"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `question` | `string` | Yes | Natural language question |

**Response `200 OK`**

```json
{
  "question": "What are the rights of data subjects under GDPR?",
  "answer": "Under GDPR, data subjects have the right to access...",
  "retrieved_chunks": [
    {
      "chunk_id": "a3f9...",
      "content": "Article 15 — Right of access by the data subject...",
      "metadata": {
        "source_file": "32016R0679_EN.pdf",
        "page_number": 42,
        "chunk_index": 2
      },
      "distance": 0.187
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `question` | `string` | The original question |
| `answer` | `string` | LLM-generated answer grounded in retrieved chunks |
| `retrieved_chunks` | `array` | Top-k chunks used as context |
| `retrieved_chunks[].chunk_id` | `string` | SHA-256 unique ID of the chunk |
| `retrieved_chunks[].content` | `string` | The actual text of the chunk |
| `retrieved_chunks[].metadata.source_file` | `string` | Filename the chunk came from |
| `retrieved_chunks[].metadata.page_number` | `int` | Page number in the source file |
| `retrieved_chunks[].metadata.chunk_index` | `int` | Chunk position within that page |
| `retrieved_chunks[].distance` | `float` | Cosine distance — lower = more relevant |

**Error responses**

| Code | Meaning |
|---|---|
| `500` | Internal server error — check terminal for details |
| `503` | Server not started — start uvicorn first |

**Example — curl**

```bash
curl -X POST http://127.0.0.1:8001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the right to be forgotten?"}'
```

**Example — Python**

```python
import requests

response = requests.post(
    "http://127.0.0.1:8001/query",
    json={"question": "What is the right to be forgotten?"}
)
print(response.json()["answer"])
```

---

## 5. Configuration Reference

All configuration lives in [config.py](src/day_09/config.py). Values can be overridden via `.env`.

```
day_09/data/          ← drop documents here for local ingestion
day_09/src/day_09/
    chroma_db/        ← auto-created, delete to force re-ingest
    config.py
    ragAPI.py         ← start this with uvicorn
src/frontend/rag.html ← open in browser
```

---

## 6. Environment Variables

Create `day_09/.env`:

```env
# Azure OpenAI (required for LLM)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name

# Databricks (required for Volume/Delta ingestion)
DATABRICKS_HOST=https://adb-XXXXXXXXXXXXXXXX.X.azuredatabricks.net
DATABRICKS_TOKEN=dapiXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Optional overrides
DELTA_CATALOG=accenture2026dbcks
DELTA_SCHEMA=team6
DELTA_TABLE=eu_chunks
VOLUME_FILE_PATH=/Volumes/accenture2026dbcks/team6/volume/pdfs/32016R0679_EN.pdf
```

---

## 7. Databricks Migration Checklist

| Step | Status | Notes |
|---|---|---|
| Chunk files from Volume → Delta table | ✅ | `all_type_ingestion.py` |
| Read chunks from Delta at startup | ✅ | `all_type_loader.py` |
| Databricks credentials in `.env` | ⬜ | Add `DATABRICKS_HOST` + `DATABRICKS_TOKEN` |
|| Replace ChromaDB → Databricks Vector Search | ✅ | Implemented through `/query-databricks` endpoint |
| FastAPI Databricks Vector Search endpoint | ✅ | `POST /query-databricks` |
| Replace local embeddings → Databricks Foundation Model API | ⬜ | Swap `LocalEmbeddingModel` in `embeddings.py` |
| Replace Azure OpenAI → Databricks-hosted LLM | ⬜ | Optional |
