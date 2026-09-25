"""
模拟工程数据生成器 · BuildHealth Phase 1
============================================

设计原则：
1. 不使用 random() 直出 - 每个指标都有 baseline + trend + periodic + noise + 可选 anomaly event
2. 3 种建筑原型：Healthy / Attention / Abnormal
3. 5 类指标：crack_width / tilt / temperature / humidity / electricity
4. 90 天 × 每天 1 条（足够触发统计检测 + 降低存储压力）
5. 写入数据库时 quality_flag='simulated' 强制标识

生成步骤：
1. 清理已有数据（dev only）
2. 创建 3 栋建筑
3. 每栋 5 个构件 + 5 个传感器（每个 metric 一个）
4. 生成 90 天监测记录
5. 立即跑异常检测 → 写入 RiskAlert
6. 立即跑健康评分 → 写入 HealthAssessment

可作为独立脚本运行：
    cd backend && python -m scripts.seed_data
"""
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import math
import random

# 让脚本可以从 backend/ 目录运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.db import models as m
from app.analytics import anomaly as anom
from app.analytics import health as ha
from app.analytics import risk as rk
from app.analytics.config import ANOMALY_DEDUP_HOURS

# 固定种子（保证测试可重现）
random.seed(42)


# =================================================================
# 数据模板
# =================================================================
BUILDING_PROFILES = {
    "healthy": {
        "building_type": "office",
        "structure_type": "frame",
        "design_life": 50,
        "metric_profiles": {
            "crack_width":   {"base": 0.10, "trend": 0.0,    "amp": 0.003, "noise": 0.0015, "event": None},
            "tilt":          {"base": 1.20, "trend": 0.0,    "amp": 0.01,  "noise": 0.01,   "event": None},
            "temperature":   {"base": 22.0, "trend": 0.0,    "amp": 5.0,   "noise": 0.4,    "event": None},
            "humidity":      {"base": 55.0, "trend": 0.0,    "amp": 8.0,   "noise": 1.0,    "event": None},
            "electricity":   {"base": 120.0,"trend": 0.0,    "amp": 30.0,  "noise": 2.5,    "event": None},
        },
    },
    "attention": {
        "building_type": "mixed",
        "structure_type": "shear",
        "design_life": 50,
        "metric_profiles": {
            "crack_width":   {"base": 0.15, "trend": 0.0008, "amp": 0.01, "noise": 0.005, "event": None},
            "tilt":          {"base": 1.80, "trend": 0.004,  "amp": 0.10, "noise": 0.05,  "event": None},
            "temperature":   {"base": 23.0, "trend": 0.0,    "amp": 5.0,  "noise": 1.2,   "event": None},
            "humidity":      {"base": 60.0, "trend": 0.02,   "amp": 8.0,  "noise": 3.0,   "event": None},
            "electricity":   {"base": 95.0, "trend": 0.0,    "amp": 25.0, "noise": 6.0,   "event": None},
        },
    },
    "abnormal": {
        "building_type": "residential",
        "structure_type": "masonry",
        "design_life": 50,
        "metric_profiles": {
            "crack_width":   {"base": 0.20, "trend": 0.005, "amp": 0.02, "noise": 0.01, "event": "spike"},
            "tilt":          {"base": 2.50, "trend": 0.015, "amp": 0.20, "noise": 0.10, "event": "spike"},
            "temperature":   {"base": 24.0, "trend": 0.0,   "amp": 5.0,  "noise": 1.5,  "event": None},
            "humidity":      {"base": 70.0, "trend": 0.05,  "amp": 8.0,  "noise": 4.0,  "event": None},
            "electricity":   {"base": 80.0, "trend": 0.0,   "amp": 20.0, "noise": 8.0,  "event": None},
        },
    },
}
_PROFILE_KEYS = list(BUILDING_PROFILES.keys())


COMPONENT_TEMPLATES = [
    ("F1-Column-A1", "column", "Ground floor east column"),
    ("F3-Beam-B2", "beam", "3rd floor secondary beam"),
    ("Wall-North", "wall", "North exterior wall"),
    ("Slab-Roof", "slab", "Roof slab"),
    ("Foundation-East", "foundation", "East foundation"),
]

