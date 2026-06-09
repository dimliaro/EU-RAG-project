"""
Azure OpenAI embedding model.
"""

from openai import AzureOpenAI


class AzureOpenAIEmbeddingModel:

    def __init__(self, endpoint: str, api_key: str, api_version: str, deployment: str):
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        self.deployment = deployment

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        # Azure caps batch size — process in chunks of 100
        for i in range(0, len(texts), 100):
            batch = texts[i : i + 100]
            response = self.client.embeddings.create(model=self.deployment, input=batch)
            embeddings.extend(item.embedding for item in response.data)
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.deployment, input=text)
        return response.data[0].embedding
