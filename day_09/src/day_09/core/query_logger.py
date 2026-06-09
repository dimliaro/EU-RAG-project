"""
Query / Answer audit log — COMPLETELY SEPARATE from the Chroma vector store.

Architecture boundary
─────────────────────
  Chroma vector store  →  holds source regulation chunks; used for retrieval.
  Query log            →  holds Q&A records + retrieval audit trail; append-only output.

  These two NEVER touch each other:
    • RAG retrieval never reads from this log.
    • This log never writes into the vector store.
    • The purpose is observability/compliance, not retrieval.

Record schema
─────────────
    {
      "id":          str,   # UUID v4
      "timestamp":   str,   # ISO-8601 UTC  e.g. "2025-06-07T21:00:00.123456+00:00"
      "query":       str,   # the user's question
      "answer":      str,   # the LLM's answer
      "model":       str,   # deployment name (from config)
      "k":           int,   # how many chunks were retrieved
      "filters":     dict | None,  # any metadata filter applied to retrieval
      "latency_ms":  int,   # wall-clock ms from embed-query to answer
      "retrieved":   list[  # the audit trail — exactly what grounded the answer
          {
            "chunk_id":       str,
            "structure_type": str,   # "article" | "recital" | ""
            "number":         int,   # article/recital number, 0 if unknown
            "regulation":     str,   # e.g. "Regulation (EU) 2016/679"
            "score":          float, # cosine distance from Chroma (lower = closer)
          }
      ]
    }

Exports
───────
    QueryLogger           — ABC; every backend implements this.
    SqliteQueryLogger     — stdlib sqlite3; works locally with no extra deps.
    DatabricksQueryLogger — documented skeleton; raises NotImplementedError.
    get_query_logger()    — factory; reads LOG_BACKEND from config.
"""

import json
import sqlite3
import uuid
import warnings
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path


# ── Interface ──────────────────────────────────────────────────────────────────

class QueryLogger(ABC):
    """
    Contract that all backends must satisfy.

    Logging is always a fire-and-forget side effect: callers catch exceptions
    so that a logging failure never crashes the pipeline.
    """

    @abstractmethod
    def log(self, record: dict) -> None:
        """Persist one Q&A record."""

    @abstractmethod
    def recent(self, n: int = 10) -> list[dict]:
        """Return the n most recent records, newest first."""

    @abstractmethod
    def search(self, keyword: str) -> list[dict]:
        """Return records whose query contains keyword (case-insensitive)."""


# ── SQLite implementation ──────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS query_log (
    id          TEXT    PRIMARY KEY,
    timestamp   TEXT    NOT NULL,
    query       TEXT    NOT NULL,
    answer      TEXT    NOT NULL,
    model       TEXT    NOT NULL,
    k           INTEGER NOT NULL,
    filters     TEXT,               -- JSON string or NULL
    latency_ms  INTEGER NOT NULL,
    retrieved   TEXT    NOT NULL    -- JSON array string
);
CREATE INDEX IF NOT EXISTS idx_ts ON query_log (timestamp DESC);
"""

_INSERT = """
INSERT OR IGNORE INTO query_log
    (id, timestamp, query, answer, model, k, filters, latency_ms, retrieved)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


class SqliteQueryLogger(QueryLogger):
    """
    Appends Q&A records to a local SQLite database.

    Concurrency
        check_same_thread=False + WAL mode makes concurrent reads safe.
        Concurrent writes from multiple uvicorn workers will serialize — fine
        for a single-process dev server.  If you spin up multiple workers,
        WAL already handles brief locking; no data will be lost.

    Size / rotation
        Not implemented.  For a demo this is fine.  For long-running prod:
        add a periodic `DELETE FROM query_log WHERE timestamp < ?` job, or
        move to Databricks Delta with automatic OPTIMIZE / VACUUM.

    GDPR note (important for a real deployment)
        This table logs the raw query text and the full LLM answer.  If
        queries or answers contain personal data you must treat this table
        as a personal-data store, apply appropriate retention limits, and
        potentially offer erasure.  Audit this before going to production.
    """

    def __init__(self, db_path: str | Path):
        self._path = str(db_path)
        self._conn = sqlite3.connect(
            self._path,
            check_same_thread=False,
            isolation_level=None,   # autocommit
        )
        self._conn.executescript("PRAGMA journal_mode=WAL;")
        self._conn.executescript(_DDL)

    # ── write ──────────────────────────────────────────────────────────────────

    def log(self, record: dict) -> None:
        self._conn.execute(
            _INSERT,
            (
                record["id"],
                record["timestamp"],
                record["query"],
                record["answer"],
                record["model"],
                record["k"],
                json.dumps(record.get("filters")),        # None → "null"
                record["latency_ms"],
                json.dumps(record.get("retrieved", [])),  # list → JSON text
            ),
        )

    # ── read ───────────────────────────────────────────────────────────────────

    def recent(self, n: int = 10) -> list[dict]:
        cur = self._conn.execute(
            "SELECT * FROM query_log ORDER BY timestamp DESC LIMIT ?", (n,)
        )
        return [self._row(r) for r in cur.fetchall()]

    def search(self, keyword: str) -> list[dict]:
        # LIKE is O(n) but fine for an audit log of this scale.
        # Never interpolate `keyword` directly — always use a parameter.
        cur = self._conn.execute(
            "SELECT * FROM query_log WHERE LOWER(query) LIKE LOWER(?) ORDER BY timestamp DESC",
            (f"%{keyword}%",),
        )
        return [self._row(r) for r in cur.fetchall()]

    # ── helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _row(row: tuple) -> dict:
        id_, ts, query, answer, model, k, filters, latency_ms, retrieved = row
        return {
            "id":         id_,
            "timestamp":  ts,
            "query":      query,
            "answer":     answer,
            "model":      model,
            "k":          k,
            "filters":    json.loads(filters) if filters else None,
            "latency_ms": latency_ms,
            "retrieved":  json.loads(retrieved),
        }


