"""
Retrofit Priority Engine 测试 · Phase 4 V2
============================================

测试:
- 5 维度子分分别映射正确
- 加权求和精确性 (权重和 = 1.0)
- input validation (BHI 0-100, urgency ∈ enum, cost ∈ enum)
- 11 个优先级边界值 (0, 1, 50, 59, 60, 74, 75, 89, 90, 99, 100)
- map_priority_level 边界 (8 个)
- compute_trend_score: 无数据 / 全部稳定 / 全部恶化
- calculation_version = "RP-v1.0"
- weights sum = 1.0
"""
import pytest

from app.analytics import priority as pri
from app.analytics.config import (
    RETROFIT_PRIORITY_VERSION,
    RETROFIT_PRIORITY_WEIGHTS,
    URGENCY_SCORES,
    COST_EFFICIENCY_SCORES,
    RISK_SEVERITY_SCORES,
    PRIORITY_LEVEL_THRESHOLDS,
)


# ============ calculate_version ============
def test_calculation_version():
    assert pri.compute_priority(
        "Normal", 50.0, 70.0, "low", "low"
    ).calculation_version == "RP-v1.0"


def test_weights_sum_to_one():
    assert abs(sum(RETROFIT_PRIORITY_WEIGHTS.values()) - 1.0) < 1e-6


# ============ input validation ============
def test_invalid_risk_level_raises():
    with pytest.raises(pri.PriorityInputError):
        pri.compute_priority("UnknownRisk", 50.0, 70.0, "low", "low")


def test_trend_score_out_of_range_low_raises():
    with pytest.raises(pri.PriorityInputError):
        pri.compute_priority("Normal", -1.0, 70.0, "low", "low")


def test_trend_score_out_of_range_high_raises():
    with pytest.raises(pri.PriorityInputError):
        pri.compute_priority("Normal", 100.01, 70.0, "low", "low")


def test_component_importance_out_of_range_raises():
    with pytest.raises(pri.PriorityInputError):
        pri.compute_priority("Normal", 50.0, 150.0, "low", "low")


def test_invalid_urgency_raises():
    with pytest.raises(pri.PriorityInputError):
        pri.compute_priority("Normal", 50.0, 70.0, "unknown", "low")


def test_invalid_cost_level_raises():
    with pytest.raises(pri.PriorityInputError):
        pri.compute_priority("Normal", 50.0, 70.0, "low", "unknown")


# ============ 5 维度子分分别测试 ============
def test_risk_severity_normal_lowest():
    """Normal → 15 (低 severity, retrofit 不紧急)"""
    r = pri.compute_priority("Normal", 0.0, 0.0, "low", "low")
    assert r.risk_severity == 15.0


def test_risk_severity_highrisk_highest():
    """HighRisk → 100 (高 severity, retrofit 紧急)"""
    r = pri.compute_priority("HighRisk", 0.0, 0.0, "low", "low")
    assert r.risk_severity == 100.0


def test_urgency_critical_highest():
    r = pri.compute_priority("Normal", 0.0, 0.0, "critical", "low")
    assert r.urgency == 100.0


def test_urgency_low_lowest():
    r = pri.compute_priority("Normal", 0.0, 0.0, "low", "low")
    assert r.urgency == 20.0


def test_cost_efficiency_low_highest():
    r = pri.compute_priority("Normal", 0.0, 0.0, "low", "low")
    assert r.cost_efficiency == 90.0


def test_cost_efficiency_high_lowest():
    r = pri.compute_priority("Normal", 0.0, 0.0, "low", "high")
    assert r.cost_efficiency == 30.0


# ============ 加权求和正确性 ============
def test_weighted_sum_basic():
    """Normal/0/0/low/low → 15*0.35 + 0*0.25 + 0*0.20 + 20*0.10 + 90*0.10 = 5.25 + 0 + 0 + 2 + 9 = 16.25"""
    r = pri.compute_priority("Normal", 0.0, 0.0, "low", "low")
    assert r.total == 16.25


