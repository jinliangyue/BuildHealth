"""
Risk Classification 边界测试 · 8 个关键 BHI 值
"""
import pytest

from app.analytics.risk import classify_risk, RiskClassification


@pytest.mark.parametrize(
    "bhi,expected_level",
    [
        (100, "Normal"),
        (90, "Normal"),
        (89.99, "Attention"),
        (89, "Attention"),
        (75, "Attention"),
        (74.99, "Abnormal"),
        (74, "Abnormal"),
        (60, "Abnormal"),
        (59.99, "HighRisk"),
        (59, "HighRisk"),
        (0, "HighRisk"),
    ],
)
def test_risk_boundaries(bhi, expected_level):
    cls = classify_risk(bhi=bhi, building_id=1)
    assert cls.risk_level == expected_level
    assert cls.bhi == round(bhi, 2)
    assert "Prototype Risk Classification" in cls.explanation


def test_risk_high_anomaly_override():
    """即使 BHI=Normal (95)，存在 HIGH 异常时应升级到 Attention"""
    cls = classify_risk(bhi=95.0, building_id=1, n_high=1, n_medium=0, n_low=0)
    assert cls.risk_level == "Attention"


def test_risk_out_of_range_raises():
    with pytest.raises(ValueError):
        classify_risk(bhi=101)
    with pytest.raises(ValueError):
        classify_risk(bhi=-1)


def test_risk_dataclass_fields():
    cls = classify_risk(bhi=85, building_id=42, n_high=0, n_medium=2, n_low=5)
    assert cls.building_id == 42
    assert cls.n_medium_anomalies == 2
    assert cls.n_low_anomalies == 5
    d = cls.to_dict()
    assert isinstance(d, dict)
    assert "risk_level" in d
