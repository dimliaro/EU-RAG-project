"""
# fastapi server

ragAPI.py

cd src
uvicorn ragAPI:app --reload
"""


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from day_09.embeddings import LocalEmbeddingModel
from day_09.llm import AzureOpenAIChatLLM
from day_09.rag_pipeline import RAGPipeline
from day_09.config import (
    PDF_PATH,
    CHROMA_PATH,
    COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TOP_K,
)
from day_09.vector_store import ChromaVectorStore

app = FastAPI()



#add cors middleware to allow requests from frontend
from fastapi.middleware.cors import CORSMiddleware


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

embedding_model = LocalEmbeddingModel(
        model_name=EMBEDDING_MODEL_NAME,
    )
vector_store = ChromaVectorStore(
        persist_path=CHROMA_PATH,
        collection_name=COLLECTION_NAME,
    )

llm = AzureOpenAIChatLLM()
rag = RAGPipeline(
        pdf_path=PDF_PATH,
        embedding_model=embedding_model,
        vector_store=vector_store,
        llm=llm,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        top_k=TOP_K,
    )

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    question: str
    answer: str
    retrieved_chunks: list


@app.post("/query")
def query(request: QueryRequest)-> QueryResponse:
    try:
        result = rag.ask(request.question)
        print("\nQUESTION:")
        return QueryResponse(
            question=result["question"],
            answer=result["answer"],
            retrieved_chunks=result["retrieved_chunks"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    





