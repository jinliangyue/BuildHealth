"""
pytest fixtures · 内存 SQLite + FastAPI TestClient

关键：内存 SQLite 必须用 StaticPool + 共享连接字符串，
否则不同 session 会拿到不同的内存 DB（导致 "no such table"）。
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.db import models as m  # 确保模型注册到 Base.metadata
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def test_engine():
    """共享内存 SQLite 引擎（StaticPool + 单 connection）"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def test_session(test_engine):
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(test_engine):
    """FastAPI TestClient with overridden DB dependency"""
    SessionLocal = sessionmaker(bind=test_engine)

    def override_get_db():
        try:
            db = SessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def full_building(test_session):
    """
    一个完整建筑: component + sensor + 20 条 monitoring records + 派生 alerts.

    共享 fixture (Phase 6B 从 test_ai_service.py 上移到 conftest):
    test_ai_service.py 与 test_knowledge_service.py 都需要它。
    """
    from app.analytics import anomaly as anom
    from app.analytics.config import ANOMALY_DEDUP_HOURS

    b = m.Building(
        name="Service Test Building",
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
            value=0.1 + 0.01 * i, quality_flag="simulated",
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
