"""
Analysis Service · 完整计算链路编排
调用 Analytics Engine 但不暴露给 API 层。
API 层只调用 service.assess_building() 等高层方法。
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional
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


def get_building_series_map(
    session: Session, building_id: int
) -> Dict[str, List[Tuple[datetime, float]]]:
    """
    拉取一栋建筑**全部** metric 的历史序列，只发一条查询。

    返回 {sensor_type: [(timestamp, value), ...]}，每条序列按时间升序 ——
    与逐 metric 调用 get_metric_series() 的内容和顺序完全一致，
    但把 N 条查询压成 1 条。

    调用方用 series_map.get(metric, []) 取值：某个 metric 没有记录时
    get_metric_series() 返回空列表，这里对应「键不存在」。
    """
    rows = (
        session.query(
            m.Sensor.sensor_type,
            m.MonitoringRecord.timestamp,
            m.MonitoringRecord.value,
        )
        .join(m.Sensor, m.MonitoringRecord.sensor_id == m.Sensor.id)
        .filter(m.Sensor.building_id == building_id)
        .order_by(m.MonitoringRecord.timestamp)
        .all()
    )
    series_map: Dict[str, List[Tuple[datetime, float]]] = {}
    for sensor_type, ts, value in rows:
        series_map.setdefault(sensor_type, []).append((ts, value))
    return series_map


def load_sensors_by_building(
    session: Session, building_ids: List[int]
) -> Dict[int, List[m.Sensor]]:
    """
    一次读入多栋建筑的传感器，按 building_id 分组。
    用于聚合接口，替代「每栋建筑查一次传感器」的循环。
    """
    if not building_ids:
        return {}
    rows = (
        session.query(m.Sensor)
        .filter(m.Sensor.building_id.in_(building_ids))
        .order_by(m.Sensor.id)
        .all()
    )
    out: Dict[int, List[m.Sensor]] = {bid: [] for bid in building_ids}
    for s in rows:
        out.setdefault(s.building_id, []).append(s)
    return out


def load_series_map_by_building(
    session: Session, building_ids: List[int]
) -> Dict[int, Dict[str, List[Tuple[datetime, float]]]]:
    """
    一次读入多栋建筑的**全部**监测序列，按 building_id -> sensor_type 分组。
    每条序列按时间升序，与 get_building_series_map() 逐栋调用的结果一致。
    """
    if not building_ids:
        return {}
    rows = (
        session.query(
            m.Sensor.building_id,
            m.Sensor.sensor_type,
            m.MonitoringRecord.timestamp,
            m.MonitoringRecord.value,
        )
        .join(m.Sensor, m.MonitoringRecord.sensor_id == m.Sensor.id)
        .filter(m.Sensor.building_id.in_(building_ids))
        .order_by(m.MonitoringRecord.timestamp)
        .all()
    )
    out: Dict[int, Dict[str, List[Tuple[datetime, float]]]] = {}
    for bid, sensor_type, ts, value in rows:
        out.setdefault(bid, {}).setdefault(sensor_type, []).append((ts, value))
    return out


def load_records_by_sensor(
    session: Session, sensor_ids: List[int]
) -> Dict[int, List[m.MonitoringRecord]]:
    """
    一次读入多个传感器的全部监测记录，按 sensor_id 分组。

    每组内按 timestamp 降序，与逐传感器 `order_by(timestamp.desc())` 的结果
    一致（每组第一条即最新一条）。用于替代逐传感器的计数/取最新记录循环。
    """
    if not sensor_ids:
        return {}
    rows = (
        session.query(m.MonitoringRecord)
        .filter(m.MonitoringRecord.sensor_id.in_(sensor_ids))
        .order_by(m.MonitoringRecord.sensor_id, m.MonitoringRecord.timestamp.desc())
        .all()
    )
    out: Dict[int, List[m.MonitoringRecord]] = {}
    for r in rows:
        out.setdefault(r.sensor_id, []).append(r)
    return out


def get_latest_assessments(
    session: Session, building_ids: Optional[List[int]] = None
) -> Dict[int, m.HealthAssessment]:
    """
    一次读入每栋建筑最新一次 HealthAssessment，替代逐建筑查询。

    返回 {building_id: HealthAssessment}。同一 created_at 出现多条时取 id
    最大的一条，保证结果确定。
    """
    subq = (
        session.query(
            m.HealthAssessment.building_id.label("building_id"),
            func.max(m.HealthAssessment.created_at).label("max_created"),
        )
        .group_by(m.HealthAssessment.building_id)
        .subquery()
    )
    q = session.query(m.HealthAssessment).join(
        subq,
        (m.HealthAssessment.building_id == subq.c.building_id)
        & (m.HealthAssessment.created_at == subq.c.max_created),
    )
    if building_ids is not None:
        if not building_ids:
            return {}
        q = q.filter(m.HealthAssessment.building_id.in_(building_ids))
    out: Dict[int, m.HealthAssessment] = {}
    for a in q.all():
        prev = out.get(a.building_id)
        if prev is None or a.id > prev.id:
            out[a.building_id] = a
    return out


@dataclass
class BuildingAnalysis:
    """
    一栋建筑在本**请求生命周期内**的全部确定性分析结果。

    目的是让同一份结果只算一次：异常检测是当前响应时间的主要成本，
    而 AI 请求链此前会把同一栋建筑的异常检测跑两遍（context_builder
    跑一遍，链路里的 retrofit decision 又跑一遍）。

    这是请求作用域的对象，不是缓存：它随调用栈传递，请求结束即释放。
    没有全局状态、没有失效逻辑、没有新增基础设施。
    """
    building: m.Building
    components: List[m.Component]
    sensors: List[m.Sensor]
    series_map: Dict[str, List[Tuple[datetime, float]]]
    anomalies: List[Dict]
    health: Dict
    risk: Dict


def build_analysis(
    session: Session,
    building: m.Building,
    components: List[m.Component],
    sensors: List[m.Sensor],
    series_map: Dict[str, List[Tuple[datetime, float]]],
) -> BuildingAnalysis:
    """
    Run the anomaly → health → risk chain once for one building and return it
    as a reusable container.

    The preloaded inputs are always supplied here, so the chain issues no
    further queries; the session is still threaded through so the underlying
    functions keep working if a preload is ever missing.
    """
    anomalies = run_anomaly_detection(
        session, building.id, sensors=sensors, series_map=series_map
    )
    health = compute_health_assessment(
        session, building, anomalies, series_map=series_map
    )
    risk = classify_risk_for_building(health["score"], anomalies, building.id)
    return BuildingAnalysis(
        building=building,
        components=components,
        sensors=sensors,
        series_map=series_map,
        anomalies=anomalies,
        health=health,
        risk=risk,
    )


def analyze_building(
    session: Session, building_id: int
) -> Optional[BuildingAnalysis]:
    """
    Compute one building's full analysis (4 queries). Returns None if the
    building does not exist.
    """
    analysis_map = analyze_buildings(session, [building_id])
    return analysis_map.get(building_id)


def analyze_buildings(
    session: Session, building_ids: List[int]
) -> Dict[int, BuildingAnalysis]:
    """
    Compute the full analysis for several buildings using a FIXED number of
    queries (buildings / components / sensors / monitoring series), then do the
    per-building computation in memory.

    Query count therefore does not grow with the number of buildings, and each
    building's anomaly detection runs exactly once.
    """
    if not building_ids:
        return {}

    buildings = (
        session.query(m.Building)
        .filter(m.Building.id.in_(building_ids))
        .order_by(m.Building.id)
        .all()
    )
    found_ids = [b.id for b in buildings]

    components_rows = (
        session.query(m.Component)
        .filter(m.Component.building_id.in_(found_ids))
        .order_by(m.Component.id)
        .all()
    )
    components_by_building: Dict[int, List[m.Component]] = {bid: [] for bid in found_ids}
    for c in components_rows:
        components_by_building.setdefault(c.building_id, []).append(c)

    sensors_by_building = load_sensors_by_building(session, found_ids)
    series_by_building = load_series_map_by_building(session, found_ids)

    out: Dict[int, BuildingAnalysis] = {}
    for b in buildings:
        out[b.id] = build_analysis(
            session,
            b,
            components_by_building.get(b.id, []),
            sensors_by_building.get(b.id, []),
            series_by_building.get(b.id, {}),
        )
    return out


def run_anomaly_detection(
    session: Session,
    building_id: int,
    sensors: Optional[List[m.Sensor]] = None,
    series_map: Optional[Dict[str, List[Tuple[datetime, float]]]] = None,
) -> List[Dict]:
    """
    对一栋建筑的全部传感器跑 3 种异常检测，返回 anomaly 字典列表。
    不写库——纯计算层。service 调用方决定是否落库。

    sensors / series_map 为可选预加载入参，供聚合调用方复用已读数据，
    避免同一栋建筑的传感器与监测序列被反复查询。传 None 时行为与
    之前完全一致（自行查询）。
    """
    if sensors is None:
        sensors = (
            session.query(m.Sensor).filter(m.Sensor.building_id == building_id).all()
        )
    if series_map is None:
        series_map = get_building_series_map(session, building_id)
    all_anomalies: List[Dict] = []
    for s in sensors:
        series = series_map.get(s.sensor_type, [])
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
    series_map: Optional[Dict[str, List[Tuple[datetime, float]]]] = None,
) -> Dict:
    """
    基于建筑 + 异常列表 + 监测数据计算 BHI（不写库）。

    series_map 为可选预加载入参，聚合调用方复用时避免重复读取同一栋
    建筑的监测序列。传 None 时行为与之前完全一致。
    """
    n_high = sum(1 for a in anomalies if a["severity"] == "high")
    n_medium = sum(1 for a in anomalies if a["severity"] == "medium")
    n_low = sum(1 for a in anomalies if a["severity"] == "low")

    structural = ha.score_structural_from_anomalies(n_high, n_medium, n_low)
    facility = ha.score_facility_from_age(building.current_age, building.design_life)

    if series_map is None:
        series_map = get_building_series_map(session, building.id)

    temp_vals = [v for _, v in series_map.get("temperature", [])]
    hum_vals = [v for _, v in series_map.get("humidity", [])]
    elec_vals = [v for _, v in series_map.get("electricity", [])]

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
    bhi: float, anomalies: List[Dict], building_id: Optional[int] = None
) -> Dict:
    """根据 BHI + 异常数计算风险等级。"""
    n_high = sum(1 for a in anomalies if a["severity"] == "high")
    n_medium = sum(1 for a in anomalies if a["severity"] == "medium")
    n_low = sum(1 for a in anomalies if a["severity"] == "low")
    cls = rk.classify_risk(
        bhi=bhi,
        building_id=building_id if building_id is not None else 0,
        n_high=n_high,
        n_medium=n_medium,
        n_low=n_low,
    )
    return {
        "building_id": cls.building_id,
        "risk_level": cls.risk_level,
        "bhi": cls.bhi,
        "explanation": cls.explanation,
        "n_high": n_high,
        "n_medium": n_medium,
        "n_low": n_low,
    }


def get_buildings_overview(session: Session) -> List[Dict]:
    """
    Batch API: 一栋建筑只访问一次完整链路（health + risk + alert count）。
    单建筑内部异常被隔离，不会让整个 endpoint 失败。

    数据读入为固定次数的批量查询（建筑 / 最新评估 / 传感器 / 监测序列各一次），
    不再随建筑数量线性增长；单建筑的计算仍在内存中逐栋进行。
    """
    buildings = session.query(m.Building).order_by(m.Building.id).all()
    building_ids = [b.id for b in buildings]
    latest_map = get_latest_assessments(session, building_ids)
    sensors_by_building = load_sensors_by_building(session, building_ids)
    series_by_building = load_series_map_by_building(session, building_ids)

    items: List[Dict] = []
    for b in buildings:
        item = {"building": b, "health": None, "risk": None, "active_alert_count": 0}
        try:
            latest = latest_map.get(b.id)
            if latest:
                item["health"] = latest
                anomalies = run_anomaly_detection(
                    session,
                    b.id,
                    sensors=sensors_by_building.get(b.id, []),
                    series_map=series_by_building.get(b.id, {}),
                )
                cls = classify_risk_for_building(latest.score, anomalies, building_id=b.id)
                item["risk"] = cls
                item["active_alert_count"] = sum(
                    1 for a in anomalies if a.get("severity") in ("high", "medium")
                )
        except Exception:
            # 单建筑异常不影响整个列表
            session.rollback()
        items.append(item)
    return items


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

    # 4+5. 最新评估一次读入，同时驱动 average_health_score 与 risk_distribution
    #      （此前每个 building 各查两次，是纯粹的重复查询）
    building_ids = [b.id for b in buildings]
    latest_map = get_latest_assessments(session, building_ids)
    sensors_by_building = load_sensors_by_building(session, building_ids)
    series_by_building = load_series_map_by_building(session, building_ids)

    latest_assessments = [
        latest_map[b.id].score for b in buildings if b.id in latest_map
    ]
    average_health_score = (
        round(sum(latest_assessments) / len(latest_assessments), 2)
        if latest_assessments
        else 0.0
    )

    distribution = {"Normal": 0, "Attention": 0, "Abnormal": 0, "HighRisk": 0}
    ranking = []
    for b in buildings:
        latest_assessment = latest_map.get(b.id)
        if not latest_assessment:
            continue
        # 重新跑异常检测（用最新数据）
        anomalies = run_anomaly_detection(
            session,
            b.id,
            sensors=sensors_by_building.get(b.id, []),
            series_map=series_by_building.get(b.id, {}),
        )
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
