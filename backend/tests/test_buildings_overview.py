"""
Buildings Overview Batch API 测试
"""
from datetime import datetime, timedelta

from app.db import models as m


def _seed_building_with_records(session, building_id=1, n_records=10):
    b = m.Building(
        id=building_id,
        name=f"B{building_id}",
        address="Test",
        year_built=2010,
        building_type="office",
        structure_type="frame",
        floors=5,
        area=1000.0,
        design_life=50,
        current_age=16,
    )
    session.add(b)
    session.flush()
    s = m.Sensor(
        building_id=b.id, sensor_type="crack_width", name="s",
        unit="mm", location="loc", status="active",
    )
    session.add(s)
    session.flush()
    for i in range(n_records):
        session.add(m.MonitoringRecord(
            sensor_id=s.id,
            timestamp=datetime.utcnow() - timedelta(days=n_records - i),
            value=0.1 + i * 0.01,
            quality_flag="simulated",
        ))
    session.commit()
    session.refresh(b)
    return b


def test_buildings_overview_empty(client):
    """空库 → total=0, items=[]"""
    r = client.get("/api/buildings/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_buildings_overview_no_assessment(client, test_engine):
    """有建筑但无评估 → health/risk 为 None, alert_count=0"""
    from sqlalchemy.orm import sessionmaker
    SL = sessionmaker(bind=test_engine)
    s = SL()
    _seed_building_with_records(s, building_id=1)
    s.close()

    r = client.get("/api/buildings/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["building"]["id"] == 1
    assert item["health"] is None
    assert item["risk"] is None
    assert item["active_alert_count"] == 0


def test_buildings_overview_with_health(client, test_engine):
    """先 recompute，再 overview"""
    from sqlalchemy.orm import sessionmaker
    SL = sessionmaker(bind=test_engine)
    s = SL()
    _seed_building_with_records(s, building_id=1, n_records=30)
    s.close()

    # recompute 1 次
    rec = client.post("/api/buildings/1/health/recompute")
    assert rec.status_code == 200

    r = client.get("/api/buildings/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["health"] is not None
    assert item["health"]["score"] >= 0
    assert item["risk"] is not None
    assert item["risk"]["risk_level"] in {"Normal", "Attention", "Abnormal", "HighRisk"}
    assert isinstance(item["active_alert_count"], int)


def test_buildings_overview_multiple_buildings(client, test_engine):
    """多建筑全部返回"""
    from sqlalchemy.orm import sessionmaker
    SL = sessionmaker(bind=test_engine)
    s = SL()
    _seed_building_with_records(s, building_id=1, n_records=20)
    _seed_building_with_records(s, building_id=2, n_records=20)
    _seed_building_with_records(s, building_id=3, n_records=20)
    s.close()

    for bid in (1, 2, 3):
        client.post(f"/api/buildings/{bid}/health/recompute")

    r = client.get("/api/buildings/overview")
    data = r.json()
    assert data["total"] == 3
    assert all(item["building"] is not None for item in data["items"])
    assert all(item["health"] is not None for item in data["items"])


def test_buildings_overview_sorted_by_building_id(client, test_engine):
    """按 building id 升序"""
    from sqlalchemy.orm import sessionmaker
    SL = sessionmaker(bind=test_engine)
    s = SL()
    _seed_building_with_records(s, building_id=3)
    _seed_building_with_records(s, building_id=1)
    _seed_building_with_records(s, building_id=2)
    s.close()

    r = client.get("/api/buildings/overview")
    ids = [item["building"]["id"] for item in r.json()["items"]]
    assert ids == [1, 2, 3]


def test_buildings_overview_partial_failure_isolated(client, test_engine, monkeypatch):
    """单建筑异常被隔离，整体不失败"""
    from sqlalchemy.orm import sessionmaker
    SL = sessionmaker(bind=test_engine)
    s = SL()
    _seed_building_with_records(s, building_id=1, n_records=20)
    _seed_building_with_records(s, building_id=2, n_records=20)
    s.close()

    # 仅 building 1 recompute
    client.post("/api/buildings/1/health/recompute")

    # 强制让 building 2 的 anomaly detection 抛错
    import app.api.buildings as api_mod
    orig = api_mod.svc.run_anomaly_detection

    def boom(session, bid):
        if bid == 2:
            raise RuntimeError("simulated failure")
        return orig(session, bid)

    monkeypatch.setattr(api_mod.svc, "run_anomaly_detection", boom)

    r = client.get("/api/buildings/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    # building 1 应有 health
    b1 = next(x for x in data["items"] if x["building"]["id"] == 1)
    assert b1["health"] is not None
    # building 2 在异常路径下应回落到 health=None
    b2 = next(x for x in data["items"] if x["building"]["id"] == 2)
    assert b2["health"] is None


def test_buildings_overview_openapi_registered(client):
    """OpenAPI 文档包含 overview 端点"""
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/buildings/overview" in paths
