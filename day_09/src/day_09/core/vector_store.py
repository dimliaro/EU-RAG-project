"""
Azure AI Search vector store.

Required index schema (create once in Azure portal or via SDK):
  - chunk_id      : Edm.String  (key, retrievable)
  - chunk_text    : Edm.String  (retrievable, searchable)
  - embedding     : Collection(Edm.Single)  (vector, dimensions match your embedding model)
  - metadata_json : Edm.String  (retrievable)
"""

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery


class AISearchVectorStore:
    def __init__(self, endpoint: str, api_key: str, index_name: str):
        self.client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(api_key),
        )

    def add_chunks(self, chunks: list[dict], embeddings: list[list[float]]):
        documents = [
            {
                "chunk_id": chunk["chunk_id"],
                "chunk_text": chunk["content"],
                "embedding": embedding,
                "metadata_json": json.dumps(
                    {
                        k: v
                        for k, v in chunk.items()
                        if k not in {"chunk_id", "content"}
                        and isinstance(v, (str, int, float, bool))
                    }
                ),
            }
            for chunk, embedding in zip(chunks, embeddings)
        ]
        self.client.upload_documents(documents=documents)

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        results = self.client.search(
            search_text=None,
            vector_queries=[
                VectorizedQuery(
                    vector=query_embedding,
                    k_nearest_neighbors=top_k,
                    fields="embedding",
                )
            ],
            select=["chunk_id", "chunk_text"],
        )

        retrieved = []
        for row in results:
            retrieved.append(
                {
                    "chunk_id": row["chunk_id"],
                    "content": row["chunk_text"],
                    "metadata": {},
                    "distance": row.get("@search.score", 0.0),
                }
            )
        return retrieved
