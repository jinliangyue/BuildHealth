"""
AI Context Builder 测试 · Phase 5 V3
"""
from datetime import datetime, timedelta
import random

import pytest

from app.ai.context_builder import build_engineering_context
from app.core.config import AI_VERSION


# ============ Fixtures ============
@pytest.fixture
def sample_healthy_building(test_session):
    from app.db import models as m
    b = m.Building(
        name="AI Healthy",
        address="addr",
        year_built=2020,
        building_type="office",
        structure_type="frame",
        floors=5,
        area=2000.0,
        design_life=50,
        current_age=5,
    )
    test_session.add(b)
    test_session.flush()
    return b


@pytest.fixture
def sample_full_building(test_session):
    """带 30 天监测 + anomalies 的完整建筑."""
    from app.db import models as m
    from app.analytics import anomaly as anom
    from app.analytics.config import ANOMALY_DEDUP_HOURS

    b = m.Building(
        name="AI Full",
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
        ("crack_width", "mm"),
        ("tilt", "‰"),
        ("temperature", "℃"),
        ("humidity", "%"),
        ("electricity", "kWh"),
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
    return b


# ============ Tests ============
def test_building_not_found(test_session):
    assert build_engineering_context(test_session, 99999) is None


def test_healthy_building_context(test_session, sample_healthy_building):
    b = sample_healthy_building
    ctx = build_engineering_context(test_session, b.id)
    assert ctx is not None
    assert ctx.building_id == b.id
    assert ctx.building.name == "AI Healthy"
    assert ctx.retrofit.recommendation_count == 0
    assert ctx.retrofit.overall_priority == 0.0


def test_full_building_context(test_session, sample_full_building):
    b = sample_full_building
    ctx = build_engineering_context(test_session, b.id)
    assert ctx is not None
    # Health
    assert ctx.health.bhi is not None
    assert ctx.health.bhi > 0
    assert ctx.health.weakest_dimension is not None
    assert ctx.health.calculation_version == "BHI-v1.0"
    # Risk
    assert ctx.risk.risk_level in ("Normal", "Attention", "Abnormal", "HighRisk")
    # Retrofit
    assert ctx.retrofit.recommendation_count >= 0
    # Monitoring summary
    assert ctx.monitoring_summary.total_records > 0
    assert len(ctx.monitoring_summary.by_metric) >= 1
    # Evidence chain
    assert len(ctx.evidence_chain) >= 1
    # Components + sensors
    assert len(ctx.components) >= 1
    assert len(ctx.sensors) >= 1
    # Disclaimer
    assert "Prototype" in ctx.disclaimer
    assert "qualified" in ctx.disclaimer.lower() or "professional" in ctx.disclaimer.lower()


def test_context_version(test_session, sample_full_building):
    b = sample_full_building
    ctx = build_engineering_context(test_session, b.id)
    assert ctx.context_version == "CTX-v1.0"


def test_evidence_chain_includes_top_anomalies(test_session, sample_full_building):
    b = sample_full_building
    ctx = build_engineering_context(test_session, b.id)
    # 顶层 evidence 至少包含 building + health + risk
    types = {e.source_type for e in ctx.evidence_chain}
    assert "building" in types
    assert "health" in types
    assert "risk" in types


def test_reuses_v1_assessment(test_session, sample_full_building):
    """BHI 必须与直接调用 assessment_svc 一致 (不强写库)."""
    from app.services import assessment as svc
    from app.db import models as m
    b = sample_full_building
    anomalies = svc.run_anomaly_detection(test_session, b.id)
    health_direct = svc.compute_health_assessment(test_session, b, anomalies)
    ctx = build_engineering_context(test_session, b.id)
    assert ctx.health.bhi == health_direct["score"]


def test_reuses_v2_retrofit(test_session, sample_full_building):
    """Retrofit 计数必须与 retrofit_svc 一致."""
    from app.services import retrofit_service as svc
    b = sample_full_building
    decision = svc.get_retrofit_decision(test_session, b.id)
    ctx = build_engineering_context(test_session, b.id)
    assert ctx.retrofit.recommendation_count == len(decision["recommendations"])


def test_does_not_modify_db(test_session, sample_full_building):
    """Context builder 不写库."""
    from app.db import models as m
    b = sample_full_building
    # 计数前后
    rec_before = test_session.query(m.MonitoringRecord).count()
    alert_before = test_session.query(m.RiskAlert).count()
    assess_before = test_session.query(m.HealthAssessment).count()
    build_engineering_context(test_session, b.id)
    rec_after = test_session.query(m.MonitoringRecord).count()
    alert_after = test_session.query(m.RiskAlert).count()
    assess_after = test_session.query(m.HealthAssessment).count()
    assert rec_before == rec_after
    assert alert_before == alert_after
    assert assess_before == assess_after


def test_sensors_have_record_count(test_session, sample_full_building):
    b = sample_full_building
    ctx = build_engineering_context(test_session, b.id)
    for s in ctx.sensors:
        assert s.record_count >= 0
        if s.record_count > 0:
            assert s.latest_value is not None
            assert s.latest_timestamp is not None


def test_monitoring_summary_anomaly_by_severity(test_session, sample_full_building):
    b = sample_full_building
    ctx = build_engineering_context(test_session, b.id)
    sev = ctx.monitoring_summary.anomaly_by_severity
    assert "high" in sev
    assert "medium" in sev
    assert "low" in sev
    assert ctx.monitoring_summary.anomaly_total == sum(sev.values())


def test_building_info_fields(test_session, sample_full_building):
    b = sample_full_building
    ctx = build_engineering_context(test_session, b.id)
    info = ctx.building
    assert info.building_id == b.id
    assert info.current_age == 15
    assert info.design_life == 50
    assert info.floors == 10


def test_generated_at_recent(test_session, sample_full_building):
    b = sample_full_building
    ctx = build_engineering_context(test_session, b.id)
    assert (datetime.utcnow() - ctx.generated_at).total_seconds() < 5
