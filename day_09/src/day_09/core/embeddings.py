"""
Local embedding model using SentenceTransformer.

In a Databricks environment, replace this class with calls to the
Databricks Foundation Model API or Azure OpenAI embeddings.
"""

from sentence_transformers import SentenceTransformer


class LocalEmbeddingModel:
    """
    Local embedding model.

    Later in Databricks, replace this class with:
    - ai_query('databricks-gte-large-en', content)
    - Databricks Foundation Model API
    - Azure OpenAI embeddings
    """

    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
        )

        return embedding.tolist()
