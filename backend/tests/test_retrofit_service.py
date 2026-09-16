"""
Retrofit Service 测试 · Phase 4 V2
==================================

测试 service 层编排:
- 空 recommendations (Healthy 场景)
- 多条 recommendations 排序
- overall_priority = max(priority_scores)
- disclaimer 包含强制关键词
- calculation_version 一致
- evidence chain 完整
"""
import pytest

from app.services import retrofit_service as svc
from app.analytics.config import (
    RETROFIT_DISCLAIMER,
    RETROFIT_PRIORITY_VERSION,
    RECOMMENDATION_RULES_VERSION,
)


# ============ generate_recommendations ============
def test_generate_recommendations_building_not_found(test_session):
    """不存在的 building → 空列表."""
    assert svc.generate_recommendations(test_session, 99999) == []


# ============ get_retrofit_decision ============
def test_get_decision_building_not_found(test_session):
    assert svc.get_retrofit_decision(test_session, 99999) is None


def test_get_decision_includes_disclaimer(test_session, sample_building_with_sensors):
    b, sensors, components = sample_building_with_sensors
    decision = svc.get_retrofit_decision(test_session, b.id)
    assert decision is not None
    assert "disclaimer" in decision
    assert "Prototype" in decision["disclaimer"]
    assert "RP-v1.0" in decision["disclaimer"]


def test_get_decision_calculation_version(test_session, sample_building_with_sensors):
    b, _, _ = sample_building_with_sensors
    decision = svc.get_retrofit_decision(test_session, b.id)
    assert decision["calculation_version"] == RETROFIT_PRIORITY_VERSION


def test_get_decision_recommendations_have_calculation_version(
    test_session, sample_building_with_sensors
):
    b, _, _ = sample_building_with_sensors
    decision = svc.get_retrofit_decision(test_session, b.id)
    for rec in decision["recommendations"]:
        assert rec["calculation_version"] == RECOMMENDATION_RULES_VERSION


def test_get_decision_recommendations_sorted_by_priority_desc(
    test_session, sample_building_with_sensors
):
    b, _, _ = sample_building_with_sensors
    decision = svc.get_retrofit_decision(test_session, b.id)
    recs = decision["recommendations"]
    if len(recs) > 1:
        scores = [r["priority_score"] for r in recs]
        assert scores == sorted(scores, reverse=True)


def test_get_decision_overall_priority_is_max(test_session, sample_building_with_sensors):
    b, _, _ = sample_building_with_sensors
    decision = svc.get_retrofit_decision(test_session, b.id)
    recs = decision["recommendations"]
    if recs:
        assert decision["overall_priority"] == recs[0]["priority_score"]
        assert decision["overall_priority"] == max(r["priority_score"] for r in recs)
    else:
        assert decision["overall_priority"] == 0.0


def test_get_decision_overall_priority_level(test_session, sample_building_with_sensors):
    b, _, _ = sample_building_with_sensors
    decision = svc.get_retrofit_decision(test_session, b.id)
    # level 必须是合法 enum 值
    valid = {"Low", "Medium", "High", "Very High"}
    assert decision["overall_priority_level"].value in valid


def test_get_decision_recommendations_have_id_building_id_created_at(
    test_session, sample_building_with_sensors
):
    b, _, _ = sample_building_with_sensors
    decision = svc.get_retrofit_decision(test_session, b.id)
    for idx, rec in enumerate(decision["recommendations"], start=1):
        assert rec["id"] == idx
        assert rec["building_id"] == b.id
        assert "created_at" in rec


def test_get_decision_evidence_chain_completeness(test_session, sample_building_with_sensors):
    b, sensors, _ = sample_building_with_sensors
    decision = svc.get_retrofit_decision(test_session, b.id)
    for rec in decision["recommendations"]:
        ev = rec["evidence"]
        # evidence 必须包含至少 1 个 sensor
        assert "sensors" in ev
        # evidence 必须包含 bhi/risk context
        assert "bhi_context" in ev
        assert "risk_context" in ev


def test_get_decision_recommendation_priority_breakdown_completeness(
    test_session, sample_building_with_sensors
):
    b, _, _ = sample_building_with_sensors
    decision = svc.get_retrofit_decision(test_session, b.id)
    for rec in decision["recommendations"]:
        bd = rec["priority_breakdown"]
        for k in [
            "risk_severity", "trend", "component_importance",
            "urgency", "cost_efficiency", "total",
        ]:
            assert k in bd
            assert 0 <= bd[k] <= 100
        # contribution 必须 = dim_score * weight
        assert abs(
            bd["risk_severity_contribution"]
            - round(bd["risk_severity"] * 0.35, 2)
        ) < 0.01


# ============ get_retrofit_recommendation ============
def test_get_recommendation_detail_building_not_found(test_session):
    assert svc.get_retrofit_recommendation(test_session, 99999, 1) is None


def test_get_recommendation_detail_no_recs(test_session, sample_empty_building):
    b = sample_empty_building
    assert svc.get_retrofit_recommendation(test_session, b.id, 1) is None


