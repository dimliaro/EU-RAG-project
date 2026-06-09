"""
Azure AI Search vector store.

The index is created automatically on first run via create_if_not_exists().
Schema: chunk_id (key), chunk_text, embedding (1536 dims).
"""

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery


class AISearchVectorStore:
    def __init__(self, endpoint: str, api_key: str, index_name: str):
        self.endpoint = endpoint
        self.api_key = api_key
        self.index_name = index_name
        self.client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(api_key),
        )

    @classmethod
    def create_if_not_exists(cls, endpoint: str, api_key: str, index_name: str, dimensions: int = 1536):
        from azure.search.documents.indexes import SearchIndexClient
        from azure.search.documents.indexes.models import (
            HnswAlgorithmConfiguration,
            SearchField,
            SearchFieldDataType,
            SearchIndex,
            SearchableField,
            SimpleField,
            VectorSearch,
            VectorSearchProfile,
        )

        idx_client = SearchIndexClient(endpoint, AzureKeyCredential(api_key))
        existing = list(idx_client.list_index_names())

        if index_name in existing:
            print(f"Index '{index_name}' already exists.")
            return

        fields = [
            SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True, retrievable=True),
            SearchableField(name="chunk_text", type=SearchFieldDataType.String, retrievable=True),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=dimensions,
                vector_search_profile_name="default-profile",
            ),
        ]

        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="default-algo")],
            profiles=[VectorSearchProfile(name="default-profile", algorithm_configuration_name="default-algo")],
        )

        idx_client.create_index(SearchIndex(name=index_name, fields=fields, vector_search=vector_search))
        print(f"Created index '{index_name}'.")

    def count(self) -> int:
        results = self.client.search("*", top=0, include_total_count=True)
        return results.get_count() or 0

    def add_chunks(self, chunks: list[dict], embeddings: list[list[float]]):
        documents = [
            {
                "chunk_id": chunk["chunk_id"],
                "chunk_text": chunk["content"],
                "embedding": embedding,
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
