"""
Retrofit Recommendation Rule Engine 测试 · Phase 4 V2
======================================================

测试每条规则的:
- 触发条件
- 不触发返回空列表
- urgency / cost_level / evidence 字段正确
- 5 条规则同时触发时返回 5 条结果
"""
from datetime import datetime, timedelta
import pytest

from app.analytics import recommendation_rules as rules
from app.analytics.config import RECOMMENDATION_RULES_VERSION


# ============ Helper ============
def _make_ctx(
    health: dict = None,
    risk: dict = None,
    anomalies: list = None,
    sensors_by_metric: dict = None,
    components: list = None,
    building_id: int = 1,
):
    """构造 RuleContext (不依赖真实 DB)."""
    from app.db import models as m

    building = m.Building(
        id=building_id,
        name=f"B{building_id}",
        address="addr",
        year_built=2010,
        building_type="office",
        structure_type="frame",
        floors=10,
        area=5000.0,
        design_life=50,
        current_age=15,
    )
    # 使用固定 ID 以便测试断言
    sensor_ids = {"crack_width": 1, "tilt": 2, "humidity": 3, "electricity": 4}
    units = {"crack_width": "mm", "tilt": "‰", "humidity": "%", "electricity": "kWh"}
    sensors = []
    for metric, sid in sensor_ids.items():
        s = m.Sensor(
            id=sid,
            building_id=building_id,
            sensor_type=metric,
            name=f"{metric}_sensor",
            unit=units[metric],
            location="test",
        )
        sensors.append(s)
    sbm = sensors_by_metric or {s.sensor_type: [s] for s in sensors}

    if components is None:
        c1 = m.Component(
            id=1, building_id=building_id, name="C1",
            component_type="column", location="loc",
        )
        components = [c1]

    return rules.RuleContext(
        building=building,
        health=health or {},
        risk=risk or {"risk_level": "Normal"},
        anomalies=anomalies or [],
        sensors_by_metric=sbm,
        components=components,
    )


# ============ rule_crack_growth ============
def test_crack_growth_no_anomalies_no_zscore_returns_empty():
    ctx = _make_ctx()
    rvs = {}
    assert rules.rule_crack_growth(ctx, rvs) == []


def test_crack_growth_with_anomaly_triggers():
    ctx = _make_ctx(
        anomalies=[{
            "sensor_id": 1, "metric": "crack_width", "severity": "medium",
            "detection_method": "threshold", "current_value": 0.25,
            "timestamp": datetime(2026, 1, 1),
        }]
    )
    rvs = {1: [{"timestamp": "2026-01-01", "value": 0.25}]}
    results = rules.rule_crack_growth(ctx, rvs)
    assert len(results) == 1
    assert results[0].urgency == "medium"  # 0 high → medium
    assert results[0].estimated_cost_level == "medium"
    assert results[0].expected_benefit == "high"
    assert results[0].category == "Structural"
    assert results[0].issue_type == "crack_growth"
    assert results[0].source == "rule:crack_growth"
    assert "evidence" in results[0].to_dict()


def test_crack_growth_with_high_severity_high_urgency():
    ctx = _make_ctx(
        anomalies=[{
            "sensor_id": 1, "metric": "crack_width", "severity": "high",
            "detection_method": "threshold", "current_value": 0.45,
            "timestamp": datetime(2026, 1, 1),
        }]
    )
    rvs = {1: [{"timestamp": "2026-01-01", "value": 0.45}]}
    results = rules.rule_crack_growth(ctx, rvs)
    assert results[0].urgency == "high"


def test_crack_growth_with_zscore_triggers():
    """无 anomaly 但 zscore abs > 2 时也触发."""
    s_id = 1
    # 100 个稳定值 + 1 个极端值
    history = [0.10 + 0.0001 * i for i in range(99)]
    ctx = _make_ctx(anomalies=[])
    rvs = {s_id: [{"timestamp": f"2026-01-{i+1:02d}", "value": v} for i, v in enumerate(history + [5.0])]}
    results = rules.rule_crack_growth(ctx, rvs)
    assert len(results) == 1


