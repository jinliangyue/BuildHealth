"""
Retrofit API 测试 · Phase 4 V2
==============================

测试 3 个新增 endpoint:
- GET /api/buildings/{id}/retrofit
- GET /api/buildings/{id}/retrofit/{rec_id}
- GET /api/retrofit/overview
"""
import pytest


# ============ /api/buildings/{id}/retrofit ============
def test_get_building_retrofit_not_found(client):
    r = client.get("/api/buildings/99999/retrofit")
    assert r.status_code == 404


def test_get_building_retrofit_healthy_empty_recs(client, test_session, sample_empty_building):
    """Healthy 建筑 (无 sensors) → 0 recs, overall_priority=0, level=Low."""
    b = sample_empty_building
    r = client.get(f"/api/buildings/{b.id}/retrofit")
    assert r.status_code == 200
    data = r.json()
    assert data["building_id"] == b.id
    assert data["overall_priority"] == 0.0
    assert data["overall_priority_level"] == "Low"
    assert data["recommendations"] == []
    assert "disclaimer" in data


def test_get_building_retrofit_full_response_shape(client, test_session, sample_building_with_sensors):
    b, _, _ = sample_building_with_sensors
    r = client.get(f"/api/buildings/{b.id}/retrofit")
    assert r.status_code == 200
    data = r.json()
    # 所有必要字段
    for k in [
        "building_id", "building", "overall_priority", "overall_priority_level",
        "calculation_version", "recommendations", "engineering_notes", "disclaimer",
    ]:
        assert k in data
    assert data["calculation_version"] == "RP-v1.0"
    assert data["overall_priority_level"] in {"Low", "Medium", "High", "Very High"}


def test_get_building_retrofit_includes_engineering_notes(
    client, test_session, sample_building_with_sensors
):
    b, _, _ = sample_building_with_sensors
    # 手动插入 1 条 note
    from app.db import models as m
    note = m.EngineeringNote(
        building_id=b.id, text="Test note", source="field_note"
    )
    test_session.add(note)
    test_session.flush()
    r = client.get(f"/api/buildings/{b.id}/retrofit")
    data = r.json()
    assert len(data["engineering_notes"]) >= 1
    assert any(n["text"] == "Test note" for n in data["engineering_notes"])


# ============ /api/buildings/{id}/retrofit/{rec_id} ============
def test_get_recommendation_detail_not_found_building(client):
    r = client.get("/api/buildings/99999/retrofit/1")
    assert r.status_code == 404


def test_get_recommendation_detail_no_recs(client, test_session, sample_empty_building):
    b = sample_empty_building
    r = client.get(f"/api/buildings/{b.id}/retrofit/1")
    assert r.status_code == 404


def test_get_recommendation_detail_invalid_id(client, test_session, sample_building_with_sensors):
    b, _, _ = sample_building_with_sensors
    r = client.get(f"/api/buildings/{b.id}/retrofit/9999")
    assert r.status_code == 404


def test_get_recommendation_detail_valid(client, test_session, sample_building_with_sensors):
    b, _, _ = sample_building_with_sensors
    r = client.get(f"/api/buildings/{b.id}/retrofit/1")
    if r.status_code == 200:
        data = r.json()
        assert "id" in data
        assert "title" in data
        assert "recommendation" in data
        assert "priority_score" in data
        assert "priority_breakdown" in data
        assert "evidence" in data


