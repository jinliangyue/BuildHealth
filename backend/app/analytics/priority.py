"""
Retrofit Priority Engine · Phase 4 V2
=====================================

5 维度子分加权得到 0-100 的 priority score:
    risk_severity       × 0.35
  + trend               × 0.25
  + component_importance × 0.20
  + urgency             × 0.10
  + cost_efficiency     × 0.10
  ─────────────────────────────
  = total (clamped 0-100, round 2)

每个 contribution 也写入 breakdown 用于前端可视化。

【强约束】这些是 Prototype Design Parameters，
不是国家标准 / 行业标准 / 真实改造优先级评估方法。
任何对权重或子分公式的修改必须更新 docs/11_Retrofit_Priority_Model.md。
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
import statistics

from app.analytics.config import (
    RETROFIT_PRIORITY_WEIGHTS,
    RETROFIT_PRIORITY_VERSION,
    URGENCY_SCORES,
    COST_EFFICIENCY_SCORES,
    RISK_SEVERITY_SCORES,
    PRIORITY_LEVEL_THRESHOLDS,
    DEFAULT_TREND_SCORE,
    RULE_RECENT_WINDOW_DAYS,
)


class PriorityInputError(ValueError):
    """优先级输入非法"""


@dataclass
class PriorityScoreBreakdown:
    risk_severity: float
    risk_severity_contribution: float
    trend: float
    trend_contribution: float
    component_importance: float
    component_importance_contribution: float
    urgency: float
    urgency_contribution: float
    cost_efficiency: float
    cost_efficiency_contribution: float
    total: float
    calculation_version: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, round(x, 2)))


def _validate_score(name: str, value: float) -> float:
    if not (0.0 <= value <= 100.0):
        raise PriorityInputError(
            f"Priority score '{name}' must be in [0, 100], got {value}"
        )
    return float(value)


def _validate_enum(name: str, value: str, allowed: Dict[str, float]) -> str:
    if value not in allowed:
        raise PriorityInputError(
            f"Priority {name} '{value}' not in allowed set {list(allowed.keys())}"
        )
    return value


def map_priority_level(total: float) -> str:
    """0-59 Low / 60-74 Medium / 75-89 High / 90-100 Very High"""
    if total < 0 or total > 100:
        raise PriorityInputError(
            f"Priority total {total} must be in [0, 100]"
        )
    for threshold, level in PRIORITY_LEVEL_THRESHOLDS:
        if total >= threshold:
            return level
    return "Low"


def compute_priority(
    risk_level: str,
    trend_score: float,
    component_importance: float,
    urgency: str,
    cost_level: str,
) -> PriorityScoreBreakdown:
    """加权求和得到 priority score + breakdown.

    Args:
        risk_level: Normal / Attention / Abnormal / HighRisk
        trend_score: 0-100, 越高越严重
        component_importance: 0-100
        urgency: critical / high / medium / low
        cost_level: low / medium / high
    """
    # 1. input validation
    _validate_enum("risk_level", risk_level, RISK_SEVERITY_SCORES)
    trend_score = _validate_score("trend_score", trend_score)
    component_importance = _validate_score("component_importance", component_importance)
    _validate_enum("urgency", urgency, URGENCY_SCORES)
    _validate_enum("cost_level", cost_level, COST_EFFICIENCY_SCORES)

    # 2. 防御性权重和检查
    total_weight = sum(RETROFIT_PRIORITY_WEIGHTS.values())
    if abs(total_weight - 1.0) > 1e-6:
        raise PriorityInputError(
            f"RETROFIT_PRIORITY_WEIGHTS sum to {total_weight}, must equal 1.0"
        )

    # 3. 查表得到各子分
    risk_sev = RISK_SEVERITY_SCORES[risk_level]
    urg = URGENCY_SCORES[urgency]
    cost_eff = COST_EFFICIENCY_SCORES[cost_level]

    # 4. 加权 contribution
    rs_c = round(risk_sev * RETROFIT_PRIORITY_WEIGHTS["risk_severity"], 2)
    tr_c = round(trend_score * RETROFIT_PRIORITY_WEIGHTS["trend"], 2)
    ci_c = round(component_importance * RETROFIT_PRIORITY_WEIGHTS["component_importance"], 2)
    ur_c = round(urg * RETROFIT_PRIORITY_WEIGHTS["urgency"], 2)
    ce_c = round(cost_eff * RETROFIT_PRIORITY_WEIGHTS["cost_efficiency"], 2)

    total = _clamp(rs_c + tr_c + ci_c + ur_c + ce_c)

    return PriorityScoreBreakdown(
        risk_severity=_clamp(risk_sev),
        risk_severity_contribution=rs_c,
        trend=_clamp(trend_score),
        trend_contribution=tr_c,
        component_importance=_clamp(component_importance),
        component_importance_contribution=ci_c,
        urgency=_clamp(urg),
        urgency_contribution=ur_c,
        cost_efficiency=_clamp(cost_eff),
        cost_efficiency_contribution=ce_c,
        total=total,
        calculation_version=RETROFIT_PRIORITY_VERSION,
    )


# =================================================================
# Trend Score 计算（5 metric 综合）
# =================================================================
def _trend_for_crack_or_tilt(
    series: List[Tuple[datetime, float]],
    recent_window_days: int,
) -> float:
    """crack_width / tilt: 比较最近 N 天均值 vs 前 N 天均值,
    上升趋势越明显 → 越高分 (0-20)."""
    if not series or len(series) < 4:
        return 0.0
    if len(series) < recent_window_days * 2:
        # 数据不足, 用整段中点分割
        half = len(series) // 2
        recent = series[half:]
        previous = series[:half]
    else:
        recent = series[-recent_window_days:]
        previous = series[-recent_window_days * 2 : -recent_window_days]
    if not previous or not recent:
        return 0.0
    prev_mean = statistics.fmean([v for _, v in previous])
    rec_mean = statistics.fmean([v for _, v in recent])
    if prev_mean == 0:
        if rec_mean == 0:
            return 0.0
        # 从 0 开始 → 视为显著上升
        return 20.0
    rel_change = (rec_mean - prev_mean) / abs(prev_mean)
    if rel_change <= 0:
        return 0.0
    # rel_change > 0 → 加分, 0.5 (50%) 对应 20 分
    return min(20.0, rel_change * 40.0)


def _trend_for_volatility_metric(
    series: List[Tuple[datetime, float]],
) -> float:
    """temperature / humidity / electricity: CV 越高越差 (0-20)."""
    if not series or len(series) < 5:
        return 0.0
    vals = [v for _, v in series]
    try:
        mean = statistics.fmean(vals)
        stdev = statistics.stdev(vals)
    except statistics.StatisticsError:
        return 0.0
    if mean == 0:
        return 0.0
    cv = abs(stdev / mean)
    # cv=0 → 0, cv=0.5 → 20
    return min(20.0, cv * 40.0)


def compute_trend_score(
    sensor_series_by_metric: Dict[str, List[Tuple[datetime, float]]],
    recent_window_days: int = RULE_RECENT_WINDOW_DAYS,
) -> float:
    """综合 5 个 metric 的趋势恶化程度 → 0-100.

    Returns:
        0 表示无任何恶化迹象, 100 表示全面恶化. 默认 50 (无数据).
    """
    if not sensor_series_by_metric:
        return DEFAULT_TREND_SCORE

    total = 0.0
    for metric, series in sensor_series_by_metric.items():
        if metric in ("crack_width", "tilt"):
            total += _trend_for_crack_or_tilt(series, recent_window_days)
        elif metric in ("temperature", "humidity", "electricity"):
            total += _trend_for_volatility_metric(series)
    return _clamp(total)
