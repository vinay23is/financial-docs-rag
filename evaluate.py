"""
Offline evaluation for the financial-docs RAG pipeline.

Metrics
-------
retrieval_precision : fraction of top-k chunks that contain at least one
                      expected keyword for the query (proxy for recall@k).
grounded            : 1 if every 4+ digit number in the response also appears
                      in the retrieved context, 0 if any number is invented.
latency_ms          : wall-clock time from retrieval start to response end.

Usage
-----
    python evaluate.py

Requires GOOGLE_API_KEY in .env or the environment.
Results are written to eval_results.csv and a summary is printed to stdout.
"""

import csv
import os
import re
import sys
import time
from pathlib import Path

# Allow imports from app/utils without installing as a package
sys.path.insert(0, str(Path(__file__).parent / "app"))

from utils.prepare_vectordb import get_vectorstore
from utils.chatbot import get_response

# ---------------------------------------------------------------------------
# 25 fixed evaluation queries with expected answer keywords
# ---------------------------------------------------------------------------
QUERIES = [
    # Apple — revenue & profit
    {"id": 1,  "company": "AAPL", "question": "What was Apple's total net revenue for the most recent fiscal year?",             "keywords": ["revenue", "billion", "aapl", "apple"]},
    {"id": 2,  "company": "AAPL", "question": "What was Apple's net income for the most recent fiscal year?",                   "keywords": ["net income", "billion", "apple"]},
    {"id": 3,  "company": "AAPL", "question": "What was Apple's earnings per share (EPS) for the most recent fiscal year?",    "keywords": ["earnings per share", "eps", "diluted"]},
    {"id": 4,  "company": "AAPL", "question": "How much did Apple spend on research and development?",                          "keywords": ["research", "development", "r&d", "billion"]},
    {"id": 5,  "company": "AAPL", "question": "What were Apple's iPhone revenues?",                                             "keywords": ["iphone", "revenue", "billion"]},
    {"id": 6,  "company": "AAPL", "question": "What were Apple's Services segment revenues?",                                   "keywords": ["services", "revenue", "billion"]},
    {"id": 7,  "company": "AAPL", "question": "What was Apple's gross margin percentage?",                                      "keywords": ["gross margin", "%", "percent"]},
    {"id": 8,  "company": "AAPL", "question": "What was Apple's total operating expenses?",                                     "keywords": ["operating expenses", "billion", "apple"]},
    {"id": 9,  "company": "AAPL", "question": "How much cash and equivalents did Apple hold at year end?",                      "keywords": ["cash", "billion", "apple"]},

    # Alphabet / Google — revenue & segments
    {"id": 10, "company": "GOOGL", "question": "What was Alphabet's total revenue for the most recent fiscal year?",            "keywords": ["revenue", "billion", "alphabet", "google"]},
    {"id": 11, "company": "GOOGL", "question": "What was Google's advertising revenue?",                                        "keywords": ["advertising", "revenue", "billion"]},
    {"id": 12, "company": "GOOGL", "question": "What was Alphabet's net income?",                                               "keywords": ["net income", "billion", "alphabet"]},
    {"id": 13, "company": "GOOGL", "question": "What were Google Cloud revenues?",                                              "keywords": ["cloud", "revenue", "billion"]},
    {"id": 14, "company": "GOOGL", "question": "What was Alphabet's operating income?",                                         "keywords": ["operating income", "billion", "alphabet"]},
    {"id": 15, "company": "GOOGL", "question": "How much did Alphabet spend on research and development?",                      "keywords": ["research", "development", "billion", "alphabet"]},
    {"id": 16, "company": "GOOGL", "question": "What were Alphabet's YouTube advertising revenues?",                            "keywords": ["youtube", "revenue", "billion"]},
    {"id": 17, "company": "GOOGL", "question": "What was Alphabet's earnings per share?",                                       "keywords": ["earnings per share", "eps", "diluted"]},

    # Tesla — deliveries, revenue & margins
    {"id": 18, "company": "TSLA", "question": "What was Tesla's total revenue for the most recent fiscal year?",                "keywords": ["revenue", "billion", "tesla"]},
    {"id": 19, "company": "TSLA", "question": "How many vehicles did Tesla deliver?",                                           "keywords": ["deliver", "vehicle", "units", "thousand"]},
    {"id": 20, "company": "TSLA", "question": "What was Tesla's net income?",                                                   "keywords": ["net income", "billion", "tesla"]},
    {"id": 21, "company": "TSLA", "question": "What was Tesla's automotive gross margin?",                                      "keywords": ["automotive", "gross margin", "%", "percent"]},
    {"id": 22, "company": "TSLA", "question": "How much did Tesla spend on research and development?",                          "keywords": ["research", "development", "billion", "tesla"]},
    {"id": 23, "company": "TSLA", "question": "What was Tesla's energy generation and storage revenue?",                        "keywords": ["energy", "revenue", "billion", "tesla"]},
    {"id": 24, "company": "TSLA", "question": "What was Tesla's free cash flow?",                                               "keywords": ["free cash flow", "billion", "tesla"]},

    # Cross-company comparison
    {"id": 25, "company": "ALL",  "question": "Which company had the highest net income — Apple, Alphabet, or Tesla?",          "keywords": ["net income", "apple", "alphabet", "tesla", "highest"]},
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chunk_contains_keyword(chunk_text: str, keywords: list[str]) -> bool:
    text = chunk_text.lower()
    return any(kw.lower() in text for kw in keywords)


def retrieval_precision(docs, keywords: list[str]) -> float:
    """Fraction of retrieved chunks that contain at least one expected keyword."""
    if not docs:
        return 0.0
    hits = sum(1 for doc in docs if _chunk_contains_keyword(doc.page_content, keywords))
    return hits / len(docs)


def is_grounded(response: str, docs) -> int:
    """
    Heuristic grounding check.
    Extracts standalone integers/decimals with 4+ significant digits from the
    response (e.g. '$394.3' → '3943', '1,234' → '1234') and checks that each
    one also appears (verbatim digit sequence) in the retrieved context.
    Returns 1 if fully grounded, 0 if at least one figure is not in context.
    """
    context = " ".join(doc.page_content for doc in docs)

    # Normalise: strip commas, strip leading $
    def normalise(s: str) -> str:
        return re.sub(r"[,$]", "", s)

    # Numbers that appear in the response (3+ digits after normalisation)
    raw_nums = re.findall(r"\$?[\d,]+(?:\.\d+)?", response)
    response_nums = {normalise(n) for n in raw_nums if len(re.sub(r"\D", "", normalise(n))) >= 3}

    if not response_nums:
        return 1  # no specific figures cited — cannot be falsified

    ctx_norm = normalise(context)
    invented = [n for n in response_nums if n not in ctx_norm]
    return 0 if invented else 1


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

def run_eval():
    print("Loading vector store …")
    vectordb = get_vectorstore([], from_session_state=True)
    if vectordb is None:
        sys.exit(
            "Vector store not found. "
            "Run the Streamlit app first to build the ChromaDB index."
        )

    rows = []
    for q in QUERIES:
        qid = q["id"]
        question = q["question"]
        company = q["company"]
        keywords = q["keywords"]

        print(f"  [{qid:02d}/25] {company:5s}  {question[:65]} …", end=" ", flush=True)

        t0 = time.perf_counter()
        response, docs = get_response(question, [], vectordb)
        latency_ms = (time.perf_counter() - t0) * 1000

        prec = retrieval_precision(docs, keywords)
        grounded = is_grounded(response, docs)

        rows.append({
            "id": qid,
            "company": company,
            "question": question,
            "retrieval_precision": round(prec, 3),
            "grounded": grounded,
            "latency_ms": round(latency_ms, 1),
            "response_snippet": response[:120].replace("\n", " "),
        })
        print(f"prec={prec:.2f}  grounded={grounded}  latency={latency_ms:.0f}ms")

    # ------------------------------------------------------------------
    # Write CSV
    # ------------------------------------------------------------------
    csv_path = Path(__file__).parent / "eval_results.csv"
    fieldnames = ["id", "company", "question", "retrieval_precision", "grounded", "latency_ms", "response_snippet"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nResults saved → {csv_path}")

    # ------------------------------------------------------------------
    # Summary table
    # ------------------------------------------------------------------
    companies = sorted({r["company"] for r in rows})
    col_w = 8

    header = f"{'Company':<8}  {'Queries':>7}  {'Avg Precision':>13}  {'Grounding %':>11}  {'Avg Latency ms':>14}"
    sep = "-" * len(header)
    print(f"\n{sep}")
    print(header)
    print(sep)

    overall_prec, overall_grounded, overall_lat = [], [], []
    for co in companies:
        subset = [r for r in rows if r["company"] == co]
        precs   = [r["retrieval_precision"] for r in subset]
        grounds = [r["grounded"] for r in subset]
        lats    = [r["latency_ms"] for r in subset]
        avg_p   = sum(precs) / len(precs)
        avg_g   = sum(grounds) / len(grounds) * 100
        avg_l   = sum(lats) / len(lats)
        print(f"{co:<8}  {len(subset):>7}  {avg_p:>13.3f}  {avg_g:>10.1f}%  {avg_l:>13.1f}")
        overall_prec.extend(precs)
        overall_grounded.extend(grounds)
        overall_lat.extend(lats)

    print(sep)
    print(
        f"{'ALL':<8}  {len(rows):>7}  "
        f"{sum(overall_prec)/len(overall_prec):>13.3f}  "
        f"{sum(overall_grounded)/len(overall_grounded)*100:>10.1f}%  "
        f"{sum(overall_lat)/len(overall_lat):>13.1f}"
    )
    print(sep)
    print()


if __name__ == "__main__":
    run_eval()