# Phase 4 V2 · 每建筑 1 条工程笔记
ENGINEERING_NOTES_BY_KEY = {
    "healthy": (
        "Routine quarterly inspection completed. "
        "No major concerns identified. All monitoring metrics stable.",
        "field_note",
    ),
    "attention": (
        "Minor moisture observed at the north envelope connection during 2026 Q2 inspection. "
        "Recommend follow-up review of moisture barrier condition.",
        "site_inspection",
    ),
    "abnormal": (
        "Observed crack development around the south facade, "
        "significant spread since 2025. Recommended detailed structural inspection.",
        "site_inspection",
    ),
}

METRIC_UNITS = {
    "crack_width": "mm",
    "tilt": "‰",
    "temperature": "℃",
    "humidity": "%",
    "electricity": "kWh",
}


# =================================================================
# 生成函数
# =================================================================
def generate_timeseries(
    metric: str,
    profile: Dict,
    days: int,
    end_time: datetime,
    samples_per_day: int = 1,
) -> List[Tuple[datetime, float]]:
    """
    生成时间序列。返回 [(timestamp, value), ...]

    公式：
      value(t) = base
               + trend * t_days
               + amp * sin(2π * t_days)   # 日周期
               + noise                    # 高斯噪声
               + event(t)                 # 可选事件
    """
    series: List[Tuple[datetime, float]] = []
    base = profile["base"]
    trend = profile["trend"]
    amp = profile["amp"]
    noise_std = profile["noise"]
    event_type = profile.get("event")

    total_samples = days * samples_per_day
    interval = timedelta(days=1) / samples_per_day

    for i in range(total_samples):
        t = end_time - timedelta(days=days) + i * interval
        t_days = i / samples_per_day

        # 日周期（按一天内的相位）
        phase = (i % samples_per_day) / samples_per_day * 2 * math.pi
        periodic = amp * math.sin(phase)

        # 噪声
        noise = random.gauss(0, noise_std)

        # 趋势
        trend_val = trend * t_days

        # 事件（最后 14 天触发，用于 Abnormal 建筑）
        event_val = 0.0
        if event_type == "spike" and t_days > days - 14:
            # 后半段时间内单调放大
            event_progress = (t_days - (days - 14)) / 14.0
            event_val = base * (event_progress ** 1.5) * 2.0  # 最多 2 倍 base

        value = base + trend_val + periodic + noise + event_val
        # 物理约束：crack_width 不能为负
        if metric == "crack_width":
            value = max(0.0, value)
        elif metric == "humidity":
            value = max(0.0, min(100.0, value))

        series.append((t, round(value, 4)))

    return series


