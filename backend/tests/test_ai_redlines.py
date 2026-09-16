"""
AI Engineering Assistant Safety Redlines · Phase 5 V3
======================================================

强制:
1. Mock Provider 输出 answer / disclaimer / key_findings 不含禁词
2. Disclaimer 必含强制关键词
3. evidence / key_findings / recommended_actions schema 完整
4. 3 个建筑类型 (Healthy / Attention / Abnormal) Mock 输出都通过
"""
from datetime import datetime, timedelta
import random

import pytest

from app.ai.context_builder import build_engineering_context
from app.ai.mock_provider import MockProvider
from app.core.config import AI_DISCLAIMER


# ============ Forbidden phrases (AI specific) ============
AI_FORBIDDEN_PHRASES = [
    # 不得声称安全 / 倒塌
    "this building is safe",
    "this building is unsafe",
    "building will collapse",
    "structure will fail",
    "structure will collapse",
    "structural failure is certain",
    "ai predicts structural failure",
    # 不得声称完成工程鉴定
    "automatic structural appraisal completed",
    "structural appraisal completed",
    "official safety certification",
    "safety certification issued",
    "official certification",
    "real-world deployment occurred",
    "deployed in production",
    # 不得声称自动设计
    "automatic reinforcement design",
    "ai-designed reinforcement",
    "auto-generated structural design",
    "auto-generated reinforcement",
    "ai designed the reinforcement",
    # 不得声称已做检查
    "professional inspection completed",
    "engineer has approved",
    "engineer approved",
    # 不得声称符合标准
    "complies with national standard",
    "符合国家标准",
    "符合行业标准",
    "符合国标",
    # 不得编造绝对结论
    "guaranteed safe",
    "guaranteed to fail",
    "definitely safe",
    "absolutely safe",
    "this is a real building",
    "this is a real monitoring",
]


# ============ Mandatory disclaimer keywords ============
DISCLAIMER_REQUIRED_KEYWORDS = [
    "Prototype",
    "decision support",
    "professional review",
    "qualified",
]


