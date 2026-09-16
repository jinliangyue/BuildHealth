"""
AI Mock Provider 测试 · Phase 5 V3
"""
from datetime import datetime, timedelta
import random

import pytest

from app.ai.context_builder import build_engineering_context
from app.ai.mock_provider import MockProvider
from app.core.config import AI_VERSION



# ============ Fixtures ============
@pytest.fixture
def full_context(test_session):
    from app.db import models as m
    from app.analytics import anomaly as anom
    from app.analytics.config import ANOMALY_DEDUP_HOURS

    b = m.Building(
        name="Mock Test Building",
        address="addr",
        year_built=2010,
        building_type="office",
        structure_type="frame",
        floors=10,
        area=5000.0,
        design_life=50,
        current_age=15,
    )
    test_session.add(b)
    test_session.flush()
    c = m.Component(building_id=b.id, name="C1", component_type="column", location="loc")
    test_session.add(c)
    test_session.flush()
    sensors = []
    for metric, unit in [
        ("crack_width", "mm"), ("tilt", "‰"), ("temperature", "℃"),
        ("humidity", "%"), ("electricity", "kWh"),
    ]:
        s = m.Sensor(
            building_id=b.id, component_id=c.id, sensor_type=metric,
            name=f"{metric}_sensor", unit=unit, location="loc", status="active",
        )
        test_session.add(s)
        sensors.append(s)
    test_session.flush()
    end = datetime.utcnow().replace(microsecond=0, second=0, minute=0)
    rng = random.Random(42)
    profiles = {
        "crack_width": (0.10, 0.01, 0.01),
        "tilt": (1.0, 0.05, 0.05),
        "temperature": (22.0, 0.0, 1.5),
        "humidity": (75.0, 0.2, 3.0),
        "electricity": (120.0, 0.0, 30.0),
    }
    for s in sensors:
        base, trend, noise = profiles[s.sensor_type]
        for i in range(30):
            ts = end - timedelta(days=30 - i)
            val = base + trend * i + rng.gauss(0, noise)
            if s.sensor_type == "crack_width":
                val = max(0.0, val)
            elif s.sensor_type == "humidity":
                val = max(0.0, min(100.0, val))
            test_session.add(m.MonitoringRecord(
                sensor_id=s.id, timestamp=ts, value=val, quality_flag="simulated",
            ))
    test_session.flush()
    for s in sensors:
        records = (
            test_session.query(m.MonitoringRecord)
            .filter(m.MonitoringRecord.sensor_id == s.id)
            .order_by(m.MonitoringRecord.timestamp).all()
        )
        seen = {}
        for i, rec in enumerate(records):
            prev = records[i - 1].value if i > 0 else None
            history = [r.value for r in records[max(0, i - 168):i]]
            results = anom.detect_for_record(
                sensor_id=s.id, building_id=b.id, metric=s.sensor_type,
                timestamp=rec.timestamp, value=rec.value,
                previous_value=prev, history_values=history,
            )
            for a in results:
                sig = (s.id, s.sensor_type, a.detection_method, a.severity)
                last_ts = seen.get(sig)
                if last_ts and (rec.timestamp - last_ts).total_seconds() < ANOMALY_DEDUP_HOURS * 3600:
                    continue
                seen[sig] = rec.timestamp
                test_session.add(m.RiskAlert(
                    building_id=b.id, sensor_id=s.id, metric=s.sensor_type,
                    timestamp=rec.timestamp, current_value=a.current_value,
                    baseline_value=a.baseline_value, change=a.change,
                    detection_method=a.detection_method, severity=a.severity,
                    explanation=a.explanation, status="active",
                ))
    test_session.flush()
    return build_engineering_context(test_session, b.id)


# ============ health_check ============
def test_health_check_returns_ok():
    p = MockProvider()
    h = p.health_check()
    assert h.status == "ok"
    assert h.provider == "mock"
    assert h.model == "mock-deterministic-v1"
    assert "Mock" in h.message or "demonstration" in h.message.lower()


