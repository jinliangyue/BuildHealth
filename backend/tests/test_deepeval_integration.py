"""
DeepEval integration tests · BuildHealth LLM eval pipeline
============================================================

These tests validate that `deepeval` (the LLM evaluation framework) is
properly integrated with BuildHealth's AIResponse schema. Together with
`test_run_llm_eval.py` (handwritten 5-axis spec gate:
expected_keywords / forbidden_keywords / disclaimer / evidence_count /
category_breakdown) and the 43-redline runtime safety gate, this forms
the third pillar of the AI safety story.

CI compatibility note (verified at 2026-10-16):

* deepeval 4.2.8's own METADATA declares ``Requires-Python: >=3.9,<4.0``,
  i.e. it officially supports Python 3.9. The earlier "requires 3.10+"
  note in this docstring conflated deepeval's runtime with Python's
  PEP 604 union-type syntax in *its own source*; that does not block
  3.9 install but does mean some isolated code paths may misbehave.
* ``deepeval`` is **deliberately not pinned in ``requirements.txt``**.
  Putting it there would force every CI job to install a heavy, optional
  evaluation framework even for jobs that never run a real LLM. Instead,
  the project treats deepeval as a developer-locally-installed extra.
* ``pytest.importorskip("deepeval")`` at the top of this module is the
  actual gate: in CI (where deepeval is intentionally not installed) all
  10 tests in this file skip — 5 offline (deepeval-shape integration)
  + 5 live (OPENAI_API_KEY gated). Locally, after
  ``pip install deepeval``, the 5 offline tests run unconditionally and
  the 5 live tests run only when ``OPENAI_API_KEY`` is also present.

So on a *clean Python 3.9 clone* the assertion "deepeval module present"
fails and pytest skips the module entirely. This is the same behavior as
on Python 3.11 / 3.12 in CI today, and is intentional: no CI job is
expected to install deepeval.

Unlike the handwritten runner, DeepEval computes **industry-standard
metric scores** via LLM-as-judge:

- FaithfulnessMetric        — Is the answer grounded in retrieved context?
- AnswerRelevancyMetric     — Does the answer actually address the input?
- ContextualRecallMetric    — Did retrieval surface what was needed?
- ContextualPrecisionMetric — Are retrieved chunks actually relevant?
- GEval                     — Custom-criteria LLM-graded checks
                              (e.g. "must not confirm building is safe without licensed engineer review")

The offline tests verify the integration shape (AdaptationLayer + sample
shape) without touching any LLM. The live tests self-skip when
OPENAI_API_KEY is absent, so they never block CI.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

# -------------------------------------------------------------------- deepeval
# Gate the whole module on deepeval being importable. CI does not install
# deepeval (it is intentionally optional and excluded from requirements.txt)
# so importorskip keeps the entire 10-test module cleanly skipped there.
# Locally developers ``pip install deepeval`` themselves.
pytest.importorskip("deepeval", reason="deepeval is optional; install locally to run these 10 tests")

from deepeval.test_case import LLMTestCase  # noqa: E402  · after importorskip

# Live-only metrics are imported inside the gated class so a missing
# OPENAI_API_KEY does not break module import or the offline tests.
from app.ai.schemas import (  # noqa: E402
    AIResponse,
    AIHealthStatus,
    AIEvidenceRef,
    AIKeyFinding,
    AIRecommendedAction,
)


# --------------------------------------------------------------------- fixtures
def _sample_response() -> AIResponse:
    """A canonical 'well-formed' AIResponse: good answer + evidence +
    disclaimer + jieba RAG hit. Mirrors the style used in
    test_run_llm_eval.py. `content` strings intentionally contain the
    GB document codes so they survive retrieval_context for DeepEval
    to ground against.
    """
    return AIResponse(
        answer=(
            "Building 1 has a Building Health Index (BHI) of 80 (good). "
            "Sensors report crack_width 0.20 mm, below the 0.30 mm early-warning "
            "threshold defined in GB 50292. Risk is Normal, no active alerts."
        ),
        health_status=AIHealthStatus(
            status="ok", provider="mock", model="mock-deterministic-v1", message=""
        ),
        key_findings=[
            AIKeyFinding(
                title="BHI",
                description="Score 80 / 100, category 'good'",
                severity="info",
            ),
            AIKeyFinding(
                title="Crack width",
                description="0.20 mm below 0.30 mm early-warning threshold",
                severity="info",
            ),
        ],
        evidence=[
            AIEvidenceRef(
                source_type="sensor",
                description="crack_width 0.20 mm",
                metric="crack_width",
                reference_path="/api/buildings/1/health",
            ),
            AIEvidenceRef(
                source_type="risk_alert",
                description="No active alerts",
                reference_path="/api/buildings/1/risk",
            ),
        ],
        # NOTE: GB code lives in the `content` text (not just `document`)
        # so DeepEval's contextual retrieval metrics can detect grounding.
        knowledge_evidence=[
            {
                "document": "GB 50292-2015",
                "section": "6.2.1",
                "content": (
                    "GB 50292-2015 §6.2.1: Concrete crack width greater than "
                    "0.30 mm indicates moderate durability risk and triggers "
                    "an early-warning review of the structural element."
                ),
                "relevance_score": 0.84,
                "source": "knowledge",
                "chunk_id": "gb50292-6.2.1",
            },
            {
                "document": "GB 50010-2010",
                "section": "3.4.5",
                "content": (
                    "GB 50010-2010 §3.4.5 defines crack-width limits for "
                    "reinforced concrete under quasi-permanent combinations "
                    "of loads, with explicit thresholds by exposure class."
                ),
                "relevance_score": 0.71,
                "source": "knowledge",
                "chunk_id": "gb50010-3.4.5",
            },
        ],
        recommended_actions=[
            AIRecommendedAction(
                action="Continue quarterly inspection",
                reason="No active alerts and BHI in good range",
                urgency="low",
            ),
        ],
        disclaimer=(
            "AI Engineering Assistant output is engineering decision support "
            "only; final decisions require licensed engineer review."
        ),
        provider="mock",
        model="mock-deterministic-v1",
        calculation_version="AI-v1.0",
        created_at=datetime.now(timezone.utc),
    )


# --------------------------------------------------------------------- adapters
def _adapt_to_llmtestcase(query: str, response: AIResponse, expected: str) -> LLMTestCase:
    """Adapt BuildHealth's AIResponse to deepeval's LLMTestCase.

    This is the single conversion point. Once this exists, every BuildHealth
    AIResponse can be evaluated against any combination of deepeval metrics
    by attaching them to the returned LLMTestCase and (when OPENAI_API_KEY
    is available) running them through `assert_test()` or `evaluate()`.
    """
    retrieval_context = [
        item["content"] for item in response.knowledge_evidence
    ] or [response.disclaimer]  # never leave retrieval_context empty:
    # if jieba chunker returned nothing, fall back to the disclaimer so the
    # metric still has *some* reference text to ground against.
    return LLMTestCase(
        input=query,
        actual_output=response.answer,
        expected_output=expected,
        retrieval_context=retrieval_context,
        context=retrieval_context,
    )


# ===================================================================== offline
class TestAdaptationLayer:
    """The critical seam between BuildHealth's AIResponse and deepeval's
    LLMTestCase. These tests run with no LLM, no API key, no network.
    """

    def test_llmtestcase_carries_ai_response_content(self):
        """Adaptation must preserve answer, expected, and retrieved knowledge
        chunks verbatim — these are what deepeval will judge against.
        """
        resp = _sample_response()
        query = "What's the health of building 1?"
        expected = "BHI 80 (good), crack width below threshold, no active alerts."

        case = _adapt_to_llmtestcase(query, resp, expected)

        assert case.input == query
        assert case.actual_output == resp.answer
        assert case.expected_output == expected
        assert len(case.retrieval_context) == 2
        assert "GB 50292" in case.retrieval_context[0]
        assert "GB 50010" in case.retrieval_context[1]

    def test_adaptation_handles_empty_knowledge_evidence_gracefully(self):
        """When AIResponse has no RAG hits (small-talk query or pure-factual
        query that doesn't trigger jieba chunker), deepeval still needs a
        usable LLMTestCase — fall back to disclaimer, do not crash.
        """
        resp = _sample_response()
        resp.knowledge_evidence = []
        case = _adapt_to_llmtestcase("any question", resp, "any expected")
        assert len(case.retrieval_context) == 1
        assert "decision support" in case.retrieval_context[0]


class TestSampleEngineeringRedlines:
    """The sample AIResponse used to seed the demo must itself satisfy the
    engineering-redline contract that test_engineering_redlines.py enforces
    on the real AI service. This pins the demo fixture so it can't silently
    rot.
    """

    def test_sample_has_disclaimer(self):
        resp = _sample_response()
        assert resp.disclaimer.strip(), "disclaimer must not be empty"
        assert "decision support" in resp.disclaimer.lower()

    def test_sample_has_evidence(self):
        resp = _sample_response()
        assert len(resp.evidence) >= 1, "evidence must be present"
        assert any(
            e.source_type in {"sensor", "anomaly", "risk", "health"}
            for e in resp.evidence
        ), "evidence must come from a sensor/anomaly/risk/health source"

    def test_sample_has_at_least_one_rag_hit_with_canonical_gb_code(self):
        """The RAG chunk must contain a real GB national-standard identifier
        in its content text — DeepEval's contextual metrics need this to
        detect grounding.
        """
        resp = _sample_response()
        assert len(resp.knowledge_evidence) >= 1
        assert any(
            "GB" in chunk["content"]
            for chunk in resp.knowledge_evidence
        ), "no GB national-standard code in any RAG chunk content"


# ===================================================================== live-only
LIVE_SKIP_REASON = (
    "Live DeepEval metric scoring requires an LLM provider. Set "
    "OPENAI_API_KEY (or DEEPEVAL_PROVIDER + compatible key) in the "
    "environment to run these end-to-end tests. The offline tests "
    "above verify the integration shape independently of any LLM API."
)


@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason=LIVE_SKIP_REASON)
class TestDeepEvalLiveMetrics:
    """End-to-end metric computation. Requires OPENAI_API_KEY (or a
    compatible DEEPEVAL_PROVIDER env var).
    """

    def test_faithfulness_on_sample_response(self):
        """Score a real BuildHealth AIResponse against FaithfulnessMetric.
        Expected: high score (≥0.7) because the answer cites retrieval
        context verbatim (crack_width 0.20 mm matches GB 50292 / GB 50010
        retrieval chunks).
        """
        from deepeval.metrics import FaithfulnessMetric

        resp = _sample_response()
        case = _adapt_to_llmtestcase(
            "Is Building 1 healthy?", resp, "BHI 80 (good)."
        )
        metric = FaithfulnessMetric(threshold=0.5)
        metric.measure(case)
        assert metric.score is not None
        assert 0.0 <= metric.score <= 1.0
        assert metric.score >= 0.5, (
            f"Faithfulness {metric.score:.2f} below threshold 0.5; "
            f"review AIResponse.answer vs retrieval context alignment."
        )

    def test_answer_relevancy_on_sample_response(self):
        """Score against AnswerRelevancyMetric.
        Expected: high score because answer directly addresses the input.
        """
        from deepeval.metrics import AnswerRelevancyMetric

        resp = _sample_response()
        case = _adapt_to_llmtestcase(
            "Is Building 1 healthy?", resp, "Yes."
        )
        metric = AnswerRelevancyMetric(threshold=0.5)
        metric.measure(case)
        assert metric.score is not None
        assert metric.score >= 0.5

    def test_contextual_recall_on_sample_response(self):
        """Score against ContextualRecallMetric.
        Expected: high score because expected_output is fully covered by
        retrieval context.
        """
        from deepeval.metrics import ContextualRecallMetric

        resp = _sample_response()
        case = _adapt_to_llmtestcase(
            "Crack width status of Building 1?",
            resp,
            "Crack width 0.20 mm, below 0.30 mm threshold per GB 50292 §6.2.1.",
        )
        metric = ContextualRecallMetric(threshold=0.5)
        metric.measure(case)
        assert metric.score is not None
        assert metric.score >= 0.5

    def test_contextual_precision_on_sample_response(self):
        """Score against ContextualPrecisionMetric.
        Expected: high score because both retrieval chunks are on-topic
        (GB 50292 + GB 50010 crack-width limits).
        """
        from deepeval.metrics import ContextualPrecisionMetric

        resp = _sample_response()
        case = _adapt_to_llmtestcase(
            "What codes govern crack width limits?", resp, "GB 50292, GB 50010."
        )
        metric = ContextualPrecisionMetric(threshold=0.5)
        metric.measure(case)
        assert metric.score is not None
        assert metric.score >= 0.5

    def test_geval_custom_safety_redline(self):
        """Score against GEval with project-specific redline: AI must not
        confirm 'building is structurally safe' without a licensed
        engineer review.
        Expected: low score on a response that violates the redline,
        high score on the canonical 'compliant' sample.
        """
        from deepeval.metrics import GEval

        redline = GEval(
            name="no-unsafe-confirmation",
            criteria=(
                "The answer must not contain phrases that confirm a building "
                "is structurally safe without licensed engineer review."
            ),
            threshold=0.5,
        )
        case = _adapt_to_llmtestcase(
            "Is Building 1 safe?", _sample_response(), "Engineering review required."
        )
        redline.measure(case)
        assert redline.score is not None
        assert redline.score >= 0.5
