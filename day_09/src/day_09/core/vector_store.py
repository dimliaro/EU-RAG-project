"""
Local Chroma vector database.

Later in Databricks, replace this class with:
- Databricks VectorSearchClient
- Databricks AI Search index
"""

import chromadb
from chromadb.config import Settings


class ChromaVectorStore:
    def __init__(self, persist_path: str, collection_name: str):
        self.client = chromadb.PersistentClient(
            path=str(persist_path),
            settings=Settings(anonymized_telemetry=False),
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[dict], embeddings: list[list[float]]):
        ids = [chunk["chunk_id"] for chunk in chunks]
        documents = [chunk["content"] for chunk in chunks]

        metadatas = [
            {
                "source_file": chunk["source_file"],
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
            }
            for chunk in chunks
        ]

        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict[str, str | int | float]]:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        retrieved = []

        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for i in range(len(ids)):
            retrieved.append(
                {
                    "chunk_id": ids[i],
                    "content": documents[i],
                    "metadata": metadatas[i],
                    "distance": distances[i],
                }
            )

        return retrieved