# ============ generate_summary ============
def test_generate_summary_returns_response(full_context):
    p = MockProvider()
    r = p.generate_summary(full_context)
    assert r is not None
    assert r.answer != ""
    assert r.disclaimer != ""
    assert r.calculation_version == AI_VERSION
    assert r.provider == "mock"


def test_summary_disclaimer_contains_keywords(full_context):
    p = MockProvider()
    r = p.generate_summary(full_context)
    assert "Prototype" in r.disclaimer
    assert "qualified" in r.disclaimer.lower() or "professional" in r.disclaimer.lower()


def test_summary_key_findings_present(full_context):
    p = MockProvider()
    r = p.generate_summary(full_context)
    assert len(r.key_findings) >= 1
    for kf in r.key_findings:
        assert kf.title
        assert kf.description
        assert kf.severity in ("info", "low", "medium", "high")


def test_summary_evidence_present(full_context):
    p = MockProvider()
    r = p.generate_summary(full_context)
    assert len(r.evidence) >= 1
    for e in r.evidence:
        assert e.source_type
        assert e.description


def test_summary_recommended_actions_present(full_context):
    p = MockProvider()
    r = p.generate_summary(full_context)
    assert len(r.recommended_actions) >= 1
    for a in r.recommended_actions:
        assert a.action
        assert a.reason
        assert a.urgency in ("low", "medium", "high")


def test_summary_numbers_match_context(full_context):
    """answer 中的数字 (BHI / risk_level) 必须与 context 一致."""
    p = MockProvider()
    r = p.generate_summary(full_context)
    if full_context.health.bhi is not None:
        assert f"{full_context.health.bhi:.2f}" in r.answer
    if full_context.risk.risk_level:
        assert full_context.risk.risk_level in r.answer


def test_summary_does_not_fabricate_data(full_context):
    """answer 不应编造新数字 / 传感器."""
    p = MockProvider()
    r = p.generate_summary(full_context)
    # answer 不应包含不存在的 sensor 编号
    for e in r.evidence:
        if e.source_type == "sensor" and e.source_id is not None:
            assert e.source_id in {s.id for s in full_context.sensors}


# ============ generate_answer (问题路由) ============
@pytest.mark.parametrize("question", [
    "总结这栋建筑的健康状况",
    "summarize building health",
    "Health status please",
    "建筑的总体状况如何",
])
def test_answer_summary_route(full_context, question):
    p = MockProvider()
    r = p.generate_answer(full_context, question)
    # 综述路由 → 包含 building name
    assert full_context.building.name in r.answer


def test_answer_risk_route(full_context):
    p = MockProvider()
    r = p.generate_answer(full_context, "Why is this building at high risk?")
    # risk 路由 → 包含 risk_level
    if full_context.risk.risk_level:
        assert full_context.risk.risk_level in r.answer
    assert "Prototype Risk" in r.answer


def test_answer_retrofit_route(full_context):
    p = MockProvider()
    r = p.generate_answer(full_context, "Explain retrofit priorities")
    # retrofit 路由 → 包含 calculation_version
    if full_context.retrofit.calculation_version:
        assert full_context.retrofit.calculation_version in r.answer


def test_answer_anomaly_route(full_context):
    p = MockProvider()
    r = p.generate_answer(full_context, "What anomalies exist?")
    assert "anomaly" in r.answer.lower() or "anomalies" in r.answer.lower()


def test_answer_default_route(full_context):
    p = MockProvider()
    r = p.generate_answer(full_context, "Some random question xyz")
    # default → 同 summary
    assert full_context.building.name in r.answer


def test_answer_strips_whitespace(full_context):
    p = MockProvider()
    r1 = p.generate_answer(full_context, "  summarize  ")
    r2 = p.generate_answer(full_context, "summarize")
    assert r1.answer == r2.answer
