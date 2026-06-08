"""
FastAPI server for the RAG pipeline.

Startup flow:
  1. Load components (embedding model, ChromaDB, LLM)
  2. If ChromaDB is empty → read chunks from Databricks Delta table → embed → store
     Falls back to local data/ directory if Databricks is unavailable.
  3. POST /query: embed question → search ChromaDB → call LLM → return answer

Run:
    cd day_09/
    uv run uvicorn day_09.api.app:app --host 0.0.0.0 --port 8080 --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from databricks.sdk import WorkspaceClient

from day_09.config import (
    CHROMA_PATH,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DATA_DIR,
    EMBEDDING_MODEL_NAME,
    MAX_ARTICLE_CHARS,
    TOP_K,
    VOLUME_FILE_PATH,
)
from day_09.core.embeddings import LocalEmbeddingModel
from day_09.core.llm import AzureOpenAIChatLLM
from day_09.core.query_logger import get_query_logger
from day_09.core.rag_pipeline import RAGPipeline
from day_09.core.vector_store import ChromaVectorStore

# ── Shared components ─────────────────────────────────────────────────────────

embedding_model = LocalEmbeddingModel(model_name=EMBEDDING_MODEL_NAME)
vector_store    = ChromaVectorStore(persist_path=CHROMA_PATH, collection_name=COLLECTION_NAME)
llm             = AzureOpenAIChatLLM()

# Query audit logger — completely separate from the Chroma vector store.
# It records questions + answers + retrieval metadata.
# It never feeds back into retrieval.
query_logger = get_query_logger()

rag = RAGPipeline(
    file_path=VOLUME_FILE_PATH,
    embedding_model=embedding_model,
    vector_store=vector_store,
    llm=llm,
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    top_k=TOP_K,
    logger=query_logger,
)

# ── Local fallback: ingest every file in data/ ───────────────────────────────

SUPPORTED = {".pdf", ".docx", ".txt", ".csv", ".html"}


def _ingest_local_data_dir():
    from day_09.ingestion.local_loader import extract_pages
    from day_09.core.smart_chunker import route_and_chunk

    files = [f for f in DATA_DIR.iterdir() if f.suffix.lower() in SUPPORTED]
    print(f"Found {len(files)} local files: {[f.name for f in files]}")

    all_chunks = []
    for f in files:
        print(f"  Ingesting {f.name}...")
        pages  = extract_pages(str(f))
        chunks = route_and_chunk(
            pages=pages,
            source_file=str(f),
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP,
            max_article_chars=MAX_ARTICLE_CHARS,
        )
        all_chunks.extend(chunks)
        print(f"    → {len(chunks)} chunks")

    print(f"Embedding {len(all_chunks)} total chunks...")
    texts      = [c["content"] for c in all_chunks]
    embeddings = embedding_model.embed_documents(texts)
    vector_store.add_chunks(chunks=all_chunks, embeddings=embeddings)
    print("Local ingestion complete.")


# ── Startup: populate ChromaDB ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    if vector_store.collection.count() == 0:
        print("ChromaDB is empty — loading chunks from Databricks Delta table...")
        try:
            from day_09.ingestion.delta_loader import load_chunks_from_delta
            chunks     = load_chunks_from_delta()
            texts      = [c["content"] for c in chunks]
            print(f"Embedding {len(chunks)} chunks...")
            embeddings = embedding_model.embed_documents(texts)
            vector_store.add_chunks(chunks=chunks, embeddings=embeddings)
            print("ChromaDB populated. Ready to serve queries.")
        except Exception as e:
            print(f"Warning: could not load from Databricks ({e}). Falling back to local ingestion.")
            _ingest_local_data_dir()
    else:
        print(f"ChromaDB already has {vector_store.collection.count()} chunks. Skipping ingestion.")
    yield


app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
    return {
        "message": "EU RAG API is running",
        "docs": "/docs",
        "endpoints": ["/query", "/query-databricks"],
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

# ── Request / Response models ─────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    question: str
    answer: str
    retrieved_chunks: list


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    try:
        result = rag.ask(request.question)
        return QueryResponse(
            question=result["question"],
            answer=result["answer"],
            retrieved_chunks=result["retrieved_chunks"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/query-databricks", response_model=QueryResponse)
def query_databricks(request: QueryRequest) -> QueryResponse:
    try:
        client = WorkspaceClient()

        results = client.vector_search_indexes.query_index(
            index_name=VECTOR_SEARCH_INDEX,
            columns=["chunk_id", "content", "source_file", "page_number", "chunk_index"],
            query_text=request.question,
            num_results=TOP_K,
        )

        retrieved_chunks = []
        for row in results.result.data_array:
            retrieved_chunks.append({
                "chunk_id": row[0],
                "content": row[1],
                "metadata": {
                    "source_file": row[2],
                    "page_number": row[3],
                    "chunk_index": row[4],
                },
                "distance": None,
            })

        context_blocks = []
        for item in retrieved_chunks:
            meta = item["metadata"]
            context_blocks.append(
                f"Source: {meta['source_file']}\n"
                f"Page: {meta['page_number']}  Chunk: {meta['chunk_index']}\n\n"
                f"{item['content']}"
            )

        context = "\n---\n".join(context_blocks)
        answer = llm.generate(question=request.question, context=context)

        sources = []
        for item in retrieved_chunks:
            meta = item["metadata"]
            source_text = f"{meta['source_file']} (page {meta['page_number']})"
            if source_text not in sources:
                sources.append(source_text)

        answer_with_sources = (
            answer + "\n\nSources:\n- " + "\n- ".join(sources)
            if sources else answer
        )

        return QueryResponse(
            question=request.question,
            answer=answer_with_sources,
            retrieved_chunks=retrieved_chunks,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))