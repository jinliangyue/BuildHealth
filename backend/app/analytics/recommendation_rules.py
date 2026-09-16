"""
Retrofit Recommendation Rule Engine · Phase 4 V2
================================================

5 条规则（每条独立、纯函数）→ 0~5 条 RuleResult。
无 LLM, 无黑盒, 完全可解释。

每条规则:
  - 输入: RuleContext（建筑 + 健康 + 风险 + 异常 + 传感器 + 构件）
  - 输出: List[RuleResult]（matched=False 时为空列表, 命中时为 1 条）
  - matched=True 时填充 evidence 字段, 包含:
      sensors:    相关传感器 + recent_values + 各 severity 异常数
      anomalies:  来自 RiskAlert 的关键字段
      bhi_context: {score, weakest_dimension} 或 None
      risk_context: {risk_level, explanation} 或 None
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import statistics

from app.db import models as m
from app.analytics.config import (
    RULE_ZSCORE_TRIGGER,
    RULE_ENV_SCORE_THRESHOLD,
    RULE_ENERGY_SCORE_THRESHOLD,
    RULE_RECENT_WINDOW_DAYS,
    RULE_RECENT_VALUES_LIMIT,
)


# =================================================================
# 数据结构
# =================================================================
@dataclass
class RuleContext:
    """规则引擎的输入."""
    building: m.Building
    health: Optional[Dict[str, Any]]        # 来自 health assessment 服务的 dict
    risk: Optional[Dict[str, Any]]           # 含 risk_level
    anomalies: List[Dict[str, Any]]          # 已 dedup 的 anomaly dict
    sensors_by_metric: Dict[str, List[m.Sensor]]
    components: List[m.Component]


@dataclass
class RuleResult:
    """单条规则的输出."""
    matched: bool
    category: str
    issue_type: str
    title: str
    recommendation: str
    rationale: str
    next_action: str
    urgency: str                            # low/medium/high/critical
    estimated_cost_level: str               # low/medium/high
    expected_benefit: str                   # low/medium/high
    component_id: Optional[int]
    source: str                             # "rule:crack_growth"
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =================================================================
# 辅助函数
# =================================================================
def _recent_records_for_sensor(
    session_components: Any,  # unused, 直接用 session
    sensor: m.Sensor,
    window_days: int = RULE_RECENT_WINDOW_DAYS,
    limit: int = RULE_RECENT_VALUES_LIMIT,
) -> List[Dict[str, Any]]:
    """从已加载的监测数据中取最近 window_days 天内最近 limit 条记录.
    实际数据由 service 层注入; 此处仅根据 sensor.id 拼 placeholder,
    真实 recent_values 由 service 在调用 rule 前填充到 evidence 缓存中.
    此函数保留为空 query hook, 当前由 service 自行查询。"""
    return []


def _anomalies_for_sensor(
    anomalies: List[Dict[str, Any]],
    sensor_id: int,
    metric: Optional[str] = None,
) -> List[Dict[str, Any]]:
    return [
        a for a in anomalies
        if a.get("sensor_id") == sensor_id
        and (metric is None or a.get("metric") == metric)
    ]


def _anomalies_for_metric(
    anomalies: List[Dict[str, Any]], metric: str
) -> List[Dict[str, Any]]:
    return [a for a in anomalies if a.get("metric") == metric]


def _has_high_severity(anoms: List[Dict[str, Any]]) -> bool:
    return any(a.get("severity") == "high" for a in anoms)


def _zscore_for_series(series: List[float], current: float) -> float:
    if len(series) < 5:
        return 0.0
    try:
        mean = statistics.fmean(series)
        stdev = statistics.stdev(series)
    except statistics.StatisticsError:
        return 0.0
    if stdev == 0:
        return 0.0
    return abs((current - mean) / stdev)


def _empty_evidence() -> Dict[str, Any]:
    return {
        "sensors": [],
        "anomalies": [],
        "bhi_context": None,
        "risk_context": None,
    }


def _build_context_block(
    health: Optional[Dict[str, Any]],
    risk: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "bhi_context": (
            {
                "score": health.get("score"),
                "weakest_dimension": _weakest_dimension(health),
            }
            if health
            else None
        ),
        "risk_context": (
            {
                "risk_level": risk.get("risk_level"),
                "explanation": risk.get("explanation"),
            }
            if risk
            else None
        ),
    }


def _weakest_dimension(health: Dict[str, Any]) -> Optional[str]:
    """从 health dict 中找最弱维度."""
    if not health:
        return None
    dims = {
        "structural_safety": health.get("structural_safety"),
        "facility_condition": health.get("facility_condition"),
        "environmental_quality": health.get("environmental_quality"),
        "energy_performance": health.get("energy_performance"),
        "fire_safety": health.get("fire_safety"),
    }
    valid = {k: v for k, v in dims.items() if isinstance(v, (int, float))}
    if not valid:
        return None
    return min(valid.items(), key=lambda x: x[1])[0]


# =================================================================
# 5 条规则
# =================================================================
def rule_crack_growth(
    ctx: RuleContext,
    recent_values_by_sensor: Dict[int, List[Dict[str, Any]]],
) -> List[RuleResult]:
    """Rule 1: 裂缝生长
    Trigger: 至少 1 个 crack_width 异常 OR crack_width zscore abs > 2 in last 30d
    """
    sensors = ctx.sensors_by_metric.get("crack_width", [])
    anoms = _anomalies_for_metric(ctx.anomalies, "crack_width")

    # 检查 z-score
    zscore_triggered = False
    for s in sensors:
        recents = recent_values_by_sensor.get(s.id, [])
        if not recents:
            continue
        vals = [r["value"] for r in recents]
        current = vals[-1]
        history = vals[:-1] if len(vals) > 1 else []
        if _zscore_for_series(history, current) > RULE_ZSCORE_TRIGGER:
            zscore_triggered = True
            break

    if not anoms and not zscore_triggered:
        return []

    urgency = "high" if _has_high_severity(anoms) else "medium"
    # 关联构件: 取第一个 crack_width 传感器挂的 component
    comp_id = sensors[0].component_id if sensors else None

    # 收集 evidence
    sensors_block = []
    for s in sensors:
        recents = recent_values_by_sensor.get(s.id, [])
        sensor_anoms = _anomalies_for_sensor(ctx.anomalies, s.id, "crack_width")
        sensors_block.append({
            "sensor_id": s.id,
            "metric": s.sensor_type,
            "name": s.name,
            "unit": s.unit,
            "location": s.location,
            "recent_values": recents[-RULE_RECENT_VALUES_LIMIT:],
            "anomaly_count_by_severity": {
                "high": sum(1 for a in sensor_anoms if a.get("severity") == "high"),
                "medium": sum(1 for a in sensor_anoms if a.get("severity") == "medium"),
                "low": sum(1 for a in sensor_anoms if a.get("severity") == "low"),
            },
        })

    evidence = _empty_evidence()
    evidence["sensors"] = sensors_block
    evidence["anomalies"] = [
        {
            "sensor_id": a.get("sensor_id"),
            "metric": a.get("metric"),
            "timestamp": str(a.get("timestamp")),
            "current_value": a.get("current_value"),
            "detection_method": a.get("detection_method"),
            "severity": a.get("severity"),
            "explanation": a.get("explanation"),
        }
        for a in anoms[:10]
    ]
    evidence.update(_build_context_block(ctx.health, ctx.risk))

    return [
        RuleResult(
            matched=True,
            category="Structural",
            issue_type="crack_growth",
            title="Conduct detailed inspection of affected structural components",
            recommendation=(
                "Conduct detailed inspection of affected structural components "
                "to evaluate crack propagation, structural integrity, and "
                "remaining service capacity."
            ),
            rationale=(
                "Crack monitoring indicates a sustained increasing trend and "
                "abnormal variation in the recent monitoring window. "
                "Prototype anomaly detection flagged the affected sensor."
            ),
            next_action=(
                "Review by qualified engineering personnel and perform detailed "
                "inspection including crack mapping and material assessment."
            ),
            urgency=urgency,
            estimated_cost_level="medium",
            expected_benefit="high",
            component_id=comp_id,
            source="rule:crack_growth",
            evidence=evidence,
        )
    ]


def rule_tilt_trend(
    ctx: RuleContext,
    recent_values_by_sensor: Dict[int, List[Dict[str, Any]]],
) -> List[RuleResult]:
    """Rule 2: 倾斜趋势
    Trigger: 至少 1 个 tilt 异常 OR tilt zscore abs > 2 in last 30d
    """
    sensors = ctx.sensors_by_metric.get("tilt", [])
    anoms = _anomalies_for_metric(ctx.anomalies, "tilt")

    zscore_triggered = False
    for s in sensors:
        recents = recent_values_by_sensor.get(s.id, [])
        if not recents:
            continue
        vals = [r["value"] for r in recents]
        current = vals[-1]
        history = vals[:-1] if len(vals) > 1 else []
        if _zscore_for_series(history, current) > RULE_ZSCORE_TRIGGER:
            zscore_triggered = True
            break

    if not anoms and not zscore_triggered:
        return []

    urgency = "high" if _has_high_severity(anoms) else "medium"
    comp_id = sensors[0].component_id if sensors else None

    sensors_block = []
    for s in sensors:
        recents = recent_values_by_sensor.get(s.id, [])
        sensor_anoms = _anomalies_for_sensor(ctx.anomalies, s.id, "tilt")
        sensors_block.append({
            "sensor_id": s.id,
            "metric": s.sensor_type,
            "name": s.name,
            "unit": s.unit,
            "location": s.location,
            "recent_values": recents[-RULE_RECENT_VALUES_LIMIT:],
            "anomaly_count_by_severity": {
                "high": sum(1 for a in sensor_anoms if a.get("severity") == "high"),
                "medium": sum(1 for a in sensor_anoms if a.get("severity") == "medium"),
                "low": sum(1 for a in sensor_anoms if a.get("severity") == "low"),
            },
        })

    evidence = _empty_evidence()
    evidence["sensors"] = sensors_block
    evidence["anomalies"] = [
        {
            "sensor_id": a.get("sensor_id"),
            "metric": a.get("metric"),
            "timestamp": str(a.get("timestamp")),
            "current_value": a.get("current_value"),
            "detection_method": a.get("detection_method"),
            "severity": a.get("severity"),
            "explanation": a.get("explanation"),
        }
        for a in anoms[:10]
    ]
    evidence.update(_build_context_block(ctx.health, ctx.risk))

    return [
        RuleResult(
            matched=True,
            category="Structural",
            issue_type="tilt_trend",
            title="Inspect potential differential deformation and structural elements",
            recommendation=(
                "Inspect potential differential deformation and affected "
                "structural elements to determine if observed inclination is "
                "progressive or stable."
            ),
            rationale=(
                "Tilt monitoring indicates progressive inclination trend or "
                "abnormal variation in the recent monitoring window. "
                "Prototype anomaly detection flagged the affected sensor."
            ),
            next_action=(
                "Engage qualified surveyor to assess deformation pattern, "
                "foundation settlement indicators, and reference network."
            ),
            urgency=urgency,
            estimated_cost_level="medium",
            expected_benefit="high",
            component_id=comp_id,
            source="rule:tilt_trend",
            evidence=evidence,
        )
    ]


def rule_moisture_control(
    ctx: RuleContext,
    recent_values_by_sensor: Dict[int, List[Dict[str, Any]]],
) -> List[RuleResult]:
    """Rule 3: 湿度 / 围护
    Trigger: 至少 1 个 humidity 异常 OR environmental_quality < 80
    """
    sensors = ctx.sensors_by_metric.get("humidity", [])
    anoms = _anomalies_for_metric(ctx.anomalies, "humidity")
    env_score = (ctx.health or {}).get("environmental_quality") if ctx.health else None

    triggered = bool(anoms) or (
        env_score is not None and env_score < RULE_ENV_SCORE_THRESHOLD
    )
    if not triggered:
        return []

    if env_score is not None and env_score < 60:
        urgency = "high"
    else:
        urgency = "medium"
    comp_id = sensors[0].component_id if sensors else None

    sensors_block = []
    for s in sensors:
        recents = recent_values_by_sensor.get(s.id, [])
        sensor_anoms = _anomalies_for_sensor(ctx.anomalies, s.id, "humidity")
        sensors_block.append({
            "sensor_id": s.id,
            "metric": s.sensor_type,
            "name": s.name,
            "unit": s.unit,
            "location": s.location,
            "recent_values": recents[-RULE_RECENT_VALUES_LIMIT:],
            "anomaly_count_by_severity": {
                "high": sum(1 for a in sensor_anoms if a.get("severity") == "high"),
                "medium": sum(1 for a in sensor_anoms if a.get("severity") == "medium"),
                "low": sum(1 for a in sensor_anoms if a.get("severity") == "low"),
            },
        })

    evidence = _empty_evidence()
    evidence["sensors"] = sensors_block
    evidence["anomalies"] = [
        {
            "sensor_id": a.get("sensor_id"),
            "metric": a.get("metric"),
            "timestamp": str(a.get("timestamp")),
            "current_value": a.get("current_value"),
            "detection_method": a.get("detection_method"),
            "severity": a.get("severity"),
            "explanation": a.get("explanation"),
        }
        for a in anoms[:10]
    ]
    evidence.update(_build_context_block(ctx.health, ctx.risk))

    return [
        RuleResult(
            matched=True,
            category="Environment",
            issue_type="moisture_control",
            title="Review ventilation, moisture control and envelope conditions",
            recommendation=(
                "Review ventilation, moisture control, and envelope conditions "
                "to identify sources of elevated humidity and reduce risk of "
                "condensation, mould, or material degradation."
            ),
            rationale=(
                "Humidity monitoring shows elevated or volatile readings, "
                "or environmental quality score is below prototype threshold. "
                "Prototype anomaly detection flagged the affected sensor."
            ),
            next_action=(
                "Inspect building envelope for moisture sources, review HVAC "
                "operation, and consider ventilation upgrade or moisture "
                "barrier installation."
            ),
            urgency=urgency,
            estimated_cost_level="low",
            expected_benefit="medium",
            component_id=comp_id,
            source="rule:moisture_control",
            evidence=evidence,
        )
    ]


def rule_energy_efficiency(
    ctx: RuleContext,
    recent_values_by_sensor: Dict[int, List[Dict[str, Any]]],
) -> List[RuleResult]:
    """Rule 4: 能耗
    Trigger: 至少 1 个 electricity 异常 OR energy_performance < 80
    """
    sensors = ctx.sensors_by_metric.get("electricity", [])
    anoms = _anomalies_for_metric(ctx.anomalies, "electricity")
    ener_score = (ctx.health or {}).get("energy_performance") if ctx.health else None

    triggered = bool(anoms) or (
        ener_score is not None and ener_score < RULE_ENERGY_SCORE_THRESHOLD
    )
    if not triggered:
        return []

    if ener_score is not None and ener_score < 60:
        urgency = "medium"
    else:
        urgency = "low"
    comp_id = sensors[0].component_id if sensors else None

    sensors_block = []
    for s in sensors:
        recents = recent_values_by_sensor.get(s.id, [])
        sensor_anoms = _anomalies_for_sensor(ctx.anomalies, s.id, "electricity")
        sensors_block.append({
            "sensor_id": s.id,
            "metric": s.sensor_type,
            "name": s.name,
            "unit": s.unit,
            "location": s.location,
            "recent_values": recents[-RULE_RECENT_VALUES_LIMIT:],
            "anomaly_count_by_severity": {
                "high": sum(1 for a in sensor_anoms if a.get("severity") == "high"),
                "medium": sum(1 for a in sensor_anoms if a.get("severity") == "medium"),
                "low": sum(1 for a in sensor_anoms if a.get("severity") == "low"),
            },
        })

    evidence = _empty_evidence()
    evidence["sensors"] = sensors_block
    evidence["anomalies"] = [
        {
            "sensor_id": a.get("sensor_id"),
            "metric": a.get("metric"),
            "timestamp": str(a.get("timestamp")),
            "current_value": a.get("current_value"),
            "detection_method": a.get("detection_method"),
            "severity": a.get("severity"),
            "explanation": a.get("explanation"),
        }
        for a in anoms[:10]
    ]
    evidence.update(_build_context_block(ctx.health, ctx.risk))

    return [
        RuleResult(
            matched=True,
            category="Energy",
            issue_type="energy_efficiency",
            title="Review electrical equipment operation and energy efficiency opportunities",
            recommendation=(
                "Review electrical equipment operation and identify energy "
                "efficiency opportunities, including load management and "
                "potential equipment upgrade."
            ),
            rationale=(
                "Energy consumption pattern shows abnormal variation or "
                "elevated baseline, or energy performance score is below "
                "prototype threshold."
            ),
            next_action=(
                "Audit major electrical loads, review equipment schedules, "
                "and identify efficiency opportunities including retrofit to "
                "higher-efficiency equipment."
            ),
            urgency=urgency,
            estimated_cost_level="low",
            expected_benefit="medium",
            component_id=comp_id,
            source="rule:energy_efficiency",
            evidence=evidence,
        )
    ]


def rule_comprehensive_assessment(
    ctx: RuleContext,
    recent_values_by_sensor: Dict[int, List[Dict[str, Any]]],
) -> List[RuleResult]:
    """Rule 5: 综合评估
    Trigger: risk_level in (Abnormal, HighRisk)
    """
    risk_level = (ctx.risk or {}).get("risk_level")
    if risk_level not in ("Abnormal", "HighRisk"):
        return []

    urgency = "high" if risk_level == "HighRisk" else "medium"
    comp_id = ctx.components[0].id if ctx.components else None

    # 综合 rule 不需要 sensors block, 走 evidence 的 bhi/risk context
    evidence = _empty_evidence()
    # 把所有 anomaly 数量统计放入 evidence
    total_anoms = len(ctx.anomalies)
    high_count = sum(1 for a in ctx.anomalies if a.get("severity") == "high")
    medium_count = sum(1 for a in ctx.anomalies if a.get("severity") == "medium")
    evidence["anomaly_summary"] = {
        "total": total_anoms,
        "high": high_count,
        "medium": medium_count,
    }
    evidence["anomalies"] = [
        {
            "sensor_id": a.get("sensor_id"),
            "metric": a.get("metric"),
            "timestamp": str(a.get("timestamp")),
            "current_value": a.get("current_value"),
            "detection_method": a.get("detection_method"),
            "severity": a.get("severity"),
            "explanation": a.get("explanation"),
        }
        for a in ctx.anomalies[:10]
    ]
    evidence.update(_build_context_block(ctx.health, ctx.risk))

    return [
        RuleResult(
            matched=True,
            category="Structural",
            issue_type="comprehensive_assessment",
            title="Conduct comprehensive engineering assessment of the building",
            recommendation=(
                "Conduct a comprehensive engineering assessment of the building "
                "to integrate structural, environmental, and operational "
                "indicators into a unified retrofit strategy."
            ),
            rationale=(
                f"Multiple risk factors detected at the building level "
                f"({total_anoms} prototype anomalies including {high_count} "
                f"high-severity). Prototype risk classification places this "
                f"building at {risk_level}, indicating integrated review is "
                f"warranted."
            ),
            next_action=(
                "Commission a comprehensive engineering assessment by qualified "
                "professionals covering structural, MEP, and envelope systems."
            ),
            urgency=urgency,
            estimated_cost_level="high",
            expected_benefit="high",
            component_id=comp_id,
            source="rule:comprehensive_assessment",
            evidence=evidence,
        )
    ]
