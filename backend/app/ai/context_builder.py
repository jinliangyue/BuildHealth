"""
Engineering Context Builder · Phase 5 V3
=======================================

把已有 V1 / V2 工程数据组装成 AI 用结构化 Context.

关键原则 (per spec):
- 不重新计算任何 BHI / Risk / Priority / Anomaly / Recommendation
- 全部从已有 service 读取
- 复用 assessment_svc + retrofit_service
- 不写库

输出 EngineeringContext dataclass,供 Provider 使用.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from app.db import models as m
from app.services import assessment as assessment_svc
from app.services import retrofit_service as retrofit_svc
from app.ai.schemas import (
    AIEvidenceRef,
    ContextBuildingInfo,
    ContextComponentInfo,
    ContextHealthInfo,
    ContextMonitoringSummary,
    ContextRetrofitInfo,
    ContextRiskInfo,
    ContextSensorInfo,
    EngineeringContext,
)
from app.core.config import AI_DISCLAIMER, AI_VERSION


# 1-based 索引用于 evidence_path
def _building_path(building_id: int) -> str:
    return f"/api/buildings/{building_id}"


def _health_path(building_id: int) -> str:
    return f"/api/buildings/{building_id}/health"


def _risk_path(building_id: int) -> str:
    return f"/api/buildings/{building_id}/risk"


def _alerts_path(building_id: int) -> str:
    return f"/api/buildings/{building_id}/alerts"


def _retrofit_path(building_id: int) -> str:
    return f"/api/buildings/{building_id}/retrofit"


def build_engineering_context(
    session: Session, building_id: int
) -> Optional[EngineeringContext]:
    """
    构建单建筑的 EngineeringContext.

    Returns None if building not found.
    """
    # 本请求内这栋建筑的分析只算一次：anomalies / health / risk 由
    # analyze_building 统一产出，并向下传给 retrofit decision 复用。
    # 此前 context_builder 自己算一遍，链路里的 retrofit decision 又算一遍，
    # 同一栋建筑的异常检测在一次请求里跑两次。
    analysis = assessment_svc.analyze_building(session, building_id)
    if analysis is None:
        return None

    building = analysis.building

    # 1. 基础元数据（已随 analysis 一次读入）
    components_rows = analysis.components
    sensors_rows = analysis.sensors

    # 2. 复用 V1 services 的计算结果
    anomalies = analysis.anomalies
    health = analysis.health
    risk = analysis.risk

    # 3. 复用 V2 service 获取完整 retrofit decision (含 evidence)，共享同一份分析
    retrofit_decision = retrofit_svc.get_retrofit_decision(
        session, building_id, analysis=analysis
    )
    if retrofit_decision is None:
        retrofit_decision = {
            "overall_priority": 0.0,
            "overall_priority_level": "Low",
            "calculation_version": "RP-v1.0",
            "recommendations": [],
            "engineering_notes": [],
        }

    # 4. 统计 monitoring 数据
    sensor_infos: List[ContextSensorInfo] = []
    by_metric: Dict[str, int] = {}
    total_records = 0
    # 一次读入本建筑所有传感器的记录（此前每个传感器一条查询），
    # 每组按 timestamp 降序，[0] 即最新一条，与逐传感器查询结果一致。
    records_by_sensor = assessment_svc.load_records_by_sensor(
        session, [s.id for s in sensors_rows]
    )
    for s in sensors_rows:
        records = records_by_sensor.get(s.id, [])
        count = len(records)
        total_records += count
        by_metric[s.sensor_type] = by_metric.get(s.sensor_type, 0) + count
        latest = records[0] if records else None
        sensor_infos.append(
            ContextSensorInfo(
                id=s.id,
                sensor_type=s.sensor_type,
                name=s.name,
                unit=s.unit,
                location=s.location,
                status=s.status,
                record_count=count,
                latest_value=latest.value if latest else None,
                latest_timestamp=latest.timestamp if latest else None,
            )
        )

    # 5. 异常统计
    anomaly_by_sev = {"high": 0, "medium": 0, "low": 0}
    anomaly_by_method: Dict[str, int] = {}
    for a in anomalies:
        sev = a.get("severity", "low")
        if sev in anomaly_by_sev:
            anomaly_by_sev[sev] += 1
        m_name = a.get("detection_method", "unknown")
        anomaly_by_method[m_name] = anomaly_by_method.get(m_name, 0) + 1

    monitoring_summary = ContextMonitoringSummary(
        total_records=total_records,
        by_metric=by_metric,
        anomaly_total=len(anomalies),
        anomaly_by_severity=anomaly_by_sev,
        anomaly_by_method=anomaly_by_method,
    )

    # 6. Health / Risk 包装
    dims = {
        "structural_safety": health.get("structural_safety"),
        "facility_condition": health.get("facility_condition"),
        "environmental_quality": health.get("environmental_quality"),
        "energy_performance": health.get("energy_performance"),
        "fire_safety": health.get("fire_safety"),
    }
    weakest = None
    valid_dims = {k: v for k, v in dims.items() if isinstance(v, (int, float))}
    if valid_dims:
        weakest = min(valid_dims.items(), key=lambda x: x[1])[0]

    health_info = ContextHealthInfo(
        bhi=health.get("score"),
        dimensions=dims,
        weakest_dimension=weakest,
        calculation_version=health.get("calculation_version"),
        explanation=health.get("explanation"),
    )

    risk_info = ContextRiskInfo(
        risk_level=risk.get("risk_level"),
        explanation=risk.get("explanation"),
        n_high=risk.get("n_high", 0),
        n_medium=risk.get("n_medium", 0),
        n_low=risk.get("n_low", 0),
    )

    # 7. Retrofit 包装
    retrofit_info = ContextRetrofitInfo(
        overall_priority=retrofit_decision["overall_priority"],
        overall_priority_level=retrofit_decision["overall_priority_level"].value
        if hasattr(retrofit_decision["overall_priority_level"], "value")
        else str(retrofit_decision["overall_priority_level"]),
        calculation_version=retrofit_decision.get("calculation_version"),
        recommendation_count=len(retrofit_decision["recommendations"]),
        recommendations=retrofit_decision["recommendations"],
        engineering_notes=[
            n.text if hasattr(n, "text") else n.get("text", "")
            for n in retrofit_decision["engineering_notes"]
        ],
    )

    # 8. 自动从 retrofit 收集顶层 evidence
    evidence_chain: List[AIEvidenceRef] = []
    # 8a. Building
    evidence_chain.append(
        AIEvidenceRef(
            source_type="building",
            source_id=building.id,
            metric=None,
            description=(
                f"{building.name} · {building.building_type} · "
                f"{building.floors}F · age {building.current_age}y · "
                f"structure={building.structure_type}"
            ),
            reference_path=_building_path(building.id),
        )
    )
    # 8b. Health
    if health_info.bhi is not None:
        evidence_chain.append(
            AIEvidenceRef(
                source_type="health",
                source_id=None,
                metric=None,
                description=(
                    f"BHI={health_info.bhi:.2f} (calculation_version="
                    f"{health_info.calculation_version}); "
                    f"weakest dimension: {health_info.weakest_dimension}"
                ),
                reference_path=_health_path(building.id),
            )
        )
    # 8c. Risk
    if risk_info.risk_level is not None:
        evidence_chain.append(
            AIEvidenceRef(
                source_type="risk",
                source_id=None,
                metric=None,
                description=(
                    f"Risk level: {risk_info.risk_level} "
                    f"(HIGH={risk_info.n_high}, MEDIUM={risk_info.n_medium}, "
                    f"LOW={risk_info.n_low})"
                ),
                reference_path=_risk_path(building.id),
            )
        )
    # 8d. Retrofit recommendations (top 3)
    for rec in retrofit_decision["recommendations"][:3]:
        evidence_chain.append(
            AIEvidenceRef(
                source_type="retrofit_recommendation",
                source_id=rec.get("id"),
                metric=rec.get("issue_type"),
                description=(
                    f"[{rec.get('category')}] {rec.get('title')} "
                    f"(priority={rec.get('priority_score'):.2f}, "
                    f"urgency={rec.get('urgency')})"
                ),
                reference_path=f"{_retrofit_path(building.id)}#{rec.get('id')}",
            )
        )
    # 8e. Top anomalies (HIGH severity, max 3)
    high_anomalies = sorted(
        [a for a in anomalies if a.get("severity") == "high"],
        key=lambda a: a.get("timestamp"),
        reverse=True,
    )[:3]
    for a in high_anomalies:
        evidence_chain.append(
            AIEvidenceRef(
                source_type="anomaly",
                source_id=a.get("sensor_id"),
                metric=a.get("metric"),
                description=(
                    f"{a.get('metric')}={a.get('current_value'):.3f} "
                    f"({a.get('detection_method')}, severity={a.get('severity')}) "
                    f"at {a.get('timestamp')}"
                ),
                reference_path=_alerts_path(building.id),
            )
        )

    # 9. 组件 / 建筑信息
    building_info = ContextBuildingInfo(
        building_id=building.id,
        name=building.name,
        address=building.address,
        year_built=building.year_built,
        current_age=building.current_age,
        design_life=building.design_life,
        building_type=building.building_type,
        structure_type=building.structure_type,
        floors=building.floors,
        area=building.area,
    )
    component_infos = [
        ContextComponentInfo(
            id=c.id,
            name=c.name,
            component_type=c.component_type,
            location=c.location,
            condition_status=c.condition_status,
        )
        for c in components_rows
    ]

    return EngineeringContext(
        building_id=building_id,
        building=building_info,
        components=component_infos,
        sensors=sensor_infos,
        monitoring_summary=monitoring_summary,
        health=health_info,
        risk=risk_info,
        retrofit=retrofit_info,
        evidence_chain=evidence_chain,
        disclaimer=AI_DISCLAIMER,
        generated_at=datetime.utcnow(),
    )
