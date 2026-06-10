"""
LLM-as-judge evaluation for the GDPR RAG pipeline.

Run from day_09/:
    uv run python src/day_09/evaluation/evaluate_rag.py

Reads   : data/evaluation_questions.csv  (columns: question, expected_document)
Writes  : data/eval_outputs/results.csv
          data/eval_outputs/results.json
          data/eval_outputs/summary.json

No existing files are modified. The RAG pipeline is imported read-only.
The evaluation results are NOT written to the query audit log — this is a
separate offline batch job, not live traffic.
"""

import csv
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

# ── project imports (read-only, no files are modified) ──────────────────────
from day_09.config import (
    AI_SEARCH_API_KEY,
    AI_SEARCH_ENDPOINT,
    AI_SEARCH_INDEX_NAME,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    AZURE_OPENAI_EMBEDDING_DIMENSION,
    AZURE_OPENAI_ENDPOINT,
    BASE_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    TOP_K,
    VOLUME_FILE_PATH,
)
from day_09.core.embeddings import AzureOpenAIEmbeddingModel
from day_09.core.llm import AzureOpenAIChatLLM
from day_09.core.rag_pipeline import RAGPipeline
from day_09.core.vector_store import AISearchVectorStore

# =============================================================================
# Configuration
# =============================================================================

DATASET_PATH = BASE_DIR / "data" / "evaluation_questions.csv"
OUT_DIR      = BASE_DIR / "data" / "eval_outputs"

JUDGE_SYSTEM = """You are a strict automated evaluator for RAG (Retrieval-Augmented Generation) outputs.

You will receive:
- question:     the user's original question
- context:      the document chunks that were retrieved and used to ground the answer
- model_answer: the answer produced by the RAG system

Your job:
1. Relevance   — does the answer actually address the question?
2. Faithfulness — does the answer contain ONLY claims that are supported by the provided context?
   A faithful answer must not introduce facts not present in the context.

Score each criterion 0–5 (5 = perfect).
overall_pass is True only when relevance_score >= 4 AND faithfulness_score >= 4.

Return ONLY a valid JSON object. No markdown fences, no extra keys.
"""
RELEVANCE_MIN    = 4
FAITHFULNESS_MIN = 4


# =============================================================================
# Data model
# =============================================================================

@dataclass
class EvalCase:
    id: str
    question: str
    expected_document: str   # e.g. "32016R0679_EN"


class JudgeResult(BaseModel):
    relevance_score:     int           = Field(..., ge=0, le=5)
    relevance_reason:    str
    faithfulness_score:  int           = Field(..., ge=0, le=5)
    faithfulness_reason: str
    overall_pass:        bool


# =============================================================================
# Pipeline setup  (no files modified — pure instantiation)
# =============================================================================

def _build_rag() -> RAGPipeline:
    embedding_model = AzureOpenAIEmbeddingModel(
        endpoint   = AZURE_OPENAI_ENDPOINT,
        api_key    = AZURE_OPENAI_API_KEY,
        api_version= AZURE_OPENAI_API_VERSION,
        deployment = AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    )
    vector_store = AISearchVectorStore(
        endpoint   = AI_SEARCH_ENDPOINT,
        api_key    = AI_SEARCH_API_KEY,
        index_name = AI_SEARCH_INDEX_NAME,
    )
    llm = AzureOpenAIChatLLM()
    return RAGPipeline(
        file_path    = VOLUME_FILE_PATH,
        embedding_model = embedding_model,
        vector_store    = vector_store,
        llm             = llm,
        chunk_size      = CHUNK_SIZE,
        chunk_overlap   = CHUNK_OVERLAP,
        top_k           = TOP_K,
        logger          = None,   # evaluation runs are NOT audit-logged
    )


def _build_judge() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint   = AZURE_OPENAI_ENDPOINT,
        api_key          = AZURE_OPENAI_API_KEY,
        api_version      = AZURE_OPENAI_API_VERSION,
        azure_deployment = AZURE_OPENAI_DEPLOYMENT_NAME,
        temperature      = 0,
    )


# =============================================================================
# Dataset loader
# =============================================================================

