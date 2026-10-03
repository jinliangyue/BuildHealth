"""
LLM output evaluation runner · BuildHealth Phase 7
====================================================

Runs the AI Engineering Assistant against a hand-curated evaluation
set of 30 queries, checks each response against expected properties,
and emits a JSON report. This is the third piece of evidence for
"AI safety story" alongside the 43-redline runtime gate and the
handwritten unit tests:

  - The 43 redlines say "the response never contains X". The eval set
    asserts *non-trivial* queries (e.g. "can you design the building?")
    are refused gracefully (without forbidden phrases, with disclaimer).

  - The unit tests assert structural correctness (schema fields, evidence
    shape). The eval set asserts *semantic* behaviour (answers mention
    the right concepts, evidence is present when expected).

The default provider is `mock` (no API key required). Switching to
`openai-compatible` runs the same set against the real LLM but
requires AI_PROVIDER + AI_BASE_URL + AI_API_KEY env vars.

Usage:
    cd backend && python -m scripts.run_llm_eval
    cd backend && python -m scripts.run_llm_eval --provider openai-compatible
    cd backend && python -m scripts.run_llm_eval --eval-set path/to/other.jsonl

Exit codes:
    0  all queries passed
    2  some queries failed; report printed
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import select

from app.ai.service import AIService
from app.ai.schemas import AIResponse
from app.ai.provider_factory import get_ai_provider
from app.db import models as m
from app.db.session import SessionLocal


DEFAULT_EVAL_SET = Path(__file__).resolve().parent.parent / "eval" / "llm_eval_set.jsonl"


# ----------------------------------------------------------------------------
# Result model
# ----------------------------------------------------------------------------
@dataclass
class QueryResult:
    qid: str
    query: str
    category: str
    passed: bool
    failures: List[str] = field(default_factory=list)
    answer_excerpt: str = ""
    has_disclaimer: bool = False
    evidence_count: int = 0
    elapsed_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "qid": self.qid,
            "query": self.query,
            "category": self.category,
            "passed": self.passed,
            "failures": self.failures,
            "answer_excerpt": self.answer_excerpt,
            "has_disclaimer": self.has_disclaimer,
            "evidence_count": self.evidence_count,
            "elapsed_ms": round(self.elapsed_ms, 3),
            "error": self.error,
        }


# ----------------------------------------------------------------------------
# Eval helpers
# ----------------------------------------------------------------------------
def _check_response(
    response: AIResponse,
    spec: Dict,
) -> List[str]:
    """Return a list of human-readable failure strings."""
    failures: List[str] = []
    full_text = _response_text(response).lower()

    # 1. Required keywords (any-of)
    expected: List[str] = spec.get("expected_keywords_any") or []
    if expected and not any(kw.lower() in full_text for kw in expected):
        failures.append(
            f"expected at least one of {expected} somewhere in response"
        )

    # 2. Forbidden keywords (none-of)
    forbidden: List[str] = spec.get("forbidden_keywords") or []
    for kw in forbidden:
        if kw.lower() in full_text:
            failures.append(f"response contained forbidden keyword: {kw!r}")

    # 3. Disclaimer presence
    if spec.get("requires_disclaimer") and not response.disclaimer:
        failures.append("disclaimer missing (required by spec)")

    # 4. Minimum evidence count
    min_ev = int(spec.get("min_evidence", 0))
    if len(response.evidence) < min_ev:
        failures.append(
            f"evidence count {len(response.evidence)} < required {min_ev}"
        )

    return failures


def _response_text(response: AIResponse) -> str:
    """Concatenate every text field that the redline scan covers.

    Same composition as `MockProvider._guard_safety`, kept consistent
    so forbidden-phrase detection here matches runtime behaviour.
    """
    parts = [response.answer]
    for kf in response.key_findings:
        parts.append(f"{kf.title} {kf.description}")
    for a in response.recommended_actions:
        parts.append(f"{a.action} {a.reason}")
    for e in response.evidence:
        parts.append(e.description)
    parts.append(response.disclaimer or "")
    return " ".join(parts)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def _make_provider():
    """Resolve the AI provider via the project's standard factory.

    Falls back to MockProvider if `get_ai_provider` raises (defensive —
    the factory normally returns _MisconfiguredProvider instead).
    """
    try:
        return get_ai_provider()
    except Exception:
        from app.ai.mock_provider import MockProvider
        return MockProvider()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the LLM evaluation set against the AI service."
    )
    parser.add_argument(
        "--eval-set",
        type=Path,
        default=DEFAULT_EVAL_SET,
        help=f"Path to the JSONL eval set (default: {DEFAULT_EVAL_SET}).",
    )
    parser.add_argument(
        "--provider",
        choices=("mock", "openai-compatible"),
        default=None,
        help="Override AI_PROVIDER env var for this run.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only run the first N queries (useful for smoke tests).",
    )
    args = parser.parse_args(argv)

    if args.provider:
        os.environ["AI_PROVIDER"] = args.provider

    if not args.eval_set.exists():
        print(json.dumps({"error": f"eval set not found: {args.eval_set}"}))
        return 1

    ai_service = AIService(provider=_make_provider())
    provider_name = os.environ.get("AI_PROVIDER", "mock")

    results: List[QueryResult] = []
    queries: List[Dict] = []
    with args.eval_set.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            queries.append(json.loads(line))
    if args.limit:
        queries = queries[: args.limit]

    db = SessionLocal()
    try:
        for spec in queries:
            qid = spec.get("qid", "?")
            query_text = spec.get("query", "")
            category = spec.get("category", "")
            failures: List[str] = []
            error: Optional[str] = None
            response: Optional[AIResponse] = None
            started = time.perf_counter()
            try:
                # ask_about_building is the public surface; it builds the
                # context internally and runs RAG, so the runner doesn't
                # need to duplicate that wiring.
                first_building_id = (
                    db.execute(select(m.Building.id).order_by(m.Building.id).limit(1))
                    .scalars()
                    .first()
                )
                if first_building_id is None:
                    failures.append("no building in DB; cannot build context")
                    response = None
                else:
                    response = ai_service.ask_about_building(
                        db, first_building_id, query_text
                    )
                if response is None:
                    failures.append("AI service returned None")
            except Exception as exc:
                error = f"{exc.__class__.__name__}: {exc}"
                failures.append(f"AI service raised: {error}")
            elapsed_ms = (time.perf_counter() - started) * 1000.0

            if response is not None:
                failures.extend(_check_response(response, spec))

            results.append(
                QueryResult(
                    qid=qid,
                    query=query_text,
                    category=category,
                    passed=not failures and error is None,
                    failures=failures,
                    answer_excerpt=(response.answer[:200] + "…") if response and len(response.answer) > 200 else (response.answer if response else ""),
                    has_disclaimer=bool(response.disclaimer) if response else False,
                    evidence_count=len(response.evidence) if response else 0,
                    elapsed_ms=elapsed_ms,
                    error=error,
                )
            )
    finally:
        db.close()

    # Aggregate report
    by_category: Dict[str, Dict[str, int]] = {}
    for r in results:
        c = r.category or "uncategorised"
        bucket = by_category.setdefault(c, {"total": 0, "passed": 0, "failed": 0})
        bucket["total"] += 1
        if r.passed:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1

    n_pass = sum(1 for r in results if r.passed)
    n_fail = len(results) - n_pass
    report = {
        "provider": provider_name,
        "n_queries": len(results),
        "n_passed": n_pass,
        "n_failed": n_fail,
        "pass_rate": round(n_pass / len(results), 4) if results else 0.0,
        "by_category": by_category,
        "results": [r.to_dict() for r in results],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    return 0 if n_fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