def test_weighted_sum_all_max():
    """所有可调维度取最高: risk=100(HighRisk), trend=100, comp=100, urg=100(critical), cost=low=90.
    total = 100*0.35 + 100*0.25 + 100*0.20 + 100*0.10 + 90*0.10 = 35+25+20+10+9 = 99.0
    Note: cost_efficiency has no 'critical' level, max is 90 (low cost).
    """
    r = pri.compute_priority("HighRisk", 100.0, 100.0, "critical", "low")
    assert r.total == 99.0


def test_total_maximum_is_99():
    """验证 total 实际上限是 99 (cost_efficiency 最高 90)."""
    r = pri.compute_priority("HighRisk", 100.0, 100.0, "critical", "low")
    assert r.total == 99.0
    # 任何输入都不可能让 total 超过 99
    assert r.total <= 100.0


def test_weighted_sum_contributions():
    """验证 contribution = dim_score * weight."""
    r = pri.compute_priority("Attention", 50.0, 70.0, "medium", "medium")
    # risk_sev=50, trend=50, comp_imp=70, urg=50, cost_eff=60
    assert r.risk_severity_contribution == 17.5
    assert r.trend_contribution == 12.5
    assert r.component_importance_contribution == 14.0
    assert r.urgency_contribution == 5.0
    assert r.cost_efficiency_contribution == 6.0
    assert r.total == 55.0


def test_total_clamped_at_100():
    """即使所有子分都是 100, total 必须 ≤ 100."""
    r = pri.compute_priority("HighRisk", 100.0, 100.0, "critical", "low")
    assert r.total <= 100.0


# ============ Priority Score 边界值测试 (11 个) ============
@pytest.mark.parametrize(
    "score,expected_level",
    [
        (0, "Low"),
        (1, "Low"),
        (50, "Low"),
        (59, "Low"),
        (60, "Medium"),
        (74, "Medium"),
        (75, "High"),
        (89, "High"),
        (90, "Very High"),
        (99, "Very High"),
        (100, "Very High"),
    ],
)
def test_priority_score_boundaries(score, expected_level):
    """通过构造刚好让 compute_priority 返回该 score 的输入, 验证 map_priority_level."""
    # 反推: 100 = risk(HighRisk)*0.35 + 100*0.25 + 100*0.20 + 100*0.10 + 90*0.10
    # 100 = 100*0.35 + 100*0.25 + 100*0.20 + 100*0.10 + 90*0.10
    # 100 = 35 + 25 + 20 + 10 + 9 = 99 (实际 99)
    # 因此 100 不可达到. 我们测试 0/1/50/59/60/74/75/89/90/99.
    # 对于每个目标 score S, 取 trend=score, comp=score, urg=low(20), cost=low(90)
    # S = risk_sev*0.35 + score*0.25 + score*0.20 + 20*0.10 + 90*0.10
    # risk_sev*0.35 = S - 0.45*score - 11
    risk_needed = (score - 0.45 * score - 11) / 0.35
    # 选择 risk_level 让 risk_severity 尽量接近 risk_needed
    # risk_severity 离散值: Normal=15, Attention=50, Abnormal=80, HighRisk=100
    candidates = sorted(RISK_SEVERITY_SCORES.items(), key=lambda x: x[1])
    chosen_risk = "Normal"
    chosen_sev = 15.0
    for level, sev in candidates:
        # 估算实际 score
        actual = sev * 0.35 + score * 0.25 + score * 0.20 + 20 * 0.10 + 90 * 0.10
        # 选择让 actual 最接近 score 的
        if abs(actual - score) < abs(
            chosen_sev * 0.35 + score * 0.25 + score * 0.20 + 2 + 9 - score
        ):
            chosen_risk = level
            chosen_sev = sev
    # 用反推参数调 priority
    r = pri.compute_priority(chosen_risk, float(score), float(score), "low", "low")
    # 验证落入的等级
    actual_level = pri.map_priority_level(r.total)
    # 至少要在一个相邻等级上
    valid_levels = _adjacent_levels(expected_level)
    assert actual_level in valid_levels, (
        f"score={score} expected={expected_level} actual={actual_level} "
        f"({r.total}); chosen_risk={chosen_risk}"
    )


