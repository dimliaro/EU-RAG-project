
#test ingestion
from pathlib import Path
import day_09
from day_09.pdf_ingestions import extract_pdf_pages
from day_09.chunking import create_chunks
from day_09.config import PDF_PATH, CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL_NAME, TOP_K, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT_NAME
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if __name__ == "__main__":
    pdf_path = PROJECT_ROOT / "data" / "32016R0679_EN.pdf"
    pages = extract_pdf_pages(pdf_path)

    
    for page in pages:
        print(f"Page {page['page_number']}:")
        print(page["text"][:200])  # Print the first 200 characters of each page
        print("-" * 50)

   

    #test chunking
   
    chunks = create_chunks(pages, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}: {chunk}\n")

    #test embeddings
    from day_09.embeddings import LocalEmbeddingModel


    prompt = """
    What are my rights as a consumer under the GDPR?"""

    embedding_model = LocalEmbeddingModel(model_name=EMBEDDING_MODEL_NAME)
    document_embeddings = embedding_model.embed_documents([chunk["content"] for chunk in chunks])
   
   
    # query_embedding = embedding_model.embed_query(prompt)
    # print("Document Embeddings:")
    # for i, embedding in enumerate(document_embeddings):
    #     print(f"Chunk {i+1} Embedding: {embedding[:5]}...")  # Print the first 5 dimensions of each embedding
    # print("\nQuery Embedding:")
    # print(query_embedding[:5])  # Print the first 5 dimensions of the query embedding       
    

    #test vector store
    from day_09.vector_store import ChromaVectorStore

    vector_store = ChromaVectorStore(persist_path="chroma_db", collection_name="pdf_rag_collection")
    vector_store.add_chunks(chunks, document_embeddings)

    query_embedding = embedding_model.embed_query(prompt) 
    search_results = vector_store.search(query_embedding=query_embedding, top_k=TOP_K+2)
    print("\nSearch Results:")
    for index, result in enumerate(search_results):
        print(f"Result {index + 1}:")
        print(f"Document: {result['content']}")
        print(f"Metadata: {result['metadata']}")
        print(f"Distance: {result['distance']}")
        print("-" * 50)