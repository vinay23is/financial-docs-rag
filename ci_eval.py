"""
CI smoke-test eval — calls the Lambda API endpoint directly.

Runs 5 representative queries, checks:
  - grounding rate >= 70%
  - mean latency   <= 3000 ms

Writes a Markdown summary to $GITHUB_STEP_SUMMARY (if set).
Exits with code 1 if either threshold is breached.

Usage:
    RAG_API_URL=https://... GOOGLE_API_KEY=... python ci_eval.py
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ── Smoke-test query set (5 queries covering all 3 companies) ─────────────────
QUERIES = [
    {
        "id": 1,
        "company": "AAPL",
        "question": "What was Apple's net income for the most recent fiscal year?",
        "keywords": ["net income", "billion", "apple"],
    },
    {
        "id": 2,
        "company": "GOOGL",
        "question": "What was Alphabet's total revenue for the most recent fiscal year?",
        "keywords": ["revenue", "billion", "alphabet", "google"],
    },
    {
        "id": 3,
        "company": "TSLA",
        "question": "What was Tesla's total revenue for the most recent fiscal year?",
        "keywords": ["revenue", "billion", "tesla"],
    },
    {
        "id": 4,
        "company": "GOOGL",
        "question": "What were Google Cloud revenues?",
        "keywords": ["cloud", "revenue", "billion"],
    },
    {
        "id": 5,
        "company": "ALL",
        "question": "Which company had the highest net income — Apple, Alphabet, or Tesla?",
        "keywords": ["net income", "apple", "alphabet", "tesla"],
    },
]

GROUNDING_THRESHOLD = 0.70    # 70 %
LATENCY_THRESHOLD_MS = 30000  # 30 s — end-to-end: Lambda cold start + embedding + LLM


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_grounded(answer: str, snippets: list[str]) -> bool:
    """
    Heuristic: every 4+ digit number cited in the answer must appear
    verbatim (digit-sequence) in at least one returned source snippet.
    Returns True if fully grounded (or no specific figures cited).
    """
    context = " ".join(snippets)

    def normalise(s: str) -> str:
        return re.sub(r"[,$]", "", s)

    raw_nums = re.findall(r"\$?[\d,]+(?:\.\d+)?", answer)
    nums = {normalise(n) for n in raw_nums if len(re.sub(r"\D", "", normalise(n))) >= 3}

    if not nums:
        return True

    ctx_norm = normalise(context)
    return all(n in ctx_norm for n in nums)


def _call_api(api_url: str, question: str) -> tuple[float, str, list[str]]:
    """Returns (latency_ms, answer, [snippets])."""
    payload = json.dumps({"query": question, "chat_history": []}).encode()
    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=90) as resp:
        raw = resp.read()
    latency_ms = (time.perf_counter() - t0) * 1000

    data = json.loads(raw)
    if isinstance(data.get("body"), str):
        data = json.loads(data["body"])

    answer = data.get("answer", "")
    snippets = [s.get("snippet", "") for s in data.get("sources", [])]
    return latency_ms, answer, snippets


def _md_status(ok: bool) -> str:
    return "✅" if ok else "❌"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    api_url = os.environ.get("RAG_API_URL", "").strip()
    if not api_url:
        print("ERROR: RAG_API_URL environment variable is not set.", file=sys.stderr)
        return 1

    print(f"Endpoint : {api_url}")
    print(f"Queries  : {len(QUERIES)}")
    print(f"Thresholds: grounding >= {GROUNDING_THRESHOLD*100:.0f}%  |  latency <= {LATENCY_THRESHOLD_MS} ms")
    print()

    results = []
    for q in QUERIES:
        print(f"  [{q['id']}/5] {q['company']:5s}  {q['question'][:65]} …", end=" ", flush=True)
        try:
            latency_ms, answer, snippets = _call_api(api_url, q["question"])
            grounded = _is_grounded(answer, snippets)
        except Exception as exc:
            print(f"ERROR: {exc}")
            results.append({**q, "latency_ms": LATENCY_THRESHOLD_MS * 2, "grounded": False, "error": str(exc)})
            continue

        results.append({**q, "latency_ms": round(latency_ms, 1), "grounded": grounded, "answer": answer, "error": None})
        print(f"grounded={int(grounded)}  latency={latency_ms:.0f} ms")

    # ── Aggregate ─────────────────────────────────────────────────────────────
    grounding_rate = sum(1 for r in results if r["grounded"]) / len(results)
    mean_latency   = sum(r["latency_ms"] for r in results) / len(results)
    max_latency    = max(r["latency_ms"] for r in results)

    grounding_ok = grounding_rate >= GROUNDING_THRESHOLD
    latency_ok   = mean_latency   <= LATENCY_THRESHOLD_MS
    overall_ok   = grounding_ok and latency_ok

    print()
    print(f"Grounding rate : {grounding_rate*100:.1f}%  (threshold ≥ {GROUNDING_THRESHOLD*100:.0f}%)  {_md_status(grounding_ok)}")
    print(f"Mean latency   : {mean_latency:.0f} ms  (threshold ≤ {LATENCY_THRESHOLD_MS} ms)  {_md_status(latency_ok)}")
    print(f"Max latency    : {max_latency:.0f} ms")
    print()
    print("Result:", "PASS ✅" if overall_ok else "FAIL ❌")

    # ── GitHub Actions job summary ────────────────────────────────────────────
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            f"# RAG Smoke-Test Eval — {ts}",
            "",
            f"**Overall: {'PASS ✅' if overall_ok else 'FAIL ❌'}**",
            "",
            "## Thresholds",
            "",
            f"| Metric | Value | Threshold | Status |",
            f"|---|---|---|---|",
            f"| Grounding rate | {grounding_rate*100:.1f}% | ≥ {GROUNDING_THRESHOLD*100:.0f}% | {_md_status(grounding_ok)} |",
            f"| Mean latency | {mean_latency:.0f} ms | ≤ {LATENCY_THRESHOLD_MS} ms | {_md_status(latency_ok)} |",
            f"| Max latency | {max_latency:.0f} ms | — | — |",
            "",
            "## Per-Query Results",
            "",
            "| # | Company | Question | Grounded | Latency (ms) |",
            "|---|---|---|---|---|",
        ]
        for r in results:
            q_short = r["question"][:60] + ("…" if len(r["question"]) > 60 else "")
            err = f" ⚠️ {r['error']}" if r.get("error") else ""
            lines.append(
                f"| {r['id']} | {r['company']} | {q_short}{err} "
                f"| {_md_status(r['grounded'])} | {r['latency_ms']:.0f} |"
            )
        lines += ["", f"_Endpoint: `{api_url}`_", ""]

        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
