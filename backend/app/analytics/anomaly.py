"""
Anomaly Detection Engine
实现 3 种方法（按优先级降序）：
1. Threshold Detection
2. Rate of Change Detection
3. Statistical Detection (Z-score)

所有结果统一封装为 Anomaly dataclass，含 10 个字段：
- sensor_id, metric, timestamp, current_value, baseline_value,
- change, detection_method, severity, explanation, building_id

所有解释基于真实计算，不允许硬编码文字模板替换真实值。
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import statistics

from app.analytics.config import (
    THRESHOLD_RULES,
    RATE_OF_CHANGE_RULES,
    ZSCORE_WINDOW_HOURS,
    ZSCORE_MIN_SAMPLES,
    ZSCORE_THRESHOLD,
    ZSCORE_SEVERITY_HIGH,
    ZSCORE_DISABLED_METRICS,
    DEFAULT_SEVERITY_BY_METRIC,
)


@dataclass
class Anomaly:
    sensor_id: int
    building_id: int
    metric: str
    timestamp: datetime
    current_value: float
    baseline_value: Optional[float]
    change: Optional[float]
    detection_method: str  # threshold / rate_of_change / zscore
    severity: str  # low / medium / high
    explanation: str

    def to_dict(self) -> dict:
        d = asdict(self)
        # datetime → isoformat 字符串
        d["timestamp"] = self.timestamp.isoformat()
        return d


# =================================================================
# 1. Threshold Detection
# =================================================================
def detect_threshold(
    sensor_id: int,
    building_id: int,
    metric: str,
    timestamp: datetime,
    value: float,
) -> List[Anomaly]:
    """
    绝对阈值检测。返回 0 或 1 条 Anomaly。
    阈值超出判定：
      value > high  → HIGH
      value > medium → MEDIUM
      value > low    → LOW
    """
    rule = THRESHOLD_RULES.get(metric)
    if rule is None:
        return []

    anomalies: List[Anomaly] = []

    severity = None
    threshold_value = None
    if rule.high is not None and value > rule.high:
        severity = "high"
        threshold_value = rule.high
    elif rule.medium is not None and value > rule.medium:
        severity = "medium"
        threshold_value = rule.medium
    elif rule.low is not None and value > rule.low:
        severity = "low"
        threshold_value = rule.low

    if severity is None:
        return []

    explanation = (
        f"{metric} reading {value:.3f}{rule.unit} exceeded prototype threshold "
        f"{threshold_value:.3f}{rule.unit} (severity: {severity}); "
        f"prototype assessment suggests further professional inspection is recommended."
    )

    anomalies.append(
        Anomaly(
            sensor_id=sensor_id,
            building_id=building_id,
            metric=metric,
            timestamp=timestamp,
            current_value=value,
            baseline_value=threshold_value,
            change=round(value - threshold_value, 4),
            detection_method="threshold",
            severity=severity,
            explanation=explanation,
        )
    )
    return anomalies


# =================================================================
# 2. Rate of Change Detection
# =================================================================
def detect_rate_of_change(
    sensor_id: int,
    building_id: int,
    metric: str,
    timestamp: datetime,
    current_value: float,
    previous_value: Optional[float],
) -> List[Anomaly]:
    """
    相邻时刻变化率检测。返回 0 或 1 条 Anomaly。
    触发条件（同时满足）：
      |delta| >= absolute_change_threshold
      |delta_pct| >= relative_change_pct
    """
    if previous_value is None:
        return []

    rule = RATE_OF_CHANGE_RULES.get(metric)
    if rule is None:
        return []

    delta = current_value - previous_value
    abs_delta = abs(delta)

    if previous_value == 0:
        # baseline 为 0 时仅判断绝对变化量
        rel_pct = float("inf") if abs_delta > 0 else 0.0
    else:
        rel_pct = abs_delta / abs(previous_value) * 100.0

    if abs_delta < rule.absolute_change_threshold:
        return []
    if rel_pct < rule.relative_change_pct:
        return []

    # 严重程度：相对变化率越大越严重
    if rel_pct >= rule.relative_change_pct * 2.5:
        severity = "high"
    elif rel_pct >= rule.relative_change_pct * 1.5:
        severity = "medium"
    else:
        severity = "low"

    direction_word = "increased" if delta > 0 else "decreased"

    explanation = (
        f"{metric} {direction_word} rapidly from baseline {previous_value:.3f} "
        f"to {current_value:.3f} (delta={delta:+.3f}, |delta_pct|={rel_pct:.1f}%); "
        f"monitoring trend indicates significant short-term change, "
        f"prototype assessment suggests further professional inspection is recommended."
    )

    return [
        Anomaly(
            sensor_id=sensor_id,
            building_id=building_id,
            metric=metric,
            timestamp=timestamp,
            current_value=current_value,
            baseline_value=previous_value,
            change=round(delta, 4),
            detection_method="rate_of_change",
            severity=severity,
            explanation=explanation,
        )
    ]


# =================================================================
# 3. Statistical Detection (Z-score)
# =================================================================
def detect_zscore(
    sensor_id: int,
    building_id: int,
    metric: str,
    timestamp: datetime,
    current_value: float,
    history_values: List[float],
) -> List[Anomaly]:
    """
    统计异常检测（Z-score）。
    在给定的历史窗口内（默认 7 天）计算均值与标准差，
    当前值的 |z-score| > ZSCORE_THRESHOLD 则触发。

    history_values 应包含除当前点外的历史值（不含 current_value）。
    """
    if len(history_values) < ZSCORE_MIN_SAMPLES:
        return []
    if metric in ZSCORE_DISABLED_METRICS:
        return []

    try:
        mean = statistics.fmean(history_values)
        stdev = statistics.stdev(history_values)
    except statistics.StatisticsError:
        return []

    if stdev == 0:
        # 历史完全无波动时不做统计判定（避免除零）
        return []

    z = (current_value - mean) / stdev

    if abs(z) < ZSCORE_THRESHOLD:
        return []

    if abs(z) >= ZSCORE_SEVERITY_HIGH:
        severity = "high"
    else:
        severity = DEFAULT_SEVERITY_BY_METRIC.get(metric, "medium")

    explanation = (
        f"{metric} reading {current_value:.3f} deviates from historical baseline "
        f"mean {mean:.3f} (stdev={stdev:.3f}, z-score={z:+.2f}); "
        f"monitoring trend indicates statistical anomaly beyond prototype threshold "
        f"(|z|>{ZSCORE_THRESHOLD}); prototype assessment suggests further professional "
        f"inspection is recommended."
    )

    return [
        Anomaly(
            sensor_id=sensor_id,
            building_id=building_id,
            metric=metric,
            timestamp=timestamp,
            current_value=current_value,
            baseline_value=round(mean, 4),
            change=round(current_value - mean, 4),
            detection_method="zscore",
            severity=severity,
            explanation=explanation,
        )
    ]


# =================================================================
# 4. 综合入口：对单条监测记录跑全部 3 种方法
# =================================================================
def detect_for_record(
    sensor_id: int,
    building_id: int,
    metric: str,
    timestamp: datetime,
    value: float,
    previous_value: Optional[float] = None,
    history_values: Optional[List[float]] = None,
) -> List[Anomaly]:
    """对一条监测记录运行 3 种检测，返回合并去重后的结果。"""
    anomalies: List[Anomaly] = []
    anomalies.extend(
        detect_threshold(sensor_id, building_id, metric, timestamp, value)
    )
    anomalies.extend(
        detect_rate_of_change(
            sensor_id, building_id, metric, timestamp, value, previous_value
        )
    )
    if history_values is not None:
        anomalies.extend(
            detect_zscore(
                sensor_id, building_id, metric, timestamp, value, history_values
            )
        )
    return anomalies
