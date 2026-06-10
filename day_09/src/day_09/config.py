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
RESET_AI_SEARCH_INDEX = os.getenv("RESET_AI_SEARCH_INDEX", "false").lower() == "true"

# Embedding deployment used for both indexing and querying
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
AZURE_OPENAI_EMBEDDING_DIMENSION = int(
    os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSION", "1536")
)

# Backward-compatible alias for the primary Azure retrieval backend.
EMBEDDING_DIMENSION = AZURE_OPENAI_EMBEDDING_DIMENSION

COLLECTION_NAME      = "pdf_rag_collection"  # kept for reference; no longer used

CHUNK_SIZE        = 500
CHUNK_OVERLAP     = 80
TOP_K             = 5
MAX_ARTICLE_CHARS = int(os.getenv("MAX_ARTICLE_CHARS", "3000"))

# ── Databricks — Unity Catalog ────────────────────────────────────────────────
DELTA_CATALOG = os.getenv("DELTA_CATALOG", "accenture2026dbcks")
DELTA_SCHEMA  = os.getenv("DELTA_SCHEMA",  "team6")
RAW_DOCUMENTS_VOLUME = os.getenv("RAW_DOCUMENTS_VOLUME", "volume")
RAW_PDF_VOLUME_DIR = os.getenv(
    "RAW_PDF_VOLUME_DIR",
    f"/Volumes/{DELTA_CATALOG}/{DELTA_SCHEMA}/{RAW_DOCUMENTS_VOLUME}/pdfs",
)

DELTA_BRONZE_TABLE = os.getenv("DELTA_BRONZE_TABLE", "gdpr_bronze_chunks")
DELTA_SILVER_TABLE = os.getenv(
    "DELTA_SILVER_TABLE",
    "gdpr_silver_enriched_chunks",
)
DELTA_GOLD_TABLE = os.getenv("DELTA_GOLD_TABLE", "gdpr_gold_index_ready")
DELTA_RESULTS_TABLE = os.getenv("DELTA_RESULTS_TABLE", "gdpr_rag_query_logs")

DELTA_BRONZE_TABLE_FULL_NAME = (
    f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{DELTA_BRONZE_TABLE}"
)
DELTA_SILVER_TABLE_FULL_NAME = (
    f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{DELTA_SILVER_TABLE}"
)
DELTA_GOLD_TABLE_FULL_NAME = f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{DELTA_GOLD_TABLE}"
DELTA_RESULTS_TABLE_FULL_NAME = (
    f"{DELTA_CATALOG}.{DELTA_SCHEMA}.{DELTA_RESULTS_TABLE}"
)

# Backward-compatible aliases for older ingestion helpers.
DELTA_TABLE = DELTA_BRONZE_TABLE
DELTA_ENRICHED_TABLE = DELTA_SILVER_TABLE

# Path to the raw file inside the Unity Catalog Volume
# Format: /Volumes/<catalog>/<schema>/<volume_name>/<filename>
VOLUME_FILE_PATH = os.getenv(
    "VOLUME_FILE_PATH",
    f"{RAW_PDF_VOLUME_DIR}/32016R0679_EN.pdf",
)

# ── Databricks — Enriched table (chunks + pre-computed embeddings) ────────────
# Databricks Foundation Model API embedding endpoint + output dimension
EMBEDDING_ENDPOINT  = os.getenv("EMBEDDING_ENDPOINT", "databricks-gte-large-en")
DATABRICKS_EMBEDDING_DIMENSION = int(
    os.getenv("DATABRICKS_EMBEDDING_DIMENSION", "1024")
)

# ── Databricks — Vector Search ────────────────────────────────────────────────
VECTOR_SEARCH_ENDPOINT = os.getenv("VECTOR_SEARCH_ENDPOINT", "rag-endpoint")
VECTOR_SEARCH_INDEX    = os.getenv(
    "VECTOR_SEARCH_INDEX",
    f"{DELTA_CATALOG}.{DELTA_SCHEMA}.gdpr_vector_index",
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
