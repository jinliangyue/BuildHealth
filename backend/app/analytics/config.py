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


# =================================================================
# Retrofit Priority (RP-v1.0) · Phase 4 V2
# =================================================================
# 5 维度子分加权得到 0-100 的 priority score
RETROFIT_PRIORITY_WEIGHTS: Dict[str, float] = {
    "risk_severity": 0.35,
    "trend": 0.25,
    "component_importance": 0.20,
    "urgency": 0.10,
    "cost_efficiency": 0.10,
}

RETROFIT_PRIORITY_VERSION = "RP-v1.0"
RECOMMENDATION_RULES_VERSION = "REC-v1.0"

# 4 档 urgency → 子分 (0-100, 越高越紧急)
URGENCY_SCORES: Dict[str, float] = {
    "critical": 100.0,
    "high": 80.0,
    "medium": 50.0,
    "low": 20.0,
}

# 3 档 cost level → cost efficiency (低成本=高效率分)
COST_EFFICIENCY_SCORES: Dict[str, float] = {
    "low": 90.0,
    "medium": 60.0,
    "high": 30.0,
}

# 6 类 component_type → 重要性 (0-100)
COMPONENT_IMPORTANCE: Dict[str, float] = {
    "foundation": 100.0,
    "column": 100.0,
    "beam": 80.0,
    "wall": 80.0,
    "slab": 60.0,
    "roof": 60.0,
}
DEFAULT_COMPONENT_IMPORTANCE = 70.0

# 4 档 risk_level → severity 子分 (高 risk = 高 severity, retrofit 越紧急)
RISK_SEVERITY_SCORES: Dict[str, float] = {
    "Normal": 15.0,
    "Attention": 50.0,
    "Abnormal": 80.0,
    "HighRisk": 100.0,
}

# Priority score → Priority Level 边界
# 0-59 Low / 60-74 Medium / 75-89 High / 90-100 Very High
PRIORITY_LEVEL_THRESHOLDS: List[tuple] = [
    (90.0, "Very High"),
    (75.0, "High"),
    (60.0, "Medium"),
    (0.0, "Low"),
]

# Trend score 默认值 (当无监测数据时)
DEFAULT_TREND_SCORE = 50.0


# =================================================================
# Recommendation Rules Trigger Thresholds
# =================================================================
# crack_width / tilt: 触发时对应的 z-score 阈值
RULE_ZSCORE_TRIGGER = 2.0
# env / energy 评分阈值（< 该值时对应 rule 触发）
RULE_ENV_SCORE_THRESHOLD = 80.0
RULE_ENERGY_SCORE_THRESHOLD = 80.0
# 监测数据最近窗口天数（用于 trend & anomaly 统计）
RULE_RECENT_WINDOW_DAYS = 30
# evidence 中保留的 recent_values 数量
RULE_RECENT_VALUES_LIMIT = 10


# =================================================================
# Disclaimer
# =================================================================
RETROFIT_DISCLAIMER = (
    "Retrofit priority is computed using Prototype Retrofit Priority Parameters "
    "(RP-v1.0). This output is engineering decision support only and does not "
    "constitute an automated structural reinforcement plan. "
    "All recommendations require qualified professional review."
)