# ============ rule_tilt_trend ============
def test_tilt_no_signal_returns_empty():
    ctx = _make_ctx()
    assert rules.rule_tilt_trend(ctx, {}) == []


def test_tilt_with_anomaly_triggers():
    ctx = _make_ctx(
        anomalies=[{
            "sensor_id": 1, "metric": "tilt", "severity": "high",
            "detection_method": "threshold", "current_value": 4.5,
            "timestamp": datetime(2026, 1, 1),
        }]
    )
    rvs = {1: [{"timestamp": "2026-01-01", "value": 4.5}]}
    results = rules.rule_tilt_trend(ctx, rvs)
    assert len(results) == 1
    assert results[0].urgency == "high"
    assert results[0].issue_type == "tilt_trend"


# ============ rule_moisture_control ============
def test_moisture_no_signal_returns_empty():
    ctx = _make_ctx(health={"environmental_quality": 90.0})
    assert rules.rule_moisture_control(ctx, {}) == []


def test_moisture_with_low_env_triggers_medium():
    ctx = _make_ctx(health={"environmental_quality": 70.0})
    results = rules.rule_moisture_control(ctx, {})
    assert len(results) == 1
    assert results[0].urgency == "medium"
    assert results[0].estimated_cost_level == "low"


def test_moisture_with_very_low_env_triggers_high():
    ctx = _make_ctx(health={"environmental_quality": 50.0})
    results = rules.rule_moisture_control(ctx, {})
    assert results[0].urgency == "high"


def test_moisture_with_humidity_anomaly_triggers():
    ctx = _make_ctx(
        health={"environmental_quality": 90.0},
        anomalies=[{
            "sensor_id": 1, "metric": "humidity", "severity": "medium",
            "detection_method": "threshold", "current_value": 90.0,
            "timestamp": datetime(2026, 1, 1),
        }],
    )
    results = rules.rule_moisture_control(ctx, {})
    assert len(results) == 1


# ============ rule_energy_efficiency ============
def test_energy_no_signal_returns_empty():
    ctx = _make_ctx(health={"energy_performance": 90.0})
    assert rules.rule_energy_efficiency(ctx, {}) == []


def test_energy_with_low_perf_triggers_low_urgency():
    ctx = _make_ctx(health={"energy_performance": 70.0})
    results = rules.rule_energy_efficiency(ctx, {})
    assert len(results) == 1
    assert results[0].urgency == "low"


def test_energy_with_very_low_perf_triggers_medium():
    ctx = _make_ctx(health={"energy_performance": 50.0})
    results = rules.rule_energy_efficiency(ctx, {})
    assert results[0].urgency == "medium"
    assert results[0].estimated_cost_level == "low"


# ============ rule_comprehensive_assessment ============
def test_comprehensive_normal_returns_empty():
    ctx = _make_ctx(risk={"risk_level": "Normal"})
    assert rules.rule_comprehensive_assessment(ctx, {}) == []


def test_comprehensive_attention_returns_empty():
    ctx = _make_ctx(risk={"risk_level": "Attention"})
    assert rules.rule_comprehensive_assessment(ctx, {}) == []


def test_comprehensive_abnormal_triggers_medium():
    ctx = _make_ctx(risk={"risk_level": "Abnormal"})
    results = rules.rule_comprehensive_assessment(ctx, {})
    assert len(results) == 1
    assert results[0].urgency == "medium"
    assert results[0].estimated_cost_level == "high"


def test_comprehensive_highrisk_triggers_high():
    ctx = _make_ctx(risk={"risk_level": "HighRisk"})
    results = rules.rule_comprehensive_assessment(ctx, {})
    assert results[0].urgency == "high"


