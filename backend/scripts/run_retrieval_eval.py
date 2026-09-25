"""
RAG retrieval evaluation set + runner · BuildHealth v1.1 release prep
====================================================================

Evaluates the TF-IDF retriever against a hand-curated 50-query evaluation set.

Usage:
    cd backend && python -m scripts.run_retrieval_eval
    cd backend && python -m scripts.run_retrieval_eval --top-k 5

Output: recall@3, MRR, median latency (ms), miss list.

Eval set design (per BuildHealth-prep-notes/34):
- 50 queries covering 5 knowledge docs (anomaly_detection / health_assessment /
  risk_classification / retrofit_decision / engineering_redlines)
- Each query has a known expected doc; evaluation checks whether the retriever
  surfaces that doc within top-K
- 50/50 split: literal-match vs paraphrase queries (tests robustness, not
  memorisation)
- No external concepts outside the 5 docs (so "not found" is never the right
  answer)
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from app.knowledge.retriever import KnowledgeRetriever


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def evaluate(jsonl_path: Path, retriever: KnowledgeRetriever) -> dict:
    rows = load_jsonl(jsonl_path)
    if not rows:
        return {"error": "empty eval set", "n_queries": 0}

    recall_correct = 0
    mrr_sum = 0.0
    latency_ms_list = []
    miss = []

    for r in rows:
        t0 = time.perf_counter()
        results = retriever.retrieve(r["query"])
        latency_ms_list.append((time.perf_counter() - t0) * 1000)

        # 找第一个 expected_doc 出现在 results 里的位置
        rank = None
        for i, hit in enumerate(results, start=1):
            if hit.document == r["expect_doc"]:
                rank = i
                break
        if rank is not None:
            recall_correct += 1
            mrr_sum += 1.0 / rank
        else:
            miss.append(r["qid"])

    return {
        "recall_at_3": round(recall_correct / len(rows), 4),
        "mrr": round(mrr_sum / len(rows), 4),
        "median_latency_ms": round(statistics.median(latency_ms_list), 3),
        "n_queries": len(rows),
        "n_hits": recall_correct,
        "miss_qids": miss,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RAG retrieval evaluation set")
    parser.add_argument(
        "--eval-set",
        type=Path,
        default=Path(__file__).parent / "retrieval_eval_set.jsonl",
        help="Path to JSONL evaluation set",
    )
    parser.add_argument(
        "--knowledge-dir",
        type=Path,
        default=Path(__file__).parent.parent / "knowledge",
        help="Path to knowledge docs directory",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Top-K chunks to retrieve (default 3, matches production config)",
    )
    args = parser.parse_args()

    if not args.eval_set.exists():
        print(f"ERROR: eval set not found: {args.eval_set}", file=sys.stderr)
        return 1

    print(f"Loading retriever from {args.knowledge_dir} (top_k={args.top_k})...")
    retriever = KnowledgeRetriever(args.knowledge_dir, top_k=args.top_k)

    print(f"Evaluating {args.eval_set}...")
    metrics = evaluate(args.eval_set, retriever)

    print()
    print("=" * 50)
    print("RAG retrieval evaluation")
    print("=" * 50)
    for k, v in metrics.items():
        print(f"  {k}: {v}")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())