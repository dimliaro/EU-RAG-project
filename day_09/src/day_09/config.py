from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

PDF_PATH = BASE_DIR / "data" / "katataxi.pdf"
CHROMA_PATH = BASE_DIR / "chroma_db"

COLLECTION_NAME = "pdf_rag_collection"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

 
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80
TOP_K = 5 

AZURE_OPENAI_ENDPOINT=os.getenv("AZURE_OPENAI_ENDPOINT"),
AZURE_OPENAI_API_KEY=os.getenv("AZURE_OPENAI_API_KEY"),
AZURE_OPENAI_API_VERSION=os.getenv("AZURE_OPENAI_API_VERSION"),
AZURE_OPENAI_DEPLOYMENT_NAME=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),