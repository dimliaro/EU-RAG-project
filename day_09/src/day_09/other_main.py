"""
file: src/mainprogram.py


"""

from day_09.config import (
    PDF_PATH,
    CHROMA_PATH,
    COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TOP_K,
)

from day_09.embeddings import LocalEmbeddingModel
from day_09.vector_store import ChromaVectorStore
from day_09.llm import AzureOpenAIChatLLM
from day_09.rag_pipeline import RAGPipeline


def main():
    embedding_model = LocalEmbeddingModel(
        model_name=EMBEDDING_MODEL_NAME,
    )

    vector_store = ChromaVectorStore(
        persist_path=CHROMA_PATH,
        collection_name=COLLECTION_NAME,
    )

    llm = AzureOpenAIChatLLM()

    rag = RAGPipeline(
        file_path=PDF_PATH,
        embedding_model=embedding_model,
        vector_store=vector_store,
        llm=llm,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        top_k=TOP_K,
    )

    if vector_store.collection.count() == 0:
        rag.ingest()
    else:
        print("Collection already populated, skipping ingestion.")

    question = "Summarize the main points of the document."

    result = rag.ask(question)

    print("\nQUESTION:")
    print(result["question"])

    print("\nANSWER:")
    print(result["answer"])

    print("\nSOURCES:")
    for item in result["retrieved_chunks"]:
        print(
            f"Page {item['metadata']['page_number']} | "
            f"Chunk {item['metadata']['chunk_index']} | "
            f"Distance: {item['distance']}"
        )







if __name__ == "__main__":
    main()
  
    
    
    