def wipe_database() -> None:
    """删除所有表（dev only · Phase 1 不挂生产）"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def build_building(session: Session, template: Dict) -> m.Building:
    b = m.Building(
        name=template["name"],
        address=template["address"],
        year_built=template["year_built"],
        building_type=template["building_type"],
        structure_type=template["structure_type"],
        floors=template["floors"],
        area=template["area"],
        design_life=template["design_life"],
        current_age=template["current_age"],
        description=template["description"],
    )
    session.add(b)
    session.flush()
    return b


def build_components(session: Session, building: m.Building) -> List[m.Component]:
    comps = []
    for name, ctype, desc in COMPONENT_TEMPLATES:
        c = m.Component(
            building_id=building.id,
            name=name,
            component_type=ctype,
            location=desc,
            condition_status="normal",
            description=f"{desc} of {building.name}",
        )
        session.add(c)
        comps.append(c)
    session.flush()
    return comps


def build_sensors(
    session: Session,
    building: m.Building,
    components: List[m.Component],
) -> List[m.Sensor]:
    """为每栋建筑创建 5 个传感器（每个 metric 一个，挂到第 1 个构件上）。"""
    sensors = []
    primary_comp = components[0]
    for metric, unit in METRIC_UNITS.items():
        s = m.Sensor(
            building_id=building.id,
            component_id=primary_comp.id,
            sensor_type=metric,
            name=f"{metric}_sensor_{building.id}",
            unit=unit,
            location=primary_comp.location,
            status="active",
        )
        session.add(s)
        sensors.append(s)
    session.flush()
    return sensors


def build_records(
    session: Session,
    building: m.Building,
    sensors: List[m.Sensor],
    template: Dict,
    days: int,
) -> int:
    """为每个传感器生成时间序列并批量插入。返回总记录数。"""
    end_time = datetime.utcnow().replace(microsecond=0, second=0, minute=0)
    total = 0
    for s in sensors:
        profile = template["metric_profiles"][s.sensor_type]
        series = generate_timeseries(s.sensor_type, profile, days, end_time)
        batch = [
            m.MonitoringRecord(
                sensor_id=s.id,
                timestamp=ts,
                value=val,
                quality_flag="simulated",
            )
            for ts, val in series
        ]
        session.bulk_save_objects(batch)
        total += len(batch)
    session.flush()
    return total


def build_engineering_note(
    session: Session,
    building: m.Building,
    components: List[m.Component],
    template_key: str,
) -> Optional[m.EngineeringNote]:
    """Phase 4 V2 · 为单建筑写入 1 条工程笔记 (从 ENGINEERING_NOTES_BY_KEY 读取)."""
    note = ENGINEERING_NOTES_BY_KEY.get(template_key)
    if note is None:
        return None
    text, source = note
    comp = components[0] if components else None
    n = m.EngineeringNote(
        building_id=building.id,
        component_id=comp.id if comp else None,
        text=text,
        source=source,
    )
    session.add(n)
    session.flush()
    return n


# =================================================================
# 异常检测 + 健康评分 + 风险分类（写入数据库）
# =================================================================
def run_anomaly_detection(session: Session, building: m.Building, sensors: List[m.Sensor]) -> List[m.RiskAlert]:
    """对每栋建筑的所有传感器监测数据跑 3 种异常检测，写入 RiskAlert。"""
    alerts: List[m.RiskAlert] = []
    now = datetime.utcnow()

    for s in sensors:
        # 拉取该传感器全部历史数据，按时间排序
        records = (
            session.query(m.MonitoringRecord)
            .filter(m.MonitoringRecord.sensor_id == s.id)
            .order_by(m.MonitoringRecord.timestamp)
            .all()
        )
        if not records:
            continue

        # 逐点检测
        seen_signatures: Dict[Tuple, datetime] = {}  # (method) -> last_ts
        for i, rec in enumerate(records):
            previous = records[i - 1].value if i > 0 else None
            history = [r.value for r in records[max(0, i - 168) : i]]  # 7 天窗口

            results = anom.detect_for_record(
                sensor_id=s.id,
                building_id=building.id,
                metric=s.sensor_type,
                timestamp=rec.timestamp,
                value=rec.value,
                previous_value=previous,
                history_values=history,
            )

            for a in results:
                sig = (s.id, s.sensor_type, a.detection_method, a.severity)
                last_ts = seen_signatures.get(sig)
                if last_ts and (rec.timestamp - last_ts).total_seconds() < ANOMALY_DEDUP_HOURS * 3600:
                    continue
                seen_signatures[sig] = rec.timestamp

                alert = m.RiskAlert(
                    building_id=building.id,
                    sensor_id=s.id,
                    metric=s.sensor_type,
                    timestamp=rec.timestamp,
                    current_value=a.current_value,
                    baseline_value=a.baseline_value,
                    change=a.change,
                    detection_method=a.detection_method,
                    severity=a.severity,
                    explanation=a.explanation,
                    status="active",
                )
                session.add(alert)
                alerts.append(alert)

    session.flush()
    return alerts


def run_health_assessment(
    session: Session, building: m.Building, sensors: List[m.Sensor], alerts: List[m.RiskAlert]
) -> m.HealthAssessment:
    """根据监测数据 + 异常数计算 BHI 并写入 HealthAssessment。"""
    # 异常统计
    n_high = sum(1 for a in alerts if a.severity == "high")
    n_medium = sum(1 for a in alerts if a.severity == "medium")
    n_low = sum(1 for a in alerts if a.severity == "low")

    structural = ha.score_structural_from_anomalies(n_high, n_medium, n_low)
    facility = ha.score_facility_from_age(building.current_age, building.design_life)

    # 拉取 temperature / humidity / electricity 序列
    temp_vals: List[float] = []
    hum_vals: List[float] = []
    elec_vals: List[float] = []
    for s in sensors:
        vals = [
            r.value
            for r in session.query(m.MonitoringRecord)
            .filter(m.MonitoringRecord.sensor_id == s.id)
            .all()
        ]
        if s.sensor_type == "temperature":
            temp_vals = vals
        elif s.sensor_type == "humidity":
            hum_vals = vals
        elif s.sensor_type == "electricity":
            elec_vals = vals

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

    assessment = m.HealthAssessment(
        building_id=building.id,
        score=result.score,
        structural_safety=result.structural_safety,
        facility_condition=result.facility_condition,
        environmental_quality=result.environmental_quality,
        energy_performance=result.energy_performance,
        fire_safety=result.fire_safety,
        calculation_version=result.calculation_version,
        explanation=result.explanation,
    )
    session.add(assessment)
    session.flush()
    return assessment


def run_risk_classification(
    session: Session, building: m.Building, assessment: m.HealthAssessment, alerts: List[m.RiskAlert]
) -> rk.RiskClassification:
    """根据 BHI + 异常数得到风险等级（不写 RiskAlert 表，与既有 alert 共存）。"""
    n_high = sum(1 for a in alerts if a.severity == "high")
    n_medium = sum(1 for a in alerts if a.severity == "medium")
    n_low = sum(1 for a in alerts if a.severity == "low")

    cls = rk.classify_risk(
        bhi=assessment.score,
        building_id=building.id,
        n_high=n_high,
        n_medium=n_medium,
        n_low=n_low,
    )

    # 把当前风险等级回写到最新一条 alert 的 status 备注（如果需要）
    # V1 选择不改 status（status 仍为 anomaly 触发状态）
    return cls


# =================================================================
# 主流程
# =================================================================
def main(
    n_buildings: int = 30,
    days: int = 180,
    seed: int = 42,
    verbose: bool = True,
) -> Dict:
    """完整数据初始化流程。返回统计字典。

    v1.1 扩规模(2026-09-26):
    - 默认 30 栋 / 5 sensors 每栋 / 180 天 / 1 sample/天 = 27000 records
    - 每栋随机选 healthy/attention/abnormal profile(1:1:1 比例大致保持)
    - 每栋的 year_built/floors/area/current_age 独立随机,facility 维度会有差异
    - 保留 random.seed(seed)=42 保证可重现
    """
    random.seed(seed)

    if verbose:
        print("=" * 60)
        print("BuildHealth · Simulated Engineering Data Seeder")
        print(f"  n_buildings={n_buildings}, days={days}, seed={seed}")
        print("=" * 60)

    wipe_database()
    if verbose:
        print("[1/5] Database wiped & tables recreated")

    session = SessionLocal()
    try:
        stats = {
            "buildings": 0, "components": 0, "sensors": 0, "records": 0,
            "alerts": 0, "assessments": 0, "engineering_notes": 0,
        }

        for i in range(n_buildings):
            profile_key = random.choice(_PROFILE_KEYS)
            profile = BUILDING_PROFILES[profile_key]
            year_built = 1990 + random.randint(0, 30)
            template = {
                **profile,
                "name": f"Simulated Building {i + 1} ({profile_key})",
                "address": f"Simulated Address {i + 1}, District {chr(65 + i % 26)}",
                "year_built": year_built,
                "floors": random.choice([4, 6, 8, 12, 18]),
                "area": random.uniform(2000, 12000),
                "current_age": 2026 - year_built,
                "description": (
                    f"Simulated {profile_key} building (scaled from v1.0 templates)."
                ),
            }

            b = build_building(session, template)
            stats["buildings"] += 1

            comps = build_components(session, b)
            stats["components"] += len(comps)

            sensors = build_sensors(session, b, comps)
            stats["sensors"] += len(sensors)

            n_records = build_records(session, b, sensors, template, days)
            stats["records"] += n_records

            alerts = run_anomaly_detection(session, b, sensors)
            stats["alerts"] += len(alerts)

            assessment = run_health_assessment(session, b, sensors, alerts)
            stats["assessments"] += 1

            cls = run_risk_classification(session, b, assessment, alerts)

            # Phase 4 V2 · 工程笔记(按 profile_key 复用)
            note = build_engineering_note(session, b, comps, profile_key)
            if note is not None:
                stats["engineering_notes"] += 1

            if verbose:
                print(
                    f"\n  → [{i + 1}/{n_buildings}] {b.name}\n"
                    f"     records={n_records}, alerts={len(alerts)} "
                    f"(H={sum(1 for a in alerts if a.severity=='high')}, "
                    f"M={sum(1 for a in alerts if a.severity=='medium')}, "
                    f"L={sum(1 for a in alerts if a.severity=='low')})\n"
                    f"     BHI={assessment.score:.2f} | {cls.risk_level}\n"
                    f"     notes={1 if note else 0}\n"
                )

        session.commit()

        if verbose:
            print("=" * 60)
            print("Seed summary:")
            for k, v in stats.items():
                print(f"  {k}: {v}")
            print("=" * 60)

        return stats
    finally:
        session.close()


if __name__ == "__main__":
    main()