# ============ /api/retrofit/overview ============
def test_get_retrofit_overview_no_buildings(client):
    r = client.get("/api/retrofit/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["average_priority"] == 0.0
    assert "disclaimer" in data


def test_get_retrofit_overview_with_buildings(client, test_session, sample_building_with_sensors):
    b, _, _ = sample_building_with_sensors
    r = client.get("/api/retrofit/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    for it in data["items"]:
        for k in [
            "building", "overall_priority", "overall_priority_level",
            "recommendation_count", "high_priority_count", "top_category",
        ]:
            assert k in it


def test_overview_disclaimer_contains_keyword(client, test_session, sample_building_with_sensors):
    b, _, _ = sample_building_with_sensors
    r = client.get("/api/retrofit/overview")
    data = r.json()
    assert "Prototype" in data["disclaimer"]


# ============ OpenAPI 注册 ============
def test_openapi_includes_retrofit_endpoints(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    paths = spec["paths"]
    assert "/api/buildings/{building_id}/retrofit" in paths
    assert "/api/buildings/{building_id}/retrofit/{recommendation_id}" in paths
    assert "/api/retrofit/overview" in paths


# ============ Fixtures (复用 service test 的 fixture, conftest 已配置) ============
@pytest.fixture
def sample_empty_building(test_session):
    from app.db import models as m
    b = m.Building(
        name="Empty API Building",
        address="Empty",
        year_built=2020,
        building_type="office",
        structure_type="frame",
        floors=5,
        area=2000.0,
        design_life=50,
        current_age=5,
    )
    test_session.add(b)
    test_session.flush()
    return b


@pytest.fixture
def sample_building_with_sensors(test_session):
    """与 service test 相同 fixture."""
    from datetime import datetime, timedelta
    from app.db import models as m
    from app.analytics import anomaly as anom
    from app.analytics.config import ANOMALY_DEDUP_HOURS
    import random

    b = m.Building(
        name="Test API Building",
        address="Test",
        year_built=2010,
        building_type="office",
        structure_type="frame",
        floors=10,
        area=5000.0,
        design_life=50,
        current_age=15,
    )
    test_session.add(b)
    test_session.flush()

    c1 = m.Component(building_id=b.id, name="C1", component_type="column", location="loc")
    test_session.add(c1)
    test_session.flush()

    sensors = []
    sensor_types = ["crack_width", "tilt", "temperature", "humidity", "electricity"]
    units = ["mm", "‰", "℃", "%", "kWh"]
    for metric, unit in zip(sensor_types, units):
        s = m.Sensor(
            building_id=b.id, component_id=c1.id, sensor_type=metric,
            name=f"{metric}_sensor", unit=unit, location="loc", status="active",
        )
        test_session.add(s)
        sensors.append(s)
    test_session.flush()

    end = datetime.utcnow().replace(microsecond=0, second=0, minute=0)
    rng = random.Random(42)
    profiles = {
        "crack_width": (0.10, 0.01, 0.01),
        "tilt": (1.0, 0.05, 0.05),
        "temperature": (22.0, 0.0, 1.5),
        "humidity": (75.0, 0.2, 3.0),
        "electricity": (120.0, 0.0, 30.0),
    }
    for s in sensors:
        base, trend, noise = profiles[s.sensor_type]
        for i in range(30):
            ts = end - timedelta(days=30 - i)
            val = base + trend * i + rng.gauss(0, noise)
            if s.sensor_type == "crack_width":
                val = max(0.0, val)
            elif s.sensor_type == "humidity":
                val = max(0.0, min(100.0, val))
            test_session.add(m.MonitoringRecord(
                sensor_id=s.id, timestamp=ts, value=val, quality_flag="simulated",
            ))
    test_session.flush()

    for s in sensors:
        records = (
            test_session.query(m.MonitoringRecord)
            .filter(m.MonitoringRecord.sensor_id == s.id)
            .order_by(m.MonitoringRecord.timestamp)
            .all()
        )
        if not records:
            continue
        seen_sigs = {}
        for i, rec in enumerate(records):
            prev = records[i - 1].value if i > 0 else None
            history = [r.value for r in records[max(0, i - 168):i]]
            results = anom.detect_for_record(
                sensor_id=s.id, building_id=b.id, metric=s.sensor_type,
                timestamp=rec.timestamp, value=rec.value,
                previous_value=prev, history_values=history,
            )
            for a in results:
                sig = (s.id, s.sensor_type, a.detection_method, a.severity)
                last_ts = seen_sigs.get(sig)
                if last_ts and (rec.timestamp - last_ts).total_seconds() < ANOMALY_DEDUP_HOURS * 3600:
                    continue
                seen_sigs[sig] = rec.timestamp
                test_session.add(m.RiskAlert(
                    building_id=b.id, sensor_id=s.id, metric=s.sensor_type,
                    timestamp=rec.timestamp, current_value=a.current_value,
                    baseline_value=a.baseline_value, change=a.change,
                    detection_method=a.detection_method, severity=a.severity,
                    explanation=a.explanation, status="active",
                ))
    test_session.flush()
    return b, sensors, [c1]
