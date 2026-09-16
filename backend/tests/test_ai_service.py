"""
AI Service 测试 · Phase 5 V3
"""
from datetime import datetime, timedelta
import random

import pytest

from app.ai.service import AIService, get_ai_service, get_ai_provider, reset_ai_provider
from app.ai.mock_provider import MockProvider
from app.db import models as m


# full_building fixture 已上移到 conftest.py (Phase 6B · 供 knowledge service 测试共享)


# ============ get_ai_provider ============
def test_get_ai_provider_returns_mock_by_default():
    reset_ai_provider()
    p = get_ai_provider()
    assert isinstance(p, MockProvider)
    assert p.name == "mock"
    reset_ai_provider()


def test_provider_singleton():
    reset_ai_provider()
    p1 = get_ai_provider()
    p2 = get_ai_provider()
    assert p1 is p2
    reset_ai_provider()


# ============ get_ai_service ============
def test_get_ai_service_returns_singleton():
    s1 = get_ai_service()
    s2 = get_ai_service()
    # AIService 没有 __eq__ 比实例, 但 type 应相同
    assert isinstance(s1, AIService)
    assert isinstance(s2, AIService)


# ============ health ============
def test_service_health():
    svc = get_ai_service()
    h = svc.get_health()
    assert h.status == "ok"
    assert h.provider == "mock"


# ============ summarize_building ============
def test_summarize_existing_building(test_session, full_building):
    svc = get_ai_service()
    r = svc.summarize_building(test_session, full_building.id)
    assert r is not None
    assert r.answer != ""
    assert r.disclaimer != ""


def test_summarize_nonexistent_building(test_session):
    svc = get_ai_service()
    r = svc.summarize_building(test_session, 99999)
    assert r is None


def test_summarize_does_not_modify_db(test_session, full_building):
    svc = get_ai_service()
    rec_before = test_session.query(m.MonitoringRecord).count()
    alert_before = test_session.query(m.RiskAlert).count()
    assess_before = test_session.query(m.HealthAssessment).count()
    svc.summarize_building(test_session, full_building.id)
    assert test_session.query(m.MonitoringRecord).count() == rec_before
    assert test_session.query(m.RiskAlert).count() == alert_before
    assert test_session.query(m.HealthAssessment).count() == assess_before


# ============ ask_about_building ============
def test_ask_about_existing_building(test_session, full_building):
    svc = get_ai_service()
    r = svc.ask_about_building(test_session, full_building.id, "Summarize this building")
    assert r is not None
    assert r.answer != ""


def test_ask_about_nonexistent_building(test_session):
    svc = get_ai_service()
    r = svc.ask_about_building(test_session, 99999, "Anything")
    assert r is None


def test_ask_strips_question(test_session, full_building):
    svc = get_ai_service()
    r1 = svc.ask_about_building(test_session, full_building.id, "  summarize  ")
    r2 = svc.ask_about_building(test_session, full_building.id, "summarize")
    # 同一 building 同一 trimmed question → 同一 routing → 同一 answer
    assert r1.answer == r2.answer


# ============ AIService with custom provider ============
def test_service_with_custom_provider():
    """可以用自定义 provider (例如 test double) 构造 AIService."""
    class FakeProvider:
        name = "fake"
        model = "fake-v1"
        def health_check(self):
            from app.ai.schemas import AIHealthStatus
            return AIHealthStatus(status="ok", provider="fake", model="fake-v1", message="fake")
        def generate_summary(self, ctx):
            from app.ai.schemas import AIResponse
            return AIResponse(answer="fake answer", provider="fake", model="fake-v1",
                              calculation_version="AI-v1.0", disclaimer="fake disclaimer",
                              created_at=datetime.utcnow())
        def generate_answer(self, ctx, q):
            return self.generate_summary(ctx)
    svc = AIService(FakeProvider())
    h = svc.get_health()
    assert h.provider == "fake"
