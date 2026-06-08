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

        # Pass every field except chunk_id and content as metadata so that
        # regulation-specific fields (structure_type, number, regulation, …)
        # survive into retrieval for citations and metadata filtering.
        # ChromaDB only accepts str | int | float | bool — convert anything
        # else (including None) to an empty string.
        _skip = {"chunk_id", "content"}
        metadatas = [
            {
                k: (v if isinstance(v, (str, int, float, bool)) else "")
                for k, v in chunk.items()
                if k not in _skip
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
