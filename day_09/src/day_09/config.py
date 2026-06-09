from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # on Databricks, env vars come from cluster config, not .env

_HERE = Path(__file__).resolve().parent        # .../src/day_09/
BASE_DIR = _HERE.parent.parent                 # .../day_09/ project root

# ── Local paths ──────────────────────────────────────────────────────────────
DATA_DIR    = BASE_DIR / "data"
PDF_PATH    = BASE_DIR / "data" / "32016R0679_EN.pdf"
# ── Azure AI Search ───────────────────────────────────────────────────────────
AI_SEARCH_ENDPOINT   = os.getenv("AI_SEARCH_ENDPOINT")
AI_SEARCH_API_KEY    = os.getenv("AI_SEARCH_API_KEY")
AI_SEARCH_INDEX_NAME = os.getenv("AI_SEARCH_INDEX_NAME", "eu-regulations")

# Embedding deployment used for both indexing and querying
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")

COLLECTION_NAME      = "pdf_rag_collection"  # kept for reference; no longer used

CHUNK_SIZE        = 500
CHUNK_OVERLAP     = 80
TOP_K             = 5
MAX_ARTICLE_CHARS = int(os.getenv("MAX_ARTICLE_CHARS", "3000"))

# ── Databricks — Unity Catalog ────────────────────────────────────────────────
DELTA_CATALOG = os.getenv("DELTA_CATALOG", "accenture2026dbcks")
DELTA_SCHEMA  = os.getenv("DELTA_SCHEMA",  "team6")
DELTA_TABLE   = os.getenv("DELTA_TABLE",   "eu_chunks")
DELTA_RESULTS_TABLE = os.getenv("DELTA_RESULTS_TABLE", "rag_results")

# Path to the raw file inside the Unity Catalog Volume
# Format: /Volumes/<catalog>/<schema>/<volume_name>/<filename>
VOLUME_FILE_PATH = os.getenv(
    "VOLUME_FILE_PATH",
    f"/Volumes/{DELTA_CATALOG}/{DELTA_SCHEMA}/volume/pdfs/32016R0679_EN.pdf",
)

# ── Databricks — Enriched table (chunks + pre-computed embeddings) ────────────
DELTA_ENRICHED_TABLE = os.getenv("DELTA_ENRICHED_TABLE", "eu_chunks_enriched")

# Databricks Foundation Model API embedding endpoint + output dimension
EMBEDDING_ENDPOINT  = os.getenv("EMBEDDING_ENDPOINT", "databricks-gte-large-en")
EMBEDDING_DIMENSION = 1024  # databricks-gte-large-en output size

# ── Databricks — Vector Search ────────────────────────────────────────────────
VECTOR_SEARCH_ENDPOINT = os.getenv("VECTOR_SEARCH_ENDPOINT", "rag-endpoint")
VECTOR_SEARCH_INDEX    = os.getenv(
    "VECTOR_SEARCH_INDEX",
    f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{DELTA_ENRICHED_TABLE}_index",
)

# ── Query audit log ───────────────────────────────────────────────────────────
# LOG_BACKEND controls which QueryLogger implementation get_query_logger() returns.
# "sqlite"     → SqliteQueryLogger  (local file, no extra deps, works right now)
# "databricks" → DatabricksQueryLogger (skeleton; deploy separately)
LOG_BACKEND  = os.getenv("LOG_BACKEND", "sqlite")
QUERY_LOG_DB = BASE_DIR / "query_log.db"  # only used when LOG_BACKEND="sqlite"

# ── Azure OpenAI ──────────────────────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT        = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY         = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION     = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")



VECTOR_SEARCH_INDEX = "accenture2026dbcks.team6.team6_panos_index"