"""
Retrofit Decision Service · Phase 4 V2
======================================

Orchestrates:
  1. 加载 building + components + sensors
  2. 拉取最新 health + risk + anomalies (via assessment service)
  3. 注入 recent_values 给 rule engine
  4. 跑 5 条 rule → RuleResult 列表
  5. 对每条 RuleResult 计算 priority breakdown (RP-v1.0)
  6. 按 priority_score 降序排序
  7. 决定 overall_priority (max of rec.priority_score, 0 if empty)
  8. 填充 disclaimer + calculation_version

API 层只调用 service, 不直接接触 analytics 或 models。
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.db import models as m
from app.analytics import priority as pri
from app.analytics import recommendation_rules as rules
from app.analytics.config import (
    RETROFIT_DISCLAIMER,
    RETROFIT_PRIORITY_VERSION,
    RECOMMENDATION_RULES_VERSION,
    COMPONENT_IMPORTANCE,
    DEFAULT_COMPONENT_IMPORTANCE,
    RULE_RECENT_WINDOW_DAYS,
    RULE_RECENT_VALUES_LIMIT,
)
from app.services import assessment as assessment_svc
from app.services.assessment import BuildingAnalysis
from app.schemas.api import RetrofitPriorityLevelEnum


def _get_recent_values_by_sensor(
    session: Session,
    sensors: List[m.Sensor],
    window_days: int = RULE_RECENT_WINDOW_DAYS,
    limit: int = RULE_RECENT_VALUES_LIMIT,
) -> Dict[int, List[Dict[str, Any]]]:
    """
    对每个传感器拉取最近 window_days 天内最近 limit 条记录。

    用一条查询读入全部候选记录，再在内存里按传感器分组取尾部 limit 条，
    而不是每个传感器发一条查询。输出与逐传感器查询完全一致（升序）。
    """
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(days=window_days)
    result: Dict[int, List[Dict[str, Any]]] = {s.id: [] for s in sensors}
    if not sensors:
        return result

    sensor_ids = [s.id for s in sensors]
    rows = (
        session.query(m.MonitoringRecord)
        .filter(m.MonitoringRecord.sensor_id.in_(sensor_ids))
        .filter(m.MonitoringRecord.timestamp >= cutoff)
        .order_by(m.MonitoringRecord.timestamp)
        .all()
    )
    # 升序遍历，每个传感器只保留最后 limit 条（等价于 desc + limit 后反转）
    for r in rows:
        bucket = result.setdefault(r.sensor_id, [])
        bucket.append(r)
        if len(bucket) > limit:
            del bucket[0]

    for sid, recs in result.items():
        result[sid] = [
            {"timestamp": r.timestamp.isoformat(), "value": r.value} for r in recs
        ]
    return result


def _component_importance(component_id: Optional[int], components: List[m.Component]) -> float:
    if component_id is None:
        return DEFAULT_COMPONENT_IMPORTANCE
    for c in components:
        if c.id == component_id:
            return COMPONENT_IMPORTANCE.get(c.component_type, DEFAULT_COMPONENT_IMPORTANCE)
    return DEFAULT_COMPONENT_IMPORTANCE


def _sensors_by_metric(sensors: List[m.Sensor]) -> Dict[str, List[m.Sensor]]:
    out: Dict[str, List[m.Sensor]] = {}
    for s in sensors:
        out.setdefault(s.sensor_type, []).append(s)
    return out


def _build_evidence_block(rr: rules.RuleResult) -> Dict[str, Any]:
    """把 RuleResult.evidence 转为可直接 JSON 序列化的 dict (含 sensors block)."""
    return {
        "sensors": rr.evidence.get("sensors", []),
        "anomalies": rr.evidence.get("anomalies", []),
        "bhi_context": rr.evidence.get("bhi_context"),
        "risk_context": rr.evidence.get("risk_context"),
        "anomaly_summary": rr.evidence.get("anomaly_summary"),
    }


def _rule_result_to_dict(
    rr: rules.RuleResult,
    breakdown: pri.PriorityScoreBreakdown,
    building_id: int,
    rec_index: int,
) -> Dict[str, Any]:
    return {
        "id": rec_index,
        "building_id": building_id,
        "component_id": rr.component_id,
        "category": rr.category,
        "issue_type": rr.issue_type,
        "title": rr.title,
        "recommendation": rr.recommendation,
        "rationale": rr.rationale,
        "next_action": rr.next_action,
        "urgency": rr.urgency,
        "estimated_cost_level": rr.estimated_cost_level,
        "expected_benefit": rr.expected_benefit,
        "source": rr.source,
        "calculation_version": RECOMMENDATION_RULES_VERSION,
        "created_at": datetime.utcnow().isoformat(),
        "evidence": _build_evidence_block(rr),
        "priority_score": breakdown.total,
        "priority_breakdown": breakdown.to_dict(),
    }


# =================================================================
# 公开服务接口
# =================================================================
def generate_recommendations(
    session: Session,
    building_id: int,
    analysis: Optional[BuildingAnalysis] = None,
    recent_values_by_sensor: Optional[Dict[int, List[Dict[str, Any]]]] = None,
) -> List[Dict[str, Any]]:
    """
    对单建筑跑 5 条 rule, 计算每条 priority score, 按 score 降序返回 dict 列表.

    analysis 为可选的请求作用域分析结果。调用方若已经在同一请求里算过这栋
    建筑的 building/components/sensors/series/anomalies/health/risk，
    传进来即可完全跳过重复读取与重复计算。

    recent_values_by_sensor 为可选的批量预加载的最近记录（按 sensor_id）。
    聚合接口一次读入所有建筑后按需切分传入，避免每栋建筑各发一条查询。

    两个参数传 None 时行为与之前完全一致。
    """
    if analysis is not None:
        building = analysis.building
        components = analysis.components
        sensors = analysis.sensors
        series_map = analysis.series_map
        anomalies = analysis.anomalies
        health = analysis.health
        risk = analysis.risk
    else:
        building = session.get(m.Building, building_id)
        if building is None:
            return []

        components = (
            session.query(m.Component)
            .filter(m.Component.building_id == building_id)
            .all()
        )
        sensors = (
            session.query(m.Sensor)
            .filter(m.Sensor.building_id == building_id)
            .all()
        )

        # 一次读入本建筑全部监测序列，供异常检测 / BHI / trend score 共用。
        # 此前这三处各自重复查询同一批序列（3× 读放大）。
        series_map = assessment_svc.get_building_series_map(session, building_id)

        # 拉 health + risk + anomalies（复用已读入的 sensors 与 series_map）
        anomalies = assessment_svc.run_anomaly_detection(
            session, building_id, sensors=sensors, series_map=series_map
        )
        health = assessment_svc.compute_health_assessment(
            session, building, anomalies, series_map=series_map
        )
        risk = assessment_svc.classify_risk_for_building(
            health["score"], anomalies, building_id
        )

    sensors_by_metric = _sensors_by_metric(sensors)

    # 计算 trend score（复用同一份序列，不再重复查询）
    sensor_series_by_metric: Dict[str, List] = {
        metric: series_map.get(metric, []) for metric in sensors_by_metric
    }
    trend_score = pri.compute_trend_score(sensor_series_by_metric)

    # 拉 recent values 给 rule 的 evidence
    # recent_values_by_sensor 可由调用方批量预加载（聚合接口一次读入所有建筑），
    # 未提供时按本建筑传感器自行读取（单建筑端点路径）。
    if recent_values_by_sensor is None:
        recent_values_by_sensor = _get_recent_values_by_sensor(session, sensors)

    # 构造 RuleContext
    ctx = rules.RuleContext(
        building=building,
        health=health,
        risk=risk,
        anomalies=anomalies,
        sensors_by_metric=sensors_by_metric,
        components=components,
    )

    # 跑 5 条 rule
    matched_results: List[rules.RuleResult] = []
    matched_results.extend(rules.rule_crack_growth(ctx, recent_values_by_sensor))
    matched_results.extend(rules.rule_tilt_trend(ctx, recent_values_by_sensor))
    matched_results.extend(rules.rule_moisture_control(ctx, recent_values_by_sensor))
    matched_results.extend(rules.rule_energy_efficiency(ctx, recent_values_by_sensor))
    matched_results.extend(rules.rule_comprehensive_assessment(ctx, recent_values_by_sensor))

    # 对每条 RuleResult 计算 priority
    rule_dicts: List[Dict[str, Any]] = []
    for idx, rr in enumerate(matched_results, start=1):
        comp_imp = _component_importance(rr.component_id, components)
        try:
            breakdown = pri.compute_priority(
                risk_level=risk["risk_level"],
                trend_score=trend_score,
                component_importance=comp_imp,
                urgency=rr.urgency,
                cost_level=rr.estimated_cost_level,
            )
        except pri.PriorityInputError:
            # 防御性: 如果 trend_score 异常, 用默认 50
            breakdown = pri.compute_priority(
                risk_level=risk["risk_level"],
                trend_score=50.0,
                component_importance=comp_imp,
                urgency=rr.urgency,
                cost_level=rr.estimated_cost_level,
            )
        rule_dicts.append(_rule_result_to_dict(rr, breakdown, building_id, idx))

    # 按 priority_score 降序
    rule_dicts.sort(key=lambda x: x["priority_score"], reverse=True)
    return rule_dicts


def get_retrofit_decision(
    session: Session,
    building_id: int,
    analysis: Optional[BuildingAnalysis] = None,
) -> Optional[Dict[str, Any]]:
    """
    返回单建筑的完整 retrofit decision (含 engineering notes + disclaimer).

    analysis 为可选的请求作用域分析结果；调用方已算过同一栋建筑的
    anomalies / health / risk 时传入即可避免重复计算。传 None 时行为不变。
    """
    if analysis is not None:
        building = analysis.building
    else:
        building = session.get(m.Building, building_id)
    if building is None:
        return None

    recs = generate_recommendations(session, building_id, analysis=analysis)
    notes = (
        session.query(m.EngineeringNote)
        .filter(m.EngineeringNote.building_id == building_id)
        .order_by(m.EngineeringNote.created_at.asc())
        .all()
    )

    if recs:
        overall = recs[0]["priority_score"]
        level_str = pri.map_priority_level(overall)
    else:
        overall = 0.0
        level_str = "Low"

    # 字符串 → enum 值 (保持 API 输出与 schema 兼容)
    level_enum = {
        "Low": RetrofitPriorityLevelEnum.Low,
        "Medium": RetrofitPriorityLevelEnum.Medium,
        "High": RetrofitPriorityLevelEnum.High,
        "Very High": RetrofitPriorityLevelEnum.VeryHigh,
    }[level_str]

    return {
        "building_id": building_id,
        "building": building,
        "overall_priority": overall,
        "overall_priority_level": level_enum,
        "calculation_version": RETROFIT_PRIORITY_VERSION,
        "recommendations": recs,
        "engineering_notes": notes,
        "disclaimer": RETROFIT_DISCLAIMER,
    }


def get_retrofit_recommendation(
    session: Session,
    building_id: int,
    recommendation_id: int,
) -> Optional[Dict[str, Any]]:
    """返回单条 recommendation (含 priority breakdown).

    Note: 由于 V2 的 RetrofitRecommendation 当前不持久化 (实时计算),
    本函数对 generate_recommendations 的结果按 id 匹配. 真实 ID 由
    caller 负责保证 (e.g. 用 1-based index).
    """
    recs = generate_recommendations(session, building_id)
    if not recs:
        return None
    if recommendation_id < 1 or recommendation_id > len(recs):
        return None
    rec = recs[recommendation_id - 1]
    # 包装成 detail shape (id 字段)
    return {
        "id": recommendation_id,
        "building_id": building_id,
        **rec,
    }


def get_retrofit_overview(session: Session) -> Dict[str, Any]:
    """
    跨建筑聚合: 全部建筑的 retrofit 概览.

    先用固定次数的批量查询算出各建筑的 building/components/sensors/series
    与 anomalies/health/risk，再逐栋在内存里跑规则。此前每栋建筑会独立
    发 4 条查询并各自重跑异常检测，查询数随建筑数线性增长。
    """
    buildings = session.query(m.Building).order_by(m.Building.id).all()
    analysis_map = assessment_svc.analyze_buildings(session, [b.id for b in buildings])

    # 最近记录也一次读入（跨全部建筑的所有传感器），再按建筑切分传入，
    # 避免每栋建筑各发一条查询。
    all_sensors = [s for a in analysis_map.values() for s in a.sensors]
    recent_all = _get_recent_values_by_sensor(session, all_sensors)

    items: List[Dict[str, Any]] = []
    total_priority = 0.0
    counted = 0

    for b in buildings:
        try:
            analysis = analysis_map.get(b.id)
            recent_subset = (
                {s.id: recent_all.get(s.id, []) for s in analysis.sensors}
                if analysis is not None
                else None
            )
            recs = generate_recommendations(
                session,
                b.id,
                analysis=analysis,
                recent_values_by_sensor=recent_subset,
            )
        except Exception:
            session.rollback()
            recs = []

        if recs:
            overall = recs[0]["priority_score"]
            level_str = pri.map_priority_level(overall)
        else:
            overall = 0.0
            level_str = "Low"

        high_count = sum(1 for r in recs if r["priority_score"] >= 75.0)
        top_category = recs[0]["category"] if recs else "—"

        level_enum = {
            "Low": RetrofitPriorityLevelEnum.Low,
            "Medium": RetrofitPriorityLevelEnum.Medium,
            "High": RetrofitPriorityLevelEnum.High,
            "Very High": RetrofitPriorityLevelEnum.VeryHigh,
        }[level_str]

        items.append({
            "building": b,
            "overall_priority": overall,
            "overall_priority_level": level_enum,
            "recommendation_count": len(recs),
            "high_priority_count": high_count,
            "top_category": top_category,
        })

        total_priority += overall
        counted += 1

    average = round(total_priority / counted, 2) if counted > 0 else 0.0
    # 按 overall_priority 降序
    items.sort(key=lambda x: x["overall_priority"], reverse=True)

    return {
        "total": len(items),
        "items": items,
        "average_priority": average,
        "calculation_version": RETROFIT_PRIORITY_VERSION,
        "disclaimer": RETROFIT_DISCLAIMER,
    }
