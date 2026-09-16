"""
FastAPI API 集成测试 · 用 in-memory SQLite + 真实 service
"""
import pytest
from datetime import datetime, timedelta

from app.db import models as m


def _seed_minimal_building(session):
    """在测试 DB 写入 1 栋建筑 + 5 sensor + 30 条监测数据 + 计算 health + alerts"""
    b = m.Building(
        name="Test Building",
        address="Test Addr",
        year_built=2010,
        building_type="office",
        structure_type="frame",
        floors=10,
        area=5000.0,
        design_life=50,
        current_age=16,
    )
    session.add(b)
    session.flush()

    metrics = [
        ("crack_width", "mm"),
        ("tilt", "‰"),
        ("temperature", "℃"),
        ("humidity", "%"),
        ("electricity", "kWh"),
    ]
    sensors = []
    for metric, unit in metrics:
        s = m.Sensor(
            building_id=b.id, sensor_type=metric, name=f"{metric}_test",
            unit=unit, location="test", status="active",
        )
        session.add(s)
        sensors.append(s)
    session.flush()

    # 30 天历史数据
    end = datetime.utcnow().replace(microsecond=0)
    for i, s in enumerate(sensors):
        for day in range(30):
            base = 0.1 if s.sensor_type == "crack_width" else 20.0
            val = base + day * 0.005 * (1 if s.sensor_type in ("crack_width", "tilt") else 0)
            rec = m.MonitoringRecord(
                sensor_id=s.id,
                timestamp=end - timedelta(days=30 - day),
                value=val,
                quality_flag="simulated",
            )
            session.add(rec)
    session.commit()
    session.refresh(b)
    return b


def test_api_buildings_empty(client):
    """空库 GET /api/buildings/ 返回 []"""
    r = client.get("/api/buildings/")
    assert r.status_code == 200
    assert r.json() == []


def test_api_building_not_found(client):
    r = client.get("/api/buildings/999")
    assert r.status_code == 404


def test_api_building_detail(client, test_engine):
    """GET /api/buildings/1 返回建筑档案"""
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=test_engine)
    s = SessionLocal()
    _seed_minimal_building(s)
    s.close()

    r = client.get("/api/buildings/1")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Test Building"
    assert data["year_built"] == 2010


def test_api_sensors(client, test_engine):
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=test_engine)
    s = SessionLocal()
    _seed_minimal_building(s)
    s.close()

    r = client.get("/api/buildings/1/sensors")
    assert r.status_code == 200
    sensors = r.json()
    assert len(sensors) == 5
    types = {s["sensor_type"] for s in sensors}
    assert types == {"crack_width", "tilt", "temperature", "humidity", "electricity"}


def test_api_monitoring(client, test_engine):
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=test_engine)
    s = SessionLocal()
    _seed_minimal_building(s)
    s.close()

    r = client.get("/api/monitoring/?building_id=1&limit=5")
    assert r.status_code == 200
    records = r.json()
    assert len(records) == 5
    assert all(rec["quality_flag"] == "simulated" for rec in records)


def test_api_monitoring_with_time_range(client, test_engine):
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=test_engine)
    s = SessionLocal()
    _seed_minimal_building(s)
    s.close()

    end = datetime.utcnow()
    start = end - timedelta(days=7)
    r = client.get(
        f"/api/monitoring/?building_id=1&start={start.isoformat()}&end={end.isoformat()}"
    )
    assert r.status_code == 200
    records = r.json()
    # 5 sensors × 7 days = 35
    assert len(records) > 0


def test_api_health_recompute(client, test_engine):
    """POST /api/buildings/{id}/health/recompute 触发完整链路"""
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=test_engine)
    s = SessionLocal()
    _seed_minimal_building(s)
    s.close()

    r = client.post("/api/buildings/1/health/recompute")
    assert r.status_code == 200
    data = r.json()
    assert "score" in data
    assert 0 <= data["score"] <= 100
    assert data["calculation_version"] == "BHI-v1.0"

    # 再 GET
    r2 = client.get("/api/buildings/1/health")
    assert r2.status_code == 200
    assert r2.json()["score"] == data["score"]


def test_api_health_no_assessment_returns_404(client, test_engine):
    """无评估记录时 GET health 返回 404"""
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=test_engine)
    s = SessionLocal()
    _seed_minimal_building(s)
    s.close()

    r = client.get("/api/buildings/1/health")
    assert r.status_code == 404


def test_api_risk(client, test_engine):
    """recompute 后 GET /risk 返回分类"""
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=test_engine)
    s = SessionLocal()
    _seed_minimal_building(s)
    s.close()

    client.post("/api/buildings/1/health/recompute")

    r = client.get("/api/buildings/1/risk")
    assert r.status_code == 200
    data = r.json()
    assert data["risk_level"] in {"Normal", "Attention", "Abnormal", "HighRisk"}
    assert "Prototype Risk Classification" in data["explanation"]
    assert 0 <= data["bhi"] <= 100


def test_api_dashboard_summary(client, test_engine):
    """dashboard 返回真实计算结果（不硬编码）"""
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=test_engine)
    s = SessionLocal()
    _seed_minimal_building(s)
    s.close()

    client.post("/api/buildings/1/health/recompute")

    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["total_buildings"] == 1
    assert data["monitoring_points"] == 5
    assert isinstance(data["average_health_score"], float)
    assert data["average_health_score"] > 0
    assert sum(data["risk_distribution"].values()) == 1


def test_api_dashboard_no_buildings_returns_zeros(client):
    """空库 dashboard 返回 0"""
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["total_buildings"] == 0
    assert data["monitoring_points"] == 0
    assert data["average_health_score"] == 0.0
    assert data["building_ranking"] == []


def test_api_dashboard_values_match_db(client, test_engine):
    """验证 dashboard 数值不是硬编码 - 直接查 DB 对比"""
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=test_engine)
    s = SessionLocal()
    _seed_minimal_building(s)
    s.close()

    client.post("/api/buildings/1/health/recompute")

    data = client.get("/api/dashboard/summary").json()

    # 直接查 DB
    s = SessionLocal()
    n_sensors = s.query(m.Sensor).filter(m.Sensor.status == "active").count()
    n_buildings = s.query(m.Building).count()
    s.close()

    assert data["total_buildings"] == n_buildings
    assert data["monitoring_points"] == n_sensors


def test_api_openapi_docs(client):
    """OpenAPI 文档自动生成"""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    # 必须包含所有业务路由
    expected = [
        "/api/buildings/",
        "/api/buildings/{building_id}",
        "/api/buildings/{building_id}/sensors",
        "/api/monitoring/",
        "/api/buildings/{building_id}/health",
        "/api/buildings/{building_id}/health/recompute",
        "/api/buildings/{building_id}/risk",
        "/api/buildings/{building_id}/alerts",
        "/api/dashboard/summary",
    ]
    for p in expected:
        assert p in paths, f"Missing API path: {p}"


def test_api_root_returns_project_info(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["project"] == "BuildHealth"
    # V2 起 phase 变为 "Phase 4 - V2 Retrofit Decision Support"
    assert "Phase" in data["phase"]
