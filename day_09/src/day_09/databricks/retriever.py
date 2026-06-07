"""
Queries a Databricks Vector Search index at query time.

The Vector Search index is created on top of the chunks Delta table
and auto-syncs as new chunks are written.

Setup (one-time, in Databricks UI or SDK):
    1. Create a Vector Search endpoint
    2. Create a Delta Sync index on the chunks table
    3. Set VECTOR_SEARCH_ENDPOINT and VECTOR_SEARCH_INDEX in .env
"""

import os
from databricks.vector_search.client import VectorSearchClient


class DatabricksVectorStore:
    def __init__(
        self,
        endpoint_name: str,
        index_name: str,
        columns: list[str] | None = None,
    ):
        self.client = VectorSearchClient()
        self.index = self.client.get_index(
            endpoint_name=endpoint_name,
            index_name=index_name,
        )
        self.columns = columns or ["chunk_id", "content", "source_file", "page_number", "chunk_index"]

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        results = self.index.similarity_search(
            query_vector=query_embedding,
            columns=self.columns,
            num_results=top_k,
        )

        retrieved = []
        for row in results.get("result", {}).get("data_array", []):
            col_map = dict(zip(self.columns, row))
            retrieved.append(
                {
                    "chunk_id": col_map.get("chunk_id", ""),
                    "content": col_map.get("content", ""),
                    "metadata": {
                        "source_file": col_map.get("source_file", ""),
                        "page_number": col_map.get("page_number", 0),
                        "chunk_index": col_map.get("chunk_index", 0),
                    },
                    "distance": row[-1] if len(row) > len(self.columns) else None,
                }
            )

        return retrieved