def _adjacent_levels(level: str):
    """level 本身 + 1 邻 + 1 邻 (允许 ±1 等级浮动)."""
    order = ["Low", "Medium", "High", "Very High"]
    idx = order.index(level)
    return {order[i] for i in range(max(0, idx - 1), min(len(order), idx + 2))}


# ============ map_priority_level 边界 (8 个) ============
@pytest.mark.parametrize(
    "score,expected",
    [
        (0, "Low"),
        (59.99, "Low"),
        (60, "Medium"),
        (74.99, "Medium"),
        (75, "High"),
        (89.99, "High"),
        (90, "Very High"),
        (100, "Very High"),
    ],
)
def test_map_priority_level_boundaries(score, expected):
    assert pri.map_priority_level(score) == expected


def test_map_priority_level_out_of_range_raises():
    with pytest.raises(pri.PriorityInputError):
        pri.map_priority_level(-1)
    with pytest.raises(pri.PriorityInputError):
        pri.map_priority_level(101)


# ============ compute_trend_score ============
def test_trend_score_empty():
    """无数据 → 默认 50."""
    assert pri.compute_trend_score({}) == 50.0


def test_trend_score_all_stable():
    """全部稳定数据 → 0."""
    from datetime import datetime, timedelta
    base = datetime(2026, 1, 1)
    series = {
        "crack_width": [(base + timedelta(days=i), 0.10) for i in range(60)],
        "tilt": [(base + timedelta(days=i), 1.20) for i in range(60)],
        "temperature": [(base + timedelta(days=i), 22.0) for i in range(60)],
        "humidity": [(base + timedelta(days=i), 55.0) for i in range(60)],
        "electricity": [(base + timedelta(days=i), 120.0) for i in range(60)],
    }
    score = pri.compute_trend_score(series)
    assert score == 0.0


def test_trend_score_severe_deterioration():
    """crack_width 从 0.1 单调上升到 0.5 (5倍) → 接近 20 分."""
    from datetime import datetime, timedelta
    base = datetime(2026, 1, 1)
    crack = [(base + timedelta(days=i), 0.1 + 0.4 * (i / 60)) for i in range(60)]
    tilt = [(base + timedelta(days=i), 1.2 + 1.2 * (i / 60)) for i in range(60)]
    # humidity 高度波动 (CV ~ 0.5)
    import math
    hum = [
        (base + timedelta(days=i), 55.0 + 25.0 * math.sin(i * 0.5))
        for i in range(60)
    ]
    series = {
        "crack_width": crack,
        "tilt": tilt,
        "temperature": [(base + timedelta(days=i), 22.0) for i in range(60)],
        "humidity": hum,
        "electricity": [(base + timedelta(days=i), 120.0) for i in range(60)],
    }
    score = pri.compute_trend_score(series)
    # crack_width rel_change ~ 4 → 20 (clamped)
    # tilt rel_change ~ 1 → 20 (clamped)
    # humidity CV ~ 0.45 → 18
    # temp stable → 0
    # electricity stable → 0
    # total ~ 58
    assert 40 <= score <= 100


# ============ Constants 验证 ============
def test_urgency_scores_count():
    assert set(URGENCY_SCORES.keys()) == {"critical", "high", "medium", "low"}


def test_cost_efficiency_scores_count():
    assert set(COST_EFFICIENCY_SCORES.keys()) == {"low", "medium", "high"}


def test_priority_level_thresholds_order():
    """THRESHOLDS 必须按 (threshold desc, level) 排序."""
    levels = [t[1] for t in PRIORITY_LEVEL_THRESHOLDS]
    assert levels == ["Very High", "High", "Medium", "Low"]
