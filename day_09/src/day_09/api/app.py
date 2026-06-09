"""
FastAPI server for the RAG pipeline.

Run:
    cd day_09/
    uv run uvicorn src.day_09.api.app:app --reload --port 8080
"""

from contextlib import asynccontextmanager

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
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    AZURE_OPENAI_ENDPOINT,
    BASE_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    TOP_K,
    VOLUME_FILE_PATH,
)
from day_09.core.embeddings import AzureOpenAIEmbeddingModel
from day_09.core.llm import AzureOpenAIChatLLM
from day_09.core.query_logger import get_query_logger
from day_09.core.rag_pipeline import RAGPipeline
from day_09.core.vector_store import AISearchVectorStore
from day_09.retrieval.databricks_retriever import (
    DatabricksVectorSearchRetriever,
)


# Shared components
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
databricks_retriever = DatabricksVectorSearchRetriever()

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # AI Search index is persistent in Azure — no startup ingestion needed.
    # To populate the index run: uv run python -m day_09.ingestion.ingest
    print("AI Search vector store ready.")
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
