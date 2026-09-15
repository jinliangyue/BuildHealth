"""
Analytics Engine · Prototype Detection Parameters
所有阈值与算法参数统一在此配置，方便版本化与文档引用。

【强约束】这些是 Prototype Detection Parameters，
不是国家标准/行业标准/真实建筑安全规范。
任何对阈值的修改必须更新 docs/05_Analytics_Design.md。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ===== Threshold Detection（绝对阈值）=====
@dataclass(frozen=True)
class ThresholdRule:
    metric: str
    high: Optional[float] = None
    medium: Optional[float] = None
    low: Optional[float] = None
    unit: str = ""
    direction: str = "above"  # above / below / both


# 当 metric 超过 high 阈值 → HIGH severity
# 当 metric 超过 medium 阈值 → MEDIUM severity
# 当 metric 超过 low 阈值 → LOW severity
THRESHOLD_RULES: Dict[str, ThresholdRule] = {
    "crack_width": ThresholdRule(
        metric="crack_width", high=0.30, medium=0.20, low=None, unit="mm"
    ),
    "tilt": ThresholdRule(
        metric="tilt", high=4.0, medium=3.0, low=None, unit="‰"
    ),
    "temperature": ThresholdRule(
        metric="temperature", high=None, medium=40.0, low=None, unit="℃"
    ),
    "humidity": ThresholdRule(
        metric="humidity", high=None, medium=85.0, low=None, unit="%"
    ),
    "electricity": ThresholdRule(
        metric="electricity", high=None, medium=None, low=None, unit="kWh"
    ),
}


# ===== Rate of Change Detection（变化率）=====
@dataclass(frozen=True)
class RateOfChangeConfig:
    metric: str
    absolute_change_threshold: float  # 绝对变化量阈值（单位同 metric）
    relative_change_pct: float  # 相对变化百分比阈值（如 50.0 表示 50%）


RATE_OF_CHANGE_RULES: Dict[str, RateOfChangeConfig] = {
    "crack_width": RateOfChangeConfig("crack_width", 0.05, 30.0),
    "tilt": RateOfChangeConfig("tilt", 0.5, 25.0),
    "temperature": RateOfChangeConfig("temperature", 8.0, 40.0),
    "humidity": RateOfChangeConfig("humidity", 15.0, 30.0),
    "electricity": RateOfChangeConfig("electricity", 20.0, 80.0),
}


# ===== Statistical Detection（Z-score / Moving Average）=====
ZSCORE_WINDOW_HOURS = 24 * 7  # 7 天滚动窗口
ZSCORE_MIN_SAMPLES = 24  # 最少样本数（<24 不计算 Z-score）
ZSCORE_THRESHOLD = 4.0  # |z| > 4.0 视为异常（仅约 0.006% 概率触发）
ZSCORE_SEVERITY_HIGH = 6.0  # |z| > 6 视为 HIGH

# 不做 Z-score 的指标（噪声大或无意义）
ZSCORE_DISABLED_METRICS = frozenset(["electricity", "humidity"])


# ===== Severity 判定默认规则 =====
# 当一种方法无法直接给出 severity 时，用 metric 默认映射
DEFAULT_SEVERITY_BY_METRIC: Dict[str, str] = {
    "crack_width": "high",
    "tilt": "high",
    "temperature": "medium",
    "humidity": "low",
    "electricity": "low",
}


# ===== Anomaly 去重窗口 =====
# 同一 sensor + metric + method 在 X 小时内只保留第一条
ANOMALY_DEDUP_HOURS = 6


# ===== Health Assessment 维度权重 =====
BHI_WEIGHTS: Dict[str, float] = {
    "structural_safety": 0.40,
    "facility_condition": 0.20,
    "environmental_quality": 0.15,
    "energy_performance": 0.10,
    "fire_safety": 0.15,
}

BHI_CALCULATION_VERSION = "BHI-v1.0"
