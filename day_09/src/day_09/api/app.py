"""
FastAPI server for the RAG pipeline.

Run:
    cd day_09/
    uv run uvicorn src.day_09.api.app:app --reload --port 8080
"""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from day_09.config import (
    AI_SEARCH_API_KEY,
    AI_SEARCH_ENDPOINT,
    AI_SEARCH_INDEX_NAME,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    AZURE_OPENAI_EMBEDDING_DIMENSION,
    AZURE_OPENAI_ENDPOINT,
    BASE_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DATA_DIR,
    MAX_ARTICLE_CHARS,
    RESET_AI_SEARCH_INDEX,
    TOP_K,
    VOLUME_FILE_PATH,
)
from day_09.core.embeddings import AzureOpenAIEmbeddingModel
from day_09.core.llm import AzureOpenAIChatLLM
from day_09.core.query_logger import get_query_logger
from day_09.core.rag_pipeline import RAGPipeline
from day_09.core.vector_store import AISearchVectorStore


def _validate_azure_environment() -> None:
    required = {
        "AI_SEARCH_ENDPOINT": AI_SEARCH_ENDPOINT,
        "AI_SEARCH_API_KEY": AI_SEARCH_API_KEY,
        "AI_SEARCH_INDEX_NAME": AI_SEARCH_INDEX_NAME,
        "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
        "AZURE_OPENAI_API_KEY": AZURE_OPENAI_API_KEY,
        "AZURE_OPENAI_API_VERSION": AZURE_OPENAI_API_VERSION,
        "AZURE_OPENAI_DEPLOYMENT_NAME": AZURE_OPENAI_DEPLOYMENT_NAME,
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(
            "Azure AI Search / Azure OpenAI configuration is incomplete. "
            "Missing environment variables: " + ", ".join(missing)
        )


def _has_databricks_environment() -> bool:
    has_host_token = bool(os.getenv("DATABRICKS_HOST") and os.getenv("DATABRICKS_TOKEN"))
    has_profile = bool(os.getenv("DATABRICKS_CONFIG_PROFILE"))
    return has_host_token or has_profile


# Shared components
_validate_azure_environment()

print("Retrieval backend: Azure AI Search")
print(f"Azure AI Search index: {AI_SEARCH_INDEX_NAME}")
print(f"Azure embedding deployment: {AZURE_OPENAI_EMBEDDING_DEPLOYMENT}")
print(f"Azure embedding dimension: {AZURE_OPENAI_EMBEDDING_DIMENSION}")
print("Databricks Vector Search is lazy and not required for /query startup.")

embedding_model = AzureOpenAIEmbeddingModel(
    endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    deployment=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
)
vector_store = AISearchVectorStore(
    endpoint=AI_SEARCH_ENDPOINT,
    api_key=AI_SEARCH_API_KEY,
    index_name=AI_SEARCH_INDEX_NAME,
)
llm = AzureOpenAIChatLLM()

# Query audit logger — completely separate from the retrieval vector store.
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


SUPPORTED = {".pdf", ".docx", ".txt", ".csv", ".html"}


def _is_evaluation_file(path) -> bool:
    return path.name == "evaluation_questions.csv" or path.name.startswith("evaluation_")


def _ingest_local_data_dir():
    from day_09.core.chunking import create_chunks
    from day_09.core.smart_chunker import route_and_chunk
    from day_09.ingestion.local_loader import extract_pages

    candidates = [f for f in DATA_DIR.iterdir() if f.suffix.lower() in SUPPORTED]
    skipped = [f for f in candidates if _is_evaluation_file(f)]
    files = [f for f in candidates if not _is_evaluation_file(f)]

    if skipped:
        print(f"Skipped evaluation files: {[f.name for f in skipped]}")
    print(f"Found {len(files)} local files: {[f.name for f in files]}")

    all_chunks = []
    for f in files:
        print(f"  Ingesting {f.name}...")
        pages = extract_pages(str(f))
        try:
            chunks = route_and_chunk(
                pages=pages,
                source_file=str(f),
                chunk_size=CHUNK_SIZE,
                overlap=CHUNK_OVERLAP,
                max_article_chars=MAX_ARTICLE_CHARS,
            )
        except Exception as e:
            print(f"  Warning: smart chunker failed ({e}). Falling back.")
            chunks = create_chunks(pages=pages, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        all_chunks.extend(chunks)
        print(f"    -> {len(chunks)} chunks")

    print(f"Files ingested: {len(files)}")
    print(f"Embedding {len(all_chunks)} total chunks...")
    texts = [c["content"] for c in all_chunks]
    embeddings = embedding_model.embed_documents(texts)
    vector_store.add_chunks(chunks=all_chunks, embeddings=embeddings)
    print("Ingestion complete.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if RESET_AI_SEARCH_INDEX:
        print("RESET_AI_SEARCH_INDEX=true: deleting and recreating Azure AI Search index")
        AISearchVectorStore.delete_if_exists(
            AI_SEARCH_ENDPOINT,
            AI_SEARCH_API_KEY,
            AI_SEARCH_INDEX_NAME,
        )

    AISearchVectorStore.create_if_not_exists(
        AI_SEARCH_ENDPOINT, AI_SEARCH_API_KEY, AI_SEARCH_INDEX_NAME,
        dimensions=AZURE_OPENAI_EMBEDDING_DIMENSION,
    )
    if vector_store.count() == 0:
        print("Index is empty — ingesting local data...")
        _ingest_local_data_dir()
    else:
        print(f"Index '{AI_SEARCH_INDEX_NAME}' ready.")
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
    return FileResponse(BASE_DIR / "frontend" / "rag.html")


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
        if not _has_databricks_environment():
            raise HTTPException(
                status_code=503,
                detail=(
                    "Databricks Vector Search is not configured. "
                    "Set DATABRICKS_HOST and DATABRICKS_TOKEN, or "
                    "DATABRICKS_CONFIG_PROFILE, before calling /query-databricks."
                ),
            )

        try:
            from day_09.retrieval.databricks_retriever import (
                DatabricksVectorSearchRetriever,
            )

            databricks_retriever = DatabricksVectorSearchRetriever()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Databricks Vector Search is not configured. "
                    "Set Databricks credentials before calling /query-databricks. "
                    f"Original error: {e}"
                ),
            ) from e

        retrieved_chunks = databricks_retriever.retrieve(
            request.question
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
