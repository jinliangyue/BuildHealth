"""
Knowledge Service Tests · Phase 6B
===================================

Tests the integration of KnowledgeRetriever with AIService:
- summary / ask include knowledge_evidence
- retriever failures don't break service (graceful degradation)
- build_retrieval_query includes metric / risk / category hints
"""
from datetime import datetime
import pytest

from app.ai.service import get_ai_service
from app.knowledge.query_builder import build_retrieval_query
from app.knowledge.schemas import KnowledgeEvidence


def test_build_retrieval_query_includes_user_question():
    from app.ai.schemas import (
        ContextBuildingInfo, ContextMonitoringSummary, ContextHealthInfo,
        ContextRiskInfo, ContextRetrofitInfo, EngineeringContext,
    )
    ctx = EngineeringContext(
        building_id=1,
        building=ContextBuildingInfo(
            building_id=1, name="B", address="a", year_built=2010,
            current_age=15, design_life=50, building_type="office",
            structure_type="frame", floors=10, area=5000.0,
        ),
        sensors=[],
        monitoring_summary=ContextMonitoringSummary(
            total_records=0, by_metric={}, anomaly_total=0,
            anomaly_by_severity={}, anomaly_by_method={},
        ),
        health=ContextHealthInfo(bhi=80.0, dimensions={}, weakest_dimension="structural_safety"),
        risk=ContextRiskInfo(risk_level="Attention"),
        retrofit=ContextRetrofitInfo(
            overall_priority=50.0, overall_priority_level="Medium",
            calculation_version="RP-v1.0", recommendation_count=1,
            recommendations=[{"category": "Structural", "issue_type": "crack_growth"}],
            engineering_notes=[],
        ),
        evidence_chain=[],
        disclaimer="x",
        generated_at=datetime.utcnow(),
    )
    q = build_retrieval_query("why?", ctx)
    # 用户问题保留
    assert "why?" in q
    # risk level 注入
    assert "Attention" in q
    # retrofit category 注入
    assert "structural" in q.lower()
    # issue type 注入
    assert "crack growth" in q


def test_build_retrieval_query_no_risk_when_normal():
    from app.ai.schemas import (
        ContextBuildingInfo, ContextMonitoringSummary, ContextHealthInfo,
        ContextRiskInfo, ContextRetrofitInfo, EngineeringContext,
    )
    ctx = EngineeringContext(
        building_id=1,
        building=ContextBuildingInfo(
            building_id=1, name="B", address="a", year_built=2010,
            current_age=15, design_life=50, building_type="office",
            structure_type="frame", floors=10, area=5000.0,
        ),
        sensors=[],
        monitoring_summary=ContextMonitoringSummary(
            total_records=0, by_metric={}, anomaly_total=0,
            anomaly_by_severity={}, anomaly_by_method={},
        ),
        health=ContextHealthInfo(bhi=95.0, dimensions={}, weakest_dimension=None),
        risk=ContextRiskInfo(risk_level="Normal"),
        retrofit=ContextRetrofitInfo(
            overall_priority=0.0, overall_priority_level="Low",
            calculation_version="RP-v1.0", recommendation_count=0,
            recommendations=[], engineering_notes=[],
        ),
        evidence_chain=[],
        disclaimer="x",
        generated_at=datetime.utcnow(),
    )
    q = build_retrieval_query("hi", ctx)
    # Normal 不注入
    assert "Normal" not in q
    assert "risk" not in q.lower()


def test_ai_service_summary_includes_knowledge_evidence(test_session, full_building):
    """Default retriever 注入 → summary response 含 knowledge_evidence."""
    from app.ai.provider_factory import reset_ai_provider
    reset_ai_provider()
    svc = get_ai_service()
    # 验证 retriever 已注入
    assert svc.knowledge_retriever is not None
    b = full_building
    r = svc.summarize_building(test_session, b.id)
    assert r is not None
    # knowledge_evidence 必有字段
    assert hasattr(r, "knowledge_evidence")
    assert isinstance(r.knowledge_evidence, list)
    # default retriever 至少能返回一些 chunks (e.g. health_assessment.md 命中 "BHI")
    # 不强制非空 (query 可能不命中), 只验证 schema


def test_ai_service_ask_includes_knowledge_evidence(test_session, full_building):
    from app.ai.provider_factory import reset_ai_provider
    reset_ai_provider()
    svc = get_ai_service()
    b = full_building
    r = svc.ask_about_building(test_session, b.id, "Why is BHI low?")
    assert r is not None
    assert isinstance(r.knowledge_evidence, list)


def test_ai_service_graceful_degradation_when_retriever_raises(test_session, full_building):
    """若 retriever 抛异常, service 不应崩, knowledge_evidence 应为空."""
    from app.ai.provider_factory import reset_ai_provider
    from app.ai import service as svc_mod

    reset_ai_provider()
    svc = get_ai_service()

    # 替换 retriever 为抛异常的
    class _BoomRetriever:
        def retrieve(self, q):
            raise RuntimeError("boom")

    svc.knowledge_retriever = _BoomRetriever()
    b = full_building
    r = svc.summarize_building(test_session, b.id)
    assert r is not None
    assert r.knowledge_evidence == []  # 优雅降级


def test_ai_service_with_no_retriever(test_session, full_building):
    """knowledge_retriever=None → knowledge_evidence 始终为空."""
    from app.ai.provider_factory import reset_ai_provider
    from app.ai.mock_provider import MockProvider

    reset_ai_provider()
    svc = get_ai_service()
    svc.knowledge_retriever = None
    svc.provider = MockProvider()
    b = full_building
    r = svc.summarize_building(test_session, b.id)
    assert r is not None
    assert r.knowledge_evidence == []
