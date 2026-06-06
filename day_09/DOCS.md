# DAY_09 — EU GDPR RAG Pipeline

A Retrieval-Augmented Generation (RAG) pipeline that lets you ask natural-language questions against documents (PDF, DOCX, TXT, CSV, HTML). Built locally with ChromaDB + SentenceTransformers, designed to migrate to Databricks.

---

## How it works (end to end)

```
Document file
     │
     ▼
pdf_ingestions.py   ← extract raw text, split into pages/paragraphs
     │
     ▼
chunking.py         ← split text into overlapping word chunks
     │
     ▼
embeddings.py       ← turn each chunk into a vector (numbers)
     │
     ▼
vector_store.py     ← save vectors + text to ChromaDB on disk
     │
     ▼  (at query time)
embeddings.py       ← embed the user's question
     │
     ▼
vector_store.py     ← find the top-K most similar chunks
     │
     ▼
llm.py              ← send question + retrieved chunks to Azure OpenAI
     │
     ▼
Answer
```

---

## File by file

### `config.py`
Centralised settings — import from here instead of hardcoding values.

| Variable | What it is |
|---|---|
| `PDF_PATH` | Path to the document to ingest |
| `CHROMA_PATH` | Where ChromaDB stores its data on disk |
| `COLLECTION_NAME` | Name of the ChromaDB collection |
| `EMBEDDING_MODEL_NAME` | HuggingFace model used to create vectors |
| `CHUNK_SIZE` | Max words per chunk (default 500) |
| `CHUNK_OVERLAP` | Words shared between adjacent chunks (default 80) |
| `TOP_K` | How many chunks to retrieve per query (default 5) |
| `AZURE_OPENAI_*` | Azure credentials, read from `.env` |

---

### `pdf_ingestions.py`
Extracts raw text from a file and returns a list of page/chunk dicts.

| Function | What it does |
|---|---|
| `extract_pages(file_path)` | **Main entry point.** Detects the file extension and routes to the correct extractor below. Returns `[{"source_file", "page_number", "text"}, ...]` |
| `_extract_pdf(file_path)` | Reads a PDF with PyMuPDF. One dict per page. |
| `_extract_docx(file_path)` | Reads a Word document. One dict per paragraph. |
| `_extract_txt(file_path)` | Reads a plain text file. One dict per double-newline block. |
| `_extract_csv(file_path)` | Reads a CSV. One dict per row, formatted as `key: value \| key: value`. |
| `_extract_html(file_path)` | Reads HTML, strips scripts/styles. One dict per `<p>`, `<li>`, or heading tag. |
| `extract_pdf_pages(pdf_path)` | Legacy alias for `_extract_pdf` — kept for backward compatibility. |

---

### `chunking.py`
Splits extracted text into smaller overlapping chunks suitable for embedding.

| Function | What it does |
|---|---|
| `chunk_text(text, chunk_size, overlap)` | Splits on `\n\n` (paragraph breaks) first to respect document structure. Paragraphs longer than `chunk_size` words are word-split further. Short paragraphs are merged together up to `chunk_size`. Overlap is applied at merge boundaries. Returns `list[str]`. |
| `create_chunks(pages, chunk_size, overlap)` | Iterates over the page dicts from `pdf_ingestions.py`, calls `chunk_text` on each, and returns a flat list of chunk dicts: `{"chunk_id", "source_file", "page_number", "chunk_index", "content"}`. `chunk_id` is a SHA-256 hash that uniquely identifies each chunk. |

---

### `embeddings.py`
Converts text into vectors (lists of floats) that capture semantic meaning.

| Class / Method | What it does |
|---|---|
| `LocalEmbeddingModel(model_name)` | Loads a SentenceTransformer model locally. |
| `.embed_documents(texts)` | Embeds a list of strings (used during ingestion). Returns `list[list[float]]`. |
| `.embed_query(text)` | Embeds a single string (used at query time). Returns `list[float]`. |

> **Databricks swap:** replace with `ai_query('databricks-gte-large-en', text)` or the Databricks Foundation Model API.

---

### `vector_store.py`
Saves and searches vectors using ChromaDB (a local vector database).

| Class / Method | What it does |
|---|---|
| `ChromaVectorStore(persist_path, collection_name)` | Opens (or creates) a persistent ChromaDB collection on disk. Uses cosine similarity. |
| `.add_chunks(chunks, embeddings)` | Saves chunks + their vectors to the collection. Uses `upsert` so re-ingesting the same file won't create duplicates. |
| `.search(query_embedding, top_k)` | Finds the `top_k` chunks most similar to the query vector. Returns `[{"chunk_id", "content", "metadata", "distance"}, ...]`. Lower `distance` = more relevant. |

> **Databricks swap:** replace with `VectorSearchClient` and a Databricks AI Search index.

---

### `llm.py`
Sends the question + retrieved context to Azure OpenAI and returns the answer.

| Class / Method | What it does |
|---|---|
| `AzureOpenAIChatLLM()` | Initialises a LangChain `AzureChatOpenAI` client using credentials from `.env`. |
| `.generate(question, context)` | Builds a grounded prompt ("answer only from the context"), calls the model, and returns the answer string. If the answer isn't in the context, the model is instructed to say so explicitly. |

---

### `rag_pipeline.py`
Orchestrates all the components above into a single object.

| Method | What it does |
|---|---|
| `RAGPipeline(file_path, embedding_model, vector_store, llm, chunk_size, chunk_overlap, top_k)` | Stores references to all components. Does nothing by itself until you call a method. |
| `.ingest()` | Full ingestion flow: extract → chunk → embed → save to vector store. Only needs to run once per document. |
| `.retrieve(question)` | Embeds the question and searches the vector store. Returns the top-K matching chunks. |
| `.build_context(retrieved_chunks)` | Formats retrieved chunks into a readable text block (source file, page, chunk index + content) to pass to the LLM. |
| `.ask(question)` | Combines `.retrieve()` + `.build_context()` + `llm.generate()`. Returns `{"question", "answer", "retrieved_chunks"}`. |

---

### `other_main.py` — Entry point
The script you run to use the pipeline.

```
1. Load config
2. Create embedding model, vector store, LLM
3. Create RAGPipeline
4. If vector store is empty → run ingest()
5. Ask a question → print answer + sources
```

Run with:
```bash
cd day_09/
uv run python src/day_09/other_main.py
```

---

## Databricks migration checklist

- [ ] Replace `LocalEmbeddingModel` → Databricks Foundation Model API
- [ ] Replace `ChromaVectorStore` → Databricks Vector Search
- [ ] Update `PDF_PATH` in `config.py` → `/Volumes/catalog/schema/volume/file.pdf`
- [ ] LLM can stay as Azure OpenAI or switch to a Databricks-hosted model