def test_get_recommendation_detail_invalid_id(test_session, sample_building_with_sensors):
    b, _, _ = sample_building_with_sensors
    # ID 超出范围
    result = svc.get_retrofit_recommendation(test_session, b.id, 9999)
    assert result is None


def test_get_recommendation_detail_valid_id(test_session, sample_building_with_sensors):
    b, _, _ = sample_building_with_sensors
    result = svc.get_retrofit_recommendation(test_session, b.id, 1)
    if result is not None:
        assert "id" in result
        assert "priority_score" in result
        assert "priority_breakdown" in result


# ============ get_retrofit_overview ============
def test_get_retrofit_overview_no_buildings(test_session):
    overview = svc.get_retrofit_overview(test_session)
    assert overview["total"] == 0
    assert overview["items"] == []
    assert overview["average_priority"] == 0.0


def test_get_retrofit_overview_with_buildings(test_session, sample_building_with_sensors):
    b, _, _ = sample_building_with_sensors
    overview = svc.get_retrofit_overview(test_session)
    assert overview["total"] >= 1
    assert "average_priority" in overview
    assert overview["calculation_version"] == RETROFIT_PRIORITY_VERSION
    assert "disclaimer" in overview
    # 排序按 overall_priority desc
    if len(overview["items"]) > 1:
        priorities = [it["overall_priority"] for it in overview["items"]]
        assert priorities == sorted(priorities, reverse=True)


def test_overview_includes_all_required_fields(test_session, sample_building_with_sensors):
    b, _, _ = sample_building_with_sensors
    overview = svc.get_retrofit_overview(test_session)
    for item in overview["items"]:
        assert "building" in item
        assert "overall_priority" in item
        assert "overall_priority_level" in item
        assert "recommendation_count" in item
        assert "high_priority_count" in item
        assert "top_category" in item


# ============ Fixtures ============
@pytest.fixture
def sample_empty_building(test_session):
    """一栋没有 sensors/components/records 的建筑 (用于空 rec 测试)."""
    from app.db import models as m
    b = m.Building(
        name="Empty Building",
        address="Empty Address",
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
def sample_building_with_sensors(test_session):
    """一栋有完整 monitoring + anomaly 数据的建筑 (触发多种 rule)."""
    from datetime import datetime, timedelta
    from app.db import models as m
    from app.analytics import anomaly as anom
    from app.analytics import health as ha
    from app.analytics.config import ANOMALY_DEDUP_HOURS
    import random

    b = m.Building(
        name="Test Building",
        address="Test Address",
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

    components = []
    for name, ctype in [
        ("C1", "column"),
        ("B1", "beam"),
        ("W1", "wall"),
    ]:
        c = m.Component(
            building_id=b.id, name=name,
            component_type=ctype, location="loc",
        )
        test_session.add(c)
        components.append(c)
    test_session.flush()

    sensors = []
    sensor_types = ["crack_width", "tilt", "temperature", "humidity", "electricity"]
    units = ["mm", "‰", "℃", "%", "kWh"]
    for metric, unit in zip(sensor_types, units):
        s = m.Sensor(
            building_id=b.id,
            component_id=components[0].id,
            sensor_type=metric,
            name=f"{metric}_sensor",
            unit=unit,
            location="loc",
            status="active",
        )
        test_session.add(s)
        sensors.append(s)
    test_session.flush()

    # 生成 30 天监测数据, crack_width/tilt 加显著趋势确保触发 anomaly
    end = datetime.utcnow().replace(microsecond=0, second=0, minute=0)
    rng = random.Random(42)
    profiles = {
        "crack_width": (0.10, 0.01, 0.01),  # base, trend, noise
        "tilt": (1.0, 0.05, 0.05),
        "temperature": (22.0, 0.0, 1.5),
        "humidity": (75.0, 0.2, 3.0),  # 上升趋势
        "electricity": (120.0, 0.0, 30.0),  # 波动
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

    # 跑 anomaly detection → 写入 RiskAlert
    all_anomalies = []
    for s in sensors:
        records = (
            test_session.query(m.MonitoringRecord)
            .filter(m.MonitoringRecord.sensor_id == s.id)
            .order_by(m.MonitoringRecord.timestamp)
            .all()
        )
        if not records:
            continue
        seen_sigs = {}
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
                last_ts = seen_sigs.get(sig)
                if last_ts and (rec.timestamp - last_ts).total_seconds() < ANOMALY_DEDUP_HOURS * 3600:
                    continue
                seen_sigs[sig] = rec.timestamp
                all_anomalies.append({
                    "sensor_id": a.sensor_id, "metric": a.metric,
                    "timestamp": rec.timestamp, "current_value": a.current_value,
                    "baseline_value": a.baseline_value, "change": a.change,
                    "detection_method": a.detection_method, "severity": a.severity,
                    "explanation": a.explanation,
                })
                test_session.add(m.RiskAlert(
                    building_id=b.id, sensor_id=s.id, metric=s.sensor_type,
                    timestamp=rec.timestamp, current_value=a.current_value,
                    baseline_value=a.baseline_value, change=a.change,
                    detection_method=a.detection_method, severity=a.severity,
                    explanation=a.explanation, status="active",
                ))
    test_session.flush()

    return b, sensors, components
