"""
Database Layer 测试 · 初始化 / 关系 / 基础 CRUD
"""
import pytest
from datetime import datetime

from app.db.base import Base
from app.db import models as m


def test_all_tables_created(test_engine):
    """所有 6 张表被创建"""
    inspector_tables = set(Base.metadata.tables.keys())
    expected = {
        "buildings", "components", "sensors",
        "monitoring_records", "health_assessments", "risk_alerts",
    }
    assert expected.issubset(inspector_tables)


def test_init_db_restores_missing_table(tmp_path):
    """Regression guard for the 4c215de bug class: a table declared on
    ``Base.metadata`` but absent from an existing on-disk SQLite.

    This test must exercise ``init_db()`` itself. The ``test_engine``
    fixture already builds a complete schema, so comparing
    declared-vs-real on that fixture passes even when ``init_db`` is
    deleted outright (verified by mutation). So build a scratch
    file-backed DB, drop ``audit_logs`` to recreate the exact production
    drift (model added, on-disk DB never recreated), then assert
    ``init_db`` fills it back in — and stays idempotent.

    The final ``real == declared`` assertion also covers the full 9-table
    completeness/symmetry check that ``test_all_tables_created`` cannot
    (it only pins the 6 Phase-1 tables). This replaces the old test one
    for one, so no documented test count in README/docs has to move.
    """
    from sqlalchemy import create_engine, inspect, text

    from app.db.session import init_db

    eng = create_engine(f"sqlite:///{tmp_path / 'drift.db'}")
    Base.metadata.create_all(bind=eng)

    with eng.begin() as conn:
        conn.execute(text("DROP TABLE audit_logs"))
    assert "audit_logs" not in inspect(eng).get_table_names(), (
        "precondition failed: DROP TABLE did not remove audit_logs"
    )

    init_db(bind=eng)

    declared = set(Base.metadata.tables.keys())
    real = set(inspect(eng).get_table_names())
    assert not (declared - real), (
        f"init_db() failed to create declared-but-missing tables: "
        f"{sorted(declared - real)}"
    )
    assert real == declared, (
        f"init_db() created tables not declared on Base.metadata: "
        f"{sorted(real - declared)}"
    )

    # Idempotent: a second call neither fails nor changes the schema.
    init_db(bind=eng)
    assert set(inspect(eng).get_table_names()) == declared


def test_building_crud(test_session):
    b = m.Building(
        name="X", address="Y", year_built=2000, building_type="office",
        structure_type="frame", floors=5, area=1000.0,
        design_life=50, current_age=26,
    )
    test_session.add(b)
    test_session.commit()
    assert b.id is not None

    found = test_session.get(m.Building, b.id)
    assert found.name == "X"
    assert found.created_at is not None


def test_building_component_relationship(test_session):
    b = m.Building(
        name="X", address="Y", year_built=2000, building_type="office",
        structure_type="frame", floors=5, area=1000.0,
        design_life=50, current_age=26,
    )
    test_session.add(b)
    test_session.flush()

    c = m.Component(
        building_id=b.id, name="col1", component_type="column",
        location="F1", condition_status="normal",
    )
    test_session.add(c)
    test_session.commit()

    assert len(b.components) == 1
    assert b.components[0].name == "col1"
    assert c.building.name == "X"


def test_sensor_component_relationship(test_session):
    b = m.Building(
        name="X", address="Y", year_built=2000, building_type="office",
        structure_type="frame", floors=5, area=1000.0,
        design_life=50, current_age=26,
    )
    test_session.add(b)
    test_session.flush()
    c = m.Component(
        building_id=b.id, name="col1", component_type="column",
        location="F1", condition_status="normal",
    )
    test_session.add(c)
    test_session.flush()

    s = m.Sensor(
        building_id=b.id, component_id=c.id, sensor_type="crack_width",
        name="s1", unit="mm", location="F1", status="active",
    )
    test_session.add(s)
    test_session.commit()

    assert c.sensors[0].id == s.id
    assert s.component.name == "col1"


def test_monitoring_record_relationship(test_session):
    b = m.Building(
        name="X", address="Y", year_built=2000, building_type="office",
        structure_type="frame", floors=5, area=1000.0,
        design_life=50, current_age=26,
    )
    test_session.add(b)
    test_session.flush()
    s = m.Sensor(
        building_id=b.id, sensor_type="crack_width", name="s1",
        unit="mm", location="F1", status="active",
    )
    test_session.add(s)
    test_session.flush()

    for i in range(5):
        test_session.add(m.MonitoringRecord(
            sensor_id=s.id, timestamp=datetime.utcnow(), value=0.1 + i*0.01,
            quality_flag="simulated",
        ))
    test_session.commit()

    assert len(s.records) == 5


def test_health_assessment_fields(test_session):
    b = m.Building(
        name="X", address="Y", year_built=2000, building_type="office",
        structure_type="frame", floors=5, area=1000.0,
        design_life=50, current_age=26,
    )
    test_session.add(b)
    test_session.flush()

    h = m.HealthAssessment(
        building_id=b.id, score=85.5,
        structural_safety=90, facility_condition=80,
        environmental_quality=85, energy_performance=88, fire_safety=82,
        calculation_version="BHI-v1.0",
        explanation="test",
    )
    test_session.add(h)
    test_session.commit()

    assert h.id is not None
    assert h.calculation_version == "BHI-v1.0"


def test_risk_alert_fields(test_session):
    b = m.Building(
        name="X", address="Y", year_built=2000, building_type="office",
        structure_type="frame", floors=5, area=1000.0,
        design_life=50, current_age=26,
    )
    test_session.add(b)
    test_session.flush()
    s = m.Sensor(
        building_id=b.id, sensor_type="crack_width", name="s1",
        unit="mm", location="F1", status="active",
    )
    test_session.add(s)
    test_session.flush()

    a = m.RiskAlert(
        building_id=b.id, sensor_id=s.id, metric="crack_width",
        timestamp=datetime.utcnow(), current_value=0.5,
        baseline_value=0.3, change=0.2, detection_method="threshold",
        severity="high", explanation="test", status="active",
    )
    test_session.add(a)
    test_session.commit()

    assert a.id is not None
    assert a.severity == "high"
    assert a.status == "active"


def test_cascade_delete_component(test_session):
    b = m.Building(
        name="X", address="Y", year_built=2000, building_type="office",
        structure_type="frame", floors=5, area=1000.0,
        design_life=50, current_age=26,
    )
    test_session.add(b)
    test_session.flush()
    c = m.Component(
        building_id=b.id, name="col1", component_type="column",
        location="F1", condition_status="normal",
    )
    test_session.add(c)
    test_session.flush()
    s = m.Sensor(
        building_id=b.id, component_id=c.id, sensor_type="crack_width",
        name="s1", unit="mm", location="F1", status="active",
    )
    test_session.add(s)
    test_session.commit()

    building_id = b.id
    sensor_id = s.id
    test_session.delete(b)
    test_session.commit()

    # 级联删除
    assert test_session.get(m.Sensor, sensor_id) is None
    assert test_session.query(m.Component).filter_by(building_id=building_id).count() == 0
