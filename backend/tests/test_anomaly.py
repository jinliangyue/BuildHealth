"""
Anomaly Detection 测试 · 3 种方法
"""
import pytest
from datetime import datetime

from app.analytics.anomaly import (
    detect_threshold,
    detect_rate_of_change,
    detect_zscore,
    detect_for_record,
)


# ============ Threshold Detection ============
def test_threshold_no_rule_returns_empty():
    """未知 metric 不触发"""
    r = detect_threshold(1, 1, "unknown_metric", datetime.utcnow(), 999.0)
    assert r == []


def test_threshold_below_returns_empty():
    r = detect_threshold(1, 1, "crack_width", datetime.utcnow(), 0.05)
    assert r == []


def test_threshold_medium():
    """crack_width 0.25 > 0.20 medium 阈值"""
    r = detect_threshold(1, 1, "crack_width", datetime.utcnow(), 0.25)
    assert len(r) == 1
    assert r[0].severity == "medium"
    assert r[0].detection_method == "threshold"
    assert "exceeded prototype threshold" in r[0].explanation


def test_threshold_high():
    """crack_width 0.40 > 0.30 high 阈值"""
    r = detect_threshold(1, 1, "crack_width", datetime.utcnow(), 0.40)
    assert len(r) == 1
    assert r[0].severity == "high"


# ============ Rate of Change ============
def test_rate_no_previous_returns_empty():
    r = detect_rate_of_change(1, 1, "crack_width", datetime.utcnow(), 0.5, None)
    assert r == []


def test_rate_small_change_returns_empty():
    """0.10 → 0.11 不应触发（abs<0.05, pct<30%）"""
    r = detect_rate_of_change(1, 1, "crack_width", datetime.utcnow(), 0.11, 0.10)
    assert r == []


def test_rate_large_change_triggers():
    """0.10 → 0.50 应触发"""
    r = detect_rate_of_change(1, 1, "crack_width", datetime.utcnow(), 0.50, 0.10)
    assert len(r) == 1
    assert r[0].detection_method == "rate_of_change"
    assert "rapidly" in r[0].explanation


def test_rate_decrease_also_triggers():
    """下降也应触发"""
    r = detect_rate_of_change(1, 1, "tilt", datetime.utcnow(), 0.1, 1.0)
    assert len(r) == 1
    assert "decreased" in r[0].explanation


# ============ Z-score ============
def test_zscore_insufficient_samples_returns_empty():
    r = detect_zscore(1, 1, "crack_width", datetime.utcnow(), 0.5, [0.1] * 10)
    assert r == []


def test_zscore_zero_stdev_returns_empty():
    r = detect_zscore(1, 1, "crack_width", datetime.utcnow(), 5.0, [0.1] * 100)
    assert r == []


def test_zscore_normal_value_no_trigger():
    history = [0.1 + 0.001 * i for i in range(100)]
    r = detect_zscore(1, 1, "crack_width", datetime.utcnow(), 0.11, history)
    assert r == []


def test_zscore_extreme_value_triggers():
    """history 均值 0.1，stdev~0.029，|z|=10 必触发"""
    history = [0.1 + 0.001 * i for i in range(100)]
    r = detect_zscore(1, 1, "crack_width", datetime.utcnow(), 5.0, history)
    assert len(r) == 1
    assert r[0].detection_method == "zscore"
    assert r[0].severity == "high"  # |z|>>6 → high


# ============ Combined ============
def test_combined_multiple_methods():
    """明显异常应该被多种方法检测"""
    history = [0.1 + 0.001 * i for i in range(100)]
    r = detect_for_record(
        sensor_id=1,
        building_id=1,
        metric="crack_width",
        timestamp=datetime.utcnow(),
        value=5.0,  # 既超阈值，又偏离历史
        previous_value=0.10,
        history_values=history,
    )
    methods = {a.detection_method for a in r}
    assert "threshold" in methods
    assert "zscore" in methods


def test_anomaly_explanation_real():
    """explanation 必须基于真实数值"""
    r = detect_threshold(1, 1, "crack_width", datetime.utcnow(), 0.45)
    assert r[0].current_value == 0.45
    assert "0.450" in r[0].explanation
