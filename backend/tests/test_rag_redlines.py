"""
RAG Redlines Tests · Phase 6B
==============================

Tests that RAG-related forbidden phrases are caught:
- LLM output containing knowledge document claims
- Service response with knowledge_evidence that contains banned phrases
- Knowledge documents themselves are scanned (Phase 6B security)
- Prompt grounding: knowledge ≠ engineering data (distinct fields)
"""
from datetime import datetime

import pytest

from app.ai.redlines import (
    AI_FORBIDDEN_PHRASES,
    scan_redlines,
    scan_response_for_redlines,
)
from pathlib import Path


# ============ RAG-specific forbidden phrases in list ============
RAG_FORBIDDEN = [
    "the knowledge document proves",
    "the knowledge document confirms",
    "the knowledge document is the official",
    "per the retrieved standard",
    "knowledge document replaces",
    "knowledge overrides engineering data",
    "building is certified based on knowledge",
    "knowledge document describes this building",
]


@pytest.mark.parametrize("phrase", RAG_FORBIDDEN)
def test_rag_forbidden_in_phrase_list(phrase):
    """RAG 红线必须出现在 AI_FORBIDDEN_PHRASES 列表中."""
    assert phrase in AI_FORBIDDEN_PHRASES


# ============ scan_response_for_redlines ============
def test_scan_response_catches_knowledge_proves():
    text = "Based on the knowledge document proves the building has cracks."
    found = scan_response_for_redlines(answer=text)
    assert "the knowledge document proves" in found


def test_scan_response_catches_knowledge_certifies():
    text = "The building is certified based on knowledge retrieved."
    found = scan_response_for_redlines(answer=text)
    assert "building is certified based on knowledge" in found


def test_scan_response_no_false_positive_on_benign_use():
    """'knowledge' 单字不禁止, 只禁有害的具体组合."""
    text = "Background knowledge is available in the project notes."
    found = scan_response_for_redlines(answer=text)
    # 应为空 (无有害组合)
    assert found == []


# ============ Knowledge documents 自身不违反 ============
def test_knowledge_documents_contain_no_self_referential_violations():
    """知识文档自身可含 'knowledge' 单词, 但不能含 RAG 红线有害组合."""
    knowledge_dir = Path(__file__).resolve().parent.parent / "knowledge"
    assert knowledge_dir.exists()
    violations = []
    for md in sorted(knowledge_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        for phrase in RAG_FORBIDDEN:
            if phrase in text.lower():
                violations.append((md.name, phrase))
    assert violations == [], f"Found RAG forbidden phrases in knowledge: {violations}"


def test_knowledge_documents_no_national_standard_numbers():
    """知识文档不得含具体国家/行业标准编号 (GB/T, JGJ 等)."""
    knowledge_dir = Path(__file__).resolve().parent.parent / "knowledge"
    assert knowledge_dir.exists()
    banned_patterns = ["GB/T", "GB 5", "JGJ ", "ISO 4", "ACI 318", "Eurocode"]
    violations = []
    for md in sorted(knowledge_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        for pat in banned_patterns:
            if pat in text:
                violations.append((md.name, pat))
    assert violations == [], f"Found standard references: {violations}"


def test_knowledge_documents_have_prototype_disclaimer():
    """每个 .md 必须含 'Prototype' 字样 ≥ 1 次."""
    knowledge_dir = Path(__file__).resolve().parent.parent / "knowledge"
    for md in sorted(knowledge_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        assert "Prototype" in text or "prototype" in text, (
            f"{md.name} missing 'Prototype' disclaimer"
        )


def test_knowledge_documents_have_source_label():
    """每个 .md 必须含 'BuildHealth Internal' 字样 ≥ 1 次 (source 声明)."""
    knowledge_dir = Path(__file__).resolve().parent.parent / "knowledge"
    for md in sorted(knowledge_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        assert "BuildHealth Internal" in text, (
            f"{md.name} missing source label 'BuildHealth Internal'"
        )


# ============ Grounding: knowledge ≠ engineering data ============
def test_ai_response_evidence_and_knowledge_evidence_are_distinct_fields():
    """AIResponse 必须同时有 evidence (engineering) 和 knowledge_evidence (knowledge) 两个字段."""
    from app.ai.schemas import AIResponse
    schema_fields = AIResponse.model_fields.keys()
    assert "evidence" in schema_fields
    assert "knowledge_evidence" in schema_fields
    # 字段独立
    assert AIResponse.model_fields["evidence"] is not AIResponse.model_fields["knowledge_evidence"]


def test_real_provider_knowledge_evidence_forced_from_input():
    """Real provider: response.knowledge_evidence 必须等于传入, 不取 LLM 输出."""
    from app.ai.real_provider import OpenAICompatibleProvider
    from app.ai.schemas import AIResponse
    from unittest.mock import MagicMock, patch
    import json

    input_knowledge = [
        {"document": "x.md", "section": "S", "content": "C",
         "relevance_score": 0.5, "source": "BuildHealth", "chunk_id": "x::0"}
    ]
    p = OpenAICompatibleProvider(
        api_key="k", base_url="https://x", model="m"
    )
    # LLM output 含 fake knowledge evidence (想覆盖)
    llm_output = {
        "answer": "ok",
        "key_findings": [],
        "evidence": [],
        "knowledge_evidence": [
            {"document": "FAKE.md", "section": "INJECTED", "content": "BAD",
             "relevance_score": 0.99, "source": "FAKE", "chunk_id": "fake::0"}
        ],
        "recommended_actions": [],
        "disclaimer": "x",
    }
    with patch("app.ai.real_provider.httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={
                "choices": [{"message": {"content": json.dumps(llm_output)}}]
            }),
        )
        # Use a minimal context
        from app.ai.schemas import EngineeringContext, ContextBuildingInfo, ContextMonitoringSummary, ContextHealthInfo, ContextRiskInfo, ContextRetrofitInfo
        ctx = EngineeringContext(
            building_id=1,
            building=ContextBuildingInfo(
                building_id=1, name="B", address="a", year_built=2010,
                current_age=15, design_life=50, building_type="office",
                structure_type="frame", floors=10, area=5000.0,
            ),
            sensors=[], components=[],
            monitoring_summary=ContextMonitoringSummary(
                total_records=0, by_metric={}, anomaly_total=0,
                anomaly_by_severity={}, anomaly_by_method={},
            ),
            health=ContextHealthInfo(bhi=80.0, dimensions={}, weakest_dimension=None),
            risk=ContextRiskInfo(risk_level="Normal"),
            retrofit=ContextRetrofitInfo(
                overall_priority=0.0, overall_priority_level="Low",
                calculation_version="RP-v1.0", recommendation_count=0,
                recommendations=[], engineering_notes=[],
            ),
            evidence_chain=[], disclaimer="x", generated_at=datetime.utcnow(),
        )
        r = p.generate_answer(ctx, "test", knowledge_evidence=input_knowledge)
    # 输入的 knowledge_evidence 应被保留 (不被 LLM 覆盖)
    assert len(r.knowledge_evidence) == 1
    assert r.knowledge_evidence[0]["document"] == "x.md"
    # LLM 注入的 FAKE.md 不应出现
    assert not any(e.get("document") == "FAKE.md" for e in r.knowledge_evidence)