# ── Databricks skeleton ────────────────────────────────────────────────────────

class DatabricksQueryLogger(QueryLogger):
    """
    Production skeleton: appends Q&A records to a Delta table in Unity Catalog.

    This class is intentionally NOT functional — it documents the design so
    you can build it during the demo explanation or as a next step.

    Target Delta table schema (run once in a SQL warehouse or notebook)
    ───────────────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS <catalog>.<schema>.query_log (
            id          STRING    NOT NULL,
            timestamp   TIMESTAMP NOT NULL,   -- or TEXT if using SQL warehouse
            query       STRING    NOT NULL,
            answer      STRING    NOT NULL,
            model       STRING    NOT NULL,
            k           INT       NOT NULL,
            filters     STRING,               -- JSON text or NULL
            latency_ms  BIGINT    NOT NULL,
            retrieved   STRING    NOT NULL    -- JSON text; see note below
        )
        USING DELTA
        TBLPROPERTIES (
            'delta.enableChangeDataFeed' = 'true'
        );

    Optional: use a typed ARRAY column for richer SQL analytics on retrieved:
        retrieved  ARRAY<STRUCT<
            chunk_id:       STRING,
            structure_type: STRING,
            number:         INT,
            regulation:     STRING,
            score:          DOUBLE
        >>
    That makes "which articles were cited most often?" a simple LATERAL VIEW
    query.  The JSON-text approach is simpler to start.

    IMPORTANT BOUNDARIES
    ────────────────────
    • This is an APPEND-ONLY audit table — no UPDATE, no DELETE (except for
      GDPR right-to-erasure, which should be handled by a separate process).
    • This table is NOT a Vector Search index and MUST NOT be used as one.
    • Never feed rows from this table back into the RAG retrieval path.

    Deployment steps
    ────────────────
    1. `databricks auth login --host <workspace_url>`
    2. Create the Delta table above in Unity Catalog.
    3. Set LOG_BACKEND=databricks in the job/cluster environment.
    4. Set DELTA_CATALOG, DELTA_SCHEMA — already used by spark_ingester.py.
    5. Pick an execution method:
         a. If running INSIDE a Databricks job → use a SparkSession:
               spark.createDataFrame([row_dict]).write.mode("append")
                    .saveAsTable(table_name)
         b. If running OUTSIDE (local API calling Databricks) → use SDK:
               WorkspaceClient().statement_execution.execute_statement(
                   warehouse_id=os.getenv("DATABRICKS_WAREHOUSE_ID"),
                   statement="INSERT INTO ... VALUES (...)",
                   parameters=[...]
               )
    """

    def __init__(self, catalog: str, schema: str, table: str = "query_log"):
        # TODO: store coordinates; initialise WorkspaceClient or SparkSession
        self._table = f"{catalog}.{schema}.{table}"
        raise NotImplementedError(
            "DatabricksQueryLogger is a documented skeleton. "
            "See the class docstring for the deployment steps and SQL schema."
        )

    def log(self, record: dict) -> None:
        # TODO: INSERT one row into self._table
        # Use parameterised SQL — never f-string user data into a query.
        raise NotImplementedError

    def recent(self, n: int = 10) -> list[dict]:
        # TODO: SELECT * FROM self._table ORDER BY timestamp DESC LIMIT :n
        raise NotImplementedError

    def search(self, keyword: str) -> list[dict]:
        # TODO: SELECT * FROM self._table
        #       WHERE LOWER(query) LIKE LOWER(CONCAT('%', :keyword, '%'))
        #       ORDER BY timestamp DESC
        raise NotImplementedError


# ── Factory ────────────────────────────────────────────────────────────────────

def get_query_logger() -> QueryLogger:
    """
    Return the configured logger.

    Import is deferred until call time so that importing this module does NOT
    open a database connection — only the first call to get_query_logger() does.
    """
    from day_09.config import LOG_BACKEND, QUERY_LOG_DB  # deferred to avoid circular import

    if LOG_BACKEND == "sqlite":
        return SqliteQueryLogger(db_path=QUERY_LOG_DB)

    if LOG_BACKEND == "databricks":
        from day_09.config import DELTA_CATALOG, DELTA_SCHEMA
        return DatabricksQueryLogger(catalog=DELTA_CATALOG, schema=DELTA_SCHEMA)

    raise ValueError(
        f"Unknown LOG_BACKEND {LOG_BACKEND!r}. "
        "Valid values: 'sqlite', 'databricks'."
    )
