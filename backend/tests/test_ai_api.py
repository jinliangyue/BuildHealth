"""
AI API 测试 · Phase 5 V3
"""
from datetime import datetime, timedelta
import random

import pytest


# ============ Fixtures ============
@pytest.fixture
def api_building(test_session):
    from app.db import models as m
    from app.analytics import anomaly as anom
    from app.analytics.config import ANOMALY_DEDUP_HOURS

    b = m.Building(
        name="API Test Building",
        address="addr",
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
    c = m.Component(building_id=b.id, name="C1", component_type="column", location="loc")
    test_session.add(c)
    test_session.flush()
    s = m.Sensor(
        building_id=b.id, component_id=c.id, sensor_type="crack_width",
        name="crack_sensor", unit="mm", location="loc", status="active",
    )
    test_session.add(s)
    test_session.flush()
    end = datetime.utcnow().replace(microsecond=0, second=0, minute=0)
    for i in range(20):
        test_session.add(m.MonitoringRecord(
            sensor_id=s.id, timestamp=end - timedelta(days=20 - i),
            value=0.1 + 0.005 * i, quality_flag="simulated",
        ))
    test_session.flush()
    records = test_session.query(m.MonitoringRecord).filter(m.MonitoringRecord.sensor_id == s.id).order_by(m.MonitoringRecord.timestamp).all()
    seen = {}
    for i, rec in enumerate(records):
        prev = records[i - 1].value if i > 0 else None
        history = [r.value for r in records[max(0, i - 168):i]]
        results = anom.detect_for_record(
            sensor_id=s.id, building_id=b.id, metric="crack_width",
            timestamp=rec.timestamp, value=rec.value,
            previous_value=prev, history_values=history,
        )
        for a in results:
            sig = (s.id, "crack_width", a.detection_method, a.severity)
            last_ts = seen.get(sig)
            if last_ts and (rec.timestamp - last_ts).total_seconds() < ANOMALY_DEDUP_HOURS * 3600:
                continue
            seen[sig] = rec.timestamp
            test_session.add(m.RiskAlert(
                building_id=b.id, sensor_id=s.id, metric="crack_width",
                timestamp=rec.timestamp, current_value=a.current_value,
                baseline_value=a.baseline_value, change=a.change,
                detection_method=a.detection_method, severity=a.severity,
                explanation=a.explanation, status="active",
            ))
    test_session.flush()
    return b


# ============ /api/ai/health ============
def test_ai_health_ok(client):
    r = client.get("/api/ai/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["provider"] == "mock"
    assert data["model"] == "mock-deterministic-v1"


# ============ /api/ai/buildings/{id}/summary ============
def test_ai_summary_404(client):
    r = client.post("/api/ai/buildings/99999/summary")
    assert r.status_code == 404


def test_ai_summary_full_response_shape(client, test_session, api_building):
    b = api_building
    r = client.post(f"/api/ai/buildings/{b.id}/summary")
    assert r.status_code == 200
    data = r.json()
    for k in [
        "answer", "key_findings", "evidence", "recommended_actions",
        "disclaimer", "provider", "model", "calculation_version", "created_at",
    ]:
        assert k in data
    assert data["provider"] == "mock"
    assert "AI Engineering Assistant" in data["disclaimer"] or "Prototype" in data["disclaimer"]
    assert isinstance(data["key_findings"], list)
    assert isinstance(data["evidence"], list)
    assert isinstance(data["recommended_actions"], list)


# ============ /api/ai/buildings/{id}/ask ============
def test_ai_ask_404(client):
    r = client.post("/api/ai/buildings/99999/ask", json={"question": "hello"})
    assert r.status_code == 404


def test_ai_ask_missing_question(client, test_session, api_building):
    b = api_building
    r = client.post(f"/api/ai/buildings/{b.id}/ask", json={})
    assert r.status_code == 422


def test_ai_ask_empty_question(client, test_session, api_building):
    b = api_building
    r = client.post(f"/api/ai/buildings/{b.id}/ask", json={"question": ""})
    assert r.status_code == 422


def test_ai_ask_too_long_question(client, test_session, api_building):
    b = api_building
    r = client.post(
        f"/api/ai/buildings/{b.id}/ask",
        json={"question": "x" * 2001},
    )
    assert r.status_code == 422


def test_ai_ask_valid_question(client, test_session, api_building):
    b = api_building
    r = client.post(
        f"/api/ai/buildings/{b.id}/ask",
        json={"question": "Summarize the building health status"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert b.name in data["answer"]


# ============ OpenAPI ============
def test_openapi_includes_ai_endpoints(client):
    r = client.get("/openapi.json")
    spec = r.json()
    paths = spec["paths"]
    assert "/api/ai/health" in paths
    assert "/api/ai/buildings/{building_id}/summary" in paths
    assert "/api/ai/buildings/{building_id}/ask" in paths


# ============ Main app /api/health includes AI ============
def test_main_health_includes_ai_component(client):
    r = client.get("/api/health")
    data = r.json()
    assert "ai_assistant" in data["components"]