# ============ Evidence 完整性 ============
def test_evidence_includes_sensors_and_anomalies_and_context():
    ctx = _make_ctx(
        health={"score": 80.0, "weakest_dimension": "structural_safety"},
        risk={"risk_level": "Attention", "explanation": "test"},
        anomalies=[{
            "sensor_id": 1, "metric": "crack_width", "severity": "medium",
            "detection_method": "threshold", "current_value": 0.25,
            "timestamp": datetime(2026, 1, 1),
        }],
    )
    rvs = {1: [{"timestamp": "2026-01-01", "value": 0.25}]}
    results = rules.rule_crack_growth(ctx, rvs)
    ev = results[0].evidence
    assert "sensors" in ev
    assert len(ev["sensors"]) >= 1
    assert "anomalies" in ev
    assert len(ev["anomalies"]) >= 1
    assert ev["bhi_context"] is not None
    assert ev["risk_context"] is not None
    assert ev["bhi_context"]["score"] == 80.0


def test_evidence_anomaly_count_severity_breakdown():
    ctx = _make_ctx(
        anomalies=[
            {"sensor_id": 1, "metric": "crack_width", "severity": "high", "detection_method": "threshold", "current_value": 0.4, "timestamp": datetime(2026, 1, 1)},
            {"sensor_id": 1, "metric": "crack_width", "severity": "high", "detection_method": "threshold", "current_value": 0.45, "timestamp": datetime(2026, 1, 2)},
            {"sensor_id": 1, "metric": "crack_width", "severity": "medium", "detection_method": "threshold", "current_value": 0.25, "timestamp": datetime(2026, 1, 3)},
        ],
    )
    rvs = {1: [{"timestamp": "2026-01-01", "value": 0.4}]}
    results = rules.rule_crack_growth(ctx, rvs)
    sensor_block = results[0].evidence["sensors"][0]
    assert sensor_block["anomaly_count_by_severity"]["high"] == 2
    assert sensor_block["anomaly_count_by_severity"]["medium"] == 1
    assert sensor_block["anomaly_count_by_severity"]["low"] == 0


# ============ 综合: 5 条规则同时触发 ============
def test_all_5_rules_trigger_independently():
    """当所有触发条件都满足时, 5 个 rule 函数分别返回 1 条结果."""
    ctx = _make_ctx(
        health={
            "score": 50.0, "weakest_dimension": "structural_safety",
            "environmental_quality": 50.0,
            "energy_performance": 50.0,
        },
        risk={"risk_level": "HighRisk"},
        anomalies=[
            {"sensor_id": 1, "metric": "crack_width", "severity": "high", "detection_method": "threshold", "current_value": 0.4, "timestamp": datetime(2026, 1, 1)},
            {"sensor_id": 2, "metric": "tilt", "severity": "high", "detection_method": "threshold", "current_value": 4.5, "timestamp": datetime(2026, 1, 1)},
            {"sensor_id": 3, "metric": "humidity", "severity": "medium", "detection_method": "threshold", "current_value": 90.0, "timestamp": datetime(2026, 1, 1)},
            {"sensor_id": 4, "metric": "electricity", "severity": "low", "detection_method": "rate_of_change", "current_value": 200.0, "timestamp": datetime(2026, 1, 1)},
        ],
    )
    rvs = {
        1: [{"timestamp": "2026-01-01", "value": 0.4}],
        2: [{"timestamp": "2026-01-01", "value": 4.5}],
        3: [{"timestamp": "2026-01-01", "value": 90.0}],
        4: [{"timestamp": "2026-01-01", "value": 200.0}],
    }
    r1 = rules.rule_crack_growth(ctx, rvs)
    r2 = rules.rule_tilt_trend(ctx, rvs)
    r3 = rules.rule_moisture_control(ctx, rvs)
    r4 = rules.rule_energy_efficiency(ctx, rvs)
    r5 = rules.rule_comprehensive_assessment(ctx, rvs)
    assert len(r1) == 1
    assert len(r2) == 1
    assert len(r3) == 1
    assert len(r4) == 1
    assert len(r5) == 1
    issue_types = {r[0].issue_type for r in [r1, r2, r3, r4, r5]}
    assert issue_types == {
        "crack_growth", "tilt_trend", "moisture_control",
        "energy_efficiency", "comprehensive_assessment",
    }


# ============ version ============
def test_recommendation_rules_version_constant():
    assert RECOMMENDATION_RULES_VERSION == "REC-v1.0"
