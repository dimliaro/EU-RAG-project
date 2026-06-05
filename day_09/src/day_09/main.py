

from day_09.embeddings import LocalEmbeddingModel
from day_09.config import EMBEDDING_MODEL_NAME
from day_09.llm import AzureOpenAIChatLLM
from day_09.vector_store import ChromaVectorStore


prompt = "What are my rights as a person under the GDPR?"
embedding_model = LocalEmbeddingModel(model_name=EMBEDDING_MODEL_NAME)
query_embedding = embedding_model.embed_query(prompt) 

vector_store = ChromaVectorStore(persist_path="chroma_db", collection_name="pdf_rag_collection")

search_results = vector_store.search(query_embedding=query_embedding, top_k=5)

llm = AzureOpenAIChatLLM()

context = "\n\n".join([result["content"] for result in search_results])


retrieved = llm.generate(prompt,context)

print("Retrieved answer:")
print(retrieved)
  