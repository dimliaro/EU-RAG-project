"""
ragAPI.py — FastAPI server

Startup flow:
  1. Load components (embedding model, ChromaDB, LLM)
  2. If ChromaDB is empty → read chunks from Databricks Delta table → embed → store
  3. POST /query: embed question → search ChromaDB → call LLM → return answer

Run:
    cd day_09/
    uv run uvicorn day_09.ragAPI:app --host 0.0.0.0 --port 8001 --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from day_09.config import (
    CHROMA_PATH,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DATA_DIR,
    EMBEDDING_MODEL_NAME,
    TOP_K,
    VOLUME_FILE_PATH,
)
from day_09.embeddings import LocalEmbeddingModel
from day_09.llm import AzureOpenAIChatLLM
from day_09.rag_pipeline import RAGPipeline
from day_09.vector_store import ChromaVectorStore

# ── Shared components (defined first so lifespan can reference them) ──────────

embedding_model = LocalEmbeddingModel(model_name=EMBEDDING_MODEL_NAME)
vector_store    = ChromaVectorStore(persist_path=CHROMA_PATH, collection_name=COLLECTION_NAME)
llm             = AzureOpenAIChatLLM()

rag = RAGPipeline(
    file_path=VOLUME_FILE_PATH,
    embedding_model=embedding_model,
    vector_store=vector_store,
    llm=llm,
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    top_k=TOP_K,
)

# ── Local fallback: ingest every file in data/ ───────────────────────────────

SUPPORTED = {".pdf", ".docx", ".txt", ".csv", ".html"}

def _ingest_local_data_dir():
    from day_09.pdf_ingestions import extract_pages
    from day_09.chunking import create_chunks

    files = [f for f in DATA_DIR.iterdir() if f.suffix.lower() in SUPPORTED]
    print(f"Found {len(files)} local files: {[f.name for f in files]}")

    all_chunks = []
    for f in files:
        print(f"  Ingesting {f.name}...")
        pages  = extract_pages(str(f))
        chunks = create_chunks(pages=pages, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
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
            from day_09.all_type_loader import load_chunks_from_delta
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
