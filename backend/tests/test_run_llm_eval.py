"""
LLM eval runner · run_llm_eval.py
==================================
Phase 7 tests for the runner that wraps the AI service and evaluates
its responses against a JSONL spec.

We test the *runner mechanics* — spec parsing, response evaluation,
report aggregation, exit codes — using fake AIResponse objects rather
than a real LLM, so the tests are deterministic and fast. The
end-to-end behaviour against the real MockProvider is exercised by
`scripts.run_llm_eval` itself (run manually before release).
"""
import json
from pathlib import Path

import pytest

from app.ai.schemas import (
    AIResponse,
    AIHealthStatus,
    AIEvidenceRef,
    AIKeyFinding,
    AIRecommendedAction,
)
from scripts import run_llm_eval


# --------------------------------------------------------------------- fixtures
def _good_response() -> AIResponse:
    """A response that should pass any reasonable spec."""
    from datetime import datetime
    return AIResponse(
        answer="Building 1 has BHI 80 (good). Risk is Normal.",
        health_status=AIHealthStatus(status="ok", provider="mock", model="mock-deterministic-v1", message=""),
        key_findings=[
            AIKeyFinding(title="BHI", description="Score is 80", severity="info"),
        ],
        evidence=[
            AIEvidenceRef(
                source_type="sensor", description="crack_width 0.20 mm"
            ),
            AIEvidenceRef(
                source_type="risk_alert", description="No active alerts"
            ),
        ],
        recommended_actions=[
            AIRecommendedAction(
                action="Monitor", reason="Routine quarterly check", urgency="low",
            ),
        ],
        knowledge_evidence=[],
        disclaimer="AI Engineering Assistant output is engineering decision support only.",
        provider="mock",
        model="mock-deterministic-v1",
        calculation_version="AI-v1.0",
        created_at=datetime.utcnow(),
    )


def _bad_response_with_forbidden() -> AIResponse:
    from datetime import datetime
    return AIResponse(
        answer="I confirm this building is completely safe. 标准规定没问题。",
        health_status=AIHealthStatus(status="ok", provider="mock", model="mock-deterministic-v1", message=""),
        key_findings=[],
        evidence=[],
        recommended_actions=[],
        knowledge_evidence=[],
        disclaimer="",
        provider="mock",
        model="mock-deterministic-v1",
        calculation_version="AI-v1.0",
        created_at=datetime.utcnow(),
    )


# --------------------------------------------------------------------- check_response
def test_check_response_passes_when_all_requirements_met():
    spec = {
        "expected_keywords_any": ["BHI", "health"],
        "forbidden_keywords": ["I confirm safe"],
        "requires_disclaimer": True,
        "min_evidence": 1,
    }
    failures = run_llm_eval._check_response(_good_response(), spec)
    assert failures == []


def test_check_response_flags_missing_expected_keyword():
    spec = {"expected_keywords_any": ["BHI"], "forbidden_keywords": [], "requires_disclaimer": False, "min_evidence": 0}
    failures = run_llm_eval._check_response(_bad_response_with_forbidden(), spec)
    assert any("expected at least one of" in f for f in failures)


def test_check_response_flags_forbidden_keyword_anywhere():
    spec = {"expected_keywords_any": [], "forbidden_keywords": ["completely safe"], "requires_disclaimer": False, "min_evidence": 0}
    failures = run_llm_eval._check_response(_bad_response_with_forbidden(), spec)
    assert any("completely safe" in f for f in failures)


def test_check_response_flags_missing_disclaimer():
    resp = _good_response()
    resp.disclaimer = ""
    spec = {"expected_keywords_any": [], "forbidden_keywords": [], "requires_disclaimer": True, "min_evidence": 0}
    failures = run_llm_eval._check_response(resp, spec)
    assert any("disclaimer missing" in f for f in failures)


def test_check_response_flags_evidence_count():
    spec = {"expected_keywords_any": [], "forbidden_keywords": [], "requires_disclaimer": False, "min_evidence": 3}
    failures = run_llm_eval._check_response(_good_response(), spec)
    assert any("evidence count 2 < required 3" in f for f in failures)


