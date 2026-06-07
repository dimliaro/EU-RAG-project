from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

_HERE = Path(__file__).resolve().parent        # .../src/day_09/
BASE_DIR = _HERE.parent.parent                 # .../day_09/ project root

# ── Local paths ──────────────────────────────────────────────────────────────
PDF_PATH    = BASE_DIR / "data" / "32016R0679_EN.pdf"
CHROMA_PATH = _HERE / "chroma_db"

COLLECTION_NAME      = "pdf_rag_collection"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


CHUNK_SIZE    = 500
CHUNK_OVERLAP = 80
TOP_K         = 5

# ── Databricks — Unity Catalog ────────────────────────────────────────────────
DELTA_CATALOG = os.getenv("DELTA_CATALOG", "accenture2026dbcks")
DELTA_SCHEMA  = os.getenv("DELTA_SCHEMA",  "team6")
DELTA_TABLE   = os.getenv("DELTA_TABLE",   "eu_chunks")
DELTA_RESULTS_TABLE = os.getenv("DELTA_RESULTS_TABLE", "rag_results")

# Path to the raw file inside the Unity Catalog Volume
# Format: /Volumes/<catalog>/<schema>/<volume_name>/<filename>
VOLUME_FILE_PATH = os.getenv(
    "VOLUME_FILE_PATH",
    f"/Volumes/{DELTA_CATALOG}/{DELTA_SCHEMA}/files/32016R0679_EN.pdf",
)

# ── Databricks — Vector Search ────────────────────────────────────────────────
VECTOR_SEARCH_ENDPOINT = os.getenv("VECTOR_SEARCH_ENDPOINT", "rag-endpoint")
VECTOR_SEARCH_INDEX    = os.getenv(
    "VECTOR_SEARCH_INDEX",
    f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{DELTA_TABLE}_index",
)

# ── Azure OpenAI ──────────────────────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT        = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY         = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION     = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