# ============ Fixtures ============
def _build_context(test_session, profile: str):
    from app.db import models as m
    from app.analytics import anomaly as anom
    from app.analytics.config import ANOMALY_DEDUP_HOURS

    if profile == "healthy":
        b = m.Building(name="RL Healthy", address="x", year_built=2020,
                       building_type="office", structure_type="frame", floors=5,
                       area=2000, design_life=50, current_age=5)
    elif profile == "attention":
        b = m.Building(name="RL Attention", address="x", year_built=2005,
                       building_type="mixed", structure_type="shear", floors=8,
                       area=5200, design_life=50, current_age=21)
    else:  # abnormal
        b = m.Building(name="RL Abnormal", address="x", year_built=1995,
                       building_type="residential", structure_type="masonry",
                       floors=6, area=3200, design_life=50, current_age=31)
    test_session.add(b)
    test_session.flush()
    c = m.Component(building_id=b.id, name="C", component_type="column", location="loc")
    test_session.add(c)
    test_session.flush()
    sensors = []
    for metric, unit in [("crack_width", "mm"), ("tilt", "‰"), ("humidity", "%"), ("electricity", "kWh")]:
        s = m.Sensor(building_id=b.id, component_id=c.id, sensor_type=metric,
                     name=f"{metric}_s", unit=unit, location="loc", status="active")
        test_session.add(s)
        sensors.append(s)
    test_session.flush()
    end = datetime.utcnow().replace(microsecond=0, second=0, minute=0)
    base = {"healthy": 0.05, "attention": 0.15, "abnormal": 0.30}[profile]
    for i in range(30):
        for s in sensors:
            if s.sensor_type == "crack_width":
                v = base + 0.01 * i + random.Random(i).gauss(0, 0.01)
            elif s.sensor_type == "tilt":
                v = 1 + 0.05 * i + random.Random(i).gauss(0, 0.05)
            elif s.sensor_type == "humidity":
                v = 60 + 0.3 * i + random.Random(i).gauss(0, 3)
            else:
                v = 100 + random.Random(i).gauss(0, 20)
            test_session.add(m.MonitoringRecord(
                sensor_id=s.id, timestamp=end - timedelta(days=30 - i),
                value=v, quality_flag="simulated",
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


# ============ AI_DISCLAIMER 必须含关键词 ============
@pytest.mark.parametrize("keyword", DISCLAIMER_REQUIRED_KEYWORDS)
def test_disclaimer_required_keyword(keyword):
    assert keyword in AI_DISCLAIMER, (
        f"AI_DISCLAIMER missing required keyword: {keyword}"
    )


# ============ Mock 输出无禁词 ============
@pytest.mark.parametrize("profile", ["healthy", "attention", "abnormal"])
@pytest.mark.parametrize("question", [
    "summarize",
    "risk",
    "retrofit",
    "anomaly",
    "default question",
])
def test_no_forbidden_phrase_in_answer(test_session, profile, question):
    ctx = _build_context(test_session, profile)
    p = MockProvider()
    if question == "summarize":
        r = p.generate_summary(ctx)
    else:
        r = p.generate_answer(ctx, question)
    text = (r.answer + " " + r.disclaimer).lower()
    for forbidden in AI_FORBIDDEN_PHRASES:
        assert forbidden not in text.lower(), (
            f"Forbidden phrase '{forbidden}' in Mock output (profile={profile}, q={question})"
        )


@pytest.mark.parametrize("profile", ["healthy", "attention", "abnormal"])
def test_no_forbidden_phrase_in_key_findings(test_session, profile):
    ctx = _build_context(test_session, profile)
    p = MockProvider()
    r = p.generate_summary(ctx)
    for kf in r.key_findings:
        text = (kf.title + " " + kf.description).lower()
        for forbidden in AI_FORBIDDEN_PHRASES:
            assert forbidden not in text, (
                f"Forbidden phrase '{forbidden}' in key_finding (profile={profile})"
            )


@pytest.mark.parametrize("profile", ["healthy", "attention", "abnormal"])
def test_no_forbidden_phrase_in_recommended_actions(test_session, profile):
    ctx = _build_context(test_session, profile)
    p = MockProvider()
    r = p.generate_summary(ctx)
    for a in r.recommended_actions:
        text = (a.action + " " + a.reason).lower()
        for forbidden in AI_FORBIDDEN_PHRASES:
            assert forbidden not in text, (
                f"Forbidden phrase '{forbidden}' in recommended_action (profile={profile})"
            )


# ============ Schema 完整性 ============
def test_evidence_has_source_type():
    """所有 evidence 必有 source_type."""
    for profile in ["healthy", "attention", "abnormal"]:
        from app.db import models as m
        from app.db.session import SessionLocal
        s = SessionLocal()
        try:
            ctx = _build_context(s, profile)
            r = MockProvider().generate_summary(ctx)
            for e in r.evidence:
                assert e.source_type, f"evidence missing source_type (profile={profile})"
                assert e.description, f"evidence missing description (profile={profile})"
        finally:
            s.close()


def test_key_findings_have_severity():
    for profile in ["healthy", "attention", "abnormal"]:
        from app.db import models as m
        from app.db.session import SessionLocal
        s = SessionLocal()
        try:
            ctx = _build_context(s, profile)
            r = MockProvider().generate_summary(ctx)
            for kf in r.key_findings:
                assert kf.severity in ("info", "low", "medium", "high")
        finally:
            s.close()


# ============ 强制 disclaimer 出现 ============
def test_response_disclaimer_matches_ai_disclaimer():
    from app.db import models as m
    from app.db.session import SessionLocal
    s = SessionLocal()
    try:
        ctx = _build_context(s, "abnormal")
        r = MockProvider().generate_summary(ctx)
        assert r.disclaimer == AI_DISCLAIMER
    finally:
        s.close()


# ============ provider 标识必须显式 ============
def test_response_provider_is_mock():
    from app.db import models as m
    from app.db.session import SessionLocal
    s = SessionLocal()
    try:
        ctx = _build_context(s, "abnormal")
        r = MockProvider().generate_summary(ctx)
        assert r.provider == "mock"
        assert "mock" in r.model.lower()  # 不伪装成真实 LLM
    finally:
        s.close()
