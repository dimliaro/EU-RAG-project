"""
Azure AI Search vector store.

The index is created automatically on first run via create_if_not_exists().
Schema: chunk_id (key), chunk_text, embedding (1536 dims).
"""

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery


class AISearchVectorStore:
    METADATA_FIELDS = [
        "source_file",
        "page_number",
        "chunk_index",
        "doc_kind",
        "structure_type",
        "number",
        "chapter",
        "title",
        "regulation",
    ]

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
            SimpleField(
                name="source_file",
                type=SearchFieldDataType.String,
                retrievable=True,
                filterable=True,
            ),
            SimpleField(
                name="page_number",
                type=SearchFieldDataType.Int32,
                retrievable=True,
                filterable=True,
            ),
            SimpleField(
                name="chunk_index",
                type=SearchFieldDataType.Int32,
                retrievable=True,
                filterable=True,
            ),
            SimpleField(
                name="doc_kind",
                type=SearchFieldDataType.String,
                retrievable=True,
                filterable=True,
            ),
            SimpleField(
                name="structure_type",
                type=SearchFieldDataType.String,
                retrievable=True,
                filterable=True,
            ),
            SimpleField(
                name="number",
                type=SearchFieldDataType.Int32,
                retrievable=True,
                filterable=True,
            ),
            SimpleField(
                name="chapter",
                type=SearchFieldDataType.String,
                retrievable=True,
                filterable=True,
            ),
            SimpleField(
                name="title",
                type=SearchFieldDataType.String,
                retrievable=True,
                filterable=True,
            ),
            SimpleField(
                name="regulation",
                type=SearchFieldDataType.String,
                retrievable=True,
                filterable=True,
            ),
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

    @classmethod
    def delete_if_exists(cls, endpoint: str, api_key: str, index_name: str):
        from azure.search.documents.indexes import SearchIndexClient

        idx_client = SearchIndexClient(endpoint, AzureKeyCredential(api_key))
        existing = list(idx_client.list_index_names())

        if index_name in existing:
            idx_client.delete_index(index_name)
            print(f"Deleted index '{index_name}'.")

    def count(self) -> int:
        results = self.client.search("*", top=0, include_total_count=True)
        return results.get_count() or 0

    def add_chunks(self, chunks: list[dict], embeddings: list[list[float]]):
        print("Uploading metadata-aware smart chunks to Azure AI Search")
        documents = [
            self._to_search_document(chunk, embedding)
            for chunk, embedding in zip(chunks, embeddings)
        ]
        self.client.upload_documents(documents=documents)
        print(f"Uploaded {len(documents)} chunks to Azure AI Search.")

    def _to_search_document(self, chunk, embedding: list[float]) -> dict:
        metadata = self._metadata(chunk)
        document = {
            "chunk_id": str(self._get_value(chunk, "chunk_id") or ""),
            "chunk_text": str(self._get_value(chunk, "content") or self._get_value(chunk, "page_content") or ""),
            "embedding": embedding,
        }

        for field in self.METADATA_FIELDS:
            value = metadata.get(field, self._get_value(chunk, field))
            if field in {"page_number", "chunk_index", "number"}:
                document[field] = self._coerce_int(value)
            else:
                document[field] = self._coerce_str(value)

        return document

    def _metadata(self, chunk) -> dict:
        if isinstance(chunk, dict):
            metadata = chunk.get("metadata", {})
            return metadata if isinstance(metadata, dict) else {}
        metadata = getattr(chunk, "metadata", {})
        return metadata if isinstance(metadata, dict) else {}

    def _get_value(self, chunk, field: str):
        if isinstance(chunk, dict):
            return chunk.get(field)
        return getattr(chunk, field, None)

    def _coerce_int(self, value):
        if value in (None, ""):
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def _coerce_str(self, value):
        if value in (None, ""):
            return None
        return str(value)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        query_text: str | None = None,
    ) -> list[dict]:
        print(
            "Azure AI Search retrieval: "
            f"backend=Azure AI Search mode=hybrid query={query_text!r} top_k={top_k}"
        )
        results = self.client.search(
            search_text=query_text,
            vector_queries=[
                VectorizedQuery(
                    vector=query_embedding,
                    k_nearest_neighbors=top_k,
                    fields="embedding",
                )
            ],
            top=top_k,
        )

        retrieved = []
        for row in results:
            score = row.get("@search.reranker_score")
            if score is None:
                score = row.get("@search.score", 0.0)
            metadata = {field: row.get(field) for field in self.METADATA_FIELDS}
            retrieved.append(
                {
                    "chunk_id": row["chunk_id"],
                    "content": row["chunk_text"],
                    "metadata": metadata,
                    "distance": score,
                }
            )
        return retrieved
