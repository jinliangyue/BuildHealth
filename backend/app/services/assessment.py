"""
Analysis Service · 完整计算链路编排
调用 Analytics Engine 但不暴露给 API 层。
API 层只调用 service.assess_building() 等高层方法。
"""
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import models as m
from app.analytics import anomaly as anom
from app.analytics import health as ha
from app.analytics import risk as rk
from app.analytics.config import ANOMALY_DEDUP_HOURS


def get_metric_series(
    session: Session, building_id: int, metric: str
) -> List[Tuple[datetime, float]]:
    """拉取某 building 某 metric 的全部历史值（按时间升序）。"""
    records = (
        session.query(m.MonitoringRecord, m.Sensor)
        .join(m.Sensor, m.MonitoringRecord.sensor_id == m.Sensor.id)
        .filter(m.Sensor.building_id == building_id)
        .filter(m.Sensor.sensor_type == metric)
        .order_by(m.MonitoringRecord.timestamp)
        .all()
    )
    return [(rec.MonitoringRecord.timestamp, rec.MonitoringRecord.value) for rec in records]


def run_anomaly_detection(session: Session, building_id: int) -> List[Dict]:
    """
    对一栋建筑的全部传感器跑 3 种异常检测，返回 anomaly 字典列表。
    不写库——纯计算层。service 调用方决定是否落库。
    """
    sensors = session.query(m.Sensor).filter(m.Sensor.building_id == building_id).all()
    all_anomalies: List[Dict] = []
    for s in sensors:
        series = get_metric_series(session, building_id, s.sensor_type)
        if not series:
            continue
        seen_sigs: Dict[Tuple, datetime] = {}
        for i, (ts, val) in enumerate(series):
            prev = series[i - 1][1] if i > 0 else None
            history = [series[j][1] for j in range(max(0, i - 168), i)]
            results = anom.detect_for_record(
                sensor_id=s.id,
                building_id=building_id,
                metric=s.sensor_type,
                timestamp=ts,
                value=val,
                previous_value=prev,
                history_values=history,
            )
            for a in results:
                sig = (s.id, s.sensor_type, a.detection_method, a.severity)
                last_ts = seen_sigs.get(sig)
                if last_ts and (ts - last_ts).total_seconds() < ANOMALY_DEDUP_HOURS * 3600:
                    continue
                seen_sigs[sig] = ts
                all_anomalies.append(
                    {
                        "sensor_id": a.sensor_id,
                        "metric": a.metric,
                        "timestamp": ts,
                        "current_value": a.current_value,
                        "baseline_value": a.baseline_value,
                        "change": a.change,
                        "detection_method": a.detection_method,
                        "severity": a.severity,
                        "explanation": a.explanation,
                    }
                )
    return all_anomalies


def compute_health_assessment(
    session: Session,
    building: m.Building,
    anomalies: List[Dict],
) -> Dict:
    """基于建筑 + 异常列表 + 监测数据计算 BHI（不写库）。"""
    n_high = sum(1 for a in anomalies if a["severity"] == "high")
    n_medium = sum(1 for a in anomalies if a["severity"] == "medium")
    n_low = sum(1 for a in anomalies if a["severity"] == "low")

    structural = ha.score_structural_from_anomalies(n_high, n_medium, n_low)
    facility = ha.score_facility_from_age(building.current_age, building.design_life)

    temp_vals = [v for _, v in get_metric_series(session, building.id, "temperature")]
    hum_vals = [v for _, v in get_metric_series(session, building.id, "humidity")]
    elec_vals = [v for _, v in get_metric_series(session, building.id, "electricity")]

    environment = ha.score_environment_from_series(temp_vals, hum_vals)
    energy = ha.score_energy_from_series(elec_vals)
    fire = ha.score_fire_placeholder(building.floors, building.current_age)

    result = ha.compute_bhi(
        structural_safety=structural,
        facility_condition=facility,
        environmental_quality=environment,
        energy_performance=energy,
        fire_safety=fire,
        building_id=building.id,
    )

    return {
        "score": result.score,
        "structural_safety": result.structural_safety,
        "facility_condition": result.facility_condition,
        "environmental_quality": result.environmental_quality,
        "energy_performance": result.energy_performance,
        "fire_safety": result.fire_safety,
        "calculation_version": result.calculation_version,
        "explanation": result.explanation,
    }


def classify_risk_for_building(
    bhi: float, anomalies: List[Dict]
) -> Dict:
    """根据 BHI + 异常数计算风险等级。"""
    n_high = sum(1 for a in anomalies if a["severity"] == "high")
    n_medium = sum(1 for a in anomalies if a["severity"] == "medium")
    n_low = sum(1 for a in anomalies if a["severity"] == "low")
    cls = rk.classify_risk(
        bhi=bhi, n_high=n_high, n_medium=n_medium, n_low=n_low
    )
    return {
        "risk_level": cls.risk_level,
        "bhi": cls.bhi,
        "explanation": cls.explanation,
        "n_high": n_high,
        "n_medium": n_medium,
        "n_low": n_low,
    }


def get_dashboard_summary(session: Session) -> Dict:
    """Dashboard 聚合接口：所有数值从数据库实时计算，不硬编码。"""
    buildings = session.query(m.Building).order_by(m.Building.id).all()

    # 1. total_buildings
    total_buildings = len(buildings)

    # 2. monitoring_points（active sensor 数）
    monitoring_points = (
        session.query(func.count(m.Sensor.id))
        .filter(m.Sensor.status == "active")
        .scalar()
        or 0
    )

    # 3. active_alerts
    active_alerts = (
        session.query(func.count(m.RiskAlert.id))
        .filter(m.RiskAlert.status == "active")
        .scalar()
        or 0
    )

    # 4. average_health_score（取最新一次评估的平均）
    latest_assessments = []
    for b in buildings:
        latest = (
            session.query(m.HealthAssessment)
            .filter(m.HealthAssessment.building_id == b.id)
            .order_by(m.HealthAssessment.created_at.desc())
            .first()
        )
        if latest:
            latest_assessments.append(latest.score)
    average_health_score = (
        round(sum(latest_assessments) / len(latest_assessments), 2)
        if latest_assessments
        else 0.0
    )

    # 5. risk_distribution（基于最新评估 + 最新 alerts 重算分类）
    distribution = {"Normal": 0, "Attention": 0, "Abnormal": 0, "HighRisk": 0}
    ranking = []
    for b in buildings:
        latest_assessment = (
            session.query(m.HealthAssessment)
            .filter(m.HealthAssessment.building_id == b.id)
            .order_by(m.HealthAssessment.created_at.desc())
            .first()
        )
        if not latest_assessment:
            continue
        # 重新跑异常检测（用最新数据）
        anomalies = run_anomaly_detection(session, b.id)
        cls = classify_risk_for_building(latest_assessment.score, anomalies)
        distribution[cls["risk_level"]] += 1
        ranking.append(
            {
                "building_id": b.id,
                "name": b.name,
                "bhi": latest_assessment.score,
                "risk_level": cls["risk_level"],
            }
        )
    ranking.sort(key=lambda x: x["bhi"])  # 风险高的（bhi 低）在前

    # 6. recent_alerts（最新 10 条 active）
    recent = (
        session.query(m.RiskAlert)
        .filter(m.RiskAlert.status == "active")
        .order_by(m.RiskAlert.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "total_buildings": total_buildings,
        "monitoring_points": monitoring_points,
        "active_alerts": active_alerts,
        "average_health_score": average_health_score,
        "risk_distribution": distribution,
        "building_ranking": ranking,
        "recent_alerts": recent,
    }
