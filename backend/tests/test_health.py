"""
BHI 计算测试 · 正常 / 边界 / 越界 / 权重 / 版本化
"""
import pytest

from app.analytics.health import (
    compute_bhi,
    HealthInputError,
    score_structural_from_anomalies,
    score_facility_from_age,
    score_environment_from_series,
    score_energy_from_series,
    score_fire_placeholder,
)
from app.analytics.config import BHI_CALCULATION_VERSION


def test_bhi_full_score():
    """全 100 → BHI=100"""
    r = compute_bhi(100, 100, 100, 100, 100)
    assert r.score == 100.0
    assert r.calculation_version == BHI_CALCULATION_VERSION


def test_bhi_zero_score():
    """全 0 → BHI=0"""
    r = compute_bhi(0, 0, 0, 0, 0)
    assert r.score == 0.0


def test_bhi_weighted_calculation():
    """验证权重应用：全 100 → 100；只 structural=100 → 40"""
    r1 = compute_bhi(100, 100, 100, 100, 100)
    assert r1.score == 100.0
    r2 = compute_bhi(100, 0, 0, 0, 0)
    assert r2.score == 40.0  # 0.40 × 100
    r3 = compute_bhi(0, 100, 0, 0, 0)
    assert r3.score == 20.0  # 0.20 × 100
    r4 = compute_bhi(0, 0, 100, 0, 0)
    assert r4.score == 15.0  # 0.15 × 100
    r5 = compute_bhi(0, 0, 0, 100, 0)
    assert r5.score == 10.0  # 0.10 × 100
    r6 = compute_bhi(0, 0, 0, 0, 100)
    assert r6.score == 15.0  # 0.15 × 100


def test_bhi_mixed():
    """混合维度"""
    r = compute_bhi(80, 70, 60, 90, 50)
    expected = 80 * 0.40 + 70 * 0.20 + 60 * 0.15 + 90 * 0.10 + 50 * 0.15
    assert r.score == round(expected, 2)


def test_bhi_out_of_range_raises():
    with pytest.raises(HealthInputError):
        compute_bhi(101, 50, 50, 50, 50)
    with pytest.raises(HealthInputError):
        compute_bhi(-1, 50, 50, 50, 50)
    with pytest.raises(HealthInputError):
        compute_bhi(50, 50, 50, 50, 150)


def test_bhi_version_present():
    r = compute_bhi(80, 80, 80, 80, 80)
    assert r.calculation_version.startswith("BHI-")


def test_bhi_explanation_contains_prototype_disclaimer():
    r = compute_bhi(80, 80, 80, 80, 80)
    assert "prototype" in r.explanation.lower()
    assert "professional inspection" in r.explanation.lower()


def test_structural_log_decay():
    """异常越多边际扣分越小"""
    s1 = score_structural_from_anomalies(1, 0, 0)
    s10 = score_structural_from_anomalies(10, 0, 0)
    s100 = score_structural_from_anomalies(100, 0, 0)
    assert s1 > s10 > s100


def test_facility_age_within_design_life():
    assert score_facility_from_age(0, 50) == 95.0
    # ratio=0.5 → 95 - 20*0.5 = 85
    assert score_facility_from_age(25, 50) == 85.0
    # ratio=1.0 → 95 - 20*1.0 = 75
    assert score_facility_from_age(50, 50) == 75.0


def test_facility_age_beyond_design_life():
    s = score_facility_from_age(60, 50)  # 超过设计年限 20%
    assert 30.0 <= s <= 75.0


def test_environment_stable_series_high_score():
    temps = [22.0] * 50
    hums = [55.0] * 50
    s = score_environment_from_series(temps, hums)
    assert s == 100.0


def test_environment_volatile_series_low_score():
    temps = [10.0, 35.0] * 25  # 极端波动
    hums = [10.0, 90.0] * 25
    s = score_environment_from_series(temps, hums)
    assert s < 70.0


def test_energy_stable_series_high_score():
    s = score_energy_from_series([100.0] * 100)
    assert s == 100.0


def test_energy_empty_series_default():
    s = score_energy_from_series([])
    assert s == 80.0


def test_fire_placeholder_low_floors_young():
    s = score_fire_placeholder(5, 5)
    assert s >= 85.0


def test_fire_placeholder_high_floors_old():
    s = score_fire_placeholder(30, 40)
    assert s <= 80.0
