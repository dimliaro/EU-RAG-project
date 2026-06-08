"""
FastAPI server for the RAG pipeline.

Run:
    cd day_09/
    uv run uvicorn src.day_09.api.app:app --reload --port 8080
"""

from contextlib import asynccontextmanager

from databricks.sdk import WorkspaceClient
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
    VECTOR_SEARCH_INDEX,
    VOLUME_FILE_PATH,
)
from day_09.core.embeddings import LocalEmbeddingModel
from day_09.core.llm import AzureOpenAIChatLLM
from day_09.core.rag_pipeline import RAGPipeline
from day_09.core.vector_store import ChromaVectorStore


# Shared components
embedding_model = LocalEmbeddingModel(model_name=EMBEDDING_MODEL_NAME)
vector_store = ChromaVectorStore(
    persist_path=CHROMA_PATH,
    collection_name=COLLECTION_NAME,
)
llm = AzureOpenAIChatLLM()

rag = RAGPipeline(
    file_path=VOLUME_FILE_PATH,
    embedding_model=embedding_model,
    vector_store=vector_store,
    llm=llm,
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    top_k=TOP_K,
)


SUPPORTED = {".pdf", ".docx", ".txt", ".csv", ".html"}


def _ingest_local_data_dir():
    from day_09.core.chunking import create_chunks
    from day_09.ingestion.local_loader import extract_pages

    files = [f for f in DATA_DIR.iterdir() if f.suffix.lower() in SUPPORTED]
    print(f"Found {len(files)} local files: {[f.name for f in files]}")

    all_chunks = []

    for f in files:
        print(f"  Ingesting {f.name}...")
        pages = extract_pages(str(f))
        chunks = create_chunks(
            pages=pages,
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP,
        )
        all_chunks.extend(chunks)
        print(f"    -> {len(chunks)} chunks")

    print(f"Embedding {len(all_chunks)} total chunks...")
    texts = [c["content"] for c in all_chunks]
    embeddings = embedding_model.embed_documents(texts)
    vector_store.add_chunks(chunks=all_chunks, embeddings=embeddings)
    print("Local ingestion complete.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if vector_store.collection.count() == 0:
        print("ChromaDB is empty -- loading chunks from Databricks Delta table...")

        try:
            from day_09.ingestion.delta_loader import load_chunks_from_delta

            chunks = load_chunks_from_delta()
            texts = [c["content"] for c in chunks]

            print(f"Embedding {len(chunks)} chunks...")
            embeddings = embedding_model.embed_documents(texts)

            vector_store.add_chunks(chunks=chunks, embeddings=embeddings)
            print("ChromaDB populated. Ready to serve queries.")

        except Exception as e:
            print(
                f"Warning: could not load from Databricks ({e}). "
                "Falling back to local ingestion."
            )
            _ingest_local_data_dir()

    else:
        print(
            f"ChromaDB already has {vector_store.collection.count()} chunks. "
            "Skipping ingestion."
        )

    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    retrieved_chunks: list


@app.get("/")
def root():
    return {
        "message": "EU RAG API is running",
        "docs": "/docs",
        "endpoints": ["/query", "/query-databricks"],
    }


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
            columns=[
                "chunk_id",
                "content",
                "source_file",
                "page_number",
                "chunk_index",
            ],
            query_text=request.question,
            num_results=TOP_K,
        )

        retrieved_chunks = []

        for row in results.result.data_array:
            retrieved_chunks.append(
                {
                    "chunk_id": row[0],
                    "content": row[1],
                    "metadata": {
                        "source_file": row[2],
                        "page_number": row[3],
                        "chunk_index": row[4],
                    },
                    "distance": None,
                }
            )

        context_blocks = []

        for item in retrieved_chunks:
            meta = item["metadata"]
            context_blocks.append(
                f"Source: {meta['source_file']}\n"
                f"Page: {meta['page_number']}  Chunk: {meta['chunk_index']}\n\n"
                f"{item['content']}"
            )

        context = "\n---\n".join(context_blocks)

        answer = llm.generate(
            question=request.question,
            context=context,
        )

        sources = []

        for item in retrieved_chunks:
            meta = item["metadata"]
            source_text = f"{meta['source_file']} (page {meta['page_number']})"

            if source_text not in sources:
                sources.append(source_text)

        if sources:
            answer_with_sources = (
                answer
                + "\n\nSources:\n- "
                + "\n- ".join(sources)
            )
        else:
            answer_with_sources = answer

        return QueryResponse(
            question=request.question,
            answer=answer_with_sources,
            retrieved_chunks=retrieved_chunks,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