def load_dataset(path: Path) -> list[EvalCase]:
    cases = []
    with open(path, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            cases.append(EvalCase(
                id                = str(i),
                question          = row["question"].strip(),
                expected_document = row["expected_document"].strip(),
            ))
    return cases


# =============================================================================
# SUT  (System Under Test)
# =============================================================================

def run_sut(case: EvalCase, rag: RAGPipeline) -> dict:
    """Call the real RAG pipeline and return answer + retrieved chunks."""
    return rag.ask(case.question)


# =============================================================================
# Judge
# =============================================================================

def judge_answer(case: EvalCase, sut_result: dict, judge_llm: AzureChatOpenAI,
                 rag: RAGPipeline) -> JudgeResult:
    context      = rag.build_context(sut_result["retrieved_chunks"])
    model_answer = sut_result["answer"]

    user_prompt = f"""question:
{case.question}

context (retrieved chunks):
{context}

model_answer:
{model_answer}

Scoring rules:
- relevance_score:    0..5 — does the answer address the question?
- relevance_reason:   short justification
- faithfulness_score: 0..5 — is every claim in the answer supported by the context?
- faithfulness_reason: short justification
- overall_pass: true only if relevance_score >= {RELEVANCE_MIN} AND faithfulness_score >= {FAITHFULNESS_MIN}

Return ONLY valid JSON. No markdown fences. No extra keys.
"""

    messages = [
        SystemMessage(content=JUDGE_SYSTEM),
        HumanMessage(content=user_prompt),
    ]

    raw = judge_llm.invoke(messages).content.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.strip("`").lstrip("json").strip()

    try:
        parsed = json.loads(raw)
    except Exception as e:
        return JudgeResult(
            relevance_score=0,
            relevance_reason=f"Judge returned invalid JSON. Error: {e}. Raw: {raw[:400]}",
            faithfulness_score=0,
            faithfulness_reason="Invalid judge JSON output.",
            overall_pass=False,
        )

    try:
        return JudgeResult(**parsed)
    except Exception as e:
        return JudgeResult(
            relevance_score=0,
            relevance_reason=f"Judge JSON failed schema validation: {e}. Parsed: {parsed}",
            faithfulness_score=0,
            faithfulness_reason="Schema validation failed.",
            overall_pass=False,
        )


# =============================================================================
# Document-hit metric  (no LLM needed)
# =============================================================================

def document_hit(sut_result: dict, expected_document: str) -> bool:
    """True if any retrieved chunk came from the expected source document."""
    for chunk in sut_result["retrieved_chunks"]:
        source = chunk.get("metadata", {}).get("source_file", "")
        if expected_document in source:
            return True
    return False


# =============================================================================
# Pipeline
# =============================================================================

def run_evaluation() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cases = load_dataset(DATASET_PATH)
    print(f"Loaded {len(cases)} evaluation cases from {DATASET_PATH}")

    rag       = _build_rag()
    judge_llm = _build_judge()

    rows: list[dict[str, Any]] = []
    t0 = time.time()

    for case in cases:
        print(f"\n[{case.id}/{len(cases)}] {case.question}")

        sut_result = run_sut(case, rag)
        print(f"  Answer: {sut_result['answer'][:120]}...")

        jr         = judge_answer(case, sut_result, judge_llm, rag)
        doc_hit    = document_hit(sut_result, case.expected_document)

        print(f"  Relevance={jr.relevance_score}  Faithfulness={jr.faithfulness_score}  "
              f"Pass={jr.overall_pass}  DocHit={doc_hit}")

        rows.append({
            "id":                  case.id,
            "question":            case.question,
            "expected_document":   case.expected_document,
            "model_answer":        sut_result["answer"],
            "num_chunks_retrieved":len(sut_result["retrieved_chunks"]),
            "document_hit":        doc_hit,
            "relevance_score":     jr.relevance_score,
            "relevance_reason":    jr.relevance_reason,
            "faithfulness_score":  jr.faithfulness_score,
            "faithfulness_reason": jr.faithfulness_reason,
            "overall_pass":        jr.overall_pass,
        })

    df = pd.DataFrame(rows)

    doc_hit_series = df["document_hit"]
    summary: dict[str, Any] = {
        "dataset":          str(DATASET_PATH),
        "num_cases":        len(df),
        "pass_rate":        round(float(df["overall_pass"].mean()), 3),
        "document_hit_rate":round(float(doc_hit_series.mean()), 3),
        "avg_relevance":    round(float(df["relevance_score"].mean()), 3),
        "avg_faithfulness": round(float(df["faithfulness_score"].mean()), 3),
        "duration_sec":     round(time.time() - t0, 2),
        "failed_cases":     df.loc[~df["overall_pass"], "id"].tolist(),
    }

    df.to_csv(OUT_DIR / "results.csv", index=False)
    df.to_json(OUT_DIR / "results.json", orient="records", force_ascii=False, indent=2)
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)
    )

    print("\n=== EVALUATION SUMMARY ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    print(f"\nResults saved to {OUT_DIR}/")


if __name__ == "__main__":
    run_evaluation()