def test_check_response_keyword_match_is_case_insensitive():
    spec = {"expected_keywords_any": ["bhi"], "forbidden_keywords": [], "requires_disclaimer": False, "min_evidence": 0}
    failures = run_llm_eval._check_response(_good_response(), spec)
    assert failures == []


def test_check_response_scans_all_text_fields():
    """A forbidden phrase hidden in key_findings must still be flagged."""
    resp = _good_response()
    resp.key_findings = [
        AIKeyFinding(title="hidden", description="complies with GB/T 12345", severity="info"),
    ]
    spec = {"expected_keywords_any": [], "forbidden_keywords": ["GB/T"], "requires_disclaimer": False, "min_evidence": 0}
    failures = run_llm_eval._check_response(resp, spec)
    assert any("GB/T" in f for f in failures)


# --------------------------------------------------------------------- spec parsing
def test_main_reads_jsonl_skips_comments_and_blanks(tmp_path, monkeypatch, capsys):
    """main() should parse JSONL, skip # comments and blank lines, and
    exit 2 when no queries pass (none here, empty building DB)."""
    # Prepare an eval set with comments + blanks
    eval_path = tmp_path / "spec.jsonl"
    eval_path.write_text(
        "# this is a header comment\n"
        "\n"
        "  \n"
        '{"qid": "X1", "query": "test", "category": "meta", "expected_keywords_any": [], "forbidden_keywords": [], "requires_disclaimer": false, "min_evidence": 0}\n'
        "# another comment\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_PROVIDER", "mock")
    # An empty DB means every query fails to build a context — but the
    # runner should still parse the spec and emit a JSON report.
    # We use the default DB which has seed data; just verify it parses.
    rc = run_llm_eval.main(["--eval-set", str(eval_path), "--limit", "1"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["n_queries"] == 1
    assert data["results"][0]["qid"] == "X1"


def test_main_missing_eval_set_returns_1(tmp_path, capsys):
    rc = run_llm_eval.main(["--eval-set", str(tmp_path / "nope.jsonl")])
    assert rc == 1
    out = capsys.readouterr().out
    assert "not found" in out


def test_main_exit_code_2_on_failure(tmp_path, monkeypatch, capsys):
    """A spec demanding an unrealistically large evidence count returns
    exit code 2 (mock provider yields ~9 evidence items, never 9999)."""
    eval_path = tmp_path / "fail.jsonl"
    eval_path.write_text(
        json.dumps({
            "qid": "FAIL-1",
            "query": "Anything",
            "category": "meta",
            "expected_keywords_any": [],
            "forbidden_keywords": [],
            "requires_disclaimer": False,
            "min_evidence": 9999,  # guaranteed unmet by mock
        }) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_PROVIDER", "mock")
    rc = run_llm_eval.main(["--eval-set", str(eval_path)])
    assert rc == 2
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["n_failed"] >= 1


# --------------------------------------------------------------------- report shape
def test_report_includes_per_category_breakdown(tmp_path, monkeypatch, capsys):
    eval_path = tmp_path / "spec.jsonl"
    eval_path.write_text(
        json.dumps({
            "qid": "A", "query": "q", "category": "BHI",
            "expected_keywords_any": [], "forbidden_keywords": [],
            "requires_disclaimer": True, "min_evidence": 0,
        }) + "\n" +
        json.dumps({
            "qid": "B", "query": "q", "category": "risk",
            "expected_keywords_any": [], "forbidden_keywords": [],
            "requires_disclaimer": True, "min_evidence": 0,
        }) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_PROVIDER", "mock")
    run_llm_eval.main(["--eval-set", str(eval_path)])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "by_category" in data
    assert "BHI" in data["by_category"]
    assert "risk" in data["by_category"]
    assert data["by_category"]["BHI"]["total"] == 1
    assert data["by_category"]["risk"]["total"] == 1


def test_response_text_includes_all_scanned_fields():
    """A response_text helper should concatenate answer + key_findings +
    actions + evidence + disclaimer so keyword checks span all surfaces."""
    resp = _good_response()
    text = run_llm_eval._response_text(resp)
    assert "Building 1" in text  # answer
    assert "BHI" in text  # key finding
    assert "Monitor" in text  # action
    assert "crack_width" in text  # evidence
    assert "decision support" in text  # disclaimer
