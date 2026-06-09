from databricks.sdk import WorkspaceClient

from day_09.config import TOP_K


class DatabricksVectorSearchRetriever:
    def __init__(
        self,
        index_name: str = "accenture2026dbcks.team6.team6_panos_index",
        top_k: int = TOP_K,
    ):
        self.index_name = index_name
        self.top_k = top_k
        self.client = WorkspaceClient()

    def retrieve(self, question: str) -> list[dict]:
        results = self.client.vector_search_indexes.query_index(
            index_name=self.index_name,
            columns=["id", "content", "source_file", "page_number", "chunk_index"],
            query_text=question,
            num_results=self.top_k,
        )

        retrieved_chunks = []

        for row in results.result.data_array:
            retrieved_chunks.append(
                {
                    "chunk_id": row[0],
                    "content": row[1],
                    "metadata": {
                        "source_file": row[2],
                        "page_number": int(float(row[3])),
                        "chunk_index": int(float(row[4])),
                    },
                    "distance": None,
                }
            )

        return retrieved_chunks